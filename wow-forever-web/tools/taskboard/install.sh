#!/bin/bash
# taskboard 安装与核对（照 ~/.nga 那套做法：仓库是源，launchd 跑的是家目录副本）
# 为什么副本必须在家目录：launchd 起的进程读不到 ~/Documents（macOS TCC），
# 同机现成反例是 com.zhangyajun.haosailei.asr 每晚退出码 126。
set -u
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME/.taskboard"
LABEL=com.zhangyajun.taskboard-collect
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

case "${1:-}" in
  --sync)
    mkdir -p "$HOME_DIR"
    for f in collect.py server.py registry.json; do
      [ -r "$REPO_DIR/$f" ] || { echo "! 源缺 $f"; exit 1; }
      [ -f "$HOME_DIR/$f" ] && cp "$HOME_DIR/$f" "$HOME_DIR/$f.bak-$(date +%Y%m%d-%H%M%S)"
      cp "$REPO_DIR/$f" "$HOME_DIR/$f"
    done
    python3 "$HOME_DIR/collect.py" >/dev/null && echo "已装好并采过一次：$HOME_DIR/status.json"
    ;;
  --check)
    rc=0
    for f in collect.py server.py registry.json; do
      if diff -q "$REPO_DIR/$f" "$HOME_DIR/$f" >/dev/null 2>&1; then echo "一致  $f"
      else echo "漂移  $f（跑 install.sh --sync）"; rc=1; fi
    done
    if launchctl list 2>/dev/null | grep -q "$LABEL"; then
      echo "launchd 已加载 $LABEL（退出码 $(launchctl list | awk -v l="$LABEL" '$3==l{print $2}')）"
    else echo "! launchd 没加载（install.sh --agent）"; rc=1; fi
    if [ -f "$HOME_DIR/status.json" ]; then
      echo "状态文件 $(stat -f '%Sm' -t '%F %T' "$HOME_DIR/status.json") 生成"
    else echo "! 还没有 status.json"; rc=1; fi
    exit $rc
    ;;
  --agent)
    [ -f "$HOME_DIR/collect.py" ] || { echo "! 先 --sync"; exit 1; }
    cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>Label</key><string>$LABEL</string>
 <key>ProgramArguments</key><array>
  <string>/usr/local/bin/python3</string><string>$HOME_DIR/collect.py</string></array>
 <key>StartInterval</key><integer>1800</integer>
 <key>RunAtLoad</key><true/>
 <key>StandardOutPath</key><string>$HOME_DIR/collect.out.log</string>
 <key>StandardErrorPath</key><string>$HOME_DIR/collect.err.log</string>
</dict></plist>
PL
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
    launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "已加载：每 30 分钟只读采集一次（撤销：install.sh --unagent）"
    ;;
  --unagent)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>&1
    rm -f "$PLIST"
    echo "已卸载定时采集（页面服务不受影响）"
    ;;
  *) echo "用法：bash install.sh --sync | --check | --agent | --unagent"; exit 2 ;;
esac
