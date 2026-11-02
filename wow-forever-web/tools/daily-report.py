#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 daily 这次跑的结果落成一份能第二天接着看的报告。

为什么要落成文件：只在终端里说过"跑完了"不算更新——第二天没人记得哪步红过。
这份报告里每个数字都是从文件现读的（steps.tsv / probe.json / scale.json / git），
不是我照印象写的。跑不了的步骤照实写"这台跑不了"，不写成通过。

用法：python3 tools/daily-report.py --day 2026-11-02 --steps <tsv> --probe <json> [--stopped 原因]
产物：docs/DATA-每日体检-<day>.md
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(WEB, "docs")

# 这台机器上"跑不了的东西"不该由我抄一份固定清单——2026-11-02 就抄错了一次：
# 报告里还挂着"缺 Pillow / 缺 miniprogram-automator"，实际那天两个都装上了、site-check 也到了 707/706→707/707。
# 所以每一项都现探：探到能用就不列，列出来的一定是当场真的不行。
def blockers():
    out = []
    try:
        import PIL                                    # noqa: F401
        pil_ok, pil_note = True, getattr(PIL, "__version__", "?")
    except Exception:
        pil_ok, pil_note = False, "装不上就 pip install -i https://mirrors.aliyun.com/pypi/simple/ pillow"
    if not pil_ok:
        out.append(("两帧像素对比 / visual-check", "缺 Pillow（%s）" % pil_note))

    # miniprogram-automator：脚本靠 NODE_PATH 注入，所以三处都看一眼
    cand = []
    for p in (os.environ.get("NODE_PATH"), os.path.expanduser("~/mp-deps/node_modules"),
              os.path.join(WEB, "node_modules"), os.path.join(os.path.dirname(WEB), "node_modules")):
        if p:
            cand.append(p)
    am = next((p for p in cand if os.path.isdir(os.path.join(p, "miniprogram-automator"))), None)
    if not am:
        out.append(("小程序回归 mini-m01 / mini-m02",
                    "缺 miniprogram-automator：npm i --prefix ~/mp-deps miniprogram-automator，"
                    "再 NODE_PATH=~/mp-deps/node_modules node tools/mini-m01-check.js"))

    # 开发者工具的自动化端口：装了包但 IDE 没开/没开服务端口照样跑不了
    import socket
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect(("127.0.0.1", 9421))
        live = True
    except Exception:
        live = False
    finally:
        s.close()
    if not live and am:
        out.append(("小程序回归 mini-m01 / mini-m02",
                    "包已装（%s），但开发者工具的 9421 端口没在听——要在 IDE 的安全设置里开服务端口" % am))

    # GitHub HTTPS：这台一直不通，推送走 SSH；这条每天都探，别让它变成信仰
    try:
        p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-m", "8", "-w", "%{http_code}",
                            "https://github.com/Eplayed/forever-mini"], capture_output=True, timeout=20)
        code = p.stdout.decode(errors="replace").strip()
    except Exception:
        code = "000"
    if not code.startswith("2"):
        out.append(("git push 走 HTTPS", "github.com 返回 %s；推送请用 SSH（remote 换成 git@github.com:Eplayed/forever-mini.git）" % (code or "无响应")))
    return out



def read_steps(path):
    rows = []
    if not os.path.exists(path):
        return rows
    for line in io.open(path, encoding="utf-8", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3:
            rows.append({"name": p[0], "rc": int(p[1] or 1), "secs": p[2],
                         "tail": (p[3] if len(p) > 3 else "")[:300]})
    return rows


def read_probe(path):
    try:
        d = json.loads(io.open(path, encoding="utf-8").read())
        return d.get("sources", []), d.get("degraded", []), d.get("blocked", [])
    except Exception:
        return [], [], []


def scale_view():
    p = os.path.join(WEB, "app", "data", "scale.json")
    try:
        s = json.loads(io.open(p, encoding="utf-8").read())
        return s.get("scale", {})
    except Exception:
        return {}


def upstream_ages(day):
    """原始快照多久没重抓了——只看**我们自己动手的日期**（fetchedAt / extractedAt / checkedAt / scrapedAt）。
       作者自述的 fetched（如 xr-items-detail 的 2026-09-20）不能算：那是他那份数据的年份，
       不是我们多久没刷新；拿它判会把今天刚重抽的算成"43 天没动"。
       另外别用 read(N) 截断再 json.loads——截断的 JSON 必然解析失败，
       那份清单会静默变成"没有超期"，看着绿其实一条都没读（2026-11-02 自查抓到）。
       meta 永远在文件开头，所以取头部用正则把日期全抓出来再按优先序挑。"""
    up = os.path.join(WEB, "app", "data", "upstream")
    today = datetime.date.fromisoformat(day)
    ours = ("fetchedAt", "extractedAt", "checkedAt", "scrapedAt")
    pat = re.compile(r'"(fetchedAt|extractedAt|checkedAt|scrapedAt|fetched)"\s*:\s*"(\d{4}-\d{2}-\d{2})"')
    out = []
    for f in sorted(os.listdir(up)) if os.path.isdir(up) else []:
        if not f.endswith(".json"):
            continue
        try:
            head = io.open(os.path.join(up, f), encoding="utf-8", errors="replace").read(6000)
        except OSError:
            continue
        found = dict(pat.findall(head))
        d = next((found[k] for k in ours if k in found), None)
        if not d:
            continue                      # 只有作者自述日期的，不参与"我们多久没刷"的判断
        try:
            age = (today - datetime.date.fromisoformat(d)).days
        except ValueError:
            continue
        if age > 14:
            out.append((f, d, age))
    return sorted(out, key=lambda x: -x[2])


def git_changed():
    """这次动了哪些数据文件。用 git 现读，不靠我记。"""
    try:
        p = subprocess.run(["git", "status", "--porcelain", "--", "wow-forever-web/app/data",
                            "for-mini/data"], cwd=os.path.dirname(WEB),
                           capture_output=True, timeout=60)
        lines = [l[3:] for l in p.stdout.decode("utf-8", "replace").splitlines() if l.strip()]
        return len(lines), lines[:14]
    except Exception:
        return 0, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=datetime.date.today().isoformat())
    ap.add_argument("--steps", required=True)
    ap.add_argument("--probe", required=True)
    ap.add_argument("--stopped", help="链条提前停在这一步，后面根本没跑")
    a = ap.parse_args()

    steps = read_steps(a.steps)
    srcs, degraded, blocked = read_probe(a.probe)
    sc = scale_view()
    stale = upstream_ages(a.day)
    n_changed, changed = git_changed()
    fails = [s for s in steps if s["rc"] != 0]

    L = []
    L.append("# 每日数据体检 · %s" % a.day)
    L.append("")
    L.append("由 `tools/daily.sh` 生成。数字全部从 `scale.json`、各数据文件 meta 与 git 现读；"
             "跑不了的步骤照实写跑不了，不记成通过。")
    L.append("")
    verdict = "✅ 全链通过" if not fails and not a.stopped else "⚠️ 有步骤没通过"
    L.append("**结论：%s**（%d 步，失败 %d 步%s）" % (
        verdict, len(steps), len(fails),
        "；链条停在「%s」，之后的步骤根本没跑" % a.stopped if a.stopped else ""))
    L.append("")

    L.append("## 一、这次跑了什么")
    L.append("")
    L.append("| 步骤 | 结果 | 秒 | 末尾输出 |")
    L.append("| --- | --- | --- | --- |")
    for s in steps:
        L.append("| %s | %s | %s | %s |" % (s["name"], "✓" if s["rc"] == 0 else "✗ rc=%d" % s["rc"],
                                            s["secs"], (s["tail"] or "").replace("|", "｜")[:110]))
    L.append("")

    L.append("## 二、来源今天在这台机器上通不通")
    L.append("")
    L.append("| 来源 / 通道 | 状态 | 耗时或码 | 谁在用 |")
    L.append("| --- | --- | --- | --- |")
    for r in srcs:
        mark = "✓" if r.get("ok") else ("!" if (r.get("state") in ("可达但拒绝", "没开") and not r.get("required")) else "✗")
        timing = ("%ss" % r["seconds"]) if r.get("kind") == "source" else r.get("code", "")
        L.append("| %s | %s %s | %s | %s |" % (
            r["name"], mark, r["state"], timing, (r.get("used_by") or "").replace("|", "｜")))
    L.append("")
    if degraded:
        L.append("推送/分发通道不可用（不影响抓取，影响发布）：%s" % "、".join(degraded))
        L.append("")

    L.append("## 三、站内数据现状")
    L.append("")
    cov = sc.get("coverage", {})
    L.append("- 分级：%s（共 %s 条，L0 占 %.1f%%）" % (
        " / ".join("%s %s" % (k, cov.get(k)) for k in ("L0", "L1", "L2", "L3")),
        sc.get("coverageTotal", "?"),
        (100.0 * (cov.get("L0") or 0) / (sc.get("coverageTotal") or 1))))
    L.append("- 规模：物品名录 %s（无限新增 %s）· 副本 %s（新增本 %s）· 首领 %s · 掉落 %s · 配方 %s · 区域 %s · 稀有 %s" % (
        sc.get("items"), sc.get("itemsNew"), sc.get("dungeons"), sc.get("dungeonsNew"),
        sc.get("bosses"), sc.get("drops"), sc.get("recipes"), sc.get("zones"), sc.get("rares")))
    L.append("- 宏 %s 条 · 配装 %s 套 · 成就 %s · 宠物家族 %s/技能 %s · 天赋节点 %s · 搜索索引 %s" % (
        sc.get("macros"), sc.get("bisSets"), sc.get("achievements"), sc.get("pets"),
        sc.get("petSkills"), sc.get("talentNodes"), sc.get("search")))
    L.append("- 客户端最高构建（站内现读）：**%s**，代表板块：%s" % (
        sc.get("newestBuild"), sc.get("newestSection")))
    L.append("")

    L.append("## 四、各板块核对日（7 天提示 / 14 天拦红）")
    L.append("")
    L.append("| 板块 | 构建 | 核对日 | 多久没核 |")
    L.append("| --- | --- | --- | --- |")
    for r in sc.get("dataVersions", []):
        st = {"warn": "⚠️ %s 天" % r.get("daysSince"), None: "%s 天" % r.get("daysSince")}.get(
            r.get("stale"), "%s 天" % r.get("daysSince"))
        L.append("| %s | %s | %s | %s |" % (r.get("section"), r.get("build") or "—",
                                            r.get("checkedAt"), st))
    L.append("")
    if stale:
        L.append("超 14 天没重抓的原始快照（%d 份）：%s" % (
            len(stale), "、".join("%s（%s，%d 天前）" % (f, d, age) for f, d, age in stale[:8])
            + ("…" if len(stale) > 8 else "")))
    else:
        L.append("原始快照没有超过 14 天没重抓的。")
    L.append("")

    L.append("## 五、这次动了多少数据文件")
    L.append("")
    L.append("工作树里 `app/data` 与 `for-mini/data` 共 **%d** 个文件与 HEAD 不同"
             "（含别的线留下的改动，不是只有本次）：" % n_changed)
    for c in changed:
        L.append("- `%s`" % c.replace("\\", "/").split("wow-forever-web/")[-1])
    L.append("")

    L.append("## 六、这台机器跑不了的（现探，别当成已通过）")
    L.append("")
    block = blockers()
    if block:
        for name, why in block:
            L.append("- **%s** —— %s" % (name, why))
    else:
        L.append("本轮没探到跑不了的项：Pillow、miniprogram-automator、开发者工具端口、SSH 都在。")
    L.append("")
    L.append("> 报告由 `tools/daily-report.py` 生成；未发布，线上包号要另看 `NOW.md`。")

    os.makedirs(DOCS, exist_ok=True)
    out = os.path.join(DOCS, "DATA-每日体检-%s.md" % a.day)
    io.open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")

    # 终端只打五行，剩下的看文件
    print("报告 → %s" % os.path.relpath(out, WEB))
    print("结论：%s｜步骤 %d，失败 %d%s" % (verdict, len(steps), len(fails),
          "（停在 %s）" % a.stopped if a.stopped else ""))
    if fails:
        for f in fails[:4]:
            print("  ✗ %s：%s" % (f["name"], (f["tail"] or "")[:90]))
    print("客户端构建 %s｜首领 %s｜配方 %s｜分级 L0 %s/L1 %s/L2 %s" % (
        sc.get("newestBuild"), sc.get("bosses"), sc.get("recipes"),
        cov.get("L0"), cov.get("L1"), cov.get("L2")))
    print("动了 %d 个数据文件；超期原始快照 %d 份；本轮现探跑不了的 %d 项" % (n_changed, len(stale), len(block)))
    sys.exit(0)


if __name__ == "__main__":
    main()
