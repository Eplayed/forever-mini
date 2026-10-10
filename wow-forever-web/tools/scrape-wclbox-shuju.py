#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 wowforever.wclbox.com 的世界线结构化数据（_shuju 数据包），写进 src/data/upstream/。

为什么不用浏览器：这一站的世界页正文虽然是客户端渲染的，但它把渲染要用的数据
放在 /_shuju/<发布号>/ 下的静态 JSON 里（maps / map-zones / map-reach / xiyou / shuji / shuidai），
curl 就能拿到，比解 DOM 干净。发布号会随上游发版变，所以每次都先从页面里现读，不写死。

红线口径：这里只取事实性标识符——名称、坐标、等级区间、mapId、图标文件名、物品 ID。
上游写在 JSON 里的描述文案（书的 flavour、营地路线的讲解）不进我们的数据文件。

用法：
    python3 tools/scrape-wclbox-shuju.py                 # 全量抓 + 写 upstream
    python3 tools/scrape-wclbox-shuju.py --what xiyou,shuji
    python3 tools/scrape-wclbox-shuju.py --show          # 只打印拿到的规模，不落盘
    python3 tools/scrape-wclbox-shuju.py --group dungeons  # 只取副本元数据 → wclbox-dungeon-meta.json
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

# 世界线要的 JSON：key → 包内路径
FILES = {
    "meta": "meta.json",
    "maps": "maps.json",
    "zones": "map-zones.json",
    "reach": "map-reach.json",
    "xiyou": "xiyou.json",
    "shuji": "shuji.json",
    "shuidai": "shuidai.json",
}
BUILD_RE = re.compile(r"/_shuju/(r-\d+)/")

# 副本线的结构化包：与 world 分开落盘，因为跑 world 场景不该顺手改动副本线的上游（幂等要求）。
# 只留事实性标识符。删掉的列与原因：
#   summary —— 上游自己写的介绍句子，红线不转述别人的描述；
#   enter   —— 逐列比对过 wago 的 GroupFinderActivity 表，对不上任何一列
#             （怒焰裂谷写 8、客户端 MinLevel 是 13），归不了因就是别人拍的数，不采；
#   abbr / short —— 上游自己的中文简称，属编辑口径，不要；
#   demo / top —— 标记位，含义上游没写，不猜。
DUNGEON_FILE = "dungeons.json"
DUNGEON_OUT = "wclbox-dungeon-meta.json"
DUNGEON_KEEP = ("name", "status", "levels", "zone", "faction", "art", "players")


def http(url):
    p = subprocess.run(["curl", "-s", "-L", "-m", "40", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True)
    body = p.stdout
    nl = body.rfind(b"\n")
    code = int(body[nl + 1:].strip() or 0) if nl >= 0 else 0
    return code, body[:nl].decode("utf-8", "replace")


def discover_build():
    """发布号写死会随上游发版失效，从任意一个世界页的 HTML 里现读。"""
    for path in ("/xiyou", "/ditu", "/"):
        code, html = http(BASE + path)
        if code == 200:
            m = BUILD_RE.search(html)
            if m:
                return m.group(1)
    sys.exit("没在页面里找到 _shuju 发布号，上游可能改了目录结构")


def fetch_dungeon_meta(build):
    """副本线专用：只取排队元数据，与 world 分开落盘。

    为什么单独一条链路：refresh.sh world 不该顺手改动副本线的上游（重跑必须幂等），
    而这两份 JSON 的下游合并器也完全不同。
    """
    url = "%s/_shuju/%s/%s" % (BASE, build, DUNGEON_FILE)
    code, text = http(url)
    if code != 200:
        sys.exit("%s 返回 HTTP %s，不写空文件" % (url, code))
    try:
        raw = json.loads(text)
    except ValueError:
        sys.exit("%s 不是合法 JSON" % url)
    if not isinstance(raw, list) or not raw:
        sys.exit("%s 解出 %r，不是预期的条目数组" % (url, type(raw)))
    rows = []
    for r in raw:
        row = {"id": r.get("id"), "nameCn": r.get("name")}
        for k in DUNGEON_KEEP:
            row[k if k != "name" else "nameCn"] = r.get(k)
        src = (r.get("sources") or [{}])[0]
        row["sourceUrl"] = src.get("url")
        row["sourceType"] = src.get("type")
        rows.append(row)
    out = {
        "meta": {
            "source": url,
            "release": build,
            "scrapedAt": datetime.date.today().isoformat(),
            "took": "等级区间、阵营与所在区域、载入图键、人数上限、是否无限新增",
            "skipped": "上游写的介绍句子（summary）、它对不上客户端表的 enter 列、"
                       "上游自定的中文简称（abbr/short）、含义不明的标记位（demo/top）",
            "note": "这一份里一条首领与掉落数据都没有，替代不了详情页名单，"
                    "接它只为拿卡片元数据这一层。",
        },
        "dungeons": rows,
    }
    if not os.path.isdir(UP):
        os.makedirs(UP)
    p = os.path.join(UP, DUNGEON_OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("ok %-10s %d 条" % ("dungeons", len(rows)))
    print("写入 %s（%.1f KB）" % (os.path.relpath(p, ROOT), os.path.getsize(p) / 1024.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default=",".join(FILES), help="逗号分隔的 key")
    ap.add_argument("--show", action="store_true", help="只报规模，不落盘")
    ap.add_argument("--group", default="world", choices=("world", "dungeons"),
                    help="world=世界线六份 JSON；dungeons=只取副本排队元数据（另落一个文件）")
    a = ap.parse_args()

    build = discover_build()
    if a.group == "dungeons":
        if a.show:
            code, text = http("%s/_shuju/%s/%s" % (BASE, build, DUNGEON_FILE))
            print("dungeons.json HTTP %s，%d 字节（--show 不落盘）" % (code, len(text.encode("utf-8"))))
            return
        fetch_dungeon_meta(build)
        return

    want = [x.strip() for x in a.what.split(",") if x.strip() in FILES]

    payload, urls = {}, {}
    for key in want:
        url = "%s/_shuju/%s/%s" % (BASE, build, FILES[key])
        code, text = http(url)
        if code != 200:
            print("!! %s HTTP %s（跳过）" % (FILES[key], code))
            continue
        try:
            payload[key] = json.loads(text)
        except ValueError:
            print("!! %s 不是合法 JSON（跳过）" % FILES[key])
            continue
        urls[key] = url
        print("ok %-8s %6d 字节" % (key, len(text.encode("utf-8"))))

    if a.show:
        return
    if not payload:
        sys.exit("一个 JSON 都没拿到，不写空文件")

    if not os.path.isdir(UP):
        os.makedirs(UP)
    meta = payload.get("meta") or {}
    out = {
        "meta": {
            "source": BASE + "/ditu",
            "sourcePages": [BASE + p for p in ("/ditu", "/xiyou", "/shuji", "/shuidai")],
            "release": build,
            "foreverBuild": meta.get("foreverBuild"),
            "classicBuild": meta.get("classicBuild"),
            "dropsAsOf": meta.get("dropsAsOf"),
            "scrapedAt": datetime.date.today().isoformat(),
            "endpoints": urls,
            "took": "地图清单、区域等级与阵营、稀有精英位置与掉落归属、书籍位置、睡袋物品",
            "skipped": "上游 JSON 里的书本文案、营地路线讲解、任何攻略性建议",
        },
        "payload": payload,
    }
    p = os.path.join(UP, "wclbox-world.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("写入 %s（%.1f KB）" % (os.path.relpath(p, ROOT), os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
