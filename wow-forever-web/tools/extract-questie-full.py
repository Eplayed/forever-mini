#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本机 QuestieDB 插件的 baked TOC 抽"任务全量字段"快照，落 upstream/questie-quests-full.json。

背景（2026-11-09 站主"任务在哪接的"第二轮）：
  既有快照 questie-quests-cn.json 只有 id/en/cn 三个字段（当时只为了译名），
  副本任务 396 条里 60 条没接取人、96 条没地点，wclbox 源本身就是空的。
  这次把 baked TOC 里 startBy（field 2）、zoneOrSort（field 17）、等级（field 4/5）
  与 NPC 名表一并抽出，给 merge-dungeon-quests.py 当第四源补空缺。

TOC 行格式（extract-questie-quests-cn.py 已验证的同一套）：
  ## X-Quest-<id>-S: <b64(cbor)>    —— 稀疏标量 map，键是字段号：1=英文名 4=最低等级 5=任务等级 17=zoneOrSort
  ## X-Quest-<id>-2: <b64(cbor)>    —— startBy 单独一行。形状直方图（5,059 行全量扫过）：
        [[int..]]                     = [npc..]
        [[..],[..],[..]]              = [npc表, 物品表, 任务物品表] 位置数组（None=空）
        [None,[int..]]                = 物品表为 object（游戏物体）
        {3:[int..]}                   = 字典变体，键 3=任务物品
      本工具统一拆成 startedByNpc / startedByObject / startedByItem 三列，判读依据写在 counts 里。
  ## X-Npc-<id>-S: <b64(cbor)>      —— NPC 名（键 1=英文）
  中文名不从本 TOC 来：zhCN 列在 BaiYunFeiQuestieCN（既有快照 questie-quests-cn.json 的
  quests[].cn 与 npcNames[]），这里按 questID 对齐进 NPC 与任务行，cnVia 记快照身份。

只取事实性标识符（名称/ID/等级/zone 编号/接取归属）；任务目标文案（field 8）、
奖励、建议等级等一概不抽。用法：python3 tools/extract-questie-full.py
"""
import base64
import hashlib
import importlib.util
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "app", "data")
CN_SNAP = os.path.join(D, "upstream", "questie-quests-cn.json")
OUT = os.path.join(D, "upstream", "questie-quests-full.json")
TOC_DEFAULT = r"C:\GAME\World of Warcraft\_forever_\Interface\AddOns\QuestieDB\QuestieDB_Forever.toc"


def load_cbor():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "extract_questie_quests_cn", os.path.join(here, "extract-questie-quests-cn.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, here)  # 该脚本会 from addons_root import resolve/explain
    spec.loader.exec_module(mod)
    return mod.cbor


def txt(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace").strip() or None
    if isinstance(v, str):
        return v.strip() or None
    return None


def split_started_by(v):
    """field2 统一拆三列：位置数组 [npc, object, item] 或字典变体 {1/2/3: [..]}。"""
    npc, obj, item = [], [], []
    if isinstance(v, dict):
        for k, lst in v.items():
            ids = [x for x in (lst or []) if isinstance(x, int) and 0 < x < 300000]
            if k == 1:
                npc = ids
            elif k == 2:
                obj = ids
            else:
                item = ids
    elif isinstance(v, list):
        # 位置数组：[npc, object, item]；None=空位
        pos = v if any(e is not None for e in v[1:]) else [v[0], None, None]
        if len(pos) == 3:
            npc = [x for x in (pos[0] or []) if isinstance(x, int) and 0 < x < 300000]
            obj = [x for x in (pos[1] or []) if isinstance(x, int) and 0 < x < 300000]
            item = [x for x in (pos[2] or []) if isinstance(x, int) and 0 < x < 300000]
        else:  # 兜底：单表全当 npc（形状直方图里没有这种，出现就显著计数核对）
            npc = [x for x in v if isinstance(x, int) and 0 < x < 300000]
    return npc, obj, item


def main():
    toc_path = sys.argv[1] if len(sys.argv) > 1 else TOC_DEFAULT
    if not os.path.exists(toc_path):
        sys.stderr.write("找不到 QuestieDB baked TOC：%s\n（本机路径由 addons_root / 插件目录决定，换机要显式传）\n" % toc_path)
        return 2
    cbor = load_cbor()
    raw = open(toc_path, "rb").read()

    cn_doc = json.load(io.open(CN_SNAP, encoding="utf-8"))
    cn_by_id = {q["id"]: q.get("cn") for q in cn_doc.get("quests", [])}
    npc_cn = {n["npcId"]: n.get("nameCn") for n in cn_doc.get("npcNames", [])}

    S, SB, NPCEN = {}, {}, {}
    for line in raw.split(b"\n"):
        if not line.startswith(b"## "):
            continue
        t = line[3:].decode("utf-8", "replace")
        m = re.match(r"X-Quest-(\d+)-S: (.+)$", t)
        if m:
            rr = cbor(base64.b64decode(m.group(2).strip()))
            if isinstance(rr, dict):
                S[int(m.group(1))] = {
                    "en": txt(rr.get(1)),
                    "reqLevel": rr.get(4) if isinstance(rr.get(4), int) else None,
                    "questLevel": rr.get(5) if isinstance(rr.get(5), int) else None,
                    "zone": rr.get(17) if isinstance(rr.get(17), int) else None,
                }
            continue
        m = re.match(r"X-Quest-(\d+)-2: (.+)$", t)
        if m:
            SB[int(m.group(1))] = cbor(base64.b64decode(m.group(2).strip()))
            continue
        m = re.match(r"X-Npc-(\d+)-S: (.+)$", t)
        if m:
            rr = cbor(base64.b64decode(m.group(2).strip()))
            if isinstance(rr, dict) and 1 in rr:
                NPCEN[int(m.group(1))] = txt(rr[1])

    quests, npcs, n_npc_en = [], [], 0
    for qid in sorted(set(S) | set(SB)):
        s = S.get(qid) or {}
        npc, obj, item = split_started_by(SB.get(qid)) if qid in SB else ([], [], [])
        quests.append({
            "id": qid,
            "en": s.get("en") or cn_by_id.get(qid) and None,  # en 只认 TOC 原文，缺就空
            "cn": cn_by_id.get(qid),
            "questLevel": s.get("questLevel"),
            "reqLevel": s.get("reqLevel"),
            "zone": s.get("zone"),
            "startedByNpc": npc,
            "startedByObject": obj,
            "startedByItem": item,
        })
    for nid, en in NPCEN.items():
        npcs.append({"npcId": nid, "en": en, "cn": npc_cn.get(nid)})
        n_npc_en += 1

    shape_dict = sum(1 for v in SB.values() if isinstance(v, dict))
    doc = {
        "meta": {
            "source": "QuestieDB（QuestieDB_Forever.toc baked metadata store，startBy/zoneOrSort/等级 + Npc 名）"
                      "＋中文名与 NPC 中文名沿用 BaiYunFeiQuestieCN 快照（questie-quests-cn.json）",
            "sourceFile": toc_path,
            "sourceStamp": {
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            "cnSnapshot": "app/data/upstream/questie-quests-cn.json",
            "extractedAt": "2026-11-09",
            "takes": "只取事实性标识符：任务英文名、等级、zone 编号、接取归属（npc/object/item 的 ID），"
                     "NPC 英文名；中文译名沿用既有快照。任务目标文案（field 8）、奖励、建议一概不抽",
            "startedByShape": "位置数组 [npc表, 物品表(object), 任务物品表]；字典变体 %d 行按键 1/2/3 同义拆列" % shape_dict,
            "counts": {
                "quests": len(quests),
                "withEn": sum(1 for q in quests if q["en"]),
                "withCn": sum(1 for q in quests if q["cn"]),
                "withStartedBy": sum(1 for q in quests if q["startedByNpc"] or q["startedByObject"] or q["startedByItem"]),
                "withZone": sum(1 for q in quests if q["zone"]),
                "npcs": len(npcs),
                "npcsEn": n_npc_en,
                "npcsCn": sum(1 for n in npcs if n["cn"]),
            },
        },
        "quests": quests,
        "npcs": npcs,
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    c = doc["meta"]["counts"]
    print("已写 questie-quests-full.json：任务 %d（有英文名 %d / 中文名 %d / 接取归属 %d / zone %d）；NPC %d（英 %d / 中 %d）" % (
        c["quests"], c["withEn"], c["withCn"], c["withStartedBy"], c["withZone"], c["npcs"], c["npcsEn"], c["npcsCn"]))


if __name__ == "__main__":
    sys.exit(main() or 0)
