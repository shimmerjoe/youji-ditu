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
from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CITY_DIR = ROOT / "城市"
OUT = ROOT
ASSETS = OUT / "assets"
IMAGES = ASSETS / "images"
ITEM_IMAGES = ASSETS / "item-images"
PHOTOS = ASSETS / "photos"
PHOTO_CACHE_FILE = ASSETS / "photo-cache.json"
SOURCE_MEDIA_CACHE_FILE = ASSETS / "source-media-cache.json"
CITIES_OUT = OUT / "cities"
USER_AGENT = "CodexTravelGuide/1.0 personal-local-static-site"
FETCH_MEDIA = os.environ.get("TRAVEL_FETCH_MEDIA", "0") == "1"
FETCH_SOURCE_MEDIA = FETCH_MEDIA or os.environ.get("TRAVEL_FETCH_SOURCE", "0") == "1"
FETCH_COMMONS_MEDIA = FETCH_MEDIA or os.environ.get("TRAVEL_FETCH_COMMONS", "0") == "1"
PHOTO_CACHE: dict[str, dict] = {}
PHOTO_CACHE_LOADED = False
SOURCE_MEDIA_CACHE: dict[str, dict] = {}
SOURCE_MEDIA_CACHE_LOADED = False
PAGE_SOURCE_MEDIA: dict[str, list[dict]] = {}
ASSET_BUILD = ""


def asset_href(path: Path, from_dir: Path) -> str:
    href = rel_to(path, from_dir)
    return f"{href}?v={ASSET_BUILD}" if ASSET_BUILD else href


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
    Page(ROOT / "记录.md", OUT / "index.html", "record", "综合旅游攻略记录", "跨城市总览、场景索引、季节索引和路线模板", "#2f6f73", "china travel landscape"),
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
        image_path = PHOTOS / "_sources" / f"source-{digest}{suffix}"
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
        if cached.get("status") == "hit":
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
           "satellite", "landsat", "sentinel", "modis", "nasa", "astronaut", "space")
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
        if cached.get("status") == "hit" and (OUT / cached["path"]).exists():
            return OUT / cached["path"], cached
        if cached.get("status") == "miss":
            return None, None
    if not FETCH_COMMONS_MEDIA:
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
        return raw_path, {
            "status": "hit",
            "path": rel_to(raw_path, OUT),
            "source": info.get("descriptionurl") or info.get("url") or "",
            "license": strip_html(meta.get("LicenseShortName", {}).get("value", "")),
            "artist": strip_html(meta.get("Artist", {}).get("value", "")),
            "query": base_query,
        }

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
            entry = {"status": "hit", "path": rel_to(raw_path, OUT), "source": img_url,
                     "license": "Wikipedia", "artist": "", "query": "wiki:" + name}
            PHOTO_CACHE[cache_key] = entry
            save_photo_cache()
            return raw_path, entry

    # 兜底二：弱相关候选（标题/描述没直接出现城市名，但搜索结果排名靠前）
    raw_path, entry = pick_best(weak_candidates)
    if entry:
        PHOTO_CACHE[cache_key] = entry
        save_photo_cache()
        return raw_path, entry

    PHOTO_CACHE[cache_key] = {"status": "miss", "query": base_query}
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


LINKIFY_SECTION_IDS = {"overview", "quick", "time-cost", "scenes", "seasons", "source-map", "months", "seasonal", "routes", "daytrip-decisions", "checklist"}


def render_item_header(page: Page, node: dict, section_id: str | None, depth: int, anchors: dict[str, str] | None, current_id: str | None) -> tuple[str, str | None]:
    label, body = split_label(node["text"])
    if label:
        text_html = f'<span class="item-label">{inline_markup(label, anchors, current_id)}</span><span class="item-body">{inline_markup(body, anchors, current_id)}</span>'
    else:
        text_html = f'<span class="item-body">{inline_markup(node["text"], anchors, current_id)}</span>'
    if not should_show_item_visual(section_id, depth, node):
        return text_html, None
    title = item_title(node["text"])
    kind = item_kind(section_id, title, node["text"])
    image_path, image_badge, meta = item_image_asset(page, title, kind)
    # 没有真实照片 → 纯文字卡（不放插画、不放自动生成的攻略框）
    if not image_path:
        return text_html, None
    rel = rel_to(image_path, page.output.parent)
    guide_label = "出名店铺 / 吃法" if kind == "food" else "游玩攻略"
    guide = item_summary(node, kind)
    source_title = ""
    if image_badge == "来源图" and meta:
        source_title = f' title="{html.escape("来源网页：" + meta.get("url", ""))}"'
    elif image_badge == "开放图库" and meta:
        source_title = f' title="{html.escape("Wikimedia Commons" + (" / " + meta.get("license", "") if meta.get("license") else ""))}"'
    visual_html = (
        f'<figure class="item-thumb-wrap photo-real">'
        f'<img class="item-thumb" src="{html.escape(rel)}" alt="{html.escape(title)}配图" width="800" height="480" loading="lazy"{source_title}>'
        f'<figcaption>{image_badge}</figcaption>'
        '</figure>'
        '<div class="item-text">'
        f'{text_html}'
        f'<div class="item-guide"><strong>{guide_label}</strong><span>{inline_markup(guide, anchors, current_id)}</span></div>'
        '</div>'
    )
    return visual_html, kind


def render_nodes(nodes: list[dict], page: Page, section_id: str | None, anchor_index: AnchorIndex, depth: int = 0) -> str:
    if not nodes:
        return ""
    # 深层的纯叶子列表（无子项、条目较多）改为多列卡片网格，打散密集文字
    is_leaf_list = depth >= 1 and len(nodes) >= 3 and all(not n.get("children") for n in nodes)
    leaf_cls = " leaf-list" if is_leaf_list else ""
    out = [f'<ul class="md-list depth-{depth}{leaf_cls}">']
    for node in nodes:
        label, body = split_label(node["text"])
        classes = ["list-card"]
        current_id = item_anchor_id(section_id, node) if depth == 0 else None
        link_anchors = anchor_index.terms if section_id in LINKIFY_SECTION_IDS else None
        text_html, kind = render_item_header(page, node, section_id, depth, link_anchors, current_id)
        if kind:
            classes.extend(["visual-card", f"kind-{kind}"])
        if node.get("children"):
            classes.append("has-children")
        if label in FACT_LABELS:
            classes.append("fact")
        id_attr = f' id="{html.escape(current_id)}"' if current_id else ""
        out.append(f'<li{id_attr} class="{" ".join(classes)}">')
        context_actions = poi_action_links_html(page, item_title(node["text"]), section_id, depth)
        child_html = render_nodes(node["children"], page, section_id, anchor_index, depth + 1)
        if kind:
            out.append(f'<div class="visual-layout">{text_html}</div>')
            out.append(context_actions)
            out.append(child_html)
        else:
            out.append(text_html)
            out.append(context_actions)
            out.append(child_html)
        out.append("</li>")
    out.append("</ul>")
    return "\n".join(out)


SECTION_ICON_RULES = [
    (("结论", "总览", "索引", "决策"), "🧭"),
    (("月份", "季节", "全年"), "📅"),
    (("票价", "营业", "时间表"), "🎫"),
    (("夜市", "市场", "商圈", "街区"), "🌃"),
    (("博物馆", "展馆", "展览"), "🏛️"),
    (("美食", "餐厅", "小吃", "吃"), "🍜"),
    (("住宿", "酒店"), "🏨"),
    (("交通", "出行", "地铁"), "🚆"),
    (("温泉",), "♨️"),
    (("自然", "远郊", "周边", "峡", "湖", "山水"), "🌲"),
    (("路线", "线路", "行程"), "🗺️"),
    (("避坑", "取舍", "复核", "提醒", "注意"), "⚠️"),
    (("行前", "准备", "清单", "攻略"), "🎒"),
    (("地图", "分区"), "🗺️"),
    (("景点", "游玩", "核心", "打卡"), "📍"),
]


def section_icon(title: str) -> str:
    for keys, icon in SECTION_ICON_RULES:
        if any(k in title for k in keys):
            return icon
    return "📌"


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
            html_parts.append("</section>")
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
            html_parts.append(f'<section id="{sid}" class="guide-section level-{level}">')
            ico = section_icon(text.strip())
            html_parts.append(f'<h{level}><span class="sec-ico" aria-hidden="true">{ico}</span>{inline_markup(text.strip())}</h{level}>')
            open_section = True
            i += 1
            continue

        if re.match(r"^\s*-\s+", line):
            block: list[str] = []
            while i < len(lines) and (re.match(r"^\s*-\s+", lines[i]) or not lines[i].strip()):
                block.append(lines[i])
                i += 1
            html_parts.append(render_nodes(parse_list(block), page, current_section_id, anchor_index))
            continue

        if line.strip():
            anchors = anchor_index.terms if current_section_id in LINKIFY_SECTION_IDS else None
            html_parts.append(f"<p>{inline_markup(line.strip(), anchors)}</p>")
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


def quick_cards_html(markdown: str, anchor_index: AnchorIndex) -> str:
    heading = "## 快速决策索引" if "## 快速决策索引" in markdown else "## 先看总览"
    section_id = "quick" if heading == "## 快速决策索引" and "quick" in anchor_index.section_ids else "overview"
    nodes = extract_first_nodes_after(markdown, heading, 4)
    cards = []
    for node in nodes:
        title = item_title(node["text"]) or node["text"]
        anchor_id = item_anchor_id(section_id, node)
        href = f"#{anchor_id}" if anchor_id else anchor_index.terms.get(title, f"#{section_id}")
        cards.append(
            '<li>'
            f'<a class="hero-point-link" href="{html.escape(href)}">'
            f'<span>{inline_markup(title)}</span>'
            f'<small>{inline_markup(quick_summary(node))}</small>'
            '</a>'
            '</li>'
        )
    if cards:
        return "\n".join(cards)
    fallback = [
        ("景点", pick_section_href(anchor_index, ["attractions", "seasonal", "nature", "source-map"])),
        ("吃喝", pick_section_href(anchor_index, ["food", "shops", "markets", "source-map"])),
        ("路线", pick_section_href(anchor_index, ["routes", "daytrip-decisions"])),
    ]
    return "\n".join(
        f'<li><a class="hero-point-link" href="{href}"><span>{label}</span><small>跳转到对应攻略区块</small></a></li>'
        for label, href in fallback if href
    )


def pick_section_href(anchor_index: AnchorIndex, candidates: list[str]) -> str | None:
    for sid in candidates:
        if sid in anchor_index.section_ids:
            return f"#{sid}"
    return None


def glass_links_html(anchor_index: AnchorIndex) -> str:
    links = [
        ("景点", "核心景点/季节景观", ["attractions", "seasonal", "nature", "source-map"]),
        ("吃喝", "美食/店铺/市场", ["food", "shops", "markets", "streets", "source-map"]),
        ("路线", "半天/一日/远郊", ["routes", "daytrip-decisions"]),
        ("避坑", "取舍/复核清单", ["warnings", "checklist"]),
    ]
    html_links = []
    for label, desc, candidates in links:
        href = pick_section_href(anchor_index, candidates)
        if href:
            html_links.append(f'<a href="{href}"><strong>{label}</strong><span>{desc}</span></a>')
    return "\n".join(html_links)


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


def hero_gallery_html(page: Page) -> str:
    paths = gallery_image_paths(page)
    if not paths:
        return ""
    images = []
    # 复制一份，配合 translateX(-50%) 动画实现无缝循环滚动。
    for idx, path in enumerate(paths * 2):
        rel = rel_to(path, page.output.parent)
        images.append(
            f'<img src="{html.escape(rel)}" alt="{html.escape(page.title)}流动图片 {idx % len(paths) + 1}" '
            'width="1200" height="675" loading="lazy" decoding="async">'
        )
    return f'<div class="hero-gallery" aria-hidden="true"><div class="gallery-track">{"".join(images)}</div></div>'


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
            if img.exists() and meta and meta.get("status") == "hit":
                with_photo.append((img, p.title.replace("旅游攻略", ""), p.output, p.subtitle))
        random.Random("hero-carousel").shuffle(with_photo)
        entries = with_photo[:14]
    else:
        name = page.title.replace("旅游攻略", "")
        img = IMAGES / f"{page.key}.jpg"
        meta = PHOTO_CACHE.get(f"cityphoto|{page.key}")
        if img.exists() and meta and meta.get("status") == "hit":
            entries.append((img, name, None, page.subtitle))
    return entries


def hero_carousel_html(page: Page) -> str:
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
        )
        inner = f'<img src="{html.escape(rel)}" alt="{html.escape(name)}" width="1280" height="720" loading="{loading}" decoding="async">{cap}'
        if target is not None:
            href = rel_to(target, page.output.parent)
            slides.append(f'<a class="hero-slide{active}" href="{html.escape(href)}">{inner}</a>')
        else:
            slides.append(f'<div class="hero-slide{active}">{inner}</div>')
        dots.append(f'<button class="hero-dot{active}" type="button" data-i="{idx}" aria-label="第 {idx + 1} 张"></button>')
    controls = ""
    if len(entries) > 1:
        controls = (
            '<button class="hero-arrow prev" type="button" aria-label="上一张" data-dir="-1">‹</button>'
            '<button class="hero-arrow next" type="button" aria-label="下一张" data-dir="1">›</button>'
            f'<div class="hero-dots">{"".join(dots)}</div>'
        )
    return (
        '<div class="hero-carousel" id="heroCarousel" data-count="' + str(len(entries)) + '">'
        f'<div class="hero-slides">{"".join(slides)}</div>'
        f'{controls}'
        '</div>'
    )


def hero_quickfind_html(anchor_index: AnchorIndex) -> str:
    links = [
        ("📍", "景点", "核心景点 / 季节景观", ["attractions", "seasonal", "nature", "source-map"]),
        ("🍜", "吃喝", "美食 / 店铺 / 市场", ["food", "shops", "markets", "streets", "source-map"]),
        ("🗺️", "路线", "半天 / 一日 / 远郊", ["routes", "daytrip-decisions"]),
        ("⚠️", "避坑", "取舍 / 复核清单", ["warnings", "checklist"]),
    ]
    cards = []
    for emoji, label, desc, candidates in links:
        href = pick_section_href(anchor_index, candidates)
        if href:
            cards.append(
                f'<a class="quickfind-card" href="{href}">'
                f'<span class="qf-emoji" aria-hidden="true">{emoji}</span>'
                f'<span class="qf-text"><strong>{label}</strong><small>{desc}</small></span></a>'
            )
    if not cards:
        return ""
    return f'<div class="hero-quickfind"><span class="qf-title">快速查找</span><div class="qf-grid">{"".join(cards)}</div></div>'


def nav_html(current: Page) -> str:
    current_out = current.output
    province_groups: list[str] = []
    direct_regions: dict[str, list[tuple[str, str, str]]] = {
        "直辖市": [],
        "特别行政区": [],
    }
    menu_active = False
    for item in NAV_GROUPS:
        if item["kind"] == "link":
            target = OUT / item["href"]
            rel = rel_to(target, current_out.parent)
            active = " active" if target.resolve() == current_out.resolve() else ""
            if item["label"] != "总览":
                group_label = "特别行政区" if item["label"] in SPECIAL_REGIONS else "直辖市"
                direct_regions[group_label].append((item["label"], rel, active))
                menu_active = menu_active or bool(active)
            continue
        group_links = []
        group_active = False
        for label, href in item["items"]:
            target = OUT / href
            rel = rel_to(target, current_out.parent)
            active = " active" if target.resolve() == current_out.resolve() else ""
            group_active = group_active or bool(active)
            group_links.append(f'<a class="destination-city{active}" href="{rel}">{html.escape(label)}</a>')
        menu_active = menu_active or group_active
        province_groups.append(
            '<section class="destination-group">'
            f'<h3>{html.escape(item["label"])}</h3>'
            f'<div>{"".join(group_links)}</div>'
            '</section>'
        )
    top_level_groups = []
    for group_label, links in direct_regions.items():
        if not links:
            continue
        top_level_groups.append(
            '<section class="destination-group">'
            f'<h3>{group_label}</h3><div>'
            + "".join(
                f'<a class="destination-city{active}" href="{html.escape(rel)}">{html.escape(label)}</a>'
                for label, rel, active in links
            )
            + '</div></section>'
        )
    province_groups[0:0] = top_level_groups

    popular_keys = ("beijing", "shanghai", "chengdu", "xian", "hangzhou", "qingdao", "chongqing", "kunming")
    by_key = {page.key: page for page in PAGES}
    quick_links = []
    for key in popular_keys:
        page = by_key.get(key)
        if not page:
            continue
        _, city = split_city_filename(page.source)
        rel = rel_to(page.output, current_out.parent)
        active = " active" if page.output.resolve() == current_out.resolve() else ""
        quick_links.append(f'<a class="destination-quick-link{active}" href="{rel}">{html.escape(city)}</a>')

    city_count = sum(1 for page in PAGES if page.key != "record")
    active_class = " active" if menu_active else ""
    return (
        f'<details class="destination-nav{active_class}">'
        '<summary><span>全国目的地</span>'
        f'<small>{city_count} 个城市</small><i aria-hidden="true"></i></summary>'
        '<div class="destination-panel">'
        '<div class="destination-panel-head"><strong>按省份查找</strong><span>选择城市进入完整攻略</span></div>'
        f'<div class="destination-groups">{"".join(province_groups)}</div>'
        '</div></details>'
        f'<div class="destination-quick" aria-label="热门目的地">{"".join(quick_links)}</div>'
    )


def card_links(current: Page) -> str:
    cards = []
    for page in PAGES:
        if page.key == current.key:
            continue
        rel = rel_to(page.output, current.output.parent)
        cards.append(
            f'<a class="city-card" href="{rel}" style="--accent:{page.accent}">'
            f'<span>{html.escape(page.title)}</span><small>{html.escape(page.subtitle)}</small></a>'
        )
    return "\n".join(cards)


MARKDOWN_CACHE: dict[str, str] = {}
CITY_PROFILE_CACHE: dict[str, dict] = {}


def read_markdown_cached(page: Page) -> str:
    if page.key not in MARKDOWN_CACHE:
        MARKDOWN_CACHE[page.key] = page.source.read_text(encoding="utf-8")
    return MARKDOWN_CACHE[page.key]


def page_location(page: Page) -> tuple[str, str]:
    if page.key == "record":
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
    arrangement = re.search(r"^-\s*适合安排[：:]\s*(.+)$", markdown, re.M)
    arrangement_text = arrangement.group(1) if arrangement else ""
    day_numbers = [int(value) for value in re.findall(r"(\d+)\s*天", arrangement_text)]
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
        5,
    )
    foods = extract_section_titles(markdown, ["## 美食总表", "## 餐厅和店铺", "## 街区、夜市和市场", "## 街区、商圈和夜市"], 5)
    routes = extract_section_titles(markdown, ["## 路线模板", "## 跨城市路线模板"], 3)
    season = city_season_summary(markdown)
    keywords = extract_markdown_keywords(markdown)
    filters = city_filter_metadata(markdown, foods)
    filters["region"] = city_region(province)
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


def city_explorer_html(current: Page) -> str:
    city_pages = [page for page in PAGES if page.key != "record"]
    provinces = []
    for card_index, page in enumerate(city_pages):
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
    for page in city_pages:
        profile = city_profile(page)
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
        if photo_meta and photo_meta.get("status") == "hit":
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
            f'<span>{html.escape(profile["title"])}</span>'
            f'<small>{html.escape(profile["subtitle"])}</small>'
            f'<p><strong>景点</strong>{html.escape(highlights)}</p>'
            f'<p><strong>吃喝</strong>{html.escape(foods)}</p>'
            f'<div class="city-tags">{tag_html}</div>'
            '</div>'
        )
        common_attrs = (
            f'href="{html.escape(rel)}" style="--accent:{page.accent}" '
            f'data-province="{html.escape(profile["province"])}" data-region="{html.escape(profile["region"])}" '
            f'data-season="{html.escape(profile["seasonTags"])}" data-days="{html.escape(profile["daysClass"])}" '
            f'data-theme="{html.escape(profile["themeTags"])}" data-transport="{html.escape(profile["transportTags"])}" '
            f'data-search="{html.escape(search_text)}" data-key="{html.escape(page.key)}" data-index="{card_index}"'
        )
        has_photo = bool(photo_meta and photo_meta.get("status") == "hit")
        if has_photo:
            cards.append(
                f'<a class="city-card rich" {common_attrs}>'
                f'<span class="img-frame">{badge}{fav_btn}{trip_btn}'
                f'<img src="{html.escape(image)}" alt="{html.escape(profile["title"])}缩略图" width="800" height="480" loading="lazy" decoding="async"{img_title}></span>'
                f'{body_html}</a>'
            )
        else:
            # 无真实照片 → 纯文字卡（不放插画）
            cards.append(
                f'<a class="city-card noimg" {common_attrs}>{fav_btn}{trip_btn}{body_html}</a>'
            )
    return (
        '<section class="city-explorer" id="city-explorer">'
        '<div class="city-explorer-head">'
        '<p class="eyebrow">City Finder</p>'
        '<h2>城市快速筛选</h2>'
        '<p>按省份、城市、景点、美食或季节关键词快速定位攻略，先展示最相关的一批结果。</p>'
        '</div>'
        '<div class="city-explorer-tools">'
        f'<div class="province-pills" aria-label="省份筛选">{"".join(filters)}</div>'
        '<div class="city-explorer-row">'
        '<label class="city-explorer-search"><span>筛选城市</span>'
        '<input id="cityExplorerSearch" type="search" placeholder="例如：雪山、夜市、博物馆、春花、避暑"></label>'
        '<button id="randomCity" type="button" class="random-city">🎲 随机一座</button>'
        '</div>'
        '</div>'
        f'<div class="city-grid rich-grid" id="cityExplorer">{"".join(cards)}</div>'
        '<div class="city-explorer-footer">'
        '<p id="cityExplorerSummary" aria-live="polite"></p>'
        '<button id="cityLoadMore" class="city-load-more" type="button">显示更多城市</button>'
        '</div>'
        '</section>'
    )


ATTRACTION_HEADINGS = ["## 核心景点", "## 季节限定景观", "## 自然、远郊和周边", "## 自然和周边"]
FOOD_HEADINGS = ["## 美食总表", "## 餐厅和店铺", "## 街区、夜市和市场", "## 街区、商圈和夜市"]


def home_stats_html() -> str:
    city_pages = [p for p in PAGES if p.key != "record"]
    provinces: set[str] = set()
    spots = 0
    foods = 0
    for p in city_pages:
        provinces.add(city_profile(p)["province"])
        markdown = read_markdown_cached(p)
        for heading in ATTRACTION_HEADINGS:
            spots += len(extract_first_nodes_after(markdown, heading, 999))
        for heading in FOOD_HEADINGS:
            foods += len(extract_first_nodes_after(markdown, heading, 999))
    # 取整到十位，呈现为「约 X+」，避免给人逐条精确统计的错觉
    spots = spots // 10 * 10
    foods = foods // 10 * 10
    stats = [
        (f"{len(city_pages)}", "座", "收录城市攻略"),
        (f"{len(provinces)}", "个", "覆盖省份 / 直辖市"),
        (f"{spots}", "+", "精选景点条目"),
        (f"{foods}", "+", "特色美食条目"),
    ]
    cards = "".join(
        f'<div class="stat-card reveal"><div class="stat-num"><span class="stat-count" data-count="{num}">{html.escape(num)}</span>'
        f'<small>{html.escape(unit)}</small></div>'
        f'<span class="stat-label">{html.escape(label)}</span></div>'
        for num, unit, label in stats
    )
    return (
        '<section class="home-section reveal" id="home-stats" aria-label="数据速览">'
        '<div class="home-section-head"><p class="eyebrow">Overview</p>'
        '<h2>数据速览</h2><p>这份跨城市攻略库目前的覆盖范围，仍在持续扩充。</p></div>'
        f'<div class="home-stats">{cards}</div>'
        '</section>'
    )


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
        return PHOTO_CACHE.get(f"cityphoto|{key}", {}).get("status") == "hit"
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
            f'<img src="{html.escape(img)}" alt="{html.escape(name)}" width="800" height="480" loading="lazy" decoding="async">'
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


def home_modules_html(current: Page) -> tuple[str, str]:
    if current.key != "record":
        return "", ""
    top = home_stats_html() + home_featured_html(current) + home_themes_html()
    return top, home_tools_html()


def city_overview_html(page: Page) -> str:
    """城市页顶部「速览名片」：所在 / 适宜季节 / 必看景点 / 必吃美食 + 收藏、加入行程。"""
    if page.key == "record":
        return ""
    prof = city_profile(page)
    province, season = prof["province"], prof["season"]
    highlights = [h for h in prof["highlights"] if h][:6]
    foods = [f for f in prof["foods"] if f][:6]
    href = rel_to(page.output, OUT)  # 相对站点根，供收藏/行程在用户中心回链
    data_attrs = (
        f'data-key="{html.escape(page.key)}" data-name="{html.escape(prof["title"])}" '
        f'data-href="{html.escape(href)}" data-sub="{html.escape(prof["subtitle"])}"'
    )
    hl = "".join(f"<em>{html.escape(h)}</em>" for h in highlights) or "<em>见下方正文</em>"
    fd = "".join(f'<em class="food">{html.escape(f)}</em>' for f in foods) or "<em>见下方正文</em>"
    return (
        '<section class="city-overview reveal" aria-label="城市速览">'
        '<div class="co-facts">'
        f'<div class="co-cell"><span class="co-k">所在</span><span class="co-v">{html.escape(province)}</span></div>'
        f'<div class="co-cell"><span class="co-k">适宜季节</span><span class="co-v">{html.escape(season)}</span></div>'
        '</div>'
        f'<div class="co-block"><span class="co-bk">📍 必看景点</span><div class="co-chips">{hl}</div></div>'
        f'<div class="co-block"><span class="co-bk">🍜 必吃美食</span><div class="co-chips">{fd}</div></div>'
        '<div class="co-actions">'
        f'<button class="co-fav" type="button" {data_attrs}>☆ 收藏</button>'
        f'<button class="co-trip" type="button" {data_attrs}>＋ 加入行程</button>'
        f'<button class="co-share" type="button" data-share-title="{html.escape(prof["title"])}" '
        f'aria-label="分享{html.escape(prof["title"])}" title="分享当前城市攻略">↗ 分享</button>'
        '</div>'
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
    if page.key == "record" or depth != 0 or section_id not in {"attractions", "museums", "seasonal"}:
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
    if page.key == "record":
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


def mobile_quickbar_html(current: Page, anchor_index: AnchorIndex) -> str:
    home_href = rel_to(OUT / "index.html", current.output.parent)
    items = [
        ("首页", home_href),
        ("搜索", "#guideSearch"),
        ("景点", pick_section_href(anchor_index, ["attractions", "seasonal", "nature", "source-map"])),
        ("吃喝", pick_section_href(anchor_index, ["food", "shops", "markets", "streets", "source-map"])),
        ("路线", pick_section_href(anchor_index, ["routes", "daytrip-decisions"])),
    ]
    links = "".join(
        f'<a href="{html.escape(href)}">{html.escape(label)}</a>'
        for label, href in items if href
    )
    return f'<nav class="mobile-quickbar" aria-label="移动端快捷入口">{links}</nav>'


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


def source_media_html(markdown: str, page: Page) -> str:
    urls = extract_urls(markdown)
    if not urls:
        return ""
    media_cards: list[str] = []
    source_cards: list[str] = []
    image_re = re.compile(r"\.(?:jpg|jpeg|png|webp|gif)(?:\?|$)", re.I)
    video_re = re.compile(r"\.(?:mp4|webm|mov)(?:\?|$)", re.I)

    source_candidates = PAGE_SOURCE_MEDIA.get(page.key, [])
    for source_media in source_candidates:
        url = source_media.get("url", "")
        label = source_label(url) if url else "来源媒体"
        local_path = source_media.get("path", "")
        source_video = source_media.get("embed") or source_media.get("video", "")
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
        elif image_re.search(url) and len(media_cards) < 6:
            media_cards.append(
                '<article class="media-card">'
                f'<img src="{html.escape(url)}" alt="{html.escape(label)}" width="1200" height="675" loading="lazy">'
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
    source_date = date.fromtimestamp(page.source.stat().st_mtime).isoformat() if page.source.exists() else "待核验"
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
    photo_path, _ = city_photo_for(page)
    if photo_path and save_cover_image(photo_path, path, (width, height)):
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
    if page.key == "record" or len(markdown) >= 4000:
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
    if page.key == "record":
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


def site_header_html(page: Page, active_key: str = "") -> str:
    home = rel_to(OUT / "index.html", page.output.parent)
    user = rel_to(OUT / "user.html", page.output.parent)
    roadtrip = rel_to(OUT / "roadtrip.html", page.output.parent)
    destinations = rel_to(OUT / "destinations.html", page.output.parent)
    themes = rel_to(OUT / "themes.html", page.output.parent)
    city_guides = rel_to(OUT / "city-guides.html", page.output.parent)
    tools = rel_to(OUT / "tools.html", page.output.parent)
    items = [
        ("home", "首页", home),
        ("destinations", "目的地", destinations),
        ("themes", "主题玩法", themes),
        ("cities", "城市攻略", city_guides),
        ("roadtrip", "自驾路书", roadtrip),
        ("tools", "实用工具", tools),
    ]
    links = "".join(
        f'<a class="header-link{" active" if k == active_key else ""}" href="{html.escape(h)}">{lbl}</a>'
        for k, lbl, h in items
    )
    user_active = " active" if active_key == "user" else ""
    mobile_links = links + f'<a class="header-link{user_active}" href="{user}">用户中心</a>'
    return f"""  <header class="site-header">
    <div class="header-bar">
      <button class="nav-toggle" id="navToggle" type="button" aria-expanded="false" aria-controls="topNav" aria-label="城市导航菜单">☰</button>
      <a class="header-home" href="{home}"><span class="brand-mark" aria-hidden="true">🧭</span><span class="brand-name">游记<b>地图</b></span></a>
      <nav class="header-links" aria-label="功能导航">{links}</nav>
      <div class="global-search">
        <label class="global-search-box">
          <span>全站搜索</span>
          <input id="siteSearch" type="search" placeholder="搜索城市、景点、美食、季节">
        </label>
        <div class="site-search-results" id="siteSearchResults" hidden></div>
      </div>
      <a class="header-user{user_active}" href="{user}" aria-label="用户中心">
        <span class="user-avatar" id="headerAvatar" aria-hidden="true">👤</span>
        <span class="header-user-name" id="headerUserName">用户中心</span>
      </a>
    </div>
    <nav class="top-nav" id="topNav" aria-label="城市导航">
      {nav_html(page)}
      <div class="mobile-primary-nav" aria-label="移动端功能导航">{mobile_links}</div>
    </nav>
  </header>"""


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
        md = (ROOT / "记录.md").read_text(encoding="utf-8")
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


def footer_html() -> str:
    return (
        '  <footer class="site-footer">\n'
        '    <p>本页为个人离线旅游攻略整理，内容来自公开网络资料的归纳，仅供出行参考；'
        '出发前请按官方景区、本地文旅、票务系统复核时间、票价与预约信息。</p>\n'
        '    <p>城市与景点照片来自 <a href="https://commons.wikimedia.org/" target="_blank" rel="noreferrer">Wikimedia Commons</a> '
        '等开放图库（遵循各自的 CC 授权）；无照片处使用程序生成的示意插画。</p>\n'
        '  </footer>'
    )


def shell_page_html(
    page: Page,
    title: str,
    main_html: str,
    active_key: str,
    extra_head: str = "",
    extra_scripts: str = "",
) -> str:
    """通用页壳：复用 header / footer / 资源，用于用户中心等非攻略页面。"""
    site_root = rel_to(OUT, page.output.parent)
    return "\n".join(line.rstrip() for line in f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(page.subtitle)}">
  <meta name="theme-color" content="{page.accent}">
  <link rel="manifest" href="{rel_to(OUT / 'manifest.webmanifest', page.output.parent)}">
  <link rel="apple-touch-icon" href="{rel_to(ASSETS / 'icon-180.png', page.output.parent)}">
  <link rel="stylesheet" href="{asset_href(ASSETS / 'travel.css', page.output.parent)}">
{extra_head}
  <noscript><style>.reveal{{opacity:1!important;transform:none!important}}</style></noscript>
  <script>try{{var s=JSON.parse(localStorage.getItem("tay_settings")||"{{}}"),r=document.documentElement;if(s.vibrancy)r.setAttribute("data-vibrancy",s.vibrancy);if(s.font)r.setAttribute("data-font",s.font);if(s.motion)r.setAttribute("data-motion",s.motion);var t=s.theme||"auto";if(t==="auto")t=(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches)?"dark":"light";r.setAttribute("data-theme",t);}}catch(e){{}}</script>
</head>
<body id="top" data-site-root="{html.escape(site_root)}" style="--accent:{page.accent}">
{site_header_html(page, active_key)}
  <main>
{main_html}
  </main>
{footer_html()}
  <button class="to-top" id="toTop" type="button" aria-label="返回顶部" title="返回顶部">↑</button>
  <script src="{asset_href(ASSETS / 'search-index.js', page.output.parent)}"></script>
  <script src="{asset_href(ASSETS / 'travel.js', page.output.parent)}"></script>
{extra_scripts}
</body>
</html>
""".splitlines()) + "\n"


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
    <nav class="user-tabs" id="userTabs" aria-label="用户中心导航">
      <button class="user-tab active" data-tab="profile" type="button">个人信息</button>
      <button class="user-tab" data-tab="favorites" type="button">我的收藏</button>
      <button class="user-tab" data-tab="history" type="button">最近浏览</button>
      <button class="user-tab" data-tab="trip" type="button">我的行程</button>
      <button class="user-tab" data-tab="roadbooks" type="button">自驾路书</button>
      <button class="user-tab" data-tab="tools" type="button">旅行工具</button>
      <button class="user-tab" data-tab="settings" type="button">设置</button>
      <button class="user-tab" data-tab="guide" type="button">使用介绍</button>
      <button class="user-tab" data-tab="changelog" type="button">更新说明</button>
    </nav>
    <div class="user-panels">
      <section class="user-panel guide-section" data-panel="profile">
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
      <section class="user-panel guide-section" data-panel="favorites" hidden>
        <h2>我的收藏</h2>
        <p class="panel-hint">在任意城市卡片右上角点 ☆ 即可收藏，这里集中管理。</p>
        <div class="fav-grid" id="favGrid"></div>
        <div class="fav-empty" id="favEmpty">还没有收藏城市。去 <a href="city-guides.html">城市攻略</a> 逛逛，点 ☆ 收藏吧。</div>
      </section>
      <section class="user-panel guide-section" data-panel="history" data-storage-key="tay_recent" hidden>
        <h2>最近浏览</h2>
        <p class="panel-hint">浏览记录只保存在当前浏览器，最多保留最近 12 座城市。</p>
        <div class="fav-grid" id="historyList"></div>
        <div class="fav-empty" id="historyEmpty">还没有浏览记录。去 <a href="city-guides.html">城市攻略</a> 选择第一座城市。</div>
        <button class="ghost-btn" id="historyClear" type="button" hidden>清空浏览记录</button>
      </section>
      <section class="user-panel guide-section" data-panel="trip" hidden>
        <h2>我的行程</h2>
        <p class="panel-hint">在城市卡片右上角点 ＋ 加入行程，这里可排序、估算节奏，规划一条出行线路。</p>
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
      <section class="user-panel guide-section" data-panel="roadbooks" hidden>
        <h2>已保存的自驾路书</h2>
        <p class="panel-hint">路书只保存在当前浏览器。打开后可以重新计算路线、打印或导出 Markdown。</p>
        <div class="roadbook-list" id="roadbookList"></div>
        <div class="fav-empty" id="roadbookEmpty">还没有保存路书。去 <a href="roadtrip.html">自驾路书生成器</a> 建立第一条路线。</div>
      </section>
      <section class="user-panel guide-section travel-tools-panel" data-panel="tools" hidden>
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
      <section class="user-panel guide-section" data-panel="settings" hidden>
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
      </section>
      <section class="user-panel guide-section" data-panel="guide" hidden>
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
      <section class="user-panel guide-section" data-panel="changelog" hidden>
        <h2>更新说明</h2>
        <p class="panel-hint">本站的内容归并与城市扩充记录。</p>
        {changelog}
      </section>
    </div>"""


def build_user_page() -> None:
    page = Page(ROOT / "记录.md", OUT / "user.html", "user", "用户中心 · 游记地图",
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
            Page(ROOT / "记录.md", OUT / "destinations.html", "destinations", "目的地 · 游记地图",
                 "按地区、季节、天数、主题和交通方式挑选下一站。", "#19756e", ""),
            "Destinations", "从条件开始，找到下一座城市", "按地区、季节、天数、主题和交通方式组合筛选；结果直接对应可收藏、可加入行程的完整城市攻略。",
            [(str(city_count), "座城市攻略"), (str(province_count), "个地区覆盖")],
            lambda page: home_finder_html(page) + city_explorer_html(page),
        ),
        (
            Page(ROOT / "记录.md", OUT / "themes.html", "themes", "主题玩法 · 游记地图",
                 "从旅行偏好出发，找到值得专程前往的城市。", "#b96733", ""),
            "Travel Themes", "用一份兴趣清单，决定一段旅程", "亲子、博物馆、山水、历史、美食、避暑、冬季与周末短途均可直接筛选；每个结果都保留到城市攻略的入口。",
            [("8", "种旅行主题"), (str(city_count), "座可筛选城市")],
            lambda page: home_themes_html() + city_explorer_html(page),
        ),
        (
            Page(ROOT / "记录.md", OUT / "city-guides.html", "cities", "城市攻略 · 游记地图",
                 "用关键词、省份和随机发现快速进入可执行的城市攻略。", "#295f89", ""),
            "City Guides", "全国城市攻略，按你的方式找", "每张卡片都包含季节、重点景点与代表美食，并支持收藏、加入行程和随机发现。",
            [(str(city_count), "座城市攻略"), ("本地保存", "收藏与行程")],
            lambda page: city_explorer_html(page),
        ),
        (
            Page(ROOT / "记录.md", OUT / "tools.html", "tools", "实用工具 · 游记地图",
                 "把行程节奏、季节选择和出行准备变成可执行的小决定。", "#85662b", ""),
            "Travel Toolkit", "出发前，把关键决定做清楚", "这些工具不涉及购买或支付。个人数据仅保存在当前浏览器，也可以在用户中心统一管理。",
            [("离线可用", "本机浏览器保存"), ("0", "站内消费入口")],
            lambda page: home_tools_html(),
        ),
    ]
    for page, eyebrow, title, subtitle, facts, body_builder in pages:
        main = catalog_masthead(eyebrow, title, subtitle, facts) + body_builder(page)
        page.output.write_text(shell_page_html(page, page.title, main, page.key), encoding="utf-8")


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
            "updatedAt": date.fromtimestamp(page.source.stat().st_mtime).isoformat(),
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
            <div class="rt-field-grid">
              <label class="rt-field"><span>每日驾驶上限</span><select id="rtMaxDailyHours"><option value="3">3 小时</option><option value="4">4 小时</option><option value="5" selected>5 小时</option><option value="6">6 小时</option><option value="8">8 小时</option></select></label>
              <label class="rt-field"><span>路线策略</span><select id="rtRouteStrategy"><option value="standard">综合推荐</option><option value="fast">时间优先</option><option value="toll">少收费</option><option value="nohighway">少走高速</option></select></label>
              <label class="rt-field"><span>旅行主题</span><select id="rtTheme"><option value="综合">综合</option><option value="自然风景">自然风景</option><option value="人文历史">人文历史</option><option value="地方美食">地方美食</option><option value="亲子轻松">亲子轻松</option><option value="摄影">摄影</option></select></label>
              <label class="rt-field"><span>车辆类型</span><select id="rtVehicle"><option value="gas">燃油车</option><option value="phev">插电混动</option><option value="ev">纯电动车</option></select></label>
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
            <button class="rt-submit" id="rtGenerate" type="submit">生成自驾路书</button>
          </form>
        </aside>
        <section class="rt-stage">
          <div class="rt-map-frame">
            <div class="rt-map" id="rtMap"><div class="rt-map-empty"><div class="rt-route-sketch"><i></i><b></b><i></i></div><div><strong>路线地图</strong><p>生成路书后显示路线状态；配置地图服务后显示真实路网。</p></div></div></div>
            <div class="rt-map-status" id="rtMapStatus">离线模式可直接使用；地图服务尚未配置。</div>
          </div>
          <div class="rt-result-actions">
            <button class="rt-action primary" id="rtSave" type="button" disabled>保存路书</button>
            <button class="rt-action" id="rtExport" type="button" disabled>导出 Markdown</button>
            <button class="rt-action" id="rtPrint" type="button" disabled>打印</button>
            <span class="rt-save-tip" id="rtSaveTip" hidden>已保存到本机</span>
          </div>
          <div class="rt-results" id="rtResults" aria-live="polite"><div class="rt-empty-state"><strong>尚未生成路书</strong><span>填写左侧条件后开始计算。</span></div></div>
        </section>
      </div>
    </section>"""


def build_roadtrip_page() -> None:
    page = Page(ROOT / "记录.md", OUT / "roadtrip.html", "roadtrip", "自驾路书 · 游记地图",
                "自驾路线、逐日安排、预算和风险清单", "#176b5d", "")
    head = f'  <link rel="stylesheet" href="{asset_href(ASSETS / "roadtrip.css", page.output.parent)}">'
    scripts = "\n".join([
        f'  <script src="{asset_href(ASSETS / "roadtrip-config.js", page.output.parent)}"></script>',
        f'  <script src="{asset_href(ASSETS / "roadtrip-data.js", page.output.parent)}"></script>',
        f'  <script src="{asset_href(ASSETS / "roadtrip-core.js", page.output.parent)}"></script>',
        f'  <script src="{asset_href(ASSETS / "roadtrip-app.js", page.output.parent)}"></script>',
    ])
    output = shell_page_html(page, page.title, roadtrip_body(), "roadtrip", head, scripts)
    page.output.write_text(output, encoding="utf-8")


def build_roadtrip_assets() -> None:
    for name in ("roadtrip-core.js", "roadtrip-app.js", "roadtrip.css"):
        shutil.copyfile(ROOT / "tools" / name, ASSETS / name)
    (ASSETS / "roadtrip-data.js").write_text(roadtrip_data_js(), encoding="utf-8")
    config_path = ASSETS / "roadtrip-config.js"
    if not config_path.exists():
        config_path.write_text(
            'window.TRAVEL_ROADTRIP_CONFIG = {\n'
            '  amapJsKey: "",\n'
            '  amapSecurityCode: ""\n'
            '};\n',
            encoding="utf-8",
        )


def city_photo_count(page: Page) -> int:
    photo_dir = PHOTOS / page.key
    if not photo_dir.exists():
        return 0
    return int((photo_dir / "scenery-01.jpg").exists())


def build_content_audit() -> None:
    load_photo_cache()
    rows = []
    for page in PAGES:
        if page.key == "record":
            continue
        markdown = read_markdown_cached(page)
        effective_markdown = markdown + reinforcement_appendix(page, markdown)
        profile = city_profile(page)
        source_count = len(extract_urls(markdown))
        photo_count = city_photo_count(page)
        cover = IMAGES / f"{page.key}.jpg"
        cover_size = cover.stat().st_size if cover.exists() else 0
        issues = []
        if len(effective_markdown) < 3000:
            issues.append("内容偏短")
        if source_count < 2:
            issues.append("来源偏少")
        if photo_count < 1:
            issues.append("正文图片偏少")
        if cover_size and cover_size < 12000:
            issues.append("封面疑似占位")
        if not issues:
            issues.append("基础完整")
        rows.append({
            "title": profile["title"],
            "province": profile["province"],
            "path": rel_to(page.output, ROOT),
            "chars": len(effective_markdown),
            "sources": source_count,
            "photos": photo_count,
            "cover_kb": round(cover_size / 1024, 1) if cover_size else 0,
            "issues": "、".join(issues),
        })

    weak = [row for row in rows if row["issues"] != "基础完整"]
    weak.sort(key=lambda row: (row["issues"].count("、"), -row["sources"], row["chars"]), reverse=True)
    lines = [
        "# 内容与图片体检",
        "",
        f"> 生成日期：{date.today().isoformat()}",
        f"> 城市页：{len(rows)}；需要优先补充：{len(weak)}。",
        "",
        "## 优先处理清单",
        "",
        "| 城市 | 省份 | 字数 | 来源 | 图片 | 封面 KB | 问题 |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in weak[:80]:
        lines.append(
            f"| [{row['title']}]({row['path']}) | {row['province']} | {row['chars']} | "
            f"{row['sources']} | {row['photos']} | {row['cover_kb']} | {row['issues']} |"
        )
    lines.extend([
        "",
        "## 补充原则",
        "",
        "- 先补官方文旅、景区官网、博物馆官网和主流购票平台；再补社媒高频玩法。",
        "- 门票、开放时间、预约和交通管制必须标注来源和更新时间。",
        "- 图片优先使用本地实拍或可确认授权来源；新增图片记录来源，避免热链。",
        "- 内容短但已有清晰官方来源的城市优先扩充路线、避坑和分区动线。",
    ])
    (ROOT / "内容与图片体检.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        "1. 打开城市页的“联网核验入口”。",
        "2. 先核对官方开放时间、门票、预约和交通，再看攻略平台路线。",
        "3. 把确认后的新增内容写入 `城市\\*.md` 的对应章节。",
        "4. 新增来源写入该城市 Markdown 末尾的“来源参考”。",
        "5. 图片放入 `assets\\photos\\城市slug\\` 或通过现有图片抓取流程补充。",
        "6. 运行 `重新生成网页.bat`，再运行 `python tools\\validate_travel_site.py`。",
    ]
    (ROOT / "资料来源与更新规则.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_project_readme() -> None:
    readme = """# 游记地图 · 旅游攻略网页

这是一个自包含静态旅游攻略站点。源内容在 `城市\\*.md` 和 `记录.md`，网页由 `tools\\build_travel_html.py` 统一生成。

## 常用命令

```powershell
python -X utf8 tools\\build_travel_html.py
python -X utf8 tools\\validate_travel_site.py
python -m http.server 8765
```

## 维护方式

- 修改攻略正文：编辑 `城市\\*.md`。
- 新增城市：新增城市 Markdown，必要时补 `tools\\city-page-meta.json`。
- 补充图片：优先放到 `assets\\photos\\城市slug\\`，重新生成后进入页面相册和审计。
- 复核资料：查看城市页“联网核验入口”，再把确认后的链接写进“来源参考”。
- 查看薄弱项：打开 `内容与图片体检.md`。

## 发布与公开地址

公开站点是 GitHub Pages：<https://shimmerjoe.github.io/youji-ditu/>。

每次维护完成后，必须把本地生成结果同步到该公开地址；不能只在本地验收后就声明完成。发布顺序如下：

1. 运行生成与校验：`python -X utf8 tools\\build_travel_html.py`、`python -X utf8 -m unittest discover -s tools -p 'test_*.py'`、`python -X utf8 tools\\validate_travel_site.py`。
2. 检查变更后提交并推送：`git add -A`、`git commit -m "..."`、`git push origin main`。
3. 等待 GitHub Pages 更新，打开上述公开地址，核对本次内容、脚本版本和移动端导航均已生效；公开地址未核验前，发布不算完成。

公开站点与 `D:\\2Life\\1Travel\\Travel_ayuan` 的已生成内容应保持同一提交版本。若发布失败，保留本地变更并记录失败原因，不要以本地预览替代公开验收。

## 自驾路书与地图配置

`roadtrip.html` 默认可以离线生成分天、预算、风险、保存和 Markdown 导出。若需真实地图、路网里程、预计时间和道路收费：

1. 在高德开放平台创建“Web 端（JS API）”应用并取得 JS Key 与安全密钥。
2. 编辑 `assets\\roadtrip-config.js`：

```javascript
window.TRAVEL_ROADTRIP_CONFIG = {
  amapJsKey: "你的 JS API Key",
  amapSecurityCode: "你的安全密钥"
};
```

3. 通过本地 HTTP 服务器预览，不能直接双击 HTML 测试地图。

生成器只会在配置文件不存在时创建空配置，后续重新生成不会覆盖已填写内容。不要把高德 Web 服务私钥写进前端配置。

## 生成结果

- `index.html`：首页工作台。
- `roadtrip.html`：自驾路线、逐日安排、参考预算和风险清单。
- `cities\\*.html`：城市攻略页。
- `assets\\travel.css`、`assets\\travel.js`：由生成器输出。
- `assets\\search-index.js`：全站搜索索引。
- `assets\\roadtrip-*.js`、`assets\\roadtrip.css`：自驾路书算法、城市数据、运行时配置和页面交互。
- `user.html`：本地用户中心。
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def page_html(page: Page, markdown: str) -> str:
    if page.key == "record":
        markdown = strip_author_sections(markdown)
    title = extract_title(markdown, page.title)
    # 底部来源抽屉用完整 markdown（含「来源参考」里的链接）
    build_source_media_index(page, markdown)
    # 正文渲染时剥离来源类章节，避免与底部「资料来源」重复
    content_md = strip_sections(markdown, SOURCE_SECTION_HEADINGS) + reinforcement_appendix(page, markdown)
    anchor_index = collect_anchor_index(content_md)
    body, toc = render_markdown(content_md, page, anchor_index)
    quick_cards = quick_cards_html(content_md, anchor_index)
    if not quick_cards:
        quick_cards = '<li><a class="hero-point-link" href="#overview"><span>开始浏览</span><small>按目录查看景点、吃喝、路线和避坑。</small></a></li>'
    image_url = rel_to(IMAGES / f"{page.key}.jpg", page.output.parent)
    carousel = hero_carousel_html(page)
    quickfind = hero_quickfind_html(anchor_index)
    gallery_section = guide_gallery_html(page)
    media_section = source_media_html(markdown, page)
    city_explorer = city_explorer_html(page)
    home_top, home_tools = home_modules_html(page)
    home_finder = home_finder_html(page)
    city_overview = city_overview_html(page)
    research_panel = research_panel_html(page)
    mobile_quickbar = mobile_quickbar_html(page, anchor_index)
    home_href = rel_to(OUT / "index.html", page.output.parent)
    site_root = rel_to(OUT, page.output.parent)
    toc_links = "\n".join(
        f'<a class="toc-level-{level}" href="#{sid}">{html.escape(text)}</a>'
        for level, text, sid in toc
    )
    city_links = card_links(page)
    return "\n".join(line.rstrip() for line in f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(page.subtitle)}">
  <meta name="theme-color" content="{page.accent}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(page.subtitle)}">
  <meta property="og:image" content="{image_url}">
  <link rel="manifest" href="{rel_to(OUT / 'manifest.webmanifest', page.output.parent)}">
  <link rel="apple-touch-icon" href="{rel_to(ASSETS / 'icon-180.png', page.output.parent)}">
  <link rel="stylesheet" href="{asset_href(ASSETS / 'travel.css', page.output.parent)}">
  <noscript><style>.reveal{{opacity:1!important;transform:none!important}}</style></noscript>
  <script>try{{var s=JSON.parse(localStorage.getItem("tay_settings")||"{{}}"),r=document.documentElement;if(s.vibrancy)r.setAttribute("data-vibrancy",s.vibrancy);if(s.font)r.setAttribute("data-font",s.font);if(s.motion)r.setAttribute("data-motion",s.motion);var t=s.theme||"auto";if(t==="auto")t=(window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches)?"dark":"light";r.setAttribute("data-theme",t);}}catch(e){{}}</script>
</head>
<body id="top" data-site-root="{html.escape(site_root)}" style="--accent:{page.accent}; --hero-image:url('{image_url}')">
{site_header_html(page, "home" if page.key == "record" else "")}
  <main>
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Travel Guide</p>
        <h1>{html.escape(title)}</h1>
        <p class="subtitle">{html.escape(page.subtitle)}</p>
        <ul class="hero-points">
          {quick_cards}
        </ul>
      </div>
      <div class="hero-stage">
        {carousel}
        {quickfind}
      </div>
    </section>
    {home_finder}
    {city_overview}
    {research_panel}
    {home_top}
    {city_explorer}
    {home_tools}
    <section class="tool-bar">
      <label class="search-box">
        <span>搜索</span>
        <input id="guideSearch" type="search" placeholder="输入景点、店铺、路线或月份">
      </label>
      <button id="expandAll" type="button">清空搜索</button>
      <button id="printPage" type="button">打印/另存 PDF</button>
    </section>
    <div class="layout">
      <aside class="sidebar">
        <div class="sidebar-panel">
          <h2>目录</h2>
          <div class="toc">{toc_links}</div>
        </div>
        <div class="sidebar-panel">
          <h2>其他攻略</h2>
          <div class="city-grid mini">{city_links}</div>
        </div>
      </aside>
      <article class="content" id="guideContent">
        {body}
      </article>
    </div>
    {gallery_section}
    {media_section}
  </main>
{footer_html()}
  {mobile_quickbar}
  <button class="to-top" id="toTop" type="button" aria-label="返回顶部" title="返回顶部">↑</button>
  <script src="{asset_href(ASSETS / 'search-index.js', page.output.parent)}"></script>
  <script src="{asset_href(ASSETS / 'travel.js', page.output.parent)}"></script>
</body>
</html>
""".splitlines()) + "\n"


CSS = r"""
:root {
  color-scheme: light;
  --bg: #f1f6f7;
  --paper: rgba(255, 255, 255, 0.94);
  --ink: #16212b;
  --muted: #58646f;
  --line: rgba(20, 35, 45, 0.12);
  --hairline: rgba(20, 35, 45, 0.07);
  --accent: #0f9e8c;
  --accent-deep: color-mix(in srgb, var(--accent) 72%, #06201d);
  --accent-soft: color-mix(in srgb, var(--accent) 14%, #ffffff);
  --accent-tint: color-mix(in srgb, var(--accent) 7%, #ffffff);
  /* 多彩点缀色 —— 让全站活力四射 */
  --c1: #ff6b4a;
  --c2: #ffb020;
  --c3: #21c08a;
  --c4: #3a86ff;
  --c5: #8b5cf6;
  --c6: #ff5d8f;
  --sky: #3a86ff;
  --sun: #ffb020;
  --gold: #f0a72e;
  --leaf: #21c08a;
  --berry: #ff5d8f;
  --food: #ff6b4a;
  --radius: 16px;
  --radius-sm: 10px;
  --radius-lg: 24px;
  --shadow-sm: 0 4px 14px rgba(26, 40, 50, 0.08);
  --shadow: 0 16px 40px rgba(26, 40, 50, 0.14);
  --shadow-lg: 0 28px 64px rgba(26, 40, 50, 0.2);
  --ease: cubic-bezier(0.22, 0.61, 0.36, 1);
  --fs: 1;
  font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", Arial, sans-serif;
  font-size: calc(16px * var(--fs));
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

/* 设置面板：配色活力度 / 字号 / 动效 */
html[data-vibrancy="calm"] body { filter: saturate(0.72); }
html[data-vibrancy="vivid"] body { filter: saturate(1.24) contrast(1.02); }
html[data-font="s"] { --fs: 0.92; }
html[data-font="l"] { --fs: 1.12; }
html[data-motion="off"] *, html[data-motion="off"] *::before, html[data-motion="off"] *::after {
  animation: none !important;
  transition: none !important;
  scroll-behavior: auto !important;
}
html[data-motion="off"] .reveal { opacity: 1 !important; transform: none !important; }

/* ===== 深色模式 ===== */
html[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0f1517;
  --paper: rgba(26, 33, 36, 0.92);
  --ink: #e9eeec;
  --muted: #9db0ab;
  --line: rgba(255, 255, 255, 0.13);
  --hairline: rgba(255, 255, 255, 0.07);
  --accent: #2bb6a4;
  --accent-deep: color-mix(in srgb, var(--accent) 78%, #ffffff);
  --accent-soft: color-mix(in srgb, var(--accent) 26%, #18201f);
  --accent-tint: color-mix(in srgb, var(--accent) 14%, #161d1f);
  --shadow-sm: 0 4px 14px rgba(0, 0, 0, 0.4);
  --shadow: 0 16px 42px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 26px 60px rgba(0, 0, 0, 0.6);
}
html[data-theme="dark"] body {
  background:
    radial-gradient(circle at 12% 8%, rgba(43,182,164,.12), transparent 30vw),
    radial-gradient(circle at 88% 6%, rgba(255,107,74,.08), transparent 26vw),
    linear-gradient(160deg, #0f1517 0%, #121b1c 55%, #0f1517 100%);
}
html[data-theme="dark"] .site-header { background: rgba(18, 25, 27, 0.85); }
html[data-theme="dark"] .guide-section,
html[data-theme="dark"] .home-section,
html[data-theme="dark"] .city-explorer,
html[data-theme="dark"] .source-media {
  background: linear-gradient(135deg, #1a2225, #161d1f);
}
html[data-theme="dark"] .sidebar-panel,
html[data-theme="dark"] .stat-card,
html[data-theme="dark"] .theme-card,
html[data-theme="dark"] .tool-card,
html[data-theme="dark"] .media-card,
html[data-theme="dark"] .city-card,
html[data-theme="dark"] .city-card.rich,
html[data-theme="dark"] .list-card,
html[data-theme="dark"] .source-link,
html[data-theme="dark"] .hero-points li,
html[data-theme="dark"] .header-home,
html[data-theme="dark"] .nav-link,
html[data-theme="dark"] .nav-group summary,
html[data-theme="dark"] .nav-menu,
html[data-theme="dark"] .site-search-results,
html[data-theme="dark"] .mobile-quickbar,
html[data-theme="dark"] .mobile-quickbar a,
html[data-theme="dark"] input[type="search"],
html[data-theme="dark"] .tool-card input,
html[data-theme="dark"] .tool-card select,
html[data-theme="dark"] button,
html[data-theme="dark"] .tool-chip,
html[data-theme="dark"] .tool-output {
  background: #1b2326;
  color: var(--ink);
}
html[data-theme="dark"] .list-card,
html[data-theme="dark"] .visual-card,
html[data-theme="dark"] .item-guide,
html[data-theme="dark"] .glass-panel {
  background: rgba(255, 255, 255, 0.045);
}
html[data-theme="dark"] .glass-panel { -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); }
html[data-theme="dark"] .stat-card { background: linear-gradient(160deg, #1d262a, var(--accent-tint)); }
html[data-theme="dark"] .quickfind-card { background: rgba(255,255,255,0.05); }
html[data-theme="dark"] a { color: color-mix(in srgb, var(--accent) 70%, #fff); }
html[data-theme="dark"] .item-label,
html[data-theme="dark"] .city-tags em,
html[data-theme="dark"] .section-count { color: var(--accent-deep); }
html[data-theme="dark"] code { background: rgba(255,255,255,0.1); }
html[data-theme="dark"] .to-top { color: #fff; }
html[data-theme="dark"] .hero h1 {
  background: linear-gradient(120deg, #eef3f1 38%, color-mix(in srgb, var(--accent) 75%, #fff));
  -webkit-background-clip: text; background-clip: text;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }

/* 跳到主要内容（仅键盘聚焦时显示） */
.skip-link {
  position: fixed;
  top: -60px;
  left: 12px;
  z-index: 300;
  padding: 10px 16px;
  border-radius: var(--radius-sm);
  background: var(--accent-deep);
  color: #fff;
  font-weight: 700;
  box-shadow: var(--shadow);
  transition: top .2s var(--ease);
}
.skip-link:focus { top: 12px; text-decoration: none; }

/* 图片灯箱 */
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 400;
  display: none;
  place-items: center;
  padding: 24px;
  background: rgba(10, 16, 16, 0.86);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  cursor: zoom-out;
}
.lightbox.open { display: grid; }
.lightbox img {
  max-width: min(96vw, 1400px);
  max-height: 92vh;
  border-radius: 12px;
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.55);
}
.lightbox-close {
  position: fixed;
  top: 18px;
  right: 18px;
  min-height: 44px;
  width: 44px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  font-size: 18px;
}

/* 顶部阅读进度条 */
.read-progress {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  width: 0;
  z-index: 200;
  background: linear-gradient(90deg, var(--accent), var(--sun));
  box-shadow: 0 0 10px color-mix(in srgb, var(--accent) 40%, transparent);
  transition: width .12s linear;
  pointer-events: none;
}

/* 滚动渐入 */
.reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity .7s var(--ease), transform .7s var(--ease);
  will-change: opacity, transform;
}
.reveal.in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  .reveal { opacity: 1 !important; transform: none !important; transition: none; }
  html { scroll-behavior: auto; }
}
body {
  margin: 0;
  background:
    radial-gradient(circle at 6% 4%, color-mix(in srgb, var(--c4) 24%, transparent), transparent 24vw),
    radial-gradient(circle at 94% 2%, color-mix(in srgb, var(--c2) 30%, transparent), transparent 22vw),
    radial-gradient(circle at 82% 36%, color-mix(in srgb, var(--c6) 18%, transparent), transparent 24vw),
    radial-gradient(circle at 14% 52%, color-mix(in srgb, var(--c3) 20%, transparent), transparent 26vw),
    radial-gradient(circle at 50% 88%, color-mix(in srgb, var(--c5) 14%, transparent), transparent 30vw),
    linear-gradient(160deg, #eef6f6 0%, #f1f5ef 45%, #f6f2ec 100%);
  background-attachment: fixed;
  color: var(--ink);
  line-height: 1.72;
}
a { color: color-mix(in srgb, var(--accent) 82%, #111); text-decoration: none; }
a:hover { text-decoration: underline; }
.auto-link {
  font-weight: 700;
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 3px;
}
:target {
  scroll-margin-top: 132px;
}
.list-card:target,
.guide-section:target {
  outline: 3px solid color-mix(in srgb, var(--accent) 38%, var(--sun));
  outline-offset: 3px;
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 80;
  background: rgba(255, 250, 242, 0.88);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--line);
  box-shadow: 0 6px 18px rgba(36, 29, 21, 0.05);
  overflow: visible;
}
.header-bar {
  position: relative;
  z-index: 90;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px clamp(16px, 4vw, 42px) 0;
}
.nav-toggle {
  display: none;
}
.header-home {
  flex: 0 0 auto;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border-radius: 999px;
  color: var(--ink);
  font-weight: 800;
  background: #fff;
  border: 1px solid var(--line);
}
.header-home:hover {
  text-decoration: none;
  border-color: color-mix(in srgb, var(--accent) 36%, var(--line));
}
.global-search {
  position: relative;
  flex: 1 1 420px;
  max-width: 680px;
  margin-left: auto;
}
.global-search-box {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
/* 隐藏"全站搜索"文字标题，让搜索框与品牌、用户中心在同一行对齐（保留无障碍可读） */
.global-search-box > span {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0);
  white-space: nowrap; border: 0;
}
.global-search-box input {
  min-height: 40px;
}
.site-search-results {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 220;
  width: min(620px, calc(100vw - 32px));
  max-height: min(520px, 70vh);
  overflow: auto;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 250, 242, 0.98);
  box-shadow: var(--shadow);
}
.site-search-results[hidden] { display: none; }
.search-result {
  display: grid;
  gap: 4px;
  padding: 10px;
  border-radius: 7px;
  color: var(--ink);
}
.search-result:hover,
.search-result.active {
  text-decoration: none;
  background: var(--accent-soft);
}
.search-result strong {
  line-height: 1.25;
}
.search-result span,
.search-result small {
  color: var(--muted);
  line-height: 1.45;
}
.top-nav {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 8px clamp(16px, 4vw, 42px) 10px;
  overflow: visible;
}
.nav-link {
  position: relative;
  z-index: 1;
  flex: 0 0 auto;
  padding: 7px 11px;
  border-radius: 999px;
  color: var(--muted);
  font-size: 14px;
  border: 1px solid transparent;
}
.nav-link.active,
.nav-link:hover {
  color: var(--ink);
  background: #fff;
  border-color: var(--line);
  text-decoration: none;
}
.nav-group {
  position: relative;
  z-index: 1;
  flex: 0 0 auto;
}
.nav-group:hover,
.nav-group:focus-within,
.nav-group[open] {
  z-index: 120;
}
.nav-group summary {
  position: relative;
  z-index: 2;
  list-style: none;
  cursor: pointer;
  padding: 7px 28px 7px 11px;
  border-radius: 999px;
  color: var(--muted);
  font-size: 14px;
  border: 1px solid transparent;
  user-select: none;
}
.nav-group summary::-webkit-details-marker { display: none; }
.nav-group summary::after {
  content: "";
  position: absolute;
  top: 50%;
  right: 12px;
  width: 7px;
  height: 7px;
  border-right: 1.5px solid currentColor;
  border-bottom: 1.5px solid currentColor;
  transform: translateY(-65%) rotate(45deg);
}
.nav-group.active summary,
.nav-group:hover summary,
.nav-group[open] summary {
  color: var(--ink);
  background: #fff;
  border-color: var(--line);
}
.nav-menu {
  display: none;
  position: absolute;
  z-index: 130;
  top: calc(100% + 8px);
  left: 0;
  min-width: 142px;
  padding: 8px;
  background: rgba(255, 250, 242, 0.98);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.nav-group:hover .nav-menu,
.nav-group:focus-within .nav-menu,
.nav-group[open] .nav-menu {
  display: grid;
  gap: 4px;
}
.nav-menu-link {
  display: block;
  padding: 8px 10px;
  border-radius: 6px;
  color: var(--muted);
  white-space: nowrap;
}
.nav-menu-link:hover,
.nav-menu-link.active {
  background: var(--accent-soft);
  color: var(--ink);
  text-decoration: none;
}

.hero {
  min-height: 430px;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
  gap: clamp(22px, 5vw, 58px);
  align-items: stretch;
  padding: clamp(26px, 5vw, 72px) clamp(16px, 5vw, 72px) 30px;
}
.hero-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--accent-deep);
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 12px;
  margin: 0 0 12px;
}
.eyebrow::before {
  content: "";
  width: 26px;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--accent), var(--sun));
}
.hero h1 {
  margin: 0;
  font-size: clamp(36px, 7vw, 74px);
  line-height: 1.04;
  letter-spacing: -0.01em;
  background: linear-gradient(120deg, var(--ink) 38%, color-mix(in srgb, var(--accent) 70%, var(--ink)));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.subtitle {
  max-width: 820px;
  color: var(--muted);
  font-size: clamp(16px, 2.2vw, 22px);
  margin: 18px 0 22px;
}
.hero-points {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}
.hero-points li {
  background: linear-gradient(90deg, rgba(255,255,255,.92), rgba(255,255,255,.70));
  border: 1px solid var(--line);
  border-left: 5px solid color-mix(in srgb, var(--accent) 65%, var(--sun));
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: transform .25s var(--ease), box-shadow .25s var(--ease), border-color .25s var(--ease);
}
.hero-points li:hover {
  transform: translateX(4px);
  box-shadow: 0 14px 30px rgba(38, 31, 25, 0.12);
  border-left-color: var(--accent);
}
.hero-point-link {
  display: grid;
  gap: 3px;
  padding: 12px 15px;
  color: var(--ink);
}
.hero-point-link:hover {
  text-decoration: none;
  background: color-mix(in srgb, var(--accent) 8%, #ffffff);
}
.hero-point-link span {
  font-weight: 800;
}
.hero-point-link small {
  color: var(--muted);
  line-height: 1.45;
}
.hero-visual {
  position: relative;
  min-height: 360px;
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
  background-image:
    linear-gradient(180deg, rgba(16,26,26,.04) 0%, rgba(16,26,26,.20) 58%, rgba(16,26,26,.50) 100%),
    var(--hero-image),
    linear-gradient(135deg, var(--accent-soft), #f4e4c8);
  background-size: cover;
  background-position: center;
  padding: 22px;
  transition: box-shadow .4s var(--ease);
}
.hero-visual:hover { box-shadow: var(--shadow-lg); }
.hero-visual::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(16,26,26,.18));
  pointer-events: none;
}
.hero-gallery {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  opacity: .94;
  transform: rotate(-2deg) scale(1.06);
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
}
.gallery-track {
  display: flex;
  gap: 14px;
  width: max-content;
  animation: gallery-flow 120s linear infinite;
}
.gallery-track img {
  flex: 0 0 auto;
  width: 178px;
  height: 112px;
  object-fit: cover;
  border-radius: 10px;
  border: 3px solid rgba(255,255,255,.78);
  box-shadow: 0 14px 30px rgba(0,0,0,.28);
}
.gallery-track img:nth-child(3n) { transform: translateY(-24px) rotate(1.5deg); }
.gallery-track img:nth-child(4n) { transform: translateY(22px) rotate(-1.5deg); }
@keyframes gallery-flow {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
.glass-panel {
  position: absolute;
  left: 22px;
  right: 22px;
  bottom: 22px;
  z-index: 3;
  width: min(100%, 420px);
  padding: 18px;
  border: 1px solid rgba(255,255,255,.52);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(10px);
  border-radius: var(--radius);
}
.glass-panel span {
  display: block;
  color: var(--muted);
  font-size: 13px;
}
.glass-panel strong {
  display: block;
  font-size: 24px;
  line-height: 1.2;
  margin-top: 4px;
}
.glass-links {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.glass-links a {
  display: grid;
  gap: 2px;
  min-height: 58px;
  padding: 8px 10px;
  border-radius: 7px;
  color: var(--ink);
  background: rgba(255,255,255,.72);
  border: 1px solid rgba(29,37,37,.09);
}
.glass-links a:hover {
  text-decoration: none;
  background: #fff;
  border-color: color-mix(in srgb, var(--accent) 35%, var(--line));
}
.glass-links strong {
  font-size: 17px;
  margin: 0;
}
.glass-links span {
  font-size: 12px;
  color: var(--muted);
}

.source-media {
  margin: 0 clamp(16px, 5vw, 72px) 24px;
  padding: clamp(16px, 3vw, 24px);
  background: rgba(255, 250, 242, 0.78);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: 0 10px 30px rgba(38, 31, 25, 0.06);
}
.source-media-head {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
}
.source-media-head h2 {
  margin: 0;
  font-size: clamp(22px, 3vw, 30px);
  line-height: 1.2;
}
.source-media-head p:last-child {
  margin: 0;
  color: var(--muted);
}
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.media-card {
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  transition: transform .3s var(--ease), box-shadow .3s var(--ease);
}
.media-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow);
}
.media-card img { transition: transform .5s var(--ease); }
.media-card:hover img { transform: scale(1.06); }
.media-card iframe,
.media-card img,
.media-card video {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  border: 0;
  object-fit: cover;
  background: #141414;
}
.media-card a {
  display: block;
  padding: 9px 11px;
  color: var(--ink);
  font-weight: 700;
}
.source-drawer summary {
  cursor: pointer;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 10px;
}
.source-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 8px;
}
.source-link {
  display: block;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid var(--line);
  border-left: 3px solid color-mix(in srgb, var(--accent) 40%, var(--line));
  border-radius: var(--radius-sm);
  color: var(--ink);
  transition: transform .2s var(--ease), border-color .2s var(--ease), box-shadow .2s var(--ease);
}
.source-link:hover {
  text-decoration: none;
  border-color: color-mix(in srgb, var(--accent) 35%, var(--line));
  border-left-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}
.source-link span,
.source-link small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-link span { font-weight: 700; }
.source-link small { color: var(--muted); margin-top: 2px; }

.city-explorer {
  margin: 0 clamp(16px, 5vw, 72px) 24px;
  padding: clamp(16px, 3vw, 26px);
  background:
    linear-gradient(135deg, rgba(255,255,255,.88), rgba(255,250,242,.84)),
    radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--accent) 13%, transparent), transparent 32%);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: 0 10px 30px rgba(38, 31, 25, 0.07);
}
.city-explorer-head {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
}
.city-explorer-head h2 {
  margin: 0;
  font-size: clamp(24px, 3.5vw, 34px);
  line-height: 1.2;
}
.city-explorer-head p:last-child {
  margin: 0;
  color: var(--muted);
}
.city-explorer-tools {
  display: grid;
  gap: 12px;
  margin-bottom: 14px;
}
.province-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.province-pill {
  min-height: 34px;
  padding: 0 13px;
  border-radius: 999px;
  color: var(--muted);
  transition: transform .2s var(--ease), background .2s var(--ease), border-color .2s var(--ease), color .2s var(--ease);
}
.province-pill:hover {
  color: var(--ink);
  border-color: color-mix(in srgb, var(--accent) 34%, var(--line));
  transform: translateY(-1px);
}
.province-pill.active {
  color: var(--ink);
  background: var(--accent-soft);
  border-color: color-mix(in srgb, var(--accent) 38%, var(--line));
  font-weight: 800;
}
.city-explorer-search {
  display: grid;
  gap: 6px;
  color: var(--muted);
  font-size: 13px;
}
.rich-grid {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  align-items: stretch;
}

.tool-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: end;
  padding: 0 clamp(16px, 5vw, 72px) 24px;
}
.search-box {
  flex: 1 1 360px;
  display: grid;
  gap: 6px;
  color: var(--muted);
  font-size: 13px;
}
input[type="search"] {
  width: 100%;
  min-height: 44px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: #fff;
  padding: 0 14px;
  font: inherit;
  color: var(--ink);
  transition: border-color .2s var(--ease), box-shadow .2s var(--ease);
}
input[type="search"]:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--accent) 55%, var(--line));
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 16%, transparent);
}
button {
  min-height: 44px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  border-radius: var(--radius-sm);
  padding: 0 16px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: border-color .2s var(--ease), background .2s var(--ease), transform .15s var(--ease), box-shadow .2s var(--ease);
}
button:hover {
  border-color: color-mix(in srgb, var(--accent) 35%, var(--line));
  background: var(--accent-tint);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
button:active { transform: translateY(0); }
:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--accent) 60%, var(--sun));
  outline-offset: 2px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  gap: 24px;
  align-items: start;
  padding: 0 clamp(16px, 5vw, 72px) 72px;
}
.sidebar {
  position: sticky;
  top: 96px;
  align-self: start;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 14px;
  height: calc(100vh - 112px);
  min-height: 0;
  overflow: hidden;
}
.sidebar-panel {
  min-height: 0;
  background: rgba(255, 250, 242, 0.88);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px;
  box-shadow: 0 8px 24px rgba(38, 31, 25, 0.06);
}
.sidebar-panel:first-child {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-panel:last-child {
  max-height: 32vh;
  overflow-y: auto;
  scrollbar-gutter: stable;
  overscroll-behavior: contain;
}
.sidebar-panel h2 {
  flex: 0 0 auto;
  margin: 0 0 10px;
  font-size: 16px;
}
.toc {
  min-height: 0;
  display: grid;
  gap: 4px;
  overflow-y: scroll;
  overflow-x: hidden;
  padding-right: 6px;
  scrollbar-gutter: stable;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--accent) 38%, #cfc7b9) transparent;
}
.toc::-webkit-scrollbar,
.sidebar-panel:last-child::-webkit-scrollbar {
  width: 9px;
}
.toc::-webkit-scrollbar-track,
.sidebar-panel:last-child::-webkit-scrollbar-track {
  background: rgba(29,37,37,.05);
  border-radius: 999px;
}
.toc::-webkit-scrollbar-thumb,
.sidebar-panel:last-child::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--accent) 38%, #cfc7b9);
  border: 2px solid rgba(255,250,242,.88);
  border-radius: 999px;
}
.toc a {
  display: block;
  padding: 7px 8px;
  border-radius: 6px;
  color: var(--muted);
  font-size: 14px;
}
.toc a:hover,
.toc a.active {
  background: var(--accent-soft);
  color: var(--ink);
  text-decoration: none;
}
.toc-level-3 { padding-left: 20px !important; font-size: 13px !important; }

.city-grid {
  display: grid;
  gap: 10px;
}
.city-grid.mini { gap: 8px; }
.city-card {
  display: block;
  border: 1px solid var(--line);
  border-left: 5px solid var(--accent);
  background: #fff;
  border-radius: var(--radius-sm);
  padding: 10px;
  color: var(--ink);
  transition: transform .25s var(--ease), box-shadow .25s var(--ease), border-color .25s var(--ease);
}
.city-card span { display: block; font-weight: 700; }
.city-card small { display: block; color: var(--muted); line-height: 1.5; margin-top: 3px; }
.city-card:hover {
  text-decoration: none;
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: color-mix(in srgb, var(--accent) 30%, var(--line));
}
.city-card.rich {
  display: grid;
  grid-template-rows: auto 1fr;
  overflow: hidden;
  padding: 0;
  border-left: 0;
  background:
    linear-gradient(135deg, rgba(255,255,255,.98), rgba(255,250,242,.88)),
    radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 34%);
}
.city-card.rich:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow);
}
/* 无真实照片的城市卡：纯文字卡（顶部色条，不放插画） */
.city-card.noimg {
  position: relative;
  border-left: 0;
  border-top: 4px solid var(--accent);
  padding: 14px 14px 12px;
  background:
    linear-gradient(135deg, rgba(255,255,255,.98), rgba(255,250,242,.9)),
    radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 40%);
}
.city-card.noimg:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.city-card.noimg .city-card-body { padding: 0; }
.city-card.noimg .fav-btn, .city-card.noimg .trip-btn { top: 12px; }
.city-card.rich .img-frame {
  display: block;
  position: relative;
  overflow: hidden;
  border-bottom: 4px solid var(--accent);
  background: var(--accent-soft);
}
.photo-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  padding: 2px 9px;
  border-radius: 999px;
  background: rgba(20, 30, 30, 0.66);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .04em;
  backdrop-filter: blur(4px);
}
.city-explorer-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: end;
}
.city-explorer-row .city-explorer-search { flex: 1 1 280px; }
.random-city {
  flex: 0 0 auto;
  min-height: 44px;
  border-radius: 999px;
  font-weight: 700;
  background: var(--accent-tint);
}
.city-card.rich img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  transition: transform .55s var(--ease);
}
.city-card.rich:hover img { transform: scale(1.07); }
.city-card-body {
  display: grid;
  gap: 7px;
  padding: 12px;
}
.city-card.rich p {
  margin: 0;
  color: var(--muted);
  line-height: 1.45;
}
.city-card.rich p strong {
  color: var(--ink);
  margin-right: 6px;
}
.city-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}
.city-tags em {
  font-style: normal;
  color: color-mix(in srgb, var(--accent) 78%, #111);
  background: color-mix(in srgb, var(--accent) 12%, #fff);
  border: 1px solid color-mix(in srgb, var(--accent) 18%, var(--line));
  border-radius: 999px;
  padding: 1px 7px;
  font-size: 12px;
}

.content {
  display: grid;
  gap: 18px;
  min-width: 0;
}
/* 全局防溢出：允许长链接 / 超长不可断字符串换行，网格子项可收缩 */
.guide-section, .md-list, .list-card, .visual-card, .item-text,
.home-section, .city-explorer, .source-media, .sidebar, .sidebar-panel { min-width: 0; }
.item-body, .item-label, .item-guide span, .auto-link,
.list-card, .guide-section p, .city-card small, .toc a, .source-link span, .source-link small {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.guide-section {
  position: relative;
  background:
    linear-gradient(135deg, #fff, color-mix(in srgb, var(--sc, var(--accent)) 5%, #fff)),
    radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--sc, var(--accent)) 16%, transparent), transparent 26%);
  border: 1px solid var(--line);
  border-top: 5px solid var(--sc, var(--accent));
  border-radius: var(--radius);
  padding: clamp(18px, 3vw, 32px);
  box-shadow: var(--shadow-sm);
  transition: box-shadow .3s var(--ease), transform .3s var(--ease);
}
.guide-section:hover {
  box-shadow: 0 16px 40px rgba(38, 31, 25, 0.10);
}
/* 章节配色轮转，告别单调 */
.content > .guide-section:nth-of-type(6n+1) { --sc: var(--c4); }
.content > .guide-section:nth-of-type(6n+2) { --sc: var(--c2); }
.content > .guide-section:nth-of-type(6n+3) { --sc: var(--c3); }
.content > .guide-section:nth-of-type(6n+4) { --sc: var(--c6); }
.content > .guide-section:nth-of-type(6n+5) { --sc: var(--c1); }
.content > .guide-section:nth-of-type(6n)   { --sc: var(--c5); }
.guide-section h2,
.guide-section h3 {
  margin: 0 0 14px;
  line-height: 1.24;
  letter-spacing: -0.01em;
}
.guide-section h2 {
  font-size: clamp(24px, 3.5vw, 36px);
  padding-bottom: 12px;
  border-bottom: 2px solid color-mix(in srgb, var(--sc, var(--accent)) 30%, var(--hairline));
  color: color-mix(in srgb, var(--sc, var(--accent)) 82%, #111);
}
.guide-section h3 {
  font-size: 22px;
  color: color-mix(in srgb, var(--sc, var(--accent)) 78%, #111);
}
.sec-ico {
  display: inline-grid;
  place-items: center;
  width: 1.5em;
  height: 1.5em;
  margin-right: 10px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--sc, var(--accent)) 18%, #fff);
  font-size: .82em;
  vertical-align: -0.22em;
}

.md-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
/* 顶层列表改为响应式多列卡片网格，提升可扫读性 */
.md-list.depth-0 {
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
  gap: 12px;
  align-items: start;
}
/* 带子项 / 带配图 / 关键事实的卡片占满整行，避免参差 */
.md-list.depth-0 > .list-card.has-children,
.md-list.depth-0 > .list-card.visual-card,
.md-list.depth-0 > .list-card.fact {
  grid-column: 1 / -1;
}
/* 嵌套列表去掉树状连接线与缩进，改为干净的分组（不再像思维导图） */
.md-list.depth-1,
.md-list.depth-2,
.md-list.depth-3 {
  margin-top: 12px;
  padding-left: 0;
  border-left: 0;
}
/* 纯叶子列表平铺为多列小卡片 */
.md-list.leaf-list {
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 230px), 1fr));
  gap: 8px;
}
/* 顶层带子项的卡片 = 彩色专题面板 */
.md-list.depth-0 > .list-card.has-children {
  background: #fff;
  border: 1px solid var(--line);
  border-left: 0;
  border-top: 4px solid var(--tc, var(--accent));
  border-radius: var(--radius);
  padding: 16px 18px 18px;
  box-shadow: var(--shadow-sm);
}
.md-list.depth-0 > .list-card.has-children:hover { box-shadow: var(--shadow); }
.md-list.depth-0 > .list-card.has-children > .item-label,
.md-list.depth-0 > .list-card.has-children > .item-body {
  font-size: 16.5px;
  font-weight: 800;
  color: var(--ink);
}
.md-list.depth-0 > .list-card.has-children > .item-label {
  background: var(--tc, var(--accent-soft));
  color: #fff;
}
/* 顶层卡片按位置轮转多彩主色（呼应主题卡的活力配色） */
.md-list.depth-0 > .list-card:nth-child(6n+1) { --tc: var(--c4); }
.md-list.depth-0 > .list-card:nth-child(6n+2) { --tc: var(--c2); }
.md-list.depth-0 > .list-card:nth-child(6n+3) { --tc: var(--c3); }
.md-list.depth-0 > .list-card:nth-child(6n+4) { --tc: var(--c6); }
.md-list.depth-0 > .list-card:nth-child(6n+5) { --tc: var(--c1); }
.md-list.depth-0 > .list-card:nth-child(6n)   { --tc: var(--c5); }
/* 深色模式下面板与卡片不要白底 */
html[data-theme="dark"] .md-list.depth-0 > .list-card.has-children,
html[data-theme="dark"] .list-card { background: #1b2326; }
html[data-theme="dark"] .list-card .list-card { background: rgba(255,255,255,0.05); }
html[data-theme="dark"] .guide-section {
  background: linear-gradient(135deg, #1a2225, #161d1f);
}

/* 章节条目计数徽标 */
.section-count {
  margin-left: 10px;
  padding: 2px 11px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-size: 13px;
  font-weight: 700;
  vertical-align: middle;
}
/* 长章节折叠 */
.clampable .section-body {
  max-height: 600px;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(#000 74%, transparent);
  mask-image: linear-gradient(#000 74%, transparent);
}
.clampable.expanded .section-body {
  max-height: none;
  -webkit-mask-image: none;
  mask-image: none;
}
.section-toggle {
  display: block;
  margin: 16px auto 0;
  min-height: 40px;
  padding: 0 24px;
  border-radius: 999px;
  font-weight: 700;
  color: var(--accent-deep);
  background: var(--accent-tint);
  border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--line));
}
.section-toggle:hover { background: var(--accent-soft); }
.list-card {
  background: #fff;
  border: 1px solid var(--line);
  border-left: 3px solid var(--tc, color-mix(in srgb, var(--accent) 40%, var(--line)));
  border-radius: var(--radius-sm);
  padding: 11px 13px;
  transition: border-color .2s var(--ease), box-shadow .2s var(--ease), transform .2s var(--ease);
}
.list-card:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}
/* 面板内的子卡片用更轻的样式，避免"盒子套盒子" */
.list-card .list-card {
  border: 1px solid var(--hairline);
  border-left: 3px solid color-mix(in srgb, var(--tc, var(--accent)) 60%, var(--line));
  background: color-mix(in srgb, var(--tc, var(--accent)) 5%, #fff);
}
.list-card.fact {
  background: color-mix(in srgb, var(--tc, var(--accent)) 10%, #fff);
  border-left-color: var(--tc, var(--accent));
}
.visual-card {
  padding: 12px;
  background:
    linear-gradient(135deg, rgba(255,255,255,.96), rgba(248,250,246,.86)),
    radial-gradient(circle at 100% 0%, rgba(104,168,201,.18), transparent 36%);
  border-left-color: color-mix(in srgb, var(--accent) 72%, var(--sky));
}
.visual-card.kind-food {
  background:
    linear-gradient(135deg, rgba(255,255,255,.96), rgba(255,246,236,.88)),
    radial-gradient(circle at 100% 0%, rgba(216,111,66,.20), transparent 36%);
  border-left-color: var(--food);
}
.visual-layout {
  display: grid;
  grid-template-columns: minmax(150px, 240px) minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}
.item-thumb-wrap {
  position: relative;
  margin: 0;
  overflow: hidden;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(29,37,37,.10);
  box-shadow: 0 10px 22px rgba(36, 29, 21, 0.10);
}
.item-thumb {
  display: block;
  width: 100%;
  aspect-ratio: 5 / 3;
  object-fit: cover;
  transition: transform .55s var(--ease);
}
.visual-card:hover .item-thumb { transform: scale(1.06); }
.item-thumb-wrap figcaption {
  position: absolute;
  left: 8px;
  bottom: 8px;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(29,37,37,.72);
  color: #fff;
  font-size: 12px;
}
.photo-generated figcaption {
  background: rgba(126, 92, 54, .78);
}
.item-text {
  min-width: 0;
  display: grid;
  gap: 8px;
}
.item-guide {
  display: grid;
  gap: 3px;
  padding: 9px 10px;
  border-radius: 7px;
  background: color-mix(in srgb, var(--accent) 9%, #ffffff);
  border: 1px solid rgba(29,37,37,.08);
}
.kind-food .item-guide {
  background: color-mix(in srgb, var(--food) 10%, #ffffff);
}
.item-guide strong {
  color: color-mix(in srgb, var(--accent) 78%, #111);
  font-size: 13px;
}
.kind-food .item-guide strong {
  color: color-mix(in srgb, var(--food) 78%, #111);
}
.item-guide span {
  color: var(--muted);
}
.item-label {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  margin-right: 8px;
  padding: 1px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent) 16%, #fff);
  color: color-mix(in srgb, var(--accent) 80%, #111);
  font-weight: 700;
  font-size: 13px;
}
.item-body { color: var(--ink); }
code {
  background: rgba(29,37,37,.08);
  border-radius: 5px;
  padding: 1px 5px;
}
.is-hidden { display: none !important; }
.search-empty {
  border: 1px dashed var(--line);
  background: #fff;
  border-radius: var(--radius);
  padding: 20px;
  color: var(--muted);
}
.search-web {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--line);
}
.search-web span { color: var(--muted); font-size: 12px; }
.search-web a {
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-size: 13px;
  font-weight: 700;
}
.search-web a:hover { text-decoration: none; background: color-mix(in srgb, var(--accent) 22%, #fff); }

.to-top {
  position: fixed;
  right: 18px;
  bottom: 18px;
  width: 46px;
  height: 46px;
  min-height: 46px;
  padding: 0;
  border-radius: 50%;
  font-weight: 700;
  font-size: 21px;
  line-height: 1;
  color: #fff;
  background: var(--accent-deep);
  border: 1px solid color-mix(in srgb, var(--accent) 60%, #000);
  box-shadow: var(--shadow);
  opacity: 0;
  transform: translateY(12px);
  pointer-events: none;
  transition: opacity .25s var(--ease), transform .25s var(--ease), box-shadow .2s var(--ease);
}
.to-top:hover {
  background: var(--accent);
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
.to-top.visible { opacity: 1; transform: translateY(0); pointer-events: auto; }
.mobile-quickbar {
  display: none;
}

/* ===== 首页增强模块：数据速览 / 精选主题 / 实用工具 ===== */
.home-section {
  margin: 0 clamp(16px, 5vw, 72px) 24px;
  padding: clamp(18px, 3vw, 30px);
  background:
    linear-gradient(135deg, rgba(255,255,255,.9), rgba(255,250,242,.84)),
    radial-gradient(circle at 0% 0%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 36%);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}
.home-section-head {
  display: grid;
  gap: 6px;
  margin-bottom: 16px;
}
.home-section-head h2 {
  margin: 0;
  font-size: clamp(22px, 3.2vw, 32px);
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.home-section-head p:last-child { margin: 0; color: var(--muted); }

/* 数据速览 */
.home-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}
.stat-card {
  position: relative;
  overflow: hidden;
  padding: 18px 18px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: linear-gradient(160deg, #fff, var(--accent-tint));
  box-shadow: var(--shadow-sm);
  transition: transform .25s var(--ease), box-shadow .25s var(--ease);
}
.stat-card:hover { transform: translateY(-3px); box-shadow: var(--shadow); }
.stat-card::after {
  content: "";
  position: absolute;
  right: -28px;
  top: -28px;
  width: 86px;
  height: 86px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--accent) 22%, transparent), transparent 70%);
}
.stat-card .stat-num {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: clamp(30px, 4vw, 42px);
  font-weight: 800;
  line-height: 1;
  color: var(--accent-deep);
  letter-spacing: -0.02em;
}
.stat-card .stat-num small { font-size: 15px; font-weight: 700; color: var(--muted); }
.stat-card .stat-label { display: block; margin-top: 8px; color: var(--muted); font-size: 14px; }

/* 精选主题 */
/* 编辑精选 · 人气目的地横向滑条 */
.featured-strip {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding: 4px 2px 14px;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
}
.featured-card {
  position: relative;
  flex: 0 0 auto;
  width: 230px;
  height: 150px;
  border-radius: var(--radius);
  overflow: hidden;
  scroll-snap-align: start;
  box-shadow: var(--shadow-sm);
  transition: transform .25s var(--ease), box-shadow .25s var(--ease);
}
.featured-card:hover { transform: translateY(-4px); box-shadow: var(--shadow); }
.featured-card img { width: 100%; height: 100%; object-fit: cover; transition: transform .5s var(--ease); }
.featured-card:hover img { transform: scale(1.07); }
.featured-grad {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 40%, rgba(10,16,16,.72));
}
.featured-name {
  position: absolute;
  left: 12px; bottom: 10px; right: 12px;
  color: #fff; font-weight: 800; font-size: 17px;
  text-shadow: 0 1px 6px rgba(0,0,0,.4);
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.theme-card {
  display: grid;
  gap: 6px;
  padding: 16px;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  transition: transform .25s var(--ease), box-shadow .25s var(--ease), border-color .25s var(--ease);
}
.theme-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow);
  border-color: color-mix(in srgb, var(--accent) 32%, var(--line));
  text-decoration: none;
}
.theme-card .theme-emoji {
  font-size: 26px;
  line-height: 1;
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: var(--accent-soft);
}
.theme-card strong { font-size: 17px; }
.theme-card span { color: var(--muted); font-size: 13px; line-height: 1.5; }

/* 实用工具 */
.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}
.tool-card {
  display: grid;
  gap: 12px;
  align-content: start;
  padding: 18px;
  border: 1px solid var(--line);
  border-top: 4px solid color-mix(in srgb, var(--accent) 55%, var(--sun));
  border-radius: var(--radius-sm);
  background: #fff;
  box-shadow: var(--shadow-sm);
}
.tool-card h3 { margin: 0; font-size: 18px; }
.tool-card p.tool-hint { margin: 0; color: var(--muted); font-size: 13px; }
.tool-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.tool-row label { color: var(--muted); font-size: 13px; }
.tool-card input[type="number"],
.tool-card select {
  min-height: 42px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: #fff;
  padding: 0 12px;
  font: inherit;
  color: var(--ink);
}
.tool-chip-row { display: flex; flex-wrap: wrap; gap: 8px; }
.tool-chip {
  min-height: 36px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.tool-chip.active {
  color: var(--ink);
  background: var(--accent-soft);
  border-color: color-mix(in srgb, var(--accent) 38%, var(--line));
}
.tool-output {
  min-height: 54px;
  padding: 13px 15px;
  border-radius: var(--radius-sm);
  background: var(--accent-tint);
  border: 1px solid var(--hairline);
  color: var(--ink);
  font-size: 14px;
  line-height: 1.6;
}
.tool-output strong { color: var(--accent-deep); }
.tool-output ul { margin: 6px 0 0; padding-left: 18px; }
.tool-output li { margin: 2px 0; }
.tool-action {
  margin-top: 10px;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 13px;
  color: #fff;
  background: linear-gradient(135deg, var(--accent), var(--accent-deep));
  border: 0;
  cursor: pointer;
}
.tool-action:hover { filter: brightness(1.06); transform: translateY(-1px); }

.site-footer {
  margin: 12px clamp(16px, 5vw, 72px) 40px;
  padding: 20px clamp(16px, 3vw, 26px);
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}
.site-footer p { margin: 0 0 4px; }
.site-footer a { font-weight: 600; }

/* ===================== 头部导航重构 ===================== */
.header-bar {
  flex-wrap: wrap;
}
.header-home {
  gap: 7px;
  background: linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 55%, var(--c4)));
  color: #fff;
  border: 0;
  font-weight: 800;
  padding: 0 14px;
}
.header-home:hover { filter: brightness(1.06); }
.brand-mark { font-size: 17px; }
.brand-name b { font-weight: 900; }
.header-links {
  display: flex;
  gap: 2px;
  flex: 0 1 auto;
}
.header-link {
  padding: 7px 12px;
  border-radius: 999px;
  color: var(--muted);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}
.header-link:hover, .header-link.active {
  color: var(--ink);
  background: var(--accent-soft);
  text-decoration: none;
}
.global-search { margin-left: auto; flex: 1 1 280px; }
.header-user {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px 0 8px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid var(--line);
  color: var(--ink);
  font-weight: 700;
  font-size: 14px;
  transition: border-color .2s var(--ease), transform .2s var(--ease), box-shadow .2s var(--ease);
}
.header-user:hover {
  text-decoration: none;
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
  border-color: color-mix(in srgb, var(--accent) 40%, var(--line));
}
.header-user.active { background: var(--accent-soft); }
.user-avatar {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--c4), var(--c5));
  font-size: 16px;
}

/* ===================== Hero：大图轮播 + 横排快速查找 ===================== */
.hero-stage {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 360px;
}
.hero-carousel {
  position: relative;
  flex: 1 1 auto;
  min-height: 384px;
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
  background: linear-gradient(135deg, var(--accent-soft), #eef3f0);
}
.hero-carousel[data-count="1"] .hero-arrow,
.hero-carousel[data-count="1"] .hero-dots { display: none; }
.hero-slides { position: absolute; inset: 0; }
.hero-slide {
  position: absolute;
  inset: 0;
  opacity: 0;
  transform: scale(1.06);
  transition: opacity .9s var(--ease), transform 6s linear;
  pointer-events: none;
}
.hero-slide.active { opacity: 1; transform: scale(1); pointer-events: auto; }
.hero-slide img { width: 100%; height: 100%; object-fit: cover; display: block; }
.hero-slide::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(10,18,24,0) 40%, rgba(10,18,24,.16) 70%, rgba(10,18,24,.62) 100%);
}
.slide-cap {
  position: absolute;
  left: 20px;
  bottom: 18px;
  right: 20px;
  z-index: 2;
  color: #fff;
  text-shadow: 0 2px 14px rgba(0,0,0,.5);
}
.slide-cap strong { display: block; font-size: clamp(20px, 3vw, 28px); font-weight: 800; }
.slide-cap span { display: block; font-size: 13px; opacity: .92; margin-top: 2px; }
a.hero-slide:hover img { filter: brightness(1.04); }
.hero-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 3;
  width: 42px;
  height: 42px;
  min-height: 0;
  padding: 0;
  border-radius: 50%;
  border: 0;
  background: rgba(255,255,255,.82);
  color: var(--ink);
  font-size: 24px;
  line-height: 1;
  box-shadow: var(--shadow-sm);
  opacity: 0;
  transition: opacity .25s var(--ease), background .2s var(--ease);
}
.hero-carousel:hover .hero-arrow { opacity: 1; }
.hero-arrow:hover { background: #fff; }
.hero-arrow.prev { left: 12px; }
.hero-arrow.next { right: 12px; }
.hero-dots {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 10px;
  z-index: 3;
  display: flex;
  gap: 7px;
  justify-content: center;
}
.hero-dot {
  width: 8px;
  height: 8px;
  min-height: 0;
  padding: 0;
  border-radius: 50%;
  border: 0;
  background: rgba(255,255,255,.55);
  box-shadow: 0 1px 4px rgba(0,0,0,.3);
  cursor: pointer;
  transition: width .25s var(--ease), background .25s var(--ease);
}
.hero-dot.active { width: 22px; border-radius: 5px; background: #fff; }
.hero-quickfind {
  flex: 0 0 auto;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 12px 14px;
  box-shadow: var(--shadow-sm);
}
.qf-title {
  display: block;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--accent-deep);
  margin-bottom: 8px;
}
.qf-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.quickfind-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 11px 12px;
  border-radius: var(--radius-sm);
  background: linear-gradient(150deg, #fff, var(--accent-tint));
  border: 1px solid var(--hairline);
  color: var(--ink);
  transition: transform .22s var(--ease), box-shadow .22s var(--ease), border-color .22s var(--ease);
}
.quickfind-card:hover {
  text-decoration: none;
  transform: translateY(-3px);
  box-shadow: var(--shadow-sm);
  border-color: color-mix(in srgb, var(--accent) 36%, var(--line));
}
.qf-emoji { font-size: 22px; line-height: 1; }
.qf-text strong { display: block; font-size: 15px; }
.qf-text small { color: var(--muted); font-size: 12px; }
.quickfind-card:nth-child(1) .qf-emoji { filter: none; }

/* ===================== 城市卡片收藏 / 加入行程按钮 ===================== */
.fav-btn, .trip-btn {
  position: absolute;
  top: 8px;
  z-index: 3;
  width: 34px;
  height: 34px;
  min-height: 0;
  padding: 0;
  border-radius: 50%;
  border: 0;
  background: rgba(255,255,255,.85);
  color: var(--c2);
  font-size: 18px;
  line-height: 34px;
  text-align: center;
  cursor: pointer;
  backdrop-filter: blur(4px);
  box-shadow: 0 2px 8px rgba(0,0,0,.18);
  transition: transform .18s var(--ease), background .18s var(--ease);
}
.fav-btn { right: 8px; }
.trip-btn { right: 48px; color: var(--c5); font-weight: 800; }
.fav-btn:hover, .trip-btn:hover { transform: scale(1.12); background: #fff; }
.fav-btn.faved { color: #fff; background: linear-gradient(135deg, var(--c2), var(--c1)); }
.trip-btn.added { color: #fff; background: linear-gradient(135deg, var(--c5), var(--c4)); }

/* ===================== 彩色点缀：主题卡 / 统计卡 / 区块条 ===================== */
.theme-card:nth-child(8n+1) { --tc: var(--c4); }
.theme-card:nth-child(8n+2) { --tc: var(--c6); }
.theme-card:nth-child(8n+3) { --tc: var(--c3); }
.theme-card:nth-child(8n+4) { --tc: var(--c2); }
.theme-card:nth-child(8n+5) { --tc: var(--c5); }
.theme-card:nth-child(8n+6) { --tc: var(--c1); }
.theme-card:nth-child(8n+7) { --tc: var(--c3); }
.theme-card:nth-child(8n+8) { --tc: var(--c4); }
.theme-card .theme-emoji {
  background: color-mix(in srgb, var(--tc, var(--accent)) 20%, #fff);
}
.theme-card:hover { border-color: color-mix(in srgb, var(--tc, var(--accent)) 50%, var(--line)); }
.theme-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  border-radius: 4px 0 0 4px;
  background: var(--tc, var(--accent));
  opacity: 0;
  transition: opacity .2s var(--ease);
}
.theme-card { position: relative; overflow: hidden; }
.theme-card:hover::before { opacity: 1; }
.stat-card:nth-child(4n+1) { --tc: var(--c4); }
.stat-card:nth-child(4n+2) { --tc: var(--c1); }
.stat-card:nth-child(4n+3) { --tc: var(--c3); }
.stat-card:nth-child(4n+4) { --tc: var(--c5); }
.stat-card {
  background: linear-gradient(160deg, #fff, color-mix(in srgb, var(--tc, var(--accent)) 12%, #fff));
}
.stat-card .stat-num { color: color-mix(in srgb, var(--tc, var(--accent)) 78%, #11202a); }
.stat-card::after { background: radial-gradient(circle, color-mix(in srgb, var(--tc, var(--accent)) 28%, transparent), transparent 70%); }
.content > .guide-section:nth-of-type(6n+1) { border-top-color: var(--c4); }
.content > .guide-section:nth-of-type(6n+2) { border-top-color: var(--c1); }
.content > .guide-section:nth-of-type(6n+3) { border-top-color: var(--c3); }
.content > .guide-section:nth-of-type(6n+4) { border-top-color: var(--c2); }
.content > .guide-section:nth-of-type(6n+5) { border-top-color: var(--c5); }
.content > .guide-section:nth-of-type(6n+6) { border-top-color: var(--c6); }

/* ===================== 用户中心 ===================== */
.user-hero {
  margin: clamp(16px, 4vw, 32px) clamp(16px, 5vw, 72px) 18px;
  padding: clamp(20px, 3vw, 32px);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 88% -10%, color-mix(in srgb, var(--c4) 28%, transparent), transparent 50%),
    linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 50%, var(--c5)));
  color: #fff;
  box-shadow: var(--shadow);
}
.user-id-card { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.user-id-card .eyebrow { color: rgba(255,255,255,.85); }
.user-id-card .eyebrow::before { background: rgba(255,255,255,.7); }
.user-id-card h1 { margin: 4px 0 6px; font-size: clamp(26px, 4vw, 38px); color: #fff; -webkit-text-fill-color: #fff; }
.user-id-card .subtitle { color: rgba(255,255,255,.92); margin: 0; }
.user-avatar-big {
  width: 84px;
  height: 84px;
  min-height: 0;
  padding: 0;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 3px solid rgba(255,255,255,.6);
  background: rgba(255,255,255,.2);
  font-size: 44px;
  line-height: 1;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}
.user-stat-row { display: flex; gap: 26px; margin-top: 20px; flex-wrap: wrap; }
.user-stat strong { font-size: 26px; font-weight: 800; }
.user-stat span { display: block; font-size: 13px; color: rgba(255,255,255,.85); }
.user-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 clamp(16px, 5vw, 72px) 16px;
}
.user-tab {
  min-height: 40px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--muted);
  font-weight: 700;
}
.user-tab.active {
  color: #fff;
  background: linear-gradient(135deg, var(--accent), var(--accent-deep));
  border-color: transparent;
}
.user-panels { margin: 0 clamp(16px, 5vw, 72px) 60px; }
.user-panel { margin: 0; }
.user-panel h2 { margin-top: 0; }
.panel-hint { color: var(--muted); font-size: 13px; margin: 0 0 16px; }
.field-row { display: grid; gap: 7px; margin-bottom: 16px; max-width: 460px; }
.field-row label, .field-label { font-weight: 700; font-size: 14px; }
.field-row input[type="text"] {
  min-height: 44px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  padding: 0 14px;
  font: inherit;
  background: #fff;
  color: var(--ink);
}
.field-row input:focus { outline: none; border-color: color-mix(in srgb, var(--accent) 55%, var(--line)); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 16%, transparent); }
.avatar-picker { display: flex; flex-wrap: wrap; gap: 8px; }
.avatar-opt {
  width: 46px;
  height: 46px;
  min-height: 0;
  padding: 0;
  display: grid;
  place-items: center;
  line-height: 1;
  border-radius: 50%;
  border: 2px solid var(--line);
  background: #fff;
  font-size: 24px;
  cursor: pointer;
  transition: transform .15s var(--ease), border-color .15s var(--ease);
}
.avatar-opt:hover { transform: scale(1.1); }
.avatar-opt.active { border-color: var(--accent); background: var(--accent-soft); }
.primary-btn {
  min-height: 46px;
  padding: 0 22px;
  border-radius: 999px;
  border: 0;
  color: #fff;
  font-weight: 800;
  background: linear-gradient(135deg, var(--accent), var(--accent-deep));
}
.primary-btn:hover { filter: brightness(1.06); transform: translateY(-1px); }
.ghost-btn {
  min-height: 42px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--c1) 50%, var(--line));
  color: var(--c1);
  background: #fff;
  font-weight: 700;
  margin-top: 8px;
}
.ghost-btn:hover { background: color-mix(in srgb, var(--c1) 10%, #fff); }
.save-tip { margin-left: 12px; color: var(--c3); font-weight: 700; }
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 14px 0;
  border-bottom: 1px solid var(--hairline);
}
.setting-row strong { display: block; }
.setting-row small { color: var(--muted); }
.seg { display: inline-flex; padding: 3px; border-radius: 999px; background: var(--accent-tint); border: 1px solid var(--line); }
.seg button {
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  font-weight: 700;
}
.seg button.active { background: #fff; color: var(--ink); box-shadow: var(--shadow-sm); }
.guide-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
.guide-item { display: flex; gap: 12px; align-items: flex-start; padding: 14px; border-radius: var(--radius-sm); background: var(--accent-tint); border: 1px solid var(--hairline); }
.gi-emoji { font-size: 26px; line-height: 1; }
.guide-item strong { display: block; margin-bottom: 3px; }
.guide-item p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.6; }
.fav-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.fav-item {
  position: relative;
  display: flex;
  gap: 10px;
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}
.fav-item img { width: 72px; height: 56px; object-fit: cover; border-radius: 8px; }
.fav-item-body { min-width: 0; }
.fav-item strong { display: block; font-size: 15px; }
.fav-item small { color: var(--muted); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fav-remove {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 24px;
  height: 24px;
  min-height: 0;
  padding: 0;
  border-radius: 50%;
  border: 0;
  background: color-mix(in srgb, var(--c1) 14%, #fff);
  color: var(--c1);
  font-size: 13px;
  line-height: 24px;
  cursor: pointer;
}
/* 我的行程 */
.trip-tools { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 12px; }
.trip-tools label { color: var(--muted); font-size: 14px; }
.trip-tools input[type="number"] { width: 84px; min-height: 40px; border-radius: var(--radius-sm); border: 1px solid var(--line); background: #fff; padding: 0 12px; font: inherit; color: var(--ink); }
.trip-tools .ghost-btn { margin-top: 0; }
.trip-summary { margin-bottom: 12px; padding: 12px 14px; border-radius: var(--radius-sm); background: var(--accent-tint); border: 1px solid var(--hairline); font-size: 14px; }
.trip-summary:empty { display: none; }
.trip-compare { margin: 0 0 16px; overflow-x: auto; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.trip-compare-table { width: 100%; min-width: 620px; border-collapse: collapse; background: #fff; font-size: 13px; }
.trip-compare-table th,
.trip-compare-table td { padding: 10px 12px; text-align: left; vertical-align: top; border-right: 1px solid var(--hairline); border-bottom: 1px solid var(--hairline); }
.trip-compare-table th:first-child { width: 90px; color: var(--muted); background: var(--accent-tint); }
.trip-compare-table thead th { color: var(--ink); background: color-mix(in srgb, var(--c4) 8%, #fff); }
.trip-compare-table tr:last-child th,
.trip-compare-table tr:last-child td { border-bottom: 0; }
.trip-compare-table th:last-child,
.trip-compare-table td:last-child { border-right: 0; }
.trip-compare-note { margin: 0; padding: 9px 12px; color: var(--muted); font-size: 12px; background: var(--accent-tint); border-top: 1px solid var(--hairline); }
.trip-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.trip-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: #fff;
}
.trip-order {
  flex: 0 0 auto;
  width: 28px; height: 28px;
  display: grid; place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--c4), var(--c5));
  color: #fff; font-weight: 800; font-size: 14px;
}
.trip-item img { width: 76px; height: 50px; object-fit: cover; border-radius: 7px; flex: 0 0 auto; }
.trip-item-body { min-width: 0; flex: 1 1 auto; }
.trip-item-body strong { display: block; font-size: 15px; }
.trip-item-body small { color: var(--muted); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trip-actions { display: flex; gap: 4px; flex: 0 0 auto; }
.trip-actions button { width: 32px; height: 32px; min-height: 0; padding: 0; border-radius: 8px; border: 1px solid var(--line); background: #fff; cursor: pointer; }
.trip-actions button:disabled { opacity: .35; cursor: default; }
.roadbook-list { display: grid; gap: 10px; }
.roadbook-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: #f8faf7;
}
.roadbook-item strong { display: block; margin-bottom: 4px; }
.roadbook-item small { display: block; color: var(--muted); }
.roadbook-actions { display: flex; gap: 6px; }
.roadbook-actions a,
.roadbook-actions button { min-height: 34px; padding: 0 10px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: #fff; color: var(--ink); font-size: 13px; }

/* 用户中心 · 本地旅行工作台 */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.user-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}
.user-panel-head h2 { margin-bottom: 6px; }
.user-panel-head .panel-hint { margin-bottom: 0; }
.tool-export-btn {
  flex: 0 0 auto;
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line));
  border-radius: var(--radius-sm);
  background: var(--accent-tint);
  color: var(--accent-deep);
  font-weight: 800;
  cursor: pointer;
}
.tool-export-btn:hover { background: var(--accent-soft); }
.travel-tool-layout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 28px 32px;
}
.tool-workspace {
  min-width: 0;
  padding-top: 14px;
  border-top: 3px solid var(--accent);
}
.checklist-workspace { border-top-color: var(--c3); }
.budget-workspace { border-top-color: var(--c2); }
.notes-workspace { grid-column: 1 / -1; border-top-color: var(--c4); }
.tool-workspace-head {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.tool-workspace-head > div { display: flex; align-items: center; gap: 9px; min-width: 0; }
.tool-workspace-head h3 { margin: 0; font-size: 18px; }
.tool-workspace-head > strong { color: var(--muted); font-size: 14px; white-space: nowrap; }
.tool-symbol {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #fff;
  font-weight: 900;
  line-height: 1;
}
.checklist-symbol { background: var(--c3); }
.budget-symbol { background: var(--c2); color: #3e2a00; }
.notes-symbol { background: var(--c4); }
.tool-inline-form,
.budget-form {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}
.tool-inline-form { grid-template-columns: minmax(0, 1fr) 42px; }
.budget-form { grid-template-columns: minmax(120px, 1.4fr) minmax(84px, .7fr) minmax(88px, .7fr) 42px; }
.tool-inline-form input,
.budget-form input,
.budget-form select,
.notes-workspace textarea {
  width: 100%;
  min-width: 0;
  min-height: 42px;
  box-sizing: border-box;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--ink);
  padding: 0 12px;
  font: inherit;
}
.notes-workspace textarea {
  min-height: 174px;
  padding: 12px 14px;
  line-height: 1.7;
  resize: vertical;
}
.tool-inline-form input:focus,
.budget-form input:focus,
.budget-form select:focus,
.notes-workspace textarea:focus {
  outline: 0;
  border-color: color-mix(in srgb, var(--accent) 58%, var(--line));
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 13%, transparent);
}
.square-action,
.tool-delete {
  width: 42px;
  height: 42px;
  min-height: 0;
  padding: 0;
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--ink);
  color: #fff;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}
.square-action:hover { background: var(--accent-deep); }
.checklist-list,
.budget-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 2px;
}
.checklist-item,
.budget-item {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 0;
  border-bottom: 1px solid var(--hairline);
}
.checklist-item label { min-width: 0; flex: 1 1 auto; display: flex; align-items: center; gap: 10px; cursor: pointer; }
.checklist-item input { width: 18px; height: 18px; accent-color: var(--c3); flex: 0 0 auto; }
.checklist-item span { overflow-wrap: anywhere; }
.checklist-item.done span { color: var(--muted); text-decoration: line-through; }
.budget-item-main { min-width: 0; flex: 1 1 auto; }
.budget-item-main strong { display: block; overflow-wrap: anywhere; }
.budget-item-main small { color: var(--muted); }
.budget-value { flex: 0 0 auto; color: var(--ink); font-weight: 800; white-space: nowrap; }
.tool-delete {
  width: 32px;
  height: 32px;
  background: #fff;
  color: var(--muted);
  font-size: 17px;
}
.tool-delete:hover { color: var(--c1); border-color: color-mix(in srgb, var(--c1) 42%, var(--line)); }
.tool-empty { margin: 10px 0 0; color: var(--muted); font-size: 13px; }
.tool-empty[hidden] { display: none; }
.autosave-status { color: var(--muted); font-size: 12px; white-space: nowrap; }
.autosave-status.saved { color: var(--c3); }
html[data-theme="dark"] .tool-inline-form input,
html[data-theme="dark"] .budget-form input,
html[data-theme="dark"] .budget-form select,
html[data-theme="dark"] .notes-workspace textarea,
html[data-theme="dark"] .tool-delete { background: #111918; }

@media (max-width: 760px) {
  .user-panel-head { align-items: stretch; }
  .tool-export-btn { align-self: flex-start; }
  .travel-tool-layout { grid-template-columns: 1fr; gap: 24px; }
  .notes-workspace { grid-column: auto; }
  .budget-form { grid-template-columns: minmax(0, 1fr) minmax(92px, .65fr) 42px; }
  .budget-form #budgetName { grid-column: 1 / -1; }
}

@media (max-width: 460px) {
  .user-panel-head { display: grid; }
  .budget-form { grid-template-columns: minmax(0, 1fr) 42px; }
  .budget-form #budgetName,
  .budget-form #budgetCategory { grid-column: 1 / -1; }
}

.changelog-block { margin-bottom: 18px; }
.changelog-block h3 { margin: 0 0 8px; font-size: 17px; color: var(--accent-deep); }
.changelog-block ul { margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.7; }

/* 城市页 · 速览名片 */
.city-overview {
  margin: 0 clamp(16px, 5vw, 72px) 24px;
  padding: clamp(16px, 3vw, 24px);
  display: grid;
  gap: 14px;
  background: linear-gradient(135deg, #fff, color-mix(in srgb, var(--accent) 7%, #fff));
  border: 1px solid var(--line);
  border-left: 5px solid var(--accent);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}
.co-facts { display: flex; flex-wrap: wrap; gap: 10px 30px; }
.co-cell { display: flex; align-items: baseline; gap: 8px; }
.co-k { color: var(--muted); font-size: 13px; }
.co-v { font-weight: 800; font-size: 16px; }
.co-block { display: grid; gap: 8px; }
.co-bk { font-weight: 800; color: var(--accent-deep); }
.co-chips { display: flex; flex-wrap: wrap; gap: 7px; }
.co-chips em {
  font-style: normal;
  font-size: 13px;
  font-weight: 700;
  padding: 4px 11px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-deep);
}
.co-chips em.food {
  background: color-mix(in srgb, var(--food) 16%, #fff);
  color: color-mix(in srgb, var(--food) 80%, #111);
}
.co-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.co-fav, .co-trip, .co-share {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 999px;
  font-weight: 800;
  border: 1px solid var(--line);
  background: #fff;
  cursor: pointer;
  transition: transform .15s var(--ease), box-shadow .2s var(--ease);
}
.co-fav:hover, .co-trip:hover, .co-share:hover { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.co-fav.on { color: #fff; background: linear-gradient(135deg, var(--c2), var(--c1)); border-color: transparent; }
.co-trip.on { color: #fff; background: linear-gradient(135deg, var(--c5), var(--c4)); border-color: transparent; }
.co-share.copied { color: #fff; background: var(--c3); border-color: transparent; }
html[data-theme="dark"] .city-overview { background: linear-gradient(135deg, #1b2326, #161d1f); }
html[data-theme="dark"] .co-fav, html[data-theme="dark"] .co-trip, html[data-theme="dark"] .co-share { background: #1b2326; color: var(--ink); }
html[data-theme="dark"] .trip-compare-table { background: #111918; }

@media (max-width: 920px) {
  .hero { grid-template-columns: 1fr; }
  .hero-stage { min-height: 0; }
  .hero-carousel { min-height: 240px; }
  .hero-visual { min-height: 240px; }
  /* 单栏阅读：移动端隐藏桌面侧栏（目录 + 其他攻略列表），正文占满宽度 */
  .layout { display: block; padding-bottom: 40px; }
  .sidebar { display: none; }
  .content { display: grid; gap: 16px; }
  .visual-layout { grid-template-columns: 1fr; }
  /* 卡片网格统一收为单列，避免窄屏挤压 / 横向溢出 */
  .md-list.depth-0,
  .md-list.leaf-list,
  .theme-grid,
  .tools-grid,
  .rich-grid { grid-template-columns: 1fr; }
  .home-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 720px) {
  html, body {
    overflow-x: hidden;
    max-width: 100%;
  }
  body {
    padding-bottom: 76px;
  }
  /* 防止长文字 / 网格撑破视口 */
  .content, .guide-section, .home-section, .city-explorer, .source-media,
  .md-list, .list-card, .visual-card, .item-text { min-width: 0; }
  .list-card, .item-body, .item-guide span, .toc a, .city-card small,
  .stat-label, .theme-card span { overflow-wrap: anywhere; word-break: break-word; }
  .home-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .guide-section { padding: 16px 14px; }
  .home-section, .city-explorer, .source-media { padding: 16px 14px; }
  .guide-section h2 { font-size: 21px; }
  :target {
    scroll-margin-top: 92px;
  }
  .site-header {
    overflow: visible;
  }
  .header-bar {
    flex-wrap: wrap;
    padding: 8px 12px;
  }
  .nav-toggle {
    display: inline-flex;
    align-items: center;
    min-height: 38px;
    padding: 0 11px;
    border-radius: 999px;
  }
  .header-home {
    min-height: 38px;
  }
  .header-links { display: none; }
  .nav-toggle { font-size: 18px; padding: 0 12px; }
  .header-user { order: 2; margin-left: auto; }
  .header-user-name { display: none; }
  .global-search {
    order: 3;
    flex-basis: 100%;
    max-width: none;
    margin-left: 0;
  }
  .qf-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .user-hero, .user-tabs, .user-panels { margin-left: 12px; margin-right: 12px; }
  .user-tabs { overflow-x: auto; flex-wrap: nowrap; -webkit-overflow-scrolling: touch; }
  .site-search-results {
    left: 0;
    right: auto;
    width: 100%;
  }
  .top-nav {
    display: none;
    max-height: 62vh;
    overflow: auto;
    padding: 0 12px 12px;
    background: rgba(255, 250, 242, 0.96);
  }
  .site-header.nav-open .top-nav {
    display: flex;
  }
  .nav-link,
  .nav-group {
    flex-basis: 100%;
  }
  .nav-link,
  .nav-group summary {
    width: 100%;
    border-radius: 7px;
    background: rgba(255,255,255,.72);
  }
  .nav-menu {
    position: static;
    width: 100%;
    margin-top: 6px;
    box-shadow: none;
  }
  .hero {
    padding-top: 20px;
  }
  .hero h1 {
    font-size: 36px;
  }
  .hero-points {
    gap: 8px;
  }
  .city-explorer,
  .source-media,
  .city-overview,
  .home-section {
    margin-left: 12px;
    margin-right: 12px;
  }
  .rich-grid {
    grid-template-columns: 1fr;
  }
  .tool-bar,
  .layout {
    padding-left: 12px;
    padding-right: 12px;
  }
  .mobile-quickbar {
    position: fixed;
    left: 10px;
    right: 10px;
    bottom: 10px;
    z-index: 90;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(54px, 1fr));
    gap: 6px;
    padding: 7px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgba(255, 250, 242, 0.94);
    backdrop-filter: blur(14px);
    box-shadow: var(--shadow);
  }
  .mobile-quickbar a {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 36px;
    border-radius: 999px;
    color: var(--ink);
    font-weight: 800;
    font-size: 13px;
    background: #fff;
  }
  .mobile-quickbar a:hover {
    text-decoration: none;
    background: var(--accent-soft);
  }
  .to-top {
    bottom: 84px;
  }
}

@media print {
  .site-header, .tool-bar, .sidebar, .to-top, .hero-visual, .source-media, .city-explorer, .mobile-quickbar { display: none !important; }
  body { background: #fff; }
  .hero { min-height: 0; display: block; padding: 0 0 18px; }
  .layout { display: block; padding: 0; }
  .guide-section { box-shadow: none; break-inside: avoid; }
}

/* ===== 2026 实用型重构覆盖层 ===== */
:root {
  --bg: #f6f4ee;
  --paper: #ffffff;
  --ink: #1d2428;
  --muted: #66706f;
  --line: rgba(28, 38, 40, .14);
  --hairline: rgba(28, 38, 40, .08);
  --accent: #1f7a68;
  --accent-deep: #16564b;
  --accent-soft: color-mix(in srgb, var(--accent) 11%, #ffffff);
  --accent-tint: color-mix(in srgb, var(--accent) 5%, #ffffff);
  --c1: #b85c38;
  --c2: #d69b38;
  --c3: #2f8664;
  --c4: #2f6f9f;
  --c5: #6b658f;
  --c6: #9d5263;
  --radius: 8px;
  --radius-sm: 6px;
  --radius-lg: 8px;
  --shadow-sm: 0 1px 2px rgba(28, 38, 40, .05), 0 8px 20px rgba(28, 38, 40, .06);
  --shadow: 0 16px 34px rgba(28, 38, 40, .11);
  --shadow-lg: 0 22px 48px rgba(28, 38, 40, .16);
  letter-spacing: 0;
}

body {
  background: linear-gradient(180deg, #f7f5ef 0%, #eef3f1 100%);
  background-attachment: fixed;
  line-height: 1.68;
}

.site-header {
  top: 0;
  background: rgba(255, 255, 255, .92);
  border-bottom: 1px solid var(--line);
  box-shadow: 0 8px 22px rgba(28, 38, 40, .06);
}
.header-bar {
  max-width: 1480px;
  min-height: 58px;
  padding-top: 8px;
  padding-bottom: 8px;
}
.header-home,
.header-link,
.header-user,
.nav-link,
.nav-group summary,
.global-search-box,
button,
input,
select {
  border-radius: var(--radius-sm);
}
.brand-mark {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: #fff;
  font-size: 0;
}
.brand-mark::after {
  content: "T";
  font-size: 15px;
  font-weight: 900;
}
.brand-name b { color: var(--accent-deep); }
.header-links { gap: 4px; }
.header-link { min-height: 36px; padding: 0 12px; }
.global-search { max-width: 420px; }
.global-search-box { min-height: 40px; background: #f7f8f5; }
.top-nav {
  max-width: 1480px;
  padding-top: 6px;
  padding-bottom: 10px;
  gap: 6px;
  overflow-x: auto;
}
.destination-nav {
  position: relative;
  z-index: 140;
  flex: 0 0 auto;
}
.destination-nav summary {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
  list-style: none;
  cursor: pointer;
  color: var(--ink);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-weight: 800;
}
.destination-nav summary::-webkit-details-marker { display: none; }
.destination-nav summary small { color: var(--muted); font-size: 12px; font-weight: 600; }
.destination-nav summary i {
  width: 7px;
  height: 7px;
  margin-left: 2px;
  border-right: 1.5px solid currentColor;
  border-bottom: 1.5px solid currentColor;
  transform: translateY(-2px) rotate(45deg);
}
.destination-nav[open] summary i { transform: translateY(2px) rotate(225deg); }
.destination-panel {
  position: absolute;
  z-index: 160;
  top: calc(100% + 8px);
  left: 0;
  width: min(1240px, calc(100vw - 84px));
  max-height: calc(100vh - 132px);
  overflow: auto;
  padding: 18px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: 0 18px 48px rgba(23, 34, 38, .18);
}
.destination-panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}
.destination-panel-head strong { font-size: 17px; }
.destination-panel-head span { color: var(--muted); font-size: 13px; }
.destination-groups {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 18px 14px;
}
.destination-group { min-width: 0; }
.destination-group h3 {
  margin: 0 0 5px;
  color: var(--accent-deep);
  font-size: 13px;
}
.destination-group > div { display: flex; flex-wrap: wrap; gap: 2px 6px; }
.destination-city {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 2px 5px;
  color: var(--muted);
  font-size: 13px;
}
.destination-city:hover,
.destination-city.active {
  color: var(--ink);
  text-decoration: none;
  background: var(--accent-tint);
  border-radius: 5px;
}
.destination-quick {
  min-width: 0;
  display: flex;
  flex: 1 1 auto;
  gap: 2px;
  overflow: hidden;
}
.destination-quick-link {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  color: var(--muted);
  font-size: 13px;
  white-space: nowrap;
}
.destination-quick-link:hover,
.destination-quick-link.active {
  color: var(--ink);
  text-decoration: none;
  background: var(--accent-tint);
  border-radius: var(--radius-sm);
}
.nav-link,
.nav-group summary {
  min-height: 34px;
  padding: 0 11px;
  background: #f7f8f5;
}
.nav-menu {
  border-radius: var(--radius);
  border: 1px solid var(--line);
}

.hero {
  max-width: 1480px;
  min-height: auto;
  grid-template-columns: minmax(0, .94fr) minmax(360px, .72fr);
  gap: clamp(18px, 3vw, 44px);
  padding: clamp(28px, 4vw, 60px) clamp(16px, 5vw, 72px) 24px;
}
.hero h1 {
  max-width: 920px;
  margin-top: 6px;
  margin-bottom: 12px;
  font-size: clamp(34px, 5.2vw, 70px);
  line-height: 1.03;
  color: var(--ink);
  background: none;
  -webkit-text-fill-color: currentColor;
}
.subtitle {
  max-width: 760px;
  color: var(--muted);
}
.hero-points {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 22px;
}

.hero-points li,
.hero-point-link,
.qf-grid a,
.quickfind-card,
.theme-card,
.tool-card,
.stat-card,
.city-card,
.list-card,
.visual-card,
.media-card,
.source-link,
.guide-section,
.home-section,
.city-explorer,
.source-media,
.city-overview,
.research-panel,
.sidebar-panel {
  border-radius: var(--radius);
}
.hero-points li {
  background: #fff;
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}
.hero-point-link { padding: 14px 15px; }
.hero-points,
.hero-points li,
.hero-point-link,
.research-panel,
.research-grid,
.research-grid a,
.city-card,
.city-card-body,
.guide-section,
.list-card,
.visual-card,
.tool-card,
.theme-card {
  min-width: 0;
}
.hero-point-link span,
.hero-point-link small,
.research-grid strong,
.research-grid span,
.city-card span,
.city-card small,
.city-card p,
.list-card,
.visual-card,
.guide-section p,
.guide-section li {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.hero-stage { gap: 10px; align-self: stretch; }
.hero-carousel {
  min-height: 320px;
  border: 1px solid rgba(255,255,255,.8);
  border-radius: var(--radius);
}
.hero-quickfind {
  position: static;
  width: auto;
  margin: 0;
  padding: 12px;
  border-radius: var(--radius);
  background: rgba(255, 255, 255, .94);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}
.qf-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }

.research-panel,
.home-section,
.city-explorer,
.source-media,
.city-overview {
  max-width: 1480px;
  margin: 18px auto 24px;
  padding: clamp(18px, 3vw, 30px);
  background: #fff;
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}
.research-panel {
  display: grid;
  grid-template-columns: minmax(220px, .42fr) minmax(0, 1fr);
  gap: 18px;
}
.research-copy h2,
.home-section-head h2,
.city-explorer-head h2 {
  margin: 2px 0 8px;
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.18;
}
.research-copy p:last-child,
.home-section-head p:last-child,
.city-explorer-head p:last-child {
  color: var(--muted);
}
.research-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.research-grid a {
  min-height: 86px;
  padding: 14px;
  display: grid;
  gap: 6px;
  align-content: start;
  color: var(--ink);
  background: #f7f8f5;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.research-grid a:hover {
  text-decoration: none;
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
  background: var(--accent-tint);
}
.research-grid span {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
}

.home-stats { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.stat-card {
  min-height: 118px;
  background: #f7f8f5;
  border: 1px solid var(--line);
}
.stat-num { color: var(--accent-deep); }
.featured-strip { gap: 10px; padding-bottom: 6px; }
.featured-card {
  min-width: 210px;
  height: 138px;
  border-radius: var(--radius);
}
.theme-grid,
.tools-grid,
.rich-grid { gap: 12px; }
.theme-card,
.tool-card {
  background: #f7f8f5;
  border: 1px solid var(--line);
  box-shadow: none;
}
.city-explorer-tools { gap: 12px; }
.province-pills { gap: 6px; }
.province-pill,
.random-city,
.tool-chip { border-radius: 999px; }
.city-card.rich,
.city-card.noimg,
.city-card {
  background: #fff;
  border: 1px solid var(--line);
  box-shadow: none;
}
.city-card.rich:hover,
.city-card.noimg:hover,
.theme-card:hover,
.tool-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.city-card.rich .img-frame { border-radius: var(--radius-sm) var(--radius-sm) 0 0; }
.city-card-body { padding: 13px; }
.city-tags em { border-radius: 999px; }

.tool-bar {
  max-width: 1480px;
  margin: 0 auto;
  padding: 10px clamp(16px, 5vw, 72px);
}
.search-box {
  border-radius: var(--radius-sm);
  background: #fff;
}
.layout {
  max-width: 1480px;
  grid-template-columns: minmax(250px, 300px) minmax(0, 1fr);
  gap: 18px;
  padding-top: 8px;
}
.sidebar { top: 124px; }
.sidebar-panel,
.guide-section {
  background: #fff;
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}
.guide-section {
  padding: clamp(22px, 3vw, 34px) 0;
  background: transparent;
  border: 0;
  border-top: 1px solid var(--line);
  border-radius: 0;
  box-shadow: none;
}
.guide-section:hover {
  transform: none;
  box-shadow: none;
}
.guide-section h2,
.guide-section h3 { letter-spacing: 0; }
.guide-section h2 {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 0;
  color: var(--ink);
  font-size: clamp(23px, 2.6vw, 31px);
}
.sec-ico {
  flex: 0 0 auto;
  border-radius: 8px;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--sc, var(--accent)) 16%, transparent);
}
.md-list.depth-0 { gap: 0; }
.list-card,
.visual-card {
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--hairline);
  border-radius: 0;
  padding: 12px 2px;
}
.list-card:hover {
  transform: none;
  box-shadow: none;
  background: color-mix(in srgb, var(--accent) 3%, transparent);
}
.md-list.depth-0 > .list-card.has-children {
  padding: 18px 0 22px;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
  box-shadow: none;
}
.md-list.depth-0 > .list-card.has-children:hover { box-shadow: none; }
.md-list.leaf-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 26px;
  margin-top: 10px;
}
.list-card .list-card {
  min-height: 46px;
  display: grid;
  grid-template-columns: minmax(88px, .34fr) minmax(0, 1fr);
  align-items: start;
  gap: 10px;
  padding: 10px 0;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--hairline);
  border-radius: 0;
}
.list-card .list-card.fact {
  background: transparent;
  border-left: 0;
}
.source-media { margin-bottom: 56px; }
.source-link,
.media-card {
  background: #f7f8f5;
  border: 1px solid var(--line);
}
.poi-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin: 10px 0 2px;
  padding-top: 10px;
  border-top: 1px solid var(--hairline);
}
.poi-action {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: #fff;
  color: var(--ink);
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}
.poi-action:hover {
  text-decoration: none;
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.poi-action i {
  display: grid;
  width: 18px;
  height: 18px;
  place-items: center;
  border-radius: 5px;
  font-style: normal;
}
.poi-action i::before { font-size: 13px; line-height: 1; }
.poi-action-search i { background: #e8f5ef; color: #17694f; }
.poi-action-search i::before { content: "⌕"; }
.poi-action-map i { background: #eaf2fb; color: #1f5f9a; }
.poi-action-map i::before { content: "⌖"; }
.poi-action-book i { background: #fff0e8; color: #9a4d28; }
.poi-action-book i::before { content: "▤"; }
.poi-action b,
.source-link b { margin-left: 2px; color: var(--muted); font-size: 11px; }
.source-media.compact {
  display: grid;
  grid-template-columns: minmax(240px, .55fr) minmax(0, 1fr);
  align-items: center;
  gap: 24px;
  padding-top: 22px;
  padding-bottom: 22px;
  border-right: 0;
  border-left: 0;
  box-shadow: none;
}
.source-media-head.compact-head h2 {
  margin: 3px 0 6px;
  font-size: clamp(21px, 2.4vw, 28px);
}
.source-media-head.compact-head p:last-child {
  max-width: 760px;
  font-size: 13px;
}
.source-drawer { min-width: 0; }
.source-drawer summary {
  min-height: 38px;
  display: flex;
  align-items: center;
  color: var(--accent-deep);
}
.city-overview {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-left: 0;
}
.co-actions { grid-column: 1 / -1; }
.co-chips em,
.section-count { border-radius: 999px; }

.mobile-primary-nav { display: none; }

.travel-finder {
  width: 100%;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(230px, .42fr) minmax(0, 1fr);
  gap: clamp(22px, 4vw, 64px);
  margin: 0 auto 26px;
  padding: clamp(24px, 4vw, 48px) clamp(16px, 5vw, 72px);
  color: #f8fbf8;
  background: #173e39;
  border-top: 4px solid #d69b38;
  border-bottom: 1px solid rgba(255, 255, 255, .18);
}
.travel-finder-copy { align-self: center; }
.travel-finder-copy .eyebrow { color: #8ed8c6; }
.travel-finder-copy h2 {
  margin: 4px 0 10px;
  color: #fff;
  font-size: clamp(26px, 3.4vw, 44px);
  line-height: 1.12;
}
.travel-finder-copy p:last-child { max-width: 520px; margin: 0; color: #cfddd9; }
.travel-finder-form {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(5, minmax(112px, 1fr));
  gap: 12px;
  align-items: end;
}
.travel-finder-form label { min-width: 0; display: grid; gap: 6px; }
.travel-finder-form label > span { color: #dce7e3; font-size: 12px; font-weight: 800; }
.travel-finder-form input,
.travel-finder-form select {
  width: 100%;
  min-height: 44px;
  padding: 0 12px;
  color: #1c2628;
  background: #fff;
  border: 1px solid rgba(255, 255, 255, .38);
}
.finder-query { grid-column: 1 / -1; }
.finder-query input { font-size: 16px; }
.travel-finder-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.finder-reset {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  padding: 0;
  color: #fff;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, .45);
  font-size: 20px;
}
.finder-reset:hover { background: rgba(255, 255, 255, .1); }
.finder-results-link {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 14px;
  color: #172523;
  background: #f3c35a;
  border-radius: var(--radius-sm);
  font-weight: 900;
}
.finder-results-link:hover { color: #172523; text-decoration: none; background: #ffd67a; }
.finder-summary {
  grid-column: 2 / -1;
  margin: 0;
  color: #cfddd9;
  font-size: 13px;
}
.city-explorer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
.city-explorer-footer p { margin: 0; color: var(--muted); }
.city-load-more {
  min-height: 42px;
  padding: 0 16px;
  color: #fff;
  background: var(--accent-deep);
  border: 0;
  font-weight: 800;
}
.city-load-more[hidden] { display: none; }
.user-tab { flex: 0 0 auto; min-width: max-content; white-space: nowrap; }

/* 独立目录页：让导航入口落在完整页面，而非首页锚点。 */
.catalog-masthead {
  width: 100%;
  min-height: 250px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(250px, .6fr);
  align-items: end;
  gap: clamp(22px, 5vw, 72px);
  padding: clamp(28px, 5vw, 72px);
  color: #f7fbf9;
  background: #173e39;
  border-bottom: 4px solid #d69b38;
}
.catalog-masthead .eyebrow { color: #9addcb; }
.catalog-masthead h1 { max-width: 780px; margin: 6px 0 12px; color: #fff; font-size: clamp(32px, 3.7vw, 50px); line-height: 1.1; }
.catalog-masthead p:not(.eyebrow) { max-width: 720px; margin: 0; color: #d3e2dd; font-size: 16px; line-height: 1.75; }
.catalog-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border-left: 1px solid rgba(255,255,255,.24); }
.catalog-facts div { min-height: 88px; display: grid; align-content: center; padding: 0 18px; border-bottom: 1px solid rgba(255,255,255,.18); }
.catalog-facts strong { color: #f3c35a; font-size: 28px; line-height: 1.1; }
.catalog-facts span { margin-top: 7px; color: #d3e2dd; font-size: 13px; font-weight: 700; }

/* 宽屏保持左右比例一致，并允许省份菜单越过导航行显示。 */
.header-bar,
.top-nav,
.hero,
.research-panel,
.home-section,
.city-explorer,
.source-media,
.city-overview,
.tool-bar,
.layout {
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}
.top-nav { overflow: visible; }
.nav-group summary::marker {
  content: "";
  font-size: 0;
}
.nav-group summary::after { display: none; }

html[data-theme="dark"] {
  --bg: #111716;
  --paper: #18211f;
  --ink: #eef2ee;
  --muted: #a7b4af;
  --line: rgba(255,255,255,.13);
  --hairline: rgba(255,255,255,.08);
  --accent: #36b391;
  --accent-deep: #74d6bd;
}
html[data-theme="dark"] body {
  background: linear-gradient(180deg, #0f1514 0%, #111918 100%);
}
html[data-theme="dark"] .site-header,
html[data-theme="dark"] .destination-panel,
html[data-theme="dark"] .destination-nav summary,
html[data-theme="dark"] .research-panel,
html[data-theme="dark"] .home-section,
html[data-theme="dark"] .city-explorer,
html[data-theme="dark"] .source-media,
html[data-theme="dark"] .city-overview,
html[data-theme="dark"] .sidebar-panel,
html[data-theme="dark"] .guide-section,
html[data-theme="dark"] .hero-points li,
html[data-theme="dark"] .hero-quickfind,
html[data-theme="dark"] .city-card.rich,
html[data-theme="dark"] .city-card.noimg,
html[data-theme="dark"] .city-card {
  background: #18211f;
}
html[data-theme="dark"] .travel-finder { background: #112d29; }
html[data-theme="dark"] .research-grid a,
html[data-theme="dark"] .theme-card,
html[data-theme="dark"] .tool-card,
html[data-theme="dark"] .stat-card,
html[data-theme="dark"] .list-card,
html[data-theme="dark"] .visual-card,
html[data-theme="dark"] .source-link,
html[data-theme="dark"] .media-card,
html[data-theme="dark"] .poi-action,
html[data-theme="dark"] .global-search-box,
html[data-theme="dark"] .nav-link,
html[data-theme="dark"] .nav-group summary {
  background: #202a28;
}

@media (max-width: 920px) {
  .site-header.nav-open .top-nav { display: flex; }
  .top-nav {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 10px 12px 14px;
  }
  .destination-nav { width: 100%; }
  .destination-nav summary {
    width: 100%;
    min-height: 44px;
    justify-content: space-between;
  }
  .destination-panel {
    position: static;
    width: 100%;
    max-height: 62vh;
    margin-top: 8px;
    padding: 14px;
    box-shadow: none;
  }
  .destination-groups { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .destination-quick {
    width: 100%;
    flex-wrap: wrap;
    overflow: visible;
  }
  .destination-quick-link { min-height: 40px; }
  .mobile-primary-nav {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    padding-top: 10px;
    border-top: 1px solid var(--line);
  }
  .mobile-primary-nav .header-link {
    min-height: 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0 8px;
    background: var(--accent-tint);
  }
  .hero {
    grid-template-columns: 1fr;
    padding-top: 20px;
  }
  .hero-stage { order: 0; }
  .research-panel,
  .city-overview,
  .source-media.compact {
    grid-template-columns: 1fr;
  }
  .qf-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .travel-finder { grid-template-columns: 1fr; }
  .travel-finder-form { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .finder-query { grid-column: 1 / -1; }
  .finder-summary { grid-column: 1 / -1; }
  .catalog-masthead { grid-template-columns: 1fr; }
}

@media (max-width: 720px) {
  .destination-panel-head { display: block; }
  .destination-panel-head span { display: block; margin-top: 2px; }
  .destination-groups { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .md-list.leaf-list { grid-template-columns: 1fr; }
  .list-card .list-card { grid-template-columns: minmax(82px, .34fr) minmax(0, 1fr); }
  .hero h1 { font-size: 34px; }
  .hero-points,
  .home-stats,
  .research-grid {
    grid-template-columns: 1fr;
  }
  .research-panel,
  .home-section,
  .city-explorer,
  .source-media,
  .city-overview {
    width: calc(100% - 24px);
    margin-left: 12px;
    margin-right: 12px;
  }
  .travel-finder-form { grid-template-columns: 1fr; }
  .finder-query,
  .finder-summary { grid-column: 1; }
  .travel-finder-actions { justify-content: space-between; }
  .city-explorer-footer { align-items: stretch; flex-direction: column; }
  .city-load-more { width: 100%; }
  .catalog-masthead { width: 100%; min-height: 0; padding: 30px 20px; }
  .catalog-facts { border-left: 0; border-top: 1px solid rgba(255,255,255,.24); }
  .catalog-facts div { padding: 14px 10px 0; min-height: 0; }
}
"""


JS = r"""
(function () {
  const input = document.getElementById("guideSearch");
  const content = document.getElementById("guideContent");
  const sections = Array.from(document.querySelectorAll(".guide-section"));
  const tocLinks = Array.from(document.querySelectorAll(".toc a"));
  const toTop = document.getElementById("toTop");
  const printBtn = document.getElementById("printPage");
  const expandBtn = document.getElementById("expandAll");
  const navGroups = Array.from(document.querySelectorAll(".nav-group, .destination-nav"));
  const navToggle = document.getElementById("navToggle");
  const header = document.querySelector(".site-header");
  const siteSearch = document.getElementById("siteSearch");
  const siteSearchResults = document.getElementById("siteSearchResults");
  const siteSearchData = document.getElementById("siteSearchData");
  const siteRoot = document.body.dataset.siteRoot || ".";
  const cityExplorerSearch = document.getElementById("cityExplorerSearch");
  const cityExplorerCards = Array.from(document.querySelectorAll("#cityExplorer .city-card"));
  const provincePills = Array.from(document.querySelectorAll(".province-pill"));
  const travelFinderForm = document.getElementById("travelFinderForm");
  const travelQuery = document.getElementById("travelQuery");
  const travelRegion = document.getElementById("travelRegion");
  const travelSeason = document.getElementById("travelSeason");
  const travelDays = document.getElementById("travelDays");
  const travelTheme = document.getElementById("travelTheme");
  const travelTransport = document.getElementById("travelTransport");
  const travelFinderSummary = document.getElementById("travelFinderSummary");
  const cityExplorerSummary = document.getElementById("cityExplorerSummary");
  const cityLoadMore = document.getElementById("cityLoadMore");
  const CITY_PAGE_SIZE = 36;
  let emptyBox = null;
  let activeProvince = "全部";
  let cityVisibleLimit = CITY_PAGE_SIZE;

  function normalize(s) {
    return (s || "").toLowerCase().trim();
  }

  function readSearchData() {
    if (Array.isArray(window.TRAVEL_SEARCH_INDEX)) return window.TRAVEL_SEARCH_INDEX;
    if (!siteSearchData) return [];
    try {
      return JSON.parse(siteSearchData.textContent || "[]");
    } catch (error) {
      return [];
    }
  }

  const allSearchItems = readSearchData();

  function rootHref(path) {
    if (!path || /^(https?:|mailto:|tel:)/.test(path)) return path || "#";
    const prefix = (siteRoot || ".").replace(/\/?$/, "/");
    return prefix + path.replace(/^\//, "");
  }

  function searchScore(item, query) {
    const tokens = normalize(query).split(/\s+/).filter(Boolean);
    if (!tokens.length) return 0;
    const title = normalize(item.title);
    const city = normalize(item.city);
    const province = normalize(item.province);
    const text = normalize([
      item.title,
      item.subtitle,
      item.province,
      item.city,
      (item.highlights || []).join(" "),
      (item.foods || []).join(" "),
      item.keywords || "",
    ].join(" "));
    let score = 0;
    for (const token of tokens) {
      if (!text.includes(token)) return 0;
      if (title.includes(token)) score += 10;
      if (city.includes(token)) score += 8;
      if (province.includes(token)) score += 4;
      score += 1;
    }
    return score;
  }

  function renderSiteSearch() {
    if (!siteSearch || !siteSearchResults) return;
    const q = siteSearch.value.trim();
    if (!q) {
      siteSearchResults.hidden = true;
      siteSearchResults.innerHTML = "";
      return;
    }
    const results = allSearchItems
      .map((item) => ({ item, score: searchScore(item, q) }))
      .filter((result) => result.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 10);
    siteSearchResults.hidden = false;
    const local = results.length
      ? results.map(({ item }) => {
          const highlights = (item.highlights || []).slice(0, 3).join("、") || item.subtitle;
          const foods = (item.foods || []).slice(0, 3).join("、");
          const meta = [item.province, highlights, foods ? "吃：" + foods : ""].filter(Boolean).join(" · ");
          return `<a class="search-result" href="${item.href || rootHref(item.path)}"><strong>${item.title}</strong><span>${meta}</span><small>${item.subtitle}</small></a>`;
        }).join("")
      : '<div class="search-empty">本站没有匹配，试试下方联网搜索。</div>';
    siteSearchResults.innerHTML = local + webSearchLinks(q);
  }

  // 联网搜索入口（新标签打开外部搜索，网页端与 App 内置浏览器都可用）
  function webSearchLinks(q) {
    const kw = encodeURIComponent(q);
    const kwt = encodeURIComponent(q + " 旅游攻略");
    // 小红书 web 端需登录才显示结果；携程/抖音/马蜂窝/百度图片可直接浏览。
    return '<div class="search-web"><span>联网搜索</span>' +
      '<a href="https://you.ctrip.com/searchsite/?query=' + kwt + '" target="_blank" rel="noreferrer">携程攻略</a>' +
      '<a href="https://www.mafengwo.cn/search/q.php?q=' + kwt + '" target="_blank" rel="noreferrer">马蜂窝</a>' +
      '<a href="https://www.douyin.com/search/' + kwt + '" target="_blank" rel="noreferrer">抖音</a>' +
      '<a href="https://image.baidu.com/search/index?tn=baiduimage&word=' + kwt + '" target="_blank" rel="noreferrer">百度图片</a>' +
      '<a href="https://www.xiaohongshu.com/search_result?keyword=' + kw + '&type=54" target="_blank" rel="noreferrer">小红书</a>' +
      '</div>';
  }

  function filterCityExplorer(resetLimit) {
    if (!cityExplorerCards.length) return;
    if (resetLimit) cityVisibleLimit = CITY_PAGE_SIZE;
    const q = normalize(travelQuery ? travelQuery.value : (cityExplorerSearch ? cityExplorerSearch.value : ""));
    const region = travelRegion ? travelRegion.value : "";
    const season = travelSeason ? travelSeason.value : "";
    const days = travelDays ? travelDays.value : "";
    const theme = travelTheme ? travelTheme.value : "";
    const transport = travelTransport ? travelTransport.value : "";
    const matches = cityExplorerCards.filter((card) => {
      const provinceHit = activeProvince === "全部" || card.dataset.province === activeProvince;
      const textHit = !q || normalize(card.dataset.search).includes(q);
      const regionHit = !region || card.dataset.region === region;
      const seasonHit = !season || normalize(card.dataset.season).includes(normalize(season));
      const daysHit = !days || card.dataset.days === days;
      const themeHit = !theme || normalize(card.dataset.theme).includes(normalize(theme));
      const transportHit = !transport || normalize(card.dataset.transport).includes(normalize(transport));
      return provinceHit && textHit && regionHit && seasonHit && daysHit && themeHit && transportHit;
    });
    cityExplorerCards.forEach((card) => card.classList.add("is-hidden"));
    matches.slice(0, cityVisibleLimit).forEach((card) => card.classList.remove("is-hidden"));
    const shown = Math.min(matches.length, cityVisibleLimit);
    const summary = matches.length
      ? `已匹配 ${matches.length} 座城市，当前显示 ${shown} 座`
      : "没有匹配城市，请放宽一个条件或重置筛选";
    if (travelFinderSummary) travelFinderSummary.textContent = summary;
    if (cityExplorerSummary) cityExplorerSummary.textContent = summary;
    if (cityLoadMore) {
      cityLoadMore.hidden = shown >= matches.length;
      cityLoadMore.textContent = `再显示 ${Math.min(CITY_PAGE_SIZE, matches.length - shown)} 座`;
    }
  }

  function readFinderState() {
    if (!travelFinderForm) return;
    const params = new URLSearchParams(window.location.search);
    if (travelQuery) travelQuery.value = params.get("q") || "";
    if (travelRegion) travelRegion.value = params.get("region") || "";
    if (travelSeason) travelSeason.value = params.get("season") || "";
    if (travelDays) travelDays.value = params.get("days") || "";
    if (travelTheme) travelTheme.value = params.get("theme") || "";
    if (travelTransport) travelTransport.value = params.get("transport") || "";
    activeProvince = params.get("province") || "全部";
    if (cityExplorerSearch) cityExplorerSearch.value = travelQuery ? travelQuery.value : "";
    provincePills.forEach((pill) => {
      pill.classList.toggle("active", (pill.dataset.province || "") === activeProvince);
    });
  }

  function writeFinderState() {
    if (!travelFinderForm) return;
    const params = new URLSearchParams(window.location.search);
    const values = {
      q: travelQuery ? travelQuery.value.trim() : "",
      region: travelRegion ? travelRegion.value : "",
      season: travelSeason ? travelSeason.value : "",
      days: travelDays ? travelDays.value : "",
      theme: travelTheme ? travelTheme.value : "",
      transport: travelTransport ? travelTransport.value : "",
      province: activeProvince === "全部" ? "" : activeProvince,
    };
    Object.keys(values).forEach((key) => {
      if (values[key]) params.set(key, values[key]);
      else params.delete(key);
    });
    const query = params.toString();
    const next = window.location.pathname + (query ? "?" + query : "") + window.location.hash;
    history.replaceState({ finder: values }, "", next);
  }

  function keepTocLinkVisible(link) {
    const toc = link && link.closest(".toc");
    if (!toc || window.matchMedia("(max-width: 920px)").matches) return;
    const top = link.offsetTop;
    const bottom = top + link.offsetHeight;
    const visibleTop = toc.scrollTop;
    const visibleBottom = visibleTop + toc.clientHeight;
    if (top < visibleTop) {
      toc.scrollTop = Math.max(0, top - 8);
    } else if (bottom > visibleBottom) {
      toc.scrollTop = bottom - toc.clientHeight + 8;
    }
  }

  function filter() {
    const q = normalize(input.value);
    let visible = 0;
    sections.forEach((section) => {
      const hit = !q || normalize(section.textContent).includes(q);
      section.classList.toggle("is-hidden", !hit);
      if (hit) visible += 1;
    });
    if (!emptyBox) {
      emptyBox = document.createElement("div");
      emptyBox.className = "search-empty";
      emptyBox.textContent = "没有匹配结果，换一个景点、店铺、城市或月份试试。";
      content.appendChild(emptyBox);
    }
    emptyBox.classList.toggle("is-hidden", visible !== 0);
  }

  if (input) input.addEventListener("input", filter);
  if (printBtn) printBtn.addEventListener("click", () => window.print());
  if (expandBtn) {
    expandBtn.addEventListener("click", () => {
      input.value = "";
      filter();
      const first = document.querySelector(".guide-section");
      if (first) first.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  if (siteSearch) {
    siteSearch.addEventListener("input", renderSiteSearch);
    siteSearch.addEventListener("focus", renderSiteSearch);
    siteSearch.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        siteSearch.value = "";
        renderSiteSearch();
        return;
      }
      const items = siteSearchResults ? Array.from(siteSearchResults.querySelectorAll(".search-result")) : [];
      if (!items.length) return;
      let idx = items.findIndex((el) => el.classList.contains("active"));
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        idx = event.key === "ArrowDown" ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length;
        items.forEach((el, i) => el.classList.toggle("active", i === idx));
        items[idx].scrollIntoView({ block: "nearest" });
      } else if (event.key === "Enter") {
        (items[idx] || items[0]).click();
      }
    });
  }
  document.addEventListener("click", (event) => {
    if (event.target.closest(".global-search")) return;
    if (siteSearchResults) siteSearchResults.hidden = true;
  });

  if (navToggle && header) {
    function closeMobileNav() {
      header.classList.remove("nav-open");
      navToggle.setAttribute("aria-expanded", "false");
    }
    navToggle.addEventListener("click", () => {
      const open = header.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.querySelectorAll(".top-nav a").forEach((link) => {
      link.addEventListener("click", () => {
        closeMobileNav();
      });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && header.classList.contains("nav-open")) {
        closeMobileNav();
        navToggle.focus();
      }
    });
  }

  if (cityExplorerSearch) cityExplorerSearch.addEventListener("input", () => {
    if (travelQuery) travelQuery.value = cityExplorerSearch.value;
    filterCityExplorer(true);
    writeFinderState();
  });
  if (travelQuery) travelQuery.addEventListener("input", () => {
    if (cityExplorerSearch) cityExplorerSearch.value = travelQuery.value;
    filterCityExplorer(true);
    writeFinderState();
  });
  [travelRegion, travelSeason, travelDays, travelTheme, travelTransport].forEach((control) => {
    if (control) control.addEventListener("change", () => {
      filterCityExplorer(true);
      writeFinderState();
    });
  });
  if (travelFinderForm) {
    travelFinderForm.addEventListener("submit", (event) => event.preventDefault());
    travelFinderForm.addEventListener("reset", () => {
      setTimeout(() => {
        activeProvince = "全部";
        provincePills.forEach((pill) => pill.classList.toggle("active", (pill.dataset.province || "") === "全部"));
        if (cityExplorerSearch) cityExplorerSearch.value = "";
        filterCityExplorer(true);
        writeFinderState();
      }, 0);
    });
  }
  if (cityLoadMore) cityLoadMore.addEventListener("click", () => {
    cityVisibleLimit += CITY_PAGE_SIZE;
    filterCityExplorer(false);
  });
  provincePills.forEach((pill) => {
    pill.addEventListener("click", () => {
      activeProvince = pill.dataset.province || "全部";
      if (travelRegion) travelRegion.value = "";
      provincePills.forEach((item) => item.classList.toggle("active", item === pill));
      filterCityExplorer(true);
      writeFinderState();
    });
  });
  readFinderState();
  filterCityExplorer(true);
  window.addEventListener("popstate", () => {
    readFinderState();
    filterCityExplorer(true);
  });

  navGroups.forEach((group) => {
    group.addEventListener("toggle", () => {
      if (!group.open) return;
      navGroups.forEach((other) => {
        if (other !== group) other.open = false;
      });
    });
  });
  document.addEventListener("click", (event) => {
    if (event.target.closest(".nav-group, .destination-nav")) return;
    navGroups.forEach((group) => { group.open = false; });
  });

  const observer = new IntersectionObserver((entries) => {
    const active = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!active) return;
    let activeLink = null;
    tocLinks.forEach((a) => {
      const hit = a.getAttribute("href") === "#" + active.target.id;
      a.classList.toggle("active", hit);
      if (hit) activeLink = a;
    });
    if (activeLink) keepTocLinkVisible(activeLink);
  }, { rootMargin: "-20% 0px -65% 0px", threshold: [0.1, 0.3, 0.6] });
  sections.forEach((section) => observer.observe(section));

  window.addEventListener("scroll", () => {
    if (toTop) toTop.classList.toggle("visible", window.scrollY > 720);
  });
  if (toTop) toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

  // 顶部阅读进度条
  const progress = document.createElement("div");
  progress.className = "read-progress";
  document.body.appendChild(progress);
  function updateProgress() {
    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    const top = window.scrollY || doc.scrollTop || 0;
    const pct = max > 0 ? Math.min(top / max, 1) : 0;
    progress.style.width = (pct * 100).toFixed(2) + "%";
  }
  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateProgress);
  updateProgress();

  // 滚动渐入
  const revealEls = Array.from(document.querySelectorAll(".reveal"));
  if (revealEls.length) {
    if ("IntersectionObserver" in window) {
      const ro = new IntersectionObserver((entries, obs) => {
        entries.forEach((e) => {
          if (e.isIntersecting) { e.target.classList.add("in"); obs.unobserve(e.target); }
        });
      }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
      revealEls.forEach((el) => ro.observe(el));
    } else {
      revealEls.forEach((el) => el.classList.add("in"));
    }
  }

  // 数据速览数字滚动
  const counters = Array.from(document.querySelectorAll(".stat-count"));
  function animateCount(el) {
    const target = parseInt(el.dataset.count, 10) || 0;
    const dur = 1100;
    const start = performance.now();
    function step(now) {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased).toString();
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  if (counters.length) {
    if ("IntersectionObserver" in window) {
      const co = new IntersectionObserver((entries, obs) => {
        entries.forEach((e) => {
          if (e.isIntersecting) { animateCount(e.target); obs.unobserve(e.target); }
        });
      }, { threshold: 0.5 });
      counters.forEach((el) => co.observe(el));
    } else {
      counters.forEach(animateCount);
    }
  }

  // 精选主题 / 工具 → 联动城市筛选并滚动到城市攻略
  const explorerSection = document.getElementById("city-explorer");
  function gotoExplorer(kw) {
    if (cityExplorerSearch) {
      cityExplorerSearch.value = kw || "";
      if (travelQuery) travelQuery.value = kw || "";
      if (travelTheme && Array.from(travelTheme.options).some((option) => option.value === kw)) {
        travelTheme.value = kw;
        cityExplorerSearch.value = "";
        if (travelQuery) travelQuery.value = "";
      }
      activeProvince = "全部";
      provincePills.forEach((p) => p.classList.toggle("active", (p.dataset.province || "") === "全部"));
      filterCityExplorer(true);
      writeFinderState();
    }
    if (explorerSection) explorerSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  document.querySelectorAll(".theme-card").forEach((card) => {
    card.addEventListener("click", () => gotoExplorer(card.dataset.themeSearch || ""));
  });
  // 工具结果里的「按主题筛选」行动按钮（事件委托）
  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-goto]");
    if (a) { e.preventDefault(); gotoExplorer(a.dataset.goto); }
  });

  // 工具：行程节奏速算
  const tripDays = document.getElementById("tripDays");
  const tripPaceOut = document.getElementById("tripPaceOut");
  function updateTripPace() {
    if (!tripDays || !tripPaceOut) return;
    let d = parseInt(tripDays.value, 10);
    if (isNaN(d) || d < 1) d = 1;
    if (d > 30) d = 30;
    let cities, pace, tip;
    if (d <= 2) { cities = "1"; pace = "单城深度"; tip = "锁定 1 座城市，集中玩核心区与代表美食，不折腾远郊。"; }
    else if (d <= 4) { cities = "1–2"; pace = "1 主 1 辅"; tip = "1 座主城 + 半天周边，留出机动时间应对天气与排队。"; }
    else if (d <= 7) { cities = "2–3"; pace = "主线串联"; tip = "2–3 座临近城市连成一条线，避免天天换酒店。"; }
    else if (d <= 12) { cities = "3–4"; pace = "区域环线"; tip = "按省 / 片区走环线，预留 1 天缓冲与休整。"; }
    else { cities = "4–6"; pace = "跨区慢游"; tip = "拆成 2 段、每段 1 个区域，体力和预算都更可控。"; }
    tripPaceOut.innerHTML = "建议覆盖 <strong>" + cities + "</strong> 座城市 · 节奏：<strong>" + pace + "</strong><br>" + tip +
      '<br><button type="button" class="tool-action" data-goto="">去「城市攻略」挑城市 →</button>';
  }
  if (tripDays) { tripDays.addEventListener("input", updateTripPace); updateTripPace(); }

  // 工具：月份适宜速查（含可点击的主题筛选关键词）
  const tripMonth = document.getElementById("tripMonth");
  const monthGuideOut = document.getElementById("monthGuideOut");
  const MONTH_GUIDE = {
    1: ["雪山 · 温泉 · 冬日暖阳", "丽江 / 香格里拉雪景、腾冲温泉、西双版纳避寒", "雪山"],
    2: ["早春花事 · 民俗年味", "罗平油菜花与樱花前奏、古镇过年氛围", "花"],
    3: ["赏花季 · 踏青", "贵安樱花、罗平油菜花、江南早春园林", "花"],
    4: ["春花尾声 · 山水回暖", "川西草甸返青、桂林漓江烟雨、苏杭园林", "喀斯特"],
    5: ["初夏 · 高原最佳", "稻城亚丁、川西雪山草原、洱海骑行", "雪山"],
    6: ["避暑前奏 · 雨季初", "贵州凉都避暑、西双版纳雨林、高原清凉", "避暑"],
    7: ["盛夏避暑 · 草原花海", "六盘水 / 贵阳避暑、乌蒙草原、高原花海", "避暑"],
    8: ["避暑 · 高原观星", "川西高原、香格里拉、海拔高处更凉爽", "避暑"],
    9: ["秋色初现 · 舒适月", "稻城亚丁金秋、九寨沟、各地秋高气爽", "雪山"],
    10: ["最佳秋色 · 黄金期", "九寨沟 / 黄龙、川西彩林、层林尽染", "雪山"],
    11: ["深秋红叶 · 银杏", "腾冲银杏村、川西彩林尾声、江南红枫", "古镇"],
    12: ["初冬 · 温泉避寒", "腾冲火山热海、西双版纳 / 海南避寒、雪山初雪", "温泉"]
  };
  function updateMonthGuide() {
    if (!tripMonth || !monthGuideOut) return;
    const m = parseInt(tripMonth.value, 10);
    const g = MONTH_GUIDE[m];
    if (!g) { monthGuideOut.textContent = ""; return; }
    monthGuideOut.innerHTML = "<strong>" + m + " 月推荐主题</strong>：" + g[0] + "<br>去处参考：" + g[1] +
      '<br><button type="button" class="tool-action" data-goto="' + g[2] + '">按「' + g[2] + '」看推荐城市 →</button>';
  }
  if (tripMonth) {
    const nowM = new Date().getMonth() + 1;
    tripMonth.value = String(nowM);
    tripMonth.addEventListener("change", updateMonthGuide);
    updateMonthGuide();
  }

  // 工具：打包清单生成
  const packTypes = document.getElementById("packTypes");
  const packListOut = document.getElementById("packListOut");
  const PACK_BASE = ["身份证 / 证件", "手机 + 充电宝", "常用药品", "移动支付 + 少量现金"];
  const PACK_EXTRA = {
    city: ["舒适步行鞋", "轻便单肩包", "折叠雨伞"],
    mountain: ["登山鞋 + 速干衣", "冲锋衣 / 防风层", "护膝 + 登山杖", "能量补给"],
    plateau: ["防晒霜 + 墨镜 + 帽子", "保暖外套（昼夜温差大）", "润唇膏 / 保湿", "按需备抗高反药"],
    summer: ["防晒 + 遮阳", "驱蚊液", "薄外套（室内空调）", "备用换洗衣物"],
    winter: ["羽绒服 / 厚外套", "保暖帽 + 手套 + 围巾", "保湿护肤", "暖宝宝"]
  };
  let activePack = "city";
  function updatePackList() {
    if (!packListOut) return;
    const items = PACK_BASE.concat(PACK_EXTRA[activePack] || []);
    packListOut.innerHTML = "<strong>随身清单</strong><ul>" + items.map((i) => "<li>" + i + "</li>").join("") + "</ul>";
  }
  if (packTypes) {
    packTypes.querySelectorAll(".tool-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        activePack = chip.dataset.pack || "city";
        packTypes.querySelectorAll(".tool-chip").forEach((c) => c.classList.toggle("active", c === chip));
        updatePackList();
      });
    });
    updatePackList();
  }

  // 随机城市探索
  const randomBtn = document.getElementById("randomCity");
  if (randomBtn) {
    randomBtn.addEventListener("click", () => {
      const visible = cityExplorerCards.filter((c) => !c.classList.contains("is-hidden"));
      const pool = visible.length ? visible : cityExplorerCards;
      if (!pool.length) return;
      const href = pool[Math.floor(Math.random() * pool.length)].getAttribute("href");
      if (href) window.location.href = href;
    });
  }

  // 图片加载淡入（用内联样式，禁用 JS 时图片始终可见，不会被隐藏）
  document.querySelectorAll(".city-card.rich img, .media-card img, .item-thumb, .hero-gallery img").forEach((img) => {
    if (img.complete && img.naturalWidth > 0) return;
    img.style.opacity = "0";
    img.style.transition = "opacity .5s ease";
    const show = () => { img.style.opacity = "1"; };
    img.addEventListener("load", show, { once: true });
    img.addEventListener("error", show, { once: true });
  });

  // 跳到主要内容（无障碍）
  const main = document.getElementById("guideContent") || document.querySelector("main");
  if (main) {
    const skip = document.createElement("a");
    skip.href = "#" + (main.id || (main.id = "guideContent"));
    skip.className = "skip-link";
    skip.textContent = "跳到主要内容";
    document.body.insertBefore(skip, document.body.firstChild);
  }

  // ===== 本地存储工具 =====
  const LS = {
    get(k, d) { try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
    del(k) { try { localStorage.removeItem(k); } catch (e) {} }
  };
  const AVATARS = ["👤", "🧭", "🏔️", "🌊", "🏯", "🐼", "🌸", "🍜", "🚆", "⛺", "🦋", "🌅"];

  // 城市页打开时记录最近浏览；不上传数据，最多保留 12 条。
  (function recordCityVisit() {
    const city = document.querySelector(".co-fav[data-key]");
    if (!city) return;
    const entry = {
      key: city.dataset.key,
      name: city.dataset.name,
      href: city.dataset.href,
      sub: city.dataset.sub,
      viewedAt: new Date().toISOString()
    };
    const recent = LS.get("tay_recent", []).filter((item) => item.key !== entry.key);
    recent.unshift(entry);
    LS.set("tay_recent", recent.slice(0, 12));
  })();

  // 把昵称 / 头像同步到顶部用户中心入口（所有页面）
  function applyProfileToHeader() {
    const p = LS.get("tay_profile", {});
    const av = document.getElementById("headerAvatar");
    const nm = document.getElementById("headerUserName");
    if (av && p.avatar) av.textContent = p.avatar;
    if (nm && p.name) nm.textContent = p.name;
  }
  applyProfileToHeader();

  // ===== 收藏 =====
  function getFavs() { return LS.get("tay_favs", []); }
  function setFavs(v) { LS.set("tay_favs", v); }
  function isFav(key) { return getFavs().some((f) => f.key === key); }
  document.querySelectorAll(".fav-btn").forEach((btn) => {
    const key = btn.dataset.key;
    if (isFav(key)) { btn.classList.add("faved"); btn.textContent = "★"; }
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      let favs = getFavs();
      const i = favs.findIndex((f) => f.key === key);
      let nowFav;
      if (i >= 0) { favs.splice(i, 1); nowFav = false; }
      else { favs.unshift({ key: key, name: btn.dataset.name, href: btn.dataset.href, sub: btn.dataset.sub }); nowFav = true; }
      setFavs(favs);
      btn.classList.toggle("faved", nowFav);
      btn.textContent = nowFav ? "★" : "☆";
    });
  });

  // ===== 行程（加入 / 移除）=====
  document.querySelectorAll(".trip-btn").forEach((btn) => {
    const key = btn.dataset.key;
    const inTrip = () => LS.get("tay_trip", []).some((t) => t.key === key);
    if (inTrip()) { btn.classList.add("added"); btn.textContent = "✓"; }
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      let trip = LS.get("tay_trip", []);
      const i = trip.findIndex((t) => t.key === key);
      let added;
      if (i >= 0) { trip.splice(i, 1); added = false; }
      else { trip.push({ key: key, name: btn.dataset.name, href: btn.dataset.href, sub: btn.dataset.sub }); added = true; }
      LS.set("tay_trip", trip);
      btn.classList.toggle("added", added);
      btn.textContent = added ? "✓" : "＋";
    });
  });

  // ===== 城市页速览：收藏 / 加入行程（带文字标签）=====
  document.querySelectorAll(".co-fav").forEach((btn) => {
    const key = btn.dataset.key;
    const sync = () => { const f = isFav(key); btn.classList.toggle("on", f); btn.textContent = f ? "★ 已收藏" : "☆ 收藏"; };
    sync();
    btn.addEventListener("click", () => {
      let favs = getFavs();
      const i = favs.findIndex((f) => f.key === key);
      if (i >= 0) favs.splice(i, 1);
      else favs.unshift({ key: key, name: btn.dataset.name, href: btn.dataset.href, sub: btn.dataset.sub });
      setFavs(favs);
      sync();
    });
  });
  document.querySelectorAll(".co-trip").forEach((btn) => {
    const key = btn.dataset.key;
    const sync = () => { const t = LS.get("tay_trip", []).some((x) => x.key === key); btn.classList.toggle("on", t); btn.textContent = t ? "✓ 已在行程" : "＋ 加入行程"; };
    sync();
    btn.addEventListener("click", () => {
      let trip = LS.get("tay_trip", []);
      const i = trip.findIndex((x) => x.key === key);
      if (i >= 0) trip.splice(i, 1);
      else trip.push({ key: key, name: btn.dataset.name, href: btn.dataset.href, sub: btn.dataset.sub });
      LS.set("tay_trip", trip);
      sync();
    });
  });
  document.querySelectorAll(".co-share").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const original = "↗ 分享";
      const title = btn.dataset.shareTitle || document.title;
      const url = location.href.split("#")[0];
      try {
        if (navigator.share) {
          await navigator.share({ title: title, text: title, url: url });
          return;
        }
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(url);
        } else {
          const input = document.createElement("input");
          input.value = url;
          input.setAttribute("readonly", "");
          input.style.position = "fixed";
          input.style.opacity = "0";
          document.body.appendChild(input);
          input.select();
          document.execCommand("copy");
          input.remove();
        }
        btn.textContent = "✓ 已复制链接";
        btn.classList.add("copied");
        setTimeout(() => { btn.textContent = original; btn.classList.remove("copied"); }, 1800);
      } catch (error) {
        if (error && error.name === "AbortError") return;
        btn.textContent = "复制失败";
        setTimeout(() => { btn.textContent = original; }, 1800);
      }
    });
  });

  // ===== Hero 大图轮播 =====
  (function () {
    const car = document.getElementById("heroCarousel");
    if (!car) return;
    const slides = Array.from(car.querySelectorAll(".hero-slide"));
    const dots = Array.from(car.querySelectorAll(".hero-dot"));
    if (slides.length <= 1) return;
    let idx = 0, timer = null;
    function go(n) {
      idx = (n + slides.length) % slides.length;
      slides.forEach((s, i) => s.classList.toggle("active", i === idx));
      dots.forEach((d, i) => d.classList.toggle("active", i === idx));
    }
    function start() {
      stop();
      if (document.documentElement.getAttribute("data-motion") === "off") return;
      timer = setInterval(() => go(idx + 1), 4800);
    }
    function stop() { if (timer) clearInterval(timer); timer = null; }
    dots.forEach((d) => d.addEventListener("click", () => { go(parseInt(d.dataset.i, 10)); start(); }));
    car.querySelectorAll(".hero-arrow").forEach((a) => a.addEventListener("click", (e) => {
      e.preventDefault();
      go(idx + parseInt(a.dataset.dir, 10));
      start();
    }));
    car.addEventListener("mouseenter", stop);
    car.addEventListener("mouseleave", start);
    // 触控滑动
    let tx = 0;
    car.addEventListener("touchstart", (e) => { tx = e.touches[0].clientX; stop(); }, { passive: true });
    car.addEventListener("touchend", (e) => {
      const dx = e.changedTouches[0].clientX - tx;
      if (Math.abs(dx) > 40) go(idx + (dx < 0 ? 1 : -1));
      start();
    }, { passive: true });
    document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); else start(); });
    start();
  })();

  // ===== 用户中心 =====
  (function () {
    const tabsWrap = document.getElementById("userTabs");
    if (!tabsWrap) return;
    const tabBtns = Array.from(tabsWrap.querySelectorAll(".user-tab"));
    const panels = Array.from(document.querySelectorAll(".user-panel"));
    tabBtns.forEach((b) => b.addEventListener("click", () => {
      tabBtns.forEach((x) => x.classList.toggle("active", x === b));
      panels.forEach((p) => { p.hidden = p.dataset.panel !== b.dataset.tab; });
    }));

    // 个人信息
    const profile = LS.get("tay_profile", { name: "", avatar: "👤", slogan: "" });
    let chosen = profile.avatar || "👤";
    const nameInput = document.getElementById("ucNameInput");
    const slogan = document.getElementById("ucSlogan");
    const nameShow = document.getElementById("ucNameShow");
    const bigAvatar = document.getElementById("ucAvatar");
    const picker = document.getElementById("avatarPicker");
    if (nameInput) nameInput.value = profile.name || "";
    if (slogan) slogan.value = profile.slogan || "";
    if (nameShow) nameShow.textContent = profile.name || "旅行者";
    if (bigAvatar) bigAvatar.textContent = chosen;
    function syncPickerActive() {
      if (picker) picker.querySelectorAll(".avatar-opt").forEach((x) => x.classList.toggle("active", x.textContent === chosen));
    }
    if (picker) {
      AVATARS.forEach((a) => {
        const b = document.createElement("button");
        b.className = "avatar-opt" + (a === chosen ? " active" : "");
        b.type = "button";
        b.textContent = a;
        b.addEventListener("click", () => { chosen = a; if (bigAvatar) bigAvatar.textContent = a; syncPickerActive(); });
        picker.appendChild(b);
      });
    }
    if (bigAvatar) bigAvatar.addEventListener("click", () => {
      const i = AVATARS.indexOf(chosen);
      chosen = AVATARS[(i + 1) % AVATARS.length];
      bigAvatar.textContent = chosen;
      syncPickerActive();
    });
    const saveBtn = document.getElementById("ucSaveProfile");
    const saveTip = document.getElementById("ucSaveTip");
    if (saveBtn) saveBtn.addEventListener("click", () => {
      const p = { name: nameInput ? nameInput.value.trim() : "", avatar: chosen, slogan: slogan ? slogan.value.trim() : "" };
      LS.set("tay_profile", p);
      if (nameShow) nameShow.textContent = p.name || "旅行者";
      if (saveTip) { saveTip.hidden = false; setTimeout(() => { saveTip.hidden = true; }, 1800); }
      applyProfileToHeader();
    });

    // 设置
    const settings = LS.get("tay_settings", { theme: "auto", vibrancy: "normal", font: "m", motion: "on" });
    function applyTheme() {
      let t = settings.theme || "auto";
      if (t === "auto") t = (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", t);
    }
    function bindSeg(id, key) {
      const seg = document.getElementById(id);
      if (!seg) return;
      seg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.val === settings[key]));
      seg.addEventListener("click", (e) => {
        const b = e.target.closest("button");
        if (!b) return;
        seg.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
        settings[key] = b.dataset.val;
        LS.set("tay_settings", settings);
        const r = document.documentElement;
        r.setAttribute("data-vibrancy", settings.vibrancy);
        r.setAttribute("data-font", settings.font);
        r.setAttribute("data-motion", settings.motion);
        applyTheme();
      });
    }
    bindSeg("setTheme", "theme");
    bindSeg("setVibrancy", "vibrancy");
    bindSeg("setFont", "font");
    bindSeg("setMotion", "motion");
    const reset = document.getElementById("ucResetAll");
    if (reset) reset.addEventListener("click", () => {
      if (confirm("确定清除本地保存的昵称、收藏、行程、路书、旅行工具和设置吗？")) {
        ["tay_profile", "tay_settings", "tay_favs", "tay_recent", "tay_trip", "tay_roadtrips", "tay_last_roadtrip", "tay_checklist", "tay_budget", "tay_notes"].forEach((k) => LS.del(k));
        location.reload();
      }
    });

    // 收藏渲染
    const favGrid = document.getElementById("favGrid");
    const favEmpty = document.getElementById("favEmpty");
    const favCount = document.getElementById("ucFavCount");
    function esc(s) { return String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
    function renderFavs() {
      const favs = getFavs();
      if (favCount) favCount.textContent = String(favs.length);
      if (!favGrid) return;
      favGrid.innerHTML = "";
      if (!favs.length) { if (favEmpty) favEmpty.hidden = false; return; }
      if (favEmpty) favEmpty.hidden = true;
      favs.forEach((f) => {
        const div = document.createElement("div");
        div.className = "fav-item";
        div.innerHTML =
          '<img src="assets/images/' + esc(f.key) + '.jpg" alt="' + esc(f.name) + '" width="800" height="480" loading="lazy">' +
          '<div class="fav-item-body"><strong>' + esc(f.name) + '</strong><small>' + esc(f.sub) + '</small>' +
          '<a href="' + esc(f.href) + '">查看攻略 →</a></div>' +
          '<button class="fav-remove" data-key="' + esc(f.key) + '" aria-label="移除收藏">✕</button>';
        favGrid.appendChild(div);
      });
      favGrid.querySelectorAll(".fav-remove").forEach((b) => b.addEventListener("click", () => {
        setFavs(getFavs().filter((x) => x.key !== b.dataset.key));
        renderFavs();
      }));
    }
    renderFavs();

    // 最近浏览
    const historyList = document.getElementById("historyList");
    const historyEmpty = document.getElementById("historyEmpty");
    const historyClear = document.getElementById("historyClear");
    function renderHistory() {
      if (!historyList) return;
      const recent = LS.get("tay_recent", []);
      historyList.innerHTML = "";
      if (!recent.length) {
        if (historyEmpty) historyEmpty.hidden = false;
        if (historyClear) historyClear.hidden = true;
        return;
      }
      if (historyEmpty) historyEmpty.hidden = true;
      if (historyClear) historyClear.hidden = false;
      recent.forEach((item) => {
        const when = item.viewedAt ? new Date(item.viewedAt).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" }) : "刚刚浏览";
        const row = document.createElement("article");
        row.className = "fav-item";
        row.innerHTML =
          '<img src="assets/images/' + esc(item.key) + '.jpg" alt="' + esc(item.name) + '" width="800" height="480" loading="lazy">' +
          '<div class="fav-item-body"><strong>' + esc(item.name) + '</strong><small>' + esc(item.sub) + ' · ' + esc(when) + '</small>' +
          '<a href="' + esc(item.href) + '">继续阅读 →</a></div>';
        historyList.appendChild(row);
      });
    }
    if (historyClear) historyClear.addEventListener("click", () => { LS.del("tay_recent"); renderHistory(); });
    renderHistory();

    // 行程渲染
    const tripList = document.getElementById("tripList");
    const tripEmpty = document.getElementById("tripEmpty");
    const tripSummary = document.getElementById("tripSummary");
    const tripDaysInput = document.getElementById("tripPlanDays");
    const tripCompare = document.getElementById("tripCompare");
    const tripCompareTable = document.getElementById("tripCompareTable");
    let compareOpen = false;
    function getTrip() { return LS.get("tay_trip", []); }
    function setTrip(v) { LS.set("tay_trip", v); }
    function renderTripCompare() {
      if (!tripCompareTable || !tripCompare) return;
      const trip = getTrip();
      tripCompare.disabled = trip.length < 2;
      if (trip.length < 2) compareOpen = false;
      tripCompare.textContent = compareOpen ? "收起对比" : "对比城市";
      tripCompareTable.hidden = !compareOpen;
      if (!compareOpen) { tripCompareTable.innerHTML = ""; return; }
      const selected = trip.slice(0, 4).map((entry) => {
        const profile = allSearchItems.find((item) => item.key === entry.key) || {};
        return { trip: entry, profile: profile };
      });
      const cells = (render) => selected.map(render).join("");
      const row = (label, render) => '<tr><th scope="row">' + label + '</th>' + cells((item) => '<td>' + render(item) + '</td>') + '</tr>';
      const table =
        '<table class="trip-compare-table"><thead><tr><th scope="col">对比项</th>' +
        cells((item) => '<th scope="col"><a href="' + esc(item.trip.href) + '">' + esc(item.trip.name.replace("旅游攻略", "")) + '</a></th>') +
        '</tr></thead><tbody>' +
        row("地区", (item) => esc(item.profile.province || "待补充")) +
        row("适宜季节", (item) => esc(item.profile.season || "见城市攻略")) +
        row("旅行印象", (item) => esc(item.profile.subtitle || item.trip.sub || "见城市攻略")) +
        row("代表景点", (item) => esc((item.profile.highlights || []).slice(0, 4).join("、") || "见城市攻略")) +
        row("代表美食", (item) => esc((item.profile.foods || []).slice(0, 4).join("、") || "见城市攻略")) +
        '</tbody></table>';
      const note = trip.length > 4 ? '<p class="trip-compare-note">为保证可读性，仅对比行程中的前 4 座城市；可通过上移调整顺序。</p>' : "";
      tripCompareTable.innerHTML = table + note;
    }
    function renderTrip() {
      if (!tripList) return;
      const trip = getTrip();
      tripList.innerHTML = "";
      renderTripCompare();
      if (!trip.length) {
        if (tripEmpty) tripEmpty.hidden = false;
        if (tripSummary) tripSummary.innerHTML = "";
        return;
      }
      if (tripEmpty) tripEmpty.hidden = true;
      let days = parseInt(tripDaysInput && tripDaysInput.value, 10);
      if (isNaN(days) || days < 1) days = trip.length;
      const per = days / trip.length;
      const tip = per < 1.2 ? "偏赶，建议减城市或加天数" : (per > 3 ? "较宽松，可加入周边" : "节奏适中");
      if (tripSummary) tripSummary.innerHTML = "共 <strong>" + trip.length + "</strong> 座城市 · 计划 <strong>" + days + "</strong> 天 · 平均每城约 <strong>" + per.toFixed(1) + "</strong> 天（" + tip + "）";
      trip.forEach((t, idx) => {
        const li = document.createElement("li");
        li.className = "trip-item";
        li.innerHTML =
          '<span class="trip-order">' + (idx + 1) + '</span>' +
          '<img src="assets/images/' + esc(t.key) + '.jpg" alt="" width="800" height="480" loading="lazy">' +
          '<div class="trip-item-body"><strong>' + esc(t.name) + '</strong><small>' + esc(t.sub) + '</small><a href="' + esc(t.href) + '">查看攻略 →</a></div>' +
          '<div class="trip-actions">' +
          '<button data-act="up" data-key="' + esc(t.key) + '" aria-label="上移"' + (idx === 0 ? " disabled" : "") + '>↑</button>' +
          '<button data-act="down" data-key="' + esc(t.key) + '" aria-label="下移"' + (idx === trip.length - 1 ? " disabled" : "") + '>↓</button>' +
          '<button data-act="del" data-key="' + esc(t.key) + '" aria-label="移除">✕</button>' +
          '</div>';
        tripList.appendChild(li);
      });
      tripList.querySelectorAll("button[data-act]").forEach((b) => b.addEventListener("click", () => {
        let trip = getTrip();
        const i = trip.findIndex((x) => x.key === b.dataset.key);
        if (i < 0) return;
        if (b.dataset.act === "del") trip.splice(i, 1);
        else if (b.dataset.act === "up" && i > 0) { const t = trip[i - 1]; trip[i - 1] = trip[i]; trip[i] = t; }
        else if (b.dataset.act === "down" && i < trip.length - 1) { const t = trip[i + 1]; trip[i + 1] = trip[i]; trip[i] = t; }
        setTrip(trip);
        renderTrip();
      }));
    }
    if (tripDaysInput) tripDaysInput.addEventListener("input", renderTrip);
    if (tripCompare) tripCompare.addEventListener("click", () => { compareOpen = !compareOpen; renderTripCompare(); });
    const tripClear = document.getElementById("tripClear");
    if (tripClear) tripClear.addEventListener("click", () => { if (confirm("清空行程？")) { setTrip([]); renderTrip(); } });
    renderTrip();

    // 已保存的自驾路书
    const roadbookList = document.getElementById("roadbookList");
    const roadbookEmpty = document.getElementById("roadbookEmpty");
    function getRoadbooks() { return LS.get("tay_roadtrips", []); }
    function renderRoadbooks() {
      if (!roadbookList) return;
      const plans = getRoadbooks();
      roadbookList.innerHTML = "";
      if (!plans.length) { if (roadbookEmpty) roadbookEmpty.hidden = false; return; }
      if (roadbookEmpty) roadbookEmpty.hidden = true;
      plans.forEach((plan) => {
        const div = document.createElement("article");
        div.className = "roadbook-item";
        const summary = plan.summary || {};
        div.innerHTML =
          '<div><strong>' + esc(plan.title) + '</strong><small>' + esc(summary.days) + ' 天 · 约 ' + esc(summary.totalKm) + ' 公里 · ' + esc(plan.generatedAt) + '</small></div>' +
          '<div class="roadbook-actions"><a href="roadtrip.html?plan=' + encodeURIComponent(plan.id) + '">打开</a>' +
          '<button type="button" data-roadbook-id="' + esc(plan.id) + '">删除</button></div>';
        roadbookList.appendChild(div);
      });
      roadbookList.querySelectorAll("button[data-roadbook-id]").forEach((button) => button.addEventListener("click", () => {
        LS.set("tay_roadtrips", getRoadbooks().filter((plan) => plan.id !== button.dataset.roadbookId));
        renderRoadbooks();
      }));
    }
    renderRoadbooks();

    // 旅行工具：清单、预算和笔记均只保存在当前浏览器
    const checklistForm = document.getElementById("checklistForm");
    const checklistInput = document.getElementById("checklistInput");
    const checklistList = document.getElementById("travelChecklist");
    const checklistEmpty = document.getElementById("checklistEmpty");
    const checklistProgress = document.getElementById("checklistProgress");
    function uniqueId(prefix) {
      return prefix + "-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
    }
    function getChecklist() {
      const items = LS.get("tay_checklist", []);
      return Array.isArray(items) ? items : [];
    }
    function setChecklist(items) { LS.set("tay_checklist", items); }
    function renderChecklist() {
      if (!checklistList) return;
      const items = getChecklist();
      const done = items.filter((item) => item.done).length;
      checklistList.innerHTML = "";
      if (checklistProgress) checklistProgress.textContent = done + " / " + items.length;
      if (checklistEmpty) checklistEmpty.hidden = items.length > 0;
      items.forEach((item) => {
        const li = document.createElement("li");
        li.className = "checklist-item" + (item.done ? " done" : "");
        li.innerHTML =
          '<label><input type="checkbox" data-check-id="' + esc(item.id) + '"' + (item.done ? " checked" : "") + '><span>' + esc(item.text) + '</span></label>' +
          '<button class="tool-delete" type="button" data-check-delete="' + esc(item.id) + '" title="删除事项" aria-label="删除清单事项">×</button>';
        checklistList.appendChild(li);
      });
      checklistList.querySelectorAll("input[data-check-id]").forEach((box) => box.addEventListener("change", () => {
        const items = getChecklist();
        const item = items.find((entry) => entry.id === box.dataset.checkId);
        if (item) item.done = box.checked;
        setChecklist(items);
        renderChecklist();
      }));
      checklistList.querySelectorAll("button[data-check-delete]").forEach((button) => button.addEventListener("click", () => {
        setChecklist(getChecklist().filter((item) => item.id !== button.dataset.checkDelete));
        renderChecklist();
      }));
    }
    if (checklistForm) checklistForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = checklistInput ? checklistInput.value.trim() : "";
      if (!text) { if (checklistInput) checklistInput.focus(); return; }
      const items = getChecklist();
      items.push({ id: uniqueId("check"), text: text, done: false });
      setChecklist(items);
      checklistInput.value = "";
      checklistInput.focus();
      renderChecklist();
    });
    renderChecklist();

    const budgetForm = document.getElementById("budgetForm");
    const budgetName = document.getElementById("budgetName");
    const budgetCategory = document.getElementById("budgetCategory");
    const budgetAmount = document.getElementById("budgetAmount");
    const budgetList = document.getElementById("budgetList");
    const budgetEmpty = document.getElementById("budgetEmpty");
    const budgetTotal = document.getElementById("budgetTotal");
    function getBudget() {
      const items = LS.get("tay_budget", []);
      return Array.isArray(items) ? items : [];
    }
    function setBudget(items) { LS.set("tay_budget", items); }
    function formatMoney(value) {
      const amount = Number(value) || 0;
      return "¥" + amount.toFixed(2);
    }
    function renderBudget() {
      if (!budgetList) return;
      const items = getBudget();
      const total = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
      budgetList.innerHTML = "";
      if (budgetTotal) budgetTotal.textContent = formatMoney(total);
      if (budgetEmpty) budgetEmpty.hidden = items.length > 0;
      items.forEach((item) => {
        const li = document.createElement("li");
        li.className = "budget-item";
        li.innerHTML =
          '<div class="budget-item-main"><strong>' + esc(item.name) + '</strong><small>' + esc(item.category) + '</small></div>' +
          '<span class="budget-value">' + formatMoney(item.amount) + '</span>' +
          '<button class="tool-delete" type="button" data-budget-delete="' + esc(item.id) + '" title="删除预算项目" aria-label="删除预算项目">×</button>';
        budgetList.appendChild(li);
      });
      budgetList.querySelectorAll("button[data-budget-delete]").forEach((button) => button.addEventListener("click", () => {
        setBudget(getBudget().filter((item) => item.id !== button.dataset.budgetDelete));
        renderBudget();
      }));
    }
    if (budgetForm) budgetForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const name = budgetName ? budgetName.value.trim() : "";
      const amount = budgetAmount ? Number(budgetAmount.value) : 0;
      if (!name) { if (budgetName) budgetName.focus(); return; }
      if (!Number.isFinite(amount) || amount <= 0) { if (budgetAmount) budgetAmount.focus(); return; }
      const items = getBudget();
      items.push({ id: uniqueId("budget"), name: name, category: budgetCategory ? budgetCategory.value : "其他", amount: amount });
      setBudget(items);
      budgetName.value = "";
      budgetAmount.value = "";
      budgetName.focus();
      renderBudget();
    });
    renderBudget();

    const travelNotes = document.getElementById("travelNotes");
    const notesSaveStatus = document.getElementById("notesSaveStatus");
    let notesTimer = null;
    if (travelNotes) {
      travelNotes.value = LS.get("tay_notes", "");
      travelNotes.addEventListener("input", () => {
        LS.set("tay_notes", travelNotes.value);
        if (notesSaveStatus) {
          notesSaveStatus.textContent = "已保存";
          notesSaveStatus.classList.add("saved");
          clearTimeout(notesTimer);
          notesTimer = setTimeout(() => {
            notesSaveStatus.textContent = "自动保存在本机";
            notesSaveStatus.classList.remove("saved");
          }, 1400);
        }
      });
    }

    function markdownCell(value) {
      return String(value || "").replace(/\|/g, "\\|").replace(/[\r\n]+/g, " ");
    }
    function downloadText(filename, value) {
      const blob = new Blob(["\ufeff" + value], { type: "text/markdown;charset=utf-8" });
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(href), 0);
    }
    const toolsExport = document.getElementById("toolsExport");
    if (toolsExport) toolsExport.addEventListener("click", () => {
      const checklist = getChecklist();
      const budget = getBudget();
      const notes = travelNotes ? travelNotes.value.trim() : LS.get("tay_notes", "").trim();
      const lines = ["# 旅行工作台", "", "> 导出时间：" + new Date().toLocaleString("zh-CN", { hour12: false }), "", "## 出行清单", ""];
      if (checklist.length) checklist.forEach((item) => lines.push("- [" + (item.done ? "x" : " ") + "] " + item.text));
      else lines.push("暂无清单事项。");
      lines.push("", "## 预算记录", "");
      if (budget.length) {
        lines.push("| 分类 | 项目 | 金额 |", "| --- | --- | ---: |");
        budget.forEach((item) => lines.push("| " + markdownCell(item.category) + " | " + markdownCell(item.name) + " | " + formatMoney(item.amount) + " |"));
        lines.push("", "合计：" + formatMoney(budget.reduce((sum, item) => sum + (Number(item.amount) || 0), 0)));
      } else lines.push("暂无预算项目。");
      lines.push("", "## 旅行笔记", "", notes || "暂无旅行笔记。", "");
      downloadText("旅行工作台.md", lines.join("\n"));
    });
  })();

  // 长章节折叠 + 顶层条目计数（渐进增强：无 JS 时正文完整展示）
  document.querySelectorAll(".guide-section").forEach((sec) => {
    const head = sec.querySelector("h2, h3");
    if (!head) return;
    const topItems = sec.querySelectorAll(".md-list.depth-0 > li").length;
    if (topItems >= 4 && !head.querySelector(".section-count")) {
      const badge = document.createElement("span");
      badge.className = "section-count";
      badge.textContent = topItems + " 条";
      head.appendChild(badge);
    }
    const body = document.createElement("div");
    body.className = "section-body";
    let n = head.nextSibling;
    while (n) { const next = n.nextSibling; body.appendChild(n); n = next; }
    sec.appendChild(body);
    requestAnimationFrame(() => {
      if (body.scrollHeight > 660) {
        sec.classList.add("clampable");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "section-toggle";
        btn.textContent = "展开全部 ▾";
        btn.addEventListener("click", () => {
          const open = sec.classList.toggle("expanded");
          btn.textContent = open ? "收起 ▴" : "展开全部 ▾";
          if (!open) sec.scrollIntoView({ behavior: "smooth", block: "start" });
        });
        sec.appendChild(btn);
      }
    });
  });

  // 图片灯箱：点击正文配图 / 参考图放大查看
  const lb = document.createElement("div");
  lb.className = "lightbox";
  lb.innerHTML = '<img alt=""><button class="lightbox-close" type="button" aria-label="关闭">✕</button>';
  document.body.appendChild(lb);
  const lbImg = lb.querySelector("img");
  function openLightbox(src, alt) { lbImg.src = src; lbImg.alt = alt || ""; lb.classList.add("open"); }
  lb.addEventListener("click", () => lb.classList.remove("open"));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") lb.classList.remove("open"); });
  document.querySelectorAll(".item-thumb, .media-card img").forEach((img) => {
    img.style.cursor = "zoom-in";
    img.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); openLightbox(img.currentSrc || img.src, img.alt); });
  });

  // PWA Service Worker（仅在 http/https 下注册；file:// 直接打开会自动跳过）
  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    const root = document.body.dataset.siteRoot || ".";
    window.addEventListener("load", () => navigator.serviceWorker.register(root + "/sw.js").catch(() => {}));
  }
})();
"""


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
        f"./assets/search-index.js?v={build_digest}",
        "./assets/icon-180.png", "./assets/icon-192.png", "./assets/icon-512.png",
    ]
    app_shell_json = json.dumps(app_shell, ensure_ascii=False, separators=(",", ","))
    sw = (
        f"const CACHE='tay-{build_digest}';\n"
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
        "      catch(_){return await c.match(e.request)||Response.error();}\n"
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


def build() -> None:
    global ASSET_BUILD
    ASSETS.mkdir(parents=True, exist_ok=True)
    if IMAGES.exists():
        shutil.rmtree(IMAGES)
    IMAGES.mkdir(parents=True, exist_ok=True)
    if ITEM_IMAGES.exists():
        shutil.rmtree(ITEM_IMAGES)
    ITEM_IMAGES.mkdir(parents=True, exist_ok=True)
    CITIES_OUT.mkdir(parents=True, exist_ok=True)
    search_index = site_search_index_js()
    ASSET_BUILD = hashlib.sha256((CSS + "\n" + JS + "\n" + search_index).encode("utf-8")).hexdigest()[:10]
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
    record = PAGES[0]
    record.output.write_text(page_html(record, record.source.read_text(encoding="utf-8")), encoding="utf-8")
    build_user_page()
    build_roadtrip_page()
    build_catalog_pages()
    build_content_audit()
    build_source_playbook()
    build_project_readme()
    sync_source_folders()


def sync_source_folders() -> None:
    return


if __name__ == "__main__":
    build()
