"""
Wrappers and Data Structures for HandbrakeCLI
"""
from __future__ import annotations

import subprocess
import json
from pathlib import Path

from pydantic import BaseModel


class AudioTrackAttributes(BaseModel):
    """Attributes"""

    AltCommentary: bool
    Commentary: bool
    Default: bool
    Normal: bool
    Secondary: bool
    VisuallyImpaired: bool


class AudioTrack(BaseModel):
    """AudioList"""

    Attributes: AudioTrackAttributes
    BitRate: int
    ChannelCount: int
    ChannelLayout: int
    ChannelLayoutName: str
    Codec: int
    CodecName: str
    CodecParam: int
    Description: str
    LFECount: int
    Language: str
    LanguageCode: str
    SampleRate: int
    TrackNumber: int


class Duration(BaseModel):
    """Duration"""

    Hours: int
    Minutes: int
    Seconds: int
    Ticks: int


class Chapter(BaseModel):
    """ChapterList"""

    Duration: Duration
    Name: str


class Color(BaseModel):
    """Color"""

    ChromaLocation: int
    Format: int
    Matrix: int
    Primary: int
    Range: int
    Transfer: int


class FrameRate(BaseModel):
    """FrameRate"""

    Den: int
    Num: int


class PixelAspectRatio(BaseModel):
    """PAR"""

    Den: int
    Num: int


class Geometry(BaseModel):
    """Geometry"""

    Height: int
    PAR: PixelAspectRatio
    Width: int


class SubtitleAttributes(BaseModel):
    """Attributes"""

    FourByThree: bool
    Children: bool
    ClosedCaption: bool
    Commentary: bool
    Default: bool
    Forced: bool
    Large: bool
    Letterbox: bool
    Normal: bool
    PanScan: bool
    Wide: bool

    def __init__(self, *args, **kwargs) -> None:
        _four_by = kwargs.pop("4By3", None)
        if _four_by is not None:
            kwargs.update({"FourByThree": _four_by})
        super().__init__(*args, **kwargs)


class SubtitleTrack(BaseModel):
    """SubtitleList"""

    Attributes: SubtitleAttributes
    Format: str
    Language: str
    LanguageCode: str
    Source: int
    SourceName: str
    TrackNumber: int


class HandBrakeTitle(BaseModel):
    """TitleList"""

    AngleCount: int
    AudioList: list[AudioTrack]
    ChapterList: list[Chapter]
    Color: Color
    Crop: list[int]
    Duration: Duration
    FrameRate: FrameRate
    Geometry: Geometry
    Index: int
    InterlaceDetected: bool
    LooseCrop: list[int]
    Metadata: dict
    Name: str
    Path: str
    Playlist: int
    SubtitleList: list[SubtitleTrack]
    Type: int
    VideoCodec: str

    @property
    def seconds(self) -> int:
        """
        The Duration in seconds (not including ticks)
        """

        hours = self.Duration.Hours
        minutes = self.Duration.Minutes
        seconds = self.Duration.Seconds

        return (hours * 3600) + (minutes * 60) + seconds


class HandBrakeScan(BaseModel):
    """HandBrakeScan"""

    MainFeature: int
    TitleList: list[HandBrakeTitle]

    @staticmethod
    def scan(path: Path) -> dict:
        """Scans a file with handbrake returns json"""
        cmd = ["HandBrakeCLI", "--json", "--title", "0", "--scan", "--min-duration", "0", "--input", path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        lines = proc.stdout.splitlines()
        idx = lines.index("JSON Title Set: {")
        lines[idx] = "{"
        return json.loads("\n".join(lines[idx:]))

    @classmethod
    def from_scan(cls, path: Path) -> HandBrakeScan:
        """
        Factory method from path scan
        """
        return cls(**cls.scan(path))
