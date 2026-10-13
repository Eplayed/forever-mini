#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 wowforever.wclbox.com 每座副本详情页的「任务 / 任务物品 / 任务起始地点」三节。

为什么只要这三节：本站副本详情页缺任务这块（见 docs/PLAN-open-items.md 第 17 条），
wclbox 的 35 座都带着，是目前覆盖面最全的一条路（wowhead 只有 4 座新本有条目）。

**刻意不抓的两类东西**（仓库根红线，不是忘了）：
  1. 任务目标描述整句（"在奥格瑞玛找到怒焰裂谷，杀掉 8 个……然后向……复命"）——
     那是文案，红线要求第三方站只取事实性标识符（名称 / 等级 / 数量 / 归属）。
  2. 掉落概率（"(<0.1%)" "(40%)"）——本站掉落一律不写概率。
产出只写 src/data/upstream/，不直接改成品数据文件；要上页面得再过 merge 与 build-data。

用法：
    python3 tools/scrape-wclbox-quests.py                 # 全部 35 座
    python3 tools/scrape-wclbox-quests.py --only ragefire-chasm,gnomeregan
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
OUT = os.path.join(UP, "wclbox-dungeon-quests.json")

NUM = re.compile(r"([\d,]+)")


def to_int(s):
    if not s:
        return None
    m = NUM.search(s)
    return int(m.group(1).replace(",", "")) if m else None


def parse_card(text):
    """一张任务卡 → 只留带标签的事实项。

    标签和值可能同行也可能分行（页面是 div 拼的），所以先把整张卡压成一行再非锚定匹配，
    比按行判断稳。**没有标签的那句任务目标描述不会被任何正则命中，等于就地丢掉**——
    这是刻意的：第三方站的文案不进我们的数据。"""
    blob = re.sub(r"\s+", " ", text or "").strip()
    if not blob:
        return None
    # 卡面第一行就是「任务名 等级 N」，按「等级」切一刀才拿得到干净的名字
    name = re.split(r"\s+等级\s|\s{2,}", blob)[0].strip()
    m = re.search(r"(?:^|\s)等级\s*(\d+)", blob)
    mr = re.search(r"最低接取等级\s*(\d+)", blob)
    mx = re.search(r"经验奖励\s*([\d,]+)", blob)
    mp = re.search(r"接取(?:地点|位置)\s*([^\s，]+)(?:，([^\s，]+))?", blob)
    mq = re.search(r"前置任务\s*([^\s，]+)", blob)
    return {
        "name": name or None,
        "questLevel": to_int(m.group(1)) if m else None,
        "reqLevel": to_int(mr.group(1)) if mr else None,
        "xp": to_int(mx.group(1)) if mx else None,
        "pickupNpc": mp.group(1) if mp else None,
        "pickupZone": mp.group(2) if mp else None,
        "preQuest": mq.group(1) if mq else None,
    } if name else None


PAGE_JS = r"""() => {
  const clean = s => (s || '').replace(/\u00a0/g, ' ').replace(/[ \t]+/g, ' ').trim();
  const chapters = [...document.querySelectorAll('.fbx-chapter')].map(ch => {
    const head = ch.querySelector('h2, h3, .fbx-title, header');
    const tables = [...ch.querySelectorAll('table')].map(t => ({
      head: [...t.querySelectorAll('th')].map(x => clean(x.innerText)),
      rows: [...t.querySelectorAll('tbody tr')].map(r =>
        [...r.querySelectorAll('td')].map(c => clean(c.innerText)))
    }));
    const cards = [...ch.querySelectorAll('.fbx-quest')].map(e => {
      // 只取这张卡自己的文本行；带标签的行才解析，描述句留给上游，我们不落盘
      const lines = clean(e.innerText).split('\n').map(x => x.trim()).filter(Boolean);
      return {lines: lines, raw: clean(e.innerText)};
    });
    return {title: head ? clean(head.innerText) : '', tables: tables, cards: cards};
  });
  const h1 = document.querySelector('h1');
  return {title: h1 ? clean(h1.innerText) : '', chapters: chapters,
          tabs: [...document.querySelectorAll('a,button')].map(e => clean(e.innerText))
                  .filter(t => /^(任务|任务物品|任务起始地点)( \d+)?$/.test(t))};
}"""


def collect(slugs):
    from playwright.sync_api import sync_playwright
    found = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 1100}).new_page()
        for i, slug in enumerate(slugs):
            url = "%s/fuben/%s" % (BASE, slug)
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                print("  ! %s 打不开：%s" % (slug, str(e)[:70]))
                continue
            # 正文是渲染出来的：等章节真的进 DOM 再读，拿不到就跳过这座（不猜结构）
            try:
                page.wait_for_selector('.fbx-chapter', timeout=15000)
            except Exception:
                print("  ! %s 没有 .fbx-chapter，跳过（页面结构可能变了）" % slug)
                continue
            page.wait_for_timeout(800)
            # 三节是点开的：只点"带条数的那个页签"（文本形如「任务 6」）。
            # 不能按裸「任务」去点——站内主导航也有一格叫「任务」，点下去就跳走了
            # （第一版就是这么把章节数读成 0 的：页面已经不是这座本了）。
            page.evaluate("""() => {
              [...document.querySelectorAll('a,button')].forEach(e => {
                if (/^(任务|任务物品|任务起始地点)\\s+\\d+$/.test((e.innerText||'').replace(/\\s+/g,' ').trim())) e.click();
              });
            }""")
            page.wait_for_timeout(900)
            data = page.evaluate(PAGE_JS)
            found[slug] = {"url": url, "pageH1": data["title"], "tabs": sorted(set(data["tabs"])),
                           "chapters": data["chapters"]}
            print("  %2d/%d %s：%d 节 / 页签 %s" % (i + 1, len(slugs), slug, len(data["chapters"]),
                                                  "、".join(found[slug]["tabs"]) or "无"))
            page.wait_for_timeout(700)
        browser.close()
    return found


def shape(raw):
    """把抓到的原始节转成落盘结构：只留标签字段与表格，描述句不进文件。"""
    quests, items, starts, summary = [], [], [], None
    for ch in raw["chapters"]:
        title = ch["title"] or ""
        tables = ch["tables"]
        if "任务起始" in title:
            for t in tables:
                for r in t["rows"]:
                    starts.append(dict(zip(t["head"], r)))
        elif "任务物品" in title:
            for t in tables:
                for r in t["rows"]:
                    items.append(dict(zip(t["head"], r)))
        elif re.match(r"^任务", title):
            for c in ch["cards"]:
                q = parse_card(c["raw"])
                if q:
                    quests.append(q)
            for t in tables:
                if summary is None and t["rows"]:
                    summary = {"head": t["head"], "rows": t["rows"]}
    return {"quests": quests, "questItems": items, "questStarts": starts, "questSummary": summary}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔的 slug，默认跑名单里全部")
    args = ap.parse_args()
    dg = json.load(io.open(os.path.join(ROOT, "src", "data", "dungeons.json"), encoding="utf-8"))
    rows = (dg.get("newDungeons") or []) + (dg.get("classicDungeons") or [])
    pairs = [(r.get("upstreamSlug") or r["id"], r["id"], r.get("nameCn") or r.get("nameEn")) for r in rows]
    if args.only:
        want = set(x.strip() for x in args.only.split(",") if x.strip())
        pairs = [x for x in pairs if x[0] in want or x[1] in want]
    print("要抓 %d 座" % len(pairs))
    raw = collect([p[0] for p in pairs])
    dungeons = {}
    for slug, our_id, name in pairs:
        r = raw.get(slug)
        if not r:
            continue
        s = shape(r)
        s.update({"wowheadSlug": slug, "ourDungeonId": our_id, "nameCn": name,
                  "url": r["url"], "pageTabs": r["tabs"]})
        dungeons[slug] = s
    out = {
        "meta": {
            "site": BASE, "source": "每座副本详情页的任务 / 任务物品 / 任务起始地点三节",
            "scrapedAt": datetime.date.today().isoformat(),
            "tool": "tools/scrape-wclbox-quests.py",
            "note": "渲染后 DOM 抓取。只落带标签的事实项（任务名、任务等级、最低接取等级、"
                    "经验值、接取 NPC 与地点、前置任务、任务物品归属、起始地点）。"
                    "任务目标描述整句与掉落概率刻意没抓——第三方站只取事实性标识符，"
                    "本站掉落不写概率。经验值是经典旧世的开放数据库数字，无限可能有调整。",
            "counts": {"dungeons": len(dungeons),
                       "withQuests": len([v for v in dungeons.values() if v["quests"]]),
                       "quests": sum(len(v["quests"]) for v in dungeons.values()),
                       "questItems": sum(len(v["questItems"]) for v in dungeons.values()),
                       "questStarts": sum(len(v["questStarts"]) for v in dungeons.values())}
        },
        "dungeons": dungeons
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    c = out["meta"]["counts"]
    print("已写 %s：%d 座 / 有任务 %d 座 / 任务 %d 条 / 任务物品 %d 条 / 起始地点 %d 条" % (
        os.path.relpath(OUT, ROOT), c["dungeons"], c["withQuests"], c["quests"],
        c["questItems"], c["questStarts"]))


if __name__ == "__main__":
    main()
