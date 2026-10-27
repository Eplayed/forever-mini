# 任务台 · 全机自动任务管理页 规格与风险（2026-10-27）

本轮角色：wow-dev ｜状态：**待用户确认三件事后才开工**（见第八节）

站主选的是第一期就做**完整控制**（改周期、启停、立即执行）。写动作一旦能改 crontab 与 launchd，
就有把正在跑的任务弄停的风险，所以这份文档先给边界、备份与回滚，再给实现顺序。

## 一、这机器上现在有四种调度机制（实测盘点，2026-10-27 14:20）

| 家族 | 条目 | 周期 | 实测状态 |
| --- | --- | --- | --- |
| 系统 cron | p2-database 数据管线 `auto_daily.sh` | 每天 09:00 | 在跑（今天 09:26 有日志与产物） |
| 系统 cron | 自媒体 头条自动写稿 `dify_auto_publish.py` | 周日/一/三/五 08:00 | **空转**：命令行带 `TOUTIAO_AUTOGEN_OFF=1`，目录里另有 `PLAN_AUTOGEN_DISABLED`；日志连续三天（10-23/25/26）都只打一句"已停用"就退出 |
| launchd | `com.wowforever.nga-daily` | 08:40 / 20:40 | 正常，退出码 0，最新快照 `board-2026-10-27.json` |
| launchd | `com.zhangyajun.aihub-scan` | （plist 里读） | 退出码 0 |
| launchd | `com.zhangyajun.haosailei.asr` | 每天 23:40 | **坏的**：退出码 **126**，err 日志整页 `Operation not permitted`（launchd 读不到 `~/Documents`）。它指的那条脚本 `scripts/run_full_asr_once.sh` 还是未入库的散文件 |
| 应用进程内 | video2text 4 组订阅同步（魔兽世界/抖音 07:30、AI 07:40、微信 09:30）+ 夜间匹配 22:00 | 见 `config/sync_tasks.json` / `plan_match.json` | 今天三条 `last_status=ok`；**工作台不开就不跑** |
| 应用进程内 | 5177 小程序产线管线（浏览器驱动） | 页面里配 | 服务在听；页面不开同样不跑 |
| Qoder 定时 | 「排产日报 每天 08:30」（Asia/Shanghai） | cron `30 8 * * *` | 上次 `succeeded`，用时 90 秒，merged 输出 |

**两个结构性事实决定设计**：

1. **launchd 起的进程读不到 `~/Documents`**（TCC）。所以任务台自己的采集器不能把代码放在 Documents 里，
   否则它就是第二个 ASR。
2. **第三家族"没跑"和"应用没开"是两回事**，而管理页如果寄生在其中一个应用里（比如塞进 15801），
   那应用关着的整天，管理页也看不到——**恰好是它最该报警的时候**。所以采集器必须是独立于各应用的进程。

## 二、形状：一个家目录采集器 + 一份状态 JSON + 一个页面

```
~/.taskboard/collect.py     只读探测四家族，写 status.json（launchd 每 30 分钟跑一次）
~/.taskboard/status.json    唯一一份机器事实（页面只读它，不各自再算一遍）
~/.taskboard/registry.json  每条任务的"成功判据"声明（见第四节）
~/.taskboard/backup/        每次写动作前的原件快照
~/.taskboard/audit.log      谁在什么时候改了什么、改前回滚路径
~/.taskboard/server.py      页面（Flask，127.0.0.1 固定端口，建议 15830）
```

**为什么不塞进 video2text 的 `web/app.py`**：① 那文件此刻正被另一个会话写（75 处未提交，含 `DB_ONLY_SHEETS`）；
② 任务台管的是全机器，不该寄生在它管理的项目之一里；③ 代码放 `~/.taskboard/` 才让 launchd 采集器也读得到（避开 TCC）。

## 三、每家族用什么手段（读与写分开）

| 家族 | 读状态 | 立即执行 | 改周期 / 启停 |
| --- | --- | --- | --- |
| launchd | `launchctl list` 的 PID+退出码；plist 的 `StartCalendarInterval`；`StandardOutPath`/`StandardErrorPath` 的 mtime 与末尾行 | `launchctl kickstart -k gui/$UID/<label>` | 改 plist 的调度字段 → `launchctl bootout/bootstrap`（**先备份 plist 原件**） |
| 系统 cron | `crontab -l` 逐行；日志 mtime 判"有没有真动" | `launchctl kickstart` 不行，只能手动跑那条命令 | 写 `crontab`（**先 `crontab -l > backup`**，整表覆盖，风险最高的一格） |
| 应用进程内 | 读它们自己的配置与 `last_run/last_status`；再用端口探测判断"应用在不在" | 调它们的 HTTP 接口（15801 已有采集接口） | 由页面写它们的配置文件（`sync_tasks.json` 那类），**周期值不进代码** |
| Qoder 定时 | 只能由 agent 用 `qoder_cron list` 读，**本地没有公开接口** | 同上，需要 agent 在场 | **第一版不做**，见第五节 |

## 四、状态判定不能把字符串写死在代码里

现在那四条 cron/plist 的"成功"含义各不相同，判据必须由 `registry.json` 声明、页面照着算：

```
{"label": "toutiao-autogen",
 "probe": {"log": "…/dify/scheduler/cron.log", "expect_line": null,
           "off_markers": ["TOUTIAO_AUTOGEN_OFF", "PLAN_AUTOGEN_DISABLED"]},
 "note": "触发但空转，不是失败"}
```

- **`off_markers` 命中 → 判"已停用"，不是"成功"也不是"失败"**。头条那条就是这种：它每天真的在触发。
- ASR 那种 → 判"失败（TCC）"，因为 `launchctl` 退出码 126 + err 日志关键字 `Operation not permitted`。
- 进程内那组 → 判"应用没开"要区别于"应用开着但今天没跑"，两个词在页面上必须分开写，
  不许合并成"未执行"。**这条是站主 10-22 抓过的老毛病（选项白放/状态说谎），别再犯。**

## 五、Qoder 那条家族：第一版只能只读

Qoder 的定时任务由 Qoder 应用自己管，本地程序没有稳定接口；能动的只有 agent 侧的 `qoder_cron`。
所以"完整控制"在这一格有硬边界：页面**能显示**（靠 agent 定期把 `list` 结果写进 `status.json`，
或首次启动手动同步一次），**不能改**。要么接受这条限制，要么把这条任务改成 launchd 跑同一个脚本
（但 8:30 那条日报本质是让模型读结论汇报，不是纯脚本，搬不动）。这一条要站主明确点头。

## 六、写动作的安全设计（照本站 OSS 写闸的先例）

1. 只绑 `127.0.0.1`；启动时在终端打印一次性 token，页面所有写请求带这个 token。
2. 校验 `Origin`/`Referer` 是本机来源，拒外部页面跨站打这个口。
3. **两道确认**：前端一次 confirm，后端要求 `--yes`/body 里带明确动作名，二者不匹配就拒。
4. 每次写之前把**原件**复制进 `backup/<时间戳>/<原路径>`，`audit.log` 记一行（动作、目标、备份路径、结果）。
5. 删除任务这一类**不在第一期做**；非要做就要求输入任务名本身当确认（对齐 `oss-release.js` 里
   `clean --env release` 必须再加 `--yes-release` 那条规矩）。
6. `crontab` 是整表覆盖，最危险：页面只能改现有行的字段（时刻/开关），
   不允许通过页面新增任意命令；写之前 `crontab -l` 存一份，写完立刻回读校验一次，
   回读不一致就自动恢复备份并报错（**不许"写了就当成功"**）。
7. 页面不存任何凭证；`~/.nga/cookie.txt` 这类只允许被"探测存在与否"，永不显示内容。

## 七、分期与工作量

- **P0（先做，只读，零风险）**：`collect.py` + `status.json` + 一页表格，把第一节那张盘出来的表变成活的，
  并高亮"126 / 空转 / 应用没开 / 超过 N 小时没跑"。这一步就已经能回答"今天到底有没有在动"。
- **P1**：立即执行（launchd kickstart、应用接口触发），带 token 与两道确认。
- **P2**：改周期与启停（plist / crontab / sync_tasks.json），带备份与"写完回读校验+自动恢复"。
- P0 与 P1 可以同一轮做完；**P2 建议单独一轮**，因为它需要你先看过 P0 的数字对不对——
  判据写错的情况下给你改 crontab 的按钮，等于把误判变成事故。

## 八、三件事的结论与 P0 落地（2026-10-27 14:53 更新）

站主答复：**任务台独立起服务**（① 同意）。② 与 ③ 没单独表态，按我的默认走：
Qoder 那一格先只读、P2 不与本轮同做。

### P0 已做完并跑着

| 件 | 位置 | 说明 |
| --- | --- | --- |
| 采集器 | `tools/taskboard/collect.py`（源）→ `~/.taskboard/collect.py`（跑的那份） | 只读，探四家族，写 `~/.taskboard/status.json` |
| 判据登记 | `tools/taskboard/registry.json` | 每条任务的成功/失败/停用判据、预期窗口都在这，**代码里没有一条硬编码关键词** |
| 页面 | `tools/taskboard/server.py` → 127.0.0.1:15830 | 只读一张表 + 一个「重新采集」按钮（它只跑采集器，不碰任何任务） |
| 安装核对 | `tools/taskboard/install.sh --sync/--check/--agent/--unagent` | 照 `~/.nga` 那套：仓库是源，launchd 跑家目录副本（TCC 原因） |
| 定时采集 | launchd `com.zhangyajun.taskboard-collect`，每 30 分钟 | 撤销：`bash tools/taskboard/install.sh --unagent` |

实测一轮（14:52）：8 条任务 → **失败×1、空转×1、正常×6**。

- **失败**：好赛雷 ASR，退出码 126 + 日志命中 `Operation not permitted`，注里写明是 TCC。
- **空转**：头条自动写稿，`0 8 * * 0,1,3,5` 确实每天触发，但命中「已停用」且 `PLAN_AUTOGEN_DISABLED` 在——
  判成"空转"而不是"成功"，也不是"失败"。
- **正常**：NGA 采集（08:41，预期 13 小时内）、p2 管线、AI hub、video2text 两组（订阅同步按每组的上次执行、
  夜间匹配按库里 `plan_match_runs` 最近一次）、Qoder 排产日报（按 agent 同步的快照，注里写"快照只读"）。

截图证据：`docs/screenshots/taskboard-2026-10-27/desktop-1440.png`、`mobile-375.png`。
状态除颜色外**都带文字**（`失败/空转（已停用）/正常`），符合本站"不靠颜色承载信息"那条。

### 已知缺口（下一轮再谈，不假装做完）

1. **P1 立即执行、P2 改周期/启停都没做**——按第六节的分级，那需要 token＋两道确认＋备份回滚，
   且要先看 P0 的判准不准（本轮 8 条判对了 8 条，但"应用没开""超期未跑"两档还没被真实触发过）。
2. Qoder 那一格靠 `~/.taskboard/qoder_cron.json` 快照，**快照不会自己更新**，要 agent 跑一次
   `qoder_cron list` 重写。页面上写明"agent 同步于 …"，不伪装成实时。
3. `video2text 订阅同步` 的"上次动作"取的是四组里最新的那条，**某单独一组停摆时会被别的组掩盖**——
   要精确到组，得让页面把四组分行列出来（P1 顺手做）。
4. 5177 那条产线没进登记表（它的状态文件与判据我还没量过，**没量过就不登记**，免得给个假绿灯）。

## 九、顺带记两笔本次盘点捞到的账（不属本线，但要有人知道）

- `com.zhangyajun.haosailei.asr` **每晚都在失败**，已经失败到日志铺满 `Operation not permitted`。
  修法是 NGA 那套的同一条：把执行体与它读的输入放到 `~/.` 下的家目录位置，或给那个具体二进制授予完全磁盘访问。
  这条归 video2text，不在本线改动范围内，我没动。
- 头条自动写稿那条 cron 与它的两个停用开关（环境变量 + `PLAN_AUTOGEN_DISABLED` 文件）**语义重复**，
  留着会让下一个会话以为"只要 unset 环境变量就恢复了"，实际还要删文件。归自媒体那线。
