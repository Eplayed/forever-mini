# 人口普查与素材补齐 · 2026-11-19

## 人口普查

| 样本 | 核对方式及时间（北京时间） | 阵营 | 职业 |
| --- | --- | --- | --- |
| Everloot 近七天社区观测 | 11 月 19 日 13:40，20,430 个角色，21 个上报安装。公开 API 用 Python urllib 访问时返回 403，系统 curl 请求返回 200，有完整九职业汇总及 CC BY-SA 4.0 许可。 | 联盟 39.8%，部落 60.2% | 九职业保留来源计数与占比 |
| 大脚国服无限服 | 微信大脚BIGFOOT「服务器人口 → 无限服 → 昨日人口」。11 月 19 日实读，按页面「数据截止 每日凌晨0点」记录为 11 月 19 日 00:00。 | 联盟 50%，部落 50% | 猎人 17.43%、圣骑士 15.63%、法师 13.35%、战士 10.42%、德鲁伊 9.82%、萨满祭司 9.03%、潜行者 8.78%、牧师 8.39%、术士 7.15% |

Everloot 公开数据范围包含未区分的地区与规则集。两份数据在小程序原有切换入口独立显示。国服沿用现有 24 小时样本结构，保留大脚页面上职业百分比的两位精度，兼容旧整数样本。大脚本次页面只展示比例，未添加人数或服务器明细。 [Everloot 普查](https://everloot.app/census) · [Everloot 方法及许可](https://everloot.app/methodology) · [大脚官网](https://bigfoot.nga.cn/)

后续可用 `python tools/refresh-census.py` 或 `bash tools/refresh.sh census` 更新 Everloot。脚本用既有 OSS 汇总校验检查数据，来源、许可、时间窗或比例校验失败时保留上一份样本。国服继续以微信可见汇总核对。

## 地图与图标

- WCLBox 旧图区缺图时，`fetch-art.py --what maps` 对已核对的 9 个地图 ID 回退到 GearInsight 已有的客户端地图。9 张均完整解码为 1002 × 668 WebP，以大陆和地图 ID 对应。取两边都有的艾尔文森林 `1429` 缩放对照，以原图无偏移时的 RGB 差最小。9 张素材逐个核对画面、清单字节和哈希，成品区域小地图增至 46 张。重建 `world.json` 和 `dungeon-geo.json` 后，世界地图数据缺图为 0，另有一座副本入口仍缺对应地图，属于本轮 9 张区域图之外。 [GearInsight 世界地图](https://gearinsight.app/wow/forever/map)
- 本机 Forever `1.60.1.70938` 的 CASC 记录按四个 FileDataID 取回物品原图，按现有 56 × 56 JPEG 规格入库。`app/img/icons/manifest.json` 保存每张图的 FileDataID、原件与成品 SHA-256。缺图数从 5 降到 1。

| 补齐或保留 | 物品 | 核对结果 |
| --- | --- | --- |
| 已补齐 | 273310 炼金区 - 邪能灰烬实验笔记 | 3717601 |
| 已补齐 | 286614 咕噜咕噜的强硬舌头 | 4639595 |
| 已补齐 | 287045 古代马托克 | 7816730 |
| 已补齐 | 289439 一袋紫色粉末 | 5931149 |
| 阻塞 | 281631 典藏版战袍 | WCLBox 页面引用 8119728。官方 CDN 请求返回 403。本机版本读这个 FileDataID 报 `unknown keyname 5699DB626E0CD467`，解出的可读 `Item.db2` 行也没有该物品 ID 可作替换证据。当前保留原有占位，缺图清单保留该键。 [WCLBox 物品记录](https://wowforever.wclbox.com/wupin/281631) |

## 构建与 MacBook 回读

- `node tools/build-data.js`、`node tools/export-mini.js`、`node tools/oss-release.js build --env beta` 均通过。小程序本机候选为 `903aa05aaa90`，首次重导出曾遇到 Windows 临时文件打开错误，重跑通过。未执行 OSS 上传、网页发布或小程序提审。
- MacBook 增量传输 22 个指定成品文件，由 `video2text/tools/sync_wow_icons.py` 重建图文索引。两份普查 JSON、9 张区域图、4 个图标在 `/Users/zhangyajun/Documents/project/video2text/output/_assets/` 的 SHA-256 全部与 Windows 文件一致。`wow_cards.json` 已实际引用四个物品图标和抽查的河林、灰谷、辛德拉地图。
- 数据范围内验证以成品、打包和 MacBook 索引回读为准。未执行微信真机渲染验证。
