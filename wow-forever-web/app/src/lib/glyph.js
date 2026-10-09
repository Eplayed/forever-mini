/* 自绘占位图形：与旧站 src/js/glyph.js 同一套算法（FNV 哈希定色），
   但只返回参数，不拼 SVG 字符串——SVG 交给组件模板声明，颜色与首字可以单测。 */
import { assetUrl } from './data.js';

export function fnv(s) {
  s = String(s == null ? '' : s);
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

export const CLASS_COLOR = {
  warrior: '#c79c6e', paladin: '#f5c7e9', hunter: '#aad372', rogue: '#fff468', priest: '#ffffff',
  shaman: '#2ed6b1', mage: '#69ccf0', warlock: '#8788ee', druid: '#ff7c0a'
};
const FACTION_HUE = { horde: 8, alliance: 212 };

export function firstChar(cn) {
  const s = String(cn == null ? '' : cn);
  return s.charAt(0) || '?';
}

/* 天赋/物品缺图时的方块：按种子给稳定色 */
export function tileStyle(seed, cn) {
  const hue = fnv(seed) % 360;
  return {
    hue: hue,
    letter: firstChar(cn),
    fill: 'hsl(' + hue + ',18%,22%)',
    stroke: 'hsl(' + hue + ',22%,38%)',
    text: 'hsl(' + hue + ',40%,78%)'
  };
}

export function classStyle(classId, cn) {
  const col = CLASS_COLOR[classId] || '#e0a96d';
  return { color: col, letter: firstChar(cn), gradId: 'g' + classId };
}

export function raceStyle(seed, faction, cn) {
  const h = fnv(seed);
  const base = FACTION_HUE[faction] === undefined ? 40 : FACTION_HUE[faction];
  const hue = (base + (h % 17) - 8 + 360) % 360;
  return {
    hue: hue, letter: firstChar(cn),
    fill: 'hsl(' + hue + ',30%,17%)', stroke: 'hsl(' + hue + ',46%,46%)', text: 'hsl(' + hue + ',62%,76%)'
  };
}

export function iconUrl(key) {
  return assetUrl('img/icons/' + encodeURIComponent(key) + '.jpg');
}
