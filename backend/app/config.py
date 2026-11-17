import os


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///duocash.db")
    # Aceita URLs "postgres://" / "postgresql://" e usa o driver psycopg 3.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Config:
    def __init__(self) -> None:
        self.SQLALCHEMY_DATABASE_URI = _database_url()
        self.SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "hide_parameters": True}
        self.SECRET_KEY = os.environ.get("SECRET_KEY", "")
        self.GOOGLE_CLIENT_IDS = [c.strip() for c in os.environ.get("GOOGLE_CLIENT_IDS", "").split(",") if c.strip()]
        self.PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
        self.INVITE_TTL_MINUTES = int(os.environ.get("INVITE_TTL_MINUTES", "60"))
        self.DEV_LOGIN_ENABLED = _bool(os.environ.get("DEV_LOGIN_ENABLED"))
        self.ACCESS_TTL_MINUTES = int(os.environ.get("ACCESS_TTL_MINUTES", "15"))
        self.REFRESH_TTL_DAYS = int(os.environ.get("REFRESH_TTL_DAYS", "30"))
        self.APP_TIMEZONE = "America/Sao_Paulo"
        self.RATELIMIT_STORAGE_URI = "memory://"
        self.RATELIMIT_ENABLED = not _bool(os.environ.get("RATELIMIT_DISABLED"))
        self.RATELIMIT_HEADERS_ENABLED = True
        self.MAX_CONTENT_LENGTH = 16 * 1024
        self.JWT_ISSUER = "duocash-api"
        self.JWT_AUDIENCE = "duocash-app"
        self.TRUST_PROXY = _bool(os.environ.get("TRUST_PROXY"))
        self.TESTING = False
