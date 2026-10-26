#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""烘一个**占位**配装模型（app/img/models/placeholder.glb），用来验"网页上转 3D 人物"这条链。

为什么要有它：参考站那 12 个 GLB 是从游戏客户端烘出来的，我们这一步还没拿到模型文件
（要 Windows 跑一次探针，见 docs/EVAL-bis更新与3D模型-2026-10-26.md 门槛①）。
但"前端能不能加载 GLB、懒加载划不划算、没有 WebGL 怎么退、部位怎么对上数据"
这四件事**不需要真模型也能验**。所以这里用纯几何体自己拼一个人形：
一个身体 + 16 个按本站部位命名的装备件，页面按 bis.json 的格子决定哪件亮、
按品质色决定它染成什么颜色。

这不是素材，是脚手架：删掉 app/img/models/ 整个目录就回到现在的 2D 纸娃娃。
不引任何游戏客户端资产，也不引第三方模型文件（见同目录 manifest.json 的 origin）。

用法：python3 tools/build-bis-placeholder-model.py
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "app", "img", "models")
OUT = os.path.join(OUT_DIR, "placeholder.glb")
MANIFEST = os.path.join(OUT_DIR, "manifest.json")

# 18 个装备件：与 app/data/bis.json 的 doll[].slot(+cell) 一一对应（38 套里出现过的部位全在这），
# 键名同时写进 GLB 的节点名，页面侧的映射表在 app/src/lib/bis-model.js。
# (节点名, x, y, z, sx, sy, sz) —— 单位立方体，y 是身高方向，整体约 1.8 高
GEAR = [
    ("head",     0.00, 1.62, 0.00, 0.26, 0.28, 0.26),
    ("neck",     0.00, 1.42, 0.00, 0.20, 0.08, 0.20),
    ("shoulder", 0.00, 1.30, 0.00, 0.66, 0.14, 0.34),
    ("back",     0.00, 1.06, -0.17, 0.44, 0.62, 0.06),
    ("chest",    0.00, 1.10, 0.00, 0.46, 0.50, 0.28),
    ("wrist",    0.40, 0.92, 0.00, 0.12, 0.10, 0.12),
    ("hands",    0.42, 0.74, 0.00, 0.14, 0.16, 0.16),
    ("waist",    0.00, 0.82, 0.00, 0.44, 0.12, 0.26),
    ("legs",     0.00, 0.48, 0.00, 0.36, 0.56, 0.24),
    ("feet",     0.00, 0.10, 0.02, 0.34, 0.18, 0.30),
    ("ring1",    0.44, 0.70, 0.06, 0.06, 0.05, 0.06),
    ("ring2",    0.44, 0.70, -0.06, 0.06, 0.05, 0.06),
    ("trinket1", 0.20, 1.24, 0.15, 0.09, 0.11, 0.05),
    ("trinket2", -0.20, 1.24, 0.15, 0.09, 0.11, 0.05),
    ("mainhand", 0.56, 0.86, 0.10, 0.07, 0.66, 0.07),
    ("ranged",   -0.56, 0.96, 0.06, 0.10, 0.34, 0.10),
    ("offhand",  -0.56, 0.96, 0.10, 0.16, 0.52, 0.05),
    ("relic",    0.00, 1.22, 0.17, 0.12, 0.14, 0.05),
]
# 身体（不参与染色，永远可见）
BODY = [
    ("body_torso", 0.00, 1.08, 0.00, 0.40, 0.46, 0.24),
    ("body_head",  0.00, 1.60, 0.00, 0.22, 0.24, 0.22),
    ("body_arm_l", 0.34, 1.02, 0.00, 0.12, 0.52, 0.12),
    ("body_arm_r", -0.34, 1.02, 0.00, 0.12, 0.52, 0.12),
    ("body_leg_l", 0.12, 0.44, 0.00, 0.15, 0.62, 0.16),
    ("body_leg_r", -0.12, 0.44, 0.00, 0.15, 0.62, 0.16),
]


def box_mesh():
    """24 顶点（带法线）+ 36 索引的单位立方体，所有件共用这一份几何。"""
    h = 0.5
    faces = [   # (法线, 四个角)
        ((0, 0, 1), [(-h, -h, h), (h, -h, h), (h, h, h), (-h, h, h)]),
        ((0, 0, -1), [(h, -h, -h), (-h, -h, -h), (-h, h, -h), (h, h, -h)]),
        ((1, 0, 0), [(h, -h, h), (h, -h, -h), (h, h, -h), (h, h, h)]),
        ((-1, 0, 0), [(-h, -h, -h), (-h, -h, h), (-h, h, h), (-h, h, -h)]),
        ((0, 1, 0), [(-h, h, h), (h, h, h), (h, h, -h), (-h, h, -h)]),
        ((0, -1, 0), [(-h, -h, -h), (h, -h, -h), (h, -h, h), (-h, -h, h)]),
    ]
    pos, nrm, idx = [], [], []
    for n, quad in faces:
        base = len(pos)
        for v in quad:
            pos.append(v)
            nrm.append(n)
        idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    return pos, nrm, idx


def main():
    pos, nrm, idx = box_mesh()
    bin_parts = []
    offset = 0

    def add(data, target):
        nonlocal offset
        b = bytearray(data)
        pad = (4 - len(b) % 4) % 4
        b += bytearray(pad)
        bin_parts.append(bytes(b))
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target}
        offset += len(b)
        return view

    views, accessors = [], []
    vp = add(b"".join(struct.pack("<3f", *v) for v in pos), 34962)
    views.append(vp)
    lo = [min(c for c, _, _ in pos), min(c for _, c, _ in pos), min(c for _, _, c in pos)]
    hi = [max(c for c, _, _ in pos), max(c for _, c, _ in pos), max(c for _, _, c in pos)]
    accessors.append({"bufferView": len(views) - 1, "componentType": 5126, "count": len(pos),
                      "type": "VEC3", "min": lo, "max": hi})
    vn = add(b"".join(struct.pack("<3f", *v) for v in nrm), 34962)
    views.append(vn)
    accessors.append({"bufferView": len(views) - 1, "componentType": 5126, "count": len(nrm), "type": "VEC3"})
    vi = add(b"".join(struct.pack("<3H", *idx[i:i + 3]) for i in range(0, len(idx), 3)), 34963)
    views.append(vi)
    accessors.append({"bufferView": len(views) - 1, "componentType": 5123, "count": len(idx), "type": "SCALAR"})
    A_POS, A_NRM, A_IDX = 0, 1, 2

    parts = BODY + GEAR
    materials, meshes, nodes = [], [], []
    for i, (name, x, y, z, sx, sy, sz) in enumerate(parts):
        is_body = name.startswith("body_")
        materials.append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.42, 0.44, 0.48, 1.0] if is_body else [0.62, 0.62, 0.62, 1.0],
                "metallicFactor": 0.0, "roughnessFactor": 0.72},
        })
        meshes.append({"name": name + "_mesh", "primitives": [{
            "attributes": {"POSITION": A_POS, "NORMAL": A_NRM},
            "indices": A_IDX, "material": i}]})
        nodes.append({"name": name, "mesh": i,
                      "translation": [x, y, z], "scale": [sx, sy, sz],
                      "extras": {"kind": "body" if is_body else "gear"}})

    gltf = {
        "asset": {"version": "2.0", "generator": "tools/build-bis-placeholder-model.py（本站自产占位模型，不含游戏资产）"},
        "scene": 0,
        "scenes": [{"name": "bis-placeholder", "nodes": list(range(len(nodes)))}],
        "materials": materials, "meshes": meshes, "nodes": nodes,
        "accessors": accessors, "bufferViews": views,
        "buffers": [{"byteLength": offset}],
    }
    json_bytes = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * pad
    bin_bytes = b"".join(bin_parts)
    bin_pad = (4 - len(bin_bytes) % 4) % 4
    bin_bytes += b"\x00" * bin_pad

    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    glb = bytearray()
    glb += struct.pack("<III", 0x46546C67, 2, total)
    glb += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    glb += struct.pack("<II", len(bin_bytes), 0x004E4942) + bin_bytes

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(bytes(glb))

    manifest = {
        "kind": "bis-models",
        "note": "占位模型，不是素材：纯几何体自己拼的，不含任何游戏客户端资产，也不含第三方站的模型文件。"
                "它只用来验前端那条链（懒加载、部位对数据、无 WebGL 退回图片）。"
                "整目录删掉 app/img/models/ 即回到 2D 纸娃娃。",
        "origin": "self-generated",
        "generator": "tools/build-bis-placeholder-model.py",
        "generatedAt": __import__("datetime").date.today().isoformat(),
        "items": [{
            "file": "placeholder.glb", "bytes": len(glb),
            "sha1": __import__("hashlib").sha1(bytes(glb)).hexdigest(),
            "source": "本站自己生成（不来自客户端、不来自任何第三方站）",
            "kind": "placeholder",
            "gearNodes": [n for n, *_ in GEAR],
            "bodyNodes": [n for n, *_ in BODY],
        }],
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("写出 %s（%.1f KB，%d 个节点：身体 %d + 装备件 %d）"
          % (os.path.relpath(OUT, ROOT), len(glb) / 1024.0, len(nodes), len(BODY), len(GEAR)))
    print("台账 %s" % os.path.relpath(MANIFEST, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
