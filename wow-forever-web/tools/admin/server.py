# -*- coding: utf-8 -*-
"""数据管线控制台 · 独立本地服务（与资料站两个服务互不相干）

    python tools/admin/server.py            # 默认 127.0.0.1:8830
    python tools/admin/server.py 8831       # 换端口

定位：站主自己的数据管理面板——看成品基底、来源与缺口，拉取待审快照，
执行已登记的白名单刷新链和检查命令。不接受任意命令或 URL；
只绑本机回环，不进发布口径（页面也不链回玩家站）。

数据架构三层（口径见 docs/DATA-MAINTENANCE.md）：
    app/data/upstream/  原始转述层（页面永不读）
    app/data/*.json     成品基底（唯一真相，两站+小程序都读）
    app/public/ 等       构建副本（永不手改）
公开物品 API 只落待审快照；已登记刷新链会改数据文件并跑门禁，
但绝不自动提交、发布或上传 OSS。
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

from catalog import catalog, gaps, records
import jobs

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.dirname(os.path.dirname(HERE))     # wow-forever-web/
DATA = os.path.join(WEB_ROOT, "app", "data")   # 2026-10-24 起站点基底在 app/ 下
UPSTREAM = os.path.join(DATA, "upstream")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8830
STALE_DAYS = 14                                        # 上游快照超过这个天数算不新鲜
OUT_MAX = 64 * 1024                                    # 命令输出截断

# 门禁白名单：id → 命令。全都只读或幂等（build-data 重跑会重写派生文件，但这正是它的本职）。
# 注意 status 不走 `bash tools/refresh.sh status`：refresh.sh 的 status 分支本来就只是
# python3 tools/data-status.py 一行，而本机只有 WSL bash（System32）+ 仓库 .sh 是 CRLF 行尾
# + 脚本里写的是 python3——三条凑齐必炸（2026-10-13 面板实测退出码 2）。直接跑同一行命令，语义等价。
GATES = {
    "status": {"label": "上游新鲜度", "cmd": [sys.executable, "tools/data-status.py"], "timeout": 120},
    "build-data": {"label": "数据校验", "cmd": ["node", "tools/build-data.js"], "timeout": 180},
    "site-dun": {"label": "副本详情回归", "cmd": [sys.executable, "tools/site-check.py", "--only", "dungeon_geo"], "timeout": 300},
}


def fstat(path):
    st = os.stat(path)
    return {"size": st.st_size, "mtime": st.st_mtime,
            "mtimeTxt": datetime.fromtimestamp(st.st_mtime).strftime("%m-%d %H:%M"),
            "age": round((time.time() - st.st_mtime) / 86400, 1)}


def count_items(obj):
    """条目数：数组给长度，对象给键数，其余 1。"""
    if isinstance(obj, list):
        return len(obj)
    if isinstance(obj, dict):
        return len(obj)
    return 1


def api_overview():
    files, ups = [], []
    for name in sorted(os.listdir(DATA)):
        p = os.path.join(DATA, name)
        if name == "upstream" or not name.endswith(".json"):
            continue
        s = fstat(p)
        try:
            n = count_items(json.load(open(p, encoding="utf-8")))
        except Exception as e:
            n = "解析失败: %s" % e
        files.append({"name": name, **s, "items": n})
    if os.path.isdir(UPSTREAM):
        for name in sorted(os.listdir(UPSTREAM)):
            p = os.path.join(UPSTREAM, name)
            if not name.endswith(".json"):
                continue
            s = fstat(p)
            ups.append({"name": "upstream/" + name, **s, "stale": s["age"] > STALE_DAYS})
    meta = {}
    dj = os.path.join(DATA, "dungeons.json")
    if os.path.exists(dj):
        m = json.load(open(dj, encoding="utf-8")).get("meta", {})
        meta = {"generatedAt": m.get("generatedAt"), "scrapedAt": (m.get("upstream") or {}).get("scrapedAt"),
                "bossPortraits": m.get("bossPortraits")}
    return {"files": files, "upstream": ups, "staleDays": STALE_DAYS, "meta": meta}


def api_dungeons():
    d = json.load(open(os.path.join(DATA, "dungeons.json"), encoding="utf-8"))
    rows = []
    for kind, arr in (("new", d.get("newDungeons", [])), ("classic", d.get("classicDungeons", [])),
                      ("raid", d.get("raids", []))):
        for x in arr:
            rows.append({
                "id": x.get("id"), "kind": kind,
                "nameCn": x.get("nameCn"), "nameEn": x.get("nameEn"),
                "nameCnConflict": x.get("nameCnConflict"),
                "levelRange": x.get("levelRange"),
                "rangeOfficial": x.get("levelRangeOfficial"),
                "rangeClient": x.get("levelRangeClient"),
                "partySize": x.get("partySize"), "partySizeAlt": x.get("partySizeAlt"),
                "bosses": len(x.get("bosses") or []),
                "drops": len(x.get("drops") or []),
                "level": x.get("level"), "art": x.get("art"),
            })
    return {"rows": rows}


def api_run(body):
    gid = (body or {}).get("id")
    if gid not in GATES:
        return 400, {"error": "不在白名单里（允许: %s）" % ", ".join(GATES)}
    with jobs.lock:
        if jobs.active is not None:
            return 409, {"error": "已有拉取、刷新或门禁任务运行"}
        jobs.active = "gate:" + gid
    g = GATES[gid]
    t0 = time.time()
    try:
        r = subprocess.run(g["cmd"], cwd=WEB_ROOT, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=g["timeout"])
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = 124, "超时（%ds）" % g["timeout"]
    except OSError as exc:
        code, out = 127, str(exc)
    finally:
        with jobs.lock:
            jobs.active = None
    if len(out.encode("utf-8", "replace")) > OUT_MAX:
        out = out[:OUT_MAX // 4] + "\n…（输出过长，已截断）\n" + out[-OUT_MAX // 4:]
    return 200, {"id": gid, "label": g["label"], "code": code,
                 "ms": int((time.time() - t0) * 1000), "out": out.strip()}


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, *a):  # 安静
        pass

    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(b)

    def _same_host(self):
        return self.headers.get("Host") in ("127.0.0.1:%d" % PORT, "localhost:%d" % PORT)

    def _same_origin(self):
        host = self.headers.get("Host")
        return self.headers.get("Origin") == "http://" + host

    def do_GET(self):
        if not self._same_host():
            return self._json(403, {"error": "仅限本机主机名"})
        if self.path == "/api/overview":
            return self._json(200, api_overview())
        if self.path == "/api/dungeons":
            return self._json(200, api_dungeons())
        if self.path == "/api/catalog":
            return self._json(200, {"topics": catalog(), "gaps": gaps()})
        if self.path == "/api/review/items":
            result = jobs.review_items()
            return self._json(200, result) if result else self._json(404, {"error": "尚无待审快照"})
        if urlsplit(self.path).path == "/api/records":
            params = parse_qs(urlsplit(self.path).query)
            try:
                result = records((params.get("topic") or [""])[0], (params.get("q") or [""])[0],
                                 int((params.get("offset") or ["0"])[0]))
                return self._json(200, result)
            except (ValueError, OSError, TypeError) as exc:
                return self._json(400, {"error": str(exc)})
        if self.path.startswith("/api/jobs/"):
            jid = self.path.rsplit("/", 1)[-1]
            job = jobs.get(jid)
            return self._json(200, job) if job else self._json(404, {"error": "任务不存在"})
        if urlsplit(self.path).path not in ("/", "/index.html"):
            return self._json(404, {"error": "no such page"})
        return super().do_GET()

    def do_HEAD(self):
        if not self._same_host() or urlsplit(self.path).path not in ("/", "/index.html"):
            self.send_response(404)
            self.end_headers()
            return
        return super().do_HEAD()

    def do_POST(self):
        if not self._same_host() or not self._same_origin():
            return self._json(403, {"error": "仅接受本机同源写请求"})
        if self.path not in ("/api/run", "/api/jobs"):
            return self._json(404, {"error": "no such api"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n < 1 or n > 4096:
                return self._json(413, {"error": "请求体大小错误"})
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                return self._json(400, {"error": "JSON 须为对象"})
        except Exception:
            return self._json(400, {"error": "bad json"})
        if self.path == "/api/jobs":
            code, obj = jobs.start(body.get("action"), body.get("topic"))
            return self._json(code, obj)
        code, obj = api_run(body)
        return self._json(code, obj)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print("数据管线控制台 → http://127.0.0.1:%d/  （只绑本机；Ctrl+C 停）" % PORT)
    srv.serve_forever()
