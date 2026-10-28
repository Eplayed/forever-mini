# Windows Qoder 续测任务书：只放通 `wowf`，定位下一阻断（2026-10-27）

状态：**待 Windows 实测**。此任务书承接 [首包独立复核](DATA-整人3D-Windows交付初审-2026-10-27.md)；根规则 #104 的公开模型下发仍未决，本轮只在 Windows 本地研究。

## 可直接交给 Qoder 的提示词

你上一轮交的 `run-20261027-102152.zip` 已在 Mac 侧独立核：ZIP SHA-256、13 个成员、12/12 文件哈希均匹配；`Product=wowf`、build `1.60.1.70532` 也从真实 `.build.info` 复核到。wow.export 0.2.19 在安装根只给空构建列表，12 槽全 `NOT_ATTEMPTED`。这轮只查**产品码放通后遇到的下一个真实阻断**，不要直接做 38 套。

1. 输入客户端是 `C:\GAME\World of Warcraft\`（这里有 `.build.info` 和 `Data\wowf`）；`_forever_` 是可执行子目录，**不能**作为 CASC 安装根。客户端及 `.build.info`、`.product.db`、`Data\` 一律不修改。
2. 在 `C:\GAME\_wowf-export-work\` 里复制一份上一轮解出的 wow.export 0.2.19 程序作为**实验副本**。先记原始 `app/src/app.js` 和 `app/package.json` 的 SHA-256；之后所有改动只在实验副本。不要改原始工具、安装器或客户端。
3. 在实验副本中定位构建选择的产品过滤逻辑及 `constants.PRODUCTS`。把相关源码片段、行号、原始 SHA-256 和**最小精确 diff**存进输出包。只允许本地 `.build.info` 中 `Product=wowf` 的条目通过选择；**不要**把客户端产品码改成 `wow_classic_era_ptr`、`wow` 等，也不要用对应的 CDN 模型冒充 Forever。若只放通筛选还需产品显示元数据，逐处记录并只加本地 `wowf` 对应项；不改模型、DB2 或渲染逻辑。
4. 继续保持 `allowCacheCollection=false`。用实验副本打开 `C:\GAME\World of Warcraft`，截图工具显示的 Product、build、source type。必须是本地 `wowf` / `1.60.1.70532`；若跳到在线 Classic/Retail，立即停手并标 `WRONG_SOURCE`。
5. 若进入下一阶段，记录**第一个实质错误**的完整原始日志和界面截图，并停手。尤其区分 CASC/TVFS、DBD 版本、zhCN、角色基础模型、ItemAppearance/ItemDisplayInfo 的缺表或缺行。不要因看到 WDC5 解析器能处理远端 Classic，就宣称 Forever 的表已成功解析。
6. 只有在真正进入本地 Forever 的 Characters 且能显示同一个人类男性战士时，才额外试**胸甲两件**：A=1488，B=2870（2870 不可用才用 250518）。先只穿胸，保持角色与相机不变，观察身体贴图是否改变；如可导出，再各出一份 GLB 和同角度正背面图。若胸甲任一件找不到或无外观，记录逐跳缺口并停，不用近似装备凑数。
7. 结果放 `C:\GAME\World of Warcraft\ziliao-export\character-probe-2026-10-27\run-<新时间>\`。至少交 `README.md`、`RESULT.json`、原始日志、关键截图、原始与实验工具 SHA-256、精确 diff、输出文件逐项字节/SHA-256。若有 GLB，再交 GLB 与截图；没有就明确 0 个。按上轮方式压 ZIP，在 ZIP 外同级写 `PACKAGE.txt` 的大小与 SHA-256。不要打包整个工具或客户端，也不要公开上传任何游戏模型。

只需汇报三句：**本地 wowf/70532 是否成功出现在可选构建并进入 Characters；第一个新阻断是什么（给日志原文）；胸甲 1488/2870 是否真的改变整人外观**。工具补丁成功只说明实验副本能越过选择阶段，不等于官方原版支持 Forever，也不等于装备链已通。
