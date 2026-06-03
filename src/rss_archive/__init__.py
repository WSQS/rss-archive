from dataclasses import asdict
import json
import tomllib
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from xml.etree import ElementTree

from rss_archive.atom import handle_atom
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
            feed_archive.upsert_source(feed_source)
            feed_archive.merge_items(feed_items)

            print(f"Feed Source: {feed_source.title}")
            for item in feed_items:
                print(f"  - {item.title}")
        elif root.tag in ("feed", "{http://www.w3.org/2005/Atom}feed"):
            feed_source, feed_items = handle_atom(source, root)
            feed_archive.upsert_source(feed_source)
            feed_archive.merge_items(feed_items)

            print(f"Feed Source: {feed_source.title}")
            for item in feed_items:
                print(f"  - {item.title}")
        else:
            print(f"Unknown root tag: {root.tag!r}")

    print(f"Merged archive: {len(feed_archive.feed_sources)} sources, {len(feed_archive.feed_items)} items")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with archive_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(feed_archive), f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote archive to: {archive_path}")
