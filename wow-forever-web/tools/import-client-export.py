#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把站主从《无限》客户端导出的资料包并进仓库（图标 + 载入图 + 来源登记）。

来源：站主在 Windows 上用 CascLib + 自写导出器从客户端取，清单出自
`docs/DATA-CLIENT-EXPORT-2026-10-19.md`，结果核对见 `docs/DATA-CLIENT-EXPORT-RESULT-2026-10-21.md`。
包默认在仓库外 `~/Documents/project/.scratch/wow/ziliao-export/`（和插件目录同一待遇，不进 git）。

为什么图标要转成 56×56 的 .jpg 而不是直接放 .png：
    两栈渲染把路径写死成 `img/icons/<key>.jpg`（src/js/app.js 四处 + app/src/lib/glyph.js 一处），
    `build-icon-map.py` 也只把 `.jpg` 当本地图标（`f.endswith(".jpg")`）。
    现有 3294 张本地图标全是 56×56（CDN /icons/56/ 那一档），客户端这批是 64×64，
    不统一尺寸会在图标轨上看出粗细差。要改成支持 .png 得动五处渲染再加一条分支，不值。

跑法：
    python3 tools/import-client-export.py            # 只报会做什么，不写盘
    python3 tools/import-client-export.py --apply    # 真写
写完之后必须接着跑：
    python3 tools/build-icon-map.py && node tools/build-data.js
（缺图登记是派生物，补图之后要重算，别手改 icon-gaps.json。）
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit('需要 Pillow：pip3 install pillow')

HOME = os.path.expanduser('~')
DEF_SRC = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow', 'ziliao-export')
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WEB, "app", "data")
ICONS = os.path.join(WEB, "app", "img", 'icons')
ART_DUNGEONS = os.path.join(WEB, "app", "img", 'art', 'dungeons')
ART_MANIFEST = os.path.join(WEB, "app", "img", 'art', 'manifest.json')
# 图标轨统一按这一档出图（CDN 那批就是 56×56）
ICON_PX = 56
ICON_Q = 90
LOAD_PX = 640      # 载入图长边压到这一档，与站内其它 dungeon-loading 同量级
LOAD_Q = 82


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load_result(src):
    p = os.path.join(src, 'RESULT.json')
    if not os.path.exists(p):
        sys.exit('找不到 %s——资料包不完整，先别并' % p)
    r = json.load(open(p, encoding='utf-8'))
    idx = {}
    mark = 'ziliao-export/'
    for e in r.get('files') or []:
        path = str(e.get('path') or '').replace('\\', '/')
        i = path.find(mark)
        rel = path[i + len(mark):] if i >= 0 else path
        idx[rel] = e
    return r, idx


def verify(src, idx, rels):
    """逐条重算 sha256。不通过就退出——来源没验过的图不进仓库。"""
    bad = []
    for rel in rels:
        e = idx.get(rel)
        fp = os.path.join(src, rel)
        if e is None or not os.path.exists(fp):
            bad.append(rel + '（RESULT.json 里没这条或文件不在）')
            continue
        if sha256(fp) != e.get('sha256'):
            bad.append(rel + '（哈希不符）')
        elif os.path.getsize(fp) != e.get('bytes'):
            bad.append(rel + '（字节数不符）')
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=DEF_SRC)
    ap.add_argument('--apply', action='store_true', help='真写盘；默认只报告')
    a = ap.parse_args()
    src = os.path.abspath(a.src)
    if not os.path.isdir(src):
        sys.exit('资料包目录不存在：%s' % src)

    r, idx = load_result(src)
    counts = r.get('counts') or {}
    build = r.get('build') or ''
    today = datetime.date.today().isoformat()

    # 1) 图标：文件名必须都在缺图登记里，登记外的一个不落
    gaps = set(json.load(open(os.path.join(DATA, 'icon-gaps.json'), encoding='utf-8')).get('keys') or [])
    icon_files = sorted(f for f in os.listdir(os.path.join(src, 'icons')) if f.endswith('.png'))
    icon_keys = [f[:-4] for f in icon_files]
    outside = [k for k in icon_keys if k not in gaps]
    if outside:
        print('跳过 %d 个不在缺图登记里的图标（已有图还来一张，可能是重名或登记过期）：%s'
              % (len(outside), outside[:6]))
    todo_icons = [f for f, k in zip(icon_files, icon_keys) if k in gaps]
    bad = verify(src, idx, ['icons/' + f for f in todo_icons])
    if bad:
        sys.exit('图标哈希没通过，一个都不写：\n  ' + '\n  '.join(bad[:5]))

    # 2) 载入图：只认导出来的那一张，且这座本在 art.json 里现在必须是空的
    art = json.load(open(os.path.join(DATA, 'art.json'), encoding='utf-8'))
    load_files = sorted(f for f in os.listdir(os.path.join(src, 'loadings')) if f.endswith('.png'))
    loads = []
    for f in load_files:
        did = f[:-4]
        if art.get('dungeons', {}).get(did):
            print('跳过载入图 %s：art.json 里这座本已经有图了' % did)
            continue
        loads.append((did, 'loadings/' + f))
    bad = verify(src, idx, [rel for _, rel in loads])
    if bad:
        sys.exit('载入图哈希没通过：\n  ' + '\n  '.join(bad[:5]))

    print('资料包 build=%s' % build)
    print('图标：登记缺 %d · 包里有 %d · 可并 %d（跳过登记外 %d）'
          % (len(gaps), len(icon_keys), len(todo_icons), len(outside)))
    print('载入图：包里有 %d · 可并 %d（%s）' % (len(load_files), len(loads), [d for d, _ in loads]))
    print('包自报 counts：%s' % json.dumps(counts, ensure_ascii=False))
    if not a.apply:
        print('预演模式，没写任何文件。加 --apply 才真写。')
        return

    written = []
    for f in todo_icons:
        key = f[:-4]
        im = Image.open(os.path.join(src, 'icons', f)).convert('RGB')
        im = im.resize((ICON_PX, ICON_PX), Image.LANCZOS)
        out = os.path.join(ICONS, key + '.jpg')
        im.save(out, 'JPEG', quality=ICON_Q, optimize=True)
        written.append(key)

    art_items = []
    for did, rel in loads:
        im = Image.open(os.path.join(src, rel)).convert('RGB')
        if max(im.size) > LOAD_PX:
            im.thumbnail((LOAD_PX, LOAD_PX), Image.LANCZOS)
        out = os.path.join(ART_DUNGEONS, did + '.webp')
        im.save(out, 'WEBP', quality=LOAD_Q)
        art.setdefault('dungeons', {})[did] = 'img/art/dungeons/%s.webp' % did
        art_items.append({'file': 'art/dungeons/%s.webp' % did, 'bytes': os.path.getsize(out),
                          'sha1': hashlib.sha1(open(out, 'rb').read()).hexdigest()[:10],
                          'source': '客户端导出（build %s）' % build,
                          'kind': 'dungeon-loading', 'origin': 'client-export',
                          'fetchedAt': today,
                          'note': '暴雪游戏美术，由站主从本机客户端导出，不经第三方站'})

    with open(os.path.join(DATA, 'art.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
        f.write('\n')

    man = json.load(open(ART_MANIFEST, encoding='utf-8'))
    man['items'] = [x for x in man.get('items') or []
                    if not (x.get('origin') == 'client-export' and x.get('file') in
                            {y['file'] for y in art_items})] + art_items
    man['total'] = len(man['items'])
    man['clientExportAt'] = today
    with open(ART_MANIFEST, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
        f.write('\n')

    # 3) 原料快照：谁、哪个 build、哪些没拿到，全留一份可回查的记录
    #    notes 是导出方自己写的一串说明（列表），原样留档，不改写也不摘要——
    #    以后有人问"这张为什么没有"，答案要能指回他当时写的那句话。
    not_found = {
        'icons': sorted(gaps - set(icon_keys)),
        'loadings': [d for d in (r.get('counts', {}).get('loadings', {}) or {})
                     if d != 'ok'],
        'notes': list(r.get('notes') or []),
    }
    snap = {
        'meta': {
            'kind': 'client-export-2026-10-21',
            'fetched': today,
            'source': '站主本机《无限》客户端导出（包在仓库外 .scratch/wow/ziliao-export/，不进 git）',
            'tool': json.dumps(r.get('tool'), ensure_ascii=False),
            'build': build,
            'packageCounts': counts,
            'method': 'tools/import-client-export.py --apply',
            'note': '这一份是原料留档：图标转成 56×56 jpg 落 app/img/icons/，'
                    '载入图落 app/img/art/dungeons/ 并挂进 art.json.dungeons。'
                    'art.json 由 fetch-art.py 按 app/img/art/manifest.json 的 items 重算，'
                    '所以这张图能活下来是因为它在 manifest 里有一条 origin=client-export 的记录。',
        },
        'icons': {k: {'file': 'icons/%s.png' % k, 'sha256': idx['icons/%s.png' % k]['sha256'],
                      'bytes': idx['icons/%s.png' % k]['bytes']} for k in written},
        'loadings': {did: {'file': rel, 'sha256': idx[rel]['sha256'],
                           'bytes': idx[rel]['bytes']} for did, rel in loads},
        'notFound': not_found,
    }
    sp = os.path.join(DATA, 'upstream', 'client-export-2026-10-21.json')
    with open(sp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
        f.write('\n')

    print('写入：图标 %d 张（%d×%d jpg）· 载入图 %d 张 · 快照 %s'
          % (len(written), ICON_PX, ICON_PX, len(art_items), os.path.relpath(sp, WEB)))
    print('下一步：python3 tools/build-icon-map.py && node tools/build-data.js')
    print('        缺图登记应从 %d 掉到 %d（掉不掉取决于有没有真落盘）'
          % (len(gaps), len(gaps) - len(written)))


main()
