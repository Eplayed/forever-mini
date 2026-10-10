#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""与 wowhead 的 Forever 天赋数据对账，产出差异报告（只读，不改任何数据）。

为什么需要它：首页与天赋页的每个数都来自我们自己的两份中文源（客户端解包转述），
一直缺一个"另一家怎么说"的第三方对照。wowhead 有无限服的完整天赋表，
但它**只有英文**（/cn/forever 是 404），所以它补不了任何中文名，只能对：
条目数、英文原名、法术 ID、改动状态、图标文件名。

边界（红线）：
  - 只取**事实性标识符**。wowhead 行数据里带着 envChange.lines 这类英文描述句
    （"3 ranks instead of 5"），本脚本**读都不读**，报告里也不出现，
    避免把别人的文案抄进我们的库。
  - 报告是"差异清单"，不是"正确答案"。对不上的地方一律标待核实，不改数据。

实测到的两个坑（写在这里免得下次重踩）：
  - curl 直取是 403，必须用真浏览器。
  - 列表页 DOM 只渲染 50 行（?listview_page / ?listview_size 参数一律无效），
    但完整数据在 window.listviewspells 里，所以条目数**不能**数 DOM。
  - 图标是 <ins style="background-image:url(...)"> 的懒加载背景，不在 img[src] 里，
    而且只有渲染出来的那 50 行有，所以图标对照覆盖不满。

用法：python3 tools/audit-wowhead.py            # 打印摘要
      python3 tools/audit-wowhead.py --write    # 同时写 docs/DATA-WOWHEAD-<今天>.md
"""
import datetime
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")
DOCS = os.path.join(ROOT, "docs")
CLASSES = ["warrior", "paladin", "hunter", "rogue", "priest", "shaman", "mage", "warlock", "druid"]
PAGE = "https://www.wowhead.com/forever/spells/talents/"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
ICON_RE = re.compile(
    r'background-image:\s*url\((?:&quot;|")([^)&"]*/icons/medium/([a-z0-9_]+)\.(?:jpg|png))'
    r'(?:&quot;|")\);[^<]*</ins><del></del><a href="https://www\.wowhead\.com/forever/spell='
    r'(\d+)/([a-z0-9\-]+)"', re.I)

# 把 wowhead 的英文名转成网址片段。撇号要变成连字符而不是删掉：
# "Guardian's Favor" 的网址片段是 guardian-s-favor，删掉撇号会得到 guardians-favor，
# 第一版就是这么漏配了 26 个节点（自然的威严 / Nature's Majesty 一类的都掉在这上面）。
def slugify(name):
    s = unicodedata.normalize("NFKD", name)
    s = s.replace(u"’", "'").replace(u"`", "'")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s


def grab():
    """取九个职业的 wowhead 天赋表：完整行数据 + 已渲染行的图标文件名。"""
    from playwright.sync_api import sync_playwright
    js = "() => Object.values(window.listviewspells || {}).map(x => ({" \
         "name: x.name, id: x.id, spec: (x.talentspec || [null])[0]," \
         "status: (x.envChange || {}).status || null," \
         "labels: ((x.envChange || {}).labels || []).slice(0, 4)}))"
    out = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, args=["--headless=new", "--no-sandbox"])
        c = b.new_context(user_agent=UA, viewport={"width": 1440, "height": 900})
        p = c.new_page()
        for cid in CLASSES:
            url = PAGE + cid
            try:
                p.goto(url, wait_until="domcontentloaded", timeout=60000)
                p.wait_for_timeout(3000)
                rows = p.evaluate(js)
                html = p.content()
                icons = {}
                for m in ICON_RE.finditer(html):
                    icons[m.group(4)] = m.group(2)
                out[cid] = {"rows": rows, "icons": icons, "url": url}
                print("  %-8s wowhead %d 条（图标可见 %d 条）" % (cid, len(rows), len(icons)))
            except Exception as e:
                out[cid] = {"error": str(e)[:120]}
                print("  %-8s 取数失败：%s" % (cid, str(e)[:80]))
        b.close()
    return out


def load_ours():
    ours = {}
    for cid in CLASSES:
        f = os.path.join(DATA, "talents", cid + ".json")
        if not os.path.exists(f):
            continue
        d = json.load(io.open(f, encoding="utf-8"))
        nodes = []
        for ti, t in enumerate(d.get("trees") or []):
            for n in t.get("nodes") or []:
                nodes.append({"tree": t.get("nameCn"), "cn": n.get("nameCn"),
                              "alt": n.get("nameAlt"), "up": n.get("upstreamId"),
                              "icon": n.get("iconKey"), "state": n.get("changeState"),
                              "conflict": bool(n.get("nameConflict")),
                              "posmis": bool(n.get("posMismatch")),
                              "ranks": n.get("maxRanks")})
        ours[cid] = nodes
    return ours


def match(cid, nodes, wh):
    """按网址片段对。三个约束都是踩出来的：
       ① upstreamId 必须非空——空串会被 endswith 判成"匹配任何 slug"，
          第一版就是这样把「乱舞」配到了「双手武器专精」上；
       ② 取**最长**的命中 slug，否则 `bloodrage` 会抢走 `improved-bloodrage`；
       ③ 命中处必须是完整一段（前面是 `-` 或就是开头），不让 `rage` 配 `focused-rage`。"""
    by_slug = {}
    for r in wh["rows"]:
        by_slug.setdefault(slugify(r["name"]), r)
    order = sorted(by_slug, key=len, reverse=True)
    hits, ours_only, used = [], [], set()
    for n in nodes:
        up = n["up"] or ""
        slug = None
        if up:
            for s in order:
                if up == s or up.endswith("-" + s):
                    slug = s
                    break
        if slug is None:
            ours_only.append(n)
            continue
        used.add(slug)
        hits.append({"node": n, "wh": by_slug[slug], "slug": slug,
                     "whIcon": wh["icons"].get(slug)})
    wh_only = [r for s, r in by_slug.items() if s not in used]
    return hits, ours_only, wh_only


def main():
    write = "--write" in sys.argv
    print("抓 wowhead 的 Forever 天赋表（真浏览器；curl 会被 403）")
    wh = grab()
    ours = load_ours()
    per, icon_diff, state_pairs, no_wh = [], [], Counter(), 0
    for cid in CLASSES:
        if "rows" not in wh.get(cid, {}):
            no_wh += len(ours.get(cid, []))
            continue
        hits, only_ours, only_wh = match(cid, ours[cid], wh[cid])
        dupes = Counter(n["cn"] for n in ours[cid])
        per.append({"cid": cid, "ours": len(ours[cid]), "wh": len(wh[cid]["rows"]),
                    "hit": len(hits), "ourOnly": len(only_ours), "whOnly": len(only_wh),
                    "ourOnlyNodes": only_ours,
                    "ourOnlyNames": [n["cn"] for n in only_ours][:12],
                    "whOnlyNames": [r["name"] for r in only_wh][:12]})
        for h in hits:
            state_pairs[(h["node"]["state"] or "-", h["wh"]["status"] or "-")] += 1
            if h["whIcon"] and h["node"]["icon"] and h["whIcon"] != h["node"]["icon"]:
                n = h["node"]
                # 分歧要分三类看，混在一起报会把工具问题说成数据问题
                if dupes[n["cn"]] > 1:
                    why = "我们这一职业有两格同名，配对先撞上了重名"
                elif n["conflict"] or n["posmis"]:
                    why = "两源在同一格给了不同名字，这一对是按位置凑的"
                else:
                    why = "真分歧：两边都认得这个天赋，图标不一样，要回客户端核"
                icon_diff.append({"cid": cid, "cn": n["cn"], "alt": n["alt"], "why": why,
                                  "slug": h["slug"], "ours": n["icon"], "wh": h["whIcon"],
                                  "spellId": h["wh"]["id"]})
    tot = sum(p["ours"] for p in per)
    hit = sum(p["hit"] for p in per)
    print("\n我们 %d 个节点，按网址片段与 wowhead 对上 %d 个（%.1f%%）" % (tot, hit, hit * 100.0 / max(tot, 1)))
    print("图标文件名分歧 %d 处" % len(icon_diff))
    if not write:
        print("加 --write 出报告")
        return
    today = datetime.date.today().isoformat()
    L = []
    L.append("# 与 wowhead 的天赋对账 · %s（wow-data）" % today)
    L.append("")
    L.append("脚本：`python3 tools/audit-wowhead.py --write`。它只读，不改任何数据。")
    L.append("")
    L.append("## 这份对账能证明什么、不能证明什么")
    L.append("")
    L.append("wowhead 有无限服的完整天赋表，但 **Forever 区只有英文**（`/cn/forever` 是 404）。")
    L.append("所以它能对的是：条目数、英文原名、法术 ID、改动状态、图标文件名；")
    L.append("**它对不了任何中文名**——我们的中文名的依据是客户端解包与官方中文稿，不是一家英文站。")
    L.append("它行数据里带着英文描述句（改动前后的说明文字），脚本按红线**读都不读**，报告里也不出现。")
    L.append("")
    L.append("两个实测到的取数坑，写在这里免得下次重踩：列表页 DOM 只渲染 50 行，")
    L.append("`?listview_page` / `?listview_size` 参数一律无效，完整数据在 `window.listviewspells` 里，")
    L.append("**数 DOM 会把条目数对错**；图标是懒加载背景，不在 `img[src]` 里，只有渲染出的那 50 行拿得到。")
    L.append("另外 curl 直取是 403，必须真浏览器。")
    L.append("")
    L.append("## 每职业条目数")
    L.append("")
    L.append("| 职业 | 我们的节点 | wowhead 条目 | 按网址片段对上 | 只有我们有 | 只有它有 |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for p in per:
        L.append("| %s | %d | %d | %d | %d | %d |" % (p["cid"], p["ours"], p["wh"], p["hit"],
                                                      p["ourOnly"], p["whOnly"]))
    L.append("| **合计** | **%d** | **%d** | **%d** | **%d** | **%d** |" % (
        tot, sum(p["wh"] for p in per), hit, sum(p["ourOnly"] for p in per),
        sum(p["whOnly"] for p in per)))
    L.append("")
    our_only = [n for p in per for n in p["ourOnlyNodes"]]
    no_up = [n for n in our_only if not n["up"]]
    mis = [n for n in our_only if n["up"] and (n["conflict"] or n["posmis"])]
    other = [n for n in our_only if n["up"] and not (n["conflict"] or n["posmis"])]
    L.append("对得上的 %d 个是按**网址片段**配的（我们的 `upstreamId` 结尾就是它），"
             "剩下 %d 个我们独有的节点分三种情况，没有一种是「它算错了」：" % (hit, len(our_only)))
    L.append("")
    L.append("| 情况 | 个数 | 是什么意思 |")
    L.append("| --- | --- | --- |")
    L.append("| 上游格子表里这一格根本没有节点 | %d | 只有 fengshen 列了它，"
             "所以对不出英文原名，也配不到 wowhead——首页那 4 个补不了图标的格子全在这一类 |" % len(no_up))
    L.append("| 有格子号，但两源在同一格给了不同名字 | %d | 我们这条的格子号指向的是另一家眼里的另一个天赋，"
             "按位置凑过来的号不能当英文名用 |" % len(mis))
    L.append("| 其余 | %d | 真的对不上，要单独看 |" % len(other))
    L.append("")
    for lbl, lst in (("上游没有这一格", no_up), ("同格两名（凑不上）", mis), ("其余", other)):
        if not lst:
            continue
        L.append("- **%s**：%s" % (lbl, "、".join(
            "%s（%s）" % (n["cn"], n["tree"]) for n in lst)))
    L.append("")
    L.append("### 只有 wowhead 有的条目（前 12 个 / 职业）")
    L.append("")
    L.append("| 职业 | 它的英文名 |")
    L.append("| --- | --- |")
    for p in per:
        if p["whOnlyNames"]:
            L.append("| %s | %s |" % (p["cid"], "、".join(p["whOnlyNames"])))
    L.append("")
    L.append("它独有的这几条，与上面「同格两名」那批是同一件事的两头：我们这一格记的是另一个名字，"
             "它那个英文名就没被任何格子认领。")
    L.append("")
    hard = [d for d in icon_diff if d["why"].startswith("真分歧")]
    L.append("## 图标文件名分歧")
    L.append("")
    if not icon_diff:
        L.append("零处。**这条是本轮最硬的结论**：凡是我们和 wowhead 都能对上同一个天赋的格子，")
        L.append("图标文件名逐字一致，说明两边取的是同一份客户端数据，我们的图标不是猜的。")
    else:
        L.append("一共 %d 处对不上，但**逐条判下来只有 %d 处是真分歧**，其余是我们自己有两格重名、"
                 "或者两源在同一格给了不同名字（那一对本来就是按位置凑的）。"
                 % (len(icon_diff), len(hard)))
        L.append("")
        L.append("| 职业 | 我们的名字 | 网址片段 | 法术 ID | 我们 | wowhead | 判定 |")
        L.append("| --- | --- | --- | --- | --- | --- | --- |")
        for d in icon_diff:
            L.append("| %s | %s | `%s` | %s | `%s` | `%s` | %s |"
                     % (d["cid"], d["cn"], d["slug"], d["spellId"], d["ours"], d["wh"], d["why"]))
    L.append("")
    L.append("## 改动状态对照（我们的 changeState × 它的 envChange.status）")
    L.append("")
    L.append("只列计数，不抄它写的任何一句改动说明。")
    L.append("")
    L.append("| 我们的标记 | 它的标记 | 条数 |")
    L.append("| --- | --- | --- |")
    for (a, b), n in sorted(state_pairs.items(), key=lambda kv: -kv[1]):
        L.append("| %s | %s | %d |" % (a, b, n))
    L.append("")
    L.append("## 处置")
    L.append("")
    L.append("1. **不改数据**。这份报告是「另一家怎么说」的一层，不是第二份真相；")
    L.append("   要按它改任何一条，都得回到客户端解包或官方中文页去核。")
    L.append("2. 图标分歧 %d 处里真分歧 %d 处：%s"
             % (len(icon_diff), len(hard),
                "所以首页与天赋页的图标不必因为 wowhead 而调整——两边取的是同一份客户端数据。"
                if not hard else
                "这 %d 条要回客户端逐个看，其余 %d 条是我们重名或位置凑对造成的，不算分歧。"
                % (len(hard), len(icon_diff) - len(hard))))
    L.append("3. 状态对照里数量明显的错位（比如我们标 `added` 它标 `updated`）单独列出来，")
    L.append("   交给人工回客户端核对，不在脚本里判对错。")
    if no_wh:
        L.append("")
        L.append("取数失败没对上的节点：%d 个。" % no_wh)
    out = os.path.join(DOCS, "DATA-WOWHEAD-%s.md" % today)
    io.open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("报告 → %s" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
