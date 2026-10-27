#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把自生成的氛围底图裁掉右下角的 AI 水印、转 webp、落进 app/img/gen/ 并写 manifest。

为什么自己生成而不抄稿子：设计稿 brief 第八节写着"AI 生图均为无字底图"，
但实际那三张 assets/changjing/*.webp 是**游戏内截图**（能看见角色模型与引擎贴图的边缘），
来源不可考，不满足我们"素材必须记来源、整目录可下线"的口径，所以一张都没搬。
"""
import datetime
import hashlib
import io
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_IMG = os.path.join(ROOT, "app", "img")
OUT = os.path.join(SRC_IMG, "gen")
VIBE = os.path.join(os.path.dirname(ROOT), "vibe_images")

# 生成图 → 入库名（裁掉底部 128px 的"Qoder AI 生成"角标）
JOBS = [
    ("gen-hero-canyuan_1791783589886_1b30c05d.png", "hero-ruins.webp",
     "首页 hero：远山废墟 + 铜金落日，左半留暗部放标题与搜索框", 128),
    ("gen-banner-yunhai_1791783632813_950d07ad.png", "banner-cloudsea.webp",
     "内页通用 banner：云海与远处塔尖剪影，一条微弱金色天光", 130),
    ("gen-dungeon-cavern_1791783664131_51a6e96a.png", "cavern-hall.webp",
     "地下城/团本氛围：石柱大厅 + 远处火光与地缝金光", 128),
    ("gen-prof-table_1793083766003_983bc2b6.png", "prof-table.webp",
     "专业与配方入口卡：右侧药剂与锻造工具台面，左半留暗部放标题", 128),
]

PROMPT = ("按设计稿 brief 第八节的规格自生成（史诗奇幻 × 暗黑金属，暗蓝炭黑底 + 铜金边光，"
          "无字、无 UI、无角色，一侧留大面积低纹理暗部承载文字）")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    mp = os.path.join(OUT, "manifest.json")
    man = json.load(io.open(mp, encoding="utf-8")) if os.path.exists(mp) else {
        "note": "本站自生成的氛围底图（AI），不是游戏原画也不是第三方站图片。"
                "整目录删除即回退到 CSS 渐变底 + 自绘横幅。",
        "kind": "generated-atmosphere",
        "items": []}
    for fname, outname, what, crop in JOBS:
        src = os.path.join(VIBE, fname)
        if not os.path.exists(src):
            print(u"找不到生成图 %s，跳过" % fname)
            continue
        im = Image.open(src).convert("RGB")
        w, h = im.size
        im = im.crop((0, 0, w, h - crop))          # 去掉右下角水印那一条
        dst = os.path.join(OUT, outname)
        im.save(dst, "WEBP", quality=82, method=6)
        blob = open(dst, "rb").read()
        rec = {"file": "gen/" + outname, "bytes": len(blob),
               "sha1": hashlib.sha1(blob).hexdigest()[:10],
               "size": "%dx%d" % im.size, "kind": "atmosphere", "what": what,
               "generatedBy": "Qoder ImageGen（本站自生成，提示词见 brief 第八节）",
               "source": "prompt: " + PROMPT,
               "processed": u"裁掉底部 %dpx：出图右下角带「Qoder AI 生成」角标，不裁会糊在页面上" % crop,
               "fetchedAt": datetime.date.today().isoformat()}
        man["items"] = [x for x in man["items"] if x["file"] != rec["file"]] + [rec]
        print(u"%-22s %s %d KB → %s" % (outname, rec["size"], len(blob) // 1024,
                                        os.path.relpath(dst, ROOT)))
    io.open(mp, "w", encoding="utf-8").write(json.dumps(man, ensure_ascii=False, indent=1) + "\n")
    print(u"manifest %d 条 → %s" % (len(man["items"]), os.path.relpath(mp, ROOT)))
    write_art_index(man)


def write_art_index(man):
    """把这三张底图并进界面索引 art.json 的 gen 键。

    为什么要进 art.json：build-data.js 会逐个检查这份索引指向的文件真的在仓库里，
    界面里的 SEC_ART / RAID_ART 常量表也被断言要求能在清单里找到——不进这里就是野素材。
    """
    ap = os.path.join(ROOT, "app", "data", "art.json")
    art = json.load(io.open(ap, encoding="utf-8")) if os.path.exists(ap) else {}
    idx = {}
    for x in man["items"]:
        rel = x["file"] if x["file"].startswith("gen/") else "gen/" + x["file"].split("/")[-1]
        idx[os.path.splitext(os.path.basename(rel))[0]] = "img/" + rel
    art["gen"] = idx
    io.open(ap, "w", encoding="utf-8").write(json.dumps(art, ensure_ascii=False, indent=1) + "\n")
    print(u"art.json.gen → %d 张" % len(idx))


if __name__ == "__main__":
    main()
