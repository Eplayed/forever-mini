#!/usr/bin/env bash
# 每天开机跑这一次：探源 → 抓 → 并 → 统一门禁 → 出报告。
#
# 为什么要有它（2026-11-02 站主定：Mac 不再做，全部在这台 Windows，每天开机手动跑一次更新）：
#   以前没有总入口，插件层根本不在 refresh.sh 的场景里，所以那批快照一路发到过期。
#   这条链把顺序写死，任何一步失败都留下记录，不靠人脑记顺序。
#
# 用法：  bash tools/daily.sh            # 完整跑（约 25~40 分钟，site-check 单跑就要 13 分钟）
#         bash tools/daily.sh --quick    # 只跑探源 + 插件层 + 门禁，不重抓网页那几块
#         bash tools/daily.sh --no-gate  # 只抓到并完，界面回归留到之后（调试用）
#
# 故意不加 set -e：一处红要**继续把后面跑完再汇总**。用 -e 的话第一个失败就把剩下
# 六个板块全跳过，报告上会出现一堆"没跑"，那比真实的"哪块坏了"更难判断。
set -uo pipefail
cd "$(dirname "$0")/.."

QUICK=0
NOGATE=0
for a in "$@"; do
  case "$a" in
    --quick) QUICK=1 ;;
    --no-gate) NOGATE=1 ;;
    *) echo "未知参数：$a（可用 --quick / --no-gate）"; exit 2 ;;
  esac
done

DAY="$(date +%F)"
RUNDIR="$(mktemp -d)"
STEPS="$RUNDIR/steps.tsv"
PROBE="$RUNDIR/probe.json"
: >"$STEPS"

# 记一步：名字、退出码、秒、末两行输出。报告与终端摘要都读这张表。
step() {
  local name="$1"; shift
  local t0=$(date +%s) out rc
  out="$("$@" 2>&1)"; rc=$?
  local tail_lines
  tail_lines="$(printf '%s\n' "$out" | grep -v '^[[:space:]]*$' | tail -2 | tr '\n' ' ' | cut -c1-220)"
  printf '%s\t%d\t%d\t%s\n' "$name" "$rc" "$(( $(date +%s) - t0 ))" "$tail_lines" >>"$STEPS"
  if [ $rc -eq 0 ]; then
    printf '\033[32m✓\033[0m %-26s %ss\n' "$name" "$(( $(date +%s) - t0 ))"
  else
    printf '\033[31m✗\033[0m %-26s rc=%d  %s\n' "$name" "$rc" "$tail_lines"
  fi
  return 0
}

echo "每日数据更新 · $DAY"
echo "----------------------------------------------------------------"

# ① 探源：必需来源不通就别往下跑。抓取脚本碰上不通的源，有的会拿旧快照继续、
#    还把日期写成今天——那种"看起来更新了"比直接失败更坏。
step "① 探源" python3 tools/daily-probe.py --json "$PROBE"
PROBE_OK=$(awk -F'\t' -v n="① 探源" '$1==n && $2==0{c++} END{print c+0}' "$STEPS")
if [ "$PROBE_OK" = "0" ]; then
  echo "----------------------------------------------------------------"
  echo "✗ 必需来源不通，停在这里。旧快照还在库里，日期没被改写，可以直接接着看上次结果。"
  python3 tools/daily-report.py --day "$DAY" --steps "$STEPS" --probe "$PROBE" --stopped probe || true
  exit 1
fi

# ② 插件层抽取：原件在这台机器的 AddOns 里，位置由 addons_root 现读
step "② 插件层抽取" bash tools/refresh.sh addons

if [ "$QUICK" = "0" ]; then
  # ③ 各板块重抓。每个场景都带 WOW_SKIP_GATE=1：门禁留到 ⑤ 统一跑一次，
  #    否则 site-check 要跑八遍（单跑约 13 分钟）
  for s in world changes dungeons prof legacy talents official icons; do
    step "③ 重抓 $s" env WOW_SKIP_GATE=1 bash tools/refresh.sh "$s"
  done
fi

# ④ 插件快照并成品。必须排在 ③ 之后：merge-dungeons / merge-professions 会整表重写，
#    并在前面的话插件并进去的字段会被冲掉（专业线栽过一次，见 refresh.sh prof 那段注释）
step "④ 插件并成品" env WOW_SKIP_GATE=1 bash tools/refresh.sh addons-merge

# ⑤ 统一门禁一次
if [ "$NOGATE" = "0" ]; then
  step "⑤ 门禁" bash tools/refresh.sh check
else
  echo "! ⑤ 门禁按要求跳过（--no-gate）；发版前必须补跑 bash tools/refresh.sh check"
fi

# ⑥ 报告
step "⑥ 出报告" python3 tools/daily-report.py --day "$DAY" --steps "$STEPS" --probe "$PROBE"

echo "----------------------------------------------------------------"
FAILED=$(awk -F'\t' '$2!=0{print $1}' "$STEPS" | tr '\n' ' ')
if [ -z "$FAILED" ]; then
  echo "✓ 全链完成。报告：wow-forever-web/docs/DATA-每日体检-$DAY.md"
else
  echo "✗ 有步骤失败：$FAILED"
  echo "  报告里逐条写了哪步红、输出了什么。红着的步骤对应的数据不要当已更新。"
fi
rm -rf "$RUNDIR"
[ -z "$FAILED" ] || exit 1
