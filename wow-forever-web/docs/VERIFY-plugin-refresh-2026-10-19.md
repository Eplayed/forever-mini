# 验证记录 · 插件 10-19 更新这一轮（稀有坐标 + 地图号主源 + 版本号来源）

本轮角色：wow-data + wow-dev ｜触发：站主"~/Documents/project/.scratch/wow/ 插件更新了"
｜产出：`tools/{extract-plugin-tables.py,extract-xr-zonemap.py,merge-world.js,merge-spells.py,merge-achievements.py,site-check.py}`、
`src/data/upstream/{gi-rares,gi-spells,gi-achievements,xr-skills}.json`、`src/data/{world,spells,achievements}.json`、
`docs/wow-infinite-sources.md` §二十 ｜代码提交：见本文件末尾

## 一、跑了什么

```bash
python3 tools/extract-plugin-tables.py --out-dir /tmp/up-new   # 先抽到临时目录比对，不动仓库
python3 tools/extract-plugin-tables.py                          # 确认差异后才真写进 upstream
python3 tools/merge-spells.py && python3 tools/merge-achievements.py
node tools/merge-world.js
node tools/build-data.js                                        # 校验通过
python3 tools/app-assets.py && cd app && npm run build && npx vitest run   # 74 / 74
python3 -u tools/site-check.py --app --only world_pins          # 25 / 25
python3 -u tools/site-check.py --app                            # 全跑，见文末
```

## 二、盘出来的版本与数据变化

| 插件 | 之前 | 现在 | 对我们这条线的实际影响 |
| --- | --- | --- | --- |
| GearInsight_Forever | 0.4.29 | **0.4.32** | 稀有仍 338 条，**每行多了 `ui=<地图号>`**；**24 条稀有的坐标改了值** |
| XR_DungeonGuide | 文档里写 0.37.1 | `.toc` 是 **Version: 65** | `Data_Skills` 577 → **583**（圣骑士 +1 / 牧师 +1 / 萨满 +1 / 法师 +3）；`Data_ZoneMap` 仍 80 条 |
| DungeonsForever | — | **1.8.20（新）** | 44 个数据文件 13 MB；**LICENSE 是「保留所有权利」** |
| HandyNotes_DungeonLocations | — | **1.10（新）** | 多资料片副本入口点位 |

合并后的成品变化（逐字段核过 diff，不靠"看起来差不多"）：

- `world.json`：326 条稀有的地图号来源标成 `gi-ui`、出处 url 与核对日跟着新版本走、
  **24 条坐标改了值**。按区域拆开看（y 变大＝往南）：
  **赤脊山 8 条 dx 全是 −5.0~−5.1、dy 全 0** —— 这明显是作者做的一次整体平移；
  莫高雷 6 条 dx 中位 −0.3、dy 中位 +9.7（范围 +1.3~+11.3）；
  东瘟疫之地 9 条 dx −4.2~−10.5、dy −5.2~−12.4，**每条都不一样，不是统一平移**；
  暴风城 1 条 +4.7 / +17.4。
  有图可标的稀有仍 329 / 362——**这一轮没有新增能标点的稀有**，因为卡的是贴图不是地图号。
- `spells.json`：498 条没变，18 条每级学习等级被 XR 新版补上/改掉、7 条等级数出现两种说法、
  4 条起学等级出现两种说法（两源分歧按红线两个都留）；出处里的版本号从快照读。
- `achievements.json`：211 条没变，只有出处 url 与核对日更新。

## 三、一条自我更正：上午说的"两份独立反推"不成立

`docs/VERIFY-world-pins-2026-10-19.md` 补二里我写了"两份独立反推对账"。实测：
**XR 的 `Data_MapLoc.lua`（251 条）与 DF 的 `Data_NPCLoc.lua`（274 条）共同的 251 条逐字相同、
0 条不同，DF 只多出 23 条**——同一条管线出来的东西，不是两处独立来源。

所以那张对账表证明的是"我们没接错"，不是"游戏确认了两遍"。真正跨作者的那一层是
**GI 行内 `ui`**（另一个作者、另一条管线，把地图号直接写在每条稀有那一行），
本轮按 npcId 精确对：**326 条与站内一致、0 冲突**。

这条口径已经写进 `docs/wow-infinite-sources.md` §二十并钉死：
这类"别人从客户端解出来的表"互证只用来确认我们没有抄错，**不能用来给任何一条升 L0**，
升档只认官方中文页或游戏内实测。

## 四、实现上改了三件事

1. **地图号顺位重排**（`merge-world.js`）：① GI 行内 `ui` → ② 站内那三层 → ③ XR 区域名对照只补空位。
   ①② 都有值却不一致时不悄悄取舍，记进 `meta.mapIdMismatch`。本轮 ③ 的补位数是 0，
   那层退成兜底与对账用（保留它是因为 GI 不是每条记录都会带 `ui`，旧快照就没有）。
2. **版本号不再手抄**：`extract-plugin-tables.py` 从插件自己的 `.toc` 读 `## Version:` 写进
   `meta.addonVersion`，`merge-spells.py` / `merge-achievements.py` / `merge-world.js` 都从快照读。
   原来 `0.4.29` / `0.37.1` 抄在四个地方，插件一升级，每条记录的出处就变成一句过期假话。
3. **门禁 `[6e]` 那两条数据侧断言重写**（25 条，比上一轮多 1 条）：改成钉"主源是 GI 行内 ui（≥300 只）、
   三份来源对账零冲突、有地图号 ≠ 许标点"。最后那条从"只看 XR 补的那 73 只"扩到**全部 362 条**，
   判据变成"这条稀有有地图号又有坐标时，`mapFile` 当且仅当本地真有那张图"。

## 五、DF 与 HandyNotes 这一版一条都不取

DF 的 LICENSE 写着「Copyright © 2026 圆圆 · 保留所有权利」。它确实有几张正好是我们缺的那一层
（副本入口坐标、副本内首领位置、区域→地图号），但**整表搬一家 All Rights Reserved 的结构化数据，
和从公开网页上取一个 NPC 的坐标不是一回事**——那是复制对方整理出来的汇编。
所以这一版只把清单与判断记在 §二十，一条不进数据基底。
职业攻略 / 战斗建议 / 分级 / 配装那几张本来就在红线上，直接不取。
要不要开这个口子列进**开放项 40**；最干净的走法是我们自己从客户端 DB2 出那份表。

## 六、还有哪里没验

- **那 24 条改动后的坐标对不对，没有任何独立依据**。我们只是从同一个源的旧值换成新值，旧值也可能是对的。
  赤脊山那 8 条 dx 完全一致（−5.0~−5.1、dy 全 0），能说的是"**作者做了一次整体平移**"这一件事实；
  但"平移后的值才对"仍然是推测。东瘟疫之地那 9 条每条位移都不一样，更像是逐条改的，
  也没法从我们这边判断依据是什么。
- **`pts=`（一只怪多个刷新点）与 `rs=`（刷新间隔 3600 秒）留在快照里没上页面**。
  刷新计时我们页面上写过"客户端里没有这类数据"，现在插件里有、但只有这一家说，
  按红线要等第二处（开服后官方或游戏内实测）才上，列进**开放项 41**。
- 没跑 `tools/audit-translations.py`：这一轮名称一条没变（变的只有坐标、学习等级与出处日期），
  逐字回查那条线查的是名字，所以没重跑。下一轮名字有变动时要补。
- 物品详情、副本、天赋、专业这些线**没重抓**（各自的抓取窗口与耗时不同），
  所以站内现在同时存在 0.4.32 的世界线数据与 10-11 至 10-16 的别线快照——这是既定漂移，见开放项 20。

## 七、全跑门禁

```bash
python3 -u tools/site-check.py --app
# 通过 873 / 873 —— 全部通过（rc=0）
```

比上一轮多 1 条（`[6e]` 从 24 → 25：那两条数据侧断言重写成三条）。
旧站 19 页那十几节一条没红——世界线与法术书、成就的成品都换了新版数据，
旧站读的是同一份基底，它的断言全是按数据现算的，所以跟着走而不是变红。
