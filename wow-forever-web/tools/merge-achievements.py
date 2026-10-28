#!/usr/bin/env python3
# 成就合并：新版 GI 目录 + 旧版独有行兜底 + 参考站端点 → app/data/achievements.json。
#
# 分级规则（这条线唯一需要判断的地方）：
#   L0 = id 对得上参考站端点**且中文名逐字相同**（两源互证，可自动回查）；实测 46/46 全一致；
#   L1 = 只有 GI 一家给的（165 条，beta 客户端解包转述，但没有第二个源能逐字回查）。
#   两源 id 对上而名字不同的 → 两个都留（nameAlt）并停 L1，不替谁圆。
# 分类：对得上的用参考站的 category（英文 slug + 中文名都齐），对不上的用 GI 的 top/cat 中文。
# 一律不带成就描述（GI 的 d、参考站的 text 在抽取阶段就删了，这里也不会有）。
# 幂等：排序与缩进固定，重跑字节一致。
import json
import os
import re
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'data')

# 大类 → 稳定短号。界面筛选与搜索跳转都读这个短号（?g=adv），不拿中文大类名当参数：
# 中文名进 query 要各处做编码对照，改一个字就静默筛不到东西。
# 顺序也是界面的显示顺序（玩家最常查的排前面）。新增大类忘了登记 → 落到 'other' 并在
# build-data.js 那侧报"大类没有登记短号"，宁可构建期发现。
TOP_ORDER = ['冒险', '职业', 'PvP', '专业技能', '地下城', '团队副本', '属性']
TOP_GID = {'冒险': 'adv', '职业': 'cls', 'PvP': 'pvp', '专业技能': 'prof',
           '地下城': 'dun', '团队副本': 'raid', '属性': 'stat'}


def gid_of(top):
    return TOP_GID.get(top, 'other')

# 客户端里有一批不是"玩家能拿的成就"的行：开发埋点、问卷、已废弃条目。判据两条一起才成立
#   ——名字里一个汉字都没有（客户端没给它中文名）+ 带这些开发标记词。
# 只中标记词但有中文名（比如真叫"隐藏"的成就）不算，只缺中文名但名字正常（"Conqueror of the Wilds"）
# 也不算，那种照原样列出来。界面上这些行进不了玩家视野，列出来反而是在骗人；
# 条数不删（成品仍是 211 条），只在界面与搜索里按 devOnly 排除，差额在 meta 里点名。
DEV_RE = re.compile(r'hidden|unused|tracking achievement|beta survey|\bbeta\b', re.I)
CJK_RE = re.compile(u'[\\u4e00-\\u9fff]')


def is_dev(name):
    s = str(name or '')
    return bool(s) and not CJK_RE.search(s) and bool(DEV_RE.search(s))

# 合法图标文件名（与 tools/fetch-icons.py 的 KEY_RE 同一条），带空格/斜杠的一律丢掉走自绘块
ICON_OK_RE = re.compile(r'^[a-z0-9_]{3,64}$')


def load(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return json.load(f)


def main():
    wb = load(os.path.join('upstream', 'wclbox-achievements.json'))
    gi = load(os.path.join('upstream', 'gi-achievements.json'))
    gi_old = load(os.path.join('upstream', 'gi-achievements-0.5.1.json'))
    w = {x['achId']: x for x in wb['achievements']}
    prov_w = {'type': 'datamine_cn', 'url': wb['meta']['source'], 'checkedAt': wb['meta']['fetched']}
    # 版本号从快照 meta 读，别写死（0.4.29 → 0.4.32 这类升级会把出处变成假话）
    def provenance(snapshot):
        return {'type': 'addon', 'url': snapshot['meta']['source'].split(' 的')[0],
                'checkedAt': snapshot['meta']['fetched']}
    prov_g = provenance(gi)
    prov_old = provenance(gi_old)
    cats_w = {c['id']: c['name'] for c in wb['meta'].get('categories') or []}

    rows, n = [], {'total': 0, 'l0': 0, 'l1': 0, 'nameDiff': 0, 'onlyWb': 0, 'noIcon': 0,
                   'devOnly': 0, 'badIcon': 0, 'fallbackOld': 0}
    current = {x['achId']: x for x in gi['achievements']}
    previous = {x['achId']: x for x in gi_old['achievements']}
    selected = [(g, gi) for g in gi['achievements']]
    selected += [(g, gi_old) for key, g in previous.items() if key not in current]
    n['fallbackOld'] = len(selected) - len(current)
    for g, source in sorted(selected, key=lambda pair: (pair[0].get('top') or '', pair[0]['achId'])):
        wrow = w.get(g['achId'])
        rec = {'id': 'ach-%d' % g['achId'], 'achId': g['achId'], 'name': g['name'],
               'nameEn': g.get('nameEn'), 'top': g.get('top'), 'gid': gid_of(g.get('top')),
               'cat': g.get('cat'),
               'iconKey': g.get('iconKey'), 'forever': bool(wrow.get('forever')) if wrow else None}
        prov = [provenance(source)]
        prior = previous.get(g['achId']) if source is gi else None
        if prior:
            prov.append(prov_old)
            if prior['name'] != g['name']:
                rec['nameHistory'] = [{'value': prior['name'], 'source': prov_old['url']}]
        if wrow:
            if wrow['name'] != g['name']:
                rec['nameAlt'] = wrow['name']
                rec['level'] = 'L1'
                n['nameDiff'] += 1
            else:
                rec['level'] = 'L0'
                n['l0'] += 1
            rec['category'] = wrow.get('category')
            rec['categoryCn'] = cats_w.get(wrow.get('category'))
            rec['criteriaCount'] = wrow.get('criteriaCount')
            if wrow.get('criteriaAchievements'):
                rec['subAchievements'] = wrow['criteriaAchievements']
            prov = [prov_w] + prov
        else:
            rec['level'] = 'L1'
            rec['categoryCn'] = rec['top']
            n['l1'] += 1
        if is_dev(rec['name']):
            rec['devOnly'] = True
            n['devOnly'] += 1
        # 图标键里混进过带空格的名字（客户端贴图叫 "achievement_zone_mount hyjal"）。
        # 空格不可能是文件名，界面拿它拼出来的 <img> 每次访问都稳定 404，两边栈的图数还会对不上。
        # 按红线不猜文件名（不去猜它是下划线还是连字符那一版），直接把这种键丢掉 → 自绘块。
        if rec.get('iconKey') and not ICON_OK_RE.match(rec['iconKey']):
            rec['iconKey'] = None
            n['badIcon'] += 1
        if not rec.get('iconKey'):
            n['noIcon'] += 1
        rec['provenance'] = prov
        rows.append(rec)
    for k in w:
        if k not in {x['achId'] for x, _ in selected}:
            n['onlyWb'] += 1

    by_top = {}
    by_top_shown = {}
    for r in rows:
        t = r.get('top') or '未分类'
        by_top[t] = by_top.get(t, 0) + 1
        if not r.get('devOnly'):
            by_top_shown[t] = by_top_shown.get(t, 0) + 1
    # 界面筛选器读这份 groups 建下拉，不在代码里写死大类名（写死必然与数据飘）；
    # count 是这一类的全部条目（与源侧自报对得上），shown 是页面上真列出来的条数
    # （扣掉开发埋点那几条），下拉里的数字用 shown，才和屏幕上看到的分组合计一致。
    order = [t for t in TOP_ORDER if t in by_top] + [t for t in sorted(by_top) if t not in TOP_ORDER]
    groups = [{'gid': gid_of(t), 'top': t, 'count': by_top[t],
               'shown': by_top_shown.get(t, 0)} for t in order]
    doc = {
        'meta': {
            'generatedAt': date.today().isoformat(), 'kind': 'achievements',
            'method': 'tools/merge-achievements.py 合新版 gi-achievements.json（%d 条）、旧版独有兜底（%d 条）'
                      '+ wclbox-achievements.json（能逐字回查的条目）。'
                      '两边 id 对上且中文名逐字相同才升 L0；成就描述整句两份都不落。'
                      '没有中文名且带开发标记的那 %d 条标 devOnly，条目照留，页面与搜索不列。'
                      % (len(current), n['fallbackOld'], n['devOnly']),
            'pageNote': '成就目录按无限测试版插件资料整理；能与另一处逐字对上的标为已核，'
                        '其余仍按单源留档。成就的具体完成条件文本一律不搬，要回游戏看。',
            'counts': {'total': len(rows), 'byTop': by_top, 'groups': groups,
                       'devOnly': n['devOnly'], 'shown': len(rows) - n['devOnly'],
                       'badIcon': n['badIcon'],
                       'l0': n['l0'], 'l1': n['l1'], 'nameDiff': n['nameDiff'],
                       'onlyInReference': n['onlyWb'], 'fallbackOld': n['fallbackOld'],
                       'noIcon': n['noIcon']},
            'sources': [{'key': 'gi', 'name': 'GearInsight 无限版 ' + (gi['meta'].get('addonVersion') or '版本未记'), 'kind': 'beta 客户端解包转述',
                         'date': gi['meta']['fetched']},
                        {'key': 'gi-old', 'name': 'GearInsight 无限版 ' + (gi_old['meta'].get('addonVersion') or '版本未记') + '（仅缺行兜底）',
                         'kind': '历史插件快照', 'date': gi_old['meta']['fetched']},
                        {'key': 'wclbox', 'name': '无限数据库 · 成就端点', 'kind': '当前 beta 客户端解包转述',
                         'url': prov_w['url'], 'build': wb['meta'].get('upstreamBuild'),
                         'date': prov_w['checkedAt']}],
        },
        'achievements': rows,
    }
    p = os.path.join(ROOT, 'achievements.json')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('成就：%d 条（L0 两源互证 %d · L1 单源 %d · 名字两说 %d · 缺图标 %d · 开发埋点 %d 条不上页面）'
          '·大类 %d 种' % (len(rows), n['l0'], n['l1'], n['nameDiff'], n['noIcon'], n['devOnly'],
                          len(by_top)))


if __name__ == '__main__':
    main()
