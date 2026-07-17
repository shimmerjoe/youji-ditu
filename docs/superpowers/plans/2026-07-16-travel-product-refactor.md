# 游记地图旅游产品全面重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 222 城静态攻略站持续重构为可一键生成、内容可追溯、桌面与手机均易用、且不含广告和交易入口的中国旅游攻略产品。

**Architecture:** 继续以 `城市/*.md`、`记录.md`、`tools/city-page-meta.json` 和 `tools/roadtrip-*.{js,css}` 为源文件，由 `tools/build_travel_html.py` 统一生成首页、城市页、用户中心、路书、搜索索引和 PWA 资源。交互数据全部使用浏览器 `localStorage`，公共视觉和行为从生成器输出，避免逐页手改 222 个 HTML；新增 `tools/browser_audit.py` 作为四视口真实浏览器回归入口。

**Tech Stack:** Python 3、Pillow、原生 HTML/CSS/JavaScript、Node.js `node:test`、Python `unittest`、Playwright Chromium、localStorage、Web App Manifest、Service Worker。

---

### Task 1: 建立可重复的浏览器与内容质量基线

**Files:**
- Create: `tools/browser_audit.py`
- Create: `tools/test_product_contract.py`
- Create: `docs/iteration-log.md`

- [ ] **Step 1: 写失败契约测试**

  在 `tools/test_product_contract.py` 中断言首页具备地区、季节、天数、主题、交通五类筛选；城市页具备价格核验元数据、上下文外链和紧凑来源区；用户中心具备收藏、浏览、行程、路书、清单、预算、笔记七类真实数据面板。先运行 `python -X utf8 -m unittest tools.test_product_contract -v`，预期至少有一项因当前产品契约缺失而失败。

- [ ] **Step 2: 建立浏览器审计器**

  使用 Playwright Chromium 访问 `http://127.0.0.1:8765/`，在 `1920x1080`、`1366x768`、`390x844`、`360x800` 保存首页、青岛城市页、用户中心和自驾路书截图；收集 `console`、`pageerror`、失败请求、横向溢出、图片自然尺寸、空链接与关键交互结果，写入 `artifacts/browser-audit/report.json`。

- [ ] **Step 3: 记录基线**

  将现有 46 项 Python 测试、8 项 Node 测试、225 个 HTML 校验结果和浏览器发现写入 `docs/iteration-log.md`，每轮保留问题、修复、重建、浏览器结果和后续项。

### Task 2: 第一轮 - 结构、导航、生成链路和联网入口

**Files:**
- Modify: `tools/build_travel_html.py`
- Modify: `tools/test_city_context_links.py`
- Modify: `tools/test_ui_regressions.py`
- Generate: `index.html`
- Generate: `cities/*.html`
- Generate: `assets/travel.css`
- Generate: `assets/travel.js`
- Generate: `assets/search-index.js`

- [ ] **Step 1: 先补失败测试**

  增加首页一级导航顺序、单一目的地菜单、城市首屏正文距离、外链 `target="_blank" rel="noopener noreferrer"`、图标/tooltip/可访问名称和城市底部来源区的契约断言；运行对应 unittest 并确认新增断言先失败。

- [ ] **Step 2: 收敛信息架构**

  调整 `site_header_html()`、`nav_html()`、`shell_page_html()`、`page_html()` 和导航 JS，使首页、目的地、主题玩法、城市攻略、自驾路书、实用工具、用户中心层级一致；城市页不再出现横向联网核验面板，只在景点条目提供相关官网、预约、地图和少量可靠补充链接。

- [ ] **Step 3: 重建与浏览器复核**

  运行 `python -X utf8 tools/build_travel_html.py`、全量测试、站点校验和浏览器审计；检查首页、青岛景点区、目的地下拉、搜索及四视口溢出，将结果写入迭代日志。

### Task 3: 第二轮 - 视觉系统、真实图片和交互状态

**Files:**
- Modify: `tools/build_travel_html.py`
- Modify: `tools/test_ui_regressions.py`
- Modify: `tools/test_priority_city_images.py`
- Modify: `assets/photo-cache.json` when verified local image metadata changes
- Add or replace: `assets/images/*` and `assets/photos/<city>/*` only with traceable source metadata
- Generate: `assets/travel.css`
- Generate: `assets/travel.js`
- Generate: generated HTML and PWA assets

- [ ] **Step 1: 先补失败视觉契约**

  测试语义色 token、统一半径/间距、稳定图片宽高、懒加载、焦点可见、`prefers-reduced-motion`、图标按钮 tooltip、移动端无横向溢出与紧凑首屏。

- [ ] **Step 2: 实现编辑式旅行手册视觉方向**

  使用清爽纸白底、墨色正文、朱红品牌、湖绿交通、靛蓝文化、金色预算和珊瑚提醒；内容主体保持连续版式，只为城市/景点重复项、工具和弹窗使用必要卡片。使用现有本地图标系统或本地 Lucide sprite，统一 hover、active、focus、disabled、loading、empty 和 error 状态。

- [ ] **Step 3: 图片审计与重建**

  保留有明确 Wikimedia Commons/官方来源记录的本地实景图，替换重点城市错误、重复或严重裁切图片；生成固定尺寸与 `alt`，运行图片测试、站点生成和四视口截图，人工检查首屏、相册、景点列表和暗色模式。

### Task 4: 第三轮 - 城市内容、价格核验和来源上下文

**Files:**
- Modify: `城市/山东_青岛.md`
- Modify: `城市/陕西_西安.md`
- Modify: `城市/云南_腾冲.md`
- Modify: `城市/安徽_滁州.md`
- Modify: `城市/浙江_金华.md`
- Modify: additional `城市/*.md` selected by coverage audit
- Modify: `tools/city-page-meta.json`
- Modify: `tools/build_travel_html.py`
- Modify: `tools/test_priority_city_content.py`
- Modify: `tools/test_qingdao_content.py`
- Modify: `tools/test_product_contract.py`
- Generate: affected city HTML, search index, roadtrip data and content audit

- [ ] **Step 1: 先补失败内容测试**

  断言重点城市包含概览、季节、天数、交通、景点、美食、路线、预算、住宿、避坑、预约、相册和来源；动态信息同时包含“参考价格/开放信息、核验日期、来源、出行前复核”措辞，且不伪造固定价格和开放时间。

- [ ] **Step 2: 联网核验并深化优先城市**

  以官方文旅、景区/博物馆官网、交通部门为一手来源，可靠攻略平台只作补充；把链接放到对应景点条目，城市底部仅保留紧凑资料来源。根据内容矩阵优先修复空泛、重复和来源不足的城市，记录核验日期与仍需人工复核项。

- [ ] **Step 3: 重建与抽查**

  重建后运行内容测试和断链校验，浏览器抽查青岛、西安、腾冲、滁州、金华以及新增城市；验证搜索命中、景点锚点、上下文外链和来源区。

### Task 5: 第四轮 - 用户中心、自驾路书和本地数据工具

**Files:**
- Modify: `tools/roadtrip-core.js`
- Modify: `tools/roadtrip-app.js`
- Modify: `tools/roadtrip.css`
- Modify: `tools/build_travel_html.py`
- Modify: `tools/test_roadtrip_core.js`
- Modify: `tools/test_roadtrip_build.py`
- Modify: `tools/test_user_tools.py`
- Modify: `tools/test_product_contract.py`
- Generate: `roadtrip.html`
- Generate: `user.html`
- Generate: `assets/roadtrip-*.js`
- Generate: `assets/roadtrip.css`

- [ ] **Step 1: 先补失败行为测试**

  Node 测试覆盖车型、路线偏好、每日驾驶上限、预算、往返、补能与风险；Python 契约覆盖收藏、最近浏览、保存行程、路书、清单、预算、笔记、城市对比、打印、Markdown 导出、分享和本地恢复。运行测试并确认新断言先失败。

- [ ] **Step 2: 实现可用功能**

  统一 `tay_*` localStorage 数据契约；所有按钮具备真实行为、状态反馈和空态。自驾无地图 Key 时明确为离线估算，有 Key 时增强为真实路网；不加入购买、支付、优惠券、广告或商业导流。

- [ ] **Step 3: 浏览器完整操作**

  用 Playwright 执行搜索/筛选、收藏城市、加入行程、比较、保存路书、清单勾选、预算记录、笔记保存、Markdown 导出和刷新恢复；在桌面与手机视口检查操作反馈与数据一致性。

### Task 6: 第五轮 - 可访问性、性能、PWA、断链和一致性

**Files:**
- Modify: `tools/build_travel_html.py`
- Modify: `tools/validate_travel_site.py`
- Modify: `tools/test_pwa_cache.py`
- Modify: `tools/test_ui_regressions.py`
- Modify: `tools/browser_audit.py`
- Generate: `manifest.webmanifest`
- Generate: `sw.js`
- Generate: all site outputs

- [ ] **Step 1: 先补失败质量门禁**

  增加重复 ID、缺 alt、空按钮、无名称图标按钮、错误外链属性、缺图片尺寸、横向溢出、控制台错误、失败请求、键盘焦点、manifest 图标/快捷方式和 Service Worker 更新策略检测。

- [ ] **Step 2: 修复质量问题**

  优化首屏与图片加载、移动导航、键盘和屏幕阅读器语义、颜色对比、缩减动画、打印样式、缓存版本和离线导航；不通过隐藏错误或移除功能规避测试。

- [ ] **Step 3: 全量重建和四视口验收**

  运行生成、46+ Python 测试、8+ Node 测试、站点校验和四视口浏览器审计；逐张检查首页、城市、用户中心和路书截图，并把未通过项带入第六轮。

### Task 7: 后续迭代、交付和长期维护

**Files:**
- Modify: `docs/iteration-log.md`
- Modify: `README.md`
- Modify: `内容与图片体检.md`
- Modify: `资料来源与更新规则.md`
- Generate: final site outputs and browser artifacts

- [ ] **Step 1: 处理全部中高优先级残留**

  对第五轮残留逐项写失败测试或浏览器复现，修改源文件、重建并复测，直到没有中高优先级问题；低优先级人工复核信息必须在文档中列明。

- [ ] **Step 2: 最终证据链**

  新开本地服务完成最后一次全量命令验证，保存四视口关键截图和 JSON 报告；确认 Git 状态中的既有修改仍被保留，没有使用重置或覆盖命令。

- [ ] **Step 3: 维护说明**

  README 记录源/生成边界、一键构建、测试、预览、图片授权、来源核验、PWA 更新与 localStorage 数据说明；交付本地地址、关键文件、每轮变更、来源、测试结果、截图及仍需人工复核清单。
