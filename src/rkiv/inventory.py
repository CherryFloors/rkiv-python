import os
from pathlib import Path
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


import pandas

# import pyudev  # type: ignore
import click


from rkiv.config import Config

CONFIG = Config()

# context = pyudev.Context()
# device = pyudev.Devices.from_device_file(context, "/dev/sr0")
# d = device.items()
# def (dir: Path)


class MediaCategory(str, Enum):
    """Media Category for classifying disc"""

    MUSIC = "music"
    MOVIE = "movie"
    TV = "tv"

    @classmethod
    def to_categorical(cls) -> pandas.CategoricalDtype:
        return pandas.CategoricalDtype(categories=[i.value for i in cls], ordered=False)


@dataclass
class StreamObject:
    """Archived Disc Object"""

    __slots__ = (
        "title",
        "path",
        "category",
        "match_name",
    )

    title: str
    path: Path
    category: MediaCategory
    match_name: str

    __annotations__ = {
        "title": str,
        "path": Path,
        "category": MediaCategory,
        "match_name": str,
    }

    def __init__(
        self,
        title: str,
        path: Path,
        category: MediaCategory,
        match_name: str,
    ) -> None:
        self.title = title
        self.path = path
        self.category = category
        self.match_name = match_name

    @classmethod
    def from_dir(cls, dir: Path) -> Optional["StreamObject"]:
        """from_dir"""

        season_in_stem = "Season_" in dir.stem
        has_video_files = OpticalDiscType.categorize(dir=dir) == OpticalDiscType.FILES
        if not (season_in_stem or has_video_files):
            return None

        parts = [i.lower() for i in dir.parts]
        _title = _match_name = dir.stem

        _category = MediaCategory.MUSIC
        if "movie" in parts or "movies" in parts:
            _category = MediaCategory.MOVIE
        if "tv" in parts:
            _category = MediaCategory.TV
            suffix = dir.stem.removeprefix("Season_")
            _title = dir.parent.stem
            _match_name = f"{_title}_S{suffix}"

        return cls(title=_title, path=dir, category=_category, match_name=_match_name)

    @classmethod
    def walk_stream_library(cls, root_path: Path) -> list["StreamObject"]:
        """
        Walks the stream library
        """
        _from_dir = cls.from_dir(dir=root_path)
        if _from_dir is not None:
            return [_from_dir]

        l = []
        root, dirs, _ = next(os.walk(root_path))
        for dir in [Path(root).joinpath(d) for d in dirs if d not in {""}]:
            l += cls.walk_stream_library(root_path=dir)

        return l


class OpticalDiscType(str, Enum):
    """Optical Disc Categories"""

    CD = "cd"
    DVD = "dvd"
    BLU_RAY = "blu_ray"
    FILES = "files"
    UNDEFINED = "undefined"

    @classmethod
    def to_categorical(cls) -> pandas.CategoricalDtype:
        return pandas.CategoricalDtype(categories=[i.value for i in cls], ordered=False)

    @classmethod
    def categorize(cls, dir: Path) -> "OpticalDiscType":
        """categorize"""

        BD_FILES = {"BDMV"}
        DVD_FILES = {"VIDEO_TS"}
        CD_EXTS = {"wav"}
        FILES_EXTS = {".m4v", ".mkv", ".mp4"}

        _, dirs, files = next(os.walk(dir))

        for d in dirs:
            if d in BD_FILES:
                return cls.BLU_RAY
            if d in DVD_FILES:
                return cls.DVD

        for file in files:
            ext = Path(file).suffix
            if ext in CD_EXTS:
                return cls.CD
            if ext in FILES_EXTS:
                return cls.FILES

        return cls.UNDEFINED


@dataclass
class ArchivedDisc:
    """Archived Disc Object"""

    __slots__ = (
        "title",
        "disc_name",
        "path",
        "category",
        "type",
        "iso",
        "problem",
    )

    title: str
    disc_name: str
    path: Path
    category: MediaCategory
    type: OpticalDiscType
    iso: bool
    problem: bool

    __annotations__ = {
        "title": str,
        "disc_name": str,
        "path": Path,
        "category": MediaCategory,
        "type": OpticalDiscType,
        "iso": bool,
        "problem": bool,
    }

    def __init__(
        self,
        title: str,
        disc_name: str,
        path: Path,
        category: MediaCategory,
        type: OpticalDiscType,
        iso: bool,
        problem: bool,
    ) -> None:
        self.title = title
        self.disc_name = disc_name
        self.path = path
        self.category = category
        self.type = type
        self.iso = iso
        self.problem = problem

    def dict(self) -> Dict[str, Any]:
        """dict"""
        return {
            "title": self.title,
            "disc_name": self.disc_name,
            "path": str(self.path),
            "category": self.category.value,
            "type": self.type.value,
            "iso": self.iso,
            "problem": self.problem,
        }

    @classmethod
    def dtypes(cls) -> Dict[str, Any]:
        return {
            "title": str,
            "disc_name": str,
            "path": str,
            "category": MediaCategory.to_categorical(),
            "type": MediaCategory.to_categorical(),
            "iso": bool,
            "problem": bool,
        }

    @classmethod
    def from_dir(cls, dir: Path) -> "ArchivedDisc":
        """from_dir"""

        parts = [i.lower() for i in dir.parts]
        _type = OpticalDiscType.categorize(dir=dir)
        _disc_name = dir.stem

        _category = MediaCategory.MUSIC
        if "movie" in parts or "movies" in parts:
            _category = MediaCategory.MOVIE
        if "tv" in parts:
            _category = MediaCategory.TV

        return cls(
            title=dir.parent.stem,
            disc_name=_disc_name,
            path=dir,
            category=_category,
            type=_type,
            iso=False,  # TODO Handle iso images
            problem=("problems" in parts) or ("problem" in parts),
        )

    @classmethod
    def walk_disc_archive(cls, root_path: Path) -> List["ArchivedDisc"]:
        """
        walk_disc_archive

        TODO Handle iso images. Need a good lib to do this, https://pypi.org/project/pycdio/
        looks good but has some deps that need to be built and installed separate. Should get
        a deps.sh script togother and document in readme. Should include other eternals like
        MakeMKV, abdcde, etc...
        """
        if root_path.stem == "lost+found":
            return []

        if OpticalDiscType.categorize(dir=root_path) != OpticalDiscType.UNDEFINED:
            return [cls.from_dir(dir=root_path)]

        l = []
        root, dirs, _ = next(os.walk(root_path))
        for dir in [Path(root).joinpath(d) for d in dirs if d not in {"ArchiveShare"}]:
            l += cls.walk_disc_archive(root_path=dir)

        return l


@dataclass
class DiscArchiveDataFrame:
    """Stores Disc Archive inventory"""

    __slots__ = "df"

    df: pandas.DataFrame

    __annotations__ = {
        "df": pandas.DataFrame,
    }

    def __init__(self, df: pandas.DataFrame) -> None:
        self.df = df

    @classmethod
    def from_archive_list(cls, archived_discs: List[ArchivedDisc]) -> "DiscArchiveDataFrame":
        """from_archive_list"""
        return cls(df=pandas.DataFrame(data=[i.dict() for i in archived_discs], dtype=ArchivedDisc.dtypes()))

    @classmethod
    def from_parquet(cls, path: Path) -> "DiscArchiveDataFrame":
        """from_parquet"""
        return cls(df=pandas.read_parquet(path=path))


@dataclass(slots=True)
class Inventory:
    """
    Object to hold video streaming inventory

    Attributes
    ----------
    stream_objects  : `list[StreamObject]`
    video_archive  : `list[ArchivedDisc]`
    unreleased_movies  : `list[ArchivedDisc]`
    unreleased_tv  : `list[ArchivedDisc]`
    """

    stream_objects: list[StreamObject]
    video_archive: list[ArchivedDisc]
    unreleased_movies: list[ArchivedDisc]
    unreleased_tv: list[ArchivedDisc]

    @staticmethod
    def find_unreleased_media(
        stream_objects: list[StreamObject], archived_objects: list[ArchivedDisc]
    ) -> list[ArchivedDisc]:
        """
        Finds unreleased media by comparing title names in a list of `StreamObject`'s and `ArchivedDisc`'s.

        Parameters
        ----------
        stream_objects : `list[StreamObject]`
        archived_objects : `list[ArchivedDisc]`

        Returns
        -------
        `list[ArchivedDisc]`
        """
        stream_titles = {t.match_name for t in stream_objects}
        return [i for i in archived_objects if i.title not in stream_titles]

    @classmethod
    def take_inventory(cls) -> "Inventory":
        """
        Factory method to build a brand new inventory object

        Returns
        -------
        `Inventory`
        """

        click.secho("Walking the Archive", bold=True)
        archived_discs = []
        for archive in CONFIG.video_archives:
            _archived_discs = ArchivedDisc.walk_disc_archive(root_path=archive)
            archived_discs += _archived_discs
            click.echo(f"  [{len(_archived_discs)}] {archive}")

        click.secho("Walking the Stream", bold=True)
        stream_objects = []
        for stream in CONFIG.video_streams:
            _stream_objects = StreamObject.walk_stream_library(root_path=stream)
            stream_objects += _stream_objects
            click.echo(f"  [{len(_stream_objects)}] {stream}")

        unreleased = cls.find_unreleased_media(stream_objects=stream_objects, archived_objects=archived_discs)
        return cls(
            stream_objects=stream_objects,
            video_archive=archived_discs,
            unreleased_movies=[s for s in unreleased if s.category == MediaCategory.MOVIE],
            unreleased_tv=[s for s in unreleased if s.category == MediaCategory.TV],
        )
