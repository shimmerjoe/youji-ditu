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
          const resources = performance.getEntriesByType('resource');
          const imageResources = resources.filter((entry) => entry.initiatorType === 'img');
          const carouselImages = Array.from(document.querySelectorAll('#heroCarousel img'));
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
            nodeCount: all.length,
            imageCount: document.images.length,
            loadedImageCount: Array.from(document.images).filter((img) => Boolean(img.currentSrc || img.src)).length,
            carouselImageCount: carouselImages.length,
            hydratedCarouselImageCount: carouselImages.filter((img) => Boolean(img.currentSrc || img.src)).length,
            resourceCount: resources.length,
            imageResourceCount: imageResources.length,
            transferSize: resources.reduce((sum, entry) => sum + Number(entry.transferSize || 0), 0),
            decodedBodySize: resources.reduce((sum, entry) => sum + Number(entry.decodedBodySize || 0), 0),
            h1Count: document.querySelectorAll('h1').length,
            mainCount: document.querySelectorAll('main').length,
          };
        }
        """
    )


def exercise_page(page: Page, page_name: str, interaction_screenshot: Path | None = None) -> dict:
    result: dict[str, object] = {}
    if page_name == "home":
        search = page.locator("#siteSearch")
        if search.count():
            search.fill("青岛")
            page.wait_for_function("() => Array.isArray(window.TRAVEL_SEARCH_INDEX) && window.TRAVEL_SEARCH_INDEX.length > 0")
            result["searchResults"] = page.locator("#siteSearchResults a").count()
            search.fill("")
        destination = page.locator(".destination-nav > summary")
        if destination.count() and destination.is_visible():
            destination.click()
            result["destinationMenuVisible"] = page.locator(".destination-panel").is_visible()
            destination.click()
        trip_button = page.locator(".trip-btn:visible").first
        if trip_button.count():
            trip_button.click()
            result["tripDockCountAfterAdd"] = page.locator("#tripDockCount").text_content()
            dock_toggle = page.locator("#tripDockToggle")
            dock_toggle.click()
            result["tripDockVisible"] = page.locator("#tripDock").is_visible()
            result["tripDockItems"] = page.locator("#tripDockList .trip-dock-item").count()
            result["tripDockFirstHref"] = page.locator("#tripDockList a").first.get_attribute("href")
            if interaction_screenshot is not None:
                page.screenshot(path=str(interaction_screenshot), full_page=False, animations="disabled")
                result["tripDockScreenshot"] = str(interaction_screenshot)
            page.keyboard.press("Escape")
            result["tripDockClosedWithEscape"] = not page.locator("#tripDock").is_visible()
            result["tripDockFocusReturned"] = page.evaluate("() => document.activeElement === document.getElementById('tripDockToggle')")
    elif page_name == "qingdao":
        favorite = page.locator(".co-fav")
        if favorite.count():
            favorite.click()
            result["favoriteSaved"] = page.evaluate("() => JSON.parse(localStorage.getItem('tay_favs') || '[]').some((item) => item.key === 'qingdao')")
        share = page.locator(".co-share")
        result["shareAvailable"] = bool(share.count())
        trip = page.locator(".co-trip")
        if trip.count():
            trip.click()
            page.locator("#tripDockToggle").click()
            result["tripDockCityHref"] = page.locator("#tripDockList a").first.get_attribute("href")
            result["tripDockCityItemVisible"] = page.locator("#tripDockList .trip-dock-item").first.is_visible()
            page.locator("#tripDockClose").click()
    elif page_name == "user":
        history = page.locator('[data-tab="history"]')
        result["historyTabAvailable"] = bool(history.count())
        profile = page.locator('[data-tab="profile"]')
        if profile.count():
            profile.focus()
            profile.press("End")
            result["keyboardEndTab"] = page.locator('[role="tab"][aria-selected="true"]').get_attribute("data-tab")
            page.locator('[role="tab"][aria-selected="true"]').press("Home")
            result["keyboardHomeTab"] = page.locator('[role="tab"][aria-selected="true"]').get_attribute("data-tab")
        tools_tab = page.locator('[data-tab="tools"]')
        if tools_tab.count():
            tools_tab.click()
            result["toolsPanelVisible"] = page.locator('[data-panel="tools"]').is_visible()
    elif page_name == "roadtrip":
        idle_box = page.locator(".rt-map-frame").bounding_box()
        result["idleMapHeight"] = round(idle_box["height"]) if idle_box else None
        result["resultActionsInitiallyHidden"] = not page.locator(".rt-result-actions").is_visible()
        page.locator("#rtOrigin").fill("上海")
        page.locator("#rtDestination").fill("杭州")
        page.locator("#rtDays").fill("3")
        page.locator('[data-rt-next="2"]').click()
        result["step2Visible"] = page.locator('[data-rt-step="2"]').is_visible()
        page.locator('[data-rt-next="3"]').click()
        result["step3Visible"] = page.locator('[data-rt-step="3"]').is_visible()
        page.locator("#rtGenerate").click()
        page.wait_for_timeout(350)
        result["planVisible"] = page.locator("#rtResults").is_visible()
        result["planDays"] = page.locator("#rtResults .rt-day").count()
        result["resultActionsVisible"] = page.locator(".rt-result-actions").is_visible()
        expanded_box = page.locator(".rt-map-frame").bounding_box()
        result["expandedMapHeight"] = round(expanded_box["height"]) if expanded_box else None
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
                initial_resources = page.evaluate(
                    """() => {
                      const resources = performance.getEntriesByType('resource');
                      return {
                        count: resources.length,
                        transferSize: resources.reduce((sum, entry) => sum + Number(entry.transferSize || 0), 0),
                        decodedBodySize: resources.reduce((sum, entry) => sum + Number(entry.decodedBodySize || 0), 0),
                        searchIndexRequested: resources.some((entry) => entry.name.includes('/search-index.js')),
                      };
                    }"""
                )
                above_fold = phase_dir / f"{safe_name(viewport_name)}-{safe_name(page_name)}-above-fold.png"
                page.screenshot(path=str(above_fold), full_page=False, animations="disabled")
                interaction_screenshot = phase_dir / f"{safe_name(viewport_name)}-{safe_name(page_name)}-interaction.png"
                interaction = exercise_page(page, page_name, interaction_screenshot if page_name == "home" else None)
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
                    "initialResources": initial_resources,
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
