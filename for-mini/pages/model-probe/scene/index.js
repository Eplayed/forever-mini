/* 探针用的 xr-frame 场景组件（临时，不进正式发布包）。
   为什么必须是"组件 + renderer: xr-frame"而不是页面里直接写 <xr-scene>：
   页面 json 里写 renderer 不生效，<xr-scene> 只会渲染成一个空盒子且零报错
   （2026-10-30 首跑实测；官方示例也是把场景放在组件根上）。 */

Component({
  properties: {
    /* 由页面传：原件 / PNG 候选。路径只在页面一处写，这里不留默认值免得两处漂 */
    src: { type: String, value: '' }
  },

  data: { ready: false },

  lifetimes: {
    detached() {
      this.scene = null
    }
  },

  methods: {
    emit(payload) {
      this.triggerEvent('status', payload || {})
    },

    handleReady(e) {
      this.scene = (e && e.detail && e.detail.value) || null
      if (!this.scene) {
        this.emit({ state: 'bad', text: '失败', err: 'xr-scene bind:ready 没给到场景对象' })
        return
      }
      /* 空场景档：ready 到了就算这一步通过（画面该是绿的），不去取任何资源 */
      if (!this.data.src) {
        this.emit({ state: 'ok', text: '空场景 ready：xr-frame 起来了（画面应是那格绿）', detail: '没加载资源，只看 ready 与清屏色' })
        return
      }
      this.emit({ state: 'loading', text: '场景就绪，取模型中' })
    },

    handleSceneError(e) {
      this.emit({ state: 'bad', text: '失败', err: 'xr-scene error：' + pickErr(e) })
    },

    handleAssetError(e) {
      this.emit({ state: 'bad', text: '失败', err: 'xr-assets error：' + pickErr(e) })
    },

    handleProgress(e) {
      const v = Number((e && e.detail && e.detail.value) || 0)
      this.emit({ state: 'loading', text: '加载中 ' + Math.round(v * 100) + '%' })
    },

    handleLoaded(e) {
      this.emit({ state: 'loading', text: '资源 loaded：' + ((e && e.detail && e.detail.value) || '') })
      this.inspect()
    },

    /* 关键一步：把"画没画出来"变成数——每个网格有没有 baseColor 贴图、贴图多大。
       加载不报错但一张贴图都没建 = 玩家看到一个白模，那也算不通过。 */
    inspect() {
      const out = { meshes: 0, tex: 0, noTex: 0, lines: [], api: [] }
      try {
        const xr = wx.getXrFrameSystem ? wx.getXrFrameSystem() : null
        if (!xr) { this.emit({ state: 'bad', text: '失败', err: 'wx.getXrFrameSystem() 取不到' }); return }
        out.api.push('GLTF=' + !!xr.GLTF)
        const elm = this.scene && this.scene.getElementById && this.scene.getElementById('hero')
        if (!elm) { this.emit({ state: 'bad', text: '失败', err: '场景里找不到 node-id=hero' }); return }
        const gltf = elm.getComponent ? elm.getComponent(xr.GLTF) : null
        if (!gltf) { this.emit({ state: 'bad', text: '失败', err: 'hero 上没有 GLTF 组件（模型没被实例化）' }); return }
        out.api.push('version=' + gltf.version)
        const meshes = gltf.meshes || []
        out.meshes = meshes.length
        meshes.forEach((m, i) => {
          const mat = m && m.material
          if (!mat) { out.noTex += 1; out.lines.push(i + ':no-material'); return }
          let t = null
          try {
            if (typeof mat.getTexture === 'function') t = mat.getTexture('u_baseColorMap')
            if (!t && mat.textures) t = mat.textures.u_baseColorMap
          } catch (err) { out.lines.push(i + ':read-threw') }
          const w = t && (t.width || (t.value && t.value.width) || (t.texture && t.texture.width))
          const h = t && (t.height || (t.value && t.value.height) || (t.texture && t.texture.height))
          if (w) { out.tex += 1; out.lines.push(i + ':' + w + 'x' + h) }
          else { out.noTex += 1; out.lines.push(i + ':' + (t ? 'tex-no-size' : 'NO-TEXTURE')) }
        })
        /* 2026-10-30 真机对过：资源 loaded 后人已经画出来了，但这版 xr-frame 在 loaded 那一刻
           meshes 还是空、version=0——所以"数到 0"只报"没数到"，不再写成失败（那次误判
           把一个带贴图的兽人判成了白模，还收回了画面）。 */
        const counted = out.tex > 0 && out.noTex === 0
        this.emit({
          state: counted ? 'ok' : 'shown',
          text: counted ? '加载成功：贴图都在'
            : '画面已出（本站数到网格 ' + out.meshes + ' 个 / 贴图 ' + out.tex + ' 张，量不全以肉眼为准）',
          meshes: out.meshes, tex: out.tex, noTex: out.noTex, detail: out.lines.join(' ') + ' ｜ ' + out.api.join(' ')
        })
      } catch (e) {
        this.emit({ state: 'bad', text: '失败', err: 'inspect 抛出：' + e.message + ' ｜ ' + JSON.stringify(out.lines) })
      }
    },

    /* 程序化转动：真机手指拖动走 camera-orbit-control，这里验"转了画面真的变" */
    turn(deg) {
      const note = []
      try {
        const elm = this.scene && this.scene.getElementById && this.scene.getElementById('hero')
        if (!elm) { this.emit({ state: 'bad', text: '失败', err: '转动失败：场景里没有 hero' }); return }
        this.__yaw = (this.__yaw || 0) + deg
        const r = elm.rotation
        note.push('rotation=' + (r && r.constructor && r.constructor.name))
        if (r && typeof r.set === 'function') {
          r.set(0, this.__yaw, 0)
          if (typeof elm.updateTRS === 'function') elm.updateTRS()
        } else if (r) { r.y = this.__yaw }
        const back = elm.rotation && elm.rotation.y
        note.push('设定 y=' + this.__yaw + ' 回读 y=' + back)
        this.emit({ yaw: this.__yaw, detail: String(this.__lastDetail || '') + ' ｜ ' + note.join(' ') })
      } catch (e) {
        this.emit({ state: 'bad', text: '失败', err: '转动抛出：' + e.message })
      }
    },

    noteDetail(text) { this.__lastDetail = text }
  }
})

function pickErr(e) {
  const d = (e && e.detail) || e || {}
  return String(d.message || d.errMsg || d.error || JSON.stringify(d)).slice(0, 600)
}
