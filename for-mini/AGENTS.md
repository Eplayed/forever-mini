# 无限资料小程序（for-mini）· 开发指引

## 产品边界

无限服中文资料线的小程序端，与 `wow-forever-web/app/data/` 共用同一份数据基底（2026-10-24 旧站删除，src/ 整目录撤掉）；网页产品就是 `wow-forever-web/app/`。个人主体，类目只有 `工具-信息查询`，零 UGC，不做付费与虚拟支付。

当前状态：**底子**。已落地数据层 + 中英速查 + 首页完整度；天赋计算器、技能书、副本手册、溯源页只有入口，未实现。

核心路径：

1. **查译名**：进「中英速查」，搜中文名 → 看英文原名/待补 → 展开看来源与核对日期 → 一键复制。
2. **看可信度**：首页显示 L0–L3 完整度与「还没确认的」缺口清单，缺什么明说。

不做的事（与资料站同一条红线）：

- 不做角色查询、战斗日志、DPS 或强度排行、宏与循环提示、新闻流、评论与投稿。
- 不做 AI 生成、不做需要登录的能力、不做 web-view 跳转（个人主体没有）。
- 站名与文案不出现「魔兽 / 魔兽世界 / WoW / 暴雪」作为名称主体；页脚固定「非官方粉丝资料站，与暴雪娱乐及网易无关」。

## 技术与数据

- 原生微信小程序，微信开发者工具直接打开本目录，无 npm 依赖。
- 数据访问统一走 `services/forever-data.js`：`loadMeta()` / `loadGlossary()`，内部完成 **OSS → storage 缓存 → 打包快照** 三级回退，返回 `{ data, source }`，`source` 必须是 `live/cache/snapshot` 之一。页面拿到 `source !== 'live'` 时要显式提示离线，禁止静默呈现。
- 不要在页面里散落硬编码 OSS URL；改路径只改 `services/forever-data.js` 的 `BASE_URL`。
- OSS 命名空间 `wow/{env}/v1/`（bucket 沿用已备案域名，与 POE、AI 两条线完全隔离）。待上传内容用 `node wow-forever-web/tools/export-mini.js` 生成到 `oss-preview/`。
- `data/forever-*-snapshot.js` 由同一个脚本生成，**结构必须与 `oss-preview/*.json` 一致**；快照只保留少量词条（默认 60 条，主包预算 60 KB），禁止把全量数据打进主包。
- 收藏存 `wow_fav_terms_v1`，缓存 key 前缀 `wow_forever_v1_`，都不依赖登录。
- 设计令牌在 `app.wxss` 的 `page` 选择器（与 `wow-forever-web/docs/UI.md` 同源：暗底 `--bg #0e1013` + 暖金 `--gold #e0a96d`），完整度徽标 `.badge-L0/L1/L2/L3` 全站统一，新页面复用，不要硬编码色值、不要自创徽标样式。
- 语法约束：不用 `?.` 与 `??`，Python 侧脚本兼容 3.9。
- 数据分级、两源分歧两个都留、掉落不写百分比、禁止机翻与编造 —— 同**仓库根 `../AGENTS.md` 第五章红线**；角色分工与交接台账见 `../AGENTS.md`、`../ROLES.md`。

## 页面与取数的两条现状（2026-10-26 补）

- **配装页 `pages/bis/index` 没有主包快照**：共享物品表 118 KB，而快照预算（60 KB）只剩 6 KB 余量，
  硬塞会把别的通道挤掉。所以这一页取数只走线上，取不到时必须明说"要联网才看得到"，不许半截显示。
  数据在分发层现算成 `bis/index.json` + `bis/items.json` + 38 个 `bis/set/*.json`，
  口径记在 `docs/DATA.md` 的"配装线"那一节。
- **3D 那一层是占位**（一件一块、颜色跟品质走），界面上固定写"不是游戏里的样子"；
  换成真模型之前这句话不许撤，换的时候要先过根 `AGENTS.md` 的素材红线。
- 写页面脚本时**别用 `self` 当 `this` 的别名**：小程序运行环境里 `self` 是全局对象，
  `const self = this` 会被它盖住，报 `TypeError: {} is not a function`（2026-10-26 撞过，排查花了很久）。
  异步链里要引用页面实例，就用箭头函数里的 `this`。

## 功能开关与专业页（2026-10-27 补）

- **页面级开关读 `services/features.js`，不许在页面里写死**。取的是 `wow/{env}/v1/flags.json`
  那一份可变对象（与指针同一档 `max-age=60`），逐条三层兜底 `live > cache > data/flags-local.js`。
  被门控的页在 `onLoad` 里 `features.load(true)` → `isOn(name)` 为假就只渲染"这一页还没开放"，
  **一个数据请求都不发**；入口卡 `wx:if` 整块收掉，不留空白格。
- **`features.load()` 只收一个参数 `force`**（2026-10-27 踩过）：第一版签名是 `load(env, force)`，
  页面按直觉传了 `load(true)`，env 就成了 `true` → 命名空间拼出 `undefined` → 请求必失败 →
  永远走打包默认表，而界面看不出任何不对（表现是"开关怎么拧都没反应"）。
- 开关的缓存 key **不许带 `@`**（`wow_forever_v1_flags_beta`）：带 `@` 的键会被 `noteBuild`
  当旧批缓存清掉，开关不是按批存的东西。
- **专业页 `pages/professions/index` 与配装页一样没有主包快照**（一片最大 65.8 KB），
  并且**默认关着**：`app/data/flags.json` 里 `professions.on=false`，站主决定何时公开。
  一屏只画 60 行（`setData` 有 1 MB 上限，511 行的制皮一次塞进去会炸），"再显示 60 条"往下放；
  分箱、技能四档、列名一律读索引下发的那份，页面不自己抄。
- **回归脚本不许往 `for-mini/` 里写文件**：开发者工具开着 `compileHotReLoad`，写进去会把小程序
  打回首页，制造一片"路由没到位"的假红（截图是这条老规矩，2026-10-27 写 flags 又踩一次）。
  要演"线上拧开关"，写 `/tmp/m01-flags-live.json`，假 OSS 用 `FAKE_OSS_FLAGS_FILE` 覆写那一份。

## 阻塞项（截至 2026-10-08）

| 项 | 状态 | 说明 |
| --- | --- | --- |
| appid | 阻塞 | 现为测试号 `touristappid`。无限服小程序需独立 appid，且名称未定（资料线待办 D1），注册即卡备案起跑 |
| request 合法域名 | 阻塞 | 有 appid 后要在公众平台把 OSS 域名加进白名单，否则真机全部走快照 |
| 天赋层级点数门槛 | 阻塞 | 无官方来源，界面不许显示猜测值；等实测或官方稿 |
| 类目与备案 | 待运营 | 备案 1–20 工作日是关键路径，任何排期先排它 |

## 验收

1. 微信开发者工具导入本目录（测试号），两个 tab 均正常渲染，无控制台报错。
2. 断网（或域名未加白名单）时：顶部出现「打包快照」提示，速查页仍有词条，不白屏。
3. 速查页：搜索、分类切换、只看收藏即时生效；复制内容正确，英文缺失时显示「英文名待补」而不是空白或机翻。
4. 词条展开区能看到该条的来源类型、备注、URL 与核对日期，2 次点击内可达。
5. 主包体积：`docs/`、`oss-preview/` 已通过 `project.config.json` 的 `packOptions.ignore` 排除在外。
6. 数据改动后跑 `node wow-forever-web/tools/build-data.js` 与 `node wow-forever-web/tools/export-mini.js`，两者退出码均为 0。
