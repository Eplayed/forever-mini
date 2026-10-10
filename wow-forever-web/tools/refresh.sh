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
#   tools/refresh.sh dungeons    # 副本：首领名单与掉落 + 卡片（两个抓取器都要跑）
#   tools/refresh.sh legacy      # 传承：三棵专长树 + 65 项挑战（句子在落盘前就删）
#   tools/refresh.sh talents     # 天赋树（双源对齐 + 图标）
#   tools/refresh.sh official    # 官方中文稿重抽（技能四态 + 种族）
#   tools/refresh.sh icons       # 只补素材（图标映射 + 官方 CDN + 缺口审计）
#   tools/refresh.sh art         # 只补原画（职业背景 / 副本载入 / 小地图 / 种族头像 / 阵营城市）
#   tools/refresh.sh check       # 只跑门禁，不碰网络
#   tools/refresh.sh publish     # 门禁 + 新站构建 + 小程序导出，全绿才算能发
#
# 详见 docs/DATA-MAINTENANCE.md。
set -euo pipefail
cd "$(dirname "$0")/.."

run() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; "$@"; }

# 所有场景收尾都跑同一套门禁：数据校验 → 图标映射 → 译名逐字回查 → 界面回归
gate() {
  run node tools/build-data.js
  run python3 tools/build-icon-map.py
  run node tools/build-data.js
  run python3 tools/audit-translations.py --strict
  run python3 tools/site-check.py
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
    gate
    ;;
  dungeons)
    # 卡片与首领名单是两个抓取器：只跑 cards 那条，BOSS 与掉落会一直停在第一次抓的版上
    # （2026-10-10 实测：卡片线重跑过，名单还是 235 个 BOSS，而详情页已经是 232 个）
    run python3 tools/scrape-wclbox.py --what dungeons --write
    run python3 tools/scrape-wclbox-dom.py --what cards
    run node tools/merge-dungeons.js
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
  check)
    gate
    ;;
  publish)
    gate
    run python3 tools/build-changelog.py
    run python3 tools/app-assets.py
    run node tools/export-mini.js
    (cd app && npm ci --silent && npx vitest run && npm run build)
    run python3 tools/app-parity.py --strict
    printf '\n\033[1;32m全绿：可以发布。发布动作本身要人工确认（见 docs/DATA-MAINTENANCE.md 第六节）。\033[0m\n'
    ;;
  *)
    awk '/^#   tools\/refresh\.sh/ { print } /^# 详见/ { print; exit }' "$0"
    exit 2
    ;;
esac
