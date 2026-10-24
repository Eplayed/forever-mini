#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NGA「魔兽世界：无限」板块采集（fid=510569）

两种模式：
  hot   访客态，App 接口 subject/hot，固定 ~32 条、覆盖最近 24 小时，不需要登录
  board 登录态，网页端板块列表按发帖时间倒序翻页 + 抓新帖正文（需要 ~/.nga/cookie.txt）

为什么走 curl 而不是 urllib：本机装了零信任代理（aTrust），TLS 链里有自签证书，
Python 默认的 certifi 信任库不认，但 **curl 用 macOS 钥匙串、认得这张证书**。
所以本脚本一律用 curl 子进程发请求——不需要任何跳过校验的开关。

登录 cookie 放在 `~/.nga/cookie.txt`（600 权限，仓库外），是一整行 `k=v; k=v`。
过期了就重新从浏览器复制。**这个文件永远不要提交进仓库。**

用法：
    python3 tools/scrape-nga-forever.py hot                    # 访客态热帖
    python3 tools/scrape-nga-forever.py board --pages 3        # 登录态：列表 3 页 + 抓新帖正文
    python3 tools/scrape-nga-forever.py board --pages 1 --no-body
    python3 tools/scrape-nga-forever.py board --pages 5 --rebuild-view

产物（默认全在 `~/.nga/data/`，不入库；可用 NGA_DATA_DIR 改）：
    hot-<日期>.json          热帖快照
    board-<日期>.json        列表快照（含 tid 全量元数据）
    index.json               已见过的 tid 台账（增量靠它判重）
    threads/<tid>.json       单帖正文
    view.html                本地双击就能看的汇总页

改了本文件要同步一份到 ~/.nga/scrape-nga-forever.py，launchd 跑的是那份副本。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from html import unescape

FID = 510569
FORUM_NAME = "魔兽世界：无限"
BASE = "https://bbs.nga.cn"
HOT_API = f"{BASE}/app_api.php?__lib=subject&__act=hot&fid={FID}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36")
COOKIE_FILE = os.path.expanduser("~/.nga/cookie.txt")
JAR_FILE = os.path.expanduser("~/.nga/jar.txt")   # 运行时会话 cookie，仓库外

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 数据只往一个地方落：~/.nga/data —— 手动跑和 launchd 跑看的是同一份。
# 为什么不落仓库 docs/nga-hot：① launchd 起的 bash 读不到 ~/Documents（macOS TCC）；
# ② 产物含玩家原创正文，仓库远程是公开的，提交进去等于我替他们转载。
# 要用别处就设环境变量 NGA_DATA_DIR。
OUT_DIR = os.environ.get("NGA_DATA_DIR") or os.path.expanduser("~/.nga/data")
THREAD_DIR = os.path.join(OUT_DIR, "threads")
INDEX_FILE = os.path.join(OUT_DIR, "index.json")

CST = timezone(timedelta(hours=8))
# 抓取节流。座间太短会被 NGA 判定异常，按 wowhead 那次的经验留 1.2-1.8 秒。
SLEEP_MIN, SLEEP_MAX = 1.2, 1.8


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def today() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d")


def ts2str(v) -> str:
    try:
        return datetime.fromtimestamp(int(v), CST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def curl(url: str, cookie: bool = False, referer: str = None) -> tuple:
    """返回 (http_code, bytes)。失败时 code=0。

    两个必须做对的地方（都是实测撞出来的）：
    ① `-L` 跟跳转。NGA（PHPWind）会用 **302 来刷新 lastvisit/lastpath 会话 cookie**，
       不跟跳转就会把一次正常的响应误判成失败——上一版就是这么只抓到 27/75 条正文。
    ② `-b/-c` 维护一个 cookie jar（在 ~/.nga/jar.txt）。登录 cookie 是种子，
       运行时服务端转的会话值要能带回去，否则每隔几次就重演一次 302。
    """
    cmd = ["curl", "-sS", "-m", "30", "-A", UA, "-L", "--max-redirs", "3",
           "-w", "\\n%{http_code}"]
    if cookie:
        cmd += ["-b", load_cookie(), "-c", JAR_FILE]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    cmd.append(url)
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=45)
    except subprocess.TimeoutExpired:
        print(f"! 超时 {url}", file=sys.stderr)
        return 0, b""
    if p.returncode != 0:
        err = p.stderr.decode("utf-8", "replace")[:160]
        print(f"! curl 失败 {url}: {err}", file=sys.stderr)
        return 0, b""
    body, _, code = p.stdout.rpartition(b"\n")
    try:
        return int(code.strip()), body
    except ValueError:
        return 0, body


def load_cookie() -> str:
    if not os.path.exists(COOKIE_FILE):
        raise SystemExit(
            f"缺少登录 cookie：{COOKIE_FILE}\n"
            "  写法：登录 bbs.nga.cn 后，从浏览器开发者工具的请求头里复制整行 Cookie 存进该文件，\n"
            "  然后 chmod 600 它。这个文件在仓库外，不要提交。")
    with open(COOKIE_FILE, encoding="utf-8") as f:
        ck = f.read().strip()
    if "ngaPassportUid=" not in ck or "ngaPassportCid=" not in ck:
        raise SystemExit(f"{COOKIE_FILE} 里缺 ngaPassportUid / ngaPassportCid，登录态不完整")
    return ck


def has_cookie() -> bool:
    return os.path.exists(COOKIE_FILE)


def strip_tags(s: str) -> str:
    s = re.sub(r"\[/?[a-zA-Z][^\]\n]{0,40}\]", " ", s)   # UBB 码
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


# ---------------------------------------------------------------- hot 模式 ----
def cmd_hot(_: argparse.Namespace) -> int:
    code, body = curl(HOT_API)
    if code != 200:
        print(f"接口 HTTP {code}", file=sys.stderr)
        return 1
    try:
        d = json.loads(body.decode("utf-8", "replace"))
    except Exception as e:
        print(f"返回不是 JSON：{e}", file=sys.stderr)
        return 1
    if d.get("code") != 0:
        print(f"接口 code={d.get('code')} msg={d.get('msg')} —— 访客政策可能收紧了，"
              f"去看 docs/DATA-NGA-2026-10-18.md", file=sys.stderr)
        return 1
    rows = []
    for x in d.get("result") or []:
        if isinstance(x, dict) and x.get("tid"):
            rows.append({k: x.get(k) for k in
                         ("tid", "fid", "subject", "author", "authorid",
                          "postdate", "lastpost", "lastposter", "replies", "type")})
    if not rows:
        print("0 条", file=sys.stderr)
        return 1
    rows.sort(key=lambda r: r.get("lastpost") or 0, reverse=True)
    for r in rows:
        r["postdateCst"] = ts2str(r.get("postdate"))
        r["lastpostCst"] = ts2str(r.get("lastpost"))
    payload = {
        "meta": {"mode": "hot", "source": "NGA App 只读接口 subject/hot",
                 "url": HOT_API, "forum": {"fid": FID, "name": FORUM_NAME},
                 "fetchedAt": now_iso(), "cacheExpiresAt": d.get("expire_at"),
                 "count": len(rows),
                 "coverage": "约最近 24 小时热帖，固定 ~32 条上限，非板块全量",
                 "usage": "仅供本站选题与热度参考；玩家原创讨论，不复制正文、不进页面、不进小程序",
                 "levelNote": "fan_forum 性质，绝不标 L0；引用需带 URL 与抓取时间"},
        "threads": rows}
    out = os.path.join(OUT_DIR, f"hot-{today()}.json")
    write_json(out, payload)
    print(f"hot：{len(rows)} 条 → {out}")
    return 0


# -------------------------------------------------------------- board 模式 ----
ROW_RE = re.compile(
    r"<td class='c1'><a id='t_rc[^']*'[^>]*href='/read\.php\?tid=(?P<tid>\d+)'[^>]*>(?P<replies>[\d*]+)</a></td>"
    r".*?class='topic'[^>]*>(?P<subject>.*?)</a>"
    r".*?class='author'[^>]*title='用户ID (?P<uid>\d+)'>(?P<author>.*?)</a>"
    r"<span class='silver postdate'[^>]*>(?P<postdate>\d+)</span>",
    re.S)


def parse_list(html: str) -> list:
    """列表行 → dict。HTML 是 GBK 解出来的字符串。"""
    out = []
    for m in ROW_RE.finditer(html):
        rep = m.group("replies")
        out.append({
            "tid": int(m.group("tid")),
            "fid": FID,
            "subject": strip_tags(m.group("subject")),
            "author": strip_tags(m.group("author")),
            "authorid": int(m.group("uid")),
            "postdate": int(m.group("postdate")),
            "postdateCst": ts2str(m.group("postdate")),
            "replies": None if "*" in rep else int(rep or 0),
            "url": f"{BASE}/read.php?tid={m.group('tid')}",
        })
    # 去重保序（置顶区会重复出现同一个 tid）
    seen, uniq = set(), []
    for r in out:
        if r["tid"] not in seen:
            seen.add(r["tid"])
            uniq.append(r)
    return uniq


def page_count(html: str):
    m = re.search(r"var __PAGE = \{[^}]*?1:(\d+),2:(\d+),3:(\d+)\}", html)
    return tuple(int(m.group(i)) for i in (1, 2, 3)) if m else (None, None, None)


def parse_thread(html: str) -> dict:
    """帖子页 → 标题 / 板块 / 首楼正文 / 回复时间。"""
    def grab(pat):
        m = re.search(pat, html, re.S)
        return m.group(1) if m else None
    subj = grab(r"<h1 id='currentTopicName'[^>]*>(.*?)</h1>")
    forum = grab(r"<h2 id='currentForumName'[^>]*>(.*?)</h2>")
    body = grab(r"<p id='postcontent0' class='postcontent[^']*'>([\s\S]*?)</p>")
    date = grab(r"<span id='postdate0'[^>]*>(.*?)</span>")
    author = grab(r"<a[^>]*class='author'[^>]*>(.*?)</a>")
    return {"subject": strip_tags(subj or ""), "forumname": strip_tags(forum or ""),
            "author": strip_tags(author or ""), "firstPostDate": strip_tags(date or ""),
            "body": strip_tags(body or "")}


def load_index() -> dict:
    if os.path.exists(INDEX_FILE):
        try:
            return json.load(open(INDEX_FILE, encoding="utf-8"))
        except Exception:
            print("! index.json 读坏了，重建（不会重复抓正文，只会重新认识一遍 tid）", file=sys.stderr)
    return {"seen": {}, "bodied": {}}


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def cmd_board(args: argparse.Namespace) -> int:
    if not has_cookie():
        raise SystemExit("board 模式需要登录 cookie（hot 模式不用）——见脚本头部说明")
    idx = load_index()
    order = "postdatedesc"
    collected, page = [], 0
    total_pages = None
    for p in range(1, args.pages + 1):
        url = f"{BASE}/thread.php?fid={FID}&order_by={order}&page={p}&rand={int(time.time()) % 900 + 10 + p}"
        code, raw = curl(url, cookie=True, referer=f"{BASE}/thread.php?fid={FID}")
        if code != 200:
            print(f"! 第 {p} 页 HTTP {code}，停在这里", file=sys.stderr)
            break
        html = raw.decode("gbk", "replace")
        if "访客不能直接访问" in html:
            print(f"! 第 {p} 页又被当访客拦了 —— cookie 可能过期，重新从浏览器复制", file=sys.stderr)
            break
        if total_pages is None:
            total_pages, _, per = page_count(html)
            print(f"板块按发帖时间倒序共 {total_pages} 页（每页约 {per} 条）")
        rows = parse_list(html)
        if not rows:
            print(f"! 第 {p} 页解析到 0 行——NGA 可能改了列表结构，先别加量，去核 ROW_RE", file=sys.stderr)
            break
        collected += rows
        page = p
        print(f"  第 {p} 页：{len(rows)} 条")
        time.sleep(SLEEP_MIN)

    if not collected:
        return 1

    new = [r for r in collected if str(r["tid"]) not in idx["seen"]]
    # 台账：所有见过的 tid 都记下来
    for r in collected:
        idx["seen"][str(r["tid"])] = r["postdate"]

    # 抓正文的候选按「还没抓过正文」算，不是按「新帖」算——
    # 否则一次抓失败的帖会被 seen 记成见过，永远补不回来（上一版就是这个 bug）。
    todo = [r for r in collected if str(r["tid"]) not in idx["bodied"]]
    if args.max_body and len(todo) > args.max_body:
        print(f"  待补正文 {len(todo)} 条，本次只做最早的 {args.max_body} 条（其余下次自动接着补）")
        todo = todo[:args.max_body]

    bodied = 0
    fails = 0
    if not args.no_body:
        os.makedirs(THREAD_DIR, exist_ok=True)
        for r in todo:
            if str(r["tid"]) in idx["bodied"]:
                continue
            u = f"{BASE}/read.php?tid={r['tid']}&rand={int(time.time()) % 900 + 10}"
            code, raw = curl(u, cookie=True, referer=f"{BASE}/thread.php?fid={FID}")
            if code != 200:
                fails += 1
                print(f"  tid={r['tid']} HTTP {code}（跳过，下次还会当新帖重试）", file=sys.stderr)
                if fails >= 6:
                    print("! 连续 6 次拿不到正文，本次就此停住——继续硬打只会把登录会话打进风控。"
                          "剩下的帖下次跑会自动补上（判重靠 index.json）。", file=sys.stderr)
                    break
                time.sleep(SLEEP_MAX * 2)
                continue
            fails = 0
            html = raw.decode("gbk", "replace")
            if "访客不能直接访问" in html or "帖子被设为隐藏" in html:
                print(f"  tid={r['tid']} 拿不到正文（隐藏或权限）")
                idx["bodied"][str(r["tid"])] = "hidden"
                continue
            d = parse_thread(html)
            d.update({"tid": r["tid"], "fid": FID, "url": u,
                      "listAuthor": r["author"], "listPostdateCst": r["postdateCst"],
                      "replies": r["replies"], "fetchedAt": now_iso(),
                      "level": "fan_forum",
                      "usage": "仅内部参考，不转载、不摘要上页面、不进小程序"})
            write_json(os.path.join(THREAD_DIR, f"{r['tid']}.json"), d)
            idx["bodied"][str(r["tid"])] = d["firstPostDate"] or r["postdateCst"]
            bodied += 1
            print(f"  tid={r['tid']} 正文 {len(d['body'])} 字 | {d['subject'][:34]}")
            time.sleep(SLEEP_MIN + 0.4)

    out = os.path.join(OUT_DIR, f"board-{today()}.json")
    # 同一天多次跑要**并**进当天文件，不能覆盖：一天跑两次是为了覆盖早晚两个发帖高峰，
    # 直接覆盖就只剩最后那一次，早上那批列表行就丢了（正文虽在 threads/ 里没丢，但对不上账）。
    day_rows = {}
    if os.path.exists(out):
        try:
            for t in json.load(open(out, encoding="utf-8")).get("threads", []):
                day_rows[t["tid"]] = t
        except Exception:
            print("! 当天旧快照读坏了，本次以新数据重建", file=sys.stderr)
    for t in collected:
        day_rows.setdefault(t["tid"], t)
    merged = sorted(day_rows.values(), key=lambda r: r.get("postdate") or 0, reverse=True)
    payload = {
        "meta": {"mode": "board", "url": f"{BASE}/thread.php?fid={FID}&order_by={order}",
                 "forum": {"fid": FID, "name": FORUM_NAME}, "fetchedAt": now_iso(),
                 "pagesFetched": page,
                 "count": len(merged), "countThisRun": len(collected),
                 "newCount": len(new), "bodySaved": bodied,
                 "boardTotalPages": total_pages,
                 "usage": "仅供本站选题与热度参考；玩家原创讨论，不复制正文上页面",
                 "levelNote": "fan_forum 性质，绝不标 L0；引用需带 URL 与抓取时间"},
        "threads": merged}
    write_json(out, payload)
    write_json(INDEX_FILE, idx)
    print(f"board：本次列表 {len(collected)} 条（新 {len(new)}、抓正文 {bodied}），"
          f"当天累计 {len(merged)} 条 → {out}")
    return 0


def cmd_view(_: argparse.Namespace) -> int:
    """把已采到的东西拼成一个本地能打开的 HTML（数据内联，不走 fetch，file:// 可直接看）。"""
    files = sorted([f for f in os.listdir(OUT_DIR) if f.startswith("board-")], reverse=True) \
        if os.path.isdir(OUT_DIR) else []
    rows, bodies = [], {}
    for fn in files[:14]:
        try:
            d = json.load(open(os.path.join(OUT_DIR, fn), encoding="utf-8"))
        except Exception:
            continue
        for t in d.get("threads", []):
            t["snapshot"] = fn[6:-5]
            rows.append(t)
    if os.path.isdir(THREAD_DIR):
        for fn in os.listdir(THREAD_DIR):
            if fn.endswith(".json"):
                try:
                    bodies[fn[:-5]] = json.load(open(os.path.join(THREAD_DIR, fn), encoding="utf-8"))
                except Exception:
                    pass
    uniq = {}
    for r in rows:
        uniq.setdefault(r["tid"], r)
    items = sorted(uniq.values(), key=lambda r: r.get("postdate", 0), reverse=True)
    tr = []
    for r in items:
        b = bodies.get(str(r["tid"]), {})
        body = (b.get("body") or "").replace("\n", "<br/>")
        tr.append(
            f"<details><summary><b>{esc(r.get('subject',''))}</b>"
            f"<span class=m>{esc(r.get('postdateCst',''))} · {esc(r.get('author',''))}"
            f" · 回复 {r.get('replies') if r.get('replies') is not None else '?'}"
            f" · 快照 {esc(r.get('snapshot',''))} · <a href='{r.get('url','')}' target=_blank>原帖</a>"
            f"</span>"
            f"<div class=body>{body or '<i>正文未抓取或为隐藏帖</i>'}</div></details>")
    html_doc = f"""<!doctype html><html lang=zh-cn><meta charset=utf-8>
<title>NGA 无限板块采集快照</title>
<style>
body{{font:15px/1.7 -apple-system,"PingFang SC",sans-serif;max-width:1000px;margin:24px auto;padding:0 16px;color:#222}}
h1{{font-size:20px}} .m{{color:#777;font-size:13px;margin-left:8px}}
details{{border-bottom:1px solid #eee;padding:8px 0}} summary{{cursor:pointer;list-style:none}}
summary::-webkit-details-marker{{display:none}}
.body{{margin:8px 0 4px 14px;padding:10px 12px;background:#fafafa;border-left:3px solid #ddd;white-space:normal}}
.note{{background:#fff7e6;border:1px solid #f0c36d;padding:10px 12px;border-radius:6px;font-size:13px}}
a{{color:#1a6fb8;text-decoration:none}} a:hover{{text-decoration:underline}}
</style>
<h1>NGA「{FORUM_NAME}」板块采集快照</h1>
<p class=note><b>这是内部选题参考，不是本站成品。</b>下面 {len(items)} 条帖子里的文字都是玩家原创，
按仓库红线：不转载、不摘要上页面、不进小程序，也不进 <code>app/data</code> 的数据基底。
生成于 {now_iso()}。</p>
<p>正文已抓 {len(bodies)} 条（点开条目展开）；未抓的只有列表元数据。</p>
{''.join(tr)}
</html>"""
    out = os.path.join(OUT_DIR, "view.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"查看页 → {out}（{len(items)} 条，正文 {len(bodies)} 条）")
    return 0


def esc(s):
    return unescape(re.sub(r"<[^>]+>", "", str(s or ""))).replace("&", "&amp;").replace("<", "&lt;")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("hot", help="访客态热帖（免登录）")
    b = sub.add_parser("board", help="登录态列表 + 正文")
    b.add_argument("--pages", type=int, default=2)
    b.add_argument("--max-body", type=int, default=60,
                   help="单次最多抓多少条正文（默认 60，0=不限）；防一次打太多把会话打进风控")
    b.add_argument("--no-body", action="store_true")
    sub.add_parser("view", help="生成/更新本地查看页")
    a = sub.add_parser("all", help="hot + board + view")
    a.add_argument("--pages", type=int, default=2)
    a.add_argument("--max-body", type=int, default=60)
    a.add_argument("--no-body", action="store_true")
    args = ap.parse_args()
    if args.cmd == "hot":
        return cmd_hot(args)
    if args.cmd == "board":
        return cmd_board(args)
    if args.cmd == "view":
        return cmd_view(args)
    if args.cmd == "all":
        rc1 = cmd_hot(args)
        rc2 = cmd_board(args) if has_cookie() else 1
        rc3 = cmd_view(args)
        return rc1 or rc2 or rc3
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
