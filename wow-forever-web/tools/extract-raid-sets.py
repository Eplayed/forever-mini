#!/usr/bin/env python3
"""从 DungeonsForever/Core/Data/Data_RaidSets.lua 提取 60 级海加尔峰 T1 团本套装（9 职业 18 套），
输出结构化上游快照 wow-forever-web/app/data/upstream/df-raid-sets.json。

遵守 AGENTS.md 第五章红线：
- 只取事实性标识符（套装 ID、职业、专精/定位、护甲类型、中文套装名、部件数与客户端物品 ID）；
- 不复制技能效果描述文案，不含百分比（部件散件属性待 12 月海加尔峰正式开放后实测核对）。
"""
import json
import os
import re
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAID_SETS_LUA = r"C:\GAME\World of Warcraft\_forever_\Interface\AddOns\DungeonsForever\Core\Data\Data_RaidSets.lua"
OUT_PATH = os.path.join(ROOT, "app", "data", "upstream", "df-raid-sets.json")

CLS_CN = {
    "WARRIOR": ("warrior", "战士"),
    "PALADIN": ("paladin", "圣骑士"),
    "HUNTER": ("hunter", "猎人"),
    "ROGUE": ("rogue", "潜行者"),
    "PRIEST": ("priest", "牧师"),
    "SHAMAN": ("shaman", "萨满祭司"),
    "MAGE": ("mage", "法师"),
    "WARLOCK": ("warlock", "术士"),
    "DRUID": ("druid", "德鲁伊"),
}

ROLE_CN = {"dps": "输出", "tank": "坦克", "heal": "治疗"}


def main():
    with open(RAID_SETS_LUA, encoding="utf-8") as f:
        lua = f.read()

    upd_m = re.search(r'updated\s*=\s*"([^"]+)"', lua)
    raid_m = re.search(r'raid\s*=\s*"([^"]+)"', lua)
    updated = upd_m.group(1) if upd_m else "2026-10-08"
    raid_cn = raid_m.group(1) if raid_m else "海加尔峰"

    pat = re.compile(
        r'\{\s*class\s*=\s*"([A-Z]+)"\s*,\s*id\s*=\s*(\d+)\s*,\s*role\s*=\s*"([a-z]+)"\s*,'
        r'\s*spec\s*=\s*"([^"]+)"\s*,\s*armor\s*=\s*"([^"]+)"\s*,.*?'
        r'name\s*=\s*"([^"]+)"\s*,\s*ids\s*=\s*\{([^}]+)\}',
        re.S,
    )

    sets_out = []
    for m in pat.finditer(lua):
        cls_raw, sid, role, spec, armor, name, ids_raw = m.groups()
        cls, cls_cn = CLS_CN[cls_raw]
        piece_ids = [int(x.strip()) for x in ids_raw.split(",") if x.strip()]
        sets_out.append(OrderedDict([
            ("id", "t1-" + sid),
            ("setId", int(sid)),
            ("cls", cls),
            ("clsCn", cls_cn),
            ("role", role),
            ("roleCn", ROLE_CN.get(role, role)),
            ("spec", spec),
            ("armor", armor),
            ("name", name),
            ("raid", raid_cn),
            ("level", 60),
            ("pieceCount", len(piece_ids)),
            ("pieceIds", piece_ids),
            ("fetched", updated),
        ]))

    doc = OrderedDict([
        ("meta", OrderedDict([
            ("source", "DungeonsForever/Core/Data/Data_RaidSets.lua"),
            ("raid", raid_cn),
            ("updated", updated),
            ("grade", "L1"),
            ("note", "Beta 客户端套装散件基础属性尚隐藏，仅记录套装标识、定位、护甲及部件数（无套装效果文案与百分比）"),
            ("count", len(sets_out)),
        ])),
        ("raidSets", sets_out),
    ])

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("已生成 %s：%d 套 %s T1 套装" % (OUT_PATH, len(sets_out), raid_cn))


if __name__ == "__main__":
    main()
