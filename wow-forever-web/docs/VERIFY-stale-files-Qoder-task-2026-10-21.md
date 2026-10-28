# 给 Qoder 的第二轮清理工单

日期：2026-10-21；主角色：wow-dev；状态：**已定（任务范围与验收）／待 Qoder 执行／待 Codex 复核**。工作仓库：`/Users/zhangyajun/Documents/project/wow-forever`。本文件是派工文本，不表示 Qoder 已收到或已开始。

## 直接交给 Qoder 的任务

> **任务目标：** 接着已完成的第一轮清理，只去掉会误导下一轮的现行入口错误，以及能证明完全无用的废弃文件/代码。不要把“文件旧”当成“可以删”。优先让下个 Agent 能准确找到当前产品与规则，不追求删除数量。
>
> **先读这四处，限定定位：** 仓库根 `AGENTS.md`、`wow-forever-web/AGENTS.md`、`wow-forever-web/docs/README.md`、`wow-forever-web/docs/VERIFY-stale-files-cleanup-2026-10-21.md`；再看 `git status --short` 和相关文件的 `git diff`。索引用 `python3 wow-forever-web/tools/project-index.py --topic rules`，索引只是路径导航。只在入口不足时对目标目录做 `rg`，不要通读全部历史 `VERIFY`、截图、大 JSON 或扫别的项目。
>
> **第一单元，消除仍会被当成现行指令的错误（优先）：** 在 `README.md`、两份子项目 `AGENTS.md`、`wow-forever-web/docs/{README,DATA-MAINTENANCE,UI,PRD,PLAN-open-items}.md` 与索引任务入口中，定点查“旧站是发布版 / 新站仍迁移中 / 两栈必须同步 / 旧禁区 / 旧数值”。只有和根规则、当前 `app/src/router.js`、`tools/refresh.sh`、发布脚本或实际数据直接冲突的句子才修；已有第一轮修改先读 diff，不重复改。对大篇历史报告只加醒目“历史快照、非现行规则”入口，**不要篡改当时的测试结果和用户决定**。根 `AGENTS.md`、`ROLES.md` 已有其他会话修改；如发现问题，记录具体行和建议，不整份重写。
>
> **第二单元，找可证实的孤儿文件（小范围）：** 只在 `wow-forever-web/tools/` 和 `wow-forever-web/docs/` 找最多 5 个候选。逐个查 `tools/refresh.sh`、`.github/workflows/gates.yml`、`app/package.json`、`app/src` 的导入/路由、其他脚本调用和活跃文档入口；考虑动态命令与人工运行。给每个候选写“路径、最后用途、引用证据、删/留理由”。只有**无运行引用、无回归/溯源用途、可以明确恢复**的才删除，并同步移除当前入口的链接。第一轮已删除 `mindmap.js` 和两份生成物，不重复处理。`src/*.html`、`src/js/` 旧站回归参照、`src/data/**` 唯一基底、插件原料、按日期留存的 `VERIFY/APP-PARITY/ASSET-GAPS` 证据、其他会话未提交文件均不作为批量删除对象。找不到可靠候选就交“0 个安全可删”，不要硬凑。
>
> **验证和交付：** 每改一处只跑相关检查。文档/索引改动至少 `git diff --check`、链接/引用定点检查、`project-index.py --topic rules` 后 `--check`；若删除运行脚本，额外跑它所属链路的最小回归；改数据才跑 `node tools/build-data.js`，改界面才按根规则跑 `site-check.py --app` 和实拍。不要为本轮启动网络抓取、发布、部署或收费调用。最后写 `wow-forever-web/docs/VERIFY-stale-files-Qoder-R2-2026-10-21.md`：逐候选处置表、实际 diff 路径、命令和退出码、保留理由、没验到的。`ROLES.md` 只追加一行带状态；刷新索引。不要 `git add .` 或批量提交共享脏文件，只处理自己可归属的 hunk。
>
> **停点：** 完成上述两单元及验证后停下，交 Codex 复核；不要自动开始大规模重构或迁移历史文档。

## Codex 验收标准

1. 下一轮从 `rules` 索引和文档入口读到的当前产品必须是 `app/`，旧站只作冻结参照；同一入口不能再同时命令“必须双栈同步”和“旧站冻结”。
2. 每个删除项都能展示“没有运行/人工用途”的证据；若保留，理由和当前权威入口清楚。删除后没有活跃链接指向不存在的文件。
3. 历史验证数据未被重写；他人未提交改动未被回滚、整份提交或混入此次交付。
4. 验证命令、退出码与实际改动相匹配；索引刷新后 `--check` 为 0。没有把“没有找到更多可删项”误报为全仓再无过时文件。
