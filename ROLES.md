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
| 2026-10-08 | wow-dev + wow-data | 按参考站 zh-hans 版复核后落地三项：内容页逐条来源、上线时间表单页（11 个时间点带官方原文，中英文两个上线口径并存不替玩家选）、技能四态表（脚本从官方中文深度解析稿整句抽取 38 条：新增 28/改动 5/改名 3/移除 1，12 条带层级线索；未变一律标未统计） | `src/timeline.html`、`src/data/timeline.json`、`src/data/abilities.json`、`tools/extract-abilities.py`、`src/js/app.js`、`src/js/data.js`、`src/css/app.css`、`tools/build-data.js`、`tools/audit-translations.py`、`tools/site-check.py`、`docs/reference-gap.md` | 已定（site-check 125/125；体检 273 条命中、5 条已知 L2/L3 名称未命中属预期） | wow-ui（新组件 .tlrow/.abtab/.srcbox 待归档进 UI.md） |


| 2026-10-08 | wow-ui | 全站 9 页实况复核：本地 8817 起服务逐页拍整页截图（桌面 1440 ×9 + 移动 375 ×5），首页/时间线/技能四态表/移动端均正常，无代码与数据改动；截图为一次性浏览件未入仓，正式证据仍在 `docs/screenshots/check-2026-10-08/` | 无（`/tmp/wow-pages-view-2026-10-08/` 临时浏览） | 已定 | 遗留：8812 端口上有个旧 http 服务进程（PID 39231）对本目录返回 404，下次起服务换端口或先清理 |
| 2026-10-08 | wow-data + wow-dev + wow-ui | 按参考站的「种族」「世界」两个菜单复刻内容：从国服官方中文种族公告抽 10 个种族行 / 56 个可选职业 ✓ / 40 条种族特长整句 / 7 组亮点组合，落成 `races.json` 并新增 `races.html`（矩阵可按职业列与阵营筛选、逐条来源、冲突两个都留）；顺手把该页 h4 小标题的归属回填进 `glossary.json`，33 条种族特长词条的 `raceId` 补齐，速查页因此能按种族筛选，meta 的未决项 11 关闭、9 改写；导航从 9 条平铺改成 5 组下拉（天赋/职业/种族/世界/工具），参考站的「攻略」「新动态」按红线不挂，世界地图/PvP/坐骑/套装/隐藏内容在副本页「还没采集的」里逐条写原因；新增卡口：矩阵行不写 quote（官方只有 X 标记，脚本还原的话不许冒充原文）、特长名必须在整句里、有 quote 必须有 url、孤儿 raceId 直接失败；体检脚本把排版空白的处理扩到全角标点两侧（45 条从误判未命中变命中），种族 40 条整句全部逐字命中；修掉移动端下拉面板被通用规则居中、`.field select` 漏了 44px 两件事；顺带把误入库的 `tools/__pycache__/*.pyc` 移出跟踪并补 .gitignore | `src/races.html`、`src/data/races.json`、`src/data/glossary.json`、`src/data/meta.json`、`tools/extract-races.py`、`tools/build-data.js`、`tools/audit-translations.py`、`tools/site-check.py`、`src/js/{app,glyph}.js`、`src/css/app.css`、`docs/UI.md`、`docs/DATA-AUDIT-2026-10-08.md`、`for-mini/**`（导出产物） | 已定（build-data 通过；site-check 157/157；体检 347 条、未命中 4 条均为已知 L2/L3；export-mini 可复现） | wow-ui（矩阵在 375px 下要横滚、无滚动提示，已记 7.3）；wow-dev（小程序侧要不要跟着上种族模块，等 D1 定名与 appid） |
| 2026-10-08 | wow-ui + wow-dev | 技能书与术语速查从 215 行平表改成按职业/种族分组（种族组按官方页阵营顺序，天裔两个子族合并），种族页特长表改成按种族分组并去掉重复的「所属种族」列；补图标：新增派生脚本 `tools/build-icon-map.py` → `src/data/icons.json`（键是 classId|中文名，避免兽人「坚韧」和牧师「坚韧」串图），图标格统一成占位块垫底 + 本地官方图盖面，111/215 条有真图、其余自绘占位并在页顶写明原因；顺带修掉技能书计数把四态条数当词条数显示的问题、分组表在 375px 下名称被挤成一字一行（改横向滚 + 名称列不换行）；新增卡口：icons.json 必须与 talents 一致且每个键的本地文件存在 | `src/js/app.js`、`src/css/app.css`、`src/data/icons.json`、`tools/build-icon-map.py`、`tools/build-data.js`、`tools/site-check.py`、`docs/UI.md`（新增 2.5 图标格、3.4/3.6 重写、7.2/7.3 更新） | 已定（build-data 通过含 3 处同名图标提示；site-check 169/169；体检 287 命中、4 条已知 L2/L3 未命中） | wow-data（基础技能与种族特长没有可信图标来源，要补得先解「新图标能否从官方 CDN 取」这个未决项）；wow-dev（小程序速查页要不要带图标：358 张 jpg 进主包会挤预算） |
| 2026-10-08 | wow-data + wow-dev + wow-ui | 图标落地：新增 `tools/fetch-icons.py`（只允许暴雪官方 CDN，别的域名直接拒），把 9 张职业图标、7 张种族图标、38 条种族特长图标键取到本地（img/icons 358 → 397 张）；`icons.json` 改由 talents + races 派生，键带归属（classId|名称 / raceId|名称），避免兽人「坚韧」拿成牧师「坚韧」的图；方块组件统一成占位块垫底 + 本地官方图盖面。实测结论：官方 CDN 有 `ability_hunter_pathfinding` 这类新技能图标，但没有 `inv_camelot_camping_welcomingcampfire` 这类新物品图标，也没有天裔种族图标与暗夜精灵/亡灵的 race_scourge/race_nightelf 键——「新图标能否从官方 CDN 取」从猜测变成逐键可测。清掉页面里的调试文案：副本抽屉的 JSON.stringify 原始输出改成列表、技能书页脚不再显示脚本路径；顺手修掉来源块在 url 为空时渲染出空链接（无障碍审计当场抓到）；classes.json 里一处把参考站标成 official_cn 的来源改回 fan_db，并把来源类型与域名一致性做成全局卡口。参考站种族特长图标配对只取页面上实际出现的 35 组，没出现的（血性狂怒、斧类武器专精）留空不猜 | `tools/fetch-icons.py`、`tools/build-icon-map.py`、`src/data/icons.json`、`src/data/classes.json`、`src/data/races.json`、`tools/extract-races.py`、`tools/build-data.js`、`tools/site-check.py`、`src/js/{app,glyph,data}.js`、`src/css/app.css`、`src/img/icons/**`（39 张新增） | 已定（build-data 通过；site-check 172/172，含「十页正文没有调试文案」与图标数量/坏图断言） | wow-pm + wow-planner：新发现的无限数据库 wowforever.wclbox.com 要不要升级成可入库源、首页动态与角色模块撞红线，见 `docs/PLAN-wclbox-source.md` |
| 2026-10-09 | wow-data + wow-dev | 接入无限数据库（wowforever.wclbox.com，实测为服务端渲染、curl 可取）：`tools/scrape-wclbox.py` 抓 35 座地下城 → `data/upstream/wclbox-dungeons.json`，`tools/merge-dungeons.js` 并进 `dungeons.json`：**首领 0 → 235 个、掉落归属 0 → 1055 条**，副本数 9/10/3 → 9/26/3；血色修道院按客户端拆成四区，并澄清旧未决项——奥卡兹监狱（48-53，新增）与监狱（24-32，经典）是两座本。图标：527 个掉落图标文件名走 `tools/fetch-icons.py` 从官方 CDN 取回（526 命中，`inv_ventureco_ring02_color4` 取不到→自绘），img/icons 397 → 924 张。原画：`tools/fetch-art.py` 转存 9 张职业天赋背景图 + 5 张副本载入图到 `src/img/art/`（带 manifest 与整目录下线方案），界面统一成"自绘垫底 + 原画盖面 + onerror 回退"，每张盖图带"客户端原画/示意图"标注。治理：按用户决策改 AGENTS.md 红线（动态流与排行仅网页放开、小程序仍不做；客户端解包 datamine_cn 可支撑 L0），卡口同步——L0 接受 datamine_cn 但必须有 url+抓取日期，掉落强制 L2 且不许出现百分比，art.json 路径必须真实存在；体检脚本把 datamine_cn 纳入逐字回查范围，26 条"结构问题"清零、命中 287 → 320、真未命中只剩 2 条已知 L2/L3。覆盖率 L0 216 → 250；site-check 180/180（新增第 11 节：首领掉落、掉落无百分比、原画加载、职业背景图）；export-mini 可复现，小程序主包快照未受影响（副本数据 282KB 走 OSS） | `AGENTS.md`、`tools/{scrape-wclbox.py,merge-dungeons.js,fetch-art.py,fetch-icons.py,build-data.js,audit-translations.py,site-check.py}`、`src/data/{dungeons,art,meta,icons}.json`、`src/data/upstream/wclbox-dungeons.json`、`src/img/{icons,art}/**`、`src/js/{app,glyph,data}.js`、`src/css/app.css`、`docs/{UI.md,wow-infinite-sources.md,PLAN-wclbox-source.md,DATA-AUDIT-2026-10-09.md}`、`for-mini/oss-preview/**` | 待用户确认（P2/P3/P4：专业、任务、世界地图要不要照同样口径接；首页动态与排行榜的具体形态） | wow-planner（专业/任务/世界三块的信息架构）；wow-ui（副本抽屉两级列表的移动端手感需真机过） |
| 2026-10-09 | wow-ui + wow-dev + wow-data | 天赋页改成真树、地下城按十级分档：`tools/scrape-wclbox-dom.py` 用浏览器渲染后抓到九职业天赋树（467 节点：格子位置、上限、新增/改动/换层/未变标记、前置连线、层级门槛、与经典旧世逐等级对照），`tools/merge-talents.js` 按「哪棵树+第几行+第几列」对齐并进 `talents/*.json`——**同位置名字不同的只记冲突、不覆盖字段**（避免张冠李戴），对照文本单独放 `data/talent-text/` 按需加载。**纠正一条老误判**：当年认定挖掘源的行列是「排版坐标」而只用列表模式，实为客户端真实结构就是 7 行 × 4 列（不是经典 10×5）；层级门槛也从「未核实」变成逐节点一致的 5/10/15/20/25/30。界面：三系并排网格 + 四类角标（左下菱形=与经典旧世差异，配图例与 title 不单靠颜色）+ 事后量格子中心注入的 `.tlines` 前置连线 + 「与经典旧世对比」开关。地下城：35 座按十级一档分档（10–19 起步…50–60 满级前后），卡面带载入图（`fetch-art.py` 从卡片清单补齐 36 张）、新角标、所在区域、首领与掉落计数，等级区间两说（领主大厅 13–18 官方 / 13–20 上游卡片等 5 处）与译名冲突直接摆在卡面上。meta 未决项两条天赋结构收口，`rules.tierUnlockCost` 归位（引擎读的是 rules 下而不是顶层）。 | `tools/{scrape-wclbox-dom.py,merge-talents.js,fetch-art.py,merge-dungeons.js,site-check.py}`、`src/data/{talents/*,talent-text/*,dungeons,art,icons,meta}.json`、`src/data/upstream/wclbox-{cards,talent-*}.json`、`src/img/art/**`、`src/js/{app,glyph}.js`、`src/css/app.css`、`docs/{UI.md}`、`for-mini/oss-preview/**` | 已定（build-data 通过；site-check 187/187，新增分档/角标/冲突标注/图例/连线/门槛文案/对照展开 7 条断言；export-mini 可复现） | wow-data + wow-dev：P2 专业与任务、P3 世界地图的抓取与建页；wow-ui：连线在 375px 下的可读性需真机看 |
| 2026-10-09 | wow-data + wow-dev + wow-ui | P2 专业系统：`tools/scrape-wclbox-prof.py`（服务端渲染，curl 可取）抓 13 个专业页 → `tools/merge-professions.js` 整形出 `data/professions.json`：**配方 1990 条（其中无限新增 889）、采集点 55 个**，每条带制成品物品 ID、材料清单与数量、技能橙黄绿灰四档、来源方式。抓取踩到两个坑并修好：① 同一页可能有多张同类表（炼金术 121 + 55 两截），只取第一张会少三分之一；② 采集点表的列名随专业变（采矿矿脉 / 草药学草药点 / 剥皮怪物等级档 / 钓鱼水域），改成按表头对齐、不套固定列序。**野营那一页上游不是表格结构，卡面上直接写「没解析出来」并说明原因，没有留空表也没有编数据。** 新页 `professions.html`：专业一排 + 搜索 / 我的技能 1–300 / 只看无限新增 三个筛选 + 配方四列表 + 采集点表；导航加「专业」入口。图标 1275 个键走官方 CDN（抽样 22/25 命中，全量在取，取不到的自动退回自绘块）。卡口：professions 结构校验（缺 ID / 缺名 / 未解析没写原因 / 出现百分比都失败），并把 33 条「L0 只有客户端解包支撑」的提示合并成一条带计数的，不再刷屏。 | `tools/{scrape-wclbox-prof.py,merge-professions.js,build-data.js,site-check.py}`、`src/data/{professions,meta}.json`、`src/data/upstream/wclbox-professions.json`、`src/professions.html`、`src/js/app.js`、`src/css/app.css`、`src/img/icons/**`、`docs/{UI.md,wow-infinite-sources.md}` | 已定（图标全量取完：新增 878 张、官方 CDN 取不到 77 张全是无限新物品；site-check 207/207，含第 12 节专业页 11 条） | wow-data + wow-dev：P3 世界地图（稀有 / 书籍 / 睡袋 + 地图底图）；wow-planner：野营页要什么结构 |
