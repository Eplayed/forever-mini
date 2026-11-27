<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button type="button" @click="boot">重试</button>
  </div>

  <template v-else-if="ready">
    <section ref="shellEl" class="card imap-shell" :class="{ 'is-fullscreen': isFullscreen }" aria-label="无限地图交互工作台">
      <!-- 全视口满铺单张完整大地图 + 悬浮控制条与磨砂筛选抽屉（仿 OpenMap） -->
      <div class="imap-body">
        <!-- 悬浮顶部控制条 -->
        <div class="imap-float-top">
          <div class="imap-bar-l">
            <button type="button" class="imap-btn" :aria-expanded="drawerOpen ? 'true' : 'false'"
                    @click="drawerOpen = !drawerOpen">{{ drawerOpen ? '收起筛选' : '展开筛选' }}</button>
            <span class="imap-title-pill"><h1 class="imap-title">无限地图</h1></span>
            <div class="imap-search" ref="searchBoxEl">
              <input id="wq" v-model="q" type="search"
                     placeholder="搜区域、稀有、NPC、副本、书籍、传承书籍…"
                     aria-label="在无限地图中搜索点位并飞跃定位"
                     @focus="dropOpen = true" @keydown.esc="dropOpen = false">
              <div v-if="dropOpen && q.trim()" class="imap-drop" role="listbox" aria-label="地图搜索命中列表">
                <div v-if="!searchHits.length" class="imap-drop-empty">没有匹配点位，换个关键词或区域名试试。</div>
                <button v-for="h in searchHits" :key="h.key" type="button" class="imap-drop-row" @click="pickHit(h)">
                  <span>{{ h.label }}</span>
                  <span class="dim mono">{{ h.sub }}</span>
                </button>
              </div>
            </div>
            <button type="button" class="imap-btn" :class="{ on: activePreset === 'kal' }" @click="fitCamera('kal')">卡利姆多</button>
            <button type="button" class="imap-btn" :class="{ on: activePreset === 'ek' }" @click="fitCamera('ek')">东部王国</button>
            <button type="button" class="imap-btn" :class="{ on: activePreset === 'new' }" @click="fitCamera('new')">无限新岛</button>
            <button type="button" class="imap-btn" @click="extraOpen = true">书籍换奖 / 套装 / 睡袋</button>
          </div>
          <div class="imap-bar-r">
            <span v-if="activeZone" class="imap-zone-crumb">
              <span>{{ activeZone.nameCn }}</span>
              <span v-if="lvShort(activeZone)" class="mono dim">{{ lvShort(activeZone) }}</span>
              <button type="button" @click="fitCamera(activeZone.continent === 'kal' ? 'kal' : (activeZone.continent === 'ek' ? 'ek' : 'world'))">退回大陆</button>
            </span>
            <!-- 右上角地图操控条：放大 / 缩小 / 整张地图 / 全屏还原 -->
            <div class="imap-top-tools" role="toolbar" aria-label="地图缩放与全屏工具">
              <button type="button" class="imap-btn" title="放大地图" aria-label="放大地图" @click="stepZoom(1.38)">＋</button>
              <button type="button" class="imap-btn" title="缩小地图" aria-label="缩小地图" @click="stepZoom(0.72)">－</button>
              <button type="button" class="imap-btn" :class="{ on: activePreset === 'world' }" title="显示整张地图" @click="fitCamera('world')">整张地图</button>
              <button type="button" class="imap-btn" :class="{ on: isFullscreen }" :title="isFullscreen ? '还原窗口' : '全屏显示地图'" @click="toggleFullscreen">{{ isFullscreen ? '还原' : '全屏' }}</button>
            </div>
          </div>
        </div>

        <!-- 左侧磨砂悬浮筛选抽屉 -->
        <aside v-show="drawerOpen" class="imap-drawer" aria-label="地图图层筛选与区域目录">
          <div class="imap-dtabs" role="tablist">
            <button type="button" class="imap-btn" :class="{ on: drawerTab === 'filter' }"
                    data-t="filter" :aria-pressed="drawerTab === 'filter' ? 'true' : 'false'"
                    @click="drawerTab = 'filter'">图层筛选</button>
            <button type="button" class="imap-btn" :class="{ on: drawerTab === 'zones' }"
                    data-t="zones" :aria-pressed="drawerTab === 'zones' ? 'true' : 'false'"
                    @click="drawerTab = 'zones'">区域直达 ({{ zones.length }})</button>
          </div>

          <div class="imap-dscroll">
            <Transition name="swap" mode="out-in">
              <div class="wswap" :key="drawerTab">
                <!-- 页签一：OpenMap 风格图层筛选 -->
                <template v-if="drawerTab === 'filter'">
                  <div class="imap-sec">
                    <div class="imap-sec-h">
                      <span>阵营显示</span>
                      <span class="mono">{{ visiblePins.length }} / {{ allPins.length }} 点</span>
                    </div>
                    <div class="imap-fac">
                      <button type="button" class="imap-btn" :class="{ on: faction === 'all' }" @click="faction = 'all'">全部</button>
                      <button type="button" class="imap-btn" :class="{ on: faction === 'A' }" @click="faction = 'A'">联盟</button>
                      <button type="button" class="imap-btn" :class="{ on: faction === 'H' }" @click="faction = 'H'">部落</button>
                    </div>
                  </div>

                  <!-- 传承书籍独立扩展进度卡 -->
                  <div class="imap-legacy-box">
                    <div class="imap-legacy-top">
                      <span>传承书籍（扩展图层）</span>
                      <span class="mono">{{ legacyDoneCount }} / {{ legacyTotalCount }}</span>
                    </div>
                    <div class="imap-legacy-bar"><i :style="{ width: legacyPct + '%' }"></i></div>
                    <p class="imap-legacy-note">
                      <template v-if="legacyTotalCount">已接入 {{ legacyTotalCount }} 本传承书籍点位，点击图钉可本地打卡。</template>
                      <template v-else>点位结构与打卡进度已就绪，待核实坐标入库后自动点亮（缺数不编造）。</template>
                    </p>
                  </div>

                  <!-- 四大分组复选 -->
                  <div v-for="g in MAP_GROUPS" :key="g.key" class="imap-sec">
                    <div class="imap-sec-h">
                      <span>{{ g.label }}</span>
                      <button type="button" class="imap-sec-act" @click="toggleGroup(g.key)">全选/反选</button>
                    </div>
                    <label v-for="c in catsByGroup[g.key]" :key="c.key" class="imap-ck">
                      <span class="imap-ck-l">
                        <input type="checkbox" v-model="enabled[c.key]" :data-cat="c.key">
                        <span class="imap-dot-ic" :class="'im-c-' + c.key" aria-hidden="true">
                          <img :src="assetUrl(c.icon)" alt="" loading="lazy" decoding="async">
                        </span>
                        <span>{{ c.label }}</span>
                      </span>
                      <span class="dim mono">{{ catCounts[c.key] || 0 }}</span>
                    </label>
                  </div>

                  <!-- OpenMap 显示选项 -->
                  <div class="imap-sec">
                    <div class="imap-sec-h"><span>显示选项</span></div>
                    <label class="imap-ck">
                      <span>按缩放自动分层（LOD）</span>
                      <input type="checkbox" v-model="optLod">
                    </label>
                    <label class="imap-ck">
                      <span>显示区域名与等级</span>
                      <input type="checkbox" v-model="optZoneLabels">
                    </label>
                    <label class="imap-ck">
                      <span>显示船只/飞艇/空艇航线</span>
                      <input type="checkbox" v-model="optRoutes">
                    </label>
                    <label class="imap-ck">
                      <span>显示飞行线路图（区分阵营）</span>
                      <input type="checkbox" v-model="optFlightRoutes">
                    </label>
                    <label class="imap-ck">
                      <span>隐藏已打卡书籍/稀有</span>
                      <input type="checkbox" v-model="optHideDone">
                    </label>
                  </div>
                </template>

                <!-- 页签二：46 区域与主城直达目录 -->
                <template v-else>
                  <button v-for="z in sortedZones" :key="z.mapId" type="button" class="imap-zrow" @click="flyToZone(z)">
                    <span>
                      <b>{{ z.nameCn }}</b>
                      <span v-if="z.isNew" class="tag new" style="margin-left:4px">新</span>
                      <small class="mono">{{ lvTxt(z) || (z.isCity ? '主城' : z.continentCn) }} · #{{ z.mapId }}</small>
                    </span>
                    <span class="dim mono">{{ zonePinCount[z.mapId] || 0 }} 点 →</span>
                  </button>
                </template>
              </div>
            </Transition>
          </div>
        </aside>

        <!-- 单张完整无缝大地图视口 -->
        <div ref="viewportEl" class="imap-stage-wrap" :class="{ dragging }"
             @wheel.prevent="onWheel"
             @pointerdown="onPointerDown"
             @pointermove="onPointerMove"
             @pointerup="onPointerUp"
             @pointercancel="onPointerUp"
             @contextmenu.prevent="onRightClickOut">
          <div class="imap-stage-vignette" aria-hidden="true"></div>

          <!-- 屏幕空间原生分辨率栅格层（绕开 CSS scale() GPU 降采样糊化，12K 瓦片逐像素锐利清晰） -->
          <div class="imap-raster-layer" aria-hidden="true">
            <img v-if="worldMapFile" class="imap-world-img" :src="assetUrl(worldMapFile)"
                 :style="worldScreenStyle" alt="完整世界大地图底图" decoding="async">

            <template v-if="mapStyle === 'world'">
              <img v-for="c in continents" :key="c.mapId" class="imap-cont-img"
                   :src="assetUrl(c.mapFile)" :alt="c.nameCn + '大陆底图'" loading="lazy" decoding="async"
                   :style="continentLayerStyle(c)">
            </template>

            <template v-else>
              <div v-if="visibleTilesZ1.length" class="imap-tiles-layer" :style="{ opacity: tileZ1Opacity }">
                <img v-for="t in visibleTilesZ1" :key="t.key" class="imap-tile"
                     :src="assetUrl(t.src)" :style="t.style" alt="" decoding="async">
              </div>
              <div v-if="visibleTilesZ2.length" class="imap-tiles-layer" style="z-index:4">
                <img v-for="t in visibleTilesZ2" :key="t.key" class="imap-tile"
                     :src="assetUrl(t.src)" :style="t.style" alt="" loading="lazy" decoding="async">
              </div>
              <div v-if="visibleTilesZ3.length" class="imap-tiles-layer" style="z-index:5">
                <img v-for="t in visibleTilesZ3" :key="t.key" class="imap-tile"
                     :src="assetUrl(t.src)" :style="t.style" alt="" loading="lazy" decoding="async">
              </div>
              <div v-if="visibleTilesZ4.length" class="imap-tiles-layer" style="z-index:6">
                <img v-for="t in visibleTilesZ4" :key="t.key" class="imap-tile"
                     :src="assetUrl(t.src)" :style="t.style" alt="" loading="lazy" decoding="async">
              </div>
              <img v-for="cz in visibleCityMaps" :key="'city-' + cz.mapId" class="imap-city-img"
                   :src="assetUrl(cz.mapFile)" :alt="cz.nameCn + '主城地图'"
                   loading="lazy" decoding="async" :style="cityScreenStyle(cz)">
            </template>
          </div>

          <div class="imap-stage" :style="stageStyle">
            <!-- 46 个区域精确投影热区与浮标 -->
            <div v-for="z in zones" :key="z.mapId" class="imap-zone"
                 :class="{ 'is-city': z.isCity, 'is-active-zone': activeZone && activeZone.mapId === z.mapId }"
                 :data-zone-id="z.mapId"
                 :style="{ left: z.rect[0] + 'px', top: z.rect[1] + 'px', width: z.rect[2] + 'px', height: z.rect[3] + 'px' }"
                 @dblclick.stop="flyToZone(z)">
              <span v-show="optZoneLabels" class="imap-ztag" :style="zoneLabelStyle(z)">
                {{ z.nameCn }}<small v-if="lvShort(z)">{{ lvShort(z) }}</small>
              </span>
            </div>

            <!-- 活字中文大陆名与海名（仿 OpenMap Labels.lua，拉近自动淡出） -->
            <div class="imap-cont-lbl" :style="{ left: '375px', top: '605px', opacity: contLabelOpacity }">卡利姆多</div>
            <div class="imap-cont-lbl" :style="{ left: '1345px', top: '745px', opacity: contLabelOpacity }">东部王国</div>
            <div class="imap-sea-lbl" :style="{ left: '910px', top: '720px', opacity: contLabelOpacity }">无尽之海</div>

            <!-- 船只 / 飞艇 / 空艇航线 + 联盟/部落飞行线路图 SVG 层 -->
            <svg v-if="optRoutes || optFlightRoutes" class="imap-routes" :width="canvasSize.w" :height="canvasSize.h"
                 :viewBox="'0 0 ' + canvasSize.w + ' ' + canvasSize.h" aria-hidden="true">
              <template v-if="optFlightRoutes && visibleFlightPaths.length">
                <path v-for="fp in visibleFlightPaths" :key="fp.id"
                      :d="polyToPath(fp.points)"
                      fill="none" stroke-width="1.35" vector-effect="non-scaling-stroke"
                      stroke-linecap="round" stroke-linejoin="round"
                      :opacity="flightRouteOpacity"
                      :class="fp.faction === 'A' ? 'imap-route-a' : (fp.faction === 'H' ? 'imap-route-h' : 'imap-route-n')" />
              </template>
              <template v-if="optRoutes">
                <path v-for="r in visibleRoutes" :key="r.id"
                      :d="routeToPath(r)"
                      fill="none" stroke-width="2.1" vector-effect="non-scaling-stroke"
                      stroke-dasharray="7 5" stroke-linecap="round" opacity="0.88"
                      :class="routeClass(r)" />
              </template>
            </svg>

            <!-- 飞跃选中脉冲信标 -->
            <div v-if="selectedPin" class="imap-beacon"
                 :style="beaconStyle(selectedPin)" aria-hidden="true"></div>

            <!-- 视口裁剪 + LOD 过滤后的游戏图标图钉层（紧凑并随缩放等比例变化） -->
            <button v-for="p in visiblePins" :key="p.id" type="button" class="imap-pin"
                    :class="['im-c-' + p.cat, 'im-fac-' + p.faction, p.transportKind ? 'im-kind-' + p.transportKind : '', { on: selectedId === p.id, done: doneSet.has(p.id) }]"
                    :data-pin-cat="p.cat"
                    :style="pinStyle(p)"
                    :title="p.name + '（' + p.zone + ' ' + p.x.toFixed(1) + ', ' + p.y.toFixed(1) + '）'"
                    :aria-label="p.name + '，' + p.zone + ' ' + p.x.toFixed(1) + ', ' + p.y.toFixed(1)"
                    @pointerdown.stop
                    @click.stop="selectPin(p)">
              <img class="imap-pin-img" :src="assetUrl(pinIcon(p))" alt="" loading="lazy" decoding="async">
              <span v-if="doneSet.has(p.id)" class="imap-pin-done" aria-hidden="true">✓</span>
            </button>
          </div>

          <!-- 右侧悬浮点位详情卡 -->
          <div v-if="selectedPin" class="imap-card" role="dialog" :aria-label="selectedPin.name + ' 点位详情'">
            <div class="imap-card-h">
              <div style="display:flex;align-items:flex-start;gap:10px;min-width:0">
                <img class="imap-card-ic" :class="'im-c-' + selectedPin.cat"
                     :src="assetUrl(pinIcon(selectedPin))" alt="">
                <div style="min-width:0">
                  <div>
                    <span class="tag">{{ selectedPin.tag }}</span>
                    <span v-if="selectedPin.isNew" class="tag new" style="margin-left:4px">无限新增</span>
                  </div>
                  <h3>{{ selectedPin.name }}</h3>
                  <div v-if="selectedPin.en" class="dim mono">{{ selectedPin.en }}</div>
                </div>
              </div>
              <button type="button" class="imap-btn" aria-label="关闭点位详情" @click="clearSelect">✕</button>
            </div>

            <div class="imap-card-meta mono">
              <div><span class="dim">区域：</span>{{ selectedPin.zone }}</div>
              <div><span class="dim">坐标：</span>{{ selectedPin.x.toFixed(1) }}, {{ selectedPin.y.toFixed(1) }}</div>
              <div><span class="dim">等级：</span>{{ selectedPin.level || '—' }}</div>
              <div><span class="dim">阵营：</span>{{ factionLabel(selectedPin.faction) }}</div>
            </div>

            <div v-if="(selectedPin.rows || []).length" class="imap-card-rows">
              <div v-for="(r, idx) in selectedPin.rows" :key="idx">
                <span class="dim">{{ r[0] }}</span>
                <b>{{ r[1] }}</b>
              </div>
            </div>

            <div v-if="(selectedPin.drops || []).length" class="imap-card-drops">
              <div class="dim" style="font-size:11px">掉落装备（不含掉落百分比）：</div>
              <div v-for="d in selectedPin.drops" :key="d.itemId" class="imap-card-drop" :class="'q' + (d.quality || 0)">
                <IconCell :icon-key="d.iconKey || ''" :seed="d.itemId" :cn="d.nameCn" small />
                <span>{{ d.nameCn }}</span>
                <span v-if="d.itemLevel" class="dim mono">iLvl {{ d.itemLevel }}</span>
                <span class="dim mono">#{{ d.itemId }}</span>
              </div>
            </div>

            <div class="imap-card-acts">
              <button type="button" class="imap-btn" @click="copyWay(selectedPin)">复制 /way 指令</button>
              <button type="button" class="imap-btn" @click="copyShare(selectedPin)">复制分享链接</button>
              <router-link v-if="selectedPin.cat === 'dungeon'" class="imap-btn on"
                           :to="selectedPin.isRaid ? '/raids' : { path: '/dungeon', query: { d: selectedPin.slug } }">
                查看{{ selectedPin.isRaid ? '团本筹备' : '副本掉落' }} →
              </router-link>
              <button v-if="CAT_BY_KEY[selectedPin.cat] && CAT_BY_KEY[selectedPin.cat].checkable"
                      type="button" class="imap-btn" :class="{ on: doneSet.has(selectedPin.id) }"
                      @click="toggleDone(selectedPin.id)">
                {{ doneSet.has(selectedPin.id) ? '✓ 已打卡（点击取消）' : (selectedPin.cat === 'rare' ? '标记已击杀' : '标记已收集') }}
              </button>
            </div>
            <p v-if="copyMsg" class="dim mono" style="margin:8px 0 0;color:var(--gold-hi)">{{ copyMsg }}</p>
          </div>

          <!-- 左下角实时光标区域与坐标 HUD -->
          <div class="imap-hud mono">
            <b>{{ hudZone }}</b>
            <span class="dim">{{ hudLevel }}</span>
            <span>{{ hudCoord }}</span>
            <span class="dim">{{ lodStatus }}</span>
          </div>

          <!-- 右下角仅保留「游戏内地图」标识按钮（不展示缩放比例与多余按钮） -->
          <div class="imap-zoom">
            <button type="button" class="imap-btn on" title="游戏内地图（点击复位全览）" @click="fitCamera('world')">游戏内地图</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 保留原有世界页附属信息：图书馆换奖 / 管理员 / 稀有套装 / 舒适睡袋参数 -->
    <div v-if="extraOpen" class="imap-modal-mask" @click.self="extraOpen = false" @keydown.esc="extraOpen = false">
      <div class="imap-modal" role="dialog" aria-label="书籍换奖、稀有套装与睡袋参数">
        <div class="imap-card-h">
          <h2 style="margin:0">书籍换奖、稀有套装与睡袋参数</h2>
          <button type="button" class="imap-btn" @click="extraOpen = false">关闭 ✕</button>
        </div>

        <div v-if="librarians.length" style="margin-bottom:16px">
          <h3>图书馆管理员（上交书籍）</h3>
          <div v-for="l in librarians" :key="l.nameCn" class="lrow">
            <b>{{ l.nameCn }}</b>
            <span class="dim">{{ l.faction }} · {{ l.city }}{{ l.quarter ? '，' + l.quarter : '' }}</span>
            <span class="mono dim">{{ coordTxt(l) }}</span>
          </div>
        </div>

        <div v-if="rewards.length" style="margin-bottom:16px">
          <h3>上交多少本换什么</h3>
          <div class="boardwrap">
            <table class="board">
              <thead><tr><th>门槛</th><th>称号</th><th>任务</th><th>奖励</th></tr></thead>
              <tbody>
                <tr v-for="rw in rewards" :key="rw.books">
                  <td class="mono">{{ rw.books }} 本</td>
                  <td>{{ rw.title }}</td>
                  <td class="mono dim">{{ rw.questId ? '#' + rw.questId : '—' }}</td>
                  <td>
                    <span v-if="rw.noReward" class="dim">奖励待补</span>
                    <span v-else v-for="d in rw.items" :key="d.itemId" class="loot-i" :class="'q' + (d.quality || 0)">
                      {{ d.nameCn }} <span class="dim mono">#{{ d.itemId }}</span>
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="rareSets.length" style="margin-bottom:16px">
          <h3>稀有精英掉落套装</h3>
          <div v-for="s in rareSets" :key="s.nameCn" style="margin-bottom:10px">
            <b>{{ s.nameCn }}</b>（{{ s.pieces.length }} 件套）
            <ul class="list">
              <li v-for="p in s.pieces" :key="p.itemId">
                {{ p.nameCn }} <span class="dim mono">#{{ p.itemId }}</span> —
                {{ p.fromRare ? '来自稀有「' + p.fromRare + '」' : '来源稀有待补' }}
              </li>
            </ul>
          </div>
        </div>

        <div v-if="bagRows.length">
          <h3>舒适的睡袋机制参数</h3>
          <div class="boardwrap">
            <table class="board">
              <thead><tr><th>机制项</th><th>记录值</th></tr></thead>
              <tbody>
                <tr v-for="r in bagRows" :key="r[0]"><td>{{ r[0] }}</td><td class="mono">{{ r[1] }}</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="missingBooks.length || unplacedRares.length" style="margin-top:14px">
          <p v-if="missingBooks.length" class="dim">暂缺坐标的图书馆书籍（{{ missingBooks.length }} 本）：{{ missingBooks.map(b => b.nameCn).join('、') }}</p>
          <p v-if="unplacedRares.length" class="dim">暂缺坐标的稀有精英（{{ unplacedRares.length }} 只）：{{ unplacedRares.map(u => u.nameCn).join('、') }}</p>
        </div>
      </div>
    </div>
  </template>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { assetUrl, loadAll } from '../lib/data.js';
import { levelRangeText as lvTxt, lvStart, coordText as coordTxt } from '../lib/fmt.js';
import IconCell from '../components/IconCell.vue';
import {
  MAP_GROUPS,
  MAP_CATEGORIES,
  CAT_BY_KEY,
  defaultEnabledMap,
  normalizeMapPins,
  filterVisiblePins,
  buildWayCommand,
  buildShareHash,
  loadDoneSet,
  saveDoneSet
} from '../lib/world-map.js';

const route = useRoute();

const ready = ref(false);
const err = ref('');
const atlas = ref(null);
const world = ref(null);
const npcsData = ref(null);
const legacyData = ref(null);

const shellEl = ref(null);
const viewportEl = ref(null);
const searchBoxEl = ref(null);

const drawerOpen = ref(true);
const drawerTab = ref('filter');
const extraOpen = ref(false);
const isFullscreen = ref(false);
const q = ref('');
const dropOpen = ref(false);
const activePreset = ref('world');

const faction = ref('all');
const mapStyle = ref('ingame');
const enabled = reactive(defaultEnabledMap());
const optLod = ref(true);
const optZoneLabels = ref(true);
const optRoutes = ref(false);
const optFlightRoutes = ref(true);
const optHideDone = ref(false);

// 勾选「航线点（船/飞艇/空艇）」时自动联动开启/关闭船艇真实航线图
watch(() => enabled.transport, (on) => {
  optRoutes.value = !!on;
});

function toggleFullscreen() {
  const next = !isFullscreen.value;
  isFullscreen.value = next;
  try {
    if (next && shellEl.value && shellEl.value.requestFullscreen && !document.fullscreenElement) {
      shellEl.value.requestFullscreen().catch(() => {});
    } else if (!next && document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
  } catch (_) {}
  nextTick(() => {
    syncVpSize();
    if (activePreset.value === 'world') fitCamera('world', false);
  });
}

function onFullscreenChange() {
  if (!document.fullscreenElement && isFullscreen.value) {
    isFullscreen.value = false;
    nextTick(() => {
      syncVpSize();
      if (activePreset.value === 'world') fitCamera('world', false);
    });
  }
}

function onEscKey(e) {
  if (e.key === 'Escape' && isFullscreen.value) {
    isFullscreen.value = false;
    nextTick(() => {
      syncVpSize();
      if (activePreset.value === 'world') fitCamera('world', false);
    });
  }
}

const doneSet = ref(loadDoneSet());
const selectedId = ref('');
const copyMsg = ref('');

// 相机状态（单张大地图平滑平移与光标锚定缩放）
const camX = ref(0);
const camY = ref(0);
const scale = ref(0.64);
const animateCam = ref(false);
const dragging = ref(false);
const vpW = ref(1160);
const vpH = ref(760);
let dragStart = { x: 0, y: 0, ox: 0, oy: 0 };

const hudZone = ref('全览大地图');
const hudLevel = ref('拖拽平移 · 滚轮缩放 · 右键缩回');
const hudCoord = ref('坐标 --.-, --.-');

function syncVpSize() {
  const el = viewportEl.value;
  if (!el) return;
  vpW.value = el.clientWidth || 1160;
  vpH.value = el.clientHeight || 760;
}

function boot() {
  err.value = '';
  loadAll([
    'data/world-atlas.json',
    'data/world.json',
    'data/map-npcs.json',
    'data/legacy-books.json'
  ]).then(([a, w, n, lb]) => {
    atlas.value = a;
    world.value = w;
    npcsData.value = n;
    legacyData.value = lb;
    ready.value = true;
    nextTick(() => {
      syncVpSize();
      fitCamera('world', false);
      applyQuery();
    });
  }).catch((e) => {
    err.value = (e && e.message) || String(e);
  });
}

const canvasSize = computed(() => ((atlas.value && atlas.value.meta && atlas.value.meta.canvas) || { w: 2004, h: 1336 }));
const worldMapFile = computed(() => (atlas.value && atlas.value.meta && atlas.value.meta.worldMap) || '');
const continents = computed(() => (atlas.value && atlas.value.continents) || []);
const zones = computed(() => (atlas.value && atlas.value.zones) || []);
const routes = computed(() => (atlas.value && atlas.value.routes) || []);
const allPins = computed(() => normalizeMapPins(atlas.value, world.value, npcsData.value, legacyData.value));

const catsByGroup = computed(() => {
  const m = {};
  MAP_GROUPS.forEach((g) => { m[g.key] = []; });
  MAP_CATEGORIES.forEach((c) => { if (m[c.group]) m[c.group].push(c); });
  return m;
});

const catCounts = computed(() => {
  const m = {};
  allPins.value.forEach((p) => { m[p.cat] = (m[p.cat] || 0) + 1; });
  return m;
});

const zonePinCount = computed(() => {
  const m = {};
  allPins.value.forEach((p) => { m[p.mapId] = (m[p.mapId] || 0) + 1; });
  return m;
});

const sortedZones = computed(() => [...zones.value].sort((a, b) =>
  (b.isNew - a.isNew) || (lvStart(a) - lvStart(b)) || a.nameCn.localeCompare(b.nameCn, 'zh')
));

const legacyTotalCount = computed(() => catCounts.value.legacy_book || 0);
const legacyDoneCount = computed(() =>
  allPins.value.filter((p) => p.cat === 'legacy_book' && doneSet.value.has(p.id)).length
);
const legacyPct = computed(() =>
  legacyTotalCount.value ? Math.round((legacyDoneCount.value / legacyTotalCount.value) * 100) : 0
);

const viewBounds = computed(() => {
  const pad = 110 / Math.max(0.45, scale.value);
  return {
    x0: (-camX.value) / scale.value - pad,
    y0: (-camY.value) / scale.value - pad,
    x1: (vpW.value - camX.value) / scale.value + pad,
    y1: (vpH.value - camY.value) / scale.value + pad
  };
});

const visiblePins = computed(() => filterVisiblePins(allPins.value, {
  enabled,
  faction: faction.value,
  hideDone: optHideDone.value,
  doneSet: doneSet.value,
  lod: optLod.value,
  scale: scale.value,
  selectedId: selectedId.value,
  viewBounds: viewBounds.value
}));

const selectedPin = computed(() =>
  selectedId.value ? allPins.value.find((p) => p.id === selectedId.value) || null : null
);

function pinIcon(p) {
  if (p && p.iconOverride) return p.iconOverride;
  const cm = p && CAT_BY_KEY[p.cat];
  return (cm && cm.icon) || 'img/icons/inv_misc_map_01.jpg';
}

const flightPaths = computed(() => (atlas.value && atlas.value.flightPaths) || []);

const visibleRoutes = computed(() => routes.value.filter((r) => {
  if (faction.value === 'all') return true;
  return r.faction === 'N' || r.faction === faction.value;
}));

const visibleFlightPaths = computed(() => {
  if (!optFlightRoutes.value) return [];
  return flightPaths.value.filter((fp) => {
    if (fp.faction === 'A' && !enabled.flight_a) return false;
    if (fp.faction === 'H' && !enabled.flight_h) return false;
    if (fp.faction === 'N' && !enabled.flight_a && !enabled.flight_h && !enabled.flight_n) return false;
    if (faction.value !== 'all' && fp.faction !== 'N' && fp.faction !== faction.value) return false;
    return true;
  });
});

const flightRouteOpacity = computed(() => {
  const rz = relZoom.value;
  if (rz < 1.05) return '0.26';
  if (rz >= 1.8) return '0.62';
  return (0.26 + ((rz - 1.05) / 0.75) * 0.36).toFixed(2);
});

function polyToPath(pts) {
  if (!Array.isArray(pts) || pts.length < 2) return '';
  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 1; i < pts.length; i++) {
    d += ` L ${pts[i][0]} ${pts[i][1]}`;
  }
  return d;
}

function routeToPath(r) {
  if (Array.isArray(r.points) && r.points.length >= 2) return polyToPath(r.points);
  if (r.p1 && r.ctrl && r.p2) return `M ${r.p1[0]} ${r.p1[1]} Q ${r.ctrl[0]} ${r.ctrl[1]} ${r.p2[0]} ${r.p2[1]}`;
  return '';
}

// OpenMap 相对缩放倍率：relZoom = 1.0 表示世界全览刚好铺满可见视口
const baseWorldScale = computed(() => {
  const leftInset = (drawerOpen.value && vpW.value >= 960) ? 274 : 0;
  const availW = Math.max(320, vpW.value - leftInset);
  const sx = availW / 1640;
  const sy = Math.max(320, vpH.value - 64) / 1180;
  return clampScale(Math.max(0.49, Math.min(sx, sy)));
});

const relZoom = computed(() => scale.value / (baseWorldScale.value || 0.5));

// 仿 OpenMap WorldMap.lua autoSwitch：滚轮放大到区域级时自动锁定当前视口中心的具体区域（或主城）
const activeZone = computed(() => {
  if (relZoom.value < 1.95) return null;
  const cxOffset = (drawerOpen.value && vpW.value >= 960) ? 132 : 0;
  const cwx = ((vpW.value + cxOffset) / 2 - camX.value) / scale.value;
  const cwy = (vpH.value / 2 - camY.value) / scale.value;
  const hits = zones.value.filter((z) =>
    cwx >= z.rect[0] && cwx <= z.rect[0] + z.rect[2] && cwy >= z.rect[1] && cwy <= z.rect[1] + z.rect[3]
  );
  if (!hits.length) return null;
  if (relZoom.value >= 4.0) {
    const city = hits.find((z) => z.isCity);
    if (city) return city;
  }
  const nonCity = hits.filter((z) => !z.isCity);
  const pool = nonCity.length ? nonCity : hits;
  pool.sort((a, b) => (a.rect[2] * a.rect[3]) - (b.rect[2] * b.rect[3]));
  return pool[0];
});

const lodStatus = computed(() => {
  if (!optLod.value) return 'LOD：已全显';
  if (scale.value < 0.9) return '世界全览：副本/营地/传承书（左键点击或滚轮切入区域地图）';
  if (scale.value < 1.35) return '大陆/区域：+稀有/书籍/鸟点';
  return '具体区域地图：+旅店炉石/修理铁砧/全部城镇 NPC';
});

// 无缝 6K 多级瓦片金字塔（屏幕空间原生像素尺寸渲染，零缩放糊化、零瓦片细缝）
const tileLevels = computed(() => {
  const arr = (atlas.value && atlas.value.tilePyramid && atlas.value.tilePyramid.levels) || [];
  const out = {};
  arr.forEach((lv) => { out[lv.z] = lv; });
  return out;
});

const worldScreenStyle = computed(() => ({
  left: camX.value.toFixed(1) + 'px',
  top: camY.value.toFixed(1) + 'px',
  width: (canvasSize.value.w * scale.value).toFixed(1) + 'px',
  height: (canvasSize.value.h * scale.value).toFixed(1) + 'px'
}));

function buildVisibleTiles(zNum) {
  const lv = tileLevels.value[zNum];
  if (!lv || !lv.tiles || !lv.tiles.length) return [];
  const cw = canvasSize.value.w;
  const ch = canvasSize.value.h;
  const b = viewBounds.value;
  const ts = lv.tileSize || 512;
  const s = scale.value;
  const ox = camX.value;
  const oy = camY.value;
  const out = [];
  for (let i = 0; i < lv.tiles.length; i++) {
    const id = lv.tiles[i];
    const parts = id.split('_');
    const c = Number(parts[0]);
    const r = Number(parts[1]);
    const px0 = c * ts;
    const py0 = r * ts;
    const pw = Math.min(ts, lv.w - px0);
    const ph = Math.min(ts, lv.h - py0);
    const wx0 = (px0 / lv.w) * cw;
    const wy0 = (py0 / lv.h) * ch;
    const ww = (pw / lv.w) * cw;
    const wh = (ph / lv.h) * ch;
    if (wx0 + ww < b.x0 || wx0 > b.x1 || wy0 + wh < b.y0 || wy0 > b.y1) continue;
    const sx0 = ox + wx0 * s;
    const sy0 = oy + wy0 * s;
    const sw = ww * s;
    const sh = wh * s;
    out.push({
      key: `z${zNum}_${id}`,
      src: `${lv.dir}/${id}.webp`,
      style: {
        left: Math.floor(sx0) + 'px',
        top: Math.floor(sy0) + 'px',
        width: (Math.ceil(sw) + 1) + 'px',
        height: (Math.ceil(sh) + 1) + 'px'
      }
    });
  }
  return out;
}

const tileZ1Opacity = computed(() => {
  const rz = relZoom.value;
  if (rz <= 1.08) return '0.00';
  if (rz >= 1.55) return '1.00';
  return ((rz - 1.08) / 0.47).toFixed(2);
});

const visibleTilesZ1 = computed(() => (relZoom.value >= 1.05 ? buildVisibleTiles(1) : []));
const visibleTilesZ2 = computed(() => (relZoom.value >= 1.5 ? buildVisibleTiles(2) : []));
const visibleTilesZ3 = computed(() => (relZoom.value >= 2.2 ? buildVisibleTiles(3) : []));
const visibleTilesZ4 = computed(() => (relZoom.value >= 3.1 ? buildVisibleTiles(4) : []));

const visibleCityMaps = computed(() =>
  zones.value.filter((z) => z.isCity && relZoom.value >= 3.6 && zoneInViewport(z))
);

function cityScreenStyle(z) {
  const s = scale.value;
  const rz = relZoom.value;
  const op = rz < 3.8 ? 0 : Math.min(1, (rz - 3.8) / 1.2);
  return {
    left: (camX.value + z.rect[0] * s).toFixed(1) + 'px',
    top: (camY.value + z.rect[1] * s).toFixed(1) + 'px',
    width: (z.rect[2] * s).toFixed(1) + 'px',
    height: (z.rect[3] * s).toFixed(1) + 'px',
    opacity: op.toFixed(2)
  };
}

const contLabelOpacity = computed(() => {
  const rz = relZoom.value;
  if (rz <= 1.25) return 0.92;
  if (rz >= 1.85) return 0;
  return Number((0.92 * (1 - (rz - 1.25) / 0.60)).toFixed(2));
});

function continentLayerStyle(c) {
  const rz = relZoom.value;
  const s = scale.value;
  const op = rz > 1.08 ? Math.min(0.96, (rz - 1.08) / 0.65) : 0;
  return {
    left: (camX.value + c.rect[0] * s).toFixed(1) + 'px',
    top: (camY.value + c.rect[1] * s).toFixed(1) + 'px',
    width: (c.rect[2] * s).toFixed(1) + 'px',
    height: (c.rect[3] * s).toFixed(1) + 'px',
    opacity: op.toFixed(2)
  };
}

function zoneInViewport(z) {
  const b = viewBounds.value;
  return !(z.rect[0] + z.rect[2] < b.x0 || z.rect[0] > b.x1 || z.rect[1] + z.rect[3] < b.y0 || z.rect[1] > b.y1);
}

function zoneLabelStyle(z) {
  const inv = Math.max(0.18, Math.min(1.0, 1 / Math.pow(scale.value, 0.82)));
  const rz = relZoom.value;
  let op = 0;
  if (z.isCity) {
    op = (rz >= 2.4 && rz < 4.5) ? 0.96 : 0;
  } else if (mapStyle.value === 'ingame' && rz >= 3.1) {
    // 6K 无缝游戏地图已呈现原生中文地标名，放大到街道级时淡出大字避免遮挡
    op = 0;
  } else if (z.isNew) {
    op = rz >= 1.15 ? 0.96 : 0.78;
  } else {
    op = rz >= 1.15 ? 0.95 : 0;
  }
  return {
    opacity: op,
    transform: `translate(-50%, -50%) scale(${inv.toFixed(2)})`
  };
}

const stageStyle = computed(() => ({
  width: canvasSize.value.w + 'px',
  height: canvasSize.value.h + 'px',
  transform: `translate3d(${camX.value.toFixed(1)}px, ${camY.value.toFixed(1)}px, 0) scale(${scale.value})`
}));

function pinStyle(p) {
  // 标注点紧凑并随地图缩放平滑等比例变化（全览 ~10px → 区域近景 ~20px）
  const targetPx = Math.max(10, Math.min(20, 8.5 + scale.value * 3.2));
  const pinScale = targetPx / (18 * scale.value);
  return {
    left: p.wx + 'px',
    top: p.wy + 'px',
    transform: `translate(-50%, -50%) scale(${pinScale.toFixed(3)})`
  };
}

function beaconStyle(p) {
  const targetPx = Math.max(18, Math.min(34, 15 + scale.value * 4.8));
  const pinScale = targetPx / (28 * scale.value);
  return {
    left: p.wx + 'px',
    top: p.wy + 'px',
    transform: `translate(-50%, -50%) scale(${pinScale.toFixed(3)})`
  };
}

function routeClass(r) {
  if (r.kind === 'airship') return 'imap-route-air';
  if (r.faction === 'A') return 'imap-route-a';
  if (r.faction === 'H') return 'imap-route-h';
  return 'imap-route-n';
}

function lvShort(z) {
  const r = z.levelRange;
  if (Array.isArray(r) && r[0] != null) return r[1] && r[1] !== r[0] ? `${r[0]}-${r[1]}` : String(r[0]);
  return z.isCity ? '主城' : (z.isNew ? '无限新域' : '');
}

function factionLabel(f) {
  return f === 'A' ? '联盟' : (f === 'H' ? '部落' : '中立 / 双阵营');
}

function clampScale(s) {
  return Math.max(0.45, Math.min(11.0, s));
}

let tweenRaf = 0;

function stopTween() {
  if (tweenRaf && typeof cancelAnimationFrame === 'function') {
    cancelAnimationFrame(tweenRaf);
  }
  tweenRaf = 0;
}

function moveCamera(tx, ty, ts, smooth = true) {
  stopTween();
  const ns = clampScale(ts);
  if (!smooth || typeof requestAnimationFrame !== 'function' || typeof performance === 'undefined') {
    scale.value = ns;
    camX.value = tx;
    camY.value = ty;
    return;
  }
  const sx0 = camX.value;
  const sy0 = camY.value;
  const ss0 = scale.value;
  const t0 = performance.now();
  const dur = 240;
  function tick(now) {
    const p = Math.min(1, (now - t0) / dur);
    const e = 1 - Math.pow(1 - p, 3);
    scale.value = ss0 + (ns - ss0) * e;
    camX.value = sx0 + (tx - sx0) * e;
    camY.value = sy0 + (ty - sy0) * e;
    if (p < 1) {
      tweenRaf = requestAnimationFrame(tick);
    } else {
      tweenRaf = 0;
    }
  }
  tweenRaf = requestAnimationFrame(tick);
}

function flyTo(wx, wy, targetScale = 3.2, smooth = true) {
  syncVpSize();
  const ns = clampScale(targetScale);
  // 若左侧筛选抽屉展开，视觉中心略向右偏移以避开抽屉遮挡
  const cxOffset = (drawerOpen.value && vpW.value >= 960) ? 132 : 0;
  const tx = (vpW.value + cxOffset) / 2 - wx * ns;
  const ty = vpH.value / 2 - wy * ns;
  moveCamera(tx, ty, ns, smooth);
}

function fitCamera(preset = 'world', smooth = true) {
  syncVpSize();
  activePreset.value = preset;
  if (preset === 'kal') { flyTo(480, 670, Math.max(0.85, baseWorldScale.value * 1.62), smooth); return; }
  if (preset === 'ek') { flyTo(1480, 660, Math.max(0.85, baseWorldScale.value * 1.62), smooth); return; }
  if (preset === 'new') { flyTo(1050, 865, 3.0, smooth); return; }
  // 全览适配：扣除桌面端左侧浮层抽屉宽度，让卡利姆多与东部王国两块大陆同时完整呈现在可见视口内
  const leftInset = (drawerOpen.value && vpW.value >= 960) ? 274 : 0;
  const availW = Math.max(320, vpW.value - leftInset);
  const ns = baseWorldScale.value;
  const tx = leftInset + availW / 2 - (canvasSize.value.w / 2) * ns;
  const ty = (vpH.value + 16) / 2 - (canvasSize.value.h / 2) * ns;
  moveCamera(tx, ty, ns, smooth);
}

function flyToZone(z) {
  if (!z || !z.rect) return;
  activePreset.value = '';
  const cx = z.rect[0] + z.rect[2] / 2;
  const cy = z.rect[1] + z.rect[3] / 2;
  const availW = (drawerOpen.value && vpW.value >= 960) ? (vpW.value - 290) : vpW.value;
  const minZ = z.isCity ? 4.8 : Math.max(1.85, baseWorldScale.value * 3.4);
  const fitZ = Math.min((availW * 0.82) / z.rect[2], ((vpH.value - 80) * 0.82) / z.rect[3]);
  const target = Math.min(8.5, Math.max(minZ, fitZ));
  flyTo(cx, cy, target, true);
}

function stepZoom(factor) {
  const cxOffset = (drawerOpen.value && vpW.value >= 960) ? 132 : 0;
  const cx = ((vpW.value + cxOffset) / 2 - camX.value) / scale.value;
  const cy = (vpH.value / 2 - camY.value) / scale.value;
  activePreset.value = '';
  flyTo(cx, cy, scale.value * factor, true);
}

function hitZoneAt(wx, wy, preferCity = false) {
  const hits = zones.value.filter((z) =>
    wx >= z.rect[0] && wx <= z.rect[0] + z.rect[2] && wy >= z.rect[1] && wy <= z.rect[1] + z.rect[3]
  );
  if (!hits.length) return null;
  if (preferCity) {
    const city = hits.find((z) => z.isCity);
    if (city) return city;
  }
  const nonCity = hits.filter((z) => !z.isCity);
  const pool = nonCity.length ? nonCity : hits;
  pool.sort((a, b) => (a.rect[2] * a.rect[3]) - (b.rect[2] * b.rect[3]));
  return pool[0];
}

function onWheel(e) {
  const el = viewportEl.value;
  if (!el) return;
  stopTween();
  activePreset.value = '';
  const rect = el.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const wx = (mx - camX.value) / scale.value;
  const wy = (my - camY.value) / scale.value;
  // 仿 OpenMap ZOOM_STEP = 1.25：锚定鼠标光标平滑切入具体区域地图与主城地图
  const ns = clampScale(scale.value * (e.deltaY < 0 ? 1.28 : 0.78));
  scale.value = ns;
  camX.value = mx - wx * ns;
  camY.value = my - wy * ns;
}

// 仿 OpenMap 右键逐级退回：主城 → 所属具体区域 → 所在大陆 → 世界全览
function onRightClickOut() {
  if (activeZone.value && activeZone.value.isCity) {
    const cxOffset = (drawerOpen.value && vpW.value >= 960) ? 132 : 0;
    const cwx = ((vpW.value + cxOffset) / 2 - camX.value) / scale.value;
    const cwy = (vpH.value / 2 - camY.value) / scale.value;
    const parent = hitZoneAt(cwx, cwy, false);
    if (parent && !parent.isCity) { flyToZone(parent); return; }
  }
  if (relZoom.value >= 2.15) {
    const z = activeZone.value;
    if (z && z.continent === 'kal') { fitCamera('kal', true); return; }
    if (z && z.continent === 'ek') { fitCamera('ek', true); return; }
    stepZoom(0.55);
    return;
  }
  fitCamera('world', true);
}

function onPointerDown(e) {
  if (e.button !== 0) return;
  stopTween();
  dragging.value = true;
  activePreset.value = '';
  dragStart = { x: e.clientX, y: e.clientY, ox: camX.value, oy: camY.value };
  if (e.currentTarget && e.currentTarget.setPointerCapture) {
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (_) {}
  }
}

function onPointerMove(e) {
  const el = viewportEl.value;
  if (el) {
    const rect = el.getBoundingClientRect();
    const wx = (e.clientX - rect.left - camX.value) / scale.value;
    const wy = (e.clientY - rect.top - camY.value) / scale.value;
    const hit = hitZoneAt(wx, wy, relZoom.value >= 3.6);
    if (hit) {
      const px = (((wx - hit.rect[0]) / hit.rect[2]) * 100).toFixed(1);
      const py = (((wy - hit.rect[1]) / hit.rect[3]) * 100).toFixed(1);
      hudZone.value = hit.nameCn;
      hudLevel.value = lvTxt(hit) || (hit.isCity ? '主城' : hit.continentCn);
      hudCoord.value = `坐标 ${px}, ${py}`;
    } else {
      hudZone.value = '无尽之海';
      hudLevel.value = '拖拽平移 · 滚轮切入区域';
      hudCoord.value = '坐标 --.-, --.-';
    }
  }
  if (!dragging.value) return;
  camX.value = dragStart.ox + (e.clientX - dragStart.x);
  camY.value = dragStart.oy + (e.clientY - dragStart.y);
}

// 仿 OpenMap WorldMap.lua：全览/大陆态左键单击某区域直接平滑飞入该具体区域地图
function onPointerUp(e) {
  const wasDragging = dragging.value;
  dragging.value = false;
  if (!wasDragging || !e) return;
  const dist = Math.hypot(e.clientX - dragStart.x, e.clientY - dragStart.y);
  if (dist < 5 && relZoom.value < 1.95 && viewportEl.value) {
    const rect = viewportEl.value.getBoundingClientRect();
    const wx = (e.clientX - rect.left - camX.value) / scale.value;
    const wy = (e.clientY - rect.top - camY.value) / scale.value;
    const hit = hitZoneAt(wx, wy, false);
    if (hit) flyToZone(hit);
  }
}

function selectPin(p) {
  selectedId.value = p.id;
  copyMsg.value = '';
}

function clearSelect() {
  selectedId.value = '';
  copyMsg.value = '';
}

function toggleGroup(gKey) {
  const list = catsByGroup.value[gKey] || [];
  const allOn = list.every((c) => enabled[c.key]);
  list.forEach((c) => { enabled[c.key] = !allOn; });
}

function toggleDone(id) {
  const next = new Set(doneSet.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  doneSet.value = next;
  saveDoneSet(next);
}

function copyText(text, label) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      copyMsg.value = `已复制${label}：${text}`;
    }).catch(() => {
      copyMsg.value = `${label}：${text}`;
    });
  } else {
    copyMsg.value = `${label}：${text}`;
  }
}

function copyWay(p) {
  copyText(buildWayCommand(p), ' /way 指令');
}

function copyShare(p) {
  const url = (typeof window !== 'undefined' ? window.location.origin + window.location.pathname : '') + buildShareHash(p);
  copyText(url, '直达链接');
}

const searchHits = computed(() => {
  const kw = q.value.trim().toLowerCase();
  if (!kw) return [];
  const zHits = zones.value
    .filter((z) => (z.nameCn + ' ' + z.mapId + ' ' + z.continentCn).toLowerCase().includes(kw))
    .slice(0, 5)
    .map((z) => ({ key: 'z:' + z.mapId, type: 'zone', label: z.nameCn, sub: lvShort(z) ? `${lvShort(z)} 级` : z.continentCn, z }));
  const pHits = allPins.value
    .filter((p) => p.search.includes(kw))
    .slice(0, 12)
    .map((p) => ({ key: 'p:' + p.id, type: 'pin', label: p.name, sub: `${p.tag} · ${p.zone}`, p }));
  return zHits.concat(pHits).slice(0, 14);
});

function pickHit(h) {
  dropOpen.value = false;
  if (h.type === 'zone') {
    flyToZone(h.z);
    return;
  }
  const p = h.p;
  enabled[p.cat] = true;
  const cm = CAT_BY_KEY[p.cat];
  activePreset.value = '';
  flyTo(p.wx, p.wy, Math.max(3.6, (cm ? cm.minZoom : 2.8) + 1.0), true);
  selectPin(p);
}

// 兼容旧链接 #/world?t=zones|rares|books|bag&q=... 与新链接 #/world?map=...&pin=...
function applyQuery() {
  if (!ready.value) return;
  const t = String(route.query.t || '');
  const pinQ = String(route.query.pin || '');
  const mapQ = String(route.query.map || '');
  const kwQ = String(route.query.q || '');

  if (t === 'rares' || t === 'books' || t === 'bag') {
    MAP_CATEGORIES.forEach((c) => { enabled[c.key] = false; });
    if (t === 'rares') enabled.rare = true;
    if (t === 'books') { enabled.book = true; enabled.legacy_book = true; }
    if (t === 'bag') enabled.camp = true;
    optLod.value = false;
  } else if (t === 'zones') {
    drawerTab.value = 'zones';
  }

  if (pinQ) {
    const hit = allPins.value.find((p) => p.id === pinQ);
    if (hit) {
      enabled[hit.cat] = true;
      flyTo(hit.wx, hit.wy, 4.2, true);
      selectPin(hit);
      return;
    }
  }
  if (mapQ) {
    const z = zones.value.find((x) => String(x.mapId) === mapQ);
    if (z) { flyToZone(z); return; }
  }
  if (kwQ) {
    q.value = kwQ;
    const hit = searchHits.value[0];
    if (hit) pickHit(hit);
  }
}

watch(() => [route.query.t, route.query.q, route.query.map, route.query.pin], applyQuery);

const librarians = computed(() => (world.value && world.value.librarians) || []);
const rewards = computed(() => (world.value && world.value.bookRewards) || []);
const rareSets = computed(() => (world.value && world.value.rareSets) || []);
const missingBooks = computed(() => (world.value && world.value.booksMissing) || []);
const unplacedRares = computed(() => (world.value && world.value.raresUnplaced) || []);
const bagRows = computed(() => {
  const p = (world.value && world.value.bagTool && world.value.bagTool.params) || null;
  if (!p) return [];
  return [
    ['铺开耗时', p.castSec + ' 秒'],
    ['休息收益名', p.buffName || '—'],
    ['收益持续', p.buffHours + ' 小时'],
    ['可叠层', p.stacks + ' 层'],
    ['铺设冷却', p.cdMin + ' 分钟']
  ];
});

function onDocClick(e) {
  if (searchBoxEl.value && !searchBoxEl.value.contains(e.target)) {
    dropOpen.value = false;
  }
}

onMounted(() => {
  if (typeof window !== 'undefined' && window.innerWidth < 960) {
    drawerOpen.value = false;
  }
  boot();
  window.addEventListener('resize', syncVpSize, { passive: true });
  document.addEventListener('click', onDocClick);
  document.addEventListener('fullscreenchange', onFullscreenChange);
  document.addEventListener('keydown', onEscKey);
});

onBeforeUnmount(() => {
  stopTween();
  window.removeEventListener('resize', syncVpSize);
  document.removeEventListener('click', onDocClick);
  document.removeEventListener('fullscreenchange', onFullscreenChange);
  document.removeEventListener('keydown', onEscKey);
});
</script>
