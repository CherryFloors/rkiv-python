"""test_iteunes.py"""

from pathlib import Path
from xml.etree import ElementTree
from datetime import datetime, timezone

import pytest

from rkiv import itunes


@pytest.fixture()
def itunes_xml() -> ElementTree.ElementTree:
    """iTunes"""
    return ElementTree.parse("./tests/resources/iTunes.xml")


@pytest.fixture
def tracks_json() -> dict:
    """tracks_json"""
    return {
        "2175": {
            "track_id": 2175,
            "size": 1405606,
            "total_time": 71613,
            "disc_number": 1,
            "disc_count": 1,
            "track_number": 1,
            "track_count": 13,
            "year": 1998,
            "date_modified": datetime(2022, 1, 17, 19, 12, 36, tzinfo=timezone.utc),
            "date_added": datetime(2005, 11, 29, 17, 58, 21, tzinfo=timezone.utc),
            "bit_rate": 128,
            "sample_rate": 44100,
            "release_date": datetime(1998, 9, 29, 7, 0, tzinfo=timezone.utc),
            "artwork_count": 1,
            "persistent_id": "DAA2333E52D5B300",
            "explicit": True,
            "track_type": "File",
            "protected": True,
            "purchased": True,
            "file_folder_count": 5,
            "library_folder_count": 1,
            "name": "Intro",
            "artist": "Black Star",
            "album_artist": "Black Star",
            "composer": "Mos Def & Talib Kweli",
            "album": "Mos Def & Talib Kweli Are Black Star",
            "genre": "Hip-Hop/Rap",
            "kind": "Protected AAC audio file",
            "sort_name": "Intro",
            "sort_album": "Mos Def & Talib Kweli Are Black Star",
            "sort_artist": "Black Star",
            "location": "file://localhost/C:/Users/Ryan/Music/iTunes/iTunes%20Media/Music/Black%20Star/Mos%20Def%20&%20Talib%20Kweli%20Are%20Black%20Star/01%20Intro.m4p",
        },
        "93534": {
            "track_id": 93534,
            "size": 41664221,
            "total_time": 336640,
            "disc_number": 3,
            "disc_count": 3,
            "track_number": 11,
            "track_count": 11,
            "year": 2023,
            "date_modified": datetime(2023, 8, 12, 13, 25, 26, tzinfo=timezone.utc),
            "date_added": datetime(2023, 8, 12, 13, 33, 38, tzinfo=timezone.utc),
            "bit_rate": 1411,
            "sample_rate": 44100,
            "release_date": datetime(2023, 7, 28, 12, 0, tzinfo=timezone.utc),
            "artwork_count": 1,
            "persistent_id": "CB177D9D7B31D654",
            "track_type": "File",
            "file_folder_count": 5,
            "library_folder_count": 1,
            "name": "U.S. Blues (Uptown Theatre, Chicago, IL 12/4/79)",
            "artist": "Grateful Dead",
            "album_artist": "Grateful Dead",
            "album": "1979.09.12 Dave's Picks Volume 47 : Kiel Auditorium, St. Louis, MO",
            "kind": "Apple Lossless audio file",
            "sort_artist": "Grateful Dead",
            "sort_album_artist": "Grateful Dead",
            "location": "file://localhost/C:/Users/Ryan/Music/iTunes/iTunes%20Media/Music/Grateful%20Dead/1979.09.12%20Dave's%20Picks%20Volume%2047%20_%20Kiel/3-11%20U.S.%20Blues%20(Uptown%20Theatre,%20Chi.m4a",
        },
    }


@pytest.fixture()
def dict_element(itunes_xml) -> ElementTree.Element:
    """dict_element"""
    return ElementTree.fromstring(
        """<dict>
			<key>Track ID</key><integer>2175</integer>
			<key>Size</key><integer>1405606</integer>
			<key>Total Time</key><integer>71613</integer>
			<key>Disc Number</key><integer>1</integer>
			<key>Disc Count</key><integer>1</integer>
			<key>Track Number</key><integer>1</integer>
			<key>Track Count</key><integer>13</integer>
			<key>Year</key><integer>1998</integer>
			<key>Date Modified</key><date>2022-01-17T19:12:36Z</date>
			<key>Date Added</key><date>2005-11-29T17:58:21Z</date>
			<key>Bit Rate</key><integer>128</integer>
			<key>Sample Rate</key><integer>44100</integer>
			<key>Release Date</key><date>1998-09-29T07:00:00Z</date>
			<key>Artwork Count</key><integer>1</integer>
			<key>Persistent ID</key><string>DAA2333E52D5B300</string>
			<key>Explicit</key><true/>
			<key>Track Type</key><string>File</string>
			<key>Protected</key><true/>
			<key>Purchased</key><true/>
			<key>File Folder Count</key><integer>5</integer>
			<key>Library Folder Count</key><integer>1</integer>
			<key>Name</key><string>Intro</string>
			<key>Artist</key><string>Black Star</string>
			<key>Album Artist</key><string>Black Star</string>
			<key>Composer</key><string>Mos Def &#38; Talib Kweli</string>
			<key>Album</key><string>Mos Def &#38; Talib Kweli Are Black Star</string>
			<key>Genre</key><string>Hip-Hop/Rap</string>
			<key>Kind</key><string>Protected AAC audio file</string>
			<key>Sort Name</key><string>Intro</string>
			<key>Sort Album</key><string>Mos Def &#38; Talib Kweli Are Black Star</string>
			<key>Sort Artist</key><string>Black Star</string>
			<key>Location</key><string>file://localhost/C:/Users/Ryan/Music/iTunes/iTunes%20Media/Music/Black%20Star/Mos%20Def%20&#38;%20Talib%20Kweli%20Are%20Black%20Star/01%20Intro.m4p</string>
		</dict>"""
    )


class TestUnzip:
    """TestUnzip"""

    @staticmethod
    def test_even_list() -> None:
        """test_even_list"""
        d = {k: v for k, v in itunes.unzip(range(4))}
        assert d == {0: 1, 2: 3}

    @staticmethod
    def test_odd_list() -> None:
        """test_odd_list"""
        d = {k: v for k, v in itunes.unzip(range(5))}
        assert d == {0: 1, 2: 3}

    @staticmethod
    def test_0_list() -> None:
        """test_0_list"""
        d = {k: v for k, v in itunes.unzip(range(0))}
        assert d == {}

    @staticmethod
    def test_negative_list() -> None:
        """test_negative_list"""
        d = {k: v for k, v in itunes.unzip(range(-10))}
        assert d == {}


class TestITunesXmlConverter:
    """Test ITunesXmlConverter"""

    @staticmethod
    def test_to_json(itunes_xml) -> None:
        """test_to_json"""
        _ = itunes.ITunesXmlConverter.to_json(itunes_xml)

    @staticmethod
    def test_dict() -> None:
        """test_dict"""
        e = ElementTree.fromstring(
            """
                <dict>
			        <key>Track ID</key><integer>2175</integer>
                    <key>Track Type</key><string>File</string>
                </dict>               
            """
        )
        out = itunes.ITunesXmlConverter._dict(e)
        assert isinstance(out, dict)
        assert set(out.keys()) == {"track_id", "track_type"}
        assert out["track_id"] == 2175
        assert out["track_type"] == "File"

    @staticmethod
    def test_array() -> None:
        """test_array"""
        e = ElementTree.fromstring(
            """
                <array>
                    <dict>
                        <key>Track ID</key><integer>2439</integer>
                    </dict>
                    <dict>
                        <key>Track ID</key><integer>2591</integer>
                    </dict>
                    <dict>
                        <key>Track ID</key><integer>2207</integer>
                    </dict>
                </array>
            """
        )
        out = itunes.ITunesXmlConverter._array(e)
        assert isinstance(out, list)
        assert all([isinstance(i, dict) for i in out])
        assert all([set(i.keys()) == {"track_id"} for i in out])
        assert out[0]["track_id"] == 2439
        assert out[1]["track_id"] == 2591
        assert out[2]["track_id"] == 2207

    @staticmethod
    def test_key() -> None:
        """test_key"""
        e = ElementTree.fromstring("<key>Track ID</key>")
        out = itunes.ITunesXmlConverter._key(e)
        assert isinstance(out, str)
        assert out == "track_id"

        e = ElementTree.fromstring("<key>track_id</key>")
        out = itunes.ITunesXmlConverter._key(e)
        assert isinstance(out, str)
        assert out == "track_id"

        e = ElementTree.fromstring("<key>Library Folder Count</key>")
        out = itunes.ITunesXmlConverter._key(e)
        assert isinstance(out, str)
        assert out == "library_folder_count"

    @staticmethod
    def test_data() -> None:
        """test_data"""
        e = ElementTree.fromstring("""<data>\n\t\t\tAQEAAw\n\t\t\tZAAAAcA</data>""")
        out = itunes.ITunesXmlConverter._data(e)
        assert isinstance(out, str)
        assert out == "AQEAAwZAAAAcA"

        e = ElementTree.fromstring("""<data>AQEAAwZAAAAcA</data>""")
        out = itunes.ITunesXmlConverter._data(e)
        assert isinstance(out, str)
        assert out == "AQEAAwZAAAAcA"

    @staticmethod
    def test_date() -> None:
        """test_date"""
        dt = datetime(2022, 1, 17, 19, 12, 36, tzinfo=timezone.utc)
        e = ElementTree.fromstring("""<date>2022-01-17T19:12:36Z</date>""")
        out = itunes.ITunesXmlConverter._date(e)
        assert isinstance(out, datetime)
        assert out == dt

    @staticmethod
    def test_real() -> None:
        """test_real"""
        e = ElementTree.fromstring("""<real>435.56</real>""")
        out = itunes.ITunesXmlConverter._real(e)
        assert isinstance(out, float)
        assert out == 435.56

    @staticmethod
    def test_integer() -> None:
        """test_integer"""
        e = ElementTree.fromstring("""<integer>14</integer>""")
        out = itunes.ITunesXmlConverter._integer(e)
        assert isinstance(out, int)
        assert out == 14

    @staticmethod
    def test_string() -> None:
        """test_string"""
        e = ElementTree.fromstring("""<string>Normal_Str With some. Stuff</string>""")
        out = itunes.ITunesXmlConverter._string(e)
        assert isinstance(out, str)
        assert out == "Normal_Str With some. Stuff"

        e = ElementTree.fromstring("""<string>A&#60;B&#62;C&#38;D</string>""")
        out = itunes.ITunesXmlConverter._string(e)
        assert isinstance(out, str)
        assert out == "A<B>C&D"

        e = ElementTree.fromstring("""<string>Iko Iko -&#62;</string>""")
        out = itunes.ITunesXmlConverter._string(e)
        assert isinstance(out, str)
        assert out == "Iko Iko ->"

        e = ElementTree.fromstring("""<string>Mos Def &#38; Talib Kweli</string>""")
        out = itunes.ITunesXmlConverter._string(e)
        assert isinstance(out, str)
        assert out == "Mos Def & Talib Kweli"

        e = ElementTree.fromstring("""<string>Fame &#60; Infamy</string>""")
        out = itunes.ITunesXmlConverter._string(e)
        assert isinstance(out, str)
        assert out == "Fame < Infamy"

    @staticmethod
    def test_bool() -> None:
        """test_true"""
        e = ElementTree.fromstring("""<true/>""")
        out = itunes.ITunesXmlConverter._bool(e)
        assert isinstance(out, bool)
        assert out

        e = ElementTree.fromstring("""<false/>""")
        out = itunes.ITunesXmlConverter._bool(e)
        assert isinstance(out, bool)
        assert not out


class TestITunesSong:
    """TestITunesSong"""

    @staticmethod
    def test_sanity(tracks_json: dict) -> None:
        """test_sanity"""
        tls = [itunes.ITunesSong(**t) for _, t in tracks_json.items()]
        assert all([isinstance(i, itunes.ITunesSong) for i in tls])


class TestITunesLibraryDataFrame:
    """TestITunesLibraryDataFrame"""

    @staticmethod
    def test_from_itunes_xml() -> None:
        """test_from_itunes_xml"""
        xml_path = Path("./tests/resources/iTunes.xml")
        itdf = itunes.ITunesLibraryDataFrame.from_itunes_xml(xml_path)
        assert isinstance(itdf, itunes.ITunesLibraryDataFrame)
