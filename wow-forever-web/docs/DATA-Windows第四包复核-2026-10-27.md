# Windows 第四包复核（2026-10-27）

状态：**插件源包已验；成就字段已入库；胸甲 A/B 已验；猎人整套未做。**本次按站主要求不使用项目角色 skill。只处理本地副本，不向外发布游戏素材。

## 包与来源

本机来源：`/Users/zhangyajun/Documents/project/.scratch/wow/ziliao-export/round4-2026-10-27/run-20261027-205712/`。

| 包 | 实测字节 / SHA-256 | 复核 |
| --- | --- | --- |
| `task1-addons-20261027.zip` | 1,403,887 / `43c8005fa90ef44cdf591dac841eaa10505bb8eeee36ff5fb94eeaec0d0e5243` | `testzip` 无错；26 个成员；清单 25/25 的字节与 SHA-256 全对；与展开目录逐字节一致 |
| `task2-3d-20261027.zip` | 47,913,099 / `b43d317d3c38eb984a060e0b381e44fa5bd5a6b2e554851985abe368f20807c5` | `testzip` 无错；101 个成员；清单 100/100 全对；与展开目录逐字节一致 |

包内日志、脚本和截图证明其**记录的实验**；本机没有重新读取 Windows 客户端归档或重新执行 wow.export，因此“全部取自本地 70532”的判断由 `resource-by-call.csv` 的 187/187 本地索引定位、E3 禁回退、工具日志和 GLB 交叉支撑，不是本机独立重演。

## 插件：能用到什么

- 新版 GI 0.5.6、XR 87、DF 1.9.10、OpenMap 只在 `_cn_beta_`；运行用的 `_forever_` 仍是 GI 0.5.1、XR 75、DF 1.8.20，且没有 OpenMap。OpenMap TOC 的 `v0.7.5-beta` 与分发清单的 `0.7.5-CN` 保持两种原文。新版 GI `Data.lua` 自述取自 70425，专业等模块自述 70532；不能整包标为同一客户端 build。
- 包内事实长表实读 139,439 行；GI 成就 **210** 条、另有 22 条宠物技能和 **18** 个家族（旧“40 家族”撤销）。当前本站成就 211 条里有 **210** 个 ID 与新版 GI 相交；旧版独有 ID `64222` 必须保留。
- GI 配方成品 ID 与本站相交 **1,971** 个；GI 独有 **301** 个。出处列混合 `foreverchanges`、vmangos 和客户端声望，且同 ID 出处有分歧，不能把 3,653 行直接覆盖本站配方。天赋 466 行的 `Data.lua` 版本自述仍是 70425，需逐节点核对后才能覆盖。
- DF/OpenMap 的 35 座对照有 31 座匹配实例、26 座带层图；OpenMap 的 1,224 个瓦片 FDID 在包内索引表均 `in_root=1` 且 `installed_locally=1`。这只证本地资源存在；逐层贴图解码、坐标系和首领点逐层落位尚未验，不能直接上页面。

**本轮已使用的字段**：新增 `tools/import-gi-achievements-csv.py`，从已验的 `gi-achievements.csv` 只取 ID、名称、分类、图标和原始 `lg`，明确丢弃描述；更新 `app/data/upstream/gi-achievements.json` 为 0.5.6，旧 0.5.1 快照单独保留。修复 `merge-achievements.py` 已过期的 `src/data` 路径，按 ID 合并新版 210 条 + 旧版独有 1 条。成品仍为 211 条，5 个名称更新、旧名称在 `nameHistory` 留档，L0 仍 46 条，其余 L1。导入/合并重跑字节一致；这使 GI 0.5.6 的成就字段成为可重复更新的**实际来源**，其余模块仍是候选源，未谎称全量入库。

验证：`node tools/build-data.js` **通过**；`npm run build` **通过**。`site-check.py` 在成就页的条数、分组、禁描述、脚本错误等断言均通过，随后保存成就截图时 Playwright 30 秒超时，故**整套界面门禁未通过**。`audit-translations.py --no-fetch --strict` 因缓存缺页和全站已有未命中报 862 条失败，不能记为通过；本轮改的五个名字仍只按插件 L1 处理。
另以独立本地静态服务拍到 [“深穴征服者”两条搜索结果](screenshots/round4-2026-10-27/achievement-new-title.png)（桌面 1440，`#62035/#64020`，2/199 条），确认新名称在构建产物里实际显示；这张局部截图不替代整套 `site-check.py` 门禁。

## 3D：证明到哪一步

- E4 补丁在工具选中的 ekey 不在本地索引时，改取同 FDID 的已安装变体。日志里 16 次替换；逐调用表 187 行均能指到本地归档，缺件计数 0。第三轮 `a0aa63f1…` 曾经通过 CDN 取到的字节已纠错，单放在 `remote-bytes-do-not-use/`，不能作为本轮本地证据。
- A=2870、B=250518 两个 GLB 的 SHA-256 与清单一致；本机独立解析 glTF：两份均为 13 个 mesh、445 个 node、6 张有效内嵌 PNG，**只有 image 0 不同**。独立查看器截图的正背四格能看到胸甲变化。因此“固定人物只换胸甲 → 导出带材质整人 GLB → 浏览器查看”技术链已成立。
- **外观忠实度仍有一处要核**：E4 搜索同 FDID 的本地变体时未再检查替代变体的 locale/content flags；本地能读、胸甲会变，不自动证明它就是原 zhCN 变体应有的外观。应核 rootType 41 等替代项的 flags，并与游戏画面对照。当前两件诊断胸甲不是猎人套装；猎人 GLB 仍为 0。
- 网站已有 `ModelViewer.vue`，但只登记自产占位。公开下发客户端派生 GLB 仍需项目素材边界决定；现行 `release-package.py` 的扩展名白名单也没有 `.glb`。本轮未把任何游戏 GLB 复制到网站。

## 下一步的精确输入

已从现行 `app/data/bis.json` 导出 [猎人两阵营逐槽物品 ID](DATA-hunter-3D-item-ids-2026-10-27.csv)，共 32 行，附基底 SHA-256 `0333ded451ccb817303786a2d4725ddc0ae54dc04093c44b5f26982ea2857e7f`。交 Windows Qoder 先做 **16 格逐 ID 可选性/外观映射预检**，尤其核之前在工具 `ItemSparse` 缺行的肩甲 `2278`；不能用相似物品替代。再做一套猎人完整人物的正背截图、逐槽资源表和独立查看器 GLB；失败逐槽标明。Mac 侧在拿到已核首套资产后才做网站接入。
可直接转发的下一轮指令见 [Windows 猎人整套续测](QODER-Windows-猎人整套续测-2026-10-27.md)。
