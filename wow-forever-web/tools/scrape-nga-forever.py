#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NGA「魔兽世界：无限」板块热帖采集（访客态，免登录）

实测记录见 docs/DATA-NGA-2026-10-18.md（同目录）。一句话结论：
  · 板块全量列表与帖子正文对访客关闭（code=46 / 网页端 403「访客不能直接访问」），
    要正文必须登录，本脚本不碰登录态；
  · 访客态唯一能拿到内容级数据的是「热帖」接口，固定返回约 32 条、覆盖最近 ~24 小时；
  · 服务端结果缓存 1 小时（响应 expire_at），跑得更密没有意义，一天 1–2 次足够。

用法：
    python3 tools/scrape-nga-forever.py                 # 采一次，落当天快照
    python3 tools/scrape-nga-forever.py --print         # 只打表不落盘
    python3 tools/scrape-nga-forever.py --fid 510569    # 换板块

落盘：docs/nga-hot/<日期>.json（不进 src/data —— 它是玩家讨论，不是本站数据基底）
"""
import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

FID_DEFAULT = 510569          # NGA 板块「魔兽世界：无限」，访客态实测可确认板块名
API = "https://bbs.nga.cn/app_api.php?__lib=subject&__act=hot&fid={fid}"
# ⚠ 不要给这个接口加分页/条数参数：page / row / rows / n / np / tpage 任一命中，
# 服务端直接返回 0 条（不是报错）。固定 ~32 条是它的上限，没有下一页。
PAGE_PARAMS_ARE_POISON = ("page", "row", "rows", "n", "np", "tpage", "order_by")

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 NGA-READONLY-SCRIPT/1.0")

CST = timezone(timedelta(hours=8))

# 本站红线：这些字段是事实性元数据（ID、时间、计数、标题）。
# 正文拿不到也不该拿；标题只用于内部选题判断，不进网页、不进小程序。
KEEP = ("tid", "fid", "subject", "author", "authorid",
        "postdate", "lastpost", "lastposter", "replies", "type")


def fetch(fid: int, timeout: int = 25) -> dict:
    url = API.format(fid=fid)
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    ctx = ssl.create_default_context()
    # 本机装了零信任代理（aTrust）时 TLS 链里会有自签证书，urllib 默认校验会失败。
    # 确认是这个原因再用环境变量放开，别默认放开。
    if os.environ.get("NGA_INSECURE") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        print("! NGA_INSECURE=1：已跳过证书校验（仅用于本机代理干扰的场景）", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def norm(d: dict) -> list:
    """只留白名单字段 + 时间转可读；多余字段（attachs/forumname）丢掉不存。"""
    rows = []
    for x in (d.get("result") or []):
        if not isinstance(x, dict) or x.get("tid") is None:
            continue
        r = {k: x.get(k) for k in KEEP}
        for f in ("postdate", "lastpost"):
            v = r.get(f)
            if isinstance(v, int) and v > 0:
                r[f + "Cst"] = datetime.fromtimestamp(v, CST).strftime("%Y-%m-%d %H:%M")
        rows.append(r)
    rows.sort(key=lambda r: r.get("lastpost") or 0, reverse=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fid", type=int, default=FID_DEFAULT)
    ap.add_argument("--print", action="store_true", help="只打印，不落盘")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    try:
        raw = fetch(args.fid)
    except urllib.error.URLError as e:
        print("取数失败：%s" % e, file=sys.stderr)
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            print("  多半是本机零信任代理插了自签证书。确认无误后可 NGA_INSECURE=1 重跑，"
                  "或在没有代理的机器上跑。", file=sys.stderr)
        return 1
    except Exception as e:                                  # 接口改动 / 被限流
        print("取数异常：%r" % (e,), file=sys.stderr)
        return 1

    code = raw.get("code")
    if code != 0:
        print("接口返回非 0：code=%s msg=%s —— 访客政策可能又收紧了，去看实测文档那段结论"
              % (code, raw.get("msg")), file=sys.stderr)
        return 1

    rows = norm(raw)
    if not rows:
        print("0 条。先确认没踩分页毒参数；若请求本就干净，说明这个接口对这座板块空了。",
              file=sys.stderr)
        return 1

    exp = raw.get("expire_at")
    print("板块 fid=%s 热帖 %d 条（服务端缓存到 %s）" % (
        args.fid, len(rows),
        datetime.fromtimestamp(exp, CST).strftime("%m-%d %H:%M") if isinstance(exp, int) else "?"))

    if args.print:
        for r in rows:
            print("  %s | 回%-4d | tid=%s | %s" %
                  (r.get("postdateCst"), r.get("replies") or 0, r.get("tid"),
                   (r.get("subject") or "")[:46]))
        return 0

    today = datetime.now(CST).strftime("%Y-%m-%d")
    out_dir = args.out_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                           "docs", "nga-hot")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "%s.json" % today)
    payload = {
        "meta": {
            "source": "NGA 玩家社区 App 只读接口 subject/hot",
            "url": API.format(fid=args.fid),
            "forum": {"fid": args.fid, "name": "魔兽世界：无限"},
            "fetchedAt": datetime.now(CST).isoformat(timespec="seconds"),
            "cacheExpiresAt": exp,
            "count": len(rows),
            # 三条要留档的口径，防止下一轮误当成数据源
            "coverage": "约最近 24 小时的热帖，固定 ~32 条上限，非板块全量",
            "usage": "仅供本站选题与热度参考；玩家原创讨论，不复制正文、不进页面、不进小程序",
            "levelNote": "fan_forum 性质，绝不标 L0；引用需带 URL 与抓取时间",
        },
        "threads": rows,
    }
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    print("已落盘 → %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
