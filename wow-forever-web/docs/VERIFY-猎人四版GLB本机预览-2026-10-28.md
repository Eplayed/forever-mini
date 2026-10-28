# 猎人四版 GLB：Mac 本机网页预览

## 运行方式

在仓库根执行 `python3 wow-forever-web/tools/preview-hunter-glb.py`，打开 <http://127.0.0.1:8892/>。服务只绑定 `127.0.0.1`，从 Mac 已挂载的 Windows 只读共享实时读取第七包四份 GLB。页面可切换阵营与远程/近战、按按钮看正背面、拖动旋转和滚轮缩放。模型字节没有复制到 `app/img/`、`app/public/` 或发布包；线上配装页没改。

数据源：`/private/tmp/wow-ro/ziliao-export/round7-2026-10-28/run-20261028-125743/glb/`。包完整性与 GLB 结构见 `DATA-3D模型资产可用性-2026-10-28.md`，本轮只验证浏览器可见画面。

## 实测

2026-10-28，Mac Chrome，1920×882。等待页面状态显示“已绘制”后截图，未用加载中的旧模型冒充切换成功。

| 版本 | 浏览器状态 | 正背与武器 | 外观验收 |
| --- | --- | --- | --- |
| 联盟远程 | 已绘制，16 网格 | [正面](screenshots/3d-local-2026-10-28/alliance-ranged-front.jpg) / [背面](screenshots/3d-local-2026-10-28/alliance-ranged-back.jpg)，枪可见 | **未通过**：帽子在头后，正面露出头顶；需同角度工具内对照与导出修复 |
| 联盟近战 | 已绘制，16 网格 | [正面](screenshots/3d-local-2026-10-28/alliance-melee-front.jpg) / [背面](screenshots/3d-local-2026-10-28/alliance-melee-back.jpg)，双手武器可见 | **未通过**：同一帽子错位 |
| 部落远程 | 已绘制，18 网格 | [正面](screenshots/3d-local-2026-10-28/horde-ranged-front.jpg) / [背面](screenshots/3d-local-2026-10-28/horde-ranged-back.jpg)，枪可见 | **未通过**：正面几乎看不到兽人头脸；背面帽子贴在肩上 |
| 部落近战 | 已绘制，18 网格 | [正面](screenshots/3d-local-2026-10-28/horde-melee-front.jpg) / [背面](screenshots/3d-local-2026-10-28/horde-melee-back.jpg)，双手武器可见 | **未通过**：同一头部/帽子错位 |

[部落近战拖动后的侧视](screenshots/3d-local-2026-10-28/horde-melee-rotated.jpg)证明 OrbitControls 实际能旋转；侧面也显示头部位置异常。四版旧包空白截图的原因是过早拍摄，不是 GLB 无法在浏览器渲染。此处的“已绘制”只证明渲染完成，不代表装备姿态正确。

## 结论与交接

**已定**：四版均可作为本机可旋转网页预览，联盟/部落与远程/近战切换真实有效。远程和近战是两份静态造型，单份模型只显示一把武器。

**阻塞（外观）**：第七包 E9 GLB 的头部与头盔贴合仍未过关，部落尤为明显；这四份不能接入线上真实模型展示。Windows Qoder 下一步应针对同一动画帧的身体头部与头盔导出修复，交人类和兽人正背及侧面，与工具内预览同角度对照。其后再优化目前约 10–14 MB/份的体积并处理公开分发边界。

**没验到的**：未核游戏内同角度外观；未测低端设备性能；未做线上站点回归，因为站点代码及公开资产完全未改。素材字节没有分发给第三方。
