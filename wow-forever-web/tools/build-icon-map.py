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


def set_paths(root):
    """把 DATA / TALENTS / ICONS / GAPS 指到另一棵树上。
       --selftest 与 --root 用它跑临时夹具：不碰真实资料与图片。"""
    global DATA, TALENTS, ICONS, GAPS
    DATA = os.path.join(root, "src", "data")
    TALENTS = os.path.join(DATA, "talents")
    ICONS = os.path.join(root, "src", "img", "icons")
    GAPS = os.path.join(DATA, "icon-gaps.json")
# 合法图标键：字母数字下划线与连字符，3–80 位。
# 连字符必须收：items.json 里 flightstone-blue、inv_chest-_cloth_skybornec60_b_01 这类
# 带横杠的键有几十个，是上游物品图标名的真实写法（fetch-icons.py 那条 [a-z0-9_] 只用来
# 拼下载 URL，比这里严——那边会跳过这些键，不代表它们不合法）。
KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{3,80}$")

# 两个字段两种语义，2026-10-20 W01-R1 定死。在此之前它们共用一个 norm_key，
# 于是尾点、双后缀、带路径分隔的坏键都被"顺手修好"再放行——独立验收拿夹具一试就露馅：
# iconKey 写成 valid_icon. / valid_icon.jpg / bad/key，--check 全都返回 0。
#   iconKey  渲染器直接拿它拼地址（app/src/lib/glyph.js：
#            'img/icons/' + encodeURIComponent(key) + '.jpg'），所以必须是规范键本身。
#            校验端不许修正：修一次，页面就少一张图而门禁仍然绿。
#   icon     这是文件名，允许生成器那套归一（剥一个扩展名、再去残留尾点），
#            不能把合法文件名全部误杀。
# 同一条记录里两个字段都出现时，必须指向同一个键。


def key_from_iconkey(v):
    """返回 (规范键 or None, 坏的原因 or None)。"""
    s = str(v)
    if not s.strip():
        return None, "空值"
    if s.lower().endswith(".jpg"):
        return None, "带 .jpg 后缀：渲染器还要再拼一次，等于请求 %s.jpg" % s
    if s.endswith("."):
        return None, "带尾点：本地文件名没有这个点，请求必然 404"
    if not KEY_RE.match(s):
        return None, "不是合法图标键（只允许字母、数字、下划线、连字符，3–80 位）"
    return s, None


def key_from_iconfile(v):
    """返回 (规范键 or None, 坏的原因 or None)。文件名按生成器规则归一。"""
    s = str(v).strip()
    if not s:
        return None, "空值"
    if not s.lower().endswith(".jpg"):
        return None, "icon 字段应是文件名（形如 x.jpg）"
    n = s[:-4].rstrip(".")
    if not KEY_RE.match(n):
        return None, "剥掉 .jpg 与残留尾点后仍不是合法图标键"
    return n, None


def where(node, src, field):
    """坏键要能定位：文件 › 字段（这一条的 id 或名字）。只说"有个坏键"没法改。"""
    ident = ""
    if isinstance(node, dict):
        ident = str(node.get("id") or node.get("nameCn") or node.get("name") or "")[:40]
    return "%s › %s%s" % (src, field, ("（%s）" % ident) if ident else "")


def collect_all_keys(data_dir=None):
    """扫全部成品数据文件引用的图标键，返回 (键→引用文件集合, 坏键清单)。

    界面是"先画自绘块、有本地图再叠上去"，所以缺图会有一次 404。
    这份清单把"哪些键本来就没有图"登记下来，回归脚本只放行清单里的，
    多出来的 404 一律算失败——防止悄悄引入外链或漏抓。

    范围：data_dir 顶层全部成品 JSON + talents/，排除 upstream/（那是原料快照不是成品）
    与 icons.json / icon-gaps.json（两份登记结果，自己扫自己会打转）。
    **坏键清单必须参与返回码**，不能只打印（上一版就是只打印，等于没有这道闸）。"""
    data_dir = data_dir or DATA
    keys = {}
    bad = []

    def take(node, src, field, fn):
        v = node.get(field)
        if not isinstance(v, str) or not v.strip():
            return None
        k, why = fn(v)
        if why:
            bad.append("%s = %s —— %s" % (where(node, src, field), v[:60], why))
            return None
        keys.setdefault(k, set()).add(src)
        return k

    def walk(node, src):
        if isinstance(node, dict):
            kkey = take(node, src, "iconKey", key_from_iconkey)
            kfile = take(node, src, "icon", key_from_iconfile)
            if kkey and kfile and kkey != kfile:
                bad.append("%s：iconKey「%s」与 icon「%s」指向两个不同的键" % (
                    where(node, src, "iconKey/icon"), kkey, kfile))
            for k, v in node.items():
                if k in ("iconKey", "icon"):
                    continue
                walk(v, src)
        elif isinstance(node, list):
            for x in node:
                walk(x, src)

    skip = {"icons.json", "icon-gaps.json"}
    talents = os.path.join(data_dir, "talents")
    for fn in sorted(f for f in os.listdir(data_dir) if f.endswith(".json") and f not in skip):
        walk(json.load(open(os.path.join(data_dir, fn), encoding="utf-8")), fn)
    if os.path.isdir(talents):
        for fn in sorted(os.listdir(talents)):
            if fn.startswith("_") or not fn.endswith(".json"):
                continue
            walk(json.load(open(os.path.join(talents, fn), encoding="utf-8")), "talents/" + fn)
    return keys, bad


def write_all():
    """生成两份登记。先校验、后落盘：有非法键就直接失败，不留半套登记。"""
    keys_all, bad = collect_all_keys()
    if bad:
        print("数据里有 %d 处图标键不合法，本次不生成任何登记文件（先修数据）：" % len(bad))
        for b_ in bad[:12]:
            print("  ✗ " + b_)
        return 1
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
    return 0


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
    # 坏键必须参与返回码（上一版只打印——独立验收拿夹具一试就是全 0 通过）
    if bad:
        print("数据里有 %d 处图标键不合法（渲染器拼出来的地址必然 404），先修数据再谈登记：" % len(bad))
        for b_ in bad[:12]:
            print("  ✗ " + b_)
    if not unreg and not stale and not dead and not bad:
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


def selftest():
    """隔离夹具回归：在临时目录里造一棵小树跑校验，不碰真实资料与图片。

    这一组用例是 2026-10-20 独立验收点名的两处误放行反例——
    上一版扫描器把 iconKey 的尾点/双后缀/路径分隔"顺手修好"再判，
    四种坏写法 --check 全部返回 0，等于这道闸对下一次错误无效。
    用法：python3 tools/build-icon-map.py --selftest
    """
    import shutil
    import tempfile
    root = tempfile.mkdtemp(prefix="icon-gaps-selftest-")
    data = os.path.join(root, "src", "data")
    icons = os.path.join(root, "src", "img", "icons")
    os.makedirs(data)
    os.makedirs(icons)
    open(os.path.join(icons, "valid_icon.jpg"), "wb").write(b"\xff\xd8\xff fake")
    results = []

    def run(name, records, gaps_keys, want_rc, also_check_files_absent=False):
        set_paths(root)
        with open(os.path.join(data, "probe.json"), "w", encoding="utf-8") as fh:
            json.dump({"items": records}, fh, ensure_ascii=False)
        gp = os.path.join(data, "icon-gaps.json")
        if gaps_keys is None:
            if os.path.exists(gp):
                os.remove(gp)
        else:
            with open(gp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"keys": gaps_keys}, ensure_ascii=False))
        rc = check_gaps()
        ok = (rc == want_rc)
        if also_check_files_absent:
            rc2 = write_all()
            gone = (not os.path.exists(gp)) and (not os.path.exists(os.path.join(data, "icons.json")))
            ok = ok and rc2 != 0 and gone
        results.append((ok, name, "check 返回 %s（期望 %s）%s" % (
            rc, want_rc, "；生成模式未产出半套登记" if also_check_files_absent else "")))
        # 把上一例的 probe 清掉，避免互相污染
        os.remove(os.path.join(data, "probe.json"))

    # ① 规范键 + 本地有图 → 通过
    run("规范键 valid_icon（本地有这张图）", [{"id": "a", "iconKey": "valid_icon"}], [], 0)
    # ② 尾点：以前被 norm_key 抹平后当成合法键，门禁 0 通过
    run("iconKey 带尾点 valid_icon.", [{"id": "b", "iconKey": "valid_icon."}], [], 1)
    # ③ 双后缀：渲染器会拼成 valid_icon.jpg.jpg
    run("iconKey 带 .jpg 后缀 valid_icon.jpg", [{"id": "c", "iconKey": "valid_icon.jpg"}], [], 1)
    # ④ 路径分隔
    run("iconKey 带路径 bad/key", [{"id": "d", "iconKey": "bad/key"}], [], 1)
    # ⑤ icon 是文件名字段，合法归一不能误杀
    run("icon 文件名 valid_icon.jpg（合法，不该误杀）", [{"id": "e", "icon": "valid_icon.jpg"}], [], 0)
    # ⑥ 同一条记录两个字段指向不同键
    run("iconKey 与 icon 指向两个键", [{"id": "f", "iconKey": "valid_icon", "icon": "other_icon.jpg"}], [], 1)
    # ⑦ 缺图引用了但没登记（漏登记）
    run("引用且本地没有、却没登记", [{"id": "g", "iconKey": "no_such_icon"}], [], 1)
    # ⑧ 登记说缺、其实本地已有（过期登记）
    run("登记过期（本地其实有图）", [], ["valid_icon"], 1)
    # ⑨ 登记里的键现在没人引用（死条目）
    run("死条目（登记里没人引用）", [], ["nobody_references_me"], 1)
    # ⑩ 精确相等才算通过
    run("引用且缺、登记一致", [{"id": "j", "iconKey": "no_such_icon"}], ["no_such_icon"], 0)
    # ⑪ 生成模式遇到非法键：失败且不产出登记
    run("非法键时生成模式不留半套登记", [{"id": "k", "iconKey": "bad.key!"}], None, 1,
        also_check_files_absent=True)

    shutil.rmtree(root, ignore_errors=True)
    set_paths(ROOT)
    bad = 0
    print("\n=== build-icon-map.py 夹具回归 ===")
    for ok, name, detail in results:
        print("  %s  %-40s %s" % ("PASS" if ok else "FAIL", name, detail))
        bad += 0 if ok else 1
    print("用例 %d 条，失败 %d 条" % (len(results), bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="只把登记与实况比一遍（build-data.js 用这条当卡口），不写文件")
    ap.add_argument("--selftest", action="store_true",
                    help="临时目录夹具回归：坏 iconKey 必须失败、合法文件名不能误杀、生成不留半套登记")
    ap.add_argument("--root", default=ROOT,
                    help="换一棵树跑（夹具与隔离测试用），默认本仓库")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if args.root != ROOT:
        set_paths(args.root)
    if args.check:
        sys.exit(check_gaps())
    sys.exit(write_all())



if __name__ == "__main__":
    main()
