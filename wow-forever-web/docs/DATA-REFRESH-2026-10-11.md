# 数据重抓与差异报告 · 2026-10-11（wow-data）

本轮角色：wow-data ｜任务：把落后的数据源重抓到最新并出差异报告 ｜上游发布目录：`_shuju/r-1791702948979`（`foreverBuild 1.60.1.70338`）
前置报告：`docs/DATA-FRESHNESS-2026-10-11.md`（只读盘点，本轮按它行动）
配套源状态：`docs/wow-infinite-sources.md` 第九节 ｜ 逐字回查证据：`docs/DATA-AUDIT-2026-10-11.md`
跑法说明：**没有用 `tools/refresh.sh <场景>`**（每个场景末尾都挂 site-check 界面门禁），一律照 `refresh.sh` 里的步骤逐条跑、去掉 `gate`；界面门禁留给主会话统一跑。

---

## ① 一句话结论

**追上来了**：wclbox 解包线的 `changes` / `world` / `legacy` / `dungeons` / `prof` 五条全部切到 `r-1791702948979`（客户端 70235 → **70338**），wago 排队表也跟到 70338；官方中文两篇新深度解析（法师与萨满祭司、潜行者与术士）已采进 `abilities.json`，**38 → 86 条、每条整句照录并逐字回查通过**。
**没有追上来（有意停手）**：**天赋线只跑了抓取器、没跑 merge**——`src/data/talents/*.json` 一个字节都没动，所以 473 个节点、91 条译名分歧、13 条待 L0 全部原地不动。原因见第四节：上游客户端确实改了 31 处，但 `tools/merge-upstream.js` 现读会**用 2026-10-07 的旧译名快照去对齐 70338 的格位**，而且它把采集日期与分歧条数写死在代码里，跑一次就等于把没证据的话写成事实。**状态：待用户确认。**
**顺带查出两处真问题**：传承挑战点数在客户端里自相矛盾（规则栏 16 点 vs 明细 65 条各 1 点）；四个生成器一重跑就把「上游 / 口径 / 结构化 / 字段 / mapId」这类维护者措辞盖回产物（`DATA-MAINTENANCE.md` 第四节警告过的幂等坑，这次轮到 `merge-world` / `merge-changes` / `merge-professions` / `scrape-wclbox-prof`）。已按"改生成器不改产物"修掉。

---

## ② 改前 / 改后数字对照

### 2.1 门禁与派生文件

| 门禁 | 改前 | 改后 |
| --- | --- | --- |
| `node tools/build-data.js` | 退出 0（基线，抄录见下） | **退出 0，校验通过** |
| `python3 tools/audit-translations.py --strict` | 未跑（本轮起点） | **退出 0**：命中 1469 / 排版空格才命中 44 / 未命中 2（都是 L2，没声称官方）/ 结构问题 0 / **声称官方却核不到 0** |
| `python3 tools/data-status.py` | 6 项能补 / 2 项人工核 / 10 项等外部 | **5 项能补** /2 /10（"比基底数据旧的派生文件"那条已消掉） |
| `tools/site-check.py`、`app-parity.py`、`export-mini.js` | — | **本轮未跑**（任务要求门禁由主会话统一跑） |

### 2.2 覆盖率与各板块条数

| 项 | 改前 | 改后 | 说明 |
| --- | --- | --- | --- |
| 全站覆盖率 L0 / L1 / L2 / L3 | 366 / 114 / 360 / 2（共 842，L0 43.5%） | **366 / 114 / L2 360 / L3 2（不变）** | 这个计数器只数带 `level` 的词条（术语、副本、天赋节点、区域…），`abilities.json` 不在其内；官方新稿带来的提升体现在 2.3 的逐职业完整度上，不在这里 |
| 成品词条（术语+副本） | L0 366 / L2 1 / L3 2，共 369 | 不变 | |
| 天赋节点 / 与官网中文一致 | 473 / 460（97.3%） | **不变**（未 merge） | 见第四节 |
| 译名有分歧的天赋节点 | **91** | **91（不变）** | 未 merge |
| 中文名没核到 L0 的天赋节点 | **13** | **13（不变）** | 证据已到位（官方稿已到），转换要等天赋 merge |
| 客户端改动清单 | 964 条（天赋 544 / 法术 420）· 有变化 751 · 新增天赋 112 · 改动天赋 306 · 移除 77 · 法术有变 256 | **965 条**（天赋 **545** / 法术 420）· 有变化 **753** · 新增天赋 **113** · 改动天赋 **304** · 移除 **79** · 法术有变 **257** | 与客户端自报计数逐项一致（脚本现读） |
| 技能四态（官方中文） | **38** | **86**（新增 54 / 改动 17 / 改名 14 / 移除 1；丢弃 0） | 法师 11、萨满祭司 9、潜行者 7、术士 21 = +48 |
| 传承：专长 / 槽位 / 未公开 / 进度奖励 | 21 / 27 / 6 / 4 | 不变 | |
| 传承：挑战条数 | **65** | **66** | 新增 #64283「参与过《魔兽世界：无限》测试」 |
| 传承：点数合计 | **65** | **81** | 客户端 `launch_earnable_total` 同步变；与明细点数之和能对上 |
| 副本（本站条目 / 上游卡片） | 38（新增 9）/ 上游 35 座 | 不变 | 首领 228、掉落 1050 也不变 |
| 排队条目 `queue.json` | 51 条（本站没名单 16） | 51 条（16） | 客户端表 109 条活动 / 5 个类别，逐字段 0 处不同 |
| 专业 / 配方 / 无限新增配方 / 采集点 | 13 / 1990 / 889 / 55 | **条数不变** | 但有 24 处**取值**被客户端改了，见 3.1 |
| 世界：区域 / 稀有 / 书籍 | 44（新增 4）/ 36 / 36 | 不变 | 内容级差异 **0**，见 3.2 |
| 图标映射 / 本地图标文件 | 509 条 / **2012** 张 | 509 条 / **2013** 张 | 新增 `inv_misc_gift_01.jpg`（官方 CDN 实测 200 后转存，走 `fetch-icons.py`） |
| 缺图登记 | 83 个键 | **83 个键** | 中途因新挑战项升到 84（`inv_misc_gift_01`），从官方 CDN 取到后回落到 83；`changes 1 / dungeons 1 / legacy 2 / professions 77 / world 9` |
| 全站搜索索引 | 4302 条 / 19 类 | **4351 条** / 19 类 | |
| 数据基线 `meta.dataBaseline` | `forever-beta 1.60.x（未逐条核对）` / `checkedAt 2026-10-07` | **`无限 Beta 客户端 1.60.1.70338（天赋树成品仍是两份第三方资料站 2026-10-07 的对齐结果）`** / `checkedAt 2026-10-11` | 溯源页与首页会显示这句话 |

### 2.3 逐职业资料完整度（`scale.json` 的 `classRank`，官方支撑条数）

| 职业 | 改前 official | 改后 official | 排名变化 |
| --- | --- | --- | --- |
| 术士 | 52 | **73** | 7 → **5** |
| 法师 | 53 | **64** | 6 → 6 |
| 潜行者 | 53 | **60** | 5 → **7**（分母也涨了） |
| 萨满祭司 | 50 | **59** | 9 → **8** |
| 战士 | 95 | 95（总数 197→198，share 48.2→48.0） | 3 → 3 |
| 猎人 / 德鲁伊 / 牧师 / 圣骑士 | 125 / 119 / 80 / 50 | 不变 | 圣骑士由 8 → **9**（垫底，只有它没有中文深度解析） |

---

## ③ 逐源实际差异（不是"预计"，是跑完对比出来的）

对比方法：`git show HEAD:<产物>` 或 `/tmp/upstream-backup-2322/` 里的旧上游，与新产物按 `id` / 坐标逐字段 diff。

| 源 | 结果 |
| --- | --- |
| `changes`（改动清单） | **+4 / −3 条，9 条取值变化**（详表见 3.1） |
| `world`（世界线） | **内容级差异 0**：44 区域逐字段（名称 / 等级上下限 / 阵营 / mapId / 图标键）0 处不同；36 稀有、36 书籍同理；只有 provenance 日期与生成器措辞变。顺带把盘点没做的 `_shuju/<r>/map-zones.json` 内容级 diff 补完了 |
| `legacy`（传承） | 专长 / 槽位 / 奖励 **0 处**；挑战 **+1 条**（#64283）+ **规则字段自相矛盾**（见 3.3） |
| `dungeons`（副本） | 详情页 35 座 / 232 首领 / 1050 掉落 **成员与归属 0 处变化**；卡片 35 张 **逐条一致**（含等级区间，抓取器打印的 13–20 等是本来就有的值）；`_shuju` 排队元数据 35 条只有 `sourceUrl` 的构建号变。成品 `dungeons.json` **0 处**、`queue.json` 0 处 |
| `prof`（专业） | 条数不变，**24 处取值被客户端修正**（见 3.1 下方） |
| `db2` 排队表（wago.tools） | 构建 70334 → 70338，**109 条活动 + 5 个类别逐字段 0 处不同**；另按盘点遗留项做了 CSV 逐字节对比：**两份 CSV md5 相同**（`22312076a6e45546a340e2a0006caa3d`，各 9265 字节）→ 盘点里"没逐字节 diff"那条已闭合 |
| `talents`（天赋上游，只抓不合） | **31 处差异**（见 3.4），成品未动 |
| 官方中文两篇新稿 | 48 条新记录，全部逐字回查命中（`--strict` 退出 0） |

### 3.1 改动清单的 9 条取值变化 + 7 条增删（客户端 70235 → 70338）

新增 4 条：`calc-warrior-fury-lingering-rage`（乱舞）、`calc-warrior-fury-furious-precision`（狂怒精准）、`calc-warrior-fury-gore-drinker`（饮血者）、`calc-druid-feral-combat-natural-instinct`（自然本能）
移除 3 条：`calc-warrior-fury-boundless-rage`（无尽怒气）、`calc-warrior-fury-precision`（精准）、`calc-druid-feral-combat-predatory-instincts`（掠食本能）
取值变化 9 条：钢铁意志 所属系 狂怒 → **防护**；强化顺劈斩 改动 → **移除**（上限 3 → 无数据）；坚韧 改动 → **移除**（5 → 无数据）；破胆怒吼 未变 → **改动**；狂暴之怒 未变 → **学得更早**；旋风斩 未变 → **改动**；荆棘术 / 水栖形态 改动 → **未变**；术士 `warlock-decimation` 名称 灭杀 → **屠戮**。

### 3.2 专业的 24 处取值变化

2 条配方材料换人（炼金术「大地精华」材料由 生命精华 → **火焰精华**；「水之精华」由 死灵精华 → **大地精华**）+ 22 条技能四档门槛（橙/黄/绿/灰起点）被客户端改写，如工程学「炸弹宠物」绿档 205 → 207 / 灰档 205 → 210、烹饪「宁神茶」黄档 25 → 30、绿档 45 → 37。**只取数值与物品名，没复制任何描述文案。**

### 3.3 传承点数：客户端自己前后对不上（新未决项）

`_shuju/r-1791702948979/legacy.json` 的 `rules` 现在写 `point_per_challenge 16`、`launch_earnable_total 81`；
但它自己的 66 条挑战明细里 **65 条 `points` 是 1**、只有 #64283 是 16，**65 + 16 = 81 恰好等于它给的合计**。
也就是"每项 16 点"这个说法被它自己的明细否证。处置（两个都留、不静默取舍）：

- `meta.rules.pointPerChallenge = 1`（界面把它写成"每项 N 点"，必须等于明细的普遍值，否则就是假话）
- `meta.rules.clientRulePointPerChallenge = 16`（客户端那个说法原样留着，带同一份 provenance）
- `meta.rules.rulesConflict`（一句话写明两个说法与合计怎么对上的）
- `meta.rules.pointVariants = [{points:16, count:1, ids:["64283"]}]`（偏差逐条声明）
- `build-data.js` 的这条断言从"每条点数必须等于规则值"改成"**偏差必须在 `pointVariants` 里声明过**"，并把"上游自报合计"从比条数改成**比点数之和**（旧数据每项 1 点时两者相等，所以这个口径混用一直没暴露）。

### 3.4 天赋上游的 31 处差异（已抓到 `src/data/upstream/`，**没并进成品**）

| 职业 | 差异 |
| --- | --- |
| 战士 | **结构重排**：节点 53 → 52（狂怒 +乱舞 / 防护 +强化血性狂暴；−无尽怒气 −强化狂暴之怒(移位) −坚城）；按格子对齐出 **12 处名称变化**（余怒、狂怒精准、饮血者、钢铁意志换位、预知换位、强化复仇换位…）与 **12 处图标键随之变化** |
| 术士 | 恶魔学识第 1 行 0 列：灭杀 → **屠戮** |
| 德鲁伊 | 野性战斗第 4 行 5 列：掠食本能 → **自然本能** |
| 圣骑士 / 猎人 / 潜行者 / 牧师 / 萨满祭司 / 法师 | **0 处**（节点数、系名、名称、图标全一致） |
| 系名（专精名） | 九职业三棵树的小标题**全部未变**；潜行者仍是"奇袭 / 战斗 / 敏锐"（早于本轮就是这样，不是这次改的） |

---

## ④ 为什么停在天赋 merge 之前（**待用户确认**）

任务要求"没有明确证据不要执行 merge"。跑抓取器之前我先取证，结论是**证据够证明客户端确实改了，但不够支撑"照现在这条链 merge 出来的成品"**，因为合并器本身会把没证据的话写成事实：

1. **它不现读两份工具站。** `tools/merge-upstream.js` 的判断是"本地快照存在就不重抓"（`if (!fs.existsSync(fFile))`），而 `src/data/upstream/fengshen-*.json` / `nieyi-*.json` 是 **2026-10-07** 的快照。我现读这九页与存档对比，得到 **110 处不同**：战士 15 处改名 + 7 处点数上限变化 + 系名 狂暴 → 狂怒；其余八职业多为纯译名改写（元素专注 → 元素集中、奥术专注 ↔ 奥术集中 互换、掠食者之刃 → 掠食者之锋、神御之盾 → 神圣庇护…）。**直接跑 merge = 拿 10-07 的旧译名去对齐 70338 的格位**，产出一棵混合了两个客户端版本的树。
2. **它把日期与条数写死在代码里。** 跑一次就会把 `collectedAt: '2026-09-13（该站自述采集日），本站对齐于 <今天>'`、`nameConflict: 89`、`nameVerified: 114` 盖进 `meta.json` 与九个天赋文件——两份工具站的存档文件**根本没有采集日期**（盘点已列为历史欠账），这句话我们没有依据；`89` 与当前数据的 **91** 条分歧也已经不符。**声称的日期与条数核对不了，就是编事实。**
3. **爆炸半径不在本任务范围内。** merge 会重写 9 个 `src/data/talents/*.json` + `meta.json`，随后 `talent-preview.json`、`search.json`、图标批次一起变；主会话刚提交界面第三批（远端 `c44463c`），`site-check.py` 的断言总数与两栈对拍都在那条基线上。现在把树结构改掉（战士 −1 节点、12 处改名），界面回归和截图要重来一轮。
4. **值得先行的替代路径**（供拍板，二选一即可）：
   - A. 先补 `merge-upstream.js`：① 加 `--refresh` 或改判断条件强制现读；② 抓取时把 `scrapedAt` 写进 `fengshen-*.json` / `nieyi-*.json`；③ 把 `collectedAt` / `nameConflict` / `nameVerified` 改成从实际数据算出来，不再写死。然后一条链跑完 `talents` 场景（`scrape-wclbox-dom --what talents` 已完成）+ 图标 + 界面门禁。
   - B. 先只做战士一个职业（唯一有结构变化的），另八个职业等两份工具站的现读快照与官方稿对完再并。

**13 条待 L0 与 91 条分歧本轮不变**，原因就在这里：证据（官方两篇稿 + 70338 客户端）已经到手，但把证据写进 `talents/*.json` 的那一步需要先修合并器。

---

## ⑤ 新出现的分歧与未决项（逐条，都要人拍板或进游戏）

| # | 事项 | 证据 | 状态 / 该谁定 |
| --- | --- | --- | --- |
| 1 | **潜行者第一棵树：奇袭 vs 刺杀** | 官方 24310968 小标题写**奇袭**（正文出现 7 次）；客户端解包（`/tianfu/rogue` 与 `changes.json` 的系名）也写**奇袭**；两份第三方工具站（fengshen 存档与 10-11 现读、nieyi）都写**刺杀**；本站 `src/data/talents/rogue.json` 的 `trees[0].nameCn` = **刺杀** | **待用户确认**。字段承载：节点级早已有 `nameCn` + `nameAlt` + `nameConflict`（界面红框两个都显示）；**树级只有一个没人读的 `nameAltUpstream`**——`rogue.json` 的 `trees[0].nameAltUpstream` 已经存着"奇袭"，但 `app.js` 与两个体检脚本都不读它，玩家看不到。建议：树级统一成 `nameAlt` + `nameConflict`（与节点级同名同义）并让天赋页显示；`nameCn` 该不该换成官方的"奇袭"是编辑决策，不是数据缺失，**请拍板后由主会话改 `merge-upstream.js` / `merge-talents.js` 与渲染** |
| 2 | **萨满第一棵树：元素战斗 vs 元素** | 官方 24302097 写**元素战斗**（出现 4 次）；客户端 `/tianfu/shaman` 的格位标题写**元素**；fengshen 写**元素战斗**；本站显示**元素战斗** | 同上，待用户确认（同为树级字段缺口；官方与工具站一致、客户端是短写，倾向保持"元素战斗"并在 `nameAlt` 记"元素"） |
| 3 | **术士天赋：灭杀 vs 屠戮**（本轮客户端改名） | 官方 24310968 写**灭杀**（第 4 层新增天赋那条整句已进 `abilities.json`）；客户端 70235 = 灭杀、70338 = **屠戮**；fengshen 10-07 存档写 屠戮、10-11 现读写 灭杀；nieyi 写 灭杀 | **数据层已经正确**：`talents/warlock.json` 该节点 `nameCn` 灭杀 + `nameAlt` 屠戮 + `nameConflict: true`，两个都留。要人定的是：正式服上线后官方会不会跟着改词——属"等外部" |
| 4 | **德鲁伊：掠食本能 → 自然本能**（本轮客户端改名） | 客户端 70338 写 自然本能；本站该节点 `nameCn` 掠食本能、`nameAlt` 丛林之王（第三方站之间的旧分歧）；官方德鲁伊稿两个词都没写过 | **没进成品**（要天赋 merge）。merge 后这格会有三个说法并存，`nameAlt` 只有一个槽位——**需要用户定：加 `nameAlt2` 还是改用数组**。现状：不动 |
| 5 | **传承每项挑战给几点，客户端自相矛盾** | 见 3.3：规则栏 16、明细 65 条各 1 点、合计 81 = 65 + 16 | 数据层已按"两个都留 + 偏差声明"落好。**但界面文案有错**：`src/js/app.js` 第 2431 行会把 `pointPerChallenge` 印成"每项 16 点"、第 2456 行又把同一个字段读成"每完成 16 项挑战得 1 点"——**同一份数据两处口径相反**，且第 598 行还写死了"65 项挑战各给 1 点"（现在 66 项）。要主会话改文案，进游戏之前该字段建议显示"待实测"而不是任选一个说法 |
| 6 | #64283 的名称带商标词 | 客户端原名就是「参与过《魔兽世界：无限》测试」，`nameCn` 照录自解包 | **交 wow-ops 判**：红线要求站名/素材避开商标词，但这是客户端里的既有名称、不是我们起的。要定的是页面上原样显示还是写成「参与过《无限》测试」并保留原名注记 |
| 7 | 3 座副本卡片自报首领数与名单条数仍对不上（达拉然、黑暗深渊、诺莫瑞根）；黑暗深渊与诺莫瑞根本轮**客户端名单比我们的少 3 + 1 个首领** | `merge-dungeons.js` 按既有做法保留我们的名单不跟着删，并把差额报出来 | **要人工进游戏数**，本轮未动（不猜） |
| 8 | Beta 关闭时间两源仍分歧 | 官方 Beta 公告写国服 Beta「10 月 6 日至 10 月 26 日」；`_shuju/<r>/meta.json` 写 `betaCloseAt 2026-10-21T00:00Z` | 两个都留，等外部（盘点已记，本轮未变） |
| 9 | 四个生成器一重跑就把维护者措辞写回产物 | 首次重跑 `merge-world` / `merge-changes` 后 `build-data.js` **报 14 条禁词**（世界线 11 条、改动清单 3 条），`merge-professions` / `scrape-wclbox-prof` 另报 3 条 | **已修生成器**（`merge-world.js` 16 处、`merge-changes.js` 4 处、`merge-professions.js` 2 处、`scrape-wclbox-prof.py` 1 处、`merge-legacy.js` 规则段重写），并验证六个产物**重跑字节一致**（幂等）。这是 `DATA-MAINTENANCE.md` 第四节那个坑的第二、第三次复发，**建议在文档里把这两条链补进"已知复发点"清单**（文档归主会话） |
| 10 | 两份工具站的存档文件没有采集日期 | `fengshen-*.json` / `nieyi-*.json` 无 `scrapedAt`；10-11 现读与 10-07 存档差 110 处 | 属于第 4 节 merge-upstream 改造项①，未单独动 |

---

## ⑥ 这次没验到、需要进游戏或人工确认的

1. **两篇新官方稿的发布日期**：列表页与文章 SSR 里都没有可靠的发表日（正文只有定档 11 月 5 日、公测 10 月 6 日），所以 `abilities.json` 里那 48 条的 `checkedAt: 2026-10-11` 是**本站核对日**，不是官方发布日。要定发表日得用真实浏览器渲染列表页。
2. **48 条官方条目里的层数与里程碑**（`tierHint` / `milestone`）是从整句里读出来的数字，**没有和游戏里的树逐格对过**；官方"第 4 层新增天赋"这类说法与实际格位是否一致，只有进游戏能定。
3. **传承点数到底怎么给**（第 3.3 / ⑤-5 条）：客户端两个说法谁对，必须进游戏做一遍挑战看结算。
4. **两份工具站是否已随 70338 更新**：fengshen 我只逐职业对比了名称与点数（9 职业 110 处差异，其中纯译名改写与客户端改名混在一起，**分不了类**——要分清得逐条回客户端源看有没有那条天赋）；nieyi 只逐字核了战士一页（现读 10/10 命中 70338 的新名）。其余八职业没做 nieyi 现读对比。
5. **图标 CDN 在 70338 下的覆盖**：本轮只补了传承那 1 个新键（`inv_misc_gift_01` 实测 200 已存；`inv_tabard_legacyc60_b_01` 实测 403 → 仍登记缺图）。**没有全量重测 83 个缺键**在新 build 下是否补上了天裔 / 新物品图标。
6. **`_shuju/<r>/chengjiu.json`（成就 46 条）与 `map/<slug>.json`（单图兴趣点、飞行线）仍未接**——本轮只重抓已接的板块，没扩板块。
7. **界面侧完全没验**：`site-check.py`、`site-check --app`、`app-parity.py --strict`、`visual-check.py --check`、`export-mini.js` 都没跑（按任务分工留给主会话）。**本轮改了数据但没有一张新截图**，`传承`、`最新动态`、`技能四态`、`资料完整度排行` 四页的文字都可能需要跟着数据改（⑤-5 那处文案错就是例子）。
8. **`src/data/releases.json` 没补条目**（任务明令不许动）。玩家可见的"本站更新"需要在主会话那轮补一条，指向本轮的数据提交。

---

## ⑦ 备份与回退

**备份路径**：`/tmp/upstream-backup-2322/`（35 个文件，2.9 MB，抓之前的 `src/data/upstream/` 全量副本）
抽样校验：备份里的 `wclbox-changes.json` md5 = `12805403ecf3c45ae404f0cb74bd05b8`（与重抓前工作区一致）。

**回退（回到本轮开始前的状态）**：

```bash
cd /Users/zhangyajun/Documents/project/wow-forever/wow-forever-web
# 1) 成品与派生文件回到 HEAD
git checkout -- src/data src/img/icons
# 2) 上游快照还原
rm -f src/data/upstream/*.json
cp -R /tmp/upstream-backup-2322/. src/data/upstream/
# 3) 本轮新增的图标文件（备份目录里没有，靠 git 删不掉——它是 untracked）
rm -f src/img/icons/inv_misc_gift_01.jpg
# 4) 生成器与工具的改动（4 个 merge / 1 个 scrape / build-data / data-status / extract-abilities / meta.json）
git checkout -- tools/merge-world.js tools/merge-changes.js tools/merge-legacy.js \
  tools/merge-professions.js tools/scrape-wclbox-prof.py tools/build-data.js \
  tools/data-status.py tools/extract-abilities.py src/data/meta.json docs/wow-infinite-sources.md
# 5) 复跑校验，确认回到基线
node tools/build-data.js && python3 tools/audit-translations.py --strict
```

**只回退某一条线**：`git checkout -- src/data/<板块>.json` + 从备份目录拷回对应 `upstream/wclbox-<板块>.json`，再 `node tools/build-data.js`。
**天赋线本来就是零改动**，不需要回退：`git diff --name-only src/data/talents/` 为空。
**本轮新增文件**：本报告、`docs/DATA-AUDIT-2026-10-11.md`（逐字回查报告，脚本自动写）、`src/img/icons/inv_misc_gift_01.jpg` + `manifest.json` 更新。

---

## ⑧ 复跑清单（命令按本轮实际执行顺序）

```bash
cd /Users/zhangyajun/Documents/project/wow-forever/wow-forever-web
cp -R src/data/upstream/. /tmp/upstream-backup-$(date +%H%M)/     # 先备份
node tools/build-data.js                                          # 改前基线（只读派生+校验）

python3 tools/scrape-wclbox-changes.py && node tools/merge-changes.js
python3 tools/scrape-wclbox-shuju.py     && node tools/merge-world.js
python3 tools/scrape-wclbox-legacy.py    && node tools/merge-legacy.js
python3 tools/scrape-wclbox.py --what dungeons --write
python3 tools/scrape-wclbox-dom.py --what cards
python3 tools/scrape-wclbox-shuju.py --group dungeons
python3 tools/fetch-db2-groupfinder.py   && node tools/merge-dungeons.js
python3 tools/scrape-wclbox-prof.py --write && node tools/merge-professions.js

python3 tools/scrape-wclbox-dom.py --what talents                 # 只抓，不 merge（见第四节）
python3 tools/extract-abilities.py --write                        # 官方两篇新稿
python3 tools/build-icon-map.py
python3 tools/fetch-icons.py --from-json src/data/legacy.json --field iconKey
python3 tools/build-icon-map.py

node tools/build-data.js                    # 退出 0
python3 tools/audit-translations.py --strict   # 退出 0
python3 tools/data-status.py                # 报告，不拦人
```

`refresh.sh` 里 `talents` / `official` 两个场景末尾还各挂了 `fetch-icons.py --from-json src/data/talents/hunter.json`，本轮没跑（天赋没 merge）。

---

## ⑥ 同日补：用户拍板后，天赋线合并完成（2026-10-12）

用户三条决定：**① 天赋合并要做；② 名称参考 `https://wowforever.wclbox.com/fashu/rogue`；③ 含商标词的那条挑战名保留原样。**

### 先修脚本，再跑（不修就是造事实）

`tools/merge-upstream.js` 两处改掉：
- **默认强制现读两个源**，只有显式 `--use-cache` 才走本地快照；产物里写清本次是"两源现读"还是"用了快照"。
  原来只要本地有文件就不现读，会拿 10-07 落盘的旧译名去对齐 70338 的格位。
- **采集日期、`nameVerified`、分歧条数全部改为本次派生**，删掉写死的 `2026-09-13 / 114 / 89`。
  `classes.json` 的 `talentCount / nameVerified` 也交给 `merge-talents.js` 同步——它手抄漏过两次，
  build-data 早就为此设了断言，这次把"手抄"这个环节整个去掉。

### 合并结果：两个解包源已经收敛，真正的分歧在树名

| 项 | 合并前 | 合并后 |
| --- | --- | --- |
| 天赋节点 | 473 | **466**（两源现读，仅单源出现的格子 0） |
| 两源译名分歧（节点级） | 91 | **0** —— 两个第三方站现在 466 个名字全一致 |
| 名称与官网中文一致 | 114 | **462（99.1%）** |
| 全站覆盖率 L0/L1/L2/L3 | 366/114/360/2 | 366/**111**/**356**/2（总数随节点数变，L1 涨是因为官方稿覆盖到 8 个职业） |

节点级分歧归零不是我们判掉了谁，是**上游自己收敛了**。所以"两个都留"这条红线现在只剩树名在用：

| 系 | 官方中文（定名） | 另一来源 | 出处 |
| --- | --- | --- | --- |
| 潜行者第一系 | **奇袭** | 刺杀 | 官方 24310968 + 该工具站 `fashu/rogue`（实测该页 14 次「奇袭」、0 次「刺杀」） |
| 牧师第三系 | **暗影** | 暗影魔法 | 官方 24301514（实测小标题：戒律 / 神圣 / 暗影） |
| 萨满第一系 | **元素战斗** | 元素 | 官方 24302097（实测小标题：元素战斗 / 增强 / 恢复） |

圣骑士官方还没发解析稿，三个系名保持现状、不猜。另有 6 个节点是"我们两个源一致、但客户端解包站叫另一个名"，
按同一规则两边都留（`nameAlt` + 红框）。

### 界面跟着改了（不留"记了但没人看"的分歧）

`nameAltUpstream` 以前只写在数据里、页面不读，等于"我们记录了分歧但决定不告诉你"。现在：
天赋页的系 tab 与树标题走**官方定名 + 红框小标 + 悬停说明两个叫法**（跟节点级同一套符号）；
本页缺口清单里写明"系名有两个叫法：「奇袭」另一来源作「刺杀」（按官方定名显示）"；
溯源页那个统计从"两源译名分歧 0"改成"译名有两个叫法 3（含 3 个系名）"——
归零的那个数字会让人以为名字问题解决了，其实只是换了分歧的位置。

### 幂等坑（第二次跑差点把分歧记录冲掉）

第一版定名逻辑在第二次运行时会把 `nameAlt` 清空：因为那时 `nameCn` 已经是官方名，
"另一个叫法"只剩在上一轮写下的 `nameAlt` 里，而候选集没算它。已改成把 `nameAlt` 也纳入候选，
并实测连跑两次 `rogue.json` 的 md5 一致。**跑一次和跑两次结果必须一样**，否则下次谁重跑就悄悄丢数据。
