#!/usr/bin/env python3
# wclbox 物品详情页试采（物品线二批方案 B 的评估步，站主 2026-10-14 拍板：先试 200 件再定全量）。
# 只抽事实性字段：中英名/品质/部位/类型/装等/需要等级/绑定/属性行/售价/来源 NPC/客户端 build。
# 礼貌间隔 0.5s；失败逐件记录不中断。不做全量——评估结论出来前不扩。
# 用法：python3 tools/scrape-wclbox-items-detail.py [--count 200]
# 产物：src/data/upstream/wclbox-items-detail-sample.json
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import date

# Mac 的 Python urllib 常缺系统 CA（CERTIFICATE_VERIFY_FAILED），优先 certifi
try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl._create_unverified_context()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'src', 'data')
BASE = 'https://wowforever.wclbox.com/wupin/'
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'}


def visible_lines(html):
    h = re.sub(r'<(script|style)[\s\S]*?</\1>', ' ', html, flags=re.I)
    txt = re.sub(r'<[^>]+>', '\n', h)
    return [l.strip() for l in txt.split('\n') if l.strip()]


def parse_page(html, item_id):
    lines = visible_lines(html)
    rec = {'url': BASE + str(item_id)}
    # 摘要行：精良，颈部，其它，物品等级 18，需要等级 13，物品 270227
    summ = None
    for l in lines:
        if ('物品 %d' % item_id) in l and '物品等级' in l:
            summ = l
            break
    if summ:
        m = re.match(r'([^，]+)，([^，]+)，([^，]+)，物品等级 (\d+)(?:，需要等级 (\d+))?，物品 \d+', summ)
        if m:
            rec['quality'], rec['slot'], rec['type'] = m.group(1), m.group(2), m.group(3)
            rec['ilvl'] = int(m.group(4))
            rec['reqLevel'] = int(m.group(5)) if m.group(5) else None
    # 中英名：摘要行前面最近的两行同名 + 英文名
    if summ:
        si = lines.index(summ)
        if si >= 3:
            rec['nameCn'] = lines[si - 3]
            rec['nameEn'] = lines[si - 1] if lines[si - 1] != '，' else None
    # 版本与状态说明
    for l in lines:
        mb = re.match(r'无限测试版 (\d+\.\d+\.\d+\.\d+)', l)
        if mb:
            rec['build'] = mb.group(1)
        if l.startswith('无限新增'):
            rec['statusNote'] = '无限新增'
        elif '经典怀旧服的客户端里没有' in l and '无限' not in l:
            rec['statusNote'] = '经典旧世没有'
    # 来源 NPC：「来源：」的下一行
    for i, l in enumerate(lines):
        if l == '来源：' and i + 1 < len(lines):
            rec['srcNpc'] = lines[i + 1]
            break
    # tooltip 属性行：绑定行之后、需要等级行之前的非噪音行；售价行
    sell = None
    st, st_on = [], False
    for l in lines:
        if l.startswith('售价：'):
            sell = l[3:]
            st_on = False
            continue
        if re.match(r'^(拾取后绑定|装备后绑定)$', l):
            rec['bind'] = l
            st_on = True
            continue
        if st_on and l.startswith('需要等级'):
            continue
        if st_on and summ and l != summ and l != rec.get('slot') and l != rec.get('nameCn') \
                and not l.startswith('物品等级') and l not in ('· 物品', str(item_id)):
            st.append(l)
    if sell:
        rec['sell'] = sell
    if st:
        rec['st'] = st
    return rec if len(rec) > 1 else None


def main():
    count = int(sys.argv[sys.argv.index('--count') + 1]) if '--count' in sys.argv else 200
    items = json.load(open(os.path.join(D, 'items.json'), encoding='utf-8'))['items']
    step = max(1, len(items) // count)
    sample = [items[i] for i in range(0, len(items), step)][:count]
    out, fails = {}, []
    for n, x in enumerate(sample):
        url = BASE + str(x['id'])
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                html = r.read().decode('utf-8', 'replace')
            rec = parse_page(html, x['id'])
            if rec:
                out[str(x['id'])] = rec
            else:
                fails.append((x['id'], '结构没认出来'))
        except Exception as e:
            fails.append((x['id'], str(e)[:80]))
        time.sleep(0.5)
        if (n + 1) % 25 == 0:
            print('  %d/%d（成 %d 败 %d）' % (n + 1, len(sample), len(out), len(fails)))
    builds = sorted({r.get('build') for r in out.values() if r.get('build')})
    doc = {
        'meta': {
            'source': 'wowforever.wclbox.com /wupin/<id>（物品详情页 SSR 试采 ' + str(len(sample)) + ' 件，'
                      '分层抽样跨全名录；方案 B 评估用，不是全量）',
            'fetched': date.today().isoformat(),
            'builds': builds,
            'counts': {'total': len(out), 'st': sum(1 for r in out.values() if r.get('st')),
                       'sell': sum(1 for r in out.values() if r.get('sell')),
                       'srcNpc': sum(1 for r in out.values() if r.get('srcNpc')),
                       'failed': len(fails)},
            'fails': fails[:50],
            'note': '试采样本；全量抓取与否等评估结论（docs/ITEMS-DETAIL-SOURCE-EVAL-2026-10-14.md）。',
        },
        'items': {k: out[k] for k in sorted(out, key=int)},
    }
    p = os.path.join(D, 'upstream', 'wclbox-items-detail-sample.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('写 %s：%d/%d 件成功（属性 %d / 卖价 %d / 来源 %d）·build %s'
          % (os.path.relpath(p), len(out), len(sample), doc['meta']['counts']['st'],
             doc['meta']['counts']['sell'], doc['meta']['counts']['srcNpc'], builds))


if __name__ == '__main__':
    main()
