from __future__ import annotations

import html
import hashlib
import os
import random
import re
import shutil
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, unquote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps


try:
    from tools.project_paths import CITY_SOURCES, RECORD_SOURCE, ROOT, SITE
    from tools.site_icons import icon
except ModuleNotFoundError:  # Direct execution from the tools directory.
    from project_paths import CITY_SOURCES, RECORD_SOURCE, ROOT, SITE
    from site_icons import icon

CITY_DIR = CITY_SOURCES
OUT = SITE
ASSETS = OUT / "assets"
IMAGES = ASSETS / "images"
ITEM_IMAGES = ASSETS / "item-images"
PHOTOS = ASSETS / "photos"
SOURCE_MEDIA_DIR = ROOT / "content" / "media-candidates" / "source-pages"
COVER_SMALL = IMAGES / "w640"
PHOTO_CACHE_FILE = ASSETS / "photo-cache.json"
PHOTO_EDITORIAL_FILE = ASSETS / "photo-editorial-decisions.json"
SOURCE_MEDIA_CACHE_FILE = ASSETS / "source-media-cache.json"
VITE_MANIFEST_FILE = ASSETS / "vite-manifest.json"
CITIES_OUT = OUT / "cities"
USER_AGENT = "CodexTravelGuide/1.0 personal-local-static-site"
PUBLIC_SITE_URL = os.environ.get("TRAVEL_PUBLIC_URL", "https://shimmerjoe.github.io/youji-ditu/").rstrip("/") + "/"
FETCH_MEDIA = os.environ.get("TRAVEL_FETCH_MEDIA", "0") == "1"
FETCH_SOURCE_MEDIA = FETCH_MEDIA or os.environ.get("TRAVEL_FETCH_SOURCE", "0") == "1"
FETCH_COMMONS_MEDIA = FETCH_MEDIA or os.environ.get("TRAVEL_FETCH_COMMONS", "0") == "1"
FETCH_CITY_KEYS = {
    key.strip()
    for key in os.environ.get("TRAVEL_FETCH_CITY_KEYS", "").split(",")
    if key.strip()
}
PHOTO_CACHE: dict[str, dict] = {}
PHOTO_CACHE_LOADED = False
PHOTO_EDITORIAL_DECISIONS: dict[str, dict] = {}
PHOTO_EDITORIAL_LOADED = False
SOURCE_MEDIA_CACHE: dict[str, dict] = {}
SOURCE_MEDIA_CACHE_LOADED = False
PAGE_SOURCE_MEDIA: dict[str, list[dict]] = {}
ASSET_BUILD = ""


def asset_href(path: Path, from_dir: Path) -> str:
    href = rel_to(path, from_dir)
    return f"{href}?v={ASSET_BUILD}" if ASSET_BUILD else href


def public_page_url(path: Path) -> str:
    """Return a stable deployment URL for SEO/share metadata without using local paths."""
    relative = path.relative_to(OUT).as_posix()
    if relative == "index.html":
        return PUBLIC_SITE_URL
    return urljoin(PUBLIC_SITE_URL, quote(relative, safe="/"))


def vite_bundle_files() -> tuple[str | None, list[str], list[str]]:
    """Return the Vite entry, imported JS chunks and CSS listed by its manifest."""
    if not VITE_MANIFEST_FILE.exists():
        return None, [], []
    manifest = json.loads(VITE_MANIFEST_FILE.read_text(encoding="utf-8"))
    entry_keys = [key for key, chunk in manifest.items() if chunk.get("isEntry")]
    if len(entry_keys) != 1:
        raise RuntimeError(f"Expected exactly one Vite entry, found {len(entry_keys)}")
    entry_key = entry_keys[0]
    seen: set[str] = set()
    imported_files: list[str] = []
    css_files: list[str] = []

    def visit(key: str) -> None:
        if key in seen:
            return
        seen.add(key)
        chunk = manifest.get(key)
        if not chunk:
            raise RuntimeError(f"Vite manifest import is missing: {key}")
        for imported_key in chunk.get("imports", []):
            visit(imported_key)
            imported_file = manifest[imported_key].get("file")
            if imported_file and imported_file not in imported_files:
                imported_files.append(imported_file)
        for css_file in chunk.get("css", []):
            if css_file not in css_files:
                css_files.append(css_file)

    visit(entry_key)
    entry_file = manifest[entry_key].get("file")
    if not entry_file:
        raise RuntimeError("Vite entry has no output file")
    return entry_file, imported_files, css_files


def vite_asset_tags(from_dir: Path) -> tuple[str, str]:
    entry_file, imported_files, css_files = vite_bundle_files()
    if not entry_file:
        return "", ""
    head_tags = [
        f'  <link rel="stylesheet" href="{asset_href(ASSETS / css_file, from_dir)}">'
        for css_file in css_files
    ]
    head_tags.extend(
        f'  <link rel="modulepreload" href="{asset_href(ASSETS / imported_file, from_dir)}">'
        for imported_file in imported_files
    )
    script = f'  <script type="module" src="{asset_href(ASSETS / entry_file, from_dir)}"></script>'
    return "\n".join(head_tags), script


@dataclass(frozen=True)
class Page:
    source: Path
    output: Path
    key: str
    title: str
    subtitle: str
    accent: str
    image_query: str


@dataclass
class AnchorIndex:
    terms: dict[str, str]
    section_ids: set[str]
    section_terms: dict[str, str]


PAGES = [
    Page(RECORD_SOURCE, OUT / "index.html", "record", "综合旅游攻略记录", "跨城市总览、场景索引、季节索引和路线模板", "#2f6f73", "china travel landscape"),
    Page(CITY_DIR / "贵州_贵阳.md", CITIES_OUT / "guiyang.html", "guiyang", "贵州贵阳旅游攻略", "城市山林、老城烟火、酸汤和避暑", "#25736a", "guiyang guizhou china"),
    Page(CITY_DIR / "贵州_兴义.md", CITIES_OUT / "xingyi.html", "xingyi", "贵州兴义旅游攻略", "万峰林、马岭河、布依村寨和羊肉粉", "#5c7a31", "xingyi guizhou karst"),
    Page(CITY_DIR / "贵州_安顺.md", CITIES_OUT / "anshun.html", "anshun", "贵州安顺旅游攻略", "黄果树、龙宫、屯堡和裹卷凉粉", "#7b6a2f", "anshun huangguoshu waterfall guizhou"),
    Page(CITY_DIR / "贵州_铜仁.md", CITIES_OUT / "tongren.html", "tongren", "贵州铜仁旅游攻略", "梵净山、侗寨、石阡温泉和锅巴粉", "#4f7c58", "fanjingshan tongren guizhou"),
    Page(CITY_DIR / "贵州_黔东南.md", CITIES_OUT / "qiandongnan.html", "qiandongnan", "贵州黔东南旅游攻略", "苗侗村寨、镇远夜景、肇兴和酸汤鱼", "#7a4f8f", "qiandongnan miao dong village"),
    Page(CITY_DIR / "贵州_遵义.md", CITIES_OUT / "zunyi.html", "zunyi", "贵州遵义旅游攻略", "红色历史、赤水丹霞、茅台酒镇和羊肉粉", "#8a3f31", "zunyi guizhou red tourism"),
    Page(CITY_DIR / "贵州_毕节.md", CITIES_OUT / "bijie.html", "bijie", "贵州毕节旅游攻略", "百里杜鹃、织金洞、韭菜坪和高原花海", "#8b5a8c", "bijie guizhou flowers cave"),
    Page(CITY_DIR / "贵州_黔南.md", CITIES_OUT / "qiannan.html", "qiannan", "贵州黔南旅游攻略", "荔波小七孔、中国天眼、都匀毛尖和喀斯特山水", "#2d7e84", "libo xiaoqikong guizhou"),
    Page(CITY_DIR / "贵州_六盘水.md", CITIES_OUT / "liupanshui.html", "liupanshui", "贵州六盘水旅游攻略", "中国凉都、乌蒙草原、梅花山和水城羊肉粉", "#5f7b3b", "liupanshui guizhou grassland"),
    Page(CITY_DIR / "河南_郑州.md", CITIES_OUT / "zhengzhou.html", "zhengzhou", "河南郑州旅游攻略", "中原文明、沉浸戏剧、夜市和嵩山", "#8c5b2e", "zhengzhou henan china"),
    Page(CITY_DIR / "四川_成都.md", CITIES_OUT / "chengdu.html", "chengdu", "四川成都旅游攻略", "熊猫、茶馆、火锅、博物馆和都江堰", "#9b3f34", "chengdu panda china"),
    Page(CITY_DIR / "四川_乐山.md", CITIES_OUT / "leshan.html", "leshan", "四川乐山旅游攻略", "乐山大佛、峨眉山、钵钵鸡和跷脚牛肉", "#8a5a2b", "leshan giant buddha sichuan"),
    Page(CITY_DIR / "四川_阿坝.md", CITIES_OUT / "aba.html", "aba", "四川阿坝旅游攻略", "九寨沟、黄龙、四姑娘山和高原秋色", "#3d7ca3", "jiuzhaigou aba sichuan"),
    Page(CITY_DIR / "四川_甘孜.md", CITIES_OUT / "ganzi.html", "ganzi", "四川甘孜旅游攻略", "稻城亚丁、康定、新都桥和川西雪山", "#6d6a9f", "garze sichuan yading"),
    Page(CITY_DIR / "四川_绵阳.md", CITIES_OUT / "mianyang.html", "mianyang", "四川绵阳旅游攻略", "李白故里、羌城、九皇山和绵阳米粉", "#6a7c43", "mianyang sichuan china"),
    Page(CITY_DIR / "四川_宜宾.md", CITIES_OUT / "yibin.html", "yibin", "四川宜宾旅游攻略", "蜀南竹海、李庄古镇、五粮液和燃面", "#4d7b54", "yibin bamboo sea sichuan"),
    Page(CITY_DIR / "四川_自贡.md", CITIES_OUT / "zigong.html", "zigong", "四川自贡旅游攻略", "恐龙、彩灯、盐业和盐帮菜", "#a45735", "zigong dinosaur lantern sichuan"),
    Page(CITY_DIR / "四川_雅安.md", CITIES_OUT / "yaan.html", "yaan", "四川雅安旅游攻略", "碧峰峡、蒙顶山、上里古镇和雅鱼", "#46775b", "yaan sichuan panda tea"),
    Page(CITY_DIR / "四川_德阳.md", CITIES_OUT / "deyang.html", "deyang", "四川德阳旅游攻略", "三星堆、绵竹年画、文庙和川西小城", "#9a6b2f", "sanxingdui deyang sichuan"),
    Page(CITY_DIR / "云南_昆明.md", CITIES_OUT / "kunming.html", "kunming", "云南昆明旅游攻略", "春城花事、滇池、斗南花市和米线", "#4d7b54", "kunming yunnan flowers"),
    Page(CITY_DIR / "云南_弥勒.md", CITIES_OUT / "mile.html", "mile", "云南弥勒旅游攻略", "红砖艺术、湖景温泉、葡萄酒庄、彝寨和卤鸡米线", "#b45b3a", "mile yunnan red brick wine hot spring"),
    Page(CITY_DIR / "云南_大理.md", CITIES_OUT / "dali.html", "dali", "云南大理旅游攻略", "苍山洱海、古城、喜洲和海边慢游", "#2f6f9f", "dali yunnan erhai"),
    Page(CITY_DIR / "云南_丽江.md", CITIES_OUT / "lijiang.html", "lijiang", "云南丽江旅游攻略", "古城、白沙、玉龙雪山和纳西风味", "#576ca8", "lijiang yunnan snow mountain"),
    Page(CITY_DIR / "云南_西双版纳.md", CITIES_OUT / "xishuangbanna.html", "xishuangbanna", "云南西双版纳旅游攻略", "热带雨林、傣味夜市、野象谷和植物园", "#2f7c47", "xishuangbanna tropical rainforest"),
    Page(CITY_DIR / "云南_香格里拉.md", CITIES_OUT / "shangrila.html", "shangrila", "云南香格里拉旅游攻略", "高原湖泊、藏传佛寺、草原和虎跳峡", "#6d70a8", "shangri la yunnan"),
    Page(CITY_DIR / "云南_腾冲.md", CITIES_OUT / "tengchong.html", "tengchong", "云南腾冲旅游攻略", "火山热海、和顺古镇、银杏村和滇西抗战", "#9a5b36", "tengchong yunnan volcano hot spring"),
    Page(CITY_DIR / "云南_建水.md", CITIES_OUT / "jianshui.html", "jianshui", "云南建水旅游攻略", "古城小火车、朱家花园、紫陶和烧豆腐", "#9b4e3f", "jianshui yunnan old town"),
    Page(CITY_DIR / "云南_普洱.md", CITIES_OUT / "puer.html", "puer", "云南普洱旅游攻略", "茶山咖啡、太阳河森林和景迈山", "#5f6f35", "puer yunnan tea mountain"),
    Page(CITY_DIR / "云南_玉溪.md", CITIES_OUT / "yuxi.html", "yuxi", "云南玉溪旅游攻略", "抚仙湖、澄江化石、铜锅鱼和高原湖景", "#2f7794", "fuxian lake yuxi yunnan"),
    Page(CITY_DIR / "云南_楚雄.md", CITIES_OUT / "chuxiong.html", "chuxiong", "云南楚雄旅游攻略", "元谋土林、彝人古镇、恐龙谷和野生菌", "#8a6a37", "chuxiong yunnan earth forest"),
    Page(CITY_DIR / "云南_临沧.md", CITIES_OUT / "lincang.html", "lincang", "云南临沧旅游攻略", "佤山秘境、翁丁古寨、茶山和边地风味", "#6f4f3a", "lincang yunnan tea village"),
    Page(CITY_DIR / "重庆.md", CITIES_OUT / "chongqing.html", "chongqing", "重庆旅游攻略", "8D 山城、两江夜景、火锅和步道", "#9a4a3c", "chongqing skyline china"),
    Page(CITY_DIR / "陕西_西安.md", CITIES_OUT / "xian.html", "xian", "陕西西安旅游攻略", "兵马俑、城墙、陕历博和碳水夜市", "#8a6032", "xian terracotta warriors china"),
    Page(CITY_DIR / "湖南_长沙.md", CITIES_OUT / "changsha.html", "changsha", "湖南长沙旅游攻略", "橘子洲、岳麓山、湘菜夜生活和湖南博物院", "#9b4336", "changsha hunan china"),
    Page(CITY_DIR / "福建_厦门.md", CITIES_OUT / "xiamen.html", "xiamen", "福建厦门旅游攻略", "鼓浪屿、海边骑行、闽南小吃和植物园", "#2f7c84", "xiamen gulangyu china"),
    Page(CITY_DIR / "浙江_杭州.md", CITIES_OUT / "hangzhou.html", "hangzhou", "浙江杭州旅游攻略", "西湖、灵隐、西溪、龙井茶和江南街巷", "#3f7a54", "hangzhou west lake china"),
    Page(CITY_DIR / "江苏_苏州.md", CITIES_OUT / "suzhou.html", "suzhou", "江苏苏州旅游攻略", "园林、平江路、苏博和苏式面", "#5a748f", "suzhou garden china"),
    Page(CITY_DIR / "江苏_南京.md", CITIES_OUT / "nanjing.html", "nanjing", "江苏南京旅游攻略", "中山陵、南博、秦淮夜景和鸭血粉丝", "#7f4f43", "nanjing china"),
    Page(CITY_DIR / "广西_桂林.md", CITIES_OUT / "guilin.html", "guilin", "广西桂林旅游攻略", "漓江山水、阳朔骑行、象鼻山和米粉", "#2f7c70", "guilin karst landscape"),
]


# 首页与跨城市总览都由 记录.md 生成；它们不是城市页，很多城市专属逻辑要跳过。
OVERVIEW_PAGE = Page(RECORD_SOURCE, OUT / "overview.html", "overview", "跨城市旅游攻略总览", "跨城市总览、时间成本、场景索引、季节索引和路线模板", "#2f6f73", "")
HUB_KEYS = {"record", "overview"}


NAV_GROUPS = [
    {"kind": "link", "label": "总览", "href": "index.html"},
    {"kind": "group", "label": "贵州", "items": [("贵阳", "cities/guiyang.html"), ("兴义", "cities/xingyi.html"), ("安顺", "cities/anshun.html"), ("铜仁", "cities/tongren.html"), ("黔东南", "cities/qiandongnan.html"), ("遵义", "cities/zunyi.html"), ("毕节", "cities/bijie.html"), ("黔南", "cities/qiannan.html"), ("六盘水", "cities/liupanshui.html")]},
    {"kind": "group", "label": "河南", "items": [("郑州", "cities/zhengzhou.html")]},
    {"kind": "group", "label": "四川", "items": [("成都", "cities/chengdu.html"), ("乐山", "cities/leshan.html"), ("阿坝", "cities/aba.html"), ("甘孜", "cities/ganzi.html"), ("绵阳", "cities/mianyang.html"), ("宜宾", "cities/yibin.html"), ("自贡", "cities/zigong.html"), ("雅安", "cities/yaan.html"), ("德阳", "cities/deyang.html")]},
    {"kind": "group", "label": "云南", "items": [("昆明", "cities/kunming.html"), ("弥勒", "cities/mile.html"), ("大理", "cities/dali.html"), ("丽江", "cities/lijiang.html"), ("西双版纳", "cities/xishuangbanna.html"), ("香格里拉", "cities/shangrila.html"), ("腾冲", "cities/tengchong.html"), ("建水", "cities/jianshui.html"), ("普洱", "cities/puer.html"), ("玉溪", "cities/yuxi.html"), ("楚雄", "cities/chuxiong.html"), ("临沧", "cities/lincang.html")]},
    {"kind": "link", "label": "重庆", "href": "cities/chongqing.html"},
    {"kind": "group", "label": "陕西", "items": [("西安", "cities/xian.html")]},
    {"kind": "group", "label": "湖南", "items": [("长沙", "cities/changsha.html")]},
    {"kind": "group", "label": "福建", "items": [("厦门", "cities/xiamen.html")]},
    {"kind": "group", "label": "浙江", "items": [("杭州", "cities/hangzhou.html")]},
    {"kind": "group", "label": "江苏", "items": [("苏州", "cities/suzhou.html"), ("南京", "cities/nanjing.html")]},
    {"kind": "group", "label": "广西", "items": [("桂林", "cities/guilin.html")]},
]


DIRECT_MUNICIPALITIES = {"北京", "上海", "天津", "重庆"}
SPECIAL_REGIONS = {"香港", "澳门"}
TOP_LEVEL_REGIONS = DIRECT_MUNICIPALITIES | SPECIAL_REGIONS
CITY_PAGE_META_FILE = ROOT / "tools" / "city-page-meta.json"
PROVINCE_SORT_KEYS = {
    "安徽": "anhui",
    "北京": "beijing",
    "重庆": "chongqing",
    "福建": "fujian",
    "甘肃": "gansu",
    "广东": "guangdong",
    "广西": "guangxi",
    "贵州": "guizhou",
    "海南": "hainan",
    "河北": "hebei",
    "河南": "henan",
    "黑龙江": "heilongjiang",
    "湖北": "hubei",
    "湖南": "hunan",
    "吉林": "jilin",
    "江苏": "jiangsu",
    "江西": "jiangxi",
    "辽宁": "liaoning",
    "澳门": "macao",
    "内蒙古": "neimenggu",
    "宁夏": "ningxia",
    "青海": "qinghai",
    "山东": "shandong",
    "山西": "shanxi",
    "陕西": "shaanxi",
    "上海": "shanghai",
    "四川": "sichuan",
    "天津": "tianjin",
    "西藏": "xizang",
    "新疆": "xinjiang",
    "香港": "hong-kong",
    "云南": "yunnan",
    "浙江": "zhejiang",
    "直辖市": "zhixiashi",
}
CITY_SORT_KEYS = {
    "阿坝": "aba",
    "安顺": "anshun",
    "北京": "beijing",
    "北海": "beihai",
    "毕节": "bijie",
    "长春": "changchun",
    "长沙": "changsha",
    "潮州": "chaozhou",
    "成都": "chengdu",
    "承德": "chengde",
    "重庆": "chongqing",
    "楚雄": "chuxiong",
    "大理": "dali",
    "大连": "dalian",
    "大同": "datong",
    "德阳": "deyang",
    "敦煌": "dunhuang",
    "恩施": "enshi",
    "福州": "fuzhou",
    "甘孜": "ganzi",
    "广州": "guangzhou",
    "贵阳": "guiyang",
    "桂林": "guilin",
    "哈尔滨": "harbin",
    "海口": "haikou",
    "杭州": "hangzhou",
    "合肥": "hefei",
    "呼和浩特": "hohhot",
    "呼伦贝尔": "hulunbuir",
    "黄山": "huangshan",
    "济南": "jinan",
    "济宁": "jining",
    "吉林市": "jilin-city",
    "建水": "jianshui",
    "景德镇": "jingdezhen",
    "九江": "jiujiang",
    "喀什": "kashgar",
    "开封": "kaifeng",
    "昆明": "kunming",
    "拉萨": "lhasa",
    "兰州": "lanzhou",
    "乐山": "leshan",
    "丽江": "lijiang",
    "临沧": "lincang",
    "林芝": "nyingchi",
    "柳州": "liuzhou",
    "六盘水": "liupanshui",
    "洛阳": "luoyang",
    "绵阳": "mianyang",
    "弥勒": "mile",
    "牡丹江": "mudanjiang",
    "澳门": "macao",
    "南昌": "nanchang",
    "南京": "nanjing",
    "南平": "nanping",
    "普洱": "puer",
    "盘锦": "panjin",
    "黔东南": "qiandongnan",
    "黔南": "qiannan",
    "秦皇岛": "qinhuangdao",
    "青岛": "qingdao",
    "泉州": "quanzhou",
    "三亚": "sanya",
    "上海": "shanghai",
    "上饶": "shangrao",
    "沈阳": "shenyang",
    "深圳": "shenzhen",
    "十堰": "shiyan",
    "苏州": "suzhou",
    "泰安": "taian",
    "太原": "taiyuan",
    "天津": "tianjin",
    "铜仁": "tongren",
    "吐鲁番": "turpan",
    "威海": "weihai",
    "武汉": "wuhan",
    "乌鲁木齐": "urumqi",
    "西安": "xian",
    "香港": "hong-kong",
    "厦门": "xiamen",
    "西宁": "xining",
    "西双版纳": "xishuangbanna",
    "香格里拉": "shangrila",
    "忻州": "xinzhou",
    "兴义": "xingyi",
    "烟台": "yantai",
    "延边": "yanbian",
    "雅安": "yaan",
    "宜宾": "yibin",
    "宜昌": "yichang",
    "伊犁": "ili",
    "银川": "yinchuan",
    "玉溪": "yuxi",
    "张掖": "zhangye",
    "郑州": "zhengzhou",
    "珠海": "zhuhai",
    "遵义": "zunyi",
    "自贡": "zigong",
}


def read_city_meta() -> dict[str, dict]:
    if not CITY_PAGE_META_FILE.exists():
        return {}
    try:
        return json.loads(CITY_PAGE_META_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def split_city_filename(path: Path) -> tuple[str, str]:
    stem = path.stem
    if "_" in stem:
        province, city = stem.split("_", 1)
    else:
        province = city = stem
    return province, city


def read_page_title(path: Path, province: str, city: str) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    if province in DIRECT_MUNICIPALITIES and province == city:
        return f"{city}旅游攻略"
    return f"{province}{city}旅游攻略"


def default_city_slug(path: Path) -> str:
    return "city-" + hashlib.sha1(path.stem.encode("utf-8")).hexdigest()[:10]


def ensure_nav_item(province: str, city: str, href: str) -> None:
    if province in TOP_LEVEL_REGIONS and province == city:
        if not any(item.get("kind") == "link" and item.get("href") == href for item in NAV_GROUPS):
            NAV_GROUPS.append({"kind": "link", "label": city, "href": href})
        return
    for group in NAV_GROUPS:
        if group.get("kind") == "group" and group.get("label") == province:
            if not any(existing_href == href for _, existing_href in group["items"]):
                group["items"].append((city, href))
            return
    NAV_GROUPS.append({"kind": "group", "label": province, "items": [(city, href)]})


def nav_label_sort_key(label: str, mapping: dict[str, str]) -> str:
    return mapping.get(label, label).lower()


def nav_href_page_key(href: str) -> str | None:
    output_name = Path(href).name
    for page in PAGES:
        if page.output.name == output_name:
            return page.key
    return None


def nav_city_sort_key(item: tuple[str, str]) -> tuple[str, str]:
    label, href = item
    return (nav_href_page_key(href) or CITY_SORT_KEYS.get(label) or label).lower(), label


def sort_nav_groups() -> None:
    overview = [
        item for item in NAV_GROUPS
        if item.get("kind") == "link" and item.get("href") == "index.html"
    ]
    municipality_links = [
        item for item in NAV_GROUPS
        if item.get("kind") == "link" and item.get("label") in TOP_LEVEL_REGIONS
    ]
    other_links = [
        item for item in NAV_GROUPS
        if item.get("kind") == "link"
        and item.get("href") != "index.html"
        and item.get("label") not in TOP_LEVEL_REGIONS
    ]
    groups = [item for item in NAV_GROUPS if item.get("kind") == "group"]
    for group in groups:
        group["items"] = sorted(group["items"], key=nav_city_sort_key)
    municipality_links.sort(key=lambda item: nav_label_sort_key(item["label"], CITY_SORT_KEYS))
    other_links.sort(key=lambda item: nav_label_sort_key(item["label"], CITY_SORT_KEYS))
    groups.sort(key=lambda item: nav_label_sort_key(item["label"], PROVINCE_SORT_KEYS))
    NAV_GROUPS[:] = overview[:1] + municipality_links + groups + other_links


def extend_pages_from_city_markdowns() -> None:
    meta = read_city_meta()
    existing_sources = {page.source.resolve() for page in PAGES if page.source.exists()}
    existing_outputs = {page.output.name for page in PAGES}
    for source in sorted(CITY_DIR.glob("*.md"), key=lambda item: item.name):
        if source.resolve() in existing_sources:
            continue
        province, city = split_city_filename(source)
        source_meta = meta.get(source.stem, {})
        slug = source_meta.get("slug") or default_city_slug(source)
        output_name = f"{slug}.html"
        if output_name in existing_outputs:
            slug = default_city_slug(source)
            output_name = f"{slug}.html"
        title = source_meta.get("title") or read_page_title(source, province, city)
        subtitle = source_meta.get("subtitle") or "综合景点、吃喝、季节玩法和路线模板"
        accent = source_meta.get("accent") or "#5f6f73"
        query = source_meta.get("image_query") or f"{city} {province} china travel"
        PAGES.append(Page(source, CITIES_OUT / output_name, slug, title, subtitle, accent, query))
        existing_sources.add(source.resolve())
        existing_outputs.add(output_name)
        ensure_nav_item(province, city, f"cities/{output_name}")


# 精选主城（手工维护、攻略最丰富、Commons 覆盖好）的 key —— 景点条目级 Commons 抓取只对它们做，
# 避免给 150 个小众城市的上千条目发无效请求；城市级大图则对全部城市抓取。
PRIMARY_PAGE_KEYS = {page.key for page in PAGES}

extend_pages_from_city_markdowns()
sort_nav_groups()


def rel_to(path: Path, start: Path) -> str:
    return Path(os.path.relpath(path, start)).as_posix()


def slugify(text: str, used: set[str]) -> str:
    table = {
        "先看总览": "overview",
        "时间成本索引": "time-cost",
        "场景索引": "scenes",
        "季节总索引": "seasons",
        "跨城市路线模板": "routes",
        "原记录点位归类清单": "source-map",
        "贵州省": "guizhou",
        "云南省": "yunnan",
        "重庆市": "chongqing",
        "河南省郑州市": "zhengzhou",
        "四川省成都市": "chengdu",
        "快速决策索引": "quick",
        "先看结论": "overview",
        "适合季节与天数": "seasonal",
        "全年月份速查": "months",
        "季节限定景观": "seasonal",
        "景点营业时间和票价速查": "hours-prices",
        "行前准备": "prep",
        "住宿建议": "stay",
        "地图分区": "areas",
        "核心景点": "attractions",
        "行程路线": "routes",
        "街区、夜市和市场": "streets",
        "街区/夜市/市场": "streets",
        "自然/远郊/周边": "nature",
        "街区、商圈和夜市": "streets",
        "市场和市井": "markets",
        "美食总表": "food",
        "美食推荐": "food",
        "餐厅和店铺": "shops",
        "博物馆和展馆": "museums",
        "自然、远郊和周边": "nature",
        "自然、公园和露营": "nature",
        "远郊和周边一日": "day-trips",
        "路线模板": "routes",
        "远郊一日游决策": "daytrip-decisions",
        "交通细节": "transport",
        "避坑和取舍": "warnings",
        "避坑提醒": "warnings",
        "出发前复核清单": "checklist",
        "出发前复核": "checklist",
        "住宿区域": "stay",
        "预算参考": "budget",
        "来源参考": "sources",
    }
    base = table.get(text.strip())
    if not base:
        base = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    if not base:
        base = "section"
    candidate = base
    n = 2
    while candidate in used:
        candidate = f"{base}-{n}"
        n += 1
    used.add(candidate)
    return candidate


def link_plain_segment(segment: str, anchors: dict[str, str] | None, current_id: str | None = None) -> str:
    if not anchors:
        return html.escape(segment)
    terms = [
        (term, href) for term, href in anchors.items()
        if len(term) >= 2 and href != f"#{current_id}"
    ]
    if not terms:
        return html.escape(segment)
    terms.sort(key=lambda item: len(item[0]), reverse=True)
    out: list[str] = []
    pos = 0
    links = 0
    while pos < len(segment):
        best: tuple[int, str, str] | None = None
        for term, href in terms:
            idx = segment.find(term, pos)
            if idx < 0:
                continue
            if best is None or idx < best[0] or (idx == best[0] and len(term) > len(best[1])):
                best = (idx, term, href)
        if best is None or links >= 12:
            out.append(html.escape(segment[pos:]))
            break
        idx, term, href = best
        out.append(html.escape(segment[pos:idx]))
        out.append(f'<a class="auto-link" href="{html.escape(href)}">{html.escape(term)}</a>')
        pos = idx + len(term)
        links += 1
    return "".join(out)


def inline_markup(text: str, anchors: dict[str, str] | None = None, current_id: str | None = None) -> str:
    parts: list[str] = []
    pos = 0
    token_re = re.compile(r"`([^`]+)`|(https?://[^\s<]+)")
    for match in token_re.finditer(text):
        parts.append(link_plain_segment(text[pos:match.start()], anchors, current_id))
        if match.group(1) is not None:
            parts.append(f"<code>{html.escape(match.group(1))}</code>")
        else:
            url = match.group(2)
            parts.append(f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(url)}</a>')
        pos = match.end()
    parts.append(link_plain_segment(text[pos:], anchors, current_id))
    return "".join(parts)


def split_label(text: str) -> tuple[str | None, str]:
    for sep in ("：", ":"):
        if sep in text:
            left, right = text.split(sep, 1)
            if 1 <= len(left) <= 16:
                return left.strip(), right.strip()
    return None, text


def parse_list(lines: Iterable[str]) -> list[dict]:
    root = {"children": []}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in lines:
        if not raw.strip():
            continue
        match = re.match(r"^(\s*)-\s+(.*)$", raw)
        if not match:
            continue
        indent = len(match.group(1)) // 2
        node = {"text": match.group(2).strip(), "children": []}
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack[-1][1]["children"].append(node)
        stack.append((indent, node))
    return root["children"]


FACT_LABELS = {"介绍", "门票", "时间限制", "时间", "票价", "提醒", "高频玩法", "适合", "类型", "推荐", "判断", "价格"}
VISUAL_SECTION_IDS = {"seasonal", "attractions", "streets", "markets", "food", "shops", "museums", "nature", "day-trips"}
FOOD_SECTION_IDS = {"food", "shops", "markets"}
FOOD_KEYWORDS = (
    "火锅", "串串", "羊肉粉", "牛肉粉", "米线", "饵丝", "饵块", "乳扇", "酸汤鱼", "烤鱼", "烧烤", "烤肉",
    "豆腐", "蘸水", "奶茶", "咖啡", "甜品", "夜市", "小吃", "餐厅", "老店", "菜市", "早市", "美食",
)


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msyhbd.ttc") if bold else Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        test = current + char
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
            continue
        if current:
            lines.append(current)
        current = char
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len("".join(lines)) < len(text):
        lines[-1] = lines[-1].rstrip("，。；、 ") + "..."
    return lines


def item_title(text: str) -> str:
    label, body = split_label(text)
    if label and label not in FACT_LABELS and len(label) >= 2:
        title = label
    else:
        title = body if label else text
    title = re.split(r"[：:，,。；;（(]", title, maxsplit=1)[0]
    title = re.sub(r"https?://\S+", "", title)
    title = title.strip(" -·[]【】「」")
    return title[:28]


def item_anchor_id(section_id: str | None, node: dict) -> str | None:
    title = item_title(node["text"])
    if not section_id or not title or title in FACT_LABELS or len(title) < 2:
        return None
    digest = hashlib.md5(f"{section_id}-{node['text']}".encode("utf-8")).hexdigest()[:10]
    return f"{section_id}-item-{digest}"


def split_index_terms(text: str) -> list[str]:
    text = re.sub(r"https?://\S+", "", text)
    label, body = split_label(text)
    raw = f"{label or ''}、{body}"
    terms = []
    for part in re.split(r"[、，,；;｜|/（）()：:\s]+", raw):
        part = part.strip(" -·[]【】「」")
        if 2 <= len(part) <= 18 and not part.isdigit() and part not in FACT_LABELS:
            terms.append(part)
    return terms


def add_anchor_term(terms: dict[str, str], term: str, href: str, prefer: bool = False) -> None:
    term = term.strip(" -·[]【】「」")
    if 2 <= len(term) <= 28 and term not in FACT_LABELS:
        if prefer or term not in terms:
            terms[term] = href


def collect_anchor_index(markdown: str) -> AnchorIndex:
    lines = markdown.splitlines()
    terms: dict[str, str] = {}
    section_terms: dict[str, str] = {}
    section_ids: set[str] = set()
    used: set[str] = set()
    current_section_id: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            if level != 1:
                sid = slugify(text, used)
                current_section_id = sid
                section_ids.add(sid)
                href = f"#{sid}"
                section_terms[text] = href
                add_anchor_term(terms, text, href)
            i += 1
            continue
        if re.match(r"^\s*-\s+", line):
            block: list[str] = []
            while i < len(lines) and (re.match(r"^\s*-\s+", lines[i]) or not lines[i].strip()):
                block.append(lines[i])
                i += 1
            for node in parse_list(block):
                if current_section_id == "sources":
                    continue
                anchor_id = item_anchor_id(current_section_id, node)
                if not anchor_id:
                    continue
                href = f"#{anchor_id}"
                prefer = current_section_id in VISUAL_SECTION_IDS
                add_anchor_term(terms, item_title(node["text"]), href, prefer)
                label, body = split_label(node["text"])
                if label and label not in FACT_LABELS:
                    add_anchor_term(terms, label, href, prefer)
                for term in split_index_terms(node["text"]):
                    add_anchor_term(terms, term, href, prefer)
            continue
        i += 1

    aliases = {
        "景点": ["attractions", "seasonal", "nature", "source-map"],
        "吃喝": ["food", "shops", "markets", "streets", "source-map"],
        "美食": ["food", "shops", "markets"],
        "路线": ["routes", "daytrip-decisions"],
        "避坑": ["warnings", "checklist"],
        "月份": ["months"],
        "季节": ["seasons", "seasonal"],
        "住宿": ["stay"],
        "交通": ["transport"],
        "门票": ["hours-prices"],
    }
    for alias, candidates in aliases.items():
        for sid in candidates:
            if sid in section_ids:
                terms.setdefault(alias, f"#{sid}")
                break
    return AnchorIndex(terms=terms, section_ids=section_ids, section_terms=section_terms)


def flatten_node_text(node: dict) -> list[str]:
    texts: list[str] = []
    for child in node["children"]:
        texts.append(child["text"])
        texts.extend(flatten_node_text(child))
    return texts


def item_kind(section_id: str | None, title: str, full_text: str) -> str:
    if section_id in FOOD_SECTION_IDS:
        return "food"
    if section_id == "streets" and any(keyword in title or keyword in full_text for keyword in ("夜市", "小吃", "美食", "餐厅", "咖啡", "菜市", "早市")):
        return "food"
    if any(keyword in title for keyword in FOOD_KEYWORDS):
        return "food"
    return "place"


def should_show_item_visual(section_id: str | None, depth: int, node: dict) -> bool:
    if depth != 0 or section_id not in VISUAL_SECTION_IDS:
        return False
    title = item_title(node["text"])
    if not title or title in FACT_LABELS or len(title) < 2:
        return False
    if title.startswith(("来源", "关键词", "官方", "本地", "提醒", "判断", "总体")):
        return False
    return True


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def load_photo_cache() -> None:
    global PHOTO_CACHE_LOADED, PHOTO_CACHE
    if PHOTO_CACHE_LOADED:
        return
    if PHOTO_CACHE_FILE.exists():
        try:
            PHOTO_CACHE = json.loads(PHOTO_CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            PHOTO_CACHE = {}
    PHOTO_CACHE_LOADED = True


def save_photo_cache() -> None:
    PHOTO_CACHE_FILE.write_text(json.dumps(PHOTO_CACHE, ensure_ascii=False, indent=2), encoding="utf-8")


def load_photo_editorial_decisions() -> None:
    """Load product-fit decisions separately from factual rights metadata."""
    global PHOTO_EDITORIAL_LOADED, PHOTO_EDITORIAL_DECISIONS
    if PHOTO_EDITORIAL_LOADED:
        return
    PHOTO_EDITORIAL_DECISIONS = {}
    if PHOTO_EDITORIAL_FILE.exists():
        try:
            payload = json.loads(PHOTO_EDITORIAL_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid photo editorial file: {PHOTO_EDITORIAL_FILE}") from exc
        if payload.get("schemaVersion") != 1 or not isinstance(payload.get("decisions"), dict):
            raise RuntimeError(f"Unsupported photo editorial schema: {PHOTO_EDITORIAL_FILE}")
        PHOTO_EDITORIAL_DECISIONS = payload["decisions"]
    PHOTO_EDITORIAL_LOADED = True


def load_source_media_cache() -> None:
    global SOURCE_MEDIA_CACHE_LOADED, SOURCE_MEDIA_CACHE
    if SOURCE_MEDIA_CACHE_LOADED:
        return
    if SOURCE_MEDIA_CACHE_FILE.exists():
        try:
            SOURCE_MEDIA_CACHE = json.loads(SOURCE_MEDIA_CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            SOURCE_MEDIA_CACHE = {}
    SOURCE_MEDIA_CACHE_LOADED = True


def save_source_media_cache() -> None:
    SOURCE_MEDIA_CACHE_FILE.write_text(json.dumps(SOURCE_MEDIA_CACHE, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(url: str) -> dict | None:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


PLACEHOLDER_PHOTO_LICENSES = {"", "unknown", "wikipedia", "wikimedia commons"}


def photo_has_republication_rights(entry: dict | None) -> bool:
    """Only publish cached photos whose actual reuse terms and attribution are known."""
    if not entry or entry.get("status") != "hit":
        return False
    source = str(entry.get("source", "") or "").strip()
    license_name = str(entry.get("license", "") or "").strip()
    artist = str(entry.get("artist", "") or "").strip()
    if not source.startswith(("https://", "http://")):
        return False
    if license_name.lower() in PLACEHOLDER_PHOTO_LICENSES:
        return False
    attribution_free = license_name.lower().startswith(("cc0", "public domain", "pdm"))
    return attribution_free or bool(artist)


def photo_editorial_rejection(city_key: str, entry: dict | None) -> dict | None:
    """Return a rejection only while the cached source still matches the reviewed source."""
    if not entry:
        return None
    load_photo_editorial_decisions()
    decision = PHOTO_EDITORIAL_DECISIONS.get(city_key)
    if not isinstance(decision, dict) or decision.get("status") != "rejected":
        return None
    if str(decision.get("source", "")).strip() != str(entry.get("source", "")).strip():
        return None
    return decision


def photo_is_publishable(entry: dict | None, city_key: str | None = None) -> bool:
    """Require both reuse rights and a positive product-fit outcome."""
    if not photo_has_republication_rights(entry):
        return False
    return not city_key or photo_editorial_rejection(city_key, entry) is None


def photo_cache_entry_after_miss(city_key: str, cached: dict | None, query: str) -> dict:
    """Preserve rejected-source evidence when a refresh finds no replacement."""
    if cached and photo_editorial_rejection(city_key, cached):
        return cached
    return {"status": "miss", "query": query}


def commons_metadata_for_image_url(image_url: str) -> dict | None:
    """Resolve an upload.wikimedia.org URL to the Commons file page and reuse metadata."""
    parts = [unquote(part) for part in urlparse(image_url).path.split("/") if part]
    if not parts:
        return None
    filename = parts[-2] if "thumb" in parts and len(parts) >= 2 else parts[-1]
    if not filename:
        return None
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "format": "json",
    }
    data = request_json("https://commons.wikimedia.org/w/api.php?" + urlencode(params))
    pages = (data or {}).get("query", {}).get("pages", {})
    if not pages:
        return None
    page = next(iter(pages.values()))
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    entry = {
        "status": "hit",
        "title": page.get("title", ""),
        "source": info.get("descriptionurl") or "",
        "license": strip_html(meta.get("LicenseShortName", {}).get("value", "")),
        "artist": strip_html(meta.get("Artist", {}).get("value", "")),
    }
    return entry if photo_has_republication_rights(entry) else None


def download_url(url: str, path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=10) as resp:
            data = resp.read()
        if len(data) < 1024:
            return False
        path.write_bytes(data)
        return True
    except Exception:
        return False


def fetch_text(url: str) -> str | None:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=6) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            raw = resp.read(900_000)
        encoding = "utf-8"
        match = re.search(br"charset=['\"]?([A-Za-z0-9_-]+)", raw[:4096], re.I)
        if match:
            encoding = match.group(1).decode("ascii", "ignore") or "utf-8"
        return raw.decode(encoding, "ignore")
    except Exception:
        return None


def meta_content(document: str, names: Iterable[str]) -> str | None:
    wanted = {name.lower() for name in names}
    for tag in re.findall(r"<meta\s+[^>]+>", document, flags=re.I):
        lower = tag.lower()
        if not any(f'property="{name}"' in lower or f"property='{name}'" in lower or f'name="{name}"' in lower or f"name='{name}'" in lower for name in wanted):
            continue
        match = re.search(r"""content\s*=\s*["']([^"']+)["']""", tag, flags=re.I)
        if match:
            return html.unescape(match.group(1)).strip()
    return None


def document_title(document: str) -> str:
    title = meta_content(document, ["og:title", "twitter:title"])
    if title:
        return strip_html(title)
    match = re.search(r"<title[^>]*>(.*?)</title>", document, flags=re.I | re.S)
    if match:
        return strip_html(html.unescape(match.group(1)))
    return ""


def first_document_image(document: str, page_url: str) -> str | None:
    image = meta_content(document, ["og:image", "og:image:url", "og:image:secure_url", "twitter:image"])
    if image:
        return urljoin(page_url, image)
    for match in re.finditer(r"""<img\s+[^>]*src\s*=\s*["']([^"']+)["']""", document, flags=re.I):
        src = html.unescape(match.group(1)).strip()
        lower = src.lower()
        if any(skip in lower for skip in ("logo", "icon", "sprite", "qrcode", "二维码")):
            continue
        return urljoin(page_url, src)
    return None


def source_page_media(url: str) -> dict:
    load_source_media_cache()
    cached = SOURCE_MEDIA_CACHE.get(url)
    if cached:
        path = cached.get("path")
        if cached.get("status") == "hit" and path and (OUT / path).exists():
            return cached
        if cached.get("status") == "miss":
            return cached
    if not FETCH_SOURCE_MEDIA:
        return {"status": "miss", "url": url}

    embed = bilibili_embed_url(url)
    if embed:
        result = {"status": "video", "url": url, "embed": embed, "title": "哔哩哔哩视频"}
        SOURCE_MEDIA_CACHE[url] = result
        save_source_media_cache()
        return result

    document = fetch_text(url)
    if not document:
        result = {"status": "miss", "url": url}
        SOURCE_MEDIA_CACHE[url] = result
        save_source_media_cache()
        return result

    title = document_title(document)
    image_url = first_document_image(document, url)
    video = meta_content(document, ["og:video", "og:video:url", "og:video:secure_url", "twitter:player"])
    if not image_url and not video:
        result = {"status": "miss", "url": url, "title": title}
        SOURCE_MEDIA_CACHE[url] = result
        save_source_media_cache()
        return result

    path_value = ""
    if image_url:
        suffix = Path(urlparse(image_url).path).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            suffix = ".jpg"
        digest = hashlib.md5(image_url.encode("utf-8")).hexdigest()[:16]
        # 来源网页图片没有转载授权，只作为候选线索保存在不发布的 content/ 目录。
        image_path = SOURCE_MEDIA_DIR / f"source-{digest}{suffix}"
        if download_url(image_url, image_path):
            path_value = rel_to(image_path, OUT)

    result = {
        "status": "hit" if path_value else ("video" if video else "miss"),
        "url": url,
        "title": title,
        "image_url": image_url or "",
        "video": urljoin(url, video) if video else "",
        "path": path_value,
        "domain": urlparse(url).netloc,
    }
    SOURCE_MEDIA_CACHE[url] = result
    save_source_media_cache()
    return result


def build_source_media_index(page: Page, markdown: str) -> list[dict]:
    candidates: list[dict] = []
    urls = [url for url in extract_urls(markdown) if "search.bilibili.com" not in url]
    limited_urls = urls[:18] + [url for url in urls[18:] if "bilibili.com/video/" in url][:4]
    for url in limited_urls:
        if "search.bilibili.com" in url:
            continue
        media = source_page_media(url)
        if media.get("status") in {"hit", "video"}:
            candidates.append(media)
    PAGE_SOURCE_MEDIA[page.key] = candidates
    return candidates


def normalized_for_match(value: str) -> str:
    value = value.lower()
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", value)
    return value


# \u6765\u6e90\u9875 og:image \u7ecf\u5e38\u662f logo / \u6a2a\u5e45 / \u4e8c\u7ef4\u7801 / \u52a0\u8f7d\u5360\u4f4d / \u5c0f\u56fe\u6807\uff0c
# \u8fd9\u91cc\u7528\u6587\u4ef6\u540d + \u5b9e\u9645\u50cf\u7d20\u5c3a\u5bf8 + \u5bbd\u9ad8\u6bd4\u628a\u8fd9\u4e9b\u6742\u8d28\u6321\u5728\u300c\u53ef\u89c6\u5316\u53c2\u8003\u300d\u548c\u7f29\u7565\u56fe\u4e4b\u5916\u3002
JUNK_IMAGE_TOKENS = (
    "logo", "_log.", "top_log", "banner", "ewm", "qrcode", "qr_", "_qr",
    "swiper", "sprite", "loading", "placeholder", "nopic", "noimg", "no-img",
    "default", "blank", "icon", "homeico", "weixin", "wx.", "/wx", "gh_",
    "sousuo", "ipv", "bg-top", "news_more", "/service", "service-", "serve_",
    "home.", "404", "_64_64",
)
_PHOTO_QUALITY_CACHE: dict[str, bool] = {}


def photo_vibrancy(path: Path) -> float:
    """0~1 的「出彩度」：综合平均饱和度与明暗对比，用来在合格候选中挑更好看的风景照。"""
    try:
        with Image.open(path) as im:
            small = im.convert("RGB").resize((64, 64))
    except Exception:
        return 0.0
    get_pixels = getattr(small, "get_flattened_data", None)
    pixels = list(get_pixels() if get_pixels else small.getdata())
    n = len(pixels) or 1
    sat_sum = 0.0
    vals = []
    for r, g, b in pixels:
        mx, mn = max(r, g, b), min(r, g, b)
        sat_sum += 0.0 if mx == 0 else (mx - mn) / mx
        vals.append(mx / 255)
    mean_sat = sat_sum / n
    mean_v = sum(vals) / n
    var = sum((v - mean_v) ** 2 for v in vals) / n
    contrast = min((var ** 0.5) / 0.25, 1.0)
    return max(0.0, min(1.0, 0.7 * mean_sat + 0.3 * contrast))


def looks_like_real_photo(out_path: Path, image_url: str = "") -> bool:
    # 缓存键必须带上 image_url：城市配图的多个候选会先后覆盖同一个临时文件
    # （cityphoto-src.jpg），只用路径做键会让第一张候选的判定污染后续候选。
    cache_key = f"{out_path}|{image_url}"
    if cache_key in _PHOTO_QUALITY_CACHE:
        return _PHOTO_QUALITY_CACHE[cache_key]
    verdict = _looks_like_real_photo(out_path, image_url)
    _PHOTO_QUALITY_CACHE[cache_key] = verdict
    return verdict


def _looks_like_real_photo(out_path: Path, image_url: str = "") -> bool:
    lower = (image_url or out_path.name).lower()
    ext = lower.split("?")[0].rsplit(".", 1)[-1]
    if ext in {"svg", "gif"}:
        return False
    name = lower.rsplit("/", 1)[-1]
    if any(tok in name for tok in JUNK_IMAGE_TOKENS):
        return False
    try:
        with Image.open(out_path) as im:
            w, h = im.size
            small = im.convert("RGB").resize((64, 64))
    except Exception:
        return False
    if min(w, h) < 200 or max(w, h) < 300:
        return False
    ratio = w / h if h else 0
    if ratio < 0.42 or ratio > 2.6:
        return False
    # 识别二维码 / 黑白图标 / 纯色块：极端明暗像素占比高且整体几乎无彩色
    extreme = 0
    sat_sum = 0.0
    get_pixels = getattr(small, "get_flattened_data", None)
    pixels = list(get_pixels() if get_pixels else small.getdata())
    for r, g, b in pixels:
        mx = max(r, g, b)
        mn = min(r, g, b)
        v = mx / 255
        sat_sum += 0.0 if mx == 0 else (mx - mn) / mx
        if v < 0.22 or v > 0.92:
            extreme += 1
    count = len(pixels) or 1
    if extreme / count >= 0.5 and sat_sum / count <= 0.14:
        return False
    return True


def source_photo_for(page: Page, title: str) -> tuple[Path | None, dict | None]:
    title_norm = normalized_for_match(title)
    if len(title_norm) < 2:
        return None, None
    title_variants = {
        title_norm,
        normalized_for_match(title.replace("景区", "").replace("公园", "").replace("古镇", "").replace("博物馆", "")),
    }
    best: tuple[int, dict] | None = None
    for media in PAGE_SOURCE_MEDIA.get(page.key, []):
        path = media.get("path")
        if media.get("status") != "hit" or not path:
            continue
        if not source_media_has_republication_rights(media):
            continue
        if not looks_like_real_photo(OUT / path, media.get("image_url", "")):
            continue
        hay = normalized_for_match(" ".join([media.get("title", ""), media.get("url", ""), media.get("domain", "")]))
        score = 0
        for variant in title_variants:
            if len(variant) >= 2 and variant in hay:
                score = max(score, 100 if variant == title_norm else 72)
        if not score:
            for term in split_index_terms(title):
                term_norm = normalized_for_match(term)
                if len(term_norm) >= 2 and term_norm in hay:
                    score += 18
        if score and (best is None or score > best[0]):
            best = (score, media)
    if not best:
        return None, None
    media = best[1]
    path = OUT / media["path"]
    if path.exists():
        return path, media
    return None, None


def search_terms_for_photo(page: Page, title: str, kind: str) -> list[str]:
    city = page.title.replace("旅游攻略", "")
    base = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", " ", title).strip()
    terms = [f"{city} {base}", base, f"{base} 中国"]
    if kind == "food":
        terms.extend([f"{base} 美食", f"{base} Chinese food"])
    return [term for term in dict.fromkeys(terms) if len(term.strip()) >= 2]


def commons_photo_for(page: Page, title: str, kind: str) -> tuple[Path | None, dict | None]:
    load_photo_cache()
    key = hashlib.md5(f"{page.key}|{kind}|{title}".encode("utf-8")).hexdigest()
    cached = PHOTO_CACHE.get(key)
    if cached:
        if photo_has_republication_rights(cached):
            path = OUT / cached["path"]
            if path.exists():
                return path, cached
        if cached.get("status") == "miss":
            return None, cached
    if not FETCH_COMMONS_MEDIA or page.key not in PRIMARY_PAGE_KEYS:
        return None, None

    for term in search_terms_for_photo(page, title, kind):
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": term,
            "gsrnamespace": "6",
            "gsrlimit": "8",
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": "900",
            "format": "json",
        }
        data = request_json("https://commons.wikimedia.org/w/api.php?" + urlencode(params))
        pages = (data or {}).get("query", {}).get("pages", {})
        candidates = sorted(pages.values(), key=lambda item: item.get("index", 999))
        for candidate in candidates:
            info = (candidate.get("imageinfo") or [{}])[0]
            mime = info.get("mime", "")
            image_url = info.get("thumburl") or info.get("url")
            if not image_url or not mime.startswith("image/") or mime == "image/svg+xml":
                continue
            suffix = Path(urlparse(image_url).path).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                suffix = ".jpg"
            photo_path = PHOTOS / page.key / f"{kind}-{key}{suffix}"
            if download_url(image_url, photo_path):
                if not looks_like_real_photo(photo_path, image_url):
                    continue
                meta = info.get("extmetadata", {})
                cache_entry = {
                    "status": "hit",
                    "path": rel_to(photo_path, OUT),
                    "title": candidate.get("title", ""),
                    "query": term,
                    "source": info.get("descriptionurl") or info.get("url") or "",
                    "license": strip_html(meta.get("LicenseShortName", {}).get("value", "")),
                    "artist": strip_html(meta.get("Artist", {}).get("value", "")),
                }
                if not photo_has_republication_rights(cache_entry):
                    photo_path.unlink(missing_ok=True)
                    continue
                PHOTO_CACHE[key] = cache_entry
                save_photo_cache()
                return photo_path, cache_entry

    PHOTO_CACHE[key] = {"status": "miss", "query": title}
    save_photo_cache()
    return None, PHOTO_CACHE[key]


def save_cover_image(src_path: Path, out_path: Path, size: tuple[int, int]) -> bool:
    """把任意图片按 cover 方式缩放居中裁剪到目标尺寸，存为体积友好的 JPEG。"""
    width, height = size
    try:
        with Image.open(src_path) as im:
            im = im.convert("RGB")
            sw, sh = im.size
            scale = max(width / sw, height / sh)
            nw, nh = max(int(sw * scale + 0.5), width), max(int(sh * scale + 0.5), height)
            im = im.resize((nw, nh), Image.LANCZOS)
            left = (nw - width) // 2
            top = (nh - height) // 3  # 略偏上，保留天空 / 地标顶部
            im.crop((left, top, left + width, top + height)).save(out_path, "JPEG", quality=82, optimize=True, progressive=True)
        return True
    except Exception:
        return False


def wikipedia_lead_image(name: str) -> str | None:
    """取 Wikipedia 条目首图 URL（先中文站后英文站，跳过消歧义页）。"""
    name = (name or "").strip()
    if len(name) < 2:
        return None
    bad = ("location", "locator", "map", "flag", "seal", "coat_of", "emblem",
           "satellite", "landsat", "sentinel", "modis", "nasa", "astronaut", "space",
           "airport", "railway", "station", "stadium", "school", "university", "bus")
    for host in ("zh.wikipedia.org", "en.wikipedia.org"):
        data = request_json(f"https://{host}/api/rest_v1/page/summary/{quote(name)}")
        if not data or data.get("type") != "standard":
            continue
        img = (data.get("originalimage") or {}).get("source") or (data.get("thumbnail") or {}).get("source")
        if not img:
            continue
        fn = img.rsplit("/", 1)[-1].lower()
        # 跳过定位地图 / 旗帜 / 徽章 类首图（如 ChinaHenanZhumadian.png）
        if any(b in fn for b in bad) or re.match(r"^china[a-z]+\.png", fn):
            continue
        return img
    return None


def city_photo_for(page: Page) -> tuple[Path, dict] | tuple[None, None]:
    """为城市抓一张有代表性的真实风景照（Wikimedia Commons + Wikipedia 兜底），用作首页卡片 / 大图。"""
    if page.key == "record":
        return None, None
    load_photo_cache()
    cache_key = f"cityphoto|{page.key}"
    cached = PHOTO_CACHE.get(cache_key)
    if cached:
        if photo_is_publishable(cached, page.key) and (OUT / cached["path"]).exists():
            return OUT / cached["path"], cached
        if cached.get("status") == "miss":
            return None, None
    if not FETCH_COMMONS_MEDIA:
        return None, None
    if FETCH_CITY_KEYS and page.key not in FETCH_CITY_KEYS:
        return None, None

    base_query = page.image_query or page.title.replace("旅游攻略", "")
    key_term = page.key.replace("-", " ") + " china"
    # 用「城市中文名 + 代表景点」做高优先查询（Commons 对中文景点名收录好，能拿到真实风景照）
    _, city_cn = page_location(page)
    all_highlights = [h for h in city_profile(page).get("highlights", []) if 2 <= len(h) <= 12]
    highlights = all_highlights[:2]
    # 相关性关键词：候选的标题或描述必须命中其一，避免「广安」误配到维也纳佛光山这类无关图
    rel_keys = [k.lower() for k in ([city_cn] + all_highlights[:4]) if k]
    cn_terms = [f"{city_cn} {h}" for h in highlights]
    if city_cn:
        cn_terms.append(city_cn)
    terms = [t for t in dict.fromkeys(cn_terms + [base_query, key_term, base_query + " landscape"]) if t.strip()]
    candidates: list[tuple[float, str, str, dict]] = []       # 强相关候选
    weak_candidates: list[tuple[float, str, str, dict]] = []  # 仅作最后兜底
    seen_urls: set[str] = set()
    for term in terms:
        params = {
            "action": "query", "generator": "search", "gsrsearch": term,
            "gsrnamespace": "6", "gsrlimit": "15", "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata", "iiurlwidth": "1280", "format": "json",
        }
        data = request_json("https://commons.wikimedia.org/w/api.php?" + urlencode(params))
        pages = (data or {}).get("query", {}).get("pages", {})
        for rank, candidate in enumerate(sorted(pages.values(), key=lambda i: i.get("index", 999))):
            info = (candidate.get("imageinfo") or [{}])[0]
            mime = info.get("mime", "")
            image_url = info.get("thumburl") or info.get("url")
            if not image_url or image_url in seen_urls or not mime.startswith("image/") or mime == "image/svg+xml":
                continue
            tw = info.get("thumbwidth") or info.get("width") or 0
            th = info.get("thumbheight") or info.get("height") or 0
            ratio = (tw / th) if th else 0
            ctitle = (candidate.get("title") or "").lower()
            if any(bad in ctitle for bad in (
                    "map", "logo", "icon", "diagram", "flag", "seal", "locator", ".svg",
                    "airport", "railway", "station", "rock", "fossil", "specimen", "mineral",
                    "stele", "石碑", "化石", "标本", "矿",
                    # 交通场所：相关但不是风景
                    "站台", "火车站", "车站", "高铁", "地铁", "机场",
                    # 卫星 / 遥感：颜色鲜艳但不是游客视角的风景照
                    "satellite", "landsat", "sentinel", "modis", "nasa", "astronaut",
                    "from space", "space station", "iss0", "topograph", "earth observ", "卫星", "遥感")):
                continue
            # 相关性：标题或图片描述出现城市名 / 代表景点才算强相关（防「广安→维也纳」这类误配）
            desc = strip_html((info.get("extmetadata", {}).get("ImageDescription", {}) or {}).get("value", ""))
            blob = (ctitle + " " + desc).lower()
            relevant = bool(rel_keys) and any(k in blob for k in rel_keys)
            score = 100 - rank * 4
            if 1.2 <= ratio <= 2.4:
                score += 30
            elif ratio < 0.9:
                score -= 30
            if (tw or 0) >= 1000:
                score += 10
            suffix = Path(urlparse(image_url).path).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                suffix = ".jpg"
            (candidates if relevant else weak_candidates).append((score, image_url, suffix, info))
            seen_urls.add(image_url)

    def pick_best(cands):
        """下载得分靠前的候选，按「鲜活度」（饱和度 + 明暗对比）挑最出彩的一张。"""
        if not cands:
            return None, None
        cands = sorted(cands, key=lambda c: c[0], reverse=True)[:6]
        max_score = max((c[0] for c in cands), default=1) or 1
        best = None  # (总分, cand_path, suffix, info)
        for i, (score, image_url, suffix, info) in enumerate(cands):
            meta = info.get("extmetadata", {})
            candidate_meta = {
                "status": "hit",
                "source": info.get("descriptionurl") or info.get("url") or "",
                "license": strip_html(meta.get("LicenseShortName", {}).get("value", "")),
                "artist": strip_html(meta.get("Artist", {}).get("value", "")),
            }
            if not photo_is_publishable(candidate_meta, page.key):
                continue
            cand_path = PHOTOS / page.key / f"cityphoto-cand{i}{suffix}"
            if not download_url(image_url, cand_path):
                continue
            if not looks_like_real_photo(cand_path, image_url):
                cand_path.unlink(missing_ok=True)
                continue
            total = 0.35 * (score / max_score) + 0.65 * photo_vibrancy(cand_path)
            if best is None or total > best[0]:
                best = (total, cand_path, suffix, info)
        if not best:
            for stale in (PHOTOS / page.key).glob("cityphoto-cand*"):
                stale.unlink(missing_ok=True)
            return None, None
        _, cand_path, suffix, info = best
        raw_path = PHOTOS / page.key / f"cityphoto-src{suffix}"
        raw_path.write_bytes(cand_path.read_bytes())
        for stale in (PHOTOS / page.key).glob("cityphoto-cand*"):
            stale.unlink(missing_ok=True)
        meta = info.get("extmetadata", {})
        entry = {
            "status": "hit",
            "path": rel_to(raw_path, OUT),
            "title": "",
            "source": info.get("descriptionurl") or info.get("url") or "",
            "license": strip_html(meta.get("LicenseShortName", {}).get("value", "")),
            "artist": strip_html(meta.get("Artist", {}).get("value", "")),
            "query": base_query,
        }
        if not photo_is_publishable(entry, page.key):
            raw_path.unlink(missing_ok=True)
            return None, None
        return raw_path, entry

    # 优先用强相关候选
    raw_path, entry = pick_best(candidates)
    if entry:
        PHOTO_CACHE[cache_key] = entry
        save_photo_cache()
        return raw_path, entry

    # 兜底一：Wikipedia 条目首图（对中国城市覆盖好）
    province, city = page_location(page)
    for name in dict.fromkeys([city + "市", city, city + " " + province]):
        img_url = wikipedia_lead_image(name)
        if not img_url:
            continue
        suffix = Path(urlparse(img_url).path).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            suffix = ".jpg"
        raw_path = PHOTOS / page.key / f"cityphoto-src{suffix}"
        if download_url(img_url, raw_path) and looks_like_real_photo(raw_path, img_url):
            metadata = commons_metadata_for_image_url(img_url)
            if not metadata:
                raw_path.unlink(missing_ok=True)
                continue
            entry = {
                **metadata,
                "path": rel_to(raw_path, OUT),
                "query": "wiki:" + name,
            }
            if not photo_is_publishable(entry, page.key):
                raw_path.unlink(missing_ok=True)
                continue
            PHOTO_CACHE[cache_key] = entry
            save_photo_cache()
            return raw_path, entry

    # 兜底二：弱相关候选（标题/描述没直接出现城市名，但搜索结果排名靠前）
    raw_path, entry = pick_best(weak_candidates)
    if entry:
        PHOTO_CACHE[cache_key] = entry
        save_photo_cache()
        return raw_path, entry

    PHOTO_CACHE[cache_key] = photo_cache_entry_after_miss(page.key, cached, base_query)
    save_photo_cache()
    return None, None


def item_image_asset(page: Page, title: str, kind: str) -> tuple[Path, str, dict | None]:
    source_path, source_meta = source_photo_for(page, title)
    if source_path:
        return source_path, "来源图", source_meta
    # Commons 对中国地方菜覆盖很差（常返回无关图），美食类只用来源图。
    if kind != "food":
        photo_path, meta = commons_photo_for(page, title, kind)
        if photo_path:
            return photo_path, "开放图库", meta
    # 没有真实照片就不再生成 / 显示插画，交由调用方渲染为纯文字卡。
    return None, "", None


def draw_item_asset(page: Page, title: str, kind: str) -> Path:
    digest = hashlib.md5(f"{page.key}-{kind}-{title}".encode("utf-8")).hexdigest()[:12]
    path = ITEM_IMAGES / page.key / f"{kind}-{digest}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 900, 540
    accent = hex_to_rgb(page.accent)
    warm = (221, 112, 68) if kind == "food" else (80, 145, 186)
    top = mix_rgb((255, 250, 238), warm, 0.12)
    bottom = mix_rgb((230, 241, 238), accent, 0.20)
    image = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(image, "RGBA")
    draw_gradient(draw, width, height, top, bottom)
    draw.ellipse([width - 250, 34, width - 86, 198], fill=(255, 214, 115, 200))
    draw.ellipse([-80, 310, 250, 650], fill=(*mix_rgb(accent, (255, 255, 255), 0.58), 105))
    draw.rounded_rectangle([42, 42, width - 42, height - 42], radius=34, outline=(255, 255, 255, 150), width=5)

    if kind == "food":
        bowl = [520, 285, 820, 430]
        draw.ellipse([520, 245, 820, 350], fill=(255, 252, 244, 230), outline=(*accent, 170), width=5)
        draw.pieslice(bowl, 0, 180, fill=(255, 252, 244, 235), outline=(*accent, 170), width=5)
        draw.arc([560, 180, 650, 260], 205, 330, fill=(*accent, 150), width=5)
        draw.arc([660, 172, 760, 262], 205, 330, fill=(*accent, 130), width=5)
        draw.line([(500, 205), (805, 135)], fill=(112, 72, 44, 200), width=9)
        draw.line([(516, 235), (825, 168)], fill=(112, 72, 44, 180), width=7)
        tag = "美食 / 店铺"
        caption = "推荐看：特色、位置、排队和同片区搭配"
    else:
        base = 390
        draw.polygon([(460, base), (585, 178), (710, base)], fill=(*mix_rgb(accent, (255, 255, 255), 0.28), 220))
        draw.polygon([(610, base), (745, 220), (880, base)], fill=(*mix_rgb(warm, accent, 0.45), 190))
        draw.polygon([(400, base + 18), (510, 275), (645, base + 18)], fill=(*mix_rgb(accent, (35, 54, 60), 0.30), 210))
        draw_pin(draw, 720, 238, accent, 1.08)
        draw.line([(455, 455), (610, 425), (780, 460), (870, 430)], fill=(255, 255, 255, 150), width=9)
        tag = "景点 / 游玩"
        caption = "推荐看：最佳时间、门票、路线和避坑提醒"

    title_font = load_font(54, bold=True)
    tag_font = load_font(24, bold=True)
    body_font = load_font(25)
    draw.rounded_rectangle([72, 78, 252, 126], radius=24, fill=(*accent, 220))
    draw.text((96, 87), tag, fill=(255, 255, 255, 245), font=tag_font)
    y = 178
    for line in wrap_text(draw, title, title_font, 390, 3):
        draw.text((76, y), line, fill=(28, 34, 34, 245), font=title_font)
        y += 64
    draw.text((80, height - 108), page.title, fill=(*accent, 230), font=tag_font)
    draw.text((80, height - 72), caption, fill=(76, 83, 80, 220), font=body_font)
    image.save(path, "PNG", optimize=True)
    return path


def item_summary(node: dict, kind: str) -> str:
    candidates = []
    for text in flatten_node_text(node):
        if any(key in text for key in ("玩法", "推荐", "搭配", "提醒", "最佳", "看点", "路线", "时间", "门票", "店", "位置", "排队", "特色")):
            candidates.append(text)
    if not candidates:
        label, body = split_label(node["text"])
        if body and len(body) > 8:
            candidates.append(body)
    if not candidates:
        if kind == "food":
            return "优先选攻略中同片区夜市、市场或老店；高峰饭点错开排队，按店铺营业时间复核。"
        return "优先安排早晚光线和低峰时段；出发前复核开放时间、门票、预约和天气。"
    text = "；".join(re.sub(r"https?://\S+", "", item).strip() for item in candidates[:2])
    return text[:150]


LINKIFY_SECTION_IDS = {"overview", "quick", "time-cost", "scenes", "seasons", "source-map", "months", "seasonal", "routes", "daytrip-decisions", "checklist", "areas"}

# 每类章节对应一种阅读组件，替代原来“标签 + 文本”逐层缩进的大纲样式。
SECTION_LAYOUTS = {
    "overview": "facts",
    "quick": "scenarios",
    "months": "months",
    "routes": "routes",
    "daytrip-decisions": "routes",
    "checklist": "checklist",
    "warnings": "tips",
    "areas": "areas",
    "hours-prices": "cards",
    "seasonal": "cards",
    "attractions": "cards",
    "food": "cards",
    "prep": "rows",
    "stay": "rows",
    "transport": "rows",
    "budget": "rows",
}
SCENARIO_ICONS = (
    (("半天", "半日"), "clock"),
    (("雨",), "umbrella"),
    (("亲子", "儿童", "带娃"), "child"),
    (("摄影", "拍照", "出片"), "camera"),
    (("夜",), "night"),
    (("美食", "吃"), "food"),
    (("自驾", "开车"), "car"),
    (("1 天", "1天", "一天", "1日"), "sun"),
    (("天", "日"), "calendar"),
)
CARD_LEAD_LABELS = ("介绍", "看点", "玩法", "特色", "定位")
CARD_VISIBLE_FACTS = 4


def scenario_icon(label: str) -> str:
    for keys, name in SCENARIO_ICONS:
        if any(key in label for key in keys):
            return name
    return "spark"


def section_layout(section_id: str | None, nodes: list[dict]) -> str:
    layout = SECTION_LAYOUTS.get(section_id or "")
    if layout:
        return layout
    if not nodes:
        return "bullets"
    with_children = sum(1 for node in nodes if node["children"])
    if with_children * 2 >= len(nodes):
        return "cards"
    labelled = sum(1 for node in nodes if split_label(node["text"])[0])
    if labelled * 2 >= len(nodes):
        return "rows"
    return "bullets"


def id_attr(anchor_id: str | None) -> str:
    return f' id="{html.escape(anchor_id)}"' if anchor_id else ""


def render_sub_list(nodes: list[dict], anchors: dict[str, str] | None, depth: int = 1) -> str:
    """Render deeper outline levels as a compact list instead of nested pills."""
    if not nodes:
        return ""
    items = []
    for node in nodes:
        label, body = split_label(node["text"])
        if label and body:
            text_html = f'<strong>{inline_markup(label, anchors)}</strong><span>{inline_markup(body, anchors)}</span>'
        else:
            text_html = f'<span>{inline_markup(node["text"], anchors)}</span>'
        items.append(f'<li>{text_html}{render_sub_list(node["children"], anchors, depth + 1)}</li>')
    return f'<ul class="sub-list depth-{depth}">{"".join(items)}</ul>'


GENERIC_VALUES_CACHE: set[str] | None = None


def generic_values() -> set[str]:
    """跨很多城市重复的模板句：页面上标成“通用提示”，与城市专属信息区分。"""
    global GENERIC_VALUES_CACHE
    if GENERIC_VALUES_CACHE is None:
        GENERIC_VALUES_CACHE = boilerplate_values([page for page in PAGES if page.key not in HUB_KEYS])
    return GENERIC_VALUES_CACHE


def value_status(body: str) -> tuple[str, str]:
    """返回 (CSS 类, 前置标签)：待核验 / 通用提示 / 城市专属。"""
    if body.startswith("待核验"):
        return " is-pending", '<span class="info-flag pending">待核验</span>'
    if body in generic_values():
        return " is-generic", '<span class="info-flag generic">通用提示</span>'
    return "", ""


def render_fact_rows(children: list[dict], anchors: dict[str, str] | None) -> list[str]:
    rows = []
    for child in children:
        label, body = split_label(child["text"])
        nested = render_sub_list(child["children"], anchors)
        if label and body:
            status_class, flag = value_status(body)
            shown = body.removeprefix("待核验").lstrip("（(").rstrip("）)") if status_class == " is-pending" else body
            rows.append(
                f'<div class="kv{status_class}"><dt>{html.escape(label)}</dt>'
                f'<dd>{flag}{inline_markup(shown, anchors)}{nested}</dd></div>'
            )
        elif child["children"]:
            rows.append(
                f'<div class="kv kv-group"><dt>{inline_markup(child["text"], anchors)}</dt>'
                f'<dd>{nested}</dd></div>'
            )
        else:
            rows.append(f'<div class="kv kv-note"><dd>{inline_markup(child["text"], anchors)}</dd></div>')
    return rows


def item_visual_html(page: Page, node: dict, section_id: str | None, css_class: str) -> str:
    if not should_show_item_visual(section_id, 0, node):
        return ""
    title = item_title(node["text"])
    kind = item_kind(section_id, title, node["text"])
    image_path, image_badge, meta = item_image_asset(page, title, kind)
    if not image_path:
        return ""
    rel = rel_to(image_path, page.output.parent)
    source_title = ""
    if image_badge == "来源图" and meta:
        source_title = f' title="{html.escape("来源网页：" + meta.get("url", ""))}"'
    elif image_badge == "开放图库" and meta:
        source_title = f' title="{html.escape("Wikimedia Commons" + (" / " + meta.get("license", "") if meta.get("license") else ""))}"'
    return (
        f'<figure class="{css_class}">'
        f'<img class="item-thumb" src="{html.escape(rel)}" alt="{html.escape(title)}配图" width="800" height="480" loading="lazy" decoding="async"{source_title}>'
        f'<figcaption>{html.escape(image_badge)}</figcaption>'
        '</figure>'
    )


PLAN_SECTION_IDS = {"attractions", "seasonal", "museums", "nature", "food", "streets", "shops", "markets", "day-trips"}


def plan_add_button(page: Page, name: str, section_id: str | None, anchor_id: str | None, kind: str) -> str:
    """“加入行程”按钮：数据由 plan-ui.ts 读取，写进按天编排的本机行程。"""
    if page.key in HUB_KEYS or section_id not in PLAN_SECTION_IDS:
        return ""
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) < 2 or len(name) > 40 or name in FACT_LABELS or name in {"使用说明", "农贸市场", "伴手礼"}:
        return ""
    href = rel_to(page.output, OUT) + (f"#{anchor_id}" if anchor_id else "")
    city = city_profile(page)["city"]
    return (
        f'<button class="poi-add" type="button" data-plan-add data-name="{html.escape(name)}" '
        f'data-city="{html.escape(city)}" data-city-key="{html.escape(page.key)}" data-href="{html.escape(href)}" '
        f'data-kind="{"food" if kind == "food" else "place"}">＋ 加入行程</button>'
    )


def render_card(page: Page, node: dict, section_id: str | None, anchors: dict[str, str] | None) -> str:
    anchor_id = item_anchor_id(section_id, node)
    label, body = split_label(node["text"])
    children = list(node["children"])
    kicker = ""
    if label and label not in FACT_LABELS and body:
        title, lead = label, body
    else:
        title, lead = node["text"], ""
    # 美食类：用“代表”菜作为卡片标题，分类作为眉题，读起来更像菜单。
    if section_id == "food":
        for idx, child in enumerate(children):
            child_label, child_body = split_label(child["text"])
            if child_label == "代表" and child_body:
                kicker, title = title, child_body
                children.pop(idx)
                break
    if not lead:
        for idx, child in enumerate(children):
            child_label, child_body = split_label(child["text"])
            if child_label in CARD_LEAD_LABELS and child_body and not child["children"]:
                lead = child_body
                children.pop(idx)
                break
    rows = render_fact_rows(children, anchors)
    visible, hidden = rows, []
    if len(rows) > CARD_VISIBLE_FACTS + 1:
        visible, hidden = rows[:CARD_VISIBLE_FACTS], rows[CARD_VISIBLE_FACTS:]
    facts_html = f'<dl class="kv-list">{"".join(visible)}</dl>' if visible else ""
    if hidden:
        facts_html += (
            '<details class="card-more">'
            f'<summary>展开其余 {len(hidden)} 项</summary>'
            f'<dl class="kv-list">{"".join(hidden)}</dl></details>'
        )
    visual = item_visual_html(page, node, section_id, "card-media")
    kind = item_kind(section_id, item_title(node["text"]), node["text"]) if section_id in VISUAL_SECTION_IDS else ""
    classes = ["info-card"]
    if visual:
        classes.append("has-media")
    if kind:
        classes.append(f"kind-{kind}")
    plan_kind = "food" if section_id == "food" or kind == "food" else "place"
    plan_button = plan_add_button(page, title if section_id == "food" else item_title(node["text"]), section_id, anchor_id, plan_kind)
    actions = poi_action_links_html(page, item_title(node["text"]), section_id, 0)
    if plan_button:
        actions = f'<div class="card-actions">{plan_button}{actions}</div>'
    return (
        f'<article class="{" ".join(classes)}"{id_attr(anchor_id)}>'
        f'{visual}'
        '<div class="card-body">'
        f'{f"<p class=\"card-kicker\">{html.escape(kicker)}</p>" if kicker else ""}'
        f'<h3 class="card-title">{inline_markup(title)}</h3>'
        f'{f"<p class=\"card-lead\">{inline_markup(lead, anchors)}</p>" if lead else ""}'
        f'{facts_html}'
        f'{actions}'
        '</div></article>'
    )


def render_month_card(node: dict, section_id: str | None, anchors: dict[str, str] | None) -> str | None:
    match = re.match(r"^\s*(\d{1,2})\s*月", node["text"])
    if not match:
        return None
    month = int(match.group(1))
    rows = render_fact_rows(node["children"], anchors)
    return (
        f'<article class="month-card" data-month="{month}"{id_attr(item_anchor_id(section_id, node))}>'
        f'<h3><b>{month}</b><span>月</span></h3>'
        f'<dl class="kv-list">{"".join(rows)}</dl></article>'
    )


def route_stops(text: str) -> list[str]:
    # 写了箭头的路线按箭头拆分，括号里的逗号属于说明，不是新的一站。
    separator = r"\s*(?:→|->)\s*" if re.search(r"→|->", text) else r"\s*(?:、|\+|＋|，|,)\s*"
    parts = [part.strip(" 。") for part in re.split(separator, text) if part.strip(" 。")]
    if 2 <= len(parts) <= 9 and all(len(part) <= 22 for part in parts):
        return parts
    return []


def render_route(node: dict, index: int, section_id: str | None, anchors: dict[str, str] | None) -> str:
    label, body = split_label(node["text"])
    title = label if label and body else node["text"]
    detail = body if label and body else ""
    stops = route_stops(detail) if detail else []
    if stops:
        stop_items = []
        for stop in stops:
            href = (anchors or {}).get(stop)
            inner = f'<a href="{html.escape(href)}">{html.escape(stop)}</a>' if href else html.escape(stop)
            stop_items.append(f'<li>{inner}</li>')
        detail_html = f'<ol class="route-stops">{"".join(stop_items)}</ol>'
    elif detail:
        detail_html = f'<p>{inline_markup(detail, anchors)}</p>'
    else:
        detail_html = ""
    children = ""
    if node["children"]:
        child_items = []
        for child in node["children"]:
            child_label, child_body = split_label(child["text"])
            if child_label and child_body:
                child_items.append(f'<li><strong>{html.escape(child_label)}</strong><span>{inline_markup(child_body, anchors)}</span>{render_sub_list(child["children"], anchors)}</li>')
            else:
                child_items.append(f'<li><span>{inline_markup(child["text"], anchors)}</span>{render_sub_list(child["children"], anchors)}</li>')
        children = f'<ol class="route-days">{"".join(child_items)}</ol>'
    return (
        f'<article class="route-card"{id_attr(item_anchor_id(section_id, node))}>'
        f'<span class="route-index">{index:02d}</span>'
        f'<div class="route-body"><h3>{inline_markup(title)}</h3>{detail_html}{children}</div>'
        '</article>'
    )


def render_block(nodes: list[dict], page: Page, section_id: str | None, anchor_index: AnchorIndex) -> str:
    """Render one Markdown list block with the component that suits its section."""
    if not nodes:
        return ""
    anchors = anchor_index.terms if section_id in LINKIFY_SECTION_IDS else None
    layout = section_layout(section_id, nodes)

    if layout == "facts":
        tiles = []
        for node in nodes:
            label, body = split_label(node["text"])
            if label and body:
                head = f'<span class="fact-k">{html.escape(label)}</span><p class="fact-v">{inline_markup(body, anchors, item_anchor_id(section_id, node))}</p>'
            else:
                head = f'<p class="fact-v fact-title">{inline_markup(node["text"], anchors)}</p>'
            tiles.append(
                f'<div class="fact-tile{" wide" if node["children"] else ""}"{id_attr(item_anchor_id(section_id, node))}>'
                f'{head}{render_sub_list(node["children"], anchors)}</div>'
            )
        return f'<div class="fact-grid">{"".join(tiles)}</div>'

    if layout == "scenarios":
        tiles = []
        for node in nodes:
            label, body = split_label(node["text"])
            title, detail = (label, body) if label and body else (node["text"], "")
            tiles.append(
                f'<div class="scenario-tile"{id_attr(item_anchor_id(section_id, node))}>'
                f'<span class="tile-ico">{icon(scenario_icon(title))}</span>'
                f'<div><strong>{html.escape(title)}</strong>'
                f'{f"<p>{inline_markup(detail, anchors, item_anchor_id(section_id, node))}</p>" if detail else ""}'
                f'{render_sub_list(node["children"], anchors)}</div></div>'
            )
        return f'<div class="scenario-grid">{"".join(tiles)}</div>'

    if layout == "months":
        cards = []
        others = []
        for node in nodes:
            card = render_month_card(node, section_id, anchors)
            if card:
                cards.append(card)
            else:
                others.append(node)
        out = f'<div class="month-grid" data-month-grid>{"".join(cards)}</div>' if cards else ""
        if others:
            out += f'<div class="card-grid">{"".join(render_card(page, node, section_id, anchors) for node in others)}</div>'
        return out

    if layout == "routes":
        return f'<div class="route-list">{"".join(render_route(node, idx, section_id, anchors) for idx, node in enumerate(nodes, 1))}</div>'

    if layout == "checklist":
        items = []
        for idx, node in enumerate(nodes):
            items.append(
                f'<li{id_attr(item_anchor_id(section_id, node))}><label>'
                f'<input type="checkbox" data-check-index="{idx}"><span class="check-box" aria-hidden="true">{icon("check")}</span>'
                f'<span class="check-text">{inline_markup(node["text"])}</span></label>'
                f'{render_sub_list(node["children"], anchors)}</li>'
            )
        return f'<ul class="check-list" data-checklist="{html.escape(page.key)}">{"".join(items)}</ul>'

    if layout == "tips":
        items = []
        for node in nodes:
            label, body = split_label(node["text"])
            text_html = (
                f'<strong>{html.escape(label)}</strong><p>{inline_markup(body, anchors)}</p>'
                if label and body else f'<p>{inline_markup(node["text"], anchors)}</p>'
            )
            items.append(
                f'<li class="tip-item"{id_attr(item_anchor_id(section_id, node))}>'
                f'<span class="tip-ico">{icon("alert")}</span><div>{text_html}{render_sub_list(node["children"], anchors)}</div></li>'
            )
        return f'<ul class="tip-list">{"".join(items)}</ul>'

    if layout == "areas":
        cards = []
        for node in nodes:
            label, body = split_label(node["text"])
            title, detail = (label, body) if label and body else (node["text"], "")
            places = [part.strip() for part in re.split(r"[、，,；;]", detail) if part.strip()] if detail else []
            chips = []
            for place in places:
                href = (anchors or {}).get(place)
                chips.append(
                    f'<a class="chip" href="{html.escape(href)}">{html.escape(place)}</a>' if href
                    else f'<span class="chip">{html.escape(place)}</span>'
                )
            cards.append(
                f'<article class="area-card"{id_attr(item_anchor_id(section_id, node))}>'
                f'<h3>{icon("pin")}{html.escape(title)}</h3>'
                f'<div class="chip-row">{"".join(chips)}</div>{render_sub_list(node["children"], anchors)}</article>'
            )
        return f'<div class="area-grid">{"".join(cards)}</div>'

    if layout == "cards":
        cards = [render_card(page, node, section_id, anchors) for node in nodes]
        return f'<div class="card-grid">{"".join(cards)}</div>'

    if layout == "rows":
        items = []
        for node in nodes:
            label, body = split_label(node["text"])
            visual = item_visual_html(page, node, section_id, "row-media")
            text_html = (
                f'<strong>{inline_markup(label, anchors)}</strong><span>{inline_markup(body, anchors, item_anchor_id(section_id, node))}</span>'
                if label and body else f'<span>{inline_markup(node["text"], anchors, item_anchor_id(section_id, node))}</span>'
            )
            actions = poi_action_links_html(page, item_title(node["text"]), section_id, 0)
            row_kind = "food" if section_id in FOOD_SECTION_IDS or item_kind(section_id, item_title(node["text"]), node["text"]) == "food" else "place"
            plan_button = plan_add_button(page, item_title(node["text"]), section_id, item_anchor_id(section_id, node), row_kind)
            if plan_button:
                actions = f'<div class="card-actions">{plan_button}{actions}</div>'
            items.append(
                f'<li class="row-item{" has-media" if visual else ""}"{id_attr(item_anchor_id(section_id, node))}>'
                f'{visual}<div class="row-text">{text_html}{render_sub_list(node["children"], anchors)}{actions}</div></li>'
            )
        return f'<ul class="row-list">{"".join(items)}</ul>'

    items = []
    for node in nodes:
        items.append(
            f'<li{id_attr(item_anchor_id(section_id, node))}>{inline_markup(node["text"], anchors)}'
            f'{render_sub_list(node["children"], anchors)}</li>'
        )
    return f'<ul class="plain-list">{"".join(items)}</ul>'


SECTION_ICON_RULES = [
    (("结论", "总览", "决策"), "compass"),
    (("月份", "季节", "全年"), "calendar"),
    (("票价", "营业", "时间表"), "ticket"),
    (("夜市", "市场", "商圈", "街区"), "night"),
    (("博物馆", "展馆", "展览"), "museum"),
    (("美食", "餐厅", "小吃", "吃", "口味"), "food"),
    (("住宿", "酒店"), "hotel"),
    (("交通", "出行", "地铁"), "train"),
    (("自然", "远郊", "周边", "峡", "湖", "山水", "花事"), "leaf"),
    (("路线", "线路", "行程"), "route"),
    (("避坑", "取舍", "提醒", "注意"), "alert"),
    (("复核", "清单", "核验"), "checklist"),
    (("行前", "准备"), "bag"),
    (("地图", "分区", "索引"), "map"),
    (("预算", "成本"), "ticket"),
    (("景点", "游玩", "核心", "打卡"), "pin"),
]


def section_icon(title: str) -> str:
    for keys, name in SECTION_ICON_RULES:
        if any(k in title for k in keys):
            return icon(name)
    return icon("layers")


def count_section_items(lines: list[str], start: int) -> int:
    count = 0
    for line in lines[start:]:
        if re.match(r"^#{1,3}\s+", line):
            break
        if re.match(r"^-\s+", line):
            count += 1
    return count


def render_markdown(markdown: str, page: Page, anchor_index: AnchorIndex) -> tuple[str, list[tuple[int, str, str]]]:
    lines = markdown.splitlines()
    html_parts: list[str] = []
    toc: list[tuple[int, str, str]] = []
    used: set[str] = set()
    i = 0
    open_section = False
    current_section_id: str | None = None

    def close_section() -> None:
        nonlocal open_section, current_section_id
        if open_section:
            html_parts.append("</div></section>")
            open_section = False
            current_section_id = None

    while i < len(lines):
        line = lines[i]
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            hashes, text = heading.groups()
            level = len(hashes)
            if level == 1:
                i += 1
                continue
            close_section()
            sid = slugify(text.strip(), used)
            current_section_id = sid
            toc.append((level, text.strip(), sid))
            count = count_section_items(lines, i + 1)
            badge = f'<span class="section-count">{count}</span>' if count >= 3 else ""
            layout = SECTION_LAYOUTS.get(sid, "auto")
            html_parts.append(f'<section id="{sid}" class="guide-section level-{level} layout-{layout}">')
            html_parts.append(
                f'<h{level} class="section-title"><span class="sec-ico">{section_icon(text.strip())}</span>'
                f'<span class="section-name">{inline_markup(text.strip())}</span>{badge}</h{level}>'
            )
            html_parts.append('<div class="section-body">')
            open_section = True
            i += 1
            continue

        if re.match(r"^\s*-\s+", line):
            block: list[str] = []
            while i < len(lines) and (re.match(r"^\s*-\s+", lines[i]) or not lines[i].strip()):
                block.append(lines[i])
                i += 1
            html_parts.append(render_block(parse_list(block), page, current_section_id, anchor_index))
            continue

        if line.strip():
            anchors = anchor_index.terms if current_section_id in LINKIFY_SECTION_IDS else None
            html_parts.append(f'<p class="section-note">{inline_markup(line.strip(), anchors)}</p>')
        i += 1

    close_section()
    return "\n".join(html_parts), toc


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def extract_first_list_after(markdown: str, heading: str, max_items: int = 5) -> list[str]:
    lines = markdown.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start = idx + 1
            break
    if start is None:
        return []
    items = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        match = re.match(r"^- (.+)$", line)
        if match:
            items.append(match.group(1).strip())
        if len(items) >= max_items:
            break
    return items


def extract_first_nodes_after(markdown: str, heading: str, max_items: int = 4) -> list[dict]:
    lines = markdown.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start = idx + 1
            break
    if start is None:
        return []
    block: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if re.match(r"^\s*-\s+", line) or (block and not line.strip()):
            block.append(line)
    return parse_list(block)[:max_items]


def quick_summary(node: dict) -> str:
    pieces = []
    for text in flatten_node_text(node):
        clean = re.sub(r"https?://\S+", "", text)
        clean = re.sub(r"`([^`]+)`", r"\1", clean).strip()
        if clean:
            pieces.append(clean)
        if len(pieces) >= 2:
            break
    if not pieces:
        label, body = split_label(node["text"])
        pieces.append(body if label else node["text"])
    summary = "；".join(pieces)
    return summary[:96]


def pick_section_href(anchor_index: AnchorIndex, candidates: list[str]) -> str | None:
    for sid in candidates:
        if sid in anchor_index.section_ids:
            return f"#{sid}"
    return None


def gallery_image_paths(page: Page) -> list[Path]:
    if page.key == "record":
        # 首页只用城市主图（1600x900 的景观图），均匀采样，避免把上千张条目图塞进图廊拖慢渲染。
        candidates = [p for p in sorted(IMAGES.glob("*.png")) if p.stem != "record" and p.exists()]
        limit = 30
        if len(candidates) > limit:
            step = len(candidates) / limit
            candidates = [candidates[int(i * step)] for i in range(limit)]
        lead = [IMAGES / "record.png"] if (IMAGES / "record.png").exists() else []
        return lead + candidates
    paths = [IMAGES / f"{page.key}.png"] + sorted((ITEM_IMAGES / page.key).glob("*.png"))
    paths = [path for path in paths if path.exists()]
    return paths[:16]


def carousel_entries(page: Page) -> list[tuple[Path, str, Path | None, str]]:
    """轮播条目 (图片, 标题, 跳转目标 or None, 副标题)。优先真实照片。"""
    load_photo_cache()
    entries: list[tuple[Path, str, Path | None, str]] = []
    if page.key == "record":
        with_photo = []
        for p in PAGES:
            if p.key == "record":
                continue
            img = IMAGES / f"{p.key}.jpg"
            meta = PHOTO_CACHE.get(f"cityphoto|{p.key}")
            # 只用有真实照片的城市，不再混入插画
            if img.exists() and photo_is_publishable(meta, p.key):
                with_photo.append((img, p.title.replace("旅游攻略", ""), p.output, p.subtitle))
        # 编辑精选城市排在前面，其余按固定种子打散，保证构建可复现。
        preferred = {key: idx for idx, key in enumerate(FEATURED_KEYS_PREF)}
        lead = sorted((entry for entry in with_photo if entry[2].stem in preferred), key=lambda entry: preferred[entry[2].stem])
        rest = [entry for entry in with_photo if entry[2].stem not in preferred]
        random.Random("hero-carousel").shuffle(rest)
        entries = (lead + rest)[:14]
    else:
        name = page.title.replace("旅游攻略", "")
        img = IMAGES / f"{page.key}.jpg"
        meta = PHOTO_CACHE.get(f"cityphoto|{page.key}")
        if img.exists() and photo_is_publishable(meta, page.key):
            entries.append((img, name, None, page.subtitle))
    return entries


def hero_carousel_html(page: Page, captions: bool = True) -> str:
    entries = carousel_entries(page)
    if not entries:
        return ""
    slides = []
    dots = []
    for idx, (img, name, target, sub) in enumerate(entries):
        rel = rel_to(img, page.output.parent)
        active = " active" if idx == 0 else ""
        loading = "eager" if idx == 0 else "lazy"
        cap = (
            f'<div class="slide-cap"><strong>{html.escape(name)}</strong>'
            f'{("<span>" + html.escape(sub) + "</span>") if sub else ""}</div>'
        ) if captions else ""
        srcset = cover_srcset(img.stem, page.output.parent)
        if idx == 0:
            source_attr = f'src="{html.escape(rel)}"{srcset}'
        else:
            source_attr = f'data-src="{html.escape(rel)}"' + (srcset.replace(" srcset=", " data-srcset=") if srcset else "")
        sizes = ' sizes="100vw"' if not captions else ' sizes="(max-width: 1080px) 100vw, 50vw"'
        inner = f'<img {source_attr}{sizes if srcset else ""} alt="{html.escape(name)}" width="1280" height="720" loading="{loading}" decoding="async">{cap}'
        if target is not None:
            href = rel_to(target, page.output.parent)
            hidden = "false" if idx == 0 else "true"
            tabindex = "0" if idx == 0 else "-1"
            slides.append(f'<a class="hero-slide{active}" href="{html.escape(href)}" aria-hidden="{hidden}" tabindex="{tabindex}">{inner}</a>')
        else:
            hidden = "false" if idx == 0 else "true"
            slides.append(f'<div class="hero-slide{active}" aria-hidden="{hidden}">{inner}</div>')
        current = ' aria-current="true"' if idx == 0 else ""
        dots.append(f'<button class="hero-dot{active}" type="button" data-i="{idx}" aria-label="第 {idx + 1} 张"{current}></button>')
    controls = ""
    if len(entries) > 1:
        controls = (
            '<button class="hero-arrow prev" type="button" aria-label="上一张" data-dir="-1">‹</button>'
            '<button class="hero-arrow next" type="button" aria-label="下一张" data-dir="1">›</button>'
            f'<div class="hero-dots">{"".join(dots)}</div>'
            '<button class="hero-pause" type="button" aria-label="暂停自动轮播" aria-pressed="false" title="暂停自动轮播">Ⅱ</button>'
        )
    return (
        '<div class="hero-carousel" id="heroCarousel" data-count="' + str(len(entries)) + '">'
        f'<div class="hero-slides">{"".join(slides)}</div>'
        f'{controls}'
        '</div>'
    )


def city_cover_credit_html(page: Page) -> str:
    """Render a compact, source-specific credit for a publishable city cover."""
    if page.key in HUB_KEYS:
        return ""
    load_photo_cache()
    entry = PHOTO_CACHE.get(f"cityphoto|{page.key}")
    if not photo_is_publishable(entry, page.key):
        return ""
    source = str(entry.get("source", "")).strip()
    artist = str(entry.get("artist", "")).strip()
    license_name = str(entry.get("license", "")).strip()
    city_name = page.title.replace("旅游攻略", "")
    source_label = f"查看{city_name}封面照片原始来源（新窗口打开）"
    return (
        '<p class="hero-photo-credit">'
        '<span class="hero-photo-credit-kicker">实景封面</span>'
        f'<span class="hero-photo-credit-meta">摄影：{html.escape(artist)} · {html.escape(license_name)}</span>'
        f'<a href="{html.escape(source, quote=True)}" target="_blank" rel="noopener noreferrer" '
        f'aria-label="{html.escape(source_label, quote=True)}">原始来源 <span aria-hidden="true">↗</span></a>'
        '</p>'
    )


def nav_html(current: Page) -> str:
    current_out = current.output
    current_profile = city_profile(current) if current.key not in HUB_KEYS else None
    catalog_href = rel_to(OUT / "destinations.html", current_out.parent)
    counts: dict[str, int] = {}
    for page in PAGES:
        if page.key == "record":
            continue
        province = city_profile(page)["province"]
        if province in DIRECT_MUNICIPALITIES:
            label = "直辖市"
        elif province in SPECIAL_REGIONS:
            label = "港澳"
        else:
            label = province
        counts[label] = counts.get(label, 0) + 1

    provinces = sorted(
        (label for label in counts if label not in {"直辖市", "港澳"}),
        key=lambda label: nav_label_sort_key(label, PROVINCE_SORT_KEYS),
    )
    labels = (["直辖市"] if counts.get("直辖市") else []) + provinces
    if counts.get("港澳"):
        labels.append("港澳")

    current_group = ""
    if current_profile:
        current_province = current_profile["province"]
        if current_province in DIRECT_MUNICIPALITIES:
            current_group = "直辖市"
        elif current_province in SPECIAL_REGIONS:
            current_group = "港澳"
        else:
            current_group = current_province

    menus = []
    for label in labels:
        if label == "直辖市":
            kind = "municipality"
            directory_href = catalog_href
        elif label == "港澳":
            kind = "special"
            directory_href = f'{catalog_href}?region={quote("港澳")}'
        else:
            kind = "province"
            directory_href = f'{catalog_href}?province={quote(label)}'
        active = " active" if label == current_group else ""
        menus.append(
            f'<details class="destination-nav province-nav{active}" data-nav-group="{html.escape(label)}" '
            f'data-nav-kind="{kind}">'
            f'<summary><span>{html.escape(label)}</span><small>{counts[label]} 城</small><i aria-hidden="true"></i></summary>'
            f'<div class="destination-panel province-menu" aria-label="{html.escape(label)}城市菜单">'
            '<div class="province-menu-head">'
            f'<div><strong>{html.escape(label)}</strong><span>选城市，或先按季节、天数与主题筛选</span></div>'
            f'<a class="province-directory-link" href="{directory_href}">条件筛选 →</a></div>'
            f'<div class="province-city-list" data-destination-menu aria-label="{html.escape(label)}城市列表" '
            'aria-live="polite" aria-busy="false"><p class="province-menu-status">展开后载入城市列表</p></div>'
            '</div></details>'
        )
    return f'<div class="province-nav-list" aria-label="按省份选择城市">{"".join(menus)}</div>'


def card_links(current: Page, limit: int = 10) -> str:
    """Render a small, deterministic set of relevant guides for the sidebar.

    The full catalog is already available from the header and city-guides page;
    repeating it in every article bloats all 222 generated city documents.
    """
    current_profile = city_profile(current) if current.key not in HUB_KEYS else None

    def relevance(page: Page) -> tuple[int, str]:
        if current_profile is None:
            return (0, page.key)
        profile = city_profile(page)
        score = 0
        if profile["province"] == current_profile["province"]:
            score += 100
        if profile["region"] == current_profile["region"]:
            score += 20
        current_themes = set(current_profile["themeTags"].split())
        score += len(current_themes.intersection(profile["themeTags"].split())) * 3
        return (-score, page.key)

    candidates = [page for page in PAGES if page.key not in {"record", current.key}]
    load_photo_cache()
    cards = []
    for page in sorted(candidates, key=relevance)[:limit]:
        rel = rel_to(page.output, current.output.parent)
        thumb = ""
        if photo_is_publishable(PHOTO_CACHE.get(f"cityphoto|{page.key}"), page.key) and (IMAGES / f"{page.key}.jpg").exists():
            thumb_path = COVER_SMALL / f"{page.key}.jpg" if (COVER_SMALL / f"{page.key}.jpg").is_file() else IMAGES / f"{page.key}.jpg"
            thumb = (
                f'<img src="{html.escape(rel_to(thumb_path, current.output.parent))}" alt="" '
                'width="120" height="80" loading="lazy" decoding="async">'
            )
        cards.append(
            f'<a class="city-card related-card" href="{rel}" style="--accent:{page.accent}">'
            f'{thumb}<span><strong>{html.escape(city_profile(page)["city"])}</strong><small>{html.escape(page.subtitle)}</small></span></a>'
        )
    catalog_href = rel_to(OUT / "city-guides.html", current.output.parent)
    cards.append(f'<a class="city-catalog-link" href="{catalog_href}">查看全部城市攻略 →</a>')
    return "\n".join(cards)


MARKDOWN_CACHE: dict[str, str] = {}
CITY_PROFILE_CACHE: dict[str, dict] = {}
REVIEW_DATE_PATTERN = re.compile(
    r"(?:动态信息核验日期|资料整理日期|信息核验日期|来源核验日期|核验日期|更新日期)"
    r"\s*[:：为]?\s*(20\d{2}-\d{1,2}-\d{1,2})"
)


def read_markdown_cached(page: Page) -> str:
    if page.key not in MARKDOWN_CACHE:
        MARKDOWN_CACHE[page.key] = page.source.read_text(encoding="utf-8")
    return MARKDOWN_CACHE[page.key]


def explicit_review_date(page: Page, markdown: str | None = None) -> str:
    """Return a version-controlled review date, never a filesystem mtime.

    City metadata may opt in an explicit date; otherwise the generator only
    accepts a labelled date written in the Markdown source.  Missing evidence
    stays visible as ``未核验`` so copying or rebuilding the repository cannot
    silently turn a file timestamp into a travel-fact claim.
    """
    meta = read_city_meta().get(page.source.stem, {}) if page.source else {}
    for key in ("sources_reviewed_at", "reviewed_at", "content_updated_at"):
        value = str(meta.get(key, "") or "").strip()
        if re.fullmatch(r"20\d{2}-\d{1,2}-\d{1,2}", value):
            try:
                return date.fromisoformat(value).isoformat()
            except ValueError:
                pass
    text = markdown if markdown is not None else read_markdown_cached(page)
    match = REVIEW_DATE_PATTERN.search(text)
    if match:
        try:
            return date.fromisoformat(match.group(1)).isoformat()
        except ValueError:
            pass
    return "未核验"


def page_location(page: Page) -> tuple[str, str]:
    if page.key in HUB_KEYS:
        return "总览", "全国"
    province, city = split_city_filename(page.source)
    if province in DIRECT_MUNICIPALITIES and province == city:
        return "直辖市", city
    return province, city


def clean_summary(text: str, limit: int = 70) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_#>-]+", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ：:，,。；;")
    return text[:limit]


def extract_section_titles(markdown: str, headings: list[str], max_items: int = 5) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for heading in headings:
        for node in extract_first_nodes_after(markdown, heading, max_items):
            title = item_title(node["text"])
            if 2 <= len(title) <= 24 and title not in FACT_LABELS and title not in seen:
                titles.append(title)
                seen.add(title)
            if len(titles) >= max_items:
                return titles
    return titles


def extract_signature_foods(markdown: str, max_items: int = 5) -> list[str]:
    """Prefer named dishes (必吃优先级 / 代表) over menu category headings."""
    foods: list[str] = []

    def add(value: str) -> None:
        value = clean_summary(value, 16)
        if 2 <= len(value) <= 16 and value not in foods and value not in FACT_LABELS:
            foods.append(value)

    match = re.search(r"^-\s*(?:必吃优先级|必吃|代表美食|口味关键词)[：:]\s*(.+)$", markdown, re.M)
    if match:
        for part in re.split(r"[、，,；;/]", match.group(1)):
            add(part)
    for node in extract_first_nodes_after(markdown, "## 美食总表", 12):
        for child in node.get("children", []):
            label, value = split_label(child.get("text", ""))
            if label == "代表" and value:
                for part in re.split(r"[、，,；;/]", value):
                    add(part)
    return foods[:max_items]


def extract_markdown_keywords(markdown: str, max_terms: int = 80) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for line in markdown.splitlines():
        text = line.strip()
        if text.startswith("#"):
            text = text.lstrip("#").strip()
        elif text.startswith("- "):
            text = item_title(text[2:].strip())
        else:
            continue
        for term in split_index_terms(text):
            if term not in seen:
                terms.append(term)
                seen.add(term)
            if len(terms) >= max_terms:
                return terms
    return terms


REGION_PROVINCES = {
    "华北": {"北京", "天津", "河北", "山西", "内蒙古"},
    "东北": {"辽宁", "吉林", "黑龙江"},
    "华东": {"上海", "江苏", "浙江", "安徽", "福建", "江西", "山东"},
    "华中": {"河南", "湖北", "湖南"},
    "华南": {"广东", "广西", "海南"},
    "西南": {"重庆", "四川", "贵州", "云南", "西藏"},
    "西北": {"陕西", "甘肃", "青海", "宁夏", "新疆"},
    "港澳": {"香港", "澳门"},
}


def city_region(province: str) -> str:
    for region, provinces in REGION_PROVINCES.items():
        if province in provinces:
            return region
    return "其他"


def city_season_summary(markdown: str) -> str:
    # 结论里明确写了“季节：”就用它；季节景观里的“最佳月份”只描述单个景观，不能代表整座城市。
    explicit = re.search(r"^-\s*(?:季节|最佳季节|适宜季节)[：:]\s*(.+)$", markdown, re.M)
    if explicit:
        return clean_summary(re.split(r"[；;]", explicit.group(1))[0], 36)
    seasonal = extract_first_nodes_after(markdown, "## 季节限定景观", 5)
    preferred_labels = {"最佳月份", "适合时间", "可看月份", "推荐时间", "季节"}
    for node in seasonal:
        for child in node.get("children", []):
            label, value = split_label(child.get("text", ""))
            if label in preferred_labels and value:
                return clean_summary(value, 36)
    if seasonal:
        return "按季节景观与天气取舍"
    return "全年可查，按天气取舍"


def city_filter_metadata(markdown: str, foods: list[str]) -> dict[str, str]:
    compact = re.sub(r"\s+", "", markdown)
    season_rules = {
        "春": ("春", "花期", "踏青", "樱花", "油菜花"),
        "夏": ("夏", "避暑", "丰水期", "海滨", "草原"),
        "秋": ("秋", "红叶", "彩林", "银杏", "丰收"),
        "冬": ("冬", "雪景", "温泉", "避寒", "冰雪"),
    }
    season_tags = [name for name, words in season_rules.items() if any(word in compact for word in words)]
    theme_rules = {
        "亲子": ("亲子", "儿童", "乐园"),
        "博物馆": ("博物馆", "美术馆", "展馆"),
        "自然风光": ("自然", "山水", "雪山", "草原", "海滨", "海岛", "湖", "峡谷", "森林"),
        "历史文化": ("历史", "文化", "古城", "古镇", "遗址", "古建筑", "寺"),
        "美食": ("美食", "小吃", "夜市", "餐厅"),
        "避暑": ("避暑", "清凉", "夏季"),
        "冬季": ("冬季", "雪景", "温泉", "避寒", "冰雪"),
        "周末短途": ("周末", "半天", "1天", "1 天", "2天", "2 天"),
    }
    theme_tags = [name for name, words in theme_rules.items() if any(word in compact for word in words)]
    if foods and "美食" not in theme_tags:
        theme_tags.append("美食")
    transport_rules = {
        "公共交通": ("地铁", "公交", "公共交通", "景区直通车"),
        "高铁": ("高铁", "火车", "动车"),
        "飞机": ("机场", "航班", "飞机"),
        "自驾": ("自驾", "停车", "包车"),
    }
    transport_tags = [name for name, words in transport_rules.items() if any(word in compact for word in words)]
    arrangement = re.search(r"^-\s*(?:推荐天数|适合安排)[：:]\s*(.+)$", markdown, re.M)
    arrangement_text = arrangement.group(1) if arrangement else ""
    day_numbers = [int(value) for value in re.findall(r"(\d+)\s*(?:天|—\d+\s*天|-\d+\s*天)", arrangement_text)]
    day_numbers += [int(value) for value in re.findall(r"[—-]\s*(\d+)\s*天", arrangement_text)]
    max_days = max(day_numbers, default=3)
    days_class = "1" if max_days <= 1 else "2-3" if max_days <= 3 else "4+"
    return {
        "region": "",
        "seasonTags": " ".join(season_tags) or "全年",
        "themeTags": " ".join(theme_tags),
        "transportTags": " ".join(transport_tags) or "公共交通 自驾",
        "daysClass": days_class,
    }


def city_profile(page: Page) -> dict:
    if page.key in CITY_PROFILE_CACHE:
        return CITY_PROFILE_CACHE[page.key]
    markdown = read_markdown_cached(page)
    province, city = page_location(page)
    highlights = extract_section_titles(
        markdown,
        ["## 核心景点", "## 季节限定景观", "## 自然、远郊和周边", "## 先看总览", "## 快速决策索引"],
        8,
    )
    # 快速决策索引里的“半天 / 1 天 / 雨天”是场景标签，不是景点名。
    highlights = [
        title for title in highlights
        if not re.fullmatch(r"(?:半天|半日|\d+\s*(?:天|日)|雨天|亲子|摄影|夜游|周末)", title)
    ][:5]
    foods = extract_signature_foods(markdown, 5) or extract_section_titles(markdown, ["## 美食总表", "## 餐厅和店铺", "## 街区、夜市和市场", "## 街区、商圈和夜市"], 5)
    routes = extract_section_titles(markdown, ["## 路线模板", "## 跨城市路线模板"], 3)
    season = city_season_summary(markdown)
    keywords = extract_markdown_keywords(markdown)
    filters = city_filter_metadata(markdown, foods)
    filters["region"] = city_region(city if province == "直辖市" else province)
    profile = {
        "title": extract_title(markdown, page.title),
        "subtitle": page.subtitle,
        "province": province,
        "city": city,
        "season": season,
        "highlights": highlights,
        "foods": foods,
        "routes": routes,
        "keywords": keywords,
        **filters,
    }
    CITY_PROFILE_CACHE[page.key] = profile
    return profile


def site_search_index_js() -> str:
    data = []
    for page in PAGES:
        profile = city_profile(page)
        data.append({
            "key": page.key,
            "title": profile["title"],
            "subtitle": profile["subtitle"],
            "province": profile["province"],
            "city": profile["city"],
            "season": profile["season"],
            "path": rel_to(page.output, OUT),
            "highlights": profile["highlights"][:4],
            "foods": profile["foods"][:4],
            "region": profile["region"],
            "seasonTags": profile["seasonTags"],
            "themeTags": profile["themeTags"],
            "transportTags": profile["transportTags"],
            "daysClass": profile["daysClass"],
            "keywords": " ".join(profile["keywords"][:80]),
        })
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f"window.TRAVEL_SEARCH_INDEX = {payload};\n"


HOME_CITY_KEYS = (
    "beijing", "shanghai", "chengdu", "xian", "hangzhou", "qingdao",
    "chongqing", "kunming", "sanya", "guangzhou", "xiamen", "nanjing",
    "suzhou", "dali", "lijiang", "guilin", "lhasa", "urumqi",
    "harbin", "wuhan", "changsha", "luoyang", "zhangjiajie", "dunhuang",
)


def city_explorer_html(current: Page) -> str:
    all_city_pages = [page for page in PAGES if page.key != "record"]
    is_curated = current.key == "record"
    if is_curated:
        page_by_key = {page.key: page for page in all_city_pages}
        city_pages = [page_by_key[key] for key in HOME_CITY_KEYS if key in page_by_key]
    else:
        city_pages = all_city_pages
    review_dates = [explicit_review_date(page, read_markdown_cached(page)) for page in city_pages]
    review_by_key = {page.key: date_value for page, date_value in zip(city_pages, review_dates)}
    reviewed_count = sum(value != "未核验" for value in review_dates)
    pending_review_count = len(city_pages) - reviewed_count
    review_filter = (
        '<div class="review-pills" id="cityReviewFilter" role="group" aria-label="资料核验状态">'
        '<button class="review-pill active" type="button" data-review="all">全部资料</button>'
        f'<button class="review-pill" type="button" data-review="reviewed">已标注日期 {reviewed_count}</button>'
        f'<button class="review-pill" type="button" data-review="pending">待复核 {pending_review_count}</button>'
        '</div>'
    )
    provinces = []
    for page in city_pages:
        province = city_profile(page)["province"]
        if province not in provinces:
            provinces.append(province)
    filters = ['<button class="province-pill active" type="button" data-province="全部">全部</button>']
    filters.extend(
        f'<button class="province-pill" type="button" data-province="{html.escape(province)}">{html.escape(province)}</button>'
        for province in provinces
    )
    load_photo_cache()
    cards = []
    for card_index, page in enumerate(city_pages):
        profile = city_profile(page)
        review_date = review_by_key[page.key]
        review_status = "reviewed" if review_date != "未核验" else "pending"
        rel = rel_to(page.output, current.output.parent)
        image = rel_to(IMAGES / f"{page.key}.jpg", current.output.parent)
        highlights = "、".join(profile["highlights"][:4]) or "核心景点见正文"
        foods = "、".join(profile["foods"][:4]) or "必吃美食见正文"
        tags = [profile["province"], profile["season"], *profile["highlights"][:2], *profile["foods"][:2]]
        tag_html = "".join(f"<em>{html.escape(tag)}</em>" for tag in tags if tag)
        search_text = " ".join([profile["title"], profile["subtitle"], profile["province"], profile["city"], highlights, foods, " ".join(profile["keywords"][:50])])
        photo_meta = PHOTO_CACHE.get(f"cityphoto|{page.key}")
        badge = ""
        img_title = ""
        if photo_is_publishable(photo_meta, page.key):
            badge = '<span class="photo-badge">实景</span>'
            credit = "实景照片"
            if photo_meta.get("license"):
                credit += " · " + photo_meta["license"]
            credit += " · Wikimedia Commons"
            img_title = f' title="{html.escape(credit)}"'
        data_attrs = (
            f'data-key="{html.escape(page.key)}" data-name="{html.escape(profile["title"])}" '
            f'data-href="{html.escape(rel)}" data-sub="{html.escape(profile["subtitle"])}"'
        )
        fav_btn = f'<button class="fav-btn" type="button" {data_attrs} aria-label="收藏 {html.escape(profile["title"])}">☆</button>'
        trip_btn = f'<button class="trip-btn" type="button" {data_attrs} aria-label="加入行程 {html.escape(profile["title"])}">＋</button>'
        body_html = (
            '<div class="city-card-body">'
            f'<a class="city-card-title" href="{html.escape(rel)}">{html.escape(profile["title"])}</a>'
            f'<small>{html.escape(profile["subtitle"])}</small>'
            f'<span class="city-review-status {review_status}">{"已标注核验日期：" + html.escape(review_date) if review_status == "reviewed" else "资料待复核"}</span>'
            f'<p><strong>景点</strong>{html.escape(highlights)}</p>'
            f'<p><strong>吃喝</strong>{html.escape(foods)}</p>'
            f'<div class="city-tags">{tag_html}</div>'
            '</div>'
        )
        common_attrs = (
            f'style="--accent:{page.accent}" data-href="{html.escape(rel)}" '
            f'data-province="{html.escape(profile["province"])}" data-region="{html.escape(profile["region"])}" '
            f'data-season="{html.escape(profile["seasonTags"])}" data-days="{html.escape(profile["daysClass"])}" '
            f'data-theme="{html.escape(profile["themeTags"])}" data-transport="{html.escape(profile["transportTags"])}" '
            f'data-review-status="{review_status}" data-review-date="{html.escape(review_date)}" '
            f'data-search="{html.escape(search_text)}" data-key="{html.escape(page.key)}" data-index="{card_index}" '
            f'data-city="{html.escape(profile["city"])}"'
        )
        has_photo = photo_is_publishable(photo_meta, page.key)
        if has_photo:
            cards.append(
                f'<article class="city-card rich" {common_attrs}>'
                f'<span class="img-frame">{badge}{fav_btn}{trip_btn}'
                f'<img src="{html.escape(rel_to(COVER_SMALL / f"{page.key}.jpg", current.output.parent) if (COVER_SMALL / f"{page.key}.jpg").is_file() else image)}" alt="{html.escape(profile["title"])}缩略图" width="640" height="360" loading="lazy" decoding="async"{img_title}></span>'
                f'{body_html}</article>'
            )
        else:
            # 无真实照片 → 纯文字卡（不放插画）
            cards.append(
                f'<article class="city-card noimg" {common_attrs}>{fav_btn}{trip_btn}{body_html}</article>'
            )
    return (
        f'<section class="city-explorer" id="city-explorer" data-catalog-scope="{"curated" if is_curated else "complete"}">'
        '<div class="city-explorer-head">'
        '<p class="eyebrow">City Finder</p>'
        f'<h2>{"24 座精选城市" if is_curated else "城市快速筛选"}</h2>'
        f'<p>{"从全国不同区域挑选高频目的地，完整 222 城仍可通过全站搜索和目的地目录查找。" if is_curated else "按省份、城市、景点、美食或季节关键词快速定位攻略，先展示最相关的一批结果。"}</p>'
        f'<p class="content-review-note"><strong>资料状态</strong><span>{pending_review_count} 座待复核</span><small>{reviewed_count} 座已标注核验日期；价格、开放时间和预约规则仍请出行前复核。</small></p>'
        '</div>'
        '<div class="city-explorer-tools">'
        f'<div class="province-pills" aria-label="省份筛选">{"".join(filters)}</div>'
        f'{review_filter}'
        '<div class="city-explorer-row">'
        '<label class="city-explorer-search"><span>筛选城市</span>'
        '<input id="cityExplorerSearch" type="search" placeholder="例如：雪山、夜市、博物馆、春花、避暑"></label>'
        '<label class="city-sort"><span>排序</span><select id="citySort">'
        '<option value="">推荐顺序</option><option value="photo">有实景照片优先</option>'
        '<option value="reviewed">已标注核验日期优先</option><option value="name">按城市名</option></select></label>'
        '<button id="randomCity" type="button" class="random-city">🎲 随机一座</button>'
        '</div>'
        '<div class="finder-chips" id="finderChips" aria-label="已选条件" hidden></div>'
        '</div>'
        f'<div class="city-grid rich-grid" id="cityExplorer">{"".join(cards)}</div>'
        '<div class="city-explorer-empty" id="cityExplorerEmpty" hidden>'
        '<strong>没有完全符合的城市</strong>'
        '<p>可以先去掉一个条件，或换个关键词：</p>'
        '<div class="chip-row" id="cityExplorerSuggest"></div>'
        '</div>'
        '<div class="city-explorer-footer">'
        '<p id="cityExplorerSummary" aria-live="polite"></p>'
        '<button id="cityLoadMore" class="city-load-more" type="button">显示更多城市</button>'
        f'{"<a class=\"city-catalog-link\" href=\"destinations.html\">浏览全部 222 座城市 →</a>" if is_curated else ""}'
        '</div>'
        '</section>'
    )


ATTRACTION_HEADINGS = ["## 核心景点", "## 季节限定景观", "## 自然、远郊和周边", "## 自然和周边"]
FOOD_HEADINGS = ["## 美食总表", "## 餐厅和店铺", "## 街区、夜市和市场", "## 街区、商圈和夜市"]


def home_finder_html(current: Page) -> str:
    if current.key not in {"record", "destinations"}:
        return ""
    region_options = "".join(f'<option value="{region}">{region}</option>' for region in REGION_PROVINCES)
    return (
        '<section class="travel-finder reveal" id="travel-finder" aria-labelledby="travelFinderTitle">'
        '<div class="travel-finder-copy">'
        '<p class="eyebrow">Plan by needs</p>'
        '<h2 id="travelFinderTitle">先定条件，再选城市</h2>'
        '<p>把地区、季节、天数、主题和交通方式组合起来，结果会同步到城市攻略列表。</p>'
        '</div>'
        '<form class="travel-finder-form" id="travelFinderForm">'
        '<label class="finder-query"><span>想去哪里或想看什么</span>'
        '<input id="travelQuery" type="search" autocomplete="off" placeholder="例如：海边、博物馆、古城、火锅"></label>'
        '<label><span>地区</span><select id="travelRegion"><option value="">全国</option>' + region_options + '</select></label>'
        '<label><span>季节</span><select id="travelSeason"><option value="">不限</option>'
        '<option value="春">春季</option><option value="夏">夏季</option><option value="秋">秋季</option><option value="冬">冬季</option></select></label>'
        '<label><span>出行天数</span><select id="travelDays"><option value="">不限</option>'
        '<option value="1">1 天内</option><option value="2-3">2-3 天</option><option value="4+">4 天以上</option></select></label>'
        '<label><span>旅行主题</span><select id="travelTheme"><option value="">不限</option>'
        '<option value="亲子">亲子</option><option value="博物馆">博物馆</option><option value="自然风光">自然风光</option>'
        '<option value="历史文化">历史文化</option><option value="美食">美食</option><option value="避暑">避暑</option>'
        '<option value="冬季">冬季</option><option value="周末短途">周末短途</option></select></label>'
        '<label><span>交通方式</span><select id="travelTransport"><option value="">不限</option>'
        '<option value="公共交通">公共交通</option><option value="高铁">高铁</option><option value="飞机">飞机</option><option value="自驾">自驾</option></select></label>'
        '<div class="travel-finder-actions">'
        '<button id="travelFinderReset" class="finder-reset" type="reset" aria-label="重置旅行筛选" title="重置筛选">↺</button>'
        '<a class="finder-results-link" href="#city-explorer">查看匹配城市</a>'
        '</div>'
        '<p id="travelFinderSummary" class="finder-summary" aria-live="polite">正在整理城市…</p>'
        '</form>'
        '</section>'
    )


HOME_THEMES = [
    ("👨‍👩‍👧", "亲子轻松游", "博物馆 · 乐园 · 低强度路线", "亲子"),
    ("🏛️", "博物馆巡礼", "城市史 · 艺术 · 工业遗产", "博物馆"),
    ("🏔️", "自然风光", "雪山 · 湖海 · 草原 · 峡谷", "自然风光"),
    ("🏯", "历史文化", "古城 · 古建 · 遗址 · 非遗", "历史文化"),
    ("🍜", "为美食出发", "早市 · 老店 · 夜市 · 地方菜", "美食"),
    ("🍃", "避暑清凉", "高原凉都 · 山林 · 海滨", "避暑"),
    ("❄️", "冬季限定", "冰雪 · 温泉 · 避寒 · 海鸥", "冬季"),
    ("🎒", "周末短途", "1-3 天 · 少换酒店 · 轻装出发", "周末短途"),
]


def home_themes_html() -> str:
    cards = "".join(
        f'<button type="button" class="theme-card reveal" data-theme-search="{html.escape(kw)}" '
        f'aria-label="按「{html.escape(title)}」筛选城市">'
        f'<span class="theme-emoji" aria-hidden="true">{emoji}</span>'
        f'<strong>{html.escape(title)}</strong><span>{html.escape(desc)}</span></button>'
        for emoji, title, desc, kw in HOME_THEMES
    )
    return (
        '<section class="home-section reveal" id="home-themes" aria-label="精选主题">'
        '<div class="home-section-head"><p class="eyebrow">Themes</p>'
        '<h2>按兴趣找去处</h2><p>点击主题，自动在下方「城市快速筛选」里按关键词过滤。</p></div>'
        f'<div class="theme-grid">{cards}</div>'
        '</section>'
    )


def home_tools_html() -> str:
    months = "".join(f'<option value="{m}">{m} 月</option>' for m in range(1, 13))
    return (
        '<section class="home-section reveal" id="homeTools" aria-label="实用工具">'
        '<div class="home-section-head"><p class="eyebrow">Toolkit</p>'
        '<h2>实用小工具</h2><p>行程节奏、季节适宜与打包清单，帮你更快做决定。</p></div>'
        '<div class="tools-grid">'
        '<a class="tool-card roadtrip-tool-entry" href="roadtrip.html">'
        '<h3>生成自驾路书</h3>'
        '<p class="tool-hint">选择所在地、目的地和天数，生成路线、逐日安排、预算与风险提醒。</p>'
        '<span class="tool-action">开始规划 →</span>'
        '</a>'
        '<div class="tool-card">'
        '<h3>行程节奏速算</h3>'
        '<p class="tool-hint">按出行天数估算合理的城市数量与游玩节奏。</p>'
        '<div class="tool-row"><label for="tripDays">出行天数</label>'
        '<input id="tripDays" type="number" min="1" max="30" value="5" inputmode="numeric"></div>'
        '<div class="tool-output" id="tripPaceOut"></div>'
        '</div>'
        '<div class="tool-card">'
        '<h3>月份适宜速查</h3>'
        '<p class="tool-hint">选择出行月份，看看当季适合的主题与去处。</p>'
        f'<div class="tool-row"><label for="tripMonth">出行月份</label><select id="tripMonth">{months}</select></div>'
        '<div class="tool-output" id="monthGuideOut"></div>'
        '</div>'
        '<div class="tool-card">'
        '<h3>打包清单生成</h3>'
        '<p class="tool-hint">选择出行类型，生成对应的随身清单。</p>'
        '<div class="tool-chip-row" id="packTypes">'
        '<button type="button" class="tool-chip active" data-pack="city">城市观光</button>'
        '<button type="button" class="tool-chip" data-pack="mountain">山地徒步</button>'
        '<button type="button" class="tool-chip" data-pack="plateau">高原</button>'
        '<button type="button" class="tool-chip" data-pack="summer">夏季避暑</button>'
        '<button type="button" class="tool-chip" data-pack="winter">冬季</button>'
        '</div>'
        '<div class="tool-output" id="packListOut"></div>'
        '</div>'
        '</div>'
        '</section>'
    )


FEATURED_KEYS_PREF = [
    "chengdu", "guilin", "xian", "hangzhou", "dali", "lijiang", "chongqing",
    "xiamen", "suzhou", "nanjing", "guiyang", "kunming", "sanya", "qingdao",
    "harbin", "datong", "zhangjiajie", "dunhuang",
]


def home_featured_html(current: Page) -> str:
    load_photo_cache()
    bykey = {p.key: p for p in PAGES}
    picks: list[Page] = []
    seen: set[str] = set()
    def has_photo(key: str) -> bool:
        return photo_is_publishable(PHOTO_CACHE.get(f"cityphoto|{key}"), key)
    for k in FEATURED_KEYS_PREF:
        p = bykey.get(k)
        if p and has_photo(k) and k not in seen:
            picks.append(p); seen.add(k)
    for p in PAGES:
        if len(picks) >= 14:
            break
        if p.key == "record" or p.key in seen or not has_photo(p.key):
            continue
        picks.append(p); seen.add(p.key)
    cards = []
    for p in picks[:14]:
        prof = city_profile(p)
        img = rel_to(IMAGES / f"{p.key}.jpg", current.output.parent)
        href = rel_to(p.output, current.output.parent)
        name = prof["title"].replace("旅游攻略", "")
        cards.append(
            f'<a class="featured-card" href="{html.escape(href)}">'
            f'<img src="{html.escape(rel_to(COVER_SMALL / f"{p.key}.jpg", current.output.parent) if (COVER_SMALL / f"{p.key}.jpg").is_file() else img)}" alt="{html.escape(name)}" width="640" height="360" loading="lazy" decoding="async">'
            f'<span class="featured-grad"></span>'
            f'<span class="featured-name">{html.escape(name)}</span>'
            '</a>'
        )
    return (
        '<section class="home-section reveal" aria-label="编辑精选">'
        '<div class="home-section-head"><p class="eyebrow">Editor’s Picks</p>'
        '<h2>编辑精选 · 人气目的地</h2><p>左右滑动，挑一座城市开始你的行程。</p></div>'
        f'<div class="featured-strip">{"".join(cards)}</div>'
        '</section>'
    )


def research_link_url(kind: str, query: str) -> str:
    encoded = quote(query)
    if kind == "official":
        return "https://www.baidu.com/s?wd=" + quote(query + " 文旅 官方 开放时间 预约 票价")
    if kind == "ctrip":
        return "https://you.ctrip.com/searchsite/?query=" + quote(query + " 旅游攻略")
    if kind == "mafengwo":
        return "https://www.mafengwo.cn/search/q.php?q=" + quote(query + " 旅游攻略")
    if kind == "qunar":
        return "https://travel.qunar.com/search/all/" + quote(query)
    if kind == "bilibili":
        return "https://search.bilibili.com/all?keyword=" + quote(query + " 旅游攻略")
    if kind == "douyin":
        return "https://www.douyin.com/search/" + quote(query + " 旅游攻略")
    if kind == "xiaohongshu":
        return "https://www.xiaohongshu.com/search_result?keyword=" + encoded + "&type=54"
    if kind == "images":
        return "https://image.baidu.com/search/index?tn=baiduimage&word=" + quote(query + " 景点 美食")
    return "#"


POI_OFFICIAL_LINKS = {
    ("青岛", "青岛啤酒博物馆"): "https://www.tsingtaomuseum.com/",
    ("青岛", "青岛市博物馆"): "https://www.qingdaomuseum.cn/",
    ("青岛", "崂山风景区"): "https://www.qdlaoshan.cn/",
    ("香港", "香港故宫文化博物馆"): "https://www.hkpm.org.hk/",
    ("澳门", "澳门博物馆"): "https://www.macaumuseum.gov.mo/",
}


def poi_action_links_html(page: Page, title: str, section_id: str | None, depth: int) -> str:
    """Place a few useful exits where a traveller is already reading about a place."""
    if page.key in HUB_KEYS or depth != 0 or section_id not in {"attractions", "museums", "seasonal"}:
        return ""
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) < 2 or len(title) > 48 or title in {"使用说明", "核心景区", "推荐地点"}:
        return ""
    profile = city_profile(page)
    city = profile["city"]
    query = f"{city} {title}" if city and city not in title else title
    official_url = POI_OFFICIAL_LINKS.get((city, title)) or research_link_url("official", query)
    map_url = (
        "https://uri.amap.com/search?keyword=" + quote(query)
        + "&city=" + quote(city)
        + "&src=travel_ayuan&coordinate=gaode&callnative=0"
    )
    guide_url = research_link_url("ctrip", query)
    links = [
        ("search", "查官网", "查询官方开放、预约与票价信息", official_url),
        ("map", "地图", "在高德地图查看位置与路线", map_url),
        ("book", "攻略", "查看补充攻略并交叉核验", guide_url),
    ]
    items = "".join(
        f'<a class="poi-action poi-action-{icon}" href="{html.escape(url)}" target="_blank" '
        f'rel="noopener noreferrer" title="{html.escape(tip)}" '
        f'aria-label="{html.escape(title + "：" + tip)}"><i aria-hidden="true"></i>{html.escape(label)}<b aria-hidden="true">↗</b></a>'
        for icon, label, tip, url in links
    )
    return f'<nav class="poi-actions" aria-label="{html.escape(title)}实用链接">{items}</nav>'


def research_panel_html(page: Page) -> str:
    if page.key in HUB_KEYS:
        return (
            '<section class="research-panel reveal" id="research-sources" aria-label="资料更新规则">'
            '<div class="research-copy"><p class="eyebrow">Research</p>'
            '<h2>资料更新规则</h2>'
            '<p>正文优先保留已归纳内容；易变信息以官方文旅、景区公告、博物馆官网和购票平台为准，'
            '社媒只用于发现高频路线、拍照点和避坑经验。</p></div>'
            '<div class="research-grid">'
            '<a href="https://www.mct.gov.cn/" target="_blank" rel="noreferrer"><strong>文化和旅游部</strong><span>政策、文旅动态、公共服务入口</span></a>'
            '<a href="https://you.ctrip.com/" target="_blank" rel="noreferrer"><strong>携程攻略</strong><span>景点、票务、用户路线参考</span></a>'
            '<a href="https://www.mafengwo.cn/" target="_blank" rel="noreferrer"><strong>马蜂窝</strong><span>长攻略、游记和路线灵感</span></a>'
            '<a href="https://travel.qunar.com/" target="_blank" rel="noreferrer"><strong>去哪儿攻略</strong><span>景点检索和票务交叉核验</span></a>'
            '</div></section>'
        )

    # 城市页的外部入口放在具体景点旁边；大面板只保留在总览页。
    return ""


def trip_toggle_html() -> str:
    """Header entry for the trip workspace (the mobile tab bar has its own)."""
    return (
        '<button class="trip-dock-toggle" id="tripDockToggle" type="button" aria-controls="tripDock" aria-expanded="false">'
        f'{icon("bag")}<span>行程</span><strong id="tripDockCount" aria-label="行程中的城市数">0</strong></button>'
    )


def trip_workspace_html(current: Page) -> str:
    """Render the global, browser-local trip workspace entry and drawer."""
    user_href = rel_to(OUT / "plan.html", current.output.parent)
    return f"""  <div class="trip-dock-backdrop" id="tripDockBackdrop" hidden></div>
  <aside class="trip-dock" id="tripDock" role="dialog" aria-modal="true" aria-labelledby="tripDockTitle" tabindex="-1" hidden>
    <header class="trip-dock-head">
      <div><p class="eyebrow">Trip workspace</p><h2 id="tripDockTitle">当前行程</h2></div>
      <button class="trip-dock-close" id="tripDockClose" type="button" aria-label="关闭行程工作台" title="关闭">×</button>
    </header>
    <div class="trip-dock-body">
      <p class="trip-dock-intro">这里是想去的城市清单。具体景点请在城市攻略里点“＋ 加入行程”，再到“行程计划”按天安排。数据只保存在这台设备。</p>
      <div class="trip-dock-list" id="tripDockList"></div>
      <div class="trip-dock-empty" id="tripDockEmpty"><strong>行程还是空的</strong><span>在城市卡片或攻略速览中点击“加入行程”。</span></div>
    </div>
    <footer class="trip-dock-footer">
      <button id="tripDockClear" type="button">清空行程</button>
      <a href="{html.escape(user_href)}">按天排行程 <span aria-hidden="true">→</span></a>
    </footer>
  </aside>"""


def extract_urls(markdown: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"https?://[^\s)）>]+", markdown):
        url = match.group(0).rstrip("。；;，,")
        if url not in seen:
            urls.append(url)
            seen.add(url)
    return urls


def source_label(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    labels = {
        "www.bilibili.com": "哔哩哔哩视频",
        "search.bilibili.com": "哔哩哔哩检索",
        "m.bilibili.com": "哔哩哔哩视频",
        "www.qingdao.gov.cn": "青岛市政府",
        "www.qdlaoshan.cn": "崂山风景区官网",
        "www.tsingtaomuseum.com": "青岛啤酒博物馆官网",
        "www.qingdaomuseum.cn": "青岛市博物馆官网",
        "www.discoverhongkong.com": "香港旅游发展局",
        "www.hko.gov.hk": "香港天文台",
        "www.hkpm.org.hk": "香港故宫文化博物馆",
        "www.macaotourism.gov.mo": "澳门旅游局",
        "www.wh.mo": "澳门世界遗产",
        "www.jlcity.gov.cn": "吉林市政府",
        "xxgk.jlcity.gov.cn": "吉林市政府信息公开",
        "www.jl.gov.cn": "吉林省政府",
        "www.panjin.gov.cn": "盘锦市政府",
        "www.panda.org.cn": "成都大熊猫繁育研究基地",
        "www.chnmus.net": "河南博物院",
        "www.wanfenglin.com": "万峰林景区",
        "www.3gmuseum.cn": "重庆中国三峡博物馆",
    }
    if domain in labels:
        return labels[domain]
    domain = domain.removeprefix("www.").removeprefix("m.")
    return domain or "来源网页"


def bilibili_embed_url(url: str) -> str | None:
    match = re.search(r"/video/(BV[0-9A-Za-z]+)", url)
    if not match:
        return None
    return f"https://player.bilibili.com/player.html?bvid={match.group(1)}&high_quality=1&danmaku=0"


def source_media_has_republication_rights(source_media: dict) -> bool:
    """Only render copied source-page media when its reuse basis is explicit.

    A public URL or a successful download is not evidence that an image may be
    republished.  The cache may opt in a future asset with a license plus an
    attribution/authorization field; legacy entries without those fields stay
    source-link-only.
    """
    license_name = str(source_media.get("license", "") or "").strip()
    attribution = str(source_media.get("artist", "") or "").strip()
    authorized = source_media.get("authorized") is True or bool(
        str(source_media.get("authorization", "") or "").strip()
    )
    return bool(license_name and (attribution or authorized))


def source_media_html(markdown: str, page: Page) -> str:
    urls = extract_urls(markdown)
    if not urls:
        return ""
    media_cards: list[str] = []
    source_cards: list[str] = []
    video_re = re.compile(r"\.(?:mp4|webm|mov)(?:\?|$)", re.I)

    source_candidates = PAGE_SOURCE_MEDIA.get(page.key, [])
    for source_media in source_candidates:
        url = source_media.get("url", "")
        label = source_label(url) if url else "来源媒体"
        local_path = source_media.get("path", "")
        source_video = source_media.get("embed") or source_media.get("video", "")
        if local_path and not source_media_has_republication_rights(source_media):
            # Keep the original source URL in the compact source list below,
            # but never expose an unlicensed copied image in the public build.
            local_path = ""
        if local_path and not looks_like_real_photo(OUT / local_path, source_media.get("image_url", "")):
            local_path = ""
        if local_path and len(media_cards) < 8:
            media_cards.append(
                '<article class="media-card">'
                f'<img src="{html.escape(rel_to(OUT / local_path, page.output.parent))}" alt="{html.escape(source_media.get("title") or label)}" width="1200" height="675" loading="lazy">'
                f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(source_media.get("title") or label)}</a>'
                '</article>'
            )
        elif source_video and len(media_cards) < 8:
            media_cards.append(
                '<article class="media-card video-card">'
                f'<iframe src="{html.escape(source_video)}" title="{html.escape(source_media.get("title") or label)}" loading="lazy" allowfullscreen="allowfullscreen" allow="fullscreen; picture-in-picture"></iframe>'
                f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(source_media.get("title") or label)}</a>'
                '</article>'
            )

    for url in urls:
        label = source_label(url)
        embed = bilibili_embed_url(url)
        if embed and len(media_cards) < 6:
            media_cards.append(
                '<article class="media-card video-card">'
                f'<iframe src="{html.escape(embed)}" title="{html.escape(label)}" '
                'loading="lazy" allowfullscreen="allowfullscreen" '
                'allow="fullscreen; picture-in-picture"></iframe>'
                f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(label)}</a>'
                '</article>'
            )
        elif video_re.search(url) and len(media_cards) < 6:
            media_cards.append(
                '<article class="media-card">'
                f'<video src="{html.escape(url)}" controls preload="metadata"></video>'
                f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(label)}</a>'
                '</article>'
            )
        elif len(source_cards) < 12:
            source_cards.append(
                f'<a class="source-link" href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">'
                f'<span>{html.escape(label)}</span><small>{html.escape(urlparse(url).netloc)}</small><b aria-hidden="true">↗</b></a>'
            )

    if not media_cards and not source_cards:
        return ""

    sources_drawer = ""
    if source_cards:
        sources_drawer = (
            '<details class="source-drawer" open>'
            f'<summary>展开来源链接（{len(source_cards)}）</summary>'
            f'<div class="source-grid">{"".join(source_cards)}</div>'
            '</details>'
        )
    source_date = explicit_review_date(page, read_markdown_cached(page))
    source_head = (
        '<div class="source-media-head compact-head">'
        '<p class="eyebrow">Trip Check</p><h2>实用信息与资料来源</h2>'
        f'<p>资料整理日期：{html.escape(source_date)}。门票、开放时间、预约和交通可能变化，请在出行前复核官方信息。</p>'
        '</div>'
    )
    # 没有实拍图时，不占用大版面，只给一个紧凑的资料来源抽屉
    if not media_cards:
        if not source_cards:
            return ""
        return f'<section class="source-media compact" aria-label="实用信息与资料来源">{source_head}{sources_drawer}</section>'
    note = "下列实拍图来自公开平台与官方网页，仅作参考；出行前请以官方信息为准。"
    return (
        '<section class="source-media" aria-label="实拍参考与资料来源">'
        f'{source_head}'
        f'<p class="source-media-note">{html.escape(note)}</p>'
        f'<div class="media-grid">{"".join(media_cards)}</div>'
        f'{sources_drawer}'
        '</section>'
    )


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def mix_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def draw_gradient(draw: ImageDraw.ImageDraw, width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    for y in range(height):
        color = mix_rgb(top, bottom, y / max(height - 1, 1))
        draw.line([(0, y), (width, y)], fill=color)


def draw_pin(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int], scale: float = 1.0) -> None:
    r = int(20 * scale)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=(*color, 230))
    draw.polygon([(x - int(9 * scale), y + int(13 * scale)), (x + int(9 * scale), y + int(13 * scale)), (x, y + int(42 * scale))], fill=(*color, 230))
    draw.ellipse([x - int(7 * scale), y - int(7 * scale), x + int(7 * scale), y + int(7 * scale)], fill=(255, 250, 242, 240))


def draw_city_skyline(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int], key: str, width: int, height: int) -> None:
    base = int(height * 0.76)
    color = mix_rgb(accent, (30, 34, 34), 0.36)
    for i, x in enumerate(range(90, width - 70, 92)):
        block_h = 95 + (i % 5) * 28
        draw.rounded_rectangle([x, base - block_h, x + 62, base], radius=8, fill=(*color, 190))
        for wy in range(base - block_h + 16, base - 14, 24):
            draw.rectangle([x + 15, wy, x + 25, wy + 10], fill=(255, 241, 190, 150))
            draw.rectangle([x + 38, wy, x + 48, wy + 10], fill=(255, 241, 190, 130))
    if key == "zhengzhou":
        cx = int(width * 0.68)
        y = base - 250
        for level in range(5):
            top = y + level * 46
            half = 92 - level * 10
            draw.polygon([(cx - half, top + 36), (cx, top), (cx + half, top + 36)], fill=(*accent, 180))
            draw.rectangle([cx - half + 24, top + 36, cx + half - 24, top + 48], fill=(*color, 210))
    if key == "chongqing":
        y = base - 95
        draw.line([(150, y), (width - 140, y + 26)], fill=(255, 238, 190, 210), width=12)
        for x in range(220, width - 180, 210):
            draw.line([(x, y + 4), (x + 60, y - 90)], fill=(255, 238, 190, 180), width=5)
            draw.line([(x, y + 4), (x + 125, y - 88)], fill=(255, 238, 190, 140), width=4)


def _ridge_points(rng: random.Random, y0: int, lo: int, hi: int, step: int, width: int, bottom: int) -> list[tuple[int, int]]:
    """生成一条随机起伏的山脊多边形（左右贴边、底部闭合）。"""
    pts: list[tuple[int, int]] = [(0, bottom), (0, y0 - rng.randint(0, lo))]
    x = -rng.randint(0, step // 2)
    while x < width:
        x += step + rng.randint(-step // 3, step // 3)
        pts.append((min(max(x, 0), width), y0 - rng.randint(lo, hi)))           # 峰
        x += rng.randint(step // 3, step // 2)
        pts.append((min(max(x, 0), width), y0 - rng.randint(0, max(lo, 1))))    # 谷
    pts.append((width, y0 - rng.randint(0, lo)))
    pts.append((width, bottom))
    return pts


def _karst_hills(draw: ImageDraw.ImageDraw, rng: random.Random, accent: tuple[int, int, int], base: int, width: int) -> None:
    """圆润的喀斯特峰丛（桂林 / 兴义 / 贵阳那种）。"""
    fill = (*mix_rgb(accent, (45, 61, 48), 0.24), 195)
    x = rng.randint(30, 130)
    while x < width - 30:
        w = rng.randint(70, 150)
        h = rng.randint(150, 320)
        draw.rounded_rectangle([x, base - h, x + w, base + 60], radius=w // 2, fill=fill)
        x += w - rng.randint(8, 40)


def draw_mountain_scene(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int], key: str, width: int, height: int) -> None:
    rng = random.Random("scene-" + key)
    base = int(height * 0.77)
    back = mix_rgb(accent, (235, 240, 228), 0.46)
    mid = mix_rgb(accent, (66, 72, 62), 0.22)
    front = mix_rgb(accent, (39, 54, 45), 0.35)
    variant = rng.choice(["peaks", "peaks", "karst", "rolling", "lake"])
    if key in {"xingyi", "guiyang", "guilin", "hezhou", "laibin", "chongzuo", "qiannan"}:
        variant = "karst"
    if key in {"lijiang", "ganzi", "aba", "shangrila", "nyingchi"}:
        variant = "peaks"
    if variant == "rolling":
        amp = [(40, 150), (50, 180), (40, 150)]
    elif variant == "karst":
        amp = [(90, 250), (60, 200), (40, 150)]
    else:
        amp = [(130, 320), (95, 270), (70, 200)]
    draw.polygon(_ridge_points(rng, base - 40, *amp[0], 230, width, base), fill=(*back, 210))
    draw.polygon(_ridge_points(rng, base + 20, *amp[1], 250, width, base + 95), fill=(*mid, 215))
    if variant == "karst":
        _karst_hills(draw, rng, accent, base + 30, width)
    else:
        draw.polygon(_ridge_points(rng, base + 50, *amp[2], 300, width, height), fill=(*front, 220))
    if variant == "lake":
        ly = base + rng.randint(20, 70)
        draw.ellipse([rng.randint(-120, 160), ly, width - rng.randint(-120, 160), height + 40], fill=(92, 161, 190, 120))
        draw.line([(0, ly + 6), (width, ly + 6)], fill=(255, 255, 255, 90), width=5)
    if key == "lijiang":
        px = rng.randint(int(width * 0.42), int(width * 0.58))
        peak = (px, base - 330)
        draw.polygon([(px - 185, base - 66), peak, (px + 195, base - 70)], fill=(236, 246, 250, 235))
        draw.polygon([peak, (px - 70, base - 140), (px + 70, base - 120)], fill=(255, 255, 255, 245))


def draw_hero_asset(page: Page) -> Path:
    path = IMAGES / f"{page.key}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1280, 720
    # 优先用抓到的真实城市照片；抓不到再画多样化插画。
    photo_path, photo_meta = city_photo_for(page)
    if photo_path:
        # 已发布的封面本身就是版本库内的可复现照片衍生物。缓存指向它时
        # 不要把文件作为自己的输入再次 JPEG 压缩；新抓取的原图则只在
        # 首次生成时转成发布封面，并立即把缓存切换到该受版本控制的路径。
        if photo_path.resolve() == path.resolve():
            return path
        if save_cover_image(photo_path, path, (width, height)):
            if photo_meta:
                photo_meta["path"] = rel_to(path, OUT)
                PHOTO_CACHE[f"cityphoto|{page.key}"] = photo_meta
                save_photo_cache()
            return path
    accent = hex_to_rgb(page.accent)
    top = mix_rgb((255, 248, 235), accent, 0.06)
    bottom = mix_rgb((225, 238, 236), accent, 0.14)
    image = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(image, "RGBA")
    draw_gradient(draw, width, height, top, bottom)
    sky_rng = random.Random("sky-" + page.key)
    # 太阳 / 月亮：位置左右、大小、冷暖随城市变化
    sun_r = sky_rng.randint(78, 120)
    sun_cx = sky_rng.choice([sky_rng.randint(230, 430), sky_rng.randint(width - 430, width - 230)])
    sun_cy = sky_rng.randint(120, 220)
    sun_fill = sky_rng.choice([(255, 219, 137, 210), (255, 205, 120, 215), (236, 244, 250, 200), (255, 228, 170, 205)])
    draw.ellipse([sun_cx - sun_r, sun_cy - sun_r, sun_cx + sun_r, sun_cy + sun_r], fill=sun_fill)
    # 漂浮的云
    for _ in range(sky_rng.randint(1, 3)):
        cx = sky_rng.randint(120, width - 320)
        cy = sky_rng.randint(80, 300)
        cw = sky_rng.randint(220, 360)
        draw.ellipse([cx, cy, cx + cw, cy + cw * 0.4], fill=(*mix_rgb(accent, (255, 255, 255), 0.72), 60))
    draw.rectangle([0, int(height * 0.70), width, height], fill=(*mix_rgb(accent, (238, 228, 206), 0.70), 170))

    if page.key in {"record", "zhengzhou", "chengdu", "chongqing"}:
        draw_city_skyline(draw, accent, page.key, width, height)
    else:
        draw_mountain_scene(draw, accent, page.key, width, height)

    river_color = mix_rgb((78, 154, 180), accent, 0.25)
    river = [(0, 790), (220, 735), (420, 765), (650, 720), (890, 758), (1140, 710), (1600, 744)]
    draw.line(river, fill=(*river_color, 155), width=72, joint="curve")
    draw.line(river, fill=(255, 255, 255, 100), width=8)

    if page.key == "dali":
        draw.ellipse([410, 545, 1180, 835], fill=(92, 161, 190, 125))
    if page.key == "kunming":
        flower_colors = [(235, 91, 115), (246, 174, 72), (128, 174, 88), (135, 106, 190)]
        for idx, x in enumerate(range(170, width - 130, 115)):
            y = 595 + (idx % 4) * 35
            c = flower_colors[idx % len(flower_colors)]
            for dx, dy in [(0, -12), (12, 0), (0, 12), (-12, 0)]:
                draw.ellipse([x + dx - 10, y + dy - 10, x + dx + 10, y + dy + 10], fill=(*c, 210))
            draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 236, 145, 230))
    if page.key == "record":
        points = [(300, 530), (525, 410), (760, 520), (980, 390), (1240, 500)]
        draw.line(points, fill=(*accent, 180), width=9)
        for x, y in points:
            draw_pin(draw, x, y, accent, 1.15)

    for _ in range(sky_rng.randint(3, 5)):
        x = sky_rng.randint(120, width - 120)
        y = sky_rng.randint(int(height * 0.5), int(height * 0.78))
        r = sky_rng.randint(24, 70)
        draw.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, 110), width=4)
    image.save(path, "JPEG", quality=84, optimize=True, progressive=True)
    return path


def ensure_body_gallery(page: Page) -> None:
    """Create one distinct, mobile-ready local derivative from the city cover."""
    if page.key == "record":
        return
    source = IMAGES / f"{page.key}.jpg"
    if not source.exists():
        return
    target = PHOTOS / page.key
    target.mkdir(parents=True, exist_ok=True)
    output_path = target / "scenery-01.jpg"
    for stale in target.glob("scenery-[0-9][0-9].jpg"):
        if stale != output_path:
            stale.unlink()
    with Image.open(source) as image:
        image = image.convert("RGB")
        output = ImageOps.fit(image, (960, 540), method=Image.Resampling.LANCZOS)
        output.save(output_path, "JPEG", quality=76, optimize=True, progressive=True)


def reinforcement_appendix(page: Page, markdown: str) -> str:
    """Add an execution-oriented city brief when the source guide is still short."""
    if page.key in HUB_KEYS or len(markdown) >= 4000:
        return ""
    profile = city_profile(page)
    city = profile["city"]
    highlights = profile["highlights"][:4] or ["核心景点", "城市街区"]
    foods = profile["foods"][:4] or ["本地早餐", "夜市小吃"]
    routes = profile["routes"][:3] or ["经典片区线", "雨天备选线"]
    sights = "、".join(highlights)
    food_list = "、".join(foods)
    route_list = "、".join(routes)
    return f"""

## 行程执行补强

### 到达后先做什么
- 抵达 {city} 后先确认当日天气、景区入园时间和返程末班；把 {sights} 按地理方向拆开，不以地图直线距离代替实际通行时间。
- 第一天只安排一个核心片区：入住、寄存行李、熟悉周边吃喝与停车/换乘点后再进景区。这样即使遇到排队、降雨或临时限流，也能保住当天的主要体验。
- 需要跨区的行程，出发前在官方入口与地图中分别核对一次。导航显示的时间不包含排队、观光车、索道、找车位和步行回程，应额外预留缓冲。

### 分区与动线
- 核心游览：优先把 {highlights[0]} 作为半天或一天的主任务；其余 {"、".join(highlights[1:])} 只在同方向、体力和开放时间允许时加入。
- 城市休整：午餐、雨天与傍晚留给市区街区、展馆或商圈；不要为了打卡在中午往返远郊。需要夜游时，先确认最后一班公共交通、停车场关闭时间和打车供给。
- 远郊选择：若只住一晚，宁可减少一个景点，也不要把远郊和市区夜游排进同一日。自驾以返回住宿地前仍留有充足精力为底线，山路、雨雾和节假日要再收紧计划。

### 餐饮与补给
- 这座城市可优先从 {food_list} 中选一到两样作为正餐，再用同片区的小吃补充；同一天不要跨城寻找网红店。
- 早餐适合安排在住宿周边或菜市场一带，午餐以靠近主景区为先，晚餐再回到夜间活动片区。热门店排队超过预留时间时，直接选择相邻街区的同类店，行程体验通常更稳定。
- 购买伴手礼时先看生产日期、常温保存和携带限制；自驾可放在返程前采购，公共交通出行则优先轻量、耐压的包装。

### 路线落地模板
- 半天：{highlights[0]} + 同片区散步/展馆 + {foods[0]}。适合早到、转场或天气不稳定的日子。
- 一天：上午 {highlights[0]}，午后在 {highlights[min(1, len(highlights) - 1)]} 或市区人文点二选一，傍晚安排 {foods[min(1, len(foods) - 1)]}。每个节点之间留出交通与休息时间。
- 两天：第一天完成城市核心与夜间街区，第二天只选择一条远郊或自然线；可从现有攻略中的 {route_list} 里选与住宿方向一致的一条。
- 雨天：优先博物馆、室内展馆、商场和老街，把需要视野、步道或水上项目的景点挪到天气恢复后；门票改签与景区公告以官方页面为准。

### 预算、停车与安全边界
- 预算按住宿、交通/油费、门票、餐饮和机动金五项拆分。门票、停车、观光车、索道、演出和游船常为独立项目，提交行程前逐项核验，避免把“景区门票”理解为全部费用。
- 自驾抵达景区前保存停车场位置、收费规则和出口方向；节假日不要依赖最后一个停车场。纯电或插混车辆应在进入远郊前完成补能，并保留一处备选充电点。
- 夜间、山地、海边、峡谷与涉水项目要服从天气预警和现场管制。遇到大风、雷雨、能见度低或道路封闭时，立即切换到市区备选，不追赶原计划。

### 出发前最后核验
- 核对 {sights} 的开放日期、预约入口、实名要求、临时闭园和分时段入园规则。
- 核对住宿到第一站的实际通行时间、停车/换乘、返程末班，以及第二天是否需要提前退房或寄存行李。
- 核对天气预警、道路施工、节假日客流和活动公告；易变项目以城市页末尾来源链接及官方当天公告为准。
"""


def guide_gallery_html(page: Page) -> str:
    if page.key in HUB_KEYS:
        return ""
    photo = PHOTOS / page.key / "scenery-01.jpg"
    if not photo.exists():
        return ""
    city = city_profile(page)["city"]
    cards = (
        '<article class="media-card"><img src="' + html.escape(rel_to(photo, page.output.parent)) +
        '" alt="' + html.escape(f"{city} 正文配图") + '" width="960" height="540" loading="lazy"></article>'
    )
    return '<section class="source-media guide-gallery"><div class="source-media-head compact-head"><p class="eyebrow">Visual Notes</p><h2>正文配图</h2><p>图片为本站本地保存的城市封面衍生构图，用于辅助浏览；授权与来源沿用该城市封面信息。</p></div><div class="media-grid">' + cards + '</div></section>'


PRIMARY_NAV = (
    ("home", "首页", "index.html", "home"),
    ("destinations", "目的地", "destinations.html", "compass"),
    ("themes", "主题玩法", "themes.html", "layers"),
    ("cities", "城市攻略", "city-guides.html", "book"),
    ("plan", "行程计划", "plan.html", "calendar"),
    ("roadtrip", "自驾路书", "roadtrip.html", "car"),
)
# 抽屉菜单比顶栏多放两项，手机上所有入口都能找到。
DRAWER_NAV = PRIMARY_NAV + (("tools", "实用工具", "tools.html", "tool"),)


def site_header_html(page: Page, active_key: str = "") -> str:
    base = page.output.parent
    home = rel_to(OUT / "index.html", base)
    user = rel_to(OUT / "user.html", base)
    destinations = rel_to(OUT / "destinations.html", base)
    links = "".join(
        f'<a class="header-link{" active" if key == active_key else ""}" href="{html.escape(rel_to(OUT / href, base))}"'
        f'{" aria-current=\"page\"" if key == active_key else ""}>{label}</a>'
        for key, label, href, _ in PRIMARY_NAV
    )
    user_active = " active" if active_key == "user" else ""
    mobile_links = "".join(
        f'<a class="header-link{" active" if key == active_key else ""}" href="{html.escape(rel_to(OUT / href, base))}">'
        f'{icon(icon_name)}<span>{label}</span></a>'
        for key, label, href, icon_name in DRAWER_NAV
    ) + f'<a class="header-link{user_active}" href="{user}">{icon("user")}<span>用户中心</span></a>'
    return f"""  <header class="site-header">
    <div class="header-bar">
      <a class="header-home" href="{home}" aria-label="游记地图首页"><span class="brand-mark" aria-hidden="true">游</span><span class="brand-name">游记<b>地图</b></span></a>
      <nav class="header-links" aria-label="功能导航">{links}</nav>
      <div class="global-search">
        <label class="global-search-box">
          <span class="sr-only">全站搜索</span>
          {icon("search", "icon search-icon")}
          <input id="siteSearch" type="search" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="siteSearchResults" placeholder="搜索城市、景点、美食、季节">
        </label>
        <div class="site-search-results" id="siteSearchResults" hidden>
          <div class="site-search-recent" id="siteSearchRecent" aria-label="最近搜索与浏览" hidden></div>
          <div class="site-search-options" id="siteSearchOptions" role="listbox" aria-label="城市与攻略搜索建议"></div>
        </div>
      </div>
      <button class="nav-toggle" id="navToggle" type="button" aria-expanded="false" aria-controls="topNav" aria-label="打开城市导航菜单">{icon("menu", "icon nav-open-icon")}{icon("close", "icon nav-close-icon")}<span class="nav-toggle-text">选城市</span></button>
      {trip_toggle_html()}
      <a class="header-user{user_active}" href="{user}" aria-label="用户中心">
        <span class="user-avatar" id="headerAvatar" aria-hidden="true">👤</span>
        <span class="header-user-name" id="headerUserName">我的</span>
      </a>
    </div>
    <nav class="top-nav" id="topNav" aria-label="城市导航">
      <div class="top-nav-inner">
        <div class="mobile-primary-nav" aria-label="移动端功能导航">{mobile_links}</div>
        <div class="top-nav-head">
          <div><strong>按省份选城市</strong><span>点开省份查看城市；想按季节、天数筛选可去目的地页。</span></div>
          <a class="top-nav-all" href="{destinations}">全部目的地 {icon("arrow")}</a>
        </div>
        {nav_html(page)}
      </div>
    </nav>
  </header>"""


def mobile_tabbar_html(page: Page, active_key: str) -> str:
    base = page.output.parent
    tabs = (
        ("home", "首页", "index.html", "home"),
        ("destinations", "目的地", "destinations.html", "compass"),
        ("plan", "行程", "plan.html", "calendar"),
        ("roadtrip", "自驾", "roadtrip.html", "car"),
    )
    links = "".join(
        f'<a class="tab{" active" if key == active_key else ""}" href="{html.escape(rel_to(OUT / href, base))}"'
        f'{" aria-current=\"page\"" if key == active_key else ""}>{icon(icon_name)}<span>{label}</span></a>'
        for key, label, href, icon_name in tabs
    )
    user_href = rel_to(OUT / "user.html", base)
    return (
        '  <nav class="mobile-tabbar" aria-label="移动端主导航">'
        f'{links}'
        f'<a class="tab{" active" if active_key == "user" else ""}" href="{html.escape(user_href)}">{icon("user")}<span>我的</span></a>'
        '</nav>'
    )




AUTHOR_SECTION_HEADINGS = (
    "使用说明",
    "批量新增城市索引",
    "第二批新增城市索引（50+）",
    "第三批新增城市索引（更多城市）",
)


def strip_author_sections(markdown: str) -> str:
    """移除面向作者的构建日志章节，使首页正文只剩对游客有用的内容。"""
    out: list[str] = []
    skip = False
    for line in markdown.splitlines():
        if line.startswith("## "):
            skip = line[3:].strip() in AUTHOR_SECTION_HEADINGS
        if not skip:
            out.append(line)
    return "\n".join(out)


# 这些来源类章节会和底部「资料来源」抽屉重复，正文里剥离，只在底部统一展示（可点击）。
SOURCE_SECTION_HEADINGS = ("来源参考", "参考来源", "资料来源", "来源链接", "参考资料")


def strip_sections(markdown: str, headings: tuple[str, ...]) -> str:
    out: list[str] = []
    skip = False
    for line in markdown.splitlines():
        m = re.match(r"^(#{2,3})\s+(.+)$", line)
        if m:
            skip = m.group(2).strip() in headings
        if not skip:
            out.append(line)
    return "\n".join(out)


def extract_changelog_html() -> str:
    """从 记录.md 的作者向章节提取更新说明，供用户中心展示。"""
    try:
        md = (RECORD_SOURCE).read_text(encoding="utf-8")
    except OSError:
        return "<p>暂无更新说明。</p>"
    blocks: list[tuple[str, list[str]]] = []
    cur: str | None = None
    for line in md.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            cur = heading if heading in AUTHOR_SECTION_HEADINGS else None
            if cur:
                blocks.append((cur, []))
            continue
        if cur and line.strip().startswith("- "):
            blocks[-1][1].append(line.strip()[2:].strip())
    parts = []
    for heading, bullets in blocks:
        if not bullets:
            continue
        items = "".join(f"<li>{inline_markup(strip_html(b))}</li>" for b in bullets)
        parts.append(f'<div class="changelog-block"><h3>{html.escape(heading)}</h3><ul>{items}</ul></div>')
    return "".join(parts) or "<p>暂无更新说明。</p>"


def footer_html(page: Page) -> str:
    base = page.output.parent

    def href(name: str) -> str:
        return html.escape(rel_to(OUT / name, base))

    city_count = sum(1 for item in PAGES if item.key not in HUB_KEYS)
    return f"""  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <a class="header-home" href="{href("index.html")}"><span class="brand-mark" aria-hidden="true">游</span><span class="brand-name">游记<b>地图</b></span></a>
        <p>个人整理的全国城市旅游攻略，收录 {city_count} 座城市的景点、美食、季节与路线。运行期纯静态，可安装到手机离线阅读。</p>
      </div>
      <nav class="footer-links" aria-label="浏览攻略"><strong>浏览</strong><a href="{href("destinations.html")}">目的地筛选</a><a href="{href("themes.html")}">主题玩法</a><a href="{href("city-guides.html")}">城市攻略</a><a href="{href("overview.html")}">跨城市总览</a></nav>
      <nav class="footer-links" aria-label="旅行工具"><strong>工具</strong><a href="{href("plan.html")}">行程计划</a><a href="{href("roadtrip.html")}">自驾路书</a><a href="{href("tools.html")}">实用工具</a><a href="{href("user.html")}">用户中心</a></nav>
      <div class="footer-note">
        <strong>资料说明</strong>
        <p>内容来自公开资料的归纳，仅供出行参考；门票、开放时间与预约请以官方景区、本地文旅和票务系统为准。</p>
        <p>城市与景点照片来自 <a href="https://commons.wikimedia.org/" target="_blank" rel="noreferrer">Wikimedia Commons</a> 等开放图库，遵循各自 CC 授权。</p>
      </div>
    </div>
    <p class="footer-copy">游记地图 · 收藏、行程与笔记只保存在你的浏览器</p>
  </footer>"""


SETTINGS_BOOT_SCRIPT = (
    '<script>try{var s=JSON.parse(localStorage.getItem("tay_settings")||"{}"),r=document.documentElement;'
    'if(s.vibrancy)r.setAttribute("data-vibrancy",s.vibrancy);if(s.font)r.setAttribute("data-font",s.font);'
    'if(s.motion)r.setAttribute("data-motion",s.motion);var t=s.theme||"auto";'
    'if(t==="auto")t=(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches)?"dark":"light";'
    'r.setAttribute("data-theme",t);}catch(e){}</script>'
)


def document_html(
    page: Page,
    title: str,
    main_html: str,
    active_key: str,
    *,
    page_kind: str,
    og_image: Path | None = None,
    extra_head: str = "",
    extra_scripts: str = "",
    body_style: str = "",
) -> str:
    """Shared page shell: metadata, header, footer, mobile tab bar and scripts."""
    base = page.output.parent
    site_root = rel_to(OUT, base)
    vite_head, vite_script = vite_asset_tags(base)
    image = og_image if og_image and og_image.exists() else ASSETS / "icon-512.png"
    style = f"--accent:{page.accent}" + (f"; {body_style}" if body_style else "")
    return "\n".join(line.rstrip() for line in f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(page.subtitle)}">
  <meta name="theme-color" content="{page.accent}">
  <link rel="canonical" href="{html.escape(public_page_url(page.output))}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(page.subtitle)}">
  <meta property="og:url" content="{html.escape(public_page_url(page.output))}">
  <meta property="og:site_name" content="游记地图">
  <meta property="og:locale" content="zh_CN">
  <meta property="og:image" content="{html.escape(public_page_url(image))}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="manifest" href="{rel_to(OUT / 'manifest.webmanifest', base)}">
  <link rel="icon" href="{rel_to(ASSETS / 'icon-192.png', base)}" type="image/png">
  <link rel="apple-touch-icon" href="{rel_to(ASSETS / 'icon-180.png', base)}">
  <link rel="stylesheet" href="{asset_href(ASSETS / 'travel.css', base)}">
{vite_head}
{extra_head}
  <noscript><style>.reveal{{opacity:1!important;transform:none!important}}</style></noscript>
  {SETTINGS_BOOT_SCRIPT}
</head>
<body id="top" data-page="{page_kind}" data-site-root="{html.escape(site_root)}" data-search-index="{asset_href(ASSETS / 'search-index.js', base)}" style="{html.escape(style)}">
  <a class="skip-link" href="#mainContent">跳到主要内容</a>
{site_header_html(page, active_key)}
  <main id="mainContent" tabindex="-1">
{main_html}
  </main>
{footer_html(page)}
{mobile_tabbar_html(page, active_key)}
{trip_workspace_html(page)}
  <button class="to-top" id="toTop" type="button" aria-label="返回顶部" title="返回顶部">↑</button>
  <script src="{asset_href(ASSETS / 'travel.js', base)}"></script>
{vite_script}
{extra_scripts}
</body>
</html>
""".splitlines()) + "\n"


def shell_page_html(
    page: Page,
    title: str,
    main_html: str,
    active_key: str,
    extra_head: str = "",
    extra_scripts: str = "",
) -> str:
    """通用页壳：用户中心、目录页与自驾路书等非攻略页面。"""
    return document_html(
        page, title, main_html, active_key,
        page_kind=active_key or "app", extra_head=extra_head, extra_scripts=extra_scripts,
    )


def user_center_body() -> str:
    changelog = extract_changelog_html()
    city_count = sum(1 for page in PAGES if page.key != "record")
    region_count = len({
        split_city_filename(page.source)[0]
        for page in PAGES
        if page.key != "record"
    })
    return f"""    <section class="user-hero reveal">
      <div class="user-id-card">
        <button class="user-avatar-big" id="ucAvatar" type="button" aria-label="切换头像">👤</button>
        <div class="user-id-text">
          <p class="eyebrow">User Center</p>
          <h1>你好，<span id="ucNameShow">旅行者</span> 👋</h1>
          <p class="subtitle">收藏城市、整理行程、保存路书，也把清单、预算和旅途笔记放在这里。</p>
        </div>
      </div>
      <div class="user-stat-row" id="ucStatRow">
        <div class="user-stat"><strong id="ucFavCount">0</strong><span>收藏城市</span></div>
        <div class="user-stat"><strong>{city_count}</strong><span>可逛城市</span></div>
        <div class="user-stat"><strong>{region_count}</strong><span>覆盖地区</span></div>
      </div>
    </section>
    <nav class="user-tabs" id="userTabs" role="tablist" aria-label="用户中心导航" aria-orientation="horizontal">
      <button class="user-tab active" id="user-tab-profile" data-tab="profile" type="button" role="tab" aria-selected="true" aria-controls="user-panel-profile" tabindex="0">个人信息</button>
      <button class="user-tab" id="user-tab-favorites" data-tab="favorites" type="button" role="tab" aria-selected="false" aria-controls="user-panel-favorites" tabindex="-1">我的收藏</button>
      <button class="user-tab" id="user-tab-history" data-tab="history" type="button" role="tab" aria-selected="false" aria-controls="user-panel-history" tabindex="-1">最近浏览</button>
      <button class="user-tab" id="user-tab-trip" data-tab="trip" type="button" role="tab" aria-selected="false" aria-controls="user-panel-trip" tabindex="-1">我的行程</button>
      <button class="user-tab" id="user-tab-roadbooks" data-tab="roadbooks" type="button" role="tab" aria-selected="false" aria-controls="user-panel-roadbooks" tabindex="-1">自驾路书</button>
      <button class="user-tab" id="user-tab-tools" data-tab="tools" type="button" role="tab" aria-selected="false" aria-controls="user-panel-tools" tabindex="-1">旅行工具</button>
      <button class="user-tab" id="user-tab-settings" data-tab="settings" type="button" role="tab" aria-selected="false" aria-controls="user-panel-settings" tabindex="-1">设置</button>
      <button class="user-tab" id="user-tab-guide" data-tab="guide" type="button" role="tab" aria-selected="false" aria-controls="user-panel-guide" tabindex="-1">使用介绍</button>
      <button class="user-tab" id="user-tab-changelog" data-tab="changelog" type="button" role="tab" aria-selected="false" aria-controls="user-panel-changelog" tabindex="-1">更新说明</button>
    </nav>
    <div class="user-panels">
      <section class="user-panel guide-section" id="user-panel-profile" data-panel="profile" role="tabpanel" aria-labelledby="user-tab-profile" tabindex="0">
        <h2>个人信息</h2>
        <p class="panel-hint">这些信息只保存在你当前这台设备的浏览器里（localStorage），不会上传到任何服务器。</p>
        <div class="field-row">
          <label for="ucNameInput">昵称</label>
          <input id="ucNameInput" type="text" maxlength="16" placeholder="给自己起个旅行昵称">
        </div>
        <div class="field-row">
          <span class="field-label">选择头像</span>
          <div class="avatar-picker" id="avatarPicker"></div>
        </div>
        <div class="field-row">
          <label for="ucSlogan">旅行签名</label>
          <input id="ucSlogan" type="text" maxlength="40" placeholder="例如：把山河装进相册">
        </div>
        <button id="ucSaveProfile" type="button" class="primary-btn">保存</button>
        <span class="save-tip" id="ucSaveTip" hidden>已保存 ✓</span>
      </section>
      <section class="user-panel guide-section" id="user-panel-favorites" data-panel="favorites" role="tabpanel" aria-labelledby="user-tab-favorites" tabindex="0" hidden>
        <h2>我的收藏</h2>
        <p class="panel-hint">在任意城市卡片右上角点 ☆ 即可收藏，这里集中管理。</p>
        <div class="fav-grid" id="favGrid"></div>
        <div class="fav-empty" id="favEmpty">还没有收藏城市。去 <a href="city-guides.html">城市攻略</a> 逛逛，点 ☆ 收藏吧。</div>
      </section>
      <section class="user-panel guide-section" id="user-panel-history" data-panel="history" data-storage-key="tay_recent" role="tabpanel" aria-labelledby="user-tab-history" tabindex="0" hidden>
        <h2>最近浏览</h2>
        <p class="panel-hint">浏览记录只保存在当前浏览器，最多保留最近 12 座城市。</p>
        <div class="fav-grid" id="historyList"></div>
        <div class="fav-empty" id="historyEmpty">还没有浏览记录。去 <a href="city-guides.html">城市攻略</a> 选择第一座城市。</div>
        <button class="ghost-btn" id="historyClear" type="button" hidden>清空浏览记录</button>
      </section>
      <section class="user-panel guide-section" id="user-panel-trip" data-panel="trip" role="tabpanel" aria-labelledby="user-tab-trip" tabindex="0" hidden>
        <h2>我的行程</h2>
        <p class="panel-hint">这里是想去的城市清单：可排序、对比和估算节奏。要把景点排进具体某一天、估算预算和分享，请用 <a href="plan.html">行程计划</a>。</p>
        <div class="trip-tools">
          <label for="tripPlanDays">计划天数</label>
          <input id="tripPlanDays" type="number" min="1" max="60" value="5" inputmode="numeric">
          <button id="tripCompare" type="button" class="ghost-btn" disabled>对比城市</button>
          <button id="tripClear" type="button" class="ghost-btn">清空行程</button>
        </div>
        <div class="trip-summary" id="tripSummary"></div>
        <div class="trip-compare" id="tripCompareTable" hidden></div>
        <ol class="trip-list" id="tripList"></ol>
        <div class="fav-empty" id="tripEmpty">行程还是空的。去 <a href="city-guides.html">城市攻略</a> 点 ＋ 把想去的城市加进来。</div>
      </section>
      <section class="user-panel guide-section" id="user-panel-roadbooks" data-panel="roadbooks" role="tabpanel" aria-labelledby="user-tab-roadbooks" tabindex="0" hidden>
        <h2>已保存的自驾路书</h2>
        <p class="panel-hint">路书只保存在当前浏览器。打开后可以重新计算路线、打印或导出 Markdown。</p>
        <div class="roadbook-list" id="roadbookList"></div>
        <div class="fav-empty" id="roadbookEmpty">还没有保存路书。去 <a href="roadtrip.html">自驾路书生成器</a> 建立第一条路线。</div>
      </section>
      <section class="user-panel guide-section travel-tools-panel" id="user-panel-tools" data-panel="tools" role="tabpanel" aria-labelledby="user-tab-tools" tabindex="0" hidden>
        <header class="user-panel-head">
          <div>
            <p class="eyebrow">Local Toolkit</p>
            <h2>旅行工具</h2>
            <p class="panel-hint">清单、预算和笔记只保存在当前浏览器，不会上传。可随时导出为 Markdown 备份。</p>
          </div>
          <button id="toolsExport" type="button" class="tool-export-btn" title="导出旅行工作台 Markdown" aria-label="导出旅行工作台 Markdown">↓ 导出</button>
        </header>
        <div class="travel-tool-layout">
          <section class="tool-workspace checklist-workspace" aria-labelledby="checklistTitle">
            <div class="tool-workspace-head">
              <div><span class="tool-symbol checklist-symbol" aria-hidden="true">✓</span><h3 id="checklistTitle">出行清单</h3></div>
              <strong id="checklistProgress">0 / 0</strong>
            </div>
            <form id="checklistForm" class="tool-inline-form">
              <label class="sr-only" for="checklistInput">新增清单事项</label>
              <input id="checklistInput" type="text" maxlength="80" autocomplete="off" placeholder="例如：身份证、充电器、防晒">
              <button id="checklistAdd" class="square-action" type="submit" title="添加清单事项" aria-label="添加清单事项">＋</button>
            </form>
            <ul class="checklist-list" id="travelChecklist"></ul>
            <p class="tool-empty" id="checklistEmpty">还没有事项，从证件、衣物或预约核验开始。</p>
          </section>
          <section class="tool-workspace budget-workspace" aria-labelledby="budgetTitle">
            <div class="tool-workspace-head">
              <div><span class="tool-symbol budget-symbol" aria-hidden="true">¥</span><h3 id="budgetTitle">预算记录</h3></div>
              <strong id="budgetTotal">¥0.00</strong>
            </div>
            <form id="budgetForm" class="budget-form">
              <label class="sr-only" for="budgetName">预算项目</label>
              <input id="budgetName" type="text" maxlength="60" autocomplete="off" placeholder="项目，例如：高铁票">
              <label class="sr-only" for="budgetCategory">预算分类</label>
              <select id="budgetCategory">
                <option value="交通">交通</option><option value="住宿">住宿</option><option value="餐饮">餐饮</option>
                <option value="门票">门票</option><option value="购物">购物</option><option value="其他">其他</option>
              </select>
              <label class="sr-only" for="budgetAmount">预算金额</label>
              <input id="budgetAmount" type="number" min="0.01" max="999999" step="0.01" inputmode="decimal" placeholder="金额">
              <button id="budgetAdd" class="square-action" type="submit" title="添加预算项目" aria-label="添加预算项目">＋</button>
            </form>
            <ul class="budget-list" id="budgetList"></ul>
            <p class="tool-empty" id="budgetEmpty">还没有预算项目。金额仅用于个人规划，不提供站内消费。</p>
          </section>
          <section class="tool-workspace notes-workspace" aria-labelledby="notesTitle">
            <div class="tool-workspace-head">
              <div><span class="tool-symbol notes-symbol" aria-hidden="true">✎</span><h3 id="notesTitle">旅行笔记</h3></div>
              <span class="autosave-status" id="notesSaveStatus">自动保存在本机</span>
            </div>
            <label class="sr-only" for="travelNotes">旅行笔记内容</label>
            <textarea id="travelNotes" rows="8" maxlength="12000" placeholder="记录想去的地方、预约信息、路线想法和旅途中发生的事……"></textarea>
          </section>
        </div>
      </section>
      <section class="user-panel guide-section" id="user-panel-settings" data-panel="settings" role="tabpanel" aria-labelledby="user-tab-settings" tabindex="0" hidden>
        <h2>设置</h2>
        <p class="panel-hint">偏好设置同样只保存在本地浏览器。</p>
        <div class="setting-row">
          <div><strong>界面主题</strong><small>浅色明快，深色护眼夜读</small></div>
          <div class="seg" id="setTheme">
            <button data-val="auto" type="button" class="active">跟随系统</button>
            <button data-val="light" type="button">浅色</button>
            <button data-val="dark" type="button">深色</button>
          </div>
        </div>
        <div class="setting-row">
          <div><strong>配色活力度</strong><small>调高更鲜艳活泼，调低更素雅护眼</small></div>
          <div class="seg" id="setVibrancy">
            <button data-val="calm" type="button">素雅</button>
            <button data-val="normal" type="button" class="active">标准</button>
            <button data-val="vivid" type="button">鲜活</button>
          </div>
        </div>
        <div class="setting-row">
          <div><strong>正文字号</strong><small>适配不同阅读习惯</small></div>
          <div class="seg" id="setFont">
            <button data-val="s" type="button">小</button>
            <button data-val="m" type="button" class="active">中</button>
            <button data-val="l" type="button">大</button>
          </div>
        </div>
        <div class="setting-row">
          <div><strong>动效</strong><small>关闭后减少滚动渐入与轮播动画</small></div>
          <div class="seg" id="setMotion">
            <button data-val="on" type="button" class="active">开启</button>
            <button data-val="off" type="button">关闭</button>
          </div>
        </div>
        <button id="ucResetAll" type="button" class="ghost-btn">清除本地数据</button>
        <div class="storage-transfer" aria-label="本机数据备份与恢复">
          <strong>本机数据备份</strong>
          <p>将收藏、行程、路书、清单、预算、笔记和偏好导出为 JSON；文件只保存在你的设备上。</p>
          <div class="storage-transfer-actions">
            <button id="dataExport" type="button" class="ghost-btn">↓ 导出 JSON</button>
            <label class="file-btn" for="dataImport">↑ 导入 JSON<input id="dataImport" type="file" accept="application/json,.json" hidden></label>
          </div>
          <p id="dataTransferStatus" class="save-tip" role="status" aria-live="polite" hidden></p>
        </div>
      </section>
      <section class="user-panel guide-section" id="user-panel-guide" data-panel="guide" role="tabpanel" aria-labelledby="user-tab-guide" tabindex="0" hidden>
        <h2>使用介绍</h2>
        <div class="guide-grid">
          <div class="guide-item"><span class="gi-emoji">🔍</span><div><strong>全站搜索</strong><p>顶部搜索框可查城市、景点、美食、季节，支持 ↑↓ 键选择、回车跳转。</p></div></div>
          <div class="guide-item"><span class="gi-emoji">📍</span><div><strong>快速查找</strong><p>首页大图下方的「景点 / 吃喝 / 路线 / 避坑」可一键跳到对应攻略板块。</p></div></div>
          <div class="guide-item"><span class="gi-emoji">🧭</span><div><strong>主题玩法</strong><p>按雪山、赏花、喀斯特、古镇、夜市等兴趣，自动筛选合适城市。</p></div></div>
          <div class="guide-item"><span class="gi-emoji">🛠️</span><div><strong>实用工具</strong><p>行程节奏速算、月份适宜速查、打包清单生成，帮你更快做决定。</p></div></div>
          <div class="guide-item"><span class="gi-emoji">🗂️</span><div><strong>城市快速筛选</strong><p>按省份与关键词定位攻略；点 🎲 随机一座发现新去处。</p></div></div>
          <div class="guide-item"><span class="gi-emoji">⭐</span><div><strong>收藏与个人中心</strong><p>收藏喜欢的城市，在这里集中查看；昵称、头像、配色都可自定义。</p></div></div>
          <div class="guide-item"><span class="gi-emoji">🚗</span><div><strong>自驾路书</strong><p>保存生成的逐日路线、预算与风险清单，并可再次打开或导出。</p></div></div>
        </div>
      </section>
      <section class="user-panel guide-section" id="user-panel-changelog" data-panel="changelog" role="tabpanel" aria-labelledby="user-tab-changelog" tabindex="0" hidden>
        <h2>更新说明</h2>
        <p class="panel-hint">本站的内容归并与城市扩充记录。</p>
        {changelog}
      </section>
    </div>"""


def build_user_page() -> None:
    page = Page(RECORD_SOURCE, OUT / "user.html", "user", "用户中心 · 游记地图",
                "个人信息、收藏、设置与说明", "#0e9e8e", "")
    page.output.write_text(shell_page_html(page, "用户中心 · 游记地图", user_center_body(), "user"), encoding="utf-8")


def catalog_masthead(eyebrow: str, title: str, subtitle: str, facts: list[tuple[str, str]]) -> str:
    facts_html = "".join(
        f'<div><strong>{html.escape(value)}</strong><span>{html.escape(label)}</span></div>'
        for value, label in facts
    )
    return (
        '<section class="catalog-masthead reveal">'
        '<div><p class="eyebrow">' + html.escape(eyebrow) + '</p>'
        '<h1>' + html.escape(title) + '</h1><p>' + html.escape(subtitle) + '</p></div>'
        '<div class="catalog-facts">' + facts_html + '</div></section>'
    )


def build_catalog_pages() -> None:
    city_count = len([page for page in PAGES if page.key != "record"])
    province_count = len({city_profile(page)["province"] for page in PAGES if page.key != "record"})
    pages = [
        (
            Page(RECORD_SOURCE, OUT / "destinations.html", "destinations", "目的地 · 游记地图",
                 "按地区、季节、天数、主题和交通方式挑选下一站。", "#19756e", ""),
            "Destinations", "从条件开始，找到下一座城市", "按地区、季节、天数、主题和交通方式组合筛选；结果直接对应可收藏、可加入行程的完整城市攻略。",
            [(str(city_count), "座城市攻略"), (str(province_count), "个地区覆盖")],
            lambda page: home_finder_html(page) + city_explorer_html(page),
        ),
        (
            Page(RECORD_SOURCE, OUT / "themes.html", "themes", "主题玩法 · 游记地图",
                 "从旅行偏好出发，找到值得专程前往的城市。", "#b96733", ""),
            "Travel Themes", "用一份兴趣清单，决定一段旅程", "亲子、博物馆、山水、历史、美食、避暑、冬季与周末短途均可直接筛选；每个结果都保留到城市攻略的入口。",
            [("8", "种旅行主题"), (str(city_count), "座可筛选城市")],
            lambda page: home_themes_html() + city_explorer_html(page),
        ),
        (
            Page(RECORD_SOURCE, OUT / "city-guides.html", "cities", "城市攻略 · 游记地图",
                 "用关键词、省份和随机发现快速进入可执行的城市攻略。", "#295f89", ""),
            "City Guides", "全国城市攻略，按你的方式找", "每张卡片都包含季节、重点景点与代表美食，并支持收藏、加入行程和随机发现。",
            [(str(city_count), "座城市攻略"), ("本地保存", "收藏与行程")],
            lambda page: city_explorer_html(page),
        ),
        (
            Page(RECORD_SOURCE, OUT / "tools.html", "tools", "实用工具 · 游记地图",
                 "把行程节奏、季节选择和出行准备变成可执行的小决定。", "#85662b", ""),
            "Travel Toolkit", "出发前，把关键决定做清楚", "这些工具不涉及购买或支付。个人数据仅保存在当前浏览器，也可以在用户中心统一管理。",
            [("离线可用", "本机浏览器保存"), ("0", "站内消费入口")],
            lambda page: home_tools_html(),
        ),
    ]
    for page, eyebrow, title, subtitle, facts, body_builder in pages:
        main = catalog_masthead(eyebrow, title, subtitle, facts) + body_builder(page)
        page.output.write_text(shell_page_html(page, page.title, main, page.key), encoding="utf-8")


def build_seo_files() -> None:
    """Emit deployment metadata from the same page inventory as the generator."""
    paths = {page.output for page in PAGES}
    paths.update(OUT / name for name in ("overview.html", "plan.html", "destinations.html", "themes.html", "city-guides.html", "tools.html", "user.html", "roadtrip.html"))
    urls = sorted({public_page_url(path) for path in paths})
    entries = "".join(f"  <url><loc>{html.escape(url)}</loc></url>\n" for url in urls)
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n"
    )
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {public_page_url(OUT / 'sitemap.xml')}\n",
        encoding="utf-8",
    )


def estimate_ticket_price(markdown: str) -> int:
    """从已标注的门票/票价文字提取保守的人均参考值；无明确数字时返回 0。"""
    values: list[int] = []
    for match in re.finditer(r"(?:门票|票价|成人票)[^\d]{0,18}[¥￥]?\s*(\d{1,4})(?:\.\d+)?", markdown):
        value = int(match.group(1))
        if 0 < value <= 500 and value not in values:
            values.append(value)
        if len(values) >= 3:
            break
    return min(1000, sum(values))


def roadtrip_city_data() -> list[dict]:
    rows: list[dict] = []
    for page in PAGES[1:]:
        markdown = page.source.read_text(encoding="utf-8")
        profile = city_profile(page)
        rows.append({
            "key": page.key,
            "province": profile["province"],
            "city": profile["city"],
            "title": profile["title"],
            "subtitle": profile["subtitle"],
            "href": f"cities/{page.output.name}",
            "image": f"assets/images/{page.key}.jpg",
            "highlights": profile["highlights"][:6],
            "foods": profile["foods"][:6],
            "routes": profile["routes"][:6],
            "ticketEstimate": estimate_ticket_price(markdown),
            "sources": extract_urls(markdown)[:8],
            "updatedAt": explicit_review_date(page, markdown),
        })
    return rows


def roadtrip_data_js() -> str:
    payload = json.dumps(roadtrip_city_data(), ensure_ascii=False, separators=(",", ":"))
    return f"window.TRAVEL_ROADTRIP_CITIES = {payload};\n"


def roadtrip_body() -> str:
    masthead = catalog_masthead(
        "Roadbook Studio",
        "自驾路书生成器",
        "输入起点和目的地，得到可以实际执行的逐日路线、时间安排、参考预算与风险清单；不提供站内交易。",
        [("离线可用", "无地图也能生成"), ("路线与预算", "分天规划与风险提醒")],
    )
    return masthead + """    <section class="roadtrip-page">
      <div class="rt-workbench">
        <aside class="rt-planner-panel">
          <div class="rt-panel-head"><p class="eyebrow">Plan</p><h2>行程条件</h2><p>地图未配置时使用离线估算，配置后自动切换真实路网。</p></div>
          <form class="rt-form" id="roadtripForm">
            <ol class="rt-stepper" aria-label="路书生成步骤">
              <li><button type="button" data-rt-step-target="1" aria-current="step"><span>01</span>路线</button></li>
              <li><button type="button" data-rt-step-target="2"><span>02</span>偏好</button></li>
              <li><button type="button" data-rt-step-target="3"><span>03</span>费用</button></li>
            </ol>
            <fieldset class="rt-step" data-rt-step="1">
              <legend><span>01</span>路线与日期</legend>
              <div class="rt-field-grid">
                <label class="rt-field"><span>出发地</span><input id="rtOrigin" list="rtCityList" autocomplete="off" placeholder="例如：郑州"></label>
                <label class="rt-field"><span>目的地</span><input id="rtDestination" list="rtCityList" autocomplete="off" placeholder="例如：成都"></label>
                <datalist id="rtCityList"></datalist>
                <label class="rt-field"><span>出发日期</span><input id="rtStartDate" type="date"></label>
                <label class="rt-field"><span>出行天数</span><input id="rtDays" type="number" min="1" max="30" value="5" inputmode="numeric"></label>
              </div>
              <div class="rt-field wide"><span>行程形式</span><div class="rt-segment" id="rtTripType">
                <label><input type="radio" name="rtTripType" value="oneway" checked><span>单程</span></label>
                <label><input type="radio" name="rtTripType" value="roundtrip"><span>往返</span></label>
                <label><input type="radio" name="rtTripType" value="loop"><span>环线</span></label>
              </div></div>
              <div class="rt-step-actions"><button class="rt-step-next" type="button" data-rt-next="2">下一步：驾驶偏好</button></div>
            </fieldset>
            <fieldset class="rt-step" data-rt-step="2">
              <legend><span>02</span>驾驶与玩法偏好</legend>
              <div class="rt-field-grid">
                <label class="rt-field"><span>每日驾驶上限</span><select id="rtMaxDailyHours"><option value="3">3 小时</option><option value="4">4 小时</option><option value="5" selected>5 小时</option><option value="6">6 小时</option><option value="8">8 小时</option></select></label>
                <label class="rt-field"><span>路线策略</span><select id="rtRouteStrategy"><option value="standard">综合推荐</option><option value="fast">时间优先</option><option value="toll">少收费</option><option value="nohighway">少走高速</option></select></label>
                <label class="rt-field"><span>旅行主题</span><select id="rtTheme"><option value="综合">综合</option><option value="自然风景">自然风景</option><option value="人文历史">人文历史</option><option value="地方美食">地方美食</option><option value="亲子轻松">亲子轻松</option><option value="摄影">摄影</option></select></label>
                <label class="rt-field"><span>车辆类型</span><select id="rtVehicle"><option value="gas">燃油车</option><option value="phev">插电混动</option><option value="ev">纯电动车</option></select></label>
              </div>
              <div class="rt-step-actions"><button type="button" data-rt-back="1">返回路线</button><button class="rt-step-next" type="button" data-rt-next="3">下一步：费用参数</button></div>
            </fieldset>
            <fieldset class="rt-step" data-rt-step="3">
              <legend><span>03</span>人数与费用参考</legend>
              <div class="rt-field-grid">
                <label class="rt-field"><span>出行人数</span><input id="rtTravelers" type="number" min="1" max="12" value="2" inputmode="numeric"></label>
                <label class="rt-field"><span data-label="consumption">百公里油耗</span><input id="rtConsumption" type="number" min="0" max="50" step="0.1" value="8" inputmode="decimal"></label>
                <label class="rt-field"><span data-label="energy-price">燃油单价</span><input id="rtEnergyPrice" type="number" min="0" max="30" step="0.1" value="8" inputmode="decimal"></label>
                <label class="rt-field"><span>每晚住宿参考</span><input id="rtHotel" type="number" min="0" value="320" inputmode="numeric"></label>
                <label class="rt-field"><span>每人每日餐饮</span><input id="rtMeals" type="number" min="0" value="120" inputmode="numeric"></label>
                <label class="rt-field"><span>每人门票参考</span><input id="rtTickets" type="number" min="0" value="0" inputmode="numeric"><small class="rt-field-note">填 0 时优先读取目的地攻略中的明确票价。</small></label>
              </div>
              <details class="rt-details">
                <summary>离线估算参数</summary>
                <div class="rt-field-grid" id="rtOfflineFields">
                  <label class="rt-field"><span>预计单程公里数</span><input id="rtEstimatedKm" type="number" min="0" value="0" inputmode="numeric"><small class="rt-field-note">留 0 由系统估算。</small></label>
                  <label class="rt-field"><span>预计道路收费</span><input id="rtEstimatedTolls" type="number" min="0" value="0" inputmode="numeric"><small class="rt-field-note">留 0 按里程估算。</small></label>
                </div>
              </details>
              <p class="rt-error" id="rtError" role="alert"></p>
              <div class="rt-step-actions"><button type="button" data-rt-back="2">返回偏好</button><button class="rt-submit" id="rtGenerate" type="submit">生成自驾路书</button></div>
            </fieldset>
          </form>
        </aside>
        <section class="rt-stage">
          <div class="rt-map-frame is-idle">
            <div class="rt-map" id="rtMap"><div class="rt-map-empty"><div class="rt-route-sketch"><i></i><b></b><i></i></div><div><strong>路线地图</strong><p>生成路书后显示路线状态；配置地图服务后显示真实路网。</p></div></div></div>
            <div class="rt-map-status" id="rtMapStatus">离线模式可直接使用；地图服务尚未配置。</div>
          </div>
          <div class="rt-result-actions" hidden>
            <button class="rt-action primary" id="rtSave" type="button" disabled>保存路书</button>
            <button class="rt-action" id="rtShare" type="button" disabled>分享链接</button>
            <button class="rt-action" id="rtExport" type="button" disabled>导出 Markdown</button>
            <button class="rt-action" id="rtPrint" type="button" disabled>打印</button>
            <span class="rt-save-tip" id="rtSaveTip" hidden>已保存到本机</span>
          </div>
          <div class="rt-results" id="rtResults" aria-live="polite"><div class="rt-empty-state"><strong>尚未生成路书</strong><span>填写左侧条件后开始计算。</span></div></div>
        </section>
      </div>
    </section>"""


def build_plan_page() -> None:
    page = Page(RECORD_SOURCE, OUT / "plan.html", "plan", "行程计划 · 游记地图",
                "把景点放进每一天，估算预算，保存、分享与旅途中查看今天安排。", "#2f6f9f", "")
    masthead = catalog_masthead(
        "Trip Planner",
        "行程计划",
        "把攻略里的景点和美食放进具体某一天，调整顺序和时间，查看每天的强度和参考预算；旅途中切到“今天”看当天安排和导航。",
        [("本机保存", "刷新、关闭后可恢复"), ("不含交易", "费用均为自填估算")],
    )
    body = masthead + (
        '<section class="plan-app" id="planApp" aria-label="行程计划工作台">'
        '<p class="plan-loading">正在载入本机保存的行程…</p>'
        '<noscript><p class="plan-notice">行程计划需要启用 JavaScript；攻略页面本身无需脚本即可阅读。</p></noscript>'
        '</section>'
    )
    page.output.write_text(shell_page_html(page, page.title, body, "plan"), encoding="utf-8")


def build_roadtrip_page() -> None:
    page = Page(RECORD_SOURCE, OUT / "roadtrip.html", "roadtrip", "自驾路书 · 游记地图",
                "自驾路线、逐日安排、预算和风险清单", "#176b5d", "")
    head = f'  <link rel="stylesheet" href="{asset_href(ASSETS / "roadtrip.css", page.output.parent)}">'
    scripts = "\n".join([
        roadtrip_runtime_config_html(),
        f'  <script src="{asset_href(ASSETS / "roadtrip-data.js", page.output.parent)}"></script>',
        f'  <script src="{asset_href(ASSETS / "roadtrip-core.js", page.output.parent)}"></script>',
        f'  <script src="{asset_href(ASSETS / "roadtrip-app.js", page.output.parent)}"></script>',
    ])
    output = shell_page_html(page, page.title, roadtrip_body(), "roadtrip", head, scripts)
    page.output.write_text(output, encoding="utf-8")


def roadtrip_runtime_config_html() -> str:
    """Inline optional browser-visible map configuration without a 404-prone file.

    AMap's JS API credentials are delivered to the browser by design.  They must
    be restricted to the published hostname; Web Service private keys never
    belong here.  Keeping the default empty preserves the fully offline planner.
    """
    config = {
        "amapJsKey": os.environ.get("TRAVEL_AMAP_JS_KEY", "").strip(),
        "amapSecurityCode": os.environ.get("TRAVEL_AMAP_SECURITY_CODE", "").strip(),
    }
    payload = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f"  <script>window.TRAVEL_ROADTRIP_CONFIG = {payload};</script>"


def build_roadtrip_assets() -> None:
    for name in ("roadtrip-core.js", "roadtrip-app.js", "roadtrip.css"):
        shutil.copyfile(ROOT / "tools" / name, ASSETS / name)
    (ASSETS / "roadtrip-data.js").write_text(roadtrip_data_js(), encoding="utf-8")


def city_photo_count(page: Page) -> int:
    photo_dir = PHOTOS / page.key
    if not photo_dir.exists():
        return 0
    return int((photo_dir / "scenery-01.jpg").exists())


def licensed_city_photo_count(page: Page) -> int:
    """Count traceable source photos, excluding generated cover derivatives."""
    load_photo_cache()
    count = 0
    prefix = f"cityphoto|{page.key}"
    for key, entry in PHOTO_CACHE.items():
        if not (key == prefix or key.startswith(prefix + "|")):
            continue
        if photo_is_publishable(entry, page.key):
            count += 1
    return count


def official_source_count(urls: Iterable[str]) -> int:
    """Conservatively count recognizable first-party/public-sector sources."""
    count = 0
    for url in urls:
        domain = urlparse(url).netloc.lower().split(":", 1)[0]
        if domain.endswith((".gov.cn", ".gov.hk", ".gov.mo", ".gov")):
            count += 1
        elif any(token in domain for token in ("museum", "mct.gov", "tourism.gov")):
            count += 1
    return count


def build_content_audit() -> None:
    load_photo_cache()
    rows = []
    for page in PAGES:
        if page.key == "record":
            continue
        markdown = read_markdown_cached(page)
        profile = city_profile(page)
        source_urls = extract_urls(markdown)
        source_count = len(source_urls)
        official_count = official_source_count(source_urls)
        photo_count = city_photo_count(page)
        licensed_photo_count = licensed_city_photo_count(page)
        photo_entry = PHOTO_CACHE.get(f"cityphoto|{page.key}")
        editorial_rejection = photo_editorial_rejection(page.key, photo_entry)
        review_date = explicit_review_date(page, markdown)
        cover = IMAGES / f"{page.key}.jpg"
        cover_size = cover.stat().st_size if cover.exists() else 0
        issues = []
        if len(markdown) < 3000:
            issues.append("原始内容偏短")
        if source_count < 2:
            issues.append("来源偏少")
        if official_count < 1:
            issues.append("缺少可识别官方来源")
        if review_date == "未核验":
            issues.append("核验日期缺失")
        if licensed_photo_count < 1:
            issues.append("缺少审核通过的可追溯实景图片")
        if editorial_rejection:
            issues.append("现有图片内容审核未通过")
        if cover_size and cover_size < 12000:
            issues.append("封面疑似占位")
        if not issues:
            issues.append("基础完整")
        rows.append({
            "title": profile["title"],
            "province": profile["province"],
            "path": rel_to(page.output, ROOT),
            "chars": len(markdown),
            "sources": source_count,
            "official_sources": official_count,
            "photos": photo_count,
            "licensed_photos": licensed_photo_count,
            "photo_editorial_reason": editorial_rejection.get("reason", "") if editorial_rejection else "",
            "photo_editorial_source": editorial_rejection.get("source", "") if editorial_rejection else "",
            "photo_editorial_reviewed_at": editorial_rejection.get("reviewedAt", "") if editorial_rejection else "",
            "review_date": review_date,
            "cover_kb": round(cover_size / 1024, 1) if cover_size else 0,
            "issues": "、".join(issues),
        })

    weak = [row for row in rows if row["issues"] != "基础完整"]
    rejected_photos = [row for row in rows if row["photo_editorial_reason"]]
    weak.sort(key=lambda row: (row["issues"].count("、"), -row["sources"], row["chars"]), reverse=True)
    lines = [
        "# 内容与图片体检",
        "",
        f"> 报告生成日期：{date.today().isoformat()}（不是城市资料核验日期）",
        f"> 城市页：{len(rows)}；需要优先补充：{len(weak)}。",
        "",
        "## 优先处理清单",
        "",
        "| 城市 | 省份 | 原始字数 | 来源 | 官方来源 | 可追溯图片 | 核验日期 | 问题 |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in weak[:80]:
        lines.append(
            f"| [{row['title']}](../../{row['path']}) | {row['province']} | {row['chars']} | "
            f"{row['sources']} | {row['official_sources']} | {row['licensed_photos']} | "
            f"{row['review_date']} | {row['issues']} |"
        )
    lines.extend([
        "",
        "## 图片内容审核拒绝清单",
        "",
        "> 授权信息只说明能否转载；此表单独记录图片是否适合作为旅行目的地内容。拒绝与原图来源绑定，换成新来源后会自动重新进入候选。",
        "",
        "| 城市 | 拒绝原因 | 原图 | 复核日期 |",
        "| --- | --- | --- | --- |",
    ])
    for row in rejected_photos:
        source = row["photo_editorial_source"]
        source_link = f"[查看原图]({source})" if source else "未记录"
        lines.append(
            f"| {row['title']} | {row['photo_editorial_reason']} | {source_link} | "
            f"{row['photo_editorial_reviewed_at'] or '未记录'} |"
        )
    lines.extend([
        "",
        "## 补充原则",
        "",
        "- 先补官方文旅、景区官网、博物馆官网和主流购票平台；再补社媒高频玩法。",
        "- 门票、开放时间、预约和交通管制必须标注来源和更新时间。",
        "- 图片优先使用本地实拍或可确认授权来源；新增图片记录来源，避免热链。授权合规与内容适配分别审核。",
        "- 封面衍生图不计为独立素材；只有带来源与授权字段的图片才进入可追溯图片统计。",
        "- 未核验表示源文件没有明确日期，不使用文件修改时间代替旅行事实日期。",
        "- 内容短但已有清晰官方来源的城市优先扩充路线、避坑和分区动线。",
    ])
    report = ROOT / "docs" / "reports" / "内容与图片体检.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


# 全站内容完整度矩阵：衡量每座城市能否回答游客的核心问题，以及有多少是模板句。
MATRIX_SECTIONS = (
    ("结论", ("先看结论", "先看总览")),
    ("怎么玩", ("快速决策索引",)),
    ("月份", ("全年月份速查",)),
    ("季节", ("季节限定景观", "适合季节与天数")),
    ("开放/票价", ("景点营业时间和票价速查",)),
    ("行前准备", ("行前准备",)),
    ("住宿", ("住宿建议", "住宿区域")),
    ("分区", ("地图分区",)),
    ("景点", ("核心景点",)),
    ("美食", ("美食总表", "美食推荐")),
    ("路线", ("路线模板", "行程路线")),
    ("交通", ("交通细节",)),
    ("预算", ("预算参考", "时间与预算拆分")),
    ("避坑", ("避坑和取舍", "避坑提醒")),
    ("复核清单", ("出发前复核清单", "出发前复核")),
)
BOILERPLATE_MIN_CITIES = 15


def markdown_value_lines(markdown: str) -> list[str]:
    values = []
    for line in markdown.splitlines():
        match = re.match(r"^\s*-\s+(.+)$", line)
        if not match:
            continue
        label, body = split_label(match.group(1))
        values.append((body if label else match.group(1)).strip())
    return values


def boilerplate_values(pages: list[Page]) -> set[str]:
    """出现在很多城市里的同一句话视为模板句（不是该城市的具体信息）。"""
    seen: dict[str, set[str]] = {}
    for page in pages:
        for value in set(markdown_value_lines(read_markdown_cached(page))):
            if len(value) >= 8:
                seen.setdefault(value, set()).add(page.key)
    return {value for value, keys in seen.items() if len(keys) >= BOILERPLATE_MIN_CITIES}


def build_content_matrix() -> None:
    city_pages = [page for page in PAGES if page.key not in HUB_KEYS]
    templates = boilerplate_values(city_pages)
    popular = set(HOME_CITY_KEYS)
    rows = []
    for page in city_pages:
        markdown = read_markdown_cached(page)
        headings = {line[3:].strip() for line in markdown.splitlines() if line.startswith("## ")}
        covered = [name for name, options in MATRIX_SECTIONS if any(option in headings for option in options)]
        values = [value for value in markdown_value_lines(markdown) if len(value) >= 8]
        template_count = sum(value in templates for value in values)
        hours_lines = re.findall(r"^\s*-\s*(?:营业时间|开放时间|时间限制)[：:]\s*(.+)$", markdown, re.M)
        specific_hours = sum(1 for value in hours_lines if value.strip() not in templates)
        price_lines = re.findall(r"^\s*-\s*(?:门票|票价|票价/预约方式)[：:]\s*(.+)$", markdown, re.M)
        specific_prices = sum(1 for value in price_lines if value.strip() not in templates and re.search(r"\d", value))
        attractions = len(extract_first_nodes_after(markdown, "## 核心景点", 99))
        urls = extract_urls(markdown)
        review = explicit_review_date(page, markdown)
        cover = photo_is_publishable(PHOTO_CACHE.get(f"cityphoto|{page.key}"), page.key)
        template_share = round(template_count / len(values), 2) if values else 0.0
        score = (
            len(covered) / len(MATRIX_SECTIONS) * 40
            + (1 - template_share) * 25
            + min(specific_hours, 4) * 2.5
            + (10 if review != "未核验" else 0)
            + (5 if official_source_count(urls) else 0)
            + (10 if cover else 0)
        )
        rows.append({
            "key": page.key,
            "city": city_profile(page)["city"],
            "province": city_profile(page)["province"],
            "path": rel_to(page.output, ROOT),
            "popular": page.key in popular,
            "chars": len(markdown),
            "sections": covered,
            "missingSections": [name for name, _ in MATRIX_SECTIONS if name not in covered],
            "attractions": attractions,
            "specificHours": specific_hours,
            "specificPrices": specific_prices,
            "templateShare": template_share,
            "sources": len(urls),
            "officialSources": official_source_count(urls),
            "reviewDate": review,
            "licensedCover": cover,
            "score": round(score, 1),
        })
    # 热门城市且分数低的排在最前：需求价值 × 缺口。
    rows.sort(key=lambda row: (not row["popular"], row["score"], row["key"]))
    reports = ROOT / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "content-matrix.json").write_text(json.dumps({
        "generatedBy": "tools/build_travel_html.py",
        "boilerplateMinCities": BOILERPLATE_MIN_CITIES,
        "boilerplateSentences": sorted(templates),
        "cities": rows,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    coverage = {name: sum(name in row["sections"] for row in rows) for name, _ in MATRIX_SECTIONS}
    total_values = sum(len([v for v in markdown_value_lines(read_markdown_cached(p)) if len(v) >= 8]) for p in city_pages)
    total_templates = sum(round(row["templateShare"] * len([v for v in markdown_value_lines(read_markdown_cached(p)) if len(v) >= 8])) for row, p in zip(rows, sorted(city_pages, key=lambda p: [r["key"] for r in rows].index(p.key))))
    lines = [
        "# 内容完整度矩阵",
        "",
        "> 由 `npm run build` 自动生成，衡量每座城市能否回答游客的核心问题。机器可读版本见 `content-matrix.json`。",
        f"> 模板句定义：同一句话出现在 ≥{BOILERPLATE_MIN_CITIES} 座城市的条目里，视为通用模板而不是该城市的具体信息。",
        "",
        "## 全站概况",
        "",
        f"- 城市：{len(rows)}；已标注核验日期：{sum(row['reviewDate'] != '未核验' for row in rows)}；有授权实景封面：{sum(row['licensedCover'] for row in rows)}",
        f"- 条目总数约 {total_values}，其中模板句约 {total_templates}（{total_templates / max(total_values, 1):.0%}）；全站识别出 {len(templates)} 种模板句",
        f"- 有具体（非模板）开放时间的城市：{sum(row['specificHours'] > 0 for row in rows)}；有具体票价数字的城市：{sum(row['specificPrices'] > 0 for row in rows)}",
        "",
        "| 章节 | 覆盖城市数 |",
        "| --- | ---: |",
        *[f"| {name} | {count} |" for name, count in coverage.items()],
        "",
        "## 城市矩阵（热门且得分低的优先）",
        "",
        "得分 = 章节覆盖 40 + 非模板比例 25 + 具体开放时间 ≤10 + 核验日期 10 + 官方来源 5 + 授权封面 10。",
        "",
        "| 城市 | 省份 | 热门 | 得分 | 章节 | 缺少章节 | 景点 | 具体开放时间 | 具体票价 | 模板句占比 | 来源/官方 | 核验日期 | 封面 |",
        "| --- | --- | :---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | :---: |",
    ]
    for row in rows:
        lines.append(
            f"| [{row['city']}](../../{row['path']}) | {row['province']} | {'★' if row['popular'] else ''} | {row['score']} | "
            f"{len(row['sections'])}/{len(MATRIX_SECTIONS)} | {'、'.join(row['missingSections']) or '—'} | {row['attractions']} | "
            f"{row['specificHours']} | {row['specificPrices']} | {row['templateShare']:.0%} | {row['sources']}/{row['officialSources']} | "
            f"{row['reviewDate']} | {'✓' if row['licensedCover'] else '—'} |"
        )
    lines += ["", "## 最常见的模板句", ""]
    counts: dict[str, int] = {}
    for page in city_pages:
        for value in markdown_value_lines(read_markdown_cached(page)):
            if value in templates:
                counts[value] = counts.get(value, 0) + 1
    for value, count in sorted(counts.items(), key=lambda item: -item[1])[:20]:
        lines.append(f"- {count} 次：{value}")
    (reports / "内容完整度矩阵.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def image_dimensions(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return (0, 0)


def build_image_inventory() -> None:
    """图片清单：每张图片的主体、来源、授权、尺寸、是否发布与审核结论。"""
    load_photo_cache()
    load_photo_editorial_decisions()
    referenced: set[str] = set()
    for html_path in OUT.rglob("*.html"):
        for match in re.finditer(r'(?:src|data-src)="(?:\.\./)*(assets/(?:images|photos|item-images)/[^"?#]+)', html_path.read_text(encoding="utf-8")):
            referenced.add(match.group(1))
    by_path: dict[str, tuple[str, dict]] = {}
    for key, entry in PHOTO_CACHE.items():
        if isinstance(entry, dict) and entry.get("path"):
            by_path.setdefault(str(entry["path"]), (key, entry))
    records = []
    hashes: dict[str, str] = {}
    for path in sorted(list(IMAGES.rglob("*")) + list(PHOTOS.rglob("*")) + list(ITEM_IMAGES.rglob("*")) + list(SOURCE_MEDIA_DIR.rglob("*"))):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            continue
        rel = rel_to(path, OUT)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        width, height = image_dimensions(path)
        cache_key, entry = by_path.get(rel, ("", {}))
        if not entry and path.parent == IMAGES and path.suffix == ".jpg":
            entry = PHOTO_CACHE.get(f"cityphoto|{path.stem}", {}) or {}
            cache_key = f"cityphoto|{path.stem}"
        if path.parent == COVER_SMALL:
            subject, kind = path.stem, "封面小图"
            entry = PHOTO_CACHE.get(f"cityphoto|{path.stem}", {}) or {}
            cache_key = f"cityphoto|{path.stem}"
        elif path.parent == IMAGES:
            subject, kind = path.stem, "城市封面" if path.suffix == ".jpg" else "程序生成插画"
        elif SOURCE_MEDIA_DIR in path.parents:
            subject, kind = "来源网页截取", "来源网页媒体"
        elif path.name.startswith("scenery-"):
            subject, kind = path.parent.name, "封面衍生裁切"
        elif path.name.startswith("cityphoto-src"):
            subject, kind = path.parent.name, "封面原图"
        else:
            subject, kind = str(entry.get("title", "")).removeprefix("File:") or path.stem, "条目配图"
        city_key = cache_key.split("|", 1)[1] if cache_key.startswith("cityphoto|") else path.parent.name if path.parent != IMAGES else path.stem
        licensed = photo_has_republication_rights(entry) if entry else False
        rejection = photo_editorial_rejection(city_key, entry) if cache_key.startswith("cityphoto|") else None
        if kind == "程序生成插画":
            verdict = "未展示：程序生成插画，不冒充实景"
        elif kind == "来源网页媒体":
            verdict = "不得发布：来源网页图片没有记录转载授权"
        elif rejection:
            verdict = f"移出展示：{rejection.get('reason', '内容审核未通过')}"
        elif not licensed and kind in {"城市封面", "条目配图", "封面原图", "封面小图"}:
            verdict = "不得发布：缺少可追溯授权"
        elif rel in referenced:
            verdict = "展示中：授权可追溯；主体为自动匹配，人工语义复核待补"
        else:
            verdict = "未展示：页面未引用"
        duplicate_of = hashes.get(digest, "")
        hashes.setdefault(digest, rel)
        records.append({
            "path": rel, "kind": kind, "subject": subject, "city": city_key,
            "source": entry.get("source", "") if entry else "", "author": entry.get("artist", "") if entry else "",
            "license": entry.get("license", "") if entry else "", "width": width, "height": height,
            "bytes": path.stat().st_size, "sha256": digest[:16], "duplicateOf": duplicate_of,
            "displayed": rel in referenced, "verdict": verdict,
        })
    reports = ROOT / "docs" / "reports"
    (reports / "image-inventory.json").write_text(json.dumps({"generatedBy": "tools/build_travel_html.py", "images": records}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summary: dict[str, int] = {}
    for record in records:
        summary[record["verdict"].split("：")[0]] = summary.get(record["verdict"].split("：")[0], 0) + 1
    kinds: dict[str, int] = {}
    for record in records:
        kinds[record["kind"]] = kinds.get(record["kind"], 0) + 1
    displayed = [record for record in records if record["displayed"]]
    lines = [
        "# 图片清单",
        "",
        "> 由 `npm run build` 自动生成。逐张列出主体、来源、作者、许可、尺寸、是否展示和审核结论；完整字段见 `image-inventory.json`。",
        "> “授权可追溯”只说明来源与许可字段齐全；主体是否切题、有无错配仍需人工复核，本清单不把自动匹配当作人工审核。",
        "",
        "## 汇总",
        "",
        f"- 图片文件：{len(records)}；页面实际展示：{len(displayed)}；重复文件：{sum(bool(r['duplicateOf']) for r in records)}",
        *[f"- {kind}：{count}" for kind, count in sorted(kinds.items(), key=lambda item: -item[1])],
        "",
        "| 结论 | 数量 |",
        "| --- | ---: |",
        *[f"| {verdict} | {count} |" for verdict, count in sorted(summary.items(), key=lambda item: -item[1])],
        "",
        "## 页面展示中的图片",
        "",
        "| 图片 | 类型 | 主体 | 作者 | 许可 | 尺寸 | 来源 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in displayed:
        source = f"[来源]({record['source']})" if record["source"] else "—"
        lines.append(f"| `{record['path']}` | {record['kind']} | {record['subject']} | {record['author'] or '—'} | {record['license'] or '—'} | {record['width']}×{record['height']} | {source} |")
    lines += ["", "## 未展示或不得发布", "", "| 图片 | 类型 | 结论 |", "| --- | --- | --- |"]
    for record in records:
        if not record["displayed"] and record["kind"] != "封面衍生裁切":
            lines.append(f"| `{record['path']}` | {record['kind']} | {record['verdict']} |")
    lines.append("")
    lines.append(f"另有 {kinds.get('封面衍生裁切', 0)} 张“封面衍生裁切”（`scenery-01.jpg`）是封面的缩略副本，页面不再展示。")
    (reports / "图片清单.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_source_playbook() -> None:
    lines = [
        "# 资料来源与更新规则",
        "",
        f"> 生成日期：{date.today().isoformat()}",
        "",
        "## 信息分级",
        "",
        "1. 官方优先：文旅部门、景区官网、博物馆官网、官方公众号、政府公告。",
        "2. 票务交叉：携程、去哪儿、同程等平台用于核对价格区间、预约和营业状态。",
        "3. 攻略补充：马蜂窝、携程攻略、去哪儿攻略用于路线、时间成本和用户体验。",
        "4. 社媒发现：小红书、抖音、B站只用于发现高频玩法、拍照点、近期拥堵和避坑，不作为唯一事实来源。",
        "",
        "## 固定入口",
        "",
        "- 文化和旅游部：https://www.mct.gov.cn/",
        "- 携程攻略：https://you.ctrip.com/",
        "- 马蜂窝：https://www.mafengwo.cn/",
        "- 去哪儿攻略：https://travel.qunar.com/",
        "- 哔哩哔哩检索：https://search.bilibili.com/",
        "- 小红书检索：https://www.xiaohongshu.com/search_result",
        "- 抖音检索：https://www.douyin.com/search/",
        "- Wikimedia Commons 图片：https://commons.wikimedia.org/",
        "",
        "## 更新流程",
        "",
        "1. 在城市页景点卡片上点“查官网 / 地图 / 攻略”。",
        "2. 先核对官方开放时间、门票、预约和交通，再看攻略平台路线。",
        "3. 把确认后的新增内容写入 `content\\城市\\*.md` 的对应章节。",
        "4. 新增来源写入该城市 Markdown 末尾的“来源参考”。",
        "5. 图片先核对 Commons 文件页的作者与许可证，再检查是否真实对应城市、主体清晰且适合旅游内容。",
        "6. 自动候选用 `TRAVEL_FETCH_CITY_KEYS` 定向抓取；人工选定文件用 `tools\\import_commons_city_photo.py` 导入。",
        "7. 不合格来源写入 `site\\assets\\photo-editorial-decisions.json`；拒绝与具体来源绑定，未来换图后自动失效。",
        "8. 在项目根目录运行 `npm run check`，并检查 `docs/reports/内容与图片体检.md`；Windows 也可运行 `scripts/windows/重新生成网页.bat`。",
    ]
    guide = ROOT / "docs" / "guides" / "资料来源与更新规则.md"
    guide.parent.mkdir(parents=True, exist_ok=True)
    guide.write_text("\n".join(lines) + "\n", encoding="utf-8")


DAYS_LABELS = {"1": "1 天内", "2-3": "2-3 天", "4+": "4 天以上"}


def explicit_days_text(markdown: str) -> str:
    """“推荐天数：3—4 天。……”里的天数部分，原样展示，避免被归档成粗略区间。"""
    match = re.search(r"^-\s*推荐天数[：:]\s*([0-9０-９一二三四五六七八九十半—\-～~ ]+天)", markdown, re.M)
    return match.group(1).strip() if match else ""


def chip_links(terms: list[str], anchor_index: AnchorIndex, css_class: str = "chip") -> str:
    chips = []
    for term in terms:
        href = anchor_index.terms.get(term)
        if href:
            chips.append(f'<a class="{css_class}" href="{html.escape(href)}">{html.escape(term)}</a>')
        else:
            chips.append(f'<span class="{css_class}">{html.escape(term)}</span>')
    return "".join(chips)


def city_overview_html(page: Page, anchor_index: AnchorIndex | None = None) -> str:
    """城市页正文顶部的「一眼看懂」：所在、季节、天数、资料状态，以及必看与必吃。"""
    if page.key in HUB_KEYS:
        return ""
    anchor_index = anchor_index or AnchorIndex(terms={}, section_ids=set(), section_terms={})
    prof = city_profile(page)
    review_date = explicit_review_date(page, read_markdown_cached(page))
    review_status = "reviewed" if review_date != "未核验" else "pending"
    review_label = f"核验日期 {review_date}" if review_status == "reviewed" else "资料待复核"
    highlights = [h for h in prof["highlights"] if h][:6]
    foods = [f for f in prof["foods"] if f][:6]
    cells = [
        ("pin", "所在", prof["province"], ""),
        ("calendar", "适宜季节", prof["season"], ""),
        ("clock", "建议天数", explicit_days_text(read_markdown_cached(page)) or DAYS_LABELS.get(prof["daysClass"], "2-3 天"), ""),
        ("info", "资料状态", review_label, f" co-review {review_status}"),
    ]
    facts = "".join(
        f'<div class="co-cell{extra}"{f" data-review-status=\"{review_status}\"" if extra else ""}>'
        f'<span class="co-ico">{icon(icon_name)}</span>'
        f'<span class="co-k">{label}</span><span class="co-v">{html.escape(value)}</span></div>'
        for icon_name, label, value, extra in cells
    )
    hl = chip_links(highlights, anchor_index) or '<span class="chip">见下方正文</span>'
    fd = chip_links(foods, anchor_index, "chip chip-food") or '<span class="chip">见下方正文</span>'
    return (
        '<section class="city-overview" aria-label="城市速览">'
        f'<div class="co-facts">{facts}</div>'
        '<div class="co-blocks">'
        f'<div class="co-block"><span class="co-bk">{icon("pin")}必看景点</span><div class="chip-row">{hl}</div></div>'
        f'<div class="co-block"><span class="co-bk">{icon("food")}必吃美食</span><div class="chip-row">{fd}</div></div>'
        '</div>'
        '<p class="co-review-note">动态信息出行前复核：门票、开放时间与预约规则会变化，请以官方渠道为准。</p>'
        '</section>'
    )


def city_actions_html(page: Page) -> str:
    prof = city_profile(page)
    href = rel_to(page.output, OUT)  # 相对站点根，供收藏/行程在用户中心回链
    data_attrs = (
        f'data-key="{html.escape(page.key)}" data-name="{html.escape(prof["title"])}" '
        f'data-href="{html.escape(href)}" data-sub="{html.escape(prof["subtitle"])}"'
    )
    return (
        '<div class="co-actions">'
        f'<button class="co-fav" type="button" {data_attrs}>☆ 收藏</button>'
        f'<button class="co-trip" type="button" {data_attrs}>＋ 加入行程</button>'
        f'<button class="co-share" type="button" data-share-title="{html.escape(prof["title"])}" '
        f'aria-label="分享{html.escape(prof["title"])}" title="分享当前城市攻略">↗ 分享</button>'
        '</div>'
    )


def city_hero_html(page: Page, title: str) -> str:
    base = page.output.parent
    prof = city_profile(page)
    entries = carousel_entries(page)
    if entries:
        media = hero_carousel_html(page, captions=False)
        hero_class = "city-hero has-photo"
    else:
        media = f'<div class="hero-fallback" aria-hidden="true"><span>{html.escape(prof["city"][:2])}</span></div>'
        hero_class = "city-hero no-photo"
    home = rel_to(OUT / "index.html", base)
    province_href = rel_to(OUT / "destinations.html", base) + "?province=" + quote(prof["province"])
    crumbs = (
        '<nav class="breadcrumb" aria-label="当前位置">'
        f'<a href="{home}">首页</a><span aria-hidden="true">/</span>'
        f'<a href="{html.escape(province_href)}">{html.escape(prof["province"])}</a><span aria-hidden="true">/</span>'
        f'<span aria-current="page">{html.escape(prof["city"])}</span></nav>'
    )
    return (
        f'<section class="{hero_class}">'
        f'<div class="city-hero-media">{media}</div>'
        '<div class="city-hero-inner">'
        f'{crumbs}'
        f'<p class="eyebrow">{html.escape(prof["region"])} · {html.escape(prof["province"])}</p>'
        f'<h1>{html.escape(title)}</h1>'
        f'<p class="subtitle">{html.escape(page.subtitle)}</p>'
        f'{city_actions_html(page)}'
        '</div>'
        f'{city_cover_credit_html(page)}'
        '</section>'
    )


def overview_hero_html(page: Page, title: str) -> str:
    base = page.output.parent
    home = rel_to(OUT / "index.html", base)
    city_count = sum(1 for item in PAGES if item.key not in HUB_KEYS)
    return (
        '<section class="city-hero no-photo hub-hero">'
        '<div class="city-hero-media"><div class="hero-fallback" aria-hidden="true"><span>总览</span></div></div>'
        '<div class="city-hero-inner">'
        f'<nav class="breadcrumb" aria-label="当前位置"><a href="{home}">首页</a><span aria-hidden="true">/</span><span aria-current="page">跨城市总览</span></nav>'
        '<p class="eyebrow">Overview</p>'
        f'<h1>{html.escape(title)}</h1>'
        f'<p class="subtitle">{html.escape(page.subtitle)}。覆盖 {city_count} 座城市的时间成本、场景、季节与跨城路线。</p>'
        '</div></section>'
    )


SECTION_TAB_LABELS = {
    "overview": "结论", "quick": "怎么玩", "months": "月份", "seasonal": "季节",
    "hours-prices": "票价", "prep": "准备", "stay": "住宿", "areas": "分区",
    "attractions": "景点", "streets": "街区", "food": "美食", "shops": "店铺",
    "museums": "博物馆", "nature": "周边", "routes": "路线", "transport": "交通",
    "warnings": "避坑", "checklist": "清单",
}


def section_tabs_html(toc: list[tuple[int, str, str]]) -> str:
    links = []
    for level, text, sid in toc:
        if level != 2:
            continue
        label = SECTION_TAB_LABELS.get(sid, text if len(text) <= 8 else text[:7] + "…")
        links.append(f'<a href="#{sid}" title="{html.escape(text)}">{html.escape(label)}</a>')
    if not links:
        return ""
    return (
        '<nav class="section-tabs" aria-label="攻略章节">'
        f'<div class="section-tabs-track toc">{"".join(links)}</div></nav>'
    )


def guide_page_html(page: Page, markdown: str) -> str:
    """城市攻略页与跨城市总览页：封面、章节标签栏、正文组件和侧栏。"""
    is_hub = page.key in HUB_KEYS
    if is_hub:
        markdown = strip_author_sections(markdown)
    title = extract_title(markdown, page.title)
    # 底部来源抽屉用完整 markdown（含「来源参考」里的链接）
    build_source_media_index(page, markdown)
    # 正文渲染时剥离来源类章节，避免与底部「资料来源」重复
    content_md = strip_sections(markdown, SOURCE_SECTION_HEADINGS) + reinforcement_appendix(page, markdown)
    anchor_index = collect_anchor_index(content_md)
    body, toc = render_markdown(content_md, page, anchor_index)
    hero = overview_hero_html(page, title) if is_hub else city_hero_html(page, title)
    overview = city_overview_html(page, anchor_index)
    toc_links = "\n".join(
        f'<a class="toc-level-{level}" href="#{sid}">{html.escape(text)}</a>'
        for level, text, sid in toc
    )
    main = f"""    {hero}
    {section_tabs_html(toc)}
    <div class="guide-layout">
      <article class="content" id="guideContent">
        {overview}
        {body}
      </article>
      <aside class="guide-aside" aria-label="攻略工具与目录">
        <div class="aside-card tool-bar">
          <label class="search-box">
            <span>在本页查找</span>
            <input id="guideSearch" type="search" placeholder="景点、店铺、路线或月份">
          </label>
          <div class="tool-bar-actions">
            <button id="expandAll" type="button">清空查找</button>
            <button id="printPage" type="button">{icon("print")}打印 / PDF</button>
          </div>
        </div>
        <div class="aside-card sidebar-panel">
          <h2>目录</h2>
          <div class="toc">{toc_links}</div>
        </div>
        <div class="aside-card sidebar-panel">
          <h2>相关攻略</h2>
          <div class="city-grid mini">{card_links(page, 6)}</div>
        </div>
      </aside>
    </div>
    {research_panel_html(page) if is_hub else ""}
    {source_media_html(markdown, page)}"""
    og_image = None if is_hub else IMAGES / f"{page.key}.jpg"
    return document_html(page, title, main, "overview" if is_hub else "", page_kind="overview" if is_hub else "city", og_image=og_image)


HOME_POPULAR_KEYS = ("chengdu", "xian", "dali", "hangzhou", "qingdao", "chongqing", "sanya", "harbin")


def home_hero_html(page: Page) -> str:
    base = page.output.parent
    city_pages = [p for p in PAGES if p.key not in HUB_KEYS]
    provinces = {city_profile(p)["province"] for p in city_pages}
    by_key = {p.key: p for p in city_pages}
    popular = "".join(
        f'<a href="{html.escape(rel_to(by_key[key].output, base))}">{html.escape(city_profile(by_key[key])["city"])}</a>'
        for key in HOME_POPULAR_KEYS if key in by_key
    )
    destinations = rel_to(OUT / "destinations.html", base)
    roadtrip = rel_to(OUT / "roadtrip.html", base)
    return (
        '<section class="home-hero">'
        '<div class="home-hero-copy">'
        '<p class="eyebrow">Travel A Yuan · 游记地图</p>'
        f'<h1>{len(city_pages)} 座城市的玩法，<span>整理成能直接出发的攻略</span></h1>'
        '<p class="subtitle">景点、美食、季节、路线与避坑一页看清；收藏城市、排行程、做自驾路书，全部在浏览器里完成。</p>'
        f'<form class="hero-search" action="{destinations}" method="get" role="search">'
        '<label class="sr-only" for="heroSearch">想去哪里</label>'
        f'{icon("search")}<input id="heroSearch" name="q" type="search" autocomplete="off" placeholder="想去哪？试试：海边、古城、火锅、避暑">'
        '<button type="submit">找城市</button></form>'
        f'<div class="hero-popular"><span>热门</span>{popular}</div>'
        '<dl class="hero-stats">'
        f'<div><dt>城市攻略</dt><dd>{len(city_pages)}</dd></div>'
        f'<div><dt>省级地区</dt><dd>{len(provinces)}</dd></div>'
        '<div><dt>旅行主题</dt><dd>8</dd></div>'
        '</dl>'
        f'<div class="hero-cta"><a class="btn btn-primary" href="#travel-finder">{icon("filter")}按条件选城市</a>'
        f'<a class="btn btn-ghost" href="{roadtrip}">{icon("car")}生成自驾路书</a></div>'
        '</div>'
        f'<div class="home-hero-stage">{hero_carousel_html(page)}</div>'
        '</section>'
    )


def home_continue_html() -> str:
    """“继续上次”占位：由 home-continue.ts 读取本机行程、浏览和收藏后填充，无数据时保持隐藏。"""
    return (
        '<section class="home-continue" id="homeContinue" aria-labelledby="homeContinueTitle" hidden>'
        '<div class="home-section-head"><p class="eyebrow">Pick up where you left off</p>'
        '<h2 id="homeContinueTitle">继续上次的旅行准备</h2></div>'
        '<div class="continue-grid" id="homeContinueGrid"></div>'
        '</section>'
    )


def home_overview_teaser_html(page: Page) -> str:
    base = page.output.parent
    overview = rel_to(OVERVIEW_PAGE.output, base)
    cards = (
        ("compass", "先看总览", "第一次去哪、口味总览与总体取舍", "overview"),
        ("clock", "时间成本", "半天、1 天、2 天以上分别怎么安排", "time-cost"),
        ("umbrella", "场景索引", "雨天、亲子、夜游、温泉等场景去处", "scenes"),
        ("calendar", "季节总索引", "春花、夏避暑、秋色与冬季去处", "seasons"),
        ("route", "跨城市路线", "贵州、云南、川渝等多城串联模板", "routes"),
    )
    items = "".join(
        f'<a class="teaser-card" href="{html.escape(overview)}#{sid}"><span class="tile-ico">{icon(icon_name)}</span>'
        f'<strong>{title}</strong><span>{desc}</span></a>'
        for icon_name, title, desc, sid in cards
    )
    return (
        '<section class="home-section reveal" id="home-overview" aria-labelledby="homeOverviewTitle">'
        '<div class="home-section-head"><p class="eyebrow">Across cities</p>'
        '<h2 id="homeOverviewTitle">跨城市攻略总览</h2>'
        '<p>把原始笔记整理成按时间、场景、季节和路线查找的索引，适合多城市连游时先做取舍。</p>'
        f'<a class="section-link" href="{html.escape(overview)}">打开总览 {icon("arrow")}</a></div>'
        f'<div class="teaser-grid">{items}</div>'
        '</section>'
    )


def home_page_html(page: Page) -> str:
    main = "\n".join([
        home_hero_html(page),
        home_continue_html(),
        home_featured_html(page),
        home_themes_html(),
        home_finder_html(page),
        city_explorer_html(page),
        home_tools_html(),
        home_overview_teaser_html(page),
        research_panel_html(page),
    ])
    return document_html(
        page, "游记地图 · 全国城市旅游攻略", main, "home",
        page_kind="home", og_image=IMAGES / "record.jpg",
    )


def page_html(page: Page, markdown: str) -> str:
    if page.key == "record":
        return home_page_html(page)
    return guide_page_html(page, markdown)


RUNTIME_DIR = ROOT / "frontend" / "runtime"
CSS = (RUNTIME_DIR / "travel.css").read_text(encoding="utf-8")



JS = (RUNTIME_DIR / "travel.js").read_text(encoding="utf-8")



def build_pwa_assets() -> None:
    """生成 PWA 清单、图标与离线 Service Worker（让网页可安装到手机主屏 / 供 PWABuilder 打包 APK）。"""
    accent, deep = (15, 158, 140), (11, 111, 100)
    for size in (192, 512, 180):
        img = Image.new("RGB", (size, size), accent)
        d = ImageDraw.Draw(img)
        draw_gradient(d, size, size, accent, deep)
        f = load_font(int(size * 0.56), bold=True)
        try:
            bbox = d.textbbox((0, 0), "游", font=f)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), "游", fill=(255, 255, 255), font=f)
        except Exception:
            pass
        img.save(ASSETS / f"icon-{size}.png", "PNG", optimize=True)
    manifest = {
        "name": "游记地图 · 旅游攻略", "short_name": "游记地图",
        "start_url": "index.html", "scope": "./", "display": "standalone",
        "background_color": "#f6efe1", "theme_color": "#0f9e8c", "lang": "zh-CN",
        "description": "跨城市旅游攻略：景点、美食、季节、自驾路书与行程编排。",
        "icons": [
            {"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "shortcuts": [
            {"name": "生成自驾路书", "short_name": "自驾路书", "url": "roadtrip.html", "icons": [
                {"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png"}
            ]},
            {"name": "城市攻略", "short_name": "城市攻略", "url": "city-guides.html", "icons": [
                {"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png"}
            ]},
        ],
    }
    (OUT / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    build_digest = ASSET_BUILD or hashlib.sha256((CSS + "\n" + JS).encode("utf-8")).hexdigest()[:10]
    # Keep first-install work small. Destination catalog pages are cached after a
    # successful visit, so downloading the entire catalog is unnecessary here.
    app_shell = [
        "./index.html", "./manifest.webmanifest",
        f"./assets/travel.css?v={build_digest}",
        f"./assets/travel.js?v={build_digest}",
        "./assets/icon-180.png", "./assets/icon-192.png", "./assets/icon-512.png",
    ]
    entry_file, imported_files, css_files = vite_bundle_files()
    for bundle_file in [entry_file, *imported_files, *css_files]:
        if bundle_file:
            app_shell.append(f"./assets/{bundle_file}?v={build_digest}")
    app_shell_json = json.dumps(app_shell, ensure_ascii=False, separators=(",", ","))
    sw = (
        f"const CACHE='tay-{build_digest}';\n"
        "const OFFLINE_PAGE='<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>游记地图 · 离线</title><style>body{font-family:system-ui,-apple-system,\"Microsoft YaHei\",sans-serif;max-width:42rem;margin:12vh auto;padding:0 1.25rem;line-height:1.7;color:#183b3a;background:#f6efe1}h1{font-size:1.6rem}p{color:#4d6765}a,button{min-height:44px;display:inline-flex;align-items:center;padding:0 14px;margin:8px 8px 0 0;border:1px solid #176b5d;border-radius:8px;color:#fff;background:#176b5d;font:inherit;font-weight:700;text-decoration:none}button{color:#176b5d;background:transparent}</style></head><body><main><p>游记地图</p><h1>当前处于离线状态</h1><p>这页还没有缓存。请先联网打开目标城市攻略，之后即可在弱网或离线时继续阅读。</p><p>已访问并缓存的攻略仍可使用；外部核验链接需要恢复网络后打开。</p><a href=\"__HOME__\">返回已缓存首页</a><button type=\"button\" onclick=\"location.reload()\">重新尝试</button></main></body></html>';\n"
        "const offlineResponse=()=>new Response(OFFLINE_PAGE.replace('__HOME__',new URL('./index.html',self.registration.scope).href),{status:503,headers:{'Content-Type':'text/html;charset=utf-8','Cache-Control':'no-store'}});\n"
        f"const APP_SHELL={app_shell_json};\n"
        "self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(APP_SHELL)).then(()=>self.skipWaiting()));});\n"
        "self.addEventListener('activate',e=>{e.waitUntil(Promise.all([\n"
        "  caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('tay-')&&k!==CACHE).map(k=>caches.delete(k)))),\n"
        "  self.clients.claim()\n"
        "]))});\n"
        "self.addEventListener('fetch',e=>{\n"
        "  if(e.request.method!=='GET')return;\n"
        "  if(e.request.mode==='navigate'||e.request.destination==='document'){\n"
        "    e.respondWith(caches.open(CACHE).then(async c=>{\n"
        "      try{const res=await fetch(e.request);if(res&&res.ok)c.put(e.request,res.clone());return res;}\n"
        "      catch(_){return await c.match(e.request)||offlineResponse();}\n"
        "    }));return;\n"
        "  }\n"
        "  if(e.request.destination==='script'||e.request.destination==='style'){\n"
        "    e.respondWith(caches.open(CACHE).then(async c=>{\n"
        "      try{const res=await fetch(e.request);if(res&&res.ok)c.put(e.request,res.clone());return res;}\n"
        "      catch(_){return await c.match(e.request)||Response.error();}\n"
        "    }));return;\n"
        "  }\n"
        "  e.respondWith(caches.open(CACHE).then(async c=>{\n"
        "    const hit=await c.match(e.request);\n"
        "    const net=fetch(e.request).then(res=>{if(res&&res.ok)c.put(e.request,res.clone());return res;}).catch(()=>hit);\n"
        "    return hit?hit:net;\n"
        "  }));\n"
        "});\n"
    )
    (OUT / "sw.js").write_text(sw, encoding="utf-8")


def build_cover_variants() -> None:
    """为授权封面生成 640px 宽的小图，供城市卡片和手机端 srcset 使用。

    只在小图缺失或封面内容变化时重新编码，避免每次构建都改写已提交的文件。
    """
    COVER_SMALL.mkdir(parents=True, exist_ok=True)
    index_path = COVER_SMALL / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        index = {}
    wanted: dict[str, str] = {}
    for cover in sorted(IMAGES.glob("*.jpg")):
        digest = hashlib.sha256(cover.read_bytes()).hexdigest()[:16]
        wanted[cover.stem] = digest
        target = COVER_SMALL / cover.name
        if target.is_file() and index.get(cover.stem) == digest:
            continue
        with Image.open(cover) as image:
            image = image.convert("RGB")
            width, height = image.size
            if width > 640:
                image = image.resize((640, round(height * 640 / width)), Image.Resampling.LANCZOS)
            image.save(target, "JPEG", quality=78, optimize=True, progressive=True)
    for stale in COVER_SMALL.glob("*.jpg"):
        if stale.stem not in wanted:
            stale.unlink()
    index_path.write_text(json.dumps(wanted, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def cover_srcset(key: str, from_dir: Path) -> str:
    """封面图的 srcset 属性（小图存在时）。"""
    small = COVER_SMALL / f"{key}.jpg"
    large = IMAGES / f"{key}.jpg"
    if not small.is_file() or not large.is_file():
        return ""
    return (
        f' srcset="{html.escape(rel_to(small, from_dir))} 640w, {html.escape(rel_to(large, from_dir))} 1280w"'
    )


def prepare_image_output() -> None:
    """Clean generated image output without deleting versioned photo derivatives."""
    load_photo_cache()
    IMAGES.mkdir(parents=True, exist_ok=True)
    preserved: set[Path] = set()
    for key, entry in PHOTO_CACHE.items():
        if not (key.startswith("cityphoto|") and key.count("|") == 1):
            continue
        slug = key.split("|", 1)[1]
        expected = IMAGES / f"{slug}.jpg"
        cached_path = OUT / str(entry.get("path", ""))
        if (
            photo_is_publishable(entry, slug)
            and expected.is_file()
            and cached_path.resolve() == expected.resolve()
        ):
            preserved.add(expected.resolve())

    for child in list(IMAGES.iterdir()):
        if child.resolve() in preserved or child.resolve() == COVER_SMALL.resolve():
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def build() -> None:
    global ASSET_BUILD
    ASSETS.mkdir(parents=True, exist_ok=True)
    prepare_image_output()
    build_cover_variants()
    if ITEM_IMAGES.exists():
        shutil.rmtree(ITEM_IMAGES)
    ITEM_IMAGES.mkdir(parents=True, exist_ok=True)
    CITIES_OUT.mkdir(parents=True, exist_ok=True)
    search_index = site_search_index_js()
    build_hash = hashlib.sha256((CSS + "\n" + JS + "\n" + search_index).encode("utf-8"))
    entry_file, imported_files, css_files = vite_bundle_files()
    for bundle_file in [entry_file, *imported_files, *css_files]:
        if bundle_file:
            bundle_path = ASSETS / bundle_file
            if not bundle_path.is_file():
                raise RuntimeError(f"Vite manifest references a missing asset: {bundle_file}")
            build_hash.update(bundle_path.read_bytes())
    ASSET_BUILD = build_hash.hexdigest()[:10]
    (ASSETS / "travel.css").write_text(CSS, encoding="utf-8")
    (ASSETS / "search-index.js").write_text(search_index, encoding="utf-8")
    (ASSETS / "travel.js").write_text(JS, encoding="utf-8")
    build_roadtrip_assets()
    build_pwa_assets()
    for page in PAGES:
        draw_hero_asset(page)
    for page in PAGES:
        ensure_body_gallery(page)
    for page in PAGES:
        markdown = page.source.read_text(encoding="utf-8")
        page.output.parent.mkdir(parents=True, exist_ok=True)
        page.output.write_text(page_html(page, markdown), encoding="utf-8")
    OVERVIEW_PAGE.output.write_text(page_html(OVERVIEW_PAGE, OVERVIEW_PAGE.source.read_text(encoding="utf-8")), encoding="utf-8")
    build_user_page()
    build_roadtrip_page()
    build_plan_page()
    build_catalog_pages()
    build_seo_files()
    build_content_audit()
    build_content_matrix()
    build_image_inventory()
    build_source_playbook()
    sync_source_folders()


def sync_source_folders() -> None:
    return


if __name__ == "__main__":
    build()
