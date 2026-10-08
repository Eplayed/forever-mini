#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓无限数据库 wowforever.wclbox.com 的结构化事实，落到 src/data/upstream/。

只取事实性标识符：名单、等级区间、新本标记、BOSS 名、掉落归属、物品 ID、图标文件名。
它的描述文案、背景故事、BiS 结论、排行一律不取（红线）。

用法：
    python3 tools/scrape-wclbox.py --what dungeons            # 打印摘要，不写盘
    python3 tools/scrape-wclbox.py --what dungeons --write    # 写 upstream/wclbox-dungeons.json

为什么分两步（抓 → upstream → 合并进 dungeons.json）：上游是第三方转述，
直接改成品数据文件会把我们自己攒的官方来源与译名冲突记录冲掉。
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys
import time

BASE = "https://wowforever.wclbox.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "src", "data", "upstream")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def get(path):
    url = path if path.startswith("http") else BASE + path
    p = subprocess.run(["curl", "-s", "-L", "-m", "30", "-A", UA, url], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        sys.exit("抓不到 %s（%s）" % (url, p.stderr.decode("utf-8", "replace")[:80]))
    return p.stdout.decode("utf-8", "replace")


CARD_RE = re.compile(r'href="/fuben/([a-z0-9\-]+)"[^>]*><b>([\s\S]*?)</b><small>([\s\S]*?)</small>')
BOSS_RE = re.compile(r'<section class="sj-boss" id="([a-z0-9\-]+)">([\s\S]*?)</section>', re.I)
H2_RE = re.compile(r'<h2[^>]*>([\s\S]*?)</h2>')
NONE_RE = re.compile(r'class="sj-none"[^>]*>([\s\S]*?)<')
ITEM_RE = re.compile(r'<a href="/wupin/(\d+)"([\s\S]*?)</a>', re.I)
ICON_IN_RE = re.compile(r'src="/tubiao/([a-z0-9_]+)\.jpg')
NAME_IN_RE = re.compile(r'class="sj-name[^"]*">([^<]+)<')
QUAL_IN_RE = re.compile(r'class="sj-name q(\d)')
LEDE_RE = re.compile(r'class="fbp-lede"[^>]*>([\s\S]*?)</p>')
TAGS = re.compile(r"<[^>]+>")


def clean(x):
    return re.sub(r"\s+", " ", TAGS.sub("", x)).strip()


def dungeons():
    html = get("/fuben")
    seen, rows = {}, []
    for m in CARD_RE.finditer(html):
        slug = m.group(1)
        if slug in seen:
            continue
        name = clean(m.group(2))
        is_new = "新" in m.group(2)
        rng = clean(m.group(3)).replace("–", "-").replace("—", "-")
        item = {"slug": slug, "nameCn": name.replace("新", "").strip() if is_new else name,
                "isNew": is_new, "levelRange": rng or None, "bosses": [], "drops": []}
        seen[slug] = item
        rows.append(item)

    for i, d in enumerate(rows):
        page = get("/fuben/" + d["slug"])
        lede = LEDE_RE.search(page)
        if lede:
            d["lootSourceNote"] = clean(lede.group(1))
        for bm in BOSS_RE.finditer(page):
            body = bm.group(2)
            h = H2_RE.search(body)
            bname = clean(h.group(1)) if h else None
            if not bname:
                continue
            d["bosses"].append({"id": bm.group(1), "nameCn": bname,
                                "noLootNote": (clean(NONE_RE.search(body).group(1))
                                               if NONE_RE.search(body) else None)})
            for im in ITEM_RE.finditer(body):
                inner = im.group(2)
                icon = ICON_IN_RE.search(inner)
                nm = NAME_IN_RE.search(inner)
                q = QUAL_IN_RE.search(inner)
                if not nm:
                    continue
                d["drops"].append({"itemId": im.group(1),
                                   "iconKey": icon.group(1) if icon else None,
                                   "nameCn": clean(nm.group(1)), "bossId": bm.group(1),
                                   "bossCn": bname,
                                   "quality": int(q.group(1)) if q else None})
        time.sleep(0.35)
        if (i + 1) % 10 == 0:
            print("  已抓 %d/%d 本" % (i + 1, len(rows)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["dungeons"], default="dungeons")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rows = dungeons()
    nb = sum(len(d["bosses"]) for d in rows)
    nd = sum(len(d["drops"]) for d in rows)
    print("副本 %d 座（新本 %d）· BOSS %d 个 · 掉落条目 %d 条" % (
        len(rows), len([x for x in rows if x["isNew"]]), nb, nd))
    for d in rows[:5]:
        print("   %-26s %-8s BOSS %d 掉落 %d" % (d["slug"], d["levelRange"], len(d["bosses"]), len(d["drops"])))
    empty = [d["slug"] for d in rows if not d["bosses"]]
    if empty:
        print("  没有 BOSS 段的本：%s" % "、".join(empty[:10]))
    if not args.write:
        print("（未写盘，加 --write 生成 upstream/wclbox-dungeons.json）")
        return
    if not os.path.isdir(UP):
        os.makedirs(UP)
    payload = {"meta": {"source": BASE + "/fuben", "site": "新手盒子 · 魔兽世界无限数据库",
                        "scrapedAt": datetime.date.today().isoformat(),
                        "method": "tools/scrape-wclbox.py --what dungeons --write",
                        "took": "名单/等级区间/新本标记/BOSS 名/掉落归属/物品 ID/图标文件名；不取描述文案与攻略"},
               "dungeons": rows}
    out = os.path.join(UP, "wclbox-dungeons.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print("已写入 %s（%d 座）" % (os.path.relpath(out, ROOT), len(rows)))


if __name__ == "__main__":
    main()
