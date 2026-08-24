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

declare global {
  interface Window {
    TRAVEL_SEARCH_INDEX?: TravelSearchItem[];
  }
}

function normalize(value: string | undefined): string {
  return (value ?? "").toLocaleLowerCase("zh-CN").trim();
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

function appendExternalSearchLinks(panel: HTMLElement, query: string): void {
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
  if (!container || !input || !panel || !options) return;

  let items = Array.isArray(window.TRAVEL_SEARCH_INDEX)
    ? window.TRAVEL_SEARCH_INDEX
    : [];
  const siteRoot = document.body.dataset.siteRoot || ".";
  const searchIndexSource = document.body.dataset.searchIndex || "";
  let activeIndex = -1;
  let searchRequest = 0;

  const optionNodes = (): HTMLAnchorElement[] =>
    Array.from(options.querySelectorAll<HTMLAnchorElement>(".search-result"));

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

  const render = (): void => {
    const query = input.value.trim();
    options.replaceChildren();
    activeIndex = -1;
    input.removeAttribute("aria-activedescendant");
    panel.querySelector(".search-web")?.remove();
    if (!query) {
      setExpanded(false);
      return;
    }

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
        options.append(link);
      });
    }
    appendExternalSearchLinks(panel, query);
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
      appendExternalSearchLinks(panel, query);
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
      render();
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
}
