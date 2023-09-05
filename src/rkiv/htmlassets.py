"""htmlassets.py"""
import base64


class HTMLTemplates:
    @staticmethod
    def embedded_image(img: bytes, fmt: str = "webp") -> str:
        return f'<img src="data:image/{fmt};base64,{base64.b64encode(img).decode()}">'

    @staticmethod
    def get_critic_rating_div(rating: int) -> str:
        """Generate a div element with the tomato svg embedded"""
        if rating < 0:
            return ""

        if rating >= 60:
            url = "https://www.rottentomatoes.com/assets/pizza-pie/images/icons/tomatometer/tomatometer-fresh.149b5e8adc3.svg"
        else:
            url = "https://www.rottentomatoes.com/assets/pizza-pie/images/icons/tomatometer/tomatometer-rotten.f1ef4f02ce3.svg"

        return f'<div style="background-image:url({url}); margin:0 0.65em 0 0; padding:0; align-items:center; background-position:0; background-repeat:no-repeat; background-size:auto 1.2em; display:flex; min-height:1.2em; padding-left:1.5em">{rating}</div>'

    @staticmethod
    def movie_tv_title(title: str) -> str:
        """Generate a div hodling the tv/movie title"""
        return f'<div style="flex-direction: column; display:flex; flex-wrap:wrap"><h2>{title}</h2></div>'

    @staticmethod
    def album_artist_title(album: str, artist: str) -> str:
        """Generate a div with the Album Name and Artist"""
        return f'<div style="flex-direction: column; display:flex; flex-wrap:wrap"><h2>{album}</h2><h3>{artist}</h3></div>'

    @staticmethod
    def media_info_item(info: str) -> str:
        return f'<div style="margin:0 0.65em 0 0; padding:0">{info}</div>'

    @staticmethod
    def official_rating(rating: str) -> str:
        return f'<div style="margin:0 0.65em 0 0; padding:0; align-items:center; border:.09em solid; border-radius:.1em; display:flex; font-size:96%; height:1.3em; justify-content:center; line-height:1.8em; padding:0 .6em">{rating}</div>'

    @staticmethod
    def star_rating(stars: float) -> str:
        if stars < 0.0:
            return ""
        return f'<div style="margin:0 0.65em 0 0; padding:0; align-items:center; display:flex; justify-content:center; padding-bottom:0; padding-top:0; vertical-align:middle"><span aria-hidden="true">&#11088;</span>{stars}</div>'

    @staticmethod
    def media_info_wrapper(media_info: str) -> str:
        """Div wrapper for all media info types"""
        return f'<div style="margin-bottom:.6em; align-items: center; display:flex;">{media_info}</div>'

    @staticmethod
    def media_banner_wrapper(title: str, media_info: str) -> str:
        """Div wrapper for media banner"""
        return f'<div style="padding: 0px 0px 0px 3px; background-color: #232425; color: D1D1D1">{title}{media_info}</div>'

    @staticmethod
    def movie_image_div(image_url: str) -> str:
        """Div containing the movie image"""
        return f'<div style="padding: 0 0 0 0" align="center"><img src="{image_url}" style="width: 250px"></div>'

    @staticmethod
    def movie_card(contents: str) -> str:
        """Div to wrap all movie info contents"""
        return f'<div style="color: #D1D1D1; box-sizing: border-box; display: block; margin: 20px auto auto auto; padding: 30px 0px 0px 0px; background: #2E3436; border-radius: 3px; width: 319px; overflow: auto;">{contents}</div>'

    @staticmethod
    def movie_summary(overview: str) -> str:
        return f'<p style="padding: 0px 5px 0px 5px;">{overview}</p>'

    @staticmethod
    def freshjelly(movies_html: str) -> str:
        s = "<!DOCTYPE html>"
        s += "<html>"
        s += "<head>"
        s += '<meta name="viewport" content="width=device-width, initial-scale=1">'
        s += "</head>"
        s += '<body style="background-color: #f6f6f6; font-family: sans-serif; -webkit-font-smoothing: antialiased; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%;">'
        s += '<h1 style="color: #00A4DC; margin-left: 20">Movies</h1>'
        s += movies_html
        s += "</body>"
        s += "</html>"
        return s
