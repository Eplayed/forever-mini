#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 从 DungeonsForever/Core/Data/Data_BIS.lua 抽「第三份配装名单」，落 upstream 修剪快照。
#
# 为什么开（2026-11-01 站主点头"DF/XR 那几张从未取过的表要开"，其中点名了这一张）：
#   本站配装现在两份并列：主名单来自解包资料站 /peizhuang，第二份来自 XR 的 Data_Bis.lua
#   （它自述抓 foreverchanges.pro）。DF 这份是**第三家**，作者与上游都不同，
#   先把"三家在同一格上怎么说"的数据摆齐，才有得谈要不要在界面上并列。
#
# 边界（DF 的 LICENSE 是「Copyright © 2026 圆圆 · 保留所有权利」）：
#   只取 等级段 / 职业 / 专精 / 部位 / 物品 ID / 顺位。
#   每格第三列那种属性句（"敏捷 +3"、"所有属性 +2"）是 DF 自己写的表述，**一条不落盘**——
#   本站的属性另有自己的来源（items-detail 那几层），不复制别人怎么写。
#   DF 的成段讲解、属性优先级建议、循环建议一律不取。
#   整体按 L1 留档（一家资料站列过），与 xr-bis 同一待遇，不许因为"看起来合理"就升 L0。
#
# 用法：python3 tools/extract-df-bis.py [--src <插件根目录>] [--show]
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
ADDON = "DungeonsForever"
REL = ADDON + "/Core/Data/Data_BIS.lua"
HOME = os.path.expanduser("~")
CANDIDATES = [os.path.join(HOME, "Documents", "project", ".scratch", "wow"),
              "C:/GAME/World of Warcraft/_cn_beta_/Interface/AddOns"]

ITEM_RE = re.compile(r'\{\s*(\d{4,8})\s*,\s*(\d+)(\s*,\s*"(?:[^"\\]|\\.)*")?\s*\}')


def resolve_src(given):
    for c in (given, os.environ.get("WOW_ADDONS")):
        if c and os.path.isdir(os.path.join(c, ADDON)):
            return c
    for c in CANDIDATES:
        if os.path.isdir(os.path.join(c, ADDON)):
            return c
    sys.exit("找不到 %s：给 --src <插件根目录> 或把 WOW_ADDONS 指到 Interface/AddOns" % ADDON)


def toc_version(src):
    p = os.path.join(src, ADDON, ADDON + ".toc")
    for line in io.open(p, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*##\s*Version:\s*(\S+)", line)
        if m:
            return m.group(1)
    return "版本未记"


def install_root(src):
    parts = os.path.abspath(src).replace("\\", "/").rstrip("/").split("/")
    return parts[-2] if parts and parts[-1] == "AddOns" else parts[-1]


def brace_end(s, start):
    """s[start] 必须是 '{'，返回配对的 '}' 下标（字符串与转义都顾及）。"""
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


def block(s, m):
    """正则匹配到的那个 '{' 起，切出配平的整块。"""
    st = s.index("{", m.start())
    return s[st:brace_end(s, st) + 1]


def parse(text):
    lv = re.search(r"\blevels\s*=\s*\{", text)
    if not lv:
        sys.exit("找不到 levels 顶层表——DF 改了结构，先人工看文件再改这里")
    body = block(text, lv)
    sets, stat_strings = [], 0
    for lm in re.finditer(r'\[(\d+)\]\s*=\s*\{', body):
        level = lm.group(1)
        lblock = block(body, lm)
        for cm in re.finditer(r'\{\s*slug\s*=\s*"([a-z_]+)"', lblock):
            cls = cm.group(1)
            cblock = block(lblock, cm)
            for sm in re.finditer(r'\{\s*id\s*=\s*"([a-z0-9\-]+)"', cblock):
                spec = sm.group(1)
                sblock = block(cblock, sm)
                sl = re.search(r"\bslots\s*=\s*\{", sblock)
                if not sl:
                    continue
                slots = block(sblock, sl)
                for km in re.finditer(r'\["([a-z0-9_]+)"\]\s*=\s*\{', slots):
                    slot = km.group(1)
                    picks = []
                    for im in ITEM_RE.finditer(block(slots, km)):
                        picks.append({"itemId": int(im.group(1)), "rank": int(im.group(2))})
                        if im.group(3):
                            stat_strings += 1
                    if picks:
                        sets.append({"level": int(level), "class": cls, "spec": spec,
                                     "slot": slot, "picks": picks})
    return sets, stat_strings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    src = resolve_src(a.src)
    lua = os.path.join(src, ADDON, "Core", "Data", "Data_BIS.lua")
    raw = io.open(lua, encoding="utf-8").read()
    b = open(lua, "rb").read()
    sets, stat_strings = parse(raw)

    ids = {p["itemId"] for s in sets for p in s["picks"]}
    print("DF 配装：%d 格（等级段×职业×专精×部位），用到 %d 个物品 ID；"
          "它写的属性句 %d 条已丢弃，一条没落盘" % (len(sets), len(ids), stat_strings))
    per = {}
    for s in sets:
        per.setdefault((s["level"], s["class"]), 0)
        per[(s["level"], s["class"])] += 1
    print("覆盖：%d 个 等级段×职业 组合（30 级 %d / 20 级 %d）"
          % (len(per), len([k for k in per if k[0] == 30]), len([k for k in per if k[0] == 20])))

    if a.show:
        return

    upd = sorted(set(re.findall(r'updated\s*=\s*"([0-9\-]+)"', raw)))
    snap = {
        "meta": {
            "source": "%s %s Core/Data/Data_BIS.lua" % (ADDON, toc_version(src)),
            "addon": ADDON, "addonVersion": toc_version(src), "installRoot": install_root(src),
            "sourceFile": REL,
            "sourceStamp": {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                            "fileDate": datetime.datetime.fromtimestamp(os.path.getmtime(lua)).strftime("%Y-%m-%d")},
            "selfReported": "文件里自述 updated=%s、默认等级段 30；作者没写上游站名（自述来源不明，"
                            "所以这份只当'另一家列过的名单'，不当独立第二证据）" % ("、".join(upd) or "未标"),
            "fetched": datetime.date.today().isoformat(),
            "took": "等级段、职业、专精、部位、物品 ID、格内顺位",
            "droppedFields": ["每格第三列的属性句（如「敏捷 +3」「所有属性 +2」）——那是 DF 自己写的表述，"
                              "本站的属性另有来源，不复制别人怎么写",
                              "DF 的成段讲解、属性优先级与循环建议（红线）"],
            "boundary": "DF 的 LICENSE 是「保留所有权利」，这一层只取名单与物品 ID 这些事实标识符；"
                        "本站没有进游戏实测过任何一套，整体 L1。"
                        "**这是第三家名单**：界面现在并列的是两家（解包资料站 + XR 转述的 foreverchanges.pro），"
                        "要不要把第三家也并列出来是产品口径，等站主定，本快照只把数据摆齐。",
            "counts": {"slotSets": len(sets), "picks": sum(len(s["picks"]) for s in sets),
                       "distinctItems": len(ids),
                       "levels": len({s["level"] for s in sets}),
                       "classes": len({s["class"] for s in sets}),
                       "specs": len({s["spec"] for s in sets}),
                       "droppedStatStrings": stat_strings},
        },
        "sets": sorted(sets, key=lambda x: (x["level"], x["class"], x["spec"], x["slot"])),
    }
    if not os.path.isdir(UP):
        os.makedirs(UP)
    p = os.path.join(UP, "df-bis.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(snap, ensure_ascii=False, indent=1) + "\n")
    print("写 %s（%.1f KB）" % (os.path.relpath(p, WEB), os.path.getsize(p) / 1024.0))


if __name__ == "__main__":
    main()
