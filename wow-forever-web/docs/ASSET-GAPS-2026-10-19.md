# 素材缺口审计 · 2026-10-19（wow-data + wow-dev）

脚本：`python3 tools/audit-assets.py`（加 `--fetch` 会把其它区域能取到的拉回本地）。图标一律只认暴雪官方 CDN，第三方站只给文件名。

## 结论

| 项 | 数 |
| --- | --- |
| 数据里引用的图标键 | 2090 |
| 本地已有 | 3291 |
| 缺 | 82 |
| 换区域/尺寸能补上 | 1 |
| 官方 CDN 五个候选路径都取不到（实测 403/404，不是我们没试） | 81 |
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
| `ability_warlock_incubus` | changes.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_10_alchemy2_quenchingfluid_color2` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_10_alchemy2_quenchingfluid_color3` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_10_alchemy2_quenchingfluid_color4` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_axe_2h_raidhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_cloth_skybornec60_b_01` | professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_leather_raiddruidhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_leather_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_leather_skybornec60_b_02` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_belt_mail_skybornec60_b_01` | professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_cloth_raidmagehyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_cloth_raidpriesthyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_cloth_raidwarlockhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_cloth_skybornec60_b_01` | professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_leather_raiddruidhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_leather_raidroguehyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_leather_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_leather_skybornec60_b_02` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_mail_raidhunterhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_mail_raidshamanhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_mail_skybornec60_b_01` | professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_plate_raidpaladinhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_boot_plate_raidwarriorhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_cloth_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_leather_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_leather_skybornec60_b_02` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_bracer_mail_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_camelot_camping_welcomingcampfire` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_leather_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_leather_skybornec60_b_02` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_chest_mail_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_enchanting_modifiedcraftingreagent_indigo` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_cloth_raidmagehyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_cloth_raidpriesthyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_cloth_raidwarlockhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_cloth_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_leather_raiddruidhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_leather_raidroguehyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_leather_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_leather_skybornec60_b_02` | professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_mail_raidhunterhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_mail_raidshamanhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_mail_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_plate_raidpaladinhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_glove_plate_raidwarriorhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_armor_buckledhat_b_01_blue` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_cloth_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_leather_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_leather_skybornec60_b_02` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_helm_mail_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_mace_1h_raidhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_armor_skybornec60_d_01` | world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_cloth_raidmagehyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_cloth_raidpriesthyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_cloth_raidwarlockhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_cloth_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_leather_raiddruidhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_leather_raidroguehyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_leather_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_leather_skybornec60_b_02` | professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_mail_raidhunterhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_mail_raidshamanhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_mail_skybornec60_b_01` | professions.json、world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_plate_raidpaladinhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_pant_plate_raidwarriorhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shield_1h_raidhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_cloth_raidmagehyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_cloth_raidwarlockhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_cloth_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_l_mail_raidhunterhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_leather_raiddruidhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_leather_raidroguehyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_leather_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_leather_skybornec60_b_02` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_mail_raidshamanhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_mail_skybornec60_b_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_plate_raidpaladinhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_plate_raidwarriorhyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_shoulder_r_cloth_raidpriesthyjalc60_d_01` | professions.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_staff_2h_skybornec60_b_01` | world.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_ventureco_ring02_color4` | dungeons.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |

## 换区域能补上的

| 图标键 | 命中位置 | 引用处 | 结果 |
| --- | --- | --- | --- |
| `spell_warlock_demonsoul` | render/us/icons/56 | changes.json | 未取（只审计） |

## 区域小地图（上游 /ditu-xiao 状态）

| mapId | 区域 | 上游 HTTP |
| --- | --- | --- |
| 1424 | 希尔斯布莱德丘陵 | 404 |
| 1430 | 逆风小径 | 404 |
| 1440 | 灰谷 | 404 |
| 1449 | 安戈洛环形山 | 404 |
| 1451 | 希利苏斯 | 404 |
| 1457 | 达纳苏斯 | 404 |
| 2548 | 河林 | 404 |
| 2652 | 辛德拉 | 404 |

## 副本载入图缺口

| 副本 | 名称 | 类型 | 两台源的状态 |
| --- | --- | --- | --- |
| `barrow-deeps` | The Barrow Deeps | raid | wowclassicforever 与无限数据库都是 404（这两座是还没开放的团本壳，客户端里本来就没有载入图）|
| `hyjal-summit` | Hyjal Summit | raid | wowclassicforever 与无限数据库都是 404（这两座是还没开放的团本壳，客户端里本来就没有载入图）|
