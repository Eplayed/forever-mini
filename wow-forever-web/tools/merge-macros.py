#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""upstream/gi-macros.json → app/data/macros.json（2026-10-30 宏命令线）。

这一步只解决一件事：**宏体里的法术名从哪儿来**。
GI 给的是 `{{法术ID}}` 占位的模板，XR 给的是同一批宏烘好中文名的正文。
本站的做法是**先用我们自己的技能表把 ID 翻成名字**（app/data/spells.json 的 spellRanks
+ upstream/gi-spells.json），翻不出的那部分才退回插件烘好的正文，并且逐条记 `nameFrom`：

  own        —— 名字出自本站技能表（可回查）
  addon      —— 技能表里没有这个 ID，取插件烘好的那一名（整条宏留在"待回客户端核"名单里）

任一 ID 若在多处被反推出不同名字，直接失败退出——那说明两份没对齐，不能出半成品。
成品里不许残留 `{{`：有就非 0 退出。

用法：python3 tools/merge-macros.py
产物：app/data/macros.json
"""
import datetime
import io
import json
import os
import re
import sys

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(WEB, 'app', 'data', 'upstream', 'gi-macros.json')
SPELLS = os.path.join(WEB, 'app', 'data', 'spells.json')
GI_SPELLS = os.path.join(WEB, 'app', 'data', 'upstream', 'gi-spells.json')
OUT = os.path.join(WEB, 'app', 'data', 'macros.json')

PROV_KEY = 'gi'
CLS_CN = {'Warrior': '战士', 'Paladin': '圣骑士', 'Hunter': '猎人', 'Rogue': '潜行者',
          'Priest': '牧师', 'Shaman': '萨满祭司', 'Mage': '法师', 'Warlock': '术士', 'Druid': '德鲁伊'}


def own_name_map():
    """本站技能表能翻出的 spellId → 中文名。两条来源：成品 spells.json 的每阶 ID、
    upstream/gi-spells.json 的逐条 spellId（后者是前者的上游，覆盖更全）。"""
    m = {}
    sp = json.load(io.open(SPELLS, encoding='utf-8'))['spells']
    for s in sp:
        nm = s.get('name')
        if not nm:
            continue
        for r in (s.get('spellRanks') or []):
            if isinstance(r.get('spellId'), int):
                m.setdefault(r['spellId'], nm)
    gi = json.load(io.open(GI_SPELLS, encoding='utf-8'))['classes']
    for lst in gi.values():
        for s in lst:
            if isinstance(s.get('spellId'), int) and s.get('name'):
                m.setdefault(s['spellId'], s['name'])
    return m


def derive_from_baked(rows):
    """把 GI 模板与 XR 烘好的正文按位置对齐，反推出每个 {{id}} 在插件里被写成什么。
    同时当一次交叉核对：字面片段对不上的宏直接算对齐失败（说明两份不是一批）。"""
    derived = {}
    failed = []
    for r in rows:
        tpl = (r.get('bodyTemplate') or '').replace('\\n', '\n')
        baked = (r.get('bodyBakedByAddon') or '').replace('\\n', '\n')
        parts = re.split(r'\{\{(\d+)\}\}', tpl)
        pat = re.escape(parts[0])
        for i in range(1, len(parts), 2):
            pat += '(.*?)' + re.escape(parts[i + 1])
        m = re.match('^%s$' % pat, baked, re.S)
        if not m:
            failed.append(r.get('key'))
            continue
        for sid, name in zip(parts[1::2], m.groups()):
            sid = int(sid)
            if sid in derived and derived[sid] != name:
                sys.exit('法术 ID %d 在插件里被写成两个名字（%s / %s），两份没对齐，不出成品'
                         % (sid, derived[sid], name))
            derived[sid] = name
    if failed:
        sys.exit('%d 条宏的模板与烘好正文对不上（%s），不出成品' % (len(failed), failed[:5]))
    return derived


def main():
    up = json.load(io.open(UP, encoding='utf-8'))
    rows = up['macros']
    own = own_name_map()
    derived = derive_from_baked(rows)

    PROV = [{'key': 'gi', 'url': 'GearInsight_Forever/MacroData.lua', 'checkedAt': up['meta']['fetchedAt']}]
    macros, unverified_ids, rank_marker = [], set(), 0
    for r in rows:
        tpl = (r.get('bodyTemplate') or '').replace('\\n', '\n')
        ids = [int(x) for x in re.findall(r'\{\{(\d+)\}\}', tpl)]
        used, name_from = [], {}
        for sid in ids:
            nm = own.get(sid)
            if nm:
                src = 'own'
            else:
                nm = derived.get(sid)
                src = 'addon'
                unverified_ids.add(sid)
            used.append({'id': sid, 'name': nm, 'nameFrom': src})
            name_from[str(sid)] = src
        body = re.sub(r'\{\{(\d+)\}\}',
                      lambda m: next(u['name'] for u in used if u['id'] == int(m.group(1))), tpl)
        if '{{' in body:
            sys.exit('宏 %s 烘完还剩占位符没翻出来：%s' % (r.get('key'), body[:80]))
        has_rank = bool(re.search(r'\(Rank \d\)', body))
        if has_rank:
            rank_marker += 1
        macros.append({
            'id': r['key'],
            'classId': r['cls'].lower(),
            'className': CLS_CN[r['cls']],
            'group': r['group'],
            'groupEn': r.get('groupEn'),
            'title': r['title'],
            'titleEn': r.get('titleEn'),
            'note': r.get('note'),
            'noteEn': r.get('noteEn'),
            'minLevel': r.get('level'),          # 这一条要几级才用得了（0 = 没有等级门槛）
            'level': 'L1',                        # 数据分级：一家插件整理、本站未回客户端逐条核
            'provenance': PROV,
            'foreverNew': bool(r.get('foreverNew')),
            'body': body,
            'spellIds': sorted(set(used and [u['id'] for u in used] or [])),
            'nameFrom': name_from,
            'rankMarker': has_rank,
        })

    all_ids = sorted(set(i for m in macros for i in m['spellIds']))
    counts = {
        'macros': len(macros),
        'classes': len(set(m['classId'] for m in macros)),
        'groups': len(set(m['group'] for m in macros)),
        'foreverNew': sum(1 for m in macros if m['foreverNew']),
        'withMinLevel': sum(1 for m in macros if m.get('minLevel')),
        'spellIds': len(all_ids),
        'spellIdsOwnTable': len(all_ids) - len(unverified_ids),
        'spellIdsAddonOnly': len(unverified_ids),
        'macrosAllOwnNamed': sum(1 for m in macros if set() == {k for k, v in m['nameFrom'].items() if v != 'own'}),
        'rankMarker': rank_marker,
    }
    out = {
        'meta': {
            'generatedAt': datetime.date.today().isoformat(),
            'checkedAt': up['meta']['fetchedAt'],
            'kind': 'macros',
            'method': 'tools/extract-gi-macros.py 抽 upstream/gi-macros.json → 本脚本烘名。'
                      '宏体里的法术名先用本站技能表（spells.json 的每阶 ID + upstream/gi-spells.json）翻，'
                      '翻不出的 %d 个 ID 退回插件烘好的那一名并标 nameFrom=addon；'
                      '两份插件文件逐条对齐（同职业 / 同组 / 同中文标题）才允许这么退。'
                      % counts['spellIdsAddonOnly'],
            'pageNote': '宏命令与技能说明由第三方插件整理（其自报来源是 foreverdb.net 与 classicwowforever.com），'
                        '本站免费列出、不收费也不分发插件；每条宏都标了是谁整理的，'
                        '但本站没有逐条进游戏试过，等级与法术名以你客户端里能学到的为准。',
            'sources': [
                {'key': 'gi', 'name': 'GearInsight 无限版 0.5.6',
                 'kind': '第三方插件整理（其文件自报宏来源为 foreverdb.net，对过 Beta 1.60.1.70205）',
                 'url': 'GearInsight_Forever/MacroData.lua', 'date': up['meta']['fetchedAt']},
                {'key': 'xr', 'name': 'XR_DungeonGuide v87（作者 血染）',
                 'kind': '同一批宏的另一份形态（文件自述「同步 GI 2026-10-19 新版」，不是独立第二来源）',
                 'url': 'XR_DungeonGuide/Data_Macros.lua', 'date': up['meta']['fetchedAt']},
            ],
            'licenseNote': up['meta']['licenseNote'],
            'unverifiedSpellIds': sorted(unverified_ids),
            'counts': counts,
        },
        'groups': up['groups'],
        'macros': macros,
    }
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print('宏 %d 条 / %d 职业 / %d 组 / 《无限》新技能 %d 条' %
          (counts['macros'], counts['classes'], counts['groups'], counts['foreverNew']))
    print('法术 ID %d 个：本站技能表翻出 %d 个、只有插件有 %d 个（这些进"待回客户端核"名单）'
          % (counts['spellIds'], counts['spellIdsOwnTable'], counts['spellIdsAddonOnly']))
    print('整条宏的名字全部出自本站表的：%d 条；带 (Rank N) 等级标记的：%d 条'
          % (counts['macrosAllOwnNamed'], counts['rankMarker']))
    print('→', OUT)


if __name__ == '__main__':
    main()
