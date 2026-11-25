# -*- coding: utf-8 -*-
"""forever_data_routes.py — 魔兽无限数据侧平台（MacBook :15801 接入 Blueprint）

架构（2026-11-23 站主定）：
- Windows 主机（默认 http://192.168.0.104:8830）是唯一数据源生产端（WCLBox / 60级BiS / 任务 / 物品 / 人口 / NGA / 插件层）；
- MacBook :15801 提供：
  1. 实时状态探测与新鲜度总览（在线显示 Windows 生产端 + Mac 本地同步副本对照，离线仍可浏览 Mac 本地数据）；
  2. 一键「从 Windows 拉取最新数据到 MacBook」（调 Windows `sync-mac` -> `sync-to-mac.py` + `sync_wow_icons.py`）；
  3. 一键「远程触发 Windows 重抓某板块并自动同步回 Mac」（调 Windows `refresh-and-sync`）；
  4. Mac 本机高速可视化浏览器（物品/属性、60级团前BiS、T1团本套、30级与练级套、38座副本、副本任务、双源人口普查、技能/宏/天赋）。
"""
from __future__ import annotations

import json
import pathlib
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request, send_from_directory
from . import ningjing_studio, wechat_mp_publisher

bp = Blueprint("forever_data", __name__)
ROOT = pathlib.Path(__file__).resolve().parents[1]

DEFAULT_WIN_URL = "http://192.168.0.104:8830"
LAN_HEADERS = {"X-Wow-Lan-Client": "macbook-15801"}

CLASS_CN = {
    "warrior": "战士", "paladin": "圣骑士", "hunter": "猎人",
    "rogue": "潜行者", "priest": "牧师", "shaman": "萨满祭司",
    "mage": "法师", "warlock": "术士", "druid": "德鲁伊",
}

_DATA_CACHE: Dict[str, Tuple[float, Any]] = {}


def _win_admin_url() -> str:
    env_cfg = wechat_mp_publisher._load_env_file(ROOT / "config" / "config.env.local")
    return (env_cfg.get("WOW_WIN_ADMIN_URL") or DEFAULT_WIN_URL).strip().rstrip("/")


def _app_data_dir() -> pathlib.Path:
    return ningjing_studio._find_app_root() / "data"


def _load_json_cached(rel_path: str) -> Any:
    p = _app_data_dir() / rel_path
    if not p.is_file():
        return None
    mt = p.stat().st_mtime
    ent = _DATA_CACHE.get(rel_path)
    if ent and ent[0] == mt:
        return ent[1]
    data = json.loads(p.read_text(encoding="utf-8"))
    _DATA_CACHE[rel_path] = (mt, data)
    return data


def _proxy_win(method: str, path: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 4.0) -> Tuple[int, Dict[str, Any]]:
    url = _win_admin_url() + path
    headers = dict(LAN_HEADERS)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {"error": str(e)}
        return e.code, body
    except Exception as e:
        return 503, {"error": f"Windows 数据主机未连通（{url}）：{e}"}


def _local_block_summary() -> Dict[str, Any]:
    data_dir = _app_data_dir()
    app_root = data_dir.parent
    icons_dir = app_root / "img" / "icons"
    icon_cnt = sum(1 for _ in icons_dir.glob("*")) if icons_dir.is_dir() else 0

    specs = [
        ("items", "物品名录", "items.json", "items", "items"),
        ("item-detail", "物品属性详情", "items-detail.json", "items", None),
        ("bis60", "60级团前 BiS（27套）", "bis.json", "bis60Sets", "bis60"),
        ("bis", "配装与套装（全套合计）", "bis.json", "sets+bis60Sets+raidSets+itemSets", "bis"),
        ("dungeons", "副本与掉落", "dungeons.json", "newDungeons+classicDungeons+raids", "dungeons"),
        ("dungeon-quests", "副本任务", "dungeon-quests.json", "dungeons", "dungeon-quests"),
        ("census", "人口普查（国服+Everloot）", "population-census-cn.json", "classes", "census"),
        ("spells", "技能书", "spells.json", "spells", "spells"),
        ("talents", "九职业天赋树", "talents/", "talents", "talents"),
        ("macros", "宏命令库", "macros.json", "macros", None),
        ("professions", "专业与配方", "professions.json", "professions", "professions"),
        ("achievements", "成就目录", "achievements.json", "achievements", "achievements"),
        ("legacy", "传承系统", "legacy.json", "perks", "legacy"),
        ("world", "世界地图与稀有", "world.json", "zones", "world"),
        ("changes", "客户端改动", "changes.json", "items", "changes"),
        ("nga", "NGA 选题雷达（Windows侧）", None, None, "nga"),
    ]
    rows: List[Dict[str, Any]] = []
    for bid, label, rel, key, refresh_topic in specs:
        count: Optional[int] = None
        stamp: Optional[str] = None
        mtime_txt: Optional[str] = None
        age: Optional[int] = None
        if bid == "talents":
            tdir = data_dir / "talents"
            if tdir.is_dir():
                count = 0
                latest_mt = 0.0
                for f in tdir.glob("*.json"):
                    if f.name.startswith("_"):
                        continue
                    latest_mt = max(latest_mt, f.stat().st_mtime)
                    doc = json.loads(f.read_text(encoding="utf-8"))
                    count += sum(len(tr.get("nodes") or []) for tr in (doc.get("trees") or []))
                if latest_mt:
                    mtime_txt = datetime.fromtimestamp(latest_mt).strftime("%m-%d %H:%M")
        elif rel:
            p = data_dir / rel
            if p.is_file():
                mtime_txt = datetime.fromtimestamp(p.stat().st_mtime).strftime("%m-%d %H:%M")
                doc = _load_json_cached(rel) or {}
                if bid == "dungeon-quests":
                    count = sum(len(g.get("quests") or []) for g in (doc.get("dungeons") or {}).values())
                elif key:
                    count = sum(len(doc.get(k) or []) for k in key.split("+"))
                meta = doc.get("meta") or {}
                if not meta and isinstance(doc.get("provenance"), dict):
                    meta = {"fetchedAt": doc["provenance"].get("checkedAt") or doc["provenance"].get("sourceTime")}
                for dk in ("fetched", "fetchedAt", "scrapedAt", "upstream.scrapedAt", "generatedAt"):
                    val = (meta.get("upstream") or {}).get("scrapedAt") if dk == "upstream.scrapedAt" else meta.get(dk)
                    if val:
                        stamp = str(val)[:10]
                        break
                if bid == "bis60" and (doc.get("bis60Sets") or []):
                    stamp = str(doc["bis60Sets"][0].get("fetched") or stamp or "")[:10]
                if stamp:
                    try:
                        age = (date.today() - date.fromisoformat(stamp)).days
                    except ValueError:
                        age = None
        level = "na" if age is None else ("fresh" if age <= 7 else ("warm" if age <= 13 else "stale"))
        rows.append({
            "id": bid,
            "label": label,
            "count": count,
            "date": stamp,
            "age": age,
            "level": level,
            "macSyncedAt": mtime_txt,
            "refreshTopic": refresh_topic,
        })
    return {"rows": rows, "iconCount": icon_cnt, "dataDir": str(data_dir)}


@bp.route("/api/forever/status")
def api_forever_status():
    local = _local_block_summary()
    win_code, win_fresh = _proxy_win("GET", "/api/freshness", timeout=2.5)
    win_online = win_code == 200 and isinstance(win_fresh, dict) and "rows" in win_fresh
    win_map = {r["id"]: r for r in (win_fresh.get("rows") or [])} if win_online else {}

    merged = []
    for row in local["rows"]:
        wr = win_map.get(row["id"])
        item = dict(row)
        if wr:
            item["winCount"] = wr.get("count")
            item["winDate"] = wr.get("date")
            item["winLevel"] = wr.get("level")
            item["behindWin"] = (
                (wr.get("count") is not None and row["count"] is not None and wr.get("count") != row["count"])
                or (wr.get("date") and row["date"] and str(wr.get("date"))[:10] > str(row["date"])[:10])
            )
        else:
            item["winCount"] = None
            item["winDate"] = None
            item["winLevel"] = None
            item["behindWin"] = False
        merged.append(item)

    return jsonify({
        "ok": True,
        "winOnline": win_online,
        "winUrl": _win_admin_url(),
        "winError": "" if win_online else (win_fresh.get("error") if isinstance(win_fresh, dict) else "未连通"),
        "iconCount": local["iconCount"],
        "rows": merged,
    })


@bp.route("/api/forever/pull_from_windows", methods=["POST"])
def api_forever_pull_from_windows():
    code, body = _proxy_win("POST", "/api/jobs", {"action": "sync-mac"}, timeout=6.0)
    if code not in (200, 202):
        return jsonify({"ok": False, "error": body.get("error") or f"Windows 返回 {code}"}), code
    return jsonify({"ok": True, "jobId": body.get("jobId")})


@bp.route("/api/forever/refresh_and_pull", methods=["POST"])
def api_forever_refresh_and_pull():
    data = request.get_json(force=True) or {}
    topic = (data.get("topic") or "").strip()
    action = (data.get("action") or "refresh-and-sync").strip()
    if action == "daily":
        payload = {"action": "daily", "topic": "--quick"}
    else:
        if not topic:
            return jsonify({"ok": False, "error": "缺少刷新板块 topic"}), 400
        payload = {"action": "refresh-and-sync", "topic": topic}
    code, body = _proxy_win("POST", "/api/jobs", payload, timeout=6.0)
    if code not in (200, 202):
        return jsonify({"ok": False, "error": body.get("error") or f"Windows 返回 {code}"}), code
    return jsonify({"ok": True, "jobId": body.get("jobId"), "topic": topic, "action": payload["action"]})


@bp.route("/api/forever/win_job/<job_id>")
def api_forever_win_job(job_id):
    code, body = _proxy_win("GET", f"/api/jobs/{job_id}", timeout=4.0)
    if code != 200:
        return jsonify({"ok": False, "error": body.get("error") or f"查询任务失败（{code}）"}), code
    if body.get("state") == "done":
        _DATA_CACHE.clear()
    return jsonify({"ok": True, "job": body})


@bp.route("/api/forever/browse")
def api_forever_browse():
    tab = (request.args.get("tab") or "items").strip()
    q = (request.args.get("q") or "").strip().casefold()
    cls = (request.args.get("cls") or "").strip().lower()
    try:
        offset = max(0, int(request.args.get("offset") or 0))
        limit = min(50, max(5, int(request.args.get("limit") or 24)))
    except ValueError:
        offset, limit = 0, 24

    if tab == "items":
        items = (_load_json_cached("items.json") or {}).get("items") or []
        det = (_load_json_cached("items-detail.json") or {}).get("items") or {}
        if q:
            if q.isdigit():
                filtered = [x for x in items if str(x.get("id")) == q]
            else:
                filtered = [x for x in items if q in str(x.get("name") or "").casefold() or q in str(x.get("slot") or "").casefold()]
        else:
            filtered = items
        page = []
        for x in filtered[offset:offset + limit]:
            d = det.get(str(x.get("id"))) or {}
            page.append({
                "id": x.get("id"),
                "name": x.get("name"),
                "q": x.get("quality") if x.get("quality") is not None else x.get("q"),
                "icon": x.get("icon") or d.get("icon") or "",
                "ilvl": x.get("ilvl") or d.get("ilvl"),
                "slot": x.get("slot") or x.get("typeMain") or "",
                "stats": (d.get("st") or [])[:4],
                "sell": d.get("sell") or "",
                "src": (" / ".join(x.get("src") or []) if x.get("src") else (x.get("type") or ""))[:50],
            })
        return jsonify({"ok": True, "tab": tab, "total": len(filtered), "rows": page})

    if tab in ("bis60", "bis30", "raid_t1", "item_sets"):
        bis = _load_json_cached("bis.json") or {}
        items_by_id = {str(x.get("id")): x for x in ((_load_json_cached("items.json") or {}).get("items") or [])}
        if tab == "bis60":
            sets = bis.get("bis60Sets") or []
            if cls:
                sets = [s for s in sets if (s.get("cls") or "").lower() == cls]
            if q:
                sets = [s for s in sets if q in json.dumps(s, ensure_ascii=False).casefold()]
            out = []
            for s in sets[offset:offset + limit]:
                refs = s.get("refs") or {}
                slots = []
                for g in (s.get("doll") or []):
                    iid = str(g.get("item") or "")
                    ref = refs.get(iid) or {}
                    it = items_by_id.get(iid) or {}
                    src_val = ref.get("srcLabel") or ref.get("src") or (" / ".join(it.get("src") or []) if isinstance(it.get("src"), list) else "")
                    slots.append({
                        "slot": g.get("slot") or "",
                        "id": iid,
                        "name": it.get("name") or ref.get("name") or f"物品 #{iid}",
                        "q": it.get("quality") if it.get("quality") is not None else (ref.get("q") or ""),
                        "icon": it.get("icon") or ref.get("icon") or "",
                        "ilvl": it.get("ilvl") or ref.get("ilvl") or "",
                        "src": str(src_val or ""),
                    })
                out.append({
                    "id": s.get("id"),
                    "title": f"{s.get('clsCn') or s.get('cls')} · {s.get('mode') or s.get('spec')}",
                    "fetched": s.get("fetched") or "",
                    "count": len(slots),
                    "slots": slots,
                })
            return jsonify({"ok": True, "tab": tab, "total": len(sets), "rows": out})

        if tab == "raid_t1":
            sets = bis.get("raidSets") or []
            if cls:
                sets = [s for s in sets if (s.get("cls") or "").lower() == cls]
            if q:
                sets = [s for s in sets if q in (str(s.get("name")) + str(s.get("clsCn")) + str(s.get("spec"))).casefold()]
            out = []
            for s in sets[offset:offset + limit]:
                pieces = []
                for pid in (s.get("pieceIds") or []):
                    it = items_by_id.get(str(pid)) or {}
                    pieces.append({"id": pid, "name": it.get("name") or f"物品 #{pid}", "slot": it.get("slot") or "", "ilvl": it.get("ilvl") or ""})
                out.append({
                    "id": s.get("id"),
                    "title": f"{s.get('name')}（{s.get('clsCn')} · {s.get('spec')}）",
                    "meta": f"{s.get('raid')} · {s.get('armor')} · {s.get('pieceCount')}件 · {s.get('roleCn')}",
                    "pieces": pieces,
                })
            return jsonify({"ok": True, "tab": tab, "total": len(sets), "rows": out})

        sets = bis.get("itemSets") or [] if tab == "item_sets" else (bis.get("sets") or [])
        if cls:
            sets = [s for s in sets if (s.get("cls") or "").lower() == cls]
        if q:
            sets = [s for s in sets if q in json.dumps(s, ensure_ascii=False).casefold()]
        return jsonify({"ok": True, "tab": tab, "total": len(sets), "rows": sets[offset:offset + limit]})

    if tab == "dungeons":
        doc = _load_json_cached("dungeons.json") or {}
        qdoc = (_load_json_cached("dungeon-quests.json") or {}).get("dungeons") or {}
        all_d = []
        for k, tag in (("newDungeons", "无限新增"), ("classicDungeons", "经典副本"), ("raids", "团队副本")):
            for d in doc.get(k) or []:
                did = d.get("id") or ""
                all_d.append({
                    "id": did,
                    "kind": tag,
                    "nameCn": d.get("nameCn") or "",
                    "zoneCn": d.get("zoneCn") or "",
                    "levelRange": d.get("levelRange") or "",
                    "bossCount": len(d.get("bosses") or []),
                    "questCount": len((qdoc.get(did) or {}).get("quests") or []),
                    "dropCount": len(d.get("drops") or []),
                })
        if q:
            all_d = [x for x in all_d if q in (x["nameCn"] + x["zoneCn"] + x["kind"]).casefold()]
        return jsonify({"ok": True, "tab": tab, "total": len(all_d), "rows": all_d[offset:offset + limit]})

    if tab == "quests":
        qdoc = (_load_json_cached("dungeon-quests.json") or {}).get("dungeons") or {}
        d_names = {}
        ddoc = _load_json_cached("dungeons.json") or {}
        for k in ("newDungeons", "classicDungeons", "raids"):
            for d in ddoc.get(k) or []:
                d_names[d.get("id")] = d.get("nameCn") or d.get("id")
        rows = []
        for did, grp in qdoc.items():
            for qx in grp.get("quests") or []:
                rows.append({
                    "dungeon": d_names.get(did, did),
                    "nameCn": qx.get("nameCn") or "",
                    "level": qx.get("questLevel") or qx.get("reqLevel") or "",
                    "xp": qx.get("xp") or "",
                    "pickup": f"{qx.get('pickupZone') or ''} · {qx.get('pickupNpc') or ''}".strip(" ·"),
                    "coord": f"({qx.get('pickupX')}, {qx.get('pickupY')})" if qx.get("pickupX") else "",
                })
        if q:
            rows = [r for r in rows if q in (r["dungeon"] + r["nameCn"] + r["pickup"]).casefold()]
        return jsonify({"ok": True, "tab": tab, "total": len(rows), "rows": rows[offset:offset + limit]})

    if tab == "census":
        cn = _load_json_cached("population-census-cn.json") or {}
        ev = _load_json_cached("population-census.json") or {}
        for doc in (cn, ev):
            for c in doc.get("classes") or []:
                c["cn"] = CLASS_CN.get(c.get("id"), c.get("id"))
        return jsonify({"ok": True, "tab": tab, "cn": cn, "everloot": ev})

    if tab == "macros":
        rows = (_load_json_cached("macros.json") or {}).get("macros") or []
        if cls:
            rows = [r for r in rows if (r.get("classId") or "").lower() == cls]
        if q:
            rows = [r for r in rows if q in json.dumps(r, ensure_ascii=False).casefold()]
        return jsonify({"ok": True, "tab": tab, "total": len(rows), "rows": rows[offset:offset + limit]})

    if tab == "spells":
        rows = (_load_json_cached("spells.json") or {}).get("spells") or []
        if cls:
            rows = [r for r in rows if (r.get("classId") or "").lower() == cls]
        if q:
            rows = [r for r in rows if q in json.dumps(r, ensure_ascii=False).casefold()]
        return jsonify({"ok": True, "tab": tab, "total": len(rows), "rows": rows[offset:offset + limit]})

    return jsonify({"ok": False, "error": f"未知浏览标签：{tab}"}), 400


@bp.route("/api/forever/icon/<path:name>")
def api_forever_icon(name: str):
    """提供 Mac 本地已同步的魔兽无限图标（严禁外链，仅读本地目录）。"""
    safe = pathlib.Path(name).name
    if not safe or safe != name:
        return jsonify({"ok": False, "error": "非法文件名"}), 400
    icons_dir = _app_data_dir().parent / "img" / "icons"
    if not safe.endswith((".jpg", ".png", ".webp")):
        for ext in (".jpg", ".png", ".webp"):
            if (icons_dir / f"{safe}{ext}").is_file():
                safe = f"{safe}{ext}"
                break
    target = icons_dir / safe
    if not target.is_file():
        return ("", 404)
    return send_from_directory(str(icons_dir), safe, max_age=86400)
