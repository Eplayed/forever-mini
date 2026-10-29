<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="R">
    <!-- 与旧站 app.js races() 逐块对齐：主卡在旧站 PAGE_HEAD_SEC 表里（races → img/art/races/human.webp），
         这里的 .cdhead.big + .hicon img 与旧站 decoratePageHead() 的产出逐字一致。
         2026-10-12 站主决定：素材出处角标与"没有可信头像"那类说明不再上内容页，出处集中在溯源页。 -->
    <div class="card">
      <div class="cdhead big">
        <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
        <h1 class="pt">种族与职业组合</h1>
      </div>
      <div class="stats">
        <div class="stat"><b>{{ R.races.length }}</b>种族行</div>
        <div class="stat"><b>{{ traitsCount }}</b>条种族特长</div>
        <div class="stat"><b>{{ R.newCombos.length }}</b>组亮点组合</div>
        <div class="stat"><b>{{ inGloss }}</b>条有中英对照</div>
        <div class="stat"><b>{{ Object.keys(POR).length }}</b>张种族头像</div>
      </div>
      <p v-if="R.skyborneNote && R.skyborneNote.text" class="dim">{{ R.skyborneNote.text }}</p>
    </div>

    <div class="facwrap" id="facbands">
      <div v-for="fac in FACS" :key="fac" class="facband" :class="fac">
        <!-- 阵营城市原画压暗当氛围底；取不到就整个不渲染，纯色带照常显示 -->
        <div v-if="CITY[fac]" class="fembg"><img :src="assetUrl(CITY[fac])" alt="" loading="lazy" @error="cityBad"></div>
        <div class="fhead">
          <img v-if="EMB[fac]" class="femb" :src="assetUrl(EMB[fac])" alt="" loading="lazy" @error="embBad">
          <b>{{ FAC[fac] }}</b><span class="dim">{{ facRows(fac).length }} 个种族行 · {{ facTraits(fac) }} 条种族特长</span>
          <span class="dim mono">{{ fac === 'alliance' ? '人类 / 矮人 / 暗夜精灵 / 侏儒 / 天裔（高阶会）' : '兽人 / 亡灵 / 牛头人 / 巨魔 / 天裔（塑风者）' }}</span>
        </div>
        <div class="racegrid">
          <button v-for="x in facRows(fac)" :key="keyOf(x)" type="button" class="racecard" :class="{ on: sel === keyOf(x) }"
                  :data-race="keyOf(x)" :aria-pressed="sel === keyOf(x) ? 'true' : 'false'" @click="pickRace(keyOf(x))">
            <RaceFace :x="x" />
            <span class="rcn">{{ dispName(x) }}</span>
            <span v-if="isSky(x)" class="tag new">无限新增</span>
            <span class="dim mono">{{ x.classes.length }} 职业 · {{ traitListOf(x).length }} 特长</span>
          </button>
        </div>
      </div>
    </div>

    <div class="card rdetail" id="rdet" ref="rdetEl">
      <template v-if="selRow">
        <div class="rdhead">
          <RaceFace :x="selRow" mod="lg" />
          <div class="rdt">
            <h2>{{ dispName(selRow) }} <span v-if="isSky(selRow)" class="tag new">无限新增</span></h2>
            <p class="dim">{{ FAC[selRow.faction] }} · 可选 {{ selRow.classes.length }} 个职业 · {{ traitListOf(selRow).length }} 条种族特长<template v-if="selRow.nameEn"> · <span class="mono">{{ selRow.nameEn }}</span></template><template v-else> · 官方未公布英文原名</template></p>
          </div>
        </div>
        <p v-if="selRow.lore" class="lore">{{ selRow.lore }}</p>
        <h3 class="rdh">可选职业</h3>
        <div class="rdcls">
          <span v-for="id in cols" :key="id" class="rdcl" :class="{ off: !canBe(selRow, id) }"
                :title="CNAME[id] + (canBe(selRow, id) ? '可选' : '不可选')">
            <ClassTile :class-id="id" :cn="CNAME[id]" :icon-key="CTILE[id] || ''" mod="sm" />
            <i>{{ CNAME[id] }}</i>
          </span>
        </div>
        <h3 class="rdh">种族特长</h3>
        <ul v-if="traitListOf(selRow).length" class="rdtr">
          <li v-for="t in traitListOf(selRow)" :key="selRow.id + t.name">
            <IconCell :icon-key="t.iconKey || ''" :seed="selRow.id + t.name" :cn="t.name" />
            <div class="rdtr-b">
              <b>{{ t.name }}</b>
              <span class="tag">{{ t.passive ? '被动' : '主动' }}</span>
              <p class="quote">{{ t.quote }}</p>
            </div>
          </li>
        </ul>
        <p v-else class="dim">这个种族没有特长条目。</p>
      </template>
      <div v-else class="empty">选一个种族看它的特长。</div>
    </div>

    <div class="card">
      <h2>种族 × 职业矩阵</h2>
      <p class="dim"><template v-if="fc">已按「{{ CNAME[fc] }}」筛选 <button type="button" class="ghost mini" id="cx" @click="clearCls">清除</button></template></p>
      <div class="field">
        <label class="dim">阵营</label>
        <select id="ff" v-model="ff">
          <option value="">全部</option>
          <option value="horde">部落</option>
          <option value="alliance">联盟</option>
        </select>
      </div>
      <div class="scrollx" id="mx">
        <table class="mtx">
          <thead><tr>
            <th class="rh">种族 \ 职业</th>
            <th v-for="id in cols" :key="id">
              <button type="button" class="ch" :class="{ on: fc === id }" :data-cl="id"
                      :aria-pressed="fc === id ? 'true' : 'false'" @click="pickCls(id)">
                <ClassTile :class-id="id" :cn="CNAME[id]" :icon-key="CTILE[id] || ''" mod="sm" />
                <span>{{ CNAME[id] }}</span>
              </button>
            </th>
          </tr></thead>
          <tbody>
            <tr v-for="x in mxRows" :key="keyOf(x)" :class="{ off: fc && x.classes.indexOf(fc) < 0 }" :data-race="keyOf(x)">
              <th class="rh">
                <RaceFace :x="x" mod="sm" />
                <span>{{ x.nameCn }}<em v-if="x.subgroup">{{ x.subgroup.nameCn.replace(x.nameCn, '') }}</em></span>
              </th>
              <td v-for="id in cols" :key="id" :class="canBe(x, id) ? 'y' : 'n'">{{ canBe(x, id) ? '✓' : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- 2026-10-20 站主决定：这一页只给一套数（矩阵表：天裔部落 5 / 联盟 5），
           原来跟在这段位置的"两份说法还没对上"红字撤掉。
           上面那句官方导语是 L0 原文引用、不是分歧标注，留着；
           分歧本身与"两个都留"的处置挪到溯源页（races.json.conflicts 没删）。 -->
    </div>

    <div class="card">
      <h2>新开放的组合</h2>
      <p class="dim">{{ (R.newCombos[0] && R.newCombos[0].provenance[0].quote) || '' }}</p>
      <div class="combos">
        <span v-for="c in R.newCombos" :key="c.label" class="combo">
          <RaceFace v-if="comboRace(c)" :x="comboRace(c)" mod="sm" />
          <b>{{ c.raceCn }}</b>
          <ClassTile :class-id="c.classId || ''" :cn="c.classCn || '?'" :icon-key="CTILE[c.classId] || ''" mod="sm" />
          <b>{{ c.classCn }}</b>
        </span>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 种族与职业组合 · 与旧站 app.js races() 逐块对齐（行 2376-2567）。
   数据全部 load() 现取：races.json（种族行/矩阵/亮点组合/两源分歧）、classes.json（可选职业列）、
   glossary.json（数「有中英对照」的种族词条）、art.json（种族头像/阵营徽记/阵营城市原画）。
   点头像卡换详情并滚动到详情卡；旧站 history.replaceState('#race=…') 的深链在 hash 路由下
   换成 query（/races?r=horde-orc），刷新与分享都能还原，认不出的值落回第一行。 */
import { computed, h, nextTick, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { assetUrl, load } from '../lib/data.js';
import { iconUrl, raceStyle } from '../lib/glyph.js';
import { scrollToEl } from '../lib/motion.js';
import IconCell from '../components/IconCell.vue';
import ClassTile from '../components/ClassTile.vue';

/* 主卡卡片头用的板块图：与首页图标轨「种族」格同一张本地原画（站内同一板块同一张脸）。
   必须走 JS 常量而不是模板字符串字面量——防 Vite 静态解析（参照 WorldPage 的 HEAD_ART）。 */
const HEAD_ART = 'img/art/races/human.webp';

const FAC = { horde: '部落', alliance: '联盟' };
const FACS = ['alliance', 'horde'];   // 旧站 band('alliance') + band('horde')，联盟带在前

const d = ref(null);
const err = ref('');
const sel = ref('');
const fc = ref('');   // 矩阵的 职业 筛选（点表头切换，再点一次取消）
const ff = ref('');   // 矩阵的 阵营 筛选
const rdetEl = ref(null);
const route = useRoute();
const router = useRouter();

function boot() {
  err.value = '';
  Promise.all([load('data/races.json'), load('data/classes.json'), load('data/glossary.json'),
    load('data/art.json').catch(() => ({}))])
    .then((r) => {
      d.value = { R: r[0], classes: r[1].classes || [], gloss: r[2].items || [], ART: r[3] || {} };
      // 深链 ?r=（旧站 urlQ('r') 与 #race= 的 hash 路由等价）：两边命名对不上时以阵营前缀为准
      const rq = String(route.query.r || '');
      const first = ((d.value.R.races || [])[0]);
      sel.value = byKey.value[rq] ? rq : (first ? keyOf(first) : '');
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次

/* ---- 查表 ---- */
const R = computed(() => (d.value && d.value.R) || null);
const classes = computed(() => (d.value && d.value.classes) || []);
const gloss = computed(() => (d.value && d.value.gloss) || []);
const ART = computed(() => (d.value && d.value.ART) || {});
const POR = computed(() => ART.value.races || {});
/* 种族**小图标**：官方 CDN 有 race_* 的那些件照旧走 iconKey；
   天裔两边都没有官方图（AGENTS 素材那一条记过），2026-10-20 站主特批先用插件目录那张
   RaceIcon_Skyborne.tga 转的 webp。它单独一个索引键 raceIcons，
   不与 races 那张大图原画混——传承页拿 races/skyborne 当页头，64px 塞进去就是放大糊。 */
const RACE_ICON = computed(() => ART.value.raceIcons || {});
const EMB = computed(() => ART.value.factions || {});
const CITY = computed(() => ART.value.factionCities || {});
const CNAME = computed(() => { const m = {}; classes.value.forEach((c) => { m[c.id] = c.cn; }); return m; });
const CTILE = computed(() => { const m = {}; classes.value.forEach((c) => { m[c.id] = c.iconKey || null; }); return m; });
const cols = computed(() => ((R.value && R.value.classOrder) || []).filter((id) => CNAME.value[id]));

// 深链 #race=horde-orc：阵营 + 种族 id
function keyOf(x) { return x.faction + '-' + x.id; }
const byKey = computed(() => {
  const m = {};
  ((R.value && R.value.races) || []).forEach((x) => { m[keyOf(x)] = x; });
  return m;
});
const selRow = computed(() => byKey.value[sel.value] || null);

function dispName(x) { return x.subgroup ? x.subgroup.nameCn : x.nameCn; }
function traitListOf(x) { return (x.subgroup ? x.subgroup.traits : x.traits) || []; }
function isSky(x) { return String(x.id).indexOf('skyborne') === 0; }
function canBe(x, id) { return x.classes.indexOf(id) >= 0; }

const traitsCount = computed(() =>
  ((R.value && R.value.races) || []).reduce((a, x) => a + traitListOf(x).length, 0));
const inGloss = computed(() =>
  gloss.value.filter((i) => i.kind === 'racial' && i.raceId).length);

function facRows(fac) { return ((R.value && R.value.races) || []).filter((x) => x.faction === fac); }
function facTraits(fac) { return facRows(fac).reduce((a, x) => a + traitListOf(x).length, 0); }
const mxRows = computed(() => ((R.value && R.value.races) || []).filter((x) => !ff.value || x.faction === ff.value));

/* 亮点组合里找种族行：按展示名（天裔命中子族行）或本名各试一遍，找不到就不放头像 */
function comboRace(c) {
  return ((R.value && R.value.races) || []).filter((y) =>
    dispName(y) === c.raceCn || y.nameCn === c.raceCn)[0] || null;
}

/* ---- 种族头像：与旧站 face() 同一结构——.rface 外壳（自绘阵营块 .liw.t 垫底 + 本地官方图标盖面），
   本地转存的客户端种族头像再盖一层（.rface-art）；两边都没有就只留自绘块，不放假图。
   四处用到（阵营带 / 详情头 / 矩阵行 / 亮点组合），收敛成一个渲染函数组件。 */
function RaceFace(props) {
  const x = props.x;
  const art = isSky(x) ? (POR.value.skyborne || '') : (POR.value[x.id] || '');
  const st = raceStyle(x.id, x.faction, x.nameCn);
  /* 小图标这一层：官方 CDN 有 race_* 的照旧用 iconKey；天裔两边都没有官方图，
     落 raceIcons（插件目录转存、站主 2026-10-20 特批，不称官方已核）。
     两边都拿不到就只是不盖这一层——底下那张自绘首字块就是回退，不放假图。 */
  const small = x.iconKey ? iconUrl(x.iconKey)
    : (isSky(x) && RACE_ICON.value.skyborne ? assetUrl(RACE_ICON.value.skyborne) : '');
  const kids = [h('span', { class: 'liw t' }, [
    h('svg', { viewBox: '0 0 40 40', 'aria-hidden': 'true' }, [
      h('rect', { width: '40', height: '40', rx: '6', fill: st.fill, stroke: st.stroke, 'stroke-opacity': '.7' }),
      h('text', { x: '20', y: '26', 'text-anchor': 'middle', 'font-size': '16', 'font-weight': '600',
        fill: st.text, 'font-family': 'PingFang SC,Microsoft YaHei,sans-serif' }, st.letter)
    ]),
    small ? h('img', { src: small, alt: '', loading: 'lazy',
      onError: (e) => { e.target.className = 'bad'; } }) : null
  ])];
  if (art) {
    kids.push(h('img', { class: 'rface-art', src: assetUrl(art), alt: '', loading: 'lazy', decoding: 'async',
      onError: (e) => { e.target.className = 'rface-art bad'; } }));
  }
  return h('span', { class: ['rface', props.mod || ''] }, kids);
}
RaceFace.props = { x: { type: Object, required: true }, mod: { type: String, default: '' } };

/* ---- 交互 ---- */
function pickRace(key) {
  sel.value = key;
  // 旧站 history.replaceState('#race=…') 的等价：hash 路由下换成 query，刷新与分享都能还原
  router.replace({ path: '/races', query: { r: key } });
  nextTick(() => {
    const t = rdetEl.value;
    scrollToEl(t);
  });
}
function pickCls(id) { fc.value = fc.value === id ? '' : id; }
function clearCls() { fc.value = ''; }
function cityBad(e) { e.target.parentNode.className = 'fembg bad'; }
function embBad(e) { e.target.className = 'femb bad'; }
</script>
