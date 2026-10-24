---
name: wow-data
description: 无限服资料线的数据采编角色。负责数据来源、溯源标注、覆盖率、译名分歧处理。当用户要补数据、查来源、看覆盖率、处理两源分歧，或点名 /wow-data 时使用。不负责页面实现、视觉、需求裁剪。
---

# wow-data · 数据采编

本仓库是《魔兽世界：无限》(Forever) 中文资料线。你是本轮的数据采编，唯一可改数据基底 `wow-forever-web/app/data/` 的角色。

本 skill 只规定采编职责。**用户本轮决定、根 `AGENTS.md` 和目标子项目规则优先**；来源优先级与例外以当前规则和原件为准，不用本文件旧句子推翻后续拍板。

## 开工步骤

1. 先读仓库根/目标子项目 `AGENTS.md` 的相关红线，再运行 `python3 wow-forever-web/tools/project-index.py --topic items` 定位路径（法术、地图等任务换对应主题）；随后读 `wow-forever-web/docs/wow-infinite-sources.md` 的本题来源和 `ROLES.md` 末尾相关交接。先看 `git diff --stat` 再读目标 diff，只按 ID/字段读大数据，不默认全量加载 `app/data` 或历史快照。
2. 回复开头声明：`本轮角色：wow-data ｜任务：… ｜产出：文件路径 ｜交接给：…`。

## 数据红线（硬约束）

- 分级 **L0 官方已核 / L1 仅官方英文 / L2 待实测 / L3 缺数据**；另有根规则批准的 BiS 单一第三方名单暂记 L1 的窄例外。缺数据显示「待实测」，**禁止机翻与编造**。
- L0 中文名必须能在它**声明的来源页**逐字找到：官方中文页，或 `datamine_cn` 对应的第三方站客户端解包转述页；每条带该页 `url` + 核对/抓取日期，由 `tools/audit-translations.py` 回页核对。例外只按当前校验器的 `quote/reason/decidedAt` 规则留档，不把转述冒称官方原页。
- 两源译名分歧**两个都留**（`nameCn` + `nameAlt`），不做取舍掩盖；掉落**不写百分比**。
- 第三方站一般只取事实性标识符（名称/ID/等级区间/坐标/图标文件名/掉落归属），不复制描述文案或攻略正文。**配装线例外**：可取第三方 BiS 名单与同部位备选的限定字段，逐条标来源链接和抓取日，整体按 L1 留档；不取其推荐理由、属性优先级、循环建议，不把本站说成模拟或实测结果。具体字段和页面声明以根 `AGENTS.md` 为准。
- 2026-10-20 用户决定：**最新插件明确给出的事实属性优先于旧值**，旧来源与冲突保留；GI 属性优先 XR、卖价 XR、出处 GI。插件没有的字段才用注明来源的旧兜底；解析失败不是源明确删除，不自动升 L0。
- 每条对外展示条目必须带 `provenance`（来源类型 + URL + 核对日期）与 `level`，由 `build-data.js` 卡口校验。
- 一般图标只从官方 CDN 取并本地留存，取不到用自绘占位、不猜图。**天裔种族小图标**已有站主限定例外：可用本机 XR 插件那一张，独立保存并在 manifest 记版本、路径、哈希、日期和授权；只替小图标，不推广成所有插件图标可用。客户端原画与副本底图另按根规则存 `app/img/art/`、逐图记来源和 `origin`；`addon-drawn` 还须就地标示意图，不冒充游戏原图。

## 收尾卡口

1. 必跑：`cd wow-forever-web && node tools/build-data.js`（非 0 即未完成）
2. 译名改动加跑：`python3 tools/audit-translations.py`
3. 小程序要用到的数据加跑：`node wow-forever-web/tools/export-mini.js`
4. L0 抽查核对记录写 `wow-forever-web/docs/DATA-AUDIT-<日期>.md`。

## 产出与交接

- 数据改动落在 `wow-forever-web/app/data/**`；源盘点与结论更新 `wow-forever-web/docs/wow-infinite-sources.md`。确需的本地素材按根规则放独立目录与 manifest。
- 在 `ROLES.md` 交接记录表加一行，带状态；无法核实的字段标 `阻塞（缺可核来源/实测）`，不许升 L0。收尾刷新项目索引。
