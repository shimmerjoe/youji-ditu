"""Real Edge regressions for the 2026-10-29 planner iterations (optional Playwright)."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import base64
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def fixture(counts=(2, 1)):
    return {"schema": 1, "id": "audit-plan", "title": "周末安排", "startDate": "2026-10-29", "travelers": 2,
            "budget": {"hotelPerNight": 350, "mealsPerPerson": 120, "localTransportPerDay": 60, "intercity": 0, "other": 0},
            "createdAt": "2026-10-29T00:00:00Z", "updatedAt": "2026-10-29T00:00:00Z",
            "days": [{"id": f"day-{d}", "note": "", "items": [
                {"id": f"item-{d}-{i}", "name": f"安排{d + 1}-{i + 1}", "kind": "place", "city": "青岛", "cityKey": "qingdao",
                 "href": "cities/qingdao.html", "time": "", "hours": 1, "cost": 0, "note": "", "booking": False}
                for i in range(count)]} for d, count in enumerate(counts)]}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run(base, output, round_number):
    results = []
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE, headless=True)
        try:
            for width, height in ((1366, 768), (390, 844)):
                context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                def seed(plan):
                    page.goto(base + "plan.html")
                    page.wait_for_load_state("networkidle")
                    page.evaluate("p => { localStorage.clear(); localStorage.setItem('tay_plans', JSON.stringify([p])); localStorage.setItem('tay_active_plan', JSON.stringify(p.id)); }", plan)
                    page.reload()
                    page.wait_for_selector(".plan-bar")

                seed(fixture((15, 15)))
                page.locator('[data-action="remove-day"][data-day="1"]').click()
                assert "无法删除" in page.locator(".plan-status").inner_text()
                assert page.locator(".plan-item").count() == 30
                assert page.evaluate("JSON.parse(localStorage.getItem('tay_plans'))[0].days.length") == 2
                seed(fixture((20, 1)))
                page.locator('[data-action="move-day"]').last.select_option("0")
                assert "没有移动" in page.locator(".plan-status").inner_text()
                assert page.locator(".plan-day").nth(1).locator(".plan-item").count() == 1
                results.append({"width": width, "case": "capacity-no-loss", "passed": True})
                if round_number >= 2:
                    duplicate = fixture()
                    for day in duplicate["days"]:
                        day["id"] = "duplicate"
                        for item in day["items"]:
                            item["id"] = "duplicate"
                    seed(duplicate)
                    note = page.locator('[data-field="note"]').nth(1)
                    note.fill("只改第二项")
                    note.press("Tab")
                    saved = page.evaluate("JSON.parse(localStorage.getItem('tay_plans'))[0]")
                    assert saved["days"][0]["items"][0]["note"] == ""
                    assert saved["days"][0]["items"][1]["note"] == "只改第二项"
                    assert len(set(page.locator("[data-item-id]").evaluate_all("els => els.map(el => el.dataset.itemId)"))) == 3
                    results.append({"width": width, "case": "duplicate-identities", "passed": True})
                if round_number >= 3:
                    seed(fixture())
                    for raw in ({"foo": "bar"}, {"plans": [fixture(), None]}):
                        page.locator('[data-action="import-json"]').set_input_files({"name": "bad.json", "mimeType": "application/json", "buffer": json.dumps(raw).encode()})
                        page.wait_for_function("document.querySelector('.plan-status').textContent.includes('导入失败')")
                        assert page.evaluate("JSON.parse(localStorage.getItem('tay_plans')).length") == 1
                    page.locator('[data-action="import-json"]').set_input_files({"name": "large.json", "mimeType": "application/json", "buffer": b" " * (1024 * 1024 + 1)})
                    assert "超过 1 MB" in page.locator(".plan-status").inner_text()
                    page.locator('[data-action="import-json"]').set_input_files({"name": "good.json", "mimeType": "application/json", "buffer": json.dumps({"schema": 1, "plans": [fixture()]}).encode()})
                    page.wait_for_function("JSON.parse(localStorage.getItem('tay_plans')).length === 2")
                    results.append({"width": width, "case": "validated-import", "passed": True})
                if round_number >= 4:
                    page.evaluate("localStorage.setItem('tay_plans', '{broken'); localStorage.removeItem('tay_storage_meta')")
                    page.reload()
                    page.wait_for_selector(".plan-notice")
                    assert page.evaluate("localStorage.getItem('tay_plans_backup')") == "{broken"
                    assert page.evaluate("localStorage.getItem('tay_plans')") == "{broken"
                    assert "已另存" in page.locator(".plan-notice").inner_text()
                    blocked = browser.new_context(viewport={"width": width, "height": height})
                    blocked.add_init_script("Storage.prototype.getItem = function() { throw new Error('blocked'); }; Storage.prototype.setItem = function() { throw new Error('quota'); };")
                    blocked_page = blocked.new_page()
                    blocked_errors = []
                    blocked_page.on("pageerror", lambda error: blocked_errors.append({"message": error.message, "stack": error.stack}))
                    blocked_page.goto(base + "plan.html")
                    blocked_page.locator('[data-action="new-plan"]').click()
                    assert "保存失败" in blocked_page.locator(".plan-status").inner_text()
                    assert "存储无法读取" in blocked_page.locator(".plan-notice").inner_text()
                    with blocked_page.expect_download() as download:
                        blocked_page.locator('[data-action="export-json"]').click()
                    assert download.value.suggested_filename.endswith(".json")
                    blocked_page.goto(base + "user.html#tab=settings")
                    blocked_page.locator("#dataExport").click()
                    assert "未生成空备份" in blocked_page.locator("#dataTransferStatus").inner_text()
                    assert not blocked_errors, blocked_errors
                    blocked.close()
                    results.append({"width": width, "case": "blocked-storage-export", "passed": True})
                if round_number >= 5:
                    seed(fixture())
                    page.locator('[data-action="share"]').click()
                    share_url = page.locator('[data-fk="share-url"]').input_value()
                    page.goto(share_url)
                    page.wait_for_selector("#planPreviewTitle")
                    ids = page.locator("[id]").evaluate_all("els => els.map(el => el.id)")
                    assert len(ids) == len(set(ids)), "shared and active plan IDs overlap"
                    assert page.locator(".plan-preview input, .plan-preview select, .plan-preview textarea").count() == 0
                    invalid = base64.urlsafe_b64encode(json.dumps({"v": 99, "d": [{"i": []}]}).encode()).decode().rstrip("=")
                    page.goto(base + "plan.html#share=" + invalid)
                    page.wait_for_selector(".plan-notice")
                    assert "不支持" in page.locator(".plan-notice").inner_text()
                    assert page.evaluate("JSON.parse(localStorage.getItem('tay_plans')).length") == 1
                    results.append({"width": width, "case": "share-validation-preview", "passed": True})
                if round_number >= 6:
                    schedule = fixture()
                    schedule["days"][0]["items"][0].update(time="09:00", hours=2)
                    schedule["days"][0]["items"][1].update(time="10:00", hours=1)
                    schedule["days"][1]["items"][0].update(time="23:00", hours=2)
                    seed(schedule)
                    assert "重叠" in page.locator(".plan-schedule").first.inner_text()
                    assert "跨日" in page.locator(".plan-schedule").last.inner_text()
                    assert "11:00" in page.locator(".pi-end").first.inner_text()
                    page.locator('[data-field="time"]').nth(1).fill("12:00")
                    page.locator('[data-field="time"]').nth(1).press("Tab")
                    assert page.locator(".plan-day").first.locator(".plan-schedule").count() == 0
                    results.append({"width": width, "case": "schedule-conflicts", "passed": True})
                if round_number >= 7:
                    buffers = fixture((2,))
                    buffers["days"][0]["items"][0].update(time="09:00", hours=2)
                    buffers["days"][0]["items"][1].update(time="11:30", hours=1)
                    seed(buffers)
                    reserve = page.locator('[data-field="bufferMinutes"]').first
                    reserve.fill("60")
                    reserve.press("Tab")
                    assert "重叠" in page.locator(".plan-schedule").inner_text()
                    assert "约 4 小时" in page.locator(".plan-load").inner_text()
                    page.reload()
                    page.wait_for_selector('[data-field="bufferMinutes"]')
                    assert page.locator('[data-field="bufferMinutes"]').first.input_value() == "60"
                    results.append({"width": width, "case": "travel-buffer-persistence", "passed": True})
                if round_number >= 8:
                    seed(fixture((2,)))
                    cost = page.locator('[data-field="cost"]').first
                    assert cost.input_value() == ""
                    cost.fill("0")
                    cost.press("Tab")
                    assert "还有 1 个地点" in page.locator(".plan-budget").inner_text()
                    page.reload()
                    page.wait_for_selector('[data-field="cost"]')
                    assert page.locator('[data-field="cost"]').first.input_value() == "0"
                    page.locator('[data-field="cost"]').first.fill("")
                    page.locator('[data-field="cost"]').first.press("Tab")
                    assert "还有 2 个地点" in page.locator(".plan-budget").inner_text()
                    results.append({"width": width, "case": "zero-vs-unknown-cost", "passed": True})
                if round_number >= 9:
                    meal = fixture((1,))
                    meal["days"][0]["items"][0].update(kind="food", cost=80, costKnown=True)
                    meal["budget"]["localTransportPerDay"] = 0
                    seed(meal)
                    assert page.locator(".plan-total strong").inner_text() == "¥240"
                    cost = page.locator('[data-field="cost"]').first
                    cost.fill("200")
                    cost.press("Tab")
                    assert page.locator(".plan-total strong").inner_text() == "¥400"
                    stress = fixture((2, 1))
                    stress["travelers"] = 20
                    stress["budget"]["mealsPerPerson"] = 10000
                    stress["budget"]["hotelPerNight"] = 100000
                    stress["budget"]["localTransportPerDay"] = 10000
                    for item in stress["days"][0]["items"]:
                        item.update(cost=100000, costKnown=True)
                    seed(stress)
                    scroll = page.locator(".plan-budget-scroll")
                    assert scroll.evaluate("el => el.scrollWidth > el.clientWidth")
                    scroll.focus()
                    page.keyboard.press("ArrowRight")
                    page.wait_for_function("document.querySelector('.plan-budget-scroll').scrollLeft > 0")
                    results.append({"width": width, "case": "meal-budget-and-large-values", "passed": True})
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), "horizontal overflow"
                assert not errors, errors
                page.screenshot(path=str(output / f"planner-{width}.png"), full_page=True, animations="disabled")
                context.close()
        finally:
            browser.close()
    (output / "browser.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, default=10)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "planner-audit")
    parser.add_argument("--base-url", default="")
    args = parser.parse_args()
    if args.base_url:
        run(args.base_url.rstrip("/") + "/", args.output, args.round)
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "site")))
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            run(f"http://127.0.0.1:{server.server_port}/", args.output, args.round)
        finally:
            server.shutdown()
            server.server_close()
