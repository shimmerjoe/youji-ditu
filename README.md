# 游记地图 · 旅游攻略网页

这是一个运行期纯静态、构建期由 Node/Vite/TypeScript 与 Python 共同生成的旅游攻略 PWA。源内容在 `城市\*.md` 和 `记录.md`；Vite 构建渐进增强层，`tools\build_travel_html.py` 统一生成页面、索引、PWA 与公共资源，因此无需 Python 后端也能部署到 GitHub Pages。

## 常用命令

```powershell
npm ci
npm run check
npm run stage
npm run preview
```

`npm run check` 会依次完成 Vite 构建、Python 全站生成、TypeScript 检查、Node/Python 测试和站内链接验证；`npm run stage` 只把公开运行文件复制到 `dist\`。可另开终端执行真实断网审计：

```powershell
python -X utf8 tools\offline_audit.py --self-serve --output D:\.AI\codex_tmp\audits\travel-ayuan\offline
```

## 维护方式

- 修改攻略正文：编辑 `城市\*.md`。
- 新增城市：新增城市 Markdown，必要时补 `tools\city-page-meta.json`。
- 补充图片：优先放到 `assets\photos\城市slug\`，重新生成后进入页面相册和审计。
- 图片审核：授权合规与内容适配是两道独立门槛；不合格来源记录在 `assets\photo-editorial-decisions.json`，不要只删除本地文件。
- 复核资料：查看城市页“联网核验入口”，再把确认后的链接写进“来源参考”。
- 查看薄弱项：打开 `内容与图片体检.md`。

### 定向补图

自动搜索只刷新指定城市，避免一次抓取覆盖全部缓存：

```powershell
$env:TRAVEL_FETCH_COMMONS = "1"
$env:TRAVEL_FETCH_CITY_KEYS = "beijing,tianjin"
python -X utf8 tools\build_travel_html.py
Remove-Item Env:TRAVEL_FETCH_COMMONS, Env:TRAVEL_FETCH_CITY_KEYS
```

如果已在 Wikimedia Commons 人工选定准确文件，先无参数 `--apply` 预检元数据，再确认写入：

```powershell
python -X utf8 tools\import_commons_city_photo.py --city beijing --source "https://commons.wikimedia.org/wiki/File:Example.jpg"
python -X utf8 tools\import_commons_city_photo.py --city beijing --source "https://commons.wikimedia.org/wiki/File:Example.jpg" --apply
```

导入器会校验 Commons 文件页、JPEG 尺寸、横向比例、许可证和作者，但不能替代肉眼语义审核；导入后仍须重建站点并检查桌面/手机裁切与 `内容与图片体检.md`。

## 数据、离线与分享

- 收藏、浏览记录、行程、清单、预算和笔记只保存在当前浏览器；版本化适配器支持 JSON 备份、导入和异常值清理。
- 自驾路书没有地图密钥也能离线估算；“分享链接”携带路书快照，不上传服务器，链接请只发给可信对象。
- Service Worker 首次联网缓存 App Shell；未缓存页面断网时会显示明确的离线说明，不伪装成实时地图、天气或票价服务。
- 约 222 城的搜索索引在用户首次输入搜索词时才按需加载并缓存，不阻塞每次首屏；离线且从未加载索引时会给出失败说明和恢复建议。

## 内容研究与素材边界

- 外部攻略和社交平台只用于发现路线、主题和待核验线索；票价、开放时间、预约和交通优先回到官方来源确认。
- 私人知识库、视频和下载目录只提供研究方法与候选线索，不直接复制原文、受限图片、视频或第三方组件到公开站点。
- 图片只有在来源与授权字段可追溯、且通过目的地内容适配审核时才进入公开复制流程；无法确认授权或与城市无关的内容不发布。

## 发布与公开地址

公开站点目标地址是 GitHub Pages：<https://shimmerjoe.github.io/youji-ditu/>。

每次维护完成后，先在本地完成生成、测试、浏览器检查和差异审查；只有本次变更得到明确授权、远端凭据可用且确认不会夹带其他工作时，才执行选择性提交与发布。发布顺序如下：

1. 运行生成与校验：`python -X utf8 tools\build_travel_html.py`、`python -X utf8 -m unittest discover -s tools -p 'test_*.py'`、`python -X utf8 tools\validate_travel_site.py`。
2. 用 `git status` 和 `git diff` 审查范围，只暂存本次文件（不要批量暂存所有文件），再创建清晰提交；没有明确授权时不推送。
3. 仅在明确授权且认证成功时推送到项目远端；等待 GitHub Pages 更新后打开上述公开地址，核对本次内容、脚本版本和移动端导航均已生效。公开地址未核验前，发布状态只能记为“未验证”。

公开站点与 `D:\2Life\1Travel\Travel_ayuan` 的已生成内容应保持同一提交版本。若发布或线上核验失败，保留本地变更并记录失败原因，不要以本地预览替代公开验收。

## 自驾路书与地图配置

`roadtrip.html` 默认可以离线生成分天、预算、风险、保存和 Markdown 导出。若需真实地图、路网里程、预计时间和道路收费：

1. 在高德开放平台创建“Web 端（JS API）”应用并取得 JS Key 与安全密钥，务必把可用域名限制为实际预览/发布域名。
2. 构建前设置 `TRAVEL_AMAP_JS_KEY` 与 `TRAVEL_AMAP_SECURITY_CODE` 环境变量，再运行 `npm run build`。生成器会把两项浏览器配置安全内联到路书页，不再请求可能缺失的配置文件。
3. 通过本地 HTTP 服务器预览，不能直接双击 HTML 测试地图。未设置变量时页面不会发起地图 SDK 请求，离线估算、保存、分享与导出仍完整可用。

Web 端 JS Key 与安全密钥会出现在最终静态 HTML 中，这是浏览器地图 SDK 的运行方式；必须依赖域名白名单限制滥用。不要设置、提交或内联高德 Web 服务私钥。

## 生成结果

- `index.html`：首页工作台。
- `roadtrip.html`：自驾路线、逐日安排、参考预算和风险清单。
- `cities\*.html`：城市攻略页。
- `assets\travel.css`、`assets\travel.js`：由生成器输出。
- `assets\search-index.js`：按首次搜索需要加载的全站搜索索引。
- `assets\roadtrip-*.js`、`assets\roadtrip.css`：自驾路书算法、城市数据和页面交互；浏览器地图配置由构建时环境变量内联。
- `user.html`：本地用户中心。
- `sitemap.xml`、`robots.txt`：由实际页面清单生成的搜索引擎入口。

公开地址改变时，用环境变量 `TRAVEL_PUBLIC_URL` 覆盖默认基址后重新构建；不要把本地路径写入 canonical 或分享元数据。
