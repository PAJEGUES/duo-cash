import logging

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)

_HTTP_DEFAULTS = {
    400: ("bad_request", "Requisição inválida."),
    401: ("unauthorized", "Autenticação necessária."),
    403: ("forbidden", "Você não tem permissão para esta ação."),
    404: ("not_found", "Recurso não encontrado."),
    405: ("method_not_allowed", "Método não permitido."),
    409: ("conflict", "Conflito com o estado atual."),
    413: ("payload_too_large", "Requisição grande demais."),
    415: ("unsupported_media_type", "Envie os dados em JSON."),
    429: ("rate_limited", "Muitas requisições. Tente novamente em instantes."),
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields


def validation_error(fields: dict[str, str], message: str = "Dados inválidos.") -> ApiError:
    return ApiError(400, "validation_error", message, fields)


def not_found(message: str = "Recurso não encontrado.") -> ApiError:
    return ApiError(404, "not_found", message)


def forbidden(message: str = "Você não tem permissão para esta ação.") -> ApiError:
    return ApiError(403, "forbidden", message)


def error_response(status: int, code: str, message: str, fields: dict | None = None):
    body = {"error": {"code": code, "message": message}}
    if fields:
        body["error"]["fields"] = fields
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _api_error(err: ApiError):
        return error_response(err.status, err.code, err.message, err.fields)

    @app.errorhandler(HTTPException)
    def _http_error(err: HTTPException):
        status = err.code or 500
        code, message = _HTTP_DEFAULTS.get(status, ("error", "Erro na requisição."))
        return error_response(status, code, message)

    @app.errorhandler(Exception)
    def _unexpected(err: Exception):
        log.exception("Erro inesperado")
        return error_response(500, "internal_error", "Erro interno. Tente novamente mais tarde.")
