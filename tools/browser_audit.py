"""Run repeatable Chromium checks against the locally served travel site."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = {
    "desktop-1920": {"width": 1920, "height": 1080},
    "desktop-1366": {"width": 1366, "height": 768},
    "mobile-390": {"width": 390, "height": 844},
    "mobile-360": {"width": 360, "height": 800},
}
PAGES = {
    "home": "index.html",
    "qingdao": "cities/qingdao.html",
    "user": "user.html",
    "roadtrip": "roadtrip.html",
}


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-") or "page"


def inspect_dom(page: Page) -> dict:
    return page.evaluate(
        r"""
        () => {
          const de = document.documentElement;
          const width = window.innerWidth;
          const all = Array.from(document.querySelectorAll('body *'));
          const visible = (el) => {
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          };
          const label = (el) => {
            const id = el.id ? `#${el.id}` : '';
            const cls = typeof el.className === 'string' && el.className.trim()
              ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
            return `${el.tagName.toLowerCase()}${id}${cls}`;
          };
          const overflow = all.filter((el) => {
            if (!visible(el) || el.closest('.destination-panel')) return false;
            const rect = el.getBoundingClientRect();
            return rect.right > width + 1 || rect.left < -1;
          }).slice(0, 30).map((el) => {
            const rect = el.getBoundingClientRect();
            return { element: label(el), left: Math.round(rect.left), right: Math.round(rect.right), width: Math.round(rect.width) };
          });
          const ids = all.map((el) => el.id).filter(Boolean);
          const duplicates = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
          const unnamedButtons = Array.from(document.querySelectorAll('button, [role="button"]'))
            .filter(visible)
            .filter((el) => !((el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim()))
            .map(label);
          const emptyLinks = Array.from(document.querySelectorAll('a[href]'))
            .filter(visible)
            .filter((el) => !((el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim()))
            .map(label);
          const brokenImages = Array.from(document.images)
            .filter((img) => (img.currentSrc || img.src) && img.complete && img.naturalWidth === 0)
            .map((img) => img.currentSrc || img.src);
          const unsizedImages = Array.from(document.images)
            .filter((img) => (img.currentSrc || img.src) && (!img.hasAttribute('width') || !img.hasAttribute('height')))
            .map(label).slice(0, 30);
          return {
            title: document.title,
            url: location.href,
            viewport: { width: window.innerWidth, height: window.innerHeight },
            document: { clientWidth: de.clientWidth, scrollWidth: de.scrollWidth, scrollHeight: de.scrollHeight },
            horizontalOverflow: de.scrollWidth > de.clientWidth + 1,
            overflowElements: overflow,
            duplicateIds: duplicates,
            unnamedButtons,
            emptyLinks,
            brokenImages,
            unsizedImages,
            h1Count: document.querySelectorAll('h1').length,
            mainCount: document.querySelectorAll('main').length,
          };
        }
        """
    )


def exercise_page(page: Page, page_name: str) -> dict:
    result: dict[str, object] = {}
    if page_name == "home":
        search = page.locator("#siteSearch")
        if search.count():
            search.fill("青岛")
            page.wait_for_timeout(250)
            result["searchResults"] = page.locator("#siteSearchResults a").count()
            search.fill("")
        destination = page.locator(".destination-nav > summary")
        if destination.count() and destination.is_visible():
            destination.click()
            result["destinationMenuVisible"] = page.locator(".destination-panel").is_visible()
            destination.click()
    elif page_name == "qingdao":
        favorite = page.locator(".co-fav")
        if favorite.count():
            favorite.click()
            result["favoriteSaved"] = page.evaluate("() => JSON.parse(localStorage.getItem('tay_favs') || '[]').some((item) => item.key === 'qingdao')")
        share = page.locator(".co-share")
        result["shareAvailable"] = bool(share.count())
    elif page_name == "user":
        history = page.locator('[data-tab="history"]')
        result["historyTabAvailable"] = bool(history.count())
        tools_tab = page.locator('[data-tab="tools"]')
        if tools_tab.count():
            tools_tab.click()
            result["toolsPanelVisible"] = page.locator('[data-panel="tools"]').is_visible()
    elif page_name == "roadtrip":
        page.locator("#rtOrigin").fill("上海")
        page.locator("#rtDestination").fill("杭州")
        page.locator("#rtDays").fill("3")
        page.locator("#rtGenerate").click()
        page.wait_for_timeout(350)
        result["planVisible"] = page.locator("#rtResults").is_visible()
        result["planDays"] = page.locator("#rtResults .rt-day").count()
    return result


def run(base_url: str, output: Path, phase: str) -> dict:
    phase_dir = output / safe_name(phase)
    phase_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"phase": phase, "baseUrl": base_url, "viewports": {}}
    with sync_playwright() as playwright:
        for viewport_name, viewport in VIEWPORTS.items():
            viewport_report: dict[str, object] = {}
            for page_name, relative_url in PAGES.items():
                # Each audit target gets an isolated connection pool. The home
                # page can legitimately continue decoding lazy media after its
                # screenshot, which must not delay the next independent check.
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport=viewport,
                    device_scale_factor=1,
                    color_scheme="light",
                    reduced_motion="reduce",
                    locale="zh-CN",
                )
                page = context.new_page()
                console_errors: list[str] = []
                page_errors: list[str] = []
                failed_requests: list[str] = []
                bad_responses: list[dict[str, object]] = []
                page.on("console", lambda message, errors=console_errors: errors.append(message.text) if message.type == "error" else None)
                page.on("pageerror", lambda error, errors=page_errors: errors.append(str(error)))
                page.on("requestfailed", lambda request, failures=failed_requests: failures.append(request.url))
                page.on(
                    "response",
                    lambda response, failures=bad_responses: failures.append({"status": response.status, "url": response.url})
                    if response.status >= 400 else None,
                )
                url = urljoin(base_url.rstrip("/") + "/", relative_url)
                response = page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(250)
                above_fold = phase_dir / f"{safe_name(viewport_name)}-{safe_name(page_name)}-above-fold.png"
                page.screenshot(path=str(above_fold), full_page=False, animations="disabled")
                interaction = exercise_page(page, page_name)
                page.wait_for_timeout(150)
                screenshot = phase_dir / f"{safe_name(viewport_name)}-{safe_name(page_name)}.png"
                page.screenshot(path=str(screenshot), full_page=True, animations="disabled")
                viewport_report[page_name] = {
                    "status": response.status if response else None,
                    "screenshot": str(screenshot),
                    "aboveFoldScreenshot": str(above_fold),
                    "consoleErrors": console_errors,
                    "pageErrors": page_errors,
                    "failedRequests": failed_requests,
                    "badResponses": bad_responses,
                    "interaction": interaction,
                    "dom": inspect_dom(page),
                }
                page.close()
                context.close()
                browser.close()
            report["viewports"][viewport_name] = viewport_report
    report_path = phase_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["reportPath"] = str(report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765/")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "browser-audit")
    parser.add_argument("--phase", default="manual")
    args = parser.parse_args()
    report = run(args.base_url, args.output, args.phase)
    print(json.dumps({"phase": report["phase"], "report": report["reportPath"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
