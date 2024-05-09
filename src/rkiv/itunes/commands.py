from typing import Optional

from rkiv import itunes
import click


@click.command()
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
    itunes.ITunesLibraryDataFrame.compare(modified=_modified)


@click.command()
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
    itunes.ITunesLibraryDataFrame.update(_modified)


@click.command()
def repair() -> None:
    """Attempts to repair missing and extra files"""
    itunes.ITunesLibraryDataFrame.repair()


@click.command()
def cache() -> None:
    """Caches cover art"""
    itunes.ITunesLibraryDataFrame.cache_album_art()
