from datetime import timedelta

from rkiv.dgmap import DiscGroupMapInfo


class TestTitleInfo:
    """test"""

    @staticmethod
    def test_eq_match_all() -> None:
        """test eq"""

        ti1 = DiscGroupMapInfo(
            id=0,
            is_main=True,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )

        ti2 = DiscGroupMapInfo(
            id=1,
            is_main=False,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )

        assert ti1 == ti2

    @staticmethod
    def test_eq_match_diff_time() -> None:
        """test eq"""

        ti1 = DiscGroupMapInfo(
            id=0,
            is_main=True,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )

        ti2 = DiscGroupMapInfo(
            id=1,
            is_main=False,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=3),
            subtitles=8,
            audio_tracks=3,
        )

        assert ti1 == ti2

    @staticmethod
    def test_eq_no_match_diff_time() -> None:
        """test eq"""

        ti1 = DiscGroupMapInfo(
            id=0,
            is_main=True,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )

        ti2 = DiscGroupMapInfo(
            id=1,
            is_main=False,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=4),
            subtitles=8,
            audio_tracks=3,
        )

        assert ti1 != ti2

    @staticmethod
    def test_eq_no_match_chapters() -> None:
        """test eq"""

        ti1 = DiscGroupMapInfo(
            id=0,
            is_main=True,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )

        ti2 = DiscGroupMapInfo(
            id=1,
            is_main=False,
            chapters=23,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )

        assert ti1 != ti2

    @staticmethod
    def test_eq_no_match_sub() -> None:
        """test eq"""

        ti1 = DiscGroupMapInfo(
            id=0,
            is_main=True,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )

        ti2 = DiscGroupMapInfo(
            id=1,
            is_main=False,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=7,
            audio_tracks=3,
        )

        assert ti1 != ti2

    @staticmethod
    def test_eq_no_match_audio() -> None:
        """test eq"""

        ti1 = DiscGroupMapInfo(
            id=0,
            is_main=True,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )

        ti2 = DiscGroupMapInfo(
            id=1,
            is_main=False,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=4,
        )

        assert ti1 != ti2

    @staticmethod
    def test_to_dict() -> None:
        ti1 = DiscGroupMapInfo(
            id=0,
            is_main=True,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=3,
        )
        td = ti1.to_dict()
        assert str(ti1.duration) == td.pop("duration")
        for k, v in td.items():
            assert v == getattr(ti1, k)

    @staticmethod
    def test_from_dict() -> None:
        td = {
            "id": 2,
            "is_main": True,
            "chapters": 12,
            "duration": "12:23:45",
            "subtitles": 2,
            "audio_tracks": 45,
        }
        ti = DiscGroupMapInfo.from_dict(td)
        assert str(ti.duration) == td.pop("duration")
        for k, v in td.items():
            assert v == getattr(ti, k)

    @staticmethod
    def test_blank() -> None:
        blank = DiscGroupMapInfo.blank()
        assert blank.id == -1
        assert blank.is_main is False
        assert blank.chapters == -1
        assert blank.duration == timedelta(seconds=0)
        assert blank.subtitles == -1
        assert blank.audio_tracks == -1


class TestDiscGroupMapInfo:
    """test dgmapinfo"""

    @staticmethod
    def test_match_title_info() -> None:
        _handbrake = [
            DiscGroupMapInfo(
                id=0,
                is_main=False,
                chapters=22,
                duration=timedelta(hours=1, minutes=32, seconds=2),
                subtitles=8,
                audio_tracks=4,
            ),
            DiscGroupMapInfo(
                id=1,
                is_main=False,
                chapters=12,
                duration=timedelta(hours=1, minutes=32, seconds=12),
                subtitles=7,
                audio_tracks=3,
            ),
            DiscGroupMapInfo(
                id=2,
                is_main=False,
                chapters=2,
                duration=timedelta(hours=1, minutes=32, seconds=14),
                subtitles=8,
                audio_tracks=4,
            ),
            DiscGroupMapInfo(
                id=3,
                is_main=True,
                chapters=22,
                duration=timedelta(hours=1, minutes=32, seconds=29),
                subtitles=8,
                audio_tracks=4,
            ),
        ]

        _makemkv = [
            DiscGroupMapInfo(
                id=4,
                is_main=False,
                chapters=12,
                duration=timedelta(hours=1, minutes=32, seconds=12),
                subtitles=7,
                audio_tracks=3,
            ),
            DiscGroupMapInfo(
                id=5,
                is_main=False,
                chapters=2,
                duration=timedelta(hours=1, minutes=32, seconds=14),
                subtitles=2,
                audio_tracks=4,
            ),
            DiscGroupMapInfo(
                id=6,
                is_main=False,
                chapters=22,
                duration=timedelta(hours=1, minutes=32, seconds=29),
                subtitles=8,
                audio_tracks=4,
            ),
        ]

        id_matches = [(0, -1), (1, 4), (2, -1), (3, 6), (-1, 5)]

        dginfo_list = DiscGroupMapInfo.match_title_info(
            disc_title="Disc1",
            handbrake=_handbrake,
            makemkv=_makemkv,
            friendly_name="",
        )
        for (hbid, mmkvid), dginfo in zip(id_matches, dginfo_list):
            print(f"{hbid} - {mmkvid}")
            assert dginfo.handbrake.id == hbid
            assert dginfo.makemkv.id == mmkvid

    @staticmethod
    def test_to_flat_dict() -> None:
        ti1 = DiscGroupMapInfo(
            id=0,
            is_main=True,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=2),
            subtitles=8,
            audio_tracks=4,
        )

        ti2 = DiscGroupMapInfo(
            id=1,
            is_main=False,
            chapters=22,
            duration=timedelta(hours=1, minutes=32, seconds=29),
            subtitles=7,
            audio_tracks=3,
        )

        dginfo = DiscGroupMapInfo(
            disc_title="Disc1",
            handbrake=ti1,
            makemkv=ti2,
            friendly_name="",
        )
        td1 = timedelta(seconds=1 * 3600 + 32 * 60 + 2)
        td2 = timedelta(seconds=1 * 3600 + 32 * 60 + 29)

        flat = dginfo.to_flat_dict()
        assert dginfo.disc_title == flat.pop("disc_title")
        assert dginfo.friendly_name == flat.pop("friendly_name")

        for k, v in flat.items():
            assert "handbrake_" in k or "makemkv_" in k

            if "handbrake_" in k:
                if "duration" in k:
                    v = td1
                _k = k.replace("handbrake_", "")
                assert v == getattr(ti1, _k)

            if "makemkv_" in k:
                if "duration" in k:
                    v = td2
                _k = k.replace("makemkv_", "")
                assert v == getattr(ti2, _k)

    @staticmethod
    def test_from_flat_dict() -> None:
        flat = {
            "disc_title": "Disc1",
            "handbrake_id": 0,
            "handbrake_is_main": True,
            "handbrake_chapters": 22,
            "handbrake_duration": "1:32:02",
            "handbrake_subtitles": 8,
            "handbrake_audio_tracks": 4,
            "makemkv_id": 1,
            "makemkv_is_main": False,
            "makemkv_chapters": 22,
            "makemkv_duration": "1:32:29",
            "makemkv_subtitles": 7,
            "makemkv_audio_tracks": 3,
            "friendly_name": "name",
        }
        td1 = timedelta(seconds=1 * 3600 + 32 * 60 + 2)
        td2 = timedelta(seconds=1 * 3600 + 32 * 60 + 29)

        dginfo = DiscGroupMapInfo.from_flat_dict(flat)
        assert dginfo.disc_title == flat.pop("disc_title")
        assert dginfo.friendly_name == flat.pop("friendly_name")

        for k, v in flat.items():
            assert "handbrake_" in k or "makemkv_" in k

            if "handbrake_" in k:
                if "duration" in k:
                    v = td1
                _k = k.replace("handbrake_", "")
                assert v == getattr(dginfo.handbrake, _k)

            if "makemkv_" in k:
                if "duration" in k:
                    v = td2
                _k = k.replace("makemkv_", "")
                assert v == getattr(dginfo.makemkv, _k)
