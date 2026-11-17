import logging
import time

from flask import Flask, g, request
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .errors import register_error_handlers
from .extensions import db, limiter, migrate

API_PREFIX = "/api/v1"
MIN_SECRET_LENGTH = 32


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config())
    if overrides:
        app.config.update(overrides)
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    if not app.config["TESTING"] and len(app.config["SECRET_KEY"] or "") < MIN_SECRET_LENGTH:
        raise RuntimeError(f"SECRET_KEY precisa ter pelo menos {MIN_SECRET_LENGTH} caracteres.")

    if app.config["TRUST_PROXY"]:
        # Atrás do Caddy: usa o IP real do cliente (X-Forwarded-For) no rate limit.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True, compare_type=True)
    limiter.init_app(app)
    register_error_handlers(app)

    from .cli import register_cli

    register_cli(app)

    from . import models  # noqa: F401  (registra as tabelas no metadata)
    from .blueprints import auth, expenses, invites, workspaces

    app.register_blueprint(auth.bp, url_prefix=API_PREFIX)
    app.register_blueprint(workspaces.bp, url_prefix=API_PREFIX)
    app.register_blueprint(invites.bp, url_prefix=API_PREFIX)
    app.register_blueprint(expenses.bp, url_prefix=API_PREFIX)
    app.register_blueprint(invites.html_bp)
    app.add_url_rule("/health", "health", auth.health)

    access_log = logging.getLogger("duocash.access")

    @app.before_request
    def _start_timer():
        g.request_started = time.perf_counter()

    @app.after_request
    def security_headers(response):
        # Loga o molde da rota (ex.: /api/v1/invites/<token>/accept), nunca o caminho real,
        # para tokens de convite e filtros de busca não irem parar nos logs.
        route = request.url_rule.rule if request.url_rule else "<sem rota>"
        elapsed = (time.perf_counter() - g.get("request_started", time.perf_counter())) * 1000
        access_log.info("%s %s %s %.0fms", request.method, route, response.status_code, elapsed)

        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if response.mimetype == "application/json":
            headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            headers.setdefault("Cache-Control", "no-store")
        return response

    return app
