from dataclasses import asdict
import json
import tomllib
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from xml.etree import ElementTree

from rss_archive.atom import handle_atom
from rss_archive.config import DataConfig, SourceConfig
from rss_archive.feed import FeedArchive
from rss_archive.rss import handle_rss


def main():
    print("Hello from rss-archive!")
    with Path("config/source.toml").open("rb") as f:
        raw_source: list[dict[str, Any]] = tomllib.load(f).get("source", [])
    sources = [SourceConfig.from_dict(source) for source in raw_source]
    with Path("config/data.toml").open("rb") as f:
        data_config = DataConfig.from_dict(tomllib.load(f))
    archive_path = Path(data_config.archive)
    if archive_path.exists():
        with archive_path.open("r", encoding="utf-8") as f:
            feed_archive = FeedArchive.from_dict(json.load(f))
    else:
        feed_archive = FeedArchive.from_dict({})
    print(f"Loaded archive: {len(feed_archive.feed_sources)} sources, {len(feed_archive.feed_items)} items")

    for source in sources:
        print(f"Handle: {source.id}")
        with urlopen(source.feed_url) as response:
            xml = response.read().decode("utf-8")
        root = ElementTree.fromstring(xml)
        if root.tag == "rss":
            feed_source, feed_items = handle_rss(source, root)
            feed_archive.upsert_source(feed_source)
            feed_archive.merge_items(feed_items)

            print(f"Feed Source: {feed_source.title}")
            for item in feed_items:
                print(f"  - {item.title}")
        elif root.tag in ("feed", "{http://www.w3.org/2005/Atom}feed"):
            feed_source, feed_items = handle_atom(source, root)
            feed_archive.upsert_source(feed_source)
            feed_archive.merge_items(feed_items)

            print(f"Feed Source: {feed_source.title}")
            for item in feed_items:
                print(f"  - {item.title}")
        else:
            print(f"Unknown root tag: {root.tag!r}")

    print(f"Merged archive: {len(feed_archive.feed_sources)} sources, {len(feed_archive.feed_items)} items")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_json = json.dumps(asdict(feed_archive), ensure_ascii=False, indent=2)
    with archive_path.open("w", encoding="utf-8") as f:
        f.write(archive_json)
        f.write("\n")
    print(f"Wrote archive to: {archive_path}")

    website_directory = Path(data_config.website_directory)
    website_directory.mkdir(parents=True, exist_ok=True)
    index_path = website_directory / "index.html"
    html_archive_json = (
        archive_json.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    index_html = f"""<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Feed Archive</title>
        <style>
            body {{
                font-family: sans-serif;
                margin: 2rem;
            }}

            table {{
                border-collapse: collapse;
                margin-bottom: 2rem;
                width: 100%;
            }}

            th,
            td {{
                border: 1px solid #ccc;
                padding: 0.5rem;
                text-align: left;
                vertical-align: top;
            }}

            th {{
                background: #f5f5f5;
            }}

            td.description {{
                max-width: 32rem;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }}
        </style>
  </head>
  <body>
    <h1>Feed Archive</h1>
    <p>Sources: {len(feed_archive.feed_sources)} / Items: {len(feed_archive.feed_items)}</p>

        <h2>Feed Sources</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Link</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody id=\"feed-sources-body\"></tbody>
        </table>

        <h2>Feed Items</h2>
        <table>
            <thead>
                <tr>
                    <th>Source ID</th>
                    <th>Title</th>
                    <th>Link</th>
                    <th>Description</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody id=\"feed-items-body\"></tbody>
        </table>

    <script id=\"feed-archive-data\" type=\"application/json\">{html_archive_json}</script>
    <script>
      const feedArchive = JSON.parse(document.getElementById("feed-archive-data").textContent);

            function appendTextCell(row, value, className) {{
                const cell = document.createElement("td");
                if (className) {{
                    cell.className = className;
                }}
                cell.textContent = value ?? "";
                row.appendChild(cell);
            }}

            function appendLinkCell(row, value) {{
                const cell = document.createElement("td");
                if (typeof value === "string" && (value.startsWith("https://") || value.startsWith("http://"))) {{
                    const link = document.createElement("a");
                    link.href = value;
                    link.textContent = value;
                    link.target = "_blank";
                    link.rel = "noopener noreferrer";
                    cell.appendChild(link);
                }} else {{
                    cell.textContent = value ?? "";
                }}
                row.appendChild(cell);
            }}

            const feedSourcesBody = document.getElementById("feed-sources-body");
            for (const feedSource of feedArchive.feed_sources) {{
                const row = document.createElement("tr");
                appendTextCell(row, feedSource.id);
                appendTextCell(row, feedSource.title);
                appendLinkCell(row, feedSource.link);
                appendTextCell(row, feedSource.description, "description");
                feedSourcesBody.appendChild(row);
            }}

            const feedItemsBody = document.getElementById("feed-items-body");
            const sortedFeedItems = [...feedArchive.feed_items].sort((a, b) => {{
                if (a.time === b.time) {{
                    return 0;
                }}
                if (a.time === "") {{
                    return 1;
                }}
                if (b.time === "") {{
                    return -1;
                }}
                return b.time.localeCompare(a.time);
            }});
            for (const feedItem of sortedFeedItems) {{
                const row = document.createElement("tr");
                appendTextCell(row, feedItem.source_id);
                appendTextCell(row, feedItem.title);
                appendLinkCell(row, feedItem.link);
                appendTextCell(row, feedItem.description, "description");
                appendTextCell(row, feedItem.time);
                feedItemsBody.appendChild(row);
            }}
    </script>
  </body>
</html>
"""
    with index_path.open("w", encoding="utf-8") as f:
        f.write(index_html)
        f.write("\n")
    print(f"Wrote index to: {index_path}")
    
