import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


def _resolve_path(path: str) -> Path:
    return Path(os.path.expanduser(path=path))


def _user_config_dir() -> Path:
    return Path.home().joinpath(".config")


def _rkiv_dir() -> Path:
    return _user_config_dir().joinpath("rkiv")


def _conf_path() -> Path:
    return _rkiv_dir().joinpath("rkiv.json")


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
        "editor",
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
    editor: Optional[Path]

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
        "editor": Optional[Path],
    }

    def _overrides(self, conf: dict) -> None:
        """apply overrides from conf"""

        _workspace = conf.get("workspace")
        if _workspace is not None:
            setattr(self, "workspace", _resolve_path(_workspace))

        _music_rip_dir = conf.get("music_rip_dir")
        if _music_rip_dir is not None:
            setattr(self, "music_rip_dir", _resolve_path(_music_rip_dir))

        _video_rip_dir = conf.get("video_rip_dir")
        if _video_rip_dir is not None:
            setattr(self, "video_rip_dir", _resolve_path(_video_rip_dir))

        _itunes_dir = conf.get("itunes_dir")
        if _itunes_dir is not None:
            setattr(self, "itunes_dir", _resolve_path(_itunes_dir))

        _mpd_dir = conf.get("mpd_dir")
        if _mpd_dir is not None:
            setattr(self, "mpd_dir", _resolve_path(_mpd_dir))

        _abcde_config = conf.get("abcde_config")
        if _abcde_config is not None:
            setattr(self, "abcde_config", _resolve_path(_abcde_config))

        _editor = conf.get("editor")
        if _editor is not None:
            setattr(self, "editor", _resolve_path(_editor))
        
        _video_archives = conf.get("video_archives")
        if _video_archives is not None:
            setattr(
                self,
                "video_archives",
                [_resolve_path(i) for i in _video_archives],
            )

        _video_streams = conf.get("video_streams")
        if _video_streams is not None:
            setattr(
                self,
                "video_streams",
                [_resolve_path(i) for i in _video_streams],
            )

        _audio_streams = conf.get("audio_streams")
        if _audio_streams is not None:
            setattr(
                self,
                "audio_streams",
                [_resolve_path(i) for i in _audio_streams],
            )

    def __init__(self, load: bool = True) -> None:
        self.workspace = _rkiv_dir().joinpath("temp")
        self.music_rip_dir = Path.home().joinpath("Music")
        self.video_rip_dir = Path.home().joinpath("Videos")
        self.itunes_dir = Path.home().joinpath("Music/iTunes")
        self.mpd_dir = _user_config_dir().joinpath("mpd")
        self.abcde_config = _rkiv_dir().joinpath("abcde.conf")
        self.video_archives = [Path.home().joinpath("Archive")]
        self.video_streams = [Path.home().joinpath("Videos")]
        self.audio_streams = [Path.home().joinpath("Music")]
        self.editor = None

        if load:
            conf_path = _conf_path()
            if conf_path.exists():
                with conf_path.open("r") as f:
                    conf = json.load(f)
                self._overrides(conf=conf)

    def __repr__(self) -> str:
        attributes = [k for k in self.__slots__]
        width = max([len(i) for i in attributes])
        s = f"Config: {str(_conf_path())}\n"
        s += "-" * len(s) + "\n"
        for k in attributes:
            v = self.__getattribute__(k)
            space = " " * (width - len(str(k)) + 2)
            if isinstance(v, list):
                extra_space = " " * (width + 2) + "    "
                end_space = len(f"  {k}{space}")
                s += f"  {k}{space}[\n"
                s += ",\n".join([extra_space + str(i) for i in v])
                s += "\n" + (end_space * " ") + "]\n"
            else:
                s += f"  {k}{space}{str(v)}\n"
        return s

    def dict(self) -> Dict[str, Any]:
        """Returns a dict representation of the object"""
        return {
            "workspace": str(self.workspace),
            "music_rip_dir": str(self.music_rip_dir),
            "video_rip_dir": str(self.video_rip_dir),
            "itunes_dir": str(self.itunes_dir),
            "mpd_dir": str(self.mpd_dir),
            "abcde_config": str(self.abcde_config),
            "video_archives": [str(i) for i in self.video_archives],
            "video_streams": [str(i) for i in self.video_streams],
            "audio_streams": [str(i) for i in self.audio_streams],
            "editor": str(self.editor),
        }

    @staticmethod
    def data_directory() -> Path:
        """Returns the data directory for rkiv"""
        return _rkiv_dir()

    @staticmethod
    def itunes_data() -> Path:
        """Returns the data directory for rkiv"""
        return _rkiv_dir().joinpath("itunes_data.dat")

    def itunes_music(self) -> Path:
        """Returns the data directory for rkiv"""
        return self.itunes_dir.joinpath("iTunes Media").joinpath("Music")

    def save(self) -> None:
        """Write the config out to disk"""

        with open(_conf_path(), "w") as f:
            f.write(json.dumps(self.dict(), indent=4))
