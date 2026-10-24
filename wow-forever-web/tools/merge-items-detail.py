#!/usr/bin/env python3
# 合并三份 upstream 快照 → app/data/items-detail.json（物品线二批：W2-3 全量抓取后重排层级）。
#
# 优先级（**站主 2026-10-16 拍板「取值也以插件为准」，层级反转**；
#   10-15 那次定的"wclbox 当前 build 优先"同日作废，两条决定都记在 ROLES.md 与 PRD §四）：
#   属性 st：GI loot（Beta 实测转述，build 1.60.1.69913）
#            > XR（社区整理稿，2026-09-20）
#            > wclbox（当前 beta 客户端解包转述，1.60.1.70374）—— 退为兜底
#   卖价 sell：XR > wclbox
#   代价已实测写清（不是猜的）：11,250 件会显示插件那套值，其中 2,487 件与当前 build 的数值真的不同
#   （例：硬根法杖 插件 36-54/每秒 13.6/+9 精神+20 法术强度 vs 当前解包 44-67/每秒 16.8/+8 精神）；
#   **覆盖率不受影响**——只有 wclbox 有属性的 5,973 件（含无限新增 1,374 件）仍由 wclbox 兜住。
#   两说的原始数值都留在 upstream 三份快照里，随时可反向重跑。
#   出处 src/srcName：只有 GI 有（"本 · 首领"口径），维持不变；
#   教益句 use（"教你学会制作X"这一句）：单独一段，按 GI > XR 补（参考站把它当风味句摆，
#   本轮快照没带这层，抓取脚本已改为下一轮重抓时自己带上（详见 split_st 的注释）；
#   wclbox 的"来源：NPC/容器 + 区域"这层**不落成品**——它是掉落归属的另一套口径，
#   红线要等实测，先只留在 upstream 快照里，进页面得单独拍板。
# 差异分两类留档，别混成一个数：
#   realConflicts  归一化后仍不同（真数值/真词条差异，是"版本间改动"的证据）
#   formatOnly     归一化后相同（只是写法不同：空格、括号、"点伤害/伤害"）
# 只收 items.json 里存在的 id；名录外孤儿计数进 meta.orphans。
# 幂等：键按数字序、缩进固定，重跑字节一致。
import json
import os
import re
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'data')
CONFLICT_CAP = 300


def load(name):
    p = os.path.join(ROOT, 'upstream', name)
    if not os.path.exists(p):
        return {}
    with open(p, encoding='utf-8') as f:
        return json.load(f)


USE_RE = re.compile(r'教你|学会|可启动')
# 使用条件行（形如 需要附魔 (200)）。2026-10-20 A02 定的口径：
# 「未提供要求」不等于「无等级要求」，所以这一类行不许被高优先级源静默清掉。
REQ_RE = re.compile(r'^\s*需要')
# 使用效果行（使用：…）。和需要行同理：高优先级源没写这句，不代表这件没有这个功能。
USE_EFF_RE = re.compile(r'^\s*使用[：:]')


def is_quoted(t):
    return (t.startswith('“') and t.endswith('”')) or (t.startswith('"') and t.endswith('"'))


def carry_missing(rec, sources):
    """高优先级源整条没写「需要X (N)」或「使用：…」时，从别的源把那一条带回来。

    2026-10-20 A02 的口径：上游换写法（XR 66 把教学句不加引号塞进 st）不能算成
    「官方说这件没有要求」——那是解析口径，不是数据授权。所以补回来的同时单独记
    它是谁给的（stExtraFrom），一段一个来源，界面上才说得清这句是谁给的。
    sources 按优先级给 [(名字, 行列表), …]，与 rec['stFrom'] 同源的那份跳过。
    返回补进来的源名列表（可能为空）。

    为什么从合并主流程里抽出来单独成函数：抽之前那两条夹具回归是在自测代码里
    把同样的表达式现写一遍再判自己，生产逻辑怎么改它都照样绿——那是假绿。
    现在自测调的就是这里，改坏了会红。"""
    extra_from = []
    for kind_re in (REQ_RE, USE_EFF_RE):
        if any(kind_re.search(x) for x in rec.get('st') or []):
            continue        # 这一类行高优先级源自己给了，不动
        for other_name, other in sources:
            if other_name == rec.get('stFrom') or not other:
                continue
            picked = [x for x in other if kind_re.search(x)]
            if picked:
                rec['st'] = (rec.get('st') or []) + picked
                if other_name not in extra_from:
                    extra_from.append(other_name)
                break
    return extra_from


def split_st(lines):
    """把一份 st 分成（属性行, 教益句, 丢掉的风味句数）。

    为什么不能整行引号一刀切掉：客户端把**教益句**（"教你学会制作鬼纹腰带。"）也放在同一个斜体框里，
    参考站照类名把它标成风味句丢掉，插件源则原样带着引号抄回来。一刀切的结果是
    1,197 件图样/秘典/公式/设计图只剩"需要工程学 (125)"这种行——那一件唯一有用的话没了，
    比 2026-10-14 那版还差。所以：教益句剥掉引号单独立进 use，纯风味句（"相信我，她会明白的。"）才丢。
    句中才出现引号的（使用：为角色解锁“炼金师”头衔）不动，那是功能文本本身。

    2026-10-20 A02 改一条：**判教学句看内容，不看源有没有给引号。**
    XR 升到 66 之后，254 件的教学句是不带引号写进 st 的（"教你学会制作优质皮靴。"），
    旧规则只认整行引号，于是这些句子被当成属性行，把解包侧的"需要制皮 (65)"整条顶掉——
    247 件就这么丢了使用条件。插件没写要求不等于没有要求（站方 2026-10-20 定的合并口径），
    这种"上游换了写法"必须在这里认出来，不能算成授权删除。"""
    keep, use, dropped = [], None, 0
    for s in lines or []:
        t = s.strip()
        q = is_quoted(t)
        inner = t[1:-1].strip() if q else t
        if USE_RE.search(inner):
            # 教学句：带不带引号都不是属性行，单独进 use
            use = use or inner
            continue
        if q:
            dropped += 1
            continue
        keep.append(s)
    return keep, use, dropped


def norm(lines):
    """整串归一（只用于"完全一样"的判断）：去空白与中文标点、去括号、"点伤害"→"伤害"、
    "护甲值"→"护甲"、"每秒伤害"→dps、"装备唯一"→"唯一"。不改落盘的原文。"""
    out = []
    for s in lines or []:
        t = s.replace('（', '(').replace('）', ')')
        t = re.sub(r'[()。，、\s]', '', t)
        t = t.replace('装备唯一', '唯一').replace('点伤害', '伤害')
        t = t.replace('护甲值', '护甲').replace('每秒伤害', 'dps')
        out.append(t)
    return sorted(out)


def nums(lines):
    """数值签名：只取每行里的数字（含小数），按大小排序。
    两源用这个判"是不是真的改了数值"——因为写法差异（GI 会自己加"装备唯一"、
    把"装备：提高所有法术…最多15点"缩写成"装备：+15 治疗"）不该算成版本差异，
    只有数字对不上才是真改了。"""
    out = []
    for s in lines or []:
        for m in re.finditer(r'\d+(?:\.\d+)?', s):
            out.append(float(m.group(0)))
    return sorted(out)


def same_text(a, b):
    return norm(a) == norm(b)


def selftest():
    """split_st 的夹具回归（2026-10-20 A02）。钉的是：
       教学句不管带不带引号都不许当属性行；整条只有教学句时属性行必须为空，
       这样合并端才会落回兜底源、而不是把「需要制皮 (65)」整条顶掉。"""
    cases = [
        ('带引号的教学句进 use，属性行留下',
         ['需要工程学 (125)', '“教你学会制作火焰偏斜器。”'],
         (['需要工程学 (125)'], '教你学会制作火焰偏斜器。', 0)),
        ('不带引号的教学句同样进 use（XR 66 的新写法）',
         ['教你学会制作优质皮靴。'], ([], '教你学会制作优质皮靴。', 0)),
        ('纯风味句仍然丢掉，条件行不动',
         ['需要制皮 (40)', '“相信我，她会明白的。”'],
         (['需要制皮 (40)'], None, 1)),
        ('句中引号不算引号行（那是功能文本）',
         ['使用：为角色解锁“炼金师”头衔'], (['使用：为角色解锁“炼金师”头衔'], None, 0)),
        ('普通属性行原样保留',
         ['148点护甲', '+12 耐力'], (['148点护甲', '+12 耐力'], None, 0)),
    ]
    bad = 0
    print('\n=== merge-items-detail.py split_st 夹具回归 ===')
    for name, inp, want in cases:
        got = split_st(inp)
        ok = got == want
        bad += 0 if ok else 1
        print('  %s  %-52s %s' % ('PASS' if ok else 'FAIL', name,
                                  '' if ok else '得到 %s 期望 %s' % (got, want)))
    # 条件行与使用效果行都不许被高优先级源静默清掉——**调真的 carry_missing**。
    # 这一段以前是在自测里把同样的表达式现写一遍再判自己：生产逻辑怎么改它都照样绿，
    # 那是假绿（2026-10-20 自己查出来的，和这一天拆掉的另外几处同一个毛病）。
    carry = [
        ('高优先级源没写条件时，兜底源的「需要附魔 (200)」必须留下并记来源',
         {'st': ['使用： 制造次级巫师之油。'], 'stFrom': 'gi'},
         (('gi', ['使用： 制造次级巫师之油。']), ('xr', None), ('wclbox', ['需要附魔 (200)'])),
         ['需要附魔 (200)'], ['wclbox']),
        ('高优先级源没写使用效果时，兜底源那句「使用：使目标昏迷」必须留下',
         {'st': ['装备唯一', '装备：每5秒恢复2法力值。'], 'stFrom': 'xr'},
         (('gi', None), ('xr', ['装备唯一', '装备：每5秒恢复2法力值。']),
          ('wclbox', ['使用： 使目标狼人昏迷4秒。 (5分钟冷却时间)'])),
         ['使用： 使目标狼人昏迷4秒。 (5分钟冷却时间)'], ['wclbox']),
        ('这一类行高优先级源自己给了就不许再补第二份（会重复显示）',
         {'st': ['需要附魔 (1)', '装备唯一'], 'stFrom': 'gi'},
         (('gi', ['需要附魔 (1)']), ('xr', None), ('wclbox', ['需要附魔 (200)'])),
         None, []),
        ('缺这一行的就是当前取值那一家（它真没写）时，不拿自己补自己',
         {'st': ['装备唯一'], 'stFrom': 'wclbox'},
         (('gi', None), ('xr', None), ('wclbox', ['需要附魔 (200)'])),
         None, []),
    ]
    for label, rec0, srcs, want_line, want_from in carry:
        rec = dict(rec0)
        rec['st'] = list(rec0['st'])
        got_from = carry_missing(rec, srcs)
        ok = got_from == want_from and (
            want_line is None or want_line[0] in ''.join(rec['st']))
        bad += 0 if ok else 1
        print('  %s  %-52s %s' % ('PASS' if ok else 'FAIL', label,
                                  '' if ok else '补进 %s / 记来源 %s（期望 %s）'
                                  % (rec['st'], got_from, want_from)))
    total = len(cases) + len(carry)
    print('用例 %d 条，失败 %d 条' % (total, bad))
    return 1 if bad else 0


def main():
    import sys
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    with open(os.path.join(ROOT, 'items.json'), encoding='utf-8') as f:
        items = json.load(f)
    gi = load('gi-items-detail.json')
    xr = load('xr-items-detail.json')
    wb = load('wclbox-items-detail.json')
    wb_items = wb.get('items', {})
    wb_build = sorted({x.get('build') for x in wb_items.values() if x.get('build')})

    gi_st, gi_src = gi.get('st', {}), gi.get('src', {})
    xr_items = xr.get('items', {})
    valid_ids = {str(x['id']) for x in items['items']}
    orphans = sorted([k for k in gi_st if k not in valid_ids]
                     + [k for k in gi_src if k not in valid_ids]
                     + [k for k in xr_items if k not in valid_ids]
                     + [k for k in wb_items if k not in valid_ids], key=int)

    out = {}
    real_conflicts = []
    sell_conflicts = []
    n = {'st': 0, 'stWb': 0, 'stGi': 0, 'stXr': 0, 'sell': 0, 'sellWb': 0, 'sellXr': 0,
         'src': 0, 'sameText': 0, 'formatOnly': 0, 'wbMissingKept': 0, 'droppedFlavor': 0, 'use': 0, 'stExtra': 0}
    for kid in sorted(valid_ids, key=int):
        rec = {}
        w = wb_items.get(kid) or {}
        # 三份都先分一次：属性行 / 教益句 / 纯风味句（详见 split_st 的说明）
        w_st, w_use, w_drop = split_st(w.get('st'))
        g_st, g_use, g_drop = split_st((gi_st.get(kid) or {}).get('st'))
        x_st, x_use, x_drop = split_st((xr_items.get(kid) or {}).get('st'))
        n['droppedFlavor'] += w_drop + g_drop + x_drop
        # 自报 missing（无限客户端里没有这个 id）与 held（保留了数据行、没有属性）的那些件，
        # 页面摆的是经典侧的提示框，不能当无限的数用——只能回落实测与社区稿
        w_ok = bool(w_st) and not w.get('tipIsClassic') and w.get('status') not in ('missing', 'held')
        if g_st:
            rec['st'] = g_st
            rec['stFrom'] = 'gi'
            n['st'] += 1
            n['stGi'] += 1
            for other, key in ((x_st, 'xr'), (w_st if w_ok else None, 'wclbox')):
                if not other:
                    continue
                if norm(other) == norm(g_st):
                    n['sameText'] += 1
                elif nums(other) == nums(g_st):
                    n['formatOnly'] += 1
                else:
                    real_conflicts.append({'id': int(kid), 'gi': g_st, key: other, 'with': key})
        elif x_st:
            rec['st'] = x_st
            rec['stFrom'] = 'xr'
            n['st'] += 1
            n['stXr'] += 1
            if w_ok and nums(w_st) != nums(x_st):
                real_conflicts.append({'id': int(kid), 'xr': x_st, 'wclbox': w_st, 'with': 'wclbox'})
        elif w_ok:
            # 插件两份都没有的件才用当前解包兜底；无限新增那 1,374 件全走这一路
            rec['st'] = w_st
            rec['stFrom'] = 'wclbox'
            n['st'] += 1
            n['stWb'] += 1
        if not g_st and w.get('status') in ('missing', 'held'):
            n['wbMissingKept'] += 1
        # 教益句单独立一段，不混进属性列表里（一段一个来源，徽标才说得清这一句是谁给的）。
        # 本轮的无限解包快照没带这一层：参考站把"教你学会制作X"按风味句的类名摆，抓取时照它的
        # 分类丢了；抓取脚本已改成下一轮按 build 重抓时会自己补上 use，那时这里就换成解包优先。
        u = g_use or x_use or w.get('use') or w_use
        if u:
            rec['use'] = u
            rec['useFrom'] = 'gi' if g_use else ('xr' if x_use else 'wclbox')
            n['use'] += 1
        # 2026-10-20 A02：高优先级源整条没写使用条件时，把兜底源那条「需要X (N)」留下，
        # 并单独记它是谁给的（stExtraFrom）。上游换写法（XR 66 把教学句不加引号塞进 st）
        # 不能算成「官方说这件没有要求」——那是解析口径，不是数据授权。
        extra_from = carry_missing(rec, (('gi', g_st), ('xr', x_st),
                                         ('wclbox', w_st if w_ok else None)))
        if extra_from:
            rec['stExtraFrom'] = extra_from
            n['stExtra'] += 1
        w_sell = w.get('sell')
        x_sell = (xr_items.get(kid) or {}).get('sell')
        if x_sell:
            # 站主定的"以插件为准"：卖价先取社区稿，wclbox 只兜它没有的
            rec['sell'] = x_sell
            rec['sellFrom'] = 'xr'
            n['sell'] += 1
            n['sellXr'] += 1
            if w_sell and w_sell != x_sell:
                sell_conflicts.append({'id': int(kid), 'xr': x_sell, 'wclbox': w_sell, 'with': 'wclbox'})
        elif w_sell:
            rec['sell'] = w_sell
            rec['sellFrom'] = 'wclbox'
            n['sell'] += 1
            n['sellWb'] += 1
        g = gi_src.get(kid)
        if g:
            rec['src'] = g['src']
            rec['srcName'] = g['srcName']
            n['src'] += 1
        if rec:
            out[kid] = rec

    doc = {
        'meta': {
            'generatedAt': date.today().isoformat(),
            'method': 'tools/merge-items-detail.py 合三份 upstream 快照：wclbox-items-detail.json'
                      '（tools/scrape-wclbox-items-detail.py 逐件全量抓物品详情页）、'
                      'gi-items-detail.json 与 xr-items-detail.json'
                      '（tools/extract-addon-items-detail.py 从两份无限服插件 Data.lua 抽取）。'
                      '属性与卖价按 GI（Beta 实测转述）> XR（社区稿）> wclbox（当前 beta 解包，兜底）取值'
                      '（站主 2026-10-16 定：取值以插件为准）；教益句单独一段按 GI > XR 补，纯风味句丢掉；'
                      '数值签名不一致的进 conflicts，只有写法不同的计 formatOnly；'
                      '出处只有 GI 有；英文名按站主拍板不取。',
            'pageNote': '属性与卖价先按两份插件资料：Beta 实测掉落记录（GearInsight 无限版转述）与'
                        '社区整理稿（XR 全能助手转述）；这两份都没有的那些件（含无限新增的大部分），'
                        '改按无限测试版客户端（经新手盒子转述）补。标题右边的小标写明这一条出自哪一份。'
                        '同一件在几份资料里数值不同的，都留了档，等实测逐件定。'
                        '出处（哪座本、哪个首领掉落）只有实测掉落记录有。'
                        '几份资料都没有的那一件，详情里就不显示那一段。',
            'sources': [
                {'key': 'wclbox', 'name': '无限数据库 · 物品详情页', 'kind': '当前 beta 客户端解包转述',
                 'builds': wb_build, 'date': wb.get('meta', {}).get('fetched')},
                # 版本与日期从快照 meta 读，不在这里手抄：
                # 以前写死 0.4.29 / 0.37.1，插件升到 GI 0.5.1、XR 66 之后
                # 成品 meta 还在给每条记录盖旧号的出处（2026-10-19 那条"版本号不手抄"的规矩补上这一处）
                {'key': 'gi', 'name': 'GearInsight 无限版 ' + str(gi.get('meta', {}).get('addonVersion', '?')),
                 'kind': 'beta 解包 + 实测掉落转述',
                 'date': gi.get('meta', {}).get('fetched'),
                 'extractedAt': gi.get('meta', {}).get('extractedAt'),
                 'sourceSha256': (gi.get('meta', {}).get('sourceStamp') or {}).get('sha256')},
                {'key': 'xr', 'name': 'XR 全能助手 ' + str(xr.get('meta', {}).get('addonVersion', '?')),
                 'kind': '社区整理稿转述',
                 'date': xr.get('meta', {}).get('fetched'),
                 'extractedAt': xr.get('meta', {}).get('extractedAt'),
                 'sourceSha256': (xr.get('meta', {}).get('sourceStamp') or {}).get('sha256')},
            ],
            'counts': dict(total=len(out), **n,
                           conflicts=len(real_conflicts),
                           conflictsListed=min(len(real_conflicts), CONFLICT_CAP),
                           orphans=len(orphans),
                           wbCollected=len(wb_items)),
            'conflicts': real_conflicts[:CONFLICT_CAP],
            'orphans': orphans[:100],
        },
        'items': out,
    }
    p = os.path.join(ROOT, 'items-detail.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('物品详情：%d 件（属性 %d：GI %d / XR %d / 解包兜底 %d · 教益句 %d · '
          '卖价 %d：XR %d / 解包兜底 %d · 出处 %d · 与另一说数值不同 %d · 只是写法不同 %d · '
          '逐字相同 %d · 丢掉纯风味句 %d · 名录外孤儿 %d）'
          % (len(out), n['st'], n['stGi'], n['stXr'], n['stWb'], n['use'], n['sell'], n['sellXr'],
             n['sellWb'], n['src'], len(real_conflicts), n['formatOnly'], n['sameText'],
             n['droppedFlavor'], len(orphans)))


if __name__ == '__main__':
    main()
