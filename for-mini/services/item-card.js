/* cards 是位置数组（列名在同片 cardCols 里），按列名取值而不是按序号写死：
   生成器加一列不会把这一页读歪。 */
function joinCard(loot, itemId) {
  if (!loot || !Array.isArray(loot.cards)) return null
  const cols = loot.cardCols || []
  const row = loot.cards.filter((r) => String(r[cols.indexOf('itemId')]) === itemId)[0]
  if (!row) return null
  const at = (k) => (cols.indexOf(k) >= 0 ? row[cols.indexOf(k)] : null)
  return {
    type: at('type'),
    ilvl: at('ilvl'),
    st: at('st') || [],
    sell: at('sell'),
    stKey: at('stKey')
  }
}

module.exports = joinCard
