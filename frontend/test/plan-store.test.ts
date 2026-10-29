import assert from "node:assert/strict";
import test from "node:test";
import { createPlan } from "../src/trip-plan.ts";
import { loadPlans, loadActivePlanId, savePlans, PLANS_KEY, PLANS_BACKUP_KEY } from "../src/plan-store.ts";

function usingStorage(store: object, run: () => void): void {
  const previous = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: store });
  try { run(); } finally {
    if (previous) Object.defineProperty(globalThis, "localStorage", previous);
    else Reflect.deleteProperty(globalThis, "localStorage");
  }
}

test("storage reads and writes can fail without crashing the app", () => {
  usingStorage({ getItem() { throw new Error("blocked"); }, setItem() { throw new Error("quota"); } }, () => {
    assert.equal(loadPlans().unavailable, true);
    assert.equal(loadActivePlanId(), "");
    assert.equal(savePlans([createPlan("临时行程")]), false);
  });
});

test("corrupt raw data is backed up only when storage actually accepts it", () => {
  const data = new Map([[PLANS_KEY, "{broken"]]);
  usingStorage({ getItem(key: string) { return data.get(key) ?? null; }, setItem(key: string, value: string) { data.set(key, value); } }, () => {
    const result = loadPlans();
    assert.equal(result.unreadable, true);
    assert.equal(result.backupSaved, true);
    assert.equal(data.get(PLANS_BACKUP_KEY), "{broken");
  });
  usingStorage({ getItem(key: string) { return key === PLANS_KEY ? "{broken" : null; }, setItem() { throw new Error("quota"); } }, () => {
    assert.equal(loadPlans().backupSaved, false);
  });
});

test("repair detects nested loss and ID changes but ignores object key order", () => {
  const valid = createPlan("有效");
  usingStorage({ getItem(key: string) { return key === PLANS_KEY ? JSON.stringify([Object.fromEntries(Object.entries(valid).reverse())]) : null; }, setItem() {} }, () => {
    assert.equal(loadPlans().repaired, false);
  });
  valid.days[1].id = valid.days[0].id;
  usingStorage({ getItem(key: string) { return key === PLANS_KEY ? JSON.stringify([valid]) : null; }, setItem() {} }, () => {
    assert.equal(loadPlans().repaired, true);
    assert.equal(loadPlans().backupSaved, true);
  });
});

test("a failed raw backup prevents overwriting corrupt originals even if the main key is writable", () => {
  const data = new Map([[PLANS_KEY, "{unrecoverable"]]);
  usingStorage({
    getItem(key: string) { return data.get(key) ?? null; },
    setItem(key: string, value: string) { if (key === PLANS_BACKUP_KEY) throw new Error("quota"); data.set(key, value); },
  }, () => {
    assert.equal(savePlans([createPlan("新行程")]), false);
    assert.equal(data.get(PLANS_KEY), "{unrecoverable");
  });
});
