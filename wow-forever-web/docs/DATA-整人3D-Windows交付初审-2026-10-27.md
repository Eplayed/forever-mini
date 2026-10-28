# Windows 整人 3D 探针交付初审（2026-10-27）

本轮角色：wow-data。状态：**已定（两包完整性、本地 wowf 人物加载、1488 的 ItemSparse 缺口、WDC5 copy table 行数纠错）／待实测（同一人物两件胸甲的渲染与 GLB）**。下面第一至三节保留最初无法连接时的记录；第四节复核首包，第五节复核第二包，现行结论以第五节为准。

## Qoder 经站主转述的交付

Windows 路径：`C:/GAME/World of Warcraft/ziliao-export/character-probe-2026-10-27/run-20261027-102152/README.md`。站主转述包内有 `README.md`、`RESULT.json`（12 条文件清单，不含自身）、`item-resolution.csv`（12 行全 `NOT_ATTEMPTED`）、6 张截图、两份完整原始日志和摘要、只读复核输出；Qoder 自报 ZIP 解包后 12/12 的哈希/字节一致且 `testzip` 通过。

Qoder 自报还包括：为避免执行 `installer.exe`，按 `data.pak.json` 用 zlib 提取 207 个文件（0 失败）并直接运行 `wow.export.exe`；NW.js 包未响应远程调试端口，改为 PowerShell+Win32 实际点击与截图，临时的 `chromium-args` 改动已恢复；加载客户端前关闭 `allowCacheCollection`；客户端五个目录在本轮 10:20 后没有新增/修改文件。这些均是**对方报告，本站尚未独立回读原文件或原始日志**。

## 本机已核与不能下的结论

- `192.168.0.105:445` TCP 可达。旧 `share` 账号使用 `mount_smbfs -N -o ro` 两次均返回 `Authentication error`；尝试由 Finder 打开系统共享连接后，未观察到已挂载卷。因此本机**没有读取 Windows 结果包的任何字节**，没有计算 ZIP SHA-256，也没有打开 `README.md`、`RESULT.json`、日志或截图。
- 由转述的 `item-resolution.csv` 12 行全 `NOT_ATTEMPTED`，可以暂定**本轮未进行逐槽物品核验与胸甲 1488→2870 的 A/B 导出**。不能据此判定 Forever 客户端本身不支持整人 GLB，也不能判定 wow.export 已兼容本 build；失败点须看原始 README 和日志。
- ZIP 的 12/12 完整性、工具未上报客户端数据及客户端未改动，现阶段都只记为 **Qoder 自报待核**。不把打包完整性当成 3D 探针通过。

## 取得包后的复核顺序

1. 先验 ZIP 本身的字节数与 SHA-256、`PACKAGE.txt`，安全解压到仓库外；拒绝绝对路径、`..` 和符号链接逃逸。
2. 逐条重算 `RESULT.json.files` 的 12 个字节数与 SHA-256，再看 `RESULT.status`、`README.md` 与 `item-resolution.csv` 是否互相一致。
3. 只读检查两份完整日志的**首个实质失败**及末尾状态，区分安装包启动、客户端识别、CASC/DB2 解码、远程网络依赖、UI 操作阶段；截图用于交叉印证，不以摘要代替原始错误。
4. 根据首个失败给 Windows 侧一条最小修复任务。若 A/B 根本未开始，绝不扩到 38 套或回去盲导 43,329 张贴图。

当前等待：站主在这台 Mac 的 Finder 系统弹窗本地登录共享，或直接附 ZIP 与 ZIP 外 `PACKAGE.txt`；密码不经聊天传递。

## 四、共享恢复后逐项独立回读（同日）

Finder 已把 `//share@192.168.0.105/World%20of%20Warcraft` 挂到 `/Volumes/World of Warcraft`。系统挂载信息没有显示 `read-only` 标志；**本轮操作本身全部是读取** `ziliao-export/character-probe-2026-10-27/`，没有复制模型到本站，也没有对 Windows 客户端或共享执行写命令。

| 核验项 | 本机复算结果 |
| --- | --- |
| ZIP 大小 / SHA-256 | **1,029,110 字节** / `50227edaaf3e21afb48bc4f07a5a51010c998914ecdc5a3b016188e2458b5d90`，与 `PACKAGE.txt` 完全一致 |
| ZIP 成员 | **13 文件**、`ZipFile.testzip()` 无错；成员路径没有绝对路径、`..` 或反斜线逃逸 |
| ZIP 与共享上的展开目录 | 13/13 字节完全一致（ZIP 内统一带 `run-20261027-102152/` 前缀） |
| `RESULT.json.files` | **12/12** 文件存在，字节数与 SHA-256 全一致；按设计不含 `RESULT.json` 自身 |
| 逐槽与导出 | `item-resolution.csv` **12/12 `NOT_ATTEMPTED`**；`export/` 0 文件；`RESULT.status=BLOCKED_CLIENT`，互相一致 |

本机还直接读了共享根 `.build.info`：它**仅有 1 条 active 构建**，`Product=wowf`、`Version=1.60.1.70532`、Build Key `2582289d81e380163c7a13472df4cb81`；`Data/wowf` 确实存在，`_forever_/.build.info` 确实不存在。因此第一次把 `_forever_` 作为安装根会失败，`screenshots/05-forever-path-rejected.png` 的红条与此吻合。

第二次选真正安装根 `C:/GAME/World of Warcraft`，交付的 `logs/tool-runtime.log` 原文在 10:50:56 给出 `Initializing local CASC installation` 后立刻打印空构建列表；`screenshots/07-root-attempt.png` 显示 `Last Opened ... (Unknown)`，未进入人物页。**已核结论：wow.export 0.2.19 在产品选择阶段没有接受这份 `wowf` 安装，胸甲 A/B 没有执行。**

Qoder 在 `README.md` 引用打包工具的过滤式 `this.builds = config.filter((entry) => constants.PRODUCTS.some((e) => e.product === entry.Product));`，并称产品白名单无 `wowf`。这与现场现象高度吻合，但**工具 bundle 源码没有随结果包交付，本机未逐字复核那一行**。另外，`README.md` 所引第一次尝试的 `[10:47:53] ... _forever_/.build.info ENOENT` 行在交付的两份完整日志中未找到；截图和目录结构能证实第一次路径无效，但那条日志引用不能算“包内原始日志已核”。

首会话日志里 WDC5 的解析发生在远端 `wow_classic_era_ptr` 预载，不是本地 `wowf`。它只能证明工具有通用 WDC5 处理能力，**不能证明 Forever 的 DB2、DBD 定义、身体贴图或装备链已可用**。`allowCacheCollection=false`、工具 207 文件解包及客户端五目录零改动目前仍以 Qoder 记录为主；本机可读 `.build.info` 与当前目录，但没有安装前后的独立客户端全量哈希基线，不把这些自报扩写为本站已核。

下一步应在 Windows 的**工具临时副本**做最小产品码适配探针：保留原始 bundle 哈希与精确补丁，只允许识别 `wowf`，安装根始终选 `C:/GAME/World of Warcraft`，绝不能改游戏 `.build.info` 或把 `wowf` 伪装成 Classic/Retail。先看能否进入本地 Characters；若出现 DBD/热更/缺表等新错误，保留日志就停，不继续批量导出。#104 仍只约束公开下发，私下诊断并未发布素材。

## 五、第二包复核：本地人物已通，旧 DB2 行数结论撤回（同日）

Windows 包 `run-20261027-120705.zip` 由当前共享只读回读：**4,204,258 B**，SHA-256 `c7a7928c72d5deb29c5f8974e1e6e6733316adfb4ce82598abb78de160ce2028`，与包外 `PACKAGE-run-20261027-120705.txt` 一致。ZIP 26 个成员、`testzip` 无错、路径无穿越；与同级展开目录 26/26 字节相同；`RESULT.json.files` 的 25 条逐条重算字节数与 SHA-256，**25/25 相符**。这证明交付包内部一致，不等于 3D 导出成功。

实验副本只在 `constants.PRODUCTS` 加 `wowf`，另在 `package.json` 设置独立用户数据目录；精确 diff、原始/实验哈希在包内。日志从 `Loading local CASC build` 的 `Product:'wowf'`、`Version:'1.60.1.70532'` 走到 **1,041,466** 个 journal 条目、**1,250,956** 个 root 条目，再加载本地 `character/human/male/...` 并在截图中出现人物；`ItemSparse` 等 DB2 从本地 CASC 解析。这证明当前工具实验副本已能读取本地 Forever 人物，尚未证明装备渲染或导出。`allowCacheCollection=false` 见包内配置；未取得外部网络侧证据，不能独立证明零上传。客户端目录“12:00 后零改动”是 Qoder 留下的只读检查，没有本机事前哈希基线。

胸甲选择器截图 `19-chest-search-1488.png` 为 **0 items**，对照 `56` 有 15 项、`2870` 有 1 项。本站另外流式查共享中的 `Item.csv` 与 `ItemSparse.csv`：`1488` 在前者、**不在后者**；`2870` 在两者。其他同类缺项 `2278/14593/4438/3341/4464/9456` 也不在 ItemSparse。这足以解释此工具为什么不能选原定胸甲 A=1488。结果包记录 **0 个 GLB、0 张 A/B 截图**；2870 仅在搜索结果里出现，未穿上。`chest_changed` 和导出视觉均为 **NOT_TESTED**。

**撤回“ItemDisplayInfo 被裁到 7,071 行”及基于它的 47.14% 断链判断。**本站直接读上一轮原始 `ItemDisplayInfo.db2` 的 WDC5 分段头与 copy table：7,071 条物理记录另带 **35,472 条复制记录**；其中一个全零加密段的 2 条被工具跳过，故工具报 **42,541 行**，两数的算术关系是 `7,071 + 35,472 - 2 = 42,541`。`ComponentModelFileData` 同理为 `58 + 50,209 = 50,267`，`ComponentTextureFileData` 为 `27 + 14,344 = 14,371`。复制记录用两枚 32 位 ID 指向原记录，不要求再存一遍 11 字节正文，所以“427,139 字节装不下 42,541 行”不是矛盾。旧 `db2csv3.py` 的 `records()` 只枚举物理记录，确实漏了 copy table。

这个错误直接碰到目标物品：`ItemAppearance 63510 → ItemDisplayInfo 3082`，而 **3082 是复制 ID，来源物理行 222**；旧 CSV 找不到 3082 不代表客户端没有。用已读出的明文原始 ID 和复制 ID 重新对 `ItemAppearance.f1` 查键：9,059 行中 26 行 `f1=0` 不作为外键；其余 9,033 行有 **9,032 行可命中（99.99%）**，1 行 `753179` 未命中，可能涉及加密段，暂不解释。旧“47.14%”及从缺行推出来的“本 build 把外观数据裁掉”均失效。既有 **21.4% 独立 M2 格位命中率**仍是旧 CSV 上做的历史计算，不再作为本 build 的覆盖率或方案取舍依据；要在展开 copy table 并复核部位目录后重算。身体贴图/整人外观的覆盖率仍未测出。

第二处失败是 **缺本地纹理后的 CDN 回退崩溃**。包内 `README.md` 摘录 `Local data file ... not cached, falling back to CDN` 和 `ERR_VUE ... (reading 'Product')`，崩溃截图可交叉印证；但这次包内的完整 `tool-runtime-experiment.log` 是后一次 12:35 会话，**不含 12:25 的回退原文**，所以缺件哈希与具体网络请求目前只能按 Qoder 摘录记，不能写成本站从完整原始日志逐行复现。其回退目标自报为远端 `wowf/1.60.1.70630`，不同于本地 70532，不应用远端结果冒充同 build 的 A/B。

**交接 wow-dev / Windows Qoder**：下一探针可把胸甲样本换成同在 ItemSparse 的 `2870` 与 `250518`；旧 IMA 显示两者均为胸槽，分别指向外观 `64064/120468`、IDI `9695/712824`，后一跳的 IDI 两个键也均在 copy table（来源物理行 222/149993）。这只证明键可解析，不证明本地纹理齐全或可见外观一定不同。固定同一人类男性与其他槽位，先逐件记录加载路径、缺件与是否触发远端回退，再决定能否做两次 GLB；任何缺件或跨 build 回退都要单列，不能拼成“纯本地 70532 已通过”。#104 的公开素材下发仍未获批，本轮仅做本地诊断。

## 六、第三包更新（同日）

[第三包逐项复核与下一轮短任务](DATA-整人3D-Windows第三包复核-2026-10-27.md)已落文件。2870 的 Equip 确实触发人物外观刷新，并**请求**胸甲袖子贴图 FDID 151975；紧接着实际 ekey 缺失，E3 禁止 CDN 后按预期停止。`Loading local CASC file` 不代表读取成功，包内也无胸部像素改变的截图证据；250518 未试、GLB 仍为 0。下一步先核 FDID 与实际 ekey 的同调用对应，并单独诊断 250518 的本地可用性，再决定补件或换样本。
