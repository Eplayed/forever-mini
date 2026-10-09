# 《魔兽无限》数据源盘点（2026-10-06 实测）

配套文档：`wow-infinite-plan.md`（定位与红线）、`wow-infinite-workflow.md`（工作流程）。本文只回答一件事：**每一条数据该从哪儿拿、能不能真拿到、拿来当什么角色。**

所有结论都经过实际访问验证，标明"可直读 / 需浏览器渲染 / 拿不到"。

---

## 〇、两个必须先纠正的认知

1. **英文官方名是 `World of Warcraft: Forever`，中文才叫《无限》。** 用 "Infinite" 检索英文源必然落空，所有搜索词、URL、仓库名都要按 Forever 来。
2. **`wow.com` 这个域名不存在。** 官方英文新闻中枢是 `news.blizzard.com` / `worldofwarcraft.blizzard.com`。

---

## 〇·补、按"到底是不是无限服的源"重新分类

我们只做无限服，所以这个分类比可用性更重要——**下面 B 类看着能用，其实说的是另一个游戏版本，直接当事实源会出错。**

### A 类：真·无限服专属（可直接采）

| 源 | 无限服内容形态 |
| --- | --- |
| `wow.blizzard.cn` 无限相关正文 | 官方中文译名（职业深度解析、座谈会）、系统规则、Beta 时间与 2 座地下城名 |
| forever 专页（中/英，含 `camelotInitialState` JSON） | 3 个新区域、露营、传承、规则集、定档时间 |
| `news.blizzard.com` / `worldofwarcraft.blizzard.com` 的 Forever 文章与 WoW Weekly | 官方英文口径，新闻级 |
| 17173 的无限转载（30 级蓝贴、副本经验改动、团本掉落爆料） | **中文唯一成体系的 14 座地下城名清单** |
| `foreverchanges.pro` | 9 座新本名单与 new/classic 标记、传承点与 BiS 页目录（内容颗粒度见 D 类，已下调） |
| GitHub 上 Forever 专属库（Napalmsteak `Forever Cache.json`、`eelliott4517/forever-loot`、`TylerAkins/forever-guide-mate`、`Stein-N/WoW-Quest-Database`） | 无限服物品与掉落，但**无授权，只读不存** |
| B站无限 beta 实测 18 条、贴吧魔兽世界无限吧 | **唯一能碰到无限服一手掉落与机制的源** |
| `us.forums.blizzard.com` 的 `search.json` | 玩家 beta 反馈（UGC，读完自己重写） |

### B 类：不是无限服的源（只当历史底表与校验，禁止当事实源）

| 源 | 它实际是什么 | 允许的用法 |
| --- | --- | --- |
| **`cmangos/classic-db`** | **1.12 经典旧世**，不是无限服。无限服改过职业、也改过经典本掉落 | 只用两样：老国服客户端的中文叫法（装备/怪物/任务译名），以及经典本的英文原名与基础结构。**掉落与数值一律不采信** |
| `Hoizame/AtlasLootClassic`、`dkpminus/Classic-WoW-Database`、`classicdb.ch` | 全部经典服，**零无限服内容**（classicdb.ch 已实测确认） | 译名与结构参考 |
| 17173 的"副本数据库/查掉落"模块、游民 handbook、TGbus/当乐/好游快爆 | 经典服或 2008 年代问答，**无无限条目** | 不用 |
| `render-us.worldofwarcraft.com/icons/` | 官方图标服务，老物品可取；**无限服新物品图标能否取到未证实**（foreverchanges 自己只用站内路由） | 先拿 1 个无限服新物品实测，不通就自绘 |
| 用 "Infinite"、"魔兽世界60级"、"怀旧服" 等关键词搜到的一切 | 怀旧服、时光服、私服内容混进来 | 一律过滤 |

**战略含义值得记一笔，但已按本轮核实修正**：中文侧**没有无限服专用的"数据库级"站点**（没有可查询的副本/掉落/物品库），但**已有成篇中文攻略与可交互天赋模拟器**（百家号 2026-09-14 的"无限天赋树模拟器（公众号直达版）"、3dmgame 与 52pk 的职业/种族天赋文章、疑似中文的 pigtogo 天赋模拟器）。所以这不是空白赛道，而是"有文章、没有工具化资料库"的空档——我们的差异点必须落在**结构化可查询 + 微信内随手打开 + 清单可勾选分享**，而不是"中文第一人"。

### C 类：与无限服相关但够不着

Wowhead 全系（理论上是最强的无限服数据库，但 Cloudflare 403 + 中文站按国家屏蔽，我们拿不到）、NGA、抖音、官方微博、微信公众号、Reddit、BlizzCon YouTube 回放、MMOChampion / Icy-Veins / WarcraftTavern / wiki.gg。

### 防"串味"的三条硬规矩

1. **每条数据必须记数据口径**：build 号或采集日期（例如 foreverchanges 自述是 "level 30 build of Oct 1"，beta 号 `1.60.1.70235`）。没有口径的条目不进正文。
2. **经典本不等于无限服里的经典本**。凡引用 1.12 数据的条目，字段里标 `basis: "classic-era"`，上线后优先重核。
3. 采集关键词必须同时满足：含 Forever 或"无限"、发布于 2026-09-01 之后、排除"怀旧 / 经典旧世 / 时光 / 私服 / GTW"字样。

---

## 一、源清单与可用性

### A 类：国服官方（定名、定规则，唯一权威）

| 来源 | 能拿到什么 | 访问方式 | 代表 URL |
| --- | --- | --- | --- |
| 新闻列表页 | 标题+摘要+日期+URL 全在 DOM，"浏览更多"是 Vue 局部加载 | 需浏览器渲染 | `wow.blizzard.cn/news/index.html` |
| 职业深度解析（猎人/德鲁伊篇等） | **上百条技能与天赋的官方标准中文名**（瞄准射击、野性成长、掠食者之锋、陆行鸟踢击），约 2800 字纯长文 | **可直读** | `/news/24301515/index.html`、`/news/24301514/index.html` |
| 深度解析座谈会回顾 | 系统名与装备名官方口径（露营系统、传承天赋树、石猪剑、尊贵法袍、拉迪莫尔家传指环），约 3200 字 | **可直读** | `/news/24303313/index.html` |
| Beta 开启公告 | 等级上限、时间，**地下城只提到 2 个**：领主大厅(13–18)、洛丹伦废墟(15–20) | 可直读 | `/news/24304160/index.html` |
| **在线修正栏目** | **已包含无限条目**（页面出现"'无限'11月5日全球同步上线"），按日期排列、**无版本号、列表不能翻页** | 可直读 | `wow.blizzard.cn/24266320/index.html` |
| forever 专页 / H5 | 只有定档 11-5 与"测一测找队友"互动页，**无任何资料** | 可直读 | `/forever/` |
| 结构化接口 | **没有**：`list_js` 里挖不到 `api/`、`.json`、`getNewsList`，无 XHR | — | 只能翻页抓 HTML |

用途定位：这一类**不给内容，只给名字和规则**。它最大的价值是当"中文标准术语表"的种子，后面所有译名都要拿它来映射。

**上线后要重点盯的是在线修正栏目**：正式服每次改动都会落在这里，等于我们的"数据过期报警器"。但它无版本号、列表不能翻页，所以不能做增量抓取，只能整页取回后比对文本差异——采集脚本必须按这个现实写。

### B 类：官方英文（补 A 类缺的英文原名）

- `en-us/forever` 专页可直读，给出 **3 个新区域**（Zephras Isle / Riverglades / Mount Hyjal）、Legacy、露营、规则集、住房；**仍无 9 座地下城名单**。内容埋在页面 HTML 的 `camelotInitialState` JSON 里，可解析——这是官方页面少见的结构化入口。
- 主文 24302093、Beta 公告、WoW Weekly 24304074：可直读，但只有预购档位和宣传口径，**平衡改动条目为 0**。
- `us.forums.blizzard.com` 的 Discourse `search.json` 开放可查（是玩家帖，不是蓝贴）；`eu.forums` 返回 429。
- BlizzCon 2026 官方回放：本机连不上 YouTube，**未证实**。

### C 类：中文转载（唯一成体系的中文副本清单）

| 来源 | 情况 |
| --- | --- |
| **17173 魔兽专区** | **可直读**，价值最高。蓝贴转载（`news.17173.com/content/10042026/085128391.shtml`）列出 **14 个地下城中文名**：挖掘场：湿地、剃刀高地、奥达曼、怒焰裂谷、诸王大厅、洛丹伦废墟、哀嚎洞穴、死亡矿井、影牙城堡、监狱、黑暗深渊、诺莫瑞根、血色修道院。另有副本经验改动/团本掉落爆料（`/content/09162026/160632951.shtml`）。但它的"副本数据库"模块只覆盖经典服，**无无限条目** |
| 游民星空 | 仅资讯，handbook 搜索页 404 |
| TGbus / 当乐 / 好游快爆 | 只有 2008 年代的"掉落怎么查"问答，**无无限数据页** |
| 网易大神 | 需浏览器渲染，单帖正文可读，但示例内容是团招募，非资料 |

### D 类：英文专库（线索源，不能当事实源）

**`foreverchanges.pro`** —— 英文侧唯一能直读的 Forever 专库，但**实际颗粒度远低于它的名气**（2026-10-06 逐页核实）：

- 有：9 座新地下城名单与等级区间（Hall of Thanes 13–18、Ruins of Lordaeron 15–20、Excavation Site: Wetlands 26–31、City of Dalaran 28–33、The Drowned City 35–40、Krol'dok Stronghold 40–45、Alcaz Prison 48–53、Blackmaw Hold 55–60、Shaper's Terrace 58–60），以及每本的 `new` / `classic` 标记；导航里有 Talents、Spellbook、**Legacy perks（传承系统）**、Tradeskills、**BiS list**、Hidden items 等专页入口
- **没有**：BOSS 等级、掉落概率、成体系的机制攻略；掉落大量标注 "not known yet"，机制只有零碎注记（例："Arcane Bolt and Focal Blast, a beam."）
- 经典本只打 `"Classic Era client data"` 标签，并明确写区间"未对 Forever 确认"，**不发布经典本的改动记录**
- 数据口径：页脚注明来自 **"level 30 build of Oct 1"**，并自述 "unofficial fan site, not affiliated with Blizzard"
- 图标全部走它自己的站内路由（`/wow-ui/reference-art/...`），**没有引用官方 CDN**
- 限制：Terms 禁止整库复制

定位因此要下调：**它是"名单与目录"级别的线索源，不是"手册内容"级别的替代者**。真正能告诉我们去哪看、看哪个 BOSS，但内容和它的 BiS 表都必须我们自己实测重建。

其余英文站基本被封：Wowhead（www/classic/a/static/webapi/blue-tracker **全部 Cloudflare 403**，中文站还按国家屏蔽）、MMOChampion、Icy-Veins、WarcraftTavern、`warcraft.wiki.gg`、io9 均 403；PCGamer 200 但只有新闻；`classicdb.ch` 200 但**零 Forever 内容**；Tenfold Junkie、SeasonZero 域名不通，未证实。

### E 类：开源数据集（60 级基础层可以不写爬虫）

| 仓库 | ★/许可/更新 | 能用在哪 |
| --- | --- | --- |
| **`cmangos/classic-db`** | 203 / **GPL-3.0** / 2026-09-23 | **最适合当 60 级基础层种子**。有 `Full_DB/ClassicDB_1_12_1.sql.gz`，含 `creature_loot_template`、`gameobject_loot_template` 掉落关系表，**还有 `locales/Chinese/{item,creature,quest,gameobject}.sql`** |
| `Napalmsteak/WoW-Classic-Item-Caches` | 1 / **无 License** / 2026-10-04 | 唯一含 Forever 的成品库：`Forever Cache.json` 9,667 物品、`itemDatabaseSources.json` 582 源（Forever 37 条含 9 新本与 Barrow Deeps/Hyjal/Onyxia）、`icons/` 6,206 张 36×36。源自 Wowhead tooltip，**无授权 → 只做比对，不入库** |
| `eelliott4517/forever-loot` | 0 / 无 License | `Data.lua` 1.75 MB，Forever BOSS→掉落，同样只作线索 |
| `Hoizame/AtlasLootClassic` | 90 / GPL-2.0 / 2024-06 | 经典掉落与 rate 参考 |
| `Stein-N/WoW-Quest-Database` | 1 / GPL-3.0 / 2026-10-05 | 明确支持 Classic + Forever 的任务 ETL，**管线设计值得参考** |
| `dkpminus/Classic-WoW-Database` | 12 / Unlicense / 2018 | 公有领域但太旧 |
| `thespags/WoWDbScripts`、`TylerAkins/forever-guide-mate` | 5 / 2 | 抓取脚本、Forever 路线逻辑参考 |

`wago.tools` 站点 200，但 CSV 导出返回 HTML 壳（疑似需登录），**bulk 导出未证实**。

**这里有一条超出预期的收获，但要加限定**：`cmangos/classic-db` 的 Chinese locale 来自 1.12 老客户端，也就是**当年国服客户端自己的中文文案**。对经典 60 级的装备、怪物、任务**名字**，它比任何第三方站都权威，直接解决你 POE1 上踩过的"新英文残留只能硬造"那个坑。

但它是 1.12 口径：无限服改过职业、也改过经典本掉落，新副本新 BOSS 它完全没有。所以**只用它的译名和结构，不用它的掉落与数值**（见〇·补 B 类）。

### F 类：视频与图文实测（Forever 独有内容的唯一来源）

B站搜索（`order=click`）可直读，实测已筛出 18 条具体条目，**但 CC 字幕全部为空，必须自己 ASR**：

- 结构化信息最有用的一条：[挖掘场：湿地实测+BOSS攻略](https://www.bilibili.com/video/BV15pHi6SE5i/) 1611 播放/04:57，2026-10-03，简介含跳怪路线、潜伏者灭团点、12 格背包与 PVP 饰品二选一
- [洛丹伦废墟 BOSS 掉落（不完全版）](https://www.bilibili.com/video/BV1uFet62Ei9/) 6299/00:42，2026-09-19
- [洛丹伦废墟隐藏 BOSS 与刷新位置](https://www.bilibili.com/video/BV1tJhh6UERb/) 6861/05:11
- 高播放但主观为主：实战画面新 BOSS 10.6 万、沉没之城实机 7.7 万、达拉然副本实机 7.5 万/09:35、副本经验大砍+BOSS 掉超模神装 2.9 万、坏木杨情报系列（大元帅装备/传承系统/贸易局配方/30 级上限）2.5 万
- 其余：隐藏 boss 1.3 万、尖牙套装变身、20 级防战单刷死亡矿井、单刷监狱、死亡矿井完整路线

结论很直白：**中文实测内容的结构化程度只到"简介级"，掉落和技能名藏在实机画面里。** 光 ASR 不够，还需要对关键帧做 OCR（游戏内 tooltip、掉落列表文本），这是新增的一项能力。

贴吧有独立的**魔兽世界无限吧**，未登录浏览器渲染即可读列表与正文摘要（时光徽章、术士练级天赋、版本评价 45 回复），但内容以主观体验为主，**无掉落表**，当需求线索用。

### G 类：图标

`render-us.worldofwarcraft.com/icons/56/*.jpg` **200 可直读**（物品图标与 `achievement_boss_*` 都能取到），比 Wowhead 系 CDN 稳；`render-br` 不通。但这是暴雪美术素材，落到小程序仍要转存自有备案域名，且保留"整体替换"的回退方案。`foreverchanges/icon/*.jpg` 与 Napalmsteak 的 `icons/` 都不可搬。

### H 类：拿不到的（别再投时间）

NGA（`fid=401` 返回"账号权限不足"，`read.php?tid=` 未登录空壳，WebFetch 403）、抖音（`__ac_signature` 验签壳）、官方微博（302 到 passport visitor）、微信公众号"魔兽世界"（搜索拿不到 mp 直链）、Reddit（本机不可达，且 UGC 是禁商用授权口径，只能读完自己重写）、头条文章（重定向后 404）、Wowhead 全系、BlizzCon YouTube 回放。

---

## 二、中文侧完全没有的四类内容

这四类决定了这活儿的工作量，别指望从任何站直接扒：

1. BOSS 技能名与机制清单
2. 物品级掉落表（装备 → BOSS → 装等 / 概率）
3. 9 座地下城的官方完整名单与中英原名对照（官方只提到 2 个，其余靠转载和英文专库拼）
4. 跑图路线坐标

补法：英文专库给"去哪看"的线索 → B站实测视频 ASR + 关键帧 OCR 给血肉 → 官方中文文章做译名映射 → 两源一致才进正文。

---

## 三、译名冲突已经出现了，举例说明处置

同一个地下城，官方 Beta 公告写 **领主大厅**（13–18），17173 蓝贴转载写 **诸王大厅**（对应英文 `Hall of Thanes`）。这就是工作流第 5 步要拦的东西。

处置规则：官方站原文优先，转载只当线索；两者不一致时正文取官方措辞，另一说法进 `conflicts.json` 等实测定夺；官方从未公布译名的（9 座本里 7 座都属于这种），**保留英文名并记 `verifiedAt`，禁止逐词硬造**——沿用你 POE1 那条门槛精神。

另一类口径风险：**掉落不要写百分比**。Forever 页上写的是"beta 玩家所见"，不是概率；cmangos 的 `chance` 字段是模拟器估值，也不是暴雪数值；而且 Forever 改动了经典本掉落。前台只出"来源＝某本某 BOSS"，要写概率必须等 patch notes 与正式服大样本双源一致。

---

## 四、接入顺序（对应工作流第 1–4 步）

| 顺序 | 动作 | 产出 | 成本 |
| --- | --- | --- | --- |
| 1 | 抓 A 类官方中文正文建**术语表**（技能/天赋/装备/系统/地名，中英对照） | `base-data/wow/glossary.json` | 我跑，1–2 小时 |
| 2 | 拉 `cmangos/classic-db` 解 Chinese locale + loot template | 60 级基础层：装备名/怪物名/掉落关系 | 我跑，2–3 小时，机器为主 |
| 3 | 用 D 类专库拼 **9 座本名单与 BOSS 骨架**，只做线索登记 | `dungeons_skeleton.json`（每本带英文原名、等级区间、来源） | 1 小时 |
| 4 | B 类英文专页解析 `camelotInitialState`，补 3 区域/系统英文原名 | 术语表补充 | 0.5 小时 |
| 5 | F 类：挑 15–20 条 B站视频 → ASR + 关键帧 OCR → 抽取 | 逐本草稿 + 冲突清单 | 机器 3–4 小时；**OCR 是新能力，要先做可行性** |
| 6 | E 类无授权库（Napalmsteak / forever-loot）**只做比对**，验证第 5 步抽取对不对 | 比对报告 | 0.5 小时 |

第 5 步里的**关键帧 OCR 是本盘点暴露出的最大未知项**：现有 video2text 是 ASR 产线，掉落表和技能名在画面里不在语音里。开工前要先拿一条视频验证能不能截到清晰的 tooltip 帧，这条不成立，F 类内容的颗粒度就要降级到"机制描述级"。

---

## 五、国际侧实测（2026-10-06 二次核实，用真实浏览器）

第一轮用 WebFetch 打这批站点时大量返回 403，改用本机浏览器后结论翻转。**关键前提：以下可达性依赖你这台机器的出网通道，不能写进自动化管线**（详见本节最后的约束）。

### 5.1 最大发现：Wowhead 有完整的 Forever 专区，且可访问

`wowhead.com/forever` 不是新闻页，是一整套针对无限服的资料站，实测能读到的分区：

| 分区 | 实测到的内容 |
| --- | --- |
| Talent Calculator | **每职业独立计算器** `/forever/talent-calc/{druid,hunter,mage,...}` |
| Dungeon Guides | 逐本指南，导航里直接出现 `The Hall of Thanes`、`Ruins of Lordaeron`，还有 Dungeons Overview、Every Dungeon Quest、Challenge Mode、Mythic+、Delve、Scenario |
| Class Guides / Tier Lists | 按专精到"30 级 DPS/治疗/坦克速览"级（如 balance/druid/level-30-dps-overview），另有 DPS / Healer / Tank 三张天梯 |
| 系统指南 | **Camping Overview & Unlock Rewards**、**Legacy System**、Beta Content Unlock Overview、Leveling / Quest / Reputation / Profession / Raid / Pet Battle 全套 |
| News（更新极快） | 直接跟 beta 改动：副本任务经验被砍、圣骑士补了嘲讽、剥皮不再是团队共享、藏书任务项链奖励砍成优秀品质、30 级交书的	new 奖励、天裔德鲁伊飞行形态、地精武器被削等，一天十几条 |
| Blue Tracker | 收录暴雪官方帖，含 **"WoW Forever Beta Development Notes (updated 1 October)"** 与各国服 beta 维护公告 |

也就是说：**中文侧完全缺失的四类内容（BOSS 机制、掉落、副本名单、路线），国际侧不仅存在，而且已成体系。**

### 5.2 官方英文名单与粉丝库有名称冲突

暴雪官方"What's Next"座谈会回顾里，9 座新本名单是：Hall of Thanes、Ruins of Lordaeron、**Whelgar's Excavation**、City of Dalaran、Blackmaw Hold、the Drowned City、Krol'dok Stronghold、Alcaz Prison、Shaper's Terrace。

而 `foreverchanges.pro` 和 Wowhead 的新闻标题都写作 **Excavation Site: Wetlands**。同一座本两个英文名，需要在正式服实测后定稿——这类冲突也必须进 `conflicts.json`，不能想当然。

### 5.3 其他 Forever 专用站（都可读，都只有线索价值）

| 站 | 实测情况 | 定位 |
| --- | --- | --- |
| **`wowclassicforever.info`** | 粉丝自制资料站，**内容最像数据库**：`/dungeons/`、`/raids/`（9 新本 + 3 团本）、`/sets/`、`/talent/{职业}/` 天赋模拟器、`/beta-datamine/new-items/`（标称 **4,809 新物品、4,963 新法术**），有 `/zh-hans/` 简中路由，日志更新到 2026-10-07，无付费无注册 | 找条目、对存在性。**Terms 未授权转载** |
| `lfcarry.com` | 无限服攻略页齐全（副本路线含 Hall of Thanes、露营机制、职业布阵、团本推进、任务追踪、天赋计算器、传承点树、职业专业 600+ 配方），每篇带"Updated 2026-09-29"，全开放；但**只写"源自暴雪 BlizzCon 座谈会"，不写数据口径**，页面下方带货代练服务 | 只当二手转述与查漏，不当事实源 |
| `classicwowforever.com` | 自述"独立粉丝回顾，非暴雪官方直播记录"，有团队规模规划、地下城分级、天赋树架构、部分职业词条，**缺完整掉落表与数值公式**，更新于 2026-09-22 | 同上 |
| `foreverchanges.pro` | 见第一节 D 类，名单与 new/classic 标记，掉落大量"not known yet" | 目录线索 |
| `pigtogo.cn/talents/forever/` | 中文"永久服天赋模拟器"，WebFetch 只拿到 JS 壳，**内容未证实** | 待浏览器复核；这是**中文竞品信号** |
| App Store `id1593368066` | 有名为 "WoW Forever Talent Calculator" 的 iOS 应用 | 竞品信号，未核 |
| `us.forums.blizzard.com` | Discourse `search.json` 开放，能查玩家 beta 反馈帖 | 需求线索（UGC，读完自己重写） |

`news.blizzard.com` 侧可直读：`What's Next` 回顾（24303862）、BlizzCon 2026 开幕式汇总（24301453）、WoW Weekly；`worldofwarcraft.blizzard.com/zh-cn/` 也存在（国服以外的简中官方页，可作为官方简体中文术语的第二来源）。

### 5.4 由此产生的三条硬约束

1. **不能把任何一站的数据搬进产物。** Wowhead 有 Terms of Use 和明确的数据库版权主张，`foreverchanges`/`wowclassicforever` 禁止整库复制，无 License 的 GitHub 库只能读不能存。**定位统一为"对答案的参照系"，不是数据源。**
2. **不能让管线依赖出网通道。** 这次 Wowhead 可达是走了你这台机器的网络；之前的直接抓取是 403，中文站还按国家屏蔽。爬虫排进日常任务的话，通道一断就全线停摆，还叠加规避地区访问的争议。所以自动化只跑官方中文站与自建录入，参照系靠人工查。
3. **资料"更全"不再是卖点。** 英文侧已经有天赋计算器、逐本指南、天梯、任务清单，硬核玩家本来就在看。我们这款产品的立足点必须收窄成：**中文 + 微信里随手打开 + 开荒清单可勾选可分享**，而不是"资料最完整"。

### 5.5 对工时估算的修正（往好的方向）

原估每本 40–90 分钟人工校对，其中很大一块是在"从零猜有什么内容"。现在有了参照系，流程改成：拿参照系列出每本的 BOSS/掉落候选 → 官方中文文章定名 → 关键实测视频或自玩确认 → 只重写我们自己要展示的字段。**预计每本降到 20–40 分钟，且缺漏风险显著下降**，代价是多一道"参照系核对"的人工步骤（不允许脚本代劳）。

---

## 六、许可与合规注意

- `cmangos/classic-db` 是 **GPL-3.0**：用作内部整理与交叉校验没问题，但不要把它的数据文件原样打进小程序产物；字段自己重排、中文文案来源在 evidence 里留痕。
- **无 License 的仓库（Napalmsteak、eelliott4517）只能读、不能存、不能搬**，代码和数据结构可以参考，数据本身没有授权。
- `foreverchanges.pro` Terms 禁止整库复制，只作线索源，条目需自有实测支撑。
- 暴雪美术素材（图标、截图）：小程序端以自绘/几何占位为主，官方图标转存要预留整体替换方案。
- Reddit/贴吧/NGA 等 UGC：读完自己重写，不复制文本与截图；个人主体本来也不能展示用户内容。

---

## 七、数据源总表（按你要的类型列，含用法标签）

标签含义：**入库**＝可以进自动化管线；**人工参照**＝只能人看、人抄，不写爬虫；**线索**＝只用它告诉我们去哪找；**不用**＝够不着或不该碰。

### 7.1 官网类（唯一权威，全部可入库）

| 源 | 有什么 | 标签 |
| --- | --- | --- |
| 国服官网新闻栏目 `wow.blizzard.cn/news/` | 无限职业深度解析（官方中文技能/天赋名）、座谈会回顾（系统名/装备名）、Beta 公告（时间与 2 座本名）、旧影拾遗（地名） | 入库 |
| 国服**在线修正**栏目 `/24266320/` | 已含无限条目；上线后的改动都在这；无版本号、不能翻页 | 入库（整页比对） |
| 国服 forever 专页 `/forever/` | 定档时间、测试信息、"测一测找队友"H5 | 线索 |
| 国际官方 `news.blizzard.com/en-us/article/{24302093,24303862,24301453,24304074}` | **9 座新本官方名单（英文）**、What's Next 回顾、BlizzCon 汇总、WoW Weekly | 入库 |
| 国际 forever 专页 `worldofwarcraft.blizzard.com/en-us/forever`（含 `camelotInitialState` JSON）与 `/zh-cn/` | 3 个新区域英文名、Legacy/露营/规则集；简中官方页可作第二译名源 | 入库（可解析） |

### 7.2 官方论坛类

| 源 | 情况 | 标签 |
| --- | --- | --- |
| 美服官方论坛 `us.forums.blizzard.com` 的 `search.json` | **匿名可访问**，能拿到 Forever 相关主题列表（标题、日期、回复数，10-07 仍有新帖），但**取不到正文全文**，本轮结果里也没见蓝贴 | 线索（需求监测） |
| 欧服论坛 `eu.forums` | 429 | 不用 |
| 国服官方论坛 | 无独立论坛，官方沟通走新闻稿 + 游戏内 + 网易大神 | 不适用 |
| 蓝贴/开发说明 | 无限服 Beta 开发说明（"Beta Development Notes, updated 1 October"）实际是**通过 Wowhead Blue Tracker 和 17173 中文转载**才成体系看到的 | 人工参照（原文尽量回官方渠道取） |

### 7.3 第三方资料站/数据库

| 源 | 有什么 | 标签 |
| --- | --- | --- |
| `wowhead.com/forever`（真实浏览器可达，脚本 403） | 每职业天赋计算器、逐本副本指南、按专精 30 级速览、三张天梯、露营/传承/解锁总览、任务/声望/专业/团本全套、beta 改动新闻流、Blue Tracker | **人工参照**（禁止搬数据） |
| `wowclassicforever.info` | `/dungeons/`、`/raids/`（9 新本+3 团本）、`/sets/`、天赋模拟器、`/beta-datamine/new-items/`（4809 新物品、4963 新法术），有 `/zh-hans/`，更新到 10-07 | 人工参照 |
| `foreverchanges.pro` | 9 新本名单与 `new`/`classic` 标记、传承点与 BiS 页目录；掉落大量"not known yet" | 线索 |
| `lfcarry.com` | 无限服攻略面很全，但只标"源自 BlizzCon"、无数据口径，带货代练 | 线索 |
| `classicwowforever.com` | 自述粉丝回顾，地下城分级、天赋树架构，缺掉落与数值 | 线索 |
| 中文综合游戏站 | `ol.3dmgame.com`（无限职业天赋）、`wow.52pk.com`（无限种族天赋）、腾讯新闻/网易/头条的蓝贴中文转载（头条有反爬 404） | 人工参照（可作译名旁证，不可当事实源） |
| 17173 `wow.17173.com` / `news.17173.com` | **中文唯一成体系的 14 座地下城名清单**（30 级蓝贴转载）＋副本经验/团本掉落爆料；其副本数据库无无限条目 | 入库（中文转载，需回校官方） |
| GitHub 数据集 | `cmangos/classic-db`（GPL-3.0，1.12 国服中文 locale + 掉落模板）；Napalmsteak `Forever Cache.json`、`eelliott4517/forever-loot`（无 License）；`Stein-N/WoW-Quest-Database`、`TylerAkins/forever-guide-mate` | classic-db 入库（**只取译名与结构**）；无 License 的两个只读不存 |
| 官方图标 CDN `render-us.worldofwarcraft.com/icons/` | 老物品可取；**无限服新物品图标能否取到未证实** | 待验证 |

### 7.4 社区/论坛类 UGC

| 源 | 情况 | 标签 |
| --- | --- | --- |
| 百度贴吧「魔兽世界无限吧」 | 未登录浏览器渲染可读列表与正文摘要；主观体验为主，无掉落表 | 线索（需求与体感） |
| NGA | 未登录"账号权限不足"，`read.php` 空壳，403 | 不用（人工看可以，采不了） |
| 网易大神 | 需浏览器渲染，单帖可读，内容是团招募 | 不用 |
| Reddit r/wow | 本机不可达；且 UGC 授权为禁商用 | 不用 |
| 微博官方号 / 微信公众号"魔兽世界" | 登录墙 / 无可见直链 | 不用 |
| QQ 群 / 游戏内聊天 | 无法公开采集 | 不用 |

### 7.5 视频与直播

| 源 | 情况 | 标签 |
| --- | --- | --- |
| B站 | 可检索可直读，已筛出 18 条无限 beta 实测（含逐本攻略、隐藏 BOSS、掉落不完全版、改动对比）；**CC 字幕全空** | 入库（ASR + 关键帧 OCR） |
| 抖音 | `__ac_signature` 验签壳 | 不用（除非人工看） |
| 搜狐视频/头条号视频 | 搜索能出条目（九大副本全解析、圣骑士白皮书天赋点法），单条可达性未逐页验 | 线索 |
| YouTube / Twitch（BlizzCon 回放、beta 直播） | 本机连接失败，未证实 | 未定 |

### 7.6 明确排除的源（不是拿不到，是不该用）

战斗日志与伤害统计类（官方已发禁止评分插件公告）、金币/材料 RMT 行情站（DD373、藏宝湾——涉交易与账号风险，且和官方整治方向冲突）、任何需要玩家战网账号授权或读本地文件的能力、私服数据库。

### 7.7 竞品监测（顺手要盯的四家）

`pigtogo.cn/talents/forever/`（中文无限天赋模拟器，JS 壳未验）、百家号 2026-09-14 那篇"可交互天赋树模拟器（公众号直达版）"、App Store `id1593368066`（WoW Forever Talent Calculator）、Wowhead 自家计算器。结论同第五节：**资料广度不是卖点，中文聚合 + 微信内随手打开 + 清单可勾选可分享才是。**

## 八、2026-10-08 复核（联网实测，含两个新发现）

### 8.1 可达性复测

| 站 | 状态 | 备注 |
| --- | --- | --- |
| `wowclassicforever.info` | 200，275 KB | 仍在更新，含 `/beta-datamine/methodology` |
| `www.wowhead.com/classic/forever` | **403** | 脚本抓取仍被拦，只能人工看 |
| `foreverchanges.pro/dungeons` | 200，158 KB | 可读 |
| `www.fengshen.cn/wuxian/` | 200 | 我们的天赋源 A |
| `nieyi.cn` | 200（**必须用不带 www 的域名**，`www.nieyi.cn` 证书 SAN 不匹配会报 SSL 错） | 我们的天赋源 B，页面 3.9 MB |
| `pigtogo.cn/talents/forever/` | 200，仅 4.4 KB | 仍是 JS 壳，内容未证实 |
| `wow.52pk.com/new_tf.shtml` | 200，仅 2.1 KB | 同上，低质壳 |
| `www.lfcarry.com/` | 200，177 KB | 攻略页，带货代练 |

### 8.2 新站：`wow.gg`（此前未收录，值得盯）

有中文站 `wow.gg/zh-cn`，含无限服前瞻板块（如"元素萨满 — 攻略（Beta 测试）"）。两个关键点：

1. **提供公开数据接口**：页面自述"Public API for AI agents … list of datasets — no key, GET only"，条款写 **CC BY 4.0**。这是我们见到的第一个带明确再授权条款的第三方数据接口。
2. 但页面**没有说明底层数据怎么来的**（客户端解包 / 官方公告 / 人工整理都没写），副本与 Boss 机制是纯文本 Markdown，无在线天赋模拟器。

用法边界：CC BY 4.0 允许引用（须署名），但**它自己的来源不明**，所以仍按 D 类线索处理——可以拿来对存在性、查漏，不能当事实源，也不能整库搬。署名要求若将来引用需落实。

### 8.3 重要线索：层级点数门槛，两个中文源口径一致

我们一直把 `rules.tierUnlockCost` 留成 `null`（硬规矩 5：未核实不做解锁判定）。本次读到两个独立来源给出**同一条规则**：

- `fengshen.cn/wuxian/warrior.php` 页面原文：**"规则：10 级获得第 1 点，之后每升 1 级获得 1 点。天赋每投入 5 点解锁下一排，部分天赋还需前置天赋点满。里程碑天赋在 11 / 16 / 21 / 31 点各开放一个"**
- `nieyi.cn/f/talents/warrior.html` 前端代码：`label.classList.toggle('unlocked', points >= row * 5)` —— 即第 N 排需在该系投满 `N × 5` 点

两者与经典旧世 60 级天赋树的标准机制（各排门槛 5 / 10 / 15 / 20）一致。**但这仍是两个粉丝工具的互相印证，不是官方来源**，且我们的树是 7 行（比经典 5 行多），外推到 25 / 30 的部分没有依据。

处置建议（未执行，待拍板）：不擅自填 `tierUnlockCost`。可选路径是先在天赋页把这条规则作为**待实测说明**展示（"两个第三方工具口径一致：每排需投满 5 的倍数解锁，本站未核实"），等进 Beta 或官方公布后再决定是否启用解锁判定。

### 8.4 参考站自述的数据来源（回答"他们的数据怎么来的"）

`wowclassicforever.info/beta-datamine/methodology` 原文要点：

- 对比两个客户端构建：**Forever beta `1.60.1.70170`** 与 **Classic Era `1.15.9.69722`**，用后者作基准过滤掉探索时代内容。
- "新"的判定是**数据库 ID 唯一性**："New: the ID is in the Forever client and in none of the Era tables we compare with."；排除未命名与占位条目，"旧名新 ID"的重制项目单列，避免统计虚高。
- 分组是站长自己写的规则："read a group as a strong hint, not a list of drops."（把分组当成强提示，不是掉落清单），实际靠对英文名做正则关键词匹配归类。
- 明确列出客户端测不到的：**Beta 内容会变或消失**、**"These tables don't say where an item drops or who sells it."**（掉落来源与 NPC 卖不卖，客户端里没有）、纯服务端数据缺失、任务表只有 ID 没有文本（任务文案来自服务器）、**中文翻译有滞后，未译时直接显示英文原名**。

这条对我们最有用：连最接近数据库的粉丝站都拿不到掉落来源，**我们"掉落不写百分比、缺就写待实测"不是能力不足，是这个阶段的客观边界**。

## 八、2026-10-09 新增源：新手盒子（wowforever.wclbox.com）

**定位：客户端解包转述源（`datamine_cn`）。** 这是目前唯一成体系的中文无限服结构化源，正好补上我们最缺的四块：BOSS 与掉落归属、专业、任务、世界地图。

### 8.1 实测结论

| 项 | 实测结果 |
| --- | --- |
| 脚本可访问 | `curl` 直接 200：首页 97.9 KB、`/renwu` 102 KB、`/fuben/<slug>` 92 KB；**服务端渲染**，不用浏览器就能取数 |
| 结构 | 带 schema.org JSON-LD；副本卡 `<a href="/fuben/<slug>"><b>名<i>新</i></b><small>13–18</small></a>`，首领 `<section class="sj-boss" id>`，掉落 `<a href="/wupin/<物品ID>">` + `<img src="/tubiao/<图标名>.jpg">` |
| 自述口径 | "天赋、法术、物品、地下城和整张世界地图，都直接从无限测试版客户端读出，再逐条与经典旧世对照" |
| 数量级 | 35 座地下城（9 座标"新"）· 235 个首领 · 1055 条掉落归属 · 5,334 件新物品 · 751 项职业改动 · 420 个法术 · 12 个专业 · 40+ 地区任务 |
| 图 | 全部它自己域名：`/tubiao/<名>.jpg`（56 图标）、`/jiemian/custom/classes/<职业>-<哈希>.webp`（职业背景）、`/ditu-tu/`（地图） |

### 8.2 我们的取数边界

- **取**：名称、物品 ID、图标文件名、等级区间、新本标记、首领名单、掉落归属（谁掉什么）。
- **不取**：它的描述文案、背景故事、BiS 结论、排行、攻略正文、任何百分比。
- **图标**：只拿文件名，字节一律走 `tools/fetch-icons.py` 从暴雪官方 CDN 取（527 张里 526 张命中，`inv_ventureco_ring02_color4` 取不到 → 界面自绘）。
- **原画**：官方 CDN 不提供，只能转存第三方副本 → 走 `tools/fetch-art.py`，落 `src/img/art/` + `manifest.json`，保留整目录删除即回退的下线方案。
- **掉落分级**：它自己也写明"谁掉落什么取自经典旧世的开放数据库，暴雪说过无限服重做过掉落"——所以**掉落一律 L2 待实测，不随名单升 L0**。

### 8.3 专业页（P2，2026-10-09 已接）

`/zhuanye/<13 个>` 是服务端渲染，`curl` 直接可取（炼金术 373 KB、锻造 850 KB）。表结构两类：
`table.zk-recipes`（制成品 / 材料 / 技能 / 来源）与 `table.zk-nodes`（列名随专业变：采矿是矿脉、
草药学是草药点、剥皮是怪物等级档、钓鱼是水域），所以采集点表**按表头对齐**而不是套固定列序。
同一页可能有多张同类表（炼金术 121 + 55 两截），只取第一张会少 1/3 条。
技能档位一格四个数：橙 / 黄 / 绿 / 灰起点，灰以上就不再涨点——这是客户端里的原始字段，不是概率。
野营那一页没有表格，本轮标"未解析"，没编。

### 8.4 已澄清的旧未决项

- 官方 Beta 公告里的「监狱」：客户端名单里 **奥卡兹监狱（Alcaz Prison，48-53，无限新增）与 监狱（The Stockade，24-32，经典）是两座不同的本**，不再是疑问。
- 新图标能否从官方 CDN 取：**逐键实测**，技能/天赋类基本有，无限新物品图标多数没有。
