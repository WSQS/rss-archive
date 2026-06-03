from typing import Tuple
from xml.etree.ElementTree import Element

from rss_archive.config import SourceConfig
from rss_archive.feed import FeedSource, FeedItem

# See also https://www.rssboard.org/rss-specification

def handle_rss(
    source: SourceConfig, root: Element[str]
) -> Tuple[FeedSource, list[FeedItem]]:
    if root.tag != "rss":
        raise ValueError(f"Expected root tag 'rss', got {root.tag!r}")

    channel = root.find("channel")
    if channel is None:
        raise ValueError("Expected 'channel' element under 'rss'")

    feed_source = FeedSource(
        id=source.id,
        title=channel.findtext("title") or "",
        link=channel.findtext("link") or source.feed_url,
        description=channel.findtext("description") or "",
    )

    feed_items: list[FeedItem] = []
    for item in channel.findall("item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        description = item.findtext("description") or ""
        time = item.findtext("pubDate") or ""

        if title == "" and description == "":
            raise ValueError("Expected at least one of 'title' or 'description' in RSS item")

        feed_items.append(
            FeedItem(
                title=title,
                link=link,
                description=description,
                time=time,
                source_id=source.id,
            )
        )

    return feed_source, feed_items
