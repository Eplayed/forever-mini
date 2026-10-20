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
from urllib.parse import quote, unquote, urlparse

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


def decide(route_exec, route_fail, shots_wanted, shot_exec, shot_fail, check_fail):
    """退出码怎么定：单独拆成一个纯函数，是为了能对它注入失败做回归——
       不用真的把浏览器弄崩，也不用在真实资料里制造缺图（2026-10-20 W01-R1 的验收点）。

    规则：
      · 路由跑过且有失败 → 非 0；
      · 请求了截图（--shots / --only-shots）时，截图本身失败、或截图里的关键断言不过 → 非 0；
      · 没请求截图时，只看路由结果（保持普通冒烟的老行为）。
    只拍图那一支绝不参与路由计数，摘要里也照实写"路由未执行"（上一版会打「路由 26 条」）。
    """
    rc = 0
    if route_exec and route_fail:
        rc = 1
    if shots_wanted and (shot_fail or check_fail):
        rc = 1
    return rc


def summary_lines(route_exec, route_fail, shots_wanted, shot_exec, shot_fail, check_fail, allowed):
    """把"跑了什么、成没成"说清，不含糊。"""
    out = []
    if route_exec:
        out.append("路由 %d 条执行，有问题的 %d 条；按缺图登记放行的取不到共 %d 次"
                   % (route_exec, route_fail, allowed))
    else:
        out.append("路由冒烟：本轮未执行（--only-shots 只拍图，不要当成 26 条路由过了）")
    if shots_wanted:
        out.append("截图 %d 处：拍制失败 %d 处、画面断言不过 %d 处"
                   % (shot_exec, shot_fail, check_fail))
    return out


def selftest():
    """失败注入回归：三类场景都喂给 decide()，看退出码对不对。不启动浏览器。"""
    cases = [
        ("全部成功（路由 26 条 0 问题 + 截图 5 处全过）",
         (26, 0, True, 5, 0, 0), 0),
        ("路由有失败", (26, 1, False, 0, 0, 0), 1),
        ("截图崩了一处（Chromium SIGSEGV 那种）", (26, 0, True, 5, 1, 0), 1),
        ("截图拍成了但关键断言不过（图标没解码）", (26, 0, True, 5, 0, 1), 1),
        ("只拍图：截图断言不过也必须非 0", (0, 0, True, 5, 0, 1), 1),
        ("只拍图且全过", (0, 0, True, 5, 0, 0), 0),
        ("没请求截图时不因截图计数报错", (26, 0, False, 0, 3, 3), 0),
    ]
    bad = 0
    print("\n=== route-smoke.py 退出码注入回归 ===")
    for name, args, want in cases:
        got = decide(*args)
        ok = got == want
        bad += 0 if ok else 1
        print("  %s  %-46s 退出码 %s（期望 %s）" % ("PASS" if ok else "FAIL", name, got, want))
    line = summary_lines(0, 0, True, 5, 0, 0, 0)
    ok = "未执行" in line[0]
    bad += 0 if ok else 1
    print("  %s  %-46s %s" % ("PASS" if ok else "FAIL", "只拍图时摘要不许说跑了 26 条", line[0]))
    print("用例 %d 条，失败 %d 条" % (len(cases) + 1, bad))
    return 1 if bad else 0


def run(base, shots, shots_only=False):
    from playwright.sync_api import sync_playwright
    gaps = load_gaps()
    fails = []
    shot_rows = []
    route_exec = 0
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
        if not shots_only:
            for path, label in ROUTES:
                errs.clear(); net.clear()
                page.goto(hashurl(base, path), wait_until="networkidle")
                page.wait_for_timeout(1500)
                route_exec += 1
                broken, srcbad, pending = scan_page(page, gaps, seen)
                badnet = ["%s → %d" % (u, s) for (u, s) in net if not allowed(u, gaps)]
                row = {"route": path, "label": label, "broken": broken,
                       "net": badnet, "src": srcbad, "pending": pending,
                       "js": [e for e in errs if "favicon" not in e]}
                # pending 只报数不算失败：那张图还没开始加载不等于加载失败
                bad_rows = [k for k in ("broken", "net", "src", "js") if row[k]]
                tail = "（%d 张 lazy 图没滚到，按 src 逐个问的服务）" % pending if pending else ""
                print("  %-42s %s%s" % (label, "OK" if not bad_rows else "问题 → " + json.dumps(
                    {k: (row[k][:4] if isinstance(row[k], list) else row[k]) for k in bad_rows},
                    ensure_ascii=False), tail))
                if bad_rows:
                    fails.append(row)
        if shots:
            shot_rows = take_shots(pw, base, gaps)
        browser.close()
    shot_fail = len([r for r in shot_rows if r["shot_err"]])
    check_fail = len([r for r in shot_rows if not r["check_ok"]])
    for line in summary_lines(route_exec, len(fails), bool(shots), len(shot_rows),
                              shot_fail, check_fail, ALLOWED[0]):
        print(line)
    for f in fails:
        print("  %s：%s" % (f["label"], json.dumps(f, ensure_ascii=False)[:300]))
    if shot_rows:
        print("截图（桌面与 375 分开算）：")
        for r in shot_rows:
            print("  %s" % r["line"])
    return decide(route_exec, len(fails), bool(shots), len(shot_rows), shot_fail, check_fail)


def take_shots(pw, base, gaps):
    """W01 要看的那几处，逐张拍桌面 + 375，两块视口分别记账。

    每一处单独兜一次：这台机器（Intel 核显）刚跑完 14 分钟整站门禁再开抽屉，
    Chromium 会在拉 3.8MB 的 items-detail 时 SIGSEGV——一处崩了不能把剩下几处带走。
    但**兜住不等于放过**：崩了要记进 shot_err，最后由 decide() 把退出码打成非 0
    （上一版只往输出里塞一行"没拍成"，rc 仍然是 0，这就是独立验收点名的第二处漏洞）。"""
    rows = []
    day = os.path.join(SHOTS, "check-2026-10-20")
    if not os.path.isdir(day):
        os.makedirs(day)
    expect = load_expectations()

    def shoot(pg, name, url, scroll_sel, click_sel, tag):
        pg.goto(hashurl(base, url), wait_until="networkidle")
        pg.wait_for_timeout(1800)
        if scroll_sel:
            pg.locator(scroll_sel).first.scroll_into_view_if_needed()
            pg.wait_for_timeout(400)
        if click_sel:
            pg.locator(click_sel).first.click()
            pg.wait_for_timeout(1200)
        path = os.path.join(day, name + ("-m.png" if tag == "m" else ".png"))
        pg.screenshot(path=path)
        return os.path.relpath(path, SHOTS)

    def one(name, url, scroll_sel=None, check=None, click_sel=None):
        """每一处一套独立的浏览器：这台机器（Intel 核显、内存紧）连拍五处会 SIGSEGV，
           共用一个 browser 时一处崩会把后面几处一起带走（2026-10-20 实测到第二次）。
           分开起浏览器只为不让"拍不成"伪装成"没做错"——崩了照样记 shot_err、照样 rc≠0。"""
        rec = {"name": name, "shot_err": [], "check_ok": True, "check_msg": "", "files": []}
        br = pw.chromium.launch()
        try:
            for tag, w, h in (("d", 1440, 1000), ("m", 375, 812)):
                c = br.new_context(viewport={"width": w, "height": h})
                pg = c.new_page()
                try:
                    rec["files"].append(shoot(pg, name, url, scroll_sel, click_sel, tag))
                    if tag == "d" and check:
                        ok, msg = check(pg)
                        rec["check_ok"] = bool(ok)
                        rec["check_msg"] = msg
                except Exception as e:
                    rec["shot_err"].append("%s:%s" % ("桌面" if tag == "d" else "375",
                                                      str(e).split(chr(10))[0][:110]))
                finally:
                    c.close()
        except Exception as e:
            rec["shot_err"].append("整套浏览器：%s" % str(e).split(chr(10))[0][:110])
        finally:
            br.close()
        if check and rec["shot_err"] and rec["check_ok"]:
            rec["check_ok"] = False
            rec["check_msg"] = rec["check_msg"] or "这一处没拍成，断言没有依据"
        rec["line"] = "%s ｜ %s ｜ 断言%s %s" % (
            " / ".join(rec["files"]) or "没拍成",
            "；".join(rec["shot_err"]) or "两块视口都拍到了",
            "过" if rec["check_ok"] else "不过", rec["check_msg"])
        rows.append(rec)

    def chk_world(pg):
        z = expect["zones"]
        got = pg.evaluate("""() => ({
          big: document.querySelectorAll('.zcard .zbig').length,
          nomap: document.querySelectorAll('.zcard .zband.nomap').length,
          broken: [...document.querySelectorAll('.zcard img')].filter(i => i.complete && !i.naturalWidth).length })""")
        ok = (got["big"] == z["with"] and got["nomap"] == z["without"] and got["broken"] == 0)
        return ok, "图框 %d（数据有图 %d）/ 紧凑态 %d（数据缺图 %d）/ 破图 %d" % (
            got["big"], z["with"], got["nomap"], z["without"], got["broken"])

    def chk_updates(pg):
        want = expect["icon"]
        got = pg.evaluate("""(want) => {
          const hit = [...document.querySelectorAll('*')]
            .filter(e => !e.children.length && e.textContent.trim() === '黑暗启发')[0];
          if (!hit) return { why: '页面上找不到"黑暗启发"这一行' };
          let box = hit;
          for (let i = 0; i < 6 && box.parentElement; i++) box = box.parentElement;
          const im = box.querySelector('img');
          return im ? { src: (im.currentSrc || im.src).split('/').pop(),
                        ok: im.complete && im.naturalWidth > 0, w: im.naturalWidth }
                    : { why: '这一行没有 img（仍退自绘块）' }; }""", want)
        ok = got.get("ok") is True and got.get("src") == want
        return ok, json.dumps(got, ensure_ascii=False)

    def chk_barrow(pg):
        """巴罗夫地穴：这座缺的是**载入图**，不是入口坐标。
           它根本不在 dungeon-geo 那 30 座里，所以「入口在哪」这一节本来就不该出现——
           第一版断言写成了"必须渲染出 .dgeo"，那是我把两节搞混了，不是页面的问题。"""
        got = pg.evaluate("""() => { const h = document.querySelector('.dhero');
          if (!h) return { why: '页头那一块没渲染出来' };
          const im = [...h.querySelectorAll('img')];
          return { noart: h.classList.contains('noart'), imgs: im.length,
                   broken: im.filter(i => i.complete && !i.naturalWidth).length,
                   geo: !!document.querySelector('.dgeo') }; }""")
        if got.get("why"):
            return False, got["why"]
        ok = got["noart"] and got["broken"] == 0 and not got["geo"]
        return ok, "页头无载入图态=%s / 页头 img %d 张破图 %d / 入口那一节存在=%s（这座不在 geo 的 30 座里，本就不该有）" % (
            got["noart"], got["imgs"], got["broken"], got["geo"])

    def chk_nofaces(pg):
        got = pg.evaluate("""() => ({ rows: document.querySelectorAll('.brow').length,
          broken: [...document.querySelectorAll('.brow img')].filter(i => i.complete && !i.naturalWidth).length })""")
        ok = got["rows"] >= expect["nofaces"] and got["broken"] == 0
        return ok, "首领行 %d（数据没脸的 %d）/ 破图 %d" % (
            got["rows"], expect["nofaces"], got["broken"])

    def chk_drawer(pg):
        got = pg.evaluate("""() => { const d = document.querySelector('.idrawer');
          if (!d) return { open: false };
          const im = [...d.querySelectorAll('img')];
          return { open: true, imgs: im.length,
                   broken: im.filter(i => i.complete && !i.naturalWidth).length }; }""")
        if not got.get("open"):
            return False, "点开那一行之后详情抽屉没出来"
        return got["broken"] == 0, "抽屉里 %d 张图，破图 %d" % (got["imgs"], got["broken"])

    one("w1-world-zones-nomap", "/world?t=zones", ".zcard", chk_world)
    one("w1-updates-dark-inspiration", "/updates?q=" + quote(expect["q"]), "text=黑暗启发", chk_updates)
    one("w1-dungeon-barrow-deeps", "/dungeon?d=barrow-deeps", None, chk_barrow)
    one("w1-dungeon-lordaeron-nofaces", "/dungeon?d=ruins-of-lordaeron", ".brow", chk_nofaces)
    one("w1-items-drawer", "/items?q=" + quote(expect["item"]), "tr.row", chk_drawer, click_sel="tr.row")
    return rows


def load_expectations():
    """断言的期望值从数据现读，不写死在脚本里（数据一升级，写死的数就变成假话）。"""
    world = json.load(io.open(os.path.join(ROOT, "src", "data", "world.json"), encoding="utf-8"))
    zones = world.get("zones") or []
    geo = json.load(io.open(os.path.join(ROOT, "src", "data", "dungeon-geo.json"), encoding="utf-8"))
    dgs = json.load(io.open(os.path.join(ROOT, "src", "data", "dungeons.json"), encoding="utf-8"))
    rows = []
    for k in ("newDungeons", "classicDungeons", "raids"):
        rows += dgs.get(k) or []
    lord = [x for x in rows if x.get("id") == "ruins-of-lordaeron"]
    nofaces = len([b for b in ((lord[0] if lord else {}).get("bosses") or []) if not b.get("portrait")])
    return {"zones": {"with": len([z for z in zones if z.get("mapFile")]),
                      "without": len([z for z in zones if not z.get("mapFile")])},
            "icon": "spell_warlock_demonsoul.jpg",
            "q": "黑暗启发", "item": "浸油护腿", "nofaces": nofaces,
            "geo_dungeons": len(geo.get("dungeons") or [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("APP_BASE", "http://127.0.0.1:8821"))
    ap.add_argument("--shots", action="store_true", help="顺手拍 W01 要看的那几处")
    ap.add_argument("--only-shots", action="store_true",
                    help="只拍那几处，不跑 26 条路由（这台机器一次跑两件事内存吃紧，Chromium 会在拉 3.8MB 的 items-detail 时崩掉）")
    ap.add_argument("--selftest", action="store_true",
                    help="不启动浏览器，只验退出码判定：截图崩了/断言不过都必须非 0")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    print("生产构建冒烟 · %s（缺图登记 %d 个键放行）" % (a.base, len(load_gaps())))
    sys.exit(run(a.base, a.shots or a.only_shots, shots_only=a.only_shots))


if __name__ == "__main__":
    main()
