"""opticaldevices.py"""

import subprocess
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

import pyudev


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

    def __eq__(self, other: "OpticalDrive") -> bool:
        """__eq__"""
        return self.device_name == other.device_name

    def __lt__(self, other: "OpticalDrive") -> bool:
        """__lt__"""
        if self._alpha() == other._alpha():
            return self._numeric() < other._numeric()
        return self._alpha < other._alpha()

    def __le__(self, other: "OpticalDrive") -> bool:
        """__le__"""
        if self._alpha() == other._alpha():
            return self._numeric() <= other._numeric()
        return self._alpha <= other._alpha()

    def __gt__(self, other: "OpticalDrive") -> bool:
        """__gt__"""
        if self._alpha() == other._alpha():
            return self._numeric() > other._numeric()
        return self._alpha > other._alpha()

    def __ge__(self, other: "OpticalDrive") -> bool:
        """__ge__"""
        if self._alpha() == other._alpha():
            return self._numeric() >= other._numeric()
        return self._alpha >= other._alpha()

    def _alpha(self) -> str:
        return "".join([i for i in self.device_name if i.isalpha()])

    def _numeric(self) -> int:
        return int("".join([i for i in self.device_name if i.isnumeric()]))

    def is_mounted(self) -> bool:
        """is mounted"""
        exists: bool = False
        try:
            exists = self.mount_path.exists()
        except:
            pass
        return exists


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
