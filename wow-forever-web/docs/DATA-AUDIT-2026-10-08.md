# 译名体检报告 · 2026-10-08（wow-data）

脚本：`python3 tools/audit-translations.py`。做法是把每个对外展示的中文名（术语词条、副本名、系统名，以及时间线、技能四态、种族页引用的官方整句）拿回它自己在 `provenance` 里声明的官方来源页做逐字包含比对。**只读核对，不改数据。**

## 结果

| 项 | 数 |
| --- | --- |
| 词条总数 | 347 |
| 在声明的官方页里逐字命中 | 287 |
| 去掉汉字间排版空格才命中（要人眼确认） | 45 |
| **未命中（要人工回原文看）** | 4 |
| 已人工判定并留痕（见 audit-exceptions.json） | 1 |
| **声称官方却核不到（L0/L1 缺官方链接）** | 0 |
| 本来就标 L2/L3 的非官方中文名（预期，界面已如实标注） | 10 |

核对范围含 `glossary.json` 词条、`dungeons.json` 副本中文名、`systems.json` 系统卡片中文名、`timeline.json` 与 `abilities.json` 的官方整句，以及 `races.json` 的种族简介、种族特长整句、亮点组合与天裔导语。
| 命中率 | 82.7% |

## 来源页

| 状态 | 页面 | 承担词条 |
| --- | --- | --- |
| 仅缓存 | https://wow.blizzard.cn/news/24301515/index.html | 143 |
| 仅缓存 | https://wow.blizzard.cn/news/24303313/index.html | 7 |
| 仅缓存 | https://wow.blizzard.cn/news/24301514/index.html | 74 |
| 仅缓存 | https://wow.blizzard.cn/news/24304075/index.html | 95 |
| 仅缓存 | https://news.blizzard.com/en-us/article/24303862/world-of-warcraft-forever-whats-next-panel-recap | 9 |
| 仅缓存 | https://wow.blizzard.cn/news/24304160/index.html | 9 |
| 仅缓存 | https://wow.blizzard.cn/news/24302070/index.html | 2 |
| 仅缓存 | https://worldofwarcraft.blizzard.com/en-us/forever | 2 |

## 只在去掉排版空格后命中（人工确认这几条）

官方页用加粗标签强调词的一部分时，转成纯文本会在汉字中间留下空格。下列词条属于这种情况，**脚本没法替你判断是不是同一个词，要人眼过一遍**。

| 词条 | 职业 | 出处 |
| --- | --- | --- |
| 火焰陷阱 | 术语 hunter | https://wow.blizzard.cn/news/24301515/index.html |
| 被遗忘者的意志：移除魅惑、恐惧和催眠效果。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 食尸：吞噬尸体，在持续时间内恢复35%的生命值和法力值。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 水下呼吸（被动）：在水下的呼吸时间延长300%。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 哀伤之触（被动）：你的攻击有时会吸取生命值。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 战争践踏：使附近的敌人昏迷，持续2秒。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 栽培：额外长出无需草药学即可采集的草药。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 原野疾驰（被动）：持续移动时，移动速度会逐渐提高。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 耐久（被动）：总生命值提高5%，命中几率提高1%。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 狂暴：施法速度和攻击速度提高10%，持续10秒。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 极速再生：在持续时间内恢复50%的最大生命值。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 野兽杀手（被动）：对野兽造成的伤害提高5%。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 再生（被动）：在战斗中保持10%的生命值恢复。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 踏空而行：在空中向下滑行10秒。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 天穹视界：获得元素祝福，移动速度提高10%。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 风灵护佑（被动）：近战、远程与法术急速提高1%。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 元素洞察（被动）：对元素生物造成的伤害提高5%。 | 种族特长 horde | https://wow.blizzard.cn/news/24304075/index.html |
| 生存意志：移除昏迷效果。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 感知：侦测潜行的敌人，持续20秒。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 剑类武器专精（被动）：剑类使法术和技能的爆击几率提高2%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 人类精魂（被动）：精神提高5%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 石像形态：免疫流血、中毒和疾病效果，并降低受到的物理伤害，持续8秒。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 寻找财宝：追踪附近的宝箱。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 锤类武器专精（被动）：锤类使法术和技能的爆击几率提高1%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 王牌猎人（被动）：对野兽造成的伤害提高5%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 艾露恩之光：爆击几率提高10%，持续15秒。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 影遁：在静止时获得潜行状态。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 迅捷（被动）：躲闪几率提高1%，移动速度提高2%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 精灵之魂（被动）：死亡时的移动速度提高75%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 逃命专家：短暂免疫定身和诱捕效果。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 我知道了！：使接下来的3个法术或技能消耗降低，伤害或治疗效果提高10%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 开阔思维（被动）：法力值、怒气值或能量值上限提高5%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 工程学专精（被动）：工程学装置更加可靠。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 踏空而行：在空中向下滑行10秒。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 阅读魔网：激活一条魔网，生命与法力恢复速度提高100%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 风灵护佑（被动）：近战、远程与法术急速提高1%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 元素洞察（被动）：对元素生物造成的伤害提高5%。 | 种族特长 alliance | https://wow.blizzard.cn/news/24304075/index.html |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html |
| 《魔兽世界》：“无限”带来了更多角色创建选择，包括兽人法师、巨魔术士、亡灵圣骑士、人类猎人、侏儒牧师、矮人萨满祭司，以及首次登场的天裔。 | 亮点组合 引用 | https://wow.blizzard.cn/news/24304075/index.html |
| 天裔是《魔兽世界》：“无限”中的全新可玩种族，并将以独特的身份参与逐步展开的故事。选择这一新种族时，玩家可以选择加入部落阵营、能够成为萨满祭司的塑风者天裔，或加入联盟阵营、能够成为法师的高阶会天裔。 | 天裔导语 引用 | https://wow.blizzard.cn/news/24304075/index.html |

## 已人工判定并留痕

这些条目没能逐字命中，但已回原文人工判定并把依据写进 `src/data/audit-exceptions.json`。

| 词条 | 结论 | 官方原句 | 判定日期 |
| --- | --- | --- | --- |
| 冰霜陷阱（术语） | keep-L0 | 冰霜 与 火焰 陷阱现在分别计算冷却时间 | 2026-10-08 |

## 未命中清单（逐条待人工核对）

未命中不等于词条错，常见原因是：官方页用的是另一个写法、词条是从同系列另一篇文章采的、或页面改版删了这段。**但在人工确认之前，这些条目的 L0 身份不可信。**

| 名称 | 出处 | 标识 | 当前级别 | 声明来源 |
| --- | --- | --- | --- | --- |
| 挖掘场：湿地 | 副本 | whelgars-excavation | L2 | https://news.blizzard.com/en-us/article/24303862/world-of-warcraft-forever-whats-next-panel-recap |
| 达拉然 | 副本 | city-of-dalaran | L2 | https://news.blizzard.com/en-us/article/24303862/world-of-warcraft-forever-whats-next-panel-recap |
| 永久 60 级 | 系统 | level-cap | L2 | https://news.blizzard.com/en-us/article/24303862/world-of-warcraft-forever-whats-next-panel-recap<br>https://wow.blizzard.cn/news/24304160/index.html |
| 海加尔山 | 系统 | zone-mount-hyjal | L3 | https://worldofwarcraft.blizzard.com/en-us/forever |

这4条当前都标 L2/L3，界面显示"待实测"，**没有在冒充官方**；列在这里是因为它们的中文名来自转载/英文页，等官方中文稿或实测后再定名。

## 本来就标着非官名的条目（预期，不需要处理）

这些中文名来自转载、开放数据或第三方挖掘，条目本身标的是 L2/L3，界面显示"待实测"，不属于"冒充官方"。留着这份清单是为了上线后逐条回官方页升级。

| 名称 | 出处 | 级别 |
| --- | --- | --- |
| 剃刀高地 | 副本 razor-krendor | L3 |
| 奥达曼 | 副本 uldaman | L3 |
| 怒焰裂谷 | 副本 ragefire-chasm | L3 |
| 哀嚎洞穴 | 副本 wailing-caverns | L3 |
| 死亡矿井 | 副本 deathmine | L3 |
| 影牙城堡 | 副本 shadowfang-keep | L3 |
| 监狱 | 副本 the-stocks | L3 |
| 黑暗深渊 | 副本 blackfathom-deeps | L3 |
| 诺莫瑞根 | 副本 gnomeregan | L3 |
| 血色修道院 | 副本 scarlet-monastery | L3 |

## 处置规则

1. 未命中条目先人工回原文比对：确实官方写过 → 把 `provenance.url` 改成真正那篇；官方没写过 → 降级 L2 并在页面显示待实测，**不允许留着 L0**。
2. 改完重跑 `node tools/build-data.js` 与本脚本，命中率必须回升。
3. 掉落与 BOSS 技能不在本脚本范围内：目前 22 座副本的 `bosses` 与 `drops` 是空的，没有数据就没有写错的风险；等实测有数据时，`build-data.js` 的百分比卡口负责拦。
