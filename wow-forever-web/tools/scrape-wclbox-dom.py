#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用真实浏览器抓 wowforever.wclbox.com 的客户端渲染内容（副本卡片 / 天赋树）。

为什么用浏览器：这些站的导航是服务端渲染的，正文卡片和天赋树要等 JS 跑完才在 DOM 里，
curl 拿不到。产出只写 data/upstream/，不直接改成品数据文件——上游转述要先过一遍合并与体检。

用法：
    python3 tools/scrape-wclbox-dom.py --what cards
    python3 tools/scrape-wclbox-dom.py --what talents
    python3 tools/scrape-wclbox-dom.py --what bossfaces   # 35 个副本页逐个读，约 2–3 分钟
"""
import argparse
import datetime
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "app", "data", "upstream")
BASE = "https://wowforever.wclbox.com"
CLASSES = ["warrior", "paladin", "hunter", "rogue", "priest", "shaman", "mage", "warlock", "druid"]

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("缺少 playwright：pip3 install playwright")

CARDS_JS = r"""() => {
  const out = [];
  document.querySelectorAll('a.fb-card-link').forEach(a => {
    const art = a.querySelector('.fb-card-art');
    const style = art ? (art.getAttribute('style') || '') : '';
    const m = /url\(([^)]+)\)/.exec(style);
    const meta = [...a.querySelectorAll('.fb-card-meta span')].map(s => s.textContent.replace(/\s+/g, ' ').trim());
    const zone = a.querySelector('.fb-card-zone');
    out.push({
      slug: (a.getAttribute('href') || '').split('/').pop(),
      name: (a.querySelector('strong') || {}).textContent || '',
      range: ((a.querySelector('.fb-card-range') || {}).textContent || '').replace(/\s+/g, '').replace('级', ''),
      isNew: !!a.querySelector('.fb-card-seal'),
      zone: zone ? zone.textContent.replace(/\s+/g, ' ').trim() : null,
      art: m ? m[1] : null,
      bosses: meta.length > 0 ? meta[0] : null,
      drops: meta.length > 1 ? meta[1] : null,
      href: a.getAttribute('href')
    });
  });
  return out;
}"""

TALENT_JS = r"""() => {
  const grids = [...document.querySelectorAll('.tf-grid')].map(g => ({
    title: (g.closest('section') || g.parentElement || {}).querySelector
      ? ((g.closest('section').querySelector('h2,h3,.tfb-title,strong') || {}).textContent || '').trim() : '',
    connectors: [...g.querySelectorAll('.tf-connectors line, .tf-connectors path')].map(l => ({
      x1: parseFloat(l.getAttribute('x1') || l.getAttribute('data-x1') || 0),
      y1: parseFloat(l.getAttribute('y1') || 0),
      x2: parseFloat(l.getAttribute('x2') || 0),
      y2: parseFloat(l.getAttribute('y2') || 0),
      d: l.tagName === 'path' ? l.getAttribute('d') : null,
      cls: l.getAttribute('class') || ''
    })),
    viewBox: (g.querySelector('.tf-connectors') || {}).getAttribute
      ? g.querySelector('.tf-connectors').getAttribute('viewBox') : null,
    nodes: [...g.querySelectorAll('.tf-node')].map(n => {
      const img = n.querySelector('img');
      const cls = n.className || '';
      const chg = (/tf-change-([a-z]+)/.exec(cls) || [, null])[1];
      const label = n.getAttribute('aria-label') || '';
      const mm = /^(.*)，(\d+)\/(\d+) 点$/.exec(label);
      return {
        id: n.getAttribute('data-talent-id'),
        name: mm ? mm[1].trim() : label,
        maxRanks: mm ? parseInt(mm[3], 10) : null,
        row: parseInt((n.style.gridRow || '0'), 10) || null,
        col: parseInt((n.style.gridColumn || '0'), 10) || null,
        change: chg,
        icon: img ? (/(?:large|56|tubiao)\/([a-z0-9_]+)\./i.exec(img.src) || [, null])[1] : null
      };
    })
  }));
  const refs = [...document.querySelectorAll('.talent-reference-entry')].forEach ? [] : [];
  [...document.querySelectorAll('.talent-reference-entry')].forEach(e => {
    const ranks = [];
    e.querySelectorAll('details dl').forEach(dl => {
      const dt = dl.querySelector('dt'), dd = dl.querySelector('dd');
      if (dt && dd) ranks.push({ label: dt.textContent.replace(/\s+/g, ' ').trim(),
                                 text: dd.textContent.replace(/\s+/g, ' ').trim() });
    });
    refs.push({
      id: e.id.replace(/^talent-info-/, ''),
      name: (e.querySelector('.talent-reference-name h4') || {}).textContent || '',
      tag: (e.querySelector('.tfk-tag') || {}).textContent || '',
      condition: (e.querySelector('.talent-reference-condition') || {}).textContent
        ? e.querySelector('.talent-reference-condition').textContent.replace(/\s+/g, ' ').trim() : null,
      effect: (e.querySelector('.talent-reference-effect') || {}).textContent
        ? e.querySelector('.talent-reference-effect').textContent.replace(/\s+/g, ' ').trim() : null,
      changeNote: (e.querySelector('.talent-reference-change') || {}).textContent
        ? e.querySelector('.talent-reference-change').textContent.replace(/\s+/g, ' ').trim() : null,
      ranks: ranks
    });
  });
  return { grids: grids, refs: refs };
}"""


def write(name, payload):
    if not os.path.isdir(UP):
        os.makedirs(UP)
    path = os.path.join(UP, name)
    io.open(path, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print("已写 %s" % os.path.relpath(path, ROOT))


def cards(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(BASE + "/fuben", wait_until="networkidle")
    page.wait_for_timeout(2500)
    rows = page.evaluate(CARDS_JS)
    page.close()
    print("副本卡片 %d 张（带图 %d，标新 %d）" % (
        len(rows), len([r for r in rows if r["art"]]), len([r for r in rows if r["isNew"]])))
    for r in rows[:4]:
        print("   %-24s %-8s %s" % (r["slug"], r["range"], r["zone"]))
    write("wclbox-cards.json", {"meta": {"source": BASE + "/fuben",
                                         "scrapedAt": datetime.date.today().isoformat(),
                                         "note": "渲染后 DOM 抓取：卡片含载入图路径、所在区域与阵营、首领与掉落计数"},
                                "cards": rows})


def talents(browser):
    today = datetime.date.today().isoformat()
    total_nodes = total_refs = 0
    for cid in CLASSES:
        page = browser.new_page(viewport={"width": 1600, "height": 1200})
        page.goto("%s/tianfu/%s" % (BASE, cid), wait_until="networkidle")
        page.wait_for_timeout(2500)
        data = page.evaluate(TALENT_JS)
        page.close()
        n = sum(len(g["nodes"]) for g in data["grids"])
        total_nodes += n
        total_refs += len(data["refs"])
        write("wclbox-talent-%s.json" % cid, {
            "meta": {"classId": cid, "source": "%s/tianfu/%s" % (BASE, cid),
                     "scrapedAt": today,
                     "note": u"渲染后 DOM 抓取：节点格子位置、改动标记、图标文件名、层级与前置文字、各级效果与经典旧世对照"},
            "grids": data["grids"], "refs": data["refs"]})
        print("  %-8s 树 %d / 节点 %d / 说明 %d" % (cid, len(data["grids"]), n, len(data["refs"])))
    print("合计节点 %d、说明 %d" % (total_nodes, total_refs))


BOSS_FACES_JS = r"""() => {
  const out = [];
  document.querySelectorAll('section.sj-boss').forEach(s => {
    const h = s.querySelector('h2'), f = s.querySelector('span.sj-face');
    if (!h) return;
    const style = f ? (f.getAttribute('style') || '') : '';
    const face = (/(?:url\(([^)]+)\)|background-image:\s*url\(([^)]+)\))/).exec(style);
    out.push({
      // h2 的 id 形如 "h-rhahkzor"，去掉前缀就是它的键；我们 dungeons.json 里的首领 id
      // 可能带连字符（rhahk-zor），两边不同名，所以只认这里读回来的头像路径，不自己拼
      bossKey: (h.id || '').replace(/^h-/, ''),
      face: face ? (face[1] || face[2] || '').replace(/^["']|["']$/g, '') : null,
      unknown: f ? f.hasAttribute('data-unknown') : null
    });
  });
  return out;
}"""


def boss_faces(browser):
    """逐个副本页读首领头像的真实路径。

    为什么不能自己拼 URL：源站的头像文件名是它自己那套首领键（rhahkzor），
    与我们 dungeons.json 里的 id（rhahk-zor）不同名，猜出来的地址会大面积 404，
    那是我们的错不是源站缺。只取路径这一件事实性标识符，不取页面上的任何文字。
    """
    cards_p = os.path.join(UP, "wclbox-cards.json")
    if not os.path.exists(cards_p):
        sys.exit(u"先跑 --what cards，拿到副本页地址才有得读")
    doc = json.load(io.open(cards_p, encoding="utf-8"))
    rows = {}
    for c in doc.get("cards") or []:
        href = c.get("href") or ("/fuben/" + c["slug"])
        rows[c["slug"]] = href
    print(u"副本页 %d 个，逐个读首领头像路径" % len(rows))
    out, total, with_face = [], 0, 0
    for slug, href in sorted(rows.items()):
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(BASE + href, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1800)
            faces = page.evaluate(BOSS_FACES_JS)
        except Exception as e:
            print(u"  %s 读失败：%s" % (slug, str(e)[:60]))
            faces = []
        page.close()
        for f in faces:
            f["dungeonSlug"] = slug
            f["sourceUrl"] = BASE + href
        total += len(faces)
        n = len([f for f in faces if f["face"]])
        with_face += n
        out += faces
        print(u"  %-28s 首领 %d ｜ 有头像 %d" % (slug, len(faces), n))
    write("wclbox-boss-faces.json", {
        "meta": {"source": BASE + "/fuben 各副本页", "scrapedAt": datetime.date.today().isoformat(),
                 "method": u"渲染后 DOM 读 section.sj-boss 的 span.sj-face 内联背景路径",
                 "note": u"只取头像文件路径这一个标识符；data-unknown 表示源站自己也没有这张脸",
                 "bosses": total, "withFace": with_face},
        "faces": out})
    print(u"合计首领 %d，源站有头像 %d，没有 %d" % (total, with_face, total - with_face))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["cards", "talents", "bossfaces", "all"], default="all")
    args = ap.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        if args.what in ("cards", "all"):
            cards(browser)
        if args.what in ("talents", "all"):
            talents(browser)
        if args.what in ("bossfaces",):
            boss_faces(browser)
        browser.close()


if __name__ == "__main__":
    main()
