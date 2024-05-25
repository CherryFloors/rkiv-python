from __future__ import annotations
import subprocess
import time
import signal
import asyncio
from asyncio.tasks import Task
from pathlib import Path
from typing import Protocol
from datetime import timedelta
from enum import Enum

import click

from rkiv.arm import UserInput, UserInputRequest, DriveManagerStatus, DriveManagerState
from rkiv.makemkv import MakeMKVInfo, MakeMKVRipper
from rkiv.opticaldevices import OpticalDrive, get_optical_drives
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


class OpticalMedaiaRippingJob:
    """
    Job rquest to rip optical media
    """

    drive: OpticalDrive
    user_input: UserInput


# class AutoRippingMachine:
#
#     drive_manageers: list[OpticalDriveManager]
#     notificaitons: list[Notification]


class ARMUserInterface:
    """ """

    terminal_buffer: list[str] = []
    progress_bar_width: int = 20
    table_one_width: int = 80
    table_two_width: int = 80
    notification_length: int = 5
    input_request_queue: asyncio.Queue[UserInputRequest] = asyncio.Queue()
    ripping_jobs: asyncio.Queue = asyncio.Queue()
    drives: list[OpticalDrive] = sorted(get_optical_drives())
    drive_status: dict[str, DriveManagerStatus] = {}
    notifications: list[Notification] = []
    disc_manger_tasks: list[Task] = []
    _shutdown_signal: bool = False

    def get_drive_status(self, drive: OpticalDrive) -> DriveManagerStatus:
        _stat = self.drive_status.get(drive.device_name)
        if _stat is None:
            _stat = DriveManagerStatus(state=DriveManagerState.WAITING, progress_fraction=0.0)
            self.drive_status[drive.device_name] = _stat

        return _stat

    def set_drive_status(self, drive: OpticalDrive, status: DriveManagerStatus) -> None:
        self.drive_status[drive.device_name] = status

    def set_drive_progress(self, drive: OpticalDrive, progress_fraction: float) -> None:
        if drive.device_name not in self.drive_status.keys():
            state = DriveManagerState.RIPPING
            if progress_fraction != 0.0:
                state = DriveManagerState.WAITING

            self.drive_status[drive.device_name] = DriveManagerStatus(state=state, progress_fraction=0.0)

        self.drive_status[drive.device_name].progress_fraction = progress_fraction

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

    def get_drive_progress(self, drive: OpticalDrive, legacy: bool = False) -> str:
        """
        Produces the drive status line

        legacy:
            |  sr0  waiting                                       |

        new style:
            |  [R]  sr0  <==============----------------->  100%  |
        """

        status = self.get_drive_status(drive)
        s1 = "|  ["
        s2 = f"]  {drive.device_name}  "

        s_length = len(s1) + len(s2) + 1
        s = s1 + status.state.symbol + s2

        progress_bar = status.state.value
        padding = self.table_one_width - s_length - len(progress_bar) - 1

        if status.state == DriveManagerState.RIPPING:
            padding = 2
            bar_width = self.table_one_width - s_length - 11  # '<>  100%  |'

            progress_tokens = "=" * int(bar_width * status.progress_fraction)
            progress_fill = "-" * (bar_width - len(progress_tokens))

            progress = f"{int(status.progress_fraction * 100) : >3}%"
            progress_bar = f"<{click.style(progress_tokens, fg='green')}{progress_fill}>  {progress}"

        s = s + progress_bar
        return s + (padding * " ") + "|"

        # s2 = "  |"
        # s1 = f"|  [{}]-{drive.device_name}  {prg}"
        # s2 = "  |"
        #
        # "[R]  sr0:  <====---->  100%
        # if self.drive_status[drive].status == RipperStatus.RIPPING and total_size != 0:
        #
        #     current_size = self._get_directory_size(self.drive_status[drive].temp_output)
        #     complete_fraction = min(current_size / total_size, 1)
        #     complete_percentage = str(int(complete_fraction * 100))
        #
        #     progress = int(complete_fraction * self.progress_bar_width)
        #
        #     s1 = f"|  {drive}  [{'#'*progress}{'-'*(self.progress_bar_width - progress)}]"
        #     s1 += f"{' '*(4 - len(complete_percentage))}{complete_percentage}%"
        #     s2 = f"({round(current_size, 2)}/{round(total_size, 2)}) GB  |"
        #
        # return f"{s1}{' '*(self.table_one_width - len(s1) - len(s2))}{s2}"

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
            *[self.get_drive_progress(drive) for drive in self.drives],
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
                f"|  {drv}   {nme[0:20]}{' '*(23 - len(nme[0:20]))}{msg[0:46]}{' '*(47 - len(msg[0:46]))}|"
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
            f"{time.strftime('%X')}",
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
            click.echo(self._reset_cursor())
        click.echo("\n".join(self.terminal_buffer))

    def user_prompt(self, request: UserInputRequest) -> UserInput:
        """
        Prompt the user for input
        """

        self.clear()
        click.echo(self._reset_cursor())

        temp_buffer = [
            f"** DEVICE    : {request.device_name}",
            f"** SOURCE    : {request.mount_location}",
            f"** LABEL     : {request.label}",
            f"** TITLES    : {request.title_count}",
            f"** LENGTH    : {request.length}",
            f"** SIZE (GB) : {round(request.gigabytes, 2)}",
        ]

        self.terminal_buffer = [
            "",
            "*" * self.table_two_width,
            "*" * self.table_two_width,
        ]

        self.terminal_buffer += [i.ljust(self.table_two_width - 2) + "**" for i in temp_buffer]
        self.render(reset=False)

        tv = click.confirm("   --TV")
        if tv:
            self.terminal_buffer += ["", "", "", ""]
            _name = click.prompt("   --Show Name", type=str)
            _season = click.prompt("   --Season", type=int)
            _disc = click.prompt("   --Disc", type=int)
        else:
            self.terminal_buffer += ["", "", ""]
            _name = click.prompt("   --Movie Name", type=str, default=request.label)
            _disc = click.prompt("   --Disc", type=int)
            _season = None

        return UserInput(
            name=_name,
            season=_season,
            disc=_disc,
        )

    async def service_input_queue(self) -> None:
        """
        Service requests for user input
        """

        event_loop = asyncio.get_event_loop()

        while not self.input_request_queue.empty():
            input_request = await self.input_request_queue.get()
            user_input = await event_loop.run_in_executor(None, self.user_prompt, input_request)
            await input_request.input_return_queue.put(user_input)

            self.clear()
            click.echo(self._reset_cursor())
            self.update_buffer()
            self.render(reset=False)

    def parse_makemkv_output(self, output: str, user_input: UserInput, drive: OpticalDrive) -> None:
        """
        Parse makemkv output prior to dumping in log file
        """

        # Grep for error
        errors = [line for line in output.splitlines() if "error" in line.lower()]
        if len(errors) > 0:
            _notification = Notification(drive_name=drive.device_name, disc_name=user_input.name, problems=errors)
            self.notifications.append(_notification)

        # Grep for fail, exclude makemkv's drive read fails
        exclude = "Failed to get full access to drive"
        failures = [line for line in output.splitlines() if "fail" in line.lower() and exclude not in line]
        if len(failures) > 0:
            _notification = Notification(drive_name=drive.device_name, disc_name=user_input.name, problems=failures)
            self.notifications.append(_notification)

    async def drive_manager(self, drive: OpticalDrive) -> None:
        """ """

        input_return_queue: asyncio.Queue[UserInput] = asyncio.Queue()
        event_loop = asyncio.get_event_loop()

        while not self._shutdown_signal:
            mount_location = await event_loop.run_in_executor(None, drive.get_mount_location)
            if mount_location != "":
                mkvinfo = await event_loop.run_in_executor(None, MakeMKVInfo.scan_disc, drive)
                request = UserInputRequest(
                    device_name=drive.device_name,
                    label=mkvinfo.name,
                    mount_location=mount_location,
                    title_count=mkvinfo.title_count,
                    length=mkvinfo.length_titles,
                    gigabytes=mkvinfo.gigabytes_titles,
                    input_return_queue=input_return_queue,
                )

                await self.input_request_queue.put(request)
                user_input = await input_return_queue.get()

                ripper = MakeMKVRipper(stage="", progress=0.0, drive=drive, progress_callback=self.set_drive_progress)
                self.set_drive_status(drive, DriveManagerStatus(DriveManagerState.RIPPING, 0.0))

                out = await ripper.extract(input=user_input, drive=drive)
                await event_loop.run_in_executor(None, self.parse_makemkv_output, out, user_input, drive)
                self.set_drive_status(drive, DriveManagerStatus(DriveManagerState.WAITING, 0.0))

            await asyncio.sleep(0.5)

    async def run(self) -> None:
        event_loop = asyncio.get_event_loop()
        drives = get_optical_drives()
        self.disc_manger_tasks += [asyncio.create_task(self.drive_manager(drive)) for drive in drives]

        await event_loop.run_in_executor(None, self.update_buffer)
        await event_loop.run_in_executor(None, self.render, False)

        while not self._shutdown_signal:
            await event_loop.run_in_executor(None, self.update_buffer)
            await event_loop.run_in_executor(None, self.render)
            await self.service_input_queue()
            await asyncio.sleep(0.5)
        # try:
        #
        #     await event_loop.run_in_executor(None, self.update_buffer)
        #     await event_loop.run_in_executor(None, self.render, False)
        #
        #     while True:
        #         await event_loop.run_in_executor(None, self.update_buffer)
        #         await event_loop.run_in_executor(None, self.render)
        #         await self.service_input_queue()
        #         await asyncio.sleep(0.5)
        #
        # except KeyboardInterrupt:
        #     click.echo("\nExiting... Thanks for flying with us today.")
        #     self.shutdown = True
        #     for disc_manger_task in disc_manger_tasks:
        #         await disc_manger_task

    def notification_dump(self) -> None:
        """
        Dump notifications to screen
        """

        header = f"  DRV   {'Name' : <20}   Message"
        bold_line_break = "=" * self.table_two_width

        click.echo(header)
        click.echo(bold_line_break)

        for notification in self.notifications[-5:]:
            drv = notification.drive_name
            nme = notification.disc_name

            for msg in notification.problems:
                click.echo(f"  {drv}   {nme[0:20] : <20}   {msg}")

    async def shutdown(self) -> None:
        """
        Shutdown kinda gracefully...

        TODO: restructure to have a UI task, the run() funct can be non async and maybe we can
        wait for tasks to shut themselves down...
        """

        click.echo("\nExiting... Thanks for flying with us today.")
        self._shutdown_signal = True

        for disc_manger_task in self.disc_manger_tasks:
            click.echo(f"{disc_manger_task} done: {disc_manger_task.done()}")

        click.echo("")
        self.notification_dump()


if __name__ == "__main__":
    try:
        ui = ARMUserInterface()
        asyncio.run(ui.run())
    except KeyboardInterrupt:
        asyncio.run(ui.shutdown())
