#!/usr/bin/env python3
"""Import the fact columns from a Windows GearInsight extraction into upstream data.

Descriptions in the addon CSV are intentionally discarded. The previous snapshot is
kept separately so a missing row in a newer addon does not silently delete it.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'app/data/upstream/gi-achievements.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True, type=Path)
    ap.add_argument('--file-hashes', required=True, type=Path)
    ap.add_argument('--date', required=True)
    args = ap.parse_args()

    with args.file_hashes.open(newline='', encoding='utf-8') as f:
        source = [r for r in csv.DictReader(f)
                  if r['plugin'] == 'GearInsight_Forever' and
                  r['install_root'] == '_cn_beta_' and r['rel_path'] == 'Data.lua']
    if len(source) != 1 or len(source[0]['sha256']) != 64:
        raise SystemExit('expected exactly one hashed _cn_beta_/GearInsight_Forever/Data.lua')

    with args.csv.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    ids = [int(r['achievement_id']) for r in rows]
    if len(rows) != 210 or len(ids) != len(set(ids)):
        raise SystemExit('achievement count/IDs changed; inspect the source before importing')
    out = []
    for r in rows:
        if not r['title_cn'] or not r['title_en'] or not r['top_cn']:
            raise SystemExit('missing title/category on achievement %s' % r['achievement_id'])
        out.append({
            'achId': int(r['achievement_id']),
            'name': r['title_cn'],
            'nameEn': r['title_en'],
            'top': r['top_cn'],
            'topEn': r['top_en'],
            'cat': r['category_cn'],
            'catEn': r['category_en'],
            'iconKey': r['icon'] or None,
            'lgRaw': int(r['legacy_points'] or 0),
        })
    out.sort(key=lambda x: x['achId'])
    doc = {
        'meta': {
            'source': 'GearInsight_Forever 0.5.6 Data.lua 的 achievements 表',
            'addonVersion': '0.5.6',
            'installRoot': '_cn_beta_',
            'originSha256': source[0]['sha256'],
            'extractCsvSha256': hashlib.sha256(args.csv.read_bytes()).hexdigest(),
            'fetched': args.date,
            'counts': {'total': len(out)},
            'droppedFields': ['desc_cn', 'desc_en'],
            'note': 'Data.lua 文件头自报 build 1.60.1.70425；lgRaw 仅留快照，不作为成品字段。',
        },
        'achievements': out,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('imported', len(out), 'GI achievements to', OUT)


if __name__ == '__main__':
    main()
