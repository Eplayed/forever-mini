# VERIFY · 11-25 插件层重抓双端数据补发（12·10 团本前）

日期：2026-11-25（北京时间）。性质：**纯数据补发**，小程序代码不重传（`v1.6.3` 已于当日 16:54 上传微信开发版，待提审）。

## 1. 背景与授权

站主当日更新了网易 DD 客户端插件（QuestieDB 升至 **v1.1.6**、DF 升至 **2.1.133**），问「数据侧那边需要更新吗？12月10号要开团本了，团本数据有最新的数据吗？」。核查结论：21:09 的插件快照尚未并入成品，线上双端（Web 16:54 包 / OSS beta `2b53c3092870`）用的仍是旧插件层数据，需要重抓合并后补发。站主看完差异与门禁结果后拍板：**「好的，推上线吧」**。

红线照旧：105 共享只读；掉落不写百分比；两源分歧都留；判落地用数据文件哈希，别用 index.html；本轮不使用项目角色 skill；源码只 git 提交不 push；gh-pages 境外备用停 11-17 不推。

## 2. 数据变化（addons-merge 六步）

| 步 | 内容 | 规模 |
| --- | --- | --- |
| DF 掉落 | 副本首领掉落重并 | 1262 条 |
| 宠物 | 宠物战斗数据 | 18+1 技能 22+10 |
| 宏 | 全职业宏命令 | 245 条 |
| 副本任务 | 任务段与桥表 | 396 桥 342 |
| 坐标 | 任务接取坐标 | 269 条 |
| 物品详情 | wclbox 物品详情 | 20685 件 |

成品变化文件（新旧两包逐文件哈希对比，共 9 个，无新增/删除文件、无素材变化）：

| 文件 | 新包 SHA-256 |
| --- | --- |
| data/dungeon-geo.json | `c386eb598a6e369193440e42099d1d0ffd3119084445b336fa4b4a82525988b2` |
| data/dungeons.json | `783a6349d51e5ceb848e5272fb95afba8d8c74d04d085289b2b94d78ccb4530f` |
| data/icon-gaps.json | `a42cd0bc069a136183457afb0aad375a837bae052abac8cb8a74d1f49eb82e75` |
| data/icons.json | `7a150d5b8c6fb306412b15b24f19d394ff81b3baca5fdb67c05b28f8e2719d8d` |
| data/items-detail.json | `8efe7a384c1e0a3ffa21217747ceeeafd4ba85b5ea0609d593c10f087c2ecf93` |
| data/macros.json | `fd90814141efb20a03a33663e193a11c612197d32b4e7b99cefac62853455480` |
| data/pets.json | `7a5c6c476b75976e3010044a648cf2ec365e765324e46b03c2139ab49ad33d5d` |
| data/scale.json | `d1d0ddd5df3606acbefd0f23b82136200ca1511f756d04400244e79eecf21973` |
| version.json | `19a6992347601556475397ef9e43f4829efcd3386491c6325eb3512aedc330b6` |

开采留档：`DATA-任务名与掉落开采-2026-11-08.md` 第五节、`wow-infinite-sources.md` §26 追记（已随提交 `8074740` 入库）；开采快照留 upstream 不进成品。

## 3. 门禁（全绿）

| 门禁 | 结果 |
| --- | --- |
| addons-merge 六步 | 通过（规模见上表） |
| `node tools/build-data.js` | 通过 |
| `audit-translations --strict` | rc=0（2 条已知非阻塞警告：1 条 L2 未命中 + 1 条来源页失效待重挂，见 DATA-AUDIT-2026-11-25.md） |
| `vitest` | 190/190 |
| `oss-release-test` | 252/252 |
| `export-mini` | 主包快照 57.9 KB ≤ 60 KB |
| `oss-release build --check-identity` | 批次 `4c85302c224e`，重跑字节差 0，冷启动 43.9 KB |
| `release-package --check-only` | 4156 文件 / 35.4 MB 通过 |
| `site-check` | 首跑 rc=1 唯一红 [6h] updates_filter，判定为并发假红（撞上 --check-only 重写 dist 窗口）；探针 `--only updates_filter` 13/13 绿；**无并发全量重跑 707/707，RC=0**（23 条 375 提示按 MOBILE_SOFT 不计门槛） |

## 4. 小程序 OSS beta 发布（已完成）

命令：`$env:WOW_ALLOW_CROSS_CREDS='1'; python tools/publish.py --target mini --env beta --upload --skip-gate`（21:44）。

- 批次 **`4c85302c224e`**：179/179 上传，0 失败，0 不可变冲突（bucket `poe2-all-class`，只写 `wow/beta/v1/`，凭证 `.oss-env`）。
- 指针：`2b53c3092870` → **`4c85302c224e`**；**回滚位 `2b53c3092870`**（`node tools/oss-release.js rollback --env beta --to 2b53c3092870`）。
- `flags.json` 3.1 KB 同步对齐，开 `[bis / professions / macros / namer / grank]`。
- `verify --env beta`：逐文件回读 **177/177 问题 0**，指针与批次清单字节一致；服务端上传时间 2026-11-25 13:44:04 GMT（北京 21:44:04）。
- 台账：`PUBLISH-LOG.md` mini 行批次列已手工修正为真实批次哈希（publish.py 误读 release/latest.json 的 web 包名，已知脚本缺陷）。
- 已知闸拦（非本轮新增）：76 张配装逐件底图因名单变更被构建闸拦下，不随本轮下发，待重渲（见 11-23 发版准备记录）。

## 5. 网页 FC 发布

- 整包：`wow-forever-web-20261125-214024-826c324.tar.gz`（18.0 MB，4156 文件 / 35.4 MB），整包 sha256 `c45914519b718330c44922d100c39c73838d25735e630a73860c65f74c3fafb0`，对应提交 `826c324`。
- `pkg-verify`：**18/18** 通过（本机严格静态服务，缺文件真 404、旧页地址真 404、hash 路由直达/刷新/子路径全过）。
- FC 包：`release/fc-deploy.zip`（20,784,731 B / 19.8 MB），sha256 **`187cc8310e6b271c041b454ea1887314fa4c94641b75c3243dd8695d3de52b2f`**，备案号 沪ICP备2025127988号。
- 部署通道：本机无 FC CLI/密钥，走阿里云 FC 3.0 控制台（cn-hangzhou `paoben-web`）上传 ZIP 部署；运行时/启动命令/端口 9000 不动。
- 部署时间：**2026-11-25 22:03:45**（控制台「上次修改时间」；运行环境 自定义运行时 Debian10 Python 3.10、启动命令 `python3 app.py`、监听端口 9000 均未变）。

## 6. 公网回读对拍（已通过）

从 `https://paoben.top/` 逐个取第 2 节文件与本地新包 SHA-256 对拍：

- **8/8 部署数据文件哈希全对**：dungeon-geo / dungeons / icon-gaps / icons / items-detail / macros / pets / scale（哈希见第 2 节表）。
- `version.json` 公网 404 **属预期**：它是 release-package 写的包级标记，不在 app/dist 与 FC zip 内（zip 4157 条目实测无此文件），从来不是网站对外文件。
- 首页 `/` 200；`POST /api/t` 合法 payload（`ev=pv`）**204**；`GET /api/t` **405**；`HEAD /talent.html` **404**。
- 过程留痕：首轮回读恰逢部署切换窗口全 404，稳定后干净 URL 重读全过；POST 首轮 400 系本机 PS 5.1 传参剥引号致 payload 非法，改文件 payload 后 204（服务端无异常）。

## 7. 回滚

- 小程序：`node tools/oss-release.js rollback --env beta --to 2b53c3092870`（上一批文件仍在 builds/ 目录）。
- 网页：上一包 `wow-forever-web-20261125-164328-a96b018-dirty`（FC zip sha256 `f48b8c836217…`）仍在 release/ 目录，控制台重传即可回退。

## 8. 提交与台账

- `8074740` feat(data): 11-25 DD QuestieDB v1.1.6 / DF 2.1.133 插件层重抓并成品，双端补发收口。
- `826c324` chore: site-check 707/707 全绿截图收口＋补记 16:52/16:54 发布台账。
- 文档收口提交：见本文件与 PROJECT_DECISIONS / NOW / ROLES 更新（只提交不 push）。
- 台账：`wow-forever-web/docs/PUBLISH-LOG.md`（16:52/16:54 补记行 + 本轮 mini/web 行）。