#!/usr/bin/env python3
# 掉落实测↔解包交叉比对（W2，站主 2026-10-14 拍板）。
# 实测侧：GearInsight_Forever Data.lua 的 loot 表（foreverchanges.pro Beta 实测掉落，build 69913）
# 解包侧：站内 src/data/dungeons.json（wclbox 解包转述，build 70338）
# 只比"哪些物品在"的事实集合，不比概率（两边都没有概率）。页面不动，差异清单落 docs。
# 用法：python3 tools/crosscheck-loot.py --dungeons hall-of-thanes ragefire-chasm
import argparse
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'src', 'data')
GI_LUA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'gi-forever', 'Data.lua')

# GI loot 表的副本名（nEn）→ 站点 slug；未列出的本跳过
NAME_TO_SLUG = {
    'Halls of Thane': 'hall-of-thanes',
    'Ragefire Chasm': 'ragefire-chasm',
    'The Deadmines': 'deathmine',
    'Wailing Caverns': 'wailing-caverns',
    'Shadowfang Keep': 'shadowfang-keep',
    'The Stockade': 'the-stocks',
    'Blackfathom Deeps': 'blackfathom-deeps',
    'Gnomeregan': 'gnomeregan',
    'Razorfen Kraul': 'razorfen-kraul',
    'Scarlet Monastery': 'scarlet-monastery-graveyard',
    'Uldaman': 'uldaman',
    'Maraudon': 'maraudon',
    'The Temple of Atal Hakkar': 'sunken-temple',
    'Blackrock Depths': 'blackrock-depths',
    'Lower Blackrock Spire': 'lower-blackrock-spire',
    'Upper Blackrock Spire': 'upper-blackrock-spire',
    'Stratholme': 'stratholme-main-gate',
    'Scholomance': 'scholomance',
    'Ruins of Lordaeron': 'ruins-of-lordaeron',
    'Dire Maul': 'dire-maul-east',
}


def brace_match(seg, start):
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
    raise ValueError('大括号不配对')


def gi_loot_sets(lua_path):
    src = open(lua_path, encoding='utf-8').read()
    a = re.search(r'(?m)^  loot = \{', src)
    b = re.search(r'(?m)^  rares = \{', src)
    if not a or not b:
        sys.exit('GI Data.lua 找不到 loot 表')
    seg = src[a.end() - 1:b.start()]
    out = {}
    # 副本条目里 lsr={...} 这类子对象挡正则，改用层级括号解析：
    # 逐个 {n=..., nEn=...} 候选拿整块，块里带 bosses={ 的才是副本级
    for dm in re.finditer(r'\{n="([^"]+)", nEn="([^"]+)"', seg):
        try:
            e = seg[dm.start():brace_match(seg, dm.start()) + 1]
        except ValueError:
            continue
        if 'bosses={' not in e:
            continue
        n_en = dm.group(2)
        slug = NAME_TO_SLUG.get(n_en)
        ids, bosses = set(), {}
        for bm in re.finditer(r'\{n="([^"]+)"[^{}]*?items=\{', e):
            i_start = e.index('items={', bm.start()) + len('items=') - 1
            i_end = brace_match(e, i_start)
            bid = set(re.findall(r'\{id=(\d+),', e[i_start + 6:i_end]))
            ids |= bid
            bosses[bm.group(1)] = bid
        if slug:
            out[slug] = {'nameEn': n_en, 'ids': ids, 'bosses': bosses}
    return out


def site_drop_sets(slug):
    dg = json.load(open(os.path.join(D, 'dungeons.json'), encoding='utf-8'))
    for d in (dg.get('classicDungeons') or []) + (dg.get('newDungeons') or []):
        if d['id'] == slug:
            ids, bosses = set(), {}
            for x in d.get('drops') or []:
                if not x.get('itemId'):
                    continue
                ids.add(str(x['itemId']))
                bosses.setdefault(x.get('bossCn') or '未知', set()).add(str(x['itemId']))
            return ids, bosses
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dungeons', nargs='+', default=['hall-of-thanes', 'ragefire-chasm'])
    ap.add_argument('--lua', default=os.path.normpath(GI_LUA))
    args = ap.parse_args()
    gi = gi_loot_sets(args.lua)
    lines = ['# 掉落实测↔解包交叉比对（%s）' % date.today().isoformat(), '',
             '实测侧：GearInsight_Forever loot 表（foreverchanges.pro Beta 实测掉落，build 1.60.1.69913）；'
             '解包侧：站内 dungeons.json（wclbox 解包转述，build 1.60.1.70338）。'
             '只比"哪些物品在"，不比概率。页面不动，本轮只修数据错漏。', '']
    for slug in args.dungeons:
        g = gi.get(slug)
        s, s_bosses = site_drop_sets(slug)
        if not g or s is None:
            lines.append('## %s：一侧缺数据（GI=%s，站内=%s），跳过' % (slug, bool(g), s is not None))
            continue
        common, only_g, only_s = g['ids'] & s, g['ids'] - s, s - g['ids']
        lines += [
            '## %s' % slug, '',
            '- GI 实测：%d 件（%d 个首领有掉落）' % (len(g['ids']), len(g['bosses'])),
            '- 站内解包：%d 件' % len(s),
            '- 两边都有：%d' % len(common),
            '- 仅实测有（站内解包缺，逐件核对候选）：%d' % len(only_g),
            '- 仅解包有（实测没打到/掉率低，不是错）：%d' % len(only_s), '',
        ]
        if only_g:
            lines.append('### 仅实测有（物品 ID）')
            lines.append(', '.join(sorted(only_g, key=int)))
            lines.append('')
        if only_s:
            lines.append('### 仅解包有（物品 ID）')
            lines.append(', '.join(sorted(only_s, key=int)))
            lines.append('')
        # 首领级口径差（注意：按中文名字符串比对，GI 中文名是 vmangos 口径、站内是客户端
        # 解包口径，译名差异会误报——2026-10-15 实抓复核两座时 4 个"缺失"里 3 个是译名差异；
        # 这行结论只当初筛，定性前必须抓 wclbox 副本页逐名复核）
        gb, sb = set(g['bosses']), set(s_bosses)
        if gb - sb:
            lines.append('GI 有掉落而站内首领名单没有的首领（初筛，译名差异可能误报，需实抓复核）：%s' % '、'.join(sorted(gb - sb)))
            lines.append('')
    p = os.path.join(ROOT, 'docs', 'ITEMS-LOOT-CROSSCHECK-2026-10-14.md')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('写 %s' % os.path.relpath(p))
    print('\n'.join(lines[:24]))


if __name__ == '__main__':
    main()
