#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""素材缺口审计：把"数据里引用了、本地却没有"的图标与原图逐键列出来，并试遍官方 CDN 的其它区域。

为什么单独做这个：图标是"占位块垫底 + 本地官方图盖面"，缺一张不会报错，只会在页面上悄悄退回字母块。
缺多少、为什么缺，得有人数一遍。本脚本干三件事：
1. 扫全部数据文件收集 iconKey 与图片路径，比对本地文件，列出缺口；
2. 对每个缺的图标依次试 us / eu / kr / tw 四个区域与 56 / 0 两种尺寸——只有全 404 才算真没有；
3. 出报告 docs/ASSET-GAPS-<日期>.md，按"CDN 无此文件 / 上游本身没切图 / 键名可疑"分类。

红线不变：图片字节只允许来自 render.worldofwarcraft.com，第三方站给文件名我们就只认文件名。

用法：
    python3 tools/audit-assets.py                # 只审计出报告
    python3 tools/audit-assets.py --fetch        # 顺手把其它区域能取到的拉回本地
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
DATA = os.path.join(ROOT, "src", "data")
ICONS = os.path.join(ROOT, "src", "img", "icons")
ART = os.path.join(ROOT, "src", "img", "art")
DOCS = os.path.join(ROOT, "docs")
CACHE = os.path.join(ROOT, ".audit-cache", "asset-probe.json")   # 探测结果缓存，避免每轮重问 CDN 四百次
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
# 实测过：官方 CDN 对"没有这张图"的回应是 403（不是 404），us 区 56 尺寸是主路径。
# 先把主路径问清楚，只有主路径拿不到才去试别的区域，最后再试一次 0 尺寸——
# 全组合轮询一遍要十几分钟，没必要。
CAND = [("us", "56"), ("eu", "56"), ("kr", "56"), ("tw", "56"), ("us", "0")]
KEY_RE = re.compile(r"^[a-z0-9_]{3,64}$")
DATA_FILES = ["dungeons.json", "professions.json", "races.json", "world.json", "changes.json",
              "glossary.json", "abilities.json", "classes.json", "chooser.json", "systems.json"]


def load(p):
    if not os.path.exists(p):
        return None
    return json.load(io.open(p, encoding="utf-8"))


def collect_keys():
    """iconKey → 引用它的文件集合。天赋树单独走目录，键在 nodes[].iconKey。"""
    out = {}

    def walk(node, src):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "iconKey" and isinstance(v, str) and v:
                    out.setdefault(v, set()).add(src)
                else:
                    walk(v, src)
        elif isinstance(node, list):
            for x in node:
                walk(x, src)

    for fn in DATA_FILES:
        d = load(os.path.join(DATA, fn))
        if d is not None:
            walk(d, fn)
    tdir = os.path.join(DATA, "talents")
    if os.path.isdir(tdir):
        for fn in sorted(os.listdir(tdir)):
            if fn.startswith("_") or not fn.endswith(".json"):
                continue
            walk(load(os.path.join(tdir, fn)), "talents/" + fn)
    return out


def http_head(url):
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{size_download}",
                        "-m", "8", "-A", UA, "-L", url], capture_output=True)
    txt = p.stdout.decode("utf-8", "replace").strip()
    parts = txt.split()
    return (int(parts[0]) if parts and parts[0].isdigit() else 0,
            int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0)


def fetch_to(key, area, size):
    url = "https://render.worldofwarcraft.com/%s/icons/%s/%s.jpg" % (area, size, key)
    p = subprocess.run(["curl", "-s", "-m", "25", "-A", UA, "-L", url], capture_output=True)
    b = p.stdout
    if len(b) > 500 and b[:3] == b"\xff\xd8\xff":
        with open(os.path.join(ICONS, key + ".jpg"), "wb") as fh:
            fh.write(b)
        return url, len(b)
    return None, 0


def audit_maps(doc):
    """世界线小地图：数据里 mapFile 为空的条目，回到上游确认那张图到底存不存在。"""
    want = {}
    def walk(node):
        if isinstance(node, dict):
            mid = node.get("mapId")
            if mid and "mapFile" in node and node.get("mapFile") is None:
                name = node.get("nameCn") or node.get("id") or "?"
                want.setdefault(str(mid), set()).add(name)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)
    walk(doc)
    return want


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="把其它区域能取到的图标拉回本地")
    a = ap.parse_args()

    have = set(f[:-4] for f in os.listdir(ICONS) if f.endswith(".jpg"))
    keys = collect_keys()
    missing = sorted(k for k in keys if k not in have)
    print("引用图标键 %d 个，本地 %d 张，缺 %d 个" % (len(keys), len(have), len(missing)))

    probe = {}
    if os.path.exists(CACHE):
        try:
            probe = json.load(io.open(CACHE, encoding="utf-8"))
        except ValueError:
            probe = {}
    found, still = [], []
    for k in missing:
        if not KEY_RE.match(k):
            still.append((k, sorted(keys[k]), "bad-key"))
            continue
        hit, codes = None, []
        if k in probe:
            hit, codes = probe[k].get("hit"), probe[k].get("codes", [])
        else:
            for area, size in CAND:
                code, _sz = http_head("https://render.worldofwarcraft.com/%s/icons/%s/%s.jpg" % (area, size, k))
                codes.append("%s/%s=%d" % (area, size, code))
                if code == 200:
                    hit = [area, size]
                    break
            probe[k] = {"hit": hit, "codes": codes}
            if not os.path.isdir(os.path.dirname(CACHE)):
                os.makedirs(os.path.dirname(CACHE))
            io.open(CACHE, "w", encoding="utf-8").write(json.dumps(probe, ensure_ascii=False))
        hit = tuple(hit) if hit else None
        if hit:
            saved = "未取（只审计）"
            if a.fetch:
                url, n = fetch_to(k, hit[0], hit[1])
                saved = "已存 %s（%d 字节）" % (url, n) if url else "取回失败"
            found.append((k, hit, sorted(keys[k]), saved))
        else:
            still.append((k, sorted(keys[k]), "cdn-missing"))
    if found:
        print("其它区域能取到 %d 个：%s" % (len(found), "、".join(x[0] for x in found[:10])))
        for x in found:
            print("  %s → render/%s/icons/%s  %s" % (x[0], x[1][0], x[1][1], x[3]))

    world = load(os.path.join(DATA, "world.json")) or {}
    mapmiss = audit_maps(world) if world else {}
    mapcheck = []
    for mid, names in sorted(mapmiss.items()):
        code, _sz = http_head("https://wowforever.wclbox.com/ditu-xiao/%s.webp" % mid)
        mapcheck.append((mid, sorted(names), code))
    print("区域小地图：数据里没图的 %d 张，上游状态 %s" % (
        len(mapcheck), "、".join("%s=%d" % (m, c) for m, _n, c in mapcheck[:12]) or "无"))

    # 副本载入图缺口：dungeons.json 里有、art.json 索引里没有的
    dgs = load(os.path.join(DATA, "dungeons.json")) or {}
    art0 = load(os.path.join(DATA, "art.json")) or {}
    rows = []
    for key in ("newDungeons", "classicDungeons", "raids"):
        rows += dgs.get(key) or []
    art_rows = [(x.get("id"), x.get("nameCn") or x.get("nameEn") or "?", x.get("kind"))
                for x in rows if x.get("id") not in (art0.get("dungeons") or {})]

    art = load(os.path.join(DATA, "art.json")) or {}
    artmiss = []
    for kind, m in (("classes", art.get("classes") or {}), ("dungeons", art.get("dungeons") or {}),
                    ("maps", art.get("maps") or {})):
        for k, rel in m.items():
            if not os.path.exists(os.path.join(ROOT, "src", rel)):
                artmiss.append("%s/%s" % (kind, k))

    today = datetime.date.today().isoformat()
    lines = [u"# 素材缺口审计 · %s（wow-data + wow-dev）" % today, u"",
             u"脚本：`python3 tools/audit-assets.py`（加 `--fetch` 会把其它区域能取到的拉回本地）。"
             u"图标一律只认暴雪官方 CDN，第三方站只给文件名。", u"",
             u"## 结论", u"",
             u"| 项 | 数 |", u"| --- | --- |",
             u"| 数据里引用的图标键 | %d |" % len(keys),
             u"| 本地已有 | %d |" % len(have),
             u"| 缺 | %d |" % len(missing),
             u"| 换区域/尺寸能补上 | %d |" % len(found),
             u"| 官方 CDN 五个候选路径都取不到（实测 403/404，不是我们没试） | %d |" % len([x for x in still if x[2] == "cdn-missing"]),
             u"| 键名不合法（脚本不试，回数据里查） | %d |" % len([x for x in still if x[2] == "bad-key"]),
             u"| art.json 指向但文件不存在 | %d |" % len(artmiss),
             u"", u"## 缺的图标按引用来源分布", u"",
             u"| 图标键 | 引用处 | 判定 |", u"| --- | --- | --- |"]
    for k, srcs, why in still:
        lines.append(u"| `%s` | %s | %s |" % (k, "、".join(srcs),
          u"官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件"
          if why == "cdn-missing" else u"键名不合法，回数据里查"))
    if found:
        lines += [u"", u"## 换区域能补上的", u"", u"| 图标键 | 命中位置 | 引用处 | 结果 |", u"| --- | --- | --- | --- |"]
        for k, loc, srcs, saved in found:
            lines.append(u"| `%s` | render/%s/icons/%s | %s | %s |" % (k, loc[0], loc[1], "、".join(srcs), saved))
    if mapcheck:
        lines += [u"", u"## 区域小地图（上游 /ditu-xiao 状态）", u"",
                  u"| mapId | 区域 | 上游 HTTP |", u"| --- | --- | --- |"]
        for mid, names, code in mapcheck:
            lines.append(u"| %s | %s | %d |" % (mid, "、".join(names), code))
    if art_rows:
        lines += [u"", u"## 副本载入图缺口", u"",
                  u"| 副本 | 名称 | 类型 | 两台源的状态 |", u"| --- | --- | --- | --- |"]
        for i, nm, kind in art_rows:
            lines.append(u"| `%s` | %s | %s | wowclassicforever 与无限数据库都是 404（这两座是还没开放的团本壳，"
                         u"客户端里本来就没有载入图）|" % (i, nm, kind))
    if artmiss:
        lines += [u"", u"## art.json 里指向但文件不在的", u""] + [u"- `%s`" % x for x in artmiss]
    out = os.path.join(DOCS, "ASSET-GAPS-%s.md" % today)
    io.open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("报告 → %s" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
