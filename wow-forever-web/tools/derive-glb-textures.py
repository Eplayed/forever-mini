#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把已登记的真实整人 GLB 转一份"微信 xr-frame 兼容候选"：只换贴图编码，不改几何。

为什么要有这一步（2026-10-30 探针）：客户端导出的 GLB 把 10 张内嵌贴图写成 WebP，
并按 glTF 规则声明 `extensionsRequired: ["EXT_texture_webp"]`。微信基础库自带的
glTF 加载器里没有这个扩展的实现，且它的逻辑是"required 扩展不认识就直接抛"
（`[GLTF]required extension "x" not supported.`），所以这份原件在微信端注定读不出来。

本脚本做的唯一改动：把每张内嵌 WebP 原图解码后重新编成 PNG，写回 BIN，
`images[].mimeType` 改 `image/png`，`textures[].extensions.EXT_texture_webp.source`
搬回标准字段 `source`，并删掉 `extensionsUsed/Required` 里的这一项。
顶点、索引、材质参数、节点、包围盒一律照搬。PNG 分支逐像素一致；
JPEG 有损且不支持透明像素，透明图遇到 JPEG 会直接停止。

来源与红线：输入必须是 art.json.bisRealModels 里已登记且 placementVerdict=PASS 的那一份，
脚本会先核 SHA；产物只是**候选**，未经真机验证不得当成已支持（见 VERIFY 文档）。
"""
import argparse
import copy
import hashlib
import io
import json
import os
import struct
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "app")
DATA = os.path.join(WEB, "data", "art.json")
CHUNK_HDR = 8


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def read_glb(path):
    raw = open(path, "rb").read()
    magic, ver, total = struct.unpack("<4sII", raw[:12])
    if magic != b"glTF" or ver != 2:
        raise SystemExit("不是 glTF 2.0 二进制：%s magic=%r ver=%d" % (path, magic, ver))
    if total != len(raw):
        raise SystemExit("声明长度 %d ≠ 实际 %d" % (total, len(raw)))
    off = 12
    json_chunk = None
    bin_chunk = b""
    while off < len(raw):
        clen, ctype = struct.unpack("<I4s", raw[off:off + 8])
        body = raw[off + 8:off + 8 + clen]
        if ctype == b"JSON":
            json_chunk = json.loads(body.decode("utf-8"))
        elif ctype == b"BIN\x00":
            bin_chunk = body
        off += CHUNK_HDR + clen + ((4 - clen % 4) % 4)
    if json_chunk is None:
        raise SystemExit("没有 JSON chunk")
    return json_chunk, bin_chunk


def write_glb(path, j, bin_bytes):
    body = json.dumps(j, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    pad = (4 - len(body) % 4) % 4
    body = body + b" " * pad
    bin_pad = (4 - len(bin_bytes) % 4) % 4
    bin_out = bin_bytes + b"\x00" * bin_pad
    chunks = (struct.pack("<I4s", len(body), b"JSON") + body)
    if bin_out:
        chunks += struct.pack("<I4s", len(bin_out), b"BIN\x00") + bin_out
    head = struct.pack("<4sII", b"glTF", 2, 12 + len(chunks))
    with open(path, "wb") as f:
        f.write(head + chunks)
    return len(head + chunks)


def find_registered(file_rel):
    art = json.load(io.open(DATA, encoding="utf-8"))
    items = (art.get("bisRealModels") or {}).get("items") or []
    for it in items:
        if it.get("file") == file_rel:
            return it
    return None


def convert(src, dst, fmt):
    source, bin_bytes = read_glb(src)
    j = copy.deepcopy(source)
    images = j.get("images") or []
    bufviews = j.get("bufferViews") or []
    # 只支持"单 buffer + image 指向 bufferView"这种客户端导出的写法；不是就停，别猜
    if len(j.get("buffers") or []) != 1 or j["buffers"][0].get("uri"):
        raise SystemExit("这份 GLB 不是单内嵌 buffer 的写法，脚本不处理（别硬改）")
    if any(view.get("buffer", 0) != 0 for view in bufviews):
        raise SystemExit("bufferView 引用了非内嵌 buffer，脚本不处理")
    replacements = {}
    image_view_ids = set()
    changed = 0
    for idx, im in enumerate(images):
        src_view = im.get("bufferView")
        if src_view is None or src_view >= len(bufviews) or src_view in image_view_ids:
            raise SystemExit("image %d 无有效且独占的内嵌 bufferView，不在处理范围" % idx)
        image_view_ids.add(src_view)
        bv = bufviews[src_view]
        start = bv.get("byteOffset", 0)
        raw = bin_bytes[start:start + bv["byteLength"]]
        if len(raw) != bv["byteLength"]:
            raise SystemExit("image %d 的 bufferView 越过 BIN 边界" % idx)
        mime = (im.get("mimeType") or "").lower()
        want = "image/" + fmt.lower()
        if mime == want:
            continue
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        if fmt == "JPEG":
            if img.getchannel("A").getextrema()[0] < 255:
                raise SystemExit("image %d 含透明像素，不能直接编码为 JPEG" % idx)
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, fmt)
        replacements[src_view] = out.getvalue()
        im["mimeType"] = want
        changed += 1

    # 保留原有全部 bufferView 的编号和元数据；accessor 仍指向原来的几何视图。
    # 只替换图片视图的字节，并重新计算每个视图的偏移。
    blob = bytearray()
    for view_id, view in enumerate(bufviews):
        start = source["bufferViews"][view_id].get("byteOffset", 0)
        length = source["bufferViews"][view_id]["byteLength"]
        data = replacements.get(view_id, bin_bytes[start:start + length])
        if view_id not in replacements and len(data) != length:
            raise SystemExit("bufferView %d 越过 BIN 边界" % view_id)
        blob.extend(b"\x00" * (-len(blob) % 4))
        view["byteOffset"] = len(blob)
        view["byteLength"] = len(data)
        blob.extend(data)

    # textures：把 EXT_texture_webp 的 source 搬回标准字段
    moved = 0
    for t in (j.get("textures") or []):
        ext = (t.get("extensions") or {}).get("EXT_texture_webp")
        if ext and "source" in ext:
            t["source"] = ext["source"]
            t["extensions"].pop("EXT_texture_webp", None)
            if not t["extensions"]:
                t.pop("extensions", None)
            moved += 1
    j["buffers"][0]["byteLength"] = len(blob)
    used = [u for u in (j.get("extensionsUsed") or []) if u != "EXT_texture_webp"]
    req = [u for u in (j.get("extensionsRequired") or []) if u != "EXT_texture_webp"]
    if used:
        j["extensionsUsed"] = used
    else:
        j.pop("extensionsUsed", None)
    if req:
        j["extensionsRequired"] = req
    else:
        j.pop("extensionsRequired", None)
    size = write_glb(dst, j, bytes(blob))
    return {"images": len(images), "reencoded": changed, "textures_moved": moved,
            "bytes": size, "sha256": sha256_file(dst),
            "extensions_left": (j.get("extensionsUsed") or []) + (j.get("extensionsRequired") or [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="相对 app/ 的登记路径，如 img/models/real/hunter-alliance.glb")
    ap.add_argument("--out", required=True, help="候选输出路径")
    ap.add_argument("--format", default="PNG", choices=["PNG", "JPEG"])
    args = ap.parse_args()

    src = os.path.join(WEB, args.file)
    reg = find_registered(args.file)
    if not reg:
        raise SystemExit("这份文件不在 art.json.bisRealModels 登记里：不许拿未登记的模型转候选")
    if reg.get("placementVerdict") != "PASS":
        raise SystemExit("登记里 placementVerdict 不是 PASS：%s" % reg.get("placementVerdict"))
    got = sha256_file(src)
    if got != reg.get("sha256"):
        raise SystemExit("源文件 SHA 与登记不符（%s ≠ %s）——先查清是谁改了" % (got[:12], reg["sha256"][:12]))
    if os.path.getsize(src) != reg.get("bytes"):
        raise SystemExit("源文件字节数与登记不符")

    j0, bin0 = read_glb(src)
    info = convert(src, args.out, args.format)
    print("源 %s\n  登记 SHA %s · %d B · 阵营 %s/%s · placementVerdict %s"
          % (args.file, got[:12], reg["bytes"], reg.get("setId"), reg.get("faction"), reg.get("placementVerdict")))
    print("候选 %s\n  %d B · sha256 %s\n  图片 %d 张（重编码 %d 张为 %s）· textures 搬回标准字段 %d 处 · 残留扩展 %s"
          % (args.out, info["bytes"], info["sha256"][:12], info["images"], info["reencoded"],
             args.format, info["textures_moved"], info["extensions_left"] or "无"))
    # 自检：产物必须还能被读回来，且几何/网格数没动
    j2, bin2 = read_glb(args.out)
    # 与**源文件**比，不写死数字：几何只许照搬，源里有几个网格就是几个
    for key in ("meshes", "nodes", "accessors", "materials", "images"):
        if len(j2.get(key) or []) != len(j0.get(key) or []):
            raise SystemExit("候选的 %s 数量与源不一致（%d ≠ %d）——几何/材质被动过了"
                             % (key, len(j2.get(key) or []), len(j0.get(key) or [])))
    if [a.get("count") for a in j2["accessors"]] != [a.get("count") for a in j0["accessors"]]:
        raise SystemExit("候选的 accessor 顶点数与源不一致，不许改几何")
    if j2.get("accessors") != j0.get("accessors") or j2.get("meshes") != j0.get("meshes") or j2.get("nodes") != j0.get("nodes") or j2.get("materials") != j0.get("materials"):
        raise SystemExit("候选的 accessor/mesh/node/material 与源不一致")
    if len(j2.get("bufferViews") or []) != len(j0.get("bufferViews") or []):
        raise SystemExit("候选的 bufferView 数量与源不一致")
    image_views = {im["bufferView"] for im in j0.get("images") or []}
    for view_id, (old, new) in enumerate(zip(j0["bufferViews"], j2["bufferViews"])):
        old_data = bin0[old.get("byteOffset", 0):old.get("byteOffset", 0) + old["byteLength"]]
        new_data = bin2[new.get("byteOffset", 0):new.get("byteOffset", 0) + new["byteLength"]]
        if len(new_data) != new["byteLength"] or (view_id not in image_views and old_data != new_data):
            raise SystemExit("候选的 bufferView %d 越界或非图片字节被改动" % view_id)
    for idx, (old, new) in enumerate(zip(j0.get("images") or [], j2.get("images") or [])):
        old_view, new_view = j0["bufferViews"][old["bufferView"]], j2["bufferViews"][new["bufferView"]]
        old_data = bin0[old_view.get("byteOffset", 0):old_view.get("byteOffset", 0) + old_view["byteLength"]]
        new_data = bin2[new_view.get("byteOffset", 0):new_view.get("byteOffset", 0) + new_view["byteLength"]]
        if Image.open(io.BytesIO(old_data)).convert("RGBA").tobytes() != Image.open(io.BytesIO(new_data)).convert("RGBA").tobytes():
            raise SystemExit("候选的 image %d 像素与源不一致" % idx)
    if (j2.get("extensionsRequired") or []):
        raise SystemExit("候选仍声明 required 扩展：%s" % j2["extensionsRequired"])
    print("自检：与源逐项等量（网格 %d · 节点 %d · accessor %d · 材质 %d · 图片 %d）· 顶点数一致 · 无 required 扩展"
          % (len(j2["meshes"]), len(j2.get("nodes") or []), len(j2["accessors"]),
             len(j2.get("materials") or []), len(j2["images"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
