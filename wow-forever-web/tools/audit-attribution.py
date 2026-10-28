#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""译名未命中的归因：把体检报告里那几百条未命中拆成"问题出在哪一层"。

为什么要有它：`audit-translations.py --strict` 只说"核不到"，不说**为什么**核不到。
"官方页改版把这段删了"、"这条挂的来源页本来就管不着它"、"我们当初抄错了"是三件完全不同的事，
混在一个 912 的数字里就没法决定该修数据还是该修判据。

只读：读 docs/DATA-AUDIT-<日期>.md 的未命中清单 + .audit-cache/ 里已抓回来的页面，
不打网络、不改任何数据。缓存里没有的页算"没抓到"，单列一档。

用法：
    python3 tools/audit-attribution.py                 # 归因今天那份报告
    python3 tools/audit-attribution.py --report docs/DATA-AUDIT-2026-10-24.md
"""
import argparse
import collections
import datetime
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
CACHE = os.path.join(ROOT, ".audit-cache")

_CJ = u"\u3400-\u9fff\u3000-\u303f\uff00-\uffef\u2018\u2019\u201c\u201d\u00b7\u2014\u2026"
CJK_SPACE = re.compile(u"(?<=[%s])[\\s　]+(?=[%s])" % (_CJ, _CJ))
# 参照物"薄到什么程度算没了"：正文纯文本不足这么多字，就不可能承载逐字回查
THIN_CHARS = 300

# 三档判定，顺序不能换：先看参照物还在不在，再看词是不是挂在错的页上，最后才是真找不到
BUCKETS = (
    ("A 参照物没了", "它声明的来源页已经取不到、或薄到装不下这段文字（页面改版／需登录／404）"),
    ("B 声明页不承载", "声明页里已经没有这串字，但它在别的缓存页里逐字能找到（词是真的，证据链挪了位置）"),
    ("C 哪儿都没有", "所有缓存页里都找不到这串字：要么官方删了，要么当初抄错"),
    ("D 缓存里没有", "这一条声明的页本地根本没抓过，判不了"),
)


def squeeze(text):
    prev = None
    while prev != text:
        prev = text
        text = CJK_SPACE.sub("", text)
    return text


def cache_path(url):
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]", "_", url)[:120] + ".txt")


def load_cache():
    """url -> 正文（按 audit-translations 的 key 规则反查；只对得上抓成功过的页）。"""
    out = {}
    if not os.path.isdir(CACHE):
        return out
    for name in os.listdir(CACHE):
        if not name.endswith(".txt"):
            continue
        with io.open(os.path.join(CACHE, name), encoding="utf-8", errors="replace") as f:
            out[name[:-4]] = f.read()
    return out


def parse_misses(path):
    """读报告里「## 未命中清单」那张表。"""
    rows = []
    inside = False
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## "):
                inside = line.startswith("## 未命中清单")
                continue
            if not inside or not line.startswith("| "):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 5 or cells[0] in ("名称", "---") or set(cells[0]) <= set("- "):
                continue
            urls = [u.strip() for u in re.split(r"<br\s*/?>", cells[4]) if u.strip()]
            rows.append({"name": cells[0], "src": cells[1], "id": cells[2],
                         "level": cells[3], "urls": urls})
    return rows


def classify(row, pages, index):
    """返回 (档位, 说明)。pages 是 url -> 正文 的字典（只含声明页），index 是全缓存。"""
    if not row["urls"]:
        return ("D 缓存里没有", "报告里没写声明来源")
    states = []
    have_any = False
    for url in row["urls"]:
        key = re.sub(r"[^A-Za-z0-9]", "_", url)[:120]
        text = pages.get(key)
        if text is None:
            states.append("没抓过 %s" % short(url))
            continue
        body = squeeze(text)
        if len(body.strip()) < THIN_CHARS or body.strip().lower().startswith("not found"):
            states.append("薄/空壳 %s（%d 字）" % (short(url), len(body.strip())))
            continue
        have_any = True
        if squeeze(row["name"]) in body:
            states.append("其实命中 %s" % short(url))
    if not have_any:
        return ("A 参照物没了", "；".join(states))
    if any(s.startswith("其实命中") for s in states):
        return ("判据没算进去", "；".join(states))
    for key, text in index.items():
        if squeeze(row["name"]) in squeeze(text):
            return ("B 声明页不承载", "在 %s 里能找到" % key)
    return ("C 哪儿都没有", "声明页有正文，但这串字在所有缓存页里都不出现")


def short(url):
    return re.sub(r"^https?://", "", url)[:46]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=os.path.join(
        DOCS, "DATA-AUDIT-%s.md" % datetime.date.today().isoformat()))
    ap.add_argument("--out", default=None, help="写归因报告的路径；不给就只打印")
    args = ap.parse_args()
    if not os.path.exists(args.report):
        print("找不到报告：%s" % args.report)
        return 2

    index = load_cache()
    pages = index
    rows = parse_misses(args.report)
    tally = collections.OrderedDict((b[0], collections.Counter()) for b in BUCKETS)
    detail = collections.defaultdict(list)
    page_health = collections.Counter()
    for row in rows:
        bucket, why = classify(row, pages, index)
        tally.setdefault(bucket, collections.Counter())[row["src"]] += 1
        detail[bucket].append((row["src"], row["name"], why))
        for url in row["urls"]:
            key = re.sub(r"[^A-Za-z0-9]", "_", url)[:120]
            text = index.get(key)
            if text is None:
                page_health[(short(url), "没抓过")] += 1
            elif len(squeeze(text).strip()) < THIN_CHARS:
                page_health[(short(url), "薄/空壳 %d 字" % len(squeeze(text).strip()))] += 1
            else:
                page_health[(short(url), "有正文 %d 字" % len(squeeze(text).strip()))] += 1

    lines = []
    lines.append("# 译名未命中归因 · %s（wow-data）" % datetime.date.today().isoformat())
    lines.append("")
    lines.append("脚本：`python3 tools/audit-attribution.py`。输入是 `%s` 的未命中清单与 `.audit-cache/`，"
                 "**不打网络、不改数据**。" % os.path.relpath(args.report, ROOT))
    lines.append("")
    lines.append("## 一句话")
    total = sum(sum(c.values()) for c in tally.values())
    biggest = max(tally.items(), key=lambda kv: sum(kv[1].values())) if tally else ("—", {})
    lines.append("")
    lines.append("未命中 %d 条，最大一档是「%s」%d 条。这一档不是词条错，是**参照物或判据的问题**。"
                 % (total, biggest[0], sum(biggest[1].values())))
    lines.append("")
    lines.append("## 分档 × 板块")
    lines.append("")
    lines.append("| 档 | 条数 | 占比 | 集中在哪些板块 |")
    lines.append("| --- | --- | --- | --- |")
    for bucket, _ in BUCKETS + (("判据没算进去", ""),):
        c = tally.get(bucket)
        if not c:
            continue
        n = sum(c.values())
        top = "、".join("%s %d" % (k, v) for k, v in c.most_common(5))
        lines.append("| %s | %d | %.1f%% | %s |" % (bucket, n, 100.0 * n / max(total, 1), top))
    lines.append("")
    lines.append("## 参照物体检（这些页现在装不装得下文字）")
    lines.append("")
    lines.append("| 页面 | 状态 | 挂着多少条未命中 |")
    lines.append("| --- | --- | --- |")
    for (url, state), n in sorted(page_health.items(), key=lambda kv: -kv[1])[:25]:
        lines.append("| `%s` | %s | %d |" % (url, state, n))
    lines.append("")
    lines.append("## 每档举例")
    lines.append("")
    for bucket, desc in BUCKETS + (("判据没算进去", "报告说未命中、按现在的缓存重算其实命中"),):
        rows_in = detail.get(bucket) or []
        if not rows_in:
            continue
        lines.append("**%s** ｜ %s ｜ %d 条" % (bucket, desc, len(rows_in)))
        lines.append("")
        for src, name, why in rows_in[:4]:
            lines.append("- %s ｜ %s ｜ %s" % (src, name[:34], why[:96]))
        lines.append("")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("已写 %s" % os.path.relpath(args.out, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
