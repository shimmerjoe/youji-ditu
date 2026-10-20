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
   const cityExplorerSearch = document.getElementById("cityExplorerSearch");
   const cityExplorerCards = Array.from(document.querySelectorAll("#cityExplorer .city-card"));
   const provincePills = Array.from(document.querySelectorAll(".province-pill"));
   const reviewPills = Array.from(document.querySelectorAll(".review-pill"));
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
  const CITY_PAGE_SIZE = window.matchMedia("(max-width: 640px)").matches ? 12
    : window.matchMedia("(max-width: 1100px)").matches ? 24
    : 36;
   let emptyBox = null;
   let activeProvince = "全部";
   let activeReview = "all";
   let cityVisibleLimit = CITY_PAGE_SIZE;

  function normalize(s) {
    return (s || "").toLowerCase().trim();
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
       const reviewHit = activeReview === "all" || card.dataset.reviewStatus === activeReview;
       const textHit = !q || normalize(card.dataset.search).includes(q);
      const regionHit = !region || card.dataset.region === region;
      const seasonHit = !season || normalize(card.dataset.season).includes(normalize(season));
      const daysHit = !days || card.dataset.days === days;
      const themeHit = !theme || normalize(card.dataset.theme).includes(normalize(theme));
      const transportHit = !transport || normalize(card.dataset.transport).includes(normalize(transport));
       return provinceHit && reviewHit && textHit && regionHit && seasonHit && daysHit && themeHit && transportHit;
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
     const params = new URLSearchParams(window.location.search);
    if (travelQuery) travelQuery.value = params.get("q") || "";
    if (travelRegion) travelRegion.value = params.get("region") || "";
    if (travelSeason) travelSeason.value = params.get("season") || "";
    if (travelDays) travelDays.value = params.get("days") || "";
    if (travelTheme) travelTheme.value = params.get("theme") || "";
     if (travelTransport) travelTransport.value = params.get("transport") || "";
     activeProvince = params.get("province") || "全部";
     const review = params.get("review") || "all";
     activeReview = ["all", "reviewed", "pending"].includes(review) ? review : "all";
     if (cityExplorerSearch) cityExplorerSearch.value = travelQuery ? travelQuery.value : (params.get("q") || "");
     provincePills.forEach((pill) => {
       pill.classList.toggle("active", (pill.dataset.province || "") === activeProvince);
     });
     reviewPills.forEach((pill) => {
       pill.classList.toggle("active", (pill.dataset.review || "") === activeReview);
     });
   }

   function writeFinderState() {
     const params = new URLSearchParams(window.location.search);
     const values = {
       q: travelQuery ? travelQuery.value.trim() : (cityExplorerSearch ? cityExplorerSearch.value.trim() : ""),
      region: travelRegion ? travelRegion.value : "",
      season: travelSeason ? travelSeason.value : "",
      days: travelDays ? travelDays.value : "",
      theme: travelTheme ? travelTheme.value : "",
       transport: travelTransport ? travelTransport.value : "",
       province: activeProvince === "全部" ? "" : activeProvince,
       review: activeReview === "all" ? "" : activeReview,
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
    if (!toc) return;
    if (toc.classList.contains("section-tabs-track")) {
      const left = link.offsetLeft - toc.clientWidth / 2 + link.offsetWidth / 2;
      toc.scrollTo({ left: Math.max(0, left), behavior: "smooth" });
      return;
    }
    if (toc.offsetParent === null) return;
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
      emptyBox.className = "search-empty guide-empty";
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

  if (navToggle && header) {
    const compactNav = window.matchMedia("(max-width: 920px)");
    function closeMobileNav() {
      header.classList.remove("nav-open");
      navToggle.setAttribute("aria-expanded", "false");
      document.body.classList.remove("nav-locked");
    }
    navToggle.addEventListener("click", () => {
      const open = header.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", open ? "true" : "false");
      document.body.classList.toggle("nav-locked", open && compactNav.matches);
    });
    document.addEventListener("pointerdown", (event) => {
      if (!header.classList.contains("nav-open")) return;
      if (event.target instanceof Node && header.contains(event.target)) return;
      closeMobileNav();
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
         activeReview = "all";
         provincePills.forEach((pill) => pill.classList.toggle("active", (pill.dataset.province || "") === "全部"));
         reviewPills.forEach((pill) => pill.classList.toggle("active", (pill.dataset.review || "") === "all"));
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
   reviewPills.forEach((pill) => {
     pill.addEventListener("click", () => {
       activeReview = ["all", "reviewed", "pending"].includes(pill.dataset.review || "") ? pill.dataset.review : "all";
       reviewPills.forEach((item) => item.classList.toggle("active", item === pill));
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

  if (toTop && "IntersectionObserver" in window) {
    const scrollThreshold = document.createElement("span");
    scrollThreshold.className = "scroll-threshold";
    scrollThreshold.setAttribute("aria-hidden", "true");
    document.body.appendChild(scrollThreshold);
    const topObserver = new IntersectionObserver(([entry]) => {
      const passedThreshold = !entry.isIntersecting && entry.boundingClientRect.top < 0;
      toTop.classList.toggle("visible", passedThreshold);
    });
    topObserver.observe(scrollThreshold);
  }
  if (toTop) toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

  // 顶部阅读进度条由 CSS scroll-driven animation 驱动，避免逐帧执行 JavaScript。
  const progress = document.createElement("div");
  progress.className = "read-progress";
  progress.setAttribute("aria-hidden", "true");
  document.body.appendChild(progress);

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
      const card = pool[Math.floor(Math.random() * pool.length)];
      const href = card.dataset.href || (card.querySelector(".city-card-title") || {}).href;
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

  // ===== 本地存储工具 =====
  // Values remain backward-compatible JSON, while a small schema envelope
  // records migrations and rejects malformed data instead of rendering it.
  const STORAGE_SCHEMA = 2;
  const STORAGE_META_KEY = "tay_storage_meta";
  const STORAGE_ARRAY_KEYS = new Set(["tay_favs", "tay_recent", "tay_search_recent", "tay_trip", "tay_roadtrips", "tay_checklist", "tay_budget"]);
  const STORAGE_OBJECT_KEYS = new Set(["tay_profile", "tay_settings", "tay_last_roadtrip", "tay_city_checks"]);
  const STORAGE_STRING_KEYS = new Set(["tay_notes"]);
  const STORAGE_KNOWN_KEYS = new Set([
    ...STORAGE_ARRAY_KEYS,
    ...STORAGE_OBJECT_KEYS,
    ...STORAGE_STRING_KEYS,
  ]);

  function parseStored(raw) {
    if (raw == null) return null;
    try { return JSON.parse(raw); } catch (_) { return null; }
  }
  function readStored(key, raw) {
    const value = parseStored(raw);
    // Early versions of the notes field may have been written as plain text;
    // migrate that form instead of treating it as a corrupt object.
    if (value == null && raw != null && STORAGE_STRING_KEYS.has(key)) return raw;
    return value;
  }
  function validStoredValue(key, value) {
    if (STORAGE_ARRAY_KEYS.has(key)) return Array.isArray(value);
    if (STORAGE_OBJECT_KEYS.has(key)) return Boolean(value && typeof value === "object" && !Array.isArray(value));
    if (STORAGE_STRING_KEYS.has(key)) return typeof value === "string";
    return true;
  }
  function migrateStorage() {
    let meta = parseStored(localStorage.getItem(STORAGE_META_KEY));
    const version = Number(meta && meta.version) || 1;
    if (version < STORAGE_SCHEMA) {
      STORAGE_KNOWN_KEYS.forEach((key) => {
        const raw = localStorage.getItem(key);
        if (raw == null) return;
        const value = readStored(key, raw);
        if (!validStoredValue(key, value)) localStorage.removeItem(key);
      });
      meta = { version: STORAGE_SCHEMA, migratedAt: new Date().toISOString() };
      try { localStorage.setItem(STORAGE_META_KEY, JSON.stringify(meta)); } catch (_) {}
    } else if (!meta || version !== STORAGE_SCHEMA) {
      meta = { version: STORAGE_SCHEMA, migratedAt: new Date().toISOString() };
      try { localStorage.setItem(STORAGE_META_KEY, JSON.stringify(meta)); } catch (_) {}
    }
    return meta;
  }
  function emitStorageChange(key, action) {
    window.dispatchEvent(new CustomEvent("tay:storage-change", { detail: { key: key, action: action } }));
  }
  const LS = {
    get(k, d) {
      migrateStorage();
      const value = readStored(k, localStorage.getItem(k));
      if (value == null || !validStoredValue(k, value)) {
        if (value == null && localStorage.getItem(k) != null) {
          try { localStorage.removeItem(k); } catch (_) {}
        }
        return d;
      }
      return value;
    },
    set(k, v) {
      migrateStorage();
      if (!validStoredValue(k, v)) return false;
      try { localStorage.setItem(k, JSON.stringify(v)); emitStorageChange(k, "set"); return true; } catch (_) { return false; }
    },
    del(k) {
      try { localStorage.removeItem(k); emitStorageChange(k, "delete"); } catch (_) {}
    },
    exportData() {
      migrateStorage();
      const data = {};
      STORAGE_KNOWN_KEYS.forEach((key) => {
        const value = readStored(key, localStorage.getItem(key));
        if (value != null && validStoredValue(key, value)) data[key] = value;
      });
      return { schemaVersion: STORAGE_SCHEMA, exportedAt: new Date().toISOString(), data: data };
    },
    importData(payload) {
      if (!payload || typeof payload !== "object" || !payload.data || typeof payload.data !== "object") return false;
      let imported = 0;
      STORAGE_KNOWN_KEYS.forEach((key) => {
        if (!Object.prototype.hasOwnProperty.call(payload.data, key)) return;
        const value = payload.data[key];
        if (!validStoredValue(key, value)) return;
        try { localStorage.setItem(key, JSON.stringify(value)); imported += 1; emitStorageChange(key, "import"); } catch (_) {}
      });
      migrateStorage();
      return imported > 0 || Object.keys(payload.data).length === 0;
    }
  };
  migrateStorage();
  window.TAY_STORAGE = LS;
  window.addEventListener("storage", (event) => {
    if (event.storageArea === localStorage && event.key && event.key.indexOf("tay_") === 0) {
      migrateStorage();
      emitStorageChange(event.key, "external");
    }
  });
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

  // ===== 全站行程工作台 =====
  const tripDockToggle = document.getElementById("tripDockToggle");
  const tripDockCount = document.getElementById("tripDockCount");
  const tripDock = document.getElementById("tripDock");
  const tripDockList = document.getElementById("tripDockList");
  const tripDockEmpty = document.getElementById("tripDockEmpty");
  const tripDockClose = document.getElementById("tripDockClose");
  const tripDockBackdrop = document.getElementById("tripDockBackdrop");
  const tripDockClear = document.getElementById("tripDockClear");
  let tripDockPreviousFocus = null;

  function rootHref(path) {
    const href = String(path || "").trim();
    if (!href || /^(?:https?:|mailto:|tel:|#|\/)/i.test(href)) return href || "#";
    const root = (document.body.dataset.siteRoot || ".").replace(/\/$/, "");
    const normalized = href.replace(/^(?:\.\.\/|\.\/)+/, "");
    return root + "/" + normalized;
  }

  function syncTripControls() {
    const keys = new Set(LS.get("tay_trip", []).map((item) => item && item.key).filter(Boolean));
    document.querySelectorAll(".trip-btn[data-key]").forEach((button) => {
      const added = keys.has(button.dataset.key);
      button.classList.toggle("added", added);
      button.textContent = added ? "✓" : "＋";
      button.setAttribute("aria-label", (added ? "从行程移除 " : "加入行程 ") + (button.dataset.name || "城市"));
    });
    document.querySelectorAll(".co-trip[data-key]").forEach((button) => {
      const added = keys.has(button.dataset.key);
      button.classList.toggle("on", added);
      button.textContent = added ? "✓ 已在行程" : "＋ 加入行程";
    });
  }

  function renderTripDock() {
    if (!tripDockList) return;
    const trip = LS.get("tay_trip", []).filter((item) => item && item.key);
    tripDockList.replaceChildren();
    trip.forEach((item, index) => {
      const row = document.createElement("div");
      row.className = "trip-dock-item";
      const link = document.createElement("a");
      link.className = "trip-dock-item-main";
      link.href = rootHref(item.href);
      const name = document.createElement("strong");
      name.textContent = item.name || "未命名城市";
      const summary = document.createElement("span");
      summary.textContent = item.sub || "打开攻略查看行程信息";
      link.append(name, summary);
      const remove = document.createElement("button");
      remove.className = "trip-dock-remove";
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", "从行程移除 " + name.textContent);
      remove.addEventListener("click", () => {
        const next = LS.get("tay_trip", []).filter((entry) => entry && entry.key !== item.key);
        LS.set("tay_trip", next);
      });
      row.append(link, remove);
      row.style.setProperty("--trip-index", String(index + 1));
      tripDockList.appendChild(row);
    });
    if (tripDockCount) {
      tripDockCount.textContent = String(trip.length);
      tripDockCount.setAttribute("aria-label", "行程中有 " + trip.length + " 座城市");
    }
    document.querySelectorAll("[data-trip-count]").forEach((badge) => {
      badge.textContent = String(trip.length);
      badge.hidden = trip.length === 0;
    });
    if (tripDockEmpty) tripDockEmpty.hidden = trip.length > 0;
    if (tripDockClear) tripDockClear.disabled = trip.length === 0;
    syncTripControls();
  }

  function tripDockFocusables() {
    if (!tripDock) return [];
    return Array.from(tripDock.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'))
      .filter((element) => !element.hidden && element.offsetParent !== null);
  }

  function openTripDock() {
    if (!tripDock || !tripDockToggle) return;
    tripDockPreviousFocus = document.activeElement;
    renderTripDock();
    tripDock.hidden = false;
    if (tripDockBackdrop) tripDockBackdrop.hidden = false;
    tripDockToggle.setAttribute("aria-expanded", "true");
    document.body.classList.add("trip-dock-open");
    requestAnimationFrame(() => tripDock.focus());
  }

  function closeTripDock() {
    if (!tripDock || tripDock.hidden) return;
    tripDock.hidden = true;
    if (tripDockBackdrop) tripDockBackdrop.hidden = true;
    if (tripDockToggle) tripDockToggle.setAttribute("aria-expanded", "false");
    document.body.classList.remove("trip-dock-open");
    if (tripDockPreviousFocus && typeof tripDockPreviousFocus.focus === "function") tripDockPreviousFocus.focus();
    tripDockPreviousFocus = null;
  }

  if (tripDockToggle && tripDock) {
    tripDockToggle.addEventListener("click", () => tripDock.hidden ? openTripDock() : closeTripDock());
    document.querySelectorAll("[data-open-trip]").forEach((button) => {
      button.addEventListener("click", () => tripDock.hidden ? openTripDock() : closeTripDock());
    });
    if (tripDockClose) tripDockClose.addEventListener("click", closeTripDock);
    if (tripDockBackdrop) tripDockBackdrop.addEventListener("click", closeTripDock);
    if (tripDockClear) tripDockClear.addEventListener("click", () => {
      const trip = LS.get("tay_trip", []);
      if (!trip.length || !window.confirm("清空当前行程中的全部城市？")) return;
      LS.set("tay_trip", []);
    });
    document.addEventListener("keydown", (event) => {
      if (tripDock.hidden) return;
      if (event.key === "Escape") { event.preventDefault(); closeTripDock(); return; }
      if (event.key !== "Tab") return;
      const focusable = tripDockFocusables();
      if (!focusable.length) { event.preventDefault(); tripDock.focus(); return; }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    window.addEventListener("tay:storage-change", (event) => {
      if (event.detail && event.detail.key === "tay_trip") renderTripDock();
    });
    renderTripDock();
  }

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
    const pauseButton = car.querySelector(".hero-pause");
    if (slides.length <= 1) return;
    let idx = 0, timer = null;
    let userPaused = false;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    function hydrateSlide(n) {
      const slide = slides[(n + slides.length) % slides.length];
      const image = slide && slide.querySelector("img[data-src]");
      if (!image) return;
      image.src = image.dataset.src;
      image.removeAttribute("data-src");
    }
    function motionDisabled() {
      return userPaused || reducedMotion.matches || document.documentElement.getAttribute("data-motion") === "off";
    }
    function syncPauseButton() {
      if (!pauseButton) return;
      const systemPaused = reducedMotion.matches || document.documentElement.getAttribute("data-motion") === "off";
      const paused = userPaused || systemPaused;
      pauseButton.setAttribute("aria-pressed", String(paused));
      pauseButton.textContent = paused ? "▶" : "Ⅱ";
      pauseButton.disabled = systemPaused;
      const label = systemPaused ? "已按减少动态设置关闭自动轮播" : (paused ? "恢复自动轮播" : "暂停自动轮播");
      pauseButton.setAttribute("aria-label", label);
      pauseButton.title = label;
    }
    function go(n) {
      idx = (n + slides.length) % slides.length;
      hydrateSlide(idx);
      hydrateSlide(idx + 1);
      slides.forEach((s, i) => {
        const active = i === idx;
        s.classList.toggle("active", active);
        s.setAttribute("aria-hidden", String(!active));
        if (s.matches("a")) s.tabIndex = active ? 0 : -1;
      });
      dots.forEach((d, i) => {
        d.classList.toggle("active", i === idx);
        if (i === idx) d.setAttribute("aria-current", "true");
        else d.removeAttribute("aria-current");
      });
    }
    function start() {
      stop();
      if (motionDisabled()) return;
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
    if (pauseButton) pauseButton.addEventListener("click", () => {
      userPaused = !userPaused;
      syncPauseButton();
      if (userPaused) stop(); else start();
    });
    // 触控滑动
    let tx = 0;
    car.addEventListener("touchstart", (e) => { tx = e.touches[0].clientX; stop(); }, { passive: true });
    car.addEventListener("touchend", (e) => {
      const dx = e.changedTouches[0].clientX - tx;
      if (Math.abs(dx) > 40) go(idx + (dx < 0 ? 1 : -1));
      start();
    }, { passive: true });
    document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); else start(); });
    const onMotionChange = () => { syncPauseButton(); if (motionDisabled()) stop(); else start(); };
    if (reducedMotion.addEventListener) reducedMotion.addEventListener("change", onMotionChange);
    else if (reducedMotion.addListener) reducedMotion.addListener(onMotionChange);
    go(0);
    syncPauseButton();
    start();
  })();

  // ===== 用户中心 =====
  (function () {
    const tabsWrap = document.getElementById("userTabs");
    if (!tabsWrap) return;
    const tabBtns = Array.from(tabsWrap.querySelectorAll(".user-tab"));
    const panels = Array.from(document.querySelectorAll(".user-panel"));
    function activateUserTab(button, options) {
      if (!button) return;
      const settings = options || {};
      tabBtns.forEach((candidate) => {
        const active = candidate === button;
        candidate.classList.toggle("active", active);
        candidate.setAttribute("aria-selected", String(active));
        candidate.tabIndex = active ? 0 : -1;
      });
      panels.forEach((panel) => { panel.hidden = panel.dataset.panel !== button.dataset.tab; });
      button.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      if (settings.focus) button.focus();
      if (settings.updateHash) {
        const next = new URL(location.href);
        next.hash = "tab=" + encodeURIComponent(button.dataset.tab || "profile");
        history.pushState({ userTab: button.dataset.tab }, "", next);
      }
    }
    function tabFromHash() {
      const rawHash = decodeURIComponent(location.hash.replace(/^#/, ""));
      const key = new URLSearchParams(rawHash).get("tab") || rawHash.replace(/^user-panel-/, "");
      return tabBtns.find((button) => button.dataset.tab === key) || null;
    }
    tabBtns.forEach((button) => {
      button.addEventListener("click", () => activateUserTab(button, { updateHash: true }));
      button.addEventListener("keydown", (event) => {
        const current = tabBtns.indexOf(button);
        let target = -1;
        if (event.key === "ArrowRight") target = (current + 1) % tabBtns.length;
        if (event.key === "ArrowLeft") target = (current - 1 + tabBtns.length) % tabBtns.length;
        if (event.key === "Home") target = 0;
        if (event.key === "End") target = tabBtns.length - 1;
        if (target < 0) return;
        event.preventDefault();
        activateUserTab(tabBtns[target], { focus: true, updateHash: true });
      });
    });
    const initialTab = tabFromHash();
    if (initialTab) activateUserTab(initialTab);
    window.addEventListener("popstate", () => {
      const requested = tabFromHash();
      if (requested) activateUserTab(requested);
    });

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
        ["tay_profile", "tay_settings", "tay_favs", "tay_recent", "tay_search_recent", "tay_trip", "tay_roadtrips", "tay_last_roadtrip", "tay_checklist", "tay_budget", "tay_notes", "tay_city_checks"].forEach((k) => LS.del(k));
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
    function downloadJson(filename, value) {
      const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json;charset=utf-8" });
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(href), 0);
    }
    const dataExport = document.getElementById("dataExport");
    const dataImport = document.getElementById("dataImport");
    const dataTransferStatus = document.getElementById("dataTransferStatus");
    function showTransferStatus(message, isError) {
      if (!dataTransferStatus) return;
      dataTransferStatus.hidden = false;
      dataTransferStatus.textContent = message;
      dataTransferStatus.classList.toggle("error", Boolean(isError));
    }
    if (dataExport) dataExport.addEventListener("click", () => {
      downloadJson("游记地图-本机数据备份.json", LS.exportData());
      showTransferStatus("已导出本机数据备份", false);
    });
    if (dataImport) dataImport.addEventListener("change", () => {
      const file = dataImport.files && dataImport.files[0];
      if (!file) return;
      file.text().then((text) => {
        let payload;
        try { payload = JSON.parse(text); } catch (_) { showTransferStatus("导入失败：JSON 文件无法解析", true); return; }
        if (!LS.importData(payload)) { showTransferStatus("导入失败：备份格式或字段不受支持", true); return; }
        showTransferStatus("已恢复本机数据，页面即将刷新", false);
        setTimeout(() => location.reload(), 450);
      }).catch(() => showTransferStatus("导入失败：无法读取文件", true));
      dataImport.value = "";
    });
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

  // 月份速查：高亮当前月份，并在手机横滑列表中把它滚到可见位置。
  (function highlightCurrentMonth() {
    const month = new Date().getMonth() + 1;
    document.querySelectorAll("[data-month-grid]").forEach((grid) => {
      const card = grid.querySelector('.month-card[data-month="' + month + '"]');
      if (!card) return;
      card.classList.add("is-current");
      card.setAttribute("aria-current", "date");
      if (grid.scrollWidth > grid.clientWidth + 4) grid.scrollLeft = Math.max(0, card.offsetLeft - grid.offsetLeft - 16);
    });
  })();

  // 出发前复核清单：勾选状态按城市保存在本机。
  (function bindCityChecklists() {
    document.querySelectorAll(".check-list[data-checklist]").forEach((list) => {
      const key = list.dataset.checklist;
      const boxes = Array.from(list.querySelectorAll('input[type="checkbox"][data-check-index]'));
      if (!key || !boxes.length) return;
      const progress = document.createElement("p");
      progress.className = "check-progress";
      progress.setAttribute("aria-live", "polite");
      list.after(progress);
      function sync() {
        const done = boxes.filter((box) => box.checked).length;
        progress.textContent = "已完成 " + done + " / " + boxes.length + "（只保存在本机）";
      }
      const saved = LS.get("tay_city_checks", {});
      const checked = new Set(Array.isArray(saved[key]) ? saved[key] : []);
      boxes.forEach((box) => {
        box.checked = checked.has(Number(box.dataset.checkIndex));
        box.addEventListener("change", () => {
          const state = LS.get("tay_city_checks", {});
          state[key] = boxes.filter((item) => item.checked).map((item) => Number(item.dataset.checkIndex));
          if (!state[key].length) delete state[key];
          LS.set("tay_city_checks", state);
          sync();
        });
      });
      sync();
    });
  })();

  // 打印时展开卡片里折叠的详情。
  window.addEventListener("beforeprint", () => {
    document.querySelectorAll("details.card-more").forEach((details) => {
      if (!details.open) { details.dataset.printOpened = "true"; details.open = true; }
    });
  });
  window.addEventListener("afterprint", () => {
    document.querySelectorAll('details.card-more[data-print-opened="true"]').forEach((details) => {
      details.open = false;
      delete details.dataset.printOpened;
    });
  });

  // 图片灯箱：保留触发元素焦点，支持键盘打开、关闭与焦点返回。
  const zoomImages = Array.from(document.querySelectorAll(".item-thumb, .media-card img"));
  if (zoomImages.length) {
    const lb = document.createElement("div");
    lb.className = "lightbox";
    lb.setAttribute("role", "dialog");
    lb.setAttribute("aria-modal", "true");
    lb.setAttribute("aria-label", "旅行图片预览");
    const lbImg = document.createElement("img");
    lbImg.alt = "";
    const closeButton = document.createElement("button");
    closeButton.className = "lightbox-close";
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", "关闭图片预览");
    closeButton.textContent = "✕";
    lb.append(lbImg, closeButton);
    document.body.appendChild(lb);
    let lightboxTrigger = null;

    function closeLightbox() {
      if (!lb.classList.contains("open")) return;
      lb.classList.remove("open");
      document.documentElement.classList.remove("lightbox-active");
      lbImg.removeAttribute("src");
      if (lightboxTrigger) lightboxTrigger.focus();
    }

    function openLightbox(img) {
      lightboxTrigger = img;
      lbImg.src = img.currentSrc || img.src;
      lbImg.alt = img.alt || "旅行图片大图";
      lb.classList.add("open");
      document.documentElement.classList.add("lightbox-active");
      closeButton.focus();
    }

    closeButton.addEventListener("click", (event) => {
      event.stopPropagation();
      closeLightbox();
    });
    lb.addEventListener("click", (event) => {
      if (event.target === lb) closeLightbox();
    });
    document.addEventListener("keydown", (event) => {
      if (!lb.classList.contains("open")) return;
      if (event.key === "Escape") closeLightbox();
      if (event.key === "Tab") {
        event.preventDefault();
        closeButton.focus();
      }
    });
    zoomImages.forEach((img) => {
      img.style.cursor = "zoom-in";
      img.setAttribute("role", "button");
      img.tabIndex = 0;
      img.setAttribute("aria-label", "查看大图：" + (img.alt || "旅行图片"));
      img.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        openLightbox(img);
      });
      img.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        openLightbox(img);
      });
    });
  }

  // PWA Service Worker（仅在 http/https 下注册；file:// 直接打开会自动跳过）
  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    const root = document.body.dataset.siteRoot || ".";
    window.addEventListener("load", () => navigator.serviceWorker.register(root + "/sw.js").catch(() => {}));
  }
})();
