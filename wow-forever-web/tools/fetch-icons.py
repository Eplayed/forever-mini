#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按图标文件名从暴雪官方 CDN 取图，本地留存到 src/img/icons/。

红线：第三方站只给"文件名"这类事实性标识符，图片字节一律从官方 CDN 取，页面里不热链任何第三方域名。
本脚本只允许 --base 指向 render.worldofwarcraft.com，别的域名直接拒绝，防止手滑把别人的图床当素材源。

用法：
    python3 tools/fetch-icons.py race_human_male class_warrior        # 取指定键
    python3 tools/fetch-icons.py --from-json src/data/world.json --field iconKey   # 递归收集该字段再补抓
    python3 tools/fetch-icons.py --list                              # 只报缺哪些，不下载
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(ROOT, "src", "img", "icons")
MANIFEST = os.path.join(ICON_DIR, "manifest.json")
ALLOWED_HOST = "render.worldofwarcraft.com"
BASE = "https://render.worldofwarcraft.com/us/icons/56/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
KEY_RE = re.compile(r"^[a-z0-9_]{3,64}$")


def fetch(url):
    """官方 CDN 对默认证书链会报错，依次试系统证书 → certifi → 系统 curl。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as r:
            return r.status, r.read()
    except Exception:
        pass
    try:
        import certifi
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context(cafile=certifi.where())) as r:
            return r.status, r.read()
    except Exception:
        pass
    p = subprocess.run(["curl", "-s", "-L", "-m", "25", "-A", UA, "-w", "\\n%{http_code}\\n", url],
                       capture_output=True)
    body = p.stdout
    idx = body.rfind(b"\n")
    m = re.search(rb"(\d{3})\s*$", body.strip())
    code = int(m.group(1)) if m else 0
    data = re.sub(rb"\n?\d{3}\s*$", b"", body)
    return code, data


def is_jpeg(b):
    return bool(b) and b[:3] == b"\xff\xd8\xff"


def load_keys(args):
    keys = list(args.keys or [])
    if args.from_json:
        path = args.from_json
        if not os.path.isabs(path):
            path = os.path.join(ROOT, path)
        doc = json.load(io.open(path, encoding="utf-8"))
        found = []

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == args.field and isinstance(v, str) and KEY_RE.match(v):
                        found.append(v)
                    else:
                        walk(v)
            elif isinstance(node, list):
                for x in node:
                    walk(x)
        walk(doc)
        keys += found
    out = []
    for k in keys:
        if not KEY_RE.match(k):
            print(u"  跳过非法键名：%s" % k)
            continue
        if k not in out:
            out.append(k)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*", help=u"图标文件名（不带 .jpg）")
    ap.add_argument("--from-json", help=u"从某个数据文件里递归收集字段值")
    ap.add_argument("--field", default="iconKey")
    ap.add_argument("--list", action="store_true", help=u"只报告本地缺哪些键")
    args = ap.parse_args()

    if not os.path.isdir(ICON_DIR):
        os.makedirs(ICON_DIR)
    keys = load_keys(args)
    if not keys:
        sys.exit(u"没有要处理的图标键")

    have = set(f[:-4] for f in os.listdir(ICON_DIR) if f.endswith(".jpg"))
    if args.list:
        miss = [k for k in keys if k not in have]
        print(u"待查 %d 键，本地已有 %d，缺 %d：%s" % (len(keys), len(keys) - len(miss), len(miss),
                                            u"、".join(miss[:20])))
        return

    today = datetime.date.today().isoformat()
    ok, missing, skipped = [], [], []
    for k in keys:
        if k in have:
            skipped.append(k)
            continue
        code, body = fetch(BASE + k + ".jpg")
        if code == 200 and is_jpeg(body) and len(body) > 500:
            with open(os.path.join(ICON_DIR, k + ".jpg"), "wb") as fh:
                fh.write(body)
            ok.append((k, len(body), hashlib.sha1(body).hexdigest()[:10]))
        else:
            missing.append(k)
        print(u"  %-46s %s %s" % (k, code, u"已存" if k in [x[0] for x in ok] else u"取不到"))

    man = {}
    if os.path.exists(MANIFEST):
        man = json.load(io.open(MANIFEST, encoding="utf-8"))
    total = len([f for f in os.listdir(ICON_DIR) if f.endswith(".jpg")])
    batches = man.get("batches") or []
    batches.append({"at": today, "added": len(ok), "unavailable": missing,
                    "note": u"见本次改动的数据文件 iconKey 字段"})
    man.update({
        "source": BASE,
        "format": "56x56 jpg",
        "fetchedAt": today,
        "total": total,
        "ok": total,
        "missing": missing,
        "batches": batches[-8:],
        "note": u"图标文件名取自上游结构化数据或第三方资料站的事实性标识符，图片一律从暴雪官方 CDN 取回本地留存，页面不热链。"
                u"属游戏美术素材：如需整体下线，删除本目录即可回退到自绘占位图标。"
    })
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(man, ensure_ascii=False, indent=1) + "\n")
    print(u"新增 %d 张（跳过已有 %d），官方 CDN 取不到 %d：%s" % (
        len(ok), len(skipped), len(missing), u"、".join(missing) or u"无"))
    print(u"目录合计 %d 张，manifest 已更新" % total)


if __name__ == "__main__":
    main()
