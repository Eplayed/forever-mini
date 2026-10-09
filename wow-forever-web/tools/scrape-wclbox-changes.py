#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 wowforever.wclbox.com 的改动清单（_shuju/<发布号>/changes.json），入库前先删句子。

这份数据 964 条，一条一个天赋或法术，原始 JSON 里带着前后版本的完整 tooltip 文本（rank_texts、
classic.rank_texts、summary、forever_note、uncertainties）。2026-10-09 用户口径：**最新动态只放名称与
改动类型，不放句子**——所以这个脚本在落盘前就把所有文本字段丢掉，仓库里不留别人转述的游戏文案，
也不给界面留误用的口子。

留下的都是事实性标识符：职业、类型（天赋/法术）、所在系、图标文件名、改动类别、层数上限、
发现日期、以及它自己的来源链接（wago.tools 的客户端 DB）。

用法：
    python3 tools/scrape-wclbox-changes.py
    python3 tools/scrape-wclbox-changes.py --show      # 只看规模与删了哪些字段
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "src", "data", "upstream")
BASE = "https://wowforever.wclbox.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BUILD_RE = re.compile(r"/_shuju/(r-\d+)/")

# 一律不落盘的字段：句子、上游自己的判断与备注
DROP = ["rank_texts", "estimated_rank_texts", "summary", "changes", "tooltip_metadata",
        "forever_note", "uncertainties", "spellbook", "order"]
# 只从 classic 里留这几个（改名条目需要旧名，其余是文本）
CLASSIC_KEEP = ["name", "status", "match_status", "build"]


def http(url):
    p = subprocess.run(["curl", "-s", "-L", "-m", "60", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True)
    body = p.stdout
    nl = body.rfind(b"\n")
    code = int(body[nl + 1:].strip() or 0) if nl >= 0 else 0
    return code, body[:nl].decode("utf-8", "replace")


def discover_build():
    for path in ("/gaidong", "/xiyou", "/"):
        code, html = http(BASE + path)
        if code == 200:
            m = BUILD_RE.search(html)
            if m:
                return m.group(1)
    sys.exit("没在页面里找到 _shuju 发布号，上游可能改了目录结构")


def strip_row(x):
    out = {k: v for k, v in x.items() if k not in DROP}
    cl = x.get("classic") or {}
    out["classic"] = {k: cl.get(k) for k in CLASSIC_KEEP if cl.get(k) is not None}
    out["sources"] = [{"type": s.get("type"), "url": s.get("url")}
                      for s in (x.get("sources") or []) if s.get("url")]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="只报规模，不落盘")
    a = ap.parse_args()

    build = discover_build()
    code, text = http("%s/_shuju/%s/changes.json" % (BASE, build))
    if code != 200:
        sys.exit("changes.json 取不到（HTTP %d）" % code)
    rows = json.loads(text)
    code, mtxt = http("%s/_shuju/%s/meta.json" % (BASE, build))
    meta = json.loads(mtxt) if code == 200 else {}

    kept = [strip_row(x) for x in rows]
    dropped = sorted({f for x in rows for f in DROP if f in x})
    print("改动 %d 条（发布号 %s，foreverBuild %s）；删掉字段：%s" % (
        len(kept), build, meta.get("foreverBuild"), "、".join(dropped)))
    if a.show:
        return

    if not os.path.isdir(UP):
        os.makedirs(UP)
    out = {
        "meta": {
            "source": BASE + "/gaidong",
            "release": build,
            "foreverBuild": meta.get("foreverBuild"),
            "classicBuild": meta.get("classicBuild"),
            "upstreamCounts": meta.get("counts"),
            "scrapedAt": datetime.date.today().isoformat(),
            "endpoint": "%s/_shuju/%s/changes.json" % (BASE, build),
            "droppedFields": dropped,
            "note": u"入库前已删除全部文本字段（前后 tooltip 原句、上游摘要与备注），只留名称与改动类别。"
        },
        "rows": kept,
    }
    p = os.path.join(UP, "wclbox-changes.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("写入 %s（%.0f KB，原始 1.6 MB）" % (os.path.relpath(p, ROOT), os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
