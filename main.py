from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen
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
    for source in sources:
        print(f"Handle: {source.title}")
        with urlopen(source.feed_url) as response:
            xml = response.read().decode("utf-8")
        print(xml)


if __name__ == "__main__":
    main()
