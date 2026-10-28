#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把客户端导出的区域图瓦片拼成本站那一张区域底图（2026-10-28 站主拍板"按 OpenMap 的方式重做区域图"）。

为什么现在能做：10-22 那一轮卡在两件事上（`docs/DATA-WINDOWS-RUN2-2026-10-22.md` 第三节），
① 语言——这台客户端的 WorldMap 美术是韩文侧的，地名烘在图里；② 几何——"12 片拼出来 1024×768，
而我们那 37 张是 560×373，比例不一样，百分比坐标能不能落上去还是未知"。
几何这一半本轮量掉了：**7 个区域逐张实测，内容盒都是 (0,0)→(1002,668)，比例 1.5000**，
与 560×373（1.5013）同一参照物，只差一个等比缩放。所以拼完裁到 1002×668 就能直接用现有那套百分比坐标。
语言那一半没量掉，要站主拍（见 docs/PLAN-区域地图按OpenMap那套重做-2026-10-28.md）。

瓦片命名：`m<uiMapID>_<目录>_<前缀>c6<序号>.png`，序号 1–12 是**行优先**（1–4 上排，9–12 下排）。
这套命名是 Windows 侧导出时按 listfile 里的原始文件名留的，不是本站起的。

跑法：
    python3 tools/build-zone-maps.py --dry-run          # 只报每区会拼成什么，不写盘
    python3 tools/build-zone-maps.py --out-dir /tmp/zm  # 出成品给人看
    python3 tools/build-zone-maps.py --apply            # 写进 app/img/art/maps/ 并登记 manifest
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys
from collections import defaultdict

try:
    from PIL import Image
except ImportError:  # 门禁机没装 PIL 时给一句人话，不抛栈
    sys.exit('需要 Pillow（本脚本要拼瓦片）：pip3 install pillow')

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILE_SRC = os.path.join(os.path.expanduser('~'), 'Documents', 'project', '.scratch', 'wow',
                        'ziliao-export', 'maps', 'tiles-png')
SHARE_TILE_SRC = '/tmp/wow-ro/ziliao-export/maps/tiles-png'
MAPS_DIR = os.path.join(WEB, 'app', 'img', 'art', 'maps')
MANIFEST = os.path.join(MAPS_DIR, 'manifest.json')
TILE = 256
COLS, ROWS = 4, 3
# 实测出来的内容盒（7 个区域逐张一致）：见上面 docstring 那条。
BOX = (0, 0, 1002, 668)
OUT_SIZE = (1002, 668)
TILE_RE = re.compile(r'^m(\d+)_.+_c6(\d+)\.png$')


def find_tiles():
    for p in (TILE_SRC, SHARE_TILE_SRC):
        if os.path.isdir(p):
            return p
    sys.exit('找不到瓦片目录。试过的两个位置：\n  %s\n  %s\n'
             '（先挂上 Windows 共享，或把资料包拷回本机 .scratch）' % (TILE_SRC, SHARE_TILE_SRC))


def collect(src):
    """uiMapID -> {序号: 文件路径}；序号不齐 12 片的区域单独列出来，不硬拼。"""
    zones = defaultdict(dict)
    for name in sorted(os.listdir(src)):
        m = TILE_RE.match(name)
        if not m:
            continue
        zones[m.group(1)][int(m.group(2))] = os.path.join(src, name)
    full, partial = {}, {}
    for z, tiles in zones.items():
        (full if len(tiles) == COLS * ROWS else partial)[z] = tiles
    return full, partial


def compose(tiles):
    img = Image.new('RGB', (COLS * TILE, ROWS * TILE))
    for i in range(1, COLS * ROWS + 1):
        n = i - 1
        img.paste(Image.open(tiles[i]).convert('RGB'), ((n % COLS) * TILE, (n // COLS) * TILE))
    box = img.getbbox()
    crop = img.crop(BOX)
    return crop, box


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', help='把拼好的图写到这个目录（给人先看效果）')
    ap.add_argument('--apply', action='store_true',
                    help='写进 app/img/art/maps/ 并在 manifest.json 里登记（只登记，不覆盖已有别处的图）')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    src = find_tiles()
    full, partial = collect(src)
    print('瓦片目录：%s' % src)
    print('齐 12 片的区域：%d 个（%s）' % (len(full), '、'.join(sorted(full))))
    for z, t in sorted(partial.items()):
        print('  片数不齐，跳过：%s 只有 %d 片（河林那种非 4×3 的布局要单独判，不硬拼）' % (z, len(t)))

    today = datetime.date.today().isoformat()
    made = []
    for z in sorted(full):
        crop, box = compose(full[z])
        if box != BOX:
            print('  %s 内容盒实测 %s，和登记的 %s 不一致 —— 跳过，不猜' % (z, box, BOX))
            continue
        out = os.path.join(args.out_dir or '/tmp/zone-maps', '%s.webp' % z)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        crop.save(out, 'WEBP', quality=88)
        made.append((z, out, crop.size, os.path.getsize(out)))
        print('  %s → %s %dx%d %d B' % (z, out, crop.size[0], crop.size[1], os.path.getsize(out)))

    if args.dry_run or not args.apply:
        print('\n没写进仓库。要并进素材层再跑 --apply（会逐张登记来源与抓取日期）。')
        return

    man = {}
    if os.path.exists(MANIFEST):
        man = json.load(io.open(MANIFEST, encoding='utf-8'))
    items = man.setdefault('items', {})
    for z, path, size, nbytes in made:
        key = 'maps/%s.webp' % z
        if key in items and items[key].get('sha256') == sha(path):
            continue
        items[key] = {
            'kind': 'zone-map',
            'origin': 'client-export',
            'source': 'Windows 侧 wowfexport 从本机《无限》客户端 Interface/WorldMap 瓦片导出（只读）',
            'uiMapId': z,
            'tiles': 12,
            'box': list(BOX),
            'px': list(size),
            'bytes': nbytes,
            'sha256': sha(path),
            'fetchedAt': today,
            'note': '地名是烘在这张客户端美术里的（这台装的是韩文侧素材），'
                    '换中文素材包后要整批重导；本条只登记来路，不声明语言已核。',
        }
        import shutil
        shutil.copyfile(path, os.path.join(MAPS_DIR, '%s.webp' % z))
    man['generatedAt'] = today
    with io.open(MANIFEST, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('已写 %d 张进 %s 并登记 manifest' % (len(made), MAPS_DIR))


if __name__ == '__main__':
    main()
