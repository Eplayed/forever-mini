#!/usr/bin/env python3
# 把插件里的副本内部底图转存成站内素材（app/img/art/dungeonmaps/），给首领坐标当画布的底图。
#
# 为什么走这一条：站内已有 28 座本的首领百分比坐标（upstream/df-dungeon-geo.json → dungeon-geo.json），
# 但**没有那批副本内部图**，所以坐标只能以数字显示、画不成点。区域底图那 9 张插件里一张都没有，
# 只能等客户端导出；副本内部图这一类插件里恰好有一批，先补这一头。
#
# 许可与边界（2026-10-19 站主拍板"从插件里用吧"）：
#   DungeonsForever 的 LICENSE 是「Copyright © 2026 圆圆 · 保留所有权利」，
#   XR_DungeonGuide 同属作者作品。这批图是插件作者画/加工出来的副本底图，
#   和站内已有的"客户端原画"（载入图、世界地图底图、职业背景）是同一类素材：
#   一律本地留存、不热链、每张记来源与抓取日、**整目录删掉即回退到只显示数字坐标**。
#   取的是图，作者写的任何文字说明与攻略内容一律不取。
#
# 用法：python3 tools/extract-plugin-maps.py [--src <插件根目录>] [--dry]
import argparse
import json
import os
import re
import sys
from datetime import date

try:
    from PIL import Image
except ImportError:
    sys.exit('需要 Pillow（转 .tga → .webp）：pip3 install pillow')

HOME = os.path.expanduser('~')
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(WEB, "app", "img", 'art', 'dungeonmaps')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from addons_root import resolve as resolve_addon_root, export_root as resolve_export_root
    DEF_SRC = resolve_addon_root('DungeonsForever')
    DEF_EXPORT = resolve_export_root()
except Exception:
    DEF_SRC = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow')
    DEF_EXPORT = os.path.join(DEF_SRC, 'ziliao-export')

# 站内副本 id → 插件或本机客户端导出的那张底图。别名对不上的一律留空，不猜。
# 两处容易搞错的：站内 razor-krendor 写的是「剃刀高地」＝Razorfen Downs → dmap_rfndowns；
# razorfen-kraul 是「剃刀沼泽」＝Razorfen Kraul → dmap_rfnkraul。
MAP = {
    'alcaz-prison': 'DF/AlcazPrison',
    'blackfathom-deeps': 'XR/dmap_blackfathom',
    'blackmaw-hold': 'DF/BlackmawHold',
    'blackrock-depths': 'XR/dmap_brd',
    'city-of-dalaran': 'DF/Dalaran',
    'deathmine': 'XR/dmap_deadmines',
    'dire-maul-east': 'XR/dmap_dm_east',
    'dire-maul-north': 'XR/dmap_dm_north',
    'dire-maul-west': 'XR/dmap_dm_west',
    'gnomeregan': 'XR/dmap_gnomeregan',
    'hall-of-thanes': 'DF/HallOfThanes',
    'kroldok-stronghold': 'DF/KroldokStronghold',
    'lower-blackrock-spire': 'XR/dmap_lbrs',
    'maraudon': 'XR/dmap_maraudon',
    'onyxias-lair': 'CLIENT/249_1',
    'ragefire-chasm': 'XR/dmap_ragefire',
    'razor-krendor': 'XR/dmap_rfndowns',
    'razorfen-kraul': 'XR/dmap_rfnkraul',
    'ruins-of-lordaeron': 'DF/RuinsOfLordaeron',
    'scarlet-monastery-armory': 'XR/dmap_sm_arm',
    'scarlet-monastery-cathedral': 'XR/dmap_sm_cath',
    'scarlet-monastery-graveyard': 'XR/dmap_sm_gy',
    'scarlet-monastery-library': 'XR/dmap_sm_lib',
    'scholomance': 'XR/dmap_scholomance',
    'shadowfang-keep': 'XR/dmap_shadowfangkeep',
    'shapers-terrace': 'DF/ShapersTerrace',
    'stratholme-main-gate': 'XR/dmap_strat',
    'stratholme-service-gate': 'XR/dmap_strat',
    'sunken-temple': 'XR/dmap_sunken_temple',
    'the-drowned-city': 'DF/TheDrownedCity',
    'the-stocks': 'XR/dmap_stockade',
    'uldaman': 'XR/dmap_uldaman',
    'upper-blackrock-spire': 'XR/dmap_ubrs',
    'wailing-caverns': 'XR/dmap_wailingcaverns',
    'whelgars-excavation': 'DF/ExcavationSite',
    'zulfarrak': 'XR/dmap_zulfarrak',
}

PREFIX = {'XR': 'XR_DungeonGuide/Media/DungeonMaps', 'DF': 'DungeonsForever/Media/Maps'}
CLIENT_FLOOR_BOX = (0, 0, 1002, 668)  # 与 build-zone-maps.py 实测内容盒一致，裁掉 1024×768 右下黑边

# 这三批图不是一类东西，必须分开记：
#   XR 的 Media/DungeonMaps —— XR_DungeonGuide/Data_DungeonMaps.lua 文件头第一行写着
#     "粉丝整理 31 张实截图；512²/192色 TGA-RLE"，也就是**游戏里那张副本地图的截图**，
#     内容是官方的，文件是作者加工出来的（还写过一次修 BGR 反色的教训）。
#   CLIENT 的 maps-floor-2026-10-29/floors/*.png —— 本机 Forever 客户端导出的官方层图拼片（如奥妮克希亚的巢穴 249_1），
#     同归 game-capture（画的就是游戏内那张官方副本地图）。
#   DF 的 Media/Maps —— 无限新增本游戏内没有底图，是**插件作者自己画的示意图**。
ORIGIN = {
    'XR': ('game-capture', '游戏内副本地图的截图（内容是官方的那张图，文件由插件作者整理）'),
    'CLIENT': ('game-capture', '本机无限服客户端导出的官方副本地图（裁切内容盒 1002×668 缩放）'),
    'DF': ('addon-drawn', '插件作者自绘的示意图（这几座本游戏内没有底图）'),
}


def toc_version(addon_dir, name):
    p = os.path.join(addon_dir, name + '.toc')
    if not os.path.exists(p):
        return '版本未记'
    with open(p, encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.match(r'\s*##\s*Version:\s*(\S+)', line)
            if m:
                return m.group(1)
    return '版本未记'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=DEF_SRC)
    ap.add_argument('--export', default=DEF_EXPORT)
    ap.add_argument('--dry', action='store_true', help='只报对得上多少张，不写文件')
    ap.add_argument('--force', action='store_true', help='强制覆盖本地已有的 webp（注意 OSS 不可变素材文件名冲突）')
    a = ap.parse_args()

    geo = json.load(open(os.path.join(WEB, "app", "data", 'dungeon-geo.json'), encoding='utf-8'))
    need = sorted(k for k, v in (geo.get('dungeons') or {}).items() if v.get('bossPos'))
    ver = {'XR': toc_version(os.path.join(a.src, 'XR_DungeonGuide'), 'XR_DungeonGuide'),
           'DF': toc_version(os.path.join(a.src, 'DungeonsForever'), 'DungeonsForever'),
           'CLIENT': '1.60.1'}
    today = date.today().isoformat()

    # XR_DungeonGuide 已退役，不在本机时保留 manifest 里既有且本地 webp 仍在盘上的条目，避免洗掉 24 张经典本实截图
    prev_manifest_path = os.path.join(OUT_DIR, 'manifest.json')
    prev_files = {}
    if os.path.exists(prev_manifest_path):
        prev_files = json.load(open(prev_manifest_path, encoding='utf-8')).get('files') or {}

    files, miss, kept_prev = {}, [], 0
    for slug in need:
        ref = MAP.get(slug)
        if not ref:
            miss.append(slug)
            continue
        tag, stem = ref.split('/')
        if tag == 'CLIENT':
            src = os.path.join(a.export, 'maps-floor-2026-10-29', 'floors', stem + '.png')
            out = slug.replace('-', '') + '.webp'
            from_name = 'maps-floor-2026-10-29/floors/' + stem + '.png'
            addon_name = 'WoW-Forever-Client'
        else:
            src = os.path.join(a.src, PREFIX[tag], stem + '.tga')
            out = stem.lower() + '.webp'
            from_name = stem + '.tga'
            addon_name = 'XR_DungeonGuide' if tag == 'XR' else 'DungeonsForever'

        if not os.path.exists(src):
            prev = prev_files.get(slug)
            prev_disk = prev and os.path.join(WEB, 'app', prev.get('file', ''))
            if prev and prev_disk and os.path.exists(prev_disk):
                files[slug] = dict(prev)
                kept_prev += 1
                continue
            miss.append(slug + '（找不到原件 ' + from_name + '）')
            continue

        files[slug] = {'file': 'img/art/dungeonmaps/' + out, 'from': from_name,
                       'addon': addon_name,
                       'addonVersion': ver[tag], 'sourcePath': src, 'tag': tag,
                       'fetched': today,
                       'origin': ORIGIN[tag][0], 'originNote': ORIGIN[tag][1]}
    print('要画首领坐标的 %d 座里，底图能对上 %d 座（其中沿用既有归档 %d 座）；对不上 %d：%s'
          % (len(need), len(files), kept_prev, len(miss), miss or '无'))
    if a.dry or not files:
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    done = 0
    for slug, v in sorted(files.items()):
        src_path = v.pop('sourcePath', None)
        tag = v.pop('tag', None)
        if not src_path:
            done += 1
            continue
        out = os.path.join(OUT_DIR, os.path.basename(v['file']))
        if os.path.exists(out) and not a.force:
            im_old = Image.open(out)
            v['pixels'] = list(im_old.size)
            done += 1
            continue
        im = Image.open(src_path)
        if im.mode not in ('RGB', 'RGBA'):
            im = im.convert('RGB')
        if tag == 'CLIENT' and im.size[0] >= CLIENT_FLOOR_BOX[2] and im.size[1] >= CLIENT_FLOOR_BOX[3]:
            im = im.crop(CLIENT_FLOOR_BOX)
        if max(im.size) > 640:
            im.thumbnail((640, 640))
        im.save(out, 'WEBP', quality=82)
        v['pixels'] = list(im.size)
        done += 1
    originCounts = {}
    for v in files.values():
        originCounts[v['origin']] = originCounts.get(v['origin'], 0) + 1
    manifest = {
        'kind': 'dungeonmaps',
        'generatedAt': today,
        'policy': '整目录删除即回退——副本详情页的首领位置退回只显示数字坐标，不画点。'
                  '这批文件都是第三方插件带的加工品、不是暴雪直接发布的素材文件，也不接任何 CDN；'
                  '其中 game-capture 那一类画的就是游戏内那张官方副本地图，'
                  'addon-drawn 那一类是插件作者自己画的示意图',
        'originCounts': originCounts,
        'originKinds': {ORIGIN['XR'][0]: ORIGIN['XR'][1], ORIGIN['DF'][0]: ORIGIN['DF'][1]},
        'authorNote': {
            'file': 'XR_DungeonGuide/Data_DungeonMaps.lua 第一行',
            'text': '-- v0.16.5 副本地图（血染 2026-09-29：粉丝整理 31 张实截图；512²/192色 TGA-RLE）',
            'readAs': '这批 dmap_*.tga 是作者从游戏里截下来的副本地图再编码的，不是从暴雪拿的原始素材文件'},
        'license': '来源插件的许可：DungeonsForever LICENSE 为「Copyright © 2026 圆圆 · 保留所有权利」，'
                   'XR_DungeonGuide 同属作者作品。2026-10-19 站主拍板"从插件里用"，'
                   '与站内已有的客户端原画同一套处理（本地留存、记来源与抓取日、可整体下线）；'
                   '作者写的任何文字说明与攻略内容一律没取',
        'note': '副本内部底图，用作首领坐标的画布；斯坦索姆两座本共用一张（dmap_strat）',
        'files': files
    }
    with open(os.path.join(OUT_DIR, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('转存 %d 座本用的底图（去重后 %d 个文件，斯坦索姆两座共用一张）→ app/img/art/dungeonmaps/'
          '（含 manifest.json 记来源与许可）' % (done, len(set(v['file'] for v in files.values()))))


main()
