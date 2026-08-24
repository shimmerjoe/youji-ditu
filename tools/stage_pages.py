from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = (ROOT / "dist").resolve()

ROOT_FILES = (
    ".nojekyll",
    "index.html",
    "destinations.html",
    "themes.html",
    "city-guides.html",
    "roadtrip.html",
    "tools.html",
    "user.html",
    "manifest.webmanifest",
    "robots.txt",
    "sitemap.xml",
    "sw.js",
)

ROOT_DIRECTORIES = ("cities",)

ASSET_FILES = (
    "icon-180.png",
    "icon-192.png",
    "icon-512.png",
    "travel.css",
    "travel.js",
    "travel-app.css",
    "travel-app.js",
    "search-index.js",
    "roadtrip.css",
    "roadtrip-core.js",
    "roadtrip-data.js",
    "roadtrip-app.js",
)

ASSET_DIRECTORIES = ("images", "item-images", "photos")


def copy_required(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing generated publish asset: {source.relative_to(ROOT)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def stage() -> None:
    root = ROOT.resolve()
    if DIST.parent != root or DIST.name != "dist":
        raise RuntimeError(f"Refusing to replace unexpected publish directory: {DIST}")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for name in ROOT_FILES:
        copy_required(ROOT / name, DIST / name)
    for name in ROOT_DIRECTORIES:
        copy_required(ROOT / name, DIST / name)
    for name in ASSET_FILES:
        copy_required(ROOT / "assets" / name, DIST / "assets" / name)
    for name in ASSET_DIRECTORIES:
        copy_required(ROOT / "assets" / name, DIST / "assets" / name)

    forbidden = tuple(DIST.rglob("roadtrip-config.js"))
    if forbidden:
        raise RuntimeError("Local road-trip configuration must never enter the Pages artifact")
    html_count = len(tuple(DIST.rglob("*.html")))
    if html_count < 200:
        raise RuntimeError(f"Publish artifact is incomplete: only {html_count} HTML files")
    print(f"Staged {html_count} HTML files in {DIST}")


if __name__ == "__main__":
    stage()
