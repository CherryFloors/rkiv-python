"""opticaldevices.py"""

import subprocess
from pathlib import Path
from typing import List
from dataclasses import dataclass
from enum import Enum

# import pyudev


class OpticalDiscType(str, Enum):
    CD = "cd"
    DVD = "dvd"
    BLU_RAY = "blu_ray"


@dataclass
class OpticalDrive:
    __slots__ = (
        "device_name",
        "device_path",
        "mount_path",
    )

    device_name: str
    device_path: Path
    mount_path: Path

    __annotations__ = {
        "device_name": str,
        "device_path": Path,
        "mount_path": Path,
    }

    def __init__(
        self,
        device_name: str,
        device_path: Path,
        mount_path: Path,
    ) -> None:
        """__init__"""
        self.device_name = device_name
        self.device_path = device_path
        self.mount_path = mount_path

    def __eq__(self, other: object) -> bool:
        """__eq__"""
        if not isinstance(other, OpticalDrive):
            return NotImplemented

        return self.device_name == other.device_name

    def __lt__(self, other: object) -> bool:
        """__lt__"""
        if not isinstance(other, OpticalDrive):
            return NotImplemented

        if self._alpha() == other._alpha():
            return self._numeric() < other._numeric()

        return self._alpha() < other._alpha()

    def __le__(self, other: object) -> bool:
        """__le__"""
        if not isinstance(other, OpticalDrive):
            return NotImplemented

        if self._alpha() == other._alpha():
            return self._numeric() <= other._numeric()

        return self._alpha() <= other._alpha()

    def __gt__(self, other: object) -> bool:
        """__gt__"""
        if not isinstance(other, OpticalDrive):
            return NotImplemented

        if self._alpha() == other._alpha():
            return self._numeric() > other._numeric()

        return self._alpha() > other._alpha()

    def __ge__(self, other: object) -> bool:
        """__ge__"""
        if not isinstance(other, OpticalDrive):
            return NotImplemented

        if self._alpha() == other._alpha():
            return self._numeric() >= other._numeric()

        return self._alpha() >= other._alpha()

    def _alpha(self) -> str:
        return "".join([i for i in self.device_name if i.isalpha()])

    def _numeric(self) -> int:
        return int("".join([i for i in self.device_name if i.isnumeric()]))

    def is_mounted(self) -> bool:
        """is mounted"""
        exists: bool = False
        try:
            exists = self.mount_path.exists()
        except Exception:
            pass
        return exists

    def get_mount_location(self) -> str:
        proc_one = subprocess.Popen(["cat", "/proc/mounts"], stdout=subprocess.PIPE)
        mount_info = subprocess.run(
            ["grep", "-i", self.device_name],
            stdin=proc_one.stdout,
            capture_output=True,
            text=True,
        )
        if proc_one.stdout is not None:
            proc_one.stdout.close()
        info = mount_info.stdout
        if info == "":
            return info
        return info.split()[1].replace("\\040", " ")

    @classmethod
    def get_optical_drive(cls, device_name: str) -> "OpticalDrive":
        """get_optical_drives"""
        return cls(
            device_name=device_name,
            device_path=Path("/dev").joinpath(device_name),
            mount_path=Path(f"/run/user/1000/gvfs/cdda:host={device_name}"),
        )


def get_optical_drives() -> List[OpticalDrive]:
    """get_optical_drives"""
    CMDlist = ["awk", "/drive name:/ {print $0}", "/proc/sys/dev/cdrom/info"]
    ProcOutput = subprocess.run(CMDlist, capture_output=True, text=True)
    return [
        OpticalDrive(
            device_name=i,
            device_path=Path("/dev").joinpath(i),
            mount_path=Path(f"/run/user/1000/gvfs/cdda:host={i}"),
        )
        for i in ProcOutput.stdout.rstrip().split("\t")[2:]
    ]
