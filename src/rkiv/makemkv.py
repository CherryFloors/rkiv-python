""" Wrapper module for MakeMKV """
import requests
import subprocess
from enum import Enum
from typing import List
from html.parser import HTMLParser
from datetime import timedelta
from pathlib import Path

from rkiv.inventory import ArchivedDisc
from rkiv.config import Config

CONFIG = Config()


class MakeMKVBetaKeyParser(HTMLParser):
    key: str = ""
    data: List[str] = []

    def handle_data(self, data: str) -> None:
        self.data.append(data)
        if "T-" in data:
            self.key = data

    def scrape_reg_key(self) -> str:
        page = requests.get("https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053")
        self.feed(page.content.decode("utf-8"))
        return self.key


def extract_mkv(disc: ArchivedDisc, location: Path, title: int) -> None:
    """
    Extracts mkv of the title to the location provided
    """
    _output = location.joinpath(disc.title)
    if _output.exists():
        print(f"ERROR: Output path exists skipping title - {disc.title} - {title}")
        return None
    _output.mkdir(parents=True)
    log_file = (
        CONFIG.workspace.parent.joinpath("logs")
        .joinpath("extract_mkv")
        .joinpath(disc.title)
        .with_suffix(".log")
    )
    log_file.parent.mkdir(parents=True, exist_ok=True)

    _args = ["makemkvcon", "-r", "mkv", f"file:{disc.path}", str(title), str(_output)]
    out = subprocess.run(args=_args, capture_output=True)
    stdout = out.stdout.decode().splitlines()
    stderr = out.stderr.decode().splitlines()

    err = [i for i in stdout if "error" in i.lower() or "fail" in i.lower()]
    err += [i for i in stderr if "error" in i.lower() or "fail" in i.lower()]
    with open(log_file, "w") as f:
        f.writelines(stdout + stderr)

    if len(err) != 0:
        print(f"ERROR: Problems detected in MakeMKV log - {disc.title} - {title}")
        for e in err:
            print(f"  {e}")

    contents = list(_output.iterdir())
    if len(contents) != 1:
        print(
            f"ERROR: Output directory has {len(contents)} files - {disc.title} - {title}"
        )

    file_name = _output.joinpath(disc.title).with_suffix(contents[0].suffix)
    contents[0].rename(file_name)


class AspectRatio(str, Enum):
    """AspectRatio"""

    FULL = "4:3"
    WIDE = "16:9"


class TitelInfoMMKV:
    """TitelInfoMMKV"""

    id: int
    size_bytes: int
    size_GB: float
    chapters: int
    streams: int
    aspect_ratio: AspectRatio
    length: timedelta

    def __init__(
        self,
        id: int,
        size_bytes: int,
        size_GB: float,
        chapters: int,
        streams: int,
        aspect_ratio: AspectRatio,
        length: timedelta,
    ) -> None:
        self.id = id
        self.size_bytes = size_bytes
        self.size_GB = size_GB
        self.chapters = chapters
        self.streams = streams
        self.aspect_ratio = aspect_ratio
        self.length = length

    def __eq__(self, other: object) -> bool:
        """__eq__"""
        if not isinstance(other, TitelInfoMMKV):
            return NotImplemented

        return self.length == other.length

    def __lt__(self, other: object) -> bool:
        """__lt__"""
        if not isinstance(other, TitelInfoMMKV):
            return NotImplemented

        return self.length < other.length

    def __le__(self, other: object) -> bool:
        """__le__"""
        if not isinstance(other, TitelInfoMMKV):
            return NotImplemented

        return self.length <= other.length

    def __gt__(self, other: object) -> bool:
        """__gt__"""
        if not isinstance(other, TitelInfoMMKV):
            return NotImplemented

        return self.length > other.length

    def __ge__(self, other: object) -> bool:
        """__ge__"""
        if not isinstance(other, TitelInfoMMKV):
            return NotImplemented

        return self.length >= other.length

    @staticmethod
    def bubble_sort(l: list["TitelInfoMMKV"]) -> None:
        end = len(l)
        for i in range(end - 1):
            for j in range(end - 1 - i):
                if l[j].length > l[j + 1].length:
                    tmp = l[j]
                    l[j] = l[j + 1]
                    l[j + 1] = tmp

        return None

    @classmethod
    def from_mkvinfo(cls, info: list[str]) -> "TitelInfoMMKV":
        splits = [i.split(",") for i in info]
        tinfo = {i[1]: i[3].replace('"', "") for i in splits if "TINFO" in i[0]}
        sinfo = {
            f"{i[1]}{i[2]}": i[4].replace('"', "") for i in splits if "SINFO" in i[0]
        }

        _id = int(info[0].split(":")[1].split(",")[0])
        _size_bytes = int(tinfo["11"])
        _aspect = AspectRatio.FULL
        if f"{0}20" in sinfo.keys():
            _aspect = AspectRatio(sinfo[f"{0}20"])
        h, m, s = tinfo["9"].split(":")
        _length = timedelta(
            hours=float(h),
            minutes=float(m),
            seconds=float(s),
        )
        _chapters = 0
        if "8" in tinfo.keys():
            _chapters = int(tinfo["8"])

        return cls(
            id=_id,
            size_bytes=_size_bytes,
            size_GB=_size_bytes / (1024**3),
            chapters=_chapters,
            streams=len({i.split(",")[1] for i in info if "SINFO" in i}),
            aspect_ratio=_aspect,
            length=_length,
        )

    @classmethod
    def parse_info(cls, info: list[str]) -> list["TitelInfoMMKV"]:
        filtered_list = [i for i in info if "TINFO" in i or "SINFO" in i]
        by_id: dict[str, list[str]] = {}

        for i in filtered_list:
            _id = i.split(":")[1].split(",")[0]

            if not _id in by_id.keys():
                by_id[_id] = []

            by_id[_id].append(i)

        return [cls.from_mkvinfo(v) for _, v in by_id.items()]


class MakeMKV:
    @classmethod
    def _compare_times(cls, tLineA: TitelInfoMMKV, tLineB: TitelInfoMMKV):
        # Sort A and B to wide and full
        if tLineA.aspect_ratio == AspectRatio.FULL:
            tLineFull = tLineA
            tLineWide = tLineB
        else:
            tLineFull = tLineB
            tLineWide = tLineA
        # Get time diff
        diff = abs(tLineA.length.total_seconds() - tLineB.length.total_seconds()) / 60
        # Return based on diff
        if diff < 10:
            return tLineWide
        else:
            return tLineFull

    @classmethod
    def get_main_title(cls, disc: ArchivedDisc) -> TitelInfoMMKV:
        _args = [
            "makemkvcon",
            "-r",
            "--noscan",
            # "--minlength=1",  # Keep at 120 until we do full rips
            "info",
            f"file:{disc.path}",
        ]
        out = subprocess.run(args=_args, capture_output=True)

        tInfo = out.stdout.decode().splitlines()

        title_list = TitelInfoMMKV.parse_info(tInfo)
        t0 = title_list[0]
        if len(title_list) > 20:
            print(f"WARNING: {disc.title} has high title count: {len(title_list)}")

        title_list = [i for i in title_list if i.chapters > 0]
        if len(title_list) == 0:
            print(f"ERROR: {disc.title} has no titles with chapters")
            return t0

        TitelInfoMMKV.bubble_sort(title_list)
        full = [i for i in title_list if i.aspect_ratio == AspectRatio.FULL]
        wide = [i for i in title_list if i.aspect_ratio == AspectRatio.WIDE]

        if len(wide) == 0:
            return full[-1]

        if len(full) == 0:
            return wide[-1]

        max_full = full[-1]
        max_wide = wide[-1]
        main = max(max_full, max_wide)
        if main.aspect_ratio == AspectRatio.FULL:
            main = cls._compare_times(max_full, max_wide)
            print(
                f"WARNING: {main.id} {main.length} {main.aspect_ratio} - 16:9_Over_rule - {max_full.id} {max_full.length} {max_full.aspect_ratio}"
            )
        return main
