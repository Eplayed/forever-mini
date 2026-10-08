# 角色交接台账（无限服资料线）

规则见本仓库 `AGENTS.md`。每轮对话由一个主角色开工，产出落文件，在这里登记一行。状态只有三种：`已定` / `待确认` / `阻塞`。

## 调用方式

- **默认自动**：只要对话工作目录是本仓库（根 `wow-forever/`、`wow-forever-web/` 或 `for-mini/`），规则文件自动生效，我每轮开头声明本轮角色，你不用点名。`daily-talk` 与 `p2-database` 不承载无限服产物，也不写无限服规则。
- **手动覆盖**：`/wow-pm`、`/wow-planner`、`/wow-ui`、`/wow-dev`、`/wow-data`、`/wow-ops`，我选错角色时用这个压回来。
- **串链条**：说"按链条走完"，我按 产品 → 数据 → 策划 → UI → 开发 顺序连着做，每步落文件，最后一次性验收。默认不自动串，避免又变成一个身份全包。
- **我漏了怎么发现**：看回复开头有没有"本轮角色：xxx｜产出：文件路径"，以及那个文件是否真的存在。缺一样就回一个字"角色"。

| 你想干什么 | 说什么 |
| --- | --- |
| 定需求、砍范围、要验收标准 | `/wow-pm` 或直接描述需求 |
| 想页面结构、清单内容、分享卡文案 | `/wow-planner` |
| 改视觉、定令牌、要截图 | `/wow-ui` |
| 写代码、跑构建、修 bug | `/wow-dev` |
| 补数据、查来源、看覆盖率 | `/wow-data` |
| 备案、提审、上线节奏、拉新 | `/wow-ops` |
| 六个角色连着走完 | "按链条走完" |

## 调用规则细则

- 自动：新对话里我先声明本轮角色与产出路径。
- 点名：`/wow-pm`、`/wow-planner`、`/wow-ui`、`/wow-dev`、`/wow-data`、`/wow-ops`。

| 角色 | skill | 主要产出位置 |
| --- | --- | --- |
| 产品经理 | `wow-pm` | `docs/PRD*.md` |
| 策划 | `wow-planner` | `docs/PLAN-*.md` |
| UI | `wow-ui` | `docs/UI.md` + `docs/screenshots/` |
| 开发 | `wow-dev` | `src/`、`tools/` + 验证记录 |
| 数据采编 | `wow-data` | `src/data/**`、`docs/wow-infinite-sources.md` |
| 运营 | `wow-ops` | `docs/OPS-*.md` |

## 当前状态快照（2026-10-08）

| 角色 | 状态 | 说明 |
| --- | --- | --- |
| 产品 | 已定 | PRD v1.0 与参考站对照 `docs/reference-gap.md` 已定范围；P0 为天赋计算器、技能书、术语、副本手册、溯源 |
| 策划 | 待确认 | 技能"新增/改动/删除/未变"四态结构已定，但无数据可填；选职业问答建议排下一批 |
| UI | 部分待补 | 设计令牌与组件状态在 `docs/UI.md`；站点截图在 `docs/screenshots/`；小程序沿用同一套令牌，截图在 `for-mini/docs/screenshots/` |
| 开发 | 已定 | 资料站新增「选职业问答」页与溯源页方法论段，修掉减点模式失效与导航高亮失效，新增 `tools/site-check.py` 回归自检（47 项全过）；仓库合并为 monorepo（远程 `Eplayed/forever-mini`）；静态站 7 页可跑，`build-data.js` 通过，图标 358 张本地化；`for-mini` 已转为无限服小程序底子（数据层三级回退 + 中英速查 + 首页完整度），新增 `tools/export-mini.js`。验证记录：`for-mini/docs/VERIFY-2026-10-08.md` |
| 数据 | 部分阻塞 | 天赋 473 节点入库但**层级点数门槛无来源**（阻塞）；89 条两源译名分歧待官方定名；英文原名全缺；掉落无源 |
| 运营 | 待确认 | 关键路径仍是小程序备案；`for-mini` 现为测试号 `touristappid`，独立 appid 与名称（D1）未定，OSS 域名白名单要等 appid |

## 待用户确认

| 编号 | 事项 | 影响 | 我的默认 |
| --- | --- | --- | --- |
| D1 | 小程序与站点名称（不得含商标词） | 卡注册与备案起跑 | 你定，或从「副本手账 / 六十级手册 / 开荒台账」里挑 |
| D2 | 是否自己买 388 元礼包打 Beta | 决定层级门槛、掉落、译名分歧能否自行核实 | 不买则数据继续标 L2，靠官方稿 |
| D3 | 无限服小程序落在哪 | **已落地**：就在本仓库 `for-mini/`（monorepo，远程 `Eplayed/forever-mini`），架构照 `poe-mini` 但 appid（待注册，现为测试号）、OSS 命名空间 `wow/{env}/v1/`、缓存 key `wow_forever_v1_`、快照文件全部独立；`poe-mini`（已移出本仓库）与 `daily-talk` 都不承载无限服代码与规则 | — |
| D4 | 小程序「先发布不备案」行不行 | **已核实：不行**。微信官方备案 FAQ 写明发布（上架）必须先完成备案，未备案发布返回 errcode 86369；平台初审 1–2 工作日 + 管局审核 1–20 工作日。可行的替代：先把**网页资料站**发出去（不涉小程序备案），小程序侧走体验版给少量人用（官方 FAQ 未明确限制，需实测确认），备案与开发并行 | 今天提交备案，同时先发网页站 |

## 交接记录

| 日期 | 角色 | 任务 | 产出 | 状态 | 下一步交给 |
| --- | --- | --- | --- | --- | --- |
| 2026-10-06 | wow-pm | 立项与合规可行性 | `docs/wow-infinite-plan.md` | 已定 | wow-data |
| 2026-10-06 | wow-data | 采编流程与源盘点 | `wow-infinite-workflow.md`、`wow-infinite-sources.md` | 已定 | wow-dev |
| 2026-10-07 | wow-data | 数据基底与采编工作台 | `docs/data-base/`（v0.3.0） | 已定 | wow-dev |
| 2026-10-07 | wow-pm | 资料站 PRD | `wow-forever-web/docs/PRD.md` | 已定 | wow-ui |
| 2026-10-07 | wow-ui | 设计系统与 7 页规范 | `docs/UI.md`、`docs/screenshots/` | 已定 | wow-dev |
| 2026-10-07 | wow-dev | 静态站实现与校验器 | `src/`、`tools/build-data.js` | 已定 | wow-data |
| 2026-10-07 | wow-data | 双源天赋对齐 + 358 图标 | `src/data/talents/*.json`、`src/img/icons/` | 已定（层级门槛阻塞） | wow-planner |
| 2026-10-07 | wow-planner | 参考站 39 板块对照与下一批 | `docs/reference-gap.md` | 待确认 | wow-pm |
| 2026-10-07 | 全部 | 建立六角色协作机制 | `AGENTS.md`、本文件、6 个 skill | 已定 | — |
| 2026-10-08 | wow-dev | 仓库合并为 monorepo（远程 `Eplayed/forever-mini`），`for-mini` 由 AI 手册改造为无限服小程序底子，新增基底→小程序导出脚本 | `for-mini/`、`tools/export-mini.js`、`for-mini/docs/VERIFY-2026-10-08.md`、根 `README.md` | 已定（chip/收藏/复制的点击动作待人工手测；`live` 链路等 OSS 上传后回验） | wow-ops |
| 2026-10-08 | wow-dev | 修根 `AGENTS.md` 上移后遗留的两处歧义：产出路径全部补上 `wow-forever-web/` 或 `for-mini/` 前缀并补小程序截图位；图标口径改回"新物品图标能否取自官方 CDN 尚未证实"，验证基线补第 4、5 条（点击动作无证据必须单列、每轮登记台账） | 根 `AGENTS.md`、本文件 | 已定 | 各角色 |
| 2026-10-08 | wow-dev | 修天赋计算器减点模式失效与导航高亮失效、补自绘头标、按 `reference-gap.md` 做选职业问答页与溯源页方法论段、新增 `tools/site-check.py` 回归自检 | `src/chooser.html`、`src/data/chooser.json`、`src/data/method.json`、`tools/site-check.py`、`tools/make-favicon.py`、`docs/VERIFY-2026-10-08-site.md`、`docs/screenshots/check-2026-10-08/` | 已定（47/47 通过；真机长按、问答权重口径、新组件未进 UI.md 三项待办） | wow-ui（归档组件）→ wow-planner（问答权重口径确认） |
| 2026-10-08 | wow-ui → wow-planner → wow-data | 新组件归档进 UI 规范并去硬编码色值；问答权重口径落成 PLAN 文档并改掉两条机制错误；新增译名回官方原文逐字核对的体检脚本与留痕例外清单 | `docs/UI.md`、`docs/PLAN-chooser.md`、`docs/DATA-AUDIT-2026-10-08.md`、`tools/audit-translations.py`、`src/data/audit-exceptions.json`、`tools/site-check.py`、`tools/build-data.js` | 已定（译名 215 条：213 逐字命中 / 1 排版空格命中 / 1 人工判定留痕；site-check 49/49） | wow-ops（发布路径待拍板） |
| 2026-10-08 | wow-data + wow-dev | 副本横幅文字被 SVG 非等比缩放拉变形（桌面端整页糊字）→ 文字移出 SVG 改 HTML 排版、配色按新本/经典/团本分族；体检范围扩到副本名与系统名，查出两条假 L0（「永久 60 级」官方中文页无此原句 → 降 L2；「不可飞行」只有英文来源 → 降 L1）；新增卡口：L0 中文名必须有 official_cn、只有官方英文的不得标 L0、系统卡片纳入统一校验；粉丝站规则收窄为「无官方中文支撑才失败」 | `src/js/glyph.js`、`src/js/app.js`、`src/css/app.css`、`src/data/systems.json`、`tools/build-data.js`、`tools/audit-translations.py`、`docs/DATA-AUDIT-2026-10-08.md` | 已定（site-check 55/55，含 6 项横幅防拉伸回归） | wow-ui（UI.md 3.5 节横幅规格待同步） |
| 2026-10-08 | wow-ui | 市场 skill 按下载量对比后决定不替换角色 skill，只吸收设计走查判据；量化基线写进 UI.md 第七节并加进 site-check 第 6 节，当场修掉八页无 H1、移动端 450 处点击目标不足 44px、滑杆无可读名 | `docs/UI.md`、`tools/site-check.py`、`src/css/app.css`、`src/js/app.js` | 已定（site-check 111/111；欠 140 处内联样式已记在 7.3） | wow-dev |

