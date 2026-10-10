# 数据维护与更新（2026-10-09 定）

这份文件回答三个问题：**数据从哪来、多久动一次、动完怎么确认没坏**。
配套的可执行入口是 `tools/refresh.sh`（把下面每条链路写死成脚本，顺序不会错）。

## 一、一条链，三层存放

```
官方中文页 ─┐                                    ┌─→ src/      旧站（当前发布口径）
            ├─→ 抓取 → src/data/upstream/ → 合并 → src/data/  ─┼─→ app/public/ → dist/  新站（Vue，迁移中）
解包资料站 ─┘        （原始转述，不进页面）    （唯一成品基底）└─→ for-mini/            小程序快照
```

**三层各自只有一个用途，别混：**

| 层 | 目录 | 规则 |
| --- | --- | --- |
| 原始转述 | `src/data/upstream/` | 抓取脚本的落点。**页面永远不读它**，改数据先改这里再合并，方便复跑与对比 |
| 成品基底 | `src/data/*.json` | **全线唯一真相**：网页两栈 + 小程序都读它，不存在第二份手抄表 |
| 构建副本 | `app/public/`、`for-mini/oss-preview/` | 由脚本从基底复制，git 忽略或可复现；**永远不手改** |

派生文件同理：`scale.json`（所有规模数字）、`search.json`（全站搜索索引）、`icons.json`（图标映射）、
`icon-gaps.json`（缺图登记）都由 `tools/build-data.js` / `build-icon-map.py` 现算，**手改会在下一次跑时被覆盖并被过期检查拦下**。

## 二、每类数据的源与刷新命令

| 板块 | 源 | 一条命令 | 备注 |
| --- | --- | --- | --- |
| 天赋树 | 两家解包站（fengshen / nieyi）双源 | `tools/refresh.sh talents` | 双源按坐标对齐，名字分歧两个都留 |
| 副本与掉落 | 解包站副本卡片（浏览器渲染） | `tools/refresh.sh dungeons` | 掉落只取"谁掉什么"，**不写百分比** |
| 世界线 | 解包站 `_shuju/<发布号>/*.json` | `tools/refresh.sh world` | 发布号每次从页面现读，别手抄 |
| 专业与配方 | 解包站专业页 | `tools/refresh.sh prof` | 野营那一页没有结构化数据，不编 |
| 客户端改动清单 | 解包站 `_shuju/…/changes.json` | `tools/refresh.sh changes` | **入库前就删掉前后对照句子**，只留名称与类别 |
| 传承（专长树 / 挑战 / 奖励） | 解包站 `_shuju/…/legacy.json` | `tools/refresh.sh legacy` | 同样**落盘前删句子**：每层效果说明、常见问题、领取说明一律不进仓库；未公开的槽位留空标"未公开" |
| 官方中文（技能四态 / 种族） | 国服官方公告页 | `tools/refresh.sh official` | 整句照录，名称不在句里就丢弃，不机翻 |
| 图标 | 暴雪官方 CDN（只允许这个域名） | `tools/refresh.sh icons` | 403 = 没有这张图，退回自绘块 |
| 原画（职业背景 / 载入图 / 小地图） | 第三方站转存 | `python3 tools/fetch-art.py --what all` | 独立目录 + `manifest.json`，整目录删掉即回退 |
| 副本排队元数据 | 解包站 `_shuju/<发布号>/dungeons.json`（35 条，**没有首领与掉落**） | `python3 tools/scrape-wclbox-shuju.py --group dungeons` | 已接进 `refresh.sh dungeons`：补阵营与所在区域；它的 `enter` 列对不上客户端表，**不采** |
| 客户端排队表 | `wago.tools/db2/GroupFinderActivity/csv?build=<客户端版本>` | `python3 tools/fetch-db2-groupfinder.py` | 英文原名、等级区间、一次几人。非暴雪域名 → 英文名只算 L1；构建号从 `_shuju/…/meta.json` 现读 |
| 英文原名 / ID / 图标名对账 | wowhead Forever 区（**只有英文**，`/cn/forever` 是 404） | `python3 tools/audit-wowhead.py --write` | 对账不是门禁：天赋线已跑通（461/473 对上、图标零真分歧）；只取标识符与计数，中文名一律不由它提供 |
| 只跑检查不碰网络 | — | `tools/refresh.sh check` | 提交前必跑 |
| **先看还缺什么** | 现成的数据文件，不碰网络 | `tools/refresh.sh status` | 体检报告：缺口分「我们能补 / 要人工进游戏核 / 只能等外部」，每条附下一步命令与上游新鲜度。**它不是门禁，永远退出 0** |

## 三、什么时候动

| 触发 | 动作 | 时限 |
| --- | --- | --- |
| **每次开工第一步** | `tools/refresh.sh status`：看缺口与哪些上游超过 14 天没重抓 | 每次 |
| 解包站发了新构建包 | 对应板块 `refresh.sh <板块>` | 当天 |
| 官方中文发了新公告（尤其 5 个还没有中文名的职业） | `refresh.sh official` + 译名体检 | 当天 |
| 每周固定 | `tools/audit-assets.py`（素材缺口）+ `tools/refresh.sh check` | 周一 |
| **2026-11-05 正式服上线后 48 小时内** | 整批重核：全部板块重跑 + 覆盖率重算 + 溯源页写清变化 | 已在 `method.json` 里对外承诺 |
| 每次改界面或数据要提交 | `tools/refresh.sh check`，界面改动还要补截图 | 提交前 |

## 四、四道门禁各拦什么

| 门禁 | 命令 | 拦的事故 |
| --- | --- | --- |
| 数据校验 | `node tools/build-data.js` | 标了已核实却没有官方来源、掉落出现百分比、图标指向外链、id 重复、来源类型与域名不匹配、**正文里出现维护者措辞**（词表 `tools/copy-banned.json`）、页面数字与 `scale.json` 漂移、上线日期三处不一致 |
| 译名逐字回查 | `python3 tools/audit-translations.py --strict` | 我们抄错了官方原句：**声称 L0/L1 的条目**拿回它自己声明的那个 URL 里逐字找不到 → 退出码非 0。L2/L3 的未命中与"去掉排版空格才命中"只出警告（后者是官方页用强调标签把词从中间拆开的转换产物，squeeze 只删汉字之间的空白，不可能把错词拼成对词）；但并写形式指代的词（官方写「冰霜与火焰陷阱」）必须逐条走 `src/data/audit-exceptions.json` 留人工判定，不能靠降级蒙过去 |
| 界面回归 | `python3 tools/site-check.py`（加 `--app` 跑新站） | 页面渲染坏、点不动、375px 点击目标偏小、**渲染后的文字里出现维护者措辞**、搜索跳过去没筛好 |
| 两栈对拍 | `python3 tools/app-parity.py --strict` | 迁一页时新旧两版内容悄悄不一样（结构 / 类名 / 正文 / 链接 / 图片） |

**对账（不是门禁，不拦提交）**：`python3 tools/audit-wowhead.py --write` → `docs/DATA-WOWHEAD-<日期>.md`。
拿 wowhead 的无限服天赋表对**条目数、英文原名、法术 ID、改动状态、图标文件名**——
它对不了任何中文名（Forever 区只有英文），也不产生"谁对"的结论，只给"另一家怎么说"这一层。
要真浏览器（curl 403），所以不进门禁；季度或大改天赋线之后跑一次即可。

小程序导出 `node tools/export-mini.js` 额外拦一条：产物必须可复现（重跑后 `git status` 干净）且不超主包预算。

> **2026-10-10 修掉一个让整条产线跑不完的门禁**：`audit-translations.py --strict` 原来把
> "排版空格才命中"（45 条）和"L2/L3 未命中"（2 条）也算失败，而这两类按定义就不是抄错——
> 于是 `refresh.sh` 的 `gate()` 在 `set -e` 下**每次都在第三步退出，site-check 从来没被跑到**，
> 九个刷新场景全都在第一步就断掉。当时没人发现是因为大家是手工分步跑脚本的。
> 现在卡口只拦真正会骗人的两类（L0/L1 未命中、结构性问题），其余降级成带计数的警告，
> `bash tools/refresh.sh check` 第一次跑到底（464/464）。教训：**门禁必须能绿**，
> 一条永远红的门禁等于没有门禁，还会连带把后面的检查一起废掉。

> **重跑必须幂等**：文案只改在产物里，下次刷新就没了。同日实测两起——
> ① `merge-dungeons.js` 写死的两句玩家可见文案带着「上游标了：」，重跑副本线把已改好的文案
> 盖回违规版本，`build-data.js` 当场报错（已修：生成器里现在放的是不触禁词的说法）；
> ② `fetch-icons.js` 整份重写素材清单，跑一次天赋线就把 `icons/manifest.json`
> 从「2012 张 + 8 批来源」缩成「359 张」（已修：改成只替换自己那一批，总数按目录实数算）。
> 自查方法：跑完一个场景后 `git status` 里**不该出现与本次抓取无关的改动**；
> 出现了就是生成器与产物在各自漂移——改生成器，别只改产物。

## 五、加一个新板块的固定七步

1. **采编**：确认能取哪些字段（只取事实性标识符），写进 `wow-infinite-sources.md`；取不到就写"等"。
2. 抓取脚本 → 落 `src/data/upstream/`，**入库前先删描述文案**。
3. 合并脚本 → 出 `src/data/<板块>.json`，每条带 `provenance[{type,url,note,checkedAt,quote}]`。
4. `build-data.js` 加这一块的校验（缺名称、id 重复、坐标对不上、禁词、百分比）。
5. 页面渲染 + 进 `search.json` 索引（在 `build-data.js` 的 `SK` 里加一类）+ 深链预填。
6. `site-check.py` 加断言、拍 1440 与 375 截图；`docs/UI.md` 加一节规格。
7. 人工写一条 `src/data/releases.json`（玩家向的更新说明）。**提交号必须指向已经存在的提交**，所以顺序是：先提功能提交 → 再补一条 releases 指向它的哈希（第二次提交很小）。`build-data.js` 会回仓库核对哈希存不存在，写个假哈希直接构建失败。

## 六、发布动作（必须人工确认，脚本不代做）

`tools/refresh.sh publish` 只负责把该跑的全跑一遍并报"全绿"。**真正的发布要人再做三件事**：

1. 网页：把 `src/`（当前发布口径）同步到托管处；新站 `app/dist/` 在迁移期不接管入口。
2. 小程序：先跑 `export-mini.js`，再在开发者工具里上传体验版手测点击类动作（本机 automator 点不动，见根 `AGENTS.md` 第 4 条）。
3. 提交与推送：只提自己改的文件，`git fetch` 后再推。

## 七、缺口只有三种归宿，不许有第四种

`tools/refresh.sh status` 就是按这三档把缺口列出来的（能补 / 要人工核 / 等外部），
每条带数量与下一步命令——想知道"这次该动哪一块"，先跑它，别靠记忆。

- **等外部**：官方没发中文稿、CDN 没有那个文件、上游没切图 → 界面上写明"待实测 / 未公布"，登记在 `icon-gaps.json` 与 `docs/ASSET-GAPS-*.md`。
- **退回自绘**：图标与原图取不到 → 自绘块，绝不热链别人的图。
- **决定不做**：攻略、百分比、强度排行、UGC、新闻流 → 写进 `docs/PLAN-open-items.md` 第三节，页面上"刻意不做的"那一栏也摆着。

**没有"先随便填个数占位"这一档。**

## 八、出事了怎么办

| 现象 | 大概率原因 | 处理 |
| --- | --- | --- |
| 抓取脚本报"拿不到发布号" | 解包站改版 | 打开站点页面看 `_shuju/<发布号>/` 还在不在，改 `scrape-wclbox-shuju.py` 的 `BUILD_RE` |
| 校验说"icon-gaps 过期" | 数据改了没重跑图标映射 | `python3 tools/build-icon-map.py` 后再跑一次 `build-data.js` |
| 图标全是自绘块 | CDN 返回 403（= 没这张图，不是网络问题） | 换区域换尺寸也没用，登记进缺口清单 |
| 对拍报差异 | 只改了一栈 | 两栈同一处一起改，或把有意差异登记进 `app-parity.py` 的 `INTENTIONAL` |
| 页面上冒出"上游 / mapId / 本轮" | 新写的句子没过禁词表 | 按 `tools/copy-banned.json` 的 `why` 改成人话，别往表里加豁免 |
| 搜索结果跳过去没筛好 | 那一页没接 `?q=` | 每加一个板块入口，就要在目标页接住词（`site-check.py` 第 17 节会红） |
