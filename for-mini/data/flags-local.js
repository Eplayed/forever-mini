/* 打包内的功能开关默认表（2026-10-27）
   ------------------------------------------------------------------
   远端 wow/{env}/v1/flags.json 取不到时（断网、还没发过、结构不对）就看这一份。
   它存在的意义只有一条：兜底不许有两个方向的错——
     · 不许把已经公开的页关掉（所以 bis 这里必须是 true）；
     · 也不许因为"远端没说关"就把没公开的页放出来（所以没上线的页默认 false）。
   真源在 wow-forever-web/app/data/flags.json；两边的开关名集合必须相等，
   由 tools/oss-release-test.js 那条卡着（名字写歪了就是这里静默兜底、线上没人知道）。

   改这里 = 改代码 = 要发小程序版本。线上想临时拧一个页，改 app/data/flags.json
   再跑 node tools/oss-release.js flags --env beta，约一分钟生效，不用发版。 */
module.exports = {
  features: {
    bis: { on: true },
    professions: { on: false },
    macros: { on: false }
  }
}
