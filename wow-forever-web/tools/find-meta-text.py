# -*- coding: utf-8 -*-
"""一次性探针：把 17 个旧站页面里剩下的"讲我们自己数据过程"的句子揪出来，按行报页码与上下文。
   只读，不改任何文件。跑法：python3 tools/find-meta-text.py"""
import os
import re
import sys
from playwright.sync_api import sync_playwright

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
PAGES = [f[:-5] for f in sorted(os.listdir(SRC)) if f.endswith(".html") and f != "index.html"]
WORDS = ["本站", "不复制", "不机翻", "不猜", "不编", "转述", "解包", "来源", "核对", "口径",
         "逐条", "红线", "示意图", "本地转存", "非游戏原画", "第三方", "官方中文稿", "待补",
         "客户端给的", "已核", "数据基线", "覆盖率"]
PAT = re.compile("|".join(re.escape(w) for w in WORDS))


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8817"
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 1000})
        for name in PAGES:
            page = ctx.new_page()
            page.goto("%s/%s.html" % (base, name), wait_until="networkidle")
            page.wait_for_timeout(1400)
            txt = page.evaluate("() => document.querySelector('#main').innerText")
            hits = [ln.strip() for ln in txt.split("\n") if PAT.search(ln)]
            print("\n### %s  (%d 行)" % (name, len(hits)))
            for h in hits[:14]:
                print("   " + h[:150])
            if len(hits) > 14:
                print("   … 还有 %d 行" % (len(hits) - 14))
            page.close()
        ctx.close()
        b.close()


if __name__ == "__main__":
    main()
