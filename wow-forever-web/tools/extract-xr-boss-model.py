#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 XR_DungeonGuide/Data_BossModel.lua 抽「首领 → 客户端模型号」这一层，落 upstream 快照。

为什么要这一层：我们挂着 82 只没头像的首领。要去找图，得知道**去 CASC 里取哪张贴图**——
按中文名猜必然配错脸（我们的原则是宁可不配也不配错）。插件作者已经把
`副本 → 首领中文名 → {d=CreatureDisplayInfo, c=npcId}` 对齐好了（他自述是照 DF 的掉落集合
交集 + 中文名复核生成的），这就是那张"该取哪个"的索引。

**这一份只取标识符（displayId / npcId），不取作者写的任何说明文字。**

slug 不同名这件事：XR 用的是另一套英文 slug（the-deadmines / razorfen-downs / the-stockade /
excavation-site），我们不猜——**按首领中文名集合的交集判同一座本**，重合数与重合比例一起写进
快照的 alias 段，谁来看都能复核这条对应是不是成立。重合不到一半的（excavation-site 只有 2/4）
照样收，但标上低置信，导清单时只当"候选"用。

用法：python3 tools/extract-xr-boss-model.py [--src <插件根目录>]
产物：src/data/upstream/xr-boss-model.json
幂等：同输入字节一致（键排序、缩进固定）。
"""
import io
import json
import os
import re
import sys
from datetime import date

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 插件在仓库外（红线：插件本体不进 git）：Documents/project/.scratch/<这一批>
DEF_SRC = os.path.join(os.path.dirname(os.path.dirname(WEB)), '.scratch', 'wow-client-2026-10-21')
UP = os.path.join(WEB, 'src', 'data', 'upstream')

# XR 的 slug → 本站 slug。判据是首领中文名集合的交集（下面 alias 段会把重合数写出来），
# 不是"名字看着像"。改这张表必须同时改下面的判定，否则快照里会留下对不上的旧证据。
SLUG_ALIAS = {'the-deadmines': 'deathmine', 'razorfen-downs': 'razor-krendor',
              'the-stockade': 'the-stocks', 'excavation-site': 'whelgars-excavation'}


def toc_version(addon_dir, name):
    try:
        s = io.open(os.path.join(addon_dir, name + '.toc'), encoding='utf-8', errors='replace').read()
    except OSError:
        return '未知'
    m = re.search(r'^##\s*Version:\s*([0-9.]+)', s, re.M)
    return m.group(1) if m else '未知'


def parse(path):
    """逐行解析 ["slug"]={["首领名"]={d=NNN,c=NNN},…}。作者把这个表排成一副本一行，
    所以按行切比括号配对省事，也不会被注释里的花括号骗到。"""
    out = {}
    for ln in io.open(path, encoding='utf-8', errors='replace').read().split('\n'):
        g = re.match(r'\s*\["([^"]+)"\]=\{(.*)\}\s*,?\s*$', ln)
        if not g or g.group(1) == 'updated':
            continue
        for name, d, c in re.findall(r'\["([^"]+)"\]=\{d=(\d+|nil),c=(\d+|nil)\}', g.group(2)):
            out.setdefault(g.group(1), {})[name] = {
                'displayId': None if d == 'nil' else int(d),
                'npcId': None if c == 'nil' else int(c)}
    return out


def main():
    src = DEF_SRC
    if '--src' in sys.argv:
        src = sys.argv[sys.argv.index('--src') + 1]
    p = os.path.join(src, 'XR_DungeonGuide', 'Data_BossModel.lua')
    if not os.path.exists(p):
        sys.exit('找不到 %s' % p)
    raw = parse(p)
    ours = json.load(io.open(os.path.join(WEB, 'src', 'data', 'dungeons.json'), encoding='utf-8'))
    our_bosses = {x['id']: [b['nameCn'] for b in (x.get('bosses') or [])]
                  for x in (ours['newDungeons'] + ours['classicDungeons'] + ours['raids'])}

    bosses, alias, unmatched = {}, [], {}
    for slug, names in sorted(raw.items()):
        mine = SLUG_ALIAS.get(slug, slug)
        if slug in SLUG_ALIAS:
            inter = sorted(set(names) & set(our_bosses.get(mine, [])))
            # 置信度按"XR 那侧的名字有多大比例在我们这座本里"算，不看绝对数：
            # 4 只里对 2 只（excavation-site）只能算中等，不能因为"过半"就标 high——
            # 这一条将来要决定"敢不敢拿它去导贴图"，标高了就是拿猜测当事实。
            ratio = len(inter) / float(max(1, len(names)))
            alias.append({'xr': slug, 'ours': mine, 'xrBosses': len(names),
                          'ourBosses': len(our_bosses.get(mine, [])), 'nameMatch': len(inter),
                          'matchRatio': round(ratio, 2),
                          'confidence': 'high' if ratio >= 0.8 else ('mid' if ratio >= 0.5 else 'low')})
        if mine not in our_bosses:
            unmatched[slug] = sorted(names)
            continue
        for nm, v in sorted(names.items()):
            if nm not in our_bosses[mine]:
                unmatched.setdefault(slug + '·首领名', []).append(nm)
                continue
            bosses.setdefault(mine, {})[nm] = v

    doc = {'meta': {
        'source': 'XR_DungeonGuide/Data_BossModel.lua（作者自述：照 DungeonsForever 掉落集合交集 + 中文名复核生成）',
        'addon': 'XR_DungeonGuide', 'addonVersion': toc_version(os.path.join(src, 'XR_DungeonGuide'), 'XR_DungeonGuide'),
        'sourceFile': os.path.relpath(p, os.path.join(WEB, '..', '..')),
        'sourceStamp': {'bytes': os.path.getsize(p),
                        'sha256': __import__('hashlib').sha256(open(p, 'rb').read()).hexdigest(),
                        'fileDate': date.fromtimestamp(os.path.getmtime(p)).isoformat()},
        'extractedAt': date.today().isoformat(),
        'takes': '只有 displayId(CreatureDisplayInfo) 与 npcId 两个标识符；作者写的说明与注释一条不取',
        'use': '给"82 只没头像的首领"指出该去客户端取哪张模型贴图，避免按中文名猜脸',
        'counts': {'dungeons': len(bosses), 'bosses': sum(len(v) for v in bosses.values()),
                   'xrSlugs': len(raw), 'alias': len(alias), 'unmatched': sum(len(v) for v in unmatched.values())},
        'slugAlias': alias,
        'note': 'XR 用另一套英文 slug，四条别名是按首领中文名交集判的（重合数见 slugAlias），不是按名字猜。'},
        'bosses': {k: bosses[k] for k in sorted(bosses)},
        'unmatched': {k: sorted(v) for k, v in sorted(unmatched.items())}}
    os.makedirs(UP, exist_ok=True)
    out = os.path.join(UP, 'xr-boss-model.json')
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('首领模型号 → %s（%d 座本 / %d 只首领；别名 %d 条 %s；没对上的 %d 条）' % (
        os.path.relpath(out, WEB), doc['meta']['counts']['dungeons'], doc['meta']['counts']['bosses'],
        len(alias), ' '.join('%s→%s(%d/%d)' % (a['xr'], a['ours'], a['nameMatch'], a['xrBosses']) for a in alias),
        doc['meta']['counts']['unmatched']))


if __name__ == '__main__':
    main()
