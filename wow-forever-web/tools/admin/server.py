# -*- coding: utf-8 -*-
"""数据管线控制台 · 独立本地服务（与资料站两个服务互不相干）

    python tools/admin/server.py            # 默认 127.0.0.1:8830
    python tools/admin/server.py 8831       # 换端口

定位：站主自己的数据管理面板——看成品基底与上游新鲜度、看 38 座副本的字段
缺口、一键跑白名单内的检查命令。只读 + 白名单命令，不接受任意命令；
只绑本机回环，不进发布口径（页面也不链回玩家站）。

数据架构三层（口径见 docs/DATA-MAINTENANCE.md）：
    app/data/upstream/  原始转述层（页面永不读）
    app/data/*.json     成品基底（唯一真相，两站+小程序都读）
    app/public/ 等       构建副本（永不手改）
本面板只读这三层 + 跑检查，不改任何数据文件。改数据的正规路径仍是
改 upstream 或 merge-*.js 后重跑合并——面板是眼睛，不是手。
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

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
    "status": {"label": "上游新鲜度", "cmd": ["python", "tools/data-status.py"], "timeout": 120},
    "build-data": {"label": "数据校验", "cmd": ["node", "tools/build-data.js"], "timeout": 180},
    "site-dun": {"label": "副本详情回归", "cmd": ["python", "tools/site-check.py", "--only", "dungeon_geo"], "timeout": 300},
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
    g = GATES[gid]
    t0 = time.time()
    try:
        r = subprocess.run(g["cmd"], cwd=WEB_ROOT, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=g["timeout"])
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = 124, "超时（%ds）" % g["timeout"]
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
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/overview":
            return self._json(200, api_overview())
        if self.path == "/api/dungeons":
            return self._json(200, api_dungeons())
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/run":
            return self._json(404, {"error": "no such api"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "bad json"})
        code, obj = api_run(body)
        return self._json(code, obj)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print("数据管线控制台 → http://127.0.0.1:%d/  （只绑本机；Ctrl+C 停）" % PORT)
    srv.serve_forever()
