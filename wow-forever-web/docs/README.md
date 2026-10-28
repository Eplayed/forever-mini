# 资料站文档入口

本目录有大量按日留存的方案、验收和截图。**日期文档是当时快照，不自动成为今天的任务或规则。** 接手新任务先读仓库根 `AGENTS.md`、目标子项目 `AGENTS.md`，再用 `PROJECT-INDEX.md` 按任务定位原文件，最后看 `ROLES.md` 末尾相关交接。发现说法冲突，以当前用户决定、根规则和实际代码/数据为准；不要用旧报告覆盖新决定。

| 要做什么 | 当前入口 | 说明 |
| --- | --- | --- |
| 产品与工程边界 | `../AGENTS.md`、仓库根 `AGENTS.md` | 新站 `app/` 是唯一网页产品；旧站 `src/` 已于 2026-10-24 删除，`app/data/` 是唯一数据基底 |
| 按任务找文件 | `PROJECT-INDEX.md`、`../tools/project-index.py` | 索引是路径导航；运行 `--check` 看是否过期，变更后刷新，不代替原件 |
| 数据刷新 | `DATA-MAINTENANCE.md`、`../tools/refresh.sh` | 命令与顺序按实际脚本；文中的日期数量是历史测量 |
| 视觉规范 | `UI.md`、`../app/src/` | UI 文档按日期追加；早期“纯静态/两栈同步”段落只供追溯 |
| 最新上线证据 | `VERIFY-prelaunch-final-2026-10-20.md`、`VERIFY-pages-and-index-2026-10-21.md` | 验证报告只证明其记录的那一版和那次检查 |
| 当前运营和内容任务 | 最近的 `OPS-*.md` 与 `ROLES.md` 对应行 | 先核状态栏及后续用户决定，再交下一角色 |
| 公众号成稿与广告收入试验 | `OPS-公众号当前策略-2026-10-25.md`、`OPS-微信文章变现参考-2026-10-26.md` | 公众号交完整文章；广告收入只作待核账号资格与实际到账的补充试验，不按阅读量预估收入 |

`project-index.py --topic business` 目前列的是早期换轨与跨渠道说明；查公众号当前执行文件以表中两份为准，也可分别用 `--find 公众号`、`--find 变现` 定位路径。索引返回旧文件不表示其决策晚于 2026-10-26 的记录。

`PRD.md`、`PLAN-open-items.md`、`wow-infinite-plan.md` 与 `IDEA-*.md` 是早期需求、盘点或假设；
`PLAN-chooser.md`、`PLAN-wclbox-source.md`、`PLAN-reference-layouts.md`、`wow-infinite-workflow.md`、
`reference-gap.md` 是**按日期定过口径的说明与评估**——问答权重、接哪个源、学哪个壳这类决定仍以它们为准，
但它们写的**页面路径与”待做”清单多半已过期**，派活前先看正文顶部的现状校正和 `app/src/router.js`。
`APP-PARITY-*.md`、带日期的 `VERIFY-*.md`、`ASSET-GAPS-*.md` 是历史证据。它们保留供追溯，不参与当前规则的优先级，也不因为”文件名看起来像待办”就自动派工。历史报告提到的旧 `src/` 页面与两栈对拍脚本均已删除；现存数据生产脚本和验证证据仍按各自现状判断，不从历史快照推断今天的代码路径。

本轮清理的具体判断和未清理边界见 `VERIFY-stale-files-cleanup-2026-10-21.md`。
