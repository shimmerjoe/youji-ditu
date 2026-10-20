# 2026-10-20 云端迁移与根目录整理

## 范围

仓库 `shimmerjoe/youji-ditu` 的根目录对应本机 `D:/2Life/1Travel/Travel_ayuan/` 内部内容。用户已自行删除“幕布备份”并把外层文件移入项目，本次不重建该备份。

## 目录调整

- 网站 HTML、PWA/SEO、依赖清单、构建配置、README 和核心内容源 `记录.md` 留在根目录，保持页面网址。
- Windows 批处理归入 `scripts/windows/`，向上两级定位根目录；重复的打开入口合并，通过 HTTP 预览。
- 运行、移动端、来源手册归入 `docs/guides/`；体检报告归入 `docs/reports/`，生成器、测试及报告内链接同步更新。
- 聊天和旧补抓日志归入 `docs/history/`；预览图归入 `docs/screenshots/`。
- 原始图片、图片候选资料、安卓模板、辅助文档和脚本纳入源码；依赖、缓存、浏览器产物及本机配置继续忽略。
- 移入的外层跳转页指向不存在的嵌套目录，通过生成链路恢复真实首页；README 整合更新。

## 完整副本与恢复

整理前对整个项目（隐藏文件、Git 历史、依赖和本机构建产物也包括在内）创建 ZIP 和逐文件 SHA-256 清单，保存目标为本仓库私有 Release：

<https://github.com/shimmerjoe/youji-ditu/releases/tag/local-migration-2026-10-20>

归档文件为 `Travel_ayuan-before-organization.zip`，清单为 `original-manifest.json`。该快照保存整理前状态；日常恢复应克隆主分支，恢复完整旧状态才解压归档。

交付以实际远端提交、Release 附件与内容校验为准。确认源码推送、归档完整且无遗漏后，才删除用户指定的本地目录。

## 实际验证结果

- 网站源码与目录整理提交：`9f2007b02beb0ef1a1f3352219b3a64eb3a64971`。GitHub API 返回的提交和完整文件树与本地一致。
- `npm run check` 通过：TypeScript 检查、16 项 Node 测试、138 项 Python 测试通过，222 个城市 Markdown 对应 222 个城市页面，缺失站内链接、缺失锚点、重复 ID 和缺少 alt 均为 0。
- `npm run stage` 成功生成 229 个部署 HTML；首页、目的地、青岛、用户中心、路书、应用脚本、manifest 和 Service Worker 的本地 HTTP 检查均返回 200。
- 整理前完整快照包含 4,382 个文件、1,121,247,068 字节原始数据；ZIP 为 1,010,302,288 字节。本地解压读取全部归档条目并逐文件比对 SHA-256 通过。
- Release 已发布，两份附件状态为 uploaded；GitHub 服务器计算的 ZIP 与清单 SHA-256 均与本地一致。ZIP SHA-256：`df652b38ae296791a23ad7b8d5d6ac7ea6825fd4bbcacfef3847a3cca150b57c`。
- 回下载尝试停留在大文件连接阶段，未完成 ZIP 回下载；已停止该下载并改用上述服务端内容校验，不将其表述为回下载成功。
- 删除前还检查源码工作树干净，两个非缓存忽略文件与原始归档清单一致。依赖、dist、浏览器产物与 Python 缓存为可重建数据；整理前版本已在完整快照中。

## 站点状态边界

本次核对时仓库为私有，GitHub Pages API 返回 404。源码上传不代表该站点已经上线；保留既有工作流，不擅自更改仓库可见性。

推送触发的 Actions 运行 `39423346050` 已完成依赖安装、构建、测试和静态产物整理，随后在 `actions/configure-pages@v5` 因 Pages 站点不存在返回 404，部署步骤跳过。这是尚未启用 Pages 的托管状态，不是源码上传失败。
