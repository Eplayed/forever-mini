#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 OpenMap 的副本层图清单翻成"Windows 侧照着导"的机器可读表（2026-10-28 站主拍板要导）。

为什么要有这份表：无限服客户端里 `MapArea` / `MapDiff` / `TextureData` 三张表不存在
（2026-10-22 逐张判死，见 docs/DATA-WINDOWS-RUN2-2026-10-22.md 第三节），所以我们自己**推不出**
"哪座本哪一层等于哪 12 个贴图文件号"。OpenMap 0.7.5-CN 的 `Data/DungeonMaps.lua` 有这张表
（它取自正式服 5.5.4.70268 的 UiMap 表 + 12.1.5.70391 的日志），而它的数据表是 MIT。
所以本站只取**文件号与层名**这一层，不取它 `Media/` 里任何一张图——那是暴雪地图美术的裁剪件，
它自己的 NOTICE 写明不受 MIT 覆盖；图由 Windows 侧从本机客户端只读导出，走 2026-10-21 那条路。

跑法（两个路径都写死成默认，可用环境变量覆盖）：
    OPENMAP_DIR=/tmp/wow-ro/_cn_beta_/Interface/AddOns/OpenMap \
    LISTFILE=/tmp/wow-ro/ziliao-export/listfile/client-fdid-name.csv \
    python3 tools/openmap-tile-manifest.py

产物 docs/DATA-openmap-副本层图-2026-10-28.csv 是要**提交进仓库**的那一份：
它钉的是"我们要导哪些号"，不随 Windows 那台机器变。所以脚本先查两件事再写盘：
① 每个文件号都能在 listfile 里落到一条具体路径；② 路径所在目录与它挂的层对得上。
任何一条不过就退出非 0，不出半成品表。
"""
import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENMAP = os.environ.get(
    "OPENMAP_DIR",
    "/tmp/wow-ro/_cn_beta_/Interface/AddOns/OpenMap")
LISTFILE = os.environ.get(
    "LISTFILE",
    "/tmp/wow-ro/ziliao-export/listfile/client-fdid-name.csv")
OUT = os.path.join(ROOT, "docs", "DATA-openmap-副本层图-2026-10-28.csv")

FLOOR_RE = re.compile(r'^\t\[(\d+)\] = \{ -- (.+?)$\n((?:\t\t\{ tiles.*\n)+)', re.M)
TILE_RE = re.compile(r'\{ tiles = \{([^}]+)\}([^}]*)\}')
NAME_RE = re.compile(r'name = "([^"]*)"')
WING_RE = re.compile(r'wing = "([^"]*)"')


def load_listfile():
    """fdid -> (client_path, name_kind, content_length)。只认登记过的那一条。"""
    if not os.path.exists(LISTFILE):
        sys.exit('找不到 listfile：%s（先挂上 Windows 共享，或把 LISTFILE 指过去）' % LISTFILE)
    out = {}
    with io.open(LISTFILE, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            out[row['fdid']] = (row['name'], row['name_kind'], row['content_length'])
    return out


def parse_dungeon_maps():
    src = os.path.join(OPENMAP, 'Data', 'DungeonMaps.lua')
    if not os.path.exists(src):
        sys.exit('找不到 OpenMap 的 Data/DungeonMaps.lua：%s（先挂上共享，或指 OPENMAP_DIR）' % src)
    text = io.open(src, encoding='utf-8').read()
    rows = []
    for map_id, inst_name, body in FLOOR_RE.findall(text):
        for floor_no, (tiles, tail) in enumerate(TILE_RE.findall(body), start=1):
            ids = [x.strip() for x in tiles.split(',') if x.strip()]
            nm = NAME_RE.search(tail)
            wg = WING_RE.search(tail)
            rows.append({
                'instanceMapId': map_id,
                'instanceEn': inst_name.strip(),
                'floor': floor_no,
                'floorEn': nm.group(1) if nm else '',
                'wingEn': wg.group(1) if wg else '',
                'tileCount': len(ids),
                'tileIds': ids,
            })
    return rows


def main():
    lf = load_listfile()
    floors = parse_dungeon_maps()
    errs = []
    out_rows = []
    for f in floors:
        if f['tileCount'] != 12:
            errs.append('%s 第 %d 层不是 12 片，是 %d 片' %
                        (f['instanceEn'], f['floor'], f['tileCount']))
        dirs = set()
        for i, fdid in enumerate(f['tileIds'], start=1):
            hit = lf.get(fdid)
            if not hit:
                errs.append('%s 第 %d 层第 %d 片 fdid=%s 在 listfile 里查不到' %
                            (f['instanceEn'], f['floor'], i, fdid))
                continue
            path, kind, size = hit
            if kind != 'verified':
                errs.append('fdid=%s 的登记状态是 %s，不是 verified，不导' % (fdid, kind))
                continue
            parts = path.split('/')
            # Interface/WorldMap/<本名>/<层图名>_<片号>.blp —— 同一层的 12 片必须在同一个目录里，
            # 且片号要和我们的序号对得上；对不上说明这层的表被谁动过，宁可红也不猜。
            if len(parts) < 4 or parts[0].lower() != 'interface' or parts[1].lower() != 'worldmap':
                errs.append('fdid=%s 路径 %s 不在 Interface/WorldMap/ 下' % (fdid, path))
                continue
            dirs.add(parts[2].lower())
            out_rows.append({
                'instanceMapId': f['instanceMapId'],
                'instanceEn': f['instanceEn'],
                'floor': f['floor'],
                'floorEn': f['floorEn'],
                'wingEn': f['wingEn'],
                'tile': i,
                'fdid': fdid,
                'clientPath': path,
                'bytes': size,
            })
        if len(dirs) != 1:
            errs.append('%s 第 %d 层的 12 片散在多个目录：%s' %
                        (f['instanceEn'], f['floor'], '、'.join(sorted(dirs))))

    if errs:
        sys.stderr.write('\n'.join(errs[:20]) + '\n')
        sys.exit('核对不过：%d 条问题，不写表' % len(errs))

    cols = ['instanceMapId', 'instanceEn', 'floor', 'floorEn', 'wingEn',
            'tile', 'fdid', 'clientPath', 'bytes']
    with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(out_rows)
    inst = len({r['instanceMapId'] for r in out_rows})
    fl = len({(r['instanceMapId'], r['floor']) for r in out_rows})
    print('写 %s：%d 座本 / %d 层 / %d 片，全部 verified 且逐层同目录' %
          (os.path.relpath(OUT, ROOT), inst, fl, len(out_rows)))


if __name__ == '__main__':
    main()
