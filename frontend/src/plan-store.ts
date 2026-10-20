/**
 * 行程计划的本机存储：localStorage 读写、损坏数据备份、写入失败提示与跨标签同步。
 * 与 travel.js 的本地数据适配器共用 `tay:storage-change` 事件和键名约定，
 * 因此用户中心的备份、导入与“清除本地数据”同样覆盖行程计划。
 */
import { normalizePlans, type TripPlan } from "./trip-plan.ts";

export const PLANS_KEY = "tay_plans";
export const ACTIVE_PLAN_KEY = "tay_active_plan";
export const PLANS_BACKUP_KEY = "tay_plans_backup";

export interface PlanLoadResult {
  plans: TripPlan[];
  /** 存储中的原始数据无法解析或部分条目被丢弃 */
  repaired: boolean;
}

function storage(): Storage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

function emit(key: string, action: string): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("tay:storage-change", { detail: { key, action } }));
}

export function loadPlans(): PlanLoadResult {
  const store = storage();
  const raw = store?.getItem(PLANS_KEY) ?? null;
  if (raw == null) return { plans: [], repaired: false };
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    parsed = undefined;
  }
  const plans = normalizePlans(parsed);
  const repaired = !Array.isArray(parsed) || plans.length !== parsed.length;
  if (repaired && store && !store.getItem(PLANS_BACKUP_KEY)) {
    // 保留一份原始数据，避免修复逻辑误伤时无法找回。
    try { store.setItem(PLANS_BACKUP_KEY, raw); } catch { /* 空间不足时放弃备份，不阻塞使用 */ }
  }
  return { plans, repaired };
}

export function savePlans(plans: TripPlan[]): boolean {
  const store = storage();
  if (!store) return false;
  try {
    store.setItem(PLANS_KEY, JSON.stringify(plans));
    emit(PLANS_KEY, "set");
    return true;
  } catch {
    return false;
  }
}

export function loadActivePlanId(): string {
  const raw = storage()?.getItem(ACTIVE_PLAN_KEY);
  if (!raw) return "";
  try {
    const value: unknown = JSON.parse(raw);
    return typeof value === "string" ? value : "";
  } catch {
    return raw;
  }
}

export function saveActivePlanId(id: string): void {
  const store = storage();
  if (!store) return;
  try {
    store.setItem(ACTIVE_PLAN_KEY, JSON.stringify(id));
    emit(ACTIVE_PLAN_KEY, "set");
  } catch { /* 激活状态丢失不影响行程本身 */ }
}

/** 本标签或其他标签修改了行程时回调（不包括本模块尚未写入的草稿）。 */
export function onPlansChanged(callback: () => void): void {
  if (typeof window === "undefined") return;
  window.addEventListener("storage", (event) => {
    if (event.key === PLANS_KEY || event.key === ACTIVE_PLAN_KEY || event.key === null) callback();
  });
}
