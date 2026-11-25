#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地维护小程序首页「区服 G 排行」真源 wow-forever-web/app/data/g-rank.json。

不发起任何绕过验证码的网络抓取。支持三种本地输入：
  1) --html <path>    解析站主在浏览器通过验证后手动保存的网页 HTML（Ctrl+S）
  2) --text <path>    解析从浏览器复制粘贴的纯文本行（每行支持：区服 联盟/部落 数值）
  3) --set "区服:阵营:数值"（可多次传入，阵营写 联盟/部落 或 alliance/horde）

示例：
  python wow-forever-web/tools/import-g-rank.py --html C:\\Users\\Administrator\\Downloads\\dd373.html
  python wow-forever-web/tools/import-g-rank.py --set "黑莲花:联盟:12.5" --set "黑莲花:部落:11.8"
"""
import argparse
import datetime
import html as html_lib
import json
import pathlib
import re
import statistics
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT_PATH = REPO / "wow-forever-web" / "app" / "data" / "g-rank.json"
BANNED_WORDS = ("金币", "人民币", "元", "¥", "￥", "交易", "购买", "dd373", "DD373", "7881", "uu898")
FACTION_MAP = {
    "alliance": "alliance",
    "lm": "alliance",
    "a": "alliance",
    "联盟": "alliance",
    "horde": "horde",
    "bl": "horde",
    "h": "horde",
    "部落": "horde",
}


def slug_id(realm: str, faction: str) -> str:
    clean = re.sub(r"\s+", "-", realm.strip())
    return f"{clean}-{faction}"


def check_clean_text(field: str, value: str):
    s = str(value or "")
    for bad in BANNED_WORDS:
        if bad.lower() in s.lower():
            raise ValueError(f"字段 {field} 包含禁用词 {bad!r}：{s!r}")


def parse_set_args(specs):
    rows = []
    for raw in specs:
        parts = re.split(r"[:：|,\t]+", raw.strip())
        if len(parts) < 3:
            raise ValueError(f"--set 格式应为 '区服:联盟/部落:数值'，收到：{raw!r}")
        realm = parts[0].strip()
        fac = FACTION_MAP.get(parts[1].strip().lower())
        if not fac:
            raise ValueError(f"未知阵营 {parts[1]!r}（请用 联盟 / 部落）")
        val = float(parts[2].strip())
        if val <= 0:
            raise ValueError(f"数值必须大于 0：{raw!r}")
        sample = int(parts[3]) if len(parts) >= 4 and parts[3].strip().isdigit() else 1
        rows.append({"realm": realm, "faction": fac, "gPerMi": round(val, 2), "sampleCount": sample})
    return rows


def strip_html(raw_html: str) -> str:
    s = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "\n", s)
    s = html_lib.unescape(s)
    lines = [re.sub(r"\s+", " ", line).strip() for line in s.splitlines()]
    return "\n".join(l for l in lines if l)


def parse_dd373_text(text: str):
    """从保存的 DD373 页面文本或手动粘贴行中提取 (realm, faction, gPerMi) 列表。"""
    buckets = {}

    # 1) 优先匹配 DD373 真实保存页的多行结构：
    #    区服：\n国服\n/\nPVP\n/\n部落 ... \n1\n元=\n2.4390\n金
    dd_pat = re.compile(
        r"区服：\s*\n([^\n]{1,16})\s*\n/\s*\n([^\n]{1,20})\s*\n/\s*\n(联盟|部落)[\s\S]{0,260}?\n1\s*\n元=\s*\n([\d.]+)\s*\n金",
        re.M,
    )
    for m in dd_pat.finditer(text):
        region = m.group(1).strip()
        server = m.group(2).strip()
        fac = FACTION_MAP[m.group(3)]
        val = float(m.group(4))
        if val <= 0:
            continue
        realm = server if region == "国服" else f"{region}·{server}"
        buckets.setdefault((realm, fac), []).append(val)

    # 2) 次优先：单行/紧凑商品块（如 "黑莲花 / 联盟 ... 1元=12.5金"）
    if not buckets:
        block_pat = re.compile(
            r"([^\s/\\|,:：]{2,16})\s*[/\-·\s]+\s*(联盟|部落)[\s\S]{0,240}?1\s*[元米]\s*[=≈]\s*([\d.]+)\s*[金Gg]",
            re.M,
        )
        for m in block_pat.finditer(text):
            realm = m.group(1).strip()
            fac = FACTION_MAP[m.group(2)]
            val = float(m.group(3))
            if val <= 0 or any(bad in realm for bad in ("魔兽", "无限", "经典", "商品", "发货")):
                continue
            buckets.setdefault((realm, fac), []).append(val)

    # 3) 回退：逐行简化格式（如 "PVP 联盟 2.35" 或 "普通-部落 1米≈2.5G"）
    if not buckets:
        line_pat = re.compile(
            r"^\s*([^\s/\\|,:：\-]{2,16})[\s/\-·,:：]+(联盟|部落)[\s,:：]+(?:1\s*[米元]\s*[=≈]\s*)?([\d.]+)\s*[Gg金]?\s*$"
        )
        for line in text.splitlines():
            m = line_pat.match(line)
            if not m:
                continue
            realm = m.group(1).strip()
            fac = FACTION_MAP[m.group(2)]
            val = float(m.group(3))
            if val > 0:
                buckets.setdefault((realm, fac), []).append(val)

    rows = []
    for (realm, fac), vals in buckets.items():
        med = round(statistics.median(vals), 2)
        rows.append({"realm": realm, "faction": fac, "gPerMi": med, "sampleCount": len(vals)})
    return rows


def main():
    ap = argparse.ArgumentParser(description="更新小程序首页区服 G 排行数据（不绕过验证码）")
    ap.add_argument("--html", action="append", default=[], help="浏览器手动保存的本地网页 HTML 路径（可多次传入）")
    ap.add_argument("--text", help="本地纯文本文件路径")
    ap.add_argument("--set", action="append", default=[], help="手动指定一条：区服:联盟/部落:数值[:样本数]")
    ap.add_argument("--merge", action="store_true", help="与现有条目合并（同区服同阵营覆盖）")
    ap.add_argument("--clear", action="store_true", help="清空条目")
    ap.add_argument("--updated-at", help="自定义更新时间（默认当前北京时间 YYYY-MM-DD HH:MM）")
    args = ap.parse_args()

    cur = json.loads(OUT_PATH.read_text(encoding="utf-8")) if OUT_PATH.is_file() else {}
    existing = {(x["realm"], x["faction"]): x for x in (cur.get("items") or [])} if args.merge else {}

    if args.clear:
        new_rows = []
        updated_at = ""
    else:
        incoming = []
        for html_path in args.html:
            raw = pathlib.Path(html_path).read_text(encoding="utf-8", errors="ignore")
            if "CF_APP_WAF" in raw and "元=" not in raw:
                raise SystemExit(f"输入 HTML 仍是 WAF 验证拦截页：{html_path}")
            incoming.extend(parse_dd373_text(strip_html(raw)))
        if args.text:
            txt = pathlib.Path(args.text).read_text(encoding="utf-8", errors="ignore")
            incoming.extend(parse_dd373_text(txt))
        if args.set:
            incoming.extend(parse_set_args(args.set))

        if not incoming:
            raise SystemExit("未解析到任何有效区服条目（请用 --set / --html / --text / --clear）。")

        for r in incoming:
            check_clean_text("realm", r["realm"])
            existing[(r["realm"], r["faction"])] = {
                "id": slug_id(r["realm"], r["faction"]),
                "realm": r["realm"],
                "faction": r["faction"],
                "gPerMi": round(float(r["gPerMi"]), 2),
                "sampleCount": int(r.get("sampleCount") or 1),
            }

        new_rows = sorted(
            existing.values(),
            key=lambda x: (-x["gPerMi"], x["realm"], x["faction"]),
        )
        tz = datetime.timezone(datetime.timedelta(hours=8))
        updated_at = args.updated_at or datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    payload = {
        "schemaVersion": 1,
        "product": "wow-forever-mini",
        "kind": "g-rank",
        "level": "L2",
        "updatedAt": updated_at,
        "unit": "G/米",
        "note": "仅供参考，以游戏内实际为准",
        "items": new_rows,
    }
    check_clean_text("note", payload["note"])
    check_clean_text("unit", payload["unit"])

    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {OUT_PATH.relative_to(REPO)}：{len(new_rows)} 条，更新时间 {updated_at or '（空）'}")


if __name__ == "__main__":
    main()
