from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any


@dataclass
class SourceConfig:
    id: str
    title: str
    feed_url: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]):
        return cls(
            id=d["id"],
            title=d["title"],
            feed_url=d["feed_url"],
        )


def main():
    print("Hello from rss-archive!")
    with Path("config/source.toml").open("rb") as f:
        raw_source: list[dict[str, Any]] = tomllib.load(f).get("source", [])
    sources = [SourceConfig.from_dict(source) for source in raw_source]
    print(sources)


if __name__ == "__main__":
    main()
