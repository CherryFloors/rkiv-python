import click.testing
import pytest


@pytest.fixture
def runner():
    return click.testing.CliRunner()
