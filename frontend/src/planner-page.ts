/** plan.html：按天编排、预算、保存分享、导入导出与“今天”视图。 */
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
  localDateString,
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
  type PlanItem,
  type TripPlan,
} from "./trip-plan.ts";
import { loadActivePlanId, loadPlans, onPlansChanged, PLANS_BACKUP_KEY, saveActivePlanId, savePlans } from "./plan-store.ts";
import { cityPlanTitle, formatDate, h, siteHref, siteRoot, yuan, type Attrs, type Child } from "./plan-dom.ts";

/* ------------------------------------------------------------------ */

type View = "days" | "today";

function download(filename: string, content: string, type: string): void {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = h("a", { href: url, download: filename });
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function readShortlist(): { key: string; name: string; href: string; sub: string }[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem("tay_trip") || "[]");
    if (!Array.isArray(value)) return [];
    return value
      .filter((item): item is Record<string, string> => Boolean(item) && typeof item === "object" && typeof (item as Record<string, unknown>).key === "string")
      .map((item) => ({ key: item.key, name: String(item.name || ""), href: String(item.href || ""), sub: String(item.sub || "") }));
  } catch {
    return [];
  }
}

export function bootstrapPlannerPage(): void {
  const found = document.getElementById("planApp");
  if (!found) return;
  const root: HTMLElement = found;

  const loaded = loadPlans();
  let plans = loaded.plans;
  let activeId = loadActivePlanId();
  const params = new URLSearchParams(location.search);
  if (params.get("plan") && plans.some((plan) => plan.id === params.get("plan"))) activeId = params.get("plan") as string;
  let view: View = params.get("view") === "today" ? "today" : "days";
  let notice = loaded.unreadable
    ? `本机保存的行程数据无法读取（可能被浏览器扩展或手动修改过）。原始内容已另存为 ${PLANS_BACKUP_KEY}，可以用之前导出的 JSON 备份恢复。`
    : loaded.repaired ? `检测到部分行程数据损坏，已保留可读取的行程；原始数据另存为 ${PLANS_BACKUP_KEY}。` : "";
  let status = "";
  let undoSnapshot: string | null = null;
  let undoLabel = "";
  let includeNotesInShare = false;
  let shareUrl = "";
  let sharedPreview: TripPlan | null = null;
  let offlineNote = "";
  const cachedGuides = new Set<string>();

  /** 旅途中常常没信号：把行程里涉及的城市攻略预先取一遍，交给 Service Worker 缓存。 */
  const cacheGuidesFor = (plan: TripPlan): void => {
    const worker = navigator.serviceWorker;
    if (!worker || !worker.controller || !navigator.onLine) return;
    const pages = new Set<string>();
    plan.days.forEach((day) => day.items.forEach((item) => {
      if (!item.href) return;
      const url = new URL(siteHref(item.href), location.href);
      url.hash = "";
      if (url.origin === location.origin) pages.add(url.href);
    }));
    const pending = [...pages].filter((page) => !cachedGuides.has(page));
    if (!pending.length) return;
    pending.forEach((page) => cachedGuides.add(page));
    Promise.allSettled(pending.map((page) => fetch(page, { credentials: "same-origin" }).then((response) => {
      if (!response.ok) throw new Error(String(response.status));
    }))).then((results) => {
      const failed = results.filter((result) => result.status === "rejected").length;
      offlineNote = failed
        ? `有 ${failed} 篇城市攻略没能存到本机，联网后再打开本页会重试。`
        : `行程涉及的 ${pages.size} 篇城市攻略已存到本机，没有网络时也能打开（图片可能不显示）。`;
      results.forEach((result, index) => { if (result.status === "rejected") cachedGuides.delete(pending[index]); });
      const note = root.querySelector(".plan-offline-note");
      if (note) note.textContent = offlineNote;
      else render();
    });
  };

  const shareMatch = location.hash.match(/share=([A-Za-z0-9_-]+)/);
  if (shareMatch) sharedPreview = decodeShare(shareMatch[1]);
  if (shareMatch && !sharedPreview) notice = "分享链接无法解析，可能被截断或修改过。";

  const active = (): TripPlan | undefined => plans.find((plan) => plan.id === activeId) || plans[0];

  const writeUrl = (): void => {
    const next = new URLSearchParams(location.search);
    const plan = active();
    if (plan) next.set("plan", plan.id); else next.delete("plan");
    if (view === "today") next.set("view", "today"); else next.delete("view");
    const query = next.toString();
    const hash = sharedPreview ? location.hash : "";
    history.replaceState(null, "", location.pathname + (query ? `?${query}` : "") + hash);
  };

  const persist = (message = "已自动保存在本机"): void => {
    const ok = savePlans(plans);
    const plan = active();
    if (plan) saveActivePlanId(plan.id);
    const time = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    status = ok ? `${message} · ${time}` : "保存失败：浏览器存储不可用或空间不足，请先导出 JSON 备份。";
    shareUrl = "";
  };

  const remember = (label: string): void => {
    undoSnapshot = JSON.stringify(plans);
    undoLabel = label;
  };

  const focusKey = (): { key: string; start: number | null } | null => {
    const element = document.activeElement as HTMLInputElement | null;
    if (!element || !root.contains(element) || !element.dataset.fk) return null;
    let start: number | null = null;
    try { start = element.selectionStart; } catch { start = null; }
    return { key: element.dataset.fk, start };
  };

  const restoreFocus = (saved: { key: string; start: number | null } | null): void => {
    if (!saved) return;
    const element = root.querySelector<HTMLInputElement>(`[data-fk="${CSS.escape(saved.key)}"]`);
    if (!element) return;
    element.focus();
    if (saved.start !== null) {
      try { element.setSelectionRange(saved.start, saved.start); } catch { /* 非文本输入框 */ }
    }
  };

  /* ---------- 渲染 ---------- */

  const field = (label: string, control: HTMLElement, extra = ""): HTMLLabelElement =>
    h("label", { class: `plan-field ${extra}`.trim() }, h("span", { text: label }), control);

  const numberInput = (fk: string, value: number, attrs: Attrs): HTMLInputElement =>
    h("input", { type: "number", inputmode: "numeric", value, "data-fk": fk, ...attrs });

  function renderEmpty(): HTMLElement {
    const shortlist = readShortlist();
    return h("section", { class: "plan-empty" },
      h("h2", { text: "还没有行程" }),
      h("p", { text: "在任意城市攻略的景点或美食卡片上点“＋ 加入行程”，就会放进这里按天排好；也可以先新建一份空行程。" }),
      h("div", { class: "plan-empty-actions" },
        h("button", { type: "button", class: "btn btn-primary", "data-action": "new-plan" }, "新建行程"),
        h("a", { class: "btn btn-ghost", href: siteHref("destinations.html") }, "先去选城市"),
        // 换手机或误删后，最需要从导出的 JSON 恢复的正是这个空状态。
        h("label", { class: "btn btn-ghost file-btn" }, "导入 JSON 备份", h("input", { type: "file", accept: "application/json,.json", hidden: true, "data-action": "import-json" })),
      ),
      status ? h("p", { class: "plan-status", role: "status", "aria-live": "polite", text: status }) : null,
      shortlist.length ? renderShortlist(shortlist) : null,
    );
  }

  function renderShortlist(shortlist = readShortlist()): HTMLElement | null {
    if (!shortlist.length) return null;
    return h("section", { class: "plan-card plan-shortlist" },
      h("h3", { text: "想去的城市" }),
      h("p", { class: "plan-hint", text: "这些城市来自“加入行程”收藏，可以直接为它建一份按天行程。" }),
      h("ul", {}, ...shortlist.map((city) => h("li", {},
        h("a", { href: siteHref(city.href) }, city.name.replace("旅游攻略", "")),
        h("button", { type: "button", class: "link-btn", "data-action": "new-plan-for", "data-name": city.name.replace("旅游攻略", "") }, "建行程"),
      ))),
    );
  }

  function renderItem(plan: TripPlan, dayIndex: number, item: PlanItem, index: number, compact: boolean): HTMLElement {
    const id = item.id;
    const nameNode = item.href
      ? h("a", { class: "pi-name", href: siteHref(item.href) }, item.name)
      : h("span", { class: "pi-name", text: item.name });
    const tags = h("span", { class: "pi-tags" },
      item.city ? h("span", { class: "pi-tag", text: item.city }) : null,
      h("span", { class: `pi-tag kind-${item.kind}`, text: item.kind === "food" ? "美食" : item.kind === "custom" ? "自定义" : "景点" }),
      item.booking ? h("span", { class: "pi-tag booking", text: "需预约" }) : null,
    );
    const navigate = h("a", { class: "pi-nav", href: mapSearchUrl(item), target: "_blank", rel: "noopener noreferrer", "aria-label": `在高德地图查看 ${item.name}` }, "导航 ↗");
    if (compact) {
      return h("li", { class: "plan-item today-item" },
        h("span", { class: "pi-time-label", text: item.time || "—" }),
        h("div", { class: "pi-main" }, nameNode, tags, item.note ? h("p", { class: "pi-note-text", text: item.note }) : null,
          h("small", { class: "pi-meta", text: [`约 ${item.hours} 小时`, item.cost ? `每人约 ${yuan(item.cost)}` : "费用待核验"].join(" · ") })),
        navigate,
      );
    }
    const moveSelect = h("select", { "data-action": "move-day", "data-item": id, "aria-label": `把 ${item.name} 移到另一天` },
      ...plan.days.map((_, target) => h("option", { value: target, selected: target === dayIndex, text: `第 ${target + 1} 天` })));
    const hours = h("select", { "data-field": "hours", "data-item": id, "data-fk": `${id}-hours`, "aria-label": `${item.name} 停留时长` },
      ...[0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12].map((value) => h("option", { value, selected: value === item.hours, text: `${value} 小时` })));
    return h("li", { class: "plan-item", "data-item-id": id },
      h("input", { type: "time", class: "pi-time", value: item.time, "data-field": "time", "data-item": id, "data-fk": `${id}-time`, "aria-label": `${item.name} 开始时间` }),
      h("div", { class: "pi-main" },
        h("div", { class: "pi-title" }, nameNode, tags),
        h("div", { class: "pi-fields" },
          hours,
          h("label", { class: "pi-cost" }, h("span", { text: "每人 ¥" }),
            numberInput(`${id}-cost`, item.cost, { min: 0, max: 100000, step: 1, "data-field": "cost", "data-item": id, "aria-label": `${item.name} 每人费用` })),
          h("label", { class: "pi-booking" },
            h("input", { type: "checkbox", checked: item.booking, "data-field": "booking", "data-item": id }), h("span", { text: "需预约" })),
        ),
        h("input", { type: "text", class: "pi-note", value: item.note, maxlength: 400, placeholder: "备注：预约时段、排队、换乘…", "data-field": "note", "data-item": id, "data-fk": `${id}-note`, "aria-label": `${item.name} 备注` }),
      ),
      h("div", { class: "pi-actions" },
        h("button", { type: "button", "data-action": "up", "data-item": id, disabled: index === 0, "aria-label": `上移 ${item.name}` }, "↑"),
        h("button", { type: "button", "data-action": "down", "data-item": id, disabled: index === plan.days[dayIndex].items.length - 1, "aria-label": `下移 ${item.name}` }, "↓"),
        moveSelect,
        navigate,
        h("button", { type: "button", class: "danger", "data-action": "remove-item", "data-item": id, "aria-label": `删除 ${item.name}` }, "删除"),
      ),
    );
  }

  function renderDay(plan: TripPlan, dayIndex: number, highlight: boolean, compact = false): HTMLElement {
    const day = plan.days[dayIndex];
    const load = dayLoad(day);
    const budget = estimateBudget(plan).days[dayIndex];
    const date = dayDate(plan, dayIndex);
    const head = h("header", { class: "plan-day-head" },
      h("div", {},
        h("h3", {}, `第 ${dayIndex + 1} 天`, date ? h("small", { text: formatDate(date) }) : null, highlight ? h("span", { class: "today-badge", text: "今天" }) : null),
        h("p", { class: `plan-load load-${load.level}`, text: load.stops ? `${load.stops} 个安排 · 约 ${load.hours} 小时 · ${load.label}` : load.label }),
      ),
      compact ? null : h("div", { class: "plan-day-actions" },
        h("button", { type: "button", "data-action": "sort-day", "data-day": dayIndex, disabled: day.items.length < 2 }, "按时间排序"),
        h("button", { type: "button", class: "danger", "data-action": "remove-day", "data-day": dayIndex, disabled: plan.days.length <= 1 }, "删除这天"),
      ),
    );
    const items = day.items.length
      ? h("ol", { class: "plan-items" }, ...day.items.map((item, index) => renderItem(plan, dayIndex, item, index, compact)))
      : h("p", { class: "plan-day-empty", text: "这天还空着：在城市攻略里点“＋ 加入行程”，或在下面直接添加。" });
    const note = compact
      ? (day.note ? h("p", { class: "plan-day-note-text", text: day.note }) : null)
      : h("textarea", { class: "plan-day-note", rows: 2, maxlength: 400, placeholder: "当天备注：住在哪个片区、怎么换乘、行李寄存…", "data-field": "day-note", "data-day": dayIndex, "data-fk": `${day.id}-note`, "aria-label": `第 ${dayIndex + 1} 天备注` });
    if (note instanceof HTMLTextAreaElement) note.value = day.note;
    const addForm = compact ? null : h("form", { class: "plan-add-custom", "data-day": dayIndex },
      h("label", { class: "sr-only", for: `add-${day.id}`, text: `给第 ${dayIndex + 1} 天添加安排` }),
      h("input", { id: `add-${day.id}`, type: "text", maxlength: 60, placeholder: "添加安排，例如：酒店寄存行李、高铁 G123", "data-fk": `${day.id}-add` }),
      h("button", { type: "submit", class: "btn btn-ghost" }, "添加"),
    );
    return h("article", { class: `plan-day${highlight ? " is-today" : ""}`, id: `plan-day-${dayIndex + 1}` },
      head, note, items, addForm,
      h("footer", { class: "plan-day-foot", text: `当天参考花费 ${yuan(budget.total)}（住宿 ${yuan(budget.hotel)} · 餐饮 ${yuan(budget.meals)} · 市内交通 ${yuan(budget.transport)} · 门票/消费 ${yuan(budget.tickets)}）` }),
    );
  }

  function renderBudget(plan: TripPlan): HTMLElement {
    const budget = estimateBudget(plan);
    const assumption = (label: string, key: keyof TripPlan["budget"], hint: string): HTMLElement => {
      const wrapper = field(label, numberInput(`budget-${key}`, plan.budget[key], { min: 0, step: 10, "data-field": `budget.${key}`, "aria-describedby": `hint-${key}` }), "compact");
      wrapper.append(h("small", { id: `hint-${key}`, text: hint }));
      return wrapper;
    };
    return h("section", { class: "plan-card plan-budget", "aria-labelledby": "planBudgetTitle" },
      h("h3", { id: "planBudgetTitle", text: "参考预算" }),
      h("p", { class: "plan-total" }, h("strong", { text: yuan(budget.total) }), h("span", { text: `全程 · 人均 ${yuan(budget.perPerson)}` })),
      h("p", { class: "plan-hint", text: `按下方假设计算，不是实时报价。${budget.nights} 晚住宿；门票按每个安排填写的“每人费用” × ${plan.travelers} 人。${budget.itemsWithoutCost ? `还有 ${budget.itemsWithoutCost} 个地点没填费用，实际可能更高。` : ""}` }),
      h("div", { class: "plan-assumptions" },
        assumption("每晚住宿", "hotelPerNight", "整间/整组的价格"),
        assumption("每人每天餐饮", "mealsPerPerson", "早中晚加小吃"),
        assumption("每天市内交通", "localTransportPerDay", "全体合计"),
        assumption("往返大交通", "intercity", "高铁/机票全体合计"),
        assumption("其他", "other", "门票套票、购物等"),
      ),
      h("table", { class: "plan-budget-table" },
        h("thead", {}, h("tr", {}, h("th", { scope: "col", text: "天" }), h("th", { scope: "col", text: "住宿" }), h("th", { scope: "col", text: "餐饮" }), h("th", { scope: "col", text: "交通" }), h("th", { scope: "col", text: "门票" }), h("th", { scope: "col", text: "合计" }))),
        h("tbody", {}, ...budget.days.map((day, index) => h("tr", {},
          h("th", { scope: "row", text: `第${index + 1}天` }),
          h("td", { text: yuan(day.hotel) }), h("td", { text: yuan(day.meals) }), h("td", { text: yuan(day.transport) }), h("td", { text: yuan(day.tickets) }), h("td", { text: yuan(day.total) }),
        ))),
      ),
    );
  }

  function renderShare(plan: TripPlan): HTMLElement {
    return h("section", { class: "plan-card plan-share", "aria-labelledby": "planShareTitle" },
      h("h3", { id: "planShareTitle", text: "保存、分享与导出" }),
      h("p", { class: "plan-hint", text: "行程自动保存在这台设备的浏览器里，清除浏览器数据会丢失；换设备前请导出 JSON。" }),
      offlineNote ? h("p", { class: "plan-hint plan-offline-note", text: offlineNote }) : null,
      h("div", { class: "plan-share-actions" },
        h("button", { type: "button", class: "btn btn-ghost", "data-action": "export-md" }, "导出 Markdown"),
        h("button", { type: "button", class: "btn btn-ghost", "data-action": "export-json" }, "导出 JSON"),
        h("label", { class: "btn btn-ghost file-btn" }, "导入 JSON", h("input", { type: "file", accept: "application/json,.json", hidden: true, "data-action": "import-json" })),
        h("button", { type: "button", class: "btn btn-ghost", "data-action": "print" }, "打印 / PDF"),
      ),
      h("label", { class: "plan-check" },
        h("input", { type: "checkbox", checked: includeNotesInShare, "data-action": "toggle-share-notes" }),
        h("span", { text: "分享链接里包含备注（默认不含）" })),
      h("p", { class: "plan-hint", text: "分享链接只包含标题、日期、人数、预算假设和每天的地点、时间、时长、费用；数据写在链接里，不经过任何服务器。" }),
      h("button", { type: "button", class: "btn btn-primary", "data-action": "share" }, "生成分享链接"),
      shareUrl ? h("div", { class: "plan-share-url" },
        h("input", { type: "text", readonly: true, value: shareUrl, "aria-label": "分享链接", "data-fk": "share-url" }),
        h("button", { type: "button", class: "btn btn-ghost", "data-action": "copy-share" }, "复制")) : null,
    );
  }

  function renderChecks(plan: TripPlan): HTMLElement | null {
    const bookings = plan.days.flatMap((day, index) => day.items.filter((item) => item.booking).map((item) => ({ item, index })));
    const noCost = plan.days.flatMap((day) => day.items).filter((item) => item.kind !== "custom" && !item.cost).length;
    const loads = plan.days.map((day, index) => ({ load: dayLoad(day), index })).filter(({ load }) => load.level === "full");
    // 单个整天项目（乐园、徒步）没有“删掉一个点”的余地，单独提醒。
    const allDay = loads.filter(({ load }) => load.stops === 1);
    const full = loads.filter(({ load }) => load.stops > 1);
    return h("section", { class: "plan-card plan-checks", "aria-labelledby": "planChecksTitle" },
      h("h3", { id: "planChecksTitle", text: "出发前核验" }),
      h("ul", {},
        bookings.length
          ? h("li", {}, `需要预约：${bookings.map(({ item, index }) => `第${index + 1}天 ${item.name}`).join("、")}。在官方渠道确认可约日期和时段。`)
          : h("li", { text: "还没有标记“需预约”的地点。博物馆、热门景区、索道和演出通常需要提前预约。" }),
        full.length ? h("li", { text: `第 ${full.map(({ index }) => index + 1).join("、")} 天偏满：考虑删掉一个点或挪到别的天，并留出吃饭和路上的时间。` }) : null,
        allDay.length ? h("li", { text: `第 ${allDay.map(({ index }) => index + 1).join("、")} 天是整天项目：前一晚住近一点，查好入园/开放时间和返程末班车。` }) : null,
        noCost ? h("li", { text: `${noCost} 个地点的费用待核验，预算可能偏低。` }) : null,
        h("li", { text: "准备雨天备选：每天至少留一个室内点（博物馆、商场、老街）。" }),
        h("li", { text: "出发前一天再看一次天气预警、闭馆日和末班车。" }),
      ),
    );
  }

  function renderPreview(plan: TripPlan): HTMLElement {
    const budget = estimateBudget(plan);
    return h("section", { class: "plan-preview", "aria-labelledby": "planPreviewTitle" },
      h("div", { class: "plan-preview-head" },
        h("div", {}, h("p", { class: "eyebrow", text: "Shared plan" }), h("h2", { id: "planPreviewTitle", text: `分享的行程：${plan.title}` }),
          h("p", { class: "plan-hint", text: `${plan.days.length} 天 · ${plan.travelers} 人 · 参考预算 ${yuan(budget.total)}。这是别人分享的副本，保存后才会出现在你的行程里。` })),
        h("div", { class: "plan-preview-actions" },
          h("button", { type: "button", class: "btn btn-primary", "data-action": "save-shared" }, "保存为我的行程"),
          h("button", { type: "button", class: "btn btn-ghost", "data-action": "close-shared" }, "关闭预览")),
      ),
      h("div", { class: "plan-days" }, ...plan.days.map((_, index) => renderDay(plan, index, false, true))),
    );
  }

  function render(): void {
    const saved = focusKey();
    const plan = active();
    if (plan) activeId = plan.id;
    const today = plan ? todayIndex(plan, localDateString()) : -1;
    const nodes: Child[] = [];
    if (notice) nodes.push(h("p", { class: "plan-notice", role: "alert", text: notice }));
    if (sharedPreview) nodes.push(renderPreview(sharedPreview));

    if (!plan) {
      nodes.push(renderEmpty());
      root.replaceChildren(...nodes.filter((node): node is Node => node instanceof Node));
      writeUrl();
      return;
    }

    const planSelect = h("select", { "data-action": "switch-plan", "aria-label": "切换行程" },
      ...plans.map((candidate) => h("option", { value: candidate.id, selected: candidate.id === plan.id, text: `${candidate.title}（${candidate.days.length} 天）` })));
    const bar = h("div", { class: "plan-bar" },
      planSelect,
      h("div", { class: "plan-bar-actions" },
        h("button", { type: "button", "data-action": "new-plan" }, "新建"),
        h("button", { type: "button", "data-action": "copy-plan" }, "复制"),
        h("button", { type: "button", class: "danger", "data-action": "delete-plan" }, "删除"),
      ),
      h("p", { class: "plan-status", role: "status", "aria-live": "polite" },
        status || "修改会自动保存在本机",
        undoSnapshot ? h("button", { type: "button", class: "link-btn", "data-action": "undo" }, `撤销${undoLabel}`) : null),
    );

    const titleInput = h("input", { type: "text", value: plan.title, maxlength: 40, "data-field": "title", "data-fk": "plan-title" });
    const meta = h("section", { class: "plan-meta" },
      field("行程名称", titleInput, "wide"),
      field("出发日期", h("input", { type: "date", value: plan.startDate, "data-field": "startDate", "data-fk": "plan-start" })),
      field("人数", numberInput("plan-travelers", plan.travelers, { min: 1, max: 20, "data-field": "travelers" })),
    );

    const viewToggle = h("div", { class: "plan-view-toggle", role: "tablist", "aria-label": "查看方式" },
      h("button", { type: "button", role: "tab", "aria-selected": view === "days" ? "true" : "false", "data-action": "view-days" }, "按天编排"),
      h("button", { type: "button", role: "tab", "aria-selected": view === "today" ? "true" : "false", "data-action": "view-today" }, today >= 0 ? `今天 · 第 ${today + 1} 天` : "今天"),
    );

    let main: HTMLElement;
    if (view === "today") {
      const index = today >= 0 ? today : -1;
      main = h("div", { class: "plan-days today-view" },
        index >= 0
          ? renderDay(plan, index, true, true)
          : h("div", { class: "plan-card plan-today-empty" },
            h("p", { text: plan.startDate ? `今天（${localDateString()}）不在这份行程的日期内。` : "还没有设置出发日期，所以无法判断“今天”是第几天。" }),
            h("p", { class: "plan-hint", text: "设置出发日期后，旅途中打开这里就能直接看到当天安排、导航和预约提醒。" }),
            h("button", { type: "button", class: "btn btn-ghost", "data-action": "view-days" }, "回到按天编排")),
        index >= 0 && index + 1 < plan.days.length ? h("details", { class: "plan-next-day" }, h("summary", { text: `明天：第 ${index + 2} 天` }), renderDay(plan, index + 1, false, true)) : null,
      );
    } else {
      main = h("div", { class: "plan-days" },
        ...plan.days.map((_, index) => renderDay(plan, index, index === today)),
        h("button", { type: "button", class: "plan-add-day", "data-action": "add-day", disabled: plan.days.length >= 30 }, "＋ 添加一天"),
      );
    }

    nodes.push(
      bar,
      h("div", { class: "plan-layout" },
        h("div", { class: "plan-main" }, meta, viewToggle, main),
        h("aside", { class: "plan-side" }, renderBudget(plan), renderChecks(plan), renderShare(plan), renderShortlist()),
      ),
    );
    root.replaceChildren(...nodes.filter((node): node is Node => node instanceof Node));
    restoreFocus(saved);
    writeUrl();
    cacheGuidesFor(plan);
  }

  /* ---------- 交互 ---------- */

  const newPlan = (title: string): void => {
    remember("新建");
    const plan = createPlan(title, 2);
    plans.unshift(plan);
    activeId = plan.id;
    view = "days";
    persist("已新建行程");
    render();
    root.querySelector<HTMLInputElement>('[data-fk="plan-title"]')?.select();
  };

  root.addEventListener("click", (event) => {
    const target = (event.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!target || target instanceof HTMLSelectElement || (target instanceof HTMLInputElement && target.type !== "button")) return;
    const action = target.dataset.action;
    const plan = active();
    const itemId = target.dataset.item || "";
    switch (action) {
      case "new-plan": newPlan("我的行程"); return;
      case "new-plan-for": newPlan(cityPlanTitle(target.dataset.name || "")); return;
      case "undo":
        if (undoSnapshot) {
          plans = normalizePlans(JSON.parse(undoSnapshot));
          undoSnapshot = null;
          persist("已撤销");
          render();
        }
        return;
      case "save-shared":
        if (sharedPreview) {
          const copy = clonePlan(sharedPreview, sharedPreview.title);
          plans.unshift(copy);
          activeId = copy.id;
          sharedPreview = null;
          history.replaceState(null, "", location.pathname + location.search);
          persist("已保存分享的行程");
          render();
        }
        return;
      case "close-shared":
        sharedPreview = null;
        history.replaceState(null, "", location.pathname + location.search);
        render();
        return;
      case "view-days": view = "days"; render(); return;
      case "view-today": view = "today"; render(); return;
    }
    if (!plan) return;
    switch (action) {
      case "copy-plan": {
        remember("复制");
        const copy = clonePlan(plan);
        plans.unshift(copy);
        activeId = copy.id;
        persist("已复制为新行程");
        break;
      }
      case "delete-plan":
        if (!window.confirm(`删除行程「${plan.title}」？删除后可点“撤销”恢复（刷新页面前有效）。`)) return;
        remember("删除行程");
        plans = plans.filter((candidate) => candidate.id !== plan.id);
        activeId = plans[0]?.id || "";
        persist("已删除行程");
        break;
      case "add-day": remember("添加一天"); addDay(plan); persist(); break;
      case "remove-day": {
        const index = Number(target.dataset.day);
        remember("删除这天");
        removeDay(plan, index);
        persist(`已删除第 ${index + 1} 天，原有安排并入相邻一天`);
        break;
      }
      case "sort-day": sortDayByTime(plan, Number(target.dataset.day)); persist("已按时间排序"); break;
      case "up": shiftItem(plan, itemId, -1); persist(); break;
      case "down": shiftItem(plan, itemId, 1); persist(); break;
      case "remove-item": remember("删除"); removeItem(plan, itemId); persist("已删除安排"); break;
      case "export-md":
        download(`${plan.title}.md`, `\uFEFF${planToMarkdown(plan, new URL(`${siteRoot()}/`, location.href).href)}`, "text/markdown;charset=utf-8");
        status = "已导出 Markdown";
        break;
      case "export-json":
        download(`${plan.title}.json`, JSON.stringify({ schema: 1, exportedAt: new Date().toISOString(), plans: [plan] }, null, 2), "application/json;charset=utf-8");
        status = "已导出 JSON";
        break;
      case "print": window.print(); return;
      case "share":
        shareUrl = `${location.origin}${location.pathname}#share=${encodeShare(plan, { includeNotes: includeNotesInShare })}`;
        status = includeNotesInShare ? "已生成分享链接（含备注）" : "已生成分享链接（不含备注）";
        break;
      case "copy-share": {
        const input = root.querySelector<HTMLInputElement>('[data-fk="share-url"]');
        if (!input) return;
        input.select();
        const done = (): void => { status = "链接已复制"; render(); };
        if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(input.value).then(done, () => { document.execCommand("copy"); done(); });
        else { document.execCommand("copy"); done(); }
        return;
      }
      default: return;
    }
    render();
  });

  root.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
    const plan = active();
    if (target.dataset.action === "switch-plan") {
      activeId = target.value;
      saveActivePlanId(activeId);
      shareUrl = "";
      status = "";
      render();
      return;
    }
    if (target.dataset.action === "toggle-share-notes") {
      includeNotesInShare = (target as HTMLInputElement).checked;
      shareUrl = "";
      render();
      return;
    }
    if (target.dataset.action === "import-json") {
      const file = (target as HTMLInputElement).files?.[0];
      if (!file) return;
      file.text().then((text) => {
        let payload: unknown;
        try { payload = JSON.parse(text); } catch { status = "导入失败：不是有效的 JSON 文件"; render(); return; }
        const list = Array.isArray(payload) ? payload
          : payload && typeof payload === "object" && Array.isArray((payload as Record<string, unknown>).plans) ? (payload as Record<string, unknown>).plans
            : [payload];
        const imported = normalizePlans(list);
        if (!imported.length) { status = "导入失败：文件里没有可识别的行程"; render(); return; }
        remember("导入");
        const ids = new Set(plans.map((candidate) => candidate.id));
        imported.forEach((candidate) => { if (ids.has(candidate.id)) Object.assign(candidate, clonePlan(candidate, candidate.title)); });
        plans = [...imported, ...plans];
        activeId = imported[0].id;
        persist(`已导入 ${imported.length} 份行程`);
        render();
      }).catch(() => { status = "导入失败：无法读取文件"; render(); });
      (target as HTMLInputElement).value = "";
      return;
    }
    if (!plan) return;
    const fieldName = target.dataset.field;
    const itemId = target.dataset.item || "";
    if (target.dataset.action === "move-day") {
      moveItem(plan, itemId, Number(target.value));
      persist(`已移到第 ${Number(target.value) + 1} 天`);
      render();
      return;
    }
    if (!fieldName) return;
    if (itemId) {
      const value = target instanceof HTMLInputElement && target.type === "checkbox" ? target.checked : target.value;
      const patch: Partial<PlanItem> = fieldName === "hours" || fieldName === "cost" ? { [fieldName]: Number(value) } : { [fieldName]: value };
      updateItem(plan, itemId, patch);
    } else if (fieldName === "day-note") {
      const day = plan.days[Number(target.dataset.day)];
      if (day) day.note = target.value.slice(0, 400);
    } else if (fieldName.startsWith("budget.")) {
      const key = fieldName.slice(7) as keyof TripPlan["budget"];
      const repaired = normalizePlan({ ...plan, budget: { ...plan.budget, [key]: Number(target.value) } });
      if (repaired) plan.budget = repaired.budget;
    } else if (fieldName === "title" || fieldName === "startDate" || fieldName === "travelers") {
      const repaired = normalizePlan({ ...plan, [fieldName]: target.value });
      if (repaired) Object.assign(plan, { title: repaired.title, startDate: repaired.startDate, travelers: repaired.travelers });
    }
    plan.updatedAt = new Date().toISOString();
    persist();
    render();
  });

  root.addEventListener("submit", (event) => {
    const form = (event.target as HTMLElement).closest<HTMLFormElement>("form.plan-add-custom");
    if (!form) return;
    event.preventDefault();
    const plan = active();
    const input = form.querySelector("input");
    const name = input?.value.trim() || "";
    if (!plan || !name) { input?.focus(); return; }
    const dayIndex = Number(form.dataset.day);
    const added = addItem(plan, dayIndex, { name, kind: "custom", hours: 1 });
    persist(added ? "已添加安排" : "这一天已经排满 20 个安排");
    render();
    root.querySelector<HTMLInputElement>(`[data-fk="${plan.days[dayIndex].id}-add"]`)?.focus();
  });

  onPlansChanged(() => {
    plans = loadPlans().plans;
    activeId = loadActivePlanId() || activeId;
    status = "已同步其他标签页的修改";
    render();
  });

  render();
}
