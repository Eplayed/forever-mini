#!/usr/bin/env python3
"""Reproduce two round-7 hunter GLBs for out-of-tree placement diagnosis.

Round 7 bakes character body vertices in renderer space (forward = +X), while
equipment is exported in glTF space (forward = +Z). Rotate only the body nodes
by -90 degrees around Y. Round 8 found misplaced helmets in both results, so
the corrected files must remain outside the website's publishable img tree.
"""

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = (ROOT.parent.parent / ".scratch" / "wow" / "ziliao-export" /
                  "round7-2026-10-28" / "run-20261028-125743" / "glb")
OUTPUT = ROOT.parent.parent / ".scratch" / "wow" / "diagnostic-hunter-3d-round8"
ART = ROOT / "app" / "data" / "art.json"
SPECS = (("alliance", "humanmale_hd_"), ("horde", "orcmale_hd_"))
ROTATION = [0, -math.sqrt(0.5), 0, math.sqrt(0.5)]
# Round 7 export uses these visible pieces from the Hunter PvE list. Keep the
# snapshot independent of bis.json so a later data refresh cannot silently
# relabel an old baked character as the new outfit.
VISIBLE_ITEMS = {
    "alliance": {"头部": 252512, "肩部": 2278, "背部": 13108,
                 "胸部": 7374, "手腕": 6410, "手": 7358,
                 "腰部": 252521, "腿部": 9624, "脚": 20093,
                 "远程": 274084},
    "horde": {"头部": 252512, "肩部": 2278, "背部": 13108,
              "胸部": 7374, "手腕": 6410, "手": 6784,
              "腰部": 252521, "腿部": 9624, "脚": 20157,
              "远程": 274084},
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def transform(raw, body_prefix, faction):
    magic, version, total = struct.unpack_from("<4sII", raw)
    if (magic, version, total) != (b"glTF", 2, len(raw)):
        raise ValueError("not a complete glTF 2 GLB")
    json_size, kind = struct.unpack_from("<I4s", raw, 12)
    if kind != b"JSON":
        raise ValueError("missing JSON chunk")
    gltf = json.loads(raw[20:20 + json_size])
    binary_start = 20 + json_size
    binary_size, binary_kind = struct.unpack_from("<I4s", raw, binary_start)
    if binary_kind != b"BIN\0" or binary_start + 8 + binary_size != len(raw):
        raise ValueError("unexpected GLB chunks")
    if gltf.get("skins") or gltf.get("animations"):
        raise ValueError("expected static baked character")
    body = 0
    for node in gltf["nodes"]:
        if node.get("name", "").startswith(body_prefix) and "mesh" in node:
            if any(key in node for key in ("matrix", "rotation", "translation", "scale")):
                raise ValueError("body node already transformed")
            node["rotation"] = ROTATION
            body += 1
    if body < 10:
        raise ValueError(f"only {body} body meshes found for {faction}")
    expected = ("Head_Item252512_0", "Shoulder (L)_Item2278_0",
                "Shoulder (R)_Item2278_0", "Main-hand_Item274084_0")
    names = {node.get("name") for node in gltf["nodes"]}
    if any(name not in names for name in expected):
        raise ValueError("required helmet, shoulders or ranged weapon absent")
    packed = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    packed += b" " * (-len(packed) % 4)
    binary = raw[binary_start + 8:]
    result = (struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(packed) + 8 + len(binary))
              + struct.pack("<I4s", len(packed), b"JSON") + packed
              + struct.pack("<I4s", len(binary), b"BIN\0") + binary)
    return result, body


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = ap.parse_args()
    bis = json.loads((ROOT / "app" / "data" / "bis.json").read_text())
    hunter = next((x for x in bis["sets"] if x["id"] == "hunter"), None)
    if hunter is None:
        raise ValueError("Hunter PvE set is absent from bis.json")
    for faction, expected in VISIBLE_ITEMS.items():
        got = {x["slot"]: x["item"] for x in hunter["doll"][faction] if x["slot"] in expected}
        if got != expected:
            raise ValueError(f"{faction} Hunter PvE outfit differs from round 7 export: {got}")
    art = json.loads(ART.read_text())
    if any(it.get("setId") != "hunter" for it in (art.get("bisRealModels") or {}).get("items", [])):
        raise ValueError("other class models are registered; this Hunter-only script must not overwrite them")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    items = []
    for faction, body_prefix in SPECS:
        original = (args.source / f"{faction}-ranged.glb").read_bytes()
        result, body_count = transform(original, body_prefix, faction)
        name = f"hunter-pve-{faction}.glb"
        (OUTPUT / name).write_bytes(result)
        items.append({
            "setId": "hunter", "faction": faction,
            "placementVerdict": "MARGINAL" if faction == "alliance" else "FAIL",
            "placementEvidence": "round8-2026-10-28/viewer-evidence/attachment-acceptance.csv",
            "raceId": "human" if faction == "alliance" else "orc",
            "bodyType": "male",
            "file": name, "bytes": len(result),
            "sha256": sha256(result), "sourceSha256": sha256(original),
            "bodyMeshesRotated": body_count,
            "visibleWeaponItemId": 274084,
            "displayWeaponItems": [{"slot": "远程", "item": 274084}],
            "visibleItems": VISIBLE_ITEMS[faction],
            "dollSnapshot": [dict(slot=d["slot"], cell=d.get("cell", 1), item=d["item"])
                             for d in hunter["doll"][faction]],
        })
    manifest = {
        "origin": "client-derived", "clientProduct": "wowf",
        "clientBuild": "1.60.1.70532", "sourceRound": "round7-2026-10-28",
        "transformation": "body mesh nodes rotated -90 degrees around Y into equipment space",
        "items": items,
        "fallback": "remove this directory and bisRealModels from art.json to use the self-generated placeholder",
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    # Round 8 measured misplaced helmets in both factions. Keep the derived
    # GLBs for diagnosis but do not advertise them as accepted site assets.
    art["bisRealModels"] = {"origin": "client-derived", "items": []}
    ART.write_text(json.dumps(art, ensure_ascii=False, indent=1) + "\n")
    for item in items:
        print(item["file"], item["bytes"], item["sha256"])


if __name__ == "__main__":
    main()
