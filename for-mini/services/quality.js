/* 品质档（2026-10-23 收口）：档名用游戏内自己那一套，与基底 items.json 的 sub 字段同源。
   以前副本页写「常见/优良/稀有」、掉落反查页写「普通/良好/稀有」，
   同一件装备在两屏上档名不一样——颜色是按 quality 下标上的，名字却是各页手抄的。
   颜色不在这里：那是 app.wxss 的 --q0…--q5 令牌，界面用 .q-<档> 类名挂。 */
const QUALITY_NAME = { 1: '普通', 2: '优秀', 3: '精良', 4: '史诗', 5: '传说', 6: '神器' }

function qualityName(q) {
  return QUALITY_NAME[q] || '未说明'
}

/* 排序用的档序：没有品质数的一律排到最后，不猜它是哪一档 */
function qualityRank(q) {
  return QUALITY_NAME[q] ? Number(q) : -1
}

module.exports = { QUALITY_NAME, qualityName, qualityRank }
