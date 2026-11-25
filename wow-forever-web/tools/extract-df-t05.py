#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 DungeonsForeverClass/Core/Data/Data_PrepT05.lua 提取 60 级 T0.5 套装升级任务链。
仅取阵营、职业、阶段、等级、区域、奖励物品ID、任务ID与NPC起止坐标等事实字段；
显式丢弃作者写的阶段心得 note 与任务指引正文 go。"""
import argparse
import datetime
import os
import sys

from addons_root import resolve, explain
from lua_lit import UPSTREAM, assert_no_percent, file_stamp, parse_assignment, toc_version, write_snapshot

ADDON = "DungeonsForeverClass"
REL = ADDON + "/Core/Data/Data_PrepT05.lua"


def resolve_src(given):
    for c in (given, os.environ.get("WOW_ADDONS")):
        if c and os.path.isfile(os.path.join(c, REL)):
            return c
    root = resolve(ADDON)
    if os.path.isfile(os.path.join(root, REL)):
        return root
    sys.exit("找不到 %s：%s\n%s" % (ADDON, REL, explain()))


def clean_quest(q):
    out = {
        "id": int(q["id"]),
        "name": q["q"],
        "side": q.get("s", ""),
        "suggestLevel": int(q["sl"]) if q.get("sl") else None,
        "fromNpc": q.get("f", ""),
        "fromLoc": q.get("fl", ""),
        "fromNpcId": int(q["fn"]) if q.get("fn") else None,
        "toNpc": q.get("t", ""),
        "toLoc": q.get("tl", ""),
        "toNpcId": int(q["tn"]) if q.get("tn") else None,
    }
    if q.get("rw"):
        out["rewardItems"] = [int(x) for x in q["rw"]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out-dir", default=UPSTREAM)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    src = resolve_src(args.src)
    path = os.path.join(src, REL)
    text = open(path, encoding="utf-8").read()
    raw = parse_assignment(text, r"ns\.ClassPrepT05\s*=\s*\{")

    chains = []
    quest_ids, item_ids = set(), set()
    for side in ("A", "H"):
        cls_map = raw.get(side) or {}
        for cls, stages_raw in cls_map.items():
            stages = []
            for st_idx in sorted(stages_raw.keys(), key=int):
                st = stages_raw[st_idx]
                rew = [int(x) for x in (st.get("rew") or [])]
                item_ids.update(rew)
                flow = [clean_quest(q) for q in (st.get("flow") or [])]
                for q in flow:
                    quest_ids.add(q["id"])
                    item_ids.update(q.get("rewardItems") or [])
                stages.append({
                    "stage": int(st_idx),
                    "name": st["name"],
                    "level": int(st["lv"]),
                    "zone": st["zone"],
                    "rewardItems": rew,
                    "quests": flow,
                })
            chains.append({"side": side, "class": cls.lower(), "stages": stages})

    ver = toc_version(src, ADDON)
    doc = {
        "meta": {
            "source": "%s %s Core/Data/Data_PrepT05.lua" % (ADDON, ver),
            "addon": ADDON,
            "addonVersion": ver,
            "fetched": datetime.date.today().isoformat(),
            "levelStatus": "L1",
            "droppedFields": ["各阶段 note 攻略解说句", "每条任务 go 指引正文（避免复制第三方任务描述）"],
            "sourceFiles": {REL: file_stamp(path)},
            "counts": {
                "chains": len(chains),
                "stages": sum(len(c["stages"]) for c in chains),
                "questSteps": sum(len(s["quests"]) for c in chains for s in c["stages"]),
                "distinctQuests": len(quest_ids),
                "distinctRewardItems": len(item_ids),
            },
        },
        "chains": chains,
    }
    assert_no_percent(doc, "df-prep-t05")
    c = doc["meta"]["counts"]
    print("DF T0.5 任务链：%d 条（阵营×职业）/ %d 阶段 / %d 任务步（%d 去重任务 ID，%d 奖励物品）" % (
        c["chains"], c["stages"], c["questSteps"], c["distinctQuests"], c["distinctRewardItems"]))
    if args.show:
        return
    out = write_snapshot(args.out_dir, "df-prep-t05.json", doc)
    print("写 %s（%.1f KB）" % (out, os.path.getsize(out) / 1024.0))


if __name__ == "__main__":
    main()
