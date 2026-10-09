#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 ../src/data 与 ../src/img 同步进 app/public/，供 Vite 开发与构建使用。

为什么不直接把 publicDir 指到 ../src：那样旧站的 14 个 html、旧 js/css 会一起被卷进新站的构建产物，
两栈边界就糊了。这里只搬数据与素材，且做增量（大小或 mtime 变了才拷），11 MB 图标不会每次全量重拷。

数据仍然只有一份真相：src/data/*.json。新站运行时读的就是这里的副本，构建前必须先跑本脚本。

用法：
    python3 tools/app-assets.py            # 增量同步
    python3 tools/app-assets.py --clean    # 先清空 public 再同步
    python3 tools/app-assets.py --check    # 只报告差了多少个文件，不写
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


def need_copy(s, d):
    if not os.path.exists(d):
        return True
    ss, ds = os.stat(s), os.stat(d)
    return ss.st_size != ds.st_size or int(ss.st_mtime) != int(ds.st_mtime)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--check", action="store_true")
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
        for dirpath, _names, files in os.walk(s):
            rel = os.path.relpath(dirpath, SRC)
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

    if a.check:
        print("public 与 src 差 %d 个文件（要同步就去掉 --check）" % stale)
        sys.exit(1 if stale else 0)
    print("同步完成：本次写入 %d 个文件 → app/public/（数据 + 素材 + 头标）" % copied)


if __name__ == "__main__":
    main()
