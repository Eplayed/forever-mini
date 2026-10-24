#!/usr/bin/env python3
# 从 XR_DungeonGuide/Data_Prof.lua 抽配方的「来源商人 / 学习门槛」两类事实字段（阶段 PRD P0 第 9 条）。
#
# 为什么只抽这两类：站内 professions.json 每条配方已有 materials 与四档技能阈值，缺的正是
# 「去哪儿学 / 学会要什么门槛」。XR 那份配方行里恰好有：
#   行第 5 位 learn = 需要角色等级（"5 级"这种），source.skill = 需要技能点，
#   source.vendors = {{name, zone, cost, id}}（商人专名与区域，游戏内专名，无 ID 才保留原文），
#   source.drops   = {{npc, zone, chance, lv}}（谁掉这张图纸）。
#
# 一律不落的字段（红线，不是风格问题）：
#   **chance**——那是掉率百分比，红线写着"掉落不写百分比"，抽取阶段就丢，不给界面任何机会；
#   插件作者写的简介 / 提示 / 练法路线（文件头自己声明「⛔ 人写的简介不在收录范围」，我们照这条办）；
#   附魔行的「效果」文本（是句子）。
#
# 用法：python3 tools/extract-xr-prof.py [--src <插件根目录>] [--out-dir <upstream 目录>]
import json
import os
import re
import sys
from datetime import date

HOME = os.path.expanduser('~')
DEF_SRC = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow')
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def brace_match(s, i):
    """从 s[i]=='{' 起找配平的右括号下标（跳过字符串里的括号）。Lua 表不能用正则截断。"""
    depth, n = 0, len(s)
    j, in_str = i, None
    while j < n:
        c = s[j]
        if in_str:
            if c == '\\':
                j += 2
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
                return j
        j += 1
    return -1


def split_top(body):
    """把一个表体（不含外层花括号）按顶层逗号切成字段列表。"""
    out, depth, cur, in_str = [], 0, [], None
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if in_str:
            cur.append(c)
            if c == '\\':
                cur.append(body[i + 1])
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in '"\'':
            in_str = c
            cur.append(c)
        elif c in '{[':
            depth += 1
            cur.append(c)
        elif c in '}]':
            depth -= 1
            cur.append(c)
        elif c == ',' and depth == 0:
            out.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    if ''.join(cur).strip():
        out.append(''.join(cur).strip())
    return out


def lua_str(v):
    v = v.strip()
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    return None


def num(v):
    v = v.strip()
    m = re.match(r'^-?\d+$', v)
    return int(m.group(0)) if m else None


def parse_source(seg):
    """source={skill=30,read="db",drops={...},vendors={...}} → 只留事实字段。"""
    out = {'skill': None, 'vendors': [], 'drops': []}
    m = re.search(r'skill\s*=\s*(\d+)', seg)
    if m:
        out['skill'] = int(m.group(1))
    for key in ('vendors', 'drops'):
        for m in re.finditer(key + r'\s*=\s*\{', seg):
            st = seg.index('{', m.start() + len(key))
            en = brace_match(seg, st)
            if en < 0:
                continue
            body = seg[st + 1:en]
            for ent in split_top(body):
                if not ent.startswith('{'):
                    continue
                e2 = brace_match(ent, 0)
                inner = ent[1:e2]
                fields = {}
                for f in split_top(inner):
                    k, _, v = f.partition('=')
                    fields[k.strip()] = v
                if key == 'vendors':
                    nm, z = lua_str(fields.get('name', '')), lua_str(fields.get('zone', ''))
                    if not nm:
                        continue
                    out['vendors'].append({'name': nm, 'zone': z,
                                           'cost': num(fields.get('cost') or '') or None,
                                           'itemId': num(fields.get('id') or '')})
                else:
                    # 掉率 chance 在这里被丢掉：只留"谁掉、在哪、几级"
                    nm, z = lua_str(fields.get('npc', '')), lua_str(fields.get('zone', ''))
                    if not nm:
                        continue
                    lv = fields.get('lv')
                    rng = None
                    if lv and lv.strip().startswith('{'):
                        parts = [num(x) for x in split_top(lv.strip()[1:-1])]
                        parts = [p for p in parts if p is not None]
                        rng = parts[:2] or None
                    out['drops'].append({'npc': nm, 'zone': z, 'levels': rng})
            break
    return out


def main():
    src = arg('--src', DEF_SRC)
    out_dir = arg('--out-dir', os.path.join(WEB, "app", "data", 'upstream'))
    path = os.path.join(src, 'XR_DungeonGuide', 'Data_Prof.lua')
    if not os.path.exists(path):
        sys.exit('找不到 %s（插件原件在仓库外，先按 Q2 拷到 .scratch/wow）' % path)
    s = open(path, encoding='utf-8').read()
    recipes = {}
    stats = {'rows': 0, 'srcHasLearn': 0, 'srcHasSkill': 0, 'vendors': 0, 'drops': 0,
             'rateDropped': 0, 'dupItem': 0}
    # 每个专业一段：["alchemy"]={...rows={{...},{...}}...}
    for m in re.finditer(r'\["([a-z]+)"\]\s*=\s*\{', s):
        slug = m.group(1)
        st = s.index('{', m.start() + len('["%s"]' % slug))
        en = brace_match(s, st)
        seg = s[st:en + 1]
        rm = re.search(r'rows\s*=\s*\{', seg)
        if not rm:
            continue
        rs = seg.index('{', rm.start() + len('rows'))
        re_end = brace_match(seg, rs)
        body = seg[rs + 1:re_end]
        for ent in split_top(body):
            if not ent.startswith('{'):
                continue
            e2 = brace_match(ent, 0)
            fields = split_top(ent[1:e2])
            if len(fields) < 13:
                continue
            spell, item = num(fields[0]), num(fields[1])
            if item is None:
                continue
            stats['rows'] += 1
            learn = lua_str(fields[4]) or ''
            src_seg = fields[12] if fields[12].startswith('{') else ''
            got = parse_source(src_seg) if src_seg else {'skill': None, 'vendors': [], 'drops': []}
            stats['rateDropped'] += len(re.findall(r'chance\s*=', src_seg or ''))
            # learn（行第 5 位）与 source.skill 这两个数**不写进每条**：
            # 实测同一个位置有时等于站内 skill.orange、有时不等（247755 是 10 对 1，250344 是 15 对 15），
            # 而 source.skill（10011 给 185，站内橙点是 200）到底是"学会要的技能点"还是别的，
            # 源文件没写、我们也没进游戏核过。**含义没定的数不上页面**（红线：不猜），
            # 只在 meta.counts 里记"源里有、这一版没取"，开放项 26 等实测。
            rec = {'spellId': spell, 'prof': slug,
                   'vendors': got['vendors'], 'drops': got['drops']}
            if item in recipes:
                stats['dupItem'] += 1
            recipes[str(item)] = rec
            stats['srcHasLearn'] += 1 if learn else 0
            stats['srcHasSkill'] += 1 if got['skill'] is not None else 0
            stats['vendors'] += 1 if rec['vendors'] else 0
            stats['drops'] += 1 if rec['drops'] else 0
    doc = {
        'meta': {
            'source': 'XR_DungeonGuide 0.37.1 Data_Prof.lua（自述数据源：无限服权威配方 2026-10-10）',
            'fetched': date.today().isoformat(),
            'counts': dict(stats, total=len(recipes)),
            'droppedFields': ['source.drops[].chance（掉率百分比，红线：掉落不写百分比）',
                              '行第 5 位的 learn 与 source.skill（两个数的含义没定：同一个位置有时等于站内橙点、有时不等，源文件没写清，也没进游戏核过 → 开放项 26）',
                              '插件作者写的简介 / 提示 / 练法路线',
                              '附魔行的效果文本（句子）',
                              'reagents 与 formula（材料这条线站内已有，不重复取）'],
            'note': '只取"去哪儿学、学会要什么门槛、图纸从谁身上掉"这三类事实字段。'
                    '商人与 NPC 是游戏内专名，原样保留；区域名用插件给的中文，站内另有定名档，'
                    '合并层按站内区域名为准、不一致只记冲突。',
        },
        'recipes': recipes,
    }
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    p = os.path.join(out_dir, 'xr-prof.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, sort_keys=True, indent=1)
        f.write('\n')
    print('XR 配方来源行 %d 条 → %s：有商人 %d · 有图纸掉落 %d · 掉率字段丢掉 %d 处；'
          '源里另有 learn %d / skill %d 两处含义没定，这一版没取'
          % (stats['rows'], p, stats['vendors'], stats['drops'], stats['rateDropped'],
             stats['srcHasLearn'], stats['srcHasSkill']))


if __name__ == '__main__':
    main()
