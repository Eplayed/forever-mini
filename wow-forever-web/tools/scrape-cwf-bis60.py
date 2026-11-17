#!/usr/bin/env python3
"""从 classicwowforever.com/bis-list/ 抓取全职业 27 专精 60 级团本前 BiS 名单，
输出结构化上游快照 wow-forever-web/app/data/upstream/cwf-bis60.json。

严格遵守 AGENTS.md 第五章红线：
- 只取事实性标识符（职业、专精、部位、物品 ID、同部位备选顺位、来源结构化指向）；
- 彻底丢弃 note、指南正文、属性优先级、循环建议、百分比等任何非事实字段；
- 全量标 L1（仅一家资料站列过），每套带回查 URL 与抓取日期。
"""
import json
import os
import re
import time
import urllib.request
from collections import OrderedDict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "app", "data", "upstream", "cwf-bis60.json")
ITEMS_PATH = os.path.join(ROOT, "app", "data", "items.json")
DUNGEONS_PATH = os.path.join(ROOT, "app", "data", "dungeons.json")
PROFS_PATH = os.path.join(ROOT, "app", "data", "professions.json")
GI_RECIPES_PATH = os.path.join(ROOT, "app", "data", "upstream", "gi-prof-recipes.json")
INDEX_URL = "https://classicwowforever.com/bis-list/"

SPEC_META = {
    "arms-warrior": ("warrior", "战士", "arms", "武器 Lv.60"),
    "fury-warrior": ("warrior", "战士", "fury", "狂怒 Lv.60"),
    "protection-warrior": ("warrior", "战士", "protection", "防护 Lv.60"),
    "holy-paladin": ("paladin", "圣骑士", "holy", "神圣 Lv.60"),
    "protection-paladin": ("paladin", "圣骑士", "protection", "防护 Lv.60"),
    "retribution-paladin": ("paladin", "圣骑士", "retribution", "惩戒 Lv.60"),
    "beast-mastery-hunter": ("hunter", "猎人", "beast-mastery", "野兽控制 Lv.60"),
    "marksmanship-hunter": ("hunter", "猎人", "marksmanship", "射击 Lv.60"),
    "survival-hunter": ("hunter", "猎人", "survival", "生存 Lv.60"),
    "assassination-rogue": ("rogue", "潜行者", "assassination", "刺杀 Lv.60"),
    "combat-rogue": ("rogue", "潜行者", "combat", "战斗 Lv.60"),
    "subtlety-rogue": ("rogue", "潜行者", "subtlety", "敏锐 Lv.60"),
    "discipline-priest": ("priest", "牧师", "discipline", "戒律 Lv.60"),
    "holy-priest": ("priest", "牧师", "holy", "神圣 Lv.60"),
    "shadow-priest": ("priest", "牧师", "shadow", "暗影 Lv.60"),
    "elemental-shaman": ("shaman", "萨满祭司", "elemental", "元素 Lv.60"),
    "enhancement-shaman": ("shaman", "萨满祭司", "enhancement", "增强 Lv.60"),
    "restoration-shaman": ("shaman", "萨满祭司", "restoration", "恢复 Lv.60"),
    "arcane-mage": ("mage", "法师", "arcane", "奥术 Lv.60"),
    "fire-mage": ("mage", "法师", "fire", "火焰 Lv.60"),
    "frost-mage": ("mage", "法师", "frost", "冰霜 Lv.60"),
    "affliction-warlock": ("warlock", "术士", "affliction", "痛苦 Lv.60"),
    "demonology-warlock": ("warlock", "术士", "demonology", "恶魔学识 Lv.60"),
    "destruction-warlock": ("warlock", "术士", "destruction", "毁灭 Lv.60"),
    "balance-druid": ("druid", "德鲁伊", "balance", "平衡 Lv.60"),
    "feral-druid": ("druid", "德鲁伊", "feral", "野性战斗 Lv.60"),
    "restoration-druid": ("druid", "德鲁伊", "restoration", "恢复 Lv.60"),
}

SLOT_KEY_CN = {
    "head": "头部",
    "neck": "项链",
    "shoulders": "肩部",
    "shoulder": "肩部",
    "back": "背部",
    "chest": "胸部",
    "wrists": "手腕",
    "wrist": "手腕",
    "hands": "手",
    "waist": "腰部",
    "legs": "腿部",
    "feet": "脚",
    "ring-1": ("戒指", 1),
    "ring-2": ("戒指", 2),
    "finger-1": ("戒指", 1),
    "finger-2": ("戒指", 2),
    "finger": "戒指",
    "trinket-1": ("饰品", 1),
    "trinket-2": ("饰品", 2),
    "trinket": "饰品",
    "main-hand": "主手",
    "off-hand": "副手",
    "two-hand": "主手",
    "ranged": "远程",
    "relic": "圣物",
}

PROF_CN = {
    "Blacksmithing": "锻造",
    "Enchanting": "附魔",
    "Engineering": "工程学",
    "Leatherworking": "制皮",
    "Tailoring": "裁缝",
    "Alchemy": "炼金术",
}

PLACE_TO_DUNGEON = {
    "Blackfathom Deeps": ("blackfathom-deeps", "黑暗深渊"),
    "Blackrock Spire": ("upper-blackrock-spire", "黑石塔"),
    "City of Dalaran": ("city-of-dalaran", "达拉然"),
    "Excavation Site: Wetlands": ("whelgars-excavation", "挖掘场：湿地"),
    "Gnomeregan": ("gnomeregan", "诺莫瑞根"),
    "Maraudon": ("maraudon", "玛拉顿"),
    "Razorfen Downs": ("razor-krendor", "剃刀高地"),
    "Razorfen Kraul": ("razorfen-kraul", "剃刀沼泽"),
    "Scarlet Monastery": ("scarlet-monastery-armory", "血色修道院"),
    "Scholomance": ("scholomance", "通灵学院"),
    "Shadowfang Keep": ("shadowfang-keep", "影牙城堡"),
    "Stratholme": ("stratholme-main-gate", "斯坦索姆"),
    "Sunken Temple": ("sunken-temple", "沉没的神庙"),
    "The Stockade": ("the-stocks", "监狱"),
    "Uldaman": ("uldaman", "奥达曼"),
    "Zul'Farrak": ("zulfarrak", "祖尔法拉克"),
    "Dire Maul": ("dire-maul-east", "厄运之槌"),
    "Blackmaw Hold": ("blackmaw-hold", "黑喉要塞"),
    "Krol'dok Stronghold": ("kroldok-stronghold", "克罗多克要塞"),
}

ZONE_CN = {
    "Arathi Highlands": "阿拉希高地",
    "Silithus": "希利苏斯",
    "Un'Goro Crater": "安戈洛环形山",
    "Blasted Lands": "诅咒之地",
    "Darnassus or Orgrimmar": "达纳苏斯 / 奥格瑞玛",
    "Dustwallow Marsh": "尘泥沼泽",
    "Eastern Plaguelands": "东瘟疫之地",
    "Felwood": "费伍德森林",
    "Feralas": "菲拉斯",
    "Hillsbrad Foothills": "希尔斯布莱德丘陵",
    "Ironforge or Orgrimmar": "铁炉堡 / 奥格瑞玛",
    "Ironforge": "铁炉堡",
    "Moonglade": "月光林地",
    "Mount Hyjal": "海加尔山",
    "Orgrimmar": "奥格瑞玛",
    "Riverglades": "河林（永望/新地图）",
    "Searing Gorge": "灼热峡谷",
    "Stormwind City or Undercity": "暴风城 / 幽暗城",
    "Stranglethorn Vale": "荆棘谷",
    "Tanaris": "塔纳利斯",
    "The Hinterlands": "辛特兰",
    "Winterspring": "冬泉谷",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


def extract_slots_json(html):
    for s in re.findall(r"<script[^>]*>(.*?)</script>", html, re.S):
        if "level-60" not in s:
            continue
        m = re.search(r'\.rsc\.push\("(.*)"\)$', s.strip(), re.S)
        if not m:
            continue
        raw = json.loads('"' + m.group(1) + '"')
        lv_pos = raw.find('"id":"level-60"')
        if lv_pos < 0:
            continue
        pos = raw.find('"slots":{', lv_pos)
        if pos < 0:
            continue
        start = pos + len('"slots":')
        depth = 0
        in_str = False
        esc = False
        end = start
        for i in range(start, len(raw)):
            ch = raw[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        return json.loads(raw[start:end])
    return None


def main():
    items_doc = json.load(open(ITEMS_PATH, encoding="utf-8"))
    duns_doc = json.load(open(DUNGEONS_PATH, encoding="utf-8"))
    profs_doc = json.load(open(PROFS_PATH, encoding="utf-8"))
    gi_rec = json.load(open(GI_RECIPES_PATH, encoding="utf-8")) if os.path.isfile(GI_RECIPES_PATH) else {}

    known_ids = {int(x["id"]) for x in items_doc["items"]}
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

    gi_by_id = {}
    for lst in (gi_rec.get("recipes") or {}).values():
        arr = lst if isinstance(lst, list) else [lst]
        for r in arr:
            rid = r.get("resultItemId")
            if rid and r.get("nameCn"):
                gi_by_id[int(rid)] = r

    today = date.today().isoformat()
    sets_out = []
    all_item_ids = set()
    missing_ids = set()
    extra_items = OrderedDict()

    def resolve_source(iid, src):
        if iid in drop_by_item:
            did, dcn, bcn = drop_by_item[iid]
            return ("副本：" + dcn + (" · " + bcn if bcn else ""), did if did in valid_dun_ids else None)
        if iid in craft_by_item:
            _, pcn, sk = craft_by_item[iid]
            return (pcn + ("（技能 %d）" % sk if sk else ""), None)
        if not isinstance(src, dict):
            return ("待实测", None)
        kind = src.get("kind") or ""
        place = (src.get("place") or "").strip()
        dun = PLACE_TO_DUNGEON.get(place)
        if kind == "crafted":
            return (PROF_CN.get(place, place or "专业制造"), None)
        if kind == "drop":
            if dun:
                return ("副本：" + dun[1], dun[0] if dun[0] in valid_dun_ids else None)
            return ("掉落：" + ZONE_CN.get(place, place or "未知"), None)
        if kind == "quest":
            if dun:
                return ("副本任务：" + dun[1], dun[0] if dun[0] in valid_dun_ids else None)
            z = ZONE_CN.get(place, place)
            return ("任务奖励" + ("（" + z + "）" if z else ""), None)
        if kind == "vendor":
            z = ZONE_CN.get(place, place)
            return ("商人出售" + ("（" + z + "）" if z else ""), None)
        return ("待实测", None)

    for slug, (cls, cls_cn, spec, mode_cn) in SPEC_META.items():
        url = INDEX_URL + slug + "/"
        html = fetch(url)
        slots_raw = extract_slots_json(html)
        if not slots_raw:
            raise RuntimeError("未能解析 slots JSON: " + url)

        doll = []
        alts = OrderedDict()
        refs = OrderedDict()

        for skey, rows in slots_raw.items():
            if not isinstance(rows, list) or not rows:
                continue
            mapped = SLOT_KEY_CN.get(skey)
            if not mapped:
                print("  [警告] 未映射部位键:", skey, "in", slug)
                continue
            if isinstance(mapped, tuple):
                slot_cn, cell = mapped
                alt_key = "finger" if slot_cn == "戒指" else "trinket"
            else:
                slot_cn, cell = mapped, 1
                alt_key = {"shoulder": "shoulder", "shoulders": "shoulder", "wrists": "wrist", "wrist": "wrist"}.get(skey, skey)

            row_ids = []
            for r in rows:
                iid = r.get("id")
                if not isinstance(iid, int) or iid <= 0:
                    continue
                row_ids.append(iid)
                all_item_ids.add(iid)
                if iid not in known_ids:
                    missing_ids.add(iid)
                    if str(iid) not in extra_items and iid in gi_by_id:
                        gr = gi_by_id[iid]
                        extra_items[str(iid)] = OrderedDict([
                            ("id", iid),
                            ("name", gr.get("nameCn")),
                            ("quality", gr.get("quality", 3)),
                            ("ilvl", gr.get("reqLevel")),
                            ("iconKey", None),
                        ])
                src_cn, dun_id = resolve_source(iid, r.get("source"))
                refs[str(iid)] = OrderedDict([("src", src_cn), ("dungeonId", dun_id)])

            if row_ids:
                doll.append(OrderedDict([
                    ("slot", slot_cn),
                    ("cell", cell),
                    ("item", row_ids[0]),
                ]))
                cur_alt = alts.setdefault(alt_key, [])
                for x in row_ids:
                    if x not in cur_alt:
                        cur_alt.append(x)

        sets_out.append(OrderedDict([
            ("id", "lv60-" + slug),
            ("cls", cls),
            ("clsCn", cls_cn),
            ("spec", spec),
            ("mode", mode_cn),
            ("level", 60),
            ("url", url),
            ("fetched", today),
            ("doll", doll),
            ("alts", alts),
            ("refs", refs),
        ]))
        print("  [%s] %s: %d 格 / %d 个备选" % (cls_cn, mode_cn, len(doll), sum(len(v) for v in alts.values())))
        time.sleep(0.25)

    doc = OrderedDict([
        ("meta", OrderedDict([
            ("source", INDEX_URL),
            ("fetched", today),
            ("level", 60),
            ("grade", "L1"),
            ("took", "职业、专精、部位、物品ID、同部位备选顺位、来源结构化指向"),
            ("dropped", "note 说明文字、属性优先级、循环建议、页面攻略正文"),
            ("extraItems", extra_items),
            ("counts", OrderedDict([
                ("sets", len(sets_out)),
                ("classes", len({s["cls"] for s in sets_out})),
                ("uniqueItems", len(all_item_ids)),
                ("missingInItemsJson", len(missing_ids)),
            ])),
            ("missingIds", sorted(missing_ids)),
        ])),
        ("sets", sets_out),
    ])

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("\n完成：%s（%d 套 / %d 件不重复物品，extraItems 兜底 %d 件）" % (
        OUT_PATH, len(sets_out), len(all_item_ids), len(extra_items)))


if __name__ == "__main__":
    main()
