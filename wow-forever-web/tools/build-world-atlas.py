#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Web 端「无限地图」（仿 OpenMap 单张完整无缝大地图）所需的静态数据层：
  1. app/data/map-npcs.json     — 从 HandyNotes_NPCs (Classic) forever 分支抽取城镇 NPC（仅事实字段，不抄描述文案）
  2. app/data/world-atlas.json  — 基于客户端 UiMapAssignment.db2 精确投影的 2004×1336 单张无缝世界大地图布局：
                                   世界底图 947 + 两大陆 1414/1415 + 46 张区域高清层精确坐标 + 37 副本/团本入口 + 10 航线
  3. app/data/legacy-books.json — 「传承书籍」独立扩展真源（保留已有条目，缺数诚实留空不编造）

遵循根 AGENTS.md 红线：
  - 不复制 OpenMap Media/ 任何贴图；
  - 947/1414/1415 底图源自本机 Forever 客户端只读导出并登记至 app/img/art/manifest.json；
  - 不复制第三方插件的描述文案；
  - 全部 NPC 与航线按 L1 留档并登记来源与核对日期。
"""
import datetime
import hashlib
import json
import math
import os
import re
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.dirname(TOOLS_DIR)
DATA_DIR = os.path.join(WEB_ROOT, "app", "data")
UPSTREAM_DIR = os.path.join(DATA_DIR, "upstream")
MAPS_IMG_DIR = os.path.join(WEB_ROOT, "app", "img", "art", "maps")
ART_MANIFEST = os.path.join(WEB_ROOT, "app", "img", "art", "manifest.json")
sys.path.insert(0, TOOLS_DIR)

import addons_root  # noqa: E402

TODAY = datetime.date.today().isoformat()

# 单张完整艾泽拉斯大地图逻辑画布（2× 1002×668，标准 3:2 比例）
CANVAS_W = 2004
CANVAS_H = 1336

CITY_EXTRAS = {
    "1453": {"id": "stormwind", "nameCn": "暴风城", "continent": "ek", "continentCn": "东部王国", "faction": "联盟", "isCity": True, "isNew": False},
    "1455": {"id": "ironforge", "nameCn": "铁炉堡", "continent": "ek", "continentCn": "东部王国", "faction": "联盟", "isCity": True, "isNew": False},
}

ROUTES = [
    {"id": "r-bb-ratchet", "kind": "boat", "faction": "N", "name": "藏宝海湾 ⇄ 棘齿城",
     "from": ("1434", 26.0, 73.0), "to": ("1413", 63.6, 38.6)},
    {"id": "r-menethil-theramore", "kind": "boat", "faction": "A", "name": "米奈希尔港 ⇄ 塞拉摩",
     "from": ("1437", 5.0, 63.0), "to": ("1445", 71.0, 56.0)},
    {"id": "r-menethil-auberdine", "kind": "boat", "faction": "A", "name": "米奈希尔港 ⇄ 奥伯丁",
     "from": ("1437", 6.0, 56.0), "to": ("1439", 32.5, 44.0)},
    {"id": "r-sw-auberdine", "kind": "boat", "faction": "A", "name": "暴风城港口 ⇄ 奥伯丁",
     "from": ("1453", 22.0, 55.0), "to": ("1439", 30.5, 41.0)},
    {"id": "r-auberdine-rut", "kind": "boat", "faction": "A", "name": "奥伯丁 ⇄ 鲁瑟兰村",
     "from": ("1439", 33.0, 39.5), "to": ("1438", 54.8, 94.0)},
    {"id": "r-org-uc", "kind": "zeppelin", "faction": "H", "name": "奥格瑞玛 ⇄ 幽暗城",
     "from": ("1411", 50.8, 13.8), "to": ("1420", 60.8, 58.8)},
    {"id": "r-org-gg", "kind": "zeppelin", "faction": "H", "name": "奥格瑞玛 ⇄ 格罗姆高",
     "from": ("1411", 50.6, 12.6), "to": ("1434", 31.4, 29.6)},
    {"id": "r-uc-gg", "kind": "zeppelin", "faction": "H", "name": "幽暗城 ⇄ 格罗姆高",
     "from": ("1420", 61.8, 59.0), "to": ("1434", 31.8, 30.2)},
    {"id": "r-air-alterac-zephras", "kind": "airship", "faction": "N", "name": "奥特兰克空艇 ⇄ 泽风岛",
     "from": ("1416", 62.0, 44.0), "to": ("2521", 52.0, 34.0)},
    {"id": "r-air-mulgore-zephras", "kind": "airship", "faction": "N", "name": "莫高雷空艇 ⇄ 泽风岛",
     "from": ("1412", 42.0, 26.0), "to": ("2521", 46.0, 62.0)},
]

NPC_CAT_MAP = {
    "flightmasters": "flight",
    "innkeepers": "innkeeper",
    "repair": "repair",
    "vendors": "vendor",
    "bankers": "banker",
    "auctioneers": "auctioneer",
    "mailboxes": "mailbox",
    "trainers": "classTrainer",
    "primaryProfession": "profTrainer",
    "secondaryProfession": "profTrainer",
    "stablemasters": "stable",
    "spirithealers": "spirit",
    "mountTrainer": "otherNpc",
    "guildmasters": "otherNpc",
}

FAC_MAP = {"Alliance": "A", "Horde": "H", "Neutral": "N"}
LOCALE_RE = re.compile(r'L\["((?:[^"\\]|\\.)*)"\]\s*=\s*"((?:[^"\\]|\\.)*)"')
MAP_HDR_RE = re.compile(r'^nodes\[(\d+)\]\s*=\s*\{', re.M)
ENTRY_RE = re.compile(r'\[(\d+)\]\s*=\s*\{([^{}]*)\}', re.S)


def unesc(s):
    return s.replace('\\"', '"').replace('\\\\', '\\')


def load_uimap_rects():
    p = os.path.join(UPSTREAM_DIR, "uimap-rects.json")
    if not os.path.isfile(p):
        sys.exit(f"缺少客户端 UiMapAssignment 坐标表：{p}")
    raw = json.load(open(p, encoding="utf-8")).get("rects") or {}
    out = {}
    for mid, (lx, ty, nw, nh) in raw.items():
        out[str(mid)] = [
            round(lx * CANVAS_W, 2),
            round(ty * CANVAS_H, 2),
            round(nw * CANVAS_W, 2),
            round(nh * CANVAS_H, 2),
        ]
    return out


def parse_locale(path):
    txt = open(path, encoding="utf-8", errors="ignore").read()
    return {unesc(k): unesc(v) for k, v in LOCALE_RE.findall(txt)}


def parse_handynotes_npcs(valid_mids):
    hn_root = addons_root.resolve("HandyNotes_NPCs (Classic)")
    data_lua = os.path.join(hn_root, "HandyNotes_NPCs (Classic)", "forever", "data.lua")
    zh_lua = os.path.join(hn_root, "HandyNotes_NPCs (Classic)", "locales", "forever", "zhCN.lua")
    if not os.path.isfile(data_lua):
        sys.exit(f"找不到 HandyNotes_NPCs forever/data.lua：{data_lua}")

    zh = parse_locale(zh_lua) if os.path.isfile(zh_lua) else {}
    txt = open(data_lua, encoding="utf-8", errors="ignore").read()

    matches = list(MAP_HDR_RE.finditer(txt))
    raw_pins = []
    maps_seen = set()

    for idx, m in enumerate(matches):
        map_id = m.group(1)
        if map_id not in valid_mids:
            continue
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(txt)
        block = txt[start:end]

        for em in ENTRY_RE.finditer(block):
            coord = int(em.group(1))
            body = em.group(2)
            cat_m = re.search(r'category\s*=\s*"([^"]+)"', body)
            if not cat_m:
                continue
            cat = NPC_CAT_MAP.get(cat_m.group(1))
            if not cat:
                continue

            x = round((coord // 10000) / 100.0, 2)
            y = round((coord % 10000) / 100.0, 2)
            if not (0 <= x <= 100 and 0 <= y <= 100):
                continue

            nm_m = re.search(r'name\s*=\s*(?:L\[)?"((?:[^"\\]|\\.)*)"\]?', body)
            name_en = unesc(nm_m.group(1)) if nm_m else ""
            name_cn = zh.get(name_en, name_en)

            fac_m = re.search(r'faction\s*=\s*"([^"]+)"', body)
            fac = FAC_MAP.get(fac_m.group(1), "N") if fac_m else "N"

            npc_m = re.search(r'npcID\s*=\s*(\d+)', body)
            npc_id = int(npc_m.group(1)) if npc_m else None

            prof_m = re.search(r'profession\s*=\s*"([^"]+)"', body)
            prof = prof_m.group(1) if prof_m else ""

            fp_m = re.search(r'fpName\s*=\s*(?:L\[)?"((?:[^"\\]|\\.)*)"\]?', body)
            fp_en = unesc(fp_m.group(1)) if fp_m else ""
            fp_cn = zh.get(fp_en, fp_en) if fp_en else ""

            if not name_cn and cat == "mailbox":
                name_cn, name_en = "邮箱", "Mailbox"
            elif not name_cn and cat == "spirit":
                name_cn, name_en = "灵魂医者", "Spirit Healer"

            rec = {"m": map_id, "x": x, "y": y, "c": cat, "f": fac, "n": name_cn or name_en or "NPC"}
            if name_en and name_en != name_cn:
                rec["e"] = name_en
            if npc_id:
                rec["id"] = npc_id
            if prof:
                rec["p"] = prof
            if fp_cn:
                rec["fp"] = fp_cn

            raw_pins.append(rec)
            maps_seen.add(map_id)

    by_npc = {}
    kept = []
    for r in raw_pins:
        if r.get("id") and r["c"] not in ("spirit", "mailbox"):
            by_npc.setdefault((r["m"], r["c"], r["id"]), []).append(r)
        else:
            kept.append(r)

    for grp in by_npc.values():
        if len(grp) <= 6:
            kept.extend(grp)
        else:
            sx = sum(p["x"] for p in grp) / len(grp)
            sy = sum(p["y"] for p in grp) / len(grp)
            kept.append(min(grp, key=lambda p: (p["x"] - sx) ** 2 + (p["y"] - sy) ** 2))

    kept.sort(key=lambda r: (r["m"], r["c"], r["n"], r["x"], r["y"]))
    counts = {}
    for r in kept:
        counts[r["c"]] = counts.get(r["c"], 0) + 1

    return {
        "meta": {
            "generatedAt": TODAY,
            "level": "L1",
            "source": "HandyNotes_NPCs (Classic) forever/data.lua + locales/forever/zhCN.lua",
            "boundary": "仅取事实字段（地图号/坐标/分类/阵营/NPC编号/中英文名/专业/鸟点名），不复制任何描述文案。",
            "maps": len(maps_seen),
            "total": len(kept),
            "counts": counts,
        },
        "pins": kept,
    }


def world_xy(zone_rects, map_id, px, py):
    rect = zone_rects.get(str(map_id))
    if not rect:
        return None
    rx, ry, rw, rh = rect
    return [round(rx + rw * (px / 100.0), 1), round(ry + rh * (py / 100.0), 1)]


def register_base_maps_in_manifest():
    if not os.path.isfile(ART_MANIFEST):
        return
    man = json.load(open(ART_MANIFEST, encoding="utf-8"))
    items = man.get("items")
    if not isinstance(items, list):
        return
    by_file = {it.get("file"): i for i, it in enumerate(items) if isinstance(it, dict)}
    meta_specs = [
        ("947", "世界总览底图（947，客户端 12 片拼接并擦除韩文标签）", "273209..273220"),
        ("1414", "卡利姆多大陆底图（1414，客户端 12 片拼接并擦除韩文标签）", "272067..272078"),
        ("1415", "东部王国大陆底图（1415，客户端 12 片拼接并擦除韩文标签）", "270450..270461"),
    ]
    changed = False
    for mid, note, fdids in meta_specs:
        fpath = os.path.join(MAPS_IMG_DIR, f"{mid}.webp")
        if not os.path.isfile(fpath):
            continue
        raw = open(fpath, "rb").read()
        rel = f"art/maps/{mid}.webp"
        rec = {
            "file": rel,
            "bytes": len(raw),
            "sha1": hashlib.sha1(raw).hexdigest()[:10],
            "source": f"client-export: Forever Interface/WorldMap ({fdids})",
            "kind": "world-map",
            "fetchedAt": TODAY,
            "note": note,
        }
        if rel in by_file:
            items[by_file[rel]] = rec
        else:
            items.append(rec)
        changed = True
    if changed:
        with open(ART_MANIFEST, "w", encoding="utf-8") as f:
            json.dump(man, f, ensure_ascii=False, indent=2)
        print("已登记 947/1414/1415 客户端底图至 app/img/art/manifest.json")


# 来自 UiMapAssignment.db2（FDID 1957219）的三大陆世界坐标范围，用于精确投影船只/飞艇/空艇与飞行航线
CONT_YARD_BOUNDS = {
    1: (-11733.30, -19733.21, 12799.90, 17066.60, "1414"),  # 卡利姆多
    0: (-16000.00, -19199.90, 7466.60, 16000.00, "1415"),   # 东部王国
    2991: (1247.92, -1331.25, 4956.25, 4231.25, "2521"),    # 泽风岛
}

OPENMAP_DIR = os.path.join(addons_root.resolve("OpenMap"), "OpenMap", "Data", "Forever")

ROUTE_NAME_CN = {
    "Booty Bay - Ratchet": ("藏宝海湾 ⇄ 棘齿城", "N"),
    "Grom'gol - Orgrimmar": ("格罗姆高 ⇄ 奥格瑞玛", "H"),
    "Menethil Ships": ("米奈希尔港 ⇄ 塞拉摩", "A"),
    "Rut'theran - Auberdine": ("鲁瑟兰村 ⇄ 奥伯丁", "A"),
    "Orgrimmar Zepplins": ("部落主城飞艇线", "H"),
    "Feathermoon - Feralas": ("羽月要塞 ⇄ 菲拉斯海岸", "A"),
    "Menethil - Southshore - Auberdine": ("米奈希尔 → 南海镇 → 奥伯丁", "A"),
    "Steamwheedle Port - Powderfuse Port": ("热砂港 ⇄ 药引港（河林）", "N"),
    "Alterac Mountains - Zephras Isle": ("奥特兰克 ⇄ 泽风岛（空艇）", "N"),
    "Mulgore - Zephras Isle": ("莫高雷 ⇄ 泽风岛（空艇）", "N"),
    "Stormwind - Auberdine": ("暴风城 ⇄ 奥伯丁", "A"),
}

FOREVER_EXTRA_FLIGHTS = {
    559: ("永恒之巅（海加尔山）", "海加尔山", "2482", "N"),
    3242: ("污染山麓（海加尔山）", "海加尔山", "2482", "N"),
    3203: ("罗格玛（河林）", "河林", "2548", "H"),
    3276: ("法霍尔德要塞（河林）", "河林", "2548", "A"),
}


def yards_to_world(rects, cont, wy_x, wy_y):
    b = CONT_YARD_BOUNDS.get(cont)
    if not b:
        return None
    x0, y0, x1, y1, mid = b
    r = rects.get(mid)
    if not r:
        return None
    # WoW 世界坐标：Y 越大越西（u 越小），X 越大越北（v 越小）
    u = (y1 - wy_y) / (y1 - y0)
    v = (x1 - wy_x) / (x1 - x0)
    wx = round(r[0] + u * r[2], 1)
    wy = round(r[1] + v * r[3], 1)
    return [wx, wy]


def world_to_zone_hit(atlas_zones, wx, wy):
    hits = [
        z for z in atlas_zones
        if not z.get("isCity")
        and z["rect"][0] <= wx <= z["rect"][0] + z["rect"][2]
        and z["rect"][1] <= wy <= z["rect"][1] + z["rect"][3]
    ]
    if not hits:
        hits = [
            z for z in atlas_zones
            if z["rect"][0] <= wx <= z["rect"][0] + z["rect"][2]
            and z["rect"][1] <= wy <= z["rect"][1] + z["rect"][3]
        ]
    if not hits:
        return None, 50.0, 50.0
    hits.sort(key=lambda z: z["rect"][2] * z["rect"][3])
    z = hits[0]
    px = round((wx - z["rect"][0]) / z["rect"][2] * 100.0, 1)
    py = round((wy - z["rect"][1]) / z["rect"][3] * 100.0, 1)
    return z, px, py


def parse_openmap_transports_and_routes(rects, atlas_zones):
    """从本机 OpenMap Data/Forever/Places.lua 提取事实航线停靠点与真实航行轨迹。"""
    places_path = os.path.join(OPENMAP_DIR, "Places.lua")
    if not os.path.isfile(places_path):
        return [], []
    txt = open(places_path, encoding="utf-8", errors="ignore").read()

    # 1. 解析 transports 停靠码头 / 飞艇塔 / 空艇港
    transports = []
    seen_ports = []
    m_tr = re.search(r"transports\s*=\s*\{(.*?)\n\t\},", txt, re.S)
    if m_tr:
        pat = re.compile(
            r'\{\s*"(boat|zeppelin|airship)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*(\d+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*\}'
        )
        kind_cn = {"boat": "船只码头", "zeppelin": "飞艇塔", "airship": "空艇停靠点"}
        for idx, m in enumerate(pat.finditer(m_tr.group(1))):
            kind, rname, c1, x1, y1, c2, x2, y2 = (
                m.group(1), m.group(2), int(m.group(3)), float(m.group(4)), float(m.group(5)),
                int(m.group(6)), float(m.group(7)), float(m.group(8)),
            )
            p1 = yards_to_world(rects, c1, x1, y1)
            p2 = yards_to_world(rects, c2, x2, y2)
            if not (p1 and p2):
                continue
            r_cn, fac = ROUTE_NAME_CN.get(rname, (rname, "H" if kind == "zeppelin" else "N"))
            z1, px1, py1 = world_to_zone_hit(atlas_zones, p1[0], p1[1])
            z2, _, _ = world_to_zone_hit(atlas_zones, p2[0], p2[1])
            z1_name = z1["nameCn"] if z1 else "海域港口"
            z2_name = z2["nameCn"] if z2 else "跨海目的地"
            # 同码头去重合并多条航线
            merged = None
            for sp in seen_ports:
                if sp["kind"] == kind and ((sp["wx"] - p1[0]) ** 2 + (sp["wy"] - p1[1]) ** 2) < 120:
                    merged = sp
                    break
            dest_label = f"前往 {z2_name}（{r_cn}）"
            if merged:
                if dest_label not in merged["destinations"]:
                    merged["destinations"].append(dest_label)
                continue
            rec = {
                "id": f"port:{kind}:{idx}",
                "kind": kind,
                "kindCn": kind_cn[kind],
                "faction": fac,
                "name": f"{z1_name} · {kind_cn[kind]}",
                "routeName": r_cn,
                "zone": z1_name,
                "mapId": z1["mapId"] if z1 else "947",
                "x": px1,
                "y": py1,
                "wx": p1[0],
                "wy": p1[1],
                "destinations": [dest_label],
            }
            seen_ports.append(rec)
            transports.append(rec)

    # 2. 解析 sailings 真实多段航行轨迹（跨海段自动补优雅弧线）
    atlas_routes = []
    m_sl = re.search(r"sailings\s*=\s*\{(.*?)\n\t\},", txt, re.S)
    if m_sl:
        line_pat = re.compile(r'\{\s*"(boat|zeppelin|airship)"\s*,\s*"([^"]+)"\s*,\s*\{(.*)\}\s*\},')
        piece_pat = re.compile(r'\{\s*(\d+)\s*,\s*\{([\-0-9.,\s]+)\}\s*\}')
        for idx, line in enumerate(m_sl.group(1).splitlines()):
            lm = line_pat.search(line)
            if not lm:
                continue
            kind, rname, body = lm.group(1), lm.group(2), lm.group(3)
            r_cn, fac = ROUTE_NAME_CN.get(rname, (rname, "H" if kind == "zeppelin" else "N"))
            way = []
            for pm in piece_pat.finditer(body):
                cont = int(pm.group(1))
                nums = [float(v.strip()) for v in pm.group(2).split(",") if v.strip()]
                seg = []
                for k in range(0, len(nums) - 1, 2):
                    pt = yards_to_world(rects, cont, nums[k], nums[k + 1])
                    if pt:
                        seg.append(pt)
                if not seg:
                    continue
                if way and seg:
                    # 跨海段用柔和二次贝塞尔弧线衔接（与 OpenMap Routes.lua 一致）
                    p0, p2 = way[-1], seg[0]
                    du, dv = p2[0] - p0[0], p2[1] - p0[1]
                    dist = math.hypot(du, dv)
                    if dist > 40:
                        side = -1.0 if ((p0[1] + p2[1]) / 2.0 < CANVAS_H * 0.5) else 1.0
                        nu, nv = -dv / dist, du / dist
                        if nv * side < 0:
                            nu, nv = -nu, -nv
                        cx = (p0[0] + p2[0]) / 2.0 + nu * min(95.0, dist * 0.14)
                        cy = (p0[1] + p2[1]) / 2.0 + nv * min(95.0, dist * 0.14)
                        for s_i in range(1, 10):
                            t = s_i / 10.0
                            bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * cx + t ** 2 * p2[0]
                            by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * cy + t ** 2 * p2[1]
                            way.append([round(bx, 1), round(by, 1)])
                way.extend(seg)
            if len(way) < 2:
                continue
            # 对 Orgrimmar Zepplins 按起止地细分清晰中文名
            z_start, _, _ = world_to_zone_hit(atlas_zones, way[0][0], way[0][1])
            z_end, _, _ = world_to_zone_hit(atlas_zones, way[-1][0], way[-1][1])
            label_cn = f"{z_start['nameCn'] if z_start else ''} ⇄ {z_end['nameCn'] if z_end else ''}" if rname == "Orgrimmar Zepplins" else r_cn
            atlas_routes.append({
                "id": f"sail:{idx}",
                "kind": kind,
                "faction": fac,
                "name": label_cn,
                "points": way,
            })

    return transports, atlas_routes


def parse_openmap_flights(rects, atlas_zones):
    """从本机 OpenMap Data/Forever/FlightData.lua 提取联盟/部落完整飞行线路图与无限新增鸟点。"""
    fp = os.path.join(OPENMAP_DIR, "FlightData.lua")
    if not os.path.isfile(fp):
        return [], []
    txt = open(fp, encoding="utf-8", errors="ignore").read()

    nodes = {}
    m_nodes = re.search(r"nodes\s*=\s*\{(.*?)\n\t\},", txt, re.S)
    if m_nodes:
        npat = re.compile(r'\[(\d+)\]\s*=\s*\{\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*,\s*(\d+)')
        for m in npat.finditer(m_nodes.group(1)):
            nid = int(m.group(1))
            name_en, cont, wx_y, wy_y, fbit = m.group(2), int(m.group(3)), float(m.group(4)), float(m.group(5)), int(m.group(6))
            pos = yards_to_world(rects, cont, wx_y, wy_y)
            if not pos:
                continue
            fac = "A" if fbit == 1 else ("H" if fbit == 2 else "N")
            nodes[nid] = {"id": nid, "nameEn": name_en, "cont": cont, "fac": fac, "pos": pos}

    # 补充 HandyNotes 中尚未收录的无限服新鸟点（海加尔山 / 河林）
    extra_flights = []
    for nid, (cn, zname, mid, fac) in FOREVER_EXTRA_FLIGHTS.items():
        nd = nodes.get(nid)
        if not nd:
            continue
        z, px, py = world_to_zone_hit(atlas_zones, nd["pos"][0], nd["pos"][1])
        extra_flights.append({
            "id": nid,
            "nameCn": cn,
            "nameEn": nd["nameEn"],
            "zone": z["nameCn"] if z else zname,
            "mapId": z["mapId"] if z else mid,
            "x": px,
            "y": py,
            "wx": nd["pos"][0],
            "wy": nd["pos"][1],
            "faction": fac,
        })

    # 解析所有双向直飞航线（合并正反向为无向边，均匀抽稀为 6–10 个控制点，体积轻且曲线顺滑）
    flight_paths = []
    seen_edges = set()
    m_paths = re.search(r"paths\s*=\s*\{(.*?)\n\t\},", txt, re.S)
    if m_paths:
        ppat = re.compile(r'\{\s*(\d+)\s*,\s*(\d+)\s*,\s*\d+\s*,\s*\d+\s*,\s*\{([\-0-9.,\s]+)\}\s*\}')
        for m in ppat.finditer(m_paths.group(1)):
            a, b = int(m.group(1)), int(m.group(2))
            if a not in nodes or b not in nodes:
                continue
            na, nb = nodes[a], nodes[b]
            if na["cont"] != nb["cont"]:
                continue
            edge_key = (min(a, b), max(a, b))
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            # 判定航线所属阵营（任一端为 A 则 A，任一端为 H 则 H，两端皆 N 则 N）
            if na["fac"] == "A" or nb["fac"] == "A":
                efac = "A"
            elif na["fac"] == "H" or nb["fac"] == "H":
                efac = "H"
            else:
                efac = "N"
            nums = [float(v.strip()) for v in m.group(3).split(",") if v.strip()]
            pts = []
            for k in range(0, len(nums) - 1, 2):
                pt = yards_to_world(rects, na["cont"], nums[k], nums[k + 1])
                if pt:
                    pts.append(pt)
            if len(pts) < 2:
                pts = [na["pos"], nb["pos"]]
            elif len(pts) > 9:
                step = (len(pts) - 1) / 8.0
                pts = [pts[int(round(i * step))] for i in range(9)]
            flight_paths.append({
                "id": f"fp:{edge_key[0]}-{edge_key[1]}",
                "from": a,
                "to": b,
                "faction": efac,
                "points": pts,
            })

    return extra_flights, flight_paths


def build_atlas(rects):
    world = json.load(open(os.path.join(DATA_DIR, "world.json"), encoding="utf-8"))
    dungeons = json.load(open(os.path.join(DATA_DIR, "dungeons.json"), encoding="utf-8"))
    dgeo = json.load(open(os.path.join(DATA_DIR, "dungeon-geo.json"), encoding="utf-8"))

    zones_by_mid = {str(z.get("mapId")): z for z in world.get("zones") or [] if z.get("mapId")}

    # 全部有本地底图且有精确投影矩形的区域（44 野外与无限新区 + 1453 暴风城 + 1455 铁炉堡）
    target_mids = list(zones_by_mid.keys()) + [k for k in CITY_EXTRAS if k not in zones_by_mid]
    atlas_zones = []
    zone_rects = {}

    for mid in target_mids:
        img_rel = f"img/art/maps/{mid}.webp"
        if not os.path.isfile(os.path.join(MAPS_IMG_DIR, f"{mid}.webp")):
            continue
        rect = rects.get(mid)
        if not rect:
            continue
        zone_rects[mid] = rect
        z = zones_by_mid.get(mid)
        if z:
            atlas_zones.append({
                "mapId": mid,
                "id": z.get("id") or mid,
                "nameCn": z.get("nameCn") or mid,
                "continent": z.get("continent") or "new",
                "continentCn": z.get("continentCn") or "无限新增区域",
                "faction": z.get("faction") or "",
                "side": z.get("side") or "N",
                "levelRange": z.get("levelRange"),
                "isNew": bool(z.get("isNew")),
                "isCity": mid == "1457",
                "mapFile": img_rel,
                "rect": rect,
            })
        elif mid in CITY_EXTRAS:
            ce = CITY_EXTRAS[mid]
            atlas_zones.append({
                "mapId": mid,
                "id": ce["id"],
                "nameCn": ce["nameCn"],
                "continent": ce["continent"],
                "continentCn": ce["continentCn"],
                "faction": ce["faction"],
                "side": "A" if ce["faction"] == "联盟" else "N",
                "levelRange": None,
                "isNew": False,
                "isCity": True,
                "mapFile": img_rel,
                "rect": rect,
            })

    # 两大陆高精度叠加层（1414 卡利姆多 / 1415 东部王国）
    continents = []
    for cid, cname in (("1414", "卡利姆多"), ("1415", "东部王国")):
        if cid in rects and os.path.isfile(os.path.join(MAPS_IMG_DIR, f"{cid}.webp")):
            continents.append({
                "mapId": cid,
                "nameCn": cname,
                "mapFile": f"img/art/maps/{cid}.webp",
                "rect": rects[cid],
            })

    # 副本与团本入口
    all_d = []
    for key, is_raid in (("newDungeons", False), ("classicDungeons", False), ("raids", True)):
        for d in dungeons.get(key) or []:
            item = dict(d)
            item["_isRaid"] = is_raid
            item["_isNew"] = key == "newDungeons" or bool(d.get("isNew"))
            all_d.append(item)
    d_by_slug = {(d.get("slug") or d.get("id")): d for d in all_d if (d.get("slug") or d.get("id"))}
    geo_map = dgeo.get("dungeons") or {}
    entries = []
    for slug, d in d_by_slug.items():
        g = geo_map.get(slug) if isinstance(geo_map, dict) else None
        ent = (g or {}).get("entry") if isinstance(g, dict) else None
        mid = str((ent or {}).get("mapId") or "")
        ex = (ent or {}).get("x")
        ey = (ent or {}).get("y")
        if (not mid or ex is None or ey is None) and slug == "hyjal-summit":
            mid, ex, ey = "2482", 62.0, 44.0
        elif (not mid or ex is None or ey is None) and slug == "barrow-deeps":
            mid, ex, ey = "2482", 34.0, 68.0
        if mid not in zone_rects or ex is None or ey is None:
            continue
        is_raid = bool(d.get("_isRaid")) or d.get("kind") == "raid"
        entries.append({
            "slug": slug,
            "nameCn": d.get("nameCn") or slug,
            "nameEn": d.get("nameEn") or "",
            "isRaid": is_raid,
            "isNew": bool(d.get("_isNew")),
            "levelRange": d.get("levelRange"),
            "zone": (ent or {}).get("zone") or d.get("zone") or (zones_by_mid.get(mid) or {}).get("nameCn", ""),
            "mapId": mid,
            "x": round(float(ex), 1),
            "y": round(float(ey), 1),
        })
    entries.sort(key=lambda e: (not e["isRaid"], (e["levelRange"] or [99])[0], e["nameCn"]))

    transports, atlas_routes = parse_openmap_transports_and_routes(zone_rects | {k: rects[k] for k in ("1414", "1415", "2521") if k in rects}, atlas_zones)
    extra_flights, flight_paths = parse_openmap_flights(zone_rects | {k: rects[k] for k in ("1414", "1415", "2521") if k in rects}, atlas_zones)

    # 若已有 6K 无缝瓦片金字塔元数据，自动合并保留
    tile_pyramid = None
    tiles_meta = os.path.join(DATA_DIR, "upstream", "world-tiles-meta.json")
    if os.path.isfile(tiles_meta):
        tile_pyramid = json.load(open(tiles_meta, encoding="utf-8"))

    out = {
        "meta": {
            "generatedAt": TODAY,
            "canvas": {"w": CANVAS_W, "h": CANVAS_H},
            "worldMap": "img/art/maps/947.webp",
            "zoneCount": len(atlas_zones),
            "dungeonEntryCount": len(entries),
            "transportCount": len(transports),
            "routeCount": len(atlas_routes),
            "flightPathCount": len(flight_paths),
            "sources": [
                {"name": "Forever 客户端世界/大陆底图 947/1414/1415 与 UiMapAssignment.db2 精确投影", "level": "L0", "checkedAt": TODAY},
                {"name": "本站 app/img/art/maps（46 张本地高清区域底图与 6K 无缝瓦片金字塔）", "level": "L0"},
                {"name": "OpenMap Data/Forever/Places.lua & FlightData.lua（MIT 事实航线与鸟点网络）", "level": "L1", "checkedAt": TODAY},
                {"name": "DungeonsForever 副本入口坐标（dungeon-geo.json）", "level": "L1", "checkedAt": TODAY},
            ],
        },
        "continents": continents,
        "zones": atlas_zones,
        "dungeons": entries,
        "transports": transports,
        "routes": atlas_routes,
        "extraFlights": extra_flights,
        "flightPaths": flight_paths,
    }
    if tile_pyramid:
        out["tilePyramid"] = tile_pyramid
    return out, zone_rects


def ensure_legacy_books():
    path = os.path.join(DATA_DIR, "legacy-books.json")
    if os.path.isfile(path):
        cur = json.load(open(path, encoding="utf-8"))
        print(f"保留已有 legacy-books.json：{len(cur.get('books') or [])} 条")
        return
    skeleton = {
        "meta": {
            "updatedAt": TODAY,
            "status": "ready",
            "note": "传承书籍点位扩展真源：缺数诚实留空不编造；后续逐条录入实测或已核来源坐标后，无限地图「传承书籍」图层自动展示并支持本地打卡。",
        },
        "books": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(skeleton, f, ensure_ascii=False, indent=2)


def main():
    rects = load_uimap_rects()
    register_base_maps_in_manifest()
    atlas, zone_rects = build_atlas(rects)
    atlas_path = os.path.join(DATA_DIR, "world-atlas.json")
    with open(atlas_path, "w", encoding="utf-8") as f:
        json.dump(atlas, f, ensure_ascii=False, separators=(",", ":"))
    print(f"写入 world-atlas.json：世界底图 947 + {len(atlas['continents'])} 大陆层 + {atlas['meta']['zoneCount']} 区域 / {atlas['meta']['dungeonEntryCount']} 副本入口 / {atlas['meta']['transportCount']} 航线停靠点 / {atlas['meta']['routeCount']} 船艇航线 / {atlas['meta']['flightPathCount']} 条飞行线路")

    npcs = parse_handynotes_npcs(set(zone_rects.keys()))
    npcs_path = os.path.join(DATA_DIR, "map-npcs.json")
    with open(npcs_path, "w", encoding="utf-8") as f:
        json.dump(npcs, f, ensure_ascii=False, separators=(",", ":"))
    print(f"写入 map-npcs.json：{npcs['meta']['total']} 条 NPC / {npcs['meta']['maps']} 张地图")

    ensure_legacy_books()


if __name__ == "__main__":
    main()
