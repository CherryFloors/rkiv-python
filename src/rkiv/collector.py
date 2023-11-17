"""
collector.py

Contains classes to aid in aggregating movie collections:
- The Rewatchables
- Dinner & A Movie
- Eberts Favorites
- Review

"""
import requests
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from enum import Enum
from pathlib import Path
from typing import Optional

import click
import pandas
from thefuzz import process

from rkiv.jellyfinproxy import JellyfinMovie, JellyfinProxy


@dataclass(slots=True)
class CollectorDataFrame:
    """
    Class to hold external collections data frame with convenient
    prperties to access columns

    Data is a dataframe with the following columns
    - jellyfin_title - title of the jellyfin movie
    - collection_title - title of the rewatchables episode
    - score - `int` indicating how well the jellyfin movie title matches
    - movie - `JellyfinMovie` object
    - movie_index - index of the jellyfin movie
    """

    data: pandas.DataFrame

    @property
    def match_mask(self) -> pandas.Series:
        return self.data["score"] == 100

    @property
    def matches(self) -> pandas.DataFrame:
        return self.data[self.match_mask]

    @property
    def missing(self) -> pandas.DataFrame:
        """External collection items not found in Jellyfin library"""
        return self.data[~self.match_mask]

    @property
    def movie(self) -> pandas.DataFrame:
        """External collection items not found in Jellyfin library"""
        return self.data["movie"]

    def table_summary(self) -> str:
        """Table summary of the data"""
        matched = click.style("{:5d}".format(len(self.matches)), fg="green")
        missing = click.style("{:5d}".format(len(self.missing)), fg="red")
        out_table = [
            "====================\n",
            "| The Rewatchables |\n",
            "====================\n",
            "| Episodes | {:5d} |\n".format(len(self.data)),
            "|----------+-------|\n",
            "| Matches  | {} |\n".format(matched),
            "|----------+-------|\n",
            "| Missing  | {} |\n".format(missing),
            "--------------------\n",
        ]
        return "".join(out_table)


@dataclass(slots=True)
class JellyfinCollectionItem:
    """Jellyfin collection item"""

    path: Path

    def to_xml(self, indent: int) -> str:
        """Convert to xml"""

        s1 = " " * (indent * 2)
        s2 = s1 + " " * indent
        path = f"{s2}<Path>{self.path}</Path>"
        return f"{s1}<CollectionItem>\n{path}\n{s1}</CollectionItem>\n"


@dataclass(slots=True)
class JellyfinCollection:
    """Representation of a Jellfin Collection"""

    added: datetime
    overview: str
    local_title: str
    collection_items: list[JellyfinCollectionItem]
    lock_data: bool = False
    _collections_path = Path = Path("/var/lib/jellyfin/data/collections/")

    def to_xml(self) -> str:
        """Convert to xml"""
        _collection_items = "".join([i.to_xml(2) for i in self.collection_items])
        s = " " * 2
        root = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        root += "<Item>\n"
        root += f"{s}<Added>{self.added.strftime('%m/%d/%Y %H:%M:%S')}</Added>\n"
        root += f"{s}<LockData>{str(self.lock_data).lower()}</LockData>\n"
        root += f"{s}<Overview>{self.overview}</Overview>\n"
        root += f"{s}<LocalTitle>{self.local_title}</LocalTitle>\n"
        root += f"{s}<CollectionItems>\n{_collection_items}{s}</CollectionItems>\n"
        root += "</Item>"
        return root

    @property
    def file_path(self) -> Path:
        """jellyfin filepath for collection xml"""
        parent = self._collections_path.joinpath(f"{self.local_title} [boxset]")
        return parent.joinpath("collection").with_suffix(".xml")

    @classmethod
    def from_root_element(cls, etree_root: Element) -> "JellyfinCollection":
        """Construct from the root of collection.xml"""

        _added = datetime.now()
        if etree_root.find("./Added") is not None:
            _str = etree_root.find("./Added").text
            _added = datetime.strptime(_str, "%m/%d/%Y %H:%M:%S")

        _overview = ""
        if etree_root.find("./Overview") is not None:
            _overview = etree_root.find("./Overview").text

        _local_title = ""
        if etree_root.find("./LocalTitle") is not None:
            _local_title = etree_root.find("./LocalTitle").text

        _lock_data = False
        if etree_root.find("./LockData") is not None:
            if etree_root.find("./LockData").text == "true":
                _lock_data = True

        _collection_items = [
            JellyfinCollectionItem(path=Path(i.text))
            for i in etree_root.findall("./CollectionItems/CollectionItem/Path")
        ]

        return cls(
            added=_added,
            overview=_overview,
            local_title=_local_title,
            collection_items=_collection_items,
            lock_data=_lock_data,
        )

    @classmethod
    def load_by_name(
        cls, name: str, default: Optional["JellyfinCollection"]
    ) -> "JellyfinCollection":
        """Attempts to a jellyfin collection by name"""
        collection_xmls = [
            Path(r).joinpath(ff)
            for r, _, f in os.walk(cls._collections_path)
            for ff in f
            if ff == "collection.xml"
        ]

        for xml in collection_xmls:
            etree = ElementTree.parse(xml).getroot()
            if name == etree.find("./LocalTitle").text:
                return cls.from_root_element(etree_root=etree)

        if default is not None:
            return default

        return cls.from_root_element(etree_root=Element(""))

    def update(self, collection: CollectorDataFrame) -> list[JellyfinMovie]:
        """
        Updates the Jellyfin collection with missing matches passed in the collector dataframe.

        returns a list of the added movies.
        """
        paths = pandas.Series([i.path for i in self.collection_items])
        new_paths = collection.movie[collection.match_mask].apply(lambda x: x.Path)

        new_match_mask = ~new_paths.isin(paths)
        new_matches = new_paths[new_match_mask]
        new_matches = new_matches.apply(JellyfinCollectionItem).to_list()

        self.collection_items = new_matches + self.collection_items

        return collection.movie[collection.match_mask][new_match_mask].to_list()

    def save(self) -> None:
        """Save the XML"""
        xml = self.to_xml()

        if not self.file_path.exists():
            self.file_path.parent.mkdir(exist_ok=True, mode=0o755)
            shutil.chown(self.file_path.parent, user="jellyfin", group="jellyfin")

        with open(self.file_path, "w") as f:
            f.write(xml)

        self.file_path.chmod(mode=0o664)
        shutil.chown(self.file_path, user="jellyfin", group="jellyfin")


class TitlePartions(str, Enum):
    """Characters used to partition the title"""

    START_TICK = "‘"
    END_TICK = "’"
    TICK = "'"
    START_QUOTE = "“"
    END_QUOTE = "”"
    QUOTE = '"'

    @staticmethod
    def as_set() -> set[str]:
        """Characters as set"""
        return {"’", "‘", "'", "“", "”", '"'}

    @staticmethod
    def ticks() -> set[str]:
        """Characters as set"""
        return {"’", "‘", "'"}

    @staticmethod
    def quotes() -> set[str]:
        """Characters as set"""
        return {"“", "”", '"'}

    @classmethod
    def match(cls, start_partition: "TitlePartions") -> set[str]:
        """gets the matching end partiton"""
        if start_partition in cls.quotes():
            return cls.quotes()

        return cls.ticks()


@dataclass(slots=True)
class TheRewatchablesEpisode:
    """Class to hold rewatcables episode information"""

    title: str
    movie_name: str
    description: str
    pub_date: datetime
    duration: int
    content_encoded: str
    movie_date: Optional[int] = None

    @staticmethod
    def _movie_name(title: str) -> str:
        """
        Attempts to extract the movie name from the title
        """
        title, _, _ = title.partition("Bill's")
        title, _, _ = title.partition("Bill’s")

        # Loop over each character to find the first partition
        partitions = [
            (i, TitlePartions(p))
            for i, p in enumerate(title)
            if p in TitlePartions.as_set()
        ]

        # No partition found, try partitioning on "with"
        if len(partitions) == 0:
            return title.lower().partition("with")[0]

        start_idx, start_partition = partitions[0]

        end_partion = TitlePartions.match(start_partition)
        end_partitions = [(i, p) for i, p in partitions if p in end_partion]
        if len(end_partitions) == 0:
            return title[(start_idx + 1) :]
        end_idx = end_partitions[-1][0]

        if end_idx == start_idx:
            return title[0:end_idx]

        return title[(start_idx + 1) : end_idx]

    @staticmethod
    def find_movie_date(element: Element) -> Optional[int]:
        """
        Attempts to extract the release year of the movie by searching
        episode metadata
        TODO maybe use to filter out duplicates
        """
        return None

    @classmethod
    def from_rss_xml_element(cls, element: Element) -> "TheRewatchablesEpisode":
        """Class constructor from an xml element"""
        _title = element.find("title").text
        _description = element.find("description").text
        _pub_date = datetime.strptime(
            element.find("pubDate").text, "%a, %d %b %Y %H:%M:%S %z"
        )
        _duration = element.find("itunes:duration")
        _content_encoded = element.find("content:encoded")

        return cls(
            title=_title,
            movie_name=cls._movie_name(title=_title),
            description=_description,
            pub_date=_pub_date,
            duration=_duration,
            content_encoded=_content_encoded,
        )


@dataclass(slots=True)
class TheRewatchables:
    """
    Scrape the rewatchables feed to find matches in the Jellyfin library
    """

    episodes: list[TheRewatchablesEpisode]
    url: str = "https://feeds.megaphone.fm/the-rewatchables"
    collection_name: str = "The Rewatchables"
    overview: str = ""

    @property
    def false_positives(self) -> list[str]:
        """
        This is a really dumb way to solve this issue... so dumb we have
        gone full cirlce to genius? Am I a genius? No. A genius wouldnt hard
        code stuff like this in source. They would make an optional config
        to load at run time. TODO.
        """
        return ["ffe95fd130101e4c27356d9719407118"]

    def defualt_collection(self) -> JellyfinCollection:
        """Returns a JellyfinCollection object with only metadata"""

        return JellyfinCollection(
            added=datetime.now(),
            overview=self.overview,
            local_title=self.collection_name,
            collection_items=[],
        )

    @classmethod
    def scrape(cls) -> "TheRewatchables":
        """
        Scrapes the rewatchables rss feed
        """
        _return = cls(episodes=[])

        response = requests.get(_return.url)
        etree = ElementTree.fromstring(response.content)
        episodes = etree.findall("./channel/item")
        overview = etree.find("./channel/description")

        _return.episodes = [
            TheRewatchablesEpisode.from_rss_xml_element(e) for e in episodes
        ]
        _return.overview = overview.text

        return _return

    def match_jellyfin_library(self) -> CollectorDataFrame:
        """
        Episodes of the rewatchables that match Jellyfin movies
        """
        movies = JellyfinProxy.get_movies()
        movies = pandas.DataFrame(
            [{"jellyfin_title": i.Name, "movie": i} for i in movies]
        )

        exclude = movies["movie"].apply(lambda x: x.Id in self.false_positives)
        movies = movies[~exclude]

        rewatchables = pandas.DataFrame(
            {"collection_title": [i.movie_name for i in self.episodes]}
        ).drop_duplicates()
        rewatchables[["jellyfin_title", "score", "movie_index"]] = (
            rewatchables["collection_title"]
            .apply(process.extractOne, choices=movies["jellyfin_title"])
            .apply(pandas.Series)
        )

        return CollectorDataFrame(
            data=rewatchables.merge(movies, on="jellyfin_title", how="left")
        )
