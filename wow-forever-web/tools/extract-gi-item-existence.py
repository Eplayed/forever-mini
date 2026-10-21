#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 GearInsight_Forever/ItemMissingData.lua 抽「这件物品在无限测试服上有没有」这一层。

为什么值得单独一层：本站物品名录 21,077 件是从参考站的全量索引来的，里面混着
"经典旧世有、无限服根本没做"的东西。玩家问的其实就一句——**这件我能不能搞到**。
以前我们只有参考站自报的 status（missing 1,944 件）一条腿。

这一份是**第二个独立来源**：GI 作者 2026-10-19 用 `/gi itemprobe all` 在测试服逐件探过，
产出两个集合——`ItemMissingIds`（服务器上查不到）与 `ItemRecommendIds`（确认掉过 ∪ 探针确认有）。
两边不重叠（作者口径就是"推荐只用确认有的"）。

对账结果（这次实测，写进 meta 免得下次重新数）：
  GI 说没有的 793 件，参考站也全部标 missing —— **没有一件是"GI 说没有、参考站说有"的正向冲突**；
  反过来有 82 件参考站标 missing、GI 却列进"确认服务器有" —— **这是唯一的反向分歧**，
  所以这一层不覆盖 status，只并排存着，界面上按站主 2026-10-20 定的"以插件为准"显示 srv，
  分歧数留在数据与溯源页。

只取 ID 集合这一层事实，作者写的注释与推荐逻辑不取。
用法：python3 tools/extract-gi-item-existence.py [--src <插件根目录>]
产物：src/data/upstream/gi-item-existence.json
幂等：同输入字节一致。
"""
import hashlib
import io
import json
import os
import re
import sys
from datetime import date

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_SRC = os.path.join(os.path.dirname(os.path.dirname(WEB)), '.scratch', 'wow-client-2026-10-21')
UP = os.path.join(WEB, 'src', 'data', 'upstream')


def toc_version(addon_dir):
    try:
        s = io.open(os.path.join(addon_dir, 'GearInsight_Forever.toc'), encoding='utf-8',
                    errors='replace').read()
    except OSError:
        return '未知'
    m = re.search(r'^##\s*Version:\s*([0-9.]+)', s, re.M)
    return m.group(1) if m else '未知'


def parse(path):
    """ns.ItemMissingIds = {[862]=true, ...} 两段，各扫一次。"""
    s = io.open(path, encoding='utf-8', errors='replace').read()
    out = {}
    for name in ('ItemMissingIds', 'ItemRecommendIds'):
        m = re.search(r'ns\.' + name + r'\s*=\s*\{(.*?)\}', s, re.S)
        if not m:
            sys.exit('找不到 ns.%s —— 文件结构变了，先看原文再改这里，别静默出空表' % name)
        out[name] = sorted({int(x) for x in re.findall(r'\[(\d+)\]\s*=\s*true', m.group(1))})
    return out


def main():
    src = DEF_SRC
    if '--src' in sys.argv:
        src = sys.argv[sys.argv.index('--src') + 1]
    p = os.path.join(src, 'GearInsight_Forever', 'ItemMissingData.lua')
    if not os.path.exists(p):
        sys.exit('找不到 %s' % p)
    blob = open(p, 'rb').read()
    got = parse(p)
    items = json.load(io.open(os.path.join(WEB, 'src', 'data', 'items.json'), encoding='utf-8'))['items']
    by = {int(x['id']): x.get('status') for x in items}
    miss, rec = set(got['ItemMissingIds']), set(got['ItemRecommendIds'])
    audit = {
        'roster': len(by),
        'giMissingInRoster': len(miss & set(by)),
        'giPresentInRoster': len(rec & set(by)),
        'agreeMissing': len({i for i in miss if by.get(i) == 'missing'}),
        'conflictGiSaysMissingOtherSaysHas': len({i for i in miss if i in by and by[i] != 'missing'}),
        'conflictGiSaysHasOtherSaysMissing': len({i for i in rec if by.get(i) == 'missing'}),
        'giIdsNotInOurRoster': len(miss - set(by)),
    }
    doc = {'meta': {
        'source': 'GearInsight_Forever/ItemMissingData.lua（作者自述：scripts/gi_forever_item_exist_import.py，'
                  '/gi itemprobe all 于 2026-10-19 00:01:38 在测试服实测生成）',
        'addon': 'GearInsight_Forever', 'addonVersion': toc_version(os.path.join(src, 'GearInsight_Forever')),
        'sourceFile': os.path.relpath(p, os.path.join(WEB, '..', '..')),
        'sourceStamp': {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
                        'fileDate': date.fromtimestamp(os.path.getmtime(p)).isoformat()},
        'probedAt': '2026-10-19',
        'extractedAt': date.today().isoformat(),
        'levelPolicy': '作者单源实测，本站没进游戏复验 → 按 L1 留档，不自动升 L0',
        'takes': '只有两个物品 ID 集合；作者的推荐规则与注释不取',
        'audit': audit,
        'counts': {'missing': len(miss), 'present': len(rec)}},
        'missing': sorted(miss), 'present': sorted(rec)}
    os.makedirs(UP, exist_ok=True)
    out = os.path.join(UP, 'gi-item-existence.json')
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    print('物品存在性 → %s（GI 说没有 %d / 确认有 %d；与本站名录对账：一致 missing %d、'
          '正向冲突 %d、反向冲突 %d）' % (os.path.relpath(out, WEB), len(miss), len(rec),
              audit['agreeMissing'], audit['conflictGiSaysMissingOtherSaysHas'],
              audit['conflictGiSaysHasOtherSaysMissing']))


if __name__ == '__main__':
    main()
