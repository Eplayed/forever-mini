#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""转存客户端原画（职业天赋背景图、副本载入图）到 app/img/art/，本地留存、不热链。

红线口径：这些是暴雪游戏美术，目前只有第三方站托管的副本（官方 CDN 不提供）。
2026-10-08 用户决策：网页与小程序都用。执行要求是全部落到独立目录 +
art/manifest.json 记来源与抓取日期 + 保留"整目录删除即回退到自绘占位"的下线方案。

用法：
    python3 tools/fetch-art.py --what classes     # 九职业背景图（从参考站首页现取带哈希的文件名）
    python3 tools/fetch-art.py --what dungeons    # 副本载入图（逐个 slug 试两台源）
    python3 tools/fetch-art.py --what maps        # 区域小地图（只下世界线数据引用到的 mapId）
    python3 tools/fetch-art.py --what specbg      # 27 棵专精背景：下四角图拼成整图（要 PIL）
    python3 tools/fetch-art.py --what panels      # 职业横幅 9 张 + 板块图 + 场景图 + 石板纹理
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "app", "img", "art")
DATA = os.path.join(ROOT, "app", "data")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
WCF = "https://wowclassicforever.info"
WBX = "https://wowforever.wclbox.com"
WBX = "https://wowforever.wclbox.com"
# 我们的副本 id → 参考站用的 slug（两边命名不一致的几座）
SLUG_ALIAS = {"whelgars-excavation": "excavation-site-wetlands", "deathmine": "the-deadmines",
              "the-stocks": "the-stockade", "razor-krendor": "razorfen-downs"}


def http(url, binary=False):
    p = subprocess.run(["curl", "-s", "-L", "-m", "30", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True)
    body = p.stdout
    nl = body.rfind(b"\n")
    code = int(body[nl + 1:].strip() or 0) if nl >= 0 else 0
    data = body[:nl]
    return code, (data if binary else data.decode("utf-8", "replace"))


def save(path, blob, url, kind):
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "wb") as fh:
        fh.write(blob)
    return {"file": os.path.relpath(path, os.path.dirname(ART)), "bytes": len(blob),
            "sha1": hashlib.sha1(blob).hexdigest()[:10], "source": url, "kind": kind,
            "fetchedAt": datetime.date.today().isoformat()}


def load_manifest():
    p = os.path.join(ART, "manifest.json")
    if os.path.exists(p):
        return json.load(io.open(p, encoding="utf-8"))
    return {"note": u"客户端原画：暴雪游戏美术，经第三方站转存。整目录删除即可回退到自绘占位图。",
            "items": []}


def save_manifest(man):
    if not os.path.isdir(ART):
        os.makedirs(ART)
    io.open(os.path.join(ART, "manifest.json"), "w", encoding="utf-8").write(
        json.dumps(man, ensure_ascii=False, indent=1) + "\n")


def classes(man):
    code, html = http(WBX + "/")
    if code != 200:
        sys.exit(u"取不到参考站首页（%d）" % code)
    urls = sorted(set(re.findall(r'(/jiemian/custom/classes/([a-z]+)-[0-9a-f]{8,}\.webp)', html)))
    print(u"首页里找到 %d 张职业背景图" % len(urls))
    got = []
    for path, cid in urls:
        url = WBX + path
        code, blob = http(url, binary=True)
        if code == 200 and len(blob) > 2000:
            rec = save(os.path.join(ART, "classes", cid + ".webp"), blob, url, "class-bg")
            man["items"] = [x for x in man["items"] if not x["file"].endswith(cid + ".webp")] + [rec]
            got.append(cid)
        else:
            print(u"  取不到 %s（%d）" % (cid, code))
    print(u"已存职业背景图 %d：%s" % (len(got), u"、".join(got)))


def card_art_map():
    """无限数据库的副本卡片里带载入图路径，键是它的 slug。"""
    p = os.path.join(DATA, "upstream", "wclbox-cards.json")
    if not os.path.exists(p):
        return {}
    doc = json.load(io.open(p, encoding="utf-8"))
    return {c["slug"]: c.get("art") for c in doc.get("cards") or [] if c.get("art")}


def dungeons(man):
    dg = json.load(io.open(os.path.join(DATA, "dungeons.json"), encoding="utf-8"))
    rows = []
    for key in ("newDungeons", "classicDungeons", "raids"):
        rows += dg.get(key) or []
    have = set(x["file"].split("/")[-1].split(".")[0] for x in man["items"] if "/dungeons/" in x["file"])
    arts = card_art_map()
    ok, miss = [], []
    for d in rows:
        slug = SLUG_ALIAS.get(d["id"], d["id"])
        if d["id"] in have:
            continue
        cands = ([WBX + arts[slug]] if slug in arts else []) + [
            WCF + "/images/dungeons/client/%s/loading-screen-640.webp" % slug,
            WCF + "/images/dungeons/client/%s/loading-screen-640.png" % slug]
        for url in cands:
            code, blob = http(url, binary=True)
            if code == 200 and len(blob) > 3000 and blob[:4] != b"<":
                ext = "webp" if blob[8:12] == b"WEBP" else ("png" if blob[:4] == b"\x89PNG" else "jpg")
                rec = save(os.path.join(ART, "dungeons", d["id"] + "." + ext), blob, url, "dungeon-loading")
                man["items"].append(rec)
                ok.append(d["id"])
                break
        else:
            miss.append(d["id"])
    print(u"副本载入图：新增 %d，取不到 %d（继续用自绘横幅）" % (len(ok), len(miss)))
    if miss:
        print(u"  缺：%s" % u"、".join(miss[:20]))


def zone_map_ids():
    """要用的小地图 id：稀有精英/书籍/营地引用的那张，加上区域表里每个区域自己那张。"""
    p = os.path.join(DATA, "upstream", "wclbox-world.json")
    if not os.path.exists(p):
        sys.exit(u"先跑 tools/scrape-wclbox-shuju.py 抓世界线数据包，才知道要下哪些小地图")
    d = json.load(io.open(p, encoding="utf-8")).get("payload") or {}
    out = {}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and v.startswith("/ditu-xiao/"):
                    m = re.search(r"/ditu-xiao/(\d+)\.", v)
                    if m:
                        out[m.group(1)] = v
                else:
                    walk(v)
        elif isinstance(o, list):
            for i in o:
                walk(i)
    walk(d)
    # 区域表里每个区域都有自己那张图，id 写在大陆地图的 paint 上（areaId → 文件名）
    zones = d.get("zones") or {}
    byslug = {m.get("slug"): m for m in d.get("maps") or []}
    for slug, rows in zones.items():
        paint = {x.get("areaId"): x.get("file") for x in (byslug.get(slug) or {}).get("paint") or []
                 if x.get("areaId") is not None and x.get("file")}
        for z in rows or []:
            f = paint.get(z.get("area"))
            if f:
                out[str(f).split(".")[0]] = "/ditu-xiao/%s" % f
    return out


def maps(man):
    """区域小地图：560×373 的客户端地图渲染，托管在第三方站（官方 CDN 不提供这个尺寸）。
    口径与副本载入图一致——只转存我们数据里真引用到的 id，整目录删除即回退到坐标文字。"""
    want = zone_map_ids()
    have = set(os.path.basename(x["file"]).split(".")[0] for x in man["items"] if "/maps/" in x["file"])
    ok, miss = [], []
    for mid, path in sorted(want.items()):
        if mid in have:
            continue
        url = WBX + path
        code, blob = http(url, binary=True)
        if code == 200 and len(blob) > 2000 and blob[:4] == b"RIFF":
            rec = save(os.path.join(ART, "maps", mid + ".webp"), blob, url, "zone-map")
            man["items"] = [x for x in man["items"]
                            if not (x["kind"] == "zone-map" and os.path.basename(x["file"]).split(".")[0] == mid)]
            man["items"].append(rec)
            ok.append(mid)
        else:
            miss.append(mid)
            print(u"  取不到小地图 %s（%d）" % (mid, code))
    print(u"区域小地图：需要 %d 张，本轮新增 %d，取不到 %d" % (len(want), len(ok), len(miss)))


# 参考站种族页的文件名 → 我们的种族 id。只有两处对不上（nightelf / skyborne），其余同名；
# 天裔两个子族共用这一张头像，与参考站一致，不另找图凑。
RACE_FILE = {"human": "human", "dwarf": "dwarf", "nightelf": "night-elf", "gnome": "gnome",
             "orc": "orc", "undead": "undead", "tauren": "tauren", "troll": "troll",
             "skyborne": "skyborne"}


def races(man):
    """种族头像与阵营徽标：128×128 的客户端头像，官方 CDN 不提供，只能转存第三方副本。

    口径与职业背景图、副本载入图完全一致：落独立目录 + manifest 记来源与抓取日期 +
    整目录删除即回退到自绘方块。文件名里的哈希（天裔那张）会变，所以每次都从种族页现读。
    """
    code, html = http(WBX + "/zhongzu")
    if code != 200:
        sys.exit(u"取不到参考站种族页（%d）" % code)
    found = sorted(set(re.findall(r'(/jiemian/(?:reference-art|custom)/(?:raceicon|faction)-[\w.-]+\.(?:webp|png))', html)))
    print(u"种族页里找到 %d 张头像/徽标" % len(found))
    ok, miss = [], []
    for path in found:
        name = os.path.basename(path)
        m = re.match(r"raceicon-([a-z]+)(?:-[0-9a-f]{6,})?\.(webp|png)$", name)
        f = re.match(r"faction-([a-z]+)\.(png|webp)$", name)
        if m:
            key = RACE_FILE.get(m.group(1))
            if not key:
                miss.append(name + u"（对不上我们的种族 id）")
                continue
            kind, dest, ext = "race-portrait", os.path.join(ART, "races", key + "." + m.group(2)), m.group(2)
        elif f:
            kind, dest, ext = "faction-emblem", os.path.join(ART, "factions", f.group(1) + "." + f.group(2)), f.group(2)
        else:
            continue
        code, blob = http(WBX + path, binary=True)
        if code != 200 or len(blob) < 800:
            miss.append(name)
            continue
        rec = save(dest, blob, WBX + path, kind)
        man["items"] = [x for x in man["items"] if x["file"] != rec["file"]] + [rec]
        ok.append(rec["file"])
    print(u"种族头像/徽标：新增或更新 %d，取不到 %d" % (len(ok), len(miss)))
    if miss:
        print(u"  缺：%s" % u"、".join(miss[:10]))


# 阵营城市背景：参考站按拼音命名（lianmeng=联盟=暴风城英雄谷，buluo=部落=奥格瑞玛正门），
# 两张都人眼确认过画的是什么，不是靠文件名猜。落到我们自己的语义名，来源记进 manifest。
CITY_FILE = {"lianmeng": ("alliance", u"暴风城英雄谷"), "buluo": ("horde", u"奥格瑞玛正门")}


def factions(man):
    """阵营城市背景原画：种族页两条阵营带要用它做底，压暗后当氛围图。

    口径与职业背景图一致：第三方站托管的客户端原画副本，落独立目录 + manifest 记来源与抓取日期，
    整目录删掉即回退到现在的纯色带。取不到就跳过，不放别的图凑数。
    """
    ok, miss = [], []
    for src, (key, what) in CITY_FILE.items():
        url = WBX + "/peitu/changjing/" + src + ".webp"
        code, blob = http(url, binary=True)
        if code != 200 or len(blob) < 8000:
            miss.append(src + u"（HTTP %s）" % code)
            continue
        dest = os.path.join(ART, "factions", "city-" + key + ".webp")
        rec = save(dest, blob, url, "faction-city")
        rec["what"] = what
        man["items"] = [x for x in man["items"] if x["file"] != rec["file"]] + [rec]
        ok.append(u"%s → %s（%s，%d KB）" % (src, rec["file"], what, len(blob) // 1024))
    print(u"阵营城市背景：新增或更新 %d，取不到 %d" % (len(ok), len(miss)))
    for x in ok:
        print(u"  " + x)
    if miss:
        print(u"  缺：%s" % u"、".join(miss))


def boss_rows():
    """dungeons.json 里的全部首领：[(本 id, 首领 id, 首领中文名)]，按出现顺序。"""
    dg = json.load(io.open(os.path.join(DATA, "dungeons.json"), encoding="utf-8"))
    rows = []
    for key in ("newDungeons", "classicDungeons", "raids"):
        for d in dg.get(key) or []:
            for b in d.get("bosses") or []:
                rows.append((d["id"], b["id"], b.get("nameCn")))
    return rows


def boss_face_map():
    """从 DOM 抓回来的首领头像路径表：键是"去掉连字符小写"的首领键，值是该页真实读到的路径。

    为什么不能自己拼：源站的头像文件名是它自己那套首领键（rhahkzor），与我们 dungeons.json
    里的 id（rhahk-zor）不同名，猜出来的地址会大面积 404——那是我们的错，不是源站缺。
    """
    p = os.path.join(DATA, "upstream", "wclbox-boss-faces.json")
    if not os.path.exists(p):
        sys.exit(u"先跑 tools/scrape-wclbox-dom.py --what bossfaces，才有头像路径可对")
    doc = json.load(io.open(p, encoding="utf-8"))
    norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
    out, allkeys = {}, {}
    for f in doc.get("faces") or []:
        k = norm(f.get("bossKey"))
        if not k:
            continue
        allkeys[k] = f
        if f.get("face"):
            out[k] = f
    return out, allkeys


def bosses(man, probe_only=False):
    """首领头像：客户端遭遇战手册里的方头像，托管在第三方站（官方 CDN 不提供）。

    这不是图标而是暴雪的游戏美术，与副本载入图同一类，所以走同一套口径——
    落独立目录 art/bosses/ + manifest 记来源与抓取日期 + 整目录删除即回退到自绘方块。
    无限新增的首领（如领主大厅那四位）源站自己也标着 data-unknown，我们这边同样拿不到，
    一律留空不猜图、不拿别的种族的脸凑。
    """
    rows = boss_rows()
    faces, allkeys = boss_face_map()
    have = set(os.path.basename(x["file"]).split(".")[0]
               for x in man["items"] if "/bosses/" in x["file"])
    ok, miss, nomatch = [], [], []
    for dun_id, bid, name in rows:
        key = re.sub(r"[^a-z0-9]", "", bid.lower())
        f = faces.get(key)
        if not f:
            if key in allkeys:
                miss.append(bid)
            else:
                nomatch.append(bid)
            continue
        if bid in have:
            continue
        url = WBX + f["face"]
        if probe_only:
            code, blob = http(url, binary=True)
            (ok if code == 200 and blob[8:12] == b"WEBP" else miss).append(bid)
            continue
        code, blob = http(url, binary=True)
        if code == 200 and len(blob) > 400 and blob[8:12] == b"WEBP":
            rec = save(os.path.join(ART, "bosses", bid + ".webp"), blob, url, "boss-portrait")
            rec["dungeon"] = dun_id
            man["items"] = [x for x in man["items"]
                            if not (x["kind"] == "boss-portrait"
                                    and os.path.basename(x["file"]).split(".")[0] == bid)]
            man["items"].append(rec)
            ok.append(bid)
        else:
            miss.append(bid + u"（HTTP %s）" % code)
    print(u"首领头像：首领共 %d ｜ 源站有脸且已下盘 %d ｜ 源站标了没有 %d ｜ 源站页面上没这一节 %d" % (
        len(rows), len(ok) + len(have), len(miss), len(nomatch)))
    if miss:
        print(u"  源站没有这张脸：%s" % u"、".join([str(x) for x in miss[:16]]))
    if nomatch:
        print(u"  名字对不上（不猜）：%s" % u"、".join(nomatch[:16]))


# ---------------------------------------------------------------------------
# 专精背景图与板块配图（2026-10-13 用户实拍："卡片背景要的是图片，不是把图标当背景拉伸"）
# ---------------------------------------------------------------------------
# 27 棵天赋树的英文键名是从参考站天赋页 DOM 现挖的（文件名规律 tianfu-beijing/<Class><Tree>-<角>.webp，
# 每系四张角图：TopLeft / TopRight / BottomLeft / BottomRight）。括号里是我们
# app/data/talents/<职业>.json 里那一系的 nameCn——下载前逐条回对，对不上就停，不靠位置猜。
# 为什么必须回对：无限服改过系名，术士三系的键是 Curses / Summoning / Destruction，
# 萨满第一系叫 ElementalCombat，都不按经典旧世的规矩来。
SPEC_TREES = {
    "warrior": [("WarriorArms", u"武器"), ("WarriorFury", u"狂怒"), ("WarriorProtection", u"防护")],
    "paladin": [("PALADINHOLY", u"神圣"), ("PALADINPROTECTION", u"防护"), ("PALADINCOMBAT", u"惩戒")],
    "hunter": [("HunterBeastMastery", u"野兽控制"), ("HunterMarksmanship", u"射击"), ("HunterSurvival", u"生存")],
    "rogue": [("RogueAssassination", u"奇袭"), ("RogueCombat", u"战斗"), ("RogueSubtlety", u"敏锐")],
    "priest": [("PriestDiscipline", u"戒律"), ("PriestHoly", u"神圣"), ("PriestShadow", u"暗影")],
    "shaman": [("ShamanElementalCombat", u"元素战斗"), ("ShamanEnhancement", u"增强"),
               ("ShamanRestoration", u"恢复")],
    "mage": [("MageArcane", u"奥术"), ("MageFire", u"火焰"), ("MageFrost", u"冰霜")],
    "warlock": [("WarlockCurses", u"痛苦"), ("WarlockSummoning", u"恶魔学识"),
                ("WarlockDestruction", u"毁灭")],
    "druid": [("DruidBalance", u"平衡"), ("DruidFeralCombat", u"野性战斗"), ("DruidRestoration", u"恢复")],
}
# 第二台源（jjwow）的键名：只有圣骑士三家写法不同（它全用驼峰），其余同名。
# 为什么要两台：wclbox 自己页面上圣骑士那 12 张角图就是坏的（浏览器实测 naturalWidth=0、直接请求 404）。
JJ_KEY = {"PALADINHOLY": "PaladinHoly", "PALADINPROTECTION": "PaladinProtection",
          "PALADINCOMBAT": "PaladinCombat"}
JJ = "https://jjwow.cn"

CORNERS = ["TopLeft", "TopRight", "BottomLeft", "BottomRight"]

# 板块入口卡的配图：职业横幅是 614×345 的职业原画（不是 128 的图标），
# 板块图与场景图是参考站首页 / 天赋页上真正在用的那几张。带 hash 的从页面现读，不写死。
CLASS_BANNER_DIR = "/peitu/zhiye/"
PANEL_SOURCES = {
    "spellbook": "/shouye-tu/spellbook.webp",
    "map": "/shouye-tu/ditu.webp",
    "library": "/shouye-tu/ditu.webp",
}
PANEL_HASHED = {"talent": r"/assets/talent-calculator-[0-9a-zA-Z]+\.webp",
                "spellbook2": r"/assets/spellbook-[0-9a-zA-Z]+\.webp"}
SCENES = {"yunhai": u"云海（部落营地氛围）", "gulin": u"古林（联盟营地氛围）",
          "zhong/tielu-dadian": u"铁路大殿", "zhong/guangshu": u"光树"}
TEXTURE = "/shiban/shi-ping.webp"


def our_tree_names():
    """我们数据里每个职业的三系中文名，用来回对参考站的键名顺序。"""
    out = {}
    for cid in SPEC_TREES:
        p = os.path.join(DATA, "talents", cid + ".json")
        if not os.path.exists(p):
            out[cid] = []
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        out[cid] = [(t.get("nameCn") or "") for t in d.get("trees") or []]
    return out


def _paste_corner(canvas, img, corner):
    """四角图按各自位置贴进一张画布：左上角原点，右上角靠右，下两排靠下。"""
    w, h = canvas.size
    iw, ih = img.size
    x = 0 if corner.endswith("Left") else max(0, w - iw)
    y = 0 if corner.startswith("Top") else max(0, h - ih)
    canvas.paste(img, (x, y), img if img.mode == "RGBA" else None)


def _is_image(blob):
    """只认文件头，不认体积：右下角那种 64×128 的角图本来就只有一百来字节，
       按体积阈值判会把好图当成缺图。"""
    return blob[:4] == b"RIFF" and blob[8:12] == b"WEBP" or blob[:4] == b"\x89PNG"


def fetch_tile(key, corner):
    """一棵树的一张角图：先试 wclbox（.webp），404 或坏图再试 jjwow（.PNG）。
       圣骑士在 wclbox 上是坏的，就是靠这条兜回来的。"""
    cands = [WBX + "/tianfu-beijing/%s-%s.webp" % (key, corner)]
    jk = JJ_KEY.get(key, key)
    cands.append(JJ + "/assets/talent-backgrounds/%s-%s.PNG" % (jk, corner))
    for url in cands:
        code, blob = http(url, binary=True)
        if code == 200 and _is_image(blob):
            return (url, blob)
    return None


def specbg(man, force=False):
    """27 棵专精树各一张背景：下四角图 → 拼成一张 → 落 art/specs/<职业>-<第几系>.webp。

    为什么不直接存四张角图：那是给它们的九宫格布局用的，我们只要一张能当卡片底的整图，
    拼好之后 27 个文件、每系一张，页面 CSS 一行就能用，也不用在两栈各写一套四角定位。
    """
    try:
        from PIL import Image
    except ImportError:
        sys.exit(u"拼角图要 PIL（pillow）。没装就先 pip3 install pillow，或跳过 --what specbg")
    mine = our_tree_names()
    bad = []
    for cid, rows in SPEC_TREES.items():
        names = mine.get(cid) or []
        for i, (key, cn) in enumerate(rows):
            if i >= len(names) or (names[i] or "").strip() != cn:
                bad.append(u"%s 第 %d 系：我们写「%s」，键名表写「%s」（%s）"
                           % (cid, i + 1, names[i] if i < len(names) else u"缺系", cn, key))
    if bad:
        sys.exit(u"专精键名表与我们的天赋数据对不上，先人工核：\n  " + u"\n  ".join(bad))
    ok, miss = [], []
    for cid, rows in SPEC_TREES.items():
        for i, (key, cn) in enumerate(rows):
            dest = os.path.join(ART, "specs", "%s-%d.webp" % (cid, i))
            if os.path.exists(dest) and not force:
                ok.append(u"%s-%d（已有，--force 重抓）" % (cid, i))
                continue
            parts, urls = [], []
            for corner in CORNERS:
                got = fetch_tile(key, corner)
                if not got:
                    miss.append(u"%s/%s（两台源都取不到）" % (key, corner))
                    parts = []
                    break
                url, blob = got
                parts.append((corner, blob))
                urls.append(url)
            if len(parts) != 4:
                continue
            imgs = {}
            for corner, blob in parts:
                im = Image.open(io.BytesIO(blob)).convert("RGBA")
                imgs[corner] = im
            tl, tr = imgs["TopLeft"], imgs["TopRight"]
            bl, br = imgs["BottomLeft"], imgs["BottomRight"]
            W, H = tl.width + tr.width, tl.height + bl.height
            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for corner, im in imgs.items():
                _paste_corner(canvas, im, corner)
            if not os.path.isdir(os.path.dirname(dest)):
                os.makedirs(os.path.dirname(dest))
            buf = io.BytesIO()
            canvas.save(buf, "WEBP", quality=82, method=4)
            blob = buf.getvalue()
            rec = save(dest, blob, urls[0], "spec-bg")
            rec["tree"] = key
            rec["treeCn"] = cn
            rec["tiles"] = urls
            rec["size"] = "%dx%d" % (W, H)
            man["items"] = [x for x in man["items"] if x["file"] != rec["file"]] + [rec]
            ok.append(u"%s-%d %s（%s，%dx%d，%d KB）" % (cid, i, key, cn, W, H, len(blob) // 1024))
    print(u"专精背景：拼好 %d / 27，取不到 %d" % (len(ok), len(miss)))
    for x in miss[:12]:
        print(u"  缺 " + x)


def panels(man):
    """板块入口卡的配图：职业横幅 9 张 + 板块图 + 场景图 + 石板纹理。

    这些都是"图"不是"图标"——用户实拍指出：以前板块卡拿 128×128 的职业图标当背景，
    拉开放大就是糊的一团。这里全部按原尺寸转存，来源与抓取日期进 manifest。
    """
    ok, miss = [], []

    def grab(url, subdir, name, kind, what=None):
        code, blob = http(url, binary=True)
        if code != 200 or len(blob) < 1500 or blob[:4] == b"<":
            miss.append(u"%s/%s（HTTP %s）" % (subdir, name, code))
            return None
        dest = os.path.join(ART, subdir, name + ".webp")
        rec = save(dest, blob, url, kind)
        if what:
            rec["what"] = what
        man["items"] = [x for x in man["items"] if x["file"] != rec["file"]] + [rec]
        ok.append(u"%s/%s（%d KB）" % (subdir, name, len(blob) // 1024))
        return rec

    code, html = http(WBX + "/")
    hashed = {}
    if code == 200:
        for k, pat in PANEL_HASHED.items():
            m = re.search(pat, html)
            if m:
                hashed[k] = m.group(0)
    for cid in ["warrior", "paladin", "hunter", "rogue", "priest", "shaman", "mage", "warlock", "druid"]:
        grab(WBX + CLASS_BANNER_DIR + cid + ".webp", "classbanners", cid, "class-banner")
    for name, path in PANEL_SOURCES.items():
        grab(WBX + path, "panels", name, "panel")
    for k in ["talent", "spellbook2"]:
        if k in hashed:
            grab(WBX + hashed[k], "panels", "talent" if k == "talent" else "spellbook-full", "panel")
        else:
            miss.append(u"panels/%s（首页 HTML 里没找到这个文件名）" % k)
    for src, what in SCENES.items():
        key = src.split("/")[-1]
        grab(WBX + "/peitu/changjing/" + src + ".webp", "scenes", key, "scene", what)
    grab(WBX + TEXTURE, "texture", "stone", "texture", u"石板纹理")
    print(u"板块配图：新增或更新 %d，取不到 %d" % (len(ok), len(miss)))
    for x in miss[:10]:
        print(u"  缺 " + x)


def write_art_index(man):
    """把 manifest 收成界面能直接用的索引：app/data/art.json。
    页面据此决定"有原画就用原画、没有就自绘"，不靠试错加载。"""
    idx = {"classes": {}, "dungeons": {}, "maps": {}, "races": {}, "factions": {},
           "factionCities": {}, "bosses": {}, "specs": {}, "classBanners": {},
           "panels": {}, "scenes": {}, "texture": {}, "raceIcons": {}, "meta": {}}
    for x in man["items"]:
        rel = x["file"] if x["file"].startswith("art/") else "art/" + x["file"]
        name = os.path.splitext(os.path.basename(rel))[0]
        if x["kind"] == "class-bg":
            idx["classes"][name] = "img/" + rel
        elif x["kind"] == "zone-map":
            idx["maps"][name] = "img/" + rel
        elif x["kind"] == "race-portrait":
            idx["races"][name] = "img/" + rel
        elif x["kind"] == "race-icon":
            # 种族**小图标**（插件目录转存的加工图，站主 2026-10-20 特批）单独一个键，
            # 不与 races 那张大图原画混：传承页拿 races/skyborne 当页头大图，
            # 64px 的小图塞进去就是全站放大糊。
            idx["raceIcons"][name] = "img/" + rel
        elif x["kind"] == "faction-emblem":
            idx["factions"][name] = "img/" + rel
        elif x["kind"] == "faction-city":
            idx["factionCities"][name.replace("city-", "")] = "img/" + rel
        elif x["kind"] == "boss-portrait":
            idx["bosses"][name] = "img/" + rel
        elif x["kind"] == "spec-bg":
            # 只放路径；系名在 talents/*.json 里，索引不重复存一份（存了就会漂）
            idx["specs"][name] = "img/" + rel
        elif x["kind"] == "class-banner":
            idx["classBanners"][name] = "img/" + rel
        elif x["kind"] == "panel":
            idx["panels"][name] = "img/" + rel
        elif x["kind"] == "scene":
            idx["scenes"][name] = "img/" + rel
        elif x["kind"] == "texture":
            idx["texture"][name] = "img/" + rel
        else:
            idx["dungeons"][name] = "img/" + rel
    idx["meta"] = {"fetchedAt": man.get("fetchedAt"), "note": man.get("note"),
                   "count": len(man["items"])}
    # 插件目录转存的那几张（origin 以 addon 开头：加工图、自绘底图）单独列出来给溯源页读。
    # 为什么不在页面里写死：授权语与回退方案都记在 manifest，抄一份到 Vue 里就是将来漂移的源头，
    # 而且以后再来一张同源的图，页面不用改就能自己把话说全。
    addon = []
    for x in man["items"]:
        if not str(x.get("origin", "")).startswith("addon"):
            continue
        # manifest 里存的是本机完整路径（我们自己回查要用），页面上只露插件内那一段：
        # 把 ~/Documents/.../.scratch 这种本机目录结构印到公开页面上没有意义，也只是给外人看我们的机器。
        src = str(x.get("source") or "")
        name = x.get("addon") or ""
        disp = src.split(name + "/", 1)[1] if name and name + "/" in src else os.path.basename(src)
        addon.append({
            "name": os.path.splitext(os.path.basename(x["file"]))[0],
            "file": "img/" + (x["file"] if x["file"].startswith("art/") else "art/" + x["file"]),
            "kind": x.get("kind"), "origin": x.get("origin"),
            "addon": x.get("addon"), "addonVersion": x.get("addonVersion"),
            "sourceDisplay": disp,
            "authorizedBy": x.get("authorizedBy"),
            "rollback": x.get("rollback"), "importedAt": x.get("importedAt"),
            "sha256": x.get("sha256"),
        })
    idx["meta"]["addonFiles"] = addon
    io.open(os.path.join(DATA, "art.json"), "w", encoding="utf-8").write(
        json.dumps(idx, ensure_ascii=False, indent=1) + "\n")
    print(u"界面索引 → app/data/art.json（职业 %d / 副本 %d / 小地图 %d / 种族头像 %d / "
          u"阵营徽标 %d / 阵营城市 %d / 首领头像 %d / 专精背景 %d / 职业横幅 %d / "
          u"板块图 %d / 场景图 %d / 纹理 %d）" % (
              len(idx["classes"]), len(idx["dungeons"]), len(idx["maps"]), len(idx["races"]),
              len(idx["factions"]), len(idx["factionCities"]), len(idx["bosses"]),
              len([k for k in idx["specs"] if not k.endswith(":cn")]),
              len(idx["classBanners"]), len(idx["panels"]), len(idx["scenes"]),
              len(idx["texture"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["classes", "dungeons", "maps", "races", "factions",
                                       "bosses", "specbg", "panels", "all"], default="all")
    ap.add_argument("--force", action="store_true",
                    help="专精背景图已存在的也重抓（源站换了角图时用）")
    ap.add_argument("--index-only", action="store_true",
                    help="不下载，只按现有 manifest 重算 app/data/art.json")
    ap.add_argument("--probe", action="store_true",
                    help="只问源站有没有这张图，不落盘（首领头像用它先量缺口）")
    args = ap.parse_args()
    man = load_manifest()
    if args.index_only:
        write_art_index(man)
        print(u"manifest 共 %d 条 → app/img/art/manifest.json" % len(man["items"]))
        return
    if args.what == "bosses" and args.probe:
        bosses(man, probe_only=True)
        return
    if args.what in ("classes", "all"):
        classes(man)
    if args.what in ("dungeons", "all"):
        dungeons(man)
    if args.what in ("maps", "all"):
        maps(man)
    if args.what in ("races", "all"):
        races(man)
    if args.what in ("factions", "all"):
        factions(man)
    if args.what in ("bosses", "all"):
        bosses(man)
    if args.what in ("specbg", "all"):
        specbg(man, force=args.force)
    if args.what in ("panels", "all"):
        panels(man)
    man["fetchedAt"] = datetime.date.today().isoformat()
    man["total"] = len(man["items"])
    save_manifest(man)
    write_art_index(man)
    print(u"manifest 共 %d 条 → app/img/art/manifest.json" % man["total"])


if __name__ == "__main__":
    main()
