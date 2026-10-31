#!/usr/bin/env node
/* 无限资料小程序 · OSS 分发层
   ------------------------------------------------------------------
   方案照搬 PoE 那条线（bucket 与「manifest 指针 + 逻辑键 + 索引/详情两级加载」），
   但把它踩过的三个坑一次修掉：
     1) PoE 是「直接覆盖同名文件」→ 传到一半失败，线上就是新清单配旧数据。
        这里改成先写不可变批次目录 builds/{buildId}/，全部校验通过后才最后换
        一份 manifest.json 指针；指针没换之前用户读到的还是上一批完整数据。
     2) PoE 的 manifest 拿不到就静默回退硬编码旧地址 → 用户读到旧数据还不显示。
        这里批次路径里带 buildId，客户端按清单里记的服务器 ETag 逐文件比对
        （见下方 integrity 段：入口文件比指针给的 ETag，按需分片比索引条目给的 ETag），
        对不上就整条当失败降级，并在界面标 live/cache/snapshot，不许静默。
     3) PoE 把「构建时间」当「数据更新时间」显示。
        这里清单里根本没有生成时间字段（2026-10-21 R1 改的：同 buildId 必须逐字节恒定，
        否则"不可变批次"每次重跑都会被自己的时间戳覆写一遍），数据的核对时间看
        factDates 和每条的 provenance，发布时刻看对象的服务端 Last-Modified。

   buildId 只由内容指纹决定：同一份基底重跑两次得到同一个目录、同样字节。
   零第三方依赖：OSS V1 签名自己用 node:crypto 算（本仓库没有 package.json，
   不给 tools/ 引 npm 依赖）。

   子命令
     node tools/oss-release.js build --env beta
     node tools/oss-release.js upload --env beta [--dry-run]
     node tools/oss-release.js verify --env beta
     node tools/oss-release.js list --env beta
     node tools/oss-release.js rollback --env beta --to <buildId>
     node tools/oss-release.js clean --env beta --yes-clean

   写授权（2026-10-21 R1 收紧，站主口径）
     upload / rollback / clean 是写 bucket 的动作，**不论凭证从哪来**，都必须显式带
     环境变量 WOW_ALLOW_CROSS_CREDS=1 才执行；只读（list / verify / --dry-run / build）
     不需要。目的不是区分钥匙归属，而是逼着每条写命令都被人工点过一次头。
     release 环境在此之上还要 --yes-release，clean 还要 --yes-clean。
   凭证解析顺序：环境变量 → $WOW_OSS_ENV → 仓库根 .oss-env → ../p2-database/auto_browser/.env
   仓库根不在小程序目录里，所以这份文件不可能被微信打包器带进代码包；
   for-mini/.oss-env 一律拒绝使用（.gitignore 挡不住打包）。密钥不入库、不打印。 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const cp = require('child_process');

const REPO = path.resolve(__dirname, '..', '..');
const WEB = path.resolve(__dirname, '..');
const MINI = path.join(REPO, 'for-mini');
const EXPORT_TOOL = path.join(__dirname, 'export-mini.js');

/* 路径每次调用现读，测试才能在同一进程里换夹具目录 */
const previewDir = () => process.env.WOW_MINI_PREVIEW || path.join(MINI, 'oss-preview');
const buildRoot = () => process.env.WOW_MINI_BUILD || path.join(MINI, 'oss-build');
/* 站点基底这一层现在是 app/（2026-10-24 旧站删掉、src/ 整目录清掉，数据与素材搬进 app/）。
   变量名 siteSrc 与那个已不存在的目录同义，留着比改成 siteBase 更容易让人以为还有一份旧站。 */
const siteSrc = () => process.env.WOW_SITE_SRC || path.join(WEB, 'app');
const siteData = () => path.join(siteSrc(), 'data');
const localCredPath = () => process.env.WOW_OSS_LOCAL_ENV || path.join(REPO, '.oss-env');
const crossCredPath = () => process.env.WOW_OSS_CROSS_ENV || path.join(REPO, '..', 'p2-database', 'auto_browser', '.env');

const SCHEMA_VERSION = 1;
const PRODUCT = 'wow-forever-mini';
const NAMESPACES = { beta: 'wow/beta/v1', release: 'wow/release/v1' };
const DEFAULT_BUCKET = 'poe2-all-class';
const DEFAULT_REGION = 'oss-cn-hangzhou';
const WRITE_MARK = 'WOW_ALLOW_CROSS_CREDS';

/* 单文件体积上限：超了就是分片粒度错了，宁可构建失败也别把大文件推给手机 */
const BUDGET_KB = {
  /* 指针从 3 个入口长到 7 个（M02 加技能/掉落，M03 加职业/指南），
     8 KB 是三个入口时代定的；冷启动真正要守的是"指针+副本索引+meta ≤ 40 KB"那条。 */
  manifest: 12,
  /* files.json 是"这一批每个文件的哈希台账"，只有构建端的 verify 会整份读，
     玩家冷启动路径是 meta + 指针 + 那一份索引，不含它——所以这条预算管的是构建产物，不是流量。
     2026-10-30 加宏命令线（1 索引 + 9 职业片）后从 64 KB 顶到需要更宽，抬到 96 KB 并留这条说明。 */
  bundle: 96,
  'dungeons/index': 40,
  meta: 8,
  glossary: 200,
  detail: 32,
  /* 2026-10-23 这一片开始还要带每件装备的详情行（属性行/装等/卖价/状态，位置数组存）。
     预算没动：最大的一座黑石深渊 133 件、整片 53.3 KB，离 64 KB 还有 17%。
     哪天属性行涨到顶破这条，说明该把详情拆成单独一片了——由构建来提醒，不等手机上出问题。 */
  loot: 64,
  'spells/classes': 12,
  spellClass: 64,
  'loots/index': 192,
  'classes/index': 64,
  talentClass: 64,
  guide: 32,
  /* 配装线（2026-10-26）：索引 38 套约 5 KB；共享物品表 829 件（位置数组存）；
     单套一片最大 16.6 KB（alts 那 175 个 ID 占大头）。 */
  /* bisItems 是"进这一页要下一次"的共享表：830 件 × (名字/品质/装等/图标键/最多 4 条属性行)。
     2026-10-26 实测 118 KB。哪天它顶破这条，说明属性行该拆成单独一片（按部位或按职业），
     由构建来提醒，不等手机上出问题。 */
  'bis/index': 24,
  bisItems: 128,
  bisSet: 28,
  /* 专业线（2026-10-27）：索引 13 个专业约 6 KB；分片自成一格（图标/材料/商人/图纸字典都就地带），
     点开哪个专业才下那一片。最大的是制皮 511 条配方。哪天顶破这条，说明该把分片再按分箱拆了，
     由构建来提醒，不等手机上出问题。 */
  'professions/index': 24,
  /* 2026-10-27 实测最大的一片：制皮 511 条配方 = 65.6 KB（紧凑写法）。
     80 KB 是给"再抓一批配方"留的余量；哪天顶破这条，下一步是按分箱把一片拆成四片，
     不是把预算再抬——手机端点开一个专业付一次这个数，得有人守着。 */
  profSet: 80,
  'macros/index': 24,
  macroClass: 48
};

/* M02 起素材走自己的通道：站内 `img/art/...` 不改字段名，只把值改写成
   相对 `wow/{env}/v1/assets/` 的路径（`art/dungeons/x.webp`），客户端用
   oss-manifest 的 assetUrl()/iconUrl() 拼绝对地址。
   本地文件不存在的（图标/原画缺一张）不阻断构建：那个字段置 null 并记进
   assets/missing.json，界面按"没有这张图"回落自绘——碎图比空图更糟。 */
const ASSET_DIR = 'assets';
const ICON_EXT = '.jpg';
/* 2026-10-22 首页改版：把"哪 7 份是导出产物、哪 8 份是基底原件"这两张名单写成常量并导出——
   门禁脚本以前自己抄了条数（加一份基底就得改门禁），现在两边读同一处，加文件只改这里。
   注意两边是**一对多**：races.json + classes.json 合成 oss-preview/classes.json，
   dungeon-geo.json 并进 dungeons.json 的 geo 字段，所以"条数相等"从来不是正确判据。 */
const EXPORT_RELS = ['meta.json', 'glossary.json', 'dungeons.json', 'spells.json', 'classes.json', 'talents.json', 'guide.json'];
/* items.json + items-detail.json 只喂分发层（装备详情卡），不进导出产物：
   所以它们出现在基底名单里、却不在导出名单里，这是有意的一对多。 */
/* bis.json + professions.json 也只喂分发层（配装线在构建时把名字/装等/来源现算进产物），
   不进 oss-preview 导出产物，理由同 items 那两条。 */
/* flags.json 故意不在这份名单里：它是策略不是数据，改开关不许换 buildId（换了就等于
   "拧一个开关要重发整批数据"）。开关走自己那份可变对象，见 buildFlags。 */
const BASE_INPUTS = ['macros.json', 'glossary.json', 'meta.json', 'dungeons.json', 'spells.json', 'races.json', 'classes.json', 'guide.json', 'dungeon-geo.json', 'ui-art.json', 'art.json', 'items.json', 'items-detail.json', 'bis.json', 'professions.json'];
const DROPPED_DETAIL_FIELDS = [];
const ASSET_NOTE = 'art 与 bosses[].portrait 的值是相对 assets/ 的路径，图标只用 drops[].iconKey 拼 assets/icons/{key}.jpg；'
  + '取不到的（在 assets/missing.json 里登记过）界面必须回落自绘块，不许热链站内 img/ 路径。';

/* 站内相对路径 → 素材相对路径；不是 img/ 开头的返回 null（调用方按缺失处理） */
function assetRelFromSite(rel) {
  const s = String(rel || '');
  return s.indexOf('img/') === 0 ? s.slice(4) : null;
}

const IMUTABLE_CACHE = 'public, max-age=31536000, immutable';
/* 素材必须按"就地显示"发：OSS 默认域名会给对象挂 Content-Disposition: attachment
   与 x-oss-force-download: true，模拟器里的 <image> 照渲染，真机不一定。
   显式写 inline 是在测"对象元数据能不能盖过默认域名的策略"——盖不过就得绑自定义域名。 */
const ASSET_DISP = 'inline';
const POINTER_CACHE = 'public, max-age=60, must-revalidate';

/* —— 功能开关（2026-10-27）——
   一个和批次并列的可变对象，路径 wow/{env}/v1/flags.json，缓存语义与指针同一档。
   为什么不并进 manifest：见 app/data/flags.json 的 whyOutsideBatch。一句话——
   builds/{buildId}/manifest.json 同时是回滚位，必须同 buildId 字节恒定；开关是要随时拧的。
   product 与批次分开（客户端按 product 认对象，混在一起等于让开关冒充数据清单）。 */
const FLAGS_PRODUCT = 'wow-forever-mini-flags';
const FLAGS_FILE = 'flags.json';
const FLAG_NAME_RE = /^[a-z][a-z0-9]*$/;

const sha256 = (buf) => crypto.createHash('sha256').update(buf).digest('hex');
const md5Hex = (buf) => crypto.createHash('md5').update(buf).digest('hex').toUpperCase();
const md5B64 = (buf) => crypto.createHash('md5').update(buf).digest('base64');
/* 同一份 MD5 给两种写法：etag(hex) 给工具比 HEAD，md5(base64) 给客户端比 Content-MD5。
   为什么两种都要：真 bucket 上 wx.request 收到的是 gzip 变体，按 HTTP 规则 ETag 会被剥掉，
   只剩 Content-MD5（2026-10-21 实测）——只写 etag 的话，客户端在线上会全部判失败。 */
const md5Of = (buf) => ({ etag: md5Hex(buf), md5: md5B64(buf) });
const kb = (b) => (b / 1024).toFixed(1);
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const writeBuf = (p, buf) => {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, buf);
};
const dump = (obj) => Buffer.from(JSON.stringify(obj, null, 1) + '\n', 'utf8');
/* 位置数组存的分片（专业那种几万行纯数字）按缩进来写会胖一倍以上：
   一份给人看的索引值排，一份机器读的行列不值这个流量。标了 flat 的条目按紧凑写，
   校验值/字节数一律走 bufOf()，两处必须是同一份字节。 */
const dumpFlat = (obj) => Buffer.from(JSON.stringify(obj), 'utf8');
const isOfficial = (list) => (list || []).some((s) => String(s.type || '').indexOf('official') === 0 || String(s.type || '') === 'datamine_cn');

/* ---------- 1. 把 oss-preview 的三份成品切成一个批次 ---------- */

function collectFactDates(records) {
  const dates = [];
  let without = 0;
  records.forEach((rec) => {
    const own = (rec.provenance || []).map((p) => p.checkedAt).filter(Boolean).sort();
    if (!own.length) { without += 1; return; }
    own.forEach((d) => dates.push(d));
  });
  dates.sort();
  return {
    min: dates.length ? dates[0] : null,
    max: dates.length ? dates[dates.length - 1] : null,
    distinct: dates.length ? new Set(dates).size : 0,
    recordsWithoutDate: without
  };
}

/* 索引条目里就带详情/掉落的 ETag 与字节：客户端取分片时不必先下载 files.json
   才能校验（一次校验多一个 25 KB 请求不值得）。 */
function indexEntry(d, useAsset) {
  return {
    id: d.id,
    kind: d.kind,
    nameCn: d.nameCn || null,
    nameEn: d.nameEn || null,
    nameCnConflict: d.nameCnConflict || null,
    levelRange: d.levelRange || null,
    levelRangeOfficial: d.levelRangeOfficial || null,
    faction: d.faction || null,
    zoneCn: d.zoneCn || null,
    partySize: d.partySize || null,
    partySizeAlt: d.partySizeAlt || null,
    sizeClaim: d.sizeClaim || null,
    level: d.level || 'L3',
    bossCount: (d.bosses || []).length,
    dropCount: (d.drops || []).length,
    hasRoute: (d.route || []).length > 0,
    /* 列表页也要出图：38 座里 37 座有客户端原画，可索引里以前只放文字字段，
       于是列表一片空白。art 是相对 assets/ 的路径（约 30 字节），
       放进索引后断网时列表也知道"这座本该有图"，只是取不到文件时回落。
       字段顺序与 export-mini.js 的 dungeonIndexEntry() 必须完全一致（那边逐字节对拍）。 */
    art: d.art ? useAsset(d.art, d.id + '.index') : null,
    detailPath: 'dungeons/detail/' + d.id + '.json',
    lootPath: 'dungeons/loot/' + d.id + '.json'
  };
}

function detailRecord(d, useAsset, geo) {
  const out = {};
  Object.keys(d).forEach((k) => {
    if (k === 'drops') return;
    if (DROPPED_DETAIL_FIELDS.some((x) => x.field === k)) return;
    out[k] = d[k];
  });
  if (out.art) out.art = useAsset(out.art, d.id + '.art');
  if (Array.isArray(out.bosses)) {
    out.bosses = out.bosses.map((b) => {
      const o = Object.assign({}, b);
      if (o.portrait) o.portrait = useAsset(o.portrait, b.id + '.portrait');
      return o;
    });
  }
  out.dropCount = (d.drops || []).length;
  out.lootPath = 'dungeons/loot/' + d.id + '.json';
  /* 副本地图（M03）：入口在哪个区、坐标多少，内部底图走素材层。
     底图分两种来源，addon-drawn 的那几座界面必须就地标"示意图"（根 AGENTS.md）。 */
  const g = geo ? geo[d.id] : null;
  if (g) {
    out.geo = {
      zone: (g.entry && g.entry.zone) || null,
      entryX: g.entry && g.entry.x !== undefined && g.entry.x !== null ? g.entry.x : null,
      entryY: g.entry && g.entry.y !== undefined && g.entry.y !== null ? g.entry.y : null,
      mapKind: g.bossMapKind || null,
      map: g.bossMap ? useAsset(g.bossMap, d.id + '.map') : null
    };
  }
  return out;
}

/* 种族条目（2026-10-22 补天裔）。两处"数据在库里、界面读不到"的坑都收在这一个函数里：
   ① 天裔两条的特长挂在 `subgroup.traits`（各 4 条，L0 官方中文原句），顶层 `traits` 是空数组——
      小程序只读顶层，于是玩家看到"这个种族的特长还没核到，不猜"，而那 4 条一直都在。
      这里合成一份给界面，并用 `traitVia` 说清是哪一层来的；基底 races.json 不动
      （网页那侧本来就读 subgroup.traits，改基底会牵动它）。
   ② 天裔没有官方 CDN 种族图标（iconKey 为 null），但站主 2026-10-20 授权用插件里那张
      种族小图标（记在 art.json 的 raceIcons，只许当小图标、不许换传承页那张大图原画），
      小程序此前没接这条线。这里按种族 id 对上，落成 `portrait`（assets 相对路径）。
   图标位取图顺序（2026-10-23 站主两次改口后的最终版）：**10 个种族统一用 `art.json.races`
   那批 128 客户端种族头像**，不再按"谁有官方 CDN 图标"各走各的——
   上一版暗夜精灵补上之后，同一排里 9 张是官方 CDN 的 56 图标、1 张是 128 头像，站主看了说"10 个统一都换成大图"。
   `raceIcons`（10-20 单独授权那张 64 插件天裔小图）退成兜底：只有大图缺了才用它；
   官方 CDN 的 `iconKey` 仍随分片下发（网页端与别处还在用），但界面这条线不再优先取它。
   三层都对不上的仍然 null，界面自绘回落。 */
function raceIconBase(id) {
  return String(id || '').replace(/-(horde|alliance)$/, '');
}
function raceTraitRow(t) {
  return { name: t.name, passive: !!t.passive, effect: t.effect || '', iconKey: t.iconKey || null };
}
function raceEntry(r, artIndex, useAsset) {
  const top = (r.traits || []).map(raceTraitRow);
  const fromSub = top.length === 0;
  const traits = fromSub ? (((r.subgroup || {}).traits) || []).map(raceTraitRow) : top;
  const base = raceIconBase(r.id);
  const bigRel = ((artIndex || {}).races || {})[base] || null;
  const iconRel = ((artIndex || {}).raceIcons || {})[base] || null;
  let portrait = null;
  /* 统一大图在前，插件小图兜底（站主 2026-10-23 口径，理由写在上面那段注释里） */
  const rel = bigRel || iconRel;
  if (rel) {
    const got = typeof useAsset === 'function' ? useAsset(rel, r.id + '.raceIcon') : String(rel);
    portrait = got ? String(got).replace(/^img\//, '') : null;
  }
  return {
    id: r.id, nameCn: r.nameCn || null, nameEn: r.nameEn || null, faction: r.faction || null,
    iconKey: r.iconKey || null, level: r.level || 'L3',
    subgroup: r.subgroup ? { nameCn: r.subgroup.nameCn || null } : null,
    classes: r.classes || [],
    traits: traits,
    traitVia: traits.length ? (fromSub ? 'subgroup' : 'race') : '',
    portrait: portrait
  };
}

/* 装备详情行（2026-10-23 站主要"点一件装备能单独看详情"）。
   行是位置数组、列名写在同片的 cardCols 里——与 loots/index.json 同一套省字节的做法。
   itemId 是客户端的归并键：装备名/品质/图标/首领那份已经在同片的 drops 里了，
   这里只补"点进详情才用得上"的那几列，不重复存第二份。
   状态键与网页端 ItemsPage.vue 的 stLabel() 同一条式子：参考站自报 missing、
   但玩家 10-19 实测确认服务器有的那 82 件，两边都必须显示"测试服有"，不能一边一个样。 */
const CARD_COLS = ['itemId', 'type', 'ilvl', 'st', 'sell', 'stKey'];
const ITEM_ST_LABEL = { new: '新增', changed: '改动', rebuilt: '重建', same: '不变', missing: '无限中没有', srvHas: '测试服有' };
function itemStKey(it) {
  return it.status === 'missing' && it.srv === 'present' ? 'srvHas' : it.status;
}
function itemCardRow(drop, itemIndex, detailIndex, miss) {
  const id = String(drop.itemId || '');
  const it = itemIndex[id];
  if (!it) { miss.noBase += 1; return null; }
  const d = detailIndex[id] || {};
  if (!d.st) miss.noDetail += 1;
  const key = itemStKey(it);
  return [
    id,
    it.type || null,
    it.ilvl === undefined ? null : it.ilvl,
    d.st || [],
    d.sell || null,
    key === 'same' ? null : (ITEM_ST_LABEL[key] ? key : null)
  ];
}

/* 系底图：art.json 的 specs[{classId}-{系序号}]，与网页 lib/art.js 的 specArt() 同一条键规则。
   顺手登记进素材台账——不登记的话界面拼得出地址、bucket 上却没有这张（2026-10-22 那次
   "缺登记 0 条却线上 404" 就是这条链）。本地缺文件则记进 assetMissing，构建当场拦。 */
/* —— 配装（BiS）线的列名与部位桥表 ——
   参考站的部位键（head/neck…）与纸娃娃上的中文标签（项链/戒指…）不是一套词，
   而且"主手"这一格在名单里可能对应 main-hand 或 two-hand 两节。
   这两张表原来只写在网页 BisPage.vue 里；小程序要读同一份数据，就把桥随索引下发，
   两端读同一处，不各抄一份（抄两份必然飘）。 */
const BIS_ITEM_COLS = ['id', 'name', 'quality', 'ilvl', 'iconKey', 'st'];
const BIS_SLOT_KEYS = { head: '头部', neck: '项链', shoulder: '肩部', back: '背部', chest: '胸部',
  wrist: '手腕', hands: '手', waist: '腰部', legs: '腿部', feet: '脚', finger: '戒指',
  trinket: '饰品', 'main-hand': '主手', 'off-hand': '副手', 'two-hand': '双手武器',
  shield: '副手：盾牌', held: '副手：手持物品', ranged: '远程', relic: '圣物' };
const BIS_SLOT_SIBS = { '主手': ['main-hand', 'two-hand'], '副手': ['off-hand', 'shield', 'held'] };
const BIS_NOTE = 'bisItems 的列名：id、中文名、品质、装等、图标键（null＝本地没这张图，界面画自绘块）、属性行（只留数值行，最多 4 条；使用/装备：那类效果文案不在其中）。'
  + '装备名/品质/装等/属性行全部回本站物品库现查，这份名单只存"哪件在哪个部位、按什么顺序"。';
const BIS_DISCLAIMER = '这份名单由本站整理自第三方资料，不是官方结论，也没做模拟计算。';

/* —— 专业与配方（2026-10-27）的表与列名 ——
   分箱（技能橙点 1–75 / 76–150 / 151–225 / 226–300）与技能四档那两张表，
   网页那份 ProfessionsPage.vue 里各写了一份字面量。配装那次的做法是"桥随索引下发、两端读同一处"，
   这里照做：小程序从分片渲染，不再自己抄第三份。漂移由 oss-release-test 那条去 grep 网页源文件的对拍抓
   （它红的是测试，不会把发布卡在一个文件格式上）。 */
const PROF_BANDS = [[1, 75, '学徒 · 1–75'], [76, 150, '熟练 · 76–150'],
  [151, 225, '专家 · 151–225'], [226, 300, '大师 · 226–300']];
const PROF_BAND_NOTE = '按技能的橙色起点分四箱；四箱盖不住的另进"技能档位没标出来"，不静默吞条目。';
const PROF_SK_KEYS = [['orange', '橙'], ['yellow', '黄'], ['green', '绿'], ['grey', '灰']];
const PROF_SK_COLS = ['orange', 'yellow', 'green', 'grey'];
/* 页首那张板块图：与网页专业页、首页图标轨「专业」那一格同一张（站内同一板块同一张脸） */
const PROF_HEAD_ICON = '10prof_table_tailoring01';
const PROF_TITLE = '专业与配方';
const PROF_DISCLAIMER = '配方、材料与采集点取自无限客户端（经第三方资料站转述）：只列名称与数量，不给掉率、不做冲级建议。';
const PROF_REC_COLS = ['itemId', 'name', 'icon', 'q', 'new', 'mats', 'sk', 'src', 'vend', 'drops', 'xr', 'vMore', 'dMore'];
const PROF_NODE_COLS = ['name', 'icon', 'yields', 'zone', 'sk'];
const PROF_MAT_COLS = ['name', 'icon'];
/* 宏命令线（2026-10-30）：一片一职业，行用位置数组存，列名只在索引写一份 */
const CLASS_IDS = ['warrior', 'paladin', 'hunter', 'rogue', 'priest', 'shaman', 'mage', 'warlock', 'druid'];
const MACRO_COLS = ['id', 'title', 'group', 'note', 'body', 'minLevel', 'new', 'src', 'nameFrom'];
const MACRO_TITLE = '宏命令';
const MACRO_COL_NOTE = '行的列名见 cols（位置数组存）。body 是宏正文，换行原样保留，界面只读＋整条复制；'
  + 'src 是 srcs 的序号（谁整理的、哪个文件、核对日）；new=1 是无限服新增；nameFrom=addon 表示法术名退回插件烘的那一份。';
const MACRO_DISCLAIMER = '宏命令与技能说明由第三方插件整理，本站免费列出、不分发插件本体、不做循环提示类宏；'
  + '每条都标了整理来源与核对日期，但本站没有逐条进游戏试过，等级与法术名以你客户端里能学到的为准。';
const PROF_COL_NOTE = '行的列名见 cols（位置数组存）。mats 是 [材料序号, 数量, 材料序号, 数量…] 平铺；'
  + 'sk 按 [' + PROF_SK_COLS.join(', ') + '] 排，null 表示这一档源里没给；'
  + 'icon 是 icons 里的序号，-1 就是这条数据本来没有图标（界面画自绘块，不许猜一张）；'
  + 'src 是 sources 的序号，-1 没标；vend/drops 是 vendors/drops 的序号；xr=1 表示首领头像那批来自 XR 表、名字是英文原名；'
  + 'vMore/dMore 是源里被截断后剩下的处数，界面写"等 N 处"时要把截掉的加起来。';

/* 「这套装备给的属性」这一排合计，规则全在网页那份 lib/item-stats.js 里
   （基础护甲的三种写法、哪四类句子不许算——2026-10-19 逐档数过，还有单测盯着）。
   小程序要是自己再抄一份解析器，两份规则迟早飘，同一套装备两端报两个数。
   所以合计在构建时算好、随分片下发，客户端只负责显示。
   这份文件没有 import，去掉 export 关键字就能在构建进程里求值；
   哪天它引入了依赖，这里必须改成显式失败而不是凑合算。 */
function loadStatParser() {
  const f = path.join(WEB, 'app', 'src', 'lib', 'item-stats.js');
  if (!fs.existsSync(f)) return { error: '找不到 app/src/lib/item-stats.js，属性合计没有依据' };
  const src = fs.readFileSync(f, 'utf8');
  if (/^\s*import\s/m.test(src)) return { error: 'item-stats.js 现在带 import，构建端这份求值器要一起改' };
  try {
    const mod = new Function(src.replace(/^export\s+/gm, '')
      + '\nreturn { sumStatLines: sumStatLines };')();
    if (typeof mod.sumStatLines !== 'function') return { error: 'item-stats.js 里没有 sumStatLines' };
    return mod;
  } catch (e) { return { error: '读 item-stats.js 失败：' + e.message }; }
}

function specArtFor(artIndex, classId, ti, useAsset) {
  const siteRel = ((artIndex || {}).specs || {})[classId + '-' + ti] || null;
  if (!siteRel) return null;
  const got = typeof useAsset === 'function' ? useAsset(siteRel, classId + '.spec' + ti) : siteRel;
  return got ? String(got).replace(/^img\//, '') : null;
}

/* 导出产物 ↔ 基底对拍：在临时目录里把真源重导一遍，逐字节比 oss-preview。
   不这么办的话，指针溯源写的是 A（app/data 的哈希），发出去的却是 B（有人手改过的
   oss-preview），两边一致只证明一致，不证明它来自基底。 */
function reExportCompare() {
  const rels = EXPORT_RELS;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ossxchk-'));
  try {
    const web = path.join(tmp, 'wow-forever-web');
    fs.mkdirSync(path.join(web, 'tools'), { recursive: true });
    fs.copyFileSync(EXPORT_TOOL, path.join(web, 'tools', 'export-mini.js'));
    /* 导出层自己也有一道对拍（索引快照 ↔ 分发层索引），要把这份工具一起拷过去，
       否则临时目录里的 export-mini.js 会因为找不到参照而直接拒绝跑。 */
    fs.copyFileSync(path.join(__dirname, 'oss-release.js'), path.join(web, 'tools', 'oss-release.js'));
    /* 导出层自己还要读禁词表（它给玩家看的说明文字也过同一把尺子），
       沙箱里少拷一个文件，重导出就会 ENOENT、对拍变成"没产出 oss-preview"这种误导性的红。 */
    fs.copyFileSync(path.join(__dirname, 'copy-banned.json'), path.join(web, 'tools', 'copy-banned.json'));
    fs.symlinkSync(siteSrc(), path.join(web, 'app'));
    let exportErr = '';
    try {
      cp.execFileSync('node', [path.join(web, 'tools', 'export-mini.js')], {
        encoding: 'utf8', maxBuffer: 8 * 1024 * 1024,
        /* 这道对拍只管"字节：源 → 导出产物"，快照↔索引那层一致性由 export-mini 自己在正式导出时查
           （oss-release-test.js 的 3·5 节直接测它）。这里关掉是为了让坏数据的红字
           由分发层自己的卡口报出来，而不是被上游那层的错误信息盖掉——归因比多跑一遍重要。 */
        env: Object.assign({}, process.env, { WOW_SNAPSHOT_CROSSCHECK: 'off' })
      });
    } catch (e) {
      const t = String(e.stderr || e.stdout || e.message || '');
      exportErr = t.split('\n').filter((x) => x.trim().indexOf('✗') === 0 || x.indexOf('失败') >= 0).slice(0, 3).join(' / ');
    }
    const outDir = path.join(tmp, 'for-mini', 'oss-preview');
    const diffs = [];
    const outputs = [];
    if (exportErr) return { diffs: ['基底重导出被导出层拒绝（源本身就不合规）：' + exportErr], outputs, tool: 'wow-forever-web/tools/export-mini.js' };
    if (!fs.existsSync(outDir)) return { diffs: ['重导出没有产出 oss-preview（export-mini.js 没跑成）'], outputs, tool: 'wow-forever-web/tools/export-mini.js' };
    rels.forEach((rel) => {
      const freshP = path.join(outDir, rel);
      const hereP = path.join(previewDir(), rel);
      if (!fs.existsSync(freshP) || !fs.existsSync(hereP)) { diffs.push(rel + '：一边不存在'); return; }
      const a = fs.readFileSync(freshP);
      const b = fs.readFileSync(hereP);
      outputs.push({ rel: 'oss-preview/' + rel, bytes: b.length, sha256: sha256(b) });
      if (!a.equals(b)) diffs.push(rel + '（重导出 ' + sha256(a).slice(0, 12) + ' ≠ 现有 ' + sha256(b).slice(0, 12) + '）');
    });
    return { diffs, outputs, tool: 'wow-forever-web/tools/export-mini.js' };
  } finally {
    cp.execSync('rm -rf ' + JSON.stringify(tmp));
  }
}

function buildBatch(env, opts) {
  const errors = [];
  const ns = NAMESPACES[env];
  const prev = previewDir();
  const glossarySrc = path.join(prev, 'glossary.json');
  const metaSrc = path.join(prev, 'meta.json');
  const dungeonsSrc = path.join(prev, 'dungeons.json');
  const spellsSrc = path.join(prev, 'spells.json');
  const classesSrc = path.join(prev, 'classes.json');
  const talentsSrc = path.join(prev, 'talents.json');
  const guideSrc = path.join(prev, 'guide.json');
  [glossarySrc, metaSrc, dungeonsSrc, spellsSrc, classesSrc, talentsSrc, guideSrc].forEach((p) => {
    if (!fs.existsSync(p)) errors.push('缺少导出产物 ' + path.relative(REPO, p) + '，先跑 node tools/export-mini.js');
  });
  if (errors.length) return { errors };

  const glossary = readJson(glossarySrc);
  const miniMeta = readJson(metaSrc);
  const dungeons = readJson(dungeonsSrc);
  const spells = readJson(spellsSrc);
  const spellList = spells.spells || [];
  const classPack = readJson(classesSrc);
  const talentPack = readJson(talentsSrc);
  const guidePack = readJson(guideSrc);
  /* 装备详情卡的两个来源（只读，不进导出产物，见 BASE_INPUTS 那条注释） */
  const itemsSrc = path.join(siteData(), 'items.json');
  const itemDetailSrc = path.join(siteData(), 'items-detail.json');
  if (!fs.existsSync(itemsSrc) || !fs.existsSync(itemDetailSrc)) {
    errors.push('缺少装备基底 app/data/items.json 或 items-detail.json，装备详情卡没有数据来源');
  }
  const itemsIndex = {};
  const itemDetailIndex = {};
  const itemCardMiss = { noBase: 0, noDetail: 0 };
  if (fs.existsSync(itemsSrc) && fs.existsSync(itemDetailSrc)) {
    (readJson(itemsSrc).items || []).forEach((x) => { itemsIndex[String(x.id)] = x; });
    const det = readJson(itemDetailSrc).items || {};
    Object.keys(det).forEach((k) => { itemDetailIndex[String(k)] = det[k]; });
  }

  /* 素材登记表：这一批真引用到、且本地确实在的文件 */
  const assetUse = {};
  const assetMissing = [];
  const statAsset = (rel) => {
    const abs = path.join(WEB, "app", "img", rel);
    if (!fs.existsSync(abs)) return null;
    const buf = fs.readFileSync(abs);
    return { rel, srcRel: 'app/img/' + rel, bytes: buf.length, sha256: sha256(buf), etag: md5Hex(buf) };
  };
  const useAsset = (siteRel, why) => {
    const rel = assetRelFromSite(siteRel);
    if (!rel) { assetMissing.push({ ref: siteRel, reason: '不是 img/ 开头的站内路径', by: why }); return null; }
    const st = statAsset(rel);
    if (!st) { assetMissing.push({ ref: siteRel, reason: '本地没有这个文件', by: why }); return null; }
    assetUse[rel] = st;
    return rel;
  };
  const useIcon = (key, why) => {
    if (!key) return null;
    const rel = 'icons/' + key + ICON_EXT;
    if (!statAsset(rel)) { assetMissing.push({ ref: rel, reason: '图标文件不在 app/img/icons/', by: why }); return; }
    assetUse[rel] = statAsset(rel);
  };
  const list = [].concat(dungeons.newDungeons || [], dungeons.classicDungeons || [], dungeons.raids || []);
  const geoPath = path.join(siteData(), 'dungeon-geo.json');
  const geoPack = fs.existsSync(geoPath) ? readJson(geoPath) : null;
  const geoById = (geoPack && geoPack.dungeons) || {};

  /* —— 卡口（与根 AGENTS.md 第五条同一口径，导出这层再拦一次） —— */
  if (!list.length) errors.push('副本 0 条');
  const ids = list.map((d) => d.id);
  if (new Set(ids).size !== ids.length) errors.push('副本 id 有重复');
  ids.forEach((id) => {
    if (!/^[a-z0-9][a-z0-9-]*$/.test(id)) errors.push('副本 id ' + id + ' 含不能作为文件名的字符');
  });
  list.forEach((d) => {
    if (d.level === 'L0' && !isOfficial(d.provenance)) errors.push('副本 ' + d.id + '：标 L0 但没有官方/解包来源');
    if (!d.nameEn && !d.nameCn) errors.push('副本 ' + d.id + '：中英文名都为空');
    if (/\d+(\.\d+)?\s*%/.test(JSON.stringify(d.drops || []))) errors.push('副本 ' + d.id + '：掉落里出现百分比');
  });
  (glossary.items || []).forEach((x) => {
    if (x.level === 'L0' && !isOfficial(x.provenance)) errors.push('词条 ' + x.id + '：标 L0 但没有官方/解包来源');
  });
  /* 法术书：分片按职业切，所以"每个职业都得有内容"是硬条件；
     classId 会直接拼进文件路径，这里再拦一次（导出层也拦，两道都要在） */
  if (!spellList.length) errors.push('法术书 0 条：spells.json 没导出成功，先跑 export-mini.js');
  (spells.classes || []).forEach((c) => {
    if (!/^[a-z][a-z0-9_-]*$/.test(String(c.classId))) errors.push('职业 ' + c.classId + '：id 不能当分片文件名');
    const n = spellList.filter((s) => s.classId === c.classId).length;
    if (!n) errors.push('职业 ' + c.classId + '：名单里有它但一条法术都没有，这个分片会是空的');
    if (n !== c.count) errors.push('职业 ' + c.classId + '：头部写 ' + c.count + ' 条，实际 ' + n + ' 条');
  });
  spellList.forEach((s) => {
    if (!(spells.classes || []).some((c) => c.classId === s.classId)) errors.push('法术 ' + s.id + '：所属职业不在职业名单里，这条永远不会被读到');
  });

  const srcFiles = BASE_INPUTS.map((f) => {
    const abs = path.join(siteData(), f);
    if (!fs.existsSync(abs)) { errors.push('找不到基底文件 app/data/' + f); return null; }
    const buf = fs.readFileSync(abs);
    return { rel: 'app/data/' + f, bytes: buf.length, sha256: sha256(buf) };
  }).filter(Boolean);

  /* —— 与真源对拍：这一批必须能由 app/data 重导出得到 —— */
  let exportCheck = null;
  if (!(opts && opts.skipExportCheck)) {
    const chk = reExportCompare();
    if (chk.diffs.length) {
      chk.diffs.forEach((d) => errors.push('导出产物与基底不配套，构建拒绝：' + d + '；先跑 node tools/export-mini.js 再 build'));
      return { errors };
    }
    exportCheck = { tool: chk.tool, reproduced: true,
      note: '构建时在临时目录用同一份 app/data 重跑了一遍 export-mini.js，' + chk.outputs.length + ' 份导出产物逐字节相同。',
      outputs: chk.outputs };
  }

  let commit = null;
  try {
    commit = cp.execSync('git -C ' + REPO + ' rev-parse --short HEAD', { encoding: 'utf8' }).trim();
  } catch (e) { commit = null; }

  if (errors.length) return { errors };

  /* —— 内容指纹 → buildId（与时间无关，重跑同源必得同一个 id） ——
     meta/glossary 来自 export-mini.js 的产物，只在外层加身份字段（schemaVersion/product/kind/buildId），
     业务字段一个不动；其余是本层生成的壳。九个身份字段让客户端不用算哈希也能认出混版。 */
  const entries = [];
  const pushObj = (key, relPath, obj, info) => { entries.push(Object.assign({ key, relPath, path: relPath, obj }, info)); };

  pushObj('meta', 'meta.json', Object.assign({ schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'batch-meta' }, miniMeta),
    { records: 1, budget: 'meta', facts: collectFactDates([miniMeta]) });
  pushObj('glossary', 'glossary.json', Object.assign({ schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'glossary' }, glossary),
    { records: (glossary.items || []).length, budget: 'glossary', facts: collectFactDates(glossary.items || []) });

  const indexObj = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    kind: 'dungeon-index',
    counts: {
      total: list.length,
      newDungeons: (dungeons.newDungeons || []).length,
      classicDungeons: (dungeons.classicDungeons || []).length,
      raids: (dungeons.raids || []).length
    },
    note: dungeons.meta ? dungeons.meta.note : '',
    lootDisclaimer: dungeons.meta ? dungeons.meta.lootDisclaimer : '',
    notCollected: { route: list.length - list.filter((d) => (d.route || []).length).length },
    items: list.map((d) => indexEntry(d, useAsset))
  };
  pushObj('dungeonIndex', 'dungeons/index.json', indexObj, {
    records: list.length, budget: 'dungeons/index', facts: collectFactDates(list)
  });

  list.forEach((d) => {
    (d.drops || []).forEach((x) => useIcon(x.iconKey, 'dungeons/loot/' + d.id));
    const det = { schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'dungeon-detail', source: 'wow-forever-web/app/data/dungeons.json', dungeon: detailRecord(d, useAsset, geoById) };
    pushObj('dungeonDetail:' + d.id, 'dungeons/detail/' + d.id + '.json', det, {
      records: 1, budget: 'detail', facts: collectFactDates([d])
    });
    /* 装备详情（2026-10-23 站主："点击装备可以单独展示装备详情"）就并进这一片，
       不单开 dungeons/cards/{id}.json，也不开 1018 个单件文件，两个理由：
       ① 玩家点的那一件一定在他刚打开的这座本的掉落表里——这一片已经在手机上了，
          再发一次请求只是把同一屏拆成两次网络；
       ② 校验值要么占索引每条 110 字节（38 座 = 冷启动多 4 KB，所有人都付），
          要么随单件文件走（1018 个对象，verify 要逐个回读）。并进本片这两条都不发生。
       代价写在 BUDGET_KB.loot 那条注释里。属性行按位置数组存（列名在 cardCols），
       133 件的黑石深渊按对象存多 12 KB。 */
    const loot = {
      schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'dungeon-loot', dungeonId: d.id,
      level: d.level || 'L3', lootNote: d.lootNote || null, drops: d.drops || [],
      cardCols: CARD_COLS,
      cardNote: 'cardCols 是 cards 每行的列名：itemId、类型、装等、属性行数组（顺序就是游戏里的读法）、'
        + '商人卖价、相对经典旧世的状态；装备名/品质/图标/首领在同片 drops 里按 itemId 对。'
        + '状态里「无限中没有」是参考站自报，不是官方结论；属性行与卖价取自插件名录或第三方解包站，本站未做游戏内实测。',
      cards: (d.drops || []).map((x) => itemCardRow(x, itemsIndex, itemDetailIndex, itemCardMiss)).filter((x) => x)
    };
    pushObj('dungeonLoot:' + d.id, 'dungeons/loot/' + d.id + '.json', loot, {
      records: (d.drops || []).length, budget: 'loot', facts: collectFactDates([d])
    });
  });

  /* —— 法术书（M02-2）：一个职业一片，客户端先取职业名单、点开哪个职业才取那一片。
     不打进主包：498 条 340 KB，主包 60 KB 预算已给副本索引；断网时界面必须说"技能表要联网"。 —— */
  const spellGroups = (spells.classes || []).map((c) => {
    const rows = spellList.filter((s) => s.classId === c.classId);
    useIcon(c.iconKey, 'spells/classes');
    rows.forEach((s) => useIcon(s.iconKey, 'spells/class/' + c.classId));
    return { c, rows };
  });
  spellGroups.forEach((g) => {
    const obj = {
      schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'spell-class',
      classId: g.c.classId, nameCn: g.c.nameCn || null, nameEn: g.c.nameEn || null,
      iconKey: g.c.iconKey || null,
      source: 'wow-forever-web/app/data/spells.json',
      fieldNote: spells.meta ? spells.meta.fieldNote : '',
      levelPolicy: spells.meta ? spells.meta.levelPolicy : '',
      spells: g.rows.map((s) => Object.assign({}, s))
    };
    pushObj('spellClass:' + g.c.classId, 'spells/class/' + g.c.classId + '.json', obj, {
      records: g.rows.length, budget: 'spellClass', facts: collectFactDates(g.rows)
    });
  });
  const spellIndexObj = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    kind: 'spell-class-index',
    source: 'wow-forever-web/app/data/spells.json',
    counts: { total: spellList.length, classes: spellGroups.length },
    fieldNote: spells.meta ? spells.meta.fieldNote : '',
    pageNote: spells.meta ? spells.meta.pageNote : '',
    classes: spellGroups.map((g) => ({
      classId: g.c.classId,
      nameCn: g.c.nameCn || null,
      nameEn: g.c.nameEn || null,
      iconKey: g.c.iconKey || null,
      level: g.c.level || 'L3',
      count: g.rows.length,
      tabs: g.c.tabs || [],
      states: g.c.states || {},
      shardPath: 'spells/class/' + g.c.classId + '.json'
    }))
  };
  pushObj('spellClasses', 'spells/classes.json', spellIndexObj, {
    records: spellGroups.length, budget: 'spells/classes', facts: collectFactDates(spellList)
  });

  /* —— 职业卡（M03）：种族+职业+可选矩阵一份索引，天赋按职业切片 ——
     2026-10-22 改口径：`rules`（totalPoints + tierUnlockCost）随片下发，天赋页要做加点判定，
     界面上固定写"按经典旧世推、无限服还没实测"。见 wow-forever-web/AGENTS.md 硬规矩第 5 条。 */
  const raceList = classPack.races || [];
  /* art.json 是"哪个种族有哪张图"的那一处真源（网页也读它），这里只取 raceIcons 那一层——
     即站主 2026-10-20 授权的天裔**种族小图标**；传承页那张大图（races 那一层）不下发、不替换。 */
  const artPath = path.join(siteData(), 'art.json');
  const artIndex = fs.existsSync(artPath) ? readJson(artPath) : {};
  const classList = classPack.classes || [];
  const talentByClass = {};
  (talentPack.classes || []).forEach((t) => { talentByClass[t.classId] = t; });
  raceList.forEach((r) => {
    /* 种族身上挂图标的地方不止一处：种族图标、特质、子群（同盟/天裔）自己的特质。
       漏一个就是 2026-10-22 那次"缺登记 0 条却线上 404"的同一种错，所以整棵递归登记。 */
    const walkIcons = (node) => {
      if (Array.isArray(node)) { node.forEach(walkIcons); return; }
      if (!node || typeof node !== 'object') return;
      Object.keys(node).forEach((k) => {
        if (k === 'iconKey' && typeof node[k] === 'string' && node[k]) useIcon(node[k], 'classes/index');
        else walkIcons(node[k]);
      });
    };
    walkIcons(r);
  });
  /* 界面底图（2026-10-22 站主：首页卡片要配图、页面背景用《无限》那张氛围图）。
     这几张不挂在任何数据条目上，是界面自己引用的，所以单独登记一次——
     不登记就会撞上下面那条反向卡口（界面要、素材层没有＝玩家看到的是一片纯色而不是报错）。 */
  const uiArtSrc = path.join(siteData(), 'ui-art.json');
  if (!fs.existsSync(uiArtSrc)) {
    errors.push('找不到基底文件 app/data/ui-art.json：首页底图没有真源，界面不许自己抄路径');
  } else {
    const uiPack = readJson(uiArtSrc);
    const walkUi = (node, where) => {
      if (!node || typeof node !== 'object') return;
      Object.keys(node).forEach((k) => {
        if (k === 'path' && typeof node[k] === 'string' && node[k]) useAsset(node[k], where);
        else if (node[k] && typeof node[k] === 'object') walkUi(node[k], where + '.' + k);
      });
    };
    /* 整份都走一遍（meta 那段是说明文字，不是素材）：以前只走 home 那一组，
       2026-10-23 底图从 home.bg 挪到 tabs.bg 时，只走 home 就等于新那张永远不登记，
       界面拼得出地址、bucket 上却没有——正是 10-22 那次"缺登记 0 条却线上 404"的形状。 */
    Object.keys(uiPack).forEach((k) => {
      if (k !== 'meta') walkUi(uiPack[k], 'ui-art.' + k);
    });
  }
  const talentGroups = classList.map((c) => {
    const t = talentByClass[c.classId] || null;
    if (t) {
      (t.trees || []).forEach((tr) => (tr.nodes || []).forEach((n) => useIcon(n.iconKey, 'talents/class/' + c.classId)));
    }
    return { c, t };
  });
  talentGroups.forEach((g) => {
    if (!g.t) return;
    const obj = {
      schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'talent-class',
      classId: g.c.classId, nameCn: g.t.classNameCn || g.c.nameCn || null,
      grid: g.t.grid || null,
      /* 2026-10-22 站主要小程序天赋树做成"能模拟点配置"，与网页版 TalentPage 用同一套数：
         totalPoints 与 tierUnlockCost 都要下发，否则小程序做不了加点判定。
         （M03 那版刻意不下发 tierUnlockCost，因为当时界面只摆位、不判定——口径变了。）
         "层级点数门槛仍未核实"这句留在界面上，来源与网页同一条：grid.note 与 structureSources。 */
      rules: g.t.rules || null,
      structureStatus: g.t.structureStatus || null,
      structureSources: g.t.structureSources || [],
      note: g.t.note || (talentPack.meta || {}).note || '',
      trees: (g.t.trees || []).map((tr, ti) => ({
        id: tr.id, nameCn: tr.nameCn || null, nameEn: tr.nameEn || null,
        nameConflict: tr.nameConflict || false, nameAlt: tr.nameAlt || null,
        /* 系底图（2026-10-22 站主：小程序的天赋系也要有底图，和网页保持一致）。
           真源还是 art.json 的 specs[{classId}-{系序号}]，与网页 lib/art.js 的 specArt() 同一条键规则，
           不在界面里另写一份"哪个系用哪张图"。 */
        specArt: specArtFor(artIndex, g.c.classId, ti, useAsset),
        nodes: (tr.nodes || []).map((n) => ({
          id: n.id, tier: n.tier, column: n.column, maxRanks: n.maxRanks,
          nameCn: n.nameCn || null, nameConflict: n.nameConflict || false,
          /* 两个叫法的节点必须两个都发（根 AGENTS.md：两源分歧不取舍掩盖），
             长按详情里并列显示，而不是只挑一个当真的 */
          nameAlt: n.nameAlt || null,
          iconKey: n.iconKey || null, requires: n.requires || [], level: n.level || 'L3',
          /* 相对经典旧世这条变了没有（added/modified/moved/unchanged）——
             库里有的事实，长按详情要给它；没有就是 null，界面不猜 */
          changeState: n.changeState || null
        }))
      }))
    };
    pushObj('talentClass:' + g.c.classId, 'talents/class/' + g.c.classId + '.json', obj, {
      records: obj.trees.reduce((s2, tr) => s2 + tr.nodes.length, 0), budget: 'talentClass', facts: collectFactDates([])
    });
  });
  /* 种族条目算一次，两处用：名单本身，和组合卡按名字回查种族图标。
     天裔两条同名（联盟/部落各一条）在这里是两条不同条目，按名字取会撞——
     但两条的图标位是同一张（raceIconBase 把阵营后缀剥掉再对 art.json），所以组合卡取哪条都一样。 */
  const raceRows = raceList.map((r) => raceEntry(r, artIndex, useAsset));
  const raceByName = {};
  raceRows.forEach((r) => { if (r.nameCn && !raceByName[r.nameCn]) raceByName[r.nameCn] = r; });
  const classIndexObj = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    kind: 'class-index',
    source: 'wow-forever-web/app/data/races.json + classes.json + talents/',
    comboNote: classPack.meta ? classPack.meta.comboNote : '',
    counts: {
      races: raceList.length,
      classes: classList.length,
      combos: (classPack.combos || []).length,
      talentNodes: talentGroups.reduce((s2, g) => s2 + (g.t ? g.t.trees.reduce((a2, tr) => a2 + (tr.nodes || []).length, 0) : 0), 0)
    },
    factions: classPack.factions || [],
    races: raceRows,
    classes: classList.map((c) => ({
      classId: c.classId, nameCn: c.nameCn || null, nameEn: c.nameEn || null, iconKey: c.iconKey || null,
      level: c.level || 'L3',
      spellCount: (spellGroups.filter((g) => g.c.classId === c.classId)[0] || { rows: [] }).rows.length,
      hasTalents: !!talentByClass[c.classId],
      shardPath: talentByClass[c.classId] ? 'talents/class/' + c.classId + '.json' : null
    })),
    /* 组合卡补上"这一格是哪个种族"：站主 2026-10-23 指令——组合卡该放种族图标，
       以前放的是职业图标（点进去确实是那个职业的天赋页，但一格写着"兽人法师"却画一张法师脸，
       玩家没法从图上看出新组合新在哪个种族）。raceCn → 种族条目按名字对，
       天裔两条同名（联盟/部落各一条）取到的图标是同一张，不影响。 */
    combos: (classPack.combos || []).map((x) => {
      const rr = raceByName[x.raceCn] || null;
      return Object.assign({}, x, {
        raceId: rr ? rr.id : null,
        racePortrait: rr ? rr.portrait : null,
        raceIconKey: rr ? rr.iconKey : null
      });
    }),
    conflicts: classPack.conflicts || []
  };
  pushObj('classIndex', 'classes/index.json', classIndexObj, {
    records: classIndexObj.counts.races + classIndexObj.counts.classes, budget: 'classes/index', facts: collectFactDates(raceList)
  });
  const guideObj = Object.assign({ schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'guide' }, guidePack);
  pushObj('guide', 'guide.json', guideObj, {
    records: (guidePack.macros || []).length + (guidePack.addons || []).length, budget: 'guide', facts: collectFactDates([])
  });

  /* —— 掉落反查（M02-3）：整座站的掉落摊成一张"这件装备哪座本掉"的表 ——
     一行一个物品，按座分片存不下（一件装备可能出现在两座），所以做成一张总表。
     为了不把手机流量打爆，这里用位置数组而不是对象键：列名写在 cols 里，
     副本名与首领名不重复存（一次 GET 里同一座本只出现一次），
     副本的中文名客户端从主包索引快照就能对上，不必再抄一遍。 */
  const LOOT_COLS = ['itemId', 'name', 'quality', 'iconKey', 'boss', 'level'];
  const lootCols = LOOT_COLS;
  const lootDungeons = list.map((d) => {
    const bosses = (d.drops || []).reduce((acc, x) => {
      const b = x.bossCn || x.bossId || '未记首领';
      if (acc.indexOf(b) < 0) acc.push(b);
      return acc;
    }, []);
    return {
      id: d.id,
      nameCn: d.nameCn || null,
      kind: d.kind || null,
      level: d.level || 'L3',
      bosses,
      rows: (d.drops || []).map((x) => [
        x.itemId || null,
        x.nameCn || null,
        x.quality === undefined ? null : x.quality,
        x.iconKey || null,
        bosses.indexOf(x.bossCn || x.bossId || '未记首领'),
        x.level || 'L3'
      ])
    };
  });
  const lootObj = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    kind: 'loot-index',
    source: 'wow-forever-web/app/data/dungeons.json',
    cols: lootCols,
    note: '一张表列全本站收录副本的掉落：每行按 cols 的顺序排，boss 是这座本 bosses 数组里的序号。'
      + '同一件装备出现在两座本时是两行，反查时按 itemId 归到一起。',
    qualityNote: '品质档名用游戏内自己那一套：1＝普通、2＝优秀、3＝精良、4＝史诗（本站掉落只出现这四档）。',
    lootDisclaimer: dungeons.meta ? dungeons.meta.lootDisclaimer : '',
    counts: {
      dungeons: lootDungeons.length,
      rows: lootDungeons.reduce((s, d) => s + d.rows.length, 0),
      /* 去重键与 export-mini.js 里 meta.counts.lootItems 同一条式子：
         两边漂了的话首页的数字与点进去的表就对不上（导出层有这道对拍） */
      items: new Set([].concat.apply([], list.map((d) => (d.drops || []).map((x) => String(x.itemId || x.nameCn || ''))))).size
    },
    dungeons: lootDungeons
  };
  pushObj('lootIndex', 'loots/index.json', lootObj, {
    records: lootObj.counts.rows, facts: collectFactDates(list), budget: 'loots/index'
  });
  /* 反查表自己的卡口：不许有百分比（红线）、不许有悬空的首领序号、
     itemId 是玩家复制粘贴要用的，缺了这条就只有一半信息 */
  lootDungeons.forEach((d) => {
    d.rows.forEach((r, i) => {
      const s = JSON.stringify(r);
      /* 客户端是按位置取值的（列名写在 cols 里），行长度与列数对不上就会把
         首领序号当品质显示——这一条必须在构建端拦住，不能指望客户端兜 */
      if (r.length !== lootCols.length) errors.push('掉落反查：' + d.id + ' 第 ' + (i + 1) + ' 行有 ' + r.length + ' 个值，列名却写了 ' + lootCols.length + ' 列');
      if (/\d+(\.\d+)?\s*%/.test(s)) errors.push('掉落反查：' + d.id + ' 第 ' + (i + 1) + ' 行出现百分比');
      if (r[4] < 0 || r[4] >= d.bosses.length) errors.push('掉落反查：' + d.id + ' 第 ' + (i + 1) + ' 行的首领序号 ' + r[4] + ' 在该座的 bosses 里不存在');
      if (!r[0]) errors.push('掉落反查：' + d.id + ' 第 ' + (i + 1) + ' 行缺 itemId，玩家复制过去查不到');
      if (!r[1]) errors.push('掉落反查：' + d.id + ' 第 ' + (i + 1) + ' 行没有中文名（itemId ' + r[0] + '），界面要显示"中文名待核"而不是空着');
    });
  });

  /* —— 配装（BiS）线（2026-10-26 站主："根据 web 页面的 BIS 页面，在小程序中添加 BIS 页面"）——
     数据只有一件事是新的：哪件装备在哪个部位、按什么顺序、这一套还列了哪些附魔与消耗品。
     名字 / 品质 / 装等 / 属性行 / 图标在构建时回本站 items.json 与 items-detail.json 现查，
     烘成一张共享物品表（所有套引用的物品去重，一次下发），38 个分片里只放 ID——
     同一件装备的数在两处各存一份必然会飘，这是本站一直守的那条。
     "从哪儿拿"也在这里现算成中文串（副本名、专业名），客户端不用为显示一行来源再下三份表。
     红线（根 AGENTS.md 2026-10-16 那条例外）：取的是"哪件在哪个部位"这一层，
     成段说明、属性优先级、循环建议、任何"这件比那件好 N%"都没取；构建时再逐片扫一遍。 */
  const bisSrc = path.join(siteData(), 'bis.json');
  const statParser = loadStatParser();
  if (statParser.error) errors.push('配装：' + statParser.error);
  const profSrc = path.join(siteData(), 'professions.json');
  let bisIndexObj = null;
  let bisItemsObj = null;
  let bisAltRows = 0;
  if (fs.existsSync(bisSrc)) {
    const bis = readJson(bisSrc);
    const bsets = bis.sets || [];
    if (!bsets.length) errors.push('配装：app/data/bis.json 里一套都没有，那这一页是空的');
    const profNames = {};
    if (fs.existsSync(profSrc)) {
      (readJson(profSrc).professions || []).forEach((x) => { profNames[x.id] = x.nameCn || x.id; });
    } else {
      errors.push('配装：缺 app/data/professions.json，来源那一列的"专业名"没法还原（不许编一个）');
    }
    const dunNames = {};
    list.forEach((d) => { dunNames[d.id] = d.nameCn; });
    const bisIcon = (key, why) => {
      if (!key) return null;
      const rel = 'icons/' + key + ICON_EXT;
      const st = statAsset(rel);
      if (!st) { assetMissing.push({ ref: rel, reason: '图标文件不在 app/img/icons/', by: why }); return null; }
      assetUse[rel] = st;
      return key;
    };
    const itemMiss = { noBase: 0 };
    const rows = {};
    const needItem = (id, why) => {
      const k = String(id);
      if (rows[k]) return rows[k];
      const base = itemsIndex[k];
      const det = itemDetailIndex[k] || {};
      /* 属性行只留"数值行"：使用/装备：/套装那几句是效果文案，既不进合计也不进这一页的简版显示，
         留着会让这张共享表从 ~95 KB 涨到 150 KB，而它是每个玩家进这一页都要下一次的。 */
      const stKeep = (det.st || []).filter((x) => x && String(x).indexOf('使用') < 0
        && String(x).indexOf('装备：') < 0).slice(0, 4);
      if (!base) {
        itemMiss.noBase += 1;
        rows[k] = [Number(id) || id, null, 0, null, null, []];
        return rows[k];
      }
      rows[k] = [base.id, base.name || null, base.quality == null ? 0 : base.quality,
        base.ilvl == null ? null : base.ilvl, bisIcon(base.iconKey, why), stKeep];
      return rows[k];
    };
    /* 来源串：与网页 BisPage.vue 的 srcOf 同一条式子，两边各写一份迟早会飘，
       所以这里算成最终字符串，网页那边将来也可以改成读这一份。 */
    const srcStr = (r) => {
      if (!r) return null;
      const out = [];
      (r.refs || []).forEach((x) => {
        if (x.kind === 'recipe') out.push(profNames[x.prof] || x.prof);
        else if (x.kind === 'dungeon') out.push('副本：' + (dunNames[x.id] || x.id));
        else if (x.kind === 'quest') out.push('任务奖励');
        else if (x.kind === 'vendor') out.push('商人出售');
        else if (x.kind === 'item') out.push('需要：' + ((itemsIndex[String(x.id)] || {}).name || ('#' + x.id)));
        else out.push('未说明（' + x.kind + '）');
      });
      if (r.skill != null && out.length) out[0] = out[0] + '（技能 ' + r.skill + '）';
      const seen = {};
      return out.filter((x) => { if (seen[x]) return false; seen[x] = 1; return true; }).join('，') || null;
    };
    const setOuts = [];
    bsets.forEach((st) => {
      const one = { alliance: {}, horde: {} };
      const src = { alliance: {}, horde: {} };
      const altOut = { alliance: [], horde: [] };
      const refs = st.refs || {};
      ['alliance', 'horde'].forEach((f) => {
        one[f] = {
          doll: ((st.doll || {})[f] || []).map((c) => { needItem(c.item, 'bis/set/' + st.id); return [c.slot, c.cell || 1, c.item]; }),
          alts: (function (m) {
            /* 备选表里的每个 ID 都必须进共享物品表——漏一个，玩家点开那个部位就是一格空白 */
            const out = {};
            Object.keys(m || {}).forEach((k) => {
              out[k] = (m[k] || []).map((x) => { needItem(x, 'bis/set/' + st.id + ' 备选'); return x; });
            });
            return out;
          })((st.alts || {})[f]),
          enchants: ((st.enchants || {})[f] || []).map((e) => { needItem(e.item, 'bis/set/' + st.id); return [e.item, (e.slots || []).join('、'), e.skill == null ? null : e.skill]; }),
          consumables: ((st.consumables || {})[f] || []).map((x) => { needItem(x, 'bis/set/' + st.id); return x; })
        };
        const rf = refs[f] || {};
        Object.keys(rf).forEach((k) => { needItem(k, 'bis/set/' + st.id); const v = srcStr(rf[k]); if (v) src[f][k] = v; });
        altOut[f] = (((st.alt || {})[f]) || []).map((a) => {
          if (a.item != null) needItem(a.item, 'bis/set/' + st.id);
          (a.top || []).forEach((x) => needItem(x, 'bis/set/' + st.id));
          bisAltRows += 1;
          return [a.slot, a.cell || 1, a.item == null ? null : a.item, a.same ? 'same' : 'diff', a.top || []];
        });
      });
      /* 属性合计：只加这一套 doll 里那些件的属性行（与网页同一份规则、同一次实现） */
      const sum = {};
      ['alliance', 'horde'].forEach((f) => {
        sum[f] = statParser.sumStatLines(one[f].doll.map((r) => ((itemDetailIndex[String(r[2])] || {}).st) || []));
      });
      const obj = {
        schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'bis-set', setId: st.id,
        cls: st.cls, clsCn: st.clsCn, mode: st.mode, spec: st.spec || null, level: st.level,
        fetched: st.fetched, url: st.url,
        cols: { doll: ['slot', 'cell', 'item'], enchants: ['item', 'slots', 'skill'],
          alt: ['slot', 'cell', 'item', 'state', 'top'] },
        note: 'alts 的键是参考站那套部位键（head/neck…），与纸娃娃上的中文标签靠索引里的 slotKeys 对；'
          + 'alt 是第二家名单逐格并列的结果：两家只是并列摆出来，本站不做裁决，页面用的那件与顺序仍以主源为准。',
        byFac: one, src, alt: altOut, sum,
        /* 中间那一栏的底：职业原画（与网页配装页同一张，走素材层，不热链） */
        art: ((artIndex.classes || {})[st.cls]
          ? useAsset(artIndex.classes[st.cls], 'bis/set/' + st.id + ' 职业原画') : null),
        sumNote: '只把上面这些装备的属性行相加：不含职业与种族的基础值，也不含附魔和套装效果。'
      };
      setOuts.push(obj);
      pushObj('bisSet:' + st.id, 'bis/set/' + st.id + '.json', obj, {
        records: obj.byFac.alliance.doll.length, budget: 'bisSet',
        facts: { min: st.fetched || null, max: st.fetched || null, distinct: st.fetched ? 1 : 0, recordsWithoutDate: st.fetched ? 0 : 1 }
      });
    });
    const itemRows = Object.keys(rows).sort((a, b) => Number(a) - Number(b)).map((k) => rows[k]);
    bisItemsObj = {
      schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'bis-items',
      source: 'wow-forever-web/app/data/items.json + items-detail.json（本站物品库）',
      cols: BIS_ITEM_COLS, colNote: BIS_NOTE, count: itemRows.length, items: itemRows
    };
    pushObj('bisItems', 'bis/items.json', bisItemsObj, {
      records: itemRows.length, budget: 'bisItems',
      facts: { min: (bis.meta || {}).scrapedAt || null, max: (bis.meta || {}).scrapedAt || null, distinct: 1, recordsWithoutDate: 0 }
    });
    const classes = [];
    setOuts.forEach((s) => {
      let c = classes.filter((x) => x.cls === s.cls)[0];
      /* 职业图标键随索引下发（9 个字符串，200 字节）：
         不然客户端为了画那一排图标还得先下 64 KB 的职业索引，不值 */
      if (!c) {
        const row = (classPack.classes || []).filter((x) => (x.classId || x.id) === s.cls)[0] || {};
        if (row.iconKey) useIcon(row.iconKey, 'bis/index 职业条');
        c = { cls: s.cls, clsCn: s.clsCn, iconKey: row.iconKey || null, sets: [] };
        classes.push(c);
      }
      c.sets.push(s.setId);
    });
    bisIndexObj = {
      schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'bis-index',
      source: 'wow-forever-web/app/data/bis.json',
      meta: {
        title: (bis.meta || {}).title, level: (bis.meta || {}).level,
        source: (bis.meta || {}).source, scrapedAt: (bis.meta || {}).scrapedAt,
        levelGrading: (bis.meta || {}).level_grading, gradingNote: (bis.meta || {}).gradingNote,
        basis: (bis.meta || {}).basis, counts: (bis.meta || {}).counts,
        alt: { source: ((bis.meta || {}).alt || {}).source, fetched: ((bis.meta || {}).alt || {}).fetched,
          declaredOrigin: ((bis.meta || {}).alt || {}).declaredOrigin },
        /* 红线要求的那一句原样下发，界面固定显示；措辞由分发层管，页面不许各自改写 */
        disclaimer: BIS_DISCLAIMER
      },
      slotCn: (bis.meta || {}).slotCn || {},
      slotKeys: BIS_SLOT_KEYS, slotSiblings: BIS_SLOT_SIBS,
      classes,
      sets: setOuts.map((s) => ({
        id: s.setId, cls: s.cls, clsCn: s.clsCn, mode: s.mode, level: s.level,
        fetched: s.fetched, url: s.url, path: 'bis/set/' + s.setId + '.json'
      }))
    };
    pushObj('bisIndex', 'bis/index.json', bisIndexObj, {
      records: setOuts.length, budget: 'bis/index',
      facts: { min: (bis.meta || {}).scrapedAt, max: (bis.meta || {}).scrapedAt,
        distinct: 1, recordsWithoutDate: (bis.meta || {}).scrapedAt ? 0 : setOuts.length }
    });
    /* 配装线的红线扫描：这些产物是给玩家看的，出现几率、秒伤、"更好 N%"这类话就是撞线。
       名字里带百分号的游戏物品不在其列，所以只扫"数字 + %"与那几个词。 */
    /* 扫的是本站自己写的字：说明句、来源串、部位名、模式名。
       bis/items.json 那一层是游戏物品的属性行原文（套装效果里就有"5% 几率"这种话），
       拿这条去扫它等于把游戏原文当违规——掉落线那次已经犯过一回，别再犯。 */
    entries.forEach((e) => {
      if (!e.obj || (e.key !== 'bisIndex' && String(e.key).indexOf('bisSet:') !== 0)) return;
      const t = JSON.stringify(e.obj);
      if (/\d+(\.\d+)?\s*%/.test(t)) errors.push('配装：' + e.path + ' 出现百分比（红线：掉落/推荐不写几率）');
      if (/秒伤|DPS|权重|更好|优于/.test(t)) errors.push('配装：' + e.path + ' 出现强度评价类词（红线：本站不自建强度评分、不做循环提示）');
    });
    /* 悬空引用：分片里每个 ID 都必须在共享物品表里有行，否则玩家点开的是一格空白 */
    entries.forEach((e) => {
      if (!e.obj || e.obj.kind !== 'bis-set') return;
      const ids = [];
      ['alliance', 'horde'].forEach((f) => {
        const b = e.obj.byFac[f];
        (b.doll || []).forEach((r) => ids.push(r[2]));
        (b.enchants || []).forEach((r) => ids.push(r[0]));
        (b.consumables || []).forEach((x) => ids.push(x));
        Object.keys(b.alts || {}).forEach((k) => (b.alts[k] || []).forEach((x) => ids.push(x)));
        (e.obj.alt[f] || []).forEach((r) => { if (r[2] != null) ids.push(r[2]); (r[4] || []).forEach((x) => ids.push(x)); });
      });
      const lost = ids.filter((x) => !rows[String(x)]);
      if (lost.length) errors.push('配装：' + e.path + ' 有 ' + lost.length + ' 个物品 ID 在共享物品表里没有行（本站名录缺件）：' + lost.slice(0, 3).join(','));
    });
  } else {
    errors.push('缺少配装基底 app/data/bis.json，配装线没有数据来源');
  }

  /* —— 专业与配方（2026-10-27）：与网页 app/src/pages/ProfessionsPage.vue 同一份口径 ——
     基底 1.5 MB / 1990 条配方不能整份塞进手机：索引一片（13 个专业 + 分箱 + 列名 + 出处），
     每个专业自成一格（图标 / 材料 / 商人 / 图纸字典就地带，点开哪个下哪个），
     行用位置数组存——与掉落反查、配装那两条同一个写法。 */
  const profPack = fs.existsSync(profSrc) ? readJson(profSrc) : null;
  let profIndexObj = null;
  const profStat = { recipes: 0, newRecipes: 0, nodes: 0, noBand: 0, noIcon: 0 };
  if (profPack) {
    const pList = profPack.professions || [];
    const pm = profPack.meta || {};
    if (!pList.length) errors.push('专业：基底里一个专业都没有');
    /* 分箱必须连续盖住 1–300：漏一档就等于把那一段配方静默吞进兜底箱 */
    let cursor = 1;
    PROF_BANDS.forEach((b) => {
      if (b[0] !== cursor) errors.push('专业分箱不连续：上一箱收到 ' + (cursor - 1) + '，这一箱从 ' + b[0] + ' 起（' + b[2] + '）');
      cursor = b[1] + 1;
    });
    if (cursor !== 301) errors.push('专业分箱没盖到 300（收到 ' + (cursor - 1) + '）');

    const setsOut = [];
    pList.forEach((p) => {
      if (!/^[a-z0-9][a-z0-9-]*$/.test(String(p.id || ''))) { errors.push('专业 id ' + p.id + ' 含不能作为文件名的字符'); return; }
      const icons = []; const iconIx = {};
      const mats = []; const matIx = {};
      const vends = []; const vndIx = {};
      const drops = []; const dropIx = {};
      const srcs = []; const srcIx = {};
      const put = (arr, map, key, val) => {
        if (!Object.prototype.hasOwnProperty.call(map, key)) { map[key] = arr.length; arr.push(val); }
        return map[key];
      };
      /* 图标键是空串 = 这条数据本来就没有图：编成 -1，界面画自绘块，不许猜一张 */
      const iconOf = (k) => { const s = String(k || ''); if (!s) { profStat.noIcon += 1; return -1; } return put(icons, iconIx, s, s); };
      const matOf = (m) => put(mats, matIx, JSON.stringify([String(m.nameCn || ''), String(m.iconKey || '')]),
        [String(m.nameCn || ''), iconOf(m.iconKey)]);
      const vndOf = (v) => put(vends, vndIx, JSON.stringify([String(v.name || ''), String(v.zone || '')]),
        [String(v.name || ''), String(v.zone || '')]);
      const dropOf = (x) => put(drops, dropIx, JSON.stringify([String(x.npc || ''), String(x.zone || '')]),
        [String(x.npc || ''), String(x.zone || '')]);
      const recipes = (p.recipes || []).map((r) => {
        const sk = r.skill || {};
        const matFlat = [];
        (r.mats || []).forEach((m) => { matFlat.push(matOf(m), m.count == null ? 1 : m.count); });
        const orange = typeof sk.orange === 'number' ? sk.orange : null;
        if (orange === null || !PROF_BANDS.some((b) => orange >= b[0] && orange <= b[1])) profStat.noBand += 1;
        if (r.isNew) profStat.newRecipes += 1;
        return [String(r.itemId), String(r.nameCn || ''), iconOf(r.iconKey), r.quality || 0, r.isNew ? 1 : 0,
          matFlat, PROF_SK_COLS.map((k) => (typeof sk[k] === 'number' ? sk[k] : null)),
          r.source == null ? -1 : put(srcs, srcIx, String(r.source), String(r.source)),
          (r.vendors || []).map((v) => vndOf(v)), (r.formulaDrops || []).map((x) => dropOf(x)),
          r.srcFrom === 'xr' ? 1 : 0, r.vMore || 0, r.dMore || 0];
      });
      const nodes = (p.nodes || []).map((n) => {
        const sk = n.skill || null;
        return [String(n.nameCn || ''), iconOf(n.iconKey), (n.yields || []).map((y) => String(y)),
          String(n.zone || ''), sk ? PROF_SK_COLS.map((k) => (typeof sk[k] === 'number' ? sk[k] : null)) : null];
      });
      /* 基底自己报的数与实际拆出来的数对不上 = 这一版拆漏了，宁可红也不静默少条目 */
      const c = p.counts || {};
      if (c.recipes !== recipes.length) errors.push('专业 ' + p.id + '：基底自报 ' + c.recipes + ' 条配方，实际拆出 ' + recipes.length + ' 条');
      if (c.nodes !== nodes.length) errors.push('专业 ' + p.id + '：基底自报 ' + c.nodes + ' 个采集点，实际拆出 ' + nodes.length + ' 个');
      profStat.recipes += recipes.length;
      profStat.nodes += nodes.length;

      const obj = {
        /* 列名与那份列说明只在索引里写一份：13 片各抄一遍等于把同一句话复制 13 次，
           改一处漏十二处。客户端是先读索引、再点分片的，取得到。 */
        schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'professions-set', profId: p.id,
        icons, mats, vendors: vends, drops, sources: srcs,
        recipes, nodes,
        counts: { recipes: recipes.length, nodes: nodes.length }
      };
      icons.forEach((k) => useIcon(k, 'professions/set/' + p.id));
      setsOut.push(obj);
      pushObj('profSet:' + p.id, 'professions/set/' + p.id + '.json', obj, {
        records: recipes.length + nodes.length, budget: 'profSet', facts: collectFactDates([p]), flat: true
      });
    });

    profIndexObj = {
      schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'professions-index',
      source: 'wow-forever-web/app/data/professions.json',
      meta: {
        generatedAt: pm.generatedAt || null, kind: pm.kind || null,
        title: PROF_TITLE,
        /* 这里刻意不下发 pm.method（"tools/scrape-wclbox-prof.py → tools/merge-professions.js"）：
           那是本站的取数工序，玩家界面看了只会莫名其妙，出处集中在网页的溯源页。
           2026-10-27 实拍里它被当副标题渲染出来了，才补的这条。 */
        took: pm.took || null, sources: pm.sources || [],
        /* 红线要的那句与分级在分发层写一次，页面不许各自改写措辞 */
        disclaimer: PROF_DISCLAIMER, levelNote: pm.levelNote || null
      },
      bands: PROF_BANDS, bandNote: PROF_BAND_NOTE,
      cols: { recipe: PROF_REC_COLS, node: PROF_NODE_COLS, mat: PROF_MAT_COLS, sk: PROF_SK_COLS },
      colNote: PROF_COL_NOTE,
      skillKeys: PROF_SK_KEYS.map((x) => ({ k: x[0], cn: x[1] })),
      /* 采集表表头那几个专业用的是自己的叫法（草药点 / 水域），与网页同一份 */
      nodeHeadLabels: { herbalism: '草药点', fishing: '水域' },
      headIcon: PROF_HEAD_ICON,
      /* 这一页的条目全是客户端解包出来的游戏内中文名（经第三方转述）→ L0；
         分级由基底逐条带（level），构建时数一遍：出现非 L0 就报出来，别整页冒充已核 */
      levels: pList.reduce((m, p) => { const k = String(p.level || '未标'); m[k] = (m[k] || 0) + 1; return m }, {}),
      professions: pList.map((p) => ({
        id: p.id, nameCn: p.nameCn, nameEn: p.nameEn || null, kind: p.kind || null,
        unparsed: !!p.unparsed, note: p.note || null, level: p.level || '未标',
        levelNote: p.levelNote || null, counts: p.counts || {},
        prov: p.provenance || [], path: 'professions/set/' + p.id + '.json'
      })),
      counts: {
        professions: pList.length,
        craft: pList.filter((p) => (p.kind || '') !== 'gather').length,
        gather: pList.filter((p) => (p.kind || '') === 'gather').length,
        recipes: profStat.recipes, newRecipes: profStat.newRecipes, nodes: profStat.nodes,
        rowsWithoutBand: profStat.noBand, rowsWithoutIcon: profStat.noIcon,
        shards: setsOut.length
      }
    };
    useIcon(PROF_HEAD_ICON, 'professions/index 板块图');
    pushObj('professionsIndex', 'professions/index.json', profIndexObj, {
      records: pList.length, budget: 'professions/index', facts: collectFactDates(pList)
    });
    /* 专业线的红线扫描：这些产物是给玩家看的，出现百分比、秒伤、"更好 N%"这类话就是撞线。
       与配装那条不同的是：这一页没有游戏原文那层（属性行不下发），所以整片都能扫。 */
    entries.forEach((e) => {
      if (!e.obj || (e.key !== 'professionsIndex' && String(e.key).indexOf('profSet:') !== 0)) return;
      const t = JSON.stringify(e.obj);
      if (/\d+(\.\d+)?\s*%/.test(t)) errors.push('专业：' + e.path + ' 出现百分比（红线：不给掉率、不做性价比建议）');
      if (/秒伤|DPS|权重|更好|优于|推荐顺序|性价比/.test(t)) errors.push('专业：' + e.path + ' 出现强度/攻略类词（红线：不做强度评分与冲级建议）');
    });
    /* 名字不许在索引和分片里各写一遍：分片只带数据，页头那几个字段一律从索引读 */
    setsOut.forEach((s) => {
      const bad = s.recipes.filter((r) => !r[0] || !r[1]).length;
      if (bad) errors.push('专业 ' + s.profId + '：' + bad + ' 条配方没有物品 ID 或名字（宁可少一条，不许拼一行空的）');
      const lostMat = s.recipes.filter((r) => r[5].length % 2 !== 0).length;
      if (lostMat) errors.push('专业 ' + s.profId + '：' + lostMat + ' 条配方的材料平铺数组是奇数（序号/数量配不上对）');
      const oob = s.recipes.filter((r) => r[2] >= s.icons.length || r[2] < -1).length;
      if (oob) errors.push('专业 ' + s.profId + '：' + oob + ' 条配方指向不存在的图标序号');
    });
  } else {
    errors.push('缺少专业基底 app/data/professions.json，专业线没有数据来源');
  }

  /* ---------- 3·4. 宏命令线（2026-10-30，网页那 245 条已经上线）----------
     数据真源只有一份：app/data/macros.json（网页宏页吃的就是它）。
     PLAN 当初写的是"沿用 guide.json.macros"，但那条一直是空的，宏实际落在了 macros.json，
     所以这里跟着真源走，不再复制第二份——同一批宏在两端各存一份迟早对不上。
     一片一类（9 片），点哪个职业才取哪一片；宏正文原样保留换行，界面只读＋复制。 */
  const macroSrcPath = path.join(siteData(), 'macros.json');
  const macroSrc = fs.existsSync(macroSrcPath) ? readJson(macroSrcPath) : null;
  let macroIndexObj = null;
  if (macroSrc && Array.isArray(macroSrc.macros)) {
    const ms = macroSrc.macros;
    const seenId = {};
    const srcs = (macroSrc.meta && macroSrc.meta.sources) || [];
    const srcIdx = {};
    srcs.forEach((x, i) => { srcIdx[x.key] = i; });
    const classIds = {}
    const groups = []
    const byClass = []
    let dropped = 0
    ms.forEach((m) => {
      const id = String(m.id || '')
      if (!id || seenId[id]) { errors.push('宏：id 空或重复（' + (id || '(空)') + '）'); return }
      seenId[id] = 1
      if (!m.classId || !CLASS_IDS.includes(m.classId)) { errors.push('宏 ' + id + ' 的 classId 不是本站九职业之一：' + m.classId); return }
      if (!String(m.title || '').trim()) errors.push('宏 ' + id + ' 没有标题')
      if (!String(m.body || '').trim()) { errors.push('宏 ' + id + ' 没有宏正文（宁可少一条，不许给一条空的）'); return }
      if (!String(m.group || '').trim()) errors.push('宏 ' + id + ' 没有用途分组')
      if (/秒伤|DPS|权重|更好|优于|推荐顺序|性价比|循环提示/.test(String(m.title) + String(m.note))) errors.push('宏 ' + id + ' 的标题/说明是强度或循环指导（红线不做）')
      const prov = (m.provenance || []).filter((x) => x && x.url && x.checkedAt)
      if (!prov.length) { dropped += 1; return }   /* 没来源的按"待核"不下发（PLAN 那条口径） */
      classIds[m.classId] = (classIds[m.classId] || 0) + 1
      if (groups.indexOf(m.group) < 0) groups.push(m.group)
      const row = [id, m.title, m.group, m.note || null, m.body, m.minLevel == null ? null : m.minLevel,
        m.foreverNew ? 1 : 0, srcIdx[prov[0].key] == null ? null : srcIdx[prov[0].key], m.nameFrom || null]
      let b = byClass.filter((x) => x.classId === m.classId)[0]
      if (!b) { b = { classId: m.classId, className: m.className || m.classId, rows: [] }; byClass.push(b) }
      if (b.className !== (m.className || b.className)) b.className = b.className || m.className
      b.rows.push(row)
    })
    if (dropped) console.log('  · 宏：' + dropped + ' 条没有可追的来源（url + 核对日），按"待核"不下发')
    /* 职业图标不自己造名字：吃 classIndex 那份（同一批里已经登记过的 iconKey），
       两处各写一套 "class_warrior" 这种字符串，迟早一端漂了另一端还绿着 */
    const classIcon = {}
    ;((classIndexObj || {}).classes || []).forEach((c) => { classIcon[c.classId] = c.iconKey || null })
    const setsOut = []
    byClass.sort((a, b) => CLASS_IDS.indexOf(a.classId) - CLASS_IDS.indexOf(b.classId)).forEach((c) => {
      const obj = {
        schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'macros-class',
        classId: c.classId, className: c.className, srcs: srcs, rows: c.rows,
        counts: { macros: c.rows.length }
      }
      setsOut.push(obj)
      pushObj('macroClass:' + c.classId, 'macros/set/' + c.classId + '.json', obj, {
        records: c.rows.length, budget: 'macroClass', facts: collectFactDates(srcs), flat: true
      })
    })
    macroIndexObj = {
      schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'macros-index',
      source: 'wow-forever-web/app/data/macros.json',
      meta: {
        generatedAt: (macroSrc.meta || {}).generatedAt || null,
        checkedAt: (macroSrc.meta || {}).checkedAt || null,
        title: MACRO_TITLE,
        /* 口径句与免责由分发层写一次，页面不许各自改写措辞（红线：不冒充实测、不收费、不分发插件） */
        disclaimer: MACRO_DISCLAIMER,
        pageNote: (macroSrc.meta || {}).pageNote || null,
        licenseNote: (macroSrc.meta || {}).licenseNote || null,
        sources: srcs
      },
      cols: MACRO_COLS, colNote: MACRO_COL_NOTE,
      groups: groups,
      levels: ms.reduce((o, m) => { const k = String(m.level || '未标'); o[k] = (o[k] || 0) + 1; return o }, {}),
      classes: byClass.map((c) => {
        const iconKey = classIcon[c.classId] || null
        if (!iconKey) errors.push('宏：职业 ' + c.classId + ' 在 classIndex 里没有图标键，职业条会缺图')
        else useIcon(iconKey, 'macros/index')
        return {
          classId: c.classId, className: c.className, count: c.rows.length,
          iconKey: iconKey, path: 'macros/set/' + c.classId + '.json'
        }
      }),
      counts: {
        macros: ms.length, sent: byClass.reduce((t, c) => t + c.rows.length, 0),
        classes: byClass.length, groups: groups.length,
        foreverNew: ms.filter((m) => m.foreverNew).length, droppedNoSource: dropped
      }
    }
    pushObj('macrosIndex', 'macros/index.json', macroIndexObj, {
      records: byClass.length, budget: 'macros/index', facts: collectFactDates(srcs)
    })
    /* 红线扫描：宏这一页最容易撞的是"强度建议 / 循环提示 / 收费"这三条。
       两条口径要写清楚，别一刀切：
       ① 我们自己的口径句（disclaimer/pageNote/licenseNote 里"不做循环提示类宏""不收费"）
          不能被当成撞线——所以只扫行数据与分组名，不扫 meta；
       ② 红线拦的是"本站算出来的掉率与强度评分"，不是插件抄来的技能效果句。
          "断筋减速 40%""威慑 +25% 躲闪"这类是技能自己的数值，网页那 245 条已按这个口径上线，
          小程序不另立一条更严的、把同一条内容判成两边不一致。
          但**宏正文**（要粘进游戏的那几行）里出现 % 一定是异常，照拦。 */
    entries.forEach((e) => {
      if (!e.obj || (e.key !== 'macrosIndex' && String(e.key).indexOf('macroClass:') !== 0)) return
      const body = e.key === 'macrosIndex'
        ? JSON.stringify({ groups: e.obj.groups, classes: e.obj.classes, counts: e.obj.counts })
        : JSON.stringify(e.obj.rows)
      if (/秒伤|DPS|权重|更好|优于|推荐顺序|性价比|循环提示/.test(body)) errors.push('宏：' + e.path + ' 出现强度/循环指导类词（红线不做这些）')
      if (/收费|购买|会员|付费/.test(body)) errors.push('宏：' + e.path + ' 出现交易类词（宏一律免费列）')
      if (e.key !== 'macrosIndex' && /https?:\/\//.test(body)) errors.push('宏：' + e.path + ' 行数据里出现链接（小程序不做跳转）')
    })
    macroIndexObj.counts.percentInNotes = ms.filter((m) => /\d+(\.\d+)?\s*%/.test(String(m.note || '') + String(m.title || ''))).length
    ms.forEach((m) => {
      if (/\d+(\.\d+)?\s*%/.test(String(m.body || ''))) errors.push('宏 ' + m.id + ' 的正文里出现百分比（正文是要原样粘进游戏的命令）')
    })
    setsOut.forEach((s) => {
      const badBody = s.rows.filter((r) => !String(r[4] || '').trim()).length
      if (badBody) errors.push('宏 ' + s.classId + '：' + badBody + ' 条正文是空的')
      const noSrc = s.rows.filter((r) => r[7] == null || !s.srcs[r[7]]).length
      if (noSrc) errors.push('宏 ' + s.classId + '：' + noSrc + ' 条指不到来源条目（不许无出处下发）')
    })
  } else {
    errors.push('缺少宏基底 app/data/macros.json，宏命令页没有数据来源')
  }

  const byKey = {};
  entries.forEach((e) => { byKey[e.key] = e; });
  entries.forEach((e) => {
    e.preBuf = e.buf || (e.flat ? dumpFlat(e.obj) : dump(e.obj));
    e.contentSha = sha256(e.preBuf);
  });
  /* buildId 必须把"生成器自己"也算进指纹。
     2026-10-21 踩过：只按注入前内容算指纹时，给产物新增一个校验字段（内容没变、字节变了）
     会得到同一个 buildId 配不同字节，正好是"不可变批次"最坏的破法——上传时被拦截才发现。
     现在生成器一改，指纹就变，同 buildId 必然同字节。 */
  const builderSha = sha256(fs.readFileSync(__filename)).slice(0, 12);
  const digest = entries.slice().sort((a, b) => (a.path < b.path ? -1 : 1)).map((e) => e.path + ':' + e.contentSha).join('\n');
  const buildId = sha256(Buffer.from([PRODUCT, SCHEMA_VERSION, 'gen=' + builderSha, digest].join('|'), 'utf8')).slice(0, 12);

  /* 先给所有生成的分片注入 buildId，再算详情/掉落的最终字节给索引当校验值，
     最后统一出 buf/bytes/sha256/etag——这一步没有随机因素，重跑必得同样字节。 */
  entries.forEach((e) => { if (e.obj) e.obj.buildId = buildId; });
  indexObj.items.forEach((it) => {
    const dBuf = dump(byKey['dungeonDetail:' + it.id].obj);
    const lBuf = dump(byKey['dungeonLoot:' + it.id].obj);
    const dm = md5Of(dBuf); const lm = md5Of(lBuf);
    it.detailEtag = dm.etag; it.detailMd5 = dm.md5; it.detailBytes = dBuf.length;
    it.lootEtag = lm.etag; it.lootMd5 = lm.md5; it.lootBytes = lBuf.length;
  });
  /* 职业分片同理：校验值随职业名单一起下发，客户端点开哪个职业才取哪一片，
     不必先下 files.json 才能校验 */
  spellIndexObj.classes.forEach((it) => {
    const sBuf = dump(byKey['spellClass:' + it.classId].obj);
    const sm = md5Of(sBuf);
    it.shardEtag = sm.etag; it.shardMd5 = sm.md5; it.shardBytes = sBuf.length;
  });
  classIndexObj.classes.forEach((it) => {
    if (!it.shardPath) return;
    const tBuf = dump(byKey['talentClass:' + it.classId].obj);
    const tm = md5Of(tBuf);
    it.shardEtag = tm.etag; it.shardMd5 = tm.md5; it.shardBytes = tBuf.length;
  });
  /* 配装：每套的校验值随索引下发，客户端点开哪套取哪片——与副本详情/掉落同一套契约 */
  if (bisIndexObj) {
    bisIndexObj.sets.forEach((it) => {
      const e = byKey['bisSet:' + it.id];
      if (!e) { errors.push('配装索引里 ' + it.id + ' 没有对应的分片'); return; }
      const sBuf = dump(e.obj);
      const sm = md5Of(sBuf);
      it.shardEtag = sm.etag; it.shardMd5 = sm.md5; it.shardBytes = sBuf.length;
    });
  }
  /* 专业：校验值随索引下发，点开哪个专业取哪一片（同一套契约） */
  if (profIndexObj) {
    profIndexObj.professions.forEach((it) => {
      const e = byKey['profSet:' + it.id];
      if (!e) { errors.push('专业索引里 ' + it.id + ' 没有对应的分片'); return; }
      const sBuf = dumpFlat(e.obj);
      const sm = md5Of(sBuf);
      it.shardEtag = sm.etag; it.shardMd5 = sm.md5; it.shardBytes = sBuf.length;
    });
   }

  if (macroIndexObj) {
    macroIndexObj.classes.forEach((it) => {
      const e = byKey['macroClass:' + it.classId];
      if (!e) { errors.push('宏索引里 ' + it.classId + ' 没有对应的职业片'); return; }
      const sBuf = dumpFlat(e.obj);
      const sm = md5Of(sBuf);
      it.shardEtag = sm.etag; it.shardMd5 = sm.md5; it.shardBytes = sBuf.length;
    });
  }

  /* 素材层的反向卡口：凡是界面会拼出来的地址（iconKey / art / portrait），
     这一批必须登记过。漏登记不会让谁报错，只会让玩家永远看到自绘占位块——
     2026-10-22 职业图标就是这么漏的：素材层报"缺登记 0 条"，线上却 404。 */
  const refAssets = {};
  const walkAssets = (node, where) => {
    if (Array.isArray(node)) { node.forEach((x) => walkAssets(x, where)); return; }
    if (!node || typeof node !== 'object') return;
    Object.keys(node).forEach((k) => {
      const v = node[k];
      if ((k === 'iconKey' && typeof v === 'string' && v) || ((k === 'art' || k === 'portrait') && typeof v === 'string' && v)) {
        const rel = k === 'iconKey' ? 'icons/' + v + ICON_EXT : v;
        if (!refAssets[rel]) refAssets[rel] = where;
      } else {
        walkAssets(v, where);
      }
    });
  };
  entries.forEach((e) => { if (e.obj) walkAssets(e.obj, e.path); });
  Object.keys(refAssets).forEach((rel) => {
    if (!assetUse[rel]) errors.push('界面会去要 ' + rel + '（出自 ' + refAssets[rel] + '），但素材层没登记 —— 玩家只会看到自绘占位块');
  });

  /* 装备详情卡口：掉落行有 itemId 却没配上详情行，玩家点进去就是一屏空白。
     件数逐座要对上；行是位置数组，所以长度对 cardCols、第一格对 itemId——
     列名漂了客户端就会把装等当卖价。 */
  let cardRows = 0;
  entries.forEach((e) => {
    if (!e.obj || e.obj.kind !== 'dungeon-loot') return;
    const withId = (e.obj.drops || []).filter((x) => x.itemId);
    const cards = e.obj.cards || [];
    if (withId.length !== cards.length) {
      errors.push('装备详情：' + e.obj.dungeonId + ' 掉落有 ' + withId.length + ' 件带 itemId，详情只有 ' + cards.length + ' 行');
    }
    if ((e.obj.cardCols || []).join(',') !== CARD_COLS.join(',')) {
      errors.push('装备详情：' + e.obj.dungeonId + ' 的列名与生成器里的 CARD_COLS 不一致');
    }
    const dropIds = {};
    (e.obj.drops || []).forEach((x) => { if (x.itemId) dropIds[String(x.itemId)] = 1; });
    cards.forEach((r, i) => {
      const at = '装备详情：' + e.obj.dungeonId + ' 第 ' + (i + 1) + ' 行';
      if (r.length !== CARD_COLS.length) errors.push(at + '有 ' + r.length + ' 个值，列名却写了 ' + CARD_COLS.length + ' 列');
      if (!r[0]) errors.push(at + '缺 itemId');
      if (!dropIds[String(r[0])]) errors.push(at + '（' + r[0] + '）在这座的掉落里找不到，客户端归不上行');
      if (/\d+(\.\d+)?\s*%/.test(String(r[4] || ''))) errors.push(at + '的卖价里出现百分比（红线：不写几率）');
      cardRows += 1;
    });
  });

  entries.forEach((e) => {
    if (!e.buf) e.buf = e.flat ? dumpFlat(e.obj) : dump(e.obj);
    e.bytes = e.buf.length;
    e.sha256 = sha256(e.buf);
    e.etag = md5Hex(e.buf);
    e.md5 = md5B64(e.buf);
    e.cacheControl = IMUTABLE_CACHE;
    if (/"(img|src|static)\//.test(e.buf.toString('utf8'))) {
      errors.push('文件 ' + e.path + ' 里还留着站内相对路径（img/ 或 src/ 开头），小程序打不开，必须先摘掉');
    }
    const limit = BUDGET_KB[e.budget] || 0;
    if (limit && e.bytes > limit * 1024) {
      errors.push('文件 ' + e.path + ' 体积 ' + kb(e.bytes) + ' KB 超预算 ' + limit + ' KB');
    }
  });

  /* 指针清单要小到可以在冷启动时随手取：79 个文件的逐条哈希不塞在这里，
     放进批次内的 files.json（路径带 buildId，永不变，可以硬缓存）。 */
  const bundle = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    buildId,
    kind: 'batch-files',
    note: '这一批每个文件的 SHA-256、ETag、字节数与条数。正常取数不必下载它：入口文件的校验值在指针里，详情/掉落的在索引条目里。',
    cacheControl: IMUTABLE_CACHE,
    files: {}
  };
  entries.forEach((e) => {
    bundle.files[e.key] = { path: e.path, sha256: e.sha256, etag: e.etag, md5: e.md5, bytes: e.bytes, records: e.records, facts: e.facts };
  });
  const bundleBuf = dump(bundle);
  const bundlePath = 'builds/' + buildId + '/files.json';

  const pickFile = (key) => entries.filter((e) => e.key === key)[0];
  const shared = (e) => ({ path: 'builds/' + buildId + '/' + e.path, sha256: e.sha256, etag: e.etag, md5: e.md5, bytes: e.bytes, records: e.records });
  const mins = [];
  const maxs = [];
  entries.forEach((e) => { const f = e.facts || {}; if (f.min) mins.push(f.min); if (f.max) maxs.push(f.max); });
  mins.sort();
  maxs.sort();
  const detailFacts = collectFactDates(list);

  const manifest = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    env,
    namespace: ns,
    buildId,
    /* 这里刻意没有任何时间字段：同一 buildId 的清单必须逐字节恒定，
       否则"不可变批次"会被自己每次重建的时间戳覆写，回滚位的字节一致性也就没意义了。
       发布时刻看对象的服务端 Last-Modified 与本地 oss-build/{env}/last-upload.json。 */
    timeNote: '本清单没有生成时间字段（同 buildId 必须字节恒定）。数据何时核对看 factDates 与每条 provenance；这批何时发布看对象的服务端 Last-Modified。',
    minClientSchemaVersion: 1,
    source: {
      commit,
      inputs: srcFiles,
      inputsNote: '这里哈希的是站点基底 app/data 的原件；批次文件由 export-mini.js 从这些原件派生，构建时已在临时目录重导一遍并逐字节对拍（见 exportCheck）。',
      generator: { tool: 'wow-forever-web/tools/oss-release.js', sha256: builderSha,
        note: 'buildId 的指纹里含生成器自身的哈希：生成逻辑变了就换批次号，同 buildId 不可能出现不同字节。' },
      exportCheck
    },
    counts: {
      dungeons: list.length,
      terms: (glossary.items || []).length,
      spells: spellList.length,
      spellClasses: spellGroups.length,
      lootRows: lootObj.counts.rows,
      lootItems: lootObj.counts.items,
      /* 掉落行里带上了装备详情卡的条数（构建时逐行数出来的，不是抄 lootRows） */
      itemCards: cardRows,
      itemCardNoDetail: itemCardMiss.noDetail,
      /* 配装线：套数 / 共享表件数 / 第二家逐格并列的行数（都是构建时数出来的，不是抄 meta.counts） */
      bisSets: bisIndexObj ? bisIndexObj.sets.length : 0,
      bisItems: bisItemsObj ? bisItemsObj.count : 0,
      bisAltRows,
      bisItemNoBase: (typeof itemMiss !== 'undefined' && itemMiss) ? itemMiss.noBase : 0,
      /* 专业线：专业数 / 配方数 / 无限新增 / 采集点 / 分片数（全部构建时数出来，不抄基底 counts） */
      professions: profIndexObj ? profIndexObj.counts.professions : 0,
      profRecipes: profIndexObj ? profIndexObj.counts.recipes : 0,
      profNewRecipes: profIndexObj ? profIndexObj.counts.newRecipes : 0,
      profNodes: profIndexObj ? profIndexObj.counts.nodes : 0,
      profShards: profIndexObj ? profIndexObj.counts.shards : 0,
      /* 宏命令线：发出去的条数与职业片数（构建时数）。
         注意别和下面那个 `macros` 撞名——那个是旧指南页 guide.json.macros 的条数，至今 0 条。 */
      macroSent: macroIndexObj ? macroIndexObj.counts.sent : 0,
      macroClasses: macroIndexObj ? macroIndexObj.counts.classes : 0,
      races: classIndexObj.counts.races,
      classes: classIndexObj.counts.classes,
      macros: (guidePack.macros || []).length,
      addons: (guidePack.addons || []).length,
      files: entries.length + 2,
      bytes: entries.reduce((s, e) => s + e.bytes, 0) + bundleBuf.length
    },
    factDates: {
      min: mins.length ? mins[0] : null,
      latest: maxs.length ? maxs[maxs.length - 1] : null,
      dungeonDetail: detailFacts,
      note: '取数据里 provenance.checkedAt 的真实日期；null 表示这批里还有条目没有核对日期，界面要写「未记录」。'
    },
    droppedFields: DROPPED_DETAIL_FIELDS,
    assetNote: ASSET_NOTE,
    assets: {
      dir: ASSET_DIR + '/',
      iconExt: ICON_EXT,
      index: ASSET_DIR + '/index.json',
      count: Object.keys(assetUse).length,
      bytes: Object.keys(assetUse).reduce((t, k) => t + assetUse[k].bytes, 0),
      missing: assetMissing.length,
      rule: 'art 与 bosses[].portrait 的值是相对 assets/ 的路径；图标只用 key 拼 assets/icons/{key}' + ICON_EXT + '。'
        + '客户端拼出来的地址必须落在 assets/ 下，出现 img/ 或 .. 就是数据被改过。'
    },
    integrity: {
      method: 'etag',
      clientChecks: [
        '指针里 fetch.* 与 bundle 都带 Content-MD5(base64) + ETag(hex) + bytes：入口文件（meta / glossary / dungeons/index / spells/classes）按指针给的值校验',
        '客户端优先比响应的 Content-MD5，退化才比 ETag——真 bucket 上 wx.request 收到 gzip 变体时 ETag 会被剥掉，只剩 Content-MD5（2026-10-21 实测）',
        '索引每条自带 detailEtag / detailBytes / lootEtag / lootBytes：进详情、看掉落时按索引给的值校验，不必先取 files.json',
        '职业分片的校验值随 spells/classes.json 的每个职业条目下发（shardEtag / shardMd5 / shardBytes），点开哪个职业才取哪一片',
        '掉落反查表 loots/index.json 是一个整块：一次 GET 换"任何一件装备都能查"，行用位置数组存，列名写在 cols 里',
        '每件装备的详情行（属性行/装等/卖价/状态）与掉落名单同在 dungeons/loot/{id}.json：点的那件一定在刚打开的这座本里，不再发第二次请求',
        '这一批的每个文件都带 buildId / product / schemaVersion / kind（副本类分片还带所属副本 id，职业分片带 classId），客户端五项齐验：etag、bytes、buildId、kind、id',
        '分片路径由条目里的 id 现推并与 detailPath/lootPath/shardPath 比对，对不上就不发请求——写坏一条路径也走不出 builds/{buildId}/',
        '任一项不符就整条当失败，走缓存或打包快照并在界面标出来，不许拿对不上内容的数据当实时'
      ],
      whatItIsNot: '这是"取回的字节是不是清单里那一份"的传输/存储完整性校验（比对服务器自己算的 MD5 ETag），不是抗伪造的内容签名，也不保证上游没写错事实——事实靠 provenance 与红线卡口。',
      serverSide: '逐文件 SHA-256 由构建端算、写进 files.json，并由 `verify` 子命令在发布后逐个回读比对。',
      trustRoot: '指针 manifest.json 自己不做哈希自证：它是信任根，靠 HTTPS + bucket 权限 + max-age=60 的新鲜度。'
    },
    pointer: { key: ns + '/manifest.json', cacheControl: POINTER_CACHE },
    fetch: {
      meta: shared(pickFile('meta')),
      glossary: shared(pickFile('glossary')),
      dungeonIndex: shared(pickFile('dungeonIndex')),
      spellClasses: shared(pickFile('spellClasses')),
      lootIndex: shared(pickFile('lootIndex')),
      classIndex: shared(pickFile('classIndex')),
      guide: shared(pickFile('guide')),
      bisIndex: bisIndexObj ? shared(pickFile('bisIndex')) : undefined,
      bisItems: bisItemsObj ? shared(pickFile('bisItems')) : undefined,
      professionsIndex: profIndexObj ? shared(pickFile('professionsIndex')) : undefined,
      macrosIndex: macroIndexObj ? shared(pickFile('macrosIndex')) : undefined
    },
    bundle: { path: bundlePath, sha256: sha256(bundleBuf), etag: md5Hex(bundleBuf), md5: md5B64(bundleBuf), bytes: bundleBuf.length }
  };

  if (manifest.counts.bytes && Buffer.byteLength(JSON.stringify(manifest, null, 1)) > BUDGET_KB.manifest * 1024) {
    errors.push('指针清单超过 ' + BUDGET_KB.manifest + ' KB，冷启动代价太大，把明细挪进 bundle');
  }
  if (bundleBuf.length > BUDGET_KB.bundle * 1024) errors.push('files.json 超过 ' + BUDGET_KB.bundle + ' KB');
  if (errors.length) return { errors };
  return { errors: [], buildId, ns, entries, manifest, bundleBuf, bundlePath, assetUse, assetMissing };
}

function writeBatch(env, built, flags) {
  const dir = path.join(buildRoot(), env, 'builds', built.buildId);
  built.entries.forEach((e) => writeBuf(path.join(dir, e.path), e.buf));
  writeBuf(path.join(dir, 'files.json'), built.bundleBuf);
  const manifestBuf = dump(built.manifest);
  writeBuf(path.join(dir, 'manifest.json'), manifestBuf);
  const pointer = path.join(buildRoot(), env, 'manifest.json');
  writeBuf(pointer, manifestBuf);
  /* 开关与指针同一档：本地假 OSS（tools/oss-fake-server.js）直接按文件发，
     所以门禁脚本改这个本地文件就能演"线上拧开关"，不必碰真 bucket。 */
  if (flags) writeBuf(path.join(buildRoot(), env, FLAGS_FILE), flags.buf);
  return { dir, pointer, manifestBuf };
}

/* ---------- 2. 凭证、写授权闸与最小签名客户端（零依赖） ---------- */

/* 凭证来源只决定"用哪把钥匙"，不再决定"能不能写"。
   能不能写由 requireWriteGate 统一判：每条写命令都要显式 WOW_ALLOW_CROSS_CREDS=1。
   2026-10-21 踩过一次：自动兜底到 p2-database 的 .env，一次"试运行"的验证命令把 82 个对象真传上去了；
   同一天复核又指出「只在 crossProject=true 时检查标记」等于换个来源就绕过。 */
function loadCreds() {
  const picked = {};
  const set = (k, v) => { if (v && !picked[k]) picked[k] = v; };
  set('region', process.env.OSS_REGION);
  set('bucket', process.env.OSS_BUCKET);
  set('accessKeyId', process.env.OSS_ACCESS_KEY_ID);
  set('accessKeySecret', process.env.OSS_ACCESS_KEY_SECRET);
  let source = '环境变量';
  let crossProject = false;

  if (!picked.accessKeyId) {
    const miniCred = path.join(MINI, '.oss-env');
    if (fs.existsSync(miniCred)) picked.warnMiniCred = path.relative(REPO, miniCred);
    const candidates = [];
    if (process.env.WOW_OSS_ENV) candidates.push({ p: path.resolve(process.env.WOW_OSS_ENV), cross: false });
    candidates.push({ p: localCredPath(), cross: false });
    candidates.push({ p: crossCredPath(), cross: true });
    for (const c of candidates) {
      if (!fs.existsSync(c.p)) continue;
      const text = fs.readFileSync(c.p, 'utf8');
      const get = (k) => {
        const m = text.match(new RegExp('^' + k + '=(.*)$', 'm'));
        return m ? m[1].trim().replace(/^["']|["']$/g, '') : '';
      };
      if (get('OSS_ACCESS_KEY_ID') && get('OSS_ACCESS_KEY_SECRET')) {
        set('accessKeyId', get('OSS_ACCESS_KEY_ID'));
        set('accessKeySecret', get('OSS_ACCESS_KEY_SECRET'));
        set('region', get('OSS_REGION'));
        set('bucket', get('OSS_BUCKET'));
        source = (c.cross ? '（跨项目钥匙，仅只读默认）' : '') + path.relative(REPO, c.p);
        crossProject = c.cross;
        break;
      }
    }
  }
  picked.region = picked.region || DEFAULT_REGION;
  picked.bucket = picked.bucket || DEFAULT_BUCKET;
  picked.from = source;
  picked.crossProject = crossProject;
  picked.ok = !!(picked.accessKeyId && picked.accessKeySecret);
  return picked;
}

/* 唯一的写授权闸：所有会动 bucket 的命令都先过这里，没过就 rc1，
   一次远端请求都不发、一个本地批次文件都不落。 */
function requireWriteGate(cmd, env, opts) {
  const out = [];
  if (process.env[WRITE_MARK] !== '1') {
    out.push('✗ ' + cmd + ' 会写 bucket。凭证从哪来都一样，必须显式加环境变量 ' + WRITE_MARK + '=1 才执行（站主口径：每条写命令都要人工点头）。');
    out.push('  报备口径：先说清用哪把钥匙、写哪个前缀，再 ' + WRITE_MARK + '=1 node tools/oss-release.js ' + cmd + ' --env ' + env + ' …');
    out.push('  只读不受影响：build / list / verify / upload --dry-run 都不需要这个标记。');
    return out;
  }
  if (env === 'release' && !opts.yesRelease) {
    out.push('✗ release 是线上环境：除 ' + WRITE_MARK + '=1 外还要显式加 --yes-release。');
    return out;
  }
  if (cmd === 'clean' && !opts.yesClean) {
    out.push('✗ 删除是不可逆动作，加 --yes-clean 才执行。');
    return out;
  }
  return null;
}

let transport = null;
function ossRaw(method, bucket, region, keyOrQuery, body, headers) {
  if (process.env.WOW_OSS_OFFLINE === '1') {
    return Promise.reject(new Error('离线闸 WOW_OSS_OFFLINE=1：禁止真实网络请求（' + method + ' ' + bucket + '）'));
  }
  return new Promise((resolve, reject) => {
    const host = bucket + '.' + region + '.aliyuncs.com';
    const req = https.request(
      { host, method, path: keyOrQuery, headers: Object.assign({ Host: host }, headers || {}), timeout: 20000 },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve({ statusCode: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
      }
    );
    req.on('timeout', () => req.destroy(new Error('超时 20s: ' + method + ' ' + keyOrQuery)));
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}
const raw = (...args) => (transport ? transport(...args) : ossRaw(...args));
const setTransportForTest = (fn) => { transport = fn || null; };

/* 素材是图片，不能一律按 JSON 发：Content-Type 错了小程序的 <image> 可能不认。
   2026-10-21 第一次传 730 个素材就踩了这个（全发成 application/json）。 */
const MIME = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.json': 'application/json; charset=utf-8' };
function contentTypeFor(rel) {
  const ext = String(rel).slice(String(rel).lastIndexOf('.')).toLowerCase();
  return MIME[ext] || 'application/octet-stream';
}

/* 素材对象的元数据头集中在这里：Content-Type 按扩展名，Content-Disposition 显式 inline。
   注意 OSS V1 签名的 StringToSign 只含 Content-MD5 / Content-Type / Date / x-oss-* / 资源路径，
   Content-Disposition 是普通头，不进签名串。 */
function assetHeaders(creds, t, cache) {
  const h = { 'Cache-Control': cache, 'Content-Type': t.type };
  if (t.disp) h['Content-Disposition'] = t.disp;
  return h;
}

function signPut(creds, key, body, extraHeaders) {
  const date = new Date().toUTCString();
  const type = extraHeaders['Content-Type'] || 'application/json; charset=utf-8';
  const md5 = md5B64(body);
  const canon = Object.assign({ 'cache-control': extraHeaders['Cache-Control'] }, extraHeaders);
  const ossHeaders = Object.keys(canon)
    .filter((k) => k.indexOf('x-oss-') === 0)
    .sort()
    .map((k) => k + ':' + String(canon[k]).trim() + '\n')
    .join('');
  const sts = ['PUT', md5, type, date, ossHeaders + '/' + creds.bucket + '/' + key].join('\n');
  const sig = crypto.createHmac('sha1', creds.accessKeySecret).update(sts).digest('base64');
  const out = {
    'Content-Type': type,
    'Content-MD5': md5,
    Date: date,
    'Cache-Control': extraHeaders['Cache-Control'],
    Authorization: 'OSS ' + creds.accessKeyId + ':' + sig,
    'Content-Length': body.length
  };
  /* Content-Disposition 不进 OSS V1 的 StringToSign（那里只有 verb、Content-MD5、Content-Type、
     Date、以 x-oss- 开头的头、资源路径），但它必须真的发出去，否则对象元数据里就没有 inline
     ——之前这里只回传固定几个头，新加的普通头会被静默丢掉。 */
  if (extraHeaders['Content-Disposition']) out['Content-Disposition'] = extraHeaders['Content-Disposition'];
  return out;
}

function signGet(creds, pathWithQuery, resource) {
  const date = new Date().toUTCString();
  const sts = ['GET', '', '', date, '/' + creds.bucket + resource].join('\n');
  const sig = crypto.createHmac('sha1', creds.accessKeySecret).update(sts).digest('base64');
  return { Date: date, Authorization: 'OSS ' + creds.accessKeyId + ':' + sig };
}

const encKey = (key) => key.split('/').map(encodeURIComponent).join('/');
const pointerKey = (env) => NAMESPACES[env] + '/manifest.json';
const buildPrefix = (env, buildId) => NAMESPACES[env] + '/builds/' + buildId + '/';

function remotePointer(creds, env) {
  return raw('GET', creds.bucket, creds.region, '/' + encKey(pointerKey(env)), null, signGet(creds, '/' + encKey(pointerKey(env)), '/' + pointerKey(env)))
    .then((r) => (r.statusCode === 200 ? { json: JSON.parse(r.body.toString('utf8')), headers: r.headers, body: r.body } : null));
}

function remoteHead(creds, key) {
  return raw('HEAD', creds.bucket, creds.region, '/' + encKey(key), null, {})
    .then((r) => ({
      exists: r.statusCode === 200,
      etag: r.statusCode === 200 ? String(r.headers.etag || '').replace(/"/g, '').toUpperCase() : '',
      bytes: r.statusCode === 200 ? Number(r.headers['content-length'] || 0) : 0,
      lastModified: r.statusCode === 200 ? r.headers['last-modified'] : '',
      contentType: r.statusCode === 200 ? String(r.headers['content-type'] || '') : '',
      cacheControl: r.statusCode === 200 ? String(r.headers['cache-control'] || '') : '',
      contentDisposition: r.statusCode === 200 ? String(r.headers['content-disposition'] || '') : '',
      forceDownload: r.statusCode === 200 ? String(r.headers['x-oss-force-download'] || '') : '',
      statusCode: r.statusCode
    }));
}

function listKeys(creds, prefix) {
  /* V1 签名的 CanonicalizedResource 只到 "/bucket/"：prefix / max-keys 是查询参数，
     不参与签名（把它们塞进签名串会得到 SignatureDoesNotMatch，实测踩过）。 */
  const q = '/?prefix=' + encodeURIComponent(prefix) + '&max-keys=1000';
  return raw('GET', creds.bucket, creds.region, q, null, signGet(creds, q, '/')).then((r) => {
    if (r.statusCode !== 200) return { ok: false, code: r.statusCode, text: r.body.toString('utf8').slice(0, 300) };
    const xml = r.body.toString('utf8');
    const keys = [];
    const re = /<Key>([^<]+)<\/Key>/g;
    let m;
    while ((m = re.exec(xml))) keys.push(m[1]);
    const truncated = /<IsTruncated>true<\/IsTruncated>/.test(xml);
    return { ok: true, keys, truncated };
  });
}

function signDelete(creds, key) {
  const date = new Date().toUTCString();
  const sts = ['DELETE', '', '', date, '/' + creds.bucket + '/' + key].join('\n');
  const sig = crypto.createHmac('sha1', creds.accessKeySecret).update(sts).digest('base64');
  return { Date: date, Authorization: 'OSS ' + creds.accessKeyId + ':' + sig };
}

function listBuilds(creds, env) {
  const prefix = NAMESPACES[env] + '/builds/';
  return listKeys(creds, prefix).then((r) => {
    if (!r.ok) return r;
    const ids = [];
    r.keys.forEach((k) => {
      const mm = k.replace(prefix, '').split('/')[0];
      if (mm && ids.indexOf(mm) < 0) ids.push(mm);
    });
    return { ok: true, objectCount: r.keys.length, buildIds: ids, truncated: r.truncated };
  });
}

/* 素材台账：不是给客户端读的（图片走 <image>，不做 ETag 校验），
   是给"这批到底发了哪些文件、每个多大、哈希多少"留的一份可对账清单。 */
function assetIndexBuf(built) {
  return dump({
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    kind: 'asset-index',
    note: '这批数据真引用到、且本地确实在的素材文件。缺的记在 missing 里，界面必须回落自绘。',
    files: built.assetUse,
    missing: built.assetMissing
  });
}

/* ---------- 3. 子命令 ---------- */

/* ---------- 1b. 功能开关：与数据批次并列的一个可变对象 ----------

   真源是 app/data/flags.json（人写的），这里只做三件事：
   ① 校验（名字形制、on 必须是布尔、页面必须在小程序的 pages 里注册、
      说要开的页必须在这一批里有它要的数据）；
   ② 只把客户端用得上的字段（on / name / note）抄进下发对象，needs 那层留在仓库；
   ③ 按指针同一档缓存语义发出去。

   字节里没有生成时间：这个对象"什么时候拧的"看服务端 Last-Modified 与本地 last-flags.json。
   开关内容没改时重跑得到同一份字节（inputSha 只跟 flags.json 走、不跟 commit 走；
   source.generator 那个哈希跟着本脚本变，所以改了生成逻辑也会换字节——那是有意的留痕）。 */
const FLAGS_BUDGET_KB = 4;
const FLAGS_POLICY = [
  '这个对象不在气密批次里：改它不换 buildId、不重发数据、不发小程序版本，玩家侧约一分钟内生效（与指针同一档 max-age=60）。',
  '取不到这个对象（断网、还没发过、结构不对）时，客户端必须退回代码包里的默认表：不许把已经公开的页关掉，也不许因为"远端没说关"就把没公开的页放出来。',
  '开关只管"这一页给不给看"，不管数据对不对。页面自己的取数校验与红线一条都不省，关掉只是收入口 + 页面自己拒绝取数。',
  '界面要把关掉的页说成"这一页还没开放"，不许编一个"数据维护中"的理由，也不许在关着的页面上留下空白格。'
];

function buildFlags(env, opts) {
  const o = opts || {};
  const errors = [];
  const srcPath = path.join(siteData(), FLAGS_FILE);
  if (!fs.existsSync(srcPath)) {
    return { errors: ['缺 app/data/' + FLAGS_FILE + '：开关真源不在，客户端只能按打包默认值走'], env };
  }
  const base = readJson(srcPath);
  const feats = base.features || {};
  const names = Object.keys(feats);
  if (!names.length) errors.push('flags.json 的 features 是空的：一个开关都没有，客户端拿默认表也无处可覆盖');

  let pages = null;
  const appJsonPath = path.join(MINI, 'app.json');
  if (fs.existsSync(appJsonPath)) {
    pages = readJson(appJsonPath).pages || [];
  } else {
    errors.push('读不到 for-mini/app.json，没法核实开关指向的页面在不在代码包里');
  }

  const out = {};
  names.forEach((n) => {
    if (!FLAG_NAME_RE.test(n)) { errors.push('开关名 ' + n + ' 只能用从小写字母开头的 [a-z0-9]'); return; }
    const f = feats[n] || {};
    if (typeof f.on !== 'boolean') errors.push('开关 ' + n + ' 的 on 必须是 true/false，不能是 ' + JSON.stringify(f.on));
    if (!f.name) errors.push('开关 ' + n + ' 缺 name（关掉页面时界面要念出这一页叫什么）');
    if (!f.note) errors.push('开关 ' + n + ' 缺 note（为什么开/为什么关，只有人写得出来）');
    if (f.page && pages && pages.indexOf(f.page) < 0) {
      errors.push('开关 ' + n + ' 指向 ' + f.page + '，但它不在 for-mini/app.json 的 pages 里 —— 页面没进代码包，开关拧成 true 玩家也打不开');
    }
    out[n] = { on: f.on === true, name: f.name || n, note: f.note || '' };

    /* 说要开的一页，这一批里必须有它要的数据。没有就是"把门打开对着一个空房间"，
       宁可在构建端红，也不要让玩家点进去看一个白屏。 */
    const needList = f.needs || [];
    if (f.on === true && o.manifest) {
      const have = o.manifest.fetch || {};
      const miss = needList.filter((k) => !have[k]);
      if (miss.length) {
        errors.push('开关 ' + n + ' 是开的，但它要的数据入口 [' + miss.join(', ') + '] 不在'
          + (o.manifestFrom || '这一批') + '里 —— 先发带这批数据的批次，再开这个开关');
      }
    }
    if (f.on === true && !o.manifest && needList.length) {
      errors.push('开关 ' + n + ' 是开的，但这次没法核实它要的数据在不在批次里（拿不到指针）——'
        + '先跑 build，或让线上指针可读');
    }
    if (f.on !== true && o.manifest && o.manifest.fetch && needList.some((k) => !o.manifest.fetch[k])) {
      /* 关着的页不拦缺数据，但要在本地留痕：哪天拧 true 就会在上面那条红 */
      errors.push('开关 ' + n + ' 现在关着，但它要的数据入口 [' + needList.filter((k) => !o.manifest.fetch[k]).join(', ')
        + '] 不在' + (o.manifestFrom || '这一批') + '里 —— 拧 true 之前先发数据批次');
    }
  });

  const obj = {
    schemaVersion: SCHEMA_VERSION,
    product: FLAGS_PRODUCT,
    env,
    namespace: NAMESPACES[env],
    minClientSchemaVersion: 1,
    timeNote: '本对象没有生成时间字段：开关内容与生成它的脚本都没改时，重跑得到同一份字节。什么时候拧的，看这个对象的服务端 Last-Modified 与构建端 last-flags.json。',
    source: {
      input: 'wow-forever-web/app/data/' + FLAGS_FILE,
      inputSha256: sha256(fs.readFileSync(srcPath)),
      generator: { tool: 'wow-forever-web/tools/oss-release.js', sha256: sha256(fs.readFileSync(__filename)).slice(0, 12) },
      note: 'needs（这一页要哪些数据入口）只给构建端校验用，不下发；下发的是客户端渲染与守卫用得上的 on/name/note。'
    },
    features: out,
    policy: FLAGS_POLICY,
    cacheControl: POINTER_CACHE,
    counts: { features: names.length, on: names.filter((n) => out[n] && out[n].on === true).length }
  };
  const buf = dump(obj);
  if (buf.length > FLAGS_BUDGET_KB * 1024) {
    errors.push('flags.json 下发对象 ' + kb(buf.length) + ' KB 超过 ' + FLAGS_BUDGET_KB + ' KB：每次冷启动都要多下这一份，收着点');
  }
  return { errors, obj, buf, key: NAMESPACES[env] + '/' + FLAGS_FILE, env, srcPath };
}

function localManifestForFlags(env) {
  const p = path.join(buildRoot(), env, 'manifest.json');
  if (!fs.existsSync(p)) return null;
  try {
    return readJson(p);
  } catch (e) {
    return null;
  }
}

async function cmdFlags(env, opts) {
  if (!opts.dryRun) {
    const gate = requireWriteGate('flags', env, opts);
    if (gate) { gate.forEach(logLine); return 1; }
  }
  const creds = loadCreds();
  let manifest = null;
  let manifestFrom = '';
  const remote = creds.ok ? await remotePointer(creds, env) : null;
  if (remote && remote.json) {
    manifest = remote.json;
    manifestFrom = '线上指针指的批次 ' + remote.json.buildId;
  } else {
    manifest = localManifestForFlags(env);
    if (manifest) manifestFrom = '本地最近构建的批次 ' + manifest.buildId + '（线上指针' + (creds.ok ? '读不到' : '没凭证读') + '，按本地算）';
  }
  const built = buildFlags(env, { manifest, manifestFrom });
  if (built.errors.length) {
    built.errors.slice(0, 25).forEach((e) => logLine('✗ ' + e));
    logLine('开关构建失败：' + built.errors.length + ' 项不合规');
    return 1;
  }
  const names = Object.keys(built.obj.features);
  logLine('开关 ' + built.key + ' · ' + kb(built.buf.length) + ' KB · 数据核实依据：' + (manifestFrom || '拿不到批次'));
  names.forEach((n) => logLine('  ' + (built.obj.features[n].on ? '开' : '关') + '  ' + n + '（' + built.obj.features[n].name + '）'));
  if (opts.dryRun) {
    logLine('试运行：没写本地、没传对象。');
    return 0;
  }
  writeBuf(path.join(buildRoot(), env, FLAGS_FILE), built.buf);
  logLine('本地 → ' + path.relative(REPO, path.join(buildRoot(), env, FLAGS_FILE)));
  if (!creds.ok) {
    logLine(credsHint(creds));
    return 1;
  }
  const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(built.key), built.buf,
    signPut(creds, built.key, built.buf, { 'Cache-Control': POINTER_CACHE }));
  if (r.statusCode < 200 || r.statusCode >= 300) {
    logLine('✗ 发开关失败：HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 300));
    return 1;
  }
  const back = await remoteHead(creds, built.key);
  const same = back.exists && back.etag === md5Hex(built.buf) && back.bytes === built.buf.length;
  logLine((same ? '回读 ETag/字节一致' : '✗ 回读不一致（远端 ETag ' + (back.etag || '没有') + ' · 本份 ' + md5Hex(built.buf)
    + ' · ' + back.bytes + '/' + built.buf.length + ' 字节）') + ' · ' + built.key + '（开关本身是可覆盖对象，这次 PUT 就是覆盖）');
  writeBuf(path.join(buildRoot(), env, 'last-flags.json'), dump({
    at: new Date().toISOString(), env, key: built.key, bytes: built.buf.length,
    sha256: sha256(built.buf), readBackEtag: back.etag || null, features: built.obj.features,
    note: '这个时间戳是"本次发开关动作"的本地记录，不进下发对象——下发对象要能在开关没改时字节恒定。'
  }));
  logLine('玩家侧生效：等 max-age=60 过完（约 1 分钟），不必发小程序版本。');
  return same ? 0 : 1;
}

function logLine(s) { process.stdout.write(s + '\n'); }

function credsHint(creds) {
  if (creds.warnMiniCred) {
    return '✗ 凭证文件放在小程序根目录（' + creds.warnMiniCred + '）。.gitignore 挡不住微信打包器，密钥会被打进代码包：请移到仓库根 .oss-env 或删除。';
  }
  return '✗ 没找到 OSS 凭证。给法三种：环境变量 OSS_ACCESS_KEY_ID/SECRET、$WOW_OSS_ENV 指向的文件、仓库根 .oss-env（不在小程序目录里）';
}

function cmdBuild(env, opts) {
  const built = buildBatch(env);
  if (built.errors.length) {
    built.errors.slice(0, 25).forEach((e) => logLine('✗ ' + e));
    logLine('构建失败：' + built.errors.length + ' 项不合规');
    return 1;
  }
  /* 开关跟着一起校：这一批要给哪些页供数据，构建端是唯一能说这话的地方 */
  const flags = buildFlags(env, { manifest: built.manifest, manifestFrom: '本批 ' + built.buildId });
  if (flags.errors.length) {
    flags.errors.slice(0, 25).forEach((e) => logLine('✗ 开关：' + e));
    logLine('构建失败：开关 ' + flags.errors.length + ' 项不合规');
    return 1;
  }
  const out = writeBatch(env, built, flags);
  const idx = built.entries.filter((e) => e.key === 'dungeonIndex')[0];
  const entryKeys = Object.keys(built.manifest.fetch);
  const cold = out.manifestBuf.length + idx.bytes + built.manifest.fetch.meta.bytes;
  const flat = fs.statSync(path.join(previewDir(), 'dungeons.json')).size;
  const maxOf = (p) => kb(Math.max.apply(null, built.entries.filter((e) => e.key.indexOf(p) === 0).map((e) => e.bytes)));
  logLine('批次 ' + built.buildId + ' → ' + path.relative(REPO, out.dir));
  logLine('  数据文件 ' + built.entries.length + ' + files.json + manifest = ' + built.manifest.counts.files
    + ' 个 · 合计 ' + kb(built.manifest.counts.bytes) + ' KB · 指针 ' + pointerKey(env));
  logLine('  导出对拍：' + (built.manifest.source.exportCheck
    ? built.manifest.source.exportCheck.outputs.length + ' 份产物与 app/data 重导出逐字节一致（' + built.manifest.source.exportCheck.tool + '）'
    : '已跳过（--skip-export-check）'));
  logLine('  冷启动按副本看是 manifest ' + kb(out.manifestBuf.length) + ' + 副本索引 ' + kb(idx.bytes)
    + ' + meta ' + kb(built.manifest.fetch.meta.bytes) + ' = ' + kb(cold)
    + ' KB（3 次 GET；整份 dungeons.json 是 ' + kb(flat) + ' KB，省下 ' + Math.round((1 - cold / flat) * 100) + '%。'
    + '入口文件现在共 ' + entryKeys.length + ' 个：' + entryKeys.join(' / ') + '，取哪个只多那一个的分片）');
  logLine('  单本详情上限 ' + maxOf('dungeonDetail:') + ' KB · 掉落上限 ' + maxOf('dungeonLoot:')
    + ' KB · 职业法术片上限 ' + maxOf('spellClass:') + ' KB · files.json ' + kb(built.manifest.bundle.bytes) + ' KB');
  logLine('  校验值分布：' + entryKeys.length + ' 个入口文件在指针里（ETag+MD5+bytes），详情/掉落/职业片随各自索引下发；files.json 只在构建端与 verify 用');
  logLine('  素材引用：' + built.manifest.assets.count + ' 个文件 / ' + kb(built.manifest.assets.bytes)
    + ' KB 在 ' + built.ns + '/assets/ 下（用 `assets --env ' + env + '` 发），缺登记 ' + built.manifest.assets.missing + ' 条');
  logLine('  事实核对日期：最新 ' + (built.manifest.factDates.latest || '未记录') + '（清单内无生成时间字段，发布时刻看服务端 Last-Modified）');
  logLine('  功能开关：' + kb(flags.buf.length) + ' KB · ' + Object.keys(flags.obj.features).length
    + ' 个（开 ' + flags.obj.counts.on + '）→ ' + path.relative(REPO, path.join(buildRoot(), env, FLAGS_FILE))
    + '（发它用 `flags --env ' + env + '`，与这批数据互不牵扯）');
  if (opts.checkIdentity) {
    const again = buildBatch(env);
    if (again.errors.length) { logLine('✗ 复算失败'); return 1; }
    const stableSame = again.buildId === built.buildId;
    const perFile = again.entries.filter((e, i) => e.sha256 !== built.entries[i].sha256).map((e) => e.path);
    const volatileOnly = Object.keys(again.manifest).filter((k) => JSON.stringify(again.manifest[k]) !== JSON.stringify(built.manifest[k]));
    const bytesSame = dump(again.manifest).equals(out.manifestBuf);
    logLine('  重跑同源：buildId ' + (stableSame ? '一致' : '不一致 ✗') + ' · 逐文件字节差异 ' + perFile.length
      + ' · manifest 变化字段 [' + volatileOnly.join(',') + '] · 指针清单字节' + (bytesSame ? '完全相同' : '不同 ✗'));
    const againFlags = buildFlags(env, { manifest: again.manifest, manifestFrom: '复算批次' });
    const flagsSame = !againFlags.errors.length && Buffer.compare(againFlags.buf, flags.buf) === 0;
    logLine('  开关对象：' + kb(flags.buf.length) + ' KB · ' + Object.keys(flags.obj.features).length + ' 个开关（开 '
      + flags.obj.counts.on + ' 个）· 重跑字节' + (flagsSame ? '相同' : '不同 ✗') + ' · 路径 ' + flags.key);
    if (!stableSame || !bytesSame || perFile.length || volatileOnly.length) {
      logLine('✗ 产物不可复现（同一 buildId 的清单必须逐字节恒定）');
      return 1;
    }
    if (!flagsSame) { logLine('✗ 开关对象不可复现'); return 1; }
    return 0;
  }
  return 0;
}

async function cmdAssets(env, opts) {
  if (!opts.dryRun) {
    const gate = requireWriteGate('assets', env, opts);
    if (gate) { gate.forEach(logLine); return 1; }
  }
  const built = buildBatch(env);
  if (built.errors.length) { built.errors.slice(0, 25).forEach((e) => logLine('✗ ' + e)); return 1; }
  const keys = Object.keys(built.assetUse).sort();
  const total = keys.reduce((t, k) => t + built.assetUse[k].bytes, 0);
  const creds = loadCreds();
  logLine('环境 ' + env + ' · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/' + ASSET_DIR + '/'
    + ' · 素材 ' + keys.length + ' 个 / ' + kb(total) + ' KB · 缺登记 ' + built.assetMissing.length + ' 条'
    + (opts.dryRun ? '（--dry-run 只读远端，不写）' : '（凭证来源 ' + creds.from + '）'));
  if (!opts.dryRun && !creds.ok) { logLine(credsHint(creds)); return 1; }

  const indexBuf = assetIndexBuf(built);
  const targets = keys.map((rel) => ({
    key: NAMESPACES[env] + '/' + ASSET_DIR + '/' + rel,
    buf: fs.readFileSync(path.join(WEB, "app", "img", rel)),
    label: rel,
    type: contentTypeFor(rel),
    disp: ASSET_DISP
  }));
  /* 台账本身是"这一批引用了哪些素材"的可重导清单，每批都会变；
     只有图片对象才是不可变的。把 index.json 也按 immutable 拦，
     第二次发素材就会得到一条假冲突（2026-10-22 加技能图标时踩到）。 */
  targets.push({
    key: NAMESPACES[env] + '/' + ASSET_DIR + '/index.json', buf: indexBuf,
    label: 'assets/index.json（素材台账）', type: MIME['.json'], mutable: true
  });

  let uploaded = 0; let unchanged = 0; let fixed = 0; let bytes = 0; let forcedCount = 0;
  const failed = []; const violations = [];
  for (const t of targets) {
    const cache = t.mutable ? POINTER_CACHE : IMUTABLE_CACHE;
    const head = creds.ok ? await remoteHead(creds, t.key) : { exists: false };
    if (head.exists && head.etag && head.etag === md5Hex(t.buf)) {
      /* 字节一样但 Content-Type 或缓存头不对：补正元数据，内容没动，不算覆写。
         比对两边都先摘掉 `; charset=` 后缀——JSON 的 MIME 带字符集，
         不摘就会每次都对不上、每次重发一遍（2026-10-22 自测里暴露出来）。 */
      const wantBase = t.type ? t.type.split(';')[0] : '';
      const gotBase = head.contentType ? head.contentType.split(';')[0] : '';
      /* Content-Disposition 只在"远端没被默认域名强制改掉"时才拿来判漂移。
         2026-10-22 实测：往对象元数据里写 inline，OSS 默认域名回读仍是 attachment
         + x-oss-force-download: true（1,117 张全这样），照字面比就会每次重传整层素材。 */
      const forced = head.forceDownload === 'true';
      if (forced) forcedCount += 1;
      const dispDrift = !!t.disp && !forced && (head.contentDisposition || '') !== t.disp;
      if ((wantBase && gotBase && wantBase !== gotBase) || (t.mutable && head.cacheControl !== cache)
        || dispDrift) {
        try {
          const r2 = await raw('PUT', creds.bucket, creds.region, '/' + encKey(t.key), t.buf,
            signPut(creds, t.key, t.buf, assetHeaders(creds, t, cache)));
          if (r2.statusCode >= 200 && r2.statusCode < 300) { fixed += 1; continue; }
          failed.push(t.label + ' → 补正 Content-Type 失败 HTTP ' + r2.statusCode);
        } catch (e2) { failed.push(t.label + ' → 补正失败 ' + e2.message); }
      }
      unchanged += 1; continue;
    }
    if (head.exists && !t.mutable) { violations.push(t.label + '：远端已存在但字节不同（素材文件名本该唯一，先查清是谁改的）'); continue; }
    if (opts.dryRun) { uploaded += 1; continue; }
    try {
      const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(t.key), t.buf,
        signPut(creds, t.key, t.buf, assetHeaders(creds, t, cache)));
      if (r.statusCode < 200 || r.statusCode >= 300) throw new Error('HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 160));
      const back = await remoteHead(creds, t.key);
      if (back.etag !== md5Hex(t.buf)) throw new Error('回读 ETag 不匹配');
      uploaded += 1; bytes += t.buf.length;
    } catch (err) { failed.push(t.label + ' → ' + err.message); }
  }
  if (violations.length) violations.slice(0, 8).forEach((v) => logLine('  ✗ ' + v));
  if (failed.length) failed.slice(0, 8).forEach((f) => logLine('  ✗ ' + f));
  logLine('素材：传 ' + uploaded + ' · 已存在跳过 ' + unchanged + ' · 补正元数据（Content-Type / Content-Disposition / 缓存头）' + fixed
    + ' · 失败 ' + failed.length + ' · 冲突 ' + violations.length + ' / 共 ' + targets.length);
  if (forcedCount) {
    logLine('  · 其中 ' + forcedCount + ' 个对象的 Content-Disposition 被 OSS 默认域名强制成 attachment'
      + '（响应带 x-oss-force-download: true）。我们写的是 inline，**对象元数据改不动它**——'
      + '这是阿里云对默认域名的策略，要按 inline 出图只能绑自定义域名（需备案）。');
    logLine('  · <image> 组件不是导航请求，一般不看 Content-Disposition；模拟器里 1,117 张全部渲染出来了。'
      + '真机到底认不认，只有真机能回答，见 for-mini/docs/DATA.md §九。');
  }
  if (opts.dryRun) { logLine('试运行结束，一个字节都没写。'); return 0; }
  writeBuf(path.join(buildRoot(), env, 'last-assets.json'), dump({
    at: new Date().toISOString(), env, uploaded, unchanged, failed: failed.length, conflicts: violations.length,
    count: keys.length, bytes: total, missing: built.assetMissing.length
  }));
  if (violations.length || failed.length) { logLine('✗ 素材没发齐，界面会有一部分图取不到（会回落自绘，不会碎图）。'); return 1; }
  logLine('素材齐了：' + keys.length + ' 个 / ' + kb(total) + ' KB 在 ' + NAMESPACES[env] + '/' + ASSET_DIR + '/ 下（immutable 一年）');
  return 0;
}

/* ---------- 3.5 真实整人模型的远端分发（2026-10-30，B2 单件 / B3 整批）---------- */

/* 模型不是数据批次里的东西：它是内容寻址的不可变对象，清单是 B1 那份独立索引
   （for-mini/oss-build/{env}/bis/models/index.json），对象落 assets/models/real/ 下。
   三条不许：本地字节或哈希与索引不符还照传、远端同名对象字节不同还覆写、
   传完不回读就报成功。 */
const MODEL_ASSET_DIR = 'assets/models/real';
const MODEL_LOCAL_DIR = 'models';
const MODEL_INDEX_REL = ['bis', 'models', 'index.json'];
/* 远端那份清单是可变对象（和指针同一档缓存）：模型不可变、名字带哈希，
   清单却必须能当天改，否则换一件模型就要等一年缓存。 */
const MODEL_INDEX_KEY = 'bis/models/index.json';
/* 配装页默认那一格的底图（2026-10-30 站主："原画那个位置换成模型穿这一身的图"）。
   按种族 6 张，名字同样带内容哈希——重渲一次就是换一个名字，不许覆盖已发出去的对象。 */
const POSTER_DIR = 'assets/models/posters';
const POSTER_LOCAL = 'posters';
const MODEL_MIME = 'model/gltf-binary';

/* 索引读一次，形状不对就直接返回错误——不发任何远端请求 */
function modelIndex(env) {
  const p = path.join(buildRoot(), env, ...MODEL_INDEX_REL);
  if (!fs.existsSync(p)) return { errors: ['找不到模型索引 ' + path.relative(REPO, p) + '（先跑 tools/build-mini-bis-models.py）'] };
  let idx;
  try { idx = JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return { errors: ['模型索引不是合法 JSON：' + e.message] }; }
  const errors = [];
  if (idx.product !== 'wow-forever-mini-models' || idx.kind !== 'bis-models-index') errors.push('索引 product/kind 不对');
  if (idx.formatVersion !== 'glb-png-v1') errors.push('索引 formatVersion 不是 glb-png-v1，先确认 B1 重跑过');
  if (String(idx.assetDir) !== MODEL_ASSET_DIR + '/') errors.push('索引 assetDir 是 ' + idx.assetDir + '，与本命令拼的 ' + MODEL_ASSET_DIR + '/ 不一致');
  const models = Array.isArray(idx.models) ? idx.models : [];
  if (!models.length) errors.push('索引里一条模型都没有');
  /* 索引自己先要算得通：counts 是 B1 构建时算的，手改过一条就对不上（B3 的"重新核一遍"落在这里） */
  const c = idx.counts || {};
  const sumBytes = models.reduce((t, m) => t + (Number(m.pngBytes) || 0), 0);
  if (c.models !== models.length) errors.push('索引 counts.models 是 ' + c.models + '，实际 ' + models.length + ' 条');
  if (c.bytes !== sumBytes) errors.push('索引 counts.bytes 是 ' + c.bytes + '，逐条加起来是 ' + sumBytes);
  const seen = new Set();
  models.forEach((m) => {
    const id = m.setId + '/' + m.faction;
    if (seen.has(id)) errors.push(id + ' 在索引里重复');
    seen.add(id);
    if (!/^[a-z0-9-]+-[0-9a-f]{12}\.glb$/.test(String(m.file || ''))) errors.push(id + ' 的文件名不合规矩（要 <setId>-<faction>-<成品sha前12>.glb）：' + m.file);
    if (String(m.file || '').indexOf('/') >= 0 || String(m.file || '').indexOf('..') >= 0) errors.push(id + ' 的文件名想往上跳：' + m.file);
    if (String(m.file || '').slice(0, -4).slice(-12) !== String(m.pngSha256 || '').slice(0, 12)) errors.push(id + ' 的文件名哈希与 pngSha256 前 12 位不同');
  });
  return { idx, models, errors, indexRel: path.relative(REPO, p) };
}

async function cmdModels(env, opts) {
  if (!opts.dryRun) {
    const gate = requireWriteGate('models', env, opts);
    if (gate) { gate.forEach(logLine); return 1; }
  }
  const rd = modelIndex(env);
  if (rd.errors.length) { rd.errors.slice(0, 12).forEach((e) => logLine('✗ ' + e)); return 1; }
  const want = (opts.models && opts.models.length) ? opts.models : null;
  const picked = want
    ? rd.models.filter((m) => want.indexOf(m.setId + '/' + m.faction) >= 0)
    : rd.models;
  const missingWant = want ? want.filter((w) => !picked.some((m) => m.setId + '/' + m.faction === w)) : [];
  if (missingWant.length) { missingWant.forEach((w) => logLine('✗ 索引里没有 ' + w)); return 1; }

  /* 传之前把每一份本地文件对完：任何一件对不上，整批停，不发一个请求 */
  const locals = [];
  const bad = [];
  for (const m of picked) {
    const p = path.join(buildRoot(), env, MODEL_LOCAL_DIR, m.file);
    if (!fs.existsSync(p)) { bad.push(m.setId + '/' + m.faction + ' 本地文件不存在：' + m.file); continue; }
    const buf = fs.readFileSync(p);
    if (buf.length !== m.pngBytes) bad.push(m.setId + '/' + m.faction + ' 本地字节与索引不符（' + buf.length + ' ≠ ' + m.pngBytes + '）');
    else if (sha256(buf) !== m.pngSha256) bad.push(m.setId + '/' + m.faction + ' 本地 SHA-256 与索引不符');
    else locals.push({ m, buf });
  }
  if (bad.length) { bad.slice(0, 12).forEach((e) => logLine('✗ ' + e)); return 1; }

  const creds = loadCreds();
  const total = locals.reduce((t, x) => t + x.buf.length, 0);
  logLine('环境 ' + env + ' · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/' + MODEL_ASSET_DIR + '/'
    + ' · 模型 ' + locals.length + ' 件 / ' + kb(total) + ' KB'
    + (opts.dryRun ? '（--dry-run 只读远端，不写）' : '（凭证来源 ' + creds.from + (opts.dryRun ? '' : '，已带 ' + WRITE_MARK + '=1') + '）'));
  if (creds.warnMiniCred) { logLine('✗ ' + credsHint(creds)); return 1; }
  if (!opts.dryRun && !creds.ok) { logLine(credsHint(creds)); return 1; }

  let uploaded = 0; let unchanged = 0; let fixed = 0; let forced = 0;
  const failed = []; const violations = []; const remoteLines = [];
  for (const it of locals) {
    const key = NAMESPACES[env] + '/' + MODEL_ASSET_DIR + '/' + it.m.file;
    const headers = { 'Cache-Control': IMUTABLE_CACHE, 'Content-Type': MODEL_MIME, 'Content-Disposition': ASSET_DISP };
    const head = creds.ok ? await remoteHead(creds, key) : { exists: false };
    const label = it.m.setId + '/' + it.m.faction;
    if (head.exists) {
      if (head.etag !== md5Hex(it.buf)) {
        violations.push(label + '：远端同名对象字节不同（远端 ETag ' + head.etag + ' ≠ 本地 ' + md5Hex(it.buf) + '），不覆写');
        continue;
      }
      /* 字节相同但元数据漂了：只补元数据。默认域名会强制 attachment（和素材那层一样），
         被强制的情况不算漂移，也记一笔给真机判定当证据。 */
      if (head.forceDownload === 'true') forced += 1;
      const drift = (head.contentType || '').split(';')[0] !== MODEL_MIME || head.cacheControl !== IMUTABLE_CACHE
        || (!head.forceDownload && head.contentDisposition !== ASSET_DISP);
      if (drift && !opts.dryRun) {
        try {
          const r2 = await raw('PUT', creds.bucket, creds.region, '/' + encKey(key), it.buf, signPut(creds, key, it.buf, headers));
          if (r2.statusCode >= 200 && r2.statusCode < 300) { fixed += 1; continue; }
          failed.push(label + ' → 补正元数据失败 HTTP ' + r2.statusCode);
        } catch (e2) { failed.push(label + ' → 补正失败 ' + e2.message); }
      }
      unchanged += 1; continue;
    }
    if (opts.dryRun) { uploaded += 1; logLine('  待传 ' + label + ' → ' + key + '  ' + kb(it.buf.length) + ' KB'); continue; }
    try {
      const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(key), it.buf, signPut(creds, key, it.buf, headers));
      if (r.statusCode < 200 || r.statusCode >= 300) throw new Error('HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 200));
      const back = await remoteHead(creds, key);
      if (back.etag !== md5Hex(it.buf) || back.bytes !== it.buf.length) throw new Error('HEAD 回读不符（etag ' + back.etag + ' / ' + back.bytes + ' B）');
      const g = await raw('GET', creds.bucket, creds.region, '/' + encKey(key), null, signGet(creds, '/' + encKey(key), '/' + key));
      if (g.statusCode !== 200) throw new Error('GET 回读 HTTP ' + g.statusCode);
      if (g.body.length !== it.buf.length || sha256(g.body) !== it.m.pngSha256) {
        throw new Error('GET 回读字节/哈希不符（' + g.body.length + ' B / ' + sha256(g.body).slice(0, 12) + '）');
      }
      uploaded += 1;
      /* 新传的对象也看一眼回读头：不然"被默认域名强制 attachment"只数已存在那批，
         整批第一次发的时候会说成 0，把真机要防的那条线索报丢了 */
      if (back.forceDownload === 'true') forced += 1;
      remoteLines.push('  ✓ ' + label + ' · ' + back.bytes + ' B · ' + it.m.pngSha256.slice(0, 12)
        + ' · HEAD/GET 回读一致 · Content-Type=' + (back.contentType || '?') + '·缓存=' + (back.cacheControl || '?')
        + '·Disposition=' + (back.contentDisposition || '无') + (back.forceDownload === 'true' ? '（默认域名强制 attachment）' : '')
        + '\n     https://' + creds.bucket + '.' + creds.region + '.aliyuncs.com/' + encKey(key));
    } catch (err) { failed.push(label + ' → ' + err.message); }
  }
  remoteLines.forEach(logLine);
  if (violations.length) violations.slice(0, 8).forEach((v) => logLine('  ✗ ' + v));
  if (failed.length) failed.slice(0, 8).forEach((f) => logLine('  ✗ ' + f));
  logLine('模型：传 ' + uploaded + ' · 已存在跳过 ' + unchanged + ' · 补正元数据 ' + fixed
    + ' · 失败 ' + failed.length + ' · 同名冲突 ' + violations.length + ' / 共 ' + locals.length
    + (forced ? ' · 其中 ' + forced + ' 个被默认域名强制 attachment' : ''));
  if (opts.dryRun) {
    if (opts.index) logLine('  待发索引 → ' + NAMESPACES[env] + '/' + MODEL_INDEX_KEY + '（短期缓存，模型齐了才发）');
    logLine('试运行结束，一个字节都没写。'); return 0;
  }
  /* 全部"已存在同字节跳过"也是成功：B3 中途断过要续传，第二次就是这一态 */
  if (violations.length || failed.length) {
    /* 这条顺序是门槛写死的：任何一件没齐，索引不许切到新清单——
       页面按索引取件，索引先走就等于给玩家发一份会 404 的地图。 */
    if (opts.index) logLine('✗ 模型没发齐，索引不发。');
    return 1;
  }
  if (opts.index) {
    const localIdx = path.join(buildRoot(), env, ...MODEL_INDEX_REL);
    const buf = fs.readFileSync(localIdx);
    const key = NAMESPACES[env] + '/' + MODEL_INDEX_KEY;
    const headers = { 'Cache-Control': POINTER_CACHE, 'Content-Type': MIME['.json'] };
    try {
      const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(key), buf, signPut(creds, key, buf, headers));
      if (r.statusCode < 200 || r.statusCode >= 300) throw new Error('HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 200));
      const back = await remoteHead(creds, key);
      const g = await raw('GET', creds.bucket, creds.region, '/' + encKey(key), null, signGet(creds, '/' + encKey(key), '/' + key));
      if (g.statusCode !== 200 || g.body.length !== buf.length || sha256(g.body) !== sha256(buf)) {
        throw new Error('索引回读不符（HTTP ' + g.statusCode + ' / ' + g.body.length + ' B）');
      }
      logLine('索引已发：' + key + ' · ' + buf.length + ' B · ' + sha256(buf).slice(0, 12)
        + ' · HEAD/GET 回读一致 · 缓存=' + (back.cacheControl || '?') + '（模型那条是长缓存，这一份要能当天改）');
    } catch (err) { logLine('  ✗ 索引 → ' + err.message); return 1; }
    return 0;
  }
  logLine('索引来源 ' + rd.indexRel + ' · 本命令只传了模型；索引要加 --index 才发（B3 口径：模型齐了最后发）。');
  return 0;
}

/* 底图那一层：与模型同一套规矩（本地清单说了算、同名不同字节不覆写、传完必回读），
   但不参与"索引最后发"那条——它不是清单，缺一张页面就自己退回职业原画。 */
async function cmdPosters(env, opts) {
  if (!opts.dryRun) {
    const gate = requireWriteGate('posters', env, opts);
    if (gate) { gate.forEach(logLine); return 1; }
  }
  const dir = path.join(buildRoot(), env, POSTER_LOCAL);
  const mfPath = path.join(dir, 'posters.json');
  if (!fs.existsSync(mfPath)) { logLine('✗ 找不到底图清单 ' + path.relative(REPO, mfPath) + '（先跑 tools/render-bis-posters.py）'); return 1; }
  let mf;
  try { mf = JSON.parse(fs.readFileSync(mfPath, 'utf8')); } catch (e) { logLine('✗ 底图清单不是合法 JSON：' + e.message); return 1; }
  const errs = [];
  if (mf.product !== 'wow-forever-mini-model-posters' || mf.kind !== 'bis-model-posters') errs.push('底图清单 product/kind 不对');
  const races = Object.keys(mf.posters || {}).sort();
  if (!races.length) errs.push('底图清单是空的');
  if (mf.count !== races.length) errs.push('清单写 ' + mf.count + ' 张，实际 ' + races.length + ' 张');
  const items = [];
  races.forEach((r) => {
    const p = mf.posters[r];
    const file = String(p.file || '');
    if (file.indexOf('/') >= 0 || file.indexOf('..') >= 0 || !new RegExp('^' + r + '-[0-9a-f]{12}\\.png$').test(file)) {
      errs.push(r + ' 的文件名不合规矩：' + file); return;
    }
    const abs = path.join(dir, file);
    if (!fs.existsSync(abs)) { errs.push(r + ' 本地文件不存在：' + file); return; }
    const buf = fs.readFileSync(abs);
    if (buf.length !== p.bytes) errs.push(r + ' 本地字节与清单不符（' + buf.length + ' ≠ ' + p.bytes + '）');
    else if (sha256(buf) !== p.sha256) errs.push(r + ' 本地 SHA-256 与清单不符');
    else items.push({ race: r, file: file, buf: buf, sha: p.sha256 });
  });
  if (errs.length) { errs.slice(0, 10).forEach((e) => logLine('✗ ' + e)); return 1; }

  const creds = loadCreds();
  const total = items.reduce((t, x) => t + x.buf.length, 0);
  logLine('环境 ' + env + ' · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/' + POSTER_DIR + '/'
    + ' · 底图 ' + items.length + ' 张 / ' + kb(total) + ' KB'
    + (opts.dryRun ? '（--dry-run 只读远端，不写）' : '（凭证来源 ' + creds.from + '，已带 ' + WRITE_MARK + '=1）'));
  if (!opts.dryRun && !creds.ok) { logLine(credsHint(creds)); return 1; }
  let uploaded = 0; let unchanged = 0; let forced = 0;
  const failed = []; const violations = [];
  for (const it of items) {
    const key = NAMESPACES[env] + '/' + POSTER_DIR + '/' + it.file;
    const headers = { 'Cache-Control': IMUTABLE_CACHE, 'Content-Type': 'image/png', 'Content-Disposition': ASSET_DISP };
    const head = creds.ok ? await remoteHead(creds, key) : { exists: false };
    if (head.exists) {
      if (head.etag !== md5Hex(it.buf)) { violations.push(it.race + '：远端同名对象字节不同，不覆写'); continue; }
      if (head.forceDownload === 'true') forced += 1;
      unchanged += 1; continue;
    }
    if (opts.dryRun) { uploaded += 1; logLine('  待传 ' + it.race + ' → ' + key + '  ' + kb(it.buf.length) + ' KB'); continue; }
    try {
      const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(key), it.buf, signPut(creds, key, it.buf, headers));
      if (r.statusCode < 200 || r.statusCode >= 300) throw new Error('HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 160));
      const back = await remoteHead(creds, key);
      const g = await raw('GET', creds.bucket, creds.region, '/' + encKey(key), null, signGet(creds, '/' + encKey(key), '/' + key));
      if (back.etag !== md5Hex(it.buf) || g.statusCode !== 200 || sha256(g.body) !== it.sha) throw new Error('回读不符');
      if (back.forceDownload === 'true') forced += 1;
      uploaded += 1;
      logLine('  ✓ ' + it.race + ' · ' + back.bytes + ' B · ' + it.sha.slice(0, 12) + ' · HEAD/GET 回读一致');
    } catch (e) { failed.push(it.race + ' → ' + e.message); }
  }
  if (violations.length) violations.forEach((v) => logLine('  ✗ ' + v));
  if (failed.length) failed.forEach((f) => logLine('  ✗ ' + f));
  logLine('底图：传 ' + uploaded + ' · 已存在跳过 ' + unchanged + ' · 失败 ' + failed.length + ' · 冲突 ' + violations.length
    + ' / 共 ' + items.length + (forced ? ' · ' + forced + ' 张被默认域名强制 attachment' : ''));
  if (opts.dryRun) { logLine('试运行结束，一个字节都没写。'); return 0; }
  return violations.length || failed.length ? 1 : 0;
}

async function cmdUpload(env, opts) {
  if (!opts.dryRun) {
    const gate = requireWriteGate('upload', env, opts);
    if (gate) { gate.forEach(logLine); return 1; }
  }
  let built = buildBatch(env);
  if (built.errors.length) {
    built.errors.slice(0, 25).forEach((e) => logLine('✗ ' + e));
    return 1;
  }
  /* 开关先校再发：这一批正是"这些数据在不在"的那一份，红在这里比红在玩家手机上便宜 */
  const flags = buildFlags(env, { manifest: built.manifest, manifestFrom: '本批 ' + built.buildId });
  if (flags.errors.length) {
    flags.errors.slice(0, 25).forEach((e) => logLine('✗ 开关：' + e));
    return 1;
  }
  const out = writeBatch(env, built, flags);
  const creds = loadCreds();
  logLine('环境 ' + env + ' · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/'
    + ' · 凭证来源 ' + creds.from + (opts.dryRun ? '（--dry-run 只读远端，不写）' : '（已带 ' + WRITE_MARK + '=1）'));
  if (creds.warnMiniCred) { logLine('✗ ' + credsHint(creds)); return 1; }
  if (!opts.dryRun && !creds.ok) { logLine(credsHint(creds)); return 1; }

  const current = creds.ok ? await remotePointer(creds, env) : null;
  const remoteBuildId = current && current.json ? current.json.buildId : null;
  logLine('线上指针：' + (remoteBuildId ? '批次 ' + remoteBuildId + ' · 服务端上传时间 ' + (current.headers['last-modified'] || '未知') : '还没有（第一次发）'));
  if (remoteBuildId === built.buildId) logLine('  指针已指向这一批，下面的传输只是补齐缺件。');

  const targets = built.entries.map((e) => ({ key: buildPrefix(env, built.buildId) + e.path, buf: e.buf, label: e.path }));
  targets.push({ key: NAMESPACES[env] + '/' + built.bundlePath, buf: built.bundleBuf, label: 'files.json（逐文件哈希，verify 用）' });
  targets.push({ key: buildPrefix(env, built.buildId) + 'manifest.json', buf: out.manifestBuf, label: 'builds/manifest.json（批次自带，回滚位）' });

  let uploaded = 0;
  let unchanged = 0;
  const failed = [];
  const violations = [];
  for (const t of targets) {
    let head = { exists: false };
    if (creds.ok) head = await remoteHead(creds, t.key);
    if (head.exists && head.etag && head.etag === md5Hex(t.buf)) {
      /* 字节一样但 Content-Type 不对（上一批素材踩过）：补正元数据，内容没动，不算覆写 */
      if (t.type && head.contentType && head.contentType.split(';')[0] !== t.type) {
        try {
          const r2 = await raw('PUT', creds.bucket, creds.region, '/' + encKey(t.key), t.buf,
            signPut(creds, t.key, t.buf, { 'Cache-Control': IMUTABLE_CACHE, 'Content-Type': t.type }));
          if (r2.statusCode >= 200 && r2.statusCode < 300) { fixed += 1; continue; }
          failed.push(t.label + ' → 补正 Content-Type 失败 HTTP ' + r2.statusCode);
        } catch (e2) { failed.push(t.label + ' → 补正失败 ' + e2.message); }
      }
      unchanged += 1; continue;
    }
    if (head.exists) {
      violations.push(t.label + '：远端已存在但字节不同（远端 ETag ' + (head.etag || '?') + ' ≠ 本批 ' + md5Hex(t.buf) + '）');
      continue;
    }
    if (opts.dryRun) { uploaded += 1; logLine('  待传 ' + t.label + '  ' + kb(t.buf.length) + ' KB'); continue; }
    try {
      const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(t.key), t.buf, signPut(creds, t.key, t.buf, { 'Cache-Control': IMUTABLE_CACHE }));
      if (r.statusCode < 200 || r.statusCode >= 300) throw new Error('HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 200));
      const back = await remoteHead(creds, t.key);
      if (back.etag !== md5Hex(t.buf)) throw new Error('回读 ETag 不匹配');
      uploaded += 1;
    } catch (err) {
      failed.push(t.label + ' → ' + err.message);
    }
  }
  logLine('批次文件：传 ' + uploaded + ' · 内容未变跳过 ' + unchanged + ' · 失败 ' + failed.length + ' · 不可变冲突 ' + violations.length + ' / 共 ' + targets.length);
  if (opts.dryRun) {
    logLine('  开关对象 ' + kb(flags.buf.length) + ' KB 会 PUT 到 ' + flags.key + '（可覆盖，不参与不可变闸）');
    logLine('试运行结束，指针没动、没写任何文件。');
    return 0;
  }
  if (violations.length) {
    violations.slice(0, 10).forEach((v) => logLine('  ✗ ' + v));
    logLine('✗ builds/{buildId}/ 是不可变批次，同一路径内容不同绝不能覆盖——指针保持不动（线上仍是 ' + (remoteBuildId || '空') + '）。');
    logLine('  要么这一批被别处写过（查 bucket 日志），要么 buildId 撞了；先查清再发。');
    return 1;
  }
  if (failed.length) {
    failed.slice(0, 10).forEach((f) => logLine('  ✗ ' + f));
    logLine('✗ 批次没传齐，指针保持不动（线上仍是 ' + (remoteBuildId || '空') + '），不会有半批数据被读到。');
    return 1;
  }

  const ptr = pointerKey(env);
  const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(ptr), out.manifestBuf, signPut(creds, ptr, out.manifestBuf, { 'Cache-Control': POINTER_CACHE }));
  if (r.statusCode < 200 || r.statusCode >= 300) {
    logLine('✗ 换指针失败：HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 300));
    return 1;
  }
  const after = await remotePointer(creds, env);
  const switched = !!after && Buffer.compare(after.body, out.manifestBuf) === 0 && after.json.buildId === built.buildId;
  logLine('指针 → ' + ptr + ' · 批次 ' + built.buildId + ' · ' + (switched ? '回读字节一致' : '回读字节不一致 ✗'));
  if (remoteBuildId && remoteBuildId !== built.buildId) {
    logLine('上一批 ' + remoteBuildId + ' 的文件还在 builds/ 目录里，回滚：node tools/oss-release.js rollback --env ' + env + ' --to ' + remoteBuildId);
  }
  writeBuf(path.join(buildRoot(), env, 'last-upload.json'), dump({
    at: new Date().toISOString(), env, buildId: built.buildId, uploaded, unchanged, failed: failed.length, previousBuildId: remoteBuildId,
    note: '这个时间戳是"本次上传动作"的本地记录，不进批次清单——批次清单必须对同一 buildId 逐字节恒定。'
  }));
  /* 开关对象跟着指针一起发：它是可覆盖的（不参与上面那条"同路径不同字节绝不覆盖"），
     带它的理由不是"必须一起动"，而是别让线上留下"批次是新的、开关还是上一份"这种两边各自合法的错位。 */
  let flagsOk = false;
  if (switched) {
    const fr = await raw('PUT', creds.bucket, creds.region, '/' + encKey(flags.key), flags.buf,
      signPut(creds, flags.key, flags.buf, { 'Cache-Control': POINTER_CACHE }));
    if (fr.statusCode < 200 || fr.statusCode >= 300) {
      logLine('✗ 开关对象没发出去：HTTP ' + fr.statusCode + ' ' + fr.body.toString('utf8').slice(0, 200));
    } else {
      const fh = await remoteHead(creds, flags.key);
      flagsOk = fh.exists && fh.etag === md5Hex(flags.buf) && fh.bytes === flags.buf.length;
      logLine('开关 → ' + flags.key + ' · ' + kb(flags.buf.length) + ' KB · ' + (flagsOk ? '回读 ETag 一致' : '回读不一致 ✗'));
      if (!flagsOk) logLine('  数据已经在新批次上了，开关这一份没对上：客户端退回打包默认值（已公开的页不会被关掉），补跑 flags --env ' + env + ' 即可。');
    }
  }
  return switched && flagsOk ? 0 : 1;
}

async function cmdVerify(env) {
  const creds = loadCreds();
  const localPath = path.join(buildRoot(), env, 'manifest.json');
  if (!fs.existsSync(localPath)) { logLine('✗ 本地没有 ' + env + ' 批次，先跑 build'); return 1; }
  /* verify 全是匿名 GET（bucket 公共读），不需要密钥 */
  const localBuf = fs.readFileSync(localPath);
  const local = JSON.parse(localBuf.toString('utf8'));
  const ptrRemote = NAMESPACES[env] + '/manifest.json';
  const remote = await raw('GET', creds.bucket, creds.region, '/' + encKey(ptrRemote), null, {});
  if (remote.statusCode !== 200) { logLine('✗ 线上指针读不到：HTTP ' + remote.statusCode); return 1; }
  const bad = [];
  /* 清单里没有任何每次构建都变的字段了，所以这里比的是逐字节，不是"除时间外一致" */
  const ptr = JSON.parse(remote.body.toString('utf8'));
  if (Buffer.compare(remote.body, localBuf) !== 0) bad.push('线上指针与本批清单不是同一份字节（内容或 buildId 与本批不同）');
  const selfManifest = await raw('GET', creds.bucket, creds.region,
    '/' + encKey(buildPrefix(env, ptr.buildId) + 'manifest.json'), null, {});
  if (selfManifest.statusCode !== 200) bad.push('批次自带清单读不到 HTTP ' + selfManifest.statusCode + '，回滚位不可用');
  else if (sha256(selfManifest.body) !== sha256(remote.body)) bad.push('指针与批次自带清单不是同一份字节（rollback 会得到不一样的指针）');
  logLine('指针批次 ' + buildIdOf(ptr) + ' · 本地批次 ' + local.buildId + ' → ' + (ptr.buildId === local.buildId ? '同一批' : '不是同一批 ✗'));
  logLine('指针 Cache-Control：' + (remote.headers['cache-control'] || '未设置') + ' · 内容 ' + kb(remote.body.length) + ' KB · 服务端上传时间 ' + (remote.headers['last-modified'] || '未知'));

  const bundleRemote = NAMESPACES[env] + '/' + ptr.bundle.path;
  if (String(ptr.bundle.path).indexOf('builds/' + ptr.buildId + '/') !== 0) bad.push('指针里的 files.json 路径不在本批目录下');
  const bres = await raw('GET', creds.bucket, creds.region, '/' + encKey(bundleRemote), null, {});
  if (bres.statusCode !== 200) { logLine('✗ files.json 读不到 HTTP ' + bres.statusCode); return 1; }
  if (sha256(bres.body) !== ptr.bundle.sha256) bad.push('files.json 哈希与指针不符（可能是半批上传）');
  const bundle = JSON.parse(bres.body.toString('utf8'));
  let bytes = remote.body.length + bres.body.length;
  const keys = Object.keys(bundle.files);
  for (const k of keys) {
    const f = bundle.files[k];
    const r = await raw('GET', creds.bucket, creds.region, '/' + encKey(buildPrefix(env, ptr.buildId) + f.path), null, {});
    if (r.statusCode !== 200) { bad.push(k + ' HTTP ' + r.statusCode); continue; }
    bytes += r.body.length;
    if (sha256(r.body) !== f.sha256) bad.push(k + ' 哈希不符（线上 ' + sha256(r.body).slice(0, 12) + ' ≠ 清单 ' + f.sha256.slice(0, 12) + '）');
    else if (r.body.length !== f.bytes) bad.push(k + ' 字节不符 ' + r.body.length + ' ≠ ' + f.bytes);
    else if (String(r.headers.etag || '').replace(/"/g, '').toUpperCase() !== f.etag) bad.push(k + ' ETag 与清单不符（客户端按这个校验，必须一致）');
    else if (String(r.headers['cache-control'] || '') !== bundle.cacheControl) bad.push(k + ' Cache-Control 是 ' + (r.headers['cache-control'] || '未设置'));
  }
  ['meta', 'glossary', 'dungeonIndex'].forEach((k) => {
    const f = (ptr.fetch || {})[k];
    if (!f || !f.etag || !f.bytes) bad.push('指针的 fetch.' + k + ' 缺 etag/bytes，客户端无法校验');
  });
  /* 开关对象也在 verify 的范围里：它是可覆盖的，所以这里比的不是"字节没被人改过"，
     而是"本地这份计划发出去的开关，线上到底是不是这一份"——改完 flags.json 忘了发，就是在这里红。 */
  const fkey = NAMESPACES[env] + '/' + FLAGS_FILE;
  const fres = await raw('GET', creds.bucket, creds.region, '/' + encKey(fkey), null, {});
  const localFlagsPath = path.join(buildRoot(), env, FLAGS_FILE);
  const plan = buildFlags(env, { manifest: ptr, manifestFrom: '线上批次 ' + ptr.buildId });
  if (fres.statusCode !== 200) {
    bad.push('线上没有 ' + fkey + '（HTTP ' + fres.statusCode + '）：客户端只能按打包默认值走，页面开没开不由线上说了算');
  } else if (plan.errors.length) {
    plan.errors.slice(0, 8).forEach((e) => bad.push('线上开关与这一批对不上：' + e));
  } else if (fs.existsSync(localFlagsPath) && sha256(fres.body) !== sha256(fs.readFileSync(localFlagsPath))) {
    bad.push('线上开关与本地 ' + FLAGS_FILE + ' 不是同一份字节（改过没发？跑 flags --env ' + env + '）');
  } else {
    const fj = JSON.parse(fres.body.toString('utf8'));
    const onNames = Object.keys(fj.features || {}).filter((n) => fj.features[n].on === true);
    logLine('开关 ' + fkey + ' · ' + kb(fres.body.length) + ' KB · 开着的页 [' + onNames.join(' / ') + '] · 服务端上传时间 '
      + (fres.headers['last-modified'] || '未知'));
  }
  logLine('逐文件回读 ' + keys.length + ' 个 · 整批下行 ' + kb(bytes) + ' KB · 问题 ' + bad.length);
  bad.slice(0, 20).forEach((b) => logLine('  ✗ ' + b));
  if (!bad.length) logLine('指针 = 批次自带清单（字节一致，回滚位可用）· 且与本批清单逐字节相同');
  logLine('事实核对日期：' + (ptr.factDates.min || '?') + ' → ' + (ptr.factDates.latest || '?'));
  return bad.length || ptr.buildId !== local.buildId ? 1 : 0;
}

function buildIdOf(m) { return (m && m.buildId) || '?'; }

async function cmdList(env) {
  const creds = loadCreds();
  const dir = path.join(buildRoot(), env, 'builds');
  const localIds = fs.existsSync(dir) ? fs.readdirSync(dir).filter((x) => !x.startsWith('.')) : [];
  logLine('本地 ' + env + ' 批次：' + (localIds.length ? localIds.join(', ') : '（还没有，先跑 build）'));
  logLine('只读查询 · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/ · 凭证来源 ' + creds.from + '（写操作仍需 ' + WRITE_MARK + '=1）');
  if (!creds.ok) { logLine('线上：没找到凭证，跳过列举'); return 0; }
  const res = await listBuilds(creds, env);
  if (!res.ok) { logLine('✗ 线上列举失败 HTTP ' + res.code + ' ' + res.text); return 1; }
  logLine('线上 ' + NAMESPACES[env] + '/builds/：' + (res.buildIds.length ? res.buildIds.join(', ') : '空') + '（对象 ' + res.objectCount + ' 个）');
  const ptr = await remotePointer(creds, env);
  logLine('线上指针指向：' + (ptr && ptr.json ? ptr.json.buildId + ' · ' + ptr.json.counts.files + ' 个文件 · 服务端上传时间 ' + (ptr.headers['last-modified'] || '未知') : '还没有'));
  return 0;
}

/* 回滚不是"把目标清单贴回指针"那么轻：半传批次的自带清单也可能存在，
   指过去就是把一批残缺数据变成线上数据。所以先把目标批次整批点清，再动指针。 */
async function verifyBatchForRollback(creds, env, to, manifest, selfRaw) {
  const problems = [];
  if (manifest.buildId !== to) problems.push('目标目录 builds/' + to + '/ 里的清单写的是 ' + manifest.buildId + '，与 --to 不符');
  if (manifest.env !== env) problems.push('该清单是 ' + manifest.env + ' 环境的，不能当 ' + env + ' 的指针');
  if (manifest.product !== PRODUCT) problems.push('该清单的 product 是 ' + manifest.product + '，不是本站的 ' + PRODUCT);
  if (manifest.schemaVersion !== SCHEMA_VERSION) problems.push('该清单的 schemaVersion 是 ' + manifest.schemaVersion + '，客户端只认 ' + SCHEMA_VERSION);
  if (manifest.namespace !== NAMESPACES[env]) problems.push('该清单的 namespace 是 ' + manifest.namespace + '，与 ' + env + ' 不符');
  const inBatch = (p) => String(p || '').indexOf('builds/' + to + '/') === 0;
  const root = buildPrefix(env, to);
  let bundle = null;
  if (!inBatch((manifest.bundle || {}).path)) problems.push('清单里的 files.json 路径不在 builds/' + to + '/ 下：' + (manifest.bundle || {}).path);
  else {
    const bres = await raw('GET', creds.bucket, creds.region, '/' + encKey(NAMESPACES[env] + '/' + manifest.bundle.path), null, {});
    if (bres.statusCode !== 200) problems.push('files.json 读不到 HTTP ' + bres.statusCode);
    else if (sha256(bres.body) !== manifest.bundle.sha256) problems.push('files.json 哈希与清单不符（这批没传齐或被改过）');
    else bundle = JSON.parse(bres.body.toString('utf8'));
    if (bundle && bundle.buildId !== to) problems.push('files.json 的 buildId 是 ' + bundle.buildId + '，与批次 ' + to + ' 不符');
  }
  Object.keys((manifest.fetch) || {}).forEach((k) => {
    if (!inBatch(manifest.fetch[k].path)) problems.push('fetch.' + k + ' 的路径越出本批目录：' + manifest.fetch[k].path);
    if (!manifest.fetch[k].etag || !manifest.fetch[k].bytes) problems.push('fetch.' + k + ' 缺 etag/bytes，客户端无法校验');
  });
  const checked = [];
  if (bundle) {
    for (const k of Object.keys(bundle.files)) {
      const f = bundle.files[k];
      /* files.json 里的 path 是批次内相对路径（与索引条目一致），拼 root 用；
         但绝对路径与 ../ 一律拒绝——拼出来的 key 越出 builds/{to}/ 就等于让这一批指到别处。 */
      if (/^(\.\.\/|\/|builds\/)/.test(String(f.path || ''))) { problems.push(k + ' 的路径越出本批目录：' + f.path); continue; }
      if (!f.sha256 || !f.etag || !f.bytes) { problems.push(k + ' 的清单项缺校验值'); continue; }
      const h = await remoteHead(creds, root + f.path);
      if (!h.exists) problems.push(k + ' 在远端不存在（HTTP ' + h.statusCode + '）——这一批是半批，不能激活');
      else if (String(h.etag) !== String(f.etag)) problems.push(k + ' 远端 ETag ' + h.etag + ' ≠ 清单 ' + f.etag);
      else if (h.bytes && h.bytes !== f.bytes) problems.push(k + ' 远端 ' + h.bytes + ' B ≠ 清单 ' + f.bytes + ' B');
      checked.push(k);
    }
    const self = await raw('GET', creds.bucket, creds.region, '/' + encKey(root + 'manifest.json'), null, {});
    if (self.statusCode !== 200) problems.push('批次自带清单读不到，回滚位不可用');
    else if (Buffer.compare(self.body, selfRaw) !== 0) problems.push('回滚途中自带清单字节变了');
  }
  return { problems, checked: checked.length };
}

async function cmdRollback(env, opts) {
  const gate = requireWriteGate('rollback', env, opts);
  if (gate) { gate.forEach(logLine); return 1; }
  if (!opts.to) { logLine('✗ rollback 要加 --to <buildId>（list 子命令能看有哪些批次）'); return 1; }
  if (!/^[a-f0-9]{12}$/.test(String(opts.to))) { logLine('✗ --to 要的是一个 12 位十六进制批次号，得到的是 ' + opts.to); return 1; }
  const creds = loadCreds();
  if (creds.warnMiniCred) { logLine(credsHint(creds)); return 1; }
  if (!creds.ok) { logLine(credsHint(creds)); return 1; }
  logLine('回滚 ' + env + ' · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/ · 目标批次 ' + opts.to + '（凭证来源 ' + creds.from + '）');

  const key = buildPrefix(env, opts.to) + 'manifest.json';
  const r = await raw('GET', creds.bucket, creds.region, '/' + encKey(key), null, {});
  if (r.statusCode !== 200) { logLine('✗ 批次 ' + opts.to + ' 的自带清单读不到（HTTP ' + r.statusCode + '），不能指回去'); return 1; }
  let manifest;
  try { manifest = JSON.parse(r.body.toString('utf8')); } catch (e) { logLine('✗ 自带清单不是合法 JSON：' + e.message); return 1; }

  const v = await verifyBatchForRollback(creds, env, opts.to, manifest, r.body);
  logLine('目标批次核验：清单项 ' + v.checked + ' 个文件逐个查过 · 问题 ' + v.problems.length);
  if (v.problems.length) {
    v.problems.slice(0, 12).forEach((p) => logLine('  ✗ ' + p));
    logLine('✗ 这一批不完整或身份不对，指针不动（线上仍是原来的批次）。');
    return 1;
  }

  /* 回滚会把玩家能读到的数据整体换一批，开关不动 —— 所以开关有可能指着一批没有这些数据的老值。
     这一页如果正好是开着的，点进去就是个空壳，宁可在这里红一次。 */
  const rollbackFlags = buildFlags(env, { manifest, manifestFrom: '目标批次 ' + opts.to });
  if (rollbackFlags.errors.length) {
    rollbackFlags.errors.slice(0, 25).forEach((e) => logLine('✗ 开关对不上目标批次：' + e));
    if (!opts.yesFlagsMismatch) {
      logLine('✗ 指针不动（线上仍是原来的批次）。要强行回滚：先把用不上的开关关掉再发一次 flags，或加 --yes-flags-mismatch。');
      return 1;
    }
    logLine('  已带 --yes-flags-mismatch，继续回滚（上面这些开着的页在新批次里没数据）。');
  }

  const ptr = pointerKey(env);
  const put = await raw('PUT', creds.bucket, creds.region, '/' + encKey(ptr), r.body, signPut(creds, ptr, r.body, { 'Cache-Control': POINTER_CACHE }));
  if (put.statusCode < 200 || put.statusCode >= 300) { logLine('✗ 回滚写指针失败 HTTP ' + put.statusCode); return 1; }
  const after = await raw('GET', creds.bucket, creds.region, '/' + encKey(ptr), null, {});
  const same = after.statusCode === 200 && Buffer.compare(after.body, r.body) === 0;
  logLine('指针已回到批次 ' + opts.to + ' · ' + (same ? '回读字节与自带清单完全一致' : '回读字节不一致 ✗')
    + ' · 文件 ' + (manifest.counts ? manifest.counts.files : '?') + ' 个');
  if (!same) logLine('✗ 回滚后的指针与自带清单不同字节，线上状态不可信，立刻人工介入。');
  return same ? 0 : 1;
}

/* 把某个环境的整个命名空间清空（发错了、或者要把内测批次撤下来时用）。
   指针和批次一起删，删完客户端只会走打包快照，所以要先在群里说一声。
   release 是线上：--yes-clean 只说明"我知道要删"，--yes-release 才说明"我知道删的是线上"。 */
async function cmdClean(env, opts) {
  const gate = requireWriteGate('clean', env, opts);
  if (gate) { gate.forEach(logLine); return 1; }
  const creds = loadCreds();
  if (creds.warnMiniCred) { logLine(credsHint(creds)); return 1; }
  if (!creds.ok) { logLine(credsHint(creds)); return 1; }
  const prefix = NAMESPACES[env] + '/';
  logLine('目标：bucket ' + creds.bucket + ' · 前缀 ' + prefix + ' · 凭证来源 ' + creds.from);
  const res = await listKeys(creds, prefix);
  if (!res.ok) { logLine('✗ 列举失败 HTTP ' + res.code + ' ' + res.text); return 1; }
  if (res.truncated) { logLine('✗ 对象超过 1000 个，这个命令只处理单页，先手工确认再删'); return 1; }
  logLine('将删除 bucket ' + creds.bucket + ' 前缀 ' + prefix + ' 下的 ' + res.keys.length + ' 个对象');
  let deleted = 0;
  const failed = [];
  for (const key of res.keys) {
    try {
      const r = await raw('DELETE', creds.bucket, creds.region, '/' + encKey(key), null, signDelete(creds, key));
      if (r.statusCode === 204 || r.statusCode === 200) deleted += 1;
      else failed.push(key + ' HTTP ' + r.statusCode);
    } catch (err) { failed.push(key + ' ' + err.message); }
  }
  const after = await listKeys(creds, prefix);
  failed.slice(0, 10).forEach((f) => logLine('  ✗ ' + f));
  if (!after.ok) {
    logLine('✗ 清完无法核验剩余对象（列举 HTTP ' + after.code + '）——已删 ' + deleted + '，必须人工确认 bucket ' + creds.bucket + ' 前缀 ' + prefix + ' 还剩什么。');
    return 1;
  }
  logLine('清后核验：bucket ' + creds.bucket + ' 前缀 ' + prefix + ' 已删 ' + deleted + ' · 失败 ' + failed.length + ' · 剩余 ' + after.keys.length + ' 个对象');
  return failed.length || after.keys.length > 0 ? 1 : 0;
}

/* ---------- 4. 入口 ---------- */

function parseArgs(argv) {
  const cmd = argv[0];
  const opts = { dryRun: false, yesRelease: false, yesClean: false, checkIdentity: false, skipExportCheck: false, yesFlagsMismatch: false };
  let env = 'beta';
  for (let i = 1; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--env') { i += 1; env = argv[i]; }
    else if (a === '--to') { i += 1; opts.to = argv[i]; }
    else if (a === '--set') { i += 1; (opts.models = opts.models || []).push(argv[i]); }
    else if (a === '--index') opts.index = true;
    else if (a === '--dry-run') opts.dryRun = true;
    else if (a === '--yes-release') opts.yesRelease = true;
    else if (a === '--yes-clean') opts.yesClean = true;
    else if (a === '--yes-flags-mismatch') opts.yesFlagsMismatch = true;
    else if (a === '--check-identity') opts.checkIdentity = true;
    else if (a === '--skip-export-check') opts.skipExportCheck = true;
    else { logLine('✗ 不认识的参数 ' + a); process.exit(2); }
  }
  if (['beta', 'release'].indexOf(env) < 0) { logLine('✗ --env 只认 beta 或 release'); process.exit(2); }
  return { cmd, env, opts };
}

function main() {
  const argv = process.argv.slice(2);
  if (!argv.length) {
    logLine('用法：node tools/oss-release.js <build|upload|flags|assets|models|posters|verify|list|rollback|clean> --env beta|release'
      + ' [--dry-run] [--check-identity] [--yes-release] [--to <buildId>] [--yes-clean] [--set <setId>/<faction>]');
    logLine('写命令（upload/flags/assets/models/rollback/clean）必须显式带环境变量 ' + WRITE_MARK + '=1；release 还要 --yes-release。');
    logLine('只拧开关、不动数据：node tools/oss-release.js flags --env beta（改 app/data/flags.json 后跑这一条，约一分钟生效，不用发版）。');
    process.exit(2);
  }
  const { cmd, env, opts } = parseArgs(argv);
  return Promise.resolve()
    .then(() => {
      if (cmd === 'build') return cmdBuild(env, opts);
      if (cmd === 'upload') return cmdUpload(env, opts);
      if (cmd === 'flags') return cmdFlags(env, opts);
      if (cmd === 'verify') return cmdVerify(env);
      if (cmd === 'list') return cmdList(env);
      if (cmd === 'assets') return cmdAssets(env, opts);
      if (cmd === 'models') return cmdModels(env, opts);
      if (cmd === 'posters') return cmdPosters(env, opts);
      if (cmd === 'rollback') return cmdRollback(env, opts);
      if (cmd === 'clean') return cmdClean(env, opts);
      logLine('✗ 没有子命令 ' + cmd);
      return 2;
    })
    .then((rc) => {
      logLine('rc=' + rc);
      process.exit(rc);
    })
    .catch((err) => {
      logLine('✗ ' + (err && err.message ? err.message : err));
      logLine('rc=1');
      process.exit(1);
    });
}

if (require.main === module) main();

module.exports = {
  SCHEMA_VERSION,
  NAMESPACES,
  BUDGET_KB,
  EXPORT_RELS,
  BASE_INPUTS,
  BIS_ITEM_COLS,
  BIS_SLOT_KEYS,
  BIS_SLOT_SIBS,
  BIS_DISCLAIMER,
  buildFlags,
  FLAGS_PRODUCT,
  FLAGS_FILE,
  FLAGS_BUDGET_KB,
  FLAGS_POLICY,
  FLAG_NAME_RE,
  PROF_BANDS,
  PROF_SK_KEYS,
  PROF_SK_COLS,
  PROF_REC_COLS,
  PROF_NODE_COLS,
  PROF_DISCLAIMER,
  PROF_TITLE,
  cmdFlags,
  raceEntry,
  itemCardRow,
  itemStKey,
  CARD_COLS,
  ITEM_ST_LABEL,
  DROPPED_DETAIL_FIELDS,
  WRITE_MARK,
  buildBatch,
  writeBatch,
  loadCreds,
  requireWriteGate,
  reExportCompare,
  assetRelFromSite,
  contentTypeFor,
  assetIndexBuf,
  ASSET_DIR,
  ICON_EXT,
  cmdAssets,
  cmdModels,
  cmdPosters,
  POSTER_DIR,
  modelIndex,
  MODEL_INDEX_KEY,
  MODEL_ASSET_DIR,
  MODEL_MIME,
  listKeys,
  pointerKey,
  buildPrefix,
  encKey,
  md5Hex,
  localCredPath,
  crossCredPath,
  siteSrc,
  setTransportForTest,
  cmdBuild,
  cmdUpload,
  cmdVerify,
  cmdList,
  cmdRollback,
  cmdClean
};
