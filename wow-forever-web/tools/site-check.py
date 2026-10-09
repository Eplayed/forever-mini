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
import socketserver
import sys
import threading

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("缺少 playwright：pip3 install playwright")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
TODAY = datetime.date.today().isoformat()
SHOT_DIR = os.path.join(ROOT, "docs", "screenshots", "check-" + TODAY)

PAGES = ["index", "talent", "chooser", "timeline", "skills", "dungeons", "systems", "races",
         "professions", "glossary", "provenance"]
# 演示结构（_demo.json）里写死了层级门槛与前置链，用它做确定性断言
DEMO_A00 = "a-0-0"
DEMO_A01 = "a-0-1"
DEMO_A11 = "a-1-1"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + (("  — " + detail) if detail else ""))


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


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
        page.on("response", lambda r, f=failed: f.append("%d %s" % (r.status, r.url.split("/")[-1])) if r.status >= 400 else None)
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
    check("特长表条数与数据一致", trs == n_traits, "DOM %d / 数据 %d" % (trs, n_traits))

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

    page.fill("#fq", "昏迷")
    page.wait_for_timeout(250)
    found = page.evaluate("() => document.querySelectorAll('#tt tbody tr').length")
    check("特长搜索按整句生效", 0 < found < trs, "「昏迷」命中 %d 条" % found)
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
    cards = page.evaluate("() => document.querySelectorAll('.rcard').length")
    check("种族卡数量与矩阵行数一致", cards == n_races, "卡片 %d" % cards)
    page.query_selector(".rcard button[data-d]").click()
    page.wait_for_timeout(250)
    dr = page.evaluate("() => { const d = document.querySelector('.rcard .drawer');"
                       "return d && d.style.display !== 'none' ? d.innerText.length : 0; }")
    check("种族卡来源抽屉能展开", dr > 20, "抽屉 %d 字" % dr)
    page.screenshot(path=os.path.join(SHOT_DIR, "races-matrix.png"), full_page=True)

    groups = page.evaluate("() => [...document.querySelectorAll('nav.main .ndb')]"
                           ".map(b => b.textContent.replace('▾', '').trim())")
    check("导航收拢成 5 个分组", groups == ["天赋", "职业", "种族", "世界", "工具"], str(groups))
    page.evaluate("() => { const b = [...document.querySelectorAll('nav.main .ndb')]"
                  ".find(x => x.textContent.indexOf('世界') >= 0); b.click(); }")
    page.wait_for_timeout(250)
    panel = page.evaluate("() => { const b = [...document.querySelectorAll('nav.main .ndb')]"
                          ".find(x => x.textContent.indexOf('世界') >= 0);"
                          "const p = b.parentNode.querySelector('.ndp');"
                          "return {open: b.parentNode.className.indexOf('open') >= 0,"
                          " items: [...p.querySelectorAll('a b')].map(a => a.textContent)}; }")
    check("点「世界」展开面板并列出副本手册",
          panel["open"] and any("副本手册" in i for i in panel["items"]), str(panel["items"]))
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    check("Esc 关闭面板", page.evaluate("() => document.querySelectorAll('nav.main .nd.open').length") == 0)
    onb = page.evaluate("() => { const b = document.querySelector('nav.main .ndb.on');"
                        "return b ? b.textContent.trim() : ''; }")
    check("当前页所在分组高亮", "种族" in onb, "高亮「%s」" % onb)
    ctx.close()

    m = browser.new_context(viewport={"width": 375, "height": 780}, is_mobile=True, has_touch=True)
    mp = m.new_page()
    mp.goto(base + "/races.html", wait_until="networkidle")
    mp.wait_for_timeout(1000)
    small = mp.evaluate("() => [...document.querySelectorAll('nav.main .ndb, nav.main a, #mx thead button.ch')]"
                        ".filter(e => e.offsetHeight && e.offsetHeight < 44)"
                        ".map(e => (e.className || 'a') + ':' + e.offsetHeight)")
    check("移动端导航与矩阵表头点击目标 ≥44px", not small, str(small[:4]))
    mp.evaluate("() => { const b = [...document.querySelectorAll('nav.main .ndb')]"
                ".find(x => x.textContent.indexOf('世界') >= 0); b.click(); }")
    mp.wait_for_timeout(250)
    mob = mp.evaluate("() => { const b = [...document.querySelectorAll('nav.main .ndb')]"
                      ".find(x => x.textContent.indexOf('世界') >= 0);"
                      "const p = b.parentNode.querySelector('.ndp'); const r = p.getBoundingClientRect();"
                      "const hs = [...p.querySelectorAll('a')].map(a => a.offsetHeight);"
                      "const lefts = [...p.querySelectorAll('a b')].map(x => Math.round(x.getBoundingClientRect().x - r.x));"
                      "return {right: Math.round(r.right), vw: window.innerWidth, min: Math.min.apply(null, hs), lefts: lefts}; }")
    check("移动端下拉不顶出视口且面板项 ≥44px",
          mob["right"] <= mob["vw"] and mob["min"] >= 44, json.dumps(mob, ensure_ascii=False))
    # 面板项是纵向 flex，移动端通用规则给的 align-items:center 会把标题与说明居中，这里必须左对齐
    check("移动端面板条目左对齐", all(v < 24 for v in mob["lefts"]), "文字左边缘偏移 %s" % mob["lefts"])
    mp.goto(base + "/dungeons.html", wait_until="networkidle")
    mp.wait_for_timeout(1000)
    dtext = mp.evaluate("() => document.querySelector('#main').innerText")
    check("副本页写明「世界」里还没采集的板块",
          "还没采集的" in dtext and "世界地图" in dtext and "PvP" in dtext)
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
        hits = [w for w in ["tools/", ".py", ".json", "[{", "undefined", "NaN", "[object"] if w in t]
        if hits:
            bad_pages.append("%s:%s" % (name, ",".join(hits)))
        dp.close()
    check("十页正文没有调试文案与原始数据", not bad_pages, "; ".join(bad_pages))
    # 官方 CDN 取回来的职业 / 种族图标要真的显示出来，且一张都不许坏
    rp = ctx.new_page()
    rp.goto(base + "/races.html", wait_until="networkidle")
    rp.wait_for_timeout(1300)
    ri = rp.evaluate("""() => { const a = [...document.querySelectorAll('.liw img')];
      return { imgs: a.length, broken: a.filter(i => i.complete && i.naturalWidth === 0).length,
               tiles: document.querySelectorAll('.rcard .liw.t').length }; }""")
    check("种族页用上本地官方图标", ri["imgs"] >= 21 and ri["broken"] == 0,
          "图 %d 张 / 坏 %d / 方块 %d" % (ri["imgs"], ri["broken"], ri["tiles"]))
    hp = ctx.new_page()
    hp.goto(base + "/index.html", wait_until="networkidle")
    hp.wait_for_timeout(1300)
    hi = hp.evaluate("""() => { const a = [...document.querySelectorAll('.cls .liw img')];
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
    check("采集型专业同时有采集点表与配方表", mt == 2 and mr > 20, "%d 张表 %d 行" % (mt, mr))
    page.click(".pick[data-p=camping]")
    page.wait_for_timeout(700)
    empty = page.evaluate("() => (document.querySelector('.empty') || {}).textContent || ''")
    check("没解析出来的专业写原因而不是留白", "没解析" in empty, empty[:44])

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


def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()
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
            test_professions(browser, base)
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
