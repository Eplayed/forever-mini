#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视觉回归基线（docs/PLAN-open-items.md 第 10 条欠账）。

site-check.py 查的是结构与文案，改完之后"页面还是不是那个页面"没有任何机器能判——
这一份补的就是像素那一层：验收通过时把当时那一版冻成基线，之后再改版就跑一次比对，
超过阈值必须逐条解释或重冻基线。

2026-10-24 旧站删除：这一份从"拍 src/ 那 16 个静态页"改成"拍 app/dist 的那 21 条路由"。
副作用是**没法再用 git archive 取历史版本**——dist 是构建产物，不在 git 里，
所以 --rev 只剩 WORKTREE；比历史版本要先把仓库切回那一版、构建、再 --make。

    cd app && npm run build                         # 先构建：这一份拍的就是 dist
    python3 tools/visual-check.py --make            # 冻结/刷新基线
    python3 tools/visual-check.py --check           # 与基线比对，非 0 即回归
    python3 tools/visual-check.py --make --only index,dungeons   # 只跑两页，调试用

三个不显然但决定成败的做法，都写在下面函数里：
1. **拍之前必须构建**。dist 落后于源码时，基线冻的是旧产物（2026-10-21 那次发出去的
   releases.json 少一条就是这么来的）；所以没 dist 直接退出，不拿半成品当标准。
2. **拍之前把会变的字按掉**：倒计时每秒一跳（`#lchip` / `#cdD` / `#cdT`）、卡片入场动画
   进度不定、懒加载图取不到就留占位块。这三处不归一，同一份代码两次截图都能对不上，
   工具就成了噪音机。清掉所有定时器后写死成等宽占位，宽度不变所以不会引起重排。
3. **基线降采样存**（默认 0.5）：整页 PNG 一页 1–3 MB，16 页 × 2 视口会吃掉几十 MB 仓库；
   布局错位、色相走偏、圆角与字号变了在 50% 下照样看得见，代价是小数点级间距差看不见——
   那种本来就该由 site-check 的尺寸断言管，不归这里。

阈值默认：单页变化像素占比 > 0.4%（阈值以下算渲染噪音）。尺寸对不上直接失败，
因为尺寸差就是布局动了，这是最有用的那一个信号。
"""
import argparse
import atexit
import datetime
import functools
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import zlib

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("缺少 playwright：pip3 install playwright")
try:
    from PIL import Image, ImageChops
except ImportError:
    sys.exit("缺少 Pillow：pip3 install pillow")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(ROOT, "docs", "screenshots", "baseline")
DIST = os.path.join(ROOT, "app", "dist")


def routes_from_router():
    """要拍的页 = app/src/router.js 里的路由，不是磁盘上的 html。
       2026-10-24 旧站删除：这一份以前拍的是 src/ 那 16 个静态页，
       写死名单的结果是"新站加了一页，视觉回归却不知道它存在"。"""
    src = open(os.path.join(ROOT, "app", "src", "router.js"), encoding="utf-8").read()
    block = re.search(r"const routes = \[(.*?)\n\];", src, re.S).group(1)
    out = []
    for path in re.findall(r"\{\s*path:\s*'([^']+)'", block):
        if ":all" in path:
            continue
        out.append((path.strip("/").replace("/", "-") or "index", path))
    return out


ROUTES = routes_from_router()
PAGES = [n for n, _ in ROUTES]
ROUTE_OF = dict(ROUTES)

VIEWS = {"desktop": (1440, 1000), "mobile": (375, 812)}
# 会变的地方：清掉定时器后写死成等宽占位文字，宽度不变就不引起重排
FREEZE = """() => {
  for (let i = 1; i < 20000; i++) { clearInterval(i); clearTimeout(i); }
  const set = (sel, txt) => document.querySelectorAll(sel)
    .forEach(e => { e.textContent = txt; });
  set('#lchip', '距上线 00 天 00:00:00');
  set('#cdD', '00'); set('#cdT', '00:00:00');
  document.querySelectorAll('img[loading]').forEach(i => { i.loading = 'eager'; });
  const st = document.createElement('style');
  st.textContent = '*,*::before,*::after{animation:none!important;transition:none!important}';
  document.head.appendChild(st);
}"""

# 计算样式指纹：每个关键选择器**实际生效**的值（不是源码怎么写的）。
# 加这一层的直接原因是一次实测：把 .card 的圆角从 3px 改成 8px，卡片四角在 0.5 倍图上一共
# 只动了不到 200 个像素，像素判据报的是 0.00%（看不见），而"硬边 3px"正是 2026-10-11
# 定下的改版决策之一——这种"决策被改回去却悄无声息"的回归，只有比生效值才抓得住。
# 选这些选择器是因为它们各自扛着一条定下的规矩，且 16 页里都在：
#   令牌值 / body 底与字体 / H1 与 H2 的排印 / 卡面与圆角 / 导航当前项 / 链接色 /
#   分级徽标 L0–L3 各自的颜色与形状 / 来源轨 / 控件圆角与命中区。
FP_TOKENS = ["--bg", "--panel", "--panel-2", "--elev", "--line", "--line-2", "--txt",
             "--txt-dim", "--txt-muted", "--accent", "--accent-deep", "--gold", "--orange",
             "--orange-ring", "--q0", "--q1", "--q2", "--q3", "--q4", "--q5",
             "--r-card", "--r-ctl", "--font-body", "--font-display", "--font-cn"]
FP = """(tk) => {
  const cs = (sel, props) => { const e = document.querySelector(sel); if (!e) return null;
    const s = getComputedStyle(e); const o = {};
    props.forEach(p => { o[p] = (s[p] || '').replace(/\\s+/g, ' ').trim(); }); return o; };
  const ty = ['color','backgroundColor','borderTopColor','borderLeftColor','borderRadius',
              'width','height','backgroundImage'];
  const ty2 = ['color','backgroundColor','borderColor','borderWidth','borderRadius',
               'boxShadow','padding','backgroundImage'];
  const tp = ['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','color',
              'textTransform','fontVariantNumeric'];
  const root = getComputedStyle(document.documentElement);
  const out = { tokens: {}, body: null, h1: null, h2: null, card: null, navOn: null,
                navOff: null, link: null, ctl: null, rail: null, pills: {}, chip: null };
  tk.forEach(k => out.tokens[k] = (root.getPropertyValue(k) || '').trim());
  out.body = cs('body', ['backgroundColor','color','fontFamily','fontSize','lineHeight']);
  out.h1 = cs('#main h1', tp);
  out.h2 = cs('#main h2', tp);
  out.card = cs('#main .card', ty2);
  out.navOn = cs('nav.main .nl.on, nav.main a.on', [...ty, 'textDecorationLine']);
  out.navOff = cs('nav.main .nl:not(.on), nav.main a:not(.on)', [...ty, 'textDecorationLine']);
  out.link = cs('#main p a, #main a', ['color','textDecorationLine','fontWeight']);
  out.ctl = cs('button, input[type=submit]', ['borderRadius','backgroundColor','color',
                                              'borderColor','fontSize','minHeight']);
  out.rail = cs('#main .rail', ['borderLeftWidth','borderLeftColor','backgroundImage','width']);
  out.chip = cs('.chip', ['borderRadius','backgroundColor','color','fontSize']);
  ['L0','L1','L2','L3'].forEach(k => out.pills[k] = cs('#main .pill.' + k, ty));
  return out;
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def handle_exception(self, exc):
        if not isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            http.server.BaseHTTPRequestHandler.handle_exception(self, exc)


class ThreadingServer(socketserver.ThreadingTCPServer):
    """必须多线程：单线程会被上一个页面的 keep-alive 连接卡住。"""
    daemon_threads = True
    allow_reuse_address = True


def start_server(src):
    httpd = ThreadingServer(("127.0.0.1", 0),
                            functools.partial(QuietHandler, directory=src))
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, "http://127.0.0.1:%d" % port


def start_server(src):
    httpd = ThreadingServer(("127.0.0.1", 0),
                            functools.partial(QuietHandler, directory=src))
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, "http://127.0.0.1:%d" % port


def clean_checkout(rev):
    """把某个提交里的 src 单独取到 /tmp，避开正在被改的工作区。
       用 git archive 而不是 worktree：仓库根是 monorepo 上一层，worktree 会把整个树
       （含几百张历史截图）落一遍盘，这台机磁盘长期 95%+；archive 只解 src，约 18 MB。"""
    top = subprocess.run(["git", "-C", ROOT, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    if not top:
        sys.exit("拿不到 git 仓库根")
    rel = os.path.relpath(ROOT, top)               # wow-forever-web
    tmp = os.path.join("/tmp", "visual-check-%s-%d"
                       % (re.sub(r"[^0-9a-z]", "-", rev.lower())[:16], os.getpid()))
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    ar = subprocess.Popen(["git", "-C", top, "archive", "--format=tar", rev, rel],
                          stdout=subprocess.PIPE)
    ex = subprocess.Popen(["tar", "-x", "-C", tmp], stdin=ar.stdout)
    ar.stdout.close()
    if ex.wait() != 0 or ar.wait() != 0:
        sys.exit("取 %s 的 src 失败（git archive 非 0）" % rev)
    atexit.register(lambda: shutil.rmtree(tmp, ignore_errors=True))
    return os.path.join(tmp, rel, "src")


def settle(page):
    """等渲染稳定：DOM 由 JS 现填，来源轨靠 MutationObserver 补，字体 swap 会二次重绘。"""
    page.wait_for_load_state("networkidle")
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(1400)
    page.evaluate(FREEZE)
    try:
        page.wait_for_function(
            "() => [...document.images].every(i => i.complete)", timeout=12000)
    except Exception:
        pass
    page.wait_for_timeout(250)


def capture(src, out_dir, names, views, scale, pixels=True):
    """取"计算样式指纹"（每页每视口一组生效值），按需再存像素图。
       像素基线是本机资产，指纹是那一半可以进仓库、跨机器比的。"""
    os.makedirs(out_dir, exist_ok=True)
    httpd, base = start_server(src)
    shots, fps = [], {}
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(channel="chrome", headless=True)
            for view, (w, h) in ((v, VIEWS[v]) for v in views):
                ctx = br.new_context(viewport={"width": w, "height": h},
                                     device_scale_factor=1, is_mobile=(view == "mobile"))
                pg = ctx.new_page()
                bad = []
                pg.on("requestfailed", lambda r: bad.append(r.url))
                for name in names:
                    pg.goto("%s/#%s" % (base, ROUTE_OF[name]), wait_until="networkidle")
                    settle(pg)
                    key = "%s-%s" % (view, name)
                    fps[key] = pg.evaluate(FP, FP_TOKENS)
                    if bad:
                        print("  ！%s 有失败请求 %d 个（%s）"
                              % (key, len(bad), bad[0].split("/")[-1][:30]))
                        bad.clear()
                    if not pixels:
                        continue
                    path = os.path.join(out_dir, key + ".png")
                    pg.screenshot(path=path, full_page=True)
                    im = Image.open(path)
                    if scale != 1.0:
                        im = im.resize((max(1, int(im.width * scale)),
                                        max(1, int(im.height * scale))), Image.LANCZOS)
                    im.save(path, optimize=True)
                    shots.append(os.path.basename(path))
                ctx.close()
            br.close()
    finally:
        httpd.shutdown()
    return shots, fps


def rev_info(rev):
    r = subprocess.run(["git", "-C", ROOT, "rev-parse", rev], capture_output=True, text=True)
    sha = r.stdout.strip() or rev
    d = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%cd", "--date=short", sha],
                       capture_output=True, text=True)
    return sha, d.stdout.strip()


def cmd_make(args, src):
    shots, fps = capture(src, args.baseline, args.only, args.views, args.scale,
                         pixels=not args.only_fingerprint)
    json.dump({"rev": args.rev, "madeAt": datetime.datetime.now().isoformat(timespec="seconds"),
               "pages": fps},
              open(args.fingerprint, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              sort_keys=True)
    sha, dat = rev_info(args.rev if args.rev != "WORKTREE" else "HEAD")
    meta = {"rev": args.rev, "commit": sha[:12], "commitDate": dat,
            "madeAt": datetime.datetime.now().isoformat(timespec="seconds"),
            "scale": args.scale, "views": args.views,
            "threshold": {"area": args.max, "mad": args.mad_max, "pixel": args.pixel_thresh},
            "files": {}}
    for f in shots:
        im = Image.open(os.path.join(args.baseline, f))
        meta["files"][f] = {"w": im.width, "h": im.height}
    json.dump(meta, open(os.path.join(args.baseline, "baseline.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1)
    total = sum(os.path.getsize(os.path.join(args.baseline, f)) for f in shots)
    print("基线：指纹 %d 页 → %s%s"
          % (len(fps), args.fingerprint,
             ("；像素 %d 张 / %.1f MB → %s" % (len(shots), total / 1048576.0, args.baseline))
             if shots else "（这一轮没取像素）"))
    print("      来自 %s（%s，提交 %s）" % (args.rev, dat, sha[:9]))
    return 0


def compare(path_a, path_b, thresh):
    """返回 (基线尺寸, 本次尺寸, 变化像素占比, 平均色差, 差异包围盒)。
       尺寸不同算不出占比，后三项返回 None——尺寸差本身就是布局动了，直接判失败。"""
    a, b = Image.open(path_a).convert("RGB"), Image.open(path_b).convert("RGB")
    if a.size != b.size:
        return a.size, b.size, None, None, None
    d = ImageChops.difference(a, b).convert("L")
    # 只数超过阈值的像素，抗字体抗锯齿与 subpixel 抖动
    hist = d.histogram()
    over = sum(hist[i] for i in range(thresh + 1, 256))
    mad = sum(i * hist[i] for i in range(256)) / float(a.width * a.height)
    return a.size, b.size, over / float(a.width * a.height), mad, d.getbbox()


def write_diff(path_a, path_b, out_dir, name):
    a, b = Image.open(path_a).convert("RGB"), Image.open(path_b).convert("RGB")
    if a.size != b.size:
        h = max(a.height, b.height)
        cv = Image.new("RGB", (a.width + b.width + 8, h), (255, 0, 255))
        cv.paste(a, (0, 0)); cv.paste(b, (a.width + 8, 0))
        os.makedirs(out_dir, exist_ok=True)
        cv.save(os.path.join(out_dir, name))
        return
    d = ImageChops.difference(a, b).convert("L")
    # 放大 3 倍再着色，免得人眼看不出 1 个通道的色相漂移
    d = d.point(lambda v: min(255, v * 3))
    os.makedirs(out_dir, exist_ok=True)
    red = Image.merge("RGB", (d, Image.new("L", d.size, 0), Image.new("L", d.size, 0)))
    red.save(os.path.join(out_dir, name), optimize=True)


def fp_flatten(obj, pre=""):
    """把指纹字典摊平成 (路径, 值)，好把差异报到行上。"""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(fp_flatten(v, pre + "." + k if pre else k))
    else:
        out[pre] = obj
    return out


def fp_diff(base, now):
    """逐页逐键比生效值。返回 [{页, 键, 基线, 本次}]。"""
    hits = []
    for page in sorted(set(base) | set(now)):
        b, n = base.get(page), now.get(page)
        if b is None or n is None:
            hits.append({"页": page, "键": "（整页）",
                         "基线": "缺" if b is None else "有", "本次": "缺" if n is None else "有"})
            continue
        fb, fn = fp_flatten(b), fp_flatten(n)
        for k in sorted(set(fb) | set(fn)):
            if fb.get(k) != fn.get(k):
                hits.append({"页": page, "键": k,
                             "基线": fb.get(k, "（没这个键）"), "本次": fn.get(k, "（没这个键）")})
    return hits


def cmd_check(args, src):
    meta_path = os.path.join(args.baseline, "baseline.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else None
    if not args.only_fingerprint and meta is None:
        sys.exit("还没有像素基线：先跑 --make（或改用 --only-fingerprint 只比生效值）")
    if not os.path.exists(args.fingerprint):
        print("！没有指纹文件 %s，这一层跳过（跑一次 --make 生成）" % args.fingerprint)
    tmp = os.path.join("/tmp", "visual-check-new-%d" % os.getpid())
    shots, fps = capture(src, tmp, args.only, args.views, args.scale,
                         pixels=not args.only_fingerprint)
    if meta:
        print("像素基线来自 %s（提交 %s，%s 冻结）｜本次取图 %s"
              % (meta["commit"], meta["rev"], meta["madeAt"][:10], args.rev))
    rows, fails = [], []
    for name in [] if args.only_fingerprint else shots:
        p_base = os.path.join(args.baseline, name)
        if not os.path.exists(p_base):
            fails.append((name, "基线里没这张（新增视口或改了页名，需 --make 重冻）"))
            continue
        size, size_b, ratio, mad, box = compare(p_base, os.path.join(tmp, name), args.pixel_thresh)
        if ratio is None:
            fails.append((name, "尺寸不同：基线 %dx%d，本次 %dx%d（布局高度变了就是改版）"
                          % (size[0], size[1], size_b[0], size_b[1])))
            write_diff(p_base, os.path.join(tmp, name), args.diff_dir, "diff-" + name)
            continue
        # 两个判据各管一类毛病：
        #   占比——有多少像素被改动，抓"某个块挪了 / 某条线没了"；
        #   平均色差 MAD——整页均匀染色，占比可以是 0.00% 而 MAD 立刻起来
        #     （实测把 --bg 从 #101010 改成 #161616：占比 0.00%，MAD 1.92，单看占比会漏）。
        why = []
        if ratio > args.max:
            why.append("变化像素 %.2f%% > %.2f%%" % (ratio * 100, args.max * 100))
        if mad > args.mad_max:
            why.append("平均色差 %.2f > %.2f" % (mad, args.mad_max))
        rows.append((name, size, ratio, mad, not why))
        if why:
            fails.append((name, "｜".join(why) + "｜差异区 %s" % (box,)))
            write_diff(p_base, os.path.join(tmp, name), args.diff_dir, "diff-" + name)
    print("%-22s %-14s %8s %7s" % ("页", "尺寸", "变化", "色差") if rows else "（--only-fingerprint：不取像素）")
    for name, size, ratio, mad, ok in rows:
        print("%-22s %-14s %7.2f%% %6.2f %s"
              % (name, "%dx%d" % size, ratio * 100, mad, "" if ok else "✗"))
    if fails:
        print("\n像素层不通过 %d 张：" % len(fails))
        for name, why in fails:
            print("  ✗ %s — %s" % (name, why))
        print("差异图 → %s（红色=逐像素差，放大 3 倍；品红=左右并排，尺寸不同）" % args.diff_dir)
    # 第二层：生效值指纹。像素看不见的小改动（圆角 3→8px 实测占比 0.00%）在这一层是明晃晃一行
    fp_fails = []
    if os.path.exists(args.fingerprint):
        base = json.load(open(args.fingerprint, encoding="utf-8"))["pages"]
        hits = fp_diff(base, fps)
        if hits:
            print("\n生效值指纹差异 %d 处：" % len(hits))
            for hh in hits[:40]:
                print("  ✗ %s ｜ %s ｜ 基线 %s → 本次 %s"
                      % (hh["页"], hh["键"], hh["基线"], hh["本次"]))
            if len(hits) > 40:
                print("  …还有 %d 处" % (len(hits) - 40))
            fp_fails = hits
        else:
            print("\n生效值指纹：%d 页 %d 键全部一致"
                  % (len(fps), len(fp_flatten(list(fps.values())[0]))))
    return 1 if (fails or fp_fails) else 0


def main():
    ap = argparse.ArgumentParser(description="页面像素级视觉回归（基线在 docs/screenshots/baseline/）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--make", action="store_true", help="冻结当前版本为基线")
    g.add_argument("--check", action="store_true", help="与基线比对")
    ap.add_argument("--rev", default="WORKTREE",
                    help="只能 WORKTREE（当前工作区构建出的 app/dist）；旧站删了以后"
                         "这一份拍的是构建产物，git archive 取不到 dist，要比历史版本请先切回去再 --make")
    ap.add_argument("--src", help="直接指定要服务的目录（跳过构建检查，测试用）")
    ap.add_argument("--only", default="", help="逗号分隔的页名，默认 16 页全跑")
    ap.add_argument("--views", nargs="+", default=list(VIEWS), choices=list(VIEWS))
    ap.add_argument("--scale", type=float, default=0.5, help="存图降采样比例（默认 0.5）")
    ap.add_argument("--max", type=float, default=0.004, help="变化像素占比阈值（默认 0.004）")
    ap.add_argument("--mad-max", type=float, default=0.35,
                    help="平均色差阈值，管整页均匀染色（默认 0.35；同一份代码两次取图实测 0.00）")
    ap.add_argument("--pixel-thresh", type=int, default=24, help="单像素算“变了”的色差下限（0-255）")
    ap.add_argument("--baseline", default=BASE_DIR)
    ap.add_argument("--fingerprint", default=os.path.join(ROOT, "docs", "visual-fingerprint.json"),
                    help="生效值指纹文件（文本，进仓库；像素基线不进仓库）")
    ap.add_argument("--only-fingerprint", action="store_true",
                    help="只比生效值，不取也不比像素图（跨机器可用，快一倍）")
    ap.add_argument("--diff-dir", default=os.path.join(ROOT, "docs", "screenshots",
                                                       "visual-diff-" + datetime.date.today().isoformat()))
    args = ap.parse_args()
    args.only = [p.strip() for p in args.only.split(",") if p.strip()] or PAGES
    unknown = [p for p in args.only if p not in PAGES]
    if unknown:
        sys.exit("页名不在 PAGES 里：%s" % unknown)
    if args.src:
        src = os.path.abspath(args.src)
    elif args.rev != "WORKTREE":
        sys.exit("--rev 现在只认 WORKTREE：被测的是 app/dist（构建产物），"
                 "git 里没有这一份。要比历史版本，先 git checkout 过去、npm run build、再 --make 冻基线。")
    else:
        src = DIST
    if not os.path.isdir(src):
        sys.exit("没有 %s：先 cd app && npm run build（视觉回归拍的是构建产物）" % src)
    sys.exit(cmd_make(args, src) if args.make else cmd_check(args, src))


if __name__ == "__main__":
    main()
