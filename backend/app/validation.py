import re
import uuid
from datetime import date, timedelta

from flask import request

from .constants import CATEGORIES, ICON_KEYS, MAX_AMOUNT_CENTS, MAX_DESCRIPTION, MAX_ICON
from .errors import ApiError, validation_error
from .timeutil import today

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")
MIN_DATE = date(2000, 1, 1)
MAX_FUTURE_DAYS = 31
MIN_YEAR, MAX_YEAR = 2000, 9998  # evita estourar date() ao calcular meses vizinhos
MAX_OFFSET = 1_000_000

_MISSING = object()


def json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "O corpo da requisição deve ser um objeto JSON válido.")
    return data


class Fields:
    """Acumula erros por campo e lança tudo de uma vez."""

    def __init__(self) -> None:
        self.errors: dict[str, str] = {}

    def add(self, field: str, message: str) -> None:
        self.errors.setdefault(field, message)

    def raise_if_any(self) -> None:
        if self.errors:
            raise validation_error(self.errors)


# --- validadores de campo: devolvem (valor, mensagem_de_erro) ---------------


def check_amount(value):
    if type(value) is not int:  # rejeita bool, float e strings
        return None, "Informe o valor em centavos (número inteiro)."
    if value <= 0:
        return None, "O valor deve ser maior que zero."
    if value > MAX_AMOUNT_CENTS:
        return None, "Valor acima do limite permitido."
    return value, None


def parse_iso_date(value) -> date | None:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def check_spent_at(value):
    parsed = parse_iso_date(value)
    if parsed is None:
        return None, "Data inválida. Use o formato AAAA-MM-DD."
    if parsed < MIN_DATE:
        return None, "A data deve ser a partir de 01/01/2000."
    if parsed > today() + timedelta(days=MAX_FUTURE_DAYS):
        return None, "A data não pode ser tão distante no futuro."
    return parsed, None


def check_description(value):
    if not isinstance(value, str):
        return None, "Informe a descrição."
    value = value.strip()
    if not value:
        return None, "Informe a descrição."
    if len(value) > MAX_DESCRIPTION:
        return None, f"A descrição deve ter no máximo {MAX_DESCRIPTION} caracteres."
    return value, None


def check_category(value):
    if value not in CATEGORIES:
        return None, "Categoria inválida."
    return value, None


def check_icon_key(value):
    if value is None:
        return None, None
    if value not in ICON_KEYS:
        return None, "Ícone inválido."
    return value, None


def check_name(value, max_len: int):
    if not isinstance(value, str) or not value.strip():
        return None, "Informe o nome."
    value = value.strip()
    if len(value) > max_len:
        return None, f"O nome deve ter no máximo {max_len} caracteres."
    return value, None


def check_icon(value):
    if not isinstance(value, str) or not value.strip():
        return None, "Ícone inválido."
    value = value.strip()
    if len(value) > MAX_ICON:
        return None, "Ícone inválido."
    return value, None


def validate(data: dict, spec: dict, *, partial: bool = False) -> dict:
    """spec: {campo: (validador, obrigatório)}. Devolve só os campos presentes."""
    errors = Fields()
    out = {}
    for field, (checker, required) in spec.items():
        raw = data.get(field, _MISSING)
        if raw is _MISSING:
            if required and not partial:
                errors.add(field, "Campo obrigatório.")
            continue
        value, message = checker(raw)
        if message:
            errors.add(field, message)
        else:
            out[field] = value
    errors.raise_if_any()
    return out


# --- query string ---------------------------------------------------------


def parse_month_arg(name: str = "month") -> tuple[int, int]:
    raw = request.args.get(name)
    if raw is None or raw == "":
        t = today()
        return t.year, t.month
    match = _MONTH_RE.match(raw)
    if not match or not (1 <= int(match.group(2)) <= 12) or not (MIN_YEAR <= int(match.group(1)) <= MAX_YEAR):
        raise validation_error({name: "Mês inválido. Use o formato AAAA-MM."})
    return int(match.group(1)), int(match.group(2))


def parse_int_arg(name: str, default=None, *, minimum: int | None = None, maximum: int | None = None):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise validation_error({name: "Número inválido."}) from None
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise validation_error({name: "Valor fora do intervalo permitido."})
    return value


def parse_date_arg(name: str) -> date | None:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    parsed = parse_iso_date(raw)
    if parsed is None:
        raise validation_error({name: "Data inválida. Use o formato AAAA-MM-DD."})
    return parsed


def parse_uuid_arg(name: str) -> uuid.UUID | None:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise validation_error({name: "Identificador inválido."}) from None


def parse_bool_arg(name: str) -> bool:
    return (request.args.get(name) or "").lower() in {"1", "true", "yes"}
