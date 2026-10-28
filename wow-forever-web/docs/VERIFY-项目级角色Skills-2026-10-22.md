# 项目级角色 Skills：路径、同步与验证

日期：2026-10-22｜角色：wow-dev｜状态：**已定（文件与静态校验）／待运行时验证（新 Codex/Qoder/Trae 会话）**。

## 问题与修法

上轮把六份规则只维护在仓库的 `.trae/skills/`。它们是项目文件，但目录只适配特定 agent；仅更新正文并不能证明换到 Codex 或 Qoder 后能自动发现。站主要求角色规则跟项目走、换 agent 仍可用。

现在仓库根 `.agents/skills/wow-{pm,planner,ui,dev,data,ops}/SKILL.md` 是六份**唯一编辑源**。Codex 官方文档说明在仓库根 `.agents/skills` 自动发现项目级 skill；Qoder 官方文档指定项目根 `.qoder/skills/{name}/SKILL.md`。因此保留原 `.trae/skills/`，另加 `.qoder/skills/`，两处都存完整镜像而非只含跳转说明；每个 agent 加载后直接拿到同一份正文。根 `AGENTS.md` 明确了真源与显式回退入口。没有使用 symlink，跨系统检出仍是普通文件。

唯一编辑流程：改 `.agents/skills/` → `python3 wow-forever-web/tools/sync-role-skills.py --write` → 同脚本 `--check`。脚本固定六个角色、核每份 frontmatter `name`、逐字节比较两个镜像；镜像缺失或内容漂移以非零退出。不能直接分别修改 `.trae/skills/` 或 `.qoder/skills/`。

## 已验证

| 检查 | 结果 |
| --- | --- |
| 六份真源 + Trae 六份 + Qoder 六份 | `skill-creator/scripts/quick_validate.py` 对 18 个入口逐个退出 0；名称、frontmatter、格式通过 |
| 同步一致性 | `sync-role-skills.py --check` 退出 0，六个角色在三处逐字节一致 |
| 漂移反例 | 临时目录复制脚本与六份真源：`--write` 生成镜像；改坏 Qoder `wow-pm` 镜像后 `--check` 非零并指名路径；再 `--write` 修复，`--check` 恢复 0。没有碰真实镜像做破坏测试 |
| 工作树 | 只新增项目级 skill、同步脚本和本验证记录，更新根 `AGENTS.md` 与 `ROLES.md`；没有改站点/小程序产品代码或数据 |

## 尚未验证的运行时行为

本机没有 Qoder CLI；`codex --help` 没有只读的技能列表子命令，本轮对话也尚未获得新目录的运行时技能清单。**静态文件检查不能冒充新会话已自动加载**。首次在各 agent 打开本仓库时，应核技能列表中有六个 `wow-*`，再显式调用其中一个并确认其读取路径是项目级文件。Qoder IDE 可重启后用 `/wow-pm` 测试，CLI 可 `/skills reload`；Codex 若未出现，按官方说明重启后重查。即使自动发现失败，根 `AGENTS.md` 仍给出真源路径供 agent 显式读取；问题应记录为“发现失败”，不能说技能机制已完全验收。

官方路径依据：[OpenAI Codex Build skills](https://learn.chatgpt.com/docs/build-skills)、[Qoder IDE Skills](https://docs.qoder.com/extensions/skills)、[Qoder CLI Skills](https://docs.qoder.com/cli/Skills)。
