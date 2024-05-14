"""finletter"""
from datetime import datetime

import click

from rkiv.jellyfinproxy import JellyfinProxy
from rkiv.htmlassets import HTMLTemplates
from rkiv.config import Config


CONFIG = Config()


class FinLetter:
    """Build HTML newsletters for the jellyfin server"""

    @staticmethod
    def fresh_jelly(start_time: datetime, end_time: datetime, greet: bool = False) -> str:
        greeting = ""
        if greet:
            _greeting = click.edit(editor=CONFIG.editor)
            if _greeting is not None:
                greeting = _greeting.rstrip()

        fresh_movies = JellyfinProxy.get_latest_movies(start_time=start_time, end_time=end_time)
        movies_html = "".join([m.to_html() for m in fresh_movies])

        fresh_series = JellyfinProxy.get_latest_series(start_time=start_time, end_time=end_time)
        series_html = "".join([s.to_html() for s in fresh_series])

        return HTMLTemplates.freshjelly(greeting=greeting, movies_html=movies_html, series_html=series_html)
