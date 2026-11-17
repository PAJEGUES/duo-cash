import sqlalchemy as sa
from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from ..constants import CATEGORIES, MAX_AMOUNT_CENTS
from ..errors import ApiError, not_found, validation_error
from ..extensions import WRITE_LIMIT, db, limiter
from ..models import Expense, Workspace
from ..security import auth_required
from ..services import active_expenses, expense_json, load_membership, require_active, require_writer
from ..timeutil import utcnow
from ..validation import (
    MAX_OFFSET,
    check_amount,
    check_category,
    check_description,
    check_icon_key,
    check_spent_at,
    json_body,
    parse_date_arg,
    parse_int_arg,
    parse_uuid_arg,
    validate,
)

bp = Blueprint("expenses", __name__)

EXPENSE_FIELDS = {
    "amount_cents": (check_amount, True),
    "spent_at": (check_spent_at, True),
    "description": (check_description, True),
    "category": (check_category, True),
    "icon_key": (check_icon_key, False),
}
MAX_IDEMPOTENCY_KEY = 128


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _list_filters(workspace_id) -> list:
    filters = [Expense.workspace_id == workspace_id, active_expenses()]
    q = (request.args.get("q") or "").strip()
    if q:
        if len(q) > 100:
            raise validation_error({"q": "Busca longa demais."})
        filters.append(Expense.description.ilike(f"%{_like_escape(q)}%", escape="\\"))
    category = request.args.get("category")
    if category:
        cats = [c.strip() for c in category.split(",") if c.strip()]
        if any(c not in CATEGORIES for c in cats):
            raise validation_error({"category": "Categoria inválida."})
        if cats:
            filters.append(Expense.category.in_(cats))
    author_id = parse_uuid_arg("author_id")
    if author_id:
        filters.append(Expense.author_id == author_id)
    date_from, date_to = parse_date_arg("date_from"), parse_date_arg("date_to")
    if date_from:
        filters.append(Expense.spent_at >= date_from)
    if date_to:
        filters.append(Expense.spent_at <= date_to)
    amount_min = parse_int_arg("amount_min", minimum=0, maximum=MAX_AMOUNT_CENTS)
    amount_max = parse_int_arg("amount_max", minimum=0, maximum=MAX_AMOUNT_CENTS)
    if amount_min is not None:
        filters.append(Expense.amount_cents >= amount_min)
    if amount_max is not None:
        filters.append(Expense.amount_cents <= amount_max)
    return filters


@bp.get("/workspaces/<uuid:workspace_id>/expenses")
@auth_required
def list_expenses(workspace_id):
    load_membership(workspace_id)
    filters = _list_filters(workspace_id)
    limit = parse_int_arg("limit", 50, minimum=1, maximum=200)
    offset = parse_int_arg("offset", 0, minimum=0, maximum=MAX_OFFSET)

    total_count, total_cents = db.session.execute(
        sa.select(sa.func.count(Expense.id), sa.func.coalesce(sa.func.sum(Expense.amount_cents), 0)).where(*filters)
    ).one()
    items = list(
        db.session.execute(
            sa.select(Expense)
            .where(*filters)
            .order_by(Expense.spent_at.desc(), Expense.created_at.desc(), Expense.id.desc())
            .limit(limit)
            .offset(offset)
        ).scalars()
    )
    next_offset = offset + len(items)
    return jsonify(
        items=[expense_json(e) for e in items],
        total_count=int(total_count),
        total_cents=int(total_cents),
        next_offset=next_offset if next_offset < total_count else None,
    )


def _find_by_key(key: str):
    return db.session.execute(
        sa.select(Expense).where(Expense.author_id == g.user.id, Expense.idempotency_key == key)
    ).scalar_one_or_none()


def _replay(existing: Expense, workspace_id):
    if existing.workspace_id != workspace_id:
        raise ApiError(409, "idempotency_conflict", "Esta chave de envio já foi usada em outro ambiente.")
    if existing.deleted_at is not None:
        raise ApiError(409, "idempotency_conflict", "Este gasto já foi enviado e depois excluído.")
    return jsonify(expense_json(existing)), 200


@bp.post("/workspaces/<uuid:workspace_id>/expenses")
@limiter.limit(WRITE_LIMIT)
@auth_required
def create_expense(workspace_id):
    membership = load_membership(workspace_id)
    require_writer(membership)
    require_active(membership.workspace)

    key = request.headers.get("Idempotency-Key")
    if key is not None:
        key = key.strip()
        if not key or len(key) > MAX_IDEMPOTENCY_KEY:
            raise validation_error({"Idempotency-Key": "Chave de envio inválida."})
        existing = _find_by_key(key)
        if existing is not None:
            return _replay(existing, workspace_id)

    data = validate(json_body(), EXPENSE_FIELDS)
    now = utcnow()
    expense = Expense(
        workspace_id=workspace_id,
        author_id=g.user.id,
        idempotency_key=key,
        created_at=now,
        updated_at=now,
        **data,
    )
    db.session.add(expense)
    try:
        db.session.commit()
    except IntegrityError:
        # Mesma chave enviada em paralelo: a outra requisição gravou primeiro.
        db.session.rollback()
        existing = _find_by_key(key) if key else None
        if existing is None:
            raise
        return _replay(existing, workspace_id)
    return jsonify(expense_json(expense)), 201


def _load_expense_for_write(expense_id) -> Expense:
    expense = db.session.execute(
        sa.select(Expense)
        .join(Workspace, Workspace.id == Expense.workspace_id)
        .where(Expense.id == expense_id, active_expenses(), Workspace.deleted_at.is_(None))
    ).scalar_one_or_none()
    if expense is None:
        raise not_found("Gasto não encontrado.")
    membership = load_membership(expense.workspace_id)  # 404 para não membros
    require_writer(membership)
    require_active(membership.workspace)
    return expense


@bp.patch("/expenses/<uuid:expense_id>")
@auth_required
def update_expense(expense_id):
    expense = _load_expense_for_write(expense_id)
    data = validate(json_body(), EXPENSE_FIELDS, partial=True)
    for field, value in data.items():
        setattr(expense, field, value)
    if data:
        expense.updated_at = utcnow()
    db.session.commit()
    return jsonify(expense_json(expense))


@bp.delete("/expenses/<uuid:expense_id>")
@auth_required
def delete_expense(expense_id):
    expense = _load_expense_for_write(expense_id)
    expense.deleted_at = utcnow()
    expense.updated_at = expense.deleted_at
    db.session.commit()
    return "", 204
