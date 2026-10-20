# VERIFY · 上线前收尾（R2 → A02 → I02 → W02 → Q05）· 2026-10-20

本轮角色：wow-dev ｜任务：执行 `docs/DATA-prelaunch-dispatch-2026-10-20.md` §4 的五项可本地执行工作（旧 A01「仅补 40 件出处」限制按站主新决定撤销）｜产出：本文件 + 五项代码与数据提交｜交接给：Codex 独立验收。

**结论先说**：五项全部在本地做完并各自验过，整站回归通过（数字见 §6）。**没有部署、没有推送、没有正式发布**；外网那一段（真实域名、CDN 兜底行为、缓存头生效情况）本轮**未验收**，阻塞原因与解除条件写在 §5。

三条状态口径全文分开写：**已验证**（我在这台机器上真跑过并有产物）／**缺素材**（原料确实拿不到，给的是可用态不是假图）／**外网未验**（依赖还没定的托管目标，本机静态服务器不能替它说话）。

---

## 0. 提交与文件对照

| 项 | 提交 | 主要文件 |
| --- | --- | --- |
| W01-R2 | `b335bace` | `tools/route-smoke.py`、`tools/build-icon-map.py`、`.github/workflows/gates.yml` |
| A02 | `92732cc7` | `tools/{extract-addon-items-detail.py,merge-items-detail.py}`、`src/data/upstream/{gi,xr}-items-detail.json`、`src/data/items-detail.json`、`docs/data-base/a02-2026-10-20/` |
| I02 | `78d5373a` | `src/img/art/raceicons/skyborne.webp`、`src/img/art/manifest.json`、`src/data/art.json`、`app/src/pages/{RacesPage,SkillsPage,GlossaryPage,ProvenancePage}.vue`、`tools/{fetch-art.py,site-check.py,shot-provenance.py}` |
| W02 | `b4da1844` | `app/src/pages/UpdatesPage.vue`、`app/tests/updates-filter.spec.js`（新）、`tools/site-check.py` |
| Q05 | `7b813330` | `app/vite.config.js`、`tools/{release-package.py,pkg-verify.py,app-assets.py}`、`docs/data-base/release-2026-10-20/package-summary.json`、`.gitignore` |
| 本站更新台账 | `ac175cf7` | `src/data/{releases.json,scale.json}`（A02/I02/W02 各一条，Q05 不写：玩家看不见这一版有变化） |
| 自测完整性 | `2a92a026` | `tools/merge-items-detail.py`（抽出 `carry_missing()` 真调用）、`tools/site-check.py`（教益句徽标按数据取来源）、`.github/workflows/gates.yml`（CI 补三步） |
| 当日实拍 | `dc5882b9` | `docs/screenshots/check-2026-10-20/`（整站回归 + 26 条路由冒烟重跑后） |

---

## 1. W01-R2 · 两处校验漏洞的边界补齐（已验证）

派工要求：桌面与 375 各自执行内容断言；图标键加纯空白等边界；两个 `--selftest` 挂进现有 CI 的独立步骤。

1. **两视口断言**。R1 那版 `route-smoke.py` 的判断式是 `if tag == "d" and check:`——375 那一趟只拍图、从不跑断言，所以"两端都验过"这句话当时只有桌面成立。改成 `capture_one()` 对**每个视口分别执行 check 并分别记账**；更关键的一条语义：**某个视口没拍成，就等于该视口的断言没有依据**，不能拿桌面的结果顶过来，判 `FAIL`。
2. **键格式边界**。`build-icon-map.py` 用 `KEY_RE = ^[A-Za-z0-9_\-]{3,80}$` + `fullmatch`，纯空白、全空格、带路径分隔、带尾点、`.jpg` 后缀当键名一律非法；`--selftest` 15 条夹具（含"合法文件名不许误杀""漏登记/过期/死条目仍失败""非法键时不留半套登记"）。真实数据在收严前量过：非规范 `iconKey` 0 / 非法文件名 0 / 两字段不一致 0，所以严格化不牵连现有数据。
3. **CI**。`gates.yml` 里 `build-icon-map --selftest` 与 `route-smoke --selftest` 各一个独立步骤（不嵌进 `build-data.js`，生产数据生成不该依赖测试代码）。本轮又补了三步：`merge-items-detail --selftest`、`app-assets --check`（孤儿副本）、`release-package --check-only`（禁含清单）——这三个都是这一天从真实漏检里长出来的，见 §2 与 §5.1。

修前反例：375 那一趟**从不执行内容断言**，所以"两端都验过"只有桌面成立——这是 Codex 在 `VERIFY-W01-R1-independent-2026-10-20.md` 里用隔离反例测出来的（写一条只在 375 才成立的断言，旧版照样 `rc=0`）。图标键那侧：`valid_icon.` / `valid_icon.jpg` / `bad/key` / 纯空白 `"   "` 四种坏法，在 R1 的校验器下 `--check` 全返回 0。
修后结果：`route-smoke --selftest` 13 条、`build-icon-map --selftest` 15 条全过，且 `--selftest` 里"手机截图崩 → 该视口断言判失败 → 退出码 1"是真判据。

---

## 2. A02 · 最新插件数据同步（已验证；属性以插件为准）

站主 2026-10-20 决定：插件更新的数据属性以插件为准，撤销"仅补 40 件出处"的限制。取值顺序沿用既有：属性 GI > XR > 解包兜底、卖价 XR、出处 GI；插件没提供的字段才用带来源标注的旧兜底，**不把"插件没写"当成"游戏里没有"**。

**数据版本**（两份快照的 meta 里都带字节数、SHA-256、文件日期、提取日期，不抄进正文）：
- `GearInsight_Forever` **0.5.1**，Data.lua 3,702,026 B，`f5e768d3…`；提取出 `st` 1,453 件 / `src` 1,587 件。
- `XR_DungeonGuide` **66**，Data.lua 4,155,082 B，`cc4e767c…`；14,591 件带记录，其中 `st` 14,197、`sell` 12,695。

**合并后落到成品的实际变化**（逐件差分在 `docs/data-base/a02-2026-10-20/item-merged-diff.json`）：
501 件条目发生变化；其中属性行 241、使用条件 422、出处补空 40、出处改写 0、卖价 1、使用条件从高优先级源没写而保留兜底源的 14 件（记 `stExtraFrom`）。
成品现状：20,528 件详情，19,605 件有属性行，1,616 件有使用条件，1,541 件有出处。

**这一轮真正修掉的是一个数据质量 bug，不是"多同步了几件"**：XR 从 66 版起把**教益句**（"使用：教你学会施放不屈意志（等级 1）。"）不再用引号包住，而 `merge-items-detail.py` 的旧规则是"整行被引号包住的当风味句丢掉"。照旧规则跑，247 件图样/秘典/公式/设计图会只剩"需要工程学 (125)"这种行——那件装备唯一有用的那句话没了，比 2026-10-14 那版还差。改成**按内容判**（`教你|学会|可启动` 立进 `use`，纯风味句才丢，句中引号不动）。

夹具回归现在是 **9 条**（5 条判 `split_st` 的分档，4 条判"不许静默清掉使用条件"）。
其中那 4 条是本轮补的第二次动作：A02 当时写的两条是在自测代码里把生产表达式重抄一遍判自己，
`carry_missing` 的逻辑怎么改它都照样绿——那是假绿，所以把那段规则从合并主流程里抽成真函数、
自测改成真调用（提交 `2a92a026`）。

**修前反例（两条都是真跑出来的，不是推演）**：
① 把分档条件退回旧的"只认整行引号"（`if USE_RE.search(inner)` → `if q and USE_RE.search(inner)`），
   夹具第 2 条「不带引号的教学句同样进 use（XR 66 的新写法）」立刻 FAIL，得到
   `(['教你学会制作优质皮靴。'], None, 0)`；
② 把 `carry_missing()` 里"跳过当前取值那一家"那一句删掉，「不许自己补自己」那条立刻 FAIL 且 `rc=1`。
**修后结果**：9 条全过；重跑合并，成品 `src/data/items-detail.json` **零改动**（`git status` 干净），
证明抽函数没改结果。`build-data.js` 的 `useFrom` 白名单放开到 `gi`/`xr`
（原来只认 `wclbox`，实质规则"必须是单句、不带引号"没变），校验通过。

**没做的**：`nEn`（英文原名）按 2026-10-14 拍板仍不取；两份插件都不含掉率与描述正文，所以这两类一条没动。**没升档**：A02 带进来的名字与数值仍按既有分级留档，不自动升 L0。

---

## 3. I02 · 天裔种族小图标（已验证；来源与撤回就地写明）

站主 2026-10-20 特批：网页天裔种族小图标先用本机 `XR_DungeonGuide/Media/Race/RaceIcon_Skyborne.tga`，不再以"只从官方 CDN 取"这条挡它；**仅限种族小图标这一个用途**，不许拿 64px 小图替换传承页那张大图原画。

- 落独立目录 `src/img/art/raceicons/`，`src/img/art/manifest.json` 记：插件名与版本（XR_DungeonGuide 66）、源文件字节与 SHA-256、源尺寸 64×64 RGBA、`alphaUsed: false`、转存后 SHA-256（`9df418ce…`）、`origin: addon-file`、授权语原文、撤回方案。
- `src/data/art.json` 新增 `raceIcons` 键，与 `races`（大图原画）**两个键分开**——上一版我按文件名认小图标，两张都叫 `skyborne.webp`，把传承页那张大图误判成"小图误用"，是断言的错不是页面的错，现在按目录认。
- 接入点按"真正用到种族小图标"的入口逐个核：`RacesPage`（种族页那张 64px 的图）、`SkillsPage`（法术书按种族分组那格）、`GlossaryPage`（术语速查的种族分组）。三处都是**官方 `iconKey` 优先，取不到才回落到这张**。
- 溯源页新增一段"从插件目录转存的素材（特批，不走官方 CDN）"，把插件名、版本、源文件、转存路径、校验和、授权语、撤回方案一条一条列出来，明确写**不算官方已核素材**。这段的文案读 `art.json.meta.addonFiles`，由 `fetch-art.py` 从 manifest 现算——不在 Vue 里另抄一份（抄了就会漂）。页面上只露插件内那一段路径，本机目录结构不印到公网。

**已验证**：`site-check --only race_icon` 8 条全过——大小图分键；种族页 5 处小图标真解码（原图宽 64px）；传承页页头仍是那张大图、小图误用 0；法术书与术语页各 1 处吃到这张图；溯源页五要素（插件名/路径/校验和/"不算官方已核素材"/撤回方案）齐；375 滚到底 5 处全解码、横向溢出 0px；整页无破图无脚本报错。实拍 `docs/screenshots/check-2026-10-20/app-raceicon-skyborne{,-m}.png`、`app-provenance-addon-art{,-m}.png`。
**反向测试（本轮真跑的，不是推演）**：把 `src/img/art/raceicons/skyborne.webp` 移走、`app-assets --prune` 清掉 `public/` 里那份副本、重构建，`race_icon` 那节 **4 条红 / rc=1**——种族页「5 处，解码 0 处，原图宽 0px，破图 …」、法术书「1 处解码 0 处」、术语速查同样、375「5 处解码 0 处」。
第一次做这个反向测时它**没报红**，查下来是 `app-assets.py` 增量同步只加不删，`public/` 里那份旧副本还在被服务——撤素材这件事在浏览器里完全看不出来。那条发现直接变成 §5.1 的孤儿卡口（`--check` 判红、`--prune` 清）。
还有一条如实记：这 4 条红里**不含溯源页那条**——它读的是 manifest 不是图片文件，所以只删图不会让留档文字消失；撤回必须连 `manifest.json` 里那条一起删（`rollback` 字段写的就是这个做法）。

---

## 4. W02 · 动态页类别计数与筛选结果一致（已验证）

派工写的是"类别数量与筛选结果一致，搜索组合/空结果正确，以数据算期望值"。查下来是**两个叠在一起的错，都从旧站原样搬来**：

1. **字段用错**：格子上的数数的是 `it.kind`（只有 `talent`/`spell` 两种），点下去筛的是 `changeKind`（`added`/`modified`/…），所以除「全部类别」外**五格恒为 0**，可一点却能筛出几百条。
2. **名单写死**：页面里 `CH_KINDS` 固定六项，数据里实际有**九种** `changeKind`——`baseline` 8 条、`earlier` 4 条、`race` 3 条压根没有格子，「全部类别 967」与六格之和 952 差的 15 条，玩家把每格都点一遍也筛不到。

改法：`kindCount()` 与 `rows` 走同一个 `pass()`，只放开被数的那一维（职业格子与「全职业」同理，所以格子上的数会跟着职业/天赋法术/搜索一起变）；格子与下拉的类别由数据里真出现过的 `changeKind` 生成，标签取条目自带的 `changeCn`（和表里"改动"那一列同一套词）。

**修后各格实际数**（数据 `changes.json` 967 条）：全部类别 967 ｜新增 140｜改动 491｜换层或换系 28｜移除 80｜改名 5｜未变 208｜基线 8｜学得更早 4｜种族技 3 —— 各类之和 967，与「全部类别」相等。

**已验证**：
- 新增 `app/tests/updates-filter.spec.js` 6 条：手搓九行小样本，把 `kind` 与 `changeKind` 刻意拧开复现旧 bug；期望值全部手算写在测试里；覆盖默认态、逐格点击后表头条数等于格子数、叠职业+"只看天赋"、叠三层、搜不到时格子全 0 + 空态文案 + 不留空表、新类别自动多一格。
- `site-check --only updates_filter` 13 条全过：桌面逐格点一遍、猎人 + 只看法术三层叠加、空结果、375 上十格排布不横溢且点击同样对得上。期望值在 python 侧按 `changes.json` 现算，类别名单也从数据取，不写死。
- **反向测试（两条都是真跑的）**：① 把 `kindCount` 改回旧实现（数 `it.kind`），6 条单测里 **4 条立刻红**，另 2 条只走职业维度测不到这一条，如实记；② 把类别名单改回写死六项并重构建，`site-check --only updates_filter` **3 条红 / rc=1**——"类别数与数据一一对上"（页面 7 格 / 数据 10 种）、"逐格相等"、以及"各类之和 **952** ≠ 全部类别 **967**"，最后这条红出来的正是修前那个差 15 条的样子。两次变异改完都已还原，还原后 13/13 重跑绿。
- 旧站 `src/js/app.js` 那一版**没动**（已冻结），所以 `app-parity.py` 拿新站比旧站时这一处会显示不一致——那是新站修对了，不是做错。

---

## 5. Q05 · 发布包与本机验收（已验证的部分）＋外网未验（阻塞）

### 5.1 已验证（本机）

**base**：`app/vite.config.js` 的注释一直写着"base './' 是为了挂子路径"，但代码里**根本没设 `base`**——`lib/data.js` 的 `assetUrl()` 读的是 `import.meta.env.BASE_URL`，不设就是 `/`，产物只能挂根目录。这轮真的把它设成 `'./'` 并**反向验过**：把 base 改回 `/` 重新打包挂到 `/wow/` 下，页面壳子开得到但 0 张卡片、JS/CSS 全 404（`pkg-verify` 报 2 条 FAIL），改回 `'./'` 后 20/20 全过。所以"挂根目录"与"挂子路径"两种都成立，不是只改成 `./` 就当完事。

**打包**：`tools/release-package.py` 走完整构建链（`app-assets` → `build-data` → `vitest` → `vite build`）→ 暂存 → 生成旧页跳转桩 → 四道卡口 → 逐文件 SHA-256 清单入包 + 整包 SHA-256 落 `.sha256` + `release/latest.json` 留上一包做回滚位 + 按 `--keep` 轮转。当前这一版：3,692 个文件 / 28.2 MB / 整包 12.5 MB，`worktreeDirty: true`（工作区还有别的会话未提交改动，脚本自动在包名上标 `-dirty`，**不假装这是发布口径**）。

**卡口第一次跑就抓到真问题**：`src/data/upstream/` 那 54 份第三方原料快照一直跟着 `data/` 整目录被复制进 `public/` 再进 `dist/`——等于把加工原料一起发到公网，`dist` 60 MB 里 24 MB 是它。修在生成端：`app-assets.py` 加 `EXCLUDE = ["data/upstream"]`，`--check` 把这类"src 已经没有、public 还留着"的副本判成孤儿并 `rc=1`，`--prune` 清掉；产物降到 28.2 MB。反向测：往 `dist` 里塞 `data/upstream/x.json`、`deploy.log`、`Data.lua` 三个文件，卡口报 5 条并 `rc=1`。

**旧页地址策略**：包里按 `app/src/router.js` 的 `MIGRATED` 生成 20 个跳转桩（`talent.html` → `./#/talent`，带查询串一起带过去），名单只有路由文件那一份。为什么必须做：新站只有 `index.html`，直接发 `dist` 的话旧链接在真静态托管上是 404，在有 SPA 兜底的托管上会被吞成首页——**玩家点了没反应还零报错**，这条坑本轮已经踩过。

**验收**：`tools/pkg-verify.py` 20 条全过，用的是**没有 SPA 兜底**的 `http.server`（vite preview 对不存在的 `.jpg` 实测返回 `200 text/html`，用它验收等于假绿）。覆盖：根目录与 `/wow/` 两种挂法、hash 直达/刷新/新上下文分享、`talent.html?c=hunter` 在浏览器里真落到 `#/talent?c=hunter`、JSON/JS/CSS/图片 Content-Type、缺图必须 404、`data/upstream/*` 必须 404、未知 hash 路由落到"这页还没迁过来"而不是空白页。

**缓存策略**（按"文件名里有没有内容哈希"机器判定，不写在文档里靠人记）：`assets/*` 4 个文件带哈希 → 可 `immutable, max-age=31536000`；`index.html`、20 个桩、`data/*.json` 49 份、`img/**` 共 3,688 个文件**不带哈希** → 必须 `no-cache` 或极短 TTL 并在发版时刷 CDN。理由：本站数据每天都在改，给 `data/*.json` 一个统一长 `max-age` 等于把玩家留在旧数据上。

### 5.2 外网未验（阻塞，不假装通过）

| 未验项 | 为什么本机替不了 | 解除条件 |
| --- | --- | --- |
| 真实域名下的直达/刷新/分享 | 本机 `http.server` 没有 DNS、没有 HTTPS、没有托管方的 rewrite 与缓存层 | 域名与托管目标定下来 |
| 托管方的 SPA 兜底行为 | 各家默认值不同：有的对不存在的路径回 200 HTML，有的回 404。本站**要求回 404**，否则缺图与错路径全都看不出来 | 拿到实际托管配置权限后按 `pkg-verify` 那几条重跑一遍 |
| 缓存头是否真生效 | 上面那条"哪些必须 no-cache"是**规则**，还没人在真托管上设过并验证 `age`/`x-cache` | 同上 |
| 上传动作本身 | 站主未确认目标；本轮不擅自购买域名/服务、不改 DNS、不正式发布 | 站主指定目标并授权上传 |

`docs/OPS-deploy-domain-2026-10-19.md` 是**调研**，不是已配置托管的证据；本轮没有确认最终域名、托管项目、目标目录或外网可访问性。

---

## 6. 整站回归（一次跑完，命令与结果）

跑法：五项做完后按派工单 §6 的最终检查清单一次跑完，不逐项重跑。构建链与门禁全部 `rc=0`。

| 命令 | 结果 | 退出码 |
| --- | --- | --- |
| `python3 tools/build-icon-map.py --selftest` | 夹具 15 条全过 | 0 |
| `python3 tools/route-smoke.py --selftest` | 注入回归 13 条全过（含"手机截图崩 → 该视口断言判失败"） | 0 |
| `python3 tools/merge-items-detail.py --selftest` | 9 条全过（其中 4 条是本轮从"重抄表达式"改成真调用 `carry_missing()` 的） | 0 |
| `python3 tools/build-icon-map.py --check` | 缺图登记与实况一致：161 个键（引用 3,454 / 本地 3,294） | 0 |
| `python3 tools/app-assets.py --check` | public 与 src 差 0 个文件、孤儿副本 0 个 | 0 |
| `node tools/build-data.js` | 校验通过；禁词体检干净；本站更新 66 条 | 0 |
| `node tools/export-mini.js` | 快照词条 60 条 25.5 KB（预算 60 KB）；跑完 `git status` 对 `for-mini/` 零改动 | 0 |
| `npx vitest run`（app） | **106/106**（W02 那 6 条在内） | 0 |
| `npm run build` | 产物 `index-DZEyyTyi.js` 351.43 KB / gzip 119.72 KB | 0 |
| `python3 tools/site-check.py --app` | **917 / 917 全过** | 0 |
| `python3 tools/route-smoke.py --shots` | 路由 26 条 0 问题；截图 5 处 × 桌面/375 共 10 张，拍制失败 0、断言不过 0 | 0 |
| `python3 tools/release-package.py` | 3,692 个文件 / 28.2 MB / 整包 12.5 MB | 0 |
| `python3 tools/pkg-verify.py` | **20 / 20** | 0 |

**总数从 896 变成 917**：本轮新增 `race_icon` 8 条（I02）与 `updates_filter` 13 条（W02），去掉一次红重跑的差异见下。**没有为了过而放宽任何判据**——唯一的期望变更是那条写死标签的教益句断言，改成"徽标必须等于这一件自己记的 `useFrom`"，比原来更严（`useFrom` 不在已知三家名单里同样算失败）。

**中途那次红（如实记）**：第一次整站跑是 **916 / 917**，红的正是那条教益句徽标——A02 之后被挑中的第一件（石板：不屈意志）那句是解包侧给的，而断言只认 gi/xr 两个标签。页面显示没错，是期望过期。改成按数据取来源后单节 `--only app` 74/74，再整站重跑 917/917。

**整站跑完之后又做了两次变异（§3、§4 的反向测）**：改坏 → 单节红 → 还原 → 单节重跑绿（`race_icon` 8/8、`updates_filter` 13/13）→ 重构建。所以 `w2-*` 与 `app-raceicon-skyborne.png` 这几张是还原后重拍的，内容对应最终这一版。还原后又跑了一次 `release-package --skip-build --check-only`，**逐文件清单哈希与已入库摘要一致**（`03ccb8e4…`），说明磁盘上现在的 `dist` 与打进包里的字节是同一份。

**最终这一版包**：`wow-forever-web-20261020-190449-dc5882b9-dirty.tar.gz`，整包 SHA-256 `7fd30daa45733ebe9c2426efda31ced157e6be2aab454affc7f17d881ba3ef64`，逐文件清单在包内 `PACKAGE-MANIFEST.json`（清单摘要 `docs/data-base/release-2026-10-20/package-summary.json`），上一包 `…182210-f24e427a-dirty` 留在 `release/latest.json` 当回滚位。

**包名里那个 `-dirty` 不是我的改动**：脚本按 `git status --porcelain` 判的，此刻工作区只有 `AGENTS.md`、`ROLES.md`、`wow-forever-web/docs/wow-infinite-sources.md` 三个文件是**别的会话**未提交的编辑，我按规矩没夹带、没批量 add。我自己这一轮的文件全部在 `dc5882b9` 及之前的提交里。**正式上线那一版必须在这些文件也收口之后重跑 `release-package.py`**，包名不带 `-dirty` 才算数——这一条不是形式主义：包名里的 `-dirty` 就是"这一版没法逐字节复现"的标记。

---

## 7. 缺素材清单（本轮一条没补，给的是可用态）

| 类别 | 数量 | 本轮状态 | 证据与解除条件 |
| --- | --- | --- | --- |
| 区域底图 | 9 张 | 仍缺原料 | 插件目录 157 个图片文件按九个地图号搜 0 命中；源站 `ditu-xiao/<id>.webp` 九条全 404，同主机 `1426.webp` 200 作对照；界面已改成"地图编号 + 整宽点位清单"的紧凑态，不摆空图框 |
| 首领头像 | 82 只 | 仍缺原料 | 78 只源站自标 `data-unknown`、4 只名字对不上不猜；不配错脸 |
| 副本载入图 | 2 座 | 仍缺原料 | 巴罗夫地穴、海加尔山：两条真实来源 × 六种组合全 404（同规则对照条 200） |
| 物品/专业图标 | 161 个键 | 官方 CDN 没有这些文件 | `icon-gaps.json` 双向登记；界面退回自绘块；"CDN 没有"不等于"游戏内没有" |
| 天裔种族图标（官方位） | 1 | 用插件图代替（站主特批） | 官方 CDN 两边都没有；来源、授权与撤回写在溯源页与 manifest |

**这一栏的口径**：以上都是"既有来源今天取不到"，不是"官方永远不存在"；解除条件写在 `docs/ASSET-GAPS-2026-10-20.md`。

---

## 8. 交接状态

**已定**：R2、A02、I02、W02 四项的实现与本机验证；Q05 的本机一半（打包、卡口、桩、两种挂法、Content-Type、缓存规则、回滚位）。
**待用户确认**：① 上传目标与真实域名（§5.2 全部四项都卡在这）；② 旧页跳转桩是我按"旧链接不该静默变首页"的理由加进包里的，如果站主希望旧地址直接 404 或另起一个 `legacy/` 子目录，改 `release-package.py` 一处即可；③ 九张区域底图/82 只头像/2 张载入图是否作为首版上线硬门槛（本轮只做到"没图也能读"）。
**阻塞**：外网验收（原因：托管目标未确认，且本轮不擅自购买域名/服务、不改 DNS、不正式发布）。
**红线自查**：没有部署、没有推送、没有自动开始别的任务；`ROLES.md` 只追加本轮自己那一行；`AGENTS.md`、`docs/wow-infinite-sources.md` 等别的会话未提交改动没动、没批量 add。
