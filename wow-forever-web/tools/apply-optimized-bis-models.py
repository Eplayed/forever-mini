#!/usr/bin/env python3
"""Verify a complete optimized E12 batch, then switch the real-model registry.

Run optimize-bis-glb.py on all 76 source GLBs first and put its JSON results in
batch-report.json beside the candidate files. Without --apply this is read-only.
"""

import argparse
import hashlib
import json
import os
import shutil
import struct
import tempfile
from pathlib import Path


WEB = Path(__file__).resolve().parent.parent
REAL = WEB / "app/img/models/real"
ART = WEB / "app/data/art.json"


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def glb_doc(path):
    data = path.read_bytes()
    magic, version, total, json_len, json_type = struct.unpack_from("<4sIII4s", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data) or json_type != b"JSON":
        raise ValueError("invalid GLB header: " + str(path))
    chunk_end = 20 + json_len
    bin_len, bin_type = struct.unpack_from("<I4s", data, chunk_end)
    if bin_type != b"BIN\0" or chunk_end + 8 + bin_len != len(data):
        raise ValueError("invalid BIN chunk: " + str(path))
    return json.loads(data[20:chunk_end]), data[chunk_end + 8:]


def accessor_values(doc, blob, accessor_id):
    acc = doc["accessors"][accessor_id]
    view = doc["bufferViews"][acc["bufferView"]]
    if acc.get("sparse") or view.get("byteStride"):
        raise ValueError("unexpected sparse or interleaved accessor")
    sizes = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    code, component_size = sizes[acc["componentType"]]
    stride = width * component_size
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    raw = blob[start:start + acc["count"] * stride]
    if len(raw) != acc["count"] * stride:
        raise ValueError("truncated accessor")
    return raw, stride, code, acc["count"]


def verify_triangle_stream(before, before_bin, after, after_bin):
    """An independent check that every indexed vertex attribute remains byte-identical."""
    for old_mesh, new_mesh in zip(before["meshes"], after["meshes"]):
        for old_prim, new_prim in zip(old_mesh["primitives"], new_mesh["primitives"]):
            old_raw, _, old_code, old_count = accessor_values(before, before_bin, old_prim["indices"])
            new_raw, _, new_code, new_count = accessor_values(after, after_bin, new_prim["indices"])
            if old_count != new_count:
                raise ValueError("triangle index count changed")
            old_ids = struct.unpack("<" + str(old_count) + old_code, old_raw)
            new_ids = struct.unpack("<" + str(new_count) + new_code, new_raw)
            index_pairs = set(zip(old_ids, new_ids))
            for name, old_id in old_prim["attributes"].items():
                new_id = new_prim["attributes"][name]
                old_data, old_stride, _, old_elements = accessor_values(before, before_bin, old_id)
                new_data, new_stride, _, new_elements = accessor_values(after, after_bin, new_id)
                if old_stride != new_stride:
                    raise ValueError("attribute element size changed")
                for old_i, new_i in index_pairs:
                    if old_i >= old_elements or new_i >= new_elements:
                        raise ValueError("remapped index exceeds accessor")
                    if (old_data[old_i * old_stride:(old_i + 1) * old_stride]
                            != new_data[new_i * new_stride:(new_i + 1) * new_stride]):
                        raise ValueError("indexed attribute changed: " + name)


def validate(stage):
    art = json.loads(ART.read_text())
    manifest = json.loads((REAL / "manifest.json").read_text())
    items = manifest["items"]
    registry = art["bisRealModels"]["items"]
    if len(items) != 76 or items != registry:
        raise ValueError("the real-model manifest and art registry differ")
    reports = json.loads((stage / "batch-report.json").read_text())
    by_name = {Path(row["output"]).name: row for row in reports}
    expected = {Path(row["file"]).name for row in items}
    if len(reports) != 76 or set(by_name) != expected:
        raise ValueError("optimized batch must contain exactly the registered 76 GLBs")
    new_items = []
    total_old = total_new = 0
    for item in items:
        filename = Path(item["file"]).name
        source, target = REAL / filename, stage / filename
        report = by_name[filename]
        if report["sourceSha256"] != item["sha256"] or report["sourceBytes"] != item["bytes"]:
            raise ValueError("source report does not match registry: " + filename)
        if sha_file(source) != item["sha256"]:
            raise ValueError("source changed since optimization: " + filename)
        if (target.stat().st_size != report["outputBytes"]
                or sha_file(target) != report["outputSha256"]):
            raise ValueError("optimized output changed: " + filename)
        (before, before_bin), (after, after_bin) = glb_doc(source), glb_doc(target)
        for key in ("nodes", "scenes", "scene", "meshes", "materials", "samplers"):
            if before.get(key) != after.get(key):
                raise ValueError("scene or material altered: " + filename + "/" + key)
        if len(before.get("images", [])) != len(after.get("images", [])):
            raise ValueError("image count changed: " + filename)
        if ("EXT_texture_webp" not in after.get("extensionsRequired", [])
                or any(x.get("mimeType") != "image/webp" for x in after.get("images", []))):
            raise ValueError("WebP textures not fully encoded: " + filename)
        if report["geometry"]["triangles"] <= 0 or report["outputBytes"] >= report["sourceBytes"]:
            raise ValueError("optimization ineffective: " + filename)
        verify_triangle_stream(before, before_bin, after, after_bin)
        updated = dict(item)
        updated["sourceBytes"] = item["bytes"]
        updated["bytes"] = report["outputBytes"]
        updated["sha256"] = report["outputSha256"]
        updated["optimization"] = {"geometry": "referenced vertices only",
                                   "textures": "WebP quality 90; body atlas max width 1024"}
        new_items.append(updated)
        total_old += item["bytes"]
        total_new += updated["bytes"]
    if total_old != 916645576:
        raise ValueError("unexpected E12 source total")
    manifest["items"] = new_items
    manifest["optimization"] = {"tool": "tools/optimize-bis-glb.py",
                                "bodyWidth": 1024, "webpQuality": 90,
                                "sourceTotalBytes": total_old,
                                "optimizedTotalBytes": total_new}
    art["bisRealModels"]["items"] = new_items
    return art, manifest, total_old, total_new


def apply(stage, art, manifest):
    candidate = Path(tempfile.mkdtemp(prefix="wow-real-candidate-", dir=str(REAL.parent)))
    backup = Path(tempfile.mkdtemp(prefix="wow-real-e12-backup-"))
    backup.rmdir()
    try:
        for item in manifest["items"]:
            name = Path(item["file"]).name
            shutil.copy2(stage / name, candidate / name)
        (candidate / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        os.replace(REAL, backup)
        try:
            os.replace(candidate, REAL)
            ART.write_text(json.dumps(art, ensure_ascii=False, indent=2) + "\n")
        except Exception:
            if REAL.exists():
                shutil.rmtree(REAL)
            os.replace(backup, REAL)
            raise
    finally:
        if candidate.exists():
            shutil.rmtree(candidate)
    print("E12 source backup retained at", backup)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    art, manifest, old, new = validate(args.stage)
    print("verified 76 optimized GLBs:", old, "->", new, "bytes",
          "(%0.1fx smaller)" % (old / new))
    if args.apply:
        apply(args.stage, art, manifest)


if __name__ == "__main__":
    main()
