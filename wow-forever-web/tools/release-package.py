#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打上线包（Q05，2026-10-20）。只做本地可执行的那一半：产物、卡口、清单、回滚位。

为什么要有这个脚本而不是"npm run build 完手工拖 dist 上去"：
  1) 发布包必须能回答"这一版到底是哪些字节"——每个文件一个 sha256，整包一个 sha256，
     上一版留着，出事才能说清"退回哪一版"。
  2) 这个仓库里有一堆**绝不能出现在公网**的东西：插件原包与 Data.lua（在仓库外的
     .scratch，但转存的 .tga 有过先例）、app/data/upstream/ 的第三方原料、
     docs/logs 与 *.log、AGENTS/ROLES 这类内部台账。构建产物一旦混进其中一样，
     就是把自己的加工过程发出去。这里逐条卡死，不靠人眼过。
  3) 只发新站这一份产物。旧站已于 2026-10-24 删除，旧 .html 地址不再做跳转桩
     （站主拍板"一起撤掉"）——书签里的 talent.html 会 404，这是有意接受的结果。
     要恢复老地址的承接，得先在 app/src/router.js 之外重新写一份映射与桩。

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
# .glb 是 2026-10-28 补的：配装页那一栏的占位模型（10-26 上线的那条）从那天起就进不了包，
# 白名单里没有这个扩展名，打包卡口直接拦红——也就是那一版根本发不出去。
# 放开的是扩展名，不是来源：下面只允许自产占位与已登记、逐哈希校验的
# 本机客户端整人模型；第三方站模型仍拦。
ALLOW_EXT = {".html", ".js", ".css", ".json", ".webp", ".png", ".jpg", ".jpeg",
             ".svg", ".ico", ".woff2", ".woff", ".txt", ".glb"}


def self_generated_models():
    """本站自产模型的白名单（相对 img/ 的路径）。清单读不到就一个都不许进包。"""
    p = os.path.join(ROOT, "app", "img", "models", "manifest.json")
    ok = set()
    try:
        man = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return ok
    if man.get("origin") != "self-generated":
        return ok
    for it in man.get("items") or []:
        if it.get("file"):
            ok.add("img/models/" + it["file"])
    return ok


SELF_GEN_MODELS = self_generated_models()


def approved_real_models():
    """网页真实模型白名单；清单与站点登记必须逐项一致。"""
    try:
        man = json.load(io.open(os.path.join(ROOT, "app", "img", "models", "real", "manifest.json"), encoding="utf-8"))
        art = json.load(io.open(os.path.join(ROOT, "app", "data", "art.json"), encoding="utf-8"))
    except Exception:
        return {}
    real = art.get("bisRealModels") or {}
    if man.get("origin") != "client-derived" or real.get("origin") != "client-derived":
        return {}
    if man.get("clientProduct") != "wowf" or not man.get("clientBuild"):
        return {}
    registered = {it.get("file"): it for it in real.get("items") or []}
    listed = man.get("items") or []
    if len(registered) != len(listed):
        return {}
    ok = {}
    for it in listed:
        rel = it.get("file") or ""
        match = registered.get(rel)
        if not re.fullmatch(r"img/models/real/[a-z0-9-]+\.glb", rel) or not match:
            return {}
        if it.get("placementVerdict") != "PASS" or match.get("placementVerdict") != "PASS":
            return {}
        if any(match.get(k) != it.get(k) for k in
               ("setId", "faction", "raceId", "bodyType", "file", "bytes", "sha256",
                "visibleItems", "dollSnapshot", "displayWeaponItems")):
            return {}
        if not isinstance(it.get("bytes"), int) or it["bytes"] <= 0:
            return {}
        if not re.fullmatch(r"[0-9a-f]{64}", it.get("sha256") or ""):
            return {}
        ok[rel] = (it["bytes"], it["sha256"])
    return ok if len(ok) == len(listed) else {}


REAL_MODELS = approved_real_models()

# 一进来就先记"工作树脏不脏"。构建链自己会重写 scale.json / search.json 这类派生件，
# 等跑完构建再查 git 状态，每一次都会被判成 -dirty（2026-10-28 打包时撞见），
# 那个标记报的就不是"这份源码没提交"而是"我刚跑完构建"——等于永远为真。
DIRTY_AT_START = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                                stdout=subprocess.PIPE).stdout.decode().strip()


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
    print("[1/4] 构建链")
    run([sys.executable, os.path.join(ROOT, "tools", "app-assets.py")], ROOT)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "app-assets.py"), "--check"], cwd=ROOT)
    if r.returncode != 0:
        sys.exit("app-assets --check 非 0：public 与 app/ 源目录不一致或有孤儿副本，先修再打包")
    run(["node", os.path.join(ROOT, "tools", "build-data.js")], ROOT)
    run(["npx", "vitest", "run"], APP)
    run(["npm", "run", "build"], APP)


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
            size, digest = os.path.getsize(p), sha256_file(p)
            if ext == ".glb":
                if rel in REAL_MODELS:
                    if (size, digest) != REAL_MODELS[rel]:
                        problems.append("%s 与客户端真实模型清单哈希或字节数不一致" % rel)
                elif rel not in SELF_GEN_MODELS:
                    problems.append("%s 未列入已核模型清单，不发" % rel)
            files.append({"path": rel, "bytes": size, "sha256": digest})
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


def dist_is_current():
    """打包前必查：app/dist 里的数据与素材是不是 app/data、app/img 的现在这一份。

    为什么单独设这道卡：--skip-build 跳过的是构建，但 public/ 只在 vite build 那一刻
    从源目录复制一次——**改了 app/data 却带着 --skip-build 打包，会得到一份"仓库里是新的、
    包里是旧的"的产物，而且全程零报错**。这一条我自己踩过（2026-10-21 那次发出去
    的 releases.json 少一条，靠线上核对才发现），所以判据放在打包这一步，不指望人记得。
    """
    bad = []
    # 不搬清单从 app-assets.py 那一份读，不在这儿再抄一遍：抄了就会漂，
    # 漂的结果是把"故意不发布的内部台账"当成漏文件报出来（这次就差点这么红一次）。
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "appassets", os.path.join(ROOT, "tools", "app-assets.py"))
    _aa = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_aa)
    # 排除规则只认 app-assets.py 那一份，这里不再抄一遍实现：
    # 2026-10-23 就是因为这里把 EXCLUDE 抄成"逐条前缀匹配"，app-assets 改成
    # "img/ 下任何 manifest.json 都不进产物"之后两边对不上，打包直接判 dist 少 5 个文件。
    skipped = _aa.excluded
    for d in ('data', 'img'):
        s_dir = os.path.join(ROOT, "app", d)
        for dirpath, names, fns in os.walk(s_dir):
            # 与 app-assets.py 同一套相对法：rel 是相对 app/ 的，EXCLUDE 也是相对 app/ 写的
            rel_dir = os.path.relpath(dirpath, os.path.join(ROOT, "app")).replace(os.sep, "/")
            if skipped(rel_dir):
                names[:] = []
                continue
            for fn in fns:
                if fn.startswith('.') or fn.endswith('.pyc') or skipped(os.path.join(rel_dir, fn)):
                    continue
                sp = os.path.join(dirpath, fn)
                dp = os.path.join(APP, "dist", rel_dir, fn)
                if not os.path.exists(dp):
                    bad.append("dist 里没有：%s" % os.path.join(rel_dir, fn))
                elif sha256_file(sp) != sha256_file(dp):
                    bad.append("内容不一致：%s" % os.path.join(rel_dir, fn))
    return bad


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
    stale = dist_is_current()
    if stale:
        for s in stale[:10]:
            print("  ✗ " + s)
        sys.exit("app/dist 不是 app/data、app/img 的现在这一份（%d 处）。带 --skip-build 打包会发出旧数据——"
                 "去掉 --skip-build 重跑构建链，或先跑 tools/app-assets.py + npm run build" % len(stale))
    print("app/dist 与 app/data、app/img 逐文件对过，是现在这一份")

    print("[2/4] 暂存产物")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                          stdout=subprocess.PIPE).stdout.decode().strip() or "nogit"
    dirty = DIRTY_AT_START
    name = "wow-forever-web-%s-%s%s" % (stamp, head, "-dirty" if dirty else "")
    stage = os.path.join(REL, name, "site")
    if os.path.isdir(os.path.join(REL, name)):
        shutil.rmtree(os.path.join(REL, name))
    os.makedirs(os.path.dirname(stage))
    shutil.copytree(DIST, stage)
    if dirty:
        print("  提醒：工作区有未提交改动，这一版标了 -dirty，不能当发布口径")

    print("[3/4] 卡口")
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
    # 2026-10-24 旧站删除后多了一个 .svg：index.html 里那颗头标现在指的是 app/img/favicon.svg，
    # 文件真的在 app/ 下了，vite 就当资源打包并加哈希（以前那个路径在 app/ 里不存在，
    # 引用只是从 public/ 原样过一遍）。扩展名写死在这里就会漏认，判据是"文件名带不带内容哈希"。
    HASHED_RE = re.compile(r"^assets/.+-[A-Za-z0-9_-]{8}\.(js|css|woff2|woff|svg)$")
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
        "index.html": "no-cache（must-revalidate）——它是指向新哈希资源的唯一入口",
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
    }
    summary.update(summary_extra)

    if a.check_only:
        print("[4/4] --check-only：不写包。清单摘要：")
        print(json.dumps({k: summary[k] for k in
                          ("package", "files", "bytes", "fileManifestSha256")}, ensure_ascii=False, indent=1))
        # 只验不写的话别把 28 MB 暂存留在盘上（这台机器长期 89%）
        shutil.rmtree(os.path.join(REL, name))
        return

    print("[4/4] 写包与回滚位")
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
