#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 ../src/data 与 ../src/img 同步进 app/public/，供 Vite 开发与构建使用。

为什么不直接把 publicDir 指到 ../src：那样旧站的 14 个 html、旧 js/css 会一起被卷进新站的构建产物，
两栈边界就糊了。这里只搬数据与素材，且做增量（大小或 mtime 变了才拷），11 MB 图标不会每次全量重拷。

数据仍然只有一份真相：src/data/*.json。新站运行时读的就是这里的副本，构建前必须先跑本脚本。

用法：
    python3 tools/app-assets.py            # 增量同步
    python3 tools/app-assets.py --clean    # 先清空 public 再同步
    python3 tools/app-assets.py --check    # 只报告差了多少个文件（含 public 里的孤儿副本），不写
    python3 tools/app-assets.py --prune    # 删掉 public 里 src 已经没有的副本

2026-10-20 Q05 补的一条：增量同步**只加不删**，所以 src 里撤掉的素材会留在 public/ 与 dist/ 里继续被服务。
实测过一次：把一张种族小图标从 src 删掉，页面仍然拿得到（public 里那份旧副本），
"素材已撤下"这件事在浏览器里完全看不出来——发布包就会带着一份没人认领的素材上线。
--check 现在把这种孤儿也算进差异，--prune 单独删孤儿（不想全量重拷 11 MB 时用）。
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # wow-forever-web
SRC = os.path.join(ROOT, "src")
PUB = os.path.join(ROOT, "app", "public")
# 顶层要搬的目录与文件（favicon 类是 index.html 直接引用的）
DIRS = ["data", "img"]
FILES = ["favicon.ico", "apple-touch-icon.png", "img/favicon.svg"]
# 明确不搬的子目录（相对 src/）。src/data/upstream/ 是第三方站与插件的原料快照，
# 只在本机参与合并，不发公网——2026-10-20 Q05 第一次跑打包卡口才抓到：
# 这 54 份一直跟着 data/ 整目录被复制进 public/ 再进 dist/，等于把加工原料一起上线。
# 列在这里之后它们会被 --check 判成孤儿、--prune 删掉，构建链不会再带上它们。
EXCLUDE = ["data/upstream"]


def excluded(rel):
    r = rel.replace(os.sep, "/")
    return any(r == e or r.startswith(e + "/") for e in EXCLUDE)


def need_copy(s, d):
    if not os.path.exists(d):
        return True
    ss, ds = os.stat(s), os.stat(d)
    return ss.st_size != ds.st_size or int(ss.st_mtime) != int(ds.st_mtime)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--prune", action="store_true",
                    help="删掉 public 里 src 已经没有的副本（孤儿素材）")
    a = ap.parse_args()

    if not os.path.isdir(SRC):
        sys.exit("找不到旧站目录 %s" % SRC)
    if a.clean and os.path.isdir(PUB) and not a.check:
        shutil.rmtree(PUB)

    copied = stale = 0
    for d in DIRS:
        s = os.path.join(SRC, d)
        if not os.path.isdir(s):
            continue
        for dirpath, names, files in os.walk(s):
            rel = os.path.relpath(dirpath, SRC)
            if excluded(rel):
                names[:] = []          # 整棵子树跳过，不进去也不建目录
                continue
            dst_dir = os.path.join(PUB, rel)
            for fn in files:
                if fn.endswith(".pyc") or fn.startswith("."):
                    continue
                sp = os.path.join(dirpath, fn)
                dp = os.path.join(dst_dir, fn)
                if need_copy(sp, dp):
                    stale += 1
                    if a.check:
                        continue
                    if not os.path.isdir(dst_dir):
                        os.makedirs(dst_dir)
                    shutil.copy2(sp, dp)
                    copied += 1
    for rel in FILES:
        sp = os.path.join(SRC, rel)
        if not os.path.exists(sp):
            continue
        dp = os.path.join(PUB, rel)
        if need_copy(sp, dp):
            stale += 1
            if not a.check:
                if not os.path.isdir(os.path.dirname(dp)):
                    os.makedirs(os.path.dirname(dp))
                shutil.copy2(sp, dp)
                copied += 1

    # 孤儿副本：public/{data,img} 下有、src 下没有的那些。增量同步不删它们，
    # 所以撤素材必须显式 --prune（或 --clean），否则发布包里还带着。
    # 键统一用相对 app/ 的路径：src/data/x.json ↔ public/data/x.json
    want = set()
    for d in DIRS:
        s_dir = os.path.join(SRC, d)
        if not os.path.isdir(s_dir):
            continue
        for dirpath, names, files in os.walk(s_dir):
            rel = os.path.relpath(dirpath, SRC)
            if excluded(rel):
                names[:] = []
                continue
            for fn in files:
                if fn.endswith(".pyc") or fn.startswith("."):
                    continue
                want.add(os.path.join("public", os.path.relpath(os.path.join(dirpath, fn), SRC)))
    for rel in FILES:
        if os.path.exists(os.path.join(SRC, rel)):
            want.add(os.path.join("public", rel))
    orphans = []
    if os.path.isdir(PUB):
        for dirpath, _n, files in os.walk(PUB):
            for fn in files:
                rp = os.path.relpath(os.path.join(dirpath, fn), os.path.join(ROOT, "app"))
                if rp not in want:
                    orphans.append(rp)
    if a.prune:
        for rp in orphans:
            os.remove(os.path.join(ROOT, "app", rp))
        print("清掉孤儿副本 %d 个（public 里 src 已经没有的素材/数据）" % len(orphans))
        if not a.check:
            return

    if a.check:
        print("public 与 src 差 %d 个文件（要同步就去掉 --check）" % stale)
        if orphans:
            print("其中 %d 个是 public 里的孤儿副本（src 已经没有了，增量同步不会删）：%s"
                  % (len(orphans), "、".join(orphans[:5])))
        sys.exit(1 if (stale or orphans) else 0)
    print("同步完成：本次写入 %d 个文件 → app/public/（数据 + 素材 + 头标）" % copied)


if __name__ == "__main__":
    main()
