const GLOSSARY_SNAPSHOT = require('../data/forever-glossary-snapshot')
const META_SNAPSHOT = require('../data/forever-meta-snapshot')

// OSS 命名空间与 POE/AI 线完全隔离：bucket 沿用已有备案域名，前缀固定 wow/{env}/
const OSS_ORIGIN = 'https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com'
const BASE_URL = OSS_ORIGIN + '/wow/release/v1'
const CACHE_PREFIX = 'wow_forever_v1_'
const FAV_KEY = 'wow_fav_terms_v1'

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

function requestJson(url) {
  return new Promise((resolve, reject) => {
    wx.request({
      url,
      method: 'GET',
      dataType: 'json',
      timeout: 10000,
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300 && response.data) {
          resolve(response.data)
          return
        }
        reject(new Error('HTTP ' + response.statusCode + ': ' + url))
      },
      fail: reject
    })
  })
}

function readCache(fileName) {
  try {
    return wx.getStorageSync(CACHE_PREFIX + fileName) || null
  } catch (error) {
    return null
  }
}

function writeCache(fileName, payload) {
  try {
    wx.setStorageSync(CACHE_PREFIX + fileName, payload)
  } catch (error) {
    // 缓存写失败不影响本次使用，只是下次断网没有兜底
  }
}

/* 三级回退：OSS 实时 → storage 缓存 → 打包快照。
   source 一路带到界面，界面上必须诚实标出「离线数据」，不许静默呈现。 */
function loadFile(fileName, fallback) {
  return requestJson(BASE_URL + '/' + fileName)
    .then((payload) => {
      writeCache(fileName, payload)
      return { data: payload, source: 'live' }
    })
    .catch((error) => {
      const cached = readCache(fileName)
      if (cached) return { data: cached, source: 'cache', error }
      return { data: fallback, source: 'snapshot', error }
    })
}

function loadGlossary() {
  return loadFile('glossary.json', GLOSSARY_SNAPSHOT)
}

function loadMeta() {
  return loadFile('meta.json', META_SNAPSHOT)
}

function getFavorites() {
  try {
    return wx.getStorageSync(FAV_KEY) || []
  } catch (error) {
    return []
  }
}

function isFavorite(id) {
  return getFavorites().indexOf(id) >= 0
}

function toggleFavorite(id) {
  const list = getFavorites()
  const exists = list.indexOf(id) >= 0
  const next = exists ? list.filter((item) => item !== id) : list.concat([id])
  try {
    wx.setStorageSync(FAV_KEY, next)
  } catch (error) {
    // 隐私模式下 storage 不可用，收藏只在本次会话生效
  }
  return !exists
}

function levelName(level) {
  return LEVEL_NAME[level] || LEVEL_NAME.L3
}

function kindName(kind) {
  return KIND_NAME[kind] || kind || '词条'
}

module.exports = {
  ADS,
  BASE_URL,
  FAV_KEY,
  getFavorites,
  isFavorite,
  kindName,
  levelName,
  loadGlossary,
  loadMeta,
  toggleFavorite
}
