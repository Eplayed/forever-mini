#!/usr/bin/env python3
# 抓 wowforever.wclbox.com 的「BiS 配装」38 套名单（站主 2026-10-16 拍板走 C 方案）。
#
# 为什么必须开浏览器而不是 curl：每套名单有联盟 / 部落两个版本，SSR 只给联盟那一版，
# 部落版是点 .pz-faction button 之后客户端换数据（实测战士 PvE 16 格里 4 件不一样）。
# 其余结构都是 SSR 好的，能直接读 DOM。
#
# 取什么（红线 2026-10-16 例外条款里点名的那几类事实字段）：
#   职业 / 专精 / 模式 / 等级段 / 阵营 / 部位 / 物品 ID / 品质 / 图标文件名 / 同部位备选顺序 /
#   配方要的材料（物品 ID + 数量）/ 来源的结构化指向（配方页 / 任务 ID / 副本 slug 这些链接本身）。
# 不取什么：**该页 .pz-from 与 .pz-stats-note 里的任何中文句子一律不落盘**。
#   实测那一段长这样："从奥特兰克花岗岩里拿到，希尔斯布莱德丘陵开启铁质宝箱世界掉落，
#   12 张掉落表里都有，也可以去拍卖行找按本页权重比第二件高 20%"、"群体打击者9-60，诺莫瑞根，掉率约 0.3%"——
#   里面同时有①它写的描述文案、②它的权重结论（"比第二件高 20%"）、③**掉率百分比**（红线明写不许出现）。
#   所以这里只把链接拆成 {kind, id}，文字全部丢掉；"这件从哪拿"由合并阶段回我们自己的
#   items-detail.json 查（那是本站已有的掉落归属口径），不抄它的句子。
# 礼貌：38 页、单线程、页间 0.6s、点一次阵营按钮算一次交互，不加并发。
# 用法：python3 tools/scrape-wclbox-bis.py [--out-dir app/data/upstream] [--only warrior]
import argparse
import json
import os
import re
import sys
import time
from datetime import date

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://wowforever.wclbox.com'
# 站内一律用官方中文职业名（与 spells / races / classes 线同一套叫法）
CLASS_CN = {'warrior': '战士', 'paladin': '圣骑士', 'hunter': '猎人', 'rogue': '潜行者',
            'priest': '牧师', 'warlock': '术士', 'mage': '法师', 'druid': '德鲁伊',
            'shaman': '萨满祭司'}
# 38 套：职业基础页 = 该职业的第一套（战士是 PvE），带 spec 的是其余各套
ROUTES = [
    ('warrior', ''), ('warrior', 'pvp'), ('warrior', 'tank'),
    ('hunter', ''), ('hunter', 'pvp'),
    ('mage', ''), ('mage', 'pvp'), ('mage', 'fire'), ('mage', 'fire-pvp'), ('mage', 'arcane'),
    ('rogue', ''), ('rogue', 'assassination'), ('rogue', 'pvp'), ('rogue', 'pvp-hemo'),
    ('priest', ''), ('priest', 'shadow-pvp'), ('priest', 'holy'), ('priest', 'discipline-pvp'),
    ('warlock', ''), ('warlock', 'pvp'),
    ('paladin', ''), ('paladin', 'retribution-pvp'), ('paladin', 'holy'),
    ('paladin', 'holy-pvp'), ('paladin', 'shockadin'), ('paladin', 'tank'),
    ('druid', ''), ('druid', 'feral-pvp'), ('druid', 'tank'), ('druid', 'balance'),
    ('druid', 'balance-pvp'), ('druid', 'restoration'), ('druid', 'restoration-pvp'),
    ('shaman', ''), ('shaman', 'elemental-pvp'), ('shaman', 'enhancement'),
    ('shaman', 'enhancement-pvp'), ('shaman', 'restoration'),
]

# 读一整套：纸娃娃（16 格，含两枚戒指与两个饰品）+ 每个部位的备选列表
JS_READ = r"""() => {
  const q = (n, r) => (r || document).querySelector(n);
  const txt = (n, r) => { const e = q(n, r); return e ? e.textContent.trim() : null; };
  const icon = (img) => { const m = /\/tubiao\/([A-Za-z0-9_]+)\./.exec(img || ''); return m ? m[1] : null; };
  const doll = [...document.querySelectorAll('.pz-doll .pz-cell-item[data-item]')].map(c => ({
    slot: txt('small', c), item: Number(c.getAttribute('data-item')),
    name: txt('b', c), iconKey: icon((q('img', c) || {}).getAttribute ? q('img', c).getAttribute('src') : ''),
    ench: txt('.pz-cell-enchant', c),
    quality: (() => { const b = q('b', c); const m = /\bq(\d)\b/.exec(b ? b.className : ''); return m ? Number(m[1]) : null; })()
  }));
  const slots = [...document.querySelectorAll('section.pz-slot')].map(s => ({
    slotKey: (s.getAttribute('id') || '').replace(/^slot-/, ''),
    slot: txt('h2', s),
    rows: [...s.querySelectorAll('li.pz-row')].map(r => {
      const a = q('a[data-item]', r), nm = q('.pz-name', r);
      const from = q('.pz-from', r);
      // 链接只留"指向哪个实体"，文字一律不要（那是它写的句子）
      const refs = [...(from ? from.querySelectorAll('a') : [])].map(x => x.getAttribute('href') || '').map(h => {
        let m = /^\/zhuanye\/([a-z-]+)\/peifang/.exec(h); if (m) return { kind: 'recipe', prof: m[1] };
        m = /^\/renwu\/(\d+)/.exec(h); if (m) return { kind: 'quest', id: Number(m[1]) };
        m = /^\/wupin\/(\d+)/.exec(h); if (m) return { kind: 'item', id: Number(m[1]) };
        m = /^\/(fuben|tuiben)\/([a-z0-9-]+)/.exec(h); if (m) return { kind: 'dungeon', id: m[2] };
        m = /^\/shangren\/(\d+)/.exec(h); if (m) return { kind: 'vendor', id: Number(m[1]) };
        return { kind: 'other' };
      }).filter(x => x.kind !== 'other');
      const m = /\bq(\d)\b/.exec(nm ? nm.className : '');
      // 括号里的数字是技能点（锻造（150）/ 附魔 210）——只抠这个数，整句不留
      const ft = from ? from.textContent : '';
      const sk = /（[^（）]*?(\d+)[^（）]*?）/.exec(ft.replace(/\s+/g, ''));
      return {
        item: Number(a.getAttribute('data-item')),
        // 名字只当交叉核对用：成品页显示的是我们 items.json 里的名字，两边不一样就两个都留并标注
        name: nm ? nm.textContent.trim() : null,
        // 附魔行才有：这条附魔贴在哪个部位上（.pz-enchant-slots）
        slotOf: txt('.pz-enchant-slots', r),
        skill: sk ? Number(sk[1]) : null,
        quality: m ? Number(m[1]) : null,
        iconKey: icon((q('img', r) || {}).getAttribute ? q('img', r).getAttribute('src') : ''),
        refs: refs
      };
    }),
    mats: [...s.querySelectorAll('li.pz-row')].map(r =>
      [...r.querySelectorAll('.pz-mat')].map(x => ({
        item: Number(x.getAttribute('data-item')),
        n: Number((x.querySelector('b') || {}).textContent || 0) })))
  }));
  return { doll: doll, slots: slots,
           h1: txt('h1'), tabs: [...document.querySelectorAll('.pz-tabs button, [role=tab]')].map(b => b.textContent.trim()) };
}"""

JS_CLICK_FACTION = """(name) => {
  const b = [...document.querySelectorAll('.pz-faction button')].find(x => x.textContent.indexOf(name) >= 0);
  if (!b) return false; b.click(); return true;
}"""


def scrape(only):
    out = []
    with sync_playwright() as p:
        br = p.chromium.launch(channel='chrome', headless=True)
        pg = br.new_page(viewport={'width': 1440, 'height': 1100})
        for cls, spec in ROUTES:
            if only and cls not in only:
                continue
            path = '/peizhuang/' + cls + ('/' + spec if spec else '')
            url = BASE + path
            pg.goto(url, wait_until='networkidle')
            pg.wait_for_selector('.pz-doll .pz-cell-item[data-item]', timeout=25000)
            pg.wait_for_timeout(700)
            ally = pg.evaluate(JS_READ)
            horde = None
            if pg.evaluate(JS_CLICK_FACTION, '部落'):
                pg.wait_for_timeout(900)
                horde = pg.evaluate(JS_READ)
            lv = re.search(r'(\d+)\s*级', ally.get('h1') or '')
            out.append({'classSlug': cls, 'classCn': CLASS_CN[cls], 'specSlug': spec,
                        'url': url, 'level': int(lv.group(1)) if lv else None,
                        'h1': ally.get('h1'), 'tabs': ally.get('tabs'),
                        'alliance': {'doll': ally['doll'], 'slots': ally['slots']},
                        'horde': ({'doll': horde['doll'], 'slots': horde['slots']} if horde else None)})
            print('  %-9s %-16s %2d 格 / %2d 部位  %s' % (
                cls, spec or '(默认)', len(ally['doll']), len(ally['slots']), url))
            time.sleep(0.6)
        br.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default=os.path.join(ROOT, "app", "data", 'upstream'))
    ap.add_argument('--only', action='append', help='只抓这些职业（调试用）')
    a = ap.parse_args()
    sets = scrape(a.only)
    if not sets:
        print('一套没抓到', file=sys.stderr)
        return 2
    n_item = sum(len(s['alliance']['doll']) + (len(s['horde']['doll']) if s['horde'] else 0) for s in sets)
    doc = {'meta': {'source': BASE + '/peizhuang', 'site': '新手盒子 · 魔兽世界无限数据库',
                    'scrapedAt': date.today().isoformat(),
                    'method': 'tools/scrape-wclbox-bis.py（真浏览器：联盟读 SSR 后的纸娃娃，点 .pz-faction 的「部落」再读一遍）',
                    'counts': {'sets': len(sets), 'dollCells': n_item,
                               'classes': len(set(x['classSlug'] for x in sets))},
                    'notTaken': '该页的成段中文说明、属性优先级、循环建议、.pz-stats-note 那句计算口径一律没取（红线）'},
           'sets': sets}
    dst = os.path.join(a.out_dir, 'wclbox-bis.json')
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
    print('写出 %s：%d 套 / 纸娃娃共 %d 格 / %d 个职业' % (dst, len(sets), n_item, doc['meta']['counts']['classes']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
