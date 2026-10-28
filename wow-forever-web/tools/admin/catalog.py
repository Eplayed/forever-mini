"""Local admin catalog. Paths and actions are an explicit allowlist, never client input."""
import json
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "app", "data")

# source = actual evidence for the current product, candidate sources stay labelled as candidates.
TOPICS = (
    ("items", "物品名录", "items.json", "items", "upstream/wclbox-items-index.json", "现有成品：新手盒子物品 SSR 名录；待审拉取：公开 API", "https://wowforever.wclbox.com/wupin/liebiao/1", None),
    ("item-detail", "物品详情", "items-detail.json", "items", "upstream/wclbox-items-detail.json", "新手盒子 + GI/XR 插件；属性按插件优先", "https://wowforever.wclbox.com/wupin", None),
    ("world", "世界地图与稀有", "world.json", "zones", "upstream/wclbox-world.json", "新手盒子客户端解包转述 + 插件", "https://wowforever.wclbox.com/ditu", "world"),
    ("changes", "客户端改动", "changes.json", "items", "upstream/wclbox-changes.json", "新手盒子客户端解包转述", "https://wowforever.wclbox.com/gaidong", "changes"),
    ("dungeons", "副本与掉落", "dungeons.json", "newDungeons+classicDungeons+raids", "upstream/wclbox-dungeons.json", "新手盒子 + 客户端排队表 + DB2", "https://wowforever.wclbox.com/fuben", "dungeons"),
    ("dungeon-quests", "副本任务", "dungeon-quests.json", "dungeons", "upstream/wclbox-dungeon-quests.json", "新手盒子 + Wowhead + GI", "https://wowforever.wclbox.com/fuben", None),
    ("professions", "专业与配方", "professions.json", "professions", "upstream/wclbox-professions.json", "新手盒子 + XR 插件", "https://wowforever.wclbox.com/zhuanye", "prof"),
    ("legacy", "传承", "legacy.json", "perks", "upstream/wclbox-legacy.json", "新手盒子客户端解包转述", "https://wowforever.wclbox.com/chuancheng", "legacy"),
    ("spells", "技能书", "spells.json", "spells", "upstream/wclbox-spells.json", "新手盒子 + GI/XR 插件", "https://wowforever.wclbox.com/jineng", None),
    ("talents", "天赋节点", "talents/（九职业）", "talents", "upstream/fengshen-hunter.json", "fengshen + nieyi 双源", "https://wowclassicforever.info/", "talents"),
    ("achievements", "成就", "achievements.json", "achievements", "upstream/gi-achievements.json", "GI 插件 + 新手盒子逐字核", "https://wowforever.wclbox.com/chengjiu", None),
    ("bis", "配装名单", "bis.json", "sets", "upstream/wclbox-bis.json", "新手盒子 + 第二社区名单（L1）", "https://wowforever.wclbox.com/peizhuang", "bis"),
    ("guide", "宏与插件目录", "guide.json", "macros+addons", None, "人工核作者、原帖和日期", None, None),
    ("quests", "全域任务（未建库）", None, None, None, "候选：新手盒子任务目录；待核 quest ID", "https://wowforever.wclbox.com/renwu", None),
    ("pets", "猎人宠物（未建库）", None, None, None, "候选：新手盒子猎人宠物；意译待核", "https://wowforever.wclbox.com/lieren-chongwu", None),
    ("pvp", "PvP 军衔（未建库）", None, None, None, "候选：新手盒子军衔；规则待实测", "https://wowforever.wclbox.com/junxian", None),
)


def _count(data, key):
    if key == "dungeon-quests":
        return sum(len(group.get("quests") or []) for group in (data.get("dungeons") or {}).values())
    return sum(len(data.get(k) or []) for k in key.split("+"))


def catalog():
    rows = []
    for slug, label, product, key, upstream, source, url, workflow in TOPICS:
        path = os.path.join(DATA, product) if product and slug != "talents" else None
        meta, count, error = {}, None, None
        if slug == "talents":
            try:
                folder = os.path.join(DATA, "talents")
                count = 0
                for name in os.listdir(folder):
                    if name.endswith(".json"):
                        with open(os.path.join(folder, name), encoding="utf-8") as f:
                            doc = json.load(f)
                        count += sum(len(tree.get("nodes") or []) for tree in doc.get("trees") or [])
            except (OSError, ValueError, TypeError) as exc:
                error = str(exc)
        elif path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("meta") or {}
                count = _count(data, "dungeon-quests" if slug == "dungeon-quests" else key)
            except (OSError, ValueError, TypeError) as exc:
                error = str(exc)
        elif path:
            error = "成品文件不存在"
        date_candidates = [("fetched", "源抓取"), ("fetchedAt", "源抓取"),
                           ("scrapedAt", "源抓取"), ("upstream.scrapedAt", "源抓取"),
                           ("generatedAt", "成品生成")]
        stamp, date_kind = None, None
        for key_name, kind_name in date_candidates:
            value = (meta.get("upstream") or {}).get("scrapedAt") if key_name == "upstream.scrapedAt" else meta.get(key_name)
            if value:
                stamp, date_kind = value, kind_name
                break
        age = None
        if stamp:
            try:
                age = (date.today() - date.fromisoformat(str(stamp)[:10])).days
            except ValueError:
                pass
        up_path = os.path.join(DATA, upstream) if upstream else None
        rows.append({"id": slug, "label": label, "product": product, "count": count,
                     "date": stamp, "dateKind": date_kind, "age": age,
                     "build": meta.get("foreverBuild") or meta.get("clientBuild"),
                     "upstream": upstream, "upstreamExists": bool(up_path and os.path.isfile(up_path)),
                     "source": source, "url": url, "workflow": workflow,
                     "state": "error" if error else ("candidate" if product is None else "ready"), "error": error})
    return rows


def gaps():
    """Only gaps derivable from current product data; no historical snapshot numbers."""
    def read(name):
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    try:
        items = read("items.json").get("items", [])
        detail = read("items-detail.json").get("items", {})
        world = read("world.json")
        dungeons = read("dungeons.json")
        guide = read("guide.json")
        ids = {str(row.get("id")) for row in items}
        detail_ids = set(detail) if isinstance(detail, dict) else {str(x.get("id")) for x in detail}
        all_dungeons = sum((dungeons.get(k, []) for k in ("newDungeons", "classicDungeons", "raids")), [])
        return [
            {"label": "名录内缺物品详情", "value": len(ids - detail_ids), "topic": "item-detail"},
            {"label": "稀有缺坐标", "value": len(world.get("raresUnplaced") or []), "topic": "world"},
            {"label": "副本无首领名单", "value": sum(not row.get("bosses") for row in all_dungeons), "topic": "dungeons"},
            {"label": "宏条目", "value": len(guide.get("macros") or []), "topic": "guide"},
            {"label": "插件条目", "value": len(guide.get("addons") or []), "topic": "guide"},
        ]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return [{"label": "缺口计算失败", "error": str(exc)}]


def records(topic, query="", offset=0):
    """Bounded read-only explorer; never accepts a filesystem path from the browser."""
    row = next((t for t in TOPICS if t[0] == topic), None)
    if row is None or row[2] is None:
        raise ValueError("没有可浏览的成品数据")
    if not isinstance(offset, int) or offset < 0 or offset > 100000 or len(query) > 80:
        raise ValueError("检索参数超出范围")
    if topic == "talents":
        collection = []
        folder = os.path.join(DATA, "talents")
        for name in sorted(os.listdir(folder)):
            if name.endswith(".json"):
                with open(os.path.join(folder, name), encoding="utf-8") as f:
                    doc = json.load(f)
                for tree in doc.get("trees") or []:
                    collection.extend(tree.get("nodes") or [])
    else:
        with open(os.path.join(DATA, row[2]), encoding="utf-8") as f:
            doc = json.load(f)
        if topic == "dungeons":
            collection = sum((doc.get(k, []) for k in ("newDungeons", "classicDungeons", "raids")), [])
        elif topic == "dungeon-quests":
            collection = [dict(item, dungeon=slug) for slug, group in (doc.get("dungeons") or {}).items()
                          for item in group.get("quests") or []]
        elif topic == "guide":
            collection = (doc.get("macros") or []) + (doc.get("addons") or [])
        else:
            key = row[3].split("+")[0]
            collection = doc.get(key) or []
    if isinstance(collection, dict):
        collection = [dict(value, id=value.get("id", key)) if isinstance(value, dict) else {"id": key, "value": value}
                      for key, value in collection.items()]
    q = query.strip().casefold()
    def searchable(item):
        return " ".join(str(item.get(k) or "") for k in ("id", "name", "nameCn", "nameEn", "title", "dungeon")).casefold()
    selected = [item for item in collection if not q or
                (str(item.get("id")) == q if q.isdigit() else q in searchable(item))]
    page = selected[offset:offset + 20]
    return {"topic": topic, "total": len(selected), "offset": offset, "limit": 20,
            "rows": [{"id": item.get("id"), "name": item.get("nameCn") or item.get("name") or item.get("nameEn") or item.get("title") or "—",
                      "level": item.get("level"), "raw": item} for item in page]}
