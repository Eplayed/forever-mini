<template>
  <section v-if="hasContent" class="ps-wrap" :class="'ps-pos-' + position" aria-label="合作推荐与广告">
    <!-- 外设 / 加速器合作推荐槽 -->
    <div v-if="partnerItems.length" class="ps-grid">
      <article v-for="item in partnerItems" :key="item.id" class="ps-card">
        <div class="ps-head">
          <span class="ps-badge">{{ item.badge || '合作推荐' }}</span>
          <span v-if="categoryLabel(item.category)" class="ps-cat">{{ categoryLabel(item.category) }}</span>
          <span v-if="item.vendor" class="ps-vendor">{{ item.vendor }}</span>
        </div>
        <div class="ps-body">
          <img v-if="item.artFile && !badImgs[item.id]"
               class="ps-art"
               :src="assetUrl(item.artFile)"
               :alt="item.title"
               width="64"
               height="64"
               loading="lazy"
               @error="badImgs[item.id] = true">
          <div class="ps-copy">
            <div class="ps-title">{{ item.title }}</div>
            <div v-if="item.subtitle" class="ps-sub">{{ item.subtitle }}</div>
            <p v-if="item.desc" class="ps-desc">{{ item.desc }}</p>
          </div>
          <a class="ps-cta"
             :href="item.url"
             target="_blank"
             rel="sponsored noopener noreferrer"
             :data-slot-id="item.id"
             @click="onClickSlot(item)">{{ item.ctaLabel }}</a>
        </div>
        <div v-if="item.note" class="ps-note">{{ item.note }}</div>
      </article>
    </div>

    <!-- 广告联盟展示位（Google AdSense / 百度联盟，默认关闭零渲染，仅在允许的生产域名加载） -->
    <div v-if="activeAd" class="ps-ad" :data-provider="activeAd.provider">
      <div class="ps-ad-hd">
        <span class="ps-badge">广告</span>
        <span class="ps-ad-tip">赞助展示用于支持本站服务器与数据维护</span>
      </div>
      <div ref="adBoxEl" class="ps-ad-box">
        <ins v-if="activeAd.provider === 'adsense'"
             class="adsbygoogle"
             style="display:block"
             :data-ad-client="activeAd.clientId"
             :data-ad-slot="activeAd.slotId"
             data-ad-format="auto"
             data-full-width-responsive="true"></ins>
        <div v-else-if="activeAd.provider === 'baidu'"
             :id="'pb-bd-ad-' + activeAd.slotId"
             class="ps-ad-bd"></div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { assetUrl, load } from '../lib/data.js';
import { trackSlotClick, trackSlotView } from '../lib/analytics.js';

const props = defineProps({
  position: {
    type: String,
    required: true
  }
});

const CATEGORY_MAP = {
  accelerator: '网络加速',
  peripheral: '外设装备',
  partner: '合作推荐'
};

const cfg = ref(null);
const badImgs = reactive({});
const adBoxEl = ref(null);
const adMounted = ref(false);

const hostAllowed = computed(() => {
  const c = cfg.value;
  if (!c || !c.enabled) return false;
  const hosts = Array.isArray(c.allowedHosts) ? c.allowedHosts : [];
  if (!hosts.length) return true;
  const cur = typeof location !== 'undefined' ? location.hostname.toLowerCase() : '';
  return hosts.some((h) => String(h || '').toLowerCase() === cur);
});

const partnerItems = computed(() => {
  const c = cfg.value;
  if (!c || !c.enabled || !Array.isArray(c.slots)) return [];
  return c.slots.filter((s) => (
    s
    && s.id
    && s.position === props.position
    && s.kind === 'partner'
    && s.title
    && s.ctaLabel
    && /^https:\/\//.test(String(s.url || ''))
  ));
});

const activeAd = computed(() => {
  const c = cfg.value;
  if (!c || !c.enabled || !hostAllowed.value) return null;
  const nets = c.adNetworks || {};
  const adsense = nets.adsense || {};
  const adsenseSlot = adsense.positions && adsense.positions[props.position];
  if (adsense.enabled && /^ca-pub-\d+$/.test(String(adsense.clientId || '')) && /^\d+$/.test(String(adsenseSlot || ''))) {
    return {
      provider: 'adsense',
      clientId: String(adsense.clientId),
      slotId: String(adsenseSlot)
    };
  }
  const baidu = nets.baidu || {};
  const baiduSlot = baidu.positions && baidu.positions[props.position];
  if (baidu.enabled && /^[A-Za-z0-9_-]+$/.test(String(baidu.unionId || '')) && /^[A-Za-z0-9_-]+$/.test(String(baiduSlot || ''))) {
    return {
      provider: 'baidu',
      unionId: String(baidu.unionId),
      slotId: String(baiduSlot)
    };
  }
  return null;
});

const hasContent = computed(() => partnerItems.value.length > 0 || Boolean(activeAd.value));

function categoryLabel(cat) {
  return CATEGORY_MAP[String(cat || '')] || '';
}

function onClickSlot(item) {
  trackSlotClick(item);
}

function ensureScript(id, src) {
  if (typeof document === 'undefined') return Promise.resolve();
  if (document.getElementById(id)) return Promise.resolve();
  return new Promise((resolve) => {
    const s = document.createElement('script');
    s.id = id;
    s.async = true;
    s.src = src;
    s.crossOrigin = 'anonymous';
    s.onload = () => resolve();
    s.onerror = () => resolve();
    document.head.appendChild(s);
  });
}

async function mountAdIfReady() {
  const ad = activeAd.value;
  if (!ad || adMounted.value) return;
  adMounted.value = true;
  trackSlotView({
    id: `ad-${ad.provider}-${props.position}`,
    kind: 'ad-network',
    position: props.position
  });
  await nextTick();
  try {
    if (ad.provider === 'adsense') {
      await ensureScript(
        'pb-adsense-sdk',
        `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(ad.clientId)}`
      );
      if (typeof window !== 'undefined') {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
      }
    } else if (ad.provider === 'baidu') {
      await ensureScript('pb-baidu-union-sdk', 'https://cpro.baidustatic.com/cpro/ui/cm.js');
      if (typeof window !== 'undefined' && Array.isArray(window.slotbydup || [])) {
        (window.slotbydup = window.slotbydup || []).push({
          id: ad.slotId,
          container: 'pb-bd-ad-' + ad.slotId
        });
      }
    }
  } catch (_) {}
}

watch(partnerItems, (list) => {
  list.forEach((item) => trackSlotView(item));
});

watch(activeAd, () => {
  mountAdIfReady();
});

onMounted(() => {
  load('data/partner-slots.json')
    .then((doc) => {
      if (!doc || typeof doc !== 'object') return;
      cfg.value = doc;
      partnerItems.value.forEach((item) => trackSlotView(item));
      mountAdIfReady();
    })
    .catch(() => { /* 无配置或加载失败时不占任何页面空间 */ });
});
</script>

<style scoped>
.ps-wrap {
  margin-top: var(--s5);
  display: flex;
  flex-direction: column;
  gap: var(--s3);
  max-width: 100%;
}

.ps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--s3);
}

.ps-card {
  background: var(--panel-2);
  border: 1px solid var(--gold-line);
  padding: var(--s3) var(--s4);
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  min-width: 0;
}

.ps-head {
  display: flex;
  align-items: center;
  gap: var(--s2);
  flex-wrap: wrap;
}

.ps-badge {
  font-size: 10.5px;
  letter-spacing: 0.05em;
  color: var(--gold-hi);
  border: 1px solid var(--gold-line);
  background: var(--panel);
  padding: 1px 6px;
}

.ps-cat {
  font-size: 11px;
  color: var(--azure);
}

.ps-vendor {
  font-size: 11px;
  color: var(--txt-muted);
  margin-left: auto;
}

.ps-body {
  display: flex;
  align-items: center;
  gap: var(--s3);
  flex-wrap: wrap;
}

.ps-art {
  width: 56px;
  height: 56px;
  object-fit: cover;
  border: 1px solid var(--line-2);
  background: var(--sunk);
  flex: 0 0 auto;
}

.ps-copy {
  flex: 1 1 180px;
  min-width: 0;
}

.ps-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: var(--txt-title);
}

.ps-sub {
  font-size: 12px;
  color: var(--gold);
  margin-top: 2px;
}

.ps-desc {
  margin: 4px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--txt-dim);
}

.ps-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 0 var(--s4);
  font-size: 12.5px;
  font-weight: 700;
  color: var(--ink-on-bright);
  background: linear-gradient(180deg, var(--gold-hi), var(--gold));
  text-decoration: none;
  white-space: nowrap;
}

.ps-cta:hover {
  text-decoration: none;
  filter: brightness(1.06);
}

.ps-note {
  font-size: 11px;
  color: var(--txt-muted);
}

.ps-ad {
  background: var(--panel-2);
  border: 1px solid var(--line);
  padding: var(--s3);
}

.ps-ad-hd {
  display: flex;
  align-items: center;
  gap: var(--s2);
  margin-bottom: var(--s2);
}

.ps-ad-tip {
  font-size: 11px;
  color: var(--txt-muted);
}

.ps-ad-box {
  min-height: 90px;
  overflow: hidden;
}
</style>
