"""jellyfinproxy"""

import requests
from enum import Enum
from typing import List
from datetime import datetime

import pydantic
from jellyfin_apiclient_python import JellyfinClient  # type: ignore

from rkiv.htmlassets import HTMLTemplates


class JellyfinMovie(pydantic.BaseModel):
    """JellyfinMovie"""

    Name: str
    ServerId: str
    Id: str
    DateCreated: str
    Container: str
    PremiereDate: str = ""
    CriticRating: int = -1
    OfficialRating: str = ""
    Overview: str = ""
    CommunityRating: float = -1.0
    RunTimeTicks: int
    ProductionYear: int
    IsFolder: bool

    @property
    def date_added(self) -> datetime:
        """date added"""
        return datetime.strptime(self.DateCreated.split("T")[0], "%Y-%m-%d")

    @property
    def running_time(self) -> str:
        """running_time"""
        sec = self.RunTimeTicks * (1 / 10_000_000)
        hours = int(sec / 3600)
        minutes = int((sec - hours * 3600) / 60)
        return f"{hours}h {minutes}m"

    def movie_info_banner(self) -> str:
        """HTML info banner"""
        s = HTMLTemplates.media_info_item(str(self.ProductionYear))
        s += HTMLTemplates.media_info_item(self.running_time)
        s += HTMLTemplates.official_rating(self.OfficialRating)
        s += HTMLTemplates.star_rating(round(self.CommunityRating, 1))
        s += HTMLTemplates.get_critic_rating_div(self.CriticRating)
        media_info = HTMLTemplates.media_info_wrapper(s)
        title = HTMLTemplates.movie_tv_title(self.Name)
        return HTMLTemplates.media_banner_wrapper(title, media_info)

    def to_html(self) -> str:
        """Produces and html card of the movie"""
        image_url = JellyfinProxy.get_movie_img_url(self.Id)
        s = HTMLTemplates.movie_image_div(image_url=image_url)
        s += self.movie_info_banner()
        s += HTMLTemplates.movie_summary(self.Overview)
        return HTMLTemplates.movie_card(s)


class JellyfinFolders(pydantic.BaseModel):
    """JellyfinFolders"""

    Name: str
    ServerId: str
    Id: str
    IsFolder: bool


class MetaDataProvider(str, Enum):
    """Metadata providers"""

    THE_MOVIE_DB = "TheMovieDb"
    THE_OPEN_MOVIE_DB = "The Open Movie Database"


class RemoteAssetImage(pydantic.BaseModel):
    """Images from a remote provider"""

    ProviderName: MetaDataProvider
    Url: str
    Height: int
    Width: int
    CommunityRating: float
    VoteCount: int
    Language: str
    Type: str
    RatingType: str


class JellyfinImageResponse(pydantic.BaseModel):
    """Response when querying for jellyfin images"""

    Images: List[RemoteAssetImage]
    TotalRecordCount: int
    Providers: List[MetaDataProvider]


class _JellyfinProxy:
    """Query jellyfin API"""

    _client: JellyfinClient

    def __init__(self) -> None:
        self._client = JellyfinClient()
        self._client.config.app("rkiv", "0.0.1", "beta", "unique_id")
        self._client.config.data["auth.ssl"] = True
        self._client.auth.connect_to_address("http://localhost:8096")
        self._client.auth.login("http://localhost:8096", "rkiv", "rkiv")

    def get_media_folders(self) -> List[JellyfinFolders]:
        """Return list of media folders"""
        return [
            JellyfinFolders(**i)
            for i in self._client.jellyfin.get_media_folders()["Items"]
        ]

    def get_movies(self) -> List[JellyfinMovie]:
        """Get list of jellyfi movies"""
        folder_id = [i.Id for i in self.get_media_folders() if i.Name == "Movies"][0]
        folder_items = self._client.jellyfin.users(
            "/Items", params={"parentId": folder_id, "Fields": "DateCreated, Overview"}
        )["Items"]
        return [JellyfinMovie(**i) for i in folder_items if i["Type"] == "Movie"]

    def get_latest_movies(
        self, start_time: datetime, end_time: datetime
    ) -> List[JellyfinMovie]:
        """Latest movies"""
        movies = self.get_movies()
        return sorted(
            [
                movie
                for movie in movies
                if movie.date_added >= start_time and movie.date_added <= end_time
            ],
            key=lambda x: x.date_added,
            reverse=True,
        )

    def get_asset_art_webp(
        self, id: str, height: int = 300, width: int = 200, quality: int = 16
    ) -> bytes:
        """get_asset_art"""
        url = f"http://localhost:8096/Items/{id}/Images/Primary?fillHeight={height}&fillWidth={width}&quality={quality}"
        img = requests.get(url=url).content
        return img

    def get_movie_img_url(self, id: str) -> str:
        """Only supports TMDB urls"""
        imgs = self._client.jellyfin.items(
            f"/{id}/RemoteImages",
            params={
                "type": "Primary",
                "startIndex": 0,
                "limit": 2,
                "IncludeAllLanguages": False,
            },
        )
        imgage_url: str = imgs["Images"][0]["Url"]
        return imgage_url.replace("original", "w300_and_h450_bestv2")


JellyfinProxy = _JellyfinProxy()
