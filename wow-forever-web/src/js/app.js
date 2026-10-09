/* 页面渲染与交互 */
(function () {
  var D = window.WowData, E = window.TalentEngine;
  // 分组导航：与参考站同构（天赋/职业/种族/世界/工具/溯源），但只挂我们自己有数据的页。
  // 参考站的「攻略」「新动态」不挂：本站红线不做攻略正文与新闻流。
  var NAV = [
    { t: '首页', href: 'index.html', d: '数据覆盖率与入口' },
    { t: '天赋', items: [
      { href: 'talent.html', t: '天赋计算器', d: '9 职业 · 树结构与加点' }] },
    { t: '职业', items: [
      { href: 'chooser.html', t: '选职业问答', d: '7 题玩法问答（非强度排行）' },
      { href: 'skills.html', t: '技能书', d: '中英对照 + 与经典旧世的四态差异' }] },
    { t: '种族', items: [
      { href: 'races.html', t: '种族与职业组合', d: '10 个种族行 · 可选职业矩阵' },
      { href: 'races.html#traits', t: '种族特长', d: '40 条官方中文原名与整句' }] },
    { t: '世界', items: [
      { href: 'dungeons.html', t: '副本手册', d: '9 新本 + 10 经典本 + 3 团本' },
      { href: 'systems.html', t: '系统与新区域', d: '规则、区域、装备名的官方中文口径' }] },
    { t: '工具', items: [
      { href: 'glossary.html', t: '术语速查', d: '官方中文词条，点一下即复制' },
      { href: 'timeline.html', t: '上线时间表', d: '11 个时间点带官方原文' },
      { href: 'provenance.html', t: '溯源与覆盖率', d: '哪些已核实、哪些只是线索' }] }
  ];
  // 结构上有位置、数据还没采到的：写清楚为什么空着，不做假页面
  var NAV_TODO = [
    { t: '世界地图', d: '跑图坐标中文侧完全没有', href: 'dungeons.html#todo' },
    { t: 'PvP', d: '官方中文未公布无限服 PvP 规则', href: 'dungeons.html#todo' },
    { t: '坐骑 / 套装 / 隐藏内容', d: '只有第三方线索，禁止搬数据', href: 'dungeons.html#todo' }
  ];
  var LS = 'wfs.build.';
  var page = document.body.getAttribute('data-page');

  function el(id) { return document.getElementById(id); }
  function set(html) { el('main').innerHTML = html; }
  function store(key, val) {
    try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); return null; }
    catch (e) { D.toast('本机存储不可用，方案仅本次有效'); return null; }
  }
  function bindSrcToggles(scope) {
    Array.prototype.forEach.call((scope || document).querySelectorAll('[data-src]'), function (b) {
      b.onclick = function (e) {
        e.stopPropagation();
        var row = el('s-' + b.dataset.src);
        if (!row) {
          var box = el('srcbox');
          if (!box) return;
          var same = box.dataset.for === b.dataset.src && box.style.display !== 'none';
          box.style.display = same ? 'none' : 'block';
          if (!same) {
            box.dataset.for = b.dataset.src;
            box.innerHTML = '<h3>' + D.esc(b.dataset.name || '') + ' · 来源与核对</h3>' +
              D.sources(JSON.parse(decodeURIComponent(b.dataset.prov || '[]')));
          }
          b.textContent = same ? '来源' : '收起';
          return;
        }
        var open = row.style.display !== 'none';
        Array.prototype.forEach.call(document.querySelectorAll('.srow'), function (r) { r.style.display = 'none'; });
        row.style.display = open ? 'none' : 'table-row';
        b.textContent = open ? '来源' : '收起';
        Array.prototype.forEach.call(document.querySelectorAll('[data-src]'), function (o) {
          if (o !== b && !el('s-' + o.dataset.src)) return;
          if (o !== b) o.textContent = '来源';
        });
      };
    });
  }
  function navKey(href) {
    var f = href.replace('.html', '').split('#')[0];
    return f === 'index' ? 'home' : f;
  }
  function bindNav() {
    var groups = Array.prototype.slice.call(document.querySelectorAll('.nd'));
    function closeAll(except) {
      groups.forEach(function (g) {
        if (g === except) return;
        g.classList.remove('open');
        var b = g.querySelector('.ndb'); if (b) b.setAttribute('aria-expanded', 'false');
      });
    }
    groups.forEach(function (g) {
      var b = g.querySelector('.ndb');
      b.onclick = function (e) {
        e.stopPropagation();
        var open = g.classList.toggle('open');
        b.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) closeAll(g);
      };
    });
    document.addEventListener('click', function () { closeAll(null); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' || e.key === 'Esc') closeAll(null);
    });
  }
  /* 图标格：有本地转存的官方图标就显示图，没有就显示自绘占位块。
     占位块垫在图后面，图加载失败（onerror 换类名）时自动露出来，不留空白。 */
  function iconCell(ic, seed, cn, small) {
    var ph = window.Glyph ? Glyph.talentTile(seed || cn, cn) : '';
    var img = ic ? '<img class="lico" src="img/icons/' + encodeURIComponent(ic) + '.jpg" alt="" loading="lazy" ' +
      'onerror="this.className=\'lico bad\'">' : '';
    return '<span class="liw' + (small ? ' sm' : '') + '">' + ph + img + '</span>';
  }
  /* 图标查表的键：职业词条用 classId，种族特长用 raceId（同名特长在不同种族是两回事） */
  function iconKeyOf(x) {
    return (x.kind === 'racial' ? (x.raceId || '') : (x.classId || '')) + '|' + x.cn;
  }
  /* 词条归属：职业词条按职业分组，种族特长按种族分组，剩下的进「装备与其他」。
     技能书页与术语速查页共用这一份，避免两处分组口径不一致。 */
  function raceLookup(races) {
    var m = { order: [] };
    (races || []).forEach(function (x) {
      m[x.id] = { cn: x.subgroup ? x.subgroup.nameCn : x.nameCn, fac: x.faction, iconKey: x.iconKey };
      m.order.push(x.id);
      // 天裔在两张表里各一行，词条归属可能落在子族上；展示时统一并进「天裔」一组
      if (x.nameCn === '天裔' && !m.skyborne) {
        m.skyborne = { cn: '天裔', fac: '', iconKey: x.iconKey };
        m.order.push('skyborne');
      }
    });
    return m;
  }
  function raceBucket(rid) { return rid.indexOf('skyborne') === 0 ? 'skyborne' : rid; }
  function groupEntries(list, classes, RACE) {
    var byCls = {}, byRace = {}, rest = [];
    list.forEach(function (x) {
      if (x.kind === 'racial') {
        var rid = raceBucket(x.raceId || '_');
        (byRace[rid] = byRace[rid] || []).push(x);
        return;
      }
      if (x.classId) { (byCls[x.classId] = byCls[x.classId] || []).push(x); return; }
      rest.push(x);
    });
    var out = [];
    classes.forEach(function (c) {
      if (byCls[c.id]) out.push({ tile: Glyph.classTile(c.id, c.cn, c.iconKey), name: c.cn, sub: c.en, rows: byCls[c.id] });
    });
    // 种族组按官方页的阵营顺序排（部落五个 → 联盟五个），不按拼音也不按 id
    Object.keys(byRace).sort(function (a, b) {
      var ia = RACE.order.indexOf(a), ib = RACE.order.indexOf(b);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    }).forEach(function (rid) {
      var rc = RACE[rid] || { cn: '未归属种族', fac: '' };
      out.push({ tile: Glyph.raceTile(rid, rc.fac, rc.cn, rc.iconKey), name: rc.cn, sub: '种族特长', rows: byRace[rid] });
    });
    if (rest.length) out.push({ tile: '', name: '装备与其他', sub: '', rows: rest });
    return out;
  }
  function shell() {
    var now = new Date('2026-11-05T00:00:00+08:00').getTime() - Date.now();
    var d = Math.max(0, Math.floor(now / 86400000)), h = Math.max(0, Math.floor(now / 3600000) % 24);
    el('top').innerHTML = '<div class="in"><div class="brand">无限<span>资料站</span></div><nav class="main" aria-label="主导航">' +
      NAV.map(function (g) {
        if (g.href) {
          return '<a href="' + g.href + '" class="' + (page === navKey(g.href) ? 'on' : '') + '">' + g.t + '</a>';
        }
        var hit = g.items.some(function (it) { return page === navKey(it.href); });
        return '<div class="nd"><button type="button" class="ndb' + (hit ? ' on' : '') +
          '" aria-haspopup="true" aria-expanded="false">' + g.t + '<span class="cr" aria-hidden="true">▾</span></button>' +
          '<div class="ndp" role="menu">' + g.items.map(function (it) {
            return '<a role="menuitem" href="' + it.href + '"' + (page === navKey(it.href) ? ' class="on"' : '') +
              '><b>' + it.t + '</b><span>' + it.d + '</span></a>';
          }).join('') + '</div></div>';
      }).join('') + '</nav><div class="chip">距上线 ' + d + ' 天 ' + h + ' 时</div></div>';
    bindNav();
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
        set('<div class="card"><h1 class="pt">《魔兽世界：无限》中文资料</h1>' +
          '<p class="dim">天赋、种族与职业组合、技能中英对照、副本与掉落。每条数据都标了来源与核对状态——' +
          '没核实的地方直接写「待实测」，不编造。</p>' + D.covBar(cov) +
          '<div class="stats" style="margin-top:12px">' +
          '<div class="stat"><b>' + gl.length + '</b>官方中文词条</div>' +
          '<div class="stat"><b>' + dn + '</b>新副本</div>' +
          '<div class="stat"><b>' + classes.length + '</b>职业</div>' +
          '<div class="stat"><b>11-05</b>上线</div></div></div>' +
          '<div class="banner">本站基于测试服资料整理，正式服 2026-11-05 上线后需整体重核。</div>' +
          '<div class="card"><h2>选职业</h2>' +
          '<p class="dim" style="margin-bottom:var(--s3)">第一次接触无限服、不知道选哪个？' +
          '<a class="cta" href="chooser.html">做个 7 题玩法问答 →</a>（本站整理，不是强度排行）</p>' +
          '<div class="grid g9">' +
          classes.map(function (c) {
            var n = gl.filter(function (g) { return g.classId === c.id; }).length;
            var lv = c.talentCount ? (c.nameVerified ? 'L2' : 'L2') : 'L3';
            return '<a class="cls" style="text-decoration:none" href="talent.html?c=' + c.id + '">' +
              '<div class="ic">' + (window.Glyph ? Glyph.classTile(c.id, c.cn, c.iconKey) : D.esc((c.cn || '?').slice(0, 1))) + '</div><div class="n">' + D.esc(c.cn) + '</div>' +
              '<div class="e">' + D.esc(c.en) + '</div>' +
              '<div style="margin-top:5px">' + D.pill(lv) + '</div>' +
              '<div class="e">' + (c.talentCount || 0) + ' 天赋' +
              (c.nameVerified ? ' · ' + c.nameVerified + ' 名与官网一致' : ' · 待实测') + '</div>' +
              (n ? '<div class="e">官方词条 ' + n + ' 条</div>' : '') + '</a>';
          }).join('') + '</div></div>' +
          '<div class="grid g3">' +
          '<div class="card"><h2>副本手册</h2><p class="dim">' + dn + ' 座新副本名单与等级区间，BOSS 与掉落按实测进度补。</p><a href="dungeons.html">进入 →</a></div>' +
          '<div class="card"><h2>中英术语速查</h2><p class="dim">' + gl.length + ' 条官方中文技能与天赋名，点一下即复制。</p><a href="glossary.html">进入 →</a></div>' +
          '<div class="card"><h2>种族与职业组合</h2><p class="dim">10 个种族行 × 9 职业的官方中文矩阵，40 条种族特长带整句。</p><a href="races.html">进入 →</a></div>' +
          '<div class="card"><h2>上线时间表</h2><p class="dim">Beta 与正式服的 11 个时间点，中英文两个上线口径都留着。</p><a href="timeline.html">进入 →</a></div>' +
          '<div class="card"><h2>溯源与覆盖率</h2><p class="dim">哪些已核实、哪些只是线索、哪些根本没有来源，全部摊开。</p><a href="provenance.html">进入 →</a></div></div>');
      }).catch(fail);
  }

  /* ---------- 天赋计算器 ---------- */
  var tstate = { classId: 'hunter', file: null, state: {}, mode: 'add', active: 0 };

  function talent() {
    var q = new URLSearchParams(location.search);
    tstate.classId = q.get('c') || 'hunter';
    Promise.all([D.load('data/classes.json'), D.load('data/glossary.json'),
      D.load('data/art.json').catch(function () { return {}; })]).then(function (r) {
      tstate.classes = r[0].classes; tstate.gloss = r[1].items; tstate.art = r[2] || {};
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
  /* 前置连线：格子是 CSS 网格，位置只能渲染完量出来再画，所以事后注入一层 SVG */
  function drawLinks() {
    var file = tstate.file;
    if (!file || !file.trees) return;
    Array.prototype.forEach.call(document.querySelectorAll('.tree[data-tree]'), function (col) {
      var old = col.querySelector('.tlines');
      if (old) old.parentNode.removeChild(old);
      var tree = file.trees[+col.getAttribute('data-tree')];
      if (!tree) return;
      var pos = {};
      Array.prototype.forEach.call(col.querySelectorAll('.node[data-n]'), function (n) { pos[n.getAttribute('data-n')] = n; });
      var box = col.getBoundingClientRect(), svg = '';
      (tree.nodes || []).forEach(function (n) {
        var to = pos[n.id];
        if (!to) return;
        (n.requires || []).forEach(function (rid) {
          var from = pos[rid];
          if (!from) return;
          var a1 = from.getBoundingClientRect(), b1 = to.getBoundingClientRect();
          svg += '<line x1="' + (a1.left - box.left + a1.width / 2).toFixed(1) + '" y1="' + (a1.top - box.top + a1.height / 2).toFixed(1) +
            '" x2="' + (b1.left - box.left + b1.width / 2).toFixed(1) + '" y2="' + (b1.top - box.top + b1.height / 2).toFixed(1) + '"></line>';
        });
      });
      if (!svg) return;
      var wrap = document.createElement('div');
      wrap.innerHTML = '<svg class="tlines" aria-hidden="true">' + svg + '</svg>';
      col.appendChild(wrap.firstChild);
    });
  }
  var CMP_TIP = '对照文本来自客户端解包（第三方资料站转述）';
  function compareHtml(t) {
    var nodes = (t && t.nodes) || {};
    var ids = Object.keys(nodes).filter(function (id) { return nodes[id].changeNote || (nodes[id].ranks || []).length; });
    if (!ids.length) return '<p class="dim">上游没有给出这些条目的对照文本。</p>';
    return '<h3>与经典旧世逐条对照 · ' + ids.length + ' 条</h3><p class="note">' + CMP_TIP +
      '，只列上游写了差异的条目；措辞照录，本站不改写。</p>' +
      ids.map(function (id) {
        var e = nodes[id];
        return '<div class="cmprow"><b>' + D.esc(e.name || '') + '</b>' +
          (e.tag ? '<span class="tag">' + D.esc(e.tag) + '</span>' : '') +
          (e.condition ? '<span class="dim mono">' + D.esc(e.condition) + '</span>' : '') +
          (e.changeNote ? '<div>' + D.esc(e.changeNote.replace(/^改动摘要：/, '')) + '</div>' : '') +
          ((e.ranks || []).length ? '<div class="cmp-ranks">' + e.ranks.map(function (r) {
            return '<span class="dim mono">' + D.esc(r.label) + '</span> ' + D.esc(r.text);
          }).join('<br>') + '</div>' : '') + '</div>';
      }).join('');
  }
  function toggleCompare() {
    var box = el('cmpbox'), btn = el('cmp');
    if (!box) return;
    var open = box.style.display !== 'none';
    box.style.display = open ? 'none' : 'block';
    if (btn) btn.setAttribute('aria-pressed', open ? 'false' : 'true');
    if (open || box.dataset.loaded) return;
    box.innerHTML = '<p class="dim">对照在载入…</p>';
    D.load('data/talent-text/' + tstate.classId + '.json').then(function (t) {
      box.dataset.loaded = '1';
      box.innerHTML = compareHtml(t);
    }).catch(function () { box.innerHTML = '<p class="dim">这个职业还没有对照文本。</p>'; });
  }
  function renderTalent() {
    var f = tstate.file, c = tstate.classes.filter(function (x) { return x.id === tstate.classId; })[0] || {};
    var pool = (f.namePool || []), trees = f.trees || [], r = E.defaults(f.rules);
    var head = '<div class="card" style="padding-bottom:0"><div class="classbar">' + tstate.classes.map(function (x) {
      return '<button class="cls ' + (x.id === tstate.classId ? 'on' : '') + '" data-c="' + x.id + '" style="min-width:78px">' +
        '<div class="ic">' + (window.Glyph ? Glyph.classTile(x.id, x.cn, x.iconKey) : D.esc((x.cn || '?').slice(0, 1))) + '</div><div class="n">' + D.esc(x.cn) + '</div></button>';
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
      var vcnt = 0, tcnt = 0, ccnt = 0, chg = { added: 0, modified: 0, moved: 0, unchanged: 0 };
      trees.forEach(function (t) {
        t.nodes.forEach(function (n) {
          tcnt++; if (n.nameVerified) vcnt++; if (n.nameConflict) ccnt++;
          if (chg[n.changeState] !== undefined) chg[n.changeState]++;
        });
      });
      var gate = (f.tierUnlockCost || []).filter(function (v) { return v; }).join(' / ');
      banner = '<div class="banner">天赋的名称、系属、点数上限、格子位置与前置连线，取自无限客户端解包' +
        '（两个挖掘源按坐标对齐，结构再经天赋模拟器逐格核对），每条都能点开看来源。' +
        '本职业 ' + tcnt + ' 个天赋：与经典旧世相比<b class="ok">' + chg.added + ' 个新增</b>、' +
        '<b class="caution">' + chg.modified + ' 个改动</b>、' + chg.moved + ' 个换层、' + chg.unchanged + ' 个未变；' +
        vcnt + ' 个名称与官网中文一致' +
        (ccnt ? '，<b class="alert">' + ccnt + ' 个两源译名不一致（红框，两个叫法都保留）</b>' : '') +
        (gate ? '。层级点数门槛：第 2 层起需在本系累计 ' + gate + ' 点' : '') +
        '。最终以游戏内为准。</div>';
    }
    var cband = (tstate.art && tstate.art.classes) ? tstate.art.classes[tstate.classId] : null;
    var body = trees.length ? renderTrees(trees, r) : renderPool(pool);
    set(head + banner + '<div class="tpanel">' +
      (cband ? '<div class="tbg"><img src="' + D.esc(cband) + '" alt="" loading="lazy" ' +
        'onerror="this.className=\'bad\'"><span class="dbn2-mark">客户端原画 · 本地转存</span></div>' : '') +
      '<div class="thead"><h1 class="title">' + D.esc(c.cn || '') + ' 天赋</h1>' +
      '<span class="pts">剩余 <b>' + Math.max(0, r.totalPoints - E.spent(tstate.state, trees)) + '</b>/' + r.totalPoints + '</span>' +
      '<input type="search" id="tq" placeholder="搜天赋名" style="max-width:180px">' +
      '<button class="ghost" id="cmp" aria-pressed="false">与经典旧世对比</button>' +
      '<span class="dim mono" id="sel"></span></div>' +
      '<div class="tlegend"><span><i class="lg added"></i>新增</span><span><i class="lg modified"></i>改动</span>' +
      '<span><i class="lg moved"></i>换层</span><span><i class="lg unchanged"></i>未变</span>' +
      '<span class="dim">标记按客户端解包与经典旧世对照给出；没标 = 上游没这条</span></div>' +
      '<div class="ttabs">' + trees.map(function (t, i) {
        return '<button data-tab="' + i + '" class="' + (i === tstate.active ? 'on' : '') + '">' + D.esc(t.nameCn) + '</button>';
      }).join('') + '</div>' + body +
      '<div class="cmpbox" id="cmpbox" style="display:none"></div>' +
      '<div class="tfoot"><label class="dim">等级 <span class="mono" id="lvv">60</span></label>' +
      '<input type="range" min="10" max="60" value="60" id="lv" aria-label="按角色等级筛选可用天赋">' +
      '<button id="mode" class="ghost">' + (tstate.mode === 'add' ? '当前：加点' : '当前：减点') + '</button>' +
      '<button id="copy" class="ghost">复制方案</button><button id="share" class="ghost">分享链接</button>' +
      '<button id="reset" class="ghost">重置</button>' +
      '<span class="sp">' + D.esc(E.describe(trees, tstate.state)) + '</span></div>' +
      '<div class="src">来源：' + D.esc(f.dataVersion) + ' ｜ ' + D.esc(f.note || '') +
      '<button class="ghost" id="tsrcbtn">本页节点来源</button></div>' +
      '<div class="srcbox" id="tsrc" style="display:none"></div></div>' +
      unconfBlock(talentGaps(f, trees), '本页还没确认的'));
    bindTalent();
    drawLinks();
    var cbtn = el('cmp');
    if (cbtn) cbtn.onclick = toggleCompare;
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
    var cls = 'node' + (wide ? ' wide' : '') + (rk ? ' on' : '') + (!can.ok && rk === 0 ? ' lock' : '') + (n.nameConflict ? ' conf' : '') + (n.changeState ? ' chg-' + n.changeState : '');
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
    var tb = el('tsrcbtn');
    if (tb) tb.onclick = function () {
      var box = el('tsrc');
      if (!box) return;
      var open = box.style.display !== 'none';
      box.style.display = open ? 'none' : 'block';
      tb.textContent = open ? '本页节点来源' : '收起';
      if (!open && !box.dataset.built) {
        var bySrc = {}, order = [];
        (tstate.file.trees || []).forEach(function (tr) {
          (tr.nodes || []).forEach(function (n) {
            (n.provenance || []).forEach(function (pr) {
              var key = (pr.type || '?') + '|' + (pr.url || '') + '|' + (pr.checkedAt || '');
              if (!bySrc[key]) { bySrc[key] = { pr: pr, n: 0 }; order.push(key); }
              bySrc[key].n += 1;
            });
          });
        });
        box.innerHTML = '<h3>本页 ' + order.length + ' 类来源，覆盖 ' + (tstate.file.trees || []).reduce(function (a, t) {
          return a + t.nodes.length;
        }, 0) + ' 个节点</h3>' + order.map(function (k) {
          var x = bySrc[k];
          return '<div class="srcline"><span class="st ' + D.esc(x.pr.type) + '">' + D.esc(x.pr.type) + '</span>' +
            '<b>' + x.n + '</b> 个节点 ｜ ' + D.esc(x.pr.note || '') +
            '<br><a href="' + D.esc(x.pr.url) + '" target="_blank" rel="noopener">' + D.esc(x.pr.url) + '</a>' +
            ' ｜ 核对：' + D.esc(x.pr.checkedAt || '未记录') + '</div>';
        }).join('');
        box.dataset.built = '1';
      }
    };
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
      '<div class="ic lg">' + (window.Glyph ? Glyph.classTile(c.id, c.cn, c.iconKey, 'lg') : D.esc((c.cn || '?').slice(0, 1))) + '</div>' +
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
    var head = '<div class="card"><h1 class="pt">选职业问答</h1><p class="dim">' + D.esc(cstate.meta.note || '') + '</p></div>';
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

  /* ---------- 上线时间表 ---------- */
  function timeline() {
    D.load('data/timeline.json').then(function (d) {
      var m = d.meta || {}, items = d.items || [], now = Date.now();
      var tz = m.timezoneConflict;
      var done = 0, upcoming = 0;
      items.forEach(function (x) {
        var t = /^\d{4}-\d{2}-\d{2}$/.test(x.date) ? new Date(x.date + 'T00:00:00+08:00').getTime() : null;
        if (t !== null && t <= now) done += 1; else if (t !== null) upcoming += 1;
      });
      var rows = items.map(function (x) {
        var t = /^\d{4}-\d{2}-\d{2}$/.test(x.date) ? new Date(x.date + 'T00:00:00+08:00').getTime() : null;
        var state = t === null ? '未定' : (t <= now ? '已过' : '待来');
        var days = t === null ? '' : (t <= now ? '已过 ' + Math.round((now - t) / 86400000) + ' 天' : '还有 ' + Math.ceil((t - now) / 86400000) + ' 天');
        return '<div class="tlrow tl-' + state + '"><div class="tl-date"><b class="mono">' + D.esc(x.date) + '</b>' +
          '<span class="dim">' + D.esc(days) + '</span></div><div class="tl-body">' +
          '<div class="tl-h">' + D.esc(x.title) + ' ' + D.pill(x.level) + ' <span class="tag">' + state + '</span></div>' +
          '<p class="dim">' + D.esc(x.what) + '</p>' + D.sources(x.provenance, { quote: true }) + '</div></div>';
      }).join('');
      set('<div class="card"><h1 class="pt">上线与 Beta 时间表</h1><p class="dim">' + D.esc(m.note || '') + '</p>' +
        '<div class="stats"><div class="stat"><b>' + items.length + '</b>个时间点</div>' +
        '<div class="stat"><b>' + done + '</b>已过</div><div class="stat"><b>' + upcoming + '</b>待来</div>' +
        '<div class="stat"><b>' + (items.length - done - upcoming) + '</b>日期未定</div></div></div>' +
        (tz ? '<div class="card"><h2>上线日期为什么有两个说法</h2>' +
          '<p class="dim">' + D.esc(tz.cn) + '<br>' + D.esc(tz.en) + '</p>' +
          '<p>' + D.esc(tz.ours) + '<span class="tag">本站推算 ' + D.esc(tz.level) + '</span></p>' +
          '<p class="dim">' + D.esc(tz.why) + '</p></div>' : '') +
        '<div class="tl">' + rows + '</div>' +
        unconfBlock(['Beta 等级上限提高到 30 级的具体日期', '专家模式（硬核）开放时间', '12 月 9 日之后各批内容的具体清单与国服对应日期',
          '三座团队副本与官方所说"new raids"是否同一批'], '还没确认的'));
    }).catch(fail);
  }

  /* ---------- 技能书 ---------- */
  var AB_STATE = { new: '新增', changed: '改动', renamed: '改名', removed: '移除' };
  var AB_KIND = { talent: '天赋', skill: '技能', pet: '宠物技能' };
  var AB_SPEC = { 'beast-mastery': '野兽控制', marksmanship: '射击', survival: '生存', feral: '野性战斗',
    restoration: '恢复', balance: '平衡', discipline: '戒律', holy: '神圣', shadow: '暗影',
    arms: '武器', fury: '狂怒', protection: '防护' };
  function skills() {
    Promise.all([D.load('data/glossary.json'), D.load('data/classes.json'), D.load('data/abilities.json'),
      D.load('data/icons.json'), D.load('data/races.json')]).then(function (r) {
      var items = r[0].items, cls = r[1].classes, ab = r[2] || { items: [], meta: {} };
      var ICONS = (r[3] || {}).map || {}, RC = (r[4] || {}).races || [];
      var f = { c: '', k: '', q: '' };
      var KIND = { talent: '天赋/技能', item: '装备', dungeon: '副本', boss: 'BOSS', system: '系统', zone: '地名', skill: '技能', racial: '种族特长' };
      var RACE = raceLookup(RC);
      function draw() {
        var list = items.filter(function (x) {
          if (f.c && x.classId !== f.c) return false;
          if (f.k && x.kind !== f.k) return false;
          if (f.q && ((x.cn || '') + (x.en || '')).toLowerCase().indexOf(f.q.toLowerCase()) < 0) return false;
          return true;
        });
        var groups = groupEntries(list, cls, RACE);
        var withIcon = list.filter(function (x) { return ICONS[iconKeyOf(x)]; }).length;
        el('tbl').innerHTML = groups.length ? groups.map(function (g) {
          return '<div class="lgrp">' + g.tile + '<b>' + D.esc(g.name) + '</b>' +
            (g.sub ? '<span class="dim mono">' + D.esc(g.sub) + '</span>' : '') +
            '<span class="dim">' + g.rows.length + ' 条</span></div>' +
            '<div class="scrollx"><table class="entab"><thead><tr><th class="ich">图标</th><th>中文名</th><th>英文原名</th><th>类型</th><th>状态</th><th></th></tr></thead><tbody>' +
            g.rows.map(function (x) {
              return '<tr><td class="ich">' + iconCell(ICONS[iconKeyOf(x)], x.id, x.cn) + '</td>' +
                '<td>' + D.hl(x.cn, f.q) + '</td>' +
                '<td class="en">' + (x.en ? D.hl(x.en, f.q) : '<span class="dim">待补</span>') + '</td>' +
                '<td>' + (KIND[x.kind] || x.kind) + '</td><td>' + D.pill(x.level) + '</td>' +
                '<td class="act"><button class="ghost" data-copy="' + D.esc(x.cn + (x.en ? ' / ' + x.en : '')) + '">复制</button>' +
                '<button class="ghost" data-src="' + D.esc(x.id) + '">来源</button></td></tr>' +
                '<tr class="srow" id="s-' + D.esc(x.id) + '" style="display:none"><td colspan="6">' + D.sources(x.provenance) + '</td></tr>';
            }).join('') + '</tbody></table></div>';
        }).join('') : '<div class="empty">没有匹配条目，试试放宽筛选。</div>';
        el('cnt').textContent = list.length + ' / ' + items.length + ' 条 · 带官方图标 ' + withIcon + ' 条';
        bindSrcToggles(el('tbl'));
        drawAbilities();
      }
      function drawAbilities() {
        var all = ab.items || [];
        var list = all.filter(function (x) { return !f.c || x.classId === f.c; });
        var byState = { new: [], changed: [], renamed: [], removed: [] };
        list.forEach(function (x) { (byState[x.state] || (byState[x.state] = [])).push(x); });
        var cnName = {};
        cls.forEach(function (c) { cnName[c.id] = c.cn; });
        var head = '<p class="dim">只列官方中文稿里带状态标记的原句，整句照录；' +
          '官方没写过"没变"的东西，所以' + '<b>未变＝未统计</b>，不拿沉默当证据。</p>';
        if (!list.length) {
          el('abtbl').innerHTML = head + '<div class="empty">这个职业还没有官方中文深度解析稿，四态无从谈起。' +
            '缺的五个职业：' + D.esc(((ab.meta || {}).notCollected || [])[1] || '圣骑士/萨满祭司/法师/术士/潜行者') + '</div>';
          return;
        }
        el('abtbl').innerHTML = head + Object.keys(byState).map(function (st) {
          var rows = byState[st] || [];
          if (!rows.length) return '';
          return '<h3>' + AB_STATE[st] + ' · ' + rows.length + ' 条</h3>' +
            '<div class="scrollx"><table class="abtab"><thead><tr><th>名称</th><th>职业/专精</th><th>层级线索</th><th>官方原句</th></tr></thead><tbody>' +
            rows.map(function (x) {
              var tier = x.tierFrom !== null && x.tierFrom !== undefined
                ? '第' + x.tierFrom + ' 层 → 第' + x.tierHint + ' 层'
                : (x.tierHint ? '第' + x.tierHint + ' 层' : '—');
              if (x.milestone) tier += ' ｜ 第' + x.milestone + ' 点关键天赋';
              return '<tr><td>' + iconCell(ICONS[x.classId + '|' + x.name], x.classId + x.name, x.name, 1) +
                '<b>' + D.esc(x.name) + '</b><br><span class="dim">' +
                D.esc(AB_KIND[x.kind] || x.kind) + '</span></td>' +
                '<td>' + D.esc(cnName[x.classId] || x.classId) +
                (x.spec ? ' · ' + D.esc(AB_SPEC[x.spec] || x.spec) : '') + '</td>' +
                '<td class="mono">' + D.esc(tier) + '</td>' +
                '<td class="quote">' + D.esc(x.quote) + '</td></tr>';
            }).join('') + '</tbody></table></div>';
        }).join('') + '<p class="src">来源：' + (((ab.meta || {}).sources) || []).map(function (x) { return D.esc(x.label); }).join('、') +
          ' ｜ 核对日期：' + D.esc((ab.meta || {}).generatedAt || '') + '，整句照录不改写</p>';
        el('abcnt').textContent = ' · ' + list.length + ' 条官方原句';
        Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function (b) {
          b.onclick = function () { D.copy(b.dataset.copy); };
        });
      }
      set('<div class="card"><h1 class="pt">技能书</h1><p class="dim">按职业与种族分组。英文原名与专精归属是待补项，缺的地方直接写「待补」，不做机翻。</p>' +
        '<p class="note">图标：能显出图案的是本地转存的官方天赋图标；字母块是自绘占位，代表这一条没有可信图标来源，不是游戏里的样子。</p>' +
        '<div class="field"><input type="search" id="q" placeholder="搜中文或英文">' +
        '<select id="c"><option value="">全部职业</option>' + cls.map(function (x) { return '<option value="' + x.id + '">' + D.esc(x.cn) + '</option>'; }).join('') + '</select>' +
        '<select id="k"><option value="">全部类型</option>' + Object.keys(KIND).filter(function (k) {
          return items.some(function (x) { return x.kind === k; });
        }).map(function (k) { return '<option value="' + k + '">' + KIND[k] + '</option>'; }).join('') + '</select>' +
        '<span class="dim mono" id="cnt"></span></div></div>' +
        '<div class="card"><h2>与经典旧世的差异（四态）<span class="dim mono" id="abcnt"></span></h2><div id="abtbl"></div></div>' +
        '<div class="card tblbox"><div id="tbl"></div></div>');
      el('q').oninput = function (e) { f.q = e.target.value; draw(); };
      el('c').onchange = function (e) { f.c = e.target.value; draw(); };
      el('k').onchange = function (e) { f.k = e.target.value; draw(); };
      draw();
    }).catch(fail);
  }

  /* ---------- 副本手册 ---------- */
  function dunGaps(x) {
    var g = [];
    if (!x.nameCn) g.push('中文定名（现在保留英文原名，未机翻）');
    if (x.nameCnConflict) g.push('中文名定稿：官方与转载两种叫法并存');
    if (!x.levelRange) g.push('可进入的等级区间');
    if (!(x.bosses || []).length) g.push('首领名单：客户端解包里还没有这座本的数据');
    else if (!(x.drops || []).length) g.push('掉落归属：上游开放数据库里还没有它的首领掉落');
    else g.push('掉落的实装情况与概率（本站不写百分比，等正式服实测）');
    if (!(x.route || []).length) g.push('跑图路线与跳怪点');
    if (x.kind === 'raid') g.push('开放时间、团队规模——仅有第三方说法');
    return g;
  }
  function dunRoute(arr) {
    if (!arr || !arr.length) return '';
    return '<ul class="list">' + arr.map(function (r) {
      var o = r && typeof r === 'object' ? r : {};
      var txt = typeof r === 'string' ? r : (r.label || r.name || r.text || '');
      var at = o.at || '';
      return '<li>' + D.esc(txt || '这一步官方没给文字说明') +
        (at ? ' <span class="dim mono">' + D.esc(at) + '</span>' : '') + '</li>';
    }).join('') + '</ul>';
  }
  var DUN_STATE = {
    L0: '名单与等级区间已按官方中文核对',
    L1: '名单已核，中文定名待官方公布',
    L2: '名单已核，细节等实测或官方补充',
    L3: '目前只有线索，细节未确认'
  };
  var WORLD_TODO = [
    ['世界地图', '跑图坐标在中文侧完全没有：官方公告不含坐标，第三方库的数据本站禁止搬，只能等实测或官方地图工具。'],
    ['PvP', '无限服的 PvP 规则、战场与积分口径官方还没给中文稿；且强度排行是本站红线，不做。'],
    ['坐骑', '只有第三方"新物品"清单的线索，没有官方中文名与原文整句。'],
    ['套装', '套装件数与效果在官方中文稿里还没出现，硬写等于编造。'],
    ['隐藏内容', '属攻略性质，本站红线不做攻略正文与机制清单。']
  ];
  function dunStateText(x) {
    var p = x.provenance || [];
    var off = p.some(function (s) { return (s.type || '').indexOf('official') === 0; });
    if (off || x.level !== 'L0') return DUN_STATE[x.level] || '';
    return '名单与等级区间取自客户端解包（第三方资料站转述），未逐条进游戏核对';
  }
  function dunLoot(x) {
    var bosses = x.bosses || [], drops = x.drops || [];
    if (!bosses.length) return '<p class="dim">客户端解包还没给出这座本的首领名单——无限新增副本里这种的掉落表上游也还没有，不猜。</p>';
    return '<ul class="bosslist">' + bosses.map(function (b) {
      var mine = drops.filter(function (y) { return y.bossId === b.id; });
      return '<li><div class="bh"><b>' + D.esc(b.nameCn) + '</b>' +
        (mine.length ? '<span class="dim">' + mine.length + ' 件掉落</span>' : '<span class="dim">掉落未列</span>') + '</div>' +
        (mine.length ? '<div class="loot">' + mine.map(function (y) {
          return '<span class="loot-i">' + iconCell(y.iconKey, y.itemId, y.nameCn, 1) +
            D.esc(y.nameCn) + '<span class="dim mono">#' + D.esc(y.itemId) + '</span>' + D.pill('L2') + '</span>';
        }).join('') + '</div>'
          : (b.note ? '<div class="note">' + D.esc(b.note) + '</div>' : '')) + '</li>';
    }).join('') + '</ul>' + (x.lootNote ? '<div class="note">' + D.esc(x.lootNote) + '</div>' : '');
  }
  // 按十级一档分：起点落在哪档就归哪档，50 级往上并成"满级前后"
  var DUN_BANDS = [[10, 19, '起步'], [20, 29, '前期'], [30, 39, '中期'], [40, 49, '中后期'], [50, 99, '满级前后']];
  function dunBand(x) {
    var s = parseInt(String(x.levelRange || '').split('-')[0], 10);
    if (!s) return null;
    for (var i = 0; i < DUN_BANDS.length; i++) if (s >= DUN_BANDS[i][0] && s <= DUN_BANDS[i][1]) return i;
    return null;
  }
  function dungeons() {
    Promise.all([D.load('data/dungeons.json'), D.load('data/art.json').catch(function () { return {}; })])
      .then(function (rs) {
      var d = rs[0], ART = rs[1] || {};
      var all = [].concat(d.newDungeons || [], d.classicDungeons || [], d.raids || []);
      var nb = all.reduce(function (s, x) { return s + (x.bosses || []).length; }, 0);
      var nd = all.reduce(function (s, x) { return s + (x.drops || []).length; }, 0);
        function card(x) {
          var banner = window.Glyph ? Glyph.dungeonBanner(x.id,
            x.nameCn || x.nameEn || '未定名',
            { kind: x.kind, sub: x.zoneCn || ((x.nameCn && x.nameEn) ? x.nameEn : ''),
              art: x.art || (ART.dungeons || {})[x.id] || null,
              seal: x.kind === 'new' ? '新' : null,
              range: x.levelRange ? x.levelRange + ' 级' : null }) : '';
          return '<div class="dcard2">' + banner +
            '<div class="dmeta">' + D.pill(x.level) +
            '<span>' + ((x.bosses || []).length || '待补') + ' 个首领</span>' +
            '<span>' + ((x.drops || []).length || '未列') + ' 件掉落</span>' +
            '<span class="dim">' + dunStateText(x) + (x.nameCn ? '' : '；中文定名未公布') + '</span></div>' +
            (x.levelRangeAlt ? '<div class="conf">等级区间两说：本站取「' + D.esc(x.levelRange) +
              '」（官方公告），上游卡片写「' + D.esc(x.levelRangeAlt) + '」，待定稿</div>' : '') +
            (x.nameCnConflict ? '<div class="conf">译名冲突：官方写「' + D.esc(x.nameCn) + '」，转载写作「' +
              D.esc(x.nameCnConflict) + '」，待定稿</div>' : '') +
            '<button class="ghost wide" data-d="' + D.esc(x.id) + '">速览首领与掉落</button>' +
            '<div class="drawer" id="d-' + D.esc(x.id) + '" style="display:none">' +
            '<h3>首领与掉落</h3>' + dunLoot(x) +
            '<h3>路线</h3>' + (dunRoute(x.route) || '<p class="dim">待实测。</p>') +
            '<h3>这座本还没确认的</h3><ul class="list">' + dunGaps(x).map(function (g) { return '<li>' + D.esc(g) + '</li>'; }).join('') + '</ul>' +
            '<h3>来源与核对</h3>' + D.sources(x.provenance) + '</div></div>';
        }
        function bandBlock(title, sub, rows) {
          if (!rows.length) return '';
          return '<div class="band"><b>' + title + '</b>' + (sub ? '<span class="dim">' + sub + '</span>' : '') +
            '<span class="dim mono">' + rows.length + ' 座</span></div>' +
            '<div class="dgrid">' + rows.map(card).join('') + '</div>';
        }
        var list = (d.newDungeons || []).concat(d.classicDungeons || []);
        var body = DUN_BANDS.map(function (b, i) {
          var rows = list.filter(function (x) { return dunBand(x) === i; })
            .sort(function (p, q) { return parseInt(p.levelRange, 10) - parseInt(q.levelRange, 10); });
          return bandBlock(b[0] + (b[1] > 60 ? '–60' : '–' + b[1]) + ' 级', b[2], rows);
        }).join('') +
          bandBlock('区间未定', '等级区间还没核', list.filter(function (x) { return dunBand(x) === null; })) +
          bandBlock('团队副本', '开放时间未定', d.raids || []);
        set('<div class="card"><h1 class="pt">副本手册</h1><p class="dim">共 ' + all.length + ' 座：' +
          (d.newDungeons || []).length + ' 座无限新增、' + (d.classicDungeons || []).length + ' 座经典本、' +
          (d.raids || []).length + ' 座团本，按十级一档分。首领 ' + nb + ' 个、掉落归属 ' + nd + ' 件。' +
          '名单与等级区间取自客户端解包（第三方资料站转述）；掉落是上游按经典旧世开放数据库推的，一律标待实测。</p></div>' +
        '<div class="banner">掉落数据本站<b>不写百分比</b>：这里只回答"谁掉了什么"，不回答"多大概率"。暴雪说过无限服重做过掉落，正式开放可能变化。</div>' +
        body +
        '<div class="card" id="todo"><h2>「世界」里还没采集的</h2>' +
        '<p class="note">这几项在参考站都有独立页面，我们这里只有位置、没有数据。' +
        '原因逐条写清楚，不做空壳页糊人。</p>' +
        '<table><thead><tr><th>板块</th><th>为什么还空着</th></tr></thead><tbody>' +
        WORLD_TODO.map(function (x) { return '<tr><td>' + D.esc(x[0]) + '</td><td class="dim">' + D.esc(x[1]) + '</td></tr>'; }).join('') +
        '</tbody></table></div>');
      Array.prototype.forEach.call(document.querySelectorAll('[data-d]'), function (b) {
        var label = b.textContent;
        b.onclick = function () {
          var x = el('d-' + b.dataset.d);
          x.style.display = x.style.display === 'none' ? 'block' : 'none';
          b.textContent = x.style.display === 'none' ? label : '收起';
        };
      });
    }).catch(fail);
  }

  /* ---------- 术语速查 ---------- */
  function glossary() {
    Promise.all([D.load('data/glossary.json'), D.load('data/races.json'),
      D.load('data/classes.json'), D.load('data/icons.json')]).then(function (r) {
      var items = r[0].items, RACE = raceLookup(r[1].races), classes = r[2].classes;
      var ICONS = (r[3] || {}).map || {};
      var KIND = { talent: '天赋/技能', item: '装备', racial: '种族特长' };
      var f = { q: '', race: '', kind: '' };
      var raceIds = [];
      items.forEach(function (x) {
        if (!x.raceId) return;
        var rid = raceBucket(x.raceId);
        if (raceIds.indexOf(rid) < 0) raceIds.push(rid);
      });
      raceIds.sort(function (a, b) { return RACE.order.indexOf(a) - RACE.order.indexOf(b); });
      function draw() {
        var list = items.filter(function (x) {
          if (f.kind && x.kind !== f.kind) return false;
          if (f.race && raceBucket(x.raceId || '') !== f.race) return false;
          if (f.q && ((x.cn || '') + (x.en || '')).toLowerCase().indexOf(f.q.toLowerCase()) < 0) return false;
          return true;
        });
        var groups = groupEntries(list, classes, RACE);
        el('pool').innerHTML = groups.length ? groups.map(function (g) {
          return '<div class="lgrp">' + g.tile + '<b>' + D.esc(g.name) + '</b>' +
            (g.sub ? '<span class="dim mono">' + D.esc(g.sub) + '</span>' : '') +
            '<span class="dim">' + g.rows.length + ' 条</span></div>' +
            '<div class="pool">' + g.rows.map(function (x) {
              return '<span class="term ' + (f.q ? 'hit' : '') + '" data-c="' + D.esc(x.cn + (x.en ? ' / ' + x.en : '')) + '">' +
                iconCell(ICONS[iconKeyOf(x)], x.id, x.cn, 1) + D.esc(x.cn) +
                '<button class="info" data-src="' + D.esc(x.id) + '" data-name="' + D.esc(x.cn) + '" data-prov="' +
                encodeURIComponent(JSON.stringify(x.provenance || [])) + '" aria-label="查看「' + D.esc(x.cn) + '」的来源">来源</button></span>';
            }).join('') + '</div>';
        }).join('') : '<div class="empty">没有匹配词条。缺的词条说明官方还没给中文名，或我们还没采到。</div>';
        el('cnt').textContent = list.length + ' / ' + items.length;
        bindSrcToggles(el('pool'));
        Array.prototype.forEach.call(document.querySelectorAll('.term[data-c]'), function (t) {
          t.onclick = function () { D.copy(t.dataset.c); };
        });
      }
      set('<div class="card"><h1 class="pt">中英术语速查</h1><p class="dim">点词条即复制，「来源」看这条中文名出自哪句官方原文。' +
        '英文原名官方没给的一律留空，所以有「待补」。</p>' +
        '<p class="note">按职业与种族分组。字母块是自绘占位，代表这一条没有可信图标来源。</p>' +
        '<div class="field"><input type="search" id="q" placeholder="输入中文或英文">' +
        '<select id="fk" aria-label="按类型筛选"><option value="">全部类型</option>' +
        Object.keys(KIND).map(function (k) { return '<option value="' + k + '">' + KIND[k] + '</option>'; }).join('') + '</select>' +
        '<select id="fr" aria-label="按种族筛选"><option value="">全部种族</option>' +
        raceIds.map(function (id) { return '<option value="' + id + '">' + D.esc((RACE[id] || {}).cn || id) + '</option>'; }).join('') + '</select>' +
        '<span class="dim mono" id="cnt"></span></div>' +
        '<div id="pool"></div>' +
        '<div class="srcbox" id="srcbox" style="display:none"></div></div>');
      el('q').oninput = function (e) { f.q = e.target.value.trim(); draw(); };
      el('fk').onchange = function (e) { f.kind = e.target.value; draw(); };
      el('fr').onchange = function (e) { f.race = e.target.value; draw(); };
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
        set('<div class="card"><h1 class="pt">溯源与覆盖率</h1><p class="dim">每条数据从哪来、什么时候核的、哪些刻意没拿，全部摊在这里。</p></div>' +
          '<div class="card"><h2>数据覆盖率</h2>' + D.covBar(cov) +
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
      set('<div class="card"><h1 class="pt">系统与新区域</h1><p class="dim">规则、区域、种族与装备名的官方中文口径，逐条带来源。</p></div>' +
        s.groups.map(function (g) {
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

  /* ---------- 种族 ---------- */
  function races() {
    Promise.all([D.load('data/races.json'), D.load('data/classes.json'), D.load('data/glossary.json')])
      .then(function (r) {
        var R = r[0], classes = r[1].classes, gloss = r[2].items;
        var CNAME = {};
        classes.forEach(function (c) { CNAME[c.id] = c.cn; });
        var FAC = { horde: '部落', alliance: '联盟' };
        var cols = (R.classOrder || []).filter(function (id) { return CNAME[id]; });
        var traits = [];
        R.races.forEach(function (x) {
          var list = x.subgroup ? x.subgroup.traits : x.traits;
          var owner = x.subgroup ? x.subgroup.nameCn : x.nameCn;
          (list || []).forEach(function (t) { traits.push({ race: x, owner: owner, t: t }); });
        });
        var inGloss = gloss.filter(function (i) { return i.kind === 'racial' && i.raceId; }).length;
        var f = { c: '', fac: '', q: '' };

        function srcBtn(id, name, prov) {
          return '<button class="info" data-src="' + D.esc(id) + '" data-name="' + D.esc(name) +
            '" data-prov="' + encodeURIComponent(JSON.stringify(prov || [])) +
            '" aria-label="查看「' + D.esc(name) + '」的来源">来源</button>';
        }
        function matrix() {
          var rows = R.races.filter(function (x) { return !f.fac || x.faction === f.fac; });
          return '<table class="mtx"><thead><tr><th class="rh">种族 \\ 职业</th>' +
            cols.map(function (id) {
              return '<th><button type="button" class="ch' + (f.c === id ? ' on' : '') + '" data-cl="' + id +
                '" aria-pressed="' + (f.c === id ? 'true' : 'false') + '">' + D.esc(CNAME[id]) + '</button></th>';
            }).join('') + '</tr></thead><tbody>' +
            rows.map(function (x) {
              var hit = f.c && x.classes.indexOf(f.c) < 0;
              return '<tr' + (hit ? ' class="off"' : '') + '><th class="rh">' + Glyph.raceTile(x.id, x.faction, x.nameCn, x.iconKey) +
                '<span>' + D.esc(x.nameCn) + (x.subgroup ? '<em>' + D.esc(x.subgroup.nameCn.replace(x.nameCn, '')) + '</em>' : '') +
                '</span></th>' +
                cols.map(function (id) {
                  var ok = x.classes.indexOf(id) >= 0;
                  return '<td class="' + (ok ? 'y' : 'n') + '">' + (ok ? '✓' : '—') + '</td>';
                }).join('') + '</tr>';
            }).join('') + '</tbody></table>';
        }
        function traitTable() {
          var q = f.q.toLowerCase();
          var list = traits.filter(function (x) {
            if (f.fac && x.race.faction !== f.fac) return false;
            if (f.c && x.race.classes.indexOf(f.c) < 0) return false;
            if (q && (x.t.name + x.t.effect + x.owner).toLowerCase().indexOf(q) < 0) return false;
            return true;
          });
          var byRace = [];
          R.races.forEach(function (x) {
            var rows = list.filter(function (t) { return t.race.id === x.id; });
            if (rows.length) byRace.push({ race: x, rows: rows });
          });
          return byRace.length ? byRace.map(function (g) {
            var x = g.race;
            return '<div class="lgrp">' + Glyph.raceTile(x.id, x.faction, x.nameCn, x.iconKey) +
              '<b>' + D.esc(x.subgroup ? x.subgroup.nameCn : x.nameCn) + '</b>' +
              '<span class="dim mono">' + FAC[x.faction] + '</span><span class="dim">' + g.rows.length + ' 条</span></div>' +
              '<div class="scrollx"><table><thead><tr><th class="ich">图标</th><th>特长</th><th>类型</th><th>官方整句</th><th></th></tr></thead><tbody>' +
              g.rows.map(function (t) {
                return '<tr><td class="ich">' + iconCell(t.t.iconKey, x.id + t.t.name, t.t.name) + '</td>' +
                  '<td>' + D.hl(t.t.name, f.q) + '</td>' +
                  '<td>' + (t.t.passive ? '被动' : '主动') + '</td>' +
                  '<td class="quote">' + D.hl(t.t.quote, f.q) + '</td>' +
                  '<td class="act">' + srcBtn('tr-' + x.id + '-' + t.t.name, t.t.name,
                    [{ type: 'official_cn', url: R.meta.sources[0].url, quote: t.t.quote,
                       note: '官方种族公告·该特长列在「' + t.owner + '」小标题下', checkedAt: x.provenance[0].checkedAt }]) + '</td></tr>';
              }).join('') + '</tbody></table></div>';
          }).join('') : '<div class="empty">没有匹配的特长。</div>';
        }
        function draw() {
          el('mx').innerHTML = matrix();
          el('tt').innerHTML = traitTable();
          el('mhint').innerHTML = f.c
            ? '已按「' + D.esc(CNAME[f.c]) + '」筛选：灰色行是不能选该职业的种族。<button type="button" class="ghost mini" id="cx">清除</button>'
            : '点表头职业名可筛选。✓ 与 — 直接来自官方表格里的 X 标记，没有第三方补的。';
          var cx = el('cx');
          if (cx) cx.onclick = function () { f.c = ''; draw(); };
          Array.prototype.forEach.call(el('mx').querySelectorAll('button.ch'), function (b) {
            b.onclick = function () { f.c = f.c === b.dataset.cl ? '' : b.dataset.cl; draw(); };
          });
          el('tcnt').textContent = el('tt').querySelectorAll('tbody tr').length + ' / ' + traits.length + ' 条';
          bindSrcToggles();
        }

        set('<div class="card"><h1 class="pt">种族与职业组合</h1>' +
          '<p class="dim">数据全部来自国服官方中文公告，逐条带原文。英文原名官方没给的一律留空，不逐词硬造。</p>' +
          '<div class="stats" style="margin-top:12px">' +
          '<div class="stat"><b>' + R.races.length + '</b>种族行</div>' +
          '<div class="stat"><b>' + traits.length + '</b>条种族特长</div>' +
          '<div class="stat"><b>' + R.newCombos.length + '</b>组亮点组合</div>' +
          '<div class="stat"><b>' + inGloss + '</b>条已进速查</div></div>' +
          (R.skyborneNote && R.skyborneNote.text ? '<p class="dim" style="margin-top:12px">' +
            '<span class="tag">官方原文</span>' + D.esc(R.skyborneNote.text) + '</p>' : '') + '</div>' +

          '<div class="card"><h2>种族 × 职业矩阵</h2><p class="dim" style="font-size:12.5px" id="mhint"></p>' +
          '<div class="field"><label class="dim">阵营</label><select id="ff"><option value="">全部</option>' +
          '<option value="horde">部落</option><option value="alliance">联盟</option></select>' +
          '<label class="dim">找特长</label><input type="search" id="fq" placeholder="名称或效果里的词">' +
          '<span class="dim mono" id="tcnt"></span></div>' +
          '<div class="scrollx" id="mx"></div></div>' +

          '<div class="card"><h2>种族一览</h2>' +
          '<p class="dim" style="font-size:12.5px">矩阵表给"能不能选"，小标题下的段落给官方怎么写这个种族。两段都在同一篇公告里，没有第三方补的。</p>' +
          R.races.map(function (x) {
            var sub = x.subgroup;
            var lore = sub ? sub.lore : x.lore;
            var tl = sub ? sub.traits : x.traits;
            return '<div class="rcard"><div class="rh">' + Glyph.raceTile(x.id, x.faction, x.nameCn, x.iconKey) +
              '<div style="flex:1"><b>' + D.esc(x.nameCn) +
              (sub ? '<span class="dim"> · ' + D.esc(sub.nameCn) + '</span>' : '') + '</b>' +
              '<div class="dim" style="font-size:12px">' + FAC[x.faction] + ' · 可选 ' + x.classes.length +
              ' 个职业 · ' + (tl || []).length + ' 条特长</div></div>' + D.pill(x.level) +
              '<button class="ghost mini" data-d="' + D.esc(x.id) + '">来源</button></div>' +
              '<p class="dim" style="margin:6px 0 0">' + (lore ? D.esc(lore) : '官方本页没有这个种族的简介段。') + '</p>' +
              '<div class="chips">' + cols.map(function (id) {
                return '<span class="chipc' + (x.classes.indexOf(id) >= 0 ? '' : ' off') + '">' + D.esc(CNAME[id]) + '</span>';
              }).join('') + '</div>' +
              '<div class="drawer" id="d-' + D.esc(x.id) + '" style="display:none"><h3>来源与核对</h3>' +
              D.sources(x.provenance) + '</div></div>';
          }).join('') + '</div>' +

          '<div class="card" id="traits"><h2>种族特长</h2>' +
          '<p class="dim" style="font-size:12.5px">官方页把每条特长写成一个句子，这里整句原样引用；数值只到官方写出的那一句，不做推算。</p>' +
          '<div class="scrollx" id="tt"></div>' +
          '<div class="srcbox" id="srcbox" style="display:none"></div></div>' +

          '<div class="card"><h2>新开放的组合</h2><p class="dim" style="font-size:12.5px">官方原文那句：' +
          D.esc((R.newCombos[0] && R.newCombos[0].provenance[0].quote) || '') + '</p>' +
          '<div class="pool">' + R.newCombos.map(function (c) {
            return '<span class="term">' + D.esc(c.label) + srcBtn('nc-' + c.label, c.label, c.provenance) + '</span>';
          }).join('') + '</div></div>' +

          (R.conflicts || []).map(function (cf) {
            return '<div class="card"><h2>同一页里两种说法并存</h2><p class="dim" style="font-size:12.5px">' +
              D.esc(cf.topic) + ' ' + D.pill(cf.level) + '</p>' +
              '<ul class="list"><li><b>矩阵表</b>：' + D.esc(cf.a.saying) +
              '<span class="dim">（明细：' + D.esc(cf.a.detail || '') + '。官方在表里只写 X，没有整句可引）</span></li>' +
              '<li><b>导语</b>：' + D.esc(cf.b.saying) + '<span class="quote">原文：' + D.esc(cf.b.quote) + '</span></li>' +
              '<li><b>本站处置</b>：' + D.esc(cf.handling) + '</li></ul></div>';
          }).join('') +

          '<div class="card"><h2>这一页没有的</h2><ul class="list">' +
          (R.meta.notCollected || []).map(function (x) { return '<li>' + D.esc(x) + '</li>'; }).join('') +
          '</ul></div>');

        el('ff').onchange = function (e) { f.fac = e.target.value; draw(); };
        el('fq').oninput = function (e) { f.q = e.target.value.trim(); draw(); };
        Array.prototype.forEach.call(document.querySelectorAll('.rcard [data-d]'), function (b) {
          b.onclick = function () {
            var x = el('d-' + b.dataset.d);
            x.style.display = x.style.display === 'none' ? 'block' : 'none';
            b.textContent = x.style.display === 'none' ? '来源' : '收起';
          };
        });
        draw();
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
  ({ home: home, talent: talent, chooser: chooser, timeline: timeline, skills: skills, dungeons: dungeons, systems: systems, races: races, glossary: glossary, provenance: provenance })[page]();
})();
