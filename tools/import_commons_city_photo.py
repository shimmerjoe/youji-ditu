from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from PIL import Image

try:
    from tools import build_travel_html as builder
except ModuleNotFoundError:  # Direct execution from the tools directory.
    import build_travel_html as builder


API_URL = "https://commons.wikimedia.org/w/api.php"


def commons_file_title(source_url: str) -> str:
    parsed = urlparse(source_url)
    if parsed.netloc.lower() != "commons.wikimedia.org":
        raise ValueError("source must be a Wikimedia Commons file page")
    path = unquote(parsed.path)
    marker = "/wiki/"
    if marker not in path:
        raise ValueError("source must use a Commons /wiki/File: URL")
    title = path.split(marker, 1)[1]
    if not title.startswith("File:") or len(title) <= len("File:"):
        raise ValueError("source must identify a Commons File page")
    return title


def request_commons_payload(source_url: str, width: int = 1600) -> dict:
    params = {
        "action": "query",
        "titles": commons_file_title(source_url),
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": str(width),
        "format": "json",
    }
    request = Request(
        API_URL + "?" + urlencode(params),
        headers={"User-Agent": builder.USER_AGENT},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def entry_from_commons_payload(payload: dict, city_key: str) -> tuple[dict, str, int, int]:
    pages = payload.get("query", {}).get("pages", {})
    if not pages:
        raise ValueError("Commons did not return a file record")
    page = next(iter(pages.values()))
    info = (page.get("imageinfo") or [{}])[0]
    if info.get("mime") != "image/jpeg":
        raise ValueError("only JPEG city covers are supported")
    raw_image_url = info.get("thumburl") or info.get("url") or ""
    image_url = urlparse(raw_image_url)._replace(query="", fragment="").geturl()
    width = int(info.get("thumbwidth") or info.get("width") or 0)
    height = int(info.get("thumbheight") or info.get("height") or 0)
    if not image_url or width < 1000 or height < 600:
        raise ValueError("candidate is too small for a responsive city cover")
    ratio = width / height
    if not 1.2 <= ratio <= 2.4:
        raise ValueError("candidate must be a landscape image with a usable cover ratio")
    metadata = info.get("extmetadata", {})
    entry = {
        "status": "hit",
        "path": f"assets/photos/{city_key}/cityphoto-src.jpg",
        "title": page.get("title", ""),
        "source": info.get("descriptionurl") or "",
        "license": builder.strip_html(metadata.get("LicenseShortName", {}).get("value", "")),
        "artist": builder.strip_html(metadata.get("Artist", {}).get("value", "")),
        "query": "manual:" + page.get("title", ""),
    }
    if not builder.photo_has_republication_rights(entry):
        raise ValueError("candidate does not expose sufficient reuse and attribution metadata")
    return entry, image_url, width, height


def download_candidate(image_url: str, path: Path, attempts: int = 3) -> None:
    """Download with bounded retries and retain the real network error for diagnosis."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = Request(image_url, headers={"User-Agent": builder.USER_AGENT})
        try:
            with urlopen(request, timeout=45) as response:
                data = response.read()
            if len(data) < 1024:
                raise ValueError("downloaded response is too small to be an image")
            path.write_bytes(data)
            return
        except Exception as exc:
            last_error = exc
            path.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(f"failed to download Commons image after {attempts} attempts: {last_error}")


def import_city_photo(city_key: str, source_url: str, apply: bool) -> dict:
    valid_keys = {page.key for page in builder.PAGES if page.key != "record"}
    if city_key not in valid_keys:
        raise ValueError(f"unknown city key: {city_key}")
    payload = request_commons_payload(source_url)
    entry, image_url, width, height = entry_from_commons_payload(payload, city_key)
    result = {**entry, "download": image_url, "width": width, "height": height, "applied": False}
    if not apply:
        return result

    target = builder.ROOT / entry["path"]
    candidate = target.with_name("cityphoto-import-candidate.jpg")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.unlink(missing_ok=True)
    download_candidate(image_url, candidate)
    try:
        with Image.open(candidate) as image:
            actual_width, actual_height = image.size
            if actual_width < 1000 or actual_height < 600:
                raise ValueError("downloaded candidate is smaller than its metadata claims")
            if not 1.2 <= actual_width / actual_height <= 2.4:
                raise ValueError("downloaded candidate is not a usable landscape cover")
        if not builder.looks_like_real_photo(candidate, image_url):
            raise ValueError("downloaded candidate did not pass the photo-content check")
        candidate.replace(target)
    except Exception:
        candidate.unlink(missing_ok=True)
        raise

    builder.load_photo_cache()
    builder.PHOTO_CACHE[f"cityphoto|{city_key}"] = entry
    builder.save_photo_cache()
    result["applied"] = True
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import one explicitly reviewed Wikimedia Commons image as a city cover.",
    )
    parser.add_argument("--city", required=True, help="Stable city key, for example: beijing")
    parser.add_argument("--source", required=True, help="Canonical Wikimedia Commons File page URL")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Download the image and update photo-cache.json; without this flag the command is read-only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = import_city_photo(args.city, args.source, args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
