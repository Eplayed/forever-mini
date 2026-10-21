# Qoder 图文攻略四关补齐：交付记录（第二轮）

日期：2026-10-21；角色：wow-dev（受派补 Codex 复核退回来的图文攻略四关未通过项）。
状态：**三项代码修复与两项工程件已提交 `video2text` HEAD／83 四关交付件已落文件，待 Codex 复验**。
本轮只动图文攻略这一条：**没碰公众号、没碰选题雷达、没动线上任何一篇文章，没有批量提交共享工作区文件，没有发布、没有登记**。

## 任务来源与本轮做了什么

派工与验收标准：本目录 `VERIFY-Qoder交付复核-2026-10-21.md`（P0 判帧、P1 走查隔离、P1 放行凭据、P2 发布字段、四关交付件）。
按号主给的顺序执行：先修判帧，再把走查搬到隔离服务，然后交 83 的四件，最后核放行凭据。

| 复核项 | 本轮结论 | 落在哪 |
|---|---|---|
| **P0 判图失败仍会放进版面** | 已修。`apply_probe` 现在只有 `post_text` 明确是布尔才给结论；空回答、缺字段、非布尔、调用异常、裁完回读失败一律"不可用 + 写明原因 + `checked=False`（下次重问）"。反向测试走真链路 `apply_probe → _probe_item → ensure_judged → usable`，断言失败帧进不了候选 | `video2text/src/frame_pool.py`、`scripts/e2e_frame_judge.py`（新增），提交 `5c65cfe` |
| 手工 `photos[].path` 是否绕过检查 | **确实绕过**。不拦出图，但标 `judged=false` 并写进成品清单（`manifest.photos_unjudged` + 一条 lint warn「未判，需人眼看」） | `video2text/src/ai_poster.py:bind_frames / unjudged_photos` |
| **反向测试另外抓到的一条**（复核件没点名） | 没定位到横幅的帧 `file` 就是 `raw` 本身，而 `build`/`ensure_judged` 判完无条件 `_drop_raw(raw)` —— **把刚判成干净、正被版面引用的那张图删了**。生产帧池实测 108 张 `clean` 里 6 张已是悬空路径（界面显示"0 张可用"却看不出原因）。改成只有成品帧与原帧不是同一文件时才删；**这 6 张本轮只报不修** | 同上，`_drop_spent_raw` |
| **P1 UI 走查仍直连生产服** | 已搬。新增 `scripts/agent/poster_test_server.py`：临时库副本 + 临时成品目录 + `openai` 内存桩 + `requests` 一调就抛（收费那一跳发不出去）+ **解析路径撞上生产库或成品目录落在仓库 `output/` 即拒绝启动（退出码 2）**。走查只连它，并按任务书加了反向验证：`--gate off` 故意让闸口失效 → 图确实出了，但只写临时目录，生产 `output/poster/87/manifest.json` 的 mtime + sha256 双核不变 | `video2text/scripts/agent/{poster_test_server,ui_guide_gate_walk}.py`，提交 `f53edcd` |
| **P1 人工放行没有核验凭据** | 已改。硬风险优先要求改掉卖点；保留放行时**必须逐条**交「出处 + 核验结论 + 核验人」（`fact_gate.check_override`）。缺任何一条：图照样出（人是最终判断者），但 `publishable=false`、lint 点名缺哪条，界面从按钮文案到结果条都不出现"已核实"，只写"⛔ 不可发布"；凭据齐了才写"✅ 已逐条留凭据（核验人 X）" | `src/fact_gate.py`、`src/ai_poster.py`、`web/app.py`、`web/templates/index.html` |
| **P2 当前发布字段未全纳入事实检查** | 已改。出图前用 `_publish_view(plan, pub)` 合成只读视图（不改原 plan）把**实际要发出去的**全字段交给同一份 `check`；发布标题（`tt_titles`/`xhs_titles`）算卖点位。回归加两条反例：待核数只写在标题里必须拦、只写在正文叙述里只提示 | 同上 + `scripts/e2e_guide_gate.py` H/I 两段 |
| **四关缺的交付件** | 已补：选题卡、三页以内最终海报、每页实际用图与判帧记录、逐页文案对照、成品上的全篇复核 | 见下 |

## 83 的四件交付在哪（文件路径）

| 件 | 路径 |
|---|---|
| 选题卡（planner，复核件点名"不存在"的那一份） | `video2text/output/角色交接/2026-10-21-头条-planner-图文攻略样本.md` |
| 最终海报（三页，0 元程序排字） | `video2text/output/样稿/2026-10-21-83/83/poster_p1.png`（=`poster.png`）、`poster_p2.png`、`poster_p3.png` + 同目录 `manifest.json` |
| 每页实际用图 + 判帧记录 + 逐张目视 | `video2text/output/角色交接/2026-10-21-头条-ui-83样张与用图记录.md`；原始判帧数据 `output/样稿/2026-10-21-83/frame_judge.json` |
| 文案修改对照 + 在最终成品上重做的全篇复核 | 追加在 `video2text/output/角色交接/2026-10-21-头条-writer-83画面设置样稿.md` 末尾（旧成品对照基准 `output/poster/83/` **未被覆盖**） |
| 开发交付（改动清单／跑了什么／没验什么） | `video2text/output/角色交接/2026-10-21-头条-dev-83四关交付-2.md`；工程侧留痕见 `video2text/CHANGELOG_FOR_AI.md` 顶部 2026-10-21 第二轮那段 |

**这一版没有走"放行"**：把「1080p毛边全消」从副标题撤掉、把"视野别一次拉满 vs 推荐拉满"统一成一句、
大字从"改完抗锯齿毛边变少的分辨率 1080p"换成"5 档"，硬伤自己变成 0。
待核的五个点（CMAA2 写法、VRS 名称、法术密度档位、视野档位、"模式关闭"是哪一项）
全部留在"要核"的位置，**一个都没升格成卖点或效果承诺**——这正是复核件要的"待核项不得升格"。

## 验证与退出码

解释器一律 `env -u PYTHONHOME -u PYTHONPATH /usr/local/bin/python3`（在 `video2text` 仓库根）。

| 命令 | 结果 | 退出码 |
|---|---|---|
| `scripts/e2e_frame_judge.py`（新增） | `FRAME_JUDGE_OK` | 0 |
| `scripts/e2e_guide_gate.py`（A–I 九段） | `GUIDE_GATE_OK` | 0 |
| `scripts/agent/ui_guide_gate_walk.py`（重写，20 项断言） | `GUIDE_GATE_WALK_OK` | 0 |
| `bash .qoder/skills/graphics-verify/scripts/run_graphics_checks.sh`（五条线） | `ALL_OK 出图与调度回归五条线全绿` | 0 |
| `scripts/agent/poster_test_server.py --db output/video2text.db` / `--poster-out output/poster` | 两次都 `REFUSED`（按设计拒绝启动） | 2 / 2 |
| `scripts/agent/render_guide_sample.py --summary 83 --plan temp/plan83_revised.json --out output/样稿/2026-10-21-83 --judge` | `RENDER_SAMPLE_OK`；三页 PNG 落样稿目录；`publishable=true`、硬伤 0、`cost_yuan_estimate=0`；线上 83 manifest sha 前后一致 | 0 |
| `py_compile`（frame_pool／ai_poster／fact_gate／web\/app／三个脚本）+ staged 三份 blob 的 `py_compile` 与 `node --check` | 无输出 | 0 |
| `git diff --check`（本轮提交范围） | 无空白错误 | 0 |

提交归属：`video2text` 三个提交 `5c65cfe`、`f53edcd`、`352b7b3`，**只含本轮自己的 hunk**。
`src/ai_poster.py`、`web/app.py`、`web/templates/index.html`、`CHANGELOG_FOR_AI.md` 在工作区仍显示 modified，
那是另一条会话未提交的活（发布标题、排产任务、抖音图文）——本轮按 op 点名重建 staged blob，
并断言 blob 里不含别人那批标记，既没替别人提交，也没回滚他们的改动。

## 没验到的（不能用桩的结果顶替）

1. **真收费模型的产出质量**：走查里出图那一跳被桩拦住（刻意如此），"闸口放行后模型画出来的图好不好"本轮没验。
2. **83 那五处「待核」**：要人进游戏看，本轮一律留在"要核"位置。
3. **手机端整页**：三页样稿只在 1080px 宽的成品图上看过，375px 下字会不会挤没验。
4. **线上 83/85/87 当前图像版本**：没打开过任何平台后台，没发布、没登记。
5. **6 张悬空帧与旧缓存里那批 `clean=true`**：只定位并报了因，没重抽帧、没重跑判帧（只有 83 用到的 4 张是本轮真重判的）。
6. **判帧失败后的真机重试成本**：桩测证明"下次会重问"，真模型连续抖动时的花费没量过。

## 复核件里 R2 那条未跟踪入口

`docs/README.md` 与 `docs/PROJECT-INDEX.{json,md}` 的未提交状态**不在本轮处理范围**（复核件写明
"第一轮负责者需单独提交，Qoder 不应代替别人批量提交"）。本轮只把 R2 的结论限定成
**"仅当前工作区有效"**，等第一轮负责者收尾未跟踪入口。

停在 Codex 验收点：不自动发布、不动公众号/雷达、不扩大清理范围。
