#!/usr/bin/env bash
# 起本地预览，一条命令把新站拉起来并告诉你该开哪个地址。
#
#   bash tools/serve.sh          # 起（已在跑就报现状，不重复起）
#   bash tools/serve.sh stop     # 关（只关这个端口上的进程）
#
# 2026-10-24 旧站删除，:8817 那一档一起撤：仓库里只剩 app/ 这一个站。
# 端口仍是 8821，README 与 AGENTS.md 里那句"serve.sh 起新站"对得上。
# 注意 vite preview 服务的是 app/dist，且带 SPA 兜底（不存在的文件也回 200 + index.html）——
# 人眼看界面够用；判"缺文件是不是真 404"要用 tools/pkg-verify.py，它起的是严格的静态服务。
set -euo pipefail

WEB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PORT="${APP_PORT:-8821}"

listening() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
pids_on() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | tr '\n' ' '; }

stop_all() {
  local pids
  pids="$(pids_on "$APP_PORT")"
  if [ -n "$pids" ]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    echo "已关 :$APP_PORT（PID $pids）"
  else
    echo ":$APP_PORT 本来就没在跑"
  fi
}

start_all() {
  if listening "$APP_PORT"; then
    echo "新站已在 :$APP_PORT（PID $(pids_on "$APP_PORT")）"
  elif [ -d "$WEB/app/dist" ]; then
    (cd "$WEB/app" && nohup npx vite preview --port "$APP_PORT" >/tmp/wow-serve-app.log 2>&1 &)
    sleep 3
    curl -sf -o /dev/null "http://127.0.0.1:$APP_PORT/" \
      || { echo "新站起不来，看 /tmp/wow-serve-app.log"; exit 1; }
    echo "新站起在 :$APP_PORT（它服务的是 app/dist，改过 app/src 或 app/data 要先 npm run build）"
  else
    echo "新站没构建过（缺 app/dist）：cd app && npm run build"
    exit 1
  fi
}

case "${1:-start}" in
  stop) stop_all ;;
  start) start_all
    echo
    echo "看新站（21 条路由，唯一在做的产品）：http://127.0.0.1:$APP_PORT/"
    echo "手机尺寸自查：浏览器 devtools 切 375×812，或 bash tools/site-check.py 出的截图在 docs/screenshots/"
    ;;
  *) echo "用法：bash tools/serve.sh [start|stop]"; exit 2 ;;
esac
