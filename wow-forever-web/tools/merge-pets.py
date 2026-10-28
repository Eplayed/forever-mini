#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 upstream/gi-pets.json 整形成成品 app/data/pets.json（猎人宠物那一层）。

这份成品只有两层：**家族**与**宠物技能**，两边互相指得通（家族列它会的技能、技能列哪些族能用）。
它**不是**逐只可驯服宠物的名录——每一只在哪个区域、几级、要不要特殊条件，这份数据里没有，
所以页面标题就叫家族与技能，不叫"宠物大全"。（缺的那一层等游戏内实测或另一处能逐只列的来源。）

分级：一律 **L1**——名字与数值都来自第三方插件转述客户端，本站没逐行回客户端表核对，
也没进游戏验过。按红线不许因为"看起来合理"升 L0。

跑法：python3 tools/merge-pets.py
"""
import datetime
import io
import json
import os
import re
import sys

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(WEB, 'app', 'data', 'upstream', 'gi-pets.json')
OUT = os.path.join(WEB, 'app', 'data', 'pets.json')
ICON_DIR = os.path.join(WEB, 'app', 'img', 'icons')
DEV_RE = re.compile(r'\btest\b|测试|占位', re.I)


def load(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def main():
    if not os.path.exists(UP):
        sys.exit('先跑 tools/extract-gi-pets.py 生成 %s' % os.path.relpath(UP, WEB))
    up = load(UP)
    meta = up['meta']
    prov = [{
        'type': 'addon',
        'url': '%s PetData.lua' % meta['source'],
        'checkedAt': meta['fetchedAt'],
    }]
    fams = {f['id']: f for f in up['families']}
    skills = up['skills']
    by_en = {s['nameEn']: s for s in skills}

    fam_rows = []
    links = 0
    missing_skill = []
    for f in up['families']:
        mine = []
        for name in f['skillNamesEn']:
            s = by_en.get(name)
            if s is None:
                missing_skill.append('%s ← %s' % (f['nameEn'], name))
                continue
            links += 1
            mine.append({'id': s['id'], 'nameCn': s['nameCn'], 'nameEn': s['nameEn'],
                         'isNew': s['isNew']})
        key = f.get('iconKey')
        fam_rows.append({
            'id': 'petfam-%d' % f['id'],
            'famId': f['id'],
            'name': f['nameCn'],
            'nameEn': f['nameEn'],
            'iconKey': key if key and os.path.exists(os.path.join(ICON_DIR, key + '.jpg')) else None,
            'iconMissing': (not key) or not os.path.exists(os.path.join(ICON_DIR, (key or '') + '.jpg')),
            'dmgMod': f['dmgMod'], 'armorMod': f['armorMod'], 'hpMod': f['hpMod'],
            'isNew': f['isNew'],
            'skills': mine,
            'level': 'L1',
            'provenance': prov,
        })
    # 家族按"无限新增的排前面、再按中文名"，与稀有怪那一页同一套次序习惯
    fam_rows.sort(key=lambda r: (not r['isNew'], r['name']))

    sk_rows = []
    for s in skills:
        fams_ok = [fams[i]['nameCn'] for i in s['familyIds'] if i in fams]
        orphan = [i for i in s['familyIds'] if i not in fams]
        sk_rows.append({
            'id': 'petsk-%d' % s['id'],
            'spellId': s['id'],
            'name': s['nameCn'],
            'nameEn': s['nameEn'],
            'ranks': s['ranks'], 'cooldownSec': s['cooldownSec'], 'cost': s['cost'],
            'learnLevel': s['learnLevel'], 'maxLevel': s['maxLevel'],
            'isNew': s['isNew'], 'renamed': s['renamed'],
            'families': fams_ok,
            'familyMissingIds': orphan,
            'level': 'L1',
            'provenance': prov,
        })
    sk_rows.sort(key=lambda r: (not r['isNew'], r['name']))

    dev = [r['name'] for r in sk_rows if DEV_RE.search(r['name'] or '')]
    today = datetime.date.today().isoformat()
    out = {
        'meta': {
            'generatedAt': today,
            'checkedAt': meta['fetchedAt'],
            'kind': 'pets',
            'method': 'tools/extract-gi-pets.py 抽 upstream/gi-pets.json → 本脚本整形；'
                      '成句的技能描述（插件里的 dcn/den）一条没取',
            'pageNote': '宠物家族与它们的技能按无限测试版插件资料整理；'
                        '哪一只在哪个区域能抓到、要不要特殊条件，这份数据里没有，本站也没进游戏实测。',
            'sources': [{
                'key': 'gi', 'name': meta['source'],
                'kind': 'beta 客户端解包转述（插件自述取自客户端 DB2 '
                        + str(meta.get('selfReportedBuild')) + '，本站未逐行回查）',
                'url': 'GearInsight_Forever/PetData.lua', 'date': meta['fetchedAt'],
            }],
            'counts': {
                'families': len(fam_rows),
                'familiesNew': sum(1 for r in fam_rows if r['isNew']),
                'familiesIconless': sum(1 for r in fam_rows if r['iconMissing']),
                'skills': len(sk_rows),
                'skillsNew': sum(1 for r in sk_rows if r['isNew']),
                'links': links,
                'devNames': len(dev),
            },
        },
        'families': fam_rows,
        'skills': sk_rows,
    }
    if missing_skill:
        out['meta']['counts']['familySkillsUnresolved'] = len(missing_skill)
        out['meta']['unresolvedFamilySkills'] = missing_skill
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write('\n')
    c = out['meta']['counts']
    print('写 %s：家族 %d（新增 %d · 缺图 %d）· 技能 %d（新增 %d）· 家族↔技能连线 %d' %
          (os.path.relpath(OUT, WEB), c['families'], c['familiesNew'],
           c['familiesIconless'], c['skills'], c['skillsNew'], c['links']))
    if missing_skill:
        print('  家族写了技能名但这份技能表里没有：%s' % '、'.join(missing_skill))


if __name__ == '__main__':
    main()
