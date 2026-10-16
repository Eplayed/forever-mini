#!/usr/bin/env python3
# 取参考站的成就批量端点 /_shuju/<发布号>/chengjiu.json（M1-B）。
#
# 为什么先要它：成就的中文名要能逐字回查才算 L0（2026-10-08 定的档）。插件那份 GI achievements
# 有 211 条、覆盖比这个端点大得多，但只有这一家说的我们没法自动回查；
# 这个端点只有 46 条（区域探索一类），**能回查的那 46 条才升 L0**，其余 165 条停在 L1 待回查。
#
# 落什么：id、分类、名字、图标文件名、是否无限新增、子成就条数与子成就 id。
# 不落什么（红线）：`text`（成就描述整句）与 `criteria[].text`（子条件说明句）——
# 落盘前就删，照 changes.json 的先例，别指望"界面上不显示"。
# 发布号从 /chengjiu 页面现读，不写死（它随上游发版变）。
# 用法：python3 tools/scrape-wclbox-achievements.py [--out-dir src/data/upstream]
import json
import os
import re
import ssl
import sys
import urllib.request
import gzip
from datetime import date

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl._create_unverified_context()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://wowforever.wclbox.com'
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/126.0 Safari/537.36',
      'Accept-Encoding': 'gzip'}
BUILD_RE = re.compile(r'/_shuju/([a-z0-9.\-]+)/')


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30, context=CTX)
    raw = r.read()
    if 'gzip' in (r.headers.get('Content-Encoding') or ''):
        raw = gzip.decompress(raw)
    return raw.decode('utf-8', 'replace')


def main():
    out_dir = sys.argv[sys.argv.index('--out-dir') + 1] if '--out-dir' in sys.argv \
        else os.path.join(ROOT, 'src', 'data', 'upstream')
    os.makedirs(out_dir, exist_ok=True)
    page = get(BASE + '/chengjiu')
    m = BUILD_RE.search(page)
    if not m:
        sys.exit('没在 /chengjiu 页面里找到 _shuju 发布号，上游可能改了目录结构')
    build_dir = m.group(1)
    data = json.loads(get('%s/_shuju/%s/chengjiu.json' % (BASE, build_dir)))
    items = []
    for x in data.get('items') or []:
        crit = x.get('criteria') or []
        items.append({'achId': x.get('id'), 'category': x.get('category'), 'name': x.get('name'),
                      'iconKey': x.get('icon'), 'forever': x.get('forever'),
                      'criteriaCount': len(crit),
                      'criteriaAchievements': sorted({c.get('achievement') for c in crit
                                                      if c.get('achievement')})})
    doc = {
        'meta': {
            'source': BASE + '/_shuju/%s/chengjiu.json' % build_dir,
            'page': BASE + '/chengjiu',
            'fetched': date.today().isoformat(),
            'upstreamBuild': data.get('build'),
            'counts': {'total': len(items), 'forever': sum(1 for x in items if x.get('forever')),
                       'withCriteria': sum(1 for x in items if x['criteriaCount'])},
            'categories': data.get('categories'),
            'droppedFields': ['text（成就描述整句）', 'criteria[].text（子条件说明句）'],
            'note': '这一份只覆盖区域探索一类（46 条），但它是能逐字回查的客户端解包转述；'
                    '插件那份 211 条里只有对得上这里的才升 L0。',
        },
        'achievements': items,
    }
    p = os.path.join(out_dir, 'wclbox-achievements.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('成就端点：%d 条（无限新增 %d · 带子条件 %d）·上游 build %s → %s'
          % (len(items), doc['meta']['counts']['forever'], doc['meta']['counts']['withCriteria'],
             data.get('build'), os.path.relpath(p, ROOT)))


if __name__ == '__main__':
    main()
