"""A migração inicial cria exatamente o esquema dos modelos."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import downgrade, upgrade

from app.extensions import db

from .conftest import make_app


def test_migrations_match_models(tmp_path):
    app = make_app(SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'm.db'}")
    with app.app_context():
        db.drop_all()  # make_app usa create_all; aqui queremos só as migrações
        upgrade()
        with db.engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), db.metadata)
        assert diff == []
        downgrade(revision="base")
        upgrade()
        db.engine.dispose()
