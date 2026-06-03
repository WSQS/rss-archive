import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from xml.etree import ElementTree


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
        root = ElementTree.fromstring(xml)
        if root.tag == "rss":
            for item in root:
                if item.tag == "channel":
                    for item in item:
                        match item.tag:
                            case "title":
                                print(f"Title: {item.text}")
                            case "link":
                                print(f"Link: {item.text}")
                            case "description":
                                print(f"Description: {item.text}")
                            case "item":
                                for item in item:
                                    match item.tag:
                                        case "title":
                                            print(f"Title: {item.text}")
                                        case _:
                                            pass
                            case _:
                                print(f"Unknown Handle: {item.tag}")


if __name__ == "__main__":
    main()
