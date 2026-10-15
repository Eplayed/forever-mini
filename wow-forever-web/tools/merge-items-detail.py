#!/usr/bin/env python3
# 合并三份 upstream 快照 → src/data/items-detail.json（物品线二批：W2-3 全量抓取后重排层级）。
#
# 优先级（站主 2026-10-15 拍板按 docs/ITEMS-DETAIL-SOURCE-EVAL-2026-10-14.md 结论执行）：
#   属性 st / 卖价 sell：wclbox 物品详情（当前 beta 客户端解包转述）
#                        > GI loot（foreverchanges Beta 实测转述）
#                        > XR（社区整理稿）
#   —— 评估实测：双方都有属性的 106 件里，数值确实随 build 改过（硬根法杖 44-67/每秒 16.8/+8 精神
#      对旧稿 36-54/每秒 13.6/+9 精神+20 法术强度），线上原来展示的是旧 build 的数。
#   出处 src/srcName：只有 GI 有（"本 · 首领"口径），维持不变；
#   教益句 use（"教你学会制作X"这一句）：单独一段，按 GI > XR 补——参考站把它当风味句摆，
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


def is_quoted(t):
    return (t.startswith('“') and t.endswith('”')) or (t.startswith('"') and t.endswith('"'))


def split_st(lines):
    """整行被引号包住的行分两类处理，返回（留下的属性行, 教益句, 丢掉的风味句数）。

    为什么不能整行引号一刀切掉：客户端把**教益句**（"教你学会制作鬼纹腰带。"）也放在同一个斜体框里，
    参考站照类名把它标成风味句丢掉，插件源则原样带着引号抄回来。一刀切的结果是
    1,197 件图样/秘典/公式/设计图只剩"需要工程学 (125)"这种行——那一件唯一有用的话没了，
    比 2026-10-14 那版还差。所以：教益句剥掉引号单独立进 use，纯风味句（"相信我，她会明白的。"）才丢。
    句中才出现引号的（使用：为角色解锁“炼金师”头衔）不动，那是功能文本本身。"""
    keep, use, dropped = [], None, 0
    for s in lines or []:
        t = s.strip()
        if is_quoted(t):
            inner = t[1:-1].strip()
            if USE_RE.search(inner):
                use = use or inner
            else:
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


def main():
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
         'src': 0, 'wbSame': 0, 'formatOnly': 0, 'wbMissingKept': 0, 'droppedFlavor': 0, 'use': 0}
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
        if w_ok:
            rec['st'] = w_st
            rec['stFrom'] = 'wclbox'
            n['st'] += 1
            n['stWb'] += 1
            for other, key in ((g_st, 'gi'), (x_st, 'xr')):
                if not other:
                    continue
                if norm(other) == norm(w_st):
                    n['wbSame'] += 1
                elif nums(other) == nums(w_st):
                    n['formatOnly'] += 1
                else:
                    real_conflicts.append({'id': int(kid), 'wclbox': w_st, key: other, 'with': key})
        elif g_st:
            rec['st'] = g_st
            rec['stFrom'] = 'gi'
            n['st'] += 1
            n['stGi'] += 1
            if w.get('status') in ('missing', 'held'):
                n['wbMissingKept'] += 1
            if x_st and x_st != g_st:
                real_conflicts.append({'id': int(kid), 'gi': g_st, 'xr': x_st})
        elif x_st:
            rec['st'] = x_st
            rec['stFrom'] = 'xr'
            n['st'] += 1
            n['stXr'] += 1
        # 教益句单独立一段，不混进属性列表里（一段一个来源，徽标才说得清这一句是谁给的）。
        # 本轮的无限解包快照没带这一层：参考站把"教你学会制作X"按风味句的类名摆，抓取时照它的
        # 分类丢了；抓取脚本已改成下一轮按 build 重抓时会自己补上 use，那时这里就换成解包优先。
        u = w.get('use') or w_use or g_use or x_use
        if u:
            rec['use'] = u
            rec['useFrom'] = 'wclbox' if (w.get('use') or w_use) else ('gi' if g_use else 'xr')
            n['use'] += 1
        w_sell = w.get('sell')
        x_sell = (xr_items.get(kid) or {}).get('sell')
        if w_sell:
            rec['sell'] = w_sell
            rec['sellFrom'] = 'wclbox'
            n['sell'] += 1
            n['sellWb'] += 1
            if x_sell and x_sell != w_sell:
                sell_conflicts.append({'id': int(kid), 'wclbox': w_sell, 'xr': x_sell})
        elif x_sell:
            rec['sell'] = x_sell
            rec['sellFrom'] = 'xr'
            n['sell'] += 1
            n['sellXr'] += 1
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
                      '属性与卖价按 wclbox（当前 beta 解包）> GI（Beta 实测转述）> XR（社区稿）取值，'
                      '教益句（教你学会制作X）单独一段按 GI > XR 补，纯风味句丢掉；'
                      '归一化后仍不一致的进 conflicts，只有写法不同的计 formatOnly；'
                      '出处只有 GI 有；英文名按站主拍板不取。',
            'pageNote': '属性与卖价先按无限测试版客户端（经新手盒子转述）；客户端里没有的那些件，'
                        '回落到 Beta 实测掉落记录与社区整理稿，标题右边的小标写明这一条出自哪一份。'
                        '"教你学会制作…"那一句按实测掉落记录与社区整理稿补——测试版客户端把它排在'
                        '风味框里，这一版没从解包中取到。出处（哪座本、哪个首领掉落）只有实测掉落记录有。'
                        '几份资料都没有的那一件，详情里就不显示那一段。',
            'sources': [
                {'key': 'wclbox', 'name': '无限数据库 · 物品详情页', 'kind': '当前 beta 客户端解包转述',
                 'builds': wb_build, 'date': wb.get('meta', {}).get('fetched')},
                {'key': 'gi', 'name': 'GearInsight 无限版 0.4.29', 'kind': 'beta 解包 + 实测掉落转述',
                 'date': '2026-10-03'},
                {'key': 'xr', 'name': 'XR 全能助手 0.37.1', 'kind': '社区整理稿转述',
                 'date': '2026-09-20'},
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
    print('物品详情：%d 件（属性 %d：wclbox %d / GI %d / XR %d · 教益句 %d · 卖价 %d：wclbox %d / XR %d · '
          '出处 %d · 数值真不同 %d · 只是写法不同 %d · 丢掉纯风味句 %d · 名录外孤儿 %d）'
          % (len(out), n['st'], n['stWb'], n['stGi'], n['stXr'], n['use'], n['sell'], n['sellWb'],
             n['sellXr'], n['src'], len(real_conflicts), n['formatOnly'], n['droppedFlavor'], len(orphans)))


if __name__ == '__main__':
    main()
