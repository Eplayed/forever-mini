#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 从 GearInsight_Forever/ProfRecipes.lua 抽「配方」这一层，落 upstream 修剪快照。
#
# 为什么开这张（2026-11-01 站主："DF/XR 那几张从未取过的表要开"，GI 这张同批点头）：
#   本站配方 1,990 条全部来自解包资料站的网页列表，**没有"去哪儿能学到、在哪个地图的哪个位置"这一层**；
#   GI 这张每行都带 主出处索引 + 材料清单 + 成品与黄灰等级，出处池里还带地图号与百分比坐标。
#
# 边界（红线，逐条写进快照 meta，合并层再卡一道）：
#   出处池 src 的每一项是 { 全文中文, 全文英文, 短句中文, 短句英文, 地图号, x, y, 阵营 } ——
#   **前四项是插件作者写的句子，一条不落盘**；只取 地图号 / x / y / 阵营 这四个事实位。
#   配方行只取 ID 与数值：法术 ID、中英名、成品物品 ID、黄/灰技能点、需求等级、品质、
#   是否《无限》新增、主出处类型编号、材料 (物品ID, 数量)。
#   GI 目录没有 LICENSE、TOC 也没有 X-License 行，按插件线同一口径整体留 **L1**。
#
# 用法：python3 tools/extract-gi-prof-recipes.py [--src <插件根目录>] [--show]
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(WEB, "app", "data", "upstream")
ADDON = "GearInsight_Forever"
REL = ADDON + "/ProfRecipes.lua"
HOME = os.path.expanduser("~")
# 主出处编号 → 玩家能懂的说法（编号是 GI 文件头自述的口径，不是本站发明的分类）
SOURCE_KIND = {1: "训练师", 2: "商人", 3: "掉落", 4: "声望", 5: "任务", 6: "商人（青睐）", 0: "未记录"}

from addons_root import resolve, explain


def resolve_src(given):
    """--src → WOW_ADDONS → 常见安装位。顺序只维护一份，在 addons_root.py 里。"""
    for c in (given, os.environ.get("WOW_ADDONS")):
        if c and os.path.isdir(os.path.join(c, ADDON)):
            return c
    root = resolve(ADDON)
    if os.path.isdir(os.path.join(root, ADDON)):
        return root
    sys.exit("找不到 %s：给 --src <插件根目录> 或把 WOW_ADDONS 指到 Interface/AddOns\n%s"
             % (ADDON, explain()))


def toc_version(src):
    p = os.path.join(src, ADDON, ADDON + ".toc")
    for line in io.open(p, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*##\s*Version:\s*(\S+)", line)
        if m:
            return m.group(1)
    return "版本未记"


def split_row(s):
    """按顶层逗号切一行 Lua 表（字符串与嵌套大括号里的逗号不算）。"""
    parts, buf, depth, q = [], "", 0, None
    for c in s:
        if q:
            buf += c
            if c == q:
                q = None
            continue
        if c in "\"'":
            q = c
            buf += c
            continue
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        if c == "," and depth == 0:
            parts.append(buf.strip())
            buf = ""
            continue
        buf += c
    if buf.strip():
        parts.append(buf.strip())
    return parts


def unq(s):
    return s.strip().strip('"').replace('\\"', '"')


def inner_braces(s):
    return re.findall(r"\{\s*(\d+)\s*,\s*(\d+)\s*\}", s)


def parse(text):
    """返回 (profs{专业:[配方]}, src[[地图号,x,y,阵营]])。src 的句子位在这一层就丢掉。"""
    i = text.find("ns.ProfRecipes =")
    if i < 0:
        sys.exit("找不到 ns.ProfRecipes 顶层表")
    seg = text[i:]
    # 这个文件只有 5 行，src={{…}} 紧挨着上一个专业的收尾括号，按行首或逗号找都会漏
    k = seg.find("src=")
    src_raw = None
    if k >= 0:
        # 从外层那层括号开始切：从内层条目开始会让 lua_list 把每条的字段当条目切碎
        pos = seg.index("{", k)
        src_raw = seg[pos:brace_end(seg, pos) + 1]
    profs = {}
    for pm in re.finditer(r"\b([a-z_]+)=\{\{", seg):
        key = pm.group(1)
        if key == "src":
            continue
        body = seg[pm.end() - 2:]
        end = brace_end(body, 0)
        profs[key] = body[:end + 1]
    src = []
    if src_raw:
        for item in lua_list(src_raw):
            # lua_list 的第一个条目会把外层括号一起带出来，不剥掉 split_row 会整条当一个字段
            f = split_row(item.strip().strip("{").rstrip("}"))
            # f = [全文中, 全文英, 短句中, 短句英, 地图号, x, y, 阵营]
            if len(f) < 8:
                continue
            ui = f[4].strip()
            src.append({"uiMap": int(ui) if ui.isdigit() else None,
                        "x": float(f[5]) if re.match(r"^-?\d", f[5]) else None,
                        "y": float(f[6]) if re.match(r"^-?\d", f[6]) else None,
                        "faction": (f[7].strip('"') or None)})
    return profs, src


def brace_end(s, start):
    depth, j, q = 0, start, None
    while j < len(s):
        c = s[j]
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
    return len(s) - 1


def lua_list(s):
    """把一个 { a, b, ... } 里的顶层元素切成一条条（每条保留外层花括号）。"""
    out, buf, depth, q, started = [], "", 0, None, False
    for c in s:
        if q:
            buf += c
            if c == q:
                q = None
            continue
        if c in "\"'":
            q = c
            buf += c
            started = True
            continue
        if c == "{":
            depth += 1
            started = True
        if c == "}":
            depth -= 1
        if c == "," and depth == 1:
            if buf.strip():
                out.append(buf.strip())
            buf = ""
            continue
        if started:
            buf += c
    if buf.strip():
        out.append(buf.strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    src = resolve_src(a.src)
    lua = os.path.join(src, ADDON, "ProfRecipes.lua")
    raw = io.open(lua, encoding="utf-8").read()
    b = open(lua, "rb").read()

    blocks, pool = parse(raw)
    recipes = {}
    for prof, block in blocks.items():
        rows = []
        for item in lua_list(block):
            f = split_row(item.strip().strip("{").rstrip("}"))
            if len(f) < 16 or not re.match(r"^\d+$", f[0]):
                continue
            materials = [{"itemId": int(x), "count": int(y)} for x, y in inner_braces(f[14])]
            src_idx = f[15].strip()
            s = pool[int(src_idx) - 1] if src_idx.isdigit() and 0 < int(src_idx) <= len(pool) else None
            rows.append({
                "spellId": int(f[0]),
                "nameCn": unq(f[1]), "nameEn": unq(f[2]),
                "skillMin": int(f[3]) if re.match(r"^\d+$", f[3]) else None,
                "yellow": int(f[4]) if re.match(r"^\d+$", f[4]) else None,
                "gray": int(f[5]) if re.match(r"^\d+$", f[5]) else None,
                "resultItemId": int(f[6]) if re.match(r"^\d+$", f[6]) else None,
                "reqLevel": int(f[7]) if re.match(r"^\d+$", f[7]) else None,
                "quality": int(f[11]) if re.match(r"^\d+$", f[11]) else None,
                "foreverNew": f[12].strip() == "true",
                "sourceKind": SOURCE_KIND.get(int(f[13]) if f[13].strip().isdigit() else -1, None),
                "materials": materials,
                "at": ({"uiMap": s["uiMap"], "x": s["x"], "y": s["y"], "faction": s["faction"]} if s else None),
            })
        recipes[prof] = rows

    total = sum(len(v) for v in recipes.values())
    with_at = sum(1 for v in recipes.values() for r in v if r["at"] and r["at"]["uiMap"])
    print("GI 配方 %d 条 / %d 个专业；带地图号与坐标的 %d 条；出处池 %d 项（前四项是插件写的句子，一条没落盘）"
          % (total, len(recipes), with_at, len(pool)))
    print("专业分布：" + "、".join("%s %d" % (k, len(v)) for k, v in sorted(recipes.items(), key=lambda x: -len(x[1]))))

    if a.show:
        return

    snap = {
        "meta": {
            "source": "%s %s ProfRecipes.lua" % (ADDON, toc_version(src)),
            "addon": ADDON, "addonVersion": toc_version(src),
            "installRoot": (lambda p: p[p.index("AddOns") - 2] if "AddOns" in p else "unknown")(
                os.path.abspath(lua).replace("\\", "/").split("/")),
            "sourceFile": REL,
            "sourceStamp": {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                            "fileDate": datetime.datetime.fromtimestamp(os.path.getmtime(lua)).strftime("%Y-%m-%d")},
            "selfReported": "文件头自述：小程序 forever/prof_route.json 的全部配方（《无限》Beta 1.60.1.70532）；"
                            "口径 = foreverchanges 物品页 + vmangos 经典库 + 客户端声望（作者脚本 gi_forever_prof.py）",
            "fetched": datetime.date.today().isoformat(),
            "took": "法术 ID、中英文名、成品物品 ID、黄/灰技能点、需求等级、品质、是否《无限》新增、"
                    "主出处类型、材料 (物品ID, 数量)、出处地图号与百分比坐标与阵营",
            "droppedFields": ["出处池每一项的前四列（插件作者写的全文中文/全文英文/短句中文/短句英文）——红线不复制第三方说明文字",
                              "作者推荐的练级顺序与路线建议", "任何成段中文句子"],
            "boundary": "GI 目录没有 LICENSE、TOC 也没有 X-License 行；按插件线同一口径整体留 L1，"
                        "等游戏内实测或第二家资料才升档。",
            "counts": {"recipes": total, "professions": len(recipes), "withMapCoords": with_at,
                       "srcPoolItems": len(pool), "materialsRows": sum(len(r["materials"]) for v in recipes.values() for r in v)},
        },
        "recipes": {k: recipes[k] for k in sorted(recipes)},
    }
    if not os.path.isdir(UP):
        os.makedirs(UP)
    p = os.path.join(UP, "gi-prof-recipes.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(snap, ensure_ascii=False, indent=1) + "\n")
    print("写 %s（%.1f KB）" % (os.path.relpath(p, WEB), os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
