#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据体检：一条命令回答"还缺什么、哪些是我们自己能补的、哪些只能等"。

为什么要有它：产线的链路和命令写在 docs/DATA-MAINTENANCE.md 里，但"现在缺哪几块、
缺的能不能补"只能靠人翻 docs/PLAN-open-items.md 手工对，容易漏也容易重复劳动。
这里把能从数据里算出来的部分算出来，剩下的直接给结论与下一步命令。

它**不是门禁**：无论发现多少缺口都退出 0。一条永远红的门禁等于没有门禁
（2026-10-10 已经栽过一次，见 DATA-MAINTENANCE.md 第四节），体检只负责说话，不负责拦人。
拦人的还是 build-data.js / audit-translations.py / site-check.py 那三道。

用法：
    python3 tools/data-status.py            # 人看的报告
    python3 tools/data-status.py --json     # 给脚本用
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")
# 多久没重抓就要提醒。解包站跟着测试服发版，两周是个折中值
STALE_DAYS = 14
DAY = datetime.timedelta(days=1)


def jload(rel):
    p = os.path.join(DATA, rel)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def dval(s):
    """把 '2026-10-10' 解析成日期，解析不了返回 None。"""
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return None


def today():
    return datetime.date.today()


def build_rows():
    now = today()
    rows = []   # (板块, 缺什么, 数量, 归类, 下一步)

    scale = (jload("scale.json") or {}).get("scale", {})
    dg = jload("dungeons.json") or {}
    drows = []
    for k in ("newDungeons", "classicDungeons", "raids"):
        drows += dg.get(k) or []

    # ---- 副本线 ----
    n = len([x for x in drows if not x.get("nameEn")])
    rows.append(("副本", "没有英文原名的条目", n, "A" if n else "OK",
                 "node tools/merge-dungeons.js（客户端排队表里有的会自动补）" if n else "—"))
    n = len([x for x in drows if not (x.get("bosses") or [])])
    rows.append(("副本", "还没有首领名单的座数", n, "H",
                 "进游戏数一遍；客户端排队表里也没这条数据（已实测）"))
    mism = []
    for x in drows:
        cc = x.get("cardCounts") or {}
        m = re.search(r"\d+", str(cc.get("bosses") or ""))
        if m and int(m.group()) != len(x.get("bosses") or []):
            mism.append(x.get("nameCn") or x["id"])
    rows.append(("副本", "卡片自报首领数与名单条数对不上", len(mism), "H",
                 "人工核：%s" % ("、".join(mism[:6]) + ("…" if len(mism) > 6 else "") if mism else "—")))
    n = len([x for x in drows if not x.get("clientActivityId")])
    rows.append(("副本", "客户端队伍查找器里还不能排队的座数", n, "W",
                 "等正式开放（界面已逐条写明）" if n else "—"))

    qu = jload("queue.json") or {}
    un = [i for i in (qu.get("items") or []) if not i.get("matchedId")]
    rows.append(("副本", "客户端能排到、本站没有名单的", len(un), "A",
                 "逐座补首领与掉落（要先有可信来源，别猜）" if un else "—"))
    raid_rows = [i for i in (qu.get("items") or []) if i.get("kind") == "raid"]
    raid_names = {i["nameEn"] for i in raid_rows}
    no_cn = len([n for n in raid_names if not any(
        (r.get("nameEn") or "").lower() == n.lower() and r.get("nameCn")
        for r in (dg.get("raids") or []))])
    rows.append(("团本", "客户端能排到、还没有中文定名的团本条目", no_cn, "W",
                 "官方中文稿没发；团本页只列英文原名与人数，不机翻" if no_cn else "—"))
    rows.append(("团本", "团本的首领名单与掉落", len(raid_names), "W",
                 "客户端排队表里没有首领数据，参考站那份是推测段落不搬——等能进游戏或官方公布"))

    # ---- 天赋线 ----
    # 以 _ 开头的文件是草稿，build-data.js 也不算它们，这里必须同一口径
    noicon, conflict, unverified, nodes = 0, 0, 0, 0
    for p in sorted(glob.glob(os.path.join(DATA, "talents", "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        t = json.load(io.open(p, encoding="utf-8"))
        for spec in (t.get("trees") or []):
            for nd in (spec.get("nodes") or []):
                nodes += 1
                if not nd.get("iconKey"):
                    noicon += 1
                if nd.get("nameAlt") or nd.get("nameConflict"):
                    conflict += 1
                if not nd.get("nameVerified"):
                    unverified += 1
    if nodes != scale.get("talentNodes"):
        rows.append(("天赋", "与规模统计对不上的节点数（口径漂移）",
                     abs(nodes - (scale.get("talentNodes") or 0)), "A",
                     "data-status 与 build-data 数出来不一样，先查哪边漏了"))
    rows.append(("天赋", "没有本地图标的节点", noicon, "W",
                 "两源格位对不上，配图必须先假定，属编造（界面退回自绘块）" if noicon else "—"))
    rows.append(("天赋", "译名有分歧的节点", conflict, "W",
                 "等官方中文稿；界面上两个叫法都留着"))
    rows.append(("天赋", "中文名还没核到 L0 的节点", unverified, "W",
                 "等 5 个职业的官方中文稿（圣骑士 / 萨满祭司 / 法师 / 术士 / 潜行者）"))

    # ---- 素材 ----
    gaps = jload("icon-gaps.json") or {}
    cnt = len(gaps.get("keys") or [])
    rows.append(("素材", "官方图片服务器没有的图标键", cnt, "W",
                 "等上游切图；界面退回自绘块，登记在 icon-gaps.json"))
    w = jload("world.json") or {}
    wmeta = w.get("meta") or {}
    n = len(wmeta.get("mapsWithoutImage") or [])
    rows.append(("素材", "没有小地图的区域", n, "W",
                 "客户端里没切这张图（已逐键试过），界面显示地图编号与坐标" if n else "—"))
    rows.append(("素材", "载入图还缺的副本 / 团本",
                 len([x for x in drows if not x.get("art")]), "W",
                 "两台源都没有，横幅退回自绘"))

    # ---- 世界 / 专业 / 改动清单 ----
    n = scale.get("raresUnplaced") or 0
    rows.append(("世界", "只有名字没有坐标的稀有", n, "W",
                 "客户端里没有位置数据，等正式服"))
    prof = jload("professions.json") or {}
    flag = [r.get("nameCn") or r.get("id") for r in (prof.get("professions") or []) if r.get("unparsed")]
    rows.append(("专业", "有配方没能解析成结构化数据的专业", len(flag), "A",
                 "先看哪几行没解析：%s" % "、".join(flag[:6]) if flag else "—"))
    ch = jload("changes.json") or {}
    n = len((ch.get("meta") or {}).get("notCollected") or [])
    rows.append(("改动清单", "客户端里没被我们收进来的类别", n, "A",
                 "见 docs/PLAN-open-items.md 第一节，按板块排" if n else "—"))

    # ---- 来源标注 ----
    no_date, no_url = [], []
    for p in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        name = os.path.basename(p)
        if name in ("scale.json", "search.json", "icons.json", "icon-gaps.json"):
            continue
        try:
            obj = json.load(io.open(p, encoding="utf-8"))
        except ValueError:
            continue
        stack = [obj]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                prov = cur.get("provenance")
                if isinstance(prov, list):
                    for s in prov:
                        if not isinstance(s, dict):
                            continue
                        if s.get("type", "").startswith(("official", "datamine")) and not s.get("checkedAt"):
                            no_date.append("%s/%s" % (name, cur.get("id") or cur.get("key") or "?"))
                        if s.get("type", "").startswith(("official", "datamine")) and not s.get("url"):
                            no_url.append("%s/%s" % (name, cur.get("id") or "?"))
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
    rows.append(("溯源", "挂了官方/客户端来源却没有核对日期", len(set(no_date)), "A",
                 "补 checkedAt，否则逐字回查没法复跑" if no_date else "—"))
    rows.append(("溯源", "挂了官方/客户端来源却没有链接", len(set(no_url)), "A",
                 "补 url，一句没法验证的断言不算来源" if no_url else "—"))

    # ---- 上游新鲜度 ----
    stales = []
    pat = os.path.join(DATA, "upstream", "*.json")
    for p in sorted(glob.glob(pat)):
        try:
            obj = json.load(io.open(p, encoding="utf-8"))
        except ValueError:
            continue
        meta = obj.get("meta") or {}
        d = dval(meta.get("scrapedAt") or meta.get("fetchedAt") or meta.get("generatedAt"))
        note = ""
        if d is None:
            # 早期那批天赋转述文件没写日期，退回文件时间，别把它们全报成"没记日期"
            d = datetime.date.fromtimestamp(os.path.getmtime(p))
            note = "（按文件时间估）"
        if (now - d).days > STALE_DAYS:
            stales.append((os.path.basename(p), d.isoformat() + note, (now - d).days))
    rows.append(("上游", "超过 %d 天没重抓的原始数据" % STALE_DAYS, len(stales), "A",
                 "按板块跑 tools/refresh.sh <场景>" if stales else "—"))

    # ---- 派生数据是否落后于基底 ----
    derived = ["scale.json", "search.json", "icons.json", "icon-gaps.json", "talent-preview.json"]
    base_latest = 0
    for p in glob.glob(os.path.join(DATA, "*.json")) + glob.glob(os.path.join(DATA, "talents", "*.json")):
        if os.path.basename(p) in derived:
            continue
        base_latest = max(base_latest, os.path.getmtime(p))
    lag = []
    for name in derived:
        p = os.path.join(DATA, name)
        if os.path.exists(p) and os.path.getmtime(p) < base_latest:
            lag.append(name)
    rows.append(("派生", "比基底数据旧的派生文件", len(lag), "A",
                 "node tools/build-data.js（图标映射先 python3 tools/build-icon-map.py）" if lag else "—"))

    # ---- 两栈迁移进度 ----
    routerp = os.path.join(ROOT, "app", "src", "router.js")
    migrated = 0
    if os.path.exists(routerp):
        txt = io.open(routerp, encoding="utf-8").read()
        m = re.search(r"MIGRATED\s*=\s*\{(.*?)\}", txt, re.S)
        if m:
            migrated = len(re.findall(r"'([^']+\.html)'", m.group(1)))
    pages = len(glob.glob(os.path.join(ROOT, "src", "*.html")))
    rows.append(("新站", "还在旧站、没迁过去的页面", max(pages - migrated, 0), "A",
                 "一页一轮：改 app/ → app-parity.py --strict → site-check.py --app"))

    return rows, scale, stales, lag, now


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows, scale, stales, lag, now = build_rows()
    can = [r for r in rows if r[3] == "A" and r[2]]
    wait = [r for r in rows if r[3] == "W" and r[2]]
    human = [r for r in rows if r[3] == "H" and r[2]]

    if a.json:
        print(json.dumps({
            "at": now.isoformat(),
            "scale": scale,
            "gaps": [{"area": r[0], "what": r[1], "count": r[2], "kind": r[3], "next": r[4]} for r in rows],
            "staleUpstream": stales, "staleDerived": lag,
            "summary": {"canFix": len(can), "waiting": len(wait), "needsHuman": len(human)},
        }, ensure_ascii=False, indent=1))
        return 0

    lab = {"A": "我们能补", "W": "等外部", "H": "要人工判定", "OK": "已齐"}
    print("数据体检 · %s" % now.isoformat())
    print("=" * 62)
    print("规模：词条 %s / 天赋节点 %s / 副本 %s（新增 %s）/ 首领 %s / 掉落 %s / 配方 %s / 区域 %s" % (
        scale.get("coverageTotal"), scale.get("talentNodes"), scale.get("dungeons"),
        scale.get("dungeonsNew"), scale.get("bosses"), scale.get("drops"),
        scale.get("recipes"), scale.get("zones")))
    cov = scale.get("coverage") or {}
    print("分级：L0 %s / L1 %s / L2 %s / L3 %s（L0 占 %s%%）" % (
        cov.get("L0"), cov.get("L1"), cov.get("L2"), cov.get("L3"),
        round(cov.get("L0", 0) * 100.0 / max(scale.get("coverageTotal", 1), 1), 1)))
    print("-" * 62)
    print("缺口分类（数量后面是下一步）")
    for kind in ("A", "H", "W", "OK"):
        pick = [r for r in rows if r[3] == kind and (kind == "OK" or r[2])]
        if not pick:
            continue
        print("\n【%s】" % lab[kind])
        for r in pick:
            print("  %-6s %-22s %5s 条   %s" % (r[0], r[1], r[2], r[4]))
    if stales:
        print("\n【原始数据新鲜度】超过 %d 天：" % STALE_DAYS)
        for name, d, days in stales:
            print("  %-34s %s（%s 天前）" % (name, d, days))
    if lag:
        print("\n【派生数据落后】比基底旧：%s → 重跑 build-data.js" % "、".join(lag))
    print("\n" + "=" * 62)
    print("结论：%d 项我们能自己补 / %d 项要人工进游戏核 / %d 项只能等外部。" % (
        len(can), len(human), len(wait)))
    if can:
        print("要动手就跑对应板块那一条链，例如：bash tools/refresh.sh dungeons")
    print("只跑检查不碰网络：bash tools/refresh.sh check")
    print("这一份是报告不是门禁——拦人的是 build-data.js、audit-translations.py、site-check.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
