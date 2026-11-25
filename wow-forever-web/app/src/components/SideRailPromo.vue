<template>
  <aside v-if="visibleSlots.length && !dismissed" class="side-rail" aria-label="桌面副屏导流与推荐">
    <button type="button" class="sr-close" aria-label="收起侧栏推荐" title="本次浏览收起" @click="dismiss">×</button>
    <div v-for="slot in visibleSlots" :key="slot.id" class="sr-card" :class="'sr-kind-' + (slot.kind || 'promo')">
      <span class="sr-badge">{{ slot.badge }}</span>
      <img v-if="slot.artFile && !badImgs[slot.id]"
           class="sr-ico"
           :class="{ 'sr-qr': slot.kind === 'mini-program' }"
           :src="assetUrl(slot.artFile)"
           :alt="slot.title"
           :width="slot.kind === 'mini-program' ? 88 : 64"
           :height="slot.kind === 'mini-program' ? 88 : 64"
           loading="lazy"
           @error="markBad(slot.id)">
      <div class="sr-title">{{ slot.title }}</div>
      <div v-if="slot.subtitle" class="sr-sub">{{ slot.subtitle }}</div>
      <p v-if="slot.desc" class="sr-desc">{{ slot.desc }}</p>
      <button v-if="slot.kind === 'mini-program'"
              type="button"
              class="sr-cta"
              :data-slot-id="slot.id"
              @click="openQrModal(slot)">{{ slot.ctaLabel }}</button>
      <a v-else
         class="sr-cta"
         :href="slot.url"
         target="_blank"
         rel="sponsored noopener noreferrer"
         :data-slot-id="slot.id"
         @click="onSlotClick(slot)">{{ slot.ctaLabel }}</a>
      <div v-if="slot.note" class="sr-note">{{ slot.note }}</div>
    </div>
  </aside>

  <div v-if="qrSlot" class="sr-modal-mask" role="dialog" aria-modal="true"
       :aria-label="qrSlot.title + ' 扫码窗口'" @click.self="closeQrModal">
    <div class="sr-modal">
      <button type="button" class="sr-modal-x" aria-label="关闭扫码窗口" @click="closeQrModal">×</button>
      <span class="sr-badge">{{ qrSlot.badge }}</span>
      <h3 class="sr-modal-h">{{ qrSlot.title }}</h3>
      <img v-if="qrSlot.artFile && !badImgs[qrSlot.id]"
           class="sr-modal-qr"
           :src="assetUrl(qrSlot.artFile)"
           :alt="qrSlot.title + ' 微信太阳码'"
           width="220"
           height="220">
      <p v-if="qrSlot.desc" class="sr-modal-desc">{{ qrSlot.desc }}</p>
      <div v-if="qrSlot.searchHint" class="sr-modal-hint">{{ qrSlot.searchHint }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { assetUrl, load } from '../lib/data.js';
import { trackSlotClick, trackSlotView } from '../lib/analytics.js';

const DISMISS_KEY = 'wow_forever_v1_side_rail_closed';
const slots = ref([]);
const enabled = ref(false);
const dismissed = ref(false);
const badImgs = reactive({});
const qrSlot = ref(null);

function isValidSlot(s) {
  if (!s || !s.id || !s.title || !s.ctaLabel) return false;
  if (s.position !== 'desktop-right-rail') return false;
  if (s.kind === 'mini-program') return Boolean(s.artFile);
  return Boolean(s.url && /^https:\/\//.test(String(s.url)));
}

const visibleSlots = computed(() => {
  if (!enabled.value || !slots.value.length) return [];
  return slots.value.filter(isValidSlot).slice(0, 3);
});

function markBad(id) {
  badImgs[id] = true;
}

function dismiss() {
  dismissed.value = true;
  qrSlot.value = null;
  try { window.sessionStorage.setItem(DISMISS_KEY, '1'); } catch (_) {}
}

function onSlotClick(slot) {
  trackSlotClick(slot);
}

function openQrModal(slot) {
  trackSlotClick(slot);
  qrSlot.value = slot;
}

function closeQrModal() {
  qrSlot.value = null;
}

function onKeyDown(e) {
  if (e && e.key === 'Escape' && qrSlot.value) {
    closeQrModal();
  }
}

function reportVisibleViews() {
  if (dismissed.value || typeof window === 'undefined' || window.innerWidth < 1440) return;
  visibleSlots.value.forEach((s) => trackSlotView(s));
}

watch(visibleSlots, () => {
  reportVisibleViews();
});

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', onKeyDown);
  }
  try {
    if (window.sessionStorage.getItem(DISMISS_KEY) === '1') {
      dismissed.value = true;
      return;
    }
  } catch (_) {}
  load('data/side-rail.json')
    .then((doc) => {
      if (!doc || !doc.enabled || !Array.isArray(doc.slots)) return;
      enabled.value = true;
      slots.value = doc.slots;
      reportVisibleViews();
    })
    .catch(() => { /* 无配置或加载失败时不占任何页面空间 */ });
});

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', onKeyDown);
  }
});
</script>

<style scoped>
.side-rail {
  display: none;
}

/* 仅在 1440px 以上桌面宽屏挂载于 1180px 主内容右侧留白区，零挤压正文、零横溢 */
@media (min-width: 1440px) {
  .side-rail {
    display: flex;
    flex-direction: column;
    gap: var(--s2);
    position: fixed;
    top: calc(var(--hd-h, 93px) + 16px);
    left: calc(50% + 596px);
    width: 116px;
    padding: 24px 6px 8px;
    background: var(--panel);
    border: 1px solid var(--gold-line);
    box-shadow: 0 8px 24px var(--sunk-2);
    z-index: 12;
  }

  .sr-close {
    position: absolute;
    top: 3px;
    right: 4px;
    width: 22px;
    height: 22px;
    padding: 0;
    line-height: 20px;
    font-size: 14px;
    color: var(--txt-muted);
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
  }

  .sr-close:hover {
    color: var(--gold-hi);
    border-color: var(--line);
  }

  .sr-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 6px;
    padding: var(--s2) 4px;
    background: var(--panel-2);
    border: 1px solid var(--line);
  }

  .sr-card + .sr-card {
    border-color: var(--gold-line-soft);
  }

  .sr-badge {
    font-size: 10px;
    letter-spacing: 0.05em;
    color: var(--gold-hi);
    border: 1px solid var(--gold-line);
    background: var(--panel);
    padding: 1px 6px;
  }

  .sr-ico {
    display: block;
    width: 52px;
    height: 52px;
    object-fit: cover;
    border: 1px solid var(--gold-line);
    background: var(--sunk);
  }

  .sr-ico.sr-qr {
    width: 82px;
    height: 82px;
    padding: 3px;
    object-fit: contain;
    background: var(--q1);
    border-color: var(--gold-line-2);
  }

  .sr-title {
    font-family: var(--font-display);
    font-size: 13px;
    font-weight: 700;
    color: var(--txt-title);
    line-height: 1.25;
  }

  .sr-sub {
    font-size: 10.5px;
    color: var(--gold);
    line-height: 1.3;
  }

  .sr-desc {
    display: none;
    margin: 0;
    font-size: 11.5px;
    line-height: 1.45;
    color: var(--txt-dim);
  }

  .sr-cta {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 30px;
    padding: 4px 6px;
    font-size: 11px;
    font-weight: 700;
    color: var(--ink-on-bright);
    background: linear-gradient(180deg, var(--gold-hi), var(--gold));
    border: 0;
    text-decoration: none;
    cursor: pointer;
  }

  .sr-cta:hover {
    text-decoration: none;
    filter: brightness(1.06);
  }

  .sr-note {
    font-size: 10px;
    line-height: 1.3;
    color: var(--txt-muted);
  }
}

/* 1600px+ 大屏展开为 184px 完整展示卡片 */
@media (min-width: 1600px) {
  .side-rail {
    left: calc(50% + 608px);
    width: 184px;
    padding: 26px var(--s3) var(--s3);
    gap: var(--s3);
  }

  .sr-card {
    padding: var(--s3) var(--s2);
    gap: 8px;
  }

  .sr-ico {
    width: 64px;
    height: 64px;
  }

  .sr-ico.sr-qr {
    width: 112px;
    height: 112px;
    padding: 4px;
  }

  .sr-title {
    font-size: 14.5px;
  }

  .sr-desc {
    display: block;
  }

  .sr-cta {
    font-size: 12px;
    min-height: 34px;
  }
}

.sr-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--top-bg);
  padding: var(--s4);
}

.sr-modal {
  position: relative;
  width: min(320px, 100%);
  padding: var(--s5) var(--s4);
  background: var(--panel);
  border: 1px solid var(--gold-line-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--s3);
  box-shadow: 0 16px 40px var(--sunk-2);
}

.sr-modal-x {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  padding: 0;
  font-size: 18px;
  line-height: 26px;
  color: var(--txt-dim);
  background: transparent;
  border: 1px solid var(--line);
  cursor: pointer;
}

.sr-modal-x:hover {
  color: var(--gold-hi);
  border-color: var(--gold-line);
}

.sr-modal-h {
  margin: 0;
  font-family: var(--font-display);
  font-size: 18px;
  color: var(--txt-title);
}

.sr-modal-qr {
  display: block;
  width: 220px;
  height: 220px;
  padding: 8px;
  background: var(--q1);
  border: 1px solid var(--gold-line);
  object-fit: contain;
}

.sr-modal-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--txt-dim);
}

.sr-modal-hint {
  font-size: 12px;
  font-weight: 700;
  color: var(--gold-hi);
  padding: 6px 12px;
  background: var(--panel-2);
  border: 1px solid var(--gold-line);
}
</style>
