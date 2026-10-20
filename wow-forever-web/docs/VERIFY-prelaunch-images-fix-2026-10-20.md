# VERIFY · W01 上线前图片修复（2026-10-20）

主角色：wow-dev ｜任务 ID：**W01（W01-A / W01-B / W01-C）**
上游输入：`wow-forever-web/docs/VERIFY-prelaunch-images-2026-10-20.md` §3 任务书（含 §2 实测清单与 §2.3 为什么原检查漏了）
交接给：**Codex 独立验收**（本文件是实现方自述，不代表已验收）

状态：**W01-A/B/C 已执行完，待独立验收。** 本轮不部署、不推送远端、不做 W02、不做 Q01B/Q02。
Q01A 已通过，本轮不重做（只带着它的门禁一起跑回归）。

## 零、三种结果先分清楚

任务书要求严格区分"实际补图 / 无图布局改善 / 仍缺原料"。本轮结果：

| 类别 | 本轮实际 | 一句结论 |
| --- | --- | --- |
| **实际补图** | **3 张图标**（1 张官方 us 区 + 2 张换区域 eu/kr/tw 能取到）+ **1 张本来就有图却 404 的**（键名带尾点，图一直在本地） | 图标缺键 **165 → 161**：补回 1 + 换区域补 2 + 尾点归正 1 = 少 4 个；引用键数 3,455 → 3,454 是那条带尾点的与无点写法合并去重（见 §2.4） |
| **无图布局改善** | 世界页四类面板的无图那一屏（区域卡 8 张 + 稀有/书/营地面板里的无图组） | 空图框撤掉，改成一行数据值 + 整宽列表；**底图一张都没补上** |
| **仍缺原料** | **9 张区域底图**、**82 只首领头像**（78 源站自标没有 + 4 名字对不上不猜）、**2 座团本载入图** | 逐张列了原因与解除条件，见 §3、§5 |

## 一、W01-A：世界页九张区域底图——本轮结论是"拿不到"，不是"修好了"

### 1.1 我这一轮自己查的三条证据（不是照抄上游文档）

| 查法 | 结果 |
| --- | --- |
| 插件目录 `~/Documents/project/.scratch/wow/`（GI 0.4.32 / XR 65 / DungeonsForever 1.8.20 / HandyNotes）全量列图片文件 | 20 个 `.blp` + 137 个 `.tga`，全在 `Media/{DungeonMaps,CustomMaps,Maps,Guide,Race,Class,icon,textures,Loadings}` 下面。**按九个地图号搜文件名：0 命中**；区域底图一张都没有（副本内部图 31 张、职业/种族图标 18 张、其余是按钮与纹理） |
| 既有来源 `wowforever.wclbox.com/ditu-xiao/<id>.webp` 逐条 curl | 九条全 **404**；同主机对照条 `1426.webp`（丹莫罗，我们已有）**200**。另试 `1424.png` / `ditu-da/1424.webp` / `ditu/1424.webp` 三种变体也全 404 |
| `ditu` 索引页 | 是个 JS 壳（17 KB，无图片直链），拿不到"源站到底有几张"的清单，只能按 id 逐条问 |

与 `DATA-CLIENT-EXPORT-2026-10-19.md` §六 A 行（"需要 45 张、本地 37 张、插件 0 命中"）本轮独立复核一致。

### 1.2 九张逐张状态（阻塞，缺原料）

| uiMapID | 名称 | 影响 | 阻塞原因与解除条件 |
| --- | --- | --- | --- |
| 2548 | 河林 | 首屏新增区域卡 | 源站 404、插件 0 命中。要客户端导出：`MapArea.db2` + `MapDiff.db2` 找贴图前缀 → `Textures/Maps/*.tex` → webp（长边 ≤640） |
| 2652 | 辛德拉 | 新增区域卡 | 同上 |
| 1424 | 希尔斯布莱德丘陵 | 区域卡 + 稀有点位 | 同上 |
| 1430 | 逆风小径 | 区域卡 | 同上 |
| 1440 | 灰谷 | 区域卡 + 稀有点位 | 同上 |
| 1449 | 安戈洛环形山 | 区域卡 + 稀有点位 | 同上 |
| 1451 | 希利苏斯 | 区域卡 + 稀有点位 | 同上 |
| 1457 | 达纳苏斯 | 区域卡 | 同上 |
| 1453 | 暴风城 | 稀有"下水道鳄鱼"这一条进不了图 | 同上；这条不在区域那 8 张里，是稀有侧的缺口 |

导出件到之后的接法写在 `docs/UI.md` §3.60 末：图落 `src/img/art/maps/<mapId>.webp` + `art/manifest.json` 逐张记来源，
`mapFile` 由 `tools/merge-world.js` 那条链重建，**不手改派生 JSON**。本轮没有新增任何一张图，
所以 manifest 与 `merge-world.js` 都没动（没有可记的东西，硬造一条就是假来源）。

**没有做任何冒充**：没拿副本内部图当区域图（两者坐标系不同，任务书与 AGENTS 都禁止），
没拿正式服/经典服地图凑，没生成图，没改文件名。

### 1.3 无图那一屏改成了什么（这是本轮真正交付的界面变化）

规格与理由在 `docs/UI.md` §3.60，实现要点：

- `app/src/components/PinMap.vue`：无图时**不渲染 `.zbig`**（原来是一个 `min-height:120px` 的空图框），
  改成一行数据值 `<p class="znomap"><b class="zbig-id mono">地图编号 2548</b></p>`，
  `.zband` 加 `.nomap` 收成单列，点位清单占满整宽。
- 一颗点都不画（点位只在 `hasMap` 时渲染），列表行的序号列是「—」，坐标照原样在列表里读。
- 区域名、等级/阵营、稀有/书/营地计数**全部保留**，没图的区域**不整条隐藏**，页面上不加"我们为什么没有这张图"。
- `imgBad` 加 `watch(mapFile)` 清零：原来一次图片失败会**永久污染这块面板**——
  同一个组件实例换到下一个有图的区域，新图明明是好的也不再显示。`ZoneMap.vue` 早就有这条 watch，这里补齐。
- 新 prop `noMapLine`（默认 true）：副本详情页「入口在哪」那张卡下面 `.dgeo-line` 已经把
  "只给坐标：地图编号 1440" 说全了，那一处传 false，无图时整块不渲染，避免同一屏两个数重复。
- `src/css/board.css`：删 `.zbig.noimg .zcanvas`，加 `.znomap` 与 `.zband.nomap`。

## 二、W01-B：图标——补回的、修好的、仍然缺的

### 2.1 实际补回（官方 CDN，本地留存 + manifest）

| 图标键 | 从哪来 | 验证 |
| --- | --- | --- |
| `spell_warlock_demonsoul`（牧师暗影"黑暗启发"，`changes.json` id=`calc-priest-shadow-dark-inspiration`） | `tools/fetch-icons.py` → `render.worldofwarcraft.com/us/icons/56/` | HTTP 200、2,691 字节、JPEG 魔数 + **PIL 解出 56×56 RGB**（不是只看 HEAD 200） |
| `flightstone-blue` | `tools/audit-assets.py --fetch` → us 区没有，换区域命中 | 同上（脚本要求 `>500` 字节 + JPEG 魔数才落盘） |
| `inv_10_worlddroplevelingoptionalreagent_archaeology_trolltooth_color2` | 同上，换区域命中 | 同上 |

### 2.2 顺手修好的一张"本来就有图却 404"

`items.json` 里 #269247 失效的护命匣 的 `iconKey` 是 `spell_shadow_devouringplague.`（**带尾点**），
而本地文件叫 `spell_shadow_devouringplague.jpg`（无尾点，`spells.json`/`changes.json`/`icons.json` 用的都是无点写法）。
`IconCell` 按 `key + '.jpg'` 拼地址 → 请求 `spell_shadow_devouringplague..jpg` → 404 退字母块。
缺图登记里那条带尾点的键于是永远"补不到"，因为**图一直在**。

修的是生成端不是成品：`tools/merge-items.py` 第 84 行 `icon.rsplit('.', 1)[0]` 只剥掉 `.jpg`，
上游那个多出来的点留在键名里 → 改成再 `.rstrip('.')`，重跑 `merge-items.py` 重建 `items.json`
（**全库只有这一条受影响**，diff 是 1 行；不是手改派生 JSON）。

### 2.3 扫描范围与双向卡口（任务书点名的"原检查为什么漏"）

| 问题 | 修法 |
| --- | --- |
| `audit-assets.py::collect_keys` 写死十个文件清单，本轮只能报 82 个缺键（实况 165） | 删掉那份清单，改成**复用 `build-icon-map.py` 那一份扫描规则**（importlib 载入，不抄第二份）：全部成品 JSON + `talents/`，排除 `upstream/` 原料与 `icons.json`/`icon-gaps.json` 两份登记自身 |
| 字段只收 `iconKey`，且有人把 `items.icon` 的 `.jpg` 文件名再拼一次后缀 | `collect_all_keys` 现在收 `iconKey` 与 `icon` 两种字段，统一 `norm_key()`：剥 `.jpg`、剥残留尾点，再按合法键判定；不合法的**报出来不静默收下**（本轮实测：`items.json` 两种字段同键，收两种不改变引用集，只把带尾点那条归正） |
| 合法键规则照抄 `fetch-icons.py` 会把带连字符的真键判成非法 | 这里用 `^[A-Za-z0-9_\-]{3,80}$`（`flightstone-blue`、`inv_chest-_cloth_skybornec60_b_01` 这类带横杠是上游物品图标名的真实写法）。第一版我照抄了 `[a-z0-9_]`，19 个真引用被踢成"没人引用"，靠反向测抓回来 |
| `build-data.js` 只查"登记说缺、其实本地有"一个方向 | 改成调 `python3 tools/build-icon-map.py --check`，**精确集合一致**：`引用键 − 本地存在键` 必须正好等于登记键。三类都报错：① 漏登记（新缺图，就是本轮 `spell_warlock_demonsoul` 那种）② 过期登记（图已补回）③ 死条目（登记里的键现在谁也不引用）。判定逻辑只留 Python 一份，Node 侧不抄第二套 |
| 登记是手抄的数 | `icon-gaps.json` 与 `icons.json` 都由 `build-icon-map.py` 生成，meta 里写清范围与"这是派生物，改数据要重跑" |
| `IconCell.vue` 注释写"不产生失败请求"，实现是 error 之后才撤 img | 注释按实现改正，并写明为什么不改成"按清单预判"（那样未知失败就再也发现不了） |
| `src/img/icons/manifest.json` 的 `missing`/`ok` 看着像全库盘点，其实装的是最近一批的结果 | `fetch-icons.py` 改成 `batchAdded`/`batchUnavailable` + 指向 `icon-gaps.json`，并删掉旧键（改名前实测过：旧 `missing` 144 个键全在 `batches` 历史里，删它不丢信息） |

### 2.4 补前 / 补后数量（以实际文件与数据集合为准）

| 项 | 补前 | 补后 |
| --- | --- | --- |
| 数据里引用的图标键 | 3,455（旧登记口径） | **3,454**（带尾点那条归正后与无点写法合并去重） |
| 本地 `src/img/icons/*.jpg` | 3,291 | **3,294** |
| 引用了但本地没有（= 缺图登记） | **165 实况 / 164 登记**（差的那 1 个就是没登记的 `spell_warlock_demonsoul`） | **161**，登记与实况一致 |

任务书里"补这一张后 164"的预期是按旧扫描算的；本轮还多做了换区域补 2 张与尾点归正 1 张，
所以落点是 161。**没有为了对上 164 这个数字去动登记或数据。**

### 2.5 仍然缺的 161 个键——来源与探测时间

`docs/ASSET-GAPS-2026-10-20.md`（本轮 `python3 tools/audit-assets.py --refresh --fetch` 产出，rc 0）：

| 报告里的项 | 数 |
| --- | --- |
| 数据里引用的图标键（全量成品 JSON + talents，含 iconKey 与 icon 两种字段） | 3,454 |
| 本地已有 | 3,294 |
| 缺 | 161 |
| **其中当天重新问过官方 CDN** | **161** |
| 其中沿用探测缓存（不是当天重测） | **0** |
| 换区域/尺寸还能补上 | 0（能补的 2 个键本轮已经落盘，见 §2.1） |
| 五个候选路径都取不到（实测 403/404） | 161 |
| 键名不合法 | 0 |
| `art.json` 指向但文件不存在 | 0 |
| 首领 228 / 挂上头像 146 / 孤儿头像文件 0 | 228 / 146 / 0 |
| 副本与团本载入图缺口 | 2 座 |
| 区域小地图上游状态 | 九张逐条 **404**（1424/1430/1440/1449/1451/1453/1457/2548/2652） |

口径：`--refresh` 是**忽略探测缓存、当天逐个重问官方 CDN**（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸），
报告顶部写明本轮跑法与"当天重问 / 沿用缓存"各多少个——不把旧缓存说成当天重测。
本轮不从第三方抓物品图标（红线：第三方站只给文件名）。

## 三、W01-B3：首领头像与两座载入图——逐类定状态，一张都没硬配

| 类别 | 数 | 本轮实测（2026-10-20） | 处理 |
| --- | --- | --- | --- |
| 首领总数 / 已挂头像 | 228 / 146 | `dungeons.json` 与 `art.json`、`src/img/art/bosses/` 三处逐个对：146 = 146 = 146，**孤儿文件 0** | 不动 |
| 未挂头像 | **82**（分布在 23 座本） | `fetch-art.py --what bosses --probe`（只问不落盘）：源站自己标 `data-unknown` 的 **78 只**；源站页面上没有这一节的 **4 只**（`old-serra-kis`、`twilight-lord-kelris`、`aku-mai`、`grubbis`） | **本轮补 0 张**：78 只是源站没有，4 只是名字对不上——按红线不猜脸、不拿别的种族凑，一律留既有自绘首字块 |
| 载入图 | 36 张已挂 / **2 座缺** | `barrow-deeps`、`hyjal-summit` 按两条真实来源各问一次（`wclbox/jiemian/dungeons/xiao/art-<id>.webp` 与 `wowclassicforever.info/images/dungeons/client/<id>/loading-screen-640.webp`），六种组合全 **404**；同规则对照条 `art-the-drowned-city.webp` **200** | 保留无图布局。**不宣称"官方永远不存在"**——这两座是还没开放的团本壳，客户端里本来就没有载入图（`DATA-CLIENT-EXPORT` §六 E 行），开放后要重问 |

头像最多的几座：洛丹伦废墟 7、影牙城堡 7、黑石塔下层 7、监狱 6、黑石深渊 6、祖尔法拉克 5、沉没的神庙 5、斯坦索姆正门 5。

## 四、W01-C：门禁与回归

### 4.1 新增的独立反向用例

| 用例 | 钉什么 | 反向测（真的把东西弄坏，看它响不响） |
| --- | --- | --- |
| `app/tests/pinmap.spec.js`（新，7 条） | 无图不画点、只留编号那行、列表信息不少、紧凑态整宽、`noMapLine=false` 整块不渲染、失败落紧凑态、**失败后换好图能恢复** | 恢复那条是把 `watch` 去掉就会红的断言（实现前它确实会红——原来 `imgBad` 不复位） |
| `build-icon-map.py --check` 三类比对 | 漏登记 / 过期登记 / 死条目 | **实测过**：① 把 `spell_warlock_demonsoul.jpg` 挪走 → `build-data.js` rc=1，报"1 个没登记"；② 往登记里塞一个本地已有的键 → rc=1，报"本地其实已有"；③ 本轮真实发生的一次：带尾点的死条目被 ③ 抓出来 |
| `tools/route-smoke.py`（新工具） | 26 条路由（21 条 + 详情带参数）每条：全部 img src 与 CSS 背景逐个问服务，状态码 **和 content-type** 都要对；破图、未登记的失败、console 报错都算不通过 | **实测过**：把 `ability_warrior_shieldcharge.jpg` 挪走再跑——第一版**没响**（vite preview 的 SPA 兜底对不存在的路径返回 200 + index.html，只看状态码等于没验）；改成看 content-type 之后才响。这条已写进脚本头注释 |
| `site-check.py` `world_pins` 新断言 | 图框数 = 数据有图数、紧凑态数 = 数据缺图数 | 本轮实测 `图框 36（数据有图 36）/ 紧凑态 8（数据缺图 8）`；改回旧的空图框实现会让"图框 44"红 |

### 4.2 命令与退出码

| 命令 | rc | 结果 |
| --- | --- | --- |
| `python3 tools/merge-items.py` | 0 | 21,077 件重建，diff 1 行（只有那条带尾点的） |
| `python3 tools/build-icon-map.py` | 0 | 映射 509 条 / 缺图登记 161 个键（派生，不手填） |
| `python3 tools/build-icon-map.py --check` | 0 | 「缺图登记与实况一致：161 个键（引用 3454、本地 3294 张）」 |
| `node tools/build-data.js` | 0 | 校验通过；禁词体检干净；缺图登记 161（按文件 items 159 / professions 77 / world 9 / legacy 2 / changes 1 / dungeons 1 / spells 1，引用有重叠不能相加） |
| `node wow-forever-web/tools/export-mini.js` | 0 | 跑了两遍（补图标前后各一遍）；`git status` 对 `for-mini/` 无新增改动，产物可复现。它只读 classes/dungeons/glossary/meta/systems 五份，本轮改的 `items.json` 与图标不在输入里 |
| `cd app && npm run build` | 0 | vite 构建通过（含 `app-assets.py` 同步）。服务侧核对过：`http://127.0.0.1:8821/` 给的 JS 与 `app/dist/index.html` 是同一个 hash（`index-BoqkwuHu.js`），新补的图标经服务取回 200 / image/jpeg / 2,691 字节 |
| `cd app && npx vitest run` | 0 | **100/100 通过**（9 个文件；本轮新增 `pinmap.spec.js` 7 条） |
| `python3 tools/audit-assets.py --refresh --fetch` | 0 | 见 §2.5：161 个键当天全部重问，0 个沿用缓存。**第一版跑到一半 `NameError: load` rc=1**（我自己删旧扫描块时把 `load()` 一起删了）——修完重跑才算数；那半程已经把 2 张换区域能取到的图标落了盘，所以登记与报告都重做了一遍 |
| `python3 tools/site-check.py --app --only world_pins` | 0 | 26/26（含本轮新增那条：图框 36 / 紧凑态 8） |
| `python3 tools/site-check.py --app --only bis` | — | 本轮没单独跑；Q01A 那 33 条在下面的全跑里逐条绿（`猎人 PvE 联盟…615护甲`、`这一套每条带护甲的行都落进了已知写法`） |
| `python3 -u tools/site-check.py --app` | **0** | **通过 896 / 896，0 条 FAIL**（上一轮 895 + 本轮 `world_pins` 新增 1 条） |
| `python3 tools/route-smoke.py` | **0** | 26 条路由 0 问题；按缺图登记放行的取不到 2 次 |
| `python3 tools/route-smoke.py --only-shots` | 0 | 五处截图全出；黑暗启发那行图标 `spell_warlock_demonsoul.jpg`、`ok:true`、`naturalWidth 56`；世界页 `图框 36 / 紧凑态 8 / 破图 0`；物品库抽屉 1 张图 0 破图 |
| `python3 tools/fetch-art.py --what bosses --probe` | 0 | 228 / 146 / 78 源站没有 / 4 名字对不上 |
| 之后：`releases.json` 补两条 → `node tools/build-data.js` | 0 | 「本站更新 63 条（每条带提交号，可回查）」、禁词体检干净 |
| 之后：`npm run build` + `site-check --app --only updates_rank,app,world_pins` | 0 | **120/120**（补完更新说明会改到动态页与导航角标，这三节重跑过；日志 `site-check-only-after-releases.log`） |

日志副本：`docs/logs/2026-10-20-W01/`（十份，含两次失败的那两份）。**`.log` 被 `.gitignore` 第 9 行挡住，进不了 git**；
所以同目录另有一份进库的 `SUMMARY.md`，把每条命令的收尾与关键断言原样抄了一份，验收方不必依赖我的 `/tmp`。

### 4.3 截图（桌面 1440 + 375，真浏览器）

目录 `docs/screenshots/check-2026-10-20/`：

| 文件 | 内容 |
| --- | --- |
| `w1-world-zones-nomap.png` / `-m.png` | 世界页区域面板：河林等无图那几张现在的紧凑读法 |
| `w1-updates-dark-inspiration.png` / `-m.png` | 最新动态搜"黑暗启发"：图标是否真加载出本地图 |
| `w1-items-drawer.png` / `-m.png` | 物品库详情抽屉（点开一行）：图标与图片 |
| `w1-dungeon-barrow-deeps.png` / `-m.png` | 缺载入图那座团本壳的无图读法 |
| `w1-dungeon-lordaeron-nofaces.png` / `-m.png` | 七只没脸首领那座：自绘首字块占位 |
| `app-bis*.png` | 配装页（Q01A 那两条，随全跑重拍） |
| 全跑其余 | `site-check --app` 当日一批 |

## 五、仍然缺的东西与解除条件（上线判据相关）

| 缺口 | 数量 | 解除条件 | 谁做 |
| --- | --- | --- | --- |
| 区域底图 | 9 张 | 从无限服客户端导 `MapArea.db2` + `MapDiff.db2` → `Textures/Maps/*.tex` → webp（长边 ≤640），带客户端版本号与导出日期 | 站主那台 Windows 客户端 → wow-data 落 manifest → wow-dev 按 §3.60 接回 |
| 首领头像 | 82 只 | 78 只等源站补（它自己标 data-unknown）；4 只要先把名字对上（不猜） | 站主压测窗口顺手看 / wow-data |
| 团本载入图 | 2 座 | 这两座开放之后重问两台源 | 开服后 wow-data |
| 图标 | 161 键 | 官方 CDN 五个候选路径当天重问全 403/404（多是无限服新装备，`inv_*_skybornec60_*` 一类）→ 只能进游戏内实测或等官方素材渠道 | 保持自绘块，不算破图 |

**上线判据本轮不宣布达成**：W02（动态页胶囊计数全 0 那个显示错误）没做（任务书要求不在 W01 里偷偷重构动态模块）；
部署产物与 base 那条（`vite.config.js` 注释说 `./`、实际没配 base）也没动——
但本轮实测到一条与它直接相关的事实，见 §六。

## 六、本轮新发现（写给 Q05/上线验收，不在 W01 范围内修）

`vite preview` 对**不存在的路径返回 200 + 一份 index.html**（SPA 兜底）。
这意味着：① 只看 HTTP 状态码的素材检查在这台预览服务上等于没检查（我的反向测就是这么抓出来的）；
② 正式静态托管如果也开 SPA 兜底，缺图/缺 JS 会**以 200 的 HTML 伪装成取到了**，页面表现为破图或白屏且零报错。
上线验收（Q05）必须按 content-type 判，并且要核选定托管的兜底行为。本轮没改 `vite.config.js` 的 base，
也没做任何部署配置。

## 七、没验到的

1. **九张底图"永远拿不到"不是本轮结论**——只证明"这三条渠道现在拿不到"。
2. **161 个缺键的判定来自当天重问官方 CDN 五个候选路径**；"CDN 没有这个文件"不等于"游戏内没有这张图"
   （无限服新图标官方 CDN 缺是已知现象）。界面退自绘块是设计行为，不是已核实正确。
3. **78 只没脸首领**是源站自标 data-unknown，本站没进游戏核对。
4. **紧凑无图布局的人眼复核没做**：我读的是压缩截图，只能证明"空框没了、信息还在、不横溢"，
   判不了"这样读起来舒不舒服"。要人眼看的点：无图那一屏现在是一行编号 + 一整列文字，
   与旁边有图的卡并排时会不会显得"这半屏没做完"。
5. **`--shots` 那几处只拍了 5 个入口**（世界/最新动态/物品库/两座副本），
   其余 21 条路由的图片是脚本按 src 逐个问服务的，没有逐条截图。
6. 抽屉/浮层里"图片解码后布局不抖"没量化（只查了破图与横溢）。
7. **W02 那个显示错误本轮没碰**（动态页"全部类别 967"与胶囊计数全 0 不一致）。
8. ~~小程序侧要不要跟着重建~~ 已核：`export-mini.js` 只读 classes / dungeons / glossary / meta / systems
   五份，本轮改的 `items.json`、图标与 `icon-gaps.json` 都不在它的输入里；补图前后各跑一遍，
   `for-mini/` 零改动（§4.2）。**但这一条只对"本轮这些改动"成立**，
   真改了那五份输入之一时必须重跑。

## 八、修改文件清单

| 文件 | 改动 |
| --- | --- |
| `app/src/components/PinMap.vue` | 无图紧凑态 + `nomap` 类 + `noMapLine` prop + `watch(mapFile)` 复位 `imgBad` |
| `app/src/pages/DungeonPage.vue` | 入口那张 PinMap 传 `:no-map-line="false"` |
| `app/src/components/IconCell.vue` | 只改注释（"不产生失败请求"与实现不符） |
| `src/css/board.css` | 删 `.zbig.noimg .zcanvas`，加 `.znomap` / `.zband.nomap` |
| `app/tests/pinmap.spec.js`（新） | 7 条组件行为断言 |
| `tools/build-icon-map.py` | 扫描范围与键归一（`iconKey`+`icon`、剥 `.jpg` 与尾点、合法键规则含连字符）+ `--check` 双向闸 |
| `tools/build-data.js` | 缺图登记卡口改成调 `--check`（三类都拦），拿不到 python3 时报"没比对"而不是静默 |
| `tools/audit-assets.py` | 删掉写死的文件清单，复用同一份扫描；加 `--refresh`；报告里分开"当天重问 / 沿用缓存"；修我自己删掉的 `load()` |
| `tools/fetch-icons.py` | manifest 的 `missing`/`ok` 改名成 `batch*` 并指向真正的登记 |
| `tools/route-smoke.py`（新） | 26 条路由生产构建冒烟 + W01 那几处的桌面/375 实拍 |
| `src/data/items.json` | 重建（1 行：那条带尾点的 iconKey 归正） |
| `src/data/icon-gaps.json`、`src/data/icons.json` | 重新派生（161 键 / 509 条映射） |
| `src/data/search.json`、`src/data/talent-preview.json`、`src/data/scale.json` | `build-data.js` 的重建产物（图标与「本站更新」条数变了） |
| `src/img/icons/`（3 张新图 + manifest） | `spell_warlock_demonsoul`、`flightstone-blue`、`inv_10_…trolltooth_color2` |
| `src/data/releases.json` | 网页「本站更新」补两条（分别指向 `39bf372` 与 `8022bf3`） |
| `docs/UI.md` | §3.60 新规格 + 改掉两条过期数字 |
| `docs/ASSET-GAPS-2026-10-20.md` | 本轮审计产出 |
| `docs/screenshots/check-2026-10-20/` | 实拍 |
| `ROLES.md` | 台账一行 |

## 九、交接状态

`- **W01-A / W01-B / W01-C 已执行完，待 Codex 独立验收**。不宣称已验收。
- 建议验收点：① 看这一轮的 `git diff`（实现 4 个文件 + 工具 4 个 + 数据 3 份）；
  ② 自己跑 `python3 tools/build-icon-map.py --check` 与 `python3 tools/route-smoke.py`，别只看我抄的行；
  ③ 开 `http://127.0.0.1:8821/#/world?t=zones` 滚到河林那一张，判"空框没了、这样读行不行"——这条只有人眼能判；
  ④ 判一句：**九张区域底图要不要作为上线硬门槛**。本轮一张都没补上，只改善了无图读法，
  按任务书 §上线判据那句，把布局改善说成"补图完成"是不行的；
  ⑤ 判一句：`docs/logs/**.log` 要不要加 `.gitignore` 例外，把完整日志进库（现在是摘要进库、全文只在本机）。
- 未做且不属于本轮：W02（动态页胶囊计数全 0 那个显示错误）、部署与 `base` 那条（§六 记了一条实测到的坑）、Q01B / Q02。
- 本轮**没有部署、没有推送远端**。`ROLES.md` 那一行与 Q01A 那轮同样处理：写进工作区但不提交，
  因为那文件里还叠着别的会话的未提交行。
- **一条仓库内务本轮没做，留给站主/Codex 定**：`docs/screenshots/` 的留存规矩是
  "新批次落库时把上一批 tar 进 `docs/screenshots-archive/` 再删原目录"。今天 `check-2026-10-20/` 已经落库，
  按规矩 `check-2026-10-19/`（Q01A 那批实拍）该归档删除——**但 Q01A 仍在验收中**，
  而且那是删 90 个已跟踪文件的大动作，我没有在别的会话还在写这个仓库时自己做。
