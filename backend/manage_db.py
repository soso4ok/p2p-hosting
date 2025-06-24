import asyncio
import os
import sys
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config

app_dir = Path(__file__).resolve().parent / "app"
sys.path.insert(0, str(app_dir))

from app.db.database_connection import create_tables, drop_tables

app = typer.Typer(help="Manage database")

SCRIPT_DIR = Path(__file__).parent
ALEMBIC_DIR = SCRIPT_DIR / "app" / "alembic.ini"


def get_alembic_config() -> Config:
    if not ALEMBIC_DIR.exists():
        typer.echo(
            f"Error: Alembic configuration file not found at {ALEMBIC_DIR}", err=True
        )
        raise typer.Exit(code=1)

    alembic_cfg = Config(str(ALEMBIC_DIR))

    database_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/p2p_db"
    )
    if not database_url:
        typer.echo("Error: DATABASE_URL environment variable is not set.", err=True)
        raise typer.Exit(code=1)

    return alembic_cfg


@app.command()
def init() -> None:
    typer.echo("Creating all database tables...")

    async def _init():
        await create_tables()
        typer.echo("✓ Database tables created successfully!")

    asyncio.run(_init())


@app.command()
def drop() -> None:
    if not typer.confirm("Are you sure you want to drop all tables?"):
        typer.echo("Operation cancelled.")
        return

    typer.echo("Dropping all database tables...")

    async def _drop():
        await drop_tables()
        typer.echo("✓ Database tables dropped successfully!")

    asyncio.run(_drop())


@app.command()
def migrate(message: str = typer.Argument(..., help="Migration message")) -> None:
    """Create a new migration."""
    typer.echo(f"Creating migration: {message}")

    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)

    typer.echo("✓ Migration created successfully!")


@app.command()
def upgrade(revision: str = typer.Argument("head", help="Target revision")) -> None:
    """Upgrade database to a revision."""
    typer.echo(f"Upgrading database to revision: {revision}")

    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)

    typer.echo("✓ Database upgraded successfully!")


@app.command()
def downgrade(revision: str = typer.Argument("-1", help="Target revision")) -> None:
    """Downgrade database to a revision."""
    if not typer.confirm(f"Are you sure you want to downgrade to {revision}?"):
        typer.echo("Operation cancelled.")
        return

    typer.echo(f"Downgrading database to revision: {revision}")

    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)

    typer.echo("✓ Database downgraded successfully!")


@app.command()
def current() -> None:
    """Show current database revision."""
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg, verbose=True)


@app.command()
def history() -> None:
    """Show migration history."""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg, verbose=True)


@app.command()
def reset() -> None:
    """Reset database (drop and recreate all tables)."""
    if not typer.confirm("Are you sure you want to reset the database?"):
        typer.echo("Operation cancelled.")
        return

    async def _reset():
        typer.echo("Dropping all tables...")
        await drop_tables()

        typer.echo("Creating all tables...")
        await create_tables()

        typer.echo("✓ Database reset successfully!")

    asyncio.run(_reset())


if __name__ == "__main__":
    app()
