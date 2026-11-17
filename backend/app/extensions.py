from flask_limiter import Limiter
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


db = SQLAlchemy(model_class=Base)
migrate = Migrate()


def _rate_limit_key() -> str:
    from .security import rate_limit_key  # import tardio: security depende de extensions

    return rate_limit_key()


# Armazenamento em memória: o limite vale por processo do gunicorn (ver README).
DEFAULT_LIMIT = "300/minute"
WRITE_LIMIT = "60/minute"
limiter = Limiter(key_func=_rate_limit_key, default_limits=[DEFAULT_LIMIT])
