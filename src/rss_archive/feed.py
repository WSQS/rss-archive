
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
    time: str
    source_id: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]):
        return cls(
            title=d.get("title", ""),
            link=d.get("link", ""),
            description=d.get("description", ""),
            time=d.get("time", ""),
            source_id=d.get("source_id", ""),
        )

@dataclass
class FeedArchive:
    feed_sources: list[FeedSource]
    feed_items: list[FeedItem]

    def upsert_source(self, feed_source: FeedSource):
        for i, existing_feed_source in enumerate(self.feed_sources):
            if existing_feed_source.id == feed_source.id:
                self.feed_sources[i] = feed_source
                return

        self.feed_sources.append(feed_source)

    def merge_items(self, feed_items: list[FeedItem]):
        for feed_item in feed_items:
            exists = False
            for existing_feed_item in self.feed_items:
                if existing_feed_item.source_id != feed_item.source_id:
                    continue
                if feed_item.link != "" and existing_feed_item.link == feed_item.link:
                    exists = True
                    break
                if (
                    feed_item.link == ""
                    and existing_feed_item.title == feed_item.title
                    and existing_feed_item.description == feed_item.description
                ):
                    exists = True
                    break
            if not exists:
                self.feed_items.append(feed_item)

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