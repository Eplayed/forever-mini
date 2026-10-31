#!/usr/bin/env python3
"""Compact unused static GLB vertices, optionally encode embedded textures as WebP.

The E12 exporter gives every visible body primitive the same 226k-vertex arrays,
while the index buffers reference only a few thousand vertices. This script keeps
the exact indexed triangles and remaps their attributes. It rejects unfamiliar
GLB layouts instead of silently producing a damaged model.
"""

import argparse
import copy
import hashlib
import io
import json
import struct
from pathlib import Path

from PIL import Image


COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
             5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
ARITY = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
         "MAT2": 4, "MAT3": 9, "MAT4": 16}


def read_glb(path):
    data = path.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise ValueError("not a complete GLB 2.0 file")
    json_len, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise ValueError("missing JSON chunk")
    json_end = 20 + json_len
    bin_len, bin_type = struct.unpack_from("<I4s", data, json_end)
    if bin_type != b"BIN\0" or json_end + 8 + bin_len != len(data):
        raise ValueError("expected one BIN chunk")
    doc = json.loads(data[20:json_end])
    if len(doc.get("buffers", [])) != 1 or doc["buffers"][0].get("uri"):
        raise ValueError("expected one embedded buffer")
    if doc.get("skins") or doc.get("animations"):
        raise ValueError("only static E12 exports are supported")
    return doc, data[json_end + 8:]


def accessor_info(doc, index):
    acc = doc["accessors"][index]
    if acc.get("sparse") or acc.get("byteOffset", 0):
        raise ValueError("sparse or offset accessor is unsupported")
    view_id = acc["bufferView"]
    view = doc["bufferViews"][view_id]
    if view.get("byteStride") or view.get("buffer", 0) != 0:
        raise ValueError("interleaved or external view is unsupported")
    fmt, width = COMPONENT[acc["componentType"]]
    arity = ARITY[acc["type"]]
    if view["byteLength"] != acc["count"] * width * arity:
        raise ValueError("accessor does not own its complete buffer view")
    return acc, view_id, fmt, width, arity


def view_bytes(doc, blob, view_id):
    view = doc["bufferViews"][view_id]
    start = view.get("byteOffset", 0)
    end = start + view["byteLength"]
    if end > len(blob):
        raise ValueError("buffer view extends beyond BIN")
    return blob[start:end]


def compact_geometry(doc, blob, replacements):
    groups = {}
    owner = {}
    for mesh in doc.get("meshes", []):
        for primitive in mesh["primitives"]:
            if primitive.get("mode", 4) != 4 or "indices" not in primitive:
                raise ValueError("expected indexed triangles")
            key = tuple(sorted(primitive["attributes"].items()))
            groups.setdefault(key, []).append(primitive)
            for _, attr_id in key:
                if attr_id in owner and owner[attr_id] != key:
                    raise ValueError("attribute reused by incompatible groups")
                owner[attr_id] = key

    stats = {"originalAttributeElements": 0, "keptAttributeElements": 0,
             "triangles": 0, "groups": len(groups)}
    for key, primitives in groups.items():
        attribute_ids = [attr_id for _, attr_id in key]
        first_count = doc["accessors"][attribute_ids[0]]["count"]
        if any(doc["accessors"][i]["count"] != first_count for i in attribute_ids):
            raise ValueError("attribute counts differ within a primitive")
        index_values = []
        for primitive in primitives:
            acc, view_id, fmt, width, arity = accessor_info(doc, primitive["indices"])
            if arity != 1 or fmt not in ("B", "H", "I") or acc["count"] % 3:
                raise ValueError("invalid triangle index accessor")
            raw = view_bytes(doc, blob, view_id)
            values = struct.unpack("<" + str(acc["count"]) + fmt, raw)
            if values and max(values) >= first_count:
                raise ValueError("index exceeds attribute count")
            index_values.append((primitive, acc, view_id, fmt, values))
            stats["triangles"] += len(values) // 3
        used = sorted(set(i for _, _, _, _, values in index_values for i in values))
        remap = {old: new for new, old in enumerate(used)}
        stats["originalAttributeElements"] += first_count
        stats["keptAttributeElements"] += len(used)
        for attr_id in attribute_ids:
            acc, view_id, fmt, width, arity = accessor_info(doc, attr_id)
            if view_id in replacements:
                raise ValueError("shared attribute buffer view")
            raw = view_bytes(doc, blob, view_id)
            stride = width * arity
            packed = b"".join(raw[i * stride:(i + 1) * stride] for i in used)
            replacements[view_id] = packed
            acc["count"] = len(used)
            if "min" in acc or "max" in acc:
                values = [struct.unpack_from("<" + fmt * arity, packed, i * stride)
                          for i in range(len(used))]
                if values:
                    acc["min"] = [min(v[k] for v in values) for k in range(arity)]
                    acc["max"] = [max(v[k] for v in values) for k in range(arity)]
        for _, acc, view_id, fmt, values in index_values:
            if view_id in replacements:
                raise ValueError("shared index buffer view")
            replacements[view_id] = struct.pack("<" + str(len(values)) + fmt,
                                                *(remap[i] for i in values))
    return stats


def encode_webp(doc, blob, replacements, body_width, quality):
    images = doc.get("images", [])
    image_views = [x.get("bufferView") for x in images]
    if len(image_views) != len(set(image_views)) or any(v is None for v in image_views):
        raise ValueError("expected unique embedded image views")
    report = []
    for image_id, image in enumerate(images):
        view_id = image["bufferView"]
        source = view_bytes(doc, blob, view_id)
        picture = Image.open(io.BytesIO(source))
        original_size = picture.size
        if image_id == 0 and body_width and picture.width > body_width:
            new_height = round(picture.height * body_width / picture.width)
            picture = picture.resize((body_width, new_height), Image.Resampling.LANCZOS)
        picture = picture.convert("RGBA" if "A" in picture.getbands() else "RGB")
        target = io.BytesIO()
        picture.save(target, format="WEBP", quality=quality, method=6)
        replacements[view_id] = target.getvalue()
        image["mimeType"] = "image/webp"
        report.append({"image": image_id, "from": list(original_size),
                       "to": list(picture.size), "sourceBytes": len(source),
                       "optimizedBytes": len(target.getvalue())})
    for texture in doc.get("textures", []):
        image_id = texture.pop("source", None)
        if image_id is None:
            raise ValueError("expected core texture source")
        texture.setdefault("extensions", {})["EXT_texture_webp"] = {"source": image_id}
    doc.setdefault("extensionsUsed", []).append("EXT_texture_webp")
    doc.setdefault("extensionsRequired", []).append("EXT_texture_webp")
    return report


def write_glb(path, doc, source_blob, replacements):
    new_blob = bytearray()
    for view_id, view in enumerate(doc["bufferViews"]):
        payload = replacements.get(view_id)
        if payload is None:
            payload = view_bytes(doc, source_blob, view_id)
        new_blob.extend(b"\0" * (-len(new_blob) % 4))
        view["byteOffset"] = len(new_blob)
        view["byteLength"] = len(payload)
        new_blob.extend(payload)
    doc["buffers"][0]["byteLength"] = len(new_blob)
    encoded = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    new_blob.extend(b"\0" * (-len(new_blob) % 4))
    total = 12 + 8 + len(encoded) + 8 + len(new_blob)
    out = (struct.pack("<4sII", b"glTF", 2, total)
           + struct.pack("<I4s", len(encoded), b"JSON") + encoded
           + struct.pack("<I4s", len(new_blob), b"BIN\0") + new_blob)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    return len(out), hashlib.sha256(out).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--webp", action="store_true")
    parser.add_argument("--body-width", type=int, default=1024)
    parser.add_argument("--quality", type=int, default=90)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        raise SystemExit("source and output must differ")
    doc, blob = read_glb(args.source)
    source_sha = hashlib.sha256(args.source.read_bytes()).hexdigest()
    result = copy.deepcopy(doc)
    replacements = {}
    geometry = compact_geometry(result, blob, replacements)
    textures = (encode_webp(result, blob, replacements, args.body_width, args.quality)
                if args.webp else [])
    size, digest = write_glb(args.output, result, blob, replacements)
    print(json.dumps({"source": str(args.source), "sourceBytes": args.source.stat().st_size,
                      "sourceSha256": source_sha, "output": str(args.output),
                      "outputBytes": size, "outputSha256": digest,
                      "geometry": geometry, "textures": textures}, ensure_ascii=False))


if __name__ == "__main__":
    main()
