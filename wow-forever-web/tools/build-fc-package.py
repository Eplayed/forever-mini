#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 app/dist 打成函数计算 FC 3.0 Web 函数的部署包（release/fc-deploy.zip）。

包结构（与控制台创建页的启动命令对齐）：
    app.py   tools/fc-static-app.py 的副本（监听 9000 的静态服务）
    dist/    Vite 构建产物整目录

为什么是 FC 而不是 OSS：备案门票是函数计算 CU 资源包，域名 CNAME 到 FC Endpoint
是接入一致性最没有争议的一条路（help.aliyun.com 函数计算「配置自定义域名」）。
代码包上限杭州/上海地域 500 MB（控制台上传同口径），本包约 42 MB，余量够。

两条硬闸：① dist/data/meta.json 必须带备案号且链工信部——内地托管没挂备案号就是违规；
② 入口标题不许出现商标词。两条都是"发内地"的前提，不是装饰。
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "app", "dist")
FC_DIR = os.path.join(ROOT, "release", "fc")
ZIP = os.path.join(ROOT, "release", "fc-deploy.zip")
MANIFEST = os.path.join(ROOT, "release", "fc-manifest.json")
ENTRY = os.path.join(ROOT, "tools", "fc-static-app.py")
BEIAN_RE = re.compile(r"^[一-龥]ICP备\d+号(-\d+)?$")
TRADEMARKS = ("魔兽", "魔兽世界", "WoW", "暴雪", "艾泽拉斯")
# 控制台/工具上传 ZIP 的地域上限：杭州、上海等 500 MB，其余 100 MB（官方配额页）
ZIP_HARD_MB = 500
ZIP_WARN_MB = 100


def git_head():
    p = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else "unknown"


def git_dirty():
    p = subprocess.run(["git", "status", "--porcelain", "--", "app"], cwd=ROOT,
                       capture_output=True, text=True)
    return [l[3:].strip() for l in p.stdout.splitlines() if l.strip()]


def main():
    if not os.path.isfile(os.path.join(DIST, "index.html")):
        sys.exit("app/dist 不存在或不完整：先跑 npm --prefix app run build（或 tools/refresh.sh publish）")
    with io.open(os.path.join(DIST, "data", "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    beian = meta.get("beian") or {}
    if not BEIAN_RE.match(beian.get("number") or ""):
        sys.exit("dist/data/meta.json 没有合法备案号（beian.number）——内地托管必须先挂备案号，不打这个包")
    if beian.get("url") != "https://beian.miit.gov.cn/":
        sys.exit("备案号链接必须指向工信部 beian.miit.gov.cn，现在是：%s" % beian.get("url"))
    with io.open(os.path.join(DIST, "index.html"), encoding="utf-8") as f:
        html = f.read()
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    title = title.group(1) if title else ""
    hit = [w for w in TRADEMARKS if w in title]
    if hit:
        sys.exit("入口标题含商标词 %s——上线后就是「备案信息与内容不符」的把柄，先改 app/index.html" % hit)

    if os.path.isdir(FC_DIR):
        shutil.rmtree(FC_DIR)
    os.makedirs(FC_DIR)
    shutil.copyfile(ENTRY, os.path.join(FC_DIR, "app.py"))
    shutil.copytree(DIST, os.path.join(FC_DIR, "dist"))

    files = 0
    dist_bytes = 0
    for base, _dirs, names in os.walk(os.path.join(FC_DIR, "dist")):
        for n in names:
            files += 1
            dist_bytes += os.path.getsize(os.path.join(base, n))
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(os.path.join(FC_DIR, "app.py"), "app.py")
        for base, _dirs, names in os.walk(os.path.join(FC_DIR, "dist")):
            for n in sorted(names):
                full = os.path.join(base, n)
                z.write(full, os.path.relpath(full, FC_DIR))
    zip_bytes = os.path.getsize(ZIP)
    with io.open(ZIP, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    if zip_bytes > ZIP_HARD_MB * 1024 * 1024:
        sys.exit("zip %d MB 超控制台上传上限 %d MB" % (zip_bytes // 1048576, ZIP_HARD_MB))

    manifest = {
        "builtAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gitHead": git_head(),
        "appDirty": git_dirty(),
        "runtime": "python3.10",
        "startCommand": "python3 app.py",
        "listenPort": 9000,
        "beian": beian,
        "title": title.strip(),
        "files": files,
        "distBytes": dist_bytes,
        "zipBytes": zip_bytes,
        "zipSha256": sha,
    }
    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("FC 部署包：%s" % ZIP)
    print("  %d 个文件｜dist %s B｜zip %s B（%.1f MB）" % (files, dist_bytes, zip_bytes, zip_bytes / 1048576))
    print("  sha256 %s" % sha)
    print("  备案号 %s｜标题 %s｜对应提交 %s%s" % (
        beian["number"], title.strip(), manifest["gitHead"],
        "（app/ 有未提交改动：%s）" % "、".join(manifest["appDirty"][:5]) if manifest["appDirty"] else ""))
    if zip_bytes > ZIP_WARN_MB * 1024 * 1024:
        print("  提醒：超 %d MB，只有杭州/上海等放开地域能传，其余地域上限 100 MB" % ZIP_WARN_MB)
    print("  清单：%s" % MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())