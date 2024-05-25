import asyncio
from datetime import timedelta
from enum import Enum

import click


class OpticalDiscType(str, Enum):
    CD = "cd"
    DVD = "dvd"
    BLU_RAY = "blu_ray"


class DriveManagerState(str, Enum):
    SHUTDOWN_REQUEST = "shutdown"
    RIPPING = "ripping"
    FINISHED = "finished"
    WAITING = "waiting"

    @property
    def symbol(self) -> str:
        if self.value == DriveManagerState.SHUTDOWN_REQUEST.value:
            return click.style("X", fg="red")

        if self.value == DriveManagerState.RIPPING.value:
            return click.style("R", fg="green")

        if self.value == DriveManagerState.FINISHED.value:
            return click.style("F", fg="green")

        if self.value == DriveManagerState.WAITING.value:
            return click.style("-", fg="blue")

        raise ValueError(f"What the hell is this: {self.value}!?")


class DriveManagerStatus:
    state: DriveManagerState
    progress_fraction: float

    def __init__(self, state: DriveManagerState, progress_fraction: float) -> None:
        self.state = state
        self.progress_fraction = progress_fraction


class ARMUserInterface:
    def update(self) -> None:
        ...


class AutomatedRippingMachine:
    pass


class UserInput:
    """
    Holds user input for optical media
    """

    name: str
    season: int | None
    disc: int

    def __init__(self, name: str, season: int | None, disc: int) -> None:
        self.name = name
        self.season = season
        self.disc = disc


class UserInputRequest:
    """
    Holds information needed to prompt user
    """

    device_name: str
    label: str
    mount_location: str
    title_count: int
    length: timedelta
    gigabytes: float
    input_return_queue: asyncio.Queue[UserInput]

    def __init__(
        self,
        device_name: str,
        label: str,
        mount_location: str,
        title_count: int,
        length: timedelta,
        gigabytes: float,
        input_return_queue: asyncio.Queue[UserInput],
    ) -> None:
        self.device_name = device_name
        self.label = label
        self.mount_location = mount_location
        self.title_count = title_count
        self.length = length
        self.gigabytes = gigabytes
        self.input_return_queue = input_return_queue

    # @classmethod
    # def from_mkvinfo(cls, device_name: str, mount_location: str, mkvinfo: MakeMKVInfo) -> UserInputRequest:
    #     """
    #     Build a reques from MakeMKVInfo
    #     """
    #
    #     return cls(
    #         device_name=device_name,
    #         label=mkvinfo.name,
    #         mount_location=mount_location,
    #         title_count=mkvinfo.title_count,
    #         length=mkvinfo.length_titles,
    #         gigabytes=mkvinfo.gigabytes_titles,
    #     )


# class OpticalDrive:
#     __slots__ = (
#         "path",
#         "is_mounted",
#         "mount_location",
#         "disc_type",
#     )

#     device_name: str
#     device_path: Path
#     is_mounted: bool
#     mount_path: Path
#     disc_type: OpticalDiscType

#     def __init__(
#         self,
#         path: str,
#         is_mounted: bool,
#         mount_location: str,
#         disc_type: OpticalDiscType,
#     ) -> None:
#         pass

#     @classmethod
#     def fetch_drives(cls) -> List["OpticalDrive"]:
#         pass


#     {
#     "mode": "search",
#     "results": {
#         "0": {
#             "crc_id": "d0d1bcba30e2dfc6",
#             "date_added": "2023-06-12 04:29:43.740132",
#             "disctype": "None",
#             "hasnicetitle": "True",
#             "imdb_id": "tt0120201",
#             "label": "STARSHIP_TROOPERS",
#             "no_of_titles": "None",
#             "poster_img": "None",
#             "title": "Starship-Troopers",
#             "tmdb_id": "None",
#             "validated": "False",
#             "video_type": "movie",
#             "year": "1997"
#         }
#     },
#     "success": true
# }
