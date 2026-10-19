#!/usr/bin/env python3
# 从 XR_DungeonGuide/Data_ZoneMap.lua 抽「中文区域名 → uiMapID」这一层对照，落成 upstream 快照。
#
# 为什么要这一份：站内 world.json 的稀有有 73 条带着百分比坐标却没有地图号（上游那份就没给这一列），
# 按"不猜位置"的口径它们只能进列表、上不了图。这份表正好补那一层——它是插件作者用
# 自己那份 npcloc（NPC → uiMapID + 坐标）与副本入口反推出来的，文件头写着"零猜测、勿手改"。
#
# 一律不取的（红线，不是风格问题）：
#   插件 Media/ 里那些 .tga——31 张副本小图、25 张讲解插画是作者自己画、自己截的，属于别人的创作；
#   插件里任何成段中文说明（营地玩法、路线讲解）；
#   名字这一层这里也用不上（我们只取映射，不取名字，区域中文名仍以客户端解包为准）。
# 取的是事实性标识符映射：区域中文名 → 地图号。
#
# 用法：python3 tools/extract-xr-zonemap.py [--src <插件根目录>] [--out-dir <upstream 目录>]
import json
import os
import re
import sys
from datetime import date

HOME = os.path.expanduser('~')
DEF_SRC = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow')
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    src = arg('--src', DEF_SRC)
    out_dir = arg('--out-dir', os.path.join(WEB, 'src', 'data', 'upstream'))
    path = os.path.join(src, 'XR_DungeonGuide', 'Data_ZoneMap.lua')
    if not os.path.exists(path):
        sys.exit('找不到 %s——这一份要的是插件目录里的 Data_ZoneMap.lua，'
                 '用 --src 指到插件根目录再跑' % path)
    with open(path, encoding='utf-8') as f:
        text = f.read()

    head = text.split('XR_DGDB.zonemap', 1)[0]
    ver = re.search(r'v(\d+\.\d+\.\d+)', head)
    cover = re.search(r'覆盖：(.+)', head)
    pairs = re.findall(r'\["([^"]+)"\]\s*=\s*(\d+)', text.split('XR_DGDB.zonemap', 1)[1])
    zones = {}
    for name, mid in pairs:
        zones[name] = int(mid)
    if not zones:
        sys.exit('一条都没解析出来——文件结构变了，去看 Data_ZoneMap.lua 的写法再改这里')

    payload = {
        'meta': {
            'source': 'XR_DungeonGuide %s Data_ZoneMap.lua 的 XR_DGDB.zonemap' % (ver.group(1) if ver else '版本未记'),
            'originFile': path,
            'fetched': date.today().isoformat(),
            'what': '中文区域名 → 地图号（uiMapID）对照',
            'how': '插件作者用它自己那份 npcloc（NPC→地图号+坐标）与副本入口反推生成，'
                   '文件头声明"零猜测、勿手改"；本站只取这一层映射',
            'coverage': cover.group(1).strip() if cover else None,
            'boundary': '只取映射。插件 Media/ 里的副本小图与讲解插画是作者自绘，不取；'
                        '任何成段说明文字不取',
            'counts': {'entries': len(zones)}
        },
        'zones': zones
    }
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    out = os.path.join(out_dir, 'xr-zonemap.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('区域→地图号 %d 条 → %s' % (len(zones), os.path.relpath(out, WEB)))


main()
