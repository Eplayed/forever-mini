# W01 / W01-R1 运行日志摘要（2026-10-20）

完整日志留在本机 `wow-forever-web/docs/logs/2026-10-20-W01/`。**仓库 `.gitignore` 第 9 行是 `*.log`，
这些全文进不了 git，全新克隆不含它们**（按 2026-10-20 独立验收的决定：不改 `.gitignore` 放行全部日志，
也不靠改后缀绕过）。所以这里把每条命令的**所测提交、命令、退出码、测试计数、相对路径与 SHA-256** 记进库，
供核验；SHA 只能证明"这份文件当时是这个内容"，不代替日志本体存档。

时间列在本机文件的 mtime 里，表内省略。

## W01（实现轮）
| 日志文件 | 命令 | 所测提交 | rc | 计数 / 结果 | SHA-256(前16) |
| --- | --- | --- | --- | --- | --- |
| `site-check-app-full.log` | `python3 -u tools/site-check.py --app` | `fe49822 之前（W01 实现全跑）` | 0 | 896/896，0 FAIL | `e2af1eca21ba123f` |
| `site-check-only-world-pins.log` | `python3 tools/site-check.py --app --only world_pins` | `fe49822 之前` | 0 | 26/26 | `b3d361e15f55013e` |
| `site-check-only-after-releases.log` | `python3 tools/site-check.py --app --only updates_rank,app,world_pins` | `39bf372+8022bf3` | 0 | 120/120 | `8dcbf7f3941de2d0` |
| `vitest.log` | `cd app && npx vitest run` | `fe49822 之前` | 0 | 100/100（9 文件） | `c95bba4ebdb3a35b` |
| `build-data.log` | `node tools/build-data.js` | `8022bf3` | 0 | 校验通过；缺图登记 161 | `6088edadb0815937` |
| `export-mini.log` | `node tools/export-mini.js` | `8022bf3` | 0 | for-mini 零改动 | `08b01335d5aa5e72` |
| `app-build.log` | `cd app && npm run build` | `8022bf3` | 0 | vite 构建通过 | `af122045c9cdab21` |
| `route-smoke.log` | `python3 tools/route-smoke.py` | `8022bf3` | 0 | 26 条 0 问题；放行 2 次 | `f7b82952465631e7` |
| `route-smoke-first-attempt-crash.log` | `python3 tools/route-smoke.py --shots（第一次）` | `8022bf3` | 非 0 | Chromium SIGSEGV，未记进退出码（旧版缺陷） | `f4599391a5bee535` |
| `route-smoke-shots-crash-2.log` | `python3 tools/route-smoke.py --shots（第二次）` | `8022bf3` | 非 0 | 同上 | `f4599391a5bee535` |
| `audit-assets.log` | `python3 tools/audit-assets.py --refresh --fetch` | `8022bf3` | 0 | 161 键当天全部重问 | `b5e2a5fae874a00f` |
| `audit-assets-first-crashed.log` | `同上第一次` | `8022bf3` | 1 | NameError: load（自己删扫描块时删掉了 helper） | `aed323e0c0ab8793` |

## W01-R1（返修轮：两处校验漏洞）

R1 只改 `tools/build-icon-map.py` 与 `tools/route-smoke.py`，**没动共享数据、没动界面**，
所以按验收要求不重跑整站 896 条（那是 W01 那一段的历史结果，原样留在上面的表里，不与本轮混记）。

## 关键断言原文（W01 全跑里摘的）
```
  PASS  猎人 PvE 联盟那排属性合计等于门禁独立解析的结果  — 界面 ['5力量', '118敏捷', '68耐力', '9智力', '4精神', '615护甲'] ／ 数据 ['5力量', '118敏捷', '68耐力', '9智力', '4精神', '615护甲']
  PASS  没有底图的区域不再留空图框：图框只给有图的区域，无图那几张换成整宽紧凑布局  — 图框 36（数据有图 36）/ 紧凑态 8（数据缺图 8）
通过 896 / 896
SITE_CHECK_RC=0
```
| 日志文件 | 命令 | 所测提交 | rc | 计数 / 结果 | SHA-256(前16) |
| --- | --- | --- | --- | --- | --- |
| `r1-icon-gaps-selftest.log` | `python3 tools/build-icon-map.py --selftest` | `bfeb171` | 0 | 夹具 11 条全过 | `cca2922a202d5973` |
| `r1-route-smoke-selftest.log` | `python3 tools/route-smoke.py --selftest` | `bfeb171` | 0 | 注入回归 8 条全过 | `c23e762bd0c25372` |
| `r1-route-smoke-only-shots-first-fail.log` | `python3 tools/route-smoke.py --only-shots（修后第一次）` | `bfeb171` | 1 | 截图 1 处崩 + 断言 1 处不过 → 如实非 0（旧版会报 0） | `1258d3a152d7f1ad` |
| `r1-route-smoke-only-shots.log` | `python3 tools/route-smoke.py --only-shots` | `bfeb171` | 0 | 5 处全过；摘要明写路由未执行 | `5dcd218710283e04` |
| `r1-route-smoke-shots-full.log` | `python3 tools/route-smoke.py --shots` | `bfeb171` | 0 | 26 条 0 问题 + 截图 5 处 0 失败 | `7eab14ddb19ee54c` |
| `r1-vitest.log` | `cd app && npm test` | `bfeb171` | 0 | 100/100 | `288b502dda3adb25` |
| `r1-app-build.log` | `cd app && npm run build` | `bfeb171` | 0 | vite 构建通过 | `d71711564b02525d` |
| `r1-build-data-first.log` | `node tools/build-data.js（修扫描器后）` | `bfeb171` | 0 | 校验通过；缺图登记 161 | `fad0207301e67da5` |
| `r1-build-data-final.log` | `node tools/build-data.js（收尾）` | `bfeb171` | 0 | 同上 | `fad0207301e67da5` |

