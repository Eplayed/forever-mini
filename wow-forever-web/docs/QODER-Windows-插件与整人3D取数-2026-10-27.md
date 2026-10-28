# 发给 Windows Qoder：插件数据与真实穿装人物模型

请只做 Windows 电脑上才能做的取数和验证。客户端在 `C:\GAME\World of Warcraft\_forever_`，本地 CASC 为 `wowf / 1.60.1.70532`。插件实际安装目录请自行确认。不要改客户端安装，不上传客户端或插件原包，不改网页仓库，不发布任何模型。所有实验在独立工具副本与输出目录做；保持 `allowCacheCollection=false`，禁止工具悄悄回退 CDN，不能把远端 70630 字节记成本地 70532。

## 任务一：新版插件是否能作为本站持续数据源

核实际安装的 GearInsight 0.5.6、XR_DungeonGuide 87、DungeonsForever 1.9.10、OpenMap 0.7.5-CN 的版本、真实源文件路径、大小和 SHA-256。只抽取可复核的事实字段，做成可重跑的提取脚本和规范化 CSV/JSON，逐行保留 `插件/版本/源文件/源内 ID/字段/值`。优先覆盖：GI 更新的天赋、专业、营地、成就、配方出处；XR/DF 对本站有用的首领、层号、点位；OpenMap 的副本→层→12 个地图 FDID。对 OpenMap 再交一张 `DF 副本 ID + 层号 + 点位坐标 ↔ OpenMap 层图` 对照表，未对上的留空并说明，不凭 756 个 verified 文件名认定层图或点位正确。GI 的 40 个宠物家族单列，不冒充逐只宠物资料。不得把插件描述文案、自绘图、原始插件文件作为网站可发布素材。

交 `addon-source-manifest.json`、规范化数据、提取脚本、异常/未覆盖清单。若 Windows 上没有本站仓库，**不要声称已经入库**；我们收到包后会在本机逐 ID/字段与 `wow-forever-web/app/data/` 对照、决定采用哪些字段，再跑数据门禁。目标是让这些插件成为今后可重复更新的**候选来源**，而非整包盲目覆盖旧数据。

## 任务二：证明能导出“穿着本站装备”的整个人物 GLB

先解决第三轮实际阻断：2870 装备请求 FDID `151975`（`item/texturecomponents/armuppertexture/plate_a_02silver_sleeve_au_m.blp`）后，本地缺 ekey `a0aa63f17a53fb7921c1adaccf73a015`。在**同一次调用**记录 FDID、路径、ekey、本地 CASC 是否有字节、失败原因；继续枚举该件所需资源的其他缺件，不要只报第一个。查清是安装缺件、索引/工具错误，还是版本不符；不能靠未核 CDN 字节蒙混。

若能在同一 build 凑齐资源，先选两件**确实可选且资源齐全**的胸甲做固定人类男角色 A/B：除胸甲外所有条件相同，交同角度正背截图与两份带材质 GLB，在独立查看器重新打开，证明胸部外观变化。此步通过后，才尝试本站 `bis.json` 中**一套猎人配装的真实物品 ID**，逐槽记录 `item ID → 外观/贴图/geoset/附件`，导出一份完整穿装人物 GLB、预览图和正背证据。诊断物品 2870/250518 不得替代猎人清单中的物品；缺一槽就标未完成，不用相似外观顶替。先完成一套样板，不批量做 38 套。

若仍缺资源或工具不能导出，就交完整缺件清单、对应调用日志和可复现步骤，结果标 `BLOCKED`；人物裸模、一次贴图请求、工具界面截图均不算真实穿装 GLB。

## 打包与报告

在 `C:\GAME\World of Warcraft\ziliao-export\` 新建独立 `run-*` 目录。ZIP 内放 `README.md`、`RESULT.json`、上述数据/脚本/日志/截图/GLB（如有）和逐文件 SHA-256；ZIP 外放 `PACKAGE-*.txt`，写 ZIP 字节数与 SHA-256。报告分别给出插件 `SOURCE_READY / BLOCKED`、模型 `DRESSED_GLB_VERIFIED / BLOCKED`，逐项列已验证、未验证、缺件与实际产物路径。不要写 `DATA_DONE` 或 `WEB_3D_DONE`；本站入库、网页接入与公开分发由 Mac 仓库侧在验包后另做。
