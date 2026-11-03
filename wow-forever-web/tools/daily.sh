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
# 整条链的子进程统一按 UTF-8 输出：这台机器的控制台默认 GBK，任何一步打 ✓ ✗ ⚠ 都会先崩在打印上，
# 而 daily 只看退出码——于是"我们的编码"会被记成"那一步失败"。第一步就这么被骗过一次。
export PYTHONIOENCODING=utf-8
# 链跑在 WSL 里时（本机 `bash` = System32\bash.exe），node 只有 Windows 侧装了——
# 把它的安装位补进 PATH，2026-11-03 那轮 world/changes/prof/legacy/门禁五步全因
# "node: command not found" 一起红就是缺这条。Git Bash / Linux 原生 node 不受影响。
command -v node >/dev/null 2>&1 || export PATH="$PATH:/mnt/c/Program Files/nodejs"

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
# steps/probe 落到工作台的固定位置（不是 $RUNDIR）：8830 面板的 00 水源台要在链跑着的
# 时候就能逐格点亮（每次 step 追加一行，面板轮询读它）——放 mktemp 里成功后就被删了，
# 面板永远只能看到"昨天"。红的时候留在原地，也正是要人看的东西。
ADMINRUN="tools/admin/daily"
mkdir -p "$ADMINRUN"
STEPS="$ADMINRUN/steps.tsv"
PROBE="$ADMINRUN/probe.json"
LOGDIR="$RUNDIR/logs"
mkdir -p "$LOGDIR"
: >"$STEPS"

# 记一步：名字、退出码、秒、一条能读懂的输出。报告与终端摘要都读这张表。
# 失败时不再取"末两行"：门禁的末两行往往是收尾汇总（今天就是"这几页没有脚本报错"这种），
# 拿它当证据等于没证据。改成先把输出里真正写着 ✗/失败/ERROR 的那几行捞出来。
step() {
  local name="$1"; shift
  local t0=$(date +%s) out rc
  out="$("$@" 2>&1)"; rc=$?
  # 全程输出留档：只靠 400 字的摘要行没法判断红的是哪条断言（今天就是靠单跑才看清的）
  printf '%s\n' "$out" >"$LOGDIR/$(printf '%s' "$name" | tr -d '①②③④⑤⑥⑦⑧⑨⑩ /｜|' ).txt"
  local tail_lines=""
  if [ $rc -ne 0 ]; then
    # 只认"这行自己在说失败"的：行首的 ✗/FAIL、Traceback、以及 build-data 的"校验失败 N 项"。
    # 不能宽到含 "失败" 就行——site-check 的 PASS 行写着「无脚本报错与失败请求」，捞它会盖住真红的那几条。
    tail_lines="$(printf '%s\n' "$out" | grep -avE 'PASS' | grep -aE '^ *(✗|FAIL)|^Traceback|校验失败|不可通过' | head -6 | tr '\n' ' ' | cut -c1-400)"
  fi
  [ -n "$tail_lines" ] || tail_lines="$(printf '%s\n' "$out" | grep -v '^[[:space:]]*$' | tail -2 | tr '\n' ' ' | cut -c1-220)"
  printf '%s\t%d\t%d\t%s\n' "$name" "$rc" "$(( $(date +%s) - t0 ))" "$tail_lines" >>"$STEPS"
  if [ $rc -eq 0 ]; then
    printf '\033[32m✓\033[0m %-26s %ss\n' "$name" "$(( $(date +%s) - t0 ))"
  else
    printf '\033[31m✗\033[0m %-26s rc=%d  %s\n' "$name" "$rc" "$tail_lines"
  fi
  return 0
}

echo "每日数据更新 · $DAY"
# 界面回归与几个抓取器要真浏览器。默认 Chrome；Chrome 坏了可以用
#   WOW_BROWSER_CHANNEL=msedge bash tools/daily.sh
# 临时换 Edge 跑完这一轮——但那份"通过"只代表 Edge，报告里会跟着写清楚，别当 Chrome 的数。
echo "浏览器：${WOW_BROWSER_CHANNEL:-chrome}（默认 chrome；换的要写进报告）"
echo "----------------------------------------------------------------"

# ① 探源：必需来源不通就别往下跑。抓取脚本碰上不通的源，有的会拿旧快照继续、
#    还把日期写成今天——那种"看起来更新了"比直接失败更坏。
step "① 探源" python3 tools/daily-probe.py --json "$PROBE"
PROBE_OK=$(awk -F'\t' -v n="① 探源" '$1==n && $2==0{c++} END{print c+0}' "$STEPS")
if [ "$PROBE_OK" = "0" ]; then
  echo "----------------------------------------------------------------"
  # rc=1 有两种：源真不通（探针写出了 JSON 并标了哪一条不通），和探针自己崩了（没有 JSON）。
  # 把后者说成"必需来源不通"是假结论——2026-11-02 就是编码崩了却报源不通，白查一轮。
  if [ -s "$PROBE" ]; then
    echo "✗ 必需来源不通，停在这里。旧快照还在库里，日期没被改写，可以直接接着看上次结果。"
  else
    echo "✗ 探源脚本自己没跑完（没写出 $PROBE），下面这条是它的原话，不要当成源的状态。"
    awk -F'\t' -v n="① 探源" '$1==n{print "  " $4}' "$STEPS"
  fi
  python3 tools/daily-report.py --day "$DAY" --steps "$STEPS" --probe "$PROBE" --stopped probe || true
  exit 1
fi

# ② 插件层抽取：原件在这台机器的 AddOns 里，位置由 addons_root 现读
step "② 插件层抽取" bash tools/refresh.sh addons

if [ "$QUICK" = "0" ]; then
  # ③ 各板块重抓。每个场景都带 WOW_SKIP_GATE=1：门禁留到 ⑤ 统一跑一次，
  #    否则 site-check 要跑十二遍（单跑约 12 分钟）
  #    顺序不是随便排的：quests / items / spells / achievements 都要排在 ② 之后
  #    （merge-dungeon-quests 吃 GI 的任务快照、merge-items 吃 GI 的存在性探针、
  #     merge-spells 吃 GI+XR 的每级学习等级、merge-achievements 吃 GI 的成就目录）；
  #    icons 放最后，让前面新写进去的 iconKey 先进登记表再补图。
  for s in world changes dungeons prof legacy talents official quests items spells achievements icons; do
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

# ⑥ 本地 vs 线上对账（只读：HEAD 比尺寸、匿名读 OSS 指针，不构建不上传不发布）
#    放门禁之后、报告之前：报告只读它写出的 JSON，自己不再碰网络（这台机到 Pages 一次要两分钟）。
#    同一份结果再存一份到工作台读的位置（那个目录 .gitignore 掉了，不进仓库）——
#    页面打开就该看见今天这一次的答案，而不是等有人去点按钮。
RECON="$RUNDIR/reconcile.json"
step "⑥ 对账" python3 tools/reconcile.py --env beta --json "$RECON" --quiet
[ -s "$RECON" ] && cp -f "$RECON" tools/admin/reconcile/latest.json

# ⑦ 报告
step "⑦ 出报告" python3 tools/daily-report.py --day "$DAY" --steps "$STEPS" --probe "$PROBE" --reconcile "$RECON"

echo "----------------------------------------------------------------"
FAILED=$(awk -F'\t' '$2!=0{print $1}' "$STEPS" | tr '\n' ' ')
if [ -z "$FAILED" ]; then
  echo "✓ 全链完成。报告：wow-forever-web/docs/DATA-每日体检-$DAY.md"
  rm -rf "$RUNDIR"
else
  echo "✗ 有步骤失败：$FAILED"
  echo "  报告里逐条写了哪步红、输出了什么。红着的步骤对应的数据不要当已更新。"
  # 红的时候不删临时目录：摘要行只有 400 字，真正要看的（哪条断言、哪个 Traceback）在全程输出里。
  echo "  每一步的完整输出留在这里，红的那步直接读："
  awk -F'\t' '$2!=0{print "    " $1 " → '"$LOGDIR"'/"}' "$STEPS"
  echo "    $LOGDIR"
fi
[ -z "$FAILED" ] || exit 1
