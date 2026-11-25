#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""today_ningjing.py — 将「今日选题」素材/整合稿一键编译为「宁静之光风格」双皮肤图文包与公众号内联排版

工作流：
1. 读取今日选题关联的视频正文/转写（含已勾选的补充资料与已有整合稿），过 term_glossary 同音字纠错；
2. 从 wow-forever 真源数据提取实名线索与高清图标候选（职业、副本、技能、物品、套装）；
3. 调用 DeepSeek / OpenAI 兼容模型按「短叙事正文 + 模块化毛玻璃信息卡」双轨结构生成 JSON；
4. 交给 ningjing_studio.render_pack() 一次性渲染：
   - carousel/slide_01..NN.png（1080×1440 3:4 小绿书/头条图包）+ caption.txt
   - wechat/card_01..MM.png（去顶底栏 1080px 内嵌卡）+ article.html（双色语义高亮 + 一键推草稿箱）
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import ningjing_studio

try:
    from . import talent_vision
except Exception:
    talent_vision = None


def _find_v2t_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    if here.parent.name == "src":
        return here.parents[1]
    return pathlib.Path.home() / "Documents/project/video2text"


def _parse_llm_json(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    start = raw.find("{")
    if start < 0:
        return {}
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(raw[start:], start):
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            in_str = not in_str
        elif not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start : i + 1])
                    except Exception:
                        return {}
    return {}


def gather_topic_materials(
    db_path: pathlib.Path,
    *,
    video_ids: Optional[List[int]] = None,
    summary_id: Optional[int] = None,
    supplement_ids: Optional[List[int]] = None,
    title: str = "",
) -> Dict[str, Any]:
    """收集今日选题对应的全部有效文本材料并做确定性同音纠错。"""
    v_ids: List[int] = []
    for x in (video_ids or []) + (supplement_ids or []):
        try:
            xi = int(x)
            if xi not in v_ids:
                v_ids.append(xi)
        except (TypeError, ValueError):
            pass

    summary_doc = None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if summary_id:
            row = conn.execute("SELECT * FROM ai_summaries WHERE id = ?", (int(summary_id),)).fetchone()
            if row:
                summary_doc = dict(row)
                try:
                    src_ids = json.loads(row["source_video_ids"] or "[]")
                except Exception:
                    src_ids = []
                if not src_ids and row["video_id"]:
                    src_ids = [row["video_id"]]
                for xi in src_ids:
                    if int(xi) not in v_ids:
                        v_ids.append(int(xi))

        videos: List[Dict[str, Any]] = []
        if v_ids:
            ph = ",".join("?" for _ in v_ids)
            rows = conn.execute(f"SELECT * FROM videos WHERE id IN ({ph})", v_ids).fetchall()
            by_id = {int(r["id"]): dict(r) for r in rows}
            videos = [by_id[vid] for vid in v_ids if vid in by_id]
    finally:
        conn.close()

    # 同音字清洗
    try:
        from . import term_glossary
        def _clean(txt: str, ctx: str) -> str:
            t1, _ = term_glossary.apply_confirmed(txt or "")
            return term_glossary.normalize_wow(t1, ctx or title)
    except Exception:
        def _clean(txt: str, ctx: str) -> str:
            return str(txt or "")

    sources_meta: List[str] = []
    blocks: List[str] = []
    for idx, v in enumerate(videos, 1):
        vt = _clean(v.get("title") or "", title)
        vb = _clean(v.get("transcript") or "", f"{title} {vt}")
        author = (v.get("author") or "未知作者").strip()
        sheet = (v.get("source_sheet") or "视频素材").strip()
        pub = (v.get("published_at") or "").strip()[:10]
        sources_meta.append(" · ".join(x for x in (author, sheet, pub) if x))
        blocks.append(f"【素材 {idx}】标题：{vt}\n作者：{author}（{sheet} {pub}）\n正文：\n{vb[:5500]}")

    summary_block = ""
    if summary_doc:
        sc = _clean(summary_doc.get("content") or "", title)
        summary_block = f"\n【已有整理稿参考】\n标题：{_clean(summary_doc.get('title') or '', title)}\n{sc[:5000]}"

    return {
        "title": _clean(title or (summary_doc or {}).get("title") or (videos[0].get("title") if videos else "无限服动态"), title),
        "videos": videos,
        "summary": summary_doc,
        "sources_meta": sources_meta or ["公开视频与社区动态整理"],
        "context_text": "\n\n".join(blocks) + summary_block,
    }


def _match_hero_art(app_root: pathlib.Path, hint_text: str) -> pathlib.Path:
    """根据文章主题精准匹配零商标 Logo 的本地高清原画底板，确保封面与主题强贴合。"""
    txt = hint_text or ""

    def _pick(rel: str) -> Optional[pathlib.Path]:
        p = app_root / rel
        return p if p.is_file() else None

    # 1. 多职业 / 全职业总览（避免被某个单一职业词劫持，按子主题区分锻造大厅 vs 英雄雕像）
    is_multi_class = any(k in txt for k in ("全职业", "九职业", "九大职业", "9大职业", "9职业", "各职业"))
    is_craft_or_gear = any(k in txt for k in ("制造业", "锻造", "裁缝", "制皮", "工程", "团本套装", "套装", "配装", "BiS", "铁炉堡", "熔炉", "专家级"))
    if is_multi_class:
        if is_craft_or_gear and _pick("img/art/scenes/tielu-dadian.webp"):
            return _pick("img/art/scenes/tielu-dadian.webp")
        if _pick("img/art/factions/city-alliance.webp"):
            return _pick("img/art/factions/city-alliance.webp")

    # 2. 制造业 / 锻造 / 团本套装 / 装备打造（铁炉堡熔炉大殿，炽金氛围）
    if is_craft_or_gear and _pick("img/art/scenes/tielu-dadian.webp"):
        return _pick("img/art/scenes/tielu-dadian.webp")

    # 3. 单职业主题（仅当文章聚焦某一个职业时使用该职业专属高清原画）
    class_map = [
        (("猎人", "宝宝", "兽王", "生存猎", "射击猎"), "img/art/classbanners/hunter.webp"),
        (("圣骑士", "防骑", "惩戒骑", "奶骑"), "img/art/classbanners/paladin.webp"),
        (("萨满", "增强萨", "元素萨", "奶萨"), "img/art/classbanners/shaman.webp"),
        (("战士", "防战", "狂暴战", "武器战"), "img/art/classbanners/warrior.webp"),
        (("牧师", "暗牧", "戒律牧", "神牧"), "img/art/classbanners/priest.webp"),
        (("法师", "冰法", "火法", "奥法"), "img/art/classbanners/mage.webp"),
        (("术士", "痛苦术", "毁灭术", "恶魔术"), "img/art/classbanners/warlock.webp"),
        (("盗贼", "潜行者", "战斗贼", "刺杀贼"), "img/art/classbanners/rogue.webp"),
        (("德鲁伊", "野德", "熊坦", "猫德", "鸟德", "奶德"), "img/art/classbanners/druid.webp"),
    ]
    matched_classes = [rel for kws, rel in class_map if any(kw in txt for kw in kws)]
    if len(matched_classes) == 1 and _pick(matched_classes[0]):
        return _pick(matched_classes[0])

    # 4. 种族专篇（零 Logo 种族原画）
    race_map = [
        (("天裔",), "img/art/races/skyborne.webp"),
        (("矮人",), "img/art/races/dwarf.webp"),
        (("兽人",), "img/art/races/orc.webp"),
        (("亡灵",), "img/art/races/undead.webp"),
        (("暗夜精灵",), "img/art/races/night-elf.webp"),
        (("牛头人",), "img/art/races/tauren.webp"),
        (("巨魔",), "img/art/races/troll.webp"),
        (("侏儒",), "img/art/races/gnome.webp"),
    ]
    for kws, rel in race_map:
        if any(kw in txt for kw in kws) and _pick(rel):
            return _pick(rel)

    # 5. 阵营 / 主城 / 人口普查
    if any(k in txt for k in ("部落", "奥格瑞玛")) and _pick("img/art/factions/city-horde.webp"):
        return _pick("img/art/factions/city-horde.webp")
    if any(k in txt for k in ("联盟", "暴风城", "人口普查", "排行")) and _pick("img/art/factions/city-alliance.webp"):
        return _pick("img/art/factions/city-alliance.webp")

    # 6. 自然/海加尔/采集 vs 副本/遗迹/隐藏任务/练级 vs 云海浮空
    if any(k in txt for k in ("海加尔", "自然", "草药", "翡翠", "森林", "精灵")) and _pick("img/art/scenes/guangshu.webp"):
        return _pick("img/art/scenes/guangshu.webp")
    if any(k in txt for k in ("副本", "地下城", "黑石", "遗迹", "隐藏任务", "跑本", "练级", "传承", "达拉然", "死亡矿井", "领主大厅", "洛丹伦", "黑喉", "血色", "通灵", "斯坦索姆")) and _pick("img/art/scenes/gulin.webp"):
        return _pick("img/art/scenes/gulin.webp")
    if any(k in txt for k in ("云海", "浮空", "飞行", "坐骑")) and _pick("img/art/scenes/yunhai.webp"):
        return _pick("img/art/scenes/yunhai.webp")

    for fallback in ("img/art/scenes/gulin.webp", "img/art/scenes/tielu-dadian.webp", "img/art/scenes/guangshu.webp", "img/art/scenes/yunhai.webp"):
        if _pick(fallback):
            return _pick(fallback)
    raise FileNotFoundError("未找到可用的本地原画底板")


_QUALITY_CN = {
    "epic": "史诗", "rare": "精良", "uncommon": "优秀", "common": "普通", "poor": "粗糙", "legendary": "传说",
    "5": "传说", "4": "史诗", "3": "精良", "2": "优秀", "1": "普通", "0": "粗糙",
}

_FALLBACK_ICON_RULES: List[tuple] = [
    # 1. 具体护甲部位 + 护甲类型（优先于泛职业名，确保装备 Tooltip 图标贴合部位）
    (("手套", "护手", "手甲", "手铠", "手部"), "inv_gauntlets_17.jpg"),
    (("护肩", "肩铠", "肩甲", "肩部", "披风"), "inv_shoulder_23.jpg"),
    (("护腿", "长裤", "腿铠", "腿部", "裤子"), "inv_pants_plate_05.jpg"),
    (("长靴", "战靴", "靴子", "鞋子", "脚部"), "inv_boots_plate_03.jpg"),
    (("头盔", "头冠", "兜帽", "头部"), "inv_helmet_02.jpg"),
    (("胸甲", "战甲", "战铠", "法衣", "外衣", "长袍", "胸部"), "inv_chest_armor_dwarfc60_d_02.jpg"),
    # 2. 专业与材料
    (("锻造",), "trade_blacksmithing.jpg"),
    (("裁缝",), "trade_tailoring.jpg"),
    (("制皮",), "trade_leatherworking.jpg"),
    (("工程",), "trade_engineering.jpg"),
    (("配方", "设计图", "图样"), "inv_scroll_06.jpg"),
    (("精华", "自然抗", "材料"), "inv_misc_gem_emerald_01.jpg"),
    # 3. 九大职业图标
    (("战士", "防战", "狂暴战", "武器战", "荣耀战"), "classicon_warrior.jpg"),
    (("圣骑士", "防骑", "奶骑", "惩戒", "正义护", "正义战"), "classicon_paladin.jpg"),
    (("猎人", "兽王", "生存猎", "野蛮猎"), "classicon_hunter.jpg"),
    (("潜行者", "盗贼", "刺杀", "战斗贼"), "classicon_rogue.jpg"),
    (("牧师", "暗牧", "戒律", "神牧", "信念法衣", "信念外衣"), "classicon_priest.jpg"),
    (("萨满", "增强萨", "元素萨", "奶萨", "唤灵者"), "classicon_shaman.jpg"),
    (("法师", "冰法", "火法", "奥法", "法力闪焰"), "classicon_mage.jpg"),
    (("术士", "痛苦术", "毁灭术", "恶魔术"), "classicon_warlock.jpg"),
    (("德鲁伊", "熊坦", "猫德", "野德", "鸟德", "奶德", "丛林守护"), "classicon_druid.jpg"),
]

_SLOT_ARMOR_ICON = {
    ("腿", "布甲"): "inv_pants_cloth_05.jpg",
    ("腿", "皮甲"): "inv_pants_leather_05.jpg",
    ("腿", "锁甲"): "inv_pants_mail_04.jpg",
    ("腿", "板甲"): "inv_pants_plate_05.jpg",
    ("脚", "布甲"): "inv_boots_cloth_05.jpg",
    ("靴", "布甲"): "inv_boots_cloth_05.jpg",
}


def _resolve_icon_uri(app_root: pathlib.Path, icon_name: str, v2t_icons: Any) -> str:
    if not icon_name:
        return ""
    name_str = str(icon_name).strip()
    if v2t_icons is not None:
        meta = v2t_icons.card_visual(name_str)
        p = v2t_icons.visual_path("icons", meta.get("icon"))
        if p:
            return p.as_uri()
        exact, uniq = v2t_icons._load()
        f = uniq.get(name_str)
        if not f:
            for k, val in exact.items():
                if k.endswith("|" + name_str):
                    f = val
                    break
        if f:
            p2 = v2t_icons.visual_path("icons", f)
            if p2:
                return p2.as_uri()

    # 护甲类型+部位精准回退
    for (slot_kw, armor_kw), fname in _SLOT_ARMOR_ICON.items():
        if slot_kw in name_str and armor_kw in name_str:
            pf = app_root / "img" / "icons" / fname
            if pf.is_file():
                return pf.as_uri()

    # 部位 / 专业 / 九职业语义回退（保证 icon_rows 与 item_tooltips 零空白图标）
    for kws, fname in _FALLBACK_ICON_RULES:
        if any(kw in name_str for kw in kws):
            pf = app_root / "img" / "icons" / fname
            if pf.is_file():
                return pf.as_uri()
    return ""


# 来自国服客户端 1.60.1 DB2 / 无限图鉴 / wclbox-world 已逐字核实的非装备类特色物品与隐藏任务（严禁编造数值）
VERIFIED_CLIENT_ITEMS: List[Dict[str, Any]] = [
    {
        "id": 221315,
        "name": "旅行者标志",
        "aliases": ("旅行者标志", "旅行者印记"),
        "quality": "精良",
        "ilvl": 60,
        "bind": "拾取后绑定",
        "unique": "唯一",
        "slot_type": "物品 · 玩具",
        "stats": [],
        "use_lines": [
            "使用：放置一个持续1分钟的旅行者印记。可以在标牌上写下信息，使其持续1小时，并对其他玩家可见。（30分钟冷却）",
        ],
        "flavor": "",
        "source": "黑石深渊隐藏对话（沧桑的旅行者）",
        "meta_right": "售价 46银 18铜",
        "icon_file": "inv_misc_note_05.jpg",
    },
    {
        "id": 216619,
        "name": "混调干果",
        "aliases": ("混调干果", "混条干果"),
        "quality": "优秀",
        "ilvl": 33,
        "bind": "拾取后绑定",
        "unique": "堆叠上限 30",
        "slot_type": "消耗品 · 其它",
        "stats": [],
        "use_lines": [
            "使用：满满吃上一捧，弥补消磨在赶路上的时间！（5分钟冷却，法术：方便零嘴）",
            "实测机制：战斗中可用，持续按比例恢复生命值及怒气、能量或法力值",
        ],
        "flavor": "“经典的葡萄干和花生……以及其他美味！”",
        "source": "任务奖励：从此以后（#82062）×3",
        "meta_right": "无限服无双倍经验条效果",
        "icon_file": "inv_misc_food_pinenut.jpg",
    },
    {
        "id": 221316,
        "name": "普拉莫的苛求体态制服",
        "aliases": ("普拉莫的苛求体态制服", "普拉莫的科球体台制服", "普拉莫"),
        "quality": "普通",
        "ilvl": 55,
        "bind": "拾取后绑定",
        "unique": "唯一",
        "slot_type": "衬衫（不占护甲属性栏）",
        "stats": [],
        "use_lines": [
            "使用：专注。（无冷却时间，点击后立刻将角色朝向/视角转向当前目标）",
        ],
        "flavor": "",
        "source": "任务奖励：从此以后（#82062 · 56级）",
        "meta_right": "售价 71银 37铜",
        "icon_file": "inv_shirt_black_01.jpg",
    },
]

def _item_icon_uri(app_root: pathlib.Path, icon_file: str, item_name: str, v2t_icons: Any) -> str:
    if icon_file:
        p = app_root / "img" / "icons" / icon_file
        if p.is_file():
            return p.as_uri()
        if not icon_file.endswith((".jpg", ".png", ".webp")):
            for ext in (".jpg", ".png", ".webp"):
                p2 = app_root / "img" / "icons" / f"{icon_file}{ext}"
                if p2.is_file():
                    return p2.as_uri()
    return _resolve_icon_uri(app_root, item_name, v2t_icons)


def _match_verified_items(app_root: pathlib.Path, raw_text: str, v2t_icons: Any = None) -> List[Dict[str, Any]]:
    """提取文本中命中的真实游戏物品 Tooltip（仅取已核实 DB2 / items-detail 字段）。"""
    matched: List[Dict[str, Any]] = []
    seen_ids = set()

    for tpl in VERIFIED_CLIENT_ITEMS:
        if any(al in raw_text for al in tpl["aliases"]):
            obj = {k: v for k, v in tpl.items() if k not in ("aliases", "icon_file")}
            obj["stats"] = list(tpl["stats"])
            obj["use_lines"] = list(tpl["use_lines"])
            obj["icon_uri"] = _item_icon_uri(app_root, tpl.get("icon_file") or "", tpl["name"], v2t_icons)
            matched.append(obj)
            seen_ids.add(str(tpl["id"]))

    try:
        items_doc = json.loads((app_root / "data/items.json").read_text(encoding="utf-8")).get("items") or []
        det_doc = json.loads((app_root / "data/items-detail.json").read_text(encoding="utf-8")).get("items") or {}
    except Exception:
        items_doc, det_doc = [], {}

    for it in items_doc:
        nm = (it.get("name") or "").strip()
        iid = str(it.get("id") or "")
        if len(nm) < 4 or iid in seen_ids or nm not in raw_text:
            continue
        d = det_doc.get(iid) or {}
        st_lines = [str(s) for s in (d.get("st") or []) if str(s).strip()]
        use_lines = [s for s in st_lines if s.startswith(("使用：", "装备：", "击中时可能："))]
        if d.get("use") and d["use"] not in use_lines:
            use_lines.append(str(d["use"]))
        other_stats = [s for s in st_lines if s not in use_lines]
        if not other_stats and not use_lines:
            continue
        slot_val = (it.get("slot") or it.get("typeMain") or "").strip()
        if slot_val in ("材料", "任务", "其它") and not use_lines:
            continue
        icon_f = (it.get("icon") or "").strip()
        raw_q = it.get("quality") if it.get("quality") is not None else it.get("q")
        matched.append({
            "id": int(iid) if iid.isdigit() else iid,
            "name": nm,
            "quality": _QUALITY_CN.get(str(raw_q if raw_q is not None else "").lower(), str(raw_q or "")),
            "ilvl": it.get("ilvl") or d.get("ilvl") or "",
            "bind": d.get("bind") or "",
            "unique": "",
            "slot_type": it.get("slot") or it.get("typeMain") or "",
            "req_level": f"需要等级 {d['req']}" if d.get("req") else "",
            "stats": other_stats[:5],
            "use_lines": use_lines[:3],
            "flavor": "",
            "source": " / ".join(it.get("src") or [])[:48],
            "meta_right": f"售价 {d['sell']}" if d.get("sell") else "",
            "icon_uri": _item_icon_uri(app_root, icon_f, nm, v2t_icons),
        })
        seen_ids.add(iid)
        if len(matched) >= 6:
            break

    return matched


_OCR_INFO_KWS = (
    "护甲", "耐力", "智力", "力量", "敏捷", "精神", "物品等级", "装备：", "使用：", "组合：",
    "冷却", "抗性", "法术", "防御提高", "攻击强度", "专家级", "配方", "设计图", "蓝帖",
    "热修复", "暴雪", "Wowhead", "需要等级", "爆击", "命中", "治疗效果", "伤害提高",
)
_OCR_NOISE_RE = re.compile(
    r"^(?:\d{1,2}:\d{2}|\d+/\d+.*|\d+(?:\.\d+)?%.*|离开战斗|等級\s*\d+|通[緩購缓购].*|[0-9.\s%()（）/]+)$"
)


def _extract_frame_ocr_context(
    videos: List[Dict[str, Any]],
    v2t_root: pathlib.Path,
    *,
    max_chars: int = 10500,
) -> str:
    """复用本地零成本 Apple Vision OCR 缓存，提取视频画面里展示的真实装备属性、套装、技能与蓝帖文字。"""
    if talent_vision is None:
        return ""
    ocr_script = v2t_root / "scripts" / "read_frame_text.swift"
    if not ocr_script.is_file():
        return ""

    blocks: List[str] = []
    seen_sigs = set()
    used_chars = 0

    for v in videos or []:
        aid = str(v.get("aweme_id") or "").strip()
        if not aid:
            continue
        fdir = v2t_root / "output" / "assets" / "frames" / aid
        raw_dir = fdir / "raw"
        if not raw_dir.is_dir():
            continue
        jpgs = sorted(raw_dir.glob("*.jpg"))
        if not jpgs:
            continue
        ocr_map = talent_vision._ocr_frames_cached(jpgs, fdir / "ocr_talent_cache.json", ocr_script)
        for p in jpgs:
            lines = ocr_map.get(str(p)) or []
            if not lines:
                continue
            blob = " ".join(lines)
            score = sum(1 for kw in _OCR_INFO_KWS if kw in blob)
            if score < 2:
                continue
            cleaned: List[str] = []
            for ln in lines:
                s = str(ln).strip()
                if len(s) < 2 or _OCR_NOISE_RE.match(s) or "Questie" in s or "Ouestle" in s:
                    continue
                cleaned.append(s)
            if len(cleaned) < 4:
                continue
            joined = " | ".join(cleaned)
            sig = joined[:90]
            if sig in seen_sigs:
                continue
            seen_sigs.add(sig)
            entry = f"[画面 {p.name}] {joined[:760]}"
            if used_chars + len(entry) > max_chars:
                break
            blocks.append(entry)
            used_chars += len(entry)

    if not blocks:
        return ""
    return (
        "\n\n【视频画面实拍提取的装备属性/技能/蓝帖界面文字（本地OCR，可能有极少繁简/形近错字如剔造=制造、法鄰=法师、宋耀=荣耀、烘定=绑定、几事=几率，请结合下方数据库实名校正，但严禁编造画面外数值）】：\n"
        + "\n".join(blocks)
    )


def _verified_db_hints(app_root: pathlib.Path, raw_text: str) -> str:
    """从 wow-forever 真源库提取命中本素材的实名事实参考，供 LLM 校验专有名词、纠正语音/OCR误听。"""
    hints: List[str] = []
    try:
        items_doc = json.loads((app_root / "data/items.json").read_text(encoding="utf-8"))["items"]
        det_doc = json.loads((app_root / "data/items-detail.json").read_text(encoding="utf-8"))["items"]
        dungeons_doc = json.loads((app_root / "data/dungeons.json").read_text(encoding="utf-8"))
        bis_doc = json.loads((app_root / "data/bis.json").read_text(encoding="utf-8"))
        spells_doc = json.loads((app_root / "data/spells.json").read_text(encoding="utf-8")).get("spells") or []
    except Exception:
        items_doc, det_doc, dungeons_doc, bis_doc, spells_doc = [], {}, {}, {}, []

    # 1. 副本实名与等级区间
    for d in (dungeons_doc.get("newDungeons") or []) + (dungeons_doc.get("classicDungeons") or []):
        nm = d.get("nameCn") or ""
        if nm and nm in raw_text:
            hints.append(f"副本：{nm}（推荐 {d.get('levelRange') or '--'} 级，位于 {d.get('zoneCn') or '--'}）")

    # 1b. 海加尔 T1 团本套装官方正名（18套，用于纠正视频 OCR 里的错字如 宋耀->荣耀、野遢->野蛮）
    raid_sets = bis_doc.get("raidSets") or []
    if raid_sets and any(k in raw_text for k in ("团本套装", "团统套装", "专家级", "海加尔", "荣耀战", "正义护", "法力闪焰", "信念法衣", "丛林守护", "野蛮猎", "唤灵者")):
        set_summary = "；".join(
            f"{rs.get('clsCn')}({rs.get('spec')}):{rs.get('name')}[{rs.get('armor')}]"
            for rs in raid_sets
        )
        hints.append(f"本站已登记海加尔峰首套团本套装（18套官方中文名）：{set_summary}")

    # 1c. 36 套无限新增/地下城套装命中
    for iset in (bis_doc.get("itemSets") or []):
        snm = (iset.get("nameCn") or "").strip()
        if len(snm) >= 3 and snm in raw_text:
            hints.append(f"套装：{snm}（{iset.get('level') or '--'}级，{iset.get('pieceCount') or '--'}件套）")

    # 1d. 技能书精准命中（附真实职业与技能说明）
    spell_hits = 0
    for sp in spells_doc:
        snm = (sp.get("nameCn") or sp.get("name") or "").strip()
        if len(snm) >= 3 and snm in raw_text:
            desc = str(sp.get("desc") or sp.get("summary") or "")[:70]
            hints.append(f"技能：{snm}（{sp.get('classCn') or sp.get('classId') or '--'} · {desc}）")
            spell_hits += 1
            if spell_hits >= 5:
                break

    # 2. 海加尔邮政背包等关键任务背包（防 ASR 把 18 格听成 48 格）
    if "背包" in raw_text or "海加尔" in raw_text:
        it_bag = next((x for x in items_doc if str(x.get("id")) == "260307"), None)
        if it_bag:
            st = (det_doc.get("260307") or {}).get("st") or []
            hints.append(f"物品：{it_bag['name']}（{' / '.join(st)}，卖价 {(det_doc.get('260307') or {}).get('sell') or '--'}）")

    # 3. 黑石深渊隐藏任务 #82062 与沧桑的旅行者标准名
    if "从此以后" in raw_text or "旅行者" in raw_text or "黑石深渊" in raw_text:
        hints.append(
            "任务：从此以后（ID #82062，黑石深渊 56 级任务 / 48 级可接，与「沧桑的旅行者」交谈；"
            "奖励 8395 经验、85 银、四大主城声望 +300、普拉莫的苛求体态制服、混调干果×3，另有玩具旅行者标志）；"
            "NPC 附近路线涉及「宝库傀儡」与天裔翼落/缓落/漂浮/降落伞跳桥"
        )

    # 4. 命中物品的完整游戏内属性 Tooltip
    for it in _match_verified_items(app_root, raw_text):
        parts = [
            f"ID {it['id']}" if it.get("id") else "",
            f"品质:{it['quality']}" if it.get("quality") else "",
            f"装等:{it['ilvl']}" if it.get("ilvl") else "",
            it.get("bind") or "",
            it.get("unique") or "",
            it.get("slot_type") or "",
            " / ".join(it.get("stats") or []),
            " / ".join(it.get("use_lines") or []),
            it.get("flavor") or "",
            it.get("meta_right") or "",
            it.get("source") or "",
        ]
        hints.append(f"游戏内真实物品「{it['name']}」：" + " ｜ ".join(p for p in parts if p))

    # 5. 高频专名提醒
    if "猎人" in raw_text or "断牙" in raw_text or "断崖" in raw_text:
        hints.append("猎人经典1.0攻速宠物标准名：断牙（荒芜之地稀有豹，非'断崖'）；可与海加尔山新1.0攻速豹对比")

    return "\n".join(f"- {h}" for h in hints[:20])


def _build_llm_prompt(topic_title: str, context_text: str, db_hints: str = "") -> str:
    hints_block = f"\n【本站数据库已核实名参考（遇到同音错听以此为准）】：\n{db_hints}\n" if db_hints else ""
    return f"""你是「宁静之光」风格的魔兽世界（无限服）资深编辑与信息图表设计师。
请严格基于下方【输入素材】与【数据库实名参考】，不要编造任何未出现的数字、掉落几率、时间或官方未宣布的机制，把选题编译成一套「宁静风双轨内容 JSON」——同时用于渲染 3:4 轮播图卡和公众号内联长文。

【输入选题】：{topic_title}
{hints_block}
【硬性纪律】：
1. **绝对忠于事实 + 过滤语音同音错听**：
   - 只写素材里有依据的事实、数字、等级与结论；如果是第三方主播经验或怀疑（如“疑似触发概率高”），必须保留“按主播实测分享/疑似”，不得写成官方结论。
   - **识别并规避 ASR 错听专名**：语音转写常把地名/物品名听歪（如“孤雾大名”“独词”“藏兵武器”“48个背包”“保库亏雷”“苍丝的旅行者”“天意”“普拉莫的科球体台制服”实为“18格背包”“宝库傀儡”“沧桑的旅行者”“天裔”“普拉莫的苛求体态制服”）。若某词明显是同音错写，必须对照上方【数据库已核实名参考】或语境还原正确名称，**绝不能把明显错别字印上大图**！
2. **禁止内部术语与敷衍省略**：
   - 读者可见文字中严禁出现「口播」「转写」「ASR」「视频1」「整理稿」「素材未提」「素材原话」「素材标题」「待核实」等编辑内部字眼；
   - **绝对禁止写「视频中展示，此处略」「详见视频」「请看画面」这类空话**！只要【视频画面实拍提取】或【数据库已核实名参考】里有具体装备名、护甲/属性数值、套装部件或技能效果，必须如实结构化呈现出来。
3. **正文与图卡互补（拒绝纯文字复读，必须配游戏装备框与图标）**：
   - `prose_sections`：写 **1~2 段克制流畅的叙事正文**（每段 45~120 字），重点定性词用 `**词组**` 包裹（染暗金色），重点数字/等级/人数/属性用 `!!数字!!` 包裹（染橙红色）。
   - **当主题涉及具体装备、套装、任务奖励或神器物品时**（无论来自上方【数据库已核实名参考】还是【视频画面实拍提取】）：
     - 必须专门设计 **2~4 张 `item_tooltips` 真实装备属性卡**（每张卡放 **2 件**装备框 + 1 条简短 `quote`，或放 **1 件**装备框 + `icon_rows`/`pill_rows`），把**物品实名、品质（如 史诗/精良）、装等、绑定/唯一限制（如 装备唯一：专家级(1)）、部位与护甲类型（如 手部 · 布甲）、全部白字基础属性（如 `58 护甲`、`+12 耐力`、`+14 智力`、`+7 自然抗性`）与 `装备：`/`使用：` 绿字效果**完整填入 `stats` 与 `use_lines`；
     - 若涉及多职业套装全览（如全职业团本 T1），用 **2~3 张 `item_tooltips` 卡展示代表性职业散件实装属性**，再用 **1~2 张 `icon_rows` 卡按职业/专精列出其余职业核心定位与图标**（`icon_query` 填纯职业/部位/专业实名如 `法师`、`战士`、`圣骑士`、`牧师`、`德鲁伊`、`猎人`、`萨满`、`锻造`、`裁缝`、`制皮`），确保整套图包既有真实装备属性又有游戏图标，绝不退化成纯文字清单！
   - `cards`：**每张普通卡片包含至少 2 个组件块**（例如 `kpis` + `icon_rows` + `quote`，或 2 件 `item_tooltips` + `quote`），保证 `3:4` 竖版卡片画面饱满（占画高 65%~85%），不要只放 1 块留下半截大黑底！
4. **卡片版式多样性（常规选题 4~5 张信息卡；多职业套装/装备全览可放 5~7 张信息卡，相邻卡片变换版式）**：
   每张信息卡可组合以下字段：
   - `kpis`: 最多 3 项三列数字看板 `[{{"val":"50-57级","label":"海山入门怪等级"}}, ...]`（每项 val ≤6 字，label ≤10 字）
   - `stat_change`: 单条核心变化对比 `{{"name":"魂铸套","sub":"坦克向调整","before":"力量","after":"法术强度"}}`
   - `hero_stat`: 醒目大数字 `{{"num":"1.0","unit":"秒攻速","desc":"海加尔山新猎人宠物亮点"}}`
   - `item_tooltips`: 游戏内真实物品属性卡组：若单张卡仅放 **1 件** `item_tooltips`，**必须额外搭配** `pill_rows`（2~3 条实战用法/场景/获取贴士）或 `kpis` + `quote`，保证 `3:4` 竖版画面饱满不留大黑底；若同卡放 2~3 件物品则仅配 `quote` 防溢出 `[{{"id":221315,"name":"物品实名","quality":"精良","ilvl":60,"bind":"拾取后绑定","unique":"唯一","slot_type":"物品 · 玩具","stats":[],"use_lines":["使用：..."],"flavor":"","source":"出处","meta_right":"售价 46银 18铜"}}]`
   - `icon_rows`: 2~4 条带游戏图标的条目 `[{{"title":"技能/物品/地点名","icon_query":"用于查图标的纯游戏实名（如 召唤雄鹰/风怒图腾/黑喉要塞/塑源者平台/战歌峡谷）","badge":"4字标签","desc":"一句话说明（≤32字）"}}]`
   - `pill_rows`: 2~4 条胶囊分类列表 `[{{"tag":"4字标签","tone":"brown或green或blue","title":"主标题（≤22字）","sub":"补充说明（≤28字）"}}]`
   - `timeline`: 2~4 个纵向阶段节点 `[{{"time":"阶段/日期","title":"节点标题","desc":"简短说明","color":"#E5B869或#52B788或#4EA1E8"}}]`
   - `compare_boxes`: 2 栏横向对比 `[{{"label":"一方","text":"要点","color":"#639BFF"}}, {{"label":"另一方","text":"要点","color":"#E05A47"}}]`
   - `q_rows`: 2~3 条待解问题或清单 `[{{"symbol":"?","title":"问题/要点","desc":"简短解释"}}]`
   - `summary`: 1 句总结语（≤45 字，可选）
   - `quote`: 金线引用 `{{"text":"金句或实操结论（≤35字）","note":"补充注解（≤25字）"}}`（强烈建议短卡底部都配一条 `quote`，压住视觉重心）
5. **标题长度限制（微信草稿箱硬上限）**：`title` 必须 **≤ 28 个汉字**，精炼有吸引力。

【严格输出如下 JSON】（不要输出多余解释）：
{{
  "title": "主标题（≤28字）",
  "column_name": "无限服日报 或 无限服攻略（二选一）",
  "hero_hint": "最贴切主题的2-4字游戏关键词（如 猎人 / 达拉然 / 战士 / 黑上）",
  "lead_text": "1句话导语钩子（≤55字）",
  "cover": {{
    "kicker": "栏目小标签 · 今日速览",
    "title_line1": "封面大标题第一行（≤9字）",
    "title_line2": "封面大标题第二行（≤9字）",
    "subtitle": "副标题一句话（≤22字）"
  }},
  "cards": [
    {{
      "title_line1": "卡片1主标题第一行（≤10字）",
      "title_line2": "卡片1主标题第二行（≤11字，可选）",
      "kpis": [{{"val": "数值", "label": "说明"}}],
      "pill_rows": [{{"tag": "标签", "tone": "green", "title": "要点", "sub": "说明"}}],
      "quote": {{"text": "核心提醒", "note": "补充依据"}}
    }}
  ],
  "prose_sections": [
    {{
      "title": "第1节小标题（≤20字）",
      "paragraphs": ["第一段叙事正文，**定性重点**与!!定量数字!!。", "第二段补充，自然引出下方图卡。"],
      "card_index": 1
    }}
  ],
  "closing_lines": ["四字或六字短句1，", "短句2，", "短句3，", "短句4。"],
  "footnote": "注：本文整理自公开视频与社区分享，具体数值与机制请以游戏内实装与官方公告为准。",
  "caption_text": "200字左右小绿书/头条配文（文末自然带一句双端工具引导：手机搜「跑本无限助手」小程序、电脑开 paoben.top 查完整配装/副本/天赋）+ 文末5个#话题标签"
}}

【注意】：`prose_sections` 的数量必须与 `cards` 数量**严格一一对应**（常规 4~5 节，多职业套装/装备全览 5~7 节），第 `i` 节的 `prose_sections[i-1]` 必须写第 `i` 张卡 `cards[i-1]` 的同一主题/同一职业，`card_index` 严格等于 `1, 2, ..., N`，**绝对禁止图文错位**！

【输入素材】：
{context_text[:15500]}
"""


def generate_pack_from_today_topic(
    *,
    db_path: pathlib.Path,
    ai_config: Dict[str, str],
    out_root: pathlib.Path,
    slot_key: str,
    title: str,
    video_ids: Optional[List[int]] = None,
    summary_id: Optional[int] = None,
    supplement_ids: Optional[List[int]] = None,
    progress_cb=None,
) -> Dict[str, Any]:
    """端到端将今日选题生成宁静风双模态成品包。"""
    def _prog(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)

    _prog("正在读取选题素材并校验游戏术语...")
    gathered = gather_topic_materials(
        db_path,
        video_ids=video_ids,
        summary_id=summary_id,
        supplement_ids=supplement_ids,
        title=title,
    )
    if not gathered["context_text"].strip():
        raise RuntimeError("该选题暂无可用正文或转写素材，请先完成采集/转写。")

    _prog("正在用大模型拆解「宁静风」双轨结构（叙事正文 + 组件化图卡）...")
    import openai

    app_root = ningjing_studio._find_app_root()
    v2t_root = _find_v2t_root()
    frame_ocr_block = _extract_frame_ocr_context(gathered["videos"], v2t_root)
    full_context = gathered["context_text"] + frame_ocr_block
    db_hints = _verified_db_hints(app_root, f"{gathered['title']} {full_context}")

    # 按需检测视频帧是否包含天赋加点截图（无天赋画面则零额外大模型耗时直接跳过）
    talent_builds: List[Dict[str, Any]] = []
    if talent_vision is not None:
        try:
            talent_builds = talent_vision.extract_talent_builds_for_videos(
                gathered["videos"],
                app_root=app_root,
                ai_config=ai_config,
                v2t_root=v2t_root,
                progress_cb=_prog,
            )
        except Exception:
            talent_builds = []

    verified_tb_hints = []
    for tb in talent_builds:
        if tb.get("status") == "verified":
            kt = "、".join(tb.get("key_talents") or [])
            verified_tb_hints.append(
                f"- 视频画面已核实天赋：{tb['class_cn']}（{tb['summary_text']}，共 {tb['total_points']} 点"
                + (f"，核心深层天赋：{kt}" if kt else "")
                + "；正文将自动附带模拟器实图，请勿编造未验证的其他职业点数）"
            )
    if verified_tb_hints:
        db_hints = (db_hints + "\n" if db_hints else "") + "\n".join(verified_tb_hints)

    client = openai.OpenAI(
        api_key=ai_config["api_key"],
        base_url=ai_config.get("api_base") or "https://api.deepseek.com",
        timeout=150,
        max_retries=1,
    )
    prompt = _build_llm_prompt(gathered["title"], full_context, db_hints=db_hints)
    kwargs: Dict[str, Any] = {
        "model": ai_config.get("model") or "deepseek-v4-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    if ai_config.get("editorial"):
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

    resp = client.chat.completions.create(**kwargs)
    raw_content = resp.choices[0].message.content or ""
    parsed = _parse_llm_json(raw_content)
    if not parsed or not parsed.get("cards") or not parsed.get("prose_sections"):
        raise RuntimeError("模型未能输出有效结构化 JSON，请重试。")

    _prog("正在匹配无限服高清图标与主题原画，准备 Playwright 渲染...")
    try:
        from .graphics import icons as v2t_icons
    except Exception:
        v2t_icons = None

    date_mmdd = datetime.now().strftime("%m.%d")
    full_date = datetime.now().strftime("%Y-%m-%d")
    hint = f"{parsed.get('hero_hint') or ''} {gathered['title']} {parsed.get('title') or ''}"
    hero_art_path = _match_hero_art(app_root, hint)
    col_name = (parsed.get("column_name") or "无限服日报").strip()
    if col_name not in ("无限服日报", "无限服攻略"):
        col_name = "无限服日报"
    emblem_path = app_root / ("img/art/panels/spellbook.webp" if col_name == "无限服日报" else "img/art/panels/library.webp")

    cov = parsed.get("cover") or {}
    cards: List[Dict[str, Any]] = [
        {
            "kind": "cover",
            "kicker": cov.get("kicker") or f"{col_name} · {date_mmdd}",
            "title_line1": cov.get("title_line1") or (parsed.get("title") or gathered["title"])[:9],
            "title_line2": cov.get("title_line2") or "",
            "subtitle": cov.get("subtitle") or (parsed.get("lead_text") or "")[:24],
        }
    ]

    verified_items = _match_verified_items(
        app_root, f"{gathered['title']} {full_context}", v2t_icons
    )
    by_vid = {str(it.get("id")): it for it in verified_items if it.get("id")}
    by_vname = {it.get("name"): it for it in verified_items if it.get("name")}

    raw_cards = parsed.get("cards") or []
    placed_ids = set()
    for c in raw_cards:
        c_obj = dict(c)
        c_obj["kind"] = "info"
        c_obj.setdefault("accent", "#E5B869")
        # 为 icon_rows 挂载真实图标
        if isinstance(c_obj.get("icon_rows"), list):
            for ir in c_obj["icon_rows"]:
                if isinstance(ir, dict):
                    q_name = ir.get("icon_query") or ir.get("title") or ""
                    ir["icon_uri"] = _resolve_icon_uri(app_root, q_name, v2t_icons)
        # 校对并挂载真实游戏物品 Tooltip
        if isinstance(c_obj.get("item_tooltips"), list) and c_obj["item_tooltips"]:
            clean_tts = []
            for tt in c_obj["item_tooltips"]:
                if not isinstance(tt, dict):
                    continue
                hit = by_vid.get(str(tt.get("id") or "")) or by_vname.get(str(tt.get("name") or "").strip())
                if hit:
                    clean_tts.append(dict(hit))
                    placed_ids.add(str(hit.get("id") or hit.get("name")))
                else:
                    tt_copy = dict(tt)
                    if not tt_copy.get("icon_uri"):
                        icon_q = " ".join(
                            str(x) for x in (
                                tt_copy.get("name"),
                                tt_copy.get("slot_type"),
                                tt_copy.get("source"),
                            ) if x
                        )
                        tt_copy["icon_uri"] = _resolve_icon_uri(app_root, icon_q, v2t_icons)
                    clean_tts.append(tt_copy)
            c_obj["item_tooltips"] = clean_tts
        cards.append(c_obj)

    # 仅当模型整篇一张 item_tooltips 都没放、且命中了已核实物品时才自动补齐，避免把低关联同名旧物品硬塞进已有装备卡的封面/概览页
    has_any_tt = any(bool(c_obj.get("item_tooltips")) for c_obj in cards[1:])
    missing_tts = [it for it in verified_items if str(it.get("id") or it.get("name")) not in placed_ids]
    if (not has_any_tt) and missing_tts and len(cards) > 1:
        best_card = None
        for c_obj in cards[1:]:
            blob = json.dumps(c_obj, ensure_ascii=False)
            if any(k in blob for k in ("神器", "奖励", "物品", "装备", "干果", "制服", "标志")):
                best_card = c_obj
                break
        if best_card is None:
            best_card = cards[min(3, len(cards) - 1)]
        existing = best_card.get("item_tooltips") or []
        merged_tts = existing + [it for it in missing_tts if it not in existing]
        best_card["item_tooltips"] = merged_tts[:3]
        if len(best_card["item_tooltips"]) >= 2:
            best_card.pop("pill_rows", None)
            best_card.pop("icon_rows", None)
            best_card.pop("q_rows", None)
            best_card.pop("compare_boxes", None)

    # 规范化 prose_sections（严格对齐 1..len(raw_cards)，防止图文错位或末尾装备卡被漏掉）
    raw_secs = list(parsed.get("prose_sections") or [])
    sections = []
    used_cidx = set()
    for idx_s, sec in enumerate(raw_secs, 1):
        c_idx = int(sec.get("card_index") or idx_s)
        if c_idx < 1 or c_idx > len(raw_cards):
            c_idx = min(idx_s, len(raw_cards))
        used_cidx.add(c_idx)
        sec_tts = cards[c_idx].get("item_tooltips") if 1 <= c_idx < len(cards) else []
        sections.append({
            "title": sec.get("title") or f"要点 {idx_s}",
            "paragraphs": sec.get("paragraphs") or [],
            "card_index": c_idx,
            "item_tooltips": sec_tts or [],
        })
    for c_idx in range(1, len(raw_cards) + 1):
        if c_idx in used_cidx:
            continue
        c_obj = cards[c_idx]
        t1 = (c_obj.get("title_line1") or f"要点 {c_idx}").strip()
        t2 = (c_obj.get("title_line2") or "").strip()
        q_txt = (c_obj.get("quote") or {}).get("text") or ""
        q_note = (c_obj.get("quote") or {}).get("note") or ""
        para = "；".join(x for x in (t2, q_txt, q_note) if x) or "详见下方实装属性图卡。"
        sections.append({
            "title": t1,
            "paragraphs": [para],
            "card_index": c_idx,
            "item_tooltips": c_obj.get("item_tooltips") or [],
        })

    # 生成稳定 pack_id（today-<slot>-<date>-<hash6>）
    safe_slot = re.sub(r"[^a-zA-Z0-9_-]", "", slot_key or "topic")[:20] or "topic"
    sig = hashlib.sha1(f"{safe_slot}:{gathered['title']}".encode("utf-8")).hexdigest()[:6]
    pack_id = f"today-{safe_slot}-{datetime.now().strftime('%m%d')}-{sig}"

    final_title = (parsed.get("title") or gathered["title"]).strip()[:30]
    if talent_builds and talent_vision is not None:
        try:
            _prog("正在打开跑本无限助手天赋模拟器并截取 .tpanel 加点容器实图...")
            talent_builds = talent_vision.render_talent_panel_screenshots(
                talent_builds,
                app_root=app_root,
                wechat_dir=out_root / pack_id / "wechat",
            )
        except Exception:
            pass

    web_dom = ningjing_studio._resolve_web_domain() if hasattr(ningjing_studio, "_resolve_web_domain") else "paoben.top"
    raw_caption = (parsed.get("caption_text") or final_title).strip()
    if web_dom not in raw_caption and "跑本无限助手" not in raw_caption:
        promo_tail = f"手机微信搜「跑本无限助手」小程序，电脑双屏直接开 {web_dom} 查完整副本、配装、天赋模拟器与宏命令。"
        if "#" in raw_caption:
            idx_hash = raw_caption.find("#")
            raw_caption = raw_caption[:idx_hash].rstrip() + "\n\n" + promo_tail + "\n\n" + raw_caption[idx_hash:]
        else:
            raw_caption = raw_caption + "\n\n" + promo_tail
    elif web_dom not in raw_caption:
        promo_add = f"电脑端大屏查表与3D配装可直接访问 {web_dom}。"
        if "#" in raw_caption:
            idx_hash = raw_caption.find("#")
            raw_caption = raw_caption[:idx_hash].rstrip() + "\n" + promo_add + "\n\n" + raw_caption[idx_hash:]
        else:
            raw_caption = raw_caption + "\n" + promo_add

    spec = {
        "pack_id": pack_id,
        "theme": "frosted-daily",
        "title": final_title,
        "column_name": col_name,
        "date_str": date_mmdd,
        "source_label": " / ".join(gathered["sources_meta"][:2]),
        "hero_art_uri": ningjing_studio._file_uri(hero_art_path),
        "emblem_uri": ningjing_studio._file_uri(emblem_path),
        "lead_text": parsed.get("lead_text") or "",
        "cards": cards,
        "prose_sections": sections,
        "closing_lines": parsed.get("closing_lines") or [
            "核心看点先理清，",
            "版本细节核到位，",
            "省心跑本少踩坑，",
            "下期内容我们接着聊。",
        ],
        "footnote": parsed.get("footnote") or "注：本文整理自公开视频与社区分享，具体机制与数值请以游戏内实装与官方公告为准。",
        "sources": gathered["sources_meta"] + [
            f"电脑端资料站：{web_dom}（大屏查表、3D配装预览、12.10团本筹备与门任务打卡）",
            "微信小程序：跑本无限助手（手机随身查副本、配装、天赋模拟器与宏命令）",
        ],
        "caption_text": raw_caption,
        "talent_builds": talent_builds,
    }

    _prog(f"正在渲染 {len(cards)} 张 3:4 轮播图与公众号内联排版...")
    manifest = ningjing_studio.render_pack(spec, out_root)
    manifest["today_meta"] = {
        "slot_key": slot_key,
        "summary_id": summary_id,
        "video_ids": [v["id"] for v in gathered["videos"]],
        "created_date": full_date,
    }
    (out_root / pack_id / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest
