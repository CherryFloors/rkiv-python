from pathlib import Path

import pytest

from rkiv.opticaldevices import OpticalDrive
from rkiv.arm import UserInput
from rkiv.arm.tui import ARMUserInterface


@pytest.fixture
def arm_ui() -> ARMUserInterface:
    """Arm UI for testing"""

    return ARMUserInterface()


@pytest.fixture
def user_input() -> UserInput:
    """user input for testing"""

    return UserInput(
        name="sr0",
        season=1,
        disc=2,
    )


@pytest.fixture
def optical_drive() -> OpticalDrive:
    """optical for testing"""

    return OpticalDrive(
        device_name="sr0",
        device_path=Path("dev_path"),
        mount_path=Path("mount_path"),
    )


class TestARMUserInterface:
    """test ARMUserInterface"""

    @staticmethod
    def test_parse_makemkv_output_clean(
        arm_ui: ARMUserInterface, user_input: UserInput, optical_drive: OpticalDrive
    ) -> None:
        """test it"""

        arm_ui.notifications = []
        assert len(arm_ui.notifications) == 0
        mkv_output = "line0\nline1"
        arm_ui.parse_makemkv_output(mkv_output, user_input, optical_drive)

        assert len(arm_ui.notifications) == 0

    @staticmethod
    def test_parse_makemkv_output_error(
        arm_ui: ARMUserInterface, user_input: UserInput, optical_drive: OpticalDrive
    ) -> None:
        """test it"""

        arm_ui.notifications = []
        assert len(arm_ui.notifications) == 0
        mkv_output = "line0\nERROR uppercase\nline2\nerror lowercase"
        arm_ui.parse_makemkv_output(mkv_output, user_input, optical_drive)

        assert len(arm_ui.notifications) == 1
        notif = arm_ui.notifications[0]

        assert notif.disc_name == user_input.name
        assert notif.drive_name == optical_drive.device_name

        assert len(notif.problems) == 2
        assert notif.problems[0] == "ERROR uppercase"
        assert notif.problems[1] == "error lowercase"

    @staticmethod
    def test_parse_makemkv_output_fail(
        arm_ui: ARMUserInterface, user_input: UserInput, optical_drive: OpticalDrive
    ) -> None:
        """test it"""

        arm_ui.notifications = []
        assert len(arm_ui.notifications) == 0
        mkv_output = "line0\nFAIL upper\nfail lower"
        arm_ui.parse_makemkv_output(mkv_output, user_input, optical_drive)

        assert len(arm_ui.notifications) == 1
        notif = arm_ui.notifications[0]

        assert notif.disc_name == user_input.name
        assert notif.drive_name == optical_drive.device_name

        assert len(notif.problems) == 2
        assert notif.problems[0] == "FAIL upper"
        assert notif.problems[1] == "fail lower"

    @staticmethod
    def test_parse_makemkv_output_fake_fail(
        arm_ui: ARMUserInterface, user_input: UserInput, optical_drive: OpticalDrive
    ) -> None:
        """test it"""

        arm_ui.notifications = []
        assert len(arm_ui.notifications) == 0
        mkv_output = 'MSG:2016,0,3,"Failed to get full access to drive "PLDS DVDROM DH16D8SH".'
        arm_ui.parse_makemkv_output(mkv_output, user_input, optical_drive)

        assert len(arm_ui.notifications) == 0
