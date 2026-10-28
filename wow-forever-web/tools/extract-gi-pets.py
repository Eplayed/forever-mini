#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 GearInsight_Forever 的 PetData.lua 抽猎人宠物那一层，落成 upstream 快照（2026-10-28 站主拍板要开宠物页）。

只取事实字段：家族（名 / 图标 / 伤害护甲生命修正 / 会不会是无限新增 / 该族技能名）、
技能（名 / 等级上限 / 等级数 / 冷却 / 耗能 / 哪些族能用 / 是否新增 / 是否改名）。

**明确丢掉的字段（红线，不是风格问题）**：`dcn` 与 `den` —— 那是成句的技能描述
（例：`dcn="对敌人造成81-99点伤害。"`），第三方插件写的文案不复制。
`renamed` 这个布尔留不留？留：它是"这条技能在《无限》里改过名"这一事实，不是文案。

图标：PetData 里 `icon=` 是客户端的贴图文件号，不是本站用的图标键名。
所以这一步要拿 listfile 把号翻成 `Interface/ICONS/<键名>.blp` 的**键名**，
翻得到的才写 iconKey，翻不到的一律留 null 并把号记在 iconFdids 里——
**不猜键名**（猜错就是拿别的图冒充这一族的长相）。

用法：
    python3 tools/extract-gi-pets.py \
        [--src ~/Documents/project/.scratch/wow] \
        [--listfile /tmp/wow-ro/ziliao-export/listfile/client-fdid-name.csv]
产物：app/data/upstream/gi-pets.json
"""
import argparse
import datetime
import io
import json
import os
import re
import sys

HOME = os.path.expanduser('~')
DEF_SRC = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow')
DEF_LISTFILE = '/tmp/wow-ro/ziliao-export/listfile/client-fdid-name.csv'
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(WEB, 'app', 'data', 'upstream', 'gi-pets.json')

ENTRY_RE = re.compile(r'\{\s*id=(\d+),(.*?)\}\s*,?\s*$')
STR_RE = re.compile(r'(\w+)="([^"]*)"')
NUM_RE = re.compile(r'(\w+)=(\-?\d+)')
BOOL_RE = re.compile(r'(\w+)=(true|false)')
ARR_RE = re.compile(r'(\w+)=\{([^{}]*)\}')
DROP = ('dcn', 'den')


def section(text, name, next_names):
    i = text.index(name + ' = {')
    j = len(text)
    for n in next_names:
        k = text.find('\n  ' + n + ' = {', i)
        if k != -1:
            j = min(j, k)
    return text[i:j]


def parse_rows(block):
    rows = []
    for line in block.split('\n'):
        line = line.strip().rstrip(',')
        # 整行形如 `{ id=1, en="Wolf", …, skills={"Bite","Dash"} }`：
        # 去掉最外层那对花括号再解析，不然技能名那个数组的右括号会被当成行的结尾。
        if not (line.startswith('{ id=') and line.endswith('}')):
            continue
        body = line[1:-1]
        m = re.match(r'^\s*id=(\d+),\s*(.*)$', body, re.S)
        if not m:
            continue
        row = {'id': int(m.group(1))}
        for k, v in STR_RE.findall(m.group(2)):
            if k in DROP:
                continue
            row[k] = v
        for k, v in NUM_RE.findall(m.group(2)):
            row[k] = int(v)
        for k, v in BOOL_RE.findall(m.group(2)):
            row[k] = (v == 'true')
        arr = ARR_RE.search(m.group(2))
        if arr:
            inner = arr.group(2)
            # 同一个花括号在两份表里装的东西不一样：家族里是技能名（字符串），
            # 技能里是家族号（数字）。按有没有引号分，不按表名分。
            if '"' in inner:
                row[arr.group(1)] = re.findall(r'"([^"]*)"', inner)
            else:
                row[arr.group(1)] = [int(x) for x in re.findall(r'\d+', inner)]
        rows.append(row)
    return rows


def load_icons(listfile, want):
    """fdid -> 图标键名（Interface/ICONS/<键>.blp）。只认 verified 那一条。"""
    hit = {}
    if not os.path.exists(listfile):
        sys.stderr.write('拿不到 listfile（%s），这一轮 iconKey 全留空。\n' % listfile)
        return hit, False
    with io.open(listfile, encoding='utf-8-sig', newline='') as f:
        import csv as _csv
        for r in _csv.DictReader(f):
            if r['fdid'] in want and r['name_kind'] == 'verified':
                p = r['name']
                m = re.match(r'^Interface/ICONS/(.+)\.blp$', p, re.I)
                if m:
                    hit[r['fdid']] = m.group(1).lower()
    return hit, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=DEF_SRC)
    ap.add_argument('--listfile', default=DEF_LISTFILE)
    args = ap.parse_args()

    path = os.path.join(args.src, 'GearInsight_Forever', 'PetData.lua')
    if not os.path.exists(path):
        sys.exit('找不到 %s（插件根目录用 --src 指）' % path)
    text = io.open(path, encoding='utf-8').read()

    build = re.search(r'build\s*=\s*"([\d.]+)"', text)
    base = re.search(r'经典旧世\s*([\d.]+)\s*宠物技能线', text)
    fams = parse_rows(section(text, 'families', ['skills']))
    skills = parse_rows(section(text, 'skills', []))
    if not fams or not skills:
        sys.exit('解析出来是空的：families %d / skills %d —— 格式变了，别写半成品' %
                 (len(fams), len(skills)))

    want = {str(f['icon']) for f in fams if f.get('icon') is not None}
    icons, used_listfile = load_icons(args.listfile, want)

    fam_rows = []
    for f in fams:
        fdid = str(f.get('icon', ''))
        fam_rows.append({
            'id': f['id'],
            'nameEn': f.get('en', ''),
            'nameCn': f.get('cn', ''),
            'iconKey': icons.get(fdid),
            'iconFdids': [fdid] if fdid else [],
            'dmgMod': f.get('dmg'), 'armorMod': f.get('arm'), 'hpMod': f.get('hp'),
            'isNew': bool(f.get('new')),
            'skillNamesEn': f.get('skills', []),
        })
    sk_rows = []
    for s in skills:
        sk_rows.append({
            'id': s['id'],
            'nameEn': s.get('en', ''),
            'nameCn': s.get('cn', ''),
            'learnLevel': s.get('lv'), 'maxLevel': s.get('maxlv'),
            'ranks': s.get('ranks'), 'cooldownSec': s.get('cd'), 'cost': s.get('cost'),
            'isNew': bool(s.get('new')), 'renamed': bool(s.get('renamed')),
            'familyIds': s.get('fams', []),
        })

    fam_ids = {f['id'] for f in fam_rows}
    orphan = sorted({i for s in sk_rows for i in s['familyIds']} - fam_ids)
    today = datetime.date.today().isoformat()
    out = {
        'meta': {
            'kind': 'gi-pets',
            'fetchedAt': today,
            'source': 'GearInsight 无限版 %s' % os.environ.get('GI_VERSION', '0.5.6'),
            'file': 'GearInsight_Forever/PetData.lua',
            'selfReportedBuild': build.group(1) if build else None,
            'selfReportedBase': base.group(1) if base else None,
            'selfReportedNote': '插件文件自述：数据取自《无限》客户端 DB2（wago.tools），'
                                '「新增」= 经典旧世那一版宠物技能线里没有。本站未逐行回客户端表核对。',
            'droppedFields': list(DROP),
            'droppedWhy': '成句的技能描述是插件写的文案，红线不复制第三方说明文字',
            'iconKeyFrom': ('客户端 listfile 逐号回读（Interface/ICONS/<键>.blp），翻不到留 null'
                            if used_listfile else '本轮没读到 listfile，iconKey 全空'),
            'counts': {
                'families': len(fam_rows),
                'familiesNew': sum(1 for f in fam_rows if f['isNew']),
                'skills': len(sk_rows),
                'skillsNew': sum(1 for s in sk_rows if s['isNew']),
                'skillIconless': len(sk_rows),
                'familyIdsReferencedButMissing': len(orphan),
            },
            'provenance': {'type': 'addon', 'url': 'GearInsight_Forever/PetData.lua',
                           'checkedAt': today},
        },
        'families': fam_rows,
        'skills': sk_rows,
        'missingFamilyIds': orphan,
    }
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write('\n')
    c = out['meta']['counts']
    print('写 %s：家族 %d（新增 %d）· 技能 %d（新增 %d）· 图标键名命中 %d/%d' %
          (os.path.relpath(OUT, WEB), c['families'], c['familiesNew'],
           c['skills'], c['skillsNew'],
           sum(1 for x in fam_rows if x['iconKey']), len(fam_rows)))
    if orphan:
        print('  技能引用了这份表里没有的家族号：%s（照实留档，不删也不补）' % orphan)


if __name__ == '__main__':
    main()
