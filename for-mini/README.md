# 无限资料小程序（for-mini）

《魔兽世界：无限》中文资料线的小程序端。与同仓库 `wow-forever-web/` 静态站共用一份数据基底，个人主体，纯工具属性：查译名、看完整度，数据每条可溯源。

**当前是底子**：数据层 + 中英速查 + 首页完整度已能跑；天赋计算器等四个模块只有入口，未实现。首次接手先读 `AGENTS.md`。

## 目录

| 位置 | 作用 |
| --- | --- |
| `app.js` / `app.json` / `app.wxss` | 小程序入口、页面与 tab 注册、设计令牌 |
| `pages/home/` | 首页：模块清单、L0–L3 完整度、还没确认的缺口 |
| `pages/glossary/` | 中英速查：搜索、分类、收藏、复制、来源展开 |
| `services/forever-data.js` | 唯一数据入口：OSS → storage 缓存 → 打包快照三级回退 |
| `data/forever-*-snapshot.js` | 打包快照，由 `wow-forever-web/tools/export-mini.js` 生成，勿手改 |
| `oss-preview/` | 将要上传到 OSS `wow/release/v1/` 的全量 JSON，勿手改，不进主包 |
| `docs/DATA.md` | 数据契约与上传流程 |

## 跑起来

1. 微信开发者工具「导入项目」选本目录，appid 用测试号（`project.config.json` 里已是 `touristappid`）。
2. 改数据不在这里改：编辑 `wow-forever-web/src/data/*.json`，然后

```bash
cd wow-forever-web
node tools/build-data.js    # 校验 + 覆盖率，非 0 即不通过
node tools/export-mini.js   # 重新生成 oss-preview/ 与 data/*-snapshot.js
```

## 已知阻塞

- 独立 appid 未注册，名称未定（D1），备案尚未提交 —— 备案 1–20 工作日是关键路径。
- 有 appid 后必须把 OSS 域名加进 request 合法域名白名单，否则真机只能读到打包快照。
