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

    /* 每个网格有没有 baseColor 贴图、贴图多大。
       2026-10-30 真机踩过一次：这一层读材质/贴图用的 API 猜错了，把已经画出来的模型
       判成"一个贴图都没建出来"，还立刻收回原画——站主连看一眼的机会都没有。
       所以现在两条分开：结构没起来＝失败；几何在、只是本站没数到贴图＝geometry，
       画面留着，把读到的形状一起报出去，肉眼才是主证据。 */
    inspect() {
      const out = { meshes: 0, tex: 0, noTex: 0, lines: [], api: [] }
      try {
        const xr = wx.getXrFrameSystem ? wx.getXrFrameSystem() : null
        if (!xr) { this.emit({ state: 'bad', text: '取不到 xr-frame 运行时（这台设备/这版基础库不支持）' }); return }
        const elm = this.scene && this.scene.getElementById && this.scene.getElementById('hero')
        if (!elm) { this.emit({ state: 'bad', text: '场景里没有这一套的模型节点', err: 'node-id=hero 找不到' }); return }
        const gltf = elm.getComponent ? elm.getComponent(xr.GLTF) : null
        if (!gltf) { this.emit({ state: 'bad', text: '模型没被实例化', err: 'hero 上没有 GLTF 组件' }); return }
        const meshes = gltf.meshes || []
        out.meshes = meshes.length
        out.api.push('gltf:' + keysOf(gltf))
        if (meshes.length) out.api.push('mesh[0]:' + keysOf(meshes[0]))
        meshes.forEach((m, i) => {
          const mat = (m && m.material) || (typeof m.getMaterial === 'function' ? m.getMaterial() : null)
          if (!mat) { out.noTex += 1; out.lines.push(i + ':no-material'); return }
          if (i === 0) out.api.push('mat:' + keysOf(mat))
          const got = textureOf(mat)
          if (!got.t) { out.noTex += 1; out.lines.push(i + ':NO-TEXTURE'); return }
          const w = sizeOf(got.t, 'width'), h = sizeOf(got.t, 'height')
          if (w) { out.tex += 1; out.lines.push(i + ':' + w + 'x' + h + '@' + got.via) }
          else { out.noTex += 1; out.lines.push(i + ':' + (got.via === 'none' ? 'NO-TEXTURE' : 'tex-no-size')) }
        })
        const detail = out.lines.join(' ') + ' ｜ ' + out.api.join(' ｜ ')
        if (out.meshes === 0) { this.emit({ state: 'bad', text: '模型里一个网格都没有', err: detail }); return }
        if (out.tex > 0 && out.noTex === 0) {
          this.emit({ state: 'ok', meshes: out.meshes, tex: out.tex, detail: detail })
          return
        }
        if (out.tex === 0) {
          /* 几何在、画面大概率是好的，是我们没数到——不许藏，也不许冒充"成功" */
          this.emit({ state: 'geometry', meshes: out.meshes, tex: 0, noTex: out.noTex, detail: detail })
          return
        }
        this.emit({ state: 'geometry', meshes: out.meshes, tex: out.tex, noTex: out.noTex, detail: detail })
      } catch (e) {
        this.emit({ state: 'bad', text: '检查画面时抛错', err: e.message + ' ｜ ' + out.lines.join(' ') })
      }
    }
  }
})

/* 不同基础库里贴图可能挂在 getTexture / textures / 直接属性 / uniform 上，逐个试，
   并把"是哪条路读到的"一起报出来——下次再判错，日志里就能看出该走哪条。 */
function textureOf(mat) {
  const tries = ['u_baseColorMap', 'u_baseColorTexture', 'baseColorMap']
  for (let i = 0; i < tries.length; i += 1) {
    const n = tries[i]
    try {
      if (typeof mat.getTexture === 'function') { const t = mat.getTexture(n); if (t) return { t: t, via: 'getTexture(' + n + ')' } }
    } catch (e) {}
    try { if (mat.textures && mat.textures[n]) return { t: mat.textures[n], via: 'textures.' + n } } catch (e) {}
    try { if (mat[n]) return { t: mat[n], via: 'direct.' + n } } catch (e) {}
    try {
      if (typeof mat.getUniformValue === 'function') { const t = mat.getUniformValue(n); if (t) return { t: t, via: 'uniform.' + n } }
    } catch (e) {}
  }
  return { t: null, via: 'none' }
}

function sizeOf(t, key) {
  if (!t) return 0
  if (t[key]) return t[key]
  if (t.value && t.value[key]) return t.value[key]
  if (t.texture && t.texture[key]) return t.texture[key]
  if (Array.isArray(t.image) && t.image.length) { return key === 'width' ? t.image.length : (t.image[0] || []).length }
  return 0
}

function keysOf(o) {
  try { return Object.keys(o).slice(0, 10).join(',') } catch (e) { return '?' }
}

function pickErr(e) {
  const d = (e && e.detail) || e || {}
  return String(d.message || d.errMsg || d.error || JSON.stringify(d)).slice(0, 400)
}
