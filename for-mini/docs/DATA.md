# 数据契约与分发流程（小程序侧）

来源：`wow-forever-web/app/data/`（站点基底）。小程序**不自己维护数据**，只消费导出与分片产物，保证与网页端同源。
分发层的完整设计与取舍在 `wow-forever-web/docs/OPS-oss-分发层-poe方案落地-2026-10-21.md`，本轮实测记录在 `docs/VERIFY-OSS-01-分发层-2026-10-21.md`。

## 一、路径与命名空间

bucket 沿用 PoE 那条线已备案的域名，前缀完全隔离，不共用文件、不共用缓存 key。

```
https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com/
  wow/{beta|release}/v1/manifest.json                      ← 唯一可变指针（max-age=60）
  wow/{env}/v1/builds/{buildId}/manifest.json               ← 批次自带清单（回滚位）
  wow/{env}/v1/builds/{buildId}/files.json                  ← 逐文件哈希（25.1 KB）
  wow/{env}/v1/builds/{buildId}/meta.json | glossary.json
  wow/{env}/v1/builds/{buildId}/dungeons/index.json
  wow/{env}/v1/builds/{buildId}/dungeons/detail/{id}.json
  wow/{env}/v1/builds/{buildId}/dungeons/loot/{id}.json
```

| 项 | 值 |
| --- | --- |
| 命名空间 | `wow/{env}/v1/`，`env` = `beta`（内测）/ `release`（线上） |
| `buildId` | 内容指纹前 12 位；同一份基底重跑不变，改一个字段就换一批 |
| 缓存 key | `wow_forever_v1_{用途}@{buildId}`（**批次号必须在 key 里**，否则旧批会冒充新批） |
| 指针缓存 key | `wow_forever_v1_pointer@{env}` |
| 收藏 key | `wow_fav_terms_v1`（本机行为数据，不上传） |
| 打包快照 | `data/forever-glossary-snapshot.js`（48 条）、`data/forever-meta-snapshot.js`、`data/forever-dungeon-snapshot.js`（**M01 起：38 本索引全放**）、`data/forever-class-snapshot.js`（**2026-10-22 首页改版起：9 职业 + 10 种族与特长，只留界面要用的字段**）；四份合计 53.6 KB / 预算 60 KB |

`wow/release/v1/` 目前**从没传过任何文件**（2026-10-21 匿名 GET 实测 404），所以线上小程序现在读到的都是打包快照。

## 二、只有一个取数口子（M01 起）

| 层 | 文件 | 管什么 |
| --- | --- | --- |
| 页面 | `pages/home`、`pages/glossary`、`pages/dungeons`、`pages/dungeon` | 只调 `services/forever-data.js`，不自己拼 URL、不自己发请求 |
| 服务 | `services/forever-data.js` | 打包快照兜底、收藏（词条 + 副本）、最近看过、L0–L3 与类型文案 |
| 分发 | `services/oss-manifest.js` | 指针 → 索引 → 分片、五项校验、缓存与四态语义 |

`forever-data.js` 里那套平铺地址（`wow/release/v1/{文件}.json`）**已经删掉了**：它没有批次身份、没有校验，
拿不到就静默回退缓存，正是 PoE 那条线踩过的坑。现在它只做 `loadMeta()` / `loadGlossary()` / `loadDungeonIndex()`
三个转调，返回值多带 `sourceText`（界面直接显示的那句话）与 `cacheHit`。

## 三、批次里每份文件长什么样

指针 `manifest.json`（M02 后 7.0 KB，冷启动必取；示例取自 2026-10-22 的批次 `a6162e5f5e45`，
里面的数会变，别抄成常量）：

```jsonc
{
  "schemaVersion": 1, "product": "wow-forever-mini", "env": "beta",
  "namespace": "wow/beta/v1", "buildId": "e38e5ae790d4",
  // 没有 builtAt：同一 buildId 的清单必须逐字节恒定，否则"不可变批次"每次重建都会被自己的时间戳改写。
  // 发布时刻看对象的服务端 Last-Modified 与本地 oss-build/{env}/last-upload.json。
  "timeNote": "…", "minClientSchemaVersion": 1,
  "source": { "commit": "bedaa241", "inputs": [{ "rel": "app/data/dungeons.json", "bytes": 334535, "sha256": "…" }],
              "exportCheck": { "tool": "wow-forever-web/tools/export-mini.js", "reproduced": true,
                               "outputs": [{ "rel": "oss-preview/meta.json", "bytes": 1724, "sha256": "…" }] } },
  "counts": { "dungeons": 38, "terms": 215, "spells": 498, "spellClasses": 9,
              "lootRows": 1050, "lootItems": 1018, "files": 92, "bytes": 1050000 },
  "factDates": { "min": "2026-10-07", "latest": "2026-10-11",
                 "dungeonDetail": { "min": "2026-10-07", "max": "2026-10-11", "distinct": 4, "recordsWithoutDate": 1 } },
  "droppedFields": [],
  "assets": { "dir": "assets/", "iconExt": ".jpg", "index": "assets/index.json",
              "count": 1117, "bytes": 3531000, "missing": 0, "rule": "界面拼出来的地址只许落在 assets/ 下" },
  "integrity": { "method": "etag", "clientChecks": ["…五项校验的完整口径见下…"],
                 "whatItIsNot": "是传输/存储完整性校验，不是抗伪造的内容签名" },
  "pointer": { "key": "wow/beta/v1/manifest.json", "cacheControl": "public, max-age=60, must-revalidate" },
  "fetch": { "meta": { "path": "builds/…/meta.json", "sha256": "…", "etag": "17952BBC…", "md5": "…", "bytes": 1829, "records": 1 },
             "glossary": { "…": "84,208 B / 215 条" }, "dungeonIndex": { "…": "29,077 B / 38 条" },
             "spellClasses": { "…": "spells/classes.json，9 个职业" },
             "lootIndex": { "…": "loots/index.json，1,050 行 / 118 KB" } },   // 五个入口，取哪个才多那一次 GET
  "bundle": { "path": "builds/e38e5ae790d4/files.json", "sha256": "0397629b…", "etag": "EAD6C901…", "bytes": 29516 }
}
```

副本索引 `dungeons/index.json`（25.2 KB / 38 条，列表页只要这一份）：

```jsonc
{ "schemaVersion": 1, "product": "wow-forever-mini", "buildId": "…", "kind": "dungeon-index",
  "counts": { "total": 38, "newDungeons": 9, "classicDungeons": 26, "raids": 3 },
  "lootDisclaimer": "…", "notCollected": { "route": 38 },
  "items": [{ "id": "hall-of-thanes", "kind": "new", "nameCn": "领主大厅", "nameEn": "Hall of Thanes",
              "nameCnConflict": "诸王大厅", "levelRange": "13-20", "levelRangeOfficial": "13-18",
              "faction": "联盟", "zoneCn": "…", "partySize": 5, "level": "L0",
              "bossCount": 4, "dropCount": 1, "hasRoute": false,
              "art": "art/dungeons/hall-of-thanes.webp",   // M02 起索引也带原画，列表页要出图；缺的那座是 null
              "detailPath": "dungeons/detail/hall-of-thanes.json", "lootPath": "dungeons/loot/hall-of-thanes.json",
              "detailEtag": "6F1CB781…", "detailBytes": 3413, "lootEtag": "A071A464…", "lootBytes": 674 }] }
```

详情 `dungeons/detail/{id}.json`（均值 2.6 KB，最大 4.9 KB）＝ `{ schemaVersion, product, kind: "dungeon-detail", buildId, source, dungeon }`，
`dungeon` 是该条完整记录（去掉 `drops`、`art`、`bosses[].portrait`，加 `dropCount` / `lootPath`），
`provenance[]` 原样带下来。**2026-10-23 起小程序副本页不再摆"来源"这一节**（站主指令），
但这份记录照旧下发：网页端那一节、`build-data.js` 的逐字回查与 M01 那条断言都读这里。
掉落 `dungeons/loot/{id}.json`（均值 12.1 KB，最大 53.3 KB）＝ `{ …, kind: "dungeon-loot", dungeonId, level, lootNote, drops[], cardCols, cards[] }`，
`drops` 里只有物品事实字段，**没有百分比**。
`cards` 是 2026-10-23 加的装备详情：位置数组，列名写在同片 `cardCols`
（`itemId / type / ilvl / st / sell / stKey`），客户端按列名取值不写死下标。
为什么不另开一片或每件一个文件、`BUDGET_KB.loot` 为什么仍是 64 KB 没放宽，
理由与量出来的数都在 `docs/VERIFY-副本详情与装备详情-2026-10-23.md` 第四节。
`meta.json` / `glossary.json` 现在也带 `schemaVersion / product / kind / buildId` 四个身份字段（业务字段一个没动）。

### M02 新增的三份

职业名单 `spells/classes.json`（约 4 KB / 9 条）＝ `{ …, kind: "spell-class-index", counts, fieldNote, classes[] }`，
每个职业一条：`classId / nameCn / nameEn / iconKey / level / count / tabs[] / states / shardPath`
加三个校验值 `shardEtag / shardMd5 / shardBytes`。客户端点开哪个职业才取那一片，校验值随名单下发。

职业法术片 `spells/class/{classId}.json`（37–55 KB，九片）＝ `{ …, kind: "spell-class", classId, spells[] }`，
`spells` 是该职业全部法术（名称、级数、起学等级、与经典旧世的对照状态、逐级 spellId、来源）。
**没有技能描述，也没有循环建议**——导出层与分发层各拦一道（`oss-release-test.js` 有对应的红线断言）。

掉落反查表 `loots/index.json`（118 KB / 1,050 行）＝ `{ …, kind: "loot-index", cols, dungeons[] }`。
一行一个物品，用**位置数组**存：`cols` 写死六列 `["itemId","name","quality","iconKey","boss","level"]`，
`boss` 是该座 `bosses[]` 里的序号，副本名与首领名一座只存一份。客户端按位置取值，
所以"行长度等于列数"是构建端的硬卡口（少一列就会把首领序号当品质显示）。
同一件装备出现在几座本就是几行，界面按 `itemId` 归并成"这件装备 → 哪几座本、哪个首领"。

### M03 新增的三份（职业卡与指南）

职业索引 `classes/index.json`（约 39 KB）＝ `{ kind: "class-index", counts, factions, races[], classes[], combos[], conflicts[] }`。
`races[]` 每条带 `classes`（可选职业矩阵）与 `traits`（特长名 + 效果），`classes[]` 每条带 `shardPath / shardEtag / shardMd5 / shardBytes`
与 `hasTalents`；`combos[]` 是无限新增的种族职业组合（官方中文来源）。
**注意键名**：基底 `classes.json` 用 `id/cn/en`，导出层换成 `classId/nameCn/nameEn`——分发层与界面只认后者。

**种族条目由 `oss-release.js` 的 `raceEntry()` 归一化一份**（2026-10-22 补天裔）：
天裔两条的特长在基底里挂在 `subgroup.traits`（各 4 条，L0 官方中文），顶层 `traits` 是空数组，
而界面只读顶层——于是玩家看到"还没核到"、数却一直都在。现在导出这一层合成一份并带 `traitVia` 说明来路，
`subgroup` 只留 `nameCn`（原来连 lore 带 traits 整个下发，等于同一份数发两遍），
`portrait` 按种族 id 去 `art.json` 对上。**2026-10-23 站主两次改口后的最终口径（写在 `raceEntry()` 里）**：
10 个种族**统一取 `art.json.races` 那批 128 客户端种族头像**（`app/img/art/races/*.webp`，2026-10-12 就在库、逐张带 manifest），
`raceIcons`（10-20 单独授权那张 64 插件天裔小图）退成兜底，只在某族大图缺了时才用。
为什么换：暗夜精灵补上之后同一排里是 9 张官方 CDN 的 56 图标 + 1 张 128 头像，清晰度一眼看出两样，
站主看完实拍说「10 个统一都换成大图」。
两条边界：官方 CDN 的 `iconKey` **仍随分片下发**（网页端一处不变，它读的还是 56 那张）；
10-20 那条插件小图授权不撤。要退回「官方 CDN 优先」，改 `raceEntry()` 的顺序，
并同步 `oss-release-test` 那条「10 个种族的图标位统一是 art/races/ 那批大图」。
暗夜精灵那条实测照旧成立：官方 CDN 的 `race_nightelf_male` 等四个候选全回 403（对照组 `race_human_male` 200），
`races.json` 里 `iconKey: null` 是对的、不是漏填。
**基底 `races.json` 一个字没改**（网页那侧本来就读 `subgroup.traits`）；
主包快照**直接 require 这个函数**，不另抄一份字段规则——这次漂移就是"两边各写一套"写出来的。
界面取图统一走 `oss.raceIconUrl(batch, race)`：先 `portrait` 再 `iconKey`，都没有就自绘首字块。
职业页那排「无限新增的组合」也走同一个口子——分发层按 `raceCn` 给每条 combo 补了
`raceId / racePortrait / raceIconKey`（2026-10-23 站主：那一格该放**种族**图标，不是职业图标）。
导出层还加了一条硬卡：**归一化后仍然一条特长都没有、却标着 L0/L1 的种族 → 拒绝出包**。

天赋片 `talents/class/{classId}.json`（约 34 KB / 九片）＝ `{ kind: "talent-class", classId, grid, rules, trees[] }`，
节点字段 `tier / column / maxRanks / nameCn / nameAlt / iconKey / requires / level / changeState`；
每棵树另带 `specArt`（系底图，真源 `art.json` 的 `specs[{classId}-{系序号}]`，与网页 `lib/art.js` 同一个键规则，
2026-10-22 起登记进素材台账：27 张 / 228 KB，台账从 1304 → 1331 个）。
`nameAlt`（两家资料站叫法不同）与 `changeState`（相对经典旧世：新增/改动/换层/未变）以前没下发，
2026-10-22 补上——前者是红线"两源分歧两个都留"，后者是长按详情里那句"与经典旧世比"。
**天赋的具体效果说明库里没有**（两家上游只采了名称/坐标/上限/前置），界面照实写"还没入库"，
要补必须先在 A 采第三方 tooltip（要开红线例外）/ B 官方中文页 / C 游戏内实测 三条里挑一条。
**`rules` 从 2026-10-22 起随片下发**（`totalPoints` + `tierUnlockCost`）：站主要小程序的天赋树做成
"能模拟点配置、和网页版那样"，网页引擎本来就用这份数做加点判定，小程序不做判定才是不一致。
M03 那条"刻意不下发"随之作废（`oss-release-test` 里那条断言一起翻了）。
放松的只是"下发"，不是"怎么说"：界面上固定留一句
"层级门槛按经典旧世推（第 2 层起 5 / 10 / 15 / 20 / 25 / 30 点），无限服还没实测"，
拿不到 `rules` 时退成"不做分层限制"并照实说——降级路径在 `f2-talent-sim.png` 里拍到了。

指南 `guide.json`（入口文件）＝ `{ kind: "guide", meta.boundaries, macros[], addons[] }`。
现在两条都是空数组——空是合法状态。**首页的指南卡固定占一格**（2026-10-22 站主指令：
"中英速查不要，我要的是指南卡片"），不再按条数决定显不显示，点进去是诚实的空状态"还没整理"。
导出层卡口跟着红线写：宏必须有文本与来源+抓取日期，插件必须有名字/作者/用途一句话与来源，
用途描述像"循环提示"的直接拒绝出包。

职业索引是**四份分片里唯一带主包快照兜底的**（`loadClassIndex()` → `data/forever-class-snapshot.js`）：
首页下面那两段（选职业 → 可选种族与种族特长）是玩家第一眼的内容，断网也要有。
快照只留界面渲染的字段（不含 `lore` / `provenance` / `combos` / `conflicts`），
所以断网时职业 tab 的"无限新增组合"那一块是空的——那是真需要联网的部分。

指针入口从 5 个变 7 个（`meta / glossary / dungeonIndex / spellClasses / lootIndex / classIndex / guide`），
`BUDGET_KB.manifest` 相应从 8 KB 提到 12 KB，冷启动上限 40 → 44 KB。

### 配装线（2026-10-26 新增，网页那条 BiS 做进小程序）

站主指令："根据 web 页面的 BIS 页面，在小程序中添加 BIS 页面…3D 模型先放模型占位，后续替换真实模型"。
数据在分发层现算（`tools/oss-release.js`，与掉落装备卡同一个先例），三份产物：

| 文件 | 大小 | 内容 |
| --- | --- | --- |
| `bis/index.json` | 17.7 KB | 38 套的编号/职业/模式/等级/核对日/来源 URL、9 个职业（带图标键）、**口径句**、部位桥表 `slotKeys`/`slotSiblings` |
| `bis/items.json` | 118 KB | 830 件装备的显示行，位置数组，列名在 `cols`：`id,name,quality,ilvl,iconKey,st` |
| `bis/set/<id>.json` × 38 | 平均 15 KB | 这一套的 `doll`（`[部位,序号,物品ID]`）、`alts`、`enchants`、`consumables`、`src`（来源中文串）、`alt`（第二家逐格并列）、`sum`（两阵营属性合计） |

四条硬口径：
1. **装备的名字/品质/装等/属性行/图标一律回本站物品库现查**，名单只存"哪件在哪个部位、按什么顺序"；
   每套引用的每个 ID 必须在共享表里有行（构建时卡住），否则玩家点开是一格空白。
2. **属性合计在构建时算**，规则读网页那份 `app/src/lib/item-stats.js`（构建期求值，不另抄一份）；
   界面上固定带那句"只把装备的属性行相加：不含职业与种族的基础值，也不含附魔和套装效果"。
3. **部位桥表随索引下发**，两端读同一份（参考站的 `head/neck…` 与纸娃娃的"项链/戒指…"不是一套词，
   两枚戒指、两个饰品同名要靠 `cell` 区分）。
4. **红线扫描**：索引与 38 片里不许出现百分比，也不许出现"秒伤/DPS/权重/更好/优于"
   （`oss-release-test` 有一条反例：往名单里塞"秒伤"必须让构建失败）。

**配装的 3D 那一层（2026-10-30 补）**：不进这三份产物，走**自己那条通道**——
清单 `wow/{env}/v1/bis/models/index.json`（151,443 B，可变、`max-age=60`，与开关同一档语义）
+ 76 份按内容寻址的不可变对象 `wow/{env}/v1/assets/models/real/<setId>-<faction>-<成品sha前12>.glb`
（合计 111,117,416 B，客户端侧一次只取一件）。它**不在气密批次里**：换一件模型不换 `buildId`、不重发数据、不发版。
清单每条同时带 PNG 成品、网页源、最初客户端导出三层 `bytes/sha256` 与 `dollSnapshot`——
客户端取之前要核 `placementVerdict=PASS` 与这份快照对当前套装逐格一致，判据写在 `services/bis-model.js`。
构建与分发记录：`for-mini/docs/VERIFY-小程序3D分发-2026-10-30.md`；真机加载：同目录 `VERIFY-小程序3D远端单件-2026-10-30.md`。
   注意扫描范围**不含** `bis/items.json` 的属性行——套装效果原文里就有"5% 几率"，那是游戏原文不是本站推荐。

**没有主包快照**：共享表 118 KB，而快照预算只剩 6 KB 余量，硬塞会挤掉别的通道。
所以这一页取数走线上，取不到时页面明说"这一版还没有配装名单 / 要联网才取到"，不半截显示。
**3D 那一层是占位**：一件一块、颜色跟品质走，界面上固定写"不是游戏里的样子"；
换真模型时只替换那一层（且要先过根 AGENTS.md 的素材红线）。

### 素材层（M02 起，图片不再"没传"）

`wow/{env}/v1/assets/` 下按目录分：`icons/{iconKey}.jpg`、`art/dungeons/*.webp`、`art/bosses/*.webp`、
`art/dungeonmaps/*.webp`（副本内部底图），2026-10-22 起再加界面底图四类
`keyart/*.webp`（官方宣传画）、`gen/*.webp`（本站自生成氛围图）、`art/classbanners/*.webp`、
`art/scenes/*.webp`、复用的 `art/dungeons/*.webp`，
外加一份 `assets/index.json` 台账（记每个对象的 sha256/etag/bytes/来源）。
数据里的 `art` 与 `bosses[].portrait` 存的是**相对 assets/ 的路径**（`art/dungeons/x.webp`），
图标只存 `iconKey`；绝对地址由客户端 `assetUrl()` / `iconUrl()` 拼，拼出来带 `img/`、`../` 或非 `assets/` 一律不给拼。
发素材是独立一条命令：`WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js assets --env beta`。
图片对象 immutable 一年、同名不许覆写；**台账是这批里唯一可重导的对象**（素材集一变它就得变，
把它也按不可变拦会得到一条假冲突，2026-10-22 踩过）。
反向卡口：批次里任何界面会拼出来的 `iconKey` / `art` / `portrait`，素材层没登记就直接构建失败——
"缺登记 0 条"却线上 404 这种自欺（职业图标漏登记那次）不再可能。

### 远程功能开关（2026-10-27 新增，与批次并列的一个可变对象）

真源 `wow-forever-web/app/data/flags.json` → 派生成 `wow/{env}/v1/flags.json`，
缓存语义与指针同一档（`public, max-age=60, must-revalidate`），**不在 `builds/{buildId}/` 里**。

为什么单独一个对象：`builds/{buildId}/manifest.json` 同时是回滚位，必须同 buildId 逐字节恒定；
开关是随时要拧的策略，写进去等于每次改开关换一次批次号，而且回滚一批数据会顺手把开关退回旧值。
`flags.json` 因此**不进 `BASE_INPUTS`**（那条名单是"算进 buildId 指纹的构建输入"）。

下发对象只带客户端用得上的三个字段（`on` / `name` / `note`）+ 四条 `policy`；
`needs`（这一页要哪些数据入口）与 `page` 留在仓库里给构建端校验用。实测 2.07 KB / 2 个开关。

三条命令各管一段：`flags --env beta` 只发开关（不重跑数据、不发版）；
`upload` 顺手把它对齐；`verify` 核"本地改了没发"；`rollback` 核"回滚过去那一批供不起现在开着的页"。
`oss-release-test` 里那 20 条钉着结构、预算、7 条反例，以及"只改开关 → buildId 与 155 个数据文件字节不变"。

### 专业与配方线（2026-10-27 新增，做完但默认关着）

基底 `app/data/professions.json` 是 1568 KB / 13 专业 / 1990 条配方 / 55 个采集点，
**不进主包快照、不整份下发**：

| 产物 | 实测体积 | 什么时候下 |
| --- | --- | --- |
| `professions/index.json` | 12.8 KB | 进这一页时一次（13 个专业 + 分箱 + 列名 + 出处 + 板块图键） |
| `professions/set/{id}.json` | 0.2–65.8 KB，13 片 273.2 KB | 点开哪个专业才下那一片（制皮 511 条最大） |

行是位置数组，列名 `cols` 与那份 `colNote` **只在索引里写一份**（13 片各抄一遍等于把同一句话复制 13 次）；
`icons / mats / vendors / drops / sources` 五张字典就地带一片一份（同一个商人在 500 行里重复 500 次是这份数据的主要体积）。
分片按紧凑 JSON 写（条目上的 `flat: true`）：同一份内容按缩进写会胖到 137.8 KB，纯数字数组不值这个流量。

构建时数出来写进指针的数（不抄基底 counts）：`professions 13 · profRecipes 1990 · profNewRecipes 889 · profNodes 55 · profShards 13`，
另记两个缺口：`rowsWithoutBand 29`（四箱盖不住 → 界面进"技能档位没标出来"那一箱）、`rowsWithoutIcon 14`（画自绘块，不猜图）。
卡口：基底 `counts` 与实际拆出的行数不等 → 红；配方行缺 ID 或缺名字 → 红；材料平铺数组奇数长 → 红；图标序号越界 → 红；
索引与 13 片整体扫百分比与强度/攻略词（这一页没有游戏原文那层，所以整片都能扫）。

分箱与技能四档随索引下发（`bands` / `skillKeys`），网页 `ProfessionsPage.vue` 那份字面量由 `oss-release-test` 一条 grep 对拍——
两端飘了就红，不把发布卡在一个文件的排版上。**已知数据缺陷**：钓鱼那 6 行的 `nameCn` 存的是技能数（25/75/150）、
`yields` 存的是"开始咬钩"，网页同一份基底同样错；这一页的开关因此先关着，要公开先由 wow-data 重排列映射。

### 三页卡片的毛玻璃（2026-10-23 起，2026-10-24 两轮加强）

站主指令链：「三页的卡片都加一些透明度」→「首页和副本页卡片添加玻璃效果，让页面的背景更容易看到」
→「首页、副本、职业页这 3 个页面卡片毛玻璃效果不够」。落法全在 `app.wxss` 的令牌 + 一层页面底图，
页面只引用：

| 令牌 | 现值 | 是哪一层 |
| --- | --- | --- |
| `--panel-glass` | `rgba(28, 39, 60, 0.46)`（10-23 是 0.72、10-24 第一版是 0.5/19,26,40） | 面色玻璃，比页底亮一档才有乳白感 |
| `--glass-sheen` | 顶部 2px 反光沿 + 上半 22% 一小段乳白 + 底部压暗 | 玻璃的反光与厚度 |
| `--glass-blur` | `blur(30px) saturate(180%) brightness(1.10)` | 把身后画面虚化（磨砂而不是透明的那一分） |
| `--glass-line` | `rgba(255, 255, 255, 0.22)` | 玻璃那道边框 |
| `.pagebg-ambient`（全局规则） | 同一张底图 `position: fixed` 铺满视口 + `filter: blur(26px)` | **整页环境底图**：没有它，往下滑卡片背后是纯色页底，玻璃再强也透不出东西 |

配套的 `--scrim-page` 从 0.88 松到 **0.76**：那张官方天裔图本身是亮蓝的，压到只剩 12% 时
它已经接近一块纯色。

**首页还多一条 `--scrim-home`（2026-10-26 站主：首页还是看不清背景图）**：首页第一屏约七成被卡片
盖住，整幅统一压暗时"背景"只剩卡片缝里一点暗色，所以首页改成渐变压暗——顶部 260rpx 一条只压 22%
（原图带，那一截不放任何文字，`.hero-space` 留出来、金色发丝线落在带的下沿当分隔），
260→300rpx 过渡完，往下才压到 0.70；过渡必须在倒计时卡顶边之前走完，否则卡里浅色小字掉到 AA 线下。
副本 / 职业两页顶部有直接压在页底上的浅色字（搜索框、筛选 chip），**不吃这条**，仍用 `--scrim-page`。

覆盖范围：**只在铺了页面底图的三页**——首页 `.cd` / `.entry` / `.race` / `.mini`、
副本列表 `.card` / `.drow` / `.search-input`、职业列表 `.card` / 两个阵营框 `.fac-*` / 组合卡 `.cmb`。
没铺底图的页面（副本详情、职业详情、装备详情、技能、掉落反查、指南）仍吃纯色那两份令牌。
阵营框是"阵营色染在玻璃最上层"（`--fac-*-bg` 排第一），识别通道没被换掉，有门禁看着这条。

页面 wxss 里**不许直接写 `rgba()` 与裸色值**——颜色一律回 `app.wxss`；
反光与虚化也必须是令牌，不许页面手写（`mini-m02-check` 逐条卡）。

四条边界，别当成"已经全好了"：
1. **搜索框是原生 `<input>`**，`backdrop-filter` 与渐变层作用不到它身上，只给面色玻璃；
   有门禁卡住"在它身上冒充已加玻璃"这个写法。
2. **真机没验**：虚化只在开发者工具内核量到生效（关掉它重拍一帧对照，卡内纹理 3.203→2.963），
   老内核不认时退化成"面色玻璃 + 已糊掉的环境底图"，版式不受影响。
   每页现在是"一张全屏 fixed 糊图 + 每卡一次 backdrop-filter"，**低端机帧率没测**。
3. **透出量有判据**：`mini-m02-check` 对首页倒计时卡与副本列表第一行各量一次
   "同一块卡内，铺上底图 vs 撤掉底图两帧的主色差"，判据 **10~60 级**
   （低于 10 是又糊成纯色，高于 60 是底图亮到会把字吃掉），2026-10-24 第二轮实测 27 / 20。
4. **可读性已接近下限**：逐行文字最差那档（倒计时卡底部 20rpx 说明）4.86:1，AA 线 4.5。
   再要透得先动那行小字，不能继续松压暗层。数值表见 `VERIFY-卡片玻璃效果-2026-10-24.md`。

### 界面底图（2026-10-22 起，路径只有一处真源）

清单在 **`wow-forever-web/app/data/ui-art.json`**：三个 tab 页共用的页面底图（`tabs.bg`）+ 首页四张入口卡（`home.cards`），共 5 条。
（2026-10-23 站主换图并把它从「首页专属」提成 `tabs` 一组，`home.bg` 这个键随之撤掉。）
导出层把它换成 `assets/` 相对路径塞进 **`meta.uiArt`**（`{ tabBg, cards: { dungeons, classes, loots, guide } }`）下发，
三个 tab 页各读一次 `service.loadMeta()` 拿这张地址（走 `services/ui-art.js` 一个口子，不在页面里各抄路径），**铺法与一个真 bug**：底图两层是 `position: absolute`，而 CSS 绘制顺序里**非定位元素会被 `z-index:0` 的定位层盖住**——
只给 `.wrap` 加 `z-index` 抬的是整页相对页面根，不是内容相对它自己的两个孩子，
结果名单整片被暗底糊住，DOM 量着一切正常。三页统一把内容包进 `.fg { position: relative; z-index: 1 }`；
`mini-m02-check` 两道看着它：静态查"有 `.pagebg` 的页面必须有 `.fg`"，再逐页做一次"有底图 / 无底图"亮字像素比对（差 >6% 即红）。
页面只认这一份，**不许在 wxml/js 里各写一遍路径**（`mini-m02-check` 有两条查这个：
meta 里五条都到位、且都不带 `img/` 前缀）。
分发层把这五张登记进素材台账（`build` 输出里素材从 1299 → 1303 个），缺文件会进 `assets.missing` 让构建红。
三类来路各自有清单可查：**`keyart/` 是官方宣传画**（取自官方新闻页自己的 `og:image`，
`app/img/keyart/manifest.json` 记来源、抓取日期、sha，并做了"画面里没有商标词与 logo"的自查——
**国服那张公告横幅因为烘死「魔兽世界 无限」字标而被否**，理由也记在同一份清单里，别因为
"国服就该用国服图"换回来）；`gen/` 是本站自生成的氛围图（AI）；`art/` 是客户端原画经第三方站转存。
**都不打进主包**，所以断网或没发素材时卡片回落纯色版式（`<image>` 的 `binderror` 接住，不留碎图）。

顺手登记一个素材层的重复：`art/panels/library.webp` 与 `art/panels/map.webp` **md5 相同**
（41,692 B，都是那张东部王国地图）——两条清单键指向同一张图，本轮两张都没用，等 wow-data 定改哪条。

## 三·五、客户端实际做的是哪五项校验（R1 改的就是这一层）

以前指针里写着"客户端每个文件都按 sha256 校验"，而 `oss-manifest.js` 一次哈希都没算过——名实不符。
R1 起把"说了什么"与"做了什么"对齐，**每个文件五项齐验**，任一项不符整条判失败并降级：

| # | 校验 | 期望值来自哪 |
| --- | --- | --- |
| 1 | 响应头 `ETag` == 清单记的 `etag`（服务器自己算的内容 MD5） | 入口三文件：指针 `fetch.*`；详情/掉落：索引条目 `detailEtag`/`lootEtag` |
| 2 | 响应头 `Content-Length` == 清单记的 `bytes`（有头才比） | 同上 |
| 3 | 内容自带 `buildId` == 请求所在的批次 | 每个文件都带（含 meta / glossary） |
| 4 | 内容自带 `product` / `schemaVersion` / `kind` | 每个文件都带 |
| 5 | 内容里的 ID 就是请求的那一条（详情比 `dungeon.id`，掉落比 `dungeonId`） | 索引条目的 `id` |

外加一条路径规则：分片路径由条目 `id` 现推，再与 `detailPath` / `lootPath` 比对，对不上直接拒绝、连请求都不发——
写坏一条路径也走不出 `builds/{buildId}/`。

坦白讲清边界（这段就写在 `manifest.integrity` 里，界面与文档不许说得比它更满）：
ETag 是"取回的字节是不是清单里那一份"的传输/存储完整性校验，**不是抗伪造的内容签名**，也不证明上游写的事实是对的（事实靠 provenance 与红线卡口）。
逐文件 SHA-256 由构建端算、写进 `files.json`，发布后由 `oss-release.js verify --env …` 匿名逐个回读比对——
所以 `files.json` 不进冷启动路径，客户端不必为校验多下 28.8 KB。

**冷启动代价（R1 后实量）**：指针 5,055 B + 索引 25,809 B + meta 1,829 B = **32,693 B ≈ 31.9 KB / 3 次 GET**；
整份 `dungeons.json` 是 326.7 KB，省 90%（比 R1 前多 7.7 KB，就是随索引下发的 76 个校验值）。
之后每进一本详情才多取 2.6–4.2 KB，看掉落再取 5.7 KB；同批二次打开命中缓存是 0 次请求。

## 四、四态语义（R1 把"省流量"与"离线降级"分开了）

`oss-manifest.js` 每次返回都带同一组字段：`data / source / cacheHit / buildId / factDates / requiresUpdate / pointerSource / stale / batch / error`，
`source` 只表示**这批数据是不是线上当前批**，不表示字节从哪来：

| `source` | 含义 | 界面义务 |
| --- | --- | --- |
| `live` | 指针是现取的，数据属于指针说的这一批。`cacheHit:true` 表示字节用的本机同批缓存、没重新下载（**这不是离线**） | 正常显示，配 `factDates.latest` 当"核对到"；`cacheHit` 时 `sourceLabel()` 会说"实时数据（本机缓存…）" |
| `cache` | 指针取不到（或用不了），退回本机存的上一批 | 顶部提示「离线缓存」 |
| `snapshot` | 连上一批指针都没有，用打进主包的快照 | 顶部提示「打包快照」+ 显示基准日期 |
| `none` | 什么都没有 | 说明 + 重试入口，**不许空列表冒充"这个本不存在"** |

`requiresUpdate`、`factDates`、`source` 在四种状态下**都存在**（R1 前一种情况会丢：命中同批缓存时升级信号被吃掉）。
线上指针结构非法时优先退回本地已存的好指针并标 `pointerSource:"invalid"`，不再把有缓存的用户一脚打回快照。
指针说批次 A、文件却是批次 B（或五项里任何一项不符）→ 整条判失败降级，不端给界面（`oss-release-test.js` 有对应断言）。
## 五、更新一次数据的完整动作

```bash
cd wow-forever-web
node tools/build-data.js                       # 1. 改 app/data 后必跑，非 0 就停
node tools/export-mini.js                      # 2. app/data → for-mini/oss-preview/ 四份成品（M02 起多了 spells.json）
node tools/oss-release.js build --env beta --check-identity   # 3. 切批次 + 与真源逐字节对拍 + 复现性核对
node tools/oss-release.js assets --env beta --dry-run         # 4. 先看素材层要传哪些（只读，不需要标记）
WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js assets --env beta    # 4b. 发素材：图片不可变，台账可重导
node tools/oss-release.js upload --env beta --dry-run         # 4. 先看会传哪些（只读，不需要标记）
WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js upload --env beta        # 5. 传批次 → 逐文件校验 → 最后换指针
node tools/oss-release.js verify --env beta                   # 6. 匿名回读比对哈希/ETag/字节/缓存头
WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js upload --env release --yes-release  # 7. 内测过了才发线上
node tools/oss-release.js list --env release                  # 8. 记下上一批 buildId（回滚位）
WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js rollback --env release --to <buildId>  # 出事就指回去
node tools/oss-release-test.js                 # 9. 动了产物结构就要跑，151 条断言全绿（本地夹具，不碰真 bucket）
node tools/mini-m01-check.js                   # 10. 小程序端回归（A 快照 / B live / C 篡改 / D 契约 / E 交互 / F 断网 / G 首页）
node tools/mini-m02-check.js                   # 11. M02 三个新面：技能速查、掉落反查、入口与包体（直连真 beta）
```

第 3 步现在多了一道**源与产物对拍**：构建时在临时目录用同一份 `app/data` 重跑一遍 `export-mini.js`，
四份 `oss-preview` 逐字节比一遍，不一致直接 rc=1（指针溯源写 A、实际发 B 这条路被堵死）。
对拍跑在临时目录里，`export-mini.js` 与 `oss-release.js` 会一起拷进去，**它俩读的文件也要一起拷**
（2026-10-22 导出层新读了一份 `tools/copy-banned.json`，沙箱里少拷这一个文件，报错长成"没产出 oss-preview"，很误导）。
第 5 步多了一道**不可变批次保护**：`builds/{buildId}/` 下已有同名对象而字节与本批不同时，报警停发、绝不覆盖，指针不动。
第 9 步的反例覆盖：无标记的写命令 PUT/DELETE=0、上传第 N 个 PUT 失败后旧指针逐字节不变、
回滚前目标批次缺件/哈希不符/清单 ID 不等于 `--to`/跨环境清单一律拒绝、`clean --env release` 缺 `--yes-release` 拒绝。

**写授权口径（R1 收紧）**：`upload / rollback / clean` 是写 bucket 的动作，**不论凭证从哪来**
（环境变量、`$WOW_OSS_ENV`、仓库根 `.oss-env`、还是自动兜底到 PoE 那条线的 `.env`），
都必须显式带 `WOW_ALLOW_CROSS_CREDS=1`；没带就在任何远端请求与本地落盘之前 rc=1 拒绝。
只读（`build` / `list` / `verify` / `upload --dry-run`）不需要。
`release` 在此之上还要 `--yes-release`；`clean` 还要 `--yes-clean`（撤线上两个都得加），且清后要能列举核验，
核验不了就 rc=1，不许报"删干净了"。
凭证文件**不放 `for-mini/`**：`.gitignore` 挡不住微信打包器。现在的顺序是环境变量 → `$WOW_OSS_ENV` → 仓库根 `.oss-env`；
真把 `.oss-env` 落进 `for-mini/` 里，脚本会直接拒绝并提示移位（`project.config.json` 也顺手排除了它）。
**本站口径（2026-10-21 站主拍板）**：不单建子账号，就共用 PoE 那把，所以**每条写命令都要显式带标记，
动手前先跟站主报"用哪把钥匙、写哪个前缀"**。
批次产物落 `for-mini/oss-build/`，不入库；重跑同源字节一致（清单里没有任何时间字段了）。
`oss-preview/*.json` 仍入库（是 `export-mini.js` 的成品对拍依据），`oss-build/` 只是它的切片。

无新证据不改数；每批按"新增 / 修正 / 撤回 / 仍待实测"留一句差分，记进 `ROLES.md`。

## 六、新增模块要做的事

1. 在 `oss-release.js` 的 `buildBatch()` 里加对应文件：先出索引（列表页要的轻字段 + 路径），再按 id 出详情，
   大字段（掉落、清单、图片）另开一级，别把整块塞进索引。分片粒度改了要顺手改 `BUDGET_KB`。
2. 客户端只在 `oss-manifest.js` 里加一个 `loadXxx()`，不新写请求与缓存逻辑，页面不许自己拼 URL。
3. `for-mini/oss-build/` 不进 git；`services/forever-data.js` 里那套平铺地址是过渡期的，新页面别再依赖它。
4. 素材（原画、头像、图标）走 `assets` 那条独立通道（M02 已发，见 §三）：路径带来源分类与 manifest，
   示意图要就地标"不是游戏里的地图"，并且不打进主包 —— 口径见仓库根 `AGENTS.md`。
   新界面要用一张图，就得在 `buildBatch()` 里 `useIcon()` / `useAsset()` 登记一次，
   不登记会被反向卡口直接拦下（这是对的：漏登记的表现是玩家永远看到自绘占位块，不是报错）。
5. 数据里缺字段一律显示「待实测」或「未记录」；`level=L0` 必须带官方或客户端解包来源，否则构建失败。

## 七、主包快照与预算（M01 起多了一份索引快照）

`export-mini.js` 生成四份主包快照，合计必须 ≤ 60 KB，超了直接 rc=1（2026-10-22 实测 53.6 KB，用了 89%）：

| 文件 | 内容 | 实测 |
| --- | --- | --- |
| `data/forever-glossary-snapshot.js` | 48 条词条（按 L0 优先、按类型/职业分散挑；2026-10-22 从 60 降下来给种族特长让位，理由写在 `export-mini.js` 那段注释里） | 19.2 KB |
| `data/forever-meta-snapshot.js` | meta（覆盖率、缺口、规则、**开服日期 launch**） | 1.9 KB |
| `data/forever-dungeon-snapshot.js` | **38 本副本索引全量**（断网首用也要有内容可搜） | 21.5 KB |
| `data/forever-class-snapshot.js` | 9 个职业格 + 10 个种族（含可选职业矩阵与种族特长文字），**首页第一眼要用** | 10.8 KB |

职业快照是 2026-10-22 首页改版加的：首页下面那两段（选职业 → 可选种族与种族特长）是玩家打开小程序
第一眼的内容，断网也得有，所以 `loadClassIndex()` 现在带兜底。它**只留界面渲染的字段**——
完整 `classes.json` 34.6 KB（带 lore 全文与逐条溯源）不进主包，`combos`（无限新增组合）也不进，
那一块仍然要联网才列。字段名与线上分片一致，页面代码不分两套取法。

M02 的技能（498 条 / 437 KB）与掉落反查（1,050 行 / 118 KB）**刻意不进主包**：
60 KB 预算是给"断网也得有东西可查"的副本索引的，把这两块塞进来就会把索引挤掉，
而且技能与掉落是更新最频繁的两块，打进包里等于每次改数都要发版。
所以这两页断网时明说"要联网才能取"，不给半个职业冒充全部。

副本索引快照与分发层的索引条目**逐字段一致**：`export-mini.js` 会 `require` 分发层的 `buildBatch()`，
把两边的 `items` 摘掉批次相关字段后逐字节比一遍，对不上就拒绝出快照（`oss-release-test.js` 的 3·5 节拿两条反例守着：
改分发层字段名、少 8 本，都必须红）。详情与掉落**不进主包**——38×2 份分片装不下，
所以断网点进详情时界面写"首领名单与掉落要联网才能取"，不拿索引字段冒充完整详情。

## 八、开发者工具里验 live 路径（本地假 OSS）

线上批次没发之前，live 分支怎么验？两步：

```bash
node wow-forever-web/tools/oss-release.js build --env beta            # 先出批次
FAKE_OSS_MODE=normal node wow-forever-web/tools/oss-fake-server.js    # 按真 HTTP 语义发出去（含 ETag / Cache-Control）
```

然后在开发者工具的小程序里把 storage 键 `wow_forever_v1_dev_origin` 设成 `http://127.0.0.1:8899`，
`oss-manifest.js` 的 `origin()` 就会改打本地。这个键只可能由开发者手动写进 storage：
真机上它不存在，而且微信线上域名白名单只放备案过的 https 域，`http://127.0.0.1` 在真机上根本发不出去。
`tools/mini-m01-check.js` 就是照这条路把 A–G 七组场景跑一遍的脚本（含篡改、新版本、断网）。
`tools/mini-m02-check.js` 走的是**真 beta**：M02 要验的就是素材与新分片在真环境里能不能被界面用上，
用本地假 OSS 测等于没测；它顺带对每个图标 URL 发一次真实 HEAD，看的是 200 + `image/*`，不是"页面没报错"。
换场景时**记得换端口**：批次文件的 `Cache-Control` 是 `immutable`，模拟器会照头缓存，
同一 URL 换内容它看不到——那是缓存生效，不是校验失效。

## 九、图片到底走不走域名白名单，以及 OSS 默认域名的强制下载（2026-10-22 实测）

站主问"图片是不是因为域名没配所以不显示"，把三件事分开量：

**1. `<image>` 不查白名单。** 微信只有 `request / uploadFile / downloadFile / socket / udp` 五类
API 受"服务器域名"限制；组件直接访问媒体资源（`<image src>`、`<video src>`）不需要配。
需要配 `downloadFile合法域名` 的是 `wx.downloadFile`、`wx.getImageInfo`、保存相册那类调用——
本站小程序**一个都没用**（素材只交给 `<image>` 渲染，来源网址走"复制到剪贴板"，不开 web-view）。
站主后台截图里 `request合法域名` 已含 `https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com`，
这条覆盖的是取 JSON 清单与分片，也就是 `oss-manifest.js` 里那个 `wx.request`。
所以"图片不显示"不是白名单问题；`urlCheck` 在开发者工具里是关着的，这一点也不构成"模拟器能显示就算过了"的证据。

**2. OSS 默认域名会强制下载，对象元数据改不动它。** 每个素材对象的响应都带：

```
Content-Disposition: attachment
x-oss-force-download: true
```

PUT 时显式写 `Content-Disposition: inline` 也照样被覆盖（1,117 张全部实测如此，2026-10-22）。
这是阿里云对 `bucket.oss-region.aliyuncs.com` 这类默认域名的策略，
**要真正按 inline 出图只有一条路：绑自定义域名**——而自定义域名要备案，接的是 wow-ops 那条线
（见 `wow-forever-web/docs/OPS-deploy-domain-*`）。
`<image>` 不是导航请求，一般不看 `Content-Disposition`，所以模拟器里全渲染；真机认不认只有真机能回答。

这条实测还顺手挡掉一个坑：`cmdAssets` 原本会把"远端是 attachment、我要的是 inline"当成元数据漂移，
于是**每次发素材都全量重传 1,117 个对象**。现在识别 `x-oss-force-download: true` 后不再判漂移，
并把这件事在命令输出里说一次，而不是静默重传或静默忽略。

**3. 列表页以前真的没图，是界面没用数据，不是素材没发。** 38 座里 37 座有客户端原画，
`art` 字段以前只进详情分片，索引里没有，所以副本列表整页一片空白。
现在 `dungeons/index.json` 每条带 `art`（相对 `assets/` 的路径，缺的那座是 `null` 不是空串），
主包快照同步带上——断网时列表也知道"这座本该有图"。两边逐字段对拍由 `export-mini.js` 守着。
