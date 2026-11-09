#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""挂账①（2026-11-09 站主拍板）：首领头像本机客户端渲染管线。

给副本首领行补"这只怪长什么样"的方形头像。素材不是网上抓的，是本机 Forever 客户端
（1.60.1，CASC）里这只怪的 M2 模型渲出来的：displayId → CreatureDisplayInfo → M2 + skin
(LOD0) + BLP 贴图 → 静态 GLB（无骨骼动画，绑定姿势）→ 无头 Chrome 透明底截图 →
256×256 webp。配套提取脚本与探针在仓库外工作区（默认 C:\\GAME\\_wowf-export-work\\），
本脚本只吃提取产物，不碰 CASC。

范围（首批 18 + c3 扩展 2 = 20 张）：贴图来源分两类——首批走 CDI f27 调色板
（该 displayId 游戏内实际贴图）；c3 扩展批 f27 全空、改吃 M2 TXID chunk 自带 fdid。
扩展侦查 47 个候选，45 个照实落空（extend-verdict.json 留档：43 个是 HD 角色基础
模型、2 个地精身体贴图是占位 stub——真脸靠运行时部件组装，渲通用人模=冒充首领
长相，不干）。侦查前段还各有 26 个 displayId 不在本构建 CDI（领主大厅 4 首领在内，
新内容真源缺口）、45 个 xr 无 displayId，没进候选。

落位：app/img/art/bosses-m2/{bossId}.webp + manifest.json（来源链/构建号/哈希/核对日；
c3 起 manifest 按候选整表重建，有失败不覆写旧 manifest）。整目录删除即回退：
dungeons.json 里对应 portrait 置回 null 即可（由 oss-release 的反向卡口兜底：
指向不存在文件的地址过不了构建）。

用法：
  python render-boss-portraits.py                # 全量
  python render-boss-portraits.py --only infurnus stonespine
"""
import argparse
import hashlib
import http.server
import json
import os
import shutil
import socket
import socketserver
import struct
import sys
import tempfile
import threading

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                                   # wow-forever-web
REPO = os.path.dirname(ROOT)
OUT_DIR = os.path.join(ROOT, "app", "img", "art", "bosses-m2")
DJ = os.path.join(ROOT, "app", "data", "dungeons.json")

WORK = r"C:\GAME\_wowf-export-work"
M2DIR = os.path.join(WORK, "exporter", "dest-m2boss")
SKINDIR = os.path.join(WORK, "exporter", "dest-bosshead")
PNGDIR = os.path.join(WORK, "exporter", "dest-bosshead-png")
CANDS = os.path.join(WORK, "boss-portraits-2026-11-09", "boss-candidates.json")
# c3 扩展批（2026-11-09）：47 个首领 f27 全空，贴图改从 M2 TXID chunk 自带 fdid 取。
# 候选里直接带 bossId/sfid/txid/texFd/texSrc（extend_resolve.py + extend_skins.py 产出）。
EXT_CANDS = os.path.join(WORK, "boss-portraits-2026-11-09", "extend-candidates.json")
GAME = r"C:\GAME\World of Warcraft"

W = H = 512          # 渲染尺寸（超采样）
OUT_PX = 256         # 成品边长（icon-cell md=88rpx，2x retina 88px，256 留足余量）
FRAC_TOP = 0.18      # 取景：从模型顶往下 size.y*FRAC_TOP 处对焦
SPAN_FRAC = 0.60     # 取景：竖向可见高度 = size.y * SPAN_FRAC（头+胸）
PAD = 1.12           # 取景余量
ACCEPT_MIN = 0.04    # 及格线：非透明像素至少占 4%（空图/纯糊判失败）
ACCEPT_MAX = 0.90    # 顶天立地贴边判失败

# 逐只微调（2026-11-09 逐张目检定）：默认取景是"头胸特写"（frac 0.18 / span 0.60），
# 形态特殊的单独改。atal-alarion 默认档裁了头顶；targorr 是扁宽龟壳，按默认算出来的
# 相机太远，壳在画面里只有指甲盖大。
OVERRIDES = {
    "atal-alarion": {"frac": 0.26},
    "targorr-the-dread": {"span": 0.45, "frac": 0.30, "pad": 1.0},
    # 骷髅模型骨架长，默认头胸框收太远，收紧到头肩（c3 扩展批目检后加）
    "archivist-galford": {"span": 0.38, "frac": 0.12},
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def client_build():
    """客户端构建号：读 .build.info 的 Active 行 Version 列（如 1.60.1.70862）。"""
    info = open(os.path.join(GAME, ".build.info"), encoding="utf-8", errors="replace").read()
    rows = [r for r in info.splitlines() if r.strip()]
    if len(rows) >= 2:
        cols = rows[1].split("|")
        if len(cols) > 12:
            return cols[12].strip()
    return "unknown"


# ---------------- M2 / SKIN 解析（实测定案格式，见 VERIFY 第十一节） ----------------

def read_m2(path):
    d = open(path, "rb").read()
    assert d[0:4] == b"MD21", "magic " + repr(d[0:4])
    base = 8   # MD21 = magic + u32(md20_size) + 完整 MD20 载荷
    nVerts, ofsVerts = struct.unpack_from("<II", d, base + 0x3C)
    nTex, _ = struct.unpack_from("<II", d, base + 0x50)
    verts = []
    for i in range(nVerts):
        o = base + ofsVerts + i * 48
        x, y, z = struct.unpack_from("<3f", d, o)
        u, v = struct.unpack_from("<2f", d, o + 36)
        verts.append((x, y, z, u, v))
    return dict(verts=verts, nTex=nTex)


def read_skin(path):
    """SKIN 容器（对拍定案）：0x04 顶点重排表 / 0x0C 三角形索引 / 0x1C submesh(48B)。"""
    s = open(path, "rb").read()
    assert s[0:4] == b"SKIN", "magic " + repr(s[0:4])

    def arr(off):
        return struct.unpack_from("<II", s, off)

    nv, ov = arr(0x04)
    nt, ot = arr(0x0C)
    ns, os_ = arr(0x1C)
    skin_verts = struct.unpack_from("<%dH" % nv, s, ov)
    tris = struct.unpack_from("<%dH" % nt, s, ot)
    subs = []
    for i in range(ns):
        o = os_ + i * 48
        sid, level, vstart, vcount, istart, icount = struct.unpack_from("<6H", s, o)
        if level == 0:
            subs.append((istart, icount))
    return skin_verts, tris, subs


def build_glb(m2path, skinpath, pngpath, outpath):
    """静态 GLB：单 primitive（贴图槽 0），M2 Z-up → glTF Y-up。"""
    m2 = read_m2(m2path)
    skin_verts, tris, subs = read_skin(skinpath)
    used = set()
    for istart, icount in subs:
        for t in tris[istart:istart + icount]:
            used.add(skin_verts[t])
    order = sorted(used)
    remap = {v: i for i, v in enumerate(order)}
    tri_idx = []
    for istart, icount in subs:
        for t in tris[istart:istart + icount]:
            tri_idx.append(remap[skin_verts[t]])
    pos = [(m2["verts"][v][0], m2["verts"][v][1], m2["verts"][v][2]) for v in order]
    uvs = [(m2["verts"][v][3], m2["verts"][v][4]) for v in order]

    gp = []
    for (x, y, z) in pos:
        gp.extend([x, z, -y])
    minp = [min(gp[0::3]), min(gp[1::3]), min(gp[2::3])]
    maxp = [max(gp[0::3]), max(gp[1::3]), max(gp[2::3])]
    png = open(pngpath, "rb").read()

    def pad4(n):
        return (n + 3) & ~3

    off_uv = len(gp) * 4
    off_idx = off_uv + len(uvs) * 8
    off_png = pad4(off_idx + len(tri_idx) * 4)
    total = off_png + len(png)
    buf = bytearray(pad4(total))
    struct.pack_into("<%df" % len(gp), buf, 0, *gp)
    flat_uv = []
    for (u, v) in uvs:
        flat_uv.extend([u, 1.0 - v])
    struct.pack_into("<%df" % len(flat_uv), buf, off_uv, *flat_uv)
    struct.pack_into("<%dI" % len(tri_idx), buf, off_idx, *tri_idx)
    buf[off_png:off_png + len(png)] = png

    bvs = [
        {"buffer": 0, "byteOffset": 0, "byteLength": off_uv},
        {"buffer": 0, "byteOffset": off_uv, "byteLength": off_idx - off_uv},
        {"buffer": 0, "byteOffset": off_idx, "byteLength": off_png - off_idx},
        {"buffer": 0, "byteOffset": off_png, "byteLength": len(png)},
    ]
    accessors = [
        {"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
         "minimum": minp, "maximum": maxp},
        {"bufferView": 1, "componentType": 5126, "count": len(uvs), "type": "VEC2"},
        {"bufferView": 2, "componentType": 5125, "count": len(tri_idx), "type": "SCALAR"},
    ]
    gltf = {
        "asset": {"version": "2.0", "generator": "wowf boss portrait"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "TEXCOORD_0": 1},
                                    "indices": 2, "material": 0, "mode": 4}]}],
        "accessors": accessors,
        "materials": [{
            "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0.0,
                                     "roughnessFactor": 0.9},
            "doubleSided": True,
        }],
        "textures": [{"source": 0, "sampler": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9729, "wrapS": 33071, "wrapT": 33071}],
        "images": [{"bufferView": 3, "mimeType": "image/png"}],
        "buffers": [{"byteLength": pad4(total)}],
        "bufferViews": bvs,
    }
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js = js + b" " * (pad4(len(js)) - len(js))
    total_len = 12 + 8 + len(js) + 8 + pad4(total)
    with open(outpath, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        f.write(struct.pack("<I4s", len(js), b"JSON"))
        f.write(js)
        f.write(struct.pack("<I4s", pad4(total), b"BIN\0"))
        f.write(buf)


# ---------------- 渲染 ----------------

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent}canvas{display:block}
</style></head><body><canvas id="c" width="__W__" height="__H__"></canvas>
<script type="importmap">{"imports":{"three":"./three/build/three.module.js","three/addons/":"./three/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
const p = new URLSearchParams(location.search)
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('c'), antialias: true, alpha: true })
renderer.setClearAlpha(0)
renderer.outputColorSpace = THREE.SRGBColorSpace
const scene = new THREE.Scene()
scene.add(new THREE.AmbientLight(0xffffff, 0.85))
const key = new THREE.DirectionalLight(0xffffff, 1.5)
key.position.set(2, 5, 3)
scene.add(key)
const rim = new THREE.DirectionalLight(0xffffff, 0.6)
rim.position.set(-3, 2, -3)
scene.add(rim)
const cam = new THREE.PerspectiveCamera(30, __W__ / __H__, 0.05, 500)
window.__err = null
new GLTFLoader().load(p.get('file'), (g) => {
  try {
    scene.add(g.scene)
    /* 按"实际被索引到的顶点"量框：静态 GLB 没这问题，但保留与 bis 底图同一套量法 */
    const box = new THREE.Box3().setFromObject(g.scene)
    const size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3())
    const target = new THREE.Vector3(c.x, box.max.y - size.y * Number(p.get('frac') || '__FRAC__'), c.z)
    const span = size.y * Number(p.get('span') || '__SPAN__')
    const half = Math.tan((cam.fov * Math.PI) / 360)
    const wide = Math.max(size.x, size.z) * Number(p.get('span') || '__SPAN__') * 1.6
    const dist = Math.max((span / 2) / half, (wide / 2) / half / cam.aspect) * Number(p.get('pad') || '__PAD__')
    const yaw = Number(p.get('yaw') || 0) * Math.PI / 180
    const pitch = Number(p.get('pitch') || 6) * Math.PI / 180
    cam.position.set(
      target.x + dist * Math.cos(pitch) * Math.cos(yaw),
      target.y + dist * Math.sin(pitch),
      target.z + dist * Math.cos(pitch) * Math.sin(yaw))
    cam.lookAt(target)
    renderer.render(scene, cam)
    setTimeout(() => { renderer.render(scene, cam); setTimeout(() => { renderer.render(scene, cam); window.__ready = true }, 150) }, 150)
  } catch (e) { window.__err = String(e && e.message || e); window.__ready = true }
}, undefined, (e) => { window.__err = 'load ' + (e && e.message || e); window.__ready = true })
</script></body></html>"""


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


def shot(page, url, path):
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:200]))
    page.goto(url)
    try:
        page.wait_for_function("window.__ready === true", timeout=25000)
    except Exception:
        raise RuntimeError("渲染超时 " + url)
    err = page.evaluate("window.__err")
    if err:
        raise RuntimeError("页面报错: " + err)
    page.screenshot(path=path, omit_background=True)
    return errs


def check_png(im):
    """成品复核：非透明占比在合理区间、色彩足够多。空图/纯糊/顶天立地都算失败。"""
    px = list(im.getdata())
    w, h = im.size
    opaque = sum(1 for p in px if p[3] > 24)
    ratio = opaque / (w * h)
    colors = len(set(p for p in px if p[3] > 24))
    ok = ACCEPT_MIN <= ratio <= ACCEPT_MAX and colors >= 32
    return ok, "ratio=%.3f colors=%d" % (ratio, colors)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="只渲这些 bossId")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    from PIL import Image

    cands = json.load(open(CANDS, encoding="utf-8"))
    dj = json.load(open(DJ, encoding="utf-8"))
    duns = (dj.get("newDungeons") or []) + (dj.get("classicDungeons") or []) + (dj.get("raids") or [])
    # slug + 首领中文名 -> bossId（数据基底的主键，成品文件名用）
    id_of = {}
    for dun in duns:
        for b in (dun.get("bosses") or []):
            id_of[(dun["id"], b.get("nameCn") or b.get("name"))] = b["id"]

    # 合并扩展批：bossId 直给，不占用首批候选的键
    ext = json.load(open(EXT_CANDS, encoding="utf-8"))

    build = client_build()
    # 统一候选形：bossId / texFd / texSrc 齐备。首批贴图走 f27 调色板，扩展批走 TXID。
    all_cands = []
    for c in cands:
        boss_id = id_of.get((c["slug"], c["boss"]))
        if not boss_id:
            continue
        f27nz = [t for t in (c.get("f27") or []) if t]
        all_cands.append(dict(bossId=boss_id, slug=c["slug"], boss=c["boss"],
                              displayId=c["displayId"], m2=c["m2"], sfid=c.get("sfid"),
                              texFd=f27nz[0] if f27nz else None, texSrc="f27" if f27nz else None))
    for c in ext:
        all_cands.append(dict(bossId=c["bossId"], slug=c["slug"], boss=c["boss"],
                              displayId=c["displayId"], m2=c["m2"], sfid=c.get("sfid"),
                              texFd=c.get("texFd"), texSrc=c.get("texSrc")))
    print("客户端构建:", build, " 候选: 首批 %d + 扩展 %d = %d" % (
        len(cands), len(ext), len(all_cands)))

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="bossport-")
    www = os.path.join(tmp, "www")
    os.makedirs(www)
    # web 根：three 从站点 node_modules 软链过来（bis 底图同一套）
    src_three = os.path.join(ROOT, "app", "node_modules", "three")
    if not os.path.isdir(src_three):
        raise SystemExit("缺 three（app/node_modules/three）——先 npm i")
    os.symlink(src_three, os.path.join(www, "three"))
    page_html = (PAGE.replace("__W__", str(W)).replace("__H__", str(H))
                 .replace("__FRAC__", repr(FRAC_TOP)).replace("__SPAN__", repr(SPAN_FRAC))
                 .replace("__PAD__", repr(PAD)))
    open(os.path.join(www, "shot.html"), "w", encoding="utf-8").write(page_html)

    port = free_port()
    srv = serve(www, port)
    manifest = {"meta": {
        "kind": "boss-portrait-m2",
        "clientBuild": build,
        "chain": "displayId -> CreatureDisplayInfo/模型链 -> M2+skin(LOD0)+BLP -> static GLB -> headless chrome",
        "texRule": "slot0 贴图：首批取 CDI f27 调色板（游戏内该 displayId 实际用的贴图）；"
                   "扩展批 f27 全空，取 M2 TXID chunk 自带的贴图 fdid（texSrc=txid）",
        "pose": "绑定姿势（无骨骼动画）；非游戏内截图，是客户端模型重渲",
        "generated": "2026-11-09",
        "fallback": "整目录删除 + dungeons.json portrait 置 null 即回退",
    }, "portraits": {}}

    fails = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            channel="chrome", headless=True,
            args=["--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--disable-gpu-sandbox"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)

        for c in all_cands:
            boss_id = c["bossId"]
            if args.only and boss_id not in args.only:
                continue
            m2p = os.path.join(M2DIR, "m2_%d.m2" % c["m2"])
            skin_fd = (c["sfid"] or [None])[0]
            tex_fd = c["texFd"]
            skinp = os.path.join(SKINDIR, "skin_%d.skin" % skin_fd)
            pngp = os.path.join(PNGDIR, "tex_%d.png" % tex_fd)
            try:
                glb = os.path.join(www, boss_id + ".glb")
                build_glb(m2p, skinp, pngp, glb)
                over = OVERRIDES.get(boss_id, {})
                qs = "&".join("%s=%s" % (k, v) for k, v in over.items())
                url = "http://127.0.0.1:%d/shot.html?file=%s.glb%s" % (
                    port, boss_id, ("&" + qs) if qs else "")
                raw = os.path.join(tmp, boss_id + ".png")
                shot(page, url, raw)
                im = Image.open(raw).convert("RGBA").resize((OUT_PX, OUT_PX), Image.LANCZOS)
                ok, info = check_png(im)
                if not ok:
                    fails.append((boss_id, c["boss"], "成品质检不过 " + info))
                    continue
                outp = os.path.join(OUT_DIR, boss_id + ".webp")
                im.save(outp, "WEBP", lossless=False, quality=90)
                manifest["portraits"][boss_id] = {
                    "dungeon": c["slug"], "boss": c["boss"], "displayId": c["displayId"],
                    "m2": c["m2"], "skin": skin_fd, "texSlot0": tex_fd,
                    "texSrc": c["texSrc"] or "f27",
                    "srcSha256": {"m2": sha256_file(m2p), "skin": sha256_file(skinp),
                                  "tex": sha256_file(os.path.join(SKINDIR, "tex_%d.blp" % tex_fd))},
                    "outSha256": sha256_file(outp), "outBytes": os.path.getsize(outp),
                    "quality": info,
                }
                print("✓ %-28s %-10s displayId=%-6d m2=%-7d tex=%-7d [%s] %s" % (
                    boss_id, c["boss"], c["displayId"], c["m2"], tex_fd,
                    c["texSrc"] or "f27", info))
            except Exception as e:
                fails.append((boss_id, c["boss"], str(e)[:120]))
                print("✗ %-28s %s" % (boss_id or c["boss"], str(e)[:120]))

        browser.close()
    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

    mpath = os.path.join(OUT_DIR, "manifest.json")
    # c3 起 manifest 按本轮候选整表重建（all_cands 就是全部应存在的头像）；
    # 有失败不覆写旧 manifest，避免半成品批次悄悄上线。
    if fails and os.path.exists(mpath):
        print("有失败，保留旧 manifest 不覆写")
    else:
        json.dump(manifest, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\nmanifest:", mpath, " 共 %d 张" % len(manifest["portraits"]))
    if fails:
        print("失败 %d：" % len(fails))
        for f in fails:
            print(" ", f)
        raise SystemExit(1)


main()
