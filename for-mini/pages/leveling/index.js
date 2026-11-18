const { builds, source } = require('./builds')

const rows = builds.map((build) => ({
  classId: build.classId,
  className: build.className,
  name: build.name,
  feature: build.feature.replace(/\n/g, ' · '),
  complete: build.complete,
  total: build.total,
  mainTreeName: build.mainTreeName,
  mainTalentName: build.mainTalentName,
  classIcon: '/pages/leveling/icons/' + build.classIconKey + '.jpg',
  mainIcon: '/pages/leveling/icons/' + build.mainIconKey + '.jpg',
  url: '/pages/class/index?classId=' + encodeURIComponent(build.classId)
    + '&b=' + encodeURIComponent(build.code) + '&s=' + encodeURIComponent(build.layout)
    + '&mode=' + (build.complete ? 'leveling' : 'partial')
}))

Page({
  data: { rows, source, focus: '' },

  onLoad(query) {
    const focus = query && query.c
    if (rows.some((row) => row.classId === focus)) this.setData({ focus })
  },

  onReady() {
    if (this.data.focus) wx.pageScrollTo({ selector: '#build-' + this.data.focus, duration: 0 })
  },

  onShareAppMessage() {
    return { title: '九职业练级天赋', path: '/pages/leveling/index' }
  },

  onShareTimeline() {
    return { title: '九职业练级天赋' }
  }
})
