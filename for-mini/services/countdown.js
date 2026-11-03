/* 开服倒计时（2026-10-22 首页改版，站主要顶部 1/4 放这块、开服后自动消失）。
   2026-10-22 站主二次指令："倒计时改成只到天，不再做具体的秒表逻辑" →
   这里只出天数，不出时:分:秒，页面也就不必每秒 setData。
   2026-11-03 站主确认开服时刻："是 11 月 5 号上午 7 点开服"——目标时刻从"北京 0 点"
   改成"北京 7 点"，与网页端 app/src/lib/fmt.js 的 LAUNCH_AT 仍是同一个瞬间（两边一起改）；
   界面那行小字照旧写"官方公告只公布到日，具体开服时刻以游戏内为准"，不把钟点当官方承诺。
   2026-11-03 站主又定读数口径："距离上线应该是 2 天"（11-03 看 11-05）→
   天数从"整 24 小时数向下取整"改成**按北京日历日做差**：11-03 看 11-05 是 2 天，
   11-04 是 1 天，11-05 当天没到点写"就在今天"，过 7 点整块消失。
   纯函数单独放这里：门禁脚本要用固定时间戳验"过了这天这块自动移除"，不能等到那天再测。 */
const DAY = 86400000
const HOUR = 3600000

/* 'YYYY-MM-DD' → UTC 时刻（北京时间当天 07:00，站主 2026-11-03 确认的开服钟点）。
   不用 new Date(字符串)：iOS 上带空格的日期串解析不稳定，日期数学必须两端同一个结果。 */
function launchInstant(launchDate) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(launchDate || ''))
  if (!m) return null
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])) - 8 * HOUR + 7 * HOUR
}

/* 北京日历日：时间戳 + 8 小时后按整天数落格，即"这一天在北京是几号"。
   纯算术，iOS/安卓两端同一个结果。 */
function bjDay(t) {
  return Math.floor((t + 8 * HOUR) / DAY)
}

/* 返回给首页的一块读数：on=false 表示这块不该出现（已开服，或日期没核到）。
   天数按北京日历日做差（2026-11-03 站主口径），不做 24 小时向下取整。 */
function state(now, launchDate) {
  const at = launchInstant(launchDate)
  if (!at) return { on: false, reason: 'no-date' }
  if (now >= at) return { on: false, reason: 'launched' }
  const p = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(launchDate))
  const d = bjDay(at) - bjDay(now)
  return {
    on: true,
    d: d,
    /* 开服当天、还没到点：界面写"就在今天"，不写"0 天" */
    today: d === 0,
    /* 去掉前导 0：界面写「11 月 5 日」，不写「11 月 05 日」 */
    dayText: Number(p[2]) + ' 月 ' + Number(p[3]) + ' 日',
    to: launchDate
  }
}

module.exports = { launchInstant, state }
