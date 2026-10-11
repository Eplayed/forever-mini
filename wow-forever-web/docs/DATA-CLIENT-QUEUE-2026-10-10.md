# 副本线 × 客户端排队表 · 对账记录（2026-10-10）

这份是**对账记录，不是门禁**：它说清"这一轮我们拿客户端的数对了什么、对出什么、哪些两个数都留着"。
配套口径在 `wow-infinite-sources.md` 8.6，链路命令在 `DATA-MAINTENANCE.md` 第二节。

## 一、取数链

```
_shuju/<发布号>/meta.json 的 foreverBuild ──┐
                                            ├→ tools/fetch-db2-groupfinder.py   → upstream/db2-group-finder.json
wago.tools/db2/GroupFinderActivity/csv ─────┘        （109 条排队活动 + 5 个类别名，构建 1.60.1.70334）

_shuju/<发布号>/dungeons.json ──→ tools/scrape-wclbox-shuju.py --group dungeons
                                        → upstream/wclbox-dungeon-meta.json（35 条排队元数据）

两份上游 + 现有的名单/掉落/卡片 ──→ tools/merge-dungeons.js
                                        → dungeons.json（补英文名 / 人数 / 区间对账）
                                        → queue.json（客户端能排到、本站没名单的）
```

三个抓取器 + 一个合并器都已经串在 `bash tools/refresh.sh dungeons` 里，单跑任何一步都不算重跑完。

## 二、补上了什么

| 项 | 之前 | 现在 |
| --- | --- | --- |
| 英文原名 | 38 座里 **18 座是空的** | **38 座全部有**（18 座由客户端排队表补，标记 `nameEnFrom: db2`，每座挂着 wago 链接与取回日期） |
| 进入人数 | 一直没有这一栏 | **31 座有**（客户端里还没排队条目的 7 座不给默认值） |
| 所在区域 / 卡片计数 / 载入图 | 4 座因名字对不上而缺 | 4 座补上（死亡矿井、暴风城监狱、剃刀高地、湿地挖掘场） |
| 客户端里能排到、本站没名单的 | 完全不知道有 | 登记 51 条排队条目，其中 **16 条 / 13 个名字**本站没有 |
| 客户端里还排不到队的无限新增本 | 界面看起来"数据齐了" | **5 座**逐条写明"客户端的队伍查找器里还没有这座本" |

补出来的 18 个英文原名（数据里 `nameEnFrom == "db2"` 的那 18 条）：
暴风城监狱 Stormwind Stockades、剃刀沼泽 Razorfen Kraul、血色修道院墓地 / 图书馆 / 军械库 / 大教堂
Scarlet Monastery - Graveyard / Library / Armory / Cathedral、祖尔法拉克 Zul'Farrak、玛拉顿 Maraudon、
沉没的神庙 Sunken Temple、黑石深渊 Blackrock Depths、厄运之槌东 / 北 / 西 Dire Maul (East / North / West)、
黑石塔下层 / 上层 Lower / Upper Blackrock Spire、通灵学院 Scholomance、
斯坦索姆主门 / 仆从入口 Stratholme (Main Gate / Service Gate)。

## 三、对出分歧的（两个数都留着，界面并列显示）

**等级区间 7 座**——本站主区间一律不改（前 4 座的现值来源写明是官方 Beta 公告）：

| 这座本 | 本站现在 | 客户端的队伍查找器 |
| --- | --- | --- |
| 领主大厅 | 13-18 | 13-20 |
| 洛丹伦废墟 | 15-20 | 15-22 |
| 挖掘场：湿地 | 26-31 | 26-33 |
| 达拉然城 | 28-33 | 28-35 |
| 哀嚎洞穴 | 17-24 | 15-24 |
| 影牙城堡 | 22-30 | 20-30 |
| 奥妮克希亚的巢穴 | 没有区间 | 60-60 |

**同一座有两种排队人数 3 座**：黑暗深渊 5 人 / 另有一条 10 人、诺莫瑞根 5 人 / 10 人、沉没的神庙 5 人 / 20 人。
是不是"同一个本两种规模"要进游戏才能定，界面上两个都摆。顺带确认：**黑石塔上层在客户端里就是 10 人条目**。

**英文原名两说 2 座**：剃刀高地（本站 The Razor Krendor / 客户端 Razorfen Downs）、
挖掘场：湿地（官方回顾 Whelgar's Excavation / 客户端 Excavation Site: Wetlands）。

**客户端里还没有排队条目 7 座**：沉没之城、克罗多克要塞、奥卡兹监狱、黑喉要塞、塑源者平台，
外加本站的两座团本占位（The Barrow Deeps、Hyjal Summit）。

## 四、本站还没有名单的 13 个名字

地下城 2 座：Demon Fall Canyon（60 级 5 人）、Karazhan Crypts（60 级 5 人）。
团本 11 个：Zul'Gurub、Molten Core（客户端记了 2 条）、Blackwing Lair、Naxxramas、
Ahn'Qiraj Ruins（2 条）、Ahn'Qiraj Temple（2 条），以及 5 个陌生新名
**Storm Cliffs、The Tainted Scar、Nightmare Grove、The Crystal Vale、Scarlet Enclave**（都 40 人 60 级）。

副本页先单列一张表摆这些，按英文原名归并（同名两条说成"客户端记了几条"，不让玩家误以为两座本），
写明"中文定名未公布、开放前可能变化"。**2026-10-11 已按用户批准展开成第 16 页 `raids.html`**：
15 个团队条目名字按人数分档、同名两条归并并写明"两种规模 / 同规模的两个入口"、参考站自述的 3 座并列对照。
规格见 `UI.md` 3.26，剩下的待办见 `PLAN-open-items.md` 8i / 8j。

## 五、没有采的（写清楚为什么）

- **`enter` 列**：解包站 `_shuju/…/dungeons.json` 每座给一个 `enter`（怒焰裂谷 8、影牙 10、黑石深渊 40……）。
  逐列与客户端排队表比对，`MinLevel / MaxLevelSuggestion / MaxPlayers / PlayerConditionID / MinGearLevelSuggestion`
  都对不上任何一个，归不了因 → 那是它自己拍的数，不采。判定原文写在 `upstream/db2-group-finder.json` 的 `meta.caveat`。
- **`summary` 列**：别人写的介绍句子，按红线不落盘（第三方站只取事实性标识符）。
- **`abbr / short / demo / top`**：它自定的中文简称与含义不明的标记位，不采。
- **不覆盖主区间**：客户端的数不冒充官方结论，官方公告的数也不替客户端隐瞒——两个都摆。
- **`queue.json` 单独成文件**：`export-mini.js` 会把整份 `dungeons.json` 打进小程序快照并用它的长度报"共 N 座"，
  混进去会让小程序首页把 38 座报成 54 座。这份是"客户端能排到"，不是"本站收录的副本"，本来也不该是一个东西。

## 六、复核方法（想自己验一遍）

```bash
cd wow-forever-web
python3 tools/fetch-db2-groupfinder.py --show      # 只看能不能取到，不落盘
python3 tools/data-status.py                       # 缺口分类报告（副本英文名应为 0）
python3 - <<'PY'                                   # 逐座看三种分歧各有几条
import json
a=sum([json.load(open('src/data/dungeons.json'))[k] for k in ('newDungeons','classicDungeons','raids')],[])
print('英文名缺', len([x for x in a if not x.get('nameEn')]))
print('有人数', len([x for x in a if x.get('partySize')]))
print('区间两说', len([x for x in a if x.get('levelRangeClient')]))
PY
```

上游那份 CSV 是原始证据：`src/data/upstream/db2-group-finder.json`，里面每条都带着它自己的活动号与列名，
可以和 `https://wago.tools/db2/GroupFinderActivity/csv?build=1.60.1.70334` 逐行对。
wago 只留最近几个构建号，对不上时先换构建号，别怀疑我们抄错。
