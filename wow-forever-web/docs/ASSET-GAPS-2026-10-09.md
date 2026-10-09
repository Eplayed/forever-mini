# 素材缺口审计 · 2026-10-09（wow-data + wow-dev）

脚本：`python3 tools/audit-assets.py`（加 `--fetch` 会把其它区域能取到的拉回本地）。图标一律只认暴雪官方 CDN，第三方站只给文件名。

## 结论

| 项 | 数 |
| --- | --- |
| 数据里引用的图标键 | 2051 |
| 本地已有 | 1970 |
| 缺 | 81 |
| 换区域/尺寸能补上 | 0 |
| 官方 CDN 五个候选路径都取不到（实测 403/404，不是我们没试） | 81 |
| 键名不合法（脚本不试，回数据里查） | 0 |
| art.json 指向但文件不存在 | 0 |

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
