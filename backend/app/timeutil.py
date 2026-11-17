from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("America/Sao_Paulo")


def utcnow() -> datetime:
    return datetime.now(UTC)


def today() -> date:
    """Data de hoje no fuso de São Paulo."""
    return datetime.now(APP_TZ).date()


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite devolve datetimes sem fuso; tratamos tudo como UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def iso(value: datetime | None) -> str | None:
    value = as_utc(value)
    return value.isoformat().replace("+00:00", "Z") if value else None


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Primeiro dia do mês e primeiro dia do mês seguinte."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1
