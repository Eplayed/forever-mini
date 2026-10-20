#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打上线包（Q05，2026-10-20）。只做本地可执行的那一半：产物、卡口、清单、回滚位。

为什么要有这个脚本而不是"npm run build 完手工拖 dist 上去"：
  1) 发布包必须能回答"这一版到底是哪些字节"——每个文件一个 sha256，整包一个 sha256，
     上一版留着，出事才能说清"退回哪一版"。
  2) 这个仓库里有一堆**绝不能出现在公网**的东西：插件原包与 Data.lua（在仓库外的
     .scratch，但转存的 .tga 有过先例）、src/data/upstream/ 的第三方原料、
     docs/logs 与 *.log、AGENTS/ROLES 这类内部台账。构建产物一旦混进其中一样，
     就是把自己的加工过程发出去。这里逐条卡死，不靠人眼过。
  3) 旧站那 19 个 .html 的链接策略要落地：新站只有 index.html，直接发 dist 的话
     旧链接（别人书签里、别的站里链过来的 talent.html）要么 404、要么被托管方的
     SPA 兜底吞成首页——玩家点了没反应还零报错（这条栽过）。所以打包时按
     app/src/router.js 的 MIGRATED 生成跳转桩，名单只有一份，不会漂。

用法：
    python3 tools/release-package.py                 # 走完整构建链再打包
    python3 tools/release-package.py --skip-build    # 用现有 app/dist 直接打
    python3 tools/release-package.py --check-only    # 只跑卡口与清单，不写包
产物：
    release/<名>/site/            解包后的目录（上传的就是这一份）
    release/<名>.tar.gz           整包（含 PACKAGE-MANIFEST.json）
    release/<名>.tar.gz.sha256    整包哈希
    release/latest.json           当前包 + 上一包（回滚位）
    docs/data-base/release-<今天>/package-summary.json   进仓库的那一份摘要
"""
from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from collections import Counter
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
DIST = os.path.join(APP, "dist")
REL = os.path.join(ROOT, "release")
TODAY = datetime.now().strftime("%Y-%m-%d")
SUM_DIR = os.path.join(ROOT, "docs", "data-base", "release-" + TODAY)

# 包里出现这些就是打包事故，直接拒。每条都写清为什么，将来要放开才知道动的是哪一条。
FORBIDDEN = [
    (r"(^|/)upstream(/|$)", "第三方站的原料快照只在本机参与合并，公网不发"),
    (r"(^|/)[^/]*\.lua$", "插件原包与 Data.lua 是别人的著作，不发"),
    (r"(^|/)[^/]*\.(tga|mpq|toc)$", "客户端/插件原始素材文件不发（转存成品走 img/art，另记 manifest）"),
    (r"(^|/)[^/]*\.log$", "运行日志不发"),
    (r"(^|/)(node_modules|\.git|\.scratch|docs|tools|src)(/|$)", "仓库结构不发，只发构建产物"),
    (r"(^|/)(AGENTS|ROLES|CLAUDE|README)(\.md)?$", "内部台账不发"),
    (r"(^|/)[^/]*\.(map|tsbuildinfo)$", "source map 会把内部路径与注释原样发出去"),
    (r"(^|/)\.env", "环境变量不发"),
]
# 允许进包的扩展名（白名单，比黑名单稳：新出现一种文件就得先想清楚该不该发）
ALLOW_EXT = {".html", ".js", ".css", ".json", ".webp", ".png", ".jpg", ".jpeg",
             ".svg", ".ico", ".woff2", ".woff", ".txt"}


def sha256_file(p, buf=1024 * 1024):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, cwd):
    print("  $ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        sys.exit("构建链非 0 退出（%s）：不打包" % " ".join(cmd))


def build_chain():
    """同步素材 → 数据卡口 → 单测 → 构建。任何一步红都不打包。"""
    print("[1/5] 构建链")
    run([sys.executable, os.path.join(ROOT, "tools", "app-assets.py")], ROOT)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "app-assets.py"), "--check"], cwd=ROOT)
    if r.returncode != 0:
        sys.exit("app-assets --check 非 0：public 与 src 不一致或有孤儿副本，先修再打包")
    run(["node", os.path.join(ROOT, "tools", "build-data.js")], ROOT)
    run(["npx", "vitest", "run"], APP)
    run(["npm", "run", "build"], APP)


def migrated_map():
    """从 app/src/router.js 解析 MIGRATED（旧 html 文件名 → 新路由）。
    只读不写：名单的唯一一份在路由文件里，这里抄一遍是抄"当前真在用的那份"，
    不会再出现第二份需要人同步的表。"""
    s = io.open(os.path.join(APP, "src", "router.js"), encoding="utf-8").read()
    m = re.search(r"export const MIGRATED = \{(.*?)\n\};", s, re.S)
    if not m:
        sys.exit("router.js 里找不到 MIGRATED 表，跳转桩没法生成")
    out = {}
    for k, v in re.findall(r"'([^']+)':\s*'([^']+)'", m.group(1)):
        out[k] = v
    if len(out) < 10:
        sys.exit("MIGRATED 只解析出 %d 条，不像全量，拒打包" % len(out))
    return out


def write_stubs(site_dir, mig):
    """给每个旧页生成一个跳转桩（index.html 除外，那是真页面）。"""
    made = []
    for fn, path in sorted(mig.items()):
        if not fn.endswith(".html") or fn == "index.html":
            continue
        if os.path.exists(os.path.join(site_dir, fn)):
            sys.exit("桩要写的位置已经有真文件了：%s（谁放的？）" % fn)
        # 目标一律相对当前文档算：挂在根目录与挂在 /wow/ 下都能跳对，不写死域名也不写死层级
        body = (u"<!doctype html>\n<html lang=\"zh-CN\">\n<meta charset=\"utf-8\">\n"
                u"<title>这一页搬家了</title>\n"
                u"<meta http-equiv=\"refresh\" content=\"0; url=./#%s\">\n"
                u"<script>var s=location.search||'';location.replace('./#%s'+s);</script>\n"
                u"<p>这一页已经并入新版，正在跳转。没动的话请点"
                u"<a href=\"./#%s\">这里</a>。</p>\n" % (path, path, path))
        io.open(os.path.join(site_dir, fn), "w", encoding="utf-8").write(body)
        made.append(fn)
    return made


def scan(site_dir):
    """遍历产物：算哈希、查禁含、查扩展名白名单。返回 (files, problems)。"""
    files, problems = [], []
    for dirpath, _names, fns in os.walk(site_dir):
        for fn in fns:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, site_dir).replace(os.sep, "/")
            for pat, why in FORBIDDEN:
                if re.search(pat, rel):
                    problems.append("禁含 %s —— %s" % (rel, why))
            ext = os.path.splitext(fn)[1].lower()
            if ext not in ALLOW_EXT:
                problems.append("扩展名不在白名单：%s" % rel)
            files.append({"path": rel, "bytes": os.path.getsize(p), "sha256": sha256_file(p)})
    return files, problems


def gate_files(site_dir, files):
    """产物自身的完整性：index.html 在、引用的每个本地资源在、没有 0 字节文件。"""
    problems = []
    paths = {f["path"] for f in files}
    idx = os.path.join(site_dir, "index.html")
    if not os.path.exists(idx):
        return ["没有 index.html"]
    html = io.open(idx, encoding="utf-8").read()
    for ref in re.findall(r'(?:src|href)="([^"]+)"', html):
        if re.match(r"^(https?:|data:|#|mailto:)", ref):
            problems.append("index.html 里有外链资源（素材必须本地留存）：%s" % ref)
            continue
        rel = ref.split("?")[0].lstrip("./")
        if rel and rel not in paths:
            problems.append("index.html 引用了但包里没有：%s" % rel)
    for f in files:
        if f["bytes"] == 0:
            problems.append("0 字节文件：%s" % f["path"])
    if "data/meta.json" not in paths:
        problems.append("产物里没有 data/meta.json（页面会整片空）")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-build", action="store_true", help="用现有 app/dist，不重跑构建链")
    ap.add_argument("--check-only", action="store_true", help="只跑卡口与清单，不写 tar 不动回滚位")
    ap.add_argument("--keep", type=int, default=2, help="本地保留几版整包（回滚位），默认 2")
    a = ap.parse_args()

    if not a.skip_build:
        build_chain()
    if not os.path.isdir(DIST):
        sys.exit("没有 app/dist，先跑构建")

    print("[2/5] 暂存产物")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                          stdout=subprocess.PIPE).stdout.decode().strip() or "nogit"
    dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                           stdout=subprocess.PIPE).stdout.decode().strip()
    name = "wow-forever-web-%s-%s%s" % (stamp, head, "-dirty" if dirty else "")
    stage = os.path.join(REL, name, "site")
    if os.path.isdir(os.path.join(REL, name)):
        shutil.rmtree(os.path.join(REL, name))
    os.makedirs(os.path.dirname(stage))
    shutil.copytree(DIST, stage)

    print("[3/5] 旧页跳转桩")
    stubs = write_stubs(stage, migrated_map())
    print("  生成 %d 个桩（%s…）" % (len(stubs), ", ".join(stubs[:4])))
    if dirty:
        print("  提醒：工作区有未提交改动，这一版标了 -dirty，不能当发布口径")

    print("[4/5] 卡口")
    files, problems = scan(stage)
    problems += gate_files(stage, files)
    n_data = len([f for f in files if f["path"].startswith("data/")])
    n_img = len([f for f in files if f["path"].startswith("img/")])
    total = sum(f["bytes"] for f in files)
    print("  %d 个文件 / %.1f MB（数据 %d、素材 %d、其它 %d）" % (
        len(files), total / 1048576.0, n_data, n_img, len(files) - n_data - n_img))
    if problems:
        for p in problems[:20]:
            print("  ✗ " + p)
        sys.exit("卡口没过（%d 条），不打包" % len(problems))
    print("  禁含清单、扩展名白名单、index.html 引用、0 字节 全部通过")

    files.sort(key=lambda f: f["path"])
    manifest_sha = hashlib.sha256(
        json.dumps(files, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    # 缓存策略按"文件名里有没有内容哈希"分两类，这一条必须机器判，不能写在文档里靠人记：
    # assets/* 是 vite 打过哈希的，改一行代码就换名，可以放心 immutable 一年；
    # index.html、data/*.json、img/** 没有哈希，托管方若给一个统一的长 max-age，
    # 玩家第二天看到的还是旧数据——本站的数据每天都在改，这一条比省流量重要。
    HASHED_RE = re.compile(r"^assets/.+-[A-Za-z0-9_-]{8}\.(js|css|woff2|woff)$")
    hashed = [f["path"] for f in files if HASHED_RE.match(f["path"])]
    unhashed = [f["path"] for f in files if f["path"].startswith("assets/")]
    problems_assets = ["assets/ 下这个文件名没有内容哈希，不能按 immutable 缓存：%s" % p
                       for p in unhashed if p not in hashed]
    if problems_assets:
        for p in problems_assets[:5]:
            print("  ✗ " + p)
        sys.exit("卡口没过（assets 命名），不打包")
    cache_policy = {
        "assets/*": "public, max-age=31536000, immutable（文件名带内容哈希，换版即换名）",
        "index.html 与 *.html 桩": "no-cache（must-revalidate）——它是指向新哈希资源的唯一入口",
        "data/*.json": "no-cache 或 max-age=60 + 每次发版刷 CDN——文件名不带哈希，长缓存等于把玩家留在旧数据",
        "img/**": "同 data：文件名不带哈希；素材换图必须让托管方主动刷新这一批",
    }
    summary_extra = {"hashedAssets": len(hashed),
                     "unhashedFiles": len(files) - len(hashed),
                     "cachePolicy": cache_policy}
    summary = {
        "kind": "release-package",
        "package": name, "gitHead": head, "worktreeDirty": bool(dirty),
        "builtAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": len(files), "bytes": total,
        "byExt": dict(Counter(os.path.splitext(f["path"])[1].lower() for f in files)),
        "fileManifestSha256": manifest_sha,
        "keyFiles": {f["path"]: f["sha256"] for f in files
                     if f["path"] == "index.html" or f["path"].startswith("assets/")},
        "dataFiles": {f["path"]: f["sha256"] for f in files if f["path"].startswith("data/")},
        "legacyStubs": stubs,
    }
    summary.update(summary_extra)

    if a.check_only:
        print("[5/5] --check-only：不写包。清单摘要：")
        print(json.dumps({k: summary[k] for k in
                          ("package", "files", "bytes", "fileManifestSha256")}, ensure_ascii=False, indent=1))
        # 只验不写的话别把 28 MB 暂存留在盘上（这台机器长期 89%）
        shutil.rmtree(os.path.join(REL, name))
        return

    print("[5/5] 写包与回滚位")
    io.open(os.path.join(stage, "PACKAGE-MANIFEST.json"), "w", encoding="utf-8").write(
        json.dumps({"package": name, "builtAt": summary["builtAt"],
                    "fileManifestSha256": manifest_sha, "files": files},
                   ensure_ascii=False, indent=1) + "\n")
    tgz = os.path.join(REL, name + ".tar.gz")
    with tarfile.open(tgz, "w:gz") as t:
        t.add(stage, arcname=name + "/site")
    pkg_sha = sha256_file(tgz)
    io.open(tgz + ".sha256", "w", encoding="utf-8").write(pkg_sha + "  " + os.path.basename(tgz) + "\n")
    summary["packageSha256"] = pkg_sha

    cur_path = os.path.join(REL, "latest.json")
    prev = None
    if os.path.exists(cur_path):
        prev = json.load(io.open(cur_path, encoding="utf-8")).get("current")
    io.open(cur_path, "w", encoding="utf-8").write(json.dumps(
        {"current": {"package": name, "tar": name + ".tar.gz", "sha256": pkg_sha,
                     "files": len(files), "bytes": total, "gitHead": head,
                     "fileManifestSha256": manifest_sha,
                     "builtAt": summary["builtAt"]},
         "previous": prev}, ensure_ascii=False, indent=1) + "\n")

    # 轮转：只留最近 keep 个整包（磁盘长期 89%，不能无限堆 60MB 的包）
    packs = sorted([f for f in os.listdir(REL) if f.endswith(".tar.gz")])
    for old in packs[:-a.keep] if a.keep > 0 else []:
        base = os.path.join(REL, old)
        for p in (base, base + ".sha256"):
            if os.path.exists(p):
                os.remove(p)
        d = os.path.join(REL, old[:-len(".tar.gz")])
        if os.path.isdir(d):
            shutil.rmtree(d)
    os.remove(stage.rstrip("/") + "/PACKAGE-MANIFEST.json")   # 暂存目录里那份只是塞进 tar 用的

    os.makedirs(SUM_DIR, exist_ok=True)
    io.open(os.path.join(SUM_DIR, "package-summary.json"), "w", encoding="utf-8").write(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    print("整包 %s（%.1f MB）" % (os.path.basename(tgz), os.path.getsize(tgz) / 1048576.0))
    print("整包 sha256 %s" % pkg_sha)
    print("上一包 %s" % ((prev or {}).get("package") or "（这是第一份，没有回滚位）"))
    print("摘要 → %s" % os.path.relpath(os.path.join(SUM_DIR, "package-summary.json"), ROOT))
    print("回滚位 → release/latest.json")
    print("提醒：上传的只有 %s/site/ 这一份；外网验收本轮没做。" % name)


if __name__ == "__main__":
    main()
