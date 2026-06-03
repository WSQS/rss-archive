import json
import tomllib
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from xml.etree import ElementTree

from rss_archive.config import DataConfig, SourceConfig
from rss_archive.feed import FeedArchive
from rss_archive.rss import handle_rss


def main():
    print("Hello from rss-archive!")
    with Path("config/source.toml").open("rb") as f:
        raw_source: list[dict[str, Any]] = tomllib.load(f).get("source", [])
    sources = [SourceConfig.from_dict(source) for source in raw_source]
    with Path("config/data.toml").open("rb") as f:
        data_config = DataConfig.from_dict(tomllib.load(f))
    archive_path = Path(data_config.archive)
    if archive_path.exists():
        with archive_path.open("r", encoding="utf-8") as f:
            feed_archive = FeedArchive.from_dict(json.load(f))
    else:
        feed_archive = FeedArchive.from_dict({})
    print(f"Loaded archive: {len(feed_archive.feed_sources)} sources, {len(feed_archive.feed_items)} items")

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
