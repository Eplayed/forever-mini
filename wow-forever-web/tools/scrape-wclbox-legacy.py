#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 wowforever.wclbox.com 的传承数据（_shuju/<发布号>/legacy.json），入库前先删句子。

这份数据里有三样东西：21 个传承专长（带每层的完整效果说明文本）、65 个传承挑战、
以及树结构与规则。2026-10-09 定的口径（和改动清单同一把尺子）：
**只留名称与数值结构，别人转述的游戏文案一句都不进仓库。**
所以 rank_texts / unranked_effect / effect_rank / 挑战的 text / 常见问题答案 / 领取说明
这些字段在落盘前就丢掉，界面也就没有误用的口子。

留下的是事实性标识符：专长名与上限、树与槽位坐标、前置关系、图标文件名、
挑战的名称与完成条件、每项点数、进度奖励的名称与物品 ID、以及规则数值。

用法：
    python3 tools/scrape-wclbox-legacy.py
    python3 tools/scrape-wclbox-legacy.py --show      # 只看规模与删了哪些字段
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "src", "data", "upstream")
BASE = "https://wowforever.wclbox.com"
PAGE = "/chuancheng"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BUILD_RE = re.compile(r"/_shuju/(r-\d+)/")

# 专长：整条效果说明文本与施法/冷却数值都不落盘（那是别人转述的 tooltip）
PERK_DROP = ["rank_texts", "unranked_effect", "effect_rank", "spell", "cast_ms", "cooldown_ms",
             "calculator_eligible", "context_only", "comparison_status", "account_scope",
             "kind", "class", "tree_id", "tree_index", "reported_change_kind", "sources"]
# 挑战：text 是带句号的整句，requirement 是不带句号的同一条完成条件——只留后者
ITEM_DROP = ["text", "criteria"]
TOP_DROP = ["faq", "additional_perks", "share_code_order", "items"]

KEPT = {}


def http(url, binary=False):
    p = subprocess.run(["curl", "-s", "-L", "-m", "60", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True)
    body = p.stdout
    nl = body.rfind(b"\n")
    code = int(body[nl + 1:].strip() or 0) if nl >= 0 else 0
    return code, (body[:nl] if binary else body[:nl].decode("utf-8", "replace"))


def discover_build():
    """发布号必须现读：上游每次解包都会换一个新的 r-<时间戳> 目录，手抄的一定会过期。"""
    for path in (PAGE, "/tianfu", "/xiyou", "/"):
        code, html = http(BASE + path)
        if code == 200:
            m = BUILD_RE.search(html)
            if m:
                return m.group(1)
    sys.exit("没在页面里找到 _shuju 发布号，上游可能改了目录结构")


def drop_note(where, keys):
    KEPT[where] = sorted(set(KEPT.get(where, [])) | set(keys))


def strip_perk(p):
    gone = [k for k in p if k in PERK_DROP]
    out = {k: v for k, v in p.items() if k not in PERK_DROP}
    drop_note("perk", gone)
    return out


def strip_item(x):
    gone = [k for k in x if k in ITEM_DROP]
    out = {k: v for k, v in x.items() if k not in ITEM_DROP}
    drop_note("challenge", gone)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="只打印规模与删掉的字段，不落盘")
    a = ap.parse_args()

    build = discover_build()
    url = "%s/_shuju/%s/legacy.json" % (BASE, build)
    code, txt = http(url)
    if code != 200:
        sys.exit("取不到 %s（HTTP %s）" % (url, code))
    d = json.loads(txt)

    perks = [strip_perk(p) for p in d.get("perks") or []]
    challenges = []
    for c in d.get("challenges") or []:
        challenges.append({"name": c.get("name"), "subcategories": c.get("subcategories") or [],
                           "items": [strip_item(x) for x in c.get("items") or []]})
    tr = (d.get("tree") or {})
    rewards = [{k: v for k, v in r.items() if k != "text"} for r in
               ((tr.get("progress_track") or {}).get("rewards") or [])]
    trees = [{"name": t.get("name"), "portrait": t.get("portrait"),
              "nodes": t.get("nodes") or [], "links": t.get("links") or []}
             for t in tr.get("trees") or []]
    srcs = (tr.get("sources") or (d.get("research") or {}).get("sources") or [])

    out = {
        "meta": {
            "source": BASE + PAGE,
            "endpoint": url,
            "build": build,
            "clientBuild": (tr.get("challenges") or {}).get("build"),
            "upstreamUpdatedAt": tr.get("updated_at"),
            "fetchedAt": datetime.date.today().isoformat(),
            "method": "tools/scrape-wclbox-legacy.py 取 _shuju/<发布号>/legacy.json，发布号现读",
            "textPolicy": "落盘前删掉的字段见 droppedFields；效果说明与整句文本一律不存仓库",
            "droppedFields": {k: KEPT.get(k, []) for k in sorted(KEPT)},
            "droppedBlocks": ["research.faq（问答整段是别人的表述）", "progress_track.claim（领取说明）",
                              "tree.share_code_order", "tree.additional_perks", "顶层 items（与 challenges 重复）"],
            "sources": srcs
        },
        "rules": tr.get("rules") or {},
        "challengeMeta": tr.get("challenges") or {},
        "trees": trees,
        "perks": perks,
        "challenges": challenges,
        "rewards": rewards
    }
    n_ch = sum(len(c["items"]) for c in challenges)
    print("发布号 %s ｜ 专长 %d（带明细）｜ 树 %d 棵 / 槽位 %d ｜ 挑战 %d 项 / 分类 %d ｜ 进度奖励 %d" % (
        build, len(perks), len(trees), sum(len(t["nodes"]) for t in trees), n_ch, len(challenges),
        len(rewards)))
    print("删掉的字段：perk %s ｜ 挑战 %s" % (
        "、".join(KEPT.get("perk", [])), "、".join(KEPT.get("challenge", []))))
    if a.show:
        return
    if not os.path.isdir(UP):
        os.makedirs(UP)
    p = os.path.join(UP, "wclbox-legacy.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("→ src/data/upstream/wclbox-legacy.json（%d KB）" % (os.path.getsize(p) // 1024))


if __name__ == "__main__":
    main()
