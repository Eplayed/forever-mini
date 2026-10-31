# 交接 · 换到 Windows 那台继续做 · 2026-10-30（10-31 增补）

本轮角色：wow-dev ｜任务：把 Mac 这一侧收口，写成能在另一台机器上独立接着做的说明 ｜产出：本文件 ｜交接给：站主 + Windows 侧的 AI。

**这份文档是自足的**：不读我们的聊天记录，按里面的路径和命令就能接手。所有数字都带"哪天现测的"——第一至八节是 2026-10-30 现测，**第九节是 2026-10-31 换机前最后一次现测**，两层的数字不一致时以第九节为准（不是抄历史快照）。
它覆盖 `HANDOVER-2026-10-29-去Windows继续.md` 的"当前状态"部分；那份留作昨天的事实快照，**第五节那张地图账表仍然有效**，本文件只补这两天的变化。

---

## 一、换过去先做三件事

1. **拉仓**：远端 `Eplayed/forever-mini`，这台机器到 `github.com` 的 HTTPS 经常连不上，走
   `ssh://git@ssh.github.com:443/Eplayed/forever-mini.git`（443 端口那条 SSH 通道实测通）。
   2026-10-31 Mac 侧已把整条 main 推上去（**含站主要求的全量收口：别人未提交的数据产物与两批证据截图一起进了库**），
   所以拉完 `git log -1` 看到的就是 Mac 这边最后的状态；拉之前先 `git fetch`，别看本地旧副本判断"对方没做"。
2. **看第九节**：那台 `git pull` 之后**库里缺的三类文件**（76 份网页 GLB、`.oss-env` 钥匙、本机开发者工具配置）
   各自怎么补、不补会撞哪条门禁——这三件不补，配装页与分发通道在那台是半瘫的。
3. **看第四·五节**：宏命令那两件**只有那台能做**（其中一件要站主本人装 zhCN 文本包）；区域图那 10+1 张游戏内实拍仍欠着，
   这是唯一卡"必须进游戏"的地图项。

| 位置 | 是什么 |
| --- | --- |
| Mac 仓库 | `/Users/zhangyajun/Documents/project/wow-forever` |
| 唯一产品（网页） | `wow-forever-web/app/`（Vue 3 + Vite，hash 路由，**24 条 `path` 声明 / 23 条实路由**，无后端） |
| 唯一数据基底 | `wow-forever-web/app/data/*.json`（小程序也读这一份，不建第二份） |
| 小程序 | `for-mini/`（原生微信小程序，另一条产品，移动端门禁一条不降） |
| 跨机信箱 | Windows 那台的 `C:\GAME\World of Warcraft\ziliao-export\`，Mac 侧只读挂在 `/tmp/wow-ro/ziliao-export/` |
| Windows 从 Mac 取文件 | `\\MACBOOKPRO-F157\project\wow-forever\...`（主机名直读实测通，Z: 盘符显示 Disconnected 不影响） |
| 线上 | <https://eplayed.github.io/wuxian-atlas/> —— **仍是 `wow-forever-web-20261028-174730-4e216292`**（10-28 17:47 打包、17:50 推送） |

---

## 二、规则在哪（接手前必读，别照本文件的转述干活）

| 要什么 | 读哪个文件 |
| --- | --- |
| 六个角色怎么分工、一轮只一个主角色 | 仓库根 `AGENTS.md` |
| 全部红线（分级 L0–L3、素材本地留存、掉落不写百分比、缺数据写"待实测"、禁机翻与编造、第三方只取事实字段、宏与 WA 的免费分享边界、真实 3D 的入站条件） | 根 `AGENTS.md` 第五节 |
| 站主按日期拍板的决定**原文**（优先于任何转述） | `PROJECT_DECISIONS.md` |
| 资料站工程约定（目录、命令、硬规矩） | `wow-forever-web/AGENTS.md` |
| 小程序工程约定 | `for-mini/AGENTS.md` |
| 验证基线（哪类改动跑哪条门禁） | `PROJECT_GATES.md` |
| 当前接手入口 | `NOW.md`；完整台账看 `ROLES.md` 末尾 |
| 界面口径（含动效第十节、宏命令页第十一节） | `wow-forever-web/docs/UI.md` |
| 人读的路径导航 | `wow-forever-web/docs/PROJECT-INDEX.md`（`tools/project-index.py --topic <主题>` 现算） |

**三条最容易踩的**（原文以文件为准）：① 素材一律本地留存、禁止热链，客户端原画类要独立目录 + `manifest.json` + 保留"整目录删除即回退"；② 两源分歧两个都留并标注，缺数据显示"待实测"，不许编；③ UI 改动必须有 `docs/screenshots/` 渲染证据，构建通过不算完成。

---

## 三、2026-10-29 之后本地又落了什么（**线上还没有其中任何一条**）

| 提交 | 是什么 | 状态 |
| --- | --- | --- |
| `b47d011` | 全站交互动效六类（换页 `out-in`、展开收起 `grid-template-rows: 1fr↔0fr`、面板切换、抽屉退场、按压、锚点滚动），新增第四层样式 `app/src/styles/motion.css` | 已提交，**等站主在 8821 人眼验收**（要看 `out-in` 那一瞬的空档能否接受，退路 `--dur-press: 0ms`） |
| `031b5ee` | 撤掉首页那张「最新动态」卡 | 已提交（站主 10-29 明确要的） |
| `9be7513` | **宏命令页上线**：`app/data/macros.json` 245 条 / 9 职业 / 38 个用途分组，整批 L1；导航「工具」组加第 13 格；`?c=&g=&q=&lv=` 深链；一键复制 | 已提交，等 8821 验收 |
| `52a5b49` | 上面那条登记进玩家可见的「本站更新」，导航那颗「新」角标随之落到「宏命令」 | 已提交 |
| `9fa2ece` | 宏命令证据图改走 `snap()`，刷新成带角标那一版 | 已提交 |
| 小程序线（`2a7a679d`…`8791680c`） | BiS 真实 3D 的 B1→B3→C 全链（76 份模型发 beta、点一次只取一件、拿不到退回原画）、配装格改竖盒 + 本站渲的 6 张底图 | 已提交，站主真机确认"模型都有了"；**拖动/换套不留旧画面/退出重进/iOS 仍未验** |
| 小程序线（`e97105ad`） | **小程序宏命令页**：245 条按职业分片、只读 + 复制，`flags.json` 里开关**默认关着** | 已提交，未开开关 |
| 小程序线（`d631ef09`，10-30 深夜） | 宏页九职业那一排换成**带职业图标的横滚职业条**（照配装页那副长相）；`iconKey` 从同批 `classIndex` 取，取不到就构建报错 | 已提交；**零新增图片上传**（图标是素材层 M02-1 那批） |
| 全量收口（10-31，站主："先全部提交并推送仓库"） | 别人两条线留在工作树的未提交改动一起进库：`for-mini/oss-preview/{dungeons,meta,spells}.json`、`for-mini/data/forever-{dungeon,meta}-snapshot.js`、`check-2026-10-29` 那批重拍的 87 张、`check-2026-10-30` 剩下 54 张（约 17 MB）、小程序三批扫码/预览图与两份 `preview-info.json`、`VERIFY-小程序3D续做门槛-2026-10-30.md` | 已提交并推送；**这批不是我做的活，我只是把它们收进库好让那台能 pull 到**——判据与来源见各自原文件 |
| 网页 3D（本轮收口时提交） | 76 份客户端整人模型接进配装页：`app/img/models/real/manifest.json` 台账、`art.json.bisRealModels`、`ModelViewer` 朝向修正、配装判据按"当前套装/阵营命中才出 3D 按钮"、三份产线工具（`import-bis-real-models.py` / `optimize-bis-glb.py` / `apply-optimized-bis-models.py`） | 台账与工具**已入库**；**34 MB 的 GLB 二进制按站主拍板不进 git**（见 3.1）；逐套人眼位置抽查仍挂着 |

### 3.1 那 34 MB GLB 为什么不进库、换机后要补什么

站主 2026-10-30 拍板：**不推，加进 `.gitignore`**。理由三条，都写在 `.gitignore` 那段注释里：
远端 `Eplayed/forever-mini` 是**公开仓库**且已 2.0 GB；"客户端派生模型上静态托管"这条红线（任务 #104）还没拍板；
发布白名单本来也只放 `models/manifest.json` 顶层 `origin == "self-generated"` 那几个，真模型从来没进过发布包。

**代价要认**：Windows 那台 `git pull` 之后 `app/img/models/real/` 里只有 `manifest.json`、没有 `.glb`，
于是 `site-check.py` 的 **[6b] 配装那一节会红**（点 3D 按钮拿不到文件就退回图片，"画布真的建起来了"那条必挂）。
两条路二选一：① 在那台按 `VERIFY-全职业真实3D接入-2026-10-29.md` 的工序重导重算（客户端原件本来就在该台，工具已入库）；
② 或从 Mac 直接把 `app/img/models/real/*.glb` 走 SMB 拷一次过去（`\\MACBOOKPRO-F157\project\wow-forever\...`），不提交。
**别为了"让门禁绿"去改 [6b] 的判据**——它钉的是"玩家点 3D 要看到真模型"，不是文件在不在库里。

**门禁截图的留存也收了口**：`docs/screenshots/check-2026-10-30/` 那 80 张 25 MB 里，10-30 那轮只把**被文档点名的 26 张**入库，
其余留本地。**10-31 改了**：站主要求换机前"全部提交并推送"，剩下那 54 张（约 17 MB）随这次全量收口进了库。
仓库规则写的"新批次落库、上一批 tar 进 `screenshots-archive/` 再删"事实上一直没执行
（`check-2026-10-16…10-29` 九个批次全在库里，现在又多 17 MB），这条要不要真执行仍是**站主的清库决定**，本轮没替他做，也没删任何一张。

**要让玩家看到上面这些，得重新发一包**（`tools/release-package.py` → `pkg-verify.py` → `deploy-gh-pages.py --push`），**发布要站主点头**。
**但站主 2026-10-30 已经定了另一头**：域名还在备案中，**web 网页延后上线**，先把小程序那三件事做掉
（原文见 `PROJECT_DECISIONS.md` 2026-10-30 那一节）——所以"这一包先不发"是符合决定的，不要拿"线上看不见"当 bug 去查组件。
"改了却看不见"先查线上包号，别先怀疑组件——10-28 那次真因就是线上停在 10-23。

---

## 四、宏命令这一层：Windows 能一次买断的两件事

数据侧已经做到"能查的都查了"：正文里的 `{{spellId}}` 先用**本站自己的技能表**反查中文名，
306 个 ID 里 **265 个出自本站表**，剩 **41 个**只对得回插件写法，单独登记在
`wow-forever-web/app/data/macros.json` → `meta.unverifiedSpellIds`。另有 **5 条**正文带 `(Rank N)` 标记（`rankMarker`）。

### 4.1 那 41 个法术 ID 的中文名（要装 zhCN 文本包）

- **前提**：那台客户端（wowf 1.60.1.70532）实际落进 DB2 的文本是**韩文**——Mac 侧复算过
  `ItemSparse.csv` 17,844 行含韩文、含汉字 **0** 行，`Spell` 同向。**韩文名一条都不能上页面**（红线：不机翻、非官方来源不进正文）。
- **总闸**：让启动器把 **zhCN 文本包**装进同一个 1.60.1.70532（同 build 同编号，键值天然齐全）。
  这属于改他的安装状态，**必须站主本人动手**，agent 不碰、不替他决定。
- 装上之后要做的：解 `SpellName`（zhCN 那条）与 `macros.json` 里那 41 个 ID 逐字对；
  对上的把该条 `nameFrom` 从 `addon` 改成"客户端 zhCN"，并同步 `meta.counts` 的 `spellIdsOwnTable` / `spellIdsAddonOnly` 与 `unverifiedSpellIds`；
  跑 `node tools/build-data.js`——卡口会核对"待核名单必须等于实际退回插件写法的集合"，少一个都拦红。
- **不许**：为了把 41 清零而猜名字、或把英文原样留在中文正文里当已核。

### 4.2 `(Rank N)` 在中文客户端里怎么写（**不用装文本包也能判**）

5 条宏的正文里有 `(Rank 1)` / `(Rank 2)` 这类等级标记。中文客户端里到底是「（等级 1）」、
还是原样英文、还是这个 build 已经把等级标记去掉了——**直接决定这 5 条宏按进去有没有效**。
判法：游戏里把那条宏粘进去，看编辑框/聊天框报不报"法术书里没有该法术"。
判完把结论写回 `macros.json`（要么改正文、要么把这条标成不可用），别只在聊天里说。

### 4.3 这一层的红线（三条，改任何一条都要站主先拍）

不分发插件本体、不给"执行"类入口、不推荐循环提示类插件；**一律免费**；
每条带来源与抓取日期（`meta.sources` 已记 GearInsight 0.5.6 与 XR_DungeonGuide v87，
且写明**这两份不是两个独立来源**——XR 自己写"同步 GI"）；不做"哪条更好"的排序或评分。
整批 **L1**，只有游戏内实测或第二家资料才能升档。

---

## 五、地图那一层（10-29 那张账表照旧有效，这里只说变化）

- **已到手并 Mac 侧复核合格**：`ziliao-export/maps-floor-2026-10-29/` 756 片 256×256 + 63 张 1024×768 层图
  （123 条哈希重算不一致 0；63 张内容框实测全部 (0,0)→(1002,668)、比例 1.5000）。判据见
  `wow-forever-web/docs/VERIFY-副本逐层图756片回件复核-2026-10-29.md`。
- **还欠四件**：① DF 层号 ↔ OpenMap 层号是否同一套**未证**（没证之前不许拿它画点，这就是 #108 犯的错）；
  ② 63 张层图**未入素材库**（转 webp 控体积、逐张 `manifest.json` 记 build + **语言 zhCN** + fdid + sha256——层图顶部横幅烘的是简体中文本名，换语言导出字会变）；
  ③ 暴风城监狱差一个复数 s（补别名）；④ 5 座团本有图无数据。
- **只能 Windows 做**：区域图 A 路 10 张实拍 + 1436 西部荒野作对照，任务书
  `wow-forever-web/docs/DATA-区域图-Windows实拍任务书-2026-10-28.md`。
- **判死的那条**：客户端瓦片拼干净区域图不可能（地名烘死在贴图里），只能游戏内实拍。
- 无限新增那 9 座本客户端**没有官方层图**，只能示意图，且页面必须就地标"这张是示意图，不是游戏里的地图"。

---

## 六、门禁怎么跑（改代码才用；Windows 上一般不跑这一套）

```bash
cd wow-forever-web
node tools/build-data.js                 # 改数据必跑：校验 + 覆盖率 + 禁词 + 提交号回查，非 0 即未完成
cd app && npm run build && npx vitest run   # 构建 + 单测（今天 181/181；build 会把 data/img 同步进 public）
python3 tools/site-check.py              # 唯一界面门槛，自己起静态服务打 app/dist（跑前必须已 build）
python3 tools/site-check.py --only app,macros   # 快速探针
python3 tools/app-assets.py --check      # public 与源目录是否一致
python3 tools/project-index.py           # 收尾刷新路径索引
```

**今天量到的一条环境事实**（写下来免得下一个人当产品 bug 追）：这台 Mac 是软件光栅，
一张视口截图实测 24–30 秒；负载 10+ 时 `site-check.py` 会撞截图超时把整场打断。
所以 ① 跑整站前先看 `uptime`；② 所有带 path 的截图统一走 `snap()`（90 秒上限，撞不上的那一拍放宽到 180 秒**重试一次**，
只放宽时间、不改判据、第二次仍失败照抛）；③ 整站今天量级是 **711 条**（583 + 128 两次拼出来，不是一次连续跑完——
换机后第一次请整跑一遍再报数）。

**改了玩家能看到的东西，就要补一条 `app/data/releases.json`**：一条对应一个真实提交，
`build-data.js` 会回仓库核对提交号（短哈希写错会直接拦红），标签决定导航那颗「新」角标落在哪一格。

---

## 七、Mac 侧还挂着的账（换机不消失，别当成已完成）

| 事项 | 状态 |
| --- | --- |
| #108 首领点位参照物错位（7 座跨层本压一张图） | **待**，阻塞在第五节 ①② |
| #113 层图接驳键与坐标系重标定 | 进行中（接驳键 19/25 已出，剩层号语义 + 入库） |
| #112 导航"当前项小药丸"断言偶发红 | **待单开一修**（同一份产物 13 次红 3 次；红出来是 `.on` 在但底色透明） |
| 剃刀高地英文名 `The Razor Krendor` | **已判是错的**（157 MB listfile 里 `krendor` 出现 0 次，WMO 路径是 `KL_Razorfen/RazorfenDowns.wmo`）。改法走 wow-data，两源分歧要留档，别直接覆盖 |
| 小程序 10-28 那批数据改动 | **没重导**（`export-mini.js` 不读 professions 的 nodes 层） |
| 小程序宏页开关 | `flags.json` 里默认关着；开之前 wow-ops 复核一次类目口径（个人主体 工具-信息查询） |
| 网页 76 套真实模型逐套人眼位置抽查 | **未做**（第八轮那两份的教训：帽子露头顶/压颈胸这类只有眼睛能判） |
| 备案 | 管局审核中，预估 11-11、最长 11-25 → **会跨过 11-05 开服**，开服窗口只能用境外 Pages |

---

## 八、两边都要守的纪律（今天用时间换的）

- **客户端只读**：不改、不新增、不删游戏目录里任何东西；所有写入只在自己的导出目录。**共享的登录口令不写进任何文件**（仓库/脚本/文档/台账都不行），用完卸载。
- **交件包规矩**：包内 `MANIFEST.json`（最后生成、不含自身）+ `RESULT.json` + 完整日志，包外 `PACKAGE.json`/`.PACKAGE.txt`，状态写 `*_PENDING_MAC_REVIEW -- NOT SITE_DONE`。
- **`tiles` 数组下标就是拼图位置，绝不许按数字排序**；不许裁空白边、不许缩放、不许加水印、不改色彩配置。
- **`wowfexport get … id` 那条 CascLib 路不可靠**（本地索引只认 440/756、4 个不同 fdid 解成同一份字节）；改走 wow.export 自己的 CASC reader。
- **导出过程不许向任何远端请求文件**：日志里出现 HTTP 行 = 整包作废。拿不到照实写 `NOTFOUND`。
- **共享工作树**：同一文件一次只给一条任务写；提交只提自己的文件（`site-check.py` 这种共享文件用 hunk 级隔离）；**push 前先 `git fetch`**；发布要站主点头。

---

## 九、10-31 换机前最后一次现测（**与前面任何一节数字冲突时，以本节为准**）

### 9.1 远端 beta 现状（10-31 用公网只读 GET/HEAD 现测，没发任何写请求）

| 对象 | 键 | 10-31 实测 |
| --- | --- | --- |
| 数据指针 | `wow/beta/v1/manifest.json` | 仍是批次 **`d25932f1c7a3`**（10-27 那条），这两天一个字没换过 |
| 模型索引 | `wow/beta/v1/bis/models/index.json` | `200`；`counts = {models:76, sets:38, bytes:111,117,416, sourceBytes:35,344,092}`；最大一件 `druid-tank/horde` 1,914,784 B、最小 `mage-arcane/alliance` 1,169,232 B |
| 76 份模型件 | `wow/beta/v1/assets/models/real/<setId>-<faction>-<哈希>.glb` | B3 上传时逐件 HEAD+GET 回读过；10-31 抽 3 件 HEAD 全 `200` |
| 6 张配装底图 | `wow/beta/v1/assets/models/posters/<race>-<哈希>.png` | **六张全 HEAD+GET `200`**：dwarf 334,140 / orc 256,497 / human 190,679 / tauren 181,324 / night-elf 178,818 / undead 170,206 B，合计 **1,311,664 B** |
| release 与开关 | `wow/release/**`、`wow/{env}/v1/flags.json` | **一个请求都没发过**；宏页开关仍 `macros.on=false` |

**衍生件到底是什么**（下一个人极容易在这里误判，所以写死）：微信加载不了 WebP 纹理的 GLB，
所以 B1 是把纹理重导成 PNG 的**同一个 glTF 二进制**——文件头实测 `glTF\x02`，扩展名仍是 `.glb`，
文件名里的哈希是**这份文件自己**的 SHA-256 前缀（不是里面某张贴图的哈希）。10-31 抽 druid/alliance 对拍：
本地 `for-mini/oss-build/beta/models/druid-alliance-fb2c11a94154.glb` 1,269,028 B、sha256 前缀 `fb2c11a94154`，与索引里 `pngBytes`/`pngSha256` 逐字相同。
底图的文件名带哈希、图在远端不在包里，取数表 `for-mini/data/bis-posters.js` 由 `tools/export-bis-posters.js` 生成（键是 `<职业>|<阵营>`，18 条），取不到就退回职业原画。

小程序这一侧这两天的账（细节各回各的 VERIFY，别在本文件里找判据）：
`for-mini/docs/VERIFY-小程序3D分发-2026-10-30.md`（B1 构建 + B3 分发，状态 `BETA_DISTRIBUTED`）、
`…/VERIFY-小程序3D远端单件-2026-10-30.md`（B2 单件真机，含设备信息）、
`…/VERIFY-小程序BiS真实3D-2026-10-30.md`（C 接入 BiS 页 + 第 9 节底图）、
`…/VERIFY-小程序宏命令页-2026-10-30.md`（宏页，第 8 节是职业图标）、
`…/VERIFY-小程序3D续做门槛-2026-10-30.md`（当时写的 B2→B3→C 顺序与门槛）。
契约与组件在 `for-mini/services/bis-model.js`、`for-mini/components/bis-3d/index.js`。

### 9.2 `git pull` 之后那台**库里没有**的三类东西

这三类都是**拍板不进库**的，不是丢了；缺了会撞哪条，写清楚：

| 缺什么 | 为什么不在库里 | 怎么补 | 不补的后果 |
| --- | --- | --- | --- |
| 76 份网页 GLB（`app/img/models/real/*.glb`，Mac 侧 10-31 清点 **76 份 / 35,344,092 B**） | 站主 10-30 拍板：公开仓库已 2.0 GB，二进制不进 git（`.gitignore:70`） | ① SMB 从 Mac 拷（`\\MACBOOKPRO-F157\project\wow-forever\...`），**别提交**；② 或按 `VERIFY-全职业真实3D接入-2026-10-29.md` 的工序在该台重导（客户端原件本来就在该台，工具已入库） | 网页 `site-check.py` 的配装 [6b] 红（点 3D 拿不到文件就退回图片）；**小程序侧 76 份衍生件也没法重建**——`tools/build-mini-bis-models.py` 只读这批 GLB |
| 小程序侧 76 份 PNG 纹理衍生件 + 索引（`for-mini/oss-build/`，**111,117,416 B**） | `for-mini/.gitignore:9` 整目录忽略（派生产物，可重算） | **不用拷**：远端 beta 已经有，客户端按 `setId+faction` 精确取一条。要重建才需要跑 `build-mini-bis-models.py`（依赖上一条的 GLB） | 无。页面读的是远端，不读本地目录 |
| OSS 钥匙：仓库根 `.oss-env`（`.gitignore:57`）与跨仓那把 PoE 钥匙 `../p2-database/auto_browser/.env` | 密钥从不入库，**本轮也没有搬运、没有写进任何文件** | 站主本人把那台要用的钥匙放回报的位置；每条写命令仍要显式 `WOW_ALLOW_CROSS_CREDS=1`，release 另加 `--yes-release` | 换机后**写真 Bucket 的通道是断的**：`upload` / `models` / `posters` 子命令全部拿不到钥匙。只读的公网回读不受影响（就是 9.1 那种） |

另外两件小的：`for-mini/project.private.config.json` 是开发者工具本机配置（gitignore，那台自己生成）；
`app/dist/`、`app/public/`、`vibe_images/`、`.audit-cache/` 也都在忽略列表里，缺了是正常状态，跑构建就有。

### 9.3 Mac 独有的工具链——那台**不要照抄命令**

- **小程序整轮门禁 `tools/mini-m01-check.js`**：Mac 侧走微信开发者工具 `cli auto --auto-port 9421`
  + 本地 automator 打桩 `MiniProgram.prototype.checkVersion = async () => true`，且 `NODE_PATH` 指到
  `~/.npm/_npx/947b10de6a8fe99b/node_modules`。Windows 版开发者工具能装，但**这条自动化路在 Windows 上从没验过**：
  第一次跑先做最小连接探针（能读到当前路由再谈整轮），别把"连不上 ws"记成"页面坏了"——
  Mac 这边 10-30 深夜就因为自动化会话掉了**整轮中断两次**，重开 `cli auto` 并用最小探针确认后才跑出 106/106。
- **底图产线 `tools/render-bis-posters.py`**：python playwright + 系统 Chrome headless，
  必须带 `--enable-unsafe-swiftshader --use-angle=swiftshader`（没有这俩就没有 WebGL 上下文）、
  rAF 被节流所以改用计时器、元素截图会带背景所以用 `omit_background=True`、出图后用 PIL/numpy 复核**不许裁头脚**。
  这些坑是一条条撞出来的，判据在 VERIFY 第 9 节；那台若有独显也先按无 GPU 走一遍。
  **模型朝向**：这批客户端导出件面朝 **+X**（xr-frame 那边手性相反），相机位置按这个定的，别"顺手改成 -Z"。
- **扫码预览**：`cli preview --qr-format image --qr-output …`；隔离预览工程的 `project.config.json` 把
  临时探针路由 ignore 掉了——`pages/model-probe` 已经撤过，**不要再加回主工程**。

### 9.4 门禁现在是什么数（**全是 Mac 侧 10-30 深夜量的，那台要重跑再报数**）

| 门禁 | 10-30 实测 | 今天动过什么 |
| --- | --- | --- |
| `node tools/mini-bis-model-test.js` | **29/29** | 模型取数契约（三条闸 + 哈希/文件名一致 + 路径防穿越） |
| `node tools/oss-release-test.js` | **242/242** | 分发层自测（含 `models` / `posters` / 宏三通道正反例） |
| `node tools/mini-m01-check.js` | **106/106** | 含宏页那 8 条，其中一条已加硬成"九个职业 chip 每个都带得出 http 图标地址" |
| `node tools/oss-release.js build --env beta` | rc 0（167 文件 / 2,537.9 KB） | **只是本地构建产物，没上传** |
| `node tools/build-data.js` / `export-mini.js` | 退出 0 | — |
| 网页 `site-check.py` | **今天没跑**（今天一行 `app/` 都没碰）；最后一次 10-30 是 676/676 | 注意 [6b] 要 GLB 在场才绿，见 9.2 |

### 9.5 这次"全量提交并推送"到底推了什么，以及它**不等于**什么

推的是 Mac 本地 main 上攒的全部提交：除了我这一轮的（图标 `d631ef09`、索引 `298db08f`、本节），
还连带**别人两条线留在工作树的未提交改动**一起收进库——`for-mini/oss-preview/{dungeons,meta,spells}.json`、
`for-mini/data/forever-{dungeon,meta}-snapshot.js`、`check-2026-10-29` 重拍的 87 张与 `check-2026-10-30` 剩下 54 张（约 17 MB）、
小程序三批扫码/预览图。**推送 ≠ 发布**：线上 Pages 仍是 10-28 那一包 `wow-forever-web-20261028-174730-4e216292`，
OSS 的 release、beta 数据指针、`flags.json` 一个字没碰，小程序没提审没发布。
"改了却看不见"先查线上包号，别先怀疑组件——10-28 那次真因就是线上停在 10-23。

### 9.6 换机不消失的账（照第七节，加今天这几条）

- 小程序 3D 四件仍未验：**拖动、换套不留旧画面、退出重进重新加载、iOS**（Android 只到"模型都出来了"和底图那一版）。
- 宏页：真机没扫；开关默认关着；开之前 wow-ops 复核一次类目口径（个人主体 `工具-信息查询`，只读 + 复制）。
  **今天"发批次会连带别人未提交数据"这条风险已经没了**（那些数据已进库），发不发仍要站主点头。
- 网页 76 套真实模型**逐套人眼位置抽查**未做（第八轮教训：帽子露头顶 / 压颈胸这类只有眼睛能判）。
- 第四节两件不变：41 个法术 ID 的中文名要装 zhCN 文本包（**站主本人动手**），`(Rank N)` 那 5 条要在游戏里判。
- 第五节地图四件不变（层号语义未证、63 张层图未入库、监狱复数 s 别名、5 座团本有图无数据）+ 10+1 张区域实拍只能那台做。
- 备案：管局审核中，预估 11-11、最长 11-25 → **会跨过 11-05 开服**，开服窗口只能用境外 Pages。

### 9.7 两件等站主拍板（别自己拍）

1. 现在要不要 `upload --env beta` 把宏这一批发出去（发出去 = 玩家联网就能查到；开关另说）。
2. 小程序宏页要不要并列显示英文 `titleEn/noteEn`——这一轮按"中文查询页"没下发，要中英对照得先定口径。

状态：**已定**（第一至八节为 2026-10-30 现测，第九节为 2026-10-31 现测，路径、字节、哈希均可回查）／**待站主**（装不装 zhCN 文本包、要不要发宏这批数据、英文对照口径、8821 那两处人眼验收、清库那条）／**阻塞**（#108 等层号语义，非换机能解）。
