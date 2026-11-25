# 旅途小憩 0.8.0 · 实用化与社交传播升级（2026-11-18）

- 状态：`已定（源码升级、安装同步与 0.8.0 ZIP 打包完成；游戏内实拍截图与网易 DD 客户端操作因沙盒会话隔离阻塞，待人工实拍并提审）`

## 1. 新增能力（承接 0.7.4 组队修复）

1. **小地图悬停监控（[Minimap.lua](D:/project/camp-portrait/CampPortrait/Minimap.lua) & [Rest.lua](D:/project/camp-portrait/CampPortrait/Rest.lua)）**：
   - 新增 `addon.GetCooldownSummary()`，悬停小地图营帐图标直接列出：
     - **睡袋状态/冷却**：就绪（绿）或 `剩余 XX分XX秒`（琥珀，读物品 `211527` 冷却）；
     - **强化休息状态/冷却**：就绪（绿）或 `剩余 XX分XX秒`（读光环 `1229451`）；
     - **双倍经验池**：`+N (XX%)`（按 `GetXPExhaustion() / UnitXPMax("player")` 计算，满级标 `已满级`）。
2. **「喊队友」队伍提示按钮（[Portrait.lua](D:/project/camp-portrait/CampPortrait/Portrait.lua) & [Rest.lua](D:/project/camp-portrait/CampPortrait/Rest.lua)）**：
   - 仅在组队休息（或预览态）显示于海报左下，必须由玩家手动点击触发（10 秒防刷屏节流、战斗中不发），向 `INSTANCE_CHAT` / `RAID` / `PARTY` 发送带剩余秒数的提醒文案，带动同队玩家了解并安装插件。
3. **一键「合影」纯净截图态（[Portrait.lua](D:/project/camp-portrait/CampPortrait/Portrait.lua)）**：
   - 海报左下新增「合影」按钮：点击后隐藏全部控制按钮与倒计时条 **6 秒**（点击卡片可提前恢复），右下角呈现极克制的「旅途小憩 · 营地留影」印章，方便玩家截图分享至公会群或社区。
4. **设置面板配套小程序引导（[Settings.lua](D:/project/camp-portrait/CampPortrait/Settings.lua)）**：
   - 面板调整为 `416×404`，底部加入无商标词引导：`60级团前配装 · 副本顺路清单：微信搜「跑本无限助手」小程序`。

## 2. 验证与打包

- 源码结构与红线检查：4 份 Lua 源码（`Minimap.lua` 14 块、`Portrait.lua` 106 块、`Rest.lua` 157 块、`Settings.lua` 17 块）括号与块语句闭合、无 Lua 5.2+ 语法、零商标词。
- 客户端同步与 ZIP 打包：9 个文件已覆盖至 `C:\GAME\World of Warcraft\_forever_\Interface\AddOns\CampPortrait\`，打包 `D:\project\camp-portrait\dist\CampPortrait-0.8.0.zip`（`63,092 B`），逐文件 SHA-256 与安装目录一致。
- **阻塞（环境桌面会话隔离）**：本轮检测到 `Wow.exe`（PID `9964` / `28132`）与 `netease_dd.exe`（PID `11928`）运行在用户交互桌面 `SessionId=1`，但代理执行环境无桌面截屏/交互权限（`PIL.ImageGrab.grab()` 报错 `OSError: screen grab failed`，`MainWindowHandle=0`），无法代为按键发送 `/reload`、拍游戏内 2 张实拍图或操控 DD 客户端提交表单。
