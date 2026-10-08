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
CJK_SPACE = re.compile(u"(?<=[\u3400-\u9fff])[\s\u3000]+(?=[\u3400-\u9fff])")


def squeeze(text):
    """去掉汉字之间的空白。官方页常用 <b> 强调词中的一部分，转纯文本后会在汉字中间留下空格，
       例如「冰霜 与 火焰 陷阱」，不做这一步会把正确词条误判成未命中。"""
    prev = None
    while prev != text:
        prev = text
        text = CJK_SPACE.sub("", text)
    return text


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

    urls = []
    for it in items:
        for prov in it["prov"]:
            if (prov.get("type") or "").startswith("official") and prov.get("url"):
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
        srcs = [p.get("url") for p in it["prov"] if (p.get("type") or "").startswith("official")]
        if not cn:
            no_source.append((it, "词条没有中文名"))
            continue
        if not srcs:
            # L0/L1 声称官方却给不出官方链接才是问题；L2/L3 本来就用转载/开放数据，属预期
            bucket = no_source if it.get("level") in ("L0", "L1") else expected_unofficial
            bucket.append((it, "没有官方来源 URL（%s）" % (it.get("level") or "L3")))
            continue
        found_in, loose = None, False
        for url in srcs:
            text = pages.get(url)
            if not text:
                continue
            if cn in text:
                found_in, loose = url, False
                break
            if cn in squeeze(text):
                found_in, loose = url, True
                break
        if found_in and loose:
            loose_hits.append((it, found_in))
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
                 "副本名、系统名）拿回它自己在 `provenance` 里声明的官方来源页做逐字包含比对。"
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
    lines.append("核对范围含 `glossary.json` 词条、`dungeons.json` 副本中文名、`systems.json` 系统卡片中文名。")
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
        lines.append("| 词条 | 职业 | 出处 |")
        lines.append("| --- | --- | --- |")
        for it, url in loose_hits:
            lines.append("| %s | %s %s | %s |" % (it["cn"], it["src"], it["cls"] or "", url))
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
            lines.append("这四条当前都标 L2/L3，界面显示\"待实测\"，**没有在冒充官方**；"
                         "列在这里是因为它们的中文名来自转载/英文页，等官方中文稿或实测后再定名。")
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
    lines.append("2. 改完重跑 `node tools/build-data.js` 与本脚本，命中率必须回升。")
    lines.append("3. 掉落与 BOSS 技能不在本脚本范围内：目前 22 座副本的 `bosses` 与 `drops` 是空的，"
                 "没有数据就没有写错的风险；等实测有数据时，`build-data.js` 的百分比卡口负责拦。")
    lines.append("")
    io.open(out, "w", encoding="utf-8").write("\n".join(lines))

    print("\n命中 %d / 排版空格才命中 %d / 未命中 %d / 结构问题 %d → 报告 %s"
          % (len(hits), len(loose_hits), len(misses), len(no_source), os.path.relpath(out, ROOT)))
    if loose_hits:
        lines.append("## 只在去掉排版空格后命中（人工确认这几条）")
        lines.append("")
        lines.append("官方页用加粗标签强调词的一部分时，转成纯文本会在汉字中间留下空格。"
                     "下列词条属于这种情况，**脚本没法替你判断是不是同一个词，要人眼过一遍**。")
        lines.append("")
        lines.append("| 词条 | 职业 | 出处 |")
        lines.append("| --- | --- | --- |")
        for it, url in loose_hits:
            lines.append("| %s | %s %s | %s |" % (it["cn"], it["src"], it["cls"] or "", url))
        lines.append("")
    if misses:
        print("未命中前 10 条：" + "、".join(it.get("cn", "?") for it, _ in misses[:10]))
    if args.strict and (misses or no_source or loose_hits):
        sys.exit(1)


if __name__ == "__main__":
    main()
