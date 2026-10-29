#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把成品里失效的 `_shuju/<发布号>/` 来源 URL 重挂到当前号，逐字验证过了才改。

为什么要它：参考站的结构化数据放在 `/_shuju/<发布号>/` 下，**号会随上游发版轮换，旧号直接 404**。
2026-10-28 实测：挂 967 条的 `r-1792976599011/changes.json` 与挂 47 条的
`r-1791987485943/chengjiu.json` 都已 404，导致译名体检 912 条"未命中"——词条没错，是证据链断了。
有刷新链的板块重跑一次链就会带上当前号；**成就这类没有链的板块只能靠这个脚本手工重挂**。

安全线：① 默认只报告不落盘，`--write` 才写；② 每条都要在新快照里逐字找得到它的名称或引用，
找不到就不改，列出来给人看——**不许为了"链接好看"把来源指向一个没承载这条内容的页**；
③ 改了哪几条、为什么改，都写进 `note` 与 `checkedAt`，不静默改。

用法：
    python3 tools/rehang-shuju-source.py            # 干跑，只列会改什么
    python3 tools/rehang-shuju-source.py --write    # 落盘
"""
import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "app", "data")
BASE = "https://wowforever.wclbox.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BUILD_RE = re.compile(r"/_shuju/(r-\d+)/")
TODAY = date.today().isoformat()


def curl(url):
    p = subprocess.run(["curl", "-sSL", "--http1.1", "--max-time", "40", "-A", UA, url],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError("抓不到 %s：%s" % (url, p.stderr.decode("utf-8", "replace")[:120]))
    return p.stdout.decode("utf-8", "replace")


def current_release():
    """发布号不写死，跟抓取器一样从页面现读。"""
    for page in ("shuju", "fuben", "gaidong"):
        try:
            m = BUILD_RE.search(curl("%s/%s" % (BASE, page)))
        except RuntimeError:
            continue
        if m:
            return m.group(1)
    sys.exit("没在页面里找到 _shuju 发布号，上游可能改了目录结构")


def entry_text(entry):
    """一条记录里能拿去逐字比对的中文：名称、引用、说明性整句。"""
    out = []
    for key in ("name", "nameCn", "cn", "title"):
        v = entry.get(key)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    for prov in entry.get("provenance") or []:
        if isinstance(prov.get("quote"), str) and prov["quote"].strip():
            out.append(prov["quote"].strip())
    return out


def http_status(url):
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                        "--http1.1", "--max-time", "30", "-A", UA, url],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (p.stdout.decode("utf-8", "replace").strip() or "?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="真的改文件（默认只报告）")
    args = ap.parse_args()

    release = current_release()
    print("当前发布号：%s" % release)
    corpus = {}
    changed_total = 0
    for path in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        with io.open(path, encoding="utf-8") as f:
            doc = json.load(f)
        touched = skipped = 0
        urls = set()

        def walk(node):
            """成品里 provenance 挂在不同层级（列表项、组、meta），所以整棵树都要走。"""
            if isinstance(node, dict):
                prov = node.get("provenance")
                if isinstance(prov, list):
                    for p in prov:
                        if isinstance(p, dict) and "/_shuju/" in (p.get("url") or ""):
                            urls.add(p["url"])
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(doc)
        stale = [u for u in urls if "/%s/" % release not in u]
        if not stale:
            continue
        # 旧号到底是"死了"还是"还活着但已不是当前号"，note 里要说实话，不能一律写 404
        old_status = {u: http_status(u) for u in stale}
        for old in stale:
            file_name = old.rstrip("/").split("/")[-1]
            new = "%s/_shuju/%s/%s" % (BASE, release, file_name)
            if new not in corpus:
                try:
                    corpus[new] = curl(new)
                except RuntimeError as exc:
                    print("  !! %s 取不到，跳过整组：%s" % (new, exc))
                    corpus[new] = None
        def fix(node):
            nonlocal touched, skipped
            if isinstance(node, dict):
                prov = node.get("provenance")
                if isinstance(prov, list):
                    for p in prov:
                        if not isinstance(p, dict):
                            continue
                        u = p.get("url") or ""
                        if "/_shuju/" not in u or "/%s/" % release in u:
                            continue
                        new = "%s/_shuju/%s/%s" % (BASE, release, u.rstrip("/").split("/")[-1])
                        text = corpus.get(new)
                        if text is None:
                            skipped += 1
                            continue
                        words = entry_text(node)
                        missing = [w for w in words if w not in text]
                        if not words or missing:
                            skipped += 1
                            print("  不改 %s ｜ %s ｜ 新快照里逐字找不到：%s"
                                  % (os.path.basename(path), node.get("id") or node.get("name") or "?",
                                     "、".join(missing[:2]) if missing else "这条没有可比对的中文名"))
                            continue
                        p["url"] = new
                        p["checkedAt"] = TODAY
                        note = (p.get("note") or "").strip()
                        old_id = u.split("/_shuju/")[1].split("/")[0]
                        why = "旧号 %s 已 404" % old_id if old_status.get(u) == "404" \
                            else "旧号 %s 还活着（HTTP %s）但已不是当前发布号" % (old_id, old_status.get(u))
                        tag = "%s 重挂到当前发布号（%s）" % (TODAY, why)
                        p["note"] = (note + "；" + tag) if note else tag
                        touched += 1
                for v in node.values():
                    fix(v)
            elif isinstance(node, list):
                for v in node:
                    fix(v)

        fix(doc)
        if touched:
            changed_total += touched
            print("%s：重挂 %d 条 URL，逐字验证没过而没改 %d 条" % (os.path.relpath(path, ROOT), touched, skipped))
            if args.write:
                with io.open(path, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=1)
                    f.write("\n")
    print("\n合计 %d 条%s" % (changed_total, "" if args.write else "（干跑，没写盘；加 --write 才落盘）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
