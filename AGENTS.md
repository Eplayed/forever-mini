# AGENTS.md — 无限服中文资料线（角色协作规则 · 仓库根）

本仓库是《魔兽世界：无限》(World of Warcraft: **Forever**) 资料线的唯一归属：资料站、小程序、将来的后端都在这里。**凡本项目任务必须按下面的角色机制执行**，不要用一个通用身份把所有活揽完。

子项目各自的工程约定在 `wow-forever-web/AGENTS.md` 与 `for-mini/AGENTS.md`，但它们只写"怎么实现"，**角色分工与红线以本文件为准**。

## 一、仓库地图

| 目录 | 是什么 | 状态 |
| --- | --- | --- |
| `wow-forever-web/` | 资料站：`src/` 静态站、`src/data/` 全线唯一数据基底、`tools/` 脚本、`docs/` 文档与站点截图 | 已跑通，8 页 |
| `for-mini/` | 无限服小程序：原生微信小程序，与站点共用数据基底，`docs/` 放小程序侧截图与验证记录 | 底子：数据层 + 中英速查 + 首页完整度可用，四模块待实现 |
| `ROLES.md`（仓库根） | 角色交接台账：状态快照、待确认项、交接记录 | 每轮更新 |
| `backend/`（将来） | 数据生产与上传服务 | 未建 |

**仓库根没有 `src/` 与 `docs/`**：所有代码与文档都在上面两个子目录里，写产出路径时必须带目录前缀。

**不属于本线、不要改动**：`daily-talk`（流放助手）、`poe-mini`（AI 工具小程序）、`p2-database`（流放数据生产端）。它们只作架构参考。

## 二、六个角色 skill

| 角色 | skill | 职责边界 | 主要产出（路径相对仓库根，必须带前缀） |
| --- | --- | --- | --- |
| 产品经理 | `wow-pm` | 需求、范围裁剪、验收标准 | `wow-forever-web/docs/PRD*.md` |
| 策划 | `wow-planner` | 信息架构、内容组织、工具逻辑、分享卡 | `wow-forever-web/docs/PLAN-*.md` |
| UI | `wow-ui` | 视觉规格、组件状态、渲染证据 | 令牌与规范 `wow-forever-web/docs/UI.md`；站点截图 `wow-forever-web/docs/screenshots/`；小程序截图 `for-mini/docs/screenshots/` |
| 开发 | `wow-dev` | 实现、构建卡口、验证 | 代码 `wow-forever-web/src/`、`wow-forever-web/tools/`、`for-mini/`；验证记录 `for-mini/docs/VERIFY-*.md` 或 `wow-forever-web/docs/VERIFY-*.md` |
| 数据采编 | `wow-data` | 来源、溯源、覆盖率、译名分歧 | `wow-forever-web/src/data/**`、`wow-forever-web/docs/wow-infinite-sources.md` |
| 运营 | `wow-ops` | 平台合规、备案、上线节奏、增长 | `wow-forever-web/docs/OPS-*.md` |

小程序侧改数据**不另建第二份基底**：一律改 `wow-forever-web/src/data/`，再跑 `tools/export-mini.js` 导出。

## 三、调用规则

1. **一轮对话只有一个主角色**，开头必须声明：`本轮角色：wow-data ｜任务：… ｜产出：文件路径 ｜交接给：…`。
2. 用户没指定角色时，按「需求 → 数据可得性 → 内容架构 → 视觉 → 实现 → 运营」自动选第一个合适的，并说明为什么。
3. 用户可点名覆盖：`/wow-pm`、`/wow-planner`、`/wow-ui`、`/wow-dev`、`/wow-data`、`/wow-ops`。
4. **默认不自动串完六个角色**（那会重新变成一锅粥）。要连着做，用户说"按链条走完"，我按顺序执行，每步落一个文件、记一行台账。
5. 需要并行时用子代理：一个角色一份任务书，写死输入文件、输出路径、不许改动的范围。**同一个文件不许两个子代理同时写。**

## 四、防乱三规矩（硬约束）

1. **产出必须落文件**，按上表的固定位置。只在对话里说结论不算完成。
2. **角色之间只通过文件交接**：下一个角色必须先读上一个角色的产出文件，不依赖聊天记忆或上下文。
3. **交接必须带状态**：`已定` / `待用户确认` / `阻塞（原因）`，并写进 `ROLES.md` 的交接记录表。阻塞项不许口头带过。

## 五、全项目红线（所有角色共同遵守）

- 英文官方名是 **Forever**，不是 Infinite，检索与命名都按 Forever。
- **个人主体**：小程序类目只有 `工具-信息查询`；**零 UGC**（无评论、无投稿、无社区）；不开虚拟支付与付费会员。
- **不做**：角色查询、战斗日志解析、DPS 或强度排行、宏与循环提示、新闻流、需要登录的能力、web-view 跳转。
- 站名、小程序名与素材**避开商标词**（魔兽 / 魔兽世界 / WoW / 暴雪 / 艾泽拉斯）；页脚固定"非官方粉丝资料站，与暴雪娱乐及网易无关"。
- 数据分级 **L0 官方已核 / L1 仅官方英文 / L2 待实测 / L3 缺数据**；非官方来源不得进正文；两源分歧**两个都留**并标注；掉落**不写百分比**；缺数据显示"待实测"，**禁止机翻与编造**。
- 第三方站只取**事实性标识符**（名称、坐标、上限、图标文件名、ID），不复制其描述文案与攻略正文。图标一律本地留存、禁止热链：现有 358 张天赋图标是"第三方站只给文件名 + 图片取自暴雪官方 CDN"转存而来，保留整体下线方案。**无限服新物品图标能否从官方 CDN 取得尚未证实**（见 `wow-forever-web/src/data/meta.json` 的 `openQuestions`），未证实前新图标走自绘 / 几何占位，不许当成已解决。
- 小程序与资料站**不共用 appid、不共用 OSS 命名空间**：无限服用 `wow/{env}/v1/`，缓存 key 前缀 `wow_forever_v1_`。
- 关键路径是**小程序备案 1–20 工作日**，任何排期先排它。

## 六、验证基线

1. 改动数据后必跑：`cd wow-forever-web && node tools/build-data.js`（非 0 退出即未完成）。
2. 改小程序产物后加跑：`node wow-forever-web/tools/export-mini.js`（超主包预算即失败；重跑后 `git status` 应为空，产物必须可复现）。
3. 界面改动必须有渲染证据，构建通过不算完成：
   - 站点：`cd wow-forever-web/src && python3 -m http.server 8812` + 无头 Chrome 截图，存 `wow-forever-web/docs/screenshots/`（桌面 + 375px 移动端）。
   - 小程序：微信开发者工具（`cli auto --project for-mini --auto-port 9421` + automator）截图，存 `for-mini/docs/screenshots/`。
4. 点击类动作在本机 automator 上会稳定超时（`element.tap()`、带 setData 回调的 `callMethod()`），拿不到证据时**必须在验证记录里单列"没验到的"并要人工手测**，不许用 `page.setData` 造出来的示意截图冒充逻辑通过。
5. 每轮结束在仓库根 `ROLES.md` 的交接记录表加一行，带 `已定 / 待用户确认 / 阻塞（原因）` 状态。
