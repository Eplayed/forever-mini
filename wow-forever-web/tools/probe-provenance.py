# -*- coding: utf-8 -*-
"""一次性探针：看溯源页现在到底渲染出哪些徽标/来源/轨/覆盖率元素。只读。"""
import sys
from playwright.sync_api import sync_playwright

Q = """() => ({
  pill: document.querySelectorAll('#main .pill').length,
  cov: document.querySelectorAll('#main .cov').length,
  covI: document.querySelectorAll('#main .cov i').length,
  stats: document.querySelectorAll('#main .stats .stat').length,
  statB: [...document.querySelectorAll('#main .stats .stat')].map(e => e.innerText.replace(/\\s+/g,' ')).slice(0,6),
  srcUl: document.querySelectorAll('#main ul.src').length,
  srcLi: document.querySelectorAll('#main .src li').length,
  srcP: document.querySelectorAll('#main p.src').length,
  st: document.querySelectorAll('#main .st').length,
  rail: document.querySelectorAll('#main .rail').length,
  dataLv: [...document.querySelectorAll('#main [data-lv]')].map(e => e.dataset.lv),
  steps: document.querySelectorAll('#main .step').length,
  head: document.querySelector('#main').innerText.slice(0, 120).replace(/\\n/g, ' | ')
})"""


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8817"
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        pg.goto(base + "/provenance.html", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        import json
        print(json.dumps(pg.evaluate(Q), ensure_ascii=False, indent=1))
        b.close()


if __name__ == "__main__":
    main()
