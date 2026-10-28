# 项目按需读取索引

自动生成。先定位再读原件；本索引不是授权、来源或验收结果。

## 用法

```sh
python3 wow-forever-web/tools/project-index.py --topic launch
python3 wow-forever-web/tools/project-index.py --find merge
python3 wow-forever-web/tools/project-index.py --check
```

普通调用自动刷新；--check只检查。无后台监听，不定时唤醒AI。HEAD或被索引文件size/mtime变化即失效；大数据/图片不在快照中，需要时直接读目标记录。

## 读取顺序

1. 根规则＋目标子项目规则；ROLES只读末尾相关交接。
2. 运行对应topic，只读列出的入口和当前任务指定交付。
3. 用git diff --stat和限定文件diff确定变更；大JSON按ID提取，日志只看失败与末尾。
4. 只有入口不足才扩大rg检索。不要把全部历史VERIFY、数据、截图清单灌入上下文。

## 任务入口

### rules · 规则与交接

- `AGENTS.md`
- `ROLES.md`
- `wow-forever-web/AGENTS.md`
- `wow-forever-web/docs/README.md`

### launch · 部署与线上验收

- `wow-forever-web/tools/release-package.py`
- `wow-forever-web/tools/deploy-gh-pages.py`
- `wow-forever-web/tools/pkg-verify.py`
- `wow-forever-web/tools/app-assets.py`
- `wow-forever-web/app/vite.config.js`
- `wow-forever-web/docs/VERIFY-pages-and-index-2026-10-21.md`

### spells · 技能取值与分歧

- `wow-forever-web/tools/merge-spells.py`
- `wow-forever-web/tools/extract-plugin-tables.py`
- `wow-forever-web/app/src/pages/SkillsPage.vue`
- `wow-forever-web/app/src/pages/ProvenancePage.vue`

### items · 物品与配装

- `wow-forever-web/tools/merge-items-detail.py`
- `wow-forever-web/tools/extract-addon-items-detail.py`
- `wow-forever-web/app/src/lib/item-stats.js`
- `wow-forever-web/app/src/pages/BisPage.vue`

### maps · 地图与素材

- `wow-forever-web/tools/extract-df-geo.py`
- `wow-forever-web/tools/merge-dungeon-geo.py`
- `wow-forever-web/tools/fetch-art.py`
- `wow-forever-web/app/src/components/PinMap.vue`
- `wow-forever-web/docs/VERIFY-prelaunch-independent-2026-10-20.md`

### updates · 动态筛选

- `wow-forever-web/app/src/pages/UpdatesPage.vue`
- `wow-forever-web/app/tests/updates-filter.spec.js`

### business · 换轨与内容主线

- `wow-forever-web/docs/OPS-换轨方向复核-2026-10-20.md`
- `wow-forever-web/docs/OPS-三渠道内容优化-2026-10-19.md`

### tests · 验证入口

- `.github/workflows/gates.yml`
- `wow-forever-web/app/package.json`
- `wow-forever-web/tools/site-check.py`
- `wow-forever-web/tools/route-smoke.py`
- `wow-forever-web/tools/build-data.js`

