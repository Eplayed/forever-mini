# Qoder 两组交付复核：图文攻略事实闸与 R2 清理

日期：2026-10-21；角色：wow-pm（按图文攻略四关验收，也核 R2 边界）。状态：**事实闸局部通过／四关未通过，退 Qoder 补齐；R2 已提交部分可接受、入口仍有未提交项**。本轮只读检查，未修改 video2text 代码、生产库、平台文章。

## 结论与证据

`video2text` 的 `fa08a68`、`1bf0d35`、`64caf93` 确实把整理稿【风险核查】接到出图前，并把原先配文 260 字硬切改成保留全文、报告超长。实际运行 `env -u PYTHONHOME -u PYTHONPATH /usr/local/bin/python3 scripts/e2e_guide_gate.py` 得 `GUIDE_GATE_OK`、退出码 0：87 的“46亿”、85 的“20%”、83 的“毛边全消”被识别，74/63/66 反向健康样本没有硬拦。`py_compile` 与 `git diff --check` 退出码 0。此结论只覆盖**事实风险和截断**，不等于整篇图文攻略可发布。

四关 PRD `PRD-图文攻略四关验收-2026-10-21.md` 要求的交付仍缺：`output/角色交接/2026-10-21-头条-planner-图文攻略样本.md` 不存在；现有 writer 样稿是文字草案，表里承认缺关键游戏内截图，未交修订后的逐页 PNG、实际贴入帧来源与判帧记录，也没有逐页人眼确认“无视频后期字幕”。“去 AI 味”已有几句定点修改建议，但尚未在**最终卡片与配文成品**上做全篇人审。因此不能称“四关做完”。

### P0：判图失败仍会放进版面

`src/frame_pool.py:235` 仍用 `if not got.get("post_text")`。本轮真实函数复现：`apply_probe(item,{})`、`{'where':'none'}`、`{'post_text':None}` 都给 `clean=True`；`_probe_item` 又把看图空结果折成 `{}`，`usable()` 会纳入 `clean` 帧。Qoder 最快修法：只有结构有效且 `post_text is False` 才判干净；缺字段、非布尔、空回答、模型异常、裁后复核失败保持不可用并写原因。补真实 `apply_probe → _probe_item → usable` 反向测试，断言失败帧不会入候选；核手工 `photos[].path` 路径是否绕过检查，至少在最终审核明确标“未判，需人眼看”。旧缓存 `clean=true` 也不能替这次的最终图目视。

### P1：UI 走查仍直连生产服

`scripts/agent/ui_guide_gate_walk.py` 把 `BASE` 写死为 `http://127.0.0.1:15801`，随后向 `/api/poster/generate` 发真实 POST。脚本的安全前提是“闸口会拦下”；一旦被测功能回归，测试本身可能开始生成、覆盖 `output/poster/87`，甚至发收费请求。只检查 manifest mtime 只能事后发现，不能防止。改用第一单已建的 `scripts/agent/plan_test_server.py` 思路：临时库/临时成品目录、模型桩、与生产库路径相同即拒绝启动；UI 脚本只连该端口，故意让闸口失效的反向验证也不得写生产。修好前 Codex 不在 15801 重跑这项。

### P1：事实闸的“人工核实”放行没有核验凭据

`src/ai_poster.py` 对 `fact_hard` 在 `force=True` 时直接出图，`web/templates/index.html` 按钮写“这些数我已人工核实”，但没有要求来源、截图或核验人填写，manifest 仅记 `overridden`。这可能把仍未核实的数字做成海报。快捷修法：硬风险优先要求**改掉待核卖点**；保留放行功能时必须记录逐条来源与核验结果，缺记录仍不得显示“已核实”或标待发布。`fact_gate_state.hard` 即使经放行也仍在 lint 里是 `error`，界面需清楚表示“有图但不可发布”，不能因已出图误读为放行。

### P2：当前发布字段未全纳入事实检查

`fact_gate._fields(plan)` 读取 `plan.publish`，而真实旧成品 `manifest.plan` 不带 `publish`，它是独立字段；`generate_poster` 调 `fact_gate.check(plan, ..., copy_extra=pub.copy_text)`，只额外传了 `copy_text`。当前工作区已有 `tt_titles/xhs_copy` 等字段，风险数放在独立发布标题或其他配文位时不会被这一调用完整检查。快捷修法：检查前构造不改原 plan 的合并视图，把**实际将发布的** `pub` 全字段交给同一 `check`；针对 `tt_titles` 卖点与 `xhs_copy`/digest 叙述各加一条反例，避免只测旧 manifest 的图面标题。

## R2 清理

`wow-forever` 的 `ccf14cfb` 只改两份 PLAN 顶部导航、删除一个自述一次性且未见运行引用的探针，并追加一行交接，改动范围符合任务；当前 router 中 `/chooser`、`/professions`、`/world`、`/updates`、`/rank` 均存在，删除文件已不存在。`git diff --check` 与 `project-index.py --check` 退出码 0。因无数据/界面/小程序产物改动，没跑三项产品门禁可以接受。

但 `docs/README.md` 的历史快照名单与 `docs/PROJECT-INDEX.{json,md}` 仍是**未跟踪文件**，并不在 `ccf14cfb` 里；因此“下一次从干净检出即可读到完整新入口/索引”不能算已交付。这是第一轮工作归属，Qoder 不应代替别人批量提交。第一轮负责者需单独提交这些新文件并核对生成索引，或 R2 验收记录明确写“仅当前工作区有效”。此问题不要求恢复被删的探针。

## 退回给 Qoder 的最短路径

1. 先补 P0，并把 UI 走查移到隔离服务；这两项决定图片证据和回归是否可信。
2. 补齐 83 的选题卡与三页以内最终样稿：每页 PNG、实际用图路径/帧号、判帧与人眼结果、完整图文和配文；没有合格截图就出无图样稿，待核项不得升格成效果承诺。
3. 将风险放行改为有来源记录的人工决定，核实际发布字段；跑定点正反向回归。交付时分清已提交 HEAD 与当前共享工作区，不能只报工作区全绿。
4. 停在 Codex 验收点，不自动发布、不动公众号/雷达、不批量提交共享脏文件。R2 只让第一轮负责者收尾未跟踪入口；无需扩大清理范围。

未验项：真实收费模型的生成质量、真实人工发布、手机端整站、线上 83/85/87 当前图像版本。以上均不能用桩测试替代。
