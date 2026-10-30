#!/usr/bin/env node
/* BiS 真实 3D 的客户端契约测试（2026-10-30 C 段）
   ------------------------------------------------------------------
   为什么单独一个脚本：这一段的风险不在"字节对不对"（B3 已逐件回读），
   而在**页面会不会拿错那一件**——借用同职业另一套、拿一份位置没核对过的模型、
   被一份改过的清单指到别处去。这类判断开发者工具里看不出来（模拟器起不了 xr-frame，
   画面永远是一块空盒子），所以把它当纯逻辑测：喂假 wx（可控的网络与 storage），
   真清单直接用 B1 产出那一份（for-mini/oss-build/beta/bis/models/index.json）。

   跑法：node wow-forever-web/tools/mini-bis-model-test.js
   全程不打网络、不碰 bucket、不往 for-mini/ 里写东西（那条老规矩：compileHotReLoad 会打回首页）。 */

const fs = require('fs')
const path = require('path')

const REPO = path.resolve(__dirname, '..', '..')
const MINI = path.join(REPO, 'for-mini')
const IDX_FILE = path.join(MINI, 'oss-build', 'beta', 'bis', 'models', 'index.json')

let pass = 0
let fail = 0
function ok(name, cond, extra) {
  if (cond) { pass += 1; process.stdout.write('  ✓ ' + name + '\n') }
  else { fail += 1; process.stdout.write('  ✗ ' + name + (extra ? '  → ' + extra : '') + '\n') }
}

/* 假 wx：storage 是一个 Map，request 由测试决定回什么；每一次请求都计数 */
let store = {}
let replies = []
let reqs = []
global.wx = {
  getStorageSync: (k) => store[k],
  setStorageSync: (k, v) => { store[k] = v },
  request(o) {
    reqs.push(o.url)
    const r = replies.length > 1 ? replies.shift() : replies[0]
    setTimeout(() => {
      if (!r) { o.fail({ errMsg: 'request:fail 断网' }); return }
      if (r.error) { o.fail({ errMsg: r.error }); return }
      o.success({ statusCode: r.status || 200, data: r.data, header: r.header || {}, headers: r.header || {} })
    }, 0)
  }
}

const oss = require(path.join(MINI, 'services', 'oss-manifest'))
const bisModel = require(path.join(MINI, 'services', 'bis-model'))

function fresh() {
  store = {}
  reqs = []
  bisModel.reset()
}

function idxObj(mutate) {
  const o = JSON.parse(fs.readFileSync(IDX_FILE, 'utf8'))
  if (mutate) mutate(o)
  return o
}
/* 套装分片里的 doll 是 [[部位, 格号, 物品ID]]，页面传的就是这个形状 */
function dollOf(entry, mode) {
  const t = entry.dollSnapshot.map((r) => [r.slot, r.cell, r.item])
  if (mode === 'drop') return t.slice(1)
  if (mode === 'add') return t.concat([['手指', 1, 999999]])
  if (mode === 'swap') { const c = t.slice(); c[0] = [c[0][0], c[0][1], 123456]; return c }
  if (mode === 'cell') { const c = t.slice(); c[c.length - 1] = [c[c.length - 1][0], 7, c[c.length - 1][2]]; return c }
  if (mode === 'shuffle') return t.slice().reverse()
  return t
}
function entryOf(o, setId, fac) {
  return o.models.filter((m) => m.setId === setId && m.faction === fac)[0]
}

function run(name, p) { return p.then((f) => { ok(name, f === true, '返回 ' + f) }, (e) => { ok(name, false, '抛出 ' + e.message) }) }

async function main() {
  if (!fs.existsSync(IDX_FILE)) {
    process.stdout.write('✗ 没有 B1 那份索引（' + IDX_FILE + '），先跑 tools/build-mini-bis-models.py\n')
    process.exit(1)
  }
  const real = idxObj()
  process.stdout.write('\nBiS 真实 3D 契约：拿对那一件、拿不到就明说，绝不冒充\n')
  process.stdout.write('用真清单 ' + path.relative(REPO, IDX_FILE) + ' 的 ' + real.models.length + ' 条\n')

  /* —— 1. 正常命中 —— */
  fresh(); replies = [{ data: real }]
  await run('命中：hunter/alliance 给得出 https + beta 命名空间的地址，文件名带成品哈希',
    bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance'))).then((x) => x.ok === true
      && /^https:\/\/poe2-all-class\.oss-cn-hangzhou\.aliyuncs\.com\/wow\/beta\/v1\/assets\/models\/real\/hunter-alliance-44747dcb05cb\.glb$/.test(x.url)))
  const n1 = reqs.length
  await run('TTL 内再点一次不再取清单', bisModel.load('hunter', 'horde', dollOf(entryOf(real, 'hunter', 'horde'))).then((x) => x.ok === true && reqs.length === n1))
  ok('同一分钟内切套只多发 0 次清单请求', reqs.length === n1)

  /* —— 2. 不许冒充 —— */
  fresh(); replies = [{ data: real }]
  await run('这一套没登记：明说"没有登记的真实模型"，不给地址',
    bisModel.load('不存在的一套', 'alliance', []).then((x) => x.ok === false && !x.url && /没有登记的真实模型/.test(x.reason)))
  await run('阵营写成别的值（neutral）→ 不命中，也不许拿联盟那一件顶上',
    bisModel.load('hunter', 'neutral', dollOf(entryOf(real, 'hunter', 'alliance'))).then((x) =>
      x.ok === false && !x.url && /没有登记的真实模型/.test(x.reason)))

  /* —— 3. 名单变了就要拦 —— */
  for (const mode of ['drop', 'add', 'swap', 'cell']) {
    fresh(); replies = [{ data: real }]
    const label = { drop: '少一件', add: '多一件', swap: '换了物品 ID', cell: '换了格号' }[mode]
    await run('名单' + label + ' → 拦下并回原画（登记 ' + mode + '）',
      bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance'), mode)).then((x) =>
        x.ok === false && !x.url && /逐格没对上|不借用别的套装/.test(x.reason)))
  }
  fresh(); replies = [{ data: real }]
  await run('同样的格子换了顺序 → 不算不一致（不误拦）',
    bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance'), 'shuffle')).then((x) => x.ok === true))

  /* —— 4. 位置没核对过的不许用 —— */
  fresh()
  replies = [{ data: idxObj((o) => { o.models.forEach((m) => { m.placementVerdict = 'MARGINAL' }) }) }]
  await run('placementVerdict 不是 PASS → 拒绝（哪怕精确命中）',
    bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance'))).then((x) =>
      x.ok === false && /没通过核对/.test(x.reason)))

  fresh()
  replies = [{ data: idxObj((o) => { o.models[0].file = 'hunter-alliance-000000000000.glb' }) }]
  await run('文件名里的哈希段与 pngSha256 脱钩 → 拒绝',
    bisModel.load(real.models[0].setId, real.models[0].faction, dollOf(real.models[0])).then((x) =>
      x.ok === false && /pngSha256/.test(x.reason)))

  /* —— 5. 路径防穿越 —— */
  for (const bad of [{ assetDir: '../../etc/' }, { file: '../x/hunter-alliance-44747dcb05cb.glb' },
    { file: 'hunter-alliance-44747dcb05cb.glb?x=1' }, { file: 'abs' }]) {
    fresh()
    replies = [{ data: idxObj((o) => { const t = bad.assetDir ? o.models[0] : o.models[0]; Object.assign(t, bad) }) }]
    await run('清单被改成 ' + JSON.stringify(bad) + ' → 拼不出地址',
      bisModel.load(real.models[0].setId, real.models[0].faction, dollOf(real.models[0])).then((x) =>
        x.ok === false && !x.url && /地址|assetDir|文件名/.test(x.reason)))
  }

  /* —— 6. 一份清单里不许有两条同键 —— */
  fresh()
  replies = [{ data: idxObj((o) => { o.models.push(Object.assign({}, o.models[0])) }) }]
  await run('同一 setId+faction 出现两条 → 拒绝（不"取第一条"）',
    bisModel.load(real.models[0].setId, real.models[0].faction, dollOf(real.models[0])).then((x) =>
      x.ok === false && /重复/.test(x.reason)))

  /* —— 7. 契约与结构不对，整份当没有 —— */
  fresh()
  replies = [{ data: idxObj((o) => { o.schemaVersion = 99 }) }]
  await run('清单契约比客户端新 → 不猜着用',
    bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance'))).then((x) =>
      x.ok === false && /比客户端新|不可用/.test(x.reason || '')))
  fresh()
  replies = [{ data: idxObj((o) => { o.formatVersion = 'glb-jpeg-v9' }) }]
  await run('不是 glb-png-v1 那一代 → 整份拒用',
    bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance'))).then((x) => x.ok === false))
  fresh()
  replies = [{ data: { product: '别人家的', models: [] } }]
  await run('product 不对 → 整份拒用',
    bisModel.load('hunter', 'alliance', []).then((x) => x.ok === false && /不可用/.test(x.reason)))

  /* —— 8. 断网：有缓存照旧能用并说明来源；没缓存就明说 —— */
  fresh(); replies = [{ data: real }]
  await bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance')))
  ok('第一次成功后 storage 里存下了清单', !!store[bisModel.STORE_KEY])
  fresh(); replies = [{ error: 'request:fail 断网' }]
  store[bisModel.STORE_KEY] = { models: real.models, at: Date.now() }
  await run('断网但有缓存（一分钟内）→ 仍给得出同一件、标 cache 且不谎称实时',
    bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance'))).then((x) =>
      x.ok === true && x.source === 'cache' && x.stale === false && /hunter-alliance-44747dcb05cb\.glb$/.test(x.url)))
  fresh(); replies = [{ error: 'request:fail 断网' }]
  store[bisModel.STORE_KEY] = { models: real.models, at: Date.now() - 7 * 60 * 1000 }
  await run('存的那份已超过 max-age=60 那一档 → 标 stale（界面上要能看出来是旧的）',
    bisModel.load('hunter', 'alliance', dollOf(entryOf(real, 'hunter', 'alliance'))).then((x) =>
      x.ok === true && x.source === 'cache' && x.stale === true))
  fresh(); replies = [{ error: 'request:fail 断网' }]
  await run('断网且没缓存 → 明说取不到清单，不显示半截',
    bisModel.load('hunter', 'alliance', []).then((x) => x.ok === false && /取不到模型清单/.test(x.reason)))

  /* —— 9. HTTP 非 200 —— */
  fresh(); replies = [{ status: 404, data: null }]
  await run('清单 404 → 走失败分支（requestRaw 判 HTTP 404）',
    bisModel.load('hunter', 'alliance', []).then((x) => x.ok === false && /404|取不到/.test(x.reason)))

  /* —— 10. 服务端那一份索引必须还是发出去的那一份 —— */
  const crypto = require('crypto')
  const buf = fs.readFileSync(IDX_FILE)
  ok('本地索引 151,443 B / 0aa0062a72f4…（与 B3 远端回读同一条）',
    buf.length === 151443 && crypto.createHash('sha256').update(buf).digest('hex') === '0aa0062a72f4f70f21932263ebbf54f97c94cdae1682535bc548f056cbb5219b')
  ok('清单里 76 条、两套阵营各 38', real.models.length === 76 &&
    real.models.filter((m) => m.faction === 'alliance').length === 38)
  ok('每一条的 assetDir 都是 assets/models/real/', real.models.every((m) => m.assetDir === 'assets/models/real/'))
  ok('地址拼出来不含本机路径', reqs.every((u) => u.indexOf('/Users/') < 0))

  process.stdout.write('\n' + (fail ? '✗ ' : '') + '通过 ' + pass + ' / 失败 ' + fail + '\n')
  process.exit(fail ? 1 : 0)
}

main().catch((e) => { process.stdout.write('\n✗ 测试自身异常：' + (e && e.stack || e) + '\n'); process.exit(1) })
