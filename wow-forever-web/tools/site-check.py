#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资料站回归自检（改界面/改交互后必跑）。

做三件事：
1. 起本地静态服务（自动挑空闲端口），逐页用无头 Chrome 渲染，检查正文非空、无控制台报错、无失败请求；
2. 跑天赋计算器的交互回归：加点 / 左键跟随减点模式 / 右键减点 / 长按减点 / 键盘回车 /
   层级门槛与前置校验 / 级联减点 / 分享编码 / 无痕窗口还原 / 复制方案文本 / 单系清空；
3. 截图存 docs/screenshots/check-<日期>/，任何一项不过直接退出码非 0。

用法：python3 tools/site-check.py [--keep-shots]
依赖：pip3 install playwright && python3 -m playwright install 之前需系统装有 Chrome（本机用 channel="chrome"）。
"""
import argparse
import datetime
import functools
import http.server
import os
import re
import socketserver
import sys
import threading
import urllib.parse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("缺少 playwright：pip3 install playwright")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
TODAY = datetime.date.today().isoformat()
SHOT_DIR = os.path.join(ROOT, "docs", "screenshots", "check-" + TODAY)

# 刻意不在导航里挂入口的页：技能书页 2026-10-12 用户实拍后从导航撤下，页面本身还在、
# 首页六个入口与职业页都还链着它。这些页跑渲染与通用判据，但不要求"导航里有高亮"。
NO_NAV_ENTRY = {"skills"}

# "某一类东西的一页"：不占导航格子，但必须亮着它所属列表页那一格（app.js 的 NAV_OF）。
# 加这类页就进这张表，否则"每个页面都能从导航走到"那条会把它当成走丢的页。
DETAIL_PARENT = {"dungeon": "dungeons"}

PAGES = ["index", "talent", "chooser", "timeline", "skills", "achievements", "dungeons", "dungeon", "raids",
         "systems", "races",
         "professions", "world", "legacy", "updates", "rank", "glossary", "provenance", "classes"]
# 官方 CDN 没有这些图标文件（多是无限服新装备），界面本来就该退回自绘块。
# 只有登记在 icon-gaps.json 里的键允许 404，多出来的失败请求一律算回归不通过。
GAPS_PATH = os.path.join(SRC, "data", "icon-gaps.json")
ICON_GAPS = set()
if os.path.exists(GAPS_PATH):
    import json as _json
    ICON_GAPS = set(_json.load(open(GAPS_PATH, encoding="utf-8")).get("keys") or [])


def tolerated(url):
    if "/img/icons/" not in url:
        return False
    return url.split("/")[-1].replace(".jpg", "") in ICON_GAPS


_APP_UP = None


def app_up(browser):
    """新站（Vue）端口通不通，一次探测全组复用。
       默认不通就跳过新站那几条并记一条通过；带 --app 时必须通，不然就是失败。"""
    global _APP_UP
    if _APP_UP is None:
        try:
            ctx = browser.new_context()
            p = ctx.new_page()
            p.goto(APP_BASE, timeout=6000)
            p.close()
            ctx.close()
            _APP_UP = True
        except Exception as e:
            _APP_UP = False
            check("新站可访问（法术书与成就这组要用）", not APP_REQUIRED,
                  "%s 不通（%s）" % (APP_BASE, str(e)[:60]))
    return _APP_UP
# 演示结构（_demo.json）里写死了层级门槛与前置链，用它做确定性断言
DEMO_A00 = "a-0-0"
DEMO_A01 = "a-0-1"
DEMO_A11 = "a-1-1"

results = []


APP_BASE = os.environ.get("APP_BASE", "http://127.0.0.1:8821")
APP_REQUIRED = False          # --app 时端口不通算失败，默认只跳过并说明


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + (("  — " + detail) if detail else ""))


# 正文里出现脚本路径、原始文件名或未替换占位符，就是开发残留漏进了玩家视野。
# 注意只拦**我们自己的**脚本路径：第三方域名里的 tools/（wago.tools/db2/…）是来源链接，
# 红线要求客户端数据能点开看到是哪个站转述的，把它一起禁掉等于逼着页面藏来源。
SCRIPT_PATH = re.compile(r"tools/[A-Za-z0-9_.-]*[.](?:py|js|sh|json)")


def dev_word_hits(body):
    hits = [w for w in [".json", ".py", "[{", "undefined", "NaN", "[object"] if w in body]
    if SCRIPT_PATH.search(body):
        hits.append("脚本路径")
    return hits


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def handle_exception(self, exc):
        # 浏览器提前关掉连接（换页、关 context）时 write 会抛 BrokenPipe，
        # 默认实现会把整段 traceback 打到 stderr，把真正的断言输出淹掉。这里静默。
        if not isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            http.server.BaseHTTPRequestHandler.handle_exception(self, exc)


class ThreadingServer(socketserver.ThreadingTCPServer):
    """必须多线程：单线程 HTTPServer 会被上一个页面的 keep-alive 连接卡住，后来者直接超时。"""
    daemon_threads = True
    allow_reuse_address = True


def start_server():
    handler = functools.partial(QuietHandler, directory=SRC)
    httpd = ThreadingServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, "http://127.0.0.1:%d" % port


def ranks(page, node_id):
    return page.evaluate(
        """(id) => { const n = document.querySelector(`[data-n="${id}"]`);
            if (!n) return null;
            const t = n.querySelector('.rank'); const m = t ? t.textContent.match(/(\\d+)/) : null;
            return { ranks: m ? +m[1] : null, lock: n.classList.contains('lock'), on: n.classList.contains('on'),
                     label: n.getAttribute('aria-label') || '' }; }""",
        node_id)


def click(page, node_id, button="left"):
    if button == "left":
        return page.evaluate("""(id) => { const n = document.querySelector(`[data-n="${id}"]`); if (!n) return false; n.click(); return true; }""", node_id)
    return page.evaluate("""(id) => { const n = document.querySelector(`[data-n="${id}"]`); if (!n) return false;
        n.oncontextmenu({ preventDefault: function(){} }); return true; }""", node_id)


def long_press(page, node_id, hold=650):
    """按下→等过 500ms→抬起，再补发一次 click（模拟手指离开时浏览器打在"新节点"上的那一下）。
       长按后重渲染会换掉元素，所以只有时间戳守卫能挡住这次补发 click。"""
    ok = page.evaluate("""(id) => { const n = document.querySelector(`[data-n="${id}"]`); if (!n) return false;
        n.ontouchstart && n.ontouchstart(); return true; }""", node_id)
    if ok:
        page.wait_for_timeout(hold)
        page.evaluate("""(id) => { const n = document.querySelector(`[data-n="${id}"]`);
            if (n && n.ontouchend) n.ontouchend({}); }""", node_id)
        page.wait_for_timeout(50)
        click(page, node_id)
    page.wait_for_timeout(250)
    return ok


def points_text(page):
    return page.evaluate("""() => { const el = document.querySelector('.pts'); return el ? el.innerText.replace(/\\s+/g, ' ') : ''; }""")


def open_talent(page, base, extra=""):
    """演示结构 = data/talents/_demo.json，写死了层级门槛与前置链，适合做确定性断言。
       走 ?c=_demo 直接载入；先清 localStorage，避免上一轮的方案残留影响断言。"""
    page.goto(base + "/talent.html", wait_until="domcontentloaded")
    page.evaluate("() => localStorage.clear()")
    page.goto(base + "/talent.html?c=_demo" + extra, wait_until="networkidle")
    page.wait_for_timeout(1200)


def test_pages(browser, base):
    print("\n[1] %d 页渲染" % len(PAGES))
    for name in PAGES:
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        errors, failed = [], []
        page.on("console", lambda m, e=errors: e.append(m.text[:120]) if m.type == "error" else None)
        page.on("response", lambda r, f=failed: f.append("%d %s" % (r.status, r.url.split("/")[-1]))
                if r.status >= 400 and not tolerated(r.url) else None)
        page.goto("%s/%s.html" % (base, name), wait_until="networkidle")
        page.wait_for_timeout(1200)
        stats = page.evaluate("""() => ({
            chars: (document.querySelector('#main') || document.body).innerText.length,
            cards: document.querySelectorAll('.card').length,
            ctl: document.querySelectorAll('button, input, a, .node').length,
            broken: [...document.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0).length })""")
        nav_on = page.evaluate("() => { const a = document.querySelector('.top nav a.on'); return a ? a.textContent.trim() : ''; }")
        page.screenshot(path=os.path.join(SHOT_DIR, "page-%s.png" % name))
        if name in NO_NAV_ENTRY:
            check("导航高亮 %s（刻意不在导航里，只要求不报错）" % name, not nav_on, "高亮「%s」" % nav_on)
        else:
            check("导航高亮 %s" % name, bool(nav_on), "当前高亮「%s」" % nav_on)
        # 问答这类页面首屏本来就短，所以看"有内容 + 有可交互控件"，不卡固定字数
        check("页面 %s" % name,
              stats["chars"] > 100 and stats["ctl"] > 0 and not errors and not failed and stats["broken"] == 0,
              "正文 %d 字 / 卡片 %d / 控件 %d / 坏图 %d / 报错 %d / 失败请求 %s" % (
                  stats["chars"], stats["cards"], stats["ctl"], stats["broken"], len(errors), failed[:2]))
        ctx.close()

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(base + "/provenance.html", wait_until="networkidle")
    page.wait_for_timeout(1200)
    steps = page.evaluate("() => document.querySelectorAll('.step').length")
    text = page.evaluate("() => document.querySelector('#main').innerText")
    check("溯源页含方法论段", steps >= 5 and "刻意不拿的东西" in text and "什么时候重核" in text,
          "方法说明 %d 条" % steps)
    page.screenshot(path=os.path.join(SHOT_DIR, "provenance-method.png"))
    code = page.request.get(base + "/favicon.ico").status
    code2 = page.request.get(base + "/img/favicon.svg").status
    check("头标资源存在", code == 200 and code2 == 200, "favicon.ico %d / favicon.svg %d" % (code, code2))
    ctx.close()


def test_talent(browser, base):
    print("\n[2] 天赋计算器交互（演示结构：层级门槛 [0,5,10,15,20] + 前置链）")
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000},
                             permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    open_talent(page, base)

    check("演示结构已载入", page.evaluate("document.querySelectorAll('.node').length") == 42,
          "节点 %d" % page.evaluate("document.querySelectorAll('.node').length"))

    # 前置校验：a-1-1 需要 a-0-0 与 a-0-1，且本系需 5 点解锁第 2 层
    before = ranks(page, DEMO_A11)
    click(page, DEMO_A11)
    page.wait_for_timeout(250)
    after = ranks(page, DEMO_A11)
    check("前置/门槛未满足时不可点", before["ranks"] == 0 and after["ranks"] == 0 and before["lock"],
          "a-1-1 点数保持 %s，锁定位=%s" % (after["ranks"], after["lock"]))

    # 加点：把第 1 层投满 5 点
    for _ in range(3):
        click(page, DEMO_A00)
        page.wait_for_timeout(150)
    for _ in range(2):
        click(page, DEMO_A01)
        page.wait_for_timeout(150)
    r00, r01 = ranks(page, DEMO_A00), ranks(page, DEMO_A01)
    check("左键加点累加", r00["ranks"] == 3 and r01["ranks"] == 2, "a-0-0=%s a-0-1=%s｜%s" % (r00["ranks"], r01["ranks"], points_text(page)))

    # 上限卡口：a-0-0 maxRanks=3，再点不该涨
    click(page, DEMO_A00)
    page.wait_for_timeout(200)
    check("达到点数上限后不再加", ranks(page, DEMO_A00)["ranks"] == 3, "a-0-0=%s" % ranks(page, DEMO_A00)["ranks"])

    # 门槛解除后前置满足 → 可点
    r11 = ranks(page, DEMO_A11)
    check("投满 5 点后第 2 层解锁", r11["lock"] is False, "a-1-1 锁定=%s" % r11["lock"])
    click(page, DEMO_A11)
    page.wait_for_timeout(200)
    check("解锁后可加点", ranks(page, DEMO_A11)["ranks"] == 1, "a-1-1=%s" % ranks(page, DEMO_A11)["ranks"])
    page.screenshot(path=os.path.join(SHOT_DIR, "talent-added.png"))

    # 键盘可达性
    page.evaluate("""() => document.querySelector('[data-n="%s"]').focus()""" % DEMO_A01)
    page.keyboard.press("Enter")
    page.wait_for_timeout(200)
    check("键盘 Enter 可加点", ranks(page, DEMO_A01)["ranks"] == 3, "a-0-1=%s" % ranks(page, DEMO_A01)["ranks"])
    page.evaluate("""() => document.querySelector('[data-n="%s"]').focus()""" % DEMO_A01)
    page.keyboard.press("Backspace")
    page.wait_for_timeout(250)
    check("键盘 Backspace 固定减点", ranks(page, DEMO_A01)["ranks"] == 2, "a-0-1=%s" % ranks(page, DEMO_A01)["ranks"])
    page.evaluate("""() => document.querySelector('[data-n="%s"]').focus()""" % DEMO_A01)
    page.keyboard.press("Enter")
    page.wait_for_timeout(250)
    check("键盘可来回加减（回到 3 点，后续用例基于此）",
          ranks(page, DEMO_A01)["ranks"] == 3, "a-0-1=%s" % ranks(page, DEMO_A01)["ranks"])

    # 减点模式：切模式后左键必须减点（本轮修的就是这个）
    page.evaluate("() => document.getElementById('mode').click()")
    page.wait_for_timeout(200)
    label = page.evaluate("() => document.getElementById('mode').textContent.trim()")
    click(page, DEMO_A01)
    page.wait_for_timeout(250)
    check("减点模式下左键真的减点", "减点" in label and ranks(page, DEMO_A01)["ranks"] == 2,
          "按钮[%s] a-0-1=%s" % (label, ranks(page, DEMO_A01)["ranks"]))
    page.evaluate("() => document.getElementById('mode').click()")
    page.wait_for_timeout(200)

    # 右键通道固定减点
    click(page, DEMO_A01, "right")
    page.wait_for_timeout(250)
    check("右键减点可用", ranks(page, DEMO_A01)["ranks"] == 1, "a-0-1=%s" % ranks(page, DEMO_A01)["ranks"])

    # 长按通道（移动端）：长按减 1，且随后触发的 click 不能又加回去
    long_press(page, DEMO_A01)
    check("长按减点可用且不会被随后的 click 抵消", ranks(page, DEMO_A01)["ranks"] == 0,
          "a-0-1=%s" % ranks(page, DEMO_A01)["ranks"])

    # 级联减点：重新铺一个确定状态，再抽掉前置，依赖它的 a-1-1 应被清空
    page.evaluate("() => { document.getElementById('reset').click(); }")
    page.wait_for_timeout(300)
    for _ in range(3):
        click(page, DEMO_A00)
        page.wait_for_timeout(120)
    for _ in range(2):
        click(page, DEMO_A01)
        page.wait_for_timeout(120)
    click(page, DEMO_A11)
    page.wait_for_timeout(200)
    check("级联减点前 a-1-1 仍有 1 点", ranks(page, DEMO_A11)["ranks"] == 1, "a-1-1=%s" % ranks(page, DEMO_A11)["ranks"])
    for _ in range(3):
        click(page, DEMO_A00, "right")
        page.wait_for_timeout(150)
    r = ranks(page, DEMO_A11)
    check("抽掉前置后级联清空", ranks(page, DEMO_A00)["ranks"] == 0 and r["ranks"] == 0,
          "a-0-0=%s → a-1-1=%s" % (ranks(page, DEMO_A00)["ranks"], r["ranks"]))
    page.screenshot(path=os.path.join(SHOT_DIR, "talent-cascade.png"))

    # 分享编码 + 无痕还原
    for _ in range(2):
        click(page, DEMO_A00)
        page.wait_for_timeout(150)
    click(page, DEMO_A01)
    page.wait_for_timeout(150)
    origin = (ranks(page, DEMO_A00)["ranks"], ranks(page, DEMO_A01)["ranks"])
    page.evaluate("() => document.getElementById('share').click()")
    page.wait_for_timeout(400)
    hash_ = page.evaluate("() => location.hash")
    check("分享生成 hash", len(hash_) > 10, "长度 %d" % len(hash_))

    ctx2 = browser.new_context(viewport={"width": 1440, "height": 1000})
    p2 = ctx2.new_page()
    open_talent(p2, base, hash_)
    back = (ranks(p2, DEMO_A00)["ranks"], ranks(p2, DEMO_A01)["ranks"])
    check("无痕窗口按 hash 还原方案", back == origin, "原 %s → 还原 %s" % (origin, back))
    ctx2.close()

    # 复制方案文本
    page.evaluate("() => document.getElementById('copy').click()")
    page.wait_for_timeout(400)
    clip = page.evaluate("() => navigator.clipboard.readText()")
    check("复制方案文本含中英名与点数", "演示系 A" in clip and "3/" in clip, repr(clip[:60]))

    # 单系清空
    page.evaluate("""() => { const b = document.querySelector('[data-clear="0"]'); if (b) b.click(); }""")
    page.wait_for_timeout(400)
    check("单系清空生效", ranks(page, DEMO_A00)["ranks"] == 0, "a-0-0=%s" % ranks(page, DEMO_A00)["ranks"])
    ctx.close()


def test_dungeon_banner(browser, base):
    print("\n[4] 副本横幅渲染（防拉伸回归）")
    import json
    ctx = browser.new_context(viewport={"width": 1440, "height": 1200})
    page = ctx.new_page()
    page.goto(base + "/dungeons.html", wait_until="networkidle")
    page.wait_for_timeout(1200)
    geo = page.evaluate("""() => {
      const t = document.querySelector('.dbn2-n'); const r = t.getBoundingClientRect();
      const cs = getComputedStyle(t);
      return { banners: document.querySelectorAll('.dbn2').length,
               svgText: document.querySelectorAll('.dbn-art text').length,
               w: r.width, h: r.height, font: parseFloat(cs.fontSize),
               transform: cs.transform };
    }""")
    per_char = geo["w"] / max(len(page.evaluate("() => document.querySelector('.dbn2-n').textContent")), 1)
    check("每张副本卡都有横幅", geo["banners"] >= 20, "%d 张" % geo["banners"])
    check("文字不在 SVG 里（不会被非等比缩放拉变形）", geo["svgText"] == 0, "SVG 内 text 节点 %d" % geo["svgText"])
    check("横幅标题无 transform 变形", geo["transform"] in ("none", "matrix(1, 0, 0, 1, 0, 0)"), geo["transform"])
    check("标题字宽未被横向拉伸", per_char <= geo["font"] * 1.35,
          "字号 %.0fpx，单字实测宽 %.1fpx" % (geo["font"], per_char))
    marks = page.evaluate("() => document.querySelectorAll('.dbn2 .dbn2-mark').length")
    # 2026-10-12 站主决定：横幅上的素材出处角标（"客户端原画 · 本地转存"/"示意图 · 非游戏原画"）撤掉，
    # 这里从"每张都要标"改成反向断言"角标不许回来"；有原画的卡仍然必须真的挂上本地图。
    check("横幅上的素材出处角标已撤", marks == 0, "%d 个角标残留" % marks)
    art = page.evaluate("""() => ({photo: document.querySelectorAll('.dbn2 img.dbn-art').length,
      svg: document.querySelectorAll('svg.dbn-art').length})""")
    check("有客户端原画的副本用上了本地图片，没原画的仍是自绘横幅",
          art["photo"] >= 1 and art["svg"] >= 1, json.dumps(art, ensure_ascii=False))
    body = page.evaluate("() => document.querySelector('#main').innerText")
    check("副本页不出现内部口径话术", "口径见来源" not in body and "provenance" not in body)
    page.screenshot(path=os.path.join(SHOT_DIR, "dungeons-banner.png"))
    ctx.close()


def test_chooser(browser, base):
    print("\n[3] 选职业问答")
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m, e=errors: e.append(m.text[:100]) if m.type == "error" else None)
    page.goto(base + "/chooser.html", wait_until="networkidle")
    page.wait_for_timeout(1200)
    total = page.evaluate("() => document.querySelectorAll('.qopt').length")
    check("首题渲染出选项", total >= 3, "第 1 题 %d 个选项" % total)

    # 答完全部题目
    steps = page.evaluate("() => document.querySelectorAll('.cov i').length")
    for _ in range(steps):
        page.evaluate("() => document.querySelector('.qopt').click()")
        page.wait_for_timeout(250)
    cards = page.evaluate("() => document.querySelectorAll('.mcard').length")
    names = page.evaluate("() => [...document.querySelectorAll('.mcard h2')].map(h => h.textContent.trim())")
    check("答完给出前三名候选", cards == 3, "%d 张候选卡：%s" % (cards, " / ".join(names)))
    check("候选带匹配度与天赋入口",
          page.evaluate("() => !!document.querySelector('.mbar i') && !!document.querySelector('a.btn[href*=talent]')"))
    body = page.evaluate("() => document.querySelector('#main').innerText")
    banned = [w for w in ["最强", "强度排行", "T0", "TOP", "梯度"] if w in body and "不是强度排行" not in body]
    check("结果页不做强度排行话术", not banned and "不是强度排行" in body, "命中词 %s" % banned)
    check("结果页标注本站观点口径", "不是官方推荐" in body or "玩法归类" in body)
    page.screenshot(path=os.path.join(SHOT_DIR, "chooser-result.png"))

    # 重开 → 答两题 → 回退改答案
    page.evaluate("() => document.getElementById('creset').click()")
    page.wait_for_timeout(300)
    check("重新开始回到第 1 题", "第 1 /" in page.evaluate("() => document.querySelector('#main').innerText"))
    page.evaluate("() => document.querySelector('.qopt').click()")
    page.wait_for_timeout(250)
    page.evaluate("() => document.querySelectorAll('.qopt')[1].click()")
    page.wait_for_timeout(250)
    page.evaluate("() => document.getElementById('cprev').click()")
    page.wait_for_timeout(300)
    check("上一题可回退并保留已选", page.evaluate("() => document.querySelectorAll('.qopt.on').length") == 1)
    page.evaluate("() => document.querySelector('.qopt.on').click()")
    page.wait_for_timeout(250)
    check("改答案后能继续往下走", "第 3 /" in page.evaluate("() => document.querySelector('#main').innerText"))
    check("问答页无控制台报错", not errors, "; ".join(errors[:2]))
    ctx.close()


def test_abilities(browser, base):
    print("\n[6] 技能四态表")
    ctx = browser.new_context(viewport={"width": 1440, "height": 1200})
    page = ctx.new_page()
    page.goto(base + "/skills.html", wait_until="networkidle")
    page.wait_for_timeout(1500)
    rows = page.evaluate(r"""() => [...document.querySelectorAll('#abtbl tbody tr')].map(tr => ({
        name: (tr.children[0].querySelector('b') || tr.children[0]).innerText.trim(),
        spec: tr.children[1].innerText.replace(/\n/g,' ').trim(),
        quote: tr.children[3].innerText.trim() }))""")
    check("四态表有真实条目", len(rows) >= 30, "%d 行" % len(rows))
    bad = [r["name"] for r in rows if not r["quote"] or len(r["name"]) < 2 or r["name"] not in r["quote"]]
    check("每行都是官方原句且含名称", not bad, "不合格 %s" % bad[:3])
    check("不出现『未变』分组",
          page.evaluate("() => !document.querySelector('#abtbl').innerText.includes('未变 ·')"))
    check("专精列显示中文不是英文 key",
          page.evaluate("() => {const t=document.querySelector('#abtbl').innerText; return t.indexOf('beast-mastery')<0 && t.indexOf('marksmanship')<0;}"))
    page.evaluate("() => { const s = document.getElementById('c'); s.value='paladin'; s.dispatchEvent(new Event('change')); }")
    page.wait_for_timeout(900)
    check("无官方稿的职业显示空态而不是空表（原因取自 abilities.json 的「没收到的」）",
          "深度解析稿" in page.evaluate("() => document.querySelector('#abtbl').innerText"))
    page.screenshot(path=os.path.join(SHOT_DIR, "skills-abilities.png"))
    ctx.close()


def test_spellbook(browser, base):
    """M2（2026-10-16）：法术书接进技能页、成就独立成页。
       两栈同页同断言——数字全部从 src/data 现算，不在脚本里写死条数。"""
    print("\n[6a] 法术书与成就页")
    import json
    S = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    sp = json.load(open(os.path.join(SRC, "data", "spells.json"), encoding="utf-8"))["spells"]
    ad = json.load(open(os.path.join(SRC, "data", "achievements.json"), encoding="utf-8"))
    ach, ameta = ad["achievements"], ad["meta"]["counts"]
    show = [a for a in ach if not a.get("devOnly")]
    sp_groups = len(set((x["classId"], x["tab"] or "未分系") for x in sp))
    n_alt = len([x for x in sp if x.get("ranksAlt")]) + len([x for x in sp if x.get("learnAlt")])
    ach_groups = len(set((a["gid"], a["cat"] or "未分类") for a in show))
    # 分组条在两栈是两种实现：旧站是一行 .lgrp，新站 10-16 起改成表内吸附的 tbody.grp
    GRPS = "() => document.querySelectorAll('%s .lgrp, %s tbody.grp').length"

    for label, url in ((u"旧站", base + "/skills.html"), (u"新站", APP_BASE + "/#/skills")):
        if label == u"新站" and not app_up(browser):
            break
        ctx = browser.new_context(viewport={"width": 1440, "height": 1200})
        page = ctx.new_page()
        errs, failed = [], []
        page.on("console", lambda m, e=errs: e.append(m.text[:120]) if m.type == "error" else None)
        page.on("response", lambda r, f=failed: f.append("%d %s" % (r.status, r.url.split("/")[-1]))
                if r.status >= 400 and not tolerated(r.url) else None)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1500)
        check("%s 法术书行数等于数据条数" % label,
              page.evaluate("() => document.querySelectorAll('#sptbl tbody tr:not(.grp2h)').length") == S["spells"],
              "%d 行 / 数据 %d" % (page.evaluate("() => document.querySelectorAll('#sptbl tbody tr:not(.grp2h)').length"),
                                   S["spells"]))
        # 分组条在两栈是两种实现：旧站一行 .lgrp，新站 10-16 起改成表内吸附的 tbody.grp
        check("%s 按职业与系分组" % label,
              page.evaluate(GRPS % ("#sptbl", "#sptbl")) == sp_groups,
              "%d 组 / 期望 %d" % (page.evaluate(GRPS % ("#sptbl", "#sptbl")), sp_groups))
        check("%s 读数写着条数" % label,
              str(S["spells"]) in page.evaluate("() => document.getElementById('spcnt').textContent"))
        check("%s 两说的行两个数都摆着" % label,
              page.evaluate("() => document.querySelectorAll('#sptbl .conf').length") == n_alt,
              "%d 处 / 数据 %d" % (page.evaluate("() => document.querySelectorAll('#sptbl .conf').length"), n_alt))
        cell = page.evaluate(r"""() => {
          const td = [...document.querySelectorAll('#sptbl tbody tr:not(.grp2h) td')];
          return td.filter(x => x.innerText.includes('有两个说法') && !/\d+\s*\/\s*\d+/.test(x.innerText)).length;
        }""")
        check("%s 两说那一行确实摆着两个数" % label, cell == 0, "%d 处只有一个数" % cell)
        long_txt = page.evaluate(r"""() => [...document.querySelectorAll('#sptbl tbody tr:not(.grp2h)')].map(tr =>
          [...tr.children].reduce((a, td) => Math.max(a, td.innerText.replace(/\n/g, ' ').length), 0))""")
        check("%s 法术书每格都是短取值，没有描述正文" % label,
              long_txt and max(long_txt) <= 30, "最长 %d 字" % (max(long_txt) if long_txt else 0))
        check("%s 没有百分号（掉率与概率都不该出现在这页）" % label,
              "%" not in page.evaluate("() => document.getElementById('sptbl').innerText"))
        one = sp[0]["classId"]
        exp_one = len([x for x in sp if x["classId"] == one])
        page.evaluate("(c) => { const s = document.getElementById('c'); s.value = c; "
                      "s.dispatchEvent(new Event('change')); }", one)
        page.wait_for_timeout(700)
        check("%s 按职业筛选后行数对得上" % label,
              page.evaluate("() => document.querySelectorAll('#sptbl tbody tr:not(.grp2h)').length") == exp_one,
              "%d 行 / 期望 %d" % (page.evaluate("() => document.querySelectorAll('#sptbl tbody tr:not(.grp2h)').length"), exp_one))
        page.screenshot(path=os.path.join(SHOT_DIR, "spellbook-%s.png" % ("app" if label == u"新站" else "legacy")))
        check("%s 法术书页无报错与失败请求" % label, not errs and not failed,
              "; ".join((errs + failed)[:2]) or "干净")
        ctx.close()

    # 搜索索引点一条法术跳进来要已经是筛好的（带 c=<职业>&q=<名字>）
    ctx = browser.new_context(viewport={"width": 1440, "height": 1200})
    page = ctx.new_page()
    tgt = [x for x in sp if x["classId"] == "warrior"][0]
    page.goto(base + "/skills.html?c=%s&q=%s" % (tgt["classId"], urllib.parse.quote(tgt["name"])),
              wait_until="networkidle")
    page.wait_for_timeout(1200)
    check("搜索带着职业与词跳进来，落地只剩那一条",
          page.evaluate("() => document.querySelectorAll('#sptbl tbody tr:not(.grp2h)').length") == 1
          and page.evaluate("() => document.getElementById('q').value") == tgt["name"],
          page.evaluate("() => document.getElementById('cnt').textContent"))
    ctx.close()

    for label, url in ((u"旧站", base + "/achievements.html"), (u"新站", APP_BASE + "/#/achievements")):
        if label == u"新站" and not app_up(browser):
            break
        ctx = browser.new_context(viewport={"width": 1440, "height": 1200})
        page = ctx.new_page()
        errs = []
        page.on("console", lambda m, e=errs: e.append(m.text[:120]) if m.type == "error" else None)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1500)
        got = page.evaluate("() => document.querySelectorAll('#tbl tbody tr:not(.grp2h)').length")
        check("%s 成就列出的条数等于「能拿的那些」" % label, got == len(show),
              "%d 行 / 数据可列 %d（总 %d）" % (got, len(show), ameta["total"]))
        check("%s 成就分组数对得上数据" % label,
              page.evaluate(GRPS % ("#tbl", "#tbl")) == ach_groups,
              "%d 组 / 期望 %d" % (page.evaluate(GRPS % ("#tbl", "#tbl")), ach_groups))
        opts = page.evaluate(r"""() => [...document.querySelectorAll('#g option')].slice(1)
          .map(o => parseInt(o.textContent.match(/（(\d+)）/)[1], 10))""")
        check("%s 下拉里每个大类的数与屏幕上看到的一致" % label,
              sum(opts) == got, "下拉合计 %d / 页面 %d 行" % (sum(opts), got))
        dev = [a["name"] for a in ach if a.get("devOnly")]
        body = page.evaluate("() => document.querySelector('#main').innerText")
        leak = [n for n in dev if n in body]
        check("%s 客户端里的开发埋点一条都不上页面" % label, not leak, "漏出 %s" % leak[:3])
        en_missing = page.evaluate(r"""() => [...document.querySelectorAll('#tbl tbody tr:not(.grp2h)')]
          .filter(tr => !tr.children[2].innerText.trim()).length""")
        check("%s 每条都带着英文原名（没中文名的不机翻）" % label, en_missing == 0,
              "%d 行缺英文原名" % en_missing)
        check("%s 成就页没有完成条件正文与百分号（红线）" % label,
              "%" not in body and "criteria" not in body.lower())
        check("%s 成就页无脚本报错" % label, not errs, "; ".join(errs[:2]) or "干净")
        g0 = show[0]["gid"]
        exp_g = len([a for a in show if a["gid"] == g0])
        page.evaluate("(g) => { const s = document.getElementById('g'); s.value = g; "
                      "s.dispatchEvent(new Event('change')); }", g0)
        page.wait_for_timeout(700)
        check("%s 按大类筛选后行数对得上" % label,
              page.evaluate("() => document.querySelectorAll('#tbl tbody tr:not(.grp2h)').length") == exp_g,
              "%d 行 / 期望 %d" % (page.evaluate("() => document.querySelectorAll('#tbl tbody tr:not(.grp2h)').length"), exp_g))
        page.screenshot(path=os.path.join(SHOT_DIR, "achievements-%s.png" %
                                          ("app" if label == u"新站" else "legacy")))
        ctx.close()

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(base + "/achievements.html?q=" + urllib.parse.quote(show[0]["name"]), wait_until="networkidle")
    page.wait_for_timeout(1200)
    check("搜索词跳进成就页就已是筛好的",
          page.evaluate("() => document.querySelectorAll('#tbl tbody tr:not(.grp2h)').length") > 0
          and page.evaluate("() => document.getElementById('q').value") == show[0]["name"],
          page.evaluate("() => document.getElementById('cnt').textContent"))
    ctx.close()

    # ---- 新站视觉层（docs/DESIGN-app-upgrade-2026-10-16.md）----
    # 旧站已冻结：新样式全部走新类名 + 单独一份 board.css（只由 app 引入），
    # 这三条钉的就是"隔离真的成立"——旧站 DOM 里出现 .board/.chip-st 说明新规则漏了作用域。
    if app_up(browser):
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        page.goto(base + "/skills.html", wait_until="networkidle")
        page.wait_for_timeout(1200)
        check("旧站（已冻结）DOM 里不出现新站的表结构",
              page.evaluate("() => document.querySelectorAll('.board, .chip-st, .bhead, .grp2h').length") == 0,
              page.evaluate("() => document.querySelectorAll('.board, .chip-st').length"))
        ctx.close()

        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        page.goto(APP_BASE + "/#/skills", wait_until="networkidle")
        page.wait_for_timeout(1800)
        exp_state = len([x for x in sp if x.get("state")])
        chips = page.evaluate("() => document.querySelectorAll('#sptbl .chip-st').length")
        check("新站状态徽标条数等于数据里有对照状态的条数", chips == exp_state,
              "%d 枚 / 数据 %d 条" % (chips, exp_state))
        lay = page.evaluate("""() => { const t = document.querySelector('#sptbl');
          if (!t) return null; const cs = getComputedStyle(t);
          const th = [...t.querySelectorAll(':scope > thead th')].map(x => Math.round(x.getBoundingClientRect().width));
          return { layout: cs.tableLayout, cols: th, over: document.documentElement.scrollWidth - innerWidth }; }""")
        check("新站板块表列宽受控（fixed + 图标列 ≤ 60px + 整页不横向溢出）",
              lay and lay["layout"] == "fixed" and lay["cols"][0] <= 60 and lay["over"] <= 1,
              json.dumps(lay, ensure_ascii=False))
        sticky = page.evaluate("""() => { const th = document.querySelector('#sptbl > thead th');
          return th ? getComputedStyle(th).position : null; }""")
        check("新站表头在桌面是吸附的（窄屏由 board.css 显式关掉，见那条注释）",
              sticky == "sticky", sticky)
        page.screenshot(path=os.path.join(SHOT_DIR, "app-board-skills.png"))
        ctx.close()

        ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.goto(APP_BASE + "/#/professions", wait_until="networkidle")
        page.wait_for_timeout(1800)
        m = page.evaluate("""() => ({ over: document.documentElement.scrollWidth - innerWidth,
          fade: [...document.querySelectorAll('.boardwrap')].length,
          src: [...document.querySelectorAll('.board .c-src')].filter(x => x.innerText.indexOf('商人') >= 0).length })""")
        check("新站专业页 375 下整页不横向溢出（表在容器里滚）", m["over"] <= 1, json.dumps(m))
        check("新站专业页来源那一格仍写着商人（视觉改版没把 M2-G 的层弄丢）", m["src"] > 0,
              "%d 行" % m["src"])
        page.screenshot(path=os.path.join(SHOT_DIR, "app-board-prof-m.png"))
        ctx.close()

        # ---- 第二批：板块表骨架铺满剩余页面（2026-10-16 用户"就这么做"）----
        # 每页只钉三件事：确有 .board 且是 fixed；桌面整页不横溢；375 整页不横溢
        # （表在 .boardwrap 里自己滚）。列宽的具体数值随数据变，钉死会变成又一处
        # "把会变的数抄进不会变的地方"，所以这里只量溢出与骨架存在性。
        BOARD_PAGES = [("world", "/#/world"), ("legacy", "/#/legacy"), ("raids", "/#/raids"),
                       ("dungeons", "/#/dungeons"), ("dungeon", "/#/dungeon?d=gnomeregan"),
                       ("updates", "/#/updates"), ("systems", "/#/systems"),
                       ("rank", "/#/rank"), ("classes", "/#/classes"), ("skills", "/#/skills")]
        for vp_tag, vp, mob in (("桌面", {"width": 1440, "height": 1000}, False),
                                ("移动 375", {"width": 375, "height": 812}, True)):
            ctx = browser.new_context(viewport=vp, is_mobile=mob, has_touch=mob)
            for pn, ppath in BOARD_PAGES:
                page = ctx.new_page()
                page.goto(APP_BASE + ppath, wait_until="networkidle")
                page.wait_for_timeout(1500)
                r = page.evaluate("""() => {
                  const ts = [...document.querySelectorAll('table.board')];
                  return { n: ts.length,
                    fixed: ts.filter(t => getComputedStyle(t).tableLayout === 'fixed').length,
                    wrap: document.querySelectorAll('.boardwrap').length,
                    over: document.documentElement.scrollWidth - innerWidth }; }""")
                check("新站 %s 页 %s：板块表骨架在位（%d 张，fixed %d，横滚容器 %d）" % (
                      pn, vp_tag, r["n"], r["fixed"], r["wrap"]),
                      r["n"] > 0 and r["fixed"] == r["n"], json.dumps(r, ensure_ascii=False))
                check("新站 %s 页 %s：整页不横向溢出（宽表在容器里滚）" % (pn, vp_tag),
                      r["over"] <= 1, "溢出 %dpx" % r["over"])
                page.close()
            ctx.close()


def test_css_tokens(browser, base):
    """设计令牌存在性检查（2026-10-17 加，起因是配装页我凭空写了 var(--bg-1)）。
       拼错的令牌名不会报错、不会构建失败，只会让那条声明整条失效——
       popover 当时底色是 transparent，内容从浮层后面透出来，只有看图才发现。
       所以这里静态扫一遍：新站用到的每个 --x 必须有地方声明过。
       只扫 app 侧（旧站已冻结：app.css 里 #foot .fwrap 与 .hsec 用的 --wrap
       从来没声明过，那是旧站的既成事实，列进开放项，不在这条断言里翻案）。"""
    print("\n[6c] 设计令牌存在性（新站）")
    import glob

    def read(fp):
        try:
            return open(fp, encoding="utf-8").read()
        except Exception:
            return ""

    # 声明来源：三份 CSS + 各 .vue 的 style 块 + JS 里 setProperty('--x'
    decl_src = glob.glob(os.path.join(SRC, "css", "*.css")) \
        + glob.glob(os.path.join(ROOT, "app", "src", "**", "*.vue"), recursive=True) \
        + glob.glob(os.path.join(ROOT, "app", "src", "**", "*.js"), recursive=True)
    declared = set()
    for fp in decl_src:
        t = read(fp)
        # 声明点有两种写法：CSS 里的 --x: 值，和 JS/Vue 内联 style 里的 '--x': 值
        # （传承页的列数就是后者：:style="{ '--cols': curTree.cols }"，第一版没认这种，误报了一次）
        for m in re.finditer(r"['\"]?(--[A-Za-z0-9_-]+)['\"]?\s*:", t):
            declared.add(m.group(1))
        for m in re.finditer(r"setProperty\(\s*['\"](--[A-Za-z0-9_-]+)['\"]", t):
            declared.add(m.group(1))
    # 使用来源：新站侧全部（含只由新站加载的 board.css）
    use_src = glob.glob(os.path.join(ROOT, "app", "src", "**", "*.vue"), recursive=True) \
        + glob.glob(os.path.join(ROOT, "app", "src", "**", "*.js"), recursive=True) \
        + [os.path.join(SRC, "css", "board.css")]
    used = {}
    for fp in use_src:
        for m in re.finditer(r"var\(\s*(--[A-Za-z0-9_-]+)", read(fp)):
            used.setdefault(m.group(1), set()).add(os.path.relpath(fp, ROOT))
    missing = {k: sorted(v) for k, v in used.items() if k not in declared}
    check("新站用到的设计令牌全部有声明（%d 个用到 / %d 个已声明）" % (len(used), len(declared)),
          not missing,
          "没声明：%s" % "; ".join("%s→%s" % (k, ",".join(v[:2])) for k, v in sorted(missing.items()))[:220]
          if missing else "干净")

def test_world_pins(browser, base):
    """世界页四个面板共用一套点位图（2026-10-19 站主：把稀有那版铺到其余三个面板；
       同日再改：区域面板**一行一张**，左边图右边点位列表，原来一行两张太小）。
       盯六件事：① 每个面板的带数/点位数/列表行数都等于 world.json 现算的数；
       ② 区域卡一行一张、卡上混标三类，点数=能标的、行数=全部条数；
       ③ 区域卡的点位与"跳到该区域稀有列表"那一行按钮不互相嵌套（按钮套按钮是无效 HTML）；
       ④ 红框里那两处文字确实没了（首屏五格读数、"先挑区域"标题）；
       ⑤ 只换查询参数也要切面板（/world?t=zones → ?t=books 不换组件实例）；
       ⑥ 桌面与 375 都不横溢，窄屏地图仍占满一整块。"""
    print("\n[6e] 世界页四面板共用点位图")
    import json
    W = json.load(open(os.path.join(SRC, "data", "world.json"), encoding="utf-8"))
    zones = W.get("zones") or []
    rares = W.get("rares") or []
    books = W.get("books") or []
    camps = [p for c in ((W.get("bagTool") or {}).get("camps") or []) for p in (c.get("places") or [])]
    # art.json 的 maps 键就是地图号，值是本地图文件——"有没有这张图"以它为准，不靠猜
    art_maps = set((json.load(open(os.path.join(SRC, "data", "art.json"), encoding="utf-8"))
                    .get("maps") or {}).keys())
    pin = lambda x: bool(x.get("mapFile") and x.get("mark"))
    znames = {z["nameCn"] for z in zones}
    want_zone_pins = len([x for x in rares + books + camps if pin(x) and x.get("zone") in znames])
    # 列表那一列比图上多：本地没切到那张图的稀有不上图但要能查到，所以行数按全部条数算
    want_zone_rows = len([x for x in rares + books + camps if x.get("zone") in znames])
    book_zones = {b.get("zone") for b in books if b.get("zone")}
    camp_zones = {c.get("zone") for c in camps if c.get("zone")}

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:140]))

    page.goto(APP_BASE + "/#/world?t=zones", wait_until="networkidle")
    page.wait_for_timeout(2400)
    z = page.evaluate("""() => { const cards = [...document.querySelectorAll('.zcard')];
      const grid = document.querySelector('.zgrid');
      const big = document.querySelector('.zcard .zbig');
      return { cards: cards.length,
        cols: grid ? (getComputedStyle(grid).gridTemplateColumns || '').trim().split(/\\s+/).length : 0,
        mapW: big ? Math.round(big.getBoundingClientRect().width) : 0,
        lists: document.querySelectorAll('.zcard .zband > .zlist').length,
        rows: document.querySelectorAll('.zcard .zband > .zlist .zrow').length,
        dots: document.querySelectorAll('.zcard .zdot').length,
        kinds: [...new Set([...document.querySelectorAll('.zcard .zdot')].map(d => d.dataset.kind))],
        nested: cards.filter(c => c.matches('button') || c.querySelector('button button')).length,
        bodyBtn: document.querySelectorAll('.zcard button.zhead').length,
        noimg: [...document.querySelectorAll('.zcard .zbig-id')].map(e => e.innerText.trim()),
        bigCards: [...document.querySelectorAll('.zcard')].filter(c => c.querySelector('.zbig')).length,
        nomap: document.querySelectorAll('.zcard .zband.nomap').length,
        heroStats: (document.querySelector('.cdhead.big').closest('.card').querySelectorAll('.stats') || []).length,
        over: document.documentElement.scrollWidth - window.innerWidth}; }""")
    check("区域面板一行一张图（站主：原来一行两个、图太小），左图右列表同一版式",
          z["cards"] == len(zones) == 44 and z["cols"] == 1 and z["lists"] == len(zones)
          and z["mapW"] >= 520,
          "%d 张卡 / 网格 %d 列 / 右侧列表 %d 份 / 图宽 %dpx"
          % (z["cards"], z["cols"], z["lists"], z["mapW"]))
    check("区域卡每张都带该区域的全部点位，三类点混标在同一张上",
          z["dots"] == want_zone_pins and sorted(z["kinds"]) == ["book", "camp", "rare"]
          and z["cards"] == len(zones),
          "%d 个点（数据能标在区域卡上的 %d）/ 类型 %s" % (z["dots"], want_zone_pins, z["kinds"]))
    check("区域卡不是按钮套按钮（点位自己是按钮，整卡是外层 div + 上面一行信息是按钮）",
          z["nested"] == 0 and z["bodyBtn"] == len(zones),
          "嵌套 %d 处 / 区域信息按钮 %d 个" % (z["nested"], z["bodyBtn"]))
    check("右侧列表那一列一条不少：行数 = 该区域的稀有 + 书 + 营地（含标不出点位的）",
          z["rows"] == want_zone_rows,
          "列表 %d 行，数据 %d 条" % (z["rows"], want_zone_rows))
    check("整张图都标不出点的区域，仍然写明这是哪张地图的编号，不留空盒",
          len(z["noimg"]) == len([x for x in zones if not x.get("mapFile")])
          and all("地图编号" in t for t in z["noimg"]),
          "%d 张没图的：%s" % (len(z["noimg"]), z["noimg"]))
    # 上面那条只证明"编号还在"，证明不了那个 120px 的空图框没了（2026-10-20 W01 改的就是这个）。
    # 这一条钉两件事：有底图的才有 .zbig；没底图的那几张整块换成单列紧凑布局（.zband.nomap）。
    check("没有底图的区域不再留空图框：图框只给有图的区域，无图那几张换成整宽紧凑布局",
          z["bigCards"] == len([x for x in zones if x.get("mapFile")])
          and z["nomap"] == len([x for x in zones if not x.get("mapFile")]),
          "图框 %d（数据有图 %d）/ 紧凑态 %d（数据缺图 %d）"
          % (z["bigCards"], len([x for x in zones if x.get("mapFile")]),
             z["nomap"], len([x for x in zones if not x.get("mapFile")])))
    check("首屏那排五格读数按站主要求撤掉了", z["heroStats"] == 0, "还剩 %d 组" % z["heroStats"])
    check("区域面板不横向溢出", z["over"] == 0, "溢出 %d" % z["over"])
    # 某一张卡上的点数必须等于该区域 rareCount + bookCount + 营地数（数据是本轮重算过的）
    per = page.evaluate("""() => { const out = {};
      [...document.querySelectorAll('.zcard')].forEach(c => {
        out[c.dataset.zone] = c.querySelectorAll('.zdot').length; });
      return out; }""")
    camp_by = {}
    for c in camps:
        if pin(c):
            camp_by[c["zone"]] = camp_by.get(c["zone"], 0) + 1
    bad = []
    for zz in zones:
        n = zz["nameCn"]
        want = int(zz.get("rareCount") or 0) + int(zz.get("bookCount") or 0) + camp_by.get(n, 0)
        if per.get(n) != want:
            bad.append("%s 画 %s 个，数据 %s 稀有 + %s 书 + %s 营地 = %d"
                       % (n, per.get(n), zz.get("rareCount"), zz.get("bookCount"),
                          camp_by.get(n, 0), want))
    check("每张区域卡上的点数 = 该区域的稀有数 + 书本数（+ 营地），逐张核过",
          not bad, "；".join(bad[:3]) or "44 张全部对得上")
    # 计数是这一轮刚从"抄上游汇总"改成"按实际条数算"的，钉住别又漂回去
    drift = [z2["nameCn"] for z2 in zones
             if int(z2.get("rareCountSource") or 0) != int(z2.get("rareTotal") or 0)]
    check("数据侧：上游那份汇总的说法留在 rareCountSource 里没删，页面用的是按实际算的那份",
          all("rareCountSource" in z2 and "rareTotal" in z2 for z2 in zones) and len(drift) > 0,
          "%d 个区域的上游汇总与实际条数不一致（正是本轮改掉的）" % len(drift))
    # 2026-10-19：地图号这一层现在有三份来源，顺位写死在 merge-world 里——
    #   ① GI 每条稀有行自带的 ui=（坐标与地图号出自同一行，最硬）② 站内那三层（paint / 分组 id / rareRegions）
    #   ③ XR 那份「区域名→地图号」只补前两层都查不到的空位。三份要对得上，
    #   对不上不悄悄取舍：记进 meta.mapIdMismatch 与 meta.zoneMapFill.conflicts，让人当场看见
    gi_ui = [r for r in rares if r.get("mapIdFrom") == "gi-ui"]
    filled = [r for r in rares if r.get("mapIdFrom") == "xr-zonemap"]
    zm = (W.get("meta") or {}).get("zoneMapFill") or {}
    check("数据侧：地图号以 GI 行内 ui 为主源，XR 那张名字表退成兜底（只补空位）",
          len(gi_ui) >= 300 and all(r.get("mapId") for r in gi_ui) and
          all(r.get("mapId") for r in filled),
          "gi-ui %d 只 · XR 补 %d 只 · 名字表与站内一致 %s 条 / 只 XR 有的区域 %d 个"
          % (len(gi_ui), len(filled), zm.get("agreeWithSite"), zm.get("zonesOnlyHere")))
    check("数据侧：三份来源对账零冲突（mapIdMismatch 与 zoneMapFill.conflicts 都得是空的）",
          not (W.get("meta") or {}).get("mapIdMismatch") and not (zm.get("conflicts") or []),
          "稀有层冲突 %d 条 · 名字表冲突 %d 条"
          % (len((W.get("meta") or {}).get("mapIdMismatch") or []), len(zm.get("conflicts") or [])))
    check("补上地图号不等于就能标点：只有本地真有那张贴图的才许上图",
          all(bool(r.get("mapFile")) == (str(r.get("mapId")) in art_maps)
              for r in rares if r.get("mapId") and r.get("mark")),
          "%d 只有地图号，其中 %d 只本地有贴图可标、%d 只仍只进列表"
          % (len([r for r in rares if r.get("mapId") and r.get("mark")]),
             len([r for r in rares if r.get("mapFile") and r.get("mark")]),
             len([r for r in rares if r.get("mapId") and r.get("mark") and not r.get("mapFile")])))

    page.goto(APP_BASE + "/#/world?t=books", wait_until="networkidle")
    page.wait_for_timeout(2200)
    bk = page.evaluate("""() => ({bands: document.querySelectorAll('.zband').length,
      dots: document.querySelectorAll('.zdot').length, rows: document.querySelectorAll('.zrow').length,
      kinds: [...new Set([...document.querySelectorAll('.zdot')].map(d => d.dataset.kind))],
      old: document.querySelectorAll('.zthumb, table.bktab').length,
      over: document.documentElement.scrollWidth - window.innerWidth})""")
    check("书籍面板也走点位图：一个有书的区域一张图，36 本全标出来",
          bk["bands"] == len(book_zones) and bk["dots"] == len([x for x in books if pin(x)])
          and bk["rows"] == len(books) and bk["kinds"] == ["book"],
          "%d 张图 / %d 个点 / %d 行（数据 %d 本、有坐标的 %d 个区域）"
          % (bk["bands"], bk["dots"], bk["rows"], len(books), len(book_zones)))
    check("书籍原来那张只标一个点的缩略图与五列表已撤掉（信息搬进浮层与列表行）",
          bk["old"] == 0 and bk["over"] == 0, "残留 %d 处" % bk["old"])
    page.evaluate("() => document.querySelectorAll('.zband')[0].scrollIntoView({block:'center'})")
    page.wait_for_timeout(300)
    page.hover(".zdot")
    page.wait_for_timeout(500)
    pop = page.evaluate("""() => { const p = document.querySelector('.zpop'); if (!p) return null;
      return {kind: p.className, title: (p.querySelector('b') || {}).innerText.trim(),
        rows: [...p.querySelectorAll('.zpop-x > div')]
        .map(e => e.innerText.replace(/\\s+/g, ' ').trim())}; }""")
    # 页面第一个浮层是"按等级排下来第一个有书的区域"的第一本书，
    # 不能拿数据里的 books[0] 去比（那是另一本）——按浮层标题回数据里找它自己
    b0 = [x for x in books if pin(x) and x.get("nameCn") == (pop or {}).get("title")]
    want0 = b0 and ["容器 %s" % (b0[0].get("container") or "—"),
                    "位置 %s" % (b0[0].get("place") or "—"),
                    "物品编号 #%s" % b0[0].get("itemId")]
    check("书点位浮层把原来表格里那三列带回来了（容器 / 位置 / 物品编号）",
          pop and "k-book" in pop["kind"] and pop["rows"] == want0,
          json.dumps({"pop": pop, "want": want0}, ensure_ascii=False))
    page.screenshot(path=os.path.join(SHOT_DIR, "app-world-books.png"))

    page.goto(APP_BASE + "/#/world?t=bag", wait_until="networkidle")
    page.wait_for_timeout(2200)
    bg = page.evaluate("""() => ({bands: document.querySelectorAll('.zband').length,
      dots: document.querySelectorAll('.zdot').length, rows: document.querySelectorAll('.zrow').length,
      kinds: [...new Set([...document.querySelectorAll('.zdot')].map(d => d.dataset.kind))],
      old: document.querySelectorAll('#main .rarecard').length,
      over: document.documentElement.scrollWidth - window.innerWidth})""")
    check("营地面板也走点位图：5 处按区域归到图上，旧的「五条各一张缩略图」撤掉",
          bg["bands"] == len(camp_zones) and bg["dots"] == len([c for c in camps if pin(c)])
          and bg["rows"] == len(camps) and bg["kinds"] == ["camp"] and bg["old"] == 0
          and bg["over"] == 0,
          "%d 张图 / %d 个点 / %d 行（数据 %d 处）" % (bg["bands"], bg["dots"], bg["rows"], len(camps)))

    # 只换查询参数也要切面板：/world?t=zones → ?t=books 不换组件实例，
    # 只在建立时读一次 route.query 的话点了不会动（2026-10-19 实测到，搜索跳这一页就撞这条）
    # 先归位到"区域"再只换查询参数——不先归位的话上一段停在营地面板，比的是残留状态
    page.goto(APP_BASE + "/#/world?t=zones", wait_until="networkidle")
    page.wait_for_timeout(1800)
    first_tab = page.evaluate("() => (document.querySelector('.pick.on b') || {}).innerText")
    page.goto(APP_BASE + "/#/world?t=rares", wait_until="networkidle")
    page.wait_for_timeout(1800)
    now = page.evaluate("""() => ({tab: (document.querySelector('.pick.on b') || {}).innerText,
      bands: document.querySelectorAll('.zband').length,
      stats: document.querySelectorAll('#main .stats').length,
      head: document.querySelector('#main').innerText.indexOf('先挑区域') >= 0})""")
    # 带数按数据现算，不写死：区域分组数会随稀有增减而变（2026-10-19 补地图号那一层之后
    # 有稀有点位的区域从 31 涨到 36，写死的数下一次就是假绿或假红）
    want_rare_bands = len({(r.get("zone") or "未归区域") for r in rares})
    check("只换查询参数（不换组件）也要切面板",
          first_tab == "区域" and now["tab"] == "稀有精英" and now["bands"] == want_rare_bands,
          "%s → %s（%d 张图，数据 %d 个区域分组）"
          % (first_tab, now["tab"], now["bands"], want_rare_bands))
    check("「先挑区域」那行标题按站主要求撤掉了", not now["head"],
          "页面上还有" if now["head"] else "已无")

    mctx = browser.new_context(viewport={"width": 375, "height": 812})
    mp = mctx.new_page()
    for t in ("zones", "books", "bag"):
        mp.goto(APP_BASE + "/#/world?t=" + t, wait_until="networkidle")
        mp.wait_for_timeout(2000)
        mm = mp.evaluate("""() => ({over: document.documentElement.scrollWidth - window.innerWidth,
          mapW: (document.querySelector('.zbig') || { offsetWidth: 0 }).offsetWidth,
          cut: [...document.querySelectorAll('.zdot')].some(d => { const r = d.getBoundingClientRect();
            return r.width && (r.right > window.innerWidth + 1 || r.left < -1); }),
          small: [...document.querySelectorAll('.zhead')].filter(e => {
            const r = e.getBoundingClientRect(); return r.width && r.height < 44; }).length})""")
        check("世界页 %s 面板 375：整页不横溢、点位没被切到屏外、区域信息行够 44px 点击区" % t,
              mm["over"] == 0 and not mm["cut"] and mm["small"] == 0,
              json.dumps(mm, ensure_ascii=False))
        # 站主这条改的就是"图太小"，所以窄屏也钉一层：地图至少铺满屏宽的七成
        check("世界页 %s 面板 375：地图占满一整块（不是半张小图）" % t,
              mm["mapW"] >= 0.7 * 375, "图宽 %dpx（屏宽 375）" % mm["mapW"])
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-world-zones-m.png"))
    mctx.close()
    check("世界页四个面板走一遍没有脚本报错", not errs, "; ".join(errs[:2]) or "干净")
    ctx.close()


def test_dungeon_geo(browser, base):
    """副本详情页的坐标那一层（2026-10-19 接上：入口画在区域图上、首领位置先给数字）。
       盯四件事：① 入口点数 = 这座本有没有那张区域图（没图就是 0 个，不猜位置）；
       ② 那个点就摆在数据给的那组百分比上；③ 首领行里的坐标条数等于成品里这座本的条数；
       ④ 溯源页把这一层的来源与"没凑上多少条"说清楚。"""
    print("\n[6f] 副本入口与本内首领坐标")
    import json
    G = json.load(open(os.path.join(SRC, "data", "dungeon-geo.json"), encoding="utf-8"))
    geo = G.get("dungeons") or {}
    gm = G.get("meta") or {}
    withmap = [k for k, v in geo.items() if (v.get("entry") or {}).get("mapFile")]
    nomap = [k for k, v in geo.items() if (v.get("entry") or {}).get("noMap")]
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:140]))

    def shot(did):
        page.goto(APP_BASE + "/#/dungeon?d=" + did, wait_until="networkidle")
        page.wait_for_timeout(1800)
        # 两张图都是 loading="lazy"：不先滚进视口，naturalWidth 就是 0，断言会打在"没加载"上
        page.evaluate("() => { const x = document.querySelector('.dboss');"
                      "if (x && x.scrollIntoView) x.scrollIntoView({ block: 'center' }); }")
        page.wait_for_timeout(900)
        return page.evaluate("""() => { const c = document.querySelector('.dgeo');
          const dots = [...document.querySelectorAll('.dgeo .zdot')];
          const img = document.querySelector('.dgeo .zcanvas img');
          const bd = [...document.querySelectorAll('.dboss .zdot')];
          const bi = document.querySelector('.dboss .zcanvas img');
          return { has: !!c, dots: dots.length,
            pos: dots.map(x => [x.style.left, x.style.top]),
            kind: dots.map(x => x.dataset.kind),
            bdots: bd.length, brows: document.querySelectorAll('.dboss .zrow').length,
            bkind: [...new Set(bd.map(x => x.dataset.kind))],
            btag: (document.querySelector('.dboss .dmap-tag') || {}).innerText || '',
            bpos: bd.map(x => [x.style.left, x.style.top]),
            bimg: bi ? { w: bi.naturalWidth, h: bi.naturalHeight,
                         ok: bi.complete && bi.naturalWidth > 0,
                         attr: bi.getAttribute('width') + 'x' + bi.getAttribute('height') } : null,
            img: img ? { w: img.naturalWidth, ok: img.complete && img.naturalWidth > 0 } : null,
            line: c ? c.querySelector('.dgeo-line').innerText.replace(/\\s+/g, ' ').trim() : '',
            pos2: [...document.querySelectorAll('.brow .bt .mono')].map(e => e.innerText.trim()),
            over: document.documentElement.scrollWidth - window.innerWidth }; }""")

    check("有入口坐标的本都画出这一节，且入口那一颗点是「entry」这一类",
          len(withmap) == gm["counts"]["entryDungeons"] - len(nomap) and withmap,
          "%d 座有图可画 / %d 座只有坐标 · 数据里入口共 %d 座"
          % (len(withmap), len(nomap), gm["counts"]["entryDungeons"]))
    w0 = withmap[0]
    r = shot(w0)
    e0 = geo[w0]["entry"]
    # 比数值不比字符串：JS 把 8.0 打成 "8"，Python 的 %s 会打成 "8.0"，按字面比必假红
    got_pos = [[float(x.rstrip('%')) for x in one] for one in r["pos"]]
    check("入口那一颗点就摆在数据给的那组百分比上，图也真加载出来了",
          r["has"] and r["dots"] == 1 and got_pos == [[float(e0["x"]), float(e0["y"])]]
          and r["kind"] == ["entry"] and r["img"] and r["img"]["ok"],
          "%s → %s · 图 %s" % (w0, r["pos"], r["img"]))
    check("这一节不横向溢出", r["over"] == 0, "溢出 %d" % r["over"])
    n0 = nomap[0]
    r2 = shot(n0)
    check("本地没有那张区域图的本：一个点都不许多画，改成写明地图编号与坐标",
          r2["has"] and r2["dots"] == 0 and "地图编号" in r2["line"]
          and str(geo[n0]["entry"]["mapId"]) in r2["line"],
          "%s：%s" % (n0, r2["line"][:60]))
    # 首领行里的坐标条数 = 成品里这座本给的那几条
    bd = [k for k, v in geo.items() if (v.get("bossPos") or {})]
    b0 = bd[0]
    r3 = shot(b0)
    want = len(geo[b0]["bossPos"])
    got = len([x for x in r3["pos2"] if x.startswith("本内")])
    check("首领那一行的「本内 x，y」条数等于这座本数据里的条数，一条不多一条不少",
          got == want, "%s：页面 %d 条 / 数据 %d 条" % (b0, got, want))
    # 原来这条是"没有内部底图所以只给数字"，底图接进来以后它变成永远为真的空话，删掉。
    # 该判的事由下面两条管：有 bossMap 的本才许画点、点数等于刷新点数。
    # 2026-10-19 晚：副本内部底图接进来之后（站主拍板"从插件里用"），首领位置从数字变成点。
    # 一个刷新点一颗点，所以点数 = 这座本所有 bossPos 的点数之和；没有 bossMap 的本一颗都不许多画
    mapped = {k: v for k, v in geo.items() if v.get("bossMap") and v.get("bossPos")}
    want_pts = sum(len(p) for v in mapped.values() for p in v["bossPos"].values())
    check("数据侧：有内部底图可画点的本 %d 座，点数合计 %d" % (len(mapped), want_pts),
          len(mapped) == (gm.get("counts") or {}).get("bossMapped"),
          "数据 %d 座 / meta.counts.bossMapped %s"
          % (len(mapped), (gm.get("counts") or {}).get("bossMapped")))
    b1 = sorted(mapped)[0]
    r4 = shot(b1)
    want_b = sum(len(x) for x in geo[b1]["bossPos"].values())
    check("副本详情页「首领在哪个位置」一颗点=一个刷新点，且底图真加载出来了",
          r4["bdots"] == want_b and r4["brows"] == want_b and r4["bimg"] and r4["bimg"]["ok"],
          "%s：点 %d / 行 %d / 数据 %d 个点" % (b1, r4["bdots"], r4["brows"], want_b))
    check("首领那颗点用的是自己的颜色（不跟稀有那颗撞色）",
          r4["bkind"] == ["boss"], "类型 %s" % (r4["bkind"] or "无"))
    check("这一节也不横向溢出", r4["over"] == 0, "溢出 %d" % r4["over"])
    # 预留框的宽高必须等于那张图的真实像素：游戏截图那批是 512² 方的、作者自绘那批是 640×427 横的，
    # 页面写死一个比例就会在图加载完时把整块往下推（2026-10-19 实测到的，不是假设）
    drawn = sorted(k for k, v in mapped.items() if v.get("bossMapKind") == "addon-drawn")
    d0 = drawn[0] if drawn else sorted(mapped)[0]
    r5 = shot(d0)
    bi = r5["bimg"] or {}
    check("首领底图预留的宽高就是那张图的真实像素（横图方图不写死同一个比例）",
          bi.get("attr") == "%dx%d" % (bi.get("w", 0), bi.get("h", 0))
          and geo[d0].get("bossMapRatio") == str(bi.get("attr", "")).replace("x", "/"),
          "%s（%s）：预留 %s · 真实 %sx%s · 数据写 %s"
          % (d0, geo[d0].get("bossMapKind"), bi.get("attr"), bi.get("w"), bi.get("h"),
             geo[d0].get("bossMapRatio")))
    # 2026-10-19 站主拍板：作者自绘的那几张要就地标一句（AGENTS.md 素材那一条的窄例外）。
    # 两条一起看才有效：该标的标了，不该标的不许冒出来——否则又变回满站挂角标。
    check("自绘示意图那一类在标题旁就地标一句，话里说清不是游戏里的图",
          bool(drawn) and "示意图" in r5["btag"] and "不是游戏里" in r5["btag"],
          "%s：%s" % (d0, r5["btag"][:40] or "没标"))
    check("游戏内地图截图那一类不标（别把提醒做成第二个角标）",
          geo[b1].get("bossMapKind") == "game-capture" and not r4["btag"],
          "%s（%s）：%s" % (b1, geo[b1].get("bossMapKind"), r4["btag"] or "没标，对的"))
    page.goto(APP_BASE + "/#/provenance", wait_until="networkidle")
    page.wait_for_timeout(1500)
    # 取"哪一段讲了这一层"要按整段取，别按句子切——三个数分在两句里，按句切就会把数切没了
    pv = page.evaluate("""() => [...document.querySelectorAll('#main .card p.dim')]
        .map(e => e.innerText.replace(/\\s+/g, ' ').trim())
        .filter(x => x.indexOf('入口') >= 0 && x.indexOf('首领位置') >= 0).join(' | ')""")
    check("溯源页说清这一层从哪来、有多少、没凑上的多少条",
          "DungeonsForever" in pv and str(gm["counts"]["entryDungeons"]) in pv
          and str(gm["counts"]["bossRows"]) in pv and str(gm["counts"]["droppedRows"]) in pv,
          pv[:120] or "溯源页没有这一段")
    # 底图这一层是 2026-10-19 站主拍板才拿进来的，和坐标不是同一家插件，必须另起一段写明来源。
    # 两类要分开交代：一类是插件作者从游戏里截下来的官方副本地图，一类是作者自绘的示意图——
    # 混着写成"插件作者画的图"是把官方的图说成别人画的，也是把别人的画说成没版权。
    pm = page.evaluate("""() => [...document.querySelectorAll('#main .card p.dim')]
        .map(e => e.innerText.replace(/\\s+/g, ' ').trim())
        .filter(x => x.indexOf('底图') >= 0).join(' | ')""")
    mc = gm["counts"]
    check("溯源页另起一段把两类底图分开交代，两类座数加起来等于能画点的座数",
          "游戏里那张副本地图" in pm and "插件作者自绘" in pm
          and ("%d 座用的是游戏里" % mc["bossMapGame"]) in pm
          and ("%d 座（" % mc["bossMapDrawn"]) in pm
          and mc["bossMapGame"] + mc["bossMapDrawn"] == mc["bossMapped"],
          "游戏截图 %s + 作者自绘 %s / 能画点 %s ｜ %s"
          % (mc["bossMapGame"], mc["bossMapDrawn"], mc["bossMapped"], pm[:60]))
    check("溯源页不许留着「没拿图」这种与现状矛盾的话",
          "都没拿" not in pm and "没拿图" not in pm,
          "干净" if "都没拿" not in pm else pm[:80])
    # 红线：这一层整份不许出现概率措辞（数据侧 build-data 也卡了一道，这里看渲染出来的）
    check("渲染出来的入口行与首领坐标行里都不许出现百分号（防掉率混进这一层）",
          "%" not in r3["line"] + " ".join(r3["pos2"]),
          "干净" if "%" not in r3["line"] + " ".join(r3["pos2"]) else "有百分号")
    mctx = browser.new_context(viewport={"width": 375, "height": 812})
    mp = mctx.new_page()
    mp.goto(APP_BASE + "/#/dungeon?d=" + w0, wait_until="networkidle")
    mp.wait_for_timeout(1800)
    mm = mp.evaluate("""() => ({over: document.documentElement.scrollWidth - window.innerWidth,
      mapW: (document.querySelector('.dgeo .zbig') || { offsetWidth: 0 }).offsetWidth,
      dot: (() => { const d = document.querySelector('.dgeo .zdot'); if (!d) return null;
        const r = d.getBoundingClientRect(); return r.width >= 30; })()})""")
    check("375 上入口那张图占满一整块、点够大、整页不横溢",
          mm["over"] == 0 and mm["mapW"] >= 0.7 * 375 and mm["dot"] is not False,
          json.dumps(mm, ensure_ascii=False))
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-dungeon-geo-m.png"))
    mctx.close()
    check("副本坐标这一层走一遍没有脚本报错", not errs, "; ".join(errs[:2]) or "干净")
    ctx.close()


def test_legacy_app(browser, base):
    """新站传承页（2026-10-18 视觉与交互重做，站主定"只用我们自己采到的那份数据"）。
       盯四件事：① 界面上每个数与每个名字都等于 legacy.json 现算的结果，一个都不手抄；
       ② 三条新交互真的动——点专长出详情、点前置跳过去、六组挑战折叠与搜索自动展开；
       ③ 换树不许把上一棵的选中态留在空栏里；
       ④ 桌面与 375 都不横溢、点击目标够大、锚点走站内路由。"""
    print("\n[6d] 新站传承页")
    import json
    L = json.load(open(os.path.join(SRC, "data", "legacy.json"), encoding="utf-8"))
    trees = L.get("trees") or []
    perks = {p["id"]: p for p in (L.get("perks") or [])}
    groups = L.get("challenges") or []
    all_items = [x for g in groups for x in (g.get("items") or [])]
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:140]))
    page.goto(APP_BASE + "/#/legacy", wait_until="networkidle")
    page.wait_for_timeout(2400)
    check("新站传承页可加载且无脚本报错", not errs, "; ".join(errs[:2]) or "干净")

    def known(t):
        return len([s for s in t["slots"] if not s.get("empty") and not s.get("unknown")])

    def unk(t):
        return len([s for s in t["slots"] if s.get("unknown")])

    # ---- ① 三棵树胶囊与格子：全部对着 legacy.json 现算 ----
    tabs = page.evaluate("() => [...document.querySelectorAll('.lge-tabs [data-t]')].map(e => {"
                         "const c = e.cloneNode(true);"
                         "return {t: e.dataset.t, name: (e.querySelector('b')||{}).textContent,"
                         " mono: [...e.querySelectorAll('.mono')].map(x => x.textContent.trim()),"
                         " on: e.classList.contains('on')}; })")
    want_tabs = [t["id"] for t in trees]
    check("三棵树的胶囊切换按数据列，默认选中第一棵",
          [x["t"] for x in tabs] == want_tabs and len(tabs) == 3 and tabs[0]["on"]
          and not any(x["on"] for x in tabs[1:]),
          "%s（数据 %s）" % ([x["t"] for x in tabs], want_tabs))
    bad_counts = []
    for x, t in zip(tabs, trees):
        if x["mono"] != ["%d 格" % known(t), "· 未公开 %d" % unk(t)]:
            bad_counts.append("%s 画 %s，数据是 %d 格 / %d 未公开" % (x["name"], x["mono"], known(t), unk(t)))
    check("胶囊上那两个数是数据算出来的（格数与未公开数），不是手抄",
          not bad_counts, "；".join(bad_counts) or "三棵都对得上")

    def grid_state():
        return page.evaluate("""() => { const t = document.querySelector('.lge-cells');
          const cells = [...document.querySelectorAll('#ltree .lslot')];
          return {tabs: document.querySelectorAll('.lge-tabs [data-t]').length,
            rails: [...document.querySelectorAll('.lge-rail')].map(e => e.innerText.trim()),
            rows: document.querySelectorAll('.lge-rowwrap').length,
            cols: t ? getComputedStyle(t).gridTemplateColumns.split(' ').length : 0,
            cells: cells.length,
            perk: cells.filter(e => e.tagName === 'BUTTON').length,
            unk: cells.filter(e => e.classList.contains('unk')).length,
            none: cells.filter(e => e.classList.contains('none')).length,
            names: cells.filter(e => e.tagName === 'BUTTON').map(e => (e.querySelector('.nm')||{}).innerText.trim()),
            tags: cells.filter(e => e.querySelector('.lge-tag')).length,
            h2: (document.querySelector('#ltree h2')||{}).innerText.replace(/\\s+/g,' ').trim()}; }""")

    g = grid_state()
    t0 = trees[0]
    # 注意"未公开"的格子也带 perk 号（形如 unknown-113508，不在这 21 个专长里），
    # 所以挑真专长必须同时排掉 empty 与 unknown——只判 perk 存在会把它们算进来（第一版就崩在这）。
    named = lambda t: [s for s in t["slots"] if s.get("perk") and not s.get("empty") and not s.get("unknown")]
    want_names = [perks[s["perk"]]["nameCn"] for s in
                  sorted(named(t0), key=lambda s: (s["row"], s["col"]))]
    check("格子按客户端坐标铺满 rows × cols，排号一行一个",
          g["rows"] == t0["rows"] and g["cells"] == t0["rows"] * t0["cols"]
          and g["cols"] == t0["cols"] and g["rails"] == ["第%d排" % (i + 1) for i in range(t0["rows"])],
          "%d 排 × %d 列 = %d 格（数据 %d × %d），排号 %s" % (g["rows"], g["cols"], g["cells"],
                                                        t0["rows"], t0["cols"], g["rails"]))
    check("三种格子各是各的数：专长 / 未公开 / 这一排没这个位置",
          g["perk"] == known(t0) and g["unk"] == unk(t0)
          and g["perk"] + g["unk"] + g["none"] == t0["rows"] * t0["cols"],
          "专长 %d / 未公开 %d / 空 %d（数据 %d / %d）" % (g["perk"], g["unk"], g["none"],
                                                      known(t0), unk(t0)))
    check("格子里的专长名与顺序等于这份数据按坐标排出来的",
          g["names"] == want_names, "页面 %s ／ 数据 %s" % (g["names"], want_names))
    pre_n = len([p for p in perks.values() if p["treeId"] == t0["id"] and p.get("prerequisiteCn")])
    check("有前置的格子都挂了角标，数量与数据一致", g["tags"] == pre_n,
          "画 %d 个，数据里这一棵有前置的 %d 个" % (g["tags"], pre_n))

    # ---- ② 详情栏：没选时不空，选了说这个专长 ----
    det0 = page.evaluate("""() => ({legend: document.querySelectorAll('.lge-legend li').length,
      read: [...document.querySelectorAll('#ldet .lge-read > span')].map(e => e.innerText.replace(/\\s+/g,' ').trim()),
      perk: !!document.querySelector('.lge-perk')})""")
    t0perks = [p for p in perks.values() if p["treeId"] == t0["id"]]
    # 读数里 <b>数</b>标签 是紧挨着写的（间距靠 CSS 的 gap），innerText 里不会有空格，
    # 所以比的是"去掉所有空白之后一样"，不是比字符串相等——否则这条会假红。
    want_read = ["%d个专长" % len(t0perks),
                 "%d层最多可点" % sum(p.get("maxRank") or 0 for p in t0perks),
                 "%d个要先点前置" % len([p for p in t0perks if p.get("prerequisiteCn")])]
    squash = lambda xs: [re.sub(r"\s+", "", x) for x in xs]
    check("没选专长时详情栏仍有内容（图例三条 + 这一棵的三行读数）",
          det0["legend"] == 3 and not det0["perk"] and squash(det0["read"]) == squash(want_read),
          "读数 %s ／ 数据 %s" % (det0["read"], want_read))
    withpre = [p for p in t0perks if p.get("prerequisiteCn")]
    pid = withpre[0]["id"]
    page.evaluate("() => document.querySelector('[data-perk=\"%s\"]').click()" % pid)
    page.wait_for_timeout(700)
    d = page.evaluate("""() => { const c = document.querySelector('.lge-perk'); if (!c) return null;
      return {name: (c.querySelector('h2')||{}).innerText.trim(),
        dots: c.querySelectorAll('.lge-ranks .rd').length,
        rank: (c.querySelector('.lge-ranks .mono')||{}).innerText.trim(),
        meta: [...c.querySelectorAll('.lmeta > span')].map(e => e.innerText.replace(/\\s+/g,' ').trim()),
        jump: (c.querySelector('.lge-jump')||{}).innerText,
        on: document.querySelectorAll('#ltree .lslot.on').length,
        bad: [...c.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0).length}; }""")
    p0 = perks[pid]
    check("点一个专长：详情说的名字、层数、位置、所属树全部对得上数据",
          d and d["name"] == p0["nameCn"] and d["rank"] == "最多 %d 层" % p0["maxRank"]
          and d["dots"] == min(p0["maxRank"], 8)
          and ("位置：第 %d 排第 %d 列" % (p0["row"] + 1, p0["col"] + 1)) in d["meta"]
          and ("属于：%s" % p0["treeCn"]) in d["meta"] and d["on"] == 1 and d["bad"] == 0,
          json.dumps(d, ensure_ascii=False))
    pre_name = d.get("jump") or ""
    page.evaluate("() => document.querySelector('.lge-jump').click()")
    page.wait_for_timeout(700)
    d2 = page.evaluate("""() => { const c = document.querySelector('.lge-perk');
      return c ? {name: (c.querySelector('h2')||{}).innerText.trim(),
        on: [...document.querySelectorAll('#ltree .lslot.on')].map(e => e.dataset.perk),
        tree: (document.querySelector('.lge-tab.on b')||{}).innerText.trim()} : null; }""")
    hit = [p for p in perks.values() if p["nameCn"] == pre_name]
    check("点前置那个名字：直接选中前置专长，树也跟着切过去",
          d2 and hit and d2["name"] == pre_name and d2["on"] == [hit[0]["id"]]
          and d2["tree"] == hit[0]["treeCn"],
          "点的是「%s」→ %s" % (pre_name, json.dumps(d2, ensure_ascii=False)))

    # ---- ③ 换树清选中，别把上一棵的选中态留在空栏里 ----
    t1 = trees[1]
    page.evaluate("() => document.querySelector('[data-t=\"%s\"]').click()" % t1["id"])
    page.wait_for_timeout(700)
    sw = page.evaluate("""() => ({on: document.querySelectorAll('#ltree .lslot.on').length,
      perk: !!document.querySelector('.lge-perk'),
      names: [...document.querySelectorAll('#ltree BUTTON.lslot .nm')].map(e => e.innerText.trim()),
      cells: document.querySelectorAll('#ltree .lslot').length})""")
    want1 = [perks[s["perk"]]["nameCn"] for s in
             sorted(named(t1), key=lambda s: (s["row"], s["col"]))]
    check("换一棵树：格子与名字跟着换，上一棵的选中态清掉、详情回到概览",
          sw["on"] == 0 and not sw["perk"] and sw["names"] == want1
          and sw["cells"] == t1["rows"] * t1["cols"],
          "%d 格 / 选中 %d / %s" % (sw["cells"], sw["on"], sw["names"][:3]))

    # ---- ④ 六组挑战：默认只开第一组，搜索自动展开，内容一条不少 ----
    ch = page.evaluate("""() => ({blocks: document.querySelectorAll('#lch .lchgrp').length,
      open: [...document.querySelectorAll('#lch [aria-expanded]')].filter(e => e.getAttribute('aria-expanded') === 'true').length,
      vis: [...document.querySelectorAll('#lch tbody tr')].filter(r => r.offsetParent).length,
      all: document.querySelectorAll('#lch tbody tr').length,
      heads: [...document.querySelectorAll('.lchhead > b')].map(e => e.innerText.trim()),
      sums: [...document.querySelectorAll('.lchhead > .mono')].map(e => e.innerText.replace(/\\s+/g,' ').trim()),
      counter: (document.querySelector('.field .mono')||{}).innerText.trim()})""")
    g0 = groups[0]
    want_sums = ["%d 项 · 合计 %d 点" % (len(g["items"]), sum(x.get("points") or 0 for x in g["items"]))
                 for g in groups]
    check("六组挑战的组头写着项数与合计点数，数全部来自明细",
          ch["blocks"] == len(groups) == 6 and ch["heads"] == [g["nameCn"] for g in groups]
          and ch["sums"] == want_sums, "；".join(ch["sums"]) + " ／ 数据 " + "；".join(want_sums))
    check("默认只展开第一组，但 66 行内容一条不少（折叠是藏起来不是删掉）",
          ch["open"] == 1 and ch["vis"] == len(g0["items"]) and ch["all"] == len(all_items)
          and ch["counter"] == "%d / %d 项" % (len(all_items), len(all_items)),
          "展开 %d 组，可见 %d 行 / DOM %d 行（数据 %d 项）" % (ch["open"], ch["vis"], ch["all"], len(all_items)))
    page.evaluate("() => document.querySelectorAll('.lchhead')[1].click()")
    page.wait_for_timeout(500)
    ch2 = page.evaluate("""() => ({open: [...document.querySelectorAll('#lch [aria-expanded]')]
        .filter(e => e.getAttribute('aria-expanded') === 'true').length,
      vis: [...document.querySelectorAll('#lch tbody tr')].filter(r => r.offsetParent).length})""")
    check("点第二组的组头能展开，可见行数跟着加上去",
          ch2["open"] == 2 and ch2["vis"] == len(g0["items"]) + len(groups[1]["items"]),
          "展开 %d 组 / 可见 %d 行（前两组 %d + %d）"
          % (ch2["open"], ch2["vis"], len(g0["items"]), len(groups[1]["items"])))
    k = "25级"
    hits = [x for x in all_items if k in ((x.get("nameCn") or "") + " " + (x.get("requirement") or "")
            + " " + (x.get("sub") or "") + " " + (x.get("group") or ""))]
    page.fill(".field input[type=search]", k)
    page.wait_for_timeout(900)
    cs = page.evaluate("""() => ({blocks: document.querySelectorAll('#lch .lchgrp').length,
      open: [...document.querySelectorAll('#lch [aria-expanded]')].filter(e => e.getAttribute('aria-expanded') === 'true').length,
      vis: [...document.querySelectorAll('#lch tbody tr')].filter(r => r.offsetParent).length,
      counter: (document.querySelector('.field .mono')||{}).innerText.trim(),
      hl: document.querySelectorAll('#lch mark, #lch .hl').length})""")
    check("搜索时命中的组自动展开（折叠不会把搜索结果藏起来），计数按命中走",
          cs["blocks"] >= 1 and cs["open"] == cs["blocks"] and cs["vis"] == len(hits)
          and cs["counter"] == "%d / %d 项" % (len(hits), len(all_items)),
          "命中 %d 组 / 展开 %d / 可见 %d 行（数据 %d 条含「%s」）" % (cs["blocks"], cs["open"], cs["vis"], len(hits), k))
    page.fill(".field input[type=search]", "")
    page.wait_for_timeout(700)
    # 清空搜索后应该回到"用户自己点开的那两组"（第一组默认开 + 上面手动开的第二组），
    # 不是停在搜索时的全部展开。期望值写 2 不写 1：这一步之前确实手动展开过一组，
    # 要求搜索把用户自己的展开状态也清掉不是这一轮定的行为。
    back = page.evaluate("() => ({open: [...document.querySelectorAll('#lch [aria-expanded]')]"
                         ".filter(e => e.getAttribute('aria-expanded') === 'true').length,"
                         " blocks: document.querySelectorAll('#lch .lchgrp').length})")
    check("清空搜索回到用户自己的展开状态，不是停在全部展开；六组都回来了",
          back == {"open": 2, "blocks": len(groups)},
          "%s（应 %d 组展开 / %d 组都在）" % (back, 2, len(groups)))

    # ---- ⑤ 锚点走站内路由（首页那批死链就是栽在裸 #id 上），点一下真的滚 ----
    anch = page.evaluate("""() => [...document.querySelectorAll('.lge-anchor a')].map(a => ({
      t: a.innerText.trim(), h: a.getAttribute('href')}))""")
    check("页内三个锚点走站内路由地址，不写裸 #id",
          [a["t"] for a in anch] == ["传承树", "传承挑战", "进度奖励"]
          and all(a["h"].startswith("#/legacy?to=") for a in anch),
          json.dumps(anch, ensure_ascii=False))
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    page.evaluate("() => document.querySelectorAll('.lge-anchor a')[2].click()")
    page.wait_for_timeout(1200)
    check("点锚点真的滚到那一段",
          page.evaluate("() => { const r = document.getElementById('lgr').getBoundingClientRect();"
                        "return window.scrollY > 400 && r.top < window.innerHeight; }"))

    # ---- ⑥ 两档视口的几何与红线 ----
    body = page.evaluate("() => document.querySelector('#main').innerText")
    check("这一页不出现百分比与掉率措辞（红线）",
          not re.search(r"\d+\s*%|掉率", body), "干净")
    page.screenshot(path=os.path.join(SHOT_DIR, "app-legacy.png"), full_page=True)
    ctx.close()
    mctx = browser.new_context(viewport={"width": 375, "height": 812})
    mp = mctx.new_page()
    mp.goto(APP_BASE + "/#/legacy", wait_until="networkidle")
    mp.wait_for_timeout(2200)
    mm = mp.evaluate("""() => ({over: document.documentElement.scrollWidth - window.innerWidth,
      cells: getComputedStyle(document.querySelector('.lge-cells')).gridTemplateColumns.split(' ').length,
      wrap: getComputedStyle(document.querySelector('.ltreewrap')).gridTemplateColumns.split(' ').length,
      small: [...document.querySelectorAll('.lge-tab, .lchhead, #ltree .lslot BUTTON, .lge-jump')]
        .filter(e => { const r = e.getBoundingClientRect();
          return r.width > 0 && Math.min(r.width, r.height) < 44; }).length,
      cut: [...document.querySelectorAll('#ltree .lslot')].some(e => e.getBoundingClientRect().right > window.innerWidth + 1)})""")
    check("传承页 375：整页不横溢、树仍按四列摆、详情叠到下面、没有格子被切掉",
          mm["over"] == 0 and mm["cells"] == 4 and mm["wrap"] == 1 and not mm["cut"],
          json.dumps(mm, ensure_ascii=False))
    check("传承页 375：胶囊、组头、专长格、前置链接都够 44px 点击区",
          mm["small"] == 0, "%d 个不够 44px" % mm["small"])
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-legacy-m.png"), full_page=True)
    mctx.close()


# 装备属性行的独立解析（2026-10-19 护甲漏算之后钉在这里）。
# 这份与 app/src/lib/item-stats.js 是各写各的两份实现、互不引用：页面那份改了，
# 门禁这份还能把它兜回来。当初正是两边抄同一条正则，才让 525 这个错数一起 PASS 了半个月。
BASE_ARMOR_RE = (r"^([0-9]+)\s*点护甲$", r"^([0-9]+)\s*护甲$", r"^护甲值\s*([0-9]+)$")
NOT_BASE_ARMOR_RE = (r"^[+-]", r"护甲（[0-9]+/[0-9]+）$",
                     u"(加成|装备|使用|套装|击中时可能|命中率|触发|机会|持续|需要|附魔|%)")
STAT_RE = r"^\+\s*([0-9]+)\s*(力量|敏捷|耐力|智力|精神)$"
SUM_ORDER = [u"力量", u"敏捷", u"耐力", u"智力", u"精神", u"护甲"]


def stat_totals(det, doll):
    """照 items-detail 的原始属性行算一遍这套装备的属性合计。
       返回 (合计, 带护甲却没落进已知档的行, 计入的基础护甲行数, 加成与效果句行数)。
       第三种返回值是留给人的读数，第四种连同第二种用来兜"库里又冒了一种新写法"。"""
    tot = {}
    offlist = []
    base_rows = 0
    other_rows = 0
    for c in doll:
        for l in (det.get(str(c["item"]), {}) or {}).get("st") or []:
            s = str(l).strip()
            m = re.match(STAT_RE, s)
            if m:
                tot[m.group(2)] = tot.get(m.group(2), 0) + int(m.group(1))
                continue
            hit = None
            for pat in BASE_ARMOR_RE:
                m = re.match(pat, s)
                if m:
                    hit = int(m.group(1))
                    break
            if hit is not None:
                tot[u"护甲"] = tot.get(u"护甲", 0) + hit
                base_rows += 1
                continue
            if u"护甲" in s:
                other_rows += 1
                if not any(re.search(p, s) for p in NOT_BASE_ARMOR_RE):
                    offlist.append(u"%s #%s：%s" % (c["slot"], c["item"], s))
    return tot, offlist, base_rows, other_rows


def sum_expect(tot):
    return ["%s%s" % (tot[k], k) for k in SUM_ORDER if k in tot]


def test_bis(browser, base):
    """配装页（2026-10-16 站主拍板走 C 方案）。盯四件事：
       ① 界面上的数与名字全部来自我们自己的数据（bis.json 的顺序 + items.json 的名字）；
       ② 点部位换备选、切阵营换装备这两条交互真的动；
       ③ 红线：不许出现百分比与掉率措辞、口径那一句必须在；
       ④ 桌面与 375 都不横溢。"""
    print("\n[6b] 配装页")
    import json

    POP_JS = """() => { const p = document.querySelector('.pzpop');
      if (!p) return null; const a = document.querySelector('.pzcell.on');
      const pb = p.getBoundingClientRect(), ab = a.getBoundingClientRect();
      return { title: (p.querySelector('h3')||{}).innerText.replace(/\\s+/g,' ').trim(),
        rows: p.querySelectorAll('#pzalts tbody tr').length,
        first: (p.querySelector('#pzalts tbody tr .nm')||{}).innerText || '',
        src: (p.querySelector('#pzalts tbody tr .w-tail')||{}).innerText || '',
        thAbove: Math.round(p.querySelector('thead th').getBoundingClientRect().top)
                 < Math.round(p.querySelector('tbody tr').getBoundingClientRect().top),
        near: Math.round(pb.left - ab.right), behind: pb.left > ab.left,
        mask: !!document.querySelector('.pzmask'),
        bg: getComputedStyle(p).backgroundColor,
        go: !!p.querySelector('.pzgo'),
        inView: pb.top >= 0 && pb.bottom <= innerHeight + 1 && pb.left >= 0 && pb.right <= innerWidth + 1 }; }"""
    if not app_up(browser):
        return
    bis = json.load(open(os.path.join(SRC, "data", "bis.json"), encoding="utf-8"))
    items = json.load(open(os.path.join(SRC, "data", "items.json"), encoding="utf-8"))["items"]
    by_id = {x["id"]: x for x in items}
    sets = bis["sets"]
    w = [s for s in sets if s["cls"] == "warrior"][0]
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.on("console", lambda m: errs.append(m.text[:120]) if m.type == "error" else None)
    page.goto(APP_BASE + "/#/bis", wait_until="networkidle")
    page.wait_for_timeout(2200)
    r = page.evaluate("""() => ({
      h1: (document.querySelector('#main h1')||{}).innerText || '',
      cells: document.querySelectorAll('.pzcell').length,
      cellNames: [...document.querySelectorAll('.pzcell .pzname')].map(x => x.textContent.trim()),
      pop: !!document.querySelector('.pzpop'),
      reads: [...document.querySelectorAll('.pz-read span')].map(x => x.innerText.replace(/\\s+/g,' ')),
      note: (document.querySelector('#main .note')||{}).innerText || '',
      over: document.documentElement.scrollWidth - innerWidth,
      body: document.querySelector('#main').innerText })""")
    check("配装页可访问且没有脚本报错", not errs, "; ".join(errs[:2]) or "干净")
    check("配装页一个 H1 且写着等级段", r["h1"].startswith(u"30 级配装"), r["h1"])
    check("纸娃娃格数等于数据里这一套的格数", r["cells"] == len(w["doll"]["alliance"]),
          "%d 格（数据 %d）" % (r["cells"], len(w["doll"]["alliance"])))
    # 纸娃娃是三栏摆的，DOM 顺序（左列→下排→右列）不等于数据顺序，
    # 所以比的是「部位 + 序号 → 装备名」这一组对应关系，不是列表顺序。
    cell_pairs = page.evaluate("""() => [...document.querySelectorAll('.pzcell')].map(c => {
      const s = c.querySelector('.pzslot'), n = c.querySelector('.pzname');
      return [(s ? s.textContent : '').trim(), (n ? n.textContent : '').trim()]; })""")
    want_names = [[c["slot"] + ("" if c["cell"] < 2 else " · %d" % c["cell"]), by_id[c["item"]]["name"]]
                  for c in w["doll"]["alliance"]]
    bad = [x for x in cell_pairs if x not in want_names]
    check("纸娃娃上每件装备的名字都取自本站名录（不是抄参考站的写法）",
          len(cell_pairs) == len(want_names) and not bad,
          "对不上：%s" % bad[:3] if bad else "%d 格全对" % len(cell_pairs))
    check("进页面时备选 popover 不自己弹出来", not r["pop"])
    check("一览表按数据里的部位逐行列出",
          page.evaluate("() => document.querySelectorAll('#pzover tbody tr').length") == len(w["doll"]["alliance"]),
          "%d 行" % page.evaluate("() => document.querySelectorAll('#pzover tbody tr').length"))
    # 站主 2026-10-17 改口径：点装备用 popover 看备选（不是 modal，不挡页面）
    head_rows = w["alts"]["alliance"]["head"]
    page.click(".pzcol:first-child .pzcell")
    page.wait_for_timeout(600)
    pop = page.evaluate(POP_JS)
    check("点纸娃娃那一格会弹出这个部位的备选（条数等于数据）",
          pop and pop["rows"] == len(head_rows), "%s" % (pop and pop["rows"]))
    check("备选第一件就是这套选的那件，且来源那一格填得出来",
          pop and pop["first"] == by_id[head_rows[0]]["name"] and len(pop["src"]) > 0,
          "%s ｜ 来源：%s" % (pop and pop["first"], pop and pop["src"]))
    check("popover 贴着点的那一格弹（在它右边，不居中挡整屏）",
          pop and pop["near"] >= 0 and pop["behind"], "左缘距格子右缘 %spx" % (pop and pop["near"]))
    check("popover 是非模态的：没有遮罩，底色不透明",
          pop and not pop["mask"] and pop["bg"] not in ("rgba(0, 0, 0, 0)", "transparent"),
          "底色 %s / 遮罩 %s" % (pop and pop["bg"], pop and pop["mask"]))
    check("popover 里表头在第一行上面（吸附的 top 不能照抄全站顶栏高度）", pop and pop["thAbove"])
    check("popover 完整落在视口内，且每行有去物品库的入口", pop and pop["inView"] and pop["go"])
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    check("按 ESC 收掉 popover", not page.evaluate("() => !!document.querySelector('.pzpop')"))
    page.click(".pzcol:first-child .pzcell:nth-child(2)")
    page.wait_for_timeout(450)
    page.mouse.click(1300, 950)
    page.wait_for_timeout(400)
    check("点页面别处也收掉 popover", not page.evaluate("() => !!document.querySelector('.pzpop')"))
    check("读数那五个数是从数据算出来的",
          r["reads"][0].startswith(str(bis["meta"]["counts"]["sets"]))
          and r["reads"][3].split(u"件")[0].strip() == str(bis["meta"]["counts"]["items"]),
          " / ".join(r["reads"]))
    check("红线口径那一句在页面上（本站整理、不是官方结论、没做模拟计算）",
          u"不是官方结论" in r["note"] and u"没做模拟计算" in r["note"])
    pct = re.findall(r"\d+(?:\.\d+)?\s*%|掉率", r["body"])
    check("配装页不出现百分比与掉率措辞（红线）", not pct, str(pct[:4]))
    check("配装页正文没有面向开发的词", not dev_word_hits(r["body"]), "干净")
    check("配装页桌面不横向溢出", r["over"] <= 1, "溢出 %dpx" % r["over"])
    # 换一个部位：popover 跟着换内容（不是新开一层）
    page.click(".pzcol:first-child .pzcell:nth-child(3)")
    page.wait_for_timeout(600)
    a = page.evaluate("() => ({t: (document.querySelector('.pzpop h3')||{}).innerText.replace(/\\s+/g,' ').trim(),"
                      " first: (document.querySelector('#pzalts tbody tr .nm')||{}).innerText})")
    sh = w["alts"]["alliance"].get("shoulder") or []
    check("点别的部位，popover 换成那个部位的备选（肩部）",
          a["t"].startswith(u"肩部") and sh and a["first"] == by_id[sh[0]]["name"], json.dumps(a, ensure_ascii=False))
    # 换阵营要把 popover 关掉（anchor 与内容都换了，浮层不该停在旧格子旁边）
    page.click(".pz-fac .pick:last-child")
    page.wait_for_timeout(800)
    check("换阵营时 popover 自动关掉", not page.evaluate("() => !!document.querySelector('.pzpop')"))
    hz = page.evaluate("() => [...document.querySelectorAll('.pzcell .pzname')].map(x => x.textContent.trim())")
    diff = [i for i, (x, y) in enumerate(zip(r["cellNames"], hz)) if x != y]
    data_diff = [i for i, (x, y) in enumerate(zip(w["doll"]["alliance"], w["doll"]["horde"])) if x["item"] != y["item"]]
    check("切阵营会换装备，且换掉的部位与数据里不一致的部位数一致",
          len(diff) > 0 and len(diff) == len(data_diff), "界面 %d 处 / 数据 %d 处" % (len(diff), len(data_diff)))
    # 10-17 站主实拍后补的三样：职业条要带职业图标、阵营要带徽记、纸娃娃要照参考站那样
    # 左右两列夹中间一块。这三条都是"少了没人报错、只能看图"的东西，所以钉成断言。
    page.click(".pz-fac .pick:first-child")   # 切回联盟，下面按联盟那一版算期望
    page.wait_for_timeout(800)
    ic = page.evaluate("""() => {
      const ok = (b) => { const i = b.querySelector('img'); return !!i && i.complete && i.naturalWidth > 0; };
      return {
        rail: [...document.querySelectorAll('.pzrail .pztab')].map(b => ({ t: b.innerText.replace(/\\s+/g,' ').trim(), img: ok(b) })),
        fac: [...document.querySelectorAll('.pz-fac .pick')].map(b => ({ t: b.innerText.trim(), img: ok(b) })),
        cols: [document.querySelectorAll('.pzcol')[0].querySelectorAll('.pzcell').length,
               document.querySelectorAll('.pzcol')[1].querySelectorAll('.pzcell').length,
               document.querySelectorAll('.pzrow .pzcell').length],
        art: getComputedStyle(document.querySelector('.pzart')).backgroundImage.indexOf('url(') >= 0,
        sum: [...document.querySelectorAll('.pzsum-i span')].map(x => x.innerText.replace(/\\s+/g,' ').trim()) }; }""")
    check("职业条九格齐全且每格都画出职业图标",
          len(ic["rail"]) == bis["meta"]["counts"]["classes"] and all(x["img"] for x in ic["rail"]),
          "%d 格，缺图 %s" % (len(ic["rail"]), [x["t"] for x in ic["rail"] if not x["img"]] or "无"))
    check("联盟与部落两个按钮各带本阵营徽记（用本地 art/factions，不热链）",
          [x["t"] for x in ic["fac"]] == [u"联盟", u"部落"] and all(x["img"] for x in ic["fac"]),
          json.dumps(ic["fac"], ensure_ascii=False))
    LEFT = [u"头部", u"项链", u"肩部", u"背部", u"胸部", u"手腕"]
    BOTTOM = [u"主手", u"副手", u"远程", u"圣物"]
    dl = w["doll"]["alliance"]
    want_cols = [len([c for c in dl if c["slot"] in LEFT]),
                 len([c for c in dl if c["slot"] not in LEFT and c["slot"] not in BOTTOM]),
                 len([c for c in dl if c["slot"] in BOTTOM])]
    check("纸娃娃三栏的部位归属与数据一致（左 %d / 右 %d / 下 %d）" % tuple(want_cols),
          ic["cols"] == want_cols, "界面 %s" % ic["cols"])
    check("中间那一块铺了职业原画（不是空框，也不拿别的图冒充人物）", ic["art"])
    # 属性合计：门禁这边独立按同一份 items-detail 解析一遍，跟界面上那排数比。
    # 2026-10-19 修：装备的基础护甲在库里有三种写法（"84点护甲" / "90 护甲" / "护甲值 74"），
    # 原来这里和页面各抄了同一条只认两种半的正则，把 #9509 的 "90 护甲" 漏掉——
    # 两边一致只证明一致，525 是错的，逐件相加应为 615。现在解析挪到 stat_totals 里
    # 按写法枚举，并加一条落档断言：以后库里冒出第四种写法，这里直接红，不会静默少算。
    det = json.load(open(os.path.join(SRC, "data", "items-detail.json"), encoding="utf-8"))["items"]
    tot, offlist, base_rows, other_rows = stat_totals(det, dl)
    check("这一套每条带护甲的行都落进了已知写法（新写法不许静默漏算）",
          not offlist, "计入基础护甲 %d 行 / 加成与效果句 %d 行 / 没认出来：%s"
                       % (base_rows, other_rows, offlist[:5] or "无"))
    want_sum = sum_expect(tot)
    check("属性合计那排等于门禁独立解析的结果（纯加法，不含基础值与附魔）",
          ic["sum"] == want_sum, "界面 %s ／ 数据 %s" % (ic["sum"], want_sum))
    page.screenshot(path=os.path.join(SHOT_DIR, "app-bis.png"))
    # 上面比的是页面默认落在的战士那一套——偏偏那一套全是 "N点护甲"，
    # 一条漏算的写法都碰不到，所以它单独证明不了这次修的东西。
    # 这一条走玩家真点的路径换到猎人 PvE 联盟（#9509 浸油护腿的 "90 护甲" 就在这套里），
    # 再按同一份门禁解析比一遍。点职业条而不是改地址：这个组件只在 setup 读一次 query，
    # 光换 hash 不会让它换职业。
    hi = page.evaluate("""() => [...document.querySelectorAll('.pzrail .pztab')]
      .findIndex(b => b.innerText.indexOf('猎人') >= 0)""")
    check("职业条里找得到猎人那一格", hi >= 0, "第 %d 格" % hi)
    page.click(".pzrail .pztab >> nth=%d" % hi)
    page.wait_for_timeout(1500)
    hdoll = [s for s in sets if s["id"] == "hunter"][0]["doll"]["alliance"]
    hsum = page.evaluate("() => [...document.querySelectorAll('.pzsum-i span')]"
                         ".map(x => x.innerText.replace(/\\s+/g,' ').trim())")
    htot, hoff, hbase, hother = stat_totals(det, hdoll)
    check("猎人 PvE 联盟每条带护甲的行都落进了已知写法（「90 护甲」这一种以前被漏掉）",
          not hoff, "计入基础护甲 %d 行 / 加成与效果句 %d 行 / 没认出来：%s"
                    % (hbase, hother, hoff[:5] or "无"))
    check("猎人 PvE 联盟那排属性合计等于门禁独立解析的结果",
          hsum == sum_expect(htot), "界面 %s ／ 数据 %s" % (hsum, sum_expect(htot)))
    # 证据两张：一张把「这套装备给的属性」那一排行滚进视口拍清楚，一张整页留全貌
    page.locator(".pzsum").scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(SHOT_DIR, "app-bis-hunter-armor.png"))
    page.screenshot(path=os.path.join(SHOT_DIR, "app-bis-hunter-armor-full.png"), full_page=True)
    ctx.close()

    ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    mp = ctx.new_page()
    mp.goto(APP_BASE + "/#/bis", wait_until="networkidle")
    mp.wait_for_timeout(2000)
    mm = mp.evaluate("""() => ({over: document.documentElement.scrollWidth - innerWidth,
      small: [...document.querySelectorAll('.pzcell, .pz-mode .pick, .pz-cls .pick')]
        .filter(b => b.getBoundingClientRect().height < 44).length })""")
    check("配装页 375 不横向溢出", mm["over"] <= 1, json.dumps(mm))
    check("配装页 375 点击目标不低于 44px", mm["small"] == 0, "%d 个偏小" % mm["small"])
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-bis-m.png"))
    # 375 上补一张猎人那套的合计行（这次修的就是这一排）
    hmi = mp.evaluate("""() => [...document.querySelectorAll('.pzrail .pztab')]
      .findIndex(b => b.innerText.indexOf('猎人') >= 0)""")
    mp.click(".pzrail .pztab >> nth=%d" % hmi)
    mp.wait_for_timeout(1500)
    mp.locator(".pzsum").scroll_into_view_if_needed()
    mp.wait_for_timeout(300)
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-bis-hunter-armor-m.png"))
    ctx.close()


def test_design_baseline(browser, base):
    """吸收自通用设计走查规则的量化底线：每屏一个 H1、触屏点击目标 ≥44px、
       控件有可读名、图片有 alt、数字用等宽对齐。见 docs/UI.md 第七节。"""
    print("\n[8] 设计量化基线")
    for mob, vp in [("桌面", {"width": 1440, "height": 1000}),
                    ("移动 375", {"width": 375, "height": 812, "is_mobile": True, "has_touch": True})]:
        ctx = browser.new_context(viewport=vp, is_mobile=("移动" in mob), has_touch=("移动" in mob))
        for name in PAGES:
            page = ctx.new_page()
            page.goto("%s/%s.html" % (base, name), wait_until="networkidle")
            page.wait_for_timeout(1100)
            r = page.evaluate("""() => {
              const els = [...document.querySelectorAll('button, a, input, .node, .qopt, .term, .cls')];
              const small = els.filter(e => { const b = e.getBoundingClientRect();
                  return b.width > 0 && b.height > 0 && Math.min(b.width, b.height) < 44; });
              return {
                h1: document.querySelectorAll('h1').length,
                small: small.map(e => e.tagName + '.' + String(e.className).split(' ')[0]),
                unnamed: els.filter(e => !e.textContent.trim() && !e.getAttribute('aria-label') && !e.placeholder).length,
                noAlt: [...document.querySelectorAll('img')].filter(i => i.getAttribute('alt') === null).length };
            }""")
            kinds = {}
            for k in r["small"]:
                kinds[k] = kinds.get(k, 0) + 1
            top = sorted(kinds.items(), key=lambda x: -x[1])[:2]
            check("%s H1 唯一 %s" % (mob, name), r["h1"] == 1, "H1 %d 个" % r["h1"])
            if "移动" in mob:
                check("移动端点击目标 ≥44px %s" % name, not r["small"],
                      "%d 个偏小 %s" % (len(r["small"]), top))
            check("控件都有可读名 %s" % name, r["unnamed"] == 0, "%d 个缺名" % r["unnamed"])
            check("图片都有 alt %s" % name, r["noAlt"] == 0, "%d 张缺 alt" % r["noAlt"])
            page.close()
        ctx.close()
    ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(base + "/glossary.html", wait_until="networkidle")
    page.wait_for_timeout(1200)
    page.screenshot(path=os.path.join(SHOT_DIR, "glossary-mobile-375.png"))
    page.goto(base + "/talent.html?c=hunter", wait_until="networkidle")
    page.wait_for_timeout(1500)
    page.screenshot(path=os.path.join(SHOT_DIR, "talent-mobile-tabs.png"))
    ctx.close()


def test_mobile(browser, base):
    print("\n[9] 375px 移动端")
    ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m, e=errors: e.append(m.text[:100]) if m.type == "error" else None)
    open_talent(page, base)
    visible = page.evaluate("() => [...document.querySelectorAll('.tree')].filter(t => !t.classList.contains('hide')).length")
    check("移动端只展开当前一系", visible == 1, "可见树 %d" % visible)
    click(page, DEMO_A00)
    page.wait_for_timeout(200)
    click(page, DEMO_A00)
    page.wait_for_timeout(250)
    check("移动端加点可用", ranks(page, DEMO_A00)["ranks"] == 2, "a-0-0=%s" % ranks(page, DEMO_A00)["ranks"])
    page.evaluate("() => document.getElementById('mode').click()")
    click(page, DEMO_A00)
    page.wait_for_timeout(250)
    check("移动端用减点按钮可减点（没有右键也能完成）", ranks(page, DEMO_A00)["ranks"] == 1,
          "a-0-0=%s" % ranks(page, DEMO_A00)["ranks"])
    page.screenshot(path=os.path.join(SHOT_DIR, "talent-mobile-375.png"))
    check("移动端无控制台报错", not errors, "; ".join(errors[:2]))
    ctx.close()


def test_races(browser, base):
    """种族页与分组导航：矩阵完整性、筛选、逐条来源、冲突留痕、移动端点击目标。"""
    print("\n[7] 种族页与分组导航")
    import json
    rc = json.load(open(os.path.join(SRC, "data", "races.json"), encoding="utf-8"))
    n_races = len(rc["races"])
    n_traits = sum(len(x.get("traits") or []) + len(((x.get("subgroup") or {}).get("traits") or []))
                   for x in rc["races"])
    n_marks = sum(len(x["classes"]) for x in rc["races"])
    n_horde = len([x for x in rc["races"] if x["faction"] == "horde"])

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: errs.append(m.text[:120]) if m.type == "error" else None)
    page.goto(base + "/races.html", wait_until="networkidle")
    page.wait_for_timeout(1000)
    check("种族页无脚本报错", not errs, "报错 %d %s" % (len(errs), errs[:2]))
    rows = page.evaluate("() => document.querySelectorAll('#mx tbody tr').length")
    cols = page.evaluate("() => document.querySelectorAll('#mx thead th').length - 1")
    marks = page.evaluate("() => document.querySelectorAll('#mx td.y').length")
    dashes = page.evaluate("() => document.querySelectorAll('#mx td.n').length")
    check("矩阵行数与数据一致", rows == n_races, "DOM %d / 数据 %d" % (rows, n_races))
    check("矩阵覆盖 9 个职业列", cols == 9, "列 %d" % cols)
    check("✓ 与 — 铺满整表不留空", marks + dashes == rows * 9,
          "✓ %d + — %d，应 %d" % (marks, dashes, rows * 9))
    check("✓ 数等于数据里的可选职业总数", marks == n_marks, "DOM %d / 数据 %d" % (marks, n_marks))
    # 2026-10-12 用户实拍反馈：「按词找特长」那张卡撤了——40 条特长在种族详情里逐条带官方整句，
    # 同一份内容不该在页面上铺两遍；跨种族搜词由顶栏搜索承担（索引里每条特长都带种族号）。
    check("「按词找特长」那张卡已撤，特长不再铺第二遍",
          page.evaluate("() => !document.querySelector('#tt') && "
                        "!(document.querySelector('#main').innerText.indexOf('按词找特长') >= 0)"))
    first = rc["races"][0]
    n_first = len(first.get("traits") or []) + len(((first.get("subgroup") or {}).get("traits") or []))
    det = page.evaluate("""() => ({ rows: document.querySelectorAll('#rdet .rdtr > li').length,
      quotes: document.querySelectorAll('#rdet .rdtr .quote').length,
      src: document.querySelectorAll('#rdet .rdtr [data-src]').length,
      name: ((document.querySelector('#rdet h2') || {}).innerText || '').trim() })""")
    # 2026-10-12 站主决定：逐条「来源」按钮从内容页撤了，出处集中在溯源页说。
    # 这条从"条数/整句/来源三项齐"改成"条数与官方整句齐，且不再有来源按钮"。
    check("特长由种族详情逐条给：条数与官方整句齐，逐条来源按钮已撤",
          det["rows"] == n_first and det["quotes"] == n_first and det["src"] == 0,
          "「%s」详情 %d 条 / 整句 %d / 来源按钮 %d / 数据 %d"
          % (det["name"], det["rows"], det["quotes"], det["src"], n_first))

    col2 = page.evaluate("() => document.querySelectorAll('#mx tbody td:nth-child(2).y').length")
    page.click("#mx thead th:nth-child(2) button")
    page.wait_for_timeout(250)
    off = page.evaluate("() => document.querySelectorAll('#mx tbody tr.off').length")
    check("点表头职业可按列筛选", off == rows - col2, "灰掉 %d 行（该列 ✓ %d 行）" % (off, col2))
    page.click("#mx thead th:nth-child(2) button")
    page.wait_for_timeout(250)
    check("再点一次取消筛选",
          page.evaluate("() => document.querySelectorAll('#mx tbody tr.off').length") == 0)

    page.select_option("#ff", "horde")
    page.wait_for_timeout(250)
    h = page.evaluate("() => document.querySelectorAll('#mx tbody tr').length")
    check("阵营筛选生效", h == n_horde, "部落 %d 行（应 %d）" % (h, n_horde))
    page.select_option("#ff", "")
    page.wait_for_timeout(200)

    text = page.evaluate("() => document.querySelector('#main').innerText")
    # 冲突不再单开一张卡，但话必须还说：矩阵与导语两种说法 + 本站处置，压成矩阵下面一行红字
    check("矩阵与导语两种说法并存，压成一行红字仍然说清楚",
          "天裔到底能选几个职业" in text and "两个都留" in text
          and page.evaluate("() => !!document.querySelector('#main p.conf')"),
          "红字 %d 处" % page.evaluate("() => document.querySelectorAll('#main p.conf').length"))
    check("「这一页没有的」那张卡已撤（缺口改由溯源页集中说）",
          "这一页没有的" not in text)
    # 头像：矩阵那一列原来被两层 6px 左边距推出格子、压住种族名（用户实拍图4）
    geo = page.evaluate("""() => { const th = document.querySelector('#mx tbody th.rh');
      const f = th.querySelector('.rface'), l = th.querySelector(':scope > span:not(.rface)');
      const a = f.getBoundingClientRect(), b = l.getBoundingClientRect();
      const card = document.querySelector('.racecard .rface');
      const cb = card.getBoundingClientRect(), ci = card.querySelector('img').getBoundingClientRect();
      return { faceRight: Math.round(a.right), labelLeft: Math.round(b.left),
        faceW: Math.round(a.width), liwMargin: getComputedStyle(f.querySelector('.liw')).marginLeft,
        cardFace: Math.round(cb.width), cardImgInside:
          Math.round(ci.left) >= Math.round(cb.left) - 1 && Math.round(ci.right) <= Math.round(cb.right) + 1 }; }""")
    check("矩阵头像不再压住种族名（两层 6px 左边距那个坑）",
          geo["labelLeft"] >= geo["faceRight"] and geo["liwMargin"] == "0px",
          "头像右 %d / 名字左 %d / 内层 margin %s"
          % (geo["faceRight"], geo["labelLeft"], geo["liwMargin"]))
    check("阵营带里的种族头像整张在框内，格子放到 72px",
          geo["cardImgInside"] and geo["cardFace"] >= 72,
          "卡内头像 %dpx，图在框内=%s" % (geo["cardFace"], geo["cardImgInside"]))
    cards = page.evaluate("() => document.querySelectorAll('.racecard').length")
    check("种族头像卡数量与矩阵行数一致", cards == n_races, "卡片 %d" % cards)
    fac = page.evaluate("""() => [...document.querySelectorAll('.facband')].map(b => ({
      cls: b.className, bg: !!b.querySelector('.fembg img'),
      src: (b.querySelector('.fembg img') || {}).src || '',
      mark: (b.querySelector('.artmark') || {}).textContent || '',
      pe: getComputedStyle(b.querySelector('.fembg') || b).pointerEvents,
      broken: [...b.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0
        && !/bad/.test(i.className)).length }))""")
    check("两条阵营带都铺了城市原画", len(fac) == 2 and all(x["bg"] for x in fac),
          json.dumps([{k: v for k, v in x.items() if k in ("cls", "bg")} for x in fac], ensure_ascii=False))
    check("阵营原画是本地文件且没有坏图",
          all("/img/art/factions/city-" in x["src"] for x in fac) and sum(x["broken"] for x in fac) == 0,
          json.dumps([x["src"].split("/")[-1] for x in fac], ensure_ascii=False))
    check("阵营原画右上角的素材出处角标已撤（2026-10-12 站主决定）",
          all(not x["mark"] for x in fac),
          " / ".join(x["mark"] for x in fac))
    check("背景层不挡种族卡的点击", all(x["pe"] == "none" for x in fac), json.dumps([x["pe"] for x in fac]))
    bands = page.evaluate("""() => [...document.querySelectorAll('.facband')].map(b => ({
      fac: b.classList.contains('alliance') ? 'alliance' : 'horde',
      n: b.querySelectorAll('.racecard').length, emb: !!b.querySelector('.femb')}))""")
    check("联盟与部落各一条阵营带，各 5 个种族且带阵营徽标",
          len(bands) == 2 and all(b["n"] == 5 and b["emb"] for b in bands) and
          sorted(x["fac"] for x in bands) == ["alliance", "horde"], str(bands))
    faces = page.evaluate("""() => { const a = [...document.querySelectorAll('.rface-art')];
      return { n: a.length, broken: a.filter(i => i.complete && i.naturalWidth === 0).length }; }""")
    check("种族头像用本地转存图且一张都不坏", faces["n"] >= 10 and faces["broken"] == 0,
          "头像 %d 张 / 坏 %d" % (faces["n"], faces["broken"]))
    page.click('.racecard[data-race="horde-troll"]')
    page.wait_for_timeout(400)
    det = page.evaluate("""() => ({ h2: document.querySelector('#rdet .rdt h2').innerText.trim(),
      hash: location.hash, cls: document.querySelectorAll('#rdet .rdcl').length,
      tr: document.querySelectorAll('#rdet .rdtr > li').length,
      lore: (document.querySelector('#rdet .lore') || {}).innerText || '' })""")
    check("点阵营里的种族卡会换下方详情并写进地址栏",
          "巨魔" in det["h2"] and det["hash"] == "#race=horde-troll" and det["cls"] == 9 and
          det["tr"] == 4 and len(det["lore"]) > 30, str(det))
    check("详情里的可选职业把不能选的标灰",
          page.evaluate("() => document.querySelectorAll('#rdet .rdcl.off').length") > 0)
    # 2026-10-12 站主决定：详情里那个「来源」展开按钮一并撤下（原来点这里会展开 #srcbox）。
    # 反向断言：内容页上不该再有点开来源的入口。
    check("种族详情没有来源按钮，也没有来源展开块",
          page.evaluate("() => !document.querySelector('#rdet [data-src]') && "
                        "![...document.querySelectorAll('.srcbox')].some(b => b.innerText.trim())"))
    page.screenshot(path=os.path.join(SHOT_DIR, "races-matrix.png"), full_page=True)

    labels = page.evaluate("() => [...document.querySelectorAll('nav.main .ngt')].map(b => b.textContent.trim())")
    # 角标「新」是入口的附属信息，不是入口名的一部分：读名字时把 .nb 剔掉再比
    subs = page.evaluate("() => [...document.querySelectorAll('nav.main a.nl')].map(a => {"
                         "const c = a.cloneNode(true);"
                         "c.querySelectorAll('.nb').forEach(n => n.remove());"
                         "return c.textContent.trim(); })")
    check("导航一级只剩分组标签", labels == ["天赋", "职业", "种族", "世界", "专业", "工具"], str(labels))
    # 导航二级项是一份对外契约，逐项写死比"数量等于页数+1"更能说明预期：
    # 2026-10-12 用户实拍后撤了「技能书」与「特长」两格（页面本身还在，见 NO_NAV_ENTRY）。
    # **2026-10-16 起这一份是旧站的（已冻结）**：新站导航收窄成 11 格，两栈有意不同，
    # 别把这里改成跟新站对齐，也别把新站那 7 格补回来——新站的钉在 [16] 节 test_app 里。
    NAV_ENTRIES = ["首页", "计算器", "职业", "玩法问答", "传承", "总览",
                   "区域与稀有", "成就", "副本", "团本", "系统规则", "配方",
                   "速查", "时间表", "动态", "排行", "溯源"]
    # 格数从表里算，不写在句子中——2026-10-16 加成就页时那句"就是这 16 格"就成了假话
    # （断言本身是对的，名字与顺序照旧逐项比，只有标题里的数字会漂）。
    check("导航二级项就是这 %d 格，顺序与名字不许漂" % len(NAV_ENTRIES), subs == NAV_ENTRIES,
          "%d 项：%s" % (len(subs), subs))
    nav_files = page.evaluate("() => [...document.querySelectorAll('nav.main a.nl')]"
                              ".map(a => (a.getAttribute('href') || '').split('#')[0])")
    no_entry = [p for p in PAGES if (p + ".html") not in nav_files
                and p not in NO_NAV_ENTRY and p not in DETAIL_PARENT]
    check("除刻意撤下入口的那几页，每个页面都能从导航走到", not no_entry, "导航里找不到：%s" % no_entry)
    check("导航里不再有任何下拉面板",
          page.evaluate("() => document.querySelectorAll('.ndp, .ndb, [aria-haspopup]').length") == 0)
    navh = page.evaluate("() => Math.round(document.querySelector('nav.main').getBoundingClientRect().height)")
    # 这条原来卡 navh<=44，编码的是"导航只有一行"的旧设计。2026-10-11 用户要求改成上下两级
    # （组名在上、入口在下），导航带必然变高，所以判据改成它真正要防的事：
    # 入口不许换行溢出、整条带子不超过 56px（再高就吃掉正文首屏）。
    nav_one = page.evaluate("() => new Set([...document.querySelectorAll('nav.main a.nl')]"
                            ".map(a => Math.round(a.getBoundingClientRect().top))).size")
    check("桌面导航排在一行内（两级结构：组名行 + 入口行）",
          navh <= 56 and nav_one == 1, "导航带 %dpx / 入口占了 %d 行" % (navh, nav_one))
    onb = page.evaluate("() => { const a = document.querySelector('nav.main a.nl.on'); if (!a) return '';"
                        "const c = a.cloneNode(true); c.querySelectorAll('.nb').forEach(n => n.remove());"
                        "return c.textContent.trim(); }")
    check("当前页在导航里高亮", onb == "总览", "高亮「%s」" % onb)
    hitg = page.evaluate("() => { const g = document.querySelector('nav.main .ngrp.hit');"
                         "return g ? g.querySelector('.ngt').textContent.trim() : ''; }")
    check("当前页所在分组的标签转金色", hitg == "种族", "分组「%s」" % hitg)
    tip = page.evaluate("() => { const a = [...document.querySelectorAll('nav.main a.nl')]"
                        ".find(x => x.textContent.replace(/新$/, '').trim() === '副本');"
                        "return a ? a.getAttribute('title') : ''; }")
    check("页面说明收进悬停提示，不占版面", bool(tip) and "38 座" in tip, tip)
    # 玩法问答的候选板：九格常驻，答过题才有人掉出候选，卡头读数要跟压暗数对上
    np = ctx.new_page()
    np.goto(base + "/chooser.html", wait_until="networkidle")
    np.wait_for_timeout(1200)
    board0 = np.evaluate("() => document.querySelectorAll('.ctile').length")
    for _ in range(3):
        np.click(".qopts .qopt >> nth=0")
        np.wait_for_timeout(260)
    bd = np.evaluate("""() => ({ off: document.querySelectorAll('.ctile.off').length,
      lead: document.querySelectorAll('.ctile.lead').length,
      pool: +(((document.querySelector('.cboard .mline') || {}).innerText || '')
        .match(/还在候选\\s*(\\d+)/) || [])[1] })""")
    check("问答页候选板九格常驻，答完题有人掉出候选且读数一致",
          board0 == 9 and bd["off"] > 0 and bd["lead"] >= 1 and bd["pool"] == 9 - bd["off"],
          json.dumps(bd, ensure_ascii=False))
    np.close()
    ctx.close()

    m = browser.new_context(viewport={"width": 375, "height": 780}, is_mobile=True, has_touch=True)
    mp = m.new_page()
    mp.goto(base + "/races.html", wait_until="networkidle")
    mp.wait_for_timeout(1000)
    small = mp.evaluate("() => [...document.querySelectorAll('nav.main a.nl, #mx thead button.ch')]"
                        ".filter(e => e.offsetHeight && e.offsetHeight < 44)"
                        ".map(e => (e.className || 'a') + ':' + e.offsetHeight)")
    check("移动端导航与矩阵表头点击目标 ≥44px", not small, str(small[:4]))
    mob = mp.evaluate("""() => { const nav = document.querySelector('nav.main');
      const inr = nav.querySelector('.in'), vw = document.documentElement.clientWidth;
      const links = [...nav.querySelectorAll('a.nl')];
      const on = links.find(a => a.classList.contains('on'));
      const r = on ? on.getBoundingClientRect() : null;
      return { rows: new Set(links.map(e => Math.round(e.getBoundingClientRect().top))).size,
               scrollable: inr.scrollWidth > inr.clientWidth + 8, overflow: inr.scrollWidth - inr.clientWidth,
               vw: vw, right: Math.round(nav.getBoundingClientRect().right),
               onVisible: r ? (r.left >= 0 && r.right <= vw) : false,
               head: Math.round(document.querySelector('.top').getBoundingClientRect().height),
               pos: getComputedStyle(document.querySelector('.top')).position }; }""")
    check("移动端导航排成一条可横滑的导航带", mob["rows"] == 1 and mob["scrollable"],
          json.dumps(mob, ensure_ascii=False))
    check("移动端顶栏整体不超过 100px", mob["head"] <= 100 and mob["pos"] == "sticky", str(mob["head"]))
    check("当前页那一项已滚进可视区", mob["onVisible"], json.dumps(mob, ensure_ascii=False))
    mp.evaluate("() => document.querySelector('nav.main .in').scrollLeft = 9999")
    mp.wait_for_timeout(250)
    tail = mp.evaluate("() => { const inr = document.querySelector('nav.main .in');"
                       "const links = [...inr.querySelectorAll('a.nl')];"
                       "const last = links[links.length - 1].getBoundingClientRect();"
                       "return { atEnd: inr.scrollLeft + inr.clientWidth >= inr.scrollWidth - 2,"
                       " lastVisible: last.right <= document.documentElement.clientWidth + 1 }; }")
    check("滑到右端能点到最后一个入口（溯源）", tail["atEnd"] and tail["lastVisible"], json.dumps(tail))
    mp.screenshot(path=os.path.join(SHOT_DIR, "nav-mobile-flat.png"))
    mp.goto(base + "/dungeons.html", wait_until="networkidle")
    mp.wait_for_timeout(1000)
    dtext = mp.evaluate("() => document.querySelector('#main').innerText")
    check("副本页那张「世界」里还没有数据的缺口卡已撤，锚点跟着撤（两栈同步）",
          "还没有数据" not in dtext and "#todo" not in mp.evaluate(
              "() => document.querySelector('#main').innerHTML"),
          "正文残留 %s" % [x for x in ("还没有数据", "世界地图") if x in dtext])
    mp.screenshot(path=os.path.join(SHOT_DIR, "nav-mobile-open.png"))
    m.close()


def test_grouping(browser, base):
    """分组与图标：技能书 / 术语速查按职业与种族分组，图标要么真图要么自绘占位，不许空白。"""
    print("\n[10] 分组与图标")
    import json
    icons = json.load(open(os.path.join(SRC, "data", "icons.json"), encoding="utf-8"))
    gl = json.load(open(os.path.join(SRC, "data", "glossary.json"), encoding="utf-8"))
    expect_rows = len(gl["items"])
    def icon_key(x):
        return ((x.get("raceId") or "") if x.get("kind") == "racial" else (x.get("classId") or "")) + "|" + x["cn"]
    expect_icons = len([x for x in gl["items"] if icons["map"].get(icon_key(x))])

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/skills.html", wait_until="networkidle")
    page.wait_for_timeout(1500)
    st = page.evaluate("""() => {
      const groups = [...document.querySelectorAll('#tbl .lgrp')];
      const rows = [...document.querySelectorAll('#tbl tbody tr:not(.grp2h)')].filter(r => !r.classList.contains('srow'));
      return { groups: groups.map(g => g.innerText.replace(/\\n/g, ' ').trim()),
               rows: rows.length,
               everyRowHasCell: rows.every(r => r.querySelector('.liw')),
               imgs: document.querySelectorAll('#tbl tbody .liw img').length,
               broken: [...document.querySelectorAll('#tbl tbody .liw img')].filter(i => i.complete && i.naturalWidth === 0).length,
               dupOwner: rows.map(r => r.querySelector('td:nth-child(5)')).length }; }""")
    check("技能书无脚本报错", not errs, "; ".join(errs[:2]))
    check("技能书按职业与种族分组", len(st["groups"]) >= 10,
          "%d 组：%s" % (len(st["groups"]), "、".join(g[:10] for g in st["groups"][:5])))
    check("分组后条目总数不丢", st["rows"] == expect_rows, "DOM %d / 数据 %d" % (st["rows"], expect_rows))
    check("每行都有图标格", st["everyRowHasCell"], "缺格 %s" % (not st["everyRowHasCell"]))
    check("官方图标数量与映射表一致", st["imgs"] == expect_icons,
          "DOM %d / 映射 %d" % (st["imgs"], expect_icons))
    check("没有加载失败的图标", st["broken"] == 0, "坏图 %d" % st["broken"])
    order = page.evaluate("() => [...document.querySelectorAll('#tbl .lgrp b')].map(x => x.textContent)")
    check("种族组按官方页阵营顺序排", order[4:9] == ["兽人", "亡灵", "牛头人", "巨魔", "天裔"], str(order[4:9]))
    page.screenshot(path=os.path.join(SHOT_DIR, "skills-grouped.png"))

    page.goto(base + "/glossary.html", wait_until="networkidle")
    page.wait_for_timeout(1500)
    gp = page.evaluate("""() => ({ groups: document.querySelectorAll('#pool .lgrp').length,
        chips: document.querySelectorAll('#pool .term').length,
        imgs: document.querySelectorAll('#pool .liw img').length })""")
    check("速查页同样分组且词条不丢", gp["groups"] >= 10 and gp["chips"] == expect_rows,
          "组 %d / 词条 %d" % (gp["groups"], gp["chips"]))
    page.select_option("#fr", "skyborne")
    page.wait_for_timeout(400)
    sky = page.evaluate("""() => ({ groups: [...document.querySelectorAll('#pool .lgrp b')].map(x => x.textContent),
        chips: document.querySelectorAll('#pool .term').length })""")
    check("按种族筛选只剩天裔组", sky["groups"] == ["天裔"] and sky["chips"] == 5,
          "%s / %d 条" % (sky["groups"], sky["chips"]))
    page.select_option("#fr", "")
    page.wait_for_timeout(300)

    page.goto(base + "/races.html", wait_until="networkidle")
    page.wait_for_timeout(1200)
    # 「按词找特长」那张跨种族全表已撤（2026-10-12 用户实拍反馈），分组检查改看种族详情
    rt = page.evaluate("""() => ({ groups: [...document.querySelectorAll('#rdet .rdtr > li b')]
          .map(x => x.textContent.trim()), quotes: document.querySelectorAll('#rdet .rdtr .quote').length })""")
    check("种族详情把这一族的特长逐条列出来，每条带官方整句",
          len(rt["groups"]) >= 4 and rt["quotes"] == len(rt["groups"]),
          "%d 条 / 整句 %d" % (len(rt["groups"]), rt["quotes"]))
    ctx.close()

    m = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    mp = m.new_page()
    mp.goto(base + "/skills.html", wait_until="networkidle")
    mp.wait_for_timeout(1500)
    mob = mp.evaluate("""() => { const gs = [...document.querySelectorAll('#tbl .lgrp')];
      const vw = document.documentElement.clientWidth;
      return { over: gs.filter(g => g.getBoundingClientRect().right > vw).length,
               first: gs.length ? gs[0].innerText.replace(/\\n/g, ' ') : '' }; }""")
    check("移动端分组标题不溢出视口", mob["over"] == 0, "溢出 %d 个；首个「%s」" % (mob["over"], mob["first"]))
    ab = mp.evaluate("""() => { const t = document.querySelector('#abtbl table');
      const box = t.closest('.scrollx'); const nm = document.querySelector('#abtbl tbody tr td b');
      return { scroll: box.scrollWidth > box.clientWidth, nameH: Math.round(nm.getBoundingClientRect().height) }; }""")
    # 单元格高度会跟着整行拉伸，所以看名称本身占几行：一行 ≈ 20px，超过 28px 就是被挤换行了
    check("移动端四态表横向滚而不是把名称挤成一字一行",
          ab["scroll"] and ab["nameH"] <= 28, json.dumps(ab))
    mp.screenshot(path=os.path.join(SHOT_DIR, "skills-grouped-mobile.png"))
    m.close()

    # 十页正文里不该出现面向开发的东西：脚本路径、原始 JSON、未替换的占位符
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    bad_pages = []
    for name in PAGES:
        dp = ctx.new_page()
        dp.goto("%s/%s.html" % (base, name), wait_until="networkidle")
        dp.wait_for_timeout(1100)
        t = dp.evaluate("() => document.querySelector('#main').innerText")
        hits = dev_word_hits(t)
        if hits:
            bad_pages.append("%s:%s" % (name, ",".join(hits)))
        dp.close()
    check("%d 页正文没有调试文案与原始数据" % len(PAGES), not bad_pages, "; ".join(bad_pages))
    # 官方 CDN 取回来的职业 / 种族图标要真的显示出来，且一张都不许坏
    rp = ctx.new_page()
    rp.goto(base + "/races.html", wait_until="networkidle")
    rp.wait_for_timeout(1300)
    ri = rp.evaluate("""() => { const a = [...document.querySelectorAll('.liw img')];
      return { imgs: a.length, broken: a.filter(i => i.complete && i.naturalWidth === 0).length,
               tiles: document.querySelectorAll('.racecard .rface .liw.t').length }; }""")
    check("种族页用上本地官方图标", ri["imgs"] >= 21 and ri["broken"] == 0,
          "图 %d 张 / 坏 %d / 方块 %d" % (ri["imgs"], ri["broken"], ri["tiles"]))
    hp = ctx.new_page()
    hp.goto(base + "/index.html", wait_until="networkidle")
    hp.wait_for_timeout(1300)
    hi = hp.evaluate("""() => { const a = [...document.querySelectorAll('.stripc .liw img')];
      return { imgs: a.length, broken: a.filter(i => i.complete && i.naturalWidth === 0).length }; }""")
    check("首页职业卡用上官方职业图标", hi["imgs"] == 9 and hi["broken"] == 0, json.dumps(hi))
    hp.screenshot(path=os.path.join(SHOT_DIR, "index-class-icons.png"))
    rp.screenshot(path=os.path.join(SHOT_DIR, "races-race-icons.png"))
    ctx.close()


def test_dungeon_data(browser, base):
    """地下城模块：客户端解包进来的首领与掉落要按口径显示，掉落不写百分比。"""
    print("\n[11] 地下城数据与客户端原画")
    import json
    dg = json.load(open(os.path.join(SRC, "data", "dungeons.json"), encoding="utf-8"))
    rows = []
    for k in ("newDungeons", "classicDungeons", "raids"):
        rows += dg.get(k) or []
    exp_boss = sum(len(x.get("bosses") or []) for x in rows)
    exp_drop = sum(len(x.get("drops") or []) for x in rows)

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/dungeons.html", wait_until="networkidle")
    page.wait_for_timeout(1500)
    check("副本页无脚本报错", not errs, "; ".join(errs[:2]))
    cards = page.evaluate("() => document.querySelectorAll('.dcard2').length")
    check("副本卡数量等于数据", cards == len(rows), "DOM %d / 数据 %d" % (cards, len(rows)))
    page.evaluate("() => document.querySelector('.dcard2 button[data-d]').click()")
    page.wait_for_timeout(400)
    # 横幅图是 loading="lazy"，不滚一遍不会发请求，先滚到底再数
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1200)
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(400)
    st = page.evaluate("""() => ({
      lists: document.querySelectorAll('.bosslist').length,
      bosses: document.querySelectorAll('.bosslist .bh b').length,
      loot: document.querySelectorAll('.loot-i').length,
      open: [...document.querySelectorAll('.drawer')].filter(x => x.style.display !== 'none').length,
      pct: (document.querySelector('#main').innerText.match(/\\d+(\\.\\d+)?\\s*%/g) || []).slice(0, 3),
      art: [...document.querySelectorAll('img.dbn-art')].filter(i => i.complete && i.naturalWidth > 0).length })""")
    check("抽屉里有首领列表", st["open"] >= 1 and st["lists"] >= 1, "展开 %d 张" % st["open"])
    check("掉落条目与逐条来源都在 DOM 里", st["loot"] >= 1, "首张卡掉落 %d 件" % st["loot"])
    check("掉落不写百分比", not st["pct"], "出现 %s" % st["pct"])
    check("本地转存的副本原画加载成功", st["art"] >= 5, "加载 %d 张" % st["art"])
    # 客户端队伍查找器对账：人数、三种分歧、还不能排队的说明，以及本站没有名单的那几张表
    qc = json.load(open(os.path.join(SRC, "data", "queue.json"), encoding="utf-8"))
    exp = {
        "party": len([x for x in rows if x.get("partySize")]),
        "twoRange": 0,   # 2026-10-13 站主定稿：等级区间只摆一个数，界面上不再出"两说"行
        "settled": len([x for x in rows if x.get("levelRangeOfficial")]),
        "twoSize": len([x for x in rows if x.get("partySizeAlt")]),
        "twoName": len([x for x in rows if x.get("nameEnClient")]),
        "noqueue": len([x for x in rows if not x.get("clientActivityId")]),
        "src": len([x for x in rows if x.get("clientActivityId") or x.get("levelRangeClient")
                    or x.get("levelRangeAlt") or x.get("partySize") or x.get("partySizeAlt")
                    or x.get("nameEnClient")]),
        "queue": len({i["nameEn"] for i in qc["items"] if not i.get("matchedId")}),
    }
    got = page.evaluate("""() => {
      const spans = [...document.querySelectorAll('.dmeta span')];
      const conf = [...document.querySelectorAll('#main .conf')].map(e => e.textContent);
      const q = document.querySelector('#queue');
      return {
        party: spans.filter(s => /^一次 \\d+ 人$/.test(s.textContent.trim())).length,
        twoRange: conf.filter(t => /等级区间/.test(t)).length,
        twoSize: conf.filter(t => /另有一条/.test(t)).length,
        twoName: conf.filter(t => /英文原名两说/.test(t)).length,
        noqueue: [...document.querySelectorAll('.dcard2 .note')]
          .filter(e => /队伍查找器里还没有这座本/.test(e.textContent)).length,
        // 数"挂了出处的本卡"而不是标记个数：一张卡可能同时为人数、区间、英文名各挂一枚
        // （2026-10-11 重抓后标记有 63 枚但只有 31 张本卡用到客户端字段，按枚数比必然对不上）。
        // 队列表不在 .dcard2 里，它那一枚由 check 的 "+1" 负责。
        src: (() => {
          const bs = [...document.querySelectorAll('.st.datamine_en')];
          return new Set(bs.map(e => e.closest('.dcard2')).filter(Boolean)).size;
        })(),
        qrows: q ? q.querySelectorAll('tbody tr').length : -1,
        qnames: q ? [...q.querySelectorAll('tbody tr td b')].map(b => b.textContent.trim()) : [],
        intro: (document.querySelector('.card .dim') || {}).textContent || ''
      }; }""")
    check("进入人数按客户端给的数逐座摆出来", got["party"] == exp["party"],
          "卡面 %d / 数据 %d" % (got["party"], exp["party"]))
    check("等级区间不再摆两说（站主 2026-10-13 按参考站卡片定稿）", got["twoRange"] == 0,
          "页面上还有 %d 条等级区间的两说行" % got["twoRange"])
    # 定稿不是把另一个数扔掉：官方公告那个必须还在数据里，且确实与采用的数不同
    bad_settled = [x["id"] for x in rows if x.get("levelRangeOfficial")
                   and str(x["levelRangeOfficial"]).replace("–", "-") == str(x.get("levelRange")).replace("–", "-")]
    check("定稿过的本仍留着定稿前那个数，且与采用的数确实不同",
          not bad_settled and exp["settled"] == 6, "留档 %d 座 / 一样的 %s" % (exp["settled"], bad_settled[:3]))
    # 界面上摆的区间要就是数据里那个数——防止"数据改了、页面还在渲染旧的那份"
    shown = page.evaluate("""() => [...document.querySelectorAll('.dcard2')]
      .map(c => { const r = c.querySelector('.dbn2-r'); const n = c.querySelector('.dbn2-n');
        return { id: (c.querySelector('[data-d]') || {}).dataset || null,
                 range: r ? r.textContent.replace(/\\s*级$/, '').trim() : '',
                 name: n ? n.textContent.trim() : '' }; })""")
    by_name = {}
    for x in rows:
        by_name[x.get("nameCn") or x.get("nameEn") or x["id"]] = str(x.get("levelRange") or "")
    wrong = [s["name"] for s in shown if s["name"] in by_name
             and by_name[s["name"]] and s["range"] != by_name[s["name"]]]
    check("卡面横幅上的区间等于数据里定稿后的数", not wrong, "对不上：%s" % wrong[:3])
    check("同一座有两种排队人数的都写明", got["twoSize"] == exp["twoSize"],
          "%d / %d" % (got["twoSize"], exp["twoSize"]))
    check("英文原名两说的都并列不取舍", got["twoName"] == exp["twoName"],
          "%d / %d" % (got["twoName"], exp["twoName"]))
    check("客户端还不能排队的本逐条说明", got["noqueue"] == exp["noqueue"],
          "%d / %d" % (got["noqueue"], exp["noqueue"]))
    # 2026-10-12 站主决定：逐条出处标记退出内容页，客户端排队数据的出处集中在溯源页讲——
    # 这条从"每张用到这份数据的本卡都挂出处"改成"内容页一枚都不许有"（数据侧的 provenance 仍由 build-data 卡口核）。
    check("副本卡不再挂逐条出处标记（出处集中在溯源页）", got["src"] == 0,
          "残留 %d 张卡挂出处" % got["src"])
    check("客户端能排到、本站没名单的单列一张表", got["qrows"] == exp["queue"],
          "表 %d 行 / 应有 %d 行" % (got["qrows"], exp["queue"]))
    have = {x.get("nameEn") for x in rows}
    dup = [n for n in got["qnames"] if n in have]
    check("那张表里不重复列本站已有的本", not dup, str(dup[:3]))
    check("首段交代了人数与分歧的来处", "一次几人取自客户端的队伍查找器" in got["intro"], got["intro"][:60])
    bands = page.evaluate("() => [...document.querySelectorAll('.band b')].map(x => x.textContent.trim())")
    check("地下城按十级一档分档", len(bands) >= 5 and any("40" in x for x in bands), str(bands))
    seals = page.evaluate("() => document.querySelectorAll('.dbn2-seal').length")
    newn = len([x for x in (dg.get("newDungeons") or []) if x.get("kind") == "new"])
    check("无限新增本带\"新\"角标", seals == newn, "%d 个角标 / %d 座新本" % (seals, newn))
    conf = page.evaluate("() => document.querySelectorAll('#main .conf').length")
    exp_conf = len([x for x in rows if x.get("partySizeAlt")]) + exp["twoName"]
    check("还活着的那些分歧（人数 / 英文原名）一条都没漏", conf == exp_conf,
          "%d 处 / 应有 %d 处" % (conf, exp_conf))
    # 译名按官方来：冲突行不许回来，但另一个写法必须还在数据里（不是删掉，是不摆）
    confCn = page.evaluate("() => [...document.querySelectorAll('#main .conf')]"
                           ".filter(e => /译名|待定稿/.test(e.textContent)).length")
    hasAlt = len([x for x in rows if x.get("nameCnConflict")])
    check("译名只写官方那个（页面上没有译名冲突行），另一个写法仍留在数据里",
          confCn == 0 and hasAlt >= 1, "页面 %d 行 / 数据 %d 座留着" % (confCn, hasAlt))
    # 首领头像：方块数要等于首领数（没脸的也得有个自绘块），只有数据里挂了本地转存路径的才放图
    faces = page.evaluate("""() => ({
      tiles: document.querySelectorAll('.bosslist .bh > .liw').length,
      imgs: [...document.querySelectorAll('.bosslist .bh > .liw img')].map(i => i.getAttribute('src'))})""")
    bosses = [b for k in ("newDungeons", "classicDungeons", "raids")
              for d in (dg.get(k) or []) for b in (d.get("bosses") or [])]
    with_p = [b for b in bosses if b.get("portrait")]
    check("每个首领位都有一个头像方块", faces["tiles"] == len(bosses),
          "%d 个方块 / 数据 %d 个首领" % (faces["tiles"], len(bosses)))
    check("只有本地转存到脸的首领才放图",
          sorted(faces["imgs"]) == sorted([b["portrait"] for b in with_p]),
          "%d 张图 / 数据 %d 张" % (len(faces["imgs"]), len(with_p)))
    page.screenshot(path=os.path.join(SHOT_DIR, "dungeons-with-loot.png"))
    ctx.close()

    tp = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = tp.new_page()
    page.goto(base + "/talent.html?c=hunter", wait_until="networkidle")
    page.wait_for_timeout(1600)
    bg = page.evaluate("""() => { const i = document.querySelector('.tbg img');
      return i ? { ok: i.complete && i.naturalWidth > 0, w: i.naturalWidth } : null; }""")
    check("天赋页用上职业背景图", bool(bg) and bg["ok"], str(bg))
    tl = page.evaluate("""() => {
      const legend = [...document.querySelectorAll('.tlegend span')].filter(x => x.querySelector('i')).length;
      const marks = document.querySelectorAll('.node[class*="chg-"]').length;
      const lines = document.querySelectorAll('.tlines line').length;
      const hint = document.querySelector('.tree .hint');
      return { legend: legend, marks: marks, lines: lines, cells: document.querySelectorAll('.node[data-n]').length,
               gate: hint ? hint.textContent : '' }; }""")
    check("天赋树有图例与改动标记", tl["legend"] == 4 and tl["marks"] >= 20,
          "图例 %d / 标记 %d / 格子 %d" % (tl["legend"], tl["marks"], tl["cells"]))
    check("前置连线画出来了", tl["lines"] >= 6, "%d 条" % tl["lines"])
    check("层级门槛不再写未核实", "未核实" not in tl["gate"], tl["gate"].strip()[:44])
    page.click("#cmp")
    page.wait_for_timeout(1200)
    cmpn = page.evaluate("() => document.querySelectorAll('.cmprow').length")
    check("与经典旧世对比能展开且有内容", cmpn >= 20, "%d 条对照" % cmpn)
    page.screenshot(path=os.path.join(SHOT_DIR, "talent-class-art.png"))
    tp.close()


def test_dungeon_detail(browser, base):
    """副本线改版（2026-10-13）：列表页只留"挑一座"要看的四件事，每座本另有一页。
       钉三件事：① 卡面收进抽屉的分歧一条都没少（按数据逐座数）；② 筛选是按等级区间真筛，
       不是把卡片藏起来；③ 详情页的数与图都来自数据，缺的直说缺，不写概率。"""
    import json
    print("\n[11a] 副本列表筛选与每座本一页")
    dg = json.load(open(os.path.join(SRC, "data", "dungeons.json"), encoding="utf-8"))
    duns = (dg.get("newDungeons") or []) + (dg.get("classicDungeons") or [])
    raids = dg.get("raids") or []
    allrows = duns + raids
    art = json.load(open(os.path.join(SRC, "data", "art.json"), encoding="utf-8"))

    def rng(x):
        m = re.search(r"(\d+)\D+(\d+)", str(x.get("levelRange") or ""))
        return (int(m.group(1)), int(m.group(2))) if m else None

    new_duns = [x for x in duns if x.get("kind") == "new"]

    def nconf(x):
        # 等级区间按参考站卡片定稿、译名按官方来，这两类 2026-10-13 起界面上都不再摆"两说"
        # （数据里都还留着，见 test_dungeon_data 的反向断言）。只剩人数与英文原名两类。
        c = 0
        if x.get("partySizeAlt"):
            c += 1
        if x.get("nameEnClient"):
            c += 1
        return c

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/dungeons.html", wait_until="networkidle")
    page.wait_for_timeout(1500)
    g = page.evaluate("""() => ({
      stat: [...document.querySelectorAll('.dunstat b')].map(x => x.textContent.trim()),
      cards: document.querySelectorAll('#dlist .dcard2').length,
      faceConf: [...document.querySelectorAll('.dcard2 > .conf')].length,
      drawerConf: [...document.querySelectorAll('.dcard2 .drawer .conf')].length,
      notes: [...document.querySelectorAll('.dcard2 .drawer .note')].length,
      links: [...document.querySelectorAll('a.dstretch')].map(a => a.getAttribute('href')),
      opts: [...document.querySelectorAll('#dpick option')].map(o => o.value).filter(Boolean).length,
      chips: [...document.querySelectorAll('.fchip')].map(x => x.textContent.trim()),
      bands: [...document.querySelectorAll('#dlist .band b')].map(x => x.textContent.trim()) })""")
    check("页首四格读数等于数据现算",
          g["stat"] == [str(len(duns)), str(len(dg.get("newDungeons") or [])),
                        str(sum(len(x.get("bosses") or []) for x in allrows)),
                        str(sum(len(x.get("drops") or []) for x in allrows))],
          "页面 %s" % g["stat"])
    check("列表页一张卡都不漏，卡片数等于地下城数", g["cards"] == len(duns),
          "DOM %d / 数据 %d" % (g["cards"], len(duns)))
    check("卡面上不再直接压着分歧行（收进速览与详情页）", g["faceConf"] == 0,
          "卡面残留 %d 条" % g["faceConf"])
    exp_conf = sum(nconf(x) for x in duns) + sum(nconf(x) for x in raids)
    check("分歧一条都没少：抽屉里仍然按数据逐条摆", g["drawerConf"] == exp_conf,
          "抽屉 %d / 应有 %d" % (g["drawerConf"], exp_conf))
    exp_note = len([x for x in allrows if not x.get("clientActivityId")])
    check("客户端还排不到的本仍然逐座写明", g["notes"] == exp_note, "%d / %d" % (g["notes"], exp_note))
    check("每张卡都链向那一座的详情页", 
          len(g["links"]) == len(duns) + len(raids)
          and all(l.startswith("dungeon.html?d=") for l in g["links"]), str(g["links"][:2]))
    check("页首那座下拉能点到每一座地下城", g["opts"] == len(duns),
          "%d 个选项 / %d 座" % (g["opts"], len(duns)))
    check("筛选按钮上的数与数据一致",
          g["chips"] == ["全部 %d" % len(duns),
                         "无限新增 %d" % len(dg.get("newDungeons") or []),
                         "经典旧世 %d" % len(dg.get("classicDungeons") or [])], str(g["chips"]))
    check("地下城仍按十级一档分档", len(g["bands"]) >= 5 and any("40" in x for x in g["bands"]),
          str(g["bands"]))

    for lv in (18, 25, 44, 60):
        hit = len([x for x in duns if rng(x) and rng(x)[0] <= lv <= rng(x)[1]])
        page.fill("#dlv", str(lv))
        page.wait_for_timeout(450)
        got = page.evaluate("() => document.querySelectorAll('#dlist .dcard2').length")
        check("填 %d 级只剩等级区间对得上的本" % lv, got == hit, "页面 %d / 数据 %d" % (got, hit))
    page.click(".fchip[data-k='new']")
    page.wait_for_timeout(450)
    got_new = page.evaluate("""() => [...document.querySelectorAll('#dlist .dcard2 .dbn2-n')]
      .map(x => x.textContent.trim())""")
    exp_new = [x.get("nameCn") or x.get("nameEn") for x in duns
               if x.get("kind") == "new" and rng(x) and rng(x)[0] <= 60 <= rng(x)[1]]
    check("等级与来源两个筛是叠加的（60 级的无限新增本）", sorted(got_new) == sorted(exp_new),
          "%s / %s" % (got_new[:3], exp_new[:3]))
    page.click("#dlvc")
    page.wait_for_timeout(400)
    # 「清空等级」只管等级那格：来源筛还停在"无限新增"，两个控件互不越界
    check("清空等级只清等级、不动来源筛",
          page.evaluate("() => document.querySelectorAll('#dlist .dcard2').length") == len(new_duns),
          "页面 %d / 无限新增 %d" % (
              page.evaluate("() => document.querySelectorAll('#dlist .dcard2').length"), len(new_duns)))
    page.click(".fchip[data-k='all']")
    page.wait_for_timeout(400)
    check("切回全部后回到整份名单",
          page.evaluate("() => document.querySelectorAll('#dlist .dcard2').length") == len(duns))
    page.screenshot(path=os.path.join(SHOT_DIR, "dungeons-list-2026-10-13.png"))

    # 抽三座：有分歧的、有掉落的、还没有首领名单的（团本）
    samples = [x for x in allrows if x.get("id") in
               ("hall-of-thanes", "ragefire-chasm", "onyxias-lair")]
    check("抽样本在数据里都在", len(samples) == 3, str([x["id"] for x in samples]))
    for x in samples:
        did = x["id"]
        page.goto(base + "/dungeon.html?d=" + did, wait_until="networkidle")
        page.wait_for_timeout(1300)
        d = page.evaluate("""() => ({
          title: document.title, h1: document.querySelectorAll('#main h1').length,
          h1t: (document.querySelector('#main h1') || {}).innerText,
          bosses: document.querySelectorAll('.brow').length,
          items: document.querySelectorAll('.itemc').length,
          conf: document.querySelectorAll('#main .conf').length,
          note: document.querySelectorAll('#main .note').length,
          near: [...document.querySelectorAll('.dnear a')].map(a => a.getAttribute('href')),
          nearText: (document.querySelector('.dnear') || {}).innerText || '',
          noFace: [...document.querySelectorAll('.brow .bt')].filter(e => /没有这张头像/.test(e.innerText)).length,
          noLoot: [...document.querySelectorAll('.brow .bt')].filter(e => /掉落待补/.test(e.innerText)).length,
          broken: [...document.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0).length,
          heroArt: !!document.querySelector('.dunh img'),
          qRows: [...document.querySelectorAll('#dquests .qtab tbody tr')]
            .map(r => [...r.querySelectorAll('td')].map(c => c.innerText.replace(/\s+/g, ' ').trim())),
          qTables: document.querySelectorAll('#dquests table').length,
          qEmpty: (document.querySelector('#dquests') || {}).innerText || '',
          qConf: [...document.querySelectorAll('#dquests .conf')].map(e => e.innerText),
          pct: (document.querySelector('#main').innerText.match(/\\d+(\\.\\d+)?\\s*%/) || [])[0] || '',
          hasRoute: /路线/.test(document.querySelector('#main').innerText),
          shownRange: (((document.querySelectorAll('.dhfact b') || [])[1] || {}).innerText || '').trim(),
          fact: document.querySelectorAll('.dhfact > div').length })""")
        nm = x.get("nameCn") or x.get("nameEn")
        check("%s：标题与 H1 都是这一座，且只有一个 H1" % did,
              d["h1"] == 1 and nm in d["title"] and d["h1t"].strip() == nm,
              "%s / %s" % (d["title"], d["h1t"]))
        check("%s：首领栏数等于数据" % did, d["bosses"] == len(x.get("bosses") or []),
              "%d / %d" % (d["bosses"], len(x.get("bosses") or [])))
        check("%s：掉落格数等于数据" % did, d["items"] == len(x.get("drops") or []),
              "%d / %d" % (d["items"], len(x.get("drops") or [])))
        # 分歧有两个来源：这座本自己的（人数 / 英文原名 / 译名），加上任务经验值那份两说
        qe0 = json.load(open(os.path.join(SRC, "data", "dungeon-quests.json"), encoding="utf-8"))
        qxp = len([y for y in ((qe0.get("dungeons") or {}).get(did) or {}).get("quests", [])
                   if y.get("xpAlt") is not None])
        check("%s：分歧逐条摆着（本级别 + 任务经验两说）" % did,
              d["conf"] == nconf(x) + qxp, "%d / 应有 %d+%d" % (d["conf"], nconf(x), qxp))
        check("%s：没脸的直说没有这张头像，不拿别的脸凑" % did,
              d["noFace"] == len([b for b in (x.get("bosses") or []) if not b.get("portrait")]),
              "%d 个" % d["noFace"])
        check("%s：没有掉落的首领写掉落待补" % did,
              d["noLoot"] == len([b for b in (x.get("bosses") or [])
                                  if not any(y.get("bossId") == b.get("id") for y in (x.get("drops") or []))]),
              "%d 个" % d["noLoot"])
        check("%s：掉落不写百分比" % did, not d["pct"], d["pct"])
        # 兄弟本按等级区间排，中文名的先后两边排序规则不完全一样，所以这里不钉死第几位，
        # 只钉"链出去的两个本号都得在数据里"与"到档的那一侧必须直说，不留空位"。
        ids = {y["id"] for y in allrows}
        linked = [str(n).split("d=")[-1] for n in d["near"]]
        ends = bool(re.search("这一档的(第一座|最后一座)", d["nearText"]))
        check("%s：上一座 / 下一座链到真存在的本，到档那侧直说" % did,
              linked and all(l in ids for l in linked) and (len(linked) == 2 or ends),
              "%s / %s" % (linked[:2], d["nearText"][:22].replace("\n", " ")))
        # 「路线」2026-10-13 站主说暂时先不要，整块撤了。这条反过来钉住它不许自己长回来。
        check("%s：路线那一块已经撤掉，不许自己长回来" % did, not d["hasRoute"],
              "页面上又出现「路线」了" if d["hasRoute"] else "整页没有「路线」")
        check("%s：进本之前四格齐、区间显示的就是定稿后那个数" % did,
              d["fact"] == 4 and d["shownRange"] == (x.get("levelRange") or "待实测"),
              "四格 %d / 页面 %s 数据 %s" % (d["fact"], d["shownRange"], x.get("levelRange")))
        qe = json.load(open(os.path.join(SRC, "data", "dungeon-quests.json"), encoding="utf-8"))
        qd = (qe.get("dungeons") or {}).get(did) or {}
        qqs = qd.get("quests") or []
        exp_conf = len([y for y in qqs if y.get("xpAlt") is not None])
        exp_single = len([y for y in qqs if y.get("xpFrom") == "wowhead" or y.get("source") == "wowhead"])
        check("%s：任务那一节按数据摆，行数等于任务条数" % did,
              len(d["qRows"]) == len(qqs), "页面 %d 行 / 数据 %d 条" % (len(d["qRows"]), len(qqs)))
        check("%s：没有任务的本直说没有，不留空表" % did,
              (len(qqs) > 0) == ("还没有任务记录" not in d["qEmpty"]),
              "有 %d 条" % len(qqs) if qqs else d["qEmpty"][:34])
        check("%s：经验值两说的逐条写明两个都留着" % did,
              len(d["qConf"]) == exp_conf, "%d 处 / 数据 %d 条" % (len(d["qConf"]), exp_conf))
        # 站主 2026-10-13：讲资料出处与缺口的话不许上这一页。反向钉住，数据侧照旧留档。
        check("%s：任务表里不出现讲资料来源与缺口的话" % did,
              not re.search("单一来源|另一份资料|待补|未标|个版本", d["qEmpty"]),
              re.search("单一来源|另一份资料|待补|未标|个版本", d["qEmpty"]).group(0)
              if re.search("单一来源|另一份资料|待补|未标|个版本", d["qEmpty"]) else "干净")
        check("%s：合并同名任务后一条名字不重复出现" % did,
              len(set(r[0].split(" ")[0] for r in d["qRows"])) == len(d["qRows"]),
              "%d 行里有重名" % len(d["qRows"]))
        check("%s：任务与任务物品里不出现百分比" % did,
              not re.search(r"\d+(\.\d+)?\s*%", d["qEmpty"]), d["qEmpty"][:40])
        check("%s：图不坏、无脚本报错" % did, d["broken"] == 0 and not errs,
              "坏图 %d / 报错 %s" % (d["broken"], errs[:1]))
        page.screenshot(path=os.path.join(SHOT_DIR, "dungeon-%s.png" % did))
    ctx.close()

    # 直接打开详情页（没带本号）：给目录，不给空页
    ctx2 = browser.new_context(viewport={"width": 1440, "height": 1000})
    p2 = ctx2.new_page()
    p2.goto(base + "/dungeon.html", wait_until="networkidle")
    p2.wait_for_timeout(1300)
    pk = p2.evaluate("""() => ({ h1: document.querySelectorAll('#main h1').length,
      links: [...document.querySelectorAll('.dirl a')].map(a => a.getAttribute('href')),
      chars: document.querySelector('#main').innerText.length })""")
    check("不带本号打开详情页时给一张按等级段排好的目录",
          pk["h1"] == 1 and len(pk["links"]) == len(duns) and pk["chars"] > 100,
          "%d 条 / %d 字" % (len(pk["links"]), pk["chars"]))
    check("目录里每一条都指向某一座的详情页",
          all(l.startswith("dungeon.html?d=") for l in pk["links"]), str(pk["links"][:2]))
    p2.goto(base + "/dungeon.html?d=%E6%B2%A1%E8%BF%99%E5%BA%A7", wait_until="networkidle")
    p2.wait_for_timeout(1100)
    check("本号对不上时直说没收录，并给回列表的路",
          "这座本还没收录" in p2.inner_text("#main")
          and "dungeons.html" in p2.evaluate(
              "() => [...document.querySelectorAll('#main a')].map(a => a.getAttribute('href')).join(',')"))
    ctx2.close()


def test_raids(browser, base):
    """团本页：两份名单并列摆、四个读数与数据一致、筛选与深链接得住、条目进索引。"""
    print("\n[11b] 团本页（客户端排队条目 × 另一份名单）")
    import json
    qu = json.load(open(os.path.join(SRC, "data", "queue.json"), encoding="utf-8"))
    dg = json.load(open(os.path.join(SRC, "data", "dungeons.json"), encoding="utf-8"))
    idx = json.load(open(os.path.join(SRC, "data", "search.json"), encoding="utf-8"))
    rows = [x for x in qu["items"] if x["kind"] == "raid"]
    names = sorted({x["nameEn"] for x in rows})
    claimed = dg["raids"] or []
    linked_names = {x["nameEn"] for x in rows if x.get("matchedId")}
    ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/raids.html", wait_until="networkidle")
    page.wait_for_selector("#client tbody tr", timeout=15000)
    check("团本页无脚本报错", not errs, "; ".join(errs[:2]))
    g = page.evaluate("""() => {
      const rows=[...document.querySelectorAll('#client tbody tr')];
      return { rows: rows.length,
        names: rows.map(r=>r.querySelector('b').textContent.trim()),
        links: [...document.querySelectorAll('#client td a')].map(a=>a.getAttribute('href')),
        claimed: [...document.querySelectorAll('#claimed tbody tr')].length,
        noMatch: [...document.querySelectorAll('#claimed tbody tr')].filter(r=>/没有对应的排队条目/.test(r.textContent)).length,
        stats: [...document.querySelectorAll('.stat b')].map(x=>x.textContent.trim()),
        noArt: [...document.querySelectorAll('#claimed tbody tr')].filter(r => /没有这张载入图/.test(r.textContent)).length,
        missingCard: !!document.querySelector('#missing'),
        badges: document.querySelectorAll('.st.datamine_en').length,
        bands: [...document.querySelectorAll('#client .band b')].map(x=>x.textContent.trim()),
        h1: document.querySelectorAll('#main h1').length }; }""")
    check("一张 H1、按人数分档摆", g["h1"] == 1 and len(g["bands"]) >= 3, str(g["bands"]))
    check("表里行数 = 客户端团队条目去重后的名字数", g["rows"] == len(names),
          "%d / %d" % (g["rows"], len(names)))
    check("同一个名字只占一行", len(set(g["names"])) == g["rows"],
          "重复 %s" % [n for n in g["names"] if g["names"].count(n) > 1][:3])
    check("对得上的都链回副本页", len(g["links"]) == len(linked_names),
          "%d 条 / 数据 %d 座" % (len(g["links"]), len(linked_names)))
    check("链接都指向那一座的详情页", all(str(h).startswith("dungeon.html?d=") for h in g["links"]),
          str(g["links"][:2]))
    check("另一份名单自述的几座都在", g["claimed"] == len(claimed), "%d / %d" % (g["claimed"], len(claimed)))
    check("两边对不上的直说没有对应条目",
          g["noMatch"] == len([r for r in claimed if not r.get("clientActivityId")]), "%d 座" % g["noMatch"])
    # 载入图那一列：数据里有本地转存路径的才放图，没有的写"源站没有"，不放别的图凑
    arts = page.evaluate("""() => [...document.querySelectorAll('#claimed tbody tr')].map(r => {
      const i = r.querySelector('td.ich img');
      return i ? (i.getAttribute('src') || '') : null; })""")
    exp_arts = [c.get("art") or None for c in claimed]
    check("团本那一列按数据摆载入图，缺的直说缺",
          len(arts) == len(exp_arts) and all(a == e for a, e in zip(arts, exp_arts)),
          "页面 %s / 数据 %s" % (arts, exp_arts))
    exp_stats = [str(len(names)), str(len(claimed)),
                 str(len([r for r in claimed if r.get("clientActivityId")])),
                 str(len([r for r in claimed if r.get("nameCn")]))]
    check("四个规模读数等于数据现算", g["stats"] == exp_stats,
          "页面 %s / 数据 %s" % (g["stats"], exp_stats))
    check("缺载入图的那几座在表格里逐座写明，页尾不再挂缺口卡",
          not g["missingCard"] and g["noArt"] == len([e for e in exp_arts if not e]),
          "表里 %d 座写「没有这张载入图」/ 数据缺 %d 座"
          % (g["noArt"], len([e for e in exp_arts if not e])))
    check("团本页不再挂逐条出处标记（出处集中在溯源页）", g["badges"] == 0, "%d 枚" % g["badges"])
    page.fill("#rq", "Storm")
    page.wait_for_timeout(600)
    exp_storm = len([n for n in names if "storm" in n.lower()])
    one = page.evaluate("() => ({rows: document.querySelectorAll('#client tbody tr').length,"
                        " cnt: document.querySelector('#rcnt').textContent})")
    check("按英文名筛真的筛了", one["rows"] == exp_storm and one["cnt"].startswith(str(exp_storm)),
          json.dumps(one, ensure_ascii=False))
    page.fill("#rq", "中文词搜不到")
    page.wait_for_timeout(600)
    check("筛不到时说明这里只有英文原名", "中文定名" in page.inner_text("#client"),
          page.inner_text("#client")[:50].replace("\n", " "))
    page.close()
    page = ctx.new_page()
    page.goto("%s/raids.html?q=Molten" % base, wait_until="networkidle")
    page.wait_for_timeout(1300)
    exp_molten = len([n for n in names if "molten" in n.lower()])
    check("带词跳进来已经筛好", page.input_value("#rq") == "Molten" and
          page.evaluate("() => document.querySelectorAll('#client tbody tr').length") == exp_molten,
          page.input_value("#rq"))
    page.close()
    ctx.close()
    rdd = [it for it in idx["items"] if it[0] == "rdd"]
    check("团本条目进了全站搜索索引", len(rdd) >= len(names),
          "%d 条 / 名字 %d 个" % (len(rdd), len(names)))
    check("索引里团本板块指向这一页",
          (idx["meta"]["kinds"].get("rdd") or [None, ""])[1] == "raids.html",
          str(idx["meta"]["kinds"].get("rdd")))


def test_professions(browser, base):
    """专业与配方：配方表、采集点表、三个筛选器、没解析出来时的空态。"""
    print("\n[12] 专业与配方")
    import json
    pf = json.load(open(os.path.join(SRC, "data", "professions.json"), encoding="utf-8"))
    profs = pf["professions"]
    exp_rec = sum(len(p.get("recipes") or []) for p in profs)
    exp_node = sum(len(p.get("nodes") or []) for p in profs)

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/professions.html", wait_until="networkidle")
    page.wait_for_timeout(1600)
    check("专业页无脚本报错", not errs, "; ".join(errs[:2]))
    picks = page.evaluate("() => document.querySelectorAll('.picks .pick[data-p]').length")
    check("13 个专业都能选", picks == len(profs), "%d 个" % picks)
    first = page.evaluate("() => document.querySelectorAll('#pbody tbody tr').length")
    check("默认专业有配方表", first > 50, "%d 行" % first)
    page.fill("#pq", "治疗")
    page.wait_for_timeout(500)
    hit = page.evaluate("() => document.querySelectorAll('#pbody tbody tr').length")
    check("按名称筛选生效", 0 < hit < first, "「治疗」%d 行" % hit)
    page.fill("#pq", "")
    page.wait_for_timeout(400)
    page.fill("#plv", "1")
    page.wait_for_timeout(500)
    low = page.evaluate("() => document.querySelectorAll('#pbody tbody tr').length")
    page.fill("#plv", "300")
    page.wait_for_timeout(500)
    high = page.evaluate("() => document.querySelectorAll('#pbody tbody tr').length")
    check("按技能等级筛选生效", low < high and high >= first, "1 级 %d 行 / 300 级 %d 行" % (low, high))
    # M2-G（2026-10-16）：来源那一格现在有三层——参考站给的类别 / 哪几个商人卖 / 图纸从谁身上掉。
    # 新字段全部来自 XR 那份插件的快照，缺哪层就不写哪层，所以判据是"行数与数据条数对上"而不是"都有值"。
    page.fill("#plv", "")
    page.wait_for_timeout(400)
    vend_rows = page.evaluate("() => [...document.querySelectorAll('#pbody tbody tr')]"
                              ".filter(tr => (tr.children[3].innerText || '').indexOf('商人：') >= 0).length")
    exp_vend = len([x for x in (profs[0].get("recipes") or []) if (x.get("vendors") or [])])
    check("默认专业里写出来源商人的行数与数据一致", vend_rows == exp_vend,
          "%d 行 / 数据 %d 条" % (vend_rows, exp_vend))
    body = page.evaluate("() => document.querySelector('#pbody').innerText")
    check("配方来源那一格不写掉率与概率（红线）", "%" not in body and "概率" not in body)
    with_drop = next((p for p in profs if any(x.get("formulaDrops") for x in (p.get("recipes") or []))), None)
    if with_drop:
        page.evaluate("(pid) => { const el = document.querySelector('.picks .pick[data-p=\"' + pid + '\"]');"
                      " if (el) el.click(); }", with_drop["id"])
        page.wait_for_timeout(700)
        d_rows = page.evaluate("() => [...document.querySelectorAll('#pbody tbody tr')]"
                               ".filter(tr => (tr.children[3].innerText || '').indexOf('图纸掉落：') >= 0).length")
        exp_d = len([x for x in (with_drop.get("recipes") or []) if (x.get("formulaDrops") or [])])
        check("换到有图纸掉落的专业，那一段真写出来了", d_rows == exp_d and d_rows > 0,
              "%s：%d 行 / 数据 %d 条" % (with_drop["id"], d_rows, exp_d))
        names = page.evaluate(r"""() => [...document.querySelectorAll('#pbody tbody tr')]
          .map(tr => (tr.children[3].innerText || '')).filter(t => t.indexOf('图纸掉落：') >= 0)""")
        bad = [t for t in names if len(t) > 160]
        check("图纸掉落那一行是专名不是整段讲解", not bad, "%d 行过长" % len(bad))
        page.screenshot(path=os.path.join(SHOT_DIR, "professions-source.png"))
    page.fill("#plv", "")
    page.click("#pn")
    page.wait_for_timeout(500)
    onlynew = page.evaluate("() => document.querySelectorAll('#pbody tbody tr').length")
    tags = page.evaluate("() => document.querySelectorAll('#pbody .tag').length")
    check("只看无限新增生效", 0 < onlynew < high and tags >= onlynew,
          "%d 行、%d 个\"新\"标" % (onlynew, tags))
    page.click("#pn")
    page.wait_for_timeout(400)

    page.click(".pick[data-p=mining]")
    page.wait_for_timeout(800)
    mt = page.evaluate("() => document.querySelectorAll('#pbody table').length")
    mr = page.evaluate("() => document.querySelectorAll('#pbody tbody tr').length")
    bands = page.evaluate("() => [...document.querySelectorAll('#pbody .rbandh')]"
                          ".map(e => e.innerText.replace(/\\s+/g, ' ').trim())")
    check("采集型专业既有采集点表，配方又按技能档位分了箱",
          mt >= 2 and mr > 20 and len(bands) >= 2 and any("学徒" in b or "熟练" in b for b in bands),
          "%d 张表 %d 行 / 分箱 %s" % (mt, mr, json.dumps(bands, ensure_ascii=False)))
    # 分箱不许吞条目：各箱计数之和必须等于卡头报的配方总数
    pchk = page.evaluate("""() => { const h = [...document.querySelectorAll('#pbody h2')]
        .find(e => /配方/.test(e.innerText || ''));
      const total = +(((h || {}).innerText || '').match(/(\\d+) 条/) || [])[1];
      const bins = [...document.querySelectorAll('#pbody .rbandh b')].map(e => +e.innerText);
      return { total, sum: bins.reduce((a, b) => a + b, 0), bins }; }""")
    check("配方按档位分箱后一条都没丢", pchk["total"] and pchk["sum"] == pchk["total"],
          json.dumps(pchk, ensure_ascii=False))
    page.click(".pick[data-p=camping]")
    page.wait_for_timeout(700)
    empty = page.evaluate("() => (document.querySelector('.empty') || {}).textContent || ''")
    # 判据只认"它有没有把原因说出来"，不认具体措辞——这句话由生成器写，改一个字就红没有意义
    check("拆不出条目的专业写原因而不是留白",
          "拆" in empty and ("没" in empty or "未" in empty) and len(empty) >= 12, empty[:44])

    page.click(".pick[data-p=alchemy]")
    page.wait_for_timeout(900)
    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1500)
    icons = page.evaluate("""() => { const a = [...document.querySelectorAll('#pbody .liw img')];
      return { n: a.length, broken: a.filter(i => i.complete && i.naturalWidth === 0).length }; }""")
    check("配方与材料图标用上本地官方图", icons["n"] > 100 and icons["broken"] == 0,
          "%d 张图、坏 %d" % (icons["n"], icons["broken"]))
    pct = page.evaluate("() => (document.querySelector('#main').innerText.match(/\\d+(\\.\\d+)?\\s*%/g) || []).slice(0,3)")
    check("专业页不出现百分比", not pct, str(pct))
    src = page.evaluate("() => document.querySelectorAll('#main .src li').length")
    # 2026-10-12 站主决定：内容页不再挂逐条来源，出处集中在溯源页——这条改成反向断言。
    check("专业页没有来源块（出处只在溯源页）", src == 0, "%d 条来源残留" % src)
    page.screenshot(path=os.path.join(SHOT_DIR, "professions.png"))
    ctx.close()


def test_world(browser, base):
    """世界页：区域卡、稀有卡与小地图标记、书籍表、睡袋参数，逐块对着 world.json 数。"""
    print("\n[13] 世界线：区域 / 稀有 / 书籍 / 睡袋")
    import json
    w = json.load(open(os.path.join(SRC, "data", "world.json"), encoding="utf-8"))
    zones, rares, books = w["zones"], w["rares"], w["books"]
    exp_drops = sum(len(r.get("drops") or []) for r in rares)

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/world.html", wait_until="networkidle")
    page.wait_for_timeout(1800)
    check("世界页无脚本报错", not errs, "; ".join(errs[:2]))

    tabs = page.evaluate("() => document.querySelectorAll('.picks .pick[data-t]').length")
    check("四个面板都能选", tabs == 4, "%d 个" % tabs)
    zc = page.evaluate("() => document.querySelectorAll('#wbody .zcard').length")
    check("区域卡数量对得上数据", zc == len(zones), "%d 张（数据 %d 个区域）" % (zc, len(zones)))
    zstate = page.evaluate("""() => { const c = [...document.querySelectorAll('#wbody .zcard')];
      return { img: c.filter(x => x.querySelector('.zmap img')).length,
               honest: c.filter(x => x.querySelector('.zmap.none')).length,
               bad: [...document.querySelectorAll('#wbody .zmap img')].filter(i => i.complete && i.naturalWidth === 0).length }; }""")
    check("每张区域卡要么有本地图要么写明没切图", zstate["img"] + zstate["honest"] == zc and zstate["bad"] == 0,
          json.dumps(zstate))
    newtag = page.evaluate("""() => { const c = [...document.querySelectorAll('#wbody .zcard')]
        .filter(x => x.querySelector('.tag.new'));
      return { n: c.length, flight: c.filter(x => /飞行/.test(x.innerText)).length }; }""")
    # 「有没有飞行路线」回答的是玩家会问的事（这块地方能不能飞），不是讲我们数据过程的备注，
    # 所以这一行留在卡上；2026-10-12 撤掉的是素材出处角标与来源说明。
    check("无限新增区域带「新」角标，且卡上写清能不能飞",
          newtag["n"] == len([z for z in zones if z.get("isNew")]) and newtag["flight"] == newtag["n"],
          json.dumps(newtag))

    page.click('[data-t="rares"]')
    page.wait_for_timeout(1400)
    rc = page.evaluate("() => document.querySelectorAll('#wbody .rarecard').length")
    check("稀有卡数量对得上数据", rc == len(rares), "%d 张（数据 %d 个）" % (rc, len(rares)))
    marks = page.evaluate("""() => { const m = [...document.querySelectorAll('#wbody .zmark')];
      return { n: m.length, placed: m.filter(b => b.style.left && b.style.top).length }; }""")
    # 有坐标但**本地图它没切**的那些（GI 补进来的那些里有这种）画不出点，
    # 页面走"没切图"的兜底 + 文字坐标——所以期望值必须同时要求 mark 与 mapFile，
    # 否则会拿一个页面根本做不到的数去卡（2026-10-16 接 GI 稀有时就踩过这条）
    exp_marks = len([r for r in rares if r.get("mark") and r.get("mapFile")])
    no_map = len([r for r in rares if r.get("mark") and not r.get("mapFile")])
    honest = page.evaluate("() => document.querySelectorAll('#wbody .zmap.none').length")
    check("没切图的那几只走兜底：标「没切图」并写文字坐标，不是静默丢掉",
          honest >= no_map, "%d 处兜底 / 数据 %d 只缺点" % (honest, no_map))
    check("每个稀有标记点都按数据摆到图上", marks["n"] == exp_marks and marks["placed"] == exp_marks,
          "%d 个点，%d 个已定位（数据 %d）" % (marks["n"], marks["placed"], exp_marks))
    dl = page.evaluate("() => document.querySelectorAll('#wbody .rarecard .loot .loot-i').length")
    check("掉落条目数量对得上数据", dl == exp_drops, "稀有卡上 %d 件（数据 %d 件）" % (dl, exp_drops))
    body = page.evaluate("() => document.querySelector('#wbody').innerText")
    pct = body.count(chr(37))
    check("稀有面板正文不出现百分比", pct == 0, "出现 {0} 处".format(pct))
    nodrop = page.evaluate("() => document.querySelectorAll('#wbody .rarecard .note').length")
    check("没掉落的稀有写明而不是留白", nodrop >= len([r for r in rares if not (r.get("drops") or [])]),
          "%d 条说明" % nodrop)
    one = page.evaluate("() => { const b = document.querySelector('.picks .pick[data-z]:not([data-z=\"\"])'); b.click(); return b.dataset.z; }")
    page.wait_for_timeout(1200)
    only = page.evaluate("() => document.querySelectorAll('#wbody .rarecard').length")
    exp_only = len([r for r in rares if r["zone"] == one])
    check("按区域筛选生效", 0 < only < rc and only == exp_only, "「%s」%d 张（数据 %d）" % (one, only, exp_only))
    page.evaluate("() => document.querySelector('.picks .pick[data-z=\"\"]').click()")
    page.wait_for_timeout(1000)
    page.fill("#wq", "泽风")
    page.wait_for_timeout(900)
    sq = page.evaluate("() => document.querySelectorAll('#wbody .rarecard').length")
    check("搜索按区域名过滤", 0 < sq < rc, "「泽风」%d 张" % sq)
    page.fill("#wq", "")
    page.wait_for_timeout(800)
    drawer = page.evaluate("""() => { const b = document.querySelector('#wbody [data-r]'); b.click();
      const d = document.querySelector('#wbody .wdr.open');
      return { txt: d ? d.innerText : '', src: d ? d.querySelectorAll('.src').length : 0 }; }""")
    # 抽屉本身留着（里面是掉落清单，是数据），但"来源与核对"那一节已经移出内容页。
    check("稀有卡的掉落抽屉能展开，且抽屉里不再挂来源块",
          len(drawer["txt"]) > 40 and drawer["src"] == 0,
          "抽屉 %d 字 / 来源块 %d" % (len(drawer["txt"]), drawer["src"]))

    page.click('[data-t="books"]')
    page.wait_for_timeout(1500)
    bt = page.evaluate("() => document.querySelectorAll('#wbody table.bktab tbody tr').length")
    check("书籍表行数对得上数据", bt == len(books), "%d 行（数据 %d 本）" % (bt, len(books)))
    bicon = page.evaluate("""() => { const a = [...document.querySelectorAll('#wbody table img')];
      return { n: a.length, broken: a.filter(i => i.complete && i.naturalWidth === 0).length }; }""")
    check("书本地图标用本地图且不出现坏图", bicon["n"] > 20 and bicon["broken"] == 0, json.dumps(bicon))
    miss = page.evaluate("() => document.querySelectorAll('#wbody .chips .chipc').length")
    check("没给坐标的书单独列出", miss == len(w.get("booksMissing") or []), "%d 本" % miss)
    rew = page.evaluate("() => [...document.querySelectorAll('#wbody table tbody tr')]"
                        ".filter(r => /奖励待补/.test(r.innerText)).length")
    # 2026-10-12 站主决定：L0-L3 徽标退出内容页，"这一档上游没给奖励"改用取值「奖励待补」直接写在格子里。
    check("上游没给奖励的那档在格子里写「奖励待补」",
          rew == len([r for r in w["bookRewards"] if r.get("noReward")]),
          "%d 行（数据 %d 档）" % (rew, len([r for r in w["bookRewards"] if r.get("noReward")])))

    page.click('[data-t="bag"]')
    page.wait_for_timeout(1200)
    bag = page.evaluate("""() => { const rows = [...document.querySelectorAll('#wbody table.mtx tbody tr')];
      return { rows: rows.length, cols: rows.length ? rows[0].querySelectorAll('td').length : 0,
               l2: rows.filter(r => /待实测/.test(r.innerText)).length,
               camps: document.querySelectorAll('#wbody .rarecard').length }; }""")
    exp_camps = sum(len(c.get("places") or []) for c in (w["bagTool"].get("camps") or []))
    # 原来这张表有三列（机制项 / 记录值 / 分级徽标），分级徽标撤下后那一列整列删掉，
    # 不留空壳——所以判据从"每行都标待实测"改成"表只剩两列且行数是那五项"。
    check("睡袋机制数值表只剩机制项与记录值两列",
          bag["rows"] == 5 and bag["cols"] == 2 and bag["l2"] == 0, json.dumps(bag))
    check("营地点数量对得上数据", bag["camps"] == exp_camps, "%d 处（数据 %d）" % (bag["camps"], exp_camps))

    ext = page.evaluate("() => [...document.querySelectorAll('#main img')].filter(i => /^https?:/.test(i.getAttribute('src') || '')).length")
    check("世界页没有一张外链图片", ext == 0, "%d 张外链" % ext)
    page.screenshot(path=os.path.join(SHOT_DIR, "world-bag.png"))
    ctx.close()

    m = browser.new_context(viewport={"width": 375, "height": 780})
    mp = m.new_page()
    mp.goto(base + "/world.html", wait_until="networkidle")
    mp.wait_for_timeout(1500)
    mob = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
      const small = [...document.querySelectorAll('#wbody .zcard, #wbody .rarecard, .picks .pick, #wbody button.ghost')]
        .filter(b => { const r = b.getBoundingClientRect(); return r.width && r.height && r.height < 44; }).length;
      return { overflow: document.documentElement.scrollWidth > vw + 1, small: small }; }""")
    check("移动端世界页不横向溢出且点击目标够高", not mob["overflow"] and mob["small"] == 0, json.dumps(mob))
    mp.click('[data-t="rares"]')
    mp.wait_for_timeout(1400)
    mp.screenshot(path=os.path.join(SHOT_DIR, "world-rares-mobile.png"))
    m.close()


def test_home(browser, base):
    """首页：数字必须来自 scale.json，模块卡必须都指向真存在的页面。"""
    print("\n[14] 首页布局与数字来源")
    import json
    sc = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/index.html", wait_until="networkidle")
    page.wait_for_timeout(1500)
    check("首页无脚本报错", not errs, "; ".join(errs[:2]))
    # 2026-10-12 站主决定：首页 hero 不再放覆盖率条、四枚分级读数与"数据基线…"那行，
    # 也不放四条规模读数——这两条从"数字对不对"改成"这些读数不许回到首页"，
    # 覆盖率那条宽度断言挪到溯源页（见本函数末尾）。
    home_cov = page.evaluate("""() => ({covnum: document.querySelectorAll('.covnum').length,
      stats4: document.querySelectorAll('.stats4').length,
      cov: document.querySelectorAll('.cov').length,
      pill: document.querySelectorAll('#main .pill').length})""")
    check("首页不再有覆盖率读数与规模四格",
          home_cov == {"covnum": 0, "stats4": 0, "cov": 0, "pill": 0}, json.dumps(home_cov))
    check("首页导语不提来源与核对状态",
          page.evaluate("() => !/来源|核对|待实测|机翻/.test((document.querySelector('.hero .lead') || {}).innerText || '')"),
          page.evaluate("() => (document.querySelector('.hero .lead') || {}).innerText || ''"))
    # 首页的招牌动作从"点职业跳计算器"改成"点职业看真树"，所以断言也跟着换：
    # 格子数必须等于派生数据里那一系的节点数，空格补到整行，不许少画。
    pv = json.load(open(os.path.join(SRC, "data", "talent-preview.json"), encoding="utf-8"))
    first_cls = page.evaluate("() => [...document.querySelectorAll('#treecard [data-pvc]')][0].dataset.pvc")
    tree0 = pv["classes"][first_cls]["trees"][0]
    rows0 = max(n[0] for n in tree0["nodes"]) + 1
    strip = page.evaluate("""() => { const t = document.querySelector('#treecard');
      const a = [...t.querySelectorAll('.stripc')];
      return { n: a.length, tag: a.map(x => x.tagName), on: t.querySelectorAll('.stripc.on').length,
               nodes: t.querySelectorAll('.pnode').length, empty: t.querySelectorAll('.pempty').length,
               tabs: [...t.querySelectorAll('.pvpicks .pick')].map(x => x.innerText.replace(/\\n/g, ' ').trim()),
               meta: t.querySelector('.pvmeta').innerText.replace(/\\n/g, ' '),
               broken: [...t.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0).length,
               href: t.querySelector('.pnode').getAttribute('href'),
               cta: t.querySelector('.cta').getAttribute('href') }; }""")
    check("首页预览卡：九职业切换都在，且只有一个选中",
          strip["n"] == sc["classes"] and strip["on"] == 1 and set(strip["tag"]) == {"BUTTON"},
          json.dumps({"n": strip["n"], "on": strip["on"], "tag": strip["tag"][:1]}, ensure_ascii=False))
    check("首页预览画的格子与派生数据一致",
          strip["nodes"] == len(tree0["nodes"]) and
          strip["nodes"] + strip["empty"] == rows0 * 4,
          "%d 格 + %d 空 = %d 行 × 4（数据 %d 个天赋）" % (
              strip["nodes"], strip["empty"], rows0, len(tree0["nodes"])))
    check("预览没有加载失败的图标", strip["broken"] == 0, "坏图 %d" % strip["broken"])
    counts = [int(x) for x in re.findall(r"(\d+)(?!\d)", strip["meta"])]
    check("预览下方的状态计数加起来等于这棵系的节点数",
          sum(counts) == len(tree0["nodes"]), "%s（应 %d）" % (strip["meta"], len(tree0["nodes"])))
    # 换职业/换系都按派生数据核对，不假设"格子数一定变"（两棵系的节点数可能相同）
    page.click("#treecard [data-pvc]:nth-of-type(4)")
    page.wait_for_timeout(700)
    cid2 = page.evaluate("() => [...document.querySelectorAll('#treecard [data-pvc]')][3].dataset.pvc")
    after = page.evaluate("""() => { const t = document.querySelector('#treecard');
      return { nodes: t.querySelectorAll('.pnode').length, on: t.querySelector('.stripc.on').dataset.pvc,
               tabs: [...t.querySelectorAll('.pvpicks .pick b')].map(x => x.textContent),
               cta: t.querySelector('.cta').getAttribute('href') }; }""")
    t0b = pv["classes"][cid2]["trees"][0]
    check("点职业换树：选中态、系名与格子数都跟着这份职业的数据走",
          after["on"] == cid2 and after["tabs"] == [x["n"] for x in pv["classes"][cid2]["trees"]]
          and after["nodes"] == len(t0b["nodes"]) and ("c=" + cid2) in after["cta"],
          json.dumps(after, ensure_ascii=False))
    page.click("#treecard .pvpicks .pick:nth-of-type(2)")
    page.wait_for_timeout(700)
    t1 = pv["classes"][cid2]["trees"][1]
    t2 = page.evaluate("""() => ({ nodes: document.querySelectorAll('#treecard .pnode').length,
      on: document.querySelector('.pvpicks .pick.on b').textContent,
      tab: document.querySelector('.pnode').getAttribute('href') })""")
    check("点系切换第二棵：画的确实是那一棵",
          t2["on"] == t1["n"] and t2["nodes"] == len(t1["nodes"]) and "tree=1" in t2["tab"],
          json.dumps(t2, ensure_ascii=False))
    page.evaluate("() => document.querySelector('#treecard .pnode').click()")
    page.wait_for_timeout(1800)
    land = page.evaluate("""() => ({ url: location.href, q: (document.getElementById('tq') || {}).value,
      lit: [...document.querySelectorAll('.node')].filter(n => n.style.outline).length })""")
    check("点格子进计算器：带着职业、哪一系与天赋名，落地就描边",
          "tree=" in land["url"] and bool(land["q"]) and land["lit"] >= 1, json.dumps(land, ensure_ascii=False))
    page.go_back()
    page.wait_for_timeout(1400)
    mods = page.evaluate("""() => { const a = [...document.querySelectorAll('.mod')];
      return { n: a.length, nums: a.reduce((s, x) => s + x.querySelectorAll('.modn b').length, 0),
               pills: a.filter(x => x.querySelector('.pill')).length,
               foot: a.filter(x => x.querySelector('.modf')).length }; }""")
    # 2026-10-12 站主决定：板块卡底下那一行（分级徽标 + "整句直接抄官方"这类口径说明）撤了，
    # 卡里只留标题、板块归属和规模数字。
    # 2026-10-13 首页重排：入口卡 13 张（两组各 6 + 一张「这一版改了什么」大卡）
    check("13 张入口卡都带读数，且都不挂徽标与口径说明行",
          mods["n"] == 13 and mods["nums"] >= 13 and mods["pills"] == 0 and mods["foot"] == 0,
          json.dumps(mods))

    # ↓ 第五批（首页整合两家参考站）的判据：结构、素材、动效、角标
    st = page.evaluate("""() => {
      const cards = [...document.querySelectorAll('.mod')];
      const arts = [...document.querySelectorAll('.bgart')];
      const bad = (f) => !f || /^https?:/.test(f) || f.indexOf('img/art/') !== 0;
      return {
        groups: [...document.querySelectorAll('.grphead h2')].map(e => e.innerText),
        perGroup: [...document.querySelectorAll('.grphead')].map(g => {
          let n = 0, e = g.nextElementSibling;
          while (e && !e.classList.contains('grphead')) { n += e.querySelectorAll('.mod').length; e = e.nextElementSibling; }
          return n;
        }),
        two: [...document.querySelectorAll('.two > section')].map(e => (e.querySelector('h2') || {}).innerText),
        clsrow: [...document.querySelectorAll('.cls9 a')].map(a => a.getAttribute('href')),
        artFiles: arts.map(e => (((e.getAttribute('style') || '').match(/url\(([^)]+)\)/) || [])[1] || '')),
        artBad: arts.filter(e => bad(e.style && (e.style.backgroundImage || '').indexOf('img/art/') < 0)).length,
        artCards: cards.filter(c => c.querySelector('.bgart')).length,
        titles: [...document.querySelectorAll('.mod h2, .two h2')].map(e => e.innerText),
        four: [...document.querySelectorAll('.four b')].map(e => +e.innerText),
        bar: (() => { const b2 = document.querySelector('#treecard .bar i');
          return b2 ? { w: b2.style.width, aria: (b2.parentElement.getAttribute('aria-label') || '') } : null; })(),
        navItems: [...document.querySelectorAll('nav.main a')].map(e => e.innerText.trim()),
        badge: [...document.querySelectorAll('nav.main .nb')].map(e => ({
          t: e.textContent, on: e.parentElement.textContent.trim().slice(0, 6),
          aria: e.getAttribute('aria-label'), title: e.getAttribute('title') })),
        heroLinks: [...document.querySelectorAll('.clsrow a')].filter(a => /talent\.html\?c=/.test(a.getAttribute('href'))).length,
        // 1440px 实拍发现：树占掉 360px 后右栏只剩 176px，职业格里的「战士」会被拆成两行
        stripH: [...document.querySelectorAll('.two .stripc b')].map(e => Math.round(e.getBoundingClientRect().height)),
        railW: (() => { const r = document.querySelector('.two .tright');
          return r ? Math.round(r.getBoundingClientRect().width) : 0; })(),
        dunRows: [...document.querySelectorAll('.two .dunrow')].map(e => e.innerText.replace(/\\s+/g, ' ')),
        ctaGap: (() => { const cs = [...document.querySelectorAll('.card a.cta')];
          const pair = cs.filter(a => a.previousElementSibling && a.previousElementSibling.matches('a.cta'))[0];
          return pair ? parseFloat(getComputedStyle(pair).marginLeft) : -1; })()
      };
    }""")
    # 2026-10-13：三条线（角色线/世界线/工具线）与「自经典旧世以来的改动」那组读数撤掉，
    # 首页只剩两组入口卡；改动那块改成一张入口卡 + 一行站方口径小入口。
    check("首页两组入口卡各 6 张，不再有第三条线与改动读数分组",
          st["groups"] == ["角色与职业", "世界与冒险"] and st["perGroup"][:2] == [6, 6],
          json.dumps({"g": st["groups"], "n": st["perGroup"]}, ensure_ascii=False))
    dup = [x for x in set(st["titles"]) if st["titles"].count(x) > 1]
    check("「最常用的两个」是天赋预览与副本，且九张卡不重复它们",
          st["two"] == ["先看一棵真树，再进计算器", "副本手册"] and not dup,
          json.dumps({"two": st["two"], "重复": dup}, ensure_ascii=False))
    # 2026-10-12 按稿改版：职业入口从 hero 里搬出来，成为 hero 之下独立一节（.cls9）。
    # 判据不变——9 个、只进那一职业的页、不在首页切树；只是找的元素换了。
    check("职业入口是 9 个链接、只进那一职业页不做切树",
          len(st["clsrow"]) == 9 and all("talent.html?c=" in x for x in st["clsrow"]),
          json.dumps(st["clsrow"][:2], ensure_ascii=False))
    check("卡片背景图全部是本地已转存素材，没有热链",
          len(st["artFiles"]) > 0 and all(f.startswith("img/art/") for f in st["artFiles"]),
          json.dumps(st["artFiles"][:3], ensure_ascii=False))
    # 用户实拍："卡片背景要的是图片，不是把图标当背景"。现在每张入口卡都必须带一张
    # art/ 下已转存的真图（13 张卡 + 2 张主推卡 = 15 层背景），一张都不许多。
    check("13 张入口卡每张都带本地原画背景，加两张主推卡共 15 层",
          len(st["artFiles"]) == 15 and st["artCards"] == 13,
          "背景层 %d 张 / 模块卡带背景 %d 张" % (len(st["artFiles"]), st["artCards"]))
    # 改动四格与"全部 vs 四格之和"的对照行搬去动态页（首页只留入口），
    # 和等于上游自报 changed 那条断言跟着挪到 test_updates_rank。
    check("首页不再有改动四格（搬到动态页 #k1）",
          st["four"] == [], json.dumps(st["four"]))
    # 2026-10-12 站主决定：天赋预览卡下面那条"名称与官网中文一致 462 / 466"的进度条与
    # 讲数据出处的说明段一起移出内容页（这条读数仍在溯源页）。
    check("天赋预览卡不再挂覆盖率进度条与出处说明段",
          st["bar"] is None and page.evaluate(
              "() => !document.querySelector('#treecard .note')"),
          json.dumps({"bar": st["bar"]}, ensure_ascii=False))
    # 角标不是手写的：app.js 拿 scale.navNew（「本站更新」最新一天的板块标签）去对导航项名字，
    # 对得上才画、对不上就不画（app.js 原话："标签对不上导航项名字就不画，不硬凑"）。
    # 2026-10-16 起这条不能再要求"至少一枚"：物品库只有新站有，旧站导航里根本没这一项，
    # 那一轮更新在旧站首页就该画 0 枚——为了出角标去凑一个对得上的标签才是错的。
    # 改成按同一条规则算期望：应画的 = 导航项名字 ∩ 最新一批标签，数量与名字都必须等。
    nav_new = sc.get("navNew") or []
    nav_labels = [re.sub(r"新$", "", str(x)).strip() for x in st["navItems"] if str(x).strip()]
    expect = sorted(l for l in set(nav_labels) if l in set(nav_new))
    bad_labels = sorted({re.sub(r"新$", "", str(x["on"]).strip()) for x in st["badge"]})
    check("导航角标只挂在最新一批更新对得上的项上，且除颜色外带可读名",
          bad_labels == expect and len(st["badge"]) == len(expect)
          and all(x["t"] == "新" and x["aria"] and x["title"] for x in st["badge"]),
          json.dumps({"角标项": bad_labels, "应画": expect,
                      "最新一批标签": nav_new}, ensure_ascii=False))
    # 1440px 实拍才会发现：树按 360px 摆时右栏只剩 176px，三列职业格把「战士」拆成两行
    check("预览卡右栏够宽，职业名不被拆成两行",
          st["railW"] >= 200 and st["stripH"] and max(st["stripH"]) <= 20,
          json.dumps({"右栏": st["railW"], "名块高": sorted(set(st["stripH"]))[:4]}))
    check("副本卡把每一座无限新增本都列出来，没首领名单的写「首领待补」",
          len(st["dunRows"]) == sc["dungeonsNew"] and
          all(("首领待补" in r) or re.search(r"\d+ 首领", r) for r in st["dunRows"]),
          "%d 行 / 数据 %d 座：%s" % (len(st["dunRows"]), sc["dungeonsNew"],
                                     [r for r in st["dunRows"] if "待补" in r][:1]))
    check("同一张卡里两个 CTA 之间有空隙，不挤成一句", st["ctaGap"] > 0, "margin-left %s" % st["ctaGap"])
    # 旧站这段模板漏了一个 </div>，浏览器自动补的位置让问答入口被框进读数卡里（191px），
    # Vue 那份是正常闭合（105px）——两栈对拍查文本查不出来，这里按结构钉住。
    # 稿子的 hero 右侧只放一枚读数牌；两个出口按钮排在正文下方，不进读数框
    check("hero 的读数框只框住倒计时，出口按钮在框外",
          page.evaluate("() => { const cd = document.querySelector('.heros .cd');"
                        "return !!cd && !cd.querySelector('a') && cd.children.length === 2 &&"
                        "!!document.querySelector('.hero .herobtns a.cta') &&"
                        "!document.querySelector('.heros a'); }"),
          "读数框里混进了链接，或出口按钮没排在框外")
    css = open(os.path.join(SRC, "css", "app.css"), encoding="utf-8").read()
    flat = css.replace(" ", "").replace("\n", "")
    check("卡片动效只有三处且都能关（hover 抬升 / 背景微缩放 / reduced-motion 归零）",
          ".mod:hover" in css and "prefers-reduced-motion" in css and
          "transform:none" in flat[flat.index("prefers-reduced-motion"):],
          "缺 hover 动效或缺可关声明")
    # 角标不能把导航撑出第二行。判据从"所有 .in 子块 top 相同"改成"所有入口 top 相同"——
    # 上下两级后，没有组名的「首页」块天然比别的块矮，比子块 top 会把这种正常差异当成换行。
    check("角标不占导航宽度：整条导航仍是一行",
          page.evaluate("() => new Set([...document.querySelectorAll('nav.main a.nl')]"
          ".map(a => Math.round(a.getBoundingClientRect().top))).size") == 1,
          "导航换行了")
    hrefs = page.evaluate("""() => [...document.querySelectorAll('.mod, .chipsrow a, .hero .cta')]
      .map(a => (a.getAttribute('href') || '').split('#')[0].split('?')[0].replace('.html', ''))
      .filter(h => h && !/^https?:/.test(h))""")
    unknown = sorted({h for h in hrefs if h not in PAGES})
    check("首页所有入口都指向真存在的页", not unknown, "指向不存在的页：%s" % (unknown or "无"))
    # 这几个数原来写死在断言里（'1055' 与 '366'）：上游一更新就红，红了之后人就去改断言，
    # 等于把卡口变成摆设。改成从 scale.json 现取，页面漏渲染哪个数就报哪个。
    need = [str(sc["recipes"]), str(sc["drops"]), str(sc["talentNodes"]),
            str(sc["bosses"]), str(sc["changes"])]
    hard = page.evaluate("""(need) => { const t = document.querySelector('#main').innerText;
      return need.filter(n => !t.includes(n)); }""", need)
    check("首页规模数字都渲染出来了（要渲染的数从 scale.json 现取）", not hard, "缺 %s" % (hard or "无"))
    nd = page.evaluate("() => document.querySelectorAll('.flowrow').length")
    # 「这一站刻意不做的」那张卡按站主决定撤了（它是讲我们取舍的说明，不是玩家要查的东西），
    # 所以这里只剩「最新动态」两节摘要各三条：判据从 >=9 改成 >=6，并且钉住那张卡不再回来。
    check("首页「最新动态」两节摘要都在，「刻意不做的」那张卡不再回来",
          nd >= 6 and "刻意不做" not in page.evaluate(
              "() => document.querySelector('#main').innerText"), "%d 行" % nd)
    foot = page.evaluate("() => document.querySelector('#foot').innerText")
    # 2026-10-12 站主决定：页脚那条覆盖率与"数据版本 · 核对于"移出内容页，只留免责句 + 两栏入口。
    # 免责句是合规固定项，不能跟着一起删，所以这里两头都钉住。
    check("页脚保留免责句，且不再挂覆盖率与核对日期",
          ("与暴雪娱乐及网易无关" in foot) and ("L0" not in foot) and ("核对于" not in foot),
          foot.replace("\n", " ")[-60:])
    pp = ctx.new_page()
    pp.goto(base + "/provenance.html", wait_until="networkidle")
    pp.wait_for_timeout(1200)
    pt = pp.evaluate("() => document.querySelector('#main').innerText")
    ok = ("%d条对外词条" % sc["pubTotal"]) in pt.replace(" ", "") and str(sc["coverageTotal"]) in pt
    check("溯源页两个口径都写明且与 scale.json 一致", ok,
          "应含「%d 条对外词条」与全站 %s" % (sc["pubTotal"], sc["coverageTotal"]))
    pp.close()
    page.screenshot(path=os.path.join(SHOT_DIR, "home-redesign.png"))
    ctx.close()

    m = browser.new_context(viewport={"width": 375, "height": 780})
    mp = m.new_page()
    mp.goto(base + "/index.html", wait_until="networkidle")
    mp.wait_for_timeout(1300)
    mob = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
      const h1e = document.querySelector('h1'); const h1 = h1e.getBoundingClientRect();
      const h1fs = parseFloat(getComputedStyle(h1e).fontSize) || 0;
      const small = [...document.querySelectorAll('.stripc, .chipsrow a, .mod, .hero .cta')]
        .filter(b => { const r = b.getBoundingClientRect(); return r.height && r.height < 44; }).length;
      return { overflow: document.documentElement.scrollWidth > vw + 1, h1w: Math.round(h1.width),
               h1h: Math.round(h1.height), h1fs: Math.round(h1fs), small: small }; }""")
    # 判据本意是"标题别被挤成一字一行"，所以按行数算而不是按绝对像素：
    # 改版后 H1 从 17px 提到移动端 28px，两行是正常排版，三行才算被挤。
    lines = mob["h1h"] / max(mob["h1fs"], 1) / 1.18
    check("移动端首页不溢出、标题不超过两行",
          not mob["overflow"] and mob["h1w"] > 280 and lines <= 2.2,
          "高 %dpx / 字号 %dpx ≈ %.1f 行" % (mob["h1h"], mob["h1fs"], lines))
    check("移动端首页点击目标 ≥44px", mob["small"] == 0, "%d 个偏小" % mob["small"])
    mp.screenshot(path=os.path.join(SHOT_DIR, "home-redesign-mobile.png"), full_page=True)
    m.close()


def test_updates_rank(browser, base):
    """动态页与排行页：改动清单只许有名称与类别，排行数字必须与 scale.json 逐项一致。"""
    print("\n[15] 最新动态与资料完整度排行")
    import json
    ch = json.load(open(os.path.join(SRC, "data", "changes.json"), encoding="utf-8"))
    cl = json.load(open(os.path.join(SRC, "data", "releases.json"), encoding="utf-8"))
    S = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    items = ch["items"]

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/updates.html", wait_until="networkidle")
    page.wait_for_timeout(2200)
    check("动态页无脚本报错", not errs, "; ".join(errs[:2]))
    cards = page.evaluate("() => ['k0','k1','k2'].filter(id => document.getElementById(id)).length")
    check("动态页三块都在（官方时间点 / 客户端改动 / 本站更新）", cards == 3, "%d 块" % cards)
    rows = page.evaluate("() => document.querySelectorAll('#chbody tbody tr').length")
    cnt = page.evaluate("() => document.querySelector('#ccnt').textContent")
    check("改动清单默认列到上限并报出全量", rows == 400 and str(len(items)) in cnt,
          "%d 行 / 计数 %s（数据 %d 条）" % (rows, cnt, len(items)))
    page.select_option("#ck", "removed")
    page.wait_for_timeout(900)
    rm = page.evaluate("() => document.querySelectorAll('#chbody tbody tr').length")
    check("按「移除」筛出的条数与卡口数一致", rm == S["changesRemoved"], "%d 条（scale %s）" % (rm, S["changesRemoved"]))
    page.select_option("#ck", "all")
    page.select_option("#cw", "spell")
    page.wait_for_timeout(900)
    sp = page.evaluate("() => parseInt(document.querySelector('#ccnt').textContent, 10)")
    check("只看法术 = 420 条", sp == S["changesSpells"], "%d（scale %s）" % (sp, S["changesSpells"]))
    page.select_option("#cw", "all")
    page.evaluate("() => document.querySelector('[data-c=hunter]').click()")
    page.wait_for_timeout(900)
    hu = page.evaluate("() => parseInt(document.querySelector('#ccnt').textContent, 10)")
    exp_hu = len([x for x in items if x["classId"] == "hunter"])
    check("按职业筛与数据一致", hu == exp_hu, "猎人 %d（数据 %d）" % (hu, exp_hu))
    body = page.evaluate("() => document.querySelector('#main').innerText")
    # 红线断言：改动清单只该有名称与类别，出现 tooltip 句式就是文本没删干净
    leaky = [w for w in ["使你的", "造成", "点伤害", "冷却时间", "生命值"] if w in body]
    check("动态页不出现技能描述句", not leaky, "疑似漏进句子：%s" % (leaky or "无"))
    tech = dev_word_hits(body)
    check("动态页正文没有面向开发的词", not tech, str(tech))
    logs = page.evaluate("() => document.querySelectorAll('#k2 .flowrow').length")
    check("本站更新条数与数据一致", logs == len(cl["items"]), "%d 条（数据 %d）" % (logs, len(cl["items"])))
    page.screenshot(path=os.path.join(SHOT_DIR, "updates.png"))
    ctx.close()

    c2 = browser.new_context(viewport={"width": 1440, "height": 1000})
    rp = c2.new_page()
    rp.goto(base + "/rank.html", wait_until="networkidle")
    rp.wait_for_timeout(1500)
    rk = rp.evaluate("""() => [...document.querySelectorAll('.ranktab tbody tr')].map(tr =>
      [...tr.querySelectorAll('td')].map(td => td.innerText.trim()))""")
    data = S["classRank"]
    check("排行九行且名次与 scale.json 一致",
          len(rk) == len(data) == 9 and all(int(r[0]) == d["place"] for r, d in zip(rk, data)),
          "%d 行" % len(rk))
    ok_cells = all(int(r[2]) == d["official"] and int(r[3]) == d["datamine"] and int(r[4]) == d["total"]
                   for r, d in zip(rk, data))
    check("排行每一列数字都来自数据现算", ok_cells,
          "首行 页面 %s/%s/%s vs 数据 %s/%s/%s" % (rk[0][2], rk[0][3], rk[0][4],
                                            data[0]["official"], data[0]["datamine"], data[0]["total"]))
    rt = rp.evaluate("() => document.querySelector('.ranktab tbody tr td:last-child').innerText")
    check("排行覆盖率与页脚口径同源", ("%s%%" % data[0]["share"]) in rt, "首行显示 %s，数据 %s%%" % (rt, data[0]["share"]))
    rtxt = rp.evaluate("() => document.querySelector('#main').innerText")
    check("排行页写明不是强度排行",
          ("不是强度排行" in rtxt or "不回答哪个职业强" in rtxt) and "战斗日志" in rtxt,
          "缺免责声明" if "强度" not in rtxt else "已写明")
    rp.screenshot(path=os.path.join(SHOT_DIR, "rank.png"))
    c2.close()

    hp = browser.new_context(viewport={"width": 1440, "height": 1000})
    hpg = hp.new_page()
    hpg.goto(base + "/index.html", wait_until="networkidle")
    hpg.wait_for_timeout(1800)
    hb = hpg.evaluate("""() => { const dyn = [...document.querySelectorAll('.card')]
          .find(x => /最新动态/.test((x.querySelector('h2') || {}).innerText || ''));
      return { rows: dyn ? dyn.querySelectorAll('.flowrow').length : 0,
               links: dyn ? [...dyn.querySelectorAll('a')].map(a => a.getAttribute('href') || '') : [],
               note: dyn ? (dyn.querySelector('.note') || {}).innerText || '' : '',
               four: document.querySelectorAll('#main .four b').length,
               chgl: document.querySelectorAll('#main .chgl').length }; }""")
    check("首页动态卡有时间点与两个入口", hb and hb["rows"] >= 4
          and any("updates.html" in x for x in hb["links"])
          and any("rank.html" in x for x in hb["links"]), str(hb))
    check("动态卡写明这三件事怎么分开", hb and "三件事分开说" in hb["note"], (hb or {}).get("note", "")[:40])
    # 2026-10-13 用户：首页那些读数像数据变动明细，不像资料站入口——四格与对照行搬到动态页，
    # 首页一张入口卡都不许多带读数（这条钉住别再搬回来）。
    check("首页不再有改动四格", hb["four"] == 0, "首页还有 %d 格" % hb["four"])

    hpg.goto(base + "/updates.html", wait_until="networkidle")
    hpg.wait_for_timeout(1800)
    k1 = hpg.evaluate("""() => { const c = document.querySelector('#k1'); if (!c) return null;
      return { four: c.querySelectorAll('.four b').length,
               fourtxt: [...c.querySelectorAll('.four b')].map(b => b.innerText.trim()),
               kv: c.querySelectorAll('.kv').length,
               head: ((c.querySelector('h2') || {}).innerText || '').replace(/\s+/g, ' ').slice(0, 30),
               text: c.innerText.replace(/\s+/g, ' ') }; }""")
    check("改动四格挂在动态页「客户端改动清单」那张卡上，且带对照行",
          k1 and k1["four"] == 4 and k1["kv"] >= 1 and all(x.isdigit() for x in k1["fourtxt"])
          and "客户端改动清单" in k1["head"], json.dumps(k1 and {"head": k1["head"], "four": k1["four"],
                                                                "kv": k1["kv"]}, ensure_ascii=False))
    # 四格之和要等于上游自报的 changed——这个数从 changes.json 的 upstreamCounts 现读，
    # 不写死常数：2026-10-11 重抓后上游自报从 751 变成 753，写死的断言当时就红了。
    self_reported = json.load(open(os.path.join(SRC, "data", "changes.json"),
                                   encoding="utf-8"))["meta"]["upstreamCounts"]["changed"]
    check("改动四格加起来等于来源站自报的 changed %d" % self_reported,
          k1 and sum(int(x) for x in k1["fourtxt"]) == self_reported,
          "%s 合计 %d / 上游自报 %d" % (k1 and k1["fourtxt"], k1 and sum(int(x) for x in k1["fourtxt"]),
                                       self_reported))
    # 全部条目与四格之和同屏出现，不解释清楚就是自己打脸
    sc = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    _sum = sum(int(x) for x in (k1 or {}).get("fourtxt") or [])
    check("改动卡自己解释清「全部 %d 条」与「四格之和 %d」差在哪" % (sc["changes"], _sum),
          k1 and str(_sum) in k1["text"] and str(sc["changes"]) in k1["text"] and
          str(sc["changesTalents"]) in k1["text"] and "本身没变" in k1["text"],
          str(k1 and k1["text"][:150]))
    hp.close()

    m = browser.new_context(viewport={"width": 375, "height": 780})
    mp = m.new_page()
    mp.goto(base + "/updates.html", wait_until="networkidle")
    mp.wait_for_timeout(1800)
    mob = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
      const small = [...document.querySelectorAll('#chbody .pick, .field select, .field input, #main a.cta, .chipsrow a')]
        .filter(b => { const r = b.getBoundingClientRect(); return r.height && r.height < 44; }).length;
      return { overflow: document.documentElement.scrollWidth > vw + 1, small: small }; }""")
    check("移动端动态页不溢出且控件够高", not mob["overflow"] and mob["small"] == 0, json.dumps(mob))
    mp.screenshot(path=os.path.join(SHOT_DIR, "updates-mobile.png"))
    m.close()



def test_race_icon(browser):
    """天裔种族小图标（2026-10-20 I02，站主特批用插件目录那张转存的图）。
       钉四件事：① 种族页那天裔的小图标真的解码出来了；② 传承页页头那张**大图**
       没有被 64px 的小图顶掉；③ 法术书与术语页的种族格也吃到这张图；
       ④ 这几页不许出现破图。小图标走 art.json 的 raceIcons，
       与 races（大图）是两个键——混用一个键迟早有一页被拿错尺寸。"""
    print("\n[6g] 天裔小图标与大图分开")
    import json
    if not app_up(browser):
        return
    art = json.load(open(os.path.join(SRC, "data", "art.json"), encoding="utf-8"))
    small = (art.get("raceIcons") or {}).get("skyborne") or ""
    big = (art.get("races") or {}).get("skyborne") or ""
    small_dir = small.rsplit("/", 1)[0] + "/"    # 按目录认小图标：两张图都叫 skyborne.webp
    check("art.json 里小图标与大图是两个不同的键（64px 不许当页头原画）",
          bool(small) and bool(big) and small != big
          and "raceicons" in small and small.endswith(".webp") and not small.endswith(".webp?"),
          "小 %s / 大 %s" % (small, big))
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.on("console", lambda m: errs.append(m.text[:120]) if m.type == "error" else None)

    def probe(url, sel=None):
        page.goto(APP_BASE + url, wait_until="networkidle")
        page.wait_for_timeout(2200)
        page.evaluate("() => { const h = document.body.scrollHeight;"
                      "for (let y = 0; y <= h; y += 500) { window.scrollTo(0, y); } window.scrollTo(0, 0); }")
        page.wait_for_timeout(700)
        return page.evaluate("""(want) => {
          const src = (i) => i.currentSrc || i.src || '';
          const imgs = [...document.querySelectorAll('img')];
          // 按**目录**分，不按文件名：小图标与大图原画都叫 skyborne.webp，
          // 上一版按文件名匹配，传承页那条把大图也算成了"小图误用"——是断言的错不是页面的错。
          const mine = imgs.filter(i => src(i).indexOf(want) >= 0);
          return { small: mine.length,
                   smallOk: mine.filter(i => i.complete && i.naturalWidth >= 32).length,
                   smallW: mine.map(i => i.naturalWidth)[0] || 0,
                   big: imgs.filter(i => src(i).indexOf('art/races/skyborne') >= 0).length,
                   broken: imgs.filter(i => i.complete && !i.naturalWidth)
                     .map(i => src(i).split('/').slice(-2).join('/')).slice(0, 4) }; }""",
            small_dir)

    r = probe("/#/races")
    check("种族页天裔那几处小图标真解码出来了（不是自绘块也不是破图）",
          r["small"] >= 2 and r["smallOk"] == r["small"] and r["smallW"] >= 32 and not r["broken"],
          "%d 处，解码 %d 处，原图宽 %dpx，破图 %s" % (r["small"], r["smallOk"], r["smallW"], r["broken"] or "无"))
    page.screenshot(path=os.path.join(SHOT_DIR, "app-raceicon-skyborne.png"))
    lg = probe("/#/legacy")
    check("传承页页头仍然用那张大图原画，没被 64px 小图顶掉",
          lg["big"] >= 1 and lg["small"] == 0 and not lg["broken"],
          "页头大图 %d 张 / 小图误用 %d 张 / 破图 %s" % (lg["big"], lg["small"], lg["broken"] or "无"))
    for url, label in (("/#/skills", "法术书"), ("/#/glossary", "术语速查")):
        g = probe(url)
        check("%s 的种族格也吃到这张小图标，且整页无破图" % label,
              g["small"] >= 1 and g["smallOk"] == g["small"] and not g["broken"],
              "%d 处解码 %d 处 / 破图 %s" % (g["small"], g["smallOk"], g["broken"] or "无"))
    p = probe("/#/provenance")
    prov = page.evaluate("""(want) => {
      const t = document.body.innerText || '';
      return { hasPlugin: t.indexOf('XR_DungeonGuide') >= 0,
               hasFile: t.indexOf(want) >= 0,
               notOfficial: t.indexOf('不算官方已核素材') >= 0,
               hasHash: /[0-9a-f]{12}/.test(t),
               hasRollback: t.indexOf('要撤回') >= 0,
               kinds: (t.match(/种族小图标/g) || []).length }; }""", small)
    check("溯源页点名了这张插件图：插件名 + 文件路径 + 校验和 + '不算官方已核素材' + 撤回方案",
          prov["hasPlugin"] and prov["hasFile"] and prov["notOfficial"]
          and prov["hasHash"] and prov["hasRollback"] and prov["kinds"] >= 1,
          "插件名 %s / 路径 %s / 非官方声明 %s / 校验和 %s / 撤回 %s / 读到 %d 条" % (
              prov["hasPlugin"], prov["hasFile"], prov["notOfficial"],
              prov["hasHash"], prov["hasRollback"], prov["kinds"]))
    check("这几页没有脚本报错", not errs, "; ".join(errs[:2]) or "干净")
    mctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    mp = mctx.new_page()
    mp.goto(APP_BASE + "/#/races", wait_until="networkidle")
    mp.wait_for_timeout(2200)
    # 手机那一屏更长，不滚到底 lazy 图压根不加载——上一版报"10 处只解码 4 处"就是这个原因，
    # 那是没验到，不是解码失败。滚完再量，并把"还没加载完"单独报出来。
    mp.evaluate("""async () => { const h = document.body.scrollHeight;
      for (let y = 0; y <= h; y += 400) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 150)); }
      window.scrollTo(0, 0); }""")
    mp.wait_for_timeout(1200)
    m = mp.evaluate("""(want) => { const src = (i) => i.currentSrc || i.src || '';
      const imgs = [...document.querySelectorAll('img')];
      const mine = imgs.filter(i => src(i).indexOf(want) >= 0);
      return { n: mine.length, ok: mine.filter(i => i.complete && i.naturalWidth >= 32).length,
               pend: mine.filter(i => !i.complete).length,
               over: document.documentElement.scrollWidth - innerWidth }; }""",
      small_dir)
    check("375 上天裔小图标同样解码成功且不撑出横向溢出",
          m["n"] >= 2 and m["ok"] == m["n"] and m["pend"] == 0 and m["over"] <= 1,
          "%d 处解码 %d 处（还有 %d 处没加载完）/ 溢出 %spx" % (m["n"], m["ok"], m["pend"], m["over"]))
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-raceicon-skyborne-m.png"))
    mctx.close()
    ctx.close()


def test_updates_filter(browser):
    """最新动态页：格子上写的数，必须就是点下去筛出来的数（2026-10-20 W02）。

    上一版这里数的是 it.kind（talent/spell），点下去筛的是 changeKind
    （added/modified/removed/…），两个字段不是一回事 → 除「全部类别」外五格恒为 0，
    可点了却能筛出上百条。旧站同样错，新站跟着错了一版。
    期望值全部在 python 里按 changeKind 现算，不抄页面、也不抄 scale.json
    （scale 那四格只数天赋，和这里的"该类别全部条目"不是同一个数，混用会假红）。"""
    print("\n[6h] 动态页类别计数与筛选结果一致")
    import json
    if not app_up(browser):
        return
    items = json.load(open(os.path.join(SRC, "data", "changes.json"), encoding="utf-8"))["items"]
    # 类别名单也从数据里现取，不写死：写死六项正是上一版漏掉 15 条的原因
    # （基线 / 学得更早 / 种族技 三种没有格子，格子之和永远小于「全部类别」）。
    kinds = ["all"] + sorted({str(x.get("changeKind") or "unchanged") for x in items})

    def exp(cls=None, what="all", k="all", kw=""):
        n = 0
        for x in items:
            if cls and x.get("classId") != cls:
                continue
            if what != "all" and x.get("kind") != what:
                continue
            if k != "all" and x.get("changeKind") != k:
                continue
            if kw and kw.lower() not in str(x.get("nameCn") or "").lower() \
                    and kw.lower() not in str(x.get("tree") or "").lower():
                continue
            n += 1
        return n

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(APP_BASE + "/#/updates", wait_until="networkidle")
    page.wait_for_timeout(2500)
    page.evaluate("() => { const n = document.getElementById('k1');"
                  "if (n) n.scrollIntoView({block: 'start'}); }")
    page.wait_for_timeout(400)

    def read_chips():
        # 点与读必须分两次调用：Vue 的更新是异步的，同一个 evaluate 里点完立刻读会拿到旧数
        return {c["k"]: c["n"] for c in page.evaluate(
            """() => [...document.querySelectorAll('.kchip')].map(b =>
                 ({ k: b.getAttribute('data-k'), n: parseInt(b.querySelector('b').textContent, 10) }))""")}

    def read_cnt():
        return int(re.sub(r"[^0-9]", "", page.inner_text("#ccnt")) or "0")

    got = read_chips()
    want = {k: exp(k=k) for k in kinds}
    check("格子的类别数与数据里真出现过的 changeKind 一一对上（不许有类别没有格子）",
          sorted(got.keys()) == sorted(kinds),
          "页面 %d 格 / 数据 %d 种：%s" % (len(got), len(kinds), sorted(got.keys())))
    check("各类别格子与按 changeKind 现算的期望逐格相等", got == want,
          "页面 %s / 期望 %s" % (got, want))
    check("各类别格子加起来 = 全部类别（每格都点一遍能覆盖整张表）",
          sum(v for k, v in got.items() if k != "all") == got.get("all"),
          "各类之和 %d / 全部 %s" % (sum(v for k, v in got.items() if k != "all"), got.get("all")))
    check("除真没有的类别外不许恒为 0（上一版五格全 0 就是这个 bug 的样子）",
          sum(1 for k in kinds if k != "all" and got.get(k, 0) > 0) >= 4,
          "非零 %d 格" % sum(1 for k in kinds if k != "all" and got.get(k, 0) > 0))
    page.screenshot(path=os.path.join(SHOT_DIR, "w2-updates-chips.png"))

    def click_chip(k):
        page.click(".kchip[data-k='%s']" % k)
        page.wait_for_timeout(500)

    bad = []
    for k in kinds:
        click_chip(k)
        if read_cnt() != got[k]:
            bad.append("%s 格写 %d、点出 %d" % (k, got[k], read_cnt()))
    check("逐格点一遍：表头报的条数等于格子上写的数", not bad, "; ".join(bad) or "各类别全对")

    # 收紧到猎人再看一遍：格子必须跟着其余条件走，不是永远显示全量
    page.click(".kchip[data-k='all']")
    page.wait_for_timeout(400)
    page.click(".pick[data-c='hunter']")
    page.wait_for_timeout(600)
    got_h = read_chips()
    want_h = {k: exp(cls="hunter", k=k) for k in kinds}
    check("选猎人后各类别格子跟着变（不是恒等于全量）", got_h == want_h, "页面 %s / 期望 %s" % (got_h, want_h))
    bad = []
    for k in kinds:
        click_chip(k)
        if read_cnt() != got_h[k]:
            bad.append("%s 格写 %d、点出 %d" % (k, got_h[k], read_cnt()))
    check("猎人 + 各类别组合：点下去的条数仍等于格子数", not bad, "; ".join(bad) or "各类别全对")
    page.screenshot(path=os.path.join(SHOT_DIR, "w2-updates-hunter-added.png"))

    # 再叠一层"只看法术"，三条件同时开：格子、表头、期望三方对齐
    page.select_option("#cw", "spell")
    page.wait_for_timeout(600)
    got_hs = read_chips()
    want_hs = {k: exp(cls="hunter", what="spell", k=k) for k in kinds}
    check("猎人 + 只看法术 + 类别三层叠加仍逐格相等", got_hs == want_hs,
          "页面 %s / 期望 %s" % (got_hs, want_hs))
    click_chip("all")
    check("三层叠加下表头条数等于「全部类别」格子", read_cnt() == got_hs["all"],
          "表头 %d / 格子 %d" % (read_cnt(), got_hs["all"]))

    # 空结果：搜一个不存在的词，格子全归零 + 空态文案在，不许留一张空表
    page.fill("#cq", "根本没有这条名字")
    page.wait_for_timeout(700)
    z = page.evaluate("""() => ({ chips: [...document.querySelectorAll('.kchip')]
             .map(b => parseInt(b.querySelector('b').textContent, 10)),
             cnt: (document.querySelector('#ccnt') || {}).textContent || '',
             empty: !!document.querySelector('.empty'),
             rows: document.querySelectorAll('#chbody tbody tr').length })""")
    check("搜不到时：格子全 0、表头 0 条、空态文案顶上（不留空表）",
          all(v == 0 for v in z["chips"]) and "0" in z["cnt"] and z["empty"] and z["rows"] == 0,
          json.dumps(z, ensure_ascii=False))
    page.screenshot(path=os.path.join(SHOT_DIR, "w2-updates-empty.png"))

    # 375 同一件事：格子换行排、点了同样对得上（以前只在桌面验，手机上溢出没人管）
    mctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    mp = mctx.new_page()
    mp.goto(APP_BASE + "/#/updates", wait_until="networkidle")
    mp.wait_for_timeout(2500)
    mp.evaluate("() => { const n = document.getElementById('k1');"
                "if (n) n.scrollIntoView({block: 'start'}); }")
    mp.wait_for_timeout(400)
    mh = mp.evaluate("""() => ({ over: document.documentElement.scrollWidth - innerWidth,
             chips: [...document.querySelectorAll('.kchip')].map(b =>
               ({ k: b.getAttribute('data-k'), n: parseInt(b.querySelector('b').textContent, 10),
                  vis: b.getBoundingClientRect().width > 0 })) })""")
    check("375 上各类别格子都排得出来且不撑出横向溢出",
          mh["over"] <= 1 and len(mh["chips"]) == len(kinds) and all(c["vis"] for c in mh["chips"]),
          "溢出 %spx / %d 格" % (mh["over"], len(mh["chips"])))
    mp.click(".kchip[data-k='modified']")
    mp.wait_for_timeout(600)
    mcnt = int(re.sub(r"[^0-9]", "", mp.inner_text("#ccnt")) or "0")
    chk = [c["n"] for c in mh["chips"] if c["k"] == "modified"][0]
    check("375 点「改动」后条数也等于格子数", mcnt == chk == exp(k="modified"),
          "表头 %d / 格子 %d / 期望 %d" % (mcnt, chk, exp(k="modified")))
    mp.screenshot(path=os.path.join(SHOT_DIR, "w2-updates-chips-m.png"))
    check("这一页没有脚本报错", not errs, "; ".join(errs[:2]) or "干净")
    mctx.close()
    ctx.close()


def test_app(browser, base):
    """新站（Vue 3 + Vite）冒烟：只跑已迁的页，断言口径与旧站第 1 节一致。

    新站不在默认流程里跑是因为它要先 npm run build + vite preview；
    端口没起时本函数记一条"跳过"并说明怎么起，--app 则把它变成硬失败。"""
    print("\n[16] 新站（Vue）冒烟")
    import json
    S = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    pages = [("首页", "/#/", "index"), ("世界页", "/#/world", "world")]
    reachable = True
    try:
        probe = browser.new_context(viewport={"width": 1440, "height": 1000})
        pp = probe.new_page()
        pp.goto(APP_BASE, timeout=8000)
        pp.wait_for_timeout(500)
        probe.close()
    except Exception as e:
        reachable = False
        check("新站可访问", not APP_REQUIRED,
              "%s 不通（%s）。先跑：cd app && npm run build && npx vite preview --port 8821" % (APP_BASE, str(e)[:60]))
    if not reachable:
        return
    check("新站可访问", True, APP_BASE)
    # ---- 新站导航收窄（2026-10-16 站主：世界只留三格、工具只留排行）----
    # 旧站那条 17 格的断言故意不动——旧站已冻结，两栈的导航**从此有意不同**。
    # 这里钉的是新站这一份：名字与顺序逐项比，摘掉的七格不许被"顺手同步"补回来。
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(APP_BASE + "/#/world", wait_until="networkidle")
    page.wait_for_timeout(1600)
    # 读标签要先把「新」角标剔掉：角标是 <i class="nb"> 塞在 <a> 里的文字，
    # 不剔的话本站更新一打上"配装"标签，这条就会拿"配装新"去比"配装"而红
    # （旧站那条早就剔了，新站这条是我漏的——2026-10-17 全量门禁抓到）
    app_subs = page.evaluate("() => [...document.querySelectorAll('nav.main a.nl')].map(a => {"
                             "const c = a.cloneNode(true);"
                             "c.querySelectorAll('.nb').forEach(n => n.remove());"
                             "return c.textContent.trim(); })")
    APP_NAV = ["首页", "计算器", "职业", "玩法问答", "传承", "总览",
               "区域与稀有", "副本", "团本", "配方", "配装", "排行"]
    check("新站导航二级就是这 %d 格，顺序与名字不许漂" % len(APP_NAV), app_subs == APP_NAV,
          "%d 项：%s" % (len(app_subs), app_subs))
    check("世界与工具两组按收窄后的口径（3 格 / 1 格）",
          page.evaluate("""() => { const g = [...document.querySelectorAll('nav.main .ngrp')];
            const of = (n) => { const b = g.find(x => (x.querySelector('.ngt')||{}).textContent === n);
              return b ? b.querySelectorAll('a.nl').length : -1; };
            return [of('世界'), of('工具')]; }""") == [3, 1])
    # 上面剔角标是为了比名字，这一条反过来查角标本身：应画的 = 最新一批本站更新的板块标签
    # ∩ 导航项名字。剔完就没人管角标在不在，等于把"这一版新开了哪几页"这个记号丢了也没人发现。
    sc_nav = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    badge = page.evaluate("() => [...document.querySelectorAll('nav.main a.nl')]"
                          ".filter(a => a.querySelector('.nb'))"
                          ".map(a => { const c = a.cloneNode(true);"
                            "c.querySelectorAll('.nb').forEach(n => n.remove());"
                            "return c.textContent.trim(); })")
    want_badge = [x for x in APP_NAV if x in (sc_nav.get("navNew") or [])]
    check("导航「新」角标只挂在最新一批更新对得上的项上",
          badge == want_badge, "画了 %s ／ 应画 %s（最新标签 %s）"
          % (badge, want_badge, sc_nav.get("navNew")))
    # 被摘掉导航的页不许成孤页：物品库与成就靠首页那行"更多入口"进（旧站没有物品库这一页，
    # 所以这一行必须走站内路由而不是写死旧站地址——写死就是 404）。
    page.goto(APP_BASE + "/#/", wait_until="networkidle")
    page.wait_for_timeout(1800)
    chips = page.evaluate("() => [...document.querySelectorAll('.chipsrow a')]"
                          ".map(a => ({ t: a.textContent.trim(), h: a.getAttribute('href') || '' }))")
    want = {"#/items": "物品库", "#/achievements": "成就"}
    got = {c["h"]: c["t"] for c in chips}
    miss = [v for k, v in want.items() if k not in got]
    check("首页那行入口补上了被摘导航的物品库与成就", not miss,
          "缺 %s ／ 现有 %s" % (miss or "无", [c["t"] for c in chips]))
    bad = [k for k in got if not k.startswith("#/")]
    check("首页那行入口全走站内路由（不回落已冻结的旧站）", not bad, "回旧站：%s" % (bad or "无"))
    counts = [got[k] for k in want if k in got]
    sc2 = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    check("那两格带的数是 scale.json 算出来的，不是手抄",
          str(sc2["items"]) in got.get("#/items", "") and str(sc2["achievements"]) in got.get("#/achievements", ""),
          " / ".join(counts) + "（数据 items %s、achievements %s）" % (sc2["items"], sc2["achievements"]))
    # ---- 10-18 站主实拍：首页"点了没反应" + 底部一条横向滚动条 + 导航太素 ----
    # 三条各钉一个断言，因为这三个毛病没有一个能靠"构建通过"发现。
    # 1) 死链：首页把已迁页的地址写成旧站文件式地址（/talent.html）时，
    #    vite preview 的 SPA 兜底会返回 200 + index.html，哈希路由静默停在首页——
    #    页面不报错、链接不是 404、门禁全绿，只有人点上去才发现。所以直接钉住：
    #    首页正文里任何链接都不许再出现文件式地址。
    file_links = page.evaluate("""() => [...document.querySelectorAll('#main a[href]')]
      .map(a => a.getAttribute('href'))
      .filter(h => !/^#/.test(h) && !/^https?:/.test(h))""")
    check("首页正文没有文件式地址（那种点了没反应的链接）", not file_links,
          "%d 条：%s" % (len(file_links), file_links[:6] or "无"))
    # 2) 横向滚动条：原来 .hrail 是 overflow-x:auto 的一条横滑轨，9 格 × 132px
    #    在 1440 以下必然溢出。改成网格后钉两层——页面不许横向溢出、轨本身不许溢出。
    ov = page.evaluate("""() => ({doc: document.documentElement.scrollWidth - window.innerWidth,
      rails: [...document.querySelectorAll('.hrail,.cls9,.modgrid,.chipsrow')]
        .map(x => x.className + ':' + (x.scrollWidth - x.clientWidth))})""")
    bad_rails = [r for r in ov["rails"] if not r.endswith(":0")]
    check("首页 1440 没有横向滚动，两条九格轨也不溢出",
          ov["doc"] == 0 and not bad_rails,
          "页面溢出 %d ／ 轨 %s" % (ov["doc"], bad_rails or "全部 0"))
    # 3) 两排 9 格不许读成同一条：中间必须有可见间距（站主截图里那两条是贴在一起的）
    check("职业条与板块轨之间留了间距，不贴成一条",
          page.evaluate("""() => { const a = document.querySelector('.cls9');
            const b = document.querySelector('.hrail');
            if (!a || !b) return -1;
            return Math.round(b.getBoundingClientRect().top - a.getBoundingClientRect().bottom); }""") >= 12)
    # 4) 导航带：2026-10-18 站主选 B 方案改成"胶囊分组"。这里钉的是**形状**不是配色——
    #    好不好看只有看图能判，但"是不是八颗丸、丸有没有描边、当前项是不是丸内一颗填充小药丸、
    #    上一版的指示条与下划线撤干净没有"全都可以量。
    #    读当前项文本一律先剔「新」角标：上一轮刚在姊妹断言上栽过，这条别再犯一遍。
    nav1440 = page.evaluate("""() => { const n = document.querySelector('nav.main');
      const pills = [...n.querySelectorAll('.ngrp')];
      const on = n.querySelector('a.nl.on');
      const cs = (e, p) => getComputedStyle(e, p || null);
      // 伪元素"没画"有两种表现：display:none，或压根没有 content（不生成盒子）
      const gone = (e, p) => { const c = cs(e, p);
        return c.display === 'none' || c.content === 'none' || c.content === ''; };
      const rad = (e) => parseFloat(cs(e).borderTopLeftRadius) || 0;
      // 把某个元素作用域里的 --gc 解析成 rgb：当前项的字色必须等于本组色，
      // 但组色是令牌，不该把 rgb 抄进断言，所以现场解析出来比。
      const gcOf = (host) => { const t = document.createElement('i');
        t.style.color = 'var(--gc)'; host.appendChild(t);
        const v = cs(t).color; t.remove(); return v; };
      return { h: Math.round(n.getBoundingClientRect().height),
        on: on ? (() => { const c = on.cloneNode(true);
               c.querySelectorAll('.nb').forEach(x => x.remove());
               return c.textContent.trim(); })() : null,
        pills: pills.length,
        pillRound: pills.every(p => rad(p) >= p.getBoundingClientRect().height / 2 - 1),
        pillBordered: pills.every(p => cs(p).borderTopWidth === '1px'
          && cs(p).borderTopStyle === 'solid'),
        pillRaised: pills.every(p => cs(p).backgroundColor !== 'rgba(0, 0, 0, 0)'),
        oneRow: new Set([...n.querySelectorAll('a.nl')].map(e => Math.round(e.getBoundingClientRect().top))).size,
        chipRound: on ? rad(on) >= on.getBoundingClientRect().height / 2 - 1 : false,
        chipFill: on ? cs(on).backgroundColor : '',
        chipIsGroupColor: on ? cs(on).color === gcOf(on.closest('.ngrp')) : false,
        dotShown: cs(n.querySelector('.ngt'), '::before').display !== 'none',
        railGone: gone(pills[0], '::after') && gone(pills[0], '::before') && gone(on, '::after'),
        dotGone: gone(n.querySelector('.ngt'), '::before') }; }""")
    # 组色单独量：七组七个色，少定义任何一组就会落回 --txt-muted 默认灰，Set 立刻少一个。
    # （「工具」这一组在 app.css 里只写到 g6，一直是灰的——胶囊描边把这个老问题照出来了。）
    gcols = page.evaluate("""() => [...document.querySelectorAll('nav.main .ngrp:not(.solo)')]
      .map(g => getComputedStyle(g.querySelector('.ngt')).color)""")
    check("首页导航是八颗圆角胶囊：丸有描边、有底色、入口排在一行",
          nav1440["pills"] == 8 and nav1440["pillRound"] and nav1440["pillBordered"]
          and nav1440["pillRaised"] and nav1440["oneRow"] == 1
          and nav1440["h"] >= 44 and nav1440["h"] <= 96,
          json.dumps({k: nav1440[k] for k in ("h", "pills", "pillRound", "pillBordered",
                                              "pillRaised", "oneRow")}, ensure_ascii=False))
    check("当前项是丸内一颗填充的小药丸，字色就是本组色（不抄硬编码 rgb，现场解析 --gc）",
          nav1440["on"] == "首页" and nav1440["chipRound"]
          and nav1440["chipFill"] not in ("", "rgba(0, 0, 0, 0)", "transparent")
          and nav1440["chipIsGroupColor"],
          json.dumps({k: nav1440[k] for k in ("on", "chipRound", "chipFill", "chipIsGroupColor")},
                     ensure_ascii=False))
    check("上一版的组底指示条、竖分隔、项下划线都撤干净了，组名前也不许再画点或短横",
          nav1440["railGone"] and nav1440["dotGone"],
          json.dumps({k: nav1440[k] for k in ("railGone", "dotGone")}, ensure_ascii=False))
    check("七个分组各有自己的颜色（少定义任何一组就会落回默认灰，这里 Set 会少一个）",
          len(set(gcols)) == len(gcols) == 7, "%d 组 %d 色：%s" % (len(gcols), len(set(gcols)), gcols))
    ctx375 = browser.new_context(viewport={"width": 375, "height": 812})
    p375 = ctx375.new_page()
    p375.goto(APP_BASE + "/#/", wait_until="networkidle")
    p375.wait_for_timeout(2000)
    m = p375.evaluate("""() => { const g = document.querySelector('.cls9');
      const h = document.querySelector('.hrail');
      const rows = (e) => new Set([...e.children].map(k => Math.round(k.getBoundingClientRect().top))).size;
      return {doc: document.documentElement.scrollWidth - window.innerWidth,
        clsRows: g ? rows(g) : 0, hubRows: h ? rows(h) : 0,
        chip: (() => { const on = document.querySelector('nav.main a.nl.on');
          const c = on ? getComputedStyle(on) : null;
          return c ? c.backgroundColor + '|' + c.borderBottomWidth : ''; })(),
        minW: g ? Math.round(Math.min(...[...g.children].map(k => k.getBoundingClientRect().width))) : 0,
        cut: g ? [...g.children].some(k => k.getBoundingClientRect().right > window.innerWidth + 1) : false}; }""")
    check("首页 375 整页不横滚，职业条换成三列且没有格子被切掉",
          m["doc"] == 0 and m["clsRows"] == 3 and m["hubRows"] == 3 and not m["cut"],
          json.dumps(m, ensure_ascii=False))
    # 窄屏这一条仍然要钉：上一版手机上靠 2px 底边当选中态（那时丸内的填充被下划线方案占了），
    # 胶囊方案改成桌面与窄屏共用丸内填充，底边彻底撤掉。这一条盯的是"填充还在、底边没了"。
    check("首页 375 的选中项仍靠丸内填充标出，2px 底边已彻底撤掉",
          m["chip"].split("|")[0] not in ("", "rgba(0, 0, 0, 0)", "transparent")
          and m["chip"].split("|")[1] == "0px", m["chip"])
    p375.screenshot(path=os.path.join(SHOT_DIR, "app-home-375.png"))
    ctx375.close()
    page.screenshot(path=os.path.join(SHOT_DIR, "app-home-1440.png"), clip=None, full_page=False)

    # ---- 10-18 站主实拍：种族页第一排头像被阵营条的组头盖掉一半 ----
    # 成因不在这一页：app.css 给 .fhead 写了 position:sticky;top:44px，而它外面那层 .facband
    # 是 overflow:hidden（城市原画要裁进圆角里），sticky 的参照物于是变成这条带自己。
    # 带不滚，top:44px 就成了"把组头从常规流里往下推 44px"，而 sticky 不额外占位，
    # 下面的格子留在原位被这条不透明、z-index 更高的组头压住 32px。
    # 所以这里钉两层：① 组头不许再是 sticky（改回 static 是这一版的定案）；
    # ② 每个头像的顶边中点与左边中点必须命中自己——**命中测试要先把元素滚进视口**，
    #    在视口外 elementFromPoint 返回 null，第一版探针就是那样把"在屏幕外"误报成"被盖住"的。
    def face_hits(vp):
        c2 = browser.new_context(viewport={"width": vp, "height": 812})
        p2 = c2.new_page()
        p2.goto(APP_BASE + "/#/races", wait_until="networkidle")
        p2.wait_for_timeout(2200)
        geo = p2.evaluate("""() => [...document.querySelectorAll('.facband')].map(b => {
          const h = b.querySelector('.fhead'), g = b.querySelector('.racegrid');
          return {pos: h ? getComputedStyle(h).position : '', z: h ? getComputedStyle(h).zIndex : '',
            overlap: (h && g) ? Math.round(h.getBoundingClientRect().bottom - g.getBoundingClientRect().top) : null,
            bandOverflow: getComputedStyle(b).overflow}; })""")
        n = p2.evaluate("() => document.querySelectorAll('.racecard .rface').length")
        bad = []
        for i in range(n):
            p2.evaluate("i => document.querySelectorAll('.racecard .rface')[i]"
                        ".scrollIntoView({block:'center'})", i)
            p2.wait_for_timeout(110)
            r = p2.evaluate("""i => { const f = document.querySelectorAll('.racecard .rface')[i];
              const b = f.getBoundingClientRect();
              const hits = [[b.left + b.width / 2, b.top + 3], [b.left + 3, b.top + b.height / 2]]
                .map(([x, y]) => { const el = document.elementFromPoint(x, y);
                  if (!el) return '视口外';
                  if (el === f || f.contains(el)) return null;
                  return el.tagName + '.' + (typeof el.className === 'string' ? el.className : ''); })
                .filter(Boolean);
              return {race: (f.closest('.racecard').querySelector('.rcn') || {}).innerText, hits: hits}; }""", i)
            if r["hits"]:
                bad.append("%s→%s" % (r["race"], r["hits"]))
        p2.screenshot(path=os.path.join(SHOT_DIR, "app-races-heads-%s.png" % vp))
        c2.close()
        return geo, bad

    geo_d, bad_d = face_hits(1440)
    check("种族页：阵营条的组头不再 sticky（sticky 落在 overflow:hidden 的带里会把组头推下 44px 盖住头像）",
          len(geo_d) == 2 and all(x["pos"] == "static" and (x["overlap"] or 0) <= 0
                                  and x["bandOverflow"] == "hidden" for x in geo_d),
          json.dumps(geo_d, ensure_ascii=False))
    check("种族页 1440：十个头像逐格做命中测试，没有一个被别的元素盖住",
          not bad_d, "；".join(bad_d) or "10 个全部露出")
    geo_m, bad_m = face_hits(375)
    check("种族页 375：头像同样没有一个被盖住", not bad_m, "；".join(bad_m) or "10 个全部露出")
    page.goto(APP_BASE + "/#/", wait_until="networkidle")
    page.wait_for_timeout(1200)
    page.screenshot(path=os.path.join(SHOT_DIR, "app-nav-narrow.png"))
    ctx.close()
    for label, path, key in pages:
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        errs, failed = [], []
        page.on("console", lambda m, e=errs: e.append(m.text[:120]) if m.type == "error" else None)
        page.on("response", lambda r, f=failed: f.append("%d %s" % (r.status, r.url.split("/")[-1]))
                if r.status >= 400 and not tolerated(r.url) else None)
        page.goto(APP_BASE + path, wait_until="networkidle")
        page.wait_for_timeout(2000)
        st = page.evaluate("""() => ({
          h1: document.querySelectorAll('#main h1').length,
          chars: (document.querySelector('#main') || document.body).innerText.length,
          ctl: document.querySelectorAll('#main button, #main a, #main input').length,
          broken: [...document.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0).length,
          noalt: [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length,
          noname: [...document.querySelectorAll('#main button')].filter(b =>
            !(b.innerText.trim() || b.getAttribute('aria-label'))).length,
          shell: { top: !!document.querySelector('#top .brand'), foot: !!document.querySelector('#foot .in span') } })""")
        check("新站 %s：一个 H1、有正文与控件" % label,
              st["h1"] == 1 and st["chars"] > 200 and st["ctl"] > 5 and st["shell"]["top"] and st["shell"]["foot"],
              "H1 %d / %d 字 / %d 控件" % (st["h1"], st["chars"], st["ctl"]))
        check("新站 %s：无脚本报错与失败请求" % label, not errs and not failed,
              "; ".join((errs + failed)[:2]) or "干净")
        check("新站 %s：图片都有 alt 且无坏图" % label, st["noalt"] == 0 and st["broken"] == 0,
              "缺 alt %d / 坏图 %d" % (st["noalt"], st["broken"]))
        check("新站 %s：按钮都有可读名" % label, st["noname"] == 0, "%d 个缺名" % st["noname"])
        page.screenshot(path=os.path.join(SHOT_DIR, "app-%s.png" % key))
        if key == "index":
            # 2026-10-12 站主决定：新站首页与旧站一样不再挂覆盖率读数，
            # 这条从"四个数与 scale.json 一致"改成"这三样都不许出现"。
            cov_left = page.evaluate("""() => ({covnum: document.querySelectorAll('.covnum').length,
              stats4: document.querySelectorAll('.stats4').length,
              pill: document.querySelectorAll('#main .pill').length})""")
            check("新站首页不再挂覆盖率读数与分级徽标（与旧站同一口径）",
                  cov_left == {"covnum": 0, "stats4": 0, "pill": 0}, json.dumps(cov_left))
            strip = page.evaluate("() => document.querySelectorAll('.stripc').length")
            check("新站首页九职业条齐全", strip == S["classes"], "%d 格" % strip)
            mods = page.evaluate("() => document.querySelectorAll('.mod').length")
            check("新站首页入口卡与旧站一样多（12 张分组卡 + 1 张大卡）", mods == 13, "%d 张" % mods)
            gs = page.evaluate("() => !!document.querySelector('#gs')")
            check("新站首页也接了全站搜索框", gs)
            page.fill("#gs", "咆鼻")
            page.wait_for_timeout(1400)
            arows = page.evaluate("() => [...document.querySelectorAll('#gres .gsr')].length")
            check("新站搜索框能出结果", arows >= 1, "%d 条" % arows)
            import re
            cd = page.inner_text(".cd i").strip()
            check("新站倒计时同样到秒", re.match(r"^\d{2}:\d{2}:\d{2}$", cd) is not None, cd)
            pv2 = page.evaluate("""() => { const t = document.querySelector('#treecard');
              if (!t) return null;
              return { nodes: t.querySelectorAll('.pnode').length, empty: t.querySelectorAll('.pempty').length,
                       cls: t.querySelectorAll('.stripc').length, on: t.querySelectorAll('.stripc.on').length,
                       broken: [...t.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0).length,
                       href: (t.querySelector('.pnode') || {}).getAttribute
                             ? t.querySelector('.pnode').getAttribute('href') : '' }; }""")
            check("新站首页也有只读天赋树预览",
                  pv2 and pv2["nodes"] > 10 and pv2["cls"] == S["classes"] and pv2["on"] == 1,
                  json.dumps(pv2, ensure_ascii=False))
            check("新站预览没有坏图，格子也链回计算器（全量迁移后是站内路由 #/talent）",
                  pv2 and pv2["broken"] == 0 and "/talent?c=" in (pv2["href"] or ""), pv2 and pv2["href"])
        else:
            tabs = page.evaluate("() => document.querySelectorAll('.picks .pick[data-t]').length")
            check("新站世界页四个面板齐全", tabs == 4, "%d 个" % tabs)
            for t in ["books", "bag", "zones"]:      # 切一圈再回到区域，验证面板切换不残留
                page.click('[data-t="%s"]' % t)
                page.wait_for_timeout(900)
            zc = page.evaluate("() => document.querySelectorAll('.zcard').length")
            check("新站区域卡数量与数据一致", zc == S["zones"], "%d 张（数据 %d）" % (zc, S["zones"]))
            page.click('[data-t="rares"]')
            page.wait_for_timeout(1400)
            # ---- 10-18 站主：一区域一张图，稀有直接标在图上 ----
            # 原来这里只数 `.zmark` 的个数（每条稀有卡上一个点），换结构之后那个类已经没有了。
            # 新的判据要能抓住三件真会出错的事：点位与坐标对不上、没图的稀有被"猜"上图、
            # 以及悬停不生效（只有看图才知道，所以这里去量计算样式）。
            W = json.load(open(os.path.join(SRC, "data", "world.json"), encoding="utf-8"))
            rs = W.get("rares") or []
            groups = {}
            for r in rs:
                groups.setdefault(r.get("zone") or "未归区域", []).append(r)
            want_bands = len(groups)
            want_dots = len([r for r in rs if r.get("mapFile") and r.get("mark")])
            want_maps = len([k for k, v in groups.items() if any(r.get("mapFile") for r in v)])
            geo = page.evaluate("""() => { const bands = [...document.querySelectorAll('.zband')];
              return { bands: bands.length,
                maps: document.querySelectorAll('.zbig img').length,
                dots: document.querySelectorAll('.zdot').length,
                rows: document.querySelectorAll('.zrow').length,
                old: document.querySelectorAll('.rarecard').length,
                perBand: bands.map(b => ({ d: b.querySelectorAll('.zdot').length,
                  r: b.querySelectorAll('.zrow').length, img: !!b.querySelector('.zbig img') })),
                badPos: [...document.querySelectorAll('.zdot')].filter(d => {
                  const l = d.style.left, t = d.style.top;
                  return !/%$/.test(l) || !/%$/.test(t); }).length,
                over: document.documentElement.scrollWidth - window.innerWidth}; }""")
            check("一个区域一张图：带数、图数、点位数、列表行数全部对得上数据",
                  geo["bands"] == want_bands and geo["maps"] == want_maps
                  and geo["dots"] == want_dots and geo["rows"] == len(rs) and geo["badPos"] == 0,
                  "带 %d（数据 %d）／图 %d（应 %d）／点 %d（数据有图有坐标的 %d）／行 %d（数据 %d）／没坐标的 %d"
                  % (geo["bands"], want_bands, geo["maps"], want_maps, geo["dots"], want_dots,
                     geo["rows"], len(rs), geo["badPos"]))
            check("旧的「每条稀有各带一张同样的区域图」已经撤掉（反向钉，别搬回来）",
                  geo["old"] == 0, "还剩 %d 张 rarecard" % geo["old"])
            # 每个点位的 left/top 必须等于这条稀有自己数据里的百分比——不猜位置、不重排
            pos = page.evaluate("""() => [...document.querySelectorAll('.zdot')].map(d => ({
              id: d.dataset.r, l: d.style.left, t: d.style.top }))""")
            byid = {str(r["id"]): r for r in rs}
            badp = []
            for x in pos:
                r = byid.get(str(x["id"]))
                if not r:
                    badp.append("页面上有个点位在数据里找不到：%s" % x["id"]); continue
                want = "(%s%%, %s%%)" % (r["mark"]["x"], r["mark"]["y"])
                got = "(%s, %s)" % (x["l"], x["t"])
                if want != got:
                    badp.append("%s 应 %s 实 %s" % (r["nameCn"], want, got))
            check("每个点位就摆在这条稀有自己的坐标百分比上，一个都不偏移",
                  not badp, "；".join(badp[:4]) or "%d 个点逐位核对通过" % len(pos))
            # 没有地图文件的那些不许出现在图上（只进列表），这是"不猜位置"的可执行版本
            plotted = set(x["id"] for x in pos)
            should = set(str(r["id"]) for r in rs if r.get("mapFile") and r.get("mark"))
            extra = plotted - {int(s) if str(s).isdigit() else s for s in should}
            check("没有地图文件的稀有不标点（只在列表里出现，不拿别的图猜位置）",
                  not extra and len(plotted) == len(should),
                  "多标 %d 个／应标 %d 个／实标 %d 个" % (len(extra), len(should), len(plotted)))
            # 悬停：默认虚、指上去实体并弹层，右边对应行同时高亮
            page.evaluate("() => document.querySelector('.zband').scrollIntoView({block:'center'})")
            page.wait_for_timeout(400)
            before = page.evaluate("""() => { const d = getComputedStyle(document.querySelector('.zdot'));
              return {op: parseFloat(d.opacity), blur: d.filter, pop: !!document.querySelector('.zpop')}; }""")
            first = page.evaluate("() => document.querySelector('.zdot').dataset.r")
            page.hover(".zdot")
            page.wait_for_timeout(500)
            hov = page.evaluate("""() => { const d = document.querySelector('.zdot.on');
              const c = getComputedStyle(d); const p = document.querySelector('.zpop');
              const r = p && p.getBoundingClientRect();
              return {op: parseFloat(c.opacity), blur: c.filter, has: !!p,
                title: p ? (p.querySelector('b') || {}).innerText : '',
                drops: p ? p.querySelectorAll('.zpop-i').length : -1,
                rows: document.querySelectorAll('.zrow.on').length,
                out: r ? (r.left < 0 || r.right > window.innerWidth || r.top < 0) : null}; }""")
            wr = byid.get(str(first)) or {}
            check("点位平时是虚的（半透明 + 模糊），指上去才实体",
                  before["op"] < 0.8 and "blur" in before["blur"] and not before["pop"]
                  and hov["op"] > 0.99 and hov["blur"] == "none",
                  "默认 透明度 %.2f/%s → 悬停 透明度 %.2f/%s"
                  % (before["op"], before["blur"], hov["op"], hov["blur"]))
            check("悬停弹出的浮层写的就是这一条：名字、掉落件数与数据一致，且不越出视口",
                  hov["has"] and hov["title"] == wr.get("nameCn")
                  and hov["drops"] == len(wr.get("drops") or []) and not hov["out"],
                  "标题 %s（数据 %s）／掉落 %d（数据 %d）／越界 %s"
                  % (hov["title"], wr.get("nameCn"), hov["drops"],
                     len(wr.get("drops") or []), hov["out"]))
            check("点位与右边列表双向联动：指点位，对应那一行也亮",
                  hov["rows"] == 1, "%d 行高亮" % hov["rows"])
            page.click(".zdot")
            page.mouse.move(10, 300)
            page.wait_for_timeout(400)
            check("手机上没有悬停，所以点一下要把这层钉住（移开鼠标仍在）",
                  page.evaluate("() => !!document.querySelector('.zpop')"))
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            check("按 ESC 收掉浮层", page.evaluate("() => !document.querySelector('.zpop')"))
            page.hover(".zlist .zrow")
            page.wait_for_timeout(400)
            check("反过来指列表那一行，图上的点位也实体并弹层",
                  page.evaluate("""() => ({dot: document.querySelectorAll('.zdot.on').length,
                    pop: !!document.querySelector('.zpop')})""") == {"dot": 1, "pop": True})
            check("换结构之后这一页仍然不横向溢出", geo["over"] == 0, "溢出 %d" % geo["over"])
            # 375 上浮层改成挂在图下面（桌面是 absolute，手机不行——手机上盖住图就等于盖住别的点位）。
            # 而点位是按父盒高度的百分比摆的，所以必须验：浮层一开，父盒不能变高、点位不能集体跳位。
            jc = browser.new_context(viewport={"width": 375, "height": 812})
            jp = jc.new_page()
            jp.goto(APP_BASE + "/#/world?t=rares", wait_until="networkidle")
            jp.wait_for_timeout(2200)
            jp.evaluate("() => document.querySelector('.zband').scrollIntoView({block:'center'})")
            jp.wait_for_timeout(400)
            # 注意 Vue 的 DOM 更新是异步的：click 与"查 .zpop / 量点位"必须分成两次 evaluate，
            # 中间等一次。写在同一个 evaluate 里永远查不到（第一版就是这么假红的）。
            # 量的是 offsetLeft/offsetTop 而不是 getBoundingClientRect：
            # 被点中的那颗会 transform:scale(1.3)，rect 会跟着涨 3px——那是设计要的放大，不是跳位。
            # offset* 只看布局位置，不吃 transform，才能把"父盒被撑高导致全体下移"和"这一颗自己变大"分开。
            jp.evaluate("""() => { const band = document.querySelector('.zband');
              window.__shot = () => [...band.querySelectorAll('.zdot')].map((d) => [d.offsetLeft, d.offsetTop]);
              window.__before = window.__shot();
              band.querySelector('.zdot').click(); }""")
            jp.wait_for_timeout(600)
            jump = jp.evaluate("""() => { const band = document.querySelector('.zband');
              const after = window.__shot();
              const before = window.__before;
              const pop = band.querySelector('.zpop');
              const pr = pop ? pop.getBoundingClientRect() : null;
              const mr = band.querySelector('.zcanvas').getBoundingClientRect();
              const moved = before.filter((b, i) => !after[i]
                || b[0] !== after[i][0] || b[1] !== after[i][1]).length;
              return { n: before.length, moved: moved, pop: !!pop,
                over: document.documentElement.scrollWidth - window.innerWidth,
                full: pr ? (Math.round(pr.left - mr.left) <= 2 && Math.round(mr.right - pr.right) <= 2) : null,
                below: pr ? pr.top >= mr.bottom - 2 : null }; }""")
            check("375 打开浮层时点位不许集体跳位（浮层撑高的是外层盒，不是点位参照的那层画布）",
                  jump["pop"] and jump["n"] > 1 and jump["moved"] == 0,
                  "%d 个点里 %d 个动了" % (jump["n"], jump["moved"]))
            check("375 浮层整宽贴在地图下方、不盖住图、也不溢出屏幕",
                  jump["over"] == 0 and jump["full"] and jump["below"],
                  "横向溢出 %d ／ 整宽 %s ／ 贴在图下方 %s"
                  % (jump["over"], jump["full"], jump["below"]))
            # 这张图存的是"浮层展开态"：上面那一步刚点开了第一个点位，正好拍到手感
            jp.screenshot(path=os.path.join(SHOT_DIR, "app-rares-m.png"))
            jc.close()
            body = page.evaluate("() => document.querySelector('#main').innerText")
            check("新站世界页正文没有面向开发的词", not dev_word_hits(body), "干净")
            page.screenshot(path=os.path.join(SHOT_DIR, "app-world-rares.png"))
        ctx.close()

    # 物品库（新站独有页，2026-10-14 站主拍板原型后实现）。断言照拍板口径：
    # 每页 50 行、筛选芯片与四个读数、页内搜索接得住、正文没有面向开发的词。
    # 行图标按本地库存如实渲染：取不到官方图的（icon-gaps.json 登记）本就该退占位块，
    # 所以"该有图的行数"由 items.json 前 50 行对照 icon-gaps 推导，404 只放行登记过的键。
    it = json.load(open(os.path.join(SRC, "data", "items.json"), encoding="utf-8"))["items"]
    it.sort(key=lambda x: x["id"])
    expect_lico = 50 - sum(1 for x in it[:50] if not x.get("iconKey") or x.get("iconKey") in ICON_GAPS)
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs, failed = [], []
    page.on("console", lambda m, e=errs: e.append(m.text[:120]) if m.type == "error" else None)
    page.on("response", lambda r, f=failed: f.append("%d %s" % (r.status, r.url.split("/")[-1]))
            if r.status >= 400 and not tolerated(r.url) else None)
    page.goto(APP_BASE + "/#/items", wait_until="networkidle")
    page.wait_for_timeout(2000)
    st = page.evaluate("""() => ({
      rows: document.querySelectorAll('.itt tbody tr').length,
      chips: document.querySelectorAll('.kchip').length,
      reads: document.querySelectorAll('.stats.readout .stat').length,
      lico: document.querySelectorAll('.itt tbody img.lico').length,
      broken: [...document.querySelectorAll('.itt tbody img.lico')]
        .filter(i => i.complete && i.naturalWidth === 0).length })""")
    check("新站物品库：每页 50 行、筛选芯片与四个读数齐全",
          st["rows"] == 50 and st["chips"] >= 9 and st["reads"] == 4, json.dumps(st))
    check("新站物品库：行图标按本地库存如实渲染、无坏图", st["lico"] == expect_lico and st["broken"] == 0,
          "图标 %d/%d（%d 行本就取不到官方图走占位）" % (st["lico"], expect_lico, 50 - expect_lico))
    page.fill(".qsearch", "护腕")
    page.wait_for_timeout(900)
    hit = page.evaluate("""() => { const n = document.querySelector('.itt tbody tr .nm');
      return { rows: document.querySelectorAll('.itt tbody tr').length,
               first: n ? n.innerText.trim() : '' }; }""")
    check("新站物品库：页内搜索接得住", hit["rows"] >= 1 and "护腕" in hit["first"],
          json.dumps(hit, ensure_ascii=False))
    body = page.evaluate("() => document.querySelector('#main').innerText")
    check("新站物品库：正文没有面向开发的词", not dev_word_hits(body), "干净")
    check("新站物品库：无脚本报错与失败请求", not errs and not failed,
          "; ".join((errs + failed)[:2]) or "干净")

    # —— 详情抽屉（物品线二批，2026-10-14 站主拍板方案 A）：搜一件名字唯一、属性 ≥3 行的物品，
    #    点行开抽屉，属性行数与 items-detail.json 逐条一致；遮罩能关；没有掉率字样。
    itd = json.load(open(os.path.join(SRC, "data", "items-detail.json"), encoding="utf-8"))["items"]
    name_count = {}
    for x in it:
        name_count[x["name"]] = name_count.get(x["name"], 0) + 1
    pick = next(x for x in it
                if name_count.get(x["name"]) == 1 and len((itd.get(str(x["id"])) or {}).get("st", [])) >= 3)
    exp = itd[str(pick["id"])]
    page.fill(".qsearch", pick["name"])
    page.wait_for_timeout(900)
    page.click(".itt tbody tr:first-child")
    page.wait_for_timeout(1200)
    dr = page.evaluate("""() => { const d = document.querySelector('.idrawer');
      if (!d) return { open: false };
      return { open: true, name: (d.querySelector('.idt .nm') || {}).innerText.trim(),
               st: d.querySelectorAll('.idl li').length,
               badges: d.querySelectorAll('.idbadge').length }; }""")
    check("新站物品详情抽屉：点行能开、名字与属性行数和数据一致",
          dr.get("open") and dr.get("name") == pick["name"] and dr.get("st") == len(exp.get("st", []))
          and dr.get("badges", 0) >= 1, json.dumps(dr, ensure_ascii=False))
    drtext = page.evaluate("() => (document.querySelector('.idrawer') || {}).innerText || ''")
    check("新站物品详情抽屉：没有掉率字样（红线）",
          "掉率" not in drtext and "掉落概率" not in drtext and "掉落几率" not in drtext, "干净")
    page.screenshot(path=os.path.join(SHOT_DIR, "app-items-detail.png"))
    page.click(".idmask")
    page.wait_for_timeout(300)
    check("新站物品详情抽屉：点遮罩能关",
          page.evaluate("() => !document.querySelector('.idrawer')"), "已关")

    # —— W2-3 全量后的层级核对（2026-10-16）：属性与卖价的取值顺序换成
    #    无限测试版客户端解包 > Beta 实测掉落 > 社区整理稿，而且三份的覆盖范围不一样，
    #    所以玩家能看出"这一条是按哪一份补的"就是硬要求：徽标必须与数据里的 stFrom/sellFrom 对齐。
    #    这张表与 ItemsPage.vue 的 FROMN 是同一份文字（页面文案不在数据里，只能两处各写一遍、
    #    在这里钉住）——改了页面不改这里，断言会红。
    FROMN = {"wclbox": "无限测试版 · 客户端解包", "gi": "beta 实测 · GearInsight 转述",
             "xr": "社区整理 · XR 助手转述"}
    itd_all = json.load(open(os.path.join(SRC, "data", "items-detail.json"), encoding="utf-8"))
    itd_items = itd_all["items"]
    st_from = {}
    for x in it:
        r = itd_items.get(str(x["id"])) or {}
        if r.get("stFrom"):
            st_from.setdefault(r["stFrom"], []).append(x)
    picks = []
    for key in ("wclbox", "gi", "xr"):
        cand = [x for x in st_from.get(key, [])
                if name_count.get(x["name"]) == 1 and len((itd_items.get(str(x["id"])) or {}).get("st", [])) >= 2]
        if cand:
            picks.append((key, cand[0]))
    check("物品详情三份来源都还有人看得见（不是只剩一份在撑页面）",
          len(picks) >= 2, "可各抽一件的来源：" + ",".join(k for k, _ in picks))
    for key, x in picks:
        page.fill(".qsearch", x["name"])
        page.wait_for_timeout(800)
        page.click(".itt tbody tr:first-child")
        page.wait_for_timeout(1100)
        dr2 = page.evaluate("""() => { const d = document.querySelector('.idrawer');
          if (!d) return null;
          const sec = [...d.querySelectorAll('.idsec')].map((s) => ({
            h: (s.querySelector('.idh3') || {}).innerText || '',
            badge: (s.querySelector('.idbadge') || {}).innerText || '',
            rows: s.querySelectorAll('.idl li').length }));
          return { name: (d.querySelector('.idt .nm') || {}).innerText.trim(), sec: sec,
                   note: (d.querySelector('.idnote') || {}).innerText || '' }; }""")
        got = next((s for s in (dr2 or {}).get("sec", []) if s["h"].startswith("属性")), None)
        check("物品详情「%s」这一件按%s补：徽标写的就是%s" % (x["name"], key, FROMN[key]),
              bool(dr2) and dr2["name"] == x["name"] and got and FROMN[key] in got["badge"]
              and got["rows"] == len(itd_items[str(x["id"])]["st"]),
              json.dumps(got, ensure_ascii=False)[:160])
        if key == "wclbox":
            # 抽屉底部那段口径说明改成从数据里取（meta.pageNote），页面不再另抄一份文案，
            # 这条断言钉住"改了源，页面跟着变"
            check("抽屉那段来源说明取自数据里的 pageNote，页面没另抄一份",
                  (dr2 or {}).get("note", "").strip() == (itd_all["meta"].get("pageNote") or "").strip()
                  and len((dr2 or {}).get("note", "")) > 30,
                  json.dumps((dr2 or {}).get("note", ""), ensure_ascii=False)[:150])
        page.screenshot(path=os.path.join(SHOT_DIR, "app-items-detail-%s.png" % key))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        page.fill(".qsearch", "")
        page.wait_for_timeout(500)
    # 名录标「无限中没有」而详情仍有属性的那些件：值只能来自实测或社区稿，挂上"无限测试版"的标
    # 就等于拿经典旧世的提示框冒充无限的数值（红线：不许编）。这类件在详情里有一千多件。
    miss = [x for x in it if x.get("status") == "missing"
            and (itd_items.get(str(x["id"])) or {}).get("st") and name_count.get(x["name"]) == 1]
    miss_wb = [x for x in miss if (itd_items.get(str(x["id"])) or {}).get("stFrom") == "wclbox"]
    check("数据层就没有「无限中没有却按无限解包取属性」的件",
          not miss_wb, "%d 件（应 0）" % len(miss_wb))
    if miss:
        x = miss[0]
        page.fill(".qsearch", x["name"])
        page.wait_for_timeout(800)
        page.click(".itt tbody tr:first-child")
        page.wait_for_timeout(1100)
        got3 = page.evaluate("""() => { const d = document.querySelector('.idrawer');
          if (!d) return null;
          const s = [...d.querySelectorAll('.idsec')].find((e) => (e.querySelector('.idh3') || {}).innerText.startsWith('属性'));
          return s ? (s.querySelector('.idbadge') || {}).innerText : null; }""")
        check("名录标无限中没有的「%s」在页面上没冒充无限解包" % x["name"],
              bool(got3) and FROMN["wclbox"] not in got3, json.dumps(got3, ensure_ascii=False)[:120])
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
    # —— 教益句那一段：图样/秘典/公式/设计图这类件，客户端把"教你学会制作X"放在斜体风味框里，
    #    参考站按类名把它当风味句丢、插件源整句带引号抄回。直接一刀切引号会让 1,197 件
    #    只剩"需要工程学 (125)"这种行（比上一版还倒退），所以它单独成段、单独标来源。
    use_rows = {k: v for k, v in itd_items.items() if v.get("use")}
    check("教益句收进了成品（图样/秘典那类件不再只剩一句需求等级）",
          len(use_rows) >= 1000, "%d 件" % len(use_rows))
    pick_u = next((x for x in it if str(x["id"]) in use_rows and name_count.get(x["name"]) == 1), None)
    if pick_u:
        page.fill(".qsearch", pick_u["name"])
        page.wait_for_timeout(800)
        page.click(".itt tbody tr:first-child")
        page.wait_for_timeout(1100)
        u = page.evaluate("""() => { const d = document.querySelector('.idrawer');
          if (!d) return null;
          const s = [...d.querySelectorAll('.idsec')].find((e) => (e.querySelector('.idh3') || {}).innerText.startsWith('学会'));
          return s ? { v: (s.querySelector('.idv') || {}).innerText,
                       badge: (s.querySelector('.idbadge') || {}).innerText } : null; }""")
        exp_u = use_rows[str(pick_u["id"])]
        # 徽标必须等于**这一件自己记的那个来源**（useFrom），不是"gi 或 xr 里随便一个都对"。
        # 原来这条写死了两个标签，A02 之后第一个被挑中的件（石板：不屈意志）那句是解包侧给的，
        # 页面显示得没错、断言却红了——那是期望过期，不是产品错。判据按数据取，只严不松：
        # useFrom 不在已知三家名单里同样算失败，防的是"来源写错也照样绿"。
        uf = exp_u.get("useFrom")
        check("「%s」的教益句按数据原样显示，且徽标等于这一件自己记的来源" % pick_u["name"],
              bool(u) and u["v"] == exp_u["use"] and uf in FROMN and u["badge"] == FROMN[uf],
              "%s / 数据记的来源 %s（%s）" % (json.dumps(u, ensure_ascii=False)[:120], uf,
                                              FROMN.get(uf, "不在名单里")))
        page.screenshot(path=os.path.join(SHOT_DIR, "app-items-detail-use.png"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
    # 整行引号的文案一条都不该出现在成品里（风味句），教益句则必须是去过引号的
    still_quoted = [s for r in itd_items.values() for s in ((r.get("st") or []) + [r.get("use") or ""])
                    if s and ((s.strip().startswith("“") and s.strip().endswith("”"))
                              or (s.strip().startswith('"') and s.strip().endswith('"')))]
    check("成品里没有整行带引号的文案（风味句红线；教益句已去引号）",
          not still_quoted, "%d 行（应 0）" % len(still_quoted))
    body_itd = page.evaluate("() => document.querySelector('#main').innerText")
    check("物品库说明已跟着改口：不再写「由两份客户端数据补齐」",
          "两份客户端数据" not in body_itd, "正文干净")
    # 风味句的尺子与 build-data 同一把：**整行**被引号包住的才算（"使用：解锁“炼金师”头衔"
    # 这类句中引号是功能文本本身，留着是对的，一刀切会把 8 条真信息删掉）。
    quoted_whole = [s for r in itd_items.values() for s in (r.get("st") or [])
                    if s.strip().startswith("“") and s.strip().endswith("”")]
    quoted_inner = [s for r in itd_items.values() for s in (r.get("st") or [])
                    if "“" in s and s not in quoted_whole]
    check("物品详情抽屉不带整行引号的风味句（红线）",
          not quoted_whole, "%d 行整句引号 / 另有 %d 行是句中引号（功能文本，允许）"
          % (len(quoted_whole), len(quoted_inner)))
    page.fill(".qsearch", "")
    page.wait_for_timeout(700)
    page.screenshot(path=os.path.join(SHOT_DIR, "app-items.png"))
    ctx.close()

    m = browser.new_context(viewport={"width": 375, "height": 780})
    mp = m.new_page()
    mp.goto(APP_BASE + "/#/", wait_until="networkidle")
    mp.wait_for_timeout(1600)
    mob = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
      const small = [...document.querySelectorAll('#main a, #main button, #top nav a, #top nav button')]
        .filter(b => { const r = b.getBoundingClientRect(); return r.width && r.height && r.height < 44; }).length;
      return { overflow: document.documentElement.scrollWidth > vw + 1, small: small }; }""")
    check("新站移动端首页不溢出、点击目标 ≥44px", not mob["overflow"] and mob["small"] == 0, json.dumps(mob))
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-index-mobile.png"), full_page=True)
    m.close()

    m = browser.new_context(viewport={"width": 375, "height": 780})
    mp = m.new_page()
    mp.goto(APP_BASE + "/#/items", wait_until="networkidle")
    mp.wait_for_timeout(1800)
    mit = mp.evaluate("""() => { const tr = document.querySelector('.itt tbody tr');
      return { overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
               card: tr ? getComputedStyle(tr).display === 'block' : false }; }""")
    check("新站物品库移动端：行卡片化、375 不横滚", not mit["overflow"] and mit["card"], json.dumps(mit))
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-items-mobile.png"), full_page=True)
    # 移动端抽屉：整宽、能开能关（物品线二批）
    mp.fill(".qsearch", pick["name"])
    mp.wait_for_timeout(900)
    mp.click(".itt tbody tr:first-child")
    mp.wait_for_timeout(1200)
    mid = mp.evaluate("""() => { const d = document.querySelector('.idrawer');
      if (!d) return { open: false };
      const vw = document.documentElement.clientWidth;
      return { open: true, w: d.getBoundingClientRect().width, vw: vw,
               overflow: document.documentElement.scrollWidth > vw + 1 }; }""")
    check("新站物品详情抽屉移动端：整宽、不横滚",
          mid.get("open") and abs(mid["w"] - mid["vw"]) <= 1 and not mid["overflow"], json.dumps(mid))
    mp.screenshot(path=os.path.join(SHOT_DIR, "app-items-detail-m.png"))
    m.close()


def test_search(browser, base):
    """全站搜索：索引完整性 + 首页框的结果分组 + 「跳进去确实筛好了」+ 倒计时到秒。
       只验界面接得住索引，不验索引对不对——那归 build-data.js 与溯源页管。"""
    print("\n[17] 全站搜索与倒计时")
    import json
    import re
    idx = json.load(open(os.path.join(SRC, "data", "search.json"), encoding="utf-8"))
    sc = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    kinds = idx["meta"]["kinds"]
    pages = sorted(set(kd[1] for kd in kinds.values()))
    check("索引板块指向的页面都真实存在",
          all(os.path.exists(os.path.join(SRC, p)) for p in pages), "%d 个页面" % len(pages))
    check("索引条数与规模快照一致", len(idx["items"]) == sc["search"],
          "JSON %d / scale %d" % (len(idx["items"]), sc["search"]))
    built = set(it[0] for it in idx["items"])
    check("每个板块都建了条目", built == set(kinds), "没条目的板块 %s" % sorted(set(kinds) - built))
    # M2 新接的两类：数据里每一条能上界面的都必须在索引里（差一条就是"页面接了、搜索忘了接"）
    sp_all = json.load(open(os.path.join(SRC, "data", "spells.json"), encoding="utf-8"))["spells"]
    ach_all = json.load(open(os.path.join(SRC, "data", "achievements.json"),
                             encoding="utf-8"))["achievements"]
    ach_show = [a for a in ach_all if not a.get("devOnly")]
    exp_spl = len(set((x["name"], "c=" + x["classId"]) for x in sp_all))
    exp_ach = len(set((x["name"], "g=" + x["gid"]) for x in ach_show))
    got_spl = len([it for it in idx["items"] if it[0] == "spl"])
    got_ach = len([it for it in idx["items"] if it[0] == "ach"])
    check("法术书全部进了搜索索引", got_spl == exp_spl, "索引 %d / 数据去重后 %d" % (got_spl, exp_spl))
    check("成就（能列的那些）全部进了搜索索引", got_ach == exp_ach,
          "索引 %d / 数据去重后 %d（开发埋点 %d 条不列）" % (got_ach, exp_ach, len(ach_all) - len(ach_show)))
    other_names = set(it[1] for it in idx["items"] if it[0] not in ("spl", "ach"))
    # 落地断言要挑一条"跳过去只可能是这一类"的名字。判据不是"全站不重名"——495 条法术名
    # 全都和改动清单重名（那是同一条法术在另一个板块的说法），而是**没有别的板块也落在这同一页**：
    # 首行取的是第一条命中，技能四态（abl）与法术书同页，撞名就会断言打到错误的行上。
    def pick_uniq_on_page(kind, src):
        page = kinds[kind][1]
        comp = set(it[1] for it in idx["items"]
                   if it[0] != kind and kinds[it[0]][1] == page)
        return next((x for x in src if x["name"] not in comp), None)
    uniq_spl = pick_uniq_on_page("spl", sp_all)
    uniq_ach = pick_uniq_on_page("ach", ach_show)
    check("法术书与成就各找得到一条不与同页板块撞名的条目用于落地断言",
          bool(uniq_spl) and bool(uniq_ach),
          "法术 %s / 成就 %s" % (uniq_spl and uniq_spl["name"], uniq_ach and uniq_ach["name"]))

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/index.html", wait_until="networkidle")
    page.wait_for_timeout(1300)
    ph = page.get_attribute("#gs", "placeholder") or ""
    check("首页搜索框写着索引条数", str(sc["search"]) in ph, ph)
    check("没输入时结果区不占屏", page.evaluate("() => document.querySelector('#gres').hidden"))

    page.fill("#gs", "这个词一定搜不到")
    page.wait_for_timeout(900)
    check("搜不到时直说没有", "索引里没有" in page.inner_text("#gres"),
          page.inner_text("#gres")[:40])

    page.fill("#gs", "潜行")
    page.wait_for_timeout(1300)
    grp = page.evaluate("() => [...document.querySelectorAll('#gres .gsh b')].map(x => x.textContent)")
    check("同一个词按板块分组列出", len(grp) >= 2, "、".join(grp))
    rows = page.evaluate("() => [...document.querySelectorAll('#gres .gsr')].map(a => a.getAttribute('href'))")
    check("每组先只列几条，总数受上限约束", 0 < len(rows) <= 5 * len(grp),
          "%d 条 / %d 组" % (len(rows), len(grp)))
    check("每条结果都跳到有数据的板块页",
          all(r.split("?")[0] in pages for r in rows), str(rows[:2]))
    subs = page.evaluate("() => [...document.querySelectorAll('#gres .gsr span')].map(s => s.textContent)")
    check("结果只写名称与归属，不夹句子", max(len(s) for s in subs) <= 44,
          "最长 %d 字" % max(len(s) for s in subs))
    lvs = page.evaluate("() => [...document.querySelectorAll('#gres .gsr .lv')].map(x => x.textContent)")
    # 2026-10-12 站主决定：搜索结果不挂分级文字，结果行只留名称与归属
    check("搜索结果不再挂分级文字", lvs == [], json.dumps(lvs[:3], ensure_ascii=False))
    page.screenshot(path=os.path.join(SHOT_DIR, "home-search-open.png"))

    def first_row(query, prefix):
        page.goto(base + "/index.html", wait_until="networkidle")
        page.wait_for_timeout(1200)
        page.fill("#gs", query)
        page.wait_for_timeout(1000)
        return page.evaluate("""(pre) => { const a = [...document.querySelectorAll('#gres .gsr')]
            .find(x => (x.getAttribute('href') || '').indexOf(pre) === 0);
          return a ? a.getAttribute('href') : null; }""", prefix)

    def rare_tab_on():
        return page.input_value("#wq") == "咆鼻" and "on" in page.get_attribute("[data-t=rares]", "class")

    LAND = [
        ("咆鼻", "world.html", rare_tab_on),
        ("莫高雷", "world.html", lambda: page.input_value("#wq") == "莫高雷"),
        ("舒适的睡袋", "world.html", lambda: "睡袋本身" in page.inner_text("#wbody")),
        ("领主大厅", "dungeon.html",
         lambda: page.evaluate("() => document.title").startswith("领主大厅")
         and page.evaluate("() => document.querySelectorAll('.brow').length") == 4),
        # 首领词条跳的是"那一座本的整页"，并且带首领号滚到那个首领那一栏
        ("法德林·安威玛尔", "dungeon.html",
         lambda: "&b=faldrim-anvilmar" in page.url
         and page.evaluate("() => !!document.getElementById('b-faldrim-anvilmar')")),
        ("预知", "talent.html",
         lambda: page.input_value("#tq") == "预知" and
         page.evaluate("() => [...document.querySelectorAll('.node')].filter(n => n.style.outline).length") >= 1),
        ("潜行者52型", "professions.html", lambda: page.input_value("#pq") == "潜行者52型"),
        ("强化英勇打击", "updates.html",
         lambda: page.input_value("#cq") == "强化英勇打击" and
         page.inner_text("#ccnt").strip() == "1 条"),
        ("影遁", "races.html",
         lambda: page.get_attribute(".racecard.on", "data-race") == "alliance-night-elf"
         and "影遁" in page.inner_text("#rdet")),
        ("影遁", "glossary.html", lambda: page.input_value("#q") == "影遁"),
        ("Molten Core", "raids.html", lambda: page.input_value("#rq") == "Molten Core"),
        ("兽人", "races.html",
         lambda: page.get_attribute(".racecard.on", "data-race") == "horde-orc"),
        # M2 新接的两类：法术名跳进技能页要把职业与词都带上，成就名跳进成就页要已筛好
        (uniq_spl["name"], "skills.html",
         lambda: page.input_value("#c") == uniq_spl["classId"]
         and page.input_value("#q") == uniq_spl["name"]
         and page.evaluate("() => document.querySelectorAll('#sptbl tbody tr:not(.grp2h)').length") >= 1),
        (uniq_ach["name"], "achievements.html",
         lambda: page.input_value("#q") == uniq_ach["name"]
         and page.input_value("#g") == uniq_ach["gid"]
         and page.evaluate("() => document.querySelectorAll('#tbl tbody tr:not(.grp2h)').length") >= 1),
    ]
    for query, prefix, judge in LAND:
        href = first_row(query, prefix)
        if not href:
            check("搜索结果里有 %s（%s）" % (prefix, query), False, "索引没给这条")
            continue
        page.goto(base + "/" + href, wait_until="networkidle")
        page.wait_for_timeout(1500 if prefix in ("talent.html", "races.html") else 1100)
        check("跳进 %s 后已经筛好（%s）" % (prefix, query), bool(judge()), href)
    ctx.close()

    ctx2 = browser.new_context(viewport={"width": 1440, "height": 1000})
    p2 = ctx2.new_page()
    p2.goto(base + "/index.html", wait_until="networkidle")
    p2.wait_for_timeout(1200)
    t1 = p2.inner_text("#cdT").strip()
    chip = p2.inner_text("#lchip")
    meta = json.load(open(os.path.join(SRC, "data", "meta.json"), encoding="utf-8"))
    check("首页倒计时精确到秒", re.match(r"^\d{2}:\d{2}:\d{2}$", t1) is not None, t1)
    check("顶栏那条与首页同一读数", chip.count(":") == 2 and "天" in chip, chip)
    check("倒计时写的就是 meta.json 那个上线日", meta["launch"] in p2.inner_text(".heros"),
          p2.inner_text(".heros")[:48].replace("\n", " "))
    p2.wait_for_timeout(2200)
    check("倒计时每秒在走", p2.inner_text("#cdT").strip() != t1,
          "%s → %s" % (t1, p2.inner_text("#cdT").strip()))
    ctx2.close()

    m = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    mp = m.new_page()
    mp.goto(base + "/index.html", wait_until="networkidle")
    mp.wait_for_timeout(1200)
    mp.fill("#gs", "睡袋")
    mp.wait_for_timeout(1100)
    small = mp.evaluate("""() => [...document.querySelectorAll('#main button, #main a, #main input')]
        .filter(e => { const b = e.getBoundingClientRect();
          return b.width > 0 && b.height > 0 && Math.min(b.width, b.height) < 44; })
        .map(e => e.tagName + '.' + e.className)""")
    check("移动端展开结果后点击目标仍 ≥44px", not small, json.dumps(small[:3], ensure_ascii=False))
    mp.screenshot(path=os.path.join(SHOT_DIR, "home-search-mobile.png"))
    m.close()
    check("搜索这一轮无脚本报错", not errs, "; ".join(errs[:2]))


def test_legacy(browser, base):
    """传承页：格子数、未公开槽、点数与分级徽标都要能对上 legacy.json，
       并且这条红线要有证据——每层效果说明不许出现在渲染文字里（详情卡只许一句话的长度）。"""
    print("\n[19] 传承页：三棵专长树与 65 项挑战")
    import json
    L = json.load(open(os.path.join(SRC, "data", "legacy.json"), encoding="utf-8"))
    cnt = L["meta"]["counts"]
    rules = L["meta"]["rules"]
    total = sum(len(c["items"]) for c in L["challenges"])
    by_tree = {t["id"]: t for t in L["trees"]}
    named_by_tree = {}
    for t in L["trees"]:
        named_by_tree[t["id"]] = len([s for s in t["slots"] if not s["empty"] and not s["unknown"]])

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs, bad = [], []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.on("response", lambda r: bad.append(r.url) if r.status >= 400 and not tolerated(r.url) else None)
    page.goto(base + "/legacy.html", wait_until="networkidle")
    page.wait_for_timeout(1400)
    check("传承页无脚本报错", not errs, "; ".join(errs[:2]))
    check("传承页无非白名单失败请求", not bad, "; ".join(bad[:2]))

    def snap():
        return page.evaluate("""() => ({
          h1: [...document.querySelectorAll('#main h1')].map(e => e.innerText.trim()),
          stats: [...document.querySelectorAll('.stats .stat b')].map(e => +e.textContent),
          tabs: [...document.querySelectorAll('.picks [data-t]')].map(e => e.dataset.t),
          onTab: (document.querySelector('.picks [data-t].on') || {}).dataset,
          treeName: (document.querySelector('#ltree h2') || {}).innerText,
          cells: [...document.querySelectorAll('#ltree .lslot')].map(e => e.className),
          names: [...document.querySelectorAll('#ltree .lslot .nm')].map(e => e.innerText.trim()),
          unkTxt: [...document.querySelectorAll('#ltree .lslot.unk')].map(e => e.innerText.trim()),
          ranks: [...document.querySelectorAll('#ltree .rk')].map(e => e.innerText.trim()),
          det: [...document.querySelectorAll('#ldet .ldetail h2')].map(e => e.innerText.replace(/\\n/g, ' ')),
          detTxt: ((document.getElementById('ldet') || {}).innerText || ''),
          detBody: (() => { const d = document.getElementById('ldet'); if (!d) return '';
            const c = d.cloneNode(true); c.querySelectorAll('.src').forEach(e => e.remove());
            return (c.textContent || '').replace(/\\s+/g, ' ').trim(); })(),
          detSrc: document.querySelectorAll('#ldet .src a').length,
          detPill: [...document.querySelectorAll('#ldet .pill')].map(e => e.innerText.trim()),
          on: [...document.querySelectorAll('#ltree .lslot.on')].length,
          cnt: (document.getElementById('lcnt') || {}).innerText,
          chRows: document.querySelectorAll('#lch .ltab tbody tr').length,
          chPills: [...document.querySelectorAll('#lch .pill')].map(e => e.innerText.trim()),
          pts: [...document.querySelectorAll('#lch .ltab tbody tr td:last-child')].map(e => e.innerText.trim()),
          reRows: document.querySelectorAll('#main > .card').length,
          reRewards: (() => { const t = [...document.querySelectorAll('#main table.ltab')].pop();
            return t ? t.querySelectorAll('tbody tr').length : 0; })(),
          rePill: [...document.querySelectorAll('#main table .pill')].map(e => e.innerText.trim()).slice(-4),
          src: document.querySelectorAll('#main .src').length,
          hot: [...document.querySelectorAll('img')].filter(i => /^https?:/.test(i.getAttribute('src') || '')).length,
          local: [...document.querySelectorAll('img')].filter(i => !(i.getAttribute('src') || '').startsWith('img/')).length
        })""")

    s0 = snap()
    check("传承页只有一个 H1", len(s0["h1"]) == 1, json.dumps(s0["h1"], ensure_ascii=False))
    check("页顶四个规模数等于 legacy.json（专长/未公开/挑战/奖励）",
          s0["stats"] == [cnt["perks"], cnt["unknownSlots"], total, cnt["rewards"]],
          "页面 %s / 数据 %s" % (s0["stats"], [cnt["perks"], cnt["unknownSlots"], total, cnt["rewards"]]))
    check("三棵传承树都在且顺序与数据一致", s0["tabs"] == [t["id"] for t in L["trees"]],
          json.dumps(s0["tabs"], ensure_ascii=False))
    # 点数不是"每条都一样"：客户端明细里 65 项各 1 点、有一项 16 点。
    # 断言因此改成"每行的点数都必须在数据声明过的取值里"——出现没声明过的点数才是回归。
    allowed = {str(rules["pointPerChallenge"])} | {str(v["points"]) for v in rules.get("pointVariants") or []}
    check("挑战每条点数都在数据声明过的取值里，且行内不再挂分级徽标",
          not s0["chPills"] and set(s0["pts"]) <= allowed,
          "徽标 %d 个 / 行 %d / 点数集合 %s（允许 %s）" % (
              len(s0["chPills"]), s0["chRows"],
              json.dumps(sorted(set(s0["pts"])), ensure_ascii=False), sorted(allowed)))
    check("进度奖励每一档都在表里，且不再挂待实测徽标",
          not s0["rePill"] and s0["reRewards"] == cnt["rewards"],
          json.dumps({"rePill": s0["rePill"], "奖励行": s0["reRewards"], "数据": cnt["rewards"]},
                     ensure_ascii=False))
    check("图全部是本地文件，没有热链", s0["hot"] == 0 and s0["local"] == 0,
          "外链 %d / 非 img 目录 %d" % (s0["hot"], s0["local"]))
    # 2026-10-12 站主决定：分级徽标与来源块退出内容页，出处集中在溯源页说。
    check("传承页不再挂来源块", s0["src"] == 0, "%d 块来源" % s0["src"])

    # 逐棵树核对格子：矩形格子数 = 行×列，具名 + 未公开 + 空格三者必须刚好铺满
    per_tree = []
    for tid in s0["tabs"]:
        page.evaluate("(id) => { const b = [...document.querySelectorAll('.picks [data-t]')]"
                      ".find(x => x.dataset.t === id); if (b) b.click(); }", tid)
        page.wait_for_timeout(500)
        s = snap()
        t = by_tree[tid]
        expect_cells = t["rows"] * t["cols"]
        per_tree.append({
            "id": tid, "cells": len(s["cells"]), "named": len(s["names"]),
            "unk": s["cells"].count("lslot unk"), "empty": s["cells"].count("lslot none"),
            "name": (s["treeName"] or "").replace("\n", " "), "unkTxt": s["unkTxt"], "ranks": s["ranks"],
        })
    check("每棵树画的格子数 = 行 × 列（空格也画出来，位置才是客户端里的位置）",
          all(x["cells"] == by_tree[x["id"]]["rows"] * by_tree[x["id"]]["cols"] for x in per_tree),
          json.dumps([{k: x[k] for k in ("id", "cells")} for x in per_tree], ensure_ascii=False))
    check("具名专长 + 未公开 + 空格 = 格子总数，且具名数与数据一致",
          all(x["named"] + x["unk"] + x["empty"] == x["cells"] and
              x["named"] == named_by_tree[x["id"]] for x in per_tree),
          json.dumps([{k: x[k] for k in ("id", "named", "unk", "empty")} for x in per_tree], ensure_ascii=False))
    check("未公开槽位用文字交代（不是只靠一个虚线框）",
          all(x["unk"] == 0 or all("未公开" in u for u in x["unkTxt"]) for x in per_tree),
          json.dumps([x["unkTxt"][:1] for x in per_tree], ensure_ascii=False))
    check("三棵树加起来正好 21 个具名专长、6 格未公开",
          sum(x["named"] for x in per_tree) == cnt["perks"] and
          sum(x["unk"] for x in per_tree) == cnt["unknownSlots"],
          "具名 %d / 未公开 %d（应 %d / %d）" % (
              sum(x["named"] for x in per_tree), sum(x["unk"] for x in per_tree),
              cnt["perks"], cnt["unknownSlots"]))
    check("每个格子的层数上限都写出来了（没有的写 ?，不许留空）",
          all(re.match(r"^\d+ 层$|^\?$", r) for x in per_tree for r in x["ranks"]),
          json.dumps([x["ranks"][:3] for x in per_tree], ensure_ascii=False))

    # 点开一格看详情：详情卡必须短，长起来就说明把每层效果说明抄回来了
    page.evaluate("() => document.querySelector('#ltree .lslot[data-perk]').click()")
    page.wait_for_timeout(500)
    s1 = snap()
    first_id = page.evaluate("() => document.querySelector('#ltree .lslot[data-perk]').dataset.perk")
    perk = [p for p in L["perks"] if p["id"] == first_id][0]
    check("点格子展开该专长的详情（名字、上限、前置、位置）",
          len(s1["det"]) == 1 and s1["on"] == 1 and perk["nameCn"] in s1["det"][0],
          json.dumps({"det": s1["det"][:1], "on": s1["on"], "id": first_id}, ensure_ascii=False))
    check("详情里不再挂分级徽标与来源块",
          not s1["detPill"] and s1["detSrc"] == 0,
          json.dumps({"pill": s1["detPill"], "src": s1["detSrc"]}, ensure_ascii=False))
    # 长度这条是红线的兜底：详情只剩名称/层数/归属/位置/前置。
    # 谁把每层效果说明抄回来，这段正文一定会撑破 200 字。
    check("详情没把每层效果说明抄回来（≤200 字，且仍给归属/位置/前置）",
          len(s1["detBody"]) <= 200 and "位置" in s1["detBody"] and "前置" in s1["detBody"],
          "详情正文 %d 字：%s" % (len(s1["detBody"]), s1["detBody"][:90]))
    page.evaluate("() => document.querySelector('#ltree .lslot[data-perk]').click()")
    page.wait_for_timeout(400)
    check("再点一次收起，同一时刻只许有一个选中格",
          len(snap()["det"]) == 0 and snap()["on"] == 0, json.dumps(snap()["det"], ensure_ascii=False))
    # 收起后右侧不许留白：给一个告诉玩家"点哪儿"的空态
    es = page.evaluate("""() => { const e = document.querySelector('#ldet .leempty');
      return { has: !!e, txt: e ? e.innerText.replace(/\\n/g, ' ').slice(0, 20) : '' }; }""")
    check("没选专长时那块给的是空态说明，不是留白",
          es["has"] and "点一个专长" in es["txt"], json.dumps(es, ensure_ascii=False))

    # 挑战搜索：命中数、计数行、空态
    page.evaluate("() => { const i = document.getElementById('lq'); i.value = '25级'; i.oninput(); }")
    page.wait_for_timeout(500)
    s2 = snap()
    n25 = len([x for c in L["challenges"] for x in c["items"]
               if "25级" in ((x.get("nameCn") or "") + " " + (x.get("requirement") or "") + " " +
                             (x.get("sub") or "") + " " + (x.get("group") or ""))])
    check("搜「25级」筛出 %d 条，计数行跟着走" % n25,
          s2["chRows"] == n25 and s2["cnt"] == "%d / %d 项" % (n25, total),
          json.dumps({"rows": s2["chRows"], "cnt": s2["cnt"], "应": n25}, ensure_ascii=False))
    page.evaluate("() => { const i = document.getElementById('lq'); i.value = 'zzz不存在'; i.oninput(); }")
    page.wait_for_timeout(400)
    s3 = snap()
    empty = page.evaluate("() => [...document.querySelectorAll('#lch .empty')].map(e => e.innerText)")
    check("搜不到时给的是玩家能照着改的空态，不是空白",
          s3["chRows"] == 0 and len(empty) == 1 and "试试" in empty[0],
          json.dumps(empty[:1], ensure_ascii=False))
    page.evaluate("() => { const i = document.getElementById('lq'); i.value = ''; i.oninput(); }")
    page.wait_for_timeout(300)
    # 分组卡必须是整块：第一版把它套在 .lgrp（别处是一行 flex 的分组条）上，
    # 结果表格被挤成 487px 靠右摆、图标按原图 56px 把行高撑到 110px，人眼一看才发现。
    tbl = page.evaluate("""() => { const g = document.querySelector('#lch .lchgrp');
      if (!g) return null;
      const tr = g.querySelector('tbody tr').getBoundingClientRect();
      const ico = g.querySelector('tbody tr .liw');
      const sx = g.querySelector('.scrollx').getBoundingClientRect();
      const card = g.getBoundingClientRect();
      return { rowH: Math.round(tr.height), icoW: ico ? Math.round(ico.getBoundingClientRect().width) : 0,
               fill: +(sx.width / card.width).toFixed(2), groups: document.querySelectorAll('#lch .lchgrp').length }; }""")
    check("挑战表用全站统一的 26px 图标格，行高没被撑开",
          tbl and tbl["icoW"] == 26 and tbl["rowH"] <= 60, json.dumps(tbl, ensure_ascii=False))
    check("分组卡整块铺开，表格宽度占满卡片", tbl and tbl["fill"] > 0.95 and tbl["groups"] == 6,
          json.dumps(tbl, ensure_ascii=False))
    # 组名与计数必须分开摆：套 flex 规则前实测连成「职业27 项」这种读法
    h2p = page.evaluate("""() => { const h = document.querySelector('#lch .lchgrp h2');
      const s = h.querySelector('span'); const hb = h.getBoundingClientRect(), sb = s.getBoundingClientRect();
      return { spread: sb.right >= hb.right - 8, nameW: Math.round(hb.width - sb.width) }; }""")
    check("分组标题的计数靠右，不与组名连读", h2p["spread"], json.dumps(h2p, ensure_ascii=False))
    # 截图要拍默认状态：树回到第一棵、并排那格摆一个打开的详情
    page.evaluate("(id) => { const b = [...document.querySelectorAll('.picks [data-t]')]"
                  ".find(x => x.dataset.t === id); if (b) b.click(); }", L["trees"][0]["id"])
    page.wait_for_timeout(400)
    page.evaluate("() => document.querySelector('#ltree .lslot[data-perk]').click()")
    page.wait_for_timeout(400)
    lay = page.evaluate("""() => { const t = document.querySelector('#ltree').getBoundingClientRect();
      const d = document.querySelector('#ldet .ldetail').getBoundingClientRect();
      return { right: d.left >= t.right - 4, gridW: document.querySelector('.lgrid').getBoundingClientRect().width }; }""")
    check("桌面是「树在左、详情在右」并排（详情原来落在下面，右侧一大片空）",
          lay["right"] and lay["gridW"] <= 520, json.dumps(lay, ensure_ascii=False))
    page.screenshot(path=os.path.join(SHOT_DIR, "legacy-desktop.png"), full_page=True)
    check("传承这一轮无脚本报错", not errs, "; ".join(errs[:2]))
    ctx.close()

    # 深链：从首页搜索带专长名跳进来 → 直接展开那条，而且不许把下面的挑战筛选抢掉
    dc = browser.new_context(viewport={"width": 1440, "height": 1000})
    dp = dc.new_page()
    target = [p for p in L["perks"] if p["treeId"] != L["trees"][0]["id"]][0]
    dp.goto("%s/legacy.html?q=%s" % (base, urllib.parse.quote(target["nameCn"])),
            wait_until="networkidle")
    dp.wait_for_timeout(1300)
    deep = dp.evaluate("""() => ({
      det: [...document.querySelectorAll('#ldet .ldetail h2')].map(e => e.innerText.replace(/\\n/g, ' ')),
      on: document.querySelectorAll('#ltree .lslot.on').length,
      onTab: (document.querySelector('.picks [data-t].on') || {}).dataset,
      lq: (document.getElementById('lq') || {}).value,
      cnt: (document.getElementById('lcnt') || {}).innerText })""")
    check("带专长名跳进来：落在它所在的树上并直接展开详情",
          len(deep["det"]) == 1 and target["nameCn"] in deep["det"][0] and deep["on"] == 1 and
          (deep["onTab"] or {}).get("t") == target["treeId"],
          json.dumps(deep, ensure_ascii=False))
    check("跳进来后挑战不被误筛（搜索框留空，仍是全部 %d 项）" % total,
          deep["lq"] == "" and deep["cnt"] == "%d / %d 项" % (total, total),
          json.dumps({"lq": deep["lq"], "cnt": deep["cnt"]}, ensure_ascii=False))
    dp.goto("%s/legacy.html?t=%s" % (base, L["trees"][-1]["id"]), wait_until="networkidle")
    dp.wait_for_timeout(1200)
    tid = dp.evaluate("() => (document.querySelector('.picks [data-t].on') || {}).dataset")
    check("带 ?t= 跳进来直接切到那棵树", (tid or {}).get("t") == L["trees"][-1]["id"],
          json.dumps(tid, ensure_ascii=False))
    dp.goto("%s/legacy.html?t=不存在" % base, wait_until="networkidle")
    dp.wait_for_timeout(1200)
    fell = dp.evaluate("() => document.querySelectorAll('#ltree .lslot').length")
    check("乱写的 ?t= 不会把页面搞成空白（退回第一棵）", fell == by_tree[L["trees"][0]["id"]]["rows"] *
          by_tree[L["trees"][0]["id"]]["cols"], "%d 格" % fell)
    dc.close()

    # 375px：格子是这页最容易挤的地方，横向不溢出 + 点击目标够大 + 名字不能被吃掉
    m = browser.new_context(viewport={"width": 375, "height": 780})
    mp = m.new_page()
    mp.goto(base + "/legacy.html", wait_until="networkidle")
    mp.wait_for_timeout(1400)
    mm = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
      const cells = [...document.querySelectorAll('#ltree .lslot')];
      const small = [...document.querySelectorAll('#main button, #main a, #main input')]
        .filter(e => { const b = e.getBoundingClientRect();
          return b.width > 0 && b.height > 0 && Math.min(b.width, b.height) < 44; })
        .map(e => e.tagName + '.' + e.className);
      const grid = document.querySelector('.lgrid').getBoundingClientRect();
      return { over: document.documentElement.scrollWidth - vw, small: small,
               named: cells.filter(c => c.querySelector('.nm')).length,
               nameless: cells.filter(c => c.querySelector('.nm') && !c.querySelector('.nm').innerText.trim()).length,
               gridW: grid.width, vw: vw,
               unkHasText: [...document.querySelectorAll('.lslot.unk')].every(e => e.innerText.includes('未公开')),
               tabMin: Math.min(...[...document.querySelectorAll('.picks [data-t]')]
                 .map(e => e.getBoundingClientRect().height)) }; }""")
    check("移动端不横向溢出", mm["over"] <= 0, "溢出 %dpx" % mm["over"])
    check("移动端点击目标都 ≥44px（含切树按钮 %.0fpx）" % mm["tabMin"], not mm["small"],
          json.dumps(mm["small"][:3], ensure_ascii=False))
    check("移动端格子仍画得下且不把专长名吞成空",
          mm["named"] == 7 and mm["nameless"] == 0 and mm["gridW"] <= mm["vw"],
          json.dumps({k: mm[k] for k in ("named", "nameless", "gridW", "vw")}))
    check("移动端的未公开格也带文字说明", mm["unkHasText"], "看未公开格的文字")
    mp.evaluate("() => document.querySelector('#ltree .lslot[data-perk]').click()")
    mp.wait_for_timeout(400)
    mlay = mp.evaluate("""() => { const t = document.querySelector('#ltree').getBoundingClientRect();
      const d = document.querySelector('#ldet .ldetail').getBoundingClientRect();
      const vw = document.documentElement.clientWidth;
      return { below: d.top >= t.bottom - 4, over: d.right > vw }; }""")
    check("移动端详情回到树卡下面而不是并排（窄屏并排会把格子挤没）", mlay["below"] and not mlay["over"],
          json.dumps(mlay, ensure_ascii=False))
    mp.screenshot(path=os.path.join(SHOT_DIR, "legacy-mobile.png"), full_page=True)
    m.close()


def test_classes(browser, base):
    """职业页（docs/PLAN-classes-and-nav-2026-10-12.md 第二节）。
       这一页的红线是"内容一条都不许写死"，所以判据全部拿 src/data 里的数去对页面文本：
       页面上那个数与 JSON 现算的数不一致，就是渲染漏了或抄成了常数。"""
    print("\n[21] 职业页 classes.html")
    import json

    def j(*p):
        return json.load(open(os.path.join(SRC, *p), encoding="utf-8"))

    cl = j("data", "classes.json")["classes"]
    byid = {c["id"]: c for c in cl}
    war = j("data", "talents", "warrior.json")
    ch = j("data", "changes.json")["items"]
    rc = j("data", "races.json")
    ab = j("data", "abilities.json")
    sc = j("data", "scale.json")["scale"]
    war_nodes = sum(len(t.get("nodes") or []) for t in war["trees"])
    war_chg = [x for x in ch if x.get("classId") == "warrior"]
    war_races = [r for r in rc["races"] if "warrior" in (r.get("classes") or [])]
    war_abs = [x for x in (ab.get("items") or []) if x.get("classId") == "warrior"]
    arms = len([x for x in war_chg if x.get("tree") == "武器"])
    # 战士的改动分几档就渲染几张表：四态之外（换层 / 改名 / 学得更早…）合并成"其它说法"一档
    CL_KEYS = ("added", "modified", "removed", "unchanged")
    war_groups = len({(x.get("changeKind") if x.get("changeKind") in CL_KEYS else "other")
                      for x in war_chg})
    # 职业色的唯一来源是 glyph.js 那张表，断言也从那里读，不再抄一份十六进制
    gtxt = open(os.path.join(SRC, "js", "glyph.js"), encoding="utf-8").read()
    mg = re.search(r"warrior:\s*'(#[0-9a-fA-F]{6})'", gtxt)
    war_rgb = ""
    if mg:
        war_rgb = "rgb(%d, %d, %d)" % tuple(int(mg.group(1)[i:i + 2], 16) for i in (1, 3, 5))

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))
    page.goto(base + "/classes.html?c=warrior", wait_until="networkidle")
    page.wait_for_timeout(1500)
    st = page.evaluate("""() => {
      const t = (s) => { const e = document.querySelector(s); return e ? e.innerText.replace(/\\s+/g, ' ').trim() : ''; };
      const cs = (s, p) => { const e = document.querySelector(s); return e ? getComputedStyle(e)[p] : ''; };
      const hero = document.querySelector('.clhero'), chart = document.querySelector('.chart');
      const on = document.querySelector('nav.main a.nl.on');
      let onb = null;
      if (on) { const c = on.cloneNode(true); c.querySelectorAll('.nb').forEach(n => n.remove());
        onb = { t: c.textContent.trim(), href: on.getAttribute('href'), badge: !!on.querySelector('.nb'),
                group: (on.closest('.ngrp').querySelector('.ngt') || {}).textContent.trim() }; }
      return {
        h1: t('#main h1'), kicker: t('.clhero .kicker'),
        enColor: cs('.clen', 'color'), chartBorder: cs('.chart', 'borderTopColor'),
        heroH: hero ? Math.round(hero.getBoundingClientRect().height) : 0,
        chartW: chart ? Math.round(chart.getBoundingClientRect().width) : 0,
        heroLine: t('.clhero .clline'), artMark: t('.clhero .dmark'),
        specs: [...document.querySelectorAll('.spec')].map(s => s.innerText.replace(/\\s+/g, ' ').trim()),
        specTitles: [...document.querySelectorAll('.spec')].map(s => s.getAttribute('title') || ''),
        pressed: [...document.querySelectorAll('.spec')].map(s => s.getAttribute('aria-pressed')),
        rows: document.querySelectorAll('#main table tbody tr').length,
        cols: (() => { const t = document.querySelector('#main table.chtab');
          return t ? t.querySelectorAll('thead th').length : 0; })(),
        chgTables: document.querySelectorAll('#main table.chtab').length,
        rowIcons: document.querySelectorAll('#main table.chtab tbody td.ich .liw').length,
        actCells: document.querySelectorAll('#main table.chtab tbody td.act').length,
        rowPills: document.querySelectorAll('#main table.chtab tbody .pill').length,
        chgsBox: (() => { const b = document.querySelector('.chgs'); if (!b) return null;
          const cs = getComputedStyle(b);
          return { maxH: cs.maxHeight, scroll: b.scrollHeight > b.clientHeight + 40 }; })(),
        chgHead: t('.two .card:nth-of-type(2) h2'),
        kvs: [...document.querySelectorAll('.kv')].map(x => x.innerText.replace(/\\s+/g, ' ').trim()),
        chips: [...document.querySelectorAll('.racerow .tag')].map(x => x.innerText.trim()),
        gaps: [...document.querySelectorAll('ol.q li')].map(x => x.innerText.trim()),
        exits: [...document.querySelectorAll('.tools6 a')].map(a => a.getAttribute('href')),
        srcBtns: document.querySelectorAll('#main [data-src]').length,
        quotes: document.querySelectorAll('#main .quote').length,
        broken: [...document.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0).length,
        on: onb };
    }""")
    check("职业页没有脚本报错、没有坏图", not errs and st["broken"] == 0,
          "报错 %s / 坏图 %d" % (errs[:2], st["broken"]))
    check("页首带 300px、立绘框 158px，英文原名与框边都吃职业色",
          st["heroH"] == 300 and st["chartW"] == 158 and st["enColor"] == war_rgb
          and st["chartBorder"] == war_rgb,
          "带高 %s / 框宽 %s / 英文字色 %s / 期望 %s" % (st["heroH"], st["chartW"], st["enColor"], war_rgb))
    check("页首写的是职业自己的名字与英文原名，不机翻不硬凑",
          "战士" in st["h1"] and "Warrior" in st["h1"] and st["kicker"] == "CLASS · WARRIOR",
          "%s ／ %s" % (st["h1"], st["kicker"]))
    check("页首读数与数据现算一致（节点数、改动条数都来自 JSON）",
          str(war_nodes) in st["heroLine"] and str(len(war_chg)) in st["heroLine"]
          and str(len(war_abs)) in st["heroLine"], st["heroLine"])
    check("页首不再挂素材出处角标（2026-10-12 站主决定，出处集中在溯源页）",
          not st["artMark"], st["artMark"])
    check("三系卡就是那一职业的三系，卡上是系名与节点数",
          len(st["specs"]) == 3 and all(t["nameCn"] in s for t, s in zip(war["trees"], st["specs"]))
          and all(str(len(t["nodes"])) in s for t, s in zip(war["trees"], st["specs"])),
          json.dumps(st["specs"], ensure_ascii=False))
    check("两源叫法不同的系，红框悬停把另一个叫法说清楚",
          st["specTitles"] == ["", "", ""], "战士无分歧：%s" % json.dumps(st["specTitles"], ensure_ascii=False))
    check("每条改动占一行，行数与数据一致；行首带图标",
          st["rows"] == len(war_chg) and st["rowIcons"] >= len(war_chg) - 1,
          "行 %d（改动 %d 条）/ 行内图标 %d" % (st["rows"], len(war_chg), st["rowIcons"]))
    check("表格只剩名称 / 类别 / 哪一系三列（分级徽标与来源两列按用户反馈撤了）",
          st["cols"] == 3 and st["actCells"] == 0 and st["rowPills"] == 0
          and st["chgTables"] == war_groups,
          "每表 %d 列 / 分档 %d 张（数据 %d 档）/ 来源格 %d / 行内徽标 %d"
          % (st["cols"], st["chgTables"], war_groups, st["actCells"], st["rowPills"]))
    check("官方中文整句按名字对上，贴的是整句不是改写",
          st["quotes"] == len(war_abs), "页内整句 %d / 数据 %d" % (st["quotes"], len(war_abs)))
    page.click(".spec >> nth=0")
    page.wait_for_timeout(1200)
    one = page.evaluate("""() => ({ rows: document.querySelectorAll('#main table tbody tr').length,
      head: (document.querySelector('.two .card:nth-of-type(2) h2') || {}).innerText || '',
      pressed: [...document.querySelectorAll('.spec')].map(s => s.getAttribute('aria-pressed')) })""")
    check("点一系就把技能变化收到那一系，条数与选中态同步",
          one["rows"] == arms and "只看 武器" in one["head"] and one["pressed"][0] == "true",
          json.dumps({"行": one["rows"], "标题": one["head"][:24], "选中": one["pressed"]}, ensure_ascii=False))
    page.click(".spec >> nth=0")
    page.wait_for_timeout(1100)
    check("再点一次回到三系都列",
          page.evaluate("document.querySelectorAll('#main table tbody tr').length") == len(war_chg))
    check("长列在卡内封顶滚动，不把两栏拉成一长一短",
          bool(st["chgsBox"]) and st["chgsBox"]["maxH"].endswith("px") and st["chgsBox"]["scroll"],
          json.dumps(st["chgsBox"], ensure_ascii=False))
    check("可选种族用 races.json 的正式中文名，一个阵营一行全列出来",
          len(st["chips"]) == len(war_races) and "塑风者天裔" in st["chips"]
          and "高阶会天裔" in st["chips"], "%d 个：%s" % (len(st["chips"]), st["chips"]))
    check("天裔两份说法没对上时，这一页也摆出来而不是藏起来（红线：两源分歧两个都留）",
          page.evaluate("() => { const c = document.querySelector('#main .conf');"
                        "return c ? c.innerText : ''; }").count("天裔") >= 1)
    check("左栏每一行都是现取的数，含资料完整度与两源分歧",
          len(st["kvs"]) >= 8 and any("资料完整度" in x for x in st["kvs"])
          and any(str(war_nodes) in x for x in st["kvs"]), "%d 行" % len(st["kvs"]))
    check("底部三个出口指向计算器、技能书与玩法问答",
          st["exits"] == ["talent.html?c=warrior", "skills.html", "chooser.html"], str(st["exits"]))
    check("页尾那张「本页还没确认的」卡已撤，只留一句层级门槛的口径",
          not st["gaps"] and "第几层要点满多少还没在正式服实测"
          in page.evaluate("() => document.querySelector('#main').innerText"))
    # 2026-10-12 站主决定：逐条来源按钮整批撤下，出处集中在溯源页——这里改成反向断言，
    # 免得下次有人把「来源」按钮顺手加回左栏那两行。
    check("本页没有任何来源按钮与来源展开块",
          st["srcBtns"] == 0 and page.evaluate(
              "() => ![...document.querySelectorAll('.srcbox')].some(b => b.innerText.trim())"),
          "来源按钮 %d 个" % st["srcBtns"])
    page.click(".cls[data-c='hunter']")
    page.wait_for_timeout(1400)
    sw = page.evaluate("""() => ({ url: location.search,
      h1: (document.querySelector('#main h1') || {}).innerText,
      rows: document.querySelectorAll('#main table tbody tr').length,
      specs: [...document.querySelectorAll('.spec b')].map(b => b.innerText.trim()) })""")
    check("换职业是同一页换数据：地址、标题、条数与三系一起变",
          "c=hunter" in sw["url"] and "猎人" in sw["h1"] and sw["rows"] > 0
          and sw["specs"] != ["武器", "狂怒", "防护"], json.dumps(sw, ensure_ascii=False))
    page.goto(base + "/classes.html?c=paladin", wait_until="networkidle")
    page.wait_for_timeout(1400)
    pal = page.evaluate("""() => { const t = document.querySelector('#main').innerText;
      return { abs: [...document.querySelectorAll('.kv')].map(x => x.innerText).find(s => /技能说明/.test(s)) || '',
               heroNote: (document.querySelector('.clhero .clnote') || {}).innerText || '',
               quotes: document.querySelectorAll('#main .quote').length,
               rows: document.querySelectorAll('#main table tbody tr').length }; }""")
    # 页首那句"天赋名与上限已入库（第三方数据挖掘，待实测）"是给维护者看的备注，已撤；
    # 但"这个职业还没有官方中文整句"是数据事实，留在左栏那一行里。
    check("官方中文稿还没发的职业：左栏直说没有，页首不再挂维护者备注",
          "还没有" in pal["abs"] and not pal["heroNote"] and pal["quotes"] == 0 and pal["rows"] > 0,
          json.dumps(pal, ensure_ascii=False))
    page.goto(base + "/classes.html?c=not_a_class", wait_until="networkidle")
    page.wait_for_timeout(1300)
    check("地址里职业认不出来就落回第一个职业，不白屏",
          page.evaluate("() => (document.querySelector('#main h1') || {}).innerText || ''")
          .startswith(byid[cl[0]["id"]]["cn"]) and not page.evaluate("() => !!document.querySelector('.fail')"),
          page.evaluate("() => (document.querySelector('#main h1') || {}).innerText"))
    check("导航里「职业」这一格指向新页，当前页高亮且组名跟着亮",
          bool(st["on"]) and st["on"]["t"] == "职业" and st["on"]["href"] == "classes.html"
          and st["on"]["group"] == "职业", json.dumps(st["on"], ensure_ascii=False))
    nav_new = sc.get("navNew") or []
    if "职业" in nav_new:
        check("「本站更新」最新一批打了「职业」标签，导航那一格就长出「新」角标",
              bool(st["on"]["badge"]), json.dumps(st["on"], ensure_ascii=False))
    else:
        check("角标跟着「本站更新」的标签走：这一版没打「职业」标签就不该画",
              not st["on"]["badge"], json.dumps(st["on"], ensure_ascii=False))
    page.screenshot(path=os.path.join(SHOT_DIR, "classes-desktop.png"), full_page=True)
    ctx.close()

    m = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    mp = m.new_page()
    mp.goto(base + "/classes.html?c=warrior", wait_until="networkidle")
    mp.wait_for_timeout(1400)
    mob = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
      const els = [...document.querySelectorAll('button, a, input, .cls, .spec')];
      const small = els.filter(e => { const b = e.getBoundingClientRect();
        return b.width > 0 && b.height > 0 && Math.min(b.width, b.height) < 44; })
        .map(e => e.tagName + '.' + String(e.className).split(' ')[0]);
      const sp = [...document.querySelectorAll('.spec')];
      return { overflow: document.documentElement.scrollWidth > vw + 1, small,
        stacked: new Set(sp.map(e => Math.round(e.getBoundingClientRect().top))).size === sp.length,
        chart: Math.round(document.querySelector('.chart').getBoundingClientRect().width),
        h1: document.querySelectorAll('h1').length }; }""")
    check("移动端职业页不横向溢出、三系卡上下排、点击目标够大",
          not mob["overflow"] and mob["stacked"] and not mob["small"] and mob["h1"] == 1,
          json.dumps(mob, ensure_ascii=False)[:170])
    mp.screenshot(path=os.path.join(SHOT_DIR, "classes-mobile.png"), full_page=True)
    m.close()


def test_player_facing(browser, base):
    """内容页只留标题和数据（2026-10-12 用户决定，面对游戏玩家）。

    这一节是**反向断言**：不是检查说明文字在不在，而是检查它们不许再出现在内容页上——
    分级徽标、逐条来源按钮、来源块、来源轨、素材出处角标、覆盖率条、"数据基线…"那行。
    出处与分级集中在溯源页（provenance.html）说，那一页反过来必须带着它们。
    谁把这些画回内容页，这里就红，不用靠人记着 AGENTS.md 第 3a 条。
    注意「待实测」不在这张黑名单里：那是数据值（缺数据显示"待实测"是仓库根红线），
    撤掉的只是它作为 L0-L3 徽标的那层皮，不是这三个字。
    文字这一半对 updates.html 放行：那一页的第二栏本来就是"本站自己改了什么"的流水账，
    条目里出现"本站"是内容本身，不是备注；元素类检查（徽标/来源/角标）仍然照它跑。"""
    import json
    print("\n[22] 内容页只留标题与数据")
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    probes = {
        "pill": "document.querySelectorAll('#main .pill').length",
        "srcBtn": "document.querySelectorAll('#main [data-src]').length",
        "srcList": "document.querySelectorAll('#main .src li').length",
        "rail": "document.querySelectorAll('#main .rail').length",
        "mark": "document.querySelectorAll('#main .dmark, #main .artmark, #main .dbn2-mark').length",
        "cov": "document.querySelectorAll('#main .covnum, #main .stats4').length",
    }
    WORDS = (u"来源与核对", u"本地转存", u"示意图 ·", u"已官方核实", u"仅官方英文",
             u"数据基线", u"逐条带来源", u"不机翻", u"本站不复制")
    bad = {}
    for name in PAGES:
        if name == "provenance":
            continue
        page.goto("%s/%s.html" % (base, name), wait_until="networkidle")
        page.wait_for_timeout(1300)
        got = {k: page.evaluate("(function(){return %s})()" % v) for k, v in probes.items()}
        txt = page.evaluate("() => document.querySelector('#main').innerText")
        leftover = [w for w in WORDS if (w in txt and name != "updates")]
        left = {k: v for k, v in got.items() if v}
        if left or leftover:
            bad[name] = {"元素": left, "文字": leftover}
    check("%d 个内容页都不挂分级徽标 / 来源按钮 / 来源块 / 来源轨 / 素材角标 / 覆盖率读数" % (len(PAGES) - 1),
          not bad, json.dumps(bad, ensure_ascii=False)[:300])

    # 溯源页是唯一的例外，反过来必须带着这些东西，否则"集中说"就变成"没人说"
    page.goto(base + "/provenance.html", wait_until="networkidle")
    page.wait_for_timeout(1400)
    pv = page.evaluate("""() => ({ bar: document.querySelectorAll('#main .cov i').length,
      pill: document.querySelectorAll('#main .pill').length,
      stats: [...document.querySelectorAll('#main .stats .stat')].map(e => e.innerText.replace(/\\s+/g, ' ')),
      src: document.querySelectorAll('#main .src, #main .src li').length,
      txt: document.querySelector('#main').innerText })""")
    # 覆盖率条只有某一档计数为 0 时那一段不画（旧站一直是这个口径），所以按"至少三段"而不是死等于四段
    check("出处与分级集中在溯源页说：那一页仍有覆盖率条、四档读数与分级徽标",
          pv["bar"] >= 3 and len(pv["stats"]) >= 4 and pv["pill"] >= 4,
          json.dumps({"条宽段": pv["bar"], "徽标": pv["pill"], "读数": len(pv["stats"])}, ensure_ascii=False))
    bar = page.evaluate("""() => { const i = [...document.querySelectorAll('#main .cov i')];
      return { n: i.length, sum: i.reduce((a, x) => a + x.getBoundingClientRect().width, 0),
               box: document.querySelector('#main .cov').getBoundingClientRect().width }; }""")
    check("溯源页覆盖率条四段宽度加起来等于条宽", abs(bar["sum"] - bar["box"]) < 3,
          "%d 段共 %.0fpx / 条 %.0fpx" % (bar["n"], bar["sum"], bar["box"]))
    check("溯源页写明内容页为什么不挂标记",
          u"内容页" in pv["txt"] and (u"这一页" in pv["txt"] or u"集中" in pv["txt"]),
          pv["txt"][:80].replace("\n", " "))
    ctx.close()


def test_design_system(browser, base):
    """改版判据（docs/DESIGN-REFRESH-2026-10-10.md 第八节）：颜色对比度、来源轨、
       琥珀金不再兼任"待实测"、动效可关、焦点可见。判据全部取计算值，不看源码。"""
    print("\n[20] 设计系统：对比度 / 来源轨 / 动效可关 / 焦点可见")
    import json

    # 页内取色：文字色沿祖先找到第一个不透明背景，再算 WCAG 对比度
    PROBE = """() => {
      const lum = (c) => { const v = c.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
      const rgb = (s) => (s.match(/\\d+(\\.\\d+)?/g) || []).slice(0, 4).map(Number);
      const ratio = (fg, bg) => { const a = lum(fg.slice(0, 3)), b = lum(bg.slice(0, 3));
        return +(((Math.max(a, b) + .05) / (Math.min(a, b) + .05)).toFixed(2)); };
      const bgOf = (e) => { let n = e;
        while (n && n !== document.documentElement) { const c = rgb(getComputedStyle(n).backgroundColor);
          if (c.length < 4 || c[3] > .92) return c; n = n.parentElement; }
        return [255, 255, 255]; };
      const px = (e) => parseFloat(getComputedStyle(e).fontSize) || 0;
      const samples = [];
      const push = (label, e) => { if (!e) return;
        const f = getComputedStyle(e); const fg = rgb(f.color);
        samples.push({ label, size: px(e), weight: +f.fontWeight, fg, bg: bgOf(e),
          cr: ratio(fg, bgOf(e)) }); };
      push('h1', document.querySelector('#main h1'));
      push('正文', document.querySelector('#main p'));
      push('note', document.querySelector('#main .note'));
      push('dim', document.querySelector('#main .dim'));
      push('徽标', document.querySelector('#main .pill'));
      push('conf', document.querySelector('#main .conf'));
      push('链接', document.querySelector('#main a'));
      const mono = [...document.querySelectorAll('#main .mono, #main .mline')][0];
      push('等宽元数据', mono);
      const bad = samples.filter(s => { const large = s.size >= 24 || (s.size >= 18.66 && s.weight >= 700);
        return s.cr < (large ? 3 : 4.5); });
      const lv = {};
      document.querySelectorAll('#main .pill').forEach(p => {
        const m = /\\bL([0-3])\\b/.exec(p.className); if (!m) return;
        const c = getComputedStyle(p).color; lv['L' + m[1]] = lv['L' + m[1]] === undefined ? c : (lv['L' + m[1]] === c ? c : 'MIX');
      });
      const marks = [...document.querySelectorAll('#main .pill')].map(p => {
        const b = getComputedStyle(p, '::before');
        return { bg: b.backgroundImage === 'none' ? b.backgroundColor : b.backgroundImage,
                 r: b.borderRadius, w: b.width };
      });
      return { samples, bad, lv,
        rails: document.querySelectorAll('#main .rail[data-lv]').length,
        // 「本站说明 / 本站承诺」不是数据来源，不算声明了分级——这种卡不该有轨
        claims: document.querySelectorAll('#main .pill, #main .src .st:not(.site-note):not(.site-promise)').length,
        railLv: [...new Set([...document.querySelectorAll('#main .rail')].map(c => c.dataset.lv))].sort(),
        railShapes: [...new Set([...document.querySelectorAll('#main .rail')].map(c => {
          const b = getComputedStyle(c, '::before'); return (b.backgroundImage || '') + '|' + b.borderStyle + '|' + b.backgroundColor; }))].length,
        goldOnPill: lv.L2 === getComputedStyle(document.documentElement).getPropertyValue('--gold').trim()
          || Object.entries(lv).filter(([, v]) => v === 'rgb(224, 169, 109)').length,
        brandHex: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() };
    }"""

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    weak = {}
    for name in PAGES:
        page.goto("%s/%s.html" % (base, name), wait_until="networkidle")
        page.wait_for_timeout(1300)
        r = page.evaluate(PROBE)
        check("%s 页文字对比度达 AA" % name, not r["bad"],
              json.dumps([{"位": b["label"], "比": b["cr"], "字": b["size"]} for b in r["bad"][:3]], ensure_ascii=False))
        weak[name] = r["bad"]

    # 2026-10-12 站主决定：分级徽标与来源轨退出内容页，全部集中到溯源页。
    # 所以这三条不再遍历 17 页，而是只在溯源页验——签名元素还在，只是只出现在该出现的那一页。
    page.goto(base + "/provenance.html", wait_until="networkidle")
    page.wait_for_timeout(1400)
    r = page.evaluate(PROBE)
    check("溯源页声明了分级的卡片都上来源轨", r["claims"] >= 1 and r["rails"] >= 1,
          json.dumps({"声明": r["claims"], "上轨": r["rails"]}, ensure_ascii=False))
    check("来源轨只在溯源页出现（内容页一处都不许有，见第 22 节）",
          r["rails"] >= 1 and r["claims"] >= r["rails"],
          json.dumps({"声明": r["claims"], "上轨": r["rails"], "级别": r["railLv"]}, ensure_ascii=False))

    # 琥珀金从此只表示交互与品牌：任何分级徽标都不许用它
    # 品牌色不兼任分级色。2026-10-11 品牌色从琥珀金换成无限蓝，所以这里读实时值比对，
    # 不再写死某个 rgb——否则下次换色这条断言会静默失效。
    bh = (r.get("brandHex") or "#49aee9").lstrip("#")
    brand = "rgb(%d, %d, %d)" % (int(bh[0:2], 16), int(bh[2:4], 16), int(bh[4:6], 16))
    gold = [k for k, v in r["lv"].items() if v in (brand, "rgb(224, 169, 109)")]
    check("分级徽标不借用品牌色（曾与琥珀金同色，现在是无限蓝）", r["lv"] and not gold,
          json.dumps({"品牌色": brand, "徽标": r["lv"]}, ensure_ascii=False))
    shapes = page.evaluate("""() => {
      const out = {};
      ['L0','L1','L2','L3'].forEach(k => {
        const p = document.querySelector('.pill.' + k); if (!p) return;
        const b = getComputedStyle(p, '::before');
        out[k] = [b.backgroundImage.slice(0, 40), b.backgroundColor, b.borderRadius, b.borderTopWidth].join('|');
      });
      return out; }""")
    check("四种分级的徽标形状各不相同", len(set(shapes.values())) == len(shapes) and len(shapes) >= 3,
          json.dumps(shapes, ensure_ascii=False))

    # 动效可关：模拟系统"减少动态效果"，卡片与轨道的动画必须归零
    # 轨道现在只在溯源页有，所以这一组也在那一页取——换页别把这条断言变成"永远走 no-rail 分支"。
    rm = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
    rp = rm.new_page()
    rp.goto(base + "/provenance.html", wait_until="networkidle")
    rp.wait_for_timeout(1200)
    m = rp.evaluate("""() => { const c = document.querySelector('#main .card');
      const r = document.querySelector('#main .rail'); const cs = getComputedStyle(c);
      const b = document.querySelector('button') || document.querySelector('a');
      return { card: cs.animationName + '/' + cs.animationDuration,
        rail: r ? getComputedStyle(r, '::before').animationDuration : 'no-rail',
        btn: b ? getComputedStyle(b).transitionDuration : 'none' }; }""")
    def secs(v):
        v = (v or '').strip()
        try:
            return float(v[:-1]) / (1000 if v.endswith('ms') else 1)
        except ValueError:
            return 9.99
    check("减少动效时卡片动画关闭（保留最终态不隐藏内容）",
          secs(m["card"].split('/')[1]) < 0.005 and secs(m["rail"]) < 0.005,
          json.dumps(m, ensure_ascii=False))
    check("减少动效时卡片仍完整可见", rp.evaluate("() => { const c = document.querySelector('#main .card');"
          "return +getComputedStyle(c).opacity > .99; }"), "opacity 应回到 1")
    rm.close()

    # 键盘焦点：Tab 到第一个链接必须有可见焦点环
    fk = browser.new_context(viewport={"width": 1440, "height": 1000})
    fp = fk.new_page()
    fp.goto(base + "/index.html", wait_until="networkidle")
    fp.wait_for_timeout(1200)
    fp.keyboard.press("Tab")
    ring = fp.evaluate("""() => { const e = document.activeElement; const s = getComputedStyle(e);
      return { tag: e.tagName, cls: (e.className || '').slice(0, 20),
        w: parseFloat(s.outlineWidth) || 0, style: s.outlineStyle }; }""")
    check("键盘 Tab 有可见焦点环（≥2px 实线）", ring["w"] >= 2 and ring["style"] != "none",
          json.dumps(ring, ensure_ascii=False))
    fk.close()

    # 组件规则里的裸色值只许减少不许增加。2026-10-11 把令牌搬进 css/tokens.css 后，
    # 组件层从 18 处降到 1 处（那处还是注释里的说明文字），基线跟着收到 6。
    css = open(os.path.join(SRC, "css", "app.css"), encoding="utf-8").read()
    body = css.split("}", 1)[1]
    raw = len(re.findall(r"#[0-9a-fA-F]{6}\b", body))
    check("组件规则里的裸色值不增（2026-10-11 基线 6 处，只降不升）", raw <= 6, "现 %d 处" % raw)

    # 令牌只有一个家：组件文件里再出现 :root 就是有人又抄了一份色值
    tk = os.path.join(SRC, "css", "tokens.css")
    # 组件文件里可以有响应式的尺度覆盖（媒体查询里改 --fs-*），但不许再定义颜色令牌
    stray = [m.group(1) for m in re.finditer(r":root\s*\{([^}]*)\}", css)
             if re.search(r"#[0-9a-fA-F]{3,6}\b|rgba?\(", m.group(1))]
    check("设计令牌只有 tokens.css 一处定义颜色（app.css 里只许媒体查询改尺度）",
          os.path.exists(tk) and not stray,
          "app.css 里又定义了色值：%s" % (stray[0][:70] if stray else "无"))

    # 字体：自托管可以，字体 CDN 一个字都不许出现（红线 2026-10-11 放开的是前者，不是后者）
    blob = css + open(os.path.join(SRC, "css", "tokens.css"), encoding="utf-8").read() \
        + open(os.path.join(SRC, "css", "fonts.css"), encoding="utf-8").read()
    cdn = [w for w in ("fonts.googleapis", "fonts.gstatic", "@import url(\"http", "@import url('http") if w in blob]
    fonts_local = all(os.path.exists(os.path.join(SRC, "fonts", f))
                      for f in ("open-sans-var.woff2", "hanken-grotesk-var.woff2", "FONTS-LICENSE.txt"))
    check("字体是自托管的本地文件，没有任何字体 CDN", not cdn and fonts_local,
          "命中 %s / 本地文件 %s" % (cdn or "无", "齐" if fonts_local else "缺"))

    # HTML 里的 theme-color 是手机地址栏的底色，值必须跟着令牌的 --bg。
    # 2026-10-11 换色时它被留在旧值 #0e1013 上——"把令牌值抄一份到别处"这类漂移
    # 肉眼看不出来（只在真机上表现为浏览器边框一条色差），所以在这里钉住。
    mbg = re.search(r"--bg\s*:\s*(#[0-9a-fA-F]{6})", open(tk, encoding="utf-8").read())
    bg = mbg.group(1).lower() if mbg else ""
    tc_files = [os.path.join(SRC, f) for f in sorted(os.listdir(SRC)) if f.endswith(".html")]
    tc_files.append(os.path.join(ROOT, "app", "index.html"))
    stale = ["%s:%s" % (os.path.relpath(f, ROOT), tc) for f in tc_files
             for tc in re.findall(r'name="theme-color"\s+content="([^"]+)"',
                                  open(f, encoding="utf-8").read()) if tc.lower() != bg]
    check("每个页面的 theme-color 等于令牌 --bg（%s）" % bg, bg and not stale,
          "不一致：%s" % " ".join(stale[:4]) if stale else "%d 个文件一致" % len(tc_files))

    # 首页图标轨：九格、图都真加载出来、每格都指向真存在的页面
    page.goto(base + "/index.html", wait_until="networkidle")
    page.wait_for_timeout(1600)
    rail = page.evaluate("""() => { const a = [...document.querySelectorAll('.hrail .hrt')];
      return { n: a.length, hrefs: a.map(x => (x.getAttribute('href') || '').split('?')[0]),
        imgs: a.filter(x => x.querySelector('img')).length,
        broken: a.reduce((n, x) => n + [...x.querySelectorAll('img')]
          .filter(i => i.complete && i.naturalWidth === 0).length, 0),
        alt: a.reduce((n, x) => n + [...x.querySelectorAll('img')]
          .filter(i => i.getAttribute('alt') === null).length, 0) }; }""")
    check("首页图标轨九格、图全部本地加载、alt 齐全",
          rail["n"] == 9 and rail["imgs"] == 9 and rail["broken"] == 0 and rail["alt"] == 0,
          json.dumps(rail, ensure_ascii=False)[:160])
    check("图标轨每格都指向真存在的页",
          all(h.replace(".html", "") in PAGES for h in rail["hrefs"]), str(rail["hrefs"][:4]))

    # 顶栏那颗搜索框不是装饰：在别的页输入回车，要落到首页搜索并出结果
    page.goto(base + "/dungeons.html", wait_until="networkidle")
    page.wait_for_timeout(1300)
    page.fill("#gstop", "领主大厅")
    page.press("#gstop", "Enter")
    page.wait_for_timeout(1600)
    ok = page.evaluate("""() => ({ url: location.pathname + location.search,
      box: (document.querySelector('#gs') || {}).value || '',
      rows: document.querySelectorAll('#gres .gsr').length })""")
    check("顶栏搜索跳到首页并直接出结果",
          "index.html" in ok["url"] and ok["box"] == "领主大厅" and ok["rows"] >= 1,
          json.dumps(ok, ensure_ascii=False))

    # ---- 改版第三批（2026-10-11 用户反馈：导航平铺看不清 / 卡片边框不对 / 跳锚点被头部遮挡）----
    # ① 导航必须真是上下两级：组名那一行在二级项之上，且六个组名颜色互不相同。
    #    只断言"组名存在"没用——上一版就是这样，组名和项挤在同一行、只差 1.5px 字号。
    page.goto(base + "/index.html", wait_until="networkidle")
    page.wait_for_timeout(1300)
    nv = page.evaluate("""() => {
      const labs = [...document.querySelectorAll('nav.main .ngt')];
      const items = [...document.querySelectorAll('nav.main a.nl')];
      const top = (e) => Math.round(e.getBoundingClientRect().top);
      const cs = (e) => getComputedStyle(e);
      const b = document.querySelector('.nb');
      const box = b ? b.getBoundingClientRect() : null;
      const ab = b ? b.closest('a.nl').getBoundingClientRect() : null;
      return { labTop: Math.max(...labs.map(top)), itemTop: Math.min(...items.map(top)),
               labels: labs.length, n: items.length,
               itemRows: [...new Set(items.map(top))].length,
               hues: [...new Set(labs.map(l => cs(l).color))],
               itemHue: cs(items.find(a => !a.classList.contains('on'))).color,
               badgeIn: b ? (box.top >= ab.top - 1 && box.right <= ab.right + 1
                             && box.bottom <= ab.bottom + 1) : true };
    }""")
    check("导航是上下两级：组名行在二级项行之上", nv["labTop"] < nv["itemTop"],
          "组名底 %s / 项顶 %s / 组 %d 个 / 项 %d 个" % (nv["labTop"], nv["itemTop"], nv["labels"], nv["n"]))
    check("六个分组标签颜色互不相同，且不跟正文项同色",
          len(nv["hues"]) == nv["labels"] and nv["itemHue"] not in nv["hues"],
          "色相 %d 种 / 项色 %s" % (len(nv["hues"]), nv["itemHue"]))
    check("「新」角标收在项框内：不飘出导航带，也不把入口挤成两行",
          nv["badgeIn"] and nv["itemRows"] == 1,
          "角标越界=%s 入口行数=%d" % (not nv["badgeIn"], nv["itemRows"]))

    # ② 卡片描边要真看得见：算一次卡面与描边的边界对比，白 10% 时只有 1.06:1（等于没边）
    edge = page.evaluate("""() => {
      const lum = (c) => { const v = c.map(x => { x /= 255; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); });
        return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
      const rgba = (s) => { const a = (s.match(/[\\d.]+/g) || []).map(Number);
        return { c: a.slice(0, 3), al: a.length > 3 ? a[3] : 1 }; };
      const r = (a, b) => (Math.max(lum(a), lum(b)) + .05) / (Math.min(lum(a), lum(b)) + .05);
      const cs = getComputedStyle(document.querySelector('#main .card'));
      const pageBg = rgba(getComputedStyle(document.body).backgroundColor).c;
      const cardBg = rgba(cs.backgroundColor).c;
      const bd = rgba(cs.borderTopColor);
      // 描边是半透明白，落在卡面上才看得见：先按 alpha 合成到卡面，再与页面底比边界对比
      const mix = bd.c.map((v, i) => Math.round(v * bd.al + cardBg[i] * (1 - bd.al)));
      return { w: cs.borderTopWidth, style: cs.borderTopStyle, al: bd.al,
               edgeVsPage: +r(mix, pageBg).toFixed(2), cardVsPage: +r(cardBg, pageBg).toFixed(2) };
    }""")
    check("卡片描边看得见（边界对页面底 ≥1.15:1，原来白 10% 只有 1.06）",
          edge["w"] != "0px" and edge["style"] != "none" and edge["edgeVsPage"] >= 1.15,
          json.dumps(edge, ensure_ascii=False))

    # ③ 锚点与吸顶表头都要让开吸顶头部：逐页跳页内锚点，目标顶部不许落在头部下沿之内
    hd_bad, th_bad, head_ok = [], [], 0
    for name in PAGES:
        page.goto("%s/%s.html" % (base, name), wait_until="networkidle")
        page.wait_for_timeout(1100)
        r = page.evaluate("""() => {
          const hd = Math.round(document.querySelector('.top').getBoundingClientRect().height);
          const hdVar = Math.round(parseFloat(getComputedStyle(document.documentElement)
            .getPropertyValue('--hd-h')) || 0);
          const seen = new Set(); const bad = [];
          document.querySelectorAll('a[href^="#"]').forEach(a => {
            const id = a.getAttribute('href').slice(1);
            if (!id || seen.has(id)) return;
            seen.add(id);
            const t = document.getElementById(id);
            if (!t) { bad.push('#' + id + ' 不存在'); return; }
            t.scrollIntoView();
            const top = Math.round(t.getBoundingClientRect().top);
            if (top < hd - 2) bad.push('#' + id + ' 顶 ' + top + ' < 头部 ' + hd);
          });
          const ths = [];
          document.querySelectorAll('#main table').forEach(tb => {
            const th = tb.querySelector('thead th'); if (!th) return;
            const cs = getComputedStyle(th);
            const inX = !!tb.closest('.scrollx');
            if (cs.position === 'sticky' && !inX) {
              const rows = tb.querySelectorAll('tbody tr');
              if (rows.length > 3) {
                rows[Math.floor(rows.length / 2)].scrollIntoView({ block: 'start' });
                if (Math.round(th.getBoundingClientRect().top) < hd - 2)
                  ths.push(tb.className + ' 表头顶 ' + Math.round(th.getBoundingClientRect().top));
              }
            }
            if (cs.position === 'sticky' && inX && !th.classList.contains('rh'))
              ths.push('假吸顶：' + tb.className + ' 在 .scrollx 里还写 sticky');
          });
          const cd = document.querySelector('#main .cdhead');
          const img = cd && cd.querySelector('img');
          // 页首标题件有两种：卡片头，或设计稿那套页首 banner（团本页 2026-10-12 起用后者）
          const head = !!cd || !!document.querySelector('#main .dhero .pt');
          return { hd, hdVar, bad, ths, head,
                   noart: cd ? cd.className.indexOf('noart') >= 0 : false,
                   broken: img ? (img.complete && img.naturalWidth === 0) : false,
                   h1: document.querySelectorAll('#main h1').length };
        }""")
        if r["bad"]:
            hd_bad.append("%s：%s" % (name, r["bad"][0]))
        if r["ths"]:
            th_bad.append("%s：%s" % (name, r["ths"][0]))
        if abs(r["hdVar"] - r["hd"]) > 2:
            th_bad.append("%s：--hd-h %s 与真实头部高 %s 不一致" % (name, r["hdVar"], r["hd"]))
        if r["head"] and not r["broken"] and r["h1"] == 1:
            head_ok += 1
    check("%d 页页内锚点跳过去都不被吸顶头部压住" % len(PAGES), not hd_bad, "; ".join(hd_bad[:3]))
    check("吸顶表头让开头部，且横向滚的容器里不留假吸顶", not th_bad, "; ".join(th_bad[:3]))
    # 主卡卡片头：除首页与天赋页外，每个内容页都要有卡片头或页首 banner（这两页第一批已单独排过）
    # 页数会随新页变化，判据按 len(PAGES) 算，不写死常数——写死的常数在新页上线那天就会悄悄少一页。
    need_head = len(PAGES) - 2
    check("%d 个内容页的主卡都换上卡片头或页首 banner（首页/天赋页除外）" % need_head,
          head_ok >= need_head, "合格 %d / %d 页" % (head_ok, len(PAGES)))

    # ④ 动态模块：读数带不能像按钮，"下一件"只能有一条，首页摘要必须收口
    page.goto(base + "/updates.html", wait_until="networkidle")
    page.wait_for_timeout(1400)
    up = page.evaluate("""() => {
      const st = document.querySelector('.stats.readout .stat');
      const pk = document.querySelector('.picks.utabs .pick');
      return { stats: document.querySelectorAll('.stats.readout .stat').length,
               statBordered: st ? getComputedStyle(st).borderTopWidth : 'none',
               readoutBoxed: !!document.querySelector('.stats.readout'),
               tabs: document.querySelectorAll('.picks.utabs .pick').length,
               near: document.querySelectorAll('#main .flowrow.near').length,
               past: document.querySelectorAll('#main .flowrow.past').length,
               when: document.querySelectorAll('#main .when').length };
    }""")
    check("动态页顶部是读数带不是按钮墙", up["stats"] >= 5 and up["readoutBoxed"],
          json.dumps(up, ensure_ascii=False)[:120])
    check("时间轴只提亮最近那一件，已过去的降一档", up["near"] == 1 and up["past"] >= 3,
          "下一件 %d / 已过 %d / 带天数 %d" % (up["near"], up["past"], up["when"]))
    page.goto(base + "/index.html", wait_until="networkidle")
    page.wait_for_timeout(1400)
    hn = page.evaluate("""() => ({
      sec: document.querySelectorAll('#main .nsec h3').length,
      acts: document.querySelectorAll('#main .nsec .nact a').length,
      clamp: document.querySelectorAll('#main .clamp2').length,
      rows: document.querySelectorAll('#main .nsec .flowrow').length,
      emptyH3: [...document.querySelectorAll('#main .nsec h3')].filter(h => !h.innerText.trim()).length })""")
    check("首页「最新动态」收成两节摘要，每节都带回动态页的出口",
          hn["sec"] == 2 and hn["acts"] == 2 and hn["rows"] <= 6 and hn["emptyH3"] == 0,
          json.dumps(hn, ensure_ascii=False))
    check("首页摘要长句在两行处收住（全文去动态页读）", hn["clamp"] >= 4, "%d 处收行" % hn["clamp"])
    ctx.close()


def test_copy(browser, base):
    """面向维护者的词不许出现在玩家看的正文里。词表与 build-data.js 用的是同一份
       tools/copy-banned.json：数据侧扫 JSON，这里扫渲染后的文字（app.js 里的句子只有渲染才看得见）。"""
    print("\n[18] 正文禁词")
    import json
    ban = json.load(open(os.path.join(ROOT, "tools", "copy-banned.json"), encoding="utf-8"))
    pats = [(p["re"], p["why"]) for p in ban["patterns"]]
    strips = ban.get("strip", [])

    def scan(label, text):
        t = text
        for s in strips:
            t = t.replace(s, "")
        bad = []
        for pat, why in pats:
            m = re.search(pat, t)
            if m:
                at = m.start()
                bad.append("%s：%s" % (pat, t[max(0, at - 22):at + 34].replace("\n", " ")))
        check("正文无维护者措辞 %s" % label, not bad, " ｜ ".join(bad[:2]))

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    for name in PAGES:
        page = ctx.new_page()
        page.goto("%s/%s.html" % (base, name), wait_until="networkidle")
        page.wait_for_timeout(1300)
        text = page.evaluate("""() => [document.querySelector('.top'), document.querySelector('#main'),
            document.querySelector('.foot')].filter(Boolean).map(e => e.innerText).join('\\n')""")
        scan(name, text)
        page.close()
    ctx.close()

    # 来源抽屉点开后的文字也在扫描范围内：那一段默认收起，但它是玩家真会点开的地方
    ctx2 = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx2.new_page()
    page.goto("%s/dungeons.html" % base, wait_until="networkidle")
    page.wait_for_timeout(1200)
    page.evaluate("() => document.querySelectorAll('[data-d]').forEach(b => b.click())")
    page.wait_for_timeout(600)
    scan("副本页来源展开后", page.evaluate("() => document.querySelector('#main').innerText"))
    page.goto("%s/talent.html" % base, wait_until="networkidle")
    page.wait_for_timeout(1500)
    page.evaluate("() => { const b = document.getElementById('tsrcbtn'); if (b) b.click(); }")
    page.wait_for_timeout(500)
    scan("天赋页来源展开后", page.evaluate("() => document.querySelector('#main').innerText"))
    ctx2.close()

    # 新站（Vue）那两页也扫一遍：两栈共用一份数据，但页面里的句子是各写各的
    ctx3 = browser.new_context(viewport={"width": 1440, "height": 1000})
    ap = ctx3.new_page()
    for route, label in [("#/", "新站首页"), ("#/world", "新站世界页")]:
        try:
            ap.goto("%s/%s" % (APP_BASE, route), wait_until="networkidle")
        except Exception:
            check("%s正文可访问" % label, False, "新站没起来：%s" % APP_BASE)
            continue
        ap.wait_for_timeout(1600)
        scan(label, ap.evaluate("""() => [document.querySelector('.top'), document.querySelector('#main')]
            .filter(Boolean).map(e => e.innerText).join('\\n')"""))
    ap.close()
    ctx3.close()


# 全跑一次 13 分钟，改一条新断言时等不起。SECTIONS 把顺序固定下来，--only 按名字挑着跑，
# 用来做 30 秒探针；正式门禁仍然不带 --only。
SECTIONS = [
    ("pages", test_pages),
    ("talent", test_talent),
    ("dungeon_banner", test_dungeon_banner),
    ("chooser", test_chooser),
    ("abilities", test_abilities),
    ("spellbook", test_spellbook),
    ("bis", test_bis),
    ("race_icon", lambda b, base: test_race_icon(b)),
    ("updates_filter", lambda b, base: test_updates_filter(b)),
    ("css_tokens", test_css_tokens),
    ("world_pins", test_world_pins),
    ("dungeon_geo", test_dungeon_geo),
    ("legacy_app", test_legacy_app),
    ("races", test_races),
    ("grouping", test_grouping),
    ("dungeon_data", test_dungeon_data),
    ("dungeon_detail", test_dungeon_detail),
    ("raids", test_raids),
    ("professions", test_professions),
    ("world", test_world),
    ("home", test_home),
    ("updates_rank", test_updates_rank),
    ("search", test_search),
    ("legacy", test_legacy),
    ("classes", test_classes),
    ("player_facing", test_player_facing),
    ("design_system", test_design_system),
    ("copy", test_copy),
    ("app", test_app),
    ("design_baseline", test_design_baseline),
    ("mobile", test_mobile),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", action="store_true",
                        help="强制跑新站（Vue）那组断言，端口不通就直接失败")
    parser.add_argument("--app-base", default=os.environ.get("APP_BASE", "http://127.0.0.1:8821"))
    parser.add_argument("--only", default="",
                        help="只跑逗号指定的小节（如 player_facing,home），用于改断言时的快速探针")
    args = parser.parse_args()
    global APP_BASE, APP_REQUIRED
    APP_BASE, APP_REQUIRED = args.app_base, args.app
    todo = SECTIONS
    if args.only:
        want = [x.strip() for x in args.only.split(",") if x.strip()]
        unknown = [w for w in want if w not in dict(SECTIONS)]
        if unknown:
            parser.error("没有这组断言：%s（可选 %s）" % ("、".join(unknown), ",".join(k for k, _ in SECTIONS)))
        todo = [s for s in SECTIONS if s[0] in want]
    if not os.path.isdir(SHOT_DIR):
        os.makedirs(SHOT_DIR)
    httpd, base = start_server()
    print("本地服务：%s（根目录 %s）" % (base, SRC))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            for name, fn in todo:
                fn(browser, base)
            browser.close()
    finally:
        httpd.shutdown()

    failed = [n for n, ok, _ in results if not ok]
    print("\n===== 结果 =====")
    print("截图目录：%s" % SHOT_DIR)
    print("通过 %d / %d" % (len(results) - len(failed), len(results)))
    if failed:
        print("失败项：\n  - " + "\n  - ".join(failed))
        sys.exit(1)
    print("全部通过")


if __name__ == "__main__":
    main()
