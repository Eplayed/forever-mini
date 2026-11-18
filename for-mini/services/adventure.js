const KEY = 'wow_forever_v1_adventure'
const FACTIONS = { alliance: '联盟', horde: '部落' }
const EMPTY = { faction: '', plans: [], gear: {} }
let saved

function read() {
  if (saved) return saved
  try {
    const value = wx.getStorageSync(KEY)
    if (value && value.gear) {
      const faction = value.faction || (value.profile && value.profile.faction)
      const plans = Array.isArray(value.plans) ? value.plans : (value.plan ? [value.plan] : [])
      saved = { faction: FACTIONS[faction] ? faction : '', plans, gear: value.gear }
    } else {
      saved = EMPTY
    }
    return saved
  } catch (error) {
    return EMPTY
  }
}

function commit(field, value) {
  read()
  if (!saved) return fail()
  const next = Object.assign({}, saved, { [field]: value })
  try {
    wx.setStorageSync(KEY, next)
    saved = next
    return true
  } catch (error) {
    return fail()
  }
}

function fail() {
  wx.showToast({ title: '保存失败，请重试', icon: 'none' })
  return false
}

function updateEntry(field, id, value) {
  const records = Object.assign({}, read()[field])
  if (value) records[id] = value
  else delete records[id]
  return commit(field, records)
}

function setFaction(faction) {
  return commit('faction', FACTIONS[faction] ? faction : '')
}

function addPlan(dungeon) {
  const plans = read().plans
  if (!dungeon.id || !dungeon.name) return false
  if (plans.some((row) => row.id === dungeon.id)) return true
  return commit('plans', plans.concat({ id: dungeon.id, name: dungeon.name }))
}

function removePlan(id) {
  return commit('plans', read().plans.filter((row) => row.id !== id))
}

function movePlan(id, to) {
  const plans = read().plans
  const from = plans.findIndex((row) => row.id === id)
  if (from < 0 || !Number.isInteger(to) || to < 0 || to >= plans.length) return false
  if (from === to) return true
  const next = plans.slice()
  next.splice(to, 0, next.splice(from, 1)[0])
  return commit('plans', next)
}

function addGearBatch(items) {
  const gear = Object.assign({}, read().gear)
  let added = 0
  items.forEach((item) => {
    const id = String(item.id || '')
    if (!/^\d+$/.test(id) || gear[id]) return
    gear[id] = {
      id,
      name: item.name || '#' + id,
      quality: item.quality == null ? '' : item.quality,
      dungeonId: item.dungeonId || '',
      dungeon: item.dungeon || '',
      boss: item.boss || '',
      source: item.source || '',
      done: false
    }
    added += 1
  })
  if (added && !commit('gear', gear)) return null
  return added
}

function addGear(item) {
  const added = addGearBatch([item])
  if (!added) return false
  wx.showToast({ title: '已加入装备目标', icon: 'none' })
  return true
}

function setGearDone(id, done) {
  const item = read().gear[id]
  return !!item && updateEntry('gear', id, Object.assign({}, item, { done: !!done }))
}

function removeGear(id) {
  return updateEntry('gear', id, null)
}

function matchesQuest(row, faction) {
  return !faction || !row.faction || row.faction === '双方' || row.faction === FACTIONS[faction]
}

function dungeonUrl(id, query) {
  return '/pages/dungeon/index?id=' + encodeURIComponent(id) + (query || '')
}

module.exports = {
  read, setFaction, addPlan, removePlan, movePlan, addGear, addGearBatch,
  setGearDone, removeGear, matchesQuest, dungeonUrl
}
