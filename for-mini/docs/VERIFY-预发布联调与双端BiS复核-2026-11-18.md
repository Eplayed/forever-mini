# 预发布联调与双端 BiS 复核 · 2026-11-18

## 小程序取数回归

- 修复前，把 `wow_forever_v1_dev_origin` 设为 `http://127.0.0.1:8899` 后，真实请求模块把指针请求发到该地址，失败即返回 `source:none`。首页将快照或离线缓存如实标成离线。旧的回归脚本只在成功收尾时还原地址，异常退出能留下这个键。
- `for-mini/services/oss-manifest.js` 去掉 Storage 覆盖。测试地址只允许开发者工具在当前 App 会话显式注入 `http://127.0.0.1:<端口>`。`for-mini/app.js` 在启动时清除历史键，并从 `ACTIVE_ENV` 派生 `globalData.dataNamespace`。M01、M02 在 `finally` 清除会话地址和历史键，再断开自动化连接。分发回归覆盖旧键、合法回环注入、真机和非回环地址的隔离以及清理后回到 OSS。
- HTTPS `wow/beta/v1/manifest.json` 回读 200，批次 `7b46092f3f08`，按线上批次清单核验 176/176、异常 0。`wow/release/v1/manifest.json` 回读 404。预发布项目维持 `ACTIVE_ENV = 'beta'`，与当前小程序线上数据入口一致。
- 线上 beta 的 76 张配装图逐件 GET 并解码，全部为 600×800 PNG，透明和不透明像素均存在。76 个套装＋阵营键对应 76 个独立文件，文件名中的 SHA-256 前 12 位与内容匹配。

## 微信开发者工具验收

- 以同一 AppID 单独编译严格校验副本，两份项目设置均为 `urlCheck:true`。清理下载缓存后用线上 `7b46092f3f08` 启动，在 Storage 重新放入 8899 历史键做反例。首页 `offline:false`，指针 `source:live`，首页素材来自真实 HTTPS OSS，App 数据命名空间为 `wow/beta/v1`。用 `https://example.com/` 做对照，工具明确返回 `request:fail url not in domain list`。见[在线首页](screenshots/prerelease-bis-2026-11-18/01-home-live.png)。
- 逐个调用模拟器配装页的职业、套装和阵营处理器，38 套、76 个组合的装备行、属性合计、图标地址和实际图像 `bindload` 均通过，人物图与各自套装和阵营键对上。另核 604 个不同图标 URL 均返回 200 `image/*`。截图见[联盟样例](screenshots/prerelease-bis-2026-11-18/02-bis-30-alliance.png)与[部落样例](screenshots/prerelease-bis-2026-11-18/03-bis-30-horde.png)。
- 海加尔峰 T1 新增整套加入冒险清单。每套使用阵营无关的六个已知部件 ID，保存名称采用“套装名 · #ID”，来源写海加尔峰。18 套逐套走页面处理器和真实清单模块通过，重复添加去重。T1 与 14–58 图鉴是固定部件名录，同部位备选来自团前 BiS 的名单数据。
- 逐一通过 27 套团前职业和专精切换，逐套打开首个部位备选。14–58 图鉴逐一切换 36 套，四分类分别为 7、9、9、11 套。T1 九职业过滤覆盖 18 套。模拟器实写并读回装备目标，三个样例分别新增团前 13 件、图鉴 5 件、T1 6 件。团前配装中梦境神像 `220606`、神圣灵动圣契 `228175` 缺已核图标键，界面用首字占位。
  [团前页面](screenshots/prerelease-bis-2026-11-18/04-bis-60.png) · [同部位备选](screenshots/prerelease-bis-2026-11-18/05-bis-60-slot.png) · [T1 职业筛选](screenshots/prerelease-bis-2026-11-18/06-tier1-priest.png) · [套装图鉴](screenshots/prerelease-bis-2026-11-18/07-item-sets.png)。
- 从实际工作区开发者工具窗口点击“BIS 配装 → 60 级团前 BiS → 战士项链出处”，跳到厄运之槌东区详情并显示地图。批量矩阵以页面事件处理器覆盖，实体手机微信体验和整套矩阵逐个触摸待复核。测试后实际工作区回到在线首页，上传入口可见。见[副本跳转实拍](screenshots/prerelease-bis-2026-11-18/08-bis-60-dungeon.jpg)和[当前开发者工具窗口](screenshots/prerelease-bis-2026-11-18/09-workspace-home.jpg)。

## 网页 BiS 与 GitHub Pages

- `BisPage.vue` 把团前主件、备选和图鉴可定位的副本出处转到实际存在的 `/#/dungeon?d=…`。之前团前点击生成未注册的 `/dungeons/:id`。
- 原画索引重生成曾丢失 `art.json.bisModels`，导致本地已有占位 GLB 却无 3D 入口。`fetch-art.py` 复用 `register-bis-models.py` 的文件校验与登记，恢复已登记的自产占位，并保留经独立验收的真实模型登记。当前网页产物使用注明身份的自产占位。真实客户端整人模型仍以通过位置审核的登记为准。
- Playwright 1440px 和 375px 均覆盖 38 套、76 个阵营纸娃娃状态、76 份两家对照、38 次弹层交互。桌面逐组合渲染 76 次 WebGL 占位，375px 抽验双阵营两次 WebGL。两视口均逐套切过 27 个团前专精及对应备选、18 个 T1 套装、36 个图鉴。分别实点主件、备选和图鉴的副本链接并等待副本详情渲染。375px 全程及桌面新增区未捕获页面异常、控制台错误或 HTTP 4xx/5xx。
  [桌面团前实拍](../../wow-forever-web/docs/screenshots/check-2026-11-18/app-bis-e2e-60-1440.png) · [375px 团前实拍](../../wow-forever-web/docs/screenshots/check-2026-11-18/app-bis-e2e-60-375.png) · [3D 占位实拍](../../wow-forever-web/docs/screenshots/check-2026-11-18/app-bis-e2e-3d-1440.png) · [375px 图鉴](../../wow-forever-web/docs/screenshots/check-2026-11-18/app-bis-e2e-item-sets-375.png)。
- 线上 Pages 状态 `built`，源分支是 `Eplayed/wuxian-atlas` 的 `main` 根目录，提交 `61997603618f5880239ad9941157736cb8b68517`，北京时间 11 月 17 日 13:21:20。公开 `data/bis.json` 实读 38 套 30 级、其余三组均为 0。新包待发布。 [公开站配装](https://eplayed.github.io/wuxian-atlas/#/bis) · [线上数据](https://eplayed.github.io/wuxian-atlas/data/bis.json)
- 按 `publish.py --target web --skip-gate --allow-dirty` 备包，`pkg-verify.py` 验收 18/18。包 `wow-forever-web-20261118-101940-cb2951d-dirty`，4,121 文件，SHA-256 `09ddc16b5f791386b42e8c0e4a9c146485b56301aac22a1b35527d53236995e9`，包内 BiS 四组为 38、27、18、36。`publish.py` 同时修复了门禁失败时引用未定义变量导致遮住原始退出码的问题。
- `deploy-gh-pages.py --repo wuxian-atlas` 已执行只读准备和本地验签。已验包的发布命令为 `python wow-forever-web/tools/deploy-gh-pages.py --repo wuxian-atlas --push --site wow-forever-web/release/wow-forever-web-20261118-101940-cb2951d-dirty/site`，待明确授权。部署后需重新核 Pages build 提交和远端 `data/bis.json`。
- 全站回归时校正了物品库两条旧数据假设。反向分歧为零时，断言入口隐藏、直达链接显示空态。探针与名录按物品 ID 独立计算分歧，再核来源统计。当前 796 条探针 `absent` 与 775 条名录 `missing` 有交集，单看总数无法判断两源是否一致。

## 构建与数据分发准备

| 验证 | 结果 |
| --- | --- |
| `node wow-forever-web/tools/build-data.js` | 通过。起名词库首次被 14 天门禁拦下，逐项对照站主提供的原始 JSON，9 职业、28 专精、1,400 个候选及顺序完全相同，随后登记本次核对日。门禁阈值继续生效。 |
| `node wow-forever-web/tools/export-mini.js` | 通过。首次写快照打开失败，重跑通过。离线快照 57.8/60 KB。 |
| `node wow-forever-web/tools/oss-release.js build --env beta --check-identity` | 通过。候选 `897e0ee4f7f2`，176 个数据文件＋2 份清单、76 张底图，7 份导出逐字节一致，二次构建字节差异 0。候选起名词库核对信息已更新，真实 beta 验收仍使用线上 `7b46092f3f08`。 |
| `node wow-forever-web/tools/oss-release-test.js` | 252/252 通过，含两个取数地址回归。 |
| `npm run build` 与 `npx vitest run` | 通过，14 文件、181 个测试。 |
| `python -X utf8 wow-forever-web/tools/site-check.py --app --app-base http://127.0.0.1:4190` | 最终串行整站回归 707/707，退出码 0，BiS 组含 375 既有硬闸。两条 375 点击目标尺寸提示保留。内置静态服务器的一次复跑出现连接拒绝，最终使用正常 Vite 静态预览。 |
| 小程序静态检查 | 微信工具 `wcc` 19 份、`wcsc` 20 份和 38 份 JS 语法通过。按要求扫描页面、服务与组件中的 `?.`、`??`、`const self = this` 及页面/组件 WXSS 裸色值，命中 0。 |
| `build --env release --check-identity` 与 `assets`、`posters`、`upload` 的 `--dry-run` | 四项退出码均为 0。`for-mini/oss-build/release/` 已准备同源候选 `897e0ee4f7f2`，含通过位置与装备清单对账的 76 张底图。远端 `release` 仍待授权。 |

## 发布命令

继续使用当前线上 beta 数据时，微信开发者工具上传的代码保持 `ACTIVE_ENV = 'beta'`。发布到独立 release 数据空间时，先授权并上传素材、人物图和批次，回读通过后再把 `ACTIVE_ENV` 切到 `release` 并复测。`project.config.json` 与本机私有配置里的 `urlCheck: false` 用于开发调试。同 AppID 的严格校验已确认 `https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com` 的请求可用，上传后按体验版在真机再验。

以下 PowerShell 命令仅供授权后在仓库根执行，顺序先素材和底图、后发布指针。

```powershell
$env:WOW_ALLOW_CROSS_CREDS = '1'
node wow-forever-web/tools/oss-release.js assets --env release --yes-release
node wow-forever-web/tools/oss-release.js posters --env release --yes-release
node wow-forever-web/tools/oss-release.js upload --env release --yes-release
node wow-forever-web/tools/oss-release.js verify --env release
```
