import os
import json
from typing import List
from dataclasses import dataclass
from pathlib import Path


def _resolve_path(path: str) -> Path:
    return Path(os.path.expanduser(path=path))


def _user_config_dir() -> Path:
    return Path.home().joinpath(".config")


def _rkiv_dir() -> Path:
    return _user_config_dir().joinpath("rkiv")


@dataclass
class Config:
    """rkiv runtime config opbject"""

    __slots__ = (
        "workspace",
        "music_rip_dir",
        "video_rip_dir",
        "itunes_dir",
        "mpd_dir",
        "abcde_config",
        "video_archives",
        "video_streams",
        "audio_streams",
    )

    workspace: Path
    music_rip_dir: Path
    video_rip_dir: Path
    itunes_dir: Path
    mpd_dir: Path
    abcde_config: Path
    video_archives: List[Path]
    video_streams: List[Path]
    audio_streams: List[Path]

    __annotations__ = {
        "workspace": Path,
        "music_rip_dir": Path,
        "video_rip_dir": Path,
        "itunes_dir": Path,
        "mpd_dir": Path,
        "abcde_config": Path,
        "video_archives": List[Path],
        "video_streams": List[Path],
        "audio_streams": List[Path],
    }

    def _overrides(self, conf: dict) -> None:
        """apply overrides from conf"""

        if conf.get("workspace"):
            setattr(self, "workspace", _resolve_path(conf.get("workspace")))

        if conf.get("music_rip_dir"):
            setattr(self, "music_rip_dir", _resolve_path(conf.get("music_rip_dir")))

        if conf.get("video_rip_dir"):
            setattr(self, "video_rip_dir", _resolve_path(conf.get("video_rip_dir")))

        if conf.get("itunes_dir"):
            setattr(self, "itunes_dir", _resolve_path(conf.get("itunes_dir")))

        if conf.get("mpd_dir"):
            setattr(self, "mpd_dir", _resolve_path(conf.get("mpd_dir")))

        if conf.get("abcde_config"):
            setattr(self, "abcde_config", _resolve_path(conf.get("abcde_config")))

        if conf.get("video_archives"):
            setattr(
                self,
                "video_archives",
                [_resolve_path(i) for i in conf.get("video_archives")],
            )

        if conf.get("video_streams"):
            setattr(
                self,
                "video_streams",
                [_resolve_path(i) for i in conf.get("video_streams")],
            )

        if conf.get("audio_streams"):
            setattr(
                self,
                "audio_streams",
                [_resolve_path(i) for i in conf.get("audio_streams")],
            )

    def __init__(self, load: bool = True) -> None:
        self.workspace = _rkiv_dir().joinpath("temp")
        self.music_rip_dir = Path.home().joinpath("Music")
        self.video_rip_dir = Path.home().joinpath("Videos")
        self.itunes_dir = Path.home().joinpath("Music/iTunes")
        self.mpd_dir = _user_config_dir().joinpath("mpd")
        self.abcde_config = _rkiv_dir().joinpath("abcde.conf")
        self.video_archives = [Path.home().joinpath("Archive")]
        self.video_streams = [Path.home().joinpath("Music")]
        self.audio_streams = [Path.home().joinpath("Videos")]

        if load:
            conf_path = _rkiv_dir().joinpath("rkiv.json")
            if conf_path.exists():
                with conf_path.open("r") as f:
                    conf = json.load(f)
                self._overrides(conf=conf)
