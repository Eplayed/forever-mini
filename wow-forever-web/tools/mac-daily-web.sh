#!/usr/bin/env bash
# MacBook 侧每日定时数据检查与自动更新链（配合 launchd com.wowforever.data-daily.plist）
# 兼容 macOS Bash 3.2 + Python 3.9 + nvm Node v22
set -uo pipefail

export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
export PYTHONIOENCODING=utf-8
export WOW_EXPORT="$HOME/Documents/project/wow-forever/wow-forever-web/ziliao-export"

cd "$(dirname "$0")/.."
WEB_DIR="$(pwd)"
STATE_DIR="$WEB_DIR/tools/admin/daily"
mkdir -p "$STATE_DIR"
V2T_DIR="$HOME/Documents/project/video2text"

MODE="auto"
for a in "$@"; do
  case "$a" in
    --check-only) MODE="check" ;;
    --merge-only) MODE="merge" ;;
    --force) MODE="force" ;;
    *) echo "未知参数: $a"; exit 2 ;;
  esac
done

echo "[mac-daily-web] $(date '+%Y-%m-%d %H:%M:%S') mode=$MODE node=$(node -v 2>/dev/null || echo missing) py=$(python3 --version 2>/dev/null || echo missing)"

PROBE_OUT="$(python3 tools/mac-daily-probe.py)"
echo "[mac-daily-web] 探针结果: $PROBE_OUT"

if [ "$MODE" = "check" ]; then
  exit 0
fi

NEED_WEB="$(printf '%s' "$PROBE_OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(1 if d["needWeb"] else 0)')"
NEED_MERGE="$(printf '%s' "$PROBE_OUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(1 if d["needMerge"] else 0)')"

if [ "$MODE" = "force" ]; then
  NEED_WEB="1"
  NEED_MERGE="1"
elif [ "$MODE" = "merge" ]; then
  NEED_WEB="0"
  NEED_MERGE="1"
fi

if [ "$NEED_WEB" = "0" ] && [ "$NEED_MERGE" = "0" ]; then
  echo "[mac-daily-web] 公网构建与插件快照均无变化，今日跳过更新 ✓"
  exit 0
fi

ERRORS=()
run_step() {
  local label="$1"; shift
  echo "[mac-daily-web] ▶ $label"
  if "$@"; then
    echo "[mac-daily-web]   ✓ $label"
  else
    echo "[mac-daily-web]   ✗ $label (rc=$?)"
    ERRORS+=("$label")
  fi
}

if [ "$NEED_WEB" = "1" ]; then
  echo "[mac-daily-web] 检测到公网新版本或超过 6 天，开始重抓公网板块..."
  for s in world changes dungeons prof legacy talents official quests items spells achievements icons; do
    run_step "公网重抓 $s" env WOW_SKIP_GATE=1 bash tools/refresh.sh "$s"
  done
  [ -f tools/scrape-cwf-bis60.py ] && run_step "公网重抓 60级团前BiS" python3 tools/scrape-cwf-bis60.py
  [ -f tools/merge-bis60.py ] && run_step "合并 60级团前BiS" python3 tools/merge-bis60.py
  [ -f tools/refresh-census.py ] && run_step "更新 Everloot 人口" python3 tools/refresh-census.py
fi

if [ "$NEED_MERGE" = "1" ]; then
  echo "[mac-daily-web] 合并插件快照 + 图标映射 + 全站数据卡口..."
  run_step "插件快照并成品" env WOW_SKIP_GATE=1 bash tools/refresh.sh addons-merge
  run_step "刷新图标映射" python3 tools/build-icon-map.py
  run_step "全站数据卡口 build-data.js" node tools/build-data.js
  run_step "译名严格核查" python3 tools/audit-translations.py --strict
fi

if [ -f "$V2T_DIR/tools/sync_wow_icons.py" ]; then
  run_step "刷新 video2text 图标与数据索引" python3 "$V2T_DIR/tools/sync_wow_icons.py"
fi

python3 tools/mac-daily-probe.py --write-status "$PROBE_OUT" "${#ERRORS[@]}"

if [ "${#ERRORS[@]}" -gt 0 ]; then
  echo "[mac-daily-web] ✗ 存在 ${#ERRORS[@]} 步失败: ${ERRORS[*]}"
  exit 1
fi
echo "[mac-daily-web] 全部完成 ✓"
