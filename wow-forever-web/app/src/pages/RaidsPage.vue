<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="P">
    <!-- 页首 banner：12 月 10 日首批 60 级团本首次开放总览 -->
    <section class="dhero raid-hero">
      <img :src="HERO" alt="" style="object-position:center 28%">
      <span class="dx"></span>
      <span class="forge-rivets" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
      <div class="db raid-hero-b">
        <div class="kicker">FIRST RAID LAUNCH · 2026-12-10</div>
        <h1 class="pt raid-hero-h1">团队副本 · 首次开放筹备</h1>
        <p class="raid-hero-sub">
          <b class="mono" style="color:var(--gold-hi)">{{ unlockDateCn }}</b> 首次同步解锁 3 座 60 级团本：
          <b>深穴（10人）</b>、<b>海加尔峰（20人）</b>、<b>奥妮克希亚的巢穴（40人）</b>，计划<b>{{ resetCycle }}</b>。
        </p>
        <div class="raid-hero-actions">
          <button type="button" class="cta-cut" @click="jumpTo('onyxia-attune')">黑龙门任务打卡清单 ↓</button>
          <button type="button" class="cta cta-line" @click="jumpTo('hyjal-t1')">海加尔峰 {{ raidSets.length }} 套 T1 ↓</button>
          <router-link class="cta cta-mute" :to="{ path: '/bis' }">60 级团前 BiS 配装 →</router-link>
        </div>
      </div>
      <div class="dstate raid-hero-cd">
        <template v-if="cdPhase === 'raid'">
          <i class="dot-on"></i>
          <div>
            <b>距首次开放 {{ cdLeft.d }} 天</b>
            <span class="mono raid-cd-clk">{{ clockText(cdLeft) }}</span>
          </div>
        </template>
        <template v-else>
          <i class="dot-ok"></i>
          <div>
            <b>已开放 · {{ resetCycle }}</b>
            <span class="raid-cd-clk">10 / 20 / 40 人</span>
          </div>
        </template>
      </div>
    </section>

    <!-- 首发 3 座团本核心档案大卡（使用已核真实团本封面图） -->
    <section class="raid-sec">
      <div class="raidgrid">
        <article v-for="c in cards" :key="c.r.id" class="raidcard raidcard-v2">
          <div class="art">
            <img :src="assetUrl(c.art)" :alt="(c.r.nameCn || c.r.nameEn || '团本') + ' 封面图'" loading="lazy">
            <span class="sh"></span>
            <span class="goldtag">{{ c.partyText }}</span>
            <span class="chip-open" :class="c.attuneRequired ? 'chip-warn' : 'chip-ok'">
              {{ c.attuneRequired ? '需' + (c.attuneItem || '门任务') : '无需门任务' }}
            </span>
            <h2 class="rc-title">{{ c.r.nameCn || c.r.nameEn || '未定名' }}</h2>
            <span v-if="c.r.nameEn" class="rc-en">{{ c.r.nameEn }}</span>
          </div>
          <div class="bd">
            <p v-if="c.summary" class="rc-sum">{{ c.summary }}</p>
            <div class="rc-kv">
              <div><span class="dim">开放时间</span><b class="mono">{{ unlockDate }}</b></div>
              <div><span class="dim">重置周期</span><b>{{ resetCycle }}</b></div>
              <div><span class="dim">首领数量</span><b class="mono">{{ c.bosses }} 位</b></div>
              <div><span class="dim">所在区域</span><b>{{ c.zoneCn || '待补' }}</b></div>
            </div>
            <div v-if="c.entrances" class="rc-meta-line"><b class="rc-lbl">入口</b>{{ c.entrances }}</div>
            <div v-if="c.attuneNote" class="rc-meta-line" :class="{ 'rc-attune-hi': c.attuneRequired }">
              <b class="rc-lbl">进本条件</b>{{ c.attuneNote }}
            </div>

            <!-- 首领速览折叠 -->
            <div v-if="c.bossList.length" class="rc-bosses">
              <button type="button" class="rc-boss-btn" @click="toggleBosses(c.r.id)">
                {{ openBosses[c.r.id] ? '收起首领名单 ▴' : '速览全部 ' + c.bossList.length + ' 位首领 ▾' }}
              </button>
              <ol v-if="openBosses[c.r.id]" class="rc-boss-ol">
                <li v-for="b in c.bossList" :key="b.id">{{ b.nameCn }}</li>
              </ol>
            </div>

            <div class="rc-btns">
              <router-link :to="{ path: '/dungeon', query: { d: c.r.id } }" class="cta-cut">
                首领、地图与掉落 →
              </router-link>
              <button v-if="c.attuneRequired" type="button" class="ghost rc-subbtn" @click="jumpTo('onyxia-attune')">
                打卡黑龙门任务 ↓
              </button>
              <button v-else-if="c.hasT1Sets" type="button" class="ghost rc-subbtn" @click="jumpTo('hyjal-t1')">
                看 18 套 T1 套装 ↓
              </button>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- 奥妮克希亚开门任务（龙火护符）交互式打卡清单 -->
    <section v-if="attune" class="card attune-card" id="onyxia-attune">
      <div class="bhead">
        <div>
          <div class="kicker">ONYXIA ATTUNEMENT CHECKLIST</div>
          <h2 class="bt">奥妮克希亚开门任务（{{ attune.itemName }}）打卡清单</h2>
        </div>
        <div class="attune-head-r">
          <span class="attune-prog mono">已完成 {{ doneCount }} / {{ currentSteps.length }} 步</span>
          <button v-if="doneCount > 0" type="button" class="ghost" @click="resetAttune">重置当前阵营</button>
        </div>
      </div>
      <p class="note">{{ attune.bagRule }} 勾选进度自动保存在本机浏览器，下次打开接着做。</p>

      <div class="attune-bar">
        <div class="picks" role="group" aria-label="选择阵营">
          <button type="button" class="pick" :class="{ on: attuneFac === 'alliance' }" @click="setFac('alliance')">
            <b>联盟（{{ (attune.alliance || []).length }} 步）</b>
          </button>
          <button type="button" class="pick" :class="{ on: attuneFac === 'horde' }" @click="setFac('horde')">
            <b>部落（{{ (attune.horde || []).length }} 步）</b>
          </button>
        </div>
        <div class="attune-meter" aria-hidden="true">
          <span class="attune-fill" :style="{ width: doneRatio + '%' }"></span>
        </div>
      </div>

      <ol class="attune-list">
        <li v-for="st in currentSteps" :key="st.id" class="attune-item" :class="{ done: !!checkedMap[st.id] }">
          <label class="attune-check">
            <input type="checkbox" :checked="!!checkedMap[st.id]" @change="toggleStep(st.id)">
            <span class="attune-num mono">{{ st.step }}</span>
          </label>
          <div class="attune-body">
            <div class="attune-top">
              <b class="attune-q">{{ st.questCn }}</b>
              <span v-if="st.zone" class="attune-zone">{{ st.zone }}</span>
              <span v-if="st.npc" class="dim attune-npc">· {{ st.npc }}</span>
            </div>
            <p class="attune-desc">{{ st.summary }}</p>
          </div>
          <router-link v-if="st.dungeonId" class="attune-go" :to="{ path: '/dungeon', query: { d: st.dungeonId } }">
            看副本 →
          </router-link>
        </li>
      </ol>
    </section>

    <!-- 海加尔峰 T1 套装（18 套）速览 -->
    <section v-if="raidSets.length" class="card" id="hyjal-t1">
      <div class="bhead">
        <div>
          <div class="kicker">HYJAL SUMMIT · TIER 1</div>
          <h2 class="bt">海加尔峰 T1 套装速览（{{ raidSets.length }} 套）</h2>
        </div>
        <router-link class="cta" :to="{ path: '/bis' }">前往配装页看 60 级团前与 T1 →</router-link>
      </div>
      <div class="picks t1-cls-bar">
        <button type="button" class="pick" :class="{ on: t1Cls === '' }" @click="t1Cls = ''">
          <b>全部职业（{{ raidSets.length }}）</b>
        </button>
        <button v-for="c in t1Classes" :key="c.cls" type="button" class="pick"
                :class="{ on: t1Cls === c.cls }" @click="t1Cls = c.cls">
          <b>{{ c.clsCn }}</b>
        </button>
      </div>
      <div class="boardwrap">
        <table class="board">
          <thead>
            <tr>
              <th>职业</th>
              <th>套装名称</th>
              <th>定位</th>
              <th>适配专精</th>
              <th>护甲</th>
              <th class="c-num">件数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rs in filteredRaidSets" :key="rs.id">
              <td><b>{{ rs.clsCn }}</b></td>
              <td><b>{{ rs.name }}</b> <span class="dim mono">#{{ rs.setId }}</span></td>
              <td>{{ rs.roleCn }}</td>
              <td class="dim">{{ rs.spec }}</td>
              <td class="dim">{{ rs.armor }}</td>
              <td class="c-num mono">{{ rs.pieceCount }} 件</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 三步时间带：日期取自 timeline.json -->
    <section class="tl3" style="margin-top:24px">
      <template v-for="(n, i) in tlSeq" :key="i">
        <span v-if="n.link" class="link"></span>
        <div v-else class="node">
          <i :style="{ background: n.col }"></i>
          <div><b>{{ n.lab }}</b><span :style="{ color: n.col }">{{ n.date }}</span></div>
        </div>
      </template>
    </section>

    <div class="card">
      <div class="stats">
        <div class="stat"><b>{{ P.claimed.length }}</b>首批开放团本</div>
        <div class="stat"><b>{{ raidSets.length }}</b>海加尔峰 T1 套装</div>
        <div class="stat"><b>{{ P.names.length }}</b>客户端团队条目</div>
        <div class="stat"><b>{{ P.named }}</b>已定中文名</div>
      </div>
    </div>

    <!-- 客户端队伍查找器团队条目（保留既有全量对照表与筛选） -->
    <div class="card" id="client">
      <h2>客户端可排队的团队条目</h2>
      <div class="field">
        <input id="rq" type="search" placeholder="按英文名筛，例如 Onyxia" aria-label="按英文名筛团本"
               :value="q" @input="onFilter">
        <span class="dim mono" id="rcnt">{{ shown.length }} / {{ P.names.length }}</span>
      </div>
      <template v-if="shown.length">
        <template v-for="b in bands" :key="b.key">
          <div class="band"><b>{{ b.label }}</b><span v-if="b.count !== null" class="dim mono">{{ b.count }} 座</span></div>
          <div class="boardwrap">
            <table class="board rtab">
              <colgroup><col style="width:30%"><col style="width:14%"><col style="width:12%"><col style="width:12%"><col></colgroup>
              <thead><tr><th>客户端里的名字</th><th>排队等级</th><th>一次几人</th><th>排队条目</th><th>本站</th></tr></thead>
              <tbody>
                <tr v-for="x in b.rows" :key="x.nameEn">
                  <td><b>{{ x.nameEn }}</b><span v-if="!x.st" class="dim">　中文定名未公布</span></td>
                  <td class="mono">{{ x.levelRange }} 级</td>
                  <td class="mono">{{ sizeText(x) }}</td>
                  <td class="mono">{{ entryText(x) }}</td>
                  <td>
                    <template v-if="x.st">
                      <span class="dim">{{ x.matchedIn === 'raid' ? '已有这一座：' : '按地下城收录：' }}</span><component :is="x.st.link.to ? 'router-link' : 'a'" v-bind="x.st.link">{{ x.st.label }}</component>
                    </template>
                    <template v-else><span class="dim">还没有名单</span></template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </template>
      <div v-else class="empty">没有匹配的名字；这一列只有客户端里的英文原名。</div>
    </div>
  </template>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { assetUrl, load } from '../lib/data.js';
import { linkFor } from '../lib/nav.js';
import { clockText } from '../lib/fmt.js';
import { useCountdown } from '../lib/countdown.js';

const HERO = 'img/gen/banner-cloudsea.webp';
const CARD_ART = {
  'barrow-deeps': 'img/art/dungeons/barrow-deeps.webp',
  'hyjal-summit': 'img/art/dungeons/hyjal-summit-v2.webp',
  'onyxias-lair': 'img/art/dungeons/onyxias-lair.webp'
};
const ATTUNE_KEY = 'wow_forever_v1_onyxia_attune_v1';

const { left: cdLeft, phase: cdPhase } = useCountdown();
const D = ref(null);
const err = ref('');
const route = useRoute();
const q = ref(String(route.query.q || ''));
const openBosses = reactive({});
const attuneFac = ref('alliance');
const checkedMap = reactive({});
const t1Cls = ref('');

function loadSavedAttune() {
  try {
    const raw = window.localStorage.getItem(ATTUNE_KEY);
    if (!raw) return;
    const obj = JSON.parse(raw);
    if (obj && (obj.fac === 'alliance' || obj.fac === 'horde')) attuneFac.value = obj.fac;
    if (obj && obj.done && typeof obj.done === 'object') {
      Object.keys(obj.done).forEach((k) => { if (obj.done[k]) checkedMap[k] = true; });
    }
  } catch (_) {}
}

function persistAttune() {
  try {
    const done = {};
    Object.keys(checkedMap).forEach((k) => { if (checkedMap[k]) done[k] = true; });
    window.localStorage.setItem(ATTUNE_KEY, JSON.stringify({ fac: attuneFac.value, done }));
  } catch (_) {}
}

function setFac(f) {
  attuneFac.value = f;
  persistAttune();
}

function toggleStep(id) {
  checkedMap[id] = !checkedMap[id];
  persistAttune();
}

function resetAttune() {
  currentSteps.value.forEach((st) => { delete checkedMap[st.id]; });
  persistAttune();
}

function toggleBosses(id) {
  openBosses[id] = !openBosses[id];
}

function jumpTo(id) {
  const el = document.getElementById(id);
  if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function boot() {
  err.value = '';
  Promise.all([
    load('data/queue.json').catch(() => ({})),
    load('data/dungeons.json'),
    load('data/timeline.json').catch(() => ({ items: [] })),
    load('data/raid-launch.json').catch(() => null),
    load('data/bis.json').catch(() => ({ raidSets: [] }))
  ])
    .then((rs) => {
      D.value = {
        QU: rs[0] || {},
        DG: rs[1],
        TL: (rs[2] || {}).items || [],
        RL: rs[3] || null,
        BIS: rs[4] || {}
      };
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}

loadSavedAttune();
boot();
onMounted(boot);

const P = computed(() => {
  if (!D.value) return null;
  const QU = D.value.QU, DG = D.value.DG, TL = D.value.TL;
  const rows = (QU.items || []).filter((x) => x.kind === 'raid');
  const claimed = DG.raids || [];
  const dunIds = {};
  [].concat(DG.newDungeons || [], DG.classicDungeons || []).forEach((x) => { dunIds[x.id] = x; });
  const raidById = {};
  claimed.forEach((x) => { raidById[x.id] = x; });
  const grp = {}, order = [];
  rows.forEach((x) => {
    if (!grp[x.nameEn]) { grp[x.nameEn] = []; order.push(x.nameEn); }
    grp[x.nameEn].push(x);
  });
  const names = order.map((k) => {
    const list = grp[k], sizes = [], diffs = {};
    let matched = null;
    list.forEach((x) => {
      if (x.partySize && sizes.indexOf(x.partySize) < 0) sizes.push(x.partySize);
      if (x.matchedId && !matched) matched = x.matchedId;
      diffs[String(x.partySize)] = 1;
    });
    sizes.sort((a, b) => b - a);
    const matchedIn = matched ? (raidById[matched] ? 'raid' : (dunIds[matched] ? 'dungeon' : '')) : '';
    let st = null;
    if (matchedIn === 'raid') {
      const rr = raidById[matched];
      st = { label: (rr && (rr.nameCn || rr.nameEn)) || matched, link: dLinkProps(matched) };
    } else if (matchedIn === 'dungeon') {
      const dn = dunIds[matched];
      st = { label: (dn && dn.nameCn) || matched, link: dLinkProps(matched) };
    }
    return {
      nameEn: k, entries: list.length, sizes,
      multiSize: Object.keys(diffs).length > 1,
      levelRange: list[0].levelRange,
      matched, matchedIn, st,
      prov: list[0].provenance || []
    };
  });
  names.sort((a, b) => (b.sizes[0] || 0) - (a.sizes[0] || 0) || a.nameEn.localeCompare(b.nameEn));
  const both = names.filter((x) => x.matchedIn === 'raid').length;
  const nextRaid = TL.filter((x) => x.id === 'raids-dec10-cn')[0]
    || TL.filter((x) => /团本|团队副本/.test(x.title || ''))[0] || null;
  const beta = TL.filter((x) => /国服 Beta 开启/.test(x.title || ''))[0] || null;
  const launch = TL.filter((x) => /全球同步上线/.test(x.title || ''))[0]
    || TL.filter((x) => /国服/.test(x.title || '') && /上线/.test(x.title || ''))[0] || null;
  const named = claimed.filter((r) => r.nameCn).length;
  return { claimed, names, both, nextRaid, beta, launch, named };
});

const rlById = computed(() => {
  const m = {};
  const list = (D.value && D.value.RL && D.value.RL.raids) || [];
  list.forEach((r) => { m[r.id] = r; });
  return m;
});

const unlockDate = computed(() => (D.value && D.value.RL && D.value.RL.unlockDate) || '2026-12-10');
const unlockDateCn = computed(() => {
  const parts = String(unlockDate.value).split('-');
  return parts.length === 3 ? `${Number(parts[1])} 月 ${Number(parts[2])} 日` : unlockDate.value;
});
const resetCycle = computed(() => (D.value && D.value.RL && D.value.RL.resetCycle) || '每周重置');
const attune = computed(() => (D.value && D.value.RL && D.value.RL.onyxiaAttunement) || null);
const currentSteps = computed(() => (attune.value && attune.value[attuneFac.value]) || []);
const doneCount = computed(() => currentSteps.value.filter((st) => !!checkedMap[st.id]).length);
const doneRatio = computed(() => (currentSteps.value.length ? Math.round((doneCount.value / currentSteps.value.length) * 100) : 0));

const raidSets = computed(() => (D.value && D.value.BIS && D.value.BIS.raidSets) || []);
const t1Classes = computed(() => {
  const seen = new Set();
  const out = [];
  raidSets.value.forEach((rs) => {
    if (!seen.has(rs.cls)) {
      seen.add(rs.cls);
      out.push({ cls: rs.cls, clsCn: rs.clsCn });
    }
  });
  return out;
});
const filteredRaidSets = computed(() => (t1Cls.value ? raidSets.value.filter((x) => x.cls === t1Cls.value) : raidSets.value));

const cards = computed(() => {
  if (!P.value) return [];
  return P.value.claimed.map((r) => {
    const info = rlById.value[r.id] || {};
    const party = info.partySize || r.partySize || r.sizeClaim || '';
    return {
      r,
      partyText: party ? party + ' 人团本' : '团本',
      bosses: (r.bosses || []).length || info.bossCount || 0,
      bossList: r.bosses || [],
      zoneCn: info.zoneCn || r.zoneCn || '',
      entrances: info.entrances || '',
      summary: info.summary || '',
      attuneRequired: !!info.attunementRequired,
      attuneItem: info.attunementItem || '',
      attuneNote: info.attunementNote || '',
      hasT1Sets: !!info.hasT1Sets,
      art: r.art || CARD_ART[r.id] || HERO
    };
  });
});

function sizeText(x) { return x.sizes.length ? x.sizes.join(' / ') + ' 人' : '未标'; }
function entryText(x) {
  if (x.entries < 2) return '1 条';
  return x.entries + ' 条（' + (x.multiSize ? '两种规模' : '同规模的两个入口') + '）';
}

const shown = computed(() => {
  const k = q.value.trim().toLowerCase();
  if (!P.value) return [];
  return k ? P.value.names.filter((x) => x.nameEn.toLowerCase().indexOf(k) >= 0) : P.value.names;
});

const tlSeq = computed(() => {
  if (!P.value) return [];
  const seq = [];
  if (P.value.beta) seq.push({ lab: '国服 Beta 测试', col: 'var(--txt-muted)', date: P.value.beta.date });
  if (P.value.beta && P.value.launch) seq.push({ link: true });
  if (P.value.launch) seq.push({ lab: P.value.launch.title, col: 'var(--ok)', date: P.value.launch.date });
  if (P.value.launch && P.value.nextRaid) seq.push({ link: true });
  if (P.value.nextRaid) seq.push({ lab: P.value.nextRaid.title, col: 'var(--gold-hi)', date: P.value.nextRaid.date });
  return seq;
});

const bands = computed(() => {
  const out = [];
  [40, 25, 20, 15, 10].forEach((n) => {
    const pick = shown.value.filter((x) => (x.sizes[0] || 0) === n);
    if (!pick.length) return;
    out.push({ key: String(n), label: n + ' 人团队条目', count: pick.length, rows: pick });
  });
  const rest = shown.value.filter((x) => [40, 25, 20, 15, 10].indexOf(x.sizes[0] || 0) < 0);
  if (rest.length) out.push({ key: 'rest', label: '人数未标', count: null, rows: rest });
  return out;
});

function onFilter(e) { q.value = e.target.value; }

function dLinkProps(id) {
  const l = linkFor('dungeon.html');
  return l.to ? { to: { path: l.to, query: { d: id } } }
    : { href: l.href + '?d=' + encodeURIComponent(id) };
}
</script>

<style scoped>
.raid-hero { min-height: 310px; height: auto; padding-bottom: 28px; }
.raid-hero-b { padding-top: 64px; max-width: 780px; }
.raid-hero-h1 { font-family: var(--font-display); font-size: clamp(30px, 3.8vw, 44px); margin: 10px 0 10px; color: var(--txt-title); }
.raid-hero-sub { font-size: 15px; color: var(--txt-dim); margin: 0 0 18px; line-height: 1.65; }
.raid-hero-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.raid-hero-cd { display: flex; align-items: center; gap: 10px; }
.raid-cd-clk { display: block; font-size: 12px; color: var(--gold-hi); margin-top: 2px; }
.dot-on { background: var(--warn); }
.dot-ok { background: var(--ok); }

.raid-sec { padding: 28px 0 0; }
.raidcard-v2 .art { position: relative; min-height: 170px; }
.raidcard-v2 .rc-title { position: absolute; left: 16px; bottom: 26px; margin: 0; font-family: var(--font-display); font-size: 22px; color: var(--txt-title); z-index: 2; }
.raidcard-v2 .rc-en { position: absolute; left: 16px; bottom: 8px; font-size: 12px; color: var(--txt-dim); z-index: 2; }
.chip-ok { color: var(--ok); border-color: var(--ok); }
.chip-warn { color: var(--warn); border-color: var(--amber-line); }

.rc-sum { margin: 0 0 12px; font-size: 13.5px; line-height: 1.6; color: var(--txt-dim); }
.rc-kv { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 12px; padding: 10px 12px; background: var(--sunk); border: 1px solid var(--line); margin-bottom: 12px; }
.rc-kv > div { display: flex; flex-direction: column; gap: 2px; font-size: 12.5px; }
.rc-kv b { color: var(--txt-title); font-size: 13.5px; }
.rc-meta-line { font-size: 13px; color: var(--txt-dim); line-height: 1.55; margin-bottom: 8px; }
.rc-lbl { display: inline-block; margin-right: 8px; padding: 1px 6px; font-size: 11px; color: var(--gold-hi); background: var(--panel); border: 1px solid var(--gold-line); }
.rc-attune-hi { padding: 8px 10px; background: var(--panel); border-left: 2px solid var(--warn); color: var(--txt); }

.rc-bosses { margin: 10px 0 14px; }
.rc-boss-btn { width: 100%; text-align: left; padding: 7px 10px; font-size: 12.5px; color: var(--gold-hi); background: var(--sunk); border: 1px dashed var(--line-2); cursor: pointer; }
.rc-boss-ol { margin: 8px 0 0; padding: 8px 12px 8px 28px; background: var(--sunk); border: 1px solid var(--line); display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 12px; font-size: 12.5px; color: var(--txt-dim); }
.rc-btns { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.rc-subbtn { padding: 8px 12px; font-size: 13px; }

.attune-card { margin-top: 24px; }
.attune-head-r { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.attune-prog { font-size: 13px; font-weight: 700; color: var(--gold-hi); padding: 4px 10px; background: var(--panel-2); border: 1px solid var(--gold-line); }
.attune-bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin: 12px 0 14px; }
.attune-meter { flex: 1 1 200px; height: 8px; background: var(--sunk); border: 1px solid var(--line); overflow: hidden; }
.attune-fill { display: block; height: 100%; background: linear-gradient(90deg, var(--gold), var(--ok)); transition: width var(--dur-2) var(--ease-out); }

.attune-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.attune-item { display: flex; align-items: flex-start; gap: 12px; padding: 10px 12px; background: var(--panel-2); border: 1px solid var(--line); }
.attune-item.done { border-color: var(--ok); opacity: 0.72; }
.attune-item.done .attune-q { text-decoration: line-through; color: var(--txt-muted); }
.attune-check { display: flex; align-items: center; gap: 8px; cursor: pointer; padding-top: 2px; flex: 0 0 auto; }
.attune-check input { width: 16px; height: 16px; accent-color: var(--gold); cursor: pointer; }
.attune-num { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; font-size: 12px; color: var(--gold-hi); background: var(--sunk); border: 1px solid var(--gold-line); }
.attune-body { flex: 1 1 auto; min-width: 0; }
.attune-top { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 8px; }
.attune-q { font-size: 14px; color: var(--txt-title); }
.attune-zone { font-size: 12px; color: var(--azure); }
.attune-npc { font-size: 12px; }
.attune-desc { margin: 4px 0 0; font-size: 13px; color: var(--txt-dim); line-height: 1.5; }
.attune-go { flex: 0 0 auto; align-self: center; font-size: 12.5px; color: var(--gold-hi); padding: 4px 10px; border: 1px solid var(--gold-line); background: var(--panel); text-decoration: none; white-space: nowrap; }
.attune-go:hover { border-color: var(--gold-hi); text-decoration: none; }

.t1-cls-bar { margin: 10px 0 14px; }
</style>
