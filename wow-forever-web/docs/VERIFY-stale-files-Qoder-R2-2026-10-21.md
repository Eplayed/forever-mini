# 第二轮清理（R2）· 过时入口与孤儿文件

日期：2026-10-21；角色：wow-dev（执行）；状态：**待 Codex 复核**。
任务书：`VERIFY-stale-files-Qoder-task-2026-10-21.md`；第一轮记录：`VERIFY-stale-files-cleanup-2026-10-21.md`。
工作仓库：`/Users/zhangyajun/Documents/project/wow-forever`。本轮**没有清空工作区、没有 `git add .`**；
别的会话未提交的文档/数据/截图一律未动（清单见文末「边界」）。

## 一、单元一：现行入口里仍会误导下一轮的说法

先读四处入口（根 `AGENTS.md`、`wow-forever-web/AGENTS.md`、`docs/README.md`、第一轮记录），
再对五个说法在**当前入口文件**里定点扫：`旧站是发布版 / 新站仍迁移中 / 两栈必须同步 / 旧禁区 / 旧数值`。
扫描范围：`README.md`、两份子项目 `AGENTS.md`、`docs/{README,DATA-MAINTENANCE,UI,PRD,PLAN-open-items}.md`、
`tools/project-index.py` 的 rules 入口。

**查过但确认不用改的（写清楚，免得下一轮又去"修")：**

| 位置 | 看起来像问题 | 实测结论 |
| --- | --- | --- |
| 根 `AGENTS.md:11`「21 条路由」 | `app/src/router.js` 里 `path:` 有 22 个 | 22 = 21 条页面路由 + 1 条 `/:all(.*)` 兜底。**数字是对的**，没动 |
| 根 `AGENTS.md:11`「旧站 19 页」 | — | `ls src/*.html` = 19，一致 |
| `wow-forever-web/AGENTS.md:63/67`「两栈同步」 | 像是残留的旧命令 | 原文写的是"以前每轮两栈同步的规矩**作废**""要恢复先改这条"——是废止声明，不是要求 |
| `docs/DATA-MAINTENANCE.md:115` | 像旧禁区 | 已按 10-18 决定分开写：网页动态与主观排行放开、小程序仍不做，并点名旧盘点不作红线 |
| `docs/UI.md:810`「两栈同步」 | 像现行要求 | 文首第 3 行已有第一轮加的阅读顺序声明（按日期追加、早期段落只描述当时）；这一条在带日期的章节里，属历史记录 |
| `docs/README.md` 引的入口文件 | 怕断链 | `VERIFY-prelaunch-final-2026-10-20.md`、`VERIFY-pages-and-index-2026-10-21.md`、`VERIFY-stale-files-cleanup-2026-10-21.md`、`PROJECT-INDEX.md`、`DATA-NGA-2026-10-18.md` 逐个 `test -f` 全在 |

**本轮实际改的三处（都只加导航与现状校正，没重写任何当时的测试结果与用户决定）：**

1. `docs/PLAN-wclbox-source.md` 顶部加一段现状校正：正文那句"P2 专业/任务、P3 世界地图、P4 首页动态与排行**待做**"
   已过期——四页都在 `app/src/router.js`（`/professions`、`/world`、`/updates`、`/rank`），
   抓取合并步骤在 `tools/refresh.sh`（`scrape-wclbox-{prof,shuju,dom}.py`、`merge-prof-sources.py`、
   `extract-xr-zonemap.py`）。**冲突对象是当前代码与脚本，不是另一份文档**，所以够格改。
2. `docs/PLAN-chooser.md` 顶部加一段：正文写的页面 `src/chooser.html` 是已冻结旧站那一版，
   当前页是 `app/src/pages/ChooserPage.vue`（`app/src/router.js:61`，旧路径跳转桩在 `:36`），
   数据基底仍是同一份 `src/data/chooser.json`——**改口径改数据，别去改旧站那页**。
   问答权重与机制纠错正文一字未动。
3. `docs/README.md` 把"哪些是历史/口径快照"的名单补全：原来只点了 `PRD/PLAN-open-items/wow-infinite-plan/IDEA-*`，
   同一目录下的 `PLAN-chooser.md`、`PLAN-wclbox-source.md`、`PLAN-reference-layouts.md`、
   `wow-infinite-workflow.md`、`reference-gap.md` 没被点名，容易被当成待办派工。
   现在写明：这些**决定口径仍以它们为准，但里面的页面路径与"待做"清单多半已过期**。
   ⚠ 这份文件是第一轮新建、**尚未提交**的（`?? docs/README.md`），所以我的这一处**不单独提交**，
   由第一轮那次提交带出去——否则就是替别人整份提一个新文件。

## 二、单元二：孤儿文件候选（tools/ 与 docs/，上限 5 个）

判据按任务书：逐个查 `tools/refresh.sh`、`.github/workflows/gates.yml`、`app/package.json`、
`app/src` 的路由与导入、其他脚本调用、活跃文档入口；`PROJECT-INDEX.json` 是生成物，**不算引用**。

| 候选 | 最后用途 | 引用证据 | 处置 |
| --- | --- | --- | --- |
| `tools/probe-provenance.py` | 自述"**一次性探针**：看溯源页现在渲染出哪些徽标/来源/轨/覆盖率元素。只读"；最后提交 2026-10-12 | 全仓 `rg -F` 只命中生成的 `PROJECT-INDEX.json` 与它自己；`refresh.sh`/`gates.yml`/`package.json`/`app/src` 都不调它；同类职责已有 `shot-provenance.py`（被 `VERIFY-prelaunch-final-2026-10-20.md` 记为交付件）与 `site-check.py --app` | **删除**（`git rm`，文件在 HEAD 里，`git checkout HEAD -- <路径>` 可整份恢复） |
| `tools/crosscheck-loot.py` | 2026-10-14 站主拍板的掉落↔解包比对 | 产物 `docs/ITEMS-LOOT-CROSSCHECK-2026-10-14.md` 在库，且被 `DATA-SOURCES-MAP-2026-10-16.md`、`PLAN-items-detail-and-site-2026-10-14.md` 引用——**它是那份证据的重跑路径** | 保留 |
| `tools/add-gen-art.py` | 10-12 生成三张自绘底图的那一步 | `ROLES.md:133` 把它列进交付文件；产物 `src/img/gen/**` 受 `build-data.js` 校验、仍在页面上用 | 保留 |
| `tools/shot-provenance.py` | 溯源页实拍取证 | 被 `VERIFY-prelaunch-final-2026-10-20.md` 的交付行点名（I02） | 保留 |
| `tools/extract-gi-dungeon-quests.py` | GI 副本任务抽取 | 被 `docs/DATA-SOURCES-MAP-2026-10-16.md` 记为来源链路一环 | 保留 |
| `docs/PLAN-chooser.md`、`docs/PLAN-wclbox-source.md`、`docs/PLAN-reference-layouts.md`、`docs/PLAN-open-items.md`、`docs/wow-infinite-workflow.md`、`docs/reference-gap.md`、`docs/CHANGELOG-DEV.md` | 口径/评估/盘点/变更日志 | 每份都有 1–23 处真实引用（`ROLES.md`、`build-data.js`、`src/data/releases.json`、其他 docs），且 `docs/README.md` 已把它们归到"保留供追溯" | 保留，改为加导航（见单元一第 3 条） |

**结论：本轮只有 1 个可靠可删项。** 其余"看起来旧"的都有运行、回归或溯源用途。
按任务书要求说清楚：这不等于全仓再无过时文件——`tools/` 里还有 60 多个脚本没被 `refresh.sh`/`gates.yml`
直接点名（`extract-*`、`merge-*`、`scrape-*` 成对的数据生产步骤，多数只在 `ROLES.md` 与按日期的 VERIFY 里被提到），
`rg` 只能证明"没有文本引用"，**证明不了"不会被动态调用或人工按流程跑"**，所以不盲删。

## 三、命令与退出码

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `git rm -q wow-forever-web/tools/probe-provenance.py` | 0 | 已删；`git cat-file -e HEAD:…` 事先确认在 HEAD（可恢复） |
| `rg -l -F probe-provenance ..`（排除生成索引） | — | 删后零命中，无残留链接 |
| `git diff --check` | 0 | 无空白错误 |
| `python3 wow-forever-web/tools/project-index.py --topic rules` | 0 | 刷新 280 条路径，HEAD `2efa4d6e`；rules 入口含 `docs/README.md` |
| `python3 wow-forever-web/tools/project-index.py --check` | 0 | 索引有效；被删文件已不在快照（`rg -c probe-provenance PROJECT-INDEX.{json,md}` = 0） |
| `python3 wow-forever-web/tools/project-index.py --find chooser` | 0 | 命中 `app/src/pages/ChooserPage.vue` 与 `docs/PLAN-chooser.md` 两条，改过的入口仍可定位 |

没跑的检查与为什么：本轮**没改数据、没改页面渲染、没改小程序产物**，所以按任务书"每改一处只跑相关检查"，
不跑 `build-data.js`、`site-check.py --app`、`export-mini.js`，也不截图；被删的是零引用的一次性探针，
不属于任何运行链路，因此没有需要补跑的最小回归。全程未启动网络抓取、发布、部署或收费调用。

## 四、边界与没验到的

- **`docs/README.md` 的那处改动没提交**：文件本身是第一轮新建、尚未提交的（未跟踪状态），
  我这一行只能由那次提交带出去。
- **`ROLES.md` 只追加一行**（本轮状态），该文件同时带着别的会话未提交的改动，提交时按 hunk 只取我自己那一行。
- **根 `AGENTS.md` 没动**：它带着别的会话未提交的"10-20 站主追加决定"与"按需读取约定"两段。
  本轮查到的两点都是"确认无误"（21 条路由、19 页），无需改动，也就没有覆盖别人的风险。
- 工作区里另有别的会话未提交的：`wow-forever-web/docs/{DATA-addon-update,DATA-prelaunch-dispatch}-2026-10-20.md`、
  十余份 `OPS-*/VERIFY-*` 新文档、`wow-forever-web/docs/wow-infinite-sources.md` 与
  `docs/{DATA-MAINTENANCE,PLAN-open-items,PRD,UI}.md`、两份子项目 `AGENTS.md`、第一轮删的 `mindmap` 三件——
  **本轮一行未碰、未提交、未回滚**。
- **没验到的**：① 没做全仓逐文件内容审计，孤儿判定只覆盖上表列出的候选；② 没运行任何数据/构建/界面门禁
  （本轮无相关改动，但也就没有"删这个探针不影响任何链路"的运行时证据，只有静态引用证据）；
  ③ `docs/README.md` 补的名单是否真能挡住下一轮误读，属于文档判断，要 Codex 或人从入口走一遍才算。
