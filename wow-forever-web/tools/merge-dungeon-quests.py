#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把上游任务数据合成成品文件 app/data/dungeon-quests.json。

站主 2026-10-13 定的优先级：**wclbox 为准，wclbox 没有的按 wowhead 来。**
落成三条规则（都在这个脚本里，页面不参与判断）：
  1. 一条任务的经验值 wclbox 有、wowhead 也有且不一样 → 用 wclbox 的，
     wowhead 那个原样留在 xpAlt 里（分歧不许被覆盖掉，溯源页交代）。
  2. wclbox 根本没给这个字段（新本的经验值全是空的）→ 用 wowhead 的，标 xpFrom=wowhead。
  3. wclbox 没列、wowhead 有的任务（洛丹伦废墟的「憎恶生物」）→ 补进来，标 source=wowhead。

2026-10-14 加第三源（PLAN 第 4 节，只补空任务座）：wclbox 与 wowhead 都没有任务的两座
（维尔加挖掘场 / 达拉然城），用 GearInsight_Forever 的 DungeonQuestData 补——它是
Wowhead Forever 1.60.1 经 Dungeon Assistant 转手的转述源，中文名 vmangos+游戏内现读
（判定见 docs/wow-infinite-sources.md 第十四节）。**只补空座，已有数据的座不掺 GI**：
lbrs/ubrs 站内更全，ragefire 等级已按官方值定稿，掺了反而降级。wowhead 直采这两座
zone 页时任务名多为方括号「未记录」串（见 upstream/wowhead-dungeon-quests.json 的
collectedButNotUsable），所以空座只能走这条转述源。GI 没给经验值（xp=0 是占位），
经验列留空不造假。

顺带做两件清洗，都是上游原样搬上页面会出问题的地方：
  - wclbox 把"用物品开启的任务"的接取人写成「物品：憎恶头颅」——那不是 NPC，拆成 startItem。
  - 表格里一个单元格塞了两行（"归还背包\\n部落"）——拆成 quest + faction，别在页面上留换行。
  - 完全相同的任务行重复出现（洛丹伦废墟「无尽的折磨」三条一字不差）——合成一条并记 variants。

用法：python3 tools/merge-dungeon-quests.py
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "app", "data")
WCL = os.path.join(D, "upstream", "wclbox-dungeon-quests.json")
WH = os.path.join(D, "upstream", "wowhead-dungeon-quests.json")
GIQ = os.path.join(D, "upstream", "gi-dungeon-quests.json")
# GI 座键 → (wclbox 上游 slug, Wowhead Forever zone 页 url)。zone id 是站内直采时
# 实测记下的（upstream/wowhead-dungeon-quests.json collectedButNotUsable）；url 挂
# 数据系源头（Wowhead Forever 1.60.1），实际取数渠道是 GI 插件转述，见 provenance note。
GI_SEATS = {
    "excavation": ("excavation-site", "https://www.wowhead.com/forever/zone=16732/x"),
    "dalaran": ("city-of-dalaran", "https://www.wowhead.com/forever/zone=16544/x"),
}
GI_SEATS_BY_WCL = {v[0]: (k, v[1]) for k, v in GI_SEATS.items()}
OUT = os.path.join(D, "dungeon-quests.json")


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def norm(v):
    if v is None:
        return None
    s = re.sub(r"\s+", " ", str(v)).strip()
    return s or None


def split_cell(v):
    """'归还背包\\n部落' → ('归还背包', '部落')"""
    if not v:
        return None, None
    parts = [p.strip() for p in re.split(r"[\n\r]+", str(v)) if p.strip()]
    if not parts:
        return None, None
    faction = None
    for p in parts[1:]:
        if p in ("联盟", "部落", "双方"):
            faction = p
    return parts[0], faction


def clean_quest(q):
    npc = norm(q.get("pickupNpc"))
    start_item = None
    if npc and (npc.startswith("物品：") or npc.startswith("物品:")):
        start_item = re.sub(r"^物品[：:]", "", npc).strip()
        npc = None
    return {
        "nameCn": norm(q.get("name")),
        "questLevel": q.get("questLevel"),
        "reqLevel": q.get("reqLevel"),
        "xp": q.get("xp"),
        "pickupNpc": npc,
        "pickupZone": norm(q.get("pickupZone")),
        "startItem": start_item,
        "preQuest": norm(q.get("preQuest")),
        "source": "wclbox",
    }


def clean_gi_quest(q):
    """GI DungeonQuestData 的任务行。xp=0 是它没给经验值的占位，不是 0 经验，
    一律转成 None（页面缺格留空的口径），不造假。英文名它逐条自带。"""
    npc = norm(q.get("pickupNpc"))
    start_item = None
    if npc and (npc.startswith("物品：") or npc.startswith("物品:")):
        start_item = re.sub(r"^物品[：:]", "", npc).strip()
        npc = None
    xp = q.get("xp")
    if xp == 0:
        xp = None
    return {
        "nameCn": norm(q.get("name")),
        "nameEn": norm(q.get("nameEn")),
        "questLevel": q.get("questLevel"),
        "reqLevel": q.get("reqLevel"),
        "xp": xp,
        "pickupNpc": npc,
        "pickupZone": norm(q.get("pickupZone")),
        "startItem": start_item,
        "preQuest": norm(q.get("preQuest")),
        "source": "gi",
        "variants": 1,
    }


def main():
    wcl = load(WCL)
    wh = load(WH)
    gi = load(GIQ)
    gi_meta = gi.get("meta") or {}
    dg = load(os.path.join(D, "dungeons.json"))
    by_slug = {}
    for row in (dg.get("newDungeons") or []) + (dg.get("classicDungeons") or []):
        by_slug[row.get("upstreamSlug") or row["id"]] = row["id"]

    wh_by_dungeon = {}
    for z in wh.get("zones") or []:
        wh_by_dungeon[z.get("matchedDungeonId")] = z

    out = {}
    st = {"dungeons": 0, "quests": 0, "fromWowhead": 0, "addedFromWowhead": 0,
          "xpKept": 0, "xpAlt": 0, "deduped": 0, "itemStart": 0, "fromGi": 0}

    for slug, raw in (wcl.get("dungeons") or {}).items():
        our_id = by_slug.get(slug)
        if not our_id:
            sys.stderr.write("跳过 %s：dungeons.json 里没有这座本\n" % slug)
            continue
        whz = wh_by_dungeon.get(our_id) or {}
        wh_quests = whz.get("quests") or []

        quests = []
        seen = {}
        for q in raw.get("quests") or []:
            c = clean_quest(q)
            if c["startItem"]:
                st["itemStart"] += 1
            key = json.dumps(c, ensure_ascii=False, sort_keys=True)
            if key in seen:
                seen[key]["variants"] = (seen[key].get("variants") or 1) + 1
                st["deduped"] += 1
                continue
            c["variants"] = 1
            # 同名的 wowhead 任务：补 wclbox 缺的字段；两边都有但数不一样，留档不覆盖
            m = None
            for h in wh_quests:
                if norm(h.get("name")) == c["nameCn"]:
                    m = h
                    break
            if m:
                if c["xp"] is None and m.get("xp") is not None:
                    c["xp"] = m["xp"]
                    c["xpFrom"] = "wowhead"
                    st["fromWowhead"] += 1
                elif c["xp"] is not None and m.get("xp") is not None and c["xp"] != m["xp"]:
                    c["xpAlt"] = m["xp"]
                    c["xpAltFrom"] = "wowhead"
                    st["xpAlt"] += 1
                else:
                    st["xpKept"] += 1
                if c["reqLevel"] is None and m.get("reqLevel") is not None:
                    c["reqLevel"] = m["reqLevel"]
                    c["reqFrom"] = "wowhead"
                if not c.get("pickupNpc") and not c.get("pickupZone") and m.get("nameEn"):
                    c["nameEn"] = m["nameEn"]
            quests.append(c)
            seen[key] = c

        # 同名任务合并成一条（站主 2026-10-13 就「无尽的折磨」定的做法，推广到全部）：
        # 留信息最全的那一行——有接取人又有地点的优先，其次看有没有经验值。
        # 被合掉的那些不删干净，条数记在 variants 里留在数据中，只是页面上不再出现
        # "同一任务 N 个版本"这种给维护者看的话。
        merged, byName = [], {}
        for y in quests:
            k = y.get("nameCn")
            if k not in byName:
                byName[k] = y
                merged.append(y)
                continue
            cur, new = byName[k], y
            score = lambda v: (1 if v.get("pickupNpc") else 0) + (1 if v.get("pickupZone") else 0) \
                + (1 if v.get("xp") is not None else 0) + (1 if v.get("reqLevel") is not None else 0)
            cur["variants"] = (cur.get("variants") or 1) + 1
            if score(new) > score(cur):
                new["variants"] = cur["variants"]
                merged[merged.index(cur)] = new
                byName[k] = new
                st["deduped"] += 1
            else:
                st["deduped"] += 1
        quests = merged

        # wclbox 整条没列、wowhead 有的任务，补在最后并标来源
        have = set(q["nameCn"] for q in quests)
        for m in wh_quests:
            nm = norm(m.get("name"))
            if not nm or nm in have or nm.startswith("["):
                continue
            quests.append({"nameCn": nm, "nameEn": norm(m.get("nameEn")),
                           "questLevel": m.get("questLevel"), "reqLevel": m.get("reqLevel"),
                           "xp": m.get("xp"), "pickupNpc": None, "pickupZone": None,
                           "startItem": None, "preQuest": None, "variants": 1,
                           "source": "wowhead"})
            st["addedFromWowhead"] += 1

        # GI 补空任务座（2026-10-14 PLAN 第 4 节）：wclbox 与 wowhead 都是 0 的两座，
        # 用 GearInsight_Forever DungeonQuestData 整座填上。只动空座——已有数据的座
        # 不掺（lbrs/ubrs 站内更全，ragefire 等级已按官方值定稿）。
        gi_seat = GI_SEATS_BY_WCL.get(slug)
        gi_used = False
        if not quests and gi_seat:
            gi_key, _zone_url = gi_seat
            gi_d = (gi.get("dungeons") or {}).get(gi_key) or {}
            for q in gi_d.get("quests") or []:
                quests.append(clean_gi_quest(q))
                st["fromGi"] += 1
            if quests:
                gi_used = True

        items = []
        for it in raw.get("questItems") or []:
            qn, fac = split_cell(it.get("对应任务"))
            items.append({"itemCn": norm(it.get("物品")), "from": norm(it.get("获取来源")),
                          "quest": qn, "faction": fac})
        starts = []
        for s in raw.get("questStarts") or []:
            qn, fac = split_cell(s.get("任务"))
            starts.append({"npc": norm(s.get("任务发布者")), "zone": norm(s.get("位置")),
                           "quest": qn, "faction": fac})

        if gi_used:
            wcl_note = "该站此座任务表为空（无记录），任务数据按下一条转述源补齐"
        elif quests:
            wcl_note = "任务名、任务等级、最低接取等级、经验值、接取人与地点取自该站的副本详情页（客户端解包转述）"
        else:
            wcl_note = "该站此座没有任务记录，两份资料与转述源都没有"
        prov = [{"type": "datamine_cn", "url": raw.get("url"),
                 "note": wcl_note,
                 "checkedAt": wcl.get("meta", {}).get("scrapedAt")}]
        if whz and any(q.get("xpFrom") == "wowhead" or q.get("source") == "wowhead" for q in quests):
            prov.append({"type": "datamine_en", "url": whz.get("url"),
                         "note": "wclbox 没给的那几项经验值与任务，按站主定的顺序退到这份来源",
                         "checkedAt": wh.get("meta", {}).get("collectedAt")})
        if gi_used:
            prov.append({"type": "datamine_cn", "url": gi_seat[1],
                         "note": "任务名/等级/接取人取自 GearInsight_Forever 0.4.29 的 DungeonQuestData"
                                 "（自述源：Wowhead Forever 1.60.1 经 Dungeon Assistant 转手，中文名 vmangos+游戏内现读）。"
                                 "直采该 zone 时任务名多为方括号「未记录」串，故走此转述源；该源没给经验值，经验列留空",
                         "checkedAt": gi_meta.get("fetched")})

        sumq, sumf, sumxp = None, None, None
        s = raw.get("questSummary") or {}
        if s.get("rows"):
            r = s["rows"][0]
            sumf = norm(r[0]) if len(r) > 0 else None
            sumq = None
            sumxp = None
            for cell in r:
                v = norm(cell) or ""
                if re.match(r"^\d+$", v) and sumq is None:
                    sumq = int(v)
                m = re.match(r"^([\d,]+) 点经验值", v)
                if m:
                    sumxp = int(m.group(1).replace(",", ""))

        out[our_id] = {
            "quests": quests, "questItems": items, "questStarts": starts,
            "summary": {"faction": sumf, "questCount": sumq, "xpTotal": sumxp,
                        "note": (s.get("head") and "该站自报的汇总，本站只列它给的数") or None},
            "provenance": prov,
        }
        st["dungeons"] += 1
        st["quests"] += len(quests)

    doc = {
        "meta": {
            "generatedAt": wcl.get("meta", {}).get("scrapedAt"),
            "method": "tools/merge-dungeon-quests.js 合 upstream 任务快照；"
                      "优先级按站主 2026-10-13 的决定：wclbox 为准，wclbox 没有的按 wowhead 来。"
                      "2026-10-14 起空任务座按 PLAN 第 4 节用 GearInsight_Forever DungeonQuestData 补"
                      "（Wowhead Forever 1.60.1 经 Dungeon Assistant 转手，只补空座，经验值该源没给）。",
            "pageNote": "副本任务这块按参考站 wclbox 的数据为准，它没给的项按另一份客户端资料补上；"
                        "个别座（挖掘场/达拉然）两份资料都没有，按 Wowhead 无限服数据的插件转述源补齐。"
                        "任务目标那句话与掉落概率都没采——第三方站只取名称与数字，本站掉落不写概率。"
                        "经验值是经典旧世的数字，无限服可能调整，本站没实测过。",
            "note": "任务目标描述整句与掉落概率刻意没采——第三方站只取事实性标识符，本站掉落不写概率。"
                    "经验值是经典旧世的数字，无限服可能调整，没实测过。"
                    "GI 补的两座任务名来自 vmangos+游戏内现读，不是 wclbox 口径。",
            "counts": {"dungeons": st["dungeons"], "quests": st["quests"],
                       "xpFromWowhead": st["fromWowhead"], "xpConflict": st["xpAlt"],
                       "addedFromWowhead": st["addedFromWowhead"], "deduped": st["deduped"],
                       "itemStart": st["itemStart"], "fromGi": st["fromGi"]}
        },
        "dungeons": out
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    c = doc["meta"]["counts"]
    print("已写 dungeon-quests.json：%d 座 / 任务 %d 条；经验值退到 wowhead %d 条 / 两源不一致留档 %d 条 / "
          "补 wowhead 独有 %d 条 / GI 补空座 %d 条 / 去重合并 %d 条 / 物品开启的任务 %d 条" % (
              c["dungeons"], c["quests"], c["xpFromWowhead"], c["xpConflict"],
              c["addedFromWowhead"], c["fromGi"], c["deduped"], c["itemStart"]))


if __name__ == "__main__":
    main()
