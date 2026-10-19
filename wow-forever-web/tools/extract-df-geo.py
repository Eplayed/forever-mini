#!/usr/bin/env python3
# 从 DungeonsForever 抽两张**坐标表**：副本入口（在区域图上的哪儿）与本内首领位置。
#
# 为什么只抽这两张（2026-10-19 站主拍板"提取副本入口和本内首领坐标"）：
#   站内 38 座本**根本没有"入口在哪"这一层**，首领也只有名单与掉落、没有位置。
#   这两层是新的，不是拿它覆盖我们已有的东西。
#
# DF 的 LICENSE 写着「Copyright © 2026 圆圆 · 保留所有权利」。取的是**坐标与地图号**这一层
# （游戏内事实），一律不取：任何成段中文说明、任务目标文本、攻略句子、图（Media/ 里那些
# 自绘副本图与载入图）、BiS 与职业建议。快照 meta 里把这条边界写死，合并层再卡一道。
#
# 首领坐标表是以**英文名**为键的，我们站内首领只有中文名，所以中间要过一座桥：
#   Data_DungeonLoot 的每行是 { 英文名, 中文名, "", npcId, {掉落…} } —— 只取前两列当名字映射，
#   掉落与概率（那行里的 100 / nil 是掉率）一律不读。
#
# 用法：python3 tools/extract-df-geo.py [--src <插件根目录>] [--out-dir <upstream 目录>]
import json
import os
import re
import sys
from datetime import date

HOME = os.path.expanduser('~')
DEF_SRC = os.path.join(HOME, 'Documents', 'project', '.scratch', 'wow')
WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# DF 自己的一套副本 slug 与站内 id 不一样，这 11 个是机械对应（下划线→横线之外的那些）。
# 对不上的宁可留在 unmapped 里，也不许猜一个塞进去。
ALIAS = {
    'excavation_wetlands': 'whelgars-excavation',
    'razorfen_downs': 'razor-krendor',
    'sm_armory': 'scarlet-monastery-armory',
    'sm_cathedral': 'scarlet-monastery-cathedral',
    'sm_graveyard': 'scarlet-monastery-graveyard',
    'sm_library': 'scarlet-monastery-library',
    'stratholme_main': 'stratholme-main-gate',
    'stratholme_service': 'stratholme-service-gate',
    'the_deadmines': 'deathmine',
    'the_stockade': 'the-stocks',
    'zul_farrak': 'zulfarrak',
}


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def our_id(df_slug):
    return ALIAS.get(df_slug, df_slug.replace('_', '-'))


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


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def parse_entry(text):
    """ns.DungeonEntry[slug] = { 地图号, x, y, "区域名" } —— 入口在**区域图**上的百分比坐标。"""
    out = {}
    for m in re.finditer(r'\["([a-z_0-9]+)"\]\s*=\s*\{\s*(\d+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*"([^"]*)"', text):
        out[m.group(1)] = {'mapId': int(m.group(2)), 'x': float(m.group(3)),
                           'y': float(m.group(4)), 'zone': m.group(5)}
    return out


def split_dungeons(text):
    """把 `ns.X = { ["slug"] = { ... }, ["slug2"] = {...} }` 切成 (slug, 正文) 段。"""
    segs = re.split(r'^\s{4}(?:\[")?([a-z_0-9]+)"?\]?\s*=\s*\{', text, flags=re.M)
    return [(segs[i], segs[i + 1]) for i in range(1, len(segs) - 1, 2)]


def parse_name_bridge(text):
    """Data_DungeonLoot 每行开头是 { "英文名", "中文名", "", "npcId", {掉落…} ——
       只取前两列当名字映射；后面那一串（含掉率数字）一律不读。"""
    out = {}
    for slug, body in split_dungeons(text):
        for m in re.finditer(r'\{\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,', body):
            if m.group(1):
                out.setdefault(slug, {})[m.group(1)] = m.group(2)
    return out


def parse_boss_pos(text):
    """ns.BossPos[slug][首领英文名] = { {x, y[, 层]}, ... } —— 坐标是**副本内部那张图**的百分比。"""
    out = {}
    cur = None
    for line in text.splitlines():
        m = re.match(r'^\s{4}\["([a-z_0-9]+)"\]\s*=\s*\{', line)
        if m:
            cur = m.group(1)
            out[cur] = {}
            continue
        m = re.match(r'^\s{8}\["([^"]+)"\]\s*=\s*\{(.*)$', line)
        if m and cur:
            pts = []
            for x, y, fl in re.findall(r'\{\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*(\d+))?\s*\}', m.group(2)):
                pts.append({'x': float(x), 'y': float(y), 'floor': int(fl) if fl else None})
            if pts:
                out[cur][m.group(1)] = pts
    return out


def main():
    src = arg('--src', DEF_SRC)
    out_dir = arg('--out-dir', os.path.join(WEB, 'src', 'data', 'upstream'))
    data_dir = os.path.join(src, 'DungeonsForever', 'Core', 'Data')
    need = ['Data_DungeonEntry.lua', 'Data_BossPos.lua', 'Data_DungeonLoot.lua']
    for f in need:
        p = os.path.join(data_dir, f)
        if not os.path.exists(p):
            sys.exit('找不到 %s——这一份要的是 DF 插件目录里的三张表（入口、首领位置、掉落名单）' % p)
    ver = toc_version(os.path.join(src, 'DungeonsForever'), 'DungeonsForever')
    entry = parse_entry(read(os.path.join(data_dir, 'Data_DungeonEntry.lua')))
    bridge = parse_name_bridge(read(os.path.join(data_dir, 'Data_DungeonLoot.lua')))
    pos = parse_boss_pos(read(os.path.join(data_dir, 'Data_BossPos.lua')))

    # 站内 id 认得过来才收；认不得的留在 unmapped 里，不猜
    dz = json.load(open(os.path.join(WEB, 'src', 'data', 'dungeons.json'), encoding='utf-8'))
    known = {}
    for key in ('newDungeons', 'classicDungeons', 'raids'):
        for x in dz.get(key) or []:
            known[x['id']] = {b.get('nameCn') for b in (x.get('bosses') or [])}

    ent_out, ent_skip = {}, []
    for slug, v in sorted(entry.items()):
        oid = our_id(slug)
        if oid in known:
            ent_out[oid] = dict(v, dfSlug=slug)
        else:
            ent_skip.append({'dfSlug': slug, 'why': '站内没有这个副本 id'})

    boss_out, boss_skip, rows = {}, [], 0
    for slug, bosses in sorted(pos.items()):
        oid = our_id(slug)
        br = bridge.get(slug) or {}
        if oid not in known:
            boss_skip.extend([{'dfSlug': slug, 'nameEn': en, 'why': '站内没有这个副本 id'} for en in bosses])
            continue
        for en, pts in sorted(bosses.items()):
            cn = br.get(en)
            if not cn:
                boss_skip.append({'dfSlug': slug, 'nameEn': en, 'why': 'DF 的掉落名单里没给这个英文名的中文名'})
                continue
            if cn not in known[oid]:
                boss_skip.append({'dfSlug': slug, 'nameEn': en, 'nameCn': cn, 'why': '站内这座本没有同名首领'})
                continue
            boss_out.setdefault(oid, {})[cn] = pts
            rows += 1

    payload = {
        'meta': {
            'source': 'DungeonsForever %s（Core/Data 的 Data_DungeonEntry.lua 与 Data_BossPos.lua）' % ver,
            'originFiles': [os.path.join(data_dir, f) for f in need],
            'fetched': date.today().isoformat(),
            'what': '副本入口在区域图上的百分比坐标 + 各首领在副本内部图上的百分比坐标（第三值是该图的层号）',
            'boundary': '只取坐标、地图号与名字映射。DF 的 LICENSE 是「保留所有权利」，'
                        '它的任何成段说明、任务目标文本、攻略句子、自绘副本图与载入图一律不取',
            'nameBridge': '首领位置以英文名为键，站内首领只有中文名，中间过 Data_DungeonLoot 的'
                          '「英文名→中文名」那一层（那座桥只取前两列，掉落与掉率不读）',
            'slugAlias': ALIAS,
            'counts': {'entryDungeons': len(ent_out), 'entrySkipped': len(ent_skip),
                       'bossDungeons': len(boss_out), 'bossRows': rows, 'bossSkipped': len(boss_skip)}
        },
        'entry': ent_out,
        'bosses': boss_out,
        'unmapped': {'entry': ent_skip, 'bosses': boss_skip}
    }
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    out = os.path.join(out_dir, 'df-dungeon-geo.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write('\n')
    c = payload['meta']['counts']
    print('DF %s：入口 %d 座（对不上 %d）· 首领 %d 座 %d 行（翻不出或对不上 %d 行）→ %s'
          % (ver, c['entryDungeons'], c['entrySkipped'], c['bossDungeons'], c['bossRows'],
             c['bossSkipped'], os.path.relpath(out, WEB)))


main()
