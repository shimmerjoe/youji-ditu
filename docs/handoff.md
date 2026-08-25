# 项目交接

更新时间：2026-08-26。

## 当前状态

- 第 44 轮已完成省份直达导航、直辖市首组、按需城市菜单、最近搜索/浏览及移动端遮挡修复。
- 源实现位于 `frontend/src/site-search.ts`、`frontend/src/app.ts` 与 `tools/build_travel_html.py`；不要批量手改 222 个生成城市页。
- 本轮本地基线验证见 `docs/completion-audit-2026-08-26-navigation-history.md`；浏览器证据见 `docs/round44-browser-report.json` 和同名前缀截图。
- 父目录说明在 `D:\2Life\1Travel\README.md`，它位于产品 Git 仓库外，不会随 GitHub Pages 发布。

## 回滚入口

- 上一稳定提交：`edfd921`（第 43 轮公开发布验收）。
- 回滚时应通过新的反向提交恢复本轮源文件，并重新运行生成器；不要只恢复生成 HTML，也不要使用会覆盖用户工作的破坏性命令。

## 待完成/待外部验证

- 提交并推送本轮产品仓库改动，等待 Pages 工作流完成。
- 在公开地址核对资源版本，并至少复测桌面与手机的直辖市/山东菜单和最近活动。
- 动态旅行事实、长尾外链与图片语义仍按既有内容治理流程逐城维护。

## 下一步

1. 运行 `npm run check` 与 `npm run stage`，审查 `git diff` 和暂存范围。
2. 选择性提交本轮源文件、测试、生成结果和验收证据。
3. 推送后等待 GitHub Pages，再对 <https://shimmerjoe.github.io/youji-ditu/> 做线上回归。
