#!/usr/bin/env python3
"""Build exact Windows export jobs for every BiS set lacking a real 3D model."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BIS = ROOT / "app/data/bis.json"
RACES = ROOT / "app/data/races.json"
ART = ROOT / "app/data/art.json"
OUT = ROOT / "docs/QODER-全职业3D导出清单-2026-10-28.json"
RACE_BY_CLASS = {
    "alliance": {"default": "human", "druid": "night-elf", "shaman": "dwarf"},
    "horde": {"default": "orc", "druid": "tauren", "paladin": "undead", "priest": "undead"},
}
VISUAL_SLOTS = {"头部", "肩部", "背部", "胸部", "手腕", "手", "腰部", "腿部", "脚",
                "主手", "副手", "远程"}


def make_jobs():
    bis_raw = BIS.read_bytes()
    bis = json.loads(bis_raw)
    races = {r["id"]: r for r in json.loads(RACES.read_text())["races"]}
    art = json.loads(ART.read_text())
    existing = {(m["setId"], m["faction"]): m
                for m in (art.get("bisRealModels") or {}).get("items", [])}
    jobs = []
    skipped = 0
    for item_set in bis["sets"]:
        for faction in ("alliance", "horde"):
            key = (item_set["id"], faction)
            doll = item_set["doll"][faction]
            normalized = [dict(slot=d["slot"], cell=d.get("cell", 1), item=d["item"]) for d in doll]
            registered = existing.get(key)
            if registered and registered.get("placementVerdict") == "PASS" and \
                    registered.get("dollSnapshot") == normalized and \
                    (ROOT / "app" / registered.get("file", "")).is_file():
                skipped += 1
                continue
            cls = item_set["cls"]
            race = RACE_BY_CLASS[faction].get(cls, RACE_BY_CLASS[faction]["default"])
            if race not in races or races[race]["faction"] != faction or cls not in races[race]["classes"]:
                raise ValueError(f"race/class mismatch: {race}/{cls}/{faction}")
            if not doll or len({(d["slot"], d.get("cell", 1)) for d in doll}) != len(doll):
                raise ValueError(f"missing or duplicate doll slots: {key}")
            visible = [dict(slot=d["slot"], cell=d.get("cell", 1), item=d["item"])
                       for d in doll if d["slot"] in VISUAL_SLOTS]
            primary = "远程" if cls == "hunter" else "主手"
            weapon = [d for d in visible if d["slot"] == primary]
            if cls != "hunter":
                weapon += [d for d in visible if d["slot"] == "副手"]
            if not weapon:
                raise ValueError(f"no display weapon: {key}")
            jobs.append({
                "setId": item_set["id"], "classId": cls, "mode": item_set["mode"],
                "faction": faction, "raceId": race, "bodyType": "male",
                "doll": normalized,
                "visualDoll": visible,
                "displayWeaponItems": weapon,
                "outputFile": f"glb/{item_set['id']}-{faction}.glb",
            })
    return {
        "schemaVersion": 1,
        "source": "wow-forever-web/app/data/bis.json",
        "sourceSha256": hashlib.sha256(bis_raw).hexdigest(),
        "existingRealModelsSkipped": skipped,
        "jobs": jobs,
        "summary": {"sets": len(bis["sets"]), "missingModels": len(jobs),
                    "byClass": dict(sorted(Counter(j["classId"] for j in jobs).items()))},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = json.dumps(make_jobs(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            raise SystemExit(f"outdated export jobs: {OUT}")
    else:
        OUT.write_text(text)
    print(f"{OUT}: {len(json.loads(text)['jobs'])} models")


if __name__ == "__main__":
    main()
