"""itunes.py"""

import html
import urllib.parse
import pickle
from dataclasses import dataclass
from typing import Optional, Union, Iterable, Callable
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from pydantic import BaseModel
import pandas

from rkiv.config import Config


CONFIG = Config()


class unzip:
    """Iterator that unzips an interable int groups of 2"""

    def __init__(self, l: Iterable):
        self.l = l

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i + 1 >= len(self.l):
            raise StopIteration
        odd, even = self.l[self.i], self.l[self.i + 1]
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
        return {
            cls.convert_element(k): cls.convert_element(v)
            for k, v in unzip(e.findall("./"))
        }

    @classmethod
    def get_type(cls, xml_type: str) -> Union[type, str]:
        """Convert iTunes string to python/pandas type"""
        return cls.DTYPES[xml_type]

    @classmethod
    def convert_element(
        cls, element: ElementTree.Element
    ) -> Union[dict, list, str, float, int, bool, datetime]:
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
    purchased: bool = False
    date_added: datetime
    disc_number: Optional[int] = None
    disc_count: Optional[int] = None
    track_number: Optional[int] = None
    track_count: Optional[int] = None
    date_modified: Optional[datetime] = None
    loved: Optional[bool] = None
    compilation: Optional[bool] = None

    __annotations__ = {
        "track_id": int,
        "size": int,
        "total_time": int,
        "name": str,
        "artist": str,
        "album_artist": str,
        "album": str,
        "location": str,
        "purchased": bool,
        "date_added": datetime,
        "disc_number": Optional[int],
        "disc_count": Optional[int],
        "track_number": Optional[int],
        "track_count": Optional[int],
        "date_modified": Optional[datetime],
        "loved": Optional[bool],
        "compilation": Optional[bool],
    }

    @classmethod
    def from_dataframe_row(cls, row: pandas.Series) -> "ITunesSong":
        """Build from a data frame row"""

        if row["disc_number"].notna():
            _disc_number = row["disc_number"]

        if row["disc_count"].notna():
            _disc_count = row["disc_count"]

        if row["track_number"].notna():
            _track_number = row["track_number"]

        if row["track_count"].notna():
            _track_count = row["Track_count"]

        if row["date_modified"].notna():
            _date_modified = row["date_modified"].to_pydatetime()

        if row["loved"].notna():
            _loved = row["loved"]

        if row["compilation"].notna():
            _compilation = row["compilation"]

        _purchased = True
        if row["purchased"].isna():
            _purchased = False

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
            purchased=_purchased,
            date_added=row["date_added"].to_pydatetime(),
            disc_number=_disc_number,
            disc_count=_disc_count,
            track_number=_track_number,
            track_count=_track_count,
            date_modified=_date_modified,
            loved=_loved,
            compilation=_compilation,
        )

    @classmethod
    def from_dataframe(cls, data: pandas.DataFrame) -> list["ITunesSong"]:
        """Convert an iTunes DataFrame to a list of ITunesSongs"""
        return list(data.apply(cls.from_dataframe_row, axis=1))


@dataclass(slots=True)
class ITunesLibraryDataFrame:
    """iTunes Library"""

    tracks: pandas.DataFrame
    playlists: pandas.DataFrame

    __annotations__ = {
        "tracks": pandas.DataFrame,
        "playlists": pandas.DataFrame,
    }

    def __init__(
        self,
        tracks: pandas.DataFrame,
        playlists: pandas.DataFrame,
    ) -> None:
        self.tracks = tracks
        self.playlists = playlists

    @staticmethod
    def _archive_path(path: str) -> Path:
        """_archive_path"""
        _path = urllib.parse.unquote(path)
        _path = _path.replace(
            "file://localhost/C:/Users/Ryan/Music/iTunes", str(CONFIG.itunes_dir)
        )
        return Path(_path)

    @staticmethod
    def _stream_path(path: Path) -> Optional[Path]:
        """_stream_path"""
        itunes = str(CONFIG.itunes_dir.joinpath("iTunes Media").joinpath("Music"))
        if len(CONFIG.audio_streams) > 1:
            raise Exception("Cant deal with more than one audio stream directory")

        stream = str(CONFIG.audio_streams[0])
        path = Path(str(path).replace(itunes, stream))
        if path.exists():
            return path

        if path.with_suffix(".flac").exists():
            return path.with_suffix(".flac")

        return None

    @classmethod
    def _process_xml(cls, it_xml: ElementTree.ElementTree) -> pandas.DataFrame:
        """Logic to process the raw iTunes XML string"""

        _dict = ITunesXmlConverter.to_json(it_xml)

        for playlist in _dict["playlists"]:
            if "playlist_items" in playlist.keys():
                playlist["playlist_items"] = [
                    t["track_id"] for t in playlist["playlist_items"]
                ]

        _tracks = pandas.DataFrame(data=_dict["tracks"].values())
        _tracks["archive_path"] = _tracks["location"].apply(cls._archive_path)
        _tracks["stream_path"] = _tracks["archive_path"].apply(cls._stream_path)

        return cls(
            tracks=_tracks,
            playlists=pandas.DataFrame(data=_dict["playlists"]),
        )

    def save(self) -> None:
        """
        Save the ITunesLibrary as a set of parquet files. Previous saved
        files will be moved to *.bak allowing recovery.
        """
        itunes_data = CONFIG.itunes_data()
        if itunes_data.exists():
            itunes_data.rename(itunes_data.with_suffix(".bak"))

        with open(itunes_data, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load() -> "ITunesLibraryDataFrame":
        with open(CONFIG.itunes_data(), "rb") as f:
            return pickle.load(f)

    @classmethod
    def from_itunes_xml(
        cls, xml_path_override: Optional[Path] = None
    ) -> "ITunesLibraryDataFrame":
        """Build from an iTunes XML"""

        xml_path = CONFIG.itunes_dir.joinpath("iTunes Music Library.xml")
        if xml_path_override is not None:
            xml_path = xml_path_override

        it_xml = ElementTree.parse(xml_path)

        return cls._process_xml(it_xml=it_xml)

    def export_playlists(self) -> None:
        """export_playlists"""
        has_playlist = self.playlists["playlist_items"].notna()
        not_library = self.playlists["name"] != "Library"
        for _, playlist in self.playlists[has_playlist & not_library].iterrows():
            plist = (
                CONFIG.mpd_dir.joinpath("playlists")
                .joinpath(playlist["name"])
                .with_suffix(".m3u")
            )
            songs = [
                str(self.tracks[self.tracks["track_id"] == id]["stream_path"].iloc[0])
                for id in playlist["playlist_items"]
            ]
            with open(plist, "w") as f:
                f.write("\n".join(songs))

