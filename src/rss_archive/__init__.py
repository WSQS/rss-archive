import json
import shutil
import tomllib
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ParseError

from rss_archive.atom import handle_atom
from rss_archive.config import DataConfig, SourceConfig
from rss_archive.feed import FeedArchive
from rss_archive.rss import handle_rss

# Cell-level DOM helpers shared by every page. Copied verbatim into the
# website directory at build time; each generated page references it and owns
# its own inline orchestration logic.
RENDER_JS_SOURCE = (
    Path(__file__).resolve().parent.parent.parent / "static" / "render.js"
)

# Shared stylesheet. Copied verbatim into the website directory at build time;
# every generated page references it via a <link> element.
STYLE_CSS_SOURCE = (
    Path(__file__).resolve().parent.parent.parent / "static" / "style.css"
)

# Inter font files (latin subset, weights 400/500/600). Downloaded at build
# time from the jsDelivr-served @fontsource/inter package (stable pinned URL,
# no UA sniffing, OFL-1.1). Cached under static/fonts/ so repeat builds don't
# re-fetch. If a download fails the build continues; the stylesheet's
# font-family falls back to system-ui, so a font fetch failure never breaks
# the site.
FONTS_SOURCE = Path(__file__).resolve().parent.parent.parent / "static" / "fonts"
INTER_WEIGHTS = (400, 500, 600)
INTER_VERSION = "5.2.8"
INTER_FONT_URL = (
    "https://cdn.jsdelivr.net/npm/@fontsource/inter@"
    + INTER_VERSION
    + "/files/inter-latin-{weight}-normal.woff2"
)


def ensure_inter_fonts() -> None:
    """Ensure Inter woff2 files are present under static/fonts/.

    Downloads each missing weight from jsDelivr (cached on disk afterward).
    Silently degrades on network failure — a missing file just means the
    @font-face rule won't resolve and the system-font fallback is used.
    """
    FONTS_SOURCE.mkdir(parents=True, exist_ok=True)
    for weight in INTER_WEIGHTS:
        dest = FONTS_SOURCE / f"inter-latin-{weight}.woff2"
        if dest.exists():
            continue
        try:
            with urlopen(INTER_FONT_URL.format(weight=weight)) as response:
                dest.write_bytes(response.read())
            print(f"  fetched Inter {weight} -> {dest.name}")
        except (HTTPError, URLError) as e:
            print(f"  font fetch failed for Inter {weight}: {e} (will fall back)")


def escape_for_html(text: str) -> str:
    """Escape `&`, `<`, `>` as JSON-style \\uXXXX so a JSON blob is safe to
    inline inside an HTML <script type="application/json"> block."""
    return text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def write_html_file(path: Path, html: str) -> None:
    """Write `html` to `path`, followed by a trailing newline."""
    with path.open("w", encoding="utf-8") as f:
        f.write(html)
        f.write("\n")


class Page:
    """A fluent builder for an HTML page.

    Title is set at construction. Chain .stylesheet_append() (lands in
    <head>), .script_append() and .body_append() (both land in <body>) to
    describe the page, then .render() for the full HTML document string.

    External scripts are rendered at the top of <body>, ahead of all body
    content, so a page can load a library (e.g. render.js) before its
    inline script runs — without the caller having to order .script_append
    before the body fragment that uses it.
    """

    def __init__(self, title: str):
        self._title = title
        self._stylesheets: list[str] = []
        self._scripts: list[str] = []
        self._body_parts: list[str] = []

    def stylesheet_append(self, href: str) -> Page:
        """Append a <link rel=stylesheet href=...> to <head>."""
        self._stylesheets.append(href)
        return self

    def script_append(self, src: str) -> Page:
        """Append an external <script src=...>; rendered atop <body>."""
        self._scripts.append(src)
        return self

    def body_append(self, html: str) -> Page:
        """Append an HTML fragment to <body>."""
        self._body_parts.append(html)
        return self

    def render(self) -> str:
        """Return the full HTML document as a string."""
        links = "".join(
            f'    <link rel="stylesheet" href="{href}" />\n'
            for href in self._stylesheets
        )
        scripts = "".join(
            f'    <script src="{src}"></script>\n' for src in self._scripts
        )
        body = "".join(self._body_parts)
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "  <head>\n"
            '    <meta charset="utf-8" />\n'
            '    <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            f"    <title>{self._title}</title>\n"
            f"{links}"
            "  </head>\n"
            "  <body>\n"
            f"{scripts}"
            f"{body}"
            "  </body>\n"
            "</html>\n"
        )


def main():
    print("Hello from rss-archive!")
    ensure_inter_fonts()
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
    print(
        f"Loaded archive: {len(feed_archive.feed_sources)} sources, {len(feed_archive.feed_items)} items"
    )

    errors: list[dict[str, str]] = []

    for source in sources:
        print(f"Handle: {source.id}")
        try:
            request = Request(
                source.feed_url,
                headers={
                    "User-Agent": "rss-archive/1.0 (+https://github.com/WSQS/rss-archive)",
                    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
                },
            )
            with urlopen(request) as response:
                xml = response.read().decode("utf-8")
            root = ET.fromstring(xml)
        except HTTPError as e:
            print(f"  HTTP error {e.code} for {source.feed_url}: {e.reason}")
            errors.append(
                {
                    "source_id": source.id,
                    "feed_url": source.feed_url,
                    "type": "HTTP",
                    "message": f"HTTP {e.code}: {e.reason}",
                }
            )
            continue
        except URLError as e:
            print(f"  URL error for {source.feed_url}: {e.reason}")
            errors.append(
                {
                    "source_id": source.id,
                    "feed_url": source.feed_url,
                    "type": "Network",
                    "message": f"URL error: {e.reason}",
                }
            )
            continue
        except ParseError as e:
            print(f"  XML parse error for {source.feed_url}: {e}")
            errors.append(
                {
                    "source_id": source.id,
                    "feed_url": source.feed_url,
                    "type": "XML Parse",
                    "message": str(e),
                }
            )
            continue
        except Exception as e:
            print(f"  Unexpected error for {source.feed_url}: {e}")
            errors.append(
                {
                    "source_id": source.id,
                    "feed_url": source.feed_url,
                    "type": "Unexpected",
                    "message": str(e),
                }
            )
            continue

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
            msg = f"Unknown root tag: {root.tag!r}"
            print(f"  {msg} for {source.feed_url}")
            errors.append(
                {
                    "source_id": source.id,
                    "feed_url": source.feed_url,
                    "type": "Unknown Format",
                    "message": msg,
                }
            )

    print(
        f"Merged archive: {len(feed_archive.feed_sources)} sources, {len(feed_archive.feed_items)} items"
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_json = json.dumps(asdict(feed_archive), ensure_ascii=False, indent=2)
    with archive_path.open("w", encoding="utf-8") as f:
        f.write(archive_json)
        f.write("\n")
    print(f"Wrote archive to: {archive_path}")

    website_directory = Path(data_config.website_directory)
    website_directory.mkdir(parents=True, exist_ok=True)
    index_path = website_directory / "index.html"
    page_updated_time = (
        datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    html_archive_json = escape_for_html(archive_json)
    errors_json = json.dumps(errors, ensure_ascii=False, indent=2)
    html_errors_json = escape_for_html(errors_json)
    index_html = (
        Page("Feed Archive")
        .stylesheet_append("style.css")
        .script_append("render.js")
        .body_append(f"""    <div class="wrap">
    <h1>Feed Archive</h1>
    <p class="meta">Sources: {len(feed_archive.feed_sources)} / Items: {len(feed_archive.feed_items)} · Page updated: <time datetime="{page_updated_time}">{page_updated_time}</time></p>

    <h2>Feed Sources</h2>
    <ul class="cards" id="feed-sources-body"></ul>

    <h2 id="errors-heading">Errors</h2>
    <ul class="cards" id="errors-body"></ul>

    <h2>Feed Items</h2>
    <ul class="cards" id="feed-items-body"></ul>
</div>
""")
        .body_append(f"""    <script id="feed-archive-data" type="application/json">{html_archive_json}</script>
    <script id="feed-errors-data" type="application/json">{html_errors_json}</script>
""")
        .body_append(f"""    <script>
      const feedArchive = JSON.parse(document.getElementById("feed-archive-data").textContent);
      const feedErrors = JSON.parse(document.getElementById("feed-errors-data").textContent);

            const feedSourcesBody = document.getElementById("feed-sources-body");
            for (const feedSource of feedArchive.feed_sources) {{
                const row = document.createElement("li");
                row.className = "card";
                // ID cell links to the per-source page; text and href differ, so
                // build it inline rather than via appendLinkCell.
                const idCell = document.createElement("span");
                idCell.className = "col-id";
                const idLink = document.createElement("a");
                idLink.href = `source/${{encodeURIComponent(feedSource.id)}}.html`;
                idLink.textContent = feedSource.id;
                idCell.appendChild(idLink);
                row.appendChild(idCell);
                appendTextCell(row, feedSource.title, "col-dim");
                feedSourcesBody.appendChild(row);
            }}

            const errorsBody = document.getElementById("errors-body");
            const errorsHeading = document.getElementById("errors-heading");
            if (feedErrors.length === 0) {{
                errorsHeading.classList.add("errors-empty");
                errorsBody.classList.add("errors-empty");
            }} else {{
                for (const err of feedErrors) {{
                    const row = document.createElement("li");
                    row.className = "card";
                    appendTextCell(row, err.source_id, "col-tag");
                    appendLinkCell(row, err.feed_url, "col-dim");
                    appendTextCell(row, err.type, "col-tag");
                    appendTextCell(row, err.message, "col-dim");
                    errorsBody.appendChild(row);
                }}
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
                const row = document.createElement("li");
                row.className = "card";
                // Title is a link to the original item; text and href differ,
                // so build it inline rather than via appendLinkCell.
                const titleCell = document.createElement("span");
                titleCell.className = "col-title";
                if (feedItem.link) {{
                    const a = document.createElement("a");
                    a.href = feedItem.link;
                    a.textContent = feedItem.title;
                    a.target = "_blank";
                    a.rel = "noopener noreferrer";
                    titleCell.appendChild(a);
                }} else {{
                    titleCell.textContent = feedItem.title;
                }}
                row.appendChild(titleCell);
                appendTextCell(row, feedItem.source_id, "col-tag");
                appendTextCell(row, feedItem.time, "col-time");
                feedItemsBody.appendChild(row);
            }}
    </script>
""")
        .render()
    )
    write_html_file(index_path, index_html)
    print(f"Wrote index to: {index_path}")

    # Shared static assets — one copy of each for the whole site.
    shutil.copyfile(RENDER_JS_SOURCE, website_directory / "render.js")
    shutil.copyfile(STYLE_CSS_SOURCE, website_directory / "style.css")
    fonts_dest = website_directory / "fonts"
    fonts_dest.mkdir(parents=True, exist_ok=True)
    for weight in INTER_WEIGHTS:
        src_font = FONTS_SOURCE / f"inter-latin-{weight}.woff2"
        if src_font.exists():
            shutil.copyfile(src_font, fonts_dest / src_font.name)

    # Per-source pages: one static .html per source in the archive, filtered to
    # that source's items. Sources are taken from the archive (what actually
    # fetched), not the config, so sources that never resolved get no page.
    source_directory = website_directory / "source"
    source_directory.mkdir(parents=True, exist_ok=True)
    for feed_source in feed_archive.feed_sources:
        source_items = [
            item for item in feed_archive.feed_items if item.source_id == feed_source.id
        ]
        source_items_json = escape_for_html(
            json.dumps(
                [asdict(item) for item in source_items], ensure_ascii=False, indent=2
            )
        )
        source_meta_json = escape_for_html(
            json.dumps(asdict(feed_source), ensure_ascii=False, indent=2)
        )
        source_html = (
            Page(f"{feed_source.title} — Feed Archive")
            .stylesheet_append("../style.css")
            .script_append("../render.js")
            .body_append(f"""    <div class="wrap">
    <p class="meta"><a href="../index.html">← All items</a></p>
    <h1>{feed_source.title}</h1>
    <p class="meta">Items: {len(source_items)} · Page updated: <time datetime="{page_updated_time}">{page_updated_time}</time></p>

    <h2>Feed Items</h2>
    <ul class="cards" id="feed-items-body"></ul>
</div>
""")
            .body_append(f"""    <script id="source-items-data" type="application/json">{source_items_json}</script>
    <script id="source-meta-data" type="application/json">{source_meta_json}</script>
""")
            .body_append(f"""    <script>
      const sourceMeta = JSON.parse(document.getElementById("source-meta-data").textContent);
      const sourceItems = JSON.parse(document.getElementById("source-items-data").textContent);

            const feedItemsBody = document.getElementById("feed-items-body");
            const sortedSourceItems = [...sourceItems].sort((a, b) => {{
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
            for (const feedItem of sortedSourceItems) {{
                const row = document.createElement("li");
                row.className = "card";
                // Title is a link to the original item; text and href differ,
                // so build it inline rather than via appendLinkCell.
                const titleCell = document.createElement("span");
                titleCell.className = "col-title";
                if (feedItem.link) {{
                    const a = document.createElement("a");
                    a.href = feedItem.link;
                    a.textContent = feedItem.title;
                    a.target = "_blank";
                    a.rel = "noopener noreferrer";
                    titleCell.appendChild(a);
                }} else {{
                    titleCell.textContent = feedItem.title;
                }}
                row.appendChild(titleCell);
                appendTextCell(row, feedItem.time, "col-time");
                feedItemsBody.appendChild(row);
            }}
    </script>
""")
            .render()
        )
        source_path = source_directory / f"{feed_source.id}.html"
        write_html_file(source_path, source_html)
        print(f"Wrote source page to: {source_path}")
