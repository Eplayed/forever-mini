# 译名体检报告 · 2026-10-28（wow-data）

脚本：`python3 tools/audit-translations.py`。做法是把每个对外展示的中文名（术语词条、副本名、系统名，以及时间线、技能四态、种族页引用的官方整句）拿回它自己在 `provenance` 里声明的官方来源页做逐字包含比对。**只读核对，不改数据。**

## 结果

| 项 | 数 |
| --- | --- |
| 词条总数 | 3931 |
| 在声明的官方页里逐字命中 | 1111 |
| 去掉汉字间排版空格才命中（要人眼确认） | 44 |
| **未命中（要人工回原文看）** | 912 |
| 已人工判定并留痕（见 audit-exceptions.json） | 2 |
| **声称官方却核不到（L0/L1 缺官方链接）** | 0 |
| 只有插件来源、按设计就没有可回查网页 | 1862 |
| 本来就标 L2/L3 的非官方中文名（预期，界面已如实标注） | 0 |

核对范围（按进来的条目数，全部从成品现算）：世界掉落 1569 条、改动清单 967 条、法术书 498 条、世界稀有 362 条、术语 215 条、技能四态 86 条、成就 46 条、种族特长 40 条、世界书籍 36 条、副本 35 条、传承专长 21 条、系统 11 条、时间线 11 条、种族简介 10 条、亮点组合 7 条、书籍奖励 4 条、传承奖励 4 条、世界套装 3 条、书籍称号 3 条、图书管理员 2 条、天裔导语 1 条。区域名不在这批：它来自结构化接口而不是页面正文，由 build-data.js 的两套 mapId 交叉验证把关；天赋与法术、传承与成就都只核名称，句子本站不存，也就没有可核的对象。
| 命中率 | 28.3% |

## 来源页

| 状态 | 页面 | 承担词条 |
| --- | --- | --- |
| 缓存 | https://wow.blizzard.cn/news/24301515/index.html | 143 |
| 缓存 | https://wow.blizzard.cn/news/24303313/index.html | 7 |
| 缓存 | https://wow.blizzard.cn/news/24301514/index.html | 74 |
| 缓存 | https://wow.blizzard.cn/news/24304075/index.html | 95 |
| 缓存 | https://news.blizzard.com/en-us/article/24303862/world-of-warcraft-forever-whats-next-panel-recap | 14 |
| 缓存 | https://wow.blizzard.cn/news/24304160/index.html | 9 |
| 缓存 | https://wowforever.wclbox.com/fuben/hall-of-thanes/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/ruins-of-lordaeron/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/excavation-site/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/city-of-dalaran/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/the-drowned-city/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/kroldok-stronghold/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/alcaz-prison/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/blackmaw-hold/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/shapers-terrace/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/ragefire-chasm/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/wailing-caverns/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/the-deadmines/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/shadowfang-keep/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/blackfathom-deeps/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/the-stockade/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/gnomeregan/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/razorfen-kraul/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/scarlet-monastery-graveyard/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/scarlet-monastery-library/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/scarlet-monastery-armory/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/razorfen-downs/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/scarlet-monastery-cathedral/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/uldaman/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/zulfarrak/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/maraudon/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/sunken-temple/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/blackrock-depths/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/dire-maul-east/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/lower-blackrock-spire/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/dire-maul-north/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/dire-maul-west/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/scholomance/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/stratholme-main-gate/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/stratholme-service-gate/ | 1 |
| 缓存 | https://wowforever.wclbox.com/fuben/upper-blackrock-spire/ | 1 |
| 缓存 | https://wow.blizzard.cn/news/24302070/index.html | 2 |
| 缓存 | https://worldofwarcraft.blizzard.com/en-us/forever | 2 |
| 缓存 | https://wow.blizzard.cn/news/24302097/index.html | 20 |
| 缓存 | https://wow.blizzard.cn/news/24310968/index.html | 28 |
| 缓存 | https://wowforever.wclbox.com/xiyou | 72 |
| 缓存 | https://wowforever.wclbox.com/shuji | 45 |
| 缓存 | https://wowforever.wclbox.com/gaidong | 967 |
| 缓存 | https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json | 967 |
| 缓存 | https://wowforever.wclbox.com/fashu/warrior | 41 |
| 缓存 | https://wowforever.wclbox.com/fashu/paladin | 56 |
| 缓存 | https://wowforever.wclbox.com/fashu/hunter | 58 |
| 缓存 | https://wowforever.wclbox.com/fashu/rogue | 56 |
| 缓存 | https://wowforever.wclbox.com/fashu/priest | 56 |
| 缓存 | https://wowforever.wclbox.com/fashu/shaman | 56 |
| 缓存 | https://wowforever.wclbox.com/fashu/mage | 61 |
| 缓存 | https://wowforever.wclbox.com/fashu/warlock | 55 |
| 缓存 | https://wowforever.wclbox.com/fashu/druid | 59 |
| 缓存 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json | 46 |
| 缓存 | https://wowforever.wclbox.com/chuancheng | 25 |
| 缓存 | https://wowforever.wclbox.com/_shuju/r-1792720578447/legacy.json | 25 |

## 只在去掉排版空格后命中（人工确认这几条）

官方页用加粗标签强调词的一部分时，转成纯文本会在汉字中间留下空格。下列词条属于这种情况，**脚本没法替你判断是不是同一个词，要人眼过一遍**。

| 词条 | id | 职业 | 出处 | 原文片段 |
| --- | --- | --- | --- | --- |
| 被遗忘者的意志：移除魅惑、恐惧和催眠效果。 | `undead/被遗忘者的意志` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 从这片土地上彻底清除。被遗忘者甚至不在乎自己的盟友；对他们而言，部落只是推进黑暗图谋的工具。被遗忘者的意志：移除魅惑、恐惧和催眠效果。食尸：吞噬尸体，在持续时间内恢复35%的生命值和法力值。水下呼吸（被动）：在水下的呼吸时间延 |
| 食尸：吞噬尸体，在持续时间内恢复35%的生命值和法力值。 | `undead/食尸` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 己的盟友；对他们而言，部落只是推进黑暗图谋的工具。被遗忘者的意志：移除魅惑、恐惧和催眠效果。食尸：吞噬尸体，在持续时间内恢复35%的生命值和法力值。水下呼吸（被动）：在水下的呼吸时间延长300%。哀伤之触（被动）：你的攻击有时会吸取生命值。 |
| 水下呼吸（被动）：在水下的呼吸时间延长300%。 | `undead/水下呼吸` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 者的意志：移除魅惑、恐惧和催眠效果。食尸：吞噬尸体，在持续时间内恢复35%的生命值和法力值。水下呼吸（被动）：在水下的呼吸时间延长300%。哀伤之触（被动）：你的攻击有时会吸取生命值。牛头人牛头人始终致力于维护自然平衡，并遵从他们所 |
| 哀伤之触（被动）：你的攻击有时会吸取生命值。 | `undead/哀伤之触` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 体，在持续时间内恢复35%的生命值和法力值。水下呼吸（被动）：在水下的呼吸时间延长300%。哀伤之触（被动）：你的攻击有时会吸取生命值。牛头人牛头人始终致力于维护自然平衡，并遵从他们所信奉的女神——大地母亲的意志。不久前，凶残的 |
| 战争践踏：使附近的敌人昏迷，持续2秒。 | `tauren/战争践踏` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 下击败了入侵者。为了报答这份以血换来的恩情，牛头人加入部落，进一步巩固了两个种族之间的友谊。战争践踏：使附近的敌人昏迷，持续2秒。栽培：额外长出无需草药学即可采集的草药。原野疾驰（被动）：持续移动时，移动速度会逐渐提高。耐 |
| 栽培：额外长出无需草药学即可采集的草药。 | `tauren/栽培` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 恩情，牛头人加入部落，进一步巩固了两个种族之间的友谊。战争践踏：使附近的敌人昏迷，持续2秒。栽培：额外长出无需草药学即可采集的草药。原野疾驰（被动）：持续移动时，移动速度会逐渐提高。耐久（被动）：总生命值提高5%，命中几率提 |
| 原野疾驰（被动）：持续移动时，移动速度会逐渐提高。 | `tauren/原野疾驰` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 族之间的友谊。战争践踏：使附近的敌人昏迷，持续2秒。栽培：额外长出无需草药学即可采集的草药。原野疾驰（被动）：持续移动时，移动速度会逐渐提高。耐久（被动）：总生命值提高5%，命中几率提高1%。巨魔凶悍的暗矛部族巨魔曾以荆棘谷的丛林为家 |
| 耐久（被动）：总生命值提高5%，命中几率提高1%。 | `tauren/耐久` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 。栽培：额外长出无需草药学即可采集的草药。原野疾驰（被动）：持续移动时，移动速度会逐渐提高。耐久（被动）：总生命值提高5%，命中几率提高1%。巨魔凶悍的暗矛部族巨魔曾以荆棘谷的丛林为家，却因各方的连年征战而被逐出了故土。后来，巨魔与兽 |
| 狂暴：施法速度和攻击速度提高10%，持续10秒。 | `troll/狂暴` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 萨尔说服他们随自己前往卡利姆多。尽管暗矛巨魔仍坚守其幽暗传统，他们在部落中依然享有崇高地位。狂暴：施法速度和攻击速度提高10%，持续10秒。极速再生：在持续时间内恢复50%的最大生命值。野兽杀手（被动）：对野兽造成的伤害提高5%。再 |
| 极速再生：在持续时间内恢复50%的最大生命值。 | `troll/极速再生` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 守其幽暗传统，他们在部落中依然享有崇高地位。狂暴：施法速度和攻击速度提高10%，持续10秒。极速再生：在持续时间内恢复50%的最大生命值。野兽杀手（被动）：对野兽造成的伤害提高5%。再生（被动）：在战斗中保持10%的生命值恢复。塑 |
| 野兽杀手（被动）：对野兽造成的伤害提高5%。 | `troll/野兽杀手` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 暴：施法速度和攻击速度提高10%，持续10秒。极速再生：在持续时间内恢复50%的最大生命值。野兽杀手（被动）：对野兽造成的伤害提高5%。再生（被动）：在战斗中保持10%的生命值恢复。塑风者天裔塑风者是首批获赐风之灵“天穹视界”天 |
| 再生（被动）：在战斗中保持10%的生命值恢复。 | `troll/再生` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 。极速再生：在持续时间内恢复50%的最大生命值。野兽杀手（被动）：对野兽造成的伤害提高5%。再生（被动）：在战斗中保持10%的生命值恢复。塑风者天裔塑风者是首批获赐风之灵“天穹视界”天赋的申多雷高等精灵的后裔。如今，新一代的塑风者 |
| 踏空而行：在空中向下滑行10秒。 | `skyborne-horde/踏空而行` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 。他们决心查明元素导师失踪的真相，并不惜一切代价迎回风之灵，誓死捍卫他们世代相传的生存之道。踏空而行：在空中向下滑行10秒。天穹视界：获得元素祝福，移动速度提高10%。风灵护佑（被动）：近战、远程与法术急速提高1%。 |
| 天穹视界：获得元素祝福，移动速度提高10%。 | `skyborne-horde/天穹视界` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | ，并不惜一切代价迎回风之灵，誓死捍卫他们世代相传的生存之道。踏空而行：在空中向下滑行10秒。天穹视界：获得元素祝福，移动速度提高10%。风灵护佑（被动）：近战、远程与法术急速提高1%。元素洞察（被动）：对元素生物造成的伤害提高5 |
| 风灵护佑（被动）：近战、远程与法术急速提高1%。 | `skyborne-horde/风灵护佑` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 相传的生存之道。踏空而行：在空中向下滑行10秒。天穹视界：获得元素祝福，移动速度提高10%。风灵护佑（被动）：近战、远程与法术急速提高1%。元素洞察（被动）：对元素生物造成的伤害提高5%。联盟高贵、荣誉、信仰、正义与牺牲的光荣传统， |
| 元素洞察（被动）：对元素生物造成的伤害提高5%。 | `skyborne-horde/元素洞察` | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html | 天穹视界：获得元素祝福，移动速度提高10%。风灵护佑（被动）：近战、远程与法术急速提高1%。元素洞察（被动）：对元素生物造成的伤害提高5%。联盟高贵、荣誉、信仰、正义与牺牲的光荣传统，将联盟诸族紧密团结在一起。联盟各族贡献出技术、奥 |
| 生存意志：移除昏迷效果。 | `human/生存意志` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 一些最伟大的王国。在这个动荡的时代，历经世代纷争的人类正努力重振昔日荣光，开创光明的新未来。生存意志：移除昏迷效果。感知：侦测潜行的敌人，持续20秒。剑类武器专精（被动）：剑类使法术和技能的爆击几率提高2%。 |
| 感知：侦测潜行的敌人，持续20秒。 | `human/感知` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 动荡的时代，历经世代纷争的人类正努力重振昔日荣光，开创光明的新未来。生存意志：移除昏迷效果。感知：侦测潜行的敌人，持续20秒。剑类武器专精（被动）：剑类使法术和技能的爆击几率提高2%。人类精魂（被动）：精神提高5%。矮 |
| 剑类武器专精（被动）：剑类使法术和技能的爆击几率提高2%。 | `human/剑类武器专精` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 力重振昔日荣光，开创光明的新未来。生存意志：移除昏迷效果。感知：侦测潜行的敌人，持续20秒。剑类武器专精（被动）：剑类使法术和技能的爆击几率提高2%。人类精魂（被动）：精神提高5%。矮人往昔，矮人只在乎从大地深处发掘的财富。后来，出土的文献记 |
| 人类精魂（被动）：精神提高5%。 | `human/人类精魂` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 感知：侦测潜行的敌人，持续20秒。剑类武器专精（被动）：剑类使法术和技能的爆击几率提高2%。人类精魂（被动）：精神提高5%。矮人往昔，矮人只在乎从大地深处发掘的财富。后来，出土的文献记载，有一个神祇般的种族赋予矮人生 |
| 石像形态：免疫流血、中毒和疾病效果，并降低受到的物理伤害，持续8秒。 | `dwarf/石像形态` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 多种族起源的真相，矮人全心投入寻找失落的神器与远古知识。如今，矮人考古学家已经遍布世界各地。石像形态：免疫流血、中毒和疾病效果，并降低受到的物理伤害，持续8秒。寻找财宝：追踪附近的宝箱。锤类武器专精（被动）：锤类使法术和技能的爆击几率提高1%。王牌猎人 |
| 寻找财宝：追踪附近的宝箱。 | `dwarf/寻找财宝` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 古学家已经遍布世界各地。石像形态：免疫流血、中毒和疾病效果，并降低受到的物理伤害，持续8秒。寻找财宝：追踪附近的宝箱。锤类武器专精（被动）：锤类使法术和技能的爆击几率提高1%。王牌猎人（被动）：对野兽造成的伤害 |
| 锤类武器专精（被动）：锤类使法术和技能的爆击几率提高1%。 | `dwarf/锤类武器专精` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 像形态：免疫流血、中毒和疾病效果，并降低受到的物理伤害，持续8秒。寻找财宝：追踪附近的宝箱。锤类武器专精（被动）：锤类使法术和技能的爆击几率提高1%。王牌猎人（被动）：对野兽造成的伤害提高5%。暗夜精灵一万年前，暗夜精灵建立了一个庞大的帝国， |
| 王牌猎人（被动）：对野兽造成的伤害提高5%。 | `dwarf/王牌猎人` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 续8秒。寻找财宝：追踪附近的宝箱。锤类武器专精（被动）：锤类使法术和技能的爆击几率提高1%。王牌猎人（被动）：对野兽造成的伤害提高5%。暗夜精灵一万年前，暗夜精灵建立了一个庞大的帝国，但他们对原始魔法的恣意使用最终带来了毁灭。悲 |
| 艾露恩之光：爆击几率提高10%，持续15秒。 | `night-elf/艾露恩之光` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 到宿敌燃烧军团再度归来。别无选择的暗夜精灵终于走出隐居之地，为自己在新世界中的立足之地而战。艾露恩之光：爆击几率提高10%，持续15秒。影遁：在静止时获得潜行状态。迅捷（被动）：躲闪几率提高1%，移动速度提高2%。精灵之魂（被动 |
| 影遁：在静止时获得潜行状态。 | `night-elf/影遁` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 于走出隐居之地，为自己在新世界中的立足之地而战。艾露恩之光：爆击几率提高10%，持续15秒。影遁：在静止时获得潜行状态。迅捷（被动）：躲闪几率提高1%，移动速度提高2%。精灵之魂（被动）：死亡时的移动速度提高75 |
| 迅捷（被动）：躲闪几率提高1%，移动速度提高2%。 | `night-elf/迅捷` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 界中的立足之地而战。艾露恩之光：爆击几率提高10%，持续15秒。影遁：在静止时获得潜行状态。迅捷（被动）：躲闪几率提高1%，移动速度提高2%。精灵之魂（被动）：死亡时的移动速度提高75%。侏儒卡兹莫丹的侏儒虽然身材矮小，却凭借过人的智 |
| 精灵之魂（被动）：死亡时的移动速度提高75%。 | `night-elf/精灵之魂` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | ，持续15秒。影遁：在静止时获得潜行状态。迅捷（被动）：躲闪几率提高1%，移动速度提高2%。精灵之魂（被动）：死亡时的移动速度提高75%。侏儒卡兹莫丹的侏儒虽然身材矮小，却凭借过人的智慧在历史上占据了一席之地。他们的地下王国诺莫瑞 |
| 逃命专家：短暂免疫定身和诱捕效果。 | `gnome/逃命专家` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 人大举入侵导致这座城市最终沦陷。如今，这座城市的建造者流落在矮人的土地上，竭尽所能协助盟友。逃命专家：短暂免疫定身和诱捕效果。我知道了！：使接下来的3个法术或技能消耗降低，伤害或治疗效果提高10%。开阔思维（被动）：法 |
| 我知道了！：使接下来的3个法术或技能消耗降低，伤害或治疗效果提高10%。 | `gnome/我知道了！` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 今，这座城市的建造者流落在矮人的土地上，竭尽所能协助盟友。逃命专家：短暂免疫定身和诱捕效果。我知道了！：使接下来的3个法术或技能消耗降低，伤害或治疗效果提高10%。开阔思维（被动）：法力值、怒气值或能量值上限提高5%。工程学专精（被动）：工程学装置更加可靠 |
| 开阔思维（被动）：法力值、怒气值或能量值上限提高5%。 | `gnome/开阔思维` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 免疫定身和诱捕效果。我知道了！：使接下来的3个法术或技能消耗降低，伤害或治疗效果提高10%。开阔思维（被动）：法力值、怒气值或能量值上限提高5%。工程学专精（被动）：工程学装置更加可靠。高阶会天裔高阶会的成员皆是古代埃雷萨拉斯上层精灵学者 |
| 工程学专精（被动）：工程学装置更加可靠。 | `gnome/工程学专精` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 能消耗降低，伤害或治疗效果提高10%。开阔思维（被动）：法力值、怒气值或能量值上限提高5%。工程学专精（被动）：工程学装置更加可靠。高阶会天裔高阶会的成员皆是古代埃雷萨拉斯上层精灵学者的后裔。风之灵从泽风岛销声匿迹后，高阶会 |
| 踏空而行：在空中向下滑行10秒。 | `skyborne-alliance/踏空而行` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 。他们决心查明元素导师失踪的真相，并不惜一切代价迎回风之灵，誓死捍卫他们世代相传的生存之道。踏空而行：在空中向下滑行10秒。天穹视界：获得元素祝福，移动速度提高10%。风灵护佑（被动）：近战、远程与法术急速提高1%。 |
| 阅读魔网：激活一条魔网，生命与法力恢复速度提高100%。 | `skyborne-alliance/阅读魔网` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 落的奥术知识，并以此为力量，让申多雷重获主宰自身命运的能力。踏空而行：在空中向下滑行10秒。阅读魔网：激活一条魔网，生命与法力恢复速度提高100%。风灵护佑（被动）：近战、远程与法术急速提高1%。元素洞察（被动）：对元素生物造成的伤害提高5 |
| 风灵护佑（被动）：近战、远程与法术急速提高1%。 | `skyborne-alliance/风灵护佑` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 相传的生存之道。踏空而行：在空中向下滑行10秒。天穹视界：获得元素祝福，移动速度提高10%。风灵护佑（被动）：近战、远程与法术急速提高1%。元素洞察（被动）：对元素生物造成的伤害提高5%。联盟高贵、荣誉、信仰、正义与牺牲的光荣传统， |
| 元素洞察（被动）：对元素生物造成的伤害提高5%。 | `skyborne-alliance/元素洞察` | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html | 天穹视界：获得元素祝福，移动速度提高10%。风灵护佑（被动）：近战、远程与法术急速提高1%。元素洞察（被动）：对元素生物造成的伤害提高5%。联盟高贵、荣誉、信仰、正义与牺牲的光荣传统，将联盟诸族紧密团结在一起。联盟各族贡献出技术、奥 |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | `combo-兽人法师` | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html | X X X X X 暗夜精灵 X X X X X 天裔 X X X X X 全新及亮点组合《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。种族特长每个可玩种族都有独特的种族特长。在艾泽拉斯冒险时，这些特长会在所选职业之外，为角色增 |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | `combo-巨魔术士` | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html | X X X X X 暗夜精灵 X X X X X 天裔 X X X X X 全新及亮点组合《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。种族特长每个可玩种族都有独特的种族特长。在艾泽拉斯冒险时，这些特长会在所选职业之外，为角色增 |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | `combo-亡灵圣骑士` | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html | X X X X X 暗夜精灵 X X X X X 天裔 X X X X X 全新及亮点组合《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。种族特长每个可玩种族都有独特的种族特长。在艾泽拉斯冒险时，这些特长会在所选职业之外，为角色增 |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | `combo-人类猎人` | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html | X X X X X 暗夜精灵 X X X X X 天裔 X X X X X 全新及亮点组合《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。种族特长每个可玩种族都有独特的种族特长。在艾泽拉斯冒险时，这些特长会在所选职业之外，为角色增 |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | `combo-侏儒牧师` | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html | X X X X X 暗夜精灵 X X X X X 天裔 X X X X X 全新及亮点组合《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。种族特长每个可玩种族都有独特的种族特长。在艾泽拉斯冒险时，这些特长会在所选职业之外，为角色增 |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | `combo-矮人萨满祭司` | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html | X X X X X 暗夜精灵 X X X X X 天裔 X X X X X 全新及亮点组合《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。种族特长每个可玩种族都有独特的种族特长。在艾泽拉斯冒险时，这些特长会在所选职业之外，为角色增 |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | `combo-天裔` | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html | X X X X X 暗夜精灵 X X X X X 天裔 X X X X X 全新及亮点组合《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。种族特长每个可玩种族都有独特的种族特长。在艾泽拉斯冒险时，这些特长会在所选职业之外，为角色增 |
| 天裔是《魔兽世界》：“无限”中的全新可玩种族，并将以独特的身份参与逐步展开的故事。选择这一新种族时，玩家可以选择加入部落阵营、能够成为萨满祭司的塑风者天裔，或加入联盟阵营、能够成为法师的高阶会天裔。 | `skyborne-note` | 天裔导语 引用 | https://wow.blizzard.cn/news/24304075/index.html | 族与职业组合，或以天裔角色开启旅程。每一种选择，都能让你以不同的方式踏入艾泽拉斯的下一篇章。天裔是《魔兽世界》：“无限”中的全新可玩种族，并将以独特的身份参与逐步展开的故事。选择这一新种族时，玩家可以选择加入部落阵营、能够成为萨满祭司的塑风者天裔，或加入联盟阵营、能够成为法师的高阶会天裔。了解职业创建角色时，除了考虑自己想玩的职业，也要留意哪些种族能够选择该职业。九种可选职业各自 |

## 已人工判定并留痕

这些条目没能逐字命中，但已回原文人工判定并把依据写进 `app/data/audit-exceptions.json`。

| 词条 | 结论 | 官方原句 | 判定日期 |
| --- | --- | --- | --- |
| 冰霜陷阱（术语） | keep-L0 | 冰霜 与 火焰 陷阱现在分别计算冷却时间 | 2026-10-08 |
| 火焰陷阱（术语） | keep-L0 | 陷阱现在可在战斗中使用，但冷却时间延长至30秒。冰霜与火焰陷阱现在分别计算冷却时间 | 2026-10-10 |

## 未命中清单（逐条待人工核对）

未命中不等于词条错，常见原因是：官方页用的是另一个写法、词条是从同系列另一篇文章采的、或页面改版删了这段。**但在人工确认之前，这些条目的 L0 身份不可信。**

| 名称 | 出处 | 标识 | 当前级别 | 声明来源 |
| --- | --- | --- | --- | --- |
| 永久 60 级 | 系统 | level-cap | L2 | https://news.blizzard.com/en-us/article/24303862/world-of-warcraft-forever-whats-next-panel-recap<br>https://wow.blizzard.cn/news/24304160/index.html |
| 海加尔山 | 系统 | zone-mount-hyjal | L3 | https://worldofwarcraft.blizzard.com/en-us/forever |
| 你可以预购天裔史诗礼包，在2026年10月6日的《魔兽世界》：“无限”国服Beta | 时间线 | cn-beta-open | L0 | https://wow.blizzard.cn/news/24304160/index.html |
| 《魔兽世界》：“无限”将于2026年11月5日全球同步上线 | 时间线 | launch-cn | L0 | https://wow.blizzard.cn/news/24304160/index.html |
| 偏斜 | 改动清单 | calc-warrior-arms-deflection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 横扫攻击 | 改动清单 | calc-warrior-arms-sweeping-strikes | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化断筋 | 改动清单 | calc-warrior-arms-improved-hamstring | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致死打击 | 改动清单 | calc-warrior-arms-mortal-strike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化拦截 | 改动清单 | calc-warrior-fury-improved-intercept | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 战斗姿态 | 改动清单 | spellbook-warrior-battle-stance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 断筋 | 改动清单 | spellbook-warrior-hamstring | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 惩戒痛击 | 改动清单 | spellbook-warrior-mocking-blow | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 反击风暴 | 改动清单 | spellbook-warrior-retaliation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 乘胜追击 | 改动清单 | spellbook-warrior-victory-rush | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 破胆怒吼 | 改动清单 | spellbook-warrior-intimidating-shout | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 挑战怒吼 | 改动清单 | spellbook-warrior-challenging-shout | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 狂暴姿态 | 改动清单 | spellbook-warrior-berserker-stance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 拦截 | 改动清单 | spellbook-warrior-intercept | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 旋风斩 | 改动清单 | spellbook-warrior-whirlwind | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 拳击 | 改动清单 | spellbook-warrior-pummel | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 鲁莽 | 改动清单 | spellbook-warrior-recklessness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 防御姿态 | 改动清单 | spellbook-warrior-defensive-stance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致命守护 | 改动清单 | calc-hunter-beast-mastery-deadly-aspects | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 耐久训练 | 改动清单 | calc-hunter-beast-mastery-endurance-training | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 集中火力 | 改动清单 | calc-hunter-beast-mastery-focused-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化灵猴守护 | 改动清单 | calc-hunter-beast-mastery-improved-aspect-of-the-monkey | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 寻路 | 改动清单 | calc-hunter-beast-mastery-pathfinding | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化复活宠物 | 改动清单 | calc-hunter-beast-mastery-improved-revive-pet | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野兽迅捷 | 改动清单 | calc-hunter-beast-mastery-bestial-swiftness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 狂怒释放 | 改动清单 | calc-hunter-beast-mastery-unleashed-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化治疗宠物 | 改动清单 | calc-hunter-beast-mastery-improved-mend-pet | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 凶暴 | 改动清单 | calc-hunter-beast-mastery-ferocity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤雄鹰 | 改动清单 | calc-hunter-beast-mastery-summon-hawk | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵魂联结 | 改动清单 | calc-hunter-beast-mastery-spirit-bond | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 胁迫 | 改动清单 | calc-hunter-beast-mastery-intimidation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野兽戒律 | 改动清单 | calc-hunter-beast-mastery-bestial-discipline | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 狂乱 | 改动清单 | calc-hunter-beast-mastery-frenzy | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 狂野怒火 | 改动清单 | calc-hunter-beast-mastery-bestial-wrath | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 鹰眼 | 改动清单 | calc-hunter-marksmanship-hawk-eye | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化震荡射击 | 改动清单 | calc-hunter-marksmanship-improved-concussive-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致命攻击 | 改动清单 | calc-hunter-marksmanship-lethal-attacks | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化钉刺 | 改动清单 | calc-hunter-marksmanship-improved-stings | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 效率 | 改动清单 | calc-hunter-marksmanship-efficiency | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精确瞄准 | 改动清单 | calc-hunter-marksmanship-careful-aim | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 疾速杀戮 | 改动清单 | calc-hunter-marksmanship-rapid-killing | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化奥术射击 | 改动清单 | calc-hunter-marksmanship-improved-arcane-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 独来独往 | 改动清单 | calc-hunter-marksmanship-lone-wolf | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强击光环 | 改动清单 | calc-hunter-marksmanship-trueshot-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致死射击 | 改动清单 | calc-hunter-marksmanship-mortal-shots | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 急速恢复 | 改动清单 | calc-hunter-marksmanship-rapid-recuperation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 弹幕 | 改动清单 | calc-hunter-marksmanship-barrage | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 驱散射击 | 改动清单 | calc-hunter-marksmanship-scatter-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 远程武器专精 | 改动清单 | calc-hunter-marksmanship-ranged-weapon-specialization | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 狙击 | 改动清单 | calc-hunter-marksmanship-sniper-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化追踪 | 改动清单 | calc-hunter-survival-improved-tracking | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 偏斜 | 改动清单 | calc-hunter-survival-deflection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 诱捕 | 改动清单 | calc-hunter-survival-entrapment | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野蛮打击 | 改动清单 | calc-hunter-survival-savage-strikes | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 生存专家 | 改动清单 | calc-hunter-survival-survivalist | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化摔绊 | 改动清单 | calc-hunter-survival-improved-wing-clip | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵巧陷阱 | 改动清单 | calc-hunter-survival-clever-traps | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 稳固 | 改动清单 | calc-hunter-survival-surefooted | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 威慑 | 改动清单 | calc-hunter-survival-deterrence | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 生存战术 | 改动清单 | calc-hunter-survival-survival-tactics | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 掠食者之锋 | 改动清单 | calc-hunter-survival-predator-s-edge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 反击 | 改动清单 | calc-hunter-survival-counterattack | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 游刃有余 | 改动清单 | calc-hunter-survival-resourcefulness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暴露猎物 | 改动清单 | calc-hunter-survival-expose-prey | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 生存专家的戒律 | 改动清单 | calc-hunter-survival-survivalist-s-discipline | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 陆行鸟踢击 | 改动清单 | calc-hunter-survival-strider-kick | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闪电反射 | 改动清单 | calc-hunter-survival-lightning-reflexes | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 裂伤打击 | 改动清单 | calc-hunter-survival-lacerating-strikes | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化野兽之眼 | 改动清单 | hunter-improved-eyes-of-the-beast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 厚皮 | 改动清单 | hunter-thick-hide | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化猎人印记 | 改动清单 | hunter-improved-hunter-s-mark | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 瞄准射击 | 改动清单 | hunter-aimed-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化毒蛇钉刺 | 改动清单 | hunter-improved-serpent-sting | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化毒蝎钉刺 | 改动清单 | hunter-improved-scorpid-sting | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 人型生物杀手 | 改动清单 | hunter-humanoid-slaying | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化假死 | 改动清单 | hunter-improved-feign-death | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 杀戮本能 | 改动清单 | hunter-killer-instinct | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 翼龙钉刺 | 改动清单 | hunter-wyvern-sting | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵猴守护 | 改动清单 | spellbook-hunter-aspect-of-the-monkey | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 雄鹰守护 | 改动清单 | spellbook-hunter-aspect-of-the-hawk | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤宠物 | 改动清单 | spellbook-hunter-call-pet | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 解散野兽 | 改动清单 | spellbook-hunter-dismiss-pet | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 喂养宠物 | 改动清单 | spellbook-hunter-feed-pet | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 复活宠物 | 改动清单 | spellbook-hunter-revive-pet | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 驯服野兽 | 改动清单 | spellbook-hunter-tame-beast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗宠物 | 改动清单 | spellbook-hunter-mend-pet | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 鹰眼术 | 改动清单 | spellbook-hunter-eagle-eye | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野兽之眼 | 改动清单 | spellbook-hunter-eyes-of-the-beast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恐吓野兽 | 改动清单 | spellbook-hunter-scare-beast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 猎豹守护 | 改动清单 | spellbook-hunter-aspect-of-the-cheetah | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野兽知识 | 改动清单 | spellbook-hunter-beast-lore | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野兽守护 | 改动清单 | spellbook-hunter-aspect-of-the-beast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 豹群守护 | 改动清单 | spellbook-hunter-aspect-of-the-pack | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野性守护 | 改动清单 | spellbook-hunter-aspect-of-the-wild | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 宁神射击 | 改动清单 | spellbook-hunter-tranquilizing-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自动射击 | 改动清单 | spellbook-hunter-auto-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 毒蛇钉刺 | 改动清单 | spellbook-hunter-serpent-sting | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术射击 | 改动清单 | spellbook-hunter-arcane-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 猎人印记 | 改动清单 | spellbook-hunter-hunter-s-mark | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 震荡射击 | 改动清单 | spellbook-hunter-concussive-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 扰乱射击 | 改动清单 | spellbook-hunter-distracting-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 多重射击 | 改动清单 | spellbook-hunter-multi-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 瞄准射击 | 改动清单 | spellbook-hunter-aimed-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 毒蝎钉刺 | 改动清单 | spellbook-hunter-scorpid-sting | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 急速射击 | 改动清单 | spellbook-hunter-rapid-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 照明弹 | 改动清单 | spellbook-hunter-flare | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 蝰蛇钉刺 | 改动清单 | spellbook-hunter-viper-sting | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 乱射 | 改动清单 | spellbook-hunter-volley | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 黑箭 | 改动清单 | spellbook-hunter-black-arrow | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 猛禽一击 | 改动清单 | spellbook-hunter-raptor-strike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪野兽 | 改动清单 | spellbook-hunter-track-beasts | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪人型生物 | 改动清单 | spellbook-hunter-track-humanoids | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 摔绊 | 改动清单 | spellbook-hunter-wing-clip | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 献祭陷阱 | 改动清单 | spellbook-hunter-immolation-trap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 猫鼬撕咬 | 改动清单 | spellbook-hunter-mongoose-bite | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪亡灵 | 改动清单 | spellbook-hunter-track-undead | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 逃脱 | 改动清单 | spellbook-hunter-disengage | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰冻陷阱 | 改动清单 | spellbook-hunter-freezing-trap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪隐藏生物 | 改动清单 | spellbook-hunter-track-hidden | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪元素生物 | 改动清单 | spellbook-hunter-track-elementals | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰霜陷阱 | 改动清单 | spellbook-hunter-frost-trap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 假死 | 改动清单 | spellbook-hunter-feign-death | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 割伤 | 改动清单 | spellbook-hunter-lacerate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪恶魔 | 改动清单 | spellbook-hunter-track-demons | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 爆炸陷阱 | 改动清单 | spellbook-hunter-explosive-trap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪巨人 | 改动清单 | spellbook-hunter-track-giants | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪龙类 | 改动清单 | spellbook-hunter-track-dragonkin | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 训练野兽 | 改动清单 | spellbook-hunter-beast-training | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔杖专精 | 改动清单 | calc-mage-arcane-wand-specialization | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术集中 | 改动清单 | calc-mage-arcane-arcane-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化引导 | 改动清单 | calc-mage-arcane-improved-channeling | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 飞弹连射 | 改动清单 | calc-mage-arcane-missile-barrage | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术精妙 | 改动清单 | calc-mage-arcane-arcane-subtlety | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔法吸收 | 改动清单 | calc-mage-arcane-magic-absorption | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术专注 | 改动清单 | calc-mage-arcane-arcane-concentration | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术充沛 | 改动清单 | calc-mage-arcane-arcane-resilience | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔法协调 | 改动清单 | calc-mage-arcane-arcane-geometry | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术冲撞 | 改动清单 | calc-mage-arcane-arcane-impact | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术冲击 | 改动清单 | calc-mage-arcane-arcane-blast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术护盾 | 改动清单 | calc-mage-arcane-arcane-shielding | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化法术反制 | 改动清单 | calc-mage-arcane-improved-counterspell | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术冥想 | 改动清单 | calc-mage-arcane-arcane-meditation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术愤怒 | 改动清单 | calc-mage-arcane-arcane-wrath | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 气定神闲 | 改动清单 | calc-mage-arcane-presence-of-mind | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术心智 | 改动清单 | calc-mage-arcane-arcane-mind | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术增效 | 改动清单 | calc-mage-arcane-arcane-instability | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术强化 | 改动清单 | calc-mage-arcane-arcane-power | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化火焰冲击 | 改动清单 | calc-mage-fire-improved-fire-blast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 烧尽 | 改动清单 | calc-mage-fire-incineration | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化火球术 | 改动清单 | calc-mage-fire-improved-fireball | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 点燃 | 改动清单 | calc-mage-fire-ignite | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 烈焰投掷 | 改动清单 | calc-mage-fire-flame-throwing | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冲击 | 改动清单 | calc-mage-fire-impact | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 燃烧之魂 | 改动清单 | calc-mage-fire-burning-soul | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化烈焰风暴 | 改动清单 | calc-mage-fire-improved-flamestrike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 炎爆术 | 改动清单 | calc-mage-fire-pyroblast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化灼烧 | 改动清单 | calc-mage-fire-improved-scorch | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化防护火焰结界 | 改动清单 | calc-mage-fire-improved-fire-ward | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 热力迸发 | 改动清单 | mage-heating-up | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素大师 | 改动清单 | calc-mage-fire-master-of-elements | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火焰重击 | 改动清单 | calc-mage-fire-critical-mass | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冲击波 | 改动清单 | calc-mage-fire-blast-wave | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火焰强化 | 改动清单 | calc-mage-fire-fire-power | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰霜障壁 | 改动清单 | calc-mage-frost-frost-warding | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化寒冰箭 | 改动清单 | calc-mage-frost-improved-frostbolt | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素精准 | 改动清单 | calc-mage-frost-elemental-precision | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 寒冰碎片 | 改动清单 | calc-mage-frost-ice-shards | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 极寒冰霜 | 改动清单 | calc-mage-frost-permafrost | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化冰霜新星 | 改动清单 | calc-mage-frost-improved-frost-nova | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 霜寒刺骨 | 改动清单 | calc-mage-frost-frostbite | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 刺骨寒冰 | 改动清单 | calc-mage-frost-piercing-ice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰霜导能 | 改动清单 | calc-mage-frost-frost-channeling | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰枪术 | 改动清单 | calc-mage-frost-ice-lance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化暴风雪 | 改动清单 | calc-mage-frost-improved-blizzard | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 极寒延伸 | 改动清单 | calc-mage-frost-arctic-reach | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 寒冰屏障 | 改动清单 | calc-mage-frost-ice-block | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 碎冰 | 改动清单 | calc-mage-frost-shatter | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化冰锥术 | 改动清单 | calc-mage-frost-improved-cone-of-cold | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 急速冷却 | 改动清单 | calc-mage-frost-cold-snap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 寒冰指 | 改动清单 | calc-mage-frost-fingers-of-frost | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 深冬之寒 | 改动清单 | calc-mage-frost-winter-s-chill | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 寒冰护体 | 改动清单 | calc-mage-frost-ice-barrier | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术智慧 | 改动清单 | spellbook-mage-arcane-intellect | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 造水术 | 改动清单 | spellbook-mage-conjure-water | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 造食术 | 改动清单 | spellbook-mage-conjure-food | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术飞弹 | 改动清单 | spellbook-mage-arcane-missiles | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 变形术 | 改动清单 | spellbook-mage-polymorph | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔法抑制 | 改动清单 | spellbook-mage-dampen-magic | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 缓落术 | 改动清单 | spellbook-mage-slow-fall | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔爆术 | 改动清单 | spellbook-mage-arcane-explosion | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔法增效 | 改动清单 | spellbook-mage-amplify-magic | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 解除次级诅咒 | 改动清单 | spellbook-mage-remove-lesser-curse | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闪现术 | 改动清单 | spellbook-mage-blink | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 唤醒 | 改动清单 | spellbook-mage-evocation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 法力护盾 | 改动清单 | spellbook-mage-mana-shield | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送：铁炉堡 | 改动清单 | spellbook-mage-teleport-ironforge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送：奥格瑞玛 | 改动清单 | spellbook-mage-teleport-orgrimmar | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送：暴风城 | 改动清单 | spellbook-mage-teleport-stormwind | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送：幽暗城 | 改动清单 | spellbook-mage-teleport-undercity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 法术反制 | 改动清单 | spellbook-mage-counterspell | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制造魔法玛瑙 | 改动清单 | spellbook-mage-conjure-mana-agate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送：达纳苏斯 | 改动清单 | spellbook-mage-teleport-darnassus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送：雷霆崖 | 改动清单 | spellbook-mage-teleport-thunder-bluff | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔甲术 | 改动清单 | spellbook-mage-mage-armor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制造魔法翡翠 | 改动清单 | spellbook-mage-conjure-mana-jade | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送门：铁炉堡 | 改动清单 | spellbook-mage-portal-ironforge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送门：奥格瑞玛 | 改动清单 | spellbook-mage-portal-orgrimmar | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送门：暴风城 | 改动清单 | spellbook-mage-portal-stormwind | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送门：幽暗城 | 改动清单 | spellbook-mage-portal-undercity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制造魔法黄水晶 | 改动清单 | spellbook-mage-conjure-mana-citrine | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送门：达纳苏斯 | 改动清单 | spellbook-mage-portal-darnassus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送门：雷霆崖 | 改动清单 | spellbook-mage-portal-thunder-bluff | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送：达拉然 | 改动清单 | spellbook-mage-teleport-dalaran | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奥术光辉 | 改动清单 | spellbook-mage-arcane-brilliance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制造魔法红宝石 | 改动清单 | spellbook-mage-conjure-mana-ruby | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 变形术：奶牛 | 改动清单 | spellbook-mage-polymorph-cow | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火球术 | 改动清单 | spellbook-mage-fireball | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火焰冲击 | 改动清单 | spellbook-mage-fire-blast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 烈焰风暴 | 改动清单 | spellbook-mage-flamestrike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 防护火焰结界 | 改动清单 | spellbook-mage-fire-ward | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灼烧 | 改动清单 | spellbook-mage-scorch | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 霜火之箭 | 改动清单 | mage-frostfire-bolt | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔火 | 改动清单 | spellbook-mage-felfire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 霜甲术 | 改动清单 | spellbook-mage-frost-armor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 寒冰箭 | 改动清单 | spellbook-mage-frostbolt | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰霜新星 | 改动清单 | spellbook-mage-frost-nova | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暴风雪 | 改动清单 | spellbook-mage-blizzard | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 防护冰霜结界 | 改动清单 | spellbook-mage-frost-ward | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰霜冲击 | 改动清单 | spellbook-mage-frost-blast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰锥术 | 改动清单 | spellbook-mage-cone-of-cold | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰甲术 | 改动清单 | spellbook-mage-ice-armor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 理解卷轴 | 改动清单 | spellbook-mage-comprehend-scroll | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 学习 | 改动清单 | spellbook-mage-study | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化凿击 | 改动清单 | calc-rogue-assassination-improved-gouge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冷酷攻击 | 改动清单 | calc-rogue-assassination-remorseless-attacks | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶意 | 改动清单 | calc-rogue-assassination-malice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 无情 | 改动清单 | calc-rogue-assassination-ruthlessness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 密谋 | 改动清单 | calc-rogue-assassination-murder | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化切割 | 改动清单 | calc-rogue-assassination-improved-slice-and-dice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 无情打击 | 改动清单 | calc-rogue-assassination-relentless-strikes | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致命偷袭 | 改动清单 | calc-rogue-assassination-lethality | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶性毒药 | 改动清单 | calc-rogue-assassination-vile-poisons | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冷血 | 改动清单 | calc-rogue-assassination-cold-blood | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化毒药 | 改动清单 | calc-rogue-assassination-improved-poisons | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精力 | 改动清单 | calc-rogue-assassination-vigor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 毁伤 | 改动清单 | calc-rogue-assassination-mutilate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化肾击 | 改动清单 | calc-rogue-assassination-improved-kidney-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 封印命运 | 改动清单 | calc-rogue-assassination-seal-fate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 毒针 | 改动清单 | calc-rogue-assassination-venom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化刺骨 | 改动清单 | calc-rogue-combat-improved-eviscerate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化邪恶攻击 | 改动清单 | calc-rogue-combat-improved-sinister-strike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闪电反射 | 改动清单 | calc-rogue-combat-lightning-reflexes | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 穿刺之伤 | 改动清单 | calc-rogue-combat-puncturing-wounds | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 偏斜 | 改动清单 | calc-rogue-combat-deflection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精确 | 改动清单 | calc-rogue-combat-precision | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 耐久 | 改动清单 | calc-rogue-combat-endurance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 还击 | 改动清单 | calc-rogue-combat-riposte | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化疾跑 | 改动清单 | calc-rogue-combat-improved-sprint | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化脚踢 | 改动清单 | calc-rogue-combat-improved-kick | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 完美处刑 | 改动清单 | rogue-flawless-execution | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 剑刃乱舞 | 改动清单 | calc-rogue-combat-blade-flurry | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 武器专家 | 改动清单 | calc-rogue-combat-weapon-expertise | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 侵略 | 改动清单 | calc-rogue-combat-aggression | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冲动 | 改动清单 | calc-rogue-combat-adrenaline-rush | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 伪装 | 改动清单 | calc-rogue-subtlety-camouflage | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 欺诈高手 | 改动清单 | calc-rogue-subtlety-master-of-deception | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 伺机而动 | 改动清单 | calc-rogue-subtlety-opportunity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 飘忽不定 | 改动清单 | calc-rogue-subtlety-elusiveness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 邪恶计谋 | 改动清单 | calc-rogue-subtlety-dirty-tricks | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化伏击 | 改动清单 | calc-rogue-subtlety-improved-ambush | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 先发制人 | 改动清单 | calc-rogue-subtlety-initiative | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 鬼魅攻击 | 改动清单 | calc-rogue-subtlety-ghostly-strike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化扰乱 | 改动清单 | calc-rogue-subtlety-improved-distract | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 察觉 | 改动清单 | calc-rogue-subtlety-heightened-senses | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 预谋 | 改动清单 | calc-rogue-subtlety-premeditation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 锯齿利刃 | 改动清单 | calc-rogue-subtlety-serrated-blades | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 卑鄙 | 改动清单 | calc-rogue-subtlety-dirty-deeds | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 伺机待发 | 改动清单 | calc-rogue-subtlety-preparation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 出血 | 改动清单 | calc-rogue-subtlety-hemorrhage | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 寂灭 | 改动清单 | rogue-quietus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 割喉 | 改动清单 | calc-rogue-subtlety-cutthroat | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 千刀万剐 | 改动清单 | calc-rogue-subtlety-thousand-cuts | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化背刺 | 改动清单 | rogue-improved-backstab | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 匕首专精 | 改动清单 | rogue-dagger-specialization | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 拳套专精 | 改动清单 | rogue-fist-weapon-specialization | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 狡诈 | 改动清单 | rogue-sleight-of-hand | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化闷棍 | 改动清单 | rogue-improved-sap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 极致 | 改动清单 | rogue-deadliness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 刺骨 | 改动清单 | spellbook-rogue-eviscerate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 切割 | 改动清单 | spellbook-rogue-slice-and-dice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 绞喉 | 改动清单 | spellbook-rogue-garrote | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 伏击 | 改动清单 | spellbook-rogue-ambush | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 割裂 | 改动清单 | spellbook-rogue-rupture | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 偷袭 | 改动清单 | spellbook-rogue-cheap-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 肾击 | 改动清单 | spellbook-rogue-kidney-shot | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 邪恶攻击 | 改动清单 | spellbook-rogue-sinister-strike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 背刺 | 改动清单 | spellbook-rogue-backstab | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 凿击 | 改动清单 | spellbook-rogue-gouge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闪避 | 改动清单 | spellbook-rogue-evasion | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 疾跑 | 改动清单 | spellbook-rogue-sprint | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 脚踢 | 改动清单 | spellbook-rogue-kick | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 佯攻 | 改动清单 | spellbook-rogue-feint | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闷棍 | 改动清单 | spellbook-rogue-sap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 扰乱 | 改动清单 | spellbook-rogue-distract | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 消失 | 改动清单 | spellbook-rogue-vanish | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 侦测陷阱 | 改动清单 | spellbook-rogue-detect-traps | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 解除陷阱 | 改动清单 | spellbook-rogue-disarm-trap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致盲 | 改动清单 | spellbook-rogue-blind | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 安全降落 | 改动清单 | spellbook-rogue-safe-fall | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 开锁 | 改动清单 | spellbook-rogue-pick-lock | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致残毒药 | 改动清单 | spellbook-rogue-crippling-poison | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 速效毒药 | 改动清单 | spellbook-rogue-instant-poison | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 毒药 | 改动清单 | spellbook-rogue-poisons | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 麻痹毒药 | 改动清单 | spellbook-rogue-mind-numbing-poison | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 速效毒药 II | 改动清单 | spellbook-rogue-instant-poison-ii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致命毒药 | 改动清单 | spellbook-rogue-deadly-poison | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致伤毒药 | 改动清单 | spellbook-rogue-wound-poison | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致盲粉 | 改动清单 | spellbook-rogue-blinding-powder | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 速效毒药 III | 改动清单 | spellbook-rogue-instant-poison-iii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致命毒药 II | 改动清单 | spellbook-rogue-deadly-poison-ii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 麻痹毒药 II | 改动清单 | spellbook-rogue-mind-numbing-poison-ii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致伤毒药 II | 改动清单 | spellbook-rogue-wound-poison-ii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 速效毒药 IV | 改动清单 | spellbook-rogue-instant-poison-iv | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致命毒药 III | 改动清单 | spellbook-rogue-deadly-poison-iii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致伤毒药 III | 改动清单 | spellbook-rogue-wound-poison-iii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致残毒药 II | 改动清单 | spellbook-rogue-crippling-poison-ii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 速效毒药 V | 改动清单 | spellbook-rogue-instant-poison-v | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 麻痹毒药 III | 改动清单 | spellbook-rogue-mind-numbing-poison-iii | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致命毒药 IV | 改动清单 | spellbook-rogue-deadly-poison-iv | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致伤毒药 IV | 改动清单 | spellbook-rogue-wound-poison-iv | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 致命毒药 V | 改动清单 | spellbook-rogue-deadly-poison-v | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 速效毒药 VI | 改动清单 | spellbook-rogue-instant-poison-vi | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣光之力 | 改动清单 | calc-priest-discipline-power-in-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔杖专精 | 改动清单 | calc-priest-discipline-wand-specialization | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 双生戒律 | 改动清单 | calc-priest-discipline-twin-disciplines | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 无声消退 | 改动清单 | calc-priest-discipline-silent-resolve | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣精准 | 改动清单 | calc-priest-discipline-holy-precision | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 心灵之力 | 改动清单 | calc-priest-discipline-mental-strength | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 殉难 | 改动清单 | calc-priest-discipline-martyrdom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神敏锐 | 改动清单 | calc-priest-discipline-mental-agility | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 心灵专注 | 改动清单 | calc-priest-discipline-inner-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化真言术：盾 | 改动清单 | calc-priest-discipline-improved-power-word-shield | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冥想 | 改动清单 | calc-priest-discipline-meditation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化心灵之火 | 改动清单 | calc-priest-discipline-improved-inner-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化法力燃烧 | 改动清单 | calc-priest-discipline-improved-mana-burn | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵魂守护 | 改动清单 | calc-priest-discipline-soul-warding | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 苦修 | 改动清单 | calc-priest-discipline-penance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 新生希望 | 改动清单 | calc-priest-discipline-renewed-hope | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣庇护 | 改动清单 | calc-priest-discipline-divine-aegis | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 能量灌注 | 改动清单 | calc-priest-discipline-power-infusion | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暮光专注 | 改动清单 | calc-priest-holy-twilight-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化恢复 | 改动清单 | calc-priest-holy-improved-renew | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣专精 | 改动清单 | calc-priest-holy-holy-specialization | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 法术屏障 | 改动清单 | calc-priest-holy-spell-warding | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣之怒 | 改动清单 | calc-priest-holy-divine-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣新星 | 改动清单 | calc-priest-holy-holy-nova | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神恩回复 | 改动清单 | calc-priest-holy-blessed-recovery | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵感 | 改动清单 | calc-priest-holy-inspiration | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣延伸 | 改动清单 | calc-priest-holy-holy-reach | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化治疗术 | 改动清单 | calc-priest-holy-improved-healing | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灼热之光 | 改动清单 | calc-priest-holy-searing-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 联结治疗 | 改动清单 | calc-priest-holy-binding-heal | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣光连祷 | 改动清单 | calc-priest-holy-litany-of-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 救赎之魂 | 改动清单 | calc-priest-holy-spirit-of-redemption | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神指引 | 改动清单 | calc-priest-holy-spiritual-guidance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神治疗 | 改动清单 | calc-priest-holy-spiritual-healing | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 愈合祷言 | 改动清单 | calc-priest-holy-prayer-of-mending | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影集中 | 改动清单 | calc-priest-shadow-magic-shadow-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 昏阙 | 改动清单 | calc-priest-shadow-magic-blackout | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神分流 | 改动清单 | calc-priest-shadow-magic-spirit-tap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化心灵震爆 | 改动清单 | calc-priest-shadow-magic-improved-mind-blast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化暗言术：痛 | 改动清单 | calc-priest-shadow-magic-improved-shadow-word-pain | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影延伸 | 改动清单 | calc-priest-shadow-magic-shadow-reach | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化心灵尖啸 | 改动清单 | calc-priest-shadow-magic-improved-psychic-scream | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神鞭笞 | 改动清单 | calc-priest-shadow-magic-mind-flay | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化精神鞭笞 | 改动清单 | calc-priest-shadow-magic-improved-mind-flay | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 黑暗启发 | 改动清单 | calc-priest-shadow-dark-inspiration | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 吸血鬼的拥抱 | 改动清单 | calc-priest-shadow-magic-vampiric-embrace | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影之波 | 改动清单 | calc-priest-shadow-magic-shadow-weaving | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 沉默 | 改动清单 | calc-priest-shadow-magic-silence | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 噬灵传染 | 改动清单 | calc-priest-shadow-magic-devouring-contagion | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 提早离世 | 改动清单 | calc-priest-shadow-magic-early-demise | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影形态 | 改动清单 | calc-priest-shadow-magic-shadowform | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 坚定意志 | 改动清单 | priest-unbreakable-will | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化真言术：韧 | 改动清单 | priest-improved-power-word-fortitude | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣之灵 | 改动清单 | priest-divine-spirit | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 意志之力 | 改动清单 | priest-force-of-will | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化治疗祷言 | 改动清单 | priest-improved-prayer-of-healing | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 光明之泉 | 改动清单 | priest-lightwell | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影亲和 | 改动清单 | calc-priest-shadow-magic-shadow-affinity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化渐隐术 | 改动清单 | calc-priest-shadow-magic-improved-fade | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化吸血鬼的拥抱 | 改动清单 | priest-improved-vampiric-embrace | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 真言术：韧 | 改动清单 | spellbook-priest-power-word-fortitude | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 真言术：盾 | 改动清单 | spellbook-priest-power-word-shield | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 迷惑闪光 | 改动清单 | priest-confounding-flash | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 星辰碎片 | 改动清单 | spellbook-priest-starshards | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 心灵之火 | 改动清单 | spellbook-priest-inner-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 驱散魔法 | 改动清单 | spellbook-priest-dispel-magic | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 应急方案 | 改动清单 | priest-contingency-plan | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 艾露恩的赐福 | 改动清单 | spellbook-priest-elune-s-grace | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 回馈 | 改动清单 | spellbook-priest-feedback | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 束缚亡灵 | 改动清单 | spellbook-priest-shackle-undead | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 法力燃烧 | 改动清单 | spellbook-priest-mana-burn | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣之灵 | 改动清单 | spellbook-priest-divine-spirit | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 漂浮术 | 改动清单 | spellbook-priest-levitate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 坚韧祷言 | 改动清单 | spellbook-priest-prayer-of-fortitude | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神祷言 | 改动清单 | spellbook-priest-prayer-of-spirit | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 次级治疗术 | 改动清单 | spellbook-priest-lesser-heal | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 惩击 | 改动清单 | spellbook-priest-smite | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恢复 | 改动清单 | spellbook-priest-renew | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 绝望祷言 | 改动清单 | priest-desperate-prayer | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣恩典 | 改动清单 | priest-divine-grace | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 复活术 | 改动清单 | spellbook-priest-resurrection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 祛病术 | 改动清单 | spellbook-priest-cure-disease | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗术 | 改动清单 | spellbook-priest-heal | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 惩击 | 改动清单 | priest-chastise | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 防护恐惧结界 | 改动清单 | priest-fear-ward | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 快速治疗 | 改动清单 | spellbook-priest-flash-heal | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣之火 | 改动清单 | spellbook-priest-holy-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗祷言 | 改动清单 | spellbook-priest-prayer-of-healing | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 驱除疾病 | 改动清单 | spellbook-priest-abolish-disease | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强效治疗术 | 改动清单 | spellbook-priest-greater-heal | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 光明之泉 | 改动清单 | spellbook-priest-lightwell | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 光明之泉回复 | 改动清单 | spellbook-priest-lightwell-renew | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗言术：痛 | 改动清单 | spellbook-priest-shadow-word-pain | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 渐隐术 | 改动清单 | spellbook-priest-fade | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 虚弱妖术 | 改动清单 | spellbook-priest-hex-of-weakness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 心灵震爆 | 改动清单 | spellbook-priest-mind-blast | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 虚弱之触 | 改动清单 | spellbook-priest-touch-of-weakness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 心灵尖啸 | 改动清单 | spellbook-priest-psychic-scream | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 黑暗献祭 | 改动清单 | priest-dark-sacrifice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 噬灵瘟疫 | 改动清单 | reported-priest-devouring-plague | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 安抚心灵 | 改动清单 | spellbook-priest-mind-soothe | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影守卫 | 改动清单 | spellbook-priest-shadowguard | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 心灵视界 | 改动清单 | spellbook-priest-mind-vision | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神控制 | 改动清单 | spellbook-priest-mind-control | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 防护暗影 | 改动清单 | spellbook-priest-shadow-protection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗言术：灭 | 改动清单 | priest-shadow-word-death | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影防护祷言 | 改动清单 | spellbook-priest-prayer-of-shadow-protection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化生命分流 | 改动清单 | calc-warlock-affliction-improved-life-tap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 镇压 | 改动清单 | warlock-suppression | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化腐蚀术 | 改动清单 | warlock-improved-corruption | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 无情延伸 | 改动清单 | calc-warlock-affliction-grim-reach | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵魂收割 | 改动清单 | warlock-soul-harvest | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化吸取 | 改动清单 | warlock-improved-drains | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化痛苦灾祸 | 改动清单 | calc-warlock-affliction-improved-bane-of-agony | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔专注 | 改动清单 | calc-warlock-affliction-fel-concentration | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 诅咒增幅 | 改动清单 | calc-warlock-affliction-amplify-curse | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶疾 | 改动清单 | warlock-pandemic | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 怨毒 | 改动清单 | calc-warlock-affliction-malevolence | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 夜幕 | 改动清单 | calc-warlock-affliction-nightfall | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 疲劳诅咒 | 改动清单 | warlock-curse-of-exhaustion | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 生命虹吸 | 改动清单 | calc-warlock-affliction-siphon-life | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵魂虹吸 | 改动清单 | calc-warlock-affliction-soul-siphon | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影掌握 | 改动清单 | calc-warlock-affliction-shadow-mastery | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 折磨 | 改动清单 | warlock-wrack | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化生命通道 | 改动清单 | warlock-improved-health-funnel | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化小鬼 | 改动清单 | calc-warlock-demonology-improved-imp | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔之拥 | 改动清单 | warlock-demonic-embrace | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 邪恶强化 | 改动清单 | calc-warlock-demonology-unholy-power | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔庇护 | 改动清单 | warlock-demonic-aegis | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化虚空行者 | 改动清单 | calc-warlock-demonology-improved-voidwalker | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 邪能活力 | 改动清单 | warlock-fel-vitality | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔能量 | 改动清单 | calc-warlock-demonology-demonic-energies | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化萨亚德 | 改动清单 | calc-warlock-demonology-improved-sayaad | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔牺牲 | 改动清单 | calc-warlock-demonology-demonic-sacrifice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤大师 | 改动清单 | calc-warlock-demonology-master-summoner | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 屠戮 | 改动清单 | warlock-decimation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔支配 | 改动清单 | calc-warlock-demonology-fel-domination | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔印记 | 改动清单 | calc-warlock-demonology-demonic-brand | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化地狱猎犬 | 改动清单 | calc-warlock-demonology-improved-felhunter | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵魂链接 | 改动清单 | warlock-soul-link | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔知识 | 改动清单 | warlock-demonic-knowledge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔学识大师 | 改动清单 | calc-warlock-demonology-master-demonologist | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔契约 | 改动清单 | warlock-demonic-pact | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 毁灭延伸 | 改动清单 | calc-warlock-destruction-destructive-reach | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化暗影箭 | 改动清单 | warlock-improved-shadow-bolt | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灾祸 | 改动清单 | warlock-bane | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 熔岩之肤 | 改动清单 | calc-warlock-destruction-molten-skin | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灾变 | 改动清单 | warlock-cataclysm | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 清算 | 改动清单 | calc-warlock-destruction-aftermath | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 毁灭 | 改动清单 | calc-warlock-destruction-ruin | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影灼烧 | 改动清单 | calc-warlock-destruction-shadowburn | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强烈 | 改动清单 | calc-warlock-destruction-intensity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 苦痛之焰 | 改动清单 | warlock-agonizing-flames | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火焰冲撞 | 改动清单 | calc-warlock-destruction-pyroclasm | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 浩劫灾祸 | 改动清单 | warlock-bane-of-havoc | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 硫磺烈火 | 改动清单 | calc-warlock-destruction-fire-and-brimstone | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 影与焰 | 改动清单 | warlock-shadow-and-flame | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 烧尽 | 改动清单 | warlock-incinerate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化虚弱诅咒 | 改动清单 | warlock-improved-curse-of-weakness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化吸取灵魂 | 改动清单 | warlock-improved-drain-soul | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化吸取法力 | 改动清单 | warlock-improved-drain-mana | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化疲劳诅咒 | 改动清单 | warlock-improved-curse-of-exhaustion | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 黑暗契约 | 改动清单 | warlock-dark-pact | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化治疗石 | 改动清单 | warlock-improved-healthstone | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔耐力 | 改动清单 | warlock-fel-stamina | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化征服恶魔 | 改动清单 | warlock-improved-subjugate-demon | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化火焰石 | 改动清单 | warlock-improved-firestone | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化法术石 | 改动清单 | warlock-improved-spellstone | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化火焰箭 | 改动清单 | warlock-improved-firebolt | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化剧痛鞭笞 | 改动清单 | warlock-improved-lash-of-pain | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 破坏 | 改动清单 | warlock-devastation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化献祭 | 改动清单 | warlock-improved-immolate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 琥珀风暴 | 改动清单 | warlock-emberstorm | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 腐蚀术 | 改动清单 | spellbook-warlock-corruption | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 虚弱诅咒 | 改动清单 | spellbook-warlock-curse-of-weakness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 生命分流 | 改动清单 | spellbook-warlock-life-tap | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 痛苦灾祸 | 改动清单 | warlock-bane-of-agony | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恐惧术 | 改动清单 | spellbook-warlock-fear | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 吸取灵魂 | 改动清单 | spellbook-warlock-drain-soul | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 鲁莽诅咒 | 改动清单 | spellbook-warlock-curse-of-recklessness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 吸取生命 | 改动清单 | spellbook-warlock-drain-life | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素诅咒 | 改动清单 | spellbook-warlock-curse-of-the-elements | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 吸取法力 | 改动清单 | spellbook-warlock-drain-mana | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 语言诅咒 | 改动清单 | spellbook-warlock-curse-of-tongues | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恐惧嚎叫 | 改动清单 | spellbook-warlock-howl-of-terror | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 死亡缠绕 | 改动清单 | spellbook-warlock-death-coil | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 末日灾祸 | 改动清单 | warlock-bane-of-doom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恶魔皮肤 | 改动清单 | spellbook-warlock-demon-skin | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤小鬼 | 改动清单 | spellbook-warlock-summon-imp | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制造治疗石 | 改动清单 | spellbook-warlock-create-healthstone | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤虚空行者 | 改动清单 | spellbook-warlock-summon-voidwalker | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 生命通道 | 改动清单 | spellbook-warlock-health-funnel | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔息术 | 改动清单 | spellbook-warlock-unending-breath | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制造灵魂石 | 改动清单 | spellbook-warlock-create-soulstone | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 魔甲术 | 改动清单 | spellbook-warlock-demon-armor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤仪式 | 改动清单 | spellbook-warlock-ritual-of-summoning | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤夜魔 | 改动清单 | warlock-incubus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤魅魔 | 改动清单 | spellbook-warlock-summon-succubus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 基尔罗格之眼 | 改动清单 | spellbook-warlock-eye-of-kilrogg | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 感知恶魔 | 改动清单 | spellbook-warlock-sense-demons | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 侦测隐形 | 改动清单 | spellbook-warlock-detect-invisibility | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 放逐术 | 改动清单 | spellbook-warlock-banish | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制造火焰石 | 改动清单 | spellbook-warlock-create-firestone | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 征服恶魔 | 改动清单 | spellbook-warlock-subjugate-demon | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤地狱猎犬 | 改动清单 | spellbook-warlock-summon-felhunter | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 防护暗影结界 | 改动清单 | spellbook-warlock-shadow-ward | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制造法术石 | 改动清单 | spellbook-warlock-create-spellstone | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 地狱火 | 改动清单 | spellbook-warlock-inferno | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤传送门 | 改动清单 | spellbook-warlock-portal-of-summoning | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 末日仪式 | 改动清单 | spellbook-warlock-ritual-of-doom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 献祭 | 改动清单 | spellbook-warlock-immolate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影箭 | 改动清单 | spellbook-warlock-shadow-bolt | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灼热之痛 | 改动清单 | spellbook-warlock-searing-pain | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火焰之雨 | 改动清单 | spellbook-warlock-rain-of-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 地狱烈焰 | 改动清单 | spellbook-warlock-hellfire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵魂之火 | 改动清单 | spellbook-warlock-soul-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤地狱战马 | 改动清单 | spellbook-warlock-summon-felsteed | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤恐惧战马 | 改动清单 | spellbook-warlock-summon-dreadsteed | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣之力 | 改动清单 | calc-paladin-holy-divine-strength | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣智慧 | 改动清单 | calc-paladin-holy-divine-intellect | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗之光 | 改动清单 | calc-paladin-holy-healing-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神集中 | 改动清单 | calc-paladin-holy-spiritual-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化圣印 | 改动清单 | calc-paladin-holy-improved-seals | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 不灭信仰 | 改动清单 | calc-paladin-holy-unyielding-faith | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 真理之音 | 改动清单 | calc-paladin-holy-voice-of-truth | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 敬畏 | 改动清单 | calc-paladin-holy-reverence | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 净化之力 | 改动清单 | calc-paladin-holy-purifying-power | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣光灌注 | 改动清单 | calc-paladin-holy-infusion-of-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 启发 | 改动清单 | calc-paladin-holy-illumination | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神恩术 | 改动清单 | calc-paladin-holy-divine-favor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣精准 | 改动清单 | calc-paladin-holy-divine-precision | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣震击 | 改动清单 | calc-paladin-holy-holy-shock | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奉献之地 | 改动清单 | calc-paladin-holy-consecrated-ground | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣强化 | 改动清单 | calc-paladin-holy-holy-power | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣光守望 | 改动清单 | calc-paladin-holy-light-s-vigil | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 盾牌壁垒 | 改动清单 | paladin-redoubt | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精确 | 改动清单 | calc-paladin-protection-precision | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 守护者的宠爱 | 改动清单 | calc-paladin-protection-guardian-s-favor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化愤怒圣印 | 改动清单 | calc-paladin-protection-improved-seal-of-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化正义之怒 | 改动清单 | calc-paladin-protection-improved-righteous-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣职责 | 改动清单 | calc-paladin-protection-sacred-duty | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 迅捷审判 | 改动清单 | calc-paladin-protection-swift-judgement | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化制裁之锤 | 改动清单 | calc-paladin-protection-improved-hammer-of-justice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣殿骑士壁垒 | 改动清单 | calc-paladin-protection-templar-s-bulwark | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 清算 | 改动清单 | calc-paladin-protection-reckoning | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 钢铁信条 | 改动清单 | calc-paladin-protection-iron-creed | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣之盾 | 改动清单 | calc-paladin-protection-holy-shield | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 偏斜 | 改动清单 | calc-paladin-retribution-deflection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 祈福 | 改动清单 | calc-paladin-retribution-benediction | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化审判 | 改动清单 | calc-paladin-retribution-improved-judgement | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣导能 | 改动清单 | calc-paladin-retribution-holy-conduit | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 定罪 | 改动清单 | calc-paladin-retribution-conviction | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 辩护 | 改动清单 | calc-paladin-retribution-vindication | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣审判 | 改动清单 | calc-paladin-retribution-sanctified-judgement | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 命令圣印 | 改动清单 | calc-paladin-retribution-seal-of-command | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 正义追击 | 改动清单 | calc-paladin-retribution-pursuit-of-justice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 以眼还眼 | 改动清单 | calc-paladin-retribution-eye-for-an-eye | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣仲裁者 | 改动清单 | calc-paladin-retribution-sacred-arbiter | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 忏悔 | 改动清单 | calc-paladin-retribution-repentance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 光芒勇士 | 改动清单 | calc-paladin-retribution-champion-of-the-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 律法之器 | 改动清单 | calc-paladin-retribution-instrument-of-law | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣光扭转 | 改动清单 | calc-paladin-retribution-twist-of-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奉献 | 改动清单 | paladin-consecration-talent | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化圣疗术 | 改动清单 | paladin-improved-lay-on-hands | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化智慧祝福 | 改动清单 | paladin-improved-blessing-of-wisdom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 持久审判 | 改动清单 | paladin-lasting-judgement | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化虔诚光环 | 改动清单 | paladin-improved-devotion-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 王者祝福 | 改动清单 | paladin-blessing-of-kings | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化专注光环 | 改动清单 | paladin-improved-concentration-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 庇护祝福 | 改动清单 | paladin-blessing-of-sanctuary | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化力量祝福 | 改动清单 | paladin-improved-blessing-of-might | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化十字军圣印 | 改动清单 | paladin-improved-seal-of-the-crusader | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化惩罚光环 | 改动清单 | paladin-improved-retribution-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣洁光环 | 改动清单 | paladin-sanctity-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣光术 | 改动清单 | spellbook-paladin-holy-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 正义圣印 | 改动清单 | spellbook-paladin-seal-of-righteousness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 纯净术 | 改动清单 | spellbook-paladin-purify | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣疗术 | 改动清单 | spellbook-paladin-lay-on-hands | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 救赎 | 改动清单 | spellbook-paladin-redemption | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 智慧祝福 | 改动清单 | spellbook-paladin-blessing-of-wisdom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 奉献 | 改动清单 | paladin-consecration | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 驱邪术 | 改动清单 | spellbook-paladin-exorcism | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣光闪现 | 改动清单 | spellbook-paladin-flash-of-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 超度亡灵 | 改动清单 | spellbook-paladin-turn-undead | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 光明圣印 | 改动清单 | spellbook-paladin-seal-of-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 智慧圣印 | 改动清单 | spellbook-paladin-seal-of-wisdom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 光明祝福 | 改动清单 | spellbook-paladin-blessing-of-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 清洁术 | 改动清单 | spellbook-paladin-cleanse | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 愤怒之锤 | 改动清单 | spellbook-paladin-hammer-of-wrath | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣愤怒 | 改动清单 | spellbook-paladin-holy-wrath | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强效智慧祝福 | 改动清单 | spellbook-paladin-greater-blessing-of-wisdom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强效光明祝福 | 改动清单 | spellbook-paladin-greater-blessing-of-light | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 虔诚光环 | 改动清单 | spellbook-paladin-devotion-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣佑术 | 改动清单 | spellbook-paladin-divine-protection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 制裁之锤 | 改动清单 | spellbook-paladin-hammer-of-justice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 保护祝福 | 改动清单 | spellbook-paladin-blessing-of-protection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 愤怒圣印 | 改动清单 | paladin-seal-of-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 正义之怒 | 改动清单 | spellbook-paladin-righteous-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自由祝福 | 改动清单 | spellbook-paladin-blessing-of-freedom | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 王者祝福 | 改动清单 | spellbook-paladin-blessing-of-kings | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 专注光环 | 改动清单 | spellbook-paladin-concentration-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 公正圣印 | 改动清单 | spellbook-paladin-seal-of-justice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 撤销 | 改动清单 | spellbook-paladin-revoke | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 拯救 | 改动清单 | spellbook-paladin-salvation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 暗影抗性光环 | 改动清单 | spellbook-paladin-shadow-resistance-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣干涉 | 改动清单 | spellbook-paladin-divine-intervention | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰霜抗性光环 | 改动清单 | spellbook-paladin-frost-resistance-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 圣盾术 | 改动清单 | spellbook-paladin-divine-shield | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火焰抗性光环 | 改动清单 | spellbook-paladin-fire-resistance-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 正义之锤 | 改动清单 | spellbook-paladin-hammer-of-the-righteous | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 牺牲祝福 | 改动清单 | spellbook-paladin-blessing-of-sacrifice | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强效王者祝福 | 改动清单 | spellbook-paladin-greater-blessing-of-kings | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 群体拯救 | 改动清单 | spellbook-paladin-mass-salvation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 力量祝福 | 改动清单 | spellbook-paladin-blessing-of-might | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 审判 | 改动清单 | additional-paladin-judgement | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 神圣打击 | 改动清单 | additional-paladin-holy-strike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 十字军圣印 | 改动清单 | spellbook-paladin-seal-of-the-crusader | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 惩罚光环 | 改动清单 | spellbook-paladin-retribution-aura | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强效力量祝福 | 改动清单 | spellbook-paladin-greater-blessing-of-might | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤军马 | 改动清单 | spellbook-paladin-summon-warhorse | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤战马 | 改动清单 | spellbook-paladin-summon-charger | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 召唤被遗忘者战马 | 改动清单 | spellbook-paladin-summon-forsaken-charger | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化愤怒 | 改动清单 | calc-druid-balance-improved-wrath | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 起源 | 改动清单 | druid-genesis | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化月火术 | 改动清单 | calc-druid-balance-improved-moonfire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然的威严 | 改动清单 | druid-nature-s-majesty | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然延伸 | 改动清单 | calc-druid-balance-nature-s-reach | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化纠缠根须 | 改动清单 | calc-druid-balance-improved-entangling-roots | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然的壮美 | 改动清单 | druid-nature-s-splendor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 虫群 | 改动清单 | druid-insect-swarm | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化星火术 | 改动清单 | calc-druid-balance-improved-starfire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 繁茂 | 改动清单 | calc-druid-balance-overgrowth | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然之赐 | 改动清单 | druid-nature-s-grace | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 日月之蚀 | 改动清单 | calc-druid-balance-eclipse | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 月怒 | 改动清单 | calc-druid-balance-moonfury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 枭兽形态 | 改动清单 | calc-druid-balance-moonkin-form | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 凶暴 | 改动清单 | druid-ferocity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野性之心 | 改动清单 | calc-druid-feral-combat-heart-of-the-wild | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 豹之迅捷 | 改动清单 | calc-druid-feral-combat-feral-swiftness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野性本能 | 改动清单 | druid-feral-instinct | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野蛮冲撞 | 改动清单 | druid-brutal-impact | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 厚皮 | 改动清单 | druid-thick-hide | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 撕碎攻击 | 改动清单 | calc-druid-feral-combat-shredding-attacks | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野蛮暴怒 | 改动清单 | calc-druid-feral-combat-savage-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野性冲锋 | 改动清单 | druid-feral-charge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 锋利兽爪 | 改动清单 | calc-druid-feral-combat-sharpened-claws | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 变形之力 | 改动清单 | druid-shifting-power | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 原始撕咬 | 改动清单 | druid-primal-bite | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 猛兽攻击 | 改动清单 | calc-druid-feral-combat-predatory-strikes | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 血性狂乱 | 改动清单 | druid-blood-frenzy | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化变形之力 | 改动清单 | druid-improved-shifting-power | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 兽群领袖 | 改动清单 | calc-druid-feral-combat-leader-of-the-pack | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然本能 | 改动清单 | calc-druid-feral-combat-natural-instinct | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然反射 | 改动清单 | druid-natural-reaction | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 狂乱撕扯 | 改动清单 | calc-druid-feral-combat-rend-and-tear | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然集中 | 改动清单 | druid-nature-s-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 激怒 | 改动清单 | calc-druid-restoration-furor | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然主义 | 改动清单 | calc-druid-restoration-naturalist | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 微妙 | 改动清单 | druid-subtlety | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然变形 | 改动清单 | druid-natural-shapeshifter | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 反射 | 改动清单 | calc-druid-restoration-reflection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然赐福 | 改动清单 | druid-gift-of-nature | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 大地母亲的恩赐 | 改动清单 | calc-druid-restoration-gift-of-the-earthmother | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 宁静之魂 | 改动清单 | calc-druid-restoration-tranquil-spirit | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化回春术 | 改动清单 | druid-improved-rejuvenation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 迅捷治愈 | 改动清单 | calc-druid-restoration-swiftmend | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然迅捷 | 改动清单 | calc-druid-restoration-nature-s-swiftness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 生命之魂 | 改动清单 | druid-living-spirit | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化宁静 | 改动清单 | druid-improved-tranquility | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化愈合 | 改动清单 | calc-druid-restoration-improved-regrowth | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野性成长 | 改动清单 | calc-druid-restoration-wild-growth | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然之握 | 改动清单 | druid-nature-s-grasp | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 武器平衡 | 改动清单 | druid-natural-weapons | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化荆棘术 | 改动清单 | druid-improved-thorns | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 清晰预兆 | 改动清单 | druid-omen-of-clarity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野性侵略 | 改动清单 | druid-feral-aggression | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 原始狂怒 | 改动清单 | druid-primal-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精灵之火（野性） | 改动清单 | druid-faerie-fire-feral | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化野性印记 | 改动清单 | druid-improved-mark-of-the-wild | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化狂怒 | 改动清单 | druid-improved-enrage | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 月火术 | 改动清单 | spellbook-druid-moonfire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 荆棘术 | 改动清单 | spellbook-druid-thorns | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 纠缠根须 | 改动清单 | spellbook-druid-entangling-roots | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然之握 | 改动清单 | spellbook-druid-nature-s-grasp | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传送：月光林地 | 改动清单 | spellbook-druid-teleport-moonglade | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精灵之火 | 改动清单 | spellbook-druid-faerie-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 休眠 | 改动清单 | spellbook-druid-hibernate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 清晰预兆 | 改动清单 | spellbook-druid-omen-of-clarity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 星火术 | 改动清单 | spellbook-druid-starfire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 安抚动物 | 改动清单 | spellbook-druid-soothe-animal | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 飓风 | 改动清单 | spellbook-druid-hurricane | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 树皮术 | 改动清单 | spellbook-druid-barkskin | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 熊形态 | 改动清单 | spellbook-druid-bear-form | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 挫志咆哮 | 改动清单 | spellbook-druid-demoralizing-roar | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 低吼 | 改动清单 | spellbook-druid-growl | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 槌击 | 改动清单 | spellbook-druid-maul | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 重击 | 改动清单 | spellbook-druid-bash | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 水栖形态 | 改动清单 | spellbook-druid-aquatic-form | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 挥击 | 改动清单 | spellbook-druid-swipe | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 爪击 | 改动清单 | spellbook-druid-claw | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 撕扯 | 改动清单 | spellbook-druid-rip | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 撕碎 | 改动清单 | spellbook-druid-shred | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 扫击 | 改动清单 | spellbook-druid-rake | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 急奔 | 改动清单 | spellbook-druid-dash | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 挑战咆哮 | 改动清单 | spellbook-druid-challenging-roar | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 畏缩 | 改动清单 | spellbook-druid-cower | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 旅行形态 | 改动清单 | spellbook-druid-travel-form | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 凶猛撕咬 | 改动清单 | spellbook-druid-ferocious-bite | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 毁灭 | 改动清单 | spellbook-druid-ravage | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 追踪人型生物 | 改动清单 | spellbook-druid-track-humanoids | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 狂暴回复 | 改动清单 | spellbook-druid-frenzied-regeneration | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 突袭 | 改动清单 | spellbook-druid-pounce | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 巨熊形态 | 改动清单 | spellbook-druid-dire-bear-form | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 豹之优雅 | 改动清单 | spellbook-druid-feline-grace | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 割伤 | 改动清单 | spellbook-druid-lacerate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗之触 | 改动清单 | spellbook-druid-healing-touch | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野性印记 | 改动清单 | spellbook-druid-mark-of-the-wild | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 回春术 | 改动清单 | spellbook-druid-rejuvenation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 愈合 | 改动清单 | spellbook-druid-regrowth | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 起死回生 | 改动清单 | druid-revive | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 消毒术 | 改动清单 | spellbook-druid-cure-poison | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 复生 | 改动清单 | spellbook-druid-rebirth | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 解除诅咒 | 改动清单 | spellbook-druid-remove-curse | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 驱毒术 | 改动清单 | spellbook-druid-abolish-poison | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 宁静 | 改动清单 | spellbook-druid-tranquility | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 激活 | 改动清单 | spellbook-druid-innervate | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 野性赐福 | 改动清单 | spellbook-druid-gift-of-the-wild | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 传导 | 改动清单 | calc-shaman-elemental-combat-convection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素浩劫 | 改动清单 | calc-shaman-elemental-combat-elemental-devastation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 回响 | 改动清单 | calc-shaman-elemental-combat-reverberation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素迅捷 | 改动清单 | calc-shaman-elemental-combat-elemental-alacrity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 烈焰召唤 | 改动清单 | calc-shaman-elemental-combat-call-of-flame | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素集中 | 改动清单 | calc-shaman-elemental-combat-elemental-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素防护 | 改动清单 | calc-shaman-elemental-combat-elemental-warding | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火焰试炼 | 改动清单 | calc-shaman-elemental-trial-by-fire | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 风暴之眼 | 改动清单 | calc-shaman-elemental-combat-eye-of-the-storm | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 地缚 | 改动清单 | calc-shaman-elemental-combat-earthbound | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素射程 | 改动清单 | calc-shaman-elemental-combat-elemental-reach | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 熔岩爆裂 | 改动清单 | calc-shaman-elemental-combat-lava-burst | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闪电超载 | 改动清单 | calc-shaman-elemental-combat-lightning-overload | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素之怒 | 改动清单 | calc-shaman-elemental-combat-elemental-fury | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素掌握 | 改动清单 | calc-shaman-elemental-elemental-mastery | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 大地之握 | 改动清单 | calc-shaman-enhancement-earth-s-grasp | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 雷鸣猛击 | 改动清单 | calc-shaman-enhancement-thundering-strikes | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 先祖知识 | 改动清单 | calc-shaman-enhancement-ancestral-knowledge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 守护图腾 | 改动清单 | calc-shaman-enhancement-guardian-totems | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 聪慧 | 改动清单 | calc-shaman-enhancement-mental-dexterity | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化幽魂之狼 | 改动清单 | shaman-improved-ghost-wolf | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化闪电之盾 | 改动清单 | calc-shaman-enhancement-improved-lightning-shield | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素武器 | 改动清单 | calc-shaman-enhancement-elemental-weapons | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 萨满专注 | 改动清单 | calc-shaman-enhancement-shamanistic-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 风暴打击 | 改动清单 | calc-shaman-enhancement-stormstrike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵魂武器 | 改动清单 | calc-shaman-enhancement-spirit-weapons | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 精神敏锐 | 改动清单 | calc-shaman-enhancement-mental-quickness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化风暴打击 | 改动清单 | calc-shaman-enhancement-improved-stormstrike | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 漩涡武器 | 改动清单 | calc-shaman-enhancement-maelstrom-weapon | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 先知之怒 | 改动清单 | shaman-rage-of-the-farseer | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化治疗波 | 改动清单 | calc-shaman-restoration-improved-healing-wave | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 潮汐集中 | 改动清单 | calc-shaman-restoration-tidal-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 全神贯注 | 改动清单 | calc-shaman-restoration-mindfulness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然优雅 | 改动清单 | calc-shaman-restoration-natural-grace | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 图腾集中 | 改动清单 | calc-shaman-restoration-totemic-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化复生 | 改动清单 | calc-shaman-restoration-improved-reincarnation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 先祖治疗 | 改动清单 | calc-shaman-restoration-ancestral-healing | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗专注 | 改动清单 | calc-shaman-restoration-healing-focus | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 水之护盾 | 改动清单 | calc-shaman-restoration-water-shield | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 潮汐掌握 | 改动清单 | calc-shaman-restoration-tidal-mastery | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 恢复图腾 | 改动清单 | calc-shaman-restoration-restorative-totems | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 法力之潮图腾 | 改动清单 | calc-shaman-restoration-mana-tide-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗之道 | 改动清单 | calc-shaman-restoration-healing-way | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然迅捷 | 改动清单 | calc-shaman-restoration-nature-s-swiftness | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 净化 | 改动清单 | calc-shaman-restoration-purification | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 激流 | 改动清单 | calc-shaman-restoration-riptide | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 雷霆召唤 | 改动清单 | calc-shaman-elemental-combat-call-of-thunder | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化图腾 | 改动清单 | shaman-enhancing-totems | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 双手斧和锤 | 改动清单 | shaman-two-handed-axes-and-maces | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 强化武器图腾 | 改动清单 | shaman-improved-weapon-totems | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 武器掌握 | 改动清单 | shaman-weapon-mastery | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然指引 | 改动清单 | shaman-nature-s-guidance | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 图腾掌握 | 改动清单 | shaman-totemic-mastery | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闪电箭 | 改动清单 | spellbook-shaman-lightning-bolt | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 地震术 | 改动清单 | spellbook-shaman-earth-shock | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 地缚图腾 | 改动清单 | spellbook-shaman-earthbind-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 石爪图腾 | 改动清单 | spellbook-shaman-stoneclaw-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 烈焰震击 | 改动清单 | spellbook-shaman-flame-shock | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灼热图腾 | 改动清单 | spellbook-shaman-searing-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火焰新星 | 改动清单 | shaman-fire-nova | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 净化术 | 改动清单 | spellbook-shaman-purge | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 元素的召唤 | 改动清单 | spellbook-shaman-call-of-the-elements | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰霜震击 | 改动清单 | spellbook-shaman-frost-shock | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 收回图腾 | 改动清单 | spellbook-shaman-totemic-recall | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 熔岩图腾 | 改动清单 | spellbook-shaman-magma-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 先祖的召唤 | 改动清单 | spellbook-shaman-call-of-the-ancestors | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闪电链 | 改动清单 | spellbook-shaman-chain-lightning | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 灵魂的召唤 | 改动清单 | spellbook-shaman-call-of-the-spirits | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 石化武器 | 改动清单 | spellbook-shaman-rockbiter-weapon | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 石肤图腾 | 改动清单 | spellbook-shaman-stoneskin-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 闪电之盾 | 改动清单 | spellbook-shaman-lightning-shield | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火舌武器 | 改动清单 | spellbook-shaman-flametongue-weapon | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 大地之力图腾 | 改动清单 | spellbook-shaman-strength-of-earth-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 冰封武器 | 改动清单 | spellbook-shaman-frostbrand-weapon | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 幽魂之狼 | 改动清单 | spellbook-shaman-ghost-wolf | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 图腾投射 | 改动清单 | spellbook-shaman-totemic-projection | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 水下呼吸 | 改动清单 | spellbook-shaman-water-breathing | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 抗寒图腾 | 改动清单 | spellbook-shaman-frost-resistance-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 视界术 | 改动清单 | spellbook-shaman-far-sight | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 抗火图腾 | 改动清单 | spellbook-shaman-fire-resistance-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 火舌图腾 | 改动清单 | spellbook-shaman-flametongue-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 水上行走 | 改动清单 | spellbook-shaman-water-walking | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 星界传送 | 改动清单 | spellbook-shaman-astral-recall | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 根基图腾 | 改动清单 | spellbook-shaman-grounding-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 自然抗性图腾 | 改动清单 | spellbook-shaman-nature-resistance-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 风怒武器 | 改动清单 | spellbook-shaman-windfury-weapon | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 风怒图腾 | 改动清单 | spellbook-shaman-windfury-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 岗哨图腾 | 改动清单 | spellbook-shaman-sentry-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 风墙图腾 | 改动清单 | spellbook-shaman-windwall-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 风之优雅图腾 | 改动清单 | spellbook-shaman-grace-of-air-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗波 | 改动清单 | spellbook-shaman-healing-wave | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 先祖之魂 | 改动清单 | spellbook-shaman-ancestral-spirit | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 消毒术 | 改动清单 | spellbook-shaman-cure-poison | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 战栗图腾 | 改动清单 | spellbook-shaman-tremor-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗之泉图腾 | 改动清单 | spellbook-shaman-healing-stream-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 次级治疗波 | 改动清单 | spellbook-shaman-lesser-healing-wave | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 祛病术 | 改动清单 | spellbook-shaman-cure-disease | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 清毒图腾 | 改动清单 | spellbook-shaman-poison-cleansing-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 法力之泉图腾 | 改动清单 | spellbook-shaman-mana-spring-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 复生 | 改动清单 | spellbook-shaman-reincarnation | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 祛病图腾 | 改动清单 | spellbook-shaman-disease-cleansing-totem | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 治疗链 | 改动清单 | spellbook-shaman-chain-heal | L0 | https://wowforever.wclbox.com/gaidong<br>https://wowforever.wclbox.com/_shuju/r-1792976599011/changes.json |
| 变换之力 | 法术书 | druid-变换之力 | L0 | https://wowforever.wclbox.com/fashu/druid |
| 探索丹莫罗 | 成就 | ach-627 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索杜隆塔尔 | 成就 | ach-728 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索莫高雷 | 成就 | ach-736 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索贫瘠之地 | 成就 | ach-750 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索奥特兰克山脉 | 成就 | ach-760 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索阿拉希高地 | 成就 | ach-761 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索荒芜之地 | 成就 | ach-765 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索诅咒之地 | 成就 | ach-766 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索提瑞斯法林地 | 成就 | ach-768 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索银松森林 | 成就 | ach-769 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索西瘟疫之地 | 成就 | ach-770 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索东瘟疫之地 | 成就 | ach-771 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索希尔斯布莱德丘陵 | 成就 | ach-772 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索辛特兰 | 成就 | ach-773 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索灼热峡谷 | 成就 | ach-774 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索燃烧平原 | 成就 | ach-775 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索艾尔文森林 | 成就 | ach-776 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索逆风小径 | 成就 | ach-777 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索暮色森林 | 成就 | ach-778 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索洛克莫丹 | 成就 | ach-779 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索赤脊山 | 成就 | ach-780 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索荆棘谷 | 成就 | ach-781 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索悲伤沼泽 | 成就 | ach-782 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索西部荒野 | 成就 | ach-802 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索湿地 | 成就 | ach-841 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索泰达希尔 | 成就 | ach-842 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索黑海岸 | 成就 | ach-844 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索灰谷 | 成就 | ach-845 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索千针石林 | 成就 | ach-846 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索石爪山脉 | 成就 | ach-847 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索凄凉之地 | 成就 | ach-848 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索菲拉斯 | 成就 | ach-849 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索尘泥沼泽 | 成就 | ach-850 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索塔纳利斯 | 成就 | ach-851 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索艾萨拉 | 成就 | ach-852 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索费伍德森林 | 成就 | ach-853 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索安戈洛环形山 | 成就 | ach-854 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索月光林地 | 成就 | ach-855 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索希利苏斯 | 成就 | ach-856 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索冬泉谷 | 成就 | ach-857 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索艾泽拉斯 | 成就 | ach-62053 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索东部王国 | 成就 | ach-62353 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索河林 | 成就 | ach-62354 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索卡利姆多 | 成就 | ach-62355 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索海加尔山 | 成就 | ach-62356 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |
| 探索辛德拉 | 成就 | ach-63684 | L0 | https://wowforever.wclbox.com/_shuju/r-1791987485943/chengjiu.json |

## 只有插件来源的那一类（按设计不可逐字回查，不算冒充官方）

这一格 1862 条的支撑来源是本地插件那份表（GearInsight / XR 的 Data.lua），**它根本没有对应的网页可以点开核对**，所以逐字回查这条路对它们不适用。这些条目在成品里一律定 L1 并写明「只有插件一家说过」，界面按单源处理——不是漏挂链接，是这条线的来源形态决定的。要升 L0 得等第二处能逐字回查的源（官方中文列表，或开服后游戏内逐条对）。

| 出处 | 条数 |
| --- | --- |
| 世界掉落 | 1537 |
| 世界稀有 | 325 |

## 处置规则

1. 未命中条目先人工回原文比对：确实官方写过 → 把 `provenance.url` 改成真正那篇；官方没写过 → 降级 L2 并在页面显示待实测，**不允许留着 L0**。
2. `--strict` 只在**声称官方（L0/L1）的条目没逐字命中**或有结构性问题时退出码非 0；L2/L3 的未命中与「去掉排版空格才命中」都只出警告——前者本来就没声称官方，后者是 HTML 强调标签把词从中间拆开造成的转换产物（squeeze 只删汉字之间的空白，不可能把错词拼成对词）。**但并写形式指代的词（如官方写「冰霜与火焰陷阱」）不是转换产物，必须逐条走 `audit-exceptions.json` 留人工判定**，不能靠这条降级蒙过去。
3. 改完重跑 `node tools/build-data.js` 与本脚本，命中率必须回升。
4. 掉落与 BOSS 技能不在本脚本范围内：目前 22 座副本的 `bosses` 与 `drops` 是空的，没有数据就没有写错的风险；等实测有数据时，`build-data.js` 的百分比卡口负责拦。
