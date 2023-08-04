import json
import time
from multiprocessing import Process
from urllib.request import urlopen

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
def inventory():
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
@click.option("-l", "--last", required=False)
def freshjelly():
    """freshjelly"""
    from rkiv.freshjelly import jellyfresh

    jellyfresh()
