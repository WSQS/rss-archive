from typing import Tuple
from xml.etree.ElementTree import Element

from rss_archive.config import SourceConfig
from rss_archive.feed import FeedSource, FeedItem


def handle_rss(
    source: SourceConfig, root: Element[str]
) -> Tuple[FeedSource, list[FeedItem]]:
    if root.tag != "rss":
        raise ValueError(f"Expected root tag 'rss', got {root.tag!r}")

