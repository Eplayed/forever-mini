#!/usr/bin/env python3
# 从 DungeonsForever 的 Data_DungeonLoot.lua 抽「每座本有哪些首领、首领掉哪些物品 ID」这一层。
#
# 为什么要它（2026-11-01 站主拍板"DF/XR 那几张从未取过的表要开"）：
#   extract-df-geo.py 早就在读这张表，但**只取了它的前两列当名字桥**，掉落那一层一条没落盘。
#   现测：本站 达拉然 / 奥妮克希亚的巢穴 两座首领名单是空的，DF 那份有 8 条与 1 条；
#   另外 11 座两边都有名单但条数不同（黑石深渊 我们 20 / DF 27）。这些差异以前看不见，
#   因为没有快照就没有对账。
#
# 边界（DF 的 LICENSE 是「Copyright © 2026 圆圆 · 保留所有权利」）：
#   取的是 首领中英文名、npcId、掉落物品 ID —— 全是游戏内事实标识符。
#   一律不取：掉落概率（行里那个 100/nil 是掉率，本站红线"掉落不写百分比"）、
#             DF 的任何成段说明、攻略句子、任务目标文本、图（Media/）。
#   这份快照不是成品：它只落 upstream/，不写 dungeons.json。要不要拿它补首领名单是合并层的决定，
#   补进去会变成"第三家名单"，与 wclbox 那份的分歧得两个都留——那一刀等站主点头再由合并层落。
#
# 用法：python3 tools/extract-df-loot.py [--src <插件根目录>] [--show]
#       --src 不给时按顺序找：环境变量 WOW_ADDONS → Mac 的 .scratch/wow → 这台 Windows 的 _cn_beta_ 安装目录
import datetime
import hashlib
import io
import json
import os
import re
import sys

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(WEB, "app", "data", "upstream")
ADDON = "DungeonsForever"
HOME = os.path.expanduser("~")

# 与 extract-df-geo.py 同一张别名表：DF 的 slug 与站内 id 不只是下划线/横线之差。
# 对不上的留在 unmapped 里，不许猜一个塞进去（改动要两处同步，先改 geo 那份）。
ALIAS = {
    "excavation_wetlands": "whelgars-excavation",
    "razorfen_downs": "razor-krendor",
    "sm_armory": "scarlet-monastery-armory",
    "sm_cathedral": "scarlet-monastery-cathedral",
    "sm_graveyard": "scarlet-monastery-graveyard",
    "sm_library": "scarlet-monastery-library",
    "stratholme_main": "stratholme-main-gate",
    "stratholme_service": "stratholme-service-gate",
    "the_deadmines": "deathmine",
    "the_stockade": "the-stocks",
    "zul_farrak": "zulfarrak",
}

from addons_root import resolve, explain


def resolve_src():
    """--src → WOW_ADDONS → 常见安装位。顺序只维护一份，在 addons_root.py 里。"""
    for i, a in enumerate(sys.argv):
        if a == "--src":
            return sys.argv[i + 1]
    root = resolve(ADDON)
    if os.path.isdir(os.path.join(root, ADDON)):
        return root
    sys.exit("找不到 %s。给 --src <插件根目录>，或把环境变量 WOW_ADDONS 指到 Interface/AddOns。\n%s"
             % (ADDON, explain()))


def our_id(df_slug):
    return ALIAS.get(df_slug, df_slug.replace("_", "-"))


def install_root(addons_dir):
    """安装根 = AddOns 往上那一层客户端目录名（本机是 _cn_beta_），别把整条绝对路径写进数据。"""
    parts = os.path.abspath(addons_dir).replace("\\", "/").rstrip("/").split("/")
    return parts[-2] if parts[-1] == "AddOns" and len(parts) >= 2 else parts[-1]


def toc_version(addon_dir):
    p = os.path.join(addon_dir, ADDON + ".toc")
    if not os.path.exists(p):
        return "版本未记"
    for line in io.open(p, encoding="utf-8", errors="ignore"):
        m = re.match(r"\s*##\s*Version:\s*(\S+)", line)
        if m:
            return m.group(1)
    return "版本未记"


def parse_loot(text):
    """ns.DungeonLoot[slug] = { {英, 中, "", npcId, { {物品ID, 掉率, 绑定}, ... }}, ... }
       返回 {slug: [ {nameEn,nameCn,npcId,itemIds[]} ]}。掉率那一列在这里就被丢掉，不往对象里放。"""
    out = {}
    blocks = re.split(r'^\s*\["([a-z0-9_]+)"\]\s*=\s*\{', text, flags=re.M)
    for i in range(1, len(blocks), 2):
        slug, body = blocks[i], blocks[i + 1]
        bosses = []
        for m in re.finditer(r'\{\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"(\d*)"', body):
            tail_start = m.end()
            tail = body[tail_start:t_start_of_next(body, tail_start)]
            bosses.append({
                "nameEn": m.group(1),
                "nameCn": m.group(2),
                "npcId": int(m.group(4)) if m.group(4) else None,
                "itemIds": sorted({int(x) for x in re.findall(r'\{\s*(\d+)\s*,\s*(?:\d+|nil)\s*,\s*(?:true|false)\s*\}', tail)},
                )
            })
        out[slug] = bosses
    return out


def t_start_of_next(body, pos):
    """把掉落列表限定在这条首领行内：从 pos 起找到与本行 '{' 配平的那个 '}'，找不到就给到文末。"""
    depth, j, q = 1, pos, None
    while j < len(body):
        c = body[j]
        if q:
            if c == "\\":
                j += 2
                continue
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return len(body)


def main():
    src = resolve_src()
    addon_dir = os.path.join(src, ADDON)
    lua = os.path.join(addon_dir, "Core", "Data", "Data_DungeonLoot.lua")
    if not os.path.exists(lua):
        sys.exit("找不到 %s" % lua)
    raw = io.open(lua, encoding="utf-8").read()
    loot = parse_loot(raw)

    dpath = os.path.join(WEB, "app", "data", "dungeons.json")
    ours = json.loads(io.open(dpath, encoding="utf-8").read()) if os.path.exists(dpath) else {}
    our_map = {}
    for key in ("newDungeons", "classicDungeons", "raids"):
        for x in ours.get(key) or []:
            our_map[x.get("id")] = {"group": key, "nameCn": x.get("nameCn"),
                                    "bosses": [b.get("nameCn") for b in (x.get("bosses") or [])]}

    matched, unmapped, recon = [], [], []
    for slug, bosses in sorted(loot.items()):
        oid = our_id(slug)
        item_ids = sorted({n for b in bosses for n in b["itemIds"]})
        # DF 的行里混着"小兵 / 图纸 / 战利品"这类没有 npcId 的伪首领行（全表 300 行里 41 行）。
        # 按整行数去对账会把它们当首领，合并层照这个数补名单就是给站内灌水，所以只数有 npcId 的。
        real = [b for b in bosses if b["npcId"] is not None]
        rec = {"dfSlug": slug, "ourId": oid, "realBossCount": len(real),
               "dfRowCount": len(bosses), "itemCount": len(item_ids)}
        if oid in our_map:
            o = our_map[oid]
            rec["ourBossCount"] = len([x for x in o["bosses"] if x])
            matched.append(oid)
            if rec["realBossCount"] != rec["ourBossCount"]:
                recon.append([oid, o["nameCn"], rec["ourBossCount"], rec["realBossCount"], rec["dfRowCount"]])
        else:
            unmapped.append(slug)

    entries = []
    for slug in sorted(loot):
        oid = our_id(slug)
        entries.append({
            "id": oid,
            "dfSlug": slug,
            "bosses": [{"nameCn": b["nameCn"], "nameEn": b["nameEn"], "npcId": b["npcId"],
                        "itemIds": b["itemIds"]} for b in loot[slug]],
        })

    b = open(lua, "rb").read()
    all_items = {n for v in loot.values() for bb in v for n in bb["itemIds"]}
    roster = set()
    ipath = os.path.join(WEB, "app", "data", "items.json")
    if os.path.exists(ipath):
        for x in (json.loads(io.open(ipath, encoding="utf-8").read()).get("items") or []):
            roster.add(str(x.get("id")))
    counts = {
        "dfDungeons": len(loot),
        "dfRows": sum(len(v) for v in loot.values()),
        "realBossRows": sum(1 for v in loot.values() for bb in v if bb["npcId"] is not None),
        "pseudoRows": sum(1 for v in loot.values() for bb in v if bb["npcId"] is None),
        "dfItemIds": len(all_items),
        "dfItemIdsAlreadyInRoster": len(all_items & {int(r) for r in roster if r.isdigit()}),
        "matchedOurIds": len(set(matched)),
        "unmappedDfSlugs": len(set(unmapped)),
    }
    print("DF 掉落表：%d 座 / %d 行（其中真首领 %d 行、无 npcId 的伪行 %d 行）/ 去重物品 ID %d 个（本站名录已有 %d）"
          % (counts["dfDungeons"], counts["dfRows"], counts["realBossRows"], counts["pseudoRows"],
             counts["dfItemIds"], counts["dfItemIdsAlreadyInRoster"]))
    print("与本站 id 对上 %d 座；DF 有、我们 id 表里找不到 %d 座：%s"
          % (counts["matchedOurIds"], counts["unmappedDfSlugs"], json.dumps(sorted(set(unmapped)), ensure_ascii=False)))
    print("按真首领行与本站条数不同的 %d 座（本站 / DF真首领 / DF全行）：" % len(recon))
    for r in recon:
        print("   %-28s %-12s %3d  %3d  %3d" % (r[0], r[1] or "(没定名)", r[2], r[3], r[4]))

    if "--show" in sys.argv:
        return

    snap = {
        "meta": {
            "source": "%s %s Core/Data/Data_DungeonLoot.lua" % (ADDON, toc_version(addon_dir)),
            "addon": ADDON,
            "addonVersion": toc_version(addon_dir),
            "installRoot": install_root(src),
            "sourceFile": "%s/Core/Data/Data_DungeonLoot.lua" % ADDON,
            "sourceStamp": {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                            "fileDate": datetime.datetime.fromtimestamp(os.path.getmtime(lua)).strftime("%Y-%m-%d")},
            "fetched": datetime.date.today().isoformat(),
            "took": "首领中文名、英文名、npcId，以及每条首领的掉落物品 ID（去重、升序）",
            "droppedFields": ["掉率那一列（DF 行里 100 / nil 那个数）——本站红线：掉落不写百分比",
                              "DF 的任何成段说明、攻略句子、任务目标文本、Media/ 里的图"],
            "boundary": "DF 的 LICENSE 是「保留所有权利」。这一层只取游戏内事实标识符；"
                        "快照不进成品，要不要用它补站内首领名单由合并层决定并两个都留。",
            "caveat": "bosses 里含 npcId=null 的行（小兵 / 图纸 / 战利品这类分组占位，全表 %d 行），"
                      "它们不是首领：合并层要按 meta.counts.realBossRows 那一层判数，别拿整行数补名单。"
                      % counts["pseudoRows"],
            "aliasFrom": "tools/extract-df-loot.py 的 ALIAS，与 extract-df-geo.py 同一张表",
            "counts": counts,
            "recountBossDiff": recon,
        },
        "dungeons": entries,
    }
    if not os.path.isdir(UP):
        os.makedirs(UP)
    p = os.path.join(UP, "df-dungeon-loot.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("写 %s（%.1f KB）" % (os.path.relpath(p, WEB), os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
