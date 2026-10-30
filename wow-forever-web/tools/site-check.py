#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资料站回归自检（改界面/改交互后必跑）——**只测新站（Vue）这一份**。

做三件事：
1. 起本地静态服务（自动挑空闲端口）打 app/dist，逐路由用无头 Chrome 渲染，
   检查正文非空、无控制台报错、无失败请求、无文件式死链接、红线措辞不出现；
2. 跑天赋计算器的交互回归：加点 / 左键跟随减点模式 / 右键减点 / 长按减点 / 键盘回车 /
   层级门槛与前置校验 / 级联减点 / 分享编码 / 无痕窗口还原 / 复制方案文本 / 单系清空；
3. 截图存 docs/screenshots/check-<日期>/，任何一项不过直接退出码非 0。

2026-10-24 旧站删除：这一份不再打 `src/*.html`，被测对象是自己起服务渲染的 app/dist。
所以**跑之前必须先构建**（`cd app && npm run build`），否则断言全打在旧 dist 上。
用 `--app-base` 可以改打已经在跑的那台（vite preview :8821 或线上地址），那一台连不上直接算失败。

用法：python3 tools/site-check.py [--only talent,app]
依赖：pip3 install playwright && python3 -m playwright install 之前需系统装有 Chrome（本机用 channel="chrome"）。
"""
import argparse
import datetime
import functools
import http.server
import json
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
SRC = os.path.join(ROOT, "app", "dist")      # 被测产物（vite build 的输出）
DATA = os.path.join(ROOT, "app", "data")     # 数据基底，取路由参数用的真值从这里读
TODAY = datetime.date.today().isoformat()
SHOT_DIR = os.path.join(ROOT, "docs", "screenshots", "check-" + TODAY)


def app_routes():
    """路由名单从 app/src/router.js 现读，不在门禁里抄第二份。
       旧站还在的时候这里写死过 19 个 html 文件名，删旧站那次全数作废；
       路由表才是"这一站有哪些页"的唯一真相，加一页就该自动进这一轮回归。
       兜底路由（catch-all）不算一页，它专门用来接住不存在的地址。"""
    src = open(os.path.join(ROOT, "app", "src", "router.js"), encoding="utf-8").read()
    m = re.search(r"const routes = \[(.*?)\n\];", src, re.S)
    if not m:
        return []
    out = []
    for path, name in re.findall(r"\{\s*path:\s*'([^']+)',\s*name:\s*'([^']+)'", m.group(1)):
        if ":all" in path:
            continue
        out.append((name, path))
    return out


# 这一页光给路由打不开（要点名哪一座本），参数从数据里现取一条真值，不抄名字
ROUTE_QUERY = {"/dungeon": lambda: "?d=" + json.load(
    open(os.path.join(DATA, "dungeons.json"), encoding="utf-8"))["classicDungeons"][0]["id"]}

# 会渲染掉落/物品信息的页：红线"掉落不写百分比"只管这些页
# （玩法问答那页的"匹配度"是本站的算法读数，不是掉率，不能一起禁）
LOOT_ROUTES = {"/world", "/dungeons", "/dungeon", "/raids", "/items", "/bis", "/legacy", "/professions"}

# 分级徽标、来源块、覆盖率条、来源轨只许出现在溯源页（2026-10-13 站主决定）
PROVENANCE_ROUTE = "/provenance"


def route_q(path):
    """这一页要不要带参数才打得开（见 ROUTE_QUERY），没登记就是空串。"""
    f = ROUTE_QUERY.get(path)
    return f() if f else ""

# 官方 CDN 没有这些图标文件（多是无限服新装备），界面本来就该退回自绘块。
# 只有登记在 icon-gaps.json 里的键允许 404，多出来的失败请求一律算回归不通过。
# 读 app/data 那一份真源，不读 dist：dist 落后一轮时这里会跟着一起变瞎。
GAPS_PATH = os.path.join(DATA, "icon-gaps.json")
ICON_GAPS = set()
if os.path.exists(GAPS_PATH):
    ICON_GAPS = set(json.load(open(GAPS_PATH, encoding="utf-8")).get("keys") or [])


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
APP_REQUIRED = False          # 显式给了 --app-base 就连不上算失败，默认用自己起的那台

# 网页的手机版（375）暂时不作为门槛——站主 2026-10-25 定的，**只管网页，小程序那条线不受影响**。
# 落法不是把断言删掉：那批 375 的断言照跑、照打印，只是不过不算红（NOTE）。
# 这样"手机上有问题"这件事还看得见，但不会拦住桌面那批改动。
# 要恢复成硬门槛，把这个开关改回 False；逐页那批 375 断言（传承/配装/世界点位/职业表头/物品库）
# 没有走这个开关，各自钉着一条真出过的 bug，保持拦红——理由见 docs/VERIFY-删旧站-2026-10-24.md。
MOBILE_SOFT = True


notes = []


def check(name, ok, detail="", soft=False):
    """soft=True 的那条不过也只记 NOTE，不进失败清单——但仍然打印、仍然计数，
       免得"降成提示"变成"没人再看"。"""
    bad = not ok and not soft
    results.append((name, not bad, detail))
    if soft and not ok:
        notes.append(name)
    tag = "  PASS  " if ok else ("  NOTE  " if soft else "  FAIL  ")
    print(tag + name + (("  — " + detail) if detail else ""))


def snap(pg, **kw):
    """带 path 的截图统一走这里（2026-10-29 加动效那一轮之后必须）。两个默认值各治一件真发生过的红：
       ① timeout 90 秒——这台机器是软件光栅（swiftshader），整页截图实测 24~30 秒一张，
          默认 30 秒是擦着上限过的，负载一高就抛 TimeoutError 把整场门禁打断（今天两次）；
       ② animations="disabled"——让 Playwright 把在跑的过渡一次性拨到终态再拍。
          换页与展开现在有过渡了，不关掉就会拍在淡入的中间（半透明、面板还没挂回来），
          既慢又会产出"看着像坏了"的证据图。
       ③ 撞不上的那一拍再给一次：2026-10-30 整场门禁在专业页这张上断在 90 秒（当时负载 10+，
          别的会话在跑 3D），判据一条没错，是这台机器交不出那一帧。重试只放宽时间，
          不改判据、不吞异常——第二次还失败就照常抛出去，宁可红也不要跳过。
       注意：只包带 path 的调用。配装页那两帧 A/B 用的是 element.screenshot() 取字节，不走这里。"""
    kw.setdefault("animations", "disabled")
    kw.setdefault("timeout", 90000)
    try:
        return pg.screenshot(**kw)
    except Exception:
        kw["timeout"] = 180000
        return pg.screenshot(**kw)


# 页面上还有没有"在跑的过渡"——按过渡类名判，不按时间猜
MOTION_BUSY = ("() => [...document.querySelectorAll('#main *')].some(e => "
               "/\\b(page|swap|unfold|pop|idr|idf)-(enter|leave)/.test("
               "typeof e.className === 'string' ? e.className : ''))")


def settle_motion(page, timeout=12000):
    """等 2026-10-29 那轮交互动效（app/src/styles/motion.css）把画面送进终态再取数。
       为什么要等：面板切换用的是 mode="out-in"（旧面板先摘掉、新面板再挂），量早了会量在
       "整块内容还没挂回来"的那一帧上，报成"数量对不上 / 读到上一页 / 悬停没生效"。
       为什么要**顺手逼一帧**：门禁这台 headless Chrome（swiftshader、没有可视表面）不主动产帧，
       实测点了之后类永远停在 unfold-enter-from、高度停在 0，光等多少超时都没用；
       拍一张 8×8 的截图（本机约 3 秒）就会把过渡推到结束。真浏览器一直在产帧，
       这一下是测试环境专用的，不是给页面打补丁。"""
    import time as _t
    import tempfile as _tf
    pump = os.path.join(_tf.gettempdir(), "site-check-frame-pump.png")
    deadline = _t.time() + timeout / 1000.0
    while True:
        try:
            busy = page.evaluate(MOTION_BUSY)
        except Exception:
            return False
        if not busy:
            return True
        if _t.time() > deadline:
            return False
        try:
            page.screenshot(path=pump, clip={"x": 0, "y": 0, "width": 8, "height": 8},
                            timeout=90000)
        except Exception:
            return False


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
    """派发真事件，不调 element.onclick / oncontextmenu：
       旧站那批页面是内联 on* 属性，直接调得到；新站是 Vue 的 addEventListener，
       `n.oncontextmenu` 是 undefined —— 2026-10-24 旧站删掉后这里必须换写法。"""
    if button == "left":
        return page.evaluate("""(id) => { const n = document.querySelector(`[data-n="${id}"]`); if (!n) return false; n.click(); return true; }""", node_id)
    return page.evaluate("""(id) => { const n = document.querySelector(`[data-n="${id}"]`); if (!n) return false;
        n.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true })); return true; }""", node_id)


def long_press(page, node_id, hold=650):
    """按下→等过 500ms→抬起，再补发一次 click（模拟手指离开时浏览器打在"新节点"上的那一下）。
       长按后重渲染会换掉元素，所以只有时间戳守卫能挡住这次补发 click。"""
    ok = page.evaluate("""(id) => { const n = document.querySelector(`[data-n="${id}"]`); if (!n) return false;
        n.dispatchEvent(new Event('touchstart', { bubbles: true })); return true; }""", node_id)
    if ok:
        page.wait_for_timeout(hold)
        page.evaluate("""(id) => { const n = document.querySelector(`[data-n="${id}"]`);
            if (n) n.dispatchEvent(new Event('touchend', { bubbles: true })); }""", node_id)
        page.wait_for_timeout(50)
        click(page, node_id)
    page.wait_for_timeout(250)
    return ok


def points_text(page):
    return page.evaluate("""() => { const el = document.querySelector('.pts'); return el ? el.innerText.replace(/\\s+/g, ' ') : ''; }""")


def open_talent(page, base, extra=""):
    """演示结构 = app/data/talents/_demo.json，写死了层级门槛与前置链，适合做确定性断言。
       走 #/talent?c=_demo 直接载入。先清 localStorage 再整页重载：
       hash 路由只换 query 不会重新 boot 组件，上一轮存的方案会残留到这一条断言里。"""
    page.goto(base + "/#/talent", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.evaluate("() => localStorage.clear()")
    page.goto(base + "/#/talent?c=_demo" + extra)
    settle_motion(page)   # 换页/换 hash 走的是路由过渡，等它结束再读
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(1400)




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
    snap(page, path=os.path.join(SHOT_DIR, "talent-added.png"))

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
    snap(page, path=os.path.join(SHOT_DIR, "talent-cascade.png"))

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
    # 新开一个无痕上下文、直接给分享出来的那条地址：这才是"别人在群里点开"的样子。
    # 不再走 open_talent()——那个函数要先落 #/talent 再换 query，会把整条 hash 拼两遍。
    p2.goto(base + "/" + hash_, wait_until="networkidle")
    settle_motion(p2)   # 这一条的 URL 是拼出来的（base + "/" + hash_），批量补等待时按字面找 "#/" 漏了它
    p2.wait_for_timeout(1600)
    back = (ranks(p2, DEMO_A00)["ranks"], ranks(p2, DEMO_A01)["ranks"])
    check("无痕窗口按 hash 还原方案", back == origin, "原 %s → 还原 %s（地址 %s）" % (origin, back, hash_[:60]))
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







def test_spellbook(browser, base):
    """M2（2026-10-16）：法术书接进技能页、成就独立成页。
       两栈同页同断言——数字全部从 app/data 现算，不在脚本里写死条数。"""
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

    for label, url in ((u"新站", APP_BASE + "/#/skills"),):
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
        if label == u"新站":
            # 2026-10-20 站主决定：新站内容页只给一个数（数值类以插件为准），
            # "两个说法都摆着"那类红字撤到溯源页。旧站已冻结、行为照旧，所以这条只对新站成立。
            nconf = page.evaluate("() => document.querySelectorAll('#sptbl .conf').length")
            check("新站 法术书不摆两说红字（数据里 %d 条分歧留在字段与溯源页）" % n_alt, nconf == 0,
                  "%d 处（应 0）" % nconf)
            # 判据按数据来，不是"每行都得有级数"——数据里就有 13 条本来没给级数，
            # 上一版我写成"每行都要匹配 N 级"，那是断言在描述我的想象。
            n_rank = len([x for x in sp if x.get("ranks")])
            shown = page.evaluate(r"""() => {
              const td = [...document.querySelectorAll('#sptbl tbody tr:not(.grp2h) td')];
              return { rank: td.filter(x => /^\s*\d+ 级\s*$/.test(x.innerText)).length,
                       both: td.filter(x => /\d+\s*\/\s*\d+/.test(x.innerText)).length }; }""")
            check("新站 级数那一格显示几个数由数据定（%d 条有级数），且全页没有 N / M 双数写法" % n_rank,
                  shown["rank"] == n_rank and shown["both"] == 0,
                  "%d 格有级数 / %d 格双数" % (shown["rank"], shown["both"]))
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
        snap(page, path=os.path.join(SHOT_DIR, "spellbook-%s.png" % ("app" if label == u"新站" else "legacy")))
        check("%s 法术书页无报错与失败请求" % label, not errs and not failed,
              "; ".join((errs + failed)[:2]) or "干净")
        ctx.close()

    # 搜索索引点一条法术跳进来要已经是筛好的（带 c=<职业>&q=<名字>）
    ctx = browser.new_context(viewport={"width": 1440, "height": 1200})
    page = ctx.new_page()
    tgt = [x for x in sp if x["classId"] == "warrior"][0]
    page.goto(APP_BASE + "/#/skills?c=%s&q=%s" % (tgt["classId"], urllib.parse.quote(tgt["name"])),
              wait_until="networkidle")
    page.wait_for_timeout(1200)
    check("搜索带着职业与词跳进来，落地只剩那一条",
          page.evaluate("() => document.querySelectorAll('#sptbl tbody tr:not(.grp2h)').length") == 1
          and page.evaluate("() => document.getElementById('q').value") == tgt["name"],
          page.evaluate("() => document.getElementById('cnt').textContent"))
    ctx.close()

    for label, url in ((u"新站", APP_BASE + "/#/achievements"),):
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
        # 这一页 226 行、每行一颗图标，本机是软件光栅（swiftshader）：
        # 实测一次视口截图就要 24~30 秒，Playwright 默认 30 秒超时是**擦着上限过的**——
        # 10-27 那轮"整站门禁跑不完"就是死在这一句，不是页面坏了。
        # 两处放宽：关掉动画等帧（省 ~5 秒）+ 把这一次调用的上限抬到 90 秒。
        snap(page, path=os.path.join(SHOT_DIR, "achievements-%s.png" %
                                          ("app" if label == u"新站" else "legacy")))
        ctx.close()

    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(APP_BASE + "/#/achievements?q=" + urllib.parse.quote(show[0]["name"]), wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1200)
    check("搜索词跳进成就页就已是筛好的",
          page.evaluate("() => document.querySelectorAll('#tbl tbody tr:not(.grp2h)').length") > 0
          and page.evaluate("() => document.getElementById('q').value") == show[0]["name"],
          page.evaluate("() => document.getElementById('cnt').textContent"))
    ctx.close()

    # ---- 新站视觉层（docs/DESIGN-app-upgrade-2026-10-16.md）----
    if app_up(browser):
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        page.goto(APP_BASE + "/#/skills", wait_until="networkidle")
        settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
        snap(page, path=os.path.join(SHOT_DIR, "app-board-skills.png"))
        ctx.close()

        ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.goto(APP_BASE + "/#/professions", wait_until="networkidle")
        settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
        page.wait_for_timeout(1800)
        m = page.evaluate("""() => ({ over: document.documentElement.scrollWidth - innerWidth,
          fade: [...document.querySelectorAll('.boardwrap')].length,
          src: [...document.querySelectorAll('.board .c-src')].filter(x => x.innerText.indexOf('商人') >= 0).length })""")
        check("新站专业页 375 下整页不横向溢出（表在容器里滚）", m["over"] <= 1, json.dumps(m))
        check("新站专业页来源那一格仍写着商人（视觉改版没把 M2-G 的层弄丢）", m["src"] > 0,
              "%d 行" % m["src"])
        snap(page, path=os.path.join(SHOT_DIR, "app-board-prof-m.png"))
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
       扫的是 app/src/styles 这三份 + 每个 .vue 的 style 块 + JS 里 setProperty('--x')：
       令牌文件已经跟着旧站一起搬过一次（src/css → app/src/styles），
       这里再留一个"从被测产物目录找源码"的写法就会静默扫到空，报出"只声明了 3 个"这种荒唐数。"""
    print("\n[6c] 设计令牌存在性（新站）")
    import glob

    def read(fp):
        try:
            return open(fp, encoding="utf-8").read()
        except Exception:
            return ""

    # 声明来源：三份 CSS + 各 .vue 的 style 块 + JS 里 setProperty('--x'
    decl_src = glob.glob(os.path.join(ROOT, "app", "src", "styles", "*.css")) \
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
        + [os.path.join(ROOT, "app", "src", "styles", "board.css")]
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    snap(page, path=os.path.join(SHOT_DIR, "app-world-books.png"))

    page.goto(APP_BASE + "/#/world?t=bag", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1800)
    first_tab = page.evaluate("() => (document.querySelector('.pick.on b') || {}).innerText")
    page.goto(APP_BASE + "/#/world?t=rares", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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

    # ---- S3（2026-10-29）：图例即筛选 + 点位分级 ----
    # 这一节存在的直接原因：第一版我把 @click 只挂在「全部」那颗上，类别芯片点了
    # aria-pressed 不动、图上一颗不少——构建和上面所有旧断言全绿，只有真点一下才暴露。
    # 所以这里必须"点一次、再量一次"，且 click 与读结果分开两次调用（Vue 更新是异步的）。
    page.goto(APP_BASE + "/#/world?t=zones", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(2000)
    lg = page.evaluate("""() => {
      const bs = [...document.querySelectorAll('.zband')];
      const i = bs.findIndex(b => b.querySelectorAll('.zlg').length > 1);
      if (i < 0) return { none: true };
      const b0 = bs[i];
      const chip = b0.querySelector('[data-lg="rare"]');
      const kinds = (el) => [...new Set([...el.querySelectorAll('.zdot')].map(d => d.dataset.kind))].sort();
      const num = (el) => parseInt((el.textContent || '').replace(/\\D/g, ''), 10) || 0;
      return { idx: i, dots: b0.querySelectorAll('.zdot').length,
               rows: b0.querySelectorAll('.zrow').length,
               chips: b0.querySelectorAll('.zlg').length,
               kinds: kinds(b0), wantRare: chip ? num(chip) : -1,
               pressed: chip ? chip.getAttribute('aria-pressed') : null,
               src: (b0.querySelector('.zcanvas img') || {}).getAttribute
                 ? b0.querySelector('.zcanvas img').getAttribute('src') : '',
               t1: [...b0.querySelectorAll('.zdot.t1 .zdot-n')].map(e => Math.round(e.getBoundingClientRect().height)),
               t2: [...b0.querySelectorAll('.zdot.t2 .zdot-n')].map(e => Math.round(e.getBoundingClientRect().height)),
               t3: [...b0.querySelectorAll('.zdot.t3 .zdot-n')].map(e => Math.round(e.getBoundingClientRect().height)),
               hit: (b0.querySelector('.zdot.t3') || {}).getBoundingClientRect
                 ? Math.round(b0.querySelector('.zdot.t3').getBoundingClientRect().height) : 0,
               over: document.documentElement.scrollWidth - window.innerWidth };
    }""")
    check("S3 区域卡上混标多类时出图例（芯片数 = 类别数 + 全部）",
          not lg.get("none") and lg["chips"] == len(lg["kinds"]) + 1,
          "%d 颗芯片 / %d 类 %s" % (lg.get("chips", 0), len(lg.get("kinds", [])), lg.get("kinds")))
    check("S3 桌面 1440 加了图例这一行也不横溢", lg.get("over", 99) <= 1, "%s" % lg.get("over"))
    # 只比"这一屏真出现的档"：世界页区域卡只有书与稀有（t3 与 t2），拿一个不存在的档
    # 当 0 去比会造出一条永远为假的断言——第一版就是这么红的，是判据错不是功能坏。
    _sz = lambda a: (min(a) if a else None)
    _tiers = [x for x in (_sz(lg.get("t1")), _sz(lg.get("t2")), _sz(lg.get("t3"))) if x is not None]
    check("S3 分级只改视觉不改点击区（小那颗仍有 20px 命中框）",
          len(_tiers) == len(set(_tiers)) and lg.get("hit", 0) >= 20,
          "这一屏出现的档从大到小 %s / 最小那颗的点击区 %spx" % (_tiers, lg.get("hit")))
    band = page.locator(".zband").nth(lg["idx"])
    band.locator('[data-lg="rare"]').click()
    page.wait_for_timeout(700)
    f = page.evaluate("""(i) => {
      const b0 = [...document.querySelectorAll('.zband')][i];
      const chip = b0.querySelector('[data-lg="rare"]');
      return { dots: b0.querySelectorAll('.zdot').length,
               rows: b0.querySelectorAll('.zrow').length,
               kinds: [...new Set([...b0.querySelectorAll('.zdot')].map(d => d.dataset.kind))],
               pressed: [...b0.querySelectorAll('.zlg')].map(c => c.getAttribute('aria-pressed')),
               src: (b0.querySelector('.zcanvas img') || {}).getAttribute
                 ? b0.querySelector('.zcanvas img').getAttribute('src') : '' };
    }""", lg["idx"])
    check("S3 点「稀有」真的只剩稀有（颗数 = 芯片上写的数）",
          f["kinds"] == ["rare"] and f["dots"] == lg["wantRare"],
          "图上 %d 颗 %s / 芯片写 %d（点前 %d 颗 %s）" % (f["dots"], f["kinds"], lg["wantRare"], lg["dots"], lg["kinds"]))
    check("S3 筛选只筛图上的点，右边列表一条不藏（选了看不见的红线）",
          f["rows"] == lg["rows"], "筛选后列表 %d 行 / 筛选前 %d 行" % (f["rows"], lg["rows"]))
    check("S3 选中态跟着走：稀有那颗 pressed=true、全部 pressed=false",
          f["pressed"][0] == "false" and "true" in f["pressed"][1:], "%s" % f["pressed"])
    check("S3 筛选不许把底图换掉（底图按全量点选，参照物不能一动就跳）",
          f["src"] == lg["src"] and bool(f["src"]), "%s -> %s" % (lg["src"][-28:], f["src"][-28:]))
    band.locator('[data-lg="rare"]').click()
    page.wait_for_timeout(700)
    back = page.evaluate("""(i) => { const b0 = [...document.querySelectorAll('.zband')][i];
      return { dots: b0.querySelectorAll('.zdot').length,
               kinds: [...new Set([...b0.querySelectorAll('.zdot')].map(d => d.dataset.kind))].length }; }""",
                         lg["idx"])
    check("S3 再点同一颗回到「全部」（不是一次性开关）",
          back["dots"] == lg["dots"] and back["kinds"] == len(lg["kinds"]),
          "回到 %d 颗 / %d 类（原本 %d 颗 / %d 类）" % (back["dots"], back["kinds"], lg["dots"], len(lg["kinds"])))

    mctx = browser.new_context(viewport={"width": 375, "height": 812})
    mp = mctx.new_page()
    for t in ("zones", "books", "bag"):
        mp.goto(APP_BASE + "/#/world?t=" + t, wait_until="networkidle")
        settle_motion(mp)   # 换 hash 走的是路由过渡，等它结束再读
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
    snap(mp, path=os.path.join(SHOT_DIR, "app-world-zones-m.png"))
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
        settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    settle_motion(mp)   # 换 hash 走的是路由过渡，等它结束再读
    mp.wait_for_timeout(1800)
    mm = mp.evaluate("""() => ({over: document.documentElement.scrollWidth - window.innerWidth,
      mapW: (document.querySelector('.dgeo .zbig') || { offsetWidth: 0 }).offsetWidth,
      dot: (() => { const d = document.querySelector('.dgeo .zdot'); if (!d) return null;
        const r = d.getBoundingClientRect(); return r.width >= 30; })()})""")
    check("375 上入口那张图占满一整块、点够大、整页不横溢",
          mm["over"] == 0 and mm["mapW"] >= 0.7 * 375 and mm["dot"] is not False,
          json.dumps(mm, ensure_ascii=False))
    snap(mp, path=os.path.join(SHOT_DIR, "app-dungeon-geo-m.png"))
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
            gates: cells.filter(e => e.querySelector('.lge-gate')).length,
            gateTxt: [...document.querySelectorAll('#ltree .lge-gate')].map(e => e.innerText.replace(/\\s+/g,' ').trim()),
            lines: document.querySelectorAll('.lge-links line').length,
            h2: (document.querySelector('#ltree h2')||{}).innerText.replace(/\\s+/g,' ').trim()}; }""")

    g = grid_state()
    t0 = trees[0]

    # 客户端 1.60.1.70532 起三棵树是 5×5，第 4 排与第 4 列整条空着。
    # 页面把全空的排/列收掉显示，但排号仍用客户端真实值——判据按同一条规则现算，
    # 不是把 4 或 5 抄进断言（2026-10-23 那条"仍按四列摆"就是把旧事实当过常量的例子）。
    def vis(t):
        used = [s for s in t["slots"] if not s.get("empty")]
        rows = [r for r in range(t["rows"]) if any(s["row"] == r for s in used)]
        cols = [c for c in range(t["cols"]) if any(s["col"] == c for s in used)]
        return rows, cols

    v0r, v0c = vis(t0)
    named = lambda t: [s for s in t["slots"] if s.get("perk") and not s.get("empty") and not s.get("unknown")]
    want_names = [perks[s["perk"]]["nameCn"] for s in
                  sorted(named(t0), key=lambda s: (s["row"], s["col"]))]
    check("格子按客户端坐标铺，全空的排与列收掉；排号仍是客户端真实排号",
          g["rows"] == len(v0r) and g["cells"] == len(v0r) * len(v0c)
          and g["cols"] == len(v0c) and g["rails"] == ["第%d排" % (r + 1) for r in v0r],
          "%d 排 × %d 列 = %d 格（数据 %d 排 %d 列，收掉后 %d × %d），排号 %s"
          % (g["rows"], g["cols"], g["cells"], t0["rows"], t0["cols"], len(v0r), len(v0c), g["rails"]))
    check("三种格子各是各的数：专长 / 未公开 / 这一排没这个位置",
          g["perk"] == known(t0) and g["unk"] == unk(t0)
          and g["perk"] + g["unk"] + g["none"] == len(v0r) * len(v0c),
          "专长 %d / 未公开 %d / 空 %d（数据 %d / %d）" % (g["perk"], g["unk"], g["none"],
                                                      known(t0), unk(t0)))
    check("格子里的专长名与顺序等于这份数据按坐标排出来的",
          g["names"] == want_names, "页面 %s ／ 数据 %s" % (g["names"], want_names))
    pre_n = len([p for p in perks.values() if p["treeId"] == t0["id"] and p.get("prerequisiteCn")])
    check("有前置的格子都挂了角标，数量与数据一致", g["tags"] == pre_n,
          "画 %d 个，数据里这一棵有前置的 %d 个" % (g["tags"], pre_n))
    gate_n = len([p for p in perks.values()
                  if p["treeId"] == t0["id"] and (p.get("treePointsRequired") or 0) > 0])
    check("要本树点数的格子都标了门槛，数字直接来自数据（不是写死的 5/10）",
          g["gates"] == gate_n and all("要 " in x for x in g["gateTxt"]),
          "画 %d 个（数据 %d 个）：%s" % (g["gates"], gate_n, g["gateTxt"]))
    check("前置连线画得出来，条数等于数据里这一棵的连线数",
          g["lines"] == len(t0["links"]), "%d 条（数据 %d 条）" % (g["lines"], len(t0["links"])))
    fixed = page.evaluate("""() => { const t = document.querySelector('#main').innerText.replace(/\\s+/g,' ');
      return {assume: t.indexOf('每层 1 点') >= 0 && t.indexOf('还没核实') >= 0,
              noAcct: t.indexOf('不读取游戏账号') >= 0, local: t.indexOf('只存在你这台设备的浏览器里') >= 0}; }""")
    check("规划假设与隐私边界这两句固定显示（方案要求的硬口径）",
          fixed["assume"] and fixed["noAcct"] and fixed["local"], json.dumps(fixed, ensure_ascii=False))

    # ---- ② 详情栏：没选时不空，选了说这个专长 ----
    det0 = page.evaluate("""() => ({legend: [...document.querySelectorAll('.lge-legend li')].map(e => e.innerText.replace(/\\s+/g,' ').trim()),
      read: [...document.querySelectorAll('#ldet .lge-read > span')].map(e => e.innerText.replace(/\\s+/g,' ').trim()),
      perk: !!document.querySelector('.lge-perk')})""")
    t0perks = [p for p in perks.values() if p["treeId"] == t0["id"]]
    # 读数里 <b>数</b>标签 是紧挨着写的（间距靠 CSS 的 gap），innerText 里不会有空格，
    # 所以比的是"去掉所有空白之后一样"，不是比字符串相等——否则这条会假红。
    want_read = ["%d个专长" % len(t0perks),
                 "%d层最多可点" % sum(p.get("maxRank") or 0 for p in t0perks),
                 "%d个要先点前置" % len([p for p in t0perks if p.get("prerequisiteCn")])]
    squash = lambda xs: [re.sub(r"\s+", "", x) for x in xs]
    # 图例从"三条"变"四条"是这一轮有意加的（门槛与连线上了界面，不解释就没人才看懂那些角标）；
    # 判据按"四种标记各有一条说明"来查，不再数条数——数条数就是又一个抄死的常量。
    ltxt = " ".join(det0["legend"])
    check("没选专长时详情栏仍有三行读数，图例把四种标记都说清了",
          not det0["perk"] and squash(det0["read"]) == squash(want_read)
          and all(k in ltxt for k in ("专长", "投满", "线", "没公开")),
          "读数 %s ／ 数据 %s ／ 图例 %d 条" % (det0["read"], want_read, len(det0["legend"])))
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

    # ---- ③ 换树清选中这一发挪到 ③c：先把加点规划器在当前这棵上跑完，
    #          不然树一切走，③b 那些格子全在另一棵里，点了等于没点（第一版就栽在这）----
    t1 = trees[1]
    # ---- ③b 加点规划器：全部用真点击走一遍，判据对着数据里的门槛/前置/上限算 ----
    def pick(pid):
        # pid 传的是数据里的完整 id（legacy-perk-xxx），不再拼前缀——拼两次会选不到格子
        page.evaluate("id => { const e = document.querySelector('[data-perk=\"' + id + '\"]');"
                      " if (e) e.click(); }", pid)
        page.wait_for_timeout(260)

    def plan_state():
        # 每个字段都做空值兜底：详情栏在"没选格子"时整块不存在，直接 .innerText.trim() 会炸在门禁里
        return page.evaluate("""() => { const A = document.querySelector('.lge-act [data-act="add"]');
          const S = document.querySelector('.lge-act [data-act="sub"]');
          const txt = (e) => e ? (e.innerText || '').replace(/\\s+/g, ' ').trim() : '';
          const mons = document.querySelectorAll('.lge-ranks .mono');
          return { bar: txt(document.querySelector('.lge-planbar .bn')),
            det: txt(document.querySelector('.lge-perk h2')),
            addDis: A ? !!A.disabled : null, subDis: S ? !!S.disabled : null,
            why: txt(document.querySelector('.ldetail .note')),
            filled: [...document.querySelectorAll('#ltree .lslot.filled .nm')].map(e => (e.innerText||'').trim()),
            now: txt(mons[1]), det2: !!document.querySelector('.lge-perk'),
            toast: txt(document.querySelector('.lge-toast')),
            lit: document.querySelectorAll('.lge-links line.on').length }; }""")

    def tap(act_, n=1):
        for _ in range(n):
            page.evaluate("m => { const e = document.querySelector('.lge-act [data-act=\"' + m + '\"]');"
                          " if (e && !e.disabled) e.click(); }", act_)
            page.wait_for_timeout(70)

    cap_n = (L["meta"]["rules"].get("launchSpendingCap") or 0)

    def legal_plan(t, want):
        """按数据里的门槛/前置/上限贪心凑一组合法点法（凑到 want 点）。
        门禁自己算一遍，不是把某个方案抄成常量——数据换了它跟着换。"""
        ps = [p for p in perks.values() if p["treeId"] == t["id"]]
        st, spent, order = {}, 0, []
        while spent < want:
            moved = False
            for p in sorted(ps, key=lambda x: (x.get("treePointsRequired") or 0)):
                cur = st.get(p["id"], 0)
                if cur >= (p.get("maxRank") or 0):
                    continue
                if spent < (p.get("treePointsRequired") or 0):
                    continue
                if p.get("prerequisite") and not st.get(p["prerequisite"]):
                    continue
                st[p["id"]] = cur + 1
                if p["id"] not in order:
                    order.append(p["id"])
                spent += 1
                moved = True
                if spent >= want:
                    break
            if not moved:
                break
        return [(i.replace("legacy-perk-", ""), st[i]) for i in order]

    gate5 = [p for p in perks.values() if p["treeId"] == t0["id"] and p.get("treePointsRequired") == 5][0]
    pick(gate5["id"])
    s0 = plan_state()
    check("门槛没够的格子：加号置灰，原因把要几点写清楚（不是只灰着不给理由）",
          s0["det2"] and s0["addDis"] is True and ("投满 %d 点" % gate5["treePointsRequired"]) in s0["why"],
          "%s → %s" % (gate5["nameCn"], json.dumps(s0, ensure_ascii=False)[:160]))
    entry = [p for p in perks.values()
             if p["treeId"] == t0["id"] and not p.get("treePointsRequired") and not p.get("prerequisite")][0]
    pick(entry["id"]); tap("add", entry["maxRank"])
    s1 = plan_state()
    check("点满一个入口格：已投点数与格子上那个数一起动（每层按 1 点，界面上标着是估算）",
          ("%s 点" % entry["maxRank"]) in s1["bar"] and entry["nameCn"] in s1["filled"]
          and s1["now"] == "已点 %d 点" % entry["maxRank"],
          "%s ／ %s" % (s1["bar"], s1["now"]))
    pick(gate5["id"]); tap("add", 1)
    s2 = plan_state()
    check("投够本树点数之后，原来锁着的格子真的能点了（不是只做样子）",
          s2["addDis"] is False or "点满" in s2["why"],
          "%s → %s" % (gate5["nameCn"], s2["why"] or "可继续加"))
    # 花满上限：按数据现算一组合法点法，逐格点到 cap 点，再验两件事——
    #   ① 还有余量的格子加号也置灰并说"已经花满"；② 退掉带后续依赖的那一格会被拦住
    page.evaluate("() => { const b=[...document.querySelectorAll('.lge-planact button')]"
                  ".find(x=>x.innerText.indexOf('全部清空')>=0); if (b) b.click(); }")
    page.wait_for_timeout(400)
    plan = legal_plan(t0, cap_n)
    got = {}
    for pid, n in plan:
        pick("legacy-perk-" + pid); tap("add", n)
        got["legacy-perk-" + pid] = n
    spare = [p for p in perks.values() if p["treeId"] == t0["id"]
             and (p.get("maxRank") or 0) > got.get(p["id"], 0)]
    if spare:
        pick(spare[0]["id"])
    s4 = plan_state()
    check("花满每个角色的上限后，还有余量的格子加号也置灰并说明要先退点",
          ("还能花 0 点" in s4["bar"]) and ("已经花满 %d 点" % cap_n) in s4["why"],
          "%s ／ %s" % (s4["bar"], s4["why"]))
    check("连线两端都点了点之后，那条线变成高亮（前置关系看得出走通了）",
          s4["lit"] >= 1, "高亮 %d 条" % s4["lit"])
    # 退点保护：从这一组合法点法里找"前置与后续都真点了点"的一对，把前置的最后一点退掉
    chain = None
    for full, n in got.items():
        kid = perks.get(full) or {}
        pre_id = kid.get("prerequisite")
        if kid and pre_id and got.get(pre_id):
            chain = (kid, pre_id)
            break
    if chain:
        kid, pre_id = chain
        pick(pre_id)
        tap("sub", got[pre_id])            # 一直退到会被拦为止
        s3 = plan_state()
        # 拦住的话走的是轻提示（toast），详情栏下面那句只说"为什么加不了"
        msg3 = (s3["toast"] or s3["why"])
        check("退掉前置那一格会被拦住，且说清是哪一格还点着（绝不静默清掉别的点）",
              "不能退" in msg3 and kid["nameCn"] in msg3,
              "%s → %s" % (perks[pre_id]["nameCn"], msg3[:120]))
    else:
        check("退掉前置那一格会被拦住，且说清是哪一格还点着（绝不静默清掉别的点）",
              False, "这一组点法里找不到「前置与后续都点了」的一对，判据没跑到")
    page.evaluate("() => { const b=[...document.querySelectorAll('.lge-planact button')]"
                  ".find(x=>x.innerText.indexOf('全部清空')>=0); if (b) b.click(); }")
    page.wait_for_timeout(500)
    s5 = plan_state()
    check("全部清空能回到 0 点（清空是显式按钮，不是刷新页面）",
          "已投 0 点" in s5["bar"] and not s5["filled"], "%s" % s5["bar"])

    # ---- ③c 换一棵树：格子与名字跟着换，上一棵的选中态清掉 ----
    pick(entry["id"])
    page.evaluate("id => document.querySelector('[data-t=\"' + id + '\"]').click()", t1["id"])
    page.wait_for_timeout(800)
    v1r, v1c = vis(t1)
    sw = page.evaluate("""() => ({on: document.querySelectorAll('#ltree .lslot.on').length,
      perk: !!document.querySelector('.lge-perk'),
      names: [...document.querySelectorAll('#ltree BUTTON.lslot .nm')].map(e => e.innerText.trim()),
      cells: document.querySelectorAll('#ltree .lslot').length,
      rails: [...document.querySelectorAll('.lge-rail')].map(e => e.innerText.trim())})""")
    want1 = [perks[s["perk"]]["nameCn"] for s in
             sorted(named(t1), key=lambda s: (s["row"], s["col"]))]
    check("换一棵树：格子与名字跟着换，上一棵的选中态清掉、详情回到概览",
          sw["on"] == 0 and not sw["perk"] and sw["names"] == want1
          and sw["cells"] == len(v1r) * len(v1c)
          and sw["rails"] == ["第%d排" % (r + 1) for r in v1r],
          "%d 格 / 选中 %d / %s" % (sw["cells"], sw["on"], sw["names"][:3]))
    page.evaluate("id => document.querySelector('[data-t=\"' + id + '\"]').click()", t0["id"])
    page.wait_for_timeout(700)

    # ---- ④ 六组挑战：默认只开第一组，搜索自动展开，内容一条不少 ----
    reg_groups = [dict(g, items=[x for x in (g.get("items") or []) if not x.get("special")])
                  for g in groups]
    reg_items = [x for g in reg_groups for x in g["items"]]
    sp_items = [x for g in groups for x in (g.get("items") or []) if x.get("special")]
    ch = page.evaluate("""() => ({blocks: document.querySelectorAll('#lch .lchgrp').length,
      open: [...document.querySelectorAll('#lch [aria-expanded]')].filter(e => e.getAttribute('aria-expanded') === 'true').length,
      vis: [...document.querySelectorAll('#lch tbody tr')].filter(r => r.offsetParent).length,
      all: document.querySelectorAll('#lch tbody tr').length,
      chk: document.querySelectorAll('#lch input[type=checkbox]').length,
      heads: [...document.querySelectorAll('.lchhead > b')].map(e => e.innerText.trim()),
      sums: [...document.querySelectorAll('.lchhead > .mono')].map(e => e.innerText.replace(/\\s+/g,' ').trim()),
      spRows: [...document.querySelectorAll('.lge-special tbody tr')].map(e => e.innerText.replace(/\\s+/g,' ').trim()),
      counter: (document.querySelector('.field .mono')||{}).innerText.trim()})""")
    g0 = reg_groups[0]
    want_sums = ["%d 项 · 已勾 0 · 合计 %d 点"
                 % (len(g["items"]), sum(x.get("points") or 0 for x in g["items"])) for g in reg_groups]
    check("六组挑战的组头写着项数、已勾数与合计点数，数全部来自明细",
          ch["blocks"] == len(reg_groups) == 6 and ch["heads"] == [g["nameCn"] for g in reg_groups]
          and ch["sums"] == want_sums, "；".join(ch["sums"]) + " ／ 数据 " + "；".join(want_sums))
    # 矩阵与表格是同一批条目的两种摆法（2026-10-25）：勾选框一律一条一个，
    # "行数"不再是判据——摆成矩阵的那两组，行是子分类不是条目。
    # 下面这份 matrixable 与 app/src/lib/legacy-plan.js 的 challengeMatrix 各写各的、互不引用：
    # 页面那份改了，门禁这份还能把它兜回来（同 item-stats 那套做法）。
    def matrixable(items):
        subs = []
        by = {}
        for x in items:
            if not x.get("sub") or not x.get("nameCn"):
                return None
            if x["sub"] not in by:
                by[x["sub"]] = []
                subs.append(x["sub"])
            by[x["sub"]].append(x)
        if len(subs) < 2:
            return None
        n = len(by[subs[0]])
        if n < 2 or any(len(by[s]) != n for s in subs):
            return None
        cols = None
        for s in subs:
            labels = []
            for x in by[s]:
                at = x["nameCn"].find(s)
                if at < 0:
                    return None
                lab = (x["nameCn"][:at] + x["nameCn"][at + len(s):]).strip()
                if not lab:
                    return None
                labels.append(lab)
            if len(set(labels)) != len(labels):
                return None
            if cols is None:
                cols = labels
            elif cols != labels:
                return None
        return {"subs": subs, "cols": cols}

    want_mtx = {g["nameCn"]: matrixable(g["items"]) for g in reg_groups}
    got = page.evaluate("""() => [...document.querySelectorAll('#lch .lchgrp')].map(g => ({
      name: (g.querySelector('.lchhead > b') || {}).innerText,
      matrix: !!g.querySelector('.lmtx'),
      cols: [...g.querySelectorAll('.lmtx thead th:not(.lmtxsub)')].map(t => t.innerText.trim()),
      rows: [...g.querySelectorAll('.lmtx tbody tr')].map(tr => (tr.querySelector('.lmtxsub') || {}).innerText.trim()),
      cells: g.querySelectorAll('.lmtx td').length,
      chks: g.querySelectorAll('input[data-chk]').length,
      tableRows: g.querySelectorAll('.ltab tbody tr').length }))""")
    bad = []
    for g, want in zip(got, [want_mtx[x["name"]] for x in got]):
        items = [gg for gg in reg_groups if gg["nameCn"] == g["name"]][0]["items"]
        if g["chks"] != len(items):
            bad.append("%s：勾选框 %d 个 / 数据 %d 条" % (g["name"], g["chks"], len(items)))
        if want and not g["matrix"]:
            bad.append("%s：数据摆得成矩阵（%d×%d）却仍是表格" % (g["name"], len(want["subs"]), len(want["cols"])))
        if not want and g["matrix"]:
            bad.append("%s：档数不齐却摆成了矩阵" % g["name"])
        if g["matrix"]:
            if g["cols"] != want["cols"] or g["rows"] != want["subs"]:
                bad.append("%s：列头/行名与数据不符 %s vs %s" % (g["name"], g["cols"], want["cols"]))
            if g["cells"] != len(want["subs"]) * len(want["cols"]):
                bad.append("%s：格数 %d ≠ %d" % (g["name"], g["cells"], len(want["subs"]) * len(want["cols"])))
        elif g["tableRows"] != len(items):
            bad.append("%s：表格 %d 行 / 数据 %d 条" % (g["name"], g["tableRows"], len(items)))
    n_mtx = len([k for k, v in want_mtx.items() if v])
    check("档数齐的组摆成矩阵（%d 组）、不齐的回落表格，两种摆法的勾选框都一条一个" % n_mtx,
          not bad and ch["chk"] == len(reg_items) and n_mtx >= 1,
          "；".join(bad[:3]) or "矩阵 %d 组 / 表格 %d 组 / 勾选框 %d 个"
          % (n_mtx, len(reg_groups) - n_mtx, ch["chk"]))
    check("矩阵的列头是从条目名里剥出来的档位，不是子分类名本身（写死列名会被客户端改字打脸）",
          all(not any(c == s for s in (want_mtx[k]["subs"] if want_mtx[k] else []))
              for k in want_mtx if want_mtx[k] for c in want_mtx[k]["cols"]),
          json.dumps({k: v["cols"] for k, v in want_mtx.items() if v}, ensure_ascii=False))
    # 几何判据：横滚容器里那条全站 `th{sticky;top:110px}` 会把头几行的表头格往下推
    # （2026-10-26 实拍抓到：列头跑到第三行、两个归属名叠一格），文本断言全绿也看不出来。
    geo = page.evaluate("""() => [...document.querySelectorAll('.lmtx')].map(t => {
        const rows = [...t.tBodies[0].rows];
        const off = rows.map(r => Math.round(r.cells[0].getBoundingClientRect().top
                                               - r.getBoundingClientRect().top));
        const hd = t.tHead.getBoundingClientRect();
        return {off: off.filter(v => v !== 0).length,
                gap: Math.round(rows[0].getBoundingClientRect().top - hd.bottom)};
      })""")
    check("矩阵每一行的归属格都跟它那一行齐平，列头紧贴第一行（sticky 参照物搞错会把表头推下去）",
          all(g["off"] == 0 and abs(g["gap"]) <= 1 for g in geo),
          json.dumps(geo, ensure_ascii=False))
    check("那条测试参与记录单列在六组之外，不混进常规分母",
          len(ch["spRows"]) == len(sp_items)
          and all(str(x["id"]) in ch["spRows"][0] for x in sp_items)
          and ch["counter"] == "%d / %d 项 · 已勾 0 项" % (len(reg_items), len(reg_items)),
          "单列 %d 条（数据特殊 %d）／计数 %s" % (len(ch["spRows"]), len(sp_items), ch["counter"]))
    page.evaluate("() => document.querySelectorAll('.lchhead')[1].click()")
    page.wait_for_timeout(500)
    ch2 = page.evaluate("""() => ({open: [...document.querySelectorAll('#lch [aria-expanded]')]
        .filter(e => e.getAttribute('aria-expanded') === 'true').length,
      chk: [...document.querySelectorAll('#lch .lchgrp')].slice(0, 2)
        .reduce((a, g) => a + [...g.querySelectorAll('input[data-chk]')].filter(e => e.offsetParent).length, 0)})""")
    check("点第二组的组头能展开，可见的勾选框跟着加上去",
          ch2["open"] == 2 and ch2["chk"] == len(g0["items"]) + len(reg_groups[1]["items"]),
          "展开 %d 组 / 可见勾选框 %d 个（前两组 %d + %d）"
          % (ch2["open"], ch2["chk"], len(g0["items"]), len(reg_groups[1]["items"])))
    # 勾一格：矩阵里只放得下一个勾，完成条件靠下面那行读数落地，所以这三处必须一起动
    page.evaluate("""() => { const g = document.querySelector('#lch .lchgrp');
      const c = g.querySelector('.lmtx input[data-chk]') || g.querySelector('input[data-chk]');
      c.click(); }""")
    page.wait_for_timeout(600)
    after = page.evaluate("""() => ({head: (document.querySelector('#lch .lchhead > .mono') || {}).innerText.replace(/\\s+/g, ' ').trim(),
      read: (document.querySelector('.lmtxread') || {}).innerText || '',
      counter: (document.querySelector('.field .mono') || {}).innerText.trim(),
      track: (document.querySelector('.lge-track') || {}).innerText.replace(/\\n/g, ' ')})""")
    first_item = reg_groups[0]["items"][0]
    check("勾一格：组头计数、上方总计数、奖励轨点数一起跟着动，并写出这一条是什么",
          "已勾 1" in after["head"] and "已勾 1 项" in after["counter"]
          and first_item["nameCn"] in after["read"]
          and (first_item.get("requirement") or "") in after["read"]
          and str(first_item.get("points") or 0) in after["track"],
          "组头 %s ／ 计数 %s ／ 读数 %s" % (after["head"], after["counter"], after["read"][:60]))
    page.evaluate("() => document.querySelector('#lch input[data-chk]').click()")
    page.wait_for_timeout(400)

    k = "25级"
    hits = [x for x in reg_items if k in ((x.get("nameCn") or "") + " " + (x.get("requirement") or "")
            + " " + (x["sub"] or "") + " " + (x["group"] or ""))]
    page.fill(".field input[type=search]", k)
    page.wait_for_timeout(900)
    cs = page.evaluate("""() => ({blocks: document.querySelectorAll('#lch .lchgrp').length,
      open: [...document.querySelectorAll('#lch [aria-expanded]')].filter(e => e.getAttribute('aria-expanded') === 'true').length,
      vis: [...document.querySelectorAll('#lch tbody tr')].filter(r => r.offsetParent).length,
      counter: (document.querySelector('.field .mono')||{}).innerText.trim(),
      hl: document.querySelectorAll('#lch mark, #lch .hl').length})""")
    check("搜索时命中的组自动展开（折叠不会把搜索结果藏起来），计数按命中走",
          cs["blocks"] >= 1 and cs["open"] == cs["blocks"] and cs["vis"] == len(hits)
          and cs["counter"] == "%d / %d 项 · 已勾 0 项" % (len(hits), len(reg_items)),
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
          back == {"open": 2, "blocks": len(reg_groups)},
          "%s（应 %d 组展开 / %d 组都在）" % (back, 2, len(reg_groups)))

    # ---- ④b 勾选 → 奖励轨：这条轨只按常规点数走，特殊那条不并进分母 ----
    first_at = min(r["at"] for r in L["rewards"])
    tr0 = page.evaluate("""() => { const txt = (e) => e ? (e.innerText || '').trim() : '';
      return [...document.querySelectorAll('.lgr-i')].map(e => ({
      nm: txt(e.querySelector('.lgr-nm')), st: txt(e.querySelector('.lgr-st')),
      got: e.classList.contains('got') })); }""")
    check("一条没勾时四档都写着还差几点（差的就是它自己那一档的点数）",
          all(not x["got"] for x in tr0) and tr0[0]["st"] == "还差 %d 点" % first_at,
          json.dumps(tr0[:2], ensure_ascii=False))
    page.evaluate("n => document.querySelectorAll('#lch input[type=checkbox]').forEach((c,i)=>{ if(i<n) c.click(); })",
                  first_at)
    page.wait_for_timeout(900)
    tr1 = page.evaluate("""() => { const txt = (e) => e ? (e.innerText || '').replace(/\\s+/g, ' ').trim() : '';
      return {track: [...document.querySelectorAll('.lgr-i')].map(e => ({
          st: txt(e.querySelector('.lgr-st')), got: e.classList.contains('got') })),
        done: txt(document.querySelector('.field .mono')),
        heads: [...document.querySelectorAll('.lchhead > .mono')].map(e => txt(e)),
        stored: localStorage.getItem('wfs.legacy.checks') }; }""")
    check("勾满第一档要的点数：那一档转成已够，后面各档改成还差几点",
          tr1["track"][0]["got"] and tr1["track"][0]["st"] == "已够"
          and not tr1["track"][1]["got"] and "还差" in tr1["track"][1]["st"],
          json.dumps(tr1["track"], ensure_ascii=False))
    check("已勾数同时出现在计数与六个组头里，且写进了本机存储",
          ("已勾 %d 项" % first_at) in tr1["done"]
          and all("已勾" in h for h in tr1["heads"]) and bool(tr1["stored"]),
          "%s ／ %s" % (tr1["done"], tr1["heads"][0]))
    page.evaluate("() => document.querySelectorAll('#lch input[type=checkbox]').forEach(c=>{ if(c.checked) c.click(); })")
    page.wait_for_timeout(700)
    settle_motion(page)   # 取消勾选会把挑战组整块收起，那是一段过渡；没等它结束就点锚点，
                          # 平滑滚动的目标还在动，落点就成了 0（这台 headless 帧饿着，1.5 秒都嫌短）

    # ---- ⑤ 锚点走站内路由（首页那批死链就是栽在裸 #id 上），点一下真的滚 ----
    anch = page.evaluate("""() => [...document.querySelectorAll('.lge-anchor a')].map(a => ({
      t: a.innerText.trim(), h: a.getAttribute('href'),
      // 锚点在哈希路由里只能靠 ?to= 传，目标那段必须真的在页面上，否则点了什么也不会发生
      id: a.getAttribute('href').split('to=')[1],
      has: !!document.getElementById(a.getAttribute('href').split('to=')[1]) }))""")
    check("页内四个锚点走站内路由地址、不写裸 #id，且目标那段真的在页面上",
          [a["t"] for a in anch] == ["传承树", "传承挑战", "进度奖励", "常见问答"]
          and all(a["h"].startswith("#/legacy?to=") and a["has"] for a in anch),
          json.dumps([{k: a[k] for k in ("t", "id", "has")} for a in anch], ensure_ascii=False))
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    anc = page.evaluate("""() => { const before = window.scrollY;
      document.querySelectorAll('.lge-anchor a')[2].click();
      // 平滑滚动是"点下去之后自己走"的，量早了就是 scrollY 还没动（这台 headless 帧被冻住，
      // 实测要 1.5 秒以上才到位）。改成等它落位，最长 6 秒——判据本身一个字没改。
      return new Promise((res) => { const t0 = performance.now();
        const t = setInterval(() => {
          const r = document.getElementById('lgr').getBoundingClientRect();
          if (window.scrollY > before || performance.now() - t0 > 6000) {
            clearInterval(t);
            res({ before: before, after: window.scrollY, top: Math.round(r.top),
                  inView: r.top < innerHeight && r.bottom > 0 }); } }, 60); }); }""")
    check("点锚点真的滚到那一段（从页顶滚到奖励轨，目标进了视口）",
          anc["before"] <= 2 and anc["after"] > anc["before"] and anc["inView"],
          json.dumps(anc, ensure_ascii=False))

    # ---- ⑤b 常见问答那四条：数必须来自数据，开放条件那句必须逐字来自数据 ----
    faq = page.evaluate("""() => { const c = document.querySelector('.lge-faq');
      if (!c) return null;
      return { dts: [...c.querySelectorAll('dt')].map(e => e.innerText.trim()),
        text: c.innerText.replace(/\\s+/g, ' '),
        h2: (c.querySelector('h2') || {}).innerText }; }""")
    R = L["meta"].get("rules") or {}
    C = L["meta"].get("counts") or {}
    check("常见问答那一段在，且正好是四条（多了就是往里塞没核实的话）",
          faq and len(faq["dts"]) == 4, json.dumps((faq or {}).get("dts"), ensure_ascii=False))
    need = [str(R.get("pointPerChallenge")), str(C.get("challengesRegular")),
            str(R.get("launchSpendingCap")), str(C.get("challengePointsRegular")),
            str(C.get("challengePointSum")), str(C.get("challenges"))]
    check("问答里每个数都等于数据里的那一个（每项点数/常规项数/角色上限/常规点数合计/条目点数合计/条目数）",
          faq and all(n in faq["text"] for n in need),
          "缺 %s" % [n for n in need if not (faq and n in faq["text"])])
    unlock = re.sub(r"\s+", " ", str(R.get("unlock") or "")).strip()
    check("开放条件那句是数据里官方那篇的说法，页面没另写一份",
          bool(unlock) and faq and unlock in faq["text"],
          "数据：%s…" % unlock[:40])
    ban = [w for w in ("洗点", "最划算", "推荐先点", "最强", "毕业") if w in (faq or {}).get("text", "")]
    check("问答里不出现没核实的结论（洗点花费、先点什么最划算这类）", not ban, "命中 %s" % ban)
    check("问答末尾仍写着'每层效果待实测'那一类交代，不装作知道效果",
          "待实测" in (faq or {}).get("text", ""))

    # ---- ⑥ 两档视口的几何与红线 ----
    body = page.evaluate("() => document.querySelector('#main').innerText")
    check("这一页不出现百分比与掉率措辞（红线）",
          not re.search(r"\d+\s*%|掉率", body), "干净")
    # ---- ⑤b 本机方案、分享链接只带方案、坏链接可恢复、存储坏了不白屏 ----
    pick(entry["id"]); tap("add", 2)
    page.evaluate("() => { const i = document.querySelector('.lge-planact input[type=text]');"
                  " i.value = '门禁测的方案'; i.dispatchEvent(new Event('input', {bubbles: true})); }")
    page.evaluate("() => [...document.querySelectorAll('.lge-planact button')]"
                  ".find(b => b.innerText.indexOf('存为本方案') >= 0).click()")
    page.wait_for_timeout(600)
    saved = page.evaluate("() => localStorage.getItem('wfs.legacy.plans')")
    page.evaluate("() => [...document.querySelectorAll('.lge-planact button')]"
                  ".find(b => b.innerText.indexOf('复制方案链接') >= 0).click()")
    page.wait_for_timeout(800)
    href = page.evaluate("() => location.href")
    code = ""
    try:
        saved_arr = json.loads(saved or "[]")
        code = saved_arr[0]["code"]
    except Exception:
        saved_arr = []
    check("方案存进本机（浏览器本地，不上传、不要登录），链接里只带方案码",
          bool(code) and saved_arr[0]["name"] == "门禁测的方案"
          and "plan=" in href and code.split(",")[0].split(":")[1].split(".")[0] in href
          and not any(str(x["id"]) in href for x in all_items),
          "本机 %s ／ 地址 %s" % ((saved or "")[:60], href[-70:]))
    mctx2 = browser.new_context(viewport={"width": 1440, "height": 1000})
    sp = mctx2.new_page(); perr = []
    sp.on("pageerror", lambda e: perr.append(str(e)[:120]))
    sp.goto(APP_BASE + "/#/legacy?t=%s&plan=%s" % (t0["id"], urllib.parse.quote(code)),
            wait_until="networkidle")
    sp.wait_for_timeout(2200)
    got = sp.evaluate("""() => ({bar: (document.querySelector('.lge-planbar .bn')||{}).innerText.replace(/\\s+/g,' ').trim(),
      filled: [...document.querySelectorAll('#ltree .lslot.filled .nm')].map(e => e.innerText.trim()),
      warn: !!document.querySelector('.lge-warn'), plans: document.querySelectorAll('.lge-planlist .plan').length})""")
    check("换一台干净浏览器打开这条链接：加点方案原样还原，且不带来任何本机方案与勾选",
          not perr and ("%d 点" % 2) in got["bar"] and got["filled"] == [entry["nameCn"]]
          and not got["warn"] and got["plans"] == 0,
          json.dumps(got, ensure_ascii=False) + " 报错 %s" % (perr[:1],))
    bad_code = "v1:%s.%d,nope.2" % (entry["id"].replace("legacy-perk-", ""), (entry.get("maxRank") or 3) + 4)
    sp.goto("about:blank")
    sp.goto(APP_BASE + "/#/legacy?t=%s&plan=%s" % (t0["id"], urllib.parse.quote(bad_code)),
            wait_until="networkidle")
    sp.wait_for_timeout(2200)
    bad = sp.evaluate("""() => { const w = document.querySelector('.lge-warn');
      return {txt: w ? w.innerText.replace(/\\s+/g,' ').trim() : '',
        hasBtn: !!(w && [...w.querySelectorAll('button')].some(b => b.innerText.indexOf('清掉') >= 0))}; }""")
    check("链接里的方案对不上时：说清哪几条对不上、按能认的还原、并给一个能清掉的出口",
          "对不上" in bad["txt"] and ("按 %d 层收" % (entry.get("maxRank") or 0)) in bad["txt"]
          and "这一版没有的格子" in bad["txt"]
          and bad["hasBtn"], bad["txt"][:120])
    sp.evaluate("() => [...document.querySelectorAll('.lge-warn button')].find(b => b.innerText.indexOf('清掉') >= 0).click()")
    sp.wait_for_timeout(900)
    cleared = sp.evaluate("""() => ({warn: !!document.querySelector('.lge-warn'),
      bar: (document.querySelector('.lge-planbar .bn')||{}).innerText.replace(/\\s+/g,' ').trim()})""")
    check("点「清掉这份」回到空白方案（不是停在半份看不懂的点法上）",
          not cleared["warn"] and "已投 0 点" in cleared["bar"], json.dumps(cleared, ensure_ascii=False))
    sp.add_init_script("localStorage.setItem('wfs.legacy.plans','{坏掉的');"
                       "localStorage.setItem('wfs.legacy.checks','[\"99999999\",\"%s\"');" % all_items[0]["id"])
    sp.goto(APP_BASE + "/#/legacy", wait_until="networkidle")
    settle_motion(sp)   # 换 hash 走的是路由过渡，等它结束再读
    sp.wait_for_timeout(2200)
    broke = sp.evaluate("""() => ({bar: (document.querySelector('.lge-planbar .bn')||{}).innerText.replace(/\\s+/g,' ').trim(),
      h2: (document.querySelector('#main h1')||{}).innerText.trim(),
      done: (document.querySelector('.field .mono')||{}).innerText.trim()})""")
    check("本机存储被写坏（不是合法 JSON）时页面照常打开、回到 0 点，不白屏也不报错",
          perr == [] and broke["h2"].startswith("传承") and "已投 0 点" in broke["bar"],
          json.dumps(broke, ensure_ascii=False) + " 报错 %s" % (perr[:2],))
    mctx2.close()
    page.evaluate("() => { const b=[...document.querySelectorAll('.lge-planact button')]"
                  ".find(x=>x.innerText.indexOf('全部清空')>=0); if (b) b.click(); }")
    page.wait_for_timeout(400)

    snap(page, path=os.path.join(SHOT_DIR, "app-legacy.png"), full_page=True)
    ctx.close()
    mctx = browser.new_context(viewport={"width": 375, "height": 812})
    mp = mctx.new_page()
    mp.goto(APP_BASE + "/#/legacy", wait_until="networkidle")
    settle_motion(mp)   # 换 hash 走的是路由过渡，等它结束再读
    mp.wait_for_timeout(2200)
    # 加减按钮只在选中某个格子之后才出现在详情栏里（没选时那栏是这一棵树的读数），
    # 所以 375 上先真点一个格子，再量这两个按钮在不在、够不够大
    mp.evaluate("() => { const b = document.querySelector('#ltree BUTTON.lslot'); if (b) b.click(); }")
    mp.wait_for_timeout(700)
    mm = mp.evaluate("""() => ({over: document.documentElement.scrollWidth - window.innerWidth,
      innerW: window.innerWidth,
      cells: getComputedStyle(document.querySelector('.lge-cells')).gridTemplateColumns.split(' ').length,
      wrap: getComputedStyle(document.querySelector('.ltreewrap')).gridTemplateColumns.split(' ').length,
      act: document.querySelectorAll('.lge-act button').length,
      plans: document.querySelectorAll('.lge-planact button').length,
      sp: document.querySelectorAll('.lge-special tbody tr').length,
      small: [...document.querySelectorAll('.lge-tab, .lchhead, #ltree .lslot, .lge-jump, .lchk, .lge-act button, .lge-planact button')]
        .filter(e => { const r = e.getBoundingClientRect();
          return r.width > 0 && Math.min(r.width, r.height) < 44; })
        .map(e => (e.className || e.tagName) + ':' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height)),
      cut: [...document.querySelectorAll('#ltree .lslot')].some(e => e.getBoundingClientRect().right > window.innerWidth + 1)})""")
    # 列数从数据里读，不写死：页面本来就是 repeat(var(--cols))，2026-10-23 客户端把
    # 传承树排成 5×5（第 4 排与第 4 列整条空着），页面收掉空行空列、写死 4 的那一版把旧事实当成了设计常量。
    want_cols = max(len(vis(t)[1]) for t in L["trees"])
    check("传承页 375：布局视口没被顶宽（innerWidth 仍是 375）、整页不横溢、格子不被切"
          "——树按数据算出的列数摆（现 %d 列）、详情叠到下面" % want_cols,
          mm["over"] == 0 and mm["innerW"] == 375 and mm["cells"] == want_cols
          and mm["wrap"] == 1 and not mm["cut"],
          json.dumps({k: mm[k] for k in ("over", "innerW", "cells", "wrap", "cut")}, ensure_ascii=False))
    check("传承页 375：胶囊、组头、专长格、勾选框、加减按钮、方案条按钮都够 44px 点击区",
          not mm["small"], "%d 个不够 44px：%s" % (len(mm["small"]), mm["small"][:6]))
    check("375 上规划器的两个按钮与那条单列记录都在（窄屏不是把功能藏掉）",
          mm["act"] == 2 and mm["plans"] >= 3 and mm["sp"] >= 1,
          "加减 %d 个 / 方案条 %d 个 / 单列 %d 条" % (mm["act"], mm["plans"], mm["sp"]))
    snap(mp, path=os.path.join(SHOT_DIR, "app-legacy-m.png"), full_page=True)
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    # ---- 「两家怎么说」对照表（2026-10-23 第二份名单接进来）----
    # 这张表最容易悄悄坏掉的三件事：① 两枚戒指/两个饰品同名，按部位做键会串格（数据侧
    # 已经踩过一次：1237 次比对只剩 1085 格）；② 判定与数据算出来的不一致（对错了格）；
    # ③ 把另一家那件的名字写成插件里的写法，而不是回本站名录查。三条都钉住。
    CMP_CN = {True: u"一致", False: u"分歧"}
    amap = {(x["slot"], x["cell"]): x for x in w["alt"]["alliance"]}
    # 名字读 .nm 那一节，不读整格 innerText：图标格子（IconCell）在图加载成功时也会把
    # 名字首字留在 DOM 里当兜底，整格读出来是"野 野人铁盔"，比名字就多一个字（2026-10-23 实拍）。
    cmp_rows = page.evaluate("""() => [...document.querySelectorAll('#pzcmp tbody tr')].map(r => ({
      slot: (r.children[0].innerText || '').replace(/\\s+/g, ' ').trim(),
      ours: ((r.children[1].querySelector('.nm') || {}).textContent || '').trim(),
      theirs: ((r.children[2].querySelector('.nm') || {}).textContent || '').trim(),
      theirsText: (r.children[2].innerText || '').replace(/\\s+/g, ' ').trim(),
      tag: (r.children[3].innerText || '').trim() }))""")
    base_labels = set(x["slot"].split(" · ")[0] for x in cmp_rows)
    check("对照表每一格纸娃娃都有一行（两枚戒指与两个饰品各占一行，不按部位合并）",
          len(cmp_rows) == len(w["doll"]["alliance"])
          and len(base_labels) < len(cmp_rows),
          "%d 行 / %d 个部位名" % (len(cmp_rows), len(base_labels)))
    cbad = []
    for c, x in zip(w["doll"]["alliance"], cmp_rows):
        a = amap.get((c["slot"], c["cell"]))
        label = c["slot"] + ("" if c["cell"] < 2 else " · %d" % c["cell"])
        if x["slot"] != label:
            cbad.append([label, x["slot"]]); continue
        if x["ours"] != by_id[c["item"]]["name"]:
            cbad.append([label, u"本站列不是名录里的写法", x["ours"]])
        want_tag = u"没列" if a is None else CMP_CN[a["same"]]
        if x["tag"] != want_tag:
            cbad.append([label, x["tag"], want_tag])
        elif a is not None and a["same"]:
            if x["theirs"] != by_id[c["item"]]["name"]:
                cbad.append([label, u"一致却没显示同一件", x["theirs"]])
        elif a is not None:
            tn = by_id.get(a["item"], {}).get("name")
            if tn and x["theirs"] != tn:
                cbad.append([label, x["theirs"], tn])
            if not tn and (u"#%d" % a["item"]) not in x["theirsText"]:
                cbad.append([label, u"名录里没有却没标编号", x["theirsText"]])
    check("对照表逐行等于按数据算出来的结果（部位、两栏名字、判定）",
          not cbad, "对不上：%s" % cbad[:3] if cbad
          else "%d 行全对（一致 %d / 分歧 %d / 没列 %d）" % (
              len(cmp_rows),
              sum(1 for x in cmp_rows if x["tag"] == u"一致"),
              sum(1 for x in cmp_rows if x["tag"] == u"分歧"),
              sum(1 for x in cmp_rows if x["tag"] == u"没列")))
    cmp_note = page.evaluate("""() => { const c = document.querySelector('#pzcmp').closest('.card');
      const n = c.querySelector('.note'); return (n ? n.innerText : '').replace(/\\s+/g, ' '); }""")
    # 日期从 bis.json 现读再比，不抄字面量：上一版这里写死 "2026-10-23"，
    # 换一次抓取日期就会红一次，而红的原因是"断言抄死了旧事实"，不是页面错。
    bis_meta = json.load(open(os.path.join(SRC, "data", "bis.json"), encoding="utf-8"))["meta"]
    alt_at = (bis_meta.get("alt") or {}).get("fetched") or ""
    main_at = bis_meta.get("scrapedAt") or ""
    check("对照表下面写清了来源、抓取日期与不裁决的口径（红线：两源分歧两个都留）",
          u"XR_DungeonGuide" in cmp_note and bool(alt_at) and alt_at in cmp_note
          and u"不裁决" in cmp_note and u"仍以主源为准" in cmp_note
          and u"L1" in cmp_note and u"升档" in cmp_note,
          "插件那份 %s ／ %s" % (alt_at, cmp_note[:52]))
    check("配装页把主源的核对日也摆在玩家看得见的地方（上一版只显插件那份，主源哪天抓的没人知道）",
          bool(main_at) and page.evaluate("(a) => (document.body.innerText || '').indexOf(a) >= 0", main_at),
          "主源核对日 %s" % main_at)
    cmp_stat = page.evaluate("""() => (document.querySelector('#pzcmp').closest('.card')
      .querySelector('.bhead .bn') || {}).innerText || ''""")
    dl_a = w["doll"]["alliance"]
    want_stat = [sum(1 for c in dl_a if amap.get((c["slot"], c["cell"])) and amap[(c["slot"], c["cell"])]["same"]),
                 sum(1 for c in dl_a if amap.get((c["slot"], c["cell"])) and not amap[(c["slot"], c["cell"])]["same"]),
                 sum(1 for c in dl_a if (c["slot"], c["cell"]) not in amap)]
    got_stat = [int(x) for x in re.findall(r"\d+", cmp_stat)]
    check("表头那三个数是这一套真算出来的（一致 / 分歧 / 没列）",
          got_stat[:3] == want_stat, "界面 %s ／ 数据 %s" % (got_stat[:3], want_stat))
    page.locator("#pzcmp").scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    snap(page, path=os.path.join(SHOT_DIR, "app-bis-compare.png"))
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
        sum: [...document.querySelectorAll('.pzsum-i span')].filter(x => x.offsetParent !== null).map(x => x.innerText.replace(/\\s+/g,' ').trim()) }; }""")
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
    # 2026-10-22 改：这一排芯片页面用的是 v-show，值为 0 的一格只是 CSS 隐藏、**节点还在 DOM 里**，
    # 直接 innerText 全读会多出一个空的「精神」。玩家看不见它，所以页面是对的、判据要按可见性过滤。
    check("属性合计那排等于门禁独立解析的结果（纯加法，不含基础值与附魔）",
          ic["sum"] == want_sum, "界面 %s ／ 数据 %s" % (ic["sum"], want_sum))
    snap(page, path=os.path.join(SHOT_DIR, "app-bis.png"))
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
                         ".filter(x => x.offsetParent !== null)"
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
    snap(page, path=os.path.join(SHOT_DIR, "app-bis-hunter-armor.png"))
    snap(page, path=os.path.join(SHOT_DIR, "app-bis-hunter-armor-full.png"), full_page=True)
    # 另一家提了、本站名录里没有的那一件（全库就 1 件：#9395，在德鲁伊「恢复」的手部）：
    # 界面上必须给编号 + 一句"名录里没有"，不许拿插件的写法冒充我们的名字。
    di = page.evaluate("""() => [...document.querySelectorAll('.pzrail .pztab')]
      .findIndex(b => b.innerText.indexOf('德鲁伊') >= 0)""")
    page.click(".pzrail .pztab >> nth=%d" % di)
    page.wait_for_timeout(1200)
    mi = page.evaluate("""() => [...document.querySelectorAll('.pz-mode .pick')]
      .findIndex(b => b.innerText.replace(/\\s+/g,'').indexOf('恢复') >= 0)""")
    page.click(".pz-mode .pick >> nth=%d" % mi)
    page.wait_for_timeout(1200)
    miss_row = page.evaluate("""() => [...document.querySelectorAll('#pzcmp tbody tr')]
      .map(r => (r.innerText || '').replace(/\\s+/g, ' ')).filter(x => x.indexOf('9395') >= 0)""")
    drest = [s for s in sets if s["id"] == "druid-restoration"][0]
    hand = [x for x in drest["alt"]["alliance"] if x["slot"] == u"手"][0]
    check("另一家提了、本站名录里没有的那件：显示编号并写明没有，不替它编名字",
          len(miss_row) == 1 and hand["item"] == 9395
          and u"#9395" in miss_row[0] and u"本站名录里没有" in miss_row[0]
          and u"猛虎" not in miss_row[0],
          miss_row[0][:70] if miss_row else "没找到这一行")
    snap(page, path=os.path.join(SHOT_DIR, "app-bis-compare-missing.png"))
    ctx.close()

    # ---- 3D 那一层（2026-10-26 站主"先给我看 3D 效果"）----
    # 判据全部落在像素上：canvas 存在、分包到位、按钮 aria-pressed 翻了，
    # 都不等于"画出来了"——第一版就是模型被整个藏掉，DOM 一切正常、屏幕上只有原画。
    art_data = json.load(open(os.path.join(SRC, "data", "art.json"), encoding="utf-8"))
    art_bm = art_data.get("bisModels") or {}
    hunter_real = [m for m in (art_data.get("bisRealModels") or {}).get("items", [])
                   if m.get("setId") == "hunter" and m.get("placementVerdict") == "PASS"]
    models = art_bm.get("items") or []
    has_model = bool(models) and art_bm.get("origin") == "self-generated"
    dctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    dp = dctx.new_page()
    dreq = []
    dp.on("request", lambda r: dreq.append(r.url))
    derr = []
    dp.on("pageerror", lambda e: derr.append(str(e)[:120]))
    dp.goto(APP_BASE + "/#/bis", wait_until="networkidle")
    settle_motion(dp)   # 换 hash 走的是路由过渡，等它结束再读
    dp.wait_for_timeout(2200)
    dbtn = dp.query_selector("button.pz-3dbtn")
    check("台账里有自产模型才出现这个按钮；没有模型就不该给玩家点（不猜路径）",
          (dbtn is not None) == has_model,
          "台账 %d 个（origin=%s）／按钮 %s" % (len(models), art_bm.get("origin"), bool(dbtn)))
    pre = [u for u in dreq if "three" in u or "GLTFLoader" in u or u.endswith(".glb")]
    check("不点按钮时 three.js 与模型一个字节都不下载（首屏不为 3D 买单）", not pre,
          "点之前 3D 相关请求 %d 条" % len(pre))
    if has_model and dbtn:
        # 分包解析与 WebGL 初始化在软件光栅环境里耗时浮动；等模型请求本身，
        # 不用固定 5 秒把慢机器误报成“没有加载模型”。
        with dp.expect_request(lambda r: urllib.parse.urlsplit(r.url).path.endswith(".glb"), timeout=20000):
            dbtn.click()
        dp.wait_for_function("() => !!document.querySelector('.pzc-gl') && !document.querySelector('.pzc-glhint')", timeout=20000)
        post = [u.split("/")[-1] for u in dreq if "three" in u or "GLTFLoader" in u or u.endswith(".glb")]
        check("点下去才加载渲染器与模型文件", any("three" in x for x in post)
              and any(x.endswith(".glb") for x in post), ", ".join(sorted(set(post))[:4]))
        gl = dp.evaluate("""() => { const c = document.querySelector('canvas.pzc-gl');
          const note = [...document.querySelectorAll('.pz-3dnote')].map(e => e.innerText).join(' ');
          return { eng: c ? (c.getAttribute('data-engine') || '') : '',
                   w: c ? c.width : 0, h: c ? c.height : 0,
                   pressed: (document.querySelector('button.pz-3dbtn') || {}).getAttribute
                     ? document.querySelector('button.pz-3dbtn').getAttribute('aria-pressed') : '',
                   honest: note.indexOf('占位模型') >= 0 && note.indexOf('不是游戏里的样子') >= 0 }; }""")
        check("画布真的建起来了（three.js 会把自己标在 canvas 上）",
              bool(gl["eng"]) and gl["w"] > 200 and gl["pressed"] == "true",
              "%s ／ %sx%s" % (gl["eng"], gl["w"], gl["h"]))
        check("界面上写死这句：这是本站自拼的占位模型、不是游戏里的样子（红线：不冒充）",
              gl["honest"], "见 .pz-3dnote")
        # A/B 两帧：开 3D 与退回图片，同一块区域必须明显不同
        box = dp.query_selector(".pzart")
        shot_on = box.screenshot()
        dp.query_selector("button.pz-3dbtn").click()
        dp.wait_for_timeout(700)
        shot_off = box.screenshot()
        dp.query_selector("button.pz-3dbtn").click()
        dp.wait_for_function("() => !!document.querySelector('.pzc-gl') && !document.querySelector('.pzc-glhint')", timeout=20000)
        try:
            from PIL import Image
            import io

            def crop_diff(a, bb):
                ia = Image.open(io.BytesIO(a)).convert("RGB")
                ib = Image.open(io.BytesIO(bb)).convert("RGB")
                w, h = ia.size
                # 只比中间那块：右上角是按钮、上面那条是说明文字，两帧本来就会变
                x0, x1 = int(w * 0.10), int(w * 0.95)
                y0, y1 = int(h * 0.42), int(h * 0.92)
                ca = ia.crop((x0, y0, x1, y1))
                cb = ib.crop((x0, y0, x1, y1))
                pa, pb = ca.getdata(), cb.getdata()
                n = 0
                for (r1, g1, b1), (r2, g2, b2) in zip(pa, pb):
                    if abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2) > 40:
                        n += 1
                return n, ca.size[0] * ca.size[1]

            diff, tot = crop_diff(shot_on, shot_off)
            ratio = 100.0 * diff / tot
            check("开 3D 与退回图片两帧对比：中间那块真的换了内容（模型没画出来时这条会接近 0）",
                  ratio >= 8.0, "差异 %.1f%%（判据 ≥8%%，比的是 %d 个像素）" % (ratio, tot))
        except ImportError:
            check("两帧对比跑不了：这台机器没有 PIL", False, "装上 Pillow 再跑这条门禁")

        # 模型要跟着数据走：换阵营 → 这一套的件不一样 → 染出来的样子也不一样
        shot_all = box.screenshot()
        old_canvas = dp.query_selector('canvas.pzc-gl')
        dp.evaluate("() => [...document.querySelectorAll('.pz-fac .pick')]"
                    ".find(b => /部落/.test(b.innerText)).click()")
        dp.wait_for_function("old => document.querySelector('canvas.pzc-gl') !== old",
                             arg=old_canvas, timeout=20000)
        dp.wait_for_function("() => !!document.querySelector('.pzc-gl') && !document.querySelector('.pzc-glhint')", timeout=20000)
        shot_horde = box.screenshot()
        try:
            from PIL import Image
            import io

            def diff_ratio(a, bb):
                ia = Image.open(io.BytesIO(a)).convert("RGB")
                ib = Image.open(io.BytesIO(bb)).convert("RGB")
                w, h = ia.size
                ca = ia.crop((int(w * .10), int(h * .42), int(w * .95), int(h * .92)))
                cb = ib.crop((int(w * .10), int(h * .42), int(w * .95), int(h * .92)))
                n = sum(1 for (r1, g1, b1), (r2, g2, b2) in zip(ca.getdata(), cb.getdata())
                        if abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2) > 40)
                return 100.0 * n / (ca.size[0] * ca.size[1])

            r2 = diff_ratio(shot_all, shot_horde)
            if len(hunter_real) == 2:
                check("两阵营真实 3D 模型跟着切换",
                      r2 >= 0.8, "联盟/部落两帧差异 %.1f%%（判据 ≥0.8%%）" % r2)
            else:
                # 占位只有一份几何，按品质上色；两阵营物品虽不同，品质相同
                # 时画面可以完全一样。验重新挂载和诚实提示，不假造像素差。
                note = dp.locator('.pz-3dnote').all_inner_texts()
                check("未验收真实模型时换阵营仍显示占位并重新挂载画布",
                      bool(note) and any("不是游戏里的样子" in x for x in note)
                      and dp.query_selector('canvas.pzc-gl') is not old_canvas,
                      "真实模型 %d 份／像素差 %.1f%%" % (len(hunter_real), r2))
        except ImportError:
            pass
        dp.wait_for_timeout(600)
        snap(dp, path=os.path.join(SHOT_DIR, "app-bis-3d.png"),
                      clip=dict((lambda b: ({"x": b["x"] - 20, "y": b["y"] - 20,
                                             "width": b["width"] + 40, "height": b["height"] + 40}))(
                          dp.query_selector(".pzmid").bounding_box())))
        check("开 3D 之后这一页没有脚本报错", not derr, "; ".join(derr[:2]) or "干净")
    dctx.close()

    ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    mp = ctx.new_page()
    mp.goto(APP_BASE + "/#/bis", wait_until="networkidle")
    settle_motion(mp)   # 换 hash 走的是路由过渡，等它结束再读
    mp.wait_for_timeout(2000)
    mm = mp.evaluate("""() => ({over: document.documentElement.scrollWidth - innerWidth,
      small: [...document.querySelectorAll('.pzcell, .pz-mode .pick, .pz-cls .pick, .pz-3dbtn')]
        .filter(b => b.getBoundingClientRect().height < 44).length })""")
    check("配装页 375 不横向溢出", mm["over"] <= 1, json.dumps(mm))
    check("配装页 375 点击目标不低于 44px", mm["small"] == 0, "%d 个偏小" % mm["small"])
    # 对照表在 375 上必须竖起来：其余表横滚是"列多、少看几列还能读"，这张不行——
    # 本站用的与另一家的分在两栏，横滚就永远看不到同一屏，表也就白做。
    cmpm = mp.evaluate("""() => { const t = document.querySelector('#pzcmp');
      if (!t) return { missing: true };
      const wrap = t.closest('.boardwrap'), rows = [...t.querySelectorAll('tbody tr')];
      return { scroll: wrap.scrollWidth - wrap.clientWidth,
               page: document.documentElement.scrollWidth - innerWidth,
               n: rows.length,
               both: rows.filter(r => (r.children[1].innerText || '').trim()
                 && (r.children[2].innerText || '').trim()
                 && r.children[1].offsetParent && r.children[2].offsetParent).length,
               lbl: getComputedStyle(rows[0].children[1], '::before').content }; }""")
    check("配装页 375 上对照表不横滚、每行两栏都在同一屏",
          not cmpm.get("missing") and cmpm["scroll"] == 0 and cmpm["page"] <= 1
          and cmpm["both"] == cmpm["n"] and cmpm["n"] > 0,
          json.dumps(cmpm, ensure_ascii=False))
    check("375 上对照表把列名补在每行前面（表头隐藏了，不写清就不知道哪栏是谁）",
          u"本站用的" in (cmpm.get("lbl") or ""), cmpm.get("lbl"))
    mp.locator("#pzcmp").scroll_into_view_if_needed()
    mp.wait_for_timeout(300)
    snap(mp, path=os.path.join(SHOT_DIR, "app-bis-compare-m.png"))
    snap(mp, path=os.path.join(SHOT_DIR, "app-bis-m.png"))
    # 375 上补一张猎人那套的合计行（这次修的就是这一排）
    hmi = mp.evaluate("""() => [...document.querySelectorAll('.pzrail .pztab')]
      .findIndex(b => b.innerText.indexOf('猎人') >= 0)""")
    mp.click(".pzrail .pztab >> nth=%d" % hmi)
    mp.wait_for_timeout(1500)
    mp.locator(".pzsum").scroll_into_view_if_needed()
    mp.wait_for_timeout(300)
    snap(mp, path=os.path.join(SHOT_DIR, "app-bis-hunter-armor-m.png"))
    ctx.close()


def test_classes_sticky(browser, base):
    """职业页「技能变化」那个滚动框里的吸附关系（2026-10-23 站主实拍：表头浮在框中间、把行推走）。
       根因是参照物：position:sticky 认的是**最近的滚动祖先**（这里是 .chgs，max-height:72vh、
       自己滚动），不是视口。原来表头照抄全站顶栏高度 var(--hd-h)（实测 110px），
       于是它在滚动框里往下掉 110px——分组条吸在框顶、表头悬在下面一米处。
       钉三件事：① 分组条吸在滚动框上沿；② 表头紧贴分组条下沿（偏移等于分组条高，不是 --hd-h）；
       ③ 表头下沿往下 2px 那点命中测试打到的是数据行——遮挡只能靠命中测试判，
         而且要先滚进视口，不然量到的是没吸住时的位置。
       375 是另一套口径：窄屏下 .boardwrap 变成横向滚动容器，sticky 的参照物会跟着换，
       所以那一边**故意不吸**（board.css 与 app.css 各有一条把它关掉，留着会画出一条空带）。
       这里把"移动端不吸"也钉住，谁要重新打开得先说清这条教训。"""
    print("\n[6i] 职业页技能变化表头吸附")
    import json
    if not app_up(browser):
        return
    JS = """() => { const box = document.querySelector('.chgs');
      if (!box) return { missing: true };
      box.scrollTop = 220;
      const bb = box.getBoundingClientRect();
      const grp = box.querySelector('.lgrp');
      const th = box.querySelector('thead th');
      const gb = grp.getBoundingClientRect(), tb = th.getBoundingClientRect();
      const under = document.elementFromPoint(Math.round(tb.left + 20), Math.round(tb.bottom + 2));
      const over = document.elementFromPoint(Math.round(tb.left + 20), Math.round(tb.top + tb.height / 2));
      return { scrollTop: box.scrollTop,
               scrollable: box.scrollHeight > box.clientHeight + 40,
               pageOver: document.documentElement.scrollWidth - innerWidth,
               boxOver: box.scrollWidth - box.clientWidth,
               grpDy: Math.round(gb.top - bb.top), grpH: Math.round(gb.height),
               grpPos: getComputedStyle(grp).position,
               thDy: Math.round(tb.top - bb.top), thPos: getComputedStyle(th).position,
               thTopCss: getComputedStyle(th).top, hdH: getComputedStyle(box).getPropertyValue('--hd-h').trim(),
               underRow: !!(under && under.closest('tbody tr') && !under.closest('thead')),
               overTh: !!(over && over.closest('thead')),
               rows: box.querySelectorAll('tbody tr').length }; }"""
    for tag, vp, mob in (("桌面", {"width": 1440, "height": 1000}, False),
                         ("375", {"width": 375, "height": 812}, True)):
        ctx = browser.new_context(viewport=vp, is_mobile=mob, has_touch=mob)
        page = ctx.new_page()
        page.goto(APP_BASE + "/#/classes", wait_until="networkidle")
        settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
        page.wait_for_timeout(2200)
        r = page.evaluate(JS)
        check("%s 技能变化是一个自己滚的框（吸附才有意义）" % tag,
              not r.get("missing") and r["scrollable"] and r["scrollTop"] >= 200,
              json.dumps({k: r.get(k) for k in ("scrollable", "scrollTop", "rows")}, ensure_ascii=False))
        if mob:
            check("375 分组条与表头都故意不吸（那一屏 .boardwrap 是横滚容器，吸了会画空带）",
                  r["grpPos"] == "static" and r["thPos"] == "static",
                  "分组条 %s / 表头 %s" % (r["grpPos"], r["thPos"]))
            check("375 整页不横溢（框内横滚是允许的，页面不能）",
                  r["pageOver"] <= 1 and r["boxOver"] >= 0,
                  json.dumps({k: r[k] for k in ("pageOver", "boxOver")}))
        else:
            check("%s 分组条吸在滚动框上沿（不是吸在视口上）" % tag,
                  r["grpPos"] == "sticky" and abs(r["grpDy"]) <= 2,
                  "position %s / 距框顶 %spx" % (r["grpPos"], r["grpDy"]))
            check("%s 表头紧贴分组条下面（偏移等于分组条高，不是顶栏那个高 %s）"
                  % (tag, r["hdH"] or "?"),
                  r["thPos"] == "sticky" and abs(r["thDy"] - r["grpH"]) <= 2
                  and r["thDy"] < 60,
                  "表头距框顶 %spx / 分组条高 %spx / top:%s" % (r["thDy"], r["grpH"], r["thTopCss"]))
            check("%s 表头没有盖住数据行：下沿那点打到的是行，表头那一点打到的还是表头" % tag,
                  r["underRow"] and r["overTh"],
                  json.dumps({k: r[k] for k in ("underRow", "overTh")}))
        page.locator(".chgs").scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        snap(page, path=os.path.join(SHOT_DIR, "app-classes-chgs-sticky%s.png"
                                          % ("-m" if mob else "")))
        ctx.close()




def test_mobile(browser, base):
    print("\n[9] 375px 移动端")
    ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m, e=errors: e.append(m.text[:100]) if m.type == "error" else None)
    open_talent(page, base)
    visible = page.evaluate("() => [...document.querySelectorAll('.tree')].filter(t => !t.classList.contains('hide')).length")
    check("移动端只展开当前一系", visible == 1, "可见树 %d" % visible, soft=MOBILE_SOFT)
    click(page, DEMO_A00)
    page.wait_for_timeout(200)
    click(page, DEMO_A00)
    page.wait_for_timeout(250)
    check("移动端加点可用", ranks(page, DEMO_A00)["ranks"] == 2,
          "a-0-0=%s" % ranks(page, DEMO_A00)["ranks"], soft=MOBILE_SOFT)
    page.evaluate("() => document.getElementById('mode').click()")
    click(page, DEMO_A00)
    page.wait_for_timeout(250)
    check("移动端用减点按钮可减点（没有右键也能完成）", ranks(page, DEMO_A00)["ranks"] == 1,
          "a-0-0=%s" % ranks(page, DEMO_A00)["ranks"], soft=MOBILE_SOFT)
    snap(page, path=os.path.join(SHOT_DIR, "talent-mobile-375.png"))
    check("移动端无控制台报错", not errors, "; ".join(errors[:2]))
    ctx.close()





















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
        # url 是变量传进来的，批量补等待那一轮按字面 "#/" 找没找到这一处：
        # 不等过渡结束就读正文，读到的是上一页，溯源页那一段就被报成"没有"。
        settle_motion(page)
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
    # 种族×职业矩阵的首列也在 .scrollx 里：全站 `th{sticky;top:110px}` 曾把头两行
    # （兽人/亡灵）往下推到牛头人那一行（2026-10-26 实测），文本断言看不出，只能量。
    mgeo = page.evaluate("""() => { const t = document.querySelector('table.mtx');
        if (!t) return null;
        return [...t.tBodies[0].rows].map(rw => Math.round(
          rw.cells[0].getBoundingClientRect().top - rw.getBoundingClientRect().top))
          .filter(v => v !== 0).length; }""")
    check("种族×职业矩阵每一行的首列都跟它那一行齐平（横滚容器里纵向 sticky 会把头几行推下去）",
          mgeo == 0, "错位行数 %s" % mgeo)
    snap(page, path=os.path.join(SHOT_DIR, "app-raceicon-skyborne.png"))
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
    settle_motion(mp)   # 换 hash 走的是路由过渡，等它结束再读
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
    snap(mp, path=os.path.join(SHOT_DIR, "app-raceicon-skyborne-m.png"))
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    snap(page, path=os.path.join(SHOT_DIR, "w2-updates-chips.png"))

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
    snap(page, path=os.path.join(SHOT_DIR, "w2-updates-hunter-added.png"))

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
    snap(page, path=os.path.join(SHOT_DIR, "w2-updates-empty.png"))

    # 375 同一件事：格子换行排、点了同样对得上（以前只在桌面验，手机上溢出没人管）
    mctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    mp = mctx.new_page()
    mp.goto(APP_BASE + "/#/updates", wait_until="networkidle")
    settle_motion(mp)   # 换 hash 走的是路由过渡，等它结束再读
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
    snap(mp, path=os.path.join(SHOT_DIR, "w2-updates-chips-m.png"))
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1600)
    # 读标签要先把「新」角标剔掉：角标是 <i class="nb"> 塞在 <a> 里的文字，
    # 不剔的话本站更新一打上"配装"标签，这条就会拿"配装新"去比"配装"而红
    # （旧站那条早就剔了，新站这条是我漏的——2026-10-17 全量门禁抓到）
    app_subs = page.evaluate("() => [...document.querySelectorAll('nav.main a.nl')].map(a => {"
                             "const c = a.cloneNode(true);"
                             "c.querySelectorAll('.nb').forEach(n => n.remove());"
                             "return c.textContent.trim(); })")
    APP_NAV = ["首页", "计算器", "职业", "玩法问答", "传承", "宠物", "总览",
               "区域与稀有", "副本", "团本", "配方", "配装", "排行", "宏命令"]
    check("新站导航二级就是这 %d 格，顺序与名字不许漂" % len(APP_NAV), app_subs == APP_NAV,
          "%d 项：%s" % (len(app_subs), app_subs))
    check("世界与工具两组按收窄后的口径（3 格 / 2 格；2026-10-30 工具组加了宏命令）",
          page.evaluate("""() => { const g = [...document.querySelectorAll('nav.main .ngrp')];
            const of = (n) => { const b = g.find(x => (x.querySelector('.ngt')||{}).textContent === n);
              return b ? b.querySelectorAll('a.nl').length : -1; };
            return [of('世界'), of('工具')]; }""") == [3, 2])
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    check("那几格带的数是 scale.json 算出来的，不是手抄",
          all(str(sc2.get(k)) in got.get("#/" + k, "") for k in ("items", "achievements")),
          " / ".join(counts) + "（数据 items %s、achievements %s）"
          % (sc2["items"], sc2["achievements"]))
    # ---- 2026-10-28 站主实拍：宠物页上线那天他在首页与线上都没找到它 ----
    # 根因不是页面坏了（直达 #/pets 一直是好的），是它只有底部那行小文字链、导航没格子。
    # 这两条钉的是"入口在不在该在的地方"，构建通过发现不了这一类毛病。
    nav_pets = page.evaluate("() => [...document.querySelectorAll('nav.main a.nl')]"
                             ".some(a => (a.getAttribute('href') || '') === '#/pets')")
    card_pets = page.evaluate("() => [...document.querySelectorAll('#main a.mod')]"
                              ".some(a => (a.getAttribute('href') || '') === '#/pets')")
    check("宠物页在顶部导航与首页板块卡各有一个入口", nav_pets and card_pets,
          "导航 %s ／ 首页卡 %s" % (nav_pets, card_pets))
    # 2026-10-29 站主：「首页的最新动态 怎么又加回来了，不要最新动态这个卡片」→ 这张卡撤掉。
    # 这条判据跟着反向钉：首页不许再出现这张卡，但动态页的入口必须还在
    # （hero 那颗「看这一版改了什么」+ 板块轨那张「自经典旧世以来改了什么」）——
    # 撤一张卡不能顺手把那一页变成孤儿。
    upd_card = page.evaluate("""() => [...document.querySelectorAll('#main h2')]
        .some(e => e.textContent.trim() === '最新动态')""")
    upd_entry = page.evaluate("""() => [...document.querySelectorAll('#main a[href]')]
        .filter(a => (a.getAttribute('href') || '').indexOf('/updates') >= 0).length""")
    check(u"首页没有「最新动态」这张卡（站主 2026-10-29 撤掉，别再顺手加回来）",
          not upd_card, "页面上还有那张卡" if upd_card else "已撤")
    check("撤卡之后动态页在首页仍有入口（不是把那一页藏起来）", upd_entry >= 2,
          "指向 #/updates 的入口 %d 处" % upd_entry)
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
    # 已知偶发：这一条在同一份产物上会自己红（实测 site-check 上下文 3/13 红，
    # 单独照 /#/world → /#/ 这条路重跑 8 次红 2 次、再重跑 6 次全绿），
    # 红出来的值是"当前项底色透明、字色是默认灰"——`.on` 这个类明明在元素上。
    # 试过"等连续两次读数一致再量"，没治好，已撤回。它不是这一轮引入的，要单开一修。
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
    settle_motion(p375)   # 换 hash 走的是路由过渡，等它结束再读
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
    snap(p375, path=os.path.join(SHOT_DIR, "app-home-375.png"))
    ctx375.close()
    snap(page, path=os.path.join(SHOT_DIR, "app-home-1440.png"), clip=None, full_page=False)

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
        settle_motion(p2)   # 换 hash 走的是路由过渡，等它结束再读
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
        snap(p2, path=os.path.join(SHOT_DIR, "app-races-heads-%s.png" % vp))
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1200)
    snap(page, path=os.path.join(SHOT_DIR, "app-nav-narrow.png"))
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
        snap(page, path=os.path.join(SHOT_DIR, "app-%s.png" % key))
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
            # 这条原来写死 13（"12 张分组卡 + 1 张大卡"）。2026-10-28 站主要求首页加一张宠物卡，
            # 那个字面量当场就红了——它抄的是"那天有几张卡"，不是"卡该不该都渲染出来"。
            # 改成从 HomePage.vue 的 MOD_GROUPS 现数：加卡/撤卡不用再动门禁，少渲染一张才会红。
            src = open(os.path.join(ROOT, "app", "src", "pages", "HomePage.vue"),
                       encoding="utf-8").read()
            grp = src.split("const MOD_GROUPS")[1] if "const MOD_GROUPS" in src else ""
            grp = grp.split("\n});")[0]
            want_mods = grp.count("{ href: '") + 1   # +1 是 hero 下面那张整宽入口大卡
            check("新站首页入口卡全渲染出来了（张数按 HomePage.vue 的分组卡表现算）",
                  mods == want_mods, "%d 张 / 表里 %d 张" % (mods, want_mods))
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
                settle_motion(page)
            zc = page.evaluate("() => document.querySelectorAll('.zcard').length")
            check("新站区域卡数量与数据一致", zc == S["zones"], "%d 张（数据 %d）" % (zc, S["zones"]))
            page.click('[data-t="rares"]')
            page.wait_for_timeout(1400)
            settle_motion(page)   # 上面那一圈刚把面板换掉，量点位前必须等它挂回来
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
            settle_motion(page)
            try:   # opacity 是从 .6 过渡到 1 的：量早了就是"悬停没生效"的假红
                page.wait_for_function("() => { const d = document.querySelector('.zdot.on');"
                                       "  return d && +getComputedStyle(d).opacity > 0.99; }", timeout=6000)
            except Exception:
                pass
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
            settle_motion(jp)   # 换 hash 走的是路由过渡，等它结束再读
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
            snap(jp, path=os.path.join(SHOT_DIR, "app-rares-m.png"))
            jc.close()
            body = page.evaluate("() => document.querySelector('#main').innerText")
            check("新站世界页正文没有面向开发的词", not dev_word_hits(body), "干净")
            snap(page, path=os.path.join(SHOT_DIR, "app-world-rares.png"))
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
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
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
    # 2026-10-21 A03：物品"测试服有没有"这一列改按探针那条显示（以插件为准）。
    # 判据全部从 items.json 现算，不写死 82：数据变了这里跟着变，写死的数迟早说旧话。
    srv_has = [x for x in it if x.get("status") == "missing" and x.get("srv") == "present"]
    srv_absent = [x for x in it if x.get("srv") == "absent"]
    chip = page.evaluate("""() => { const b = [...document.querySelectorAll('.kchip, .chips .chip, .chipb')]
             .find(x => (x.innerText || '').indexOf('测试服有') >= 0);
             return b ? b.innerText.replace(/\\s+/g, ' ').trim() : null; }""")
    check("物品库状态条里有「测试服有」这一格，且格子上写的数等于数据里反向分歧的条数",
          chip is not None and str(len(srv_has)) in (chip or ""), "%s / 数据 %d 件" % (chip, len(srv_has)))
    page.evaluate("""() => { const b = [...document.querySelectorAll('.kchip, .chips .chip, .chipb')]
             .find(x => (x.innerText || '').indexOf('测试服有') >= 0); if (b) b.click(); }""")
    page.wait_for_timeout(900)
    got = page.evaluate("""() => ({ n: document.querySelectorAll('.itt tbody tr').length,
             total: (document.querySelector('.pinfo') || {}).innerText || '',
             pager: !!document.querySelector('.pinfo'),
             labels: [...document.querySelectorAll('.itt tbody .ist')].map(x => x.innerText.trim()) })""")
    # 一页只有 50 行，所以判"筛出来多少条"要读页脚那个总数，不能数行——
    # 上一版我按行数比 82，红的是我自己的断言不是页面。
    # 2026-10-22 再补一层：页脚那句「共 N 件」在 .pager 里面，而 .pager 是 v-if="pages > 1"，
    # **结果不足一页时它整条不渲染**，读 innerText 只会拿到空串。名录重算后
    # 「测试服有」从 82 条掉到 3 条，红的就是这条判据本身，不是页面坏了。所以分两种判：
    # 不足一页 → 行数就是总数、且必须没有分页条；超过一页 → 才去读页脚那个数。
    if len(srv_has) <= 50:
        total_ok = (not got["pager"]) and got["n"] == len(srv_has)
    else:
        total_ok = str(len(srv_has)) in got["total"].replace(",", "")
    check("点「测试服有」筛出来的总数等于数据条数，且这一页列里显示的都是同一种",
          total_ok and set(got["labels"]) == {"测试服有"},
          "页脚「%s」/ 分页条 %s / 行数 %d / 数据 %d / 标签 %s" % (
              got["total"].strip() or "（不足一页，分页条不渲染）", got["pager"],
              got["n"], len(srv_has), sorted(set(got["labels"]))[:3]))
    snap(page, path=os.path.join(SHOT_DIR, "a03-items-srvhas.png"))
    page.evaluate("() => { const b = [...document.querySelectorAll('.kchip, .chips .chip, .chipb')]"
                  ".find(x => (x.innerText || '').indexOf('全部') >= 0); if (b) b.click(); }")
    page.wait_for_timeout(700)
    check("探针说「测试服查不到」的条数与名录侧自报 missing 是两条独立的腿（不互相覆盖）",
          len(srv_absent) > 0 and len(srv_absent) <= len([x for x in it if x.get("status") == "missing"]),
          "探针 absent %d / 名录 missing %d" % (
              len(srv_absent), len([x for x in it if x.get("status") == "missing"])))
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
    snap(page, path=os.path.join(SHOT_DIR, "app-items-detail.png"))
    page.click(".idmask")
    settle_motion(page)   # 抽屉现在有退场过渡，而这台环境不产帧：不逼一帧的话离场元素一直挂在 DOM 里
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
        snap(page, path=os.path.join(SHOT_DIR, "app-items-detail-%s.png" % key))
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
        snap(page, path=os.path.join(SHOT_DIR, "app-items-detail-use.png"))
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
    snap(page, path=os.path.join(SHOT_DIR, "app-items.png"))
    ctx.close()

    m = browser.new_context(viewport={"width": 375, "height": 780})
    mp = m.new_page()
    mp.goto(APP_BASE + "/#/", wait_until="networkidle")
    settle_motion(mp)   # 换 hash 走的是路由过渡，等它结束再读
    mp.wait_for_timeout(1600)
    mob = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
      const small = [...document.querySelectorAll('#main a, #main button, #top nav a, #top nav button')]
        .filter(b => { const r = b.getBoundingClientRect(); return r.width && r.height && r.height < 44; }).length;
      return { overflow: document.documentElement.scrollWidth > vw + 1, small: small }; }""")
    check("新站移动端首页不溢出、点击目标 ≥44px", not mob["overflow"] and mob["small"] == 0, json.dumps(mob))
    snap(mp, path=os.path.join(SHOT_DIR, "app-index-mobile.png"), full_page=True)
    m.close()

    m = browser.new_context(viewport={"width": 375, "height": 780})
    mp = m.new_page()
    mp.goto(APP_BASE + "/#/items", wait_until="networkidle")
    settle_motion(mp)   # 换 hash 走的是路由过渡，等它结束再读
    mp.wait_for_timeout(1800)
    mit = mp.evaluate("""() => { const tr = document.querySelector('.itt tbody tr');
      return { overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
               card: tr ? getComputedStyle(tr).display === 'block' : false }; }""")
    check("新站物品库移动端：行卡片化、375 不横滚", not mit["overflow"] and mit["card"], json.dumps(mit))
    snap(mp, path=os.path.join(SHOT_DIR, "app-items-mobile.png"), full_page=True)
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
    snap(mp, path=os.path.join(SHOT_DIR, "app-items-detail-m.png"))
    m.close()












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
    for name, path in app_routes():
        page = ctx.new_page()
        page.goto("%s/#%s%s" % (APP_BASE, path, route_q(path)), wait_until="networkidle")
        settle_motion(page)   # 换页/换 hash 走的是路由过渡，等它结束再读
        page.wait_for_timeout(1400)
        text = page.evaluate("""() => [document.querySelector('#top'), document.querySelector('#main'),
            document.querySelector('#foot')].filter(Boolean).map(e => e.innerText).join('\\n')""")
        scan(path, text)
        page.close()
    ctx.close()

    # 来源抽屉点开后的文字也在扫描范围内：那一段默认收起，但它是玩家真会点开的地方
    ctx2 = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx2.new_page()
    page.goto("%s/#/dungeons" % APP_BASE, wait_until="networkidle")
    settle_motion(page)   # 换页/换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1400)
    page.evaluate("() => document.querySelectorAll('[data-d]').forEach(b => b.click())")
    page.wait_for_timeout(600)
    scan("副本页来源展开后", page.evaluate("() => document.querySelector('#main').innerText"))
    page.goto("%s/#/talent?c=hunter" % APP_BASE, wait_until="networkidle")
    settle_motion(page)   # 换页/换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1500)
    page.evaluate("() => { const b = document.getElementById('tsrcbtn'); if (b) b.click(); }")
    page.wait_for_timeout(500)
    scan("天赋页来源展开后", page.evaluate("() => document.querySelector('#main').innerText"))
    ctx2.close()


CONTRAST_PROBE = """() => {
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
    samples.push({ label, size: px(e), weight: +f.fontWeight,
      cr: ratio(fg, bgOf(e)) }); };
  push('h1', document.querySelector('#main h1'));
  push('正文', document.querySelector('#main p'));
  push('note', document.querySelector('#main .note'));
  push('dim', document.querySelector('#main .dim'));
  push('链接', document.querySelector('#main a'));
  const mono = [...document.querySelectorAll('#main .mono, #main .mline')][0];
  push('等宽元数据', mono);
  return samples.filter(s => { const large = s.size >= 24 || (s.size >= 18.66 && s.weight >= 700);
    return s.cr < (large ? 3 : 4.5); });
}"""

PAGE_PROBE = """() => {
  const q = (s) => [...document.querySelectorAll(s)];
  const main = document.querySelector('#main') || document.body;
  const links = [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href'));
  return {
    h1: q('#main h1').length,
    chars: main.innerText.length,
    ctl: q('#main button, #main a, #main input').length,
    broken: q('img').filter(i => i.complete && i.naturalWidth === 0).length,
    noalt: q('img').filter(i => !i.hasAttribute('alt')).length,
    noname: q('#main button').filter(b => !(b.innerText.trim() || b.getAttribute('aria-label'))).length,
    // 文件式地址（talent.html 这一类）在 SPA 里等于"点了没反应"：新站一律走 #/路由
    fileLinks: links.filter(h => /(^|\\/)\\w+\\.html(\\?|#|$)/.test(h) && !h.startsWith('#')),
    over: document.documentElement.scrollWidth - window.innerWidth,
    marks: { pill: q('#main .pill').length, src: q('#main .src').length,
             covnum: q('#main .covnum').length, rails: q('#main .rail').length },
    body: main.innerText
  };
}"""

TOUCH_PROBE = """() => {
  // 有效点击区 = 元素自己 与 它身上那一层真会接住点击的祖先（label / cursor:pointer 的行或卡）
  // 取大的那个。配装页"部位"那颗 button 只是为了键盘能 Tab 到，热区是整行；
  // 传承页的复选框本体 13px，玩家点的是包住它的 label 那一行。
  // 只按元素自己的矩形量，这两处都会假红（2026-10-24 第一版就红在这）。
  const hit = (e) => { let best = e, b = e.getBoundingClientRect();
    let n = e.parentElement;
    while (n && n !== document.body) { const cs = getComputedStyle(n);
      if (n.tagName === 'LABEL' || cs.cursor === 'pointer') { const r = n.getBoundingClientRect();
        if (Math.min(r.width, r.height) > Math.min(b.width, b.height)) { best = n; b = r; } }
      n = n.parentElement; }
    return best; };
  const els = [...document.querySelectorAll('button, a, input, .node, .qopt, .term, .cls')];
  // .zdot 是地图上的编号点位，故意画得小；每一条都有右侧列表那一行做等价的大目标，
  // world_pins 那节钉着"指点位 → 对应那一行也亮"的双向联动，所以 44px 这条不套在点位本体上。
  const small = els.filter(e => { if (e.classList.contains('zdot')) return false;
      const b = hit(e).getBoundingClientRect();
      return b.width > 0 && b.height > 0 && Math.min(b.width, b.height) < 44; });
  // "被切掉"只算没有被横向滚动容器接住的那些：.boardwrap 里的表超出视口是设计如此，
  // 溢出由那条轨自己的 scrollWidth 吞掉（量错层就会把整张表判成 bug）。
  const scroller = (e) => { let n = e.parentElement;
    while (n && n !== document.body) { const ox = getComputedStyle(n).overflowX;
      if (ox === 'auto' || ox === 'scroll') return true; n = n.parentElement; } return false; };
  const cut = [...document.querySelectorAll('#main .lslot, #main .cls, #main .racecard')]
      .filter(e => !scroller(e) && e.getBoundingClientRect().right > window.innerWidth + 1).length;
  return { small: small.map(e => { const h = hit(e);
      return h.tagName + '.' + String(h.className).split(' ')[0] + ':' + (h.innerText || '').slice(0, 8); }),
           over: document.documentElement.scrollWidth - window.innerWidth,
           vw: window.innerWidth, cut: cut };
}"""


def test_site_wide(browser, base):
    """逐路由的全站底线：渲染完整性 + 红线措辞 + 溯源层不回流内容页 + 可访问性 + 移动端。
       路由名单读 app/src/router.js，加一页自动进这一轮，不必回来补第二份表。"""
    print("\n[21] 全站逐路由底线")
    routes = app_routes()
    check("路由表能从 app/src/router.js 读出来", len(routes) >= 20,
          "%d 条：%s" % (len(routes), ",".join(p for _n, p in routes[:6])))
    if not routes:
        return
    for mob, vp in [("桌面", {"width": 1440, "height": 1000}),
                    ("移动 375", {"width": 375, "height": 812, "is_mobile": True, "has_touch": True})]:
        ctx = browser.new_context(viewport=vp, is_mobile=("移动" in mob), has_touch=("移动" in mob))
        for name, path in routes:
            page = ctx.new_page()
            errs, failed = [], []
            page.on("console", lambda m, e=errs: e.append(m.text[:120]) if m.type == "error" else None)
            page.on("response", lambda r, f=failed: f.append("%d %s" % (r.status, r.url.split("/")[-1]))
                    if r.status >= 400 and not tolerated(r.url) else None)
            url = "%s/#%s%s" % (APP_BASE, path, route_q(path))
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(1500)
            st = page.evaluate(PAGE_PROBE)
            if "移动" not in mob:
                # 不要求"控件数 > N"：系统规则、时间表、排行、溯源这几页本来就是纯读数页，
                # 没按钮是对的。正文非空 + 一个 H1 才是"这页渲染出来了"的判据。
                check("%s：一个 H1、正文非空" % path,
                      st["h1"] == 1 and st["chars"] > 200,
                      "H1 %d / %d 字 / %d 控件" % (st["h1"], st["chars"], st["ctl"]))
                check("%s：无脚本报错与失败请求" % path, not errs and not failed,
                      "; ".join((errs + failed)[:2]) or "干净")
                check("%s：图片都有 alt 且无坏图" % path,
                      st["noalt"] == 0 and st["broken"] == 0,
                      "缺 alt %d / 坏图 %d" % (st["noalt"], st["broken"]))
                check("%s：按钮都有可读名" % path, st["noname"] == 0, "%d 个缺名" % st["noname"])
                check("%s：正文没有文件式地址（那种点了没反应的链接）" % path,
                      not st["fileLinks"], "、".join(st["fileLinks"][:3]))
                check("%s：整页不横溢" % path, st["over"] == 0, "溢出 %d" % st["over"])
                if path == PROVENANCE_ROUTE:
                    check("溯源页仍然挂着分级徽标与来源轨",
                          st["marks"]["pill"] >= 1 and st["marks"]["rails"] >= 1,
                          json.dumps(st["marks"], ensure_ascii=False))
                else:
                    check("%s：不挂徽标/来源块/覆盖率条/来源轨（只在溯源页）" % path,
                          not any(st["marks"].values()), json.dumps(st["marks"], ensure_ascii=False))
                if path in LOOT_ROUTES:
                    check("%s：不出现百分比与掉率措辞（红线）" % path,
                          not re.search(r"\d+\s*%|掉率", st["body"]),
                          re.findall(r".{0,14}(?:\d+\s*%|掉率).{0,14}", st["body"])[:1])
                hits = dev_word_hits(st["body"])
                check("%s：正文没有面向开发的词" % path, not hits, "命中 %s" % hits[:3])
                bad = page.evaluate(CONTRAST_PROBE)
                check("%s 页文字对比度达 AA" % path, not bad,
                      json.dumps(bad, ensure_ascii=False)[:150])
                snap(page, path=os.path.join(SHOT_DIR, "wide-%s.png" % (name or "x")),
                                full_page=False)
            else:
                # 375 这一遍走 soft：站主 2026-10-25 定的"网页手机版暂时不作要求"，
                # 断言照跑照打印，不过只记 NOTE（要恢复硬门槛改 MOBILE_SOFT 一个开关）
                t = page.evaluate(TOUCH_PROBE)
                check("移动端 375 %s：点击目标都够 44px" % path, not t["small"],
                      "%d 个偏小 %s" % (len(t["small"]), sorted(set(t["small"]))[:3]), soft=MOBILE_SOFT)
                check("移动端 375 %s：整页不横溢、没有格子被切掉（视口 %d）" % (path, t["vw"]),
                      t["over"] == 0 and t["cut"] == 0, json.dumps(t, ensure_ascii=False)[:140],
                      soft=MOBILE_SOFT)
            page.close()
        ctx.close()


def test_data_versions(browser, base):
    """全站那句"数据来源版本"撤了以后，版本这件事落到三个地方：页脚一句话、首页一颗徽标、
       溯源页一张逐板块表。三处的值都必须来自规模快照现算的那一份——写死一个号，
       下一次只核了传承就会变成发给玩家的假数（2026-10-23 传承核到 70532 而页脚还写 70338 就是这么来的）。"""
    print("\n[22] 各板块数据版本（页脚 / 首页徽标 / 溯源页表）")
    sc = json.load(open(os.path.join(DATA, "scale.json"), encoding="utf-8"))["scale"]
    vers = sc.get("dataVersions") or []
    meta = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
    note = ((meta.get("dataBaseline") or {}).get("note") or "")
    check("规模快照里有逐板块版本表", len(vers) >= 5, "%d 行" % len(vers))
    check("每一行都至少有一个版本号或一个日期", all(v.get("build") or v.get("checkedAt") for v in vers),
          json.dumps([v["section"] for v in vers if not (v.get("build") or v.get("checkedAt"))], ensure_ascii=False))
    tail = lambda x: str(x or "").split(".")[-1]
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m, e=errs: e.append(m.text[:120]) if m.type == "error" else None)
    page.goto(APP_BASE + "/#/", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1600)
    foot = page.evaluate("() => (document.querySelector('#foot .in') || {}).innerText || ''")
    check("页脚写的是那句'分别核对'，不再挂全站一个版本号", note and note in foot,
          foot.replace("\n", " ／ ")[:120])
    check("页脚不再出现客户端号那一串（1.60.1.x 或'核对于'）",
          not re.search(r"1\.60\.1\.\d|核对于", foot), foot.replace("\n", " ")[:100])
    badge = page.evaluate("() => (document.querySelector('.bbadge') || {}).innerText || ''")
    want = "%s（%s）" % (tail(sc.get("newestBuild")), sc.get("newestSection") or "")
    check("首页徽标报的是快照里最新那个号与那一块（%s）" % want, want in badge.replace(" ", ""),
          badge)
    page.goto(APP_BASE + "/#/provenance", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1600)
    rows = page.evaluate("""() => [...document.querySelectorAll('#lver tbody tr')]
        .map(tr => [...tr.children].map(td => td.innerText.trim()))""")
    check("溯源页那张表的行数等于快照里的板块数", len(rows) == len(vers),
          "表 %d 行 / 快照 %d 行" % (len(rows), len(vers)))
    bad = []
    for r, v in zip(rows, vers):
        if r[0] != v["section"] or r[1] != (tail(v.get("build")) or "—"):
            bad.append("%s：页面 %s / 快照 %s" % (v["section"], r[:2], [v["section"], tail(v.get("build"))]))
    check("逐行的板块名与客户端号都跟快照一致（不是页面自己写死的）", not bad, "；".join(bad[:2]))
    dates = [r[2] for r in rows]
    check("日期那列要么是快照里的日期、要么明写未记录，不留空",
          all(d and (d == "未记录" or re.match(r"^\d{4}-\d{2}-\d{2}$", d)) for d in dates),
          json.dumps(dates, ensure_ascii=False))
    ages = [r[3] for r in rows]
    pol = sc.get("stalePolicy") or {}
    check("「多久没核了」那一列每行都有天数，且与快照现算的天数逐行一致",
          bool(ages) and all(re.match(r"^\d+ 天", a or "") for a in ages)
          and [int(a.split(" ")[0]) for a in ages] == [v.get("daysSince") for v in vers],
          json.dumps(ages, ensure_ascii=False))
    body = page.evaluate("() => document.body.innerText")
    check("过期阈值那句话的天数来自规模快照，不是页面自己抄的第二份数",
          bool(pol.get("soft")) and bool(pol.get("hard"))
          and (u"超过 %d 天" % pol["soft"]) in body and (u"超过 %d 天" % pol["hard"]) in body,
          "提示 %s 天 / 拦红 %s 天" % (pol.get("soft"), pol.get("hard")))
    check("这一页无脚本报错", not errs, "; ".join(errs[:2]) or "干净")
    snap(page, path=os.path.join(SHOT_DIR, "app-provenance-versions.png"))
    ctx.close()


# 全跑一次 13 分钟，改一条新断言时等不起。SECTIONS 把顺序固定下来，--only 按名字挑着跑，
# 用来做 30 秒探针；正式门禁仍然不带 --only。


def test_macros(browser, base):
    """宏命令页（2026-10-30 站主："素材库中有魔兽无限的宏命令素材，先整理好数据，
       然后在网页端导航条添加宏命令入口，设计宏命令页面"）。
       数据整批 L1（一家第三方插件整理、本站未逐条实测），所以这节盯的四件事都是
       "界面有没有比数据多说东西"与"筛了到底生不生效"：
       ① 导航有这一格、走站内路由；② 芯片上的数 = 点下去看到的数（放了不生效的数比不放更坏）；
       ③ 职业 / 分组 / 搜索 / 等级四个条件真叠加生效，且地址能原样带进来（可分享）；
       ④ 复制按钮粘出去的字符串与页面上那段 <pre> 逐字相同——这条不靠眼看；
       ⑤ 红线：页面上不许出现下载插件 / 收费 / 已实测这类话，也不许残留没翻出来的法术占位。"""
    print("\n[6g] 宏命令页")
    if not app_up(browser):
        return
    import json as _j
    doc = _j.load(open(os.path.join(SRC, "data", "macros.json"), encoding="utf-8"))
    MS = doc["macros"]
    by_cls = {}
    for m in MS:
        by_cls.setdefault(m["classId"], []).append(m)
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=APP_BASE)
    except Exception:
        pass
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:140]))
    page.goto(APP_BASE + "/#/macros", wait_until="networkidle")
    settle_motion(page)
    page.wait_for_timeout(1200)

    nav = page.evaluate("""() => { const a = [...document.querySelectorAll('nav.main a.nl')]
        .find(x => x.textContent.trim().indexOf('宏命令') === 0);
      return a ? { href: a.getAttribute('href'), on: a.classList.contains('on') } : null; }""")
    check("导航「工具」组里有「宏命令」这一格，且走的是站内路由",
          nav and nav["href"] == "#/macros", json.dumps(nav, ensure_ascii=False))
    h1 = page.evaluate("() => [...document.querySelectorAll('#main h1')].map(e => e.innerText.trim())")
    check("这一页只有一个 H1 且标题是宏命令", h1 == [u"宏命令"], str(h1))
    note = page.evaluate("() => (document.querySelector('#main .note')||{}).innerText || ''")
    check("页顶那句口径在（第三方整理 + 未逐条实测），不是空话",
          u"第三方插件" in note and u"没有逐条进游戏试过" in note, note[:60])
    cards = page.evaluate("() => document.querySelectorAll('.mc').length")
    check("默认落在第一个职业，卡数等于数据里这一职业的条数",
          cards == len(by_cls["warrior"]), "%s 张 / 数据 %s" % (cards, len(by_cls["warrior"])))

    chips = page.evaluate("""() => [...document.querySelectorAll('.picks [data-c]')].map(b => ({
        c: b.getAttribute('data-c'), n: +(b.querySelector('.mono')||{}).textContent }))""")
    bad = [x for x in chips if x["n"] != len(by_cls.get(x["c"], []))]
    check("九颗职业芯片各带自己的条数，且与数据一致（不是手抄的数）",
          len(chips) == 9 and not bad, json.dumps(bad or [c["c"] for c in chips], ensure_ascii=False))
    page.click('[data-c="priest"]')
    settle_motion(page)
    page.wait_for_timeout(400)
    check("点一颗职业芯片真的换画面（卡数 = 该职业条数）",
          page.evaluate("() => document.querySelectorAll('.mc').length") == len(by_cls["priest"]),
          "%s 张 / 数据 %s" % (page.evaluate("() => document.querySelectorAll('.mc').length"), len(by_cls["priest"])))

    grp = page.evaluate("""() => { const b = [...document.querySelectorAll('.mc-groups [data-g]')]
        .filter(x => x.getAttribute('data-g'))[0];
      return b ? { g: b.getAttribute('data-g'), n: +b.querySelector('.mono').textContent } : null; }""")
    want = len([m for m in by_cls["priest"] if m["group"] == grp["g"]])
    page.click('.mc-groups [data-g]:not([data-g=""])')
    settle_motion(page)
    page.wait_for_timeout(400)
    check("点一颗用途分组芯片筛出来的条数就是芯片上那个数",
          grp and grp["n"] == want and page.evaluate("() => document.querySelectorAll('.mc').length") == want,
          json.dumps({"芯片": grp, "数据": want,
                      "画面": page.evaluate("() => document.querySelectorAll('.mc').length")}, ensure_ascii=False))
    check("分组芯片里没有『点了为空』的那颗",
          page.evaluate("""() => [...document.querySelectorAll('.mc-groups [data-g]')]
            .filter(b => b.getAttribute('data-g')).every(b => +b.querySelector('.mono').textContent > 0)"""), "全都有数")

    page.click('[data-g=""]')
    settle_motion(page)
    # 搜的是牧师真有的词：这一页的搜索**在当前职业内**搜（跨职业由空态那排按钮引过去），
    # 拿"嘲讽"这种战士技能来搜牧师，测的就不是搜索而是空态了——那条单独钉。
    page.fill("#mq", "真言术")
    page.wait_for_timeout(700)
    hit = page.evaluate("""() => [...document.querySelectorAll('.mc')].map(c =>
        (c.innerText || '') )""")
    check("搜「真言术」筛出来的每一条都真含这个词（在标题/说明/正文/组名任一处）",
          0 < len(hit) < len(by_cls["priest"]) and all(u"真言术" in t for t in hit), "%s 条" % len(hit))
    page.fill("#mq", "嘲讽")
    page.wait_for_timeout(700)
    empty = page.evaluate("""() => ({ txt: (document.querySelector('#main .empty')||{}).innerText || '',
      jump: [...document.querySelectorAll('.mc-jump')].map(b => b.getAttribute('data-c')) })""")
    check("当前职业里没有这个词时走空态，并把别的职业有几条摆出来（不是白屏也不是死路）",
          u"没有匹配的宏" in empty["txt"] and "warrior" in empty["jump"],
          json.dumps(empty, ensure_ascii=False)[:120])
    page.fill("#mq", "")
    page.wait_for_timeout(500)
    # 选了一个组、又搜一个那个组里没有的词：不能掉进"芯片还亮着、画面 0 条"的死路
    page.fill("#mq", "")
    page.wait_for_timeout(500)
    gbtns = page.evaluate("() => [...document.querySelectorAll('.mc-groups [data-g]')]"
                          ".map(b => b.getAttribute('data-g')).filter(Boolean)")
    if len(gbtns) > 1:
        page.click('.mc-groups [data-g="%s"]' % gbtns[0])
        page.wait_for_timeout(300)
        page.fill("#mq", "zzzqqqxx")
        page.wait_for_timeout(700)
        stuck = page.evaluate("""() => ({ on: [...document.querySelectorAll('.mc-groups [data-g]')]
            .filter(b => b.classList.contains('on')).map(b => b.getAttribute('data-g')),
            empty: !!document.querySelector('#main .empty') })""")
        check("搜到空的时候，上一屏选中的组会自动清掉（不留『芯片亮着、画面 0 条』的死路）",
              stuck["empty"] and stuck["on"] == [], json.dumps(stuck, ensure_ascii=False))
    page.fill("#mq", "")
    page.wait_for_timeout(500)
    page.fill("#mlv", "20")
    page.wait_for_timeout(500)
    lv = page.evaluate("""() => [...document.querySelectorAll('.mc')].map(c => {
        const m = (c.querySelector('.mc-m')||{}).innerText || '';
        const k = m.match(/(\\d+)\\s*级能用/); return k ? +k[1] : 0; })""")
    check("填了等级之后留下的每一条门槛都 ≤ 该等级，且确实滤掉了几条",
          lv and max(lv) <= 20 and len(lv) < len(by_cls["priest"]),
          "%s 条 / 最高门槛 %s 级" % (len(lv), max(lv) if lv else "-"))
    cnt = page.evaluate("() => (document.querySelector('#mcnt')||{}).innerText || ''")
    cut = len([m for m in by_cls["priest"] if m["minLevel"] and m["minLevel"] > 20])
    check("读数行说的「学不会的滤掉 N 条」与数据一致（这句话不是摆设）",
          (u"滤掉 %d 条" % cut) in cnt and cut > 0, cnt[:80])
    page.fill("#mlv", "")
    page.wait_for_timeout(400)

    # 复制：粘出去的必须与页面上那段逐字相同
    pre = page.evaluate("""() => { const p = document.querySelector('.mc .mc-b');
      return { id: p.getAttribute('data-m'), txt: p.textContent }; }""")
    page.click(".mc .mc-copy")
    page.wait_for_timeout(500)
    got = None
    try:
        got = page.evaluate("() => navigator.clipboard.readText()")
    except Exception:
        got = None
    toast = page.evaluate("() => { const t = document.getElementById('toast');"
                          " return t ? { on: t.classList.contains('on'), txt: t.textContent } : null; }")
    same = (got == pre["txt"]) if got is not None else bool(toast and toast["on"])
    check("点「复制宏」粘出去的正文与页面上那段逐字相同（含换行）",
          same and bool(toast and toast["on"]),
          ("剪贴板比对" if got is not None else "剪贴板读不到，退回看提示") + "：" + (toast or {}).get("txt", "")[:24])
    body_in_data = next((m["body"] for m in MS if m["id"] == pre["id"]), None)
    check("页面上那段正文就是数据里那段（没有被排版改字）", body_in_data == pre["txt"],
          "对得上" if body_in_data == pre["txt"] else "不一致")

    # 地址能原样带进来（发给别人要用）
    pick = by_cls["druid"][0]
    page.goto(APP_BASE + "/#/macros?c=druid&g=%s&lv=10" % pick["group"], wait_until="networkidle")
    settle_motion(page)
    page.wait_for_timeout(1200)
    deep = page.evaluate("""() => {
      const onOf = (sel) => { const b = [...document.querySelectorAll(sel)].find((x) => x.classList.contains('on'));
        return b ? b.getAttribute('data-c') || b.getAttribute('data-g') || '' : null; };
      return { on: onOf('[data-c]'), grpOn: onOf('.mc-groups [data-g]'),
               cards: document.querySelectorAll('.mc').length }; }""")
    want_deep = len([m for m in by_cls["druid"] if m["group"] == pick["group"]
                     and (not m["minLevel"] or m["minLevel"] <= 10)])
    check("带 ?c=&g=&lv= 的地址直接进来就是那个筛法（可分享）",
          deep["on"] == "druid" and deep["grpOn"] == pick["group"] and deep["cards"] == want_deep,
          json.dumps({"画面": deep, "应有": want_deep}, ensure_ascii=False))

    txt = page.evaluate("() => document.querySelector('#main').innerText")
    bad_words = [w for w in (u"下载插件", u"安装插件", u"付费", u"会员", u"购买", u"已实测", u"官方宏")
                 if w in txt]
    check("红线：页面上没有下载插件 / 收费 / 已实测这类说法", not bad_words, str(bad_words))
    check("红线：页面上不残留没翻出来的法术占位", "{{" not in txt, "干净")
    check("这一页无脚本报错", not errs, "; ".join(errs[:2]) or "干净")
    snap(page, path=os.path.join(SHOT_DIR, "macros-1440.png"))
    ctx.close()


def test_motion(browser, base):
    """交互动效（2026-10-29 站主："页面跳转或者是展开收起，卡片切换等动作加入动效"）。
       这节盯的不是"有没有写 CSS"，而是"点下去到底动没动"：白放的选项比不放的选项更坏
       （10-23 那轮抓过五处），动效同理——过渡类挂不上、或者挂了但算出来的时长是 0，
       玩家看到的就是原来那一下硬切。
       判据用 getAnimations()，不用"中间帧的高度"：首屏之后主线程还被图片与懒加载占着，
       过渡的时间轴会被冻住（实测点下去 500ms 内高度一直停在 0fr），量高度会把
       "真在动"误判成"没动"。getAnimations() 在过渡建立的那一刻就有条目，跟帧率无关。
       ① 换页：淡出类与淡入类都出现过，out-in 保证同屏只有一个 .view；
       ② 抽屉：过渡类 + 真有一条 grid-template-rows 过渡在跑 + 终态高度是内容的自然高度；
       ③ 折叠：传承页那六组以前挂的是 animation，但元素是 v-show，只有页面加载那次会播——
          "折叠/展开这两下有过渡"是本轮才有的事，反向钉得住；
       ④ 面板切换：切完画面真的换成那一块（不是挂了个类就算）；
       ⑤ 物品抽屉能退场（原来只有 @keyframes 管进场，关的时候是直接消失）；
       ⑥ 减弱动态效果：同一批过渡类算出来的时长 <1ms，且 getAnimations() 里没有条目，
          换页全程 opacity=1（关了动效不等于闪空白，也不等于还在滑）；
       ⑦ 场景红线扫 motion.css 源码：不许 infinite、位移 ≤20px、时长 ≤240ms。
       采样一律真 page.click()、观察器先挂再点：Vue 更新是异步的，点击与读结果挤在同一个
       同步 evaluate 里只会量到点击前那一帧（10-15 踩过）。"""
    print("\n[6f] 交互动效")
    if not app_up(browser):
        return
    import re as _re

    # —— ⑦ 源码红线：不起浏览器 ——
    mcss = open(os.path.join(ROOT, "app", "src", "styles", "motion.css"), encoding="utf-8").read()
    body = _re.sub(r"/\*.*?\*/", "", mcss, flags=_re.S)      # 注释里那句"不许 infinite"不算违规
    check("motion.css 里没有循环动效（infinite）", "infinite" not in body,
          "命中 %d 处" % body.count("infinite") if "infinite" in body else "零处")
    shift = [abs(int(x)) for x in _re.findall(r"translate[XY]\((-?\d+)px\)", body)]
    check("位移全部 ≤20px，且没有超过 1.05 的缩放",
          (max(shift) if shift else 0) <= 20 and not _re.search(r"scale\(\s*1\.(0[6-9]|[1-9]\d)", body),
          "最大位移 %spx" % (max(shift) if shift else 0))
    check("motion.css 里没有写死超过 240ms 的时长",
          all(int(d) <= 240 for d in _re.findall(r"(\d+)ms", body)),
          "ms 值 %s" % sorted(set(int(x) for x in _re.findall(r"(\d+)ms", body))))
    dist_css = "".join(open(os.path.join(SRC, "assets", f), encoding="utf-8", errors="ignore").read()
                       for f in os.listdir(os.path.join(SRC, "assets")) if f.endswith(".css"))
    need = (".page-enter-active", ".unfold-enter-active", ".swap-enter-active", ".idr-leave-active")
    check("动效层进了构建产物（main.js 那行 import 没漏、也没只停在工作区）",
          all(k in dist_css for k in need), "缺 " + ",".join(k for k in need if k not in dist_css) or "四类齐")

    WATCH = """(sel) => { window.__m = { classes: [], ops: [], anims: [] }; const st = window.__m;
      const grab = () => { const el = document.querySelector(sel); if (!el) return;
        const cn = typeof el.className === 'string' ? el.className : '';
        if (st.classes.indexOf(cn) < 0) st.classes.push(cn);
        st.ops.push(+getComputedStyle(el).opacity);   // 先读一次计算值把样式刷出来：
        // 不刷就 getAnimations()，过渡还没建立，永远抓不到条目（实测就是这个顺序）
        el.getAnimations().forEach(a => { const d = (a.effect && a.effect.getTiming
            ? a.effect.getTiming().duration : 0) || 0;
          const k = (a.transitionProperty || a.animationName || '') + '@' + Math.round(d);
          if (st.anims.indexOf(k) < 0) st.anims.push(k); }); };
      st.mo = new MutationObserver(grab);
      st.mo.observe(document.querySelector('#main') || document.body,
                    { attributes: true, attributeFilter: ['class'], subtree: true, childList: true });
      st.tick = setInterval(grab, 16); grab(); }"""
    STOP = """() => { clearInterval(window.__m.tick); window.__m.mo.disconnect();
      const o = window.__m; window.__m = null;
      o.views = document.querySelectorAll('#main > .view').length; return o; }"""
    # 问 CSSOM：这套过渡类在这台机器上算出来是几毫秒
    DUR = """(cls) => { const d = document.createElement('div'); d.className = cls;
      (document.querySelector('#main') || document.body).appendChild(d);
      const v = getComputedStyle(d).transitionDuration; d.remove(); return v; }"""
    TRN = [".page-enter-active", ".swap-enter-active", ".unfold-enter-active",
           ".pop-enter-active", ".idr-enter-active", ".idf-leave-active"]
    ms = lambda v: max(float(x.rstrip("s")) * 1000 for x in v.split(",") if x.strip()) if v else 0.0

    def watch(page, sel):
        page.evaluate(WATCH, sel)

    def stop(page):
        return page.evaluate(STOP)

    ctx = browser.new_context(viewport={"width": 1440, "height": 950})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:120]))

    # —— ① 换页 ——
    page.goto(APP_BASE + "/#/", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_selector("#main > .view", timeout=15000)
    page.wait_for_timeout(600)
    durs = [page.evaluate(DUR, c.lstrip(".")) for c in TRN]
    check("正常模式下这六类过渡算出来的时长都 ≥1ms（动效是真挂上去的）",
          all(ms(d) >= 1 for d in durs), " / ".join(durs))
    watch(page, "#main > .view")
    page.evaluate("() => { location.hash = '#/world' }")
    settle_motion(page)
    r = stop(page)
    check("换页时旧页淡出类与新页淡入类都出现过",
          any("page-leave-active" in c for c in r["classes"])
          and any("page-enter-active" in c for c in r["classes"]), str(r["classes"][:4]))
    check("换页这一路确实建立了 opacity 过渡（类刚变那一刻抓到的）",
          any(x.startswith("opacity@") and x.split("@")[1] != "0" for x in r["anims"]),
          json.dumps(r["anims"][:4]))
    check("out-in 生效：#main 下始终只有一个 .view（新旧页不重叠）",
          r["views"] == 1, "同屏 %s 个" % r["views"])
    settle_motion(page)
    rest = page.evaluate("""() => { const v = document.querySelector('#main > .view');
      return { cls: v.className, op: +getComputedStyle(v).opacity }; }""")
    check("过渡结束后 .view 恢复干净状态且看得见（不会停在半透明）",
          "page-" not in rest["cls"] and rest["op"] == 1, json.dumps(rest))

    # —— ② 副本抽屉 ——
    page.goto(APP_BASE + "/#/dungeons", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_selector("[data-d]", timeout=20000)
    page.wait_for_timeout(400)
    watch(page, ".drawer-clip")
    page.click("[data-d]")
    settle_motion(page)
    r = stop(page)
    check("抽屉挂着 unfold 过渡类展开", any("unfold-enter-active" in c for c in r["classes"]),
          str(r["classes"][:2]))
    # 这里钉的是"建立的是哪一条过渡"，不是"逐帧高度"。原因写清楚免得下轮又去量高度：
    # 门禁这台 headless Chrome（--use-angle=swiftshader）的动画时钟不走——getAnimations() 里
    # playState 是 running 但 currentTime 恒 0，中间帧在这台环境里根本采不到；
    # 同一份产物在普通 --headless=new 下实测会走 8px → 361px → 456px → 466px。
    # "逐帧真的在长"交给 8821 人眼验收 + 中间帧截图，机器只钉"挂的是 grid-template-rows 且时长非零"。
    check("抽屉展开建立的是 grid-template-rows 这条过渡，且时长非零",
          any(x.startswith("grid-template-rows@") and x.split("@")[1] != "0" for x in r["anims"]),
          json.dumps(r["anims"][:4]))
    settle_motion(page)   # 再逼一帧：这台环境不产帧，高度会停在 0
    fin = page.evaluate("() => Math.round(document.querySelector('.drawer-clip')"
                        ".getBoundingClientRect().height)")
    check("展开到底之后是内容的自然高度（不会停在 0fr 那一档）", fin > 120, "终值 %s" % fin)
    snap(page, path=os.path.join(SHOT_DIR, "motion-副本抽屉展开.png"))

    # —— ③ 传承页折叠 ——
    page.goto(APP_BASE + "/#/legacy", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_selector("[data-blk]", timeout=20000)
    page.wait_for_timeout(600)
    watch(page, ".lchbody")
    page.click("[data-blk]")
    settle_motion(page)
    rl = stop(page)
    watch(page, ".lchbody")
    page.click("[data-blk]")
    settle_motion(page)
    re_ = stop(page)
    check("传承页收起来那一下有退场过渡（旧版 animation 挂在 v-show 上，这里一条都采不到）",
          any("unfold-leave-active" in c for c in rl["classes"]), str(rl["classes"][:2]))
    check("再点一次是反向展开（进场类也在）",
          any("unfold-enter-active" in c for c in re_["classes"]), str(re_["classes"][:2]))

    # —— ④ 世界页换面板 ——
    page.goto(APP_BASE + "/#/world", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_selector('[data-t="rares"]', timeout=20000)
    page.wait_for_timeout(900)
    before = page.evaluate("() => document.querySelectorAll('#main .zcard').length")
    watch(page, ".wswap")
    page.click('[data-t="rares"]')
    rows = []
    for _ in range(12):
        rows.append(page.evaluate("() => !!document.querySelector('.wswap.swap-enter-active,"
                                  " .wswap.swap-leave-active')"))
        settle_motion(page, timeout=2500)
    # out-in 之后新面板要重挂整块（世界页那一面板 25000 像素），等它换完再判画面
    page.wait_for_function("""() => { const on = [...document.querySelectorAll('[data-t]')]
        .find(x => x.classList.contains('on')); return on && on.getAttribute('data-t') === 'rares'
        && !document.querySelector('.wswap.swap-leave-active'); }""", timeout=8000)
    r = stop(page)
    check("世界页换面板有 swap 过渡类（淡出再淡入）",
          any("swap-leave-active" in c for c in r["classes"])
          and any("swap-enter-active" in c for c in r["classes"]), str(r["classes"][:4]))
    check("这一路过渡类真的挂上过（不是只换了块内容）", any(rows), str(rows[:6]))
    after = page.evaluate("""() => ({ z: document.querySelectorAll('#main .zcard').length,
      band: document.querySelectorAll('#main .band').length,
      on: (([...document.querySelectorAll('[data-t]')].find(x => x.classList.contains('on')) || {})
           ).getAttribute('data-t') || '' })""")
    check("切到「稀有」之后画面上确实换成那一块（区域卡没了、稀有那一排的分组条出来了）",
          before > 0 and after["z"] == 0 and after["on"] == "rares" and after["band"] > 0,
          json.dumps({"切换前区域卡": before, "切换后": after}, ensure_ascii=False))
    snap(page, path=os.path.join(SHOT_DIR, "motion-世界页换面板.png"))

    # —— ⑤ 物品抽屉退场 ——
    page.goto(APP_BASE + "/#/items", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_selector(".itt tbody tr", timeout=20000)
    page.wait_for_timeout(500)
    page.click(".itt tbody tr:first-child")
    page.wait_for_timeout(900)
    check("点一行能开抽屉，宽度还是那一条（横向位移不改宽度）",
          page.evaluate("() => { const d=document.querySelector('.idrawer');"
                        " return !!d && Math.round(d.getBoundingClientRect().width) >= 300 }"), "开")
    watch(page, ".idmask")
    page.click(".idmask")
    settle_motion(page)
    r = stop(page)
    check("关抽屉时遮罩走退场过渡（不是当场消失）",
          any("idf-leave-active" in c for c in r["classes"]), str(r["classes"][:2]))
    page.wait_for_timeout(400)
    check("退场结束后抽屉与遮罩都不在 DOM 里（离场元素没留下来挡点击）",
          page.evaluate("() => !document.querySelector('.idrawer') && !document.querySelector('.idmask')"),
          "已清")
    ctx.close()

    # —— ⑥ 减弱动态效果 ——
    ctx2 = browser.new_context(viewport={"width": 1440, "height": 950}, reduced_motion="reduce")
    rp = ctx2.new_page()
    rp.on("pageerror", lambda e: errs.append(str(e)[:120]))
    rp.goto(APP_BASE + "/#/", wait_until="networkidle")
    settle_motion(rp)   # 换 hash 走的是路由过渡，等它结束再读
    rp.wait_for_selector("#main > .view", timeout=15000)
    rp.wait_for_timeout(500)
    rdurs = [rp.evaluate(DUR, c.lstrip(".")) for c in TRN]
    check("减弱动态效果下：同一批过渡类算出来 ≤1ms（真的没在动）",
          all(ms(d) <= 1 for d in rdurs), " / ".join(rdurs))
    watch(rp, "#main > .view")
    rp.evaluate("() => { location.hash = '#/world' }")
    rp.wait_for_timeout(700)
    r = stop(rp)
    # 反向钉：ANIM 会一路轮满 1.2 秒，正常模式下这里至少抓到一条；
    # 减弱动态效果下必须一条都没有——这才叫"关了"，而不是"关了但还在滑"。
    check("减弱动态效果下：换页没有建立任何过渡（类变那一刻也没有条目）",
          not r["anims"], json.dumps(r["anims"][:4]))
    check("减弱动态效果下：换页这一路没有任何一帧是不可见的",
          r["ops"] and all(o == 1 for o in r["ops"]), "采样 %s" % r["ops"][:8])
    settle_motion(rp)
    check("减弱动态效果下：换到的还是同一块内容（世界页区域卡照常出来）",
          rp.evaluate("() => document.querySelectorAll('#main .zcard').length") > 0, "有卡")
    rp.goto(APP_BASE + "/#/dungeons", wait_until="networkidle")
    settle_motion(rp)   # 换 hash 走的是路由过渡，等它结束再读
    rp.wait_for_selector("[data-d]", timeout=20000)
    rp.wait_for_timeout(400)
    watch(rp, ".drawer-clip")
    rp.click("[data-d]")
    first = rp.evaluate("() => Math.round(document.querySelector('.drawer-clip')"
                        ".getBoundingClientRect().height)")
    rp.wait_for_timeout(400)
    r = stop(rp)
    # 不写"466"这种量出来的数：拿这一行自己的计算值和内层自然高度比。
    natural = rp.evaluate("() => Math.round(document.querySelector('.drawer-clip > .wf-in')"
                          ".getBoundingClientRect().height)")
    check("减弱动态效果下：抽屉一点就开到底（没建立过渡、也没有半截高度），内容照常看得见",
          not r["anims"] and natural > 0 and first >= natural - 3,
          json.dumps({"过渡": r["anims"], "首帧高度": first, "内容自然高度": natural}))
    snap(rp, path=os.path.join(SHOT_DIR, "motion-reduced-副本抽屉.png"))
    check("这一节没引出脚本报错", not errs, "; ".join(errs[:2]) or "干净")
    ctx2.close()


def test_prof_tiers(browser, base):
    """钓鱼那张表按技能分段出列（2026-10-28 修的那处列映射错位）。
       单独成一节而不是塞在 [6a] 里：那一节现在在这台机器上跑不到底，
       断言埋在跑不到的地方等于没有。"""
    print("\n[6e] 专业页·钓鱼技能分段" if False else "\n[6e] 专业页 钓鱼技能分段")
    # 钓鱼那张表的列映射（2026-10-27 来源复核记的已知错）：源页给的是
    # 「稳定上钩 / 开始咬钩 / 区域」三段，当年抓取按采集点列序硬套，
    # 页面上就把名字画成了 25、75 这种光数字。钉三件事：
    # 表头换成技能分段、第一格不是纯数字、"开始咬钩"那一列真有值。
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(APP_BASE + "/#/professions", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(1500)
    page.evaluate("() => { const b=[...document.querySelectorAll('.pick')]"
                  "  .find(x => x.innerText.indexOf('钓鱼') >= 0); if (b) b.click(); }")
    page.wait_for_timeout(700)
    fh = page.evaluate("""() => {
      const card = [...document.querySelectorAll('.card')].find(c =>
        (c.querySelector('.bt') || {}).innerText && c.querySelector('.bt').innerText.indexOf('技能分段') >= 0);
      if (!card) return { head: null };
      const ths = [...card.querySelectorAll('thead th')].map(x => x.innerText.trim());
      const first = [...card.querySelectorAll('tbody tr')].slice(0, 2)
        .map(tr => [...tr.querySelectorAll('td')].map(td => td.innerText.trim()));
      return { head: ths, rows: first, n: card.querySelectorAll('tbody tr').length };
    }""")
    check("钓鱼那张表按技能分段出表头，不再借采集点那五列",
          fh.get("head") == [u"技能段", u"几点开始咬钩", u"稳定上钩", u"这些水域"], json.dumps(fh, ensure_ascii=False)[:150])
    check("分段第一格是「稳定上钩 N 级」这种读得通的名字，不是光一个数字",
          bool(fh.get("rows")) and bool(re.match(r'^稳定上钩 \d+ 级$', fh["rows"][0][0] or "")),
          json.dumps(fh.get("rows", [])[:1], ensure_ascii=False))
    check("「几点开始咬钩」那一列真有值（一开始 / 51 起 这类）",
          all(len(r) > 1 and r[1] for r in fh.get("rows") or []),
          json.dumps([r[1:2] for r in fh.get("rows") or []], ensure_ascii=False))
    # 反面样本：换一个真有采集点的专业，那五列必须还在——
    # 否则"按数据判断是不是分段表"这个开关就是把别的页也一起改了。
    page.evaluate("() => { const b=[...document.querySelectorAll('.pick')]"
                  "  .find(x => x.innerText.indexOf('草药学') >= 0); if (b) b.click(); }")
    page.wait_for_timeout(700)
    hb = page.evaluate("""() => {
      const card = [...document.querySelectorAll('.card')].find(c => c.querySelector('table.board'));
      return { ths: [...card.querySelectorAll('thead th')].map(x => x.innerText.trim()),
               first: ((card.querySelector('tbody tr .nm') || {}).innerText || '').trim() };
    }""")
    check("草药学仍走采集点那五列（分段开关没有误伤别的页）",
          hb["ths"] == [u"图标", u"草药点", u"可得", u"最多区域", u"技能"] and hb["first"] != "",
          json.dumps(hb, ensure_ascii=False)[:140])
    snap(page, path=os.path.join(SHOT_DIR, "app-prof-fishing-tiers.png"))
    ctx.close()


def test_pets(browser, base):
    """宠物家族与技能页（2026-10-28 站主拍板开这一页）。盯五件事：
       ① 两张表的行数与 pets.json 的条数对得上，计数行也是同一份数；
       ② 三个筛选项**都真生效**（搜索框、只看新增、按家族筛）——放了不生效的选项比不放更坏；
       ③ 家族行上的技能条点一下要真把技能表筛到那一条（这是这条链唯一的入口，白放就是装饰）；
       ④ 0 这个值显示成 0，不许空着（空着会被读成"没数据"）；图标全部本地且真加载出来；
       ⑤ 红线：不许出现成句的技能描述（插件里 dcn/den 那一层一条没取）。"""
    print("\n[6d] 宠物家族与技能")
    import json
    pets = json.load(open(os.path.join(SRC, "data", "pets.json"), encoding="utf-8"))
    fams, sks, pc = pets["families"], pets["skills"], pets["meta"]["counts"]
    if not app_up(browser):
        return
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.goto(APP_BASE + "/#/pets", wait_until="networkidle")
    settle_motion(page)   # 换 hash 走的是路由过渡，等它结束再读
    page.wait_for_timeout(900)
    h1 = page.evaluate("() => [...document.querySelectorAll('h1')].map(x => x.innerText.trim())")
    check("这一页只有一个 H1 且标题写的是家族与技能",
          h1 == [u"宠物家族与技能"], str(h1))
    rows = page.evaluate("() => ({ f: document.querySelectorAll('#ptfam tbody tr').length,"
                         " s: document.querySelectorAll('#ptsk tbody tr').length,"
                         " cnt: (document.querySelector('#ptcnt')||{}).innerText || '' })")
    check("家族表行数 = 数据条数", rows["f"] == len(fams), "%s vs %s" % (rows["f"], len(fams)))
    check("技能表行数 = 数据条数", rows["s"] == len(sks), "%s vs %s" % (rows["s"], len(sks)))
    check("计数行两个数都从数据来（不是手抄）",
          (u"家族 %d / %d" % (len(fams), len(fams))) in rows["cnt"]
          and (u"技能 %d / %d" % (len(sks), len(sks))) in rows["cnt"], rows["cnt"])
    # ① 搜索框
    page.fill("#q", fams[0]["name"])
    page.wait_for_timeout(350)
    got = page.evaluate("() => [...document.querySelectorAll('#ptfam tbody tr .nm')]"
                        ".map(x => x.innerText.trim())")
    check("搜中文名筛得动，且筛出来的每一条都真含那个词",
          0 < len(got) < len(fams) and all(fams[0]["name"] in x for x in got), str(got[:4]))
    # ② 只看新增
    page.fill("#q", "")
    page.wait_for_timeout(250)
    page.click("#onlynew")
    page.wait_for_timeout(350)
    nf = page.evaluate("() => ({ n: document.querySelectorAll('#ptfam tbody tr').length,"
                       " tags: [...document.querySelectorAll('#ptfam tbody tr .tag')]"
                       ".map(x => x.innerText.trim()) })")
    check("勾「只看《无限》新加的」真的变少，且每条都带新增标",
          nf["n"] == pc["familiesNew"] and len(nf["tags"]) == nf["n"],
          "%s 行 / 标 %s 个（数据记 %s）" % (nf["n"], len(nf["tags"]), pc["familiesNew"]))
    page.click("#onlynew")
    page.wait_for_timeout(300)
    # ③ 家族行点技能条 → 技能表筛到那一条
    chip = page.evaluate("() => { const b = document.querySelector('#ptfam tbody tr .pt-chip');"
                         " return b ? b.innerText.trim() : ''; }")
    page.click("#ptfam tbody tr .pt-chip")
    page.wait_for_timeout(400)
    after = page.evaluate("() => [...document.querySelectorAll('#ptsk tbody tr .nm')]"
                          ".map(x => x.innerText.trim())")
    check("点家族行上的技能条，技能表真被筛到那一条（不是白放的装饰）",
          chip != "" and len(after) >= 1 and all(chip in x for x in after),
          "点了「%s」→ %s" % (chip, after[:3]))
    page.fill("#q", "")
    page.wait_for_timeout(300)
    # ④ 按家族筛
    opts = page.evaluate("() => [...document.querySelectorAll('#ptfamf option')].map(o => o.value)"
                         ".filter(v => v)")
    if opts:
        page.select_option("#ptfamf", opts[0])
        page.wait_for_timeout(400)
        sel = page.evaluate("() => [...document.querySelectorAll('#ptsk tbody tr')]"
                            ".map(tr => (tr.querySelector('.w-tail')||{}).innerText || '')")
        check("「按家族筛」这个下拉选了真生效，且筛出来的每一行都写着那一族",
              0 < len(sel) < len(sks) and all(opts[0] in x for x in sel),
              "%s 行 / 选了 %s（下拉共 %s 项）" % (len(sel), opts[0], len(opts)))
        page.select_option("#ptfamf", "")
        page.wait_for_timeout(300)
    else:
        check("「按家族筛」这个下拉有可选项", False, "下拉是空的")
    # ⑤ 0 不空、图标真加载
    zero = page.evaluate("() => { const tds = [...document.querySelectorAll('#ptfam tbody tr')]"
                         ".map(tr => [...tr.querySelectorAll('.c-num2')].map(x => x.innerText.trim()));"
                         " return { has: tds.some(r => r.includes('0')), empty: tds.some(r => r.some(x => x === '')) }; }")
    check("三项修正里 0 显示成 0、没有空格子",
          zero["has"] and not zero["empty"], str(zero))
    imgs = page.evaluate("() => [...document.querySelectorAll('#ptfam tbody tr td.c-ico img')]"
                         ".map(i => ({ ok: i.complete && i.naturalWidth > 0, src: i.getAttribute('src') || '' }))")
    check("18 个家族的图标都从本地 img/icons 出且真加载出来",
          len(imgs) == len(fams) and all(i["ok"] for i in imgs)
          and all(i["src"].startswith("img/icons/") or "/img/icons/" in i["src"] for i in imgs),
          "%s/%s 张" % (sum(1 for i in imgs if i["ok"]), len(fams)))
    cells = page.evaluate("() => [...document.querySelectorAll('#ptsk tbody tr')]"
                          ".map(tr => [...tr.querySelectorAll('td')].some(td => !td.innerText.trim()))")
    check("技能表没有空格子（缺值要写待实测，不许留白）", not any(cells), str(cells.count(True)))
    cd = page.evaluate("() => [...document.querySelectorAll('#ptsk tbody tr')]"
                       ".map(tr => (tr.querySelectorAll('.c-num2')[3]||{}).innerText || '')")
    check("冷却为 0 的那几条显示「不用冷却」，不是「没写」",
          u"不用冷却" in cd and u"没写" not in cd, " / ".join(sorted(set(cd))))
    # ⑥ 红线：不许有整句描述（这一页本来就没有描述栏）
    body = page.evaluate("() => document.body.innerText")
    sent = [w for w in (u"造成", u"点伤害", u"使你的") if w in body]
    check("页面上没有成句的技能描述（插件的 dcn/den 一条没取）", not sent, "出现 %s" % sent)
    shot = os.path.join(SHOT_DIR, "pets-families.png")
    snap(page, path=shot, full_page=True)
    check("整页截图落盘", os.path.exists(shot), shot)
    ctx.close()


SECTIONS = [
    ("talent", test_talent),
    ("mobile", test_mobile),
    ("spellbook", test_spellbook),
    ("css_tokens", test_css_tokens),
    ("site_wide", test_site_wide),
    ("app", test_app),
    ("world_pins", test_world_pins),
    ("dungeon_geo", test_dungeon_geo),
    ("legacy_app", test_legacy_app),
    ("bis", test_bis),
    ("prof_tiers", test_prof_tiers),
    ("pets", test_pets),
    ("macros", test_macros),
    ("motion", test_motion),
    ("classes_sticky", test_classes_sticky),
    ("race_icon", lambda b, base: test_race_icon(b)),
    ("updates_filter", lambda b, base: test_updates_filter(b)),
    ("copy", test_copy),
    ("data_versions", test_data_versions),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", action="store_true",
                        help="已默认：2026-10-24 旧站删除后这一份只测新站，留着这个旗标只为兼容旧命令")
    parser.add_argument("--app-base", default="",
                        help="指到已经在跑的服务（如 :8821 的 vite preview 或线上地址）；"
                             "默认用本脚本自己起的静态服务打 app/dist")
    parser.add_argument("--only", default="",
                        help="只跑逗号指定的小节（如 talent,app），用于改断言时的快速探针")
    args = parser.parse_args()
    global APP_BASE, APP_REQUIRED
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
    # 显式给了 --app-base（或环境变量）就用那一台，并且连不上就算失败：
    # 那说明人已经在测另一份产物（preview / 线上），静默跳过会把整组断言打在空气上。
    given = args.app_base or os.environ.get("APP_BASE") or ""
    APP_BASE, APP_REQUIRED = (given or base), bool(given)
    print("被测：%s（%s）" % (APP_BASE, "--app-base 指定" if given else "本脚本起的静态服务，根目录 " + SRC))
    try:
        with sync_playwright() as p:
            # 开软件 GL：配装页那层 3D 要在无 GPU 的 headless 里也真渲染出来，
            # 不然那条"两帧对比"永远只能验到降级路径（2026-10-26 第一次跑就是没 WebGL，
            # 组件正常退回静态图，看着像功能坏了）。
            browser = p.chromium.launch(channel="chrome", headless=True, args=[
                "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
            for name, fn in todo:
                # 传进去的 base 就是 APP_BASE：这一份只有新站一个被测对象，
                # 留两个名字迟早会有某一节打错台（--app-base 时尤其明显）。
                fn(browser, APP_BASE)
            browser.close()
    finally:
        httpd.shutdown()

    failed = [n for n, ok, _ in results if not ok]
    print("\n===== 结果 =====")
    print("截图目录：%s" % SHOT_DIR)
    print("通过 %d / %d" % (len(results) - len(failed), len(results)))
    if notes:
        print("其中 %d 条是提示（375 那一档，站主 2026-10-25 定的暂不作门槛；改 MOBILE_SOFT 可恢复拦红）："
              % len(notes))
        print("  - " + "\n  - ".join(notes[:8]))
    if failed:
        print("失败项：\n  - " + "\n  - ".join(failed))
        sys.exit(1)
    print("全部通过")


if __name__ == "__main__":
    main()
