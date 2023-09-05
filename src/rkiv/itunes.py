"""itunes.py"""

import pandas

from rkiv.config import Config


_CONFIG = Config()


class ItunesLibrary:
    """iTunes Library"""

    __slots__ = ("data",)

    data: pandas.DataFrame

    __annotations__ = {
        "data": pandas.DataFrame,
    }

    def __init__(self, data: pandas.DataFrame) -> None:
        self.data = data
