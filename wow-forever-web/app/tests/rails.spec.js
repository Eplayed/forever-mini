import { describe, it, expect } from 'vitest';
import { applyRails, levelOfCard } from '../src/lib/rails.js';

/* 来源轨的规则只在页面已渲染出的事实上做推断：分级徽标 + 来源类型标签。
   这些用例锁住三件事：取最弱的一级、本站说明不算数据声明、显式定级的卡不被重新推断。 */
function html(inner) {
  document.body.innerHTML = `<div id="main">${inner}</div>`;
  return document.getElementById('main');
}

describe('rails 来源轨', () => {
  it('徽标里取最弱的那一级，不按出现顺序', () => {
    const root = html('<div class="card"><span class="pill L0">已官方核实</span>' +
      '<span class="pill L2">待实测</span></div>');
    expect(levelOfCard(root.querySelector('.card'))).toBe('L2');
    applyRails(root);
    const c = root.querySelector('.card');
    expect(c.classList.contains('rail')).toBe(true);
    expect(c.dataset.lv).toBe('L2');
  });

  it('来源类型按既定口径映射（官方中文 L0、第三方转述 L2）', () => {
    const root = html('<div class="card"><ul class="src"><li><span class="st official_cn">官方中文</span></li></ul></div>');
    expect(levelOfCard(root.querySelector('.card'))).toBe('L0');
    const root2 = html('<div class="card"><ul class="src"><li><span class="st fan_db">第三方资料站</span></li></ul></div>');
    expect(levelOfCard(root2.querySelector('.card'))).toBe('L2');
  });

  it('「本站说明」不是数据来源，不给轨', () => {
    const root = html('<div class="card"><ul class="src"><li><span class="st site-note">本站说明</span></li></ul></div>');
    expect(levelOfCard(root.querySelector('.card'))).toBe(null);
    expect(applyRails(root)).toBe(0);
  });

  it('既无徽标也无来源的卡不上轨（没定级就别装作定了级）', () => {
    const root = html('<div class="card"><h2>选职业问答</h2></div>');
    expect(applyRails(root)).toBe(0);
    expect(root.querySelector('.card').classList.contains('rail')).toBe(false);
  });

  it('渲染时已显式定级的卡只补类，不重新推断', () => {
    const root = html('<div class="card" data-lv="L3"><span class="pill L0">已官方核实</span></div>');
    applyRails(root);
    expect(root.querySelector('.card').dataset.lv).toBe('L3');
    expect(root.querySelector('.card').classList.contains('rail')).toBe(true);
  });

  it('重复调用无副作用（观察者会反复触发）', () => {
    const root = html('<div class="card"><span class="pill L1">仅官方英文</span></div>');
    applyRails(root);
    const first = root.querySelector('.card').className;
    applyRails(root);
    expect(root.querySelector('.card').className).toBe(first);
  });
});
