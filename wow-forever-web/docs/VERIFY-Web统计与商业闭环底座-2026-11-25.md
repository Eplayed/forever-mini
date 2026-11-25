# Web 轻量统计与商业闭环底座落地验证 · 2026-11-25

> 本轮按站主 2026-11-25 明确指示落地两项主线：
> 1. **先做 1（轻量隐私友好统计与点击归因）**：零 Cookie、尊重 DNT、同源阿里云 FC 3.0 `POST /api/t` 采集 + SLS 结构化日志落库，并预留第三方统计（Umami / 百度统计 / Clarity）白名单配置槽；
> 2. **Web 商业化与导流矩阵底座**：明确方向为 **「外设 / 加速器合作槽 + 广告联盟」**，并同步在 1440px+ 桌面副屏纳入 **「微信小程序（跑本无限助手）+ 自研游戏（超武刷宝觉醒）」双导流位**，全槽位接入曝光与点击归因埋点。

---

## 一、改动明细

### 1. 轻量隐私统计与转化归因
- **单源配置** [analytics.json](file:///d:/project/forever/wow-forever-web/app/data/analytics.json)：
  - `allowedHosts: ["paoben.top", "www.paoben.top"]`（仅生产域名发包，本地预览、`site-check`、`pkg-verify` 与 GitHub Pages 绝不向 `/api/t` 发请求，零 404 噪声）；
  - `fcBeacon` 指向同源 `/api/t`；`provider` 预留 `none | umami | baidu | clarity` 扩展槽。
- **FC 3.0 同源采集端** [fc-static-app.py](file:///d:/project/forever/wow-forever-web/tools/fc-static-app.py)：
  - 新增 `POST /api/t`（最大 4096 B，超限 413、非法 JSON/事件 400、`GET /api/t` 405，正常返回 `204 No Content`）；
  - 仅接收低基数事件白名单（`pv` / `page_stay` / `slot_view` / `slot_click` / `outbound_click` / `search`），不记录原 IP（以当日北京日期 + 进程盐做单向 SHA-256 前 12 位 `vh` 估算日 UV），单行 `[PB_STAT] {...}` 输出至 `stdout` 自动进入阿里云 FC 日志服务 SLS。
- **前端采集引擎** [analytics.js](file:///d:/project/forever/wow-forever-web/app/src/lib/analytics.js) & [main.js](file:///d:/project/forever/wow-forever-web/app/src/main.js)：
  - 绑定 `router.afterEach`（自动统计路由 PV、上一页 `page_stay` 停留毫秒数与站内搜索事件）；
  - 监听 `visibilitychange` / `pagehide` 补发停留时长；
  - 全局委托自动捕获全站外链点击（`outbound_click`），与商业位 `slot_click`（带 `data-slot-id`）互斥防重复计数；同页同槽曝光自动去重。

### 2. 桌面副屏双导流（小程序 + 自研游戏）
- **配置升级** [side-rail.json](file:///d:/project/forever/wow-forever-web/app/data/side-rail.json) & 台账 [manifest.json](file:///d:/project/forever/wow-forever-web/app/img/art/side-rail/manifest.json)：
  - 槽 1：`mini-program-paoben`（「跑本无限助手」微信小程序，使用本地太阳码 `img/art/brand/mini-qrcode.jpg` +「微信搜一搜：跑本无限助手」）；
  - 槽 2：`cw-taptap-minigame`（站长自研《超武刷宝觉醒》，跳转 TapTap 试玩）。
- **组件升级** [SideRailPromo.vue](file:///d:/project/forever/wow-forever-web/app/src/components/SideRailPromo.vue)：
  - 1440–1599px 为 116px 紧凑双卡（`left: calc(50% + 596px)`，零压正文、零横溢），1600px+ 展开 184px 完整展示卡，`<1440px` 隐藏；
  - 小程序卡支持点击「放大扫码」弹出 220×220 高清太阳码居中窗口（支持 ESC/点击遮罩关闭）；全卡接入 `slot_view` / `slot_click` 埋点。

### 3. 外设 / 加速器合作槽 + 广告联盟底座
- **单源配置** [partner-slots.json](file:///d:/project/forever/wow-forever-web/app/data/partner-slots.json)：
  - 当前生产默认 `enabled: false`、`slots: []`、联盟默认关闭（未签约/未过审前**零 DOM、零空白栏、零外链请求**）。
- **共享组件** [PartnerSlots.vue](file:///d:/project/forever/wow-forever-web/app/src/components/PartnerSlots.vue)，挂载于 [AppShell.vue](file:///d:/project/forever/wow-forever-web/app/src/components/AppShell.vue)（`position="page-bottom"`）与 [BisPage.vue](file:///d:/project/forever/wow-forever-web/app/src/pages/BisPage.vue)（`position="bis-inline"`）：
  - 支持 `kind: "partner"`（外设装备 `peripheral` / 网络加速 `accelerator`），固定明示「合作推荐」角标与 `rel="sponsored noopener noreferrer"`，接入 `slot_view` / `slot_click`；
  - 支持 Google AdSense 与百度联盟按需懒加载，固定明示「广告」角标，仅在 `allowedHosts` 下触发，防 CLS 抖动。
- **数据卡口** [build-data.js](file:///d:/project/forever/wow-forever-web/tools/build-data.js)：新增 `analytics.json`、`partner-slots.json` 校验，并升级 `side-rail.json` 校验（强制 HTTPS / 本地素材存在 / 严拦 RMT、私服、代练、收费宏与商标词）。

---

## 二、验证证据清单

| 验证项 | 命令 / 方式 | 实测结果 |
| --- | --- | --- |
| 数据卡口与禁词体检 | `node wow-forever-web/tools/build-data.js` | **校验通过**，禁词体检干净 |
| 生产构建 | `npm --prefix wow-forever-web/app run build` | **通过**（`app-assets.py` 同步 8 文件，`vite build` 10.52s） |
| 组件与统计引擎单测 | `npm --prefix wow-forever-web/app run test` | **15/15 文件，188/188 用例 PASS**（含新增 [analytics-and-slots.spec.js](file:///d:/project/forever/wow-forever-web/app/tests/analytics-and-slots.spec.js) 7 条全绿） |
| FC `/api/t` 采集端测试 | `test_fc_stat.py` | **6/6 PASS**（POST 204 + `[PB_STAT]` 12 位不可逆 `vh` / GET 405 / 非法事件 400 / 坏 JSON 400 / 超长 413 / `/talent.html` 真 404） |
| Playwright 多视口实拍与几何校验 | `verify_commercial_ui.py` | **全部 PASS**：1440px `overflowX=0` / `mainRight=1310` / `railLeft=1316` / `railRight=1432` / 双图全加载 / 生产空 `partnerDom=false` / `badReqs=[]`；1680px `width=184` + 扫码弹窗通过；合作槽 fixture 双列 `sponsored` 链接通过；375px `display=none` / `overflowX=0` |
| 界面回归门禁 | `python wow-forever-web/tools/site-check.py --only site_wide,bis` | **311/311 PASS（rc=0）** |
| 发布打包与验包 | `release-package.py --skip-build` + `pkg-verify.py` + `build-fc-package.py` | `pkg-verify` **18/18 PASS**；新 FC 部署包 `wow-forever-web/release/fc-deploy.zip`（`4,155` 文件 / `19.8 MB` / sha256 `0fc162be5afd05dfcf0cc52782800bc6554a43234b88f81979ae213ad8ecc91b` / 备案号 `沪ICP备2025127988号`） |

### 实拍渲染证据
- [commercial-rail-1440-2026-11-25.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/commercial-rail-1440-2026-11-25.png)（1440px 生产态双导流副屏）
- [commercial-rail-1680-2026-11-25.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/commercial-rail-1680-2026-11-25.png)（1680px 完整副屏）
- [commercial-qr-modal-1680-2026-11-25.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/commercial-qr-modal-1680-2026-11-25.png)（小程序太阳码放大弹窗）
- [commercial-partner-fixture-1440-2026-11-25.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/commercial-partner-fixture-1440-2026-11-25.png)（1440px 配装页合作推荐槽示例效果）
- [commercial-375-2026-11-25.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/commercial-375-2026-11-25.png)（375px 移动端零侧栏零横溢）

---

## 三、阿里云 FC 控制台查询统计与商业位上线操作说明

### 1. 部署后在阿里云 FC 日志服务（SLS）查看统计
部署 `wow-forever-web/release/fc-deploy.zip` 到杭州 `paoben-web` 后，进入函数计算 → 日志查询，检索关键词 `[PB_STAT]`，示例统计 SQL：

```sql
-- 1) 按天看 PV 与估算 UV（vh 为单日不可逆访客摘要）
[PB_STAT] | parse-json message | select day, count_if(ev = 'pv') as pv, approx_distinct(vh) as uv group by day order by day desc

-- 2) 热门页面与平均停留时长（秒）
[PB_STAT] | parse-json message | select p, count_if(ev = 'pv') as pv, round(avg(if(ev = 'page_stay', ms, null)) / 1000.0, 1) as avg_stay_s group by p order by pv desc limit 20

-- 3) 各商业/导流位曝光、点击与点击率（CTR）
[PB_STAT] | parse-json message | where ev in ('slot_view', 'slot_click') | select slot, kind, count_if(ev = 'slot_view') as views, count_if(ev = 'slot_click') as clicks, round(100.0 * count_if(ev = 'slot_click') / greatest(count_if(ev = 'slot_view'), 1), 2) as ctr_pct group by slot, kind order by clicks desc
```

### 2. 签约合作方或广告联盟过审后的开启方式（免改代码）
- **开启外设 / 加速器合作位**：编辑 [partner-slots.json](file:///d:/project/forever/wow-forever-web/app/data/partner-slots.json)，把 `enabled` 改为 `true`，在 `slots` 填入合作条目（`position` 选 `bis-inline` 或 `page-bottom`，`category` 选 `accelerator` 或 `peripheral`，素材放本地 `app/img/art/`），跑 `build-data.js` → `npm run build` → `build-fc-package.py` 部署即可。
- **开启 Google AdSense / 百度联盟**：在 `partner-slots.json` 的 `adNetworks.adsense` 或 `adNetworks.baidu` 填入审核通过的 `clientId`/`unionId` 与对应 `positions` 广告位 ID 并置 `enabled: true`。
- **可选加挂第三方统计**：如需可视化看板，可在 [analytics.json](file:///d:/project/forever/wow-forever-web/app/data/analytics.json) 的 `provider` 填入 `umami` / `baidu` / `clarity` 及合法 `siteId` / `scriptUrl`。

---

## 四、未验到项与待执行动作
1. ~~**`paoben.top` 公网 FC 部署与真公网回读**~~：已于 **2026-11-25 14:56:07** 部署至阿里云 FC 3.0 杭州 `paoben-web` 并通过公网逐项回读验收（见下方第五节）。
2. **广告联盟真实脚本与真广告填充**：当前 `adNetworks` 为默认关闭态，仅在单测与校验层验证 schema 与开关隔离，待联盟审核通过填入真实 ID 后再做真公网验证。
3. **7 天 SLS 统计基线汇总**：需等待公网真实访客运行数日后，在阿里云 FC SLS 日志查询 `[PB_STAT]` 汇总 PV/UV、停留时长与点击率。

---

## 五、`paoben.top` 阿里云 FC 3.0 部署与公网回读验收（2026-11-25 14:56 补记）

- **控制台部署**：在阿里云函数计算 FC 3.0（华东1 杭州 `paoben-web`）上传 `wow-forever-web/release/fc-deploy.zip`（19.81 MB / 4,155 文件 / sha256 `0fc162be5afd05dfcf0cc52782800bc6554a43234b88f81979ae213ad8ecc91b`）并点击「保存并部署」，控制台显示「代码部署成功！」，**上次修改时间更新至 `2026年11月25日 14:56:07`**；运行环境（Python 3.10）、启动命令（`/var/fc/lang/python3.10/bin/python3 app.py`）与监听端口（`9000`）均未改动。
- **公网 HTTP 回读实测（2026-11-25 14:57）**：

| 检查地址 | 方法与状态 | 实测响应 |
| --- | --- | --- |
| `https://paoben.top/` | `GET` → **HTTP 200** | `text/html`（825 B），`<title>无限资料站</title>` |
| `https://paoben.top/data/scale.json` | `GET` → **HTTP 200** | `5,284` B，`generatedAt: "2026-11-25"` |
| `https://paoben.top/data/analytics.json` | `GET` → **HTTP 200** | `254` B，`enabled: true`，`allowedHosts: ["paoben.top","www.paoben.top"]`，`endpoint: "/api/t"` |
| `https://paoben.top/data/side-rail.json` | `GET` → **HTTP 200** | `1,111` B，`enabled: true`，含 `mini-program-paoben` 与 `cw-taptap-minigame` |
| `https://paoben.top/data/partner-slots.json` | `GET` → **HTTP 200** | `423` B，`enabled: false`，`slots: []` |
| `https://paoben.top/img/art/brand/mini-qrcode.jpg` | `HEAD` → **HTTP 200** | `image/jpeg` |
| `https://paoben.top/api/t`（合法事件 JSON） | `POST` → **HTTP 204** | 同源统计采集端公网真实响应成功 |
| `https://paoben.top/api/t` | `GET` → **HTTP 405** | 拒绝非 POST 请求 |
| `https://paoben.top/talent.html` | `HEAD` → **HTTP 404** | 真 404（无 SPA 200 兜底） |
