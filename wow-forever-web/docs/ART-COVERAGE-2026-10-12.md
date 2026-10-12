# 素材覆盖盘点 · 2026-10-12（wow-data + wow-dev）

起因：用户给了豆包那条对话 `https://www.doubao.com/thread/xPanHjJ1YkmeQt38q`，要求"按设计稿还原 web 页面（包括团本）"。那条对话里给豆包的原话是：

> 卡片、天赋图、副本、团本中需要图标和背景图，数据在 wow-forever 中有，你看看能不能全部补齐后，再出全部的设计稿

所以本轮先把**前半段**用实测回答掉：我们这边的图标和背景图到底齐不齐、缺的能不能补。后半段（照稿还原）现在做不了，原因写在第一节。

## 一、设计稿本身：取不到（阻塞，不是没试）

用真实浏览器打开那条链接，页面上只有三行：

```
和豆包的对话
2026 年 10 月 12 日 · AI 生成可能有误 注意核实
卡片、天赋图、副本、团本中需要图标和背景图，数据在 wow-forever 中有，你看看能不能全部补齐后，在出全部的设计稿
暂不支持该消息类型
```

- 豆包的回复是一条**共享页不支持的消息类型**（大概率是它生成的 HTML/代码类产物），文本层拿不到。
- 页面自带的账号态是 `会话过期，请重新登录`（`_ROUTER_DATA.accountInfo.error_code = 13`），未登录状态下接口不再往下发内容。
- 网络面板里除了埋点与 SDK 握手，没有会话数据请求——正文不是被我们过滤掉了，是没下发。

**没有稿子我就不会动手改版式**：那等于凭想象复刻，改完你也没法判"像不像"。可用下面任一种方式把稿子给我：

1. 在豆包里把那条回复**导出成 HTML 文件**或复制成纯文本，放进 `wow-forever-web/docs/reference/`；
2. 直接把稿子的**截图**发进来（桌面一张 + 手机一张最好），我按图逐页对；
3. 或者你把稿子描述成字段清单（哪一页、几栏、每栏摆什么），我按清单实现。

## 二、四条线的实测数字

| 线 | 该有多少 | 现在有多少 | 缺的能不能补 |
| --- | --- | --- | --- |
| 天赋图（节点图标） | 466 个节点 | 466 个都有图标键，且本地文件全在 | 齐，无缺口 |
| 全站图标键 | 引用 2095 个 | 本地 2013 个 | 缺 83 个：官方 CDN 五个候选路径实测全 403/404，多是无限新装备，界面退回自绘块（登记在 `src/data/icon-gaps.json`） |
| 副本与团本载入图 | 38 座 | 36 座 | 缺 2 座：`barrow-deeps`、`hyjal-summit`——两台源站对应地址实测都回 404，不拿别的图凑 |
| 首领头像 | 228 个首领 | **本轮从 0 补到 146** | 剩下 82 个：78 个源站自己标着"没有这张脸"（页面上就是 `data-unknown` 占位块），4 个源站页面上根本没有这一节 |
| 页面卡片头原画 | 14 个内容页 | 9 个板块有图 | 另外 5 页（系统规则 / 时间表 / 动态 / 排行 / 溯源）没有对得上的原画，走 `noart` 分支，只留标题左侧蓝线 |

团本那一行单独说：`barrow-deeps` / `hyjal-summit` / `onyxias-lair` 三座在数据里**首领名单是空的**（客户端队伍查找器只有排队条目，没有首领），所以团本页现在能挂的只有一张载入图，一个头像都挂不上。

## 三、本轮改了什么

1. **头像路径必须从源站页面读，不能拼。** 我先按我们存的首领 id 拼 URL 去试，228 条全 404；实际源站用的是另一套键（`rhahkzor` 对我们存的 `rhahk-zor`）。猜出来的 404 不是源站缺，是我们的错——这条已经写进抓取器的注释里。新增 `tools/scrape-wclbox-dom.py --what bossfaces`：35 个副本页逐个渲染，从 `section.sj-boss` 的内联背景里读真实路径，产出 `src/data/upstream/wclbox-boss-faces.json`。
2. **转存工具**：`tools/fetch-art.py --what bosses`（配 `--probe` 只量不下载）。落到 `src/img/art/bosses/`，`manifest.json` 逐条记来源 URL 与抓取日期，`art.json` 新增 `bosses` 索引——与副本载入图、职业背景图同一套口径：整目录删掉就回退自绘，只影响视觉。
3. **数据字段**：`merge-dungeons.js` 给每个首领挂 `boss.portrait`（146/228），并写 `dungeons.json` 的 `meta.bossPortraits` 交代口径。重跑两次 md5 一致，幂等。
4. **顺手修了一个真 bug**：`merge-dungeons.js` 里挂载入图那一段在"这张卡片找不到"时提前 `return`，而团本根本不在卡片列表里——结果奥妮克希亚的巢穴的图明明转存在本地，`raids` 三条的 `art` 却一直是空。现在先挂图再找卡片。
5. **界面上脸**：副本抽屉每个首领名前一个头像方块（复用 `.liw t`：自绘块垫底、本地图盖上面、`onerror` 露出自绘，不留裂图）；团本页"另一份资料自述"那张表加了「载入图」一列，没有的写"源站没有"，并在"这一页还没有的"里交代缺几座。
6. **卡口**：`build-data.js` 校验 `art.json` 的 `bosses`/`factionCities` 指向的文件存在，并逐个检查首领挂的 `portrait` 路径真的在仓库里；`site-check.py` 新增 4 条断言（头像方块数 = 首领数、放图的集合 = 数据里 `portrait` 的集合、团本载入图列逐行等于数据、缺图座数在页面上有交代）；`audit-assets.py` 的体检报告加了"首领总数/挂上头像/孤儿文件/按本列缺口"。
7. **一条命令**：`bash tools/refresh.sh dungeons` 的链路里补上了 `bossfaces` 与 `fetch-art --what bosses` 两步，顺序在 `merge-dungeons` 之前。

## 四、没做到的

- 团本的首领头像：0 个可挂，因为三座团本在客户端里就没有首领名单。要等能进游戏或官方名单。
- 4 个首领（`old-serra-kis`、`twilight-lord-kelris`、`aku-mai`、`grubbis`）源站页面上没有对应小节，名字对不上就不猜图。
- 2 座团本的载入图：两台源站实测 404。
- 83 个图标键：官方 CDN 没有文件，界面继续自绘。
- 小程序侧：`portrait` 字段已经随 `dungeons.json` 导出（`export-mini.js` 通过，快照 25.5 KB / 预算 60 KB），但小程序现在的首领列表界面**还没改**——这批头像目前只在网页上露出来。

## 五、复现

```bash
cd wow-forever-web
python3 tools/scrape-wclbox-dom.py --what bossfaces   # 35 页，约 2–3 分钟
python3 tools/fetch-art.py --what bosses --probe      # 只量缺口，不落盘
python3 tools/fetch-art.py --what bosses              # 转存 + 重建 art.json
node tools/merge-dungeons.js && node tools/build-data.js
python3 tools/audit-assets.py                         # 素材缺口体检报告
```
