import json
import time
import os
from datetime import datetime, timedelta
from multiprocessing import Process
from urllib.request import urlopen
from typing import Optional
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
from rkiv.dgmap import DiscGroupMap

CONFIG = Config()


@click.version_option(version=__version__)
@click.group()
def rkiv():
    pass


@rkiv.command()
def config():
    """
    Configure rkiv
    """
    click.echo(CONFIG)


@rkiv.command()
def email():
    """
    Send Email
    """
    click.echo("ugh...")


@rkiv.command()
@click.option("-d", "--directory", help="Root directory of the disc group to map.", required=True)
def dgmap(directory: str) -> None:
    """
    Create a dgmap (disc group map) csv if one does not exist in the directory.
    """
    path = Path(directory)
    _csv = path.joinpath("dgmap.csv")

    if _csv.exists():
        click.echo(f"{_csv} alredy exists")
        return None

    click.echo(f"Analyzing discs in {directory}")
    dgmap = DiscGroupMap.from_dir(path)
    dgmap.to_csv(_csv)


@rkiv.command()
def unreleased() -> None:
    """
    Find any unreleased media (Movies and TV) not in the Stream
    """
    from rkiv.inventory import Inventory

    inventory = Inventory.take_inventory()

    click.echo("")
    click.echo(f"Archived Discs:    {len(inventory.video_archive)}")
    click.echo(f"Streaming:         {len(inventory.stream_objects)}")
    click.echo(f"Unreleased TV:     {len(inventory.unreleased_tv)}")
    click.echo(f"Unreleased Movies: {len(inventory.unreleased_movies)}")
    click.secho("\nUnreleased Movies", bold=True)

    for movie in inventory.unreleased_movies:
        click.echo(movie.title)

    click.secho("\nUnreleased TV Shows", bold=True)
    for show in inventory.unreleased_tv:
        click.echo(show.title)


@rkiv.command()
@click.option("-d", "--disc", help="Root of the disc/directory containing archived material")
def analyze(disc: Path) -> None:
    """
    Analyzes an archived directory/disc and prints out information.

    """
    click.echo(disc)


@rkiv.command()
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


@rkiv.command()
@click.option("-d", "--dev", required=True)
def sync():
    """
    syncs media to backup location
    """

    click.secho("Begin media sync to howard")


@rkiv.command()
def audio():
    click.secho("rkiv Audio Ripper\n", bold=True, underline=True)

    active_drives = opticaldevices.get_optical_drives()
    procs = [Process(target=auto_audio_ripper, args=(d,)) for d in active_drives]

    for prc in procs:
        prc.start()

    drive_progress, reset_cursor = audio_rip_dash(active_drives)
    click.echo(drive_progress)

    while True:
        time.sleep(5)
        drive_progress, reset_cursor = audio_rip_dash(active_drives)
        click.echo(reset_cursor)
        click.echo(drive_progress)


@rkiv.command()
@click.option("-d", "--drive", required=False)
def video(drive: str):
    from rkiv.video import AutoVideoRipper
    from rkiv.opticaldevices import get_optical_drives

    auto_video_ripper = AutoVideoRipper(drives=get_optical_drives())
    auto_video_ripper.run()


@rkiv.command()
def inventory() -> None:
    """inventory"""
    click.echo(
        "Stats summary (archive and stream): number of discs in archive, number of movies, number of shows, size"
    )
    click.echo("list of unreleased movies and tv shows by season")
    pass
    # stat


@rkiv.group()
def itunes() -> None:
    """
    itunes related commands
    """
    pass


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


@itunes.command()
def cache() -> None:
    """Caches cover art"""
    _itunes.ITunesLibraryDataFrame.cache_album_art()


@rkiv.command()
@click.option("-c", "--collection", required=True, is_flag=False, help="Directory containing the movies to release")
@click.option("-n", "--number", required=False, default=-1, help="Number of movies to select for release.")
@click.option("-e", "--exclude", required=False, default=None, help="Patterns to ignore, comma delimited")
def release(collection: str, number: int, exclude: Optional[str]) -> None:
    """
    releases movies
    """

    def touchless(file: Path, touch_time: datetime = datetime.now()) -> None:
        # Example of input string for unix time stamp, always local
        # 201512180130.09 yyyymmddhhMM.ss

        unix_time = touch_time.astimezone().strftime("%Y%m%d%H%M.%S")
        _file = str(file)

        cmd = ["touch", "-m", "-t", unix_time, _file]
        proc_out = subprocess.run(cmd, capture_output=True, text=True)
        return proc_out.returncode

    unreleased = Path(collection)
    movies = [Path(r).joinpath(ff) for r, _, f in os.walk(unreleased) for ff in f]

    if exclude:
        ex = exclude.split(",")
        movies = [m for m in movies if not any(x in m.stem for x in ex)]

    if number >= 0:
        import random

        random.shuffle(movies)
        movies = movies[:number]

    touch_time = datetime.now()
    for movie in movies:
        new_path = str(movie.parent).replace(str(unreleased), str(CONFIG.video_streams[0]))
        _ = touchless(movie, touch_time)
        _ = touchless(movie.parent, touch_time)
        click.echo(f"[{click.style('*', fg='green')}] {movie.parent} -> {new_path}")
        movie.parent.rename(new_path)


@rkiv.command()
@click.option("-c", "--collection", is_flag=False, default=None, help="Exctract archived discs found here")
@click.option("-o", "--output", is_flag=False, default=None, help="Store .mkv files here")
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

    movies = [i for i in walk_ark if i.category == MediaCategory.MOVIE and "_D01" in i.path.stem]
    for disc in movies:
        print(f"{disc.title} - {disc.path.parent.stem} - {disc.path}")
        title = MakeMKV.get_main_title(disc)
        print(f"  Title: {title.id} Chapters: {title.chapters} Length: {title.length} Aspect: {title.aspect_ratio}")
        extract_mkv(disc, Path(output), title.id)


@rkiv.command()
@click.option("-c", "--collection", is_flag=False, default=None, help="Directory containing video files")
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

        log_lines = [i for i in log.splitlines() if all([fp not in i for fp in false_positives])]
        error_list = [i for i in log_lines if "fail" in i.lower() or "error" in i.lower()]
        if len(error_list) > 0:
            for e in error_list:
                print(e)
            with open(dump_name, "w") as f:
                f.write(log)

    def handbrake_encode(input: Path, output: Path) -> None:
        handbrake_preset = str(CONFIG.data_directory().joinpath("h265AutoRipMedMkv.json"))
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
        Path(p).joinpath(ff) for p, _, f in os.walk(_collection) for ff in f if Path(ff).suffix in video_extensions
    ]

    total = len(in_files)
    for idx, file in enumerate(in_files):
        out_file = Path(str(file).replace(str(_collection), str(_output)))
        out_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"({idx + 1}/{total}) {file} -> {out_file}")
        handbrake_encode(input=file, output=out_file)


@rkiv.command()
def makemkv():
    """flacify"""
    from rkiv.makemkv import MakeMKVBetaKeyParser

    parser = MakeMKVBetaKeyParser()
    click.echo(parser.scrape_reg_key())
    click.echo(f"Reg Exit Code: {parser.set_reg_key()}")


@rkiv.command()
@click.option("-l", "--last", required=False)
def latest(last: int = 90):
    """
    Creates a "Recently Added" playlist in the mpd playlist folder. It will replace
    any existing playlist with the same name.
    """
    pass


@rkiv.command()
@click.option("-d", "--days", required=False, type=int)
@click.option(
    "-s",
    "--save-date",
    is_flag=True,
    default=False,
    help="Replace last date and time run with now",
)
@click.option(
    "-g",
    "--greet",
    is_flag=True,
    default=False,
    help="Add personalized greeting to the start of the newsletter",
)
def freshjelly(days: Optional[int], save_date: bool, greet: bool):
    """
    freshjelly

    Creates an html file with the latest media. Can optionally specify number of days to go back. If days are not
    specified, the script will look for last date ran. If the last date doesnt exist, the script will default to 7 days.
    """
    from rkiv.finletter import FinLetter

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

    with open("freshjelly.html", "w") as f:
        f.write(FinLetter.fresh_jelly(start_time=start, end_time=end, greet=greet))


@rkiv.command()
@click.option("-s", "--scrape", is_flag=True, default=False, help="Update collection info")
def collector(scrape: bool) -> None:
    """
    gathers and manages movie collectoions including Ebert's favorites,
    Dinner and a Movie, and The Rewatchables
    """
    click.secho("The Collector")

    from rkiv.collector import TheRewatchables, JellyfinCollection

    rewatchables = TheRewatchables.scrape()
    collection_df = rewatchables.match_jellyfin_library()

    rewatch = JellyfinCollection.load_by_name(rewatchables.collection_name, rewatchables.defualt_collection())

    new_additions = rewatch.update(collection_df)
    rewatch.save()

    num = click.style(str(len(new_additions)), fg="green")
    click.echo(f"Added {num} new matches")
    click.echo(collection_df.table_summary())


@rkiv.command()
@click.option("-p", "--pattern")
def jellytag(pattern: Optional[str] = None) -> None:
    """
    Perform actions using jellyfins tags. Only lists tags that match a pattern.
    """
    click.secho("Build Tagged Collection")

    from rkiv.collector import (
        TaggedCollection,
        JellyfinCollection,
        JellyfinCollectionItem,
    )
    from rkiv.jellyfinproxy import JellyfinProxy

    patterns = set()
    if pattern is not None:
        patterns = set(pattern.split(","))

    tags = TaggedCollection.pattern_matched_tags(patterns)
    click.secho(f"Patterns:      {patterns}")
    click.secho(f"Matching Tags: {tags}")

    movies = JellyfinProxy.get_movies()
    matches = [m for m in movies if len(tags.intersection(m.Tags)) > 0]

    for tag in tags:
        tagged = [m for m in matches if tag in m.Tags]
        click.secho(f"{tag}:")
        for t in tagged:
            click.secho(f"  * {t.Name}")

    christmas_collection = JellyfinCollection.load_by_name("Christmas")
    paths = [cc.path for cc in christmas_collection.collection_items]
    additions = [JellyfinCollectionItem(m.Path) for m in matches if m.Path not in paths]

    click.secho(f"Adding {len(additions)} to christmas collection")
    christmas_collection.collection_items += additions
    click.secho(f"Collection now has {len(christmas_collection.collection_items)} items")
    christmas_collection.save()
