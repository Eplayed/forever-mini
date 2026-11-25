var model = require('../../services/share-poster-model')
var analytics = require('../../services/analytics')

var CANVAS_W = 720
var FONT_STACK = 'sans-serif'
var IMAGE_TIMEOUT_MS = 3500

var PALETTE = {
  bg: '#15202f',
  card: '#213241',
  cardAlt: '#1b2b39',
  slotBg: '#121c27',
  scrim: 'rgba(10, 16, 24, 0.72)',
  border: '#806644',
  line: '#385064',
  gold: '#c8a35c',
  goldHi: '#e6c886',
  title: '#f3eee2',
  txt: '#ebdec2',
  dim: '#bec9d1',
  muted: '#9eafbf',
  badgeBg: '#3b2c1a',
  q: {
    0: '#9d9d9d',
    1: '#ffffff',
    2: '#1eff00',
    3: '#4aa3ff',
    4: '#d79bff',
    5: '#ff8000'
  }
}

function measureRowHeight(row) {
  if (row.iconKind === 'route' && row.routeThumbs && row.routeThumbs.length) {
    return 134
  }
  if (row.iconKind === 'dungeon') {
    var dLinesH = Math.max(1, row.titleLines.length) * 30 + Math.min(1, row.subLines.length) * 24
    var miniH = (row.miniIcons && row.miniIcons.length) ? 40 : 0
    return Math.max(106, 24 + dLinesH + miniH)
  }
  if (row.iconKind === 'item') {
    var iLinesH = Math.max(1, row.titleLines.length) * 30 + row.subLines.length * 24
    return Math.max(84, 24 + iLinesH)
  }
  var linesH = Math.max(1, row.titleLines.length) * 32 + row.subLines.length * 24
  return 26 + linesH
}

function measurePageHeight(page) {
  var h = 198
  if (page.titleLines.length > 1) h += 42
  if (page.subtitleLines.length > 1) h += 28
  if (page.noteLines.length) h += 16 + page.noteLines.length * 24
  page.rows.forEach(function (row) {
    h += measureRowHeight(row) + 12
  })
  h += 156
  return Math.max(540, Math.min(1840, h))
}

function drawRoundedRect(ctx, x, y, w, h, r) {
  var rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.lineTo(x + w - rr, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + rr)
  ctx.lineTo(x + w, y + h - rr)
  ctx.quadraticCurveTo(x + w, y + h, x + w - rr, y + h)
  ctx.lineTo(x + rr, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - rr)
  ctx.lineTo(x, y + rr)
  ctx.quadraticCurveTo(x, y, x + rr, y)
  ctx.closePath()
}

function drawCoverImage(ctx, img, x, y, w, h, r, borderColor, borderWidth, fallbackLabel) {
  ctx.save()
  drawRoundedRect(ctx, x, y, w, h, r)
  ctx.fillStyle = PALETTE.slotBg
  ctx.fill()
  ctx.clip()

  if (img && img.width > 0 && img.height > 0) {
    var iw = img.width
    var ih = img.height
    var scale = Math.max(w / iw, h / ih)
    var sw = w / scale
    var sh = h / scale
    var sx = (iw - sw) / 2
    var sy = (ih - sh) / 2
    ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h)
  } else if (fallbackLabel) {
    ctx.fillStyle = PALETTE.gold
    ctx.font = 'bold ' + Math.max(14, Math.round(h * 0.34)) + 'px ' + FONT_STACK
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(String(fallbackLabel).slice(0, 2), x + w / 2, y + h / 2)
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
  }
  ctx.restore()

  ctx.strokeStyle = borderColor || PALETTE.border
  ctx.lineWidth = borderWidth || 1.5
  drawRoundedRect(ctx, x, y, w, h, r)
  ctx.stroke()
}

function trimToWidth(text, maxUnits) {
  var s = String(text || '')
  var w = 0
  var out = ''
  for (var i = 0; i < s.length; i++) {
    var cw = s.charCodeAt(i) > 127 ? 2 : 1.08
    if (w + cw > maxUnits) {
      return out + '…'
    }
    out += s.charAt(i)
    w += cw
  }
  return out
}

function collectPageUrls(page) {
  var seen = {}
  var list = []
  function add(u) {
    if (!u || typeof u !== 'string' || seen[u]) return
    seen[u] = true
    list.push(u)
  }
  ;(page.rows || []).forEach(function (row) {
    add(row.iconUrl)
    add(row.badgeIconUrl)
    ;(row.miniIcons || []).forEach(function (m) { add(m && m.url) })
    ;(row.routeThumbs || []).forEach(function (t) { add(t && t.artUrl) })
  })
  return list
}

function decodeImageOnCanvas(canvas, src) {
  return new Promise(function (resolve) {
    if (!canvas || !canvas.createImage || !src) {
      resolve(null)
      return
    }
    var done = false
    var timer = setTimeout(function () {
      if (done) return
      done = true
      resolve(null)
    }, IMAGE_TIMEOUT_MS)
    var img = canvas.createImage()
    img.onload = function () {
      if (done) return
      done = true
      clearTimeout(timer)
      resolve(img)
    }
    img.onerror = function () {
      if (done) return
      done = true
      clearTimeout(timer)
      resolve(null)
    }
    img.src = src
  })
}

function resolveLocalPath(url, cache) {
  if (cache && cache[url]) return Promise.resolve(cache[url])
  if (typeof wx === 'undefined' || !wx.getImageInfo) {
    return Promise.resolve(url)
  }
  return new Promise(function (resolve) {
    var done = false
    var timer = setTimeout(function () {
      if (done) return
      done = true
      resolve(url)
    }, IMAGE_TIMEOUT_MS)
    wx.getImageInfo({
      src: url,
      success: function (res) {
        if (done) return
        done = true
        clearTimeout(timer)
        var p = (res && res.path) ? res.path : url
        if (cache && res && res.path) cache[url] = res.path
        resolve(p)
      },
      fail: function () {
        if (done) return
        done = true
        clearTimeout(timer)
        resolve(url)
      }
    })
  })
}

function preloadPageImages(canvas, page, localPathCache) {
  var urls = collectPageUrls(page)
  if (!urls.length) return Promise.resolve({})
  var map = {}
  var tasks = urls.map(function (url) {
    return resolveLocalPath(url, localPathCache).then(function (localOrRemote) {
      return decodeImageOnCanvas(canvas, localOrRemote).then(function (img) {
        if (img) {
          map[url] = img
          return
        }
        if (localOrRemote !== url) {
          return decodeImageOnCanvas(canvas, url).then(function (img2) {
            if (img2) map[url] = img2
          })
        }
      })
    })
  })
  return Promise.all(tasks).then(function () { return map })
}

function paintRouteRow(ctx, row, x, y, w, rowH, imgMap) {
  /* 顶部标签与副标题 */
  ctx.fillStyle = PALETTE.badgeBg
  drawRoundedRect(ctx, x + 16, y + 12, 98, 28, 5)
  ctx.fill()
  ctx.strokeStyle = PALETTE.gold
  ctx.lineWidth = 1
  ctx.stroke()

  ctx.fillStyle = PALETTE.goldHi
  ctx.font = 'bold 18px ' + FONT_STACK
  ctx.textBaseline = 'middle'
  ctx.fillText(row.tag || '跑本顺序', x + 28, y + 26)
  ctx.textBaseline = 'top'

  ctx.fillStyle = PALETTE.dim
  ctx.font = '19px ' + FONT_STACK
  ctx.fillText(row.subLines && row.subLines[0] ? row.subLines[0] : '', x + 126, y + 16)

  /* 副本封面缩略条 */
  var thumbs = row.routeThumbs || []
  var count = Math.min(4, thumbs.length)
  if (!count) return
  var innerW = w - 32
  var arrowW = 22
  var tileW = Math.min(144, Math.floor((innerW - arrowW * (count - 1)) / count))
  var tileH = 72
  var tx = x + 16
  var ty = y + 48

  for (var i = 0; i < count; i++) {
    var t = thumbs[i]
    var img = t.artUrl ? imgMap[t.artUrl] : null
    drawCoverImage(ctx, img, tx, ty, tileW, tileH, 8, PALETTE.gold, 1.5, t.name)

    /* 底部渐变暗遮罩 + 副本名 */
    ctx.save()
    drawRoundedRect(ctx, tx, ty, tileW, tileH, 8)
    ctx.clip()
    ctx.fillStyle = PALETTE.scrim
    ctx.fillRect(tx, ty + tileH - 26, tileW, 26)
    ctx.fillStyle = PALETTE.title
    ctx.font = 'bold 17px ' + FONT_STACK
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(trimToWidth((i + 1) + '.' + t.name, Math.max(8, Math.floor(tileW / 12))), tx + tileW / 2, ty + tileH - 13)
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.restore()

    if (i < count - 1) {
      ctx.fillStyle = PALETTE.goldHi
      ctx.font = 'bold 20px ' + FONT_STACK
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('→', tx + tileW + arrowW / 2, ty + tileH / 2)
      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'
    }
    tx += tileW + arrowW
  }
}

function paintDungeonRow(ctx, row, x, y, w, rowH, imgMap) {
  var qColor = PALETTE.q[row.quality] || PALETTE.txt
  /* 左侧副本实景封面 */
  var thumbSize = 78
  var thumbX = x + 16
  var thumbY = y + Math.round((rowH - thumbSize) / 2)
  var artImg = row.iconUrl ? imgMap[row.iconUrl] : null
  drawCoverImage(ctx, artImg, thumbX, thumbY, thumbSize, thumbSize, 10, PALETTE.gold, 2, row.iconLabel)

  /* 副本图左上角 TOP 徽标 */
  if (row.tag) {
    ctx.fillStyle = PALETTE.badgeBg
    drawRoundedRect(ctx, thumbX + 3, thumbY + 3, 62, 22, 4)
    ctx.fill()
    ctx.strokeStyle = PALETTE.gold
    ctx.lineWidth = 1
    ctx.stroke()
    ctx.fillStyle = PALETTE.goldHi
    ctx.font = 'bold 14px ' + FONT_STACK
    ctx.textBaseline = 'middle'
    ctx.fillText(row.tag, thumbX + 9, thumbY + 14)
    ctx.textBaseline = 'top'
  }

  /* 右侧文字与核心装备图标行 */
  var tx = thumbX + thumbSize + 14
  var curY = y + 12

  ctx.fillStyle = PALETTE.title
  ctx.font = 'bold 23px ' + FONT_STACK
  row.titleLines.forEach(function (line) {
    ctx.fillText(line, tx, curY)
    curY += 30
  })

  /* 适用职业简述（仅保留第一行，避免与装备图标抢空间） */
  if (row.subLines && row.subLines.length) {
    var firstSub = row.subLines[0]
    var pipeAt = firstSub.indexOf('|')
    var cleanSub = (row.miniIcons && row.miniIcons.length && pipeAt > 0) ? firstSub.slice(0, pipeAt).trim() : firstSub
    ctx.fillStyle = PALETTE.dim
    ctx.font = '18px ' + FONT_STACK
    ctx.fillText(cleanSub, tx, curY)
    curY += 24
  }

  /* 3 件核心装备小图标 + 装备名 */
  var minis = row.miniIcons || []
  if (minis.length) {
    var iconSize = 30
    var availW = (x + w - 16) - tx
    var colW = Math.floor(availW / minis.length)
    var mx = tx
    for (var i = 0; i < minis.length; i++) {
      var m = minis[i]
      var mq = PALETTE.q[m.quality] || qColor
      var mImg = m.url ? imgMap[m.url] : null
      drawCoverImage(ctx, mImg, mx, curY + 2, iconSize, iconSize, 5, mq, 1.5, (m.name || '').slice(0, 1))
      ctx.fillStyle = mq
      ctx.font = '17px ' + FONT_STACK
      ctx.textBaseline = 'middle'
      var nameMaxUnits = Math.max(6, Math.floor((colW - iconSize - 10) / 9))
      ctx.fillText(trimToWidth(m.name || '', nameMaxUnits), mx + iconSize + 6, curY + 2 + iconSize / 2)
      ctx.textBaseline = 'top'
      mx += colW
    }
  }
}

function paintItemRow(ctx, row, x, y, w, rowH, imgMap) {
  var qColor = PALETTE.q[row.quality] || PALETTE.txt
  /* 左侧装备图标 */
  var iconSize = 58
  var iconX = x + 16
  var iconY = y + Math.round((rowH - iconSize) / 2)
  var iconImg = row.iconUrl ? imgMap[row.iconUrl] : null
  drawCoverImage(ctx, iconImg, iconX, iconY, iconSize, iconSize, 8, qColor, 2, row.iconLabel)

  var tx = iconX + iconSize + 14
  var curY = y + 12

  /* 首行：可选副本小图 + 标签 + 装备名 */
  var nameX = tx
  if (row.tag) {
    var tagX = tx
    if (row.badgeIconUrl && imgMap[row.badgeIconUrl]) {
      drawCoverImage(ctx, imgMap[row.badgeIconUrl], tagX, curY + 2, 22, 22, 4, PALETTE.gold, 1, '')
      tagX += 27
    }
    ctx.fillStyle = PALETTE.gold
    ctx.font = 'bold 19px ' + FONT_STACK
    var tagStr = trimToWidth(row.tag, 10)
    ctx.fillText(tagStr, tagX, curY + 2)
    nameX = tagX + Math.round(model.visualWidth(tagStr) * 10.5) + 12
  }

  ctx.fillStyle = qColor
  ctx.font = 'bold 23px ' + FONT_STACK
  row.titleLines.forEach(function (line, li) {
    var drawX = li === 0 ? nameX : tx
    var availUnits = Math.max(10, Math.floor(((x + w - 16) - drawX) / 11.8))
    ctx.fillText(li === 0 ? trimToWidth(line, availUnits) : line, drawX, curY)
    curY += 30
  })

  if (row.subLines && row.subLines.length) {
    ctx.fillStyle = PALETTE.dim
    ctx.font = '19px ' + FONT_STACK
    row.subLines.forEach(function (line) {
      ctx.fillText(line, tx, curY)
      curY += 24
    })
  }
}

function paintPlainRow(ctx, row, x, y, w, rowH) {
  var qColor = PALETTE.q[row.quality] || PALETTE.txt
  ctx.fillStyle = qColor
  ctx.fillRect(x, y + 10, 6, rowH - 20)

  var textX = x + 20
  var curY = y + 12

  if (row.tag) {
    ctx.fillStyle = PALETTE.gold
    ctx.font = 'bold 20px ' + FONT_STACK
    ctx.fillText(row.tag, textX, curY)
    textX = x + 130
  }

  ctx.fillStyle = qColor
  ctx.font = 'bold 24px ' + FONT_STACK
  row.titleLines.forEach(function (line, li) {
    ctx.fillText(line, li === 0 ? textX : x + 20, curY)
    curY += 32
  })

  if (row.subLines.length) {
    ctx.fillStyle = PALETTE.dim
    ctx.font = '20px ' + FONT_STACK
    row.subLines.forEach(function (line) {
      ctx.fillText(line, x + 20, curY)
      curY += 24
    })
  }
}

function paintPage(ctx, page, w, h, imgMap) {
  var imgs = imgMap || {}
  ctx.fillStyle = PALETTE.bg
  ctx.fillRect(0, 0, w, h)

  /* 外金边框 */
  ctx.strokeStyle = PALETTE.border
  ctx.lineWidth = 3
  drawRoundedRect(ctx, 18, 18, w - 36, h - 36, 14)
  ctx.stroke()

  /* 顶部徽标 */
  var y = 44
  ctx.fillStyle = PALETTE.badgeBg
  drawRoundedRect(ctx, 40, y, 210, 38, 6)
  ctx.fill()
  ctx.strokeStyle = PALETTE.gold
  ctx.lineWidth = 1.5
  ctx.stroke()

  ctx.fillStyle = PALETTE.goldHi
  ctx.font = 'bold 21px ' + FONT_STACK
  ctx.textBaseline = 'middle'
  ctx.fillText(page.badge, 56, y + 19)

  if (page.totalPages > 1) {
    ctx.fillStyle = PALETTE.muted
    ctx.font = '20px ' + FONT_STACK
    ctx.textAlign = 'right'
    ctx.fillText('第 ' + (page.pageIndex + 1) + ' / ' + page.totalPages + ' 页', w - 42, y + 19)
    ctx.textAlign = 'left'
  }

  /* 主标题 */
  y += 58
  ctx.fillStyle = PALETTE.title
  ctx.font = 'bold 34px ' + FONT_STACK
  ctx.textBaseline = 'top'
  page.titleLines.forEach(function (line) {
    ctx.fillText(line, 40, y)
    y += 42
  })

  /* 副标题 */
  if (page.subtitleLines.length) {
    ctx.fillStyle = PALETTE.dim
    ctx.font = '22px ' + FONT_STACK
    page.subtitleLines.forEach(function (line) {
      ctx.fillText(line, 40, y)
      y += 28
    })
  }

  /* 口径说明 */
  if (page.noteLines.length) {
    y += 4
    ctx.fillStyle = PALETTE.muted
    ctx.font = '19px ' + FONT_STACK
    page.noteLines.forEach(function (line) {
      ctx.fillText(line, 40, y)
      y += 24
    })
  }

  /* 金色分隔线 */
  y += 10
  ctx.strokeStyle = PALETTE.gold
  ctx.lineWidth = 1.5
  ctx.beginPath()
  ctx.moveTo(40, y)
  ctx.lineTo(w - 40, y)
  ctx.stroke()
  y += 16

  /* 条目列表 */
  var cardX = 36
  var cardW = w - 72
  page.rows.forEach(function (row, idx) {
    var rowH = measureRowHeight(row)
    if (y + rowH > h - 130) return

    ctx.fillStyle = idx % 2 === 0 ? PALETTE.card : PALETTE.cardAlt
    drawRoundedRect(ctx, cardX, y, cardW, rowH, 10)
    ctx.fill()
    ctx.strokeStyle = PALETTE.line
    ctx.lineWidth = 1
    ctx.stroke()

    if (row.iconKind === 'route' && row.routeThumbs && row.routeThumbs.length) {
      paintRouteRow(ctx, row, cardX, y, cardW, rowH, imgs)
    } else if (row.iconKind === 'dungeon') {
      paintDungeonRow(ctx, row, cardX, y, cardW, rowH, imgs)
    } else if (row.iconKind === 'item') {
      paintItemRow(ctx, row, cardX, y, cardW, rowH, imgs)
    } else {
      paintPlainRow(ctx, row, cardX, y, cardW, rowH)
    }

    y += rowH + 12
  })

  /* 底部搜一搜引导栏 */
  var footY = h - 128
  ctx.fillStyle = PALETTE.badgeBg
  drawRoundedRect(ctx, 36, footY, w - 72, 74, 10)
  ctx.fill()
  ctx.strokeStyle = PALETTE.gold
  ctx.lineWidth = 1.5
  ctx.stroke()

  ctx.fillStyle = PALETTE.goldHi
  ctx.font = 'bold 26px ' + FONT_STACK
  ctx.fillText(page.footerBrand, 56, footY + 12)

  ctx.fillStyle = PALETTE.dim
  ctx.font = '19px ' + FONT_STACK
  ctx.fillText(page.footerHint || '微信搜一搜直达完整清单与掉落坐标', 56, footY + 45)

  ctx.fillStyle = PALETTE.muted
  ctx.font = '16px ' + FONT_STACK
  ctx.textAlign = 'center'
  ctx.fillText(page.footerLegal, w / 2, h - 42)
  ctx.textAlign = 'left'
}

Component({
  properties: {
    visible: {
      type: Boolean,
      value: false,
      observer: function (val) {
        if (val) this.startRender()
        else this.invalidate()
      }
    },
    spec: {
      type: Object,
      value: null,
      observer: function () {
        if (this.data.visible) this.startRender()
      }
    }
  },

  data: {
    titleText: '生成分享图',
    pageIndex: 0,
    totalPages: 1,
    previewUrl: '',
    errorText: '',
    rendering: false,
    saving: false,
    canvasW: CANVAS_W,
    canvasH: 960
  },

  lifetimes: {
    attached: function () {
      this.localPathCache = {}
    },
    detached: function () {
      this.invalidate()
    }
  },

  methods: {
    noop: function () {},

    invalidate: function () {
      this.renderSeq = (this.renderSeq || 0) + 1
      this.pageFiles = {}
    },

    close: function () {
      this.invalidate()
      this.triggerEvent('close')
    },

    startRender: function () {
      var spec = this.properties.spec
      if (!spec) return
      var perPage = spec.kind === 'raid_prep' ? 6 : 8
      var pages = model.paginatePoster(spec, perPage)
      this.pages = pages
      this.pageFiles = {}
      this.localPathCache = this.localPathCache || {}
      this.setData({
        titleText: spec.badge || '分享长图',
        pageIndex: 0,
        totalPages: pages.length,
        previewUrl: '',
        errorText: ''
      })
      this.renderCurrentPage(0)
    },

    retryRender: function () {
      this.renderCurrentPage(this.data.pageIndex || 0)
    },

    prevPage: function () {
      var next = (this.data.pageIndex || 0) - 1
      if (next < 0) return
      this.setData({ pageIndex: next })
      this.renderCurrentPage(next)
    },

    nextPage: function () {
      var next = (this.data.pageIndex || 0) + 1
      if (!this.pages || next >= this.pages.length) return
      this.setData({ pageIndex: next })
      this.renderCurrentPage(next)
    },

    renderCurrentPage: function (idx) {
      if (!this.pages || !this.pages[idx]) return
      if (this.pageFiles && this.pageFiles[idx]) {
        this.setData({ previewUrl: this.pageFiles[idx], errorText: '', rendering: false })
        return
      }
      var seq = this.renderSeq = (this.renderSeq || 0) + 1
      var page = this.pages[idx]
      var h = measurePageHeight(page)
      this.setData({ canvasW: CANVAS_W, canvasH: h, rendering: true, previewUrl: '', errorText: '' })

      if (typeof wx === 'undefined' || !wx.createSelectorQuery) {
        this.setData({ rendering: false, errorText: '当前微信版本不支持本地绘卡，请升级微信后重试' })
        analytics.track('poster_generate', { kind: page.kind, result: 'no_api' })
        return
      }

      var query = wx.createSelectorQuery().in(this)
      query.select('#posterCanvas').fields({ node: true, size: true }).exec((res) => {
        if (seq !== this.renderSeq || !this.properties.visible) return
        var item = res && res[0]
        var canvas = item && item.node
        if (!canvas || !canvas.getContext) {
          this.setData({ rendering: false, errorText: '未能初始化画布，请点击重试' })
          analytics.track('poster_generate', { kind: page.kind, result: 'no_canvas' })
          return
        }
        preloadPageImages(canvas, page, this.localPathCache || {}).then((imgMap) => {
          if (seq !== this.renderSeq || !this.properties.visible) return
          try {
            var info = wx.getWindowInfo ? wx.getWindowInfo() : (wx.getSystemInfoSync ? wx.getSystemInfoSync() : {})
            var dpr = Math.min(2, Math.max(1, Number(info.pixelRatio) || 1.5))
            canvas.width = Math.round(CANVAS_W * dpr)
            canvas.height = Math.round(h * dpr)
            var ctx = canvas.getContext('2d')
            ctx.scale(dpr, dpr)
            paintPage(ctx, page, CANVAS_W, h, imgMap)
            wx.canvasToTempFilePath({
              canvas: canvas,
              width: CANVAS_W,
              height: h,
              destWidth: Math.round(CANVAS_W * dpr),
              destHeight: Math.round(h * dpr),
              fileType: 'png',
              success: (out) => {
                if (seq !== this.renderSeq || !this.properties.visible) return
                this.pageFiles[idx] = out.tempFilePath
                this.setData({ previewUrl: out.tempFilePath, rendering: false, errorText: '' })
                analytics.track('poster_generate', { kind: page.kind, result: 'ok' })
              },
              fail: () => {
                if (seq !== this.renderSeq) return
                this.setData({ rendering: false, errorText: '导出图片失败，请点击重试' })
                analytics.track('poster_generate', { kind: page.kind, result: 'export_fail' })
              }
            })
          } catch (err) {
            if (seq !== this.renderSeq) return
            this.setData({ rendering: false, errorText: '绘卡异常，请重试或升级微信客户端' })
            analytics.track('poster_generate', { kind: page.kind, result: 'exception' })
          }
        })
      })
    },

    previewImage: function () {
      if (!this.data.previewUrl || !wx.previewImage) return
      wx.previewImage({
        current: this.data.previewUrl,
        urls: [this.data.previewUrl]
      })
    },

    saveToAlbum: function () {
      var filePath = this.data.previewUrl
      var kind = (this.properties.spec && this.properties.spec.kind) || 'generic'
      if (!filePath || this.data.saving) return
      if (!wx.saveImageToPhotosAlbum) {
        wx.showToast({ title: '请点预览长按保存', icon: 'none' })
        return
      }
      this.setData({ saving: true })
      wx.saveImageToPhotosAlbum({
        filePath: filePath,
        success: () => {
          this.setData({ saving: false })
          analytics.track('poster_save', { kind: kind, result: 'ok' })
          wx.showToast({ title: '已存相册，快去发群吧', icon: 'success' })
        },
        fail: (err) => {
          this.setData({ saving: false })
          var msg = (err && err.errMsg) ? String(err.errMsg) : ''
          if (msg.indexOf('cancel') >= 0) {
            analytics.track('poster_save', { kind: kind, result: 'cancel' })
            return
          }
          if (msg.indexOf('auth deny') >= 0 || msg.indexOf('authorize') >= 0 || msg.indexOf('denied') >= 0) {
            analytics.track('poster_save', { kind: kind, result: 'denied' })
            wx.showModal({
              title: '需要相册权限',
              content: '授权保存到相册后可直接发群；也可以点「预览长按转发」长按保存。',
              confirmText: '去授权',
              success: (r) => {
                if (r.confirm && wx.openSetting) wx.openSetting({})
              }
            })
            return
          }
          analytics.track('poster_save', { kind: kind, result: 'fail' })
          wx.showToast({ title: '保存失败，可点预览长按存图', icon: 'none' })
        }
      })
    }
  }
})
