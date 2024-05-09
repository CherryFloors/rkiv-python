"""
The dgmap (disc group map) module has logic that analyzes a group of discs and organizes title and lenth iformation.
This intent is to produce a manifest of disc contents that can be used when extracting titles to provide good
names. This is mainly an issue with tv shows.
"""
from __future__ import annotations

import csv
from typing import Any
from datetime import timedelta
from pathlib import Path

from pandas import DataFrame

from rkiv.inventory import ArchivedDisc
from rkiv.handbrake import HandBrakeScan
from rkiv.makemkv import MakeMKVInfo


class DiscGroupMapInfo:
    """
    General Title Info
    """

    disc_title: str
    id: int
    is_main: bool
    chapters: int
    duration: timedelta
    subtitles: int
    audio_tracks: int
    friendly_name: str
    season_prefix: str
    size_bytes: int

    def __init__(
        self,
        disc_title: str,
        id: int,
        is_main: bool,
        chapters: int,
        duration: timedelta,
        subtitles: int,
        audio_tracks: int,
        friendly_name: str,
        season_prefix: str,
        size_bytes: int,
    ) -> None:
        self.disc_title = disc_title
        self.id = id
        self.is_main = is_main
        self.chapters = chapters
        self.duration = duration
        self.subtitles = subtitles
        self.audio_tracks = audio_tracks
        self.friendly_name = friendly_name
        self.season_prefix = season_prefix
        self.size_bytes = size_bytes

    def __eq__(self, o: object) -> bool:
        """__eq__"""

        if not isinstance(o, DiscGroupMapInfo):
            return NotImplemented

        comparisons = (
            self.chapters == o.chapters,
            abs(self.duration.total_seconds() - o.duration.total_seconds()) <= 1,
            self.subtitles == o.subtitles,
            self.audio_tracks == o.audio_tracks,
        )

        return all(comparisons)

    @classmethod
    def from_handbrake_scan(cls, handbrake: HandBrakeScan) -> list[DiscGroupMapInfo]:
        """
        Create from a handbrake scan
        """

        _tinfos = []
        for title in handbrake.TitleList:
            _id = title.Index
            _is_main = _id == handbrake.MainFeature
            _chapters = len(title.ChapterList)
            _duration = timedelta(
                hours=title.Duration.Hours, minutes=title.Duration.Minutes, seconds=title.Duration.Seconds
            )
            _subtitles = len(title.SubtitleList)
            _audio_tracks = len(title.AudioList)

            _tinfos.append(
                cls(
                    id=_id,
                    is_main=_is_main,
                    chapters=_chapters,
                    duration=_duration,
                    subtitles=_subtitles,
                    audio_tracks=_audio_tracks,
                )
            )

        return _tinfos

    @classmethod
    def from_makemkv_scan(cls, makemkv: MakeMKVInfo) -> list[DiscGroupMapInfo]:
        """
        Create from a makemkv scan
        """

        _tinfos = []
        for title in makemkv.titles:
            _id = title.id
            _is_main = False
            _chapters = title.chapters
            _duration = title.length
            _subtitles = len(title.subtitle_streams)
            _audio_tracks = len(title.audio_streams)

            _tinfos.append(
                cls(
                    id=_id,
                    is_main=_is_main,
                    chapters=_chapters,
                    duration=_duration,
                    subtitles=_subtitles,
                    audio_tracks=_audio_tracks,
                )
            )

        return _tinfos

    def to_dict(self) -> dict[str, Any]:
        """
        convert to a dictionary
        """

        return {
            "id": self.id,
            "is_main": int(self.is_main),
            "chapters": self.chapters,
            "duration": str(self.duration),
            "subtitles": self.subtitles,
            "audio_tracks": self.audio_tracks,
        }

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> DiscGroupMapInfo:
        """
        convert to a dictionary
        """
        _id = int(obj.get("id", -1))
        _is_main = bool(int(obj.get("is_main", 0)))
        _chapters = int(obj.get("chapters", -1))
        _duration = obj.get("duration", "0:0:0")
        _subtitles = int(obj.get("subtitles", -1))
        _audio_tracks = int(obj.get("audio_tracks", -1))

        h, m, s = _duration.split(":")
        _duration = timedelta(hours=int(h), minutes=int(m), seconds=int(s))

        return cls(
            id=_id,
            is_main=_is_main,
            chapters=_chapters,
            duration=_duration,
            subtitles=_subtitles,
            audio_tracks=_audio_tracks,
        )

    @classmethod
    def blank(cls) -> DiscGroupMapInfo:
        """
        Blank title info to fill in mismatches
        """
        return cls(
            id=-1,
            is_main=False,
            chapters=-1,
            duration=timedelta(seconds=0),
            subtitles=-1,
            audio_tracks=-1,
        )


# class DiscGroupMapInfo:
#     """
#     Holds matching title info objects
#     """
#
#     disc_title: str
#     handbrake: TitleInfo
#     makemkv: TitleInfo
#     friendly_name: str
#
#     def __init__(
#         self,
#         disc_title: str,
#         handbrake: TitleInfo,
#         makemkv: TitleInfo,
#         friendly_name: str,
#     ) -> None:
#         self.disc_title = disc_title
#         self.handbrake = handbrake
#         self.makemkv = makemkv
#         self.friendly_name = friendly_name
#
#     @classmethod
#     def match_title_info(
#         cls, disc_title: str, handbrake: list[TitleInfo], makemkv: list[TitleInfo], friendly_name: str
#     ) -> list[DiscGroupMapInfo]:
#         """
#         Zip up some tinfos
#         """
#
#         dgmap_infos = []
#         for makemkv_info in makemkv:
#             handbrake_match = TitleInfo.blank()
#             matching_idx = next((i for i, v in enumerate(handbrake) if v == makemkv_info), None)
#
#             if matching_idx is not None:
#                 handbrake_match = handbrake.pop(matching_idx)
#
#             dgmap_infos.append(
#                 cls(disc_title=disc_title, handbrake=handbrake_match, makemkv=makemkv_info, friendly_name=friendly_name)
#             )
#
#         for handbrake_info in handbrake:
#             dgmap_infos.append(
#                 cls(
#                     disc_title=disc_title,
#                     handbrake=handbrake_info,
#                     makemkv=TitleInfo.blank(),
#                     friendly_name=friendly_name,
#                 )
#             )
#
#         return dgmap_infos
#
#     def to_split_dict(self) -> dict[str, Any]:
#         """
#         Returns a dictionary with two keys 'handbrake' and 'makemkv'
#         """
#
#         handbrake = {"disc_title": self.disc_title, **self.handbrake.to_dict(), "friendly_name": self.friendly_name}
#         makemkv = {"disc_title": self.disc_title, **self.makemkv.to_dict(), "friendly_name": self.friendly_name}
#
#         return {
#             "handbrake": handbrake,
#             "makemkv": makemkv,
#         }
#
#     @classmethod
#     def from_split_dict(cls, obj: dict[str, Any]) -> DiscGroupMapInfo:
#         """
#         From it
#         """
#
#         _handbrake = TitleInfo.from_dict(obj["handbrake"])
#         _makemkv = TitleInfo.from_dict(obj["makemv"])
#
#         return cls(
#             disc_title=obj["makemkv"]["disc_title"],
#             handbrake=_handbrake,
#             makemkv=_makemkv,
#             friendly_name=["makemkv"]["friendly_name"],
#         )
#
#     def to_flat_dict(self) -> dict[str, Any]:
#         """
#         Returns a flat dictionary with handbrake_ and makemkv_ prefixed to the title info attrs
#         """
#
#         _handbrake = self.handbrake.to_dict()
#         _makemkv = self.makemkv.to_dict()
#
#         _flat = {}
#         _keys = TitleInfo.__annotations__.keys()
#         for k in _keys:
#             _flat[f"makemkv_{k}"] = _makemkv.get(k, None)
#             _flat[f"handbrake_{k}"] = _handbrake.get(k, None)
#
#         return {"disc_title": self.disc_title, **_flat, "friendly_name": self.friendly_name}
#
#     @classmethod
#     def from_flat_dict(cls, obj: dict[str, Any]) -> DiscGroupMapInfo:
#         """
#         From it
#         """
#
#         handbrake_dict = {k.replace("handbrake_", ""): v for k, v in obj.items() if "handbrake_" in k}
#         _handbrake = TitleInfo.from_dict(handbrake_dict)
#
#         makemkv_dict = {k.replace("makemkv_", ""): v for k, v in obj.items() if "makemkv_" in k}
#         _makemkv = TitleInfo.from_dict(makemkv_dict)
#
#         return cls(
#             disc_title=obj["disc_title"],
#             handbrake=_handbrake,
#             makemkv=_makemkv,
#             friendly_name=obj["friendly_name"],
#         )


class DiscGroupMap:
    """
    Holds title info for all discs in a disc group
    """

    group_name: str
    dgmap_info: list[DiscGroupMapInfo]

    def __init__(
        self,
        group_name: str,
        dgmap_info: list[DiscGroupMapInfo],
    ) -> None:
        self.group_name = group_name
        self.dgmap_info = dgmap_info

    @classmethod
    def from_dir(cls, path: Path) -> DiscGroupMap:
        """
        from dir
        """

        _dgmap_info = []
        group_discs = ArchivedDisc.walk_disc_archive(path)
        group_discs.sort(key=lambda disc: disc.disc_name)

        for disc in group_discs:
            print(disc.path)
            handbrake_scan = DiscGroupMapInfo.from_handbrake_scan(HandBrakeScan.from_scan(disc.path))
            makemkv_scan = DiscGroupMapInfo.from_makemkv_scan(MakeMKVInfo.scan_disc(disc.path))

            _dgmap_info += DiscGroupMapInfo.match_title_info(
                disc_title=disc.disc_name,
                handbrake=handbrake_scan,
                makemkv=makemkv_scan,
                friendly_name="",
            )

        return cls(
            group_name=path.stem,
            dgmap_info=_dgmap_info,
        )

    def to_dataframe(self) -> DataFrame:
        """
        to a dataframe
        """
        _dgmap_info = [{"group_name": self.group_name, **i.to_flat_dict()} for i in self.dgmap_info]
        return DataFrame(_dgmap_info)

    def to_csv(self, path: Path) -> None:
        """
        Writes a csv
        """

        _dgmap_info = [{"group_name": self.group_name, **i.to_flat_dict()} for i in self.dgmap_info]
        _fieldnames = list(_dgmap_info[0].keys())

        with open(path, "w") as f:
            writer = csv.DictWriter(f, fieldnames=_fieldnames)
            writer.writeheader()
            writer.writerows(_dgmap_info)

    @classmethod
    def read_csv(cls, path: Path) -> DiscGroupMap:
        """
        Writes a csv
        """

        _group_name = ""
        _dgmap_info = []

        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                _group_name = row.pop("group_name")
                _dgmap_info.append(DiscGroupMapInfo.from_flat_dict(row))

        return cls(
            group_name=_group_name,
            dgmap_info=_dgmap_info,
        )
