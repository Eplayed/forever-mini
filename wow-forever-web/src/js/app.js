/* 页面渲染与交互 */
(function () {
  var D = window.WowData, E = window.TalentEngine;
  /* 两级常驻导航：一级是分组标签（不可点），二级项全部平铺露出，说明文字收进 title 悬停提示。
     参考站的「攻略」「新动态」不挂：本站红线不做攻略正文与新闻流。 */
  var NAV = [
    { t: '首页', href: 'index.html', d: '数据覆盖率与全部入口' },
    { t: '天赋', items: [
      { href: 'talent.html', t: '计算器', d: '9 职业 · 树结构与加点' }] },
    /* 2026-10-12：这一组的第一格改成「职业」页（每职业一页），技能书降成二级项。
       导航项的名字必须与「本站更新」里的板块标签一字不差，角标才会画出来（见 shell() 里那段）。 */
    /* 2026-10-12 用户实拍后决定：导航这条「技能书」先撤。
       技能书页本身还在站上（首页六个入口与职业页都还链着它），只是不占导航这一格——
       导航要留给"每职业一页"这种玩家会反复找的入口。*/
    { t: '职业', items: [
      { href: 'classes.html', t: '职业', d: '9 职业逐页：三系与节点数、技能变化、可选种族' },
      { href: 'chooser.html', t: '玩法问答', d: '7 题玩法取向问答，不是强度排行' },
      { href: 'legacy.html', t: '传承', d: '三棵专长树与全部传承挑战，每条点数照客户端写' }] },
    /* 「特长」那一格也撤了：它指向 races.html 里那张「按词找特长」卡，卡片按用户要求已去掉，
       40 条特长仍在种族详情里逐条带官方整句；搜索点特长会直接落到所属种族那一行。 */
    { t: '种族', items: [
      { href: 'races.html', t: '总览', d: '10 个种族行 · 可选职业矩阵' }] },
    { t: '世界', items: [
      { href: 'world.html', t: '区域与稀有', d: '44 个区域 · 36 个稀有刷新点 · 书籍与营地' },
      { href: 'dungeons.html', t: '副本', d: '38 座按十级一档分：首领与掉落归属' },
      { href: 'raids.html', t: '团本', d: '客户端能排到的团队条目与另一份名单对照' },
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
  /* 来源轨（签名元素）：卡片左缘一条竖轨，填充程度 = 这张卡最弱的那条数据的分级。
     级别从两处现读，不额外发明一份真相：
       ① 卡里已渲染出的分级徽标（.pill L0…L3）；
       ② 卡里的来源类型标签（.src .st）——官方中文/官方英文/客户端解包按既定口径可支撑 L0，
          第三方资料站与转载属 L2，没有任何来源记录属 L3。
     两处都有时取更弱的那个。卡里既没徽标也没来源就不上轨——没定级就别装作定了级。 */
  var LV_ORDER = { L0: 0, L1: 1, L2: 2, L3: 3 };
  var ST_LV = { official_cn: 'L0', official_en: 'L1', datamine_cn: 'L0',
    datamine_en: 'L1',
    fan_db: 'L2', media_cn: 'L2', video: 'L2' };
  function applyRails(scope) {
    Array.prototype.forEach.call((scope || document).querySelectorAll('.card, .mod, .dcard, .drawer'), function (c) {
      if (c.dataset.lv) { c.classList.add('rail'); return; }   // 渲染时已显式定级的卡，补类不走推断
      var worst = null;
      function take(k) {
        if (!LV_ORDER.hasOwnProperty(k)) return;
        if (worst === null || LV_ORDER[k] > LV_ORDER[worst]) worst = k;
      }
      Array.prototype.forEach.call(c.querySelectorAll('.pill'), function (p) {
        // 图例（覆盖率条那一排、四态图例、板块 chips）里的徽标是在数全站分布，
        // 不是这张卡自己的数据；拿它定轨会把"汇总卡"标成缺数据。
        if (p.closest('.covnum, .legend, .tlegend, .chipsrow, .cov')) return;
        var m = /\bL([0-3])\b/.exec(p.className);
        if (m) take('L' + m[1]);
      });
      Array.prototype.forEach.call(c.querySelectorAll('.src .st'), function (s) {
        take(ST_LV[Array.prototype.filter.call(s.classList, function (x) { return x !== 'st'; })[0]]);
      });
      if (!worst) return;
      c.classList.add('rail'); c.dataset.lv = worst;
    });
  }
  /* 卡片头（改版第二批）：每页主卡的 H1 换成「圆图标 + 标题」。
     图标只允许一种来源——这一页所属板块在首页图标轨上用的那张本地原画（同一板块站内同一张脸）。
     时间表 / 速查 / 动态 / 排行 / 溯源这五页讲的是本站的观点或流水，没有对应的板块原画，
     就不放图（cdHead 的 noart 分支保留标题左侧蓝线），不拿不相干的图凑数。
     放在 set() 里做而不是改 14 处字符串：主卡标题的写法各页不同（有的带 data-lv、有的后面紧跟
     .mline），一处装饰函数比 14 次字符串手术少得多出错面；重复调用无副作用（没 h1.pt 就跳过）。 */
  var PAGE_HEAD_SEC = { talent: 'talent', chooser: 'chooser', skills: 'skills', dungeons: 'dungeons',
    races: 'races', professions: 'professions', legacy: 'legacy', world: 'world' };
    // 团本页不在这张表里：它 2026-10-12 起按设计稿改用页首 banner（.dhero 里放 H1），不再套卡片头 
  function decoratePageHead() {
    var m = el('main');
    if (!m || page === 'home') return;   // 首页主卡在 hero 里，第一批已经给它单独排过（kicker + 图标轨）
    var card = m.querySelector('.card');
    var h1 = card && card.querySelector('h1.pt');
    if (!h1 || !card) return;
    var sec = PAGE_HEAD_SEC[page];
    h1.outerHTML = cdHead(h1.innerHTML, { h1: 1, img: sec ? secArt(sec) : '' });
  }
  function set(html) { el('main').innerHTML = html; decoratePageHead(); applyRails(el('main')); }
  /* 各页切 tab / 开抽屉时是局部重渲染，不经过 set()。用一个 observer 兜住：
     #main 里新增节点后补一次轨（已定过级的卡直接跳过，重复调用无副作用）。 */
  function watchRails() {
    var m = el('main');
    if (!m || !window.MutationObserver) return;
    var queued = false;
    new MutationObserver(function () {
      if (queued) return;
      queued = true;
      (window.requestAnimationFrame || setTimeout)(function () { queued = false; applyRails(m); });
    }).observe(m, { childList: true, subtree: true });
  }
  function store(key, val) {
    try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); return null; }
    catch (e) { D.toast('本机存储不可用，方案仅本次有效'); return null; }
  }
  /* 2026-10-12 站主决定：内容页只留标题与数据，出处与分级集中到溯源页（provenance.html）说。
     原来这里的 bindSrcToggles 负责把逐条「来源」按钮接到 srcbox 上，整块已从各页渲染里删掉。 */
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
  /* 树名与节点名同一套约定（2026-10-12）：官方定名当显示名，另一个叫法不删——
     红框小标 + 悬停说明，跟节点级分歧长得一样，玩家不用学第二套符号。
     以前 nameAltUpstream 只写在数据里没人读，等于"我们记录了分歧但决定不告诉你"。 */
  function treeAltTip(t) {
    return t && t.nameConflict && t.nameAlt
      ? ' title="这一系有两个叫法：官方中文写「' + D.esc(t.nameCn) + '」，另一来源译作「' + D.esc(t.nameAlt) + '」，待定稿"' : '';
  }
  function treeName(t) {
    if (!t || !t.nameCn) return '';
    return D.esc(t.nameCn) + (t.nameConflict && t.nameAlt ? '<i class="cfl" aria-hidden="true"></i>' : '');
  }
  /* 卡片头（2026-10-11 改版第二批）：图标 + 标题 + 右侧读数。
     o.img 只允许两种来源——这张卡讲的那个具体实体自己的本地图，或 secArt() 给的板块图；
     没有就传空，标题保留蓝线，不放不相干的图凑数。o.act 是这张卡自己的计数或出口，
     不再塞在标题后面当后缀（"配方 · 118 条"读起来要拐一下，右对齐一眼就扫到）。 */
  function cdHead(title, o) {
    o = o || {};
    var ic = o.img ? '<span class="hicon"><img src="' + D.esc(o.img) + '" alt="" loading="lazy"></span>' : '';
    var t = o.h1 ? '<h1 class="pt">' + title + '</h1>' : '<h2>' + title + '</h2>';
    return '<div class="cdhead' + (ic ? '' : ' noart') + (o.h1 ? ' big' : '') + '">' + ic + t +
      (o.act ? '<span class="cdact">' + o.act + '</span>' : '') + '</div>';
  }
  /* 板块图：页级主卡与首页图标轨共用这一份表，同一板块在站内始终是同一张脸。
     值是本地文件路径；由 site-check 断言每个路径都出现在 src/data/art.json 的清单里
     （专业那格除外，它用的是官方 CDN 转存的专业图标）——没登记过的图不许上页面。
     做成常量表而不是从 art.json 现取，是因为各页的数据加载清单不一样，
     现取会让没引 art.json 的那几页静默没有图标，卡口查不出来。 */
  var SEC_ART = {
    talent: 'img/art/classes/druid.webp', chooser: 'img/art/classes/paladin.webp',
    skills: 'img/art/classes/mage.webp', legacy: 'img/art/races/skyborne.webp',
    races: 'img/art/races/human.webp', world: 'img/art/dungeons/city-of-dalaran.webp',
    dungeons: 'img/art/dungeons/blackrock-depths.webp', raids: 'img/art/dungeons/blackmaw-hold.webp',
    professions: 'img/icons/10prof_table_tailoring01.jpg'
  };
  function secArt(sec) { return SEC_ART[sec] || null; }
  /* 专精背景图（27 张，每系一张 320×384）：来自 art.json 的 specs 键，键名是「职业-第几系」。
     取不到就退回该职业的横幅，再没有就留空——不拿 128 的图标放大凑数（用户实拍指的就是这个）。 */
  function specArt(A, cid, ti) {
    var S = (A || {}).specs || {};
    return S[(cid || '') + '-' + (ti === undefined ? 0 : ti)] || S[(cid || '') + '-0'] || '';
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
  /* 吸顶头部的真实高度写回 --hd-h：锚点让位（#main [id] 的 scroll-margin-top）与
     吸顶表头都读这一个值。头部高度是内容撑出来的（搜索框、导航带行数、移动端单行），
     在 CSS 里写死常数一定会飘——2026-10-11 用户反馈"跳锚点顶部被遮挡"就是这么来的。 */
  function syncHeaderH() {
    var t = el('top');
    if (!t) return;
    var h = Math.round(t.getBoundingClientRect().height);
    if (h) document.documentElement.style.setProperty('--hd-h', h + 'px');
  }
  var hdTimer = 0;
  window.addEventListener('resize', function () {
    clearTimeout(hdTimer);
    hdTimer = setTimeout(syncHeaderH, 120);
  });
  function shell() {
    var left = launchLeft();
    // 一级是分组标签（只说明归属，不可点），二级项全部平铺：玩家不用点开菜单就知道这站有什么
    function navLink(it) {
      return '<a class="nl' + (page === navKey(it.href) ? ' on' : '') + '" href="' + it.href +
        '" title="' + D.esc(it.d) + '">' + it.t + '</a>';
    }
    el('top').innerHTML =
      '<div class="hd hd-top"><div class="in bar-flex">' +
        '<a class="brand" href="index.html">无限<span>资料站</span></a>' +
        '<form class="top-search" role="search" action="index.html" method="get">' +
        '<svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true"><path d="M10 2a8 8 0 105.3 14.3l5 5 ' +
        '1.4-1.4-5-5A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z"/></svg>' +
        '<input type="search" id="gstop" name="q" autocomplete="off" placeholder="搜全站词条、天赋、副本、配方" ' +
        'aria-label="全站搜索：跳到首页搜索框并带上这个词">' +
        '<button type="submit" class="gsgo">搜索</button></form>' +
        '<div class="chip mono" id="lchip">距上线 ' + left.d + ' 天 ' + pad2(left.h) + ':' +
        pad2(left.m) + ':' + pad2(left.s) + '</div></div></div>' +
      '<nav class="main" aria-label="主导航"><div class="in">' + NAV.map(function (g, i) {
        // 上下两级：组名一块、它的入口排在下面，组与组靠竖分隔与组色区分（见 app.css .ngrp）
        if (g.href) return '<span class="ngrp solo"><span class="ngi">' + navLink(g) + '</span></span>';
        var hit = g.items.some(function (it) { return page === navKey(it.href); });
        return '<span class="ngrp g' + i + (hit ? ' hit' : '') + '" role="group" aria-label="' +
          D.esc(g.t) + '"><b class="ngt">' + g.t + '</b><span class="ngi">' +
          g.items.map(navLink).join('') + '</span></span>';
      }).join('') + '</div></nav>';
    // 手机上是横滑导航带：把当前页那一项先滚到中间，免得进来只看到别的分组
    var cur = el('top').querySelector('nav.main a.nl.on');
    if (cur && cur.scrollIntoView && window.innerWidth <= 600) {
      cur.scrollIntoView({ inline: 'center', block: 'nearest' });
    }
    syncHeaderH();
    Promise.all([D.load('data/meta.json'), D.load('data/scale.json')])
      .then(function (r) {
        var meta = r[0], sc = r[1].scale;
        // 角标由 releases.json 派生（本版新增 / 近期更新），只在标签正好等于某个导航项名字时出现
        (el('top').querySelectorAll('nav.main a.nl') || []).forEach(function (a) {
          var t = a.textContent.trim();
          if ((sc.navNew || []).indexOf(t) < 0) return;   // 标签对不上导航项名字就不画，不硬凑
          var i = document.createElement('i');
          i.className = 'nb new';
          // 一个字：整条导航宽 1180px，写「本版新增」会把这一项挤到第二行（实测 39→79px）
          i.textContent = '新';
          i.setAttribute('title', '这一版新开了这一页');
          i.setAttribute('aria-label', '这一版新开了这一页');
          a.appendChild(i);
        });
        /* 页脚按设计稿换成三栏铭牌（1.6fr 1fr 1fr + 一条底栏）。
           2026-10-12 站主决定：页脚只留免责句，数据版本/核对日期与覆盖率那两条移出内容页，
           出处与覆盖率集中在溯源页（provenance.html）说。
           两栏链接不写死名单：从 NAV 那张表里挑，标签与说明跟导航同源，
           导航改名/挪页时页脚不会留一份过期副本（稿子里那 8 项是 <span> 假链接，这里全做成能点的）。 */
        var TOOL = { 'talent.html': 1, 'chooser.html': 1, 'glossary.html': 1, 'timeline.html': 1,
          'updates.html': 1, 'rank.html': 1, 'systems.html': 1, 'provenance.html': 1 };
        var cols = { tool: [], data: [] };
        NAV.forEach(function (g) {
          (g.items || [{ href: g.href, t: g.t, d: g.d }]).forEach(function (it) {
            if (!it.href || it.href === 'index.html') return;
            (TOOL[it.href.split('#')[0]] ? cols.tool : cols.data).push(it);
          });
        });
        function fcol(c) {
          return '<div class="fcol">' + c.map(function (x) {
            return '<a href="' + D.esc(x.href) + '" title="' + D.esc(x.d || '') + '">' + D.esc(x.t) + '</a>';
          }).join('') + '</div>';
        }
        el('foot').innerHTML = '<div class="fwrap"><div class="fgrid">' +
          '<div class="fcol fbrand"><span class="fstar"><svg viewBox="0 0 48 48" aria-hidden="true">' +
          '<circle cx="24" cy="24" r="22" fill="none" stroke="currentColor" stroke-width="2"/>' +
          '<path d="M24 8 L28 22 L42 24 L28 26 L24 40 L20 26 L6 24 L20 22 Z" fill="currentColor"/></svg></span>' +
          '<b>无限资料站</b>' +
          '<p>' + D.esc(meta.disclaimer) + '</p></div>' +
          '<div><div class="fh">工具</div>' + fcol(cols.tool) + '</div>' +
          '<div><div class="fh">资料</div>' + fcol(cols.data) + '</div></div></div>';
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
  var SKIND_ORDER = ['cls', 'race', 'tal', 'lpg', 'lch', 'chg', 'term', 'abl', 'dun', 'boss', 'rdd',
    'zone', 'rare', 'bok', 'camp', 'prof', 'rec', 'gnd', 'tra'];
  // 加一个板块必须同时进这张表：不在表里的板块，首页搜索会直接搜不到（build-data.js 卡这条）
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
      box.innerHTML = '<p class="gsl">索引里没有叫「' + D.esc(k) + '」的条目。</p>';
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
    // 稿子在搜索框里放了一颗实心"立即搜索"：有结果就进第一条，没结果就只是把结果展开
    var go = el('ggo');
    if (go) go.onclick = function () {
      run();
      if (SX.rows && SX.rows.length) location.href = sHref(SX.rows[0]);
    };
    // 顶栏搜索框跳到首页会带 ?q=，这里接住：填进去并立刻出结果，不让人重打一遍
    var q0 = urlQ('q');
    if (q0 && !inp.value) { inp.value = q0; run(); }
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
      /* 2026-10-12 站主决定：讲数据出处与角标含义的那段说明已从内容页删掉，出处集中在溯源页。 */
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

  // 客户端号只报 build 尾号：字段里括号那段（"天赋树成品仍是两份第三方资料站…的对齐结果"）
  // 是我们自己的核对备注，不上页面。取号先按括号截断，再按点取最后一段。
  function buildTail(meta) {
    var b = String(((meta || {}).dataBaseline || {}).build || '');
    return b.split('（')[0].split('.').pop();
  }
  /* ---------- 首页 ---------- */
  // 时间表里有"待定""择期"这类没有具体日期的条目，排序时让真日期排前面，别顶掉首屏
  function byDate(a, b) {
    var ra = /^\d{4}-\d{2}-\d{2}$/.test(a.date || ''), rb = /^\d{4}-\d{2}-\d{2}$/.test(b.date || '');
    if (ra && rb) return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
    if (ra !== rb) return ra ? -1 : 1;
    return 0;
  }
  /* 时间点分"已过 / 待来 / 日期未定"：按 +08:00 的当日零点比，和上线日期同一个时区口径。
     首页那张卡的两个数与时间表页必须同一算法，否则同一站两处数互相打脸。 */
  function tlCounts(items) {
    var now = Date.now(), done = 0, up = 0;
    (items || []).forEach(function (x) {
      var t = /^\d{4}-\d{2}-\d{2}$/.test(x.date || '')
        ? new Date(x.date + 'T00:00:00+08:00').getTime() : null;
      if (t === null) return;
      if (t <= now) done += 1; else up += 1;
    });
    return { done: done, upcoming: up };
  }
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
      var ART = r[8] || {};
      // 副本卡的背景取第一座"无限新增"本的载入图；素材没转存到位就不加背景层
      var DUN = { art: '' };
      (r[2].newDungeons || []).some(function (x) {
        var f = (ART.dungeons || {})[x.slug || x.id];
        if (f) { DUN.art = f; return true; }
        return false;
      });
      var left = launchLeft();
      var recent = tl.slice().sort(byDate).slice(0, 3);
      // 四格之和现算，不写死：写死的数会在同一张卡里与"全部条目"互相打脸
      var chgSum = (S.changesNew || 0) + (S.changesModified || 0) + (S.changesRemoved || 0) +
        (S.changesSpellsChanged || 0);

      /* 入口卡：一张卡 = 一个去处，背景一定是"图"（客户端原画 / 载入图 / 场景图），
         不是把 128 的图标拉开放大。2026-10-13 用户实拍：以前那些卡拿职业图标当背景，
         放大就是一团糊的；这次每格都从 art.json 里取真图，取不到留纯色，不放假图。
         卡上只留三样：板块归属一行、标题、一行读数。 */
      function artOf(group, key) { return ((ART[group] || {})[key]) || ''; }
      function mod(m) {
        return '<a class="mod' + (m.art ? ' hasart' : '') + '" href="' + m.href + '">' +
          (m.art ? '<span class="bgart" aria-hidden="true" style="background-image:url(' + m.art + ')"></span>' : '') +
          '<div class="mline">' + D.esc(m.kicker) + '</div>' +
          '<h2>' + m.t + '</h2>' +
          '<div class="modn">' + m.n.map(function (x) {
            return '<span><b class="mono">' + x[0] + '</b>' + x[1] + '</span>';
          }).join('') + '</div></a>';
      }
      function E(href, t, kicker, n, art) { return { href: href, t: t, kicker: kicker, n: n, art: art }; }
      var MODS = [
        { line: '角色与职业', items: [
        E('talent.html', '天赋计算器', '工具 · ' + S.classes + ' 职业',
          [[S.talentNodes, '个天赋节点'], [S.changesNew, '个新增天赋']], artOf('panels', 'talent')),
        E('classes.html', '职业总览', '职业 · ' + S.classes + ' 页',
          [[S.classes, '个职业'], [S.abilities, '条技能说明']], artOf('classBanners', 'warrior')),
        E('chooser.html', '不知道选哪个职业', '工具 · 问答 7 题',
          [[7, '题'], [S.classes, '职业候选']], artOf('classBanners', 'druid')),
        E('skills.html', '技能书', '角色 · 技能',
          [[S.abilities, '条官方整句'], [S.glossary, '条四态对照']], artOf('panels', 'spellbook')),
        E('legacy.html', '传承专长与挑战', '角色 · 本版新增',
          [[S.legacy.perks, '个专长有明细'], [S.legacy.unknown, '格未公开']], artOf('scenes', 'guangshu')),
        E('races.html', '种族与职业组合', '角色 · 种族 ' + S.races + ' 行',
          [[S.races, '个种族行'], [S.traits, '条特长整句']], artOf('factionCities', 'alliance'))
        ] },
        { line: '世界与冒险', items: [
        E('world.html', '区域与稀有精英', '世界 · 区域 ' + S.zones + ' 个',
          [[S.zones, '区域'], [S.rares, '已定位稀有'], [S.books, '本书有坐标']], artOf('maps', '1411')),
        E('dungeons.html', '副本与掉落', '世界 · ' + S.dungeons + ' 座',
          [[S.dungeons, '座本'], [S.bosses, '个首领'], [S.drops, '条掉落']], artOf('dungeons', 'city-of-dalaran')),
        E('raids.html', '团队副本', '世界 · 团本',
          [[(S.raids || {}).names || 0, '个团队条目'], [(S.raids || {}).claimed || 0, '座有名单']],
          artOf('scenes', 'tielu-dadian')),
        E('professions.html', '专业与配方', '专业 · ' + S.professions + ' 个',
          [[S.professions, '个专业'], [S.recipes, '条配方'], [S.gatherNodes, '个采集点']], artOf('scenes', 'gulin')),
        E('glossary.html', '中英术语速查', '世界 · 词条',
          [[S.glossary, '条词条'], [S.classes, '组职业']], artOf('classBanners', 'mage')),
        E('timeline.html', '上线与 Beta 时间表', '工具 · 时间点',
          [[S.timeline, '个时间点'], [tlCounts(tl).done, '个已过'], [tlCounts(tl).upcoming, '个待来']],
          artOf('factionCities', 'horde'))
        ] }
      ];
      /* 站方那几个去处不做卡片了（2026-10-13 用户：首页要留一行小入口）：
         排行 / 溯源 / 系统规则 / 最新动态，一行文字链，点得进但不抢版面。 */
      var MINILINKS = [['rank.html', '资料完整度排行'], ['provenance.html', '溯源与覆盖率'],
        ['systems.html', '系统与新区域'], ['updates.html', '这一版改了什么']];

      /* 首页主卡按设计稿改成整幅底图带：图是本站自生成的氛围图，左边压到 97% 暗给标题与搜索框。
         2026-10-12 站主决定：内容页只留标题与数据——「示意图」角标、覆盖率条与数据基线那几段
         已从页面上删掉，出处与覆盖率集中在溯源页（provenance.html）说。 */
      set('<section class="card hero dh mhero"><img class="dhbg" src="img/gen/hero-ruins.webp" alt="" ' +
        'style="object-position:center 42%"><span class="dhx"></span>' +
        '<div class="herot">' +
        '<span class="bbadge"><i></i>测试服进行中 · 客户端 ' + D.esc(buildTail(meta)) + '</span>' +
        '<h1 class="pt">回到最初的世界<br><em>探索无限的可能</em></h1>' +
        '<p class="lead">天赋、区域与稀有、副本掉落、专业配方、种族组合、中英术语。</p>' +
        '<div class="gsearch hs" role="search">' +
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>' +
        '<input type="search" id="gs" autocomplete="off" aria-controls="gres" aria-expanded="false" ' +
        'aria-label="全站搜索：天赋、改动、术语、副本、区域、配方、种族" ' +
        'placeholder="搜天赋、副本、区域、配方、种族特长（共 ' + S.search + ' 条）">' +
        '<button type="button" class="cta cta-gold" id="ggo">立即搜索</button>' +
        '<p class="gsex">' + [['潜行', '同一个词在改动清单和配方里都有'], ['领主大厅', '副本名'],
          ['咆鼻', '稀有精英'], ['舒适的睡袋', '世界页的营点']].map(function (x) {
            return '<button type="button" class="gsx" data-s="' + D.esc(x[0]) + '" title="' + D.esc(x[1]) + '">' +
              x[0] + '</button>';
          }).join('') + '</p>' +
        '<div class="gres" id="gres" hidden></div></div>' +
        '<div class="herobtns">' +
        '<a class="cta cta-line" href="updates.html">看这一版改了什么</a>' +
        '<a class="cta cta-mute" href="chooser.html">不知道选哪个职业：做 7 题玩法问答</a></div>' +
        '</div>' +
        '<aside class="heros"><div class="cd"><div class="cdrow"><b class="mono" id="cdD">' + left.d +
        '</b><span>天</span><i class="mono" id="cdT">' + pad2(left.h) + ':' + pad2(left.m) + ':' +
        pad2(left.s) + '</i></div>' +
        '<p class="dim">到正式服上线（' + LAUNCH.slice(0, 10) + '）</p></div></aside></section>' +
        /* 下面几块是稿子首页的骨架：选择你的职业 → 六个入口 → 板块图标轨 → 常用两卡。
           数字全部从 scale.json 现取，稿子里写死的 753 / 5353 / 6 开放 一个都不抄。 */
        /* 这九格点进去是"那一职业的天赋计算器"，不是职业页——2026-10-12 用户实拍后确认这样是对的，
           别"顺手"改成 classes.html：这一节的语义是"选一个职业开始加点"，
           职业页的入口在导航条那一格与页脚「资料」栏。 */
        '<section class="hsec"><div class="krow"><div><div class="kicker">CHOOSE YOUR CLASS</div>' +
        '<h2>选择你的职业</h2></div><a class="kall" href="chooser.html">7 题玩法问答 · 帮你定一个 →</a></div>' +
        '<div class="cls9">' + classes.map(function (c) {
          var ic = (ART.classes || {})[c.id];
          return '<a href="talent.html?c=' + encodeURIComponent(c.id) + '">' +
            (ic ? '<img src="' + D.esc(ic) + '" alt="" loading="lazy">'
              : '<i class="hrt-x">' + D.esc((c.cn || '?').charAt(0)) + '</i>') +
            '<b>' + D.esc(c.cn) + '</b></a>';
        }).join('') + '</div></section>' +
        /* 首页只留"去哪儿"：六个文字入口卡与三条线分组卡的读数版式一起撤掉（2026-10-13 用户实拍：
           入口重复、那些读数像数据变动明细不像资料站）。留图标轨 + 一组带真原画的入口卡。 */
        // 图标轨：一格一张本地原画的快速入口，没有图的退回字母块（用户实拍：这一排要留着）
        (function () {
          var tiles = [
            ['天赋计算器', 'talent.html', secArt('talent'), 'D'],
            ['玩法问答', 'chooser.html', secArt('chooser'), 'P'],
            ['技能书', 'skills.html', secArt('skills'), 'M'],
            ['传承', 'legacy.html', secArt('legacy'), 'L'],
            ['种族', 'races.html', secArt('races'), 'H'],
            ['世界', 'world.html', secArt('world'), 'W'],
            ['副本', 'dungeons.html', secArt('dungeons'), 'D'],
            ['团本', 'raids.html', secArt('raids'), 'R'],
            ['专业', 'professions.html', secArt('professions'), 'C']
          ];
          var isNew = (S.navNew || []);
          return '<div class="hrail" aria-label="板块入口">' + tiles.map(function (t) {
            return '<a class="hrt" href="' + t[1] + '" title="' + D.esc(t[0]) + '">' +
              '<span class="hrt-b">' + (t[2] ? '<img src="' + D.esc(t[2]) + '" alt="" loading="lazy">'
                : '<i class="hrt-x">' + t[3] + '</i>') +
              (isNew.indexOf(t[0]) >= 0 ? '<em class="hrt-n">新</em>' : '') + '</span>' +
              '<span class="hrt-l">' + t[0] + '</span></a>';
          }).join('') + '</div>';
        })() +
        /* 两张主推卡整卡可点（用户：「最常用的两个」那行标题不要了，卡片本身当入口）。
           data-go 的跳转由 bindGo() 做：点在卡里的链接或按钮上时不抢它们自己的去向。 */
        '<div class="two">' +
        '<section class="card hasart go" id="treecard" tabindex="0" data-go="talent.html?c=' + encodeURIComponent(PV.c) + '"><span class="bgart" aria-hidden="true" style="' +
          (specArt(ART, PV.c, PV.t) ? 'background-image:url(' + specArt(ART, PV.c, PV.t) + ')' : '') +
          '"></span><div class="mline">工具 · 天赋 · <b>' + S.classes + '</b> 职业 <b>' + S.talentNodes +
          '</b> 节点</div><h2>先看一棵真树，再进计算器</h2>' + treeCard() + '</section>' +
        '<section class="card hasart go" tabindex="0" data-go="dungeons.html"><span class="bgart" ' +
          'aria-hidden="true" style="' + (DUN.art ? 'background-image:url(' + DUN.art + ')' : '') + '"></span>' +
        '<div class="mline">世界 · 副本 · <b>' + S.dungeons + '</b> 座 <b>' + S.bosses +
          '</b> 首领 <b>' + S.drops + '</b> 条掉落归属</div><h2>副本手册</h2>' +
        '<div class="kv"><span>无限新增</span><b>' + S.dungeonsNew + ' 座</b></div>' +
        '<div class="mline" style="margin-top:var(--s3)">无限新增的 ' + (r[2].newDungeons || []).length +
          ' 座</div>' +
        (r[2].newDungeons || []).map(function (x) {
          var nb = (x.bosses || []).length;
          return '<div class="dunrow"><i' + (x.art ? ' style="background-image:url(' + x.art + ')"' : '') +
            ' aria-hidden="true"></i><b>' + D.esc(x.nameCn) + '</b>' +
            '<span class="dim mono">' + D.esc(typeof x.levelRange === 'string' ? x.levelRange + ' 级'
              : ((x.levelRange || [])[0] ? x.levelRange.join('–') + ' 级' : '等级待补')) + '</span>' +
            '<span class="dim mono">' + (nb ? nb + ' 首领' : '首领待补') + '</span></div>';
        }).join('') +
        '<a class="cta" href="dungeons.html">按十级一档看全部 ' + S.dungeons + ' 座 →</a></section></div>' +
        MODS.map(function (g) {
          return '<div class="grphead"><h2>' + g.line + '</h2></div>' +
            '<div class="modgrid">' + g.items.map(mod).join('') + '</div>';
        }).join('') +
        /* 「自经典旧世以来的改动」那四格与"全部 vs 四格之和"的对照行搬去动态页
           （2026-10-13 用户：那是数据明细，首页要的是入口）。这里只留一张入口卡。 */
        '<a class="mod big hasart" href="updates.html">' +
        '<span class="bgart" aria-hidden="true" style="background-image:url(' +
          (((ART.scenes || {}).yunhai) || ((ART.panels || {}).talent)) + ')"></span>' +
        '<div class="mline">这一版 · 客户端改动</div><h2>自经典旧世以来改了什么</h2>' +
        '<div class="modn"><span><b class="mono">' + S.changes + '</b>条改动</span>' +
        '<span><b class="mono">' + S.changesNew + '</b>个新增天赋</span>' +
        '<span><b class="mono">' + cl.length + '</b>条本站更新</span></div></a>' +
        // 站方口径的去处：一行文字链，点得进但不占卡位
        '<div class="chipsrow"><span class="dim">更多入口：</span>' + MINILINKS.map(function (x) {
          return '<a href="' + x[0] + '">' + x[1] + ' →</a>';
        }).join('') + '</div>' +
        // 原来这里是 .grid.g2 两栏（最新动态 + 「这一站刻意不做的」）；后一张卡按站主决定撤掉后只剩一张，
        // 两栏会空出半行，所以连壳一起换成整宽单卡。
        '<div class="card"><h2>最新动态</h2>' +
        '<p class="note">三件事分开说：官方公告里的时间点、客户端里的职业改动、本站自己改了什么。</p>' +
        /* 首页只给摘要：每块三条 + 一个出口，整段提交说明在两行处收住，
           要读全文点进动态页（2026-10-11 用户反馈这一卡读起来像流水账）。 */
        '<div class="nsec"><h3>官方公告里的时间点<span class="nact"><a href="updates.html#k0">全部 ' +
          recent.length + ' 个 →</a></span></h3>' +
        recent.slice(0, 3).map(function (x) {
          return '<div class="flowrow"><b class="mono">' + D.esc(x.date) + '</b>' +
            '<div><b class="clamp2">' + D.esc(x.title) + '</b>' +
            '<p class="dim clamp2">' + D.esc(x.what) + '</p></div></div>';
        }).join('') + '</div>' +
        (cl.length ? '<div class="nsec"><h3>本站最近改了什么<span class="nact"><a href="updates.html#k2">全部 ' +
          cl.length + ' 条 →</a></span></h3>' + cl.slice(0, 3).map(function (e) {
          return '<div class="flowrow"><b class="mono">' + D.esc(e.date) + '</b>' +
            '<div><b class="clamp2">' + D.esc(e.title) + '</b></div></div>';
        }).join('') + '</div>' : '') +
        '<a class="cta" href="updates.html">全部动态（' + S.timeline + ' 个时间点 · ' + S.changes +
        ' 条改动 · ' + cl.length + ' 条本站更新）→</a>' +
        '<a class="cta" href="rank.html">资料完整度排行全表 →</a></div>');
      /* 整卡当入口（2026-10-13 用户：「最常用的两个」那行标题不要了，卡片本身点进去）：
         点在卡里的链接或按钮上时让给它们自己，只有点在卡的空白处才按 data-go 跳。
         键盘用 tabindex + Enter，不用 <a> 套 <a>（HTML 不允许，浏览器会把内层拆出去）。 */
      function bindGo() {
        Array.prototype.forEach.call(document.querySelectorAll('[data-go]'), function (c) {
          if (c.dataset.gobound) return;
          c.dataset.gobound = '1';
          function go(e) {
            if (e && e.target && e.target.closest && e.target.closest('a, button, .stripc, .pnode, .pick')) return;
            location.href = c.dataset.go;
          }
          c.onclick = go;
          c.onkeydown = function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(e); } };
        });
      }
      bindSearch();
      bindPreview();
      bindGo();
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
  function compareHtml(t) {
    var nodes = (t && t.nodes) || {};
    var ids = Object.keys(nodes).filter(function (id) { return nodes[id].changeNote || (nodes[id].ranks || []).length; });
    if (!ids.length) return '';
    /* 2026-10-12 站主决定：对照文本出自哪里那句话已删（出处在溯源页），这里只留条目本身。 */
    return '<h3>与经典旧世逐条对照 · ' + ids.length + ' 条</h3>' +
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
    }).catch(function () { box.innerHTML = ''; });
  }
  function renderTalent() {
    var f = tstate.file, c = tstate.classes.filter(function (x) { return x.id === tstate.classId; })[0] || {};
    var pool = (f.namePool || []), trees = f.trees || [], r = E.defaults(f.rules);
    var head = '<div class="card" style="padding-bottom:0"><div class="classbar">' + tstate.classes.map(function (x) {
      return '<button class="cls ' + (x.id === tstate.classId ? 'on' : '') + '" data-c="' + x.id + '" style="min-width:78px">' +
        '<div class="ic">' + (window.Glyph ? Glyph.classTile(x.id, x.cn, x.iconKey) : D.esc((x.cn || '?').slice(0, 1))) + '</div><div class="n">' + D.esc(x.cn) + '</div></button>';
    }).join('') + '</div></div>';
    var banner = '';
    /* 2026-10-12 站主决定：内容页只留标题与数据——讲天赋数据出处与角标含义的那几段已删，
       出处集中在溯源页（provenance.html）。这里只留这一页自己的条数读数。 */
    if (f.structureStatus === 'none') {
      banner = '<div class="banner">这个职业还没有天赋数据。</div>';
    } else if (!trees.length) {
      banner = pool.length ? '<div class="banner"><button class="ghost" id="demo">载入演示数据</button></div>' : '';
    } else if (f.structureStatus === 'demo') {
      banner = '<div class="banner gray">当前是<b>演示结构</b>，节点名与位置都不是游戏数据。' +
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
      banner = '<div class="banner">本职业 ' + tcnt + ' 个天赋：与经典旧世相比<b class="ok">' + chg.added + ' 个新增</b>、' +
        '<b class="caution">' + chg.modified + ' 个改动</b>、' + chg.moved + ' 个换层、' + chg.unchanged + ' 个未变；' +
        vcnt + ' 个名称与官网中文一致' +
        (ccnt ? '，<b class="alert">' + ccnt + ' 个译名有两个叫法</b>' : '') +
        (gate ? '。层级点数门槛：第 2 层起需在本系累计 ' + gate + ' 点' : '') + '。</div>';
    }
    var cband = (tstate.art && tstate.art.classes) ? tstate.art.classes[tstate.classId] : null;
    var body = trees.length ? renderTrees(trees, r) : renderPool(pool);
    set(head + banner + '<div class="tpanel">' +
      (cband ? '<div class="tbg"><img src="' + D.esc(cband) + '" alt="" loading="lazy" ' +
        'onerror="this.className=\'bad\'"></div>' : '') +
      '<div class="thead"><h1 class="title">' + D.esc(c.cn || '') + ' 天赋</h1>' +
      '<span class="pts">剩余 <b>' + Math.max(0, r.totalPoints - E.spent(tstate.state, trees)) + '</b>/' + r.totalPoints + '</span>' +
      '<input type="search" id="tq" class="tqs" placeholder="搜天赋名" value="' + D.esc(tstate.q) + '">' +
      '<button class="ghost" id="cmp" aria-pressed="false">与经典旧世对比</button>' +
      '<span class="dim mono" id="sel"></span></div>' +
      '<div class="tlegend"><span><i class="lg added"></i>新增</span><span><i class="lg modified"></i>改动</span>' +
      '<span><i class="lg moved"></i>换层</span><span><i class="lg unchanged"></i>未变</span></div>' +
      '<div class="ttabs">' + trees.map(function (t, i) {
        return '<button data-tab="' + i + '" class="' + (i === tstate.active ? 'on' : '') + '"' +
          treeAltTip(t) + '>' + treeName(t) + '</button>';
      }).join('') + '</div>' + body +
      '<div class="cmpbox" id="cmpbox" style="display:none"></div>' +
      '<div class="tfoot"><label class="dim">等级 <span class="mono" id="lvv">60</span></label>' +
      '<input type="range" min="10" max="60" value="60" id="lv" aria-label="按角色等级筛选可用天赋">' +
      '<button id="mode" class="ghost">' + (tstate.mode === 'add' ? '当前：加点' : '当前：减点') + '</button>' +
      '<button id="copy" class="ghost">复制方案</button><button id="share" class="ghost">分享链接</button>' +
      '<button id="reset" class="ghost">重置</button>' +
      '<span class="sp">' + D.esc(E.describe(trees, tstate.state)) + '</span></div></div>');
    bindTalent();
    drawLinks();
    var cbtn = el('cmp');
    if (cbtn) cbtn.onclick = toggleCompare;
  }
  function renderPool(pool) {
    if (!pool.length) return '<div class="empty">这个职业还没有天赋条目。</div>';
    return '<div style="padding:16px"><h3 style="margin-bottom:8px">天赋名 ' + pool.length + ' 条</h3>' +
      '<div class="pool">' + pool.map(function (p) {
        return '<span class="term" data-copy="' + D.esc(p.nameCn) + '">' + D.esc(p.nameCn) + '</span>';
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
      var bg = specArt(tstate.art, tstate.classId, ti);
      return '<div class="tree t' + (ti % 3) + ' ' + (document.body.clientWidth < 861 && ti !== tstate.active ? 'hide' : '') + '" data-tree="' + ti + '">' +
        (bg ? '<span class="tbg" aria-hidden="true" style="background-image:url(' + bg + ')"></span>' : '') +
        '<h3><span' + treeAltTip(t) + '>' + treeName(t) + ' <span class="dim mono">' + D.esc(t.nameEn || '') + '</span></span>' +
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
    var pct = max ? Math.round(score / max * 100) : 0;
    return '<div class="card mcard"><div class="crow">' +
      '<div class="ic lg">' + (window.Glyph ? Glyph.classTile(c.id, c.cn, c.iconKey, 'lg') : D.esc((c.cn || '?').slice(0, 1))) + '</div>' +
      '<div style="flex:1"><h2 style="margin:0">' + D.esc(c.cn) + ' <span class="dim mono">' + D.esc(c.en || '') + '</span></h2>' +
      '<div class="mbar"><i style="width:' + pct + '%"></i></div>' +
      '<div class="dim">匹配度 ' + pct + '%（' + score + ' 分，本题库最高 ' + max + ' 分）</div></div></div>' +
      (reasons.length ? '<ul class="list">' + reasons.map(function (x) { return '<li>' + D.esc(x) + '</li>'; }).join('') + '</ul>' : '') +
      /* 2026-10-12 站主决定：这一页只留问答结果，讲本站天赋名核对进度的那句已删，出处见溯源页。 */
      '<a class="btn" href="talent.html?c=' + c.id + '">看这个职业的天赋树 →</a></div>';
  }
  function drawChooser() {
    var total = cstate.qs.length, done = cstate.step >= total;
    var answered = Object.keys(cstate.answers).length;
    var live = chooserScores();
    var ids = cstate.classes.map(function (c) { return c.id; });
    var maxScore = Math.max.apply(null, ids.map(function (i) { return live.score[i]; }).concat([0]));
    var lead = maxScore ? ids.filter(function (i) { return live.score[i] === maxScore; }) : [];
    var pool = (answered && maxScore) ? ids.filter(function (i) { return live.score[i] > 0; }) : ids;
    /* 这一页的内容就是"9 个职业被 7 题逐步筛掉"，所以把 9 个职业一直摆在屏幕上：
       答一题，掉出候选的变暗、领先的转金。进度不再是细条，而是"还剩几个候选"。 */
    function board() {
      var order = ids.slice().sort(function (a, b) { return live.score[b] - live.score[a]; });
      return '<aside class="cboard"><div class="mline">还在候选 ' +
        '<b>' + pool.length + '</b> 个</div><div class="ctiles">' +
        order.map(function (id) {
          var c = cstate.classes.filter(function (x) { return x.id === id; })[0] || { id: id, cn: id };
          var s = live.score[id];
          return '<div class="ctile' + (answered && !s ? ' off' : '') +
            (lead.indexOf(id) >= 0 && answered ? ' lead' : '') + '"><span class="ci">' +
            (window.Glyph ? Glyph.classTile(id, c.cn, c.iconKey, '') : D.esc((c.cn || '?').slice(0, 1))) +
            '</span><b>' + D.esc(c.cn) + '</b><em class="mono">' + s + '</em>' +
            '<span class="en dim">' + D.esc(c.en || '') + '</span>' +
            '<i class="cs"><s style="width:' + (maxScore ? Math.round(s / maxScore * 100) : 0) + '%"></s></i>' +
            '</div>';
        }).join('') + '</div></aside>';
    }
    var progress = '<div class="card cstep"><div class="crow">' +
      '<span class="dim mono">第 ' + Math.min(cstate.step + 1, total) + ' / ' + total + ' 题</span>' +
      '<span class="sp"></span><button class="ghost" id="creset">重新开始</button></div>' +
      '<div class="cov">' + cstate.qs.map(function (q, i) {
        var w = (100 / total).toFixed(2) + '%';
        var cls = cstate.answers[q.id] ? (i < cstate.step ? 'L0' : 'L1') : 'L3';
        return '<i class="' + cls + '" style="width:' + w + '" title="' + D.esc(q.q) + '"></i>';
      }).join('') + '</div></div>';
    var head = '<div class="card chead"><div class="mline">7 题 · 9 职业</div>' +
      '<h1 class="pt">选职业问答</h1></div>';
    var body;
    if (done) {
      var s = live, ranked = ids.slice().sort(function (a, b) { return s.score[b] - s.score[a]; });
      var max = Math.max.apply(null, ranked.map(function (id) { return s.score[id]; }).concat([1]));
      var byId = {};
      cstate.classes.forEach(function (c) { byId[c.id] = c; });
      var top = ranked.slice(0, 3);
      var tied = ranked.filter(function (id) { return s.score[id] === max; });
      // 这句不是"说明文案"，是红线要求的标注：排行必须写清是本站按玩法取向整理的，不冒充强度结论
      body = '<div class="banner gray">下面是按你选的玩法归类的候选，<b>不是强度排行，也不代表哪个职业更强</b>。' +
        (tied.length > 3 ? '这次并列第一有 ' + tied.length + ' 个职业，都算同样合适。' : '') + '</div>' +
        top.map(function (id) { return classCard(byId[id] || { id: id, cn: id }, s.score[id], max, s.reasons[id] || []); }).join('') +
        '<div class="card"><h2>其余候选</h2><div class="pool">' +
        ranked.filter(function (id) { return top.indexOf(id) < 0; }).map(function (id) {
          return '<span class="term">' + D.esc((byId[id] || {}).cn || id) + ' ' + s.score[id] + ' 分</span>';
        }).join('') + '</div></div>';
    } else {
      var q = cstate.qs[cstate.step];
      body = '<div class="card cq"><div class="mline">已答 ' + answered + ' 题 · 还剩 ' +
        pool.length + ' 个候选</div><h2>' + D.esc(q.q) + '</h2>' +
        (q.hint ? '<p class="dim">' + D.esc(q.hint) + '</p>' : '') +
        '<div class="qopts">' + q.options.map(function (o, i) {
          return '<button class="qopt' + (cstate.answers[q.id] === o.id ? ' on' : '') + '" data-o="' + o.id + '">' +
            '<span class="qi mono">' + 'ABC'.slice(i, i + 1) + '</span>' + D.esc(o.label) + '</button>';
        }).join('') + '</div>' +
        '<div class="crow" style="margin-top:10px">' +
        (cstate.step ? '<button class="ghost" id="cprev">← 上一题</button><span class="sp"></span>' : '') +
        '</div></div>';
    }
    set(head + progress + '<div class="csplit">' + body + board() + '</div>');
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
        return '<div class="tlrow tl-' + state + '"><i class="tldot" aria-hidden="true"></i><div class="tl-date"><b class="mono">' + D.esc(x.date) + '</b>' +
          '<span class="dim">' + D.esc(days) + '</span></div><div class="tl-body">' +
          '<div class="tl-h">' + D.esc(x.title) + ' <span class="tag">' + state + '</span></div>' +
          '<p class="dim">' + D.esc(x.what) + '</p></div></div>';
      }).join('');
      // 轴的意义是"现在站在哪"：在第一个待来之前钉一格今天，没有待来就钉在末尾
      var nowRow = '<div class="tlrow tl-now"><i class="tldot now" aria-hidden="true"></i>' +
        '<div class="tl-body"><b class="mono">今天</b></div></div>';
      if (rows.indexOf('tl-待来') >= 0) rows = rows.replace('<div class="tlrow tl-待来"', nowRow + '<div class="tlrow tl-待来"');
      else rows += nowRow;
      /* 2026-10-12 站主决定：这一页只留时间点与两个官方日期本身，
         讲来源标注与分级口径的那两句已删，出处集中在溯源页（provenance.html）。 */
      set('<div class="card"><h1 class="pt">上线与 Beta 时间表</h1>' +
        '<div class="stats"><div class="stat"><b>' + items.length + '</b>个时间点</div>' +
        '<div class="stat"><b>' + done + '</b>已过</div><div class="stat"><b>' + upcoming + '</b>待来</div>' +
        '<div class="stat"><b>' + (items.length - done - upcoming) + '</b>日期未定</div></div></div>' +
        (tz ? '<div class="card"><h2>上线日期为什么有两个说法</h2>' +
          '<p class="dim">' + D.esc(tz.cn) + '<br>' + D.esc(tz.en) + '</p>' +
          '<p>' + D.esc(tz.ours) + '</p></div>' : '') +
        '<div class="tl">' + rows + '</div>');
    }).catch(fail);
  }

  /* ---------- 技能四态与专精名的用表（技能书页与职业页共用这一份）---------- */
  var AB_STATE = { new: '新增', changed: '改动', renamed: '改名', removed: '移除' };
  var AB_KIND = { talent: '天赋', skill: '技能', pet: '宠物技能' };
  var AB_SPEC = { 'beast-mastery': '野兽控制', marksmanship: '射击', survival: '生存', feral: '野性战斗',
    restoration: '恢复', balance: '平衡', discipline: '戒律', holy: '神圣', shadow: '暗影',
    arms: '武器', fury: '狂怒', protection: '防护' };
  /* ---------- 职业页（每职业一页 · 2026-10-12 补）----------
     任务书 docs/PLAN-classes-and-nav-2026-10-12.md 第二节。版式按设计稿 3.2 节那四块
     （页首职业带 300px + 右侧 158px 立绘框 → 三系专精卡 → 左「这一职业有什么」右「技能变化」两栏
     → 底部三个出口），内容一律从 src/data 现取，一条都不写死：
       职业名 / 英文原名 / 分级 ← classes.json，职业色 ← glyph.js 那份职业色表；
       三系、节点数、两源叫法 ← data/talents/<职业>；
       官方中文整句 ← abilities.json（按职业过滤，只有官方句子里出现的名字才收）；
       改动类别与计数 ← changes.json 按职业聚合（只列名称与类别，不复制逐字前后对照）；
       可选种族与阵营 ← races.json 的职业矩阵（用正式中文名，不抄稿子里的简称）。
     稿子「职业概览」六行里除了可选种族，其余五条（战斗定位 / 核心资源 / 护甲类型 / 可用武器 /
     团队职责）是写死的常识描述，我们没有能核对的官方中文来源，这一页就不显示，
     缺的那几行进本页的未确认清单——不把别人的描述句当数据搬进来。 */
  var CL_STATE = { added: '新增', modified: '改动', removed: '移除', unchanged: '未变' };
  var CL_ORDER = ['added', 'modified', 'removed', 'unchanged'];
  var CL_KIND = { talent: '天赋', spell: '技能' };
  function classPage() {
    Promise.all([D.load('data/classes.json'), D.load('data/scale.json'),
      D.load('data/abilities.json'), D.load('data/changes.json'), D.load('data/races.json'),
      D.load('data/art.json').catch(function () { return {}; })])
      .then(function (rs) {
        var CLS = rs[0].classes || [], SC = rs[1].scale || {}, AB = rs[2] || { items: [], meta: {} };
        var CHR = rs[3] || {}, CH = CHR.items || [], RC = rs[4] || {}, ART = rs[5] || {};
        var byId = {}; CLS.forEach(function (c) { byId[c.id] = c; });
        var want = urlQ('c');
        var f = { c: byId[want] ? want : (CLS[0] || {}).id, s: '' };

        function facName(id) {
          var hit = (RC.factions || []).filter(function (x) { return x.id === id; })[0];
          return hit ? hit.nameCn : id;
        }
        /* 可选种族：矩阵里存的是职业 id，展示用 races.json 的正式中文名；
           天裔在两张表里各一行，官方给的名字本来就带子族（塑风者天裔 / 高阶会天裔），照官方写法。 */
        function racesOf(cid) {
          var out = { horde: [], alliance: [], skyborne: false };
          (RC.races || []).forEach(function (r) {
            if ((r.classes || []).indexOf(cid) < 0) return;
            var nm = (r.subgroup && r.subgroup.nameCn) || r.nameCn;
            if (out[r.faction]) out[r.faction].push(nm); else out[r.faction] = [nm];
            if (String(r.id).indexOf('skyborne') === 0) out.skyborne = true;
          });
          return out;
        }
        function chListOf(cid, tree) {
          return CH.filter(function (x) { return x.classId === cid && (!tree || x.tree === tree); });
        }
        function abListOf(cid) {
          return (AB.items || []).filter(function (x) { return x.classId === cid; });
        }
        function loadInto(cid, done) {
          D.load('data/talents/' + cid + '.json').then(function (T) { done(T); }).catch(function () { done(null); });
        }
        function openClass(cid) {
          f.c = cid; f.s = '';
          try { history.replaceState(null, '', 'classes.html?c=' + encodeURIComponent(cid)); } catch (e) { /* 演示环境不支持就不改地址 */ }
          loadInto(cid, draw);
        }
        function draw(T) {
          var c = byId[f.c] || {}, trees = (T && T.trees) || [], st = (T && T.stats) || {};
          /* 名称核对数与分歧数：stats 里只有节点级分歧，系名的两个叫法记在 trees[] 自己身上
             （潜行者「奇袭 / 刺杀」、萨满「元素战斗 / 元素」、牧师「暗影 / 暗影魔法」），
             所以这两个数按节点与系各现数一遍，不拿 classes.json 那个粗数凑。 */
          var tcnt = 0, vcnt = 0;
          trees.forEach(function (t) {
            (t.nodes || []).forEach(function (n) { tcnt++; if (n.nameVerified) vcnt++; });
          });
          if (!tcnt) tcnt = st.nodes || 0;
          var altTrees = trees.filter(function (t) { return t.nameConflict && t.nameAlt; });
          var col = (window.Glyph && Glyph.color) ? (Glyph.color[c.id] || '') : '';
          var art = (ART.classes || {})[c.id] || '';
          var all = chListOf(c.id, ''), abs = abListOf(c.id);
          var abm = {}; abs.forEach(function (x) { if (x.name && !abm[x.name]) abm[x.name] = x; });
          var bc = ((CHR.meta || {}).byClass || []).filter(function (x) { return x.classId === c.id; })[0] || {};
          var rank = (SC.classRank || []).filter(function (x) { return x.classId === c.id; })[0] || {};
          var R3 = racesOf(c.id);

          /* 2026-10-12 站主决定：职业页只留职业名与条数——讲数据出处（客户端解包 / 官方中文稿）
             与素材来源的角标、备注那几段已删，出处集中在溯源页（provenance.html）。 */
          // artOf 是 home() 里的局部函数，这里不能用它——直接取，取不到退回这一职业第一系的原画
          var banner = ((ART.classBanners || {})[c.id]) || specArt(ART, c.id, 0);
          var hero = '<section class="dhero clhero"' + (col ? ' style="--cl:' + col + '"' : '') + '>' +
            (banner ? '<img src="' + D.esc(banner) + '" alt="" loading="lazy">' : '') +
            '<span class="dx"></span><div class="db"><div class="clt">' +
            '<div class="kicker">' + D.esc('CLASS · ' + String(c.en || c.id || '').toUpperCase()) + '</div>' +
            '<h1 class="pt">' + D.esc(c.cn || '未定名') +
            (c.en ? '<span class="clen">' + D.esc(c.en) + '</span>' : '') + '</h1>' +
            '<div class="clline">三系 <b>' + trees.length + '</b> · 天赋节点 <b>' + tcnt +
            '</b> · 改动 <b>' + (bc.all || 0) + '</b> 条 · 技能说明 <b>' + abs.length + '</b> 条</div>' +
            '</div><div class="chart">' +
            (window.Glyph ? Glyph.classTile(c.id, c.cn, c.iconKey, 'lg') : '') +
            (art ? '<img src="' + D.esc(art) + '" alt="' + D.esc((c.cn || '') + '的职业立绘') +
              '" loading="lazy" onerror="this.className=\'bad\'">' : '') +
            '</div></div></section>';

          var bar = '<div class="card" style="padding-bottom:0"><div class="classbar" role="group" aria-label="换一个职业">' +
            CLS.map(function (x) {
              return '<button type="button" class="cls' + (x.id === f.c ? ' on' : '') + '" data-c="' +
                D.esc(x.id) + '" style="min-width:78px" aria-pressed="' + (x.id === f.c ? 'true' : 'false') + '">' +
                '<div class="ic">' + (window.Glyph ? Glyph.classTile(x.id, x.cn, x.iconKey)
                  : D.esc((x.cn || '?').slice(0, 1))) + '</div><div class="n">' + D.esc(x.cn) + '</div></button>';
            }).join('') + '</div></div>';

          /* 三系卡：选中那一系就把右边的技能变化收到这一系，再点一次回到三系都列。
             系名用官方定名，另一来源的叫法走红框悬停（与天赋页同一套符号，见 treeName / treeAltTip）。 */
          var spec = trees.length ? '<section class="spec3" aria-label="这一职业的三系专精">' +
            trees.map(function (t, ti) {
              var on = f.s === t.nameCn;
              return '<button type="button" class="spec plate' + (on ? ' on' : '') + '" data-s="' +
                D.esc(t.nameCn) + '" aria-pressed="' + (on ? 'true' : 'false') + '"' + treeAltTip(t) + '>' +
                (specArt(ART, c.id, ti) ? '<span class="sbg" aria-hidden="true" style="background-image:url(' +
                  specArt(ART, c.id, ti) + ')"></span>' : '') +
                '<b>' + treeName(t) + '</b><span>' + (t.nodes || []).length + ' 个节点</span>' +
                '<span class="spnote">' + (on ? '已只看这一系，再点一次看全部' : '只看这一系的改动') + '</span>' +
                '</button>';
            }).join('') + '</section>' : '';

          function kv(k, v, ex) {
            return '<div class="kv"><span>' + k + '</span><b>' + v + (ex ? ' ' + ex : '') + '</b></div>';
          }
          var raceChips = ['horde', 'alliance'].map(function (fid) {
            var list = R3[fid] || [];
            if (!list.length) return '';
            return '<div class="racerow"><b>' + D.esc(facName(fid)) + '</b>' +
              '<span class="chips">' + list.map(function (n) {
                return '<span class="tag">' + D.esc(n) + '</span>';
              }).join('') + '</span><a href="races.html">矩阵 →</a></div>';
          }).join('');
          /* 天裔能选几个职业有两份说法：这是"同一处两个数都留"的数据分歧（仓库根红线要求标注），
             不是本页的备注文案，所以这一行留着；它前面那段带分级徽标的说明段已按站主决定删掉。 */
          var skyCfl = R3.skyborne && (RC.conflicts || []).length
            ? '<p class="conf">天裔能选几个职业，两份说法还没对上（同页两张矩阵表与导语不一致），' +
              '<a href="races.html">种族页两个都留着</a></p>' : '';
          var have = '<section class="card"><h2>这一职业有什么</h2>' +
            kv('职业中文名', D.esc(c.cn || '') + (c.en ? ' / ' + D.esc(c.en) : '')) +
            kv('三系', trees.map(function (t) { return treeName(t); }).join(' · ') || '待补') +
            kv('天赋节点', tcnt + ' 个' +
              '<a href="talent.html?c=' + encodeURIComponent(c.id) + '">打开计算器 →</a>') +
            /* 这四行是数（核对上的条数、两源分歧的条数、说明句条数、本站覆盖度），不是说明文案，
               所以留在页面上；跟在它们后面的分级徽标、来源按钮与"这是本站自己排的"那段 note
               按 2026-10-12 站主决定已删——只有"不是强度排行"那几个字以行内标签的形式留着（红线要求）。 */
            kv('名称与官网中文一致', vcnt + ' / ' + tcnt) +
            kv('两个来源叫法不同', ((st.nameConflict || 0) +
              (altTrees.length ? ' 个节点、' + altTrees.length + ' 个系名' : ' 个节点')) + '（两个都留着）') +
            kv('技能说明', abs.length ? abs.length + ' 条' : '<span class="dim">还没有</span>') +
            kv('改动条目', (bc.all || 0) + ' 条' + (bc.changed ? '（其中 ' + bc.changed + ' 条与经典旧世不同）' : '')) +
            kv('资料完整度', (rank.share !== undefined ? rank.share + '%' : '未排') +
              (rank.place ? ' · 第 ' + rank.place + ' 位' : '') +
              '<span class="dim">（本站整理，不是强度排行）</span>') +
            (raceChips ? '<h3 class="rdh">谁可以选这一职业</h3>' + raceChips + skyCfl : '') +
            '</section>';

          var shown = chListOf(c.id, f.s);
          var grp = {};
          shown.forEach(function (x) {
            var k = CL_STATE[x.changeKind] ? x.changeKind : 'other';
            (grp[k] = grp[k] || []).push(x);
          });
          var order = CL_ORDER.filter(function (k) { return grp[k]; });
          if (grp.other) order.push('other');
          var listHtml = shown.length ? order.map(function (k) {
            var rows = grp[k];
            return '<div class="lgrp"><b>' + (k === 'other' ? '其它说法' : CL_STATE[k]) + '</b>' +
              '<span class="dim">' + rows.length + ' 条</span></div>' +
              '<div class="scrollx"><table class="entab chtab"><thead><tr><th class="ich">名称</th>' +
              '<th>类别</th><th>哪一系</th></tr></thead><tbody>' +
              rows.map(function (x, i) {
                var ab = abm[x.nameCn];
                return '<tr><td class="ich">' + iconCell(x.iconKey, x.id || x.nameCn, x.nameCn) +
                  '<b>' + D.esc(x.nameCn || '未命名') + '</b>' +
                  (x.maxRank ? '<span class="dim"> · 最多 ' + D.esc(x.maxRank) + ' 层</span>' : '') +
                  (ab ? '<span class="quote">' + D.esc(ab.quote) + '</span>' : '') + '</td>' +
                  '<td>' + (CL_KIND[x.kind] || '其他') + (k === 'other' && x.changeCn
                    ? '<br><span class="tag">' + D.esc(x.changeCn) + '</span>' : '') + '</td>' +
                  '<td>' + (x.tree ? D.esc(x.tree) : '<span class="dim">未归系</span>') + '</td></tr>';
              }).join('') + '</tbody></table></div>';
          }).join('') : '<div class="empty">这一系没有改动条目。</div>';
          var chg = '<section class="card"><h2>技能变化' +
            (f.s ? '<span class="dim mono"> 只看 ' + D.esc(f.s) + '</span>'
              : '<span class="dim mono"> 三系都列</span>') +
            '<span class="dim mono"> · ' + shown.length + ' 条</span></h2>' +
            '<div class="chgs">' + listHtml + '</div>' +
            (abs.length ? '<div class="chipsrow"><a href="skills.html">这一职业在技能书里的条目 →</a></div>' : '') +
            '</section>';

          var tools = '<section class="card"><h2>接着看这一职业</h2><div class="tools6">' +
            [['talent.html?c=' + encodeURIComponent(c.id), '天赋计算器', tcnt + ' 个节点 · 三系天赋树'],
            ['skills.html', '技能书', abs.length + ' 条技能说明（这一职业）'],
            ['chooser.html', '玩法问答', '答完题才知道这一职业合不合手']].map(function (t) {
              return '<a class="tool plate" href="' + t[0] + '">' +
                '<span class="tico"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" ' +
                'stroke-width="1.8" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="1"/>' +
                '<path d="M9 12h6M12 9v6"/></svg></span>' +
                '<h3>' + t[1] + '</h3>' +
                '<span class="foot"><em>' + t[2] + '</em><i>进入 →</i></span></a>';
            }).join('') + '</div></section>';

          /* 2026-10-12 用户实拍后决定：这一页不再挂「本页还没确认的」那张卡。
             缺什么仍然如实写在数据里，集中到溯源页与动态页看；
             这一页只留"层级门槛没实测"这类会误导加点的口径，收进三系卡下面一句话。 */
          set(hero + bar + spec + '<p class="note">三系的格子只按客户端里的位置摆，' +
            '第几层要点满多少还没在正式服实测，所以不做「够点才能点下一层」的判定。</p>' +
            '<div class="two">' + have + chg + '</div>' + tools);
          Array.prototype.forEach.call(document.querySelectorAll('.cls[data-c]'), function (b) {
            b.onclick = function () { if (b.dataset.c !== f.c) openClass(b.dataset.c); };
          });
          Array.prototype.forEach.call(document.querySelectorAll('.spec[data-s]'), function (b) {
            b.onclick = function () { f.s = f.s === b.dataset.s ? '' : b.dataset.s; loadInto(f.c, draw); };
          });
        }
        loadInto(f.c, draw);
      }).catch(fail);
  }

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
            '<div class="scrollx"><table class="entab"><thead><tr><th class="ich">图标</th><th>中文名</th><th>英文原名</th><th>类型</th><th></th></tr></thead><tbody>' +
            g.rows.map(function (x) {
              return '<tr><td class="ich">' + iconCell(ICONS[iconKeyOf(x)], x.id, x.cn) + '</td>' +
                '<td>' + D.hl(x.cn, f.q) + '</td>' +
                '<td class="en">' + (x.en ? D.hl(x.en, f.q) : '<span class="dim">待补</span>') + '</td>' +
                '<td>' + (KIND[x.kind] || x.kind) + '</td>' +
                '<td class="act"><button class="ghost" data-copy="' + D.esc(x.cn + (x.en ? ' / ' + x.en : '')) + '">复制</button></td></tr>';
            }).join('') + '</tbody></table></div>';
        }).join('') : '<div class="empty">没有匹配条目，试试放宽筛选。</div>';
        el('cnt').textContent = list.length + ' / ' + items.length + ' 条 · 有图标 ' + withIcon + ' 条';
        drawAbilities();
      }
      function drawAbilities() {
        var all = ab.items || [];
        var list = all.filter(function (x) { return !f.c || x.classId === f.c; });
        var byState = { new: [], changed: [], renamed: [], removed: [] };
        list.forEach(function (x) { (byState[x.state] || (byState[x.state] = [])).push(x); });
        var cnName = {};
        cls.forEach(function (c) { cnName[c.id] = c.cn; });
        /* 2026-10-12 站主决定：这一页只留词条与原句，讲"原句出自哪份稿子、为什么没有未变这一档"
           与来源核对日期的那几段已删，出处集中在溯源页（provenance.html）。 */
        if (!list.length) {
          // 空态要说清"为什么空"，那句话取自 abilities.json 的「没收到的」，不在代码里另写一遍
          var cname = ((cls.filter(function (x) { return x.id === f.c; })[0] || {}).cn) || '';
          var why = ((ab.meta || {}).notCollected || []).filter(function (s) {
            return cname && String(s).indexOf(cname) >= 0;
          })[0] || '';
          el('abtbl').innerHTML = '<div class="empty">' + D.esc(why ||
            '这个职业还没有官方中文深度解析稿，四态无从谈起。') + '</div>';
          return;
        }
        el('abtbl').innerHTML = Object.keys(byState).map(function (st) {
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
        }).join('');
        el('abcnt').textContent = ' · ' + list.length + ' 条';
        Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function (b) {
          b.onclick = function () { D.copy(b.dataset.copy); };
        });
      }
      set('<div class="card"><h1 class="pt">技能书</h1>' +
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
  function dunRoute(arr) {
    if (!arr || !arr.length) return '';
    return '<ul class="list">' + arr.map(function (r) {
      var o = r && typeof r === 'object' ? r : {};
      var txt = typeof r === 'string' ? r : (r.label || r.name || r.text || '');
      var at = o.at || '';
      return '<li>' + D.esc(txt || '—') +
        (at ? ' <span class="dim mono">' + D.esc(at) + '</span>' : '') + '</li>';
    }).join('') + '</ul>';
  }
  function dunLoot(x) {
    var bosses = x.bosses || [], drops = x.drops || [];
    if (!bosses.length) return '<p class="dim">这座本还没有首领名单。</p>';
    return '<ul class="bosslist">' + bosses.map(function (b) {
      var mine = drops.filter(function (y) { return y.bossId === b.id; });
      return '<li><div class="bh">' + window.Glyph.bossFace(b.id, b.nameCn, b.portrait, 'sm') +
        '<b>' + D.esc(b.nameCn) + '</b>' +
        (mine.length ? '<span class="dim">' + mine.length + ' 件掉落</span>' : '<span class="dim">掉落待补</span>') + '</div>' +
        (mine.length ? '<div class="loot">' + mine.map(function (y) {
          return '<span class="loot-i">' + iconCell(y.iconKey, y.itemId, y.nameCn, 1) +
            D.esc(y.nameCn) + '<span class="dim mono">#' + D.esc(y.itemId) + '</span></span>';
        }).join('') + '</div>' : '') + '</li>';
    }).join('') + '</ul>';
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
    Promise.all([D.load('data/dungeons.json'), D.load('data/art.json').catch(function () { return {}; }),
      D.load('data/queue.json').catch(function () { return {}; })])
      .then(function (rs) {
      var d = rs[0], ART = rs[1] || {}, QU = rs[2] || {};
      var all = [].concat(d.newDungeons || [], d.classicDungeons || [], d.raids || []);
      var nb = all.reduce(function (s, x) { return s + (x.bosses || []).length; }, 0);
      var nd = all.reduce(function (s, x) { return s + (x.drops || []).length; }, 0);
      var nParty = all.filter(function (x) { return x.partySize; }).length;
      var nTwo = all.filter(function (x) { return x.levelRangeClient || x.partySizeAlt || x.nameEnClient; }).length;
        /* 下面这几段 .conf 不是"备注文案"，是红线要求的两源分歧标注：同一座本的等级区间、
           排队人数、英文原名在官方公告 / 参考站 / 客户端排队表里说法不一致，两个都得摆出来。
           2026-10-12 撤掉的是卡片上的分级徽标与逐条来源，不是这些分歧本身。 */
        function rangeNote(x) {
          var cli = x.levelRangeClient, alt = x.levelRangeAlt;
          if (!cli && !alt) return '';
          if (cli && alt && cli === alt) {
            return '<div class="conf">等级区间两说：本站取「' + D.esc(x.levelRange) + '」（官方公告），'
              + '客户端的队伍查找器与副本卡片都写「' + D.esc(cli) + '」，待定稿</div>';
          }
          if (cli && alt) {
            return '<div class="conf">等级区间有三种说法：本站取「' + D.esc(x.levelRange || '还没核') + '」（官方公告），'
              + '另一份资料写「' + D.esc(alt) + '」，客户端的队伍查找器写「' + D.esc(cli) + '」，都留着待定稿</div>';
          }
          if (cli) {
            return '<div class="conf">等级区间两说：本站取「' + D.esc(x.levelRange || '还没核') + '」，'
              + '客户端的队伍查找器写「' + D.esc(cli) + '」，两个都留着</div>';
          }
          return '<div class="conf">等级区间两说：本站取「' + D.esc(x.levelRange) + '」（官方公告），'
            + '另一份资料写「' + D.esc(alt) + '」，待定稿</div>';
        }
        function card(x) {
          var banner = window.Glyph ? Glyph.dungeonBanner(x.id,
            x.nameCn || x.nameEn || '未定名',
            { kind: x.kind, sub: x.zoneCn || ((x.nameCn && x.nameEn) ? x.nameEn : ''),
              art: x.art || (ART.dungeons || {})[x.id] || null,
              seal: x.kind === 'new' ? '新' : null,
              range: x.levelRange ? x.levelRange + ' 级' : null }) : '';
          return '<div class="dcard2">' + banner +
            '<div class="dmeta">' +
            '<span>' + ((x.bosses || []).length || '待补') + ' 个首领</span>' +
            '<span>' + ((x.drops || []).length ? (x.drops || []).length + ' 件掉落' : '掉落待补') + '</span>' +
            (x.partySize ? '<span>一次 ' + x.partySize + ' 人</span>' : '') +
            (x.levelRange || x.levelRangeClient ? '' : '<span class="dim">等级区间待实测</span>') +
            (x.nameCn ? '' : '<span class="dim">中文定名未公布</span>') + '</div>' +
            rangeNote(x) +
            (x.partySizeAlt ? '<div class="conf">客户端的队伍查找器里它另有一条 ' + x.partySizeAlt +
              ' 人的排队条目，与本站的 ' + x.partySize + ' 人并列，是不是同一个本两种规模要实测</div>' : '') +
            (x.nameEnClient ? '<div class="conf">英文原名两说：本站写「' + D.esc(x.nameEn) + '」，'
              + '客户端写「' + D.esc(x.nameEnClient) + '」</div>' : '') +
            (x.nameCnConflict ? '<div class="conf">译名冲突：官方写「' + D.esc(x.nameCn) + '」，转载写作「' +
              D.esc(x.nameCnConflict) + '」，待定稿</div>' : '') +
            (!x.clientActivityId ? '<div class="note">客户端的队伍查找器里还没有这座本，'
              + '所以现在还不能排队进去，名单与掉落以正式开放后为准。</div>' : '') +
            '<button class="ghost wide" data-d="' + D.esc(x.id) + '">速览首领与掉落</button>' +
            '<div class="drawer" id="d-' + D.esc(x.id) + '" style="display:none">' +
            '<h3>首领与掉落</h3>' + dunLoot(x) +
            '<h3>路线</h3>' + (dunRoute(x.route) || '<p class="dim">待实测。</p>') + '</div></div>';
        }
        function bandBlock(title, sub, rows) {
          if (!rows.length) return '';
          return '<div class="band"><b>' + title + '</b>' + (sub ? '<span class="dim">' + sub + '</span>' : '') +
            '<span class="dim mono">' + rows.length + ' 座</span></div>' +
            '<div class="dgrid">' + rows.map(card).join('') + '</div>';
        }
        // 客户端的队伍查找器里现在能排到、本站还没有首领与掉落名单的那些：按名字归并，
        // 同一个本在客户端里挂两条（比如两种规模）只说一次，免得看着像两座本
        function queueBand() {
          var rows = (QU.items || []).filter(function (x) { return !x.matchedId; });
          if (!rows.length) return '';
          var g = {}, order = [];
          rows.forEach(function (x) {
            var k = x.nameEn;
            if (!g[k]) {
              g[k] = { nameEn: k, kind: x.kind, levelRange: x.levelRange, sizes: [], n: 0, prov: x.provenance || [] };
              order.push(k);
            }
            g[k].n += 1;
            if (x.partySize && g[k].sizes.indexOf(x.partySize) < 0) g[k].sizes.push(x.partySize);
          });
          var items = order.map(function (k) { return g[k]; });
          function table(list) {
            return '<table class="entab"><thead><tr><th>客户端里的名字</th><th>排队等级</th>'
              + '<th>一次几人</th><th>客户端记了几条</th></tr></thead><tbody>' +
              list.map(function (x) {
                return '<tr><td><b>' + D.esc(x.nameEn) + '</b><span class="dim">　中文定名未公布</span></td>'
                  + '<td class="mono">' + D.esc(x.levelRange) + ' 级</td>'
                  + '<td class="mono">' + (x.sizes.length ? x.sizes.join(' / ') + ' 人' : '未标') + '</td>'
                  + '<td class="mono">' + x.n + (x.n > 1
                    ? (x.sizes.length > 1 ? ' 条（同一座本两种人数）' : ' 条（同名两个入口，人数一样）') : '') + '</td></tr>';
              }).join('') + '</tbody></table>';
          }
          var dun = items.filter(function (x) { return x.kind === 'dungeon'; });
          var raid = items.filter(function (x) { return x.kind === 'raid'; });
          return '<div class="card" id="queue"><h2>能排到队、还没有名单的本</h2>'
            + (dun.length ? '<h3>地下城</h3>' + table(dun) : '')
            + (raid.length ? '<h3>团队副本</h3>' + table(raid) : '') + '</div>';
        }
        var list = (d.newDungeons || []).concat(d.classicDungeons || []);
        var body = DUN_BANDS.map(function (b, i) {
          var rows = list.filter(function (x) { return dunBand(x) === i; })
            .sort(function (p, q) { return parseInt(p.levelRange, 10) - parseInt(q.levelRange, 10); });
          return bandBlock(b[0] + (b[1] > 60 ? '–60' : '–' + b[1]) + ' 级', b[2], rows);
        }).join('') +
          bandBlock('区间未定', '', list.filter(function (x) { return dunBand(x) === null; })) +
          bandBlock('团队副本', '开放时间未定 · <a href="raids.html">团本那一页</a>', d.raids || []) +
          queueBand();
        /* 2026-10-12 站主决定：这一页只留本数、首领与掉落这些数——讲名单与区间从哪份解包来、
           为什么不写百分比的那两段说明已删，「世界里还没有数据的」那张缺口卡也撤了。
           但"哪几座有两种说法"必须留在首段：那是玩家决定信哪个数的依据。 */
        set('<div class="card"><h1 class="pt">副本手册</h1><p class="dim">共 ' + all.length + ' 座：' +
          (d.newDungeons || []).length + ' 座无限新增、' + (d.classicDungeons || []).length + ' 座经典本、' +
          (d.raids || []).length + ' 座团本，按十级一档分。首领 ' + nb + ' 个、掉落归属 ' + nd + ' 件。' +
          '一次几人取自客户端的队伍查找器（' + nParty + ' 座有数）。' +
          '另有 ' + nTwo + ' 座的等级区间或人数有两种说法，两个数都摆在卡片上，不做取舍。' +
          '掉落只回答"谁掉了什么"，不写概率。</p></div>' +
        body);
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

  /* ---------- 团本 ---------- */
  function raids() {
    Promise.all([D.load('data/queue.json').catch(function () { return {}; }), D.load('data/dungeons.json'),
      D.load('data/timeline.json').catch(function () { return { items: [] }; })])
      .then(function (rs) {
      var QU = rs[0] || {}, DG = rs[1], TL = (rs[2] || {}).items || [];
      var rows = (QU.items || []).filter(function (x) { return x.kind === 'raid'; });
      var claimed = DG.raids || [];
      var dunIds = {};
      [].concat(DG.newDungeons || [], DG.classicDungeons || []).forEach(function (x) { dunIds[x.id] = x; });
      var raidById = {};
      claimed.forEach(function (x) { raidById[x.id] = x; });
      // 同名两条归并成一座，条目数留着：说清到底是"两种规模"还是"两个入口"，不靠猜
      var grp = {}, order = [];
      rows.forEach(function (x) {
        if (!grp[x.nameEn]) { grp[x.nameEn] = []; order.push(x.nameEn); }
        grp[x.nameEn].push(x);
      });
      var names = order.map(function (k) {
        var list = grp[k], sizes = [], matched = null;
        list.forEach(function (x) {
          if (x.partySize && sizes.indexOf(x.partySize) < 0) sizes.push(x.partySize);
          if (x.matchedId && !matched) matched = x.matchedId;
        });
        sizes.sort(function (a, b) { return b - a; });
        var diffs = {};
        list.forEach(function (x) { diffs[String(x.partySize)] = 1; });
        return {
          nameEn: k, entries: list.length, sizes: sizes,
          multiSize: Object.keys(diffs).length > 1,
          levelRange: list[0].levelRange,
          matched: matched, matchedIn: matched ? (raidById[matched] ? 'raid' : (dunIds[matched] ? 'dungeon' : '')) : '',
          prov: list[0].provenance || []
        };
      });
      names.sort(function (a, b) {
        return (b.sizes[0] || 0) - (a.sizes[0] || 0) || a.nameEn.localeCompare(b.nameEn);
      });
      var both = names.filter(function (x) { return x.matchedIn === 'raid'; }).length;
      var f = { q: urlQ('q') || '' };

      function statusText(x) {
        if (x.matchedIn === 'raid') {
          var rr = raidById[x.matched];
          return '<span class="dim">已有这一座：</span><a href="dungeons.html?d=' + D.esc(x.matched) + '">'
            + D.esc((rr && (rr.nameCn || rr.nameEn)) || x.matched) + '</a>';
        }
        if (x.matchedIn === 'dungeon') {
          var dn = dunIds[x.matched];
          return '<span class="dim">按地下城收录：</span><a href="dungeons.html?d=' + D.esc(x.matched) + '">'
            + D.esc((dn && dn.nameCn) || x.matched) + '</a>';
        }
        return '<span class="dim">还没有名单</span>';
      }
      function sizeText(x) {
        return x.sizes.length ? x.sizes.join(' / ') + ' 人' : '未标';
      }
      function entryText(x) {
        if (x.entries < 2) return '1 条';
        return x.entries + ' 条（' + (x.multiSize ? '两种规模' : '同规模的两个入口') + '）';
      }
      function table(list) {
        return '<div class="scrollx"><table class="entab rtab"><thead><tr><th>客户端里的名字</th><th>排队等级</th>'
          + '<th>一次几人</th><th>排队条目</th><th>本站</th></tr></thead><tbody>' +
          list.map(function (x) {
            return '<tr><td><b>' + D.esc(x.nameEn) + '</b><span class="dim">　中文定名未公布</span></td>'
              + '<td class="mono">' + D.esc(x.levelRange) + ' 级</td>'
              + '<td class="mono">' + sizeText(x) + '</td>'
              + '<td class="mono">' + entryText(x) + '</td>'
              + '<td>' + statusText(x) + '</td></tr>';
          }).join('') + '</tbody></table></div>';
      }
      function draw() {
        var k = f.q.trim().toLowerCase();
        var shown = k ? names.filter(function (x) { return x.nameEn.toLowerCase().indexOf(k) >= 0; }) : names;
        /* 页首那一排团本卡按设计稿的版式件摆（稿子 docs/DESIGN-DOUBAO-2026-10-12.md 第 3.7 节）。
           卡上的图一律是本站自生成的氛围底图，不拿一张通用风景冒充某个团本的载入图。
           2026-10-12 站主决定：素材出处的"示意图"角标不再上内容页，说明集中在溯源页。
           名字与人数只用我们数据里有的说法：中文定名没公布就写英文原名，两说的两个数都摆。 */
        var HERO = 'img/gen/banner-cloudsea.webp';
        var CARD_ART = { 'barrow-deeps': 'img/gen/cavern-hall.webp', 'hyjal-summit': HERO,
          'onyxias-lair': 'img/gen/hero-ruins.webp' };
        var first = claimed[0] || {};
        var nextRaid = TL.filter(function (x) { return /团本|团队副本/.test(x.title || ''); })[0] || null;
        var beta = TL.filter(function (x) { return /国服 Beta 开启/.test(x.title || ''); })[0] || null;
        var launch = TL.filter(function (x) { return /国服/.test(x.title || '') && /上线/.test(x.title || ''); })[0] || null;
        var hero = '<section class="dhero" style="height:300px">' +
          '<img src="' + HERO + '" alt="" style="object-position:center 25%">' +
          '<span class="dx"></span>' +
          '<div class="db" style="padding-top:104px">' +
          '<div class="kicker">RAID</div>' +
          '<h1 class="pt" style="font-family:var(--font-display);font-size:46px;margin:10px 0 8px;color:#f2ead8">团队副本</h1>' +
          '<div style="font-size:15px;color:var(--txt-dim)">现在能排到 ' + names.length + ' 个团队条目。' +
          (nextRaid ? '新团本 <b style="color:var(--gold-hi);font-family:var(--font-mono)">' +
            D.esc(nextRaid.date.slice(5).replace('-', ' 月 ')) + ' 日</b> 开放。' : '') + '</div></div>' +
          '<div class="dstate"><i></i><b>' + (both ? '部分已有名单' : '全部未开放') + '</b></div></section>';
        var cards = '<section style="padding:36px 0 0"><div class="raidgrid">' + claimed.map(function (r, i) {
          var inClient = names.filter(function (x) { return x.matchedIn === 'raid' && x.matched === r.id; })[0];
          var sizes = [];
          if (r.sizeClaim) sizes.push(String(r.sizeClaim));
          if (inClient && inClient.sizes) inClient.sizes.forEach(function (s) {
            if (sizes.indexOf(String(s)) < 0) sizes.push(String(s));
          });
          return '<div class="raidcard"><div class="art">' +
            '<img src="' + (CARD_ART[r.id] || HERO) + '" alt="" loading="lazy">' +
            '<span class="sh"></span>' +
            '<span class="goldtag">' + (sizes.length ? D.esc(sizes[0]) + ' 人' : '人数未定') + '</span>' +
            '<span class="chip-open">' + ((r.bosses || []).length ? '名单已收录' : '未开放') + '</span>' +
            '<h3>' + D.esc(r.nameEn || r.nameCn || '未定名') + '</h3></div>' +
            '<div class="bd"><div class="facts">' +
            (sizes.length > 1 ? '人数两说：' + sizes.map(function (s) { return '<b>' + D.esc(s) + '</b>'; }).join(' / ') + ' 人'
              : sizes.length ? '进入人数 <b>' + D.esc(sizes[0]) + '</b> 人' : '人数未定') +
            '<br>' + (r.nameCn ? D.esc(r.nameCn) : '中文定名未公布') +
            '</div>' +
            '<div class="dashedbox">' + ((r.bosses || []).length ? '首领 ' + (r.bosses || []).length + ' 个已收录'
              : '首领名单待补') + '</div>' +
            // 红线：两份名单人数不一致时两个都摆着，不替玩家挑一个
            (sizes.length > 1 ? '<div class="conf">规模两说：另一份资料自报的人数与客户端排队条目写的不是一个数，'
              + '两个都摆着等定稿。</div>' : '') +
            (inClient ? '<a class="cta-cut" href="dungeons.html?d=' + D.esc(r.id) + '">看这一座的收录情况</a>'
              : '<a class="cta-cut" href="timeline.html">看上线时间表那一页</a>') +
            '</div></div>';
        }).join('') + '</div></section>';
        var bands = '';
        [40, 25, 20, 15, 10].forEach(function (n) {
          var pick = shown.filter(function (x) { return (x.sizes[0] || 0) === n; });
          if (!pick.length) return;
          bands += '<div class="band"><b>' + n + ' 人团队条目</b><span class="dim mono">' + pick.length + ' 座</span></div>' + table(pick);
        });
        var rest = shown.filter(function (x) { return [40, 25, 20, 15, 10].indexOf(x.sizes[0] || 0) < 0; });
        if (rest.length) bands += '<div class="band"><b>人数未标</b></div>' + table(rest);
        /* 三步带：日期全部取自 timeline.json（官方那条怎么写就怎么摆），
           不抄稿子写死的"12 月 10 日"——官方英文回顾给的是 12 月 9 日。 */
        function tlNode(x, col, lab) {
          if (!x) return '';
          return '<div class="node"><i style="background:' + col + '"></i><div>' +
            '<b>' + D.esc(lab || x.title) + '</b>' +
            '<span style="color:' + col + '">' + D.esc(x.date === '待定' || x.date === '择期' ? x.date : x.date) + '</span>' +
            '</div></div>';
        }
        var tl3 = '<section class="tl3" style="margin-top:32px">' +
          tlNode(beta, 'var(--ok)', '国服 Beta 进行中') +
          (beta && launch ? '<span class="link"></span>' : '') +
          tlNode(launch, 'var(--gold)') +
          (launch && nextRaid ? '<span class="link"></span>' : '') +
          tlNode(nextRaid, 'var(--warn)') + '</section>';
        /* 2026-10-12 站主决定：团本页只留两份名单本身的数与表——"这一页为什么是两份名单"、
           两份名单各是从哪来的、同一座挂两条该怎么读那几段说明已删，出处集中在溯源页。 */
        set(hero + cards + tl3 +
          '<div class="card">'
          + '<div class="stats"><div class="stat"><b>' + names.length + '</b>可排队的团队条目</div>'
          + '<div class="stat"><b>' + claimed.length + '</b>名单里的团本</div>'
          + '<div class="stat"><b>' + both + '</b>两边对得上</div>'
          + '<div class="stat"><b>' + claimed.filter(function (r) { return r.nameCn; }).length + '</b>有中文名</div></div>'
          + '</div>'
          + '<div class="card" id="client"><h2>能排到队的团队副本</h2>'
          + '<div class="field"><input type="search" id="rq" placeholder="按英文名筛，例如 Storm" aria-label="按英文名筛团本" value="'
          + D.esc(f.q) + '"><span class="dim mono" id="rcnt">' + shown.length + ' / ' + names.length + '</span></div>'
          + (shown.length ? bands : '<div class="empty">没有匹配的名字；这一列只有客户端里的英文原名，中文定名还没公布。</div>') + '</div>'
          + '<div class="card" id="claimed"><h2>名单里的 ' + claimed.length + ' 座</h2>'
          + '<div class="scrollx"><table class="entab rtab"><thead><tr><th>载入图</th><th>名字</th><th>它自报规模</th><th>客户端的队伍查找器里</th>'
          + '</tr></thead><tbody>' +
          claimed.map(function (r) {
            var inClient = names.filter(function (x) { return x.matchedIn === 'raid' && x.matched === r.id; })[0];
            return '<tr><td class="ich">' + (r.art
                ? '<span class="liw t"><img src="' + D.esc(r.art) + '" alt="' + D.esc(r.nameEn || '') + ' 的客户端载入图" loading="lazy" onerror="this.className=\'bad\'"></span>'
                : '<span class="dim">没有这张载入图</span>') + '</td>'
              + '<td><b>' + D.esc(r.nameEn || r.nameCn || '未定名') + '</b>'
              + (r.nameCn ? '<span class="dim">　' + D.esc(r.nameCn) + '</span>' : '<span class="dim">　中文定名未公布</span>')
              + '</td><td class="mono">' + D.esc(r.sizeClaim || '未写') + ' 人</td>'
              + '<td>' + (inClient ? '有这一条：' + sizeText(inClient) + '、' + entryText(inClient)
                  : '<span class="dim">没有对应的排队条目</span>') + '</td></tr>';
          }).join('') + '</tbody></table></div>'
          + '</div>');
        var box = el('rq');
        if (box) box.oninput = function () { f.q = box.value; var p = document.activeElement === box; draw(); if (p) { el('rq').focus(); el('rq').setSelectionRange(9999, 9999); } };
      }
      draw();
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
                iconCell(ICONS[iconKeyOf(x)], x.id, x.cn, 1) + D.esc(x.cn) + '</span>';
            }).join('') + '</div>';
        }).join('') : '<div class="empty">没有匹配词条，试试放宽筛选。</div>';
        el('cnt').textContent = list.length + ' / ' + items.length;
        Array.prototype.forEach.call(document.querySelectorAll('.term[data-c]'), function (t) {
          t.onclick = function () { D.copy(t.dataset.c); };
        });
      }
      /* 2026-10-12 站主决定：这一页只留词条本身，讲「来源」按钮、待补口径与自绘占位图标的
         那两句说明已删，出处集中在溯源页（provenance.html）。 */
      set('<div class="card"><h1 class="pt">中英术语速查</h1>' +
        '<div class="field"><input type="search" id="q" placeholder="输入中文或英文" value="' + D.esc(f.q) + '">' +
        '<select id="fk" aria-label="按类型筛选"><option value="">全部类型</option>' +
        Object.keys(KIND).map(function (k) { return '<option value="' + k + '">' + KIND[k] + '</option>'; }).join('') + '</select>' +
        '<select id="fr" aria-label="按种族筛选"><option value="">全部种族</option>' +
        raceIds.map(function (id) { return '<option value="' + id + '">' + D.esc((RACE[id] || {}).cn || id) + '</option>'; }).join('') + '</select>' +
        '<span class="dim mono" id="cnt"></span></div>' +
        '<div id="pool"></div></div>');
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
        ['wago.tools/db2', '客户端数据表的 CSV 转储（非暴雪域名，只留最近几个版本）',
          '只取英文名、ID、等级与人数；文案一律不搬'],
        ['wowclassicforever.info', '最接近数据库的粉丝站', '人工参照，禁止搬数据'],
        ['foreverchanges.pro', '9 新本名单与区间', '线索，禁止整库复制'],
        ['news.17173.com', '中文蓝贴转载', '旁证，需回校官方'],
        ['github.com/cmangos/classic-db', '1.12 国服中文 locale（GPL-3.0）', '只取译名与结构'],
        ['search.bilibili.com', '测试服实测视频', 'ASR + 关键帧识别后人工确认']];
        var ti = r[0].talentImport;
        set('<div class="card"><h1 class="pt">溯源与覆盖率</h1><p class="dim">' +
          '每条数据从哪来、什么时候核的、哪些刻意没拿，全部摊在这里。' +
          '内容页（天赋、副本、世界、种族那些）只放标题与数据，不挂分级徽标与来源标记——' +
          '要看出处就到这一页。</p></div>' +
          '<div class="card"><h2>数据覆盖率</h2><p class="note">这里统计的是 ' + sc.pubTotal +
          ' 条对外词条（术语 + 副本 + 世界线），不含天赋；连九棵天赋树的节点一起算是 ' + sc.coverageTotal +
          ' 条，多出来的 ' + (sc.coverageTotal - sc.pubTotal) + ' 条是天赋节点。' +
          '页面上只有这一处给覆盖率，内容页不再重复。</p>' + D.covBar(cov) +
          '<div class="stats">' + Object.keys(names).map(function (k) {
            // 全站只有这一页画分级徽标与来源轨：内容页那些按 2026-10-12 站主决定撤到这里来
            return '<div class="stat">' + D.pill(k) + '<b>' + cov[k] + '</b>' + names[k] + '</div>';
          }).join('') + '</div>' +
          '<p class="dim">判定标准：一条数据只有挂着官方来源且人工核过，才算已核实；粉丝站与转载最高只算待实测。</p></div>' +
          (ti ? '<div class="card"><h2>天赋数据来源与风险</h2>' +
            '<div class="grid g2"><div><h3>来源与方法</h3><p class="dim">' + D.esc(ti.method) + '<br>' +
            (ti.sources || []).map(function (s) { return '<span class="mono" style="font-size:11.5px">' + D.esc(s) + '</span>'; }).join('<br>') +
            '<br>' + D.esc(ti.collectedAt) + '</p>' +
            '<div class="stats" style="margin-top:10px">' +
            '<div class="stat"><b>' + ti.nodes + '</b>天赋节点</div>' +
            '<div class="stat"><b>' + ti.nameVerified + '</b>名与官网一致</div>' +
            '<div class="stat"><b>' + (ti.nameConflict + (sc.talentTreeConflict || 0)) +
            '</b>译名有两个叫法' + (sc.talentTreeConflict ? '（含 ' + sc.talentTreeConflict + ' 个系名）' : '') + '</div>' +
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
  function systems() {
    D.load('data/systems.json').then(function (s) {
      /* 2026-10-12 站主决定：这一页只留词条名——逐条的来源说明（note 字段）与分级徽标不再上内容页，
         出处集中在溯源页（provenance.html）。撤完那些句子后一条一个卡片太空，
         所以改成一组一张表：这一页本来就是"这个词官方中文叫什么"的对照表。 */
      set('<div class="card"><h1 class="pt">系统与新区域</h1></div>' +
        s.groups.map(function (g) {
        return '<div class="card"><h2>' + D.esc(g.label) + '<span class="dim mono"> · ' + g.items.length +
          ' 条</span></h2><div class="scrollx"><table class="entab"><thead><tr>' +
          '<th>中文名</th><th>英文原名</th></tr></thead><tbody>' +
          g.items.map(function (x) {
            return '<tr><td><b>' + D.esc(x.nameCn || '中文名未定') + '</b></td>' +
              '<td class="en mono">' + (x.nameEn ? D.esc(x.nameEn) : '<span class="dim">英文原名未证实</span>') +
              '</td></tr>';
          }).join('') + '</tbody></table></div></div>';
      }).join(''));
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
          /* 2026-10-12 站主决定：素材出处角标与"没有可信头像"那类说明不再上内容页，
             出处集中在溯源页（provenance.html）；图与它的有无判断照旧。 */
          return '<div class="facband ' + fac + '">' +
            // 阵营城市原画压暗当氛围底；取不到就整个不渲染，纯色带照常显示
            (CITY[fac] ? '<div class="fembg"><img src="' + D.esc(CITY[fac]) + '" alt="" loading="lazy" ' +
              'onerror="this.parentNode.className=\'fembg bad\'"></div>' : '') +
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
                '</button>';
            }).join('') + '</div></div>';
        }

        function detail() {
          var x = byKey[f.sel];
          if (!x) return '<div class="empty">选一个种族看它的特长。</div>';
          var tl = traitListOf(x);
          return '<div class="rdhead">' + face(x, 'lg') +
            '<div class="rdt"><h2>' + raceName(x) +
            (x.id.indexOf('skyborne') === 0 ? ' <span class="tag new">无限新增</span>' : '') + '</h2>' +
            '<p class="dim">' + FAC[x.faction] + ' · 可选 ' + x.classes.length + ' 个职业 · ' + tl.length +
            ' 条种族特长' + (x.nameEn ? ' · <span class="mono">' + D.esc(x.nameEn) + '</span>' : ' · 官方未公布英文原名') + '</p>' +
            '</div></div>' +
            (x.lore ? '<p class="lore">' + D.esc(x.lore) + '</p>' : '') +
            '<h3 class="rdh">可选职业</h3><div class="rdcls">' + cols.map(function (id) {
              var ok = x.classes.indexOf(id) >= 0;
              return '<span class="rdcl' + (ok ? '' : ' off') + '" title="' + D.esc(CNAME[id]) + (ok ? '可选' : '不可选') + '">' +
                (window.Glyph ? Glyph.classTile(id, CNAME[id], CTILE[id], 'sm') : '') +
                '<i>' + D.esc(CNAME[id]) + '</i></span>';
            }).join('') + '</div>' +
            '<h3 class="rdh">种族特长</h3>' +
            (tl.length ? '<ul class="rdtr">' + tl.map(function (t) {
              return '<li>' + iconCell(t.iconKey, x.id + t.name, t.name) +
                '<div class="rdtr-b"><b>' + D.esc(t.name) + '</b>' +
                '<span class="tag">' + (t.passive ? '被动' : '主动') + '</span>' +
                '<p class="quote">' + D.esc(t.quote) + '</p></div></li>';
            }).join('') + '</ul>' : '<p class="dim">这个种族没有特长条目。</p>');
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
        function draw() {
          el('facbands').innerHTML = band('alliance') + band('horde');
          el('rdet').innerHTML = detail();
          el('mx').innerHTML = matrix();
          /* 2026-10-12 站主决定：矩阵那排讲"标记从哪来、去哪里搜词"的说明已删，
             只留筛选状态与清除按钮；出处集中在溯源页（provenance.html）。 */
          el('mhint').innerHTML = f.c
            ? '已按「' + D.esc(CNAME[f.c]) + '」筛选 <button type="button" class="ghost mini" id="cx">清除</button>'
            : '';
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
            };
          });
        }

        set('<div class="card"><h1 class="pt">种族与职业组合</h1>' +
          '<div class="stats">' +
          '<div class="stat"><b>' + R.races.length + '</b>种族行</div>' +
          '<div class="stat"><b>' + traits.length + '</b>条种族特长</div>' +
          '<div class="stat"><b>' + R.newCombos.length + '</b>组亮点组合</div>' +
          '<div class="stat"><b>' + inGloss + '</b>条有中英对照</div>' +
          '<div class="stat"><b>' + Object.keys(POR).length + '</b>张种族头像</div></div>' +
          (R.skyborneNote && R.skyborneNote.text ? '<p class="dim">' +
            D.esc(R.skyborneNote.text) + '</p>' : '') + '</div>' +

          '<div class="facwrap" id="facbands"></div>' +
          '<div class="card rdetail" id="rdet"></div>' +

          '<div class="card"><h2>种族 × 职业矩阵</h2><p class="dim" id="mhint"></p>' +
          '<div class="field"><label class="dim">阵营</label><select id="ff"><option value="">全部</option>' +
          '<option value="horde">部落</option><option value="alliance">联盟</option></select></div>' +
          '<div class="scrollx" id="mx"></div>' +
          /* 这一行不是"备注文案"，是红线要求的两源分歧标注：矩阵给一套数、官方导语给另一套说法，
             两个都留着并写清本站怎么处置。缺了它，页面就等于替玩家挑了一个说法。
             跟在后面的分级徽标与来源按钮按 2026-10-12 站主决定已撤，出处集中在溯源页。 */
          (R.conflicts || []).map(function (cf) {
            return '<p class="conf">' + D.esc(cf.topic) + '——' + D.esc(cf.a.saying) +
              D.esc(cf.b.saying) + D.esc(cf.handling) + '</p>';
          }).join('') + '</div>' +

          '<div class="card"><h2>新开放的组合</h2><p class="dim">' +
          D.esc((R.newCombos[0] && R.newCombos[0].provenance[0].quote) || '') + '</p>' +
          '<div class="combos">' + R.newCombos.map(function (c) {
            var x = R.races.filter(function (y) {
              return (y.subgroup ? y.subgroup.nameCn : y.nameCn) === c.raceCn || y.nameCn === c.raceCn;
            })[0];
            return '<span class="combo">' + (x ? face(x, 'sm') : '') +
              '<b>' + D.esc(c.raceCn) + '</b>' +
              (window.Glyph ? Glyph.classTile(c.classId, c.classCn, CTILE[c.classId], 'sm') : '') +
              '<b>' + D.esc(c.classCn) + '</b></span>';
          }).join('') + '</div></div>');

        el('ff').onchange = function (e) { f.fac = e.target.value; draw(); };
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
          '<div class="field"><input type="search" id="pq" placeholder="搜制成品或材料名" value="' + D.esc(f.q) + '">' +
          '<input type="number" id="plv" min="1" max="300" placeholder="我的技能 1–300" value="' + D.esc(f.lv) + '" class="lv">' +
          '<button type="button" class="pick tog' + (f.onlyNew ? ' on' : '') + '" id="pn" aria-pressed="' +
          (f.onlyNew ? 'true' : 'false') + '">只看无限新增</button>' +
          '<span class="dim mono" id="pcnt"></span></div></div>';
        var body = '';
        if (sel.unparsed) {
          // 空态要说清为什么空，那句话在 professions.json 的 note 里，不在代码里另写一遍
          body = '<div class="card"><div class="empty">' + D.esc(sel.note || '这一版还没拆出可列的条目。') +
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
          /* 这一页的任务是"我这点技能能做什么、下一步要什么"，所以配方不排成一张
             一万像素高的平表：按技能橙点分成 1–75 / 76–150 / 151–225 / 226–300 四箱，
             每箱报条数，材料画成条——"要 20 个草"和"只要 1 个矿"得一眼看出来不一样。 */
          var bands = [[1, 75, '学徒 · 1–75'], [76, 150, '熟练 · 76–150'],
            [151, 225, '专家 · 151–225'], [226, 300, '大师 · 226–300']];
          var inBand = function (x, b) {
            var o = (x.skill || {}).orange;
            return typeof o === 'number' && o >= b[0] && o <= b[1];
          };
          var maxMat = Math.max.apply(null, recipes.map(function (x) {
            return (x.mats || []).reduce(function (a, m) { return a + (m.count || 1); }, 0);
          }).concat([1]));
          var rowOf = function (x) {
            var mats = x.mats || [];
            var total = mats.reduce(function (a, m) { return a + (m.count || 1); }, 0);
            return '<tr><td>' + iconCell(x.iconKey, x.itemId, x.nameCn, 1) +
              '<span class="q' + (x.quality || 0) + '">' + D.hl(x.nameCn, f.q) + '</span>' +
              (x.isNew ? '<span class="tag">新</span>' : '') +
              '<span class="dim mono"> #' + D.esc(x.itemId) + '</span></td>' +
              '<td class="mats">' + (mats.length
                ? '<i class="mbar" aria-hidden="true"><s style="width:' +
                  Math.max(6, Math.round(total / maxMat * 100)) + '%"></s></i>' +
                  mats.map(function (m) {
                    return '<span class="mat">' + iconCell(m.iconKey, m.nameCn, m.nameCn, 1) +
                      D.esc(m.nameCn) + '<b class="mono">×' + m.count + '</b></span>';
                  }).join('')
                : '<span class="dim">无需材料</span>') + '</td>' +
              '<td>' + skillCell(x.skill) + '</td>' +
              '<td class="dim">' + D.esc(x.source || '—') + '</td></tr>';
          };
          var table = function (list) {
            return '<div class="scrollx"><table class="entab"><thead><tr><th class="ich">制成品</th>' +
              '<th>材料</th><th>技能</th><th>来源</th></tr></thead><tbody>' +
              list.map(rowOf).join('') + '</tbody></table></div>';
          };
          var boded = 0;
          /* 2026-10-12 站主决定：这一页只留配方表与采集点表，讲"技能四档怎么读、材料条怎么比长短"
             与逐条来源的那几段已删，出处集中在溯源页（provenance.html）。 */
          body += '<div class="card"><h2>配方 · ' + recipes.length + ' 条</h2>' +
            bands.map(function (b) {
              var list = recipes.filter(function (x) { return inBand(x, b); });
              if (!list.length) return '';
              boded += list.length;
              return '<h3 class="rbandh">' + b[2] + ' <b class="mono">' + list.length + '</b></h3>' + table(list);
            }).join('');
          var rest = recipes.filter(function (x) {
            return !bands.some(function (b) { return inBand(x, b); });
          });
          if (rest.length) {
            body += '<h3 class="rbandh">技能档位没标出来 <b class="mono">' + rest.length + '</b></h3>' + table(rest);
          }
          body += '</div>';
          if (boded !== recipes.length) { /* 分箱数与总数对不上就是逻辑漏了，不静默吞条目 */
            console.warn('配方分箱漏条', boded, recipes.length);
          }
        }
        if (!nodes.length && !recipes.length && !sel.unparsed) {
          body += '<div class="card"><div class="empty">这个专业没有匹配条目，试试放宽搜索或技能等级。</div></div>';
        }
        el('pbody').innerHTML = head + body;
        el('pcnt').textContent = (recipes.length + nodes.length) + ' 条';
        var qi = el('pq');
        qi.oninput = function () { f.q = qi.value.trim(); draw(); };
        var li = el('plv');
        li.oninput = function () { f.lv = parseInt(li.value, 10) || ''; draw(); };
        var ni = el('pn');
        ni.onclick = function () { f.onlyNew = !f.onlyNew; draw(); };
      }

      /* 2026-10-12 站主决定：页首那句讲"配方数据从哪来、本站红线不碰什么"的说明已删，
         出处集中在溯源页（provenance.html）；这一页只留专业数、配方数这些读数与表。 */
      set('<div class="card"><h1 class="pt">专业与配方</h1>' +
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

  /* ---------- 传承（Legacy）：三棵专长树 + 65 项挑战 ---------- */
  function legacy() {
    Promise.all([D.load('data/legacy.json'), D.load('data/icons.json').catch(function () { return { map: {} }; })])
      .then(function (r) {
        var L = r[0];
        var M = L.meta || {}, rules = M.rules || {}, cnt = M.counts || {};
        var perkById = {};
        (L.perks || []).forEach(function (p) { perkById[p.id] = p; });
        var total = (L.challenges || []).reduce(function (a, c) { return a + c.items.length; }, 0);
        /* 点数说法要能从数据里自己长出来：客户端明细里多数挑战给 1 点、有一项给 16 点，
           写死"每项 1 点"就是假的，上游哪天再改数也会悄悄过期。 */
        var allPts = (L.challenges || []).reduce(function (a, c) { return a.concat(c.items || []); }, []);
        var onesN = allPts.filter(function (x) { return (x.points || 0) === 1; }).length;
        var oddPts = allPts.filter(function (x) { return (x.points || 0) !== 1; });
        var f = {
          tree: urlQ('t') && (L.trees || []).some(function (t) { return t.id === urlQ('t'); })
            ? urlQ('t') : ((L.trees || [])[0] || {}).id || '',
          q: urlQ('q'), open: urlQ('p')
        };
        // 从首页搜索带着专长名跳进来：直接展开那条并切到它所在的树，别让人自己找格子。
        // 只认全等，避免"搜索挑战时命中一个同名的专长"把下面的挑战筛选给抢掉。
        if (f.q && !f.open) {
          var lk = f.q.trim().toLowerCase();
          var hitp = (L.perks || []).filter(function (x) {
            return String(x.nameCn || '').toLowerCase() === lk;
          })[0];
          if (hitp) {
            f.jumpFrom = hitp.nameCn;
            f.open = hitp.id;
            f.tree = hitp.treeId || f.tree;
            f.q = '';
          }
        }

        function iconOf(key, seed, cn) {
          var ph = window.Glyph ? Glyph.talentTile(seed || cn, cn) : '';
          var img = key ? '<img class="ico" src="img/icons/' + encodeURIComponent(key) + '.jpg" alt="" ' +
            'loading="lazy" onerror="this.className=\'ico bad\'">' : '';
          return '<span class="ico-wrap">' + ph + img + '</span>';
        }
        function perkCell(s) {
          if (s.empty) return '<div class="lslot none" aria-hidden="true"></div>';
          if (s.unknown) {
            return '<div class="lslot unk"><b>?</b><span class="dim">未公开</span></div>';
          }
          var p = perkById[s.perk];
          if (!p) return '<div class="lslot unk"><b>?</b></div>';
          var on = f.open === p.id;
          return '<button type="button" class="lslot' + (on ? ' on' : '') + '" data-perk="' + D.esc(p.id) + '"' +
            ' aria-pressed="' + (on ? 'true' : 'false') + '"><span class="lcell">' +
            iconOf(p.iconKey, p.id, p.nameCn) + '<span class="rk mono">' +
            (p.maxRank == null ? '?' : p.maxRank) + ' 层</span></span>' +
            '<span class="nm">' + D.esc(p.nameCn) + '</span></button>';
        }
        function treeGrid(t) {
          var out = '<div class="lgrid">';
          for (var row = 0; row < t.rows; row++) {
            for (var col = 0; col < t.cols; col++) {
              var s = t.slots.filter(function (x) { return x.row === row && x.col === col; })[0];
              out += perkCell(s || { empty: true });
            }
          }
          return out + '</div>';
        }
        function treePanel() {
          var t = (L.trees || []).filter(function (x) { return x.id === f.tree; })[0];
          if (!t) return '<div class="empty">这棵树还没收录。</div>';
          var n = t.slots.filter(function (x) { return !x.empty && !x.unknown; }).length;
          var unk = t.slots.filter(function (x) { return x.unknown; }).length;
          /* 2026-10-12 站主决定：树格怎么读、每层效果为什么不写那几句已从内容页删掉，
             出处与取舍集中在溯源页（provenance.html）。 */
          return '<h2>' + D.esc(t.nameCn) + '<span class="dim mono">' + n + ' 个专长' +
            (unk ? ' · ' + unk + ' 格未公开' : '') + '</span></h2>' + treeGrid(t);
        }
        function perkDetail() {
          var p = perkById[f.open];
          if (!p) return '<div class="card leempty"><h2>点一个专长看细节</h2></div>';
          return '<div class="card ldetail"><h2>' + D.esc(p.nameCn) +
            ' <span class="dim mono">最多 ' + (p.maxRank == null ? '未核实' : p.maxRank + ' 层') + '</span></h2>' +
            '<div class="lmeta"><span>属于：<b>' + D.esc(p.treeCn) + '</b></span>' +
            '<span>位置：第 ' + (p.row + 1) + ' 排第 ' + (p.col + 1) + ' 列</span>' +
            '<span>前置：' + (p.prerequisiteCn ? '<b>' + D.esc(p.prerequisiteCn) + '</b>'
              : '<span class="dim">没有前置</span>') + '</span></div></div>';
        }
        function rowsOf(c) {
          var kw = f.q.trim().toLowerCase();
          if (!kw) return c.items;
          return c.items.filter(function (x) {
            return ((x.nameCn || '') + ' ' + (x.requirement || '') + ' ' + (x.sub || '') + ' ' +
              (x.group || '')).toLowerCase().indexOf(kw) >= 0;
          });
        }
        function challengeBlock(c) {
          var rows = rowsOf(c);
          if (!rows.length) return '';
          // 组头不写"每项 N 点"：客户端明细里 65 项各给 1 点、有一项给 16 点，
          // 统一说"每项 1 点"就是假的。逐条点数在表格最后一列，组头只给合计。
          var sum = rows.reduce(function (a, x) { return a + (x.points || 0); }, 0);
          return '<div class="card lchgrp"><h2>' + D.esc(c.nameCn) +
            '<span class="dim mono">' + rows.length + (rows.length === c.items.length ? '' : ' / ' + c.items.length) +
            ' 项 · 合计 ' + sum + ' 点</span></h2>' +
            (c.subcategories.length ? '<div class="chips">' + c.subcategories.map(function (s) {
              var n = c.items.filter(function (x) { return x.sub === s || x.group === s; }).length;
              return n ? '<span class="chipc">' + D.esc(s) + '<b class="mono">' + n + '</b></span>' : '';
            }).join('') + '</div>' : '') +
            '<div class="scrollx"><table class="entab ltab"><thead><tr><th class="ich">图标</th><th>挑战</th>' +
            '<th>完成条件</th><th>归属</th><th>点数</th></tr></thead><tbody>' +
            rows.map(function (x) {
              return '<tr><td class="ich">' + iconCell(x.iconKey, x.id, x.nameCn) + '</td>' +
                '<td>' + D.hl(x.nameCn, f.q) + '<span class="dim mono">#' + D.esc(x.id) + '</span>' +
                D.pill(x.level) + '</td>' +
                '<td class="dim">' + D.hl(x.requirement || '未记录', f.q) + '</td>' +
                '<td class="dim">' + D.esc(x.sub || x.group || c.nameCn) + '</td>' +
                '<td class="mono">' + (x.points == null ? '—' : x.points) + '</td></tr>';
            }).join('') + '</tbody></table></div></div>';
        }
        function challengeArea() {
          var body = (L.challenges || []).map(challengeBlock).join('');
          var shown = (L.challenges || []).reduce(function (a, c) { return a + rowsOf(c).length; }, 0);
          return body + (!shown ? '<div class="card"><div class="empty">这个关键词下没有挑战，' +
            '换个说法试试（比如"25 级""烹饪""军衔"）。</div></div>' : '');
        }

        /* 2026-10-12 站主决定：这一页只留机制本身（怎么拿点、点数合计、解锁条件）与表格，
           讲数据出自哪份解包、每层效果为什么不复制、点数两说怎么取舍那几段已删，
           出处与缺口集中在溯源页（provenance.html）。 */
        set('<div class="card"><h1 class="pt">传承专长与传承挑战</h1>' +
          '<p class="dim">完成传承挑战拿传承点数，用点数在三棵传承树里点永久专长（账号级，不随角色重置）。' +
          '<b class="mono">' + total + '</b> 项挑战的点数合计 <b class="mono">' +
          (rules.launchEarnableTotal || '?') + '</b> 点，' +
          '首发上限 <b class="mono">' + (rules.launchSpendingCap || '?') + '</b> 点；' +
          D.esc(rules.unlock || '') + '</p>' +
          '<div class="stats"><div class="stat"><b>' + cnt.perks + '</b>个专长有明细</div>' +
          '<div class="stat"><b>' + cnt.unknownSlots + '</b>格还没公开</div>' +
          '<div class="stat"><b>' + total + '</b>项挑战</div>' +
          '<div class="stat"><b>' + cnt.rewards + '</b>档进度奖励</div></div>' +
          '<div class="picks">' + (L.trees || []).map(function (t) {
            return '<button type="button" class="pick' + (f.tree === t.id ? ' on' : '') + '" data-t="' +
              D.esc(t.id) + '"><b>' + D.esc(t.nameCn) + '</b><span class="dim mono">' +
              t.slots.filter(function (x) { return !x.empty; }).length + '</span></button>';
          }).join('') + '</div></div>' +
          '<div class="ltreewrap"><div class="card ltreecard" id="ltree">' + treePanel() + '</div>' +
          '<div id="ldet">' + perkDetail() + '</div></div>' +
          '<div class="card"><h2>传承挑战 · ' + total + ' 项</h2>' +
          '<p class="dim">' + onesN + ' 项各 1 点' +
          (oddPts.length ? '，另有 ' + oddPts.map(function (x) {
            return D.esc(x.nameCn) + ' 给 ' + x.points + ' 点';
          }).join('、') : '') + '。</p>' +
          '<div class="field"><input type="search" id="lq" placeholder="搜挑战名、完成条件或归属" value="' +
          D.esc(f.q) + '"><span class="dim mono" id="lcnt"></span></div></div>' +
          '<div id="lch">' + challengeArea() + '</div>' +
          '<div class="card"><h2>攒到一定挑战数给的奖励 · ' + cnt.rewards + ' 档</h2>' +
          '<div class="scrollx"><table class="entab ltab"><thead><tr><th class="ich">图标</th><th>奖励</th>' +
          '<th>需要的挑战数</th><th>物品编号</th></tr></thead><tbody>' +
          (L.rewards || []).map(function (x) {
            return '<tr><td class="ich">' + iconCell(x.iconKey, x.itemId, x.nameCn) + '</td>' +
              '<td>' + D.esc(x.nameCn) + '</td><td class="mono">' + x.at + '</td>' +
              '<td class="dim mono">#' + D.esc(x.itemId) + '</td></tr>';
          }).join('') + '</tbody></table></div></div>');

        function repaint() {
          el('ltree').innerHTML = treePanel();
          el('ldet').innerHTML = perkDetail();
          bindCells();
        }
        function bindCells() {
          Array.prototype.forEach.call(document.querySelectorAll('[data-perk]'), function (b) {
            b.onclick = function () { f.open = f.open === b.dataset.perk ? '' : b.dataset.perk; repaint(); };
          });
        }
        Array.prototype.forEach.call(document.querySelectorAll('.picks [data-t]'), function (b) {
          b.onclick = function () { f.tree = b.dataset.t; repaint(); };
        });
        bindCells();
        var qi = el('lq'), lc = el('lcnt');
        var shown = (L.challenges || []).reduce(function (a, c) { return a + rowsOf(c).length; }, 0);
        lc.textContent = shown + ' / ' + total + ' 项';
        qi.oninput = function () {
          f.q = qi.value;
          el('lch').innerHTML = challengeArea();
          lc.textContent = (L.challenges || []).reduce(function (a, c) { return a + rowsOf(c).length; }, 0) +
            ' / ' + total + ' 项';
        };
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
           因为那是数据不是样式，不该把坐标值硬编进 class。
           2026-10-12 站主决定：图上那句素材出处角标不再上内容页，出处集中在溯源页。 */
        function mapBox(o, alt) {
          if (!o.mapFile) {
            return '<div class="zmap none">' +
              (o.mapId ? '<b class="mono">地图编号 ' + D.esc(o.mapId) + '</b>' : '') + '</div>';
          }
          return '<div class="zmap"><img src="' + D.esc(o.mapFile) + '" alt="' + D.esc(alt) +
            '的区域小地图" loading="lazy" decoding="async" width="560" height="373" ' +
            'onerror="this.className=\'bad\'">' +
            (o.mark ? '<b class="zmark" data-x="' + o.mark.x + '" data-y="' + o.mark.y +
              '" aria-hidden="true"></b>' : '') + '</div>';
        }
        function coordTxt(o) {
          var s = [];
          if (o.mark) s.push('(' + o.mark.x + ', ' + o.mark.y + ')');
          if (o.world) s.push('世界 ' + o.world.x + ', ' + o.world.y);
          return '<span class="mono dim">' + (s.join(' · ') || '坐标待补') + '</span>';
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
            out += '<div class="band"><b>无限新增区域</b><span class="dim">飞行路线多未定</span>' +
              '<span class="dim mono">' + nz.length + ' 个</span></div><div class="zgrid">' +
              nz.map(function (z) { return zoneCard(z, '新'); }).join('') + '</div>';
          }
          (w.continents || []).concat([{ id: 'new', nameCn: '单独成图的新区域' }]).forEach(function (c) {
            var rows = zs.filter(function (z) { return z.continent === c.id && !z.isNew; });
            if (!rows.length) return;
            out += '<div class="band"><b>' + D.esc(c.nameCn) + '</b>' +
              '<span class="dim mono">' + rows.length + ' 个</span></div>' +
              '<div class="zgrid">' + rows.map(function (z) { return zoneCard(z, ''); }).join('') + '</div>';
          });
          if (!out) out = '<div class="card"><div class="empty">没有匹配的区域，换个名字试试。</div></div>';
          /* 2026-10-12 站主决定：地图清单只列表身，"哪几张没切出图、为什么不搬别人的交互地图"
             那两段说明已删，素材与缺口集中在溯源页（provenance.html）。 */
          return out + '<div class="card"><h2>地图清单</h2>' +
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
            (z.flight ? '<span class="dim">' + (z.flight === 'no-route' ? '没有飞行路线' : '有飞行路线，站点待实测') + '</span>' : '') +
            '<span class="zcnt">' + (z.rareCount ? z.rareCount + ' 个稀有' : '') +
            (z.rareCount && z.bookCount ? ' · ' : '') + (z.bookCount ? z.bookCount + ' 本书' : '') + '</span>' +
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
            }).join('') + '</div></div>';
          /* 2026-10-12 站主决定：稀有精英卡只留名字、坐标与掉落，讲"数据取自哪次解包、
             为什么不写刷新计时、坐标两套怎么读、来源在哪"那几段已删，出处集中在溯源页。 */
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
                    : '<div class="note">这一条没有掉落记录。</div>') +
                  '<button type="button" class="ghost wide" data-r="' + D.esc(r.id) + '">掉落与坐标</button>' +
                  '<div class="wdr" id="wr-' + D.esc(r.id) + '">' +
                  '<h3>掉落清单</h3>' + (r.drops.length
                    ? '<ul class="list">' + r.drops.map(function (d) {
                      return '<li>' + D.esc(d.nameCn) + '（#' + D.esc(d.itemId) + '，' +
                        (d.bind ? D.esc(d.bind) : '绑定方式待补') + '）</li>';
                    }).join('') + '</ul>'
                    : '<p class="dim">待补。</p>') + '</div></div></div>';
              }).join('') + '</div>';
          });
          var sets = (w.rareSets || []).map(function (s) {
            return '<div class="card"><h2>套装 · ' + D.esc(s.nameCn) + '</h2>' +
              '<p class="dim">' + s.pieces.length + ' 件套</p>' +
              '<div class="loot">' + s.pieces.map(dropRow).join('') + '</div>' +
              '<ul class="list">' + s.pieces.map(function (p) {
                return '<li>' + D.esc(p.nameCn) + ' — ' + (p.fromRare ? '来自稀有「' + D.esc(p.fromRare) + '」' : '来源稀有待补') + '</li>';
              }).join('') + '</ul></div>';
          }).join('');
          var un = (w.raresUnplaced || []);
          return out + sets + (un.length ? '<div class="card"><h2>没有坐标的 ' + un.length + ' 个稀有</h2>' +
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
              '<td>' + (r.noReward ? '<span class="dim">奖励待补</span>'
                : r.items.map(dropRow).join('')) + '</td></tr>';
          }).join('');
          /* 2026-10-12 站主决定：书籍面板只留书名、容器、坐标与奖励表，
             讲"这些数据从哪来、本文为什么不搬"的那段说明已删，出处集中在溯源页。 */
          var out = '<div class="card"><h2>先找书，再找管理员</h2>' +
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
          if (!bag) return '<div class="card"><div class="empty">没有睡袋条目。</div></div>';
          /* 2026-10-12 站主决定：睡袋面板只留物品与机制数值，讲数据来源、
             冲级路线为什么不搬那两段说明已删，出处集中在溯源页（provenance.html）。 */
          var out = '<div class="card"><h2>睡袋本身</h2>' +
            '<div class="itemrow">' + iconCell(bag.iconKey, bag.itemId, bag.nameCn) +
            '<div><b>' + D.esc(bag.nameCn) + '</b>' +
            '<span class="dim mono">#' + D.esc(bag.itemId) + '</span>' +
            (bag.bind ? '<span class="dim">' + D.esc(bag.bind) + '</span>' : '') +
            (bt.usableLevel ? '<span class="dim mono">' + bt.usableLevel + ' 级可用</span>' : '') + '</div></div>';
          out += '<table class="mtx"><thead><tr><th>机制项</th><th>记录值</th></tr></thead><tbody>' +
            [['铺开耗时', p.castSec + ' 秒'], ['休息收益名', p.buffName || '—'],
              ['收益持续', p.buffHours + ' 小时'], ['可叠层', p.stacks + ' 层'],
              ['铺设冷却', p.cdMin + ' 分钟']]
              .map(function (x) {
                return '<tr><td>' + D.esc(x[0]) + '</td><td class="mono">' + D.esc(x[1]) + '</td></tr>';
              }).join('') + '</tbody></table></div>';
          var camps = [];
          (bt.camps || []).forEach(function (c) { camps = camps.concat(c.places || []); });
          var kk = kw();
          if (kk) camps = camps.filter(function (c) {
            return ((c.zone || '') + ' ' + (c.whereCn || '') + ' ' + (c.landmark || '')).toLowerCase().indexOf(kk) >= 0;
          });
          out += '<div class="card"><h2>营地点清单 · ' + camps.length +
            (kk ? '（搜索 ' + D.esc(f.q) + ' 命中）' : '') + '</h2>' +
            (camps.length ? '<div class="rgrid">' + camps.map(function (c) {
              return '<div class="rarecard">' + mapBox(c, c.zone) + '<div class="rbody">' +
                '<b>' + D.esc(c.zone || '区域未标') + '</b>' +
                (c.landmark ? '<span class="dim">' + D.esc(c.landmark) + '</span>' : '') +
                (c.whereCn ? '<span class="dim">' + D.esc(c.whereCn) + '</span>' : '') +
                coordTxt(c) + '</div></div>';
            }).join('') + '</div>' : '<div class="empty">这个关键词下没有营点。</div>') +
            '</div>';
          return out;
        }

        function draw() {
          var body = f.tab === 'zones' ? panelZones() : f.tab === 'rares' ? panelRares()
            : f.tab === 'books' ? panelBooks() : panelBag();
          el('wbody').innerHTML = body;
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
        /* 2026-10-12 站主决定：页首那句讲"世界线数据从哪来、刷新计时与攻略为什么不做"已删，
           出处集中在溯源页（provenance.html）；这一页只留区域、稀有、书与营地的数。 */
        set('<div class="card"><h1 class="pt">世界：区域、稀有与书</h1>' +
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
        // 四格之和现算（与首页同一口径），不写死
        var chgSum2 = (S.changesNew || 0) + (S.changesModified || 0) + (S.changesRemoved || 0) +
          (S.changesSpellsChanged || 0);

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
          el('chbody').innerHTML = '<div class="kchips" role="group" aria-label="按改动类别筛">' +
            CH_KINDS.map(function (x) {
              var n = (ch.items || []).filter(function (it) {
                return x[0] === 'all' || it.kind === x[0]; }).length;
              return '<button type="button" class="kchip' + (f.kind === x[0] ? ' on' : '') +
                '" data-k="' + x[0] + '" aria-pressed="' + (f.kind === x[0] ? 'true' : 'false') + '">' +
                x[1] + ' <b class="mono">' + n + '</b></button>';
            }).join('') + '</div>' +
            '<div class="picks">' +
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
          Array.prototype.forEach.call(document.querySelectorAll('.kchip'), function (b) {
            b.onclick = function () { f.kind = b.dataset.k; draw(); };
          });
          var qi = el('cq');
          qi.oninput = function () { f.q = qi.value; draw(); };
        }

        var K = ['官方时间点', '客户端改动', '本站更新'];
        /* 时间轴要能一眼看出"下一件是哪件"：只提亮最近的那一条（不是"30 天内的全部"——
           实测那样会一次亮 4 行，等于没有重点），已过去的整行降一档。差多少天按今天现算。 */
        var TODAY0 = new Date(new Date().toDateString()).getTime();
        var tsOf = function (x) {
          return /^\d{4}-\d{2}-\d{2}$/.test(x.date || '')
            ? new Date(x.date + 'T00:00:00+08:00').getTime() : null;
        };
        var nextI = -1, nextT = 0;
        // 这一页的时间轴是**倒序**排的（最近的日期在最上面），所以"下一件"不能取第一条 ≥ 今天的：
        // 那样会把 12 月那条当成下一件。按日期取"还没发生里最早的那一条"，与排序方向无关。
        tl.forEach(function (x, i) {
          var t = tsOf(x);
          if (t === null || t < TODAY0) return;
          if (nextI < 0 || t < nextT) { nextI = i; nextT = t; }
        });
        function tlState(x, i) {
          var t = tsOf(x);
          if (t === null) return { cls: '', note: '' };
          var d = Math.round((t - TODAY0) / 86400000);
          if (i === nextI) return { cls: ' near', note: d === 0 ? '就是今天' : '还有 ' + d + ' 天' };
          if (d < 0) return { cls: ' past', note: '已过 ' + (-d) + ' 天' };
          return { cls: '', note: '还有 ' + d + ' 天' };
        }
        set('<div class="card"><h1 class="pt">最新动态</h1>' +
          '<p class="dim">官方公告里的时间点、客户端里的职业改动、本站自己改了什么，三件事分开列。</p>' +
          '<div class="stats readout">' +
          '<div class="stat"><b>' + tl.length + '</b>个官方时间点</div>' +
          '<div class="stat"><b>' + (ch.items || []).length + '</b>条客户端改动</div>' +
          '<div class="stat"><b>' + S.changesNew + '</b>个新增天赋</div>' +
          '<div class="stat"><b>' + S.changesRemoved + '</b>个移除天赋</div>' +
          '<div class="stat"><b>' + cl.length + '</b>条本站更新</div></div>' +
          '<div class="picks utabs" role="group" aria-label="跳到本页三个板块">' + K.map(function (t, i) {
            return '<a class="pick" href="#k' + i + '"><b>' + t + '</b><span class="dim">跳 ↓</span></a>';
          }).join('') + '</div></div>' +

          /* 2026-10-12 站主决定：三个板块只留条目本身——讲"这一页为什么拆三件事、本站不做什么、
             改动文本为什么不复制"那几段说明与逐条来源已删，出处集中在溯源页（provenance.html）。 */
          '<div class="card" id="k0"><h2>官方公告里的时间点</h2>' +
          tl.map(function (x, i) {
            var st = tlState(x, i);
            return '<div class="flowrow' + st.cls + '"><b class="mono">' + D.esc(x.date) + '</b>' +
              '<div><b>' + D.esc(x.title) + '</b>' +
              (st.note ? ' <span class="when mono">' + st.note + '</span>' : '') +
              '<p class="dim">' + D.esc(x.what) + '</p></div></div>';
          }).join('') + '</div>' +

          '<div class="card" id="k1"><h2>客户端改动清单 · ' + (ch.items || []).length + ' 条</h2>' +
          /* 这四格与下面那行对照从首页搬来（2026-10-13 用户：首页那些读数像数据变动明细，
             不像资料站入口）。放在它描述的那张表头上，才对得上"全部 965 条 vs 四格之和 751"。 */
          '<div class="four"><div><b>' + S.changesNew + '</b><s>新增天赋</s></div>' +
          '<div><b>' + S.changesModified + '</b><s>改动天赋</s></div>' +
          '<div><b>' + S.changesRemoved + '</b><s>移除</s></div>' +
          '<div><b>' + S.changesSpellsChanged + '</b><s>法术有变</s></div></div>' +
          '<div class="kv"><span>这四格加起来比上面的 ' + (ch.items || []).length + ' 少 ' +
          ((ch.items || []).length - chgSum2) + ' 条</span><b>' + (ch.items || []).length +
          ' = 天赋 ' + S.changesTalents + ' + 法术 ' + ((ch.items || []).length - S.changesTalents) + '</b></div>' +
          '<p class="dim">清单把 ' + (ch.items || []).length + ' 条客户端条目都列了出来，其中 ' + chgSum2 +
          ' 条在无限服真的动了（新增、改动、移除，或法术说明有变）；剩下的只是列进对照表、本身没变。</p>' +
          '<div id="chbody"></div></div>' +

          '<div class="card" id="k2"><h2>本站更新 · ' + cl.length + ' 条</h2>' +
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
          '<div class="card"><h2>九职业的官方中文佐证，先比长短</h2>' +
          '<div class="rankbars">' + rows.map(function (x) {
            return '<div class="rb"><b>' + D.esc(cnOf[x.classId] || x.classId) + '</b>' +
              '<i><s style="width:' + Math.round(x.official / max * 100) + '%"></s>' +
              '<u style="width:' + Math.round(x.datamine / max * 100) + '%"></u></i>' +
              '<em class="mono">' + x.official + ' / ' + x.datamine + '</em></div>';
          }).join('') + '</div>' +
          '<p class="note">上条是官方中文佐证的条数，下条是只有客户端解包支撑的条数；' +
          '长短按全站最多的那个职业归一。表格在下面，给的是同一批数的精确值。</p></div>' +
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
          /* 2026-10-12 站主决定：这一页只留排行本身，外加那句"是本站整理的排序、不是强度排行"
             （红线要求留着）。"每一列怎么算出来的"那段口径说明、L0/L2 图例与「来源与核对」块
             都移出内容页：列名已在表头，条数的含义由右侧那句"x% 有官方中文"直接给。 */
          '<p class="dim">这个排序是本站按自己查得到的条数排的，改了数据重新生成就会变，不是官方结论。</p></div>');
      }).catch(fail);
  }


  function fail(e) {
    if (window.console) console.error('数据加载失败', e);
    // 只有真的用 file:// 打开时才给本地服务命令，否则页面上不该出现这些
    var local = location.protocol === 'file:';
    set('<div class="card"><h2>数据没加载出来</h2><p class="dim">刷新一下试试；' +
      (local ? '这个站要起一个本地服务才能读数据：在项目里执行 <code>bash tools/serve.sh</code>，' +
        '再访问 <code>http://127.0.0.1:8817</code>。' : '如果一直这样，请把这一页的地址发给我们。') +
      '</p><button id="rt">重试</button></div>');
    var b = el('rt'); if (b) b.onclick = function () { location.reload(); };
  }

  shell();
  watchRails();
  tickCountdown();
  setInterval(tickCountdown, 1000);
  ({ home: home, talent: talent, classes: classPage, chooser: chooser, timeline: timeline, skills: skills, dungeons: dungeons, raids: raids, systems: systems, races: races, professions: professions, legacy: legacy, world: world, updates: updates, rank: rank, glossary: glossary, provenance: provenance })[page]();
})();
