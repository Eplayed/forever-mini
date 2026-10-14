#!/usr/bin/env python3
# 合并两份 upstream 修剪快照 → src/data/items-detail.json（物品线二批，方案 A）。
# 优先级（docs/wow-infinite-sources.md 第十四/十五节 + 站主 2026-10-14 拍板）：
#   属性 st：GI loot 表（fc Beta 实测转述）优先，XR（社区整理稿）兜底；两源不一致取 GI 并留档差异
#   卖价 sell：只有 XR 有；出处 src/srcName：只有 GI gear 表有
#   英文名不取（站主拍板）；两份源都不含描述正文与掉率
# 只收 items.json 里存在的 id；孤儿（源里有、名录没有）计数不丢弃信息（meta.orphans）。
# 幂等：键按数字序、缩进固定，重跑字节一致。
import json
import os
import sys
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'data')
CONFLICT_CAP = 300


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def main():
    gi = load(os.path.join(ROOT, 'upstream', 'gi-items-detail.json'))
    xr = load(os.path.join(ROOT, 'upstream', 'xr-items-detail.json'))
    items = load(os.path.join(ROOT, 'items.json'))
    valid_ids = {str(x['id']) for x in items['items']}

    gi_st, gi_src = gi.get('st', {}), gi.get('src', {})
    xr_items = xr.get('items', {})
    orphans = sorted(
        [k for k in gi_st if k not in valid_ids] +
        [k for k in gi_src if k not in valid_ids] +
        [k for k in xr_items if k not in valid_ids],
        key=int)

    out, conflicts = {}, []
    n_st = n_st_gi = n_st_xr = n_sell = n_src = 0
    for kid in sorted(valid_ids, key=int):
        rec = {}
        g_st = (gi_st.get(kid) or {}).get('st')
        x_st = (xr_items.get(kid) or {}).get('st')
        if g_st:
            rec['st'] = g_st
            rec['stFrom'] = 'gi'
            n_st += 1
            n_st_gi += 1
            if x_st and x_st != g_st:
                conflicts.append({'id': int(kid), 'gi': g_st, 'xr': x_st})
        elif x_st:
            rec['st'] = x_st
            rec['stFrom'] = 'xr'
            n_st += 1
            n_st_xr += 1
        x_sell = (xr_items.get(kid) or {}).get('sell')
        if x_sell:
            rec['sell'] = x_sell
            n_sell += 1
        g = gi_src.get(kid)
        if g:
            rec['src'] = g['src']
            rec['srcName'] = g['srcName']
            n_src += 1
        if rec:
            out[kid] = rec

    doc = {
        'meta': {
            'generatedAt': date.today().isoformat(),
            'method': 'tools/merge-items-detail.py 合 upstream 两份修剪快照（gi-items-detail / xr-items-detail，'
                      '由 tools/extract-addon-items-detail.py 从两份无限服插件 Data.lua 抽取）；'
                      '属性 GI 实测转述优先、XR 社区稿兜底，两源不一致取 GI 并留档；'
                      '卖价只有 XR 有，出处只有 GI 有；英文名按站主拍板不取。',
            'pageNote': '物品详情由两份客户端数据补齐：属性与出处主要按 beta 客户端解包与实测掉落'
                        '（GearInsight 无限版转述），卖价按社区整理稿（XR 全能助手转述）。'
                        '两份资料都没有的那一件，详情里就不显示这一段。',
            'sources': [
                {'key': 'gi', 'name': 'GearInsight 无限版 0.4.29', 'kind': 'beta 解包 + 实测掉落转述',
                 'date': '2026-10-03'},
                {'key': 'xr', 'name': 'XR 全能助手 0.37.1', 'kind': '社区整理稿转述', 'date': '2026-09-20'},
            ],
            'counts': {
                'total': len(out), 'st': n_st, 'stFromGi': n_st_gi, 'stFromXr': n_st_xr,
                'sell': n_sell, 'src': n_src,
                'conflicts': len(conflicts), 'conflictsListed': min(len(conflicts), CONFLICT_CAP),
                'orphans': len(orphans),
            },
            'conflicts': conflicts[:CONFLICT_CAP],
            'orphans': orphans[:100],
        },
        'items': out,
    }
    p = os.path.join(ROOT, 'items-detail.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('物品详情：%d 件（属性 %d：GI %d / XR %d · 卖价 %d · 出处 %d · 两源差异留档 %d · 名录外孤儿 %d）'
          % (len(out), n_st, n_st_gi, n_st_xr, n_sell, n_src, len(conflicts), len(orphans)))


if __name__ == '__main__':
    main()
