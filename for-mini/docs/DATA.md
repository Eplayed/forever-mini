# 数据契约与分发流程（小程序侧）

来源：`wow-forever-web/src/data/`（站点基底）。小程序**不自己维护数据**，只消费导出与分片产物，保证与网页端同源。
分发层的完整设计与取舍在 `wow-forever-web/docs/OPS-oss-分发层-poe方案落地-2026-10-21.md`，本轮实测记录在 `docs/VERIFY-OSS-01-分发层-2026-10-21.md`。

## 一、路径与命名空间

bucket 沿用 PoE 那条线已备案的域名，前缀完全隔离，不共用文件、不共用缓存 key。

```
https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com/
  wow/{beta|release}/v1/manifest.json                      ← 唯一可变指针（max-age=60）
  wow/{env}/v1/builds/{buildId}/manifest.json               ← 批次自带清单（回滚位）
  wow/{env}/v1/builds/{buildId}/files.json                  ← 逐文件哈希（25.1 KB）
  wow/{env}/v1/builds/{buildId}/meta.json | glossary.json
  wow/{env}/v1/builds/{buildId}/dungeons/index.json
  wow/{env}/v1/builds/{buildId}/dungeons/detail/{id}.json
  wow/{env}/v1/builds/{buildId}/dungeons/loot/{id}.json
```

| 项 | 值 |
| --- | --- |
| 命名空间 | `wow/{env}/v1/`，`env` = `beta`（内测）/ `release`（线上） |
| `buildId` | 内容指纹前 12 位；同一份基底重跑不变，改一个字段就换一批 |
| 缓存 key | `wow_forever_v1_{用途}@{buildId}`（**批次号必须在 key 里**，否则旧批会冒充新批） |
| 指针缓存 key | `wow_forever_v1_pointer@{env}` |
| 收藏 key | `wow_fav_terms_v1`（本机行为数据，不上传） |
| 打包快照 | `data/forever-glossary-snapshot.js`、`data/forever-meta-snapshot.js`；副本索引快照待 M01 |

`wow/release/v1/` 目前**从没传过任何文件**（2026-10-21 匿名 GET 实测 404），所以线上小程序现在读到的都是打包快照。

## 二、两套取数口子（过渡期，别混用）

| 口子 | 谁在用 | 读什么 |
| --- | --- | --- |
| `services/forever-data.js` | 已有首页 + 中英速查（旧平铺地址 `{env}/v1/{file}.json`） | 只有 `meta` / `glossary`，`live/cache/snapshot` 三态 |
| `services/oss-manifest.js` | 新页面一律用它 | 指针 → 索引 → 详情/掉落，四态 `live/cache/snapshot/none` |

M01 把页面接到 `oss-manifest.js` 之后，`forever-data.js` 里那套平铺地址就该收掉，只留收藏与译名文案函数。

## 三、批次里每份文件长什么样

指针 `manifest.json`（5,055 B，冷启动必取；示例取自 2026-10-21 R1 后的批次 `e38e5ae790d4`，
里面的数会变，别抄成常量）：

```jsonc
{
  "schemaVersion": 1, "product": "wow-forever-mini", "env": "beta",
  "namespace": "wow/beta/v1", "buildId": "e38e5ae790d4",
  // 没有 builtAt：同一 buildId 的清单必须逐字节恒定，否则"不可变批次"每次重建都会被自己的时间戳改写。
  // 发布时刻看对象的服务端 Last-Modified 与本地 oss-build/{env}/last-upload.json。
  "timeNote": "…", "minClientSchemaVersion": 1,
  "source": { "commit": "bedaa241", "inputs": [{ "rel": "src/data/dungeons.json", "bytes": 334535, "sha256": "…" }],
              "exportCheck": { "tool": "wow-forever-web/tools/export-mini.js", "reproduced": true,
                               "outputs": [{ "rel": "oss-preview/meta.json", "bytes": 1724, "sha256": "…" }] } },
  "counts": { "dungeons": 38, "terms": 215, "files": 81, "bytes": 464300 },
  "factDates": { "min": "2026-10-07", "latest": "2026-10-11",
                 "dungeonDetail": { "min": "2026-10-07", "max": "2026-10-11", "distinct": 4, "recordsWithoutDate": 1 } },
  "droppedFields": [{ "field": "art", "reason": "…" }, { "field": "bosses[].portrait", "reason": "…" }],
  "assetNote": "iconKey 只是图标键，图标文件没传 OSS",
  "integrity": { "method": "etag", "clientChecks": ["…五项校验的完整口径见下…"],
                 "whatItIsNot": "是传输/存储完整性校验，不是抗伪造的内容签名" },
  "pointer": { "key": "wow/beta/v1/manifest.json", "cacheControl": "public, max-age=60, must-revalidate" },
  "fetch": { "meta": { "path": "builds/…/meta.json", "sha256": "…", "etag": "17952BBC…", "bytes": 1829, "records": 1 },
             "glossary": { "…": "84,208 B / 215 条" }, "dungeonIndex": { "…": "25,809 B / 38 条" } },
  "bundle": { "path": "builds/e38e5ae790d4/files.json", "sha256": "0397629b…", "etag": "EAD6C901…", "bytes": 29516 }
}
```

副本索引 `dungeons/index.json`（25.2 KB / 38 条，列表页只要这一份）：

```jsonc
{ "schemaVersion": 1, "product": "wow-forever-mini", "buildId": "…", "kind": "dungeon-index",
  "counts": { "total": 38, "newDungeons": 9, "classicDungeons": 26, "raids": 3 },
  "lootDisclaimer": "…", "notCollected": { "route": 38 },
  "items": [{ "id": "hall-of-thanes", "kind": "new", "nameCn": "领主大厅", "nameEn": "Hall of Thanes",
              "nameCnConflict": "诸王大厅", "levelRange": "13-20", "levelRangeOfficial": "13-18",
              "faction": "联盟", "zoneCn": "…", "partySize": 5, "level": "L0",
              "bossCount": 4, "dropCount": 1, "hasRoute": false,
              "detailPath": "dungeons/detail/hall-of-thanes.json", "lootPath": "dungeons/loot/hall-of-thanes.json",
              "detailEtag": "6F1CB781…", "detailBytes": 3413, "lootEtag": "A071A464…", "lootBytes": 674 }] }
```

详情 `dungeons/detail/{id}.json`（均值 2.6 KB，最大 4.2 KB）＝ `{ schemaVersion, product, kind: "dungeon-detail", buildId, source, dungeon }`，
`dungeon` 是该条完整记录（去掉 `drops`、`art`、`bosses[].portrait`，加 `dropCount` / `lootPath`），
`provenance[]` 原样带下来，界面上的"来源与核对日期"就取这里的 `checkedAt`。
掉落 `dungeons/loot/{id}.json`（均值 5.7 KB，最大 26.3 KB）＝ `{ …, kind: "dungeon-loot", dungeonId, level, lootNote, drops[] }`，
`drops` 里只有物品事实字段，**没有百分比**。
`meta.json` / `glossary.json` 现在也带 `schemaVersion / product / kind / buildId` 四个身份字段（业务字段一个没动）。

## 三·五、客户端实际做的是哪五项校验（R1 改的就是这一层）

以前指针里写着"客户端每个文件都按 sha256 校验"，而 `oss-manifest.js` 一次哈希都没算过——名实不符。
R1 起把"说了什么"与"做了什么"对齐，**每个文件五项齐验**，任一项不符整条判失败并降级：

| # | 校验 | 期望值来自哪 |
| --- | --- | --- |
| 1 | 响应头 `ETag` == 清单记的 `etag`（服务器自己算的内容 MD5） | 入口三文件：指针 `fetch.*`；详情/掉落：索引条目 `detailEtag`/`lootEtag` |
| 2 | 响应头 `Content-Length` == 清单记的 `bytes`（有头才比） | 同上 |
| 3 | 内容自带 `buildId` == 请求所在的批次 | 每个文件都带（含 meta / glossary） |
| 4 | 内容自带 `product` / `schemaVersion` / `kind` | 每个文件都带 |
| 5 | 内容里的 ID 就是请求的那一条（详情比 `dungeon.id`，掉落比 `dungeonId`） | 索引条目的 `id` |

外加一条路径规则：分片路径由条目 `id` 现推，再与 `detailPath` / `lootPath` 比对，对不上直接拒绝、连请求都不发——
写坏一条路径也走不出 `builds/{buildId}/`。

坦白讲清边界（这段就写在 `manifest.integrity` 里，界面与文档不许说得比它更满）：
ETag 是"取回的字节是不是清单里那一份"的传输/存储完整性校验，**不是抗伪造的内容签名**，也不证明上游写的事实是对的（事实靠 provenance 与红线卡口）。
逐文件 SHA-256 由构建端算、写进 `files.json`，发布后由 `oss-release.js verify --env …` 匿名逐个回读比对——
所以 `files.json` 不进冷启动路径，客户端不必为校验多下 28.8 KB。

**冷启动代价（R1 后实量）**：指针 5,055 B + 索引 25,809 B + meta 1,829 B = **32,693 B ≈ 31.9 KB / 3 次 GET**；
整份 `dungeons.json` 是 326.7 KB，省 90%（比 R1 前多 7.7 KB，就是随索引下发的 76 个校验值）。
之后每进一本详情才多取 2.6–4.2 KB，看掉落再取 5.7 KB；同批二次打开命中缓存是 0 次请求。

## 四、四态语义（R1 把"省流量"与"离线降级"分开了）

`oss-manifest.js` 每次返回都带同一组字段：`data / source / cacheHit / buildId / factDates / requiresUpdate / pointerSource / stale / batch / error`，
`source` 只表示**这批数据是不是线上当前批**，不表示字节从哪来：

| `source` | 含义 | 界面义务 |
| --- | --- | --- |
| `live` | 指针是现取的，数据属于指针说的这一批。`cacheHit:true` 表示字节用的本机同批缓存、没重新下载（**这不是离线**） | 正常显示，配 `factDates.latest` 当"核对到"；`cacheHit` 时 `sourceLabel()` 会说"实时数据（本机缓存…）" |
| `cache` | 指针取不到（或用不了），退回本机存的上一批 | 顶部提示「离线缓存」 |
| `snapshot` | 连上一批指针都没有，用打进主包的快照 | 顶部提示「打包快照」+ 显示基准日期 |
| `none` | 什么都没有 | 说明 + 重试入口，**不许空列表冒充"这个本不存在"** |

`requiresUpdate`、`factDates`、`source` 在四种状态下**都存在**（R1 前一种情况会丢：命中同批缓存时升级信号被吃掉）。
线上指针结构非法时优先退回本地已存的好指针并标 `pointerSource:"invalid"`，不再把有缓存的用户一脚打回快照。
指针说批次 A、文件却是批次 B（或五项里任何一项不符）→ 整条判失败降级，不端给界面（`oss-release-test.js` 有对应断言）。
## 五、更新一次数据的完整动作

```bash
cd wow-forever-web
node tools/build-data.js                       # 1. 改 src/data 后必跑，非 0 就停
node tools/export-mini.js                      # 2. src/data → for-mini/oss-preview/ 三份成品
node tools/oss-release.js build --env beta --check-identity   # 3. 切批次 + 与真源逐字节对拍 + 复现性核对
node tools/oss-release.js upload --env beta --dry-run         # 4. 先看会传哪些（只读，不需要标记）
WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js upload --env beta        # 5. 传批次 → 逐文件校验 → 最后换指针
node tools/oss-release.js verify --env beta                   # 6. 匿名回读比对哈希/ETag/字节/缓存头
WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js upload --env release --yes-release  # 7. 内测过了才发线上
node tools/oss-release.js list --env release                  # 8. 记下上一批 buildId（回滚位）
WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js rollback --env release --to <buildId>  # 出事就指回去
node tools/oss-release-test.js                 # 9. 动了产物结构就要跑，101 条断言全绿（本地夹具，不碰真 bucket）
```

第 3 步现在多了一道**源与产物对拍**：构建时在临时目录用同一份 `src/data` 重跑一遍 `export-mini.js`，
三份 `oss-preview` 逐字节比一遍，不一致直接 rc=1（指针溯源写 A、实际发 B 这条路被堵死）。
第 5 步多了一道**不可变批次保护**：`builds/{buildId}/` 下已有同名对象而字节与本批不同时，报警停发、绝不覆盖，指针不动。
第 9 步的反例覆盖：无标记的写命令 PUT/DELETE=0、上传第 N 个 PUT 失败后旧指针逐字节不变、
回滚前目标批次缺件/哈希不符/清单 ID 不等于 `--to`/跨环境清单一律拒绝、`clean --env release` 缺 `--yes-release` 拒绝。

**写授权口径（R1 收紧）**：`upload / rollback / clean` 是写 bucket 的动作，**不论凭证从哪来**
（环境变量、`$WOW_OSS_ENV`、仓库根 `.oss-env`、还是自动兜底到 PoE 那条线的 `.env`），
都必须显式带 `WOW_ALLOW_CROSS_CREDS=1`；没带就在任何远端请求与本地落盘之前 rc=1 拒绝。
只读（`build` / `list` / `verify` / `upload --dry-run`）不需要。
`release` 在此之上还要 `--yes-release`；`clean` 还要 `--yes-clean`（撤线上两个都得加），且清后要能列举核验，
核验不了就 rc=1，不许报"删干净了"。
凭证文件**不放 `for-mini/`**：`.gitignore` 挡不住微信打包器。现在的顺序是环境变量 → `$WOW_OSS_ENV` → 仓库根 `.oss-env`；
真把 `.oss-env` 落进 `for-mini/` 里，脚本会直接拒绝并提示移位（`project.config.json` 也顺手排除了它）。
**本站口径（2026-10-21 站主拍板）**：不单建子账号，就共用 PoE 那把，所以**每条写命令都要显式带标记，
动手前先跟站主报"用哪把钥匙、写哪个前缀"**。
批次产物落 `for-mini/oss-build/`，不入库；重跑同源字节一致（清单里没有任何时间字段了）。
`oss-preview/*.json` 仍入库（是 `export-mini.js` 的成品对拍依据），`oss-build/` 只是它的切片。

无新证据不改数；每批按"新增 / 修正 / 撤回 / 仍待实测"留一句差分，记进 `ROLES.md`。

## 六、新增模块要做的事

1. 在 `oss-release.js` 的 `buildBatch()` 里加对应文件：先出索引（列表页要的轻字段 + 路径），再按 id 出详情，
   大字段（掉落、清单、图片）另开一级，别把整块塞进索引。分片粒度改了要顺手改 `BUDGET_KB`。
2. 客户端只在 `oss-manifest.js` 里加一个 `loadXxx()`，不新写请求与缓存逻辑，页面不许自己拼 URL。
3. `for-mini/oss-build/` 不进 git；`services/forever-data.js` 里那套平铺地址是过渡期的，新页面别再依赖它。
4. 素材（原画、头像、图标）要单独一批：路径带来源分类与 manifest，示意图要就地标"不是游戏里的地图"，
   并且不打进主包 —— 口径见仓库根 `AGENTS.md`，本轮没发。
5. 数据里缺字段一律显示「待实测」或「未记录」；`level=L0` 必须带官方或客户端解包来源，否则构建失败。
