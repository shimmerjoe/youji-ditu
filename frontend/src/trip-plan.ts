/**
 * 按天编排的行程计划：纯数据模型与计算，不触碰 DOM 或 localStorage，便于测试。
 *
 * 所有费用都是“按用户假设计算的参考估算”，不是实时报价；停留时长默认值
 * 只是排程起点，界面上会提示用户按实际调整。
 */

export const PLAN_SCHEMA = 1;
export const MAX_DAYS = 30;
export const MAX_ITEMS_PER_DAY = 20;

export type PlanItemKind = "place" | "food" | "custom";

export interface PlanItem {
  id: string;
  name: string;
  kind: PlanItemKind;
  /** 所属城市的显示名，例如“北京” */
  city: string;
  /** 城市页 key，用于回链与导航搜索；自定义条目可为空 */
  cityKey: string;
  /** 相对站点根的攻略链接，例如 cities/beijing.html#attractions-item-xxx */
  href: string;
  /** 计划开始时间 HH:MM，可为空 */
  time: string;
  /** 预计停留小时数（0.5 – 12） */
  hours: number;
  /** 每人参考门票/消费（元），0 表示未填写 */
  cost: number;
  note: string;
  /** 用户标记“需要预约” */
  booking: boolean;
}

export interface PlanDay {
  id: string;
  note: string;
  items: PlanItem[];
}

export interface BudgetAssumptions {
  /** 每晚住宿总价（整间/整组，元） */
  hotelPerNight: number;
  /** 每人每天餐饮（元） */
  mealsPerPerson: number;
  /** 每天市内交通总额（元） */
  localTransportPerDay: number;
  /** 往返大交通总额（元，全体） */
  intercity: number;
  /** 其他总额（元） */
  other: number;
}

export interface TripPlan {
  schema: number;
  id: string;
  title: string;
  startDate: string;
  travelers: number;
  budget: BudgetAssumptions;
  days: PlanDay[];
  createdAt: string;
  updatedAt: string;
}

export interface DayLoad {
  hours: number;
  stops: number;
  level: "empty" | "light" | "balanced" | "full";
  label: string;
}

export interface DayBudget {
  hotel: number;
  meals: number;
  transport: number;
  tickets: number;
  total: number;
}

export interface PlanBudget {
  days: DayBudget[];
  nights: number;
  intercity: number;
  other: number;
  total: number;
  perPerson: number;
  /** 有多少条目没有填写费用（提示用户估算不完整） */
  itemsWithoutCost: number;
}

export const DEFAULT_BUDGET: BudgetAssumptions = {
  hotelPerNight: 350,
  mealsPerPerson: 120,
  localTransportPerDay: 60,
  intercity: 0,
  other: 0,
};

export function makeId(prefix = "p", random: () => number = Math.random, now: () => number = Date.now): string {
  return `${prefix}-${now().toString(36)}-${Math.floor(random() * 1e8).toString(36)}`;
}

function text(value: unknown, max: number): string {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim().slice(0, max) : "";
}

function longText(value: unknown, max: number): string {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

function number(value: unknown, min: number, max: number, fallback: number): number {
  const parsed = typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function validDate(value: unknown): string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value ? "" : value;
}

function validTime(value: unknown): string {
  return typeof value === "string" && /^([01]\d|2[0-3]):[0-5]\d$/.test(value) ? value : "";
}

/** 只接受站内相对链接，避免把外部或脚本链接写进可分享的行程。 */
function safeHref(value: unknown): string {
  const href = text(value, 300);
  if (!href || /^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith("//")) return "";
  return href.replace(/^(?:\.\.\/|\.\/)+/, "").replace(/^\//, "");
}

export function normalizeItem(raw: unknown): PlanItem | null {
  if (!raw || typeof raw !== "object") return null;
  const value = raw as Record<string, unknown>;
  const name = text(value.name, 60);
  if (!name) return null;
  const kind = value.kind === "food" || value.kind === "custom" ? value.kind : "place";
  return {
    id: text(value.id, 40) || makeId("i"),
    name,
    kind,
    city: text(value.city, 20),
    cityKey: text(value.cityKey, 40),
    href: safeHref(value.href),
    time: validTime(value.time),
    hours: Math.round(number(value.hours, 0.5, 12, kind === "food" ? 1 : 2) * 2) / 2,
    cost: Math.round(number(value.cost, 0, 100000, 0)),
    note: longText(value.note, 400),
    booking: value.booking === true,
  };
}

export function normalizeDay(raw: unknown): PlanDay | null {
  if (!raw || typeof raw !== "object") return null;
  const value = raw as Record<string, unknown>;
  const items = Array.isArray(value.items)
    ? value.items.map(normalizeItem).filter((item): item is PlanItem => item !== null).slice(0, MAX_ITEMS_PER_DAY)
    : [];
  return { id: text(value.id, 40) || makeId("d"), note: longText(value.note, 400), items };
}

export function normalizeBudget(raw: unknown): BudgetAssumptions {
  const value = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  return {
    hotelPerNight: Math.round(number(value.hotelPerNight, 0, 100000, DEFAULT_BUDGET.hotelPerNight)),
    mealsPerPerson: Math.round(number(value.mealsPerPerson, 0, 10000, DEFAULT_BUDGET.mealsPerPerson)),
    localTransportPerDay: Math.round(number(value.localTransportPerDay, 0, 10000, DEFAULT_BUDGET.localTransportPerDay)),
    intercity: Math.round(number(value.intercity, 0, 1000000, DEFAULT_BUDGET.intercity)),
    other: Math.round(number(value.other, 0, 1000000, DEFAULT_BUDGET.other)),
  };
}

/** 校验并修复一份来自存储、导入或分享链接的行程；完全不可用时返回 null。 */
export function normalizePlan(raw: unknown): TripPlan | null {
  if (!raw || typeof raw !== "object") return null;
  const value = raw as Record<string, unknown>;
  const days = Array.isArray(value.days)
    ? value.days.map(normalizeDay).filter((day): day is PlanDay => day !== null).slice(0, MAX_DAYS)
    : [];
  const now = new Date().toISOString();
  return {
    schema: PLAN_SCHEMA,
    id: text(value.id, 40) || makeId(),
    title: text(value.title, 40) || "未命名行程",
    startDate: validDate(value.startDate),
    travelers: Math.round(number(value.travelers, 1, 20, 2)),
    budget: normalizeBudget(value.budget),
    days: days.length ? days : [{ id: makeId("d"), note: "", items: [] }],
    createdAt: text(value.createdAt, 40) || now,
    updatedAt: text(value.updatedAt, 40) || now,
  };
}

export function normalizePlans(raw: unknown): TripPlan[] {
  if (!Array.isArray(raw)) return [];
  const seen = new Set<string>();
  const plans: TripPlan[] = [];
  for (const candidate of raw) {
    const plan = normalizePlan(candidate);
    if (!plan) continue;
    if (seen.has(plan.id)) plan.id = makeId();
    seen.add(plan.id);
    plans.push(plan);
  }
  return plans;
}

export function createPlan(title: string, dayCount = 2, now = new Date()): TripPlan {
  const days = Array.from({ length: Math.min(MAX_DAYS, Math.max(1, dayCount)) }, () => ({ id: makeId("d"), note: "", items: [] }));
  return normalizePlan({ title, days, createdAt: now.toISOString(), updatedAt: now.toISOString() }) as TripPlan;
}

function touch(plan: TripPlan): TripPlan {
  plan.updatedAt = new Date().toISOString();
  return plan;
}

export function clonePlan(plan: TripPlan, title = `${plan.title}（副本）`): TripPlan {
  const copy = normalizePlan(JSON.parse(JSON.stringify(plan))) as TripPlan;
  copy.id = makeId();
  copy.title = title.slice(0, 40);
  copy.days = copy.days.map((day) => ({ ...day, id: makeId("d"), items: day.items.map((item) => ({ ...item, id: makeId("i") })) }));
  copy.createdAt = new Date().toISOString();
  return touch(copy);
}

export function addDay(plan: TripPlan): boolean {
  if (plan.days.length >= MAX_DAYS) return false;
  plan.days.push({ id: makeId("d"), note: "", items: [] });
  touch(plan);
  return true;
}

/** 删除某天；该天条目并入前一天（第一天则并入后一天），避免误删内容。 */
export function removeDay(plan: TripPlan, dayIndex: number): boolean {
  if (plan.days.length <= 1 || !plan.days[dayIndex]) return false;
  const [removed] = plan.days.splice(dayIndex, 1);
  const target = plan.days[Math.max(0, dayIndex - 1)];
  target.items.push(...removed.items.slice(0, MAX_ITEMS_PER_DAY - target.items.length));
  touch(plan);
  return true;
}

export function addItem(plan: TripPlan, dayIndex: number, raw: Partial<PlanItem>): PlanItem | null {
  const day = plan.days[dayIndex];
  const item = normalizeItem({ ...raw, id: makeId("i") });
  if (!day || !item || day.items.length >= MAX_ITEMS_PER_DAY) return null;
  day.items.push(item);
  touch(plan);
  return item;
}

export function findItem(plan: TripPlan, itemId: string): { day: number; index: number } | null {
  for (let day = 0; day < plan.days.length; day += 1) {
    const index = plan.days[day].items.findIndex((item) => item.id === itemId);
    if (index >= 0) return { day, index };
  }
  return null;
}

/** 把条目移动到指定天的指定位置（默认末尾）。 */
export function moveItem(plan: TripPlan, itemId: string, toDay: number, toIndex?: number): boolean {
  const from = findItem(plan, itemId);
  const target = plan.days[toDay];
  if (!from || !target) return false;
  if (from.day !== toDay && target.items.length >= MAX_ITEMS_PER_DAY) return false;
  const [item] = plan.days[from.day].items.splice(from.index, 1);
  const index = toIndex === undefined ? target.items.length : Math.max(0, Math.min(toIndex, target.items.length));
  target.items.splice(index, 0, item);
  touch(plan);
  return true;
}

export function shiftItem(plan: TripPlan, itemId: string, delta: -1 | 1): boolean {
  const from = findItem(plan, itemId);
  if (!from) return false;
  const items = plan.days[from.day].items;
  const next = from.index + delta;
  if (next < 0 || next >= items.length) return false;
  [items[from.index], items[next]] = [items[next], items[from.index]];
  touch(plan);
  return true;
}

export function updateItem(plan: TripPlan, itemId: string, patch: Partial<PlanItem>): PlanItem | null {
  const from = findItem(plan, itemId);
  if (!from) return null;
  const current = plan.days[from.day].items[from.index];
  const next = normalizeItem({ ...current, ...patch, id: current.id });
  if (!next) return null;
  plan.days[from.day].items[from.index] = next;
  touch(plan);
  return next;
}

export function removeItem(plan: TripPlan, itemId: string): PlanItem | null {
  const from = findItem(plan, itemId);
  if (!from) return null;
  const [removed] = plan.days[from.day].items.splice(from.index, 1);
  touch(plan);
  return removed;
}

/** 按开始时间排序当天条目；没有时间的条目保持原先相对顺序排在后面。 */
export function sortDayByTime(plan: TripPlan, dayIndex: number): void {
  const day = plan.days[dayIndex];
  if (!day) return;
  const indexed = day.items.map((item, index) => ({ item, index }));
  indexed.sort((a, b) => {
    if (a.item.time && b.item.time) return a.item.time.localeCompare(b.item.time) || a.index - b.index;
    if (a.item.time) return -1;
    if (b.item.time) return 1;
    return a.index - b.index;
  });
  day.items = indexed.map(({ item }) => item);
  touch(plan);
}

export function dayLoad(day: PlanDay): DayLoad {
  const hours = day.items.reduce((sum, item) => sum + item.hours, 0);
  const stops = day.items.length;
  const cities = new Set(day.items.map((item) => item.cityKey).filter(Boolean));
  if (stops === 0) return { hours: 0, stops, level: "empty", label: "还没有安排" };
  // 跨城当天额外计入通勤；游玩达到 8 小时或超过 6 个点（还没算吃饭和路上）视为偏满。
  const effective = hours + Math.max(0, cities.size - 1) * 2;
  if (effective >= 8 || stops > 6) return { hours, stops, level: "full", label: "偏满，考虑减一个点或拆到别的天" };
  if (effective <= 4) return { hours, stops, level: "light", label: "轻松，适合留白、休息或加一个顺路点" };
  return { hours, stops, level: "balanced", label: "节奏适中" };
}

export function estimateBudget(plan: TripPlan): PlanBudget {
  const { budget, travelers } = plan;
  const nights = Math.max(0, plan.days.length - 1);
  let itemsWithoutCost = 0;
  const days = plan.days.map((day, index) => {
    const tickets = day.items.reduce((sum, item) => {
      if (item.kind !== "custom" && item.cost === 0) itemsWithoutCost += 1;
      return sum + item.cost * travelers;
    }, 0);
    const hotel = index < nights ? budget.hotelPerNight : 0;
    const meals = budget.mealsPerPerson * travelers;
    const transport = budget.localTransportPerDay;
    return { hotel, meals, transport, tickets, total: hotel + meals + transport + tickets };
  });
  const total = days.reduce((sum, day) => sum + day.total, 0) + budget.intercity + budget.other;
  return {
    days,
    nights,
    intercity: budget.intercity,
    other: budget.other,
    total,
    perPerson: travelers ? Math.round(total / travelers) : total,
    itemsWithoutCost,
  };
}

export function dayDate(plan: TripPlan, dayIndex: number): string {
  if (!plan.startDate) return "";
  const date = new Date(`${plan.startDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + dayIndex);
  return date.toISOString().slice(0, 10);
}

/** 今天是行程的第几天（从 0 开始）；不在行程期间返回 -1。 */
export function todayIndex(plan: TripPlan, today: string): number {
  if (!plan.startDate || !validDate(today)) return -1;
  const start = Date.parse(`${plan.startDate}T00:00:00Z`);
  const now = Date.parse(`${today}T00:00:00Z`);
  const offset = Math.round((now - start) / 86400000);
  return offset >= 0 && offset < plan.days.length ? offset : -1;
}

export function localDateString(date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function mapSearchUrl(item: Pick<PlanItem, "name" | "city">): string {
  const keyword = item.city && !item.name.includes(item.city) ? `${item.city} ${item.name}` : item.name;
  const params = new URLSearchParams({ keyword, src: "travel_ayuan", coordinate: "gaode", callnative: "1" });
  if (item.city) params.set("city", item.city);
  return `https://uri.amap.com/search?${params.toString()}`;
}

function toBase64Url(input: string): string {
  const bytes = new TextEncoder().encode(input);
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(input: string): string {
  const padded = input.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(input.length / 4) * 4, "=");
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

/**
 * 生成分享载荷。默认不包含任何备注（个人笔记），只含标题、日期、人数、
 * 预算假设和每天的地点/时间/时长/费用。
 */
export function encodeShare(plan: TripPlan, options: { includeNotes?: boolean } = {}): string {
  const includeNotes = options.includeNotes === true;
  const payload = {
    v: PLAN_SCHEMA,
    t: plan.title,
    s: plan.startDate,
    n: plan.travelers,
    b: plan.budget,
    d: plan.days.map((day) => ({
      ...(includeNotes && day.note ? { o: day.note } : {}),
      i: day.items.map((item) => ({
        n: item.name, k: item.kind, c: item.city, y: item.cityKey, h: item.href,
        t: item.time, r: item.hours, m: item.cost, ...(item.booking ? { b: 1 } : {}),
        ...(includeNotes && item.note ? { o: item.note } : {}),
      })),
    })),
  };
  return toBase64Url(JSON.stringify(payload));
}

export function decodeShare(encoded: string): TripPlan | null {
  try {
    const raw = JSON.parse(fromBase64Url(encoded)) as Record<string, unknown>;
    if (!raw || typeof raw !== "object" || !Array.isArray(raw.d)) return null;
    const days = (raw.d as unknown[]).map((day) => {
      const value = (day && typeof day === "object" ? day : {}) as Record<string, unknown>;
      const items = Array.isArray(value.i) ? value.i : [];
      return {
        note: value.o,
        items: items.map((item) => {
          const v = (item && typeof item === "object" ? item : {}) as Record<string, unknown>;
          return { name: v.n, kind: v.k, city: v.c, cityKey: v.y, href: v.h, time: v.t, hours: v.r, cost: v.m, booking: v.b === 1, note: v.o };
        }),
      };
    });
    return normalizePlan({ title: raw.t, startDate: raw.s, travelers: raw.n, budget: raw.b, days });
  } catch {
    return null;
  }
}

function yuan(value: number): string {
  return `¥${Math.round(value).toLocaleString("zh-CN")}`;
}

export function planToMarkdown(plan: TripPlan, siteUrl = ""): string {
  const budget = estimateBudget(plan);
  const lines = [`# ${plan.title}`, ""];
  lines.push(`- 人数：${plan.travelers} 人`);
  lines.push(`- 日期：${plan.startDate ? `${plan.startDate} 起，共 ${plan.days.length} 天` : `共 ${plan.days.length} 天（未设出发日期）`}`);
  lines.push(`- 参考预算：全程约 ${yuan(budget.total)}，人均约 ${yuan(budget.perPerson)}（按自填假设估算，不是实时报价）`);
  lines.push("");
  plan.days.forEach((day, index) => {
    const date = dayDate(plan, index);
    const load = dayLoad(day);
    lines.push(`## 第 ${index + 1} 天${date ? `（${date}）` : ""}`, "");
    lines.push(`> ${load.stops} 个安排 · 约 ${load.hours} 小时 · ${load.label} · 当天参考花费 ${yuan(budget.days[index].total)}`, "");
    if (day.note) lines.push(day.note, "");
    if (!day.items.length) lines.push("- 暂无安排");
    day.items.forEach((item) => {
      const link = item.href && siteUrl ? `（[攻略](${siteUrl.replace(/\/?$/, "/")}${item.href})）` : "";
      const extras = [
        item.hours ? `约 ${item.hours} 小时` : "",
        item.cost ? `每人约 ${yuan(item.cost)}` : item.kind === "custom" ? "" : "费用待核验",
        item.booking ? "需预约" : "",
      ].filter(Boolean).join(" · ");
      lines.push(`- ${item.time ? `${item.time} ` : ""}${item.name}${item.city ? ` · ${item.city}` : ""}${link}：${extras}${item.note ? `。${item.note}` : ""}`);
    });
    lines.push("");
  });
  lines.push("## 预算假设", "");
  lines.push(`- 住宿：每晚 ${yuan(plan.budget.hotelPerNight)} × ${budget.nights} 晚`);
  lines.push(`- 餐饮：每人每天 ${yuan(plan.budget.mealsPerPerson)}`);
  lines.push(`- 市内交通：每天 ${yuan(plan.budget.localTransportPerDay)}`);
  lines.push(`- 往返大交通：${yuan(plan.budget.intercity)}；其他：${yuan(plan.budget.other)}`);
  if (budget.itemsWithoutCost) lines.push(`- 还有 ${budget.itemsWithoutCost} 个地点没有填写门票/消费，实际花费可能更高`);
  lines.push("", "> 门票、开放时间和预约规则请在出发前按官方渠道复核。");
  return lines.join("\n") + "\n";
}
