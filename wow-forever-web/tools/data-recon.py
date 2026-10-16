#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""板块对账表（PRD-web-parity §二 的验收件，2026-10-16 起）。

站主验收要看的是"每个板块：源侧自报多少 / 站内多少 / 差多少 / 差的为什么不能补"，
而且**差值非 0 的行必须有解释，不接受"漏了"**。这份表把三个数都从文件里现读，
不手抄——手抄的数在验收那天就已经过期了。

- 源侧数读不到（抓下来的快照没自报数、或那个数只在 docs 里写着）→ 显示「源侧没登记」，
  该行自动算"要人工核"，不拿站内数冒充两边都对上过。
- 它**不是门禁**：发现对不上也退出 0。拦人的还是 build-data.js / site-check.py。

用法：
    python3 tools/data-recon.py          # 人看的表
    python3 tools/data-recon.py --json   # 给脚本用
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")


def jload(rel):
    p = os.path.join(DATA, rel)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def dig(spec):
    """spec 形如 "scale:spells" / "items-detail.json:meta.counts.total"，取不到返回 None。"""
    if spec.startswith("scale:"):
        sc = jload("scale.json")
        if not sc:
            return None
        return sc["scale"].get(spec[6:])
    f, _, path = spec.partition(":")
    doc = jload(f)
    if doc is None:
        return None
    cur = doc
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur if isinstance(cur, (int, float)) else None


# 行定义：板块 / 源侧自报怎么读 / 站内怎么读 / 页面上在哪 / 差值解释（None = 要人工核）
# 解释只写已经做过的事，不写推测；源侧或站内任一侧读不到，表里会自己说。
ROWS = [
    ("法术书", "upstream/wclbox-spells.json:meta.counts.total", "scale:spells",
     "技能页「法术书」表（site-check 6a 钉行数）",
     "参考站九页法术逐行取回，成品一条没丢；级数与起学等级两边说法不同的那些条，两个数都摆着（条数见 spells.json 的 meta.counts）"),
    ("成就", "upstream/gi-achievements.json:meta.counts.total", "scale:achievements",
     "成就页（列 198 条，可列数在 achievements.json 的 meta.counts.shown）",
     "差的那些是客户端里的开发条目（Hidden / UNUSED / 测试问卷），玩家拿不到所以不列，条目没删；" +
     "可列数在 achievements.json 的 meta.counts.shown"),
    ("稀有精英", "upstream/gi-rares.json:meta.counts.total", "scale:rares",
     "世界页「稀有」",
     "站内是两家的并集：插件那份 338 + 参考站 36 − 重合 12 = 362。参考站那 36 的自报数没落进快照 "
     "meta，只在 docs/wow-infinite-sources.md 里，所以这一行的差是按 338 算的（+24），"
     "不是按并集算的"),
    ("物品详情", "upstream/wclbox-items-detail.json:meta.counts.total",
     "items-detail.json:meta.counts.total", "物品库抽屉",
     "差的 549 件参考站页面没有无限侧详情块（自报 missing / held），按红线不许拿经典侧数值冒充"),
    ("物品名录", None, "scale:items", "物品库列表",
     "名称索引那次抓取没在快照里写自报数，站内 21,077 就是抓回来的条数 → 要人工核"),
    ("副本任务", "upstream/wclbox-dungeon-quests.json:meta.counts.quests",
     "dungeon-quests.json:meta.counts.quests", "副本详情页「本里的任务」",
     "两个数不是简单加减：合并时逐字重复的行被并掉（meta.counts.deduped）、"
     "接取人写成「物品：X」的改了归属（itemStart）、另有 29 座来自插件那份（fromGi）。"
     "要逐条对上得重跑一次 merge 出明细 → 要人工核"),
    ("副本", None, "scale:dungeons", "副本手册 + 每座本一页",
     "源侧（参考站 35 座 + 官方新增）没在快照 meta 里自报 → 要人工核；"
     "站内 38 座里 9 座是无限新增，等级区间已逐座对过（0 座不一致）"),
    ("首领与掉落", None, "scale:bosses", "每座本一页",
     "首领 228 / 掉落 1,050 条；掉落全部标待实测（源站自己写着无限服重做过掉落）→ 概率一类刻意不拿"),
    ("专业与配方", None, "scale:recipes", "专业页",
     "源侧专业页没自报配方总数（抓取时未记）→ 要人工核；站内 13 专业 / 1,990 条配方"),
    ("传承", None, "legacy.json:meta.counts.challenges", "传承页",
     "参考站那份快照的 meta 没有自报挑战条数（只有 build 与抓取日期）→ 要人工核；"
     "站内 66 项、点数合计 81 与上游那页自报的 81 对上（legacy.json 的 "
     "meta.counts.upstreamChallengeTotal），条数这一层两家没在同一颗粒度上比过"),
    ("世界区域", None, "scale:zones", "世界页「区域」",
     "源侧区域表自报 43，站内 44：多出来的一格是站内单列的城市/新区域行（源侧把它归到别组）→ 要人工核"),
    ("天赋节点", None, "scale:talentNodes", "天赋计算器九棵树",
     "源侧按系自报、站内按节点计，两个颗粒度不能直接减 → 要人工核；"
     "改动清单那份的自报数（changes.json 的 upstreamCounts 七个数）已逐个对上"),
    ("改动清单", "upstream/wclbox-changes.json:meta.upstreamCounts.all", "scale:changes",
     "动态页 + 职业页技能变化",
     "无差：上游自报 965 与站内 965 逐条对上（天赋 545 + 法术 420 两族分开数）"),
    ("中英术语", None, "scale:glossary", "速查页",
     "官方中文稿逐句抽的，没有第三方源侧自报数可对 → 不适用"),
    ("全站搜索", None, "scale:search", "首页那颗搜索框",
     "派生件，不是板块：条数由 build-data.js 从各板块派生后写回 scale，"
     "逐类对数（数据有条数、索引必须一条不少）已进卡口"),
]


def stamps(spec):
    """从源侧那份快照的 meta 里取「抓取日 + 客户端版本」——验收要看的不只是条数对没对，
       还有"这个数是哪天从哪一版读来的"。取不到就返回 None，表里显示 —。"""
    if not spec or not spec.startswith("upstream/"):
        return None, None
    doc = jload(spec.split(":")[0]) or {}
    m = doc.get("meta") or {}
    d = m.get("fetched") or m.get("fetchedAt") or m.get("generatedAt") or m.get("scrapedAt")
    b = (m.get("foreverBuild") or m.get("upstreamBuild") or m.get("clientBuild")
         or m.get("build") or (m.get("builds") or [None])[0])
    return d, b


def gen_date():
    sc = jload("scale.json") or {}
    return (sc.get("meta") or {}).get("generatedAt") or "日期读不到"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    out = []
    for name, src_spec, ours_spec, page, why in ROWS:
        src = dig(src_spec) if src_spec else None
        ours = dig(ours_spec)
        diff = None if (src is None or ours is None) else ours - src
        manual = diff is None or (diff != 0 and not why)
        snap, build = stamps(src_spec)
        out.append({"board": name, "source": src, "ours": ours, "diff": diff,
                    "page": page, "explain": why, "snapshot": snap, "build": build,
                    "status": ("已对齐" if diff == 0 else
                               ("差值有解释" if diff is not None and why else "要人工核")),
                    "needHuman": bool(manual),
                    "sourceSpec": src_spec, "oursSpec": ours_spec})
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    print("板块对账表 · 三个数全部现读（数据日期 %s）" % gen_date())
    print("=" * 78)
    print("%-8s %10s %10s %8s  %-11s %-13s %s"
          % ("板块", "源侧自报", "站内", "差", "快照日", "客户端版本", "结论"))
    for r in out:
        s = "—" if r["source"] is None else "{:,}".format(r["source"])
        o = "—" if r["ours"] is None else "{:,}".format(r["ours"])
        df = "?" if r["diff"] is None else ("%+d" % r["diff"])
        print("%-8s %10s %10s %8s  %-11s %-13s %s"
              % (r["board"], s, o, df, r["snapshot"] or "—", r["build"] or "—", r["status"]))
        print("         页面：%s" % r["page"])
        print("         说明：%s" % r["explain"])
    need = [r["board"] for r in out if r["needHuman"]]
    zero = [r["board"] for r in out if r["diff"] == 0]
    exp = [r["board"] for r in out if not r["needHuman"] and r["diff"] != 0]
    print("=" * 78)
    print("逐数对上（差 0）：%d 行（%s）" % (len(zero), "、".join(zero)))
    print("有差但已解释：%d 行（%s）" % (len(exp), "、".join(exp)))
    print("要人工核：%d / %d（%s）" % (len(need), len(out), "、".join(need)))
    builds = sorted({str(r["build"]) for r in out if r["build"]})
    print("各线读到的客户端版本：%s" % "、".join(builds) if builds else "各线版本：都没记在快照 meta 里")
    if len(builds) > 1:
        print("→ 这几行不是同一版读来的。版本最高那组才是当前值，其余按各自快照日排队重抓"
              "（顺序与判据见根 ROLES.md 的 D6）。")
    print("「源侧自报」那列是 — 的不是漏抓，是那一侧当时没把自报数落进快照——"
          "补法是让对应抓取脚本把源侧自报数写进 meta（下一批重抓时带上）。")
    print("这一份是验收件不是门禁：对不上也退出 0，拦人的是 build-data.js、site-check.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
