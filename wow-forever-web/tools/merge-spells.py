#!/usr/bin/env python3
# 法术书合并：参考站（定名与状态）+ 两份插件（id、每级学习等级）→ src/data/spells.json（M1-A）。
#
# 谁是主源、为什么（这条是数据分级问题，不能含糊）：
#   名字与"与经典旧世的关系"取参考站——它写的是从无限测试版客户端读出来的中文，
#   按 2026-10-08 站主定的档算 L0，并且必须能逐字回查（tools/audit-translations.py 走同一把尺）；
#   两份插件那边：GI 的中文混了作者/vmangos 口径、XR 来自 Wowhead 中文转译，
#   **都不给名字定档**，只用来回填 spellId 与每级学习等级这类数值。
#   插件描述字段（d/dz）在抽取阶段就没落盘，这里也拿不到。
#
# 两源分歧怎么办（2026-10-20 站主改口）：等级数（ranks）与起学等级（learnLevel）
# 参考站与插件对不上时，**主字段取插件**（GI 行数为先，其次 XR 的每级学习列表），
# 参考站那一说挪进 ranksAlt / learnAlt + *AltFrom 留档不删。
# 改这条的代价要认：数值侧从"参考站自报"变成"插件自报"，两边都不是我们进游戏测的，
# 所以这两类字段仍是 L0 名称 + 待实测数值，界面上不再摆"两个说法没对上"那句
# （站主 2026-10-20 决定：玩家看的页面只给一个数，分歧记录留在数据与溯源页）。
# 同名不同职业是常态（联盟/部落各有同名法术），所以**按 (职业, 名字) 而不是名字做键**。
#
# 幂等：排序固定、缩进固定，重跑字节一致。
import json
import os
import sys
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'data')
UP = os.path.join(ROOT, 'upstream')
CLASS_EN2ID = {'Warrior': 'warrior', 'Paladin': 'paladin', 'Hunter': 'hunter', 'Rogue': 'rogue',
               'Priest': 'priest', 'Shaman': 'shaman', 'Mage': 'mage', 'Warlock': 'warlock',
               'Druid': 'druid'}


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def main():
    wb = load(os.path.join(UP, 'wclbox-spells.json'))
    gi = load(os.path.join(UP, 'gi-spells.json'))
    xk = load(os.path.join(UP, 'xr-skills.json'))
    prov_wb = {'type': 'datamine_cn', 'url': wb['meta']['source'].split('（')[0],
               'checkedAt': wb['meta']['fetched']}
    # 版本号从快照自己的 meta 里读（插件升到 0.4.32 之后这里还写 0.4.29，等于给每条记录盖过期出处）
    prov_gi = {'type': 'addon', 'url': gi['meta']['source'].split(' 的')[0],
               'checkedAt': gi['meta']['fetched']}
    prov_xr = {'type': 'addon', 'url': xk['meta']['source'].split('（')[0],
               'checkedAt': xk['meta']['fetched']}

    # 插件索引：(职业, 名字) → 行；同名在同职业里重复出现的，整条不参与回填（宁缺不猜）
    gi_idx, xr_idx = {}, {}
    for en, rows in gi['classes'].items():
        cid = CLASS_EN2ID.get(en)
        for r in rows:
            k = (cid, r['name'])
            gi_idx.setdefault(k, []).append(r)
    for en, rows in xk['classes'].items():
        cid = CLASS_EN2ID.get(en)
        for r in rows:
            xr_idx.setdefault((cid, r['name']), []).append(r)

    seen_ids = set()
    spells, counts = [], {'ranksAlt': 0, 'learnAlt': 0, 'withId': 0, 'withLevels': 0,
                          'noPluginMatch': 0, 'noIcon': 0}
    for i, s in enumerate(wb['spells']):
        key = (s['classId'], s['name'])
        g = gi_idx.get(key)
        x = xr_idx.get(key)
        base_id = '%s-%s' % (s['classId'], s['name'])
        rid, n = base_id, 2
        while rid in seen_ids:
            rid = '%s#%d' % (base_id, n)
            n += 1
        seen_ids.add(rid)
        rec = {'id': rid, 'classId': s['classId'],
               'tab': s.get('tab'), 'name': s['name'], 'iconKey': s.get('iconKey'),
               'ranks': s.get('ranks'), 'learnLevel': s.get('learnLevel'),
               'state': s.get('state'), 'stateTag': s.get('stateTag'),
               'relation': s.get('relation'), 'level': 'L0'}
        if s.get('stateUnknown'):
            rec['stateUnknown'] = s['stateUnknown']
        if not rec['iconKey']:
            counts['noIcon'] += 1
        # spellId 只在同职业同名且**唯一**一条时才回填；两份都给且号不同就两个都留
        if g:
            # GI 按等级铺行：同一个名字的多条就是这一个法术的各级，按学习等级排好整条留下。
            # 这才是"共 N 级 / X 级起可学"的原始依据，比只回填一个 id 有用得多。
            ranks = sorted(({'spellId': r['spellId'], 'learnLevel': r.get('learnLevel')}
                            for r in g), key=lambda x: (x['learnLevel'] is None, x['learnLevel']))
            rec['spellRanks'] = ranks
            counts['withId'] += 1
            # 2026-10-20 站主改口：数值以插件为准。所以 GI 的行数**顶掉**参考站那个数，
            # 参考站那一说不删、挪进 ranksAlt 留档（build-data.js 仍卡"两说相同"这种假分歧）。
            gi_ranks = len(ranks)
            if gi_ranks and rec['ranks'] and rec['ranks'] != gi_ranks:
                rec['ranksAlt'] = rec['ranks']
                rec['ranksAltFrom'] = 'wclbox'
                rec['ranks'] = gi_ranks
                rec['ranksFrom'] = 'gi'
                counts['ranksAlt'] += 1
            elif gi_ranks and not rec['ranks']:
                rec['ranks'] = gi_ranks
                rec['ranksFrom'] = 'gi'
            flags = {('auto', str(r.get('auto')) == 'true') for r in g if r.get('auto') is not None}
            if len(flags) == 1:
                rec['auto'] = list(flags)[0][1]
            tg = {str(r.get('talentGated')) == 'true' for r in g if r.get('talentGated') is not None}
            if len(tg) == 1:
                rec['talentGated'] = bool(next(iter(tg)))
        if x and len(x) == 1:
            lv = x[0].get('learnLevels') or []
            if lv:
                rec['learnLevels'] = lv
                counts['withLevels'] += 1
                # 同上：XR 的每级学习列表顶掉参考站的"共 N 级 / X 级起可学"，旧值挪进 *Alt 留档。
                # GI 已经定过 ranks 就不再动（取值顺序 GI > XR，与物品详情那条一致）。
                xr_ranks = len(lv)
                if xr_ranks and 'ranksFrom' not in rec:
                    if rec['ranks'] and rec['ranks'] != xr_ranks:
                        rec['ranksAlt'] = rec['ranks']
                        rec['ranksAltFrom'] = 'wclbox'
                        rec['ranks'] = xr_ranks
                        rec['ranksFrom'] = 'xr'
                        counts['ranksAlt'] += 1
                    elif not rec['ranks']:
                        rec['ranks'] = xr_ranks
                        rec['ranksFrom'] = 'xr'
                lo = min(lv)
                if lo and 'learnFrom' not in rec:
                    if rec['learnLevel'] and rec['learnLevel'] != lo:
                        rec['learnAlt'] = rec['learnLevel']
                        rec['learnAltFrom'] = 'wclbox'
                        rec['learnLevel'] = lo
                        rec['learnFrom'] = 'xr'
                        counts['learnAlt'] += 1
                    elif not rec['learnLevel']:
                        rec['learnLevel'] = lo
                        rec['learnFrom'] = 'xr'
        if not g and not x:
            counts['noPluginMatch'] += 1
        # 每条挂自己那一页的真地址（抓取时已写进 upstream 的 url）。
        # 红线要求 L0 的每条都带能点开的 url + 日期，写 /fashu/<职业> 这种模板等于没给。
        prov_rec = dict(prov_wb)
        if s.get('url'):
            prov_rec['url'] = s['url']
        rec['provenance'] = [prov_rec]
        if g:
            rec['provenance'].append(prov_gi)
        if x:
            rec['provenance'].append(prov_xr)
        spells.append(rec)

    by_class = {}
    for r in spells:
        by_class[r['classId']] = by_class.get(r['classId'], 0) + 1
    doc = {
        'meta': {
            'generatedAt': date.today().isoformat(),
            'kind': 'spellbook',
            'method': 'tools/merge-spells.py 合三份 upstream：wclbox-spells.json（定名与状态，客户端解包转述）'
                      '+ gi-spells.json（spellId / 自动或天赋自带）+ xr-skills.json（每级学习等级）。'
                      '两份插件的描述字段在抽取阶段就没落盘；等级数与起学等级两边不一致时主字段取插件'
                      '（GI 先行、其次 XR），参考站那一说留在 ranksAlt / learnAlt + *AltFrom 不删。',
            'pageNote': '法术书按无限测试版客户端读出，与经典旧世逐条对照状态；'
                        '等级数与起学等级另按两份职业技能表交叉核对过，两边说法不一样的两条都留着。',
            'counts': {'total': len(spells), 'byClass': by_class,
                       'dupNameInClass': len(wb['spells']) - len({(x['classId'], x['name']) for x in wb['spells']}),
                       'byRelation': {k: sum(1 for r in spells if r.get('relation') == k)
                                      for k in ('talent', 'race', 'earlier', 'baseline', None)},
                       'byState': {k: sum(1 for r in spells if r['state'] == k)
                                   for k in ('same', 'changed', 'new', 'removed', 'renamed', None)},
                       **counts},
            'levelPolicy': '名字与状态来自客户端解包转述，按 2026-10-08 站主定的档算 L0；'
                           '插件来源（作者译名 / Wowhead 转译）不参与定名。',
            'sources': [
                {'key': 'wclbox', 'name': '无限数据库 · 法术书', 'kind': '当前 beta 客户端解包转述',
                 'url': prov_wb['url'], 'date': prov_wb['checkedAt'],
                 'build': wb['meta'].get('foreverBuild'), 'release': wb['meta'].get('release'),
                 # 九个真地址逐条列着：逐字回查（tools/audit-translations.py）按职业取那一页
                 'pages': (wb['meta'].get('pageUrls') or {})},
                {'key': 'gi', 'name': 'GearInsight 无限版 ' + (gi['meta'].get('addonVersion') or '版本未记'), 'kind': 'beta 解包转述（回填 id 与标记）',
                 'date': gi['meta']['fetched']},
                {'key': 'xr', 'name': 'XR 全能助手 ' + (xk['meta'].get('addonVersion') or '版本未记'), 'kind': '社区整理稿（回填每级学习等级）',
                 'date': xk['meta']['fetched']}],
        },
        'spells': spells,
    }
    p = os.path.join(ROOT, 'spells.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('法术书：%d 条 / %d 职业（带每级 id %d · 带每级学习等级 %d · 等级数两说 %d · 起学等级两说 %d · '
          '插件都没对上 %d · 缺图标 %d）'
          % (len(spells), len(by_class), counts['withId'], counts['withLevels'],
             counts['ranksAlt'], counts['learnAlt'], counts['noPluginMatch'], counts['noIcon']))
    print('来历分布：', json.dumps(doc['meta']['counts']['byRelation'], ensure_ascii=False))
    print('状态分布：', json.dumps(doc['meta']['counts']['byState'], ensure_ascii=False))


if __name__ == '__main__':
    main()
