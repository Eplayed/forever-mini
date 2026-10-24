#!/usr/bin/env python3
# upstream/df-dungeon-geo.json → app/data/dungeon-geo.json（副本入口与本内首领坐标，成品层）。
#
# 为什么要单独一层成品，而不是把快照直接给页面读：
#   ① 快照的 meta 里写着许可与"哪些字段一律不取"，那是给我们看的，不能上页面（红线：玩家看得见
#      的地方不许讲资料出处与缺口）；成品层只留渲染要的东西，出处放 provenance 字段，
#      由溯源页集中说。
#   ② 成品层要能进 build-data.js 的卡口：每座本的坐标必须在 0–100 之间、地图号要能在
#      art.json 里查到那张图（查不到就明确标 noMap，页面据此不画点）、
#      首领名必须是 dungeons.json 里这座本真有的首领，不许凭空多出一个名字。
#   ③ 单独一个文件、不塞进 dungeons.json：只有副本详情页用得到，列表页没必要背这份。
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "app", "data")


def main():
    snap = json.load(open(os.path.join(DATA, 'upstream', 'df-dungeon-geo.json'), encoding='utf-8'))
    art = json.load(open(os.path.join(DATA, 'art.json'), encoding='utf-8')).get('maps') or {}
    dz = json.load(open(os.path.join(DATA, 'dungeons.json'), encoding='utf-8'))
    bosses_of = {}
    dun_name = {}
    for key in ('newDungeons', 'classicDungeons', 'raids'):
        for x in dz.get(key) or []:
            bosses_of[x['id']] = {b.get('nameCn') for b in (x.get('bosses') or [])}
            dun_name[x['id']] = x.get('nameCn') or x.get('nameEn') or x['id']

    prov = {'type': 'addon', 'url': snap['meta']['source'], 'checkedAt': snap['meta']['fetched'],
            'note': '副本入口与各首领的百分比坐标（第三方插件从客户端读出的位置，本站未进游戏实测）'}

    out, n_boss = {}, 0
    for did, v in sorted((snap.get('entry') or {}).items()):
        mid = str(v['mapId'])
        out.setdefault(did, {})['entry'] = {
            'mapId': mid, 'x': v['x'], 'y': v['y'], 'zone': v['zone'],
            'mapFile': art.get(mid), 'noMap': mid not in art}
    # 首领坐标的画布：副本内部底图。这批图不在 art.json 里（那是 fetch-art.py 从 CDN 建的索引），
    # 它由 tools/extract-plugin-maps.py 转存并自带 manifest，所以这里直接读那份 manifest。
    dmaps, dm = {}, {}
    mapPixels = {}
    mpath = os.path.join(ROOT, "app", "img", 'art', 'dungeonmaps', 'manifest.json')
    if os.path.exists(mpath):
        dm = json.load(open(mpath, encoding='utf-8'))
        dmaps = {k: v.get('file') for k, v in (dm.get('files') or {}).items() if v.get('file')}
        # 每张图的像素尺寸：底图不全是方的（游戏截图 512²、作者自绘那几张是 640×427），
        # 页面要靠这个比例预留位置，写死 512/512 会让横图加载完抖一下
        mapPixels = {k: v.get('pixels') for k, v in (dm.get('files') or {}).items()}
    # 底图来自哪几家插件——从 manifest 现算，不手写（手写过的版本号已经错过两轮）
    mapFrom = {}
    for v in (dm.get('files') or {}).values():
        k = '%s %s' % (v.get('addon'), v.get('addonVersion'))
        mapFrom[k] = mapFrom.get(k, 0) + 1
    mapSrcName = '、'.join('%s %d 张' % (k, n) for k, n in sorted(mapFrom.items()))
    originOf = {k: (v.get('origin') or '') for k, v in (dm.get('files') or {}).items()}
    for did, bs in sorted((snap.get('bosses') or {}).items()):
        # 首领名必须是这座本真有的那一条；对不上的一律不进成品（快照的 unmapped 里留着原因）
        keep = {n: pts for n, pts in bs.items() if n in bosses_of.get(did, set())}
        if keep:
            e = out.setdefault(did, {})
            e['bossPos'] = keep
            if dmaps.get(did):
                e['bossMap'] = dmaps[did]
                e['bossMapKind'] = originOf.get(did) or '未知'
                px = mapPixels.get(did) or []
                if len(px) == 2 and px[0] and px[1]:
                    e['bossMapRatio'] = '%d/%d' % (px[0], px[1])
            n_boss += len(keep)
    # 两类底图各多少座：按成品里真挂上图的座数现算，不按 manifest 的文件数
    #（一张斯坦索姆摊到两座本，按文件数算就对不上 bossMapped）
    mapSplit, drawnNames = {}, []
    for did, e in out.items():
        if e.get('bossMap'):
            mapSplit[e['bossMapKind']] = mapSplit.get(e['bossMapKind'], 0) + 1
            if e['bossMapKind'] == 'addon-drawn':
                drawnNames.append(dun_name.get(did, did))
    mapCounts = {'game': mapSplit.get('game-capture', 0),
                 'drawn': mapSplit.get('addon-drawn', 0),
                 'unknown': sum(v for k, v in mapSplit.items()
                                if k not in ('game-capture', 'addon-drawn'))}
    mapCounts['total'] = sum(mapCounts.values())
    for did in out:
        out[did]['provenance'] = [dict(prov)]

    payload = {
        'meta': {
            'kind': 'dungeon-geo',
            'generatedAt': date.today().isoformat(),
            'method': 'tools/extract-df-geo.py 抽快照 → tools/merge-dungeon-geo.py 出这份成品',
            'note': '副本入口（在区域图上的百分比坐标）与各首领在副本内部图上的位置。'
                    '只有副本详情页读这一份，列表页不背它。',
            'coordinateNote': '入口坐标的参照物是那一行的「地图编号」所指的区域图；'
                              '首领坐标的参照物是这座本自己的内部图（bossMap 那张）。'
                              '没有 bossMap 的本，首领位置仍只给数字、不画点',
            # 这句是给溯源页直接念的：底图必须分两类交代——游戏里那张副本地图的截图 vs 作者自绘，
            # 座数从成品现算，不手写（手写过的版本号已经错过两轮）。
            'mapNote': ('首领画点的底图分两类：'
                        + '%d 座用的是游戏里那张副本地图（插件作者从游戏里截下来整理的，'
                          '画的就是官方那张图）；' % mapCounts['game']
                        + ('%d 座（%s）游戏内没有地图，用的是插件作者自绘的示意图。'
                           % (mapCounts['drawn'], '、'.join(drawnNames)) if mapCounts['drawn'] else '')
                        + ('另有 %d 座没记上来源类别。' % mapCounts['unknown']
                           if mapCounts['unknown'] else '')
                        + '文件都来自第三方插件（' + mapSrcName + '），'
                          '不是暴雪直接发布的素材文件，2026-10-19 站主决定采用；'
                          '只拿图，作者写的说明一条没取。整目录删掉就退回只显示数字坐标。'),
            'sources': [{'key': 'df', 'name': snap['meta']['source'], 'kind': '第三方插件从客户端读出的位置',
                         'date': snap['meta']['fetched'],
                         'license': '插件 LICENSE：保留所有权利——这一层只取坐标与地图编号，'
                                    '作者写的文字说明一条没取'},
                        # 底图这一层单独记一条：它不是坐标那一层的同一家插件，许可也不同
                        {'key': 'map', 'name': mapSrcName or '本站自绘占位（没有可画点的底图）',
                         'kind': '副本内部底图（%d 座用游戏内地图的截图、%d 座用插件作者自绘）'
                                 % (mapCounts['game'], mapCounts['drawn']),
                         'date': (dm.get('generatedAt') or ''),
                         'license': dm.get('license', '')}],
            'counts': {'entryDungeons': len(snap.get('entry') or {}),
                       'bossDungeons': len(snap.get('bosses') or {}), 'bossRows': n_boss,
                       'bossMapped': len([1 for v in out.values() if v.get('bossMap')]),
                       'bossMapGame': mapCounts['game'], 'bossMapDrawn': mapCounts['drawn'],
                       'droppedRows': (snap['meta'].get('counts') or {}).get('bossSkipped')}
        },
        'dungeons': out
    }
    p = os.path.join(DATA, 'dungeon-geo.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write('\n')
    c = payload['meta']['counts']
    print('副本坐标 → app/data/dungeon-geo.json：入口 %d 座 · 首领位置 %d 座 %d 条（快照里对不上首领先丢 %s 条）'
          % (c['entryDungeons'], c['bossDungeons'], c['bossRows'], c['droppedRows']))


main()
