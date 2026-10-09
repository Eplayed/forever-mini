#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""转存客户端原画（职业天赋背景图、副本载入图）到 src/img/art/，本地留存、不热链。

红线口径：这些是暴雪游戏美术，目前只有第三方站托管的副本（官方 CDN 不提供）。
2026-10-08 用户决策：网页与小程序都用。执行要求是全部落到独立目录 +
art/manifest.json 记来源与抓取日期 + 保留"整目录删除即回退到自绘占位"的下线方案。

用法：
    python3 tools/fetch-art.py --what classes     # 九职业背景图（从参考站首页现取带哈希的文件名）
    python3 tools/fetch-art.py --what dungeons    # 副本载入图（逐个 slug 试两台源）
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "src", "img", "art")
DATA = os.path.join(ROOT, "src", "data")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
WCF = "https://wowclassicforever.info"
WBX = "https://wowforever.wclbox.com"
WBX = "https://wowforever.wclbox.com"
# 我们的副本 id → 参考站用的 slug（两边命名不一致的几座）
SLUG_ALIAS = {"whelgars-excavation": "excavation-site-wetlands", "deathmine": "the-deadmines",
              "the-stocks": "the-stockade", "razor-krendor": "razorfen-downs"}


def http(url, binary=False):
    p = subprocess.run(["curl", "-s", "-L", "-m", "30", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True)
    body = p.stdout
    nl = body.rfind(b"\n")
    code = int(body[nl + 1:].strip() or 0) if nl >= 0 else 0
    data = body[:nl]
    return code, (data if binary else data.decode("utf-8", "replace"))


def save(path, blob, url, kind):
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "wb") as fh:
        fh.write(blob)
    return {"file": os.path.relpath(path, os.path.dirname(ART)), "bytes": len(blob),
            "sha1": hashlib.sha1(blob).hexdigest()[:10], "source": url, "kind": kind,
            "fetchedAt": datetime.date.today().isoformat()}


def load_manifest():
    p = os.path.join(ART, "manifest.json")
    if os.path.exists(p):
        return json.load(io.open(p, encoding="utf-8"))
    return {"note": u"客户端原画：暴雪游戏美术，经第三方站转存。整目录删除即可回退到自绘占位图。",
            "items": []}


def save_manifest(man):
    if not os.path.isdir(ART):
        os.makedirs(ART)
    io.open(os.path.join(ART, "manifest.json"), "w", encoding="utf-8").write(
        json.dumps(man, ensure_ascii=False, indent=1) + "\n")


def classes(man):
    code, html = http(WBX + "/")
    if code != 200:
        sys.exit(u"取不到参考站首页（%d）" % code)
    urls = sorted(set(re.findall(r'(/jiemian/custom/classes/([a-z]+)-[0-9a-f]{8,}\.webp)', html)))
    print(u"首页里找到 %d 张职业背景图" % len(urls))
    got = []
    for path, cid in urls:
        url = WBX + path
        code, blob = http(url, binary=True)
        if code == 200 and len(blob) > 2000:
            rec = save(os.path.join(ART, "classes", cid + ".webp"), blob, url, "class-bg")
            man["items"] = [x for x in man["items"] if not x["file"].endswith(cid + ".webp")] + [rec]
            got.append(cid)
        else:
            print(u"  取不到 %s（%d）" % (cid, code))
    print(u"已存职业背景图 %d：%s" % (len(got), u"、".join(got)))


def card_art_map():
    """无限数据库的副本卡片里带载入图路径，键是它的 slug。"""
    p = os.path.join(DATA, "upstream", "wclbox-cards.json")
    if not os.path.exists(p):
        return {}
    doc = json.load(io.open(p, encoding="utf-8"))
    return {c["slug"]: c.get("art") for c in doc.get("cards") or [] if c.get("art")}


def dungeons(man):
    dg = json.load(io.open(os.path.join(DATA, "dungeons.json"), encoding="utf-8"))
    rows = []
    for key in ("newDungeons", "classicDungeons", "raids"):
        rows += dg.get(key) or []
    have = set(x["file"].split("/")[-1].split(".")[0] for x in man["items"] if "/dungeons/" in x["file"])
    arts = card_art_map()
    ok, miss = [], []
    for d in rows:
        slug = SLUG_ALIAS.get(d["id"], d["id"])
        if d["id"] in have:
            continue
        cands = ([WBX + arts[slug]] if slug in arts else []) + [
            WCF + "/images/dungeons/client/%s/loading-screen-640.webp" % slug,
            WCF + "/images/dungeons/client/%s/loading-screen-640.png" % slug]
        for url in cands:
            code, blob = http(url, binary=True)
            if code == 200 and len(blob) > 3000 and blob[:4] != b"<":
                ext = "webp" if blob[8:12] == b"WEBP" else ("png" if blob[:4] == b"\x89PNG" else "jpg")
                rec = save(os.path.join(ART, "dungeons", d["id"] + "." + ext), blob, url, "dungeon-loading")
                man["items"].append(rec)
                ok.append(d["id"])
                break
        else:
            miss.append(d["id"])
    print(u"副本载入图：新增 %d，取不到 %d（继续用自绘横幅）" % (len(ok), len(miss)))
    if miss:
        print(u"  缺：%s" % u"、".join(miss[:20]))


def write_art_index(man):
    """把 manifest 收成界面能直接用的索引：src/data/art.json。
    页面据此决定"有原画就用原画、没有就自绘"，不靠试错加载。"""
    idx = {"classes": {}, "dungeons": {}, "meta": {}}
    for x in man["items"]:
        rel = x["file"] if x["file"].startswith("art/") else "art/" + x["file"]
        name = os.path.splitext(os.path.basename(rel))[0]
        key = "classes" if x["kind"] == "class-bg" else "dungeons"
        idx[key][name] = "img/" + rel
    idx["meta"] = {"fetchedAt": man.get("fetchedAt"), "note": man.get("note"),
                   "count": len(man["items"])}
    io.open(os.path.join(DATA, "art.json"), "w", encoding="utf-8").write(
        json.dumps(idx, ensure_ascii=False, indent=1) + "\n")
    print(u"界面索引 → src/data/art.json（职业 %d / 副本 %d）" % (len(idx["classes"]), len(idx["dungeons"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["classes", "dungeons", "all"], default="all")
    args = ap.parse_args()
    man = load_manifest()
    if args.what in ("classes", "all"):
        classes(man)
    if args.what in ("dungeons", "all"):
        dungeons(man)
    man["fetchedAt"] = datetime.date.today().isoformat()
    man["total"] = len(man["items"])
    save_manifest(man)
    write_art_index(man)
    print(u"manifest 共 %d 条 → src/img/art/manifest.json" % man["total"])


if __name__ == "__main__":
    main()
