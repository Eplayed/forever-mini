#!/usr/bin/env bash
# 起本地预览，一条命令把两个站都拉起来，并告诉你该开哪个地址。
#
#   bash tools/serve.sh          # 起（已在跑就报现状，不重复起）
#   bash tools/serve.sh stop     # 关（只关这两个端口上的进程）
#
# 端口为什么是 8817 / 8821：tools/app-parity.py 默认就连这两个（旧站 :8817、新站 :8821），
# 预览端口和对拍端口对齐，才不会出现"页面能看但对拍脚本说连不上"。
# README 与两份 AGENTS.md 里以前写的 8812 只是手起服务的习惯端口，不是卡口要求的，
# 用这个脚本就不用记端口号了。
set -euo pipefail

WEB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEGACY_PORT="${LEGACY_PORT:-8817}"
APP_PORT="${APP_PORT:-8821}"

listening() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
pids_on() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | tr '\n' ' '; }

stop_all() {
  local pids
  for port in "$LEGACY_PORT" "$APP_PORT"; do
    pids="$(pids_on "$port")"
    if [ -n "$pids" ]; then
      # shellcheck disable=SC2086
      kill $pids 2>/dev/null || true
      echo "已关 :$port（PID $pids）"
    else
      echo ":$port 本来就没在跑"
    fi
  done
}

start_all() {
  if listening "$LEGACY_PORT"; then
    echo "旧站已在 :$LEGACY_PORT（PID $(pids_on "$LEGACY_PORT")）"
  else
    (cd "$WEB/src" && nohup python3 -m http.server "$LEGACY_PORT" >/tmp/wow-serve-legacy.log 2>&1 &)
    sleep 1
    curl -sf -o /dev/null "http://127.0.0.1:$LEGACY_PORT/index.html" \
      || { echo "旧站起不来，看 /tmp/wow-serve-legacy.log"; exit 1; }
    echo "旧站起在 :$LEGACY_PORT"
  fi

  if listening "$APP_PORT"; then
    echo "新站已在 :$APP_PORT（PID $(pids_on "$APP_PORT")）"
  elif [ -d "$WEB/app/dist" ]; then
    (cd "$WEB/app" && nohup npx vite preview --port "$APP_PORT" >/tmp/wow-serve-app.log 2>&1 &)
    sleep 3
    curl -sf -o /dev/null "http://127.0.0.1:$APP_PORT/" \
      || { echo "新站起不来，看 /tmp/wow-serve-app.log"; exit 1; }
    echo "新站起在 :$APP_PORT（注意：它服务的是 app/dist，改过 app/src 或 src/css 要先 npm run build）"
  else
    echo "新站没构建过（缺 app/dist）：cd app && npm run build，或先只看旧站"
  fi
}

case "${1:-start}" in
  stop) stop_all ;;
  start) start_all
    echo
    echo "看整站 16 页（当前可发布口径）：http://127.0.0.1:$LEGACY_PORT/index.html"
    echo "看 Vue 新站（只迁了首页与世界页）：http://127.0.0.1:$APP_PORT/"
    echo "手机尺寸自查：浏览器 devtools 切 375×812，或 bash tools/site-check.py 出的截图在 docs/screenshots/"
    ;;
  *) echo "用法：bash tools/serve.sh [start|stop]"; exit 2 ;;
esac
