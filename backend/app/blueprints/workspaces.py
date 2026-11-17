import uuid
from collections import defaultdict

import sqlalchemy as sa
from flask import Blueprint, g, jsonify
from sqlalchemy.orm import contains_eager

from ..audit import audit
from ..constants import DEFAULT_WORKSPACE_ICON, MAX_WORKSPACE_NAME, OWNER
from ..errors import ApiError, not_found, validation_error
from ..extensions import WRITE_LIMIT, db, limiter
from ..models import Expense, Membership, User, Workspace
from ..security import auth_required
from ..services import (
    active_expenses,
    cancel_pending_invites,
    load_membership,
    member_json,
    members_of,
    month_totals,
    require_roles,
    single_workspace_json,
    workspace_json,
)
from ..timeutil import month_bounds, shift_month, utcnow
from ..validation import check_icon, check_name, json_body, parse_bool_arg, parse_month_arg, validate

bp = Blueprint("workspaces", __name__)

WORKSPACE_FIELDS = {
    "name": (lambda v: check_name(v, MAX_WORKSPACE_NAME), True),
    "icon": (check_icon, False),
}


@bp.get("/workspaces")
@auth_required
def list_workspaces():
    year, month = parse_month_arg()
    include_archived = parse_bool_arg("include_archived")
    query = (
        sa.select(Membership)
        .join(Membership.workspace)
        .options(contains_eager(Membership.workspace))
        .where(Membership.user_id == g.user.id, Workspace.deleted_at.is_(None))
        .order_by(Workspace.created_at, Workspace.id)
    )
    if not include_archived:
        query = query.where(Workspace.archived_at.is_(None))
    mine = list(db.session.execute(query).unique().scalars())
    ids = [m.workspace_id for m in mine]

    members_by_ws: dict[uuid.UUID, list[Membership]] = defaultdict(list)
    if ids:
        rows = db.session.execute(
            sa.select(Membership).where(Membership.workspace_id.in_(ids)).order_by(Membership.joined_at, Membership.id)
        ).scalars()
        for m in rows:
            members_by_ws[m.workspace_id].append(m)
    totals = month_totals(ids, year, month)
    items = [
        workspace_json(m.workspace, m.role, members_by_ws[m.workspace_id], totals.get(m.workspace_id, 0)) for m in mine
    ]
    return jsonify(items=items)


@bp.post("/workspaces")
@limiter.limit(WRITE_LIMIT)
@auth_required
def create_workspace():
    data = validate(json_body(), WORKSPACE_FIELDS)
    ws = Workspace(
        name=data["name"],
        icon=data.get("icon") or DEFAULT_WORKSPACE_ICON,
        owner_id=g.user.id,
        currency="BRL",
    )
    db.session.add(ws)
    db.session.flush()
    membership = Membership(workspace_id=ws.id, user_id=g.user.id, role=OWNER, joined_at=ws.created_at)
    db.session.add(membership)
    db.session.commit()
    year, month = parse_month_arg()
    return jsonify(single_workspace_json(membership, year, month)), 201


@bp.get("/workspaces/<uuid:workspace_id>")
@auth_required
def get_workspace(workspace_id):
    membership = load_membership(workspace_id)
    year, month = parse_month_arg()
    return jsonify(single_workspace_json(membership, year, month))


@bp.patch("/workspaces/<uuid:workspace_id>")
@auth_required
def update_workspace(workspace_id):
    membership = load_membership(workspace_id)
    require_roles(membership, (OWNER,))
    body = json_body()
    data = validate(body, WORKSPACE_FIELDS, partial=True)
    if "archived" in body and not isinstance(body["archived"], bool):
        raise validation_error({"archived": "Use true ou false."})
    ws = membership.workspace
    events = []
    if "name" in data and data["name"] != ws.name:
        ws.name = data["name"]
        events.append("workspace_renamed")
    if "icon" in data:
        ws.icon = data["icon"]
    if "archived" in body:
        if body["archived"] and ws.archived_at is None:
            ws.archived_at = utcnow()
            cancel_pending_invites(ws.id)  # convites pendentes deixam de valer
            events.append("workspace_archived")
        elif not body["archived"] and ws.archived_at is not None:
            ws.archived_at = None
            events.append("workspace_unarchived")
    db.session.commit()
    for event in events:
        audit(event, user_id=g.user.id, workspace_id=ws.id)
    year, month = parse_month_arg()
    return jsonify(single_workspace_json(membership, year, month))


@bp.delete("/workspaces/<uuid:workspace_id>")
@auth_required
def delete_workspace(workspace_id):
    membership = load_membership(workspace_id)
    require_roles(membership, (OWNER,))
    membership.workspace.deleted_at = utcnow()
    db.session.commit()
    audit("workspace_deleted", user_id=g.user.id, workspace_id=workspace_id)
    return "", 204


@bp.get("/workspaces/<uuid:workspace_id>/members")
@auth_required
def list_members(workspace_id):
    load_membership(workspace_id)
    return jsonify(items=[member_json(m) for m in members_of(workspace_id)])


@bp.delete("/workspaces/<uuid:workspace_id>/members/<uuid:user_id>")
@auth_required
def remove_member(workspace_id, user_id):
    membership = load_membership(workspace_id)
    require_roles(membership, (OWNER,))
    if user_id == membership.workspace.owner_id:
        raise ApiError(400, "cannot_remove_owner", "O dono não pode ser removido do ambiente.")
    target = db.session.execute(
        sa.select(Membership).where(Membership.workspace_id == workspace_id, Membership.user_id == user_id)
    ).scalar_one_or_none()
    if target is None:
        raise not_found("Membro não encontrado.")
    db.session.delete(target)
    db.session.commit()
    audit("member_removed", user_id=g.user.id, workspace_id=workspace_id, removed_user_id=user_id)
    return "", 204


@bp.post("/workspaces/<uuid:workspace_id>/leave")
@auth_required
def leave_workspace(workspace_id):
    membership = load_membership(workspace_id)
    if membership.role == OWNER:
        raise ApiError(400, "owner_cannot_leave", "O dono não pode sair do ambiente. Exclua-o ou arquive-o.")
    db.session.delete(membership)
    db.session.commit()
    audit("workspace_left", user_id=g.user.id, workspace_id=workspace_id)
    return "", 204


@bp.get("/workspaces/<uuid:workspace_id>/summary")
@auth_required
def summary(workspace_id):
    load_membership(workspace_id)
    year, month = parse_month_arg()
    start, end = month_bounds(year, month)
    in_month = (
        Expense.workspace_id == workspace_id,
        active_expenses(),
        Expense.spent_at >= start,
        Expense.spent_at < end,
    )
    total_sum = sa.func.coalesce(sa.func.sum(Expense.amount_cents), 0)

    total, count = db.session.execute(sa.select(total_sum, sa.func.count(Expense.id)).where(*in_month)).one()

    by_category = [
        {"category": cat, "total_cents": int(t), "count": int(c)}
        for cat, t, c in db.session.execute(
            sa.select(Expense.category, total_sum, sa.func.count(Expense.id))
            .where(*in_month)
            .group_by(Expense.category)
        ).all()
        if int(t) > 0
    ]
    by_category.sort(key=lambda row: (-row["total_cents"], row["category"]))

    author_rows = {
        uid: (name, int(t), int(c))
        for uid, name, t, c in db.session.execute(
            sa.select(Expense.author_id, User.display_name, total_sum, sa.func.count(Expense.id))
            .join(User, User.id == Expense.author_id)
            .where(*in_month)
            .group_by(Expense.author_id, User.display_name)
        ).all()
    }
    by_author = []
    for m in members_of(workspace_id):
        _, t, c = author_rows.pop(m.user_id, (None, 0, 0))
        by_author.append({"user_id": str(m.user_id), "display_name": m.user.display_name, "total_cents": t, "count": c})
    for uid, (name, t, c) in sorted(author_rows.items(), key=lambda kv: -kv[1][1]):
        by_author.append({"user_id": str(uid), "display_name": name, "total_cents": t, "count": c})

    months = [shift_month(year, month, -i) for i in range(5, -1, -1)]
    first_start, _ = month_bounds(*months[0])
    evo_rows = db.session.execute(
        sa.select(Expense.spent_at, total_sum)
        .where(
            Expense.workspace_id == workspace_id,
            active_expenses(),
            Expense.spent_at >= first_start,
            Expense.spent_at < end,
        )
        .group_by(Expense.spent_at)
    ).all()
    per_month: dict[tuple[int, int], int] = defaultdict(int)
    for spent_at, t in evo_rows:
        per_month[(spent_at.year, spent_at.month)] += int(t)
    evolution = [{"month": f"{y:04d}-{m:02d}", "total_cents": per_month[(y, m)]} for y, m in months]

    return jsonify(
        month=f"{year:04d}-{month:02d}",
        total_cents=int(total),
        count=int(count),
        by_category=by_category,
        by_author=by_author,
        evolution=evolution,
    )
