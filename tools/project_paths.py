"""Shared project layout used by the generator, maintenance tools and tests."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 源内容：城市 Markdown 与综合总览
CONTENT = ROOT / "content"
CITY_SOURCES = CONTENT / "城市"
RECORD_SOURCE = CONTENT / "记录.md"
# 网站目录：生成页面、静态资源与图片库（GitHub Pages 由此暂存发布）
SITE = ROOT / "site"
SITE_ASSETS = SITE / "assets"
SITE_CITIES = SITE / "cities"
