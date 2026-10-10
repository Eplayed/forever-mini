#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 src/data/talents/*.json 与 src/data/races.json 派生「归属|中文名 → 本地图标键」映射，写 src/data/icons.json。

为什么要派生而不是手抄：图标键本来就在天赋与种族数据里，手抄第二份必然和上游漂移。
界面（技能书、术语速查）按 classId|名称 查这张表，种族特长用 raceId|名称——同一个名字在不同
种族是两回事，只按名字查会串图。查得到就用本地转存图，查不到就画自绘占位块：基础技能与没拿到
键的特长没有可信图标来源，不拿别的图凑数。
用法：python3 tools/build-icon-map.py
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")
TALENTS = os.path.join(DATA, "talents")
ICONS = os.path.join(ROOT, "src", "img", "icons")


def collect_all_keys():
    """扫全部数据文件里出现过的 iconKey，找出本地没转存下来的那些。

    界面是"先画自绘块、有本地图再叠上去"，所以缺图会有一次 404。
    这份清单把"哪些键本来就没有图"登记下来，回归脚本只放行清单里的，
    多出来的 404 一律算失败——防止悄悄引入外链或漏抓。"""
    keys = {}

    def walk(node, src):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "iconKey" and isinstance(v, str) and v:
                    keys.setdefault(v, set()).add(src)
                else:
                    walk(v, src)
        elif isinstance(node, list):
            for x in node:
                walk(x, src)

    # 以前这里写死了一份文件清单，加一个新模块就会漏登记（传承页差点带着未登记的 404 上线）。
    # 现在扫 data 目录下所有数据文件，只排除两份自身就是登记结果的。
    SKIP = {"icons.json", "icon-gaps.json"}
    names = sorted(fn for fn in os.listdir(DATA)
                   if fn.endswith(".json") and fn not in SKIP)
    for fn in names:
        fp = os.path.join(DATA, fn)
        if os.path.exists(fp):
            walk(json.load(open(fp, encoding="utf-8")), fn)
    for fn in sorted(os.listdir(TALENTS)):
        if fn.startswith("_") or not fn.endswith(".json"):
            continue
        walk(json.load(open(os.path.join(TALENTS, fn), encoding="utf-8")), "talents/" + fn)
    return keys


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
    # 种族特长：键用 raceId|特长名，和 glossary 里 racial 词条的 raceId 对齐
    rc_path = os.path.join(DATA, "races.json")
    if os.path.exists(rc_path):
        rc = json.load(open(rc_path, encoding="utf-8"))
        for x in rc.get("races") or []:
            pool = list(x.get("traits") or [])
            if x.get("subgroup"):
                pool += list(x["subgroup"].get("traits") or [])
            for t in pool:
                if t.get("iconKey") and t.get("name"):
                    mapping[x["id"] + "|" + t["name"]] = t["iconKey"]
                    # 天裔词条的归属可能记在合并键上，两个子族都补一份
                    if x["id"].startswith("skyborne"):
                        mapping["skyborne|" + t["name"]] = t["iconKey"]

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

    all_keys = collect_all_keys()
    files = set(f[:-4] for f in os.listdir(ICONS) if f.endswith(".jpg"))
    gaps = sorted(k for k in all_keys if k not in files)
    _byfile = {}
    for k in gaps:
        for f in sorted(all_keys[k]):
            _byfile[f] = _byfile.get(f, 0) + 1
    gap_payload = {
        "meta": {
            "generatedAt": datetime.date.today().isoformat(),
            "method": "tools/build-icon-map.py 扫全部数据文件的 iconKey，比对 src/img/icons/ 本地文件",
            "note": "这些图标键在数据里被引用，但官方 CDN 没有对应文件（多是无限服新装备）。"
                    "界面退回自绘块；回归脚本只放行这份清单里的 404。",
            "count": len(gaps),
            "localFiles": len(files),
            "referenced": len(all_keys)
        },
        "keys": gaps,
        "byFile": dict(sorted(_byfile.items()))
    }
    gp = os.path.join(DATA, "icon-gaps.json")
    with open(gp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(gap_payload, ensure_ascii=False, indent=1) + "\n")
    print("缺图登记 %d 个键 → src/data/icon-gaps.json" % len(gaps))
    if gaps:
        print("  %s" % "、".join(gaps[:8]))


if __name__ == "__main__":
    main()
