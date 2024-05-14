from __future__ import annotations
import subprocess
import sys
import datetime
import json
import time
import signal
import os
from pathlib import Path
from multiprocessing import connection, Process, Pipe
from enum import Enum
from typing import Protocol

import click

from rkiv.video import RipperStatus, RipperMessage, Notification
from rkiv.config import Config
from rkiv import __version__

CONFIG = Config()


class OpticalMediaRipper(Protocol):

    def rip(self):
        ...

    def progress(self):
        ...

    def prompt(self):
        ...


class OpticalDriveManager:
    """
    Spies on optical devices and schedules media
    """

    drive: str


class UserInput:
    """
    Holds user input for optical media
    """

    name: str
    season: int
    disc: int

    def __init__(self, name: str, season: int, disc: int) -> None:
        self.name = name
        self.season = season
        self.disc = disc


class UserInputRequest:
    """
    Holds information needed to prompt user
    """

    device_name
    disc_string
    mount_location
    archive_path

    def __init__(self, name: str, season: int, disc: int) -> None:
        self.name = name
        self.season = season
        self.disc = disc


class ARMUserInterface:
    """

    """

    terminal_buffer: list[str] = []
    progress_bar_width: int = 20
    table_one_width: int = 55
    table_two_width: int = 80
    notification_length: int = 5

    @property
    def drive_status(self) -> dict[str, RipperMessage]:

        return {
            "sr0": RipperMessage.waiting_message(),
            "sr1": RipperMessage.waiting_message(),
            "sr2": RipperMessage.waiting_message(),
            "sr3": RipperMessage.waiting_message(),
        }

    @property
    def notifications(self) -> list[Notification]:

        return [
            Notification(
                drive_name="sr0",
                disc_name="Movie Title",
                problems=["This is a problem"],
            )
        ]

    @staticmethod
    def _get_free_disk_space(path: Path) -> str:

        out = subprocess.run(["df", "-h", path], capture_output=True, text=True)
        return out.stdout

    @staticmethod
    def _get_directory_size(path: Path) -> float:

        out = subprocess.run(["du", "-s", path], capture_output=True, text=True)
        if out.stdout == "":
            return 0.0

        return float(out.stdout.split()[0]) / 1024**2

    def get_drive_progress(self, drive: str) -> str:

        total_size = self._get_directory_size(self.drive_status[drive].mount_path)
        s1 = f"|  {drive}  {self.drive_status[drive].status}"
        s2 = "  |"

        if self.drive_status[drive].status == RipperStatus.RIPPING and total_size != 0:

            current_size = self._get_directory_size(self.drive_status[drive].temp_output)
            complete_fraction = min(current_size / total_size, 1)
            complete_percentage = str(int(complete_fraction * 100))

            progress = int(complete_fraction * self.progress_bar_width)

            s1 = f"|  {drive}  [{'#'*progress}{'-'*(self.progress_bar_width - progress)}]"
            s1 += f"{' '*(4 - len(complete_percentage))}{complete_percentage}%"
            s2 = f"({round(current_size, 2)}/{round(total_size, 2)}) GB  |"

        return f"{s1}{' '*(self.table_one_width - len(s1) - len(s2))}{s2}"

    def heading(self) -> list[str]:
        """
        Produces the UI header

            Filesystem      Size  Used Avail Use% Mounted on
            /dev/sda2       916G  227G  642G  27% /
        """

        storage_path = CONFIG.video_rip_dir
        return self._get_free_disk_space(storage_path).splitlines()

    def drive_progress_table(self) -> list[str]:
        """
        Produces the drive progress table

            +-----------------------------------------------------+
            | rkiv Auto Video Ripper Version 0.1.0                |
            +-----------------------------------------------------+
            |  sr0  waiting                                       |
            |  sr1  waiting                                       |
            |  sr2  waiting                                       |
            |  sr3  waiting                                       |
            +-----------------------------------------------------+
        """

        line_break = "+" + "-" * (self.table_one_width - 2) + "+"
        header = f"rkiv Auto Ripping Machine {__version__}"

        return [
            line_break,
            f"| {header}{' '*(self.table_one_width - len(header) - 3)}|",
            line_break,
            *[self.get_drive_progress(drive) for drive in self.drive_status.keys()],
            line_break,
        ]

    def notifications_table(self) -> list[str]:
        """
        Produces the notification table

            +------------------------------------------------------------------------------+
            | Notifications: 1                                                             |
            |  DRV   Name                   Message                                        |
            +==============================================================================+
            |  sr0    Movie Title            This is a problem                             |
            |                                                                              |
            |                                                                              |
            |                                                                              |
            |                                                                              |
            +------------------------------------------------------------------------------+
        """

        notification_total = len(self.notifications)
        line_break = "+" + "-" * (self.table_two_width - 2) + "+"
        notification_num = f"| Notifications: {notification_total}"
        header = "|  DRV   Name                   Message                                        |"
        bold_line_break = "+" + "=" * (self.table_two_width - 2) + "+"

        notification_table = [
            line_break,
            f"{notification_num}{' '*(self.table_two_width - len(notification_num) - 1)}|",
            header,
            bold_line_break,
        ]

        for notification in self.notifications[-5:]:

            drv = notification.drive_name
            nme = notification.disc_name
            msg = "-".join(notification.problems)

            notification_table.append(
                f"|  {drv}    {nme[0:20]}{' '*(23 - len(nme[0:20]))}{msg[0:46]}{' '*(46 - len(msg[0:46]))}|"
            )

        if notification_total < 5:
            fill = [f"|{' '*(self.table_two_width - 2)}|" for _ in range((5 - notification_total))]
            notification_table += fill

        notification_table.append(line_break)

        return notification_table

    def update_buffer(self) -> None:
        """
        Update the terminal buffer
        """

        self.terminal_buffer = [
            "",
            *self.heading(),
            "",
            *self.drive_progress_table(),
            "",
            *self.notifications_table(),
            "",
        ]

    def _reset_cursor(self) -> str:
        return "\033[F" * (len(self.terminal_buffer) + 1)

    def clear(self) -> None:
        self.terminal_buffer = [" " * self.table_two_width] * len(self.terminal_buffer)
        self.render()

    def render(self, reset: bool = True) -> None:
        if reset:
            print(self._reset_cursor())
        print("\n".join(self.terminal_buffer))

    def user_prompt(self) -> UserInput:
        """
        Prompt the user for input
        """

        self.clear()
        print(self._reset_cursor())

        self.terminal_buffer = [
            "*" * self.table_one_width,
            "*" * self.table_one_width,
            "** sr0",
            "** dname",
            "** SOURCE      : /ho/dhflo/h",
            "** DESTINATION : /ldkfh/hdlf/h",
        ]

        self.render(reset=False)

        tv = click.confirm("   --TV")
        if tv:
            self.terminal_buffer += ["", "", ""]
            _name = click.prompt("   --Show Name", type=str)
            _season = click.prompt("   --Season", type=int)
            _disc = click.prompt("   --Disc", type=int)
        else:
            self.terminal_buffer += ["", ""]
            _name = click.prompt("   --Show Name", type=str)
            _disc = click.prompt("   --Disc", type=int)
            _season = 0

        print(self._reset_cursor())

        return UserInput(
            name=_name,
            season=_season,
            disc=_disc,
        )

    def service_input_queue(self) -> UserInput:
        """
        Service requests for user input
        """

        user_input = self.user_prompt()
        self.update_buffer()
        self.render(reset=False)
        return user_input


class AutoRippingMachine:

    drive_manageers: list[OpticalDriveManager]
    notificaitons: list[Notification]

    def run(self) -> None:

        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGINT, original_sigint_handler)

        try:
            # Check each drive
            # Prompt for input
            # submit ripping Process
            # update progress
            # render ui

            self.update_buffer()
            self.render(reset=False)

            for i in range(3):
                self.update_buffer()
                self.render()
                time.sleep(1)

            self.service_input_queue()

            for i in range(3):
                self.update_buffer()
                self.render()
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nExiting... Thanks for flying with us today.")


if __name__ == "__main__":

    ui = ARMUserInterface()
    ui.run()
