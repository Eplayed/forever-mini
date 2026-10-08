# 数据契约与上传流程（小程序侧）

来源：`wow-forever-web/src/data/`（站点基底）。小程序**不自己维护数据**，只消费导出产物，保证与网页端同源。

## 一、路径与命名空间

| 用途 | 位置 |
| --- | --- |
| OSS 根 | `https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com/wow/release/v1/` |
| 环境切换 | `wow/{env}/v1/`，`env` 目前只有 `release`；预发用 `wow/beta/v1/` |
| 缓存前缀 | storage key `wow_forever_v1_{文件名}` |
| 收藏 key | `wow_fav_terms_v1` |
| 打包快照 | `data/forever-glossary-snapshot.js`、`data/forever-meta-snapshot.js` |

与 POE 线（`poe2-*` 前缀）、AI 线（`ai-box/` 前缀）完全隔离，不共用文件、不共用缓存 key。

## 二、JSON 结构

`glossary.json`（与站点 `src/data/glossary.json` 完全一致）：

```jsonc
{
  "meta": { "generatedAt": "YYYY-MM-DD", "note": "采集口径", "pending": ["缺口…"], "coverage": { "L0": 0, "total": 0 } },
  "items": [{
    "id": "hunter-talent-1",
    "cn": "瞄准射击",
    "en": null,                       // null 表示无权威英文名，界面显示「英文名待补」，禁止机翻
    "kind": "talent|item|racial|skill|dungeon|boss|system|zone",
    "classId": "hunter",              // 可为 null（种族技能）
    "spec": null,
    "level": "L0|L1|L2|L3",
    "provenance": [{ "type": "official_cn", "url": "https://…", "note": "…", "checkedAt": "YYYY-MM-DD" }]
  }]
}
```

`meta.json`（小程序专用精简版，由导出脚本从站点 `meta.json` + 实时统计生成）：

```jsonc
{
  "site": "无限中文资料站",
  "disclaimer": "非官方粉丝资料站，与暴雪娱乐及网易无关。",
  "dataBaseline": { "build": "forever-beta 1.60.x（未逐点核对）", "checkedAt": "YYYY-MM-DD" },
  "launch": "2026-11-05",
  "checkedAt": "YYYY-MM-DD",
  "source": "wow-forever-web/src/data",
  "coverage": { "L0": 0, "L1": 0, "L2": 0, "L3": 0, "total": 0 },
  "counts": { "terms": 0, "dungeons": 0, "talentNodes": 0, "talentNameVerified": 0 },
  "openQuestions": ["…"],             // 最多 6 条，首页原样列出
  "rules": ["…"]
}
```

`dungeons.json` 与站点同结构，本期未接入界面，先随导出脚本一起产出，避免以后补页面时再改流程。

## 三、三级回退语义

`services/forever-data.js` 的 `loadFile()` 返回 `{ data, source }`：

| `source` | 含义 | 界面义务 |
| --- | --- | --- |
| `live` | OSS 拉到最新 | 正常显示 |
| `cache` | 断网，用上次缓存 | 顶部提示「离线缓存」 |
| `snapshot` | 缓存也没有，用打进主包的快照 | 顶部提示「打包快照」+ 显示基准日期 |

任何一级失败都不许白屏，也不许把降级数据当实时数据显示。

## 四、更新一次数据的完整动作

```bash
cd wow-forever-web
# 1. 改 src/data/*.json（译名、来源、完整度）
node tools/build-data.js     # 校验红线 + 覆盖率，非 0 退出即停
node tools/export-mini.js    # 生成 oss-preview/ 与 for-mini/data/*-snapshot.js（默认 60 条快照）
node tools/export-mini.js 80 # 需要更多离线词条时，超 60 KB 预算会直接失败
# 2. 把 oss-preview/ 三个文件上传到 OSS 的 wow/release/v1/ 下（覆盖同名）
# 3. 词条数或结构变化时，同步 git 提交，快照文件必须与 oss-preview 同一批
```

## 五、新增模块要做的事

1. 在导出脚本里加对应文件（如 `talents/{class}.json`），按职业分片，别把 473 个节点全塞进一个文件。
2. `services/forever-data.js` 加一个 `loadXxx()`，沿用 `loadFile()`，不新写请求逻辑。
3. 页面只消费 `{ data, source }`，徽标沿用 `.badge-L0/L1/L2/L3`。
4. 数据里缺字段一律显示「待实测」；`level=L0` 必须带官方来源，否则 `build-data.js` 会让构建失败。
