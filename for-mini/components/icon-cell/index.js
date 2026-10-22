/* 图标/图片格：能取到就显示，取不到（没地址、加载失败、缺图）一律回落自绘块。
   红线：不许热链站内 img/ 路径，也不许出现碎图——所以 binderror 必须接住。 */
const PALETTE = ['#2f3a52', '#3a2f2a', '#26333d', '#33283a', '#2b3a30'];

Component({
  properties: {
    src: { type: String, value: '' },
    label: { type: String, value: '' },
    size: { type: String, value: 'sm' },
    fallbackText: { type: String, value: '' }
  },

  data: { bad: false, initial: '', fbBg: PALETTE[0] },

  observers: {
    'src, label': function (src, label) {
      const t = String(label || '').replace(/[^0-9A-Za-z一-龥]/g, '')
      this.setData({
        bad: false,
        initial: t ? t.charAt(0).toUpperCase() : '?',
        fbBg: PALETTE[hash(String(label || src || '0')) % PALETTE.length]
      })
    }
  },

  methods: {
    onErr() { this.setData({ bad: true }) }
  }
})

function hash(s) {
  let h = 0
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) & 0x7fffffff
  return h
}
