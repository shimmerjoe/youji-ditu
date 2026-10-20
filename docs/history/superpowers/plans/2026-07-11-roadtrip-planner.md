# 自驾路书生成器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为“游记地图”增加不含广告和交易入口的完整自驾路书生成器，支持路线、分天、预算、风险、保存、打印、Markdown 导出与高德地图增强。

**Architecture:** 使用独立的纯 JavaScript 核心模块处理输入校验、分天、预算、风险和导出，浏览器应用模块只负责 DOM、localStorage 与高德 JS API。Python 生成器继续作为唯一构建入口，负责生成 `roadtrip.html`、城市攻略数据、资源文件、导航和 PWA 资产；没有地图 Key 时保留离线规划能力。

**Tech Stack:** Python 3 静态站点生成器、原生 HTML/CSS/JavaScript、Node.js `node:test`、高德地图 JS API 2.0（可选运行时增强）、localStorage、PWA。

---

### Task 1: 核心算法契约

**Files:**
- Create: `tools/test_roadtrip_core.js`
- Create: `tools/roadtrip-core.js`

- [ ] 编写失败测试，覆盖输入校验、单程/往返里程、每日分段、燃油/电动车预算、票价预算、长距离驾驶风险和 Markdown 导出。
- [ ] 运行 `node --test tools/test_roadtrip_core.js`，确认因核心模块不存在而失败。
- [ ] 实现无 DOM 依赖的纯函数并导出 CommonJS/browser UMD 接口。
- [ ] 再次运行测试，确认全部通过。

### Task 2: 页面生成与数据契约

**Files:**
- Create: `tools/test_roadtrip_build.py`
- Modify: `tools/build_travel_html.py`
- Generate: `roadtrip.html`
- Generate: `assets/roadtrip-data.js`
- Generate: `assets/roadtrip-config.js`

- [ ] 编写失败测试，要求生成器包含自驾页面、非交易声明、地图容器、表单、结果区、脚本顺序及城市数据字段。
- [ ] 运行 `python -X utf8 -m unittest tools.test_roadtrip_build -v`，确认失败原因是页面和构建函数尚不存在。
- [ ] 在生成器中新增自驾页面构建函数，并从现有城市 Markdown 提取省份、城市、亮点、美食、路线、参考票价、来源及更新时间。
- [ ] 生成空 Key 配置文件且后续构建不覆盖用户填写的配置。
- [ ] 重新生成网站并运行构建测试。

### Task 3: 自驾页面和交互

**Files:**
- Create: `tools/roadtrip-app.js`
- Create: `tools/roadtrip.css`
- Modify: `tools/build_travel_html.py`

- [ ] 增加起点、终点、日期、天数、行程类型、每日驾驶上限、路线策略、旅行主题、车型、能耗和人数输入。
- [ ] 默认使用离线估算模式，根据输入和本站城市资料生成逐日路线、预算区间、风险提示、来源说明。
- [ ] 增加地图状态、加载状态、输入错误和无结果状态。
- [ ] 实现保存路书、恢复最近方案、清空、打印和 Markdown 下载。
- [ ] 在桌面使用左右工作台布局，手机端改成单列且结果优先可读。

### Task 4: 高德地图增强

**Files:**
- Modify: `tools/roadtrip-app.js`
- Modify: `README.md`

- [ ] 仅在配置 Key 时动态加载高德 JS API 2.0 和安全配置。
- [ ] 使用地点关键词计算驾车路线并在地图上绘制，读取真实距离、时间、收费与步骤。
- [ ] 根据路线累计距离分割每日节点，使用逆地理编码识别建议住宿城市，并匹配本站城市攻略。
- [ ] 支持常规、少收费、不走高速和高速优先策略；地图失败时自动退回离线估算并明确标注。
- [ ] 文档写明申请 Key、填写配置、限制来源以及不应暴露 Web 服务私钥。

### Task 5: 全站集成

**Files:**
- Modify: `tools/build_travel_html.py`
- Generate: `index.html`
- Generate: `user.html`
- Generate: `manifest.webmanifest`
- Generate: `sw.js`

- [ ] 顶部导航新增“自驾路书”，首页实用工具区增加紧凑入口。
- [ ] 用户中心增加“已保存路书”，读取 `tay_roadtrips` 并支持打开和删除。
- [ ] PWA 清单增加自驾快捷方式，Service Worker 更新缓存版本。
- [ ] 所有价格统一使用“参考价格/预算”措辞，保留来源和更新时间，不出现购买、下单、支付、优惠券或广告入口。

### Task 6: 验证

**Files:**
- Modify: `tools/validate_travel_site.py`（仅在验证器需要识别新页面时）

- [ ] 运行 Node 核心测试、Python 构建测试、现有 UI 回归测试和 Python 编译检查。
- [ ] 重新生成全部页面并运行 `tools/validate_travel_site.py`，确认本地链接和锚点均无缺失。
- [ ] 启动本地服务器，在 1920×1080 和手机视口测试首页入口、自驾表单、离线生成、保存、恢复、导出和用户中心。
- [ ] 检查控制台错误、布局溢出、按钮文字、地图无 Key 状态和 PWA 注册。
