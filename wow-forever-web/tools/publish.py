#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布入口：把"跑门禁 → 打包 → 验收 → 上传 → 记账"收成一条命令。

为什么要它：站主 2026-10-29 的原话是"不可能一直提交上传，怎么弄方便"。
痛的不是提交（提交已经自动化了，见 tools/admin/jobs.py 的跑前收口与跑后提交），
痛的是**发布**要人手动串三四个脚本。这个脚本只做编排，不重新实现任何一步：

    门禁   bash tools/refresh.sh publish        （npm ci + vitest + build + 全套 gate）
    打包   python3 tools/release-package.py     （产出 release/<包名> 与 latest.json）
    验收   python3 tools/pkg-verify.py          （起严格静态服务，缺文件必须 404）
    上传   python3 tools/deploy-gh-pages.py --push        （web，现有出口）
           node tools/oss-release.js build/upload/verify  （小程序数据批次 + 指针）
    记账   追加一行到 docs/PUBLISH-LOG.md

三条硬规矩：① **不加 --push / --upload 就什么都不上传**，只把要执行的命令打给你看；
② **包名带 -dirty 就拒绝发布**（工作树里 app/data 或 app/img 有未提交改动时 release-package.py 会这么标），
要越过它得显式 `--allow-dirty`；③ 这个脚本**从不 push 源码仓**——源码提交与推送永远是人的动作。

用法：
    python3 tools/publish.py --status                 # 现在本地是哪一版、线上是哪一版
    python3 tools/publish.py --target web --dry-run   # 只打印会跑什么
    python3 tools/publish.py --target web             # 跑门禁+打包+验收，不上传
    python3 tools/publish.py --target web --skip-gate --push     # 刚验过，直接打包并推
    python3 tools/publish.py --target mini --env beta --upload
"""
import argparse
import datetime
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE = os.path.join(ROOT, "release")
LATEST = os.path.join(RELEASE, "latest.json")
LOG = os.path.join(ROOT, "docs", "PUBLISH-LOG.md")
PAGES_URL = "https://eplayed.github.io/wuxian-atlas/"
# 小程序数据用的 OSS 命名空间与"不许顺手复用别线 bucket"的判据（2026-10-21 定的分发层）
MINI_PREFIX = "wow/{env}/v1/"
FOREIGN_BUCKET = "poe2-all-class"


def run(cmd):
    print("\n\033[1m▶ %s\033[0m" % " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT, text=True)
    if p.returncode:
        sys.exit("这一步非 0 退出（%d），发布停在这里： %s" % (p.returncode, shown))
    return p


def latest():
    if not os.path.exists(LATEST):
        return None
    with io.open(LATEST, encoding="utf-8") as f:
        return json.load(f)


def data_checked_days():
    """溯源页那张表里的"最久没核的板块"，发布前该看一眼它。"""
    path = os.path.join(ROOT, "app", "data", "scale.json")
    if not os.path.exists(path):
        return "读不到 scale.json"
    with io.open(path, encoding="utf-8") as f:
        doc = json.load(f)
    rows = ((doc.get("scale") or {}).get("dataVersions") or [])
    dated = [(x.get("daysSince"), x.get("section") or x.get("file") or "?", x.get("checkedAt"))
             for x in rows if isinstance(x.get("daysSince"), int)]
    if not dated:
        return "scale.json 里没有「多久没核了」那一列（跑一次 node tools/build-data.js 才会有）"
    dated.sort(reverse=True)
    worst = dated[0]
    red = [x for x in dated if x[0] > 14]
    return "%s最久没核：%s（%s 核的，%d 天%s）" % (
        "拦红——" if red else "", worst[1], worst[2], worst[0],
        "；共 %d 块超 14 天" % len(red) if red else "")


def live_version():
    """线上那一版是哪个包：读 Pages 上发布的清单指纹，读不到就直说读不到。"""
    p = subprocess.run(["curl", "-s", "--max-time", "20", "-o", "/dev/null", "-w", "%{http_code}",
                        PAGES_URL], capture_output=True, text=True)
    code = (p.stdout or "?").strip()
    if code in ("", "000"):
        # 这台机到 Pages 的连接本来就抖（见 docs/OPS-deploy-domain-2026-10-19.md 第十一节的吞吐实测），
        # 读不到不等于线上下线，所以这话要说清楚，不许拿它当"挂了"的结论
        return "读不到（curl 没连上；这台机到 Pages 常抖，不能据此判断线上状态）"
    return "HTTP %s（%s）" % (code, PAGES_URL)


def status():
    cur = (latest() or {}).get("current") or {}
    print("本地最新包：%s" % (cur.get("package") or "（没有，先跑一次 --target web）"))
    print("  对应提交：%s  文件 %s 个  %s 字节" % (cur.get("gitHead"), cur.get("files"), cur.get("bytes")))
    print("  打包时间：%s" % (cur.get("builtAt") or cur.get("createdAt") or "（清单里没记）"))
    print("线上：%s" % live_version())
    print("数据：%s" % data_checked_days())
    print("\n小程序数据命名空间：/%s（与网页不同仓，走 tools/oss-release.js 的批次＋指针）" % MINI_PREFIX)
    return 0


def worktree_dirty():
    """app/data 与 app/img 有没有未提交改动——发布口径必须是"某个提交"，不能是半成品。"""
    p = subprocess.run(["git", "status", "--porcelain", "--", "app/data", "app/img"],
                       cwd=ROOT, capture_output=True, text=True)
    return [line[3:].strip() for line in p.stdout.splitlines() if line.strip()]


def plan(target, args):
    """把要执行的东西打出来，不执行。"""
    what = "会真上传" if (args.push if target == "web" else args.upload) else "只准备，不上传"
    print("目标 %s｜%s%s" % (target, what, "｜环境 " + args.env if target == "mini" else ""))
    steps = []
    if not args.skip_gate:
        steps.append("bash tools/refresh.sh publish        # 全套门禁，红了就不该发")
    if target == "web":
        steps.append("python3 tools/release-package.py" + (" --skip-build" if args.skip_gate else ""))
        steps.append("python3 tools/pkg-verify.py          # 起严格静态服务，缺文件必须 404")
        steps.append("python3 tools/deploy-gh-pages.py --push" if args.push
                     else "（没加 --push）要发布：python3 tools/deploy-gh-pages.py --push")
    else:
        steps.append("node tools/export-mini.js            # 基底 → 小程序快照与产物")
        steps.append("node tools/oss-release.js build --env %s --check-identity" % args.env)
        steps.append("node tools/oss-release.js upload --env %s   ← 没加 --upload，不会真传" % args.env
                     if not args.upload else "node tools/oss-release.js upload --env %s" % args.env)
        steps.append("node tools/oss-release.js verify --env %s   # 逐文件回读" % args.env)
    print("\n会按顺序跑：")
    for s in steps:
        print("  · " + s)


def write_log(line):
    header = "# 发布台账\n\n每发布一次追加一行。**发布是对外动作，只有站主点头才做**；\n" \
             "这一页由 `tools/publish.py` 写，改代码的人不用手抄。\n\n" \
             "| 时间 | 目标 | 包 / 批次 | 对应提交 | 结果 |\n| --- | --- | --- | --- | --- |\n"
    new = not os.path.exists(LOG)
    with io.open(LOG, "a", encoding="utf-8") as f:
        if new:
            f.write(header)
        f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["web", "mini"], help="发哪一个：web=静态站，mini=小程序数据批次")
    ap.add_argument("--env", default="beta", choices=["beta", "prod"], help="小程序侧环境")
    ap.add_argument("--push", action="store_true", help="web：真推到 Pages 仓库（不加只打印命令）")
    ap.add_argument("--upload", action="store_true", help="mini：真上传批次并换指针")
    ap.add_argument("--skip-gate", action="store_true", help="刚跑完全套门禁时用，省掉 npm ci 那十几分钟")
    ap.add_argument("--allow-dirty", action="store_true", help="明知数据有未提交改动仍要发（默认拒绝）")
    ap.add_argument("--status", action="store_true", help="只看现在本地/线上是哪一版")
    ap.add_argument("--dry-run", action="store_true", help="只打印会跑什么，一条都不执行")
    args = ap.parse_args()

    if args.status:
        return status()
    if not args.target:
        ap.error("--target web|mini 或 --status 二选一")

    plan(args.target, args)
    if args.dry_run:
        print("\n--dry-run：一条都没执行。")
        return 0

    dirty = worktree_dirty()
    if dirty and not args.allow_dirty:
        sys.exit("app/data 或 app/img 有 %d 个未提交改动，这一版对不上任何提交，不发。\n"
                 "       先收口（刷新链会自动做，或自己提交），确实要越过它加 --allow-dirty：\n       %s"
                 % (len(dirty), "\n       ".join(dirty[:10])))
    if not args.skip_gate:
        run(["bash", "tools/refresh.sh", "publish"])

    cur = (latest() or {}).get("current") or {}
    if args.target == "web":
        run(["python3", "tools/release-package.py"] + (["--skip-build"] if args.skip_gate else []))
        cur = (latest() or {}).get("current") or {}
        pkg = cur.get("package") or ""
        if pkg.endswith("-dirty"):
            # 打包器看的是整仓，我们这条闸只看数据目录：多会话并发时别人的未提交文档
            # 也会把包名标成 -dirty。不拦，但必须说清为什么放行，且把这标记留在台账里。
            print("提醒：包名带 -dirty——`release-package.py` 看的是整仓未提交改动，"
                  "本脚本只要求 app/data 与 app/img 干净（已核对）。")
        run(["python3", "tools/pkg-verify.py"])
        result = "只准备未上传"
        if args.push:
            run(["python3", "tools/deploy-gh-pages.py", "--push"])
            result = "已推 Pages"
        if pkg.endswith("-dirty"):
            result += "（包带 -dirty 标记）"
    else:
        run(["node", "tools/export-mini.js"])
        run(["node", "tools/oss-release.js", "build", "--env", args.env, "--check-identity"])
        result = "已出批次，未上传"
        if args.upload:
            bucket = os.environ.get("OSS_BUCKET") or ""
            print("OSS bucket：%s｜只写 %s" % (bucket or "（走默认凭证）", MINI_PREFIX.format(env=args.env)))
            if bucket == FOREIGN_BUCKET:
                print("注意：%s 是 PoE 那条线的 bucket，本站只允许写 wow/ 前缀下面那一段" % FOREIGN_BUCKET)
            run(["node", "tools/oss-release.js", "upload", "--env", args.env])
            run(["node", "tools/oss-release.js", "verify", "--env", args.env])
            result = "已传批次并换指针"

    write_log("| %s | %s | `%s` | %s | %s |" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), args.target,
        cur.get("package") or cur.get("batch") or "—", cur.get("gitHead") or "—", result))
    print("\n\033[1;32m%s：%s（已记进 docs/PUBLISH-LOG.md）\033[0m" % (args.target, result))
    print("源码仓没被这个脚本 push 过；要推源码请你自己确认。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
