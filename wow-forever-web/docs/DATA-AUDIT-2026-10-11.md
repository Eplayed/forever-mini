# 译名体检报告 · 2026-10-11（wow-data）

脚本：`python3 tools/audit-translations.py`。做法是把每个对外展示的中文名（术语词条、副本名、系统名，以及时间线、技能四态、种族页引用的官方整句）拿回它自己在 `provenance` 里声明的官方来源页做逐字包含比对。**只读核对，不改数据。**

## 结果

| 项 | 数 |
| --- | --- |
| 词条总数 | 1468 |
| 在声明的官方页里逐字命中 | 1420 |
| 去掉汉字间排版空格才命中（要人眼确认） | 44 |
| **未命中（要人工回原文看）** | 2 |
| 已人工判定并留痕（见 audit-exceptions.json） | 2 |
| **声称官方却核不到（L0/L1 缺官方链接）** | 0 |
| 本来就标 L2/L3 的非官方中文名（预期，界面已如实标注） | 0 |

核对范围含 `glossary.json` 词条、`dungeons.json` 副本中文名、`systems.json` 系统卡片中文名、`world.json` 的稀有精英名与掉落物名、书名与上交奖励名（区域名不在此列，见上）、`changes.json` 的 964 条天赋与法术名（只核名称，句子本站不存）、`legacy.json` 的传承专长名与进度奖励名（同样只核名称），`timeline.json` 与 `abilities.json` 的官方整句，以及 `races.json` 的种族简介、种族特长整句、亮点组合与天裔导语。
| 命中率 | 96.7% |

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
| 缓存 | https://wowforever.wclbox.com/xiyou | 66 |
| 缓存 | https://wowforever.wclbox.com/shuji | 45 |
| 缓存 | https://wowforever.wclbox.com/gaidong | 964 |
| 缓存 | https://wowforever.wclbox.com/_shuju/r-1791485113190/changes.json | 964 |
| 缓存 | https://wowforever.wclbox.com/chuancheng | 25 |
| 缓存 | https://wowforever.wclbox.com/_shuju/r-1791561473931/legacy.json | 25 |

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

这些条目没能逐字命中，但已回原文人工判定并把依据写进 `src/data/audit-exceptions.json`。

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

这2条当前都标 L2/L3，界面显示"待实测"，**没有在冒充官方**；列在这里是因为它们的中文名来自转载/英文页，等官方中文稿或实测后再定名。

## 处置规则

1. 未命中条目先人工回原文比对：确实官方写过 → 把 `provenance.url` 改成真正那篇；官方没写过 → 降级 L2 并在页面显示待实测，**不允许留着 L0**。
2. `--strict` 只在**声称官方（L0/L1）的条目没逐字命中**或有结构性问题时退出码非 0；L2/L3 的未命中与「去掉排版空格才命中」都只出警告——前者本来就没声称官方，后者是 HTML 强调标签把词从中间拆开造成的转换产物（squeeze 只删汉字之间的空白，不可能把错词拼成对词）。**但并写形式指代的词（如官方写「冰霜与火焰陷阱」）不是转换产物，必须逐条走 `audit-exceptions.json` 留人工判定**，不能靠这条降级蒙过去。
3. 改完重跑 `node tools/build-data.js` 与本脚本，命中率必须回升。
4. 掉落与 BOSS 技能不在本脚本范围内：目前 22 座副本的 `bosses` 与 `drops` 是空的，没有数据就没有写错的风险；等实测有数据时，`build-data.js` 的百分比卡口负责拦。
