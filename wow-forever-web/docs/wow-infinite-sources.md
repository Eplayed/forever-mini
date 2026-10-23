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
| 职业深度解析（猎人/德鲁伊、牧师/战士、**法师/萨满祭司**、**潜行者/术士**四篇） | **上百条技能与天赋的官方标准中文名**（瞄准射击、野性成长、掠食者之锋、陆行鸟踢击；2026-10-11 新增的两篇另给出法师/萨满/潜行者/术士共 48 条带状态标记的整句），约 2800 字纯长文 | **可直读** | `/news/24301515/index.html`、`/news/24301514/index.html`、`/news/24302097/index.html`、`/news/24310968/index.html` |
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
- **传承系统说明（同一篇有繁中与英文两版）** `worldofwarcraft.blizzard.com/zh-tw/news/24307383` 与 `…/en-us/news/24307383`：2026-10-23 实测两页都 HTTP 200、正文可直读。这一篇是传承线四个事实的**唯一权威出处**——挑战总数 65 项分六类、每完成一项给 1 点、每个角色最多花 16 点、开放条件是三条途径（首点／25 级／非采集主专业 150／探完整张图）。它同时**否掉了两处二手说法**：转述页那句"第一个角色升到 25 级后开放"少说了两条途径，客户端那个名叫 `point_per_challenge` 的字段给的 16 其实是上限。注意它是繁中/英文，不是国服简中页：数字与条件可以直用，**中文专名不能拿繁中字形去跟简中做"逐字相同"判定**。

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

### 8.4 结构化接口：`/_shuju/<发布号>/*.json`（P3 世界线时发现，2026-10-09）

世界页（`/ditu`）正文是客户端渲染的，`curl` 只有 13.8 KB 空壳。但它渲染要用的数据是**静态 JSON**，
放在 `/_shuju/<发布号>/` 下，`curl` 直接可取：

| 文件 | 大小 | 里面是什么 |
| --- | --- | --- |
| `meta.json` | 0.4 KB | `foreverBuild 1.60.1.70235`、`classicBuild`、`dropsAsOf`、天赋更新日 |
| `maps.json` | 25 KB | 48 张客户端地图：slug / mapId / 分组（大陆·无限新增·副本·战场）/ 兴趣点数 / `paint[]`（areaId → 那张小地图的文件名） |
| `map-zones.json` | 4 KB | 东部王国 23 + 卡利姆多 20 个区域：slug / 中文名 / 等级上下限 / 阵营 / areaId |
| `map-reach.json` | 1 KB | 4 个无限新增区域：阵营、等级档、有没有飞行路线 |
| `xiyou.json` | 22 KB | 36 个稀有精英（含掉落归属与两套坐标）+ 14 个地区汇总 + 23 个只有名字没坐标的 |
| `shuji.json` | 20 KB | 36 本书（容器、区域、图上百分比 + 世界坐标）+ 3 档上交奖励 + 2 名管理员 + 2 本没给坐标的 |
| `shuidai.json` | 8 KB | 睡袋物品与机制数值 + 5 处营地点 |
| `changes.json` | **1.7 MB** | 964 条职业改动（544 天赋 + 420 法术）：职业、所在系、名称、改动类别、层数、图标键，**以及前后两版 tooltip 原句** |
| `chengjiu.json` | 25 KB | 成就 46 条（本轮没接） |
| `dungeons.json` | 14.9 KB | 35 座副本的**排队元数据**：中文名、等级区间、阵营与所在区域、载入图键、`status`（new/classic）、`sources`（指到客户端队伍查找器表）。**一条首领与掉落数据都没有**，替代不了 `/fuben/<slug>` 详情页（2026-10-10 实测，已接成 `upstream/wclbox-dungeon-meta.json`） |

**发布号会随上游发版变**（形如 `r-1791485113190`），所以 `tools/scrape-wclbox-shuju.py` 每次都先从页面 HTML 里现读，不写死。
另有 `chengjiu.json`（成就 46 条）与 `map/<slug>.json`（单张地图的兴趣点、飞行线、航线）本轮没接。
`/ditu` 的可缩放底图是它自己切的 1715 张瓦片（`/ditu-tu/`），**不在我们的授权范围内，不搬**。
`/gaidong` 页面正文同样是客户端渲染，SSR 里只有抽样名字——所以 P4 的 964 条改动名做逐字体检时，
来源必须指到这个 JSON 端点，不能指到 `/gaidong`（指过去会 859 条"未命中"，是核对方法错而不是数据错）。

**P4 已接 `changes.json`（2026-10-09）**：按用户口径"动态只放名称与改动类型，不放句子"，
`tools/scrape-wclbox-changes.py` 在落盘前删掉 `rank_texts` / `estimated_rank_texts` / `summary` /
`forever_note` / `uncertainties` / `spellbook` 等全部文本字段，仓库里不留别人转述的游戏文案；
卡口两处盯：数据里再出现句子字段就失败，本站七项计数必须与上游 `meta.json` 自报的逐项一致。
实测还查出上游一个键名带尾点（`spell_shadow_devouringplague.`），去掉尾点才从官方 CDN 取到图。

### 8.5 已澄清的旧未决项

- 官方 Beta 公告里的「监狱」：客户端名单里 **奥卡兹监狱（Alcaz Prison，48-53，无限新增）与 监狱（The Stockade，24-32，经典）是两座不同的本**，不再是疑问。
- 新图标能否从官方 CDN 取：**逐键实测**，技能/天赋类基本有，无限新物品图标多数没有。
  P3 又添一组反例：世界线 56 个图标键里 9 个取不到，全是 `inv_*_skybornec60_*` 这类天裔新装备。
- 区域 mapId 能不能信：大陆地图 `paint[]` 的 `areaId → 文件名` 与稀有/书籍分组自带的 `id` 是两套独立字段，
  44 个区域逐一对齐零冲突，这条交叉验证已进 `build-data.js`（对不上直接失败）。

### 8.6 2026-10-10 新增源：wago.tools 的客户端 DB2 转储（实测可达）

| 项 | 实测结果 |
| --- | --- |
| 是什么 | 把暴雪客户端解包出来的 DB2 表转成 CSV 提供的第三方站，**不是暴雪域名** |
| 能取 | `curl` 直接 200：`/db2/GroupFinderActivity/csv?build=1.60.1.70334` → 9.3 KB / 109 行；`/db2/GroupFinderCategory/csv` → 5 个类别（2=Dungeons、114=Raids、116=Quests & Zones、118=Battlegrounds、120=Custom） |
| 有无限服内容 | 有。9 座无限新增本里的 4 座、以及 5 个陌生团本名都在这张排队表里 |
| 限制 | 只留最近几个构建号，旧构建会 400/404（脚本报错并说明，不静默用旧的）；表里的 `Description_lang` 一类说明文本按红线不落盘 |
| 我们用它做什么 | 副本的**英文原名**（客户端里游戏内就叫这个）、**等级区间**、**一次几人**（`MaxPlayers`）。取回日期与 URL 逐条挂进数据，卡口要求 `datamine_en` 必须有链接与日期 |
| 定级 | 英文名属"官方英文原文、经第三方转述" → **L1**，不像 `datamine_cn` 那样支撑 L0（`build-data.js` 的 `isOfficial()` 里刻意没有它） |
| 脚本 | `tools/fetch-db2-groupfinder.py` → `src/data/upstream/db2-group-finder.json`；构建号从 `_shuju/<发布号>/meta.json` 的 `foreverBuild` 现读 |

同一轮把 `_shuju/<发布号>/dungeons.json` 也接进来了（`tools/scrape-wclbox-shuju.py --group dungeons`）。
它的 `enter` 列**没有采**：逐列与上面这张客户端表比对过，对不上任何一列（怒焰裂谷写 8，客户端 `MinLevel` 是 13），
归不了因就说明那是它自己拍的数，不是客户端里的字段。它的 `summary` 是介绍句子，同样不落盘。

### 8.7 这条源顺手澄清 / 新留下的问题

- **澄清**：38 座副本里 18 座一直没有英文原名，现在从客户端排队表补齐 —— 38 座全部有英文原名，其中 18 座来自这张表。
- **澄清**：黑石塔上层在客户端里是 **10 人**条目（不是记忆里的 5 人），黑暗深渊 / 诺莫瑞根 / 沉没的神庙除了 5 人条目外**另有一条 10/20 人的排队条目**。是不是同一个本两种规模，进游戏才能定，界面上两个数都摆着。
- **新缺口**：客户端排队表里还有 13 个本站没有名单的名字——地下城 2 座（Demon Fall Canyon、Karazhan Crypts，都 60 级 5 人），
  团本 11 个（含熔火之心、黑翼之巢、纳克萨玛斯、祖尔格拉布、安其拉两处，以及 Storm Cliffs / The Tainted Scar / Nightmare Grove / The Crystal Vale / Scarlet Enclave 这 5 个陌生新名）。
  副本页单列一张表说明"客户端能排到、本站还没有首领与掉落来源"，不当成成品数据。
- **新缺口**：9 座无限新增本里有 5 座（沉没之城、克罗多克要塞、奥卡兹监狱、黑喉要塞、塑源者平台）**在客户端的队伍查找器里还没有条目**，
  也就是现在还排不到队。卡片逐条写明，不猜开放日期。
- **仍分歧**：剃刀高地的英文原名，参考站写 "The Razor Krendor"，客户端排队表写 "Razorfen Downs"；
  湿地那座官方回顾写 "Whelgar's Excavation"，客户端写 "Excavation Site: Wetlands"。两个都留。

## 九、2026-10-11 整批重抓之后的源状态（wow-data）

细节与逐源差异见 `docs/DATA-REFRESH-2026-10-11.md`，这里只记源层面的长期事实。

### 9.1 官方中文：六个职业已有深度解析，只剩圣骑士

`/news/24302097/index.html`（法师与萨满祭司）与 `/news/24310968/index.html`（潜行者与术士）实测 200、可直读，
已加进 `tools/extract-abilities.py` 的 `PAGES`：`abilities.json` 38 → 86 条，每条整句照录 + 回指自己那篇。
新稿的小标题写法变了：老两篇是「万千形态：德鲁伊职业解析」，新两篇是「法师：因时制宜，施放恰当的法术」，
`head_class` 两种都认。**两篇稿子的发表日期在列表页与文章 SSR 里都取不到**，只有正文里的定档 11 月 5 日，
所以 `checkedAt` 记的是本站核对日，不是官方发布日。

专精名一律取页面小标题原词，逐页核过：法师 奥术 / 火焰 / 冰霜，萨满祭司 **元素战斗** / 增强 / 恢复，
潜行者 **奇袭** / 战斗 / 敏锐，术士 痛苦 / 恶魔学识 / 毁灭。
`SPEC_HEAD` 里长词必须排在短词前面（`head_spec` 是"等于或开头匹配"，`元素` 排在 `元素战斗` 前面会把官方词切掉）。

### 9.2 新增的两条译名分歧（都不静默取舍）

| 词 | 官方中文 | 客户端解包（第三方站转述） | 两份第三方天赋工具站 | 本站现在显示 |
| --- | --- | --- | --- | --- |
| 潜行者第一棵树 | **奇袭**（24310968 小标题） | **奇袭**（`/tianfu/rogue` 与 `changes.json` 的系名） | 刺杀（fengshen 存档与现读都是） | 刺杀（`talents/rogue.json` 树名） |
| 萨满祭司第一棵树 | **元素战斗** | **元素**（`/tianfu/shaman`） | 元素战斗 | 元素战斗 |

- 节点级早有 `nameCn` + `nameAlt` + `nameConflict`（界面红框两个都显示）。
- 专精/树级只有一个没人读的 `nameAltUpstream`：`talents/rogue.json` 的 `trees[0].nameAltUpstream` 已经存着"奇袭"，
  但 `app.js` 与体检脚本都不读它 → 玩家看不到。**这是字段结构缺口，不是数据缺失**，改哪个字段承载要主会话或用户拍板。

### 9.3 两份天赋工具站的快照已经落后，抓取器却没现读

`src/data/upstream/fengshen-*.json` / `nieyi-*.json` 是 2026-10-07 的快照，**文件里没有采集日期字段**（历史欠账）。
2026-10-11 现读这九页对比存档：**110 处不同**（战士 15 处改名 + 7 处点数上限变化 + 系名 狂暴→狂怒，
另八个职业多为纯译名改动，如 元素专注→元素集中、奥术专注→奥术集中 互换）。
`tools/merge-upstream.js` 的逻辑是"本地快照存在就不重抓"（`if (!fs.existsSync(fFile))`），
所以直接跑它会**用 10-07 的旧译名去对齐 70338 的客户端格位**，把混合版本当成事实写进 `src/data/talents/`。
另外它把 `collectedAt: '2026-09-13（上游自述）'`、`nameConflict: 89`、`nameVerified: 114` 写死在代码里，
跑一次就把这些旧数盖回 `meta.json`。本轮因此**停在 merge 之前**（详见 DATA-REFRESH 报告第四节）。

### 9.4 客户端解包线：现读目录与 build

- 发布目录 `_shuju/r-1791702948979`（2026-10-11 首页 / `/ditu` / `/gaidong` / `/fuben` 四页一致引用）。
- `meta.json`：`foreverBuild 1.60.1.70338`、`classicBuild 1.15.9.70003`、`talentsUpdated {build 70338, 10-10}`、
  `launchAt 2026-11-04T23:00Z`、`betaCloseAt 2026-10-21T00:00Z`、`dropsAsOf 2026-10-06`。
- 自报计数 965 / 753 / 113 / 304 / 79 / 420 / 257，本站 `changes.json` 逐项一致（脚本现读，无需改代码）。
- **wago.tools 的 GroupFinderActivity 表：`build=1.60.1.70334` 与 `build=1.60.1.70338` 两份 CSV 逐字节相同**
  （各 9265 字节，md5 `22312076a6e45546a340e2a0006caa3d`）→ 排队表这一版零变化，109 条活动逐字段对比 0 处不同。

### 9.5 客户端传承表自相矛盾的一条

`_shuju/r-1791702948979/legacy.json` 的 `rules` 写 `point_per_challenge 16`、`launch_earnable_total 81`，
而它自己的 66 条挑战明细里 65 条 `points` 是 1、只有 #64283「参与过《魔兽世界：无限》测试」是 16（65+16=81）。
本站按明细摆每条的点数，客户端那个 16 原样留在 `meta.rules.clientRulePointPerChallenge`，
冲突写进 `meta.rules.rulesConflict`，`build-data.js` 改为"点数偏差必须在 `pointVariants` 里声明过"，
不再拿一个说法覆盖另一个。**进游戏核过之前，页面上不该出现"每项挑战 16 点"这种话。**

## 十、网易DD（dd.163.com，原「网易有爱」）能不能当数据源 —— 2026-10-13 判过，结论：暂不用

站主问过这条。查完的结论是**对我们这条线暂时无用**，理由按重要性排：

1. **它没有无限服的内容。** 2026-10-13 现读 `https://dd.163.com/` 首页：只列**正式服与怀旧服**，
   没有《魔兽世界：无限》/ 无限服专区，也没有副本 / 任务 / 掉落资料库入口。
   我们要的 35 座本（尤其 9 座新本）它压根没有 → 这条单独就足以否掉。
2. **DD 上的"插件"不是网易的数据，是第三方作者作品被网易分发。** 它的定位对标大脚 / CurseForge / 黑盒工坊。
   插件里的中文串确实是国服客户端串（有价值的那类事实性标识符），但"网易托管"≠"网易授权我们抓"，
   而且不少插件带作者自定义许可。**要碰也只能当人工参照，不进自动化**（与 wowhead 同一档处理）。
3. **它的战绩 / 3D 英雄榜 / 战斗数据那一块直接排除**：那是玩家个人数据，
   本站红线明确不做角色查询、不做 DPS 与排行、不做宏与循环提示。
4. **就算哪天它开了无限服专区，正确取法也不是爬**：装完插件后数据就在本地
   `Interface/AddOns/<插件>/Locale/*zhCN*.lua` 的明文键值表里，本地脚本读文件即可，零抓取零反爬。
   但**经验值与金币这类数值插件里通常没有**（那是服务端数据），所以它顶多补"中文定名"，
   补不了数值——数值仍要走 wclbox（它 35 座都带任务那一节）。

对照记录：本站现有副本数据来源见 `docs/DATA-WOWHEAD-DUNGEONS-2026-10-13.md`（wowhead 盘点）与
`src/data/upstream/wowhead-dungeon-quests.json`（2026-10-13 实采快照）。

## 十一、wclbox 的副本任务三节已采下来（2026-10-13，接第十节的判断）

站主让"如果网易DD不行就去采 wclbox 详情页的任务那一节"。网易DD 确实不行（第十节），已采。

- 工具：`tools/scrape-wclbox-quests.py`（渲染后 DOM 抓，逐座点「任务 / 任务物品 / 任务起始地点」三节）。
- 产出：`src/data/upstream/wclbox-dungeon-quests.json` —— **35 座全抓到，28 座有任务，
  任务 407 条、任务物品 377 条、起始地点 316 条**；字段齐率：任务等级 407/407、
  最低接取等级 406/407、经验值 366/407、接取 NPC+地点 397/407。
- **刻意没抓**：任务目标描述整句（那是文案，红线只让取事实性标识符）、掉落概率（本站不写概率）。
  实现上不是"抓了再删"——解析器只认带标签的字段，那句描述不匹配任何规则，就地不落盘。
- **两源分歧已经出现**：怒焰裂谷「试探敌人」经验值，wclbox 850 / wowhead 1050；
  洛丹伦废墟任务数 wclbox 9 / wowhead 15。挂进成品数据时两个都要留，不许覆盖。
- **新本 9 座里只有 2 座有任务**（领主大厅 4 条、洛丹伦废墟 9 条），另外 7 座 wclbox 也没有。
  这条本身就是结论：**无限新增本大部分没有副本任务**，不是我们没采到。
  领主大厅两边都是 4 条，可交叉印证。
- 还没做：挂进 `dungeons.json` 与详情页那一块（wow-dev 的活），要先定两源分歧怎么摆。

## 十二、网易DD 上的"钓鱼手账 FishingLedger"插件 API 分析（2026-10-14）

站主在网易DD 装了"老牌轻量化钓鱼助手-功能全面"，本地实为 `FishingLedger` v0.6.6
（`C:\GAME\World of Warcraft\_retail_\Interface\AddOns\FishingLedger\`，15 个 Lua 单文件插件，无外部依赖库）。
作者自称"使用公开的 api"，逐文件读源码核实：**属实**。定位结论先给：**它不是数据源，是一条"无限服客户端 API 能力"的一手参照 + 将来玩家侧实测采集的现成范式**，按"人工参照"档处理（同第十节对 DD 插件的原则，不进自动化）。

### 12.1 作者"公开 API"的核实结论

- **全部调用是暴雪公开文档化的 UI Lua API**，没有私服魔改接口、没有未公开函数、没有内存读写。
- **零网络通信**：无 `SendAddonMessage` / `SendChatMessage` / `SendMail`（WoW 插件沙盒本就不允许联网），统计只存角色本地 SavedVariables（`FishingLedgerDB`）。
- **操作辅助走合法边界**：单击/双击抛竿与右键互动全部由玩家真实硬件点击触发，用 `SecureHandlerStateTemplate` + `RegisterStateDriver("[combat] combat; …")` + `SetOverrideBinding` 实现，战斗锁自动解绑，实际施法由客户端校验——这是暴雪明确允许的插件写法。
- 改过的 CVar（软交互开关、音量）都记录原值、退出时恢复。
- 全部 API 调用包 `pcall` + **按能力探测降级**（源码注释原话 "capability-based, not number-based"），同一份代码跑六种客户端。

### 12.2 它用到的 API 全清单（按模块）

| 模块 | 新接口（正式服/无限用） | 旧接口降级 | 用途 |
| --- | --- | --- | --- |
| 物品 | `C_Item.GetItemInfo` / `GetItemInfoInstant` / `GetItemIconByID` / `GetItemSpell` / `GetItemCount` / `RequestLoadItemDataByID` | `GetItemInfo` / `GetItemIcon` / `GetItemSpell` / `GetItemCount` | 物品名/品质/图标、鱼竿判定（classID=2 subclassID=20）、鱼饵来源 |
| 容器 | `C_Container.GetContainerNumSlots/GetContainerItemID/GetContainerItemLink/GetContainerItemInfo` | 同名旧函数 | 背包扫描（拾取空间、鱼饵物品反查） |
| 法术 | `C_Spell.GetSpellName/GetSpellTexture`、`C_SpellBook.IsSpellKnown` | `GetSpellInfo` / `GetSpellTexture` / `IsPlayerSpell` / `IsSpellKnown` | 钓鱼技能识别（法术 ID 7620/7731/7732/18248/33095/51294/88868/110410/131474） |
| 引导 | `UnitChannelInfo` | 同 | 读钓鱼引导起止时间（统计收杆时长） |
| 光环 | `C_UnitAuras.GetAuraDataByIndex`、`C_TooltipInfo.GetUnitBuff` | `UnitBuff`、隐藏 GameTooltip `SetUnitBuff` 扫描器 | 鱼饵/增益剩余时间与描述（扫描器不污染玩家可见 tooltip） |
| 专业 | `GetProfessions` + `GetProfessionInfo`、`C_TradeSkillUI.GetProfessionSlots`、`C_PaperDollInfo.GetTemporaryEnchantmentInfo` | `GetNumSkillLines` + `GetSkillLineInfo`、`GetWeaponEnchantInfo` | 钓鱼技能值、专业装备槽、鱼竿临时附魔 |
| 地区 | `C_Map.GetBestMapForUnit` + `C_Map.GetMapInfo`（沿 parentMapID 上溯到 mapType=3 的大区） | `GetRealZoneText`/`GetZoneText`/`GetSubZoneText` | 每竿按抛竿瞬间大地区归档 |
| 拾取 | `IsFishingLoot`、`GetNumLootItems`/`GetLootSlotLink`/`GetLootSlotInfo` | 同 | **只记实证**：`IsFishingLoot()` 确认钓鱼拾取 + 槽位实际清除确认 + `CHAT_MSG_LOOT` 交叉去重 |
| 软交互 | `UnitGUID("softinteract")`、`UnitIsInInteractRange`、事件 `PLAYER_SOFT_INTERACT_CHANGED`、CVar `SoftTargetInteract/Arc/Range` | — | 鱼漂互动范围红绿字判定；GUID 解析物件 ID **35591**（普通鱼漂）识别 |
| 客户端识别 | `GetBuildInfo`、`WOW_PROJECT_ID` | 同 | 接口号 16001–16999 且有 `C_Spell`/`C_Item` → 判定为"魔兽世界：无限 Beta"，命令行加挂 `/flf` |

事件面（60+ 个，均在 `Main.lua` 注册）：钓鱼链路 `UNIT_SPELLCAST_CHANNEL_START/UPDATE/STOP/INTERRUPTED/FAILED`、`LOOT_READY/OPENED/SLOT_CLEARED/CLOSED`、`CHAT_MSG_LOOT`、`UI_ERROR_MESSAGE`、`LOOT_BIND_CONFIRM`；状态面 `PLAYER_REGEN_*/PLAYER_DEAD/UNIT_ENTERED_VEHICLE/ZONE_CHANGED*/GET_ITEM_INFO_RECEIVED` 等。

### 12.3 对我们项目的四点价值

1. **无限服客户端 API 能力表（最有价值的一手情报）**：作者把无限服当一等客户端适配——判定条件（16001 + 现代 `C_Spell`/`C_Item` 命名空间存在）说明**无限服客户端是正式服代码基础改的，10.0+ 的 `C_*` API 面可用**；README 还记录了"无限 Beta 自身的 SavedVariables 读取故障"这种踩坑实录。将来若做采集插件，`Compat.lua` 的能力探测写法可直接参照，不必重踩。
2. **内置 ID 表可交叉核对我们 items.json**：约 130 个钓鱼物品 ID（经典→Midnight 分组）、鱼饵附魔 ID（263–5386）、增益光环 ID（1237974 等 6 个）、鱼饵物品 ID（6529–68049）、鱼漂物件 35591、钓鱼法术 9 个。这些是事实性标识符，符合红线取数边界；Midnight 组注释写明交叉核对自 "GatherBuffs' author-maintained fishing catalog"，溯源链条清晰。**只对 ID 核存在性与覆盖，不搬它的任何文案**。
3. **"客户端内实测采集"范式的活样本（战略级参考）**：我们的 L2 待实测数据（掉落、服务器实测内容）缺采集管道。这个插件证明了在无限服上可稳定读到 物品信息 + 拾取（`IsFishingLoot` 确认 + 实际拾取确认 + 聊天事件交叉验证去重）+ 地区（mapID 上溯归档）+ 时间，玩家侧存 `itemID→数量→mapID→时间`。这正是 wowhead 靠玩家插件众包实测数据的模式——将来做"无限服实测掉落/鱼种分布"采集器时，它的**确认口径**（只记实证、证据不全归未知、不从背包增量猜来源）与我们的 L0/L2 分级方法论同构，SavedVariables 导出 → `tools/` 解析 → 进基底即可衔接现有管线。
4. **帮不上的部分**：它明确"没有自动聊天、分享或上传"，所以它本身不产出可采集的数据；钓鱼内容也只是很小的板块，不改变物品库优先的排期。

### 12.4 处置

- 不抓取、不依赖、不进任何自动化管线；仅作为**参照存档**（本节即存档）。
- 第 2 点的 ID 交叉核对：待物品库二批详情抓取排期时顺带比对（低优先级）。
- 第 3 点的采集范式：留给将来"L2 实测数据收集器"立项时引用，当前不执行。

## 十三、GearInsight 插件家族能不能当数据源 —— 2026-10-14 判过，结论：不能进数据基底；按"参照"档处理

站主提供拷贝 `D:\project\wow\`：GearInsight 0.97.9 主插件 + GearInsight_Talents（天赋库）+
GearInsight_Rotation（手法）+ GearInsight_Macros（宏库）+ GearInsight_Layout 等分模块。
作者"枫叶大象-格瑞姆巴托/yinpeng"，CurseForge 项目 1554172，Interface 120100/120007，
更新极活跃（判定当天 0.97.9 还在发版），**明确三客户端适配**：正式服 / 无限 Forever / 时光服 Titan
（`GIWidgets.lua` 的 GAME_TXT 三分支，多处"无限客户端实测"注释；站主客户端即 `C:\GAME\World of Warcraft\_retail_`）。
SavedVariables：`GearInsightDB`（GearReader+StatReader 的角色装备快照）/ `GearInsightRecsDB`；WTF 实测存档本轮未拷。

### 13.1 内置数据是什么、从哪来（判定依据）

- **BisData.lua**：文件头自述 "Live BiS data from WarcraftLogs V2 — Zone 53（烈毒之渊 S2）, Mythic —
  auto-fetched"，2026-09-27 生成，40 专精 / 2993 件——**正式服当前赛季**的团本 BiS。
- **GearInsight_Talents**（PopularTalents/PvpTalents.lua）：文件头自述由 `build_popular_talents.py`
  生成，"WCL 顶尖天赋（团本/冲分/割草 前5；常规 = +12 第 300~500 名附近 5 人）"——**WCL 排行聚合**。
- **CheeseData.lua**：正式服 S2 玩法情报（ROLL 币全流程、周常捷径等），正文自己注明转载自
  "魔兽阿落、熊本超人、星空心语、冰糖雪栗儿"等创作者——**攻略聚合转述**。
- 判定：三样都不是"官方/客户端解包"级事实，而是**第三方聚合排行与攻略转述**——按本站分级到不了
  L0/L1；且内容对应正式服 S2 赛季（烈毒之渊、地下堡、化生台、ROLL 币），与无限服经典旧世进程
  （站内 35 座本、经典团本排期）几乎不重叠，站内同类字段（物品/天赋/掉落）已有 L0 解包源。
- **红线冲突**：站内已定"抄 BiS = 红线、排行只声明『本站整理的排序』、零 UGC"——BiS / 使用率 /
  顶尖构筑三类数据整块踩线；WCL 也不构成无限服证据（其 logs 不覆盖无限服）。
- **授权与合规**：数据是作者脚本从 WCL API 抓取的产物，插件自带 Supporters 赞助体系，整包搬用等于
  复制他人数据产品；GearInsight_Rotation（手法助手）与 GearInsight_Macros（宏库）属
  9-24《付费插件及其违规商业化行为专项治理公告》敏感区——**本站与变现线一律不碰、不推广、不引用**。

### 13.2 那它有什么用（同第十二节"参照"档）

- **无限服客户端兼容写法的一手情报**（最有价值的一块）：作者对无限客户端的兼容注释很具体——
  "无限客户端可能没有 C_AddOns → 退回老的全局函数"（GuildTab.lua）、"只用 60 级经典客户端也有的
  贴图（无限/时光服客户端里一定存在）"（GIWidgets.lua）、按无限英文客户端截图修布局（LayoutPage.lua）、
  无限纸娃娃版式参照（GearMap.lua，引 **addon-forever** PagePlan.lua）。将来 L2 实测收集器或
  小程序做同款功能时，这些"哪个 API 在无限客户端没有/怎么退"的记录能省大量试错；
  `addon-forever` 这个项目名同时是一条新线索：**无限服已存在自己的插件生态**。
- **schema 参照**：BisData 头部 `version / updatedAt / source` 显式声明的写法与站内产物 manifest
  同构，值得学（学的是格式，不取数据）。
- SavedVariables 装备快照 = 第十二节 FishingLedger 同款"客户端内实测"范式，本轮无增量。

### 13.3 一个待核实口

作者对无限服适配的深度本轮没全验：若其 BiS 页在无限服内出的是经典进程内容，说明作者另有无限服
数据管线（比 wclbox 更早的玩家侧聚合）——那也改变不了"聚合源不进数据基底"的结论，顶多将来当
交叉核对的第三证据，且需重新取证（抓取端点、更新频率、覆盖范围）。

> **13.3 的口子当晚就闭合了**：站主补拷了作者另发的无限服专版 `GearInsight_Forever`（见第十四节）
> ——第十三节判的正式服全家桶与本节口子无关，无限服数据管线确实存在，且出处声明相当规范。

## 十四、GearInsight_Forever（无限版 0.4.29）数据文件盘点 —— 2026-10-14，结论：可按既有"转述"档当交叉核对与缺口补充源；不整包搬

站主补拷 `D:\project\wow\GearInsight_Forever\`（5.2MB，v0.4.29，文件日期 2026-10-13，Interface
16001/11507——16001 正是台账已知的无限服接口号；`dd_author.toc` 带网易DD 分发指纹，说明经 DD
渠道安装，与第十节"DD 平台本身无无限服内容"不矛盾）。**与第十三节的正式服全家桶不是同一份东西**。

### 14.1 出处结构（文件头自述，逐文件核实）

- **Data.lua**（3.5MB）：`scripts/gi_forever_addon_data.py` 自动生成，源 = **Forever beta client
  1.60.1.69876（2026-10-03）**；其中 loot 表自带二级出处：`foreverchanges.pro（Beta 实测掉落 ·
  build 1.60.1.69913）`。build 69876 **旧于**站内 wclbox 现行 70338。
- **DungeonQuestData.lua**（494KB）：源 = Dungeon Assistant（CurseForge，Shadowblade，取自
  **Wowhead WoW: Forever 1.60.1**）；中文名 vmangos + 游戏内现读；地名《无限》客户端 DB2。
- 出处声明规范（来源/build/生成脚本/日期齐全），与站内产物 manifest 同构——这点本身就值得学。

### 14.2 表清单与对站内基底的交叉核对数（本轮实测）

| 表 | 量级 | 内容 | 对站内的意义 |
| --- | --- | --- | --- |
| `gear` | 1,515 件 | id/中英名/图标/slot/**ilvl/需要等级**/品质/来源 | 1,501 件在站内 items.json（21,077）；**14 件站内没有**（腐疗者套 5 件 + 273022~273030 连号绿蓝装，wclbox 索引漏收或后续 build 移除，物品二批时核对）；**ilvl/req 正是物品二批要的字段** |
| `loot` | 1,875 条 | **Beta 实测掉落**（foreverchanges.pro，build 69913），**无概率字段**（红线不破） | 站内掉落是 wclbox 解包 1,050 条——"实测"对"解包"是双向交叉的好对子；foreverchanges.pro 即台账记过的竞品站（Ko-fi、明写无广告） |
| `DungeonQuestData` | 29 座 / 387 qid | 副本任务（Wowhead Forever 1.60.1 系），每座带入口坐标 | **能补 2 座空座**：whelgars-excavation 14 条、city-of-dalaran 15 条；其余 5 座空座它也是 0；lbrs/ubrs 反而站内更全（29/30 vs 18/23）——双向各有覆盖；ragefire 标 13-18（Wowhead 口径，站内定稿 13-20 的第三证据，支持官方值那一侧） |
| `rares` | 338 条 | npc id/中英名/品质/等级区间/区域/**坐标** | 站内世界线 36 稀有是"配书"口径，覆盖面不同；坐标准备率是亮点（将来世界线扩容可引） |
| `achievements` | 211 条 | id/中英名/描述 | 站内 upstream **还没有成就文件**（wclbox chengjiu.json 当时"顺手有了"但没入库）——GAP ③ 的两路原料在此 |
| `spells` | 1,480 条 | 九职业技能表（lv/id/名/描述/auto/tal） | GAP ② 法术书（现 86 条，目标 420+）的第二源 |
| `talents` | 9 职业 27 树 | 节点级 n/c/m/r/col/**s=changed\|same\|moved（对照经典旧世）**/图标/中英描述 | 站内 changes 线与天赋线的交叉核对材料；注意 build 旧于 70338，且中文名是作者/vmangos 人工译名，**不能升译名等级** |
| `tier` | 18 套 | T1 套装（9 职业 × 2 角色） | 套装页未立项，存档 |
| `keys`/`questSeries`/`leveling` | — | 键位推荐 / 职业任务线（含接取人坐标）/ 升级里程碑 | 职业任务线是事实性内容，低优先 |
| `MacroData`/`KeysRot`/`DefaultBuildsData` | — | 宏库 / 循环 / 天赋构筑推荐 | **不碰**：前两者踩 9-24 公告敏感区；构筑推荐是强度导向（红线邻区） |

### 14.3 判定与用法

- **可进站内管线**：按既有 L0 解包转述档（wclbox 同级）与实测转述档（foreverchanges.pro 系，
  记双跳出处），**逐表挂 provenance 做交叉核对与缺口补充**；不整包搬、不取攻略文案、不升译名等级。
- **授权**：仍属作者数据产品（CurseForge 项目 + 网易DD 分发 + Supporters 赞助体系）；用法克制
  （交叉核对 + 补空 + 引用登记），不复制其产品形态，不与其构成同类竞争功能。
- **待拍板的三件**（与既有台账欠账并轨）：① 物品二批的 ilvl/req 从这取还是 wclbox 抓、两源怎么
  并；② 法术书 GAP② 与成就 GAP③ 动工前两源并评；③ 掉落实测↔解包抽 2 座本逐条比对，差异清单
  交站主。

## 十五、XR_DungeonGuide（魔兽无限游戏全能助手 0.37.1）—— 2026-10-14，结论：同第十四节口径；任务库与物品详情是最大增量

站主拷贝 `D:\project\wow\XR_DungeonGuide\`（50MB，v0.37.1，作者"血染"，Interface
11503~16001，网易DD 分发指纹，SavedVariables `XR_DGDB_SV`）。TOC 自述：**"数据与
www.wx-wow.com 同源"**、"不采集任何个人用户数据，永久免费"——作者自有站点（wx-wow.com），
插件是其数据的分发形态，与 GearInsight 家族同模式。

### 15.1 出处结构（文件头自述，逐文件核实）

- **Data.lua**（4MB，items **14,352 件**）：真源 = 作者站点 `research/dg-loot.json`（**社区整理稿 +
  本站物品库**），fetched 2026-09-20；自带口径"掉率未知的一律不写数字"。条目带
  装等/品质/部位/卖价。
- **Data_QuestDB.lua**（5MB）：**fc 全量任务 5,205 条**（fc = foreverchanges.pro——与 GearInsight
  loot 的上游同一家！）——带等级/阵营/经验/中文描述/目标/完成文本/接取人/坐标。
- **Data_Bis.lua**（1MB）：抓"权威资料库 zh-cn/bis/*"（38 页，2026-10-09）——**Wowhead 系 BiS**，
  强度导向不取。
- **Data_Skills**：权威资料库 zh-cn/spellbook/*（页内嵌法术书 JSON：全训练师技能 + 学习等级 +
  客户端中文 tooltip，2026-10-02）。
- **Data_Talents**：权威资料库 talents 页内嵌（2026-10-02）+ fc 热门加点（强度导向）。
- **Data_Legacy**：权威资料库 zh-cn/legacy-perks（2026-09-26，Beta 1.60.1）——challenges **66 项与
  站内 66 项直接对上**（wowhead 页面口径 独立印证 wclbox 客户端口径）。
- **Data_Prof**（286 配方）："权威资料 forever 事实数据…经 wasmoon 真解析抽取"；作者自立的
  两条规矩与本站完全同构——"人写的简介/提示/练级路线/配装推荐不在收录范围"、"物品/区域名
  一律不落盘只存 ID，显示时问客户端"（规避译名的做法一致）。
- **Data_DungeonRates**：掉率显示管线已建但**数据未填**（权威资料被地区封锁，1.12 镜像管线已
  验证待补）——实际上没有掉率数据。
- **Data_DungeonGuides**：副本攻略文字（要点参考权威资料、文字重组、界面固定标注来源）——
  **攻略正文红线，不取**。
- Data_Codex（稀有/卷轴图鉴，"未逐一在游戏内确认，条目注明"）/ Data_PvP（军衔，只存 ID）/
  Data_Crates（板条箱）/ Data_Legacy：事实性，低优先存档。

### 15.2 关键结论

1. **"权威资料" = Wowhead**（zh-cn 页 + classic 1.12 镜像）、**"fc" = foreverchanges.pro**——两个
   插件的上游高度重合（fc + wowhead + beta 客户端解包），互为旁证。无限服中文社区的数据网
   形状就此清楚：**Wowhead（英文权威）→ fc（中文聚合）→ wx-wow / GearInsight 作者（中文站与
   插件）→ 玩家**。本站拿任何一手的"转述"，溯源链都能落到这三家之一。
2. **最大增量是任务库**：5,205 条全量任务的**事实字段**（ID/名称/等级/经验/阵营/接取人/坐标）
   ——站内目前只有副本任务 367 条 + 世界书 36 + 职业任务线；**描述/目标/完成文本三类文案
   不取**（转述文案 + 机翻风险）。
3. 物品 14,352 件（装等/品质/部位/卖价）——物品二批的**第三个候选源**；出处口径最弱（社区
   整理稿），排序：wclbox 解包 > GI beta 解包 > XR 社区整理。
4. Legacy 66 项挑战独立印证站内（两路不同上游得出同数）；专业 286 配方（材料/阈值/产物）可
   对照站内 professions.json。
5. 掉率管线有、数据空——天然不破红线；**BiS / 热门加点 / 攻略文字三块照第十四节口径不碰**。

### 15.3 待拍板（与第十四节那三件并轨）

- 任务库要不要立项（"任务大全"页或并入世界/副本线）——事实字段与描述文案的边界照旧；
- 物品二批源排序（wclbox / GI / XR）与并表规则；
- 法术书 GAP②：XR spellbook（Wowhead 系）与 GI spells（beta 解包系）两路都齐了，动工前并评。

---

## 十六、物品详情层全量落地（2026-10-16，W2-3）—— 第十五节那条"源排序"已拍板并跑完

站主 2026-10-15 派"W2-3 wclbox 采集全量数据"，按第十四/十五节的盘点与
`docs/ITEMS-DETAIL-SOURCE-EVAL-2026-10-14.md` §3 的结论执行。**这个源的角色变了**：
它不再只是"第三份参考"，而是**当前 build 的权威转述**，属性与卖价一律先取它，
实测与社区稿退为兜底。定稿顺序 **wclbox（1.60.1.70374）> GI loot（69913 实测转述）> XR（09-20 社区稿）**。

- **成本模型（决定以后怎么重抓）**：`/_shuju/<发布号>/` 目录实测只有 `meta.json` / `changes.json` /
  `dungeons.json` 三个端点，**物品详情没有批量接口**——只能逐页 21,077 次请求。
  单线程 + 逐件 0.5s、`Accept-Encoding: gzip`（单页 76 KB → 15 KB）实测 **216.6 分钟、0 失败、无封禁迹象**。
  产物 `src/data/upstream/wclbox-items-detail.json` 7.7 MB。可续跑（逐件 flush），中断重跑不重复请求。
- **取的都是事实字段**：品质 / 部位 / 类型 / 装等 / 需要等级 / 绑定 / 属性行 / 售价 /
  来源 NPC 与区域 / 双方 build 号 / 页面自报状态。**没取**：描述正文、攻略、BiS、掉率（红线不变）。
- **tooltip 里的两类句子要分清**（这一条是本轮踩出来的，直接影响数据质量）：
  客户端把 **教益句**（"教你学会制作X。"）和 **纯风味句**（"相信我，她会明白的。"）放在同一个
  斜体框（`.wp-flavor`）里。参考站按类名两者一起丢，插件源则整句带引号抄回。
  合并层按内容分家：教益句 → 成品 `use` 字段（1,207 件，单独成段单独标源），
  纯风味句 → 丢（448 行），**并且加了"整行引号不许进成品"的构建卡口**。
  本轮快照没带教益句（抓取时按参考站的分类丢了），`use` 暂按 GI > XR 补；
  抓取脚本已改为下一轮按 build 重抓时自己从解包侧带上。
- **页面自报状态是五种**：不变 / 有改动 / 无限新增 / 无限中没有（missing）/ 保留数据行但没属性（held）。
  后两种页面摆的是**经典侧**提示框，记录里打 `tipIsClassic`，合并层禁止它们按解包取属性——
  否则就是拿经典旧的数冒充无限的数（红线：不许编）。
- **跨源一致性（白捡的验证）**：详情页自报状态与 10-13 抓的名称索引逐类对平
  （7,678 / 6,102 / 5,346 / 1,334+610=1,944 / 重建 7）。
- **顺带核到副本线**：`/_shuju/<build>/dungeons.json`（排队表）与站内定稿的等级区间
  逐座对，**38 座 0 座不一致**——10-13"按参考站卡片定稿"那批数值在新 build 下原样成立。
- **build 会漂**：上游从评估时的 70338 走到 70374，`meta.json` 自报开服时间 `2026-11-04T23:00:00Z`、
  beta 关闭 2026-10-21。**开服后按 build 号重抓一轮**是既定动作（管线幂等，重跑即更新）。
- 全过程与门禁结果：`docs/VERIFY-items-w23-2026-10-16.md`；解析层细节：
  `docs/ITEMS-DETAIL-SOURCE-EVAL-2026-10-14.md` §5。

## 十七、猎人宠物页 `/lieren-chongwu` 的结构与取数边界（2026-10-16 实探，只调研未入库）

M1-D 三条板块里唯一"结构没认出来"的那条，今天用 `curl --http1.1` 直接取到 145 KB 服务端渲染 HTML 认完了。
**结论：可取的事实字段比原来估计的少，而且源站自己承认一半名字是意译。**

- 兽卡：`article.lr-card.lr-beast` **共 40 张**，在 `.lr-grid.lr-found` 里。
  每张 = `img.lr-ico.lr-ico-lg`（图标键，路径就是 `/tubiao/<key>.jpg`）+ `h4` 名字 +
  `dl.lr-facts` 四对 `dt/dd`：**种类 / 等级 / 地区 / 攻速**，卡末尾一句 `<p>` 坐标（例：河林 60, 84 附近）。
- **攻速 40 张全是「—」**：那页顶部自己写着「攻速要驯服后才知道」。这一列没有数据，不是我们没采。
- **15/40 张的名字带 `sup.lr-draft title="暂无官方中文名，为意译"`**——源站明说是它意译的。
  按红线"禁止机翻与编造"，这 15 个名字**不能当客户端读出的中文名入库**；
  能入库的只有另外 25 条有官方中文名的。要不要把意译那 15 条也列出来（列就得标"意译"），
  是个范围决定，已进开放项 25 等站主定。
- 种类分布（40 张）：熊 7、猛禽 5、豹 5、蜘蛛 5、陆行鸟 4、狐狸 3、迅猛龙 3、野猪 2、鳄鱼 2、狼 2、
  蝙蝠 1、螃蟹 1 等——这一层是纯事实，可以当筛选维度。
- 页面上另有四块正文：`宠物有哪些改动` / `狐狸` / `攻击速度` / `怎样训练宠物` / `数据来源`。
  **这四块是机制讲解与攻略性质，按红线一块都不取**（`怎样训练宠物` 那种是玩法建议）。
- `.lr-teacher`（28 处）是宠物训练师那一节，与 `/fashu` 的训练师口径同源，取名字与地区可以，取正文不行。

**这一条的入库成本**：一页 145 KB、0.5 秒抓完，40 张卡，比副本任务线便宜两个数量级；
卡点在于"意译名要不要上页面"和"页面归到哪一页"（Q3 仍未答）。

## 十八、BiS 配装层 `/peizhuang`（2026-10-16 实采并入库，站主拍板走 C 方案）

**这一节是本站第一次真采第三方站的"推荐类"数据**，因为站主 2026-10-16 在 `AGENTS.md` 第五节开了例外条款：
配装线允许取 BiS 名单与同部位备选顺序，只到"哪件装备在哪个部位、按什么顺序"这一层。
除此之外这个源没有任何新东西可取——它的属性、装等、名字、图标全部与我们从客户端读出来的同源。

### 结构（实测）

| 层 | 地址 | 内容 |
| --- | --- | --- |
| 总览 | `/peizhuang` | 9 职业 38 套，按 PvE / PvP / 坦克 / 治疗分 |
| 职业页 | `/peizhuang/<class>`、`/peizhuang/<class>/<spec>` | 纸娃娃 `.pz-doll > .pz-cell`（`data-item` + `<small>部位</small>` + `<b class="qN">名</b>` + `<i class="pz-cell-enchant">`）；每部位一节 `section.pz-slot#slot-<key>`，里面 `li.pz-row` 按顺序列同部位备选 |
| 附魔一节 | 同页 `#enchants` | `li.pz-row` 里 `.pz-enchant-slots` 是"贴在哪个部位"（可以是一串，如"胸部、脚、手、腿部"），`.pz-from` 里的 `data-item` 是附魔物品，括号里的数是技能点 |
| 消耗品一节 | 同页 `#consumables` | 与备选同结构 |
| 模拟器 | `/peizhuang-moni/<class>` | 换装 + 属性即时重算 + 本地存方案 + 分享链接。**本轮没做**，缺的是职业基础属性与换算规则，见 `docs/VERIFY-bis-2026-10-16.md` 第五节 |

### 三条取数要点

1. **部落那一版必须点出来**。SSR 只给联盟版；`/warrior/pve/horde`、`/warrior/horde` 这类 URL 全 404，
   `/_shuju/<发布号>/peizhuang.json` 也没有（404，这一层没进静态接口）。
   只能开真浏览器：读一次 → 点 `.pz-faction button`（文本"部落"）→ 再读一次。
   战士 PvE 实测 16 格里 4 件不同。
2. **`.pz-from` 那一段中文整段丢掉**。原文里混着三样红线东西：它写的描述文案
   （"从奥特兰克花岗岩里拿到…也可以去拍卖行找"）、它的权重结论（"按本页权重比第二件高 20%"）、
   **掉率百分比**（"掉率约 0.3%"）。只把链接拆成 `{kind, id}`（配方专业 / 任务号 / 副本 / 物品），
   数字只抠括号里的技能点。落盘后 `掉率 / 权重 / 拾取后绑定 / 拍卖行 / 使用： / 使你的` 全部 0 处。
3. **两套部位词表不是一套话**。它叫"项链 / 戒指 / 双手武器 / 副手：盾牌"，我们库里 `slot` 记的是
   "颈部 / 手指 / 双手 / 盾牌"；另外单手武器它按放的那只手分节，我们统一记"单手"。
   合并脚本里 `SLOT_OK` 那张对照表就是为这个，补完之后**部位分歧从 912 处归零**。
   投掷与弹药列进"远程"是经典旧世规则，不是它写错。

### 交叉核对结果（这个源能信到什么程度）

175 件首选 + 全部备选，物品 ID **100% 在我们名录里**；中文名 **1,265 格零分歧**；
部位 **零分歧**（对上词表之后）。三项都同源（都是客户端解包出来的东西），
所以这个"零分歧"证明的是**我们没抄错**，不能证明"它推荐的强度对不对"——
后者没有任何一处可以核对，因此整条线按 **L1** 留档，页面上固定写"本站整理、不是官方结论、没做模拟计算"。

产物：`src/data/upstream/wclbox-bis.json`（快照 1.4 MB）→ `tools/merge-bis.py` → `src/data/bis.json`（986 KB，只存顺序与结构化指向）。
卡口在 `build-data.js` 的"配装名单"一段：ID 必须在名录、每套必须有 url + 抓取日、
整份文件不许出现百分比与掉率措辞、分级必须 L1（升 L0 直接构建失败）。

## 十九、插件目录里到底有什么：区域→地图号这一层已入库，图一张都没有（2026-10-19 逐文件核过）

站主问"插件采集的数据现在存放在哪、里面有没有网页上缺的那些图"。把那份数据整个翻了一遍，
结论改写了 `docs/DATA-MAP-EXPORT-2026-10-19.md` 的前两条。

**存放位置**：插件产物在 `~/Documents/project/.scratch/wow/`（55 MB，**仓库外、不进 git**），
两个插件 `GearInsight_Forever`（49 个文件）与 `XR_DungeonGuide`（33 个文件）；
`tools/extract-plugin-tables.py` 的默认 `--src` 就指这里。
进仓库的只有抽出来的快照：`src/data/upstream/`（`gi-*.json` / `xr-*.json`，20 MB），
再由 merge 层合成 `src/data/*.json`。

**取到的一样新东西**：`XR_DungeonGuide/Data_ZoneMap.lua` 的 `XR_DGDB.zonemap`——
**80 条中文区域名 → 地图号（uiMapID）**，作者自述是用它自己那份 `npcloc`（NPC→地图号+坐标）
与副本入口反推生成的，文件头写"零猜测、勿手改"。抽取：`tools/extract-xr-zonemap.py`
→ `src/data/upstream/xr-zonemap.json`（带来源、抓取日与"只取映射"的边界声明）。

**它补上了什么**：站内 73 条稀有带着百分比坐标却没有地图号（上游那份就没给这一列），
按"不猜位置"只能进列表。这份表把 73 条**全部**补到地图号，其中 **40 条本地贴图已有 → 立刻能标上图**，
剩 33 条仍缺 5 张贴图（1424 希尔斯布莱德丘陵 / 1440 灰谷 / 1449 安戈洛环形山 / 1451 希利苏斯 / 1453 暴风城）。
落地在 `merge-world.js` 里是**补位不覆盖**：只填前三层（地图 paint / 稀有与书籍分组自带 id / rareRegions）
都查不到的那些，补上的每条带 `mapIdFrom:'xr-zonemap'` 与第二条出处。
顺带把两份独立反推对了一次账，结果写进 `world.json` 的 `meta.zoneMapFill`，并由 `[6e]` 钉住：

| 对账 | 结果 |
| --- | --- |
| XR 那 80 条 vs 站内已有地图号 | 可比对 **31 条一致，冲突 0 条**；只 XR 有的区域 49 个 |
| 站内已标的 289 条稀有 | 可比对的 288 条里地图号逐条一致（1 条的区域名不在这 80 条里） |
| 36 本书 / 5 处营地 | 36/36、5/5 一致 |
| 补完之后能标点的稀有 | 289 → **329**（有稀有点位的区域 31 → 36 片） |

**坐标参照系那一问也大半有答案**：`Data_MapLoc.lua` 头部写着它的口径——
"x 西→东、y 北→南百分比，地图规范化 y 以北为 0，直接 /100"，且挂在 uiMapID 上（不是大陆图）。
这与上面那张"逐条一致"合起来看，点位按区域图摆这条基本成立。
**但两份插件的坐标可能同出一个上游**（XR 自述来源是"权威资料 forever 的 NPC 页 `g_mapperData`"），
所以算互证、不算独立两源；进游戏那一眼仍值得看，只是不再是卡住这一版的前提。

**图：一张都补不上。** 插件带的 79 个 `.tga` 全是它自己的东西——GI 的 logo 与九个渠道图标、
XR 的 9 张职业图标、25 张副本讲解插画、31 张手绘副本小图 + 3 张新本手绘图。所以：
8 张区域底图仍要那三选一（客户端 MapArt 出图 / 等 CDN 有 / 维持空态）；
缺的 2 座副本载入图是 `barrow-deeps` 与 `hyjal-summit`（还没开放的团本壳，客户端本来就没有）；
缺的 82 张首领头像插件没有头像文件，但 `Data_BossModel.lua` 有每个首领的
`CreatureDisplayInfo` 显示 id 与 `npcid`，这是头像那条的下一步线索；缺的 81 个图标同理只有文件名。

**边界写死**：`Media/` 里那些自绘副本图与讲解插画属于插件作者的创作，按红线"只取事实性标识符、
不复制别人的图与文案"，**不搬**；要用得先取得作者同意，或我们自己从客户端出。

## 二十、插件 10-19 这次更新：GI 稀有行自带地图号了；但 XR 与 DF 的坐标表是同一份（2026-10-19 实测更正）

站主说"插件更新了"，把 `~/Documents/project/.scratch/wow/` 整个重盘一遍。

### 版本与新增

| 插件 | 之前 | 现在 | 变化 |
| --- | --- | --- | --- |
| GearInsight_Forever | 0.4.29 | **0.4.32** | 稀有条数仍 338，但**每行多了 `ui=<地图号>`**、`pts=`（多个刷新点）、`rs=`（刷新间隔秒）；**24 条稀有的坐标改了值** |
| XR_DungeonGuide | 0.37.1（我们文档里的写法） | `.toc` 写 **Version: 65** | `Data_Skills` 577 → **583**；`Data_ZoneMap` 仍 80 条没变 |
| DungeonsForever | 没有 | **1.8.20（新）** | 44 个数据文件 13 MB：副本首领位置、副本入口坐标、区域→地图号、装备与商人表 |
| HandyNotes_DungeonLocations | 没有 | **1.10（新）** | 多资料片副本入口点位 |

**版本号这一层本轮改了做法**：以前 `0.4.29` / `0.37.1` 是我们手抄进脚本的，插件一升级，
每条记录的出处就变成一句过期假话。现在 `extract-plugin-tables.py` 从插件自己的 `.toc` 读
`## Version:` 写进快照 `meta.addonVersion`，`merge-spells.py` / `merge-achievements.py` /
`merge-world.js` 都从快照读，不再各抄一份。

### 一条要更正的事：那两份"独立"坐标表其实是同一份

上午我在 §十九 写「两份独立反推对账」。**这句不成立**，实测：
XR 的 `Data_MapLoc.lua`（251 条 npcId → 地图号 + 坐标 + 区域名）与 DF 的 `Data_NPCLoc.lua`（274 条）
**共同的 251 条逐字相同，一条不差，DF 只多出 23 条** —— 这是同一条管线出来的东西，不是两处独立来源。
所以"XR 的区域→地图号与站内一致 31 条"证明的是**我们没接错**，不是"游戏确认了两遍"。

那还剩下什么算互证？GI 的 `ui` 是**另一个作者、另一条管线**（它把地图号直接写在每条稀有那一行），
这一层与站内 326 条逐条一致、0 冲突——这条才算跨作者的互证。
DF 的 `Data_AreaMap.lua`（54 条 areaId→地图号）与站内 43 个带 areaId 的区域也是 43/43 一致，
但它与 XR 那张表都是"从客户端 AreaTable 那层读出来的"，同源风险同上。

**结论写死在这里**：这类"别人从客户端解出来的表"互证，证明的是**我们没抄错**，
不能用来给任何一条升 L0；升档只认官方中文页或游戏内实测。

### 地图号这一层现在的顺位

`merge-world.js` 里定成三层，① GI 行内 `ui`（与坐标同一行，最硬）→ ② 站内那三层（paint / 分组 id / rareRegions）
→ ③ XR 那张区域名对照**只补空位、不覆盖**。①② 都有值却不一致时不悄悄取舍，记进 `meta.mapIdMismatch`。
本轮结果：**326 只走 gi-ui、0 只再靠 XR 补**（XR 那层退成兜底与对账），
`mapIdFrom` 这个键现在记的是"地图号出自哪一层"。

### DF 与 HandyNotes 能不能取：先停在"不取"

**DF 的 LICENSE 写着「Copyright © 2026 圆圆 (Yuanyuan) · 保留所有权利 · All Rights Reserved」。**
它里面确实有几张是我们缺的那一层，比如：

| 表 | 是什么 | 我们这边对应什么状态 |
| --- | --- | --- |
| `Data_DungeonEntry.lua` | 24+ 座副本入口的 {地图号, x, y, 区域名} | 副本页现在**没有**入口点位，这是能做那张图的钥匙 |
| `Data_BossPos.lua` | 每座副本里各首领的坐标（键是英文名） | 我们只有首领名单与掉落，没有位置 |
| `Data_Explore.lua` | 探索者百科那批书的 itemId + 地图 + 坐标 + **一句人写的找法** | 书我们有 36 条，那句"在哪个桌上"是作者文案，按红线不取 |
| `Data_AreaMap.lua` | 54 条 areaId → 地图号 | 与站内 43/43 一致，可作对账用 |
| `Data_ClassGuide` / `Data_ClassCombat` / `Data_ClassTier` / `Data_BIS` | 职业攻略、战斗建议、分级、配装 | **红线不做**：循环提示与本站不做的强度评价；配装只认已拍板那条例外 |

我的判断是：**坐标与 ID 这类事实字段本身不受版权保护，但整表搬一家"All Rights Reserved"的
结构化数据，跟从公开网页上取一个 NPC 的坐标不是一回事**——那是复制对方整理出来的汇编。
所以这一版**一条都不取**，只把这张表记在这儿。要开这个口子得站主明确拍板（列进开放项 40），
最干净的走法是我们自己从客户端 DB2 出那份表，不搬他的。
**实测覆盖数（决定"取不取"之前先把账算清，2026-10-19）**

| DF 那张表 | 它有多少 | 我们有多少 | 取过来能补多少 |
| --- | --- | --- | --- |
| `Data_DungeonQuests`（副本任务） | 431 条 / 32 座 | 396 条 / 30 座 | 我们两份都没有的 8 座里**只补到 2 座**（沉没之城 +1、奥妮克希亚 +16）；重叠的 23 座里 **DF 更多 12 座**（差最多的是沉没的神庙 10 → 20）、相等 4 座、**我们更多 7 座** |
| `Data_DungeonEntry`（副本入口坐标） | 28 座 {地图号, x, y, 区域名} | **0**（副本页没有"入口在哪"这一层） | 整层都是新的 |
| `Data_BossPos`（本内首领位置） | 30 座 | **0** | 整层都是新的 |
| `Data_AreaMap`（areaId→地图号） | 54 条 | 43 个带 areaId 的区域 | 43/43 一致，只当对账用 |

一句结论：**DF 对我们最大的价值不是"补缺"，而是补两层我们根本没有的东西**（副本入口与本内首领位置）；
副本任务那条它只是第三家，而且我们有 7 座比它多——当对账可以，拿它覆盖我们已有的不值。

### 2026-10-19 晚：站主拍板"从插件里用吧"——副本内部底图这一类转存进来了

上面那句"不搬他的"是**我给的默认判断**，站主当天晚上明确改口："从 DungeonsForever 里面用吧，没事的"。
按项目机制，这条属于**站主拍板的例外**，落地时把风险控制做成和站内已有的"客户端原画"同一套：

| 控制项 | 怎么做 |
| --- | --- |
| 独立目录 | `src/img/art/dungeonmaps/`（27 个 `.webp` 文件覆盖 28 座本，斯坦索姆上下共用一张；744 KB），不与 CDN 素材混放 |
| 来源与日期 | 目录内 `manifest.json` 逐张记：来自哪个插件、哪个版本（XR 65 / DF 1.8.20）、原文件名、抓取日 |
| **分两类记** | 每张带 `origin`：`game-capture` 是插件作者从游戏里截下来的官方副本地图，`addon-drawn` 是作者自绘的示意图（见下面那段更正） |
| 许可原文 | manifest 里写死「DungeonsForever LICENSE：Copyright © 2026 圆圆 · 保留所有权利」，并注明这是站主拍板 |
| 可整体下线 | **删掉这个目录就回退到"首领位置只显示数字"**，不裂图、不报错；`build-data.js` 卡一条"bossMap 指向的文件必须存在"，防止留半个状态 |
| 只取图 | 作者写的任何文字说明、攻略句子、任务目标文本一律没取 |
| 页面要交代 | 溯源页另起一段（`dungeon-geo.json` 的 `meta.mapNote`，座数从成品现算）：两类分别多少座、自绘的是哪三座、文件来自哪家插件、删目录即退回数字 |
| 自绘那三座就地提醒 | **副本详情页标题旁标一句「这张是示意图，不是游戏里的地图」**（2026-10-19 深夜站主拍板）。这是"内容页只留标题与数据"的窄例外，已写进仓库根 `AGENTS.md` 素材那一条；`[6f]` 双向钉住：该标的必须标、游戏截图那 25 座不许标 |

**更正一条（同一晚逐目录看过作者自己的注释之后）**：这批图**不是一种东西**，
我第一版统一写成"插件作者绘制的副本内部图"是错的，把官方的图说成了别人画的。实际是：

- **25 座用的是游戏里那张副本地图**。文件在 `XR_DungeonGuide/Media/DungeonMaps/dmap_*.tga`，
  该目录的清单文件 `Data_DungeonMaps.lua` 第一行写着
  「v0.16.5 副本地图（血染 2026-09-29：**粉丝整理 31 张实截图**；512²/192色 TGA-RLE）」，
  同一份注释还写了"256 色 PNG 此客户端不显示，改 TGA(RLE)"和"24bpp 像素序是 BGR，
  此前按 RGB 直写导致红蓝反色"——都是**加工游戏内已有画面**才会遇到的问题。
  也就是说：**画面内容是官方的，文件是插件作者整理出来的**，和站内"客户端原画只能转存第三方"
  那一类完全同构。
- **3 座用的是插件作者自绘的示意图**：领主大厅、洛丹伦废墟、挖掘场（湿地）——
  这三座是无限新增本，**游戏内本来没有副本地图**，所以只能靠作者画。
  同一批文件（`HallOfThanes` / `RuinsOfLordaeron` / `ExcavationSite`）XR 放在 `Media/CustomMaps`、
  DF 放在 `Media/Maps`，**谁先画的判不出来**，本站按 DF 那一份记，并写明归属不明。
  这一类才是这次拍板真正新开的口子。

**为什么这一类可以谈、区域底图那 9 张不行**：副本内部图插件里确实有（XR 的 DungeonMaps 31 张 +
两家的自绘 5 张，按别名表能对上我们 28 座本里的 28 座）；区域底图插件里**一张都没有**，
逐文件名对过 0 命中，那 9 张仍然只能等客户端导出。

**这一条已经进规则了**：2026-10-19 深夜站主拍板"两件都可以"，仓库根 `AGENTS.md` 素材那一条下面
多了一个子条，写明"同一类还包含本地插件目录里转存的加工图"、两类来源怎么记、
自绘那种必须就地标一句，以及退路（删 `src/img/art/dungeonmaps/` 整目录）。


## 2026-10-20 更新插件盘点补充（未导入成品）

GI 0.5.1、XR 66；DF仍1.8.20。518个文件/157个图片的哈希清单与336件试合并差分已落 `docs/data-base/addon-update-2026-10-20/`。四张已支持事实表和GI任务payload与网站upstream相等。物品增量能补40件缺失出处，但旧合并器全量套用会使247件失去原“需要”条件行，禁止直接全量覆盖。缺失世界底图/首领头像/两座载入图未发现可直接使用的对应图片；Skyborne.tga只作为未核线索。详细证据与A01限定任务见 `docs/DATA-addon-update-2026-10-20.md`。本轮仅盘点，未改src/data；不提升任何数据分级。


### 2026-10-20 用户决策更新：最新插件优先、天裔小图标先用

最新插件事实属性允许覆盖旧值，前述暂缓覆盖不再作为阻塞；历史差分保留。网页天裔小图标采用XR随包素材作为明确例外，不冒充官方已核且不替换大幅原画。执行范围、来源记录及上线任务详见DATA-prelaunch-dispatch-2026-10-20.md与根AGENTS追加决定。本次记录决定，未执行生产数据或图片替换。

## 二十一、站主本机客户端导出（2026-10-21）——第一个"不经过任何第三方"的美术来源

前面所有素材都是"别人转存过我们再去取"，这一条不一样：**站主在自己那台装《无限》客户端的
Windows 上，用 CascLib + 自写导出器直接从客户端归档里取**，包落在仓库外
`.scratch/wow/ziliao-export/`（不进 git），并进来的动作由 `tools/import-client-export.py` 做。

| 项 | 内容 |
| --- | --- |
| 客户端 build | `70245 (WOW-70245patch1.60.1_Retail, flavor=wowf, schema=wowstatic_camelot_1_60_1)` |
| 工具 | CascLib master(3f8be47817) + 自写 `wowfexport.dll`(.NET 8) + `wdc5.py` WDC5 解析器 |
| 完整性 | 包自带 `RESULT.json`（194 条 path/bytes/sha256）；并入前逐条重算，**194/194 全对**才动盘 |
| 拿到了什么 | 物品/技能/成就图标 **160 张**（64×64 PNG → 站内统一 56×56 jpg）、载入画面 **1 张**（海加尔山 512²）、DB2 **10 张**（含 CSV 与位布局，尚未消费） |
| 没拿到（原样记，不猜） | 区域底图 9 张全 notFound（私服归档无 `MapArea`/`MapDiff`/`TextureData`，链路缺环节）；首领头像 64 只全空（51 noTexture + 13 notFound，经典 boss 头像是运行时渲的）；`8119728` 一个图标键 listfile 无同名文件；巴罗夫地穴载入图无变体；DB2 缺 8 张表 |
| 留档 | `src/data/upstream/client-export-2026-10-21.json`：build、工具、逐文件 sha256、以及导出方自己写的那串"哪些没拿到、为什么"（**原样存，不改写不摘要**） |
| 边界 | 只取图标与载入画面这类**素材文件本身**；DB2 里的文本列在没有逐列核对前一律不取（WDC5 的 CSV 是 `f0..fN` 索引列，猜列名=编数据）；`ItemSparse` 若只有 enUS 名，按红线不机翻 |
| 分级 | 这批图**不因此升 L0**——它证明的是"客户端里长这样"，不是"官方中文页这么写"。名称类记录仍按各自原有出处与分级 |

一句判断：**这一层真正的价值不是补上 160 个图标，是把"还能从客户端拿什么"这个问题变成了可测的**——
底图拿不到是链路缺表（判死），头像拿不到是客户端根本没有肖像文件（判成结论），
DB2 拿到了但列含义没核（判成下一单）。三种"拿不到"性质不一样，别再混成一句"等客户端导出"。

### 2026-10-22：排队表按客户端 build 70532 重取——内容一条没变，但挖出一个出处重复的缺陷

`src/data/queue.json` 的构建戳停在 `1.60.1.70338`（2026-10-11 取），而站主的客户端已经到 **70532**。
按 `tools/fetch-db2-groupfinder.py --build 1.60.1.70532` 重取后逐字节比了三份：
**70338 / 70450 / 70532 的 `GroupFinderActivity`（109 条）与 `GroupFinderCategory`（5 条）完全相同**
——同一张表 9265 字节、0 个字段变化。所以过期的是那个戳，不是数据；
副本页与团本页那些"客户端里还有另一条排队条目"的并列判断没有建立在旧名单上。

**顺带修掉一个我们自己的缺陷**（`tools/merge-dungeons.js`）：给每座本挂"排队表出处"时，
去重比的是**整条 url**，而 url 里带 `?build=` 号——于是每重取一次就多挂一行同表出处。
10-10 与 10-11 两次重取已经把 `70334`、`70338` 两行留在 31 座本的来源清单里，
界面上"来源"点开会看到同一张表出现两三次，只是日期不同。
现在改成按"同类型 + 同表（去掉 build 参数）"去重，只留最新一次，旧的两行已清掉。
**这条与红线不冲突**：红线说的"两源分歧两个都留"指的是**不同来源**（比如官方公告与参考站卡片两个等级区间），
不是同一张表的旧版本；把旧 build 的转述记录一直挂着，只会让人以为我们同时参考了三个来源。

## 二十二、名录 10-22 重采与 `_shuju` 接口清单更正（2026-10-22 实测）

**一句话**：参考站的物品名录涨到 21,296 件并整体重算了与经典旧世的对照；
同时我们文档里"`_shuju` 数据包只有三个文件"这句**过时了，实测是 9 个**。

### 名录这次跟到了什么

`tools/scrape-wclbox-items.py` 全量重跑：107 页 / **21,296 件**（旧快照 10-13 是 106 页 / 21,077）。
四类变化：**新增 228、下架 9、改名 42、状态翻转 2,795**（其中 2,496 件从"有改动"变"没有变化"）。
四格总量：不变 7,678→10,146、有改动 6,102→3,873、无限中没有 1,944→1,705、无限新增 5,346→5,565。

**逐类的口径与取证都写在 `DATA-ITEMS-REFRESH-2026-10-22.md`**，这里只记两条与"来源"有关的结论：

1. **那 2,496 件的翻转是参考站自己重算对照的结果，我们没有任何独立依据判断对不对**。
   它页面顶部写"当前版本 1.60.1.70450 Beta"、`_shuju` meta 里 `classicBuild=1.15.9.70003`，
   但**页面上没留一句说明**。我们跟了（站主拍板"四类都跟"），性质是**可回退的跟随**，
   不是本站确认过的事实。客户端侧对不了属性——那台装的 DB2 文本是韩文。
2. **下架的 9 件不是抓取漏行**：逐件直接请求详情页，7 件实测 **404 找不到这个页面**，
   对照组（仍在名录的 285352）返回 200 且标题正常。索引与详情页同时消失 = 真下架。

### `_shuju` 数据包接口清单（更正第十一节以来的旧说法）

我们文档里一直写"这个静态数据包里只有 `meta` / `changes` / `dungeons` 三个文件，
**物品没有批量接口**"。**2026-10-22 逐个探，现在能取到 9 个**：

```
/_shuju/<发布号>/meta.json         407 B    build 号、launchAt/betaOpenAt/dropsAsOf、counts
/_shuju/<发布号>/changes.json      1.67 MB  967 条改动（与我们成品条数一致）
/_shuju/<发布号>/dungeons.json     14.9 KB  35 座
/_shuju/<发布号>/chengjiu.json     25.4 KB  ★ 成就，但只有 46 条（不是全量 211，别指望它补齐）
/_shuju/<发布号>/professions.json  164 KB   ★ 13 个专业的配方
/_shuju/<发布号>/legacy.json       59 KB    ★ 传承：perks 21 / challenges 6 / research 4 / tree 8 / items 27
/_shuju/<发布号>/xiyou.json        24.7 KB  ★ 稀有：zones 8 / unplaced 23 / count
/_shuju/<发布号>/shuji.json        19.8 KB  ★ 书籍：zones 25 / missing 2
/_shuju/<发布号>/shuidai.json      8.5 KB   ★ 水袋：items 17 / stops 4 / bag 8
（items / spells / world / talents / fashu / wupin / ditu / gear / rare 这些名字仍然 404）
```

**意义**：带 ★ 的五类我们现在都是**从网页 DOM 抓的**，其实有 JSON 可直取——
少一层解析、少一类抄错的可能，`audit-translations.py` 的逐字回查也好做。
**下一轮采集这三类（专业 / 传承 / 世界点位）时应优先走 JSON**，页面抓取留作对照。
另外 `chengjiu.json` 只有 46 条这件事要记牢：**成就的全量仍然是"GI 目录 + 46 条可回查"**，
别因为看到有个 `chengjiu.json` 就以为成就升档了。

### 顺手清掉的写死数字

`app/src/router.js`、`ItemsPage.vue` 两处注释、`scrape-wclbox-items.py` 与
`extract-gi-item-existence.py` 的 docstring 里都写着"21,077 件"，**全部改成指向 `scale.json`**。
这个数每跟一次名录就会变，抄在代码注释里必然过期（同类问题已经犯过四次）。
