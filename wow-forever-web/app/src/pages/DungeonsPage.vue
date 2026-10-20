<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="D">
    <!-- 页首：与旧站 app.js dungeons() 的 set() 串逐字对齐（2026-10-13 改版后的卡面口径）。 -->
    <div class="card hero dunhero">
      <div class="herot">
        <span class="kicker">副本 · {{ lohi.lo }} 至 {{ lohi.hi }} 级</span>
        <!-- 卡片头：旧站 decoratePageHead() 会把这页 H1 包进 cdhead big + hicon（板块图），逐字复刻 -->
        <div class="cdhead big">
          <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
          <h1 class="pt">副本手册</h1>
        </div>
        <!-- 2026-10-20 站主决定：内容页只给一个数。原来那句"另有 N 座有两种说法，两个数都留着"撤掉；
             一次几人取自客户端队伍查找器那一条（就是显示的这个），另一说留在 partySizeAlt，
             英文原名同理留在 nameEnClient——两条都在数据里没删，要看到溯源页。 -->
        <p class="dim">共 {{ all.length }} 座：{{ newN }} 座无限新增、{{ clN }} 座经典本、{{ raids.length }} 座团本，按十级一档分。一次几人取自客户端的队伍查找器（{{ nParty }} 座有数）。等级区间一座只给一个数，其中 {{ nSettled }} 座按参考站的副本卡片定过稿。掉落只回答"谁掉了什么"，不写概率。</p>
        <div class="four dunstat">
          <div><s>地下城</s><b>{{ newN + clN }}</b><s>座</s></div>
          <div><s>无限新增</s><b>{{ newN }}</b><s>座</s></div>
          <div><s>首领</s><b>{{ nb }}</b><s>个</s></div>
          <div><s>掉落归属</s><b>{{ nd }}</b><s>条</s></div>
        </div>
      </div>
      <div class="heros"><div class="cd">
        <span>首领与掉落表</span><b class="cdttl">选一座地下城</b>
        <select id="dpick" v-model="pick" class="dunsel" aria-label="直接跳到某一座地下城的详情页" @change="goPick">
          <option value="">按等级段找一座</option>
          <optgroup v-for="g in pickGroups" :key="g.label" :label="g.label">
            <option v-for="y in g.rows" :key="y.id" :value="y.id">{{ (y.nameCn || y.nameEn || y.id) + (y.levelRange ? '（' + y.levelRange + ' 级）' : '') }}</option>
          </optgroup>
        </select>
        <component :is="raidsLink.to ? 'router-link' : 'a'" v-bind="raidsLink" class="cta-cut">团本那一页 →</component>
      </div></div>
    </div>

    <!-- 筛选条：等级输入（1–70，区间对不上就过滤）+ 三枚类型片，行为与旧站 bindDunBar 等价 -->
    <div class="card dunbar">
      <span class="dim">我的等级</span>
      <input id="dlv" v-model="lvInput" type="number" min="1" max="70" step="1" inputmode="numeric"
             placeholder="填你的等级" aria-label="填你的等级，只列等级区间对得上的地下城">
      <button class="ghost" id="dlvc" type="button" @click="lvInput = ''">清空等级</button>
      <span class="fchips">
        <button class="fchip" :class="{ on: kind === 'all' }" type="button" data-k="all" @click="kind = 'all'">全部 {{ newN + clN }}</button>
        <button class="fchip" :class="{ on: kind === 'new' }" type="button" data-k="new" @click="kind = 'new'">无限新增 {{ newN }}</button>
        <button class="fchip" :class="{ on: kind === 'classic' }" type="button" data-k="classic" @click="kind = 'classic'">经典旧世 {{ clN }}</button>
      </span>
    </div>

    <!-- 筛选只重画这一段（旧站 dunListHtml / #dlist） -->
    <div id="dlist">
      <p v-if="lvNum" class="dim">{{ lvNum }} 级落在 {{ rowsFiltered.length }} 座本的等级区间里。区间取本站采用的那个数。</p>
      <template v-for="band in listBands" :key="band.title">
        <div class="band"><b>{{ band.title }}</b><span v-if="band.sub" class="dim">{{ band.sub }}</span><span class="dim mono">{{ band.rows.length }} 座</span></div>
        <div class="dgrid">
          <div v-for="c in band.rows" :key="c.x.id" class="dcard2">
            <!-- 副本横幅：Glyph.dungeonBanner 的等价内联复刻（同算法同类名，SVG 自绘 + 客户端原画盖面） -->
            <div class="dbn2"><span class="dbn2-shade"></span>
              <svg class="dbn-art" viewBox="0 0 320 86" preserveAspectRatio="none" aria-hidden="true">
                <defs>
                  <linearGradient :id="c.b.gid" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" :stop-color="'hsl(' + c.b.hue + ',32%,18%)'" />
                    <stop offset="1" :stop-color="'hsl(' + c.b.hue + ',26%,7%)'" />
                  </linearGradient>
                </defs>
                <rect width="320" height="86" :fill="'url(#' + c.b.gid + ')'" />
                <circle :cx="c.b.mx" cy="21" r="8" :fill="'hsl(' + c.b.hue + ',58%,74%)'" fill-opacity=".38" />
                <polygon :points="'0,86 ' + c.b.pts.join(' ') + ' 320,86'" :fill="'hsl(' + c.b.hue + ',20%,26%)'" fill-opacity=".9" />
              </svg>
              <img v-if="c.b.art" class="dbn-art" :class="{ bad: badArt[c.x.id] }" :src="assetUrl(c.b.art)" alt="" loading="lazy" @error="badArt[c.x.id] = true">
              <span v-if="c.b.seal" class="dbn2-seal">{{ c.b.seal }}</span>
              <span class="dbn2-txt">
                <span v-if="c.b.range" class="dbn2-r">{{ c.b.range }}</span>
                <span class="dbn2-n">{{ c.b.label }}</span>
                <span v-if="c.b.sub" class="dbn2-e">{{ c.b.sub }}</span>
              </span>
            </div>
            <div class="dmeta">
              <span>{{ c.bosses.length ? c.bosses.length + ' 个首领' : '首领待补' }}</span>
              <span>{{ (c.x.drops || []).length ? (c.x.drops || []).length + ' 件掉落' : '掉落待补' }}</span>
              <span v-if="c.x.partySize">一次 {{ c.x.partySize }} 人</span>
              <span v-if="!c.x.levelRange" class="dim">等级区间待实测</span>
              <span v-if="!c.x.nameCn" class="dim">中文定名未公布</span>
            </div>
            <router-link class="dstretch" :to="{ path: '/dungeon', query: { d: c.x.id } }" :aria-label="'看「' + (c.x.nameCn || c.x.nameEn || '这座本') + '」这一座的整页'"></router-link>
            <button class="ghost wide" type="button" :data-d="c.x.id" @click="toggleDrawer(c.x.id)">{{ drawerOf(c.x.id) ? '收起' : '速览首领与掉落' }}</button>
            <div v-show="drawerOf(c.x.id)" class="drawer" :id="'d-' + c.x.id">
              <div v-for="(t, ti) in c.conf" :key="ti" class="conf">{{ t }}</div>
              <div v-if="c.noQueue" class="note">客户端的队伍查找器里还没有这座本，所以现在还不能排队进去，名单与掉落以正式开放后为准。</div>
              <h3>首领与掉落</h3>
              <ul v-if="c.bosses.length" class="bosslist">
                <li v-for="b in c.bosses" :key="b.id">
                  <div class="bh">
                    <span class="liw t sm">
                      <svg viewBox="0 0 40 40" aria-hidden="true">
                        <rect width="40" height="40" rx="6" :fill="'hsl(' + b.f.hue + ',22%,16%)'" :stroke="'hsl(' + b.f.hue + ',30%,42%)'" stroke-opacity=".65" />
                        <text x="20" y="26" text-anchor="middle" font-size="16" font-weight="600" :fill="'hsl(' + b.f.hue + ',46%,78%)'" font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ b.f.letter }}</text>
                      </svg>
                      <img v-if="b.portrait" :class="{ bad: badFace[c.x.id + '|' + b.id] }" :src="assetUrl(b.portrait)" alt="" loading="lazy" @error="badFace[c.x.id + '|' + b.id] = true">
                    </span>
                    <b>{{ b.nameCn }}</b>
                    <span class="dim">{{ b.mine.length ? b.mine.length + ' 件掉落' : '掉落待补' }}</span>
                  </div>
                  <div v-if="b.mine.length" class="loot">
                    <span v-for="y in b.mine" :key="y.itemId" class="loot-i"><IconCell :icon-key="y.iconKey || ''" :seed="y.itemId" :cn="y.nameCn" small />{{ y.nameCn }}<span class="dim mono">#{{ y.itemId }}</span></span>
                  </div>
                </li>
              </ul>
              <p v-else class="dim">这座本还没有首领名单。</p>
              <router-link class="cta-cut" :to="{ path: '/dungeon', query: { d: c.x.id } }">看这一座的整页 →</router-link>
            </div>
          </div>
        </div>
      </template>
      <p v-if="!listBands.length" class="empty">{{ emptyTxt }}</p>
    </div>

    <!-- 团本带：不吃上面的筛选（旧站 dunBandBlock('团队副本', …) 在 #dlist 外） -->
    <template v-if="raids.length">
      <div class="band"><b>团队副本</b><span class="dim">开放时间未定 · <component :is="raidsLink.to ? 'router-link' : 'a'" v-bind="raidsLink">团本那一页</component></span><span class="dim mono">{{ raids.length }} 座</span></div>
      <div class="dgrid">
        <div v-for="c in raidCards" :key="c.x.id" class="dcard2">
          <div class="dbn2"><span class="dbn2-shade"></span>
            <svg class="dbn-art" viewBox="0 0 320 86" preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient :id="c.b.gid" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" :stop-color="'hsl(' + c.b.hue + ',32%,18%)'" />
                  <stop offset="1" :stop-color="'hsl(' + c.b.hue + ',26%,7%)'" />
                </linearGradient>
              </defs>
              <rect width="320" height="86" :fill="'url(#' + c.b.gid + ')'" />
              <circle :cx="c.b.mx" cy="21" r="8" :fill="'hsl(' + c.b.hue + ',58%,74%)'" fill-opacity=".38" />
              <polygon :points="'0,86 ' + c.b.pts.join(' ') + ' 320,86'" :fill="'hsl(' + c.b.hue + ',20%,26%)'" fill-opacity=".9" />
            </svg>
            <img v-if="c.b.art" class="dbn-art" :class="{ bad: badArt[c.x.id] }" :src="assetUrl(c.b.art)" alt="" loading="lazy" @error="badArt[c.x.id] = true">
            <span v-if="c.b.seal" class="dbn2-seal">{{ c.b.seal }}</span>
            <span class="dbn2-txt">
              <span v-if="c.b.range" class="dbn2-r">{{ c.b.range }}</span>
              <span class="dbn2-n">{{ c.b.label }}</span>
              <span v-if="c.b.sub" class="dbn2-e">{{ c.b.sub }}</span>
            </span>
          </div>
          <div class="dmeta">
            <span>{{ c.bosses.length ? c.bosses.length + ' 个首领' : '首领待补' }}</span>
            <span>{{ (c.x.drops || []).length ? (c.x.drops || []).length + ' 件掉落' : '掉落待补' }}</span>
            <span v-if="c.x.partySize">一次 {{ c.x.partySize }} 人</span>
            <span v-if="!c.x.levelRange" class="dim">等级区间待实测</span>
            <span v-if="!c.x.nameCn" class="dim">中文定名未公布</span>
          </div>
          <router-link class="dstretch" :to="{ path: '/dungeon', query: { d: c.x.id } }" :aria-label="'看「' + (c.x.nameCn || c.x.nameEn || '这座本') + '」这一座的整页'"></router-link>
          <button class="ghost wide" type="button" :data-d="c.x.id" @click="toggleDrawer(c.x.id)">{{ drawerOf(c.x.id) ? '收起' : '速览首领与掉落' }}</button>
          <div v-show="drawerOf(c.x.id)" class="drawer" :id="'d-' + c.x.id">
            <div v-for="(t, ti) in c.conf" :key="ti" class="conf">{{ t }}</div>
            <div v-if="c.noQueue" class="note">客户端的队伍查找器里还没有这座本，所以现在还不能排队进去，名单与掉落以正式开放后为准。</div>
            <h3>首领与掉落</h3>
            <ul v-if="c.bosses.length" class="bosslist">
              <li v-for="b in c.bosses" :key="b.id">
                <div class="bh">
                  <span class="liw t sm">
                    <svg viewBox="0 0 40 40" aria-hidden="true">
                      <rect width="40" height="40" rx="6" :fill="'hsl(' + b.f.hue + ',22%,16%)'" :stroke="'hsl(' + b.f.hue + ',30%,42%)'" stroke-opacity=".65" />
                      <text x="20" y="26" text-anchor="middle" font-size="16" font-weight="600" :fill="'hsl(' + b.f.hue + ',46%,78%)'" font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ b.f.letter }}</text>
                    </svg>
                    <img v-if="b.portrait" :class="{ bad: badFace[c.x.id + '|' + b.id] }" :src="assetUrl(b.portrait)" alt="" loading="lazy" @error="badFace[c.x.id + '|' + b.id] = true">
                  </span>
                  <b>{{ b.nameCn }}</b>
                  <span class="dim">{{ b.mine.length ? b.mine.length + ' 件掉落' : '掉落待补' }}</span>
                </div>
                <div v-if="b.mine.length" class="loot">
                  <span v-for="y in b.mine" :key="y.itemId" class="loot-i"><IconCell :icon-key="y.iconKey || ''" :seed="y.itemId" :cn="y.nameCn" small />{{ y.nameCn }}<span class="dim mono">#{{ y.itemId }}</span></span>
                </div>
              </li>
            </ul>
            <p v-else class="dim">这座本还没有首领名单。</p>
            <router-link class="cta-cut" :to="{ path: '/dungeon', query: { d: c.x.id } }">看这一座的整页 →</router-link>
          </div>
        </div>
      </div>
    </template>

    <!-- 能排到队、还没有名单的本（queueBand）：按名字归并，同一座本挂两条只说一次。
         10-16 视觉第二批：两张 .entab 合成一张 .board，地下城 / 团队副本做成吸附分组头，
         列宽固定（原来四列的文字长短不一，两张表的"排队等级"列根本不对齐） -->
    <div v-if="queueRows.length" class="card" id="queue">
      <div class="bhead">
        <h2 class="bt">能排到队、还没有名单的本</h2>
        <span class="bn">{{ queueRows.length }} 条</span>
      </div>
      <div class="boardwrap">
        <table class="board">
          <thead><tr>
            <th class="w-name">客户端里的名字</th><th class="c-num2">排队等级</th>
            <th class="c-num2">一次几人</th><th class="w-tail">客户端记了几条</th>
          </tr></thead>
          <tbody class="grp" v-for="q in queueGroups" :key="q.label">
            <tr class="grp2h" v-if="q.rows.length"><th colspan="4">
              {{ q.label }}<span class="gcount">{{ q.rows.length }} 条</span>
            </th></tr>
            <tr v-for="g in q.rows" :key="g.nameEn">
              <td><span class="nm">{{ g.nameEn }}</span><span class="sub">中文定名未公布</span></td>
              <td class="c-num2 num">{{ g.levelRange }} 级</td>
              <td class="c-num2 num">{{ g.sizes.length ? g.sizes.join(' / ') + ' 人' : '未标' }}</td>
              <td class="w-tail num">{{ g.n }}<template v-if="g.n > 1">{{ g.sizes.length > 1 ? ' 条（同一座本两种人数）' : ' 条（同名两个入口，人数一样）' }}</template></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 副本手册列表页 · 与旧站 src/js/app.js 的 dungeons()（含 dunCard/dunListHtml/queueBand）逐块对齐。
   数据全部 src/data 现取；art.json / queue.json 加载失败按旧站 catch 空对象兜底。
   Glyph.dungeonBanner 在本组件内等价复刻（同 FNV 哈希、同 DUNGEON_HUE、同类名），不引图标库。 */
import { computed, nextTick, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { assetUrl, load } from '../lib/data.js';
import { fnv } from '../lib/glyph.js';
import { linkFor } from '../lib/nav.js';
import IconCell from '../components/IconCell.vue';

// 按十级一档分：起点落在哪档就归哪档，50 级往上并成"满级前后"（与旧站同一份表）
const DUN_BANDS = [[10, 19, '起步'], [20, 29, '前期'], [30, 39, '中期'], [40, 49, '中后期'], [50, 99, '满级前后']];
const DUNGEON_HUE = { new: 32, classic: 200, raid: 288 };
// 页首卡片头的板块图（旧站 SEC_ART.dungeons 同一张脸；JS 常量防 Vite 把它当模块解析）
const HEAD_ART = 'img/art/dungeons/blackrock-depths.webp';

const D = ref(null);
const ART = ref({});
const QU = ref({});
const err = ref('');
const lvInput = ref('');
const kind = ref('all');
const drawers = ref({});
const badArt = ref({});
const badFace = ref({});
const pick = ref('');
const route = useRoute();
const router = useRouter();
const raidsLink = linkFor('raids.html');

/* 与旧站 dunRange/dunLvMatch/dunBand/dunSort 同一套算法 */
function dunRange(x) {
  const m = String(x.levelRange || '').match(/(\d+)\D+(\d+)/);
  return m ? [parseInt(m[1], 10), parseInt(m[2], 10)] : null;
}
function dunLvMatch(x, lv) {
  const r = dunRange(x);
  return !!r && lv >= r[0] && lv <= r[1];
}
function dunBand(x) {
  const s = parseInt(String(x.levelRange || '').split('-')[0], 10);
  if (!s) return null;
  for (let i = 0; i < DUN_BANDS.length; i++) if (s >= DUN_BANDS[i][0] && s <= DUN_BANDS[i][1]) return i;
  return null;
}
function dunSort(a, b) {
  const ra = dunRange(a) || [99, 99], rb = dunRange(b) || [99, 99];
  if (ra[0] !== rb[0]) return ra[0] - rb[0];
  if (ra[1] !== rb[1]) return ra[1] - rb[1];
  return String(a.nameCn || a.nameEn || '').localeCompare(String(b.nameCn || b.nameEn || ''));
}
/* 两源分歧（旧站 dunConf）：三条定稿的撤了，这两条一条不许少 */
function confRows(x) {
  const out = [];
  if (x.partySizeAlt) {
    out.push('客户端的队伍查找器里它另有一条 ' + x.partySizeAlt +
      ' 人的排队条目，与本站的 ' + x.partySize + ' 人并列，是不是同一个本两种规模要实测');
  }
  if (x.nameEnClient) {
    out.push('英文原名两说：本站写「' + x.nameEn + '」，客户端写「' + x.nameEnClient + '」');
  }
  return out;
}
/* Glyph.dungeonBanner 等价复刻：只算参数，SVG 交给模板（文字放 HTML 里不进 SVG） */
function bannerOf(x) {
  const h = fnv(x.id);
  const base = DUNGEON_HUE[x.kind] === undefined ? 32 : DUNGEON_HUE[x.kind];
  const hue = (base + (h % 21) - 10 + 360) % 360;
  const w = 320, ht = 86, n = 9, pts = [];
  for (let i = 0; i <= n; i++) {
    const v = ((h >> (i * 3)) & 31);
    pts.push((w / n * i).toFixed(1) + ',' + (ht - 18 - (v % 20) - (i % 2 ? 0 : 8)).toFixed(1));
  }
  return {
    gid: 'dbng' + (h % 9999),
    hue: hue, pts: pts, mx: w - 46 - h % 44,
    art: x.art || ((ART.value.dungeons || {})[x.id]) || '',
    seal: x.kind === 'new' ? '新' : '',
    range: x.levelRange ? x.levelRange + ' 级' : '',
    label: x.nameCn || x.nameEn || '未定名',
    sub: x.zoneCn || ((x.nameCn && x.nameEn) ? x.nameEn : '')
  };
}
/* Glyph.bossFace 等价复刻（色相算法与首字同一套） */
function faceOf(b) {
  const h = fnv(b.id || b.nameCn || '');
  return { hue: (32 + h % 300) % 360, letter: (b.nameCn || '?').charAt(0) };
}

function boot() {
  err.value = '';
  Promise.all([load('data/dungeons.json'),
    load('data/art.json').catch(() => ({})),
    load('data/queue.json').catch(() => ({}))])
    .then((rs) => {
      D.value = rs[0];
      ART.value = rs[1] || {};
      QU.value = rs[2] || {};
      // 从首页搜索跳进来（?d=）：替用户把等级筛设成那座本的起点、点开速览并滚到它（旧站 dd 逻辑）
      const dd = String(route.query.d || '');
      if (dd) {
        const hit = duns.value.filter((x) => x.id === dd)[0];
        if (hit) lvInput.value = String((dunRange(hit) || [0, 0])[0]);
        nextTick(() => {
          let target = null;
          document.querySelectorAll('[data-d]').forEach((b) => { if (!target && b.dataset.d === dd) target = b; });
          if (target) {
            drawers.value[dd] = true;
            if (target.parentNode && target.parentNode.scrollIntoView) target.parentNode.scrollIntoView({ block: 'center' });
          }
        });
      }
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
onMounted(boot);

const duns = computed(() => [].concat((D.value || {}).newDungeons || [], (D.value || {}).classicDungeons || []));
const raids = computed(() => (D.value || {}).raids || []);
const all = computed(() => duns.value.concat(raids.value));

/* 每座本的渲染件一次算好：横幅参数、分歧两条、首领带掉落归属 */
const decorated = computed(() => {
  const m = {};
  all.value.forEach((x) => {
    m[x.id] = {
      x: x,
      b: bannerOf(x),
      conf: confRows(x),
      noQueue: !x.clientActivityId,
      bosses: (x.bosses || []).map((bb) => ({
        id: bb.id, nameCn: bb.nameCn, portrait: bb.portrait, f: faceOf(bb),
        mine: (x.drops || []).filter((y) => y.bossId === bb.id)
      }))
    };
  });
  return m;
});
const raidCards = computed(() => raids.value.map((x) => decorated.value[x.id]).filter(Boolean));

/* 页首读数（与旧站 dungeons() 里的 nb/nd/nParty/nTwo/nSettled/lo/hi 同一算法） */
const nb = computed(() => all.value.reduce((s, x) => s + (x.bosses || []).length, 0));
const nd = computed(() => all.value.reduce((s, x) => s + (x.drops || []).length, 0));
const nParty = computed(() => all.value.filter((x) => x.partySize).length);
// nTwo 撤下：这两类的条数改由溯源页现算（altCounts），内容页不再摆那一句"两种说法都留着"
const nSettled = computed(() => all.value.filter((x) => x.levelRangeOfficial).length);
const newN = computed(() => ((D.value || {}).newDungeons || []).length);
const clN = computed(() => ((D.value || {}).classicDungeons || []).length);
const lohi = computed(() => {
  let lo = 99, hi = 0;
  duns.value.forEach((x) => {
    const r = dunRange(x);
    if (!r) return;
    if (r[0] < lo) lo = r[0];
    if (r[1] > hi) hi = r[1];
  });
  return { lo: lo, hi: hi };
});

/* 选本下拉：按等级段分组（旧站 picks/optgroup） */
const pickGroups = computed(() => {
  const out = [];
  DUN_BANDS.forEach((b, i) => {
    const rows = duns.value.filter((x) => dunBand(x) === i).sort(dunSort);
    if (rows.length) out.push({ label: b[0] + (b[1] > 60 ? '–60' : '–' + b[1]) + ' 级 · ' + b[2], rows: rows });
  });
  const rest = duns.value.filter((x) => dunBand(x) === null);
  if (rest.length) out.push({ label: '区间未定', rows: rest });
  return out;
});

/* 筛选（旧站 dunListHtml）：等级 1–70 才算数，类型三选一 */
const lvNum = computed(() => {
  const v = parseInt(String(lvInput.value), 10);
  return (v >= 1 && v <= 70) ? v : 0;
});
const rowsFiltered = computed(() => duns.value.filter((x) => {
  if (kind.value === 'new' && x.kind !== 'new') return false;
  if (kind.value === 'classic' && x.kind === 'new') return false;
  if (lvNum.value && !dunLvMatch(x, lvNum.value)) return false;
  return true;
}));
const listBands = computed(() => {
  const out = [];
  DUN_BANDS.forEach((b, i) => {
    const rows = rowsFiltered.value.filter((x) => dunBand(x) === i).sort(dunSort);
    if (rows.length) out.push({ title: b[0] + (b[1] > 60 ? '–60' : '–' + b[1]) + ' 级', sub: b[2], rows: rows.map((x) => decorated.value[x.id]) });
  });
  const rest = rowsFiltered.value.filter((x) => dunBand(x) === null);
  if (rest.length) out.push({ title: '区间未定', sub: '', rows: rest.map((x) => decorated.value[x.id]) });
  return out;
});
const emptyTxt = computed(() => {
  const which = kind.value === 'new' ? '无限新增的' : (kind.value === 'classic' ? '经典旧世的' : '');
  return (lvNum.value ? lvNum.value + ' 级还没有对得上的' + which + '地下城。' : '这一类还没有本。') +
    '换一个等级或切回"全部"再看看。';
});

/* queueBand：没对上本站名单的排队条目，按名字归并 */
const queueRows = computed(() => {
  const rows = ((QU.value || {}).items || []).filter((x) => !x.matchedId);
  if (!rows.length) return [];
  const g = {}, order = [];
  rows.forEach((x) => {
    const k = x.nameEn;
    if (!g[k]) {
      g[k] = { nameEn: k, kind: x.kind, levelRange: x.levelRange, sizes: [], n: 0 };
      order.push(k);
    }
    g[k].n += 1;
    if (x.partySize && g[k].sizes.indexOf(x.partySize) < 0) g[k].sizes.push(x.partySize);
  });
  return order.map((k) => g[k]);
});
const queueDun = computed(() => queueRows.value.filter((x) => x.kind === 'dungeon'));
const queueRaid = computed(() => queueRows.value.filter((x) => x.kind === 'raid'));
// 两张表合成一张：分组头做成表内吸附的 tbody.grp（与技能页法术书同一套骨架）
const queueGroups = computed(() => ([
  { label: '地下城', rows: queueDun.value },
  { label: '团队副本', rows: queueRaid.value }
]));

function toggleDrawer(id) { drawers.value[id] = !drawers.value[id]; }
function drawerOf(id) { return !!drawers.value[id]; }
function goPick() {
  if (pick.value) router.push({ path: '/dungeon', query: { d: pick.value } });
}
</script>
