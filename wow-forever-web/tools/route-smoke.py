#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站路由生产构建冒烟：21 条真实路由逐条打开、滚到底触发懒加载，
   把每条路由的失败请求、DOM 里的破图、CSS 背景 URL 与 console 报错都记下来。

为什么单独做这个（2026-10-20 W01-C）：site-check 的断言按功能点写，查的是"这一屏对不对"；
上线前还需要一条粗网——**缺图不会报错，只会悄悄退成字母块**，2026-10-20 那次
spell_warlock_demonsoul 没登记也照样构建通过、页面照常上线，就是缺这一层。

放行依据只有一份：src/data/icon-gaps.json（tools/build-icon-map.py 派生，
build-data.js 会双向比对：漏登记、过期登记、死条目都让构建失败）。
不在那份登记里的失败请求一律算不通过——**不许靠扩大白名单把 404 说成正常**。

用法：
    python3 tools/route-smoke.py                      # 只跑冒烟
    python3 tools/route-smoke.py --shots              # 顺手把 W01 要看的几处拍进 docs/screenshots/
    python3 tools/route-smoke.py --base http://127.0.0.1:8821

前提：先 `cd app && npm run build`（preview 服务的是 dist，改了数据不重构建就会"磁盘新、服务旧"），
再 `bash tools/serve.sh` 把 :8821 起起来。
退出码 0 = 21 条路由没有未登记的失败请求、没有破图、没有 CSS 背景取不到、没有 console 报错。
"""
import argparse
import io
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # wow-forever-web
GAPS = os.path.join(ROOT, "src", "data", "icon-gaps.json")
SHOTS = os.path.join(ROOT, "docs", "screenshots")

# 21 条真实路由（router.js 里数出来的，含详情路由带有效参数）
ROUTES = [
    ("/", "首页"),
    ("/world", "世界·区域"),
    ("/world?t=rares", "世界·稀有精英"),
    ("/world?t=books", "世界·书"),
    ("/world?t=bag", "世界·营地"),
    ("/classes", "职业"),
    ("/talent?c=priest", "天赋计算器"),
    ("/chooser", "选职业问答"),
    ("/legacy", "传承"),
    ("/races", "种族"),
    ("/dungeons", "副本手册"),
    ("/dungeon?d=ragefire-chasm", "副本详情·有首领头像"),
    ("/dungeon?d=ruins-of-lordaeron", "副本详情·七只没脸"),
    ("/dungeon?d=barrow-deeps", "副本详情·缺载入图"),
    ("/raids", "团本名单"),
    ("/systems", "系统规则"),
    ("/professions", "专业与配方"),
    ("/glossary", "术语速查"),
    ("/timeline", "时间表"),
    ("/skills", "技能书"),
    ("/achievements", "成就"),
    ("/updates", "最新动态"),
    ("/rank", "资料完整度排行"),
    ("/provenance", "溯源与覆盖率"),
    ("/items?q=%E6%B5%B8%E6%B2%B9%E6%8A%A4%E8%85%BF", "物品库·带搜索词"),
    ("/bis?c=hunter&s=hunter&f=alliance", "配装名单"),
]

# 图片类资源：src/img/… 与字体；数据 JSON 的失败另算（会让页面显示失败态）
ASSET_RE = re.compile(r"/img/|\.woff2?\b|\.css\b", re.I)


def hashurl(base, path):
    """这个站是 hash 路由（app/src/router.js 用 createWebHashHistory）。
       直接 goto base + "/items?..." 会被单页兜底吃回去、渲染成首页且零报错
       ——2026-10-20 第一版就栽在这里，26 条"路由"其实全是首页。"""
    return base + "/#" + path


def load_gaps():
    if not os.path.exists(GAPS):
        sys.exit("拿不到 src/data/icon-gaps.json（缺图登记）——先跑 python3 tools/build-icon-map.py")
    g = json.load(io.open(GAPS, encoding="utf-8"))
    return set(g.get("keys") or [])


def allowed(url, gaps):
    """只有"登记过的缺图图标"允许 404。art 目录（区域底图/载入图/首领头像）不在放行范围里——
       那些路径是数据里给了才会去请求，取不到就是链路错，不能算已知缺口。"""
    if "/img/icons/" not in url:
        return False
    name = unquote(os.path.basename(urlparse(url).path))
    return name[:-4] in gaps if name.endswith(".jpg") else False


SCAN_JS = r"""() => {
  const imgs = [...document.querySelectorAll('img')].map(i => ({
    src: i.currentSrc || i.src, done: i.complete, w: i.naturalWidth }));
  const bgs = new Set();
  [...document.querySelectorAll('*')].forEach(e => {
    const b = getComputedStyle(e).backgroundImage;
    if (!b || b.indexOf('url(') < 0) return;
    const re = /url\((['"]?)([^'")]+)\1\)/g;
    let m;
    while ((m = re.exec(b))) bgs.add(m[2]);
  });
  /* 破图 = 已经加载完（complete）但一张像素都没有。
     没滚到、还没开始加载的 lazy 图 complete 是 false——那种不能靠"看起来没坏"放过，
     所以下面把它们各自的 src 也交给 check_srcs 逐个问一次服务（2026-10-20 第一版
     只按滚动后的 DOM 判，副本手册那一屏就有 1147 张根本没开始加载，等于没验）。 */
  return { broken: imgs.filter(i => i.src && i.done && !i.w).map(i => i.src),
           srcs: [...new Set(imgs.map(i => i.src).filter(Boolean))],
           pending: imgs.filter(i => i.src && !i.done).length,
           bgs: [...bgs].filter(u => u.indexOf('data:') !== 0) }; }"""


ALLOWED = [0]        # 整轮被「登记过的缺图」这条规则放行的 404 次数——放行必须可见


KIND = ((".jpg", "image/"), (".jpeg", "image/"), (".webp", "image/"), (".png", "image/"),
        (".gif", "image/"), (".svg", "image/"), (".woff2", "font/"), (".woff", "font/"),
        (".css", "text/css"))


def bad_asset(st, ctype, url):
    """这个冒烟跑在 vite preview 上，**它带 SPA 兜底：路径不存在时返回 200 + 一份 index.html**。
       所以只看状态码会把"文件没了"读成"取到了"（2026-10-20 反向测就是这么抓出来的：
       把一张本地图标挪走，冒烟仍然全绿）。必须同时看 content-type 对不对得上这个扩展名。
       正式静态托管的兜底行为要单独在上线验收里核（见 VERIFY-prelaunch-images §4.2 那条）。"""
    if st >= 400 or st < 0:
        return "HTTP %s" % st
    path = urlparse(url).path.lower()
    for ext, want in KIND:
        if path.endswith(ext) and not ctype.lower().startswith(want):
            return "200 但不是资源（content-type=%s，SPA 兜底把缺文件伪装成取到了）" % (ctype or "?")
    return None


def check_srcs(page, gaps, urls, seen):
    """每个 src 直接问一次本地服务：状态码或 content-type 不对、且不在缺图登记里 = 不通过。
       seen 是整轮共享的结果缓存（同一张图标会在几十条记录里反复出现）。"""
    bad = []
    for u in urls:
        absu = page.evaluate("() => new URL(%s, location.href).href" % json.dumps(u))
        if absu in seen:
            why = seen[absu]
        else:
            try:
                r = page.request.get(absu)
                why = bad_asset(r.status, r.headers.get("content-type", ""), absu)
            except Exception:
                why = "请求没成（连接被掐或超时）"
            seen[absu] = why
        if why:
            if allowed(absu, gaps):
                ALLOWED[0] += 1        # 放行的是登记过的缺图，报数用，不静默
                continue
            bad.append("%s → %s" % (absu, why))
    return bad


def scan_page(page, gaps, seen):
    """滚到底触发懒加载，然后收四样：失败响应、DOM 里的破图、全部 src 的可取性、CSS 背景 URL。"""
    for _ in range(2):
        page.evaluate("""async () => {
          const h = document.body.scrollHeight;
          for (let y = 0; y <= h; y += Math.max(300, innerHeight - 120)) {
            window.scrollTo(0, y); await new Promise(r => setTimeout(r, 150)); }
          window.scrollTo(0, 0); }""")
        for _t in range(8):
            page.wait_for_timeout(400)
            if page.evaluate("() => [...document.querySelectorAll('img')].every(i => i.complete)") is True:
                break
    bad = page.evaluate(SCAN_JS)
    broken = [u for u in bad["broken"] if not allowed(u, gaps)]
    srcbad = check_srcs(page, gaps, bad["srcs"] + bad["bgs"], seen)
    return broken, srcbad, bad["pending"]


def run(base, shots, shots_only=False):
    from playwright.sync_api import sync_playwright
    gaps = load_gaps()
    fails = []
    shots_out = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)[:160]))
        page.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
        seen = {}          # src → 状态码，整轮共享（同一张图标会在几十条记录里反复出现）
        net = []
        page.on("response", lambda r: net.append((r.url, r.status))
                if r.status >= 400 and ASSET_RE.search(r.url) else None)
        for path, label in ([] if shots_only else ROUTES):
            errs.clear(); net.clear()
            page.goto(hashurl(base, path), wait_until="networkidle")
            page.wait_for_timeout(1500)
            broken, srcbad, pending = scan_page(page, gaps, seen)
            badnet = ["%s → %d" % (u, s) for (u, s) in net if not allowed(u, gaps)]
            row = {"route": path, "label": label, "broken": broken,
                   "net": badnet, "src": srcbad, "pending": pending,
                   "js": [e for e in errs if "favicon" not in e]}
            # pending 只报数不算失败：那张图还没开始加载不等于加载失败
            bad_rows = [k for k in ("broken", "net", "src", "js") if row[k]]
            # pending：滚动没触发到的 lazy 图，它们的 src 已经逐个问过服务了，这里只报个数
            tail = "（%d 张 lazy 图没滚到，按 src 逐个问的服务）" % pending if pending else ""
            print("  %-42s %s%s" % (label, "OK" if not bad_rows else "问题 → " + json.dumps(
                {k: (row[k][:4] if isinstance(row[k], list) else row[k]) for k in bad_rows},
                ensure_ascii=False), tail))
            if bad_rows:
                fails.append(row)
        if shots:
            shots_out = take_shots(ctx, base, gaps)
        browser.close()
    print("\n路由 %d 条，有问题的 %d 条；按缺图登记放行的取不到共 %d 次" % (
        len(ROUTES), len(fails), ALLOWED[0]))
    for f in fails:
        print("  %s：%s" % (f["label"], json.dumps(f, ensure_ascii=False)[:300]))
    if shots_out:
        print("截图：")
        for s in shots_out:
            print("  " + s)
    return 1 if fails else 0


def take_shots(ctx, base, gaps):
    """W01 要看的那几处，逐张拍桌面 + 375（375 用同一个 context 开第二块视口）。

    每一处单独兜一次：这台机器（Intel 核显）刚跑完 14 分钟的整站门禁再开抽屉，
    Chromium 会在拉 3.8MB 的 items-detail 时 SIGSEGV——一处崩了不能把剩下几处带走，
    所以 shot() 捕获异常、换新页面继续，并把"这一处没拍成"如实记进输出。"""
    out = []
    day = os.path.join(SHOTS, "check-2026-10-20")
    if not os.path.isdir(day):
        os.makedirs(day)
    page = ctx.new_page()
    vp375 = ctx.new_page()
    vp375.set_viewport_size({"width": 375, "height": 812})

    def both(name, url, scroll_sel=None, check=None, click_sel=None):
        page.goto(hashurl(base, url), wait_until="networkidle")
        page.wait_for_timeout(1800)
        if scroll_sel:
            page.locator(scroll_sel).first.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
        if click_sel:
            page.locator(click_sel).first.click()
            page.wait_for_timeout(1200)
        p1 = os.path.join(day, name + ".png")
        page.screenshot(path=p1)
        vp375.goto(hashurl(base, url), wait_until="networkidle")
        vp375.wait_for_timeout(1800)
        if scroll_sel:
            vp375.locator(scroll_sel).first.scroll_into_view_if_needed()
            vp375.wait_for_timeout(400)
        if click_sel:
            vp375.locator(click_sel).first.click()
            vp375.wait_for_timeout(1200)
        p2 = os.path.join(day, name + "-m.png")
        vp375.screenshot(path=p2)
        msg = check() if check else ""
        out.append("%s / %s %s" % (os.path.relpath(p1, SHOTS), os.path.relpath(p2, SHOTS), msg))

    def shot(name, url, scroll_sel=None, check=None, click_sel=None):
        nonlocal page, vp375
        try:
            both(name, url, scroll_sel, check, click_sel)
        except Exception as e:
            out.append("%s 没拍成：%s" % (name, str(e).split(chr(10))[0][:140]))
            page = ctx.new_page()
            vp375 = ctx.new_page()
            vp375.set_viewport_size({"width": 375, "height": 812})

    # 1) 世界页区域面板：河林那一张（首屏就是它，本轮改的就是这种卡）
    shot("w1-world-zones-nomap", "/world?t=zones", ".zcard",
         check=lambda: "图框 %d 张 / 紧凑态 %d 张 / 破图 %d 张" % (
             page.evaluate("() => document.querySelectorAll('.zcard .zbig').length"),
             page.evaluate("() => document.querySelectorAll('.zcard .zband.nomap').length"),
             page.evaluate("() => [...document.querySelectorAll('img')].filter(i => i.complete && !i.naturalWidth).length")))
    # 2) 黑暗启发那条改动的图标：现在必须真加载出本地图
    shot("w1-updates-dark-inspiration", "/updates?q=%E9%BB%91%E6%9A%97%E5%90%AF%E5%8F%91", "text=黑暗启发",
         check=lambda: "黑暗启发那一行的图标 " + json.dumps(page.evaluate("""() => {
           const hit = [...document.querySelectorAll('*')]
             .filter(e => !e.children.length && e.textContent.trim() === '黑暗启发')[0];
           if (!hit) return '页面上找不到"黑暗启发"这一行';
           let box = hit;
           for (let i = 0; i < 6 && box.parentElement; i++) box = box.parentElement;
           const im = box.querySelector('img');
           return im ? { src: (im.currentSrc || im.src).split('/').pop(),
                         ok: im.complete && im.naturalWidth > 0, w: im.naturalWidth }
                     : '这一行没有 img（仍退自绘块）'; }"""), ensure_ascii=False))
    # 3) 副本详情：缺载入图那座 + 七只没脸那座（头像占位）
    shot("w1-dungeon-barrow-deeps", "/dungeon?d=barrow-deeps")
    shot("w1-dungeon-lordaeron-nofaces", "/dungeon?d=ruins-of-lordaeron", ".brow")
    # 4) 物品库详情抽屉（点开一行）
    shot("w1-items-drawer", "/items?q=%E6%B5%B8%E6%B2%B9%E6%8A%A4%E8%85%BF", "tr.row", click_sel="tr.row",
         check=lambda: "抽屉里 %d 张图，破图 %d 张" % (
             page.evaluate("() => document.querySelectorAll('.idrawer img').length"),
             page.evaluate("() => [...document.querySelectorAll('.idrawer img')].filter(i => i.complete && !i.naturalWidth).length")))
    vp375.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("APP_BASE", "http://127.0.0.1:8821"))
    ap.add_argument("--shots", action="store_true", help="顺手拍 W01 要看的那几处")
    ap.add_argument("--only-shots", action="store_true",
                    help="只拍那几处，不跑 26 条路由（这台机器一次跑两件事内存吃紧，Chromium 会在拉 3.8MB 的 items-detail 时崩掉）")
    a = ap.parse_args()
    print("生产构建冒烟 · %s（缺图登记 %d 个键放行）" % (a.base, len(load_gaps())))
    sys.exit(run(a.base, a.shots or a.only_shots, shots_only=a.only_shots))


if __name__ == "__main__":
    main()
