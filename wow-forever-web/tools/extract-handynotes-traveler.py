#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 HandyNotes_Traveler 提取无限服船舶、飞艇、飞空艇、矿道地铁与传送门交通点位。
仅取事实字段（uiMapID、坐标、类型、阵营、区域ID、目的地、Forever 新增标记、Wowhead object ID 与 zhCN 译名），
不抄写 note 位置描述句。"""
import argparse
import datetime
import os
import sys

from addons_root import resolve, explain
from lua_lit import UPSTREAM, assert_no_percent, file_stamp, parse_assignment, toc_version, write_snapshot

ADDON = "HandyNotes_Traveler"
DATA_REL = ADDON + "/Data.lua"
ZH_REL = ADDON + "/zhCN.lua"


def resolve_src(given):
    for c in (given, os.environ.get("WOW_ADDONS")):
        if c and os.path.isfile(os.path.join(c, DATA_REL)):
            return c
    root = resolve(ADDON)
    if os.path.isfile(os.path.join(root, DATA_REL)):
        return root
    sys.exit("找不到 %s：%s\n%s" % (ADDON, DATA_REL, explain()))


def decode_coord(packed):
    x = round((packed // 10000) / 100.0, 2)
    y = round((packed % 10000) / 100.0, 2)
    return x, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out-dir", default=UPSTREAM)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    src = resolve_src(args.src)
    data_path = os.path.join(src, DATA_REL)
    zh_path = os.path.join(src, ZH_REL)
    data_text = open(data_path, encoding="utf-8").read()
    zh_text = open(zh_path, encoding="utf-8").read()

    points_raw = parse_assignment(data_text, r"ns\.points\s*=\s*\{")
    zh_ui = parse_assignment(zh_text, r"ns\.zhCN\s*=\s*\{")
    places_cn = parse_assignment(zh_text, r"ns\.placeNames\s*=\s*\{")

    routes = []
    for map_id, coords_map in sorted(points_raw.items()):
        for packed, pt in sorted(coords_map.items()):
            x, y = decode_coord(int(packed))
            name_en = pt.get("name", "")
            dests = []
            for d in pt.get("to") or []:
                den = d.get("name", "")
                dests.append({
                    "areaId": int(d["area"]) if d.get("area") else None,
                    "uiMapId": int(d["map"]) if d.get("map") else None,
                    "nameEn": den,
                    "nameCn": places_cn.get(den, den),
                })
            rec = {
                "uiMapId": int(map_id),
                "x": x,
                "y": y,
                "kind": pt.get("kind", ""),
                "kindCn": (zh_ui.get("KIND") or {}).get(pt.get("kind", ""), ""),
                "side": pt.get("side", "N"),
                "areaId": int(pt["area"]) if pt.get("area") else None,
                "nameEn": name_en,
                "nameCn": places_cn.get(name_en, name_en),
                "to": dests,
                "isNewForever": bool(pt.get("new", False)),
            }
            if pt.get("next"):
                nx = pt["next"]
                rec["next"] = {
                    "areaId": int(nx["area"]) if nx.get("area") else None,
                    "uiMapId": int(nx["map"]) if nx.get("map") else None,
                    "nameEn": nx.get("name", ""),
                    "nameCn": places_cn.get(nx.get("name", ""), nx.get("name", "")),
                }
            for flag in ("tower", "ferry", "skyborne"):
                if pt.get(flag):
                    rec[flag] = True
            if pt.get("object"):
                rec["objectId"] = int(pt["object"])
            routes.append(rec)

    ver = toc_version(src, ADDON)
    by_kind = {}
    for r in routes:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1

    doc = {
        "meta": {
            "source": "%s %s Data.lua + zhCN.lua" % (ADDON, ver),
            "addon": ADDON,
            "addonVersion": ver,
            "fetched": datetime.date.today().isoformat(),
            "levelStatus": "L1",
            "droppedFields": ["pt.note 位置说明句（避免复制第三方描述文本）"],
            "sourceFiles": {DATA_REL: file_stamp(data_path), ZH_REL: file_stamp(zh_path)},
            "counts": {
                "maps": len(points_raw),
                "points": len(routes),
                "newInForever": sum(1 for r in routes if r["isNewForever"]),
                "byKind": by_kind,
            },
        },
        "points": routes,
    }
    assert_no_percent(doc, "handynotes-traveler")
    print("HandyNotes_Traveler：%d 张地图 / %d 个交通点（无限服新增 %d 个）" % (
        doc["meta"]["counts"]["maps"], len(routes), doc["meta"]["counts"]["newInForever"]))
    if args.show:
        return
    out = write_snapshot(args.out_dir, "handynotes-traveler.json", doc)
    print("写 %s（%.1f KB）" % (out, os.path.getsize(out) / 1024.0))


if __name__ == "__main__":
    main()
