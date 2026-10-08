#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 src/data/talents/*.json 派生「职业+中文名 → 本地图标键」映射，写 src/data/icons.json。

为什么要派生而不是手抄：图标键本来就在天赋数据里，手抄第二份必然和上游漂移。
界面（技能书、术语速查、种族特长表）按 "classId|名称" 查这张表，查得到就用本地转存图，
查不到就画自绘占位块——基础技能与种族特长我们没有可信图标来源，不拿别的图凑数。

用法：python3 tools/build-icon-map.py
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")
TALENTS = os.path.join(DATA, "talents")
ICONS = os.path.join(ROOT, "src", "img", "icons")


def main():
    mapping = {}
    dup = []
    files = set(f[:-4] for f in os.listdir(ICONS) if f.endswith(".jpg"))
    for fn in sorted(os.listdir(TALENTS)):
        if fn.startswith("_") or not fn.endswith(".json"):
            continue
        tree = json.load(open(os.path.join(TALENTS, fn), encoding="utf-8"))
        cid = tree.get("classId") or fn[:-5]
        for tr in tree.get("trees") or []:
            for n in tr.get("nodes") or []:
                name, key = n.get("nameCn"), n.get("iconKey")
                if not name or not key:
                    continue
                k = cid + "|" + name
                if k in mapping and mapping[k] != key:
                    dup.append(k)
                mapping[k] = key
    missing = sorted({v for v in mapping.values() if v not in files})
    payload = {
        "meta": {
            "generatedAt": datetime.date.today().isoformat(),
            "method": "tools/build-icon-map.py 从 src/data/talents/*.json 派生，键是 classId|中文名",
            "note": "只有天赋节点有本地转存图标。基础技能与种族特长没有可信图标来源，界面用自绘占位块，不拿别的图凑数。",
            "count": len(mapping),
            "localFiles": len(files),
            "missingFiles": missing,
            "sameNameDifferentIcon": sorted(dup)
        },
        "map": mapping
    }
    out = os.path.join(DATA, "icons.json")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print("映射 %d 条（本地图标文件 %d 张，缺文件 %d）→ src/data/icons.json" % (len(mapping), len(files), len(missing)))
    if dup:
        print("  同名不同图标键 %d 处：%s" % (len(dup), "、".join(dup[:5])))
    if missing:
        print("  缺本地文件：%s" % "、".join(missing[:8]))


if __name__ == "__main__":
    main()
