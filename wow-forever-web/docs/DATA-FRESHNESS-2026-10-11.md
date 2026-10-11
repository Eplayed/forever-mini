# 数据源新鲜度盘点 · 2026-10-11（只读验收报告）

本轮角色：wow-data ｜性质：**只盘点、不重抓**。全程未改动任何已跟踪文件；网络取证只用 GET/HEAD，抓取脚本一律未带 `--write`。
回答的问题：用户问"数据是否拉取最新"——**结论：不是全部最新。wclbox 解包线整体落后一个发布目录（客户端版本 70235/70334 → 上游已到 70338），且官方中文新发了两篇职业深度解析（法师与萨满祭司 / 潜行者与术士）完全没有采**，正好卡着我们最大的两个缺口（13 个待 L0 天赋名、91 条译名分歧）。

---

## ① 一句话结论

- **落后，需要重抓**：wclbox 全部 `_shuju/<r>` 线（世界 / 改动清单 / 传承 / 副本卡片与元数据 / 专业 / 天赋）、wago.tools 排队表、官方中文（两篇深度解析 + 三篇系统/外观/战场稿）。
- **不用动**：国服在线修正栏目（最新一条仍是 9 月 23 日，无新增无限条目）、`releases.json`（23 个提交号全部在仓库里）、上线日期口径（与上游一致）。
- **最大风险不是"旧"，是"官方稿已到而我们没采"**：`docs/wow-infinite-sources.md` A 类行与 `meta.json` openQuestions 里"5 个职业没有中文深度解析"的表述**已经过时**——现在只剩圣骑士一篇没出。

## ② 逐源盘点

### 2.1 wclbox 解包线（`src/data/upstream/wclbox-*.json`）

**上游现状（2026-10-11 现读，`curl` 四个页面 + meta.json）**：
- 当前发布目录：`_shuju/r-1791702948979`（解码时间戳 = 2026-10-11 07:15 UTC），首页 / `/ditu` / `/gaidong` / `/fuben` 四页一致引用这一个目录。
- `meta.json` 现值：**`foreverBuild 1.60.1.70338`**（我们停在 70235）、`classicBuild 1.15.9.70003`（未变）、`talentsUpdated: build 1.60.1.70338, 10 月 10 日`、`launchAt 2026-11-04T23:00Z`、`betaCloseAt 2026-10-21T00:00Z`、`dropsAsOf 2026-10-06`（未变）。
- 上游自报计数 vs 我们入库的 `wclbox-changes.json`（`meta.upstreamCounts`）：

| 计数项 | 上游现在 | 我们存的 | 差 |
| --- | --- | --- | --- |
| all | **965** | 964 | +1 |
| changed | **753** | 751 | +2 |
| newTalents | **113** | 112 | +1 |
| changedTalents | **304** | 306 | −2 |
| removedTalents | **79** | 77 | +2 |
| spells | 420 | 420 | 0 |
| spellsChanged | **257** | 256 | +1 |

**逐文件（内部 `scrapedAt`/`fetchedAt` 字段 与 文件 mtime 对照）**：

| 文件 | 内部时间戳 | 停在哪个 r- 目录 / 构建 | mtime 与内部一致？ |
| --- | --- | --- | --- |
| `wclbox-world.json` | `scrapedAt 2026-10-09` | `r-1791485113190`（2026-10-08 18:45 UTC）/ foreverBuild **70235** | 一致（mtime 10-09 12:21） |
| `wclbox-changes.json` | `scrapedAt 2026-10-09` | `r-1791485113190` / **70235** | 一致（10-09 14:43） |
| `wclbox-talent-*.json`（9 职业） | `scrapedAt 2026-10-09` | 页面源 `/tianfu/<职业>`，当时构建 70235 | 一致（10-09 08:35~08:36） |
| `wclbox-professions.json` | `provenance.checkedAt 2026-10-09` | 同上 70235 期 | 一致（10-09 09:06） |
| `wclbox-legacy.json` | `fetchedAt 2026-10-10` | `r-1791561473931`（10-09 15:57 UTC）/ clientBuild **70235**，上游自述更新 10-05 | 一致（10-10 09:39） |
| `wclbox-dungeons.json` / `-cards.json` | `scrapedAt 2026-10-10` | `/fuben` 详情页（渲染抓取） | 一致（10-10 19:44） |
| `wclbox-dungeon-meta.json` | `scrapedAt 2026-10-10` | `r-1791619179598`（**10-10 07:59 UTC**） | 一致（10-10 23:16） |

**判定**：上游在 10-08 至 10-11 三天里连切三个发布目录（r-1791485113190 → r-1791561473931 → r-1791619179598 → **r-1791702948979**），我们最新的一条（dungeon-meta）也停在昨天早上那个。所有 `_shuju` 线**全部落后至少一代，world/changes/talent/prof 落后两代**（构建号 70235 → 70338，客户端版本 +103）。旧目录目前仍返回 200（`r-1791619179598/meta.json`、`r-1791485113190/changes.json` 实测），所以已有 provenance 的逐字回查暂时不受影响，但**上游随时可能收旧目录**。

### 2.2 双源天赋站（`fengshen-*.json` / `nieyi-*.json`）

- 文件 **没有任何时间戳字段**（meta 里查不到 scrapedAt），只有 mtime：**2026-10-07 21:18~21:19**，距今日 4 天（未到 14 天的周检红线）。
- `src/data/talents/*.json` 内部日期：`2026-09-13`（两站自述采集日）+ `2026-10-09`（本站对齐/合并日）。
- 判定：**取证不足**。本轮没有回 fengshen/nieyi 页面核它们是否随 70338 更新（见第四节）；但 wclbox `talentsUpdated 10-10 / 70338` 已证明客户端天赋数据本身动过，双源对齐线该重跑。

### 2.3 wago.tools 客户端排队表（`db2-group-finder.json`）

- 内部：`build 1.60.1.70334`、`fetchedAt 2026-10-10`、URL 带构建号（mtime 10-10 23:04，一致）。
- 现测：`?build=1.60.1.70334` → 200 / 9265 字节（仍在保留窗口内）；`?build=1.60.1.70336` → **400**；`?build=1.60.1.70338`（= wclbox 现在的 foreverBuild）→ **200 / 9265 字节**。
- 判定：70338 已在 wago 上架；70334 与 70338 的 CSV **字节数相同，内容大概率没变但没逐字节 diff**。`queue.json` 的 checkedAt 全部是 2026-10-10，属"落后一个构建号、内容可能零变化"，重抓成本低、可顺手。

### 2.4 官方中文页（`wow-infinite-sources.md` A 类行，7.1 表）

现读 `wow.blizzard.cn/news/index.html` 列表 DOM，**三篇新稿在整个 `src/data/` 里零引用**（`grep -rl` 无命中）：

| 文章 ID | 标题 | 我们状态 |
| --- | --- | --- |
| **24302097** | "无限"职业深度解析——**法师与萨满祭司** | **完全没采**。直接解锁 `data-status.py` 报的"13 个中文名没核到 L0 的节点"里法师/萨满的部分和 meta.openQuestions"5 个职业没中文深度解析"的 2 个 |
| **24310968** | "无限"职业深度解析——**潜行者与术士** | **完全没采**。同上，再解锁 2 个职业（5 缺 4，只剩圣骑士） |
| 24303316 | "无限"PvP 成长系统详解 | 没采。与 `systems.json`（checkedAt 最新 2026-10-08，共 8 条带日期）相关 |
| 24307308 | "无限"暗矛群岛之战（新 15v15 战场） | 没采。世界/副本线相关 |
| 24302546 | "无限"天裔外观更新展望 | 没采。与 `icon-gaps.json` 里"天裔图标 CDN 没有"那条可能有关（外观是否给了新图标键，本轮未核） |

- 已采的（24301515 猎德、24301514 牧战、24303313 座谈会、24304075 种族矩阵、24304160 Beta 公告）无需重抓，内容未变。
- **在线修正栏目**（`/24266320/`）：整页文本提取后最新一条仍是《在线修正——9月23日》，**无新增无限条目，不用动**。
- 注意到的口径分歧（记录、不处置）：官方 Beta 公告写国服 Beta"10月6日至10月26日"，wclbox meta.json 写 `betaCloseAt 2026-10-21T00:00Z`，两源分歧按红线两个都留、待核。

### 2.5 已知会过期的字段

| 字段 | 现值 | 判定 |
| --- | --- | --- |
| `meta.json` `launch` | `2026-11-05` | **与上游一致**（wclbox `launchAt 2026-11-04T23:00Z` = 北京时间 11-05），倒计时不用改 |
| `meta.json` `dataBaseline.checkedAt` | `2026-10-07` | **过时**：晚于它的抓取已有（legacy/queue 10-10、dungeons 成品 10-11），重抓后应刷新 |
| `releases.json` 提交号 | 23 个唯一哈希 | `git cat-file -t` 全部存在，**通过** |
| 成品数据 checkedAt 分布（除 scale/search 派生） | changes `10-09`(1928 条)、world `10-09`(129)、talents `10-09`、prof `10-09`、legacy `10-10`(188)、queue `10-10`(51)、dungeons 最新 `10-11`(2/72)、abilities/glossary/races/systems/timeline/classes `10-08` | 与上面各源落后判定一致 |

### 2.6 体检脚本与派生文件数字（抄录，未重跑 build-data）

- `python3 tools/data-status.py`（已跑，只读）：词条 842 / 天赋节点 473 / 副本 38（新增 9）/ 首领 228 / 掉落 1050 / 配方 1990 / 区域 44；分级 L0 366 / L1 114 / L2 360 / L3 2（L0 占 43.5%）；缺口 5 项能补 / 2 项人工核 / 10 项等外部。
- `node tools/build-data.js` **本轮没跑**：查过源码，它会 `fs.writeFileSync` 写 `src/data/search.json`、`src/data/talent-preview.json`、`src/data/scale.json`（约 1108/1144/1297 行），按任务约束（主会话在改界面，派生文件动了门禁和截图会拿到不一致的数）改为抄现成数字：三个派生文件 mtime **2026-10-11 12:46**，即主会话今天已重跑过，非陈旧。
- 工作区状态：`git status --porcelain` 只有主会话自己的 `src/css/app.css`、`src/css/tokens.css`、`src/js/app.js` 三个改动，本轮**零写入跟踪文件**（本报告除外）。

## ③ 要重抓的话：顺序、命令、代价

上游发版活跃期（三天切四个 r- 目录），且 `DATA-MAINTENANCE.md` 明确"解包站发了新构建包 → 当天重抓"。建议顺序：

1. **`tools/refresh.sh official`**（最高优先）——先把 24302097、24310968 两篇深度解析的官方中文名收进来（`extract-abilities.py --write` + 译名体检），解锁 13 条 L0 与部分 91 条分歧；顺带评估 PvP/战场/外观三篇进 `systems.json` 与否。**这一步不依赖 wclbox 版本**，先跑可以立刻提升 L0 占比。
2. **`tools/refresh.sh talents`**——wclbox `talentsUpdated` 已到 70338/10-10，九职业上游数据换版；与官方新中文名正好同一轮合并（两件事互相成全，拆开跑会白对齐一次）。
3. **`tools/refresh.sh world` → `changes` → `legacy` → `dungeons` → `prof`**——全部走 `r-1791702948979` 现读。`changes` 注意计数卡口要对上游新 `meta.json` 逐项一致（964→965 等 5 项变了，脚本是现读不用改代码）；`dungeons` 场景会把 `/fuben` 详情页与 `_shuju/dungeons.json` 一起补。
4. **`python3 tools/fetch-db2-groupfinder.py`**（或随 dungeons 链）——构建号现读会变成 70338；CSV 字节数与 70334 相同，预期改动近零，成本一次 GET。
5. 收尾门禁：`node tools/build-data.js` + `python3 tools/audit-translations.py --strict` + `tools/refresh.sh check`；刷新 `meta.dataBaseline.checkedAt`；`releases.json` 补一条玩家向更新。

**代价**：1 约半小时（含逐字回查），2~3 是大头（talents 双源对齐 + changes 1.7 MB + 渲染页抓取），4~5 各几分钟。
**风险**：① 上游正在活跃发版，重抓可能撞上再次切目录——合并前再看一次页面现值；② 旧 r- 目录现在还 200，但**重抓前先备份 `src/data/upstream/`**，否则一旦上游收旧目录，老 provenance URL 的逐字回查会整线失效；③ 天赋重对齐可能翻出新的双源分歧（现 91 条是基线）；④ 界面侧 `scale.json` 数字会随 counts 变，主会话正在改界面，**这条链要等他那轮提交后再跑**，别交叉。

## ④ 这次没验到、需要人工或真跑抓取才能确认的

1. **官方新稿的发布日期**：列表页与文章 SSR 里都没抽到可靠发表日期（只有正文里的定档 11月5日/公测 10月6日），要真实浏览器渲染列表才能定 24302097/24310968 是哪天发的。
2. **wago 70338 与 70334 的 CSV 是否逐字节相同**：只比了状态码和字节数（都 200/9265），没 diff 内容。
3. **fengshen / nieyi 两站页面本身是否已随 70338 更新**：本轮没回这两个站取证（它们的文件也没存内部时间戳，属采集脚本的历史欠账，建议下次给抓取脚本补 `scrapedAt` 字段）。
4. **`_shuju/r-1791702948979/legacy.json`、`map-zones.json` 等内容级差异**：只核了目录与 `meta.json`，没有逐字段 diff，差异量要真重抓才知道。
5. **图标 CDN 在 70338 下的覆盖**：`icon-gaps.json` 的 83 条缺键是 70235 期的实测结论，新版本是否补了天裔/新物品图标未逐键重测。
6. **wowhead 对账**：季度性核对，本轮不在范围。
7. **`build-data.js` 当前是否全绿**：因约束未跑（它会写 `src/data/` 三个派生文件）；现成派生文件是 10-11 12:46 主会话跑出来的，但"此刻数据+最新代码仍全绿"需要在提交前由主会话或下轮 `refresh.sh check` 确认。

---

*证据留存：本报告全部数字来自 2026-10-11 夜间的现读（wclbox 四页 + `_shuju/r-1791702948979/meta.json`、wago 三个构建号探针、`wow.blizzard.cn/news/index.html` + 两篇文章页 + 在线修正整页），临时文件在 `/tmp/wclbox_*.html`、`/tmp/art_2431096*.html`、`/tmp/hotfix.html`，可复跑命令见各节。*
