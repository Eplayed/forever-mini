#!/usr/bin/env python3
# 把 XR 那份「配方去哪儿学」的快照并进 app/data/professions.json（阶段 PRD P0 第 9 条）。
#
# 只并两样：source.vendors（卖这张图纸的商人与区域）与 source.drops（图纸从谁身上掉、在哪个区域）。
# 站内原有的 `source`（"训练师" / null）不动——那是参考站给的来源类别，与"具体哪个商人"是两件事，
# 覆盖掉就等于把两个不同层次的说法揉成一个。新字段各带自己的出处标记 srcFrom。
#
# merge-professions.js 用 --stdin 合并已归档的快照，然后才替换成品。
# 幂等：只加/改 vendors、formulaDrops、srcFrom 三个键，重跑字节一致。
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "app", "data")
MAX_V = 6      # 一条配方最多列 6 个商人，多的记进 vMore
MAX_D = 4      # 图纸掉落 NPC 同理


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def main():
    stream = sys.argv[1:] == ['--stdin']
    prof = json.load(sys.stdin) if stream else load('professions.json')
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
    m['sourceFrom'] = '商人和图纸掉落来自已归档的 ' + xr['meta']['source'] + '，核对日期 ' + xr['meta']['fetched']
    m['xrProf'] = dict(n, fetched=xr['meta']['fetched'], total=xr['meta']['counts']['total'],
                       rateDropped=xr['meta']['counts']['rateDropped'])
    if stream:
        json.dump(prof, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write('\n')
        return
    out = os.path.join(DATA, 'professions.json')
    with open(out + '.tmp', 'w', encoding='utf-8', newline='\n') as f:
        json.dump(prof, f, ensure_ascii=False, indent=1)
        f.write('\n')
    os.replace(out + '.tmp', out)
    print('配方 %d 条：并上商人 %d · 图纸掉落 %d（商人超 6 个截断 %d 条、掉落超 4 个截断 %d 条）；'
          'XR 有、站内没有的 %d 条'
          % (n['recipes'], n['withVendors'], n['withDrops'], n['vTrimmed'], n['dTrimmed'], n['xrOnly']))


if __name__ == '__main__':
    main()
