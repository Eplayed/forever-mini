#!/bin/bash
# NGA 无限板块每日采集 —— launchd 执行体（这份是源，装到 ~/.nga 才生效）
#
# 为什么源在仓库、跑的是 ~/.nga 里的副本：macOS 的 TCC 不让 launchd 起的进程读
# ~/Documents，直接指仓库脚本会报 "Operation not permitted"（同机那条
# com.zhangyajun.haosailei.asr 每晚 23:40 就是这么失败的，退出码 126）。
# 所以副本、数据、日志都在 ~/.nga，脚本里**不许出现仓库路径**——包括下面那段导入。
#
# 用法：
#   bash tools/nga-daily.sh              # launchd 用的默认动作：抓 → （可选）导
#   bash tools/nga-daily.sh --sync       # 把仓库这份与 scrape 脚本装到 ~/.nga（人工在终端跑，它有 Documents 权限）
#   bash tools/nga-daily.sh --check      # 只读体检：副本与源是否漂移、launchd 在不在、数据新不新
#   bash tools/nga-daily.sh --only-import # 只跑导入那一步（不碰网络，用来验接线）
set -u

REPO="/Users/zhangyajun/Documents/project/wow-forever/wow-forever-web"
HOME_DIR="$HOME/.nga"
RUN_SCRIPT="$HOME_DIR/nga-daily.sh"
RUN_SCRAPER="$HOME_DIR/scrape-nga-forever.py"
LOG="$HOME_DIR/daily.log"
PY="/Library/Frameworks/Python.framework/Versions/3.9/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

# 导入这一步默认关着，原因不是没想到，是量过之后确认做不到：
# 导入器在 ~/Documents/project/video2text，要写的库也在 ~/Documents，
# launchd 起的进程读不到，开着只会让每次采集多一条失败记录。
# 号主把这条通道换到"有人登录的会话"里去跑（工作台定时器或 Qoder 定时任务），
# 见 wow-forever-web/docs/DATA-NGA-2026-10-18.md 的「采集之后导给谁跑」。
V2T="${V2T_DIR:-/Users/zhangyajun/Documents/project/video2text}"
NGA_IMPORT="${NGA_IMPORT:-0}"

sync_copies() {
  if [ ! -r "$REPO/tools/nga-daily.sh" ]; then
    echo "! 这份是运行副本（REPO 已被改成 ~/.nga）。装副本要在仓库里跑：bash tools/nga-daily.sh --sync"
    return 1
  fi
  mkdir -p "$HOME_DIR"
  for f in "$REPO/tools/nga-daily.sh" "$REPO/tools/scrape-nga-forever.py"; do
    [ -r "$f" ] || { echo "! 源文件读不到：$f"; return 1; }
  done
  for t in "$RUN_SCRIPT" "$RUN_SCRAPER"; do
    [ -f "$t" ] && cp "$t" "$t.bak-$(date +%Y%m%d-%H%M%S)"
  done
  # 运行体的路径口径就是 ~/.nga：副本里不能留仓库路径，否则等于把 TCC 坑装回去
  sed "s|^REPO=.*|REPO=\"$HOME_DIR\"|" "$REPO/tools/nga-daily.sh" > "$RUN_SCRIPT"
  cp "$REPO/tools/scrape-nga-forever.py" "$RUN_SCRAPER"
  chmod +x "$RUN_SCRIPT" "$RUN_SCRAPER"
  echo "已装好：$RUN_SCRIPT"
  echo "已装好：$RUN_SCRAPER"
  echo "下一步核对：bash tools/nga-daily.sh --check"
}

check_drift() {
  rc=0
  if [ ! -r "$REPO/tools/nga-daily.sh" ]; then
    echo "! 这份是运行副本（REPO 已被改成 ~/.nga）。体检要在仓库里跑：bash tools/nga-daily.sh --check"
    return 1
  fi
  for pair in "$REPO/tools/nga-daily.sh|$RUN_SCRIPT" "$REPO/tools/scrape-nga-forever.py|$RUN_SCRAPER"; do
    src="${pair%%|*}"; dst="${pair##*|}"
    [ -f "$dst" ] || { echo "! 缺运行副本 $dst（跑 --sync）"; rc=1; continue; }
    # 装过去的时候 REPO 那一行是有意改掉的，比漂移时跳过它，别把设计当差异
    if diff -q <(grep -v '^REPO=' "$src") <(grep -v '^REPO=' "$dst") >/dev/null 2>&1; then
      echo "一致  $(basename "$dst")"
    else
      echo "漂移  $(basename "$dst")（差 $(diff <(grep -v '^REPO=' "$src") <(grep -v '^REPO=' "$dst") | grep -c '^[<>]') 行，跑 --sync 覆盖；副本见 *.bak-*）"
      rc=1
    fi
  done
  # 运行副本的执行行里不许有 launchd 读不到的 Documents 路径（注释里提到不算）——126 那一类故障的形状
  if grep -v '^[[:space:]]*#' "$RUN_SCRIPT" 2>/dev/null | grep -q "$HOME/Documents"; then
    if grep -q 'NGA_IMPORT="\${NGA_IMPORT:-1}"' "$RUN_SCRIPT" 2>/dev/null; then
      echo "! 副本默认开着导入，可 launchd 读不到 Documents，这一步每晚都会失败——把默认改回 0，或换到有人登录的会话跑"
    else
      echo "备注  副本执行行里有个 Documents 路径（video2text 的库），导入默认关着所以不影响采集；要真开，改走工作台定时器或 Qoder 定时任务"
    fi
  fi
  if launchctl list 2>/dev/null | grep -q "com.wowforever.nga-daily"; then
    echo "launchd 已加载 com.wowforever.nga-daily（退出码 $(launchctl list | awk '/com.wowforever.nga-daily/{print $2}')）"
  else
    echo "! launchd 没加载这个任务（登录会话里 launchctl load -w ~/Library/LaunchAgents/com.wowforever.nga-daily.plist）"; rc=1
  fi
  latest=$(ls -1 "$HOME_DIR"/data/board-*.json 2>/dev/null | tail -1)
  echo "最新快照 $(basename "${latest:-无}") ｜ $(tail -3 "$LOG" 2>/dev/null | grep -o '退出码 [0-9]*' | tail -1)"
  return $rc
}

run_import() {
  # 只有显式打开才试，且失败绝不影响采集那一步的退出码
  [ "$NGA_IMPORT" = "1" ] || { echo "导入那一步没开（NGA_IMPORT=0；launchd 读不到 Documents，说明见文件头）"; return 0; }
  if [ ! -r "$V2T/src/nga_import.py" ]; then
    echo "! 找不到 $V2T/src/nga_import.py，跳过导入，快照照常产出"
    return 0
  fi
  "$PY" "$V2T/src/nga_import.py" || echo "! 导入这一步报错（采集已成功，不追回）"
}

case "${1:-run}" in
  --sync) sync_copies ;;
  --check) check_drift ;;
  --only-import) run_import ;;
  run|"")
    export NGA_DATA_DIR="$HOME_DIR/data"
    {
      echo "===== $(date '+%F %T') 开始 ====="
      [ -r "$HOME_DIR/cookie.txt" ] || echo "! 没有 ~/.nga/cookie.txt，board 模式会跳过，只跑 hot"
      "$PY" "$HOME_DIR/scrape-nga-forever.py" all --pages 2 --max-body 60
      rc=$?
      echo "----- 采集退出码 $rc -----"
      run_import
      exit $rc
    } >> "$LOG" 2>&1
    ;;
  *) echo "用法：bash tools/nga-daily.sh [--sync|--check|--only-import|run]"; exit 2 ;;
esac
