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
    const dist = Math.max((size.y / 2) / half, (wide / 2) / half / cam.aspect) * 1.18
    cam.position.set(c.x + dist, c.y, c.z)
    cam.lookAt(c.x, c.y, c.z)
    /* 不用 requestAnimationFrame 等"画够几帧"：无头浏览器这一页不在前台，
       rAF 会被节流，第一版就是卡在这里——25 秒到点也没有 ready，且一条错误都不报。
       改成定时重画两次再置标志，和前台可见性无关。 */
    renderer.render(scene, cam)
    setTimeout(() => { renderer.render(scene, cam); setTimeout(() => { renderer.render(scene, cam); window.__ready = true }, 200) }, 200)
  } catch (e) { window.__err = String(e && e.message || e); window.__ready = true }
}, undefined, (e) => { window.__err = 'load 失败 ' + (e && e.message || e); window.__ready = true })
</script></body></html>""".replace("__W__", str(W)).replace("__H__", str(H))


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
    if not os.path.isfile(INDEX):
        raise SystemExit("找不到 B1 索引：" + INDEX)
    if not os.path.isdir(THREE):
        raise SystemExit("找不到 three：" + THREE)
    reps = pick_reps()
    print("按种族选出的代表件：")
    for r in sorted(reps):
        print("  %-10s ← %s/%s  %s" % (r, reps[r]["setId"], reps[r]["faction"], reps[r]["file"]))

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
        for race in sorted(reps):
            m = reps[race]
            url = "http://127.0.0.1:%d/render.html?file=%s" % (port, quote("models/" + m["file"]))
            del errs[:]          # 清在 goto 之前：清在等待之后就把自己抓到的错误扔了（第一版就这么瞎了）
            page.goto(url)
            try:
                page.wait_for_function("window.__ready === true", timeout=25000)
                err = page.evaluate("window.__err")
                if err:
                    raise RuntimeError(str(err))
                png = os.path.join(out, race + "-tmp.png")
                # 元素截图会把页面底色一起合成进去（第一版量到"整张不透明"就是这个）；
                # 要透明底必须走 omit_background，让 PNG 真的带 alpha
                page.screenshot(path=png, omit_background=True, clip={"x": 0, "y": 0, "width": W, "height": H})
                check = verify(png)
                if check:
                    raise RuntimeError(check)
                sha = sha256_file(png)
                named = os.path.join(out, race + "-" + sha[:12] + ".png")
                os.replace(png, named)
                png = named
                manifest[race] = {
                    "file": os.path.basename(png), "bytes": os.path.getsize(png), "sha256": sha,
                    "width": W, "height": H, "sourceModel": {
                        "setId": m["setId"], "faction": m["faction"], "file": m["file"], "pngSha256": m["pngSha256"]
                    }
                }
                print("  ✓ %-10s %d B" % (race, manifest[race]["bytes"]))
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
               "rule": "每个种族取 B1 清单里 setId 排最前的那一件；相机按包围盒框整个人；背景透明",
               "count": len(manifest), "posters": manifest},
              open(os.path.join(OUT_DIR, "posters.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, sort_keys=True)
    total = sum(v["bytes"] for v in manifest.values())
    print("\n6 张全出：%d B 合计 → %s" % (total, os.path.relpath(OUT_DIR, REPO)))
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
    # 上下边缘不许碰到人：碰边说明脚或头被裁
    top = float((a[:6, :, 3] > 24).mean())
    bottom = float((a[-6:, :, 3] > 24).mean())
    if top > 0.01 or bottom > 0.01:
        return "人顶到画边（上 %.3f 下 %.3f），头或脚被裁" % (top, bottom)
    return None


if __name__ == "__main__":
    sys.exit(main())
