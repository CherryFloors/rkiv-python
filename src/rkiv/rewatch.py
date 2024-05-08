"""
TODO: The aspect ratio scaling is not right, need to improve filter complex. Should be able to ref original inputs
and grab chapter time codes and add fades.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

import click

from rkiv.handbrake import HandBrakeScan, HandBrakeTitle


class RewatchSegment:
    """
    A rewatchable segment
    """

    id: int
    source: Path
    start: int
    end: int | None
    height: int
    width: int
    fade: int = 5
    codec: str = "libx265"

    def __init__(
        self,
        id: int,
        source: Path,
        start: int,
        end: int | None,
        height: int,
        width: int,
        fade: int = 5,
        codec: str = "libx265",
    ) -> None:
        self.id = id
        self.source = source
        self.start = start
        self.end = end
        self.height = height
        self.width = width
        self.fade = fade
        self.codec = codec

    @property
    def path(self) -> Path:
        return Path.cwd().joinpath(f"rewatch-{self.id}.mp4")

    @property
    def duration(self) -> int:
        """
        Length in seconds
        """

        if self.end is None:
            return -1

        return self.end - self.start

    @property
    def video_filter(self) -> str:
        """
        Video filter
        """

        fade_in = ""
        if self.start != 0:
            fade_in = f"fade=t=in:st={self.start}:d={self.fade}"
            # fade_in = f"fade=t=in:st=0:d={self.fade}"

        fade_out = ""
        if self.end is not None:
            fade_out += f"fade=t=out:st={self.end - self.fade}:d={self.fade}"
            # fade_out += f"fade=t=out:st={self.duration - self.fade}:d={self.fade}"

        delim = ""
        if fade_in != "" and fade_out != "":
            delim = ","

        return f"{fade_in}{delim}{fade_out}"  #,scale={self.width}:{self.height}"

    @property
    def audio_filter(self) -> str:
        """
        Audio filter
        """

        fade_in = ""
        if self.start != 0:
            fade_in = f"afade=t=in:st={self.start}:d={self.fade}"
            # fade_in = f"afade=t=in:st=0:d={self.fade}"

        fade_out = ""
        if self.end is not None:
            fade_out += f"afade=t=out:st={self.end - self.fade}:d={self.fade}"
            # fade_out += f"afade=t=out:st={self.duration - self.fade}:d={self.fade}"

        delim = ""
        if fade_in != "" and fade_out != "":
            delim = ","

        return f"{fade_in}{delim}{fade_out}"

    def command(self) -> list[str]:
        """
        Command list to do the thing...
        """

        cmd = ["ffmpeg", "-i", str(self.source)]

        cmd += ["-ss", str(self.start)]
        if self.end is not None:
            cmd += ["-t", str(self.duration)]

        cmd += ["-vf", self.video_filter, "-af", self.audio_filter]
        # cmd += ["-c:v", "libx265", f"{self.id}.mkv"]
        cmd += [str(self.path)]

        return cmd

    def make(self) -> None:
        """Make the segment cut"""

        # cmd = ["ffmpeg", "-i", str(self.source), "-ss", str(self.start)]
        # if self.end is not None:
        #     cmd += ["-t", str(self.duration)]
        #
        # cmd.append(str(self.path))

        #TEMP _ = TheRewatch.run_cmd(self.command())
        assert self.path.exists()


class MovieChapterSegment:

    id: int
    path: Path

    def __init__(self, id: int, path: Path) -> None:
        self.id = id
        self.path = path


class TheRewatch:

    rewatchables_scan: HandBrakeTitle
    movie_scan: HandBrakeTitle
    movie: Path
    rewatchable: Path

    def __init__(
        self,
        rewatchables_scan: HandBrakeTitle,
        movie_scan: HandBrakeTitle,
        movie: Path,
        rewatchable: Path,
    ) -> None:
        self.rewatchables_scan = rewatchables_scan
        self.movie_scan = movie_scan
        self.movie = movie
        self.rewatchable = rewatchable

    @property
    def resolution_width(self) -> int:
        """The width of the final resolution"""
        return self.movie_scan.Geometry.Width

    @property
    def target_height(self) -> int:
        """The target height"""

        height = int((self.resolution_width / 16) * 9)
        return height - (height % 2)

    @classmethod
    def from_paths(cls, movie: Path, rewatchable: Path) -> TheRewatch:
        """
        Create a new object from two paths
        """

        _rewatchables_titles = HandBrakeScan.from_scan(rewatchable).TitleList
        assert len(_rewatchables_titles) == 1

        _movie_titles = HandBrakeScan.from_scan(movie).TitleList
        assert len(_movie_titles) == 1

        return cls(
            rewatchables_scan=_rewatchables_titles[0],
            movie_scan=_movie_titles[0],
            rewatchable=rewatchable,
            movie=movie,
        )

    def split_movie_chapters(self) -> list[MovieChapterSegment]:

        cmd = ["mkvmerge", "-o", "movie.mkv", "--split", "chapters:all", str(self.movie)]
        #TEMP self.run_cmd(cmd)
        segments = [Path(f"movie-{str(i + 1).zfill(3)}.mkv") for i, _ in enumerate(self.movie_scan.ChapterList)]

        for p in segments:
            assert p.exists()

        return [MovieChapterSegment(id=i, path=p) for i, p in enumerate(segments)]

    def build_command(self, segments: list[MovieChapterSegment | RewatchSegment]) -> str:

        cmd = ["ffmpeg"]
        for seg in segments:
            cmd += ["-i", str(seg.path)]

        filter_complex = ""
        for i, seg in enumerate(segments):
            if isinstance(seg, MovieChapterSegment):
                filter_complex += f"[{i}:v]fps=fps=film,scale=w=1920:h=1080:force_original_aspect_ratio=1,setsar=1:1,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v{i}]; "
            else:
                filter_complex += f"[{i}:v]fps=fps=film[v{i}]; "

        for i, seg in enumerate(segments):

            # # s = f"[{i}:v]"
            # s = ""
            # if isinstance(seg, RewatchSegment):
            #     s += f"[{i}]"
            #     s += f"{seg.video_filter}"
            #
            # # s += f" [{i}:a]"
            # if isinstance(seg, RewatchSegment):
            #     s += f"{seg.audio_filter}"
            #
            # s += f"{s}; "
            #
            # if not isinstance(seg, RewatchSegment):
            #     s = ""

            # filter_complex += s
            filter_complex += f"[v{i}][{i}:a] "
            # if isinstance(seg, MovieChapterSegment):
            #     filter_complex += f"[v{i}][{i}:a] "
            # else:
            #     filter_complex += f"[{i}:v][{i}:a] "

        filter_complex += f"concat=n={len(segments)}:v=1:a=1 [v] [a]"
        cmd += ["-filter_complex", filter_complex]
        cmd += ["-map", "[v]", "-map", "[a]", "-c:v", "libx264", "The_Rewatch.mp4"]

        return cmd

    def do_the_thing(self, segments: int = 4, fade: int = 5) -> None:
        """Make the rewatch"""

        max_rewatch_length = 600

        segment_length = int(self.rewatchables_scan.seconds / segments)
        if segment_length > max_rewatch_length:
            segment_length = max_rewatch_length

        offset = segment_length - fade * 2

        rewatch_segments = []
        for id in range(segments):

            start = id * offset
            end = start + segment_length
            if id == segments - 1:
                end = None

            rewatch_segments.append(
                RewatchSegment(
                    id=id,
                    source=self.rewatchable,
                    start=start,
                    end=end,
                    height=self.target_height,
                    width=self.target_height,
                )
            )

        for seg in rewatch_segments:
            seg.make()

        # Make movie segments
        movie_chapters = self.split_movie_chapters()

        # Combo
        combined = []
        stride = int(len(movie_chapters) / (len(rewatch_segments) - 1))
        combined.append(rewatch_segments.pop(0))
        last = rewatch_segments.pop(-1)
        for i, x in enumerate(rewatch_segments):
            combined += movie_chapters[(i * stride):((i + 1) * stride)]
            combined.append(x)

        combined += movie_chapters[((i + 1) * stride):]
        combined.append(last)
        # Join
        for comb in combined:
            click.echo(comb.path)

        the_big_one = self.build_command(combined)
        click.secho(the_big_one, bold=True)

        self.run_cmd(the_big_one)
        click.secho("[*] Fin", bold=True)

    @staticmethod
    def run_cmd(cmd: list[str]) -> int:
        click.secho(f"\n{cmd}\n", bold=True)
        out = subprocess.run(cmd, text=True)
        return out.returncode


if __name__ == "__main__":
    rewatch = Path("/home/ryan/Videos/rewatch/The Rewatchables: In the Line of Fire.webm")
    movie = Path("/home/ryan/Archive/Stream/movies/In_The_Line_Of_Fire/In_The_Line_Of_Fire.mkv")
    rw = TheRewatch.from_paths(movie, rewatch)
    rw.do_the_thing()

