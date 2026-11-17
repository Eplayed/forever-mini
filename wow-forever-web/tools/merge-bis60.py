#!/usr/bin/env python3
"""
merge-bis60.py — 把 Lv.60 团前 Pre-Raid BiS（upstream/cwf-bis60.json）与海加尔峰 T1 团本套装
（upstream/df-raid-sets.json）合并写入 app/data/bis.json，保持原有 38 套 30 级配装与 36 套图鉴原样不动。
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT, 'app', 'data')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_no_percent(obj, label):
    raw = json.dumps(obj, ensure_ascii=False)
    hits = re.findall(r'\d+%', raw)
    if hits:
        sys.exit('%s 含百分比字样（触犯红线）：%s' % (label, hits[:5]))


def main():
    bis_path = os.path.join(DATA_DIR, 'bis.json')
    items_path = os.path.join(DATA_DIR, 'items.json')
    dungeons_path = os.path.join(DATA_DIR, 'dungeons.json')
    cwf_path = os.path.join(DATA_DIR, 'upstream', 'cwf-bis60.json')
    raid_path = os.path.join(DATA_DIR, 'upstream', 'df-raid-sets.json')

    for p in (bis_path, items_path, dungeons_path, cwf_path, raid_path):
        if not os.path.isfile(p):
            sys.exit('缺少必需文件：%s' % p)

    bis = load_json(bis_path)
    items_raw = load_json(items_path)
    dungeons_raw = load_json(dungeons_path)
    cwf = load_json(cwf_path)
    raid = load_json(raid_path)

    base_ids = {int(it['id']) for it in (items_raw.get('items') or []) if 'id' in it}
    dungeon_ids = {
        d['id']
        for key in ('newDungeons', 'classicDungeons', 'raids')
        for d in (dungeons_raw.get(key) or [])
        if 'id' in d
    }

    cwf_meta = cwf.get('meta') or {}
    extra_items = cwf_meta.get('extraItems') or {}
    extra_ids = {int(k) for k in extra_items.keys()}
    bis60_sets = cwf.get('sets') or []

    check_no_percent(cwf, 'cwf-bis60.json')
    check_no_percent(raid, 'df-raid-sets.json')

    if len(bis60_sets) != 27:
        sys.exit('cwf-bis60.json 期望 27 套，实际 %d 套' % len(bis60_sets))

    seen_60 = set()
    missing_items = set()
    bad_dungeons = set()
    for st in bis60_sets:
        sid = st.get('id')
        if not sid or sid in seen_60:
            sys.exit('60 级配装 id 缺失或重复：%s' % sid)
        seen_60.add(sid)
        if st.get('level') != 60 or not st.get('url') or not st.get('fetched'):
            sys.exit('%s 缺少 level=60 / url / fetched' % sid)
        for d in st.get('doll') or []:
            iid = int(d['item'])
            if iid not in base_ids and iid not in extra_ids:
                missing_items.add(iid)
        for arr in (st.get('alts') or {}).values():
            for iid in arr:
                iid = int(iid)
                if iid not in base_ids and iid not in extra_ids:
                    missing_items.add(iid)
        for ref in (st.get('refs') or {}).values():
            did = ref.get('dungeonId')
            if did and did not in dungeon_ids:
                bad_dungeons.add(did)

    if missing_items:
        sys.exit('60 级配装有未登记的物品 ID：%s' % sorted(missing_items)[:10])
    if bad_dungeons:
        sys.exit('60 级配装有未对齐 dungeons.json 的副本 ID：%s' % sorted(bad_dungeons)[:10])

    raid_sets = raid.get('raidSets') or []
    if len(raid_sets) != 18:
        sys.exit('df-raid-sets.json 期望 18 套，实际 %d 套' % len(raid_sets))
    seen_raid = set()
    for rs in raid_sets:
        rid = rs.get('id')
        if not rid or rid in seen_raid:
            sys.exit('T1 团本套装 id 缺失或重复：%s' % rid)
        seen_raid.add(rid)
        if not rs.get('setId') or not rs.get('name') or not rs.get('pieceCount'):
            sys.exit('T1 团本套装字段缺失：%s' % rid)

    bis.setdefault('meta', {})
    bis['meta']['bis60Meta'] = cwf_meta
    bis['bis60Sets'] = bis60_sets
    bis['meta']['raidSetsMeta'] = raid.get('meta') or {}
    bis['raidSets'] = raid_sets

    blob = json.dumps(bis, ensure_ascii=False, indent=1)
    with open(bis_path, 'w', encoding='utf-8') as f:
        f.write(blob + '\n')

    print('已写入 bis.json：Lv.30 %d 套（未改）/ 套装图鉴 %d 套 / Lv.60 团前 %d 套（兜底物品 %d 件）/ 海加尔峰 T1 %d 套' % (
        len(bis.get('sets') or []),
        len(bis.get('itemSets') or []),
        len(bis60_sets),
        len(extra_items),
        len(raid_sets),
    ))


if __name__ == '__main__':
    main()
