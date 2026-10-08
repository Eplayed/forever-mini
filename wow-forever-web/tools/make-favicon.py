#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成站点头标（自绘几何图形，不含任何外部素材与商标元素）。

产出三个文件：
  src/img/favicon.svg            矢量头标（现代浏览器）
  src/favicon.ico                兜底 ico（放在站点根，浏览器默认去根目录要它）
  src/apple-touch-icon.png       iOS 主屏图标
改图形只改本文件，重跑即可复现：python3 tools/make-favicon.py
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
IMG = os.path.join(SRC, "img")

BG = "#0e1013"
PANEL = "#171a1f"
GOLD = "#e0a96d"
SLATE = "#7f8ea8"
LINE = "#2b3038"
S = 512


def layout():
    """三系并列的节点：中间一系实心金（已加点），两侧描边（未点）。"""
    cols = [S * 0.25, S * 0.5, S * 0.75]
    rows = [S * (0.24 + 0.17 * i) for i in range(4)]
    return cols, rows, [(x, y, ci == 1) for ci, x in enumerate(cols) for y in rows]


def draw(img):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, S, S], radius=96, fill=BG)
    d.rounded_rectangle([S * 0.09, S * 0.09, S * 0.91, S * 0.91], radius=67, outline=LINE, width=6)
    cols, rows, pts = layout()
    r = int(S * 0.062)
    for x in cols:
        d.line([(x, rows[0]), (x, rows[-1])], fill=LINE, width=8)
    for y in rows[1:]:
        d.line([(cols[0], y), (cols[2], y)], fill=LINE, width=6)
    for x, y, filled in pts:
        if filled:
            d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD)
            d.ellipse([x - r - 12, y - r - 12, x + r + 12, y + r + 12], outline=GOLD, width=6)
        else:
            d.ellipse([x - r, y - r, x + r, y + r], fill=PANEL, outline=SLATE, width=7)
    return img


def svg_text():
    cols, rows, pts = layout()
    r = S * 0.062
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" role="img" aria-label="无限资料站标记：三系天赋节点">' % (S, S)]
    out.append('<rect width="%d" height="%d" rx="96" fill="%s"/>' % (S, S, BG))
    out.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="67" fill="none" stroke="%s" stroke-width="6"/>'
               % (S * .09, S * .09, S * .82, S * .82, LINE))
    for x in cols:
        out.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" stroke-width="8"/>' % (x, rows[0], x, rows[-1], LINE))
    for y in rows[1:]:
        out.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" stroke-width="6"/>' % (cols[0], y, cols[2], y, LINE))
    for x, y, filled in pts:
        out.append('<circle cx="%.0f" cy="%.0f" r="%.0f" fill="%s"/>' % (x, y, r, GOLD) if filled
                   else '<circle cx="%.0f" cy="%.0f" r="%.0f" fill="%s" stroke="%s" stroke-width="7"/>' % (x, y, r, PANEL, SLATE))
        if filled:
            out.append('<circle cx="%.0f" cy="%.0f" r="%.0f" fill="none" stroke="%s" stroke-width="6"/>' % (x, y, r + 12, GOLD))
    out.append('</svg>')
    return "\n".join(out)


def main():
    with open(os.path.join(IMG, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(svg_text())
    base = draw(Image.new("RGBA", (S, S), (0, 0, 0, 0)))
    base.save(os.path.join(SRC, "apple-touch-icon.png"))
    base.save(os.path.join(SRC, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    for path in (os.path.join(IMG, "favicon.svg"), os.path.join(SRC, "apple-touch-icon.png"), os.path.join(SRC, "favicon.ico")):
        print("  %-28s %d B" % (os.path.relpath(path, ROOT), os.path.getsize(path)))


if __name__ == "__main__":
    main()
