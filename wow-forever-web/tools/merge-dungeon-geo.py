#!/usr/bin/env python3
# upstream/df-dungeon-geo.json → src/data/dungeon-geo.json（副本入口与本内首领坐标，成品层）。
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
DATA = os.path.join(ROOT, 'src', 'data')


def main():
    snap = json.load(open(os.path.join(DATA, 'upstream', 'df-dungeon-geo.json'), encoding='utf-8'))
    art = json.load(open(os.path.join(DATA, 'art.json'), encoding='utf-8')).get('maps') or {}
    dz = json.load(open(os.path.join(DATA, 'dungeons.json'), encoding='utf-8'))
    bosses_of = {}
    for key in ('newDungeons', 'classicDungeons', 'raids'):
        for x in dz.get(key) or []:
            bosses_of[x['id']] = {b.get('nameCn') for b in (x.get('bosses') or [])}

    prov = {'type': 'addon', 'url': snap['meta']['source'], 'checkedAt': snap['meta']['fetched'],
            'note': '副本入口与各首领的百分比坐标（第三方插件从客户端读出的位置，本站未进游戏实测）'}

    out, n_boss = {}, 0
    for did, v in sorted((snap.get('entry') or {}).items()):
        mid = str(v['mapId'])
        out.setdefault(did, {})['entry'] = {
            'mapId': mid, 'x': v['x'], 'y': v['y'], 'zone': v['zone'],
            'mapFile': art.get(mid), 'noMap': mid not in art}
    for did, bs in sorted((snap.get('bosses') or {}).items()):
        # 首领名必须是这座本真有的那一条；对不上的一律不进成品（快照的 unmapped 里留着原因）
        keep = {n: pts for n, pts in bs.items() if n in bosses_of.get(did, set())}
        if keep:
            out.setdefault(did, {})['bossPos'] = keep
            n_boss += len(keep)
    for did in out:
        out[did]['provenance'] = [dict(prov)]

    payload = {
        'meta': {
            'kind': 'dungeon-geo',
            'generatedAt': date.today().isoformat(),
            'method': 'tools/extract-df-geo.py 抽快照 → tools/merge-dungeon-geo.py 出这份成品',
            'note': '副本入口（在区域图上的百分比坐标）与各首领在副本内部图上的位置。'
                    '只有副本详情页读这一份，列表页不背它。',
            'coordinateNote': '入口坐标的参照物是那一行的「地图编号」所指的区域图；首领坐标的参照物是这座本自己的'
                              '内部图，本站目前没有那批内部图，所以先落数据、不在图上画点',
            'sources': [{'key': 'df', 'name': snap['meta']['source'], 'kind': '第三方插件从客户端读出的位置',
                         'date': snap['meta']['fetched'],
                         'license': '插件 LICENSE：保留所有权利——本站只取坐标与地图号，不取任何文字与图'}],
            'counts': {'entryDungeons': len(snap.get('entry') or {}),
                       'bossDungeons': len(snap.get('bosses') or {}), 'bossRows': n_boss,
                       'droppedRows': (snap['meta'].get('counts') or {}).get('bossSkipped')}
        },
        'dungeons': out
    }
    p = os.path.join(DATA, 'dungeon-geo.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write('\n')
    c = payload['meta']['counts']
    print('副本坐标 → src/data/dungeon-geo.json：入口 %d 座 · 首领位置 %d 座 %d 条（快照里对不上首领先丢 %s 条）'
          % (c['entryDungeons'], c['bossDungeons'], c['bossRows'], c['droppedRows']))


main()
