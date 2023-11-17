"""finletter"""
from datetime import datetime

import click

from rkiv.jellyfinproxy import JellyfinProxy
from rkiv.htmlassets import HTMLTemplates
from rkiv.config import Config


CONFIG = Config()


class FreshJelly:
    @staticmethod
    def fresh_jelly(start_time: datetime, end_time: datetime) -> str:
        # greeting = click.edit(editor=CONFIG.editor)
        fresh_movies = JellyfinProxy.get_latest_movies(
            start_time=start_time, end_time=end_time
        )
        movies_html = "".join([m.to_html() for m in fresh_movies])
        return HTMLTemplates.freshjelly(movies_html=movies_html)
