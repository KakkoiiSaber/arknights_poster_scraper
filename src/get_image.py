from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


META_CACHE_PATH = Path("cache/meta_cache.json")
IMAGE_CACHE_PATH = Path("cache/image_cache.json")
ASSETS_DIR = Path("assets")


def load_json(path: Path) -> dict[str, str]:
    """Load JSON from disk, returning an empty dict on missing/blank/invalid files."""
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def save_json(path: Path, payload: dict[str, str]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sanitize_title(title: str) -> str:
    """Create a filesystem-friendly string while keeping the original readable."""
    cleaned = re.sub(r"\s+", "_", title.strip())
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_") or "image"


def filename_from_title(title: str, url: str, index: int, total: int) -> tuple[str, str]:
    """Return (base_name, extension)."""
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix
    if not ext:
        ext = ".jpg"

    base_title = sanitize_title(title) or sanitize_title(Path(parsed.path).stem)
    if total > 1:
        base_title = f"{base_title}_{index + 1}"

    return base_title, ext


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={"GET"},
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "arknights-poster-updater/1.0"})
    return session


def download_image(url: str, destination: Path, session: requests.Session, retries: int = 3) -> None:
    temp_path = destination.with_suffix(destination.suffix + ".part")

    for attempt in range(1, retries + 1):
        try:
            with session.get(url, timeout=30, stream=True) as resp:
                resp.raise_for_status()
                with temp_path.open("wb") as file:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            file.write(chunk)
            temp_path.replace(destination)
            return
        except Exception as exc:  # noqa: BLE001
            temp_path.unlink(missing_ok=True)
            if attempt == retries:
                raise
            print(f"Retry {attempt}/{retries} for {url} after error: {exc}")


def choose_filename(
    base: str, ext: str, url: str, image_cache: dict[str, str], reserved: set[str]
) -> str:
    """
    Pick a deterministic filename, avoiding collisions with other URLs.

    - If a filename already maps to the same URL, reuse it.
    - If the filename is used by another URL or reserved in this run, append counters.
    """
    candidate = f"{base}{ext}"
    counter = 2

    while True:
        conflict_cache = candidate in image_cache and image_cache[candidate] != url
        conflict_reserved = candidate in reserved and candidate not in image_cache

        if conflict_cache or conflict_reserved:
            candidate = f"{base}_{counter}{ext}"
            counter += 1
            continue

        return candidate


def main() -> None:
    if not META_CACHE_PATH.exists():
        raise FileNotFoundError(f"Meta cache not found: {META_CACHE_PATH}")

    meta = json.loads(META_CACHE_PATH.read_text(encoding="utf-8"))
    posters = meta.get("posters", [])

    image_cache = load_json(IMAGE_CACHE_PATH)
    url_to_filename = {url: name for name, url in image_cache.items()}
    reserved_names = set(image_cache.keys())

    downloaded = 0
    skipped = 0
    renamed = 0

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    session = build_session()

    for poster in posters:
        images = poster.get("images", [])
        for idx, url in enumerate(images):
            if not url:
                continue

            title = poster.get("title", "")
            base, ext = filename_from_title(title, url, idx, len(images))
            target_filename = choose_filename(base, ext, url, image_cache, reserved_names)

            # Already cached with correct name and present on disk.
            if (
                target_filename in image_cache
                and image_cache[target_filename] == url
                and (ASSETS_DIR / target_filename).exists()
            ):
                skipped += 1
                continue

            # Same URL but stored under a different name: rename if the file exists.
            existing_name = url_to_filename.get(url)
            if existing_name and existing_name != target_filename:
                existing_path = ASSETS_DIR / existing_name
                target_path = ASSETS_DIR / target_filename
                if existing_path.exists():
                    existing_path.rename(target_path)
                    del image_cache[existing_name]
                    reserved_names.discard(existing_name)
                    image_cache[target_filename] = url
                    url_to_filename[url] = target_filename
                    reserved_names.add(target_filename)
                    renamed += 1
                    print(f"Renamed {existing_name} -> {target_filename}")
                    continue
                else:
                    # Drop stale cache entry; will re-download.
                    del image_cache[existing_name]
                    reserved_names.discard(existing_name)

            destination = ASSETS_DIR / target_filename
            try:
                download_image(url, destination, session=session)
            except Exception as exc:  # noqa: BLE001
                print(f"Failed to download {url}: {exc}")
                continue

            image_cache[target_filename] = url
            url_to_filename[url] = target_filename
            reserved_names.add(target_filename)
            downloaded += 1
            print(f"Downloaded {target_filename}")

    save_json(IMAGE_CACHE_PATH, image_cache)
    print(
        "Done. "
        f"Downloaded: {downloaded}, renamed: {renamed}, skipped: {skipped}, "
        f"total cached: {len(image_cache)}"
    )


if __name__ == "__main__":
    main()
