/** 攻略页上的“加入行程”弹窗：把景点或美食放进某份行程的某一天。 */
import { addDay, addItem, createPlan, dayDate, type PlanItem, type TripPlan } from "./trip-plan.ts";
import { loadActivePlanId, loadPlans, onPlansChanged, saveActivePlanId, savePlans } from "./plan-store.ts";
import { cityPlanTitle, formatDate, h, siteHref } from "./plan-dom.ts";

/* ------------------------------------------------------------------ */

interface PendingItem {
  name: string;
  city: string;
  cityKey: string;
  href: string;
  kind: PlanItem["kind"];
}

function itemFromButton(button: HTMLElement): PendingItem {
  const kind = button.dataset.kind === "food" ? "food" : "place";
  return {
    name: button.dataset.name || "",
    city: button.dataset.city || "",
    cityKey: button.dataset.cityKey || "",
    href: button.dataset.href || "",
    kind,
  };
}

function isPlanned(plans: TripPlan[], activeId: string, item: PendingItem): number {
  const plan = plans.find((candidate) => candidate.id === activeId);
  if (!plan) return -1;
  return plan.days.findIndex((day) => day.items.some((entry) => entry.name === item.name && entry.cityKey === item.cityKey));
}

function syncPlanButtons(): void {
  const { plans } = loadPlans();
  const activeId = loadActivePlanId();
  document.querySelectorAll<HTMLButtonElement>("[data-plan-add]").forEach((button) => {
    const day = isPlanned(plans, activeId, itemFromButton(button));
    button.classList.toggle("added", day >= 0);
    button.textContent = day >= 0 ? `✓ 已在第 ${day + 1} 天` : "＋ 加入行程";
    button.setAttribute("aria-label", `${day >= 0 ? "调整" : "加入行程"}：${button.dataset.name || ""}`);
  });
}

export function bootstrapPlanPicker(): void {
  const buttons = document.querySelectorAll<HTMLButtonElement>("[data-plan-add]");
  if (!buttons.length) return;
  let pending: PendingItem | null = null;
  let source: HTMLButtonElement | null = null;

  const dialog = h("dialog", { class: "plan-picker", "aria-labelledby": "planPickerTitle" });
  const title = h("h2", { id: "planPickerTitle", text: "加入行程" });
  const close = h("button", { type: "button", class: "plan-picker-close", "aria-label": "关闭" }, "×");
  const itemLine = h("p", { class: "plan-picker-item" });
  const select = h("select", { id: "planPickerSelect" });
  const days = h("div", { class: "plan-picker-days", role: "group", "aria-label": "选择第几天" });
  const status = h("p", { class: "plan-picker-status", role: "status", "aria-live": "polite" });
  const open = h("a", { class: "btn btn-primary", href: siteHref("plan.html") }, "打开行程计划");
  dialog.append(
    h("div", { class: "plan-picker-head" }, title, close),
    itemLine,
    h("label", { class: "plan-picker-field", for: "planPickerSelect" }, h("span", { text: "放进哪份行程" }), select),
    h("p", { class: "plan-picker-label", text: "放到第几天" }),
    days,
    status,
    h("div", { class: "plan-picker-foot" }, h("span", { class: "plan-picker-hint", text: "停留时长先按 2 小时（美食 1 小时）计，可在行程计划里调整。" }), open),
  );
  document.body.append(dialog);

  const renderDays = (): void => {
    if (!pending) return;
    const { plans } = loadPlans();
    const plan = plans.find((candidate) => candidate.id === select.value);
    days.replaceChildren();
    const dayCount = plan ? plan.days.length : 2;
    for (let index = 0; index < dayCount; index += 1) {
      const count = plan ? plan.days[index].items.length : 0;
      const date = plan ? dayDate(plan, index) : "";
      days.append(h("button", { type: "button", class: "plan-day-choice", "data-day": index },
        h("strong", { text: `第 ${index + 1} 天` }),
        h("small", { text: [date ? formatDate(date) : "", count ? `${count} 个安排` : "空"].filter(Boolean).join(" · ") }),
      ));
    }
    if (!plan || plan.days.length < 30) {
      days.append(h("button", { type: "button", class: "plan-day-choice add", "data-day": "new" }, h("strong", { text: "＋ 新的一天" })));
    }
  };

  const renderSelect = (): void => {
    if (!pending) return;
    const { plans } = loadPlans();
    const activeId = loadActivePlanId();
    select.replaceChildren();
    plans.forEach((plan) => select.append(h("option", { value: plan.id, text: `${plan.title}（${plan.days.length} 天）` })));
    select.append(h("option", { value: "__new", text: `＋ 新建「${cityPlanTitle(pending.city)}」` }));
    const preferred = plans.find((plan) => plan.id === activeId)
      || plans.find((plan) => plan.days.some((day) => day.items.some((item) => item.cityKey === pending?.cityKey)));
    select.value = preferred ? preferred.id : "__new";
  };

  const openPicker = (button: HTMLButtonElement): void => {
    pending = itemFromButton(button);
    source = button;
    itemLine.replaceChildren(h("strong", { text: pending.name }), h("span", { text: [pending.city, pending.kind === "food" ? "美食" : "景点/地点"].filter(Boolean).join(" · ") }));
    status.textContent = "";
    renderSelect();
    renderDays();
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    const first = days.querySelector<HTMLButtonElement>("button");
    first?.focus();
  };

  const closePicker = (): void => {
    if (dialog.open) dialog.close();
    source?.focus();
  };

  select.addEventListener("change", renderDays);
  close.addEventListener("click", closePicker);
  dialog.addEventListener("click", (event) => { if (event.target === dialog) closePicker(); });
  dialog.addEventListener("close", () => { syncPlanButtons(); });
  days.addEventListener("click", (event) => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>("button[data-day]");
    if (!button || !pending) return;
    const { plans } = loadPlans();
    let plan = plans.find((candidate) => candidate.id === select.value);
    if (!plan) {
      plan = createPlan(cityPlanTitle(pending.city), 2);
      plans.unshift(plan);
    }
    let dayIndex = button.dataset.day === "new" ? plan.days.length : Number(button.dataset.day);
    if (dayIndex >= plan.days.length && !addDay(plan)) {
      status.textContent = "最多 30 天，请先整理现有天数。";
      return;
    }
    dayIndex = Math.min(dayIndex, plan.days.length - 1);
    const added = addItem(plan, dayIndex, { ...pending, hours: pending.kind === "food" ? 1 : 2 });
    if (!added) {
      status.textContent = "这一天已经排满 20 个安排，换一天试试。";
      return;
    }
    if (!savePlans(plans)) {
      status.textContent = "保存失败：浏览器存储不可用或空间不足。可在行程计划页导出备份。";
      return;
    }
    saveActivePlanId(plan.id);
    status.textContent = `已加入「${plan.title}」第 ${dayIndex + 1} 天。`;
    renderSelect();
    select.value = plan.id;
    renderDays();
    syncPlanButtons();
  });

  buttons.forEach((button) => button.addEventListener("click", () => openPicker(button)));
  window.addEventListener("tay:storage-change", syncPlanButtons);
  onPlansChanged(syncPlanButtons);
  syncPlanButtons();
}

