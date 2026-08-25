# 2026-08-26 省份导航与最近活动验收

验收范围：第 44 轮省份直达导航、最近搜索/浏览、移动端导航修复、父目录项目说明和本轮生成结果。上一稳定提交为 `edfd921`。

| 需求 | 文件 | 证据 | 验证结果 | 状态 |
| --- | --- | --- | --- | --- |
| 用省份取代“全国目的地 + 热门城市” | `tools/build_travel_html.py`、`frontend/src/site-search.ts`、生成页面 | 直辖市排首位，随后为省份与港澳；每组按需载入城市 | 四视口真实展开直辖市与山东；旧文案和热门条均不存在 | 已验收 |
| 保留条件优先的目的地玩法 | `tools/build_travel_html.py`、`destinations.html` | 各省菜单提供“条件筛选”，既有目的地页继续支持组合条件 | 生成契约检查省份参数；浏览器确认入口可见且不遮挡城市 | 已验收 |
| 最近搜索与最近浏览 | `frontend/src/site-search.ts`、`tools/build_travel_html.py` | 空搜索框展示两组记录；支持恢复、返回城市和清空 | 四视口操作恢复“青岛”、返回青岛链接、Esc 关闭与清空键值通过 | 已验收 |
| 本地数据治理 | `tools/build_travel_html.py`、`tools/test_product_contract.py` | `tay_search_recent` 纳入已知数组键与全量清理 | 产品契约与 137 项 Python 测试通过 | 已验收 |
| 桌面与手机响应式 | `assets/travel.css`、`docs/round44-*.png` | 桌面全宽菜单；手机双列、内部滚动，展开时隐藏固定底栏/浮钮 | 1920、1366、390、360 均无横向溢出；截图人工复核通过 | 已验收 |
| 可访问性与错误状态 | `frontend/src/site-search.ts`、生成页面 | 当前城市使用 `aria-current`，列表有 `aria-live`/`aria-busy`，加载失败有状态文本 | 8 组浏览器检查无控制台/页面/网络错误、坏图或重复 ID | 已验收 |
| 父目录项目说明 | `D:\2Life\1Travel\README.md` | 含在线链接、仓库、本地入口、架构、命令、目录、隐私和发布说明 | UTF-8 回读并核对路径/命令；该文件位于产品 Git 仓库外 | 已验收 |
| 构建与发布包 | `package.json`、`tools/stage_pages.py`、生成站点 | Node/Vite + Python 全站生成，静态 PWA 运行 | `npm run check` 与 `npm run stage` 的最终结果见本轮验证摘要 | 已验收 |

## 验证摘要

- `npm run check`：16 项 Node 测试、137 项 Python 测试通过；458 个 HTML、222 个城市页、222 个城市 Markdown 对齐；缺链、缺锚点、重复 ID、空文件和缺失图片 `alt` 均为 0。
- Playwright：1920×1080、1366×768、390×844、360×800 × 首页/青岛，共 8 组全部通过。
- 浏览器错误：控制台、页面脚本、失败请求、HTTP 4xx/5xx、横向溢出、坏图、重复 ID 均为 0。
- 证据：`docs/round44-browser-report.json` 与四张 `docs/round44-*.png`。

## 未纳入本轮的真实限制

- 最近记录仍是浏览器本地数据，不是账号云同步。
- 省份菜单第一次打开需按需读取搜索索引；从未加载过索引的首次离线会显示失败状态。
- 本轮不重新核验 222 城的全部动态票价、开放时间或外链；这些仍按来源和复核日期持续维护。
- 本地验收不能替代本轮提交后的 GitHub Pages 部署与公开 URL 复核；在远端工作流和线上浏览器检查完成前，公开发布状态应标记为未验证。
