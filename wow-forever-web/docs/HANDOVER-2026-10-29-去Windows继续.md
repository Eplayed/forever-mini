# 交接 · 去 Windows 那台继续做 · 2026-10-29

本轮角色：wow-dev ｜任务：把 Mac 这一侧的状态收口，写成一份能拿到另一台机器上独立接着做的说明 ｜产出：本文件 ｜交接给：站主 + Windows 侧的 AI。

**这份文档是自足的**：不需要读我们的聊天记录，按里面的路径和命令就能接手。所有数字都是今天现测的，不是抄历史快照。

---

## 一、这是个什么东西

《魔兽世界：无限》(World of Warcraft: **Forever**，英文名一律用 Forever) 的中文资料站。

| 位置 | 是什么 |
| --- | --- |
| Mac 仓库 | `/Users/zhangyajun/Documents/project/wow-forever` |
| 唯一产品 | `wow-forever-web/app/`（Vue 3 + Vite，hash 路由，22 条路由，**没有后端**） |
| 唯一数据基底 | `wow-forever-web/app/data/*.json`（小程序也读这一份，不建第二份） |
| 跨机信箱 | Windows 那台的 `C:\GAME\World of Warcraft\ziliao-export\`，Mac 侧只读挂在 `/tmp/wow-ro/ziliao-export/` |
| Windows 从 Mac 取文件 | `\\MACBOOKPRO-F157\project\wow-forever\...`（站主实测按主机名直读是通的，Z: 盘符显示 Disconnected 不影响） |
| 线上 | <https://eplayed.github.io/wuxian-atlas/>（GitHub Pages，**当前包 `wow-forever-web-20261028-174730-4e216292`**，10-28 17:47 发） |
| 源码仓 | `Eplayed/forever-mini`，走 `ssh://git@ssh.github.com:443/...`（这台机器到 `github.com` 的 HTTPS 经常连不上） |

**小程序线**在 `for-mini/`，是另一条产品，移动端门禁一条不降——**"手机网页版不做"这条只管网页，不管小程序**。

---

## 二、规则在哪（接手前必读，别照这份文档的转述干活）

| 要什么 | 读哪个文件 |
| --- | --- |
| 六个角色怎么分工、一轮只一个主角色 | 仓库根 `AGENTS.md` |
| 全部红线（分级 L0–L3、素材本地留存、掉落不写百分比、缺数据写"待实测"、禁机翻与编造、第三方站只取事实字段…） | 根 `AGENTS.md` 第五节 |
| 站主按日期拍板的决定**原文** | `PROJECT_DECISIONS.md`（**优先于任何转述**） |
| 资料站工程约定（目录、命令、硬规矩） | `wow-forever-web/AGENTS.md` |
| 验证基线（哪类改动跑哪条门禁） | `PROJECT_GATES.md` |
| 当前接手入口 | `NOW.md` |
| 完整交接台账（每轮追加） | `ROLES.md` 末尾 |

**三条最容易踩的，先抄在这里**（原文以文件为准）：

1. **素材一律本地留存、禁止热链**；客户端原画类要落独立目录 + `manifest.json` 记来源与抓取日期 + 保留"整目录删除即回退"。
2. **两源分歧两个都留**并标注；缺数据显示"待实测"，**不许编**。
3. **UI 改动必须有渲染证据**（`docs/screenshots/`），构建通过不算完成。

---

## 三、Mac 侧门禁怎么跑（Windows 上一般不跑这些，改代码才用）

```bash
cd /Users/zhangyajun/Documents/project/wow-forever/wow-forever-web
node tools/build-data.js            # 改数据必跑：校验 + 覆盖率 + 禁词，非 0 即未完成
cd app && npm run build && npx vitest run   # 构建 + 组件单测（build 会先把 data/img 同步进 public）
python3 tools/site-check.py         # 唯一界面门槛：自己起静态服务打 app/dist，跑前必须已 npm run build
python3 tools/site-check.py --only app,world_pins   # 快速探针（整站那一遍很慢，见第六节那条已知问题）
python3 tools/app-assets.py --check # public 与源目录是否一致
python3 tools/release-package.py    # 打发布包（只在干净工作树打，见下）
python3 tools/pkg-verify.py         # 包验收；--live <url> 是对真远端跑
python3 tools/deploy-gh-pages.py --repo wuxian-atlas --push   # 发布（要站主点头才能跑）
```

**发布链的三条硬规矩**（今天踩过）：① 打包必须在**独立干净工作树**（`git worktree add --detach`）里做，包里只能有已提交内容；② 白名单里 `.glb` 只放 `app/img/models/manifest.json` **顶层** `origin == "self-generated"` 的那几个；③ 脏标记要在脚本入口先记一次，否则构建链自己重写 `scale.json` 会让每次都判"源码没提交"。

---

## 四、地图这一层：现在到底有什么、缺什么（**这是交接的主线**）

### 4.1 OpenMap 那个插件给的是什么（已核，别再猜）

OpenMap 0.7.5-CN（上游 `v0.7.5-beta`）的 `Data/DungeonMaps.lua` 存的是**每层 12 个客户端文件号**，它运行时 `SetTexture(数字)` 让**客户端自己出图**（证据：`Map/Dungeons.lua:229`、`:293`）。它自带的 283 MB `Media/Textures` 是它画世界地图用的裁剪件/色场/蒙版，**NOTICE 自述不受 MIT 覆盖** → **我们一张都不取它的图**，只取那张表（MIT 数据表，要署名）。

### 4.2 已经到手并复核合格的：756 片逐层副本图

- 包：`ziliao-export/maps-floor-2026-10-29/`（+ 同名 `.zip` 92,834,618 B，sha256 `5d225d01cc5be13d5c83a51c8e906fd96e755dd5ab22f310e3965b6f95da3a70`）
- 内容：`tiles/` 756 张 256×256、`floors/` 63 张 1024×768、`tiles.csv`、`RESULT.json`、`logs/`、`probe-blp/`、`MANIFEST.json`(846 条，不含自身)、`PACKAGE.json`
- **Mac 侧独立复核全过**：123 条哈希重算不一致 0；63 张内容框实测**全部 (0,0)→(1002,668)、比例 1.5000**（和区域图同一参照物，坐标能直接落）；排序坑三道独立证明（逐键对表 / 客户端路径尾号==tile 号 756/756 / 肉眼开影牙城堡）
- 细节与判据：`wow-forever-web/docs/VERIFY-副本逐层图756片回件复核-2026-10-29.md`
- 接驳键产物：`wow-forever-web/app/data/upstream/openmap-floors.json`（25 座里 **19 座**按名字接到本站条目，含"我们拆翼/它分层"的四组）

### 4.3 还缺的（按能不能立刻做排）

| # | 缺什么 | 谁能做 | 判据/注意 |
| --- | --- | --- | --- |
| 1 | **DF 层号 ↔ OpenMap 层号是否同一套，还没证** | Mac 可推，但**结论只能标"待核"** | 方法是"坐标落点反推"：把旧点画到候选层上，看哪种对应让点落在房间里而非空白羊皮纸。**没证之前不许拿它画点**——这就是 #108 犯的错 |
| 2 | 63 张层图**还没入素材库** | Mac | 转 webp 控体积、只入接得上的那些；逐张 `manifest.json` 记 build + **语言 zhCN** + fdid + sha256。**层图顶部横幅烘的是简体中文本名**（影牙城堡那张我亲眼看到），换语言客户端导出字会变 → 语言必须记 |
| 3 | 暴风城监狱差一个复数 s（我们 `Stormwind Stockades` vs 表里 `Stormwind Stockade`） | Mac | 补一条别名即可 |
| 4 | 5 座团本（祖尔格拉布 309 / 熔火之心 409 / 黑翼之巢 469 / 安其拉废墟 509 / 安其拉神殿 531）**有图无数据** | Mac（要采）或明确不做 | 我们 `raids` 只有 3 条且不含这些，画不出点 |
| 5 | **区域图那 10 张游戏内实拍**（A 路，站主 10-28 已选） | **只能 Windows**（要进游戏） | 任务书 `wow-forever-web/docs/DATA-区域图-Windows实拍任务书-2026-10-28.md`；要 1424/1430/1440/1449/1451/1453/1454/1457/2548/2652 十张 + **1436 西部荒野作对照**；截图时临时关掉会在地图上画东西的四个插件（只写 WTF 设置层）；给画面区像素框；不许缩放加水印；游戏里没图就写 `no_ingame_map` |
| 6 | 无限新增那 9 座本**客户端根本没有官方层图** | 只能示意图/待补 | 包里 25 座全是经典本+团本，不含它们 |

### 4.4 探针已经回答的一个问题

`OpenMap/Media/Textures/MapZones/` 那两片（`10_10`、`10_11`）**烘着地名文字**（拉丁字母英文名牌 + 跨边两位数字，对方给了裁好的证据图）。→ **"从客户端瓦片拼一张干净区域图"这条路判死**，区域图只能走 A 路实拍。

---

## 五、Windows 那台现在能立刻做的三件事

1. **区域图 A 路实拍**（第四节第 5 行）——这是唯一卡"进游戏"的事，本机做不了。
2. **round9 全职业 76 份整人 GLB 导出**——那台 10-29 凌晨已在跑，`ziliao-export/round9-all-bis-3d/` 里 `INPUT_READY` 已过（76 jobs、38 套×2 阵营、字节与 SHA 全对）。**交件按老规矩**：包内 `MANIFEST.json`（最后生成、不含自身）+ `RESULT.json` + 完整日志，包外 `PACKAGE.json`/`.PACKAGE.txt`，状态写 `*_PENDING_MAC_REVIEW -- NOT SITE_DONE`。
3. **清一下 `maps-floor-2026-10-29/blp/`**——756 张原始 `.blp` 没进 ZIP（对的），但留在共享目录里占地方；Mac 侧只用 PNG。

### 给 Windows 侧的导出纪律（今天用血换的，别再犯）

- **只读客户端**：不改、不新增、不删游戏目录里任何东西；所有写入只在自己的导出目录。**共享的登录口令不要写进任何文件**（仓库/脚本/文档/台账都不行）。
- **`tiles` 数组下标就是拼图位置，绝不许按数字排序**（影牙城堡第一层第 1 位 448226、第 2–9 位 448230…448237、**第 10–12 位才是 448227/28/29**）。排完序拼出来的图是错的且肉眼难查。
- **不许裁空白边、不许缩放、不许加水印/文字、不许改色彩配置**——留白是几何的一部分，坐标要落上去。
- **`wowfexport get … id` 那条 CascLib 路不可靠**：今天实测它本地索引只认 440/756、316 报缺、**4 个不同 fdid 解成同一份字节**。改走 wow.export 自己的 CASC reader（那台用的 `app-e10` 那份）。
- **导出过程不许向任何远端请求文件**：未打补丁的 CascLib 会自己向 `level3.blizzard.com` 发 HTTP GET 兜底（今天已披露一次）。日志里出现 HTTP 行 = 整包作废。
- **拿不到照实写 `NOTFOUND`**，宁可写满也不许拿邻近号凑——Mac 侧逐条回读 sha256 与字节，对不上会退回重做。

---

## 六、Mac 侧还挂着的账（接手人别当成已完成）

| 事项 | 状态 |
| --- | --- |
| #108 首领点位参照物错位（7 座跨层本压一张图） | **待**，阻塞在第四节第 1、2 行 |
| #113 层图接驳键与坐标系重标定 | 进行中，接驳键已出（19/25），剩层号语义 + 入库 |
| #112 门禁那条"导航当前项小药丸"断言偶发红 | **待单开一修**。同一份产物 13 次里红 3 次；红出来是 `.on` 类在元素上但底色透明、字色落回默认灰。试过"等连续两次读数一致再量"没治好，已撤回不留半修 |
| 整站 `site-check.py` 跑不完 | 卡在 `site-check.py:499` 那张成就页截图，本机一次视口截图要 24.5–30 秒（软件光栅）。两种放宽都试过都失败已撤回。**要动的是"这张图非拍不可吗、能不能只拍视口一块"**，不是再抬超时 |
| 剃刀高地英文名 `The Razor Krendor` | **已判是错的**：客户端 157 MB listfile 里 `krendor` 出现 **0 次**，那座本 WMO 路径是 `World/WMO/Dungeon/KL_Razorfen/RazorfenDowns.wmo`；我们同一条目里 `nameEnClient` 就是 `Razorfen Downs`。改法走 wow-data（两源分歧要留档，别直接覆盖） |
| 小程序侧 | 10-28 那批数据改动**没重导**（`export-mini.js` 不读 professions 的 nodes 层） |
| 备案 | 管局审核中，预估 11-11、最长 11-25 → **会跨过 11-05 开服**，开服窗口只能用境外 Pages |

---

## 七、这次交接时线上/本地的差异

- **线上**（`174730-4e216292`）有：宠物页、专业页钓鱼分段表、21 件物品出处改名、12 条法术值、导航「宠物」格 + 首页宠物卡、首页「最新动态」提到第一屏。
- **线上还没有、本地已提交**：S3 点位分级与图例筛选、OpenMap 层图接驳键。要在网页上看到 S3，得再发一包（**发布要站主点头**）。

状态：**已定**（本文件所列事实均为今日现测，路径与哈希可回查）／**待站主**（区域图实拍什么时候转给 Windows、要不要为 S3 再发一包）／**阻塞**（#108 等层号语义，非本轮能解）。
