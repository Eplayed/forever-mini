#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本机插件目录抽《无限》全职业宏库，落成 upstream 快照（2026-10-30 站主：素材库里有宏命令素材，先整理数据）。

源文件两份，**同一批宏的两个形态，不是两个独立来源**（XR 自己在文件头写「v66 同步 GI 2026-10-19 新版」）：

1. `GearInsight_Forever/MacroData.lua` —— 245 条，宏体里法术名是 `{{法术ID}}` 占位，
   另带 key / 组名（中英）/ 中英标题 / 中英说明 / 最低等级 / fv（《无限》新技能）/ spells 列表。
   文件头自报：宏来源 foreverdb.net（对过 Beta 1.60.1.70205）+ classicwowforever.com。
2. `XR_DungeonGuide/Data_Macros.lua` —— 同样 245 条、逐条同序，宏体里的法术名**已烘成中文**。

这一步**两份都原样留着**，不做判断：烘好的那份是下一步交叉核对用的反面参照，
不是"另一个来源"。真正的成品由 tools/merge-macros.py 出。

取哪些字段（红线口径，见根 AGENTS.md 2026-10-18「网页端放开清单」第 1 条）：
宏正文、宏名、用途分组、最低可用等级、《无限》新技能标记、法术 ID —— 这些是"哪条宏做什么"的事实层。
插件/上游写的说明（`nc` / `n`）**留着但整条标来源**：那条例外明写"串与说明标来源"，
指不出谁写的就不发布；这里能指到 GI 插件与它自报的 foreverdb.net。
不取的东西：插件的 UI 代码、按钮布局、任何"按这个顺序打"的循环提示类建议（红线另有一条）。

用法：
    python3 tools/extract-gi-macros.py [--src ~/Documents/project/.scratch/wow]
产物：app/data/upstream/gi-macros.json
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys

HOME = os.path.expanduser('~')
DEF_SRC = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow')
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(WEB, 'app', 'data', 'upstream', 'gi-macros.json')

GI_FILE = os.path.join('GearInsight_Forever', 'MacroData.lua')
XR_FILE = os.path.join('XR_DungeonGuide', 'Data_Macros.lua')
CLASSES = ['Warrior', 'Paladin', 'Hunter', 'Rogue', 'Priest', 'Shaman', 'Mage', 'Warlock', 'Druid']

STR_RE = re.compile(r'\b(\w+)="((?:[^"\\]|\\.)*)"')
NUM_RE = re.compile(r'\b(\w+)=(-?\d+)')
SPELLS_RE = re.compile(r'spells=\{([^}]*)\}')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def strings(line):
    return dict(STR_RE.findall(line))


def nums(line):
    # findall 交回来的是字符串，不转 int 就会把等级写成带引号的 4，前端一比较就错
    return {k: int(v) for k, v in NUM_RE.findall(line)}


def class_blocks(text, open_re):
    """按职业切段：段内每条宏占一行。返回 [(class, [line, ...]), ...]"""
    marks = []
    for c in CLASSES:
        m = re.search(open_re % c, text)
        if not m:
            raise SystemExit('找不到职业段 %s' % c)
        marks.append((c, m.start()))
    marks.sort(key=lambda x: x[1])
    out = []
    for i, (c, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        seg = text[start:end]
        out.append((c, [ln.strip() for ln in seg.split('\n') if ln.strip().startswith('{')]))
    return out


def parse_gi(text):
    rows = []
    for cls, lines in class_blocks(text, r'\n  %s = \{'):
        for ln in lines:
            if 'key=' not in ln:
                continue
            s, n = strings(ln), nums(ln)
            body = s.get('b')
            spells = [int(x) for x in re.findall(r'\d+', SPELLS_RE.search(ln).group(1))] \
                if SPELLS_RE.search(ln) else []
            rows.append({
                'cls': cls,
                'key': s.get('key'),
                'no': n.get('no'),
                'group': s.get('g'),
                'groupEn': s.get('gEn'),
                'titleEn': s.get('t'),
                'title': s.get('tc'),
                'noteEn': s.get('n'),
                'note': s.get('nc'),
                'bodyTemplate': body,
                'foreverNew': 'fv=true' in ln,
                'level': n.get('lv'),
                'spellIds': spells,
                'spellIdsInBody': [int(x) for x in re.findall(r'\{\{(\d+)\}\}', body or '')],
            })
    return rows


def parse_xr(text):
    rows = []
    for cls, lines in class_blocks(text, r'\n    %s = \{'):
        for ln in lines:
            if not ln.startswith('{g="'):
                continue
            s, n = strings(ln), nums(ln)
            rows.append({'cls': cls, 'group': s.get('g'), 'title': s.get('tc'),
                         'note': s.get('nc'), 'level': n.get('lv'), 'bodyBaked': s.get('b')})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=DEF_SRC)
    args = ap.parse_args()
    gi_path = os.path.join(args.src, GI_FILE)
    xr_path = os.path.join(args.src, XR_FILE)
    for p in (gi_path, xr_path):
        if not os.path.isfile(p):
            sys.exit('找不到源文件：%s' % p)

    gi_text = io.open(gi_path, encoding='utf-8').read()
    xr_text = io.open(xr_path, encoding='utf-8').read()
    gi = parse_gi(gi_text)
    xr = parse_xr(xr_text)

    # 结构核对：两份必须逐条同职业、同标题、同组，否则"烘好的那份"就当不了参照
    if len(gi) != len(xr):
        sys.exit('条数对不上：GI %d / XR %d' % (len(gi), len(xr)))
    mis = [i for i, (a, b) in enumerate(zip(gi, xr))
           if a['cls'] != b['cls'] or a['title'] != b['title'] or a['group'] != b['group']]
    if mis:
        sys.exit('两份不是同一批同顺序（第 %s 条起对不上），不能拿 XR 当烘名参照' % mis[:5])

    # 逐条把 XR 烘好的正文并进去（下一步用它反推本站技能表缺的那批法术名）
    for a, b in zip(gi, xr):
        a['bodyBakedByAddon'] = b['bodyBaked']

    groups = []
    for a in gi:
        if a['group'] not in groups:
            groups.append(a['group'])

    out = {
        'meta': {
            'kind': 'gi-macros',
            'fetchedAt': datetime.date.today().isoformat(),
            'source': 'GearInsight_Forever 0.5.6 + XR_DungeonGuide v87（同一批宏的两个形态）',
            'files': [
                {'path': GI_FILE.replace(os.sep, '/'), 'sha256': sha256(gi_path),
                 'selfReported': '宏来源：foreverdb.net（对过 Beta 1.60.1.70205）+ classicwowforever.com；'
                                 '技能名 → 法术 ID：Beta 1.60.1.70532'},
                {'path': XR_FILE.replace(os.sep, '/'), 'sha256': sha256(xr_path),
                 'selfReported': 'XR_DungeonGuide 全职业宏库 v0.39.0 新增，v66 同步 GI 2026-10-19 新版；'
                                 '宏体内法术名已烘焙为中文'},
            ],
            'licenseNote': '两个插件目录里都没有 LICENSE 文件、TOC 也没有 X-License 行；'
                           '按根 AGENTS.md 2026-10-18「网页端放开清单」第 1 条分享宏文本与说明，'
                           '硬边界是免费 + 标来源 + 不分发插件本体。',
            'alignment': '两份逐条同职业 / 同组 / 同中文标题，条数都是 %d；顺序一致才允许拿 XR 当烘名参照' % len(gi),
            'notTaken': ['插件的界面代码与文案排版', '任何"下一个技能打什么"的循环提示类建议（红线）'],
            'counts': {
                'macros': len(gi),
                'classes': len(set(a['cls'] for a in gi)),
                'groups': len(groups),
                'foreverNew': sum(1 for a in gi if a['foreverNew']),
                'distinctSpellIds': len(set(i for a in gi for i in a['spellIdsInBody'])),
                'spellRefs': sum(len(a['spellIdsInBody']) for a in gi),
            },
        },
        'groups': groups,
        'macros': gi,
    }
    if not os.path.isdir(os.path.dirname(OUT)):
        os.makedirs(os.path.dirname(OUT))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    c = out['meta']['counts']
    print('宏 %d 条 / %d 职业 / %d 个用途分组 / 《无限》新技能 %d 条 / 法术 ID %d 个（引用 %d 次）'
          % (c['macros'], c['classes'], c['groups'], c['foreverNew'], c['distinctSpellIds'], c['spellRefs']))
    print('→', OUT)


if __name__ == '__main__':
    main()
