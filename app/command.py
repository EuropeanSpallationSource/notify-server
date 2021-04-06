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


@cli.command()
def delete_user(username: str = typer.Argument(..., help="The user to delete")):
    """Delete the user USERNAME"""
    db = database.SessionLocal()
    user = crud.get_user_by_username(db, username)
    if user is None:
        typer.secho(f"User '{username}' not found. Aborting.", fg=typer.colors.RED)
    else:
        crud.delete_user(db, user)
        typer.secho(f"User '{username}' deleted", fg=typer.colors.GREEN)
    db.close()


if __name__ == "__main__":
    cli()
