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


from rkiv.opticaldevices import OpticalDrive
from rkiv.config import Config
from rkiv import __version__

CONFIG = Config()


class RipperStatus(str, Enum):
    SHUTDOWN_REQUEST = "shutdown"
    RIPPING = "ripping"
    FINISHED = "finished"
    WAITING = "waiting"


class UserInput:
    output_path: str
    log_path: str
    disc_name: str

    def __init__(
        self,
        output_path: str,
        log_path: str,
        disc_name: str,
    ) -> None:
        self.output_path = output_path
        self.log_path = log_path
        self.disc_name = disc_name

    def to_json(self) -> dict:
        return {
            "output_path": self.output_path,
            "log_path": self.log_path,
            "disc_name": self.disc_name,
        }

    @classmethod
    def from_json(cls, json: dict) -> "UserInput":
        return cls(
            output_path=json["output_path"],
            log_path=json["log_path"],
            disc_name=json["disc_name"],
        )


class RipperMessage:
    """
    Relay messages and status updates to parent process
    """

    status: RipperStatus
    temp_output: Path
    log_path: Path
    disc_name: str
    mount_path: Path

    def __init__(
        self,
        status: RipperStatus,
        temp_output: Path,
        log_path: Path,
        disc_name: str,
        mount_path: Path,
    ) -> None:
        self.status = status
        self.temp_output = temp_output
        self.log_path = log_path
        self.disc_name = disc_name
        self.mount_path = mount_path

    @classmethod
    def waiting_message(cls) -> "RipperMessage":
        return cls(
            status=RipperStatus.WAITING,
            temp_output=Path(""),
            log_path=Path(""),
            mount_path=Path(""),
            disc_name="",
        )

    @classmethod
    def shutdown_request(cls) -> "RipperMessage":
        return cls(
            status=RipperStatus.SHUTDOWN_REQUEST,
            temp_output=Path(""),
            log_path=Path(""),
            mount_path=Path(""),
            disc_name="",
        )


class VideoRipper:
    """
    Functions that rip
    """

    drive: OpticalDrive
    _temp_file_path: Path

    def __init__(self, drive: OpticalDrive) -> None:
        self.drive = drive
        self._temp_file_path = CONFIG.workspace.joinpath(
            f"{drive.device_name}.video.temp"
        )

    def _store_user_input(self, user_input: UserInput) -> None:
        with open(self._temp_file_path, "w") as info_file:
            info_file.write(json.dumps(user_input.to_json()))

    def _read_user_input(self) -> UserInput:
        with open(self._temp_file_path, "r") as info_file:
            info = json.load(info_file)
        return UserInput.from_json(json=info)

    def launch_terminal_prompt(self) -> None:
        python = sys.executable
        run_script = f"{python} {__file__} {self.drive.device_name}"
        cmd = ["gnome-terminal", "--disable-factory", "--", "/bin/bash", "-c", run_script]
        _ = subprocess.run(cmd, stderr=subprocess.PIPE)

    def _is_blu_ray(self) -> bool:
        return Path(self.drive.get_mount_location()).joinpath("BDMV").exists()

    def _prompt_user(self) -> None:
        mount_location = self.drive.get_mount_location()
        # Check disc type
        if self._is_blu_ray():
            archive_path = CONFIG.video_rip_dir.joinpath("blu_ray")
            log_root = CONFIG.workspace.parent.joinpath("logs").joinpath("blu_ray")
            disc_string = "DISC        : BD"
        else:
            archive_path = CONFIG.video_rip_dir.joinpath("dvd")
            log_root = CONFIG.workspace.parent.joinpath("logs").joinpath("dvd")
            disc_string = "DISC        : DVD"

        # Report the information
        print("****************************")
        print(self.drive.device_name)
        print(disc_string.rstrip())
        print(f"SOURCE      : {mount_location}")
        print(f"DESTINATION : {archive_path}")
        print("****************************\n")

        # Prompt for TV
        tv = input("--TV? (y/n): ")

        if tv == "y":
            # TV disc info from user
            sName = input("--Show Name: ")
            sNum = input("--Season: ")
            dNum = input("--Disc: ")
            disc_path = f"{archive_path}/tv/{sName}/{sName}_S{sNum}"
            disc_name = f"{sName}_S{sNum}_D{dNum}"
        else:
            # Movie disc info from user
            mName = input("--Movie Name: ")
            dNum = input("--Disc: ")
            disc_path = f"{archive_path}/movies/{mName}"
            disc_name = f"{mName}_D{dNum}"

        log_file = log_root.joinpath(f"{disc_name}.log")
        _user_input = UserInput(
            output_path=disc_path, log_path=str(log_file), disc_name=disc_name
        )
        self._store_user_input(user_input=_user_input)

    def _archive_disc(self, user_input: UserInput) -> None:
        
        temp_dvd_output_holder = Path(user_input.output_path).joinpath(f"TEMP_{user_input.disc_name}")
        final_output_path = Path(user_input.output_path).joinpath(user_input.disc_name)

        if not Path(user_input.output_path).exists():
            Path(user_input.output_path).mkdir(parents=True)

        if self._is_blu_ray():
            cmd = [
                "makemkvcon",
                "backup",
                "--decrypt",
                "-r",
                f"disc:{self.drive.device_path}",
                str(final_output_path),
            ]
        else:
            cmd = [
                "dvdbackup",
                "-i",
                str(self.drive.device_path),
                "-o",
                temp_dvd_output_holder,
                "-M",
                "-v",
            ]

        if not Path(user_input.log_path).parent.exists():
            Path(user_input.log_path).parent.mkdir(parents=True)

        with open(user_input.log_path, "a+") as log:
            _ = subprocess.run(cmd, stdout=log, stderr=log)

        # Rename the disc
        if not self._is_blu_ray():
            original_name = next(os.walk(temp_dvd_output_holder))[1][0]
            old_path = Path(temp_dvd_output_holder).joinpath(original_name)
            old_path.rename(final_output_path)
            temp_dvd_output_holder.rmdir()

        _ = subprocess.run(["eject", str(self.drive.device_path)])

    def run(self, pipe: connection.Connection):
        pipe.send(RipperMessage.waiting_message())
        while True:
            mount_location = self.drive.get_mount_location()
            if mount_location != "":
                self.launch_terminal_prompt()
                user_input = self._read_user_input()
                pipe.send(
                    RipperMessage(
                        status=RipperStatus.RIPPING,
                        temp_output=Path(user_input.output_path),
                        log_path=Path(user_input.log_path),
                        disc_name=user_input.disc_name,
                        mount_path=Path(mount_location),
                    )
                )
                self._archive_disc(user_input=user_input)
                pipe.send(
                    RipperMessage(
                        status=RipperStatus.FINISHED,
                        temp_output=Path(user_input.output_path),
                        log_path=Path(user_input.log_path),
                        disc_name=user_input.disc_name,
                        mount_path=Path(mount_location),
                    )
                )
                pipe.send(RipperMessage.waiting_message())

                if pipe.poll():
                    message: RipperMessage = pipe.recv()
                    if message.status == RipperStatus.SHUTDOWN_REQUEST:
                        break

                time.sleep(2)

        print("Gracefully Exiting")


class Notification:
    drive_name: str
    disc_name: str
    problems: list[str]

    def __init__(
        self,
        drive_name: str,
        disc_name: str,
        problems: list[str],
    ) -> None:
        self.drive_name = drive_name
        self.disc_name = disc_name
        self.problems = problems


class AutoVideoRipper:
    """
    Auto Video Ripper
    """

    notifications: list[Notification]
    drives: list[OpticalDrive]
    _child_processes: list[Process]
    _process_pipes: dict[str, connection.Connection]
    _ripping_state: dict[str, RipperMessage]

    def __init__(self, drives: list[OpticalDrive]) -> None:
        self.drives = drives
        self._process_pipes = {}
        self._child_processes = []
        self.notifications = []
        self._ripping_state = {}

        for drive in drives:
            child, parent = Pipe()
            video_ripper = VideoRipper(drive=drive)
            self._process_pipes[drive.device_name] = parent
            self._child_processes.append(Process(target=video_ripper.run, args=[child]))
            self._ripping_state[drive.device_name] = RipperMessage.waiting_message()

    def parse_log_file(self, drive_name: str, log_path: Path, disc_name: str) -> None:
        # Grep for error
        out = subprocess.run(
            f"cat {log_path} | grep -i error",
            shell=True,
            capture_output=True,
            text=True,
        )
        errors = out.stdout.rstrip().split("\n")
        if errors[0] != "":
            self.notifications.append(
                Notification(
                    drive_name=drive_name,
                    disc_name=disc_name,
                    problems=errors,
                )
            )

        # Grep for fail, exclude makemkv's drive read fails
        out = subprocess.run(
            f'cat {log_path} | grep -i fail | grep -v "Failed to get full access to drive"',
            shell=True,
            capture_output=True,
            text=True,
        )
        failures = out.stdout.rstrip().split("\n")
        if failures[0] != "":
            self.notifications.append(
                Notification(
                    drive_name=drive_name,
                    disc_name=disc_name,
                    problems=failures,
                )
            )
        

    def _update_ripping_state(self) -> None:
        """
        Update the _ripping_state
        """
        for drive, pipe in self._process_pipes.items():
            while pipe.poll():
                _state: RipperMessage = pipe.recv()
                if _state.status == RipperStatus.FINISHED:
                    self.parse_log_file(
                        drive_name=drive,
                        log_path=_state.log_path,
                        disc_name=_state.disc_name,
                    )
                self._ripping_state[drive] = _state
            

    def run(self) -> None:
        """
        Entry point to start the auto drive
        """

        ui = VideoRipUI()
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGINT, original_sigint_handler)
        try:
            for process in self._child_processes:
                process.start()

            dash_string, reset = ui.build_dash_string(
                drive_status=self._ripping_state, notifications=self.notifications
            )
            print(dash_string)

            while True:
                self._update_ripping_state()
                dash_string, reset = ui.build_dash_string(
                    drive_status=self._ripping_state, notifications=self.notifications
                )
                print(reset)
                print(dash_string)
                time.sleep(1)

        except KeyboardInterrupt:
            for process in self._child_processes:
                process.terminate()
            print("\nExiting... Thanks for flying with us today.")


class VideoRipUI:
    progress_bar_width: int = 20
    table_one_width: int = 55
    table_two_width: int = 80
    notification_length: int = 5

    @staticmethod
    def _get_free_disk_space(path: Path) -> str:
        out = subprocess.run(["df", "-h", path], capture_output=True, text=True)
        return out.stdout

    @staticmethod
    def _get_directory_size(path: Path) -> float:
        out = subprocess.run(["du", "-s", path], capture_output=True, text=True)
        if out.stdout == "":
            return 0.0
        else:
            return float(out.stdout.split()[0]) / 1024**2

    def get_drive_progress(
        self, drive: str, drive_status: dict[str, RipperMessage]
    ) -> str:
        # Get mount string
        total_size = self._get_directory_size(drive_status[drive].mount_path)
        if drive_status[drive].status == RipperStatus.RIPPING and total_size != 0:
            CurrentSize = self._get_directory_size(drive_status[drive].temp_output)
            DecComplete = min(CurrentSize / total_size, 1)
            PercentageComplete = str(int(DecComplete * 100))
            Prg = int(DecComplete * self.progress_bar_width)
            s1 = f"|  {drive}  [{'#'*Prg}{'-'*(self.progress_bar_width - Prg)}]{' '*(4 - len(PercentageComplete))}{PercentageComplete}%"
            s2 = f"({round(CurrentSize, 2)}/{round(total_size, 2)}) GB  |"
            return f"{s1}{' '*(self.table_one_width - len(s1) - len(s2))}{s2}\n"
        else:
            s1 = f"|  {drive}  {drive_status[drive].status}"
            s2 = "  |"
            return f"{s1}{' '*(self.table_one_width - len(s1) - len(s2))}{s2}\n"

    def build_dash_string(
        self, drive_status: dict[str, RipperMessage], notifications: list[Notification]
    ) -> tuple[str, str]:
        """
        Returns a tuple (dashboard, reset)
        """
        storage_path = CONFIG.video_rip_dir
        # Table One Parameters
        table_one_line_break = f"+{'-'*(self.table_one_width - 2)}+\n"
        table_one_header = f"rkiv Auto Video Ripper Version {__version__}"

        # Table two parameters
        table_two_line_break = f"+{'-'*(self.table_two_width - 2)}+\n"
        table_two_header = "|  DRV   Name                   Message                                        |\n"
        table_two_bold_line_break = f"+{'='*(self.table_two_width - 2)}+\n"

        # Start dash string with time stamp
        dash_string = f"{datetime.datetime.now().ctime()}\n{self._get_free_disk_space(storage_path)}\n"
        # Add line break
        dash_string += table_one_line_break
        # Add Header
        dash_string += f"| {table_one_header}{' '*(self.table_one_width - len(table_one_header) - 3)}|\n"
        dash_string += table_one_line_break
        # Add path
        dash_string += f"| {str(storage_path)[0:(self.table_one_width - 3)]}{' '*(self.table_one_width - len(str(storage_path)[0:(self.table_one_width - 3)]) - 3)}|\n"
        for drive in drive_status.keys():
            dash_string += self.get_drive_progress(drive, drive_status)
        # DashString += "|  SR0  [####----------------]  100%  (2.54/3.55) GB  |\n"
        # Add the last line break and double space
        dash_string += table_one_line_break
        dash_string += "\n"

        # Start table 2
        dash_string += table_two_line_break
        # NOtifications line
        notification_total = len(notifications)
        s1 = f"| Notifications: {notification_total}"
        dash_string += f"{s1}{' '*(self.table_two_width - len(s1) - 1)}|\n"

        # Header and bold line break
        dash_string += table_two_header
        dash_string += table_two_bold_line_break
        for Notification in notifications[-5:]:
            drv = Notification.drive_name
            nme = Notification.disc_name
            msg = "-".join(Notification.problems)
            dash_string += f"|  {drv}    {nme[0:20]}{' '*(23 - len(nme[0:20]))}{msg[0:46]}{' '*(46 - len(msg[0:46]))}|\n"

        if notification_total < 5:
            for i in range((5 - notification_total)):
                dash_string += f"|{' '*(self.table_two_width - 2)}|\n"
        # End the table
        dash_string += table_two_line_break
        return dash_string, "\033[F" * (dash_string.count("\n") + 2)


if __name__ == "__main__":
    device_name = sys.argv[1]
    drive = OpticalDrive.get_optical_drive(device_name=device_name)
    video_ripper = VideoRipper(drive=drive)
    video_ripper._prompt_user()
