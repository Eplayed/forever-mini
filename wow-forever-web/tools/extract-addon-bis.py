#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 XR_DungeonGuide 的 Data_Bis.lua 抽成 upstream/xr-bis.json（第二家 BiS 名单的原料快照）。

为什么要自己写解析器，而不是直接用别人已经转好的 JSON：
  本站的规矩是"原料快照要能从手上的文件复算"。别人转的那一份我们核过哈希能用，
  但解析规则不是我们的，将来对账时说不清哪一层出的错。这里 130 行自己解析，
  跑一次几秒，重跑字节一致。

取什么（红线 2026-10-16 例外条款点名的那几类事实字段）：
  职业 slug / 职业中文名 / 专精 id 与名 / 部位 / 阵营侧 / 排名顺序 / 物品 ID / 品质 /
  插件里带的中文名 / 来源的**类型标签**（src.t，如 other、drop、craft）。
**不取什么**：src.note —— 那是别人写的成段中文说明（"世界掉落，可在拍卖行购买 掉落时从36种
随机属性中抽出一种…"），红线明写不复制第三方描述文案。"这件从哪拿"由合并阶段回我们自己的
items-detail.json 查，不抄它的句子。

一条必须写进快照的诚实边界：
  这份数据作者声明抓自 foreverchanges.pro/zh-cn/bis，而我们现有 bis.json 抓自
  wowforever.wclbox.com/peizhuang。**两个是不同的站，名单也确实不同**（战士 PvE 12 个部位里
  4 个首选不同；全量物品交集 371/609），但**"两家没有共同上游"我们证明不了**——
  所以这里只叫它"第二份名单"，不叫"第二家独立来源"，合并与卡口都按这个口径写。

用法：
    python3 tools/extract-addon-bis.py                 # 抽 + 写 upstream/xr-bis.json
    python3 tools/extract-addon-bis.py --check-only    # 只解析并打印规模，不落盘
"""
from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
# 插件装在仓库外（不进 git）：…/project/.scratch/wow/，比仓库根再往上一层
SCRATCH = os.path.join(os.path.dirname(REPO), ".scratch", "wow")
SRC = os.path.join(SCRATCH, "XR_DungeonGuide", "Data_Bis.lua")
OUT = os.path.join(ROOT, "app", "data", "upstream", "xr-bis.json")

# 2026-10-22 与 ai_data 包内核对：本地 XR 66 这一份与包内那份字节相同（sha256 前 16 位一致），
# 所以 BiS 这一件不受"本地 66 / 包出自 75"那个版本问题影响。钉住它，换了就要重新核过再改。
PINNED_SHA256_16 = "2c6c296fea1d8cab"

DECLARED_ORIGIN = "foreverchanges.pro/zh-cn/bis（38 页，作者声明 2026-10-16 重抓）"

IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


class LuaError(Exception):
    pass


def parse_lua_table(text, pos=0):
    """递归下降解析一个 Lua 表字面量。返回 (value, next_pos)。"""
    n = len(text)

    def skip(i):
        while i < n:
            c = text[i]
            if c in ' \t\r\n':
                i += 1
            elif text.startswith('--[', i):          # 块注释 --[[ ... ]]
                j = text.find(']]', i)
                if j < 0:
                    raise LuaError('未闭合的块注释')
                i = j + 2
            elif text.startswith('--', i):           # 行注释
                j = text.find('\n', i)
                i = n if j < 0 else j + 1
            else:
                return i

    def value(i):
        i = skip(i)
        if i >= n:
            raise LuaError('内容提前结束')
        c = text[i]
        if c == '{':
            return table(i + 1)
        if c in '"\'':
            return string(i, c)
        m = re.match(r'-?\d+(\.\d+)?([eE][-+]?\d+)?', text[i:])
        if m:
            raw = m.group(0)
            v = float(raw) if ('.' in raw or 'e' in raw.lower()) else int(raw)
            return v, i + len(raw)
        m = IDENT.match(text, i)
        if m:
            w = m.group(0)
            if w in ('true', 'false'):
                return w == 'true', m.end()
            if w == 'nil':
                return None, m.end()
            raise LuaError('出现裸标识符当值（不是合法数据）：%s @%d' % (w, i))
        raise LuaError('不认识的起始字符 %r @%d' % (c, i))

    def string(i, q):
        out = []
        i += 1
        while i < n:
            c = text[i]
            if c == '\\':
                nxt = text[i + 1]
                esc = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                       '"': '"', "'": "'", '/': '/'}.get(nxt)
                if esc is None and nxt.isdigit():
                    j = i + 1
                    digits = ''
                    while j < n and text[j].isdigit() and len(digits) < 3:
                        digits += text[j]
                        j += 1
                    out.append(chr(int(digits)))
                    i = j
                    continue
                if esc is None:
                    raise LuaError('不支持的转义 \\%s @%d' % (nxt, i))
                out.append(esc)
                i += 2
                continue
            if c == q:
                return ''.join(out), i + 1
            out.append(c)
            i += 1
        raise LuaError('字符串未闭合')

    def table(i):
        arr = []
        dct = {}
        keys_seen = False
        while True:
            i = skip(i)
            if i >= n:
                raise LuaError('表未闭合')
            if text[i] == '}':
                if keys_seen:
                    return dct, i + 1
                return arr, i + 1
            key = None
            if text[i] == '[':
                j = i + 1
                if j < n and text[j] == '[':
                    raise LuaError('[[[ 型键不支持')
                k, j = value(j)
                j = skip(j)
                if j >= n or text[j] != ']':
                    raise LuaError('] 缺失 @%d' % j)
                key = k
                i = skip(j + 1)
                if i < n and text[i] == '=':
                    i = skip(i + 1)
                else:
                    raise LuaError('[k] 后面没有 = @%d' % i)
            else:
                m = IDENT.match(text, i)
                if m:
                    after = skip(m.end())
                    if after < n and text[after] == '=':
                        key = m.group(0)
                        i = skip(after + 1)
            v, i = value(i)
            if key is None:
                arr.append(v)
            else:
                dct[key] = v
                keys_seen = True
            i = skip(i)
            if i < n and text[i] in ',;':
                i += 1
                continue
            if i < n and text[i] == '}':
                return (dct if keys_seen else arr), i + 1
            if i >= n:
                raise LuaError('表未闭合（尾部）')

    v, pos = value(pos)
    return v, pos


def load_root(path):
    text = io.open(path, encoding='utf-8').read()
    m = re.search(r'^\s*XR_DGDB\.bis\s*=\s*\{', text, re.M)
    if not m:
        raise LuaError('找不到 XR_DGDB.bis 的赋值起点')
    v, end = parse_lua_table(text, m.end() - 1)
    rest = text[end:]
    if rest.strip():
        raise LuaError('解析结束后还有未消费内容（说明解析器漏了结构）：%r' % rest[:80])
    return v


def side_of(entry):
    """slots[slot] 是 {联盟侧, 部落侧}；两家都用同一条时是两个相同 dict。"""
    if isinstance(entry, dict):
        vals = [entry.get('1'), entry.get('2')]
        return [v for v in vals if v] or [entry]
    return list(entry) if isinstance(entry, list) else [entry]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=SRC)
    ap.add_argument('--check-only', action='store_true')
    args = ap.parse_args()

    if not os.path.isfile(args.src):
        sys.stderr.write('找不到源文件：%s\n（插件目录在仓库外 .scratch/wow，先把它取回来）\n' % args.src)
        return 2
    raw = open(args.src, 'rb').read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha[:16] != PINNED_SHA256_16:
        sys.stderr.write('源文件哈希与钉住的不一致：\n  期望 %s…\n  实得 %s…\n'
                         '先人工确认插件是否升版、名单口径有没有变，再改 PINNED_SHA256_16 重跑。\n'
                         % (PINNED_SHA256_16, sha[:16]))
        return 3

    toc = os.path.join(os.path.dirname(args.src), 'XR_DungeonGuide.toc')
    ver = ''
    if os.path.isfile(toc):
        m = re.search(r'## Version:\s*(.+)', io.open(toc, encoding='utf-8').read())
        ver = m.group(1).strip() if m else ''
    dv = re.search(r'--\s*v(\d+\.\d+\.\d+)\s*全量重生成', raw[:4000].decode('utf-8', 'replace'))

    root = load_root(args.src)
    bis = root.get('XR_DGDB.bis') if 'XR_DGDB.bis' in root else root
    classes = bis.get('classes')
    if isinstance(classes, dict):
        classes = list(classes.values())

    out_classes = []
    n_spec = n_row = n_slot = 0
    for c in classes:
        specs = c.get('specs')
        specs = list(specs.values()) if isinstance(specs, dict) else list(specs or [])
        ospecs = []
        for s in specs:
            n_spec += 1
            slots = s.get('slots') or {}
            rows = s.get('rows') or {}

            def kv(d):
                return list(d.values()) if isinstance(d, dict) else list(d or [])

            oslots = {}
            for slot in sorted(slots):
                sides = side_of(slots[slot])
                cells = []
                for idx, ent in enumerate(sides):
                    if not isinstance(ent, dict) or not ent.get('item'):
                        continue
                    cells.append({'side': 'alliance' if idx == 0 else 'horde',
                                  'item': int(ent['item']),
                                  'q': ent.get('q'),
                                  'name': ent.get('zh'),
                                  'srcKind': (ent.get('src') or {}).get('t')})
                oslots[slot] = cells
                n_slot += len(cells)
            orows = {}
            for slot in sorted(rows):
                lst = []
                for rank, ent in enumerate(kv(rows[slot]), 1):
                    if isinstance(ent, dict) and ent.get('item'):
                        lst.append({'rank': rank, 'item': int(ent['item']),
                                    'q': ent.get('q'), 'name': ent.get('zh'),
                                    'side': ent.get('side'),
                                    'srcKind': (ent.get('src') or {}).get('t')})
                        n_row += 1
                if lst:
                    orows[slot] = lst
            ospecs.append({'id': s.get('id'), 'name': s.get('name'),
                           'slots': oslots, 'rows': orows})
        out_classes.append({'slug': c.get('slug'), 'nameCn': c.get('zh'), 'specs': ospecs})

    doc = {
        'meta': {
            'kind': 'xr-bis',
            'source': 'XR_DungeonGuide 插件数据文件 Data_Bis.lua（作者 血染）',
            'declaredOrigin': DECLARED_ORIGIN,
            'declaredUpdated': bis.get('updated'),
            'addon': 'XR_DungeonGuide',
            'addonVersionLocal': ver,
            'dataVersionInFile': dv.group(1) if dv else None,
            'srcFile': os.path.relpath(args.src, REPO),
            'srcBytes': len(raw),
            'srcSha256': sha,
            'fetched': date.today().isoformat(),
            'counts': {'classes': len(out_classes), 'specs': n_spec,
                       'slotPicks': n_slot, 'rankRows': n_row},
            'notTaken': ('src.note（成段中文说明）一律不落盘——红线不复制第三方描述文案；'
                         '"这件从哪拿"由合并阶段回本站 items-detail.json 查'),
            'independenceNote': (
                '作者声明抓 foreverchanges.pro，我们现有 bis.json 抓 wowforever.wclbox.com/peizhuang，'
                '是两个不同的站、名单也确有差异（战士 PvE 12 个部位里 4 个首选不同，'
                '全量物品交集 371/609）；但"两家没有共同上游"证明不了，'
                '所以本文件只当"第二份名单"用，不当"第二家独立来源"，也不据此升档。'),
        },
        'classes': out_classes,
    }

    print('解析完成：%d 职业 / %d 专精 / %d 条部位首选 / %d 条排名行；'
          '本地 .toc 版本 %s，文件内数据版本 %s'
          % (len(out_classes), n_spec, n_slot, n_row, ver or '?',
             (dv.group(1) if dv else '?')))
    if args.check_only:
        print('--check-only：不落盘')
        return 0
    io.open(OUT, 'w', encoding='utf-8').write(
        json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print('写出 %s（%d KB）' % (OUT, os.path.getsize(OUT) // 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
