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

  /* 方块通用外壳：自绘块垫底，本地转存的官方图标盖在上面。
     图标取不到（文件缺失或 onerror）时自动露出自绘块，不留空白；也不热链第三方域名。 */
  function tileWrap(placeholder, iconKey, mod) {
    var img = iconKey ? '<img src="img/icons/' + encodeURIComponent(iconKey) + '.jpg" alt="" loading="lazy" ' +
      'onerror="this.className=\'bad\'">' : '';
    return '<span class="liw t' + (mod ? ' ' + mod : '') + '">' + placeholder + img + '</span>';
  }

  /* 职业方块：职业色渐变 + 中文首字（有本地图标时显示官方职业图标） */
  function classTile(classId, cn, iconKey, mod) {
    var col = CLASS_COLOR[classId] || '#e0a96d';
    var art = '<svg viewBox="0 0 40 40" aria-hidden="true">' +
      '<defs><linearGradient id="g' + classId + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="' + col + '" stop-opacity=".32"/>' +
      '<stop offset="1" stop-color="#12151a"/></linearGradient></defs>' +
      '<rect width="40" height="40" rx="6" fill="url(#g' + classId + ')" stroke="' + col + '" stroke-opacity=".5"/>' +
      '<text x="20" y="26" text-anchor="middle" font-size="16" font-weight="600" fill="' + col + '" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + esc((cn || '?').charAt(0)) + '</text></svg>';
    return tileWrap(art, iconKey, mod);
  }

  /* 副本示意图横幅。
     文字一律放在 HTML 里，不进 SVG —— 之前 SVG 用 preserveAspectRatio="none" 把 320 宽的
     viewBox 拉到 1100+ 像素，连字一起横向拉变形，桌面端副本名全是糊的。
     色相按副本类型给基准值，再按种子小幅浮动：同类副本看起来是一族，不是随机配色。 */
  var DUNGEON_HUE = { new: 32, classic: 200, raid: 288 };
  function dungeonBanner(seed, label, opts) {
    opts = opts || {};
    var h = hash(seed), w = 320, ht = 86, n = 9, i, pts = [];
    var base = DUNGEON_HUE[opts.kind] === undefined ? 32 : DUNGEON_HUE[opts.kind];
    var hue = (base + (h % 21) - 10 + 360) % 360;
    for (i = 0; i <= n; i++) {
      var v = ((h >> (i * 3)) & 31);
      pts.push((w / n * i).toFixed(1) + ',' + (ht - 18 - (v % 20) - (i % 2 ? 0 : 8)).toFixed(1));
    }
    var gid = 'dbng' + (h % 9999);
    var art = '<svg class="dbn-art" viewBox="0 0 ' + w + ' ' + ht + '" preserveAspectRatio="none" aria-hidden="true">' +
      '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="hsl(' + hue + ',32%,18%)"/>' +
      '<stop offset="1" stop-color="hsl(' + hue + ',26%,7%)"/></linearGradient></defs>' +
      '<rect width="' + w + '" height="' + ht + '" fill="url(#' + gid + ')"/>' +
      '<circle cx="' + (w - 46 - h % 44) + '" cy="21" r="8" fill="hsl(' + hue + ',58%,74%)" fill-opacity=".38"/>' +
      '<polygon points="0,' + ht + ' ' + pts.join(' ') + ' ' + w + ',' + ht + '" fill="hsl(' + hue + ',20%,26%)" fill-opacity=".9"/>' +
      '</svg>';
    // 有本地转存的客户端原画就盖在自绘横幅上；图取不到时（onerror）自动露出自绘版
    var photo = opts.art ? '<img class="dbn-art" src="' + esc(opts.art) + '" alt="" loading="lazy" ' +
      'onerror="this.className=\'dbn-art bad\'">' : '';
    return '<div class="dbn2"><span class="dbn2-shade"></span>' + art + photo +
      '<span class="dbn2-mark">' + (opts.art ? '客户端原画 · 本地转存' : '示意图 · 非游戏原画') + '</span>' +
      '<span class="dbn2-txt"><span class="dbn2-n">' + esc(label || '未定名') + '</span>' +
      (opts.sub ? '<span class="dbn2-e">' + esc(opts.sub) + '</span>' : '') + '</span></div>';
  }

  /* 图标缺失时的天赋格占位：按名字生成稳定色块 + 首字 */
  function talentTile(seed, cn) {
    var h = hash(seed), hue = h % 360;
    return '<svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">' +
      '<rect width="28" height="28" rx="4" fill="hsl(' + hue + ',18%,22%)" stroke="hsl(' + hue + ',22%,38%)"/>' +
      '<text x="14" y="19" text-anchor="middle" font-size="12" fill="hsl(' + hue + ',40%,78%)" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + esc((cn || '?').charAt(0)) + '</text></svg>';
  }
  /* 种族方块：阵营色打底（部落偏暖红、联盟偏冷蓝），同阵营内按种子小幅浮动区分。
     无限服新种族的官方图标能不能取到尚未证实，所以一律自绘，不热链第三方图标。 */
  var FACTION_HUE = { horde: 8, alliance: 212 };
  function raceTile(seed, faction, cn, iconKey, mod) {
    var h = hash(seed);
    var base = FACTION_HUE[faction] === undefined ? 40 : FACTION_HUE[faction];
    var hue = (base + (h % 17) - 8 + 360) % 360;
    var art = '<svg viewBox="0 0 40 40" aria-hidden="true">' +
      '<rect width="40" height="40" rx="6" fill="hsl(' + hue + ',30%,17%)" stroke="hsl(' + hue + ',46%,46%)" stroke-opacity=".7"/>' +
      '<text x="20" y="26" text-anchor="middle" font-size="16" font-weight="600" fill="hsl(' + hue + ',62%,76%)" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + esc((cn || '?').charAt(0)) + '</text></svg>';
    return tileWrap(art, iconKey, mod);
  }
  return { classTile: classTile, dungeonBanner: dungeonBanner, talentTile: talentTile, raceTile: raceTile, color: CLASS_COLOR };
})();
