#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本机 Windows 最新的 wow-forever 成品数据、图标、地图原画及套装表增量同步到局域网 MacBook (192.168.0.101)，
并自动触发 MacBook 上的 video2text/tools/sync_wow_icons.py 更新图文产线资产。

用法：
  python wow-forever-web/tools/sync-to-mac.py
  python wow-forever-web/tools/sync-to-mac.py --host zhangyajun@192.168.0.101
"""
import argparse
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import tarfile
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
WEB_APP = REPO / "wow-forever-web" / "app"
ADDONS_DIR = pathlib.Path(r"C:/GAME/World of Warcraft/_forever_/Interface/AddOns")

REMOTE_FOREVER_APP = "~/Documents/project/wow-forever/wow-forever-web/app"
REMOTE_V2T = "~/Documents/project/video2text"


def extract_flb_sets():
    """从本机 ForeverLevelingBiS 插件提取套装 ID、中英文名、件数与物品 ID 列表（仅取事实字段）。"""
    sets_lua = ADDONS_DIR / "ForeverLevelingBiS" / "Data" / "Sets.lua"
    if not sets_lua.is_file():
        return []
    text = sets_lua.read_text(encoding="utf-8")
    zh_map = {}
    m_zh = re.search(r"zhCN\s*=\s*\{([^\}]+)\}", text)
    if m_zh:
        for km in re.finditer(r"\[(\d+)\]\s*=\s*\"([^\"]+)\"", m_zh.group(1)):
            zh_map[int(km.group(1))] = km.group(2)
    out = []
    for m in re.finditer(r"\{id=(\d+),name=\"([^\"]+)\",level=(\d+),items=\{([^\}]+)\}", text):
        sid = int(m.group(1))
        name_en = m.group(2)
        level = int(m.group(3))
        items = [int(x) for x in re.findall(r"\d+", m.group(4))]
        out.append({
            "id": sid,
            "nameCn": zh_map.get(sid, name_en),
            "nameEn": name_en,
            "level": level,
            "items": items,
            "pieces": len(items),
        })
    return out


def collect_local_files():
    """收集需要同步到 MacBook 的成品 JSON（不含 upstream）、图标和原画文件。"""
    files = {}
    data_dir = WEB_APP / "data"
    for p in sorted(data_dir.rglob("*.json")):
        if "upstream" in p.parts:
            continue
        rel = p.relative_to(WEB_APP).as_posix()
        files[rel] = p
    img_dir = WEB_APP / "img"
    for sub in ("icons", "art"):
        target = img_dir / sub
        if not target.is_dir():
            continue
        for p in sorted(target.rglob("*")):
            if p.is_file():
                rel = p.relative_to(WEB_APP).as_posix()
                files[rel] = p
    return files


def get_remote_manifest(host):
    """在 MacBook 端计算目标目录下已有文件的 (size, sha1) 以实现秒级增量对比。"""
    remote_py = f"""
import hashlib, json, os, pathlib
root = pathlib.Path(os.path.expanduser("{REMOTE_FOREVER_APP}"))
out = {{}}
if root.is_dir():
    for sub in ("data", "img/icons", "img/art"):
        d = root / sub
        if not d.is_dir(): continue
        for p in d.rglob("*"):
            if not p.is_file() or "upstream" in p.parts: continue
            rel = p.relative_to(root).as_posix()
            st = p.stat()
            if rel.startswith("data/"):
                h = hashlib.sha1(p.read_bytes()).hexdigest()[:12]
                out[rel] = [st.st_size, h]
            else:
                out[rel] = [st.st_size, ""]
print(json.dumps(out))
"""
    proc = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", host, "python3", "-"],
        input=remote_py.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError("SSH 连接 MacBook 失败: " + proc.stderr.decode("utf-8", "ignore"))
    return json.loads(proc.stdout.decode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="zhangyajun@192.168.0.101", help="MacBook SSH 地址")
    ap.add_argument("--full", action="store_true", help="强制全量同步")
    args = ap.parse_args()

    t0 = time.time()
    local_files = collect_local_files()
    remote_map = {} if args.full else get_remote_manifest(args.host)

    to_send = []
    total_bytes = 0
    for rel, path in local_files.items():
        st = path.stat()
        rem = remote_map.get(rel)
        if rem is not None:
            if rel.startswith("data/"):
                h = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
                if rem[0] == st.st_size and rem[1] == h:
                    continue
            else:
                if rem[0] == st.st_size:
                    continue
        to_send.append((rel, path))
        total_bytes += st.st_size

    sets_data = extract_flb_sets()
    sets_bytes = json.dumps({"updatedAt": time.strftime("%Y-%m-%d"), "sets": sets_data},
                            ensure_ascii=False, indent=2).encode("utf-8")

    print(f"[sync-to-mac] 扫描 {len(local_files)} 个本地文件，需增量传输 {len(to_send)} 个（{total_bytes/1024/1024:.2f} MB）+ 套装表 {len(sets_data)} 套")

    if to_send or sets_data:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for rel, path in to_send:
                tar.add(str(path), arcname=rel)
            if sets_data:
                info = tarfile.TarInfo(name="data/_flb_item_sets.json")
                info.size = len(sets_bytes)
                info.mtime = int(time.time())
                tar.addfile(info, io.BytesIO(sets_bytes))
        payload = buf.getvalue()
        print(f"[sync-to-mac] 压缩包大小 {len(payload)/1024/1024:.2f} MB，正在通过 SSH 写入 MacBook...")
        cmd = f"mkdir -p {REMOTE_FOREVER_APP} && tar -xzf - -C {REMOTE_FOREVER_APP}"
        proc = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", args.host, cmd],
            input=payload,
            capture_output=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError("解压失败: " + proc.stderr.decode("utf-8", "ignore"))

    # 触发 MacBook video2text 同步脚本
    sync_cmd = f"cd {REMOTE_V2T} && python3 tools/sync_wow_icons.py"
    proc2 = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", args.host, sync_cmd],
        capture_output=True,
        timeout=60,
    )
    out_txt = proc2.stdout.decode("utf-8", "ignore").strip()
    err_txt = proc2.stderr.decode("utf-8", "ignore").strip()
    if proc2.returncode != 0:
        print("[sync-to-mac] 警告：MacBook sync_wow_icons.py 退出非 0：", err_txt, file=sys.stderr)
        return proc2.returncode
    print(f"[sync-to-mac] 完成（耗时 {time.time()-t0:.1f}s）：\n{out_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
