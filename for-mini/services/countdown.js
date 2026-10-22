/* 开服倒计时（2026-10-22 首页改版，站主要顶部 1/4 放这块、开服后自动消失）。
   2026-10-22 站主二次指令："倒计时改成只到天，不再做具体的秒表逻辑" →
   这里只出天数，不出时:分:秒，页面也就不必每秒 setData。
   口径与网页端 app/src/lib/fmt.js 的 LAUNCH_AT 一致：日期只认 data/meta.json 的 launch 一处真相，
   目标时刻取"北京时间 0 点"——国服公告只公布到日（11 月 5 日全球同步上线），
   官方英文那句 11 月 4 日 15:00 PST 折成北京 07:00 是本站推算（timeline.json 里标 L2），
   所以界面只写"到这一天还剩几天"，不冒充知道具体钟点。
   纯函数单独放这里：门禁脚本要用固定时间戳验"过了这天这块自动移除"，不能等到那天再测。 */
const DAY = 86400000
const HOUR = 3600000

/* 'YYYY-MM-DD' → UTC 时刻（北京时间 0 点）。不用 new Date(字符串)：
   iOS 上带空格的日期串解析不稳定，日期数学必须两端同一个结果。 */
function launchInstant(launchDate) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(launchDate || ''))
  if (!m) return null
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])) - 8 * HOUR
}

/* 返回给首页的一块读数：on=false 表示这块不该出现（已开服，或日期没核到）。
   只算"还剩几个整天"：不足 24 小时的那半天显示 0 天，界面那行写"今天开服"。 */
function state(now, launchDate) {
  const at = launchInstant(launchDate)
  if (!at) return { on: false, reason: 'no-date' }
  if (now >= at) return { on: false, reason: 'launched' }
  const p = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(launchDate))
  const d = Math.floor((at - now) / DAY)
  return {
    on: true,
    d: d,
    /* 剩不到一个整天：界面写"就在今天"，不写"0 天" */
    today: d === 0,
    /* 去掉前导 0：界面写「11 月 5 日」，不写「11 月 05 日」 */
    dayText: Number(p[2]) + ' 月 ' + Number(p[3]) + ' 日',
    to: launchDate
  }
}

module.exports = { launchInstant, state }
