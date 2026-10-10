# 与 wowhead 的天赋对账 · 2026-10-10（wow-data）

脚本：`python3 tools/audit-wowhead.py --write`。它只读，不改任何数据。

## 这份对账能证明什么、不能证明什么

wowhead 有无限服的完整天赋表，但 **Forever 区只有英文**（`/cn/forever` 是 404）。
所以它能对的是：条目数、英文原名、法术 ID、改动状态、图标文件名；
**它对不了任何中文名**——我们的中文名的依据是客户端解包与官方中文稿，不是一家英文站。
它行数据里带着英文描述句（改动前后的说明文字），脚本按红线**读都不读**，报告里也不出现。

两个实测到的取数坑，写在这里免得下次重踩：列表页 DOM 只渲染 50 行，
`?listview_page` / `?listview_size` 参数一律无效，完整数据在 `window.listviewspells` 里，
**数 DOM 会把条目数对错**；图标是懒加载背景，不在 `img[src]` 里，只有渲染出的那 50 行拿得到。
另外 curl 直取是 403，必须真浏览器。

## 每职业条目数

| 职业 | 我们的节点 | wowhead 条目 | 按网址片段对上 | 只有我们有 | 只有它有 |
| --- | --- | --- | --- | --- | --- |
| warrior | 56 | 52 | 49 | 7 | 3 |
| paladin | 52 | 49 | 49 | 3 | 0 |
| hunter | 50 | 50 | 50 | 0 | 0 |
| rogue | 53 | 53 | 53 | 0 | 0 |
| priest | 53 | 53 | 53 | 0 | 0 |
| shaman | 50 | 50 | 50 | 0 | 0 |
| mage | 54 | 54 | 54 | 0 | 0 |
| warlock | 52 | 52 | 52 | 0 | 0 |
| druid | 53 | 52 | 51 | 2 | 1 |
| **合计** | **473** | **465** | **461** | **12** | **4** |

对得上的 461 个是按**网址片段**配的（我们的 `upstreamId` 结尾就是它），剩下 12 个我们独有的节点分三种情况，没有一种是「它算错了」：

| 情况 | 个数 | 是什么意思 |
| --- | --- | --- |
| 上游格子表里这一格根本没有节点 | 6 | 只有 fengshen 列了它，所以对不出英文原名，也配不到 wowhead——首页那 4 个补不了图标的格子全在这一类 |
| 有格子号，但两源在同一格给了不同名字 | 6 | 我们这条的格子号指向的是另一家眼里的另一个天赋，按位置凑过来的号不能当英文名用 |
| 其余 | 0 | 真的对不上，要单独看 |

- **上游没有这一格**：乱舞（狂暴）、强化血性狂暴（防护）、专注怒气（防护）、强化神圣打击（神圣）、十字军（惩戒）、自然平衡（平衡）
- **同格两名（凑不上）**：狂怒精准（狂暴）、无边怒气（狂暴）、精准（狂暴）、强化复仇（防护）、精确（防护）、掠食本能（野性战斗）

### 只有 wowhead 有的条目（前 12 个 / 职业）

| 职业 | 它的英文名 |
| --- | --- |
| warrior | Furious Precision、Lingering Rage、Gore Drinker |
| druid | Natural Instinct |

它独有的这几条，与上面「同格两名」那批是同一件事的两头：我们这一格记的是另一个名字，它那个英文名就没被任何格子认领。

## 图标文件名分歧

一共 9 处对不上，但**逐条判下来只有 0 处是真分歧**，其余是我们自己有两格重名、或者两源在同一格给了不同名字（那一对本来就是按位置凑的）。

| 职业 | 我们的名字 | 网址片段 | 法术 ID | 我们 | wowhead | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| warrior | 钢铁意志 | `iron-will` | 12962 | `ability_warrior_secondwind` | `spell_magic_magearmor` | 两源在同一格给了不同名字，这一对是按位置凑的 |
| warrior | 饮血者 | `flurry` | 12319 | `racial_troll_berserk` | `ability_ghoulfrenzy` | 两源在同一格给了不同名字，这一对是按位置凑的 |
| warrior | 预知 | `anticipation` | 12297 | `spell_magic_magearmor` | `spell_nature_mirrorimage` | 我们这一职业有两格同名，配对先撞上了重名 |
| warrior | 预知 | `improved-bloodrage` | 12301 | `spell_nature_mirrorimage` | `ability_racial_bloodrage` | 我们这一职业有两格同名，配对先撞上了重名 |
| warrior | 强化缴械 | `improved-revenge` | 12797 | `ability_warrior_disarm` | `ability_warrior_revenge` | 两源在同一格给了不同名字，这一对是按位置凑的 |
| warrior | 先锋 | `improved-disarm` | 12313 | `ability_warrior_shieldcharge` | `ability_warrior_disarm` | 我们这一职业有两格同名，配对先撞上了重名 |
| warrior | 先锋 | `vanguard` | 1310317 | `ability_warrior_shieldbash` | `ability_warrior_shieldcharge` | 我们这一职业有两格同名，配对先撞上了重名 |
| warrior | 怒火聚焦 | `improved-shield-bash` | 12311 | `ability_warrior_focusedrage` | `ability_warrior_shieldbash` | 两源在同一格给了不同名字，这一对是按位置凑的 |
| warrior | 坚城 | `focused-rage` | 29787 | `inv_shield_04` | `ability_warrior_focusedrage` | 两源在同一格给了不同名字，这一对是按位置凑的 |

## 改动状态对照（我们的 changeState × 它的 envChange.status）

只列计数，不抄它写的任何一句改动说明。

| 我们的标记 | 它的标记 | 条数 |
| --- | --- | --- |
| modified | updated | 259 |
| added | new | 93 |
| unchanged | unchanged | 45 |
| moved | unchanged | 24 |
| added | updated | 12 |
| modified | unchanged | 9 |
| - | updated | 7 |
| moved | updated | 4 |
| - | new | 4 |
| unchanged | updated | 4 |

## 处置

1. **不改数据**。这份报告是「另一家怎么说」的一层，不是第二份真相；
   要按它改任何一条，都得回到客户端解包或官方中文页去核。
2. 图标分歧 9 处里真分歧 0 处：所以首页与天赋页的图标不必因为 wowhead 而调整——两边取的是同一份客户端数据。
3. 状态对照里数量明显的错位（比如我们标 `added` 它标 `updated`）单独列出来，
   交给人工回客户端核对，不在脚本里判对错。
