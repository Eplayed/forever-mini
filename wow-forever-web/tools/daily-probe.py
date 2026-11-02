#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日开工前先问一句：这些来源今天在这台机器上连不连得通。

为什么要它：2026-11-02 定「Mac 不再做，全部在这台 Windows」。这台机器的外网是半残的——
GitHub HTTPS 连不上、PyPI 官方源读超时、NGA 直接拒。抓取脚本碰上不通的源，
有的会退出（好），有的会**拿旧快照继续跑**并把日期写成今天（坏）。所以先把"通不通"摊开，
再决定往下跑不跑。

口径：
  - URL 一律抄工具代码里真在用的那个，别自己拼。自己拼错过一次：
    拿一个不存在的图标名去测官方 CDN 得到 403，差点判成"CDN 挂了"。
  - required 里任一项不通 → 退出码 1，daily 会停下，不会带着瞎掉的源往下跑。
  - 这一脚本不写任何数据文件，只说话。

用法：python3 tools/daily-probe.py [--json 路径]
"""
import argparse
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.parse

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (名字, URL, 谁在用, 是否必需)
def sample_icon_url():
    """从本机已入库的图标里现取一个名字去测 CDN。
       别硬编码文件名——2026-11-02 就是硬编了一个不存在的图标名，拿到 403 差点判成"CDN 挂了"。"""
    d = os.path.join(WEB, "app", "img", "icons")
    try:
        for f in sorted(os.listdir(d)):
            if f.endswith(".jpg"):
                return "https://render.worldofwarcraft.com/us/icons/56/" + f
    except OSError:
        pass
    return "https://render.worldofwarcraft.com/us/icons/56/"


def nga_hot_url():
    """NGA 的地址与 fid 从抓取脚本自己那里读，不在这里抄第二份。
       抄错过一次：我手写的 fid 得到一个 404，报告里就成了"NGA 异常 404"。"""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrape-nga-forever.py")
    base, fid = "https://bbs.nga.cn", ""
    try:
        t = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r'^BASE\s*=\s*"([^"]+)"', t, re.M)
        f = re.search(r"^FID\s*=\s*'?(\d+)'?", t, re.M)
        if m:
            base = m.group(1)
        if f:
            fid = f.group(1)
    except OSError:
        pass
    if not fid:
        return base
    return "%s/app_api.php?__lib=subject&__act=hot&fid=%s" % (base, fid)


SOURCES_STATIC = [
    ("解包资料站 wclbox", "https://wowforever.wclbox.com/", "scrape-wclbox-*.py｜世界/改动/专业/配装/传承的首席来源", True),
    ("wago.tools 客户端表", "https://wago.tools/api/builds", "fetch-db2-groupfinder.py｜排队表与 DB2 对账", True),
    ("官方图标 CDN", sample_icon_url(),
     "fetch-icons.py｜素材唯一允许的来源；拿本机已有图标名去回读，403 才算真有问题", True),
    ("官方中文站", "https://wow.blizzard.cn/", "extract-abilities.py / extract-races.py｜L0 定名的出处", True),
    ("封神盒子", "https://www.fengshen.cn/", "译名与资讯转述（datamine_cn 那一类）", False),
    ("社区资料站 A", "https://wowclassicforever.info/", "宏与经典库对照的自述来源", False),
    ("社区资料站 B", "https://jjwow.cn/", "社区资料补充", False),
    ("XR 名单自述的上游", "https://foreverchanges.pro/zh-cn/bis", "只做对照参考，不直接抓", False),
    ("Wowhead", "https://www.wowhead.com/forever/", "audit-wowhead.py｜英文对账（访客态会 403，已知）", False),
    ("NGA 热帖接口", nga_hot_url(), "scrape-nga-forever.py｜只当选题雷达，不上页面（正文需登录）", False),
]
SOURCES = SOURCES_STATIC

# 不是"数据源"但每天会用到的通道。
# 第三条字段是"判定成功的关键字"：ssh -T 到 GitHub **成功也返回 255**（它不给 shell 就断开），
# 只信退出码会把通的判成不通——2026-11-02 实测错过一次。
CHANNELS = [
    ("GitHub SSH（推送与拉取）",
     ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
      "-T", "git@github.com"], "git push / pull；这台 HTTPS 不通，只能走 SSH", "successfully authenticated"),
    ("OSS 只读列表（小程序分发）",
     ["node", "tools/oss-release.js", "list", "--env", "beta"], "oss-release.js list/verify", None),
]


def hit(url, timeout=20):
    """返回 (状态码, 秒, 字节)。用 curl 而不是 urllib：抓取脚本本来就走 curl，
       证书与代理行为要和它们一致，否则我测通了脚本照样挂。"""
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-m", str(timeout), "-L",
                        "-w", "%{http_code} %{time_total} %{size_download}", url],
                       capture_output=True, timeout=timeout + 10)
    parts = (p.stdout.decode("utf-8", "replace").split() + ["000", "0", "0"])[:3]
    return parts


def run(cmd, timeout=90):
    try:
        p = subprocess.run(cmd, cwd=WEB, capture_output=True, timeout=timeout,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        full = (p.stdout + b"\n" + p.stderr).decode("utf-8", "replace").strip()
        return p.returncode, full
    except Exception as e:
        return 2, repr(e)[:150]


def classify(code):
    c = str(code)
    if c.startswith("2") or c.startswith("3"):
        return "通", None
    if c == "403":
        return "可达但拒绝", "warn"      # 多半是需要登录态或该文件不存在
    if c in ("000", "500", "502", "503", "504"):
        return "不通", "bad"
    return "异常 " + c, "warn"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="把结果写成 JSON，给 daily 的报告用")
    a = ap.parse_args()
    rows, bad_required = [], []
    print("数据源连通性 · %s" % time.strftime("%Y-%m-%d %H:%M"))
    print("-" * 66)
    for name, url, who, required in SOURCES:
        try:
            code, secs, size = hit(url)
        except Exception as e:
            code, secs, size = "000", "0", repr(e)[:40]
        state, lvl = classify(code)
        ok = lvl is None
        mark = "✗" if lvl == "bad" else ("!" if lvl == "warn" else "✓")
        print("%s %-22s %-6s %5ss  %s" % (mark, name, state, round(float(secs), 1), "必需" if required else "可选"))
        rows.append({"kind": "source", "name": name, "code": code, "seconds": round(float(secs), 2),
                     "state": state, "ok": ok, "required": required, "used_by": who})
        if required and lvl == "bad":
            bad_required.append(name)

    degraded = []
    for name, cmd, who, marker in CHANNELS:
        rc, full = run(cmd)
        ok = (rc == 0) or bool(marker) and (marker in full)
        brief = " / ".join(x.strip()[:70] for x in full.splitlines()[-2:])[:120]
        state = "通" if ok else "不通"
        print("%s %-22s %-6s        （%s）" % ("✓" if ok else "!", name, state, brief))
        rows.append({"kind": "channel", "name": name, "code": str(rc), "state": state,
                     "ok": ok, "required": False, "used_by": who, "detail": brief})
        # 推送/分发通道挂了不影响"把今天的数据抓准"，所以不写进 bad_required：
        # 停链只会让数据更旧。它进 degraded，报告里单独列一行提醒。
        if not ok:
            degraded.append(name)

    # 小程序回归的通道：脚本连的是已经开着的开发者工具（ws 9421），不是自己拉进程。
    # 这一条以前被写进文档当成"这台跑不了"，其实它每天状态都可能不一样（IDE 开没开、包装没装），
    # 所以这里现探，不让人去信一份会过期的说明。
    name, host, port = "微信开发者工具自动化端口", "127.0.0.1", 9421
    who = "mini-m01-check.js / mini-m02-check.js 靠它（还要 NODE_PATH 指向 miniprogram-automator）"
    s = socket.socket()
    s.settimeout(4)
    try:
        s.connect((host, port))
        live = True
    except Exception:
        live = False
    finally:
        s.close()
    print("%s %-22s %-6s        （%s:%d）" % ("✓" if live else "!", name, "在听" if live else "没开", host, port))
    rows.append({"kind": "channel", "name": name, "code": "open" if live else "closed",
                 "state": "在听" if live else "没开", "ok": live, "required": False, "used_by": who})
    if not live:
        degraded.append(name)

    print("-" * 66)
    if bad_required:
        print("✗ 必需来源不通：%s" % "、".join(bad_required))
        print("  抓取会拿旧快照继续跑、还把日期写成今天——所以 daily 停在这一步。")
    else:
        print("✓ 必需来源全部可用")
    if degraded:
        print("! 通道不可用（不影响抓取，影响推送与发布）：%s" % "、".join(degraded))
    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(
            json.dumps({"sources": rows, "degraded": degraded, "blocked": bad_required},
                       ensure_ascii=False, indent=1))
    sys.exit(1 if bad_required else 0)


if __name__ == "__main__":
    main()
