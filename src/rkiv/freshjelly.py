import requests
import base64
from datetime import datetime
from typing import List


import pydantic
from jellyfin_apiclient_python import JellyfinClient


def get_asset_art_webp(id) -> bytes:
    """get_asset_art"""
    url = f"http://localhost:8096/Items/{id}/Images/Primary?fillHeight=300&fillWidth=200&quality=16"
    img = requests.get(url=url).content
    return img


# def freshjelly(movies: str) -> str:
#     return (
#         "<!DOCTYPE html>"
#         "<html>"
#         "<head>"
#         '<meta name="viewport" content="width=device-width, initial-scale=1">'
#         "</head>"
#         '<body style="background-color: #f6f6f6; font-family: sans-serif; -webkit-font-smoothing: antialiased; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%;">'
#         '<h1 style="color: #00A4DC; margin-left: 20">Movies</h1>'
#         "</body>"
#         "</html>"
#     )


class MovieInfo(pydantic.BaseModel):
    id: str
    name: str
    year: int
    running_time: str
    offical_rating: str
    community_rating: float
    critic_rating: int
    overview: str
    date_added: datetime

    @classmethod
    def from_db(cls, entry: dict) -> "MovieInfo":
        ticks = entry["RunTimeTicks"]
        sec = ticks * (1 / 10_000_000)
        hours = int(sec / 3600)
        minutes = int((sec - hours * 3600) / 60)
        _rating = "NR"
        _critic_rating = 0
        _community_rating = 0
        _overview = ""

        if "OfficialRating" in entry.keys():
            _rating = entry["OfficialRating"]

        if "CommunityRating" in entry.keys():
            _community_rating = round(entry["CommunityRating"], 1)

        if "CriticRating" in entry.keys():
            _critic_rating = int(entry["CriticRating"])

        if "Overview" in entry.keys():
            _overview = entry["Overview"]

        return cls(
            id=entry["Id"],
            name=entry["Name"],
            year=int(entry["ProductionYear"]),
            running_time=f"{hours}h {minutes}m",
            offical_rating=_rating,
            community_rating=_community_rating,
            critic_rating=_critic_rating,
            overview=_overview,
            date_added=datetime.strptime(
                entry["DateCreated"].split("T")[0], "%Y-%m-%d"
            ),
        )


class MovieHTML(pydantic.BaseModel):
    image_layer: str
    info_layer: str
    summary_layer: str

    @classmethod
    def from_movie_info(cls, minfo: MovieInfo) -> "MovieHTML":
        return cls(
            image_layer=f'<div style="width: 319px; padding: 0 0 0 0" align="center">{embedded_image(get_asset_art_webp(minfo.id))}</div>',
            info_layer=movie_info(minfo),
            summary_layer=f'<p style="padding: 0px 5px 0px 5px;">{minfo.overview}</p>',
        )

    def convert(self) -> str:
        s = '<div style="color: #D1D1D1; box-sizing: border-box; display: block; margin: 20px auto auto auto; padding: 30px 0px 0px 0px; background: #2E3436; border-radius: 3px; width: 319px; overflow: auto;">'
        s += self.image_layer
        s += self.info_layer
        s += self.summary_layer
        s += "</div>"
        return s


def embedded_image(img: bytes, fmt: str = "webp") -> str:
    return f'<img src="data:image/{fmt};base64,{base64.b64encode(img).decode()}">'


def get_critic_rating_div(rating: int):
    """Generate a div element with the tomato svg embedded"""
    if rating >= 60:
        with open("fresh.webp", "rb") as f:
            img = f.read()
    else:
        with open("rotten.webp", "rb") as f:
            img = f.read()
    return f'<div style="background-image:url(data:image/webp;base64,{base64.b64encode(img).decode()}); margin:0 0.65em 0 0; padding:0; align-items:center; background-position:0; background-repeat:no-repeat; background-size:auto 1.2em; display:flex; min-height:1.2em; padding-left:1.5em">{rating}</div>'


def movie_tv_title(title: str) -> str:
    """Generate a div hodling the tv/movie title"""
    return f'<div style="flex-direction: column; display:flex; flex-wrap:wrap"><h2>{title}</h2></div>'


def album_artist_title(album: str, artist: str) -> str:
    """Generate a div with the Album Name and Artist"""
    return f'<div style="flex-direction: column; display:flex; flex-wrap:wrap"><h2>{album}</h2><h3>{artist}</h3></div>'


def media_info_item(info: str) -> str:
    return f'<div style="margin:0 0.65em 0 0; padding:0">{info}</div>'


def official_rating(rating: str) -> str:
    return f'<div style="margin:0 0.65em 0 0; padding:0; align-items:center; border:.09em solid; border-radius:.1em; display:flex; font-size:96%; height:1.3em; justify-content:center; line-height:1.8em; padding:0 .6em">{rating}</div>'


def star_rating(stars: str) -> str:
    return f'<div style="margin:0 0.65em 0 0; padding:0; align-items:center; display:flex; justify-content:center; padding-bottom:0; padding-top:0; vertical-align:middle"><span aria-hidden="true">&#11088;</span>{stars}</div>'


def media_info_wrapper(media_info: str) -> str:
    """Div wrapper for all media info types"""
    return f'<div style="margin-bottom:.6em; align-items: center; display:flex;">{media_info}</div>'


def movie_info(info: MovieInfo) -> str:
    s = media_info_item(info.year)
    s += media_info_item(info.running_time)
    s += official_rating(info.offical_rating)
    s += star_rating(info.community_rating)
    s += get_critic_rating_div(info.critic_rating)
    media_info = media_info_wrapper(s)
    title = movie_tv_title(info.name)
    return f'<div style="padding: 0px 0px 0px 3px; background-color: #232425; color: D1D1D1">{title}{media_info}</div>'


def freshjelly(movies: List[MovieHTML]) -> str:
    s = "<!DOCTYPE html>"
    s += "<html>"
    s += "<head>"
    s += '<meta name="viewport" content="width=device-width, initial-scale=1">'
    s += "</head>"
    s += '<body style="background-color: #f6f6f6; font-family: sans-serif; -webkit-font-smoothing: antialiased; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%;">'
    s += '<h1 style="color: #00A4DC; margin-left: 20">Movies</h1>'
    s += "".join([m.convert() for m in movies])
    s += "</body>"
    s += "</html>"
    return s


def jellyfresh() -> None:
    client = JellyfinClient()
    client.config.app("rkiv", "0.0.1", "beta", "unique_id")
    client.config.data["auth.ssl"] = True
    client.auth.connect_to_address("http://localhost:8096")
    client.auth.login("http://localhost:8096", "rkiv", "rkiv")

    # Get Movie, TV, and Music parentIds
    media_folders = client.jellyfin.get_media_folders()["Items"]
    for media_folder in media_folders:
        if media_folder["Name"] == "Movies":
            movie_id = media_folder["Id"]

        # if media_folder["Name"] == "TV Shows":
        #     tv_id = media_folder["Id"]

        # if media_folder["Name"] == "Music":
        #     music_id = media_folder["Id"]

    movies = [
        MovieInfo.from_db(entry=i)
        for i in client.jellyfin.users(
            "/Items", params={"parentId": movie_id, "Fields": "DateCreated, Overview"}
        )["Items"]
        if i["Type"] == "Movie"
    ]

    new_movies = sorted(
        [
            movie
            for movie in movies
            if movie.date_added >= datetime(2023, 5, 28)
            and movie.date_added <= datetime(2023, 6, 2)
        ],
        key=lambda x: x.date_added,
        reverse=True,
    )

    with open("freshjelly.html", "w") as f:
        f.write(freshjelly(movies=[MovieHTML.from_movie_info(m) for m in new_movies]))
