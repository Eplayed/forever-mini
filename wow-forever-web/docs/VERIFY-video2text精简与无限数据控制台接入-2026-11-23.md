# VERIFY — video2text 工作台 5 菜单精简与魔兽无限数据控制台接入（2026-11-23）

## 一、改动范围

### 1. Windows 生产端数据后台（`192.168.0.104:8830`）
- [catalog.py](file:///d:/project/forever/wow-forever-web/tools/admin/catalog.py)：
  - `bis` 板块计数改为 `sets+bis60Sets+raidSets+itemSets`（合计 119 套）；
  - 新增 `census`（双源人口普查，读 `population-census-cn.json` `provenance.checkedAt`）与 `nga`（读 `~/.nga/data/{hot,board}-*.json` 选题雷达快照）。
- [jobs.py](file:///d:/project/forever/wow-forever-web/tools/admin/jobs.py)：
  - 新增 `PIPELINE["sync-mac"]`（执行 `tools/sync-to-mac.py` 推送最新数据与图标到 MacBook）；
  - 补全 `DIRECT_REFRESH`：`census`（`refresh-census.py` + `build-data.js`）、`nga`（`scrape-nga-forever.py hot`）、`bis60`（`scrape-cwf-bis60.py` + `merge-bis60.py` + `build-data.js`）；
  - 新增 `action="refresh-and-sync"`（Windows 重抓指定板块并自动链式同步回 MacBook）。
- [server.py](file:///d:/project/forever/wow-forever-web/tools/admin/server.py)：
  - 绑定 `0.0.0.0:8830`；`_same_host()` 放行 `192.168.0.*:8830`；`_same_origin()` 放行携带 `X-Wow-Lan-Client: macbook-15801` 的可信局域网客户端（`127.0.0.1` / `192.168.0.101` / `192.168.0.104`）。

### 2. MacBook 工作台（`192.168.0.101:15801`，`~/Documents/project/video2text`）
- 新增数据控制台 API 蓝图 [forever_data_routes.py](file:///d:/project/forever/wow-forever-web/tools/forever_data_routes.py)（由 [sync-to-mac.py](file:///d:/project/forever/wow-forever-web/tools/sync-to-mac.py) 同步至 MacBook `src/forever_data_routes.py` 并在 `web/app.py` 注册）：
  - `GET /api/forever/status`：探测 Windows `8830` 在线状态并对照 MacBook 本地 16 个数据板块与 3,529 张本地图标；
  - `POST /api/forever/pull_from_windows`：一键触发 Windows `sync-mac` 将最新数据同步回 MacBook；
  - `POST /api/forever/refresh_and_pull`：支持单板块 `refresh-and-sync` 或 `daily --quick` 快速日更并自动同步；
  - `GET /api/forever/win_job/<job_id>`：实时轮询 Windows 端任务状态与日志，完成后自动清空 MacBook 侧 JSON 缓存；
  - `GET /api/forever/browse`：离线可读 MacBook 本机数据（`items` / `bis60` / `raid_t1` / `bis30` / `item_sets` / `dungeons` / `quests` / `census` / `macros` / `spells`）；
  - `GET /api/forever/icon/<name>`：严格按文件名白名单读取 MacBook 本地 `app/img/icons/`，零外链。
- 新增前端模块化脚本（MacBook `web/static/`）：
  - `web/static/forever-console.js`：无限数据控制台（Windows 状态栏、16 板块新鲜度与远程刷新卡片、9 标签可视化浏览器、双源人口横条图、真实本地图标与物品品质色）；
  - `web/static/ningjing-panel.js`：内嵌式「宁静排版工坊」面板（复用全套 `/api/ningjing/*` 接口，保留 `/ningjing` 独立路由兼容）。
- 精简 `web/templates/index.html` 与死代码清理：
  - 左侧菜单由 13 项精简为 **5 项**：`今日选题` / `宁静排版工坊` / `无限数据控制台` / `采集与素材库`（三合一子标签：采集任务 · 订阅与自动同步 · 素材库）/ `AI 设置`；
  - 移除废弃页面 DOM 与前端死代码：`面试题库`、`答案库与交付`、`头条图文`、`公众号图文`、`AI 海报`、`发布审核`、`运营周报`、`整理稿`、`排产表`，`index.html` 由 **12,380 行缩减至 5,905 行（移除 6,475 行，降幅 52.3%）**；
  - 后端移除已废弃的 `src/bank_board.py` 与 `/api/bank/overview`、`/api/bank/file` 路由（保留 `e2e_poster_checklist.py` 依赖的底层模块未动）。

## 二、验证结果与实拍证据

| 验证项 | 命令 / 方式 | 结果 |
| --- | --- | --- |
| Windows `8830` 单元测试 | `python -m unittest discover -s wow-forever-web/tools/admin -v` | **PASS**（Ran 11 tests in 1.255s — OK） |
| MacBook 攻略清单回归门禁 | `Python scripts/e2e_poster_checklist.py` | **PASS**（`POSTER_CHECKLIST_OK`） |
| 废弃接口移除验证 | `GET http://127.0.0.1:15801/api/bank/overview` | **PASS**（HTTP 404） |
| 无限数据 API 全量巡检 | `GET /api/forever/status` + 8 个 `browse` 标签 | **PASS**（`winOnline=True`，`icons=3529`，`items=21869`，`bis60=27`，`raid_t1=18`，`dungeons=38`，`quests=396`，`census=9`，`macros=245`，`spells=493`） |
| **真机跨机同步端到端** | `POST /api/forever/pull_from_windows` -> 轮询 `/api/forever/win_job/15cfa25514db` | **PASS**（4.1s 完成 `state=done`，成功从 Windows `8830` 拉取至 MacBook） |
| Playwright 5 菜单与子标签巡检 | Chromium 1440×900 逐项点击 5 菜单 + 全部子标签 | **PASS**（侧栏精确 5 项；0 console error / 0 pageerror；BiS60 正确显示中文名如「狮心头盔」；双源人口百分比与条形图正常；采集三子标签隔离无泄漏） |

实拍截图（已逐张人工核查）：
- 今日选题（5 菜单首页）：[workbench_5menu_1_dashboard.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/ningjing-packs/workbench_5menu_1_dashboard.png)
- 宁静排版工坊（内嵌面板）：[workbench_5menu_2_ningjing.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/ningjing-packs/workbench_5menu_2_ningjing.png)
- 无限数据控制台（Windows 在线与 16 板块）：[workbench_5menu_3_forever_console.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/ningjing-packs/workbench_5menu_3_forever_console.png)
- 60级团前 BiS 可视化浏览器：[workbench_5menu_4_forever_bis60.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/ningjing-packs/workbench_5menu_4_forever_bis60.png)
- 人口普查双源对比条形图：[workbench_5menu_5_forever_census.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/ningjing-packs/workbench_5menu_5_forever_census.png)
- 采集与素材库（三合一子标签）：[workbench_5menu_6_collect_videos.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/ningjing-packs/workbench_5menu_6_collect_videos.png)

## 三、边界与未验项
- NGA 选题雷达仅作为 Windows 侧选题监控与刷新入口，不向资料站或小程序端发布论坛标题与正文（符合红线）。
- 远程单板块重抓（`refresh-and-sync`）与 `daily --quick` 已通过单元测试、路由联调与 `sync-mac` 真机执行验证；未在本次回归中对外部站点（WCLBox/BigFoot）批量发起实抓，避免触发外站限流，日常按需在控制台点击单卡「刷新并同步」即可。
- 若 Windows 主机关机或休眠，MacBook `:15801` 会自动显示「Windows 生产端离线（仅浏览本机副本）」，禁用远程刷新按钮，但本机 9 标签可视化浏览器与宁静排版工坊继续离线可用。
