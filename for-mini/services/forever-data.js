const GLOSSARY_SNAPSHOT = require('../data/forever-glossary-snapshot')
const META_SNAPSHOT = require('../data/forever-meta-snapshot')
const DUNGEON_SNAPSHOT = require('../data/forever-dungeon-snapshot')
const CLASS_SNAPSHOT = require('../data/forever-class-snapshot')
const oss = require('./oss-manifest')

/* 2026-10-21 M01：这个文件不再自己发请求。
   以前它把 bucket 的平铺地址（`wow/release/v1/{文件}.json`）写在自己身上，
   拿不到就静默回退缓存——和 PoE 那条线同一个毛病：没有批次身份、没有校验、旧数据能冒充新数据。
   现在取数全部走 services/oss-manifest.js（指针 → 索引 → 分片，四态 + 五项校验），
   这里只留三样东西：**打包快照兜底、收藏、译名文案函数**。
   要改地址只改 oss-manifest.js 的 OSS_ORIGIN / ACTIVE_ENV，别再往页面里散。 */

const FAV_KEY = 'wow_fav_terms_v1'
const FAV_DUNGEON_KEY = oss.CACHE_PREFIX + 'fav_dungeons'
const RECENT_DUNGEON_KEY = oss.CACHE_PREFIX + 'recent_dungeons'
const RECENT_MAX = 8

// 个人主体第一阶段不接任何广告；留空即无广告，勿在页面里判断开关
const ADS = {
  rewardedUnitId: '',
  bannerUnitId: ''
}

const LEVEL_NAME = {
  L0: '已官方核实',
  L1: '仅官方英文',
  L2: '待实测',
  L3: '缺数据'
}

const KIND_NAME = {
  talent: '天赋',
  item: '物品',
  racial: '种族技能',
  skill: '技能',
  dungeon: '副本',
  boss: '首领',
  system: '系统',
  zone: '区域'
}

/* 统一成页面一直在用的形状：{ data, source, sourceText, ... }，
   source 的四种取值与各自义务见 oss-manifest.js 头部注释。 */
function shape(r) {
  return {
    data: r.data,
    source: r.source,
    sourceText: oss.sourceLabel(r),
    cacheHit: !!r.cacheHit,
    requiresUpdate: !!r.requiresUpdate,
    factDates: r.factDates || null,
    buildId: r.buildId || null,
    batch: r.batch || null,
    pointerSource: r.pointerSource || null,
    integrityError: !!r.integrityError,
    error: r.error || null
  }
}

function loadGlossary() {
  return oss.loadKey('glossary', { fallback: GLOSSARY_SNAPSHOT }).then(shape)
}

function loadMeta() {
  return oss.loadKey('meta', { fallback: META_SNAPSHOT }).then(shape)
}

/* 38 本索引全在主包快照里：断网首用也有内容可搜（PRD §4.5）。
   详情与掉落没有快照——分片按 id 走，打进主包就超预算了，断网点详情必须说"详情需联网"。 */
function loadDungeonIndex() {
  return oss.loadKey('dungeonIndex', { fallback: DUNGEON_SNAPSHOT }).then(shape)
}

function loadDungeonDetail(item, batch) {
  return oss.loadDungeonDetail(item, batch).then(shape)
}

function loadDungeonLoot(item, batch) {
  return oss.loadDungeonLoot(item, batch).then(shape)
}

/* 技能速查（M02-2）：职业名单 + 按职业分片，全部走线上，主包里没有快照。
   498 条 340 KB，打进主包会挤掉副本索引那份 60 KB 预算；断网点进这一页
   必须看到"技能表要联网"，不许拿职业名单里的条数冒充内容。 */
function loadSpellClasses() {
  return oss.loadKey('spellClasses').then(shape)
}

function loadSpellClass(item, batch) {
  return oss.loadSpellClass(item, batch).then(shape)
}

/* 职业卡（M03）：种族+职业+矩阵一份索引；天赋按职业分片，点开哪个职业取哪份。
   天赋树只读：门槛没核到之前界面只摆位，不做解锁判定（根 AGENTS.md 第五条）。
   2026-10-22 首页改版：首页第一眼就是"选一个职业看可选种族与种族特长"，
   所以这一份带主包快照兜底（只精简字段，键名与线上一致）；
   天赋树分片仍然没有快照——那才是真需要联网的部分。 */
function loadClassIndex() {
  return oss.loadKey('classIndex', { fallback: CLASS_SNAPSHOT }).then(shape)
}

function loadTalentClass(item, batch) {
  return oss.loadTalentClass(item, batch).then(shape)
}

function loadGuide() {
  return oss.loadKey('guide').then(shape)
}

/* 掉落反查（M02-3）：一整个 118 KB 的表换"任何一件装备都能查"，
   同样不打进主包，断网必须说"这张表要联网"。 */
function loadLootIndex() {
  return oss.loadKey('lootIndex').then(shape)
}

function readList(key) {
  try {
    return wx.getStorageSync(key) || []
  } catch (error) {
    return []
  }
}

function writeList(key, list) {
  try {
    wx.setStorageSync(key, list)
  } catch (error) {
    // 隐私模式下 storage 不可用，收藏与最近查看只在本次会话生效
  }
}

function toggleInList(key, id, cap) {
  const list = readList(key)
  const exists = list.indexOf(id) >= 0
  const next = exists ? list.filter((item) => item !== id) : [id].concat(list)
  writeList(key, cap ? next.slice(0, cap) : next)
  return !exists
}

function getFavorites() {
  return readList(FAV_KEY)
}

function isFavorite(id) {
  return getFavorites().indexOf(id) >= 0
}

function toggleFavorite(id) {
  return toggleInList(FAV_KEY, id)
}

function getFavoriteDungeons() {
  return readList(FAV_DUNGEON_KEY)
}

function isFavoriteDungeon(id) {
  return getFavoriteDungeons().indexOf(id) >= 0
}

function toggleFavoriteDungeon(id) {
  return toggleInList(FAV_DUNGEON_KEY, id)
}

function getRecentDungeons() {
  return readList(RECENT_DUNGEON_KEY)
}

function noteRecentDungeon(id) {
  if (!id) return
  /* 最近查看要的是"提到最前"，不是 toggleInList 那种"已有就移除"，所以自己拼 */
  const list = getRecentDungeons().filter((x) => x !== id)
  writeList(RECENT_DUNGEON_KEY, [id].concat(list).slice(0, RECENT_MAX))
}

function levelName(level) {
  return LEVEL_NAME[level] || LEVEL_NAME.L3
}

function kindName(kind) {
  return KIND_NAME[kind] || kind || '词条'
}

module.exports = {
  ADS,
  FAV_KEY,
  FAV_DUNGEON_KEY,
  RECENT_DUNGEON_KEY,
  OSS_POINTER_URL: oss.pointerUrl(oss.ACTIVE_ENV),
  ACTIVE_ENV: oss.ACTIVE_ENV,
  getFavorites,
  getFavoriteDungeons,
  getRecentDungeons,
  isFavorite,
  isFavoriteDungeon,
  kindName,
  levelName,
  loadDungeonDetail,
  loadDungeonIndex,
  loadDungeonLoot,
  loadClassIndex,
  loadGlossary,
  loadGuide,
  loadLootIndex,
  loadMeta,
  loadSpellClass,
  loadSpellClasses,
  loadTalentClass,
  noteRecentDungeon,
  toggleFavorite,
  toggleFavoriteDungeon
}
