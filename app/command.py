import typer
from app.database import engine
from app import models, crud, database

cli = typer.Typer()


@cli.command()
def create_db():
    """Create the database from scratch

    For development with sqlite only.
    Use alembic in production.
    """
    typer.echo("Create database...")
    models.Base.metadata.create_all(bind=engine)


@cli.command()
def delete_notifications(days: int = typer.Option(30, help="Number of days to keep")):
    """Delete notifications older than X days"""
    typer.echo(f"Delete notifications older than {days} days...")
    db = database.SessionLocal()
    crud.delete_notifications(db, days)
    db.close()


if __name__ == "__main__":
    cli()
