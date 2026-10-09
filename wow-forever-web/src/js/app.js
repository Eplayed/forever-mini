/* 页面渲染与交互 */
(function () {
  var D = window.WowData, E = window.TalentEngine;
  /* 两级常驻导航：一级是分组标签（不可点），二级项全部平铺露出，说明文字收进 title 悬停提示。
     参考站的「攻略」「新动态」不挂：本站红线不做攻略正文与新闻流。 */
  var NAV = [
    { t: '首页', href: 'index.html', d: '数据覆盖率与全部入口' },
    { t: '天赋', items: [
      { href: 'talent.html', t: '计算器', d: '9 职业 · 树结构与加点' }] },
    { t: '职业', items: [
      { href: 'chooser.html', t: '玩法问答', d: '7 题玩法取向问答，不是强度排行' },
      { href: 'skills.html', t: '技能书', d: '中英对照 + 与经典旧世的四态差异' }] },
    { t: '种族', items: [
      { href: 'races.html', t: '总览', d: '10 个种族行 · 可选职业矩阵' },
      { href: 'races.html#traits', t: '特长', d: '40 条官方中文原名与整句' }] },
    { t: '世界', items: [
      { href: 'world.html', t: '区域与稀有', d: '44 个区域 · 36 个稀有刷新点 · 书籍与营地' },
      { href: 'dungeons.html', t: '副本', d: '38 座按十级一档分：首领与掉落归属' },
      { href: 'systems.html', t: '系统规则', d: '规则、区域、装备名的官方中文说法' }] },
    { t: '专业', items: [
      { href: 'professions.html', t: '配方', d: '13 个专业 · 配方材料与采集点' }] },
    { t: '工具', items: [
      { href: 'glossary.html', t: '速查', d: '中英术语，点一下即复制' },
      { href: 'timeline.html', t: '时间表', d: '11 个上线时间点带官方原文' },
      { href: 'updates.html', t: '动态', d: '官方时间点 + 客户端改动（仅网页）' },
      { href: 'rank.html', t: '排行', d: '本站资料完整度排序，不是强度（仅网页）' },
      { href: 'provenance.html', t: '溯源', d: '哪些已核实、哪些只是线索' }] }
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
    var left = launchLeft();
    // 一级是分组标签（只说明归属，不可点），二级项全部平铺：玩家不用点开菜单就知道这站有什么
    function navLink(it) {
      return '<a class="nl' + (page === navKey(it.href) ? ' on' : '') + '" href="' + it.href +
        '" title="' + D.esc(it.d) + '">' + it.t + '</a>';
    }
    el('top').innerHTML = '<div class="in"><a class="brand" href="index.html">无限<span>资料站</span></a>' +
      '<div class="chip mono" id="lchip">距上线 ' + left.d + ' 天 ' + pad2(left.h) + ':' +
      pad2(left.m) + ':' + pad2(left.s) + '</div></div>' +
      '<nav class="main" aria-label="主导航"><div class="in">' + NAV.map(function (g) {
        if (g.href) return navLink(g);
        var hit = g.items.some(function (it) { return page === navKey(it.href); });
        return '<span class="ngrp' + (hit ? ' hit' : '') + '"><b class="ngt">' + g.t + '</b>' +
          g.items.map(navLink).join('') + '</span>';
      }).join('') + '</div></nav>';
    // 手机上是横滑导航带：把当前页那一项先滚到中间，免得进来只看到别的分组
    var cur = el('top').querySelector('nav.main a.nl.on');
    if (cur && cur.scrollIntoView && window.innerWidth <= 600) {
      cur.scrollIntoView({ inline: 'center', block: 'nearest' });
    }
    Promise.all([D.load('data/meta.json'), D.load('data/scale.json')])
      .then(function (r) {
        var meta = r[0], sc = r[1].scale, cov = sc.pubCoverage;
        el('foot').innerHTML = '<div class="in"><span>' + D.esc(meta.disclaimer) + '</span>' +
          '<span>数据来源版本：<span class="mono">' + D.esc(meta.dataBaseline.build) + '</span>，核对于 ' +
          D.esc(meta.dataBaseline.checkedAt) + '</span>' +
          '<span>资料覆盖率（不含天赋）L0 ' + cov.L0 + ' / L1 ' + cov.L1 + ' / L2 ' + cov.L2 +
          ' / L3 ' + cov.L3 + '，共 ' + sc.pubTotal + ' 条</span></div>';
      }).catch(function () { });
  }

  /* ---------- 上线倒计时：顶栏 chip 与首页共用一个算法与同一个定时器 ---------- */
  // 日期与 data/meta.json 的 launch 字段对齐，build-data.js 会卡两边不一致，别在这里手改日期
  var LAUNCH = '2026-11-05T00:00:00+08:00';
  function launchLeft() {
    var ms = Math.max(0, new Date(LAUNCH).getTime() - Date.now());
    return {
      d: Math.floor(ms / 86400000), h: Math.floor(ms / 3600000) % 24,
      m: Math.floor(ms / 60000) % 60, s: Math.floor(ms / 1000) % 60
    };
  }
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  // 每秒只改两个节点的文本，不重排页面；节点没渲染出来就跳过这一跳（其他页没有倒计时块）
  function tickCountdown() {
    var l = launchLeft(), t = pad2(l.h) + ':' + pad2(l.m) + ':' + pad2(l.s);
    var chip = el('lchip');
    if (chip) chip.textContent = '距上线 ' + l.d + ' 天 ' + t;
    var d = el('cdD'), h = el('cdT');
    if (d) d.textContent = String(l.d);
    if (h) h.textContent = t;
  }

  /* ---------- 全站搜索：一个框搜到所有板块 ----------
     索引由 build-data.js 从已校验的数据派生（src/data/search.json），
     只收「名称 + 归属」，命中后带着词跳进对应页面，由那一页自己的筛选器接手。 */
  var SX = { idx: null, kinds: null, job: null, rows: [] };
  // 分组显示顺序：先身份类，再内容类，配方与采集点这种长尾放后面
  var SKIND_ORDER = ['cls', 'race', 'tal', 'chg', 'term', 'abl', 'dun', 'boss', 'zone', 'rare',
    'bok', 'camp', 'prof', 'rec', 'gnd', 'tra'];
  var SSHOWN = 5;

  function searchIdx() {
    if (SX.idx) return Promise.resolve(SX.idx);
    if (!SX.job) {
      SX.job = D.load('data/search.json').then(function (j) {
        SX.kinds = j.meta.kinds; SX.idx = j.items; return SX.idx;
      }).catch(function (e) { SX.job = null; throw e; });
    }
    return SX.job;
  }
  function sHref(it) {
    var kd = SX.kinds[it[0]];
    if (!kd) return 'index.html';
    var parts = [];
    if (it[3]) parts.push(it[3]);
    if (kd[2]) parts.push(kd[2] + '=' + encodeURIComponent(it[1]));
    return kd[1] + (parts.length ? '?' + parts.join('&') : '');
  }
  function sScore(n, k) {
    if (n === k) return 0;
    if (n.indexOf(k) === 0) return 1;
    if (n.indexOf(k) > 0) return 2;
    return -1;
  }
  function sRun(q) {
    var k = q.trim().toLowerCase();
    if (!k || !SX.idx) return [];
    var hits = [];
    SX.idx.forEach(function (it) {
      var sc = sScore(String(it[1]).toLowerCase(), k);
      if (sc < 0) return;
      hits.push([sc, SKIND_ORDER.indexOf(it[0]), String(it[1]).length, it]);
    });
    hits.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1] || a[2] - b[2]; });
    return hits.slice(0, 120).map(function (h) { return h[3]; });
  }
  function sGroups(hits) {
    var g = {};
    hits.forEach(function (it) { (g[it[0]] = g[it[0]] || []).push(it); });
    return SKIND_ORDER.filter(function (k) { return g[k] && SX.kinds[k]; }).map(function (k) {
      return { k: k, label: SX.kinds[k][0], page: SX.kinds[k][1], param: SX.kinds[k][2],
        all: g[k].length, show: g[k].slice(0, SSHOWN) };
    });
  }
  function sRender(q) {
    var box = el('gres'), inp = el('gs');
    if (!box || !inp) return;
    var k = q.trim();
    SX.rows = [];
    inp.setAttribute('aria-expanded', k ? 'true' : 'false');
    if (!k) { box.hidden = true; box.innerHTML = ''; return; }
    if (!SX.idx) {
      box.hidden = false;
      box.innerHTML = '<p class="gsl">正在读索引…</p>';
      return;
    }
    var hits = sRun(k);
    if (!hits.length) {
      box.hidden = false;
      box.innerHTML = '<p class="gsl">索引里没有叫「' + D.esc(k) + '」的条目。本站按官方中文原名收录，' +
        '别名与英文请进对应页面搜；也不搜攻略说法。</p>';
      return;
    }
    box.hidden = false;
    box.innerHTML = sGroups(hits).map(function (g) {
      var all = g.param ? g.page + '?' + g.param + '=' + encodeURIComponent(k) : g.page;
      return '<div class="gsh"><b>' + D.esc(g.label) + '</b><a href="' + D.esc(all) + '">' +
        (g.all > SSHOWN ? '这一类共 ' + g.all + ' 条，进去看全部 →' : g.all + ' 条 →') + '</a></div>' +
        g.show.map(function (it) {
          SX.rows.push(it);
          return '<a class="gsr" href="' + D.esc(sHref(it)) + '">' +
            '<b>' + D.hl(it[1], k) + '</b>' +
            '<span class="dim">' + D.esc(it[2]) + '</span>' +
            (it[4] && it[4] !== 'L0' ? '<em class="lv ' + D.esc(it[4]) + '">' + D.pillName(it[4]) + '</em>' : '') +
            '</a>';
        }).join('');
    }).join('') +
      '<p class="gsl dim mono">命中 ' + hits.length + ' 条，这里先列 ' + SX.rows.length + ' 条</p>';
  }
  function bindSearch() {
    var inp = el('gs');
    if (!inp) return;
    var run = function () {
      var v = inp.value;
      var ready = SX.idx ? Promise.resolve(SX.idx) : searchIdx().catch(function () { return null; });
      ready.then(function () { if (el('gs') === inp && inp.value === v) sRender(v); });
    };
    inp.oninput = run;
    inp.onkeydown = function (e) {
      if (e.key === 'Escape') { inp.value = ''; sRender(''); inp.blur(); return; }
      if (e.key === 'ArrowDown') {
        var a = document.querySelector('#gres .gsr');
        if (a) { a.focus(); e.preventDefault(); }
        return;
      }
      if (e.key === 'Enter' && SX.rows.length) location.href = sHref(SX.rows[0]);
    };
    // 点框外收起：结果区里点链接会自己跳转，不需要额外处理
    document.addEventListener('click', function (e) {
      var box = el('gres');
      if (!box || box.hidden) return;
      var w = document.querySelector('.gsearch');
      if (w && !w.contains(e.target)) sRender('');
    });
    // 示例词：给不知道搜什么的人一个起点，点了就当真搜一遍
    Array.prototype.forEach.call(document.querySelectorAll('.gsx'), function (b) {
      b.onclick = function () {
        inp.value = b.dataset.s;
        inp.focus();
        run();
      };
    });
  }
  function urlQ(name) {
    try { return new URLSearchParams(location.search).get(name) || ''; } catch (e) { return ''; }
  }
  // 跳进来的页面把词填进自己的搜索框，用户落地就看到筛好的结果
  function prefill(id, val) {
    var i = el(id);
    if (i && val && !i.value) { i.value = val; if (i.oninput) i.oninput({ target: i }); }
    return i;
  }


  /* ---------- 首页的只读天赋树预览 ----------
     数据是 build-data.js 从完整天赋文件派生的轻量件（28 KB，只有画格子要的六个字段）。
     九职业条从"每个都跳计算器"改成"点谁就看谁的树"：先让人看见真结构，再给一个明确的入口。
     格子本身是链接，点下去进计算器并把那个天赋描边高亮。 */
  var PV = { c: 'hunter', t: 0, data: null, classes: [] };
  var PV_CHG = { added: '新增', modified: '改动', moved: '换层或换系', unchanged: '未变', removed: '已移除' };

  function pvNode(cid, ti, nd) {
    var stTxt = nd[5] ? (PV_CHG[nd[5]] || '') : '';
    var label = nd[2] + '，上限 ' + (nd[4] === null || nd[4] === undefined ? '未核实' : nd[4] + ' 层') +
      (stTxt ? '；与经典旧世相比：' + stTxt : '；没有对照结果');
    return '<a class="pnode' + (nd[5] ? ' chg-' + D.esc(nd[5]) : '') + '" href="talent.html?c=' +
      encodeURIComponent(cid) + '&tree=' + ti + '&q=' + encodeURIComponent(nd[2]) +
      '" title="' + D.esc(label) + '" aria-label="' + D.esc(label) + '">' +
      '<span class="ico-wrap">' + (window.Glyph ? Glyph.talentTile(cid + '-' + ti + '-' + nd[0] + '-' + nd[1], nd[2]) : '') +
      (nd[3] ? '<img class="ico" src="img/icons/' + encodeURIComponent(nd[3]) + '.jpg" alt="" loading="lazy" ' +
        'onerror="this.className=\'ico bad\'">' : '') + '</span></a>';
  }
  function pvGrid() {
    var cls = (PV.data && PV.data.classes) ? PV.data.classes[PV.c] : null;
    if (!cls || !cls.trees.length) return '<div class="empty">这个职业的结构还没收录。</div>';
    var t = cls.trees[PV.t] || cls.trees[0];
    var rows = 0, byPos = {};
    t.nodes.forEach(function (n) {
      byPos[n[0] + '-' + n[1]] = n;
      if (n[0] > rows) rows = n[0];
    });
    var out = '';
    for (var r = 0; r <= rows; r++) {
      for (var c = 0; c < 4; c++) {
        var n = byPos[r + '-' + c];
        out += n ? pvNode(PV.c, PV.t, n) : '<span class="pempty"></span>';
      }
    }
    return '<div class="pv">' + out + '</div>';
  }
  function pvCounts() {
    var cls = PV.data.classes[PV.c], t = (cls.trees[PV.t] || cls.trees[0]), cnt = {};
    t.nodes.forEach(function (n) { cnt[n[5] || 'none'] = (cnt[n[5] || 'none'] || 0) + 1; });
    return ['added', 'modified', 'moved', 'unchanged'].filter(function (k) { return cnt[k]; })
      .map(function (k) { return '<span><i class="dot chg-' + k + '"></i>' + PV_CHG[k] + ' <b class="mono">' + cnt[k] + '</b></span>'; }).join('') +
      (cnt.none ? '<span><i class="dot"></i>没有对照结果 <b class="mono">' + cnt.none + '</b></span>' : '');
  }
  function treeCard() {
    var cls = PV.data && PV.data.classes ? PV.data.classes[PV.c] : null;
    var cnOf = {};
    PV.classes.forEach(function (c) { cnOf[c.id] = c.cn; });
    if (!cls) return '<div class="empty">天赋预览数据没加载出来。</div>';
    return '<div class="pvpicks">' + cls.trees.map(function (tr, i) {
      return '<button type="button" class="pick' + (i === PV.t ? ' on' : '') + '" data-pvt="' + i + '"' +
        ' aria-pressed="' + (i === PV.t ? 'true' : 'false') + '"><b>' + D.esc(tr.n) + '</b>' +
        '<span class="dim mono">' + tr.nodes.length + '</span></button>';
    }).join('') + '</div>' +
      '<div class="treewrap"><div class="treeleft">' + pvGrid() +
      '<div class="pvmeta">' + pvCounts() + '</div></div>' +
      '<aside class="tright"><div class="strip">' + PV.classes.map(function (c) {
        return '<button type="button" class="stripc' + (c.id === PV.c ? ' on' : '') + '" data-pvc="' + D.esc(c.id) + '"' +
          ' aria-pressed="' + (c.id === PV.c ? 'true' : 'false') + '">' +
          (window.Glyph ? Glyph.classTile(c.id, c.cn, c.iconKey) : '') +
          '<b>' + D.esc(c.cn) + '</b><span class="dim mono">' + (c.talentCount || 0) + ' 天赋</span></button>';
      }).join('') + '</div>' +
      '<p class="note">树的结构、每层上限与前置都来自客户端解包（第三方资料站转述），格子位置就是游戏里的位置；' +
      '层级点数门槛按 5 / 10 / 15 / 20 / 25 / 30 摆，未在游戏内核实。' +
      '角标是与经典旧世对照的结果，没角标 = 没有对照结果，不代表没变。</p>' +
      '<a class="cta" href="talent.html?c=' + encodeURIComponent(PV.c) + '&tree=' + PV.t + '">打开' +
      D.esc(cnOf[PV.c] || PV.c) + ' · ' + D.esc((cls.trees[PV.t] || {}).n || '') +
      ' 的完整计算器（能加点、能存方案）→</a></aside></div>';
  }
  function bindPreview() {
    var card = el('treecard');
    if (!card || !PV.data) return;
    var paint = function () { card.innerHTML = treeCard(); bindPreview(); };
    Array.prototype.forEach.call(card.querySelectorAll('[data-pvt]'), function (b) {
      b.onclick = function () { PV.t = +b.dataset.pvt; paint(); };
    });
    Array.prototype.forEach.call(card.querySelectorAll('[data-pvc]'), function (b) {
      b.onclick = function () { PV.c = b.dataset.pvc; PV.t = 0; paint(); };
    });
  }

  /* ---------- 首页 ---------- */
  // 时间表里有"待定""择期"这类没有具体日期的条目，排序时让真日期排前面，别顶掉首屏
  function byDate(a, b) {
    var ra = /^\d{4}-\d{2}-\d{2}$/.test(a.date || ''), rb = /^\d{4}-\d{2}-\d{2}$/.test(b.date || '');
    if (ra && rb) return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
    if (ra !== rb) return ra ? -1 : 1;
    return 0;
  }
  var NOT_DOING = [
    ['DPS 与强度排行', '个人主体 + 零 UGC 的类目下不做排行；而且无限服的战斗数据我们没实测过。'],
    ['宏与循环提示', '属攻略性质，本站红线不写打法。'],
    ['掉落概率', '资料里只有"谁掉什么"，没有百分比；官方说过无限服重做过掉落。'],
    ['角色查询 / 战斗日志', '要登录态与个人数据，类目与合规都不允许。'],
    ['新闻流与评论区', '只做资料与工具，不做内容 feed，也不开 UGC。']
  ];
  function home() {
    Promise.all([
      D.load('data/classes.json'), D.load('data/glossary.json'), D.load('data/dungeons.json'),
      D.load('data/meta.json'), D.load('data/scale.json'), D.load('data/timeline.json'),
      D.load('data/releases.json').catch(function () { return { items: [] }; }),      D.load('data/talent-preview.json').catch(function () { return { classes: {} }; }),
      D.load('data/art.json').catch(function () { return {}; })
    ]).then(function (r) {
      var classes = r[0].classes, gl = r[1].items, meta = r[3], S = r[4].scale, tl = r[5].items || [];
      var cl = (r[6] || {}).items || [];
      PV.data = r[7] || { classes: {} }; PV.classes = classes;
      // 默认看 classes.json 里的第一个职业：两栈必须同一个起点，否则对拍会差在选中态
      if (classes.length) PV.c = classes[0].id;
      var rankTop = (S.classRank || []).slice(0, 3);
      // 首页的覆盖率用 build-data 算出来的全站口径（含天赋节点与世界线），
      // 页脚那条"不含天赋节点"是另一个口径，两边都写明各自范围，别让数字看着互相打脸。
      var cov = { L0: S.coverage.L0, L1: S.coverage.L1, L2: S.coverage.L2, L3: S.coverage.L3, total: S.coverageTotal };
      var left = launchLeft();
      var recent = tl.slice().sort(byDate).slice(0, 3);

      function mod(m) {
        return '<a class="mod" href="' + m.href + '"><h2>' + m.t + '</h2>' +
          '<p class="dim">' + m.p + '</p>' +
          '<div class="modn">' + m.n.map(function (x) {
            return '<span><b class="mono">' + x[0] + '</b>' + x[1] + '</span>';
          }).join('') + '</div>' +
          '<div class="modf">' + D.pill(m.lv) + '<span class="dim">' + m.note + '</span></div></a>';
      }
      var MODS = [
        { href: 'talent.html', t: '全职业天赋模拟器', lv: 'L2',
          p: '九棵树都是 7 行 × 4 列的客户端真实结构，层级门槛 5 / 10 / 15 / 20 / 25 / 30，能加点、能存链接、能和经典旧世逐格对照。',
          n: [[S.classes, '职业'], [S.talentNodes, '天赋节点'], [S.talentVerified, '名与官网一致']],
          note: '结构与译名来自客户端解包，未经游戏内核实' },
        { href: 'world.html', t: '区域与稀有精英', lv: 'L0',
          p: '每个区域多少级、什么阵营、哪只稀有在哪个坐标、掉了什么；书在哪个容器也标了。',
          n: [[S.zones, '区域'], [S.rares, '已定位稀有'], [S.books, '本书有坐标']],
          note: '刷新计时游戏里没有这个数据，不猜' },
        { href: 'dungeons.html', t: '副本手册', lv: 'L2',
          p: '按十级一档排的 38 座本：首领名单、谁掉什么、等级区间两说的地方两个都留着。',
          n: [[S.dungeons, '座'], [S.bosses, '个首领'], [S.drops, '条掉落归属']],
          note: '掉落不写百分比' },
        { href: 'professions.html', t: '专业与配方', lv: 'L0',
          p: '13 个专业的配方、材料数量、技能橙黄绿灰四档与采集点，能按"我的技能等级"筛。',
          n: [[S.professions, '个专业'], [S.recipes, '条配方'], [S.gatherNodes, '个采集点']],
          note: '冲级路线与性价比建议属攻略，不做' },
        { href: 'races.html', t: '种族与职业组合', lv: 'L0',
          p: '国服官方中文公告里的 10 个种族行与可选职业矩阵，40 条种族特长带官方整句。',
          n: [[S.races, '个种族行'], [S.traits, '条特长整句'], [S.classes, '职业可选']],
          note: '整句直接抄官方，不改写' },
        { href: 'glossary.html', t: '中英术语速查', lv: 'L0',
          p: '技能与天赋的中英对照，按职业与种族分组，点一下即复制；38 条带与经典旧世的四态差异。',
          n: [[S.glossary, '条词条'], [S.abilities, '条四态对照'], [S.classes, '组职业']],
          note: '只有官方英文的算 L1，不冒充已核' }
      ];

      set('<section class="card hero"><div class="herot">' +
        '<h1 class="pt">《魔兽世界：无限》中文资料站</h1>' +
        '<p class="dim">天赋、区域与稀有、副本掉落、专业配方、种族组合、中英术语——' +
        '每条数据都挂着来源与核对状态，没核实的地方直接写「待实测」，不编也不机翻。</p>' +
        '<div class="gsearch" role="search">' +
        '<input type="search" id="gs" autocomplete="off" aria-controls="gres" aria-expanded="false" ' +
        'aria-label="全站搜索：天赋、改动、术语、副本、区域、配方、种族" ' +
        'placeholder="搜天赋、副本、区域、配方、种族特长（共 ' + S.search + ' 条）">' +
        '<p class="gsex">' + [['潜行', '同一个词在改动清单和配方里都有'], ['领主大厅', '副本名'],
          ['咆鼻', '稀有精英'], ['舒适的睡袋', '世界页的营点']].map(function (x) {
            return '<button type="button" class="gsx" data-s="' + D.esc(x[0]) + '" title="' + D.esc(x[1]) + '">' +
              x[0] + '</button>';
          }).join('') + '<span class="dim">只搜名称与归属，不搜攻略说法，也不搜别人站的正文。</span></p>' +
        '<div class="gres" id="gres" hidden></div></div>' +
        D.covBar(cov) +
        '<div class="covnum">' +
        ['L0', 'L1', 'L2', 'L3'].map(function (k) {
          return '<span class="pill ' + k + '">' + D.pillName(k) + ' <b>' + (cov[k] || 0) + '</b></span>';
        }).join('') + '<span class="dim mono">全站 ' + cov.total + ' 条（含天赋节点）</span></div>' +
        '<p class="note">数据基线：' + D.esc(meta.dataBaseline.build) + '，核对于 ' +
        D.esc(meta.dataBaseline.checkedAt) + '；本站统计 ' + D.esc(r[4].meta.generatedAt) +
        '。本站基于测试服资料整理，正式服上线后需整体重核。</p></div>' +
        '<aside class="heros"><div class="cd"><div class="cdrow"><b class="mono" id="cdD">' + left.d +
        '</b><span>天</span><i class="mono" id="cdT">' + pad2(left.h) + ':' + pad2(left.m) + ':' +
        pad2(left.s) + '</i></div>' +
        '<p class="dim">到正式服上线（' + LAUNCH.slice(0, 10) + '）· 差秒按本地时钟走</p>' +
        '<a class="cta" href="chooser.html">不知道选哪个职业？做 7 题玩法问答 →</a>' +
        '<span class="dim">问答是本站整理的玩法取向，不是强度排行。</span></aside></section>' +
        '<section class="card" id="treecard"><h2>挑一个职业，先看一棵真树</h2>' +
        '<p class="dim">格子就是客户端里的天赋本身，位置、每层上限、与经典旧世的差异都按真结构摆；' +
        '这里只能看，点格子进计算器并高亮那一格。</p>' + treeCard() + '</section>' +
        '<div class="chipsrow"><span class="dim">还要去哪：</span>' +
        [['updates.html', '最新动态'], ['rank.html', '资料完整度排行'], ['timeline.html', '上线时间表'],
          ['provenance.html', '溯源与覆盖率'], ['systems.html', '系统规则'], ['skills.html', '技能书'],
          ['dungeons.html#todo', '还没有数据的']].map(function (x) {
            return '<a href="' + x[0] + '">' + x[1] + ' →</a>';
          }).join('') + '</div>' +
        '<div class="modgrid">' + MODS.map(mod).join('') + '</div>' +
        '<div class="grid g2">' +
        '<div class="card"><h2>最新动态</h2>' +
        '<p class="note">三件事分开说：官方公告里的时间点、客户端解包出的职业改动条数、本站自己改了什么。' +
        '不做新闻转载与评价；这一页只在网页有，小程序按红线不做动态与排行。</p>' +
        '<h3>官方公告里的时间点</h3>' +
        recent.slice(0, 3).map(function (x) {
          return '<div class="flowrow"><b class="mono">' + D.esc(x.date) + '</b>' +
            '<div><b>' + D.esc(x.title) + '</b> ' + D.pill(x.level) +
            '<p class="dim">' + D.esc(x.what) + '</p></div></div>';
        }).join('') +
        '<h3>客户端改动清单</h3>' +
        '<div class="chgl">' +
        '<span><b class="mono">' + S.changes + '</b>条已入库</span>' +
        '<span><b class="mono">' + S.changesNew + '</b>个新增天赋</span>' +
        '<span><b class="mono">' + S.changesRemoved + '</b>个移除天赋</span>' +
        '<span><b class="mono">' + (S.changes - S.changesNew - S.changesRemoved) + '</b>条是改动或移位</span>' +
        '</div><p class="note">清单只列名称与改动类别，前后对照的句子本站不复制。</p>' +
        '<h3>资料完整度前三</h3><div class="chgl">' + rankTop.map(function (x, i) {
          var nm = (classes.filter(function (c) { return c.id === x.classId; })[0] || {}).cn || x.classId;
          return '<span><b class="mono">' + x.place + '</b>' + D.esc(nm) + ' · ' + x.official + ' 条有官方中文</span>';
        }).join('') + '</div>' +
        (cl.length ? '<h3>本站最近改了什么</h3>' + cl.slice(0, 3).map(function (e) {
          return '<div class="flowrow"><b class="mono">' + D.esc(e.date) + '</b>' +
            '<div><b>' + D.esc(e.title) + '</b></div></div>';
        }).join('') : '') +
        '<a class="cta" href="updates.html">全部动态（' + S.timeline + ' 个时间点 · ' + S.changes +
        ' 条改动 · ' + cl.length + ' 条本站更新）→</a>' +
        '<a class="cta" href="rank.html">资料完整度排行全表 →</a></div>' +
        '<div class="card"><h2>这一站刻意不做的</h2>' +
        '<p class="note">不是漏了，是决定不做。理由逐条写在这。</p>' +
        NOT_DOING.map(function (x) {
          return '<div class="flowrow"><b>' + D.esc(x[0]) + '</b><span class="dim">' + D.esc(x[1]) + '</span></div>';
        }).join('') + '</div></div>');
      bindSearch();
      bindPreview();
      tickCountdown();
    }).catch(fail);
  }

  /* ---------- 天赋计算器 ---------- */
  var tstate = { classId: 'hunter', file: null, state: {}, mode: 'add', active: 0, q: '' };

  function talent() {
    var q = new URLSearchParams(location.search);
    tstate.classId = q.get('c') || 'hunter';
    tstate.q = q.get('q') || '';
    // 首页预览点格子跳进来时带着是哪一系（移动端只显示当前那一系）
    var tt = parseInt(q.get('tree'), 10);
    if (tt >= 0 && tt < 3) tstate.active = tt;
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
    if (!ids.length) return '<p class="dim">这些条目没有可对照的官方文本。</p>';
    return '<h3>与经典旧世逐条对照 · ' + ids.length + ' 条</h3><p class="note">' + CMP_TIP +
      '，只列官方原文里写了差异的条目；措辞照录，本站不改写。</p>' +
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
      '<input type="search" id="tq" class="tqs" placeholder="搜天赋名" value="' + D.esc(tstate.q) + '">' +
      '<button class="ghost" id="cmp" aria-pressed="false">与经典旧世对比</button>' +
      '<span class="dim mono" id="sel"></span></div>' +
      '<div class="tlegend"><span><i class="lg added"></i>新增</span><span><i class="lg modified"></i>改动</span>' +
      '<span><i class="lg moved"></i>换层</span><span><i class="lg unchanged"></i>未变</span>' +
      '<span class="dim">标记来自客户端解包与经典旧世的对照；没标记 = 这一条没有对照结果</span></div>' +
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
    // 带着词跳进来时立刻描一遍，落地就能看到高亮的是哪个格子
    if (q && q.value) q.oninput();
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
      var f = { c: '', k: '', q: urlQ('q') };
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
        '<div class="field"><input type="search" id="q" placeholder="搜中文或英文" value="' + D.esc(f.q) + '">' +
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
    else if (!(x.drops || []).length) g.push('掉落归属：公开数据库里还没有它的首领掉落');
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
    ['PvP', '无限服的 PvP 规则、战场与积分官方还没给中文稿；且强度排行是本站红线，不做。'],
    ['坐骑', '只有第三方"新物品"清单的线索，没有官方中文名与原文整句。'],
    ['套装', '套装件数与效果在官方中文稿里还没出现，硬写等于编造。'],
    ['隐藏内容', '属攻略性质，本站红线不做攻略正文与机制清单。']
  ];
  function dunStateText(x) {
    var p = x.provenance || [];
    var off = p.some(function (s) { return (s.type || '').indexOf('official') === 0; });
    if (off || x.level !== 'L0') return DUN_STATE[x.level] || '';
    return '客户端解包名单 · 未实测';
  }
  function dunLoot(x) {
    var bosses = x.bosses || [], drops = x.drops || [];
    if (!bosses.length) return '<p class="dim">客户端解包还没给出这座本的首领名单——无限新增副本里这种的掉落表也还没有可信来源，不猜。</p>';
    return '<ul class="bosslist">' + bosses.map(function (b) {
      var mine = drops.filter(function (y) { return y.bossId === b.id; });
      return '<li><div class="bh"><b>' + D.esc(b.nameCn) + '</b>' +
        (mine.length ? '<span class="dim">' + mine.length + ' 件掉落</span>' : '<span class="dim">掉落待补</span>') + '</div>' +
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
            '<span>' + ((x.drops || []).length ? (x.drops || []).length + ' 件掉落' : '掉落待补') + '</span>' +
            '<span class="dim">' + dunStateText(x) + (x.nameCn ? '' : '；中文定名未公布') + '</span></div>' +
            (x.levelRangeAlt ? '<div class="conf">等级区间两说：本站取「' + D.esc(x.levelRange) +
              '」（官方公告），另一份资料写「' + D.esc(x.levelRangeAlt) + '」，待定稿</div>' : '') +
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
          '名单与等级区间取自客户端解包（由第三方资料站转述）；掉落是按经典旧世公开数据库推出来的，一律标待实测。</p></div>' +
        '<div class="banner">掉落数据本站<b>不写百分比</b>：这里只回答"谁掉了什么"，不回答"多大概率"。暴雪说过无限服重做过掉落，正式开放可能变化。</div>' +
        body +
        '<div class="card" id="todo"><h2>「世界」里还没有数据的</h2>' +
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
      // 从首页搜索跳进来：替用户点开那座本的速览并滚到它，不靠人自己在一堆卡片里找
      var dd = urlQ('d');
      if (dd) {
        var target = null;
        Array.prototype.forEach.call(document.querySelectorAll('[data-d]'), function (b) {
          if (!target && b.dataset.d === dd) target = b;
        });
        if (target) {
          target.click();
          var card = target.parentNode;
          if (card && card.scrollIntoView) card.scrollIntoView({ block: 'center' });
        }
      }
    }).catch(fail);
  }

  /* ---------- 术语速查 ---------- */
  function glossary() {
    Promise.all([D.load('data/glossary.json'), D.load('data/races.json'),
      D.load('data/classes.json'), D.load('data/icons.json')]).then(function (r) {
      var items = r[0].items, RACE = raceLookup(r[1].races), classes = r[2].classes;
      var ICONS = (r[3] || {}).map || {};
      var KIND = { talent: '天赋/技能', item: '装备', racial: '种族特长' };
      var f = { q: urlQ('q'), race: '', kind: '' };
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
        '官方未公布的英文原名一律留空，所以有「待补」。</p>' +
        '<p class="note">按职业与种族分组。字母块是自绘占位，代表这一条没有可信图标来源。</p>' +
        '<div class="field"><input type="search" id="q" placeholder="输入中文或英文" value="' + D.esc(f.q) + '">' +
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
    Promise.all([D.load('data/meta.json'), D.load('data/method.json'), D.load('data/scale.json')])
      .then(function (r) {
        var sc = r[2].scale;
        // covBar 按 total 算四段宽度，scale.json 里的分级不带 total，这里显式补上
        var cov = { L0: sc.pubCoverage.L0, L1: sc.pubCoverage.L1, L2: sc.pubCoverage.L2,
          L3: sc.pubCoverage.L3, total: sc.pubTotal };
        var m = r[1] || {};
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
        var ti = r[0].talentImport;
        set('<div class="card"><h1 class="pt">溯源与覆盖率</h1><p class="dim">每条数据从哪来、什么时候核的、哪些刻意没拿，全部摊在这里。</p></div>' +
          '<div class="card"><h2>数据覆盖率</h2><p class="note">这条与页脚同一个数：' + sc.pubTotal +
          ' 条对外词条（术语 + 副本 + 世界线），不含天赋。首页那条是全站统计 ' + sc.coverageTotal +
          ' 条，多出来的 ' + (sc.coverageTotal - sc.pubTotal) + ' 条是九棵天赋树的节点。</p>' + D.covBar(cov) +
          '<div class="stats">' + Object.keys(names).map(function (k) {
            return '<div class="stat"><b>' + cov[k] + '</b>' + names[k] + '</div>';
          }).join('') + '</div>' +
          '<p class="dim">判定标准：一条数据只有挂着官方来源且人工核过，才算已核实；粉丝站与转载最高只算待实测。</p></div>' +
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
          (r[0].openQuestions || []).map(function (q) { return '<li>' + D.esc(q) + '</li>'; }).join('') + '</ol></div>' +
          '<div class="card"><h2>来源站点与用法边界</h2><table><thead><tr><th>站点</th><th>能给什么</th><th>怎么用</th></tr></thead><tbody>' +
          refs.map(function (x) { return '<tr><td class="mono">' + x[0] + '</td><td>' + x[1] + '</td><td>' + x[2] + '</td></tr>'; }).join('') +
          '</tbody></table></div>' +
          '<div class="card"><h2>发布前的检查规则</h2><ul>' +
          (r[0].rules || []).map(function (x) { return '<li>' + D.esc(x) + '</li>'; }).join('') + '</ul></div>');
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
      set('<div class="card"><h1 class="pt">系统与新区域</h1><p class="dim">规则、区域、种族与装备名的官方中文说法，逐条带来源。</p></div>' +
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
    Promise.all([D.load('data/races.json'), D.load('data/classes.json'), D.load('data/glossary.json'),
      D.load('data/art.json').catch(function () { return {}; })])
      .then(function (r) {
        var R = r[0], classes = r[1].classes, gloss = r[2].items, ART = r[3] || {};
        var CNAME = {}, CTILE = {};
        classes.forEach(function (c) { CNAME[c.id] = c.cn; CTILE[c.id] = c.iconKey || null; });
        var POR = ART.races || {}, EMB = ART.factions || {}, CITY = ART.factionCities || {};
        var FAC = { horde: '部落', alliance: '联盟' };
        var cols = (R.classOrder || []).filter(function (id) { return CNAME[id]; });
        var traits = [];
        R.races.forEach(function (x) {
          var list = x.subgroup ? x.subgroup.traits : x.traits;
          var owner = x.subgroup ? x.subgroup.nameCn : x.nameCn;
          (list || []).forEach(function (t) { traits.push({ race: x, owner: owner, t: t }); });
        });
        var inGloss = gloss.filter(function (i) { return i.kind === 'racial' && i.raceId; }).length;
        // 深链 #race=horde-orc：阵营 + 种族 id，两边命名对不上时以阵营前缀为准
        function keyOf(x) { return x.faction + '-' + x.id; }
        var byKey = {};
        R.races.forEach(function (x) { byKey[keyOf(x)] = x; });
        var m0 = /#race=([\w-]+)/.exec(location.hash || '');
        var rq = urlQ('r');
        var f = { c: '', q: urlQ('q'), all: false,
          sel: byKey[rq] ? rq : ((m0 && byKey[m0[1]]) ? m0[1] : keyOf(R.races[0])) };

        function srcBtn(id, name, prov) {
          return '<button class="info" data-src="' + D.esc(id) + '" data-name="' + D.esc(name) +
            '" data-prov="' + encodeURIComponent(JSON.stringify(prov || [])) +
            '" aria-label="查看「' + D.esc(name) + '」的来源">来源</button>';
        }
        /* 头像：本地转存的客户端种族头像盖在自绘方块上；两边都没有就只留自绘块，不放假图 */
        function faceOf(x) {
          return x.id.indexOf('skyborne') === 0 ? (POR.skyborne || null) : (POR[x.id] || null);
        }
        function face(x, mod) {
          var art = faceOf(x);
          return '<span class="rface' + (mod ? ' ' + mod : '') + '">' +
            Glyph.raceTile(x.id, x.faction, x.nameCn, x.iconKey) +
            (art ? '<img class="rface-art" src="' + D.esc(art) + '" alt="" loading="lazy" decoding="async" ' +
              'onerror="this.className=\'rface-art bad\'">' : '') + '</span>';
        }
        function raceName(x) {
          return D.esc(x.subgroup ? x.subgroup.nameCn : x.nameCn);
        }
        function traitListOf(x) { return (x.subgroup ? x.subgroup.traits : x.traits) || []; }

        function band(fac) {
          var rows = R.races.filter(function (x) { return x.faction === fac; });
          var n = rows.reduce(function (a, x) { return a + traitListOf(x).length; }, 0);
          return '<div class="facband ' + fac + '">' +
            // 阵营城市原画压暗当氛围底；取不到就整个不渲染，纯色带照常显示
            (CITY[fac] ? '<div class="fembg"><img src="' + D.esc(CITY[fac]) + '" alt="" loading="lazy" ' +
              'onerror="this.parentNode.className=\'fembg bad\'"></div>' +
              '<span class="artmark">客户端原画 · 本地转存</span>' : '') +
            '<div class="fhead">' +
            (EMB[fac] ? '<img class="femb" src="' + D.esc(EMB[fac]) + '" alt="" loading="lazy" ' +
              'onerror="this.className=\'femb bad\'">' : '') +
            '<b>' + FAC[fac] + '</b><span class="dim">' + rows.length + ' 个种族行 · ' + n +
            ' 条种族特长</span>' +
            '<span class="dim mono">' + (fac === 'alliance' ? '人类 / 矮人 / 暗夜精灵 / 侏儒 / 天裔（高阶会）'
              : '兽人 / 亡灵 / 牛头人 / 巨魔 / 天裔（塑风者）') + '</span></div>' +
            '<div class="racegrid">' + rows.map(function (x) {
              var on = f.sel === keyOf(x);
              return '<button type="button" class="racecard' + (on ? ' on' : '') + '" data-race="' + keyOf(x) +
                '" aria-pressed="' + (on ? 'true' : 'false') + '">' + face(x) +
                '<span class="rcn">' + raceName(x) + '</span>' +
                (x.id.indexOf('skyborne') === 0 ? '<span class="tag new">无限新增</span>' : '') +
                '<span class="dim mono">' + x.classes.length + ' 职业 · ' + traitListOf(x).length + ' 特长</span>' +
                D.pill(x.level) +
                (faceOf(x) ? '' : '<span class="dim rcnote">没有可信头像，用自绘块</span>') +
                '</button>';
            }).join('') + '</div></div>';
        }

        function detail() {
          var x = byKey[f.sel];
          if (!x) return '<div class="empty">选一个种族看它的特长。</div>';
          var tl = traitListOf(x);
          var cf = (R.conflicts || []).filter(function (c) { return x.id.indexOf('skyborne') === 0; });
          return '<div class="rdhead">' + face(x, 'lg') +
            '<div class="rdt"><h2>' + raceName(x) +
            (x.id.indexOf('skyborne') === 0 ? ' <span class="tag new">无限新增</span>' : '') + '</h2>' +
            '<p class="dim">' + FAC[x.faction] + ' · 可选 ' + x.classes.length + ' 个职业 · ' + tl.length +
            ' 条种族特长' + (x.nameEn ? ' · <span class="mono">' + D.esc(x.nameEn) + '</span>' : ' · 官方未公布英文原名') + '</p>' +
            '<div class="rdacts">' + D.pill(x.level) + srcBtn('rc-' + x.id, raceName(x), x.provenance) +
            '<button type="button" class="ghost mini" data-jump="traits">这族的特长去哪找</button></div></div></div>' +
            '<p class="lore">' + (x.lore || D.esc(R.meta.loreMissingNote || '官方本页没有这个种族的简介段。')) + '</p>' +
            '<h3 class="rdh">可选职业</h3><div class="rdcls">' + cols.map(function (id) {
              var ok = x.classes.indexOf(id) >= 0;
              return '<span class="rdcl' + (ok ? '' : ' off') + '" title="' + D.esc(CNAME[id]) + (ok ? '可选' : '不可选') + '">' +
                (window.Glyph ? Glyph.classTile(id, CNAME[id], CTILE[id], 'sm') : '') +
                '<i>' + D.esc(CNAME[id]) + '</i></span>';
            }).join('') + '</div>' +
            '<h3 class="rdh">种族特长（官方整句原样引用）</h3>' +
            (tl.length ? '<ul class="rdtr">' + tl.map(function (t) {
              return '<li>' + iconCell(t.iconKey, x.id + t.name, t.name) +
                '<div class="rdtr-b"><b>' + D.esc(t.name) + '</b>' +
                '<span class="tag">' + (t.passive ? '被动' : '主动') + '</span>' +
                '<p class="quote">' + D.esc(t.quote) + '</p></div>' +
                srcBtn('dt-' + x.id + '-' + t.name, t.name, [{ type: 'official_cn', url: R.meta.sources[0].url,
                  quote: t.quote, note: '官方种族公告·该特长列在「' + raceName(x) + '」小标题下',
                  checkedAt: x.provenance[0].checkedAt }]) + '</li>';
            }).join('') + '</ul>' : '<p class="dim">官方公告里这个小标题下没有列出可用的特长条目。</p>') +
            (cf.length ? '<p class="conf">这个种族有' + cf.length + '处两种说法并存，见下方「同一页里两种说法并存」——两个都留着，不替玩家选。</p>' : '');
        }

        function matrix() {
          var rows = R.races.filter(function (x) { return !f.fac || x.faction === f.fac; });
          return '<table class="mtx"><thead><tr><th class="rh">种族 \\ 职业</th>' +
            cols.map(function (id) {
              return '<th><button type="button" class="ch' + (f.c === id ? ' on' : '') + '" data-cl="' + id +
                '" aria-pressed="' + (f.c === id ? 'true' : 'false') + '">' +
                (window.Glyph ? Glyph.classTile(id, CNAME[id], CTILE[id], 'sm') : '') +
                '<span>' + D.esc(CNAME[id]) + '</span></button></th>';
            }).join('') + '</tr></thead><tbody>' +
            rows.map(function (x) {
              var hit = f.c && x.classes.indexOf(f.c) < 0;
              return '<tr' + (hit ? ' class="off"' : '') + ' data-race="' + keyOf(x) + '"><th class="rh">' +
                face(x, 'sm') + '<span>' + D.esc(x.nameCn) +
                (x.subgroup ? '<em>' + D.esc(x.subgroup.nameCn.replace(x.nameCn, '')) + '</em>' : '') +
                '</span></th>' +
                cols.map(function (id) {
                  var ok = x.classes.indexOf(id) >= 0;
                  return '<td class="' + (ok ? 'y' : 'n') + '">' + (ok ? '✓' : '—') + '</td>';
                }).join('') + '</tr>';
            }).join('') + '</tbody></table>';
        }
        function traitTable() {
          var q = f.q.toLowerCase();
          if (!q && !f.c && !f.fac && !f.all) {
            return '<p class="dim">上面点任意种族就能看到它的全部特长与官方整句；' +
              '要跨种族搜词（比如"潜行""亡灵"），在上面的框里输入。' +
              '<button type="button" class="ghost mini" data-act="all">还是要一次看全 ' + traits.length +
              ' 条</button></p>';
          }
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
            return '<div class="lgrp">' + face(x, 'sm') + '<b>' + raceName(x) + '</b>' +
              '<span class="dim mono">' + FAC[x.faction] + '</span><span class="dim">' + g.rows.length + ' 条</span>' +
              '<button type="button" class="ghost mini" data-race="' + keyOf(x) + '">看这个种族</button></div>' +
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
          el('facbands').innerHTML = band('alliance') + band('horde');
          el('rdet').innerHTML = detail();
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
          // 点头像卡、点"看这个种族"都能换详情；矩阵行只负责读，不做点击（行里已有按钮，嵌套点击会打架）
          Array.prototype.forEach.call(document.querySelectorAll('.racecard[data-race], .lgrp [data-race]'), function (b) {
            b.onclick = function () {
              f.sel = b.dataset.race;
              if (history.replaceState) history.replaceState(null, '', '#race=' + f.sel);
              draw();
              var t = el('rdet');
              if (t && t.scrollIntoView) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
            };
          });
          Array.prototype.forEach.call(document.querySelectorAll('[data-jump]'), function (b) {
            b.onclick = function () {
              var t = el(b.dataset.jump);
              if (t && t.scrollIntoView) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
              var fq = el('fq');
              if (fq) { fq.value = raceName(byKey[f.sel]); f.q = fq.value; draw(); fq.focus(); }
            };
          });
          var ab = document.querySelector('[data-act=all]');
          if (ab) ab.onclick = function () { f.all = true; draw(); };
          el('tcnt').textContent = (f.q || f.c || f.fac || f.all)
            ? el('tt').querySelectorAll('tbody tr').length + ' / ' + traits.length + ' 条' : traits.length + ' 条';
          bindSrcToggles();
        }

        set('<div class="card"><h1 class="pt">种族与职业组合</h1>' +
          '<p class="dim">数据全部来自国服官方中文公告，逐条带原文。官方未公布的英文原名一律留空，不逐词硬造。' +
          '阵营是这一页的主线：左边联盟、右边部落，头像与徽标都是本地转存的客户端素材。</p>' +
          '<div class="stats">' +
          '<div class="stat"><b>' + R.races.length + '</b>种族行</div>' +
          '<div class="stat"><b>' + traits.length + '</b>条种族特长</div>' +
          '<div class="stat"><b>' + R.newCombos.length + '</b>组亮点组合</div>' +
          '<div class="stat"><b>' + inGloss + '</b>条已进速查</div>' +
          '<div class="stat"><b>' + Object.keys(POR).length + '</b>张本地头像</div></div>' +
          (R.skyborneNote && R.skyborneNote.text ? '<p class="dim"><span class="tag">官方原文</span>' +
            D.esc(R.skyborneNote.text) + '</p>' : '') + '</div>' +

          '<div class="facwrap" id="facbands"></div>' +
          '<div class="card rdetail" id="rdet"></div>' +

          '<div class="card"><h2>种族 × 职业矩阵</h2><p class="dim" id="mhint"></p>' +
          '<div class="field"><label class="dim">阵营</label><select id="ff"><option value="">全部</option>' +
          '<option value="horde">部落</option><option value="alliance">联盟</option></select>' +
          '<label class="dim">找特长</label><input type="search" id="fq" placeholder="名称或效果里的词" value="' + D.esc(f.q) + '">' +
          '<span class="dim mono" id="tcnt"></span></div>' +
          '<div class="scrollx" id="mx"></div></div>' +

          '<div class="card" id="traits"><h2>按词找特长</h2>' +
          '<p class="dim">官方页把每条特长写成一个句子，这里整句原样引用；数值只到官方写出的那一句，不做推算。</p>' +
          '<div class="scrollx" id="tt"></div>' +
          '<div class="srcbox" id="srcbox"></div></div>' +

          '<div class="card"><h2>新开放的组合</h2><p class="dim">官方原文那句：' +
          D.esc((R.newCombos[0] && R.newCombos[0].provenance[0].quote) || '') + '</p>' +
          '<div class="combos">' + R.newCombos.map(function (c) {
            var x = R.races.filter(function (y) {
              return (y.subgroup ? y.subgroup.nameCn : y.nameCn) === c.raceCn || y.nameCn === c.raceCn;
            })[0];
            return '<span class="combo">' + (x ? face(x, 'sm') : '') +
              '<b>' + D.esc(c.raceCn) + '</b>' +
              (window.Glyph ? Glyph.classTile(c.classId, c.classCn, CTILE[c.classId], 'sm') : '') +
              '<b>' + D.esc(c.classCn) + '</b>' +
              srcBtn('nc-' + c.label, c.label, c.provenance) + '</span>';
          }).join('') + '</div></div>' +

          (R.conflicts || []).map(function (cf) {
            return '<div class="card"><h2>同一页里两种说法并存</h2><p class="dim">' +
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
        draw();
      }).catch(fail);
  }


  /* ---------- 专业与配方 ---------- */
  function professions() {
    D.load('data/professions.json').then(function (doc) {
      var ps = doc.professions || [], sel = ps[0];
      var q = new URLSearchParams(location.search);
      var byId = {};
      ps.forEach(function (p) { byId[p.id] = p; });
      if (q.get('p') && byId[q.get('p')]) sel = byId[q.get('p')];
      var f = { q: q.get('q') || '', lv: '', onlyNew: false };

      function skillCell(sk) {
        if (!sk) return '<span class="dim">—</span>';
        var k = [['orange', '橙'], ['yellow', '黄'], ['green', '绿'], ['grey', '灰']];
        return '<span class="sk">' + k.map(function (x) {
          return sk[x[0]] === undefined ? '' :
            '<i class="sk-t sk-' + x[0] + '" title="' + x[1] + '色起点">' + x[1] + '<b>' + sk[x[0]] + '</b></i>';
        }).join('').replace(/<i class="sk-t sk-[a-z]+"[^>]*><\/i>/g, '') + '</span>';
      }
      function learnable(sk) {
        if (!sk || !f.lv) return true;
        return sk.orange <= f.lv;
      }
      function draw() {
        var kw = f.q.toLowerCase();
        var recipes = (sel.recipes || []).filter(function (x) {
          if (f.onlyNew && !x.isNew) return false;
          if (!learnable(x.skill)) return false;
          if (!kw) return true;
          return (x.nameCn || '').toLowerCase().indexOf(kw) >= 0 ||
            (x.mats || []).some(function (m) { return (m.nameCn || '').toLowerCase().indexOf(kw) >= 0; });
        });
        var nodes = (sel.nodes || []).filter(function (x) {
          return !kw || (x.nameCn || '').toLowerCase().indexOf(kw) >= 0 ||
            (x.yields || []).join(' ').toLowerCase().indexOf(kw) >= 0;
        });
        var head = '<div class="card"><h2>' + D.esc(sel.nameCn) +
          (sel.nameEn ? ' <span class="dim mono">' + D.esc(sel.nameEn) + '</span>' : '') +
          ' <span class="dim">' + (sel.kind === 'gather' ? '采集' : '制作') + '</span></h2>' +
          '<p class="note">' + D.esc(sel.levelNote || '') + '</p>' +
          '<div class="field"><input type="search" id="pq" placeholder="搜制成品或材料名" value="' + D.esc(f.q) + '">' +
          '<input type="number" id="plv" min="1" max="300" placeholder="我的技能 1–300" value="' + D.esc(f.lv) + '" class="lv">' +
          '<button type="button" class="pick tog' + (f.onlyNew ? ' on' : '') + '" id="pn" aria-pressed="' +
          (f.onlyNew ? 'true' : 'false') + '">只看无限新增</button>' +
          '<span class="dim mono" id="pcnt"></span></div></div>';
        var body = '';
        if (sel.unparsed) {
          body = '<div class="card"><div class="empty">' + D.esc(sel.note || '这一页目前只有叙述文字，还没拆出可列的条目。') +
            '</div></div>';
        }
        if (nodes.length) {
          body += '<div class="card"><h2>采集点 · ' + nodes.length + '</h2><div class="scrollx"><table class="entab">' +
            '<thead><tr><th class="ich">图标</th><th>' + (sel.id === 'herbalism' ? '草药点' : sel.id === 'fishing' ? '水域' : '采集点') +
            '</th><th>可得</th><th>最多区域</th><th>技能</th></tr></thead><tbody>' +
            nodes.map(function (n) {
              return '<tr><td class="ich">' + iconCell(n.iconKey, n.nameCn, n.nameCn) + '</td>' +
                '<td>' + D.hl(n.nameCn, f.q) + '</td>' +
                '<td class="dim">' + D.esc((n.yields || []).join('、')) + '</td>' +
                '<td class="dim">' + D.esc(n.zone || '—') + '</td>' +
                '<td>' + skillCell(n.skill) + '</td></tr>';
            }).join('') + '</tbody></table></div></div>';
        }
        if (recipes.length) {
          body += '<div class="card"><h2>配方 · ' + recipes.length + ' 条</h2>' +
            '<p class="note">技能四档是这条配方在什么点数变橙 / 黄 / 绿 / 灰；灰 = 技能超过它就不再涨点。' +
            '材料后面的 ×N 是单次制作消耗量。</p>' +
            '<div class="scrollx"><table class="entab"><thead><tr><th class="ich">制成品</th><th>材料</th><th>技能</th><th>来源</th></tr></thead><tbody>' +
            recipes.map(function (x) {
              return '<tr><td>' + iconCell(x.iconKey, x.itemId, x.nameCn, 1) +
                '<span class="q' + (x.quality || 0) + '">' + D.hl(x.nameCn, f.q) + '</span>' +
                (x.isNew ? '<span class="tag">新</span>' : '') +
                '<span class="dim mono"> #' + D.esc(x.itemId) + '</span></td>' +
                '<td class="mats">' + ((x.mats || []).length
                  ? x.mats.map(function (m) {
                    return '<span class="mat">' + iconCell(m.iconKey, m.nameCn, m.nameCn, 1) +
                      D.esc(m.nameCn) + '<b class="mono">×' + m.count + '</b></span>';
                  }).join('')
                  : '<span class="dim">无需材料</span>') + '</td>' +
                '<td>' + skillCell(x.skill) + '</td>' +
                '<td class="dim">' + D.esc(x.source || '—') + '</td></tr>';
            }).join('') + '</tbody></table></div></div>';
        }
        if (!nodes.length && !recipes.length && !sel.unparsed) {
          body += '<div class="card"><div class="empty">这个专业没有匹配条目，试试放宽搜索或技能等级。</div></div>';
        }
        el('pbody').innerHTML = head + body +
          '<div class="card"><h2>这一页没有的</h2><ul class="list">' +
          (doc.meta.notCollected || []).map(function (x) { return '<li>' + D.esc(x) + '</li>'; }).join('') +
          '</ul><h3>来源与核对</h3>' + D.sources(sel.provenance) + '</div>';
        el('pcnt').textContent = (recipes.length + nodes.length) + ' 条';
        var qi = el('pq');
        qi.oninput = function () { f.q = qi.value.trim(); draw(); };
        var li = el('plv');
        li.oninput = function () { f.lv = parseInt(li.value, 10) || ''; draw(); };
        var ni = el('pn');
        ni.onclick = function () { f.onlyNew = !f.onlyNew; draw(); };
      }

      set('<div class="card"><h1 class="pt">专业与配方</h1>' +
        '<p class="dim">配方、材料、数量与技能档位都取自无限客户端解包（第三方资料站转述），逐条能点开看来源。' +
        '不做冲级路线与性价比建议——那是攻略，本站红线不碰。</p>' +
        '<div class="stats" style="margin-top:12px">' +
        '<div class="stat"><b>' + ps.length + '</b>个专业</div>' +
        '<div class="stat"><b>' + ps.reduce(function (s, p) { return s + p.counts.recipes; }, 0) + '</b>条配方</div>' +
        '<div class="stat"><b>' + ps.reduce(function (s, p) { return s + p.counts.newRecipes; }, 0) + '</b>条无限新增</div>' +
        '<div class="stat"><b>' + ps.reduce(function (s, p) { return s + p.counts.nodes; }, 0) + '</b>个采集点</div></div>' +
        '<div class="picks">' + ps.map(function (p) {
          return '<button class="pick' + (p.id === sel.id ? ' on' : '') + '" data-p="' + D.esc(p.id) + '">' +
            '<b>' + D.esc(p.nameCn) + '</b><span class="dim mono">' +
            (p.counts.recipes || p.counts.nodes) + '</span></button>';
        }).join('') + '</div></div><div id="pbody"></div>');
      Array.prototype.forEach.call(document.querySelectorAll('[data-p]'), function (b) {
        b.onclick = function () {
          sel = byId[b.dataset.p];
          Array.prototype.forEach.call(document.querySelectorAll('[data-p]'), function (o) {
            o.classList.toggle('on', o === b);
          });
          draw();
        };
      });
      draw();
    }).catch(fail);
  }

  /* ---------- 世界：区域 / 稀有精英 / 图书馆书籍 / 睡袋 ---------- */
  var WTABS = [['zones', '区域'], ['rares', '稀有精英'], ['books', '图书馆书籍'], ['bag', '睡袋与营地']];
  function world() {
    Promise.all([D.load('data/world.json'), D.load('data/art.json').catch(function () { return {}; })])
      .then(function (rs) {
        var w = rs[0], f = { tab: 'zones', q: urlQ('q'), zone: '' };
        // 搜索结果带着板块跳进来（稀有、书、营地在不同板块里），板块名不认识就留在默认页
        var rt = urlQ('t');
        if (WTABS.some(function (t) { return t[0] === rt; })) f.tab = rt;
        var zByName = {};
        (w.zones || []).forEach(function (z) { zByName[z.nameCn] = z; });
        var newZones = (w.zones || []).filter(function (z) { return z.isNew; });
        var kw = function () { return f.q.trim().toLowerCase(); };
        var hit = function (x) {
          var k = kw();
          if (!k) return true;
          return ((x.nameCn || '') + ' ' + (x.nameEn || '') + ' ' + (x.zone || '') + ' ' +
            (x.zoneCn || '') + ' ' + (x.container || '')).toLowerCase().indexOf(k) >= 0;
        };
        function lvTxt(r) {
          var a = r.levelRange || [];
          var lo = a[0], hi = a[1];
          if (lo === undefined || lo === null) return r.levelStatus && r.levelStatus !== 'ok' ? D.esc(r.levelStatus) : '—';
          if (hi === undefined || hi === null || hi === lo) return lo + ' 级';
          return lo + '–' + hi + ' 级';
        }
        // 没给等级的区域排在最后，别当 0 级排到最前面
        function lvStart(z) {
          return z && z.levelRange && z.levelRange[0] !== null && z.levelRange[0] !== undefined ? z.levelRange[0] : 99;
        }
        function facTxt(x) {
          return x.faction ? D.esc(x.faction) : '<span class="dim">阵营未定</span>';
        }
        /* 小地图块：本地转存的区域图 + 数据里的百分比标记；标记位置在渲染后用 JS 写，
           因为那是数据不是样式，不该把坐标值硬编进 class。 */
        function mapBox(o, alt) {
          if (!o.mapFile) {
            return '<div class="zmap none"><span class="dim">这一张客户端没有切出小地图</span>' +
              (o.mapId ? '<b class="mono">地图编号 ' + D.esc(o.mapId) + '</b>' : '') + '</div>';
          }
          return '<div class="zmap"><img src="' + D.esc(o.mapFile) + '" alt="' + D.esc(alt) +
            '的区域小地图" loading="lazy" decoding="async" width="560" height="373" ' +
            'onerror="this.className=\'bad\'">' +
            (o.mark ? '<b class="zmark" data-x="' + o.mark.x + '" data-y="' + o.mark.y +
              '" aria-hidden="true"></b>' : '') +
            '<span class="dbn2-mark">客户端地图 · 本地转存</span></div>';
        }
        function coordTxt(o) {
          var s = [];
          if (o.mark) s.push('(' + o.mark.x + ', ' + o.mark.y + ')');
          if (o.world) s.push('世界 ' + o.world.x + ', ' + o.world.y);
          return '<span class="mono dim">' + (s.join(' · ') || '坐标未采') + '</span>';
        }
        function dropRow(d) {
          return '<span class="loot-i q' + (d.quality || 0) + '">' +
            iconCell(d.iconKey, d.itemId, d.nameCn, 1) + D.esc(d.nameCn) +
            (d.itemLevel ? '<span class="dim mono">iLvl ' + d.itemLevel + '</span>' : '') +
            (d.reqLevel ? '<span class="dim mono">需 ' + d.reqLevel + '</span>' : '') +
            '<span class="dim mono">#' + D.esc(d.itemId) + '</span></span>';
        }

        /* --- 面板一：区域 --- */
        function panelZones() {
          var zs = (w.zones || []).filter(hit), nz = newZones.filter(hit);
          var out = '';
          if (nz.length) {
            out += '<div class="band"><b>无限新增区域</b><span class="dim">客户端新加的，飞行路线多未定</span>' +
              '<span class="dim mono">' + nz.length + ' 个</span></div><div class="zgrid">' +
              nz.map(function (z) { return zoneCard(z, '新'); }).join('') + '</div>';
          }
          (w.continents || []).concat([{ id: 'new', nameCn: '单独成图的新区域' }]).forEach(function (c) {
            var rows = zs.filter(function (z) { return z.continent === c.id && !z.isNew; });
            if (!rows.length) return;
            out += '<div class="band"><b>' + D.esc(c.nameCn) + '</b>' +
              '<span class="dim">按进入等级排</span><span class="dim mono">' + rows.length + ' 个</span></div>' +
              '<div class="zgrid">' + rows.map(function (z) { return zoneCard(z, ''); }).join('') + '</div>';
          });
          if (!out) out = '<div class="card"><div class="empty">没有匹配的区域，换个名字试试。</div></div>';
          return out + '<div class="card"><h2>客户端里的地图清单</h2>' +
            '<p class="note">有 ' + ((w.meta.mapsWithoutImage || []).length) + ' 个区域没有对应的小地图（' +
            D.esc(((w.meta.mapsWithoutImage || []).slice(0, 4)).join('、')) + ' 等），' +
            '这些卡只显示地图编号与坐标，不放假图。</p>' +
            '<p class="note">48 张地图是解包出来的全量：' +
            (w.maps || []).filter(function (m) { return m.group === '大陆'; }).length + ' 张大陆、' +
            (w.maps || []).filter(function (m) { return m.isNew; }).length + ' 张无限新增、' +
            (w.maps || []).filter(function (m) { return m.group === '副本'; }).length + ' 张副本、' +
            (w.maps || []).filter(function (m) { return m.group === '战场'; }).length + ' 张战场。' +
            '本站不做可缩放交互地图——那套底图瓦片是别人自己切的，不搬；只把区域名、等级与坐标取过来。</p>' +
            '<div class="scrollx"><table class="entab"><thead><tr><th>地图</th><th>类型</th><th>地图编号</th>' +
            '<th>兴趣点</th><th>已切图</th></tr></thead><tbody>' +
            (w.maps || []).filter(function (m) { return m.isNew || m.group === '大陆'; })
              .map(function (m) {
                return '<tr><td>' + D.esc(m.nameCn) + (m.isNew ? '<span class="tag">新</span>' : '') + '</td>' +
                  '<td class="dim">' + D.esc(m.group || '—') + '</td>' +
                  '<td class="mono dim">' + D.esc(m.mapId) + '</td>' +
                  '<td class="mono">' + (m.placeCount === null ? '—' : m.placeCount) + '</td>' +
                  '<td class="mono">' + (m.painted || 0) + '</td></tr>';
              }).join('') + '</tbody></table></div></div>';
        }
        function zoneCard(z, seal) {
          return '<button type="button" class="zcard' + (z.rareCount || z.bookCount ? ' lk' : '') +
            '" data-zone="' + D.esc(z.nameCn) + '">' + mapBox(z, z.nameCn) +
            '<div class="zbody"><b>' + D.esc(z.nameCn) + '</b>' +
            (seal ? '<span class="tag new">' + seal + '</span>' : '') +
            '<span class="dim mono">' + lvTxt(z) + '</span>' +
            '<span class="dim">' + facTxt(z) + '</span>' +
            (z.flight ? '<span class="dim">' + (z.flight === 'no-route' ? '客户端里还没有飞行路线' : '有飞行路线，站点待实测') + '</span>' : '') +
            '<span class="zcnt">' + (z.rareCount ? z.rareCount + ' 个稀有' : '') +
            (z.rareCount && z.bookCount ? ' · ' : '') + (z.bookCount ? z.bookCount + ' 本书' : '') +
            (!z.rareCount && !z.bookCount ? '<i class="dim">这一版还没有数据</i>' : '') + '</span>' +
            '</div></button>';
        }

        /* --- 面板二：稀有精英 --- */
        function panelRares() {
          var rows = (w.rares || []).filter(hit);
          var byZone = {};
          rows.forEach(function (r) { (byZone[r.zone || '未归区域'] = byZone[r.zone || '未归区域'] || []).push(r); });
          var zorder = Object.keys(byZone).sort(function (a, b) {
            return lvStart(zByName[a]) - lvStart(zByName[b]) || (a < b ? -1 : 1);
          });
          if (f.zone) zorder = zorder.filter(function (z) { return z === f.zone; });
          var out = '<div class="card"><h2>先挑区域</h2><div class="picks">' +
            '<button type="button" class="pick' + (f.zone ? '' : ' on') + '" data-z="">' +
            '<b>全部</b><span class="dim mono">' + (w.rares || []).length + '</span></button>' +
            (w.rareRegions || []).filter(function (r) { return r.count; }).map(function (r) {
              return '<button type="button" class="pick' + (f.zone === r.zone ? ' on' : '') +
                '" data-z="' + D.esc(r.zone) + '"><b>' + D.esc(r.zone) + '</b>' +
                '<span class="dim mono">' + r.count + '</span></button>';
            }).join('') + '</div>' +
            '<p class="note">稀有精英是刷新型怪物，位置与掉落归属取自客户端解包；' +
            '刷新间隔与 respawn 计时游戏里没有对应字段，本站不猜。</p></div>';
          if (!zorder.length) {
            out += '<div class="card"><div class="empty">这个筛选下没有稀有精英，换个区域或清空搜索。</div></div>';
          }
          zorder.forEach(function (z) {
            var list = byZone[z], meta = zByName[z] || {};
            out += '<div class="band"><b>' + D.esc(z) + '</b><span class="dim">' + lvTxt(meta) + ' · ' + facTxt(meta) +
              '</span><span class="dim mono">' + list.length + ' 个</span></div><div class="rgrid">' +
              list.map(function (r) {
                return '<div class="rarecard">' + mapBox(r, z) +
                  '<div class="rbody"><b>' + D.esc(r.nameCn) + '</b>' +
                  (r.nameEn ? '<span class="dim mono">' + D.esc(r.nameEn) + '</span>' : '') +
                  '<span class="rtags">' +
                  '<span class="tag">' + (r.kind === 'rare-elite' ? '稀有精英' : '稀有') + '</span>' +
                  (r.isNew ? '<span class="tag new">无限新增</span>' : '') +
                  '<span class="dim mono">' + lvTxt(r) + '</span></span>' +
                  coordTxt(r) +
                  (r.drops.length
                    ? '<div class="loot">' + r.drops.map(dropRow).join('') + '</div>'
                    : '<div class="note">这一条没有掉落记录，本站不补——等实测或下一次数据核对。</div>') +
                  '<button type="button" class="ghost wide" data-r="' + D.esc(r.id) + '">看这条的来源</button>' +
                  '<div class="wdr" id="wr-' + D.esc(r.id) + '">' +
                  '<h3>掉落清单</h3>' + (r.drops.length
                    ? '<ul class="list">' + r.drops.map(function (d) {
                      return '<li>' + D.esc(d.nameCn) + '（#' + D.esc(d.itemId) + '，' +
                        (d.bind ? D.esc(d.bind) : '绑定方式未采') + '）</li>';
                    }).join('') + '</ul>'
                    : '<p class="dim">未采到。</p>') +
                  '<h3>坐标说明</h3><p class="note">括号里是那张小地图上的百分比位置，"世界"是客户端原始坐标；两套都是同一次解包出来的。</p>' +
                  '<h3>来源与核对</h3>' + D.sources(r.provenance) + '</div></div></div>';
              }).join('') + '</div>';
          });
          var sets = (w.rareSets || []).map(function (s) {
            return '<div class="card"><h2>套装 · ' + D.esc(s.nameCn) + '</h2>' +
              '<p class="note">' + s.pieces.length + ' 件套，件名与物品 ID 取自客户端；套装效果那句本站不写，等官方中文稿。</p>' +
              '<div class="loot">' + s.pieces.map(dropRow).join('') + '</div>' +
              '<ul class="list">' + s.pieces.map(function (p) {
                return '<li>' + D.esc(p.nameCn) + ' — ' + (p.fromRare ? '来自稀有「' + D.esc(p.fromRare) + '」' : '来源稀有未采') + '</li>';
              }).join('') + '</ul></div>';
          }).join('');
          var un = (w.raresUnplaced || []);
          return out + sets + (un.length ? '<div class="card"><h2>位置没核出来的 ' + un.length + ' 个稀有</h2>' +
            '<p class="note">名单里有这些名字，但没有坐标。名字留着当线索，不当数据——不猜位置。</p>' +
            '<div class="chips">' + un.map(function (x) {
              return '<span class="chipc">' + D.esc(x.nameCn) + '</span>';
            }).join('') + '</div></div>' : '');
        }

        /* --- 面板三：书籍 --- */
        function panelBooks() {
          var rows = (w.books || []).filter(hit);
          var byZone = {};
          rows.forEach(function (b) { (byZone[b.zone || '未归区域'] = byZone[b.zone || '未归区域'] || []).push(b); });
          var zname = Object.keys(byZone).sort(function (a, b) {
            return lvStart(zByName[a]) - lvStart(zByName[b]) || (a < b ? -1 : 1);
          });
          var lib = (w.librarians || []).map(function (l) {
            return '<div class="lrow"><b>' + D.esc(l.nameCn) + '</b><span class="dim">' + D.esc(l.faction || '') +
              ' · ' + D.esc(l.city || '') + (l.quarter ? '，' + D.esc(l.quarter) : '') + '</span>' + coordTxt(l) + '</div>';
          }).join('');
          var rw = (w.bookRewards || []).map(function (r) {
            return '<tr><td class="mono">' + r.books + ' 本</td><td>' + D.esc(r.title) + '</td>' +
              '<td class="mono dim">' + (r.questId ? '#' + D.esc(r.questId) : '—') + '</td>' +
              '<td>' + (r.noReward ? D.pill('L2') + ' <span class="dim">' + D.esc(r.noRewardNote) + '</span>'
                : r.items.map(dropRow).join('')) + '</td></tr>';
          }).join('');
          var out = '<div class="card"><h2>先找书，再找管理员</h2>' +
            '<p class="note">书名、所在容器与坐标取自客户端解包（第三方转述）。' +
            '书本文字是第三方站的描述文案，本站不搬；只留"叫什么、在哪个容器、图上哪一点"。</p>' +
            '<div class="stats"><div class="stat"><b>' + (w.books || []).length + '</b>本已定位</div>' +
            '<div class="stat"><b>' + Object.keys(byZone).length + '</b>个区域有书</div>' +
            '<div class="stat"><b>' + (w.booksMissing || []).length + '</b>本只有名字</div></div>' +
            (lib ? '<h3>上交对象</h3>' + lib : '') + '</div>';
          if (!zname.length) out += '<div class="card"><div class="empty">这个筛选下没有书。</div></div>';
          zname.forEach(function (z) {
            var list = byZone[z], meta = zByName[z] || {};
            out += '<div class="band"><b>' + D.esc(z) + '</b><span class="dim">' + lvTxt(meta) +
              (list[0].zoneKind === 'city' ? ' · 主城' : '') + '</span>' +
              '<span class="dim mono">' + list.length + ' 本</span></div>' +
              (list[0].mapFile ? '<div class="zthumb">' + mapBox(list[0], z) + '</div>' : '') +
              '<div class="scrollx"><table class="entab bktab"><thead><tr><th class="ich">书</th><th>名称</th>' +
              '<th>容器</th><th>位置</th><th>物品 ID</th></tr></thead><tbody>' +
              list.map(function (b) {
                return '<tr><td class="ich">' + iconCell(b.iconKey, b.itemId, b.nameCn, 1) + '</td>' +
                  '<td><b>' + D.esc(b.nameCn) + '</b>' +
                  (b.forever ? '<span class="tag new">无限新增</span>' : '') +
                  (b.place ? '<span class="dim"> · ' + D.esc(b.place) + '</span>' : '') + '</td>' +
                  '<td class="dim">' + D.esc(b.container || '—') + '</td>' +
                  '<td>' + coordTxt(b) + '</td>' +
                  '<td class="mono dim">' + (b.itemId ? '#' + D.esc(b.itemId) : '—') + '</td></tr>';
              }).join('') + '</tbody></table></div>';
          });
          return out + (rw ? '<div class="card"><h2>上交多少本换什么</h2>' +
            '<p class="note">门槛与称号取自客户端；奖励物品 ID 一并列出。没有奖励记录的那一档写待实测，不编。</p>' +
            '<div class="scrollx"><table class="entab"><thead><tr><th>门槛</th><th>称号</th><th>任务</th><th>奖励</th></tr></thead>' +
            '<tbody>' + rw + '</tbody></table></div></div>' : '') +
            ((w.booksMissing || []).length ? '<div class="card"><h2>只有名字、没给坐标的 ' + (w.booksMissing || []).length + ' 本</h2>' +
              '<div class="chips">' + (w.booksMissing || []).map(function (b) {
                return '<span class="chipc">' + D.esc(b.nameCn) + '<b class="mono dim">#' + D.esc(b.itemId) + '</b></span>';
              }).join('') + '</div></div>' : '');
        }

        /* --- 面板四：睡袋 --- */
        function panelBag() {
          var bt = w.bagTool || {}, p = bt.params || {}, bag = bt.bag;
          if (!bag) return '<div class="card"><div class="empty">睡袋这一条还没有可信的物品记录，本站不编。</div></div>';
          var out = '<div class="card"><h2>睡袋本身</h2>' +
            '<div class="itemrow">' + iconCell(bag.iconKey, bag.itemId, bag.nameCn) +
            '<div><b>' + D.esc(bag.nameCn) + '</b>' +
            '<span class="dim mono">#' + D.esc(bag.itemId) + '</span>' +
            (bag.bind ? '<span class="dim">' + D.esc(bag.bind) + '</span>' : '') +
            (bt.usableLevel ? '<span class="dim mono">' + bt.usableLevel + ' 级可用</span>' : '') + '</div></div>';
          out += '<table class="mtx"><thead><tr><th>机制项</th><th>记录值</th><th>分级</th></tr></thead><tbody>' +
            [['铺开耗时', p.castSec + ' 秒'], ['休息收益名', p.buffName || '—'],
              ['收益持续', p.buffHours + ' 小时'], ['可叠层', p.stacks + ' 层'],
              ['铺设冷却', p.cdMin + ' 分钟']]
              .map(function (x) {
                return '<tr><td>' + D.esc(x[0]) + '</td><td class="mono">' + D.esc(x[1]) + '</td>' +
                  '<td>' + D.pill(bt.paramsLevel) + '</td></tr>';
              }).join('') + '</tbody></table>' +
            '<p class="note">' + D.esc(bt.paramsNote || '') + '</p></div>';
          var camps = [];
          (bt.camps || []).forEach(function (c) { camps = camps.concat(c.places || []); });
          var kk = kw();
          if (kk) camps = camps.filter(function (c) {
            return ((c.zone || '') + ' ' + (c.whereCn || '') + ' ' + (c.landmark || '')).toLowerCase().indexOf(kk) >= 0;
          });
          out += '<div class="card"><h2>营地点清单 · ' + camps.length +
            (kk ? '（搜索 ' + D.esc(f.q) + ' 命中）' : '') + '</h2>' +
            '<p class="note">这里只回答"这些营点在哪个区域的哪一点"。' +
            '睡袋页面本身是一条冲级路线，步骤与收益讲解属攻略性质，本站红线不搬。</p>' +
            (camps.length ? '<div class="rgrid">' + camps.map(function (c) {
              return '<div class="rarecard">' + mapBox(c, c.zone) + '<div class="rbody">' +
                '<b>' + D.esc(c.zone || '区域未标') + '</b>' +
                (c.landmark ? '<span class="dim">' + D.esc(c.landmark) + '</span>' : '') +
                (c.whereCn ? '<span class="dim">' + D.esc(c.whereCn) + '</span>' : '') +
                coordTxt(c) + '</div></div>';
            }).join('') + '</div>' : '<div class="empty">这个关键词下没有营点，上面的关键词是按区域或地标名搜的。</div>') +
            '</div>';
          return out;
        }

        function draw() {
          var body = f.tab === 'zones' ? panelZones() : f.tab === 'rares' ? panelRares()
            : f.tab === 'books' ? panelBooks() : panelBag();
          el('wbody').innerHTML = body +
            '<div class="card" id="todo"><h2>这一页没有的</h2><ul class="list">' +
            (w.meta.notCollected || []).map(function (x) { return '<li>' + D.esc(x) + '</li>'; }).join('') +
            '</ul><h3>坐标说明</h3><p class="note">' + D.esc(w.meta.coordinateNote || '') + '</p>' +
            '<h3>来源与核对</h3>' + D.sources(w.provenance) + '</div>';
          Array.prototype.forEach.call(document.querySelectorAll('.zmark'), function (b) {
            b.style.left = b.dataset.x + '%'; b.style.top = b.dataset.y + '%';
          });
          Array.prototype.forEach.call(document.querySelectorAll('[data-r]'), function (btn) {
            if (btn.dataset.bound) return;
            btn.dataset.bound = '1';
            var label = btn.textContent;
            btn.onclick = function () {
              var x = el('wr-' + btn.dataset.r);
              var open = x.classList.toggle('open');
              btn.textContent = open ? '收起' : label;
            };
          });
          Array.prototype.forEach.call(document.querySelectorAll('[data-z]'), function (btn) {
            if (btn.dataset.bound) return;
            btn.dataset.bound = '1';
            btn.onclick = function () { f.zone = btn.dataset.z; f.tab = 'rares'; paint(); draw(); };
          });
          Array.prototype.forEach.call(document.querySelectorAll('.zcard[data-zone]'), function (btn) {
            if (btn.dataset.bound) return;
            btn.dataset.bound = '1';
            btn.onclick = function () {
              if (!btn.classList.contains('lk')) return;
              f.zone = btn.dataset.zone; f.tab = 'rares'; paint(); draw();
            };
          });
        }
        function tabBtn(t, n) {
          return '<button type="button" class="pick' + (f.tab === t[0] ? ' on' : '') + '" data-t="' + t[0] + '"' +
            ' aria-pressed="' + (f.tab === t[0] ? 'true' : 'false') + '"><b>' + t[1] + '</b>' +
            '<span class="dim mono">' + n + '</span></button>';
        }
        function paint() {
          Array.prototype.forEach.call(document.querySelectorAll('[data-t]'), function (b) {
            var on = b.dataset.t === f.tab;
            b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
          });
        }
        var qi;
        set('<div class="card"><h1 class="pt">世界：区域、稀有与书</h1>' +
          '<p class="dim">区域等级与阵营、稀有精英的刷新点和掉落归属、图书馆书籍的位置，' +
          '全部来自无限客户端解包（第三方资料站转述），逐条能点开看来源。' +
          '刷新计时、冲级路线、任何掉落概率都不做。</p>' +
          '<div class="stats"><div class="stat"><b>' + (w.zones || []).length + '</b>个区域</div>' +
          '<div class="stat"><b>' + newZones.length + '</b>个无限新增</div>' +
          '<div class="stat"><b>' + (w.rares || []).length + '</b>个已定位稀有</div>' +
          '<div class="stat"><b>' + (w.books || []).length + '</b>本书有坐标</div>' +
          '<div class="stat"><b>' + (w.maps || []).length + '</b>张客户端地图</div></div>' +
          '<div class="picks">' + WTABS.map(function (t, i) {
            return tabBtn(t, [
              (w.zones || []).length,
              (w.rares || []).length,
              (w.books || []).length,
              ((w.bagTool || {}).camps || []).length
            ][i]);
          }).join('') + '</div>' +
          '<div class="field"><input type="search" id="wq" placeholder="搜区域、稀有或书名" value="' + D.esc(f.q) + '"></div></div>' +
          '<div id="wbody"></div>');
        paint();
        Array.prototype.forEach.call(document.querySelectorAll('[data-t]'), function (b) {
          b.onclick = function () { f.tab = b.dataset.t; f.zone = ''; paint(); draw(); };
        });
        qi = el('wq');
        qi.oninput = function () { f.q = qi.value; draw(); };
        draw();
      }).catch(fail);
  }

  /* ---------- 最新动态：官方时间点 + 客户端改动清单 + 本站更新 ---------- */
  var CH_KINDS = [['all', '全部类别'], ['added', '新增'], ['modified', '改动'], ['moved', '换层或换系'],
    ['removed', '移除'], ['renamed', '改名'], ['unchanged', '未变']];
  function updates() {
    Promise.all([D.load('data/changes.json'), D.load('data/timeline.json'),
      D.load('data/releases.json'), D.load('data/classes.json'), D.load('data/scale.json')])
      .then(function (r) {
        var ch = r[0], tl = (r[1].items || []).slice().sort(byDate), cl = r[2].items || [],
          classes = r[3].classes, S = r[4].scale;
        var f = { cls: '', kind: 'all', what: 'all', q: urlQ('q') };
        // 搜索结果是带着职业与「天赋/法术」跳进来的，落地就停在那张表上
        var uc = urlQ('c'), uw = urlQ('w');
        if (classes.some(function (c) { return c.id === uc; })) f.cls = uc;
        if (uw === 'talent' || uw === 'spell') f.what = uw;
        var cnOf = {};
        classes.forEach(function (c) { cnOf[c.id] = c.cn; });

        function rows() {
          var kw = f.q.trim().toLowerCase();
          return (ch.items || []).filter(function (x) {
            if (f.cls && x.classId !== f.cls) return false;
            if (f.what !== 'all' && x.kind !== f.what) return false;
            if (f.kind !== 'all' && x.changeKind !== f.kind) return false;
            if (kw && (x.nameCn || '').toLowerCase().indexOf(kw) < 0 &&
              (x.tree || '').toLowerCase().indexOf(kw) < 0) return false;
            return true;
          });
        }
        function draw() {
          var list = rows();
          el('chbody').innerHTML = '<div class="picks">' +
            '<button type="button" class="pick' + (f.cls ? '' : ' on') + '" data-c="">' +
            '<b>全职业</b><span class="dim mono">' + (ch.items || []).length + '</span></button>' +
            classes.map(function (c) {
              var n = (ch.items || []).filter(function (x) { return x.classId === c.id; }).length;
              return '<button type="button" class="pick' + (f.cls === c.id ? ' on' : '') +
                '" data-c="' + D.esc(c.id) + '"><b>' + D.esc(c.cn) + '</b>' +
                '<span class="dim mono">' + n + '</span></button>';
            }).join('') + '</div>' +
            '<div class="field">' +
            '<select id="cw" aria-label="按天赋或法术筛">' +
            [['all', '天赋 + 法术'], ['talent', '只看天赋'], ['spell', '只看法术']].map(function (x) {
              return '<option value="' + x[0] + '"' + (f.what === x[0] ? ' selected' : '') + '>' + x[1] + '</option>';
            }).join('') + '</select>' +
            '<select id="ck" aria-label="按改动类别筛">' + CH_KINDS.map(function (x) {
              return '<option value="' + x[0] + '"' + (f.kind === x[0] ? ' selected' : '') + '>' + x[1] + '</option>';
            }).join('') + '</select>' +
            '<input type="search" id="cq" placeholder="搜天赋名或系名" value="' + D.esc(f.q) + '">' +
            '<span class="dim mono" id="ccnt"></span></div>' +
            (list.length ? '<div class="scrollx"><table class="entab"><thead><tr><th class="ich">图标</th>' +
              '<th>名称</th><th>职业</th><th>所在系</th><th>类型</th><th>改动</th><th>核到哪天</th></tr></thead><tbody>' +
              list.slice(0, 400).map(function (x) {
                return '<tr><td class="ich">' + iconCell(x.iconKey, x.id, x.nameCn, 1) + '</td>' +
                  '<td>' + D.hl(x.nameCn, f.q) + (x.oldNameCn ? '<span class="dim">（旧名 ' +
                    D.esc(x.oldNameCn) + '）</span>' : '') + '</td>' +
                  '<td>' + D.esc(cnOf[x.classId] || x.classId) + '</td>' +
                  '<td class="dim">' + D.esc(x.tree || '—') + '</td>' +
                  '<td class="dim">' + (x.kind === 'spell' ? '法术' : '天赋') +
                  (x.maxRank ? ' <span class="mono">' + x.maxRank + ' 层</span>' : '') + '</td>' +
                  '<td><span class="tag' + (x.changeKind === 'added' ? ' new' : '') + '">' +
                  D.esc(x.changeCn) + '</span></td>' +
                  '<td class="mono dim">' + D.esc(x.discoveredAt || '—') + '</td></tr>';
              }).join('') + '</tbody></table></div>' +
              (list.length > 400 ? '<p class="note">一次只列 400 条（当前命中 ' + list.length +
                ' 条），把职业或类别收紧一点再看其余的。</p>' : '')
              : '<div class="empty">这个筛选下没有条目。</div>');
          el('ccnt').textContent = list.length + ' 条';
          Array.prototype.forEach.call(document.querySelectorAll('[data-c]'), function (b) {
            b.onclick = function () { f.cls = b.dataset.c; draw(); };
          });
          el('cw').onchange = function () { f.what = el('cw').value; draw(); };
          el('ck').onchange = function () { f.kind = el('ck').value; draw(); };
          var qi = el('cq');
          qi.oninput = function () { f.q = qi.value; draw(); };
        }

        var K = ['官方时间点', '客户端改动', '本站更新'];
        set('<div class="card"><h1 class="pt">最新动态</h1>' +
          '<p class="dim">这一页把"什么变了"拆成三件事各说各的：官方公告里写过的时间点、' +
          '客户端解包出来的职业改动清单、以及我们这座站自己改了什么。' +
          '<b>只在网页提供</b>——小程序按红线不做动态流与排行。</p>' +
          '<div class="stats">' +
          '<div class="stat"><b>' + tl.length + '</b>个官方时间点</div>' +
          '<div class="stat"><b>' + (ch.items || []).length + '</b>条客户端改动</div>' +
          '<div class="stat"><b>' + S.changesNew + '</b>个新增天赋</div>' +
          '<div class="stat"><b>' + S.changesRemoved + '</b>个移除天赋</div>' +
          '<div class="stat"><b>' + cl.length + '</b>条本站更新</div></div>' +
          '<div class="picks">' + K.map(function (t, i) {
            return '<a class="pick" href="#k' + i + '"><b>' + t + '</b></a>';
          }).join('') + '</div></div>' +

          '<div class="card" id="k0"><h2>官方公告里的时间点</h2>' +
          '<p class="note">只列官方公告写过的原话与日期，本站不做新闻转载与评论；中英文两个上线日期并存，不替玩家选一个。</p>' +
          tl.map(function (x) {
            return '<div class="flowrow"><b class="mono">' + D.esc(x.date) + '</b>' +
              '<div><b>' + D.esc(x.title) + '</b> ' + D.pill(x.level) +
              '<p class="dim">' + D.esc(x.what) + '</p></div></div>';
          }).join('') +
          '<h3>来源与核对</h3>' + D.sources((tl[0] || {}).provenance) + '</div>' +

          '<div class="card" id="k1"><h2>客户端改动清单 · ' + (ch.items || []).length + ' 条</h2>' +
          '<p class="note">本站写法（' + D.esc(ch.meta.generatedAt) + ' 定）：<b>只列名称与改动类别，不列改动的具体句子</b>。' +
          '别人整理的前后对照文本本站不复制，也不改写；' +
          '要看逐字对照请去来源页。改动类别是把客户端数据和经典旧世比对出来的，没进游戏实测。</p>' +
          '<div id="chbody"></div>' +
          '<h3>来源与核对</h3>' + D.sources((ch.items || [])[0] ? (ch.items[0].provenance) : []) +
          '<p class="note">' + D.esc(ch.meta.textPolicy) + '</p></div>' +

          '<div class="card" id="k2"><h2>本站更新 · ' + cl.length + ' 条</h2>' +
          '<p class="note">这一栏只报我们自己改了什么：每一条都对应仓库里一个真实提交，能回查。' +
          '不含官方消息，也不做任何评价。</p>' +
          cl.map(function (e) {
            var tags = (e.tags || []).slice(0, 5);
            return '<div class="flowrow"><b class="mono">' + D.esc(e.date) + '</b><div><b>' +
              D.esc(e.title) + '</b>' +
              '<span class="chips">' + tags.map(function (t) {
                return '<span class="chipc">' + D.esc(t) + '</span>';
              }).join('') + '</span></div></div>';
          }).join('') + '</div>');
        draw();
        // 从首页搜索跳进来时直接滚到那张表，别让人自己找
        if (f.q) {
          var k1 = el('k1');
          if (k1 && k1.scrollIntoView) k1.scrollIntoView({ block: 'start' });
        }
      }).catch(fail);
  }

  /* ---------- 资料完整度排行：本站覆盖排序，不是强度排行 ---------- */
  function rank() {
    Promise.all([D.load('data/scale.json'), D.load('data/classes.json'),
      D.load('data/art.json').catch(function () { return {}; })])
      .then(function (r) {
        var S = r[0].scale, classes = r[1].classes, cnOf = {};
        classes.forEach(function (c) { cnOf[c.id] = c.cn; });
        var rows = S.classRank || [];
        var max = rows.reduce(function (m, x) { return Math.max(m, x.total); }, 1);
        set('<div class="card"><h1 class="pt">职业资料完整度排行</h1>' +
          '<p class="dim">这是<b>本站资料覆盖度</b>的排序：哪个职业在我们这儿查得到的东西多、' +
          '哪部分还是只有客户端解包撑着。它回答"这个职业的资料全不全"，' +
          '<b>不回答哪个职业强</b>——我们没有战斗日志与实测数据，也不做强度排行。</p>' +
          '<div class="banner">排序依据：先按"官方中文佐证的条数"，再按"本站条目合计"。' +
          '全部由数据现算，改了数据重新生成就会变，不是人工排的名次。</div>' +
          '<div class="scrollx"><table class="entab ranktab"><thead><tr><th class="ich">名次</th><th>职业</th>' +
          '<th>官方中文佐证</th><th>客户端解包</th><th>本站条目合计</th><th>覆盖情况</th></tr></thead><tbody>' +
          rows.map(function (x) {
            return '<tr><td class="ich"><b class="rankno mono">' + x.place + '</b></td>' +
              '<td>' + iconCell((classes.filter(function (c) { return c.id === x.classId; })[0] || {}).iconKey,
                x.classId, cnOf[x.classId] || x.classId, 1) +
              '<b>' + D.esc(cnOf[x.classId] || x.classId) + '</b>' +
              '<span class="dim mono">' + D.esc(x.classId) + '</span></td>' +
              '<td class="mono">' + x.official + '</td>' +
              '<td class="mono">' + x.datamine + '</td>' +
              '<td class="mono">' + x.total + '</td>' +
              '<td><span class="cov mini"><i class="L0" style="width:' +
              Math.round(x.official / max * 100) + '%"></i><i class="L2" style="width:' +
              Math.round(x.datamine / max * 100) + '%"></i></span>' +
              '<span class="mono dim">' + x.share + '% 有官方中文</span></td></tr>';
          }).join('') + '</tbody></table></div>' +
          '<h3>每一列是怎么算出来的</h3><ul class="list">' +
          '<li>官方中文佐证：国服官方公告里出现过同名整句的天赋节点、词条与技能四态条目。</li>' +
          '<li>客户端解包：只有无限客户端解包（第三方站转述）支撑的名称与改动记录。</li>' +
          '<li>本站条目合计：天赋节点 + 术语词条 + 技能四态 + 客户端改动清单里挂在该职业名下的全部条目。</li>' +
          '<li>百分比：官方中文佐证 ÷ 合计。剩下的不是缺数据，是官方中文稿还没写到那块。</li>' +
          '</ul>' +
          '<div class="legend"><span><i class="sw L0"></i>官方中文已核</span>' +
          '<span><i class="sw L2"></i>客户端解包 / 待实测</span></div>' +
          '<h2>这一页刻意没有的</h2><ul class="list">' +
          '<li>DPS、副本强度、PvP 胜率：没有战斗数据，也不做（小程序侧更是红线）。</li>' +
          '<li>第三方站的 BiS 与梯队结论：属他人判断，不搬。</li>' +
          '<li>"推荐玩什么职业"：那是玩法取向，走选职业问答页，不混进这张表。</li></ul>' +
          '<h3>来源与核对</h3>' + D.sources([{ type: 'site-note', url: '',
            note: '本页数字是拿本站自己的数据现算的，没有外部链接' }]) + '</div>');
      }).catch(fail);
  }


  function fail(e) {
    if (window.console) console.error('数据加载失败', e);
    // 只有真的用 file:// 打开时才给本地服务命令，否则页面上不该出现这些
    var local = location.protocol === 'file:';
    set('<div class="card"><h2>数据没加载出来</h2><p class="dim">刷新一下试试；' +
      (local ? '这个站要起一个本地服务才能读数据：在项目里执行 <code>cd src &amp;&amp; python3 -m http.server 8812</code>，' +
        '再访问 <code>http://127.0.0.1:8812</code>。' : '如果一直这样，请把这一页的地址发给我们。') +
      '</p><button id="rt">重试</button></div>');
    var b = el('rt'); if (b) b.onclick = function () { location.reload(); };
  }

  shell();
  tickCountdown();
  setInterval(tickCountdown, 1000);
  ({ home: home, talent: talent, chooser: chooser, timeline: timeline, skills: skills, dungeons: dungeons, systems: systems, races: races, professions: professions, world: world, updates: updates, rank: rank, glossary: glossary, provenance: provenance })[page]();
})();
