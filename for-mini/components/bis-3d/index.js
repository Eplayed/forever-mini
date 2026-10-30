/* BiS 页的真实模型预览组件（2026-10-30 C 段）。
   为什么必须是"组件 + json 里 renderer: xr-frame"：页面 json 写 renderer 不生效，
   <xr-scene> 只会渲染成一个空盒子且零报错（2026-10-30 首跑实测）。
   场景参数照搬 B2 那台 Android 真机验过的那一份，不改相机、不改灯光、不改清屏色——
   改了就不是"已被证实的那条加载方法"。

   组件自己不判该不该显示：src 由 services/bis-model.js 过了三道闸之后才给进来；
   这里只把"到底画没画出来"变成数与事件——加载不报错但一张贴图都没建＝白模，那也算失败。 */

Component({
  properties: {
    /* 由页面给的 https 地址；路径与哈希都在服务层核过，这里不留默认值免得两处漂 */
    src: { type: String, value: '' }
  },

  lifetimes: {
    detached() { this.scene = null }
  },

  methods: {
    emit(payload) { this.triggerEvent('status', payload || {}) },

    handleReady(e) {
      this.scene = (e && e.detail && e.detail.value) || null
      if (!this.scene) {
        this.emit({ state: 'bad', text: 'xr-scene 的 bind:ready 没给到场景对象' })
        return
      }
      this.emit({ state: 'loading', text: '场景就绪，正在从远端取这一套的模型' })
    },

    handleSceneError(e) { this.emit({ state: 'bad', text: 'xr-scene 报错', err: pickErr(e) }) },

    handleAssetError(e) { this.emit({ state: 'bad', text: '模型没取到', err: pickErr(e) }) },

    handleProgress(e) {
      const v = Number((e && e.detail && e.detail.value) || 0)
      this.emit({ state: 'loading', text: '取模型中 ' + Math.round(v * 100) + '%' })
    },

    handleLoaded() { this.inspect() },

    /* 每个网格有没有 baseColor 贴图、贴图多大：这一层能区分"几何出来了"与"看着像个白模" */
    inspect() {
      const out = { meshes: 0, tex: 0, noTex: 0, lines: [] }
      try {
        const xr = wx.getXrFrameSystem ? wx.getXrFrameSystem() : null
        if (!xr) { this.emit({ state: 'bad', text: '取不到 xr-frame 运行时（这台设备/这版基础库不支持）' }); return }
        const elm = this.scene && this.scene.getElementById && this.scene.getElementById('hero')
        if (!elm) { this.emit({ state: 'bad', text: '场景里没有这一套的模型节点', err: 'node-id=hero 找不到' }); return }
        const gltf = elm.getComponent ? elm.getComponent(xr.GLTF) : null
        if (!gltf) { this.emit({ state: 'bad', text: '模型没被实例化', err: 'hero 上没有 GLTF 组件' }); return }
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
        if (out.tex > 0 && out.noTex === 0) {
          this.emit({ state: 'ok', meshes: out.meshes, tex: out.tex, detail: out.lines.join(' ') })
          return
        }
        this.emit({
          state: 'bad',
          text: out.tex > 0 ? ('有 ' + out.noTex + ' 个网格没建出贴图（会看到白模）') : '一个贴图都没建出来（白模）',
          err: out.lines.join(' '), meshes: out.meshes, tex: out.tex, noTex: out.noTex
        })
      } catch (e) {
        this.emit({ state: 'bad', text: '检查画面时抛错', err: e.message + ' ｜ ' + out.lines.join(' ') })
      }
    }
  }
})

function pickErr(e) {
  const d = (e && e.detail) || e || {}
  return String(d.message || d.errMsg || d.error || JSON.stringify(d)).slice(0, 400)
}
