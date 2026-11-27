import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { initForgeFx, isForgeFxOff, setForgeFxOff, toggleForgeFx } from '../src/lib/forge-fx.js';
import ForgeEmbers from '../src/components/ForgeEmbers.vue';

describe('Obsidian Forge interactive engine (forge-fx & ForgeEmbers)', () => {
  let stop = null;

  beforeEach(() => {
    document.body.innerHTML = '';
    document.documentElement.classList.remove('forge-fx-off');
    try { window.localStorage.removeItem('wow_forever_v1_forge_fx'); } catch (_) {}
    vi.stubGlobal('matchMedia', (q) => ({
      matches: q.includes('hover: hover'),
      media: q,
      addEventListener() {},
      removeEventListener() {}
    }));
    vi.stubGlobal('requestAnimationFrame', (cb) => { cb(0); return 1; });
    vi.stubGlobal('cancelAnimationFrame', () => {});
  });

  afterEach(() => {
    if (stop) { stop(); stop = null; }
    vi.unstubAllGlobals();
  });

  it('tracks pointer spotlight (--mx/--my) and applies 3D tilt on desktop class tiles', () => {
    document.body.innerHTML = '<div class="cls9"><a href="#/talent?c=warrior">战士</a></div>';
    const tile = document.querySelector('.cls9 > a');
    tile.getBoundingClientRect = () => ({ left: 100, top: 200, width: 120, height: 100 });

    stop = initForgeFx();
    const ev = new Event('pointermove', { bubbles: true });
    Object.defineProperty(ev, 'clientX', { value: 190 });
    Object.defineProperty(ev, 'clientY', { value: 225 });
    tile.dispatchEvent(ev);

    expect(tile.style.getPropertyValue('--mx')).toBe('90px');
    expect(tile.style.getPropertyValue('--my')).toBe('25px');
    expect(tile.style.transform).toContain('perspective(660px)');
    expect(tile.style.transform).toContain('rotateX(');
  });

  it('focuses #gs on Ctrl+K and ignores / while typing inside an input', () => {
    document.body.innerHTML = '<input id="gs" type="search"><input id="other" type="text">';
    const gs = document.getElementById('gs');
    const other = document.getElementById('other');
    stop = initForgeFx();

    other.focus();
    other.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }));
    expect(document.activeElement).toBe(other);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true }));
    expect(document.activeElement).toBe(gs);
  });

  it('mounts ForgeEmbers cleanly as aria-hidden canvas without throwing when canvas context is unavailable', () => {
    const w = mount(ForgeEmbers, { props: { count: 20 } });
    const canvas = w.find('canvas.forge-embers');
    expect(canvas.exists()).toBe(true);
    expect(canvas.attributes('aria-hidden')).toBe('true');
    w.unmount();
  });

  it('toggles forge-fx-off cleanly and persists user choice without breaking under OS reduced-motion', () => {
    expect(isForgeFxOff()).toBe(false);
    expect(toggleForgeFx()).toBe(false);
    expect(isForgeFxOff()).toBe(true);
    expect(document.documentElement.classList.contains('forge-fx-off')).toBe(true);

    // Turning off disables 3D tilt even on desktop fine pointer
    document.body.innerHTML = '<div class="cls9"><a href="#/talent?c=warrior">战士</a></div>';
    const tile = document.querySelector('.cls9 > a');
    tile.getBoundingClientRect = () => ({ left: 0, top: 0, width: 120, height: 100 });
    stop = initForgeFx();
    const ev = new Event('pointermove', { bubbles: true });
    Object.defineProperty(ev, 'clientX', { value: 80 });
    Object.defineProperty(ev, 'clientY', { value: 30 });
    tile.dispatchEvent(ev);
    expect(tile.style.transform).toBe('');

    // Re-enabling restores normal state
    setForgeFxOff(false);
    expect(isForgeFxOff()).toBe(false);
    expect(document.documentElement.classList.contains('forge-fx-off')).toBe(false);
  });
});
