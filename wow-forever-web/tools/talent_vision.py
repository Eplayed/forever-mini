#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""talent_vision.py — 视频天赋加点帧识别、Forever 模拟器规则校验与 .tpanel 容器精截图。

流程（严格按需触发：无天赋帧的视频零耗时跳过，不干扰正常图文流程）：
1. 基于本机已有视频抽帧（output/assets/frames/<aweme_id>/raw/ 或 note_images）走 macOS Apple Vision OCR
   （带本地 JSON 缓存），严格过滤“仅当帧内包含多棵天赋树与大量 0/5..5/5 角标时”才命中，拒绝单技能弹窗或战斗误触发；
2. 命中后使用多模态模型（关闭思考档 + 2x 放大）对照 wow-forever/app/data/talents/<class>.json 的网格坐标读取；
   若整图某棵树合计与顶部圆圈数不一致或触发规则冲突，自动裁出该单棵树 3x 放大重读一次；
3. 按 TalentPage.vue 同源规则校验（totalPoints<=51、tierUnlockCost、requires、maxRanks）：
   - 全部通过 -> status="verified"，生成标准 (c, p) 编码并在 Playwright 中只截取 app/dist/#/talent 的 .tpanel 容器；
   - 规则有冲突或模糊 -> status="needs_review"，保留候选参数、原因与原帧参考图，绝不强行编造错树。
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import threading
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

CLASS_META: Dict[str, Dict[str, Any]] = {
    "warrior": {
        "cn": "战士",
        "trees_en": (("arms",), ("fury",), ("protection",)),
        "trees_cn": (("武器",), ("狂怒",), ("防护",)),
    },
    "paladin": {
        "cn": "圣骑士",
        "trees_en": (("holy",), ("protection",), ("retribution",)),
        "trees_cn": (("神圣",), ("防护",), ("惩戒",)),
    },
    "hunter": {
        "cn": "猎人",
        "trees_en": (("beast mastery", "beastmastery"), ("marksmanship",), ("survival",)),
        "trees_cn": (("野兽控制", "兽王"), ("射击",), ("生存",)),
    },
    "rogue": {
        "cn": "潜行者",
        "trees_en": (("assassination",), ("combat",), ("subtlety",)),
        "trees_cn": (("奇袭", "刺杀"), ("战斗",), ("敏锐",)),
    },
    "priest": {
        "cn": "牧师",
        "trees_en": (("discipline",), ("holy",), ("shadow", "shadow magic")),
        "trees_cn": (("戒律",), ("神圣",), ("暗影",)),
    },
    "shaman": {
        "cn": "萨满祭司",
        "trees_en": (("elemental", "elemental combat"), ("enhancement",), ("restoration",)),
        "trees_cn": (("元素战斗", "元素"), ("增强",), ("恢复",)),
    },
    "mage": {
        "cn": "法师",
        "trees_en": (("arcane",), ("fire",), ("frost",)),
        "trees_cn": (("奥术",), ("火焰",), ("冰霜",)),
    },
    "warlock": {
        "cn": "术士",
        "trees_en": (("affliction",), ("demonology",), ("destruction",)),
        "trees_cn": (("痛苦",), ("恶魔学识", "恶魔"), ("毁灭",)),
    },
    "druid": {
        "cn": "德鲁伊",
        "trees_en": (("balance",), ("feral", "feral combat"), ("restoration",)),
        "trees_cn": (("平衡",), ("野性战斗", "野性"), ("恢复",)),
    },
}

_RANK_FRAC_RE = re.compile(r"\b[0-5]\s*/\s*[1-5]\b")


def _find_v2t_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    if here.parent.name == "src":
        return here.parents[1]
    return pathlib.Path.home() / "Documents/project/video2text"


def load_class_talents(app_root: pathlib.Path, class_id: str) -> Dict[str, Any]:
    cid = (class_id or "").strip().lower()
    if cid not in CLASS_META:
        raise ValueError(f"不支持的职业标识：{class_id}")
    p = app_root / "data" / "talents" / f"{cid}.json"
    if not p.is_file():
        raise FileNotFoundError(f"缺少天赋真源文件：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def parse_talent_url_or_code(text: str, default_class: str = "") -> Tuple[str, str]:
    """解析 `#/talent?c=priest&p=xxx` URL、query 串或纯 p 编码，返回 (class_id, p_code)。"""
    raw = str(text or "").strip()
    if not raw:
        return default_class.strip().lower(), ""

    cid = default_class.strip().lower()
    p_code = ""

    if "?" in raw or "c=" in raw or "p=" in raw:
        frag = raw.split("#", 1)[1] if "#" in raw else raw
        qstr = frag.split("?", 1)[1] if "?" in frag else frag
        qs = urllib.parse.parse_qs(qstr)
        if qs.get("c"):
            cid = qs["c"][0].strip().lower()
        if qs.get("p"):
            p_code = qs["p"][0].strip()
        if not cid and "/talent/" in raw:
            seg = raw.split("/talent/", 1)[1].split("?", 1)[0].strip("/ ")
            if seg in CLASS_META:
                cid = seg
    elif "-" in raw:
        p_code = raw
    elif raw in CLASS_META:
        cid = raw

    return cid, p_code


def _validate_state_and_build_result(
    tdoc: Dict[str, Any],
    class_id: str,
    state: Dict[str, int],
    issues: List[str],
    header_totals: Optional[List[int]] = None,
) -> Dict[str, Any]:
    trees = tdoc.get("trees") or []
    rules = tdoc.get("rules") or {}
    tier_cost = rules.get("tierUnlockCost") or [0, 5, 10, 15, 20, 25, 30]
    total_cap = int(rules.get("totalPoints") or 51)

    tree_sums: List[int] = []
    tree_names: List[str] = []
    key_talents: List[str] = []

    for t in trees:
        t_name = t.get("nameCn") or ""
        tree_names.append(t_name)
        sp = sum(int(state.get(n["id"], 0)) for n in (t.get("nodes") or []))
        tree_sums.append(sp)
        for n in t.get("nodes") or []:
            rk = int(state.get(n["id"], 0))
            if rk <= 0:
                continue
            tier = int(n.get("tier") or 0)
            below = sum(int(state.get(m["id"], 0)) for m in (t.get("nodes") or []) if int(m.get("tier") or 0) < tier)
            need = int(tier_cost[tier]) if tier < len(tier_cost) else 0
            if below < need:
                issues.append(f"{t_name}「{n.get('nameCn') or n['id']}」(第{tier+1}层): 下层已投 {below} 点 < 门槛 {need} 点")
            for req in n.get("requires") or []:
                if int(state.get(req, 0)) < 1:
                    issues.append(f"{t_name}「{n.get('nameCn') or n['id']}」: 缺少前置天赋 {req}")
            mx = int(n.get("maxRanks") or 0)
            if tier >= 3 or (mx == 1 and rk == 1 and tier >= 2):
                key_talents.append(f"{n.get('nameCn') or ''}({rk}/{mx})")

    if sum(tree_sums) > total_cap:
        issues.append(f"总点数 {sum(tree_sums)} 超过上限 {total_cap}")
    if sum(tree_sums) <= 0:
        issues.append("未识别到有效加点（总点数为 0）")
    if header_totals and len(header_totals) == len(tree_sums) and header_totals != tree_sums:
        issues.append(f"三系总点 {tree_sums} 与画面顶部 {header_totals} 不一致")

    p_parts = []
    for t in trees:
        p_parts.append("".join(str(min(int(state.get(n["id"], 0)), 9)) for n in (t.get("nodes") or [])))
    p_code = "-".join(p_parts)

    summary_text = " / ".join(f"{nm} {sp}" for nm, sp in zip(tree_names, tree_sums))
    class_cn = (CLASS_META.get(class_id) or {}).get("cn") or class_id
    ok = len(issues) == 0 and sum(tree_sums) > 0
    return {
        "ok": ok,
        "status": "verified" if ok else "needs_review",
        "class_id": class_id,
        "class_cn": class_cn,
        "p_code": p_code,
        "simulator_url": f"#/talent?c={class_id}&p={p_code}",
        "tree_names": tree_names,
        "tree_sums": tree_sums,
        "total_points": sum(tree_sums),
        "header_totals": header_totals,
        "summary_text": summary_text,
        "key_talents": key_talents[:6],
        "issues": issues,
    }


def validate_p_code(app_root: pathlib.Path, class_id: str, p_code: str) -> Dict[str, Any]:
    """按 TalentPage.vue 同款编码规则解码并校验 p_code。"""
    tdoc = load_class_talents(app_root, class_id)
    trees = tdoc.get("trees") or []
    parts = str(p_code or "").strip().split("-")
    state: Dict[str, int] = {}
    issues: List[str] = []

    for ti, t in enumerate(trees):
        seg = parts[ti] if ti < len(parts) else ""
        for ni, n in enumerate(t.get("nodes") or []):
            ch = seg[ni] if ni < len(seg) else "0"
            try:
                v = int(ch, 36)
            except ValueError:
                v = 0
                issues.append(f"{t.get('nameCn')} 第{ni+1}格字符 '{ch}' 非法")
            mx = int(n.get("maxRanks") or 0)
            if v > mx:
                issues.append(f"{t.get('nameCn')}「{n.get('nameCn')}」点数 {v} > 上限 {mx}")
                v = mx
            if v > 0:
                state[n["id"]] = v

    return _validate_state_and_build_result(tdoc, class_id, state, issues)


def _encode_tree_from_pos_map(t: Dict[str, Any], pos_map: Dict[str, Any], rules: Dict[str, Any]) -> Tuple[Dict[str, int], int, List[str]]:
    tier_cost = (rules or {}).get("tierUnlockCost") or [0, 5, 10, 15, 20, 25, 30]
    t_name = t.get("nameCn") or ""
    state: Dict[str, int] = {}
    issues: List[str] = []
    for n in t.get("nodes") or []:
        key = f"{n['tier']},{n['column']}"
        try:
            v = int((pos_map or {}).get(key) or 0)
        except (TypeError, ValueError):
            v = 0
        v = max(0, v)
        mx = int(n.get("maxRanks") or 0)
        if v > mx:
            issues.append(f"{t_name}({key})「{n.get('nameCn')}」点数 {v} > 上限 {mx}")
            v = mx
        if v > 0:
            state[n["id"]] = v
    sp = sum(state.values())
    for n in t.get("nodes") or []:
        if state.get(n["id"], 0) > 0:
            tier = int(n.get("tier") or 0)
            below = sum(state.get(m["id"], 0) for m in (t.get("nodes") or []) if int(m.get("tier") or 0) < tier)
            need = int(tier_cost[tier]) if tier < len(tier_cost) else 0
            if below < need:
                issues.append(f"{t_name}「{n.get('nameCn')}」(第{tier+1}层): 下层 {below} < {need}")
            for req in n.get("requires") or []:
                if state.get(req, 0) < 1:
                    issues.append(f"{t_name}「{n.get('nameCn')}」缺前置 {req}")
    return state, sp, issues


def _ocr_frames_cached(frame_paths: List[pathlib.Path], cache_path: pathlib.Path, ocr_script: pathlib.Path) -> Dict[str, List[str]]:
    if sys.platform != "darwin" or not ocr_script.is_file() or not frame_paths:
        return {}
    cache: Dict[str, Any] = {}
    if cache_path.is_file():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    out: Dict[str, List[str]] = {}
    todo: List[pathlib.Path] = []
    for p in frame_paths:
        try:
            st = p.stat()
            sig = f"{p.name}:{st.st_size}:{int(st.st_mtime)}"
        except OSError:
            continue
        ent = cache.get(p.name)
        if isinstance(ent, dict) and ent.get("sig") == sig and isinstance(ent.get("lines"), list):
            out[str(p)] = ent["lines"]
        else:
            todo.append(p)

    if todo:
        try:
            res = subprocess.run(
                ["/usr/bin/swift", str(ocr_script), *(str(p) for p in todo)],
                capture_output=True,
                text=True,
                timeout=90,
                check=True,
            )
            rows = json.loads(res.stdout or "[]")
            if len(rows) == len(todo):
                for p, lines in zip(todo, rows):
                    st = p.stat()
                    sig = f"{p.name}:{st.st_size}:{int(st.st_mtime)}"
                    clean_lines = [str(x).strip() for x in (lines or []) if str(x).strip()]
                    out[str(p)] = clean_lines
                    cache[p.name] = {"sig": sig, "lines": clean_lines}
                try:
                    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
                except OSError:
                    pass
        except Exception:
            pass
    return out


def _classify_ocr_lines(lines: List[str]) -> Tuple[Optional[str], int, int]:
    """根据 OCR 文字判断是否属于三系天赋加点大图，返回 (class_id, rank_match_count, tree_name_hits)。"""
    blob = " | ".join(lines)
    low = blob.lower()
    frac_cnt = len(_RANK_FRAC_RE.findall(blob))
    if frac_cnt < 1:
        return None, frac_cnt, 0

    best_cid: Optional[str] = None
    best_hits = 0
    for cid, meta in CLASS_META.items():
        en_hits = sum(1 for aliases in meta["trees_en"] if any(re.search(r"\b" + re.escape(a) + r"\b", low) for a in aliases))
        cn_hits = sum(1 for aliases in meta["trees_cn"] if any(a in blob for a in aliases))
        hits = max(en_hits, cn_hits)
        if hits >= 2 and hits > best_hits:
            best_hits = hits
            best_cid = cid

    if best_cid and ((best_hits >= 3 and frac_cnt >= 1) or (best_hits >= 2 and frac_cnt >= 3)):
        return best_cid, frac_cnt, best_hits
    return None, frac_cnt, best_hits


def _detect_candidate_frames(
    videos: List[Dict[str, Any]],
    *,
    v2t_root: pathlib.Path,
) -> List[Dict[str, Any]]:
    ocr_script = v2t_root / "scripts" / "read_frame_text.swift"
    if not ocr_script.is_file():
        return []

    by_class: Dict[str, Dict[str, Any]] = {}
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

        ocr_map = _ocr_frames_cached(jpgs, fdir / "ocr_talent_cache.json", ocr_script)
        for p in jpgs:
            lines = ocr_map.get(str(p)) or []
            if not lines:
                continue
            cid, frac_cnt, tree_hits = _classify_ocr_lines(lines)
            if not cid:
                continue
            score = tree_hits * 10 + frac_cnt
            prev = by_class.get(cid)
            if prev is None or score > prev["score"]:
                by_class[cid] = {
                    "class_id": cid,
                    "frame_path": p,
                    "aweme_id": aid,
                    "video_id": v.get("id"),
                    "score": score,
                    "ocr_lines": lines,
                }
    return list(by_class.values())


def _vision_client_and_model(ai_config: Optional[Dict[str, Any]], v2t_root: pathlib.Path) -> Tuple[Any, str]:
    try:
        from . import ai_thinking, wechat_mp_publisher
        ai_thinking.install()
        env_cfg = wechat_mp_publisher._load_env_file(v2t_root / "config" / "config.env.local")
    except Exception:
        env_cfg = {}

    import openai
    api_key = (
        env_cfg.get("AI_API_KEY_FAST")
        or env_cfg.get("OPENAI_API_KEY")
        or (ai_config or {}).get("api_key")
        or ""
    ).strip()
    api_base = (
        env_cfg.get("AI_API_BASE")
        or (ai_config or {}).get("api_base")
        or "https://maas.qianwenaiapi.com/compatible-mode/v1"
    ).strip()
    # 优先使用实测在网格坐标计数准确率高的 qwen3.8-max-0902，其次读取环境池
    model = (env_cfg.get("AI_MODEL_TALENT") or "qwen3.8-max-0902").strip()
    if not api_key:
        raise RuntimeError("未配置视觉识别 API Key")
    client = openai.OpenAI(api_key=api_key, base_url=api_base, timeout=90, max_retries=1)
    return client, model


def _encode_image_b64(img_path: pathlib.Path, scale: int = 2, crop_box: Optional[Tuple[int, int, int, int]] = None) -> str:
    from PIL import Image
    im = Image.open(str(img_path)).convert("RGB")
    if crop_box is not None:
        im = im.crop(crop_box)
    if scale > 1:
        im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=93)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _extract_single_frame_build(
    cand: Dict[str, Any],
    *,
    app_root: pathlib.Path,
    client: Any,
    model: str,
) -> Dict[str, Any]:
    cid = cand["class_id"]
    fpath = pathlib.Path(cand["frame_path"])
    tdoc = load_class_talents(app_root, cid)
    trees = tdoc.get("trees") or []
    rules = tdoc.get("rules") or {}

    grid_desc = []
    for ti, t in enumerate(trees):
        items = [f"({n['tier']},{n['column']}):{n['nameCn']}[{n['maxRanks']}]" for n in (t.get("nodes") or [])]
        grid_desc.append(f"树{ti+1} {t.get('nameCn')}: " + " ".join(items))

    prompt = (
        f"这是一张魔兽世界({cid})的三系天赋加点截图。顶部绿色圆圈里写着三棵树各自的总点数。\n"
        "请你逐树读取：1) 顶部圆圈总点数 header_totals [左,中,右]；2) 只列出**高亮亮色图标且右上角分子大于0**的格子 `\"行,列\": 点数`（行row从0到6，列col从0到3；灰暗图标和 0/x 一律不输出）。\n"
        "硬约束：如果某树顶部圆圈是 0，则该树输出 `{}`；如果某树顶部是 N>0，输出的点数值之和必须严格等于 N！\n"
        "网格坐标参考：\n" + "\n".join(grid_desc) + "\n"
        '仅返回JSON：{"header_totals":[a,b,c],"trees":[{...},{...},{...}]}'
    )
    b64 = _encode_image_b64(fpath, scale=2)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
            {"type": "text", "text": prompt},
        ]}],
        temperature=0.0,
        max_tokens=1500,
        extra_body={"enable_thinking": False},
    )
    raw = resp.choices[0].message.content or ""
    m = re.search(r"\{.*\}", raw, re.S)
    parsed = json.loads(m.group(0)) if m else {}

    headers = parsed.get("header_totals")
    raw_trees = parsed.get("trees") or [{}, {}, {}]
    combined_state: Dict[str, int] = {}
    all_issues: List[str] = []

    from PIL import Image
    with Image.open(str(fpath)) as im0:
        w0, h0 = im0.size

    crop_ranges = [
        (0, 0, int(w0 * 0.38), h0),
        (int(w0 * 0.31), 0, int(w0 * 0.69), h0),
        (int(w0 * 0.62), 0, w0, h0),
    ]

    for ti, t in enumerate(trees):
        pos_map = raw_trees[ti] if ti < len(raw_trees) and isinstance(raw_trees[ti], dict) else {}
        st_t, sp_t, iss_t = _encode_tree_from_pos_map(t, pos_map, rules)
        exp_h = int(headers[ti]) if isinstance(headers, list) and ti < len(headers) and headers[ti] is not None else None

        # 自动单系 3x 放大重读：若合计不等顶部总数，或存在前置/超限错误（且顶部 > 0）
        if (exp_h is not None and exp_h > 0 and sp_t != exp_h) or (iss_t and (exp_h is None or exp_h > 0)):
            retry_items = [f"({n['tier']},{n['column']}):{n['nameCn']}[上限{n['maxRanks']}]" for n in (t.get("nodes") or [])]
            target_hint = f"顶部圆圈总点数为 **{exp_h}**" if exp_h is not None else "请逐格核对顶部总点数"
            retry_prompt = (
                f"这是「{t.get('nameCn')}」单棵天赋树的 3 倍放大截图，{target_hint}。\n"
                "请你逐行逐列（行0..6，列0..3）读出**所有亮色图标且右上角分子 > 0** 的格子，只输出 JSON {\"0,0\":3, ...}。\n"
                "务必核对每个点数 <= 该格上限，且不得编造或漏掉高亮层格子。\n"
                "节点列表：" + " ".join(retry_items)
            )
            b64_crop = _encode_image_b64(fpath, scale=3, crop_box=crop_ranges[ti])
            resp2 = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64_crop}},
                    {"type": "text", "text": retry_prompt},
                ]}],
                temperature=0.0,
                max_tokens=1000,
                extra_body={"enable_thinking": False},
            )
            raw2 = resp2.choices[0].message.content or ""
            m2 = re.search(r"\{.*\}", raw2, re.S)
            if m2:
                try:
                    pos2 = json.loads(m2.group(0))
                    if isinstance(pos2, dict):
                        st2, sp2, iss2 = _encode_tree_from_pos_map(t, pos2, rules)
                        # 若重读版本问题更少或刚好对上顶部点数，采用重读结果
                        better_sum = exp_h is not None and sp2 == exp_h and sp_t != exp_h
                        fewer_issues = len(iss2) < len(iss_t)
                        if better_sum or (fewer_issues and (exp_h is None or abs(sp2 - exp_h) <= abs(sp_t - exp_h))):
                            st_t, iss_t = st2, iss2
                except Exception:
                    pass

        combined_state.update(st_t)
        all_issues.extend(iss_t)

    result = _validate_state_and_build_result(
        tdoc, cid, combined_state, all_issues,
        header_totals=[int(x) for x in headers] if isinstance(headers, list) else None,
    )
    result["source_frame_path"] = str(fpath)
    result["aweme_id"] = cand.get("aweme_id")
    result["video_id"] = cand.get("video_id")
    return result


def extract_talent_builds_for_videos(
    videos: List[Dict[str, Any]],
    *,
    app_root: pathlib.Path,
    ai_config: Optional[Dict[str, Any]] = None,
    v2t_root: Optional[pathlib.Path] = None,
    progress_cb=None,
) -> List[Dict[str, Any]]:
    """从视频已有帧中检测并识别天赋加点，无天赋画面时毫秒级返回 []。"""
    root = v2t_root or _find_v2t_root()
    candidates = _detect_candidate_frames(videos, v2t_root=root)
    if not candidates:
        return []

    if progress_cb:
        cns = "、".join((CLASS_META.get(c["class_id"]) or {}).get("cn") or c["class_id"] for c in candidates)
        progress_cb(f"检测到 {len(candidates)} 张天赋加点帧（{cns}），正在高精度读取并按模拟器规则校验...")

    try:
        client, model = _vision_client_and_model(ai_config, root)
    except Exception:
        return []

    builds: List[Dict[str, Any]] = []
    for cand in candidates:
        try:
            res = _extract_single_frame_build(cand, app_root=app_root, client=client, model=model)
            builds.append(res)
        except Exception as exc:
            cid = cand["class_id"]
            builds.append({
                "ok": False,
                "status": "needs_review",
                "class_id": cid,
                "class_cn": (CLASS_META.get(cid) or {}).get("cn") or cid,
                "p_code": "",
                "simulator_url": f"#/talent?c={cid}",
                "tree_names": [],
                "tree_sums": [],
                "total_points": 0,
                "summary_text": "识别中断，请在工坊内核对点选",
                "key_talents": [],
                "issues": [f"视觉读取异常：{str(exc)[:120]}"],
                "source_frame_path": str(cand.get("frame_path") or ""),
            })
    return builds


def render_talent_panel_screenshots(
    builds: List[Dict[str, Any]],
    *,
    app_root: pathlib.Path,
    wechat_dir: pathlib.Path,
) -> List[Dict[str, Any]]:
    """打开本地 app/dist/#/talent?c=...&p=...，仅对 .tpanel 模拟器加点容器做高清截图。"""
    dist_dir = app_root / "dist"
    verified = [b for b in builds if b.get("status") == "verified" and b.get("p_code")]
    if verified and dist_dir.is_dir():
        wechat_dir.mkdir(parents=True, exist_ok=True)
        handler = partial(SimpleHTTPRequestHandler, directory=str(dist_dir))
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                pg = browser.new_page(viewport={"width": 1280, "height": 1100}, device_scale_factor=1.5)
                for b in verified:
                    cid = b["class_id"]
                    p_code = b["p_code"]
                    url = f"http://127.0.0.1:{port}/#/talent?c={cid}&p={p_code}"
                    pg.goto(url, wait_until="networkidle")
                    pg.wait_for_selector(".tpanel .trees .node", timeout=15000)
                    pg.wait_for_timeout(300)
                    pg.add_style_tag(content="""
                      .tpanel #tq, .tpanel #cmp, .tpanel #sel, .tpanel .tfoot,
                      .tpanel button[data-clear], .tpanel .ttabs { display: none !important; }
                      .tpanel { margin: 0 !important; box-shadow: none !important; }
                    """)
                    pg.wait_for_timeout(120)
                    fname = f"talent_{cid}.png"
                    out_png = wechat_dir / fname
                    pg.locator(".tpanel").screenshot(path=str(out_png))
                    b["panel_img_rel"] = fname
                browser.close()
        finally:
            srv.shutdown()

    # 为待人工复核的条目拷贝原帧作为参考预览
    for b in builds:
        if b.get("status") != "verified":
            sf = b.get("source_frame_path")
            if sf and pathlib.Path(sf).is_file():
                wechat_dir.mkdir(parents=True, exist_ok=True)
                ref_name = f"talent_ref_{b['class_id']}.jpg"
                (wechat_dir / ref_name).write_bytes(pathlib.Path(sf).read_bytes())
                b["ref_frame_rel"] = f"wechat/{ref_name}"
    return builds
