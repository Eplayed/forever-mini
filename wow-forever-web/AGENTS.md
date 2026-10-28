# wow-forever-web · 资料站工程约定

角色分工、红线与验收基线以**仓库根 `../AGENTS.md`** 为准，本文件只写资料站特有的工程约定。

## 目录

```
app/            Vue 3 + Vite，这一站唯一的产品（21 条路由；实际路由以 app/src/router.js 为准）
  data/         **全线唯一数据基底**：classes / glossary / dungeons / systems / meta / timeline / abilities /
                chooser / method / legacy / bis / items / spells / achievements / releases / scale /
                talents/*.json / upstream/
                （chooser 与 method 是本站观点类内容必须标 kind；timeline 与 abilities 每条必须带官方来源，
                 official_cn 条目还必须带原文引用 quote）
  img/          本地素材：icons/（官方 CDN 转存 + manifest.json，可整体下线）、art/（客户端原画与副本底图）、
                gen/、keyart/、favicon.ico、apple-touch-icon.png；每张图的来路记在各层 manifest.json
                models/（配装 3D：根目录自产占位 + `real/` 中逐套核过的客户端整人模型；各有 manifest）：
                真实模型只在精确套装与阵营命中时展示；未导出的套装继续占位；删 `real/` 及 `art.json.bisRealModels` 即回自产占位
  src/styles/   tokens.css（设计令牌单一事实源，令牌表见 docs/UI.md）、app.css（组件基线）、
                board.css（只有这一站加载）、fonts.css + fonts/（自托管可变字体）
  src/lib/      data.js 带缓存的数据层、fmt.js 纯函数、glyph.js 自绘图参数、nav.js 导航、
                legacy-plan.js 传承加点引擎（纯函数，单测直接打真数据）
  src/components/ IconCell / ClassTile / LevelPill / SourceList / CovBar / ZoneMap / ZoneCard / HlText
  src/pages/    各路由页面；不要按 2026-10-09 的迁移名单判断现状
  public/       由 tools/app-assets.py 从 app/data 与 app/img 同步出来的副本（不入库）
  dist/         vite build 的产物，也是 site-check 与视觉回归的被测对象
tools/          build-data.js 校验卡口、merge-upstream.js 双源对齐、fetch-icons.js 图标、
                export-mini.js 导出小程序产物、site-check.py 界面回归门槛、audit-translations.py 译名体检、
                extract-abilities.py 抽技能四态、make-favicon.py 头标、release-package.py 发布包
docs/           当前入口见 README.md；带日期的 PRD / VERIFY / DATA-* 是当时快照
                screenshots/ 渲染证据 / reference/ 参考站实拍
                ASSET-GAPS-*.md 素材缺口逐键审计
```

**这里没有 `src/` 那一层旧静态站了**：2026-10-24 站主拍板删除，数据与素材搬到 `app/` 下，
两栈对拍脚本 `tools/app-parity.py` 一起删。看到任何 `src/data`、`src/img`、`src/css`、`src/js`
的写法就当它是错路径（历史 VERIFY 文档里那些是当时的样子，不改）。

## 命令

```bash
tools/refresh.sh <world|changes|prof|dungeons|talents|official|icons|check|publish>
                              # 一条链跑完：抓取 → 合并 → 门禁；顺序错了会把半成品当成品发出去
                              # 详见 docs/DATA-MAINTENANCE.md（数据从哪来、多久动一次、动完怎么确认没坏）
node tools/build-data.js        # 改数据必跑：校验 + 覆盖率 + 禁词体检，非 0 退出即未完成
node tools/merge-upstream.js    # 双源对齐（会改写 app/data/talents，谨慎）
node tools/fetch-icons.js       # 补图标：从官方 CDN 拉取到 app/img/icons
node tools/export-mini.js       # 导出 for-mini 用的 OSS 产物与打包快照
node tools/oss-release.js build --env beta --check-identity
                                # 小程序分发层：把 oss-preview 切成不可变批次 + 指针清单
                                # 同一文件还有 upload/verify/list/rollback/clean；指针永远最后换，见
                                # docs/OPS-oss-分发层-poe方案落地-2026-10-21.md
node tools/oss-release-test.js  # 分发层自测（正向+坏数据反例+客户端契约）；动过产物结构必跑
python3 tools/app-assets.py     # 把 app/data 与 app/img 增量同步进 app/public（构建前必跑，--check 查孤儿）
cd app && npm run build && npx vitest run   # 新站构建 + 组件级单测（build 自己会先跑 app-assets.py）
python3 tools/site-check.py     # **唯一的界面门槛**：自己起静态服务打 app/dist，
                                # 逐路由查渲染/红线/可访问性 + 天赋交互 + 世界点位 + 副本坐标 + 传承 + 配装 + 禁词。
                                # 跑之前必须已 npm run build，否则断言全打在旧 dist 上。
                                # --only talent,site_wide 用来快速探针；正式门禁不带 --only。
python3 tools/visual-check.py --make|--check
                                # 视觉回归：像素 + 生效值指纹两层，拍的也是 app/dist（改版后跑）
python3 tools/audit-translations.py  # 译名体检
python3 tools/build-bis-placeholder-model.py  # 重烘配装 3D 的**占位**模型（纯几何体，不含游戏资产）
python3 tools/register-bis-models.py          # 只登记自产占位进 art.json.bisModels
python3 tools/prepare-hunter-models.py        # 第七包猎人 GLB 坐标校正并留作诊断；第八轮位置未通过，不登记入站
python3 tools/build-bis-3d-jobs.py --check    # 其余套装的 Windows 导出任务清单与当前 bis.json 对拍
python3 tools/extract-gi-pets.py                 # GI 的 PetData.lua → upstream/gi-pets.json（dcn/den 成句描述一条不取，图标号先拿客户端 listfile 翻成键名）
python3 tools/merge-pets.py                      # → app/data/pets.json（18 家族 / 22 技能；全部 L1，未回客户端表核）
python3 tools/openmap-tile-manifest.py           # OpenMap 的层图表 → docs/DATA-openmap-副本层图-*.csv（756 号逐条回读 listfile，任一不 verified 就非 0 退出，不出半成品表）
python3 tools/build-zone-maps.py --dry-run|--out-dir|--apply   # 客户端 12 片区域瓦片拼成一张，裁到实测的 1002×668；片数不齐或内容盒对不上就跳过不硬拼
python3 tools/build-changelog.py     # 开发日志 → docs/CHANGELOG-DEV.md（不进网页；网页那份是手写的 app/data/releases.json）
python3 tools/extract-abilities.py --write  # 从官方中文职业深度解析稿重抽技能四态（整句照录，名称不在句里就丢弃）
python3 tools/release-package.py     # 打发布包（只发 app/dist，旧 html 的跳转桩已撤）
python3 tools/pkg-verify.py          # 发布包验收：起严格静态服务，缺文件必须 404（vite preview 的兜底会假绿）
bash tools/serve.sh            # 本地预览：新站 :8821（file:// 打不开本地 JSON）；stop 子命令关掉
```

## 站点硬规矩

1. **只有 `app/`（Vue 3 + Vite）这一个站**。仍然不许破的：无图标库、素材一律本地文件、不热链第三方域名、不引 UI 组件库、先不上 TypeScript。
   - **字体例外（2026-10-11 用户决策）**：允许**自托管**的 OFL 字体文件（`app/src/styles/fonts/` 两个可变 woff2，共 77 KB），
     **仍然禁止任何字体 CDN**（fonts.googleapis.com / gstatic 一律不许出现）。中文继续走系统字体；
     授权与来源写在 `app/src/styles/fonts/FONTS-LICENSE.txt`，删掉 `app/src/styles/fonts.css` 里两段 @font-face 即整体回落到系统字体。
   - **2026-10-24 站主决定：删除旧站。** 那份零构建静态站（19 页 + `src/js/` 那套无框架实现）已整目录删除，
     `tools/app-parity.py`（两栈对拍）随它一起删；"两栈同步"这个概念从此不存在。
     当时降级为参考报告的三条，现在的最终态是：
     ① 界面门槛只剩 `python3 tools/site-check.py`（它自己起静态服务打 `app/dist`，跑前必须 `npm run build`）；
     ② 老地址（`talent.html` 那一类）不再做跳转桩，发布包里除了 `index.html` 不许有第二个 `.html`，
        `pkg-verify.py` 钉的就是"访问它必须 404"——要恢复承接老书签，得重写一份映射与桩，先改这条；
     ③ 仍然有效的：`build-data.js`（数据卡口）、`audit-translations.py`（译名逐字回查）。
   - **`app/data/*.json` 是唯一的数据基底**，页面一律运行时读同一份数据，不得自带第二份、不得在组件里写死内容数字。
2. **数据与代码分离**：改内容只动 `app/data/`，不碰渲染逻辑。
3. **数据层**每条对外展示的条目必须带 `provenance`（来源类型 + URL + 核对日期）与 `level`（L0–L3），由 `build-data.js` 卡口：L0 无官方来源、iconKey 指向不存在的本地文件、掉落出现百分比、节点 id 重复、前置指向不存在的 id —— 任一命中直接构建失败。这条**没有放松**。
   3a. **内容页展示选定值，来源和历史分歧集中在溯源页**（2026-10-20 站主决定）。分级徽标、逐条来源轨和维护者术语不回流内容页；`LevelPill / SourceList / CovBar` 只在溯源页使用。插件有明确事实字段时按根规则的最新插件优先级选主值，旧值与冲突仍在数据和溯源页留档；插件缺字段才用注明来源的旧兜底，不把解析失败当成明确删除。缺字段显示“待实测”等真实状态，不编值。
       排行仍标“本站整理，非官方结论”；`addon-drawn` 地图必须就地标“这张是示意图，不是游戏里的地图”。这些说明不能被“内容页不展示出处”的旧决定吞掉。具体来源优先级和天裔小图标例外见根 `AGENTS.md` 2026-10-20 追加决定；历史决策与已撤口径见 `docs/VERIFY-pages-and-index-2026-10-21.md`。
4. 两源译名和数值分歧在数据里完整保留并注明来源；内容页使用选定值，分歧到溯源页查，不再要求内容页画旧 `.conf` 红框。
4b. **标 L0 的中文名必须能在它自己声明的官方页里逐字找到**（`tools/audit-translations.py` 负责核对）。找不到的要么改指向真正那篇、要么降 L2，只有写了官方原句与判定理由的例外（`app/data/audit-exceptions.json`）才允许保留，且缺 quote/reason/decidedAt 会让构建失败。
4c. **数据不许悄悄过期**（2026-10-26 站主定的天数）：`build-data.js` 拿逐板块版本表的"本站核对日"与当天比，
   超 `STALE_SOFT_DAYS`（7）提示、超 `STALE_HARD_DAYS`（14）**拦红**；阈值随 `scale.stalePolicy` 下发，
   溯源页那张表多一列「多久没核了」。**红了就去重抓那一块，不许把日期手抄新一点糊过去**——
   这条故意随"今天"变化，同一份数据放着不动才会红，重抓当天就绿。配装页还须把主源核对日显示给玩家
   （`site-check.py` 钉着，日期一律从 `bis.json.meta` 现读，门禁里再抄一个字面量就是第二次犯同一个错）。
5. **天赋层级点数门槛（2026-10-22 站主改口径，推翻本条原写法）**：`app/data/talents/*.json` 的 `rules`
   （`totalPoints` + `tierUnlockCost`）**随分片下发**，网页与小程序的天赋页都用它做加点判定——站主要的是
   "天赋树是模拟器的样子，可以模拟点击配置，和网页版那样的功能"。但这组数仍是**按经典旧世层级推的**，
   `grid.note` 自己写着"仍未核实"，所以两条硬约束跟着来：① 界面上必须固定一句
   "层级门槛按经典旧世推、无限服还没实测"（`mini-m02-check` 与 `site-check` 都查这句在不在）；
   ② 分片拿不到 `rules` 时退成"不做分层判定"并照实说，不许自己编一组门槛。
   要回到"只摆位、不判定"，先改这条。
6. **缺口要交代，但不再占内容页**（2026-10-12 用户实拍后改口径，推翻同日早上"每页自动挂一张清单"那条）：
   内容页不再挂「本页还没确认的」「这一页没有的」「同一页里两种说法并存」「按词找特长」这类卡片。
   缺口仍由数据字段（`notCollected` / `unconfirmed` / `conflicts`）带着来源集中到**溯源页**说，
   页面上只留会影响玩家操作判断的真实状态（如层级门槛待实测），不把旧 `.conf` 分歧提示加回内容页。
   文案面向玩家，不出现内部术语。**别把删掉的卡又加回来**——要恢复先改这条。
   - **禁词表 `tools/copy-banned.json` 是硬闸**：`build-data.js` 扫数据文件的字符串值，`site-check.py` 的 copy 小节逐路由扫渲染文字与来源展开后的渲染文字。「上游 / 口径 / mapId / 本轮 / 结构化 / 卡口 / 构建 / 文件名 / 脚本名」这类话不许上页面；加词前先想替代说法，别把正常中文（如物品名「大口径秘银步枪」）禁掉。
   - 网页上的「本站更新」读 **手写的 `app/data/releases.json`**（一条对应一个真实提交，`build-data.js` 会回仓库核对提交号）；git 自动生成的开发日志在 `docs/CHANGELOG-DEV.md`，**不进页面**。改了玩家能看到的东西就要补一条。
7. 界面改动必须有 `docs/screenshots/` 截图，构建通过不算完成。**桌面 1440 必给**；
   375px 那一档**从 2026-10-25 起暂时不作为门槛**（站主决定，见根 `AGENTS.md` 那一节）：
   `site-check.py` 的 `MOBILE_SOFT = True` 把逐路由那遍 375 与天赋 375 降成提示（照跑照打印，不过只记 NOTE），
   但传承/配装/世界点位/职业表头/物品库那几页自己的 375 断言仍拦红——各自钉着一条真出过的 bug。
   小程序那条线不受这条影响。**留存口径（2026-10-13 起）**：`docs/screenshots/` 只留当前有效的一套——按日整站重拍进 `check-YYYY-MM-DD/`，新批次落库时把上一批 tar 进 `docs/screenshots-archive/`（已 gitignore，不入库）再删原目录；根目录散图同页重拍直接覆盖，不无限新增。翻旧图去 `screenshots-archive/*.tar.gz`（清单见其 `MANIFEST.txt`）；旧 VERIFY 记录里引用的归档路径已失效，以 tar 内文件为准。仓库新克隆体积要等 git 历史重写才会真正变小（`wow-forever-web/docs/ARCH-REVIEW-2026-10-13.md` P0-2）。
