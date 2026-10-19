#!/bin/bash
# NGA 无限板块每日采集 —— 给 launchd 调的执行体
# 为什么单独包一层：launchd 不读你的 .zshrc，PATH 和 HOME 都得自己交代清楚，
# 出问题时要有一个固定的日志地方可查。
set -u

REPO="/Users/zhangyajun/Documents/project/wow-forever/wow-forever-web"
PY="/Library/Frameworks/Python.framework/Versions/3.9/bin/python3"
LOG="$HOME/.nga/daily.log"

[ -x "$PY" ] || PY="$(command -v python3)"
[ -r "$HOME/.nga/cookie.txt" ] || echo "$(date '+%F %T') ! 没有 ~/.nga/cookie.txt，board 模式会跳过，只跑 hot" >> "$LOG"

cd "$REPO" || { echo "$(date '+%F %T') ! 进不去仓库目录" >> "$LOG"; exit 1; }

{
  echo "===== $(date '+%F %T') 开始 ====="
  # 列表 2 页 + 最多 60 条正文：按这座板块现在的发帖量，一天两次这个量够了
  "$PY" tools/scrape-nga-forever.py all --pages 2 --max-body 60
  rc=$?
  echo "----- 退出码 $rc -----"
  exit $rc
} >> "$LOG" 2>&1
