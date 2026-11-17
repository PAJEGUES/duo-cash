"""Comandos de manutenção: `flask purge-refresh-tokens` e `flask revoke-sessions <user_id>`."""

import uuid

import click
from flask import Flask

from .extensions import db
from .models import User
from .security import purge_expired_refresh_tokens, revoke_all_sessions


def register_cli(app: Flask) -> None:
    @app.cli.command("purge-refresh-tokens")
    def purge_refresh_tokens():
        """Apaga refresh tokens vencidos."""
        removed = purge_expired_refresh_tokens()
        db.session.commit()
        click.echo(f"{removed} refresh tokens vencidos removidos.")

    @app.cli.command("revoke-sessions")
    @click.argument("user_id")
    def revoke_sessions(user_id):
        """Encerra todas as sessões de um usuário (ex.: celular perdido)."""
        user = db.session.get(User, uuid.UUID(user_id))
        if user is None:
            raise click.ClickException("Usuário não encontrado.")
        revoke_all_sessions(user)
        click.echo("Sessões encerradas.")
