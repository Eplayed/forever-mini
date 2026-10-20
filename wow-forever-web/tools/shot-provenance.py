#!/usr/bin/env python3
# I02 溯源页那段"插件目录转存的素材"名单的实拍（桌面 + 375）。
# 为什么单独拍：site-check 的 race_icon 那节只断言文字在不在，看不出这段被谁盖住、
# 在手机上排成什么样——这段是新增内容，必须有一张人眼能看的图。
import os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "screenshots", "check-2026-10-20")
BASE = os.environ.get("APP_BASE", "http://127.0.0.1:8821")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    for tag, w, h in (("d", 1440, 1000), ("m", 375, 812)):
        ctx = b.new_context(viewport={"width": w, "height": h},
                            is_mobile=(tag == "m"), has_touch=(tag == "m"))
        pg = ctx.new_page()
        pg.goto(BASE + "/#/provenance", wait_until="networkidle")
        pg.wait_for_timeout(2500)
        # 滚到那张卡片，让它进视口（不滚就在页尾，截出来是一屏别的）
        pg.evaluate("""() => {
          const el = [...document.querySelectorAll('h3')].find(h =>
            (h.innerText || '').indexOf('插件目录转存的素材') >= 0);
          if (el) el.scrollIntoView({block: 'start'});
          window.scrollBy(0, -90);
          return !!el; }""")
        pg.wait_for_timeout(600)
        n = pg.evaluate("""() => {
          const t = document.body.innerText || '';
          return { blk: t.indexOf('插件目录转存的素材') >= 0,
                   over: document.documentElement.scrollWidth - window.innerWidth }; }""")
        name = "app-provenance-addon-art%s.png" % ("-m" if tag == "m" else "")
        pg.screenshot(path=os.path.join(OUT, name))
        print("%s → %s  段落在 %s / 横向溢出 %spx" % (name, BASE, n["blk"], n["over"]))
        ctx.close()
    b.close()
