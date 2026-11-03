# 素材缺口审计 · 2026-11-03（wow-data + wow-dev）

脚本：`python3 tools/audit-assets.py`（加 `--fetch` 会把其它区域能取到的拉回本地；加 `--refresh` 忽略缓存、当天逐个重问官方 CDN）。图标一律只认暴雪官方 CDN，第三方站只给文件名。
本轮跑法：**沿用缓存里已有的探测结果，只补问新的**；探测结果缓存 `.audit-cache/asset-probe.json`（缓存只记结果不记当天，所以这一栏必须写清）。

## 结论

| 项 | 数 |
| --- | --- |
| 数据里引用的图标键（全量成品 JSON + talents，含 iconKey 与 icon 两种字段） | 3493 |
| 本地已有 | 3499 |
| 缺 | 3 |
| 其中当天重新问过官方 CDN | 0 |
| 其中沿用探测缓存（不是当天重测） | 3 |
| 换区域/尺寸能补上 | 0 |
| 官方 CDN 五个候选路径都取不到（实测 403/404，不是我们没试） | 3 |
| 键名不合法（脚本不试，回数据里查） | 0 |
| art.json 指向但文件不存在 | 229 |
| 首领总数 / 挂上本地转存头像 | 278 / 146 |
| 头像转存了但数据里没引用（孤儿文件） | 0 |
| 副本与团本载入图缺口 | 1 座 |

## 首领头像缺口（按本）

| 副本 | 没脸的首领 |
| --- | --- |
| blackfathom-deeps | 瑟拉吉斯、暮光领主克尔里斯、阿库麦尔、梦游者克尔里斯 |
| blackrock-depths | 秩序竞技场、霍尔雷·黑须、雷布里·斯库比格特、普拉格、黑铁七贤、达格兰·索瑞森大帝、竞技场：修行者高罗什、竞技场：格里兹尔、竞技场：腕眼者、竞技场：破坏者奥科索尔、竞技场：阿努希尔、竞技场：爬行者赫杜姆、黑暗宝箱、维雷克、卫兵杜格瑞普、黑铁酒吧、无敌的潘佐尔、七贤之箱 |
| city-of-dalaran | 墓穴骑士阿特雷克斯、被无视的琳恩、奥术畸体、奥术之谜、不稳定的哨兵、法力吞噬者、邪能古树、大法师之影 |
| deathmine | 斯尼德的伐木机、矿工约翰森 |
| dire-maul-east | 普希林 |
| dire-maul-west | 赫尔努拉斯、苏斯、辛德拉圣职者 |
| gnomeregan | 黑铁大师、格鲁比斯、科技机器人 |
| hall-of-thanes | 法德林·安威玛尔、茵弗努斯、劫掠者、杜根·挽锤、普兰德 |
| lower-blackrock-spire | 尖石屠夫、尖石统帅、尖石首席法师、班诺克·巨斧、霍克·巴什古德、水晶之牙、燃烧地狱卫士 |
| maraudon | 收割者麦什洛克、温格、玛拉多斯、无名先知、库尔克、盖尔克、玛格拉 |
| onyxias-lair | 奥妮克希亚 |
| razor-krendor | 腐烂的普雷莫尔、拉戈斯诺特、亨利·斯特恩 |
| razorfen-kraul | 盲眼猎手、唤地者哈穆加、剃刀沼泽刺鬃守卫 |
| ruins-of-lordaeron | 枯牙、被遗弃者、屠夫、洛丹伦上尉、邪恶的维克多、比约克、拉斯玛尔、男爵、邪恶的维克托 |
| scarlet-monastery-graveyard | 铁脊死灵、永醒的艾希尔、死灵勇士、瑟克恩 |
| scholomance | 库尔莫克、基尔图诺斯的卫士、传令官基尔图诺斯、死亡骑士达克雷尔 |
| shadowfang-keep | 雷希戈尔、屠夫拉佐克劳、盲眼守卫奥杜、吞噬者芬鲁斯、狼王南杜斯、大法师阿鲁高、死亡之誓、邪恶战马 / 暗影战马、阿鲁高的虚空行者、塞沃尔 |
| stratholme-main-gate | 狂热的玛洛尔、档案管理员加尔福特、红衣铸锤师、艾兹拉·格里姆、斯库尔、斯坦索姆信使、悲惨的提米 |
| stratholme-service-gate | 黑衣守卫铸剑师、石脊 |
| sunken-temple | 阿塔拉利恩、哈扎斯、摩弗拉斯、德拉维沃尔、可悲的奥戈姆、阳台的小头目、哈卡的后代 |
| the-stocks | 可怕的塔格尔、卡姆·深怒、哈姆霍克、迪克斯特·瓦德、巴吉尔·特雷德、布鲁高·铁拳、巴基尔·斯瑞德 |
| upper-blackrock-spire | 索拉卡·火冠、古拉鲁克、瓦塔拉克公爵、杰德 |
| wailing-caverns | 变异精灵龙 |
| whelgars-excavation | 盐脊、暗齿、高地恐魔、遗迹守卫者、高地惊魂、遗物守护者 |
| zulfarrak | 布莱中士、暗影祭司塞瑟斯、泽雷利斯、杉达尔·沙掠者、灰尘怨灵、沙怒刽子手 |

## 缺的图标按引用来源分布

| 图标键 | 引用处 | 判定 |
| --- | --- | --- |
| `8119728` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_12_tailoring_reagent_bag_violet_reagent_bag` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |
| `inv_inscription_modified_craftingreagent06` | items.json | 官方 CDN 五个候选路径（us/eu/kr/tw 的 56 尺寸 + us 的 0 尺寸）都取不到，实测回 403 = 无此文件 |

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

## art.json 里指向但文件不在的

- `classes/druid`
- `classes/hunter`
- `classes/mage`
- `classes/paladin`
- `classes/priest`
- `classes/rogue`
- `classes/shaman`
- `classes/warlock`
- `classes/warrior`
- `dungeons/hall-of-thanes`
- `dungeons/ruins-of-lordaeron`
- `dungeons/whelgars-excavation`
- `dungeons/city-of-dalaran`
- `dungeons/onyxias-lair`
- `dungeons/the-drowned-city`
- `dungeons/kroldok-stronghold`
- `dungeons/alcaz-prison`
- `dungeons/blackmaw-hold`
- `dungeons/shapers-terrace`
- `dungeons/ragefire-chasm`
- `dungeons/wailing-caverns`
- `dungeons/deathmine`
- `dungeons/shadowfang-keep`
- `dungeons/blackfathom-deeps`
- `dungeons/the-stocks`
- `dungeons/gnomeregan`
- `dungeons/razorfen-kraul`
- `dungeons/scarlet-monastery-graveyard`
- `dungeons/scarlet-monastery-library`
- `dungeons/scarlet-monastery-armory`
- `dungeons/razor-krendor`
- `dungeons/scarlet-monastery-cathedral`
- `dungeons/uldaman`
- `dungeons/zulfarrak`
- `dungeons/maraudon`
- `dungeons/sunken-temple`
- `dungeons/blackrock-depths`
- `dungeons/dire-maul-east`
- `dungeons/lower-blackrock-spire`
- `dungeons/dire-maul-north`
- `dungeons/dire-maul-west`
- `dungeons/scholomance`
- `dungeons/stratholme-main-gate`
- `dungeons/stratholme-service-gate`
- `dungeons/upper-blackrock-spire`
- `dungeons/hyjal-summit`
- `maps/1411`
- `maps/1412`
- `maps/1413`
- `maps/1416`
- `maps/1417`
- `maps/1418`
- `maps/1419`
- `maps/1420`
- `maps/1421`
- `maps/1423`
- `maps/1425`
- `maps/1426`
- `maps/1427`
- `maps/1428`
- `maps/1429`
- `maps/1432`
- `maps/1434`
- `maps/1435`
- `maps/1436`
- `maps/1437`
- `maps/1438`
- `maps/1439`
- `maps/1441`
- `maps/1442`
- `maps/1443`
- `maps/1444`
- `maps/1445`
- `maps/1446`
- `maps/1447`
- `maps/1455`
- `maps/2482`
- `maps/2521`
- `maps/1422`
- `maps/1431`
- `maps/1433`
- `maps/1448`
- `maps/1452`
- `bosses/oggleflint`
- `bosses/taragaman-the-hungerer`
- `bosses/jergosh-the-invoker`
- `bosses/bazzalan`
- `bosses/lady-anacondra`
- `bosses/lord-cobrahn`
- `bosses/kresh`
- `bosses/lord-pythas`
- `bosses/skum`
- `bosses/lord-serpentis`
- `bosses/verdan-the-everliving`
- `bosses/mutanus-the-devourer`
- `bosses/rhahk-zor`
- `bosses/sneed`
- `bosses/gilnid`
- `bosses/captain-greenskin`
- `bosses/mr-smite`
- `bosses/cookie`
- `bosses/edwin-vancleef`
- `bosses/baron-silverlaine`
- `bosses/commander-springvale`
- `bosses/ghamoo-ra`
- `bosses/lady-sarevess`
- `bosses/geilhast`
- `bosses/lorgus-jett`
- `bosses/baron-aquanis`
- `bosses/viscous-fallout`
- `bosses/electrocutioner-6000`
- `bosses/crowd-pummeler-9-60`
- `bosses/mekgineer-thermaplugg`
- `bosses/roogug`
- `bosses/aggem-thorncurse`
- `bosses/death-speaker-jargba`
- `bosses/overlord-ramtusk`
- `bosses/agathelos-the-raging`
- `bosses/charlga-razorflank`
- `bosses/interrogator-vishas`
- `bosses/bloodmage-thalnos`
- `bosses/houndmaster-loksey`
- `bosses/arcanist-doan`
- `bosses/herod`
- `bosses/tuten-kash`
- `bosses/mordresh-fire-eye`
- `bosses/glutton`
- `bosses/amnennar-the-coldbringer`
- `bosses/high-inquisitor-fairbanks`
- `bosses/scarlet-commander-mograine`
- `bosses/high-inquisitor-whitemane`
- `bosses/revelosh`
- `bosses/baelog`
- `bosses/olaf`
- `bosses/eric-the-swift`
- `bosses/ironaya`
- `bosses/obsidian-sentinel`
- `bosses/ancient-stone-keeper`
- `bosses/galgann-firehammer`
- `bosses/grimlok`
- `bosses/archaedas`
- `bosses/hydromancer-velratha`
- `bosses/gahz-rilla`
- `bosses/antu-sul`
- `bosses/theka-the-martyr`
- `bosses/witch-doctor-zum-rah`
- `bosses/nekrum-gutchewer`
- `bosses/chief-ukorz-sandscalp`
- `bosses/noxxion`
- `bosses/razorlash`
- `bosses/tinkerer-gizlock`
- `bosses/lord-vyletongue`
- `bosses/celebras-the-cursed`
- `bosses/landslide`
- `bosses/rotgrip`
- `bosses/princess-theradras`
- `bosses/avatar-of-hakkar`
- `bosses/shade-of-eranikus`
- `bosses/dreamscythe`
- `bosses/jammal-an-the-prophet`
- `bosses/high-interrogator-gerstahn`
- `bosses/lord-roccor`
- `bosses/houndmaster-grebmar`
- `bosses/pyromancer-loregrain`
- `bosses/lord-incendius`
- `bosses/warder-stilgiss`
- `bosses/fineous-darkvire`
- `bosses/bael-gar`
- `bosses/general-angerforge`
- `bosses/golem-lord-argelmach`
- `bosses/phalanx`
- `bosses/ambassador-flamelash`
- `bosses/magmus`
- `bosses/princess-moira-bronzebeard`
- `bosses/zevrim-thornhoof`
- `bosses/hydrospawn`
- `bosses/lethtendris`
- `bosses/alzzin-the-wildshaper`
- `bosses/highlord-omokk`
- `bosses/shadow-hunter-vosh-gajin`
- `bosses/war-master-voone`
- `bosses/mother-smolderweb`
- `bosses/urok-doomhowl`
- `bosses/quartermaster-zigris`
- `bosses/halycon`
- `bosses/gizrul-the-slavener`
- `bosses/overlord-wyrmthalak`
- `bosses/guard-mol-dar`
- `bosses/stomper-kreeg`
- `bosses/guard-fengus`
- `bosses/guard-slip-kik`
- `bosses/captain-kromcrush`
- `bosses/cho-rush-the-observer`
- `bosses/king-gordok`
- `bosses/tendris-warpwood`
- `bosses/illyanna-ravenoak`
- `bosses/magister-kalendris`
- `bosses/immol-thar`
- `bosses/prince-tortheldrin`
- `bosses/kirtonos`
- `bosses/jandice-barov`
- `bosses/rattlegore`
- `bosses/marduk-blackpool`
- `bosses/vectus`
- `bosses/ras-frostwhisperer`
- `bosses/instructor-malicia`
- `bosses/doctor-theolen-krastinov`
- `bosses/lorekeeper-polkelt`
- `bosses/the-ravenian`
- `bosses/lord-alexei-barov`
- `bosses/lady-illucia-barov`
- `bosses/darkmaster-gandling`
- `bosses/hearthsinger-forresten`
- `bosses/timmy-the-cruel`
- `bosses/cannon-master-willey`
- `bosses/balnazzar`
- `bosses/the-unforgiven`
- `bosses/postmaster-malown`
- `bosses/baroness-anastari`
- `bosses/nerub-enkan`
- `bosses/maleki-the-pallid`
- `bosses/magistrate-barthilas`
- `bosses/ramstein-the-gorger`
- `bosses/baron-rivendare`
- `bosses/pyroguard-emberseer`
- `bosses/warchief-rend-blackhand`
- `bosses/gyth`
- `bosses/the-beast`
- `bosses/general-drakkisath`
