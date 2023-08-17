""" Wrapper module for MakeMKV """
import requests
from typing import List
from html.parser import HTMLParser


class MakeMKVBetaKeyParser(HTMLParser):
    key: str = ""
    data: List[str] = []

    def handle_data(self, data: str) -> None:
        self.data.append(data)
        if "T-" in data:
            self.key = data

    def scrape_reg_key(self) -> str:
        page = requests.get("https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053")
        self.feed(page.content.decode("utf-8"))
        return self.key

