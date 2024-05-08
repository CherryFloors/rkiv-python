from typing import Optional

from rkiv import itunes as _itunes
from rkiv.cli import itunes
import click


@itunes.command()
@click.option(
    "-m",
    "--modified",
    is_flag=False,
    default=None,
    help="Over ride modified algorithm by passing list of albums",
)
def compare(modified: Optional[str]) -> None:
    _modified = None
    if modified is not None:
        _modified = modified.split(",")
    _itunes.ITunesLibraryDataFrame.compare(modified=_modified)


@itunes.command()
@click.option(
    "-m",
    "--modified",
    is_flag=False,
    default=None,
    help="Over ride modified algorithm by passing list of albums",
)
def update(modified: Optional[str]) -> None:
    """Updates the music stream based on the iTunes XML"""
    _modified = None
    if modified is not None:
        _modified = modified.split(",")
    _itunes.ITunesLibraryDataFrame.update(_modified)


@itunes.command()
def repair() -> None:
    """Attempts to repair missing and extra files"""
    _itunes.ITunesLibraryDataFrame.repair()
