
from dataclasses import dataclass

@dataclass
class FeedSource:
    # Comes from the user config.
    id: str
    title: str
    link: str
    description: str

@dataclass
class FeedItem:
    # At least one of `title` or `description` must be non-empty.
    title: str
    link: str
    description: str
    source_id: str

@dataclass
class FeedArchive:
    feed_sources: list[FeedSource]
    feed_items: list[FeedItem]