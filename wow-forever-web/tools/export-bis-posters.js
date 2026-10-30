#!/usr/bin/env node
/* 生成小程序主包里那一份"职业+阵营 → 模型底图"的小表（2026-10-30 站主：
   默认那一格不要职业原画，要"模型穿着这一身"的图；他选的是按种族 6 张那一档）。

   为什么是生成而不是手抄：这张表的两个来源都会变——
   art.json.bisRealModels 里每套登记着 raceId（换种族就换图），
   posters/posters.json 里每张图的名字带内容哈希（重渲一次就换名）。
   手抄一份等于把会变的数钉死在代码里，迟早对不上。

   为什么不放进 bis/index.json（那才是它该去的地方）：那要重发一个数据批次，
   而批次是从 app/data 现算的——工作树里现在有别条线未提交的数据改动，
   为了几张底图把别人没准备好的东西发到线上，这个代价不该由这条功能单付。
   等下一次正常发数据批次时，这张表可以整体搬进去，页面只要改一行取数。

   跑法：node wow-forever-web/tools/export-bis-posters.py 同目录 .js
   产物：for-mini/data/bis-posters.js（主包内，约 1 KB；图片本身在远端，不进包） */
const crypto = require('crypto')
const fs = require('fs')
const path = require('path')

const ROOT = path.resolve(__dirname, '..', '..')
const ART = path.join(ROOT, 'wow-forever-web/app/data/art.json')
const BIS = path.join(ROOT, 'wow-forever-web/app/data/bis.json')
const MANIFEST = path.join(ROOT, 'for-mini/oss-build/beta/posters/posters.json')
const OUT = path.join(ROOT, 'for-mini/data/bis-posters.js')
const POSTER_DIR = 'models/posters/'

const sha256 = (buf) => crypto.createHash('sha256').update(buf).digest('hex')

function main() {
  const errs = []
  const art = JSON.parse(fs.readFileSync(ART, 'utf8'))
  const bis = JSON.parse(fs.readFileSync(BIS, 'utf8'))
  let mf = null
  if (fs.existsSync(MANIFEST)) mf = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'))
  if (!mf || mf.product !== 'wow-forever-mini-model-posters') {
    console.log('✗ 没有底图清单（先跑 tools/render-bis-posters.py）')
    return 1
  }
  const sets = {}
  ;(bis.sets || []).forEach((s) => { sets[s.id] = s })
  const items = ((art.bisRealModels || {}).items) || []

  /* 每个种族一张图；(职业|阵营) 必须只对一个种族——今天成立（18 个组合各一族），
     哪天某职业某阵营出现两种族，这里当场报错停下，而不是悄悄挑一个 */
  const raceOf = {}
  const posterOf = {}
  Object.keys(mf.posters || {}).forEach((race) => {
    const p = mf.posters[race]
    const abs = path.join(path.dirname(MANIFEST), p.file)
    if (!fs.existsSync(abs)) { errs.push(race + ' 清单里的文件不在：' + p.file); return }
    const buf = fs.readFileSync(abs)
    if (buf.length !== p.bytes || sha256(buf) !== p.sha256) { errs.push(race + ' 本地字节/哈希与清单不符'); return }
    posterOf[race] = POSTER_DIR + p.file
  })
  items.forEach((m) => {
    const cls = (sets[m.setId] || {}).cls
    if (!cls) { errs.push(m.setId + '/' + m.faction + ' 在 bis.json 里找不到这套'); return }
    if (!posterOf[m.raceId]) { errs.push(m.setId + '/' + m.faction + ' 的种族 ' + m.raceId + ' 没有底图'); return }
    const k = cls + '|' + m.faction
    if (raceOf[k] && raceOf[k] !== m.raceId) errs.push(k + ' 对应两个种族：' + raceOf[k] + ' 与 ' + m.raceId)
    raceOf[k] = m.raceId
  })
  if (errs.length) { errs.slice(0, 12).forEach((e) => console.log('✗ ' + e)); return 1 }

  const map = {}
  Object.keys(raceOf).sort().forEach((k) => { map[k] = posterOf[raceOf[k]] })
  const body = {
    product: 'wow-forever-mini-bis-posters',
    note: '本文件由 tools/export-bis-posters.js 生成，不要手改。'
      + '键是 <职业>|<阵营>，值是相对 assets/ 的底图路径（文件名带内容哈希，图片在远端不在包里）。'
      + '取不到这张图时页面必须退回职业原画，不许留空格。',
    races: Object.keys(posterOf).sort(),
    map: map
  }
  const text = '/* 生成文件：node wow-forever-web/tools/export-bis-posters.js\n'
    + '   来源 app/data/art.json.bisRealModels + oss-build/beta/posters/posters.json，不要手改。 */\n'
    + 'module.exports = ' + JSON.stringify(body, null, 1) + '\n'
  const before = fs.existsSync(OUT) ? fs.readFileSync(OUT, 'utf8') : ''
  if (before === text) { console.log('底图表未变化：' + path.relative(ROOT, OUT) + '（' + Object.keys(map).length + ' 条）'); return 0 }
  fs.writeFileSync(OUT, text)
  console.log('已写 ' + path.relative(ROOT, OUT) + '：' + Object.keys(map).length + ' 条 (职业|阵营) → 底图，种族 '
    + body.races.join('/') + ' · ' + Buffer.byteLength(text) + ' B')
  return 0
}

if (require.main === module) process.exit(main())
module.exports = { main }
