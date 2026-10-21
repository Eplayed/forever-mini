const GLOSSARY_SNAPSHOT = require('../data/forever-glossary-snapshot')
const META_SNAPSHOT = require('../data/forever-meta-snapshot')
const DUNGEON_SNAPSHOT = require('../data/forever-dungeon-snapshot')
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
  loadGlossary,
  loadMeta,
  noteRecentDungeon,
  toggleFavorite,
  toggleFavoriteDungeon
}
