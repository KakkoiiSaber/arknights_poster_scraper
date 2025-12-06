from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mwparserfromhell
import requests
from mwparserfromhell.nodes.heading import Heading
from mwparserfromhell.nodes.template import Template


RAW_URL = (
    "https://prts.wiki/w/%E5%AE%98%E6%96%B9%E5%AE%A3%E4%BC%A0%E5%9B%BE%E4%B8%80%E8%A7%88"
    "?action=raw"
)
META_CACHE_PATH = Path("cache/meta_cache.json")


def normalize_wiki_value(value: Any) -> str:
    """Unescape common wiki placeholders like `{{=}}` and trim whitespace."""
    text = str(value)
    return text.replace("{{=}}", "=").replace("{{!}}", "|").strip()


def fetch_wikitext(url: str) -> str:
    """Download the raw wikitext for the page."""
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_link_field(raw_link: str) -> tuple[str, str]:
    """
    Convert a wiki link field like `[https://... label]` into (url, label).
    The label is treated as the poster name.
    """
    cleaned = normalize_wiki_value(raw_link).strip("[]")
    if not cleaned:
        return "", ""
    if " " in cleaned:
        url, label = cleaned.split(None, 1)
    else:
        url, label = cleaned, ""
    return url, label


def extract_posters(wikitext: str) -> list[dict[str, Any]]:
    """
    Parse all `{{微博}}` templates and collect poster metadata.

    Category and year are tracked by the nearest level-2 and level-3 headings
    respectively, matching the table of contents on the wiki page.
    """
    code = mwparserfromhell.parse(wikitext)
    posters: list[dict[str, Any]] = []
    current_category: str | None = None
    current_year: str | None = None

    for node in code.nodes:
        if isinstance(node, Heading):
            level = node.level
            title = str(node.title.strip_code()).strip()
            if level == 2:
                current_category = title
                current_year = None
            elif level == 3:
                current_year = title
            continue
        if not isinstance(node, Template) or not node.name.matches("微博"):
            continue
        template = node

        link_field = template.get(1).value if template.has(1) else ""
        weibo_url, title = parse_link_field(str(link_field))

        description = ""
        if template.has(2):
            description = template.get(2).value.strip_code().strip()

        image_urls: list[str] = []
        for param in template.params:
            name = str(param.name).strip()
            if name.isdigit() and int(name) >= 3:
                url = normalize_wiki_value(param.value)
                if url:
                    image_urls.append(url)

        posters.append(
            {
                "title": title,
                "weibo_url": weibo_url,
                "description": description,
                "images": image_urls,
                "category": current_category,
                "year": current_year,
            }
        )

    return posters


def main() -> None:
    wikitext = fetch_wikitext(RAW_URL)
    posters = extract_posters(wikitext)

    payload = {"source": RAW_URL, "count": len(posters), "posters": posters}

    META_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Wrote {len(posters)} poster entries to {META_CACHE_PATH}")


if __name__ == "__main__":
    main()
