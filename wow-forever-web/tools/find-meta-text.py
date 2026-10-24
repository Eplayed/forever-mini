# -*- coding: utf-8 -*-
"""探针：把页面上剩下的"讲我们自己数据过程"的句子揪出来，按行报页与上下文。
   只读，不改任何文件。2026-10-24 起打的是新站那 21 条路由（旧站已删）。
   跑法：先 cd app && npm run build && npx vite preview --port 8821，
        再 python3 tools/find-meta-text.py"""
import os
import re
import sys
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_router = open(os.path.join(ROOT, "app", "src", "router.js"), encoding="utf-8").read()
_block = re.search(r"const routes = \[(.*?)\n\];", _router, re.S).group(1)
PAGES = [pth for pth in re.findall(r"\{\s*path:\s*'([^']+)'", _block) if ":all" not in pth]
WORDS = ["本站", "不复制", "不机翻", "不猜", "不编", "转述", "解包", "来源", "核对", "口径",
         "逐条", "红线", "示意图", "本地转存", "非游戏原画", "第三方", "官方中文稿", "待补",
         "客户端给的", "已核", "数据基线", "覆盖率"]
PAT = re.compile("|".join(re.escape(w) for w in WORDS))


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8821"
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 1000})
        for name in PAGES:
            page = ctx.new_page()
            page.goto("%s/#%s" % (base, name), wait_until="networkidle")
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
