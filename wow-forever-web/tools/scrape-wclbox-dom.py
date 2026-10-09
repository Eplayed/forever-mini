#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用真实浏览器抓 wowforever.wclbox.com 的客户端渲染内容（副本卡片 / 天赋树）。

为什么用浏览器：这些站的导航是服务端渲染的，正文卡片和天赋树要等 JS 跑完才在 DOM 里，
curl 拿不到。产出只写 data/upstream/，不直接改成品数据文件——上游转述要先过一遍合并与体检。

用法：
    python3 tools/scrape-wclbox-dom.py --what cards
    python3 tools/scrape-wclbox-dom.py --what talents
"""
import argparse
import datetime
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "src", "data", "upstream")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["cards", "talents", "all"], default="all")
    args = ap.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        if args.what in ("cards", "all"):
            cards(browser)
        if args.what in ("talents", "all"):
            talents(browser)
        browser.close()


if __name__ == "__main__":
    main()
