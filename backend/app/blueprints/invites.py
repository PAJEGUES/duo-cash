import re
import secrets
from datetime import timedelta

import sqlalchemy as sa
from flask import Blueprint, current_app, g, jsonify, make_response, render_template
from sqlalchemy.exc import IntegrityError

from ..audit import audit
from ..constants import INVITE_ROLES, OWNER
from ..errors import ApiError, not_found, validation_error
from ..extensions import db, limiter
from ..models import Invite, Membership, Workspace
from ..security import auth_required, hash_token
from ..services import invite_list_json, load_membership, require_active, require_roles, single_workspace_json
from ..timeutil import as_utc, iso, utcnow
from ..validation import json_body, parse_month_arg

bp = Blueprint("invites", __name__)
html_bp = Blueprint("invite_page", __name__)

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
INVITE_USED = ("invite_used", "Este convite já foi usado ou cancelado.")
INVITE_EXPIRED = ("invite_expired", "Este convite expirou. Peça um novo.")


def _pending_filter(now):
    return (Invite.consumed_at.is_(None), Invite.cancelled_at.is_(None), Invite.expires_at > now)


def _find_by_token(token: str) -> Invite:
    """Busca só pelo hash do token (nunca comparamos o token em texto)."""
    if not _TOKEN_RE.match(token):
        raise not_found("Convite não encontrado.")
    invite = db.session.execute(
        sa.select(Invite)
        .join(Workspace, Workspace.id == Invite.workspace_id)
        .where(Invite.token_hash == hash_token(token), Workspace.deleted_at.is_(None))
    ).scalar_one_or_none()
    if invite is None:
        raise not_found("Convite não encontrado.")
    return invite


def _ensure_usable(invite: Invite) -> None:
    if invite.consumed_at is not None or invite.cancelled_at is not None:
        raise ApiError(410, *INVITE_USED)
    if as_utc(invite.expires_at) <= utcnow():
        raise ApiError(410, *INVITE_EXPIRED)


@bp.post("/workspaces/<uuid:workspace_id>/invites")
@limiter.limit("20/minute")
@auth_required
def create_invite(workspace_id):
    membership = load_membership(workspace_id)
    require_roles(membership, (OWNER,))
    require_active(membership.workspace)
    role = json_body().get("role")
    if role not in INVITE_ROLES:
        raise validation_error({"role": "Permissão inválida. Use EDITOR ou VIEWER."})

    token = secrets.token_urlsafe(24)
    now = utcnow()
    invite = Invite(
        workspace_id=workspace_id,
        created_by=g.user.id,
        token_hash=hash_token(token),
        role=role,
        created_at=now,
        expires_at=now + timedelta(minutes=current_app.config["INVITE_TTL_MINUTES"]),
    )
    db.session.add(invite)
    db.session.commit()
    audit("invite_created", user_id=g.user.id, workspace_id=workspace_id, invite_id=invite.id, role=role)
    base = current_app.config["PUBLIC_BASE_URL"]
    return jsonify(
        id=str(invite.id),
        token=token,
        role=role,
        expires_at=iso(invite.expires_at),
        app_url=f"duocash://join/{token}",
        share_url=f"{base}/convite/{token}",
    ), 201


@bp.get("/workspaces/<uuid:workspace_id>/invites")
@auth_required
def list_invites(workspace_id):
    membership = load_membership(workspace_id)
    require_roles(membership, (OWNER,))
    rows = db.session.execute(
        sa.select(Invite)
        .where(Invite.workspace_id == workspace_id, *_pending_filter(utcnow()))
        .order_by(Invite.created_at)
    ).scalars()
    return jsonify(items=[invite_list_json(i) for i in rows])


@bp.delete("/invites/<uuid:invite_id>")
@auth_required
def cancel_invite(invite_id):
    invite = db.session.get(Invite, invite_id)
    if invite is None:
        raise not_found("Convite não encontrado.")
    membership = load_membership(invite.workspace_id)  # 404 para quem não é membro
    require_roles(membership, (OWNER,))
    if invite.consumed_at is None and invite.cancelled_at is None:
        invite.cancelled_at = utcnow()
        db.session.commit()
        audit("invite_cancelled", user_id=g.user.id, workspace_id=invite.workspace_id, invite_id=invite.id)
    return "", 204


@bp.get("/invites/<token>")
@limiter.limit("30/minute")
@auth_required
def preview_invite(token):
    invite = _find_by_token(token)
    if invite.workspace.archived_at is not None:
        raise ApiError(410, *INVITE_USED)
    _ensure_usable(invite)
    return jsonify(
        workspace_name=invite.workspace.name,
        workspace_icon=invite.workspace.icon,
        role=invite.role,
        invited_by=invite.creator.display_name,
        expires_at=iso(invite.expires_at),
    )


@bp.post("/invites/<token>/accept")
@limiter.limit("30/minute")
@auth_required
def accept_invite(token):
    invite = _find_by_token(token)
    require_active(invite.workspace)
    year, month = parse_month_arg()

    def existing_membership():
        return db.session.execute(
            sa.select(Membership).where(Membership.workspace_id == invite.workspace_id, Membership.user_id == g.user.id)
        ).scalar_one_or_none()

    current = existing_membership()
    if current is not None:  # já é membro: não consome o convite
        return jsonify(workspace=single_workspace_json(current, year, month))

    _ensure_usable(invite)
    now = utcnow()
    # UPDATE condicional: só um aceite concorrente consegue marcar o convite.
    result = db.session.execute(
        sa.update(Invite)
        .where(Invite.id == invite.id, *_pending_filter(now))
        .values(consumed_at=now, consumed_by=g.user.id)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.session.rollback()
        db.session.refresh(invite)
        _ensure_usable(invite)
        raise ApiError(410, *INVITE_USED)

    membership = Membership(workspace_id=invite.workspace_id, user_id=g.user.id, role=invite.role, joined_at=now)
    db.session.add(membership)
    try:
        db.session.commit()
    except IntegrityError:  # entrou por outro convite ao mesmo tempo; este não é consumido
        db.session.rollback()
        current = existing_membership()
        if current is None:
            raise
        return jsonify(workspace=single_workspace_json(current, year, month))
    audit("invite_accepted", user_id=g.user.id, workspace_id=invite.workspace_id, invite_id=invite.id)
    return jsonify(workspace=single_workspace_json(membership, year, month))


@html_bp.get("/convite/<token>")
def invite_page(token):
    if not _TOKEN_RE.match(token):
        token = None
    html = render_template("convite.html", token=token)
    response = make_response(html, 200 if token else 404)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response
