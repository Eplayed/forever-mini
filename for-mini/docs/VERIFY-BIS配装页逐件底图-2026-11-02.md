# 小程序配装页：3D 整层撤下 → 逐件静态底图（2026-11-02）

本轮角色：wow-dev ｜任务：站主 11-02 两条指令（不要 3D、装备展示全换成样图那样；出处跳转在前一轮已交）
产出：`for-mini/pages/bis/index.{js,wxml,wxss,json}`、`wow-forever-web/tools/{render-bis-posters,oss-release,mini-m01-check,oss-release-test,oss-fake-server}.js/py`、
`for-mini/oss-build/beta/posters/`（76 张，gitignore 层）、`wow-forever-web/tools/oss-release.js` 的 `posterLink`
交接给：站主（真机扫码 + 是否把图发 OSS）｜状态：**本机可做全部做完，两处只能由人回答**（见第六节）

决定原文见 `PROJECT_DECISIONS.md` 2026-11-02 那一节；口径落在根 `AGENTS.md`（2026-10-30 那条下新增 11-02 子条）
与 `for-mini/AGENTS.md`（那一节整段重写）。

---

## 一、文件级：删了什么、换成了什么

**删除（整层，不留"以后可能用得上"的半截链路）**

| 路径 | 原来干什么 |
| --- | --- |
| `for-mini/components/bis-3d/`（4 个文件） | xr-frame 挂模型、相机自适应、状态回抛 |
| `for-mini/services/bis-model.js` | 取模型清单 + 三道闸（客户端侧） |
| `wow-forever-web/tools/mini-bis-model-test.js` | 上面那份契约的 29 条自检（没有被测对象了） |
| `wow-forever-web/tools/export-bis-posters.js` | 生成按「职业\|阵营」打包的底图表 |
| `for-mini/data/bis-posters.js` | 那张表本身——**它就是 11-01 被撤的错源**：键按职业、值按种族渲，法师拿到猎人那身 |

`services/oss-manifest.js` 里随之删掉 `modelsIndexUrl()` / `modelUrl()`（只有那条链用它们）；
图现在走普通素材地址 `assetUrl(batch, 'models/posters/<file>')`，与图标同一条拼法。
**网页配装页一行没动**（仍是 10-28 那两条决定下的真实 3D 预览）。

**新增**：分发层 `bis/index.json` 多一张桥表 `posterLink`（`<setId>|<阵营>` → `models/posters/<带哈希的文件名>`）。

---

## 二、76 张怎么出来的，以及为什么取景不是一次算完

`python3 tools/render-bis-posters.py --per-set`：读 B1 那份模型索引（`oss-build/beta/bis/models/index.json`，
76 条 = 38 套 × 两阵营），每条取它自己那件 GLB，无头 Chrome + three.js 渲 600×800 透明底 PNG，
文件名带这张图自己的 SHA-256 前 12 位。

**踩到的真问题**：第一版跑完全量 74 张过、2 张红——`warlock/horde` 与 `warlock-pvp/horde`
"人顶到画边（上 0.000 下 0.083）"。量中间产物发现这两张实际画出来占 **98.8% 画高**（y 7..796），
而 `Box3.setFromObject` 报的框远小于此：**three.js 的包围盒不认蒙皮后的顶点**（SkinnedMesh 给的是绑定姿势的框）。
也就是说"按包围盒留 18% 余量"这句话对蒙皮件根本不成立，`warlock-alliance` 也只是侥幸过了（占 96.5%，离判红线只差 4 px）。

改法不是把系数调大蒙过去，而是**按渲染回来的像素收敛**：量非透明外接框 → 上下留白不足 6%（或左右不足 4%）
就按 `画面尺寸 ∝ 1/fit` 反推新的 fit 重渲，最多 4 次；收敛后仍不合格才算失败。
结果：**76/76 全出，15 张需要放大**，用到的 fit 是 1.18 / 1.20 / 1.22 / 1.30 / 1.34
（最大 1.34 正是 warlock 部落那两件）。每张仍逐条当场校验：尺寸、非透明占比 0.06–0.85、颜色不能是一整块、留白够。

**接着又踩到第二层**：连着跑两遍全量对账，发现需要放大的那批每次算出的 fit 都不一样（1.29 vs 1.32 这种），
于是**同一张图每次重渲都换内容哈希**——文件名带哈希是设计，但"渲一次就要重构建一次、上一批对象全成孤儿"不是。
原因是收敛值是个连续量，光栅噪声（±1 px）就够把它带走。加了两样：
`FIT_STEP = 0.02` 网格取整，以及**及格线低于目标线的迟滞**（目标留白 6%/4%，及格线 5%/3%）。
再跑两遍：**fit 决策完全稳定**（两遍都是 1.18/1.20/1.22/1.30/1.34，逐张同档）。

但必须写清一件事：**像素本身仍然不逐字节可复现**。两遍全量在 fit 完全相同的前提下仍有 **12/76 张哈希不同**
（都落在没被放大的那批，fit=1.18），合计字节只差 20（16,371,497 vs 16,371,477）。
这是无头 Chrome + SwiftShader 这一层的性质，不是取景逻辑的问题，本轮不再往下追。
**代价与规矩**：`渲染 → 构建 → 发布` 必须是连着的一串，中间重渲就要重构建；
`posterLink` 与 `cmdPosters` 都按清单现算现核，所以"批次指向磁盘上没有的文件"这种状态构建就会拦下来
（m01 也钉了一条"桥表每条指向的那张真在发布目录里"）。文件名带哈希正是为此——重渲永不覆盖已发出去的对象。

合计 **16,371,477 B / 76 张**（约 215 KB 一张），落在 `for-mini/oss-build/beta/posters/`（gitignore 那一层，二进制不进 git）。
清单 `posters.json` 每条带 `fit` 与实际用的那件模型（`sourceModel.pngSha256`），取景规则与张数写在 `rule`/`count` 里。

---

## 三、三道闸从客户端搬到构建时，并且加到五道

`tools/oss-release.js` 配装那一段现在会读 `posters/posters.json`，逐张过五道，**过不了就不写进 `posterLink`**：

1. 图登记的来源件（`sourceModel.setId + faction`）必须在 B1 模型索引里精确命中；
2. 那一件的 `placementVerdict` 必须是 `PASS`（10-28 第八轮就是把两份 MARGINAL 撤下来的）；
3. 图记录的模型 `pngSha256` 必须与索引里同一条一致——证明这张图是从**登记过的那一件**渲的，不是相似的另一件；
4. 文件必须真在 `posters/` 目录里，字节与 SHA-256 与清单一致，且文件名里那 12 位就是它自己的哈希；
5. 索引里的 `dollSnapshot` 必须与当前这一套这一阵营的 doll **逐格**相同（名单后来改过一件，这张图就不再代表这一套）。

**这比原来严，不是松**：原来 1–3 跑在玩家设备上（取不到才提示），现在跑在构建里，
构建输出直接写"逐件底图进桥表 N 张"，被拦下的逐条给原因。本轮实测 **76 张全过、0 张被拦**。

发布侧 `cmdPosters` 也补了同一层核对（发之前回到 B1 索引对来源件与哈希），
并把变量名从 `race` 改成 `key`——它现在管的是逐件，不再是六张种族图。

---

## 四、页面这一层

`pages/bis/index.js`：`showPoster()`（查表 → `assetUrl` → 指上去）、`clearPoster()`（切职业/切套/切阵营/离开先摘）、
`onPosterLoad` / `onPosterError`（都用 `_posterKey` 核"这是不是当前这一套的回调"，迟到的不改状态）。
删掉的是 `loadModel/teardownModel/modelFail/onModelStatus/measureStage/stageAspect` 与 `MODEL_IDLE/MODEL_NONE`。
**页面不拼地址、不猜地址**：桥表里没有这一格就显示"这一格没有可显示的图"＋一句为什么
（没导出 / 位置没核对 / 名单改过三种可能都写在那句里），不拿任何图回退。

`index.wxml`：`<image class="stage-art" src mode="aspectFit">`，竖盒 860rpx 尺寸一条没改；
底下那句说明改成「静态图，不能拖动：…不是游戏里的截图，也不是本站画的；图本身背景透明，看到的是这一栏自己的底色」，
只在真的取到那一格才出现。`index.wxss`：`.stage` 底色改成图实际铺的 `--sunk`（透明底要成立，这一格必须是页面自己的色，
不能是图里带的一块白），`.model` 那层绝对定位包装随组件一起撤。

**本轮我自己写出来的一个 bug**：`showPoster()` 一开始挂在 `render()` 的 `setData` 回调里，
于是"换阵营后同一拍读 `posterSrc`"还是空——m01 新加的那条断言直接抓红
（`{"after":{"fac":"alliance","src":"","state":"none"}}`）。它其实只依赖内存里的索引与 `this.data`，
不该等视图；改成同步调用后同一条转绿。

---

## 五、跑了什么（都是本机实测，不是推断）

| 命令 | 结果 |
| --- | --- |
| `python3 tools/render-bis-posters.py --per-set` | 本机共跑 **4 遍全量**：第一遍 74/76（抓到蒙皮包围盒那个真缺陷），改完三遍都 **76/76 全出**；最后一遍 16,371,477 B，`rc=0` |
| `node tools/export-mini.js` | `rc=0`；主包快照 53.7 KB / 预算 60 KB（90%） |
| `node tools/oss-release.js build --env beta --check-identity` | `rc=0`；`配装：38 套 · 共享物品 830 件 · 逐件底图进桥表 76 张`；重跑同源 **buildId 一致 · 逐文件字节差异 0** |
| `node tools/oss-release.js posters --env beta --dry-run` | 76 张全部通过来源核对，**待传 76 · 冲突 0 · 一字节没写** |
| `node tools/oss-release-test.js` | **243 / 244**（新增 2 条底图反例：来源件没登记、来源件哈希不符，都在传前停住 0 请求） |
| `NODE_PATH=… node tools/mini-m01-check.js` | 最终一轮 **105 / 107**（本轮新增/改写的 11 条逐件图断言全绿；两条红见下） |

**这一轮回归跑了四遍，中间两遍不作数，教训写下来**：
① 第一遍 105/107 是对着**上一批**（重渲之前的 posterLink）跑的；
② 我在回归跑到一半时存盘改了 `pages/bis/index.js` 的一句注释 → 开发者工具 `compileHotReLoad` 把正在跑的会话打断，
那一遍变成 104/123（16 条"链路抖动：截图 …"）；
③ 我用 `cli quit` + `cli auto` 重启后直接再跑，结果截图与导航整片楔死（80/153，`导航后路由没到位` 连锁到专业/宏两段）——
原因是窗口没被真正打开过；`cli open --project …` 先开窗口、再 `cli auto`，最后一遍才回到 105/107。
**给下一个人**：跑 m01 期间不要改 `for-mini/` 里任何文件；工具看着活着但截图全 TMO 时，先 `cli open` 再 `cli auto`。

m01 这一轮新钉/改写的断言共 11 条（下面 7 组，有的组合并了两条；实拍截图 `docs/screenshots/m01-2026-10-21/h1-bis-page.png` = 战士 · PvP · 联盟那一身）：

- `data` 里不再有 `modelSrc` / `stageAspect`（3D 字段没留在页面上）；
- 进页就指上当前 `setId+阵营` 那一张，URL 形如 `…/models/posters/warrior-horde-f80bf7751229.png`；
- 桥表 76 条**每条指向的 PNG 都在发布目录里**、且 38 套 × 2 阵营一条不缺；
- 换阵营 → 阵营翻了、指到的是另一阵营那一张；**切一次只多取一张图，且不再取模型清单**（假 OSS 流水数到 图 1 次 · 清单 0 次）；
- 换一套 → 图与名单一起换成那一套；
- 桥表里没有这一格 → 明说"没有可显示的图"＋原因，16 行名单与 5 项合计一条不少；
- 迟到的 load 回调不改当前状态；`binderror` 时不许留空 `src` 假装还在加载；
- 页面代码里既没有 `<bis-3d>` / `xr-scene` / 相机字段，也没有"查看 3D／退出 3D"这类入口残留。

**两条红的归属**（都不是本轮改出来的，与本轮改动前同一对）：
`断网有缓存：标离线缓存且默认五人本仍在`（读数 `{"src":"","n":0}`——断网后那一屏连来源文字都没报出来，
这条在 11-01 那轮就是红的，本轮没碰离线通道，**留作待查**）；
`切角铭牌真的渲染出来了`（像素探针，10-30 那轮已记为"自己抖"）。
另外本轮顺手修了一条**断言写死数字**的红：`详情页：新本首领没有头像时走自绘回落` 原来钉"恰好 4 个首领"，
而 `hall-of-thanes` 在 11-01 那批数据里已经是 5 个——数据对、断言错，改成从 `oss-preview/dungeons.json` 读条数后转绿。

`oss-release-test` 那一条红是 `真 PoE 路径仍被标成跨项目`：它要求凭证文件的**路径里含 `p2-database`**，
而 11-01 站主让我把 `.oss-env` 直接拷进了本仓库根（gitignore 内），路径判定自然不含那个目录名——
**这条只在 Mac 的目录布局下成立**，属两台机器的既有差异，不是本轮引入。

---

## 六、没验到的、没做的（不许被上面那些绿盖过去）

1. **真机一次没跑**。这台 Windows 的模拟器只证明"地址指对、切换真的换、取不到会明说"；
   `<image>` 在 iOS/Android 微信上的解码与缓存没验过。要站主扫码看。
2. **76 张图没发 OSS**。只跑了 `--dry-run`。线上 `wow/beta/v1/assets/models/posters/` 目前仍是
   10-30 那 6 张**按种族**的旧图，`assets/models/real/` 那 106 MB GLB 也还挂着——
   撤旧对象与发新图都是写线上，等站主点头再做（发：`node tools/oss-release.js posters --env beta`）。
   旧 6 张现在没有任何引用，删不删由站主定，我不擅自动线上对象。
3. **逐套人眼位置抽查（76 套）仍挂着**。五道闸保证"这张图出自位置核对 PASS 的那一件、且名单逐格没改过"，
   **不保证**"这一身看着对"——那是 10-28 第八轮那种实拍复核，本轮没做。
4. **"哪个首领"这一层没做**（站主当日只选了 1+3）。三源并集对 BiS 名单的首领归属覆盖率只到 26%，
   DF 那 36 座的 `bosses` 全空；现在跳过去落在副本详情页并高亮这一件。
5. **网页配装页那三句（口径句 / 来源与核对日 / L1 留档）没撤**，也不该撤——11-01 那条只作用于小程序这一页。
6. `bis/index` 预算 24 KB → 32 KB 是**我按实测 28,632 B 抬的**，理由与"下次该往哪走"写在 `oss-release.js` 的注释里；
   这条属于会改变构建卡口的决定，站主若不同意，方向应是"两张桥表单独分一片"，不是回退到没图。

---

## 七、下一步

- 站主：扫码看这一屏（换职业 / 换套 / 换阵营 / 断网那一屏），并点头是否发这 76 张与是否撤线上那 6 张旧图。
- wow-data：首领归属那一层要往上抬，得先有能落到首领的掉落来源（DF 的 `bosses` 是空的）。
- wow-dev：`断网有缓存` 那条红值得单开一轮查（现象是断网后 `sourceText` 空、列表 0，不是"标成离线缓存"）。


---

## 补记（同日 17:50 之后）：这批数据已经发上线了

站主选"现在就传 beta"。执行与回读：

```
WOW_ALLOW_CROSS_CREDS=1 node tools/oss-release.js upload --env beta
  批次文件：传 167 · 内容未变跳过 0 · 失败 0 · 不可变冲突 0 / 共 167
  指针 → wow/beta/v1/manifest.json · 批次 d3e222b74dc1 · 回读字节一致
  开关 → wow/beta/v1/flags.json · 2.3 KB · 回读 ETag 一致
```
**回滚目标：`node tools/oss-release.js rollback --env beta --to d25932f1c7a3`**（上一批文件仍在 `builds/` 里）。

线上侧独立回读（不是看本地）：指针 `d3e222b74dc1`、数据核对日 **2026-11-02**、
`bis/index.json` 的 `title=BIS配装`、`posterLink=76`、`dropLink=114`；
`warrior|alliance` 指向 `models/posters/warrior-alliance-10f4db97c9c8.png`，公网取回 **HTTP 200 / image/png / 211,576 B**。

**真机路径复现**（清 storage → 走线上 OSS，不经过本地假 OSS）：
`posterSrc` 是线上真实地址、**`posterState: "ok"`**（`<image>` 的 `bindload` 真的回来了）、
`posterLinkCount: 76`、`dropLinkCount: 114`、`batch: d3e222b74dc1`。
**顺带消掉一条挂了一天的疑虑**：这些对象带 `Content-Disposition: attachment` + `x-oss-force-download: true`，
微信的 `<image>` 照样解码成功——与现用的 `assets/icons/*` 同一档，不构成加载障碍。

**为什么站主那张真机图当时是空的**（值得记，别再猜）：那张图里顶部导航写「BIS配装」（来自**代码包**，新的），
卡片大标题写「30 级配装名单」（来自**数据批次**，10-27 那批）——**两个标题不同步就是"代码新、数据旧"的指纹**。
以后判断"到底哪一侧旧"，先看这两个标题对不对得上，比看任何日志都快。

**仍未做的**：iOS/Android 真机（上面是 Windows 开发者工具走线上域名，不是手机）；
逐套人眼位置抽查；`posters` 那 6 张按种族的旧图与 106 MB GLB 还挂在线上没人引用，撤不撤等站主定。
