# 按任务执行的验证基线

本文件从根 `AGENTS.md` 原文移出。按实际改动范围读取；不要为了小改动无条件执行不相关的全套验证。

## 六、验证基线

1. 改动数据后必跑：`cd wow-forever-web && node tools/build-data.js`（非 0 退出即未完成）。
2. 改小程序产物后加跑：`node wow-forever-web/tools/export-mini.js`（超主包预算即失败；重跑后 `git status` 应为空，产物必须可复现）。
3. 界面改动必须有渲染证据，构建通过不算完成：
   - 站点：只有 `app/` 这一个站。人看用 `cd wow-forever-web && bash tools/serve.sh`（新站 :8821），
     + 无头 Chrome 截图，存 `wow-forever-web/docs/screenshots/`（桌面 + 375px 移动端）；
     界面回归用 `python3 tools/site-check.py`（**这条是唯一的界面门槛**：它自己起静态服务打 `app/dist`，
     所以跑之前必须 `cd app && npm run build`，否则断言全打在旧产物上）。
     2026-10-24 旧站删除后 `--app` 旗标只是兼容旧命令；`tools/app-parity.py`（两栈对拍）随旧站一起删除。
   - 小程序：微信开发者工具（`cli auto --project for-mini --auto-port 9421` + automator）截图，存 `for-mini/docs/screenshots/`。
4. 点击类动作在本机 automator 上会稳定超时（`element.tap()`、带 setData 回调的 `callMethod()`），拿不到证据时**必须在验证记录里单列"没验到的"并要人工手测**，不许用 `page.setData` 造出来的示意截图冒充逻辑通过。
5. 每轮结束在仓库根 `ROLES.md` 的交接记录表加一行，带 `已定 / 待用户确认 / 阻塞（原因）` 状态。


