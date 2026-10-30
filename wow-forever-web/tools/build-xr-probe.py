#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组装"仅供扫码真机验证"的隔离小程序预览工程 xr-probe/。

为什么要单独一个工程（2026-10-30 复核指出的第二个坑）：正式小程序的
`packOptions.ignore` 把 `tmp-model/` 排除了，**开发者工具里能看到磁盘文件 ≠ 扫码预览包带了这份文件**。
要拿真机证据，就得有一个"探针页就是首页、两份 GLB 真的进包"的工程，
而不是去改正式工程的打包排除规则（那会让 1.6 MB 样本有机会被传到线上）。

它做的事：
  1) 复制探针页与场景组件（唯一真源仍在 for-mini/pages/model-probe/，这里只是拷贝），
     并把样本目录从 /tmp-model/ 改写成 /probe-model/；
  2) app.json 的 pages[0] 就是探针页 —— 扫码后直接落在这一页，不要人在手机里输路径；
  3) 原件从 app/img/models/real/ 取（先核 art.json 登记的 SHA），PNG 候选调
     derive-glb-textures.py 现做（不在这里另写一套 GLB 转换）；
  4) 打印打包清单：每个文件的字节与两份 GLB 的 SHA-256，并核主包 2 MB 上限。
     超了就报错让人改用 --only webp / --only png 分两个码，不许删模型凑体积。
"""
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
REPO = os.path.dirname(ROOT)
WEB = os.path.join(ROOT, "app")
PROBE_SRC = os.path.join(REPO, "for-mini", "pages", "model-probe")
OUT_DIR = os.path.join(REPO, "xr-probe")
REMOTE_DIR = os.path.join(REPO, "xr-probe-remote")
MODEL_DIR_NAME = "probe-model"
MAIN_PKG_LIMIT = 2 * 1024 * 1024          # 微信主包上限 2 MB
APP_ID = "wxfd9a2b985a6cedc3"             # 与正式小程序同一个号：预览码要用这个 AppID 才扫得开


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def registered_source():
    art = json.load(io.open(os.path.join(WEB, "data", "art.json"), encoding="utf-8"))
    for it in (art.get("bisRealModels") or {}).get("items") or []:
        if it.get("setId") == "hunter" and it.get("faction") == "alliance":
            return it
    raise SystemExit("art.json 里没有 hunter/alliance 的登记，探针不该继续")


def write(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)


def copy_page(dst_root, keep, remote_url):
    """把探针页与场景组件拷进隔离工程；顺手改写样本目录、远端地址与"这次包里到底有哪几档"。"""
    out_pages = os.path.join(dst_root, "pages", "model-probe")
    if os.path.isdir(out_pages):
        shutil.rmtree(out_pages)
    shutil.copytree(PROBE_SRC, out_pages)
    js = os.path.join(out_pages, "index.js")
    t = io.open(js, encoding="utf-8").read()
    t = t.replace("const MODEL_DIR = '/tmp-model/'", "const MODEL_DIR = '/%s/'" % MODEL_DIR_NAME)
    if remote_url:
        t = t.replace("const REMOTE_URL = ''", "const REMOTE_URL = %s" % json.dumps(remote_url), 1)
    # 只留这次真能测的档：留一个点得开却 404 的按钮，等于给真机留一条假证据
    t = re.sub(r"(const SRC = \{[\s\S]*?\n\})",
               lambda m: "\n".join([l for l in m.group(1).split("\n")
                                    if not re.match(r"^\s+([a-z]+):", l) or l.split(":")[0].strip() in keep]),
               t, count=1)
    if 'const SRC = {' in t:
        body = t.split("const SRC = {")[1].split("\n}")[0]
        if not re.search(r"\b%s\b\s*:" % keep[0], body):
            raise SystemExit("改写把 SRC 档位删空了（keep=%s）" % keep)
    write(js, t)
    wxml = os.path.join(out_pages, "index.wxml")
    u = io.open(wxml, encoding="utf-8").read()
    def keep_btn(m):
        return m.group(0) if re.search(r"data-w=\"(%s)\"" % "|".join(keep), m.group(0)) else ""
    u = re.sub(r"[ \t]*<view class=\"btn[^\n]*?</view>\n", keep_btn, u)
    write(wxml, u)
    return out_pages


SRC_VALUES = {
    "blank": "",
    "webp": "hunter-alliance.glb",
    "png": "hunter-alliance-png.glb",
    "remote": "",
    "dl": ""
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["webp", "png"], help="只打其中一份模型（两份合计超包体时用）")
    ap.add_argument("--remote", help="B2：包里不放 GLB，改成从这条 beta HTTPS 地址取（与 --only 互斥）")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    remote = args.remote
    if remote and args.only:
        raise SystemExit("--remote 与 --only 是两件事：远端探针不在包里放模型")
    if remote:
        if not remote.startswith("https://"):
            raise SystemExit("--remote 要的是 https 地址（微信只认 https）")
        if not remote.endswith(".glb"):
            raise SystemExit("--remote 指向的不是 .glb，先核对文件名")

    reg = registered_source()
    src_glb = os.path.join(WEB, reg["file"])
    got = sha256_file(src_glb)
    if got != reg["sha256"]:
        raise SystemExit("源 GLB 的 SHA 与登记不符（%s ≠ %s）——先查清是谁改了" % (got[:12], reg["sha256"][:12]))
    if os.path.getsize(src_glb) != reg["bytes"]:
        raise SystemExit("源 GLB 字节与登记不符")

    out = args.out or (REMOTE_DIR if remote else OUT_DIR)
    models = os.path.join(out, MODEL_DIR_NAME)
    if os.path.isdir(models):
        shutil.rmtree(models)

    keep = ["blank"]
    if remote:
        keep += ["remote", "dl"]      # ④ 直接给 xr-asset-load，⑤ 先 downloadFile 到本机再给场景
    else:
        os.makedirs(models)
        if args.only in (None, "webp"):
            shutil.copy2(src_glb, os.path.join(models, SRC_VALUES["webp"]))
            keep.append("webp")
        if args.only in (None, "png"):
            subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "derive-glb-textures.py"),
                                   "--file", reg["file"],
                                   "--out", os.path.join(models, "hunter-alliance-png.glb"), "--format", "PNG"],
                                  cwd=ROOT)
            keep.append("png")

    write(os.path.join(out, "app.json"), json.dumps({
        "pages": ["pages/model-probe/index"],
        "window": {"navigationBarTitleText": "3D 探针（远端扫码专用）" if remote else "3D 探针（扫码预览专用）",
                   "navigationBarBackgroundColor": "#0b0f16",
                   "navigationBarTextStyle": "white", "backgroundColor": "#0b0f16", "backgroundTextStyle": "light"},
        "style": "v2",
        "lazyCodeLoading": "requiredComponents",
        "sitemapLocation": "sitemap.json"
    }, ensure_ascii=False, indent=2) + "\n")
    write(os.path.join(out, "app.js"), "App({})\n")
    shutil.copy2(os.path.join(REPO, "for-mini", "app.wxss"), os.path.join(out, "app.wxss"))
    write(os.path.join(out, "sitemap.json"),
          json.dumps({"desc": "仅供真机验证，不被索引", "rules": [{"action": "disallow", "page": "*"}]},
                     ensure_ascii=False) + "\n")
    write(os.path.join(out, "project.config.json"), json.dumps({
        "compileType": "miniprogram",
        "appid": APP_ID,
        "projectname": "xr-probe" + ("-remote" if remote else ("-" + args.only if args.only else "")),
        "setting": {"es6": True, "postcss": True, "minified": False, "urlCheck": False,
                    "checkInvalidKey": False, "compileHotReLoad": False},
        # 这里刻意没有任何 packOptions.ignore：远端版要证的就是"包里没有模型也取得到"
        "packOptions": {"ignore": []}
    }, ensure_ascii=False, indent=2) + "\n")
    copy_page(out, keep, remote)
    write(os.path.join(out, "README.md"), (
        "# %s —— 仅供扫码真机验证的隔离工程\n\n"
        "由 `python3 wow-forever-web/tools/build-xr-probe.py%s` 生成，不要手改，也不要发布。\n"
        % (os.path.basename(out), " --remote <beta HTTPS 地址>" if remote else "")
        + ("这个工程**包内没有任何 GLB**，要回答的是：xr-frame 能不能直接从本站 OSS 的 https 地址取到模型"
           "（④ 直接把地址给 xr-asset-load；⑤ 先 wx.downloadFile 落到本机临时文件再交给场景，两条路各自一条结论）。\n"
           if remote else
           "探针页真源在 `for-mini/pages/model-probe/`；两份 GLB 一份是从 `art.json` 登记核过 SHA 的原件、\n"
           "一份是 `derive-glb-textures.py` 现做的 PNG 候选。本工程不排除任何文件，模型必须进预览包。\n")
        + "本目录整体可以从仓库删除，删掉即回到没有探针的状态。\n")
    )

    # 改写坏了宁可不出码：生成的每个 js 都过一遍 node --check（引号/逗号错了就是这里红）
    for dirpath, _dirs, files in os.walk(out):
        for fn in files:
            if not fn.endswith(".js"):
                continue
            p_js = os.path.join(dirpath, fn)
            r = subprocess.run(["node", "--check", p_js], capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit("生成的 %s 语法不对（改写坏了）：\n%s" % (os.path.relpath(p_js, out), r.stderr[:600]))
    print("产物语法自检：node --check 全过")

    # 打包清单：逐文件列出来，并核两份 GLB 的哈希与主包上限
    total = 0
    lines = []
    glbs = []
    for dirpath, dirnames, filenames in os.walk(out):
        dirnames.sort()
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            b = os.path.getsize(p)
            total += b
            rel = os.path.relpath(p, out)
            if fn.endswith(".glb"):
                glbs.append(rel)
            lines.append("%9d  %s%s" % (b, rel, ("  sha256 " + sha256_file(p)[:16] + "…")
                                        if rel.startswith(MODEL_DIR_NAME) else ""))
    print("\n".join(lines))
    print("合计 %d B（%.2f MB）· 主包上限 %d B · 档位 %s" % (total, total / 1048576.0, MAIN_PKG_LIMIT, keep))
    if remote:
        if glbs:
            raise SystemExit("远端探针的包里出现了 GLB（%s）——那就测不出远端能不能取到了" % ", ".join(glbs))
        js_txt = io.open(os.path.join(out, "pages", "model-probe", "index.js"), encoding="utf-8").read()
        if remote not in js_txt:
            raise SystemExit("生成的页面里没有那条地址，改写没生效")
        print("包内 GLB：0 份 · 页面取数地址：\n  " + remote)
    else:
        for m in keep:
            if m == "blank":
                continue
            p = os.path.join(models, SRC_VALUES[m])
            if not os.path.isfile(p):
                raise SystemExit("预览包里缺 %s" % p)
    if total > MAIN_PKG_LIMIT:
        raise SystemExit("超主包 2 MB 上限：改用 --only webp 与 --only png 分两个预览码，不许删模型凑体积")
    print("工程 → %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
