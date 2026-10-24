#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对站主客户端导出的 DB2 表做一次「能不能用」的体检，只读，不落任何数据文件。

为什么要有这个脚本而不是直接看 CSV：
    WDC5 导出的 CSV **表头是 id,f0..fN，没有列名**，值也还是原始 packed 整数。
    所以"这一列是不是名字/图标"不能靠猜列序，只能用已知集合反查。这个脚本干的就是反查：
      ① 全表有没有可读文本（判"名字能不能直接从 CSV 拿"）；
      ② 拿 ManifestInterfaceItemIcon 的 FileDataID 全集去各表逐列命中（判"ID 是不是裸值"
         并顺带定出图标列在哪）；
      ③ 原始 .db2 里有没有字符串块（判"名字要不要自己解析才能拿到"）；
      ④ 客户端 Item 表与我们 items.json 名录互相差多少（名录线的缺口与冲突数）。
    这四条是"要不要开工解析 DB2"的判断依据，跑一次几十秒，比凭印象决定省一整轮返工。

用法：
    python3 tools/audit-db2-item-table.py                 # 用默认包路径
    python3 tools/audit-db2-item-table.py --pkg <目录>     # 指定某一轮的包
"""
import argparse
import csv
import io
import json
import os
import re
import sys

HOME = os.path.expanduser('~')
DEF_PKG = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow', 'ziliao-export-2026-10-22')
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WEB, "app", "data")
WORD = re.compile(r'[A-Za-z][A-Za-z\'-]{4,}')
TEXTISH = re.compile(rb'[ -~]{6,}')
# 导出方自己确认过的列（见包内 RESULT.json 的 notes），这里只是复述，不当成本脚本的结论
KNOWN = {'CreatureDisplayInfo': {'f1': 'CreatureModelID', 'f27': '贴图变体数组'},
         'CreatureModelData': {'f2': '模型 .m2 的 FileDataID'}}


def rows(path):
    with io.open(path, encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        cols = list(r.fieldnames or [])
        yield cols
        for x in r:
            yield x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pkg', default=DEF_PKG)
    a = ap.parse_args()
    db2 = os.path.join(a.pkg, 'db2')
    if not os.path.isdir(db2):
        sys.exit('找不到 %s——包没到本地？先按 docs/DATA-CLIENT-EXPORT-RESULT-2026-10-21.md 第四节把文件弄过来' % db2)

    csvs = sorted(f for f in os.listdir(db2) if f.endswith('.csv') and f != 'db2-export-report.csv')
    print('包：%s' % os.path.abspath(a.pkg))
    print('CSV %d 张\n' % len(csvs))

    # ① 可读文本
    print('① CSV 里有没有可读文本（判"名字能不能直接从 CSV 拿"）')
    any_text = False
    for f in csvs:
        txt = io.open(os.path.join(db2, f), encoding='utf-8', errors='ignore').read(6_000_000)
        n = len(WORD.findall(txt))
        any_text = any_text or n > 0
        print('   %-30s 英文词 %6d' % (f, n))
    print('   → 判定：%s\n' % ('有文本，可以直接读' if any_text else
                          '全部 0 文本——CSV 导出没解析字符串，名字类信息一张都不在 CSV 里'))

    # ② FileDataID 反查
    icon = set()
    mip = os.path.join(db2, 'ManifestInterfaceItemIcon.csv')
    if os.path.exists(mip):
        for i, row in enumerate(rows(mip)):
            if i == 0:
                continue
            v = (row.get('id') or '').strip()
            if v:
                icon.add(v)
    print('② 用图标表的 FileDataID 全集反查各列（判"ID 是不是裸值"，并定出图标列）')
    print('   ManifestInterfaceItemIcon 给了 %d 个号' % len(icon))
    icon_cols = {}
    for f in csvs:
        if f.startswith('ManifestInterface'):
            continue
        hits = {}
        it = rows(os.path.join(db2, f))
        cols = next(it)
        n = 0
        for row in it:
            n += 1
            for k, v in row.items():
                if v.strip() in icon:
                    hits[k] = hits.get(k, 0) + 1
        top = {k: c for k, c in hits.items() if c > max(20, n // 100)}
        if top:
            tbl = f[:-4]
            icon_cols[tbl] = top
            print('   %-24s 行数 %6d · 命中列 %s' % (tbl, n, top))
    if not icon_cols:
        print('   没有任何一列大量命中')
    print('   → 判定：%s\n' % ('FileDataID 在 CSV 里是裸数值，所以"按 ID 搜不到"这种负结论是有效证据'
                           if icon_cols else '没找到裸 ID，按 ID 搜出的 0 命中不能当证据'))

    # ③ .db2 字符串块
    print('③ 原始 .db2 里有没有字符串块（判"名字要不要自己解析才拿得到"）')
    for f in sorted(os.listdir(db2)):
        if not f.endswith('.db2'):
            continue
        b = open(os.path.join(db2, f), 'rb').read()
        frags = [x.decode('ascii', 'ignore') for x in TEXTISH.findall(b)]
        frags = [x for x in frags if re.search(r'[A-Za-z]{4}', x) and 'camelot' not in x and 'wowstatic' not in x]
        print('   %-28s 可读片段 %6d 个  例：%s' % (f, len(frags), frags[:3]))
    print()

    # ④ 名录对账
    ip = os.path.join(db2, 'Item.csv')
    if os.path.exists(ip) and os.path.exists(os.path.join(DATA, 'items.json')):
        cli = set()
        it = rows(ip)
        next(it)
        for row in it:
            s = (row.get('id') or '').strip()
            if s and int(s) > 0:
                cli.add(int(s))
        ours = json.load(io.open(os.path.join(DATA, 'items.json'), encoding='utf-8'))['items']
        ours_ids = {int(x['id']) for x in ours}
        by_id = {int(x['id']): x for x in ours}
        only_us = sorted(ours_ids - cli)
        print('④ 客户端 Item 表 vs 我们的物品名录')
        print('   客户端 %d 件 · 我们 %d 件 · 客户端有而我们没有 %d 件'
              % (len(cli), len(ours_ids), len(cli - ours_ids)))
        print('   我们有而客户端没有 %d 件，按我们标的状态分开看：' % len(only_us))
        buckets = {}
        for i in only_us:
            st = by_id[i].get('status') or '?'
            buckets.setdefault(st, []).append(i)
        for st, ids in sorted(buckets.items()):
            # 标"无限中没有"的本来就该缺，那是互相印证；标新增的缺了才是冲突
            tag = '互相印证，不是问题' if st == 'missing' else '**冲突，要单独记**'
            print('     状态 %s：%d 件 %s ← %s' % (st, len(ids), ids[:8], tag))
    print('\n已知列（复述导出方在 RESULT.json notes 里自己确认的，本脚本没独立验）：')
    for t, cols in KNOWN.items():
        print('   %s：%s' % (t, cols))


main()
