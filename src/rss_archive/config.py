from dataclasses import dataclass
from typing import Any


@dataclass
class SourceConfig:
    id: str
    feed_url: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]):
        return cls(
            id=d["id"],
            feed_url=d["feed_url"],
        )
