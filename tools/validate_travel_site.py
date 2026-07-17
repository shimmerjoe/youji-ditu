from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.duplicate_ids: list[str] = []
        self.images_missing_alt: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        anchor_id = values.get("id")
        if anchor_id:
            if anchor_id in self.ids and anchor_id not in self.duplicate_ids:
                self.duplicate_ids.append(anchor_id)
            self.ids.add(anchor_id)
        if tag == "img" and "alt" not in values:
            self.images_missing_alt.append(values.get("src") or "<inline image>")
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.links.append(value)


def parse_html(path: Path) -> LinkParser:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return parser


def is_external(link: str) -> bool:
    return link.startswith(
        ("http://", "https://", "mailto:", "tel:", "javascript:", "data:")
    )


def split_local_link(link: str) -> tuple[str, str]:
    """Return a local target and fragment without deployment cache parameters."""
    parsed = urlsplit(link)
    return unquote(parsed.path), unquote(parsed.fragment)


def main() -> None:
    html_files = sorted(ROOT.rglob("*.html"))
    ids_by_file: dict[Path, set[str]] = {}
    missing: list[tuple[str, str]] = []
    missing_anchors: list[tuple[str, str]] = []
    duplicate_ids: list[tuple[str, str]] = []
    images_missing_alt: list[tuple[str, str]] = []
    empty_local_files: set[tuple[str, str]] = set()

    for path in html_files:
        parser = parse_html(path)
        ids_by_file[path.resolve()] = parser.ids
        duplicate_ids.extend(
            (str(path.relative_to(ROOT)), anchor_id)
            for anchor_id in parser.duplicate_ids
        )
        images_missing_alt.extend(
            (str(path.relative_to(ROOT)), source)
            for source in parser.images_missing_alt
        )
        for link in parser.links:
            if not link or is_external(link):
                continue

            target, fragment = split_local_link(link)
            if not target:
                if fragment and fragment not in parser.ids:
                    missing_anchors.append((str(path.relative_to(ROOT)), link))
                continue

            target_path = (path.parent / unquote(target)).resolve()
            try:
                target_path.relative_to(ROOT.resolve())
            except ValueError:
                continue

            if not target_path.exists():
                missing.append((str(path.relative_to(ROOT)), link))
                continue
            if target_path.is_file() and target_path.stat().st_size == 0:
                empty_local_files.add((str(path.relative_to(ROOT)), link))

            if fragment and target_path.suffix.lower() == ".html":
                if target_path not in ids_by_file:
                    ids_by_file[target_path] = parse_html(target_path).ids
                if fragment not in ids_by_file[target_path]:
                    missing_anchors.append((str(path.relative_to(ROOT)), link))

    print(f"root={ROOT}")
    print(f"htmlFiles={len(html_files)}")
    print(f"cityHtml={len(list((ROOT / 'cities').glob('*.html')))}")
    print(f"cityMarkdown={len(list((ROOT / '城市').glob('*.md')))}")
    print(f"missingLocalLinks={len(missing)}")
    print(f"missingAnchors={len(missing_anchors)}")
    print(f"duplicateIds={len(duplicate_ids)}")
    print(f"emptyLocalFiles={len(empty_local_files)}")
    print(f"imagesMissingAlt={len(images_missing_alt)}")

    if missing:
        print("missingLocalLinksSample=")
        for item in missing[:10]:
            print(item)
    if missing_anchors:
        print("missingAnchorsSample=")
        for item in missing_anchors[:10]:
            print(item)
    if duplicate_ids:
        print("duplicateIdsSample=")
        for item in duplicate_ids[:10]:
            print(item)
    if empty_local_files:
        print("emptyLocalFilesSample=")
        for item in sorted(empty_local_files)[:10]:
            print(item)
    if images_missing_alt:
        print("imagesMissingAltSample=")
        for item in images_missing_alt[:10]:
            print(item)

    has_errors = missing or missing_anchors or duplicate_ids or empty_local_files or images_missing_alt
    raise SystemExit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
