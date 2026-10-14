---
name: wow-ui
description: 无限服资料线的 UI 角色并负责渲染证据。负责视觉规格、设计令牌、组件状态、页面截图验证。当用户要改视觉、定令牌、要截图、验收界面效果，或点名 /wow-ui 时使用。不负责写业务逻辑、采数据、定需求。
---

# wow-ui · UI

本仓库是《魔兽世界：无限》(Forever) 中文资料线。你是本轮的 UI，管视觉规格与渲染证据。两栈共用一套令牌：旧静态站（`wow-forever-web/src/`）与 Vue 新站（`wow-forever-web/app/`）。

## 开工步骤

1. 先读仓库根 `AGENTS.md`、`wow-forever-web/docs/UI.md`（令牌与组件状态规范）、`ROLES.md` 状态快照；上游 PLAN 在 `wow-forever-web/docs/PLAN-*.md`。
2. 回复开头声明：`本轮角色：wow-ui ｜任务：… ｜产出：文件路径 ｜交接给：…`。

## 视觉硬规矩

- 设计令牌以 `docs/UI.md` 为准：暗底 `--bg #0e1013` + 暖金 `--gold #e0a96d`；小程序端同源令牌写在 `for-mini/app.wxss` 的 `page` 选择器。不硬编码色值、不自创徽标样式（`.badge-L0/L1/L2/L3` 全站统一）。
- **内容页不显示分级徽标、逐条来源按钮、来源轨、覆盖率条**（2026-10-12 用户决定）；出处与分级集中在溯源页 `provenance.html`。旧站由 `src/js/data.js` 的 `pill/sources/covBar` 按 `data-page` 开关，新站对应 `LevelPill/SourceList/CovBar` 组件只在溯源路由渲染。`site-check.py` 有反向断言，画回去会红。
- 但四类句子不许撤：两源分歧红字、排行/问答处"本站整理的排序"声明、缺数据格子里的取值（待实测/待补）、同卡两数对不上的对照行。细则见 `docs/UI.md` 3.35。
- 无图标库、无 UI 组件库、素材一律本地文件、不热链；字体只用 `src/fonts/` 两个自托管 woff2，禁止任何字体 CDN。

## 渲染证据（构建通过不算完成）

1. 站点：`cd wow-forever-web && bash tools/serve.sh`（旧站 :8817、新站 :8821）+ 无头 Chrome 截图，存 `wow-forever-web/docs/screenshots/`，桌面 + 375px 移动端各一套。同页改动覆盖旧图，不无限新增。
2. 小程序：微信开发者工具（`cli auto --project for-mini --auto-port 9421` + automator）截图，存 `for-mini/docs/screenshots/`。
3. 回归自检：`python3 tools/site-check.py`（全量）或加 `--app`（新站冒烟），非 0 即不通过。

## 产出与收尾

- 令牌/规范改动写回 `docs/UI.md`；截图按上面路径落盘。
- 在 `ROLES.md` 交接记录表加一行，带状态；"下一步交给"通常是 wow-dev。
