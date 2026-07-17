# 游记地图 · 旅游攻略网页

这是一个自包含静态旅游攻略站点。源内容在 `城市\*.md` 和 `记录.md`，网页由 `tools\build_travel_html.py` 统一生成。

## 常用命令

```powershell
python -X utf8 tools\build_travel_html.py
python -X utf8 tools\validate_travel_site.py
python -m http.server 8765
```

## 维护方式

- 修改攻略正文：编辑 `城市\*.md`。
- 新增城市：新增城市 Markdown，必要时补 `tools\city-page-meta.json`。
- 补充图片：优先放到 `assets\photos\城市slug\`，重新生成后进入页面相册和审计。
- 复核资料：查看城市页“联网核验入口”，再把确认后的链接写进“来源参考”。
- 查看薄弱项：打开 `内容与图片体检.md`。

## 发布与公开地址

公开站点是 GitHub Pages：<https://shimmerjoe.github.io/youji-ditu/>。

每次维护完成后，必须把本地生成结果同步到该公开地址；不能只在本地验收后就声明完成。发布顺序如下：

1. 运行生成与校验：`python -X utf8 tools\build_travel_html.py`、`python -X utf8 -m unittest discover -s tools -p 'test_*.py'`、`python -X utf8 tools\validate_travel_site.py`。
2. 检查变更后提交并推送：`git add -A`、`git commit -m "..."`、`git push origin main`。
3. 等待 GitHub Pages 更新，打开上述公开地址，核对本次内容、脚本版本和移动端导航均已生效；公开地址未核验前，发布不算完成。

公开站点与 `D:\2Life\1Travel\Travel_ayuan` 的已生成内容应保持同一提交版本。若发布失败，保留本地变更并记录失败原因，不要以本地预览替代公开验收。

## 自驾路书与地图配置

`roadtrip.html` 默认可以离线生成分天、预算、风险、保存和 Markdown 导出。若需真实地图、路网里程、预计时间和道路收费：

1. 在高德开放平台创建“Web 端（JS API）”应用并取得 JS Key 与安全密钥。
2. 编辑 `assets\roadtrip-config.js`：

```javascript
window.TRAVEL_ROADTRIP_CONFIG = {
  amapJsKey: "你的 JS API Key",
  amapSecurityCode: "你的安全密钥"
};
```

3. 通过本地 HTTP 服务器预览，不能直接双击 HTML 测试地图。

生成器只会在配置文件不存在时创建空配置，后续重新生成不会覆盖已填写内容。不要把高德 Web 服务私钥写进前端配置。

## 生成结果

- `index.html`：首页工作台。
- `roadtrip.html`：自驾路线、逐日安排、参考预算和风险清单。
- `cities\*.html`：城市攻略页。
- `assets\travel.css`、`assets\travel.js`：由生成器输出。
- `assets\search-index.js`：全站搜索索引。
- `assets\roadtrip-*.js`、`assets\roadtrip.css`：自驾路书算法、城市数据、运行时配置和页面交互。
- `user.html`：本地用户中心。
