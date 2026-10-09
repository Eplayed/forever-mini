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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default=",".join(FILES), help="逗号分隔的 key")
    ap.add_argument("--show", action="store_true", help="只报规模，不落盘")
    a = ap.parse_args()

    build = discover_build()
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
