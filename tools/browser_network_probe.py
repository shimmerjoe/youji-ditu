"""Capture browser network activity without requiring an idle network."""

from __future__ import annotations

import argparse
import json

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--before", help="Visit this URL before probing the target URL.")
    args = parser.parse_args()

    events: list[dict[str, str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        if args.before:
            page.goto(args.before, wait_until="commit", timeout=30_000)
            page.wait_for_timeout(1_000)
            page.close()
            page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.on("request", lambda request: events.append({"event": "request", "url": request.url}))
        page.on("requestfinished", lambda request: events.append({"event": "finished", "url": request.url}))
        page.on("requestfailed", lambda request: events.append({"event": "failed", "url": request.url}))
        page.on("console", lambda message: events.append({"event": f"console:{message.type}", "url": message.text}))
        page.on("pageerror", lambda error: events.append({"event": "pageerror", "url": str(error)}))
        response = page.goto(args.url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(5_000)
        print(
            json.dumps(
                {
                    "status": response.status if response else None,
                    "readyState": page.evaluate("document.readyState"),
                    "title": page.title(),
                    "events": events,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
