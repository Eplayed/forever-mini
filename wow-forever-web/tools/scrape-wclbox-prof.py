#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓无限数据库的专业页（配方与采集点），写 src/data/upstream/wclbox-professions.json。

这些页是服务端渲染的，curl 就够，不用起浏览器。
只取事实性标识符：配方制成品与物品 ID、材料清单与数量、技能难度四档、来源方式、
采集点与可得物；不取它的攻略文字、冲级路线建议、BiS 结论。

用法：
    python3 tools/scrape-wclbox-prof.py            # 只打印摘要
    python3 tools/scrape-wclbox-prof.py --write    # 写盘
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

GATHER = {"mining": u"采矿", "herbalism": u"草药学", "skinning": u"剥皮", "fishing": u"钓鱼",
          "first-aid": u"急救", "cooking": u"烹饪", "camping": u"野营"}

ROW_RE = re.compile(r"<tr[^>]*>([\s\S]*?)</tr>", re.I)
CELL_RE = re.compile(r"<td[^>]*>([\s\S]*?)</td>", re.I)
ITEM_RE = re.compile(r'data-item="(\d+)"[^>]*>(?:(?!</a>)[\s\S])*?'
                     r'(?:src="/tubiao/([a-z0-9_]+)\.jpg")?(?:(?!</a>)[\s\S])*?'
                     r'(?:class="zk-name zk-q(\d)">([^<]+)<|aria-label="([^"]+?) ×(\d+)")', re.I)
LINK_RE = re.compile(r'data-item="(\d+)"', re.I)
NAME_RE = re.compile(r'class="zk-name[^"]*">([^<]+)<', re.I)
QRE = re.compile(r'class="zk-name zk-q(\d)"', re.I)
ICON_RE = re.compile(r'src="/tubiao/([a-z0-9_]+)\.jpg')
MAT_RE = re.compile(r'aria-label="([^"]+?) ×(\d+)"')
SKILL_RE = re.compile(r'class="zk-t-(o|y|g|x)">(\d+)<')
SRC_RE = re.compile(r'class="zk-src-t"[^>]*>([^<]+)<')
NEW_RE = re.compile(r'class="zk-new"')
TAGS = re.compile(r"<[^>]+>")


def get(path):
    p = subprocess.run(["curl", "-s", "-L", "-m", "40", "-A", UA, BASE + path], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        return None
    return p.stdout.decode("utf-8", "replace")


def tables(html, cls):
    """同一页可能有多张同类表（炼金术就是 121 + 55 两截），全都要。"""
    return [m.group(1) for m in re.finditer(r'<table class="[^"]*%s[^"]*">([\s\S]*?)</table>' % cls, html)]


def h1(html):
    m = re.search(r"<h1[^>]*>([\s\S]{0,80}?)</h1>", html)
    return re.sub(r"\s+", "", TAGS.sub("", m.group(1))).strip() if m else None


def made_of(cell):
    item = LINK_RE.search(cell)
    name = NAME_RE.search(cell)
    icon = ICON_RE.search(cell)
    q = QRE.search(cell)
    if not item or not name:
        return None
    return {"itemId": item.group(1), "nameCn": name.group(1).strip(),
            "iconKey": icon.group(1) if icon else None,
            "quality": int(q.group(1)) if q else None,
            "isNew": bool(NEW_RE.search(cell))}


def mats_of(cell):
    out = []
    for m in MAT_RE.finditer(cell):
        icon = ICON_RE.search(cell[m.start():m.start() + 400])
        out.append({"nameCn": m.group(1).strip(), "count": int(m.group(2)),
                    "iconKey": icon.group(1) if icon else None})
    return out


def skill_of(cell):
    d = {}
    for k, v in SKILL_RE.findall(cell):
        d[{"o": "orange", "y": "yellow", "g": "green", "x": "grey"}[k]] = int(v)
    return d or None


def rows_of(html, cls):
    out = []
    for tb in tables(html, cls):
        for rm in ROW_RE.finditer(tb):
            out.append([c.group(1) for c in CELL_RE.finditer(rm.group(1))])
    return out


def recipes(html):
    out = []
    for cells in rows_of(html, "zk-recipes"):
        if len(cells) < 3:
            continue
        made = made_of(cells[0])
        if not made:
            continue
        row = dict(made)
        row["mats"] = mats_of(cells[1])
        row["skill"] = skill_of(cells[2])
        row["source"] = SRC_RE.search(cells[3]).group(1).strip() if len(cells) > 3 and SRC_RE.search(cells[3]) else None
        out.append(row)
    return out


def headers(tb):
    head = re.search(r"<thead>([\s\S]*?)</thead>", tb, re.I)
    if not head:
        return []
    return [re.sub(r"\s+", "", TAGS.sub("", c.group(1))) for c in CELL_RE.finditer(head.group(1))] or \
           [re.sub(r"\s+", "", TAGS.sub("", c.group(1))) for c in re.finditer(r"<th[^>]*>([\s\S]*?)</th>", head.group(1), re.I)]


def nodes(html):
    """剥皮是"怪物等级档"、钓鱼是"水域"、采矿是"矿脉"——列名各不相同，
       所以按表头对齐，不硬套固定列序。"""
    out = []
    for tb in tables(html, "zk-nodes"):
        hs = headers(tb)
        for rm in ROW_RE.finditer(tb):
            cells = [c.group(1) for c in CELL_RE.finditer(rm.group(1))]
            if len(cells) < 2:
                continue
            text = lambda c: re.sub(r"\s+", " ", TAGS.sub(" ", c)).strip()
            first = cells[0]
            nm = NAME_RE.search(first) or re.search(r'aria-label="([^"]+?)"', first)
            label = (nm.group(1).strip() if nm else text(first)) or None
            if not label:
                continue
            ic = ICON_RE.search(first)
            row = {"nameCn": label, "iconKey": ic.group(1) if ic else None,
                   "yields": [m.group(1) for m in MAT_RE.finditer(cells[1])] if len(cells) > 1 else [],
                   "zone": text(cells[2]) if len(cells) > 2 else None,
                   "skill": skill_of(cells[3]) if len(cells) > 3 else None}
            if hs:
                row["columns"] = dict(list(zip(hs, [text(c) for c in cells])))
            if not row["yields"] and len(cells) > 1 and text(cells[1]):
                row["yields"] = [text(cells[1])]
            out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    index = get("/zhuanye")
    if not index:
        sys.exit(u"取不到 /zhuanye")
    # 名字不从这里取：这里的链接一半是侧栏、一半是"专业详情"按钮，文字对不上。
    # 每个专业页自己的 <h1> 才是这一页的标题，用它。
    ids = []
    for m in re.finditer(r'href="/zhuanye/([a-z\-]+)"', index):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    profs = [{"id": pid, "kind": "gather" if pid in GATHER else "craft"} for pid in ids]
    print("专业 %d 个：%s" % (len(profs), u"、".join(p["id"] for p in profs)))

    today = datetime.date.today().isoformat()
    for p in profs:
        html = get("/zhuanye/" + p["id"])
        if not html:
            p["error"] = u"页面取不到"
            continue
        p["nameCn"] = h1(html) or GATHER.get(p["id"]) or p["id"]
        p["recipes"] = recipes(html)
        p["nodes"] = nodes(html)
        if not p["recipes"] and not p["nodes"]:
            # 上游这一页不是配方/采集点表格结构（野营就是卡片页）——如实记没解析，别写成"没有内容"
            p["unparsed"] = True
            p["note"] = u"上游这一页不是配方或采集点表格，本轮没解析出条目；有页面但不编数据"
        p["provenance"] = [{"type": "datamine_cn", "url": "%s/zhuanye/%s" % (BASE, p["id"]),
                            "note": u"配方、材料、技能难度与采集点取自无限客户端（经新手盒子转述）",
                            "checkedAt": today}]
        print("  %-16s %-6s 配方 %3d · 采集点 %2d" % (p["id"], p["nameCn"], len(p["recipes"]), len(p["nodes"])))
        time.sleep(0.3)

    nr = sum(len(p.get("recipes") or []) for p in profs)
    nn = sum(len(p.get("nodes") or []) for p in profs)
    icons = sorted({x["iconKey"] for p in profs for x in
                    (p.get("recipes") or []) + (p.get("nodes") or []) if x.get("iconKey")} |
                   {m["iconKey"] for p in profs for x in (p.get("recipes") or []) for m in x.get("mats") or []
                    if m.get("iconKey")})
    print("合计配方 %d、采集点 %d、涉及图标文件名 %d 个" % (nr, nn, len(icons)))
    if not args.write:
        print("（未写盘，加 --write）")
        return
    if not os.path.isdir(UP):
        os.makedirs(UP)
    payload = {"meta": {"source": BASE + "/zhuanye", "site": u"新手盒子 · 魔兽世界无限数据库",
                        "scrapedAt": today,
                        "method": "tools/scrape-wclbox-prof.py --write",
                        "took": u"制成品与物品 ID、材料清单与数量、技能难度四档、来源方式、采集点与可得物",
                        "skipped": u"冲级路线建议、BiS 结论、攻略文字、任何百分比",
                        "iconKeys": icons},
               "professions": profs}
    out = os.path.join(UP, "wclbox-professions.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print("已写入 %s" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
