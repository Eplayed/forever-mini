# VERIFY · 第一批功能：专业开闸 + 副本任务段 + 职业怎么选（2026-11-08）

本轮角色：wow-dev ｜ 任务：站主拍板的第一批三个工作项（依据 `wow-forever-web/docs/PLAN-功能盘点与候选-2026-11-08.md` 第七节排序）｜ 产出：本文件 + 代码与线上批次

站主原话：「第一批就做 ①+②，把 ③ 作为搭头（数据量小、一页轻内容）」。

- ① 专业页开闸：拧 `flags.json` 的 `professions.on=true`（页面与数据通道 10-27 已就绪，只差开关）。
- ② 副本详情加任务段：`dungeon-quests.json`（35 座 / 396 条）在**构建时**并入副本详情分片，详情页多一张任务卡——与详情同一次请求，不发第二个。
- ③ chooser「职业怎么选」：新页 7 题问卷，客户端本地按权重算分给参考方向，不冒充官方结论。

## 一、改动清单

**分发层 `wow-forever-web/tools/oss-release.js`**
- `BASE_INPUTS` 加 `dungeon-quests.json`、`chooser.json`（真源哈希进基底清单）；`BUDGET_KB` 加 `chooser: 16`（实测 6.5 KB，余量给加题）。
- 副本任务并入详情：`det.quests = { summary, note, checkedAt, rows[] }`，只带界面字段（nameCn/nameEn/questLevel/reqLevel/xp/source）；pickupNpc 等缺得厉害的不发。构建卡口：`dungeon-quests.json` 里的 id 必须全在副本名单内、0 条任务直接构建失败（不许发空壳）。
- chooser 产物 `chooser/chooser.json` 走 `pushObj`，manifest `fetch.chooser` 注册（records=7）。
- **manifest 减脂**：`integrity.clientChecks` 九条长文案（每批重复约 1.7 KB，无任何消费方，grep 验证过）挪进脚本注释，清单留一行指针——不改这处，新加两个基底哈希会顶破指针清单 12 KB 预算。顺带把指针清单超预算的报错改成报实际 KB。

**客户端**
- `for-mini/services/oss-manifest.js`：SHARD_SPECS 加 chooser 条目（shape 校验：questions 数组、选项带 weight 对象、`meta.note` 含「不是官方」）。
- 新页 `for-mini/pages/chooser/`（四件套）+ `app.json` 注册。九职业中文名本地映射（rogue=潜行者）；逐题前进；结果页同分并列、top 之外取 3 名；「看它的天赋与技能」跳职业页；页头口径句来自数据下发；取不到问卷直说「要联网才能取」，不编题。
- `for-mini/pages/classes/index`：lead plate 后加整宽入口卡「不知道玩什么职业？」（带一句「本站整理，不是官方推荐」）。
- `for-mini/pages/dungeon/index`：首领名单卡与掉落卡之间插任务卡——`quest.summary`、逐条行（等级/需求等级/经验缺哪段不写哪段、英文名缺中文名标「译名待核」）、来源、`quest.note`；这座本没记录就写「任务线还没有记录，不猜」。
- `for-mini/pages/loots/index.js`：`buildId` 修为 `r.buildId`（原来误取 `r.batch`——那是元信息对象，页面字段从没写对过，m02 同源断言因此读不到批次）。

**开关**
- 真源 `wow-forever-web/app/data/flags.json`：`professions.on=true`、`since=2026-11-08`，note 记拍板依据。

**门禁脚本（都是断言改写，不是删）**
- `mini-m01-check.js` / `mini-m02-check.js` 加 `connectWithRetry`：9421 会话秒退（cli auto 报成功但监听只活几秒，2026-11-08 起本机规律）→ 连不上重拉 auto 再连，最多四轮。
- m02 三类断言按当前事实改写：
  - 倒计时两条（设备段）改条件式：launch 没到点块在且与 meta 同源、过了点整块消失（11-05 07:00 已开服，`cd=null` 是**正确行为**，原断言还钉着 `on===true`）。
  - 「没写死开服日期」剥注释再比（11-03 口径注释追加后落在旧剥法范围外，命中的全是注释里的开发记录——与「四张入口卡」那条同一处理先例）。
  - 抄死数字改数据驱动：技能总数 498→493（11-05 日更）改为「牧师那格与分片同源」对拍；`disc.disc.slice` 崩溃防护（11-02 撤文案后 loots 页已无 disclaimer 字段）。
  - 新增两条静态卡口：chooser 进批次（题目数与 `fetch.chooser.records` 同源、每题选项带权重、口径句在）、详情分片带任务段（summary+rows+checkedAt）。

## 二、验证证据

| 项 | 结果 |
| --- | --- |
| `oss-release build --env beta --check-identity` | rc=0，批次 **`999614801ac9`** 178 文件；抽查最大详情分片 blackrock-depths 14.2 KB 含 39 行任务（detail 预算 32 KB 未顶） |
| `oss-release-test` | 243/244（唯一红＝`.oss-env` 路径判定只在 Mac 布局成立，11-02 基线同一条，非本轮引入） |
| m01（假 OSS 全链路） | **111/113**；两条红＝断网缓存、切角铭牌像素（历史红，与上轮相同）；专业页 J 段全绿：13 专业可切、开关关着时进页只说「还没开放」且一个请求不发、首页入口卡随开关整块出现/收掉 |
| m02（真 bucket beta） | **112/112 全绿**。关键行：掉落同源 `{"页面":[1053,1021],"批次":{"rows":1053,"items":1021},"build":"999614801ac9"}`；倒计时 `{"cd":null,"past":true}`；chooser 7 题；任务段 39 条·2026-11-05；tabBar 仍三项、chooser 走二级页 |
| `upload --env beta --check-identity` | rc=0：**传 178 / 失败 0 / 不可变冲突 0**，指针 → `999614801ac9` 回读字节一致；开关对象随批发出（2.8 KB 回读 ETag 一致）。**回滚**：`node wow-forever-web/tools/oss-release.js rollback --env beta --to c1d8fdf09520` |
| 线上回读（curl） | 指针 `999614801ac9` ✓；`flags.json` professions.on=true ✓；`builds/999614801ac9/chooser/chooser.json` 7 题、kind=site-opinion、口径句 66 字 ✓；`builds/999614801ac9/dungeons/detail/blackrock-depths.json` quests 39 行+summary ✓ |

## 三、没验到的（不许口头带过）

1. **真机**：chooser 答题与结果页、副本页任务卡、专业页入口卡——全在代码包里，**要开发者工具重新上传一版代码才进真机**（PENDING_CODE_UPLOAD，与分享/起名/首页重排/倒计时同一次欠账，已积累五批改动）。
2. **chooser 交互实拍截图**：mp.screenshot 在这台 headless 会话持续 TMO（环境限制）；结构级证据靠 m02 设备段与静态卡口。
3. m01 的两条历史红（断网缓存、切角像素）本轮未查根因，沿用上轮定性。

## 四、给下一轮的挂账

- **PENDING_CODE_UPLOAD**：真机要看到本轮全部（chooser / 任务卡 / 专业开闸 / 分享 / 起名 / 首页重排 / 倒计时消失），只欠开发者工具上传代码一版；OSS 数据层不用再动。
- chooser 页权重表是本站主观整理（`meta.kind=site-opinion`、notRanked），升档或改题只动 `app/data/chooser.json` 重跑构建即可。
- 副本任务线 396 条的核对日是 2026-11-05，来源是白云飞整合开采（`DATA-任务名与掉落开采-2026-11-08.md`），questID 合并层还没接——任务段只列了它给的事实字段。

## 五、追记（2026-11-09）：野营从专业名单剔除

站主看真机截图后拍板：「专业与配方中，野营不是的话，去除掉」。野营（camping）在参考站有页面但不是配方表格、条目一直拆不出（0 条配方），摆进名单只会让玩家点进空页。

- **剔除做在整形层** [merge-professions.js](file:///d:/project/forever/wow-forever-web/tools/merge-professions.js)：`DROP_IDS` 过滤 + EN 表删 camping + `notCollected` 改写记拍板。upstream 快照不动——重抓 upstream 这里仍是唯一闸，名单不会漏回来。
- **数据链**：merge → merge-prof-sources（补回 xrProf 来源层，直接重跑 merge 会把它冲掉，链条顺序）→ build-data 过闸（12 专业 · 配方 1986 不变 · 无限新增 885 · 采集点 55）→ export-mini → 新批次 **`e2de279eb9af`**（177 文件 0 失败）→ 指针切过去，回滚位 `999614801ac9`。线上回读：professions 12 条、无 camping。
- **文案**：`app/data/meta.json` 两处（板块说明「13 个专业」→「12 个专业…野营剔除」、缺口清单记拍板）；小程序专业页注释同步。
- **门禁改写**（同"数据对、断言错"处理，不删断言）：m01 名单断言从抄死 13 改为**与分片现读同源**（`PROF_N`）；野营断言从「切到野营看空态」改写为「名单里没有它且 12 个」；开关剧本基线从"professions 关着"改成"开着"——关态路径改为段内主动拧关来演（收回路径反而多验一遍），测后还原断言跟着改。
- **验证**：m01 **111/113**（仅剩断网缓存、切角像素两条历史环境红，无新增）；网页侧 `npm run build` + `site-check --only prof_tiers,copy` **29/29**；小程序专业页 12 格、页头读数 1986/885/55 全对。
- 没验到的：真机重看（等 PENDING_CODE_UPLOAD 那一版代码，12 格名单随分片自动生效，无需再动数据层）。

## 六、追记（2026-11-09 第二笔）：任务行补「在哪接的」（接取 NPC 与地点）

站主原话：「pages/dungeons/index 副本关联相关任务，各个任务在哪接的地点、npc都显示出来」。实测真源覆盖率：**pickupNpc 336/396、pickupZone 300/396 有值**——11-08 并入详情分片时「pickupNpc 缺得厉害不发」的判断不成立（当时没实测覆盖率），这次补上。

- **分发层** [oss-release.js](file:///d:/project/forever/wow-forever-web/tools/oss-release.js)：`det.quests.rows` 补 `pickupNpc`/`pickupZone`（trim 后空值发 null，缺哪段不发哪段）。
- **页面** `pages/dungeon/index.js` questPack 拼 `pickup`（NPC · 地点）、`pickupNone`；wxml 任务行加「接取」一行（`.pick-k` 金色标签、正文字色摆 NPC·地点；两条都缺照实写「接取人还没记录，进游戏确认」，语气是"没记录"不是"没有"）；wxss 三个新类全令牌。
- **发布**：批次 **`c60a7d5cd7c8`**（构建 rc=0、重跑同源），指针已切，回滚位 `e2de279eb9af`。线上回读 blackrock-depths：39 行、接取有值 37/39、首条「罗克诺特的麦酒 ← 罗克诺特下士」。
- **门禁**：m02 静态卡口加强（每行都带 pickup 字段且批次内有值）＋ 新增详情页设备断言（进 blackrock-depths 读任务首行 pickup）→ **113/113 全绿**。
- 没验到的：wxml 渲染效果（automator 读的是页面 data 非像素，真机样式等 PENDING_CODE_UPLOAD 那版代码）；60 条无 NPC / 96 条无地点是源数据本身的缺口，留待实测补充，界面上已按"没记录"呈现。

## 七、追记（2026-11-09 第三笔）：详情页首领可点跳掉落 + 撤两句文案；图标与接取补全的源况

站主四条：首领图标、补接取数据、点首领跳掉落列表、撤「另一说法」「副本原画取自…」。

**做了的两件（代码改动，主包层，不涉 OSS 批次）**
- **点首领跳掉落**：详情页首领行 bindtap → `/pages/loots/index?dungeon={id}&dname={中文名}&boss={首领名}`；掉落页 onLoad 接参，refresh 后把物品的 sources 裁到命中的那座本那位首领（一件装备别处也掉时不混进来）；lead 卡下加筛选条「只看：xx · yy 掉的装备｜看全表 ×」可一键清除。bosses 组装补 `id` 字段。
- **撤两句**：wxml 删「另一说法：{{conflict}}」行与 `{{artNote}}` 行；js 删 `ART_NOTE` 常量、`artNote`/`conflict` 的 data 字段与赋值。**数据层不动**（`nameCnConflict` 照旧下发，hall-of-thanes 实测仍在）。

**没做成两件的源况（不编数据，挂账拍板）**
- **首领图标**：线上链路本身是通的——146 个有图首领地址拼得出、文件 200 可达；缺的 136 个里，源站清单（11-05 抓）确认**78 个源站就没有**（data-unknown）、58 个不在源站清单。但 `upstream/xr-boss-model.json`（10-21 采的插件索引）能按中文名对上 **98 个**缺图首领的客户端 CreatureDisplayInfo——从本机 Forever 客户端 CASC 取贴图可补，属新工作项（需客户端提取工具链 + 站主拍板素材来源，边界同 10-08 客户端原画决定）。
- **接取 NPC/地点补全**：60 条无 NPC、96 条无地点，实测是 **wclbox 源里那些条目本身就是空**；questie 快照只有 id/en/cn 三个字段、没有 questGiver——本地无第二源可补，按红线不编。要补需抓完整 QuestieDB（startedBy/zone 字段）或游戏内实测。

**验证**：m02 **115/115 全绿**（新增两条静态断言：首领行 bindtap+跳转参数拼法；两句撤下且 js 无残留）。m01 111/113（仅剩断网缓存、切角像素两条历史红）——过程中撞一次 **IDE 会话坏死**（reLaunch 全部停在 dungeon 页、portraitUrl 读出空串等不可能状态，49 条连锁假红），硬杀开发者工具进程重开即恢复，已在台账记手段。m01「分歧名两个都留」断言按撤口径改写：钉数据层 conflict 字段仍在 + 界面静态无这句，不再读页面 data。
**没验到的**：点首领跳转的真机点击（automator 只验了 data-id/bindtap/跳转 URL 拼法与 loots 筛选逻辑的页面数据层）；真机全部等 PENDING_CODE_UPLOAD。

## 八、追记（2026-11-09 第四笔）：真机跳转 bug 三处修复 + 列表页撤句 + 补两道断言

站主真机截图反馈三件事：① 点首领跳到掉落页**查不出任何东西**，筛选条显示 `%E9%B2%82…` 编码串；② 错误提示滚出 `[object Object]`；③ 列表页 `pages/dungeons/index` 也还有「另一说法：xx」（第七节只撤了详情页）。三个全是真 bug，根因各不相同：

- **① 解码缺失（主因）**：微信 `onLoad(options)` **不自动解码**——跳转时 `encodeURIComponent` 了 dungeon/dname/boss，接的时候必须自己 `decodeURIComponent` 解回来；旧代码直接用，`filterDungeon` 是编码串匹配不上任何 dungeonId，items 全空。修复：[loots/index.js](file:///d:/project/forever/for-mini/pages/loots/index.js) onLoad 加 `dec()`（带 try/catch，解不动原样放行）。
- **② error 对象上屏**：`String(r.error.message || r.error)` 在 error 没有 message 字段时出来 `[object Object]`。修复：新增 `errText(e)`（string 直取 / message / errMsg / JSON.stringify 兜底，截 120 字），refresh 的 errorText 走它。
- **③ 列表页撤句**：删 [dungeons/index.wxml](file:///d:/project/forever/for-mini/pages/dungeons/index.wxml) 52 行 `<text class="conflict">另一说法：…</text>`；m01「分歧名」断言同一口径扩到列表页（数据层 `nameCnConflict` 仍在 + 两页界面静态都无这句）。
- **顺手揪出第四个（交互缺口）**：复查时发现 `applyFilter` 在没有关键词时返回空列表——就算解码修好，首领跳转落地也只会看到「先输入要查的东西」，玩家还得再打一遍关键词才出清单，不符合"点首领看它掉什么"的本意。重排：`refresh` 恢复存全量 items，筛选裁剪挪进 `applyFilter`——带筛选参数进来就**落地直接列这一位掉的**（不输关键词）；没筛选保持原样不把一千行泼出来。wxml 空态跟着改：筛选模式下这位首领没收录掉落时照实说「还没有记录」＋引导看全表（不编不猜）。
- **跳转可靠性旁证（不修代码）**：本地批次全量对拍——201 个有掉落的首领名在详情分片与掉落表**逐字同名**，唯一例外是掉落表的「小怪」桶（详情页首领行里没有它，点不到），字符串拼写层无第二类分歧；详情页点了但掉落表没收录的首领（如诸王大厅 4/5 个）走「还没有记录」空态，是真实数据状态不是 bug。

**门禁**：m01 **111/113**（仅剩断网缓存、切角像素两条历史红，无新增）；m02 **116/116 全绿**——新增运行时断言（e7）：按 `onOpenBoss` 的真实编码方式带参进页，钉「参数解码回中文 + 落地直接列清单（不输关键词）+ 清单全部属于这位首领」，实测 `黑石深渊 · 铁炉堡公主茉艾拉·铜须` 5 件全命中。
**没验到的**：真机复测（本轮改动全在主包代码层，不发 OSS 批次；等 PENDING_CODE_UPLOAD 那版代码）；真机红条「现在没连上」的深层原因（可能是真机 `downloadFile` 合法域名未配，属 wow-ops 侧，等站主用修复版再测一次的反馈）。

## 九、追记（2026-11-09 第五笔）：首领头像线源况探明——客户端没有肖像文件，旧判决两处更正，渲染立项待站主拍板

站主点名「执行 3」（98 个缺图首领的头像）。结论先行：**这轮做不出来，也不该硬做**——把整条链探到底之后，答案是"客户端里不存在首领肖像贴图，唯一路径是从 3D 模型渲头像"，那是一条需要立项的渲染管线，且覆盖上限只有 136 缺里的 14–30 个。

**探明了什么（全在本机客户端与既有导出工作区，未动仓库数据层）**：
- `bosses/resolve.csv`（10-22 那轮的判决书）两处要更正：①它说"纹理被私服剥离"——错，`CreatureDisplayInfo.db2` 的 f27 列（`TextureVariationFileDataID[4]` 调色板数组）里 **4,391 行带真实纹理引用**，抽出的 fdid 在 listfile 全部有名、带 ekey 与字节长度（`Creature/<种族>/<皮肤>.blp`）；旧解析把 f27 当标量列读，读出来全空。②它说"30 个 M2 无纹理"——错在现代 M2 用 fdid 引用、本来就没有名字字符串与内嵌 BLP，"剥离"是误读。
- 但**肖像贴图确实不存在**：客户端没有按首领预渲的头像文件（`jobs-boss-verify.json` 里那些"肖像 fdid"逐一查实是 FriendsFrame/DressUp 界面图与身体皮肤，就是当年那轮在证伪）；经典首领头像是运行时渲 3D 模型的。DungeonsForever 插件媒体目录也没有肖像类资源。
- **覆盖量化**（136 缺）：91 个有 XR displayId 映射（45 个连映射都没有，其中一部分是译名分歧可桥）；91 里 65 个在安装包 CDI 表（上限 id 14207），26 个新本 displayId 不在安装包也不在 `_forever_/Cache/ADB` 热修缓存（新本模型 M2 倒是在 CASC 里，displayId→M2 的映射来源未解）；65 里只有 18 个有纹理引用，18 里 14 个 M2 已在 `dest-m2boss`。
- 渲染链两端其实都在：`exporter/dest-tex` 有贴图、`Blp2Png.cs` 有解码器、`viewer/` 是 three.js+headless chrome 的 GLB 截图机；缺的是 M2→GLB 转换与逐模型取景（怪物模型姿态/体型差异大，不能套用配装人形的机位）。

**为什么不硬做**：为 14–30 个首领搭一条逐模型调机位的渲染管线，属于多轮工作量，且剩下的 100+ 个依然没图——小程序首领行会出现"少数真头图＋多数占位"的混合态。要不要立项、做到哪算够（只做有完整纹理的 18 个？还是先做新本的？），需要站主拍板。本轮没有为"呈现"动任何界面代码（frontend-design 技能已加载，等素材成立再进页面）。
**没验到的**：M2→GLB 转换工具是否真的可复用（`offline-export/` 是那轮工程，未跑通验证）；新本 displayId→M2 映射的来源。探针脚本都在 `C:\GAME\_wowf-export-work\boss-portraits-2026-11-09\`（仓库外）。

## 十、追记（2026-11-09 第六笔）：挂账④ 收尾——完整 QuestieDB 第四源补接取 NPC 与地点，批次 `0451d1ceeb85` 已上线

站主点名「执行 4」：抓完整 QuestieDB 补 60/96 的接取 NPC 与地点缺口。第六节那轮落过结论"questie 快照无 questGiver"——这轮查明真因：**上一轮的 `questie-quests-cn.json` 只抽了每任务一行的稀疏标量行，而 startedBy（接取归属）在 baked TOC 里是另一类单独的行**（`X-Quest-<id>-2`，5,059 条），没抽所以"没有"。

**新抽取器** [extract-questie-full.py](file:///d:/project/forever/wow-forever-web/tools/extract-questie-full.py)：同一份本地插件 baked TOC（`C:\GAME\World of Warcraft\_forever_\Interface\AddOns\QuestieDB\QuestieDB_Forever.toc`，15.5 MB，Base64→zlib→CBOR），三类行型都拆——`X-Quest-<id>-S`（稀疏标量：英文名/最低等级/任务等级/种族位掩码/起始物品/zoneOrSort）、`X-Quest-<id>-2`（startedBy 位置数组 `[npc表, object表, item表]`＋字典变体 381 行按键 1/2/3 同义拆列）、`X-Npc-<id>-S`（12,078 条 NPC 名，注意键名是 `X-Npc` 不是 `X-NPC`）。产出 [questie-quests-full.json](file:///d:/project/forever/wow-forever-web/app/data/upstream/questie-quests-full.json)：任务 **5,232**（英文名 5,232／中文名 5,011／接取归属 4,745／zone 5,168），NPC **12,078**（英 12,078／中 12，中文名沿用既有 cn 快照不新造）；meta 带 `sourceStamp` sha256、`cnSnapshot` 出处、`startedByShape` 说明，extractedAt 2026-11-09。只取事实性标识符，任务目标文案/奖励/建议一概不抽（meta.takes 原文记档）。

**合并层** [merge-dungeon-quests.py](file:///d:/project/forever/wow-forever-web/tools/merge-dungeon-quests.py) 加第四源：`build_questie_index()`（中英名→qid、qid→行、npc id→名中文优先）＋ `questie_npcs()`（只取 startedByNpc，无名字条目跳过）＋ `fill_from_questie()` **两遍法**——第一遍按"名字桥＋任务等级一致"锁定（单名直接命中 292 条），从锁定行学出 npc id↔中文名、zone id↔中文名两张小表；第二遍拿学到的表消歧多候选（72 条里大半定上）。**只补空缺、绝不覆盖既有值**，补过的行记内部溯源字段 `npcFrom/zoneFrom`；涉及座加 prov 条目（url=Questie 官方仓库、note 写明"只补空缺/中文名优先/拿不到用英文原文不翻译"、checkedAt=快照 extractedAt）。

**实跑数字**（与 `dungeon-quests.json` meta.counts 现值核对一致）：桥接 **342/396**（没接上的 **54** 条照实留空——多候选消歧定不下与名字在 QuestieDB 里找不到的）；补接取人 **9**（其中 6 个只有英文原名，按红线不翻译直接用原文）；补地点 **63**（96 缺→**33**）；接取缺口 60→**51**；涉及 **18 座**副本。

**数据链与发布**：build-data 过闸（卡口拦下过 prov `url:null` 与正文脚本路径禁词，已修后通过）→ export-mini → `oss-release build --env beta --check-identity` 重跑同源 → 批次 **`0451d1ceeb85`** → `upload --env beta`（`WOW_ALLOW_CROSS_CREDS='1'`）**177 文件 0 失败**，指针已切。**回滚**：`node wow-forever-web/tools/oss-release.js rollback --env beta --to c60a7d5cd7c8`。

**线上回读**：dire-maul-east「铸造奎尔塞拉」接取人=博学者莱德罗斯（学到的中文名桥生效）；hall-of-thanes「永不安息的亡者」=Afadra Dunwall（QuestieDB 英文原名，不翻译）；玛拉顿地点缺口 0；多座抽查 103 行任务里地点有值 93／接取有值 88；分发层逐字段确认 `npcFrom/zoneFrom` 不外漏。

**门禁**：
- m01（上一窗口跑的干净单实例）：**111/113**，仅剩断网缓存、切角像素两条历史红。
- m02（真 bucket beta，直读批次 `0451d1ceeb85`）：三轮定性——第一轮 114/116（红＝dungeons 页两条像素测量"量不出来"）；第二轮 115/116（那两条绿了，红挪到职业详情断言量到导航中间态 `route:pages/dungeons/index`）；第三轮 **116/116 全绿**（EXIT=0）。**红在轮间漂移＝会话时序抖动的指纹，不是数据回归**：数据类断言（掉落同源 `build=0451d1ceeb85`、任务段、chooser、首领跳转）三轮全绿。
- 网页侧：DungeonPage.vue 本就渲染 pickupNpc/pickupZone（无需改码），`npm run build` 通过（dist 晚于数据 12 分钟）；`site-check --only dungeon_geo,data_versions` **29/29 全过**。

**没验到的（照实挂账）**：① 真机上任务卡"在哪接的"两列——数据已在线上批次里，但渲染这两列的界面代码在主包里，**要等 PENDING_CODE_UPLOAD 那版代码**（与第八节三处 bug 修复同一次上传）；② 剩余接取 51／地点 33——QuestieDB 里也没有（wclbox 源站本身为空的同一批），只能游戏内实测；③ 54 条消歧失败照实留空，没有拿"看起来合理"的候选充数。

## 十一、追记（2026-11-09 第七笔）：挂账① 收尾——首领头像本机渲染管线建成，首批 18 张上线，批次 `1bf6dcc67aed`

站主拍板「立项首领头像渲染管线」（`PROJECT_DECISIONS.md` 2026-11-09 节）：先做有完整纹理链的 18 个，逐份记来源链＋构建号＋哈希＋核对日，取不到的照旧占位不冒充。本轮把第九节探明的"两端在、中间缺"补成了完整产线。

**中间缺的那块补上了（格式探明，两个证伪）**：
- `offline-export/` **不是 M2→GLB 转换器**——它是楼层贴图那轮的"离线 CASC 提取器"（强制不用 CDN 回退），与 exporter 的区别只是回退策略。第九节"疑 M2→GLB 工程未验证"的猜测作废，转换器自建。
- `wow.export-0.2.19` 是 nw.js 打包成品（resources.pak），抠不出导出器源码，弃用。
- **M2 格式定案**（`boss-portraits-2026-11-09/probe_m2header.py` 等三个探针对拍）：MD21 容器 = magic + u32(md20_size) + 完整 MD20 载荷（version 272/274，WotLK 时代），所有头偏移 **+8** 才是正解；`CreatureDisplayInfo.db2` 的 f27 调色板 fdid 就是游戏里该 displayId 的实际贴图（M2 自身 TXID 槽 0 为 0，正是"由 CDI 调色板注入"的实证）；skin 也是容器（'SKIN' magic），段表 `0x04 顶点重排表 / 0x0C 三角形索引 / 0x14 每顶点附加表（渲染忽略）/ 0x1C submesh(48B: sid,level,vstart,vcount,istart,icount)`——submesh 首次定位在 0x1C 不是 0x24（0x28A0 处 48 字节对拍 vcount=873/icount=2532 全对上）。
- M2 提取缺口 4 份补齐（科技机器人 124329 / 刺鬃守卫 124208 / 温格 123225 / 基尔图诺斯卫士 124210，jobs-m2-boss2.json），**18 候选 = 16 份独立模型**：泽雷利斯/杉达尔/灰尘怨灵共用 m2_125223，前两者连贴图（125225）都相同，各渲各的账。
- 客户端构建随取随记：**1.60.1.70862**（`.build.info` Version 列，旧账里的 70532 是 10-28 那轮的构建）。

**产线**：[render-boss-portraits.py](../../wow-forever-web/tools/render-boss-portraits.py)（仓库内，吃仓库外提取产物）：M2+skin(LOD0)→静态 GLB（纯几何＋UV＋槽 0 贴图，无骨骼动画=绑定姿势，Z-up→Y-up，单 primitive 双面材质）→无头 Chrome 512×512 透明底截图→PIL 缩 256×256→webp→`app/img/art/bosses-m2/{bossId}.webp`＋`manifest.json`（displayId/m2/skin/texSlot0 三源 sha256＋成品 sha256＋构建号＋核对日＋回退说明）。质检卡口：非透明占比 4%–90%、色彩≥32，不过不落盘。
- **取景逐只调**：默认头胸特写（frac 0.18/span 0.60），逐张目检后修正两只——atal-alarion（裁头顶→frac 0.26）、targorr-the-dread（扁宽龟壳按默认算出来太远→span 0.45/frac 0.30/pad 1.0）；修正参数固化在脚本 `OVERRIDES` 表。
- 多槽贴图模型（石脊/温格/霍克等）本轮只挂槽 0——主皮肤在槽 0，逐张目检没有发现"缺配件"级别的失真；多槽精确映射（skin batches/texCombos）留待有真实需求再补。
- **盲眼守卫奥杜**渲出来是一桶绿液（它本体就是影牙城堡那只"哥布林浸液桶"模型），不是渲染错误，照实上线。

**18 张清单**（displayId→模型）：菌弗努斯 1070→124427（马形）、矿工约翰森 556→123105、盲眼守卫奥杜 522→123040、瑟拉吉斯 1816→123170、可怕的塔格尔 517→123324、卡姆·深怒 825→125559、科技机器人 7288→124329、剃刀沼泽刺鬃守卫 6078→124208、泽雷利斯 9293/杉达尔·沙掠者 9291/灰尘怨灵 9292→125223、温格 9418→123225、阿塔拉利恩 7873→125263、摩弗拉斯 7975→123747、霍克·巴什古德 11809→1134000、基尔图诺斯的卫士 10925→124210、黑衣守卫铸剑师 775→124272、石脊 7856→125796。逐张拼图人工目检两轮（`boss-portraits-2026-11-09/sheet_final.png`）。

**分发与页面**：数据基底 `dungeons.json` 18 条 `portrait` 写 `img/art/bosses-m2/{bossId}.webp`（apply_portraits.py 幂等写入）；oss-release 分发层 `useAsset` 自动剥前缀转 assets 相对路径＋哈希登记，**零代码改动**；页面 icon-cell 接图链路本来就在（有图出图、无图回落自绘块）。

**发布**：`oss-release build --env beta --check-identity` 过（重跑同源 buildId 一致、字节差异 0）；`assets --env beta` 素材 **107 传 0 失败**（18 头像＋此前欠账的 89 个被引用素材），全量 2358 个素材齐；`upload --env beta` 数据 **177 传 0 失败**，指针 → **`1bf6dcc67aed`**，回滚位 `0451d1ceeb85`；`verify --env beta` rc=0（175 文件逐个回读字节一致）。

**门禁**：
- m01：**111/113**。断网缓存、切角像素两条历史红照旧；**新红 1 条是断言过时**——"hall-of-thanes 首领全部无头像走回落"钉着挂账①之前的旧现实，而本轮恰恰给这座本的 infurnus 补了真头像。断言改写为**从 oss-preview 的 portrait 字段动态推导期望名单**（有图的比对 assets 地址、无图比对空串），端口也改从 `PORT` 取不再写死 9384——下一批补图不用再改断言。改后重跑 111/113。
- m02：**116/116 全绿**。
- 网页侧本轮不动（AGENTS：头像先小程序侧落地）。

**线上回读**（真 bucket）：`builds/1bf6dcc67aed/dungeons/detail/hall-of-thanes.json` 的 `dungeon.bosses[]` 里 infurnus.portrait=`art/bosses-m2/infurnus.webp`（其余 4 个未渲首领 portrait 空串照旧回落）；`assets/art/bosses-m2/infurnus.webp` HEAD 200，4388 B，image/webp。

**没验到的（照实挂账）**：① 剩余 118 个缺图首领（新本 26 个 displayId→M2 映射未解 + 无纹理引用的 47 个 + 无 XR 映射的 45 个）——管线本身已就绪，卡在映射来源与纹理覆盖，等解；
② 真机头像实拍——本地模拟器门禁已验（bosses 渲染、icon-cell 出图），真机走 OSS 域名，待站主下次真机预览顺带看一眼；
③ 多槽贴图精确映射——18 张逐张目检无失真才敢只挂槽 0，将来若有首领需精确到 skin batches 再补；
④ 断言的新期望仍依赖 `oss-preview/dungeons.json` 与分发层 useAsset 的转换约定（`img/`→assets 相对路径），约定变了断言要跟着改。

## 十二、追记（2026-11-09 第八笔）：站主真机三反馈——`[object Object]` 修复、掉落空态诚实化、头像扩展侦查（47 探 2 上），批次 `7b832b1fc141`

**起因**：站主真机截图三件事——① 副本详情任务卡第一行渲出字面量 `[object Object]`；② 点首领跳掉落页只见"还没有记录"；③ 首领头像大多没有（领主大厅 5 首领只有茵弗努斯有渲图）。指令"还差哪些没有做，完成他"。

**① `[object Object]`（真 bug，根因+双修）**：`dungeon-quests.json` 35 座的 `summary` 全是对象 `{faction,questCount,xpTotal,note}`，oss-release 的 detailRecord 一直整对象直发，wxml `{{quest.summary}}` 就渲成字面量。修复两端：分发层 [oss-release.js](../../wow-forever-web/tools/oss-release.js) 新增 `questSummaryText()` 把对象拼成"联盟阵营 · 4 条任务"直发字符串（新批）；页面 [dungeon/index.js](../../for-mini/pages/dungeon/index.js) `summaryText()` 判型兜底（string 直用/对象同拼法，旧批缓存不炸）。**m02 断言同步改写**（任务段 summary 从"必须是对象"改为"必须是可直渲的非空字符串"，断言旁留改写注），改后 116/116。

**② 掉落空态（真源缺口，不编）**：回查参考站 wclbox 自报领主大厅全本就"1 件掉落"（连首领数都写 4），questie 掉落快照对杜根·挽锤（npcId 261319）也无记录——真源就这么少，照实呈现。分发层 detailRecord 逐首领数 `drops` 计数下发；页面首领行两态：有货"看它掉什么 ›"/ 无货"收录的掉落还没记录 ›"（同 hint 色，靠文案区分，不新造令牌）。

**③ 头像扩展侦查（工作区 `boss-portraits-2026-11-09/extend_*.py` + `extend-verdict.json` 留档）**：118 个缺图首领全过一遍链路——xr 有 displayId 73 个；其中 46 个唯一 id 在本构建 CDI（24 个不在：达拉安城/领主大厅 4 首领/哀嚎新怪等**新内容真源缺口**，本地 CASC 与 10-22 提取件逐字节一致、非提取过时）；得 47 个候选，M2 全部提取到位，**TXID chunk 全部自带贴图 fdid**（f27 全空，与首批正好互补）。但渲完 65 张目检暴露大问题：10 个人形首领渲出**同一张脸**。溯因：这批 displayId 在本构建被映射到 **HD 角色基础模型**（HumanMale_HD/DwarfMale_HD/NightElfFemale_HD…），真脸靠运行时部件组装，TXID 里只有跨 fdid 字节相同的**占位 stub**（44900 B 一群）；且映射荒诞——奥妮克希亚→暗夜女、达格兰大帝→矮人**女**、阿库麦尔→亡灵女。**定案：渲通用人模=冒充首领长相，不干。**质检规则（listfile placeholder 标签 + 跨 fdid 文件字节指纹）剔 45（43 HD 基础模型 + 2 地精身体贴图占位），**只收 2 张真·专属模型**：苏斯（克苏恩眼杆真生物模型+真贴图）、档案管理员加尔福特（经典骷髅模型+真皮肤，取景覆写 span 0.38/frac 0.12 收到头肩）。头像总数 18→**20**，apply_portraits 幂等写入 dungeons.json（改 2 条）；渲染脚本 manifest 改**整表重建**语义（有失败不覆写旧 manifest），头部说明同步。工作区脚本踩坑留痕：listfile 第二列以后是标签/哈希元数据，按整行存会让 `endswith('_hd.m2')` 永假（芬鲁斯/哈扎斯漏网即此因，已修）。

**发布**：首次 build 撞"导出产物与基底不配套"卡口（portrait 改了基底）→ 先 `export-mini.js` 再 build 过；批次 **`7b832b1fc141`**（重跑同源字节一致），`assets` 传 3（2 新头像+1）跳 2358，`upload` 177 传 0 失败，指针 → `7b832b1fc141`，回滚位 `1bf6dcc67aed`；`verify` rc=0（175 文件逐个回读 0 问题）。

**门禁**：开发者工具会话坏死（Connection closed），按既有处置硬杀 wechatdevtools 进程重开后过。m01 **111/113**（断网缓存、切角像素两条历史红照旧，无新红）；m02 断言改写后 **116/116**。

**线上回读**（真 bucket）：`builds/7b832b1fc141/dungeons/detail/hall-of-thanes.json` `dungeon.quests.summary`=**"联盟阵营 · 4 条任务"**（字符串，①修复上线实证）；`dungeon.bosses[]` drops = faldrim 0 / infurnus 0 / plunder 0 / **durgen 1** / plunder-2 0（与 wclbox 真源一致，②两态的数据底座）；`assets/art/bosses-m2/` 下 tsu-zee.webp 4498 B、archivist-galford.webp 8584 B、infurnus.webp 4388 B 全 HEAD 200。

**没验到的（照实挂账）**：① 领主大厅 4 首领头像——displayId（142826 等）不在本构建 CDI，本机渲不出真脸，照实走"没有这张脸"回落；26 个同因首领 + 45 个 xr 无 displayId 首领同账；HD 组若将来构建补了真贴图，管线重跑即出（质检规则会自动放行）；② "看它掉什么/还没记录"两态只有代码走查、未加自动断言（m02 现有任务段/掉落断言未覆盖这一格）；③ 真机实拍本轮三处改动（任务卡汇总行、首领行两态、2 张新头像），待站主下次真机预览。

