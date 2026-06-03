from typing import Tuple
from xml.etree.ElementTree import Element

from rss_archive.config import SourceConfig
from rss_archive.feed import FeedItem, FeedSource, normalize_time


def handle_atom(
    source: SourceConfig, root: Element[str]
) -> Tuple[FeedSource, list[FeedItem]]:
    if root.tag not in ("feed", "{http://www.w3.org/2005/Atom}feed"):
        raise ValueError(f"Expected root tag 'feed', got {root.tag!r}")

    feed_link = source.feed_url
    for link_element in root.findall("{*}link"):
        href = link_element.attrib.get("href", "")
        if href == "":
            continue
        if link_element.attrib.get("rel", "alternate") == "alternate":
            feed_link = href
            break
        if feed_link == source.feed_url:
            feed_link = href

    feed_source = FeedSource(
        id=source.id,
        title=root.findtext("{*}title") or "",
        link=feed_link,
        description=root.findtext("{*}subtitle") or "",
    )

    feed_items: list[FeedItem] = []
    for entry in root.findall("{*}entry"):
        title = entry.findtext("{*}title") or ""

        entry_link = ""
        for link_element in entry.findall("{*}link"):
            href = link_element.attrib.get("href", "")
            if href == "":
                continue
            if link_element.attrib.get("rel", "alternate") == "alternate":
                entry_link = href
                break
            if entry_link == "":
                entry_link = href

        description = ""
        content = entry.find("{*}content")
        if content is not None:
            description = "".join(content.itertext()).strip()
        if description == "":
            summary = entry.find("{*}summary")
            if summary is not None:
                description = "".join(summary.itertext()).strip()
        time = normalize_time(
            entry.findtext("{*}published") or entry.findtext("{*}updated") or ""
        )

        if title == "" and description == "":
            raise ValueError("Expected at least one of 'title' or 'description' in Atom entry")

        feed_items.append(
            FeedItem(
                title=title,
                link=entry_link,
                description=description,
                time=time,
                source_id=source.id,
            )
        )

    return feed_source, feed_items