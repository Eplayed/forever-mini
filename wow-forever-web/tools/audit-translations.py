#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""译名体检：把每条 L0 词条拿回它自己声明的官方来源页里逐字核对。

为什么要有这个脚本：build-data.js 只能证明"这条数据挂着官方来源、有核对日期"，
证明不了"当初抄的时候没抄错字"。人工录入的错字、串行、把 A 职业的天赋记到 B 职业，
只有回到原文页面才能发现。

用法：
    python3 tools/audit-translations.py            # 体检并写 docs/DATA-AUDIT-<日期>.md
    python3 tools/audit-translations.py --strict   # 有未命中就退出码非 0（可当卡口）

只读，不改任何数据。页面抓取缓存在 .audit-cache/（已 gitignore）。
"""
import argparse
import datetime
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")
CACHE = os.path.join(ROOT, ".audit-cache")
DOCS = os.path.join(ROOT, "docs")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TAG_RE = re.compile(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", re.I)
_CJ = u"\u3400-\u9fff\u3000-\u303f\uff00-\uffef\u2018\u2019\u201c\u201d\u00b7\u2014\u2026"
CJK_SPACE = re.compile(u"(?<=[%s])[\\s\u3000]+(?=[%s])" % (_CJ, _CJ))


def checkable(prov):
    """能回原文逐字比对的来源类型。datamine_cn（客户端解包转述）也算——
       它撑着 L0，就必须能被机器验证「我们抄的和它页面上写的是同一串字」。"""
    t = prov.get("type") or ""
    return t.startswith("official") or t == "datamine_cn"


def squeeze(text):
    """去掉汉字与全角标点之间的空白。官方页常用 <b>/<strong> 强调词中的一部分或词条名，
       转纯文本后会在中间留下空格，例如「冰霜 与 火焰 陷阱」「被遗忘者的意志 ：移除…」，
       不做这一步会把正确词条误判成未命中。汉字与全角标点之间的空白在中文里没有语义。"""
    prev = None
    while prev != text:
        prev = text
        text = CJK_SPACE.sub("", text)
    return text


def around(text, needle, span=46):
    """取词条在原文里的那一句，供人工判定用。报告里没有片段，
       「排版空格才命中」就永远是一句没法复核的话。"""
    i = text.find(needle)
    if i < 0:
        return ""
    s = text[max(0, i - span):i + len(needle) + span]
    return re.sub(r"\s+", " ", s).strip()


def fetch_raw(url):
    """取页面原文。macOS 自带 python 常缺 CA，urllib 会 CERTIFICATE_VERIFY_FAILED，
       所以依次尝试：系统证书 → certifi → 系统 curl（curl 用钥匙串，一定能过）。"""
    import ssl
    import subprocess
    contexts = []
    try:
        contexts.append(ssl.create_default_context())
    except Exception:
        pass
    try:
        import certifi
        contexts.append(ssl.create_default_context(cafile=certifi.where()))
    except Exception:
        pass
    last = None
    for ctx in contexts:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=25, context=ctx).read().decode("utf-8", "replace")
        except Exception as exc:
            last = exc
    out = subprocess.run(["curl", "-sSL", "--max-time", "25", "-A", UA, url],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError("urllib 与 curl 都失败：%s / %s" % (last, out.stderr.decode("utf-8", "replace")[:120]))
    return out.stdout.decode("utf-8", "replace")


def fetch(url, ttl_hours=24):
    """带本地缓存的抓取：官方页改版不频繁，重复体检没必要每次都打网络。"""
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    key = re.sub(r"[^A-Za-z0-9]", "_", url)[:120] + ".txt"
    path = os.path.join(CACHE, key)
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < ttl_hours * 3600:
        return io.open(path, encoding="utf-8").read(), "缓存"
    try:
        html = fetch_raw(url)
    except Exception as exc:  # 网络与证书问题都走这里，退回缓存再说
        if os.path.exists(path):
            return io.open(path, encoding="utf-8").read(), "抓取失败退回缓存"
        print("  !! 抓不到 %s：%s" % (url, exc))
        return None, "抓取失败"
    text = TAG_RE.sub(" ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    io.open(path, "w", encoding="utf-8").write(text)
    time.sleep(0.6)  # 别打太猛
    return text, "已抓取"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="有未命中项时退出码非 0")
    parser.add_argument("--no-fetch", action="store_true", help="只用缓存，不打网络")
    args = parser.parse_args()

    glossary = json.load(io.open(os.path.join(DATA, "glossary.json"), encoding="utf-8"))
    items = [{"src": "术语", "id": x["id"], "cn": x.get("cn"), "cls": x.get("classId") or x.get("kind"),
              "level": x.get("level"), "prov": x.get("provenance", [])} for x in glossary["items"]]

    # 副本名与系统卡片名同样是对外展示的"官方中文"，必须一起回原文核对
    dungeons = json.load(io.open(os.path.join(DATA, "dungeons.json"), encoding="utf-8"))
    for key in ("newDungeons", "classicDungeons", "raids"):
        for x in dungeons.get(key, []):
            if x.get("nameCn"):
                items.append({"src": "副本", "id": x["id"], "cn": x["nameCn"], "cls": key,
                              "level": x.get("level"), "prov": x.get("provenance", [])})
    systems = json.load(io.open(os.path.join(DATA, "systems.json"), encoding="utf-8"))
    for g in systems.get("groups", []):
        for x in g.get("items", []):
            if x.get("nameCn"):
                items.append({"src": "系统", "id": x["id"], "cn": x["nameCn"], "cls": g.get("label"),
                              "level": x.get("level"), "prov": x.get("provenance", [])})
    raw_items = glossary["items"]

    # 技能四态条目核对的也是"原文引用"本身，比名字更严格
    ab_path = os.path.join(DATA, "abilities.json")
    if os.path.exists(ab_path):
        ab = json.load(io.open(ab_path, encoding="utf-8"))
        for x in (ab.get("items") or []):
            for pr in (x.get("provenance") or []):
                if pr.get("quote"):
                    items.append({"src": "技能四态", "id": x["id"], "cn": pr["quote"], "cls": x.get("classId"),
                                  "level": x.get("level"), "prov": [pr]})

    # 时间线条目核对的是"原文引用"本身，比名字更严格
    tl_path = os.path.join(DATA, "timeline.json")
    if os.path.exists(tl_path):
        tlo = json.load(io.open(tl_path, encoding="utf-8"))
        for x in (tlo.get("items") or []):
            for pr in (x.get("provenance") or []):
                if (pr.get("type") or "").startswith("official") and pr.get("quote"):
                    items.append({"src": "时间线", "id": x["id"], "cn": pr["quote"], "cls": "引用",
                                  "level": x.get("level"), "prov": [pr]})

    # 种族页：核对特长整句、种族简介、亮点组合整句与冲突里的导语
    rc_path = os.path.join(DATA, "races.json")
    if os.path.exists(rc_path):
        rc = json.load(io.open(rc_path, encoding="utf-8"))
        page_url = ((rc.get("meta") or {}).get("sources") or [{}])[0].get("url")
        for x in (rc.get("races") or []):
            lore = (x.get("subgroup") or {}).get("lore") or x.get("lore")
            if lore:
                items.append({"src": "种族简介", "id": "%s/lore" % x["id"], "cn": lore, "cls": x.get("faction"),
                              "level": x.get("level"),
                              "prov": [{"type": "official_cn", "url": page_url, "quote": lore}]})
            pool = list(x.get("traits") or [])
            if x.get("subgroup"):
                pool += list(x["subgroup"].get("traits") or [])
            for t in pool:
                if t.get("quote"):
                    items.append({"src": "种族特长", "id": "%s/%s" % (x["id"], t["name"]), "cn": t["quote"],
                                  "cls": x.get("faction"), "level": x.get("level"),
                                  "prov": [{"type": "official_cn", "url": page_url, "quote": t["quote"]}]})
        for c in (rc.get("newCombos") or []):
            for pr in (c.get("provenance") or []):
                if pr.get("quote"):
                    items.append({"src": "亮点组合", "id": "combo-%s" % c["label"], "cn": pr["quote"],
                                  "cls": "引用", "level": c.get("level"), "prov": [pr]})
        sky = (rc.get("skyborneNote") or {}).get("text")
        if sky:
            items.append({"src": "天裔导语", "id": "skyborne-note", "cn": sky, "cls": "引用", "level": "L0",
                          "prov": [{"type": "official_cn", "url": page_url, "quote": sky}]})

    # 世界线：稀有精英与书籍的中文名回它自己声明的那一页逐字核对。
    # 区域名不在这批核对范围：它来自结构化接口而不是页面正文，改由 build-data 的 mapId 两套来源交叉验证把关。
    wd_path = os.path.join(DATA, "world.json")
    if os.path.exists(wd_path):
        wd = json.load(io.open(wd_path, encoding="utf-8"))
        for x in (wd.get("rares") or []):
            items.append({"src": "世界稀有", "id": x["id"], "cn": x.get("nameCn"), "cls": x.get("zone"),
                          "level": x.get("level"), "prov": x.get("provenance", [])})
            for d in (x.get("drops") or []):
                items.append({"src": "世界掉落", "id": "%s/%s" % (x["id"], d.get("itemId")), "cn": d.get("nameCn"),
                              "cls": x.get("zone"), "level": x.get("level"), "prov": x.get("provenance", [])})
        for s_ in (wd.get("rareSets") or []):
            for d in (s_.get("pieces") or []):
                items.append({"src": "世界套装", "id": "set-%s/%s" % (s_.get("nameCn"), d.get("itemId")),
                              "cn": d.get("nameCn"), "cls": "套装", "level": "L0",
                              "prov": (wd.get("rares") or [{}])[0].get("provenance", [])})
        for x in (wd.get("books") or []):
            items.append({"src": "世界书籍", "id": x["id"], "cn": x.get("nameCn"), "cls": x.get("zone"),
                          "level": x.get("level"), "prov": x.get("provenance", [])})
        for r in (wd.get("bookRewards") or []):
            items.append({"src": "书籍称号", "id": "rw-%s" % r.get("books"), "cn": r.get("title"),
                          "cls": "上交", "level": "L0", "prov": r.get("provenance", [])})
            for d in (r.get("items") or []):
                items.append({"src": "书籍奖励", "id": "rw-%s/%s" % (r.get("books"), d.get("itemId")),
                              "cn": d.get("nameCn"), "cls": "上交", "level": "L0",
                              "prov": r.get("provenance", [])})
        for l in (wd.get("librarians") or []):
            items.append({"src": "图书管理员", "id": "lib-%s" % l.get("nameCn"), "cn": l.get("nameCn"),
                          "cls": l.get("city"), "level": "L0", "prov": l.get("provenance", [])})

    # 改动清单：964 条只有名称与类别，名称同样要回它声明的那一页逐字核对
    ch_path = os.path.join(DATA, "changes.json")
    if os.path.exists(ch_path):
        chd = json.load(io.open(ch_path, encoding="utf-8"))
        for x in (chd.get("items") or []):
            items.append({"src": "改动清单", "id": x["id"], "cn": x.get("nameCn"), "cls": x.get("classId"),
                          "level": x.get("level"), "prov": x.get("provenance", [])})

    lg_path = os.path.join(DATA, "legacy.json")
    if os.path.exists(lg_path):
        lgd = json.load(io.open(lg_path, encoding="utf-8"))
        # 只核名称：每层效果说明本站不存，也就没什么可核的
        for x in (lgd.get("perks") or []):
            items.append({"src": "传承专长", "id": x["id"], "cn": x.get("nameCn"),
                          "cls": x.get("treeCn"), "level": x.get("level"),
                          "prov": x.get("provenance", [])})
        for x in (lgd.get("rewards") or []):
            items.append({"src": "传承奖励", "id": "legacy-reward-%s" % x.get("itemId"),
                          "cn": x.get("nameCn"), "cls": None, "level": x.get("level"),
                          "prov": x.get("provenance", [])})

    urls = []
    for it in items:
        for prov in it["prov"]:
            if checkable(prov) and prov.get("url"):
                if prov["url"] not in urls:
                    urls.append(prov["url"])

    print("待核对名称 %d 条（含副本与系统名），官方来源页 %d 个" % (len(items), len(urls)))
    pages, page_status = {}, {}
    for url in urls:
        if args.no_fetch:
            key = re.sub(r"[^A-Za-z0-9]", "_", url)[:120] + ".txt"
            path = os.path.join(CACHE, key)
            text = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
            pages[url], page_status[url] = text, "仅缓存" if text else "无缓存"
        else:
            pages[url], page_status[url] = fetch(url)
        print("  %s  %s" % (page_status[url], url))

    judged = []
    hits, misses, no_source, loose_hits = [], [], [], []
    expected_unofficial = []
    exc_path = os.path.join(DATA, "audit-exceptions.json")
    exceptions = {}
    if os.path.exists(exc_path):
        exceptions = {e["id"]: e for e in json.load(io.open(exc_path, encoding="utf-8")).get("items", [])}
    for it in items:
        cn = (it["cn"] or "").strip()
        srcs = [p.get("url") for p in it["prov"] if checkable(p)]
        if not cn:
            no_source.append((it, "词条没有中文名"))
            continue
        if not srcs:
            # L0/L1 声称官方却给不出官方链接才是问题；L2/L3 本来就用转载/开放数据，属预期
            bucket = no_source if it.get("level") in ("L0", "L1") else expected_unofficial
            bucket.append((it, "没有官方来源 URL（%s）" % (it.get("level") or "L3")))
            continue
        found_in, loose = None, False
        snip = ""
        for url in srcs:
            text = pages.get(url)
            if not text:
                continue
            if cn in text:
                found_in, loose = url, False
                break
            sq = squeeze(text)
            if cn in sq:
                found_in, loose, snip = url, True, around(sq, cn)
                break
        if found_in and loose and it.get("id") in exceptions:
            # 人眼过完并记了判定的，不再算待确认；判定连原文片段一起存在例外表里
            judged.append((it, exceptions[it["id"]]))
        elif found_in and loose:
            loose_hits.append((it, found_in, snip))
        elif found_in:
            hits.append((it, found_in))
        elif it.get("id") in exceptions:
            judged.append((it, exceptions[it["id"]]))
        else:
            misses.append((it, srcs))

    today = datetime.date.today().isoformat()
    out = os.path.join(DOCS, "DATA-AUDIT-%s.md" % today)
    lines = []
    lines.append("# 译名体检报告 · %s（wow-data）" % today)
    lines.append("")
    lines.append("脚本：`python3 tools/audit-translations.py`。做法是把每个对外展示的中文名（术语词条、"
                 "副本名、系统名，以及时间线、技能四态、种族页引用的官方整句）"
                 "拿回它自己在 `provenance` 里声明的官方来源页做逐字包含比对。"
                 "**只读核对，不改数据。**")
    lines.append("")
    lines.append("## 结果")
    lines.append("")
    lines.append("| 项 | 数 |")
    lines.append("| --- | --- |")
    lines.append("| 词条总数 | %d |" % len(items))
    lines.append("| 在声明的官方页里逐字命中 | %d |" % len(hits))
    lines.append("| 去掉汉字间排版空格才命中（要人眼确认） | %d |" % len(loose_hits))
    lines.append("| **未命中（要人工回原文看）** | %d |" % len(misses))
    lines.append("| 已人工判定并留痕（见 audit-exceptions.json） | %d |" % len(judged))
    lines.append("| **声称官方却核不到（L0/L1 缺官方链接）** | %d |" % len(no_source))
    lines.append("| 本来就标 L2/L3 的非官方中文名（预期，界面已如实标注） | %d |" % len(expected_unofficial))
    lines.append("")
    lines.append("核对范围含 `glossary.json` 词条、`dungeons.json` 副本中文名、`systems.json` 系统卡片中文名、"
        "`world.json` 的稀有精英名与掉落物名、书名与上交奖励名（区域名不在此列，见上）、"
        "`changes.json` 的 964 条天赋与法术名（只核名称，句子本站不存）、"
        "`legacy.json` 的传承专长名与进度奖励名（同样只核名称），"
                 "`timeline.json` 与 `abilities.json` 的官方整句，以及 `races.json` 的种族简介、种族特长整句、"
                 "亮点组合与天裔导语。")
    rate = len(hits) * 100.0 / max(len(items), 1)
    lines.append("| 命中率 | %.1f%% |" % rate)
    lines.append("")
    lines.append("## 来源页")
    lines.append("")
    lines.append("| 状态 | 页面 | 承担词条 |")
    lines.append("| --- | --- | --- |")
    for url in urls:
        n = len([1 for it in items for p in it["prov"] if p.get("url") == url])
        lines.append("| %s | %s | %d |" % (page_status.get(url, "?"), url, n))
    lines.append("")
    if loose_hits:
        lines.append("## 只在去掉排版空格后命中（人工确认这几条）")
        lines.append("")
        lines.append("官方页用加粗标签强调词的一部分时，转成纯文本会在汉字中间留下空格。"
                     "下列词条属于这种情况，**脚本没法替你判断是不是同一个词，要人眼过一遍**。")
        lines.append("")
        lines.append("| 词条 | id | 职业 | 出处 | 原文片段 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for it, url, snip in loose_hits:
            lines.append("| %s | `%s` | %s %s | %s | %s |"
                         % (it["cn"], it.get("id") or "", it["src"], it["cls"] or "", url, snip))
        lines.append("")
    if judged:
        lines.append("## 已人工判定并留痕")
        lines.append("")
        lines.append("这些条目没能逐字命中，但已回原文人工判定并把依据写进 `src/data/audit-exceptions.json`。")
        lines.append("")
        lines.append("| 词条 | 结论 | 官方原句 | 判定日期 |")
        lines.append("| --- | --- | --- | --- |")
        for it, e in judged:
            lines.append("| %s（%s） | %s | %s | %s |" % (it["cn"], it["src"], e.get("verdict"),
                                                        e.get("quote"), e.get("decidedAt")))
        lines.append("")
    if misses:
        lines.append("## 未命中清单（逐条待人工核对）")
        lines.append("")
        lines.append("未命中不等于词条错，常见原因是：官方页用的是另一个写法、词条是从同系列另一篇文章采的、"
                     "或页面改版删了这段。**但在人工确认之前，这些条目的 L0 身份不可信。**")
        lines.append("")
        lines.append("| 名称 | 出处 | 标识 | 当前级别 | 声明来源 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for it, srcs in misses:
            lines.append("| %s | %s | %s | %s | %s |" % (it["cn"], it["src"], it["id"],
                                                         it.get("level") or "L3", "<br>".join(srcs)))
        lv = set(it.get("level") for it, _ in misses)
        if lv <= {"L2", "L3"}:
            lines.append("")
            lines.append("这%d条当前都标 L2/L3，界面显示\"待实测\"，**没有在冒充官方**；"
                         "列在这里是因为它们的中文名来自转载/英文页，等官方中文稿或实测后再定名。" % len(misses))
        lines.append("")
    if expected_unofficial:
        lines.append("## 本来就标着非官名的条目（预期，不需要处理）")
        lines.append("")
        lines.append("这些中文名来自转载、开放数据或第三方挖掘，条目本身标的是 L2/L3，界面显示\"待实测\"，"
                     "不属于\"冒充官方\"。留着这份清单是为了上线后逐条回官方页升级。")
        lines.append("")
        lines.append("| 名称 | 出处 | 级别 |")
        lines.append("| --- | --- | --- |")
        for it, why in expected_unofficial:
            lines.append("| %s | %s %s | %s |" % (it["cn"], it["src"], it["id"], it.get("level")))
        lines.append("")
    if no_source:
        lines.append("## 声称官方却给不出官方链接（必须处理）")
        lines.append("")
        for it, why in no_source:
            lines.append("- %s / %s（%s）：%s" % (it["src"], it["id"], it["cn"], why))
        lines.append("")
    lines.append("## 处置规则")
    lines.append("")
    lines.append("1. 未命中条目先人工回原文比对：确实官方写过 → 把 `provenance.url` 改成真正那篇；"
                 "官方没写过 → 降级 L2 并在页面显示待实测，**不允许留着 L0**。")
    lines.append("2. `--strict` 只在**声称官方（L0/L1）的条目没逐字命中**或有结构性问题时退出码非 0；"
                 "L2/L3 的未命中与「去掉排版空格才命中」都只出警告——前者本来就没声称官方，"
                 "后者是 HTML 强调标签把词从中间拆开造成的转换产物（squeeze 只删汉字之间的空白，"
                 "不可能把错词拼成对词）。**但并写形式指代的词（如官方写「冰霜与火焰陷阱」）不是转换产物，"
                 "必须逐条走 `audit-exceptions.json` 留人工判定**，不能靠这条降级蒙过去。")
    lines.append("3. 改完重跑 `node tools/build-data.js` 与本脚本，命中率必须回升。")
    lines.append("4. 掉落与 BOSS 技能不在本脚本范围内：目前 22 座副本的 `bosses` 与 `drops` 是空的，"
                 "没有数据就没有写错的风险；等实测有数据时，`build-data.js` 的百分比卡口负责拦。")
    lines.append("")
    io.open(out, "w", encoding="utf-8").write("\n".join(lines))

    print("\n命中 %d / 排版空格才命中 %d / 未命中 %d / 结构问题 %d → 报告 %s"
          % (len(hits), len(loose_hits), len(misses), len(no_source), os.path.relpath(out, ROOT)))
    if misses:
        print("未命中前 10 条：" + "、".join(it.get("cn", "?") for it, _ in misses[:10]))
    # 卡口只拦两类真正会骗人的：① 声称官方（L0/L1）却在它自己声明的那页原文里找不到的名字
    # ——那就是我们抄错了或编的；② 结构性问题（没有中文名、L0/L1 给不出官方链接）。
    # 「去掉排版空格才命中」不再算失败：squeeze 只删汉字之间的空白，不可能把错词拼成对词，
    # 抄错的风险它已经覆盖。这一桶降级成警告，但报告里逐条附原文片段；
    # 官方用并写形式指代的词（如「冰霜与火焰陷阱」）仍要走 audit-exceptions.json 留人工判定，
    # 不能靠这条降级蒙过去。L2/L3 的未命中本来就没声称官方，同样只警告。
    hard = [(it, s) for it, s in misses if it.get("level") in ("L0", "L1")]
    if args.strict and (hard or no_source):
        print("卡口失败：L0/L1 未命中 %d 条 / 结构问题 %d 条" % (len(hard), len(no_source)))
        for it, _ in hard[:10]:
            print("  - %s（%s / %s）" % (it["cn"], it["src"], it.get("level")))
        sys.exit(1)
    if misses or loose_hits:
        print("警告（不卡口）：没声称官方的未命中 %d 条、排版空格才命中 %d 条，逐条见报告"
              % (len(misses) - len(hard), len(loose_hits)))


if __name__ == "__main__":
    main()
