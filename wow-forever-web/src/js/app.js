/* 页面渲染与交互 */
(function () {
  var D = window.WowData, E = window.TalentEngine;
  var NAV = [['index.html', '首页'], ['talent.html', '天赋计算器'], ['chooser.html', '选职业问答'],
    ['skills.html', '技能书'], ['dungeons.html', '副本手册'], ['systems.html', '系统与新区域'],
    ['glossary.html', '术语速查'], ['provenance.html', '溯源']];
  var LS = 'wfs.build.';
  var page = document.body.getAttribute('data-page');

  function el(id) { return document.getElementById(id); }
  function set(html) { el('main').innerHTML = html; }
  function store(key, val) {
    try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); return null; }
    catch (e) { D.toast('本机存储不可用，方案仅本次有效'); return null; }
  }
  function shell() {
    var now = new Date('2026-11-05T00:00:00+08:00').getTime() - Date.now();
    var d = Math.max(0, Math.floor(now / 86400000)), h = Math.max(0, Math.floor(now / 3600000) % 24);
    el('top').innerHTML = '<div class="in"><div class="brand">无限<span>资料站</span></div><nav class="main">' +
      NAV.map(function (n) {
        // 高亮按文件名比对：page 存的是 data-page（英文键），拿中文标签比永远不命中
        var key = page === 'home' ? 'index' : page;
        return '<a href="' + n[0] + '" class="' + (key === n[0].replace('.html', '') ? 'on' : '') + '">' + n[1] + '</a>';
      }).join('') + '</nav><div class="chip">距上线 ' + d + ' 天 ' + h + ' 时</div></div>';
    Promise.all([D.load('data/meta.json'), D.load('data/classes.json'), D.load('data/glossary.json'), D.load('data/dungeons.json')])
      .then(function (r) {
        var meta = r[0], cov = D.coverage(r[3], r[1], r[2]);
        el('foot').innerHTML = '<div class="in"><span>' + D.esc(meta.disclaimer) + '</span>' +
          '<span>数据口径：<span class="mono">' + D.esc(meta.dataBaseline.build) + '</span>，核对于 ' +
          D.esc(meta.dataBaseline.checkedAt) + '</span>' +
          '<span>词条覆盖率（不含天赋节点）L0 ' + cov.L0 + ' / L1 ' + cov.L1 + ' / L2 ' + cov.L2 + ' / L3 ' + cov.L3 + '</span></div>';
      }).catch(function () { });
  }

  /* ---------- 首页 ---------- */
  function home() {
    Promise.all([D.load('data/classes.json'), D.load('data/glossary.json'), D.load('data/dungeons.json'), D.load('data/meta.json')])
      .then(function (r) {
        var classes = r[0].classes, gl = r[1].items, dg = r[3];
        var cov = D.coverage(r[2], r[0], r[1]);
        var dn = r[2].newDungeons.length;
        set('<div class="card"><h2>《魔兽世界：无限》中文资料</h2>' +
          '<p class="dim">天赋、技能中英对照、副本与掉落。每条数据都标了来源与核对状态——' +
          '没核实的地方直接写「待实测」，不编造。</p>' + D.covBar(cov) +
          '<div class="stats" style="margin-top:12px">' +
          '<div class="stat"><b>' + gl.length + '</b>官方中文词条</div>' +
          '<div class="stat"><b>' + dn + '</b>新副本</div>' +
          '<div class="stat"><b>' + classes.length + '</b>职业</div>' +
          '<div class="stat"><b>11-05</b>上线</div></div></div>' +
          '<div class="banner">本站基于测试服资料整理，正式服 2026-11-05 上线后需整体重核。</div>' +
          '<div class="card"><h2>选职业</h2>' +
          '<p class="dim" style="margin-bottom:var(--s3)">第一次接触无限服、不知道选哪个？' +
          '<a href="chooser.html">做个 7 题玩法问答 →</a>（本站整理，不是强度排行）</p>' +
          '<div class="grid g9">' +
          classes.map(function (c) {
            var n = gl.filter(function (g) { return g.classId === c.id; }).length;
            var lv = c.talentCount ? (c.nameVerified ? 'L2' : 'L2') : 'L3';
            return '<a class="cls" style="text-decoration:none" href="talent.html?c=' + c.id + '">' +
              '<div class="ic">' + (window.Glyph ? Glyph.classTile(c.id, c.cn) : D.esc((c.cn || '?').slice(0, 1))) + '</div><div class="n">' + D.esc(c.cn) + '</div>' +
              '<div class="e">' + D.esc(c.en) + '</div>' +
              '<div style="margin-top:5px">' + D.pill(lv) + '</div>' +
              '<div class="e">' + (c.talentCount || 0) + ' 天赋' +
              (c.nameVerified ? ' · ' + c.nameVerified + ' 名与官网一致' : ' · 待实测') + '</div>' +
              (n ? '<div class="e">官方词条 ' + n + ' 条</div>' : '') + '</a>';
          }).join('') + '</div></div>' +
          '<div class="grid g3">' +
          '<div class="card"><h2>副本手册</h2><p class="dim">' + dn + ' 座新副本名单与等级区间，BOSS 与掉落按实测进度补。</p><a href="dungeons.html">进入 →</a></div>' +
          '<div class="card"><h2>中英术语速查</h2><p class="dim">' + gl.length + ' 条官方中文技能与天赋名，点一下即复制。</p><a href="glossary.html">进入 →</a></div>' +
          '<div class="card"><h2>溯源与覆盖率</h2><p class="dim">哪些已核实、哪些只是线索、哪些根本没有来源，全部摊开。</p><a href="provenance.html">进入 →</a></div></div>');
      }).catch(fail);
  }

  /* ---------- 天赋计算器 ---------- */
  var tstate = { classId: 'hunter', file: null, state: {}, mode: 'add', active: 0 };

  function talent() {
    var q = new URLSearchParams(location.search);
    tstate.classId = q.get('c') || 'hunter';
    Promise.all([D.load('data/classes.json'), D.load('data/glossary.json')]).then(function (r) {
      tstate.classes = r[0].classes; tstate.gloss = r[1].items;
      return loadTree(tstate.classId);
    }).catch(fail);
  }
  function loadTree(cid) {
    D.load('data/talents/' + cid + '.json').then(function (f) {
      tstate.file = f; tstate.demoOnly = false; restore(cid, f);
    }).catch(function () {
      tstate.file = { classId: cid, structureStatus: 'none', dataVersion: '—', trees: [], namePool: [],
        note: '尚未收录该职业的天赋数据' };
      tstate.demoOnly = true; tstate.state = {}; renderTalent();
    });
  }
  function restore(cid, f) {
    var saved = store(LS + cid) || (location.hash ? decodeURIComponent(location.hash.slice(1)) : '');
    var dec = E.decode(saved, f.trees || []);
    tstate.state = dec.state;
    if (dec.bad && saved) D.toast('方案与当前数据版本不完全匹配，已按可识别部分还原');
    renderTalent();
  }
  function renderTalent() {
    var f = tstate.file, c = tstate.classes.filter(function (x) { return x.id === tstate.classId; })[0] || {};
    var pool = (f.namePool || []), trees = f.trees || [], r = E.defaults(f.rules);
    var head = '<div class="card" style="padding-bottom:0"><div class="classbar">' + tstate.classes.map(function (x) {
      return '<button class="cls ' + (x.id === tstate.classId ? 'on' : '') + '" data-c="' + x.id + '" style="min-width:78px">' +
        '<div class="ic">' + (window.Glyph ? Glyph.classTile(x.id, x.cn) : D.esc((x.cn || '?').slice(0, 1))) + '</div><div class="n">' + D.esc(x.cn) + '</div></button>';
    }).join('') + '</div></div>';
    var banner = '';
    if (f.structureStatus === 'none') {
      banner = '<div class="banner">这个职业还没有可入库的天赋数据。' +
        '官网只发过四个职业的深度解析，其余职业要么等官方中文稿，要么等实测核实——不做机翻，也不硬凑。</div>';
    } else if (!trees.length) {
      banner = '<div class="banner">该职业的天赋<b>树结构（层、列、点数上限、前置）尚无可靠来源</b>，' +
        '下面列出的是已核实的官方中文名，等结构核对后归位。' +
        (pool.length ? '想先看交互，可 <button class="ghost" id="demo">载入演示数据</button>' : '') + '</div>';
    } else if (f.structureStatus === 'demo') {
      banner = '<div class="banner gray">当前是<b>演示结构</b>，节点名与位置都不是游戏数据，只用于验证加点逻辑。' +
        '<button class="ghost" id="back">回到真实数据</button></div>';
    } else {
      var vcnt = 0, tcnt = 0, ccnt = 0;
      trees.forEach(function (t) { t.nodes.forEach(function (n) { tcnt++; if (n.nameVerified) vcnt++; if (n.nameConflict) ccnt++; }); });
      banner = '<div class="banner">天赋的名称、系属、点数上限、坐标与前置，来自<b>两个第三方数据挖掘源按坐标对齐</b>（' +
        D.esc(f.dataVersion || '上游数据挖掘') + '），<b>未经游戏内核实</b>。' +
        '本职业 ' + tcnt + ' 个天赋：' + vcnt + ' 个名称与官网中文一致' +
        (ccnt ? '，<b class="alert">' + ccnt + ' 个两源译名不一致（红框，两个叫法都保留）</b>' : '') +
        '。层级点数门槛还没核实，所以只按坐标摆位置、不算"第几层需要几点解锁"。最终以游戏内为准。</div>';
    }
    var body = trees.length ? renderTrees(trees, r) : renderPool(pool);
    set(head + banner + '<div class="tpanel">' +
      '<div class="thead"><span class="title">' + D.esc(c.cn || '') + ' 天赋</span>' +
      '<span class="pts">剩余 <b>' + Math.max(0, r.totalPoints - E.spent(tstate.state, trees)) + '</b>/' + r.totalPoints + '</span>' +
      '<input type="search" id="tq" placeholder="搜天赋名" style="max-width:180px">' +
      '<span class="dim mono" id="sel"></span></div>' +
      '<div class="ttabs">' + trees.map(function (t, i) {
        return '<button data-tab="' + i + '" class="' + (i === tstate.active ? 'on' : '') + '">' + D.esc(t.nameCn) + '</button>';
      }).join('') + '</div>' + body +
      '<div class="tfoot"><label class="dim">等级 <span class="mono" id="lvv">60</span></label>' +
      '<input type="range" min="10" max="60" value="60" id="lv">' +
      '<button id="mode" class="ghost">' + (tstate.mode === 'add' ? '当前：加点' : '当前：减点') + '</button>' +
      '<button id="copy" class="ghost">复制方案</button><button id="share" class="ghost">分享链接</button>' +
      '<button id="reset" class="ghost">重置</button>' +
      '<span class="sp">' + D.esc(E.describe(trees, tstate.state)) + '</span></div>' +
      '<div class="src">来源：' + D.esc(f.dataVersion) + ' ｜ ' + D.esc(f.note || '') + '</div></div>' +
      unconfBlock(talentGaps(f, trees), '本页还没确认的'));
    bindTalent();
  }
  function renderPool(pool) {
    if (!pool.length) return '<div class="empty">该职业暂未收录任何已核实天赋名。</div>';
    return '<div style="padding:16px"><h3 style="margin-bottom:8px">已核实的官方中文名 ' + pool.length + ' 条（待归位）</h3>' +
      '<div class="pool">' + pool.map(function (p) {
        return '<span class="term" data-copy="' + D.esc(p.nameCn) + '">' + D.esc(p.nameCn) + ' ' + D.pill(p.level) + '</span>';
      }).join('') + '</div></div>';
  }
  function renderTrees(trees, r) {
    return '<div class="trees">' + trees.map(function (t, ti) {
      var sp = E.treeSpent(t, tstate.state);
      var grid = E.hasTiers(t)
        ? E.tiers(t).map(function (row) {
          var cols = maxCol(t) + 1;
          return '<div class="row" style="grid-template-columns:repeat(' + cols + ',1fr)">' + slots(row, cols).map(function (n) { return cell(n, t, ti, r, trees); }).join('') + '</div>';
        }).join('')
        : '<div class="flow">' + t.nodes.map(function (n) { return cell(n, t, ti, r, trees, true); }).join('') + '</div>';
      return '<div class="tree t' + (ti % 3) + ' ' + (document.body.clientWidth < 861 && ti !== tstate.active ? 'hide' : '') + '" data-tree="' + ti + '">' +
        '<h3><span>' + D.esc(t.nameCn) + ' <span class="dim mono">' + D.esc(t.nameEn || '') + '</span></span>' +
        '<button class="ghost" data-clear="' + ti + '" style="font-size:11px;padding:2px 6px">清空</button></h3>' +
        '<div class="hint">已投 ' + sp + ' 点 · ' + t.nodes.length + ' 个天赋 · ' + nextGate(t, r) + '</div>' + grid + '</div>';
    }).join('') + '</div>';
  }
  function cell(n, t, ti, r, trees, wide) {
    if (!n) return '<div></div>';
    var rk = tstate.state[n.id] || 0, can = E.canAdd(t, tstate.state, n, r, trees);
    var cls = 'node' + (wide ? ' wide' : '') + (rk ? ' on' : '') + (!can.ok && rk === 0 ? ' lock' : '') + (n.nameConflict ? ' conf' : '');
    var tip = [n.nameCn || '未命名', n.nameEn, rk + '/' + (n.maxRanks === null ? '?' : n.maxRanks),
      n.nameAlt ? '另一来源译作「' + n.nameAlt + '」，待定稿' : '',
      n.nameVerified ? '名称与官网中文一致' : '名称待实测',
      can.ok ? (tstate.mode === 'add' ? '点击加 1 点（右键或长按减点）' : '点击减 1 点') : can.why].filter(Boolean).join(' ｜ ');
    var ph = window.Glyph ? Glyph.talentTile(n.id, n.nameCn) : '';
    var img = n.iconKey ? '<img class="ico" src="img/icons/' + encodeURIComponent(n.iconKey) + '.jpg" alt="" loading="lazy" onerror="this.className=\'ico bad\'">' : '';
    var label = (n.nameCn || n.nameEn || '未命名天赋') + '，已点 ' + rk + ' / 上限 ' + (n.maxRanks == null ? '未核实' : n.maxRanks);
    return '<div class="' + cls + '" data-n="' + D.esc(n.id) + '" data-t="' + ti + '" title="' + D.esc(tip) +
      '" role="button" tabindex="0" aria-label="' + D.esc(label) + '" aria-pressed="' + (rk ? 'true' : 'false') + '">' +
      '<span class="ico-wrap">' + ph + img + '</span>' +
      (n.level === 'L2' ? '<i class="flag"></i>' : '') + (n.nameVerified ? '<i class="vok"></i>' : '') +
      (n.nameConflict ? '<i class="cfl"></i>' : '') +
      '<span class="nm">' + D.esc(n.nameCn || n.nameEn || '') + '</span>' +
      '<span class="rank">' + rk + '/' + (n.maxRanks == null ? '?' : n.maxRanks) + '</span></div>';
  }
  function maxCol(t) {
    return t.nodes.reduce(function (m, n) { return n.column > m ? n.column : m; }, 0);
  }
  function slots(row, cols) {
    var out = [], i;
    for (i = 0; i < cols; i++) out.push(null);
    row.forEach(function (n) { if (n.column >= 0 && n.column < cols) out[n.column] = n; });
    return out;
  }
  function nextGate(t, r) {
    if (!r.tierUnlockCost) return '层级门槛未核实';
    var sp = E.treeSpent(t, tstate.state);
    for (var i = 0; i < r.tierUnlockCost.length; i++) if (sp < r.tierUnlockCost[i]) return '再投 ' + (r.tierUnlockCost[i] - sp) + ' 点解锁第 ' + (i + 1) + ' 层';
    return '全部层已解锁';
  }
  function talentGaps(f, trees) {
    var all = [], g = [];
    trees.forEach(function (t) { t.nodes.forEach(function (n) { all.push(n); }); });
    if (!all.length) return ['该职业尚无可用天赋数据'];
    if (!f.rules || !f.rules.tierUnlockCost) g.push('每层需要投入多少点才解锁下一层（层级门槛）——没有可信来源');
    if (all.some(function (n) { return !n.nameEn; })) g.push('英文原名：' + all.filter(function (n) { return !n.nameEn; }).length + ' 个缺失，缺失即留空不猜');
    g.push('天赋效果描述：第三方站的中文文案不复制，需自采或实测');
    var conf = all.filter(function (n) { return n.nameConflict; }).length;
    if (conf) g.push(conf + ' 个天赋两源译名不一致（红框），等官方中文定名');
    var withReq = all.filter(function (n) { return (n.requires || []).length; }).length;
    g.push('前置链不完整：仅 ' + withReq + '/' + all.length + ' 个天赋带前置');
    var unverified = all.filter(function (n) { return !n.nameVerified; }).length;
    if (unverified) g.push(unverified + ' 个天赋名尚未与官网中文对上，标黄点，以游戏内为准');
    return g;
  }
  var lastLongPress = 0;
  function bindLongPress(node) {
    var timer = null;
    function cancel() { if (timer) { clearTimeout(timer); timer = null; } }
    node.ontouchstart = function () {
      timer = setTimeout(function () {
        timer = null;
        // 长按即减点；记时间戳用于吞掉手指抬起后浏览器补发的 click（此时节点已被重渲染替换，元素级标记会失效）
        lastLongPress = Date.now();
        act(node.dataset.t, node.dataset.n, 'sub');
      }, 500);
    };
    node.ontouchmove = cancel;
    node.ontouchcancel = cancel;
    node.ontouchend = cancel;
  }
  function bindTalent() {
    Array.prototype.forEach.call(document.querySelectorAll('.cls[data-c]'), function (b) {
      b.onclick = function () { location.href = 'talent.html?c=' + b.dataset.c; };
    });
    var d = el('demo');
    if (d) d.onclick = function () { D.load('data/talents/_demo.json').then(function (f) {
      tstate.file = f;
      var code = location.hash ? decodeURIComponent(location.hash.slice(1)) : '';
      tstate.state = code ? E.decode(code, f.trees).state : {};
      renderTalent(); }); };
    var b2 = el('back');
    if (b2) b2.onclick = function () { loadTree(tstate.classId); };
    Array.prototype.forEach.call(document.querySelectorAll('.node'), function (n) {
      // 左键跟随当前模式（加点/减点），右键与长按固定减点——移动端没有右键，长按是第二条通道
      n.onclick = function () {
        if (Date.now() - lastLongPress < 700) return;
        act(n.dataset.t, n.dataset.n);
      };
      n.oncontextmenu = function (e) { e.preventDefault(); act(n.dataset.t, n.dataset.n, 'sub'); };
      n.onkeydown = function (e) {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); act(n.dataset.t, n.dataset.n); }
        else if (e.key === 'Backspace' || e.key === 'Delete') { e.preventDefault(); act(n.dataset.t, n.dataset.n, 'sub'); }
      };
      bindLongPress(n);
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-clear]'), function (b) {
      b.onclick = function () { clearTree(+b.dataset.clear); };
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-tab]'), function (b) {
      b.onclick = function () { tstate.active = +b.dataset.tab; renderTalent(); };
    });
    Array.prototype.forEach.call(document.querySelectorAll('.term[data-copy]'), function (t) {
      t.onclick = function () { D.copy(t.dataset.copy); };
    });
    var m = el('mode'); if (m) m.onclick = function () { tstate.mode = tstate.mode === 'add' ? 'sub' : 'add'; renderTalent(); };
    var cp = el('copy'); if (cp) cp.onclick = function () { D.copy(textBuild(), '方案文本'); };
    var sh = el('share'); if (sh) sh.onclick = function () {
      var code = E.encode(tstate.file.trees || [], tstate.state);
      history.replaceState(null, '', '?c=' + tstate.classId + '#' + code);
      D.copy(location.href, '分享链接');
    };
    var rs = el('reset'); if (rs) rs.onclick = function () { tstate.state = {}; persist(); renderTalent(); };
    var lv = el('lv'); if (lv) lv.oninput = function () { el('lvv').textContent = lv.value; };
    var q = el('tq'); if (q) q.oninput = function () {
      var v = q.value.trim().toLowerCase();
      Array.prototype.forEach.call(document.querySelectorAll('.node'), function (n) {
        n.style.outline = v && n.title.toLowerCase().indexOf(v) >= 0 ? '2px solid var(--warn)' : '';
      });
    };
  }
  function act(ti, id, force) {
    var f = tstate.file, t = f.trees[+ti];
    var n = t.nodes.filter(function (x) { return x.id === id; })[0];
    if (!n) return;
    var mode = force || tstate.mode;
    var res = mode === 'add' ? E.add(f.trees, tstate.state, n, f.rules) : E.remove(f.trees, tstate.state, n);
    if (res.msg) D.toast(res.msg);
    if (res.state !== tstate.state) { tstate.state = res.state; persist(); }
    renderTalent();
  }
  function clearTree(ti) {
    var t = tstate.file.trees[ti], s = Object.assign({}, tstate.state);
    t.nodes.forEach(function (n) { delete s[n.id]; });
    tstate.state = s; persist(); renderTalent(); D.toast('已清空 ' + t.nameCn);
  }
  function persist() {
    store(LS + tstate.classId, E.encode(tstate.file.trees || [], tstate.state));
  }
  function textBuild() {
    var f = tstate.file, out = [f.classId || tstate.classId];
    (f.trees || []).forEach(function (t) {
      out.push('## ' + t.nameCn + ' ' + E.treeSpent(t, tstate.state) + ' 点');
      t.nodes.forEach(function (n) {
        var rk = tstate.state[n.id] || 0;
        if (rk) out.push('- ' + (n.nameCn || '（未核实名）') + (n.nameEn ? ' / ' + n.nameEn : '') + ' ' + rk + '/' + n.maxRanks);
      });
    });
    return out.join('\n');
  }

  /* ---------- 选职业问答 ---------- */
  var cstate = { qs: [], meta: {}, classes: [], gloss: [], answers: {}, step: 0 };

  function chooser() {
    Promise.all([D.load('data/chooser.json'), D.load('data/classes.json'), D.load('data/glossary.json')]).then(function (r) {
      cstate.qs = r[0].questions || []; cstate.meta = r[0].meta || {};
      cstate.classes = r[1].classes || []; cstate.gloss = r[2].items || [];
      drawChooser();
    }).catch(fail);
  }
  function chooserScores() {
    var score = {}, reasons = {}, cid;
    cstate.classes.forEach(function (c) { score[c.id] = 0; reasons[c.id] = []; });
    Object.keys(cstate.answers).forEach(function (qid) {
      var q = cstate.qs.filter(function (x) { return x.id === qid; })[0];
      if (!q) return;
      var opt = q.options.filter(function (o) { return o.id === cstate.answers[qid]; })[0];
      if (!opt) return;
      for (cid in (opt.weight || {})) {
        if (!Object.prototype.hasOwnProperty.call(opt.weight, cid)) continue;
        var w = opt.weight[cid];
        if (score[cid] === undefined) score[cid] = 0;
        score[cid] += w;
        if (w >= 2 && opt.note && reasons[cid].indexOf(opt.note) < 0) reasons[cid].push(opt.note);
      }
    });
    return { score: score, reasons: reasons };
  }
  function classCard(c, score, max, reasons) {
    var terms = cstate.gloss.filter(function (g) { return g.classId === c.id; }).length;
    var pct = max ? Math.round(score / max * 100) : 0;
    return '<div class="card mcard"><div class="crow">' +
      '<div class="ic lg">' + (window.Glyph ? Glyph.classTile(c.id, c.cn) : D.esc((c.cn || '?').slice(0, 1))) + '</div>' +
      '<div style="flex:1"><h2 style="margin:0">' + D.esc(c.cn) + ' <span class="dim mono">' + D.esc(c.en || '') + '</span></h2>' +
      '<div class="mbar"><i style="width:' + pct + '%"></i></div>' +
      '<div class="dim">匹配度 ' + pct + '%（' + score + ' 分，本题库最高 ' + max + ' 分）</div></div></div>' +
      (reasons.length ? '<ul class="list">' + reasons.map(function (x) { return '<li>' + D.esc(x) + '</li>'; }).join('') + '</ul>' : '') +
      '<p class="dim">' + (c.talentCount ? '天赋 ' + c.talentCount + ' 个，其中 ' + (c.nameVerified || 0) + ' 个中文名已与官网核对' : '该职业还没有已核实的官方中文天赋名') +
      '；官方中文词条 ' + terms + ' 条。</p>' +
      '<a class="btn" href="talent.html?c=' + c.id + '">看这个职业的天赋树 →</a></div>';
  }
  function drawChooser() {
    var total = cstate.qs.length, done = cstate.step >= total;
    var answered = Object.keys(cstate.answers).length;
    var progress = '<div class="card"><div class="crow"><span class="dim">第 ' + Math.min(cstate.step + 1, total) + ' / ' + total + ' 题</span>' +
      '<span class="sp"></span><button class="ghost" id="creset">重新开始</button></div>' +
      '<div class="cov">' + cstate.qs.map(function (q, i) {
        var w = (100 / total).toFixed(2) + '%';
        var cls = cstate.answers[q.id] ? (i < cstate.step ? 'L0' : 'L1') : 'L3';
        return '<i class="' + cls + '" style="width:' + w + '" title="' + D.esc(q.q) + '"></i>';
      }).join('') + '</div></div>';
    var head = '<div class="card"><h2>选职业问答</h2><p class="dim">' + D.esc(cstate.meta.note || '') + '</p></div>';
    var body;
    if (done) {
      var s = chooserScores(), ids = Object.keys(s.score);
      var max = Math.max.apply(null, ids.map(function (id) { return s.score[id]; }).concat([1]));
      var ranked = ids.sort(function (a, b) { return s.score[b] - s.score[a]; });
      var byId = {};
      cstate.classes.forEach(function (c) { byId[c.id] = c; });
      var top = ranked.slice(0, 3);
      var tied = ranked.filter(function (id) { return s.score[id] === max; });
      body = '<div class="banner gray">下面是按你选的玩法归类的候选，<b>不是强度排行，也不代表哪个职业更强</b>——' +
        '无限服的机制改动还没实测，任何"哪个职业厉害"的说法现在都不可信。' +
        (tied.length > 3 ? '这次并列第一有 ' + tied.length + ' 个职业，都算同样合适。' : '') + '</div>' +
        top.map(function (id) { return classCard(byId[id] || { id: id, cn: id }, s.score[id], max, s.reasons[id] || []); }).join('') +
        '<div class="card"><h2>其余候选</h2><div class="pool">' +
        ranked.filter(function (id) { return top.indexOf(id) < 0; }).map(function (id) {
          return '<span class="term">' + D.esc((byId[id] || {}).cn || id) + ' ' + s.score[id] + ' 分</span>';
        }).join('') + '</div>' +
        '<p class="dim" style="margin-top:8px">分数差距小于 2 分时应视为同样合适。想换个答案再算一次，点上面「重新开始」。</p></div>';
    } else {
      var q = cstate.qs[cstate.step];
      body = '<div class="card"><h2>' + D.esc(q.q) + '</h2>' +
        (q.hint ? '<p class="dim">' + D.esc(q.hint) + '</p>' : '') +
        '<div class="qopts">' + q.options.map(function (o) {
          return '<button class="qopt' + (cstate.answers[q.id] === o.id ? ' on' : '') + '" data-o="' + o.id + '">' + D.esc(o.label) + '</button>';
        }).join('') + '</div>' +
        '<div class="crow" style="margin-top:10px">' +
        (cstate.step ? '<button class="ghost" id="cprev">← 上一题</button><span class="sp"></span>' : '') +
        '<span class="dim">已答 ' + answered + ' 题</span></div></div>';
    }
    set(head + progress + body);
    var rs = el('creset'); if (rs) rs.onclick = function () { cstate.answers = {}; cstate.step = 0; drawChooser(); };
    var pv = el('cprev'); if (pv) pv.onclick = function () { cstate.step = Math.max(0, cstate.step - 1); drawChooser(); };
    Array.prototype.forEach.call(document.querySelectorAll('.qopt'), function (b) {
      b.onclick = function () {
        cstate.answers[cstate.qs[cstate.step].id] = b.dataset.o;
        cstate.step += 1;
        drawChooser();
      };
    });
    if (done) window.scrollTo(0, 0);
  }

  /* ---------- 技能书 ---------- */
  function skills() {
    Promise.all([D.load('data/glossary.json'), D.load('data/classes.json')]).then(function (r) {
      var items = r[0].items, cls = r[1].classes, f = { c: '', k: '', q: '' };
      var KIND = { talent: '天赋/技能', item: '装备', dungeon: '副本', boss: 'BOSS', system: '系统', zone: '地名', skill: '技能' };
      function draw() {
        var list = items.filter(function (x) {
          if (f.c && x.classId !== f.c) return false;
          if (f.k && x.kind !== f.k) return false;
          if (f.q && ((x.cn || '') + (x.en || '')).toLowerCase().indexOf(f.q.toLowerCase()) < 0) return false;
          return true;
        });
        el('tbl').innerHTML = list.length ? '<table><thead><tr><th>中文名</th><th>英文原名</th><th>类型</th><th>职业</th><th>状态</th><th></th></tr></thead><tbody>' +
          list.map(function (x) {
            var c = cls.filter(function (y) { return y.id === x.classId; })[0];
            return '<tr><td>' + D.hl(x.cn, f.q) + '</td><td class="en">' + (x.en ? D.hl(x.en, f.q) : '<span class="dim">待补</span>') + '</td>' +
              '<td>' + (KIND[x.kind] || x.kind) + '</td><td>' + (c ? D.esc(c.cn) : '—') + '</td><td>' + D.pill(x.level) + '</td>' +
              '<td><button class="ghost" data-copy="' + D.esc(x.cn + (x.en ? ' / ' + x.en : '')) + '" style="font-size:11px;padding:1px 6px">复制</button></td></tr>';
          }).join('') + '</tbody></table>' : '<div class="empty">没有匹配条目，试试放宽筛选。</div>';
        el('cnt').textContent = list.length + ' / ' + items.length + ' 条';
        Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function (b) {
          b.onclick = function () { D.copy(b.dataset.copy); };
        });
      }
      set('<div class="card"><h2>技能书</h2><p class="dim">英文原名与专精归属是待补项，缺的地方直接写「待补」，不做机翻。</p>' +
        '<div class="field"><input type="search" id="q" placeholder="搜中文或英文">' +
        '<select id="c"><option value="">全部职业</option>' + cls.map(function (x) { return '<option value="' + x.id + '">' + D.esc(x.cn) + '</option>'; }).join('') + '</select>' +
        '<select id="k"><option value="">全部类型</option>' + Object.keys(KIND).filter(function (k) {
          return items.some(function (x) { return x.kind === k; });
        }).map(function (k) { return '<option value="' + k + '">' + KIND[k] + '</option>'; }).join('') + '</select>' +
        '<span class="dim mono" id="cnt"></span></div></div>' +
        '<div class="card" style="padding:0;overflow:auto;max-height:72vh"><div id="tbl"></div></div>');
      el('q').oninput = function (e) { f.q = e.target.value; draw(); };
      el('c').onchange = function (e) { f.c = e.target.value; draw(); };
      el('k').onchange = function (e) { f.k = e.target.value; draw(); };
      draw();
    }).catch(fail);
  }

  /* ---------- 副本手册 ---------- */
  function dunGaps(x) {
    var g = [];
    if (!x.nameCn) g.push('官方中文名（现在保留英文原名，未机翻）');
    if (x.nameCnConflict) g.push('中文名定稿：官方与转载两种叫法并存');
    if (!x.levelRange) g.push('可进入的等级区间');
    if (!(x.bosses || []).length) g.push('BOSS 名单与数量');
    g.push('掉落物品与掉落来源（本站不写百分比）');
    if (!(x.route || []).length) g.push('跑图路线与跳怪点');
    if (x.kind === 'raid') g.push('开放时间、团队规模、BOSS 数——仅有第三方说法');
    return g;
  }
  function dungeons() {
    D.load('data/dungeons.json').then(function (d) {
      var groups = [['newDungeons', '无限服新副本'], ['classicDungeons', '经典副本（在无限服）'], ['raids', '团队副本']];
      set('<div class="card"><h2>副本手册</h2><p class="dim">名单与等级区间来自官方与线索源；BOSS 技能、掉落、路线在没实测前一律留空并标注。</p></div>' +
        '<div class="banner">掉落数据本站<b>不写百分比</b>：测试服看到的是"谁掉了"，不是"多大概率"。</div>' +
        groups.map(function (g) {
          return '<div class="grp">' + g[1] + ' · ' + (d[g[0]] || []).length + '</div>' +
            (d[g[0]] || []).map(function (x) {
              return '<div class="card dcardx"><div class="dbn-wrap">' +
                (window.Glyph ? Glyph.dungeonBanner(x.id, x.nameCn || x.nameEn || '未定名',
                  (x.levelRange ? x.levelRange + ' 级' : '等级区间待核') + ' · 示意图，非游戏原画') : '') +
                '</div><div class="dcard"><div>' +
                '<div class="nm">' + D.esc(x.nameCn || '中文名未定') + ' <span class="dim mono">' + D.esc(x.nameEn || '') + '</span> ' + D.pill(x.level) + '</div>' +
                '<div class="sub">' + (x.levelRange ? x.levelRange + ' 级 · ' : '等级区间待核 · ') +
                'BOSS ' + ((x.bosses || []).length || '待实测') + ' · 路线 ' + ((x.route || []).length || '待实测') + ' 步</div>' +
                (x.nameCnConflict ? '<div class="conf">译名冲突：官方写「' + D.esc(x.nameCn) + '」，转载写作「' + D.esc(x.nameCnConflict) + '」，待定稿</div>' : '') +
                '</div><button class="ghost" data-d="' + D.esc(x.id) + '">展开来源</button></div>' +
                '<div class="drawer" id="d-' + D.esc(x.id) + '" style="display:none">' +
                '<h3>BOSS 与掉落</h3>' + ((x.bosses || []).length ? JSON.stringify(x.bosses) : '<p class="dim">待实测——没有任何可信来源给出这座本的 BOSS 与掉落，此处不留假数据。</p>') +
                '<h3>路线</h3>' + ((x.route || []).length ? JSON.stringify(x.route) : '<p class="dim">待实测。</p>') +
                '<h3>这座本还没确认的</h3><ul class="list">' + dunGaps(x).map(function (g) { return '<li>' + D.esc(g) + '</li>'; }).join('') + '</ul>' +
                '<h3>来源与核对</h3>' + D.sources(x.provenance) + '</div></div>';
            }).join('');
        }).join(''));
      Array.prototype.forEach.call(document.querySelectorAll('[data-d]'), function (b) {
        b.onclick = function () {
          var x = el('d-' + b.dataset.d);
          x.style.display = x.style.display === 'none' ? 'block' : 'none';
          b.textContent = x.style.display === 'none' ? '展开来源' : '收起';
        };
      });
    }).catch(fail);
  }

  /* ---------- 术语速查 ---------- */
  function glossary() {
    D.load('data/glossary.json').then(function (g) {
      var items = g.items;
      function draw(q) {
        var list = items.filter(function (x) { return !q || ((x.cn || '') + (x.en || '')).toLowerCase().indexOf(q.toLowerCase()) >= 0; });
        el('pool').innerHTML = list.length ? list.map(function (x) {
          return '<span class="term ' + (q ? 'hit' : '') + '" data-c="' + D.esc(x.cn + (x.en ? ' / ' + x.en : '')) + '">' + D.esc(x.cn) + '</span>';
        }).join('') : '<div class="empty">没有匹配词条。缺的词条说明官方还没给中文名，或我们还没采到。</div>';
        el('cnt').textContent = list.length + ' / ' + items.length;
        Array.prototype.forEach.call(document.querySelectorAll('.term[data-c]'), function (t) {
          t.onclick = function () { D.copy(t.dataset.c); };
        });
      }
      set('<div class="card"><h2>中英术语速查</h2><p class="dim">点词条即复制。当前只有猎人与德鲁伊的官方中文名，其余职业待采。</p>' +
        '<div class="field"><input type="search" id="q" placeholder="输入中文或英文"><span class="dim mono" id="cnt"></span></div>' +
        '<div class="pool" id="pool"></div></div>');
      el('q').oninput = function (e) { draw(e.target.value.trim()); };
      draw('');
    }).catch(fail);
  }

  /* ---------- 溯源 ---------- */
  function provenance() {
    Promise.all([D.load('data/classes.json'), D.load('data/glossary.json'), D.load('data/dungeons.json'), D.load('data/meta.json'), D.load('data/method.json')])
      .then(function (r) {
        var cov = D.coverage(r[2], r[1] ? r[0] : r[0], r[1]);
        var m = r[4] || {};
        var names = { L0: '已官方核实', L1: '仅官方英文', L2: '待实测', L3: '缺数据' };
        var refs = [['wow.blizzard.cn/news/', '国服官方公告与职业深度解析', '可入自动化'],
        ['wow.blizzard.cn/24266320/', '国服在线修正', '可入自动化（需整页比对）'],
        ['news.blizzard.com', '官方英文回顾与上线时间', '可入自动化'],
        ['worldofwarcraft.blizzard.com/en-us/forever', '官方英文 forever 页', '可入自动化'],
        ['wowhead.com/forever', '逐本指南、天赋计算器、天梯', '人工参照，禁止搬数据'],
        ['wowclassicforever.info', '最接近数据库的粉丝站', '人工参照，禁止搬数据'],
        ['foreverchanges.pro', '9 新本名单与区间', '线索，禁止整库复制'],
        ['news.17173.com', '中文蓝贴转载', '旁证，需回校官方'],
        ['github.com/cmangos/classic-db', '1.12 国服中文 locale（GPL-3.0）', '只取译名与结构'],
        ['search.bilibili.com', '测试服实测视频', 'ASR + 关键帧识别后人工确认']];
        var ti = r[3].talentImport;
        set('<div class="card"><h2>数据覆盖率</h2>' + D.covBar(cov) +
          '<div class="stats" style="margin-top:12px">' + Object.keys(names).map(function (k) {
            return '<div class="stat"><b>' + cov[k] + '</b>' + names[k] + '</div>';
          }).join('') + '</div>' +
          '<p class="dim">口径：一条数据只有挂着官方来源且人工核过，才算 L0；粉丝站与转载一律最高 L2。</p></div>' +
          (ti ? '<div class="card"><h2>天赋数据来源与风险</h2>' +
            '<div class="grid g2"><div><h3>来源与方法</h3><p class="dim">' + D.esc(ti.method) + '<br>' +
            (ti.sources || []).map(function (s) { return '<span class="mono" style="font-size:11.5px">' + D.esc(s) + '</span>'; }).join('<br>') +
            '<br>' + D.esc(ti.collectedAt) + '</p>' +
            '<div class="stats" style="margin-top:10px">' +
            '<div class="stat"><b>' + ti.nodes + '</b>天赋节点</div>' +
            '<div class="stat"><b>' + ti.nameVerified + '</b>名与官网一致</div>' +
            '<div class="stat"><b>' + ti.nameConflict + '</b>两源译名分歧</div>' +
            '<div class="stat"><b>' + ti.onlyInOneSource + '</b>仅单源出现</div>' +
            '<div class="stat"><b>' + ti.withIcon + '</b>带图标</div>' +
            '<div class="stat"><b>' + ti.resolvedRequires + '</b>带前置</div></div></div>' +
            '<div><h3>刻意没拿的部分</h3><p class="dim">' + D.esc(ti.excluded) + '</p>' +
            '<h3 style="margin-top:8px">还缺什么</h3><p class="dim">' + D.esc(ti.stillMissing) + '</p>' +
            '<h3 style="margin-top:8px">风险</h3><p class="caution">' + D.esc(ti.risk) + '</p></div></div></div>' : '') +
          (m.steps ? '<div class="card"><h2>我们怎么拿到这些数据</h2><p class="dim">' + D.esc(m.meta ? m.meta.note : '') + '</p>' +
            '<div class="grid g2">' + m.steps.map(function (x) {
              return '<div class="step"><h3>' + D.esc(x.title) + '</h3><p class="dim">' + D.esc(x.body) + '</p></div>';
            }).join('') + '</div>' +
            (m.neverTake ? '<h3 style="margin-top:var(--s4)">刻意不拿的东西</h3><ul class="list">' +
              m.neverTake.map(function (x) { return '<li>' + D.esc(x) + '</li>'; }).join('') + '</ul>' : '') +
            (m.onError ? '<h3 style="margin-top:var(--s4)">被指出错了怎么办</h3><p class="dim">' + D.esc(m.onError) + '</p>' : '') +
            (m.recheck ? '<h3 style="margin-top:var(--s4)">什么时候重核</h3><p class="dim">' + D.esc(m.recheck) + '</p>' : '') +
            '<p class="src">方法说明核对日期：' + D.esc((m.meta || {}).generatedAt || '—') + '</p></div>' : '') +
          '<div class="card"><h2>还没被证实的</h2><ol class="q">' +
          (r[3].openQuestions || []).map(function (q) { return '<li>' + D.esc(q) + '</li>'; }).join('') + '</ol></div>' +
          '<div class="card"><h2>来源站点与用法边界</h2><table><thead><tr><th>站点</th><th>能给什么</th><th>怎么用</th></tr></thead><tbody>' +
          refs.map(function (x) { return '<tr><td class="mono">' + x[0] + '</td><td>' + x[1] + '</td><td>' + x[2] + '</td></tr>'; }).join('') +
          '</tbody></table></div>' +
          '<div class="card"><h2>规则（构建时卡口）</h2><ul>' +
          (r[3].rules || []).map(function (x) { return '<li>' + D.esc(x) + '</li>'; }).join('') + '</ul></div>');
      }).catch(fail);
  }

  /* ---------- 系统与新区域 ---------- */
  function unconfBlock(items, title) {
    if (!items || !items.length) return '';
    return '<div class="card"><h2>' + (title || '还没确认的') + '</h2><ol class="q">' +
      items.map(function (t) { return '<li>' + D.esc(t) + '</li>'; }).join('') + '</ol>' +
      '<p class="dim" style="margin-top:6px">这些条目缺官方来源或未实测，宁可空着也不编。</p></div>';
  }
  function systems() {
    D.load('data/systems.json').then(function (s) {
      var q = document.body.getAttribute('data-page');
      set(s.groups.map(function (g) {
        return '<div class="grp">' + D.esc(g.label) + ' · ' + g.items.length + '</div>' +
          g.items.map(function (x) {
            return '<div class="card"><div class="hd" style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap">' +
              '<span style="font-size:15px;font-weight:600">' + D.esc(x.nameCn || '中文名未定') + '</span>' +
              '<span class="dim mono">' + D.esc(x.nameEn || '') + '</span>' + D.pill(x.level) + '</div>' +
              (x.note ? '<div class="dim" style="font-size:12.5px;margin:4px 0">' + D.esc(x.note) + '</div>' : '') +
              D.sources(x.provenance) + '</div>';
          }).join('');
      }).join('') + unconfBlock(s.unconfirmed, '还没确认的设定'));
    }).catch(fail);
  }

  function fail(e) {
    set('<div class="card"><h2>数据没加载出来</h2><p class="dim">' + D.esc(e && e.message ? e.message : e) + '</p>' +
      '<p class="dim">这个站要读本地 JSON，不能用 file:// 直接打开。在项目里执行：<br>' +
      '<code>cd src &amp;&amp; python3 -m http.server 8812</code>，再访问 <code>http://127.0.0.1:8812</code></p>' +
      '<button id="rt">重试</button></div>');
    var b = el('rt'); if (b) b.onclick = function () { location.reload(); };
  }

  shell();
  ({ home: home, talent: talent, chooser: chooser, skills: skills, dungeons: dungeons, systems: systems, glossary: glossary, provenance: provenance })[page]();
})();
