# 验证记录 · 职业页与导航二级（2026-10-12 · wow-dev）

任务书：`docs/PLAN-classes-and-nav-2026-10-12.md`（用户 2026-10-12 拍板：items 与 search 两页先不做，
classes 要补，导航那格"技能书"改叫"职业"，导航要有二级与"新"标识）。
提交：`6e66216`（功能）+ 本笔（本站更新条目与收尾）。

## 一、改了什么

| 位置 | 改动 |
| --- | --- |
| `src/classes.html` | 新页（第 17 页），`data-page="classes"`，`theme-color` 跟 `--bg` |
| `src/js/app.js` | `NAV` 的「职业」组第一格换成新页、技能书降为二级；新增 `classPage()` 渲染器并注册进派发表 |
| `src/css/app.css` | 新件 `.clhero / .chart / .spec3 / .spec / .racerow / .chtab / .chgs`；修 `.two` 单列时的栅格炸裂 |
| `app/src/lib/nav.js` | 与旧站同一份表（顺带补回新站缺的「团本」一格、统一传承的悬停说明）；`MIGRATION_NOTE` 改口 |
| `app/src/pages/ClassesPage.vue` + `router.js` | 新站第三页：路由 `/classes`、`MIGRATED['classes.html']` |
| `tools/build-data.js` | 搜索索引「职业」词条的归属页 `talent.html` → `classes.html`（带 `c=` 落到那一职业） |
| `tools/site-check.py` | `PAGES` 加 `classes`；导航断言补「职业」项；页数文案改成按 `len(PAGES)` 现算；新增第 21 节 23 条职业页断言 |
| `tools/app-parity.py` | 对拍表加 `classes` 这一条 |
| `src/data/releases.json` | 补一条带 `职业` 标签的「本站更新」→ 导航角标自己长出来 |
| `tools/serve.sh`、`AGENTS.md` ×2、`README.md`、`docs/UI.md` 3.33 | 页数与迁移状态的说法跟着改 |

## 二、跑过什么、看到什么

| 命令 | 结果 |
| --- | --- |
| `node tools/build-data.js` | 校验通过（29 条本站更新、搜索索引 4347 条 / 19 类）；`scale.navNew` 出现 `职业` |
| `python3 tools/site-check.py --app` | **561 / 561 全过**（改版前基线 526 条，本轮 +35：23 条职业页专属 + 新页带出的通用组） |
| `python3 tools/app-parity.py --page classes --strict` | **全部组合无差异**（结构计数 / 类名集合 / 正文行 / 链接 / 图片 / H1） |
| `python3 tools/app-parity.py --strict`（三页） | `classes`、`world` 无差异；`home` 仍红——那是 2026-10-12 首页改版留下的旧账（`PLAN-open-items.md` 第 13 条），本轮没碰 |
| `cd app && npm run build && npx vitest run` | 构建通过，**73 / 73** |
| `node tools/export-mini.js` | 重跑后 `git status` 里 `for-mini` 无变化（本轮没动小程序，产物仍可复现） |

渲染证据（全部由 `site-check` 产出，桌面 1440 + 移动 375）：

- `docs/screenshots/check-2026-10-12/page-classes.png` — 首屏
- `docs/screenshots/check-2026-10-12/classes-desktop.png` — 整页（含三系筛选后与未确认清单）
- `docs/screenshots/check-2026-10-12/classes-mobile.png` — 375px 整页
- `docs/screenshots/check-2026-10-12/page-index.png`、`nav-mobile-flat.png`、`nav-mobile-open.png` — 顶栏那 18 项与「新」角标

**截图入库范围**：门禁跑完会重拍整套（53 张、约 23 MB）。本轮只把职业页与顶栏这 6 张提交进仓库，
其余 47 张与已提交版本只差顶栏那一格和倒计时读数，为避免 23 MB 的 PNG churn 已回退——
随时 `python3 tools/site-check.py --app` 重生成，代价是十几分钟。

界面行为是脚本点出来的，不是只看静态图：三系卡点一下把 95 条收到 32 条、再点回 95 条；
换职业后地址、H1、三系名、条数一起变；每条改动的「来源」能展开（来源块 229 字）；
顶栏搜索"战士"在旧站落 `classes.html?c=warrior`、在新站落 `#/classes?c=warrior`。

## 三、按红线刻意没做的

- 稿子"职业概览"六行里，只有**可选种族**我们有可核对来源。其余五行（战斗定位 / 核心资源 /
  护甲类型 / 可用武器 / 团队职责）**整块不显示**，缺的写进本页未确认清单，不搬稿子的描述句。
- 层级点数门槛不做暗示（数据里那组数没在正式服实测过），界面只按坐标摆位。
- 改动只列名称、归属与类别，**不列逐字前后对照**；官方整句只在名字真出现在官方句子里才贴，
  对不上就空着（战士 95 条里只有 9 条有官方整句，剩下 86 条就写着没有）。
- 圣骑士还没有官方中文深度解析稿 → 那一格写"还没有"，并把数据里那句"尚未发布"摆出来，不凑数。
- 底部三个出口不做稿子里"生成分享链接"那种要账号的按钮。

## 四、没验到的（要人盯的地方）

1. **审美与"像不像稿子"我不当裁判**。几何判据过了（页首带 300px、立绘框 158px、职业色吃到英文名），
   但好不好看要用户在浏览器里看：`bash tools/serve.sh` 后开 <http://127.0.0.1:8817/classes.html?c=warrior>
   与新站 <http://127.0.0.1:8821/#/classes> 各扫一眼。
2. **视觉基线没重冻**：`tools/visual-check.py` 的像素与指纹基线仍冻在改版前的 16 页（`e2bf063`），
   新页不在内，所以这一轮没跑 `--check`（跑了必红，红的是"基线过期"而不是"改坏了"）。
   等这批版式被认可后再 `--make` 重冻。
3. **只有 headless Chrome 两档视口**（1440 / 375）。真机 iOS Safari、Android、以及 900–1100px 中间档
   没实拍过。
4. **封顶滚动这件事是本轮最后加的**（95 条不封顶会把两栏拉成一长一短：右栏 ~2500px、左栏 ~600px）。
   数字上现在两栏是 896 / 526，列表在卡内滚（容器 720px、内容 5790px）。
   "嵌套滚动好不好用"属于手感，没做真人测试。
5. **首页那九个职业圆标仍指向天赋计算器**，没改指新页——任务书范围外，记在 `docs/UI.md` 7.3 欠账里。
6. **小程序侧没跟**（任务书第四节明确本轮不动）。这一页的信息结构（职业 → 三系 → 技能变化 → 可选种族）
   可以复用给 `for-mini` 那个"职业"模块坑位。
7. 新站首页对拍仍红（旧账），所以 `app-parity --strict` 整仓跑起来不是零退出——这一条与本轮无关。
