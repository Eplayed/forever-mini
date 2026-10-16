#!/usr/bin/env python3
# 把 XR 那份「配方去哪儿学」的快照并进 src/data/professions.json（阶段 PRD P0 第 9 条）。
#
# 只并两样：source.vendors（卖这张图纸的商人与区域）与 source.drops（图纸从谁身上掉、在哪个区域）。
# 站内原有的 `source`（"训练师" / null）不动——那是参考站给的来源类别，与"具体哪个商人"是两件事，
# 覆盖掉就等于把两个不同层次的说法揉成一个。新字段各带自己的出处标记 srcFrom。
#
# 顺序：merge-professions.js 之后跑本脚本（refresh.sh prof 那条链已排好）。
# 幂等：只加/改 vendors、formulaDrops、srcFrom 三个键，重跑字节一致。
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'src', 'data')
MAX_V = 6      # 一条配方最多列 6 个商人，多的记进 vMore
MAX_D = 4      # 图纸掉落 NPC 同理


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def main():
    prof = load('professions.json')
    xr = load(os.path.join('upstream', 'xr-prof.json'))
    rec = xr['recipes']
    n = {'recipes': 0, 'matched': 0, 'withVendors': 0, 'withDrops': 0, 'vTrimmed': 0,
         'dTrimmed': 0, 'xrOnly': 0}
    have = set()
    for p in prof['professions']:
        for r in (p.get('recipes') or []):
            n['recipes'] += 1
            key = str(r.get('itemId'))
            have.add(key)
            x = rec.get(key)
            if not x:
                continue
            n['matched'] += 1
            vs = x.get('vendors') or []
            ds = x.get('drops') or []
            if vs:
                n['withVendors'] += 1
                r['vendors'] = [{'name': v.get('name'), 'zone': v.get('zone')} for v in vs[:MAX_V]]
                if len(vs) > MAX_V:
                    r['vMore'] = len(vs) - MAX_V
                    n['vTrimmed'] += 1
            else:
                r.pop('vendors', None)
                r.pop('vMore', None)
            if ds:
                n['withDrops'] += 1
                r['formulaDrops'] = [{'npc': d.get('npc'), 'zone': d.get('zone')} for d in ds[:MAX_D]]
                if len(ds) > MAX_D:
                    r['dMore'] = len(ds) - MAX_D
                    n['dTrimmed'] += 1
            else:
                r.pop('formulaDrops', None)
                r.pop('dMore', None)
            if vs or ds:
                r['srcFrom'] = 'xr'
            else:
                r.pop('srcFrom', None)
    for k in rec:
        if k not in have:
            n['xrOnly'] += 1
    m = prof.setdefault('meta', {})
    m['sourceFrom'] = ('配方行的 vendors / formulaDrops 来自 XR_DungeonGuide 0.37.1 Data_Prof.lua'
                       '（tools/extract-xr-prof.py 抽取 → tools/merge-prof-sources.py 并入），'
                       '掉率百分比在抽取阶段就丢了；原有的 source（训练师/商人这类归法）仍来自参考站，两套并存')
    m['xrProf'] = dict(n, fetched=xr['meta']['fetched'], total=xr['meta']['counts']['total'],
                       rateDropped=xr['meta']['counts']['rateDropped'])
    out = os.path.join(DATA, 'professions.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(prof, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('配方 %d 条：并上商人 %d · 图纸掉落 %d（商人超 6 个截断 %d 条、掉落超 4 个截断 %d 条）；'
          'XR 有、站内没有的 %d 条'
          % (n['recipes'], n['withVendors'], n['withDrops'], n['vTrimmed'], n['dTrimmed'], n['xrOnly']))


if __name__ == '__main__':
    main()
