"""itunes.py"""

from typing import Optional
from datetime import datetime

import pandas
from pandas import Int64Dtype, Timestamp, BooleanDtype, StringDtype
from numpy import int64
from rkiv.config import Config


_CONFIG = Config()


class ITunesSong:
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
    purchased: bool
    date_added: datetime
    disc_number: Optional[int]
    disc_count: Optional[int]
    track_number: Optional[int]
    track_count: Optional[int]
    date_modified: Optional[datetime]
    loved: Optional[bool]
    compilation: Optional[bool]

    def __init__(
        self,
        track_id: int,
        size: int,
        total_time: int,
        name: str,
        artist: str,
        album_artist: str,
        album: str,
        location: str,
        purchased: bool,
        date_added: datetime,
        disc_number: Optional[int],
        disc_count: Optional[int],
        track_number: Optional[int],
        track_count: Optional[int],
        date_modified: Optional[datetime],
        loved: Optional[bool],
        compilation: Optional[bool],
    ) -> None:
        self.track_id = track_id
        self.size = size
        self.total_time = total_time
        self.name = name
        self.artist = artist
        self.album_artist = album_artist
        self.album = album
        self.location = location
        self.purchased = purchased
        self.date_added = date_added
        self.disc_number = disc_number
        self.disc_count = disc_count
        self.track_number = track_number
        self.track_count = track_count
        self.date_modified = date_modified
        self.loved = loved
        self.compilation = compilation

    @classmethod
    def from_dataframe_row(cls, row: pandas.Series) -> "ITunesSong":
        """Build from a data frame row"""

        if row["Disc Number"].notna():
            _disc_number = row["Disc Number"]

        if row["Disc Count"].notna():
            _disc_count = row["Disc Count"]

        if row["Track Number"].notna():
            _track_number = row["Track Number"]

        if row["Track Count"].notna():
            _track_count = row["Track Count"]

        if row["Date Modified"].notna():
            _date_modified = row["Date Modified"].to_pydatetime()

        if row["Loved"].notna():
            _loved = row["Loved"]

        if row["Compilation"].notna():
            _compilation = row["Compilation"]

        _purchased = True
        if row["Purchased"].isna():
            _purchased = False

        return cls(
            track_id=row["Track ID"],
            size=row["Size"],
            total_time=row["Total Time"],
            name=row["Name"],
            artist=row["Artist"],
            album_artist=row["Album Artist"],
            album=row["Album"],
            location=row["Location"],
            purchased=_purchased,
            date_added=row["Date Added"].to_pydatetime(),
            disc_number=_disc_number,
            disc_count=_disc_count,
            track_number=_track_number,
            track_count=_track_count,
            date_modified=_date_modified,
            loved=_loved,
            compilation=_compilation,
        )

    @classmethod
    def convert_dataframe(cls, data: pandas.DataFrame) -> list["ITunesSong"]:
        """Convert an iTunes DataFrame to a list of ITunesSongs"""
        return list(data.apply(cls.from_dataframe_row, axis=1))


class ItunesLibrary:
    """iTunes Library"""

    __slots__ = ("data",)

    data: pandas.DataFrame

    __annotations__ = {
        "data": pandas.DataFrame,
    }

    def __init__(self, data: pandas.DataFrame) -> None:
        self.data = data
