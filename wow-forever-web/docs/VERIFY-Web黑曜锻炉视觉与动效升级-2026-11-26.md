# Web 端「黑曜锻炉 · 史诗剧场」× 全屏火星 × 左侧导航侧栏 × 旋转流光边框验收 · 2026-11-26

> 2026-11-26 站主从 4 套交互式重设计方案中选定 **方案 A「黑曜锻炉 · 史诗剧场」**，并进一步拍板叠加三项招牌视觉升级：**全页面漂浮火星粒子** + **桌面左侧导航侧栏** + **旋转流光边框**。本轮已完成全站落地、门禁同步、4 张 1440px 实拍核验与最新 `fc-deploy.zip` 打包验包。

---

## 一、核心升级清单

1. **黑曜锻炉令牌体系**（[tokens.css](file:///d:/project/forever/wow-forever-web/app/src/styles/tokens.css)、[index.html](file:///d:/project/forever/wow-forever-web/app/index.html)）
   - 全站底色切换为深黑曜石炭黑（`#0b090d`）与暖金/余烬体系，同步更新 `meta[name=theme-color]`，全站文字保持 AA/AAA 对比度。
   - 新增 `--forge-*`、`--nav-w`（`196px`）、`--forge-beam`、`--mx`/`--my`、`--cls-glow` 全部声明在 `tokens.css` 单一事实源。
2. **全页面漂浮火星粒子**（[ForgeEmbers.vue](file:///d:/project/forever/wow-forever-web/app/src/components/ForgeEmbers.vue)、[AppShell.vue](file:///d:/project/forever/wow-forever-web/app/src/components/AppShell.vue)）
   - 将 `<ForgeEmbers :count="54" fullscreen />` 上提挂载至全局外壳 `AppShell.vue`，以 `position: fixed; inset: 0; pointer-events: none; mix-blend-mode: screen;` 覆盖全站 23 条路由（双景深 54 颗缓飘余烬火星，支持窗口自适应、页签隐藏自动暂停与 `prefers-reduced-motion: reduce` 关闭）。
3. **桌面左侧黑曜锻造导航侧栏**（[forge.css](file:///d:/project/forever/wow-forever-web/app/src/styles/forge.css)、[SideRailPromo.vue](file:///d:/project/forever/wow-forever-web/app/src/components/SideRailPromo.vue)）
   - `≥1280px` 桌面端将 `nav.main` 固定至左缘（`196px` 宽、满视口高度 `calc(100vh - var(--hd-h))`），8 组导航与底部 `极速检索 ⌘K` 在 1440×950 视口内无滚动完整展示；顶栏收窄为单行磨砂黑曜条（`~54px`，将 `backdrop-filter` 挂于兄弟 `.hd-top` 避免劫持子元素 `fixed` 包含块）。
   - `1440px+` 与右侧副屏导流卡（`right: 10px/14px`）组成均衡三栏布局，正文零挤压、零横向溢出；`<1280px` 及 `375px` 移动端自动回落为横滑胶囊带。
   - 按 2026-11-26 站主决定同步更新 `site-check.py` `test_app` 1440 导航侧栏断言（8 组齐、7 组色、固定贴左、满高 `h>=400` 且不遮挡 `#main`）。
4. **旋转流光边框 + 3D 倾角 + 鼠标金光追踪**（[forge.css](file:///d:/project/forever/wow-forever-web/app/src/styles/forge.css)、[forge-fx.js](file:///d:/project/forever/wow-forever-web/app/src/lib/forge-fx.js)）
   - 基于 CSS `@property --forge-beam` + `mask-composite: exclude`：
     - **常驻熔金旋转流光边框**：首页 Hero 剧场、团本页 Hero 剧场、首页 12/10 倒计时基座、团本页倒计时徽章、右侧副屏导流容器；
     - **悬停点亮旋转流光边框**：团本大卡、模块卡、首页双主卡，以及**九职业徽章悬停点亮各自本命色（`CLASS_COLOR`）旋转流光边框**。
   - 全站卡片支持事件委托鼠标金光追踪（`--mx`/`--my`），桌面端职业徽章/板块画廊/倒计时基座支持 3D 倾角，并支持 `Ctrl+K` / `⌘K` / `/` 全局快速聚焦搜索。
   - 独立作为第五层样式引入 [main.js](file:///d:/project/forever/wow-forever-web/app/src/main.js)，不改动 `motion.css` 门禁。

---

## 二、验证证据清单

| 验证项 | 命令 / 方式 | 实测结果 |
| --- | --- | --- |
| 前端构建 | `npm --prefix wow-forever-web/app run build` | **通过**（4.09s，`index-*.css` 162.55 KB） |
| 单元测试 | `npm --prefix wow-forever-web/app test` | **17/17 文件，193/193 用例 PASS**（含新增 [forge-fx.spec.js](file:///d:/project/forever/wow-forever-web/app/tests/forge-fx.spec.js)） |
| 全套回归门禁 | `site-check.py --only css_tokens,app,motion,site_wide` | **369 / 369 PASS（rc=0）**，23 路由 AA 对比度 0 失败、`motion.css` 全绿 |
| 侧栏修复后专项复验 | `site-check.py --only css_tokens,app` | **81 / 81 PASS（rc=0）**，实测侧栏 `pos=fixed, left=0, w=196, h=946, mainClear=true`，375 移动端 0 偏小点击项 |
| 发布打包与验包 | `release-package.py --skip-build` + `pkg-verify.py` + `build-fc-package.py` | `pkg-verify` **18/18 PASS**；新 FC 部署包 `wow-forever-web/release/fc-deploy.zip`（`4,156` 文件 / `19.8 MB` / sha256 `668934576754…`） |

### 1440px 实拍渲染证据（全部 `navW=196, navH=896, mainL=196, over=0`）
- [forge-home-1440-2026-11-26.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/forge-home-1440-2026-11-26.png)（首页：单行顶栏 + 左侧全高导航栏 + 全屏火星 + Hero/倒计时/副屏旋转流光边框 + 三颗按钮单行对齐）
- [forge-raids-1440-2026-11-26.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/forge-raids-1440-2026-11-26.png)（团本中心：左栏「世界→团本」高亮 + 全屏火星 + Hero/倒计时旋转流光边框 + 三座团本金属大卡）
- [forge-dungeons-1440-2026-11-26.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/forge-dungeons-1440-2026-11-26.png)（副本手册：三栏黑曜锻造布局 + 全屏火星）
- [forge-bis-1440-2026-11-26.png](file:///d:/project/forever/wow-forever-web/docs/screenshots/forge-bis-1440-2026-11-26.png)（BIS 配装：左栏「配装」高亮 + 全屏火星 + 3D 展示窗）

---

## 三、提交推送与公网发布回读（2026-11-26 21:19–21:23）
- **Git 提交与推送**：提交 `267d35f`（20 个白名单文件）已推送至远端 `codex/forever-mini-adventure`（`327c496..267d35f`）。
- **阿里云 FC 3.0 部署**：已在杭州 `paoben-web` 函数上传部署最新 `fc-deploy.zip`（`19.83 MB` / `20,790,710 B` / sha256 `668934576754…`），控制台核验上次修改时间更新为 **`2026-11-26 21:22:53`**（Python 3.10、启动命令 `/var/fc/lang/python3.10/bin/python3 app.py`、监听端口 `9000`、超时 `60 秒` 均未改动）。
- **公网 `https://paoben.top/` 实测回读**：
  - `GET /` → **`200`**（`825 B`，`theme-color=#0b090d`，引用 `./assets/index-BN_5Ke6f.css` 与 `./assets/index-CxSY-uE2.js`）
  - `GET ./assets/index-BN_5Ke6f.css` → **`200`**（`162,550 B`，命中 `--forge-beam` / `forge-embers-full` / `--nav-w`）
  - `POST /api/t` → **`204`**，`GET /api/t` → **`405`**，`HEAD /talent.html` → **`404`**
