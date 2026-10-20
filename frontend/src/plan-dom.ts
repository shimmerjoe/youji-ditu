/** 行程计划界面共用的 DOM 与格式化小工具（不拼接 HTML 字符串）。 */
export type Child = Node | string | null | undefined | false;
export type Attrs = Record<string, string | number | boolean | undefined | null>;

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Attrs = {}, ...children: Child[]): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") element.className = String(value);
    else if (key === "text") element.textContent = String(value);
    else if (value === true) element.setAttribute(key, "");
    else element.setAttribute(key, String(value));
  }
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    element.append(child);
  }
  return element;
}

export const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];

export function yuan(value: number): string {
  return `¥${Math.round(value).toLocaleString("zh-CN")}`;
}

export function siteRoot(): string {
  return (document.body.dataset.siteRoot || ".").replace(/\/$/, "");
}

export function siteHref(path: string): string {
  return `${siteRoot()}/${path.replace(/^\//, "")}`;
}

export function formatDate(value: string): string {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  return `${date.getMonth() + 1}月${date.getDate()}日 周${WEEKDAYS[date.getDay()]}`;
}

export function cityPlanTitle(city: string): string {
  return city ? `${city}行程` : "我的行程";
}

