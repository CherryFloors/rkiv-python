import os
import subprocess
import pathlib
import time
from typing import Tuple, List
from datetime import datetime, timezone
from pathlib import Path

from rkiv.config import Config
from rkiv.opticaldevices import OpticalDrive


CONFIG = Config()

def get_files_list(root_path: str) -> List[str]:
    """Returns list full file path strings"""
    return [
        os.path.join(rName, fName)
        for rName, _, fNames in os.walk(root_path)
        for fName in fNames
    ]


def get_current_datetime_object() -> datetime:
    return datetime.now().astimezone()


def convert_to_meta_data_timestamp_str(date_time_object: datetime) -> str:
    # DateTimeObject.astimezone(timezone.utc).isoformat()
    return date_time_object.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.000000Z"
    )

def convert_to_meta_data_date_str(date_time_object: datetime) -> str:
    """convert_to_meta_data_date_str"""
    return date_time_object.strftime("%Y-%m-%d")

def time_stamp_alac(file: str, timestamp: str) -> None:
    """time_stamp_alac"""
    cmd_list = ["AtomicParsley", file, "--overWrite", "--rDNSatom", timestamp, "name=date_added", "domain=com.apple.iTunes"]
    proc_output = subprocess.run(cmd_list, capture_output=True, text=True)
    
    return proc_output.returncode


def convert_to_alac(
    in_file_path: str, out_file_path: str, timestamp: str = None
) -> int:
    # Define the cmd strings
    cmd_list = [
        "ffmpeg",
        "-i",
        in_file_path,
        "-v",
        "error",
        "-c:a",
        "alac",
        "-c:v",
        "copy",
        out_file_path,
    ]
    proc_output = subprocess.run(cmd_list, capture_output=True, text=True)
    if proc_output.returncode != 0:
        return proc_output.returncode

    if timestamp:
        return time_stamp_alac(file=out_file_path, timestamp=timestamp)
        
    return proc_output.returncode


def audio_rip_dash(drive_list: List[OpticalDrive]) -> Tuple[str]:
    # Calculate reset
    reset_cursor = "\033[F" * (5 + len(drive_list))
    prog_bar_w = 20
    drive_progress = ""
    for drv in sorted(drive_list):
        rip_path = f"{CONFIG.workspace}/{drv.device_name}"
        if drv.is_mounted():
            out = subprocess.run(
                [f"ls {drv.mount_path} | wc -l"],
                shell=True,
                capture_output=True,
                text=True,
            )
            total = int(out.stdout)
            ripped = len(
                [
                    os.path.join(rName, fName)
                    for rName, dNames, fNames in os.walk(rip_path)
                    for fName in fNames
                    if "abcde" not in rName
                ]
            )
            n_prg = int((ripped / total) * prog_bar_w)
            s_prg = "#" * n_prg
            fill = " " * (prog_bar_w - n_prg)
            drive_progress = (
                f"{drive_progress}{drv.device_name}: [{s_prg}{fill}] ({ripped}/{total})\n"
            )
        else:
            fill = " " * (prog_bar_w + 9)
            drive_progress = f"{drive_progress}{drv.device_name}: X{fill}\n"
    # Get disk space
    out = subprocess.run(["df", "-h", CONFIG.workspace], capture_output=True, text=True)
    drive_progress = f"{drive_progress}\n{out.stdout}"
    return drive_progress, reset_cursor


def audio_rip_wrapper(drive: OpticalDrive) -> None:
    # Mounted drive location
    # drive_loc = f"/dev/{drive}"
    # cd_mount = f"/run/user/1000/gvfs/cdda:host={drive}"
    # Wav dir and alac dir
    temp_wav_dir = f"{CONFIG.workspace}/{drive.device_name}"
    # Set as loc
    os.chdir(temp_wav_dir)
    # Start the ripping proc
    out = subprocess.run(
        [
            "abcde",
            "-d",
            drive.device_path,
            "-o",
            "flac",
            "-N",
            "-x",
            "-c",
            CONFIG.abcde_config,
        ],
        capture_output=True,
        text=True,
    )  # Run abcde with drive
    output_array = out.stderr.splitlines()
    # Check for errors
    if "error" in out.stdout or "error" in out.stderr:
        with open(f"{CONFIG.music_rip_dir}/{drive.device_name}_error.log", "a+") as errorout:
            errorout.write(f"--- {output_array[0]} ---\n")
            for l in output_array:
                errorout.write(f"  {l}\n")
    # Convert to alac
    files = get_files_list(".")
    for f in files:
        out = convert_to_alac(
            f,
            pathlib.Path(f).with_suffix(".m4a").as_posix(),
            convert_to_meta_data_date_str(get_current_datetime_object()),
        )
        if out == 0:
            # Remove wav file
            os.remove(f)
    # Move files to
    out = subprocess.run(
        [f"cp -r * {CONFIG.music_rip_dir}/"], shell=True, capture_output=True, text=True
    )
    out = subprocess.run(["rm -r *"], shell=True, capture_output=True, text=True)


def auto_audio_ripper(drive: OpticalDrive) -> None:
    cd_mount = f"/run/user/1000/gvfs/cdda:host={drive.device_name}"
    # Wav dir and alac dir
    temp_wav_dir = f"{CONFIG.workspace}/{drive.device_name}"
    # Check if it exists to make
    if not Path(temp_wav_dir).exists():
        Path(temp_wav_dir).mkdir(parents=True)
    # Set as loc
    os.chdir(temp_wav_dir)
    # Continuous loop to search for newly entered discs
    while True:
        try:
            if os.path.exists(cd_mount):  # Checks if an audio disc has been entered
                audio_rip_wrapper(drive)
        except:
            pass
        time.sleep(2)
