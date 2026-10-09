#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 git 历史生成 src/data/changelog.json —— 本站数据变更日志。

为什么要它：首页要"有东西在更新"，但红线不做新闻流与转载评论。最诚实的做法是报我们自己做了什么：
每一条都对应仓库里一个真实提交，改了哪个板块、哪一天，全部可回溯，不写一句没法验证的话。

界面不显示提交哈希与文件路径（那是面向开发的东西），只显示日期 + 提交标题 + 板块标签；
板块标签由路径映射成中文，映射不到的按"其他"处理，不猜。

用法：
    python3 tools/build-changelog.py            # 重新生成
    python3 tools/build-changelog.py --since 2026-10-01
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # wow-forever-web
REPO = os.path.dirname(ROOT)                                           # monorepo 根
OUT = os.path.join(ROOT, "src", "data", "changelog.json")

# 路径前缀 → 界面显示的板块名（顺序即优先级，命中第一个就用）
SCOPE = [
    ("src/data/talents", "天赋数据"), ("src/data/talent-text", "天赋文本"),
    ("src/data/world.json", "世界数据"), ("src/data/professions.json", "专业数据"),
    ("src/data/dungeons.json", "副本数据"), ("src/data/races.json", "种族数据"),
    ("src/data/glossary.json", "术语词条"), ("src/data/abilities.json", "技能四态"),
    ("src/data/changes.json", "改动清单"), ("src/data/timeline.json", "上线时间表"),
    ("src/data/changelog.json", "变更日志"), ("src/data/scale.json", "规模快照"),
    ("src/data/meta.json", "口径与未决项"), ("src/data/upstream", "上游快照"),
    ("src/img/icons", "图标"), ("src/img/art", "客户端原画"),
    ("src/js", "界面逻辑"), ("src/css", "样式"), ("src/", "页面"),
    ("tools/", "卡口与脚本"), ("docs/screenshots", "截图证据"), ("docs/", "文档"),
    ("for-mini", "小程序"), ("ROLES.md", "交接台账"), ("AGENTS.md", "协作规则"),
]
# 只动这些的提交不进"数据变更日志"——它们没改玩家能看到的东西
NON_CONTENT = set(["文档", "截图证据", "交接台账", "协作规则"])

# 提交标题里会写文件名与脚本名，那是面向开发的话，不能原样进玩家看的页面。
# 这里把它们换成板块中文名；认不出的 *.json 归"数据文件"、*.py / *.js 归"脚本"。
GLOSS = [
    (r"scale\.json", "规模快照"), (r"changes\.json", "改动清单"), (r"world\.json", "世界数据"),
    (r"professions\.json", "专业数据"), (r"changelog\.json", "变更日志"), (r"icons?\.json", "图标映射"),
    (r"dungeons\.json", "副本数据"), (r"races\.json", "种族数据"), (r"glossary\.json", "术语词条"),
    (r"abilities\.json", "技能四态"), (r"timeline\.json", "上线时间表"), (r"meta\.json", "口径文件"),
    (r"talent-text/?\*", "天赋文本"), (r"talents/\*", "天赋数据"), (r"src/data/upstream", "上游快照"),
    (r"build-data\.js", "校验脚本"), (r"site-check\.py", "回归脚本"), (r"export-mini\.js", "导出脚本"),
    (r"audit-translations\.py", "体检脚本"), (r"build-icon-map\.py", "图标派生脚本"),
    (r"fetch-icons\.py", "图标抓取脚本"), (r"fetch-art\.py", "原画转存脚本"),
    (r"scrape-wclbox-[a-z]+\.py", "抓取脚本"), (r"merge-[a-z]+\.js", "整形脚本"),
    (r"extract-[a-z]+\.py", "抽取脚本"), (r"build-changelog\.py", "日志脚本"),
    (r"tools/\S+", "脚本"), (r"\bD\.coverage\(\)", "页面侧那份算法"),
    (r"\bicon-gaps\.json", "缺图登记"), (r"\bworld\.html", "世界页"), (r"\bindex\.html", "首页"),
    (r"\b[\w./-]+\.(json|md|html)", "数据文件"), (r"\b[\w./-]+\.(py|js|css)", "脚本"),
]


def gloss(subject):
    out = subject
    for pat, rep in GLOSS:
        out = re.sub(pat, rep, out)
    return out


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if p.returncode != 0:
        raise SystemExit("git 失败：%s" % p.stderr.decode("utf-8", "replace")[:200])
    return p.stdout.decode("utf-8", "replace")


def tags_for(paths):
    got = []
    for rel in paths:
        r = rel.split("wow-forever-web/", 1)[-1] if "wow-forever-web/" in rel else rel
        for pre, name in SCOPE:
            if r.startswith(pre):
                if name not in got:
                    got.append(name)
                break
        else:
            if "其他" not in got:
                got.append("其他")
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-10-01")
    ap.add_argument("--max", type=int, default=40)
    a = ap.parse_args()

    sep, us = "\x1e", "\x1f"
    # 分隔符放在每条记录最前面：git 的 --name-only 会把文件列表接在标题之后的空行里，
    # 分隔符放末尾会把文件列表划到下一条记录去（第一次跑就是 0 条，栽在这）。
    raw = git("log", "--no-merges", "--date=short",
              "--pretty=format:" + sep + "%ad" + us + "%h" + us + "%s",
              "--name-only", "--since=" + a.since)
    entries = []
    for chunk in raw.split(sep):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue
        lines = chunk.split("\n")
        head = lines[0].split(us)
        if len(head) < 3:
            continue
        date, subject = head[0], us.join(head[2:]).strip()
        paths = [x.strip() for x in lines[1:] if x.strip()]
        if not paths:
            continue
        tags = tags_for(paths)
        if not [t for t in tags if t not in NON_CONTENT]:
            continue          # 只改文档/台账/截图的提交不进"数据变更日志"
        entries.append({"date": date, "subject": gloss(subject), "tags": tags, "files": len(paths)})
    entries = entries[:a.max]

    payload = {
        "meta": {
            "generatedAt": datetime.date.today().isoformat(),
            "method": "tools/build-changelog.py 读 git 历史生成，一条对应一个真实提交",
            "note": "这是本站自己做了什么，不是官方新闻，也不含任何转载与评价。"
                    "界面只显示日期、标题与板块，不显示提交号与文件路径。",
            "count": len(entries),
            "since": a.since
        },
        "entries": entries
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print("变更日志 %d 条 → src/data/changelog.json（最早 %s，最新 %s）" % (
        len(entries), entries[-1]["date"] if entries else "—", entries[0]["date"] if entries else "—"))


if __name__ == "__main__":
    main()
