/* 装备属性行解析：配装页「这套装备给的属性」这一排合计用。
   输入是本站 items-detail.json 里每件装备的 st 原始中文行，输出按属性名累加。
   这里只认"装备自己给的属性行"，护甲在库里实际有四种档位（2026-10-19 逐档数过，
   见 docs/VERIFY-armor-sum-2026-10-19.md）：

     计入基础护甲    "84点护甲" / "84 点护甲" / "90 护甲" / "护甲值 74"
     不计（加成）    "+60 护甲" / "+90 护甲加成" / "-100 护甲"——不是这件装备的基础护甲行
     不计（效果句）  "装备：…" / "使用：…" / "（2）套装：…" / "击中时可能：…" / 带 % 的句子
     不计（收藏行）  "魔暴龙护甲（0/2）"这类外观收集计数，根本不是属性

   为什么不用"排除法"而用"写法枚举"：排除法要把所有不该算的句子列全，漏一条就多算；
   枚举法漏一条写法就少算——所以 armorLineKind 必须把每一条带"护甲"的行分进上面四个档，
   落进 'other' 的说明库里出现了新写法。tests/item-stats.spec.js 有一条全库断言盯着这个，
   新写法一进来就红，不会再像 2026-10-19 那次一样静默漏掉 "90 护甲"。
*/

export const ATTR_KEYS = ['力量', '敏捷', '耐力', '智力', '精神'];

/* 基础护甲的三种写法（全库 7,948 行逐字核过，只有这三种是装备的基础护甲行） */
const BASE_ARMOR_RE = [/^(\d+)\s*点护甲$/, /^(\d+)\s*护甲$/, /^护甲值\s*(\d+)$/];
/* 加成的护甲与罚值：带正负号，不是这件装备的基础护甲 */
const BONUS_ARMOR_RE = /^[+-]\s*\d+\s*点?护甲(?:加成)?$/;
/* 外观收藏计数行：护甲（已收集/总数） */
const COLLECT_RE = /护甲（\d+\/\d+）$/;
/* 效果句与百分比句里的"护甲"都是在说触发后的变化，不是属性行 */
const EFFECT_MARKS = ['%', '装备', '使用', '套装', '击中时可能', '命中率', '触发', '机会', '持续', '需要', '附魔'];

function armorLine(line) {
  const s = String(line == null ? '' : line).trim();
  if (s.indexOf('护甲') < 0) return 'non-armor';
  for (let i = 0; i < BASE_ARMOR_RE.length; i++) {
    const m = BASE_ARMOR_RE[i].exec(s);
    if (m) return 'base';
  }
  if (BONUS_ARMOR_RE.test(s)) return 'bonus';
  if (COLLECT_RE.test(s)) return 'collect';
  for (let i = 0; i < EFFECT_MARKS.length; i++) {
    if (s.indexOf(EFFECT_MARKS[i]) >= 0) return 'effect';
  }
  return 'other';
}

/* 一条属性行落在哪一档。非护甲行返回 'non-armor'，交给 parseStatLine 判属性。 */
export function armorLineKind(line) {
  return armorLine(line);
}

/* 单行 → { key, value }；不是装备自身属性行就返回 null。 */
export function parseStatLine(line) {
  const s = String(line == null ? '' : line).trim();
  if (!s) return null;
  /* 力量这类只有 "+N 力量" 一种写法（全库数过：无加号的裸属性行 0 条），
     所以这里不额外放开写法，免得把"没见过的行"也当成属性行收进来。 */
  let m = /^\+\s*(\d+)\s*(力量|敏捷|耐力|智力|精神)$/.exec(s);
  if (m) return { key: m[2], value: Number(m[1]) };
  if (armorLine(s) !== 'base') return null;
  for (let i = 0; i < BASE_ARMOR_RE.length; i++) {
    const g = BASE_ARMOR_RE[i].exec(s);
    if (g) return { key: '护甲', value: Number(g[1]) };
  }
  return null;
}

/* 多件装备的属性行 → 合计对象。入参是 [[行…], [行…]]，一件一个数组。
   只做加法：不含职业与种族的基础值，不含附魔与套装效果，也不做任何评价。 */
export function sumStatLines(groups) {
  const out = {};
  (groups || []).forEach((lines) => {
    (lines || []).forEach((l) => {
      const one = parseStatLine(l);
      if (!one) return;
      out[one.key] = (out[one.key] || 0) + one.value;
    });
  });
  return out;
}
