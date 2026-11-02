#!/usr/bin/env python3
# 从两份无限服插件的 Data.lua 抽物品详情字段，落成 upstream 修剪快照（物品线二批，方案 A）。
# 依据 docs/wow-infinite-sources.md 第十四/十五节的判定：只取事实性字段——
#   GI（GearInsight 无限版，beta 解包）：st（tooltip 事实行）、src（dungeon/quest 出处归类）
#   XR（XR_DungeonGuide 全能助手，社区整理稿）：st、sell（卖价）
# nEn 按站主 2026-10-14 拍板不取；两份数据都不含描述正文与掉率（XR loot 无概率字段）。
# 用法：python3 tools/extract-addon-items-detail.py --gi <GearInsight_Forever/Data.lua> --xr <XR_DungeonGuide/Data.lua>
#       XR v94.7 之后物品表在 XR_DungeonGuide/Data_Items.lua，--xr 给它就行（两个锚点都认）。
# 产物：app/data/upstream/gi-items-detail.json、app/data/upstream/xr-items-detail.json
# 幂等：同输入字节一致（键按数字序、缩进固定）。
import argparse
import io
import json
import os
import re
import sys
from datetime import date

from addons_root import resolve

UP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'data', 'upstream')
# 2026-10-24 删旧站时这一层就没了，路径一直留在 'src/data' 上没跟着改：
# 结果这个脚本写不出快照（物品线的刷新等于断在 10-21 那一版）。改指 app/data/upstream。

# XR 物品总表的两个锚点：v94.7 之前是 Data.lua 里的 D.items，之后是 Data_Items.lua 里的 XR_DGDB.items。
# 顺序不能倒——'D.items = {' 是 'XR_DGDB.items = {' 的子串，先试它会匹配到拆表后那份的尾巴上。
XR_ANCHORS = ('XR_DGDB.items = {', 'D.items = {')


def toc_version(lua_path, addon_name):
    """版本号从插件自己的 .toc 读。以前这里手写 0.4.29 / 0.37.1，
       插件升到 GI 0.5.1、XR 66 之后快照还在盖旧号的出处——等于每条记录都写了句过期假话。
       （2026-10-19 那条"版本号不再手抄"的规矩同样适用于这份提取器。）"""
    p = os.path.join(os.path.dirname(os.path.abspath(lua_path)), addon_name + '.toc')
    if not os.path.exists(p):
        return 'unknown'
    for line in io.open(p, encoding='utf-8', errors='replace'):
        m = re.match(r'\s*##\s*Version:\s*(\S+)', line)
        if m:
            return m.group(1)
    return 'unknown'


def src_stamp(lua_path):
    """源文件自己的指纹：字节数 + SHA256 + 文件日期。
       fetched（插件数据的自述/落盘日）与 extractedAt（本次跑提取的日）分开记，不混。"""
    b = open(lua_path, 'rb').read()
    import hashlib
    from datetime import datetime
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
            'fileDate': datetime.fromtimestamp(os.path.getmtime(lua_path)).strftime('%Y-%m-%d')}


def brace_match(seg, start):
    """seg[start] 必须是 '{'，返回配对 '}' 的下标（Lua 字符串感知）。"""
    depth, j, n, q = 0, start, len(seg), None
    while j < n:
        c = seg[j]
        if q:
            if c == '\\':
                j += 2
                continue
            if c == q:
                q = None
        elif c in '"\'':
            q = c
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError('大括号不配对 @%d' % start)


def inner_list(entry, key):
    """取 entry 里 key={...} 的内部文本并按顶层逗号切分成字符串数组。"""
    m = re.search(key + r'\s*=\s*\{', entry)
    if not m:
        return None
    b = m.end() - 1
    e = brace_match(entry, b)
    inner = entry[b + 1:e]
    parts, buf, q, i, n = [], '', None, 0, len(inner)
    while i < n:
        c = inner[i]
        if q:
            if c == '\\' and i + 1 < n:
                buf += c + inner[i + 1]
                i += 2
                continue
            if c == q:
                q = None
                i += 1
                continue
            buf += c
            i += 1
            continue
        if c in '"\'':
            q = c
            i += 1
            continue
        if c == ',':
            parts.append(buf)
            buf = ''
            i += 1
            continue
        buf += c
        i += 1
    if buf.strip():
        parts.append(buf)
    # 扫描时引号已剥掉，这里只做反转义，不能再剥首尾字符
    return [p.strip().replace('\\"', '"').replace('\\\\', '\\') for p in parts if p.strip()]


def extract_gi(path):
    src = open(path, encoding='utf-8').read()
    # 锚定必须带行首两格缩进：'gear = {' 的裸字符串在 loot 表一带出现过，
    # 直接 index 会切错片段。GI 有两张互补表：
    #   loot（fc Beta 实测掉落，foreverchanges.pro）：本→首领→物品，物品带 st/nEn/seen —— 取 st
    #   gear（按九职业铺的出处表）：物品带 src(dungeon/quest) + srcName("本 · 首领") —— 取出处
    a_loot = re.search(r'(?m)^  loot = \{', src)
    a_rares = re.search(r'(?m)^  rares = \{', src)
    a_gear = re.search(r'(?m)^  gear = \{', src)
    a_spells = re.search(r'(?m)^  spells = \{', src)
    if not (a_loot and a_rares and a_gear and a_spells):
        sys.exit('GI Data.lua 找不到 loot/rares/gear/spells 顶层表')
    loot_seg = src[a_loot.end() - 1:a_rares.start()]
    gear_seg = src[a_gear.end() - 1:a_spells.start()]
    st_items, src_items = {}, {}
    for m in re.finditer(r'\{id=(\d+), n="[^"]*", nEn="', loot_seg):
        e = loot_seg[m.start():brace_match(loot_seg, m.start()) + 1]
        st = inner_list(e, 'st')
        if st:
            st_items[m.group(1)] = {'st': st}
    for m in re.finditer(r'\{id=(\d+), n="', gear_seg):
        e = gear_seg[m.start():brace_match(gear_seg, m.start()) + 1]
        rec = {}
        ms = re.search(r'(?<!\w)src="([^"]*)"', e)
        mn = re.search(r'srcName="([^"]*)"', e)
        if ms and ms.group(1):
            rec['src'] = ms.group(1)
        if mn and mn.group(1):
            rec['srcName'] = mn.group(1)
        if rec:
            src_items[m.group(1)] = rec
    return st_items, src_items


def extract_xr(path):
    src = open(path, encoding='utf-8').read()
    # XR v94.7 把这张物品总表从 Data.lua 拆进了 Data_Items.lua，锚点名也跟着变了。
    # 只认旧锚点会在"文件读到了、表没了"时静默抽回 0 件，所以两个都试、都没有就报错退出。
    for a_prefix in XR_ANCHORS:
        a = src.find(a_prefix)
        if a >= 0:
            break
    else:
        sys.exit('XR 物品表锚点没找到（试过 %s）——插件又改了表名或拆分方式，先人工看文件再改这里'
                 % ' / '.join(XR_ANCHORS))
    b = brace_match(src, a + len(a_prefix) - 1)
    seg = src[a:b]
    items, st_n, sell_n = {}, 0, 0
    for m in re.finditer(r'\[(\d{4,7})\]=\{', seg):
        start = m.end() - 1
        e = seg[start:brace_match(seg, start) + 1]
        rec = {}
        st = inner_list(e, 'st')
        if st:
            rec['st'] = st
            st_n += 1
        ms = re.search(r'sell="([^"]*)"', e)
        if ms and ms.group(1):
            rec['sell'] = ms.group(1)
            sell_n += 1
        if rec:
            items[m.group(1)] = rec
    return items, st_n, sell_n


def source_ref(path, addon):
    """快照里记「插件名/文件名」＋安装根目录名，不记绝对路径：
       插件装在仓库外的另一块盘上，跨盘 relpath 会直接抛 ValueError；
       绝对路径又会把某台机器的目录写进全线共用的数据基底。"""
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
    return '%s/%s' % (addon if parent == addon else parent, os.path.basename(path))


def install_root(path):
    """安装根是 AddOns 往上两层那个客户端目录（本机是 _cn_beta_），不是它上面的 Interface。"""
    parts = os.path.abspath(path).split(os.sep)
    if 'AddOns' in parts:
        i = len(parts) - 1 - parts[::-1].index('AddOns')
        if i >= 2:
            return parts[i - 2]
    return 'unknown'


def xr_fetched(path):
    """作者自述的抓取日写在同目录 Data.lua 的 D.fetched 里，拆出去的 Data_Items.lua 自己没带。
       以前这里手抄 '2026-09-20'：插件重生成一次，快照上那一行就变成写在每条记录上的过期假话。"""
    sib = os.path.join(os.path.dirname(os.path.abspath(path)), 'Data.lua')
    if os.path.exists(sib):
        m = re.search(r'D\.fetched\s*=\s*"([^"]+)"',
                      io.open(sib, encoding='utf-8', errors='replace').read())
        if m:
            return m.group(1)
    return 'unknown'


def dump(p, obj, n):
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('写 %s（%d 件）' % (os.path.relpath(p), n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gi', help='GearInsight_Forever/Data.lua 路径（不给就用本机插件目录里那份）')
    ap.add_argument('--xr', help='XR_DungeonGuide 的物品表路径（不给就用本机那份）')
    args = ap.parse_args()
    # 不给路径就用 addons_root 解析出来的现役插件目录：
    # 站主 2026-11-01 定「Mac 不再做，全部在这台」，手给 --src 这种用法不该是每天的必经步骤
    if not args.gi:
        cand = os.path.join(resolve('GearInsight_Forever'), 'GearInsight_Forever', 'Data.lua')
        args.gi = cand if os.path.exists(cand) else None
    if not args.xr:
        root = resolve('XR_DungeonGuide')
        for name in ('Data_Items.lua', 'Data.lua'):     # v94.7 之后物品表在 Data_Items.lua
            cand = os.path.join(root, 'XR_DungeonGuide', name)
            if os.path.exists(cand) and 'items' in io.open(cand, encoding='utf-8', errors='replace').read(4000000):
                args.xr = cand
                break
    if not args.gi and not args.xr:
        sys.exit('至少给 --gi 或 --xr 其一（或把插件装到 addons_root 认的位置）')
    os.makedirs(UP, exist_ok=True)
    if args.gi:
        st_items, src_items = extract_gi(args.gi)
        dump(os.path.join(UP, 'gi-items-detail.json'), {
            'meta': {
                'addon': 'GearInsight_Forever',
                'addonVersion': toc_version(args.gi, 'GearInsight_Forever'),
                'sourceFile': source_ref(args.gi, 'GearInsight_Forever'),
                'installRoot': install_root(args.gi),
                'sourceStamp': src_stamp(args.gi),
                # 表内自述的采集口径（作者标注的 build / 日期），与本次提取日分开记
                'selfReported': 'st 抽自 loot 表（作者标 Beta 实测掉落，build 1.60.1.69913）；'
                                'src/srcName 抽自 gear 表（作者标 beta 客户端 1.60.1.69876 解包，2026-10-03）',
                'fetched': '2026-10-03',
                'extractedAt': date.today().isoformat(),
                'counts': {'st': len(st_items), 'src': len(src_items)},
            },
            'st': {k: st_items[k] for k in sorted(st_items, key=int)},
            'src': {k: src_items[k] for k in sorted(src_items, key=int)},
        }, len(st_items) + len(src_items))
    if args.xr:
        items, st_n, sell_n = extract_xr(args.xr)
        dump(os.path.join(UP, 'xr-items-detail.json'), {
            'meta': {
                'addon': 'XR_DungeonGuide',
                'addonVersion': toc_version(args.xr, 'XR_DungeonGuide'),
                'sourceFile': source_ref(args.xr, 'XR_DungeonGuide'),
                'installRoot': install_root(args.xr),
                'sourceStamp': src_stamp(args.xr),
                'selfReported': '站点 research/dg-loot 社区整理稿（作者自述实测，不自动升本站 L0）',
                'fetched': xr_fetched(args.xr),
                'extractedAt': date.today().isoformat(),
                'counts': {'total': len(items), 'st': st_n, 'sell': sell_n},
            },
            'items': {k: items[k] for k in sorted(items, key=int)},
        }, len(items))


if __name__ == '__main__':
    main()
