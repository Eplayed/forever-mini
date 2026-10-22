#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成小程序 tabBar 的六个图标（首页 / 副本 / 职业 × 普通态与选中态）。

为什么自绘：tabBar 图标必须是打进主包的本地文件（微信不吃网络地址），
而游戏图标与官方素材都不该出现在我们自己的导航条上——所以这一组按本站设计令牌自绘，
不抄任何第三方素材。删除 for-mini/img/tabbar/ 整个目录并把 app.json 里那六行撤掉，
即回退到"只有文字"的 tab（现在的样子）。

颜色不抄第二份：两个色直接从 for-mini/app.wxss 的令牌里读（--txt-muted 与 --gold-hot），
令牌改了重跑本脚本即可，图标不会跟主题对不上。

跑法：python3 wow-forever-web/tools/gen-tabbar-icons.py
"""
import os
import re
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WXSS = os.path.join(ROOT, "for-mini", "app.wxss")
OUT = os.path.join(ROOT, "for-mini", "img", "tabbar")

# 微信建议 81x81；按 4 倍画再缩小，边缘才不会锯齿
SIZE = 81
SS = 4
CANVAS = SIZE * SS
STROKE = 7 * SS


def token(name):
    with open(WXSS, "r", encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"--%s:\s*(#[0-9a-fA-F]{3,8});" % re.escape(name), text)
    if not m:
        sys.exit("✗ app.wxss 里找不到令牌 --%s，图标不许自己编颜色" % name)
    return m.group(1)


def canvas():
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def save(img, name):
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    img.save(os.path.join(OUT, name + ".png"), optimize=True)
    return os.path.getsize(os.path.join(OUT, name + ".png"))


def home(img, d, c):
    """房子：屋顶三角 + 房身，中间留一道门缝。"""
    w = STROKE
    d.line([(CANVAS * 0.12, CANVAS * 0.46), (CANVAS * 0.5, CANVAS * 0.13), (CANVAS * 0.88, CANVAS * 0.46)],
           fill=c, width=w, joint="curve")
    d.rectangle([CANVAS * 0.22, CANVAS * 0.46, CANVAS * 0.78, CANVAS * 0.86], outline=c, width=w)
    d.rectangle([CANVAS * 0.42, CANVAS * 0.63, CANVAS * 0.58, CANVAS * 0.86], fill=c)


def dungeon(img, d, c):
    """副本：一座拱门（外框圆顶 + 里面一道暗门洞）。"""
    w = STROKE
    box = [CANVAS * 0.2, CANVAS * 0.16, CANVAS * 0.8, CANVAS * 0.86]
    d.rounded_rectangle(box, radius=CANVAS * 0.3, outline=c, width=w)
    inner = [CANVAS * 0.38, CANVAS * 0.42, CANVAS * 0.62, CANVAS * 0.86]
    d.rounded_rectangle(inner, radius=CANVAS * 0.12, fill=c)


def classes(img, d, c):
    """职业：一面盾牌（上宽下尖，中间一道脊）。"""
    w = STROKE
    pts = [
        (CANVAS * 0.5, CANVAS * 0.12),
        (CANVAS * 0.84, CANVAS * 0.24),
        (CANVAS * 0.84, CANVAS * 0.52),
        (CANVAS * 0.5, CANVAS * 0.88),
        (CANVAS * 0.16, CANVAS * 0.52),
        (CANVAS * 0.16, CANVAS * 0.24),
    ]
    d.polygon(pts, outline=c, width=w)
    d.line([(CANVAS * 0.5, CANVAS * 0.2), (CANVAS * 0.5, CANVAS * 0.76)], fill=c, width=w // 2)


SHAPES = {"home": home, "dungeons": dungeon, "classes": classes}
TABS = [("home", "首页"), ("dungeons", "副本"), ("classes", "职业")]


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    idle = token("txt-muted")
    on = token("gold-hot")
    sizes = []
    for key, label in TABS:
        for state, color in (("idle", idle), ("on", on)):
            img, d = canvas()
            SHAPES[key](img, d, color)
            sizes.append((("%s-%s" % (key, state)), label, color, save(img, "%s-%s" % (key, state))))
    print("生成 %d 张 → for-mini/img/tabbar/（普通态 %s / 选中态 %s，两色都读自 app.wxss 令牌）"
          % (len(sizes), idle, on))
    for name, label, color, b in sizes:
        print("  %s.png  %-6s %s  %d B" % (name, label, color, b))
    big = [s for s in sizes if s[3] > 40 * 1024]
    if big:
        sys.exit("✗ 有图标超过微信单张 40KB 上限：" + ", ".join(x[0] for x in big))


if __name__ == "__main__":
    main()
