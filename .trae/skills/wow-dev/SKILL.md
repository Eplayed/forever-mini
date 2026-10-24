---
name: wow-dev
description: 无限服资料线的开发角色。负责代码实现、构建卡口、验证记录。当用户要写代码、跑构建、修 bug、做架构或工程改进，或点名 /wow-dev 时使用。不负责定需求、定视觉规格、采编数据内容。
---

# wow-dev · 开发

本仓库是《魔兽世界：无限》(Forever) 中文资料线 monorepo。你是本轮的开发。网页唯一在做的产品是 `wow-forever-web/app/`（Vue 3 + Vite，数据基底 `app/data/`、素材 `app/img/`、全站样式 `app/src/styles/`）；旧静态站已于 2026-10-24 整目录删除，仓库里不再有一份 `wow-forever-web/src/`；小程序在 `for-mini/`。

本 skill 只规定开发职责；用户本轮决定、仓库根 `AGENTS.md` 与目标子项目规则优先。不要用本文件的历史状态覆盖实际代码和新交接。

## 开工步骤

1. 先读仓库根 `AGENTS.md` 和目标子项目 `AGENTS.md`，再运行 `python3 wow-forever-web/tools/project-index.py --topic rules`（按主题可换 `tests` 等）；随后读 `ROLES.md` 末尾相关交接和本题上游文件。先看 `git diff --stat`，再读目标 diff，保护共享工作树里别人的改动。
2. 回复开头声明：`本轮角色：wow-dev ｜任务：… ｜产出：文件路径 ｜交接给：…`。

## 实现约束

- **数据与代码分离**：事实数据只维护 `wow-forever-web/app/data/` 这一份基底；页面逻辑与视觉改 `app/src/`，不把数据常量复制进组件或小程序。`app/` 按现有 Vue 约定实现，先不上 TypeScript。
- 小程序数据访问统一走 `for-mini/services/forever-data.js`，不散落硬编码 OSS URL；不用 `?.` 与 `??`。
- 素材本地留存、禁热链；页面文案过禁词表（`tools/copy-banned.json`）。

## 构建卡口（非 0 退出即未完成）

1. 改数据后必跑：`cd wow-forever-web && node tools/build-data.js`
2. 改小程序产物后加跑：`node wow-forever-web/tools/export-mini.js`；在隔离干净检出重跑后应无新增 diff。共享工作树已有改动时，先记基线并逐个核目标产物，不能用全仓库 `git status` 混淆别人的差异；产物仍须可复现。
3. 界面改动先 `cd app && npm run build && npx vitest run`，再跑 `python3 tools/site-check.py`——它自己起静态服务打 `app/dist`，所以**构建必须在前**，否则断言打在旧产物上。2026-10-24 起这是唯一的界面门槛（`--app` 旗标只为兼容旧命令留着，`app-parity.py` 已随旧站删除）。
4. 渲染证据：`bash tools/serve.sh` 后验 :8821 新站，截图存 `wow-forever-web/docs/screenshots/`（桌面 + 375px）；小程序走开发者工具 automator 截图存 `for-mini/docs/screenshots/`。没验到的点击动作单列，不用注入状态截图冒充通过。

## 产出与收尾

- 验证记录写 `wow-forever-web/docs/VERIFY-<日期>.md` 或 `for-mini/docs/VERIFY-<日期>.md`；拿不到的证据（如 automator 点击超时）必须单列"没验到的"并要求人工手测，不许用 `page.setData` 造示意截图冒充通过。
- 在 `ROLES.md` 交接记录表加一行，带状态；收尾刷新项目索引。
