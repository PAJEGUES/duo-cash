import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .constants import CATEGORIES, DEFAULT_WORKSPACE_ICON, INVITE_ROLES, ROLES
from .extensions import db
from .timeutil import utcnow

# Enums guardados como texto (portável entre SQLite e PostgreSQL).
RoleEnum = sa.Enum(*ROLES, name="membership_role", native_enum=False, length=10)
InviteRoleEnum = sa.Enum(*INVITE_ROLES, name="invite_role", native_enum=False, length=10)
CategoryEnum = sa.Enum(*CATEGORIES, name="expense_category", native_enum=False, length=32)
TS = sa.DateTime(timezone=True)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    google_sub: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(sa.String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(TS, nullable=False, default=utcnow)
    # Tokens emitidos antes deste instante são recusados (encerra todas as sessões).
    sessions_revoked_at: Mapped[datetime | None] = mapped_column(TS)


class RefreshToken(db.Model):
    """Um refresh token emitido. Guarda só o sha256 do jti; tokens da mesma
    sequência de rotação compartilham o family_id (detecção de reuso)."""

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), nullable=False, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(TS, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TS, nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(TS)
    revoked_at: Mapped[datetime | None] = mapped_column(TS)


class Workspace(db.Model):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(60), nullable=False)
    icon: Mapped[str] = mapped_column(sa.String(16), nullable=False, default=DEFAULT_WORKSPACE_ICON)
    owner_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False, default="BRL")
    created_at: Mapped[datetime] = mapped_column(TS, nullable=False, default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(TS)
    deleted_at: Mapped[datetime | None] = mapped_column(TS)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="workspace", order_by="Membership.joined_at")


class Membership(db.Model):
    __tablename__ = "memberships"
    __table_args__ = (sa.UniqueConstraint("workspace_id", "user_id", name="uq_membership_workspace_user"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(RoleEnum, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(TS, nullable=False, default=utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(lazy="joined")


class Invite(db.Model):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(InviteRoleEnum, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TS, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(TS)
    consumed_by: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("users.id"))
    cancelled_at: Mapped[datetime | None] = mapped_column(TS)

    workspace: Mapped[Workspace] = relationship()
    creator: Mapped[User] = relationship(foreign_keys=[created_by])


class Expense(db.Model):
    __tablename__ = "expenses"
    __table_args__ = (
        sa.UniqueConstraint("author_id", "idempotency_key", name="uq_expense_author_idempotency"),
        sa.Index("ix_expenses_workspace_spent", "workspace_id", "spent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("workspaces.id"), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    spent_at: Mapped[date] = mapped_column(sa.Date, nullable=False)
    description: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    category: Mapped[str] = mapped_column(CategoryEnum, nullable=False)
    icon_key: Mapped[str | None] = mapped_column(sa.String(32))
    idempotency_key: Mapped[str | None] = mapped_column(sa.String(128))
    created_at: Mapped[datetime] = mapped_column(TS, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(TS)

    author: Mapped[User] = relationship(lazy="joined")
