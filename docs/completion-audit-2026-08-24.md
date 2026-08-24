# 2026-08-24 发布验收

验收范围：第 36—42 轮应用化、性能、移动端、PWA、发布链与图片可复现性改造。产品代码基线为 `1ea8b23`，本文件作为后续发布记录提交。

| 要求 | 关键文件 | 证据 | 验证 | 状态 |
| --- | --- | --- | --- | --- |
| Node + Python 源码优先、静态运行 | `package.json`、`frontend/`、`tools/build_travel_html.py` | Vite/TypeScript 构建后由 Python 生成可静态部署页面 | Windows 与全新 Ubuntu 24.04 均执行 `npm run check` | 已验收 |
| 干净 Pages 构建 | `.github/workflows/pages.yml`、`requirements-build.txt`、`tools/stage_pages.py` | Node 24、Python 3.12、Pillow 12.2.0 均显式安装/锁定，发布目录使用白名单 | GitHub Actions `32714435655` 的 build/deploy 全部成功 | 已验收 |
| 图片输入可复现 | `assets/photo-cache.json`、`tools/test_priority_city_images.py` | 210 条已发布城市照片指向 Git 跟踪封面；清理逻辑保留审核通过的版本化衍生图 | 相关契约先红后绿；全新 Linux 首次构建后实景目录差异为 0 | 已验收 |
| 首页性能与按需搜索 | `frontend/src/site-search.ts`、`tools/test_performance_budget.py` | 首页仅精选 24 城；搜索索引在首次查询后加载；轮播初始只水合 2 张 | 公开首页约 277 KB HTML；16 组首屏在交互前均未请求搜索索引 | 已验收 |
| 桌面/手机核心流程 | `assets/travel.js`、`user.html`、`roadtrip.html` | 搜索、下拉、收藏、行程面板、用户标签、三步路书均有真实行为 | 1920、1366、390、360 四视口 × 4 页面共 16 组线上 Playwright 操作通过 | 已验收 |
| 可访问性与响应式 | `assets/travel.css`、`tools/browser_audit.py` | ARIA Tabs、键盘 Home/End、焦点回归、44px 触控目标、安全区与减少动态 | 线上审计无横向溢出、重复 ID、无名称按钮、空链接或无尺寸图片；截图人工复核通过 | 已验收 |
| PWA 与离线边界 | `sw.js`、`tools/offline_audit.py` | 已访问页精确缓存；未缓存路由显示 503 离线说明；索引按需运行时缓存 | 真实关闭自持服务器后，青岛离线 200、离线搜索恢复、未缓存澳门路由 503 | 已验收 |
| 公开发布 | `.github/workflows/pages.yml`、`dist/` | 自定义 Pages 与 GitHub 既有 Pages 流程均完成 | 公开地址返回 200，资源版本 `df7da9910d`；线上 16 组回归无控制台/页面/请求/HTTP 错误 | 已验收 |

## 验证摘要

- `npm run check`：13 项 Node 测试、135 项 Python 测试通过；458 个本地 HTML 中 222 个城市页与 222 个 Markdown 对齐，缺链、缺锚点、重复 ID、空文件、缺失图片替代文本均为 0。
- `npm run stage`：生成 229 个发布 HTML；未包含本机地图配置。
- Ubuntu 干净构建：Node 24.19.0、Python 3.12、Pillow 12.2.0 下同一检查通过；发布图片未被插画替换。
- 线上审计报告：`D:\.AI\codex_tmp\audits\travel-ayuan\public-after-deploy-1ea8b23\report.json`。
- 真实离线报告：`D:\.AI\codex_tmp\audits\travel-ayuan\round-5-offline-real\report.json`。

## 真实限制与交接

- 收藏、行程、清单、预算和笔记仍是浏览器本机数据；没有账号后端时不能自动跨设备同步，需依赖导入、导出与分享。
- 未配置高德 JS Key 与安全密钥时，路书使用明确标注的离线估算，不伪装成实时路况或真实导航；正式启用地图还需配置域名白名单。
- 222 城长尾事实、易变票价/开放时间和全部外链仍需按来源与核验日期持续维护，不能把构建通过等同于内容永久正确。
- 首次离线且从未搜索时不预缓存完整搜索索引，这是降低首次安装成本的有意取舍；联网搜索一次后可由运行时缓存继续使用。
