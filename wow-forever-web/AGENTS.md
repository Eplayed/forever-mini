# wow-forever-web · 资料站工程约定

角色分工、红线与验收基线以**仓库根 `../AGENTS.md`** 为准，本文件只写资料站特有的工程约定。

## 目录

```
src/            8 个页面（index / talent / chooser / skills / dungeons / systems / glossary / provenance）
  css/app.css   设计令牌与组件样式（令牌表见 docs/UI.md）
  js/           data.js 加载与溯源、talent.js 天赋引擎、glyph.js 本地占位图、app.js 页面渲染
  data/         站点数据：classes / glossary / dungeons / systems / meta / chooser / method /
                talents/*.json / upstream/（chooser 与 method 是本站观点类内容，必须标 kind）
  img/icons/    从官方 CDN 转存的天赋图标 + manifest.json（可整体下线）
tools/          build-data.js 校验卡口、merge-upstream.js 双源对齐、fetch-icons.js 图标、
                export-mini.js 导出小程序产物、site-check.py 界面回归自检、make-favicon.py 头标、
                mindmap.js 生成导图
docs/           PRD / UI / reference-gap / wow-infinite-*（方案、流程、源盘点）/ data-base 采编工作台
                screenshots/ 渲染证据 / reference/ 参考站实拍
```

## 命令

```bash
node tools/build-data.js        # 改数据必跑：校验 + 覆盖率，非 0 退出即未完成
node tools/merge-upstream.js    # 双源对齐（会改写 src/data/talents，谨慎）
node tools/fetch-icons.js       # 补图标：从官方 CDN 拉取到 src/img/icons
node tools/export-mini.js       # 导出 for-mini 用的 OSS 产物与打包快照
python3 tools/site-check.py       # 界面回归自检：8 页渲染 + 天赋交互 + 问答流程 + 375px，非 0 即不通过
cd src && python3 -m http.server 8812   # 本地预览（file:// 打不开本地 JSON）
```

## 站点硬规矩

1. **纯静态、无框架、无 Web 字体、无外链图标**；JS 不用 `?.` 与 `??`。
2. **数据与代码分离**：改内容只动 `src/data/`，不碰渲染逻辑。
3. 每条对外展示的数据必须带 `provenance`（来源类型 + URL + 核对日期）与 `level`（L0–L3），由 `build-data.js` 卡口：L0 无官方来源、iconKey 指向不存在的本地文件、掉落出现百分比、节点 id 重复、前置指向不存在的 id —— 任一命中直接构建失败。
4. 两源译名分歧的节点必须同时保留 `nameCn` 与 `nameAlt`，页面红框标注，不做取舍掩盖。
5. 层级点数门槛未核实前，`rules.tierUnlockCost` 保持 `null`，界面只按坐标摆位，不做解锁判定。
6. 每个内容页必须自动产出「本页还没确认的」清单（由数据缺口推导，不靠手写），文案面向玩家，不出现内部术语。
7. 界面改动必须有 `docs/screenshots/` 截图（桌面 + 375px 移动端），构建通过不算完成。
