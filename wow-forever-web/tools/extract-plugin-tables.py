#!/usr/bin/env python3
# 从两份无限服插件抽四张表的**事实字段**，落成 upstream 快照（阶段 PRD 的 M1-A/B/C 原料）。
#
# 抽哪四张（2026-16 实测条数）：
#   GI Data.lua  spells         九职业技能表（id / 每级学习等级 / 名 / 图标 / 是否自动 / 是否天赋自带）
#   GI Data.lua  achievements   成就 211 条（id / 中英文名 / 大类 / 子类 / 图标）
#   GI Data.lua  rares          稀有精英 338 条（npc id / 中英文名 / 区域 / 等级区间 / 坐标 / 掉落物 id 与名）
#   XR Data_Skills.lua          九职业法术书（名 / 图标 / 每级学习等级）
#
# 一律不落的字段（红线，不是风格问题）：
#   GI `spells` 与 `achievements` 的 `d` / `dEn`（tooltip 正文与成就描述是句子）；
#   XR 的 `dz`（作者自述"fc 漏翻的英文描述按内置模板词典翻译"——那是翻译，红线禁机翻）与 `lz`（同样可能来自模板）；
#   GI `rares` 里嵌套物品的 `st/stEn`（那是另一条线的数值文案，本条只要"谁掉什么"）。
#   名字这一层另有一道闸：GI 的中文混了作者/vmangos 口径、XR 是 Wowhead 中文转译，
#   **都不能当官方定名**，所以这里只落名字与出处声明，分级由合并层按能否回查逐条定（见 merge-spells.py）。
#
# 用法：python3 tools/extract-plugin-tables.py [--src <插件根目录>] [--out-dir <upstream 目录>]
#   默认 --src ~/Documents/project/.scratch/wow （仓库外，插件产物不进 git）
import json
import os
import re
import sys
from datetime import date

HOME = os.path.expanduser('~')
DEF_SRC = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow')
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASS_EN = ['Warrior', 'Paladin', 'Hunter', 'Rogue', 'Priest', 'Shaman', 'Mage', 'Warlock', 'Druid']
CLASS_CN = {'Warrior': '战士', 'Paladin': '圣骑士', 'Hunter': '猎人', 'Rogue': '潜行者',
            'Priest': '牧师', 'Shaman': '萨满祭司', 'Mage': '法师', 'Warlock': '术士', 'Druid': '德鲁伊'}


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def brace_match(s, i):
    """从 s[i]=='{' 起找到配平的右括号下标（跳过字符串里的括号）。
    照抄 extract-addon-items-detail.py 的做法——Lua 表不能用正则截断，会切进字符串。"""
    depth, n = 0, len(s)
    in_str = None
    while i < n:
        c = s[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in '"\'':
            in_str = c
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n - 1


def table_seg(src, name, nxt, indent=2):
    a = re.search(r'(?m)^ {%d}%s = \{' % (indent, name), src)
    if not a:
        sys.exit('找不到顶层表 %s（上游结构变了，别硬抽）' % name)
    b = re.search(r'(?m)^ {%d}%s = \{' % (indent, nxt), src) if nxt else None
    return src[a.end() - 1:b.start()] if b else src[a.end() - 1:]


def entry_fields(e):
    """一条 Lua 记录里的 k=v（字符串值与整数/布尔值），不碰嵌套表。"""
    out = {}
    for m in re.finditer(r'(?<![\w])([a-zA-Z]{1,6})\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^",}\s]+))', e):
        out[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    return out


def gi_spells(src):
    seg = table_seg(src, 'spells', 'questSeries')
    per, total = {}, 0
    for en in CLASS_EN:
        m = re.search(r'%s = \{' % en, seg)
        if not m:
            per[en] = []
            continue
        body = seg[m.end() - 1:brace_match(seg, m.end() - 1) + 1]
        rows = []
        for em in re.finditer(r'\{lv=', body):
            e = body[em.start():brace_match(body, em.start()) + 1]
            f = entry_fields(e)
            if not f.get('id') or not f.get('n'):
                continue
            rows.append({'spellId': int(f['id']), 'learnLevel': int(f.get('lv', 1)),
                         'name': f['n'], 'nameEn': f.get('nEn'),
                         'iconKey': f.get('i'), 'auto': f.get('auto'), 'talentGated': f.get('tal')})
        per[en] = rows
        total += len(rows)
    return per, total


def gi_achievements(src):
    seg = table_seg(src, 'achievements', 'keys')
    rows = []
    for m in re.finditer(r'\{id=', seg):
        e = seg[m.start():brace_match(seg, m.start()) + 1]
        f = entry_fields(e)
        if not f.get('id') or not f.get('t'):
            continue
        rows.append({'achId': int(f['id']), 'name': f['t'], 'nameEn': f.get('tEn'),
                     'top': f.get('top'), 'topEn': f.get('topEn'),
                     'cat': f.get('cat'), 'catEn': f.get('catEn'), 'iconKey': f.get('i'),
                     # lg 只有 0/1/16 三种值、含义没确认，先只留快照不进成品（含义要进游戏或回查源站才能定）
                     'lgRaw': int(f['lg']) if f.get('lg', '').isdigit() else None})
    return rows


def pts_count(e):
    pm = re.search(r'pts\s*=\s*\{', e)
    if not pm:
        return 0
    body = e[pm.end() - 1:brace_match(e, pm.end() - 1) + 1]
    return len(re.findall(r'\{\s*[\d.]+\s*,\s*[\d.]+\s*\}', body))


def gi_rares(src):
    seg = table_seg(src, 'rares', 'achievements')
    rows = []
    for m in re.finditer(r'\{npc=', seg):
        e = seg[m.start():brace_match(seg, m.start()) + 1]
        f = entry_fields(e)
        items = []
        im = re.search(r'items=\{', e)
        if im:
            body = e[im.end() - 1:brace_match(e, im.end() - 1) + 1]
            for em in re.finditer(r'\{id=', body):
                ent = body[em.start():brace_match(body, em.start()) + 1]
                g = entry_fields(ent)
                if g.get('id'):
                    # 只留"谁掉什么"这一层：st/stEn 是另一条线的数值文案，这里不抄
                    items.append({'itemId': int(g['id']), 'name': g.get('n'), 'nameEn': g.get('nEn')})
        lv = re.search(r'lv\s*=\s*\{\s*(\d+)\s*,\s*(\d+)', e)
        rows.append({'npcId': int(f['npc']) if f.get('npc', '').isdigit() else None,
                     'name': f.get('n'), 'nameEn': f.get('nEn'), 'rareKind': f.get('rare'),
                     'lvMin': int(lv.group(1)) if lv else None, 'lvMax': int(lv.group(2)) if lv else None,
                     'zone': f.get('z'), 'zoneEn': f.get('zEn'),
                     'x': float(f['x']) if f.get('x') else None,
                     'y': float(f['y']) if f.get('y') else None,
                     'spawnPoints': pts_count(e),
                     'respawnRaw': f.get('rs'), 'items': items})
    return rows


def xr_skills(src):
    per, total = {}, 0
    for en in CLASS_EN:
        m = re.search(r'\["%s"\] = \{' % en, src)
        if not m:
            per[en] = []
            continue
        body = src[m.end() - 1:brace_match(src, m.end() - 1) + 1]
        rows = []
        for sm in re.finditer(r'\{\s*zh\s*=', body):
            e = body[sm.start():brace_match(body, sm.start()) + 1]
            f = entry_fields(e)
            lv = re.search(r'lv\s*=\s*\{([^}]*)\}', e)
            levels = [int(x) for x in re.findall(r'\d+', lv.group(1))] if lv else []
            if not f.get('zh'):
                continue
            rows.append({'name': f['zh'], 'iconKey': f.get('icon'), 'learnLevels': levels})
        per[en] = rows
        total += len(rows)
    return per, total


def dump(path, doc):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')


def main():
    src_dir = arg('--src', DEF_SRC)
    out_dir = arg('--out-dir', os.path.join(WEB, 'src', 'data', 'upstream'))
    os.makedirs(out_dir, exist_ok=True)
    gi_p = os.path.join(src_dir, 'GearInsight_Forever', 'Data.lua')
    xr_p = os.path.join(src_dir, 'XR_DungeonGuide', 'Data_Skills.lua')
    for p in (gi_p, xr_p):
        if not os.path.exists(p):
            sys.exit('原件不在：%s（先按 §六 Q2 把插件拷过来）' % p)
    gi = open(gi_p, encoding='utf-8').read()
    xr = open(xr_p, encoding='utf-8').read()
    today = date.today().isoformat()

    sp_per, sp_total = gi_spells(gi)
    ac = gi_achievements(gi)
    ra = gi_rares(gi)
    xk_per, xk_total = xr_skills(xr)

    dump(os.path.join(out_dir, 'gi-spells.json'), {
        'meta': {
            'source': 'GearInsight_Forever 0.4.29 Data.lua 的 spells 表（源：Forever beta client 1.60.1.69876，2026-10-03）',
            'originFile': gi_p, 'fetched': today,
            'counts': {'total': sp_total, 'byClass': {k: len(v) for k, v in sp_per.items()}},
            'droppedFields': ['d（tooltip 描述正文，红线）'],
            'note': '中文名混有作者/vmangos 口径，**不能当官方定名**，合并层只用来对 id 与每级学习等级。'},
        'classes': sp_per})
    dump(os.path.join(out_dir, 'gi-achievements.json'), {
        'meta': {
            'source': 'GearInsight_Forever 0.4.29 Data.lua 的 achievements 表',
            'originFile': gi_p, 'fetched': today, 'counts': {'total': len(ac)},
            'droppedFields': ['d（成就描述句子，红线）', 'dEn（英文描述）'],
            'note': 'lg 字段取值只有 0/1/16、含义未确认，留在快照里不进成品。'},
        'achievements': ac})
    dump(os.path.join(out_dir, 'gi-rares.json'), {
        'meta': {
            'source': 'GearInsight_Forever 0.4.29 Data.lua 的 rares 表',
            'originFile': gi_p, 'fetched': today,
            'counts': {'total': len(ra), 'withItems': sum(1 for x in ra if x['items']),
                       'withCoords': sum(1 for x in ra if x['x'] is not None)}},
        'rares': ra})
    dump(os.path.join(out_dir, 'xr-skills.json'), {
        'meta': {
            'source': 'XR_DungeonGuide 0.37.1 Data_Skills.lua（源：权威资料库/zh-cn/spellbook 页内嵌 JSON，2026-10-02 抓）',
            'originFile': xr_p, 'fetched': today,
            'counts': {'total': xk_total, 'byClass': {k: len(v) for k, v in xk_per.items()}},
            'droppedFields': ['dz（作者自述部分为模板词典翻译，红线禁机翻）', 'lz（同段 tooltip 文案）'],
            'note': '只留名字、图标与每级学习等级；名字按 Wowhead 中文转译对待，不当定名。'},
        'classes': xk_per})

    print('GI spells %d（九职业：%s）' % (sp_total, ' '.join('%s=%d' % (k[:3], len(v)) for k, v in sp_per.items())))
    print('GI achievements %d（大类 %d 种）' % (len(ac), len({x['top'] for x in ac if x['top']})))
    print('GI rares %d（带掉落 %d · 带坐标 %d）' % (
        len(ra), sum(1 for x in ra if x['items']), sum(1 for x in ra if x['x'] is not None)))
    print('XR skills %d' % xk_total)
    print('写四份快照到 %s' % out_dir)


if __name__ == '__main__':
    main()
