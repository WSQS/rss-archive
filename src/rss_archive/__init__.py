import tomllib
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from xml.etree import ElementTree

from rss_archive.config import DataConfig, SourceConfig
from rss_archive.rss import handle_rss


def main():
    print("Hello from rss-archive!")
    with Path("config/source.toml").open("rb") as f:
        raw_source: list[dict[str, Any]] = tomllib.load(f).get("source", [])
    sources = [SourceConfig.from_dict(source) for source in raw_source]
    with Path("config/data.toml").open("rb") as f:
        data_config = DataConfig.from_dict(tomllib.load(f))
    for source in sources:
        print(f"Handle: {source.id}")
        with urlopen(source.feed_url) as response:
            xml = response.read().decode("utf-8")
        root = ElementTree.fromstring(xml)
        if root.tag == "rss":
            feed_source, feed_items = handle_rss(source, root)
            print(f"Feed Source: {feed_source.title}")
            for item in feed_items:
                print(f"  - {item.title}")
