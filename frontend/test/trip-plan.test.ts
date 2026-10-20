import assert from "node:assert/strict";
import test from "node:test";
import {
  addDay,
  addItem,
  clonePlan,
  createPlan,
  dayDate,
  dayLoad,
  decodeShare,
  encodeShare,
  estimateBudget,
  mapSearchUrl,
  moveItem,
  normalizePlan,
  normalizePlans,
  planToMarkdown,
  removeDay,
  removeItem,
  shiftItem,
  sortDayByTime,
  todayIndex,
  updateItem,
} from "../src/trip-plan.ts";


function samplePlan() {
  const plan = createPlan("北京周末", 2);
  plan.startDate = "2026-10-24";
  plan.travelers = 2;
  addItem(plan, 0, { name: "故宫博物院", city: "北京", cityKey: "beijing", href: "cities/beijing.html#attractions-item-1", hours: 4, cost: 60, booking: true });
  addItem(plan, 0, { name: "北京烤鸭", kind: "food", city: "北京", cityKey: "beijing", hours: 1.5 });
  addItem(plan, 1, { name: "八达岭长城", city: "北京", cityKey: "beijing", hours: 5, cost: 40 });
  return plan;
}


test("corrupt or hostile stored data is repaired instead of rendered", () => {
  assert.equal(normalizePlan(null), null);
  assert.equal(normalizePlan("text"), null);
  const plan = normalizePlan({
    title: "  ",
    travelers: 999,
    startDate: "2026-02-30",
    days: [{ items: [{ name: "" }, { name: "西湖", href: "javascript:alert(1)", hours: 99, cost: -5, time: "25:00" }] }],
  });
  assert.ok(plan);
  assert.equal(plan.title, "未命名行程");
  assert.equal(plan.travelers, 20);
  assert.equal(plan.startDate, "");
  assert.equal(plan.days[0].items.length, 1);
  const [item] = plan.days[0].items;
  assert.equal(item.href, "");
  assert.equal(item.hours, 12);
  assert.equal(item.cost, 0);
  assert.equal(item.time, "");
  assert.deepEqual(normalizePlans("nope"), []);
  const plans = normalizePlans([{ id: "same", title: "a" }, { id: "same", title: "b" }, 3]);
  assert.equal(plans.length, 2);
  assert.notEqual(plans[0].id, plans[1].id);
});


test("items can move between days, reorder, update and be removed", () => {
  const plan = samplePlan();
  const duck = plan.days[0].items[1];
  assert.ok(moveItem(plan, duck.id, 1, 0));
  assert.deepEqual(plan.days[1].items.map((item) => item.name), ["北京烤鸭", "八达岭长城"]);
  assert.ok(shiftItem(plan, duck.id, 1));
  assert.deepEqual(plan.days[1].items.map((item) => item.name), ["八达岭长城", "北京烤鸭"]);
  assert.equal(shiftItem(plan, duck.id, 1), false);
  const updated = updateItem(plan, duck.id, { time: "18:30", note: "提前取号" });
  assert.equal(updated?.time, "18:30");
  updateItem(plan, plan.days[1].items[0].id, { time: "08:00" });
  sortDayByTime(plan, 1);
  assert.deepEqual(plan.days[1].items.map((item) => item.time), ["08:00", "18:30"]);
  assert.equal(removeItem(plan, duck.id)?.name, "北京烤鸭");
  assert.equal(removeItem(plan, "missing"), null);
});


test("removing a day keeps its stops instead of silently deleting them", () => {
  const plan = samplePlan();
  assert.ok(addDay(plan));
  assert.equal(plan.days.length, 3);
  assert.ok(removeDay(plan, 1));
  assert.equal(plan.days.length, 2);
  assert.deepEqual(plan.days[0].items.map((item) => item.name), ["故宫博物院", "北京烤鸭", "八达岭长城"]);
  const single = createPlan("一天", 1);
  assert.equal(removeDay(single, 0), false);
});


test("day load flags overfull and cross-city days", () => {
  const plan = samplePlan();
  assert.equal(dayLoad(plan.days[0]).level, "balanced");
  assert.equal(dayLoad({ id: "x", note: "", items: [] }).level, "empty");
  addItem(plan, 1, { name: "颐和园", city: "北京", cityKey: "beijing", hours: 3 });
  assert.equal(dayLoad(plan.days[1]).level, "full");
  const cross = createPlan("跨城", 1);
  addItem(cross, 0, { name: "A", cityKey: "a", hours: 3 });
  addItem(cross, 0, { name: "B", cityKey: "b", hours: 3 });
  assert.equal(dayLoad(cross.days[0]).level, "full");
  const park = createPlan("乐园", 1);
  addItem(park, 0, { name: "主题乐园", cityKey: "x", hours: 10 });
  assert.equal(dayLoad(park.days[0]).level, "full");
  assert.match(dayLoad(park.days[0]).label, /整天项目/);
});


test("budget separates per-day, total and per-person and counts nights correctly", () => {
  const plan = samplePlan();
  plan.budget = { hotelPerNight: 400, mealsPerPerson: 100, localTransportPerDay: 50, intercity: 600, other: 0 };
  const budget = estimateBudget(plan);
  assert.equal(budget.nights, 1);
  assert.deepEqual(budget.days[0], { hotel: 400, meals: 200, transport: 50, tickets: 120, total: 770 });
  assert.deepEqual(budget.days[1], { hotel: 0, meals: 200, transport: 50, tickets: 80, total: 330 });
  assert.equal(budget.total, 770 + 330 + 600);
  assert.equal(budget.perPerson, 850);
  assert.equal(budget.itemsWithoutCost, 1);
});


test("dates and today's index follow the start date", () => {
  const plan = samplePlan();
  assert.equal(dayDate(plan, 1), "2026-10-25");
  assert.equal(todayIndex(plan, "2026-10-25"), 1);
  assert.equal(todayIndex(plan, "2026-10-26"), -1);
  plan.startDate = "";
  assert.equal(todayIndex(plan, "2026-10-25"), -1);
});


test("share links exclude personal notes unless explicitly included", () => {
  const plan = samplePlan();
  plan.days[0].note = "住在王府井附近";
  updateItem(plan, plan.days[0].items[0].id, { note: "身份证号已记" });
  const shared = decodeShare(encodeShare(plan));
  assert.ok(shared);
  assert.equal(shared.title, "北京周末");
  assert.equal(shared.days[0].note, "");
  assert.equal(shared.days[0].items[0].note, "");
  assert.equal(shared.days[0].items[0].booking, true);
  assert.equal(shared.days[1].items[0].name, "八达岭长城");
  const withNotes = decodeShare(encodeShare(plan, { includeNotes: true }));
  assert.equal(withNotes?.days[0].note, "住在王府井附近");
  assert.equal(decodeShare("%%%"), null);
});


test("copies get fresh identities and markdown labels estimates honestly", () => {
  const plan = samplePlan();
  const copy = clonePlan(plan);
  assert.notEqual(copy.id, plan.id);
  assert.notEqual(copy.days[0].items[0].id, plan.days[0].items[0].id);
  assert.equal(copy.days[0].items[0].name, "故宫博物院");
  const markdown = planToMarkdown(plan, "https://example.test/site/");
  assert.match(markdown, /# 北京周末/);
  assert.match(markdown, /不是实时报价/);
  assert.match(markdown, /北京烤鸭.*费用待核验/);
  addItem(plan, 0, { name: "酒店寄存行李", kind: "custom" });
  assert.doesNotMatch(planToMarkdown(plan), /酒店寄存行李.*费用待核验/);
  assert.match(markdown, /\(https:\/\/example\.test\/site\/cities\/beijing\.html#attractions-item-1\)/);
  assert.match(mapSearchUrl({ name: "故宫博物院", city: "北京" }), /^https:\/\/uri\.amap\.com\/search\?keyword=%E5%8C%97/);
});
