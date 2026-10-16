#!/usr/bin/env python3
# 把参考站采回来的 BiS 名单合并成站点成品 src/data/bis.json。
#
# 这份合并的原则：**名单只存"哪件装备在哪个部位、按什么顺序"，不存任何数值与句子。**
# 物品名、品质、装等、需要等级、属性行、图标、与经典旧世的对照状态——全部在运行时回
# items.json / items-detail.json 查（那是本站唯一数据基底，已经在 build-data 里卡过）。
# 理由有两条：① 同一件装备的数在两个地方各存一份必然会飘；② 参考站那些字段本来就是
# 从客户端解包转述的，我们库里已经有同一份，抄第二遍没有意义。
#
# 两源分歧照红线处理：它的物品名与我们的不一样时**两个都留**（nameAlt），页面标注。
# 部位交叉核对：它把某件装备列在哪个部位 vs 我们库里这件装备自己的 slot —— 对不上的
# 记进 meta.slotMismatch 并列出前几条，不静默丢（经典旧世的投掷/弹药确实进远程槽，属正常）。
#
# 幂等：不写时间戳到条目上（fetched 取快照 meta 里的日期），重跑产物 md5 不变。
# 用法：python3 tools/merge-bis.py [--dry]     # 与 merge-achievements.py 一样默认直接写
import argparse
import json
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, 'src', 'data', 'upstream', 'wclbox-bis.json')
OUT = os.path.join(ROOT, 'src', 'data', 'bis.json')
ITEMS = os.path.join(ROOT, 'src', 'data', 'items.json')

# 参考站的部位键 → 本站中文部位（2026-10-16 从 38 页实测枚举出来的 21 种）
SLOT_CN = OrderedDict([
    ('head', '头部'), ('neck', '项链'), ('shoulder', '肩部'), ('back', '背部'),
    ('chest', '胸部'), ('shirt', '衬衣'), ('robe', '衬裙'), ('wrist', '手腕'),
    ('hands', '手'), ('waist', '腰部'), ('legs', '腿部'), ('feet', '脚'),
    ('finger', '戒指'), ('trinket', '饰品'), ('main-hand', '主手'),
    ('off-hand', '副手'), ('two-hand', '双手'), ('shield', '盾牌'),
    ('held', '手持物品'), ('ranged', '远程'), ('relic', '圣物'),
])
# 部位核对时算"对得上"的等价关系（经典旧世的规则，不是我们发明的口径）。
# 键是**本站 items.json 的 slot 词表**，值是该部位允许出现在参考站的哪一节里。
# 参考站的中文部位名与我们的不是一套词（它叫"项链 / 戒指 / 双手武器"，我们叫"颈部 / 手指 / 双手"），
# 所以这里按"我们的 slot → 允许的参考站节"来判，而不是拿两边的中文名硬比。
SLOT_OK = {
    '头部': {'头部'}, '颈部': {'项链'}, '肩部': {'肩部'}, '背部': {'背部'},
    '胸部': {'胸部'}, '衬衣': {'衬衣', '衬衫'}, '手腕': {'手腕'}, '手': {'手'},
    '腰部': {'腰部'}, '腿部': {'腿部'}, '脚': {'脚'}, '手指': {'戒指'},
    '饰品': {'饰品'}, '主手': {'主手'}, '副手': {'副手', '副手：盾牌', '副手：手持物品'},
    '副手物品': {'副手', '副手：手持物品', '手持物品'}, '盾牌': {'副手：盾牌', '盾牌'},
    '双手': {'双手武器', '双手'}, '远程': {'远程'}, '投掷': {'远程'}, '弹药': {'远程'},
    # 我们库里单手武器记的 slot 是"单手"（不分主副手），参考站按它放的那只手列节，两边都算对
    '单手': {'主手', '副手', '副手：盾牌', '副手：手持物品'},
    '圣物': {'圣物'}, '战袍': {'战袍'}, '背包': {'背包'},
}


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def mode_of(h1, cls_cn):
    """'战士 PvE · 30 级最佳配装' → 'PvE'；'德鲁伊 野性战斗 PvP · …' → '野性战斗 PvP'"""
    s = (h1 or '').replace(cls_cn, '', 1).strip()
    i = s.find('·')
    return (s[:i] if i > 0 else s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true', help='只报数不写文件')
    args = ap.parse_args()
    snap = load(UP)
    items = load(ITEMS)
    base = {x['id']: x for x in items['items']}
    smeta = snap['meta']

    sets = []
    conflicts = []
    mism = []
    seen_ids = set()
    for s in snap['sets']:
        cls, spec, cls_cn = s['classSlug'], s['specSlug'], s['classCn']
        sid = cls + ('-' + spec if spec else '')
        if sid in seen_ids:
            sys.exit('套装 id 重复：' + sid)
        seen_ids.add(sid)
        doll, alts, ench, cons, refs = {}, {}, {}, {}, {}
        for fac in ('alliance', 'horde'):
            blk = s.get(fac)
            if not blk:
                continue
            cells = []
            cell_n = {}
            for c in blk['doll']:
                key = c['slot']
                cell_n[key] = cell_n.get(key, 0) + 1
                cells.append({'slot': key, 'cell': cell_n[key], 'item': c['item']})
                # 名字交叉核对：只在纸娃娃首选上做（备选同名，不必重复记）
                ours = base.get(c['item'], {}).get('name')
                if ours and c.get('name') and ours != c['name']:
                    conflicts.append({'item': c['item'], 'ours': ours, 'theirs': c['name'], 'set': sid})
            doll[fac] = cells
            a2 = {}
            e = []
            cn = []
            rf = {}
            for sl in blk['slots']:
                k = sl['slotKey']
                rows = [r['item'] for r in sl['rows'] if r.get('item')]
                if k == 'enchants':
                    for r in sl['rows']:
                        if r.get('item'):
                            e.append({'item': r['item'],
                                      'slots': [x for x in (r.get('slotOf') or '').replace('、', '，').split('，') if x],
                                      'skill': r.get('skill')})
                    continue
                if k == 'consumables':
                    cn = rows
                    continue
                a2[k] = rows
                # 来源：只收结构化的指向（配方专业 / 任务号 / 副本 / 物品），句子一条不留。
                # 为什么不用我们自己的 src：实测 175 件首选装备里 items-detail 有 src 的只有 16 件（9%），
                # 而这份名单里 67% 的行带着配方/任务/副本的结构化指向——来源那一列全靠它才填得满。
                for r in sl['rows']:
                    if r.get('item') and (r.get('refs') or r.get('skill')):
                        cur = rf.setdefault(str(r['item']), {'refs': [], 'skill': None})
                        if r.get('skill') and cur['skill'] is None:
                            cur['skill'] = r['skill']
                        for x in (r.get('refs') or []):
                            if x not in cur['refs']:
                                cur['refs'].append(x)
                # 它的这一节叫什么（中文原样） vs 我们库里这件装备自己的 slot
                their = (sl.get('slot') or SLOT_CN.get(k, k)).strip()
                for r in sl['rows']:
                    it = base.get(r.get('item')) or {}
                    got = it.get('slot')
                    if got and their not in SLOT_OK.get(got, set()):
                        mism.append({'set': sid, 'slot': their, 'item': r['item'],
                                     'name': it.get('name'), 'ourSlot': got})
            alts[fac] = a2
            ench[fac] = e
            cons[fac] = cn
            refs[fac] = rf
        sets.append(OrderedDict([
            ('id', sid), ('cls', cls), ('clsCn', cls_cn), ('spec', spec),
            ('mode', mode_of(s.get('h1'), cls_cn)), ('level', s.get('level')),
            ('url', s['url']), ('fetched', smeta['scrapedAt']),
            ('doll', doll), ('alts', alts), ('enchants', ench), ('consumables', cons),
            ('refs', refs)]))

    miss = sorted({r['item'] for st in sets for f in st['doll'] for c in st['doll'][f] if c['item'] not in base})
    if miss:
        sys.exit('名单里有 %d 个物品 ID 不在 items.json：前 10 个 %s —— 先补名录再合并' % (len(miss), miss[:10]))

    doc = OrderedDict([
        ('meta', OrderedDict([
            ('kind', 'bis'),
            ('title', '30 级配装名单'),
            ('level', 30),
            ('source', smeta['source']),
            ('scrapedAt', smeta['scrapedAt']),
            ('method', smeta['method']),
            ('notTaken', smeta['notTaken']),
            ('basis', '数值与名称一律回 items.json / items-detail.json 查，这份只存"哪件装备在哪个部位、按什么顺序"'),
            ('level_grading', 'L1'),
            ('gradingNote', '本站只有一家资料站列过这份名单，没法逐字回查"推荐对不对"，按 L1 留档；等游戏内实测或第二家资料再升档'),
            ('counts', OrderedDict([
                ('sets', len(sets)),
                ('classes', len(set(x['cls'] for x in sets))),
                ('items', len({c['item'] for st in sets for f in st['doll'] for c in st['doll'][f]})),
                ('altRows', sum(len(v) for st in sets for f in st['alts'] for v in st['alts'][f].values())),
                ('nameConflicts', len(conflicts)),
                ('slotMismatch', len(mism))])),
            ('slotCn', SLOT_CN),
        ])),
        ('sets', sets)])
    if conflicts:
        doc['meta']['nameConflictSample'] = conflicts[:12]
    if mism:
        doc['meta']['slotMismatchSample'] = mism[:12]

    print('套数 %d / 职业 %d / 名单里用到的物品 %d 件 / 备选行 %d 条' % (
        len(sets), doc['meta']['counts']['classes'], doc['meta']['counts']['items'],
        doc['meta']['counts']['altRows']))
    print('名字与本站不一致 %d 处 / 部位对不上 %d 处（投掷进远程这类是正常的，全量留在 meta 里）' % (
        len(conflicts), len(mism)))
    if conflicts:
        for x in conflicts[:6]:
            print('   名字分歧 #%s：本站「%s」/ 参考站「%s」(%s)' % (x['item'], x['ours'], x['theirs'], x['set']))
    if mism:
        for x in mism[:6]:
            print('   部位分歧：%s 列在「%s」，本站记的是「%s」（%s）' % (x['name'], x['slot'], x['ourSlot'], x['set']))
    blob = json.dumps(doc, ensure_ascii=False, indent=1)
    if args.dry:
        print('（--dry：没写文件）')
    else:
        with open(OUT, 'w', encoding='utf-8') as f:
            f.write(blob + '\n')
        print('写出 %s（%.0f KB）' % (OUT, len(blob.encode()) / 1024.0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
