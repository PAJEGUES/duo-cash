import hashlib
import re
import secrets
import threading
import time
import uuid
from datetime import timedelta
from functools import wraps

import jwt
import requests
import sqlalchemy as sa
from flask import current_app, g, request
from flask_limiter.util import get_remote_address

from .audit import audit
from .errors import ApiError
from .extensions import db
from .models import RefreshToken, User
from .timeutil import as_utc, utcnow

ALGORITHM = "HS256"
INVALID = "Token inválido."
SESSION_ENDED = "Sessão encerrada. Entre novamente."
PURGE_ONE_IN = 50  # a cada ~50 logins, apaga refresh tokens vencidos


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _unauthorized(message: str = INVALID) -> ApiError:
    return ApiError(401, "unauthorized", message)


# --- emissão ------------------------------------------------------------------


def _encode(user: User, token_type: str, ttl: timedelta, jti: str) -> str:
    now = utcnow()
    payload = {
        "iss": current_app.config["JWT_ISSUER"],
        "aud": current_app.config["JWT_AUDIENCE"],
        "sub": str(user.id),
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": jti,
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=ALGORITHM)


def issue_tokens(user: User, family_id: uuid.UUID | None = None) -> dict:
    """Gera access + refresh e registra o refresh. Sem family_id = nova sessão (login).
    Quem chama faz o commit."""
    cfg = current_app.config
    refresh_ttl = timedelta(days=cfg["REFRESH_TTL_DAYS"])
    jti = secrets.token_hex(16)
    db.session.add(
        RefreshToken(
            jti=hash_token(jti),
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            expires_at=utcnow() + refresh_ttl,
        )
    )
    if family_id is None and secrets.randbelow(PURGE_ONE_IN) == 0:
        purge_expired_refresh_tokens()
    return {
        "access_token": _encode(user, "access", timedelta(minutes=cfg["ACCESS_TTL_MINUTES"]), uuid.uuid4().hex),
        "refresh_token": _encode(user, "refresh", refresh_ttl, jti),
    }


def purge_expired_refresh_tokens() -> int:
    result = db.session.execute(sa.delete(RefreshToken).where(RefreshToken.expires_at < utcnow()))
    return result.rowcount or 0


# --- validação ------------------------------------------------------------------


def decode_payload(token: str, expected_type: str, *, expired_code: str = "token_expired", verify_exp=True):
    """Valida assinatura e claims do JWT. Devolve (usuário, payload) ou lança ApiError 401."""
    required = ["exp", "iat", "iss", "aud", "sub", "type"]
    if expected_type == "refresh":
        required.append("jti")
    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=[ALGORITHM],  # algoritmo fixo: "none" e RS/ES são recusados
            issuer=current_app.config["JWT_ISSUER"],
            audience=current_app.config["JWT_AUDIENCE"],
            options={"require": required, "verify_exp": verify_exp},
        )
    except jwt.ExpiredSignatureError:
        if expired_code == "token_expired":
            raise ApiError(401, "token_expired", "Sessão expirada. Renove o token.") from None
        raise _unauthorized(SESSION_ENDED) from None
    except jwt.InvalidTokenError:
        raise _unauthorized() from None

    if payload.get("type") != expected_type or not isinstance(payload.get("iat"), int):
        raise _unauthorized()
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except ValueError:
        raise _unauthorized() from None
    user = db.session.get(User, user_id)
    if user is None:
        raise _unauthorized("Usuário não encontrado.")
    revoked = as_utc(user.sessions_revoked_at)
    if revoked is not None and payload["iat"] < int(revoked.timestamp()):
        raise _unauthorized(SESSION_ENDED)
    return user, payload


def decode_token(token: str, expected_type: str, expired_code: str = "token_expired") -> User:
    return decode_payload(token, expected_type, expired_code=expired_code)[0]


def _revoke_family(family_id: uuid.UUID) -> None:
    db.session.execute(
        sa.update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def rotate_refresh_token(token: str) -> tuple[User, dict]:
    """Troca um refresh válido por um novo par (mesma família). Reuso revoga a família."""
    user, payload = decode_payload(token, "refresh", expired_code="unauthorized")
    row = db.session.get(RefreshToken, hash_token(str(payload["jti"])))
    if row is None or row.user_id != user.id or row.revoked_at is not None:
        audit("refresh_failed", user_id=user.id, reason="unknown_or_revoked")
        raise _unauthorized(SESSION_ENDED)
    if as_utc(row.expires_at) <= utcnow():
        audit("refresh_failed", user_id=user.id, reason="expired")
        raise _unauthorized(SESSION_ENDED)

    now = utcnow()
    claimed = db.session.execute(
        sa.update(RefreshToken)
        .where(RefreshToken.jti == row.jti, RefreshToken.used_at.is_(None), RefreshToken.revoked_at.is_(None))
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    ).rowcount
    if claimed != 1:
        # Já usado (ou usado agora por outra requisição): possível roubo. Derruba a sessão inteira.
        db.session.rollback()
        _revoke_family(row.family_id)
        db.session.commit()
        audit("refresh_reuse_detected", user_id=user.id, family_id=row.family_id)
        raise _unauthorized(SESSION_ENDED)

    tokens = issue_tokens(user, family_id=row.family_id)
    db.session.commit()
    audit("refresh_success", user_id=user.id, family_id=row.family_id)
    return user, tokens


def revoke_refresh_family(token: str) -> None:
    """Logout: revoga a família do refresh token. Silencioso para tokens inválidos."""
    try:
        user, payload = decode_payload(token, "refresh", expired_code="unauthorized", verify_exp=False)
    except ApiError:
        return
    row = db.session.get(RefreshToken, hash_token(str(payload["jti"])))
    if row is None or row.user_id != user.id:
        return
    _revoke_family(row.family_id)
    db.session.commit()
    audit("logout", user_id=user.id, family_id=row.family_id)


def revoke_all_sessions(user: User) -> None:
    user.sessions_revoked_at = utcnow()
    db.session.execute(
        sa.update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.session.commit()
    audit("sessions_revoked", user_id=user.id)


def auth_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise ApiError(401, "unauthorized", "Autenticação necessária.")
        g.user = decode_token(token.strip(), "access")
        return view(*args, **kwargs)

    return wrapper


# --- rate limit -----------------------------------------------------------------


def rate_limit_key() -> str:
    """Chave do limite: o usuário (se o access token tiver assinatura válida) ou o IP."""
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        try:
            payload = jwt.decode(
                token.strip(),
                current_app.config["SECRET_KEY"],
                algorithms=[ALGORITHM],
                audience=current_app.config["JWT_AUDIENCE"],
                options={"verify_exp": False},
            )
            return f"user:{payload.get('sub')}"
        except jwt.InvalidTokenError:
            pass
    return f"ip:{get_remote_address()}"


# --- Google -----------------------------------------------------------------------

_MAX_AGE_RE = re.compile(r"max-age=(\d+)")
GOOGLE_HTTP_TIMEOUT = 10
DEFAULT_CERTS_TTL = 3600


class _CachingGoogleRequest:
    """Transporte do google-auth que guarda em memória as respostas GET (os certificados
    públicos do Google) pelo tempo do Cache-Control, com timeout de 10s."""

    def __init__(self) -> None:
        from google.auth.transport import requests as google_requests

        self._inner = google_requests.Request(session=requests.Session())
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, object]] = {}

    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs):
        cacheable = method == "GET" and body is None
        if cacheable:
            with self._lock:
                hit = self._cache.get(url)
                if hit and hit[0] > time.monotonic():
                    return hit[1]
        response = self._inner(
            url, method=method, body=body, headers=headers, timeout=timeout or GOOGLE_HTTP_TIMEOUT, **kwargs
        )
        if cacheable and response.status == 200:
            match = _MAX_AGE_RE.search(response.headers.get("cache-control", "") or "")
            ttl = int(match.group(1)) if match else DEFAULT_CERTS_TTL
            with self._lock:
                self._cache[url] = (time.monotonic() + ttl, response)
        return response


_google_request: _CachingGoogleRequest | None = None
_google_request_lock = threading.Lock()


def google_request() -> _CachingGoogleRequest:
    global _google_request  # transporte único por processo
    with _google_request_lock:
        if _google_request is None:
            _google_request = _CachingGoogleRequest()
        return _google_request


def verify_google_id_token(token: str, audiences: list[str]) -> dict:
    """Valida o id_token do Google. Isolado para os testes poderem substituir."""
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(token, google_request(), audience=audiences)
