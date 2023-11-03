from pathlib import Path

from rkiv import config


class TestConfig:
    @staticmethod
    def test_default_config() -> None:
        """test_default_config"""
        c = config.Config(load=False)
        assert c.workspace == config._rkiv_dir().joinpath("temp")
        assert c.music_rip_dir == Path.home().joinpath("Music")
        assert c.video_rip_dir == Path.home().joinpath("Videos")
        assert c.itunes_dir == Path.home().joinpath("Music/iTunes")
        assert c.mpd_dir == config._user_config_dir().joinpath("mpd")
        assert c.abcde_config == config._rkiv_dir().joinpath("abcde.conf")
        assert c.video_archives == [Path.home().joinpath("Archive")]
        assert c.video_streams == [Path.home().joinpath("Videos")]
        assert c.audio_streams == [Path.home().joinpath("Music")]
        assert c.editor == None

    @staticmethod
    def test_overload_config() -> None:
        """test_default_config"""

        overloads = {
            "workspace": "foo",
            "music_rip_dir": "qoo",
            "video_rip_dir": "woo",
            "itunes_dir": "eoo",
            "mpd_dir": "roo",
            "abcde_config": "aoo",
            "video_archives": ["too", "goo"],
            "video_streams": ["yoo", "doo"],
            "audio_streams": ["uoo", "loo"],
            "editor": "vim",
        }

        c = config.Config(load=False)
        c._overrides(overloads)

        for k, v in overloads.items():
            if isinstance(v, list):
                assert getattr(c, k) == [Path(i) for i in v]
            else:
                assert isinstance(v, str)
                assert getattr(c, k) == Path(v)
