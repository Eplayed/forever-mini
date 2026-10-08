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

PAGES = ["index", "talent", "chooser", "skills", "dungeons", "systems", "glossary", "provenance"]
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
    print("\n[1] 七页渲染")
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


def test_mobile(browser, base):
    print("\n[4] 375px 移动端")
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
            test_chooser(browser, base)
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
