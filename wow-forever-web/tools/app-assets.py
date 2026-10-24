#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 app/data 与 app/img 同步进 app/public/，供 Vite 开发与构建使用。

为什么不直接把 publicDir 指到 app/：构建会把 data 与 img 之外的东西一起卷进产物。
这里只搬数据与素材，且做增量（大小或 mtime 变了才拷），11 MB 图标不会每次全量重拷。

数据仍然只有一份真相：app/data/*.json。新站运行时读的就是这里的副本，构建前必须先跑本脚本。

用法：
    python3 tools/app-assets.py            # 增量同步
    python3 tools/app-assets.py --clean    # 先清空 public 再同步
    python3 tools/app-assets.py --check    # 只报告差了多少个文件（含 public 里的孤儿副本），不写
    python3 tools/app-assets.py --prune    # 删掉 public 里 app/ 源目录已经没有的副本

2026-10-20 Q05 补的一条：增量同步**只加不删**，所以源目录里撤掉的素材会留在 public/ 与 dist/ 里继续被服务。
实测过一次：把一张种族小图标从素材目录删掉，页面仍然拿得到（public 里那份旧副本），
"素材已撤下"这件事在浏览器里完全看不出来——发布包就会带着一份没人认领的素材上线。
--check 现在把这种孤儿也算进差异，--prune 单独删孤儿（不想全量重拷 11 MB 时用）。
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # wow-forever-web
SRC = os.path.join(ROOT, "app")
PUB = os.path.join(ROOT, "app", "public")
# 顶层要搬的目录（相对 app/）
DIRS = ["data", "img"]
# 单独指定的文件：(源路径相对 app/, 落到 public 的路径)。
# 头标源在 app/img/ 里（make-favicon.py 的产出），但 index.html 按站点根去要它们。
FILES = [("img/favicon.svg", "img/favicon.svg"),
         ("img/favicon.ico", "favicon.ico"),
         ("img/apple-touch-icon.png", "apple-touch-icon.png")]
# 明确不搬的子目录与文件（相对 app/）。
# ① app/data/upstream/ 是第三方站与插件的原料快照，只在本机参与合并，不发公网——
#    2026-10-20 Q05 第一次跑打包卡口才抓到：这 54 份一直跟着 data/ 整目录被复制进
#    public/ 再进 dist/，等于把加工原料一起上线。
# ② 三份 img/**/manifest.json 是我们的**加工台账**（每张图的抓取地址、哈希、日期，
#    还有天裔那张的插件目录路径），不是页面运行时要读的东西——运行读的是 data/art.json 与
#    data/icons.json。台账留在源目录（进 git，出问题能回查），不上公网：
#    把 394 条抓取源清单原样发出去，等于把自己的加工过程交给同行。
# 被排除的文件会被 --check 判成孤儿、--prune 删掉，构建链不会再带上它们。
#
# 2026-10-23 改成按规则排，不再一个目录一个目录手写死：那天新加了 img/keyart/，
# 台账跟着进来但没人补这条名单，deploy-gh-pages 的禁含闸在 3,883 个文件里精准抓到它
# （"img/keyart/manifest.json 命中 manifest\.json$"）并拒绝部署。
# 写死名单的毛病就是**每加一个素材目录都要记得回来补一次**，忘了就把加工台账发上公网。
# 规则：img/ 下任何一层目录里的 manifest.json 都不进产物（页面运行读的是
# data/art.json 与 data/icons.json，要用的字段由 fetch-art.py 从台账现算）。
EXCLUDE = ["data/upstream"]


def excluded(rel):
    r = rel.replace(os.sep, "/")
    if any(r == e or r.startswith(e + "/") for e in EXCLUDE):
        return True
    return r.startswith("img/") and r.endswith("/manifest.json")


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
                    help="删掉 public 里源目录已经没有的副本（孤儿素材）")
    a = ap.parse_args()

    if not os.path.isdir(SRC):
        sys.exit("找不到新站目录 %s" % SRC)
    # 头标这类单点文件缺了必须响：public 里往往还留着上一轮的副本，静默跳过等于
    # "站根没有图标"这件事在本地永远看不出来。
    missing = [s for s, _ in FILES if not os.path.isfile(os.path.join(SRC, s))]
    if missing:
        sys.exit("app/ 里缺头标源文件：%s（跑 python3 tools/make-favicon.py 重生成）" % "、".join(missing))
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
                if excluded(os.path.join(rel, fn)):
                    continue           # 单个文件级排除（img/**/manifest.json 这类台账）
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
    for s_rel, d_rel in FILES:
        sp = os.path.join(SRC, s_rel)
        dp = os.path.join(PUB, d_rel)
        if need_copy(sp, dp):
            stale += 1
            if not a.check:
                if not os.path.isdir(os.path.dirname(dp)):
                    os.makedirs(os.path.dirname(dp))
                shutil.copy2(sp, dp)
                copied += 1

    # 孤儿副本：public/{data,img} 下有、源目录里没有的那些。增量同步不删它们，
    # 所以撤素材必须显式 --prune（或 --clean），否则发布包里还带着。
    # 键统一用相对 app/ 的路径：app/data/x.json ↔ public/data/x.json
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
                if excluded(os.path.join(rel, fn)):
                    continue           # 排除掉的不算"应该有"，于是它们在 public 里的副本会被判成孤儿
                want.add(os.path.join("public", os.path.relpath(os.path.join(dirpath, fn), SRC)))
    for _s_rel, d_rel in FILES:
        want.add(os.path.join("public", d_rel))
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
        print("清掉孤儿副本 %d 个（public 里源目录已经没有的素材/数据）" % len(orphans))
        if not a.check:
            return

    if a.check:
        print("public 与 app/ 源目录差 %d 个文件（要同步就去掉 --check）" % stale)
        if orphans:
            print("其中 %d 个是 public 里的孤儿副本（源目录已经没有了，增量同步不会删）：%s"
                  % (len(orphans), "、".join(orphans[:5])))
        sys.exit(1 if (stale or orphans) else 0)
    print("同步完成：本次写入 %d 个文件 → app/public/（数据 + 素材 + 头标）" % copied)


if __name__ == "__main__":
    main()
