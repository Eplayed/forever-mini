# 架构评审 · forever-mini（2026-10-13）

- 角色：wow-dev
- 范围：整仓（`wow-forever-web/` + `for-mini/`），基于 clone 自 `Eplayed/forever-mini` 的 2026-10-12 前后代码
- 结论先行：**骨架健康，问题在工程运维层**。单一数据基底 + 构建门禁 + 三级回退这套设计是对的，不建议动；要处理的是 CI 缺位、仓库体积、双栈窗口期、台账膨胀四件事。

## 一、现状快照（实测数字）

| 项 | 数值 | 说明 |
| --- | --- | --- |
| 仓库工作区体积 | 167 MB | 含 `docs/` 截图 147 MB（88%） |
| 截图 | 375 张 / 147 MB | 全部进 git，随验证基线持续增长 |
| 静态站页面 | 20 个 HTML 壳页 | 每页约 0.8 KB，内容全由 JS 渲染 |
| 旧站渲染器 | `src/js/app.js` 3407 行 / 223 KB | 全站 20 页共用一个 IIFE |
| Vue 新站 | 3/17 页迁完 | HomePage / WorldPage / ClassesPage，其余落 `Unmigrated.vue` |
| 数据基底 | `src/data/` 26 份 JSON | 最大 professions.json 1.4 MB、changes.json 907 KB、search.json 275 KB |
| 数据门禁 | `tools/build-data.js` 1376 行 | 校验 + 覆盖率 + 禁词 + 溯源，单文件 |
| 工具脚本 | 41 个 | Python 3.9 与 Node 混编 |
| 小程序 | 2 个 tab 页 | 数据层三级回退（OSS → storage → 打包快照） |
| CI | 无 | 没有 `.github/`，门禁全靠本地手动跑 |
| 台账 | `ROLES.md` 149 KB | 每轮加一行，永不归档，已超单次读取上限 |

## 二、架构骨架（值得保留的部分）

数据只有一个真相源，三端消费：

```
第三方源(wclbox/wowhead/官方页)
  → tools/（采集·合并·门禁·导出）
  → src/data/（唯一数据真相，26 份 JSON）
      ├→ src/ 静态站：运行时 fetch JSON
      ├→ app/ Vue 新站：app-assets.py 同步副本
      └→ export-mini.js → for-mini：OSS(实时) → storage(缓存) → 快照(兜底)
```

优点，不要在演进中破坏：

1. **单一数据基底**：改内容只动 `src/data/`，两栈一小程序读同一份，无双源漂移。
2. **门禁前置**：`build-data.js` 把分级/溯源/禁词做成非 0 退出卡口；`export-mini.js` 导出前再拦一遍。
3. **三级回退 + source 诚实标注**：小程序断网不白屏，且禁止静默呈现离线数据。
4. **素材本地化 + manifest 溯源**：图标/原画全部本地留存，可整体下线回退自绘。
5. **角色协作机制**（AGENTS.md 六角色 + 产出落文件 + 台账）：为 AI 协作设计的流程，防一锅粥。

## 三、问题与建议（按优先级）

### P0-1 没有 CI，门禁无强制执行者

- 现状：`.github/` 不存在。`build-data.js`、`site-check.py`、`app-parity.py`、vitest 全靠自觉。"非 0 退出即未完成"没有人强制。
- 风险：AI 协作 + 多机开发场景下，一次忘跑门禁的提交就会把坏数据/坏界面带上主干。
- 建议：加最简 GitHub Actions（push/PR 触发）：`node tools/build-data.js` + `cd app && npm ci && npm run build && npx vitest run`。Python 侧自检（site-check 需要起服务+无头浏览器）可后置到合前手动跑。半天工作量，收益最大。

### P0-2 截图撑爆仓库

- 现状：375 张截图 147 MB，占仓库 88%，全部在 git 历史里，且验证基线要求每轮界面改动都新增截图（桌面 + 375px 两套）。
- 风险：clone 越来越慢，git diff/log 噪音大，仓库不可持续。
- 建议（选其一，按代价从小到大）：
  1. **归档旧批次**：`docs/screenshots/` 只保留每个页面最新一套；历史截图按日期打 tar 移出仓库（网盘/OSS 留档），`.gitignore` 掉归档目录。
  2. git lfs 管 `*.png`（历史已入库的部分需要 rewrite，成本高，仅在前两者不够时考虑）。
  3. 约定里补一条：验证记录引用截图文件名即可，同页重复截图覆盖不新增。

### P1-1 双栈并存没有截止线

- 现状：旧站（`src/` + 3407 行 `app.js`）与 Vue 新站（`app/`）并行，靠 `app-parity.py` 逐页对拍。已迁 3/17。
- 风险：迁移窗口越长，每个功能改动越可能要写两遍；`app-parity.py` 对 DOM 类名/文本敏感，旧站任何调整都可能把对拍打红；`app.js` 会继续膨胀。
- 建议：
  - 旧站**冻结新功能**，只修 bug 与数据文案（数据本来就与渲染分离，成本低）。
  - 给迁移定完成时间点或按页排期，迁完即删 `src/js/app.js` 与对拍脚本。
  - 迁移期间新页面只在 `app/` 做，不再往 `app.js` 加渲染函数。

### P1-2 ROLES.md 台账无限增长

- 现状：149 KB，超出常用工具单次读取上限，历史交接记录已不可读。
- 建议：主文件只保留「调用方式 + 当前状态快照 + 待确认项 + 近 30 条交接」；更早的交接记录按月切到 `wow-forever-web/docs/roles/2026-09.md`、`2026-10.md`（链接回主文件）。AGENTS.md 相应加一句归档规则。

### P2-1 工具链双运行时 + 类 Unix 假设

- 现状：41 个脚本 Python/Node 混编；`bash tools/serve.sh`、`python3` 命令在原生 Windows PowerShell 下不可用（`python3` 常缺失、bash 需 Git Bash/WSL）。
- 影响：本机（Windows 编码 + Mac 跑服务的双机模式）在 Windows 侧跑验证基线（起服务 + 截图）会卡。
- 建议：增量收敛——新工具一律 Node（已有 Node 基建与门禁链）；Python 存量不急着改，但在 `wow-forever-web/AGENTS.md` 写明 Windows 侧需要 Git Bash + `python` 别名（或直接规定验证在 Mac 侧跑）。`serve.sh` 可补一个 `serve.ps1` 等价物，两个命令的事。

### P2-2 build-data.js 单文件门禁继续膨胀

- 现状：1376 行，数据类型每加一种就再涨。
- 建议：低优先级。迁移完成后可拆 `tools/gates/`（每类数据一个规则文件 + 一个 runner）。现在不动，避免在双栈期增加变量。

### P3-1 大 JSON 首屏加载

- 现状：静态托管下 professions.json 1.4 MB / changes.json 907 KB 整份拉取。
- 建议：先确认托管端 gzip/br 已开启（OSS 或静态托管默认多有）。开启后暂不必分片；若后续移动端实测慢，再按职业/副本分片懒加载。

### 明确不做 / 无需担心

- 小程序快照与 OSS JSON 结构一致性：由 `export-mini.js` 单点生成，结构漂移风险已被设计消掉。
- 数据与渲染分离、禁词闸、两源分歧保留等红线机制：本身是好设计，不动。

## 四、行动清单（按序）

| # | 事项 | 角色 | 状态 |
| --- | --- | --- | --- |
| 1 | 加 GitHub Actions 最简门禁（build-data + app 构建 + vitest） | wow-dev | 已定（2026-10-13）：`.github/workflows/gates.yml`，fetch-depth 0 保 releases 提交号核对；四条命令本地全链预验通过（build-data exit 0 / npm ci / vite build / vitest 69-69） |
| 2 | 归档 `docs/screenshots/` 旧批次，改验证截图覆盖式留存 | wow-ui / wow-dev | 已定（2026-10-13）：10-08~10-12 共 254 张 / 94.6MB tar 入 `docs/screenshots-archive/`（已 gitignore，张数逐一核对），工作区截图 147MB→49MB；留存口径写入 `wow-forever-web/AGENTS.md` 第 7 条；git 历史仍带旧图，彻底变小需历史重写（另行决策） |
| 3 | 旧站冻结新功能；迁移排期定截止 | wow-pm / wow-dev | 待确认 |
| 4 | ROLES.md 按月归档，主文件瘦身 | wow-dev | 待确认 |
| 5 | Windows 侧验证路径说明（Git Bash / ps1）写入子项目 AGENTS.md | wow-dev | 待确认 |
| 6 | 六角色 skill 实体化（本次已做，见 `.trae/skills/` 或项目 skills 目录） | wow-dev | 已定 |

## 五、skill / 插件配套（2026-10-13 决策）

- **skill-creator**：把 AGENTS.md 六角色做成项目级 skill，`/wow-dev` 等点名直接生效（本次落地）。
- **TRAE-browseruse**：已可用，覆盖"界面改动必须有渲染证据"的截图环节，无需安装。
- **schedule**（可选）：`tools/refresh.sh` 数据抓取链定时化。
- **Lark**（可选）：台账交接同步飞书多维表格，缓解 ROLES.md 膨胀。
- 营销类、行业研究类、办公文档类插件与本仓库场景无关，不装。
