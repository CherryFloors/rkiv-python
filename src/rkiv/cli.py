import json
import time
from datetime import datetime, timedelta
from multiprocessing import Process
from urllib.request import urlopen
from typing import Optional

from pydvdid import compute  # type: ignore
import click

from rkiv import __version__
from rkiv.config import Config
from rkiv.audio import auto_audio_ripper, audio_rip_dash
from rkiv import opticaldevices

CONFIG = Config()


@click.version_option(version=__version__)
@click.group()
def cli():
    pass


@cli.command()
def config():
    """
    Configure rkiv
    """
    print(CONFIG)


@cli.command()
@click.option("-d", "--dev", required=True)
def arm(dev):
    """arm"""

    # get_disc_type
    # get_disc_info
    # get_disc_title

    click.secho("Automatic Ripping Machine", fg="green")
    click.echo(f"Searching for match to {dev}")
    crc64 = compute(dev)
    click.echo(f"CRC64: {crc64}")
    urlstring = f"https://1337server.pythonanywhere.com/api/v1/?mode=s&crc64={crc64}"
    dvd_xml = urlopen(urlstring).read()
    print(json.dumps(json.loads(dvd_xml), indent=4))


@cli.command()
def audio():
    click.secho("rkiv Audio Ripper", fg="green")

    ActiveDriveList = opticaldevices.get_optical_drives()
    ProcList = [Process(target=auto_audio_ripper, args=(d,)) for d in ActiveDriveList]

    for prc in ProcList:
        prc.start()

    DriveProgress, ResetCursor = audio_rip_dash(ActiveDriveList)
    click.echo(DriveProgress)

    while True:
        time.sleep(5)
        DriveProgress, ResetCursor = audio_rip_dash(ActiveDriveList)
        click.echo(ResetCursor)
        click.echo(DriveProgress)


@cli.command()
def visual():
    pass


@cli.command()
def inventory() -> None:
    """inventory"""
    pass
    # stat


@cli.command()
def flacify():
    """flacify"""
    pass


@cli.command
@click.option("-l", "--last", required=False)
def latest(last: int = 90):
    """
    Creates a "Recently Added" playlist in the mpd playlist folder. It will replace
    any existing playlist with the same name.
    """
    pass


@cli.command()
@click.option("-d", "--days", required=False, type=int)
@click.option(
    "-s",
    "--save-date",
    is_flag=True,
    default=False,
    help="Replace last date and time run with now",
)
def freshjelly(days: Optional[int], save_date: bool):
    """
    freshjelly

    Creates an html file with the latest media. Can optionally specify number of days to go back. If days are not
    specified, the script will look for last date ran. If the last date doesnt exist, the script will default to 7 days.
    """
    from rkiv.finletter import FreshJelly

    # Sensible defaults
    end = datetime.utcnow()
    start = end - timedelta(days=7)

    # Override default with cache if it exists
    last_ran_cache = CONFIG.data_directory().joinpath("freshjelly.last")
    if last_ran_cache.exists():
        with open(last_ran_cache, "r") as f:
            cache = json.load(f)
        start = datetime.fromisoformat(cache["last_ran"])

    # Cache time
    if save_date:
        with open(last_ran_cache, "w") as f:
            f.write(json.dumps(obj={"last_ran": datetime.isoformat(end)}))

    # Replace start with user supplied amount of days
    if days is not None:
        start = end - timedelta(days=days)

    click.echo(FreshJelly.fresh_jelly(start_time=start, end_time=end))


@cli.command()
@click.option(
    "-s", "--scrape", is_flag=True, default=False, help="Update collection info"
)
def collector(scrape: bool) -> None:
    """
    gathers and manages movie collectoions including Ebert's favorites,
    Dinner and a Movie, and The Rewatchables
    """
    click.secho("collector")

    if scrape:
        click.secho("You have picked scrape")
