/* 本地生成的占位图形：职业徽标与副本示意图。不引用任何外部美术素材。 */
window.Glyph = (function () {
  function hash(s) {
    s = String(s || '');
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  var CLASS_COLOR = {
    warrior: '#c79c6e', paladin: '#f5c7e9', hunter: '#aad372', rogue: '#fff468', priest: '#ffffff',
    shaman: '#2ed6b1', mage: '#69ccf0', warlock: '#8788ee', druid: '#ff7c0a'
  };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  /* 职业方块：职业色渐变 + 中文首字 */
  function classTile(classId, cn) {
    var col = CLASS_COLOR[classId] || '#e0a96d';
    return '<svg viewBox="0 0 40 40" width="34" height="34" aria-hidden="true">' +
      '<defs><linearGradient id="g' + classId + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="' + col + '" stop-opacity=".32"/>' +
      '<stop offset="1" stop-color="#12151a"/></linearGradient></defs>' +
      '<rect width="40" height="40" rx="6" fill="url(#g' + classId + ')" stroke="' + col + '" stroke-opacity=".5"/>' +
      '<text x="20" y="26" text-anchor="middle" font-size="16" font-weight="600" fill="' + col + '" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + esc((cn || '?').charAt(0)) + '</text></svg>';
  }

  /* 副本示意图：按种子生成天际线轮廓，不含任何游戏原画 */
  function dungeonBanner(seed, label, sub) {
    var h = hash(seed), w = 320, ht = 86;
    var hue = h % 360, hue2 = (h >> 8) % 360;
    var pts = [], n = 9, i;
    for (i = 0; i <= n; i++) {
      var v = ((h >> (i * 3)) & 31);
      pts.push((w / n * i).toFixed(1) + ',' + (ht - 14 - (v % 18) - (i % 2 ? 0 : 6)).toFixed(1));
    }
    return '<svg class="dbn" viewBox="0 0 ' + w + ' ' + ht + '" width="100%" height="' + ht + '" preserveAspectRatio="none" aria-hidden="true">' +
      '<defs><linearGradient id="bg' + (h % 9999) + '" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0" stop-color="hsl(' + hue + ',34%,16%)"/>' +
      '<stop offset="1" stop-color="hsl(' + hue2 + ',28%,8%)"/></linearGradient></defs>' +
      '<rect width="' + w + '" height="' + ht + '" fill="url(#bg' + (h % 9999) + ')"/>' +
      '<polygon points="0,' + ht + ' ' + pts.join(' ') + ' ' + w + ',' + ht + '" fill="hsl(' + hue + ',22%,26%)" fill-opacity=".85"/>' +
      '<circle cx="' + (40 + h % 220) + '" cy="' + (18 + h % 12) + '" r="7" fill="hsl(' + hue + ',60%,72%)" fill-opacity=".55"/>' +
      '<text x="12" y="' + (ht - 14) + '" font-size="15" font-weight="600" fill="#f0e6d6" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + esc(label || '') + '</text>' +
      (sub ? '<text x="12" y="' + (ht - 2) + '" font-size="10.5" fill="#b9c0cc" font-family="ui-monospace,Menlo,monospace">' + esc(sub) + '</text>' : '') +
      '</svg>';
  }

  /* 图标缺失时的天赋格占位：按名字生成稳定色块 + 首字 */
  function talentTile(seed, cn) {
    var h = hash(seed), hue = h % 360;
    return '<svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">' +
      '<rect width="28" height="28" rx="4" fill="hsl(' + hue + ',18%,22%)" stroke="hsl(' + hue + ',22%,38%)"/>' +
      '<text x="14" y="19" text-anchor="middle" font-size="12" fill="hsl(' + hue + ',40%,78%)" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + esc((cn || '?').charAt(0)) + '</text></svg>';
  }
  return { classTile: classTile, dungeonBanner: dungeonBanner, talentTile: talentTile, color: CLASS_COLOR };
})();
