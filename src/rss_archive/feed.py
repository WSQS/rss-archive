
from dataclasses import dataclass
from typing import Any

@dataclass
class FeedSource:
    # Comes from the user config.
    id: str
    title: str
    link: str
    description: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]):
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            link=d.get("link", ""),
            description=d.get("description", ""),
        )

@dataclass
class FeedItem:
    # Missing parsed fields use empty strings.
    # At least one of `title` or `description` must be non-empty.
    title: str
    link: str
    description: str
    source_id: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]):
        return cls(
            title=d.get("title", ""),
            link=d.get("link", ""),
            description=d.get("description", ""),
            source_id=d.get("source_id", ""),
        )

@dataclass
class FeedArchive:
    feed_sources: list[FeedSource]
    feed_items: list[FeedItem]

    @classmethod
    def from_dict(cls, d: dict[str, Any]):
        return cls(
            feed_sources=[
                FeedSource.from_dict(feed_source)
                for feed_source in d.get("feed_sources", [])
            ],
            feed_items=[
                FeedItem.from_dict(feed_item)
                for feed_item in d.get("feed_items", [])
            ],
        )