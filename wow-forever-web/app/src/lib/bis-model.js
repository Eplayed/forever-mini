/* 配装部位 → 模型节点名。
   节点名是 tools/build-bis-placeholder-model.py 烘进 GLB 的，两边只靠这张表对齐，
   所以 app/tests/bis-model.spec.js 直接拿真 bis.json 验"每个部位都映射得到"——
   上游哪天新增一个部位（比如以后有衬衫），那条测试会先红，而不是界面上静默少一件。 */

export const SLOT_NODE = {
  头部: 'head', 项链: 'neck', 肩部: 'shoulder', 背部: 'back', 胸部: 'chest',
  手腕: 'wrist', 手: 'hands', 腰部: 'waist', 腿部: 'legs', 脚: 'feet',
  主手: 'mainhand', 副手: 'offhand', 远程: 'ranged', 圣物: 'relic',
  戒指: ['ring1', 'ring2'],
  饰品: ['trinket1', 'trinket2']
};

/* doll = [{slot, cell, item}]（两套阵营各自的一份）。
   返回 { 节点名: { slot, item, cell } }；认不出的部位收进 unmapped，界面要如实说。 */
export function gearNodes(doll) {
  const out = { unmapped: [] };
  (doll || []).forEach((c) => {
    const m = SLOT_NODE[c.slot];
    if (!m) { out.unmapped.push(c.slot); return; }
    const node = Array.isArray(m) ? (m[(c.cell || 1) - 1] || m[m.length - 1]) : m;
    out[node] = { slot: c.slot, item: c.item, cell: c.cell || 1 };
  });
  return out;
}

/* 品质色从令牌读，不在组件里抄第二份十六进制（tokens.css 的 --q0..--q5 是唯一来源） */
export function qualityColor(q) {
  const n = q == null ? 1 : q;
  const v = getComputedStyle(document.documentElement).getPropertyValue('--q' + Math.max(0, Math.min(5, n)));
  return (v || '#8a8f98').trim() || '#8a8f98';
}
