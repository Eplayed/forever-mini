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

PAGES = ["index", "talent", "chooser", "timeline", "skills", "dungeons", "raids", "systems", "races",
         "professions", "world", "legacy", "updates", "rank", "glossary", "provenance"]
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
    marks = page.evaluate("() => [...document.querySelectorAll('.dbn2-mark')].map(m => m.textContent.trim())")
    honest = [m for m in marks if ("非游戏原画" in m) or ("客户端原画" in m)]
    check("每张横幅都标明图是示意图还是客户端原画", len(honest) == len(marks) and marks,
          "%d/%d 带标注" % (len(honest), len(marks)))
    check("有客户端原画的副本用上了本地图",
          any("客户端原画" in m for m in marks), "标注种类 %s" % sorted(set(marks)))
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
    check("无官方稿的职业显示空态而不是空表",
          "还没有官方中文深度解析稿" in page.evaluate("() => document.querySelector('#abtbl').innerText"))
    page.screenshot(path=os.path.join(SHOT_DIR, "skills-abilities.png"))
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
    trs = page.evaluate("() => document.querySelectorAll('#tt tbody tr').length")
    check("矩阵行数与数据一致", rows == n_races, "DOM %d / 数据 %d" % (rows, n_races))
    check("矩阵覆盖 9 个职业列", cols == 9, "列 %d" % cols)
    check("✓ 与 — 铺满整表不留空", marks + dashes == rows * 9,
          "✓ %d + — %d，应 %d" % (marks, dashes, rows * 9))
    check("✓ 数等于数据里的可选职业总数", marks == n_marks, "DOM %d / 数据 %d" % (marks, n_marks))
    check("默认不把 40 条特长再铺一遍（按种族浏览交给上方详情面板）",
          trs == 0 and page.evaluate("() => !!document.querySelector('#traits button[data-act=\"all\"]')"),
          "默认 %d 行 + 一个「看全 %d 条」按钮" % (trs, n_traits))

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

    page.click('#traits button[data-act="all"]')
    page.wait_for_timeout(250)
    allrows = page.evaluate("() => document.querySelectorAll('#tt tbody tr').length")
    check("跨种族特长全表可展开且条数与数据一致", allrows == n_traits, "%d 条（数据 %d）" % (allrows, n_traits))
    page.fill("#fq", "昏迷")
    page.wait_for_timeout(250)
    found = page.evaluate("() => document.querySelectorAll('#tt tbody tr').length")
    check("特长搜索按整句生效", 0 < found <= n_traits and found < allrows,
          "「昏迷」命中 %d / 全表 %d" % (found, allrows))
    page.fill("#fq", "")
    page.wait_for_timeout(200)

    page.click("#tt tbody tr:first-child button.info")
    page.wait_for_timeout(300)
    box = page.evaluate("() => { const b = document.getElementById('srcbox');"
                        "return b && b.style.display !== 'none' ? b.innerText : ''; }")
    check("特长逐条来源可展开并指向官方中文页",
          ("官方中文" in box or "official_cn" in box) and "wow.blizzard.cn" in box,
          box[:56].replace("\n", " "))
    text = page.evaluate("() => document.querySelector('#main').innerText")
    check("矩阵与导语两种说法并存且写了处置",
          "同一页里两种说法并存" in text and "本站处置" in text)
    check("种族页写明没采集什么", "这一页没有的" in text and "英文原名" in text)
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
    check("原画右上角标明素材出处", all("本地转存" in x["mark"] for x in fac),
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
    page.click("#rdet button.info")
    page.wait_for_timeout(300)
    dr = page.evaluate("() => { const b = document.getElementById('srcbox');"
                       "return b && b.innerText.trim() ? b.innerText.length : 0; }")
    check("种族详情的来源能展开", dr > 20, "来源块 %d 字" % dr)
    page.screenshot(path=os.path.join(SHOT_DIR, "races-matrix.png"), full_page=True)

    labels = page.evaluate("() => [...document.querySelectorAll('nav.main .ngt')].map(b => b.textContent.trim())")
    # 角标「新」是入口的附属信息，不是入口名的一部分：读名字时把 .nb 剔掉再比
    subs = page.evaluate("() => [...document.querySelectorAll('nav.main a.nl')].map(a => {"
                         "const c = a.cloneNode(true);"
                         "c.querySelectorAll('.nb').forEach(n => n.remove());"
                         "return c.textContent.trim(); })")
    check("导航一级只剩分组标签", labels == ["天赋", "职业", "种族", "世界", "专业", "工具"], str(labels))
    check("全部二级入口常驻，不用点开",
          len(subs) == len(PAGES) + 1 and all(x in subs for x in ["首页", "区域与稀有", "副本", "团本",
                                                                  "系统规则", "传承", "排行"]),
          "%d 项：%s" % (len(subs), subs))
    check("导航里不再有任何下拉面板",
          page.evaluate("() => document.querySelectorAll('.ndp, .ndb, [aria-haspopup]').length") == 0)
    navh = page.evaluate("() => Math.round(document.querySelector('nav.main').getBoundingClientRect().height)")
    check("桌面导航排在一行内", navh <= 44, "%d px" % navh)
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
    check("副本页写明「世界」里还没有数据的板块",
          "还没有数据" in dtext and "世界地图" in dtext and "PvP" in dtext)
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
      const rows = [...document.querySelectorAll('#tbl tbody tr')].filter(r => !r.classList.contains('srow'));
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
    page.click('#traits button[data-act="all"]')   # 改版后默认不铺全表，分组检查要先展开
    page.wait_for_timeout(300)
    rt = page.evaluate("""() => ({ groups: [...document.querySelectorAll('#tt .lgrp')].map(x => x.innerText.replace(/\\n/g,' ').trim()),
        rows: [...document.querySelectorAll('#tt tbody tr')].length })""")
    check("种族特长表按种族分组", len(rt["groups"]) == 10 and rt["rows"] == 40,
          "%d 组 / %d 行" % (len(rt["groups"]), rt["rows"]))
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
        "twoRange": len([x for x in rows if x.get("levelRangeClient") or x.get("levelRangeAlt")]),
        "twoSize": len([x for x in rows if x.get("partySizeAlt")]),
        "twoName": len([x for x in rows if x.get("nameEnClient")]),
        "noqueue": len([x for x in rows if not x.get("clientActivityId")]),
        "src": len([x for x in rows if any(p.get("type") == "datamine_en"
                                           for p in (x.get("provenance") or []))]),
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
        src: document.querySelectorAll('.st.datamine_en').length,
        qrows: q ? q.querySelectorAll('tbody tr').length : -1,
        qnames: q ? [...q.querySelectorAll('tbody tr td b')].map(b => b.textContent.trim()) : [],
        intro: (document.querySelector('.card .dim') || {}).textContent || ''
      }; }""")
    check("进入人数按客户端给的数逐座摆出来", got["party"] == exp["party"],
          "卡面 %d / 数据 %d" % (got["party"], exp["party"]))
    check("等级区间分歧每一条都有标注", got["twoRange"] == exp["twoRange"],
          "%d / %d" % (got["twoRange"], exp["twoRange"]))
    check("同一座有两种排队人数的都写明", got["twoSize"] == exp["twoSize"],
          "%d / %d" % (got["twoSize"], exp["twoSize"]))
    check("英文原名两说的都并列不取舍", got["twoName"] == exp["twoName"],
          "%d / %d" % (got["twoName"], exp["twoName"]))
    check("客户端还不能排队的本逐条说明", got["noqueue"] == exp["noqueue"],
          "%d / %d" % (got["noqueue"], exp["noqueue"]))
    # 徽章数 = 用到这份数据的副本卡各一枚 + 那张排队条目表一枚
    check("用到客户端排队数据的都挂着它的出处", got["src"] == exp["src"] + 1,
          "徽章 %d / 条目 %d" % (got["src"], exp["src"]))
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
    check("区间或译名两说的条目都摆在卡面上", conf >= 5, "%d 处冲突标注" % conf)
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
        missing: document.querySelectorAll('#missing li').length,
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
    check("链接都指向副本页那一座", all(str(h).startswith("dungeons.html?d=") for h in g["links"]),
          str(g["links"][:2]))
    check("另一份名单自述的几座都在", g["claimed"] == len(claimed), "%d / %d" % (g["claimed"], len(claimed)))
    check("两边对不上的直说没有对应条目",
          g["noMatch"] == len([r for r in claimed if not r.get("clientActivityId")]), "%d 座" % g["noMatch"])
    exp_stats = [str(len(names)), str(len(claimed)),
                 str(len([r for r in claimed if r.get("clientActivityId")])),
                 str(len([r for r in claimed if r.get("nameCn")]))]
    check("四个规模读数等于数据现算", g["stats"] == exp_stats,
          "页面 %s / 数据 %s" % (g["stats"], exp_stats))
    check("「这一页还没有的」逐条交代", g["missing"] >= 5, "%d 条" % g["missing"])
    check("用到客户端排队数据的挂着出处", g["badges"] >= 2, "%d 枚" % g["badges"])
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
    check("拆不出条目的专业写原因而不是留白", "还没拆出条目" in empty, empty[:44])

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
    check("每个专业带来源与核对", src >= 1, "%d 条来源" % src)
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
    check("无限新增区域带标且写清怎么去", newtag["n"] == len([z for z in zones if z.get("isNew")]) and newtag["flight"] == newtag["n"],
          json.dumps(newtag))

    page.click('[data-t="rares"]')
    page.wait_for_timeout(1400)
    rc = page.evaluate("() => document.querySelectorAll('#wbody .rarecard').length")
    check("稀有卡数量对得上数据", rc == len(rares), "%d 张（数据 %d 个）" % (rc, len(rares)))
    marks = page.evaluate("""() => { const m = [...document.querySelectorAll('#wbody .zmark')];
      return { n: m.length, placed: m.filter(b => b.style.left && b.style.top).length }; }""")
    exp_marks = len([r for r in rares if r.get("mark")])
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
      return d ? d.innerText.length : 0; }""")
    check("逐条来源能展开", drawer > 40, "抽屉 %d 字" % drawer)

    page.click('[data-t="books"]')
    page.wait_for_timeout(1500)
    bt = page.evaluate("() => document.querySelectorAll('#wbody table.bktab tbody tr').length")
    check("书籍表行数对得上数据", bt == len(books), "%d 行（数据 %d 本）" % (bt, len(books)))
    bicon = page.evaluate("""() => { const a = [...document.querySelectorAll('#wbody table img')];
      return { n: a.length, broken: a.filter(i => i.complete && i.naturalWidth === 0).length }; }""")
    check("书本地图标用本地图且不出现坏图", bicon["n"] > 20 and bicon["broken"] == 0, json.dumps(bicon))
    miss = page.evaluate("() => document.querySelectorAll('#wbody .chips .chipc').length")
    check("没给坐标的书单独列出", miss == len(w.get("booksMissing") or []), "%d 本" % miss)
    rew = page.evaluate("() => document.querySelectorAll('#wbody table .pill').length")
    check("上游没给奖励的那档标待实测", rew >= len([r for r in w["bookRewards"] if r.get("noReward")]),
          "%d 个待实测徽标" % rew)

    page.click('[data-t="bag"]')
    page.wait_for_timeout(1200)
    bag = page.evaluate("""() => { const rows = [...document.querySelectorAll('#wbody table.mtx tbody tr')];
      return { rows: rows.length, l2: rows.filter(r => /待实测/.test(r.innerText)).length,
               camps: document.querySelectorAll('#wbody .rarecard').length }; }""")
    exp_camps = sum(len(c.get("places") or []) for c in (w["bagTool"].get("camps") or []))
    check("睡袋机制数值整表标待实测", bag["rows"] and bag["rows"] == bag["l2"], json.dumps(bag))
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
    nums = page.evaluate("""() => ({
      cov: [...document.querySelectorAll('.covnum .pill')].map(p => +p.querySelector('b').textContent),
      total: (document.querySelector('.covnum > span:last-child').textContent.match(/\\d+/) || [0])[0] })""")
    check("首页覆盖率四个数来自 scale.json",
          nums["cov"] == [sc["coverage"]["L0"], sc["coverage"]["L1"], sc["coverage"]["L2"], sc["coverage"]["L3"]],
          "页面 %s / 数据 %s" % (nums["cov"], [sc["coverage"][k] for k in ("L0", "L1", "L2", "L3")]))
    check("首页总条数与数据一致", int(nums["total"]) == sc["coverageTotal"],
          "页面 %s / 数据 %s" % (nums["total"], sc["coverageTotal"]))
    bar = page.evaluate("""() => { const i = [...document.querySelectorAll('.cov i')];
      return { n: i.length, sum: i.reduce((a, x) => a + x.getBoundingClientRect().width, 0),
               box: document.querySelector('.cov').getBoundingClientRect().width }; }""")
    check("覆盖率条四段宽度加起来等于条宽", bar["n"] == 4 and abs(bar["sum"] - bar["box"]) < 3,
          "四段 %.0fpx / 条 %.0fpx" % (bar["sum"], bar["box"]))
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
               notes: a.filter(x => x.querySelector('.modf .dim')).length }; }""")
    check("九张模块卡都带规模数字与口径说明", mods["n"] == 9 and mods["pills"] == 9 and mods["notes"] == 9,
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
        clsrow: [...document.querySelectorAll('.clsrow a')].map(a => a.getAttribute('href')),
        artFiles: arts.map(e => (((e.getAttribute('style') || '').match(/url\(([^)]+)\)/) || [])[1] || '')),
        artBad: arts.filter(e => bad(e.style && (e.style.backgroundImage || '').indexOf('img/art/') < 0)).length,
        artCards: cards.filter(c => c.querySelector('.bgart')).length,
        titles: [...document.querySelectorAll('.mod h2, .two h2')].map(e => e.innerText),
        four: [...document.querySelectorAll('.four b')].map(e => +e.innerText),
        bar: (() => { const b2 = document.querySelector('#treecard .bar i');
          return b2 ? { w: b2.style.width, aria: (b2.parentElement.getAttribute('aria-label') || '') } : null; })(),
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
    check("首页按三条线分组、每组三张卡，第四段是改动模块",
          st["groups"] == ["角色线", "世界线", "工具线", "自经典旧世以来的改动"] and
          st["perGroup"][:3] == [3, 3, 3],
          json.dumps({"g": st["groups"], "n": st["perGroup"]}, ensure_ascii=False))
    dup = [x for x in set(st["titles"]) if st["titles"].count(x) > 1]
    check("「最常用的两个」是天赋预览与副本，且九张卡不重复它们",
          st["two"] == ["先看一棵真树，再进计算器", "副本手册"] and not dup,
          json.dumps({"two": st["two"], "重复": dup}, ensure_ascii=False))
    check("hero 的职业入口是 9 个链接、只进那一职业页不做切树",
          len(st["clsrow"]) == 9 and st["heroLinks"] == 9, json.dumps(st["clsrow"][:2], ensure_ascii=False))
    check("卡片背景图全部是本地已转存素材，没有热链",
          len(st["artFiles"]) > 0 and all(f.startswith("img/art/") for f in st["artFiles"]),
          json.dumps(st["artFiles"][:3], ensure_ascii=False))
    check("带背景的卡是 5 张（3 张模块卡 + 2 张主推卡），其余留纯色",
          len(st["artFiles"]) == 5 and st["artCards"] == 3,
          "背景层 %d 张 / 模块卡带背景 %d 张" % (len(st["artFiles"]), st["artCards"]))
    check("改动四格加起来等于来源站自报的 changed 751",
          sum(st["four"]) == 751, "%s 合计 %d" % (st["four"], sum(st["four"])))
    check("天赋卡进度条有可读替代（aria-label 写明分子分母）",
          bool(st["bar"]) and "/" in st["bar"]["aria"] and str(st["bar"]["w"]).endswith("%"),
          json.dumps(st["bar"], ensure_ascii=False))
    # 角标不是手写的：app.js 拿 scale.navNew（「本站更新」最新一天的板块标签）去对导航项名字，
    # 对得上才画。所以这里不能写死"只有一枚"，要按同一条规则核。
    nav_new = sc.get("navNew") or []
    bad_labels = {re.sub(r"新$", "", str(x["on"]).strip()) for x in st["badge"]}
    check("导航角标只挂在最新一批更新对得上的项上，且除颜色外带可读名",
          len(st["badge"]) >= 1 and all(x["t"] == "新" and x["aria"] and x["title"] for x in st["badge"])
          and bool(bad_labels) and bad_labels <= set(nav_new),
          json.dumps({"角标项": sorted(bad_labels), "最新一批标签": nav_new}, ensure_ascii=False))
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
    check("hero 的读数框只框住倒计时，问答入口在框外",
          page.evaluate("() => { const cd = document.querySelector('.heros .cd');"
                        "return !!cd && !cd.querySelector('a') && cd.children.length === 2 &&"
                        "!!document.querySelector('.heros > a.cta'); }"),
          "读数框里混进了链接或段落层级不对")
    css = open(os.path.join(SRC, "css", "app.css"), encoding="utf-8").read()
    flat = css.replace(" ", "").replace("\n", "")
    check("卡片动效只有三处且都能关（hover 抬升 / 背景微缩放 / reduced-motion 归零）",
          ".mod:hover" in css and "prefers-reduced-motion" in css and
          "transform:none" in flat[flat.index("prefers-reduced-motion"):],
          "缺 hover 动效或缺可关声明")
    check("角标不占导航宽度：整条导航仍是一行",
          page.evaluate("() => { const ns=[...document.querySelectorAll('nav.main .in > *')];"
          "return new Set(ns.map(e => Math.round(e.getBoundingClientRect().top))).size; }") == 1,
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
    check("刻意不做的与时间点都在页上", nd >= 9, "%d 行" % nd)
    foot = page.evaluate("() => document.querySelector('#foot').innerText")
    check("页脚用的是 scale.json 那份词条口径", str(sc["pubTotal"]) in foot and "842" not in foot,
          "页脚写 %s，应含 %s 且不含全站数" % (foot.replace("\n", " ")[-40:], sc["pubTotal"]))
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
    check("排行页写明不是强度排行", ("不是强度排行" in rtxt or "不回答哪个职业强" in rtxt) and "DPS" in rtxt,
          "缺免责声明" if "强度" not in rtxt else "已写明")
    rp.screenshot(path=os.path.join(SHOT_DIR, "rank.png"))
    c2.close()

    hp = browser.new_context(viewport={"width": 1440, "height": 1000})
    hpg = hp.new_page()
    hpg.goto(base + "/index.html", wait_until="networkidle")
    hpg.wait_for_timeout(1800)
    hb = hpg.evaluate("""() => { const byTitle = (re) => [...document.querySelectorAll('.card')]
          .find(x => re.test((x.querySelector('h2') || {}).innerText || ''));
      const dyn = byTitle(/最新动态/);
      // 「自经典旧世以来的改动」是分组眉标，标题不在卡里：按卡里的四格找到这张卡
      const four = document.querySelector('#main .card .four');
      const chg = four ? four.closest('.card') : null;
      const head = chg && chg.previousElementSibling ? chg.previousElementSibling.innerText : '';
      return { rows: dyn ? dyn.querySelectorAll('.flowrow').length : 0,
               links: dyn ? [...dyn.querySelectorAll('a')].map(a => a.getAttribute('href') || '') : [],
               note: dyn ? (dyn.querySelector('.note') || {}).innerText || '' : '',
               four: chg ? chg.querySelectorAll('.four b').length : 0,
               fourtxt: chg ? [...chg.querySelectorAll('.four b')].map(b => b.innerText.trim()) : [],
               head: head.replace(/\\s+/g, ' ').slice(0, 40),
               kv: chg ? chg.querySelectorAll('.kv').length : 0,
               chgText: chg ? chg.innerText.replace(/\\s+/g, ' ') : '',
               chgl: document.querySelectorAll('#main .chgl').length }; }""")
    check("首页动态卡有时间点与两个入口", hb and hb["rows"] >= 4
          and any("updates.html" in x for x in hb["links"])
          and any("rank.html" in x for x in hb["links"]), str(hb))
    # 第五批改版把改动清单的数挪进「自经典旧世以来的改动」卡：同一个数不许在首页摆两遍
    check("改动四格是四个实数，动态卡不再重复列一遍",
          hb and hb["four"] == 4 and all(x.isdigit() for x in hb["fourtxt"]) and hb["chgl"] == 0,
          str(hb and {"four": hb["four"], "fourtxt": hb["fourtxt"], "chgl": hb["chgl"]}))
    check("改动四格挂在「自经典旧世以来的改动」这张卡上，且带对照行",
          hb and hb["four"] == 4 and "自经典旧世以来的改动" in hb["head"] and hb["kv"] >= 3,
          str(hb and {"head": hb["head"], "kv": hb["kv"]}))
    # 964（全部条目）与四格之和 751（真有变化的）同屏出现，不解释清楚就是自己打脸
    sc = json.load(open(os.path.join(SRC, "data", "scale.json"), encoding="utf-8"))["scale"]
    _sum = sum(int(x) for x in hb["fourtxt"])
    check("改动卡自己解释清「全部 964 条」与「四格之和 751」差在哪",
          hb and str(_sum) in hb["chgText"] and str(sc["changes"]) in hb["chgText"] and
          str(sc["changesTalents"]) in hb["chgText"] and "本身没变" in hb["chgText"],
          str(hb and hb["chgText"][:150]))
    check("动态卡写明这三件事怎么分开", hb and "三件事分开说" in hb["note"], (hb or {}).get("note", "")[:40])
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
            nums = page.evaluate("""() => [...document.querySelectorAll('.covnum .pill b')].map(b => +b.textContent)""")
            check("新站首页覆盖率四个数与 scale.json 一致",
                  nums == [S["coverage"]["L0"], S["coverage"]["L1"], S["coverage"]["L2"], S["coverage"]["L3"]],
                  "%s vs %s" % (nums, [S["coverage"][k] for k in ("L0", "L1", "L2", "L3")]))
            strip = page.evaluate("() => document.querySelectorAll('.stripc').length")
            check("新站首页九职业条齐全", strip == S["classes"], "%d 格" % strip)
            mods = page.evaluate("() => document.querySelectorAll('.mod').length")
            check("新站首页模块卡与旧站一样多", mods == 9, "%d 张" % mods)
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
            check("新站预览没有坏图，格子也链回计算器",
                  pv2 and pv2["broken"] == 0 and "talent.html?c=" in pv2["href"], pv2 and pv2["href"])
        else:
            tabs = page.evaluate("() => document.querySelectorAll('.picks .pick[data-t]').length")
            check("新站世界页四个面板齐全", tabs == 4, "%d 个" % tabs)
            for t in ["books", "bag", "zones"]:      # 切一圈再回到区域，验证面板切换不残留
                page.click('[data-t="%s"]' % t)
                page.wait_for_timeout(900)
            zc = page.evaluate("() => document.querySelectorAll('.zcard').length")
            check("新站区域卡数量与数据一致", zc == S["zones"], "%d 张（数据 %d）" % (zc, S["zones"]))
            page.click('[data-t="rares"]')
            page.wait_for_timeout(1200)
            marks = page.evaluate("""() => { const m = [...document.querySelectorAll('.zmark')];
              return { n: m.length, placed: m.filter(b => b.style.left).length }; }""")
            check("新站稀有标记点按数据摆位", marks["n"] == marks["placed"] and marks["n"] > 30,
                  "%d 个点全部定位" % marks["n"])
            body = page.evaluate("() => document.querySelector('#main').innerText")
            check("新站世界页正文没有面向开发的词", not dev_word_hits(body), "干净")
            page.screenshot(path=os.path.join(SHOT_DIR, "app-world-rares.png"))
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
    check("非已核实的条除颜色外带分级文字", all(lvs) and len(lvs) >= 1,
          json.dumps(lvs[:3], ensure_ascii=False))
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
        ("领主大厅", "dungeons.html",
         lambda: page.evaluate("() => document.querySelector('#d-hall-of-thanes').style.display") == "block"),
        ("预知", "talent.html",
         lambda: page.input_value("#tq") == "预知" and
         page.evaluate("() => [...document.querySelectorAll('.node')].filter(n => n.style.outline).length") >= 1),
        ("潜行者52型", "professions.html", lambda: page.input_value("#pq") == "潜行者52型"),
        ("强化英勇打击", "updates.html",
         lambda: page.input_value("#cq") == "强化英勇打击" and
         page.inner_text("#ccnt").strip() == "1 条"),
        ("影遁", "races.html", lambda: page.input_value("#fq") == "影遁"),
        ("影遁", "glossary.html", lambda: page.input_value("#q") == "影遁"),
        ("Molten Core", "raids.html", lambda: page.input_value("#rq") == "Molten Core"),
        ("兽人", "races.html",
         lambda: page.get_attribute(".racecard.on", "data-race") == "horde-orc"),
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
    check("挑战每条都带「待实测」徽标，点数每条都是 %s" % rules["pointPerChallenge"],
          len(s0["chPills"]) == total and set(s0["chPills"]) == {"待实测"} and
          set(s0["pts"]) == {str(rules["pointPerChallenge"])},
          "徽标 %d 个 / 行 %d / 点数集合 %s" % (
              len(s0["chPills"]), s0["chRows"], json.dumps(sorted(set(s0["pts"])), ensure_ascii=False)))
    check("进度奖励四条都标了待实测", set(s0["rePill"] or []) == {"待实测"},
          json.dumps(s0["rePill"], ensure_ascii=False))
    check("图全部是本地文件，没有热链", s0["hot"] == 0 and s0["local"] == 0,
          "外链 %d / 非 img 目录 %d" % (s0["hot"], s0["local"]))
    # 页面级来源块 1 块；点开某个专长才多一块（那条断言在下面的详情里查）
    check("页顶与页尾的来源块渲染出来了", s0["src"] >= 1, "%d 块来源" % s0["src"])

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
    check("详情里带分级徽标与可点开的来源",
          s1["detPill"] == ["已官方核实"] and s1["detSrc"] >= 1,
          json.dumps({"pill": s1["detPill"], "src": s1["detSrc"]}, ensure_ascii=False))
    # 长度这条是红线的兜底：详情里除了"本站不复制"那句声明，只剩名称/上限/位置/前置/日期。
    # 谁把每层效果说明抄回来，这段正文一定会撑破 200 字。
    check("详情没把每层效果说明抄回来（来源块以外 ≤200 字）",
          len(s1["detBody"]) <= 200 and "不写" in s1["detBody"] and "前置" in s1["detBody"],
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
    rails_seen = 0
    for name in PAGES:
        page.goto("%s/%s.html" % (base, name), wait_until="networkidle")
        page.wait_for_timeout(1300)
        r = page.evaluate(PROBE)
        check("%s 页文字对比度达 AA" % name, not r["bad"],
              json.dumps([{"位": b["label"], "比": b["cr"], "字": b["size"]} for b in r["bad"][:3]], ensure_ascii=False))
        weak[name] = r["bad"]
        rails_seen += r["rails"]
        if r["claims"]:
            check("%s 页声明了分级/来源，卡片就有来源轨" % name, r["rails"] >= 1,
                  "声明 %d 处 / 上轨 %d 张" % (r["claims"], r["rails"]))
    check("来源轨在全站铺得开（16 页合计 ≥20 张）", rails_seen >= 20, "%d 张" % rails_seen)

    # 琥珀金从此只表示交互与品牌：任何分级徽标都不许用它
    page.goto(base + "/systems.html", wait_until="networkidle")
    page.wait_for_timeout(1300)
    r = page.evaluate(PROBE)
    # 品牌色不兼任分级色。2026-10-11 品牌色从琥珀金换成无限蓝，所以这里读实时值比对，
    # 不再写死某个 rgb——否则下次换色这条断言会静默失效。
    bh = (r.get("brandHex") or "#49aee9").lstrip("#")
    brand = "rgb(%d, %d, %d)" % (int(bh[0:2], 16), int(bh[2:4], 16), int(bh[4:6], 16))
    gold = [k for k, v in r["lv"].items() if v in (brand, "rgb(224, 169, 109)")]
    check("分级徽标不借用品牌色（曾与琥珀金同色，现在是无限蓝）", not gold,
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
    rm = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
    rp = rm.new_page()
    rp.goto(base + "/legacy.html", wait_until="networkidle")
    rp.wait_for_timeout(1200)
    m = rp.evaluate("""() => { const c = document.querySelector('#main .card');
      const r = document.querySelector('#main .rail'); const cs = getComputedStyle(c);
      return { card: cs.animationName + '/' + cs.animationDuration,
        rail: r ? getComputedStyle(r, '::before').animationDuration : 'no-rail',
        btn: getComputedStyle(document.querySelector('button')).transitionDuration }; }""")
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




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", action="store_true",
                        help="强制跑新站（Vue）那组断言，端口不通就直接失败")
    parser.add_argument("--app-base", default=os.environ.get("APP_BASE", "http://127.0.0.1:8821"))
    args = parser.parse_args()
    global APP_BASE, APP_REQUIRED
    APP_BASE, APP_REQUIRED = args.app_base, args.app
    if not os.path.isdir(SHOT_DIR):
        os.makedirs(SHOT_DIR)
    httpd, base = start_server()
    print("本地服务：%s（根目录 %s）" % (base, SRC))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            test_pages(browser, base)
            test_talent(browser, base)
            test_dungeon_banner(browser, base)
            test_chooser(browser, base)
            test_abilities(browser, base)
            test_races(browser, base)
            test_grouping(browser, base)
            test_dungeon_data(browser, base)
            test_raids(browser, base)
            test_professions(browser, base)
            test_world(browser, base)
            test_home(browser, base)
            test_updates_rank(browser, base)
            test_search(browser, base)
            test_legacy(browser, base)
            test_design_system(browser, base)
            test_copy(browser, base)
            test_app(browser, base)
            test_design_baseline(browser, base)
            test_mobile(browser, base)
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
