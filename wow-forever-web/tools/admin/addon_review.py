"""Compare the installed Forever add-ons with the upstream snapshots."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime

WEB = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WEB / "tools"))
from addons_root import candidates

REVIEW = Path(__file__).resolve().parent / "review" / "addons"
UPSTREAM = WEB / "app" / "data" / "upstream"
DF = "DungeonsForever/Core/Data/"
GI = "GearInsight_Forever/"
QD = "QuestieDB/support/Forever/DropTables/"
QCN = "BaiYunFeiQuestieCN/Locale/"
SOURCES = {
    "df-dungeon-loot": ("副本首领与掉落", (DF + "Data_DungeonLoot.lua",), (), "extract-df-loot.py", ("dungeons",)),
    "df-dungeon-geo": ("副本入口与首领坐标", tuple(DF + n for n in ("Data_DungeonEntry.lua", "Data_BossPos.lua", "Data_DungeonLoot.lua")), (), "extract-df-geo.py", ("entry", "bosses")),
    "df-bis": ("DF 配装参考名单", ("DungeonsForeverGear/Core/Data/Data_BIS.lua",), (), "extract-df-bis.py", ("sets",)),
    "questie-quests-cn": ("任务中文名", ("QuestieDB/QuestieDB_Forever.toc",), (QCN + "QuestNames.lua", QCN + "NpcNames.lua"), "extract-questie-quests-cn.py", ("quests", "npcNames")),
    "questie-item-drops": ("任务插件掉落归属", (QD + "classicItemDrops.lua", QD + "itemDropCorrections.lua"), (), "extract-questie-drops.py", ("npcs",)),
    "gi-prof-recipes": ("专业配方", (GI + "ProfRecipes.lua",), (), "extract-gi-prof-recipes.py", ("recipes",)),
    "gi-item-existence": ("物品存在性", (GI + "ItemMissingData.lua",), (), None, ()),
    "gi-items-detail": ("物品资料", (GI + "Data.lua",), (), None, ()),
    "gi-macros": ("宏命令", (GI + "MacroData.lua",), (), None, ()),
    "gi-pets": ("猎人宠物", (GI + "PetData.lua",), (), None, ()),
    "gi-dungeon-quests": ("副本任务", (GI + "DungeonQuestData.lua",), (), None, ()),
}
COUNTS = {
    "realBossRows": "首领", "dfItemIds": "掉落物品", "entryDungeons": "有入口坐标的副本",
    "bossRows": "首领坐标", "bossSkipped": "待匹配的首领坐标", "questIds": "任务",
    "rowsWithCn": "有中文名的任务", "patchDiffersFromColumn": "汉化补丁与主库译名分歧",
    "pairs": "掉落归属", "recipes": "配方", "withMapCoords": "带出处坐标的配方",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def resolve_file(root, rel, roots=None):
    direct = root / rel
    if direct.is_file():
        return direct
    for alt in roots or ():
        cand = Path(alt) / rel
        if cand.is_file():
            return cand
    return direct


def signatures(root, files, roots=None):
    return {file: digest(resolve_file(root, file, roots)) for file in files}


def install_for(key, required, roots):
    options = [required]
    if key == "df-bis":
        options.append((DF + "Data_BIS.lua",))
    for root in roots:
        for files in options:
            if all((root / f).is_file() for f in files):
                return root, files
    return None, required


def version(root, file):
    addon = file.split("/")[0]
    name = "QuestieDB_Forever.toc" if addon == "QuestieDB" else addon + ".toc"
    toc = root / addon / name
    if not toc.is_file():
        return ""
    with toc.open(encoding="utf-8-sig", errors="replace") as handle:
        for line in handle:
            match = re.match(r"##\s*Version:\s*(\S+)", line)
            if match:
                return match.group(1)
    return ""


def previous_signatures(meta, files):
    if "reviewSources" in meta:
        return meta["reviewSources"]
    stamp = meta.get("sourceStamp") or {}
    if "sha256" in stamp:
        return {files[0]: stamp["sha256"]}
    if all(Path(f).stem in stamp for f in files):
        return {f: stamp[Path(f).stem]["sha256"] for f in files}
    return {r["path"]: r["sha256"] for r in meta.get("files", []) if r["path"] in files}


def save(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8", delete=False) as stream:
        temp = Path(stream.name)
        json.dump(doc, stream, ensure_ascii=False, indent=1)
        stream.write("\n")
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def latest():
    return load(REVIEW / "report.json")


def scan(progress):
    roots = [Path(root) for root in candidates()]
    rows = []
    for key, (label, required, optional, script, fields) in SOURCES.items():
        progress("检查 " + label)
        name = key + ".json"
        target = UPSTREAM / name
        base_hash = digest(target)
        old = load(target)
        meta = old.get("meta", {})
        root, files = install_for(key, required, roots)
        row = {"id": key, "label": label, "snapshot": name, "previous": meta.get("addonVersion") or meta.get("source", ""),
               "counts": meta.get("counts", {}), "state": "missing", "detail": "缺少已登记的插件文件"}
        rows.append(row)
        if not root:
            continue
        row["version"] = version(root, files[0])
        source_files = files + optional
        current = signatures(root, source_files, roots)
        previous = previous_signatures(meta, source_files)
        if previous and all(current.get(f) == previous.get(f) for f in source_files):
            row.update(state="same", detail="数据文件哈希一致")
            continue
        if not script:
            row.update(state="review", detail="源文件已变化" if previous else "旧快照缺文件哈希，待结构对拍")
            continue
        try:
            with tempfile.TemporaryDirectory() as temp:
                cmd = [sys.executable, "-X", "utf8", str(WEB / "tools" / script),
                       "--src", str(root), "--out-dir", temp]
                if key == "questie-quests-cn" and optional:
                    opt_path = resolve_file(root, optional[0], roots)
                    if opt_path.is_file() and opt_path.parents[2] != root:
                        cmd.extend(["--cn-src", str(opt_path.parents[2])])
                p = subprocess.run(cmd, cwd=WEB, capture_output=True, encoding="utf-8", errors="replace",
                                   timeout=90, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if p.returncode:
                    raise ValueError((p.stderr or p.stdout).strip()[-350:])
                new = load(Path(temp) / name)
            if any(not new.get(f) for f in fields if f != "npcNames"):
                raise ValueError("抽取结果缺少必要记录")
            if signatures(root, source_files, roots) != current:
                raise ValueError("扫描期间源文件已变化，请重新检查")
            new_counts = new.get("meta", {}).get("counts", {})
            if all(new.get(f) == old.get(f) for f in fields):
                row.update(state="same", detail="抽取后的事实字段一致")
                continue
            changes = ["%s %s → %s" % (label, row["counts"][k], new_counts[k])
                       for k, label in COUNTS.items()
                       if k in new_counts and k in row["counts"] and new_counts[k] != row["counts"][k]]
            row.update(state="changed", detail="、".join(changes) or "记录字段变化，条数一致", nextCounts=new_counts)
            new.setdefault("meta", {})["reviewSources"] = current
            save(REVIEW / name, {"baseHash": base_hash, "root": str(root), "sources": current, "data": new})
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            row.update(state="error", detail=str(exc))
    report = {"checkedAt": datetime.now().astimezone().isoformat(timespec="seconds"), "rows": rows}
    save(REVIEW / "report.json", report)
    return report


def apply(key):
    report = latest()
    row = next((r for r in report.get("rows", []) if r["id"] == key and r["state"] == "changed"), None)
    if not row:
        raise ValueError("该快照没有待应用的检查结果")
    name = key + ".json"
    draft = load(REVIEW / name)
    if not draft or digest(UPSTREAM / name) != draft["baseHash"]:
        raise ValueError("本地快照已变化，请重新检查")
    root, files = Path(draft["root"]), draft["sources"]
    roots = [Path(r) for r in candidates()] if any(not (root / f).is_file() for f in files) else None
    if signatures(root, files, roots) != files:
        raise ValueError("插件源已变化，请重新检查")
    save(UPSTREAM / name, draft["data"])
    row.update(state="applied", detail="已写入上游快照")
    save(REVIEW / "report.json", report)
    return {"message": row["label"] + "快照已更新"}
