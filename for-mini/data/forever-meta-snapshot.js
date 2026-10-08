/* 自动生成，勿手改：node wow-forever-web/tools/export-mini.js */
module.exports = {
 "site": "无限中文资料站",
 "disclaimer": "非官方粉丝资料站，与暴雪娱乐及网易无关。",
 "dataBaseline": {
  "build": "forever-beta 1.60.x（未逐点核对）",
  "checkedAt": "2026-10-07"
 },
 "launch": "2026-11-05",
 "checkedAt": "2026-10-07",
 "source": "wow-forever-web/src/data",
 "coverage": {
  "L0": 216,
  "L1": 114,
  "L2": 368,
  "L3": 12,
  "total": 710
 },
 "counts": {
  "terms": 215,
  "dungeons": 22,
  "talentNodes": 473,
  "talentNameVerified": 114
 },
 "openQuestions": [
  "九职业天赋结构与名称全部标 L2：需游戏内实测或等官方中文深度解析后升 L0",
  "3 座团队副本的名称与 BOSS 数量：来源互相矛盾，未采信",
  "每座本的 BOSS 名单与数量：无官方来源，只能实测",
  "掉落表：所有来源都是零碎注记，且本站禁止写百分比",
  "Whelgar's Excavation 与 Excavation Site: Wetlands 哪个是正式服英文名",
  "官方 Beta 公告里的「监狱」是新本 Alcaz Prison 还是经典 The Stockade"
 ],
 "rules": [
  "L0 必须至少含一条 official 来源，否则构建失败",
  "掉落字段禁止出现百分比",
  "iconKey 只允许本地文件，出现 http 即失败",
  "缺数据显示「待实测」，禁止编造"
 ]
};
