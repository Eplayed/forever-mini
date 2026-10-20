# W01 运行日志摘要（2026-10-20）

完整日志在这台机器的 `docs/logs/2026-10-20-W01/` 下，但仓库 `.gitignore` 第 9 行是 `*.log`，
**它们进不了 git**（与 Q01A 那轮同一件事，改 .gitignore 加一条 `!docs/logs/**/*.log` 是仓库级决定，我没自己改）。
所以这里把每条命令的收尾与关键断言原样抄一份进 git，验收方不必依赖我的 /tmp。

要长期留住完整日志，需要给 `.gitignore` 加一条 `!docs/logs/**/*.log`——那是仓库级决定，我没自己改。

## site-check-app-full.log —— 整站 --app 全跑（896/896，rc 0）
```
  PASS  这一套每条带护甲的行都落进了已知写法（新写法不许静默漏算）  — 计入基础护甲 9 行 / 加成与效果句 0 行 / 没认出来：无
  PASS  猎人 PvE 联盟那排属性合计等于门禁独立解析的结果  — 界面 ['5力量', '118敏捷', '68耐力', '9智力', '4精神', '615护甲'] ／ 数据 ['5力量', '118敏捷', '68耐力', '9智力', '4精神', '615护甲']
  PASS  配装页 375 不横向溢出  — {"over": 0, "small": 0}
  PASS  没有底图的区域不再留空图框：图框只给有图的区域，无图那几张换成整宽紧凑布局  — 图框 36（数据有图 36）/ 紧凑态 8（数据缺图 8）
通过 896 / 896
SITE_CHECK_RC=0
```

## site-check-only-world-pins.log —— world_pins 小节探针
```
  PASS  整张图都标不出点的区域，仍然写明这是哪张地图的编号，不留空盒  — 8 张没图的：['地图编号 2548', '地图编号 2652', '地图编号 1424', '地图编号 1430', '地图编号 1440', '地图编号 1449', '地图编号 1451', '地图编号 1457']
  PASS  没有底图的区域不再留空图框：图框只给有图的区域，无图那几张换成整宽紧凑布局  — 图框 36（数据有图 36）/ 紧凑态 8（数据缺图 8）
通过 26 / 26
```

## vitest.log —— 新站单测 100/100
```
 Test Files  9 passed (9)
      Tests  100 passed (100)
```

## build-data.log —— 数据卡口
```
物品名录：21077 件（无限新增 5346）·抓取日 2026-10-13
  提示 缺图登记 161 个图标键（官方 CDN 没有这些文件，界面退回自绘块），按文件：changes.json 1 / dungeons.json 1 / items.json 159 / legacy.json 2 / professions.json 77 / spells.json 1 / world.json 9
校验通过
```

## export-mini.log —— 小程序产物导出
```
导出完成 → for-mini
  快照词条 60 条，合计 25.5 KB（预算 60 KB）
```

## route-smoke.log —— 26 条路由生产构建冒烟
```
  副本手册                                       OK（1147 张 lazy 图没滚到，按 src 逐个问的服务）
路由 26 条，有问题的 0 条；按缺图登记放行的取不到共 2 次
```

## audit-assets.log —— 素材缺口审计（当天重问）
```
引用图标键 3454 个，本地 3294 张，缺 161 个
区域小地图：数据里没图的 9 张，上游状态 1424=404、1430=404、1440=404、1449=404、1451=404、1453=404、1457=404、2548=404、2652=404
报告 → docs/ASSET-GAPS-2026-10-20.md
AUDIT_RC=0
```

## audit-assets-first-crashed.log —— 第一次审计：跑到一半 NameError rc=1
```
其它区域能取到 2 个：flightstone-blue、inv_10_worlddroplevelingoptionalreagent_archaeology_trolltooth_color2
NameError: name 'load' is not defined
AUDIT_RC=1
```

## route-smoke-first-attempt-crash.log —— 第一次带截图的冒烟：Chromium SIGSEGV
```
Traceback (most recent call last):
playwright._impl._errors.TargetClosedError: Target page, context or browser has been closed
[pid=29159] <process did exit: exitCode=null, signal=SIGSEGV>
```

