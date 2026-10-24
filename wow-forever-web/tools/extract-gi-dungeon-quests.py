#!/usr/bin/env python3
# 从 GearInsight_Forever 的 DungeonQuestData.lua 抽副本任务详情，落 upstream 修剪快照。
# 依据 docs/wow-infinite-sources.md 第十四节：该表是 Wowhead Forever 1.60.1（经 Dungeon Assistant
# 转手）+ vmangos 中文名；只取事实性字段（名/等级/经验/接取人/区域/开启物品/前置），
# 任务目标原文（o=）与坐标不取（坐标站点没有承载字段，记在 provenance 里说明）。
# 用法：python3 tools/extract-gi-dungeon-quests.py <DungeonQuestData.lua>
# 产物：app/data/upstream/gi-dungeon-quests.json（键保留 GI 自己的 k，merge 侧再映射站点 slug）
# 幂等：同输入字节一致。
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, "app", "data", 'upstream')


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
    raise ValueError('大括号不配对 @%d' % start)


def top_split(inner):
    """按顶层逗号切 k=v 词元（v 可能是带嵌套大括号的对象）。"""
    parts, buf, depth, q, i, n = [], '', 0, None, 0, len(inner)
    while i < n:
        c = inner[i]
        if q:
            if c == '\\' and i + 1 < n:
                buf += c + inner[i + 1]
                i += 2
                continue
            if c == q:
                q = None
            buf += c
            i += 1
            continue
        if c in '"\'':
            q = c
            buf += c
            i += 1
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        if c == ',' and depth == 0:
            parts.append(buf)
            buf = ''
            i += 1
            continue
        buf += c
        i += 1
    if buf.strip():
        parts.append(buf)
    return parts


def unq(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    return v


def parse_entry(e):
    """顶层 k=v 词元 → dict；嵌套对象保留原始大括号文本。"""
    d = {}
    for tok in top_split(e[1:-1] if e.startswith('{') else e):
        m = re.match(r'(\w+)=(.*)$', tok.strip(), re.S)
        if m:
            d[m.group(1)] = m.group(2).strip()
    return d


def obj_field(raw):
    """'k="npc",id=11833,c="拉哈罗",...' → dict（只剥一层；标量值剥引号）。"""
    if not raw or not raw.startswith('{'):
        return None
    d = {}
    for tok in top_split(raw[1:-1]):
        m = re.match(r'(\w+)=(.*)$', tok.strip(), re.S)
        if m:
            d[m.group(1)] = unq(m.group(2).strip())
    return d


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.expanduser('~'), 'Documents/Trae-CN/temp_20261014_01/gi-forever/DungeonQuestData.lua')
    src = open(path, encoding='utf-8').read()

    # 副本清单内联在 ns.DQ = { dungeons = {...} 里（不在行首）；任务详情表才是行首顶层键。
    # 用 [5722]（第一座本的第一条任务）反查详情表锚点，dungeons 区用括号配平切出来。
    dk = src.index('dungeons = {')
    d_open = src.index('{', dk)
    d_seg_end = brace_match(src, d_open)
    d_seg = src[d_open + 1:d_seg_end]
    # 任务详情表：条目就是两格缩进的 [数字]={...，从 [5722] 那行直切到文件尾
    # （尾部若有别的字符串值小表，\]=\{ 的条目模式天然跳过它们）
    m_first = re.search(r'(?m)^  \[\d+\]=\{', src)
    if not m_first:
        sys.exit('DungeonQuestData.lua 找不到任务条目区')
    q_seg = src[m_first.start():]
    dungeons = {}
    # loot={...} 有嵌套大括号，[^{}] 过不去——按已知字段序显式写（此前 29 座比对用的同款模式）
    for m in re.finditer(r'\{k="([^"]+)",n="([^"]+)",loot=\{[^}]*\},min=\d+,max=\d+,'
                         r'side="[^"]*",new=\w+,q=\{([\d,]*)\}', d_seg):
        dungeons[m.group(1)] = {
            'nameEn': m.group(2),
            'qids': [x for x in m.group(3).split(',') if x],
        }

    # 任务条目区直切到文件尾（q_seg[0] 就是第一条的开括号所在行）；
    # 尾部若混有字符串值小表（[id]="名字"），条目模式 \]=\{ 天然跳过
    details = {}
    for m in re.finditer(r'\[(\d+)\]=\{', q_seg):
        # 条目正文从 '{' 起，别把 "[id]=" 前缀带进解析器
        ob = q_seg.index('{', m.start())
        e = q_seg[ob:brace_match(q_seg, ob) + 1]
        f = parse_entry(e)
        qid = m.group(1)
        st = obj_field(f.get('st', ''))
        rec = {
            'name': unq(f.get('c', '')) or None,          # 中文名（vmangos+游戏内现读）
            'nameEn': unq(f.get('n', '')) or None,
            'questLevel': int(f['lv']) if f.get('lv', '').isdigit() else None,
            'reqLevel': int(f['req']) if f.get('req', '').isdigit() else None,
            'xp': int(f['xp']) if f.get('xp', '').isdigit() else None,
            'pickupNpc': unq(st.get('c')) if st and st.get('k') == 'npc' else None,
            'pickupZone': unq(st.get('zc')) if st else None,
            'startItem': unq(st.get('c')) if st and st.get('k') == 'item' else None,
        }
        # 前置：pre/preAny 里是任务 id，用 id→中文名 映射成名字串（站点字段承载的是名字）
        pre_ids = []
        for key in ('pre', 'preAny'):
            raw = f.get(key, '')
            if raw and raw.startswith('{'):
                pre_ids += re.findall(r'\d+', raw)
        names = []
        for pid in pre_ids:
            pd = details.get(pid) or {}
            names.append(pd.get('name') or None)
        # details 此时可能还没填到该 id——第二遍再补
        rec['_pre_ids'] = pre_ids
        details[qid] = rec

    # 第二遍：补前置名
    for qid, rec in details.items():
        names = []
        for pid in rec.pop('_pre_ids', []):
            pd = details.get(pid) or {}
            if pd.get('name'):
                names.append(pd['name'])
        rec['preQuest'] = '、'.join(dict.fromkeys(names)) or None

    out_dungeons = {}
    for k, info in dungeons.items():
        quests = []
        for qid in info['qids']:
            if qid in details:
                rec = dict(details[qid])
                rec['source'] = 'gi'
                quests.append(rec)
        out_dungeons[k] = {
            'nameEn': info['nameEn'],
            'questTotal': len(info['qids']),
            'quests': quests,
        }

    doc = {
        'meta': {
            'source': 'GearInsight_Forever 0.4.29 DungeonQuestData.lua（Dungeon Assistant→Wowhead '
                      'Forever 1.60.1 转述；中文名 vmangos+游戏内现读；站点判定见 '
                      'docs/wow-infinite-sources.md 第十四节）',
            'fetched': '2026-10-13',
            'extractedAt': date.today().isoformat(),
            'counts': {'dungeons': len(out_dungeons),
                       'quests': sum(len(v['quests']) for v in out_dungeons.values())},
            'note': '接取人坐标字段站点没有承载，本轮不取；任务目标原文（o=）按红线不取。',
        },
        'dungeons': out_dungeons,
    }
    os.makedirs(UP, exist_ok=True)
    p = os.path.join(UP, 'gi-dungeon-quests.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('写 %s：%d 座 / 任务 %d 条' % (os.path.relpath(p), doc['meta']['counts']['dungeons'],
                                        doc['meta']['counts']['quests']))
    for k in ('excavation', 'dalaran'):
        v = out_dungeons.get(k, {})
        print('  %s：%d 条（站点空座候选）' % (k, len(v.get('quests', []))))


if __name__ == '__main__':
    main()
