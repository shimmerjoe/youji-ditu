"""Optional real-Edge release smoke: navigation, saved plans, downloads and offline PWA.

Uses disposable browser contexts, never the user's browser profile. Requires the
Python Playwright package and the Edge executable used by planner_browser_audit.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright
from planner_browser_audit import EDGE, ROOT, QuietHandler, fixture

SIZES = ((1920, 1080), (1366, 768), (390, 844), (360, 800))


def run(base, output):
    output.mkdir(parents=True, exist_ok=True)
    report = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE, headless=True)
        try:
            for width, height in SIZES:
                context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
                page = context.new_page()
                errors, console_errors, failures = [], [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on("requestfailed", lambda request: failures.append({"url": request.url, "reason": request.failure}))
                bad_responses = []
                page.on("response", lambda response: bad_responses.append({"url": response.url, "status": response.status}) if response.status >= 400 else None)

                def snapshot(name):
                    page.wait_for_load_state("networkidle")
                    page.evaluate("scrollTo({top:0,left:0,behavior:'instant'})")
                    page.locator(".plan-side, .plan-budget-scroll").evaluate_all("els => els.forEach(el => el.scrollTo({top:0,left:0,behavior:'instant'}))")
                    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (name, width, "overflow")
                    ids = page.locator("[id]").evaluate_all("els => els.map(el => el.id)")
                    assert len(ids) == len(set(ids)), (name, "duplicate ids", [key for key, count in Counter(ids).items() if count > 1])
                    broken = page.locator("img").evaluate_all("els => els.filter(el => { const r=el.getBoundingClientRect(); return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}) && r.top < innerHeight && r.bottom > 0 && r.left < innerWidth && r.right > 0 && el.complete && !el.naturalWidth; }).map(el => el.outerHTML)")
                    assert not broken, (name, broken)
                    page.screenshot(path=str(output / f"{name}-{width}.png"), full_page=True, animations="disabled")
                    page.screenshot(path=str(output / f"{name}-viewport-{width}.png"), animations="disabled")

                page.goto(base)
                page.wait_for_selector("#siteSearch")
                snapshot("home")
                search = page.locator("#siteSearch")
                search.fill("青岛")
                page.wait_for_selector("#siteSearchOptions .search-result")
                search.press("ArrowDown")
                search.press("Enter")
                page.wait_for_url("**/cities/qingdao.html*")
                assert page.evaluate("JSON.parse(localStorage.getItem('tay_search_recent')).includes('青岛')")
                page.wait_for_function("document.documentElement.dataset.appRuntime === 'ready'")
                favorite = page.locator('.co-fav[data-key="qingdao"]').first
                favorite.click()
                assert favorite.evaluate("el => el.classList.contains('on')")
                assert page.evaluate("JSON.parse(localStorage.getItem('tay_favs')).some(f => f.key === 'qingdao')")
                page.locator("#navToggle").click()
                assert page.locator("#navToggle").get_attribute("aria-expanded") == "true"
                page.locator("#navToggle").click()
                snapshot("city")

                page.goto(base)
                page.wait_for_selector("#travelQuery")
                page.locator("#travelQuery").fill("青岛")
                page.locator("#travelSeason").select_option("夏")
                page.wait_for_function("new URLSearchParams(location.search).get('q') === '青岛'")
                assert "season=" in page.url
                page.reload()
                assert page.locator("#travelQuery").input_value() == "青岛"
                assert page.locator("#travelSeason").input_value() == "夏"
                assert page.locator("#cityExplorer .city-card:not(.is-hidden)").count() >= 1
                page.locator("#travelQuery").fill("不存在的目的地测试")
                assert page.locator("#cityExplorerEmpty").is_visible()
                page.locator("#finderChips .clear-all").click()
                assert page.locator("#cityExplorer .city-card:not(.is-hidden)").count() > 0
                page.goto(base + "user.html")
                page.wait_for_selector("#userTabs")
                snapshot("user")

                plan = fixture()
                for day in plan["days"]:
                    for item in day["items"]:
                        item.update(bufferMinutes=0, costKnown=False)
                plan["days"][0]["items"][0].update(time="09:00", hours=1, bufferMinutes=30, costKnown=True, note="私人备注测试")
                page.goto(base + "plan.html")
                page.wait_for_selector("[data-action='new-plan']")
                page.evaluate("p => { localStorage.setItem('tay_plans', JSON.stringify([p])); localStorage.setItem('tay_active_plan', JSON.stringify(p.id)); }", plan)
                page.reload()
                page.wait_for_selector(".plan-item")
                with page.expect_download() as download:
                    page.locator('[data-action="export-json"]').click()
                backup = Path(download.value.path()).read_bytes()
                assert len(json.loads(backup)["plans"][0]["days"]) == 2
                with page.expect_download() as download:
                    page.locator('[data-action="export-md"]').click()
                markdown = Path(download.value.path()).read_text(encoding="utf-8-sig")
                assert "私人备注测试" in markdown and "30" in markdown
                page.once("dialog", lambda dialog: dialog.accept())
                page.locator('[data-action="delete-plan"]').click()
                assert page.locator(".plan-item").count() == 0
                page.locator('[data-action="import-json"]').set_input_files({"name": "restore.json", "mimeType": "application/json", "buffer": backup})
                page.wait_for_selector(".plan-item")
                assert page.locator(".plan-item").count() == 3
                assert page.locator('[data-field="bufferMinutes"]').first.input_value() == "30"
                assert page.locator('[data-field="cost"]').first.input_value() == "0"
                page.locator('[data-action="share"]').click()
                share_url = page.locator('[data-fk="share-url"]').input_value()
                recipient = browser.new_context(viewport={"width": width, "height": height})
                recipient_page = recipient.new_page()
                recipient_page.goto(share_url)
                recipient_page.wait_for_selector("#planPreviewTitle")
                assert "私人备注测试" not in recipient_page.locator(".plan-preview").inner_text()
                recipient_page.locator('[data-action="save-shared"]').click()
                assert recipient_page.locator(".plan-item").count() == 3
                assert recipient_page.locator('[data-field="bufferMinutes"]').first.input_value() == "30"
                recipient.close()
                page.evaluate("window.auditPrintCalled=false; window.print=()=>{window.auditPrintCalled=true;}")
                page.locator('[data-action="print"]').click()
                assert page.evaluate("window.auditPrintCalled")
                page.emulate_media(media="print")
                assert page.locator(".plan-day").first.is_visible()
                page.emulate_media(media="screen")
                snapshot("planner")

                page.goto(base + "roadtrip.html")
                page.locator("#rtOrigin").fill("青岛")
                page.locator("#rtDestination").fill("济南")
                page.locator("#rtDays").fill("3")
                page.locator('[data-rt-next="2"]').click()
                page.locator('[data-rt-next="3"]').click()
                offline_details = page.locator("#rtEstimatedKm").locator("xpath=ancestor::details[1]")
                if offline_details.count() and offline_details.get_attribute("open") is None:
                    offline_details.locator("summary").click()
                page.locator("#rtEstimatedKm").fill("380")
                page.locator("#rtGenerate").click()
                page.wait_for_selector(".rt-day")
                assert page.locator(".rt-day").count() == 3
                page.locator("#rtSave").click()
                assert page.evaluate("JSON.parse(localStorage.getItem('tay_roadtrips')).length") == 1
                with page.expect_download() as download:
                    page.locator("#rtExport").click()
                assert download.value.suggested_filename.endswith(".md")
                page.reload()
                page.wait_for_selector(".rt-day")
                assert "恢复上次" in page.locator("#rtMapStatus").inner_text()
                snapshot("roadtrip")
                assert not errors and not console_errors and not failures and not bad_responses, (errors, console_errors, failures, bad_responses)
                online = {"onlinePageErrors": list(errors), "onlineConsoleErrors": list(console_errors),
                          "onlineNetworkFailures": list(failures), "onlineBadResponses": list(bad_responses)}

                page.goto(base + "plan.html")
                page.evaluate("navigator.serviceWorker.ready.then(() => true)")
                page.wait_for_function("navigator.serviceWorker.controller !== null")
                context.set_offline(True)
                response = page.reload()
                assert response.status == 200
                page.wait_for_selector(".plan-item")
                assert page.locator(".plan-item").count() == 3
                page.locator('[data-field="title"]').fill("离线编排可恢复")
                page.locator('[data-field="title"]').press("Tab")
                page.reload()
                assert page.locator('[data-field="title"]').input_value() == "离线编排可恢复"
                page.screenshot(path=str(output / f"offline-{width}.png"), full_page=True, animations="disabled")
                response = page.goto(base + "never-cached-audit.html")
                assert response.status == 503
                assert page.get_by_role("heading", name="当前处于离线状态").is_visible()
                assert not errors, errors
                context.close()
                report.append({"width": width, "height": height, "passed": True,
                               "cases": ["keyboard-search-history", "favorite", "navigation", "filter-url-reload-empty",
                                         "json-roundtrip", "markdown", "share-save-private-notes", "print-handler-and-media",
                                         "roadtrip-generate-save-export-restore", "offline-plan-edit-reload", "offline-fallback"],
                               **online, "uncachedOfflineFallbackStatus": 503})
        finally:
            browser.close()
    (output / "release.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "release-audit")
    args = parser.parse_args()
    if args.base_url:
        run(args.base_url.rstrip("/") + "/", args.output)
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "site")))
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            run(f"http://127.0.0.1:{server.server_port}/", args.output)
        finally:
            server.shutdown()
            server.server_close()
