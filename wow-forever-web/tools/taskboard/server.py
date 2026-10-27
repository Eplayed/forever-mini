#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskboard 页面：读 ~/.taskboard/status.json 把四家族自动任务摆一张表。

第一期只读：只有「重新采集」这一个动作（它跑的是只读采集器，不碰任何任务）。
改周期、启停、立即执行是后面几期的事，那时才需要 token 与两道确认（设计见
wow-forever-web/docs/DEV-taskboard-2026-10-27.md 第六节）。

只绑 127.0.0.1：这页迟早要拿到能改 crontab 的手，不能对局域网开放。
"""
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
STATUS = os.path.expanduser("~/.taskboard/status.json")
COLLECT = os.path.join(HERE, "collect.py")
HOST, PORT = "127.0.0.1", 15830

CSS = """
:root{--bg:#0e1013;--panel:#171b22;--line:#2c3850;--txt:#e9e2d2;--dim:#8a93a5;--gold:#e0a96d;
--ok:#67c267;--fail:#c75c5c;--idle:#dd9f44;--late:#dd9f44}
*{box-sizing:border-box}body{margin:0;padding:22px;background:var(--bg);color:var(--txt);
font:14px/1.6 -apple-system,"PingFang SC",sans-serif}
h1{font-size:19px;margin:0 0 4px}sub{color:var(--dim);font-size:12px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}
.chip{background:var(--panel);border:1px solid var(--line);padding:6px 10px;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;background:var(--panel)}
th,td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}
th{color:var(--gold);font-weight:600;font-size:12px;letter-spacing:.04em}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.st{font-weight:600;white-space:nowrap}.st::before{content:"";display:inline-block;width:8px;height:8px;
margin-right:6px;border-radius:2px;background:currentColor}
.s-正常{color:var(--ok)}.s-失败{color:var(--fail)}.s-空转{color:var(--idle)}
.s-超期{color:var(--late)}.s-应用没开{color:var(--dim)}.s-未知{color:var(--dim)}
.dim{color:var(--dim);font-size:12px}.why{font-size:12.5px}
button{background:transparent;border:1px solid var(--gold);color:var(--gold);
padding:9px 14px;min-height:44px;cursor:pointer;font:inherit}
button:hover{background:rgba(224,169,109,.12)}
footer{margin-top:16px;color:var(--dim);font-size:12px}
@media(max-width:760px){table,th,td{display:block;width:auto}tr{border-bottom:1px solid var(--line);padding:6px 0}
th{display:none}td{border:0;padding:2px 10px}td::before{content:attr(data-l);color:var(--gold);
font-size:11px;display:block}}
"""
CLS = {"空转（已停用）": "空转", "应用没开": "应用没开"}


def load():
    try:
        with open(STATUS, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"rows": [], "summary": {}, "error": "读不到 %s：%s" % (STATUS, e)}


def render():
    d = load()
    rows = d.get("rows") or []
    chips = "".join('<span class="chip">%s × <b>%d</b></span>' % (k, v)
                    for k, v in (d.get("summary") or {}).items() if v)
    tr = ""
    for r in rows:
        st = r["status"]
        tr += ('<tr><td class="st s-%s"><span class="sr">%s</span></td>'
               '<td>%s<div class="dim">%s ｜ %s</div></td>'
               '<td class="num">%s</td><td class="num">%s</td>'
               '<td class="why">%s%s</td></tr>\n') % (
            CLS.get(st, st), st, r["name"], r["kind"], r.get("owner", ""),
            r.get("schedule", "") or "—",
            r.get("last_run", "") or "—",
            r.get("why", "") or "—",
            ('<div class="dim">注：%s</div>' % r["note"]) if r.get("note") else "")
    err = '<p class="s-失败">%s</p>' % d["error"] if d.get("error") else ""
    return ("<!doctype html><meta charset=utf-8><title>任务台</title>"
            "<style>%s</style><h1>任务台 · 本机自动执行的任务</h1>"
            "<sub>采集于 %s｜状态由 registry.json 声明的判据现算，页面不另存一份</sub>%s"
            '<div class="chips">%s<form method=post action=/refresh><button>重新采集</button></form></div>'
            "<table><thead><tr><th>状态</th><th>任务</th><th>调度</th><th>上次动作</th><th>依据</th></tr></thead>"
            "<tbody>%s</tbody></table>"
            "<footer>状态词分开用：<b>失败</b>＝跑过但非 0 退出；<b>空转</b>＝触发了但进去就退（配置里被停用）；"
            "<b>应用没开</b>＝这类的定时器活在应用进程里，没开就不会跑；<b>超期未跑</b>＝距上次超过预期窗口；"
            "<b>未知</b>＝没有可用证据。不靠颜色区分。</footer>") % (
        CSS, d.get("generatedAt", "?"), err, chips or "", tr or "<tr><td colspan=5>没有行</td></tr>")


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/status"):
            return self._send(200, json.dumps(load(), ensure_ascii=False, indent=1), "application/json; charset=utf-8")
        if self.path in ("/", "/index.html"):
            return self._send(200, render())
        return self._send(404, "404")

    def do_POST(self):
        if self.path != "/refresh":
            return self._send(404, "404")
        org = self.headers.get("Origin") or self.headers.get("Referer") or ""
        if org and ("127.0.0.1:%d" % PORT) not in org and ("localhost:%d" % PORT) not in org:
            return self._send(403, "只接受本机页面")
        try:
            r = subprocess.run([sys.executable, COLLECT], capture_output=True, text=True, timeout=120)
            note = "采集完成" if r.returncode == 0 else "采集失败：%s" % (r.stderr or "")[:200]
        except Exception as e:
            note = "采集器没跑起来：%s" % str(e)[:160]
        body = render().replace("<h1>", '<p class="dim">%s</p><h1>' % note, 1)
        return self._send(200, body)

    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (datetime.now().strftime("%H:%M:%S"), fmt % a))


def main():
    if not os.path.exists(STATUS):
        subprocess.run([sys.executable, COLLECT], capture_output=True)
    srv = ThreadingHTTPServer((HOST, PORT), H)
    print("任务台 http://%s:%d  状态文件 %s" % (HOST, PORT, STATUS), flush=True)
    threading.Timer(600, lambda: subprocess.run([sys.executable, COLLECT], capture_output=True)).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()
