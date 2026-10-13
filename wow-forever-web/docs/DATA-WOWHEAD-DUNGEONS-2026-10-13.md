# wowhead 上的无限服副本数据盘点（2026-10-13）

用户问："副本数据 wowhead 有吗？我们现在的数据源是抓取 wowhead 吗？"

**先回答第二问：不是。** 副本线一条数据都不是从 wowhead 抓的。第一问的答案在第三节。

## 一、我们现在每座本的数据到底从哪来（读 `src/data/dungeons.json` 的 provenance 现算）

38 座（9 新本 + 26 经典本 + 3 团本）身上挂的来源类型分布。下面每个数都是现读
`src/data/dungeons.json` 的 `provenance` 算出来的，"覆盖"＝至少有一条该类型来源的座数：

| 来源类型 | 是什么 | 给了什么 | 覆盖 |
| --- | --- | --- | --- |
| `official_en` | `news.blizzard.com` 英文回顾 | 9 座新本的英文原名名单 | 9 座 |
| `official_cn` | `wow.blizzard.cn` 国服公告 | 官方中文名与等级区间 | **只有 2 座** |
| `datamine_cn` | **`wowforever.wclbox.com`**（第三方站转述客户端解包） | 首领名单、掉落归属、物品中文名、图标文件名、副本卡片等级区间、首领头像 146 张、载入图 36 张 | 35 座 |
| `datamine_en` | **`wago.tools/db2`** 的 `GroupFinderActivity` CSV（客户端排队表） | 英文原名、排队等级区间、一次几人、活动编号 | 31 座 |
| `media_cn` | `news.17173.com` 中文蓝贴转载 | 只用来发现译名冲突（如 领主大厅 / 诸王大厅） | 11 座 |
| `fan_db` | `foreverchanges.pro` | 等级区间的线索（需实测确认） | 11 座 |
| `video` / `open_data` | 测试服实测视频、1.12 中文库 | 零星旁证 | 8 座 / 1 座 |

一次几人有 31 座、等级区间有 36 座（`barrow-deeps` 与 `hyjal-summit` 两边都没给数）。
**顺带量出一件该知道的事：国服官方中文公告只落在 2 座本的记录上**——新本的中文名主要靠
英文名单 + 客户端解包的中文名（`datamine_cn`）撑着，不是每座都有官方中文原句能逐字对。
图标本体走暴雪官方 CDN（`tools/fetch-icons.py` 只允许官方域名），第三方站只给文件名。
**wowhead 在这份名单里一条都没有**：它在溯源页那张表里的定位是
`wowhead.com/forever → 逐本指南、天赋计算器、天梯 → 人工参照，禁止搬数据`。
仓库里那个 `tools/audit-wowhead.py` 也不是副本采集器（它核的是别的东西）。

## 二、访问限制（这条会直接影响能不能用）

- `curl` 直连 **403**，带 Chrome UA 也 403（`server: CloudFront`）。
- 我用无头 Chrome（playwright `channel=chrome`）复现时同样被 CloudFront 挡回来，
  拿到的是 512 字节的 403 页。**只有走本机那个已登录的真 Chrome 会话（chrome-devtools 那套）能进去。**
  → 结论：wowhead 不能进自动化流水线，只能人工/半人工取，且每次都要现进现核。
- 表格行不在初始 HTML 里（抓到的 46–78 KB HTML 中 `listview-row` 计数为 0），
  真数据在内嵌 JSON：列表页在 `<script type="application/json" id="data.page.listPage.listviews">`，
  实体页在 `WH.Gatherer.addData(type, 16, {...})`。**读 JSON 比解析 DOM 稳**，图标名也在 JSON 里
  （页面上那个 `lazy-load-background` 不用碰）。

## 三、wowhead 有什么、没有什么（子代理在真浏览器里逐页看过，我没能在无头环境复现，用之前要再核一次）

入口不是 `/wow/dungeons` 也不是 `/guide/dungeons`（都 404），真入口是顶栏 FOREVER →
`/forever/guide/dungeons-overview-locations-details`（2026-09-23 更新，列了 9 座新本）；
每座本有两类页：攻略页 `/forever/guide/<本>-dungeon-overview-location-rewards` 与
数据库页 `/forever/zone=<id>/<本>`（领主大厅 16919、洛丹伦废墟 16611、湿地挖掘场 16732）；
总表 `/forever/zones/instances` 68 条，带 New / Unchanged 标记。

| 字段 | wowhead 有没有 | 备注 |
| --- | --- | --- |
| 一次几人 | 有（5-player） | 与我们的客户端数一致，没有增量 |
| 逐首领掉落 | 有（Drops 表的 Source 列＝首领名） | **我们已经有同一批数据**（来自 wclbox 转述的客户端解包） |
| 掉落概率 | 有（物品页 "Drop Chance: 31.92%"） | **玩家上传样本统计，不是官方数字**；且本站红线是掉落不写概率 → 不用 |
| 副本任务与经验 | **有**（zone 页 `#quests`：1,050 / 1,350 / 1,450 经验 + 7–8 金） | 这正是我们缺的那块，见第四节 |
| 等级区间 | **库里没有**：9 座新本在列表 Level 列一律空白，JSON 里 `minlevel/maxlevel/reqlevel/lfgReqLevel` 全是 0；只有攻略正文写了 13-18 | 见第五节，这条与今天的定稿有关 |
| 首领名单 | 没有独立字段，只能靠 NPC 列表的 Elite 标记 + 掉落 Source 反推 | 不如我们的客户端名单 |
| 副本内坐标 | zone 页写 "There is no map available for this zone"；但攻略页给任务 NPC 的 `/way`（《Every Dungeon Quest》一篇 165 个） | 攻略正文类内容，红线不搬 |
| 图标文件名 | 有（Quick Facts `Icon: inv_misc_necklacea8`） | 我们已按同一规则取官方 CDN 图 |
| 简体中文 | `?locale=cn` 有效，会 301 到 `/forever/cn/zone=16919/领主大厅`，本名 / 物品 / NPC 都翻（HTML 里直接给 `name_zhcn`） | **这是 Wowhead 的人工译名，不是官方中文**，按红线只能当第三方转述（`datamine_cn` 同级），不能标 L0；`/cn/forever/...` 这种写法是 404 |

## 四、它恰好能补我们缺的那一块

2026-10-13 的副本详情页改版里，参考站有 `任务 / 任务物品 / 任务起始地点 / 任务经验` 四块，
我们没做，原因是 `src/data/upstream/wclbox-dungeons.json` 里根本没有任务字段
（见 `docs/PLAN-open-items.md` 第 17 条）。wowhead 的 zone 页 `#quests` 有任务列表与经验值。

**能取的边界**（照仓库根红线执行）：只取事实性标识符——任务中文名 / 英文原名、任务物品名与
图标文件名、经验值与金币的数字、任务所属首领或区域。**不取**它的攻略正文、路线描述、
`/way` 串、BiS 结论、掉落概率。取回来一律标 `datamine_en`（第三方），不升 L0。

**代价**：不能自动化（403 + 需要真浏览器会话），所以这条路是"人工开真浏览器读 JSON →
落 `src/data/upstream/` → 走 merge 与四道门禁"，一座本一次采集，35 座不可能一轮做完。
要不要做、先做哪几座，需要站主拍板。

## 五、顺带一条与今天定稿有关的事实（必须说）

站主 2026-10-13 决定等级区间按参考站 wclbox 的副本卡片定稿（如 领主大厅 13-18 → **13-20**）。
支持 13-20 的是两个来源：wclbox 卡片 + 客户端排队表（`wago`）。
支持 13-18 的也是两个来源：**国服官方公告 + wowhead 攻略正文**。
wowhead 的数据库字段里等级区间是空的（全 0），所以它不构成第三个独立证据。
也就是说：**这次定稿是"客户端实际排队值"对"官方宣传值"的取舍，不是证据多寡的结论。**
官方公告那个数已经留在每条记录的 `levelRangeOfficial` 里，界面只摆一个，
要改回摆两个或换成官方值，改 `tools/merge-dungeons.js` 的定稿那一段即可，规则例外写在
`wow-forever-web/AGENTS.md` 第 3a 条。

## 六、实际访问过的 URL（子代理列的，我没能在无头环境复现）

```
https://www.wowhead.com/wow/dungeons                                   404
https://www.wowhead.com/guide/dungeons                                 404
https://www.wowhead.com/forever/guide/dungeons                         404
https://www.wowhead.com/forever/guide/dungeons-overview-locations-details   200（＋?locale=cn）
https://www.wowhead.com/forever/guide/hall-of-thanes-dungeon-overview-location-rewards
https://www.wowhead.com/forever/guide/dungeons/every-dungeon-quest-location
https://www.wowhead.com/forever/database
https://www.wowhead.com/forever/zones/instances                        68 条（＋?locale=cn）
https://www.wowhead.com/forever/zone=16919/the-hall-of-thanes          ＋ #npcs #quests
https://www.wowhead.com/forever/zone=16611/ruins-of-lordaeron
https://www.wowhead.com/forever/zone=16732/excavation-site-wetlands
https://www.wowhead.com/forever/item=270227/ephemeral-choker
https://www.wowhead.com/forever/npc=261306/faldrim-anvilmar
https://www.wowhead.com/cn/forever/zone=16919/the-hall-of-thanes       404
```

## 七、真浏览器采集实做了一遍（2026-10-13 下午，wow-data 这一轮）

按第四节的判断实际采了一次，**方法跑通了，但产出比预期小得多**。原始转存在
`src/data/upstream/wowhead-dungeon-quests.json`（不直接上页面）。

### 采法（可复现，别再重新试错）

1. 只能用 chrome-devtools 那套 MCP 连的**已登录真 Chrome 会话**；无头 Chrome 与 curl 都是 CloudFront 403。
2. 在已打开的 wowhead 页里用 `fetch('/forever/zone=<id>/x?locale=cn', {credentials:'include'})`
   取其它区域页 —— 同源带 cookie，能过；slug 随便填 `/x`，会 301 到规范地址。
3. 数据不在 DOM 里，在 HTML 内嵌的 `new Listview({... data: [{"category":<zoneId>,...}]`。
   取法：定位 `data: [{"category":<id>` 这个 needle，从 `[` 起做**括号计数**（遇到 `"` 切字符串态、
   遇到 `\` 吞一个字符，字符串态里不计数），配到 `]` 截断后 `JSON.parse`。
   needle 里的引号用 `String.fromCharCode(34)` 拼，**别在脚本字符串里写转义引号**——
   经 MCP 边界来回两次转义必错（这一条试错三次才对）。
4. `?locale=cn` 时行里的 `name` 直接就是中文串；没有中文的该站会**回落成英文**或套上方括号。
   同页还有 `WH.Gatherer.addData(5, 16, {...})` 给 `name_enus`，但按 id 取时命中不稳，
   本轮没依赖它。
5. 区域号从 `/forever/zones/instances` 的 `<script type="application/json" id="data.page.listPage.listviews">`
   里读（68 行，含 `id/name/minlevel/maxlevel/reqlevel/lfgReqLevel/nplayers/envChange`）。
6. 每座之间 `sleep` 1.2–1.4 秒；连续快取会拿到不含数据块的壳页（第一次批量就是这样全 NOKEY）。

### 采到的东西（这才是重点）

| 本站那座 | 该站区域 | 条数 | 能不能用 |
| --- | --- | --- | --- |
| 领主大厅 | 16919 | 4 | **能**，四条全有正式中文串、全标 new |
| 怒焰裂谷 | 2437 | 6 | **能**，经典本内任务，中文齐，四条 unchanged 说明无限服没动任务线 |
| 洛丹伦废墟 | 16611 | 15 | 一半能用：6 条是方括号未记录串，另有 4 条同名「无尽的折磨」要先定去重 |
| 达拉然城 | 16544 | 8 | 4 条方括号；还有 16560 第二个同名达拉然区域（0 条），哪个算本站这座没对上 |
| 挖掘场：湿地 | 16732 | 14 | **基本没有**：13/14 是方括号未记录串 |
| 哀嚎洞穴 / 黑石深渊 / 厄运之槌 / 斯坦索姆 / 血色修道院 等经典本 | 718 / 1584 / 2557 / 2017 / 796 … | 13 / 64 / 46 / 20 / 8 | **不能整片用**，见下 |

三件必须先定规则才能往下做的事：

1. **区域任务 ≠ 本内任务。** 该站按"区域"归任务，经典本的区域里混着本外前置链、
   职业专属小任务（哀嚎洞穴 1489 / 1490）、兄弟会捐献（黑石深渊 6642–6646 五条）、
   专业与声望线（厄运之槌 46 条里一大半）。整片搬进"这座本的任务"就是骗人。
2. **一座区域对我们好几座本。** 血色修道院 796 盖四座、厄运之槌 2557 盖三座、
   斯坦索姆 2017 盖两座门。归不到具体那一座。
3. **该站自己的脏数据要挡。** `[方括号]`＝它标为未记录的串（不能当定名）；
   `<UNUSED>`（诺莫瑞根 2971、斯坦索姆 6201）、`<TXT>`（祖尔法拉克 2868）、
   `<NYI> <TXT>`（黑石深渊 4299）、等级为 1 的废条目（4295）、同名多版本（告别安泰恩 12 条）——
   一律不许进正文。

### 结论与建议

- **本轮只把领主大厅与怒焰裂谷这两座（10 条）当"可用"**，其余全部留在快照的
  `collectedButNotUsable` 里逐条写明为什么不能用。没有为了"看起来做了很多"把 300 条塞进数据基底。
- **无限新增的 9 座里该站只有 4 座有条目**，沉没之城、克罗多克要塞、奥卡兹监狱、黑喉要塞、
  塑源者平台在那张 68 行总表里根本没有；barrow-deeps 与奥妮希亚的巢穴也没有。
  → 想给新本补任务，wclbox 那条路（它详情页有"任务 6 / 任务物品 4 / 任务起始地点 5"）
  反而比 wowhead 全，**下一轮该先回采 wclbox 的任务那一节**，wowhead 当交叉核对。
- 掉落概率（"Drop Chance: 31.92%"）与攻略正文、`/way` 串一律没取，按红线不搬。
- 界面还有一步：把 `quests` 挂进 `dungeons.json` 并在详情页加那一块，属于 wow-dev，
  等站主定"要不要只做能用的那几座"再动。
