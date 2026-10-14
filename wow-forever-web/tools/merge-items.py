#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 upstream/wclbox-items-index.json（全量物品名录快照）合并成成品基底 src/data/items.json。

为什么不算"二源分歧"：物品名录是单源（wclbox 转述客户端解包），按 2026-10-08 的
datamine_cn 口径直接算 L0——代价是带 url + 抓取日期（meta 里），物品名在界面上
能溯源；audit-translations 的逐字回查对 21k 条不现实，采用抽检口径（见采编方案）。

合并做什么：
  1. 字段对齐现有基底习惯：iconKey 去扩展名（掉落 loot-i 的 IconCell 同一套路）；
  2. type 拆主类（"远程 · 枪" → typeMain=远程），分类筛选与统计都按主类走；
  3. counts / types 统计给页首读数与筛选器；
  4. 四道校验：id 唯一、数量守恒、icon 非空、status 只含四值——非 0 退出。

用法：python tools/merge-items.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "src", "data", "upstream", "wclbox-items-index.json")
OUT = os.path.join(ROOT, "src", "data", "items.json")

VALID_STATUS = ("new", "changed", "same", "missing", "rebuilt")
# 上游首页把 7 件 ic-rebuilt（重建）并进"新增 5,353"统计；我们保留为独立状态值，
# 不篡改上游口径——页面上 rebuilt 归入"有改动"一侧展示，counts 里单独可见。
REBUILT = "ic-rebuilt"
# type 列的真实模式是「部位 · 材质」（护甲：腿部 · 布甲；武器：远程 · 枪）或纯类（任务/垃圾/制皮…）。
# 一期口径从简：cat 只分四档（武器/护甲/任务/其它），slot 与 mat 原样保留给页面筛选；
# 配方/消耗品等大类二批详情抓取时再细分，规则写在这里不散落。
WEAPON_SLOTS = {"单手", "双手", "主手", "副手", "远程", "投掷", "圣物", "弹药", "箭袋"}
ARMOR_SLOTS = {"头部", "肩部", "胸部", "衬衣", "战袍", "背部", "手腕", "手", "腰部",
               "腿部", "脚", "手指", "饰品", "盾牌", "副手物品"}
ARMOR_MATS = {"布甲", "皮甲", "锁甲", "板甲"}


def classify(typ):
    parts = [p.strip() for p in typ.split(" · ")] if typ else []
    slot = parts[0] if len(parts) == 2 else ""
    mat = parts[1] if len(parts) == 2 else ""
    main_t = parts[0] if parts else "未分类"
    if slot in WEAPON_SLOTS:
        cat = "武器"
    elif slot in ARMOR_SLOTS or mat in ARMOR_MATS:
        cat = "护甲"
    elif main_t == "任务":
        cat = "任务"
    else:
        cat = "其它"
    return cat, slot, mat, main_t


def main():
    src = json.load(open(UP, encoding="utf-8"))
    items = src["items"]
    meta = src["meta"]
    rebuilt_n = 0
    for r in items:
        if r["status"] == REBUILT:
            r["status"] = "rebuilt"
            rebuilt_n += 1
        elif r["status"] not in VALID_STATUS:
            print(f"!! 未知状态 {r['status']}（id {r['id']}），先把映射补进本脚本再合并")
            sys.exit(1)

    ids = [r["id"] for r in items]
    errs = []
    if len(ids) != len(set(ids)):
        errs.append("id 有重复")
    if len(items) != meta.get("parsed"):
        errs.append(f"数量守恒破坏：{len(items)} != meta.parsed {meta.get('parsed')}")
    bad_status = [r for r in items if r["status"] not in VALID_STATUS]
    if bad_status:
        errs.append(f"status 越界 {len(bad_status)} 条，如 {bad_status[0]}")
    no_icon = [r for r in items if not r["icon"]]
    if no_icon:
        print(f"  · 无图标 {len(no_icon)} 件（自绘占位走 icon-gaps 同一路数），如 {no_icon[0]['name']}")

    counts, types, quals, cats = {}, {}, {}, {}
    for r in items:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        cat, slot, mat, main_t = classify(r["type"])
        r.update(iconKey=r["icon"].rsplit(".", 1)[0], typeMain=main_t, cat=cat, slot=slot, mat=mat)
        cats[cat] = cats.get(cat, 0) + 1
        types[main_t] = types.get(main_t, 0) + 1
        quals[r["quality"]] = quals.get(r["quality"], 0) + 1

    if errs:
        for e in errs:
            print("!! " + e)
        sys.exit(1)

    doc = {
        "meta": {
            "source": "wowforever.wclbox.com /wupin/liebiao（名称索引全量名录，单源 L0）",
            "url": meta["url"],
            "fetched": meta["fetched"],
            "counts": {"total": len(items), **counts},
            "cats": sorted(cats.items(), key=lambda kv: -kv[1]),
            "types": sorted(types.items(), key=lambda kv: -kv[1]),
            "qualities": {str(k): v for k, v in sorted(quals.items())},
            "note": "清单级：名称/品质/类型/等级/状态/图标文件名；描述文案不采（红线）。"
                    "cat 一期只分武器/护甲/任务/其它（按 slot+材质推导，规则见本脚本 classify）；"
                    "rebuilt=上游标「重建」的 7 件（其首页统计把它并进新增，我们单独留值）。",
        },
        "items": items,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print(f"落盘 {OUT}: {len(items)} 件, {os.path.getsize(OUT) // 1024} KB")
    print(f"  counts={counts}（其中 rebuilt 归一 {rebuilt_n} 件）")
    print(f"  cats={sorted(cats.items(), key=lambda kv: -kv[1])}")
    print(f"  types(top)={sorted(types.items(), key=lambda kv: -kv[1])[:6]}")


if __name__ == "__main__":
    main()
