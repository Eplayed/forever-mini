import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import {
  initAnalytics,
  trackEvent,
  trackSlotView,
  trackSlotClick,
  getAnalyticsBuffer,
  resetAnalyticsForTest,
  isHostAllowed,
  getViewportBucket,
  extractHost
} from '../src/lib/analytics.js';
import { forget } from '../src/lib/data.js';
import SideRailPromo from '../src/components/SideRailPromo.vue';
import PartnerSlots from '../src/components/PartnerSlots.vue';

describe('轻量隐私统计引擎（analytics.js）', () => {
  beforeEach(() => {
    resetAnalyticsForTest();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    resetAnalyticsForTest();
    vi.restoreAllMocks();
  });

  it('视口分档与域名提取准确且安全', () => {
    expect(getViewportBucket(375)).toBe('mobile');
    expect(getViewportBucket(900)).toBe('tablet');
    expect(getViewportBucket(1440)).toBe('desktop');
    expect(getViewportBucket(1920)).toBe('wide');
    expect(extractHost('https://www.taptap.cn/app/1090838?from=web')).toBe('www.taptap.cn');
    expect(extractHost('javascript:alert(1)')).toBe('');
  });

  it('仅允许白名单生产域名发包，本地测试域名静默不发网络请求', async () => {
    const cfg = {
      enabled: true,
      allowedHosts: ['paoben.top', 'www.paoben.top'],
      respectDnt: true,
      fcBeacon: { enabled: true, endpoint: '/api/t' },
      provider: { type: 'none', siteId: '', scriptUrl: '' }
    };
    expect(isHostAllowed(cfg, 'paoben.top')).toBe(true);
    expect(isHostAllowed(cfg, 'www.paoben.top')).toBe(true);
    expect(isHostAllowed(cfg, '127.0.0.1')).toBe(false);
    expect(isHostAllowed(cfg, 'localhost')).toBe(false);
    expect(isHostAllowed(cfg, 'eplayed.github.io')).toBe(false);

    const beaconSpy = vi.fn(() => true);
    Object.defineProperty(navigator, 'sendBeacon', { value: beaconSpy, configurable: true });

    const afterHooks = [];
    const fakeRouter = {
      currentRoute: { value: { path: '/bis', query: {} } },
      afterEach: (fn) => afterHooks.push(fn)
    };
    await initAnalytics(fakeRouter, cfg);
    // jsdom 默认 hostname 为 localhost，不在 allowedHosts 内，因此不发 beacon 但记录在本地缓冲
    expect(beaconSpy).not.toHaveBeenCalled();
    expect(getAnalyticsBuffer().some((e) => e.ev === 'pv' && e.p === '/bis')).toBe(true);

    // 切换路由时记录新 PV，搜索路由额外记录 search
    afterHooks[0]({ path: '/', query: { q: '通灵学院' } }, { path: '/bis', query: {} });
    const buf = getAnalyticsBuffer();
    expect(buf.some((e) => e.ev === 'pv' && e.p === '/')).toBe(true);
    expect(buf.some((e) => e.ev === 'search' && e.p === '/')).toBe(true);
  });

  it('推荐位曝光同页去重，点击每次均记录归因字段', async () => {
    const cfg = {
      enabled: true,
      allowedHosts: ['localhost'],
      respectDnt: false,
      fcBeacon: { enabled: true, endpoint: '/api/t' },
      provider: { type: 'none', siteId: '', scriptUrl: '' }
    };
    const beaconSpy = vi.fn(() => true);
    Object.defineProperty(navigator, 'sendBeacon', { value: beaconSpy, configurable: true });

    await initAnalytics({ currentRoute: { value: { path: '/' } }, afterEach: () => {} }, cfg);
    const slot = {
      id: 'cw-taptap-minigame',
      kind: 'self-game',
      position: 'desktop-right-rail',
      url: 'https://www.taptap.cn/app/1090838'
    };
    expect(trackSlotView(slot)).toBe(true);
    expect(trackSlotView(slot)).toBe(false); // 同路由重复曝光不刷数
    expect(trackSlotClick(slot)).toBe(true);
    expect(trackSlotClick(slot)).toBe(true);

    const views = getAnalyticsBuffer().filter((e) => e.ev === 'slot_view' && e.slot === 'cw-taptap-minigame');
    const clicks = getAnalyticsBuffer().filter((e) => e.ev === 'slot_click' && e.slot === 'cw-taptap-minigame');
    expect(views.length).toBe(1);
    expect(clicks.length).toBe(2);
    expect(clicks[0].host).toBe('www.taptap.cn');
    expect(beaconSpy).toHaveBeenCalled();
  });

  it('全站外链点击自动归因且不与带 data-slot-id 的推荐位重复计账', async () => {
    await initAnalytics({ currentRoute: { value: { path: '/dungeons' } }, afterEach: () => {} }, {
      enabled: true,
      allowedHosts: ['paoben.top'],
      respectDnt: false,
      fcBeacon: { enabled: true, endpoint: '/api/t' }
    });
    const a1 = document.createElement('a');
    a1.href = 'https://beian.miit.gov.cn/';
    document.body.appendChild(a1);
    a1.click();

    const a2 = document.createElement('a');
    a2.href = 'https://www.taptap.cn/app/1090838';
    a2.setAttribute('data-slot-id', 'cw-taptap-minigame');
    document.body.appendChild(a2);
    a2.click();

    const out = getAnalyticsBuffer().filter((e) => e.ev === 'outbound_click');
    expect(out.length).toBe(1);
    expect(out[0].host).toBe('beian.miit.gov.cn');

    a1.remove();
    a2.remove();
  });
});

describe('桌面副屏导流（SideRailPromo）', () => {
  beforeEach(() => {
    resetAnalyticsForTest();
    window.sessionStorage.clear();
    forget('data/side-rail.json');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('同时渲染微信小程序太阳码卡与自研游戏卡，并支持点击弹出大图扫码与上报点击', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        enabled: true,
        slots: [
          {
            id: 'mini-program-paoben',
            position: 'desktop-right-rail',
            kind: 'mini-program',
            badge: '微信小程序',
            title: '跑本无限助手',
            subtitle: '手机同步跑本清单',
            ctaLabel: '放大扫码',
            searchHint: '微信搜一搜：跑本无限助手',
            artFile: 'img/art/brand/mini-qrcode.jpg'
          },
          {
            id: 'cw-taptap-minigame',
            position: 'desktop-right-rail',
            kind: 'self-game',
            badge: '站长自研',
            title: '超武刷宝觉醒',
            ctaLabel: '去 TapTap 试玩',
            url: 'https://www.taptap.cn/app/1090838',
            artFile: 'img/art/side-rail/cw-icon.png'
          }
        ]
      })
    }));

    const wrapper = mount(SideRailPromo);
    await flushPromises();

    expect(wrapper.findAll('.sr-card').length).toBe(2);
    expect(wrapper.text()).toContain('跑本无限助手');
    expect(wrapper.text()).toContain('超武刷宝觉醒');

    // 点击放大扫码按钮弹出太阳码窗口并记录 slot_click
    await wrapper.find('button.sr-cta').trigger('click');
    expect(wrapper.find('.sr-modal').exists()).toBe(true);
    expect(wrapper.find('.sr-modal').text()).toContain('微信搜一搜：跑本无限助手');
    expect(getAnalyticsBuffer().some((e) => e.ev === 'slot_click' && e.slot === 'mini-program-paoben')).toBe(true);

    // 关闭弹窗
    await wrapper.find('.sr-modal-x').trigger('click');
    expect(wrapper.find('.sr-modal').exists()).toBe(false);
  });
});

describe('合作推荐与广告联盟底座（PartnerSlots）', () => {
  beforeEach(() => {
    resetAnalyticsForTest();
    forget('data/partner-slots.json');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('关闭或空配置时不渲染任何 DOM（零占位、零空白栏）', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        enabled: false,
        allowedHosts: ['paoben.top'],
        adNetworks: { adsense: { enabled: false, clientId: '', positions: {} } },
        slots: []
      })
    }));

    const wrapper = mount(PartnerSlots, { props: { position: 'page-bottom' } });
    await flushPromises();
    expect(wrapper.find('.ps-wrap').exists()).toBe(false);
    expect(wrapper.html()).toBe('<!--v-if-->');
  });

  it('启用外设/加速器合作槽时仅渲染匹配位置的条目并带 sponsored 关系与埋点', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        enabled: true,
        allowedHosts: ['localhost'],
        adNetworks: { adsense: { enabled: false, clientId: '', positions: {} } },
        slots: [
          {
            id: 'partner-acc-demo',
            position: 'bis-inline',
            kind: 'partner',
            category: 'accelerator',
            vendor: '测试加速伙伴',
            badge: '合作推荐',
            title: '低延迟游戏加速节点',
            desc: '团本开荒低延迟线路支持',
            ctaLabel: '了解详情',
            url: 'https://example.com/acc',
            note: '合作推荐链接，与本站资料无关'
          },
          {
            id: 'partner-other-pos',
            position: 'page-bottom',
            kind: 'partner',
            category: 'peripheral',
            title: '其他位置的条目',
            ctaLabel: '查看',
            url: 'https://example.com/other'
          }
        ]
      })
    }));

    const wrapper = mount(PartnerSlots, { props: { position: 'bis-inline' } });
    await flushPromises();

    const cards = wrapper.findAll('.ps-card');
    expect(cards.length).toBe(1);
    expect(wrapper.text()).toContain('合作推荐');
    expect(wrapper.text()).toContain('网络加速');
    const link = wrapper.find('a.ps-cta');
    expect(link.attributes('rel')).toBe('sponsored noopener noreferrer');
    await link.trigger('click');
    expect(getAnalyticsBuffer().some((e) => e.ev === 'slot_click' && e.slot === 'partner-acc-demo')).toBe(true);
  });
});
