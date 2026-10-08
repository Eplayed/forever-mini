#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从国服官方中文「种族与职业组合」公告抽取种族名单、种族×职业矩阵、种族特长与亮点组合。

为什么要有这个脚本：那篇公告把 10 个种族、9 列职业、40 条种族特长写在两张表和三段列表里，
手抄最容易出的错是"某族能选哪个职业"抄串行、把部落的特长记到联盟种族头上。
脚本只按官方页自己的结构取数（h3 → 紧跟的 table、h4 → 紧跟的 em 段与 ul 列表），
并要求每条产出的名称原样出现在它自己的整句引用里，不满足就丢弃。

用法：
    python3 tools/extract-races.py            # 只打印，不写盘
    python3 tools/extract-races.py --write    # 生成 src/data/races.json
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

URL = "https://wow.blizzard.cn/news/24304075/index.html"
LABEL = u"国服官方中文·种族与职业组合公告"

# 官方表头是英文字母序，这里的中文名与 classes.json 对齐
CLASS_CN = {u"德鲁伊": "druid", u"猎人": "hunter", u"法师": "mage", u"圣骑士": "paladin",
            u"牧师": "priest", u"潜行者": "rogue", u"萨满祭司": "shaman", u"术士": "warlock",
            u"战士": "warrior"}
RACE_CN = {u"兽人": "orc", u"牛头人": "tauren", u"巨魔": "troll", u"亡灵": "undead",
           u"人类": "human", u"矮人": "dwarf", u"暗夜精灵": "night-elf", u"侏儒": "gnome",
           u"天裔": "skyborne", u"塑风者天裔": "windshaper", u"高阶会天裔": "high-order"}
FACTION_H3 = [(u"部落种族与职业组合", "horde"), (u"联盟种族与职业组合", "alliance")]

H_RE = re.compile(r"<h([2-4])[^>]*>([\s\S]*?)</h\1>", re.I)
TABLE_RE = re.compile(r"<table[\s\S]*?</table>", re.I)
ROW_RE = re.compile(r"<tr[\s\S]*?</tr>", re.I)
CELL_RE = re.compile(r"<(th|td)[^>]*>([\s\S]*?)</\1>", re.I)
UL_ITEM_RE = re.compile(r"<li[^>]*>([\s\S]*?)</li>", re.I)
EM_RE = re.compile(r"<em>([\s\S]*?)</em>", re.I)

ENTITIES = [(u"&nbsp;", u" "), (u"&amp;", u"&"), (u"&lt;", u"<"), (u"&gt;", u">"),
            (u"&quot;", u'"'), (u"&#39;", u"'"), (u"&ldquo;", u"“"), (u"&rdquo;", u"”")]


def txt(fragment):
    for a, b in ENTITIES:
        fragment = fragment.replace(a, b)
    fragment = re.sub(r"<[^>]+>", " ", fragment).replace(u"\u3000", " ")
    return re.sub(r"\s+", "", fragment)


def heads(html):
    out = []
    for m in H_RE.finditer(html):
        t = txt(m.group(2))
        if t:
            out.append((m.start(), m.end(), t))
    return out


def next_table(html, pos, limit):
    m = TABLE_RE.search(html, pos, limit)
    return m.group(0) if m else None


def parse_matrix(table, faction):
    """返回 [{raceCn, faction, classes[], headCells, marks}]。

    官方矩阵行只有 X 标记，没有可引用的整句，所以这里不造 quote：
    headCells 与 marks 保留原样，需要说明时按表头还原成职业名写进 note。
    """
    rows = []
    head_cells = None
    for rm in ROW_RE.finditer(table):
        cells = [(m.group(1), txt(m.group(2))) for m in CELL_RE.finditer(rm.group(0))]
        if not cells:
            continue
        if cells[0][1] == u"种族":
            head_cells = [c[1] for c in cells[1:]]
            continue
        name = cells[0][1]
        if name not in RACE_CN or head_cells is None:
            continue
        marks = [c[1] for c in cells[1:]]
        classes = []
        for cn, mk in zip(head_cells, marks):
            if mk.upper() == "X" and cn in CLASS_CN:
                classes.append(CLASS_CN[cn])
        rows.append({
            "raceCn": name, "faction": faction, "classes": classes,
            "headCells": head_cells, "marks": marks
        })
    return rows


def parse_traits(html, hl):
    """h4 种族小标题 → 该段内的 em 简介与 ul 特长列表。"""
    out = []
    for i, (start, end, title) in enumerate(hl):
        race_cn = title.strip()
        if race_cn not in RACE_CN:
            continue
        stop = hl[i + 1][0] if i + 1 < len(hl) else len(html)
        block = html[end:stop]
        # 官方页自己不一致：多数种族的简介包在 <em> 里，矮人那段是裸 <p>，
        # 所以取 h4 之后第一段非空文本，不依赖 <em>。
        lore = None
        for pm in re.finditer(r"<p[^>]*>([\s\S]*?)</p>", block):
            cand = txt(re.sub(r"</?em>", "", pm.group(1)))
            if len(cand) >= 12:
                lore = cand
                break
        traits = []
        for li in UL_ITEM_RE.finditer(block):
            line = txt(li.group(1))
            if not line or u"：" not in line:
                continue
            name, effect = line.split(u"：", 1)
            passive = u"（被动）" in name
            name = name.replace(u"（被动）", u"").strip()
            if len(name) < 2 or not effect.strip():
                continue
            traits.append({"name": name, "passive": passive, "effect": effect.strip(),
                           "quote": line})
        if lore or traits:
            out.append({"raceCn": race_cn, "lore": lore, "traits": traits,
                        "raw": block[:0]})
    return out


def find_sentence(html, keyword, stop_words):
    """按关键词取官方原文整句（从关键词所在段落起，到句末句号为止）。"""
    idx = html.find(keyword)
    if idx < 0:
        return None
    m = re.search(r"<p[^>]*>([\s\S]*?)</p>", html[max(0, idx - 900):idx + 900])
    if not m:
        return None
    s = txt(m.group(1))
    for sw in stop_words:
        if sw in s:
            return s
    return None


def prov(quote, note, today):
    p = {"type": "official_cn", "url": URL, "note": note, "checkedAt": today}
    # 官方矩阵行只有 X 标记，没有可引用的句子。这种条目一律不写 quote 字段，
    # 免得把"脚本还原出来的话"当成官方原文展示给读者。
    if quote:
        p["quote"] = quote
    return [p]


def norm(n):
    return n.strip().strip(u"！!。．.：: ")


def link_glossary(races):
    """把 glossary 里 kind=racial 的词条按特长名回填 raceId。

    归属依据是官方页自己的 h4 小标题（特长列在哪个种族名下），不是猜的；
    两个天裔子族同名的特长（风灵护佑、元素洞察）只回填到天裔，不指定子族。
    """
    path = os.path.join(DATA, "glossary.json")
    gl = json.loads(io.open(path, encoding="utf-8").read())
    owner = {}
    for r in races:
        for t in r.get("traits") or []:
            owner.setdefault(norm(t["name"]), set()).add(r["id"])
        sg = r.get("subgroup") or {}
        for t in sg.get("traits") or []:
            owner.setdefault(norm(t["name"]), set()).add(r["id"])
    today = datetime.date.today().isoformat()
    changed, orphans = 0, []
    for it in gl["items"]:
        if it.get("kind") != "racial":
            continue
        if not any(URL in (p.get("url") or "") for p in it.get("provenance") or []):
            continue
        owners = owner.get(norm(it["cn"]))
        if not owners:
            orphans.append(it["cn"])
            continue
        if len(owners) > 1 and all(o.startswith("skyborne") for o in owners):
            it["raceId"] = "skyborne"
        elif len(owners) > 1:
            orphans.append(it["cn"] + u"（跨阵营同名）")
            continue
        else:
            it["raceId"] = sorted(owners)[0]
        for p in it["provenance"]:
            if URL in (p.get("url") or ""):
                p["note"] = u"官方种族公告原文；种族归属由 tools/extract-races.py 按该页 h4 小标题回填"
                p["checkedAt"] = today
        changed += 1
    io.open(path, "w", encoding="utf-8").write(json.dumps(gl, ensure_ascii=False, indent=1) + "\n")
    print(u"glossary：回填 %d 条 racial 词条的 raceId；未归属 %d 条 %s" % (
        changed, len(orphans), (u"（" + u"、".join(orphans) + u"）") if orphans else u""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--link-glossary", action="store_true",
                    help=u"把 races 里的特长归属回填到 glossary.json 的 racial 词条")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    html = at.fetch_raw(URL)
    hl = heads(html)

    # 1) 两张矩阵表
    matrix = []
    for j, (start, end, title) in enumerate(hl):
        for kw, fac in FACTION_H3:
            if title.strip() == kw:
                stop = hl[j + 1][0] if j + 1 < len(hl) else len(html)
                tb = next_table(html, end, stop)
                if not tb:
                    continue
                rows = parse_matrix(tb, fac)
                print(u"%s → %d 行" % (kw, len(rows)))
                matrix.extend(rows)

    # 2) 特长段（只取「种族特长」小标题之后的 h4）
    trait_start = None
    for start, end, title in hl:
        if title.strip() == u"种族特长":
            trait_start = end
            break
    tail = html[trait_start:] if trait_start else html
    traits = parse_traits(tail, heads(tail))
    print(u"特长段 → %d 个种族块，共 %d 条特长" % (len(traits), sum(len(t["traits"]) for t in traits)))

    # 3) 亮点组合整句
    combo_sentence = None
    for i, (start, end, title) in enumerate(hl):
        if title.strip() == u"全新及亮点组合":
            stop = hl[i + 1][0] if i + 1 < len(hl) else len(html)
            m = re.search(r"<p[^>]*>([\s\S]*?)</p>", html[end:stop])
            if m:
                combo_sentence = txt(m.group(1))
            break
    print(u"亮点组合句：%s" % (combo_sentence or u"（没抓到）"))

    # 4) 天裔子族与阵营的整句（只取以「天裔是」开头那一段，别把上一段并进来）
    sky_sentence = None
    for m in re.finditer(r"<p[^>]*>([\s\S]*?)</p>", html):
        cand = txt(m.group(1))
        if cand.startswith(u"天裔是") and u"塑风者天裔" in cand and u"高阶会天裔" in cand:
            sky_sentence = cand
            break
    print(u"天裔子族句：%s" % (sky_sentence or u"（没抓到）"))

    print(u"\n=== 矩阵明细 ===")
    for r in matrix:
        print(u"  %-6s %-8s %d 职业: %s" % (r["faction"], r["raceCn"], len(r["classes"]),
                                        u" ".join(r["classes"])))
    for t in traits:
        print(u"  特长 %-8s lore=%s traits=%d" % (t["raceCn"], bool(t["lore"]), len(t["traits"])))

    if not (args.write or args.link_glossary):
        print(u"\n（未写盘，加 --write 生成 src/data/races.json，加 --link-glossary 回填词条归属）")
        return

    # 组装：天裔在两张表里各一行（部落/联盟），特长段里是两个子族
    by_key = {}
    for r in matrix:
        by_key[(r["raceCn"], r["faction"])] = r
    tr_by_race = {}
    for t in traits:
        tr_by_race[t["raceCn"]] = t

    races = []
    order = [(u"兽人", "horde"), (u"亡灵", "horde"), (u"牛头人", "horde"), (u"巨魔", "horde"),
             (u"天裔", "horde"), (u"人类", "alliance"), (u"矮人", "alliance"),
             (u"暗夜精灵", "alliance"), (u"侏儒", "alliance"), (u"天裔", "alliance")]
    for race_cn, fac in order:
        mrow = by_key.get((race_cn, fac))
        if not mrow:
            continue
        is_sky = race_cn == u"天裔"
        sub = None
        if is_sky:
            sub_cn = u"塑风者天裔" if fac == "horde" else u"高阶会天裔"
            st = tr_by_race.get(sub_cn)
            sub = {"nameCn": sub_cn, "lore": st["lore"] if st else None,
                   "traits": st["traits"] if st else [],
                   "provenance": prov(st["traits"][0]["quote"], LABEL + u"·子族特长原文", today)
                   if st and st["traits"] else []}
        main_cn = race_cn if not is_sky else sub["nameCn"]
        tr = None if is_sky else tr_by_race.get(race_cn)
        cols_cn = u"、".join([k for k, v in CLASS_CN.items() if v in mrow["classes"]]) or u"未列出"
        rid = RACE_CN[race_cn] if not is_sky else ("skyborne-" + fac)
        races.append({
            "id": rid,
            "nameCn": race_cn,
            "nameEn": None,
            "faction": fac,
            "subgroup": sub,
            "classes": mrow["classes"],
            "lore": tr["lore"] if tr else None,
            "traits": tr["traits"] if tr else [],
            "level": "L0",
            "provenance": prov(None, LABEL + u"·矩阵表「%s」行：官方只给 X 标记，职业名按同页表头还原为 %s" % (race_cn, cols_cn), today)
                          + (prov(tr["lore"], LABEL + u"·种族简介原文", today) if tr and tr["lore"] else [])
                          + (prov(sub["traits"][0]["quote"], LABEL + u"·子族特长原文", today)
                             if sub and sub["traits"] else [])
        })

    combos = []
    if combo_sentence:
        for piece in re.split(u"[，、]", combo_sentence):
            piece = piece.strip(u"。包括以及首次登场的 ")
            hit = None
            for rcn in [u"兽人", u"牛头人", u"巨魔", u"亡灵", u"人类", u"矮人", u"暗夜精灵", u"侏儒", u"天裔"]:
                for kcn, cid in CLASS_CN.items():
                    if piece == rcn + kcn:
                        hit = (rcn, kcn, cid)
            if hit:
                combos.append({"raceCn": hit[0], "classCn": hit[1], "classId": hit[2],
                               "label": piece, "level": "L0",
                               "provenance": prov(combo_sentence, LABEL + u"·亮点组合整句", today)})
            elif u"天裔" in piece:
                combos.append({"raceCn": u"天裔", "classCn": None, "classId": None,
                               "label": piece, "level": "L0",
                               "provenance": prov(combo_sentence, LABEL + u"·亮点组合整句", today)})

    payload = {
        "meta": {
            "generatedAt": today,
            "kind": "official-cn-extract",
            "method": u"tools/extract-races.py 按官方页自身结构取数：h3「部落/联盟种族与职业组合」→ 紧跟的表格；"
                      u"h4 种族名 → 紧跟的 em 简介与 ul 特长列表。矩阵里官方只写 X，职业名取自同页表头。",
            "sources": [{"url": URL, "label": LABEL}],
            "notCollected": [
                u"英文原名：官方中文公告未给出，逐词硬造等于编造，一律留空",
                u"阵营之外的可选种族：血精灵、兽人萨满之外的经典旧世组合等，官方本页没提就是没提",
                u"种族数值平衡与实测改动：Beta 阶段官方只给描述句，不做推算",
                u"种族图标：无限服新种族图标能否从官方 CDN 取得尚未证实，本页用首字色块不热链"
            ]
        },
        "factions": [
            {"id": "horde", "nameCn": u"部落"},
            {"id": "alliance", "nameCn": u"联盟"}
        ],
        "classOrder": [u"druid", u"hunter", u"mage", u"paladin", u"priest",
                       u"rogue", u"shaman", u"warlock", u"warrior"],
        "races": races,
        "newCombos": combos,
        "conflicts": [
            {
                "id": "skyborne-class-breadth",
                "topic": u"天裔到底能选几个职业",
                "level": "L2",
                "a": {
                    "saying": u"同页两张矩阵表里，天裔在部落标了 5 个职业、在联盟标了 5 个职业（含德鲁伊、猎人、潜行者、战士）。",
                    "detail": u"%s" % u"；".join(
                        [u"%s：%s" % (u"部落" if r["faction"] == "horde" else u"联盟",
                                      u"、".join([k for k, v in CLASS_CN.items() if v in r["classes"]]))
                         for r in matrix if r["raceCn"] == u"天裔"])
                },
                "b": {
                    "saying": u"同页导语只写明：塑风者天裔能成为萨满祭司、高阶会天裔能成为法师，没有说子族是否只能选这一个。",
                    "quote": sky_sentence or u""
                },
                "handling": u"两个都留：可选职业按矩阵表显示，导语那句原样引用，不替玩家判定子族是否独占单一职业；正式服建号实测后再定。"
            }
        ],
        "skyborneNote": {"text": sky_sentence, "level": "L0",
                         "provenance": prov(sky_sentence, LABEL + u"·天裔子族与阵营整句", today)
                         if sky_sentence else []}
    }
    out = os.path.join(DATA, "races.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print(u"已写入 %s：%d 个种族行 / %d 条亮点组合" % (os.path.relpath(out, ROOT), len(races), len(combos)))
    if args.link_glossary:
        link_glossary(races)


if __name__ == "__main__":
    main()
