# forever-mini · 无限服中文资料线（monorepo）

《魔兽世界：无限》(World of Warcraft: Forever) 中文资料线的所有代码与文档。一个仓库，两个前端项目，后续后端项目继续往这里加。

远程：`https://github.com/Eplayed/forever-mini`

## 仓库地图

| 目录 | 是什么 | 状态 |
| --- | --- | --- |
| `wow-forever-web/` | 资料站：纯静态 7 页（`src/`）、站点数据（`src/data/`）、构建与导出脚本（`tools/`）、全部角色产出（`docs/`） | 已跑通，`node tools/build-data.js` 通过 |
| `for-mini/` | 无限服小程序：原生微信小程序，与站点共用同一份数据基底 | 底子：数据层 + 中英速查 + 首页完整度已可用，四个模块待实现 |
| `backend/`（将来） | 数据生产与上传服务 | 未建 |

## 常用命令

```bash
# 数据校验 + 覆盖率卡口（改数据必跑，非 0 退出即未完成）
cd wow-forever-web && node tools/build-data.js

# 导出小程序产物：oss-preview/ 全量 JSON + data/*-snapshot.js 打包快照
node tools/export-mini.js

# 本地预览静态站
cd src && python3 -m http.server 8812

# 上游天赋数据对齐（会改写 src/data/talents，谨慎）
node tools/merge-upstream.js
```

小程序：微信开发者工具「导入项目」选 `for-mini/`，appid 用测试号（`project.config.json` 里已是 `touristappid`，独立 appid 待注册）。

## 协作规则

角色机制、红线与验收基线见 `wow-forever-web/AGENTS.md` 与 `docs/ROLES.md`；小程序侧的工程约定见 `for-mini/AGENTS.md`。要点：

- 英文官方名是 **Forever**，不是 Infinite。
- 个人主体：类目只有 `工具-信息查询`，零 UGC，不做付费。
- 站名与素材避开商标词，页脚固定「非官方粉丝资料站，与暴雪娱乐及网易无关」。
- 数据分级 L0–L3，缺数据显示「待实测」，禁止机翻与编造，掉落不写百分比。
- 关键路径是小程序备案 1–20 工作日，任何排期先排它。
