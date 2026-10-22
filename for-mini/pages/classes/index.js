const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')

/* 职业 tab（M03）
   站主给的新 IA：种族 → 职业 → 可选职业 → 天赋树。
   玩家面规矩照旧：不挂条数、不挂分级徽标、不写"我们缺什么"；
   天赋树只读摆位，门槛没核到之前不做解锁判定（根 AGENTS.md 第五条）。 */
const FACTION = { alliance: '联盟', horde: '部落' }

Page({
  data: {
    races: [],
    classes: [],
    combos: [],
    expandedRace: '',
    loaded: false,
    offline: false,
    requiresUpdate: false,
    errorText: ''
  },

  onLoad() {
    this.batch = null
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  onShareAppMessage() {
    return { title: '无限职业与种族：可选组合、技能书与天赋树', path: '/pages/classes/index' }
  },

  refresh() {
    return service.loadClassIndex().then((r) => {
      this.batch = r.batch
      const d = r.data || {}
      const classMap = {}
      ;(d.classes || []).forEach((c) => { classMap[c.classId] = c })
      this.classMap = classMap
      /* WXML 里不能用变量当下标取对象（classMap[cid] 不生效），
         所以可选职业在 JS 里先拼成带名字的数组 */
      const races = (d.races || []).map((x) => ({
        id: x.id,
        nameCn: x.nameCn || '中文名待核',
        nameEn: x.nameEn || '',
        factionText: FACTION[x.faction] || x.faction || '',
        /* 种族小图优先走素材层那张（天裔官方 CDN 没有，站主授权用插件里小的） */
        iconUrl: oss.raceIconUrl(this.batch, x),
        subgroup: x.subgroup ? (x.subgroup.nameCn || '') : '',
        traits: (x.traits || []).map((t) => ({
          name: t.name, passive: t.passive, effect: t.effect || '',
          iconUrl: oss.iconUrl(this.batch, t.iconKey)
        })),
        classList: (x.classes || []).map((cid) => ({
          classId: cid,
          nameCn: (classMap[cid] || {}).nameCn || cid
        }))
      }))
      this.setData({
        races,
        classes: (d.classes || []).map((c) => ({
          classId: c.classId,
          nameCn: c.nameCn || '中文名待核',
          nameEn: c.nameEn || '',
          iconUrl: oss.iconUrl(this.batch, c.iconKey),
          hasTalents: !!c.hasTalents
        })),
        /* 组合卡：图标在上、"兽人法师"这样的整名在下（2026-10-22 站主要 3 列上下结构）。
           用职业图标——点它进的是这个职业的天赋页，种族名已经在文字里了 */
        combos: (d.combos || []).map((x) => ({
          label: x.label || (x.raceCn + x.classCn),
          classId: x.classId,
          iconUrl: oss.iconUrl(this.batch, (classMap[x.classId] || {}).iconKey)
        })),
        loaded: true,
        offline: r.source !== 'live',
        requiresUpdate: !!r.requiresUpdate,
        errorText: r.error ? String(r.error.message || r.error).slice(0, 120) : ''
      })
      return null
    })
  },

  onRaceToggle(e) {
    const id = String(e.currentTarget.dataset.id || '')
    this.setData({ expandedRace: this.data.expandedRace === id ? '' : id })
  },

  onPickClass(e) {
    const id = String(e.currentTarget.dataset.id || '')
    if (!id) return
    wx.navigateTo({ url: '/pages/class/index?classId=' + encodeURIComponent(id) })
  }
})
