#!/usr/bin/env bash
# 数据刷新与发布的一键入口。
#
# 为什么要它：这条产线有 20 多个脚本，顺序错了会把半成品当成品发出去
# （比如没跑 build-icon-map 就抓图标，或没重跑校验就构建）。这里把每个场景写死一条链路，
# 任何一步非 0 立刻停，不会带着坏数据往下走。
#
# 用法：
#   tools/refresh.sh world       # 世界线（区域 / 稀有 / 书籍 / 睡袋）重抓重整
#   tools/refresh.sh changes     # 客户端改动清单
#   tools/refresh.sh prof        # 专业与配方
#   tools/refresh.sh dungeons    # 副本：首领名单与掉落 + 卡片 + 客户端排队表（四个抓取器都要跑）
#   tools/refresh.sh legacy      # 传承：三棵专长树 + 65 项挑战（句子在落盘前就删）
#   tools/refresh.sh bis         # 配装名单：38 套 + 同部位备选（要开真浏览器点阵营，见 case 里的注释）
#   tools/refresh.sh talents     # 天赋树（双源对齐 + 图标）
#   tools/refresh.sh official    # 官方中文稿重抽（技能四态 + 种族）
#   tools/refresh.sh icons       # 只补素材（图标映射 + 官方 CDN + 缺口审计）
#   tools/refresh.sh art         # 只补原画（职业背景 / 副本载入 / 小地图 / 种族头像 / 阵营城市）
#   tools/refresh.sh status      # 数据体检：还缺什么、哪些我们能补、哪些只能等（报告，不是门禁）
#   tools/refresh.sh check       # 只跑门禁，不碰网络
#   tools/refresh.sh publish     # 门禁 + 新站构建 + 小程序导出，全绿才算能发
#
# 详见 docs/DATA-MAINTENANCE.md。
set -euo pipefail
cd "$(dirname "$0")/.."

run() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; "$@"; }

# 只出报告、不拦人的那一步（2026-10-16 起 app-parity 属于这类：旧站已冻结，
# "新站与旧站不一样"不再是错误）。失败会打一行提醒但继续走。
soft() {
  printf '\n\033[1m▶ %s\033[0m（报告模式，不拦人）\n' "$*"
  "$@" || printf '\033[1;33m  ↑ 这一步报了差异：旧站已冻结，红不代表做错，看一眼理由即可。\033[0m\n'
  return 0
}

# 所有场景收尾都跑同一套门禁：数据校验 → 图标映射 → 译名逐字回查 → 界面回归（含新站）
gate() {
  run node tools/build-data.js
  run python3 tools/build-icon-map.py
  run node tools/build-data.js
  run python3 tools/audit-translations.py --strict
  # --app：新站（Vue）那组断言是硬门槛，端口不通直接失败——2026-10-16 起新站是唯一在做的产品
  run python3 tools/site-check.py --app
  soft python3 tools/app-parity.py --strict
}

case "${1:-}" in
  world)
    run python3 tools/scrape-wclbox-shuju.py
    run node tools/merge-world.js
    gate
    ;;
  changes)
    run python3 tools/scrape-wclbox-changes.py
    run node tools/merge-changes.js
    gate
    ;;
  prof)
    run python3 tools/scrape-wclbox-prof.py --write
    run node tools/merge-professions.js
    # 商人与图纸掉落来自 XR 那份插件（原件在仓库外 .scratch/wow），顺序不能倒：
    # merge-professions.js 会整表重写配方，先并后 merge 会被冲掉
    run python3 tools/extract-xr-prof.py
    run python3 tools/merge-prof-sources.py
    gate
    ;;
  dungeons)
    # 卡片与首领名单是两个抓取器：只跑 cards 那条，BOSS 与掉落会一直停在第一次抓的版上
    # （2026-10-10 实测：卡片线重跑过，名单还是 235 个 BOSS，而详情页已经是 232 个）
    run python3 tools/scrape-wclbox.py --what dungeons --write
    run python3 tools/scrape-wclbox-dom.py --what cards
    # 首领头像：源站的头像文件名是它自己那套首领键（rhahkzor），跟我们存的 id（rhahk-zor）不同名，
    # 只能逐个副本页把真实路径读回来再下，猜地址会大面积 404（2026-10-12 实测踩过一次）
    run python3 tools/scrape-wclbox-dom.py --what bossfaces
    run python3 tools/fetch-art.py --what bosses
    # 客户端排队表与排队元数据：等级区间、进入人数、英文原名的第三方可回查来源
    run python3 tools/scrape-wclbox-shuju.py --group dungeons
    run python3 tools/fetch-db2-groupfinder.py
    run node tools/merge-dungeons.js
    gate
    ;;
  bis)
    # 配装线必须开真浏览器：部落那一版是点 .pz-faction 按钮才换数据的，SSR 只给联盟版
    # （URL 变体与静态接口都试过，全是 404）。抓取阶段就把参考站写的句子与掉率百分比丢掉。
    run python3 tools/scrape-wclbox-bis.py
    run python3 tools/merge-bis.py
    gate
    ;;
  legacy)
    # 抓取脚本在写盘前就把每层效果说明删掉，仓库里不会留下转述句子
    run python3 tools/scrape-wclbox-legacy.py
    run node tools/merge-legacy.js
    run python3 tools/build-icon-map.py
    run python3 tools/fetch-icons.py --from-json src/data/legacy.json --field iconKey
    gate
    ;;
  talents)
    run python3 tools/scrape-wclbox-dom.py --what talents
    run node tools/merge-upstream.js
    run node tools/merge-talents.js
    run python3 tools/build-icon-map.py
    run python3 tools/fetch-icons.py --from-json src/data/talents/hunter.json --field iconKey
    gate
    ;;
  official)
    run python3 tools/extract-abilities.py --write
    run python3 tools/extract-races.py --write --link-glossary
    gate
    ;;
  art)
    run python3 tools/fetch-art.py --what all
    run node tools/build-data.js
    ;;
  icons)
    run python3 tools/build-icon-map.py
    run python3 tools/fetch-icons.py --list
    run python3 tools/audit-assets.py
    gate
    ;;
  status)
    # 体检只说话不拦人：任何一步非 0 都会把后面的链断掉，见 DATA-MAINTENANCE.md 第四节
    run python3 tools/data-status.py
    ;;
  check)
    gate
    ;;
  publish)
    # 先构建新站再跑门禁：site-check --app 连的是 app/dist 的预览端口，
    # 不先 build 会拿上一版产物当这一版验
    (cd app && npm ci --silent && npx vitest run && npm run build)
    gate
    run python3 tools/build-changelog.py
    run python3 tools/app-assets.py
    run node tools/export-mini.js
    printf '\n\033[1;32m全绿：可以发布（发布的是 app/dist）。发布动作本身要人工确认，见 docs/DATA-MAINTENANCE.md 第六节。\033[0m\n'
    ;;
  *)
    awk '/^#   tools\/refresh\.sh/ { print } /^# 详见/ { print; exit }' "$0"
    exit 2
    ;;
esac
