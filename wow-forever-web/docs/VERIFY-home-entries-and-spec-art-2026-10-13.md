# 验证记录 · 首页入口化与专精原画（2026-10-13）

本轮角色：wow-dev ｜任务：用户实拍四条——① 首页入口重复，撤六个文字入口卡、留带图的图标轨；
② 角色线 / 世界线 / 工具线与「自经典旧世以来的改动」那些读数像数据变动明细，改成入口；
③ 「最常用的两个」标题撤掉，两张卡本身可点跳转；④ **卡片背景要的是图片不是图标**，
参考 `wowforever.wclbox.com` 与 `jjwow.cn`，天赋页每职业每系都要有一张背景图 ｜
产出：`tools/fetch-art.py`、`src/img/art/{specs,classbanners,panels,scenes,texture}/`、`src/data/art.json`、
`src/js/app.js`、`src/css/app.css`、`app/src/**`、`tools/site-check.py`、`docs/UI.md` 3.36 ｜交接给：用户验收

## 一、跑了什么，看到什么

| 命令 | 结果 |
| --- | --- |
| `python3 tools/fetch-art.py --what specbg` | 专精背景 27/27 拼成（第一轮 22、修掉两处误判后 27） |
| `python3 tools/fetch-art.py --what panels` | 板块配图 18 张（职业横幅 9 + 板块 4 + 场景 4 + 纹理 1），1 张带哈希的在首页 HTML 里没找到，跳过 |
| `python3 tools/fetch-art.py --index-only` | `art.json` 重算：专精 27 / 职业横幅 9 / 板块 4 / 场景 4 / 纹理 1 |
| `node tools/build-data.js` | 校验通过 |
| `python3 tools/app-parity.py --strict` | **全部组合无差异**（home / world 四个面板 / classes） |
| `npx vitest run` | **69 / 69** |
| `python3 tools/site-check.py --app` | **556 / 556 全绿**（截图在 `docs/screenshots/check-2026-10-13/`） |

## 二、素材是怎么来的（第 ④ 条）

两个参考站的天赋页 DOM 里，每系背景是**四张角图**：`tianfu-beijing/<Class><Tree>-{TopLeft,TopRight,BottomLeft,BottomRight}.webp`
（256×256 / 64×256 / 256×128 / 64×128，正好拼成 320×384）。`fetch-art.py` 下四角 → PIL 拼一张整图 →
落 `src/img/art/specs/<职业>-<第几系>.webp`，`manifest.json` 里每条记四张角图的原始 URL 与抓取日期。

三个坑与怎么处理的：

1. **圣骑士 12 张在 wclbox 上是坏的**（他们自己页面 `naturalWidth=0`，直接请求 404）→ 每台树配两条源，
   第二条走 jjwow 的驼峰键名（`PaladinHoly-TopLeft.PNG`）。
2. **右下角只有 334 字节**，我原来按"体积 < 400 就当没取到"判，把两张好图误判成缺图 → 改成只验文件头
   （`RIFF…WEBP` 或 PNG 签名）。
3. **PNG 签名比错长度**：`blob[:8] == b"\x89PNG"` 永远不成立（签名 8 字节、字面量 4 字节）→ 改成 `blob[:4]`。

系名映射写在 `SPEC_TREES`，下载前逐条回对 `talents/*.json` 的 `nameCn`，对不上直接退出——
无限服改过系名（术士三系的键是 `Curses / Summoning / Destruction`，萨满第一系是 `ElementalCombat`），
按位置猜会悄悄错到别的系上。

## 三、页面改了什么

- **首页**：六个文字入口卡删除；图标轨保留；板块卡变两组各 6 张带原画的入口卡；
  「自经典旧世以来的改动」四格与"全部 965 vs 四格之和 751"的对照行搬到动态页 `#k1`（放在它描述的那张表头上），
  首页只留一张大入口卡；排行 / 溯源 / 系统规则 / 这一版改了什么收成一行文字小入口。
  小入口那行的标签写"更多入口"——原来想写"站方口径"，`口径` 在自家禁词表里，会被第 18 节打死。
- **两张主推卡整卡可点**：`data-go` + `bindGo()`（旧站）/ `goCard()`（新站），
  点在卡里的链接、按钮、天赋格子、职业条上时不抢它们的去向；`tabindex="0"` + Enter/Space 可达。
  没用 `<a>` 套 `<a>`（HTML 不允许）。天赋预览卡的背景从 128 的职业图标换成"当前这一系"的原画。
- **天赋页**：三棵柱各垫一张这一系的原画（`.tbg` 在 z-index 0，格子抬到 1，依赖连线夹在中间），
  底部用 inset 阴影压暗，标题与"已投 N 点"不吃素材亮度。
- **职业页**：页首横幅用 `classBanners/<职业>`（614×345 真原画），三系卡各带 `.sbg` 专精原画。
- 取不到图的卡一律留纯色：`artOf()` / `specArt()` 找不到就返回空串，不拿别的图凑。

## 四、断言跟着改了什么

- 首页那组按新结构重写：13 张入口卡都带读数、两组各 6 张、15 层背景、首页不再有 `.four`。
- 改动四格与对照行的三条断言搬到 `#k1`（含"四格之和等于上游自报 changed"，那个数仍从 `changes.json` 现读，不写死）。
- 新站冒烟"模块卡 9 张"改成 13 张。
- 全跑一次 556 条（比上一轮多 1 条，因为把首页背景层那条拆成了"入口卡 13 张都带图"）。

## 五、没验到的 / 要人看的

1. **27 张图我只人眼看了 2 张**（warrior-0 岩浆巨剑、paladin-2 闪电洞穴）。
   键名与系名是逐条回对过的，但"这张画画的是不是那一系"没法机器验——源站文件名本身就是唯一线索。
   要挑刺的话，在浏览器里翻 9 个职业 × 3 系看一遍最快。
2. **像素基线没重冻**：`tools/visual-check.py` 仍冻在 `e2bf063`，这一轮改了首页结构与背景，
   指纹必然变。等你看过实拍再决定要不要 `--make`。
3. 移动端我只看了 375 的整页截图（入口卡单列、图在上文字在下），没在真机上划过。
4. **图标轨与入口卡现在仍有语义重叠**（同一去处两个入口）——这是你要的"留图标轨 + 卡片入口"，
   但如果觉得还是重复，下一步可以把图标轨收成一行小的。
5. 小程序侧一行代码没动。

## 六、怎么验收

```bash
cd wow-forever-web
bash tools/serve.sh            # 旧站 :8817、新站 :8821
```
看四页：`index.html`（入口化后的首页）、`talent.html?c=hunter`（三棵柱各一张原画）、
`classes.html?c=warrior`（页首横幅 + 三系卡背景）、`updates.html#k1`（四格与对照行搬到这里了）。
`python3 tools/site-check.py --app` 应报 556 / 556。
