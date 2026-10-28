# 给 Windows 侧 AI 的提示词 · 按 OpenMap 那张表导 756 片逐层副本图

**用法**：把下面 `---8<---` 之间的整段复制给 Windows 那台机器上的 AI（Qoder/Codex 都行），不用附别的文件——
它要读的表就在它自己那台机器的插件目录里。
本站侧的对应任务书是 `wow-forever-web/docs/DATA-副本层图-Windows任务书-2026-10-28.md`，Mac 复核时按那份的契约对。

---8<--- 复制以下内容 ---8<---

# 任务：从本机《魔兽世界：无限》客户端按文件号导出 756 片副本逐层地图

## 你要做什么（一句话）

读你机器上 OpenMap 插件的那张"哪座本哪一层 = 哪 12 个贴图文件号"的表，
**按号从客户端 CASC 里把 756 片原图解出来转成 PNG**，再按每层 12 片拼成 63 张整层图，
连清单一起放进一个**新目录**。这批图用来修我们资料站"跨层首领点画在同一张图上"的错。

## 硬边界（先读这段，违反任何一条这单就算失败）

1. **只读客户端**。不修改、不新增、不删除游戏目录里的任何东西；不注入、不装会动游戏文件的工具。
   所有写入只发生在你自己建的导出目录里。
2. **不上传客户端本体、插件原包、`.mp`/CASC 归档**到任何地方。只回传解出来的 PNG 与清单文件。
3. **结果放进新目录**，不要覆盖以前任何一批（`ziliao-export/` 下已有 10-21 / 10-22 / models-2026-10-26 / round6 / round7 等）。
4. **拿不到的号照实登记 `NOTFOUND`**。不许用邻近号凑、不许留空当成功、不许"看着差不多"就跳过。
5. **不许自己编文件名或层名**。表里怎么写就怎么记。

## 第一步：读表（表就在你机器上）

路径（`_cn_beta_` 是 Mac 侧共享里看到的那个目录名，以你机器实际的客户端根为准；
如果这台机器装的是 `_forever_` 之类的别的目录名，就找 `Interface/AddOns/OpenMap/Data/DungeonMaps.lua`）：

```
<客户端根>\_cn_beta_\Interface\AddOns\OpenMap\Data\DungeonMaps.lua
```

顺手记一下版本，写进清单：同目录上一层的 `OpenMap.toc` 里的版本号。
**我们这边实测那行是 `## Version: v0.7.5-beta`**（我们登记名写作 "0.7.5-CN" 指的是网易DD 分发的汉化分支；
同目录的 `addon_version.txt` 是 CurseForge 文件号 `668062`、`dd_author.toc` 是分发哈希，**这两个都不是版本号，别抄进清单**）。
**只读这一个文件，不要读、不要拷 OpenMap 的 `Media/` 任何图片**——那些是它从暴雪地图美术裁出来的件，
它自己的 `NOTICE.md` 写明不受 MIT 覆盖，我们不要。

表的结构（文件头注释原话：`4 x 3 tiles of 256 px, the picture ~1002 x 668 of its 1024 x 768`）：

```lua
[33] = { -- Shadowfang Keep
    { tiles = { 448226, 448230, 448231, ..., 448237, 448227, 448228, 448229 }, name = "The Courtyard" },
    ...
}
```

- 外层 key = **instanceMapId**（33 = 影牙城堡），数组里每一项 = **一层**（顺序就是第 1 层、第 2 层…）
- 本名在**那一行后面的注释里**（`[33] = { -- Shadowfang Keep`）；注释没有就留空，**不许自己翻译或补中文名**
- `tiles` = 这一层的 12 个 **FileDataID**
- `name` = 层名（可能没有；另有 `wing` 分区名的条目也要照记）

### 一个必须避开的坑：数组顺序 ≠ 数字顺序

**`tiles` 数组的下标就是拼图位置，绝对不许按数字排序。** 上面影牙城堡那行为例：
第 1 位是 448226，第 2–9 位是 448230…448237，**第 10–12 位才是 448227/448228/448229**。
排完序会把左下角三片挪到上面去，拼出来的整层图是错的，而我们肉眼很难发现。
（正确顺序：下标 1–4 = 上排从左到右，5–8 = 中排，9–12 = 下排。）

## 第二步：逐号导出（命令是现成的，2026-10-22 那单就跑通过）

```
wowfexport get "<客户端根>" wowf id <fdid> <输出目录> <文件名> <日志文件>
```

- 一条号一条命令，**全部 756 条都要留日志**（不要只留失败的）。
- 解出来是 `.blp`，转成 **PNG**，**保持原尺寸 256×256**。
- **不许裁掉空白边、不许缩放、不许加文字或水印、不许改色彩配置**。留白是几何的一部分，
  我们的坐标要落在这张图上，裁了就对不上。
- 这批号在客户端 listfile 里登记的字节数**全是 44,876**（我们已逐号回读过，756/756 命中且 `name_kind=verified`）。
  解出来的 `.blp` 字节数不是这个数，就在清单里记 `bytesMismatch` 并写实际值——**但图照留**。

## 第三步：拼整层图

每层 12 片按 `tiles` 下标 **4 列 × 3 行** 拼成 **1024×768** 的一张 PNG。
拼出来的图**不要自己再处理**（不裁、不缩、不加边框）。

## 第四步：交付形状

放到 `ziliao-export/maps-floor-<YYYY-MM-DD>/`：

```
maps-floor-2026-10-28/
  tiles/<fdid>.png                     756 张
  floors/<instanceMapId>_<floor>.png    63 张（floor 从 1 起）
  tiles.csv                             见下
  RESULT.json                           见下
  logs/wowfexport.log                   完整原始日志，别截断
  MANIFEST.json                         包内每个文件的 sha256 + 字节（**最后生成，不要把自己算进去**）
  PACKAGE.json                          包级：生成时间、客户端根、build 号、总数、本包 sha256
```

`tiles.csv` 一行一片，列固定为：

```
instanceMapId,instanceEn,floor,floorEn,wingEn,tile,fdid,clientPath,srcBytes,status
```

（`clientPath` = 导出时客户端返回/登记的实际路径；拿不到就写空并在 `status` 写 `NOTFOUND`。）

`RESULT.json` 至少要有：

```json
{
  "generatedAt": "…",
  "clientRoot": "你实际用的那个绝对路径",
  "build": "读 .build.info 得到的 Product + build 号",
  "openmapVersion": "OpenMap.toc 里读到的版本号",
  "requested": 756, "exported": 0, "notfound": 0, "bytesMismatch": 0,
  "instances": 0, "floors": 0,
  "files": [
    {"file": "tiles/448226.png", "fdid": "448226", "clientPath": "Interface/…",
     "srcBytes": 44876, "pngSha256": "…", "status": "ok"}
  ],
  "floorsOut": [
    {"instanceMapId": "33", "floor": 1, "floorEn": "The Courtyard",
     "tiles": ["448226","448230","…按数组原顺序…"], "out": "floors/33_1.png", "status": "ok"}
  ],
  "notes": ["任何异常、跳号、工具版本、你改过什么都写这里"]
}
```

## 第五步：交之前自己先跑这几条自检（数不对就别交，先修）

1. 表里数出来应当是 **25 座本 / 63 层 / 756 片**，且**每层正好 12 片**。
   对不上就把你实际数到的写进 `RESULT.notes` 并**停下来问**，不要自己删条目凑数。
2. `tiles/` 里的 PNG 张数 = `RESULT.exported`，且 **`exported + notfound = 756`**；`floors/` 里 63 张。
3. 每张 PNG 尺寸必须是 **256×256**，每张整层图必须是 **1024×768**。
4. 抽 3 层（建议 33 座里取第 1、第 4、最后一层）打开看一眼，确认拼出来的房间形状连贯、
   没有哪一片转了 90° 或放错格。**这条是防上面那个排序坑的最后一道**。
5. `MANIFEST.json` 是最后生成的，里面不含 `MANIFEST.json` 自己。

## 顺手一件小事（和上面无关，可以晚做，只要 2 个文件）

从 `<客户端根>\_cn_beta_\Interface\AddOns\OpenMap\Media\Textures\MapZones\` 任选 2 片
（建议 `10_10.blp` 和 `10_11.blp`）解成 PNG，放进 `maps-floor-<日期>/probe-blp/`。

**只看一件事：那上面有没有烘死的地名文字**（任何语言都算，包括韩文）。
这 2 片只用来判路，**不会进我们的素材库**——它们属于 OpenMap 从暴雪地图美术裁出来的那一层。
判完在 `RESULT.notes` 里写一句"有/没有，看到的语言是什么"。

## 我们收到后会做什么（先说清，免得来回返工）

逐条回读 `RESULT.files` 的 sha256 与字节、和 `tiles.csv` 的 `fdid`/`bytes` 对一遍；
数 756/63/25 三个数；抽 3 层人眼看图对不对得上那座本那一层。**任何一条对不上我会退回来重做**，
所以宁可 `NOTFOUND` 写满，也不要拿别的号填上。

---8<--- 复制到此结束 ---8<---

## Mac 侧这一边同时要做的事（不给 Windows，给自己记）

1. 收到包后按 `DATA-副本层图-Windows任务书-2026-10-28.md` 第五节那三步复核。
2. 第一件事就是看**层图里烘没烘地名**——它决定 `PLAN-把OpenMap那套展示搬到网页-2026-10-28.md` 里的 S2（中文标注层）能不能做。
3. 图过了才动 `dungeon-geo.json` 与 `DungeonPage.vue`（#108：一层一张、只画那一层的点）。
