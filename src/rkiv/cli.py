import json
import time
from datetime import datetime, timedelta
from multiprocessing import Process
from urllib.request import urlopen
from typing import Optional
import os
import subprocess

from pydvdid import compute  # type: ignore
import click
from pathlib import Path

from rkiv import __version__
from rkiv.config import Config
from rkiv.audio import auto_audio_ripper, audio_rip_dash
from rkiv import opticaldevices
from rkiv.inventory import ArchivedDisc, MediaCategory
from rkiv.makemkv import MakeMKV, extract_mkv
from rkiv import itunes as _itunes

CONFIG = Config()


@click.version_option(version=__version__)
@click.group()
def cli():
    pass

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
@click.option("-d", "--drive", required=False)
def video(drive: str):
    from rkiv.video import AutoVideoRipper
    from rkiv.opticaldevices import get_optical_drives

    auto_video_ripper = AutoVideoRipper(drives=get_optical_drives())
    auto_video_ripper.run()


@cli.command()
def inventory() -> None:
    """inventory"""

    pass
    # stat

@cli.command()
def itunes() -> None:
    """
    exports itunes playlists
    """
    itdf = _itunes.ITunesLibraryDataFrame.from_itunes_xml()
    itdf.export_playlists()

@cli.command()
@click.option(
    "-c",
    "--collection",
    is_flag=False,
    default=None,
    help="Exctract archived discs found here",
)
@click.option(
    "-o", "--output", is_flag=False, default=None, help="Store .mkv files here"
)
def extract(collection: str, output: str):
    """
    Extracts mkv files from disc media. Defaults to searching for main feature.
    Checks consensus between handbrake and longest title
    """

    # TODO walk_sl can be used to filter
    # walk_sl = StreamObject.walk_stream_library(
    #     root_path=CONFIG.video_streams[0]
    # ) + StreamObject.walk_stream_library(root_path=CONFIG.video_streams[1])
    walk_ark = ArchivedDisc.walk_disc_archive(Path(collection))

    # stream_matches = {i.match_name for i in walk_sl}
    # unextracted = [i for i in walk_ark if i.path.parent.stem not in stream_matches]

    movies = [
        i
        for i in walk_ark
        if i.category == MediaCategory.MOVIE and "_D01" in i.path.stem
    ]
    for disc in movies:
        print(f"{disc.title} - {disc.path.parent.stem} - {disc.path}")
        title = MakeMKV.get_main_title(disc)
        print(
            f"  Title: {title.id} Chapters: {title.chapters} Length: {title.length} Aspect: {title.aspect_ratio}"
        )
        extract_mkv(disc, Path(output), title.id)


@cli.command()
@click.option(
    "-c",
    "--collection",
    is_flag=False,
    default=None,
    help="Directory containing video files",
)
@click.option("-o", "--output", is_flag=False, help="Output directory")
def h265(collection: str, output: str):
    """
    Mirrors the collectoion directory with h265 encoded files
    """

    def process_hadbrake_log(log: str, dump_name: str) -> None:
        false_positives = [
            "disc.c:333: failed opening UDF image",
            "disc.c:437: error opening file BDMV/index.bdmv",
            "disc.c:437: error opening file BDMV/BACKUP/index.bdmv",
            "libdvdread: DVDOpenFileUDF:UDFFindFile /VIDEO_TS/VIDEO_TS.IFO failed",
            "libdvdnav: vm: vm: failed to read VIDEO_TS.IFO",
            "0 decoder errors",
            "ECMA 167 Volume Recognition failed",
        ]

        log_lines = [
            i for i in log.splitlines() if all([fp not in i for fp in false_positives])
        ]
        error_list = [
            i for i in log_lines if "fail" in i.lower() or "error" in i.lower()
        ]
        if len(error_list) > 0:
            for e in error_list:
                print(e)
            with open(dump_name, "w") as f:
                f.write(log)

    def handbrake_encode(input: Path, output: Path) -> None:
        handbrake_preset = str(
            CONFIG.data_directory().joinpath("h265AutoRipMedMkv.json")
        )
        _cmd = [
            "HandBrakeCLI",
            "--main-feature",
            "--preset-import-file",
            handbrake_preset,
            "-Z",
            "h265AutoRipMedMkv",
            "-i",
            str(input),
            "-o",
            str(output),
        ]
        proc = subprocess.run(args=_cmd, text=True, stderr=subprocess.PIPE)
        process_hadbrake_log(proc.stderr, output.with_suffix(".err.log").stem)

    _collection = Path(collection)
    _output = Path(output)

    video_extensions = {".m4v", ".mkv", ".mp4"}

    # Gather
    in_files = [
        Path(p).joinpath(ff)
        for p, _, f in os.walk(_collection)
        for ff in f
        if Path(ff).suffix in video_extensions
    ]

    total = len(in_files)
    for idx, file in enumerate(in_files):
        out_file = Path(str(file).replace(str(_collection), str(_output)))
        out_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"({idx + 1}/{total}) {file} -> {out_file}")
        handbrake_encode(input=file, output=out_file)


@cli.command()
def makemkv():
    """flacify"""
    from rkiv.makemkv import MakeMKVBetaKeyParser

    parser = MakeMKVBetaKeyParser()
    click.echo(parser.scrape_reg_key())


@cli.command()
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
