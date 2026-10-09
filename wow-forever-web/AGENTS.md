# wow-forever-web · 资料站工程约定

角色分工、红线与验收基线以**仓库根 `../AGENTS.md`** 为准，本文件只写资料站特有的工程约定。

## 目录

```
src/            14 个页面（index / talent / chooser / timeline / skills / dungeons / systems / races /
                professions / world / updates / rank / glossary / provenance）——零构建，当前可发布版本
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
app/            Vue 3 + Vite 新站（2026-10-09 起按页迁移，目前只有首页与世界页）
                  src/lib/     data.js 带缓存的数据层、fmt.js 纯函数、glyph.js 自绘图参数、nav.js 导航与新旧归属
                  src/components/  IconCell / ClassTile / LevelPill / SourceList / CovBar / ZoneMap / ZoneCard / HlText
                  src/pages/     HomePage / WorldPage / Unmigrated（未迁路径明确提示回旧站）
                  public/      由 tools/app-assets.py 从 src/data 与 src/img 同步出来的副本（不入库）
                  tests/       Vitest 单测（纯函数 + 组件行为）
docs/           PRD / UI / reference-gap / wow-infinite-*（方案、流程、源盘点）/ data-base 采编工作台
                screenshots/ 渲染证据 / reference/ 参考站实拍
                ASSET-GAPS-*.md 素材缺口逐键审计 / APP-PARITY-*.md 新旧站逐页对拍
```

## 命令

```bash
node tools/build-data.js        # 改数据必跑：校验 + 覆盖率，非 0 退出即未完成
node tools/merge-upstream.js    # 双源对齐（会改写 src/data/talents，谨慎）
node tools/fetch-icons.js       # 补图标：从官方 CDN 拉取到 src/img/icons
node tools/export-mini.js       # 导出 for-mini 用的 OSS 产物与打包快照
python3 tools/site-check.py       # 界面回归自检：14 页渲染 + 天赋交互 + 分组导航 + 地下城 + 专业 + 世界线 +
                                  # 首页 + 动态/排行 + 设计基线 + 375px，非 0 即不通过
python3 tools/site-check.py --app # 加跑新站（Vue）冒烟：要先 cd app && npm run build && npx vite preview --port 8821
python3 tools/app-assets.py       # 把 src/data 与 src/img 增量同步进 app/public（新站构建前必跑）
python3 tools/app-parity.py --strict   # 新旧两站逐页对拍（结构计数 / 类名 / 正文文本 / 链接 / 图片）
cd app && npm run build && npx vitest run   # 新站构建 + 组件级单测
python3 tools/audit-translations.py  # 译名体检：把每条 L0 拿回它声明的官方页逐字核对，写 docs/DATA-AUDIT-<日期>.md
python3 tools/extract-abilities.py --write  # 从官方中文职业深度解析稿重抽技能四态（整句照录，名称不在句里就丢弃）
cd src && python3 -m http.server 8812   # 本地预览（file:// 打不开本地 JSON）
```

## 站点硬规矩

1. **表现层允许 Vue 3 + Vite**（2026-10-09 用户决策，按页迁移中）。仍然不许破的：无 Web 字体、无图标库、素材一律本地文件、不热链第三方域名、不引 UI 组件库、先不上 TypeScript。
   - 迁移期**两栈并存**：`src/` 是旧的零构建静态站（当前可发布版本，全部 14 页），`app/` 是新的 Vite + Vue 3 工程。旧站没删干净之前，它仍是线上口径。
   - **`src/data/*.json` 是两栈唯一的数据基底**，新站一律运行时读同一份数据，不得自带第二份、不得在组件里写死内容数字。
   - 旧 `src/js/` 继续守无框架约束（不用 `?.` 与 `??`、不引依赖）；`app/` 里可以用现代语法，但**必须过同一套卡口**（`build-data.js` 校验数据、`site-check.py` 校验界面、`audit-translations.py` 校验译名，断言总数只增不减）。
   - **每迁一页必须与旧页逐条对拍**（DOM 结构、文案、类名、图片数量与缺口回退），差异要么归零要么逐条写明理由；对拍没过的页不许当"已迁完"。
2. **数据与代码分离**：改内容只动 `src/data/`，不碰渲染逻辑。
3. 每条对外展示的数据必须带 `provenance`（来源类型 + URL + 核对日期）与 `level`（L0–L3），由 `build-data.js` 卡口：L0 无官方来源、iconKey 指向不存在的本地文件、掉落出现百分比、节点 id 重复、前置指向不存在的 id —— 任一命中直接构建失败。
4. 两源译名分歧的节点必须同时保留 `nameCn` 与 `nameAlt`，页面红框标注，不做取舍掩盖。
4b. **标 L0 的中文名必须能在它自己声明的官方页里逐字找到**（`tools/audit-translations.py` 负责核对）。找不到的要么改指向真正那篇、要么降 L2，只有写了官方原句与判定理由的例外（`src/data/audit-exceptions.json`）才允许保留，且缺 quote/reason/decidedAt 会让构建失败。
5. 层级点数门槛未核实前，`rules.tierUnlockCost` 保持 `null`，界面只按坐标摆位，不做解锁判定。
6. 每个内容页必须自动产出「本页还没确认的」清单（由数据缺口推导，不靠手写），文案面向玩家，不出现内部术语。
7. 界面改动必须有 `docs/screenshots/` 截图（桌面 + 375px 移动端），构建通过不算完成。
