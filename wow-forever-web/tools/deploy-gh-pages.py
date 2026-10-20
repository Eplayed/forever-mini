#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把发布包推到 GitHub Pages（Q05 的外网那一步，2026-10-20 站主指定用 Pages）。

三条硬规矩，都是这个仓库踩过的坑：
1) **推的只有构建产物**。源码仓库里全是内部台账（AGENTS / ROLES / docs 下的验收记录 /
   src/data/upstream 第三方原料 / .scratch 插件路径），一次公开推送就全泄了。
   所以这里在仓库外另起一个干净目录 git init，只放 site/ 那一份。
2) **推之前先按包内清单逐文件核一遍哈希**，确认要上线的字节就是 release-package 验过的那一份，
   不是"看着一样"。清单不过直接拒。
3) 站名避开商标词：仓库名默认 wuxian-atlas（取自站内那三个字的拼音 + 中性词），
   不出现 魔兽 / WoW / 暴雪 / 艾泽拉斯。要换名一条命令的事，见 --repo。

用法：
    python3 tools/deploy-gh-pages.py                 # 只准备与核对，不动远端
    python3 tools/deploy-gh-pages.py --push          # 建仓库 / 推 main / 开 Pages
    python3 tools/deploy-gh-pages.py --repo 新名字 --push
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL = os.path.join(ROOT, "release")
STAGE = os.path.join(REL, "ghpages")
DEFAULT_REPO = "wuxian-atlas"

# 公开仓库里绝不许出现的东西（比 release-package 那份更严：那份管包，这份管"公开"）
NEVER = [r"\.log$", r"(^|/)upstream/", r"\.lua$", r"\.tga$", r"\.toc$",
         r"AGENTS\.md$", r"ROLES\.md$", r"(^|/)docs/", r"(^|/)\.git/",
         r"PACKAGE-MANIFEST\.json$", r"(^|/)data-base/", r"manifest\.json$"]

README = u"""# 无限资料站（静态托管）

《魔兽世界：无限》中文资料的**构建产物**仓库，只放编译出来的静态文件，源码与加工过程不在这里。

- 本站是非官方粉丝资料站，与暴雪娱乐及网易无关。
- 页面底部写了每条数据的核对日期；哪些是官方已核、哪些待实测，集中在站内的「溯源与覆盖率」那一页。
- 数据取不到的地方显示「待实测」，不猜、不机翻、不编。

这个目录里的内容全部由上游仓库的 `tools/release-package.py` 生成，
**不要手工改这里的文件**——下一次发布会整体覆盖。
"""


def sh(cmd, cwd=None, cap=False):
    print("  $ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE if cap else None,
                       stderr=subprocess.STDOUT)
    if r.returncode != 0:
        sys.exit("命令非 0：%s\n%s" % (" ".join(cmd), (r.stdout or b"").decode("utf-8", "replace")))
    return (r.stdout or b"").decode("utf-8", "replace") if cap else ""


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def latest_site():
    lj = os.path.join(REL, "latest.json")
    if not os.path.exists(lj):
        sys.exit("没有 release/latest.json，先跑 tools/release-package.py")
    cur = json.load(io.open(lj, encoding="utf-8"))["current"]
    s = os.path.join(REL, cur["package"], "site")
    if not os.path.isdir(s):
        sys.exit("包目录不存在：%s（被轮转删掉了？重跑 release-package）" % s)
    return s, cur


def stage_from(site_dir, cur):
    """把包内容复制进公开工作目录，并逐文件核清单。

    清单从 **tar 里**读，不从目录里读：release-package 打完会把暂存目录里那份
    PACKAGE-MANIFEST.json 删掉（它只是塞进包用的），所以"要上线的字节"必须以包为准。
    这样还顺带验了一件事：磁盘上那份 site/ 没被人动过。"""
    import tarfile
    tgz = os.path.join(REL, cur["tar"])
    if not os.path.exists(tgz):
        sys.exit("找不到整包 %s（被轮转删了？重跑 release-package）" % tgz)
    if sha256_file(tgz) != cur["sha256"]:
        sys.exit("整包哈希与 latest.json 记的不一致：这个包别用，先查是谁动过")
    with tarfile.open(tgz) as t:
        mem = [m for m in t.getmembers() if m.name.endswith("PACKAGE-MANIFEST.json")]
        if not mem:
            sys.exit("包里找不到 PACKAGE-MANIFEST.json")
        man = json.load(io.BytesIO(t.extractfile(mem[0]).read()))
    want = {f["path"]: f["sha256"] for f in man["files"]}
    if len(want) != cur["files"]:
        sys.exit("清单条数 %d 与摘要里的 %d 不一致" % (len(want), cur["files"]))
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    bad, n = [], 0
    for rel, dig in sorted(want.items()):
        sp = os.path.join(site_dir, rel)
        if not os.path.exists(sp):
            bad.append("清单有、目录里没有：%s" % rel)
            continue
        if sha256_file(sp) != dig:
            bad.append("字节不一致：%s" % rel)
            continue
        dp = os.path.join(STAGE, rel)
        if os.path.dirname(dp):
            os.makedirs(os.path.dirname(dp), exist_ok=True)
        shutil.copy2(sp, dp)
        n += 1
    if bad:
        for b in bad[:10]:
            print("  ✗ " + b)
        sys.exit("清单核对没过（%d 条），不部署" % len(bad))
    print("  逐文件核过 %d / %d，全部与清单一致" % (n, len(want)))
    # 公开目录里再扫一遍禁含（清单本身、内部文档都不许进）
    leak = []
    for dirpath, _n, fns in os.walk(STAGE):
        for fn in fns:
            rel = os.path.relpath(os.path.join(dirpath, fn), STAGE).replace(os.sep, "/")
            for pat in NEVER:
                if re.search(pat, rel):
                    leak.append("%s 命中 %s" % (rel, pat))
    if leak:
        for l in leak[:10]:
            print("  ✗ " + l)
        sys.exit("公开目录里有不该公开的东西（%d 条），不部署" % len(leak))
    io.open(os.path.join(STAGE, ".nojekyll"), "w").write("")
    io.open(os.path.join(STAGE, "README.md"), "w", encoding="utf-8").write(README)
    print("  禁含扫描干净；补 .nojekyll 与公开 README")
    return man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="真建仓库并推送（默认只准备与核对）")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="GitHub 仓库名（决定 Pages 地址）")
    ap.add_argument("--site", default=None, help="指定包目录（默认取 release/latest.json）")
    a = ap.parse_args()

    site_dir, cur = (a.site, {"package": "manual", "files": 0}) if a.site else latest_site()
    if a.site:                                   # 手工指目录时没有清单计数，按清单本身走
        cur = dict(cur)
    print("[1/3] 暂存公开目录并核清单（来源 %s）" % os.path.relpath(site_dir, ROOT))
    man = stage_from(site_dir, cur)
    print("      → %s" % STAGE)

    owner = sh(["gh", "api", "user", "--jq", ".login"], cap=True).strip()
    url = "https://%s.github.io/%s/" % (owner, a.repo)
    print("[2/3] 目标：%s（owner=%s）" % (url, owner))

    if not a.push:
        print("[3/3] 没加 --push：只准备到这里。")
        print("      要部署：python3 tools/deploy-gh-pages.py --repo %s --push" % a.repo)
        return

    print("[3/3] 推送并开 Pages")
    if os.path.isdir(os.path.join(STAGE, ".git")):
        shutil.rmtree(os.path.join(STAGE, ".git"))
    sh(["git", "init", "-b", "main"], cwd=STAGE)
    sh(["git", "config", "user.name", "zyjwb1482"], cwd=STAGE)
    sh(["git", "config", "user.email", "zyjwb1482@users.noreply.github.com"], cwd=STAGE)
    sh(["git", "add", "-A"], cwd=STAGE)
    msg = "deploy %s\n\n包 %s\n整包 SHA-256 %s\n逐文件清单哈希 %s\n文件 %d 个" % (
        cur.get("builtAt", ""), cur["package"], cur["sha256"],
        man["fileManifestSha256"], len(man["files"]))
    sh(["git", "commit", "-m", msg], cwd=STAGE)
    out = sh(["gh", "repo", "list", owner, "--limit", "200", "--json", "name",
              "--jq", "map(.name) | join(\",\")"], cap=True)
    if a.repo in out.split(","):
        print("  仓库已存在，直接推")
        # gh 2.92 没有 repo set-remote 这个子命令（第一次部署时踩到），自己加 origin 最省事
        remote = "https://github.com/%s/%s.git" % (owner, a.repo)
        has = subprocess.run(["git", "remote", "get-url", "origin"], cwd=STAGE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        sh(["git", "remote", "add" if not has else "set-url", "origin", remote], cwd=STAGE)
    else:
        sh(["gh", "repo", "create", a.repo, "--public", "--source", ".", "--remote", "origin"],
           cwd=STAGE)
    sh(["git", "push", "-u", "origin", "main", "--force"], cwd=STAGE)
    # Pages：项目站，源就是 main 分支根目录
    r = subprocess.run(["gh", "api", "repos/%s/%s/pages" % (owner, a.repo)],
                       cwd=STAGE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode == 0:
        print("  Pages 已开过，推一次就会重建")
    else:
        sh(["gh", "api", "repos/%s/%s/pages" % (owner, a.repo), "-X", "POST",
            "-f", "build_type=legacy", "-f", "source[branch]=main", "-f", "source[path]=/"],
           cwd=STAGE)
        print("  Pages 已开启（main / 根目录）")
    print("地址 %s —— 构建通常 1–2 分钟，用这条看进度：" % url)
    print("  gh api repos/%s/%s/pages --jq .status" % (owner, a.repo))
    print("验收：python3 tools/pkg-verify.py --live %s --site %s" % (url, os.path.relpath(site_dir, ROOT)))


if __name__ == "__main__":
    main()
