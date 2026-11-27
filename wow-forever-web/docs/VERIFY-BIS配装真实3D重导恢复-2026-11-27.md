# 验证记录 · BIS配装页 76 套真实 3D 模型重导与恢复（2026-11-27）

## 1. 故障根因

1. **线上下架真实模型回落占位**：2026-11-03（提交 `5ebe28a`）因体积清理，原 76 份真实 3D 模型被暂存至 `wow-forever-web/img-models-parked/real/`，`app/data/art.json` 的 `bisRealModels` 登记被移除；网页端 `BisPage.vue` 在无匹配真实模型时自动退回自产方块占位模型（`placeholder.glb`）。
2. **旧暂存模型不可直接复用**：2026-11-23 全量重抓 `app/data/bis.json` 后，38 套 × 2 阵营共 76 份 30 级 BIS 套装的物品清单全部发生变动（`exact_doll=0 / visual_diff=76`）。按根 `AGENTS.md`（2026-10-28 续定）红线，必须按本站当前实际物品 ID 从本机 Forever 1.60.1.70532 客户端逐套重新导出、核位置、带源/成品哈希与 `dollSnapshot` 登记，不得以旧模型冒充。

## 2. 本轮重导工具修复（`app-e10`）

重导前在 2 份样本实测中拦截并修复了两项导出缺陷：

1. **绑定姿态骨骼矩阵污染（头盔下移 + 武器双重位移）**：`wow.export` 0.2.19 的 `M2RendererGL.stopAnimation()` 切到 `No Animation` 时仍按动画 0（Stand 首帧）刷新了一次 `bone_matrices`，导致身体网格导出 bind pose，而挂点装备叠乘了 Stand 首帧的平移与缩放（兽人头盔下沉约 0.30 m、武器悬空约 2× 手部坐标）。已修补 `stopAnimation()` 统一重置 `bone_matrices` 为单位阵，并在 `getAttachmentTransform()` 的 `no_anim` 分支直取 `att_mat`（与 `getBakedGeometry()` 严格一致）。
2. **E11 披风贴图漏注入 GLB 分支**：原补丁仅注入 `OBJ/STL` 分支，已补齐至 `GLTF/GLB` 导出分支；同时永久禁用自动更新（防止 `0.2.19 → 0.2.21` 覆写补丁）。

## 3. 全量重导与轻量化结果

- 客户端：`World of Warcraft: Forever` 本机 CASC（`1.60.1.70532`），`allowCacheCollection=false`，姿态 `No Animation`，按 `2026-11-23` `app/data/bis.json` 实际物品 ID 逐套导出。
- 导出数量：**76 / 76**（38 套 × 联盟/部落，覆盖人类/兽人/亡灵/暗夜精灵/牛头人/矮人 6 种族），失败 **0**。
- 76 份报告全量审计：`total=76`、`non_identity_helmet=0`（全部挂点旋转基底严格为单位阵 `[[1,0,0],[0,1,0],[0,0,1]]`）、`no_cloak=0`（76/76 披风均已写入背部物品真实 cape 贴图）。
- 轻量化（`tools/optimize-bis-glb.py --webp --body-width 1024 --quality 90`）：总量 **`873.0 MB → 33.70 MB`**，76 份经 `verify_triangle_stream` 逐三角面属性字节比对全部一致；已登记至 `app/img/models/real/manifest.json` 与 `app/data/art.json`（`bisRealModels`，76 条全部 `placementVerdict: "PASS"`）。
- `.gitignore` 规则保持不变：`app/img/models/real/*.glb` 不入公开 Git 仓库，随 `fc-deploy.zip` 打包发布至阿里云 FC 3.0。

## 4. 门禁与实拍验证

| 检查项 | 结果 | 关键指标 / 证据 |
| --- | --- | --- |
| `node wow-forever-web/tools/build-data.js` | **PASS** | 0 错，`bisRealModels` 76/76 `dollSnapshot` 逐格与 `bis.json` 一致 |
| `npm --prefix wow-forever-web/app run build` | **PASS** | 同步 80 文件至 `app/public/`，`vite build` 6.09 s |
| `npm --prefix wow-forever-web/app test` | **PASS** | **198 / 198** 全绿 |
| `python -u wow-forever-web/tools/site-check.py --only css_tokens,bis` | **PASS** | **50 / 50** 全绿；点「旋转 3D 模型」按需加载 Three.js + GLB（首屏 0 请求），开 3D 与退回图片差异 93.3%，两阵营切换差异 24.8% |
| 目视实拍核验 | **PASS** | `docs/screenshots/check-2026-11-27/app-bis-3d.png`：兽人战士牛角头盔正戴头顶、双肩贴合、旋风之斧稳握右手、盔甲纹理清晰 |
| `release-package.py` + `pkg-verify.py` | **PASS** | 4,455 文件 / 76.7 MB，**18 / 18** 验包通过 |
| `build-fc-package.py` | **PASS** | `release/fc-deploy.zip`（51.8 MB，4,455 文件，含全部 76 个 `.glb`） |
| 阿里云 FC 3.0 线上部署与公网实拍 | 待本轮收口 | 提交推送后重打无 `-dirty` FC 包上传 `paoben-web`，实拍验证 `https://www.paoben.top/#/bis` |
