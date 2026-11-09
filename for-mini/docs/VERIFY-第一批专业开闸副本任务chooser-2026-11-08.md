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
