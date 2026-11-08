#!/usr/bin/env python3
# 从 QuestieDB 的 Forever 专属掉落表抽「哪个物品从哪个 NPC 身上掉」这一层归属。
#
# 源（support/Forever/DropTables/）：
#   classicItemDrops.lua    wowhead 数据自动生成：[itemId] = { [npcId] = 掉率float, ... }
#   itemDropCorrections.lua 人工修正：Expansion 段里 [itemId] = { [npcId] = float 或 DropKeys.WOWHEAD }
# 方向与 DF 那份相反（extract-df-loot.py 是 首领→物品），这里统一成 (npcId, itemId) 归属对。
#
# 边界：
#   取的是 itemID、npcID、归属关系——全是事实标识符。
#   一律不取：掉率数值（float 与 DropKeys 引用都只当"归属成立"，本站红线：掉落不写百分比）、
#             注释里的物品名（那是 wowhead 的转述命名，与本站名录可能冲突，不需要）、任何说明文字。
#   这份是第三家掉落名单（与 df-dungeon-loot、wclbox 系并列），分歧都留：快照只落 upstream，
#   要不要并进成品由合并层决定。
#
# 用法：python3 tools/extract-questie-drops.py [--src <AddOns 目录>] [--show]
import datetime
import hashlib
import io
import json
import os
import re
import sys

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(WEB, "app", "data", "upstream")
DB_ADDON = "QuestieDB"
DROP_DIR = os.path.join(DB_ADDON, "support", "Forever", "DropTables")

from addons_root import resolve, explain

# 与 extract-df-loot.py 同款：正则抓 [id] = { 块，块内 [npcId] = 值。
# 值是 float（掉率）或 DropKeys.WOWHEAD（引用）——两类都只记归属，数值当场丢。
BLOCK_RE = re.compile(r"\[(\d+)\]\s*=\s*\{([^{}]*)\}", re.S)
PAIR_RE = re.compile(r"\[(\d+)\]\s*=\s*[^,\s]")
SECT_RE = re.compile(r"^\s*Questie\w+\.\w+\s*=\s*\{", re.M)


def parse_pairs(text):
    """返回 {(npcId, itemId)} 集合与块计数。"""
    pairs, blocks = set(), 0
    for m in BLOCK_RE.finditer(text):
        item_id, body = int(m.group(1)), m.group(2)
        npcs = {int(x) for x in PAIR_RE.findall(body)}
        if not npcs:
            continue
        blocks += 1
        for npc in npcs:
            pairs.add((npc, item_id))
    return pairs, blocks


def resolve_src():
    for i, a in enumerate(sys.argv):
        if a == "--src":
            return sys.argv[i + 1]
    root = resolve(DB_ADDON)
    if os.path.isdir(os.path.join(root, DB_ADDON)):
        return root
    sys.exit("找不到 %s。给 --src <AddOns 目录>，或设 WOW_ADDONS。\n%s" % (DB_ADDON, explain()))


def stamp(path):
    b = open(path, "rb").read()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
            "fileDate": datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")}


def main():
    src = resolve_src()
    drops_path = os.path.join(src, DROP_DIR, "classicItemDrops.lua")
    corr_path = os.path.join(src, DROP_DIR, "itemDropCorrections.lua")
    for p in (drops_path, corr_path):
        if not os.path.exists(p):
            sys.exit("找不到 %s" % p)

    drops_text = io.open(drops_path, encoding="utf-8").read()
    corr_text = io.open(corr_path, encoding="utf-8").read()

    wow_pairs, wow_blocks = parse_pairs(drops_text)
    corr_pairs, corr_blocks = parse_pairs(corr_text)
    all_pairs = wow_pairs | corr_pairs

    # ---- 与 DF 掉落快照对拍（npcId 桥：只比两边都认得的 npcId，野外 NPC 不算 DF 差异） ----
    df_path = os.path.join(UP, "df-dungeon-loot.json")
    df_pairs, df_npc_total = set(), 0
    df_unread = ""
    if os.path.exists(df_path):
        df = json.loads(io.open(df_path, encoding="utf-8").read())
        for d in df.get("dungeons") or []:
            for b in d.get("bosses") or []:
                npc = b.get("npcId")
                if npc is None:
                    continue
                df_npc_total += 1
                for it in b.get("itemIds") or []:
                    df_pairs.add((int(npc), int(it)))
    shared_npcs = {n for n, _ in all_pairs} & {n for n, _ in df_pairs}
    q_on_shared = {(n, i) for n, i in all_pairs if n in shared_npcs}
    d_on_shared = {(n, i) for n, i in df_pairs if n in shared_npcs}
    both = q_on_shared & d_on_shared
    counts = {
        "wowheadBlocks": wow_blocks, "wowheadPairs": len(wow_pairs),
        "correctionBlocks": corr_blocks, "correctionPairs": len(corr_pairs),
        "correctionOnlyPairs": len(corr_pairs - wow_pairs),
        "pairs": len(all_pairs),
        "distinctNpcs": len({n for n, _ in all_pairs}),
        "distinctItems": len({i for _, i in all_pairs}),
        "dfPairs": len(df_pairs), "dfBossRows": df_npc_total,
        "sharedNpcBridgedPairs": len(both),
        "questieOnlyOnSharedNpcs": len(q_on_shared - d_on_shared),
        "dfOnlyOnSharedNpcs": len(d_on_shared - q_on_shared),
    }

    print("QuestieDB 掉落表：wowhead 自动表 %d 块 / %d 对；人工修正 %d 块 / %d 对（其中只出现在修正里 %d 对）"
          % (wow_blocks, len(wow_pairs), corr_blocks, len(corr_pairs), counts["correctionOnlyPairs"]))
    print("合计 %d 对（%d 个 NPC × %d 个物品）" % (counts["pairs"], counts["distinctNpcs"], counts["distinctItems"]))
    if df_pairs:
        print("与 DF 掉落快照对拍（npcId 桥，共同 NPC %d 个）：归属两源都认 %d 对；只 Questie 有 %d 对；只 DF 有 %d 对"
              % (len(shared_npcs), counts["sharedNpcBridgedPairs"],
                 counts["questieOnlyOnSharedNpcs"], counts["dfOnlyOnSharedNpcs"]))
    else:
        print("（没找到 df-dungeon-loot.json，跳过对拍）%s" % df_unread)

    if "--show" in sys.argv:
        return

    # 落盘按 npcId 归组：首领掉落消费方（副本页）天然按 NPC 查。
    by_npc = {}
    for n, i in sorted(all_pairs):
        by_npc.setdefault(n, []).append(i)
    snap = {
        "meta": {
            "source": "%s（QuestieDB，support/Forever/DropTables/）classicItemDrops.lua + itemDropCorrections.lua"
                      % DB_ADDON,
            "addon": DB_ADDON,
            "sourceFiles": ["%s/classicItemDrops.lua" % DROP_DIR, "%s/itemDropCorrections.lua" % DROP_DIR],
            "sourceStamp": {"classicItemDrops": stamp(drops_path), "itemDropCorrections": stamp(corr_path)},
            "fetched": datetime.date.today().isoformat(),
            "took": "itemID→npcID 的掉落归属对（方向统一为 npcId → itemIds 升序去重）",
            "droppedFields": ["掉率数值（wowhead float）——本站红线：掉落不写百分比",
                              "DropKeys 引用与修正说明——只当「归属成立」用",
                              "注释里的物品英文名——wowhead 转述命名，本站名录已有自己的名字层"],
            "boundary": "文件自述由 wowhead 数据自动生成（objective 数据）。与 df-dungeon-loot、wclbox 系并列第三家，"
                        "分歧都留；快照不进成品，要不要并进 dungeons.json 由合并层决定。",
            "decodeNote": "classicItemDrops 是 [[return {...}]] 长字符串，正则按 [itemId]={…} 块与 [npcId]=值 行抽取；"
                          "掉率 float 与 DropKeys.WOWHEAD 引用两类值都只读键名",
            "counts": counts,
        },
        "npcs": [{"npcId": n, "itemIds": v} for n, v in sorted(by_npc.items())],
    }
    if not os.path.isdir(UP):
        os.makedirs(UP)
    p = os.path.join(UP, "questie-item-drops.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("写 %s（%.1f KB）" % (os.path.relpath(p, WEB), os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
