from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIST = (ROOT / "dist").resolve()

ROOT_FILES = (
    ".nojekyll",
    "index.html",
    "overview.html",
    "plan.html",
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

# 图片按引用发布：只复制页面和脚本实际用到的图片。site/assets/photos 里还有封面原图、
# 衍生裁切和来源网页截取（没有转载授权）等非发布素材，不能整目录复制到公开站点。
IMAGE_REFERENCE = re.compile(r"assets/((?:images|photos|item-images)/[^\"'?#)\s]+\.(?:jpe?g|png|webp|gif))", re.I)
UNPUBLISHABLE_MARKERS = ("/_sources/", "cityphoto-src")


def copy_required(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing generated publish asset: {source.relative_to(ROOT)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def referenced_images() -> set[str]:
    """Collect image paths (relative to assets/) used by staged pages and scripts."""
    references: set[str] = set()
    for path in [*DIST.rglob("*.html"), *(DIST / "assets").glob("*.js")]:
        references.update(IMAGE_REFERENCE.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return references


def stage_referenced_images() -> int:
    copied = 0
    for reference in sorted(referenced_images()):
        if any(marker in f"/{reference}" for marker in UNPUBLISHABLE_MARKERS):
            raise RuntimeError(f"Unlicensed source media is referenced by a public page: {reference}")
        source = SITE / "assets" / reference
        # roadtrip-data.js 为每座城市给出封面路径；没有授权封面的城市本来就没有该文件。
        if not source.is_file():
            continue
        destination = DIST / "assets" / reference
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return copied


def stage() -> None:
    root = ROOT.resolve()
    if DIST.parent != root or DIST.name != "dist":
        raise RuntimeError(f"Refusing to replace unexpected publish directory: {DIST}")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for name in ROOT_FILES:
        copy_required(SITE / name, DIST / name)
    for name in ROOT_DIRECTORIES:
        copy_required(SITE / name, DIST / name)
    for name in ASSET_FILES:
        copy_required(SITE / "assets" / name, DIST / "assets" / name)
    # Vite 按需加载的分块（行程计划等），文件名带内容哈希。
    for chunk in sorted((SITE / "assets").glob("travel-chunk-*.js")):
        copy_required(chunk, DIST / "assets" / chunk.name)
    image_count = stage_referenced_images()

    forbidden = tuple(DIST.rglob("roadtrip-config.js"))
    if forbidden:
        raise RuntimeError("Local road-trip configuration must never enter the Pages artifact")
    html_count = len(tuple(DIST.rglob("*.html")))
    if html_count < 200:
        raise RuntimeError(f"Publish artifact is incomplete: only {html_count} HTML files")
    print(f"Staged {html_count} HTML files and {image_count} referenced images in {DIST}")


if __name__ == "__main__":
    stage()
