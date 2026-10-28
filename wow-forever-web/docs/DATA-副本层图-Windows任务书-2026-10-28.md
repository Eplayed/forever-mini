# Windows 侧任务书 · 按 756 个文件号导逐层官方副本图（2026-10-28 站主拍板）

本轮角色：wow-data ｜任务：把 OpenMap 那张"哪座本哪一层 = 哪 12 个贴图文件号"的表落成可执行的导数单
｜产出：本文件 + `docs/DATA-openmap-副本层图-2026-10-28.csv` ｜交接给：站主转给 Windows 那台 → 回来由本站复核

**这份表为什么必须从别人手里拿**：无限服客户端里没有 `MapArea` / `MapDiff` / `TextureData` 三张表
（2026-10-22 逐张判死，`ziliao-export/maps/resolve.csv` 那 9 行 `ok=false` 就是那次留下的），
所以我们**推不出**"影牙城堡第 6 层是哪 12 个文件"。OpenMap 0.7.5-CN 有这张表，
它的层与分区名取自**正式服 5.5.4.70268 的 UiMap 表 + 12.1.5.70391 的日志**，数据表是 MIT。

**本站只取文件号与层名，不取 OpenMap 的任何一张图**（它 `Media/` 里的图是暴雪地图美术的裁剪件，
它自己的 `NOTICE.md` 写明不受 MIT 覆盖）。图由 Windows 侧从本机客户端只读导出，走 2026-10-21 那条已经跑通的路。
所以下面这一单**不需要读 AddOns 目录**，只需要那份 CSV + 客户端本体。

---

## 一、硬边界（和以前几单一样，先读这段）

1. **只读**：不改客户端、不注入、不装任何会动游戏文件的工具；导出过程只在导出目录里写。
2. 不把客户端本体、插件原包、`.mp`/CASC 归档上传到任何地方；只回传解出来的 PNG 与清单。
3. 结果放回共享里的**新目录**，不要覆盖以前任何一批（`ziliao-export/` 下已有 10-21 / 10-22 / models-2026-10-26 三批）。
4. 拿不到的号**照实登记 `NOTFOUND`**，不许用邻近号凑、不许留空当成功。

## 二、要导什么

输入：`DATA-openmap-副本层图-2026-10-28.csv`（**757 行 = 表头 + 756 片**，25 座本 / 63 层 / 每层 12 片）。
列的意思：

| 列 | 是什么 |
| --- | --- |
| `instanceMapId` | 副本的 instance mapID（33 = 影牙城堡、249 = 奥妮克希亚的巢穴…） |
| `instanceEn` / `floor` / `floorEn` / `wingEn` | 本名 / 第几层（1 起） / 层名（51 层有名，12 层空着） / 分区名（15 层有） |
| `tile` | 这一层 12 片里的第几片，**行优先**（1–4 是上排，9–12 是下排） |
| `fdid` | 要导的文件号（用现成的 `wowfexport get … id` 那一条命令） |
| `clientPath` | listfile 里登记的期望路径，导出来要能对上 |
| `bytes` | listfile 登记的字节数（这批全是 44,876，用来判"是不是拿错了文件"） |

这一批 756 个号在 listfile 里**全部 `name_kind=verified`**（本站已逐号回读，不是抽样），
所以正常情况应该 756/756 全成；只要出现一条 `NOTFOUND` 或字节不符，就是真信号，要写进 RESULT 里。

## 三、要交付的形状

放到 `ziliao-export/maps-floor-2026-10-28/`：

```
maps-floor-2026-10-28/
  tiles/<fdid>.png                 756 张，逐片解出来的原图（256×256，不缩放、不加字、不裁边）
  floors/<instanceMapId>_<floor>.png   63 张，每层 12 片按 tile 序号 4 列 × 3 行拼起来（1024×768）
  RESULT.json                      见下
```

`RESULT.json` 至少要有：

```json
{
  "generatedAt": "…",
  "clientRoot": "C:\\GAME\\World of Warcraft\\_forever_ 或实际用的那个",
  "build": "读 .build.info 得到的 Product + build 号",
  "requested": 756, "exported": 0, "notfound": 0, "bytesMismatch": 0,
  "files": [
    {"file": "tiles/448226.png", "fdid": "448226", "clientPath": "Interface/WorldMap/…",
     "srcBytes": 44876, "pngSha256": "…", "status": "ok"}
  ],
  "floors": [
    {"instanceMapId": "33", "floor": 1, "floorEn": "The Courtyard",
     "tiles": ["448226","448230","…"], "out": "floors/33_1.png", "status": "ok"}
  ]
}
```

三条要注意的：

- **BLP 解出来不要顺手裁掉空白边**。官方副本图 1024×768 里真正的画约 1002×668，
  留白是几何的一部分——我们的首领坐标要落在这张图上，裁了就对不上。
- **别加任何水印、文字、缩放**。我们要的是原图，排版是本站这一侧的事。
- `manifest.json`（自哈希那份）**最后生成**，别把自己算进去（10-26 那单已经为这个返过一次工）。

## 四、顺手只要 2 个文件的一小问（和上面无关，可以晚做）

我们要判"区域图能不能拿干净的一张、地名自己排"。请从共享里
`_cn_beta_/Interface/AddOns/OpenMap/Media/Textures/MapZones/` 任选 **2 片**
（建议 `10_10.blp` 和 `10_11.blp`）解成 PNG，放回 `ziliao-export/maps-floor-2026-10-28/probe-blp/`。

**只看一件事：那上面有没有烘死的地名文字**（任何语言都算）。这 2 片我们只用来判路，
**不会当成素材进仓库**——它们属于 OpenMap 从暴雪地图美术裁剪出来的那一层，许可写明了不在 MIT 里。

## 五、回来之后本站会做什么

1. 逐条回读 `RESULT.files` 的 sha256 与字节，和 CSV 的 `fdid`/`bytes` 对一遍（10-22 那单起就有的规矩）。
2. 抽 3 层人眼看：图是不是那座本那一层（用层名与房间形状对）。
3. 拼进 `app/img/art/dungeonmaps/` 旁边的新目录 + `manifest.json` 逐张登记来源与抓取日期，
   然后按 `docs/DATA-插件盘点-2026-10-28.md` 第六节改副本详情页：**一层一张图、只画那一层的点**
   （现在 30 座里有 7 座把跨层的点画在同一张图上，这条是站主 10-27 认下要修的）。
