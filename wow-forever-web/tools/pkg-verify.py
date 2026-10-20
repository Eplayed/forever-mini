#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布包本机验收（Q05，2026-10-20）。拿**真静态服务器**跑包，不用 vite preview。

为什么不能用 preview 交这一关：vite preview 带 SPA 兜底——任何找不到文件的请求都
返回 index.html 且 200。于是"缺一个 .jpg""数据路径写错"这类事在它上面全是绿的，
到了真托管（Nginx / 对象存储 / Pages）就变成 404 或整页空白。这条坑本轮已经踩过一次
（route-smoke 只查状态码被兜底骗过），所以这里刻意用 http.server：它**没有**兜底，
更接近"把目录扔上去"的托管方，缺文件就是 404。

钉的几件事（对应派工单 Q05 那一段）：
  1. base 用相对路径之后，挂根目录与挂子路径 /wow/ 两种都真能开（不能只改成 ./ 就当完事）；
  2. hash 路由的直达 / 刷新 / 换设备分享（新上下文、无历史无 referer）都能渲染出内容；
  3. 旧页地址 talent.html 这一类：包里必须有桩，且带着查询串跳到位（不是被兜底吞成首页）；
  4. JSON / JS / CSS / 图片的 Content-Type 正确，缺的 .jpg 必须是 404 而不是 200 HTML；
  5. 站内的未知 hash 路由走"这页还没迁过来"，不给空白页。

用法：python3 tools/pkg-verify.py [--site release/<名>/site]
退出码：有任何一条不过就非 0。
"""
from __future__ import print_function

import argparse
import functools
import http.server
import json
import os
import re
import socketserver
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []
FAILED = []
SHOT_DIR = os.path.join(ROOT, "docs", "screenshots", "check-" + __import__("datetime").date.today().isoformat())


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    if not ok:
        FAILED.append(name)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail else ""))


def serve(dirpath):
    """起一个只读静态服务（无 SPA 兜底），返回 (base, shutdown)。"""
    class Quiet(http.server.SimpleHTTPRequestHandler):   # 不静音的话 3700 个 GET 会把结果冲掉
        def log_message(self, *a):
            pass
    httpd = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=dirpath))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return "http://127.0.0.1:%d" % httpd.server_address[1], httpd


def head(url):
    import urllib.request
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.headers.get("Content-Type", "")
    except Exception as e:                      # noqa: BLE001
        code = getattr(e, "code", None)
        return (code or 0), getattr(e, "reason", str(e))[:40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=None, help="要验收的目录（默认取 release/latest.json 指的那一版）")
    a = ap.parse_args()
    if not a.site:
        latest = os.path.join(ROOT, "release", "latest.json")
        if not os.path.exists(latest):
            sys.exit("没给 --site，也没有 release/latest.json；先跑 tools/release-package.py")
        cur = json.load(open(latest, encoding="utf-8"))["current"]["package"]
        a.site = os.path.join(ROOT, "release", cur, "site")
    site = os.path.abspath(a.site)
    if not os.path.isdir(site):
        sys.exit("没有产物目录 %s" % site)
    print("验收产物：%s" % site)
    os.makedirs(SHOT_DIR, exist_ok=True)

    # 挂两种：根目录、子路径 /wow/（用软链，不复制 28 MB）
    import tempfile
    parent = tempfile.mkdtemp(prefix="pkgverify-")
    os.symlink(site, os.path.join(parent, "wow"))
    base_root, s1 = serve(site)
    base_sub, s2 = serve(parent)
    print("根目录挂载 %s / 子路径挂载 %s/wow/" % (base_root, base_sub))

    print("\n[A] 资源类型与缺文件（无兜底的静态服务器）")
    st, ct = head(base_root + "/")
    check("根目录 / 与 /wow/ 都回 200 text/html", st == 200 and "html" in ct, "%s %s" % (st, ct))
    st2, ct2 = head(base_sub + "/wow/")
    check("子路径 /wow/ 同样 200 text/html", st2 == 200 and "html" in ct2, "%s %s" % (st2, ct2))
    html = open(os.path.join(site, "index.html"), encoding="utf-8").read()
    refs = [r for r in re.findall(r'(?:src|href)="([^"]+)"', html) if not r.startswith(("http", "data:"))]
    TYPES = {".js": "javascript", ".css": "text/css", ".svg": "image/svg", ".png": "image/png",
             ".ico": "x-icon", ".woff2": "font", ".webp": "image/webp", ".jpg": "image/jpeg",
             ".html": "text/html"}
    bad = []
    for r in refs:
        rel = r.lstrip("./")
        if not rel or rel.startswith("#"):
            continue
        s, c = head(base_root + "/" + rel)
        ext = os.path.splitext(rel)[1].lower()
        want = TYPES.get(ext)
        if s != 200 or (want and want not in c):
            bad.append("%s → %s %s" % (rel, s, c))
    check("index.html 引用的每个本地资源都在、类型正确（不是 200 HTML 兜底）", not bad,
          "; ".join(bad[:3]) or "%d 个" % len(refs))
    s, c = head(base_root + "/data/meta.json")
    check("data/*.json 是 application/json", s == 200 and "json" in c, "%s %s" % (s, c))
    s, c = head(base_root + "/img/icons/inv_misc_questionmark.jpg")
    check("存在的图标是 image/jpeg", s == 200 and "jpeg" in c, "%s %s" % (s, c))
    s, c = head(base_root + "/img/icons/definitely_not_a_real_icon.jpg")
    check("缺的 .jpg 必须 404，不许被 200 HTML 冒充（preview 会假绿）", s == 404 and "html" not in c,
          "%s %s" % (s, c))
    s, c = head(base_root + "/data/upstream/anything.json")
    check("upstream 原料不在包里（请求它得 404）", s == 404, "%s" % s)

    print("\n[B] 旧页地址（talent.html 这一类）")
    stubs = [f for f in os.listdir(site) if f.endswith(".html") and f != "index.html"]
    check("每个旧页都有一个跳转桩（%d 个）" % len(stubs), len(stubs) >= 18, "、".join(stubs[:5]))
    s, c = head(base_root + "/talent.html")
    check("/talent.html 回的是桩自己（200 text/html），不是被兜底换成首页", s == 200 and "html" in c,
          "%s %s" % (s, c))
    body = open(os.path.join(site, "talent.html"), encoding="utf-8").read()
    check("桩用相对路径跳 ./#/talent（挂根目录与子路径都成立）",
          "./#/talent" in body and "http://" not in body and "https://" not in body, body[:0] or "无绝对地址")

    from playwright.sync_api import sync_playwright
    print("\n[C] 浏览器里真开一遍（直达 / 刷新 / 分享 / 子路径）")
    with sync_playwright() as p:
        br = p.chromium.launch(channel="chrome", headless=True)

        def open_url(base, url_hash):
            """每次都开一个全新的上下文：这就是"别人把链接发到群里、你点开"的样子
            ——没有历史、没有 referer、没有缓存，能开才算直达能用。"""
            ctx = br.new_context(viewport={"width": 1440, "height": 1000})
            pg = ctx.new_page()
            fails = []
            pg.on("response", lambda r: fails.append("%d %s" % (r.status, r.url.rsplit("/", 1)[-1]))
                  if r.status >= 400 and "not_a_real_icon" not in r.url else None)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:100]))
            pg.goto(base + url_hash, wait_until="networkidle")
            pg.wait_for_timeout(2500)
            pg.on("close", lambda _p, c=ctx: c.close())
            return pg, fails, errs

        # 1) 根目录直达子页
        #    判据按数据来：world.json 里前几个区域名必须出现在页面上，
        #    只量"有几个卡片"会被页面结构的变化悄悄放宽（这一页的卡片数本来就是 2）。
        zones = json.load(open(os.path.join(site, "data", "world.json"), encoding="utf-8"))["zones"]
        want_names = [z0["nameCn"] for z0 in zones[:6]]
        pg, fails, errs = open_url(base_root, "/#/world")
        n = pg.evaluate("() => document.querySelectorAll('#main .zonecard, #main .card').length")
        txt = pg.evaluate("() => (document.querySelector('#main') || {}).innerText || ''")
        miss = [w for w in want_names if w not in txt]
        check("根目录 #/world 直达能渲染出区域内容（数据真的取到了）",
              n >= 2 and len(txt) > 5000 and not miss and not errs,
              "%d 个卡片 / %d 字 / 缺区域名 %s / 报错 %s" % (n, len(txt), miss or "无", errs[:1]))
        check("根目录 #/world 没有失败请求", not fails, "; ".join(fails[:3]) or "干净")
        # 2) 刷新（同一 URL 再走一遍，等于 F5）
        pg.reload(wait_until="networkidle")
        pg.wait_for_timeout(2200)
        n2 = pg.evaluate("() => document.querySelectorAll('#main .zonecard, #main .card').length")
        check("刷新后仍是同一页且内容不丢（hash 路由不依赖托管方 rewrite）", n2 == n and n2 >= 2,
              "%d → %d" % (n, n2))
        pg.close()
        # 3) 子路径挂载：同一份包挂到 /wow/ 下也要能开（base 相对路径的验收点）
        pg, fails, errs = open_url(base_sub, "/wow/#/world")
        n3 = pg.evaluate("() => document.querySelectorAll('#main .zonecard, #main .card').length")
        check("挂到子路径 /wow/ 下 #/world 同样渲染（数据与图标都按相对路径取到）",
              n3 == n and not errs, "%d 个卡片 / 报错 %s" % (n3, errs[:1]))
        check("子路径挂载没有失败请求", not fails, "; ".join(fails[:3]) or "干净")
        pg.screenshot(path=os.path.join(SHOT_DIR, "q05-subpath-world.png"))
        pg.close()
        # 4) 分享链接：新上下文、直接给完整地址（别人在群里点开的样子）
        pg, fails, errs = open_url(base_root, "/#/dungeon?d=scholomance")
        t4 = pg.evaluate("() => (document.querySelector('#main') || {}).innerText || ''")
        check("分享副本详情直达链接能开到那一座（站名带该副本）",
              "通灵学院" in t4 and not errs, "%d 字 / 报错 %s" % (len(t4), errs[:1]))
        pg.close()
        # 5) 旧页地址在浏览器里真跳到位，且查询串跟着过去
        pg, fails, errs = open_url(base_root, "/talent.html?c=hunter")
        pg.wait_for_timeout(1500)
        u = pg.evaluate("() => location.hash")
        n5 = pg.evaluate("() => document.querySelectorAll('.tnode, .node, #main button').length")
        check("浏览器点 talent.html?c=hunter 落到 #/talent?c=hunter 且渲染出内容",
              u == "#/talent?c=hunter" and n5 > 10, "落到 %s / %d 个可点节点" % (u, n5))
        pg.close()
        pg, fails, errs = open_url(base_sub, "/wow/talent.html?c=mage")
        pg.wait_for_timeout(1500)
        u = pg.evaluate("() => location.hash")
        check("子路径下旧页桩同样跳到位（不是跳到根目录）", u == "#/talent?c=mage", "落到 %s" % u)
        pg.close()
        # 6) 站内未知 hash 路由：给"还没迁过来"，不给空白
        pg, fails, errs = open_url(base_root, "/#/no-such-page")
        t6 = pg.evaluate("() => (document.querySelector('#main') || {}).innerText || ''")
        check("未知 hash 路由落到兜底页而不是空白", len(t6) > 20 and not errs, "%d 字" % len(t6))
        pg.close()
        # 7) 带搜索与筛选的直达（动态页那条链）
        pg, fails, errs = open_url(base_root, "/#/updates?c=hunter&w=spell&q=%E7%8C%8E")
        c7 = pg.evaluate("() => (document.querySelector('#ccnt') || {}).textContent || ''")
        check("带职业/类型/关键词的直达链接，落地就是筛好的", "条" in c7 and int(re.sub(r"\D", "", c7 or "0") or 0) >= 1,
              c7 or "没有计数")
        pg.close()
        br.close()

    s1.shutdown()
    s2.shutdown()
    import shutil as _sh
    _sh.rmtree(parent, ignore_errors=True)

    print("\n===== 结果 =====")
    print("通过 %d / %d" % (len(RESULTS) - len(FAILED), len(RESULTS)))
    if FAILED:
        print("失败：" + "、".join(FAILED))
        sys.exit(1)
    print("全部通过（外网托管仍未验收：这一份是本机静态服务器）")


if __name__ == "__main__":
    main()
