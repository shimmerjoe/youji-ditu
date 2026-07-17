
(function () {
  const input = document.getElementById("guideSearch");
  const content = document.getElementById("guideContent");
  const sections = Array.from(document.querySelectorAll(".guide-section"));
  const tocLinks = Array.from(document.querySelectorAll(".toc a"));
  const toTop = document.getElementById("toTop");
  const printBtn = document.getElementById("printPage");
  const expandBtn = document.getElementById("expandAll");
  const navGroups = Array.from(document.querySelectorAll(".nav-group, .destination-nav"));
  const navToggle = document.getElementById("navToggle");
  const header = document.querySelector(".site-header");
  const siteSearch = document.getElementById("siteSearch");
  const siteSearchResults = document.getElementById("siteSearchResults");
  const siteSearchData = document.getElementById("siteSearchData");
  const siteRoot = document.body.dataset.siteRoot || ".";
  const cityExplorerSearch = document.getElementById("cityExplorerSearch");
  const cityExplorerCards = Array.from(document.querySelectorAll("#cityExplorer .city-card"));
  const provincePills = Array.from(document.querySelectorAll(".province-pill"));
  const travelFinderForm = document.getElementById("travelFinderForm");
  const travelQuery = document.getElementById("travelQuery");
  const travelRegion = document.getElementById("travelRegion");
  const travelSeason = document.getElementById("travelSeason");
  const travelDays = document.getElementById("travelDays");
  const travelTheme = document.getElementById("travelTheme");
  const travelTransport = document.getElementById("travelTransport");
  const travelFinderSummary = document.getElementById("travelFinderSummary");
  const cityExplorerSummary = document.getElementById("cityExplorerSummary");
  const cityLoadMore = document.getElementById("cityLoadMore");
  const CITY_PAGE_SIZE = 36;
  let emptyBox = null;
  let activeProvince = "全部";
  let cityVisibleLimit = CITY_PAGE_SIZE;

  function normalize(s) {
    return (s || "").toLowerCase().trim();
  }

  function readSearchData() {
    if (Array.isArray(window.TRAVEL_SEARCH_INDEX)) return window.TRAVEL_SEARCH_INDEX;
    if (!siteSearchData) return [];
    try {
      return JSON.parse(siteSearchData.textContent || "[]");
    } catch (error) {
      return [];
    }
  }

  const allSearchItems = readSearchData();

  function rootHref(path) {
    if (!path || /^(https?:|mailto:|tel:)/.test(path)) return path || "#";
    const prefix = (siteRoot || ".").replace(/\/?$/, "/");
    return prefix + path.replace(/^\//, "");
  }

  function searchScore(item, query) {
    const tokens = normalize(query).split(/\s+/).filter(Boolean);
    if (!tokens.length) return 0;
    const title = normalize(item.title);
    const city = normalize(item.city);
    const province = normalize(item.province);
    const text = normalize([
      item.title,
      item.subtitle,
      item.province,
      item.city,
      (item.highlights || []).join(" "),
      (item.foods || []).join(" "),
      item.keywords || "",
    ].join(" "));
    let score = 0;
    for (const token of tokens) {
      if (!text.includes(token)) return 0;
      if (title.includes(token)) score += 10;
      if (city.includes(token)) score += 8;
      if (province.includes(token)) score += 4;
      score += 1;
    }
    return score;
  }

  function renderSiteSearch() {
    if (!siteSearch || !siteSearchResults) return;
    const q = siteSearch.value.trim();
    if (!q) {
      siteSearchResults.hidden = true;
      siteSearchResults.innerHTML = "";
      return;
    }
    const results = allSearchItems
      .map((item) => ({ item, score: searchScore(item, q) }))
      .filter((result) => result.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 10);
    siteSearchResults.hidden = false;
    const local = results.length
      ? results.map(({ item }) => {
          const highlights = (item.highlights || []).slice(0, 3).join("、") || item.subtitle;
          const foods = (item.foods || []).slice(0, 3).join("、");
          const meta = [item.province, highlights, foods ? "吃：" + foods : ""].filter(Boolean).join(" · ");
          return `<a class="search-result" href="${item.href || rootHref(item.path)}"><strong>${item.title}</strong><span>${meta}</span><small>${item.subtitle}</small></a>`;
        }).join("")
      : '<div class="search-empty">本站没有匹配，试试下方联网搜索。</div>';
    siteSearchResults.innerHTML = local + webSearchLinks(q);
  }

  // 联网搜索入口（新标签打开外部搜索，网页端与 App 内置浏览器都可用）
  function webSearchLinks(q) {
    const kw = encodeURIComponent(q);
    const kwt = encodeURIComponent(q + " 旅游攻略");
    // 小红书 web 端需登录才显示结果；携程/抖音/马蜂窝/百度图片可直接浏览。
    return '<div class="search-web"><span>联网搜索</span>' +
      '<a href="https://you.ctrip.com/searchsite/?query=' + kwt + '" target="_blank" rel="noreferrer">携程攻略</a>' +
      '<a href="https://www.mafengwo.cn/search/q.php?q=' + kwt + '" target="_blank" rel="noreferrer">马蜂窝</a>' +
      '<a href="https://www.douyin.com/search/' + kwt + '" target="_blank" rel="noreferrer">抖音</a>' +
      '<a href="https://image.baidu.com/search/index?tn=baiduimage&word=' + kwt + '" target="_blank" rel="noreferrer">百度图片</a>' +
      '<a href="https://www.xiaohongshu.com/search_result?keyword=' + kw + '&type=54" target="_blank" rel="noreferrer">小红书</a>' +
      '</div>';
  }

  function filterCityExplorer(resetLimit) {
    if (!cityExplorerCards.length) return;
    if (resetLimit) cityVisibleLimit = CITY_PAGE_SIZE;
    const q = normalize(travelQuery ? travelQuery.value : (cityExplorerSearch ? cityExplorerSearch.value : ""));
    const region = travelRegion ? travelRegion.value : "";
    const season = travelSeason ? travelSeason.value : "";
    const days = travelDays ? travelDays.value : "";
    const theme = travelTheme ? travelTheme.value : "";
    const transport = travelTransport ? travelTransport.value : "";
    const matches = cityExplorerCards.filter((card) => {
      const provinceHit = activeProvince === "全部" || card.dataset.province === activeProvince;
      const textHit = !q || normalize(card.dataset.search).includes(q);
      const regionHit = !region || card.dataset.region === region;
      const seasonHit = !season || normalize(card.dataset.season).includes(normalize(season));
      const daysHit = !days || card.dataset.days === days;
      const themeHit = !theme || normalize(card.dataset.theme).includes(normalize(theme));
      const transportHit = !transport || normalize(card.dataset.transport).includes(normalize(transport));
      return provinceHit && textHit && regionHit && seasonHit && daysHit && themeHit && transportHit;
    });
    cityExplorerCards.forEach((card) => card.classList.add("is-hidden"));
    matches.slice(0, cityVisibleLimit).forEach((card) => card.classList.remove("is-hidden"));
    const shown = Math.min(matches.length, cityVisibleLimit);
    const summary = matches.length
      ? `已匹配 ${matches.length} 座城市，当前显示 ${shown} 座`
      : "没有匹配城市，请放宽一个条件或重置筛选";
    if (travelFinderSummary) travelFinderSummary.textContent = summary;
    if (cityExplorerSummary) cityExplorerSummary.textContent = summary;
    if (cityLoadMore) {
      cityLoadMore.hidden = shown >= matches.length;
      cityLoadMore.textContent = `再显示 ${Math.min(CITY_PAGE_SIZE, matches.length - shown)} 座`;
    }
  }

  function readFinderState() {
    if (!travelFinderForm) return;
    const params = new URLSearchParams(window.location.search);
    if (travelQuery) travelQuery.value = params.get("q") || "";
    if (travelRegion) travelRegion.value = params.get("region") || "";
    if (travelSeason) travelSeason.value = params.get("season") || "";
    if (travelDays) travelDays.value = params.get("days") || "";
    if (travelTheme) travelTheme.value = params.get("theme") || "";
    if (travelTransport) travelTransport.value = params.get("transport") || "";
    activeProvince = params.get("province") || "全部";
    if (cityExplorerSearch) cityExplorerSearch.value = travelQuery ? travelQuery.value : "";
    provincePills.forEach((pill) => {
      pill.classList.toggle("active", (pill.dataset.province || "") === activeProvince);
    });
  }

  function writeFinderState() {
    if (!travelFinderForm) return;
    const params = new URLSearchParams(window.location.search);
    const values = {
      q: travelQuery ? travelQuery.value.trim() : "",
      region: travelRegion ? travelRegion.value : "",
      season: travelSeason ? travelSeason.value : "",
      days: travelDays ? travelDays.value : "",
      theme: travelTheme ? travelTheme.value : "",
      transport: travelTransport ? travelTransport.value : "",
      province: activeProvince === "全部" ? "" : activeProvince,
    };
    Object.keys(values).forEach((key) => {
      if (values[key]) params.set(key, values[key]);
      else params.delete(key);
    });
    const query = params.toString();
    const next = window.location.pathname + (query ? "?" + query : "") + window.location.hash;
    history.replaceState({ finder: values }, "", next);
  }

  function keepTocLinkVisible(link) {
    const toc = link && link.closest(".toc");
    if (!toc || window.matchMedia("(max-width: 920px)").matches) return;
    const top = link.offsetTop;
    const bottom = top + link.offsetHeight;
    const visibleTop = toc.scrollTop;
    const visibleBottom = visibleTop + toc.clientHeight;
    if (top < visibleTop) {
      toc.scrollTop = Math.max(0, top - 8);
    } else if (bottom > visibleBottom) {
      toc.scrollTop = bottom - toc.clientHeight + 8;
    }
  }

  function filter() {
    const q = normalize(input.value);
    let visible = 0;
    sections.forEach((section) => {
      const hit = !q || normalize(section.textContent).includes(q);
      section.classList.toggle("is-hidden", !hit);
      if (hit) visible += 1;
    });
    if (!emptyBox) {
      emptyBox = document.createElement("div");
      emptyBox.className = "search-empty";
      emptyBox.textContent = "没有匹配结果，换一个景点、店铺、城市或月份试试。";
      content.appendChild(emptyBox);
    }
    emptyBox.classList.toggle("is-hidden", visible !== 0);
  }

  if (input) input.addEventListener("input", filter);
  if (printBtn) printBtn.addEventListener("click", () => window.print());
  if (expandBtn) {
    expandBtn.addEventListener("click", () => {
      input.value = "";
      filter();
      const first = document.querySelector(".guide-section");
      if (first) first.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  if (siteSearch) {
    siteSearch.addEventListener("input", renderSiteSearch);
    siteSearch.addEventListener("focus", renderSiteSearch);
    siteSearch.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        siteSearch.value = "";
        renderSiteSearch();
        return;
      }
      const items = siteSearchResults ? Array.from(siteSearchResults.querySelectorAll(".search-result")) : [];
      if (!items.length) return;
      let idx = items.findIndex((el) => el.classList.contains("active"));
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        idx = event.key === "ArrowDown" ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length;
        items.forEach((el, i) => el.classList.toggle("active", i === idx));
        items[idx].scrollIntoView({ block: "nearest" });
      } else if (event.key === "Enter") {
        (items[idx] || items[0]).click();
      }
    });
  }
  document.addEventListener("click", (event) => {
    if (event.target.closest(".global-search")) return;
    if (siteSearchResults) siteSearchResults.hidden = true;
  });

  if (navToggle && header) {
    function closeMobileNav() {
      header.classList.remove("nav-open");
      navToggle.setAttribute("aria-expanded", "false");
    }
    navToggle.addEventListener("click", () => {
      const open = header.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.querySelectorAll(".top-nav a").forEach((link) => {
      link.addEventListener("click", () => {
        closeMobileNav();
      });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && header.classList.contains("nav-open")) {
        closeMobileNav();
        navToggle.focus();
      }
    });
  }

  if (cityExplorerSearch) cityExplorerSearch.addEventListener("input", () => {
    if (travelQuery) travelQuery.value = cityExplorerSearch.value;
    filterCityExplorer(true);
    writeFinderState();
  });
  if (travelQuery) travelQuery.addEventListener("input", () => {
    if (cityExplorerSearch) cityExplorerSearch.value = travelQuery.value;
    filterCityExplorer(true);
    writeFinderState();
  });
  [travelRegion, travelSeason, travelDays, travelTheme, travelTransport].forEach((control) => {
    if (control) control.addEventListener("change", () => {
      filterCityExplorer(true);
      writeFinderState();
    });
  });
  if (travelFinderForm) {
    travelFinderForm.addEventListener("submit", (event) => event.preventDefault());
    travelFinderForm.addEventListener("reset", () => {
      setTimeout(() => {
        activeProvince = "全部";
        provincePills.forEach((pill) => pill.classList.toggle("active", (pill.dataset.province || "") === "全部"));
        if (cityExplorerSearch) cityExplorerSearch.value = "";
        filterCityExplorer(true);
        writeFinderState();
      }, 0);
    });
  }
  if (cityLoadMore) cityLoadMore.addEventListener("click", () => {
    cityVisibleLimit += CITY_PAGE_SIZE;
    filterCityExplorer(false);
  });
  provincePills.forEach((pill) => {
    pill.addEventListener("click", () => {
      activeProvince = pill.dataset.province || "全部";
      if (travelRegion) travelRegion.value = "";
      provincePills.forEach((item) => item.classList.toggle("active", item === pill));
      filterCityExplorer(true);
      writeFinderState();
    });
  });
  readFinderState();
  filterCityExplorer(true);
  window.addEventListener("popstate", () => {
    readFinderState();
    filterCityExplorer(true);
  });

  navGroups.forEach((group) => {
    group.addEventListener("toggle", () => {
      if (!group.open) return;
      navGroups.forEach((other) => {
        if (other !== group) other.open = false;
      });
    });
  });
  document.addEventListener("click", (event) => {
    if (event.target.closest(".nav-group, .destination-nav")) return;
    navGroups.forEach((group) => { group.open = false; });
  });

  const observer = new IntersectionObserver((entries) => {
    const active = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!active) return;
    let activeLink = null;
    tocLinks.forEach((a) => {
      const hit = a.getAttribute("href") === "#" + active.target.id;
      a.classList.toggle("active", hit);
      if (hit) activeLink = a;
    });
    if (activeLink) keepTocLinkVisible(activeLink);
  }, { rootMargin: "-20% 0px -65% 0px", threshold: [0.1, 0.3, 0.6] });
  sections.forEach((section) => observer.observe(section));

  window.addEventListener("scroll", () => {
    if (toTop) toTop.classList.toggle("visible", window.scrollY > 720);
  });
  if (toTop) toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

  // 顶部阅读进度条
  const progress = document.createElement("div");
  progress.className = "read-progress";
  document.body.appendChild(progress);
  function updateProgress() {
    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    const top = window.scrollY || doc.scrollTop || 0;
    const pct = max > 0 ? Math.min(top / max, 1) : 0;
    progress.style.width = (pct * 100).toFixed(2) + "%";
  }
  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateProgress);
  updateProgress();

  // 滚动渐入
  const revealEls = Array.from(document.querySelectorAll(".reveal"));
  if (revealEls.length) {
    if ("IntersectionObserver" in window) {
      const ro = new IntersectionObserver((entries, obs) => {
        entries.forEach((e) => {
          if (e.isIntersecting) { e.target.classList.add("in"); obs.unobserve(e.target); }
        });
      }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
      revealEls.forEach((el) => ro.observe(el));
    } else {
      revealEls.forEach((el) => el.classList.add("in"));
    }
  }

  // 数据速览数字滚动
  const counters = Array.from(document.querySelectorAll(".stat-count"));
  function animateCount(el) {
    const target = parseInt(el.dataset.count, 10) || 0;
    const dur = 1100;
    const start = performance.now();
    function step(now) {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased).toString();
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  if (counters.length) {
    if ("IntersectionObserver" in window) {
      const co = new IntersectionObserver((entries, obs) => {
        entries.forEach((e) => {
          if (e.isIntersecting) { animateCount(e.target); obs.unobserve(e.target); }
        });
      }, { threshold: 0.5 });
      counters.forEach((el) => co.observe(el));
    } else {
      counters.forEach(animateCount);
    }
  }

  // 精选主题 / 工具 → 联动城市筛选并滚动到城市攻略
  const explorerSection = document.getElementById("city-explorer");
  function gotoExplorer(kw) {
    if (cityExplorerSearch) {
      cityExplorerSearch.value = kw || "";
      if (travelQuery) travelQuery.value = kw || "";
      if (travelTheme && Array.from(travelTheme.options).some((option) => option.value === kw)) {
        travelTheme.value = kw;
        cityExplorerSearch.value = "";
        if (travelQuery) travelQuery.value = "";
      }
      activeProvince = "全部";
      provincePills.forEach((p) => p.classList.toggle("active", (p.dataset.province || "") === "全部"));
      filterCityExplorer(true);
      writeFinderState();
    }
    if (explorerSection) explorerSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  document.querySelectorAll(".theme-card").forEach((card) => {
    card.addEventListener("click", () => gotoExplorer(card.dataset.themeSearch || ""));
  });
  // 工具结果里的「按主题筛选」行动按钮（事件委托）
  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-goto]");
    if (a) { e.preventDefault(); gotoExplorer(a.dataset.goto); }
  });

  // 工具：行程节奏速算
  const tripDays = document.getElementById("tripDays");
  const tripPaceOut = document.getElementById("tripPaceOut");
  function updateTripPace() {
    if (!tripDays || !tripPaceOut) return;
    let d = parseInt(tripDays.value, 10);
    if (isNaN(d) || d < 1) d = 1;
    if (d > 30) d = 30;
    let cities, pace, tip;
    if (d <= 2) { cities = "1"; pace = "单城深度"; tip = "锁定 1 座城市，集中玩核心区与代表美食，不折腾远郊。"; }
    else if (d <= 4) { cities = "1–2"; pace = "1 主 1 辅"; tip = "1 座主城 + 半天周边，留出机动时间应对天气与排队。"; }
    else if (d <= 7) { cities = "2–3"; pace = "主线串联"; tip = "2–3 座临近城市连成一条线，避免天天换酒店。"; }
    else if (d <= 12) { cities = "3–4"; pace = "区域环线"; tip = "按省 / 片区走环线，预留 1 天缓冲与休整。"; }
    else { cities = "4–6"; pace = "跨区慢游"; tip = "拆成 2 段、每段 1 个区域，体力和预算都更可控。"; }
    tripPaceOut.innerHTML = "建议覆盖 <strong>" + cities + "</strong> 座城市 · 节奏：<strong>" + pace + "</strong><br>" + tip +
      '<br><button type="button" class="tool-action" data-goto="">去「城市攻略」挑城市 →</button>';
  }
  if (tripDays) { tripDays.addEventListener("input", updateTripPace); updateTripPace(); }

  // 工具：月份适宜速查（含可点击的主题筛选关键词）
  const tripMonth = document.getElementById("tripMonth");
  const monthGuideOut = document.getElementById("monthGuideOut");
  const MONTH_GUIDE = {
    1: ["雪山 · 温泉 · 冬日暖阳", "丽江 / 香格里拉雪景、腾冲温泉、西双版纳避寒", "雪山"],
    2: ["早春花事 · 民俗年味", "罗平油菜花与樱花前奏、古镇过年氛围", "花"],
    3: ["赏花季 · 踏青", "贵安樱花、罗平油菜花、江南早春园林", "花"],
    4: ["春花尾声 · 山水回暖", "川西草甸返青、桂林漓江烟雨、苏杭园林", "喀斯特"],
    5: ["初夏 · 高原最佳", "稻城亚丁、川西雪山草原、洱海骑行", "雪山"],
    6: ["避暑前奏 · 雨季初", "贵州凉都避暑、西双版纳雨林、高原清凉", "避暑"],
    7: ["盛夏避暑 · 草原花海", "六盘水 / 贵阳避暑、乌蒙草原、高原花海", "避暑"],
    8: ["避暑 · 高原观星", "川西高原、香格里拉、海拔高处更凉爽", "避暑"],
    9: ["秋色初现 · 舒适月", "稻城亚丁金秋、九寨沟、各地秋高气爽", "雪山"],
    10: ["最佳秋色 · 黄金期", "九寨沟 / 黄龙、川西彩林、层林尽染", "雪山"],
    11: ["深秋红叶 · 银杏", "腾冲银杏村、川西彩林尾声、江南红枫", "古镇"],
    12: ["初冬 · 温泉避寒", "腾冲火山热海、西双版纳 / 海南避寒、雪山初雪", "温泉"]
  };
  function updateMonthGuide() {
    if (!tripMonth || !monthGuideOut) return;
    const m = parseInt(tripMonth.value, 10);
    const g = MONTH_GUIDE[m];
    if (!g) { monthGuideOut.textContent = ""; return; }
    monthGuideOut.innerHTML = "<strong>" + m + " 月推荐主题</strong>：" + g[0] + "<br>去处参考：" + g[1] +
      '<br><button type="button" class="tool-action" data-goto="' + g[2] + '">按「' + g[2] + '」看推荐城市 →</button>';
  }
  if (tripMonth) {
    const nowM = new Date().getMonth() + 1;
    tripMonth.value = String(nowM);
    tripMonth.addEventListener("change", updateMonthGuide);
    updateMonthGuide();
  }

  // 工具：打包清单生成
  const packTypes = document.getElementById("packTypes");
  const packListOut = document.getElementById("packListOut");
  const PACK_BASE = ["身份证 / 证件", "手机 + 充电宝", "常用药品", "移动支付 + 少量现金"];
  const PACK_EXTRA = {
    city: ["舒适步行鞋", "轻便单肩包", "折叠雨伞"],
    mountain: ["登山鞋 + 速干衣", "冲锋衣 / 防风层", "护膝 + 登山杖", "能量补给"],
    plateau: ["防晒霜 + 墨镜 + 帽子", "保暖外套（昼夜温差大）", "润唇膏 / 保湿", "按需备抗高反药"],
    summer: ["防晒 + 遮阳", "驱蚊液", "薄外套（室内空调）", "备用换洗衣物"],
    winter: ["羽绒服 / 厚外套", "保暖帽 + 手套 + 围巾", "保湿护肤", "暖宝宝"]
  };
  let activePack = "city";
  function updatePackList() {
    if (!packListOut) return;
    const items = PACK_BASE.concat(PACK_EXTRA[activePack] || []);
    packListOut.innerHTML = "<strong>随身清单</strong><ul>" + items.map((i) => "<li>" + i + "</li>").join("") + "</ul>";
  }
  if (packTypes) {
    packTypes.querySelectorAll(".tool-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        activePack = chip.dataset.pack || "city";
        packTypes.querySelectorAll(".tool-chip").forEach((c) => c.classList.toggle("active", c === chip));
        updatePackList();
      });
    });
    updatePackList();
  }

  // 随机城市探索
  const randomBtn = document.getElementById("randomCity");
  if (randomBtn) {
    randomBtn.addEventListener("click", () => {
      const visible = cityExplorerCards.filter((c) => !c.classList.contains("is-hidden"));
      const pool = visible.length ? visible : cityExplorerCards;
      if (!pool.length) return;
      const href = pool[Math.floor(Math.random() * pool.length)].getAttribute("href");
      if (href) window.location.href = href;
    });
  }

  // 图片加载淡入（用内联样式，禁用 JS 时图片始终可见，不会被隐藏）
  document.querySelectorAll(".city-card.rich img, .media-card img, .item-thumb, .hero-gallery img").forEach((img) => {
    if (img.complete && img.naturalWidth > 0) return;
    img.style.opacity = "0";
    img.style.transition = "opacity .5s ease";
    const show = () => { img.style.opacity = "1"; };
    img.addEventListener("load", show, { once: true });
    img.addEventListener("error", show, { once: true });
  });

  // 跳到主要内容（无障碍）
  const main = document.getElementById("guideContent") || document.querySelector("main");
  if (main) {
    const skip = document.createElement("a");
    skip.href = "#" + (main.id || (main.id = "guideContent"));
    skip.className = "skip-link";
    skip.textContent = "跳到主要内容";
    document.body.insertBefore(skip, document.body.firstChild);
  }

  // ===== 本地存储工具 =====
  const LS = {
    get(k, d) { try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
    del(k) { try { localStorage.removeItem(k); } catch (e) {} }
  };
  const AVATARS = ["👤", "🧭", "🏔️", "🌊", "🏯", "🐼", "🌸", "🍜", "🚆", "⛺", "🦋", "🌅"];

  // 城市页打开时记录最近浏览；不上传数据，最多保留 12 条。
  (function recordCityVisit() {
    const city = document.querySelector(".co-fav[data-key]");
    if (!city) return;
    const entry = {
      key: city.dataset.key,
      name: city.dataset.name,
      href: city.dataset.href,
      sub: city.dataset.sub,
      viewedAt: new Date().toISOString()
    };
    const recent = LS.get("tay_recent", []).filter((item) => item.key !== entry.key);
    recent.unshift(entry);
    LS.set("tay_recent", recent.slice(0, 12));
  })();

  // 把昵称 / 头像同步到顶部用户中心入口（所有页面）
  function applyProfileToHeader() {
    const p = LS.get("tay_profile", {});
    const av = document.getElementById("headerAvatar");
    const nm = document.getElementById("headerUserName");
    if (av && p.avatar) av.textContent = p.avatar;
    if (nm && p.name) nm.textContent = p.name;
  }
  applyProfileToHeader();

  // ===== 收藏 =====
  function getFavs() { return LS.get("tay_favs", []); }
  function setFavs(v) { LS.set("tay_favs", v); }
  function isFav(key) { return getFavs().some((f) => f.key === key); }
  document.querySelectorAll(".fav-btn").forEach((btn) => {
    const key = btn.dataset.key;
    if (isFav(key)) { btn.classList.add("faved"); btn.textContent = "★"; }
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      let favs = getFavs();
      const i = favs.findIndex((f) => f.key === key);
      let nowFav;
      if (i >= 0) { favs.splice(i, 1); nowFav = false; }
      else { favs.unshift({ key: key, name: btn.dataset.name, href: btn.dataset.href, sub: btn.dataset.sub }); nowFav = true; }
      setFavs(favs);
      btn.classList.toggle("faved", nowFav);
      btn.textContent = nowFav ? "★" : "☆";
    });
  });

  // ===== 行程（加入 / 移除）=====
  document.querySelectorAll(".trip-btn").forEach((btn) => {
    const key = btn.dataset.key;
    const inTrip = () => LS.get("tay_trip", []).some((t) => t.key === key);
    if (inTrip()) { btn.classList.add("added"); btn.textContent = "✓"; }
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      let trip = LS.get("tay_trip", []);
      const i = trip.findIndex((t) => t.key === key);
      let added;
      if (i >= 0) { trip.splice(i, 1); added = false; }
      else { trip.push({ key: key, name: btn.dataset.name, href: btn.dataset.href, sub: btn.dataset.sub }); added = true; }
      LS.set("tay_trip", trip);
      btn.classList.toggle("added", added);
      btn.textContent = added ? "✓" : "＋";
    });
  });

  // ===== 城市页速览：收藏 / 加入行程（带文字标签）=====
  document.querySelectorAll(".co-fav").forEach((btn) => {
    const key = btn.dataset.key;
    const sync = () => { const f = isFav(key); btn.classList.toggle("on", f); btn.textContent = f ? "★ 已收藏" : "☆ 收藏"; };
    sync();
    btn.addEventListener("click", () => {
      let favs = getFavs();
      const i = favs.findIndex((f) => f.key === key);
      if (i >= 0) favs.splice(i, 1);
      else favs.unshift({ key: key, name: btn.dataset.name, href: btn.dataset.href, sub: btn.dataset.sub });
      setFavs(favs);
      sync();
    });
  });
  document.querySelectorAll(".co-trip").forEach((btn) => {
    const key = btn.dataset.key;
    const sync = () => { const t = LS.get("tay_trip", []).some((x) => x.key === key); btn.classList.toggle("on", t); btn.textContent = t ? "✓ 已在行程" : "＋ 加入行程"; };
    sync();
    btn.addEventListener("click", () => {
      let trip = LS.get("tay_trip", []);
      const i = trip.findIndex((x) => x.key === key);
      if (i >= 0) trip.splice(i, 1);
      else trip.push({ key: key, name: btn.dataset.name, href: btn.dataset.href, sub: btn.dataset.sub });
      LS.set("tay_trip", trip);
      sync();
    });
  });
  document.querySelectorAll(".co-share").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const original = "↗ 分享";
      const title = btn.dataset.shareTitle || document.title;
      const url = location.href.split("#")[0];
      try {
        if (navigator.share) {
          await navigator.share({ title: title, text: title, url: url });
          return;
        }
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(url);
        } else {
          const input = document.createElement("input");
          input.value = url;
          input.setAttribute("readonly", "");
          input.style.position = "fixed";
          input.style.opacity = "0";
          document.body.appendChild(input);
          input.select();
          document.execCommand("copy");
          input.remove();
        }
        btn.textContent = "✓ 已复制链接";
        btn.classList.add("copied");
        setTimeout(() => { btn.textContent = original; btn.classList.remove("copied"); }, 1800);
      } catch (error) {
        if (error && error.name === "AbortError") return;
        btn.textContent = "复制失败";
        setTimeout(() => { btn.textContent = original; }, 1800);
      }
    });
  });

  // ===== Hero 大图轮播 =====
  (function () {
    const car = document.getElementById("heroCarousel");
    if (!car) return;
    const slides = Array.from(car.querySelectorAll(".hero-slide"));
    const dots = Array.from(car.querySelectorAll(".hero-dot"));
    if (slides.length <= 1) return;
    let idx = 0, timer = null;
    function go(n) {
      idx = (n + slides.length) % slides.length;
      slides.forEach((s, i) => s.classList.toggle("active", i === idx));
      dots.forEach((d, i) => d.classList.toggle("active", i === idx));
    }
    function start() {
      stop();
      if (document.documentElement.getAttribute("data-motion") === "off") return;
      timer = setInterval(() => go(idx + 1), 4800);
    }
    function stop() { if (timer) clearInterval(timer); timer = null; }
    dots.forEach((d) => d.addEventListener("click", () => { go(parseInt(d.dataset.i, 10)); start(); }));
    car.querySelectorAll(".hero-arrow").forEach((a) => a.addEventListener("click", (e) => {
      e.preventDefault();
      go(idx + parseInt(a.dataset.dir, 10));
      start();
    }));
    car.addEventListener("mouseenter", stop);
    car.addEventListener("mouseleave", start);
    // 触控滑动
    let tx = 0;
    car.addEventListener("touchstart", (e) => { tx = e.touches[0].clientX; stop(); }, { passive: true });
    car.addEventListener("touchend", (e) => {
      const dx = e.changedTouches[0].clientX - tx;
      if (Math.abs(dx) > 40) go(idx + (dx < 0 ? 1 : -1));
      start();
    }, { passive: true });
    document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); else start(); });
    start();
  })();

  // ===== 用户中心 =====
  (function () {
    const tabsWrap = document.getElementById("userTabs");
    if (!tabsWrap) return;
    const tabBtns = Array.from(tabsWrap.querySelectorAll(".user-tab"));
    const panels = Array.from(document.querySelectorAll(".user-panel"));
    tabBtns.forEach((b) => b.addEventListener("click", () => {
      tabBtns.forEach((x) => x.classList.toggle("active", x === b));
      panels.forEach((p) => { p.hidden = p.dataset.panel !== b.dataset.tab; });
    }));

    // 个人信息
    const profile = LS.get("tay_profile", { name: "", avatar: "👤", slogan: "" });
    let chosen = profile.avatar || "👤";
    const nameInput = document.getElementById("ucNameInput");
    const slogan = document.getElementById("ucSlogan");
    const nameShow = document.getElementById("ucNameShow");
    const bigAvatar = document.getElementById("ucAvatar");
    const picker = document.getElementById("avatarPicker");
    if (nameInput) nameInput.value = profile.name || "";
    if (slogan) slogan.value = profile.slogan || "";
    if (nameShow) nameShow.textContent = profile.name || "旅行者";
    if (bigAvatar) bigAvatar.textContent = chosen;
    function syncPickerActive() {
      if (picker) picker.querySelectorAll(".avatar-opt").forEach((x) => x.classList.toggle("active", x.textContent === chosen));
    }
    if (picker) {
      AVATARS.forEach((a) => {
        const b = document.createElement("button");
        b.className = "avatar-opt" + (a === chosen ? " active" : "");
        b.type = "button";
        b.textContent = a;
        b.addEventListener("click", () => { chosen = a; if (bigAvatar) bigAvatar.textContent = a; syncPickerActive(); });
        picker.appendChild(b);
      });
    }
    if (bigAvatar) bigAvatar.addEventListener("click", () => {
      const i = AVATARS.indexOf(chosen);
      chosen = AVATARS[(i + 1) % AVATARS.length];
      bigAvatar.textContent = chosen;
      syncPickerActive();
    });
    const saveBtn = document.getElementById("ucSaveProfile");
    const saveTip = document.getElementById("ucSaveTip");
    if (saveBtn) saveBtn.addEventListener("click", () => {
      const p = { name: nameInput ? nameInput.value.trim() : "", avatar: chosen, slogan: slogan ? slogan.value.trim() : "" };
      LS.set("tay_profile", p);
      if (nameShow) nameShow.textContent = p.name || "旅行者";
      if (saveTip) { saveTip.hidden = false; setTimeout(() => { saveTip.hidden = true; }, 1800); }
      applyProfileToHeader();
    });

    // 设置
    const settings = LS.get("tay_settings", { theme: "auto", vibrancy: "normal", font: "m", motion: "on" });
    function applyTheme() {
      let t = settings.theme || "auto";
      if (t === "auto") t = (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", t);
    }
    function bindSeg(id, key) {
      const seg = document.getElementById(id);
      if (!seg) return;
      seg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.val === settings[key]));
      seg.addEventListener("click", (e) => {
        const b = e.target.closest("button");
        if (!b) return;
        seg.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
        settings[key] = b.dataset.val;
        LS.set("tay_settings", settings);
        const r = document.documentElement;
        r.setAttribute("data-vibrancy", settings.vibrancy);
        r.setAttribute("data-font", settings.font);
        r.setAttribute("data-motion", settings.motion);
        applyTheme();
      });
    }
    bindSeg("setTheme", "theme");
    bindSeg("setVibrancy", "vibrancy");
    bindSeg("setFont", "font");
    bindSeg("setMotion", "motion");
    const reset = document.getElementById("ucResetAll");
    if (reset) reset.addEventListener("click", () => {
      if (confirm("确定清除本地保存的昵称、收藏、行程、路书、旅行工具和设置吗？")) {
        ["tay_profile", "tay_settings", "tay_favs", "tay_recent", "tay_trip", "tay_roadtrips", "tay_last_roadtrip", "tay_checklist", "tay_budget", "tay_notes"].forEach((k) => LS.del(k));
        location.reload();
      }
    });

    // 收藏渲染
    const favGrid = document.getElementById("favGrid");
    const favEmpty = document.getElementById("favEmpty");
    const favCount = document.getElementById("ucFavCount");
    function esc(s) { return String(s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
    function renderFavs() {
      const favs = getFavs();
      if (favCount) favCount.textContent = String(favs.length);
      if (!favGrid) return;
      favGrid.innerHTML = "";
      if (!favs.length) { if (favEmpty) favEmpty.hidden = false; return; }
      if (favEmpty) favEmpty.hidden = true;
      favs.forEach((f) => {
        const div = document.createElement("div");
        div.className = "fav-item";
        div.innerHTML =
          '<img src="assets/images/' + esc(f.key) + '.jpg" alt="' + esc(f.name) + '" width="800" height="480" loading="lazy">' +
          '<div class="fav-item-body"><strong>' + esc(f.name) + '</strong><small>' + esc(f.sub) + '</small>' +
          '<a href="' + esc(f.href) + '">查看攻略 →</a></div>' +
          '<button class="fav-remove" data-key="' + esc(f.key) + '" aria-label="移除收藏">✕</button>';
        favGrid.appendChild(div);
      });
      favGrid.querySelectorAll(".fav-remove").forEach((b) => b.addEventListener("click", () => {
        setFavs(getFavs().filter((x) => x.key !== b.dataset.key));
        renderFavs();
      }));
    }
    renderFavs();

    // 最近浏览
    const historyList = document.getElementById("historyList");
    const historyEmpty = document.getElementById("historyEmpty");
    const historyClear = document.getElementById("historyClear");
    function renderHistory() {
      if (!historyList) return;
      const recent = LS.get("tay_recent", []);
      historyList.innerHTML = "";
      if (!recent.length) {
        if (historyEmpty) historyEmpty.hidden = false;
        if (historyClear) historyClear.hidden = true;
        return;
      }
      if (historyEmpty) historyEmpty.hidden = true;
      if (historyClear) historyClear.hidden = false;
      recent.forEach((item) => {
        const when = item.viewedAt ? new Date(item.viewedAt).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" }) : "刚刚浏览";
        const row = document.createElement("article");
        row.className = "fav-item";
        row.innerHTML =
          '<img src="assets/images/' + esc(item.key) + '.jpg" alt="' + esc(item.name) + '" width="800" height="480" loading="lazy">' +
          '<div class="fav-item-body"><strong>' + esc(item.name) + '</strong><small>' + esc(item.sub) + ' · ' + esc(when) + '</small>' +
          '<a href="' + esc(item.href) + '">继续阅读 →</a></div>';
        historyList.appendChild(row);
      });
    }
    if (historyClear) historyClear.addEventListener("click", () => { LS.del("tay_recent"); renderHistory(); });
    renderHistory();

    // 行程渲染
    const tripList = document.getElementById("tripList");
    const tripEmpty = document.getElementById("tripEmpty");
    const tripSummary = document.getElementById("tripSummary");
    const tripDaysInput = document.getElementById("tripPlanDays");
    const tripCompare = document.getElementById("tripCompare");
    const tripCompareTable = document.getElementById("tripCompareTable");
    let compareOpen = false;
    function getTrip() { return LS.get("tay_trip", []); }
    function setTrip(v) { LS.set("tay_trip", v); }
    function renderTripCompare() {
      if (!tripCompareTable || !tripCompare) return;
      const trip = getTrip();
      tripCompare.disabled = trip.length < 2;
      if (trip.length < 2) compareOpen = false;
      tripCompare.textContent = compareOpen ? "收起对比" : "对比城市";
      tripCompareTable.hidden = !compareOpen;
      if (!compareOpen) { tripCompareTable.innerHTML = ""; return; }
      const selected = trip.slice(0, 4).map((entry) => {
        const profile = allSearchItems.find((item) => item.key === entry.key) || {};
        return { trip: entry, profile: profile };
      });
      const cells = (render) => selected.map(render).join("");
      const row = (label, render) => '<tr><th scope="row">' + label + '</th>' + cells((item) => '<td>' + render(item) + '</td>') + '</tr>';
      const table =
        '<table class="trip-compare-table"><thead><tr><th scope="col">对比项</th>' +
        cells((item) => '<th scope="col"><a href="' + esc(item.trip.href) + '">' + esc(item.trip.name.replace("旅游攻略", "")) + '</a></th>') +
        '</tr></thead><tbody>' +
        row("地区", (item) => esc(item.profile.province || "待补充")) +
        row("适宜季节", (item) => esc(item.profile.season || "见城市攻略")) +
        row("旅行印象", (item) => esc(item.profile.subtitle || item.trip.sub || "见城市攻略")) +
        row("代表景点", (item) => esc((item.profile.highlights || []).slice(0, 4).join("、") || "见城市攻略")) +
        row("代表美食", (item) => esc((item.profile.foods || []).slice(0, 4).join("、") || "见城市攻略")) +
        '</tbody></table>';
      const note = trip.length > 4 ? '<p class="trip-compare-note">为保证可读性，仅对比行程中的前 4 座城市；可通过上移调整顺序。</p>' : "";
      tripCompareTable.innerHTML = table + note;
    }
    function renderTrip() {
      if (!tripList) return;
      const trip = getTrip();
      tripList.innerHTML = "";
      renderTripCompare();
      if (!trip.length) {
        if (tripEmpty) tripEmpty.hidden = false;
        if (tripSummary) tripSummary.innerHTML = "";
        return;
      }
      if (tripEmpty) tripEmpty.hidden = true;
      let days = parseInt(tripDaysInput && tripDaysInput.value, 10);
      if (isNaN(days) || days < 1) days = trip.length;
      const per = days / trip.length;
      const tip = per < 1.2 ? "偏赶，建议减城市或加天数" : (per > 3 ? "较宽松，可加入周边" : "节奏适中");
      if (tripSummary) tripSummary.innerHTML = "共 <strong>" + trip.length + "</strong> 座城市 · 计划 <strong>" + days + "</strong> 天 · 平均每城约 <strong>" + per.toFixed(1) + "</strong> 天（" + tip + "）";
      trip.forEach((t, idx) => {
        const li = document.createElement("li");
        li.className = "trip-item";
        li.innerHTML =
          '<span class="trip-order">' + (idx + 1) + '</span>' +
          '<img src="assets/images/' + esc(t.key) + '.jpg" alt="" width="800" height="480" loading="lazy">' +
          '<div class="trip-item-body"><strong>' + esc(t.name) + '</strong><small>' + esc(t.sub) + '</small><a href="' + esc(t.href) + '">查看攻略 →</a></div>' +
          '<div class="trip-actions">' +
          '<button data-act="up" data-key="' + esc(t.key) + '" aria-label="上移"' + (idx === 0 ? " disabled" : "") + '>↑</button>' +
          '<button data-act="down" data-key="' + esc(t.key) + '" aria-label="下移"' + (idx === trip.length - 1 ? " disabled" : "") + '>↓</button>' +
          '<button data-act="del" data-key="' + esc(t.key) + '" aria-label="移除">✕</button>' +
          '</div>';
        tripList.appendChild(li);
      });
      tripList.querySelectorAll("button[data-act]").forEach((b) => b.addEventListener("click", () => {
        let trip = getTrip();
        const i = trip.findIndex((x) => x.key === b.dataset.key);
        if (i < 0) return;
        if (b.dataset.act === "del") trip.splice(i, 1);
        else if (b.dataset.act === "up" && i > 0) { const t = trip[i - 1]; trip[i - 1] = trip[i]; trip[i] = t; }
        else if (b.dataset.act === "down" && i < trip.length - 1) { const t = trip[i + 1]; trip[i + 1] = trip[i]; trip[i] = t; }
        setTrip(trip);
        renderTrip();
      }));
    }
    if (tripDaysInput) tripDaysInput.addEventListener("input", renderTrip);
    if (tripCompare) tripCompare.addEventListener("click", () => { compareOpen = !compareOpen; renderTripCompare(); });
    const tripClear = document.getElementById("tripClear");
    if (tripClear) tripClear.addEventListener("click", () => { if (confirm("清空行程？")) { setTrip([]); renderTrip(); } });
    renderTrip();

    // 已保存的自驾路书
    const roadbookList = document.getElementById("roadbookList");
    const roadbookEmpty = document.getElementById("roadbookEmpty");
    function getRoadbooks() { return LS.get("tay_roadtrips", []); }
    function renderRoadbooks() {
      if (!roadbookList) return;
      const plans = getRoadbooks();
      roadbookList.innerHTML = "";
      if (!plans.length) { if (roadbookEmpty) roadbookEmpty.hidden = false; return; }
      if (roadbookEmpty) roadbookEmpty.hidden = true;
      plans.forEach((plan) => {
        const div = document.createElement("article");
        div.className = "roadbook-item";
        const summary = plan.summary || {};
        div.innerHTML =
          '<div><strong>' + esc(plan.title) + '</strong><small>' + esc(summary.days) + ' 天 · 约 ' + esc(summary.totalKm) + ' 公里 · ' + esc(plan.generatedAt) + '</small></div>' +
          '<div class="roadbook-actions"><a href="roadtrip.html?plan=' + encodeURIComponent(plan.id) + '">打开</a>' +
          '<button type="button" data-roadbook-id="' + esc(plan.id) + '">删除</button></div>';
        roadbookList.appendChild(div);
      });
      roadbookList.querySelectorAll("button[data-roadbook-id]").forEach((button) => button.addEventListener("click", () => {
        LS.set("tay_roadtrips", getRoadbooks().filter((plan) => plan.id !== button.dataset.roadbookId));
        renderRoadbooks();
      }));
    }
    renderRoadbooks();

    // 旅行工具：清单、预算和笔记均只保存在当前浏览器
    const checklistForm = document.getElementById("checklistForm");
    const checklistInput = document.getElementById("checklistInput");
    const checklistList = document.getElementById("travelChecklist");
    const checklistEmpty = document.getElementById("checklistEmpty");
    const checklistProgress = document.getElementById("checklistProgress");
    function uniqueId(prefix) {
      return prefix + "-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
    }
    function getChecklist() {
      const items = LS.get("tay_checklist", []);
      return Array.isArray(items) ? items : [];
    }
    function setChecklist(items) { LS.set("tay_checklist", items); }
    function renderChecklist() {
      if (!checklistList) return;
      const items = getChecklist();
      const done = items.filter((item) => item.done).length;
      checklistList.innerHTML = "";
      if (checklistProgress) checklistProgress.textContent = done + " / " + items.length;
      if (checklistEmpty) checklistEmpty.hidden = items.length > 0;
      items.forEach((item) => {
        const li = document.createElement("li");
        li.className = "checklist-item" + (item.done ? " done" : "");
        li.innerHTML =
          '<label><input type="checkbox" data-check-id="' + esc(item.id) + '"' + (item.done ? " checked" : "") + '><span>' + esc(item.text) + '</span></label>' +
          '<button class="tool-delete" type="button" data-check-delete="' + esc(item.id) + '" title="删除事项" aria-label="删除清单事项">×</button>';
        checklistList.appendChild(li);
      });
      checklistList.querySelectorAll("input[data-check-id]").forEach((box) => box.addEventListener("change", () => {
        const items = getChecklist();
        const item = items.find((entry) => entry.id === box.dataset.checkId);
        if (item) item.done = box.checked;
        setChecklist(items);
        renderChecklist();
      }));
      checklistList.querySelectorAll("button[data-check-delete]").forEach((button) => button.addEventListener("click", () => {
        setChecklist(getChecklist().filter((item) => item.id !== button.dataset.checkDelete));
        renderChecklist();
      }));
    }
    if (checklistForm) checklistForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = checklistInput ? checklistInput.value.trim() : "";
      if (!text) { if (checklistInput) checklistInput.focus(); return; }
      const items = getChecklist();
      items.push({ id: uniqueId("check"), text: text, done: false });
      setChecklist(items);
      checklistInput.value = "";
      checklistInput.focus();
      renderChecklist();
    });
    renderChecklist();

    const budgetForm = document.getElementById("budgetForm");
    const budgetName = document.getElementById("budgetName");
    const budgetCategory = document.getElementById("budgetCategory");
    const budgetAmount = document.getElementById("budgetAmount");
    const budgetList = document.getElementById("budgetList");
    const budgetEmpty = document.getElementById("budgetEmpty");
    const budgetTotal = document.getElementById("budgetTotal");
    function getBudget() {
      const items = LS.get("tay_budget", []);
      return Array.isArray(items) ? items : [];
    }
    function setBudget(items) { LS.set("tay_budget", items); }
    function formatMoney(value) {
      const amount = Number(value) || 0;
      return "¥" + amount.toFixed(2);
    }
    function renderBudget() {
      if (!budgetList) return;
      const items = getBudget();
      const total = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
      budgetList.innerHTML = "";
      if (budgetTotal) budgetTotal.textContent = formatMoney(total);
      if (budgetEmpty) budgetEmpty.hidden = items.length > 0;
      items.forEach((item) => {
        const li = document.createElement("li");
        li.className = "budget-item";
        li.innerHTML =
          '<div class="budget-item-main"><strong>' + esc(item.name) + '</strong><small>' + esc(item.category) + '</small></div>' +
          '<span class="budget-value">' + formatMoney(item.amount) + '</span>' +
          '<button class="tool-delete" type="button" data-budget-delete="' + esc(item.id) + '" title="删除预算项目" aria-label="删除预算项目">×</button>';
        budgetList.appendChild(li);
      });
      budgetList.querySelectorAll("button[data-budget-delete]").forEach((button) => button.addEventListener("click", () => {
        setBudget(getBudget().filter((item) => item.id !== button.dataset.budgetDelete));
        renderBudget();
      }));
    }
    if (budgetForm) budgetForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const name = budgetName ? budgetName.value.trim() : "";
      const amount = budgetAmount ? Number(budgetAmount.value) : 0;
      if (!name) { if (budgetName) budgetName.focus(); return; }
      if (!Number.isFinite(amount) || amount <= 0) { if (budgetAmount) budgetAmount.focus(); return; }
      const items = getBudget();
      items.push({ id: uniqueId("budget"), name: name, category: budgetCategory ? budgetCategory.value : "其他", amount: amount });
      setBudget(items);
      budgetName.value = "";
      budgetAmount.value = "";
      budgetName.focus();
      renderBudget();
    });
    renderBudget();

    const travelNotes = document.getElementById("travelNotes");
    const notesSaveStatus = document.getElementById("notesSaveStatus");
    let notesTimer = null;
    if (travelNotes) {
      travelNotes.value = LS.get("tay_notes", "");
      travelNotes.addEventListener("input", () => {
        LS.set("tay_notes", travelNotes.value);
        if (notesSaveStatus) {
          notesSaveStatus.textContent = "已保存";
          notesSaveStatus.classList.add("saved");
          clearTimeout(notesTimer);
          notesTimer = setTimeout(() => {
            notesSaveStatus.textContent = "自动保存在本机";
            notesSaveStatus.classList.remove("saved");
          }, 1400);
        }
      });
    }

    function markdownCell(value) {
      return String(value || "").replace(/\|/g, "\\|").replace(/[\r\n]+/g, " ");
    }
    function downloadText(filename, value) {
      const blob = new Blob(["\ufeff" + value], { type: "text/markdown;charset=utf-8" });
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(href), 0);
    }
    const toolsExport = document.getElementById("toolsExport");
    if (toolsExport) toolsExport.addEventListener("click", () => {
      const checklist = getChecklist();
      const budget = getBudget();
      const notes = travelNotes ? travelNotes.value.trim() : LS.get("tay_notes", "").trim();
      const lines = ["# 旅行工作台", "", "> 导出时间：" + new Date().toLocaleString("zh-CN", { hour12: false }), "", "## 出行清单", ""];
      if (checklist.length) checklist.forEach((item) => lines.push("- [" + (item.done ? "x" : " ") + "] " + item.text));
      else lines.push("暂无清单事项。");
      lines.push("", "## 预算记录", "");
      if (budget.length) {
        lines.push("| 分类 | 项目 | 金额 |", "| --- | --- | ---: |");
        budget.forEach((item) => lines.push("| " + markdownCell(item.category) + " | " + markdownCell(item.name) + " | " + formatMoney(item.amount) + " |"));
        lines.push("", "合计：" + formatMoney(budget.reduce((sum, item) => sum + (Number(item.amount) || 0), 0)));
      } else lines.push("暂无预算项目。");
      lines.push("", "## 旅行笔记", "", notes || "暂无旅行笔记。", "");
      downloadText("旅行工作台.md", lines.join("\n"));
    });
  })();

  // 长章节折叠 + 顶层条目计数（渐进增强：无 JS 时正文完整展示）
  document.querySelectorAll(".guide-section").forEach((sec) => {
    const head = sec.querySelector("h2, h3");
    if (!head) return;
    const topItems = sec.querySelectorAll(".md-list.depth-0 > li").length;
    if (topItems >= 4 && !head.querySelector(".section-count")) {
      const badge = document.createElement("span");
      badge.className = "section-count";
      badge.textContent = topItems + " 条";
      head.appendChild(badge);
    }
    const body = document.createElement("div");
    body.className = "section-body";
    let n = head.nextSibling;
    while (n) { const next = n.nextSibling; body.appendChild(n); n = next; }
    sec.appendChild(body);
    requestAnimationFrame(() => {
      if (body.scrollHeight > 660) {
        sec.classList.add("clampable");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "section-toggle";
        btn.textContent = "展开全部 ▾";
        btn.addEventListener("click", () => {
          const open = sec.classList.toggle("expanded");
          btn.textContent = open ? "收起 ▴" : "展开全部 ▾";
          if (!open) sec.scrollIntoView({ behavior: "smooth", block: "start" });
        });
        sec.appendChild(btn);
      }
    });
  });

  // 图片灯箱：点击正文配图 / 参考图放大查看
  const lb = document.createElement("div");
  lb.className = "lightbox";
  lb.innerHTML = '<img alt=""><button class="lightbox-close" type="button" aria-label="关闭">✕</button>';
  document.body.appendChild(lb);
  const lbImg = lb.querySelector("img");
  function openLightbox(src, alt) { lbImg.src = src; lbImg.alt = alt || ""; lb.classList.add("open"); }
  lb.addEventListener("click", () => lb.classList.remove("open"));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") lb.classList.remove("open"); });
  document.querySelectorAll(".item-thumb, .media-card img").forEach((img) => {
    img.style.cursor = "zoom-in";
    img.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); openLightbox(img.currentSrc || img.src, img.alt); });
  });

  // PWA Service Worker（仅在 http/https 下注册；file:// 直接打开会自动跳过）
  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    const root = document.body.dataset.siteRoot || ".";
    window.addEventListener("load", () => navigator.serviceWorker.register(root + "/sw.js").catch(() => {}));
  }
})();
