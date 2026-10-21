# OSS-01 独立复核与 Qoder 整改交接

日期：2026-10-21｜主角色：wow-dev｜范围：`tools/oss-release.js`、`oss-release-test.js`、`for-mini/services/oss-manifest.js`、`for-mini/docs/DATA.md`、`for-mini/project.config.json`。仅做本地构建/桩测试与一次只读 `list --env beta`；**没有上传、删除、回滚或切换真 Bucket 指针**。

## 结论

**分片与本地构建方向正确，但 OSS-01 不通过上线前验收。** 本地 `oss-release-test.js` 38/38、语法检查 rc0、`build --env beta --check-identity` rc0；`list --env beta` 只读显示线上 `wow/beta/v1/builds/` 为空、指针不存在，与交接一致。当前的 38 条覆盖了构建正常路径和少数数据反例，**没有覆盖写授权的全部凭证来源、客户端数据完整性、缓存/版本分支及回滚安全性**。先修下表，再接 M01 页面；不需要任何真 Bucket 写入来复现这些问题。

| 优先级 | 定点证据 | 影响与验收要求 |
| --- | --- | --- |
| P0 写授权可绕过 | `oss-release.js:341-385` 只在 `crossProject=true` 时检查 `WOW_ALLOW_CROSS_CREDS`。本地用**假** `OSS_ACCESS_KEY_ID/SECRET` 调 `loadCreds(true)`，无标记返回 `ok:true,crossProject:false`。`WOW_OSS_ENV` 与 `for-mini/.oss-env` 路径也标成 `cross:false`。 | 与站主“**每条写命令都显式带标记**”不符。把标记检查设为所有 `upload/rollback/clean` 的统一写前置，与钥匙从哪里读无关；无标记必须在任何远端请求或本地上传动作前 rc1。只读、build、dry-run 不需要标记。反例分别覆盖环境变量、指定文件、本地文件及自动 PoE 路径，凭证使用假值/本地桩，不碰线上。 |
| P0 release 撤空缺第二道确认 | `oss-release.js:678-699` 的 `clean --env release --yes-clean` 没有 `--yes-release` 检查；它会列举 `wow/release/v1/` 并进入删除循环。`after` 列举失败时，行 699 也可能报 rc0。 | `clean` 是最大破坏面，release 必须同时要求 `--yes-clean`、`--yes-release`、写标记，且清前/清后明确打印桶与前缀；清后无法验证剩余数应 rc1。用本地假 OSS 失败注入断言 0 DELETE。`for-mini/.oss-env` 目前不存在，但若今后放在小程序根，仅 `.gitignore` 不保证不进微信代码包；把凭证文件改放项目外，或加打包排除并以实际包文件清单证明不含密钥。 |
| P0 客户端声称逐文件验 SHA，实际没有 | `oss-release.js:263-313` 的 `files.json` 与 `integrityNote` 写“客户端每个文件都按 sha256 校验”；`oss-manifest.js:144-178,215-216` 从未计算/比较 SHA。`meta/glossary` 没有内嵌 `buildId`，索引/详情只在有 `buildId` 且不同时才拒绝。纯本地桩给指针一个错误 SHA、返回相同 buildId 的假索引，`loadKey()` 仍返回 `live`。 | 接页面前必须让实际检查与文档一致：至少对指针列出的入口文件验证哈希/字节，对按需详情与掉落从可信索引或 bundle 取期望哈希；否则删去“逐文件验证”承诺，改成明确的有限批次校验，并对全部文件强制校验 buildId、类型、ID 与路径。以篡改一个字段但保持有效 JSON 的反例证明不返回 `live`；无论选择哪种设计，重算冷启动字节/GET 成本。 |
| P1 缓存与升级信号丢失 | `oss-manifest.js:150-159` 只要同批缓存命中就直接返回 `source:'cache'`，即使刚刚在线取到指针；这会让第二次正常打开显示“离线缓存”。该分支没有 `requiresUpdate`。本地桩：指针要求 `minClientSchemaVersion:99`，首次返回 `live,requiresUpdate:true`，再次返回 `cache,requiresUpdate:undefined`。坏指针在 `:113-115` 返回 `invalid`，也不回退已有好指针。 | 区分“用本地数据省流量”与“因离线而降级”；`requiresUpdate`、事实日期和批次状态对 live/cache/snapshot/none 都有一致契约，旧客户端不能因缓存命中绕过升级提示。指针内容非法与网络失败都测试已有缓存的退路，不能把损坏的线上指针视为正常空数据。 |
| P1 回滚未核目标批次 | `oss-release.js:658-673` 只读回目标 `manifest.json`、检查 `env`，即把它写成新指针；未核目标 `buildId` 与 `--to` 一致、`files.json` 哈希和目标数据文件完整。 | 半传批次的自带清单也可能存在，回滚会激活坏批。先在本地假 OSS 注入“目标缺一个详情/哈希错/自带 manifest 的 ID 不等于 --to”，应拒绝且指针字节不变；再有真实 beta 验收条件时，按站主已定的凭证报备口径做有限演练。 |
| P1 “不可变批次”可被同 ID 覆写 | `buildBatch()` 的 `buildId` 不含时间，但 `manifest.builtAt` 每次变；`cmdUpload:556-566` 只要 ETag 不同就 PUT 同一个 `builds/{buildId}/manifest.json`（其他同 ID 文件若远端被改也会覆写）。`--check-identity` 自己承认 `manifest` 差异字段 `[builtAt]`。 | 同一 `buildId` 的发布批次应真正不可变：重跑构建不改已存在自带清单字节；远端同路径内容不同应报警停发，不应覆盖。允许用一个独立的发布记录记“这次上传时间”，但不把它写进不可变批次。给“同源隔一分钟重建/远端同键异字节”两个反例。 |
| P1 基底与导出产物可漂移 | `buildBatch:142-183` 从 `oss-preview` 取实际数据，却只把 `src/data` 原件哈希填进 `manifest.source.inputs`，没有比较两者语义。独立临时夹具把预览里的第一本改名，源基底不改，`buildBatch('beta')` 仍返回 `errors:[]`。 | 构建前检查 `glossary/dungeons` 语义与真源一致、`meta` 与 `export-mini.js` 生成结果一致，或在隔离目录重导出再逐字节对拍。源和导出不配套必须 rc1，避免指针溯源写 A、实际发布 B。 |
| P2 页面取数上下文尚未闭合 | `loadKey()` 只返回数据和 `buildId`，`loadDungeonDetail(manifest,item)` 需调用方另取 manifest；若列表与详情之间指针切批，页面容易混用旧索引和新指针。`forever-data.js` 仍走旧平铺地址。 | M01 应把本次索引使用的 manifest/批次上下文一起交给详情，整条查询固定同一 buildId；首页与中英速查同步收敛至新入口，保留收藏。分享冷启、无缓存离线、38 本索引快照都用微信开发者工具和人工点击验。 |

## 已运行的独立验证

| 命令/方式 | 结果 |
| --- | --- |
| `node wow-forever-web/tools/oss-release-test.js` | **38/38 rc0**；说明原测试绿，但未覆盖上表反例 |
| `node --check` 三个 JS | rc0 |
| `node tools/oss-release.js build --env beta --check-identity` | `buildId=2bbd8bd4d36b`，数据文件逐字节 0 差异；`builtAt` 仍随重建改变 |
| `node tools/oss-release.js list --env beta` | 只读：线上批次 0、指针不存在、rc0；不等于上传/回滚已验 |
| 假凭证调用 `loadCreds(true)` | 无标记返回 `ok:true`（只调用函数，**没有网络**） |
| `wx` 本地桩 | 错 SHA 的假索引仍为 `live`；第二次同批读为 `cache` 且 `requiresUpdate` 丢失；坏指针不回退好缓存 |
| 临时 `oss-preview` 改名夹具 | 源基底不改，`buildBatch('beta')` 仍成功，源/预览未对拍 |

## 给 Qoder 的提示词（先修 OSS-01-R1，再交 M01）

> 本轮角色 wow-dev。先读仓库根与 `for-mini/AGENTS.md`、`wow-forever-web/docs/PRD-移动查询首期-2026-10-21.md`、本复核文件、现有 `for-mini/docs/VERIFY-OSS-01-分发层-2026-10-21.md`。只改 `wow-forever-web/tools/oss-release.js`、`oss-release-test.js`、`for-mini/services/oss-manifest.js`、必要的 `for-mini/project.config.json` 与 `for-mini/docs/DATA.md`；第一阶段交 `for-mini/docs/VERIFY-OSS-01-R1-2026-10-21.md`。先修**所有写命令统一要求 `WOW_ALLOW_CROSS_CREDS=1`**（不依赖凭证来源）；`clean release` 额外要求 `--yes-release`；清后核验失败要非零。凭证不能进入小程序包。用假凭证/本地假 OSS 覆盖四种来源与 upload/rollback/clean，断言没标记或没二次确认时 **PUT/DELETE=0**。再修客户端实际完整性/版本/缓存契约（错哈希、坏指针、同批缓存、旧客户端）、回滚目标批次完整性、同 buildId 的不可变性和源/导出对拍；每条先补能红的反例，再改代码，不许靠改期望变绿。失败注入“第 N 个 PUT 失败”时旧指针必须逐字节不变，并测试回滚缺文件拒绝。所有测试先用本地夹具，**不得访问写入真 Bucket**；只读查询可以做，尤其不要拿真实钥匙做“失败实验”。现有工作区叠有别的会话未提交变更，禁止批量 `git add`/提交/重置。
>
> OSS-01-R1 验收通过后，按 PRD 第 8 节继续 M01，单独交 `for-mini/docs/VERIFY-M01-副本随手查-2026-10-21.md`：接页面到 `oss-manifest.js`，生成 38 本索引主包快照并卡 60 KB，完整核对首页/速查旧入口迁移、冷启分享、断网和缺字段。点击 automator 取不到证据时列“没验到的”并交人工手测，不用 `page.setData` 冒充。M01 与 R1 分两份验证、分两次提交；不上传 beta/release、不发小程序。交回文件路径、命令 rc、反例结果、截图及未验项后停下，等独立复核。若后续获准写真 Bucket，再按站主已定口径**先报告使用 PoE 哪把钥匙和确切前缀，每条写命令显式加 `WOW_ALLOW_CROSS_CREDS=1`；release 另加 `--yes-release`**。

状态：**已定**——本地构建和批次切片可用，beta 当前为空；**阻塞（原因）**——上表 P0/P1 未修，不能签发 OSS-01 或进行 M01 发布；**待用户确认**——无新的产品决定，真 Bucket 写入仍需沿已定报备口径另行执行。
