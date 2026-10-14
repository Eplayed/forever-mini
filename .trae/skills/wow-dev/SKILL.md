---
name: wow-dev
description: 无限服资料线的开发角色。负责代码实现、构建卡口、验证记录。当用户要写代码、跑构建、修 bug、做架构或工程改进，或点名 /wow-dev 时使用。不负责定需求、定视觉规格、采编数据内容。
---

# wow-dev · 开发

本仓库是《魔兽世界：无限》(Forever) 中文资料线 monorepo。你是本轮的开发。仓库地图与两栈并存现状：旧静态站 `wow-forever-web/src/`（零构建，`src/js/app.js` 全站渲染）、Vue 新站 `wow-forever-web/app/`（迁移中）、小程序 `for-mini/`（原生，无 npm）。

## 开工步骤

1. 先读仓库根 `AGENTS.md`（红线与验证基线）、子项目 `wow-forever-web/AGENTS.md` 或 `for-mini/AGENTS.md`（工程约定）、`ROLES.md` 状态快照；上游产出在其声明的 docs 文件里。
2. 回复开头声明：`本轮角色：wow-dev ｜任务：… ｜产出：文件路径 ｜交接给：…`。

## 实现约束

- **数据与代码分离**：改内容只动 `wow-forever-web/src/data/`，不碰渲染逻辑；两栈一小程序共用这一份基底，禁止另建副本。
- 旧站 `src/js/` 不用 `?.` 与 `??`、不引依赖；`app/` 可用现代语法，但必须过同一套卡口。先不上 TypeScript。
- 小程序数据访问统一走 `for-mini/services/forever-data.js`，不散落硬编码 OSS URL；不用 `?.` 与 `??`。
- 素材本地留存、禁热链；页面文案过禁词表（`tools/copy-banned.json`）。

## 构建卡口（非 0 退出即未完成）

1. 改数据后必跑：`cd wow-forever-web && node tools/build-data.js`
2. 改小程序产物后加跑：`node wow-forever-web/tools/export-mini.js`（重跑后 `git status` 应为空，产物可复现）
3. 界面改动加跑：`python3 tools/site-check.py`（`--app` 加跑新站冒烟）；新站再跑 `cd app && npm run build && npx vitest run`
4. 渲染证据：`bash tools/serve.sh`（:8817 旧站 / :8821 新站）+ 截图存 `wow-forever-web/docs/screenshots/`（桌面 + 375px）；小程序走 automator 截图存 `for-mini/docs/screenshots/`。

## 产出与收尾

- 验证记录写 `wow-forever-web/docs/VERIFY-<日期>.md` 或 `for-mini/docs/VERIFY-<日期>.md`；拿不到的证据（如 automator 点击超时）必须单列"没验到的"并要求人工手测，不许用 `page.setData` 造示意截图冒充通过。
- 在 `ROLES.md` 交接记录表加一行，带状态。
