"""Regras compartilhadas: acesso ao ambiente, totais e serialização."""

import uuid
from datetime import date

import sqlalchemy as sa
from flask import g, request

from .audit import audit
from .constants import WRITE_ROLES
from .errors import ApiError, forbidden, not_found
from .extensions import db
from .models import Expense, Invite, Membership, User, Workspace
from .timeutil import iso, month_bounds, utcnow

# --- acesso -------------------------------------------------------------------


def load_membership(workspace_id: uuid.UUID) -> Membership:
    """Vínculo do usuário logado com o ambiente; 404 se não for membro ou se foi excluído."""
    membership = db.session.execute(
        sa.select(Membership)
        .join(Workspace, Workspace.id == Membership.workspace_id)
        .where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == g.user.id,
            Workspace.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if membership is None:
        raise not_found("Ambiente não encontrado.")
    return membership


def require_roles(membership: Membership, roles) -> None:
    if membership.role not in roles:
        audit(
            "permission_denied",
            user_id=membership.user_id,
            workspace_id=membership.workspace_id,
            role=membership.role,
            endpoint=request.endpoint,
        )
        raise forbidden()


def require_writer(membership: Membership) -> None:
    require_roles(membership, WRITE_ROLES)


def require_active(workspace: Workspace) -> None:
    """Ambiente arquivado é somente leitura (exceto PATCH/DELETE do próprio ambiente pelo dono)."""
    if workspace.archived_at is not None:
        raise ApiError(409, "workspace_archived", "Este ambiente está arquivado. Desarquive-o para fazer alterações.")


def cancel_pending_invites(workspace_id: uuid.UUID) -> None:
    now = utcnow()
    db.session.execute(
        sa.update(Invite)
        .where(
            Invite.workspace_id == workspace_id,
            Invite.consumed_at.is_(None),
            Invite.cancelled_at.is_(None),
            Invite.expires_at > now,
        )
        .values(cancelled_at=now)
    )


# --- totais -------------------------------------------------------------------


def active_expenses():
    return Expense.deleted_at.is_(None)


def month_totals(workspace_ids: list[uuid.UUID], year: int, month: int) -> dict[uuid.UUID, int]:
    if not workspace_ids:
        return {}
    start, end = month_bounds(year, month)
    rows = db.session.execute(
        sa.select(Expense.workspace_id, sa.func.coalesce(sa.func.sum(Expense.amount_cents), 0))
        .where(
            Expense.workspace_id.in_(workspace_ids),
            active_expenses(),
            Expense.spent_at >= start,
            Expense.spent_at < end,
        )
        .group_by(Expense.workspace_id)
    ).all()
    return {wid: int(total) for wid, total in rows}


# --- serialização -------------------------------------------------------------


def user_json(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }


def member_json(m: Membership) -> dict:
    return {
        "user_id": str(m.user_id),
        "display_name": m.user.display_name,
        "email": m.user.email,
        "avatar_url": m.user.avatar_url,
        "role": m.role,
        "joined_at": iso(m.joined_at),
    }


def members_of(workspace_id: uuid.UUID) -> list[Membership]:
    return list(
        db.session.execute(
            sa.select(Membership)
            .where(Membership.workspace_id == workspace_id)
            .order_by(Membership.joined_at, Membership.id)
        ).scalars()
    )


def workspace_json(ws: Workspace, role: str, members: list[Membership], month_total: int) -> dict:
    return {
        "id": str(ws.id),
        "name": ws.name,
        "icon": ws.icon,
        "currency": ws.currency,
        "role": role,
        "owner_id": str(ws.owner_id),
        "created_at": iso(ws.created_at),
        "archived_at": iso(ws.archived_at),
        "members": [member_json(m) for m in members],
        "month_total_cents": month_total,
    }


def single_workspace_json(membership: Membership, year: int, month: int) -> dict:
    ws = membership.workspace
    total = month_totals([ws.id], year, month).get(ws.id, 0)
    return workspace_json(ws, membership.role, members_of(ws.id), total)


def expense_json(e: Expense) -> dict:
    return {
        "id": str(e.id),
        "workspace_id": str(e.workspace_id),
        "author": {
            "id": str(e.author.id),
            "display_name": e.author.display_name,
            "avatar_url": e.author.avatar_url,
        },
        "amount_cents": e.amount_cents,
        "spent_at": e.spent_at.isoformat() if isinstance(e.spent_at, date) else e.spent_at,
        "description": e.description,
        "category": e.category,
        "icon_key": e.icon_key,
        "created_at": iso(e.created_at),
        "updated_at": iso(e.updated_at),
    }


def invite_list_json(inv: Invite) -> dict:
    return {
        "id": str(inv.id),
        "role": inv.role,
        "created_at": iso(inv.created_at),
        "expires_at": iso(inv.expires_at),
        "created_by": str(inv.created_by),
    }
