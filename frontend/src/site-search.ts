export interface TravelSearchItem {
  key: string;
  title: string;
  subtitle?: string;
  province?: string;
  city?: string;
  path?: string;
  href?: string;
  highlights?: string[];
  foods?: string[];
  keywords?: string;
}

export interface RankedSearchItem {
  item: TravelSearchItem;
  score: number;
}

export type RecentSearchEntry = string;

export interface RecentVisitEntry {
  key: string;
  name: string;
  href: string;
}

const SEARCH_HISTORY_KEY = "tay_search_recent";
const VISIT_HISTORY_KEY = "tay_recent";
const DIRECT_MUNICIPALITIES = new Set(["北京", "上海", "天津", "重庆"]);
const SPECIAL_REGIONS = new Set(["香港", "澳门"]);

declare global {
  interface Window {
    TRAVEL_SEARCH_INDEX?: TravelSearchItem[];
  }
}

function normalize(value: string | undefined): string {
  return (value ?? "").toLocaleLowerCase("zh-CN").trim();
}

function storedArray(key: string): unknown[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function normalizeRecentSearches(value: unknown, limit = 6): RecentSearchEntry[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const entries: RecentSearchEntry[] = [];
  for (const candidate of value) {
    const query = typeof candidate === "string"
      ? candidate.trim()
      : candidate && typeof candidate === "object" && typeof (candidate as Record<string, unknown>).query === "string"
        ? ((candidate as Record<string, unknown>).query as string).trim()
        : "";
    const identity = normalize(query);
    if (!identity || seen.has(identity)) continue;
    seen.add(identity);
    entries.push(query);
    if (entries.length >= limit) break;
  }
  return entries;
}

export function rememberSearchQuery(
  value: unknown,
  query: string,
  limit = 6,
): RecentSearchEntry[] {
  const cleaned = query.trim();
  const existing = normalizeRecentSearches(value, limit);
  if (!cleaned) return existing;
  const identity = normalize(cleaned);
  return [
    cleaned,
    ...existing.filter((entry) => normalize(entry) !== identity),
  ].slice(0, limit);
}

export function normalizeRecentVisits(value: unknown, limit = 4): RecentVisitEntry[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const entries: RecentVisitEntry[] = [];
  for (const candidate of value) {
    if (!candidate || typeof candidate !== "object") continue;
    const raw = candidate as Record<string, unknown>;
    if (typeof raw.key !== "string" || typeof raw.name !== "string" || typeof raw.href !== "string") continue;
    const key = raw.key.trim();
    const name = raw.name.trim();
    const href = raw.href.trim();
    if (!key || !name || !href || seen.has(key)) continue;
    seen.add(key);
    const entry: RecentVisitEntry = { key, name, href };
    entries.push(entry);
    if (entries.length >= limit) break;
  }
  return entries;
}

export function destinationItemsForGroup(
  items: readonly TravelSearchItem[],
  group: string,
): TravelSearchItem[] {
  return items
    .filter((item) => {
      const province = item.province || "";
      if (!item.key || !item.city || !(item.path || item.href)) return false;
      if (group === "直辖市") return province === group || DIRECT_MUNICIPALITIES.has(province);
      if (group === "港澳") return SPECIAL_REGIONS.has(province);
      return province === group;
    })
    .sort((left, right) => (left.city || left.title).localeCompare(right.city || right.title, "zh-CN"));
}

function searchScore(item: TravelSearchItem, query: string): number {
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return 0;

  const title = normalize(item.title);
  const city = normalize(item.city);
  const province = normalize(item.province);
  const key = normalize(item.key);
  const searchable = normalize([
    item.key,
    item.title,
    item.subtitle,
    item.province,
    item.city,
    ...(item.highlights ?? []),
    ...(item.foods ?? []),
    item.path,
    item.keywords,
  ].filter(Boolean).join(" "));

  let score = 0;
  for (const token of tokens) {
    if (!searchable.includes(token)) return 0;
    if (title.includes(token)) score += 10;
    if (city.includes(token)) score += 8;
    if (key === token) score += 8;
    if (province.includes(token)) score += 4;
    score += 1;
  }
  return score;
}

export function rankSearchItems(
  items: readonly TravelSearchItem[],
  query: string,
  limit = 10,
): RankedSearchItem[] {
  return items
    .map((item, index) => ({ item, index, score: searchScore(item, query) }))
    .filter(({ score }) => score > 0)
    .sort((left, right) => right.score - left.score || left.index - right.index)
    .slice(0, limit)
    .map(({ item, score }) => ({ item, score }));
}

export function resolveSiteHref(path: string | undefined, siteRoot: string): string {
  if (!path) return "#";
  if (/^(?:https?:|mailto:|tel:)/i.test(path)) return path;
  const prefix = (siteRoot || ".").replace(/\/?$/, "/");
  return prefix + path.replace(/^\//, "");
}

function textElement<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  text: string,
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  element.textContent = text;
  return element;
}

function appendExternalSearchLinks(panel: HTMLElement, query: string, onNavigate?: () => void): void {
  const group = document.createElement("div");
  group.className = "search-web";
  group.setAttribute("aria-label", "外部资料搜索");
  group.append(textElement("span", "联网复核"));

  const encoded = encodeURIComponent(query);
  const travelEncoded = encodeURIComponent(`${query} 旅游攻略`);
  const links = [
    ["携程攻略", `https://you.ctrip.com/searchsite/?query=${travelEncoded}`],
    ["马蜂窝", `https://www.mafengwo.cn/search/q.php?q=${travelEncoded}`],
    ["哔哩哔哩", `https://search.bilibili.com/all?keyword=${travelEncoded}`],
    ["抖音", `https://www.douyin.com/search/${travelEncoded}`],
    ["百度图片", `https://image.baidu.com/search/index?tn=baiduimage&word=${travelEncoded}`],
    ["小红书", `https://www.xiaohongshu.com/search_result?keyword=${encoded}&type=54`],
  ] as const;

  for (const [label, href] of links) {
    const link = textElement("a", label);
    link.href = href;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.setAttribute("aria-label", `${label}（新窗口打开）`);
    if (onNavigate) link.addEventListener("click", onNavigate);
    group.append(link);
  }
  panel.append(group);
}

let searchIndexPromise: Promise<TravelSearchItem[]> | undefined;

export function ensureSearchIndex(source: string): Promise<TravelSearchItem[]> {
  if (Array.isArray(window.TRAVEL_SEARCH_INDEX) && window.TRAVEL_SEARCH_INDEX.length > 0) {
    return Promise.resolve(window.TRAVEL_SEARCH_INDEX);
  }
  if (searchIndexPromise) return searchIndexPromise;
  if (!source) return Promise.reject(new Error("搜索索引地址缺失"));

  searchIndexPromise = new Promise<TravelSearchItem[]>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = source;
    script.async = true;
    script.dataset.travelSearchIndex = "true";
    script.addEventListener("load", () => {
      if (Array.isArray(window.TRAVEL_SEARCH_INDEX)) resolve(window.TRAVEL_SEARCH_INDEX);
      else reject(new Error("搜索索引格式无效"));
    }, { once: true });
    script.addEventListener("error", () => reject(new Error("搜索索引加载失败")), { once: true });
    document.head.append(script);
  }).catch((error: unknown) => {
    searchIndexPromise = undefined;
    throw error;
  });
  return searchIndexPromise;
}

export function bootstrapSiteSearch(): void {
  const container = document.querySelector<HTMLElement>(".global-search");
  const input = document.querySelector<HTMLInputElement>("#siteSearch");
  const panel = document.querySelector<HTMLElement>("#siteSearchResults");
  const options = document.querySelector<HTMLElement>("#siteSearchOptions");
  const recentPanel = document.querySelector<HTMLElement>("#siteSearchRecent");
  if (!container || !input || !panel || !options || !recentPanel) return;

  let items = Array.isArray(window.TRAVEL_SEARCH_INDEX)
    ? window.TRAVEL_SEARCH_INDEX
    : [];
  const siteRoot = document.body.dataset.siteRoot || ".";
  const searchIndexSource = document.body.dataset.searchIndex || "";
  let activeIndex = -1;
  let searchRequest = 0;

  const optionNodes = (): HTMLAnchorElement[] =>
    Array.from(options.querySelectorAll<HTMLAnchorElement>(".search-result"));

  const recordSearch = (query: string): void => {
    const recent = rememberSearchQuery(storedArray(SEARCH_HISTORY_KEY), query);
    try {
      localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(recent));
    } catch {
      // Storage may be unavailable in private or restricted browser contexts.
    }
  };

  const setExpanded = (expanded: boolean): void => {
    panel.hidden = !expanded;
    input.setAttribute("aria-expanded", String(expanded));
    if (!expanded) {
      activeIndex = -1;
      input.removeAttribute("aria-activedescendant");
    }
  };

  const setActive = (index: number): void => {
    const nodes = optionNodes();
    if (nodes.length === 0) return;
    activeIndex = Math.max(0, Math.min(index, nodes.length - 1));
    nodes.forEach((node, nodeIndex) => {
      const selected = nodeIndex === activeIndex;
      node.classList.toggle("active", selected);
      node.setAttribute("aria-selected", String(selected));
    });
    const active = nodes[activeIndex];
    input.setAttribute("aria-activedescendant", active.id);
    active.scrollIntoView({ block: "nearest" });
  };

  const appendRecentGroup = (
    parent: HTMLElement,
    label: string,
    children: readonly HTMLElement[],
  ): void => {
    if (children.length === 0) return;
    const group = document.createElement("section");
    group.className = "search-recent-group";
    group.append(textElement("h3", label));
    const list = document.createElement("div");
    list.className = "search-recent-list";
    list.append(...children);
    group.append(list);
    parent.append(group);
  };

  const renderRecentActivity = (): boolean => {
    recentPanel.replaceChildren();
    const searches = normalizeRecentSearches(storedArray(SEARCH_HISTORY_KEY));
    const visits = normalizeRecentVisits(storedArray(VISIT_HISTORY_KEY));
    if (searches.length === 0 && visits.length === 0) {
      recentPanel.hidden = true;
      return false;
    }

    const heading = document.createElement("div");
    heading.className = "search-recent-head";
    heading.append(textElement("strong", "最近使用"));
    const clear = textElement("button", "清除记录");
    clear.type = "button";
    clear.className = "search-recent-clear";
    clear.addEventListener("click", () => {
      try {
        localStorage.removeItem(SEARCH_HISTORY_KEY);
        localStorage.removeItem(VISIT_HISTORY_KEY);
      } catch {
        // Keep the UI usable even if storage removal is rejected.
      }
      renderRecentActivity();
      setExpanded(false);
      input.focus();
    });
    heading.append(clear);
    recentPanel.append(heading);

    const searchButtons = searches.map((query) => {
      const button = textElement("button", query);
      button.type = "button";
      button.className = "search-recent-query";
      button.addEventListener("click", () => {
        input.value = query;
        requestRender();
        input.focus();
      });
      return button;
    });
    appendRecentGroup(recentPanel, "最近搜索", searchButtons);

    const visitLinks = visits.map((entry) => {
      const link = textElement("a", entry.name.replace("旅游攻略", ""));
      link.className = "search-recent-visit";
      link.href = resolveSiteHref(entry.href, siteRoot);
      return link;
    });
    appendRecentGroup(recentPanel, "最近浏览", visitLinks);
    recentPanel.hidden = false;
    return true;
  };

  const render = (): void => {
    const query = input.value.trim();
    options.replaceChildren();
    activeIndex = -1;
    input.removeAttribute("aria-activedescendant");
    panel.querySelector(".search-web")?.remove();
    if (!query) {
      setExpanded(renderRecentActivity());
      return;
    }

    recentPanel.hidden = true;

    const results = rankSearchItems(items, query);
    if (results.length === 0) {
      const empty = textElement("div", "本站没有匹配；可修改关键词，或使用下方入口联网复核。");
      empty.className = "search-empty";
      empty.setAttribute("role", "status");
      options.append(empty);
    } else {
      results.forEach(({ item }, index) => {
        const link = document.createElement("a");
        link.id = `site-search-option-${index}`;
        link.className = "search-result";
        link.href = item.href || resolveSiteHref(item.path, siteRoot);
        link.setAttribute("role", "option");
        link.setAttribute("aria-selected", "false");
        const highlights = (item.highlights ?? []).slice(0, 3).join("、") || item.subtitle || "";
        const foods = (item.foods ?? []).slice(0, 3).join("、");
        const meta = [item.province, highlights, foods ? `吃：${foods}` : ""]
          .filter(Boolean)
          .join(" · ");
        link.append(
          textElement("strong", item.title),
          textElement("span", meta),
          textElement("small", item.subtitle || "查看完整城市攻略"),
        );
        link.addEventListener("pointermove", () => setActive(index));
        link.addEventListener("click", () => recordSearch(query));
        options.append(link);
      });
    }
    appendExternalSearchLinks(panel, query, () => recordSearch(query));
    setExpanded(true);
  };

  const requestRender = (): void => {
    const query = input.value.trim();
    const request = ++searchRequest;
    if (!query || items.length > 0) {
      render();
      return;
    }
    options.replaceChildren();
    panel.querySelector(".search-web")?.remove();
    const loading = textElement("div", "正在载入城市与攻略索引…");
    loading.className = "search-empty";
    loading.setAttribute("role", "status");
    options.append(loading);
    setExpanded(true);
    void ensureSearchIndex(searchIndexSource).then((loadedItems) => {
      if (request !== searchRequest) return;
      items = loadedItems;
      render();
    }).catch(() => {
      if (request !== searchRequest) return;
      options.replaceChildren();
      const failure = textElement("div", "搜索索引加载失败；请检查网络后重试，或使用下方入口联网复核。");
      failure.className = "search-empty";
      failure.setAttribute("role", "status");
      options.append(failure);
      appendExternalSearchLinks(panel, query, () => recordSearch(query));
      setExpanded(true);
    });
  };

  input.addEventListener("input", requestRender);
  input.addEventListener("focus", requestRender);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      input.value = "";
      searchRequest += 1;
      options.replaceChildren();
      recentPanel.hidden = true;
      setExpanded(false);
      return;
    }

    const nodes = optionNodes();
    if ((event.key === "ArrowDown" || event.key === "ArrowUp") && nodes.length > 0) {
      event.preventDefault();
      if (panel.hidden) setExpanded(true);
      if (event.key === "ArrowDown") {
        setActive(activeIndex < 0 ? 0 : activeIndex + 1);
      } else {
        setActive(activeIndex < 0 ? nodes.length - 1 : activeIndex - 1);
      }
      return;
    }

    if (event.key === "Enter" && nodes.length > 0) {
      event.preventDefault();
      (nodes[activeIndex] || nodes[0]).click();
    }
  });

  document.addEventListener("pointerdown", (event) => {
    if (event.target instanceof Node && !container.contains(event.target)) {
      setExpanded(false);
    }
  });

  window.addEventListener("storage", (event) => {
    if ((event.key === SEARCH_HISTORY_KEY || event.key === VISIT_HISTORY_KEY) && !input.value.trim()) {
      setExpanded(renderRecentActivity());
    }
  });
}

export function bootstrapDestinationNavigation(): void {
  const groups = Array.from(document.querySelectorAll<HTMLDetailsElement>(".province-nav[data-nav-group]"));
  if (groups.length === 0) return;
  const searchIndexSource = document.body.dataset.searchIndex || "";
  const siteRoot = document.body.dataset.siteRoot || ".";

  const renderGroup = (details: HTMLDetailsElement, items: readonly TravelSearchItem[]): void => {
    const menu = details.querySelector<HTMLElement>("[data-destination-menu]");
    if (!menu) return;
    const group = details.dataset.navGroup || "";
    const matches = destinationItemsForGroup(items, group);
    menu.replaceChildren();
    if (matches.length === 0) {
      const empty = textElement("p", "暂无城市。");
      empty.className = "province-menu-status";
      menu.append(empty);
    } else {
      matches.forEach((item) => {
        const link = textElement("a", item.city || item.title.replace("旅游攻略", ""));
        link.className = "destination-city";
        link.href = item.href || resolveSiteHref(item.path, siteRoot);
        if (item.path && location.pathname.endsWith(`/${item.path}`)) {
          link.classList.add("active");
          link.setAttribute("aria-current", "page");
        }
        menu.append(link);
      });
    }
    menu.setAttribute("aria-busy", "false");
    details.dataset.loaded = "true";
  };

  groups.forEach((details) => {
    details.addEventListener("toggle", () => {
      if (!details.open) return;
      groups.forEach((peer) => {
        if (peer !== details) peer.open = false;
      });
      if (details.dataset.loaded === "true") return;
      const menu = details.querySelector<HTMLElement>("[data-destination-menu]");
      if (menu) {
        menu.setAttribute("aria-busy", "true");
        menu.replaceChildren(textElement("p", "载入城市…"));
      }
      void ensureSearchIndex(searchIndexSource)
        .then((items) => renderGroup(details, items))
        .catch(() => {
          if (!menu) return;
          const failure = textElement("p", "载入失败，请重试。");
          failure.className = "province-menu-status";
          failure.setAttribute("role", "status");
          menu.replaceChildren(failure);
          menu.setAttribute("aria-busy", "false");
        });
    });
  });
}
