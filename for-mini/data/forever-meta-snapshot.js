/* 自动生成，勿手改：node wow-forever-web/tools/export-mini.js */
module.exports = {
 "site": "无限中文资料站",
 "disclaimer": "非官方粉丝资料站，与暴雪娱乐及网易无关。",
 "dataBaseline": {
  "note": "各板块的数据分别核对，版本与核对日期见溯源页"
 },
 "launch": "2026-11-05",
 "checkedAt": "2026-10-07",
 "source": "wow-forever-web/app/data",
 "coverage": {
  "L0": 250,
  "L1": 111,
  "L2": 356,
  "L3": 2,
  "total": 719
 },
 "counts": {
  "terms": 215,
  "dungeons": 38,
  "spells": 498,
  "lootRows": 1053,
  "lootItems": 1021,
  "macros": 0,
  "addons": 0,
  "talentNodes": 466,
  "talentNameVerified": 462
 },
 "openQuestions": [
  "天赋结构已按客户端解包核对（格子位置、点数上限、前置连线、层级门槛 5/10/15/20/25/30），473 个节点里 114 个名称与官网中文稿逐字一致；其余名称仍只有解包来源，等官方中文稿或实测再收口",
  "3 座团队副本的名称与 BOSS 数量：来源互相矛盾，先不写",
  "每座本的 BOSS 名单：29/35 座已从客户端解包名单拿到（经第三方资料站转述，记为已核实但注明出自解包）；6 座无限新增本还没有可信名单，等实测",
  "掉落表：所有来源都是零碎注记，且本站禁止写百分比",
  "Whelgar's Excavation 与 Excavation Site: Wetlands 哪个是正式服英文名",
  "已澄清（2026-10-09 客户端名单）：两者是两座不同的本——奥卡兹监狱（Alcaz Prison，48-53，无限新增）与监狱（The Stockade，24-32，经典）"
 ],
 "rules": [
  "标为已核实的数据必须至少含一条官方来源，否则不发",
  "掉落数据一律不写百分比",
  "图标只允许本地文件，出现外链即失败",
  "缺数据显示「待实测」，禁止编造"
 ],
 "uiArt": {
  "tabBg": "keyart/skyborne-bg.webp",
  "cards": {
   "dungeons": "art/dungeons/city-of-dalaran.webp",
   "classes": "art/classbanners/warrior.webp",
   "loots": "gen/cavern-hall.webp",
   "guide": "art/scenes/guangshu.webp",
   "bis": "gen/banner-cloudsea.webp",
   "professions": "gen/prof-table.webp"
  }
 }
};
