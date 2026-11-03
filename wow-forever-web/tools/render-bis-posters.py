#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给小程序配装页渲"这一种族穿着模型"的静态底图（2026-10-30 站主选的那一档：按种族 6 张）。

站主原话：默认那一格不要职业图标，要"模型装备的这个图片"，点「查看 3D」才是 3D。
他挑的口径是**按种族各一张**（不是 76 套各一张）——所以这里只渲 6 张，
每张取该种族在 B1 清单里 setId 排最前的那一件，规则写死、可重出。

它做的事：
  1) 读 B1 那份索引，按 raceId 选代表件（不猜、不手填）；
  2) 在 /tmp 里搭一个只读 web 根（软链 three 与模型目录），用系统 Chrome 无头渲染，
     相机按包围盒把**整个人**框进来（站主要的是"完整展示整体装备"，裁头裁脚都不行）；
  3) 出图带 alpha（背景透明），小程序那格自己铺 --panel 底色，不会出现两种底色；
  4) 每张独立回读校验：尺寸、非透明像素占比在合理区间、不是纯色一块——**图糊了/空了不算成功**；
  5) 产物落 for-mini/oss-build/beta/posters/（gitignore 的那一层，二进制不进 git），
     并写一份 posters.json 记 bytes/sha256/用的是哪一件模型，给上传与门禁对账用。

不发 OSS、不改页面：那是下一步（先让站主看图对不对，再谈上线）。
"""
import hashlib
import http.server
import json
import os
import shutil
import socket
import socketserver
import sys
import threading
from urllib.parse import quote

# 这台 Windows 的控制台默认是 GBK：这个脚本要打印 ✓/✗ 与中文，不重设编码的话
# 连"哪一件失败了"都打不出来（2026-11-01 实测：真实报错是缺 numpy，被 UnicodeEncodeError 盖掉了）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # wow-forever-web
REPO = os.path.dirname(ROOT)
BUILD = os.path.join(REPO, "for-mini", "oss-build", "beta")
INDEX = os.path.join(BUILD, "bis", "models", "index.json")
MODELS = os.path.join(BUILD, "models")
OUT_DIR = os.path.join(BUILD, "posters")
THREE = os.path.join(ROOT, "app", "node_modules", "three")
WWW = "/tmp/bis-poster-www"
W, H = 600, 800                                    # 与页面那一格的竖比例一致（3:4）
FIT_BASE = 1.18                                    # 起步取景余量，像素实测后可能再加
FIT_MAX_TRIES = 4                                  # 一张最多重渲几次
MARGIN_Y = 0.06                                    # 目标：上下各留 6% 画高（头与脚都不许贴边）
MARGIN_X = 0.04                                    # 目标：左右各留 4% 画宽
# 及格线故意比目标低一档，且放大后的 fit 往 0.02 的网格上取整：
# 2026-11-02 实测过不这么做的代价——按连续量收敛时，光栅噪声（±1 px）会让 fit 每次都差一点，
# 需要放大的那 15 张**每次重渲都换内容哈希**，于是"渲一次就要重构建一次、旧对象全成孤儿"。
# 有了网格 + 迟滞，同一批输入稳定落在同一档，只有真的换模型/换名单才改名。
FIT_STEP = 0.02
ACCEPT_Y = 0.05
ACCEPT_X = 0.03

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent}canvas{display:block}
</style></head><body><canvas id="c" width="__W__" height="__H__"></canvas>
<script type="importmap">{"imports":{"three":"./three/build/three.module.js","three/addons/":"./three/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
const p = new URLSearchParams(location.search)
const file = p.get('file')
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('c'), antialias: true, alpha: true })
renderer.setClearAlpha(0)
renderer.outputColorSpace = THREE.SRGBColorSpace
const scene = new THREE.Scene()
/* 与小程序那一格同一套光：环境 0.75 + 一盏方向光 2.2，位置角 30/120 —— 底图和 3D 差太多
   玩家点进去会以为换了个人 */
scene.add(new THREE.AmbientLight(0xffffff, 0.75))
const dir = new THREE.DirectionalLight(0xffffff, 2.2)
dir.rotation.set(Math.PI / 6, Math.PI * 2 / 3, 0)
scene.add(dir)
const cam = new THREE.PerspectiveCamera(32, __W__ / __H__, 0.05, 100)
window.__err = null
new GLTFLoader().load(file, (g) => {
  try {
    scene.add(g.scene)
    const box = new THREE.Box3().setFromObject(g.scene)
    const size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3())
    /* 整个人框进来：竖方向和横方向都要放得下（第一版只按竖直算，
       矮壮体型（牛头/兽人）横向溢出、脚还顶到画边，验图直接判了裁切） */
    const half = Math.tan((cam.fov * Math.PI) / 360)
    /* 这一批客户端导出的模型"正面"是朝 +X 的：从 +Z 看过去是侧脸（第一版渲出来
       兽人是正侧面、牛头人像躺着的，站主肯定不认）。xr-frame 那边看到的是正面，
       是因为它自己转了手性——底图这边要跟它同一视角，就得站到 +X 去。
       横向余量按 max(宽, 深) 算：牛头人那条尾巴往后伸得远。 */
    const wide = Math.max(size.x, size.z)
    /* 1.18 只是起步余量：Box3 不认蒙皮后的顶点（SkinnedMesh 报的是绑定姿势的框），
       个别模型画出来比这个框大得多——warlock/部落两件量到占 98.8% 画高、脚贴边。
       真正的取景由外面按渲染回来的像素迭代这个 fit（见 fitOf）。 */
    const dist = Math.max((size.y / 2) / half, (wide / 2) / half / cam.aspect) * Number(p.get('fit') || '__FIT__')
    cam.position.set(c.x + dist, c.y, c.z)
    cam.lookAt(c.x, c.y, c.z)
    /* 不用 requestAnimationFrame 等"画够几帧"：无头浏览器这一页不在前台，
       rAF 会被节流，第一版就是卡在这里——25 秒到点也没有 ready，且一条错误都不报。
       改成定时重画两次再置标志，和前台可见性无关。 */
    renderer.render(scene, cam)
    setTimeout(() => { renderer.render(scene, cam); setTimeout(() => { renderer.render(scene, cam); window.__ready = true }, 200) }, 200)
  } catch (e) { window.__err = String(e && e.message || e); window.__ready = true }
}, undefined, (e) => { window.__err = 'load 失败 ' + (e && e.message || e); window.__ready = true })
</script></body></html>""".replace("__W__", str(W)).replace("__H__", str(H)).replace("__FIT__", repr(FIT_BASE))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def pick_reps():
    idx = json.load(open(INDEX, encoding="utf-8"))
    best = {}
    for m in sorted(idx["models"], key=lambda x: x["setId"]):
        r = m["raceId"]
        if r not in best:
            best[r] = m
    return best


def pick_per_set():
    """按 setId+阵营 一件一图——站主 2026-11-01 定的新形态。
       按种族那张表为什么不能用：键是「职业|阵营」、值却是按种族渲的猎人那身，
       法师/牧师看到的是猎人的装备，等于拿别的套装冒充当前套（红线）。"""
    idx = json.load(open(INDEX, encoding="utf-8"))
    return {(m["setId"] + "/" + m["faction"]): m for m in sorted(idx["models"], key=lambda x: (x["setId"], x["faction"]))}


def serve(directory, port):
    class Q(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)

        def log_message(self, *a):
            pass
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", port), Q)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-set", action="store_true",
                    help="按 setId+阵营 一件一图（新形态；默认那条按种族的旧规则只出 6 张，会把猎人那身发给所有职业）")
    ap.add_argument("--only", default="",
                    help="只渲清单里的几件，逗号分隔，如 warrior/alliance,mage/horde——先看样图用")
    args = ap.parse_args()
    if not os.path.isfile(INDEX):
        raise SystemExit("找不到 B1 索引：" + INDEX)
    if not os.path.isdir(THREE):
        raise SystemExit("找不到 three：" + THREE)
    reps = pick_per_set() if args.per_set else pick_reps()
    if args.only:
        want = [x.strip() for x in args.only.split(",") if x.strip()]
        missing = [w for w in want if w not in reps]
        if missing:
            raise SystemExit("--only 里有不存在的件：" + "、".join(missing) + "（可用的键前几个：" + "、".join(sorted(reps)[:6]) + "…）")
        reps = {w: reps[w] for w in want}
    print(("按 setId+阵营 逐件" if args.per_set else "按种族选出的代表件") + "：")
    for r in sorted(reps):
        print("  %-26s ← %s/%s  %s" % (r, reps[r]["setId"], reps[r]["faction"], reps[r]["file"]))

    if os.path.isdir(WWW):
        shutil.rmtree(WWW)
    os.makedirs(WWW)
    # WWW/three 直接指向 three 这个包本身：页面里两条路径
    # three/build/three.module.js 与 three/examples/jsm/… 才对得上（第一版链到 node_modules，
    # 结果 GLTFLoader 404，只剩一句 Timeout——所以错误捕获那次也一起加了）
    os.symlink(THREE, os.path.join(WWW, "three"))
    os.symlink(MODELS, os.path.join(WWW, "models"))
    open(os.path.join(WWW, "render.html"), "w", encoding="utf-8").write(PAGE)
    out = "/tmp/bis-posters-out"
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    port = free_port()
    srv = serve(WWW, port)
    from playwright.sync_api import sync_playwright
    failures = []
    manifest = {}
    errs = []
    with sync_playwright() as pw:
        # 无头 Chrome 不放开 SwiftShader 就没有 WebGL 上下文，WebGLRenderer 构造即抛
        browser = pw.chromium.launch(channel="chrome", headless=True,
                                     args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader",
                                           "--disable-gpu-sandbox"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        # 光有 Timeout 答不出为什么；模块解析失败、GLB 404 都会静默卡住
        page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:200]))
        page.on("console", lambda m: errs.append("console." + m.type + ": " + m.text[:200])
                if m.type == "error" and "favicon" not in m.text else None)
        page.on("requestfailed", lambda r: errs.append("请求失败: " + r.url[-90:] + " " + str(r.failure)))
        for key in sorted(reps):
            m = reps[key]
            # 逐件模式下键是 "setId/阵营"，斜杠不能进文件名
            race = key.replace("/", "-")
            url0 = "http://127.0.0.1:%d/render.html?file=%s" % (port, quote("models/" + m["file"]))
            png = os.path.join(out, race + "-tmp.png")
            try:
                # 取景是按"渲染回来的像素"收敛的，不是一次算完（原因见 fit_of）
                fit = FIT_BASE
                for attempt in range(1, FIT_MAX_TRIES + 1):
                    del errs[:]      # 清在 goto 之前：清在等待之后就把自己抓到的错误扔了（第一版就这么瞎了）
                    page.goto(url0 + "&fit=%.4f" % fit)
                    page.wait_for_function("window.__ready === true", timeout=25000)
                    err = page.evaluate("window.__err")
                    if err:
                        raise RuntimeError(str(err))
                    # 元素截图会把页面底色一起合成进去（第一版量到"整张不透明"就是这个）；
                    # 要透明底必须走 omit_background，让 PNG 真的带 alpha
                    page.screenshot(path=png, omit_background=True, clip={"x": 0, "y": 0, "width": W, "height": H})
                    check = verify(png)
                    if check:
                        raise RuntimeError(check)
                    need, info = fit_of(png, fit)
                    if need is None:
                        break
                    if attempt == FIT_MAX_TRIES:
                        raise RuntimeError("重渲 %d 次仍框不住整个人｜最后一版 fit %.3f，%s" % (attempt, fit, info))
                    fit = need
                sha = sha256_file(png)
                named = os.path.join(out, race + "-" + sha[:12] + ".png")
                os.replace(png, named)
                png = named
                manifest[race] = {
                    "file": os.path.basename(png), "bytes": os.path.getsize(png), "sha256": sha,
                    "width": W, "height": H, "fit": round(fit, 4),
                    "sourceModel": {
                        "setId": m["setId"], "faction": m["faction"], "file": m["file"], "pngSha256": m["pngSha256"]
                    }
                }
                print("  ✓ %-10s %d B%s" % (race, manifest[race]["bytes"],
                                            "" if fit == FIT_BASE else "（取景放大到 %.2f）" % fit))
            except Exception as e:
                failures.append("%s → %s ｜ %s" % (race, e, " ; ".join(errs[:3]) or "页面没报错也没 ready"))
                print("  ✗ %-10s %s ｜ %s" % (race, e, " ; ".join(errs[:3]) or "页面没报错也没 ready"))
        browser.close()
    srv.shutdown()

    if failures:
        print("\n失败清单：\n  " + "\n  ".join(failures))
        print("状态：PARTIAL——一张没出全就不写清单")
        return 1
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)
    for race in manifest:
        shutil.copy2(os.path.join(out, manifest[race]["file"]), os.path.join(OUT_DIR, manifest[race]["file"]))
    json.dump({"product": "wow-forever-mini-model-posters", "kind": "bis-model-posters",
               "formatVersion": "png-alpha-v1", "dir": "assets/models/posters/",
               "rule": ("每件 setId+阵营 各一张（2026-11-02 站主定：小程序配装页全部换成这一档）" if args.per_set
                        else "每个种族取 B1 清单里 setId 排最前的那一件（旧规则：会把猎人那身发给所有职业）")
               + "；取景先按包围盒、再按渲染回来的像素迭代放大（fit 见每条），头脚不许贴边；背景透明",
               "count": len(manifest), "posters": manifest},
              open(os.path.join(OUT_DIR, "posters.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, sort_keys=True)
    total = sum(v["bytes"] for v in manifest.values())
    print("\n%d 张全出：%d B 合计 → %s" % (len(manifest), total, os.path.relpath(OUT_DIR, REPO)))
    print("清单 sha256", sha256_file(os.path.join(OUT_DIR, "posters.json"))[:12])
    print("状态：LOCAL_READY（未上传 OSS、未改页面）")
    return 0


def verify(png):
    """图糊了/空了/裁了都不算成功：非透明像素占比要在合理区间，且颜色不能是一整块"""
    from PIL import Image
    import numpy as np
    im = Image.open(png)
    if im.size != (W, H):
        return "尺寸不对 %s" % (im.size,)
    a = np.asarray(im.convert("RGBA")).astype(float)
    alpha = a[:, :, 3]
    ratio = float((alpha > 24).mean())
    if not (0.06 < ratio < 0.85):
        return "画面占比异常 %.3f（要么空了要么铺满＝裁了）" % ratio
    body = a[:, :, :3][alpha > 24]
    if body.size == 0:
        return "整张全透明"
    sat = float(np.std(body, axis=0).mean())
    if sat < 6:
        return "颜色几乎单一（std %.1f），像是没贴图的纯色模" % sat
    # 贴边（头/脚被裁）不在这里判：那是取景问题，交给 fit_of 迭代重渲，
    # 在这里判会让每一次收敛前的正常尝试都变成"失败"。
    return None


def alpha_box(png):
    """量"画出来的像素"的外接框，折成画宽/画高的比例（top/bottom/left/right 是留白）"""
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(png).convert("RGBA"))[:, :, 3]
    m = a > 24
    if not m.any():
        return None
    rows = np.where(m.any(1))[0]
    cols = np.where(m.any(0))[0]
    return {"top": rows.min() / float(H), "bottom": (H - 1 - rows.max()) / float(H),
            "left": cols.min() / float(W), "right": (W - 1 - cols.max()) / float(W),
            "half_v": (rows.max() - rows.min() + 1) / (2.0 * H),
            "half_h": (cols.max() - cols.min() + 1) / (2.0 * W)}


def fit_of(png, fit):
    """按实测像素决定要不要把相机推远：Box3 报的是绑定姿势的包围盒，
       蒙皮件画出来会比它大——warlock 部落那两件量到占 98.8% 画高、脚贴边（2026-11-02）。
       画面尺寸 ∝ 1/fit，所以需要的 fit = 旧 fit × (实测半高 / 允许的半高)。
       返回 (要用的 fit 或 None, 实测留白串)：None = 这一张及格（留白过 ACCEPT 那一档）。
       给新的 fit 往 FIT_STEP 网格上取整，理由见常量那一段（不让噪声改名）。"""
    b = alpha_box(png)
    if b is None:
        return None, "整张全透明"
    info = "上 %.3f 下 %.3f 左 %.3f 右 %.3f" % (b["top"], b["bottom"], b["left"], b["right"])
    if b["top"] >= ACCEPT_Y and b["bottom"] >= ACCEPT_Y and b["left"] >= ACCEPT_X and b["right"] >= ACCEPT_X:
        return None, info
    s = max(b["half_v"] / (0.5 - MARGIN_Y), b["half_h"] / (0.5 - MARGIN_X))
    want = fit * s
    steps = int((want - FIT_BASE) / FIT_STEP) + 1        # 向上取整到网格（不引 math，避免再动 import）
    return round(FIT_BASE + steps * FIT_STEP, 4), info


if __name__ == "__main__":
    sys.exit(main())
