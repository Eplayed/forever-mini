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
  "L0": 250,
  "L1": 114,
  "L2": 360,
  "L3": 2,
  "total": 726
 },
 "counts": {
  "terms": 215,
  "dungeons": 38,
  "talentNodes": 473,
  "talentNameVerified": 460
 },
 "openQuestions": [
  "天赋结构已按客户端解包核对（格子位置、点数上限、前置连线、层级门槛 5/10/15/20/25/30），473 个节点里 114 个名称与官网中文稿逐字一致；其余名称仍是解包口径，等官方中文稿或实测再收口",
  "3 座团队副本的名称与 BOSS 数量：来源互相矛盾，未采信",
  "每座本的 BOSS 名单：29/35 座已从客户端解包名单拿到（经新手盒子转述，标 L0 但注明是解包）；6 座无限新增本上游还没有，等实测",
  "掉落表：所有来源都是零碎注记，且本站禁止写百分比",
  "Whelgar's Excavation 与 Excavation Site: Wetlands 哪个是正式服英文名",
  "已澄清（2026-10-09 客户端名单）：两者是两座不同的本——奥卡兹监狱（Alcaz Prison，48-53，无限新增）与监狱（The Stockade，24-32，经典）"
 ],
 "rules": [
  "L0 必须至少含一条 official 来源，否则构建失败",
  "掉落字段禁止出现百分比",
  "iconKey 只允许本地文件，出现 http 即失败",
  "缺数据显示「待实测」，禁止编造"
 ]
};
