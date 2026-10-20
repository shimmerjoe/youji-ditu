# 本地迁移备份（2026-10-20）

这里记录项目从本机 `D:\2Life\1Travel\Travel_ayuan` 迁移到云端之前的完整快照。原本地目录已经删除，不要再依赖那个路径。

## 文件说明

| 文件 | 位置 | 说明 |
| --- | --- | --- |
| `original-manifest.json` | 本文件夹 | 快照中全部 4,382 个文件的路径、大小和 SHA-256，共 1,121,247,068 字节 |
| `Travel_ayuan-before-organization.zip` | 原 Release `local-migration-2026-10-20`（已决定删除） | 完整压缩包，1,010,302,288 字节，SHA-256 `df652b38ae296791a23ad7b8d5d6ac7ea6825fd4bbcacfef3847a3cca150b57c` |

压缩包有 1.01 GB，超过 GitHub 仓库单个文件 100 MB 的上限，无法放进这个文件夹。2026-10-20，仓库所有者决定只保留本文件夹里的清单和说明，并删除这个 Release。Release 删除后压缩包将无法再下载，下文列出的“仓库中没有”的内容也会随之永久丢失。标签 `local-migration-2026-10-20` 仍然指向整理前的提交 `9f2007b`。

## 快照内容构成

| 顶层目录或文件 | 文件数 | 大小（MB） |
| --- | ---: | ---: |
| `.git` | 328 | 306.1 |
| `artifacts` | 298 | 284.2 |
| `dist` | 1212 | 213.1 |
| `assets` | 983 | 188.8 |
| `node_modules` | 941 | 68.2 |
| `docs` | 70 | 31.7 |
| `cities` | 222 | 22.3 |
| `城市` | 222 | 2.8 |
| `tools` | 62 | 1.5 |
| 其他根目录文件 | 若干 | < 3 |

## 与仓库的比对结果（2026-10-20）

我下载了 `original-manifest.json`，把清单中每个文件的 SHA-256 与仓库所有提交中的文件逐一比对：

- **已在仓库中**：图片（`assets/`）、文档截图和大部分源码，哈希值完全一致。
- **内容相同、换行符不同**：222 篇城市 Markdown、`记录.md` 以及生成的 HTML。备份里是 Windows 换行（CRLF），仓库里统一为 LF。其中 217 篇换算成 CRLF 后哈希值逐字节一致。另外 8 个文件（`tools/build_travel_html.py`、`tools/city-page-meta.json`，以及滁州、青岛、南昌、金华、万宁、三亚的 Markdown）大小只相差几百字节，推断是混合换行；这一点没有解压压缩包逐行核验。
- **仓库中没有**：
  - `artifacts/browser-audit/`：以前的浏览器审计截图（约 284 MB）。
  - `node_modules/`、`dist/`、`tools/__pycache__/`：可以用 `npm ci`、`npm run stage` 重新生成。
  - `.git/`：本机 Git 历史，已经推送到远端的提交在仓库里都能看到。
  - `assets/roadtrip-config.js`：本机地图密钥配置，故意没有进入仓库。

## 如何使用

- 日常开发：直接克隆仓库，不需要这个备份。
- 确认某个旧文件：在 `original-manifest.json` 里查它的路径和 SHA-256。
- 查看整理前的源码：`git checkout local-migration-2026-10-20`（即提交 `9f2007b`）。
