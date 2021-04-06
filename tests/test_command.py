from typer.testing import CliRunner
from app.command import cli

runner = CliRunner()


def test_cli():
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "create-db" in result.output
    assert "delete-notifications" in result.output
