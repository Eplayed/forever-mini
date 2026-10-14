#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 wowforever.wclbox.com 的全量物品名录（/wupin/liebiao/N 名称索引），写进 src/data/upstream/。

为什么走名称索引而不是详情页：wclbox 的 _shuju 数据包里没有物品文件（2026-10-13 逐名试探，
只翻出 chengjiu.json），物品库是 SSR 表格分页——每页 200 件、共 106 页，行字段恰好是
清单级五件套：名称（品质色 + 图标文件名）/ 类型·部位 / 物品等级 / 需要等级 / 状态（新增/改动/不变/无）。
全量 21,077 件 106 次请求就齐；详情页 tooltip（属性效果行、来源归属）不在这一期，
见 docs/GAP-VS-WCLBOX-2026-10-13.md 的二批计划。

红线口径：列表行里只有事实性标识符（名称、ID、图标文件名、等级、类型、状态），
没有描述文案可抄——天然合规。图标文件名照旧只记名字，取图走暴雪官方 CDN（fetch-icons.py），
取不到的按 2026-10-08 口径自绘，不猜图。

用法：
    python tools/scrape-wclbox-items.py --show        # 只抓第 1 页打印规模，不落盘
    python tools/scrape-wclbox-items.py               # 全量抓 + 写 upstream/wclbox-items-index.json
    python tools/scrape-wclbox-items.py --pages 3     # 只抓前 3 页（调试用）
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "src", "data", "upstream")
BASE = "https://wowforever.wclbox.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PER_PAGE = 200
SLEEP = 0.5  # 礼貌间隔：106 页约 1 分钟

ROW_RE = re.compile(
    r'<td><a class="(q\d)" href="/wupin/(\d+)"[^>]*>'
    r'<img src="/tubiao/([^"]+)"[^>]*/>'
    r'<span>(.*?)</span></a>(?:<small>([^<]*)</small>)?</td>'
    r'<td>([^<]*)</td><td>([\d—–]*)</td><td>([\d—–]*)</td>'
    r'<td><span class="ic-status (ic-[^"]+)">([^<]*)</span></td>')


def http(url):
    p = subprocess.run(["curl", "-s", "-L", "-m", "40", "-A", UA, url], capture_output=True)
    return p.stdout.decode("utf-8", "replace").replace("<!-- -->", "")


def num(s):
    return int(s) if s.isdigit() else None


def clean(s):
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').strip()


def parse_page(html):
    rows = []
    for m in ROW_RE.finditer(html):
        q, iid, icon, name, sub, typ, ilvl, rlvl, stcls, sttxt = m.groups()
        rows.append({
            "id": int(iid),
            "name": clean(name),
            "quality": int(q[1]),
            "icon": icon.rsplit("/", 1)[-1],
            "sub": clean(sub) if sub else "",
            "type": clean(typ),
            "ilvl": num(ilvl),
            "rlvl": num(rlvl),
            "status": {"ic-new": "new", "ic-changed": "changed", "ic-same": "same",
                       "ic-missing": "missing"}.get(stcls, stcls),
        })
    n = re.search(r'本页\s*(\d+)', html)
    nxt = re.search(r'rel="next"\s+href="/wupin/liebiao/(\d+)"', html)
    return rows, (int(n.group(1)) if n else 0), (int(nxt.group(1)) if nxt else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="只抓第 1 页打印规模，不落盘")
    ap.add_argument("--pages", type=int, default=0, help="只抓前 N 页（调试）")
    args = ap.parse_args()

    first = http(BASE + "/wupin/liebiao/1")
    rows, shown, nxt = parse_page(first)
    print(f"第 1 页：解析 {len(rows)} 行（页面声明本页 {shown} 件）；下一页 → {nxt}")
    if not rows or len(rows) != shown:
        print(f"!! 第 1 页解析行数 {len(rows)} != 声明 {shown}，正则可能漏行，先修再跑全量")
        sys.exit(1)
    if args.show:
        print("样例:", json.dumps(rows[:2], ensure_ascii=False, indent=1)[:400])
        return

    all_rows = list(rows)
    page, nxt = 1, nxt
    while nxt and (not args.pages or page < args.pages):
        page = nxt
        html = http(f"{BASE}/wupin/liebiao/{page}")
        rr, shown, nxt = parse_page(html)
        if len(rr) != shown:
            print(f"!! 第 {page} 页解析 {len(rr)} != 声明 {shown}，中止（已抓 {len(all_rows)}）")
            sys.exit(1)
        all_rows.extend(rr)
        if page % 10 == 0 or not nxt:
            print(f"  … {page} 页，累计 {len(all_rows)} 件")
        time.sleep(SLEEP)

    stats = {}
    for r in all_rows:
        stats[r["status"]] = stats.get(r["status"], 0) + 1
    doc = {
        "meta": {
            "source": "wowforever.wclbox.com /wupin/liebiao（名称索引全量名录）",
            "url": BASE + "/wupin/liebiao/1",
            "fetched": datetime.date.today().isoformat(),
            "pages": page,
            "parsed": len(all_rows),
            "stats": stats,
            "note": "清单级名录：无描述文案可采（红线天然合规）；详情 tooltip 属二批增量",
        },
        "items": sorted(all_rows, key=lambda r: r["id"]),
    }
    out = os.path.join(UP, "wclbox-items-index.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"落盘 {out}：{page} 页共 {len(all_rows)} 件，状态分布 {stats}")


if __name__ == "__main__":
    main()
