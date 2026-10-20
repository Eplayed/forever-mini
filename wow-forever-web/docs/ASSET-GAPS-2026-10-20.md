# 素材缺口审计 · 2026-10-20（wow-data + wow-dev）

脚本：`python3 tools/audit-assets.py`（加 `--fetch` 会把其它区域能取到的拉回本地；加 `--refresh` 忽略缓存、当天逐个重问官方 CDN）。图标一律只认暴雪官方 CDN，第三方站只给文件名。
本轮跑法：**忽略缓存、当天重测**；探测结果缓存 `.audit-cache/asset-probe.json`（缓存只记结果不记当天，所以这一栏必须写清）。

## 结论

| 项 | 数 |
| --- | --- |
| 数据里引用的图标键（全量成品 JSON + talents，含 iconKey 与 icon 两种字段） | 3454 |
| 本地已有 | 3294 |
| 缺 | 161 |
| 其中当天重新问过官方 CDN | 161 |
| 其中沿用探测缓存（不是当天重测） | 0 |
| 换区域/尺寸能补上 | 0 |
| 官方 CDN 五个候选路径都取不到（实测 403/404，不是我们没试） | 161 |
| 键名不合法（脚本不试，回数据里查） | 0 |
| art.json 指向但文件不存在 | 0 |
| 首领总数 / 挂上本地转存头像 | 228 / 146 |
| 头像转存了但数据里没引用（孤儿文件） | 0 |
| 副本与团本载入图缺口 | 2 座 |

## 首领头像缺口（按本）

| 副本 | 没脸的首领 |
| --- | --- |
| blackfathom-deeps | 瑟拉吉斯、暮光领主克尔里斯、阿库麦尔 |
| blackrock-depths | 秩序竞技场、霍尔雷·黑须、雷布里·斯库比格特、普拉格、黑铁七贤、达格兰·索瑞森大帝 |
| deathmine | 斯尼德的伐木机、矿工约翰森 |
| dire-maul-east | 普希林 |
| dire-maul-west | 赫尔努拉斯、苏斯 |
| gnomeregan | 黑铁大师、格鲁比斯 |
| hall-of-thanes | 法德林·安威玛尔、茵弗努斯、劫掠者、杜根·挽锤 |
| lower-blackrock-spire | 尖石屠夫、尖石统帅、尖石首席法师、班诺克·巨斧、霍克·巴什古德、水晶之牙、燃烧地狱卫士 |
| maraudon | 收割者麦什洛克 |
| razor-krendor | 腐烂的普雷莫尔、拉戈斯诺特 |
| razorfen-kraul | 盲眼猎手、唤地者哈穆加 |
| ruins-of-lordaeron | 枯牙、被遗弃者、屠夫、拉斯玛尔、洛丹伦上尉、邪恶的维克多、比约克 |
| scarlet-monastery-graveyard | 铁脊死灵、永醒的艾希尔、死灵勇士 |
| scholomance | 库尔莫克 |
| shadowfang-keep | 雷希戈尔、屠夫拉佐克劳、盲眼守卫奥杜、吞噬者芬鲁斯、狼王南杜斯、大法师阿鲁高、死亡之誓 |
| stratholme-main-gate | 狂热的玛洛尔、档案管理员加尔福特、红衣铸锤师、艾兹拉·格里姆、斯库尔 |
| stratholme-service-gate | 黑衣守卫铸剑师、石脊 |
| sunken-temple | 阿塔拉利恩、哈扎斯、摩弗拉斯、德拉维沃尔、可悲的奥戈姆 |
| the-stocks | 可怕的塔格尔、卡姆·深怒、哈姆霍克、迪克斯特·瓦德、巴吉尔·特雷德、布鲁高·铁拳 |
| upper-blackrock-spire | 索拉卡·火冠、古拉鲁克、瓦塔拉克公爵、杰德 |
| wailing-caverns | 变异精灵龙 |
| whelgars-excavation | 盐脊、暗齿、高地恐魔、遗迹守卫者 |
| zulfarrak | 布莱中士、暗影祭司塞瑟斯、泽雷利斯、杉达尔·沙掠者、灰尘怨灵 |

## 缺的图标按引用来源分布

| 图标键 | 引用处 | 判定 |
| --- | --- | --- |
| `8119728` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `ability_warlock_incubus` | changes.json、spells.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `achievement_zone_mount-hyjal` | legacy.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_10_alchemy2_quenchingfluid_color2` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_10_alchemy2_quenchingfluid_color3` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_10_alchemy2_quenchingfluid_color4` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_10_alchemy_bottle_shape4_violet` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_10_specialization_professionbook_alchemy_color2` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_ability_poison_missile` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_ability_poison_orb` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_axe_2h_raidhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_armor_skybornec60_d_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_cloth_skybornec60_b_01` | items.json、professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_leather_raiddruidhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_leather_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_leather_skybornec60_b_02` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_mail_skybornec60_b_01` | items.json、professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_armor_skybornec60_d_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_cloth_raidmagehyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_cloth_raidpriesthyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_cloth_raidwarlockhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_cloth_skybornec60_b_01` | items.json、professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_leather_raiddruidhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_leather_raidroguehyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_leather_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_leather_skybornec60_b_02` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_mail_raidhunterhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_mail_raidshamanhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_mail_skybornec60_b_01` | items.json、professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_plate_raidpaladinhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_plate_raidwarriorhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bow_1h_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bow_2h_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_cloth_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_leather_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_leather_skybornec60_b_02` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_mail_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_camelot_camping_welcomingcampfire` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_cape_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_cape_armor_skybornec60_d_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_cape_leather_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_cape_special_camping_d_01_green` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_catskybornemount_c60_blue` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest-_cloth_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_armor_skybornec60_a_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_armor_skybornec60_a_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_armor_skybornec60_d_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_leather_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_leather_skybornec60_b_02` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_mail_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_craneskyborne_c60_green` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_craneskybornemount_c60_blue` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_craneskybornemount_c60_gray` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_craneskybornemount_c60_white` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_craneskyborneswiftmount_c60_blue` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_craneskyborneswiftmount_c60_gray` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_craneskyborneswiftmount_c60_white` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_diablofunsized_c60_red` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_dragonhawk2_cyan` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_drink_31_embalmingfluid_color03` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_dwarfbearmount_c60` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_enchanting_modifiedcraftingreagent_indigo` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_first_aid_70_-jar` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_armor_skybornec60_d_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_cloth_raidmagehyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_cloth_raidpriesthyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_cloth_raidwarlockhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_cloth_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_leather_raiddruidhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_leather_raidroguehyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_leather_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_leather_skybornec60_b_02` | items.json、professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_mail_raidhunterhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_mail_raidshamanhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_mail_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_plate_raidpaladinhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_plate_raidwarriorhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_heart_of_the_thunder-king_icon` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_armor_buckledhat_b_01_blue` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_armor_buckledhat_b_01_brown` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_armor_skybornec60_d_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_cloth_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_leather_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_leather_skybornec60_b_02` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_mail_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_inscription_modified_craftingreagent07` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_jewelcrafting_cut-standart-gem-hybrid_color5_1` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_knife_1h_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_mace_1h_raidhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_mace_1h_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_mace_2h_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_magicalowlbearbaby_black` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_misc_food_93_skethylberries-` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_misc_food_meat_raw_01_color03` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_misc_kobysstools_knifetrap_color3` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_misc_spineleaf-_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_ore_ironclaw_corrupted` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pachimarapet` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pandacub_c60_black` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_armor_skybornec60_d_01` | items.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_cloth_raidmagehyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_cloth_raidpriesthyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_cloth_raidwarlockhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_cloth_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_leather_raiddruidhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_leather_raidroguehyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_leather_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_leather_skybornec60_b_02` | items.json、professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_mail_raidhunterhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_mail_raidshamanhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_mail_skybornec60_b_01` | items.json、professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_plate_raidpaladinhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_plate_raidwarriorhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_robe_armor_skybornec60_d_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shield_1h_raidhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shield_1h_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_armor_dwarfc60_d_02` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_armor_skybornec60_d_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_cloth_raidmagehyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_cloth_raidwarlockhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_cloth_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_l_mail_raidhunterhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_leather_raiddruidhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_leather_raidroguehyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_leather_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_leather_skybornec60_b_02` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_mail_raidshamanhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_mail_skybornec60_b_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_plate_raidpaladinhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_plate_raidwarriorhyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_r_cloth_raidpriesthyjalc60_d_01` | items.json、professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_skinning_sunlesscarapace2` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_staff_2h_skybornec60_b_01` | items.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_sword_1h_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_sword_2h_skybornec60_b_01_white` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_tabard_darkspearc60` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_tabard_legacyc60_b_01` | items.json、legacy.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_tabard_lordaeronc60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_tabard_merchantalliancec60` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_tabard_merchanthordec60` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_tabard_rivergladesc60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_tabard_theramorec60` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_ventureco_ring02_color4` | dungeons.json、items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_wand_1h_skybornec60_b_01` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_zerglingpet_c60` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `jewelcrafting_cut-standart-gem_color1` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `jewelcrafting_uncut-epic-gem_color1` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `spell_frost_ring-of-frost` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `trade_archaeology_bones-of-transformation` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `trade_archaeology_carved-wildhammer-gryphon-figurine` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `trade_archaeology_insect-in-amber` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `trade_archaeology_pendant-of-the-aqir` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `trade_archaeology_silverdoorknocker-of-female-dwarf` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `ui-hud-actionbar-keyring` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |

## 区域小地图（上游 /ditu-xiao 状态）

| mapId | 区域 | 上游 HTTP |
| --- | --- | --- |
| 1424 | 克雷普塞斯、塔尔玛·雷矛、塞菲莉斯、希尔斯布莱德丘陵、斯卡基尔、洛巴尔克、萨姆拉斯 | 404 |
| 1430 | 逆风小径 | 404 |
| 1440 | 乌索洛克、埃卡洛姆、恐狼族长、拉兹王子、橡爪、洛吉什、灰谷、玛戈芬、药剂师法尔瑟斯、薇丝比娅、迷雾嚎叫者、钳枝沼泽兽、阿克瑞鲁斯 | 404 |
| 1449 | 乌卡洛克、安戈洛环形山、暴掠龙女王、暴龙之王摩什、格鲁夫、萨瓦丝女王 | 404 |
| 1451 | 克里拉克、哈瑞坎尼安、希利苏斯、拉普雷斯、暮光之王艾沃兰、格雷瑟尔、格鲁布索尔、瑟提斯、苏尔拉、雷克斯·亚希尔 | 404 |
| 1453 | 下水道鳄鱼 | 404 |
| 1457 | 达纳苏斯 | 404 |
| 2548 | 河林 | 404 |
| 2652 | 辛德拉 | 404 |

## 副本载入图缺口

| 副本 | 名称 | 类型 | 两台源的状态 |
| --- | --- | --- | --- |
| `barrow-deeps` | The Barrow Deeps | raid | wowclassicforever 与无限数据库都是 404（这两座是还没开放的团本壳，客户端里本来就没有载入图）|
| `hyjal-summit` | Hyjal Summit | raid | wowclassicforever 与无限数据库都是 404（这两座是还没开放的团本壳，客户端里本来就没有载入图）|
