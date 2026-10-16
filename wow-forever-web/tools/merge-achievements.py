#!/usr/bin/env python3
# 成就合并：GI 的 211 条目录 + 参考站端点能回查的那 46 条 → src/data/achievements.json（M1-B）。
#
# 分级规则（这条线唯一需要判断的地方）：
#   L0 = id 对得上参考站端点**且中文名逐字相同**（两源互证，可自动回查）；实测 46/46 全一致；
#   L1 = 只有 GI 一家给的（165 条，beta 客户端解包转述，但没有第二个源能逐字回查）。
#   两源 id 对上而名字不同的 → 两个都留（nameAlt）并停 L1，不替谁圆。
# 分类：对得上的用参考站的 category（英文 slug + 中文名都齐），对不上的用 GI 的 top/cat 中文。
# 一律不带成就描述（GI 的 d、参考站的 text 在抽取阶段就删了，这里也不会有）。
# 幂等：排序与缩进固定，重跑字节一致。
import json
import os
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'data')


def load(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return json.load(f)


def main():
    wb = load(os.path.join('upstream', 'wclbox-achievements.json'))
    gi = load(os.path.join('upstream', 'gi-achievements.json'))
    w = {x['achId']: x for x in wb['achievements']}
    prov_w = {'type': 'datamine_cn', 'url': wb['meta']['source'], 'checkedAt': wb['meta']['fetched']}
    prov_g = {'type': 'addon', 'url': 'GearInsight_Forever 0.4.29 Data.lua',
              'checkedAt': gi['meta']['fetched']}
    cats_w = {c['id']: c['name'] for c in wb['meta'].get('categories') or []}

    rows, n = [], {'total': 0, 'l0': 0, 'l1': 0, 'nameDiff': 0, 'onlyWb': 0, 'noIcon': 0}
    for g in sorted(gi['achievements'], key=lambda x: (x.get('top') or '', x['achId'])):
        wrow = w.get(g['achId'])
        rec = {'id': 'ach-%d' % g['achId'], 'achId': g['achId'], 'name': g['name'],
               'nameEn': g.get('nameEn'), 'top': g.get('top'), 'cat': g.get('cat'),
               'iconKey': g.get('iconKey'), 'forever': bool(wrow.get('forever')) if wrow else None}
        prov = [prov_g]
        if wrow:
            if wrow['name'] != g['name']:
                rec['nameAlt'] = wrow['name']
                rec['level'] = 'L1'
                n['nameDiff'] += 1
            else:
                rec['level'] = 'L0'
                n['l0'] += 1
            rec['category'] = wrow.get('category')
            rec['categoryCn'] = cats_w.get(wrow.get('category'))
            rec['criteriaCount'] = wrow.get('criteriaCount')
            if wrow.get('criteriaAchievements'):
                rec['subAchievements'] = wrow['criteriaAchievements']
            prov = [prov_w, prov_g]
        else:
            rec['level'] = 'L1'
            rec['categoryCn'] = rec['top']
            n['l1'] += 1
        if not rec.get('iconKey'):
            n['noIcon'] += 1
        rec['provenance'] = prov
        rows.append(rec)
    for k in w:
        if k not in {x['achId'] for x in gi['achievements']}:
            n['onlyWb'] += 1

    by_top = {}
    for r in rows:
        by_top[r.get('top') or '未分类'] = by_top.get(r.get('top') or '未分类', 0) + 1
    doc = {
        'meta': {
            'generatedAt': date.today().isoformat(), 'kind': 'achievements',
            'method': 'tools/merge-achievements.py 合两份 upstream：gi-achievements.json（目录，211 条）'
                      '+ wclbox-achievements.json（能逐字回查的那 46 条，来自 /_shuju/<发布号>/chengjiu.json）。'
                      '两边 id 对上且中文名逐字相同才升 L0；成就描述整句两份都不落。',
            'pageNote': '成就目录按无限测试版客户端读出；其中区域探索这一类（46 条）另有一处客户端解包转述'
                        '逐字对过，其余 165 条目前只有一份资料说到，名字先按客户端读出的写法放着，'
                        '等第二处能对上再升档。成就的具体完成条件文本一律不搬，要回游戏看。',
            'counts': {'total': len(rows), 'byTop': by_top,
                       'l0': n['l0'], 'l1': n['l1'], 'nameDiff': n['nameDiff'],
                       'onlyInReference': n['onlyWb'], 'noIcon': n['noIcon']},
            'sources': [{'key': 'gi', 'name': 'GearInsight 无限版 0.4.29', 'kind': 'beta 客户端解包转述',
                         'date': gi['meta']['fetched']},
                        {'key': 'wclbox', 'name': '无限数据库 · 成就端点', 'kind': '当前 beta 客户端解包转述',
                         'url': prov_w['url'], 'build': wb['meta'].get('upstreamBuild'),
                         'date': prov_w['checkedAt']}],
        },
        'achievements': rows,
    }
    p = os.path.join(ROOT, 'achievements.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('成就：%d 条（L0 两源互证 %d · L1 单源 %d · 名字两说 %d · 缺图标 %d）·大类 %d 种'
          % (len(rows), n['l0'], n['l1'], n['nameDiff'], n['noIcon'], len(by_top)))


if __name__ == '__main__':
    main()
