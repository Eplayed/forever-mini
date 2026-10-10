#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓暴雪客户端 DB2 表「队伍查找器活动」的转储，写进 src/data/upstream/。

为什么要它：这张表是**客户端里的排队数据**，一个副本的等级区间、进入人数上限、
地图 ID 都在这一行里。以前这些数只能从第三方资料站的网页 DOM 里读，
读回来的是"别人怎么排版"，不是"客户端写了什么"。有了这张表可以：
  1) 逐座对账本站的等级区间（谁和客户端不一样，两个都留、标出来）；
  2) 补上我们一直没有英文原名的副本（18 座）；
  3) 把"客户端队伍查找器里已经有条目、本站还没有名单"的本列出来。

口径（红线）：
  - 只取事实性标识符：ID、英文名、等级、人数上限、地图 ID、类别。
    表里的 Description_lang 这类说明文本一律不落盘。
  - wago.tools 是把客户端 DB2 转成 CSV 的第三方站，不是暴雪域名。
    所以这批英文名是"官方英文原文，经第三方转述"，界面上算 L1，不当 L0 支撑。
  - 构建号从解包资料站的 _shuju/<发布号>/meta.json 里现读（它会跟着上游发版变），
    不写死；读不到就报错退出，不用旧构建号蒙混。

用法：
    python3 tools/fetch-db2-groupfinder.py            # 抓 + 写 upstream
    python3 tools/fetch-db2-groupfinder.py --show     # 只看规模，不落盘
    python3 tools/fetch-db2-groupfinder.py --build 1.60.1.70334   # 指定构建号（复核历史用）
"""
import argparse
import csv
import datetime
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "src", "data", "upstream")
SITE = "https://wowforever.wclbox.com"
WAGO = "https://wago.tools/db2"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

TABLE = "GroupFinderActivity"
CATEGORY_TABLE = "GroupFinderCategory"
# 只留这些列：全是标识符与数值，没有句子
KEEP = ["ID", "FullName_lang", "ShortName_lang", "GroupFinderCategoryID", "OrderIndex",
        "MinGearLevelSuggestion", "PlayerConditionID", "MapID", "DifficultyID", "AreaID",
        "ExpansionID", "MaxPlayers", "MinLevel", "MaxLevelSuggestion"]
FIELD = {
    "ID": "activityId", "FullName_lang": "nameEn", "ShortName_lang": "nameEnShort",
    "GroupFinderCategoryID": "categoryId", "OrderIndex": "orderIndex",
    "MinGearLevelSuggestion": "gearLevelSuggestion", "PlayerConditionID": "playerConditionId",
    "MapID": "mapId", "DifficultyID": "difficultyId", "AreaID": "areaId",
    "ExpansionID": "expansionId", "MaxPlayers": "maxPlayers",
    "MinLevel": "minLevel", "MaxLevelSuggestion": "maxLevel",
}
BUILD_RE = re.compile(r"/_shuju/(r-\d+)/")
VER_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


def http(url):
    p = subprocess.run(["curl", "-s", "-L", "-m", "60", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True)
    body = p.stdout
    nl = body.rfind(b"\n")
    code = int(body[nl + 1:].strip() or 0) if nl >= 0 else 0
    return code, body[:nl].decode("utf-8", "replace")


def discover_build():
    """客户端构建号跟着上游发版变，写死就会对不上账，所以每次现读。"""
    for path in ("/ditu", "/fuben", "/"):
        code, html = http(SITE + path)
        if code != 200:
            continue
        m = BUILD_RE.search(html)
        if not m:
            continue
        code2, text = http("%s/_shuju/%s/meta.json" % (SITE, m.group(1)))
        if code2 != 200:
            continue
        try:
            meta = json.loads(text)
        except ValueError:
            continue
        b = meta.get("foreverBuild")
        if b and VER_RE.match(str(b)):
            return b, m.group(1), meta
    sys.exit("拿不到客户端构建号（_shuju/<发布号>/meta.json 里的 foreverBuild），"
             "上游可能改了目录结构，先人工看页面再重跑")


def table_csv(build, table):
    url = "%s/%s/csv?build=%s" % (WAGO, table, build)
    code, text = http(url)
    if code != 200:
        sys.exit("%s 在构建 %s 上返回 HTTP %s——wago 只留最近几个构建，"
                 "换一个构建号或等上游更新" % (table, build, code))
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        sys.exit("%s 解出 0 行，不落盘" % table)
    return url, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", help="指定客户端构建号（默认从解包站现读）")
    ap.add_argument("--show", action="store_true", help="只报规模，不落盘")
    a = ap.parse_args()

    shuju_release = None
    if a.build:
        build = a.build
    else:
        build, shuju_release, _ = discover_build()
    print("构建号 %s（发布号 %s）" % (build, shuju_release or "手工指定"))

    cat_url, cat_rows = table_csv(build, CATEGORY_TABLE)
    categories = {}
    for r in cat_rows:
        # Description_lang 是说明文本，红线不搬；只要 ID 与名称
        categories[str(r.get("ID"))] = (r.get("Name_lang") or "").replace("\n", " / ").strip()
    print("ok %-22s %d 个类别" % (CATEGORY_TABLE, len(categories)))

    url, rows = table_csv(build, TABLE)
    keep = [r for r in rows if (r.get("GroupFinderCategoryID") or "") in categories]
    acts = []
    for r in keep:
        row = {}
        for col in KEEP:
            if col not in r:
                continue
            v = (r[col] or "").strip()
            if v.isdigit() or (v and re.match(r"^-?\d+$", v)):
                row[FIELD[col]] = int(v)
            else:
                row[FIELD[col]] = v or None
        row["categoryName"] = categories.get(str(r.get("GroupFinderCategoryID")))
        acts.append(row)
    print("ok %-22s %d 条排队活动" % (TABLE, len(acts)))

    if a.show:
        return

    if not os.path.isdir(UP):
        os.makedirs(UP)
    out = {
        "meta": {
            "table": TABLE,
            "build": build,
            "release": shuju_release,
            "url": url,
            "categoryUrl": cat_url,
            "fetchedAt": datetime.date.today().isoformat(),
            "took": "活动 ID、英文原名、类别、最低等级与建议上限等级、人数上限、地图 ID",
            "skipped": "表里的说明文本列；本站不转述别人的描述",
            "note": "wago.tools 是客户端 DB2 的 CSV 转储站，不是暴雪域名。"
                    "这里的英文名属「官方英文原文，经第三方转述」，界面按 L1 显示，不支撑 L0。",
            "caveat": "上游的 _shuju 卡片里还有个 enter 字段，逐列比过这张表都对不上"
                      "（怒焰裂谷写 8，客户端 MinLevel 是 13），归不了因，所以不采。",
        },
        "categories": [{"id": k, "nameEn": v} for k, v in sorted(categories.items())],
        "activities": acts,
    }
    p = os.path.join(UP, "db2-group-finder.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("写入 %s（%.1f KB）" % (os.path.relpath(p, ROOT), os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
