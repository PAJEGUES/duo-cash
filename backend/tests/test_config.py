"""Leitura da configuração a partir do ambiente (Render + Neon)."""

import pytest

from app.config import Config

NEON_URL = "postgresql://user:pw@ep-x.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in ("PUBLIC_BASE_URL", "RENDER_EXTERNAL_URL", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)


def test_public_base_url_uses_render_external_url(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://duocash-api.onrender.com/")
    assert Config().PUBLIC_BASE_URL == "https://duocash-api.onrender.com"


def test_explicit_public_base_url_wins_over_render(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://duocash-api.onrender.com")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://duocash.example.com")
    assert Config().PUBLIC_BASE_URL == "https://duocash.example.com"


def test_public_base_url_default_is_localhost():
    assert Config().PUBLIC_BASE_URL == "http://localhost:8000"


def test_neon_url_uses_psycopg3_and_keeps_ssl_params(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", NEON_URL)
    url = Config().SQLALCHEMY_DATABASE_URI
    assert url.startswith("postgresql+psycopg://")
    assert url.endswith("?sslmode=require&channel_binding=require")
