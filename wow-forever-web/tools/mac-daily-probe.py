#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MacBook 每日定时更新的轻量探针：检查公网 wclbox 发布号 / 构建号 + 本地插件快照指纹 + 距上次更新天数。"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time


def main():
    web = pathlib.Path(os.getcwd())
    state_file = web / "tools" / "admin" / "daily" / "mac-daily-status.json"
    prev = {}
    if state_file.is_file():
        try:
            prev = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            prev = {}

    if len(sys.argv) >= 4 and sys.argv[1] == "--write-status":
        probe = json.loads(sys.argv[2])
        err_cnt = int(sys.argv[3])
        state_file.parent.mkdir(parents=True, exist_ok=True)
        now_s = time.strftime("%Y-%m-%dT%H:%M:%S")
        doc = {
            "checkedAt": now_s,
            "lastUpdatedAt": now_s if err_cnt == 0 else prev.get("lastUpdatedAt", ""),
            "wclboxRelease": probe.get("wclboxRelease"),
            "foreverBuild": probe.get("foreverBuild"),
            "addonFingerprint": probe.get("addonFingerprint"),
            "errorCount": err_cnt,
            "status": "ok" if err_cnt == 0 else "partial_error",
        }
        state_file.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return

    release_id, forever_build = None, None
    try:
        html = subprocess.check_output(
            ["curl", "-sL", "-m", "20", "https://wowforever.wclbox.com/gaidong"],
            timeout=25,
        ).decode("utf-8", "replace")
        m = re.search(r"/_shuju/(r-\d+)/", html)
        if m:
            release_id = m.group(1)
            meta_txt = subprocess.check_output(
                ["curl", "-sL", "-m", "20", f"https://wowforever.wclbox.com/_shuju/{release_id}/meta.json"],
                timeout=25,
            ).decode("utf-8", "replace")
            meta = json.loads(meta_txt)
            forever_build = meta.get("foreverBuild")
    except Exception:
        release_id = prev.get("wclboxRelease")
        forever_build = prev.get("foreverBuild")

    h = hashlib.sha1()
    up_dir = web / "app" / "data" / "upstream"
    if up_dir.is_dir():
        for p in sorted(up_dir.glob("*.json")):
            if p.name.startswith(("df-", "gi-", "questie-", "flb-", "raid-")):
                st = p.stat()
                h.update(f"{p.name}:{st.st_size}:{int(st.st_mtime)}|".encode("utf-8"))
    addon_fp = h.hexdigest()[:12]

    last_ok = prev.get("lastUpdatedAt", "")
    days_old = 999
    if last_ok:
        try:
            t0 = time.mktime(time.strptime(last_ok[:10], "%Y-%m-%d"))
            days_old = int((time.time() - t0) // 86400)
        except Exception:
            days_old = 999

    need_web = (
        (bool(release_id) and release_id != prev.get("wclboxRelease"))
        or (bool(forever_build) and forever_build != prev.get("foreverBuild"))
        or (days_old >= 6)
    )
    need_merge = need_web or (addon_fp != prev.get("addonFingerprint"))

    print(json.dumps({
        "wclboxRelease": release_id,
        "foreverBuild": forever_build,
        "prevRelease": prev.get("wclboxRelease"),
        "prevBuild": prev.get("foreverBuild"),
        "addonFingerprint": addon_fp,
        "prevAddonFingerprint": prev.get("addonFingerprint"),
        "daysSinceLastUpdate": days_old,
        "needWeb": bool(need_web),
        "needMerge": bool(need_merge),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
