# 验证记录 · 副本线改成两页式（2026-10-13）

本轮角色：wow-dev ｜任务：用户点名参考 `wowforever.wclbox.com/fuben`（副本列表）与
`/fuben/ragefire-chasm`（副本详情），把我们的副本线做成"列表挑一座 + 每座本一页" ｜
产出：`src/dungeon.html`（新页）、`src/js/app.js`、`src/css/app.css`、
`tools/{build-data.js,site-check.py}`、`src/data/{search,scale}.json`、
`app/src/lib/nav.js`、`docs/UI.md` 3.37 ｜交接给：用户验收

## 〇、先说清两件"没照着做"的事

1. **用户给的 URL 是 `world.html`，参考的两页是副本列表与副本详情。** 这两件事不一样：
   `world.html` 是"区域、稀有与书"。按参考页判断要改的是**副本线**，
   所以动的是 `dungeons.html` + 新增 `dungeon.html`，`world.html` 一行没碰。
   如果他其实想改的是世界页，这一轮的改动仍然独立成立（副本页本来就该有详情页），
   世界页另开一轮。
2. **参考站详情页的四块内容我们没做**：`任务 / 任务物品 / 任务起始地点 / 任务经验`。
   原因是数据里没有，不是漏了——`src/data/upstream/wclbox-dungeons.json` 的 35 条记录
   只有 `slug / nameCn / isNew / levelRange / bosses / drops`，没有任何任务与经验字段。
   按红线"缺数据不许编、不拿别人的攻略正文填"，这四块整块不做。
   要做先走一轮 wow-data 采集（下表列了要补什么）。
   参考站掉落的百分比（`<0.1%`、`40%`）也一律不搬——本站红线是掉落不写概率。

## 一、这一页一页对得上，四块对不上（盘点）

| 参考站详情页有的 | 我们数据里有没有 | 这一轮怎么落 |
| --- | --- | --- |
| 载入图当页首底图 | 36/38 有（`barrow-deeps`、`hyjal-summit` 缺） | 有就上，缺的留深色底不放假图 |
| 等级区间、阵营、所在区域 | 有（`levelRange` / `faction` / `zoneCn`） | 四格读数 + 去世界页找这一片的链接 |
| 一次几人 | 有（`partySize`，31 座有数） | 四格里给，客户端另有一条人数的走分歧行 |
| 首领头像 + 名单 | 有（228 个首领里 146 个有本地转存的脸） | 一个首领一段，没脸的直说`没有这张头像` |
| 按首领分组的掉落 | 有（`drops[].bossId`） | 物品名按品质着色，**不写概率** |
| 进本之前四格表 | 有 | `.four` 四格 |
| 任务 / 任务物品 / 任务起始地点 / 任务经验 | **没有** | 不做（见上） |
| 路线 | 数据里 `route` 38 座全是空数组 | 直说`待实测`，不抄别人的路线 |

## 二、跑了什么，看到什么

| 命令 | 结果 |
| --- | --- |
| `node tools/build-data.js` | 校验通过；搜索索引 4350 条 / 19 类，`dun`/`boss` 两类改指 `dungeon.html` |
| `python3 tools/site-check.py --only dungeon_detail`（新节探针） | **50 / 50** |
| `python3 tools/site-check.py --only dungeon_data,dungeon_banner,search` | **61 / 61**（旧判据一条没改口径） |
| `python3 tools/site-check.py --app`（全跑，收尾又复跑一次） | **618 / 618 全绿**（上一轮 556，+50 是这一轮新增的 `dungeon_detail` 一节，+12 是 `test_pages` / 设计基线 / 禁词 / 对比度 / 锚点那几组按 `len(PAGES)` 自动多覆盖了一页） |
| `python3 tools/app-parity.py --strict` | **全部组合无差异**（第一次跑出 home 一组红了 5 行：`app/dist` 是上一轮提完「本站更新」条目之前构建的，新站吃的是构建时打包的 JSON。`npm run build` 重构建后归零——**这不是这一轮改坏的，是构建产物过期**，serve.sh 第 52 行本来就提示过） |
| `npx vitest run` | **69 / 69**（`SiteSearch` 那条 "injection router not found" 是测试壳没装路由，历史噪声，不是这一轮引入） |

改前 / 改后都实拍过（桌面 1440 + 375px 移动端），入库在
`docs/screenshots/check-2026-10-13/`：`dungeons-list-2026-10-13.png`、
`dungeon-hall-of-thanes.png`、`dungeon-ragefire-chasm.png`、`dungeon-onyxias-lair.png`。

## 三、界面做了什么（要点三条）

1. **列表页卡面收成"挑一座"**：原来每张卡上压着五行红字分歧与"还不能排队"的说明，
   35 张卡看着像数据变动明细。现在卡面只剩原画横幅（加高到 118px）、
   `N 个首领 / N 件掉落 / 一次 N 人`、速览按钮，整卡可点进详情页。
   **分歧是收进速览抽屉与详情页，不是删掉**——`test_dungeon_data` 那四条按数据逐条数
   数量的断言一条都没改，新增的反向断言是"卡面 `.dcard2 > .conf` 必须为 0"。
2. **两个筛选控件**：`我的等级`（按等级区间真筛，不是 `display:none`）+
   全部 / 无限新增 / 经典旧世。断言分别钉住"填 18 / 25 / 44 / 60 级各自剩几座"、
   "两个筛叠加"、"清空等级不动来源筛"。
3. **详情页不占导航格子但亮着列表页那一格**：`NAV_OF = { dungeon: 'dungeons' }`，
   `site-check.py` 里同名单 `DETAIL_PARENT` 放行"每页都能从导航走到"那条。

## 四、踩到并修掉的三个坑（都会复发）

1. **375px 整页横向溢出 45px**：`.hero` 是网格，网格子项默认最小宽度是 `min-content`，
   而下拉框的固有宽度取决于**最长的那个 option**（"提瑞斯法林地，洛丹伦废墟（15-22 级）"）。
   点击目标断言查不出来（它只量元素尺寸，不看层叠与溢出），**必须实拍**。
   修法：`.dunhero>*{min-width:0}`。
2. **整卡链接盖住速览按钮**：`.dstretch{position:absolute;inset:0;z-index:1}`
   要配 `.dcard2>button,.dcard2>.drawer{position:relative;z-index:2}`，否则抽屉点不开。
3. **`.cta-line` 压在载入图上像断框**：它带 `clip-path` 斜切，边框被切掉一半；
   深色页首上改用 `.cta`。

另外两处是"断言写得不对"而不是页面不对：① `清空等级` 那条我按"回到 35 座"判，
实际来源筛还停在"无限新增"，两个控件互不越界才是预期，改成钉 9 座 + 再切回全部钉 35 座；
② 上一座 / 下一座那条按"必须两个链接"判，第一座本来就没有上一座，
改成"链出去的本号都得在数据里 + 到档那侧必须写明"。

**实拍之后才发现的一处措辞**：没有首领名单的那几座（三座团本 + 六座新本）卡面上写的是
`待补 个首领`——这是上一版留下的 `((bosses.length || '待补') + ' 个首领')` 拼出来的病句，
断言查数量查不出语病。改成 `首领待补`，详情页页首同一处一起改。
改完定向复跑 `--only dungeon_data,dungeon_detail` → **75 / 75**。

## 五、没验到的 / 要人眼看的

1. **38 座详情页只逐条核过 3 座**（`hall-of-thanes` 有分歧、`ragefire-chasm` 有掉落、
   `onyxias-lair` 没有首领名单），其余 35 座走的是同一渲染分支，
   但**没有逐座实拍**。要抽查的话建议再看这两座：`stratholme-service-gate`（同名的两个入口）、
   `barrow-deeps`（没有载入图、也没有中文定名）。
2. **筛选在真机上顺不顺手**：等级输入框是 `<input type=number>`，手机上会弹数字键盘，
   但我用的是无头浏览器，**没有真手点过**。
3. **`&b=<首领>` 深链的滚动位置**：断言只验"那个块在 DOM 里、URL 带首领号"，
   滚到屏幕哪个位置没量（`scrollIntoView({block:'center'})`，可能被吸顶头部压住）。
4. **新站没迁这一页**：`dungeon.html` 只在旧站，新站的搜索结果与导航入口按 `MIGRATED`
   表自动链回旧站文件，实测 `:8821/dungeon.html` 与 `:8821/dungeons.html` 都返回 200。
   要不要把副本线也迁进 Vue，等这一版界面被认可后再决定。
5. **视觉基线没重冻**：`visual-check.py` 的基线还冻在 `e2bf063`，
   这次 dungeons.html 版式变了，重冻要等用户看过实拍再一起处理（前两批也欠着）。

---

## 六、同日第二批：用户实拍后撤路线 + 等级区间定稿（追加）

用户三条：路线暂时不要；`等级区间两说…` 按 `wclbox/fuben` 定下来；问 wowhead 有没有副本数据、
我们现在是不是抓的 wowhead。第三条的答案单独成文：`docs/DATA-WOWHEAD-DUNGEONS-2026-10-13.md`
（一句话：**不是抓 wowhead**，副本线一条数据都不来自它）。

**跑了什么**

| 命令 | 结果 |
| --- | --- |
| `python3 tools/scrape-wclbox-dom.py --what cards` | 35 张卡与 10-11 那份快照**逐字段 0 处变化**，`scrapedAt` 更新到 2026-10-13 |
| `node tools/merge-dungeons.js`（连跑三次验幂等） | 等级区间定稿：改写 6 座 + 用客户端数补空值 1 座；第二次与第三次 md5 一致 |
| `node tools/build-data.js` | 校验通过；搜索索引里副本词条副标题跟着变成定稿后的区间（`无限新增 · 13-20` 等） |
| `python3 tools/site-check.py --only dungeon_data,dungeon_detail,dungeon_banner` | **87 / 87** |
| `python3 tools/site-check.py --app`（全跑，收尾） | **623 / 618 全绿**（+5 条：区间反向钉、留档核对、卡面区间逐座等于数据、路线反向钉、四格与区间那条） |
| `python3 tools/app-parity.py --strict` | **全部组合无差异** |
| `npx vitest run` | **69 / 69** |

**改了哪六座**（左边是定稿前=官方公告，右边是定稿后=参考站卡片=客户端排队表）：
领主大厅 13-18→13-20、洛丹伦废墟 15-20→15-22、挖掘场：湿地 26-31→26-33、
达拉然城 28-33→28-35、哀嚎洞穴 17-24→15-24、影牙城堡 22-30→20-30。
另补一座空值：奥妮希亚的巢穴 → 60-60（取自客户端排队表，参考站那 35 张卡里没有团本）。

**两个坑（都会复发，已写进 UI.md 3.38）**

1. `merge-dungeons.js` 的 `build()` 每轮重建条目对象，**新字段不带就活不过第二轮**——
   第一次重跑 `levelRangeOfficial` 有值，第二次整个键被洗掉，而界面上已经只显示一个数，
   等于"留档"悄悄没了。修法：`build()` 里显式 `levelRangeOfficial: (mine && mine.levelRangeOfficial) || null`。
2. **键在不在比值是什么更容易破幂等**：`levelRangeAlt` 定稿后一支写 `null`、另一支整个键消失，
   内容一样但字节不一样，重跑 md5 就对不上。补一次收尾归一化才稳。

**规则跟着改了**：`wow-forever-web/AGENTS.md` 第 3a 条 ① 加了这条例外，并写明
"人数、英文原名、译名这三类分歧照旧一条不许撤"。不改规则下一轮会被自家规则逼着把红字加回来。

**一条必须让站主知道的反证**（写在 wowhead 盘点第五节）：支持 13-18 的还有**国服官方公告 +
wowhead 攻略正文**两个来源，wowhead 数据库里的等级区间字段是空的（全 0）。
所以这次定稿是"客户端实际排队值"对"官方宣传值"的取舍，不是谁证据多。
两个数都在数据里，要换回去只改 `merge-dungeons.js` 定稿那一段。

**没验到的**：wowhead 那批字段（任务经验 1,050 / 1,350 / 1,450、掉落概率 31.92%、
`minlevel` 全 0）是子代理在**本机已登录的真 Chrome 会话**里看到的；
我用无头 Chrome 复现时被 CloudFront 直接 403 挡回（拿到 512 字节的报错页），
**没能二次复现**。真要拿这些数据之前，得再进那个会话现读现核一遍。

---

## 七、第三批：详情页加「本里的任务」（2026-10-13，站主定 wclbox 为准）

站主对上一轮那两个问题的回答：**wclbox 为准，wclbox 没有的按 wowhead 来。**

**跑了什么**

| 命令 | 结果 |
| --- | --- |
| `python3 tools/scrape-wclbox-quests.py` | 35 座全抓到：任务 407 / 任务物品 377 / 起始地点 316（原始快照） |
| `python3 tools/merge-dungeon-quests.py` | 396 条任务；经验值退到 wowhead 11 条、两源不一致留档 2 条、补 wowhead 独有 1 条、去重合并 12 条、物品开启 50 条 |
| `node tools/build-data.js` | 校验通过；`scale` 多两项（dungeonQuests 396 / 28 座有记录） |
| `python3 tools/site-check.py --only dungeon_detail,dungeon_data` | **95 / 95** |
| 全跑 `python3 tools/site-check.py --app` | **638 / 638 全绿**（上一轮 623，+15 条是任务这一节的判据） |
| `python3 tools/app-parity.py --strict` | **全部组合无差异** |
| `npx vitest run` | **69 / 69** |
| 加完「本站更新」后定向复跑 `--only updates_rank,pages,copy,player_facing,design_system` | **127 / 127** |

**页面上长什么样**：怒焰裂谷 6 条任务，其中「试探敌人」「寻找背包」两行底下各带一句红字
`经验值两说：本站取「850」，另一份资料写「1050」，两个都留着`；领主大厅 4 条的经验值
全部来自另一份资料，每条数字后面标`只有单一来源`；洛丹伦废墟末尾多一条`憎恶生物`，
标`这一条只有另一份资料有`，另有一条「无尽的折磨」标`同一任务 3 个版本`。

**没验到的 / 要人眼看的**

1. **35 座只逐条核过 5 座**（怒焰 / 领主大厅 / 洛丹伦 / 诺莫瑞根 / 黑喉要塞空态），
   其余 30 座走同一渲染分支但没逐座看。
2. **`variants` 那个口径是我定的**：wclbox 把同名任务列 4 行、wowhead 给的是 4 个不同任务号
   （97288 / 97289 / 97291 / 97292），我按"同一任务的多个版本"合并显示。
   **它们到底是 4 个版本还是 4 条不同任务，没实测过**——要人进游戏看一眼才敢说。
3. **任务经验值合计（怒焰 6,925）是该站自己给的汇总数**，本站只照抄没自己加总核对过。
4. 新站没迁这一页，`dungeon-quests.json` 目前只有旧站副本详情页在读。
