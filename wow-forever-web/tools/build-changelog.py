#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 git 历史生成 docs/CHANGELOG-DEV.md —— 面向维护者的开发日志（不进网页）。

为什么要单独一份：网页上那条「本站更新」是写给玩家看的（src/data/releases.json，人工随改动一起写，
一条对应一个真实提交）。提交标题里全是脚本名、文件名和 fix/feat 这类话，不能原样进页面，
所以 git 自动生成的这份只给维护者看，放在 docs/ 里，构建卡口也不检查它。

要改网页上的更新说明，改 src/data/releases.json；这份文件不用管。

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
OUT = os.path.join(ROOT, "docs", "CHANGELOG-DEV.md")

# 路径前缀 → 界面显示的板块名（顺序即优先级，命中第一个就用）
SCOPE = [
    ("src/data/talents", "天赋数据"), ("src/data/talent-text", "天赋文本"),
    ("src/data/world.json", "世界数据"), ("src/data/professions.json", "专业数据"),
    ("src/data/dungeons.json", "副本数据"), ("src/data/races.json", "种族数据"),
    ("src/data/glossary.json", "术语词条"), ("src/data/abilities.json", "技能四态"),
    ("src/data/changes.json", "改动清单"), ("src/data/timeline.json", "上线时间表"),
    ("src/data/releases.json", "本站更新"), ("src/data/scale.json", "规模快照"),
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
    (r"professions\.json", "专业数据"), (r"icons?\.json", "图标映射"),
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
        entries.append({"date": date, "hash": head[1], "raw": subject, "subject": gloss(subject),
                       "tags": tags, "files": len(paths)})
    entries = entries[:a.max]

    lines = [u"# 开发日志（自动生成，不进网页）", u"",
             u"由 `tools/build-changelog.py` 读 git 历史生成。玩家看的那份是 "
             u"`src/data/releases.json`（人工写、卡口把关），不是这份。", u"",
             u"生成时间：%s ｜ 起于 %s ｜ 共 %d 条" % (datetime.date.today().isoformat(), a.since, len(entries)),
             u"", u"| 日期 | 提交 | 标题 | 动到的板块 | 文件数 |", u"| --- | --- | --- | --- | --- |"]
    for e in entries:
        lines.append(u"| %s | `%s` | %s | %s | %d |" % (
            e["date"], e["hash"], e["raw"].replace("|", "\|"), u"、".join(e["tags"]) or u"—", e["files"]))
    io.open(OUT, "w", encoding="utf-8").write(u"\n".join(lines) + u"\n")
    print(u"开发日志 %d 条 → docs/CHANGELOG-DEV.md（最早 %s，最新 %s）" % (
        len(entries), entries[-1]["date"] if entries else u"—", entries[0]["date"] if entries else u"—"))
    print(u"提醒：网页上的「本站更新」读的是 src/data/releases.json，需要人工同步一条。")


if __name__ == "__main__":
    main()
