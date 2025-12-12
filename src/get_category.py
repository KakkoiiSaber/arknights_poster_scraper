from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


META_CACHE_PATH = Path("cache/meta_cache.json")
CATEGORY_CACHE_PATH = Path("cache/category_cache.json")
FALLBACK_CATEGORY = "Uncategorized"


def load_meta(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Meta cache not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_categories(meta: dict) -> list[dict[str, object]]:
    posters = meta.get("posters", [])
    counter: Counter[str] = Counter()

    for poster in posters:
        category = (poster.get("category") or FALLBACK_CATEGORY).strip()
        counter[category] += 1

    summary = [
        {"name": name, "count": count}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]
    return summary


def save_summary(path: Path, summary: list[dict[str, object]], total: int) -> None:
    payload = {
        "source": str(META_CACHE_PATH),
        "total_items": total,
        "total_categories": len(summary),
        "categories": summary,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    meta = load_meta(META_CACHE_PATH)
    summary = summarize_categories(meta)
    total_items = len(meta.get("posters", []))
    save_summary(CATEGORY_CACHE_PATH, summary, total_items)
    print(
        f"Wrote {len(summary)} categories "
        f"covering {total_items} items to {CATEGORY_CACHE_PATH}"
    )


if __name__ == "__main__":
    main()
