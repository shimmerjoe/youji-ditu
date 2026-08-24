"""Verify the generated PWA's visited-page and missing-page offline behavior."""

from __future__ import annotations

import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, _format: str, *args) -> None:
        return


def start_local_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}/"


def run(base_url: str, output: Path, before_offline: Callable[[], None] | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"baseUrl": base_url}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            color_scheme="light",
            reduced_motion="reduce",
            locale="zh-CN",
            service_workers="allow",
        )
        page = context.new_page()
        console_errors: list[str] = []
        page_errors: list[str] = []
        failed_requests: list[str] = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("requestfailed", lambda request: failed_requests.append(request.url))

        home_url = urljoin(base_url.rstrip("/") + "/", "index.html")
        qingdao_url = urljoin(base_url.rstrip("/") + "/", "cities/qingdao.html")
        # A unique query makes this a valid city route that cannot already be
        # present as an exact runtime-cache key.
        uncached_url = urljoin(base_url.rstrip("/") + "/", "cities/macao.html?offline-audit=uncached")

        page.goto(home_url, wait_until="domcontentloaded")
        page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.ready")
        page.wait_for_function("() => Boolean(navigator.serviceWorker.controller)")

        # Load the search index once so the on-demand script cache can also be
        # exercised after connectivity is disabled.
        search = page.locator("#siteSearch")
        search.fill("澳门")
        page.wait_for_function("() => Array.isArray(window.TRAVEL_SEARCH_INDEX) && window.TRAVEL_SEARCH_INDEX.length > 0")
        report["onlineSearchResults"] = page.locator("#siteSearchResults a.search-result").count()

        page.goto(qingdao_url, wait_until="domcontentloaded")
        online_title = page.title()
        if before_offline is not None:
            before_offline()
        context.set_offline(True)
        cached_response = page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(180)
        cached_screenshot = output / "cached-qingdao-mobile.png"
        page.screenshot(path=str(cached_screenshot), full_page=False, animations="disabled")
        report["cachedCity"] = {
            "status": cached_response.status if cached_response else None,
            "titlePreserved": page.title() == online_title,
            "heading": page.locator("h1").first.text_content(),
            "offlineNoticeVisible": page.locator("#appRuntimeStatus").is_visible(),
            "offlineNotice": page.locator("#appRuntimeStatus").text_content(),
            "screenshot": str(cached_screenshot),
        }

        offline_search = page.locator("#siteSearch")
        offline_search.fill("澳门")
        page.wait_for_function("() => Array.isArray(window.TRAVEL_SEARCH_INDEX) && window.TRAVEL_SEARCH_INDEX.length > 0")
        page.wait_for_timeout(100)
        report["offlineCachedSearchResults"] = page.locator("#siteSearchResults a.search-result").count()

        missing_response = page.goto(uncached_url, wait_until="domcontentloaded")
        missing_screenshot = output / "uncached-page-fallback-mobile.png"
        page.screenshot(path=str(missing_screenshot), full_page=False, animations="disabled")
        report["uncachedPage"] = {
            "status": missing_response.status if missing_response else None,
            "title": page.title(),
            "heading": page.locator("h1").text_content(),
            "homeHref": page.locator("a").first.get_attribute("href"),
            "screenshot": str(missing_screenshot),
        }
        report["consoleErrors"] = console_errors
        report["pageErrors"] = page_errors
        # Offline network failures are expected; retain them as evidence rather
        # than treating them as an application error.
        report["offlineFailedRequests"] = failed_requests
        context.close()
        browser.close()

    report_path = output / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["reportPath"] = str(report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765/")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "offline-audit")
    parser.add_argument("--self-serve", action="store_true", help="Start and stop an owned local server to prove real cache fallback")
    args = parser.parse_args()
    server = None
    base_url = args.base_url
    try:
        if args.self_serve:
            server, base_url = start_local_server()
        def stop_owned_server() -> None:
            if server is None:
                return
            server.shutdown()
            server.server_close()

        print(json.dumps(run(base_url, args.output, stop_owned_server if server else None), ensure_ascii=False, indent=2))
    finally:
        if server is not None:
            server.server_close()


if __name__ == "__main__":
    main()
