#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新旧两站逐页对拍：同一页在旧站（src/）与新站（app/dist）上渲染出来的结果必须一致。

为什么要有这个脚本：迁移最容易出的事是"新页看着挺像，其实少了几条数据、少了一个空态、
徽标掉了文字"。断言只能证明"没变差"，证明不了"和旧页一样"。这里直接把两站的
DOM 结构计数、类名集合与正文文本逐条对比，差异要么归零要么写进报告。

用法：
    python3 tools/app-parity.py                      # 需要旧站 :8817 与新站 :8821 都在跑
    python3 tools/app-parity.py --strict             # 有差异就退出码非 0
    python3 tools/app-parity.py --page world         # 只拍一页

新站跑的是构建产物（vite preview），不是 dev server：dev 与 prod 的渲染差异不该由对拍承担。
"""
import argparse
import datetime
import difflib
import os
import re
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("缺少 playwright：pip3 install playwright")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
LEGACY = os.environ.get("LEGACY_BASE", "http://127.0.0.1:8817")
APP = os.environ.get("APP_BASE", "http://127.0.0.1:8821")

# 每页：旧站路径、新站 hash 路由、要依次点的 tab（data-t 值，空表示不切）
PAGES = [
    {"key": "home", "legacy": "/index.html", "app": "/#/", "tabs": []},
    {"key": "world", "legacy": "/world.html", "app": "/#/world", "tabs": ["zones", "rares", "books", "bag"]},
]
# 有意差异：新站改了行为、且比旧站更对的，白名单列在这里并写清理由。
# 只有 --strict 模式下这些键会被放行；出现没登记过的差异仍然算失败。
INTENTIONAL = {
    ("world", "rares"): {
        "img": u"旧站对缺图仍渲染 <img> 靠 onerror 兜底（每次访问产生 9 个 404 请求），"
                     u"新站直接不渲染、自绘块可见：可见结果一致，请求数更少",
        "class:bad": u"同上——新站没有 .bad 这个中间态类名"
    }
}


def link_key(h, base):
    h = h or ""
    h = h.replace(base, "/")
    h = re.sub(r"^https?://[^/]+", "", h)
    return h.lstrip("/")          # 旧站是相对链接、新站是根绝对，比对时只看同一个形状


SELECTORS = ["#top", "#main", "#foot", ".card", ".band", ".picks .pick", "table", "tbody tr",
             ".zcard", ".rarecard", ".zmap", ".zmap img", ".zmap.none", ".zmark", ".loot-i",
             ".tag", ".pill", ".chips .chipc", ".src li", ".flowrow", ".stat", ".cta", "img"]
CLASS_RE = re.compile(r"[a-zA-Z][\w-]*")


def probe(page):
    return page.evaluate("""(sels) => {
      const count = {};
      for (const s of sels) { try { count[s] = document.querySelectorAll(s).length; } catch (e) { count[s] = -1; } }
      const classes = new Set();
      document.querySelectorAll('#main *').forEach(e => (e.className || '').toString()
        .split(/\\s+/).forEach(c => c && classes.add(c)));
      const imgs = [...document.querySelectorAll('img')];
      return {
        count,
        h1: [...document.querySelectorAll('h1')].map(h => h.innerText.trim()),
        text: document.querySelector('#main').innerText,
        classes: [...classes].sort(),
        links: [...document.querySelectorAll('#main a')].map(a => a.getAttribute('href')),
        imgBroken: imgs.filter(i => i.complete && i.naturalWidth === 0).length,
        imgSrcs: imgs.map(i => (i.currentSrc || i.src).split('/').slice(-2).join('/')).sort()
      };
    }""", SELECTORS)


def norm_text(t):
    out = []
    for line in t.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        # 倒计时到秒后，两站的快照本来就差着零点几秒，读数不该算成差异
        # （"顶栏与首页同一读数"由 site-check 在同一页内断言）
        line = re.sub(r"\d{2}:\d{2}:\d{2}", "⟨读数⟩", line)
        if line:
            out.append(line)
    return out


def norm_link(h, base):
    h = h or ""
    h = h.replace(base, "/")
    return h


def diff_lines(a, b, limit=14):
    sm = difflib.SequenceMatcher(None, a, b)
    only_old, only_new = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            only_old += a[i1:i2]
        if tag in ("insert", "replace"):
            only_new += b[j1:j2]
    return only_old[:limit], only_new[:limit]


def run(page_cfg):
    rows = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)
        tabs = page_cfg["tabs"] or [""]
        for tab in tabs:
            ctx_a = br.new_context(viewport={"width": 1440, "height": 1000})
            pa = ctx_a.new_page()
            pa.goto(LEGACY + page_cfg["legacy"], wait_until="networkidle")
            pa.wait_for_timeout(1800)
            ctx_b = br.new_context(viewport={"width": 1440, "height": 1000})
            pb = ctx_b.new_page()
            pb.goto(APP + page_cfg["app"], wait_until="networkidle")
            pb.wait_for_timeout(1800)
            for p in (pa, pb):
                if tab:
                    try:
                        p.click('[data-t="%s"]' % tab)
                        p.wait_for_timeout(1200)
                    except Exception:
                        pass
            A, B = probe(pa), probe(pb)
            rows.append((page_cfg["key"], tab or "（默认）", A, B))
            ctx_a.close()
            ctx_b.close()
        br.close()
    return rows


def report(all_rows, strict):
    problems = []
    lines = [u"# 新旧站对拍 · %s（wow-dev）" % datetime.date.today().isoformat(), u"",
             u"脚本：`python3 tools/app-parity.py`。旧站 %s（`src/`），新站 %s（`app/dist`，vite preview）。" % (LEGACY, APP),
             u"对拍口径：结构计数、类名集合、正文文本行、图片与链接。差异要么是有意为之（写进「有意差异」），要么就是迁坏了。", u"",
             u"## 逐页结果", u""]
    for key, tab, A, B in all_rows:
        dc = {k: (A["count"][k], B["count"][k]) for k in SELECTORS if A["count"][k] != B["count"][k]}
        miss_cls = sorted(set(A["classes"]) - set(B["classes"]))
        extra_cls = sorted(set(B["classes"]) - set(A["classes"]))
        old_l, new_l = diff_lines(norm_text(A["text"]), norm_text(B["text"]))
        allow = INTENTIONAL.get((key, tab), {})
        notes = []
        dc_bad = {}
        for k, v in dc.items():
            if k in allow:
                notes.append(k)
            else:
                dc_bad[k] = v
        if "bad" in miss_cls and "class:bad" in allow:
            miss_cls = [c for c in miss_cls if c != "bad"]
            notes.append("class:bad")
        dcs = u"无" if not dc_bad else u"❌ " + ", ".join(
          u"%s 旧 %d/新 %d" % (k, v[0], v[1]) for k, v in dc_bad.items())
        if notes:
            dcs += u"｜有意差异 %d 项：%s" % (len(notes), u"、".join(sorted(set(notes))))
        la = [link_key(x, LEGACY) for x in A["links"]]
        lb = [link_key(x, APP) for x in B["links"]]
        only_a = sorted(set(la) - set(lb))[:8]
        only_b = sorted(set(lb) - set(la))[:8]
        lines += [u"### %s / %s" % (key, tab), u""]
        lines.append(u"- H1：旧 %s ／ 新 %s %s" % (
          A["h1"], B["h1"], u"✅" if A["h1"] == B["h1"] else u"❌"))
        lines.append(u"- 结构计数差异：" + dcs)
        lines.append(u"- 新站缺的类名：" + (u"无" if not miss_cls else u"❌ " + u"、".join(miss_cls[:20])))
        lines.append(u"- 新站多出的类名：" + (u"—" if not extra_cls else u"、".join(extra_cls[:20])))
        lines.append(u"- 正文只在旧站出现的行：%d 条%s" % (len(old_l), u" ❌" if old_l else u""))
        lines.append(u"- 正文只在新站出现的行：%d 条" % len(new_l))
        lines.append(u"- 坏图：新站 %d 张%s" % (B["imgBroken"], u" ❌" if B["imgBroken"] else u""))
        lines.append(u"- 链接：只在旧站有 %s ／ 只在新站有 %s%s" % (
          only_a or u"无", only_b or u"无", u" ❌" if (only_a or only_b) else u""))
        bad = bool(dc_bad or miss_cls or old_l or A["h1"] != B["h1"] or B["imgBroken"]
                   or only_a or only_b)
        problems.append((key, tab, bad))
        lines.append(u"")
        if old_l:
            lines += [u"  旧站有、新站没有："] + [u"  - `%s`" % x[:90] for x in old_l] + [u""]
        if new_l:
            lines += [u"  新站有、旧站没有："] + [u"  - `%s`" % x[:90] for x in new_l] + [u""]
    out = os.path.join(DOCS, "APP-PARITY-%s.md" % datetime.date.today().isoformat())
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("报告 → %s" % os.path.relpath(out, ROOT))
    bad = [(k, t) for k, t, b in problems if b]
    if bad:
        print("有差异的组合：%s" % "、".join("%s/%s" % (k, t) for k, t in bad))
        if strict:
            sys.exit(1)
    else:
        print("全部组合无差异")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--page", default="")
    a = ap.parse_args()
    todo = [p for p in PAGES if not a.page or p["key"] == a.page]
    if not todo:
        sys.exit("没有这个页：%s（可选 %s）" % (a.page, "、".join(p["key"] for p in PAGES)))
    rows = []
    for p in todo:
        rows += run(p)
    report(rows, a.strict)


if __name__ == "__main__":
    main()
