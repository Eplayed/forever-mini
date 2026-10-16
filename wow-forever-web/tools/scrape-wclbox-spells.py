#!/usr/bin/env python3
# 抓 wowforever.wclbox.com 的九职业法术书（阶段 PRD 的 M1-A：技能从 86 条补到 ≥420）。
#
# 为什么主源是参考站而不是插件：法术的中文名要能逐字回查（10-08 定的"客户端解包中文名算 L0"），
# 参考站的页面就是它从无限测试版客户端读出来的中文；两份插件那边——GI 的名字混了作者/vmangos 口径、
# XR 明写"fc 漏翻的英文描述按内置模板词典翻译"，那是转述与翻译，按红线不能当定名。
# 所以插件在这条线上只当**交叉核对与补字段**（spell id、每级数值行），不当名字来源。
#
# 取什么（全是事实字段）：中文名、图标文件名、所属页签（专精/职业通用）、等级数、起学等级、与经典旧世的状态。
# 不取什么：.fsk-row-text 里那句改动摘要（"第3级：数值不变，描述措辞调整"）和 .fsk-card 里的
#           整段 tooltip 描述——那是它写的句子，红线（照 changes.json 的先例：句子在落盘前就删）。
# 结构（2026-10-16 实测）：一行一个 <button class="fsk-row k-same|k-changed">，
#   <img src="/tubiao/<图标键>.jpg"> + <strong>中文名</strong> +
#   <span class="tfk-tag k-unchanged|k-modified|k-added|k-new"> + <small>页签 · 共N级 · M级起可学</small>
#   （1 级的法术没有"共N级"那一段。）
# 礼貌：9 个页面、单线程、页间 0.5s，gzip；页面静态可取，不用浏览器。
# 用法：python3 tools/scrape-wclbox-spells.py [--out-dir src/data/upstream]
import json
import os
import re
import ssl
import sys
import time
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
# 站内一律用官方中文职业名（与 races/classes 线同一套叫法），别拿参考站的叫法带出第二个口径
CLASSES = [('warrior', '战士'), ('paladin', '圣骑士'), ('hunter', '猎人'), ('rogue', '潜行者'),
           ('priest', '牧师'), ('shaman', '萨满祭司'), ('mage', '法师'), ('warlock', '术士'),
           ('druid', '德鲁伊')]
ROW_RE = re.compile(r'<button class="fsk-row (k-[\w-]+)"[^>]*>(.*?)</button>', re.S)
ICON_RE = re.compile(r'src="/tubiao/([^"/]+)\.jpg"')
NAME_RE = re.compile(r'<strong>(.*?)</strong>', re.S)
TAG_RE = re.compile(r'<span class="tfk-tag (k-[\w-]+)"')
META_RE = re.compile(r'<small>(.*?)</small>', re.S)
# 行上的 class 有两族，别混成一列：
#   与经典旧世的关系 → same / changed / new / removed
#   这条法术的来历   → talent（两边都是天赋技能）/ race（种族技能）/
#                      earlier（比经典更早学会）/ baseline（职业基础技能，没有"共N级"那种）
# 来历不是改动状态，硬塞进四态会把"天赋技能"说成"没变"，所以分开存两个字段。
STATE = {'k-same': 'same', 'k-changed': 'changed', 'k-new': 'new', 'k-removed': 'removed',
         'k-renamed': 'renamed'}
RELATION = {'k-talent': 'talent', 'k-race': 'race', 'k-earlier': 'earlier', 'k-baseline': 'baseline'}
TAG_STATE = {'k-unchanged': 'same', 'k-modified': 'changed', 'k-added': 'new', 'k-new': 'new',
             'k-removed': 'removed', 'k-renamed': 'renamed'}


def strip_tags(s):
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()


def fetch(path):
    req = urllib.request.Request(BASE + path, headers=UA)
    r = urllib.request.urlopen(req, timeout=30, context=CTX)
    raw = r.read()
    if 'gzip' in (r.headers.get('Content-Encoding') or ''):
        raw = gzip.decompress(raw)
    return raw.decode('utf-8', 'replace')


def parse_meta(meta_txt):
    """「武器 · 共9级 · 1级起可学」→ 页签 / 等级数 / 起学等级；缺段就是 None，不猜。"""
    parts = [p.strip() for p in re.split(r'·', meta_txt) if p.strip()]
    tab, ranks, learn = None, None, None
    for p in parts:
        m = re.match(r'^共(\d+)级$', p)
        if m:
            ranks = int(m.group(1))
            continue
        m = re.match(r'^(\d+)级起可学$', p)
        if m:
            learn = int(m.group(1))
            continue
        if tab is None:
            tab = p
    return tab, ranks, learn


def parse_page(html, class_id, class_cn):
    out = []
    for m in ROW_RE.finditer(html):
        seg = m.group(2)
        nm = NAME_RE.search(seg)
        if not nm:
            continue
        name = strip_tags(nm.group(1))
        ic = ICON_RE.search(seg)
        tg = TAG_RE.search(seg)
        mt = META_RE.search(seg)
        tab, ranks, learn = parse_meta(strip_tags(mt.group(1))) if mt else (None, None, None)
        row_state = STATE.get(m.group(1))
        relation = RELATION.get(m.group(1))
        tag_state = TAG_STATE.get(tg.group(1)) if tg else None
        # 行上的 class 与标签里的 class 是两个层级（行=这一条整体状态，标签=对照结论），
        # 不一致时两个都留，不替它圆——两源分歧两个都留是红线
        rec = {'classId': class_id, 'classNameCn': class_cn, 'name': name,
               'iconKey': ic.group(1) if ic else None, 'tab': tab,
               'ranks': ranks if ranks else None, 'learnLevel': learn,
               'state': row_state, 'stateTag': tag_state, 'relation': relation,
               'level': 'L0'}
        if row_state is None and relation is None:
            rec['stateUnknown'] = m.group(1)
        out.append(rec)
    return out


def main():
    out_dir = sys.argv[sys.argv.index('--out-dir') + 1] if '--out-dir' in sys.argv \
        else os.path.join(ROOT, 'src', 'data', 'upstream')
    os.makedirs(out_dir, exist_ok=True)
    spells, per_class, pages = [], {}, {}
    for cid, cname in CLASSES:
        path = '/fashu/' + cid
        html = fetch(path)
        rows = parse_page(html, cid, cname)
        spells.extend(rows)
        per_class[cid] = len(rows)
        pages[cid] = len(html)
        print('  %-8s %3d 条（页面 %d KB）' % (cid, len(rows), len(html) // 1024), flush=True)
        time.sleep(0.5)

    tabs = sorted({s['tab'] for s in spells if s['tab']})
    no_icon = sum(1 for s in spells if not s['iconKey'])
    doc = {
        'meta': {
            'source': BASE + '/fashu/<职业>（九职业法术书，服务端渲染逐页取，共 9 页）',
            'fetched': date.today().isoformat(),
            'counts': {'total': len(spells), 'byClass': per_class, 'noIcon': no_icon},
            'tabs': tabs,
            'states': {k: sum(1 for s in spells if s['state'] == k)
                       for k in ('same', 'changed', 'new', 'removed', 'renamed')},
            'relations': {k: sum(1 for s in spells if s.get('relation') == k)
                          for k in ('talent', 'race', 'earlier', 'baseline')},
            'stateTags': {k: sum(1 for s in spells if s['stateTag'] == k)
                          for k in ('same', 'changed', 'new', 'removed', 'renamed')},
            'droppedFields': ['行内改动摘要句（.fsk-row-text 第二段）',
                              '对照 tooltip 正文（.fsk-card 经典/无限两栏）'],
            'note': '中文名与图标文件名取自参考站对无限测试版客户端的转述（按 2026-10-08 的定档算 L0，'
                    '逐字回查用 tools/audit-translations.py）；状态两个层级都留，不一致不圆。',
        },
        'spells': spells,
    }
    p = os.path.join(out_dir, 'wclbox-spells.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('写 %s：%d 条 / %d 职业 · 无图标 %d · 页签 %d 种'
          % (p, len(spells), len(per_class), no_icon, len(tabs)))


if __name__ == '__main__':
    main()
