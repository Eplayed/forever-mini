# 数据源全景 · 我们手上有什么、缺什么（2026-10-16）

用途：站主说"先把数据源弄好"。这份是**当前所有源的实测清单**——每个源有什么、我们已经落了什么、
没落的是什么、卡在哪。数字全部来自本机文件与快照的 `meta`，不是照旧文档抄的（旧文档里有一条已过时，
见 §5 的更正）。配套的角色是 wow-data，交接建议写在 §6。

## 一、一句话结论

- **远端代码与数据已经全量到手**：本地 `main` = `a7c7ecd5` = 远端 `main`，`git status` 不领先不落后。
- **物品线是全量**：名录 21,077 件 + 详情 21,077 件逐页（0 失败），成品有详情的 20,528 件。
- **其他板块是"清单级全量、明细级按需"**：副本 38 座、任务 396 条、专业 13 类 1,990 配方、
  世界 44 区域 36 稀有 36 本书、天赋 466 节点、改动 965 条——都抓过，但抓取时间分散在
  10-11 到 10-16，**跨了三个 build**。
- **两份插件源只落了"我们当时要的三张表"**，插件里还有成就、法术、稀有坐标、任务库等没抽；
  而且 **Data.lua 原件不在这台 Mac 上**（在 Windows 那台 `D:\project\wow\`），
  要抽新表必须先拷原件过来。这是"把数据源弄好"目前唯一真正的硬卡点。

## 二、官方一手源（红线唯一能算 L0 的那一档）

| 源 | 我们取什么 | 落在哪 |
| --- | --- | --- |
| `wow.blizzard.cn/news/` 国服公告与职业深度解析 | 职业/天赋/技能的**官方中文名**、等级区间、机制说明 | `abilities.json`、`races.json`、`glossary.json`、`talents/*.json` 的 L0 部分 |
| `wow.blizzard.cn/24266320/` 在线修正 | 逐条修正记录（要整页比对才敢引用） | `docs/` 比对记录，未整表入库 |
| `news.blizzard.com` 英文回顾 / `worldofwarcraft.blizzard.com/en-us/forever` | 英文原名、上线时间 | `meta.json` 的 launch、`changes.json` 英文名 |
| 暴雪官方图标 CDN（`tools/fetch-icons.py` 只允许这个域名） | 图标字节本体（第三方只给文件名） | `src/img/icons/`（`manifest.json` 记来源与抓取日期） |

**没做的**：官方没有"物品属性/卖价"的中文页，所以物品详情天生只能走转述档，这一档到不了 L0 以上。

## 三、转述源 A：无限数据库 `wowforever.wclbox.com`（中文结构化主力）

| 快照（`src/data/upstream/`） | 抓取日 | 它自报 build | 条数 | 已进成品 |
| --- | --- | --- | --- | --- |
| `wclbox-items-index.json` 名称索引 | 10-13 | — | 21,077 | `items.json` 21,077 |
| **`wclbox-items-detail.json` 物品详情全量** | **10-16** | **1.60.1.70374** | **21,077（0 失败）** | `items-detail.json` 20,528 |
| `wclbox-items-detail-sample.json` 试采 200 | 10-14 | 70338 期 | 200 | 只作评估依据，历史留档 |
| `wclbox-changes.json` 天赋+法术改动 | 10-11 | 1.60.1.70338 | 965 | `changes.json` 965 |
| `wclbox-dungeons.json` + `wclbox-cards.json` | 10-11 / 10-13 | — | 35 座 | `dungeons.json` 38 座（另 3 团本） |
| `wclbox-dungeon-quests.json` 任务三节 | 10-13 | — | 35 座 / 407 行 | `dungeon-quests.json` 396 条、30 座有 |
| `wclbox-boss-faces.json` 首领头像 | 10-13 | — | 232 首领 / 146 有脸 | 图标与缺脸标记 |
| `wclbox-talent-<9 职业>.json` | 10-12 | — | 9×3 网格 + 对照文本 | 天赋树 466 节点 |
| `wclbox-professions.json` | 10-11 | — | 13 类 | 配方 1,990（新增 889） |
| `wclbox-world.json` / `wclbox-dungeon-meta.json` / `wclbox-legacy.json` | 10-11 | 70338 / r-1791702948979 | 7 块 / 35 / 传承 | `world.json`、`legacy.json` |

**接口边界（决定成本）**：`/_shuju/<发布号>/` 实测只有 `meta.json` / `changes.json` / `dungeons.json`
三个端点，**物品详情与天赋树没有批量接口**，只能逐页（物品 21,077 页 ≈ 3.6 小时）。
`meta.json` 会自报当前 build、开服时间、以及它自己的计数——**这份自报数是免费的对照尺**，
每次重抓第一件事就是拿它跟站内 `scale.json` 逐条比。

## 四、转述源 B：两份无限服插件（原件在 Windows，不在本机）

上游链条实测清楚了一件事：**`fc` = foreverchanges.pro（Beta 实测掉落/任务），"权威资料" = Wowhead**，
两个插件的上游高度重合，互为旁证；GI 另有一层 beta 客户端 69876 解包。

| 插件里的表 | 量级 | 我们**已抽**的吗 | 备注 |
| --- | --- | --- | --- |
| GI `gear` | 1,515 件 | ✅ → `upstream/gi-items-detail.json` 的 `src`（1,515）/属性 1,370 | 出处"本 · 首领"口径，成品里 1,501 件用这个 |
| GI `loot` | 1,875 条 | ✅（属性 st）+ 已做掉落交叉比对 2 座 | 无概率字段，红线不破；`docs/ITEMS-LOOT-CROSSCHECK-2026-10-14.md` |
| GI `DungeonQuestData` | 29 座 / 387 qid | ✅ → `upstream/gi-dungeon-quests.json` | 补了 wclbox 与 wowhead 都空的两座（挖掘场 14、达拉然 15） |
| GI `spells` | **1,480 条** | ❌ | 法术书 GAP② 的第二源（现 86 条 → 目标 420+） |
| GI `achievements` | **211 条** | ❌ | 成就 GAP③，站内连 upstream 文件都还没有 |
| GI `rares` | **338 条（带坐标）** | ❌ | 站内世界线只有 36 条"配书"口径，这是扩容材料 |
| GI `talents` | 9 职业 27 树（带 changed/same/moved） | ❌（只当交叉核对读过头） | 中文名是作者/vmangos 译名，**不能升译名等级** |
| GI `tier` / `keys` / `questSeries` / `leveling` | 18 套 / — | ❌ 存档 | 套装页未立项 |
| GI `MacroData` / `KeysRot` / `DefaultBuildsData` | 宏 / 循环 / 构筑推荐 | ❌ **不碰** | 9-24 公告敏感区 + 强度导向红线 |
| XR `Data.lua` items | 14,352 件（st/sell） | ✅ → `upstream/xr-items-detail.json`（14,331） | 现在只当兜底源：属性 1,502 件、卖价 2,258 件来自它 |
| XR `Data_QuestDB` | **5,205 条任务**（fc 全量，带等级/阵营/经验/坐标） | ❌ **明确暂不立项** | 描述/目标/完成文本三类文案不可取，剩下的裸表价值打折；站主 10-14 拍板 |
| XR `Data_Skills` / `Data_Talents` | 法术书 / 天赋内嵌 JSON | ❌ | 法术书 GAP② 的第一源，与 GI `spells` 并评 |
| XR `Data_Prof` | 286 配方 | ❌（站内专业已走 wclbox） | 作者自定的收录规矩与本站同构，可当旁证 |
| XR `Data_Bis` / `Data_DungeonGuides` / `Data_DungeonRates` | BiS / 攻略文字 / 掉率管线 | ❌ **不碰 / 本来就没数据** | 强度与攻略正文红线；掉率那张表作者也没填 |
| XR `Data_Legacy` / `Data_Codex` / `Data_PvP` / `Data_Crates` | 传承 66 项 / 图鉴 / 军衔 / 板条箱 | 部分（传承挑战 66 项已互证） | 事实性、低优先 |

**卡点**：`tools/extract-addon-items-detail.py` / `extract-gi-dungeon-quests.py` 都要传
`--gi <GearInsight_Forever/Data.lua>` 这样的**路径参数**，本机现在**没有任何 Data.lua**
（`find` 实测为空）。GI 是 5.2MB、XR 是 50MB 目录，都在 Windows 那台 `D:\project\wow\`。
所以成就、法术书、稀有坐标这三块**不是"我们决定不做"，是"原料不在手边"**。

## 五、其余源与新鲜度（含一条更正）

| 源 | 用途 | 状态 |
| --- | --- | --- |
| `wago.tools/db2` `GroupFinderActivity` CSV | 副本英文名、排队区间、一次几人 | 快照 `db2-group-finder.json` @ **1.60.1.70338**，109 条活动；非暴雪域名，只当 L1 |
| `wowhead.com/forever` | 逐本指南、天赋计算器 | **人工参照，禁止搬数据**；只有副本任务两处区域能用它补（`wowhead-dungeon-quests.json`），其余 9 个区域逐条写明为什么不能用 |
| `foreverchanges.pro` / `wowclassicforever.info` / `news.17173.com` | 线索与译名旁证 | 只当线索，整库复制禁止 |
| `github.com/cmangos/classic-db`（GPL-3.0） | 1.12 中文 locale | 只取译名与结构 |
| 网易DD `dd.163.com` | 曾评估 | **排除**：只有正式服/怀旧服，没有无限服内容（`docs/wow-infinite-sources.md` 第十、十二节） |

**更正一条（我之前在 D6 里写错了）**：台账与 `PLAN-open-items` 第 20 条写着"`changes.json`
自报已升到 965 / 753，站内还是 964 / 751 那一版"。今天实测：站内 `scale.json` 记
`changes 965 / changesNew 113 / changesModified 304 / changesRemoved 79 / changesSpellsChanged 257`，
与上游 `meta.json` 的 `all 965 / newTalents 113 / changedTalents 304 / removedTalents 79 / spellsChanged 257`
**逐条已经对上**——改动线其实早被另一台机器刷过，不是欠账。真正旧的是这几批：
名称索引（10-13）、副本卡片与头像（10-11/10-13）、天赋（10-12）、专业与世界（10-11）、db2（70338）。

## 六、按这个现状，建议的三步（不动红线）

1. **拷原件到本机（站主做，10 分钟）**：把 Windows 那台的 `GearInsight_Forever\`（5.2MB）与
   `XR_DungeonGuide\`（50MB）里我们要的 `Data.lua` / `DungeonQuestData.lua` 放到仓库外目录
   （建议 `~/Documents/project/.scratch/addon-data/`，**不提交进仓库**——那是别人的插件产物）。
   有了原件，成就、法术书、稀有坐标三块的抽取就能在本机跑。
2. **先抽成就与法术书（各一轮，产出直接进现有页）**：GI `achievements` 211 条 + GI `spells` 1,480 条
   与 XR `Data_Skills` 并评，就是 GAP②/③；抽取脚本照 `extract-gi-dungeon-quests.py` 的形状写，
   只落事实字段（id/名/等级/图标文件名/所属），描述与推荐一律不取。
3. **重抓排后，先跑一个"新鲜度体检"再决定**：`tools/data-status.py`（已有）+ `meta.json` 的自报数
   与 `scale.json` 逐条比，哪几条对不上就只重抓那几条。**物品线不用急着再抓**：
   它已经是 70374；等 11-05 开服后 build 稳定了再跑一轮（3.6 小时机器活），
   那一轮会顺带补上教益句的解包侧（`use` 字段，见 `PLAN-open-items` 第 19 条）。
