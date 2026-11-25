#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 HandyNotes_NPCs (Classic) 的 Forever 分支提取无限服新增及重标地图的 NPC 点位
（2482 海加尔山、2548 河林、1423 东瘟疫之地、1453 暴风城，通过与 classic/data.lua 逐地图对比得出）。
仅取事实字段（uiMapID、坐标、npcID、category、faction、profession、fpName、中英文名），丢弃 description 文本。"""
import argparse
import datetime
import os
import re
import sys

from addons_root import resolve, explain
from lua_lit import UPSTREAM, LuaParser, assert_no_percent, file_stamp, toc_version, write_snapshot

ADDON = "HandyNotes_NPCs (Classic)"
FOREVER_REL = ADDON + "/forever/data.lua"
CLASSIC_REL = ADDON + "/classic/data.lua"
ZH_REL = ADDON + "/locales/forever/zhCN.lua"


def resolve_src(given):
    for c in (given, os.environ.get("WOW_ADDONS")):
        if c and os.path.isfile(os.path.join(c, FOREVER_REL)):
            return c
    root = resolve(ADDON)
    if os.path.isfile(os.path.join(root, FOREVER_REL)):
        return root
    sys.exit("找不到 %s：%s\n%s" % (ADDON, FOREVER_REL, explain()))


def load_zh_locale(path):
    text = open(path, encoding="utf-8").read()
    loc = {}
    for m in re.finditer(r'L\["((?:[^"\\]|\\.)*)"\]\s*=\s*"((?:[^"\\]|\\.)*)"', text):
        loc[m.group(1)] = m.group(2)
    return loc


def split_map_blocks(text):
    """Return {map_id_str: raw_block_slice_start_end} for each nodes[mapId] = { ... }."""
    blocks = {}
    for m in re.finditer(r"(?m)^nodes\[(\d+)\]\s*=\s*\{", text):
        mid = m.group(1)
        idx = text.index("{", m.start())
        blocks[mid] = idx
    return blocks


def parse_map_nodes(text, idx, loc_en, loc_cn):
    raw_en = LuaParser(text, idx, locale=loc_en).parse_table()
    raw_cn = LuaParser(text, idx, locale=loc_cn).parse_table()
    pins = []
    for packed in sorted(raw_en.keys()):
        en = raw_en[packed]
        cn = raw_cn[packed]
        p = int(packed)
        rec = {
            "x": round((p // 10000) / 100.0, 2),
            "y": round((p % 10000) / 100.0, 2),
            "npcId": int(en["npcID"]) if en.get("npcID") else None,
            "category": en.get("category", ""),
            "faction": en.get("faction", ""),
            "nameEn": en.get("name", ""),
            "nameCn": cn.get("name", ""),
        }
        if en.get("profession"):
            rec["profession"] = en["profession"]
        if en.get("fpName"):
            rec["fpNameEn"] = en["fpName"]
            rec["fpNameCn"] = cn.get("fpName", en["fpName"])
        pins.append(rec)
    return pins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out-dir", default=UPSTREAM)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    src = resolve_src(args.src)
    f_path = os.path.join(src, FOREVER_REL)
    c_path = os.path.join(src, CLASSIC_REL)
    z_path = os.path.join(src, ZH_REL)

    f_text = open(f_path, encoding="utf-8").read()
    c_text = open(c_path, encoding="utf-8").read()
    loc_cn = load_zh_locale(z_path)
    loc_en = {}

    f_idx = split_map_blocks(f_text)
    c_idx = split_map_blocks(c_text)

    # Identify maps only in Forever or whose parsed table differs from classic
    maps_out = []
    for mid in sorted(f_idx.keys(), key=int):
        f_pins = parse_map_nodes(f_text, f_idx[mid], loc_en, loc_cn)
        is_new_map = mid not in c_idx
        if not is_new_map:
            c_pins = parse_map_nodes(c_text, c_idx[mid], loc_en, loc_cn)
            if f_pins == c_pins:
                continue
        maps_out.append({
            "uiMapId": int(mid),
            "isNewMapInForever": is_new_map,
            "pinCount": len(f_pins),
            "pins": f_pins,
        })

    ver = toc_version(src, ADDON, "HandyNotes_NPCs (Classic)-forever.toc")
    doc = {
        "meta": {
            "source": "%s %s forever/data.lua + locales/forever/zhCN.lua" % (ADDON, ver),
            "addon": ADDON,
            "addonVersion": ver,
            "fetched": datetime.date.today().isoformat(),
            "levelStatus": "L1",
            "droppedFields": ["description 短说明文本（仅保留 category / profession / fpName / npcID / 坐标 / 中英文名）"],
            "sourceFiles": {
                FOREVER_REL: file_stamp(f_path),
                CLASSIC_REL: file_stamp(c_path),
                ZH_REL: file_stamp(z_path),
            },
            "counts": {
                "changedOrNewMaps": len(maps_out),
                "newMaps": sum(1 for m in maps_out if m["isNewMapInForever"]),
                "recalibratedMaps": sum(1 for m in maps_out if not m["isNewMapInForever"]),
                "totalPins": sum(m["pinCount"] for m in maps_out),
                "newMapPins": sum(m["pinCount"] for m in maps_out if m["isNewMapInForever"]),
            },
        },
        "maps": maps_out,
    }
    assert_no_percent(doc, "handynotes-npcs-forever")
    c = doc["meta"]["counts"]
    print("HandyNotes_NPCs Forever：%d 张差异/新增地图（新增 %d / 重标 %d），共 %d 个点位（新增地图 %d 个）" % (
        c["changedOrNewMaps"], c["newMaps"], c["recalibratedMaps"], c["totalPins"], c["newMapPins"]))
    if args.show:
        return
    out = write_snapshot(args.out_dir, "handynotes-npcs-forever.json", doc)
    print("写 %s（%.1f KB）" % (out, os.path.getsize(out) / 1024.0))


if __name__ == "__main__":
    main()
