import logging

import sqlalchemy as sa
from flask import Blueprint, current_app, g, jsonify
from sqlalchemy.exc import IntegrityError

from .. import security
from ..audit import audit
from ..constants import CATEGORIES, ICON_KEYS
from ..errors import ApiError, not_found, validation_error
from ..extensions import db, limiter
from ..models import User
from ..security import auth_required, issue_tokens, revoke_refresh_family, rotate_refresh_token
from ..services import user_json
from ..validation import json_body

GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")

log = logging.getLogger(__name__)
bp = Blueprint("auth", __name__)
REQUIRED = "Campo obrigatório."


@bp.get("/health")
@limiter.exempt
def health():
    return jsonify(status="ok")


@bp.get("/config")
def config():
    cfg = current_app.config
    ids = cfg["GOOGLE_CLIENT_IDS"]
    return jsonify(
        google_web_client_id=ids[0] if ids else None,
        categories=list(CATEGORIES),
        icon_keys=list(ICON_KEYS),
        invite_ttl_minutes=cfg["INVITE_TTL_MINUTES"],
    )


def _upsert_user(sub: str, email: str, display_name: str, avatar_url: str | None) -> User:
    def apply(user: User) -> None:
        user.email = email
        user.display_name = display_name[:120]
        user.avatar_url = avatar_url

    user = db.session.execute(sa.select(User).where(User.google_sub == sub)).scalar_one_or_none()
    if user is None:
        user = User(google_sub=sub)
        apply(user)
        db.session.add(user)
        try:
            db.session.commit()
            return user
        except IntegrityError:  # login simultâneo do mesmo usuário
            db.session.rollback()
            user = db.session.execute(sa.select(User).where(User.google_sub == sub)).scalar_one()
    apply(user)
    db.session.commit()
    return user


def _session_response(user: User, tokens: dict | None = None):
    if tokens is None:  # login: começa uma nova família de refresh tokens
        tokens = issue_tokens(user)
        db.session.commit()
    return jsonify(**tokens, user=user_json(user))


def _refresh_token_from_body() -> str:
    token = json_body().get("refresh_token")
    if not isinstance(token, str) or not token:
        raise validation_error({"refresh_token": REQUIRED})
    return token


@bp.post("/auth/google")
@limiter.limit("20/minute")
def login_google():
    data = json_body()
    token = data.get("id_token")
    if not isinstance(token, str) or not token:
        raise validation_error({"id_token": REQUIRED})
    audiences = current_app.config["GOOGLE_CLIENT_IDS"]
    if not audiences:
        log.error("GOOGLE_CLIENT_IDS não configurado")
        raise ApiError(503, "google_not_configured", "Login com Google indisponível no momento.")
    try:
        claims = security.verify_google_id_token(token, audiences)
    except Exception as exc:  # noqa: BLE001 - qualquer falha de validação vira 401
        audit("login_failed", method="google", reason=type(exc).__name__)
        raise ApiError(401, "unauthorized", "Não foi possível validar o login com o Google.") from None

    sub = claims.get("sub")
    email = claims.get("email")
    reason = None
    if claims.get("iss") not in GOOGLE_ISSUERS:
        reason = "bad_issuer"
    elif claims.get("aud") not in audiences:
        reason = "bad_audience"
    elif not sub or not isinstance(email, str) or "@" not in email:
        reason = "missing_claims"
    elif claims.get("email_verified") not in (True, "true"):
        reason = "email_not_verified"
    if reason:
        audit("login_failed", method="google", reason=reason)
        raise ApiError(401, "unauthorized", "Não foi possível validar o login com o Google.")
    name = (claims.get("name") or email.split("@")[0]).strip() or "Usuário"
    user = _upsert_user(str(sub), email, name, claims.get("picture"))
    audit("login_success", method="google", user_id=user.id)
    return _session_response(user)


@bp.post("/auth/dev")
@limiter.limit("20/minute")
def login_dev():
    if not current_app.config["DEV_LOGIN_ENABLED"]:
        raise not_found()
    data = json_body()
    email = data.get("email")
    name = data.get("display_name")
    errors = {}
    if not isinstance(email, str) or "@" not in email or len(email) > 320:
        errors["email"] = "E-mail inválido."
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        errors["display_name"] = "Informe o nome."
    if errors:
        raise validation_error(errors)
    email = email.strip().lower()
    user = _upsert_user(f"dev:{email}", email, name.strip(), None)
    audit("login_success", method="dev", user_id=user.id)
    return _session_response(user)


@bp.post("/auth/refresh")
@limiter.limit("60/minute")
def refresh():
    token = _refresh_token_from_body()
    # Qualquer falha devolve "unauthorized" (nunca token_expired) para o app não tentar
    # renovar em loop: ele deve mandar o usuário entrar de novo.
    try:
        user, tokens = rotate_refresh_token(token)
    except ApiError:
        audit("refresh_failed")
        raise
    return _session_response(user, tokens)


@bp.post("/auth/logout")
@limiter.limit("60/minute")
def logout():
    revoke_refresh_family(_refresh_token_from_body())
    return "", 204


@bp.get("/me")
@auth_required
def me():
    return jsonify(user_json(g.user))
