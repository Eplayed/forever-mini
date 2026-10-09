/* 数据加载与覆盖率统计 */
window.WowData = (function () {
  var cache = {};
  function load(path) {
    if (cache[path]) return cache[path];
    cache[path] = fetch(path + '?v=' + Date.now(), { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error(path + ' → HTTP ' + r.status);
        return r.json();
      });
    return cache[path];
  }
  /* 覆盖率一律读 src/data/scale.json（由 build-data.js 在校验时算出并写出）。
     这里以前另算一份，只数术语 + 副本 + 职业，和卡口那份对不上，同一站两个覆盖率互相打脸，已删。 */
  function covBar(t) {
    var keys = ['L0', 'L1', 'L2', 'L3'], names = { L0: '已官方核实', L1: '仅官方英文', L2: '待实测', L3: '缺数据' };
    var total = Math.max(t.total, 1);
    return '<div class="cov">' + keys.map(function (k) {
      return t[k] ? '<i class="' + k + '" style="width:' + (t[k] / total * 100) + '%" title="' + names[k] + ' ' + t[k] + ' 条"></i>' : '';
    }).join('') + '</div>';
  }
  var PILL = { L0: '已官方核实', L1: '仅官方英文', L2: '待实测', L3: '缺数据' };
  function pillName(level) { return PILL[level] || PILL.L3; }
  function pill(level) {
    var l = PILL[level] ? level : 'L3';
    return '<span class="pill ' + l + '">' + PILL[l] + '</span>';
  }
  var TYPE_LABEL = { official_cn: '官方中文', official_en: '官方英文', datamine_cn: '客户端解包',
    fan_db: '第三方资料站', media_cn: '中文转载', video: '实测视频', 'site-promise': '本站承诺', 'site-note': '本站说明' };
  function sources(list) {
    if (!list || !list.length) return '<div class="dim" style="font-size:12px">无来源记录</div>';
    return '<ul class="src">' + list.map(function (s) {
      return '<li><span class="st ' + esc(s.type) + '">' + esc(TYPE_LABEL[s.type] || s.type) + '</span>' +
        (s.url ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(host(s.url)) + '</a>'
               : '<span class="dim">（无外部链接：本站自己的说明）</span>') +
        '<span>' + esc(s.note || '') + '</span>' +
        (s.checkedAt ? '<span class="dim">核对于 ' + esc(s.checkedAt) + '</span>' : '') +
        (s.quote ? '<span class="quote">原文：' + esc(s.quote) + '</span>' : '') + '</li>';
    }).join('') + '</ul>';
  }
  function host(u) { try { var x = new URL(u); return x.host + x.pathname.slice(0, 34) + (x.pathname.length > 34 ? '…' : ''); } catch (e) { return u; } }
  function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function hl(text, q) {
    var t = esc(text || '');
    if (!q) return t;
    var i = t.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return t;
    return t.slice(0, i) + '<mark>' + t.slice(i, i + q.length) + '</mark>' + t.slice(i + q.length);
  }
  function toast(msg) {
    var el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg; el.classList.add('on');
    clearTimeout(el._t); el._t = setTimeout(function () { el.classList.remove('on'); }, 1800);
  }
  function copy(text, label) {
    var done = function () { toast('已复制：' + (label || String(text).slice(0, 12))); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(text); done(); });
    } else { fallback(text); done(); }
  }
  function fallback(text) {
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch (e) { }
    document.body.removeChild(ta);
  }
  return { load: load, pillName: pillName, covBar: covBar, pill: pill, sources: sources, esc: esc, hl: hl, toast: toast, copy: copy };
})();
