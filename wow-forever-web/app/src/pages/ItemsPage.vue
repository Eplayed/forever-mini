<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <!-- 新站独有页（旧站已冻结，无对拍基准）。交互口径照站主拍板的原型
         docs/prototypes/items-page-prototype.html：状态/分类/细分/等级区间/搜索/排序/分页。
         数据全部来自 src/data/items.json（21,077 件全量名录），单源 L0：客户端解包经参考站转述。 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">物品库</h1></div>
      <p class="dim">测试版客户端里的每件物品，与经典旧世逐条对照：新增、改动、不变，还是无限里已经没有。
        名录出自客户端解包（经<a :href="srcUrl" target="_blank" rel="noopener">新手盒子</a>转述，
        {{ d.meta.fetched }} 取回），只记名称、品质、类型与等级这些事实；点任意一行可看详情——
        属性与卖价先按两份插件资料（Beta 实测掉落记录与社区整理稿），这两份没有的才按当前测试版客户端补；
        出处按 Beta 实测掉落记录补。没有的那一段就不显示。
        图标取自暴雪官方 CDN 本地转存，官方没有的那一部分从测试版客户端导出补上，取不到的用占位块。</p>
      <div class="stats readout">
        <div class="stat"><b>{{ items.length }}</b>件全量</div>
        <div class="stat"><b>{{ C.new }}</b>无限新增</div>
        <div class="stat"><b>{{ C.changed }}</b>有改动</div>
        <div class="stat"><b>{{ C.missing }}</b>无限中没有</div>
      </div>
    </div>

    <div class="card">
      <div class="field irow">
        <span class="flabel">状态</span>
        <span class="kchips">
          <button v-for="x in stChips" :key="x[0]" type="button" class="kchip"
                  :class="{ on: st === x[0] }" :aria-pressed="st === x[0] ? 'true' : 'false'"
                  @click="st = st === x[0] && x[0] ? '' : x[0]">{{ x[1] }} <b class="mono">{{ x[2] }}</b></button>
        </span>
      </div>
      <div class="field irow">
        <span class="flabel">分类</span>
        <span class="kchips">
          <button v-for="x in catChips" :key="x[0]" type="button" class="kchip"
                  :class="{ on: cat === x[0] }" :aria-pressed="cat === x[0] ? 'true' : 'false'"
                  @click="pickCat(x[0])">{{ x[1] }} <b class="mono">{{ x[2] }}</b></button>
        </span>
        <button type="button" class="reset" @click="reset">重置筛选</button>
      </div>
      <div class="field irow">
        <span class="flabel">细分</span>
        <span v-if="cat === '护甲'" class="kchips">
          <button v-for="x in matChips" :key="x[0]" type="button" class="kchip"
                  :class="{ on: mat === x[0] }" :aria-pressed="mat === x[0] ? 'true' : 'false'"
                  @click="mat = mat === x[0] ? '' : x[0]; page = 1">{{ x[0] }} <b class="mono">{{ x[1] }}</b></button>
        </span>
        <select v-model="slot" aria-label="按部位筛" @change="page = 1">
          <option value="">全部部位</option>
          <option v-for="s in slotOpts" :key="s" :value="s">{{ s }}</option>
        </select>
        <span class="rng">物品等级
          <input v-model.number="ilMin" type="number" min="1" placeholder="最低" aria-label="物品等级最低">
          –
          <input v-model.number="ilMax" type="number" min="1" placeholder="最高" aria-label="物品等级最高">
        </span>
        <select v-model="sort" aria-label="排序方式" @change="page = 1">
          <option value="id">按编号</option>
          <option value="ilvl-d">物品等级 高→低</option>
          <option value="ilvl">物品等级 低→高</option>
          <option value="rlvl">需要等级 低→高</option>
          <option value="name">按名称</option>
        </select>
      </div>
      <div class="field"><input v-model="qRaw" type="search" class="qsearch"
             placeholder="搜物品名，比如：雷霆之怒、秘法、护腕…" aria-label="搜物品名"></div>
    </div>

    <div class="card" ref="tableCard">
      <table class="itt">
        <thead><tr><th>名称</th><th>类型 / 材质</th><th class="num">物品等级</th><th class="num">需要等级</th><th>状态</th><th class="num">编号</th></tr></thead>
        <tbody>
          <tr v-for="(x, i) in pageRows" :key="x.id" :style="{ animationDelay: Math.min(i * 14, 280) + 'ms' }"
              class="row" tabindex="0" :aria-label="x.name + ' 详情'"
              @click="openRow(x)" @keydown.enter.prevent="openRow(x)">
            <td data-k="名称">
              <span class="icell"><IconCell :icon-key="x.iconKey || ''" :seed="x.id" :cn="x.name" />
                <span class="nm" :class="'q' + (x.quality || 0)"><HlText :text="x.name" :q="q" /></span></span>
            </td>
            <td data-k="类型">{{ typeText(x) }}</td>
            <td class="num" data-k="物品等级">{{ x.ilvl == null ? '—' : x.ilvl }}</td>
            <td class="num" data-k="需要等级">{{ x.rlvl == null ? '—' : x.rlvl }}</td>
            <td data-k="状态"><span class="ist" :class="'ist-' + statusKey(x)">{{ STN[statusKey(x)] || statusKey(x) }}</span></td>
            <td class="num" data-k="编号"><span class="iid">#{{ x.id }}</span></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!rows.length" class="empty">这个筛选下没有条目。换个说法，或清掉几个筛选再试。</div>
      <div v-if="pages > 1" class="pager">
        <button type="button" :disabled="page === 1" @click="go(1)">«</button>
        <button type="button" :disabled="page === 1" @click="go(page - 1)">‹</button>
        <button v-for="p in pagerWin" :key="p" type="button" :class="{ on: p === page }" @click="go(p)">{{ p }}</button>
        <button type="button" :disabled="page === pages" @click="go(page + 1)">›</button>
        <button type="button" :disabled="page === pages" @click="go(pages)">»</button>
        <span class="pinfo">共 {{ rows.length }} 件 · 第 {{ page }}/{{ pages }} 页</span>
      </div>
    </div>

    <!-- 详情抽屉（物品线二批，方案 A + W2-3 全量后重排层级；2026-10-16 站主定「取值以插件为准」）：
         首次点行才拉 items-detail.json，列表页首屏零负担。
         属性与卖价按"Beta 实测掉落 → 社区整理稿 → 无限测试版客户端解包（兜底）"取值，
         徽标写明这一条出自哪一份；出处（哪座本、哪个首领）只有实测掉落记录有；
         几份都没有的就不显示那一段，不摆占位。 -->
    <div v-if="sel" class="idmask" @click="close"></div>
    <aside v-if="sel" class="idrawer" role="dialog" aria-modal="true" :aria-label="sel.name + ' 详情'">
      <div class="idh">
        <IconCell :icon-key="sel.iconKey || ''" :seed="sel.id" :cn="sel.name" />
        <div class="idt">
          <div class="nm" :class="'q' + (sel.quality || 0)">{{ sel.name }}</div>
          <div class="ids">#{{ sel.id }} · {{ typeText(sel) }}</div>
          <div class="ids">物品等级 {{ sel.ilvl == null ? '—' : sel.ilvl }} · 需要等级 {{ sel.rlvl == null ? '—' : sel.rlvl }}</div>
        </div>
        <span class="ist" :class="'ist-' + statusKey(sel)">{{ STN[statusKey(sel)] || statusKey(sel) }}</span>
        <button type="button" class="idclose" aria-label="关闭详情" @click="close">×</button>
      </div>
      <div v-if="dErr" class="idempty">详情数据没加载出来，刷新一下再试。</div>
      <div v-else-if="!itd" class="idempty">详情加载中…</div>
      <template v-else>
        <div v-if="rec && rec.st && rec.st.length" class="idsec">
          <h3 class="idh3">属性 / 提示
            <span class="idbadge">{{ FROMN[rec.stFrom] || '客户端数据' }}</span>
          </h3>
          <ul class="idl"><li v-for="(s, i) in rec.st" :key="i">{{ s }}</li></ul>
        </div>
        <div v-if="rec && rec.use" class="idsec">
          <h3 class="idh3">学会 / 启动 <span class="idbadge">{{ FROMN[rec.useFrom] || '客户端数据' }}</span></h3>
          <div class="idv">{{ rec.use }}</div>
        </div>
        <div v-if="rec && rec.sell" class="idsec">
          <h3 class="idh3">卖价 <span class="idbadge">{{ FROMN[rec.sellFrom] || FROMN.xr }}</span></h3>
          <div class="idv">{{ rec.sell }}</div>
        </div>
        <div v-if="rec && rec.src" class="idsec">
          <h3 class="idh3">出处 <span class="idbadge">beta 解包 · GearInsight 转述</span></h3>
          <div class="idv">{{ SRCN[rec.src] || rec.src }}<template v-if="rec.srcName"> · {{ rec.srcName }}</template></div>
        </div>
        <div v-if="!rec" class="idempty">这一件的详情还没收录。</div>
      </template>
      <!-- 这段说明由合并脚本写在数据里（meta.pageNote），页面不另抄一份，避免改了源忘了改文案 -->
      <p v-if="itd && itd.meta" class="dim idnote">{{ itd.meta.pageNote }}</p>
    </aside>
  </template>
</template>

<script setup>
/* 物品库：全量名录的筛与查。一次载入 items.json（约 5MB，gzip 后小得多），
   筛选/排序/分页全在本页内存里做——21,077 条线性扫一遍在毫秒级，不需要后端。
   物品不进全站搜索索引（会把 search.json 撑大一倍），本页自带页内搜索；
   ?q= 与 ?st= 仍接住：将来任何入口（更新说明、副本掉落反链）带着词跳进来都能落地。 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import IconCell from '../components/IconCell.vue';
import HlText from '../components/HlText.vue';

const STN = { new: '新增', changed: '改动', rebuilt: '重建', same: '不变', missing: '无限中没有', srvHas: '测试服有' };
const ST_ORDER = ['new', 'changed', 'rebuilt', 'same', 'srvHas', 'missing'];
/* 2026-10-21 A03：状态这一列改按"以插件为准"显示（站主 2026-10-20 定的口径）。
   名录侧那条 status 是参考站自报，探针那条 srv 是玩家 10-19 在测试服逐件实测；
   两边正向不冲突（探针说没有的 793 件参考站也说没有），反向有 82 件——
   参考站标"无限中没有"、探针却确认服务器有。这 82 件显示成"测试服有"，
   原来那条留在数据里没删（status 字段照旧），对不上的条数写在溯源页。
   列、筛选条、计数三处都走同一个 statusKey，不然又会出现"格子的数和点出来的不一样"。 */
function statusKey(x) {
  return x.status === 'missing' && x.srv === 'present' ? 'srvHas' : x.status;
}
const PER = 50;
const srcUrl = 'https://wowforever.wclbox.com/wupin';
const SRCN = { dungeon: '地下城', quest: '任务' };
/* 属性与卖价各按哪一份补的：抽屉里逐条标出来，顺序就是取值顺序——
   Beta 实测掉落 → 社区整理稿 → 无限测试版客户端解包（兜底）。
   这是站主 2026-10-16 定的"取值以插件为准"，把 10-15 那版反过来的；两说的原始数值都留档。 */
const FROMN = {
  wclbox: '无限测试版 · 客户端解包',
  gi: 'beta 实测 · GearInsight 转述',
  xr: '社区整理 · XR 助手转述'
};

const route = useRoute();
const d = ref(null);
const err = ref('');
const st = ref(String(route.query.st || ''));
const cat = ref('');
const mat = ref('');
const slot = ref('');
const ilMin = ref(null);
const ilMax = ref(null);
const q = ref(String(route.query.q || ''));
const qRaw = ref(q.value);
const sort = ref('id');
const page = ref(1);
const tableCard = ref(null);

/* 详情抽屉：sel 是列表行对象；itd 是懒加载的 items-detail.json（首次点行才拉） */
const sel = ref(null);
const itd = ref(null);
const dErr = ref(false);
let itdStarted = false;

function openRow(x) {
  sel.value = x;
  if (!itdStarted) {
    itdStarted = true;
    load('data/items-detail.json').then((r) => { itd.value = r; }).catch(() => { dErr.value = true; });
  }
}
function close() { sel.value = null; }
function onKey(e) { if (e.key === 'Escape') close(); }
onMounted(() => window.addEventListener('keydown', onKey));
onBeforeUnmount(() => { window.removeEventListener('keydown', onKey); close(); });

const rec = computed(() => {
  if (!itd.value || !sel.value) return null;
  return itd.value.items[String(sel.value.id)] || null;
});

function boot() {
  err.value = '';
  load('data/items.json')
    .then((r) => {
      d.value = r;
      // 带着状态或词跳进来时，筛好再给看，别让人自己点一遍
      if (st.value && !ST_ORDER.includes(st.value)) st.value = '';
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
onMounted(boot);

/* hash 路由同路径换 query 时组件复用（router-view 按 path 做 key），补齐重读 */
watch(() => route.query, () => {
  const nq = String(route.query.q || '');
  const ns = String(route.query.st || '');
  q.value = nq; qRaw.value = nq;
  st.value = ST_ORDER.includes(ns) ? ns : '';
  page.value = 1;
});

/* 搜索 150ms 防抖：输入框即时回显，筛选延迟生效 */
let qTimer = 0;
watch(qRaw, (v) => {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { q.value = v; page.value = 1; }, 150);
});
watch([st, cat, mat, slot, ilMin, ilMax], () => { page.value = 1; });

const items = computed(() => (d.value && d.value.items) || []);
const C = computed(() => ((d.value || {}).meta || {}).counts || {});
const stChips = computed(() => {
  const n = {};
  items.value.forEach((x) => { const k = statusKey(x); n[k] = (n[k] || 0) + 1; });
  return [['', '全部', items.value.length],
    ...ST_ORDER.filter((k) => n[k]).map((k) => [k, STN[k], n[k]])];
});
const catChips = computed(() => {
  const n = {};
  items.value.forEach((x) => { n[x.cat] = (n[x.cat] || 0) + 1; });
  return [['', '全部', items.value.length],
    ...Object.keys(n).sort().map((k) => [k, k, n[k]])];
});
/* 材质只在护甲下有意义；部位跟着分类与材质走 */
const matChips = computed(() => {
  if (cat.value !== '护甲') return [];
  const n = {};
  items.value.forEach((x) => { if (x.cat === '护甲' && x.mat) n[x.mat] = (n[x.mat] || 0) + 1; });
  return Object.keys(n).sort().map((k) => [k, n[k]]);
});
const slotOpts = computed(() => {
  const s = new Set();
  items.value.forEach((x) => {
    if (x.slot && (!cat.value || x.cat === cat.value) && (!mat.value || x.mat === mat.value)) s.add(x.slot);
  });
  return [...s].sort();
});
function pickCat(v) {
  cat.value = cat.value === v && v ? '' : v;
  mat.value = ''; slot.value = '';
}

const rows = computed(() => {
  const kw = q.value.trim().toLowerCase();
  const lo = Number.isFinite(ilMin.value) ? ilMin.value : null;
  const hi = Number.isFinite(ilMax.value) ? ilMax.value : null;
  const xs = items.value.filter((x) =>
    (!st.value || statusKey(x) === st.value) &&
    (!cat.value || x.cat === cat.value) &&
    (!mat.value || x.mat === mat.value) &&
    (!slot.value || x.slot === slot.value) &&
    (lo == null || (x.ilvl != null && x.ilvl >= lo)) &&
    (hi == null || (x.ilvl != null && x.ilvl <= hi)) &&
    (!kw || x.name.toLowerCase().indexOf(kw) >= 0));
  const by = {
    id: (a, b) => a.id - b.id,
    'ilvl-d': (a, b) => ((b.ilvl || 0) - (a.ilvl || 0)) || a.id - b.id,
    ilvl: (a, b) => ((a.ilvl == null ? 9999 : a.ilvl) - (b.ilvl == null ? 9999 : b.ilvl)) || a.id - b.id,
    rlvl: (a, b) => ((a.rlvl == null ? 9999 : a.rlvl) - (b.rlvl == null ? 9999 : b.rlvl)) || a.id - b.id,
    name: (a, b) => a.name.localeCompare(b.name, 'zh')
  }[sort.value];
  return xs.slice().sort(by);
});
const pages = computed(() => Math.max(1, Math.ceil(rows.value.length / PER)));
const pageRows = computed(() => rows.value.slice((page.value - 1) * PER, page.value * PER));
const pagerWin = computed(() => {
  const w = [];
  for (let p = Math.max(1, page.value - 2); p <= Math.min(pages.value, page.value + 2); p++) w.push(p);
  return w;
});
watch(pages, (n) => { if (page.value > n) page.value = n; });

function go(p) {
  page.value = Math.min(Math.max(1, p), pages.value);
  const el = tableCard.value;
  if (el && el.scrollIntoView) el.scrollIntoView({ block: 'start' });
}
function reset() {
  st.value = ''; cat.value = ''; mat.value = ''; slot.value = '';
  ilMin.value = null; ilMax.value = null;
  q.value = ''; qRaw.value = '';
  sort.value = 'id'; page.value = 1;
}
function typeText(x) {
  if (x.slot) return x.slot + (x.mat ? ' · ' + x.mat : '');
  return x.cat === '其它' ? (x.mat || '—') : x.cat;
}
</script>

<style scoped>
/* 本页专属件：筛选行标签、状态章、分页器、清单表与移动端卡片化。
   令牌全部取 tokens.css，不新开颜色（状态章三色照拍板的原型稿）。 */
.irow{flex-wrap:wrap;align-items:center}
.flabel{font-size:12px;color:var(--lead);flex:none;min-width:34px}
.reset{margin-left:auto;background:none;border:1px solid var(--line);color:var(--lead);
  font-size:12px;padding:6px 14px;cursor:pointer}
.reset:hover{color:var(--gold);border-color:var(--gold)}
.rng{display:flex;gap:6px;align-items:center;color:var(--lead);font-size:12.5px}
.rng input{width:72px}
.qsearch{width:100%;margin-top:2px}
/* 状态章（ist：不与共享的溯源章 .st 混用） */
.ist{font-size:10.5px;padding:1.5px 7px;letter-spacing:1px;white-space:nowrap}
.ist-new{background:var(--gold);color:#1a1408;font-weight:700}
.ist-changed{color:var(--azure);border:1px solid rgba(73,174,233,.5)}
.ist-rebuilt{color:#c993e8;border:1px solid rgba(163,53,238,.55)}
.ist-same{color:var(--lead);border:1px solid var(--line)}
.ist-missing{color:#ff9b8f;border:1px solid rgba(199,92,92,.5)}
/* 「测试服有」是探针确认过存在的那 82 件（名录侧原本标"无限中没有"）。
   用与"改动"同一系的中性蓝，不用金色——金色在我们这儿是"无限新增"的专有色。 */
.ist-srvHas{color:var(--azure);border:1px solid rgba(73,174,233,.35);background:rgba(73,174,233,.08)}
/* 清单表 */
.itt{width:100%;border-collapse:collapse;font-size:13.5px}
.itt th{font-size:11.5px;color:var(--lead);font-weight:600;text-align:left;letter-spacing:1px;
  padding:8px 10px;border-bottom:1px solid var(--gold-line,rgba(200,163,92,.3));white-space:nowrap}
.itt td{padding:8px 10px;border-bottom:1px solid rgba(44,56,80,.45);vertical-align:middle}
.itt tbody tr{animation:itn .3s ease both}
.itt tbody tr:hover td{background:rgba(200,163,92,.05)}
@keyframes itn{from{opacity:0;transform:translateY(4px)}to{opacity:1}}
.itt .num{text-align:right;font-family:var(--font-mono);color:var(--lead)}
.itt .iid{color:var(--lead);opacity:.75;font-size:12px}
.icell{display:flex;gap:10px;align-items:center;min-width:0}
.icell .nm{min-width:0;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.itt .q0{color:var(--q0)}
/* 分页器 */
.pager{display:flex;gap:6px;justify-content:center;align-items:center;margin-top:16px;flex-wrap:wrap}
.pager button{background:var(--sunk);border:1px solid var(--line);color:var(--lead);
  min-width:34px;height:32px;font:12.5px var(--font-mono);cursor:pointer}
.pager button.on{background:var(--gold);color:#1a1408;font-weight:700;border-color:var(--gold)}
.pager button:disabled{opacity:.35;cursor:default}
.pinfo{color:var(--lead);font-size:12px;margin:0 8px}
/* 移动端：行变卡（照拍板的原型稿，375px 不横滚） */
@media (max-width:720px){
  .itt thead{display:none}
  .itt tbody tr{display:block;border:1px solid var(--line);margin:8px 0;background:var(--sunk)}
  .itt td{border:0;display:flex;justify-content:space-between;gap:10px;padding:7px 12px}
  .itt td::before{content:attr(data-k);color:var(--lead);font-size:11.5px;flex:none;align-self:center}
  .itt td:first-child{padding-top:12px}
  .itt td:last-child{padding-bottom:12px}
}
/* 详情抽屉：右侧滑出，移动端整宽；令牌取 tokens.css 不新开颜色 */
.row{cursor:pointer}
.row:focus-visible{outline:1px solid var(--gold);outline-offset:-1px}
.idmask{position:fixed;inset:0;background:rgba(4,7,12,.62);z-index:70}
.idrawer{position:fixed;top:0;right:0;bottom:0;width:min(430px,100%);z-index:71;
  background:var(--sunk);border-left:1px solid var(--gold-line,rgba(200,163,92,.3));
  overflow-y:auto;padding:18px 18px 24px;animation:idr .22s ease both}
@keyframes idr{from{transform:translateX(24px);opacity:0}to{transform:none;opacity:1}}
.idh{display:flex;gap:12px;align-items:flex-start;padding-bottom:12px;border-bottom:1px solid var(--line)}
.idt{flex:1;min-width:0}
.idt .nm{font-weight:700;font-size:15.5px}
.ids{color:var(--lead);font-size:12px;margin-top:2px}
.idclose{flex:none;background:none;border:1px solid var(--line);color:var(--lead);
  width:32px;height:32px;font-size:18px;line-height:1;cursor:pointer}
.idclose:hover{color:var(--gold);border-color:var(--gold)}
.idh .ist{flex:none;margin-top:2px}
.idsec{margin-top:16px}
.idh3{font-size:11.5px;color:var(--lead);font-weight:600;letter-spacing:1px;
  display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 6px}
.idbadge{font-size:10.5px;color:var(--lead);border:1px solid var(--line);
  padding:1px 7px;letter-spacing:.5px;font-weight:400;white-space:nowrap}
.idl{margin:0;padding:0;list-style:none;font-size:13.5px;line-height:1.75}
.idl li{padding:2px 0;border-bottom:1px dashed rgba(44,56,80,.35)}
.idv{font-size:13.5px}
.idempty{margin-top:18px;color:var(--lead);font-size:13px;border:1px dashed var(--line);padding:12px 14px}
.idnote{font-size:11.5px;margin-top:20px;line-height:1.7}
</style>
