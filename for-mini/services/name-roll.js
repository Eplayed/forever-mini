/* 起名的随机逻辑（2026-11-03）
   故意做成"可注入随机数"的纯函数：VERIFY 的固定种子样例就这么打出来，
   不用靠反复手点去碰某一条。页面只传 Math.random 进来。 */

/* 一个职业片的全部名字摊平成一组池：三四个专精混着摇，
   界面不问"这条是哪个专精的"，词库本身就是按专精收的灵感。 */
function poolOf(shard) {
  const out = []
  const ts = (shard && shard.talents) || []
  ts.forEach((t) => {
    ;(t.names || []).forEach((n) => {
      const s = String(n || '').trim()
      if (s) out.push(s)
    })
  })
  return out
}

/* 从池里挑一条；avoid 是上一次的结果（连着摇不重复同一条）。
   池里只有一条时不躲（没得躲），其余情况命中 avoid 就换到另一条。 */
function pick(pool, rnd, avoid) {
  if (!pool || !pool.length) return ''
  if (pool.length === 1) return pool[0]
  let idx = Math.floor(rnd() * pool.length) % pool.length
  if (avoid && pool[idx] === avoid) {
    const step = 1 + Math.floor(rnd() * (pool.length - 1))
    idx = (idx + step) % pool.length
  }
  return pool[idx]
}

module.exports = { poolOf, pick }
