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
  3. 旧页地址 talent.html 这一类：2026-10-24 起跳转桩已随旧站撤掉，所以钉的是反向事实——
     包里除 index.html 不许有第二个 .html，且访问它必须真 404（不是被兜底成 200 首页）；
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


def head(url, tries=2):
    """状态码 + Content-Type。
    打远端（HTTPS）时 python 自带的 urllib 在这台机器上过不了证书校验（本机实测，
    与 2026-10 那次抓 DD373 同一现象），所以一律走 curl——它用系统信任库。
    远端的 404 也慢：GitHub Pages 要渲染它自己的 404 页，实测一条不存在的 .jpg 用了 26 秒，
    所以超时给到 60 秒并允许重试一次；不然"缺文件必须 404"这条会因为超时假红。"""
    import subprocess
    last = (0, "")
    for _ in range(tries):
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{content_type}",
                            "--max-time", "60", url], stdout=subprocess.PIPE)
        if r.returncode != 0:
            last = (0, "curl rc=%d" % r.returncode)
            continue
        parts = (r.stdout or b"").decode("utf-8", "replace").split(" ", 1)
        try:
            return int(parts[0]), (parts[1] if len(parts) > 1 else "").strip()
        except ValueError:
            last = (0, parts[0])
    return last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=None, help="要验收的目录（默认取 release/latest.json 指的那一版）")
    ap.add_argument("--live", default=None,
                    help="线上地址（如 https://x.github.io/repo/）：给了它就不起本机服务，"
                         "所有判据打真远端；子路径那几条跳过（远端挂哪由托管方定）")
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

    # 本机跑：挂两种（根目录 + 子路径 /wow/，软链不复制 28 MB）。
    # --live：不起服务，判据全打远端；子路径那几条跳过（挂在哪儿由托管方定，不是我们能在这台机器上验的）。
    import tempfile
    parent = None
    s1 = s2 = None
    if a.live:
        base_root = a.live.rstrip("/")
        base_sub = None
        print("线上验收：%s（本机服务不起，子路径用例跳过）" % base_root)
    else:
        parent = tempfile.mkdtemp(prefix="pkgverify-")
        os.symlink(site, os.path.join(parent, "wow"))
        base_root, s1 = serve(site)
        base_sub, s2 = serve(parent)
        print("根目录挂载 %s / 子路径挂载 %s/wow/" % (base_root, base_sub))

    print("\n[A] 资源类型与缺文件（无兜底的静态服务器）")
    st, ct = head(base_root + "/")
    check("首页 / 回 200 text/html", st == 200 and "html" in ct, "%s %s" % (st, ct))
    if base_sub:
        st2, ct2 = head(base_sub + "/wow/")
        check("子路径 /wow/ 同样 200 text/html", st2 == 200 and "html" in ct2, "%s %s" % (st2, ct2))
    html = open(os.path.join(site, "index.html"), encoding="utf-8").read()
    refs = [r for r in re.findall(r'(?:src|href)="([^"]+)"', html) if not r.startswith(("http", "data:"))]
    TYPES = {".js": ("javascript",), ".css": ("text/css",), ".svg": ("image/svg",),
             ".png": ("image/png",), ".ico": ("x-icon", "image/vnd.microsoft.icon"),
             ".woff2": ("font",), ".webp": ("image/webp",), ".jpg": ("image/jpeg",),
             ".html": ("text/html",)}
    bad = []
    for r in refs:
        rel = r.lstrip("./")
        if not rel or rel.startswith("#"):
            continue
        s, c = head(base_root + "/" + rel)
        ext = os.path.splitext(rel)[1].lower()
        wants = TYPES.get(ext)
        if s != 200 or (wants and not any(w in c for w in wants)):
            bad.append("%s → %s %s" % (rel, s, c))
    check("index.html 引用的每个本地资源都在、类型正确（不是 200 HTML 兜底）", not bad,
          "; ".join(bad[:3]) or "%d 个" % len(refs))
    s, c = head(base_root + "/data/meta.json")
    check("data/*.json 是 application/json", s == 200 and "json" in c, "%s %s" % (s, c))
    s, c = head(base_root + "/img/icons/inv_misc_questionmark.jpg")
    check("存在的图标是 image/jpeg", s == 200 and "jpeg" in c, "%s %s" % (s, c))
    s, c = head(base_root + "/img/icons/definitely_not_a_real_icon.jpg")
    # 判据是"状态码必须是 404"，不是"404 的正文不能是 HTML"——托管方的 404 页本来就是 HTML
    # （GitHub Pages 实测回 404 + text/html）。要防的是另一种：缺文件被兜底成 **200** HTML。
    check("缺的 .jpg 必须 404，不许被 200 HTML 冒充（preview 会假绿）", s == 404, "%s %s" % (s, c))
    s, c = head(base_root + "/data/upstream/anything.json")
    check("upstream 原料不在包里（请求它得 404）", s == 404, "%s" % s)

    print("\n[B] 旧页地址（talent.html 这一类，2026-10-24 站主拍板撤掉跳转桩）")
    extra = [f for f in os.listdir(site) if f.endswith(".html") and f != "index.html"]
    check("包里没有旧页地址的跳转桩（除 index.html 外不许有 .html）", not extra,
          "、".join(extra[:5]) or "只有 index.html")
    s, c = head(base_root + "/talent.html")
    check("/talent.html 是 404，不是被兜底成 200 首页（撤桩后要的是明确失败，不是点了没反应）",
          s == 404, "%s %s" % (s, c))

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
            if a.live:
                # 真远端首屏慢（实测 GitHub Pages 冷路径一条请求 6–10 秒），固定等 2.5 秒
                # 会把"还没渲染完"误判成"渲染不出来"。等到 #main 有字为止，最多 25 秒。
                try:
                    pg.wait_for_function(
                        "() => { const m = document.querySelector('#main');"
                        "return m && (m.innerText || '').length > 200; }", timeout=25000)
                except Exception:               # noqa: BLE001
                    pass                        # 等不到也让下面的断言去判，并如实报字数
                pg.wait_for_timeout(800)
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
        # 3) 子路径挂载：同一份包挂到 /wow/ 下也要能开（base 相对路径的验收点）。--live 时跳过。
        if base_sub:
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
        # 5) 旧页地址（talent.html 这一类）已经不再承接：跳转桩于 2026-10-24 随旧站一起撤掉，
        #    静态托管方会直接回 404。上面 [B] 那条判的就是这个 404，浏览器里不必再跑五种形态。
        # 6) 站内未知 hash 路由：必须**留在本站**并落到有内容的一页
        #    （以前只判"不是空白"，2026-10-20 发 Pages 才发现它会跳到主机根的旧站地址，
        #     拿到的其实是 GitHub 的 404 页——那也是"有字"，光看字数抓不住）
        pg, fails, errs = open_url(base_root, "/#/no-such-page")
        z = pg.evaluate("""() => ({ t: (document.querySelector('#main') || {}).innerText || '',
                 host: location.hostname, path: location.pathname, title: document.title })""")
        want_host = re.sub(r"^https?://", "", base_root).split("/")[0].split(":")[0]
        check("未知 hash 路由留在本站并回首页（不甩到主机根、不给空白）",
              len(z["t"]) > 500 and z["host"] == want_host and not errs
              and "GitHub Pages" not in z["title"],
              "%d 字 / host %s / path %s / 标题 %s" % (len(z["t"]), z["host"], z["path"], z["title"][:26]))
        pg.close()
        # 6b) 认得出的旧文件名走 catch-all 时也应送到它那一页，不是首页
        pg, fails, errs = open_url(base_root, "/#/races.html")
        z2 = pg.evaluate("""() => ({ h: location.hash, t: document.title })""")
        check("#/races.html 这种旧文件名地址送到种族页而不是首页",
              z2["h"] == "#/races" and z2["t"].startswith("种族"), "%s / %s" % (z2["h"], z2["t"][:24]))
        pg.close()
        # 7) 带搜索与筛选的直达（动态页那条链）
        pg, fails, errs = open_url(base_root, "/#/updates?c=hunter&w=spell&q=%E7%8C%8E")
        c7 = pg.evaluate("() => (document.querySelector('#ccnt') || {}).textContent || ''")
        check("带职业/类型/关键词的直达链接，落地就是筛好的", "条" in c7 and int(re.sub(r"\D", "", c7 or "0") or 0) >= 1,
              c7 or "没有计数")
        pg.close()
        br.close()

    if s1:
        s1.shutdown()
    if s2:
        s2.shutdown()
    if parent:
        import shutil as _sh
        _sh.rmtree(parent, ignore_errors=True)

    print("\n===== 结果 =====")
    print("通过 %d / %d" % (len(RESULTS) - len(FAILED), len(RESULTS)))
    if FAILED:
        print("失败：" + "、".join(FAILED))
        sys.exit(1)
    if a.live:
        print("全部通过（这一份打在 %s 上，是真远端）" % a.live)
    else:
        print("全部通过（外网托管仍未验收：这一份是本机静态服务器）")


if __name__ == "__main__":
    main()
