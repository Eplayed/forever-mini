# wow-forever · 当前接手入口

更新：2026-10-28（北京时间）。这是短索引；开工时先核实际 Git 状态、Qoder/Codex 正在运行的任务和本题最新交接。历史快照不自动代表现状。

## 先读哪里

| 问题 | 真源或入口 |
| --- | --- |
| 角色、红线、验证方式 | 根 `AGENTS.md`；具体门禁见 `PROJECT_GATES.md`；网页再看 `wow-forever-web/AGENTS.md`，小程序再看 `for-mini/AGENTS.md` |
| 站主按日期追加的决定 | `PROJECT_DECISIONS.md`，只读本题相关章节 |
| 最新任务证据与待确认项 | `ROLES.md` 末尾相关交接；对应的 `wow-forever-web/docs/` 或 `for-mini/docs/` 原件 |
| **换机器接手（去 Windows 那台继续）** | `wow-forever-web/docs/HANDOVER-2026-10-29-去Windows继续.md`——自足：路径表、规则真源指针、门禁命令、地图那一层缺什么、给 Windows 的六条导出纪律 |
| 网页文档导航 | `wow-forever-web/docs/README.md` 与 `PROJECT-INDEX.md`；索引只负责找路径 |
| 六个角色 Skill | `.agents/skills/wow-*/SKILL.md` 是真源；`.qoder/skills/` 和 `.trae/skills/` 是镜像，按根规则同步 |

## 线上是哪一包

网页 <https://eplayed.github.io/wuxian-atlas/> 当前是 **`wow-forever-web-20261028-174730-4e216292`**（整包 SHA-256 `d8fb1a4faeaa6891…`，3,880 文件，2026-10-28 17:47 打包、17:50 推送）。
这一包比上一包多：顶部导航一格「宠物」（带「新」角标）+ 首页一张宠物卡、首页「最新动态」提到大图正下方、职业页撤掉那句层级门槛说明、一条对应的「本站更新」。
线上实测：导航 13 格里有「宠物」、「最新动态」距页首 692px、首页宠物卡读数 18 家族 / 22 技能、`index.html` 与包内逐字节一致、直达渲染零报错。
上一包 `wow-forever-web-20261028-153918-476218a8`（`41f62c6c…`）在 `release/latest.json` 的 previous 位，含宠物页本身、专业页钓鱼分段表、21 件物品出处改名、12 条法术值。
真远端 `pkg-verify --live` 这一轮跑三次是 15/15、14/15、14/15——掉的那条每次都是同一个资源拉取超时：这台机器到 GitHub 现在 33 秒起步、偶尔 60 秒截断（同一份 JS 单独 curl 是 200 / 400,253 字节），不是线上缺文件。
打包与验收细节写在 `wow-forever-web/docs/VERIFY-GI返工第一批-2026-10-28.md` 第六节。
**"改了却看不见"先查线上包号，别先怀疑组件**——10-28 那次真因就是线上停在 10-23 那一包。

## 仍需接续的工作线

| 工作线 | 最近证据 | 接续前要核什么 |
| --- | --- | --- |
| 全职业真实 3D 配装 | `wow-forever-web/docs/VERIFY-第九轮修复诊断复核-2026-10-29.md`、`wow-forever-web/docs/QODER-全职业3D批量包修复-2026-10-29.md` | 76 份首批候选已导出但披风材质错接；Windows E11 五份修复诊断包经 Mac 独立重渲通过（披风、帽环、胸甲归因）。Windows 可按原任务立即重导 76 份九包，状态仍 `EXPORTED_PENDING_MAC_REVIEW`；Mac 逐套验收前不登记网页 PASS。旧“58 份穿披风”更正为清单 76/76 |
| BiS 数据 | `ROLES.md` 末尾 2026-10-28 的 wow-data 交接 | 本地来源更新、网页/小程序发布、候选差分门禁是不同状态；按本轮文件和线上包分别核 |
| 内容与变现 | `wow-forever-web/docs/OPS-变现底层逻辑-2026-10-28.md` 和 `ROLES.md` 最近的 wow-planner 行 | 运营建议、待站主决定、已验证数据分开看；不把待确认的方案当已执行 |
| 手机网页版 | `wow-forever-web/docs/UI.md` 第八节、根 `AGENTS.md` 第五节、`PROJECT_DECISIONS.md` 2026-10-28 | **站主 2026-10-28 定：不做，不需要考虑**——不再为窄屏专门设计入口/排布/适配，也不为"手机上某处不好点"开工作项。仍拦红的那批 375 断言（钉真出过的 bug）与小程序线的移动端门禁**不在这条范围内** |
| 地图这一层（副本逐层图 / 区域图选路 / 宠物页） | `wow-forever-web/docs/VERIFY-宠物页与区域图几何-2026-10-28.md`、`wow-forever-web/docs/PLAN-区域地图按OpenMap那套重做-2026-10-28.md`、`wow-forever-web/docs/DATA-副本层图-Windows任务书-2026-10-28.md` | 756 片逐层图**一张都没真导出**（要 Windows 那台跑，任务书已出）；区域图已选 A 路（游戏内实拍），任务书出到 10 张 + 1 张对照、等回件；`wow-forever-web/docs/DATA-区域图-Windows实拍任务书-2026-10-28.md`；宠物页只有家族与技能两层，逐只宠物的位置与驯服条件仍缺（#40 没关） |

## Qoder 与 Codex 如何接手

1. 一件可验收的交付开一条任务，标题写 `项目/工作线｜具体结果`；现有长对话留作历史，不把它当状态真源。
2. 开工先看 `git status --short` 和目标文件的 diff；同一工作树的同一文件一次只给一条任务写。Qoder 与 Codex 并行时，另一方先做只读复核或使用独立工作树。
3. 收尾把状态写入本页对应行，并按根规则在 `ROLES.md` 追加交接：产出路径、验证证据、没验到的事项、下一位负责人。只在聊天里说“做完了”不算交接。
4. 跨到 `video2text` 时，本仓库负责游戏数据、名称、来源与版本；内容产线从明确的文件或接口取数，在交接里记路径、字段、版本和未核项。
