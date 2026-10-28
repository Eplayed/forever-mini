# forever-mini · 无限服中文资料线（monorepo）

《魔兽世界：无限》(World of Warcraft: Forever) 中文资料线的所有代码与文档。一个仓库，两个前端项目，后续后端项目继续往这里加。

远程：`https://github.com/Eplayed/forever-mini`

## 仓库地图

| 目录 | 是什么 | 状态 |
| --- | --- | --- |
| `wow-forever-web/` | 资料站：`app/` 是唯一的产品（Vue 3 + Vite，21 条路由），数据基底在 `app/data/`、素材在 `app/img/`、全站样式在 `app/src/styles/`；工程脚本在 `tools/`，角色产出在 `docs/` | 旧零构建静态站已于 2026-10-24 删除 |
| `for-mini/` | 无限服小程序：原生微信小程序，与站点共用同一份数据基底 | 底子：数据层 + 中英速查 + 首页完整度已可用，四个模块待实现 |
| `backend/`（将来） | 数据生产与上传服务 | 未建 |

## 常用命令

```bash
# 数据校验 + 覆盖率卡口（改数据必跑，非 0 退出即未完成）
cd wow-forever-web && node tools/build-data.js

# 导出小程序产物：oss-preview/ 全量 JSON + data/*-snapshot.js 打包快照
node tools/export-mini.js

# 构建 + 组件单测（界面回归打的就是这份 dist，所以构建必须在前）
cd app && npm run build && npx vitest run && cd ..

# 界面门槛（自己起静态服务打 app/dist，不用先起 serve.sh）
python3 tools/site-check.py

# 本地人看：新站 :8821
bash tools/serve.sh            # 起；bash tools/serve.sh stop 关

# 上游天赋数据对齐（会改写 app/data/talents，谨慎）
node tools/merge-upstream.js
```

小程序：微信开发者工具「导入项目」选 `for-mini/`；appid 以当前 `for-mini/project.config.json` 与微信后台实际状态为准，不沿用历史快照中的测试号。

## 协作规则

角色机制、红线与验收基线见仓库根 **`AGENTS.md`**，当前接手入口见 **`NOW.md`**，按日期保留的站主决定见 **`PROJECT_DECISIONS.md`**，交接历史见 **`ROLES.md`**；资料站工程约定见 `wow-forever-web/AGENTS.md`，小程序侧约定见 `for-mini/AGENTS.md`。当前文档入口见 `wow-forever-web/docs/README.md`，历史报告不是当前规则。要点：

- 英文官方名是 **Forever**，不是 Infinite。
- 小程序个人主体：类目只有 `工具-信息查询`，零 UGC，不开虚拟支付或付费会员；网页具体边界看根 `AGENTS.md`。
- 站名与素材避开商标词，页脚固定「非官方粉丝资料站，与暴雪娱乐及网易无关」。
- 数据分级 L0–L3，缺数据显示「待实测」，禁止机翻与编造，掉落不写百分比。
- 关键路径是小程序备案 1–20 工作日，任何排期先排它。
