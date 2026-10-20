#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 src/data/talents/*.json 与 src/data/races.json 派生「归属|中文名 → 本地图标键」映射，写 src/data/icons.json。

为什么要派生而不是手抄：图标键本来就在天赋与种族数据里，手抄第二份必然和上游漂移。
界面（技能书、术语速查）按 classId|名称 查这张表，种族特长用 raceId|名称——同一个名字在不同
种族是两回事，只按名字查会串图。查得到就用本地转存图，查不到就画自绘占位块：基础技能与没拿到
键的特长没有可信图标来源，不拿别的图凑数。
用法：python3 tools/build-icon-map.py
"""
import argparse
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")
TALENTS = os.path.join(DATA, "talents")
ICONS = os.path.join(ROOT, "src", "img", "icons")
GAPS = os.path.join(DATA, "icon-gaps.json")
# 合法图标键：字母数字下划线与连字符，3–80 位。
# 连字符必须收：items.json 里 "flightstone-blue"、"inv_chest-_cloth_skybornec60_b_01" 这类
# 带横杠的键有几十个，是上游物品图标名的真实写法（fetch-icons.py 那条 [a-z0-9_] 只用来
# 拼下载 URL，比这里严——那边会跳过这些键，不代表它们不合法）。
# 不收的只有：带路径分隔的、带空格的、空串、以及归一完还剩点的（那是文件名不是键名）。
KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{3,80}$")


def norm_key(v):
    """图标键归一：items.json 的 icon 存的是"inv_sword_04.jpg"这种带后缀的文件名，
       本地文件也叫这个名字——再拼一次 .jpg 就变成 inv_sword_04.jpg.jpg，
       永远查不到，会被算成一张根本不存在的缺图（2026-10-20 审查点名的那条）。
       所以统一剥掉后缀，只留键名；剥完还不是合法键的，单独报出来不静默收下。"""
    s = str(v).strip()
    if s.lower().endswith(".jpg"):
        s = s[:-4]
    # 上游键名带尾点是实测到过的（"spell_shadow_devouringplague."），归一掉再比
    return s.rstrip(".")


def collect_all_keys():
    """扫全部数据文件里出现过的图标键，找出本地没转存下来的那些。

    界面是"先画自绘块、有本地图再叠上去"，所以缺图会有一次 404。
    这份清单把"哪些键本来就没有图"登记下来，回归脚本只放行清单里的，
    多出来的 404 一律算失败——防止悄悄引入外链或漏抓。

    范围（2026-10-20 W01 定死）：src/data 顶层全部成品 JSON + talents/ 目录，
    排除 upstream/（那是原料快照不是成品）与 icons.json / icon-gaps.json（这两份是登记结果，
    自己扫自己会打转）。字段收 iconKey 与 icon 两种，按 norm_key 归一。"""
    keys = {}
    bad = []

    def walk(node, src):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("iconKey", "icon") and isinstance(v, str) and v.strip():
                    kk = norm_key(v)
                    if KEY_RE.match(kk):
                        keys.setdefault(kk, set()).add(src)
                    else:
                        bad.append("%s: %s" % (src, v[:60]))
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
    return keys, bad



def write_all():
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

    all_keys, bad = collect_all_keys()
    files = set(f[:-4] for f in os.listdir(ICONS) if f.endswith(".jpg"))
    gaps = sorted(k for k in all_keys if k not in files)
    _byfile = {}
    for k in gaps:
        for f in sorted(all_keys[k]):
            _byfile[f] = _byfile.get(f, 0) + 1
    gap_payload = {
        "meta": {
            "generatedAt": datetime.date.today().isoformat(),
            "method": "tools/build-icon-map.py 扫全部成品数据文件的 iconKey / icon（归一掉 .jpg 后缀），"
                      "比对 src/img/icons/ 本地文件。范围排除 upstream/ 原料与 icons.json、icon-gaps.json 两份登记自身",
            "note": "这些图标键在数据里被引用，但官方 CDN 没有对应文件（多是无限服新装备）。"
                    "界面退回自绘块；回归脚本只放行这份清单里的 404。"
                    "这份清单是派生物，改数据或补图之后要重跑本脚本，不要手填。",
            "count": len(gaps),
            "localFiles": len(files),
            "referenced": len(all_keys)
        },
        "keys": gaps,
        "byFile": dict(sorted(_byfile.items()))
    }
    with open(GAPS, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(gap_payload, ensure_ascii=False, indent=1) + "\n")
    print("缺图登记 %d 个键 → src/data/icon-gaps.json" % len(gaps))
    if gaps:
        print("  %s" % "、".join(gaps[:8]))
    if bad:
        print("  不是合法图标键、没进登记的字段值 %d 处：%s" % (len(bad), "、".join(bad[:5])))


def check_gaps():
    """--check：把登记与实况逐键比一遍，两个方向都要一致（2026-10-20 W01 加的那道闸）。

    以前 build-data.js 只查"登记说缺、其实本地有"这一个方向，所以 10-16 之后新引用的
    spell_warlock_demonsoul 没登记也照样构建通过，页面上悄悄退成字母块。
    现在：引用键 − 本地存在键 必须**正好等于**登记键；
    少登记（新缺图）与多登记（图已补回）两边都算失败，退出码 1。
    """
    all_keys, bad = collect_all_keys()
    files = set(f[:-4] for f in os.listdir(ICONS) if f.endswith(".jpg"))
    want = set(k for k in all_keys if k not in files)
    if not os.path.exists(GAPS):
        print("icon-gaps.json 不存在：跑 python3 tools/build-icon-map.py 生成")
        return 1
    reg = set(json.load(open(GAPS, encoding="utf-8")).get("keys") or [])
    unreg = sorted(want - reg)                       # 引用了、本地没有、却没登记 —— 会悄悄退字母块
    stale = sorted(k for k in reg - want if k in files)   # 登记说缺、其实图已经在了
    dead = sorted(k for k in reg - want if k not in files)  # 登记里的键现在谁也不引用了（数据改过没重跑登记）
    if bad:
        print("非法图标键值 %d 处（没进登记，先回数据里查）：%s" % (len(bad), "、".join(bad[:5])))
    if not unreg and not stale and not dead:
        print("缺图登记与实况一致：%d 个键（引用 %d、本地 %d 张）" % (len(reg), len(all_keys), len(files)))
        return 0
    if unreg:
        print("icon-gaps：数据里引用且本地没有的键有 %d 个没登记（%s）——重跑 build-icon-map.py"
              % (len(unreg), "、".join(unreg[:6])))
    if stale:
        print("icon-gaps：登记说缺 %d 个，本地其实已有（%s）——重跑 build-icon-map.py"
              % (len(stale), "、".join(stale[:6])))
    if dead:
        print("icon-gaps：登记里有 %d 个键现在没有任何数据引用（%s）——登记是派生物，重跑 build-icon-map.py"
              % (len(dead), "、".join(dead[:6])))
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="只把登记与实况比一遍（build-data.js 用这条当卡口），不写文件")
    args = ap.parse_args()
    if args.check:
        sys.exit(check_gaps())
    write_all()



if __name__ == "__main__":
    main()
