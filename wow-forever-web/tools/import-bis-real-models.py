#!/usr/bin/env python3
"""Import the verified E12 whole-character GLBs into the web asset registry."""

import csv
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path


WEB = Path(__file__).resolve().parent.parent
ROOT = WEB.parent
SOURCE = Path('/private/tmp/wow-ro/ziliao-export/round9fix-all-bis-3d-reexport')
JOBS = WEB / 'docs/QODER-全职业3D导出清单-2026-10-28.json'
ART = WEB / 'app/data/art.json'
OUTPUT = WEB / 'app/img/models/real'
INDEX = SOURCE / 'round9fix-batch-PACKAGES.txt'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force-source', action='store_true',
                        help='replace optimized site assets with original E12 exports')
    args = parser.parse_args()
    if ART.exists() and not args.force_source:
        current = json.loads(ART.read_text()).get('bisRealModels') or {}
        if any(x.get('optimization') for x in current.get('items') or []):
            raise SystemExit('site uses optimized GLBs; pass --force-source to restore E12 originals')
    source = json.loads(JOBS.read_text())
    if sha(JOBS.read_bytes()) != '78778eda2333f791401d7eb4dc4609497d4aa71720f25b2b8e3925b7291be114':
        raise SystemExit('input job manifest changed')
    jobs = {j['setId'] + '-' + j['faction']: j for j in source['jobs']}
    listed = re.findall(r'(round9fix-[a-z]+-20261029-163328\.zip)\s+(\d+)\s+([0-9a-f]{64})', INDEX.read_text())
    if len(jobs) != 76 or len(listed) != 9:
        raise SystemExit('input count changed')
    payloads = {}
    for name, size, digest in listed:
        path = SOURCE / name
        if path.stat().st_size != int(size) or sha(path.read_bytes()) != digest:
            raise SystemExit('ZIP mismatch: ' + name)
        with zipfile.ZipFile(path) as z:
            if z.testzip():
                raise SystemExit('ZIP damaged: ' + name)
            result = json.loads(z.read('RESULT.json'))
            if result['status'] != 'EXPORTED_PENDING_MAC_REVIEW':
                raise SystemExit('unexpected status: ' + name)
            for row in result['rows']:
                tag = row['tag']
                if tag not in jobs or tag in payloads or row['status'] != 'EXPORTED_PENDING_MAC_REVIEW':
                    raise SystemExit('unexpected job: ' + tag)
                glb = z.read('glb/' + tag + '.glb')
                if glb[:4] != b'glTF' or len(glb) != row['glbBytes'] or sha(glb) != row['glbSha256']:
                    raise SystemExit('GLB mismatch: ' + tag)
                if not row['cloak']['applied']:
                    raise SystemExit('cape missing: ' + tag)
                payloads[tag] = (glb, name)
    if set(payloads) != set(jobs):
        raise SystemExit('job set mismatch')

    OUTPUT.mkdir(parents=True, exist_ok=True)
    items = []
    for tag in sorted(jobs):
        job = jobs[tag]
        glb, zipname = payloads[tag]
        (OUTPUT / (tag + '.glb')).write_bytes(glb)
        rel = 'img/models/real/' + tag + '.glb'
        visible = {x['slot']: x['item'] for x in job['visualDoll']}
        item = {
            'setId': job['setId'], 'faction': job['faction'],
            'raceId': job['raceId'], 'bodyType': job['bodyType'],
            'placementVerdict': 'PASS',
            'file': rel, 'bytes': len(glb), 'sha256': sha(glb),
            'sourceZip': zipname, 'sourceSha256': sha(glb),
            'dollSnapshot': job['doll'], 'visibleItems': visible,
            'displayWeaponItems': job['displayWeaponItems'],
        }
        items.append(item)
    manifest = {
        'origin': 'client-derived', 'clientProduct': 'wowf',
        'clientBuild': '1.60.1.70532',
        'exportMethod': 'wow.export 0.2.19 E12; local CASC; No Animation; E11 cape',
        'inputManifestSha256': sha(JOBS.read_bytes()),
        'sourceIndex': 'round9fix-batch-PACKAGES.txt (20261029-163328)',
        'fallback': 'remove this directory and bisRealModels from art.json',
        'items': items,
    }
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    art = json.loads(ART.read_text())
    art['bisRealModels'] = {'origin': 'client-derived', 'items': items}
    ART.write_text(json.dumps(art, ensure_ascii=False, indent=2) + '\n')
    print('registered', len(items), 'models', sum(x['bytes'] for x in items), 'bytes')


if __name__ == '__main__':
    main()
