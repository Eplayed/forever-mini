#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从国服官方「无限」职业深度解析稿抽取技能与天赋的四态线索（新增 / 改动 / 移除 / 改名）。

为什么要有这个脚本：官方稿把每条改动写成"某技能：（新增天赋。）说明…"这种带标记的句子，
手抄容易串行、漏字，或把猎人的条目记到德鲁伊头上。脚本按官方页的小标题分段
（职业解析 → 基础技能/宠物/天赋 → 具体专精），只在段落内抓标记，
并要求"名称原样出现在整句引用里"，不满足就丢弃。

用法：
    python3 tools/extract-abilities.py            # 只打印，不写盘
    python3 tools/extract-abilities.py --write    # 生成 src/data/abilities.json

"未变"这一态官方不会写，脚本一律留空；页面显示"未统计"，不许把"没提到"当成"没变"。
"""
import argparse
import datetime
import importlib.util
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")

_spec = importlib.util.spec_from_file_location("at", os.path.join(ROOT, "tools", "audit-translations.py"))
at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(at)

PAGES = [
    {"url": "https://wow.blizzard.cn/news/24301515/index.html", "label": "猎人与德鲁伊职业深度解析"},
    {"url": "https://wow.blizzard.cn/news/24301514/index.html", "label": "牧师与战士职业深度解析"},
]

CLASS_HEAD = [(u"猎人", "hunter"), (u"德鲁伊", "druid"), (u"牧师", "priest"), (u"战士", "warrior")]
SPEC_HEAD = [(u"野兽控制", "beast-mastery"), (u"射击", "marksmanship"), (u"生存", "survival"),
             (u"野性战斗", "feral"), (u"恢复", "restoration"), (u"平衡", "balance"),
             (u"戒律", "discipline"), (u"神圣", "holy"), (u"暗影", "shadow"),
             (u"武器", "arms"), (u"狂怒", "fury"), (u"防护", "protection")]
KIND_HEAD = [(u"基础技能", "skill"), (u"职业基础技能", "skill"), (u"宠物", "pet"), (u"天赋", "talent")]

HEAD_RE = re.compile(r"<h([2-4])[^>]*>([\s\S]*?)</h\1>", re.I)
TAG_RE = re.compile(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", re.I)
MARK_RE = re.compile(u"([\\u4e00-\\u9fffA-Za-z0-9·—’'\\- ]{2,18})\\s*[：:]\\s*（([^）]{2,28}?)）")
STATE_WORDS = [(u"移除", "removed"), (u"新增", "new"), (u"重做", "changed"), (u"改为", "changed"),
               (u"调整", "changed"), (u"削弱", "changed"), (u"加强", "changed"), (u"原", "renamed")]
TIER_RE = re.compile(u"第(\\d+)层")
MOVE_RE = re.compile(u"从第(\\d+)层[上下]移至第(\\d+)层")
MILE_RE = re.compile(u"第(\\d+)点关键天赋")


ENTITIES = [(u"&nbsp;", u" "), (u"&amp;", u"&"), (u"&lt;", u"<"), (u"&gt;", u">"),
            (u"&quot;", u'"'), (u"&#39;", u"'"), (u"&ldquo;", u"“"), (u"&rdquo;", u"”")]


def strip_tags(html):
    for a, b in ENTITIES:
        html = html.replace(a, b)
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html).replace(u"\u3000", " "))


def state_of(tag):
    for kw, st in STATE_WORDS:
        if kw in tag:
            return st
    return None


def head_class(title):
    if u"职业解析" not in title:
        return None
    for cn, en in CLASS_HEAD:
        if cn in title:
            return en
    return None


def head_spec(title):
    t = title.strip()
    for cn, en in SPEC_HEAD:
        if t == cn or t.startswith(cn):
            return en
    return None


def head_kind(title):
    t = title.strip()
    for cn, en in KIND_HEAD:
        if t == cn:
            return en
    return None


def sentence_end(txt, pos):
    ends = [i + 1 for i in (txt.find(u"。", pos), txt.find(u"；", pos)) if i >= 0]
    return min(ends) if ends else len(txt)


def parse_page(page):
    html = at.fetch_raw(page["url"])
    heads = [(m.start(), re.sub(r"<[^>]+>", "", m.group(2)).strip()) for m in HEAD_RE.finditer(html)]
    blocks = []
    cls = spec = kind = None
    for i, (pos, title) in enumerate(heads):
        c = head_class(title)
        if c:
            cls, spec, kind = c, None, None
        s = head_spec(title)
        if s:
            spec = s
        k = head_kind(title)
        if k:
            kind = k
        end = heads[i + 1][0] if i + 1 < len(heads) else len(html)
        if cls and end > pos:
            blocks.append((cls, spec, kind, strip_tags(html[pos:end])))
    return blocks


def clean_name(raw):
    name = re.sub(u"^天赋\\s*", u"", raw.strip())
    for cn, _en in CLASS_HEAD:
        name = re.sub(u"^%s\\s+" % cn, u"", name)
    for cn, _en in SPEC_HEAD:
        name = re.sub(u"^%s\\s+" % cn, u"", name)
    return name.strip(u" ：，。")


def extract():
    today = datetime.date.today().isoformat()
    rows, skipped = [], 0
    for page in PAGES:
        for cls, spec, kind, text in parse_page(page):
            for m in MARK_RE.finditer(text):
                raw_name, tag = m.group(1).strip(), m.group(2).strip()
                st = state_of(tag)
                if not st:
                    continue
                name = clean_name(raw_name)
                if len(name) < 2:
                    skipped += 1
                    continue
                quote = text[m.start():sentence_end(text, m.end())].strip()
                if name not in quote:
                    skipped += 1
                    continue
                tier = TIER_RE.search(tag)
                move = MOVE_RE.search(quote)
                mile = MILE_RE.search(tag) or MILE_RE.search(quote)
                rows.append({
                    "id": "%s-%s-%d" % (cls, name, len(rows)),
                    "classId": cls,
                    "spec": spec,
                    "kind": kind or "talent",
                    "name": name,
                    "state": st,
                    "officialTag": tag,
                    "tierHint": int(tier.group(1)) if tier else (int(move.group(2)) if move else None),
                    "tierFrom": int(move.group(1)) if move else None,
                    "milestone": int(mile.group(1)) if mile else None,
                    "quote": quote,
                    "level": "L0",
                    "provenance": [{
                        "type": "official_cn",
                        "url": page["url"],
                        "quote": quote,
                        "note": page["label"] + u"原文整句",
                        "checkedAt": today
                    }]
                })
    return rows, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rows, skipped = extract()
    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    print(u"抓到 %d 条带官方状态标记的条目（丢弃 %d 条不合格），分布：%s" % (len(rows), skipped, counts))
    for r in rows[:8]:
        print(u"   %-8s %-12s %-10s %-8s %s ← %s" % (r["classId"], r["spec"] or "-", r["name"], r["state"],
                                                r["kind"], r["officialTag"]))
    if not args.write:
        print(u"（未写盘，加 --write 生成 src/data/abilities.json）")
        return

    payload = {
        "meta": {
            "generatedAt": datetime.date.today().isoformat(),
            "kind": "official-cn-extract",
            "method": u"tools/extract-abilities.py 按官方页小标题分段（职业解析 → 基础技能/宠物/天赋 → 专精），"
                      u"只收「名称：（状态标记。）…」这种整句，名称必须原样出现在句里，否则丢弃。",
            "states": {"new": u"新增", "changed": u"改动", "renamed": u"改名（原X）", "removed": u"移除"},
            "notCollected": [u"未变：官方不会列出没改的东西，缺就是缺，不拿沉默当证据",
                             u"圣骑士/萨满祭司/法师/术士/潜行者：官方中文深度解析稿尚未发布",
                             u"数值细节：除原文写出的那句之外，不做推算"],
            "sources": [{"url": p["url"], "label": p["label"]} for p in PAGES]
        },
        "items": rows
    }
    out = os.path.join(DATA, "abilities.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print(u"已写入 %s（%d 条）" % (os.path.relpath(out, ROOT), len(rows)))


if __name__ == "__main__":
    main()
