/** 首页“继续上次的旅行准备”：当前行程、今天安排、最近浏览与收藏。没有本机数据时保持隐藏。 */
import { dayLoad, localDateString, todayIndex } from "./trip-plan.ts";
import { loadActivePlanId, loadPlans } from "./plan-store.ts";
import { normalizeRecentVisits } from "./site-search.ts";
import { h, siteHref } from "./plan-dom.ts";

function storedArray(key: string): unknown[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function bootstrapHomeContinue(): void {
  const section = document.getElementById("homeContinue");
  const grid = document.getElementById("homeContinueGrid");
  if (!section || !grid) return;
  const cards: HTMLElement[] = [];

  const { plans } = loadPlans();
  const activeId = loadActivePlanId();
  const plan = plans.find((candidate) => candidate.id === activeId) || plans[0];
  if (plan) {
    const stops = plan.days.reduce((sum, day) => sum + day.items.length, 0);
    const today = todayIndex(plan, localDateString());
    const link = siteHref(`plan.html?plan=${encodeURIComponent(plan.id)}`);
    const fullDays = plan.days.filter((day) => dayLoad(day).level === "full").length;
    cards.push(h("article", { class: "continue-card continue-plan" },
      h("p", { class: "continue-kicker", text: today >= 0 ? `旅途中 · 今天是第 ${today + 1} 天` : "行程计划" }),
      h("h3", { text: plan.title }),
      h("p", { text: `${plan.days.length} 天 · ${stops} 个安排${plan.startDate ? ` · ${plan.startDate} 出发` : " · 未设出发日期"}${fullDays ? ` · ${fullDays} 天偏满` : ""}` }),
      h("div", { class: "continue-actions" },
        today >= 0 ? h("a", { class: "btn btn-primary", href: `${link}&view=today` }, "看今天的安排") : null,
        h("a", { class: today >= 0 ? "btn btn-ghost" : "btn btn-primary", href: link }, "继续编排"),
      ),
    ));
  }

  const recent = normalizeRecentVisits(storedArray("tay_recent"), 4);
  if (recent.length) {
    cards.push(h("article", { class: "continue-card continue-recent" },
      h("p", { class: "continue-kicker", text: "最近浏览" }),
      h("ul", { class: "continue-list" }, ...recent.map((visit) => {
        const image = h("img", { src: siteHref(`assets/images/${visit.key}.jpg`), alt: "", width: 64, height: 48, loading: "lazy", decoding: "async" });
        image.addEventListener("error", () => image.remove(), { once: true });
        return h("li", {}, h("a", { href: siteHref(visit.href) }, image, h("span", { text: visit.name.replace("旅游攻略", "") })));
      })),
    ));
  }

  const favorites = storedArray("tay_favs").length;
  if (favorites) {
    cards.push(h("article", { class: "continue-card continue-favs" },
      h("p", { class: "continue-kicker", text: "收藏" }),
      h("h3", { text: `${favorites} 座收藏的城市` }),
      h("p", { text: "在用户中心查看、对比，或挑一座建行程。" }),
      h("div", { class: "continue-actions" }, h("a", { class: "btn btn-ghost", href: siteHref("user.html#tab=favorites") }, "打开收藏")),
    ));
  }

  grid.replaceChildren(...cards);
  section.hidden = cards.length === 0;
}
