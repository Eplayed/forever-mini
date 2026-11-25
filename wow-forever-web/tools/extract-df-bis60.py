#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 DungeonsForeverGear 提取 60 级团前（ns.BisPre）、预设方案（Data_BisPreset）、
部位顺位（Data_BisRank）与安德麦货币商人（Data_GearVendorGoods + Data_GearVendors）。
仅取事实标识符与名单（L1，未实测），不抄写第三方解说或属性句，无百分比。"""
import argparse
import datetime
import os
import sys

from addons_root import resolve, explain
from lua_lit import UPSTREAM, assert_no_percent, file_stamp, parse_assignment, toc_version, write_snapshot

ADDON = "DungeonsForeverGear"
FILES = {
    "bis": "DungeonsForeverGear/Core/Data/Data_BIS.lua",
    "preset": "DungeonsForeverGear/Core/Data/Data_BisPreset.lua",
    "rank": "DungeonsForeverGear/Core/Data/Data_BisRank.lua",
    "vendorGoods": "DungeonsForeverGear/Core/Data/Data_GearVendorGoods.lua",
    "vendors": "DungeonsForeverGear/Core/Data/Data_GearVendors.lua",
}


def resolve_src(given):
    for c in (given, os.environ.get("WOW_ADDONS")):
        if c and os.path.isfile(os.path.join(c, FILES["bis"])):
            return c
    root = resolve(ADDON)
    if os.path.isfile(os.path.join(root, FILES["bis"])):
        return root
    sys.exit("找不到 %s：%s\n%s" % (ADDON, FILES["bis"], explain()))


def clean_pick(row):
    item_id, src_type = int(row[0]), row[1]
    out = {
        "itemId": item_id,
        "srcType": src_type,
        "place": row[2] or "",
        "detail": row[3] or "",
        "ilvl": int(row[4]),
        "quality": int(row[5]),
    }
    if len(row) > 6 and isinstance(row[6], list) and row[6]:
        q = row[6]
        out["quest"] = {
            "id": int(q[0]),
            "name": q[1],
            "level": int(q[2]) if q[2] else None,
            "tag": q[3] or "",
            "fromNpc": q[4] or "",
            "fromZone": q[5] or "",
            "fromCoord": q[6] or "",
            "toNpc": q[7] or "",
            "toZone": q[8] or "",
            "toCoord": q[9] or "",
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out-dir", default=UPSTREAM)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    src = resolve_src(args.src)
    paths = {k: os.path.join(src, rel) for k, rel in FILES.items()}
    texts = {k: open(p, encoding="utf-8").read() for k, p in paths.items()}

    bis_pre = parse_assignment(texts["bis"], r"ns\.BisPre\s*=\s*\{")
    presets_raw = parse_assignment(texts["preset"], r"ns\.BisPreset\s*=\s*\{")
    ranks_raw = parse_assignment(texts["rank"], r"ns\.BisRank\s*=\s*\{")
    goods_raw = parse_assignment(texts["vendorGoods"], r"ns\.GearVendorGoods\s*=\s*\{")
    vendors_raw = parse_assignment(texts["vendors"], r"ns\.GearVendors\s*=\s*\{")

    specs = []
    item_ids = set()
    for cls in bis_pre.get("classes") or []:
        slug = cls["slug"]
        for sp in cls.get("specs") or []:
            slots = {}
            for slot, rows in (sp.get("slots") or {}).items():
                cleaned = [clean_pick(r) for r in rows]
                slots[slot] = cleaned
                item_ids.update(x["itemId"] for x in cleaned)
            specs.append({
                "class": slug,
                "spec": sp["key"],
                "label": sp["label"],
                "role": sp.get("role", ""),
                "style": sp.get("style", ""),
                "slots": slots,
            })

    presets = []
    for cls in presets_raw:
        for sp in cls.get("specs") or []:
            for pr in sp.get("presets") or []:
                items = {slot: [int(x) for x in vals] for slot, vals in (pr.get("items") or {}).items()}
                for vals in items.values():
                    item_ids.update(vals)
                presets.append({
                    "class": cls["slug"],
                    "spec": sp["key"],
                    "label": sp["label"],
                    "presetId": pr["id"],
                    "tab": pr.get("tab") or pr.get("label") or pr["id"],
                    "level": int(pr.get("level", 60)),
                    "items": items,
                    "incomplete": bool(pr.get("incomplete", False)),
                })

    ranks = {}
    for cls_slug, cls_specs in (ranks_raw or {}).items():
        if not isinstance(cls_specs, dict) or not cls_specs:
            continue
        ranks[cls_slug] = {}
        for spec_key, slot_map in cls_specs.items():
            if not isinstance(slot_map, dict) or not slot_map:
                continue
            ranks[cls_slug][spec_key] = {}
            for slot, entries in slot_map.items():
                ranks[cls_slug][spec_key][slot] = [
                    {"itemId": int(e[0]), "rank": int(e[1])} for e in entries
                ]
                item_ids.update(int(e[0]) for e in entries)

    vendors = []
    for npc_id, v in goods_raw.items():
        locs = [
            {"zoneId": int(loc[0]), "uiMapId": int(loc[1]), "x": float(loc[2]), "y": float(loc[3])}
            for loc in vendors_raw.get(npc_id, [])
        ]
        groups = []
        for g in v.get("groups") or []:
            rows = []
            for entry in g[2]:
                iid, cost = int(entry[0]), entry[1]
                item_ids.add(iid)
                if isinstance(cost, list):
                    item_ids.add(int(cost[0]))
                    rows.append({"itemId": iid, "costItem": {"itemId": int(cost[0]), "count": int(cost[1])}})
                else:
                    rows.append({"itemId": iid, "costCurrency": int(cost)})
            groups.append({"key": g[0], "label": g[1], "items": rows})
        cur = v.get("cur") or []
        vendors.append({
            "npcId": int(npc_id),
            "name": v["name"],
            "tag": v.get("tag", ""),
            "zoneId": int(v["zone"]) if v.get("zone") else None,
            "currency": {"id": int(cur[0]), "name": cur[1]} if len(cur) >= 2 else None,
            "locations": locs,
            "groups": groups,
        })

    ver = toc_version(src, ADDON)
    doc = {
        "meta": {
            "source": "%s %s Core/Data/{Data_BIS(ns.BisPre),Data_BisPreset,Data_BisRank,Data_GearVendorGoods,Data_GearVendors}.lua" % (ADDON, ver),
            "addon": ADDON,
            "addonVersion": ver,
            "level": int(bis_pre.get("level", 60)),
            "addonUpdated": bis_pre.get("updated", ""),
            "fetched": datetime.date.today().isoformat(),
            "levelStatus": "L1",
            "boundary": "DF LICENSE 保留所有权利；仅取 60 级团前事实标识符（职业/专精/部位/物品ID/顺位/来源类型/任务ID/商人货币价），不抄写解说正文，未进游戏实测，整体 L1。",
            "sourceFiles": {rel: file_stamp(os.path.join(src, rel)) for rel in FILES.values()},
            "counts": {
                "specs": len(specs),
                "presets": len(presets),
                "rankSpecs": sum(len(v) for v in ranks.values()),
                "vendors": len(vendors),
                "distinctItems": len(item_ids),
            },
        },
        "specs": specs,
        "presets": presets,
        "ranks": ranks,
        "vendors": vendors,
    }
    assert_no_percent(doc, "df-bis60")
    print("DF 60团前：%d 专精 / %d 预设 / %d 顺位表 / %d 商人 / %d 去重物品" % (
        len(specs), len(presets), doc["meta"]["counts"]["rankSpecs"], len(vendors), len(item_ids)))
    if args.show:
        return
    out = write_snapshot(args.out_dir, "df-bis60.json", doc)
    print("写 %s（%.1f KB）" % (out, os.path.getsize(out) / 1024.0))


if __name__ == "__main__":
    main()
