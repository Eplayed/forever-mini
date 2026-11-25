#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Windows 端轻传感器：只检查本机魔兽客户端导出（ziliao-export）与本地插件（Interface/AddOns）
是否真的发生内容变动（按文件 SHA-256 哈希判定，不只看 .toc 版本号）。

职责分工：
  - 公网网页源（wclbox / cwf-bis60 / wago / 官方网 / CDN / Everloot / NGA）交由 MacBook 定时自查；
  - 本机 Windows 只管「客户端导出」与「本地插件原件」：
      无变化 → 2 秒内直接退出 0；
      有变化（或 --force）→ 抽取最新插件快照 upstream/*.json 并增量同步 tools/ + upstream/ + listfile 到 MacBook。

用法：
  python wow-forever-web/tools/win-client-sensor.py              # 检查变动，有变动才抽取并同步到 MacBook
  python wow-forever-web/tools/win-client-sensor.py --check-only # 只查不抽不推
  python wow-forever-web/tools/win-client-sensor.py --force      # 强制全量对齐 tools/ + upstream/ + listfile 到 MacBook
  python wow-forever-web/tools/win-client-sensor.py --trigger-mac # 同步后远程触发 MacBook 跑一次合并校验
"""
import argparse
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
WEB_DIR = TOOLS_DIR.parent
UPSTREAM_DIR = WEB_DIR / "app" / "data" / "upstream"
STATE_FILE = TOOLS_DIR / "admin" / "reconcile" / "win-sensor-state.json"

sys.path.insert(0, str(TOOLS_DIR))
from addons_root import candidates as addon_candidates, export_root, listfile_csv

REMOTE_HOST_DEFAULT = "zhangyajun@192.168.0.101"
REMOTE_WEB_DIR = "~/Documents/project/wow-forever/wow-forever-web"

# Windows 本地插件真实数据文件监视表（按文件 SHA-256 判变动，不只看 .toc 版本号）
ADDON_WATCH = {
    "df-loot": {
        "label": "DungeonsForever 副本首领与掉落",
        "files": ["DungeonsForever/Core/Data/Data_DungeonLoot.lua"],
        "extract": ["extract-df-loot.py"],
    },
    "df-geo": {
        "label": "DungeonsForever 副本坐标",
        "files": [
            "DungeonsForever/Core/Data/Data_DungeonEntry.lua",
            "DungeonsForever/Core/Data/Data_BossPos.lua",
        ],
        "extract": ["extract-df-geo.py"],
    },
    "df-bis": {
        "label": "DungeonsForeverGear 配装与 60 级团前",
        "files": [
            "DungeonsForeverGear/Core/Data/Data_BIS.lua",
            "DungeonsForeverGear/Core/Data/Data_BisPreset.lua",
            "DungeonsForeverGear/Core/Data/Data_BisRank.lua",
            "DungeonsForeverGear/Core/Data/Data_GearVendorGoods.lua",
            "DungeonsForeverGear/Core/Data/Data_GearVendors.lua",
        ],
        "extract": ["extract-df-bis.py", "extract-df-bis60.py"],
    },
    "df-raid-sets": {
        "label": "DungeonsForever 海加尔峰 T1 目录",
        "files": ["DungeonsForever/Core/Data/Data_RaidSets.lua"],
        "extract": ["extract-raid-sets.py"],
    },
    "flb-sets": {
        "label": "ForeverLevelingBiS 14-58 级套装",
        "files": ["ForeverLevelingBiS/Data/Sets.lua"],
        "extract": ["extract-flb-sets.py --upstream-only"],
    },
    "questie": {
        "label": "QuestieDB 任务与掉落",
        "files": [
            "QuestieDB/QuestieDB_Forever.toc",
            "QuestieDB/support/Forever/DropTables/classicItemDrops.lua",
            "QuestieDB/support/Forever/DropTables/itemDropCorrections.lua",
        ],
        "extract": ["extract-questie-drops.py", "extract-questie-quests-cn.py"],
    },
    "gi": {
        "label": "GearInsight_Forever 宏/宠物/配方/任务/存在性",
        "files": [
            "GearInsight_Forever/MacroData.lua",
            "GearInsight_Forever/PetData.lua",
            "GearInsight_Forever/ProfRecipes.lua",
            "GearInsight_Forever/DungeonQuestData.lua",
            "GearInsight_Forever/ItemMissingData.lua",
        ],
        "extract": [
            "extract-gi-macros.py",
            "extract-gi-pets.py",
            "extract-gi-prof-recipes.py",
            "extract-gi-dungeon-quests.py",
            "extract-gi-item-existence.py",
        ],
    },
}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def resolve_addon_file(rel: str, roots: list[pathlib.Path]):
    for root in roots:
        cand = root / rel
        if cand.is_file():
            return cand
    return None


def scan_current_state():
    roots = [pathlib.Path(r) for r in addon_candidates()]
    exp = pathlib.Path(export_root())
    client_sig = {}
    for rel in ("export-manifest.json", "listfile/client-fdid-name.csv", "3d-provenance-manifest.json"):
        p = exp / rel
        if p.is_file():
            st = p.stat()
            client_sig[rel] = {"size": st.st_size, "sha": sha256_file(p)}

    addons_sig = {}
    for key, cfg in ADDON_WATCH.items():
        fmap = {}
        for rel in cfg["files"]:
            found = resolve_addon_file(rel, roots)
            if found:
                fmap[rel] = {"size": found.stat().st_size, "sha": sha256_file(found)}
        addons_sig[key] = fmap

    return {
        "checkedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "exportRoot": str(exp),
        "client": client_sig,
        "addons": addons_sig,
    }


def load_prev_state():
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def diff_states(prev, curr):
    changed_client = prev.get("client") != curr.get("client")
    changed_addons = []
    prev_addons = prev.get("addons") or {}
    for key, fmap in curr.get("addons", {}).items():
        if fmap and prev_addons.get(key) != fmap:
            changed_addons.append(key)
    return changed_client, changed_addons


def run_extractors(keys):
    ran, failed = [], []
    for key in keys:
        cfg = ADDON_WATCH[key]
        for spec in cfg["extract"]:
            parts = spec.split()
            script = parts[0]
            extra_args = parts[1:]
            sp = TOOLS_DIR / script
            if not sp.is_file():
                continue
            print(f"  ▶ 抽取 {spec} ({cfg['label']})")
            p = subprocess.run(
                [sys.executable, str(sp)] + extra_args,
                cwd=str(WEB_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            if p.returncode == 0:
                ran.append(script)
            else:
                tail = (p.stderr or p.stdout or "").strip().splitlines()[-3:]
                failed.append((script, " | ".join(tail)))
                print(f"    ✗ 失败 (rc={p.returncode}): {' | '.join(tail)}")
    return ran, failed


def sync_bundle_to_mac(host: str, include_tools: bool = True, include_listfile: bool = True):
    """增量同步 upstream/*.json + tools/ + 核心成品基底 + listfile 到 MacBook。"""
    items = []  # (arcname, local_path)

    if UPSTREAM_DIR.is_dir():
        for p in sorted(UPSTREAM_DIR.glob("*.json")):
            items.append((f"app/data/upstream/{p.name}", p))

    # 同步成品 data/*.json（含 talents/ 与 side-rail.json）确保 Mac 基底一致
    data_dir = WEB_DIR / "app" / "data"
    for p in sorted(data_dir.rglob("*.json")):
        if "upstream" in p.parts:
            continue
        rel = p.relative_to(WEB_DIR).as_posix()
        items.append((rel, p))

    if include_tools:
        for p in sorted(TOOLS_DIR.iterdir()):
            if p.is_file() and p.suffix in (".py", ".js", ".sh", ".json"):
                items.append((f"tools/{p.name}", p))

    if include_listfile:
        lf = pathlib.Path(listfile_csv())
        if lf.is_file():
            items.append(("ziliao-export/listfile/client-fdid-name.csv", lf))

    # 先在 Mac 端收集 (size, sha1_12) 跳过未变化文件
    remote_py = f"""
import hashlib, json, os, pathlib
root = pathlib.Path(os.path.expanduser("{REMOTE_WEB_DIR}"))
out = {{}}
for sub in ("app/data", "tools", "ziliao-export/listfile"):
    d = root / sub
    if not d.is_dir(): continue
    for p in d.rglob("*"):
        if not p.is_file(): continue
        rel = p.relative_to(root).as_posix()
        st = p.stat()
        h = hashlib.sha1(p.read_bytes()).hexdigest()[:12] if st.st_size < 15_000_000 else ""
        out[rel] = [st.st_size, h]
print(json.dumps(out))
"""
    probe = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6", host, "/usr/local/bin/python3", "-"],
        input=remote_py.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )
    if probe.returncode != 0:
        raise RuntimeError("SSH 连接 MacBook 失败: " + probe.stderr.decode("utf-8", "ignore"))
    remote_map = json.loads(probe.stdout.decode("utf-8"))

    to_send = []
    total_bytes = 0
    for arc, local in items:
        st = local.stat()
        rem = remote_map.get(arc)
        if rem is not None:
            if st.st_size < 15_000_000:
                h = hashlib.sha1(local.read_bytes()).hexdigest()[:12]
                if rem[0] == st.st_size and rem[1] == h:
                    continue
            elif rem[0] == st.st_size:
                continue
        to_send.append((arc, local))
        total_bytes += st.st_size

    print(f"[win-client-sensor] 对比 {len(items)} 份文件 → 需增量同步 {len(to_send)} 份（{total_bytes/1024/1024:.2f} MB）")
    if not to_send:
        return 0

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for arc, local in to_send:
            tar.add(str(local), arcname=arc)
    payload = buf.getvalue()

    unpack_cmd = (
        f"mkdir -p {REMOTE_WEB_DIR} && "
        f"tar -xzf - -C {REMOTE_WEB_DIR} && "
        f"chmod +x {REMOTE_WEB_DIR}/tools/*.sh 2>/dev/null || true"
    )
    push = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, unpack_cmd],
        input=payload,
        capture_output=True,
        timeout=120,
    )
    if push.returncode != 0:
        raise RuntimeError("增量推送至 MacBook 失败: " + push.stderr.decode("utf-8", "ignore"))
    print(f"[win-client-sensor] 推送完成（压缩传输 {len(payload)/1024/1024:.2f} MB）")
    return len(to_send)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default=REMOTE_HOST_DEFAULT, help="MacBook SSH 地址")
    ap.add_argument("--check-only", action="store_true", help="只检查客户端与插件变动，不抽取不同步")
    ap.add_argument("--force", action="store_true", help="强制同步 tools/ + upstream/ + listfile 到 MacBook")
    ap.add_argument("--no-extract", action="store_true", help="强制同步时跳过本地插件重抽")
    ap.add_argument("--trigger-mac", action="store_true", help="同步完成后通知 MacBook 立即跑一次本地合并与校验")
    args = ap.parse_args()

    t0 = time.time()
    prev = load_prev_state()
    curr = scan_current_state()
    changed_client, changed_addons = diff_states(prev, curr)

    print(f"[win-client-sensor] 客户端导出变化={changed_client} | 变动插件组={changed_addons or '无'}")
    if args.check_only:
        return

    if not args.force and not changed_client and not changed_addons:
        print(f"[win-client-sensor] 客户端与本地插件均无变化，跳过抽取与同步（{time.time()-t0:.1f}s）")
        return

    extract_targets = list(changed_addons) if changed_addons else (list(ADDON_WATCH.keys()) if (args.force and not args.no_extract) else [])
    ran, failed = [], []
    if extract_targets:
        ran, failed = run_extractors(extract_targets)

    sent = sync_bundle_to_mac(args.host, include_tools=True, include_listfile=True)

    if not failed:
        save_state(curr)

    if args.trigger_mac:
        print("[win-client-sensor] 触发 MacBook 端增量合并与 video2text 资产同步...")
        trig = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", args.host,
             f"bash {REMOTE_WEB_DIR}/tools/mac-daily-web.sh --merge-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        print(trig.stdout.strip())
        if trig.returncode != 0:
            print("Mac 端合并报错:", trig.stderr.strip(), file=sys.stderr)
            sys.exit(trig.returncode)

    print(f"[win-client-sensor] 完毕：抽取 {len(ran)} 项（失败 {len(failed)}），推送 {sent} 份，耗时 {time.time()-t0:.1f}s")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
