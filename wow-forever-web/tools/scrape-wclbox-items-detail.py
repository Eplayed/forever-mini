#!/usr/bin/env python3
# wclbox 物品详情页抓取（物品线二批 W2-3：2026-10-15 站主拍板"按评估建议现在跑一轮垫底"，全量）。
#
# 这份是试采版（同路径、2026-10-14 提交）改成全量后的正式工具。换掉的不只是数量，解析也重写了——
# 试采那版按"可见文本行"的位置取数，实测四处硬伤，全量落地时每一个都会变成脏数据：
#   1) 每件物品页面里是**两块对照 tooltip**（.wp-pair 下两个 .wp-tip：经典怀旧服 / 无限测试版），
#      按行位置扫会把两边扫成一串——评估文档里"双方都有属性的 106 件行集 100% 不一致"就是这么来的；
#   2) 名称取行会错位（争战手套那类取到「›」），所以这份**不取名**，名称一律以 items.json 名录为准；
#   3) 来源那一节是 <p class="wp-drops">，写成 div 去匹配就一条都取不到（第一版就这么漏空的）；
#   4) 页面自报状态其实有**五种**：同 / 有改动 / 无限新增 / 无限中没有 / 保留了数据行但没有属性
#      （held）。后两种页面摆的是经典侧提示框，抓下来只留痕，不许当无限的数值用。
#   5) tooltip 里的风味引句（.wp-flavor，例："血色十字军领袖之剑"）会被当属性行收进来——那是描述
#      文案，红线不许进正文，抓取阶段就丢掉，不留到合并。
# 这版按 DOM 类名取：.wp-label 说清每块是哪个客户端（带 build 号），.wp-line 行级的 wp-add / wp-del
# 就是页面自己标的"两个客户端不一样的地方"；无限侧整条留（含 wp-green 效果行，与 GI/XR 里
# "装备：…"同类），经典侧只留被改动的那几行，部位/类型这类说明行不重复进属性里。
#
# 字段全是事实性的：品质/部位/类型/装等/需要等级/绑定/属性行/售价/来源 NPC 与区域/build。
# 红线：不取描述正文、不取攻略、不取掉率（掉落归属那层只在 upstream 里，不进成品，见合并脚本）。
# 礼貌：单线程、逐件 0.5s，与试采一致；Accept-Encoding: gzip 让每页 76 KB 降到 15 KB，少占对方带宽。
# 可续跑：逐件 flush 到 partial.jsonl（系统临时目录），中断后重跑自动跳过已抓的；汇总段从
#   partial.jsonl 重建，重跑字节一致。21,077 件实测约 3.7 小时（1.59 件/秒）。
# 用法：python3 tools/scrape-wclbox-items-detail.py            # 全量（默认）
#       python3 tools/scrape-wclbox-items-detail.py --limit 50  # 小批试跑
#       python3 tools/scrape-wclbox-items-detail.py --sample 200  # 等步长抽样（只当校准，别覆盖历史试采样本）
# 产物：src/data/upstream/wclbox-items-detail.json

import json
import os
import re
import ssl
import sys
import time
import tempfile
import urllib.request
import gzip
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'src', 'data')

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl._create_unverified_context()

BASE = 'https://wowforever.wclbox.com/wupin/'
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/126.0 Safari/537.36',
      'Accept-Encoding': 'gzip'}
BIND_RE = re.compile(r'^(拾取后绑定|装备后绑定|账号绑定)$')
# 客户端把教益句也放在斜体风味框里（.wp-flavor），一刀切按类名丢会让 1,197 件图样/秘典
# 只剩"需要工程学 (125)"这种行。这里按内容把它捞出来单独进 use，纯风味句仍然丢。
USE_RE = re.compile(r'教你|学会|可启动')
PRICE_RE = re.compile(r'^售价：(.+)$')
REQ_RE = re.compile(r'^需要等级')
SUB_RE = re.compile(r'([\u4e00-\u9fff]{1,8})，([\u4e00-\u9fff]{1,10})，([^，]{1,16})，物品等级')
STATUS_MAP = {'wp-status-new': 'new', 'wp-status-changed': 'changed',
              'wp-status-same': 'same', 'wp-status-missing': 'missing',
              # 第五种：客户端保留了这件的数据行但没有属性，页面这时显示的是经典侧提示框——
              # 和 missing 一样不能当无限的数用，合并阶段一律排除
              'wp-status-held': 'held'}
# 对照客户端的 build 号全量只有一个，不逐件存，汇总时进 meta
SEEN = {'classicBuilds': set()}


def strip_tags(s):
    s = re.sub(r'<!--\s*-->', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def attr_of(tag, name):
    m = re.search(r'\b%s="([^"]*)"' % name, tag)
    return m.group(1) if m else ''


def lines_of(block):
    """一段 tooltip 的 HTML → [{t, k, parts}]；k 收 add/del/green/flavor/muted/unique，普通行不给 k。
    parts 是行内各 <span> 的文本：tooltip 里"58 - 108 点伤害 / 速度 2.10"这类本来就是两栏，
    拆开后与 GI/XR 现有 st 的写法一致（"17 - 33 伤害"、"速度 1.30" 各一条）。"""
    out = []
    for m in re.finditer(r'<div class="(wp-line[^"]*)"[^>]*>(.*?)</div>', block, re.S):
        cls, inner = m.group(1), m.group(2)
        text = strip_tags(inner)
        if not text:
            continue
        spans = [strip_tags(s) for s in re.findall(r'<span[^>]*>(.*?)</span>', inner, re.S)]
        spans = [s for s in spans if s]
        kind = []
        if 'wp-add' in cls:
            kind.append('add')
        if 'wp-del' in cls:
            kind.append('del')
        if 'wp-green' in cls:
            kind.append('green')
        if 'wp-flavor' in cls:
            kind.append('flavor')
        if 'wp-muted' in cls:
            kind.append('muted')
        out.append({'t': text, 'k': ' '.join(kind) or 'plain',
                    'parts': spans if len(spans) > 1 else [text]})
    return out


def allowed_desc(rec):
    """部位/类型这类"说明行"的词表：站内的 slot/type 已在独立字段里，st 里不重复摆。"""
    words = set()
    for v in (rec.get('slot'), rec.get('type'), rec.get('quality')):
        if v:
            words.add(v)
    for w in ('主手', '副手', '双手', '单手', '远程', '投掷', '持握'):
        words.add(w)
    for w in ('布甲', '皮甲', '锁甲', '链甲', '板甲', '盾', '匕首'):
        words.add(w)
    t = rec.get('type') or ''
    for pre in ('单手', '双手', '轻型', '重型'):
        if t.startswith(pre) and len(t) > len(pre):
            words.add(pre)
            words.add(t[len(pre):])
    return words


def fold(lines, words):
    """整段 tooltip → 可入库的属性行 + 售价 + 绑定 + 需要等级。
    丢掉的：风味引句（红线）、说明行（部位/类型已有独立字段）、需要等级（独立字段）、售价（独立字段）。"""
    st, sell, bind, req, add, use = [], None, None, None, [], None
    for x in lines:
        k = x['k']
        if 'flavor' in k:
            inner = x['t'].strip().strip('“”"')
            if USE_RE.search(inner):
                use = use or inner
            continue
        m = PRICE_RE.match(x['t'])
        if m:
            sell = m.group(1)
            continue
        if BIND_RE.match(x['t']):
            bind = x['t']
            continue
        if REQ_RE.match(x['t']):
            mr = re.search(r'(\d+)', x['t'])
            req = int(mr.group(1)) if mr else None
            continue
        parts = x['parts']
        if all(p in words for p in parts):
            continue
        for p in parts:
            st.append(p)
            if 'add' in k:
                add.append(p)
    return {'st': st, 'sell': sell, 'bind': bind, 'reqLevel': req, 'add': add, 'use': use}


def parse(html, item_id):
    main_i = html.find('<main')
    if main_i < 0:
        return None
    main = html[main_i:html.find('</main>') if html.find('</main>') > 0 else len(html)]
    head = re.search(r'<h1 class="(q\d)"[^>]*>(.*?)</h1>', main, re.S)
    if not head:
        return None
    rec = {'qClass': head.group(1)}
    meta = re.search(r'<div class="wp-meta"[^>]*>(.*?)</div>', main, re.S)
    if meta:
        mi = re.search(r'物品等级\s*(\d+)', strip_tags(meta.group(1)))
        if mi:
            rec['ilvlDetail'] = int(mi.group(1))
    sub = re.search(r'<p class="wp-sub"[^>]*>(.*?)</p>', main, re.S)
    if sub:
        m = SUB_RE.search(strip_tags(sub.group(1)))
        if m:
            rec['quality'], rec['slot'], rec['type'] = m.group(1), m.group(2), m.group(3)
    ver = re.search(r'<p class="(wp-verdict[^"]*)"[^>]*>(.*?)</p>', main, re.S)
    if ver:
        cls, txt = ver.group(1), strip_tags(ver.group(2))
        for key, val in STATUS_MAP.items():
            if key in cls:
                rec['status'] = val
        m = re.search(r'经典旧世中的名称是[“"]([^”"]+)[”"]', txt)
        if m:
            rec['classicName'] = m.group(1)
    # 来源那一节是 <p class="wp-drops">，不是 div；原来多锚了一个尾邻接条件，一条都没命中过
    src = re.search(r'<(p|div) class="wp-drops"[^>]*>(.*?)</\1>', main, re.S)
    if src:
        txt = strip_tags(src.group(2))
        if txt.startswith('来源：'):
            parts = [p.strip() for p in txt[3:].replace('，', ',').split(',') if p.strip()]
            if parts:
                rec['srcNpc'] = parts[0]
                if len(parts) > 1:
                    rec['srcZone'] = parts[1]
    # 两块对照：按 .wp-label 切，标签文本自带客户端与 build 号
    pair_i = main.find('wp-pair')
    sides = []
    if pair_i >= 0:
        pair = main[pair_i:]
        for m in re.finditer(r'<div class="wp-label"[^>]*>(.*?)</div>', pair, re.S):
            sides.append((strip_tags(m.group(1)), m.end()))
        blocks = []
        for i, (label, pos) in enumerate(sides):
            end = sides[i + 1][1] - 40 if i + 1 < len(sides) else len(pair)
            blocks.append((label, pair[pos:end]))
        for label, block in blocks:
            mb = re.match(r'(\S+)\s+(\d+\.\d+\.\d+\.\d+)', label)
            who, build = (mb.group(1), mb.group(2)) if mb else (label, None)
            lines = lines_of(block)
            if '无限' in who:
                rec['build'] = build
                rec['fvLines'] = lines
            elif '经典' in who:
                rec['classicBuild'] = build
                rec['clLines'] = lines
    fv = rec.pop('fvLines', [])
    cl = rec.pop('clLines', [])
    f = fold(fv, allowed_desc(rec))
    if f['st']:
        rec['st'] = f['st']
    if f['sell']:
        rec['sell'] = f['sell']
    if f['bind']:
        rec['bind'] = f['bind']
    if f['reqLevel'] is not None:
        rec['reqLevelDetail'] = f['reqLevel']
    if f['add']:
        rec['foreverDiff'] = f['add']
    if f.get('use'):
        rec['use'] = f['use']
    cdel = [p for x in cl if 'del' in x['k'] and 'flavor' not in x['k'] for p in x['parts']]
    if cdel:
        rec['classicDiff'] = cdel
    if rec.get('status') in ('missing', 'held'):
        # 这两类页面摆的是经典侧的提示框，抓下来只为留痕，合并时不许当无限的数值用
        rec['tipIsClassic'] = True
    cb = rec.pop('classicBuild', None)
    if cb:
        SEEN['classicBuilds'].add(cb)
    return rec if rec.get('build') else None


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    items_p = arg('--items', os.path.join(DATA, 'items.json'))
    ck_p = arg('--ck', os.path.join(tempfile.gettempdir(), 'wclbox-items-detail.partial.jsonl'))
    out_p = arg('--out', os.path.join(DATA, 'upstream', 'wclbox-items-detail.json'))
    limit = int(arg('--limit', '0'))
    sleep_s = float(arg('--sleep', '0.5'))

    ids = [int(x['id']) for x in json.load(open(items_p, encoding='utf-8'))['items']]
    done = {}
    if os.path.exists(ck_p):
        with open(ck_p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                done[str(r['id'])] = r
    todo = [i for i in ids if str(i) not in done]
    sample = int(arg('--sample', '0'))
    if sample:
        step = max(1, len(todo) // sample)
        todo = todo[::step][:sample]
    if limit:
        todo = todo[:limit]
    print('全量 %d 件：已有 %d，本轮待抓 %d（间隔 %ss）' % (len(ids), len(done), len(todo), sleep_s), flush=True)

    ck = open(ck_p, 'a', encoding='utf-8', newline='\n')
    ok = fail = 0
    t0 = time.time()
    for n, i in enumerate(todo):
        rec = None
        err = None
        for attempt in range(2):
            try:
                req = urllib.request.Request(BASE + str(i), headers=UA)
                r = urllib.request.urlopen(req, timeout=25, context=CTX)
                raw = r.read()
                enc = r.headers.get('Content-Encoding') or ''
                html = gzip.decompress(raw).decode('utf-8', 'replace') if 'gzip' in enc else raw.decode('utf-8', 'replace')
                rec = parse(html, i)
                if rec:
                    err = None
                    break
                err = '结构没认出来'
            except Exception as e:
                err = str(e)[:120]
            time.sleep(2.0 if attempt == 0 else sleep_s)
        line = {'id': i, 'at': date.today().isoformat()}
        if rec:
            line['rec'] = rec
            ok += 1
        else:
            line['err'] = err
            fail += 1
        ck.write(json.dumps(line, ensure_ascii=False) + '\n')
        ck.flush()
        time.sleep(sleep_s)
        if (n + 1) % 200 == 0:
            sp = (n + 1) / max(1.0, time.time() - t0)
            print('  %d/%d（成 %d 败 %d）%.2f 件/秒 · 约剩 %.0f 分钟'
                  % (n + 1, len(todo), ok, fail, sp, (len(todo) - n - 1) / max(0.01, sp) / 60.0), flush=True)
    ck.close()
    print('本轮完成：成 %d 败 %d，用时 %.1f 分钟' % (ok, fail, (time.time() - t0) / 60.0), flush=True)

    out = {}
    fails = []
    with open(ck_p, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            k = str(r['id'])
            if r.get('rec'):
                out[k] = r['rec']
            elif k not in out:
                fails.append([r['id'], r.get('err', '')])
    builds = sorted({x.get('build') for x in out.values() if x.get('build')})
    doc = {
        'meta': {
            'source': 'wowforever.wclbox.com /wupin/<id>（物品详情页 SSR 全量，逐件抓取；无限侧 tooltip 整条，经典侧只留改动行）',
            'url': 'https://wowforever.wclbox.com/wupin/',
            'fetched': date.today().isoformat(),
            'builds': builds,
            'counts': {'total': len(out),
                       'st': sum(1 for x in out.values() if x.get('st')),
                       'sell': sum(1 for x in out.values() if x.get('sell')),
                       'use': sum(1 for x in out.values() if x.get('use')),
                       'srcNpc': sum(1 for x in out.values() if x.get('srcNpc')),
                       'changed': sum(1 for x in out.values() if x.get('status') == 'changed'),
                       'new': sum(1 for x in out.values() if x.get('status') == 'new'),
                       'missing': sum(1 for x in out.values() if x.get('status') == 'missing'),
                       'missing': sum(1 for x in out.values() if x.get('status') == 'missing'),
                       'held': sum(1 for x in out.values() if x.get('status') == 'held'),
                       'srcZone': sum(1 for x in out.values() if x.get('srcZone')),
                       'failed': len(fails)},
            'classicBuilds': sorted(SEEN['classicBuilds']),
            'fails': fails[:200],
            'note': '全量快照；无限侧整条属性留（含效果行），经典侧只留被改动的行；'
                    '风味引句抓取时即丢弃（红线：不复制描述文案）。'
                    '自报状态 missing / held 的那些件，页面摆的是经典侧提示框（记录带 tipIsClassic），'
                    '合并时不许当无限的数值用。'
                    '评估见 docs/ITEMS-DETAIL-SOURCE-EVAL-2026-10-14.md。',
        },
        'items': {k: out[k] for k in sorted(out, key=int)},
    }
    with open(out_p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    c = doc['meta']['counts']
    print('写 %s：%d 件（属性 %d / 卖价 %d / 来源 %d · 有改动 %d · 无限新增 %d）·build %s'
          % (out_p, c['total'], c['st'], c['sell'], c['srcNpc'], c['changed'], c['new'], builds), flush=True)


if __name__ == '__main__':
    main()
