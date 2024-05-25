""" Wrapper module for MakeMKV """
from __future__ import annotations
import requests
import subprocess
import os
import tempfile
from enum import Enum
from typing import List, Callable
from html.parser import HTMLParser
from datetime import timedelta
from pathlib import Path
from csv import reader
from asyncio.streams import StreamReader
import asyncio

from rkiv.arm import UserInput
from rkiv.opticaldevices import OpticalDrive
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

    def set_reg_key(self) -> int:
        proc = subprocess.run(["makemkvcon", "reg", self.key], capture_output=False)
        return proc.returncode


def extract_mkv(disc: ArchivedDisc, location: Path, title: int) -> None:
    """
    Extracts mkv of the title to the location provided
    """
    _output = location.joinpath(disc.title)
    if _output.exists():
        print(f"ERROR: Output path exists skipping title - {disc.title} - {title}")
        return None
    _output.mkdir(parents=True)
    log_file = CONFIG.workspace.parent.joinpath("logs").joinpath("extract_mkv").joinpath(disc.title).with_suffix(".log")
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
        print(f"ERROR: Output directory has {len(contents)} files - {disc.title} - {title}")

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
    def bubble_sort(l: list[TitelInfoMMKV]) -> None:
        end = len(l)
        for i in range(end - 1):
            for j in range(end - 1 - i):
                if l[j].length > l[j + 1].length:
                    tmp = l[j]
                    l[j] = l[j + 1]
                    l[j + 1] = tmp

        return None

    @classmethod
    def from_mkvinfo(cls, info: list[str]) -> TitelInfoMMKV:
        splits = [i.split(",") for i in info]
        tinfo = {i[1]: i[3].replace('"', "") for i in splits if "TINFO" in i[0]}
        sinfo = {f"{i[1]}{i[2]}": i[4].replace('"', "") for i in splits if "SINFO" in i[0]}

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
    def parse_info(cls, info: list[str]) -> list[TitelInfoMMKV]:
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


class VideoStreamInfo:
    id: int
    title_id: int
    codec: str
    codec_friendly: str
    resolution: str
    aspect_ratio: str
    bitrate: str
    frame_rate: str
    stream_name: str

    def __init__(
        self,
        id: int,
        title_id: int,
        codec: str,
        codec_friendly: str,
        resolution: str,
        aspect_ratio: str,
        bitrate: str,
        frame_rate: str,
        stream_name: str,
    ) -> None:
        self.id = id
        self.title_id = title_id
        self.codec = codec
        self.codec_friendly = codec_friendly
        self.resolution = resolution
        self.aspect_ratio = aspect_ratio
        self.bitrate = bitrate
        self.frame_rate = frame_rate
        self.stream_name = stream_name

    @classmethod
    def from_csv_list(cls, sinfo: list[str]) -> VideoStreamInfo:
        """
        Returns a TitleInfo class by parsing a list of TINFO lines:
        "id,code,value,strin_value" <- TINFO: has been stripped
        """
        _id = int(sinfo[0].split(",")[1])
        _title_id = int(sinfo[0].split(",")[0])
        _codec = ""
        _codec_friendly = ""
        _resolution = ""
        _aspect_ratio = ""
        _bitrate = ""
        _frame_rate = ""
        _stream_name = ""

        for line in reader(sinfo):
            tid, sid, code, vcode, value = line
            value = value.strip('"')

            if code == "6":
                _codec = value

            if code == "7":
                _codec_friendly = value

            if code == "13":
                _bitrate = value

            if code == "19":
                _resolution = value

            if code == "20":
                _aspect_ratio = value

            if code == "21":
                _frame_rate = value

            if code == "30":
                _stream_name = value

        return cls(
            id=_id,
            title_id=_title_id,
            codec=_codec,
            codec_friendly=_codec_friendly,
            resolution=_resolution,
            aspect_ratio=_aspect_ratio,
            bitrate=_bitrate,
            frame_rate=_frame_rate,
            stream_name=_stream_name,
        )


class AudioStreamInfo:
    id: int
    title_id: int
    channels_friendly: str
    language_code: str
    language_name: str
    codec: str
    codec_friendly: str
    bitrate: str
    channels: str
    sample_rate: str
    bit_depth: str
    stream_name: str

    def __init__(
        self,
        id: int,
        title_id: int,
        channels_friendly: str,
        language_code: str,
        language_name: str,
        codec: str,
        codec_friendly: str,
        bitrate: str,
        channels: str,
        sample_rate: str,
        bit_depth: str,
        stream_name: str,
    ) -> None:
        self.id = id
        self.title_id = title_id
        self.channels_friendly = channels_friendly
        self.language_code = language_code
        self.language_name = language_name
        self.codec = codec
        self.codec_friendly = codec_friendly
        self.bitrate = bitrate
        self.channels = channels
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.stream_name = stream_name

    @classmethod
    def from_csv_list(cls, sinfo: list[str]) -> AudioStreamInfo:
        """
        Returns a TitleInfo class by parsing a list of TINFO lines:
        "id,code,value,strin_value" <- TINFO: has been stripped
        """

        _id = int(sinfo[0].split(",")[1])
        _title_id = int(sinfo[0].split(",")[0])
        _channels_friendly = ""
        _language_code = ""
        _language_name = ""
        _codec = ""
        _codec_friendly = ""
        _bitrate = ""
        _channels = ""
        _sample_rate = ""
        _bit_depth = ""
        _stream_name = ""

        for line in reader(sinfo):
            tid, sid, code, vcode, value = line
            value = value.strip('"')

            if code == "2":
                _channels_friendly = value

            if code == "3":
                _language_code = value

            if code == "4":
                _language_name = value

            if code == "6":
                _codec = value

            if code == "7":
                _codec_friendly = value

            if code == "13":
                _bitrate = value

            if code == "14":
                _channels = value

            if code == "17":
                _sample_rate = value

            if code == "18":
                _bit_depth = value

            if code == "30":
                _stream_name = value

        return cls(
            id=_id,
            title_id=_title_id,
            channels_friendly=_channels_friendly,
            language_code=_language_code,
            language_name=_language_name,
            codec=_codec,
            codec_friendly=_codec_friendly,
            bitrate=_bitrate,
            channels=_channels,
            sample_rate=_sample_rate,
            bit_depth=_bit_depth,
            stream_name=_stream_name,
        )


class SubtitleStreamInfo:
    id: int
    title_id: int
    language_code: str
    language_name: str
    codec: str
    codec_friendly: str
    stream_name: str

    def __init__(
        self,
        id: int,
        title_id: int,
        language_code: str,
        language_name: str,
        codec: str,
        codec_friendly: str,
        stream_name: str,
    ) -> None:
        self.id = id
        self.title_id = title_id
        self.language_code = language_code
        self.language_name = language_name
        self.codec = codec
        self.codec_friendly = codec_friendly
        self.stream_name = stream_name

    @classmethod
    def from_csv_list(cls, sinfo: list[str]) -> SubtitleStreamInfo:
        """
        Returns a TitleInfo class by parsing a list of TINFO lines:
        "id,code,value,strin_value" <- TINFO: has been stripped
        """

        _id = int(sinfo[0].split(",")[1])
        _title_id = int(sinfo[0].split(",")[0])
        _language_code = ""
        _language_name = ""
        _codec = ""
        _codec_friendly = ""
        _stream_name = ""

        for line in reader(sinfo):
            tid, sid, code, vcode, value = line
            value = value.strip('"')

            if code == "3":
                _language_code = value

            if code == "4":
                _language_name = value

            if code == "6":
                _codec = value

            if code == "7":
                _codec_friendly = value

            if code == "30":
                _stream_name = value

        return cls(
            id=_id,
            title_id=_title_id,
            language_code=_language_code,
            language_name=_language_name,
            codec=_codec,
            codec_friendly=_codec_friendly,
            stream_name=_stream_name,
        )


class MakeMKVTitleInfo:
    id: int
    video_streams: tuple[VideoStreamInfo, ...]
    audio_streams: tuple[AudioStreamInfo, ...]
    subtitle_streams: tuple[SubtitleStreamInfo, ...]
    chapters: int
    source_file: str
    export_name: str
    size_bits: int
    length: timedelta

    def __init__(
        self,
        id: int,
        video_streams: tuple[VideoStreamInfo, ...],
        audio_streams: tuple[AudioStreamInfo, ...],
        subtitle_streams: tuple[SubtitleStreamInfo, ...],
        chapters: int,
        source_file: str,
        export_name: str,
        size_bits: int,
        length: timedelta,
    ) -> None:
        self.id = id
        self.video_streams = video_streams
        self.audio_streams = audio_streams
        self.subtitle_streams = subtitle_streams
        self.chapters = chapters
        self.source_file = source_file
        self.export_name = export_name
        self.size_bits = size_bits
        self.length = length

    @classmethod
    def from_csv_lists(cls, tinfo: list[str], sinfo: list[str]) -> MakeMKVTitleInfo:
        """
        Returns a TitleInfo class by parsing a list of TINFO and SINFO lines:
        "id,code,value,strin_value" <- TINFO: has been stripped
        """

        _id = int(tinfo[0].split(",")[0])
        streams: dict[str, list[list[str]]] = {"Video": [], "Audio": [], "Subtitles": []}
        temp_sinfo: list[str] = []
        stype = None

        for line in reader(sinfo):
            tid, sid, code, vcode, value = line
            value = value.strip('"')

            if code == "1" and stype is None:
                stype = value

            if code == "1" and len(temp_sinfo) > 0 and stype is not None:
                streams[stype].append(temp_sinfo)
                temp_sinfo = []
                stype = value

            temp_sinfo.append(",".join(line))

        _video_streams = tuple(VideoStreamInfo.from_csv_list(i) for i in streams["Video"])
        _audio_streams = tuple(AudioStreamInfo.from_csv_list(i) for i in streams["Audio"])
        _subtitle_streams = tuple(SubtitleStreamInfo.from_csv_list(i) for i in streams["Subtitles"])

        _chapters = 0
        _source_file = ""
        _export_name = ""
        _size_bits = 0
        _length = timedelta(seconds=0)

        for csv in reader(tinfo):
            id, code, _, value = csv
            value = value.strip('"')

            if code == "8":
                _chapters = int(value)

            if code == "16":
                _source_file = value

            if code == "27":
                _export_name = value

            if code == "11":
                _size_bits = int(value)

            if code == "9":
                h, m, s = value.split(":")
                _length = timedelta(
                    hours=float(h),
                    minutes=float(m),
                    seconds=float(s),
                )

        return cls(
            id=_id,
            video_streams=_video_streams,
            audio_streams=_audio_streams,
            subtitle_streams=_subtitle_streams,
            chapters=_chapters,
            source_file=_source_file,
            export_name=_export_name,
            size_bits=_size_bits,
            length=_length,
        )


class MakeMKVInfo:
    """
    Optical video disc info provided by makemkv
    """

    name: str
    title_count: int
    disc_type: str
    titles: tuple[MakeMKVTitleInfo, ...]
    length_titles: timedelta
    gigabytes_titles: float

    def __init__(
        self,
        name: str,
        title_count: int,
        disc_type: str,
        titles: tuple[MakeMKVTitleInfo, ...],
        length_titles: timedelta,
        gigabytes_titles: float,
    ) -> None:
        self.name = name
        self.title_count = title_count
        self.disc_type = disc_type
        self.titles = titles
        self.length_titles = length_titles
        self.gigabytes_titles = gigabytes_titles

    @classmethod
    def from_info(cls, info: str) -> MakeMKVInfo:
        """
        Returns a TitleInfo class by parsing a list of TINFO lines:
        "id,code,value,strin_value" <- TINFO: has been stripped
        """
        _titles = []
        build_title = False

        info_lines = info.splitlines()
        tinfo: list[str] = []
        sinfo: list[str] = []

        _name = ""
        _title_count = 0
        _disc_type = ""

        for line in info_lines:
            key, _, csv = line.partition(":")
            if key == "TCOUNT":
                _title_count = int(csv)

            if key == "CINFO":
                id, code, value = csv.split(",")
                if id == "1":
                    _disc_type = value

                if id == "2":
                    _name = value.strip('"')

            if key == "TINFO" and build_title:
                _titles.append(MakeMKVTitleInfo.from_csv_lists(tinfo, sinfo))
                tinfo = []
                sinfo = []
                build_title = False

            if key == "TINFO":
                tinfo.append(csv)

            if key == "SINFO":
                build_title = True
                sinfo.append(csv)

        _titles.append(MakeMKVTitleInfo.from_csv_lists(tinfo, sinfo))

        return cls(
            name=_name,
            title_count=_title_count,
            disc_type=_disc_type,
            titles=tuple(_titles),
            length_titles=sum([i.length for i in _titles], timedelta()),
            gigabytes_titles=sum(i.size_bits for i in _titles) / (1024**3),
        )

    @classmethod
    def scan_disc(cls, disc: Path | ArchivedDisc | OpticalDrive) -> MakeMKVInfo:
        _args = ["makemkvcon", "--noscan", "--minlength=0", "-r", "info"]

        if isinstance(disc, Path):
            _args.append(f"file:{disc}")

        if isinstance(disc, ArchivedDisc):
            _args.append(f"file:{disc.path}")

        if isinstance(disc, OpticalDrive):
            _args.append(f"dev:{disc.device_path}")

        proc = subprocess.run(args=_args, capture_output=True, text=True)
        return cls.from_info(proc.stdout)


class MakeMKVRipper:
    """
    Use makemkv to rip stuff
    """

    stage: str
    progress: float
    drive: OpticalDrive
    progress_callback: Callable[[OpticalDrive, float], None]

    def __init__(
        self, stage: str, progress: float, drive: OpticalDrive, progress_callback: Callable[[OpticalDrive, float], None]
    ) -> None:
        self.stage = stage
        self.progress = progress
        self.drive = drive
        self.progress_callback = progress_callback

    async def update_progress(self, stderr: StreamReader) -> None:
        """
        Update the progress of the running process
        """

        while True:
            buffer = await stderr.readline()
            if not buffer:
                break

            line = buffer.rstrip(b"\n").decode()
            code, _, csv = line.partition(":")
            if code == "PRGV":
                _, total, max = csv.split(",")
                self.progress = float(total) / float(max)
                self.progress_callback(self.drive, self.progress)

    async def extract(self, input: UserInput, drive: OpticalDrive) -> str:
        title = input.name
        _output = CONFIG.video_rip_dir.joinpath("makemkv").joinpath(title)

        disc_suffix = f"D{str(input.disc).zfill(2)}"
        if input.season is not None:
            season_suffix = f"S{str(input.season).zfill(2)}"
            disc_suffix = f"{season_suffix}.{disc_suffix}"
            _output = _output.joinpath(f"{title}.{season_suffix}")

        disc_title = f"{input.name}.{disc_suffix}"
        _output = _output.joinpath(disc_title)

        if not _output.exists():
            _output.mkdir(parents=True)

        device = f"dev:{drive.device_path}"
        # _args = ("mkv", "-r", "--noscan", "--messages=msg.log", "--progress=-stderr", "dev:/dev/sr1", "all", "/home/ryan/Videos/makemkv/")
        # _args = ("mkv", "-r", "--noscan", "--progress=-stderr", device, "all", str(_output))
        _args = ("mkv", "-r", "--noscan", "--progress=-stderr", device, "all", str(_output))
        aproc = await asyncio.create_subprocess_exec(
            "makemkvcon", *_args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.gather(self.update_progress(aproc.stderr))

        out_code = await aproc.wait()
        results = await aproc.stdout.read()
        results = results.decode()

        log = CONFIG.workspace.parent.joinpath("logs").joinpath("makemkv").joinpath(title).joinpath(f"{disc_title}.log")
        if not log.parent.exists():
            log.parent.mkdir(parents=True)

        with open(log, "a") as f:
            f.write(results)

        _ = subprocess.run(["eject", str(drive.device_path)])
        return results

    # def rippper(input: UserInput, drive: OpticalDrive) -> None:


if __name__ == "__main__":
    # _args = ["makemkvcon", "mkv", "all", "--noscan", "--minlength=0", "-r", f"file:{disc}"]
    drive = OpticalDrive.get_optical_drive("sr1")
    mkvinfo = MakeMKVInfo.scan_disc(disc=drive)
