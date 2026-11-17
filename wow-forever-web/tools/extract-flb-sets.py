#!/usr/bin/env python3
"""从本地客户端插件 ForeverLevelingBiS/Data/{Sets,Items}.lua 提取 36 套装备套装（14–58 级，含 7 套无限新增套装与 9 职业 T0 地下城套），
输出结构化上游快照 wow-forever-web/app/data/upstream/flb-sets.json。

遵守 AGENTS.md 第五章红线：
- 只取事实性标识符（套装 ID、中英文名、最低等级、部件物品 ID、掉落归属/专业制造归属）；
- 不取任何描述文案、不写掉落百分比、不编造未核出处（缺出处统一标"待实测"）。
"""
import json
import os
import re
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_DIR = r"C:\GAME\World of Warcraft\_forever_\Interface\AddOns\ForeverLevelingBiS\Data"
SETS_LUA = os.path.join(ADDON_DIR, "Sets.lua")
ITEMS_LUA = os.path.join(ADDON_DIR, "Items.lua")
OUT_JSON = os.path.join(ROOT, "app", "data", "upstream", "flb-sets.json")

ITEMS_JSON = os.path.join(ROOT, "app", "data", "items.json")
DUNGEONS_JSON = os.path.join(ROOT, "app", "data", "dungeons.json")
PROFS_JSON = os.path.join(ROOT, "app", "data", "professions.json")

NEW_SET_IDS = {2131, 2133, 2134, 2135, 1968, 2136, 2071}
T0_CLASS_MAP = {
    189: ("warrior", "战士"),
    188: ("paladin", "圣骑士"),
    186: ("hunter", "猎人"),
    184: ("rogue", "盗贼"),
    182: ("priest", "牧师"),
    187: ("shaman", "萨满祭司"),
    181: ("mage", "法师"),
    183: ("warlock", "术士"),
    185: ("druid", "德鲁伊"),
}
CRAFT_SET_IDS = {1968, 490, 321, 144, 141, 142, 491, 489, 143}

ZONE_TO_DUN = {
    "The Deadmines": ("deathmine", "死亡矿井"),
    "Wailing Caverns": ("wailing-caverns", "哀嚎洞穴"),
    "Shadowfang Keep": ("shadowfang-keep", "影牙城堡"),
    "Blackfathom Deeps": ("blackfathom-deeps", "黑暗深渊"),
    "The Stockade": ("the-stocks", "监狱"),
    "Gnomeregan": ("gnomeregan", "诺莫瑞根"),
    "Razorfen Kraul": ("razorfen-kraul", "剃刀沼泽"),
    "Razorfen Downs": ("razor-krendor", "剃刀高地"),
    "Scarlet Monastery": ("scarlet-monastery-armory", "血色修道院"),
    "Dalaran": ("city-of-dalaran", "达拉然"),
    "City of Dalaran": ("city-of-dalaran", "达拉然"),
    "Uldaman": ("uldaman", "奥达曼"),
    "Zul'Farrak": ("zulfarrak", "祖尔法拉克"),
    "Maraudon": ("maraudon", "玛拉顿"),
    "The Temple of Atal'Hakkar": ("sunken-temple", "沉没的神庙"),
    "Krol'dok Stronghold": ("kroldok-stronghold", "克罗多克要塞"),
    "Alcaz Prison": ("alcaz-prison", "奥卡兹监狱"),
    "Blackrock Depths": ("blackrock-depths", "黑石深渊"),
    "Blackrock Spire": ("upper-blackrock-spire", "黑石塔上层"),
    "Scholomance": ("scholomance", "通灵学院"),
    "Stratholme": ("stratholme-main-gate", "斯坦索姆正门"),
    "Dire Maul": ("dire-maul-east", "厄运之槌东区"),
}


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    items_doc = load_json(ITEMS_JSON)
    duns_doc = load_json(DUNGEONS_JSON)
    profs_doc = load_json(PROFS_JSON)

    item_map = { int(x["id"]): x for x in items_doc["items"] }
    valid_dun_ids = set()
    drop_by_item = {}
    for k in ("newDungeons", "classicDungeons", "raids"):
        for d in duns_doc.get(k) or []:
            valid_dun_ids.add(d["id"])
            for r in d.get("drops") or []:
                iid = int(r["itemId"]) if r.get("itemId") else None
                if iid and iid not in drop_by_item:
                    drop_by_item[iid] = (d["id"], d.get("nameCn") or d["id"], r.get("bossCn") or "")

    craft_by_item = {}
    for p in profs_doc.get("professions") or []:
        for r in p.get("recipes") or []:
            iid = int(r["itemId"]) if r.get("itemId") else None
            if iid and iid not in craft_by_item:
                sk = (r.get("sk") or {}).get("orange")
                craft_by_item[iid] = (p["id"], p["nameCn"], sk)

    with open(SETS_LUA, encoding="utf-8") as f:
        sets_lua = f.read()
    with open(ITEMS_LUA, encoding="utf-8") as f:
        items_lua = f.read()

    zh_match = re.search(r"zhCN\s*=\s*\{([^\n]+)\}", sets_lua)
    zh_names = {}
    if zh_match:
        for m in re.finditer(r"\[(\d+)\]\s*=\s*\"([^\"]+)\"", zh_match.group(1)):
            zh_names[int(m.group(1))] = m.group(2)

    out_sets = []
    for m in re.finditer(r"\{id=(\d+),name=\"([^\"]+)\",level=(\d+),items=\{([^}]+)\}", sets_lua):
        sid = int(m.group(1))
        name_en = m.group(2)
        level = int(m.group(3))
        piece_ids = [int(x.strip()) for x in m.group(4).split(",") if x.strip()]
        name_cn = zh_names.get(sid, name_en)

        is_new = sid in NEW_SET_IDS
        cls_slug, cls_cn = T0_CLASS_MAP.get(sid, (None, None))
        if is_new:
            cat = "new"
            cat_cn = "无限新套装"
        elif sid in T0_CLASS_MAP:
            cat = "t0"
            cat_cn = "职业T0套"
        elif level >= 52 and sid not in CRAFT_SET_IDS:
            cat = "endgame"
            cat_cn = "满级副本套"
        else:
            cat = "craft"
            cat_cn = "练级与制造套"

        first_it = item_map.get(piece_ids[0], {})
        mat = first_it.get("mat") or first_it.get("slot") or "套装"
        if mat == "其它":
            mat = first_it.get("slot") or "饰品"

        pieces = []
        for iid in piece_ids:
            it = item_map[iid]
            slot_cn = it.get("slot") or "部位"
            src_text = "待实测"
            dun_id = None

            if iid in drop_by_item:
                did, dcn, bcn = drop_by_item[iid]
                dun_id = did if did in valid_dun_ids else None
                src_text = "副本：" + dcn + (" · " + bcn if bcn else "")
            elif iid in craft_by_item:
                pid, pcn, sk = craft_by_item[iid]
                src_text = pcn + ("（技能 %d）" % sk if sk else "")
            else:
                im = re.search(r"\[" + str(iid) + r"\]=\{([^\n]+)\}", items_lua)
                if im:
                    line = im.group(1)
                    zm = re.search(r'zone="([^"]+)"', line)
                    tm = re.search(r'type="([^"]+)"', line)
                    if zm and zm.group(1) in ZONE_TO_DUN:
                        did, dcn = ZONE_TO_DUN[zm.group(1)]
                        dun_id = did if did in valid_dun_ids else None
                        src_text = "副本：" + dcn
                    elif tm:
                        tk = tm.group(1)
                        if tk == "quest":
                            src_text = "任务奖励"
                        elif tk == "boe":
                            src_text = "世界掉落（装绑）"
                        elif tk == "drop":
                            src_text = "世界/区域掉落"
                        elif tk == "vendor":
                            src_text = "商人出售"

            pieces.append(OrderedDict([
                ("item", iid),
                ("slot", slot_cn),
                ("src", src_text),
                ("dungeonId", dun_id),
            ]))

        out_sets.append(OrderedDict([
            ("id", "set-%d" % sid),
            ("setId", sid),
            ("name", name_cn),
            ("nameEn", name_en),
            ("level", level),
            ("cat", cat),
            ("catCn", cat_cn),
            ("isNew", is_new),
            ("cls", cls_slug),
            ("clsCn", cls_cn or mat),
            ("mat", mat),
            ("fetched", "2026-11-16"),
            ("pieces", pieces),
        ]))

    doc = OrderedDict([
        ("meta", OrderedDict([
            ("source", "ForeverLevelingBiS/Data/Sets.lua + Items.lua"),
            ("declaredOrigin", "客户端解包转述（Forever 1.60.1）"),
            ("fetched", "2026-11-16"),
            ("grade", "L1"),
            ("count", len(out_sets)),
            ("pieceCount", sum(len(s["pieces"]) for s in out_sets)),
        ])),
        ("itemSets", out_sets),
    ])

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    bis_path = os.path.join(ROOT, "app", "data", "bis.json")
    if os.path.isfile(bis_path):
        with open(bis_path, encoding="utf-8") as f:
            bis_doc = json.load(f, object_pairs_hook=OrderedDict)
        bis_doc["meta"]["scrapedAt"] = "2026-11-05"
        for st in bis_doc.get("sets") or []:
            st["fetched"] = "2026-11-05"
        bis_doc["meta"]["itemSetsMeta"] = doc["meta"]
        bis_doc["itemSets"] = out_sets
        if os.path.exists(bis_path):
            os.remove(bis_path)
        with open(bis_path, "w", encoding="utf-8") as f:
            json.dump(bis_doc, f, ensure_ascii=False, indent=1)
            f.write("\n")

    print("已生成 %s 并合入 bis.json：%d 套 / %d 件部件" % (OUT_JSON, len(out_sets), doc["meta"]["pieceCount"]))


if __name__ == "__main__":
    main()
