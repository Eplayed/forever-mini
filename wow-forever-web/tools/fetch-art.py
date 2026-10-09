#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""转存客户端原画（职业天赋背景图、副本载入图）到 src/img/art/，本地留存、不热链。

红线口径：这些是暴雪游戏美术，目前只有第三方站托管的副本（官方 CDN 不提供）。
2026-10-08 用户决策：网页与小程序都用。执行要求是全部落到独立目录 +
art/manifest.json 记来源与抓取日期 + 保留"整目录删除即回退到自绘占位"的下线方案。

用法：
    python3 tools/fetch-art.py --what classes     # 九职业背景图（从参考站首页现取带哈希的文件名）
    python3 tools/fetch-art.py --what dungeons    # 副本载入图（逐个 slug 试两台源）
    python3 tools/fetch-art.py --what maps        # 区域小地图（只下世界线数据引用到的 mapId）
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


def zone_map_ids():
    """要用的小地图 id：稀有精英/书籍/营地引用的那张，加上区域表里每个区域自己那张。"""
    p = os.path.join(DATA, "upstream", "wclbox-world.json")
    if not os.path.exists(p):
        sys.exit(u"先跑 tools/scrape-wclbox-shuju.py 抓世界线数据包，才知道要下哪些小地图")
    d = json.load(io.open(p, encoding="utf-8")).get("payload") or {}
    out = {}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and v.startswith("/ditu-xiao/"):
                    m = re.search(r"/ditu-xiao/(\d+)\.", v)
                    if m:
                        out[m.group(1)] = v
                else:
                    walk(v)
        elif isinstance(o, list):
            for i in o:
                walk(i)
    walk(d)
    # 区域表里每个区域都有自己那张图，id 写在大陆地图的 paint 上（areaId → 文件名）
    zones = d.get("zones") or {}
    byslug = {m.get("slug"): m for m in d.get("maps") or []}
    for slug, rows in zones.items():
        paint = {x.get("areaId"): x.get("file") for x in (byslug.get(slug) or {}).get("paint") or []
                 if x.get("areaId") is not None and x.get("file")}
        for z in rows or []:
            f = paint.get(z.get("area"))
            if f:
                out[str(f).split(".")[0]] = "/ditu-xiao/%s" % f
    return out


def maps(man):
    """区域小地图：560×373 的客户端地图渲染，托管在第三方站（官方 CDN 不提供这个尺寸）。
    口径与副本载入图一致——只转存我们数据里真引用到的 id，整目录删除即回退到坐标文字。"""
    want = zone_map_ids()
    have = set(os.path.basename(x["file"]).split(".")[0] for x in man["items"] if "/maps/" in x["file"])
    ok, miss = [], []
    for mid, path in sorted(want.items()):
        if mid in have:
            continue
        url = WBX + path
        code, blob = http(url, binary=True)
        if code == 200 and len(blob) > 2000 and blob[:4] == b"RIFF":
            rec = save(os.path.join(ART, "maps", mid + ".webp"), blob, url, "zone-map")
            man["items"] = [x for x in man["items"]
                            if not (x["kind"] == "zone-map" and os.path.basename(x["file"]).split(".")[0] == mid)]
            man["items"].append(rec)
            ok.append(mid)
        else:
            miss.append(mid)
            print(u"  取不到小地图 %s（%d）" % (mid, code))
    print(u"区域小地图：需要 %d 张，本轮新增 %d，取不到 %d" % (len(want), len(ok), len(miss)))


# 参考站种族页的文件名 → 我们的种族 id。只有两处对不上（nightelf / skyborne），其余同名；
# 天裔两个子族共用这一张头像，与参考站一致，不另找图凑。
RACE_FILE = {"human": "human", "dwarf": "dwarf", "nightelf": "night-elf", "gnome": "gnome",
             "orc": "orc", "undead": "undead", "tauren": "tauren", "troll": "troll",
             "skyborne": "skyborne"}


def races(man):
    """种族头像与阵营徽标：128×128 的客户端头像，官方 CDN 不提供，只能转存第三方副本。

    口径与职业背景图、副本载入图完全一致：落独立目录 + manifest 记来源与抓取日期 +
    整目录删除即回退到自绘方块。文件名里的哈希（天裔那张）会变，所以每次都从种族页现读。
    """
    code, html = http(WBX + "/zhongzu")
    if code != 200:
        sys.exit(u"取不到参考站种族页（%d）" % code)
    found = sorted(set(re.findall(r'(/jiemian/(?:reference-art|custom)/(?:raceicon|faction)-[\w.-]+\.(?:webp|png))', html)))
    print(u"种族页里找到 %d 张头像/徽标" % len(found))
    ok, miss = [], []
    for path in found:
        name = os.path.basename(path)
        m = re.match(r"raceicon-([a-z]+)(?:-[0-9a-f]{6,})?\.(webp|png)$", name)
        f = re.match(r"faction-([a-z]+)\.(png|webp)$", name)
        if m:
            key = RACE_FILE.get(m.group(1))
            if not key:
                miss.append(name + u"（对不上我们的种族 id）")
                continue
            kind, dest, ext = "race-portrait", os.path.join(ART, "races", key + "." + m.group(2)), m.group(2)
        elif f:
            kind, dest, ext = "faction-emblem", os.path.join(ART, "factions", f.group(1) + "." + f.group(2)), f.group(2)
        else:
            continue
        code, blob = http(WBX + path, binary=True)
        if code != 200 or len(blob) < 800:
            miss.append(name)
            continue
        rec = save(dest, blob, WBX + path, kind)
        man["items"] = [x for x in man["items"] if x["file"] != rec["file"]] + [rec]
        ok.append(rec["file"])
    print(u"种族头像/徽标：新增或更新 %d，取不到 %d" % (len(ok), len(miss)))
    if miss:
        print(u"  缺：%s" % u"、".join(miss[:10]))


# 阵营城市背景：参考站按拼音命名（lianmeng=联盟=暴风城英雄谷，buluo=部落=奥格瑞玛正门），
# 两张都人眼确认过画的是什么，不是靠文件名猜。落到我们自己的语义名，来源记进 manifest。
CITY_FILE = {"lianmeng": ("alliance", u"暴风城英雄谷"), "buluo": ("horde", u"奥格瑞玛正门")}


def factions(man):
    """阵营城市背景原画：种族页两条阵营带要用它做底，压暗后当氛围图。

    口径与职业背景图一致：第三方站托管的客户端原画副本，落独立目录 + manifest 记来源与抓取日期，
    整目录删掉即回退到现在的纯色带。取不到就跳过，不放别的图凑数。
    """
    ok, miss = [], []
    for src, (key, what) in CITY_FILE.items():
        url = WBX + "/peitu/changjing/" + src + ".webp"
        code, blob = http(url, binary=True)
        if code != 200 or len(blob) < 8000:
            miss.append(src + u"（HTTP %s）" % code)
            continue
        dest = os.path.join(ART, "factions", "city-" + key + ".webp")
        rec = save(dest, blob, url, "faction-city")
        rec["what"] = what
        man["items"] = [x for x in man["items"] if x["file"] != rec["file"]] + [rec]
        ok.append(u"%s → %s（%s，%d KB）" % (src, rec["file"], what, len(blob) // 1024))
    print(u"阵营城市背景：新增或更新 %d，取不到 %d" % (len(ok), len(miss)))
    for x in ok:
        print(u"  " + x)
    if miss:
        print(u"  缺：%s" % u"、".join(miss))


def write_art_index(man):
    """把 manifest 收成界面能直接用的索引：src/data/art.json。
    页面据此决定"有原画就用原画、没有就自绘"，不靠试错加载。"""
    idx = {"classes": {}, "dungeons": {}, "maps": {}, "races": {}, "factions": {},
           "factionCities": {}, "meta": {}}
    for x in man["items"]:
        rel = x["file"] if x["file"].startswith("art/") else "art/" + x["file"]
        name = os.path.splitext(os.path.basename(rel))[0]
        if x["kind"] == "class-bg":
            idx["classes"][name] = "img/" + rel
        elif x["kind"] == "zone-map":
            idx["maps"][name] = "img/" + rel
        elif x["kind"] == "race-portrait":
            idx["races"][name] = "img/" + rel
        elif x["kind"] == "faction-emblem":
            idx["factions"][name] = "img/" + rel
        elif x["kind"] == "faction-city":
            idx["factionCities"][name.replace("city-", "")] = "img/" + rel
        else:
            idx["dungeons"][name] = "img/" + rel
    idx["meta"] = {"fetchedAt": man.get("fetchedAt"), "note": man.get("note"),
                   "count": len(man["items"])}
    io.open(os.path.join(DATA, "art.json"), "w", encoding="utf-8").write(
        json.dumps(idx, ensure_ascii=False, indent=1) + "\n")
    print(u"界面索引 → src/data/art.json（职业 %d / 副本 %d / 小地图 %d / 种族头像 %d / "
          u"阵营徽标 %d / 阵营城市 %d）" % (
              len(idx["classes"]), len(idx["dungeons"]), len(idx["maps"]), len(idx["races"]),
              len(idx["factions"]), len(idx["factionCities"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["classes", "dungeons", "maps", "races", "factions", "all"],
                    default="all")
    args = ap.parse_args()
    man = load_manifest()
    if args.what in ("classes", "all"):
        classes(man)
    if args.what in ("dungeons", "all"):
        dungeons(man)
    if args.what in ("maps", "all"):
        maps(man)
    if args.what in ("races", "all"):
        races(man)
    if args.what in ("factions", "all"):
        factions(man)
    man["fetchedAt"] = datetime.date.today().isoformat()
    man["total"] = len(man["items"])
    save_manifest(man)
    write_art_index(man)
    print(u"manifest 共 %d 条 → src/img/art/manifest.json" % man["total"])


if __name__ == "__main__":
    main()
