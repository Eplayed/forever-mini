#!/usr/bin/env python3
"""Lightweight task index. Reads Git paths/stat metadata, not data or document bodies."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WEB = REPO / 'wow-forever-web'
STATE = WEB / 'docs/PROJECT-INDEX.json'
GUIDE = WEB / 'docs/PROJECT-INDEX.md'
TOPICS = {
 'rules': ('规则与交接', ['AGENTS.md', 'ROLES.md', 'wow-forever-web/AGENTS.md', 'wow-forever-web/docs/README.md']),
 'launch': ('部署与线上验收', ['wow-forever-web/tools/release-package.py', 'wow-forever-web/tools/deploy-gh-pages.py', 'wow-forever-web/tools/pkg-verify.py', 'wow-forever-web/tools/app-assets.py', 'wow-forever-web/app/vite.config.js', 'wow-forever-web/docs/VERIFY-pages-and-index-2026-10-21.md']),
 'spells': ('技能取值与分歧', ['wow-forever-web/tools/merge-spells.py', 'wow-forever-web/tools/extract-plugin-tables.py', 'wow-forever-web/app/src/pages/SkillsPage.vue', 'wow-forever-web/app/src/pages/ProvenancePage.vue']),
 'items': ('物品与配装', ['wow-forever-web/tools/merge-items-detail.py', 'wow-forever-web/tools/extract-addon-items-detail.py', 'wow-forever-web/app/src/lib/item-stats.js', 'wow-forever-web/app/src/pages/BisPage.vue']),
 'maps': ('地图与素材', ['wow-forever-web/tools/extract-df-geo.py', 'wow-forever-web/tools/merge-dungeon-geo.py', 'wow-forever-web/tools/fetch-art.py', 'wow-forever-web/app/src/components/PinMap.vue', 'wow-forever-web/docs/VERIFY-prelaunch-independent-2026-10-20.md']),
 'updates': ('动态筛选', ['wow-forever-web/app/src/pages/UpdatesPage.vue', 'wow-forever-web/app/tests/updates-filter.spec.js']),
 'business': ('换轨与内容主线', ['wow-forever-web/docs/OPS-换轨方向复核-2026-10-20.md', 'wow-forever-web/docs/OPS-三渠道内容优化-2026-10-19.md']),
 'tests': ('验证入口', ['.github/workflows/gates.yml', 'wow-forever-web/app/package.json', 'wow-forever-web/tools/site-check.py', 'wow-forever-web/tools/route-smoke.py', 'wow-forever-web/tools/build-data.js']),
}

def git(*args):
 return subprocess.check_output(['git', '-C', str(REPO), *args]).decode('utf-8')

def inventory():
 paths = sorted(set(git('ls-files', '-co', '--exclude-standard', '-z').split('\0')) - {''})
 rows = []
 for name in paths:
  if name in ('wow-forever-web/docs/PROJECT-INDEX.md', 'wow-forever-web/docs/PROJECT-INDEX.json'):
   continue
  if any(x in name.split('/') for x in ('screenshots', 'screenshots-archive', 'data-base', 'logs', 'node_modules', 'public', 'dist', 'release', '.git')):
   continue
  if name.startswith('wow-forever-web/app/data/') or name.startswith('wow-forever-web/app/img/'):
   continue
  p = REPO / name
  if p.suffix not in ('.md', '.py', '.js', '.vue', '.yml', '.yaml', '.json', '.sh') or not p.is_file():
   continue
  st = p.stat()
  rows.append({'path': name, 'bytes': st.st_size, 'mtimeNs': st.st_mtime_ns})
 return rows

def main():
 ap = argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--topic', choices=TOPICS)
 ap.add_argument('--check', action='store_true', help='Return 1 if stale; do not update')
 ap.add_argument('--find', help='Search path names only, without reading file contents')
 args = ap.parse_args()
 rows = inventory()
 head = git('rev-parse', 'HEAD').strip()
 sig = hashlib.sha256(json.dumps([head, rows], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
 old = json.loads(STATE.read_text()) if STATE.exists() else {}
 if args.check:
  fresh = old.get('fingerprint') == sig and GUIDE.exists()
  print('索引有效（文件元信息检查，不是产品验收）' if fresh else '索引过期：运行 python3 wow-forever-web/tools/project-index.py')
  return 0 if fresh else 1
 state = {'head': head, 'fingerprint': sig, 'method': 'Git路径＋size/mtime；不读文档/数据正文，不代替原件。', 'files': rows}
 STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1)+'\n')
 lines = ['# 项目按需读取索引', '', '自动生成。先定位再读原件；本索引不是授权、来源或验收结果。', '',
          '## 用法', '', '```sh', 'python3 wow-forever-web/tools/project-index.py --topic launch',
          'python3 wow-forever-web/tools/project-index.py --find merge',
          'python3 wow-forever-web/tools/project-index.py --check', '```', '',
          '普通调用自动刷新；--check只检查。无后台监听，不定时唤醒AI。HEAD或被索引文件size/mtime变化即失效；大数据/图片不在快照中，需要时直接读目标记录。', '',
          '## 读取顺序', '', '1. 根规则＋目标子项目规则；ROLES只读末尾相关交接。',
          '2. 运行对应topic，只读列出的入口和当前任务指定交付。',
          '3. 用git diff --stat和限定文件diff确定变更；大JSON按ID提取，日志只看失败与末尾。',
          '4. 只有入口不足才扩大rg检索。不要把全部历史VERIFY、数据、截图清单灌入上下文。', '',
          '## 任务入口', '']
 for key,(title,paths) in TOPICS.items():
  lines += ['### '+key+' · '+title, '']
  lines += ['- `'+p+'`'+('（文件不存在，需定位）' if not (REPO/p).exists() else '') for p in paths]
  lines += ['']
 GUIDE.write_text('\n'.join(lines)+'\n')
 print('已刷新 %d 条文件路径；HEAD %s。没有读取其正文。' % (len(rows), head[:8]))
 if args.topic:
  title, paths = TOPICS[args.topic]
  print(title+'\n'+'\n'.join(paths))
 if args.find:
  found = [r['path'] for r in rows if args.find.lower() in r['path'].lower()]
  print('\n'.join(found[:40])); print('命中%d条，最多显示40条。' % len(found))
 return 0

if __name__ == '__main__':
 raise SystemExit(main())
