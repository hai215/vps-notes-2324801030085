from pathlib import Path

import click
import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


def get_db():
    """Return the request-scoped PostgreSQL connection."""
    if "db" not in g:
        g.db = psycopg.connect(
            current_app.config["DATABASE_URL"], row_factory=dict_row
        )
    return g.db


def close_db(exception=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    schema_path = Path(current_app.root_path).parent / "schema.sql"
    connection = get_db()
    connection.execute(schema_path.read_text(encoding="utf-8"))
    connection.commit()


def init_db_command():
    init_db()
    click.echo("Database schema initialized.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(click.command("init-db")(init_db_command))
