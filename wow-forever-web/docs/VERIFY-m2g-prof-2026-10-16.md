# VERIFY · M2-G 配方补「来源商人 / 图纸掉落」（2026-10-16）

角色：wow-dev（含 wow-data 的抽取）｜输入：`docs/PRD-web-parity-2026-10-16.md` §三 P0 第 9 条
（"补来源商人 / 学习门槛两列的可得部分；缺失整列不显示"）｜产出：数据 + 两栈界面 + 卡口
｜交接给：站主（**"学习门槛"这一列这一版没做，原因在 §三**）

## 一、做了什么

站内配方行原来只有一格 `source`，取值只有"训练师"（451 条）或空（1,539 条），
玩家看到的是"来源：训练师"——等于没说。这一轮把 XR 那份专业库里真正的事实并进来：

| 新东西 | 覆盖 | 从哪来 |
| --- | --- | --- |
| `vendors`（哪几个商人在哪个区域卖这张图纸） | **647 / 1,990 条配方** | `XR_DungeonGuide/Data_Prof.lua` 的 `source.vendors` |
| `formulaDrops`（图纸从谁身上掉、在哪个区域） | **336 / 1,990 条** | 同上的 `source.drops`，**掉率 `chance` 在抽取阶段就丢（782 处）** |

管线：`tools/extract-xr-prof.py`（新）→ `src/data/upstream/xr-prof.json`（1,902 条）
→ `tools/merge-prof-sources.py`（新）→ `src/data/professions.json`。
`tools/refresh.sh prof` 那条链已按顺序补上这两步（**顺序不能倒**：`merge-professions.js` 整表重写配方，
先并后 merge 会被冲掉）。合并幂等：连跑两次 md5 一致。

界面：专业页「来源」那一格改成三层，各来自不同资料、**缺哪层就不写哪层**（不写"待补"）——
参考站给的类别 → `商人：山达·细须（洛克莫丹）、…  等 N 处` → `图纸掉落：X（区域）`。
两栈同轮改（旧站 `src/js/app.js` 的 `srcCell`、新站 `ProfessionsPage.vue` 的 `srcLines`），
`app-parity --strict --page professions` 全组合无差异。

## 二、卡口与反向测试

`build-data.js` 专业段加四条：`srcFrom` 只许 `xr`、有 `vendors`/`formulaDrops` 必须带 `srcFrom`、
名字里不许有句子标点与百分号、`vMore`/`dMore` 必须是正整数；
另加两条对数：`meta.xrProf.withVendors` / `withDrops` 必须等于实际逐条数（防"快照与成品两张皮"）。
`scale.json` 新增 `profVendors` / `profDrops`。

`site-check.py` 专业段 +4 条：默认专业里写出商人的行数 = 数据条数（60/60）、
换到有图纸掉落的专业那一段真出来（47/47）、那一行是专名不是整段讲解、
来源格不写掉率与概率。

**反向测试 4 条全部咬住**（`/tmp/m2g-reverse.py`）：商人名字塞整句、有商人却不标 `srcFrom`、
`withVendors` 造假、截断计数写 0；还原后 exit 0 且 `professions.json` md5 与备份一致。
这一轮还抓出自己测试脚本的一个假通过：`find()` 里另开了一次 `json.load`，
脏数据改在另一份对象上、根本没进要写盘的那份，前三条一开始全"通过"。
**判据：反向测试必须先看到它红，再看它绿**——已经在同一类坑上栽过第三次了。

## 三、"学习门槛"这一列这一版没做（要站主或实测定）

XR 那份配方行里有两个数看着就是"学习门槛"，但**含义没定，所以一个都没上页面**：

1. 行第 5 位 `learn`：247755 给 10，而站内 `skill.orange` 是 1；250344 给 15，站内橙点也是 15。
   同一个位置有时等于橙点、有时不等 → 说不清它是"学会要的技能点"还是"要的角色等级"。
2. `source.skill`：10011 给 185，站内橙点 200。同样没有依据。

按红线"缺数据显示待实测、禁止猜"，**没依据的数不发**。两个数在快照的 `meta.counts` 里记着
（`srcHasLearn` 1,697 / `srcHasSkill` 1,078），源里有什么、我们没取什么，一目了然。
要定这两个数的含义，只能进游戏对着某个配方看它的"学会需要…"提示（站主那台装有客户端的机器），
或等官方/参考站把字段名写清。已列进开放项 26。

## 四、还有一条观感问题（不卡，等站主看）

`formulaDrops` 里的 NPC 名是英文专名（`Gnarlpine Gardener`、`Kul Tiras Sailor`），区域是中文——
因为插件那份就没给这些 NPC 的中文名，红线禁止机翻，所以照原样显示。
要不要在界面上给这类英文专名加一个"英文原名"的提示样式（像术语页那样分两列），
是个设计决定，没替站主做。

## 五、跑了什么

| 命令 | 结果 |
| --- | --- |
| `python3 tools/extract-xr-prof.py` | 1,905 行 → 1,902 条；商人 648、图纸掉落 334、掉率字段丢 782 处 |
| `python3 tools/merge-prof-sources.py` | 配方 1,990 条：并上商人 647 · 掉落 336；XR 有、站内没有 16 条；连跑两次 md5 一致 |
| `node tools/build-data.js` | exit 0；专业行读数「带来源商人 647 条 · 带图纸掉落 336 条」 |
| `python3 tools/site-check.py --only professions` | 16 / 16 通过（含新增 4 条） |
| `python3 tools/app-parity.py --strict --page professions` | 全部组合无差异 |
| `python3 /tmp/m2g-reverse.py` | 4 条脏数据全部拦下 + 还原 md5 一致 |
| 整站全量 + 两栈全量 | 见文末补记 |
