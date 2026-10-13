# wow-forever-web · 资料站工程约定

角色分工、红线与验收基线以**仓库根 `../AGENTS.md`** 为准，本文件只写资料站特有的工程约定。

## 目录

```
src/            17 个页面（index / talent / classes / chooser / timeline / skills / dungeons / raids / systems /
                races / professions / world / legacy / updates / rank / glossary / provenance）
                ——零构建，当前可发布版本（页数以 ls src/*.html 为准）
  css/app.css   设计令牌与组件样式（令牌表见 docs/UI.md）
  js/           data.js 加载与溯源、talent.js 天赋引擎、glyph.js 本地占位图、app.js 页面渲染
  data/         站点数据：classes / glossary / dungeons / systems / meta / timeline / abilities /
                chooser / method / talents/*.json / upstream/
                （chooser 与 method 是本站观点类内容必须标 kind；timeline 与 abilities 每条必须带官方来源，
                 official_cn 条目还必须带原文引用 quote）
  img/icons/    从官方 CDN 转存的天赋图标 + manifest.json（可整体下线）
tools/          build-data.js 校验卡口、merge-upstream.js 双源对齐、fetch-icons.js 图标、
                export-mini.js 导出小程序产物、site-check.py 界面回归自检、audit-translations.py 译名体检、
                extract-abilities.py 抽技能四态、make-favicon.py 头标、mindmap.js 生成导图
app/            Vue 3 + Vite 新站（2026-10-09 起按页迁移，目前迁了首页、世界页与职业页）
                  src/lib/     data.js 带缓存的数据层、fmt.js 纯函数、glyph.js 自绘图参数、nav.js 导航与新旧归属
                  src/components/  IconCell / ClassTile / LevelPill / SourceList / CovBar / ZoneMap / ZoneCard / HlText
                  src/pages/     HomePage / WorldPage / ClassesPage / Unmigrated（未迁路径明确提示回旧站）
                  public/      由 tools/app-assets.py 从 src/data 与 src/img 同步出来的副本（不入库）
                  tests/       Vitest 单测（纯函数 + 组件行为）
docs/           PRD / UI / reference-gap / wow-infinite-*（方案、流程、源盘点）/ data-base 采编工作台
                screenshots/ 渲染证据 / reference/ 参考站实拍
                ASSET-GAPS-*.md 素材缺口逐键审计 / APP-PARITY-*.md 新旧站逐页对拍
```

## 命令

```bash
tools/refresh.sh <world|changes|prof|dungeons|talents|official|icons|check|publish>
                              # 一条链跑完：抓取 → 合并 → 四道门禁；顺序错了会把半成品当成品发出去
                              # 详见 docs/DATA-MAINTENANCE.md（数据从哪来、多久动一次、动完怎么确认没坏）
node tools/build-data.js        # 改数据必跑：校验 + 覆盖率 + 禁词体检，非 0 退出即未完成
node tools/merge-upstream.js    # 双源对齐（会改写 src/data/talents，谨慎）
node tools/fetch-icons.js       # 补图标：从官方 CDN 拉取到 src/img/icons
node tools/export-mini.js       # 导出 for-mini 用的 OSS 产物与打包快照
python3 tools/site-check.py       # 界面回归自检：17 页渲染 + 天赋交互 + 分组导航 + 地下城 + 专业 + 世界线 +
                                  # 首页 + 动态/排行 + 设计基线 + 375px，非 0 即不通过
python3 tools/site-check.py --app # 加跑新站（Vue）冒烟：要先 cd app && npm run build && npx vite preview --port 8821
python3 tools/app-assets.py       # 把 src/data 与 src/img 增量同步进 app/public（新站构建前必跑）
python3 tools/app-parity.py --strict   # 新旧两站逐页对拍（结构计数 / 类名 / 正文文本 / 链接 / 图片）
python3 tools/visual-check.py --check  # 视觉回归：像素 + 生效值指纹两层（改版后跑；基线见 docs/UI-VISUAL-REGRESSION-2026-10-11.md）
cd app && npm run build && npx vitest run   # 新站构建 + 组件级单测
python3 tools/audit-translations.py  # 译名体检
python3 tools/build-changelog.py     # 开发日志 → docs/CHANGELOG-DEV.md（不进网页；网页那份是手写的 src/data/releases.json）
：把每条 L0 拿回它声明的官方页逐字核对，写 docs/DATA-AUDIT-<日期>.md
python3 tools/extract-abilities.py --write  # 从官方中文职业深度解析稿重抽技能四态（整句照录，名称不在句里就丢弃）
bash tools/serve.sh            # 本地预览：旧站 :8817 + 新站 :8821（file:// 打不开本地 JSON）
                               # 端口跟 tools/app-parity.py 的默认值对齐；stop 子命令关掉
```

## 站点硬规矩

1. **表现层允许 Vue 3 + Vite**（2026-10-09 用户决策，按页迁移中）。仍然不许破的：无图标库、素材一律本地文件、不热链第三方域名、不引 UI 组件库、先不上 TypeScript。
   - **字体例外（2026-10-11 用户决策）**：允许**自托管**的 OFL 字体文件（`src/fonts/` 两个可变 woff2，共 77 KB），**仍然禁止任何字体 CDN**（fonts.googleapis.com / gstatic 一律不许出现）。中文继续走系统字体；授权与来源写在 `src/fonts/FONTS-LICENSE.txt`，删掉 `src/css/fonts.css` 里两段 @font-face 即整体回落到系统字体。
   - 迁移期**两栈并存**：`src/` 是旧的零构建静态站（当前可发布版本，全部 17 页），`app/` 是新的 Vite + Vue 3 工程。旧站没删干净之前，它仍是线上口径。
   - **`src/data/*.json` 是两栈唯一的数据基底**，新站一律运行时读同一份数据，不得自带第二份、不得在组件里写死内容数字。
   - 旧 `src/js/` 继续守无框架约束（不用 `?.` 与 `??`、不引依赖）；`app/` 里可以用现代语法，但**必须过同一套卡口**（`build-data.js` 校验数据、`site-check.py` 校验界面、`audit-translations.py` 校验译名，断言总数只增不减）。
   - **每迁一页必须与旧页逐条对拍**（DOM 结构、文案、类名、图片数量与缺口回退），差异要么归零要么逐条写明理由；对拍没过的页不许当"已迁完"。
2. **数据与代码分离**：改内容只动 `src/data/`，不碰渲染逻辑。
3. **数据层**每条对外展示的条目必须带 `provenance`（来源类型 + URL + 核对日期）与 `level`（L0–L3），由 `build-data.js` 卡口：L0 无官方来源、iconKey 指向不存在的本地文件、掉落出现百分比、节点 id 重复、前置指向不存在的 id —— 任一命中直接构建失败。这条**没有放松**。
   3a. **但内容页面上不显示这些标记**（2026-10-12 用户决定，面对游戏玩家）：分级徽标、逐条「来源」按钮、来源轨、覆盖率条、素材出处角标（示意图 / 本地转存）一律不上内容页，
       出处与分级**集中在 `provenance.html`（溯源页）说**。落地方式：`src/js/data.js` 里 `pill / sources / covBar` 按 `data-page` 开关，只在溯源页输出；
       新站对应 `LevelPill / SourceList / CovBar` 组件同样只在溯源路由渲染。
       **加新页面时不要又把手写徽标或「来源」按钮画回内容页**，`site-check.py` 有反向断言会红。要在内容页恢复出处，先改这条。
       **别一并撤掉这四类句子**（撤了就是违红线或骗人）：① 两源分歧那一行红字（`.conf`，见第 4 条）；② 排行 / 问答处"这是本站整理的排序，不是强度排行"那句；③ 缺数据时写在格子里的取值本身（`待实测` / `待补` / `奖励待补` / `没有这张载入图`）与空态的原因（取自数据字段，不手写）；④ 同一张卡里两个数对不上时的对照行。细则与清单见 `docs/UI.md` 3.35。
       **①有两条已拍板的例外**（2026-10-13 站主决定，都在副本线）：
       - **等级区间**不再摆两个数——按参考站 `wowforever.wclbox.com/fuben` 卡片显示的那个数定稿，官方公告那个数留在每条记录的 `levelRangeOfficial` 里没删，决定与出处写在溯源页（`dungeons.json` 的 `meta.levelRangeSettled` 驱动，界面读它）。
       - **译名**一律按官方来——页面上只写官方那个名字，转载/另一站的写法留在 `nameCnConflict` 里（数据与卡口照旧），不再摆"译名冲突…待定稿"那行。副本、团本、区域与稀有全查过：只有领主大厅（官方「领主大厅」/ 17173「诸王大厅」）一处有冲突，世界线 44 区域 / 36 稀有 / 36 书 / 48 图**根本没有别名字段**。
       **人数与英文原名这两类分歧照旧一条不许撤。** 要恢复上面两条先改这条。
       **另有一条新口径**（同日）：**玩家看得见的地方不许出现"讲资料出处与缺口"的话**——
       `只有单一来源` / `这一条只有另一份资料有` / `接取地点待补` / `未标` / `同一任务 N 个版本` 这类
       是给维护者看的，一律不上页面（数据字段 `source` / `xpFrom` / `variants` 照旧留着，卡口照查）。
       缺的格子**留空**，不写"待补"。例外两种要留：① 玩法信息（`用物品开启：X`）；
       ② 两源数不一样时**两个数都得摆**（红线），但换成玩家读得懂的写法
       （`经验值有两个说法：850 / 1050，还没实测`，不是"本站取…另一份资料写…"）。
4. 两源译名分歧的节点必须同时保留 `nameCn` 与 `nameAlt`，页面红框标注，不做取舍掩盖。
4b. **标 L0 的中文名必须能在它自己声明的官方页里逐字找到**（`tools/audit-translations.py` 负责核对）。找不到的要么改指向真正那篇、要么降 L2，只有写了官方原句与判定理由的例外（`src/data/audit-exceptions.json`）才允许保留，且缺 quote/reason/decidedAt 会让构建失败。
5. 层级点数门槛未核实前，`rules.tierUnlockCost` 保持 `null`，界面只按坐标摆位，不做解锁判定。
6. **缺口要交代，但不再占内容页**（2026-10-12 用户实拍后改口径，推翻同日早上"每页自动挂一张清单"那条）：
   内容页不再挂「本页还没确认的」「这一页没有的」「同一页里两种说法并存」「按词找特长」这类卡片。
   缺口仍由数据字段（`notCollected` / `unconfirmed` / `conflicts`）带着来源集中到**溯源页**说，
   页面上只留会影响玩家判断的那一句（层级门槛没实测、两个叫法并存），写成一行 `.note` / `.conf`，不单独开卡。
   文案面向玩家，不出现内部术语。**别把删掉的卡又加回来**——要恢复先改这条。
   - **禁词表 `tools/copy-banned.json` 是硬闸**：`build-data.js` 扫数据文件的字符串值，`site-check.py` 第 18 节扫全部页面与来源展开后的渲染文字。「上游 / 口径 / mapId / 本轮 / 结构化 / 卡口 / 构建 / 文件名 / 脚本名」这类话不许上页面；加词前先想替代说法，别把正常中文（如物品名「大口径秘银步枪」）禁掉。
   - 网页上的「本站更新」读 **手写的 `src/data/releases.json`**（一条对应一个真实提交，`build-data.js` 会回仓库核对提交号）；git 自动生成的开发日志在 `docs/CHANGELOG-DEV.md`，**不进页面**。改了玩家能看到的东西就要补一条。
7. 界面改动必须有 `docs/screenshots/` 截图（桌面 + 375px 移动端），构建通过不算完成。
