"""itunes.py"""

import subprocess
import json
import os
import html
import urllib.parse
import pickle
import shutil
from dataclasses import dataclass
from typing import Optional, Union, Iterable, Callable
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from pydantic import BaseModel
import pandas
import click

from rkiv.config import Config


CONFIG = Config()


class unzip:
    """Iterator that unzips an interable int groups of 2"""

    def __init__(self, iterable: Iterable):
        self.iterable = iterable

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i + 1 >= len(self.iterable):
            raise StopIteration
        odd, even = self.iterable[self.i], self.iterable[self.i + 1]
        self.i += 2
        return odd, even


class ITunesXmlConverter:
    """
    iTunes XML converter
    """

    DTYPES: dict[str, Union[type, str]] = {
        "data": str,
        "date": datetime,
        "real": float,
        "integer": "Int64",
        "string": str,
        "true": "boolean",
        "false": "boolean",
    }

    @staticmethod
    def _data(e: ElementTree.Element) -> str:
        return "".join(str(e.text).split())

    @staticmethod
    def _date(e: ElementTree.Element) -> datetime:
        """Parse a date element"""
        # 'Z' not supported in python 3.8, convert to offset
        return datetime.fromisoformat(e.text.replace("Z", "+00:00"))

    @staticmethod
    def _real(e: ElementTree.Element) -> float:
        """Parse a real element"""
        return float(e.text)

    @staticmethod
    def _integer(e: ElementTree.Element) -> int:
        """Parse and int element"""
        return int(e.text)

    @staticmethod
    def _string(e: ElementTree.Element) -> str:
        """Parse a string element"""
        return html.unescape(str(e.text))

    @staticmethod
    def _bool(e: ElementTree.Element) -> bool:
        """Parse a bool element"""
        if e.tag.lower() == "true":
            return True
        return False

    @staticmethod
    def _key(e: ElementTree.Element) -> str:
        """Parse and process key to snake case"""
        return e.text.lower().replace(" ", "_")

    @classmethod
    def _array(cls, e: ElementTree.Element) -> list:
        """Parse an array type element"""
        return [cls.convert_element(i) for i in e.findall("./")]

    @classmethod
    def _dict(cls, e: ElementTree.Element) -> dict:
        """Parse a dict type element"""
        return {cls.convert_element(k): cls.convert_element(v) for k, v in unzip(e.findall("./"))}

    @classmethod
    def get_type(cls, xml_type: str) -> Union[type, str]:
        """Convert iTunes string to python/pandas type"""
        return cls.DTYPES[xml_type]

    @classmethod
    def convert_element(cls, element: ElementTree.Element) -> Union[dict, list, str, float, int, bool, datetime]:
        """Convert iTunes xml value to python/pandas type"""
        LOGIC: dict[str, Callable] = {
            "dict": cls._dict,
            "array": cls._array,
            "key": cls._key,
            "data": cls._data,
            "date": cls._date,
            "real": cls._real,
            "integer": cls._integer,
            "string": cls._string,
            "true": cls._bool,
            "false": cls._bool,
        }
        return LOGIC[element.tag](element)

    @classmethod
    def to_json(cls, it_xml: ElementTree.ElementTree) -> dict:
        """Converts the itunes xml into json"""
        root_element = it_xml.getroot().find("./")
        return cls.convert_element(root_element)

    # Could recursively parse element tree using
    # .findall("./")
    # urllib.parse.unquote(html.unescape("file://localhost/C:/Users/Ryan/Music/iTunes/iTunes%20Media/Music/Black%20Star/Mos%20Def%20&#38;%20Talib%20Kweli%20Are%20Black%20Star/01%20Intro.m4p"))


@dataclass(slots=True)
class StagedTimestamp:
    """
    Holds the timestamps of the staged files

    path: where to stage the file
    timestamp: Timestamp for the file
    dest: Music stream location for the file
    """

    path: Path
    timestamp: datetime
    dest: Path

    @staticmethod
    def _datetime_to_unix(timestamp: datetime) -> str:
        # Example of input string for unix time stamp, always local
        # 201512180130.09 yyyymmddhhMM.ss
        return timestamp.astimezone().strftime("%Y%m%d%H%M.%S")

    def set_timestamp(self) -> int:
        """Sets the timestamp of the file"""

        _time = self._datetime_to_unix(self.timestamp)
        _file = str(self.path)

        cmd = ["touch", "-m", "-t", _time, _file]
        proc_out = subprocess.run(cmd, capture_output=True, text=True)
        return proc_out.returncode


class ITunesSong(BaseModel):
    """
    Song object to store select iTunes song information. The iTunes
    dataframe stores everything in the itunes xml.
    """

    track_id: int
    size: int
    total_time: int
    name: str
    artist: str
    album_artist: str
    album: str
    location: str
    archive_path: Path
    kind: str
    purchased: bool = False
    date_added: datetime
    disc_number: Optional[int] = None
    disc_count: Optional[int] = None
    track_number: Optional[int] = None
    track_count: Optional[int] = None
    date_modified: Optional[datetime] = None
    loved: Optional[bool] = None
    compilation: Optional[bool] = None
    stream_path: Optional[Path] = None

    __annotations__ = {
        "track_id": int,
        "size": int,
        "total_time": int,
        "name": str,
        "artist": str,
        "album_artist": str,
        "album": str,
        "location": str,
        "archive_path": Path,
        "kind": str,
        "purchased": bool,
        "date_added": datetime,
        "disc_number": Optional[int],
        "disc_count": Optional[int],
        "track_number": Optional[int],
        "track_count": Optional[int],
        "date_modified": Optional[datetime],
        "loved": Optional[bool],
        "compilation": Optional[bool],
        "stream_path": Optional[Path],
    }

    @classmethod
    def from_dataframe_row(cls, row: pandas.Series) -> "ITunesSong":
        """Build from a data frame row"""

        _disc_number = None
        if not pandas.isnull(row["disc_number"]):
            _disc_number = row["disc_number"]

        _disc_count = None
        if not pandas.isnull(row["disc_count"]):
            _disc_count = row["disc_count"]

        _track_number = None
        if not pandas.isnull(row["track_number"]):
            _track_number = row["track_number"]

        _track_count = None
        if not pandas.isnull(row["track_count"]):
            _track_count = row["track_count"]

        _date_modified = None
        if not pandas.isnull(row["date_modified"]):
            _date_modified = row["date_modified"].to_pydatetime()

        _loved = False
        if not pandas.isnull(row["loved"]):
            _loved = True

        _compilation = False
        if not pandas.isnull(row["compilation"]):
            _compilation = True

        _purchased = False
        if not pandas.isnull(row["purchased"]):
            _purchased = True

        _stream_path = None
        if not pandas.isnull(row["stream_path"]):
            _stream_path = Path(row["stream_path"])

        return cls(
            track_id=row["track_id"],
            persistent_id=row["persistent_id"],
            size=row["size"],
            total_time=row["total_time"],
            name=row["name"],
            artist=row["artist"],
            album_artist=row["album_artist"],
            album=row["album"],
            location=row["location"],
            archive_path=Path(row["archive_path"]),
            kind=row["kind"],
            purchased=_purchased,
            date_added=row["date_added"].to_pydatetime(),
            disc_number=_disc_number,
            disc_count=_disc_count,
            track_number=_track_number,
            track_count=_track_count,
            date_modified=_date_modified,
            loved=_loved,
            compilation=_compilation,
            stream_path=_stream_path,
        )

    @classmethod
    def wrap_remove_path(cls, stream_path: Path) -> "ITunesSong":
        """
        Generate a dummy ITunesSong with only the stream_path attribute
        for use by the repair functionality
        """
        return cls(
            track_id=-1,
            size=-1,
            total_time=-1,
            name="remove",
            artist="remove",
            album_artist="remove",
            album="remove",
            location="remove",
            archive_path=Path(),
            kind="remove",
            date_added=datetime.utcnow(),
            stream_path=stream_path,
        )

    @classmethod
    def from_dataframe(cls, data: pandas.DataFrame) -> list["ITunesSong"]:
        """Convert an iTunes DataFrame to a list of ITunesSongs"""
        if data.empty:
            return []
        return list(data.apply(cls.from_dataframe_row, axis=1))

    @staticmethod
    def stage_path() -> Path:
        """Return a temp staging directory"""
        return CONFIG.workspace.joinpath("music_stage")

    @classmethod
    def generate_stream_path(cls, path: str, stage: bool = False) -> Path:
        """Generates the stream version of the string path with the same suffix"""
        stream = CONFIG.audio_streams[0]
        if stage:
            stream = cls.stage_path()

        return Path(path.replace(str(CONFIG.itunes_music()), str(stream)))

    def _to_flac(self, out_file: str) -> int:
        in_file = str(self.archive_path)
        cmd = [
            "ffmpeg",
            "-i",
            in_file,
            "-v",
            "error",
            "-c:a",
            "flac",
            "-c:v",
            "copy",
            out_file,
        ]
        proc_out = subprocess.run(cmd, capture_output=True, text=True)
        return proc_out.returncode

    def _copy(self, destination: str) -> int:
        source = str(self.archive_path)
        cmd = ["cp", source, destination]
        proc_out = subprocess.run(cmd, capture_output=True, text=True)
        return proc_out.returncode

    def create_stream(self, stage: bool = True) -> StagedTimestamp:
        """Stages an iTunes song"""
        _path = self.generate_stream_path(path=str(self.archive_path), stage=stage)
        _dest = self.generate_stream_path(path=str(self.archive_path), stage=False)
        _path.parent.mkdir(parents=True, exist_ok=True)
        if self.kind == "Apple Lossless audio file":
            _path = _path.with_suffix(".flac")
            _ = self._to_flac(out_file=str(_path))
        else:
            _ = self._copy(destination=_path)

        return StagedTimestamp(path=_path, timestamp=self.date_added, dest=_dest)


@dataclass(slots=True)
class ITunesDiff:
    """ "Holds a list of library differences"""

    new_tracks: list[ITunesSong]
    removed_tracks: list[ITunesSong]
    modifed_tracks: list[ITunesSong]


@dataclass(slots=True)
class ITunesLibraryDataFrame:
    """iTunes Library"""

    tracks: pandas.DataFrame
    playlists: pandas.DataFrame
    date: datetime

    __annotations__ = {
        "tracks": pandas.DataFrame,
        "playlists": pandas.DataFrame,
        "date": datetime,
    }

    def __init__(
        self,
        tracks: pandas.DataFrame,
        playlists: pandas.DataFrame,
        date: datetime,
    ) -> None:
        self.tracks = tracks
        self.playlists = playlists
        self.date = date

    def to_json(self) -> dict:
        return {
            "tracks": json.loads(self.tracks.to_json(date_format="iso")),
            "playlists": json.loads(self.playlists.to_json(date_format="iso")),
            "date": self.date.isoformat(),
        }

    @classmethod
    def from_json(cls, obj: dict) -> "ITunesLibraryDataFrame":
        """Construct from json"""
        _tracks = obj["tracks"]
        _playlists = obj["playlists"]
        _date = obj["date"]

        _ = [d for d in obj["tracks"]["date_modified"]]
        return cls(
            tracks=pandas.DataFrame(_tracks),
            playlists=pandas.DataFrame(_playlists),
            date=datetime.fromisoformat(_date),
        )

    @staticmethod
    def _set_gain() -> tuple[int, list[str]]:
        """
        Sets gain for all files in the music stage

        Returns a 2 tuple containing the exit code and list of the
        filtered standard out.
        """
        stage = ITunesSong.stage_path()
        cmd = ["r128gain", "-r", "-a", stage]
        proc_out = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        stdout_lines = proc_out.stdout.splitlines()
        filtered_stdout = [i for i in stdout_lines if "File" in i or "Album" in i]
        return proc_out.returncode, filtered_stdout

    @staticmethod
    def files_in_archive() -> list[str]:
        """Returns a list of the files in the iTunes Music archive"""
        return [os.path.join(r, ff) for r, _, f in os.walk(CONFIG.itunes_music()) for ff in f]

    @staticmethod
    def files_in_stream() -> list[str]:
        """Returns a list of the files in the audio stream"""
        return [os.path.join(r, ff) for r, _, f in os.walk(CONFIG.audio_streams[0]) for ff in f]

    def _archive_paths(self, files: list[str]) -> None:
        """
        _archive_path updates the tracks dataframe with case correct paths
        to the archived itunes files.
        """
        files = pandas.DataFrame({"archive_path": files})
        files["_temp"] = files["archive_path"].str.lower()

        self.tracks["_temp"] = self.tracks["location"].apply(urllib.parse.unquote)
        self.tracks["_temp"] = (
            self.tracks["_temp"]
            .str.replace("file://localhost/C:/Users/ryan/Music/iTunes", str(CONFIG.itunes_dir))
            .str.lower()
        )

        self.tracks["archive_path"] = self.tracks.merge(files, how="outer", on="_temp")["archive_path"]
        self.tracks.drop(columns="_temp")

        return None

    @staticmethod
    def _stream_paths(path: str) -> Optional[str]:
        """_stream_paths"""

        if len(CONFIG.audio_streams) > 1:
            raise Exception("Cant deal with more than one audio stream directory")

        stream = str(CONFIG.audio_streams[0])
        _path = Path(path.replace(str(CONFIG.itunes_music()), stream))
        if _path.exists():
            return str(_path)

        if _path.with_suffix(".flac").exists():
            return str(_path.with_suffix(".flac"))

        return None

    def update_stream_paths(self) -> None:
        """Updates the stream paths in the tracks df"""

        self.tracks["stream_path"] = self.tracks["archive_path"].apply(self._stream_paths)

    @classmethod
    def _process_xml(cls, it_xml: ElementTree.ElementTree) -> "ITunesLibraryDataFrame":
        """Logic to process the raw iTunes XML string"""

        _dict = ITunesXmlConverter.to_json(it_xml)

        for playlist in _dict["playlists"]:
            if "playlist_items" in playlist.keys():
                playlist["playlist_items"] = [t["track_id"] for t in playlist["playlist_items"]]

        itdf = cls(
            tracks=pandas.DataFrame(data=_dict["tracks"].values()),
            playlists=pandas.DataFrame(data=_dict["playlists"]),
            date=_dict["date"],
        )

        itdf._archive_paths(files=itdf.files_in_archive())
        itdf.update_stream_paths()

        return itdf

    def save(self, bak: bool = False) -> None:
        """
        Save the ITunesLibrary as a pickle (set of parquet TODO) files.

        Optional paramter bak will append the .bak extension to the file
        when saving
        """
        itunes_data = CONFIG.itunes_data()
        if bak:
            itunes_data = itunes_data.with_suffix(".bak")

        with open(itunes_data, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, bak: bool = False) -> "ITunesLibraryDataFrame":
        """
        Loads a library dataframe from disk. If one does not exist
        an itunes xml will be parsed.

        bak: bool optional parameter that will attempt to load
        the backup of the ituned lib df. Defaults to False, if True
        and a backup doesnt exist, the function will return the current
        df
        """
        itdf_data = CONFIG.itunes_data()
        if bak and itdf_data.with_suffix(".bak").exists():
            itdf_data = itdf_data.with_suffix(".bak")

        if not itdf_data.exists():
            return cls.from_itunes_xml()

        with open(itdf_data, "rb") as f:
            return pickle.load(f)

    @classmethod
    def from_itunes_xml(cls, xml_path_override: Optional[Path] = None) -> "ITunesLibraryDataFrame":
        """Build from an iTunes XML"""

        xml_path = CONFIG.itunes_dir.joinpath("iTunes Music Library.xml")
        if xml_path_override is not None:
            xml_path = xml_path_override

        it_xml = ElementTree.parse(xml_path)

        return cls._process_xml(it_xml=it_xml)

    def export_playlists(self) -> None:
        """export_playlists"""

        click.echo(click.style("\nGenerating Playlists", bold=True))
        has_playlist = self.playlists["playlist_items"].notna()
        not_library = self.playlists["name"] != "Library"

        for _, playlist in self.playlists[has_playlist & not_library].iterrows():
            plist = CONFIG.mpd_dir.joinpath("playlists").joinpath(playlist["name"]).with_suffix(".m3u")
            songs = [
                str(self.tracks[self.tracks["track_id"] == id]["stream_path"].iloc[0])
                for id in playlist["playlist_items"]
            ]
            with open(plist, "w") as f:
                f.write("\n".join(songs))
            click.echo(f"[{click.style('*', fg='green')}] {playlist['name']}")

    def new_files(self, old_itdf: "ITunesLibraryDataFrame") -> list[ITunesSong]:
        """Returns a list of new itunes songs"""
        # New files are found by checking for persistent ids not in the old df
        new_songs = ~self.tracks["persistent_id"].isin(old_itdf.tracks["persistent_id"])
        return ITunesSong.from_dataframe(self.tracks.loc[new_songs])

    def removed_files(self, old_itdf: "ITunesLibraryDataFrame") -> list[ITunesSong]:
        """Returns a list of removed itunes songs"""
        # Removed files are found by checking for persistent ids not in the new df
        removed_songs = ~old_itdf.tracks["persistent_id"].isin(self.tracks["persistent_id"])
        return ITunesSong.from_dataframe(old_itdf.tracks.loc[removed_songs])

    def modified_files(self, old_itdf: "ITunesLibraryDataFrame", mod: Optional[list[str]] = None) -> list[ITunesSong]:
        """
        Returns a list of modified itunes songs

        mod: optional list of modified album names to overrride algorithm
        """
        # If mod is provided, its a list of modified albums to override the algorithm in case
        # data is corrupted
        if mod is not None:
            modified_songs = self.tracks["album"].isin(mod)
            return ITunesSong.from_dataframe(self.tracks[modified_songs])

        # TODO(Ryan): add entire album to modified list, not just songs
        # Modified songs are found by checking for persistent ids that exist in both
        # dataframes but have a different modified date
        existing_songs = self.tracks["persistent_id"].isin(old_itdf.tracks["persistent_id"])

        merged = self.tracks[existing_songs].merge(
            old_itdf.tracks.filter(["date_modified", "persistent_id"]),
            on=["persistent_id"],
            how="left",
            suffixes=["", "_old"],
        )
        modified_songs = merged["date_modified"] != merged["date_modified_old"]
        return ITunesSong.from_dataframe(merged[modified_songs])

    def missing_from_stream(self) -> list[ITunesSong]:
        """Files with no matching stream paths"""
        return ITunesSong.from_dataframe(self.tracks[self.tracks["stream_path"].isna()])

    def extra_stream_files(self) -> list[str]:
        """Files in the stream with no match in iTunes"""
        stream_files = pandas.Series(self.files_in_stream())
        return list(stream_files[~stream_files.isin(self.tracks["stream_path"])])

    @classmethod
    def current_xml_timestamp(cls) -> datetime:
        """Returns the Date field from the itunes xml"""

        xml_path = CONFIG.itunes_dir.joinpath("iTunes Music Library.xml")
        it_xml = ElementTree.parse(xml_path)
        date = next(v for k, v in unzip(it_xml.findall("./dict/")) if k.text == "Date")
        return ITunesXmlConverter._date(e=date)

    def diff(self, older_itdf: "ITunesLibraryDataFrame", mod: Optional[list[str]] = None) -> ITunesDiff:
        """
        Updates the stream library files based on changes to the
        itunes archive
        """
        # New Files - Files that did not exist before
        new = self.new_files(older_itdf)

        # Removed Files - Files that no longer exist
        removed = self.removed_files(older_itdf)

        # Modified Files - Files that have been modified somehow
        modified = self.modified_files(older_itdf, mod)

        delim = "-" * 80
        click.secho(f"New Tracks\n{delim}", fg="green")
        for f in new:
            click.secho(f"{f.artist} - {f.album} - {f.name}", fg="green")

        click.secho(f"\nModified Tracks\n{delim}", fg="blue")
        for f in modified:
            click.secho(f"{f.artist} - {f.album} - {f.name}", fg="blue")

        click.secho(f"\nRemoved Tracks\n{delim}", fg="red")
        for f in removed:
            click.secho(f"{f.artist} - {f.album} - {f.name}", fg="red")
        click.echo("\n")

        return ITunesDiff(
            new_tracks=new,
            removed_tracks=removed,
            modifed_tracks=modified,
        )

    @classmethod
    def compare(cls, modified: Optional[list[str]] = None) -> ITunesDiff:
        """Compare two latest versions of the iTunes DB"""

        _star = click.style("*", fg="green")
        click.secho("\nLoading iTunes Data", bold=True)
        itdf = cls.load()
        click.echo(f"[{_star}] - {itdf.date} - iTunes Date Modified")

        xml_timestamp = cls.current_xml_timestamp()
        click.echo(f"[{_star}] - {xml_timestamp} - XML Date Modified")

        if itdf.date != xml_timestamp:
            click.echo(f"[{click.style('>', fg='yellow')}] Swapping")
            old_itdf = itdf
            itdf = cls.from_itunes_xml()
        else:
            old_itdf = cls.load(bak=True)

        click.echo(f"[{_star}] - {itdf.date} - New iTunes Data")
        click.echo(f"[{_star}] - {old_itdf.date} - Old iTunes Data\n")

        # Save the data
        itdf.save()
        old_itdf.save(bak=True)

        return itdf.diff(older_itdf=old_itdf, mod=modified)

    def _update(self, diff: ITunesDiff) -> None:
        """Update the stream library based on the diff"""

        rem = click.style("X", fg="red")
        add = click.style("A", fg="green")
        mod = click.style("M", fg="blue")

        modified_albums = {i.album for i in diff.modifed_tracks}

        modded = ITunesSong.from_dataframe(self.tracks[self.tracks["album"].isin(modified_albums)])

        # Stage
        click.echo(click.style("Staging Tracks", bold=True))
        files_to_stamp = []

        # Add new files
        for new in diff.new_tracks:
            stage_stamp = new.create_stream(stage=True)
            files_to_stamp.append(stage_stamp)
            click.echo(f"[{add}] {stage_stamp.path}")

        # Stage modified files
        for modified in modded:
            stage_stamp = modified.create_stream(stage=True)
            files_to_stamp.append(stage_stamp)
            click.echo(f"[{mod}] {stage_stamp.path}")

        # Remove files
        for removed in diff.removed_tracks:
            if removed.stream_path is not None:
                click.echo(f"[{rem}] {removed.stream_path}")
                removed.stream_path.unlink()

        # Normalize the staged music
        click.echo(click.style("\nNormalize Staged Tracks", bold=True))
        exit_code, filtered_stdout = self._set_gain()
        if exit_code == 0:
            for line in filtered_stdout:
                click.echo(f"[{click.style('*', fg='green')}] {line}")
        else:
            click.echo(f"[{click.style('-', fg='red')}] {exit_code}")

        # Set timestamps of the staged tracks
        click.echo(click.style("\nTimestamp Staged Tracks", bold=True))
        parent_stamps = {str(i.path.parent): i for i in files_to_stamp}
        for _, v in parent_stamps.items():
            files_to_stamp.append(StagedTimestamp(path=v.path.parent, timestamp=v.timestamp, dest=v.dest.parent))

        for staged_file in files_to_stamp:
            exit_code = staged_file.set_timestamp()
            if exit_code == 0:
                click.echo(f"[{click.style('*', fg='green')}] {staged_file.timestamp} {staged_file.path}")
            else:
                click.echo(f"[{click.style('-', fg='red')}] {exit_code} {staged_file.path}")

        # Add staged music to stream and clean
        click.echo(click.style("\nAdding staged albums to music stream", bold=True))
        album_folders = [(p.path.parent, p.dest.parent) for _, p in parent_stamps.items()]
        for staged, destination in album_folders:
            click.echo(f"[{click.style('>', fg='green')}] {destination}")
            shutil.copytree(staged, destination, dirs_exist_ok=True)

        if ITunesSong.stage_path().exists():
            shutil.rmtree(ITunesSong.stage_path())

    @staticmethod
    def _cache_album_art(src_file: Path, cache_dir: Path) -> None:
        """
        Extracts the album art
        """
        outfile = cache_dir.joinpath("cover.jpg")

        if not outfile.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            cmd = ["ffmpeg", "-i", str(src_file), "-an", "-vcodec", "copy", str(outfile)]
            proc = subprocess.run(cmd, capture_output=True)

            status = click.style("#", fg="green")
            if proc.returncode != 0:
                status = click.style("#", fg="red")
            click.echo(f"[{status}] {outfile}")

    @staticmethod
    def cache_album_art() -> None:
        """
        Walks the stream music and caches album art in a mirrored directory. The mirrored directory will contain

        /Artist/Album/cover
        """

        empty_directories = []
        for root, dirs, files in os.walk(CONFIG.audio_streams[0]):
            if len(dirs) == 0 and len(files) > 0:
                _cache = Path(root.replace(str(CONFIG.audio_streams[0]), "/home/ryan/Pictures/.covercache/"))
                _src = Path(root).joinpath(files[0])
                ITunesLibraryDataFrame._cache_album_art(_src, _cache)

            if len(dirs) == 0 and len(files) == 0:
                empty_directories.append(root)

        click.echo("Empty Directories")
        for dir in empty_directories:
            click.echo(dir)

    @classmethod
    def update(cls, modified: Optional[list[str]] = None) -> None:
        """Update the stream library with based on diff"""

        # Run comparison of the data itunes data
        it_diff = cls.compare(modified=modified)
        click.echo(click.style("\nUpdating music stream", bold=True))
        s = f"[{click.style('A', fg='green')}] Add:     {len(it_diff.new_tracks)}\n"
        s += f"[{click.style('M', fg='blue')}] Replace: {len(it_diff.modifed_tracks)}\n"
        s += f"[{click.style('R', fg='red')}] Remove:  {len(it_diff.removed_tracks)}\n"
        click.secho(s)

        # Call the update
        itdf = cls.load()
        itdf._update(diff=it_diff)

        # Refresh the dataframe stream paths
        click.echo(click.style("\nUpdating Stream Paths", bold=True))
        itdf.update_stream_paths()
        itdf.save()
        click.echo(f"[{click.style('*', fg='green')}] Done")

        # Export playlists
        itdf.export_playlists()

        # Cache albums
        click.secho("\nCache Artwork")
        cls.cache_album_art()

        # Find extra and missing files
        click.echo(click.style("\nExtra And Missing Files", bold=True))
        missing_files = itdf.missing_from_stream()
        extra_files = itdf.extra_stream_files()

        for extra in extra_files:
            click.echo(f"[{click.style('E', fg='yellow')}] {extra}")

        for missing in missing_files:
            click.echo(f"[{click.style('?', fg='yellow')}] {missing.archive_path}")

    @classmethod
    def repair(cls) -> None:
        """Repair missing and extra files"""

        itdf = cls.load()

        # Find extra and missing files
        click.echo(click.style("\nAttempting to repair music stream", bold=True))
        missing_files = itdf.missing_from_stream()
        extra_files = itdf.extra_stream_files()

        for extra in extra_files:
            click.echo(f"[{click.style('E', fg='yellow')}] {extra}")

        for missing in missing_files:
            click.echo(f"[{click.style('?', fg='yellow')}] {missing.archive_path}")

        # Turn missing_files into modified itunes songs
        missing_albums = set([i.album for i in missing_files])
        mod_mask = itdf.tracks["album"].isin(missing_albums)
        modified_songs = ITunesSong.from_dataframe(itdf.tracks[mod_mask])

        # Turn extra_files into reomved_tracks
        removed_tracks = [ITunesSong.wrap_remove_path(Path(i)) for i in extra_files]
        repair_diff = ITunesDiff(new_tracks=[], modifed_tracks=modified_songs, removed_tracks=removed_tracks)

        # Call update with the repair diff
        click.echo()
        itdf._update(diff=repair_diff)
