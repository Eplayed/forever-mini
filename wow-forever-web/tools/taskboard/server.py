#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskboard 页面：读 ~/.taskboard/status.json 摆一张全机自动任务的健康表。

P1 起多了「立即执行」。三条边界，都是刻意的：
  · **只能执行 registry.json 里声明过的动作**（kickstart 或写死的 argv），
    页面不接受任何来自浏览器的命令文本——能跑什么由仓库里那份登记表决定。
  · 每次启动生成一次性 token，写进页面与请求；只接本机 Origin。
    这页迟早要拿到改 crontab 的手，不能对局域网敞开。
  · 改周期、启停、删任务（P2）没做。触发是异步的：kickstart 与长脚本都不阻塞页面，
    结果写进 ~/.taskboard/audit.log，页面上给"已触发＋去哪看"。
"""
import json
import manage
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HOME_DIR = os.path.expanduser("~/.taskboard")
STATUS = os.path.join(HOME_DIR, "status.json")
REGISTRY = os.path.join(HOME_DIR, "registry.json")
AUDIT = os.path.join(HOME_DIR, "audit.log")
COLLECT = os.path.join(HERE, "collect.py")
HOST, PORT = "127.0.0.1", 15830
TOKEN = secrets.token_urlsafe(9)

CSS = """
:root{--bg:#0e1013;--panel:#171b22;--line:#2c3850;--txt:#e9e2d2;--dim:#8a93a5;--gold:#e0a96d;
--ok:#67c267;--fail:#c75c5c;--idle:#dd9f44}
*{box-sizing:border-box}body{margin:0;padding:22px;background:var(--bg);color:var(--txt);
font:14px/1.6 -apple-system,"PingFang SC",sans-serif}
h1{font-size:19px;margin:0 0 4px}sub{color:var(--dim);font-size:12px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0;align-items:center}
.chip{background:var(--panel);border:1px solid var(--line);padding:6px 10px;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;background:var(--panel);table-layout:fixed}
col.c-st{width:96px}col.c-op{width:190px}col.c-name{width:15%}col.c-sch{width:17%}col.c-last{width:12%}
.wrap{overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}
td,th{word-break:break-word;overflow-wrap:anywhere}
th{color:var(--gold);font-weight:600;font-size:12px;letter-spacing:.04em}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.st{font-weight:600;white-space:nowrap}.st::before{content:"";display:inline-block;width:8px;height:8px;
margin-right:6px;border-radius:2px;background:currentColor}
.s-正常{color:var(--ok)}.s-失败{color:var(--fail)}.s-空转{color:var(--idle)}
.s-超期{color:var(--idle)}.s-应用没开{color:var(--dim)}.s-未知{color:var(--dim)}
.dim{color:var(--dim);font-size:12px}.why{font-size:12.5px}
.grp{font-size:12px;color:var(--dim);font-variant-numeric:tabular-nums}
.grp b{color:var(--txt);font-weight:600}
form{display:inline-block;margin:2px 0}
button{background:transparent;border:1px solid var(--gold);color:var(--gold);
padding:9px 12px;min-height:44px;cursor:pointer;font:inherit;white-space:nowrap}
button:hover:not(:disabled){background:rgba(224,169,109,.12)}
button:disabled{border-color:var(--line);color:var(--dim);cursor:not-allowed}
.note{margin:10px 0;padding:9px 12px;border-left:3px solid var(--gold);background:var(--panel);font-size:13px}
.note.bad{border-left-color:var(--fail)}
footer{margin-top:16px;color:var(--dim);font-size:12px}
@media(max-width:820px){table,th,td{display:block;width:auto}tr{border-bottom:1px solid var(--line);padding:6px 0}
th{display:none}td{border:0;padding:2px 10px}td[data-l]::before{content:attr(data-l);color:var(--gold);
font-size:11px;display:block}}
"""
CLS = {"空转（配置里停用）": "空转"}


def load():
    try:
        with open(STATUS, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"rows": [], "summary": {}, "error": "读不到 %s：%s" % (STATUS, e)}


def registry():
    try:
        with open(REGISTRY, encoding="utf-8") as f:
            return {t["id"]: t for t in json.load(f).get("tasks", [])}
    except Exception:
        return {}


def audit(rec):
    rec["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def expand(a):
    return os.path.expanduser(os.path.expandvars(a))


def trigger(row):
    """只执行登记表里声明过的动作。返回 (是否成功, 说明)。"""
    reg = registry().get(row["id"])
    if not reg:
        return False, "登记表里没有这条 id，拒绝执行"
    spec = reg.get("run") or {}
    kind = spec.get("kind")
    if kind == "none" or not kind:
        return False, spec.get("why", "这条没声明可执行动作")
    if kind == "kickstart":
        label = reg.get("label")
        r = subprocess.run(["launchctl", "kickstart", "-k", "gui/%d/%s" % (os.getuid(), label)],
                           capture_output=True, text=True, timeout=30)
        ok = r.returncode == 0
        return ok, ("已 kickstart %s" % label if ok else "kickstart 失败：%s" % (r.stderr or r.stdout)[:160])
    if kind == "cmd":
        argv = [expand(a) for a in spec.get("argv", [])]
        if not argv:
            return False, "run.argv 是空的"
        log = os.path.join(HOME_DIR, "run-%s-%s.log" % (row["id"], time.strftime("%Y%m%d-%H%M%S")))
        h = open(log, "w")
        p = subprocess.Popen(argv, stdout=h, stderr=subprocess.STDOUT, cwd=os.path.dirname(argv[0]))
        return True, "已在后台起（PID %s），输出看 %s；跑完点「重新采集」看状态" % (p.pid, os.path.basename(log))
    return False, "未知的 run.kind：%s" % kind


def do_toggle(row, want_on):
    """启停。只按 registry 的 manage.toggle 走，且每一步都备份＋回读。"""
    reg = registry().get(row["id"]) or {}
    mg = reg.get("manage") or {}
    kind = mg.get("toggle")
    if kind in (None, "none"):
        return False, mg.get("why", "这条没声明可启停")
    if kind == "launchd":
        label = reg.get("label", "")
        plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % label)
        if not os.path.exists(plist):
            return False, "找不到 plist：%s" % plist
        bdir = manage.backup([plist])
        ok, msg = manage.launchd_set(label, plist, want_on)
        return ok, "%s（plist 备份在 %s）" % (msg, bdir.replace(os.path.expanduser("~"), "~"))
    if kind == "cron":
        bdir = manage.backup([])
        manage.snapshot_cron(bdir)
        lines = manage.read_cron().splitlines()
        out, err = manage.cron_set_enabled(lines, reg.get("cron_hint", ""), want_on)
        if err:
            return False, err
        ok, msg = manage.apply_cron(out, row["id"])
        if not ok:
            manage.restore_cron(bdir)
            msg += "；已自动恢复备份 " + bdir.replace(os.path.expanduser("~"), "~")
        return ok, "crontab 整表覆盖过一次，回读校验%s（备份 %s）" % (
            "通过" if ok else "没过", bdir.replace(os.path.expanduser("~"), "~"))
    if kind == "json":
        path = manage.expand(mg.get("json", ""))
        if not os.path.exists(path):
            return False, "找不到配置文件 %s" % path
        bdir = manage.backup([path])
        ok, msg = manage.json_patch_text(path, "enabled", want_on)
        return ok, "%s（备份 %s）" % (msg, bdir.replace(os.path.expanduser("~"), "~"))
    return False, "未知的 toggle 类型 %s" % kind


def do_schedule(row, hm):
    """改时刻。launchd 改 plist、cron 只改分与时、json 改 run_at。都不动别的字段。"""
    reg = registry().get(row["id"]) or {}
    mg = reg.get("manage") or {}
    kind = mg.get("reschedule")
    if kind in (None, "none"):
        return False, mg.get("why", "这条没声明可改周期")
    if not manage.TIME_RE.match(hm or ""):
        return False, "时间要 HH:MM 这种格式"
    if kind == "launchd":
        label = reg.get("label", "")
        plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % label)
        bdir = manage.backup([plist])
        h, m = hm.split(":")
        old = manage.plist_read(plist).get("StartCalendarInterval") or []
        n = len(old) if isinstance(old, list) else 1
        ok, msg = manage.plist_set_times(plist, [(int(h), int(m))] * n)
        if not ok:
            manage.backup([plist]) and shutil.copy2(os.path.join(bdir, os.path.basename(plist)), plist)
            return False, "回读不符，已恢复原 plist"
        loaded = manage.launchctl_loaded(label)
        if loaded:
            subprocess.run(["launchctl", "bootout", "gui/%d/%s" % (os.getuid(), label)], capture_output=True)
            subprocess.run(["launchctl", "bootstrap", "gui/%d" % os.getuid(), plist], capture_output=True)
        return True, "%s；%s（备份 %s）" % (msg, "已按新时刻重新加载" if loaded else "没加载着，只改了文件",
                                    bdir.replace(os.path.expanduser("~"), "~"))
    if kind == "cron":
        bdir = manage.backup([])
        manage.snapshot_cron(bdir)
        lines = manage.read_cron().splitlines()
        out, err = manage.cron_set_time(lines, reg.get("cron_hint", ""), hm)
        if err:
            return False, err
        ok, msg = manage.apply_cron(out, row["id"])
        if not ok:
            manage.restore_cron(bdir)
        return ok, msg + "（备份 %s）" % bdir.replace(os.path.expanduser("~"), "~")
    if kind == "json":
        path = manage.expand(mg.get("json", ""))
        bdir = manage.backup([path])
        ok, msg = manage.json_patch_text(path, "run_at", hm)
        return ok, "%s（备份 %s）" % (msg, bdir.replace(os.path.expanduser("~"), "~"))
    return False, "未知的 reschedule 类型 %s" % kind


def render(banner=None):
    d = load()
    rows = d.get("rows") or []
    chips = "".join('<span class="chip">%s × <b>%d</b></span>' % (k, v)
                    for k, v in (d.get("summary") or {}).items() if v)
    tr = ""
    for r in rows:
        st = r["status"]
        run = r.get("run") or {"kind": "none"}
        if run.get("kind") in (None, "none"):
            act = '<button disabled title="%s">不可执行</button><div class="dim">%s</div>' % (
                run.get("why", ""), (run.get("why", "") or "")[:34])
        else:
            warn = run.get("warn", "")
            act = ('<form method=post action=/api/run onsubmit="return confirm(\'真的现在跑「%s」？\\n%s\')">'
                   '<input type=hidden name=id value="%s"><input type=hidden name=t value="%s">'
                   '<button%s>立即执行</button></form>') % (
                r["name"].replace("'", ""), warn.replace("'", ""), r["id"], TOKEN,
                ' style="border-color:var(--fail);color:var(--fail)"' if warn else "")
        mg = r.get("manage") or {}
        on = (r.get("loaded") if r["kind"] == "launchd" else
              (not r.get("cron_off")) if r["kind"] == "cron" else r.get("enabled_flag"))
        tk = mg.get("toggle")
        if tk in (None, "none") or on is None:
            tog = '<button disabled>不可启停</button>'
        else:
            act_word = "停用" if on else "开回来"
            tog = ('<form method=post action=/api/toggle onsubmit="return confirm(\'真的%s「%s」？\')">'
                   '<input type=hidden name=id value="%s"><input type=hidden name=want value="%s">'
                   '<input type=hidden name=t value="%s"><button%s>%s</button></form>') % (
                act_word, r["name"].replace("'", ""), r["id"], "off" if on else "on", TOKEN,
                ' style="border-color:var(--fail);color:var(--fail)"' if on else "", act_word)
        if mg.get("reschedule") not in (None, "none"):
            sch = ('<form method=post action=/api/schedule onsubmit="return confirm(\'改这条的触发时刻？\')">'
                   '<input type=time name=hm value="%s" required style="background:var(--panel);'
                   'color:var(--txt);border:1px solid var(--line);min-height:44px;padding:6px">'
                   '<input type=hidden name=id value="%s"><input type=hidden name=t value="%s">'
                   '<button>改时刻</button></form>') % (
                (r.get("last_run") or "")[11:16] if False else "", r["id"], TOKEN)
        else:
            sch = '<div class="dim">时刻不在这里改：%s</div>' % (mg.get("why") or "没声明")
        act = act + tog + sch
        grp = "".join('<div class="grp">%s <b>%s</b> ｜ %s ｜ %s</div>' % (
            g["name"], g["sched"], g["last"], g["status"]) for g in (r.get("groups") or []))
        tr += ('<tr><td class="st s-%s">%s</td>'
               '<td data-l="任务">%s<div class="dim">%s ｜ %s</div></td>'
               '<td class="num" data-l="调度">%s</td>'
               '<td class="num" data-l="上次动作">%s%s</td>'
               '<td class="why" data-l="依据">%s%s</td><td data-l="操作">%s</td></tr>\n') % (
            CLS.get(st, st), st, r["name"], r["kind"], r.get("owner", ""),
            r.get("schedule", "") or "—", r.get("last_run", "") or "—", grp,
            r.get("why", "") or "—",
            ('<div class="dim">注：%s</div>' % r["note"]) if r.get("note") else "", act)
    bn = ""
    if banner:
        bn = '<div class="note%s">%s</div>' % (" bad" if not banner[0] else "", banner[1])
    err = '<div class="note bad">%s</div>' % d["error"] if d.get("error") else ""
    return ("<!doctype html><meta charset=utf-8><title>任务台</title><style>%s</style>"
            "<h1>任务台 · 本机自动执行的任务</h1>"
            "<sub>采集于 %s｜状态由 registry.json 声明的判据现算，页面不另存一份｜"
            "「立即执行」只能跑登记表里声明过的动作</sub>%s%s"
            '<div class="chips">%s<form method=post action=/refresh><button>重新采集</button></form></div>'
            "<div class=wrap><table><colgroup><col class=c-st><col class=c-name><col class=c-sch><col class=c-last><col><col class=c-op></colgroup><thead><tr><th>状态</th><th>任务</th><th>调度</th><th>上次动作</th>"
            "<th>依据</th><th>操作（执行 / 启停 / 时刻）</th></tr></thead><tbody>%s</tbody></table></div>"
            "<footer>状态词分开用：<b>失败</b>＝跑过但非 0 退出；<b>空转</b>＝触发了但进去就退（配置里被停用）；"
            "<b>应用没开</b>＝这类定时器活在应用进程里，没开就不跑；<b>超期未跑</b>＝距上次超过预期窗口；"
            "<b>未知</b>＝没有可用证据。除颜色外都带文字。执行记录在 <b>~/.taskboard/audit.log</b>。"
            "改周期与启停（P2）没做。</footer>") % (
        CSS, d.get("generatedAt", "?"), err, bn, chips or "", tr or "<tr><td colspan=6>没有行</td></tr>")


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _local(self):
        org = self.headers.get("Origin") or self.headers.get("Referer") or ""
        return (not org) or ("127.0.0.1:%d" % PORT in org) or ("localhost:%d" % PORT in org)

    def do_GET(self):
        if self.path.startswith("/api/status"):
            return self._send(200, json.dumps(load(), ensure_ascii=False, indent=1), "application/json; charset=utf-8")
        if self.path in ("/", "/index.html"):
            return self._send(200, render())
        return self._send(404, "404")

    def _form(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8") if n else ""
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}

    def do_POST(self):
        if not self._local():
            return self._send(403, "只接受本机页面")
        if self.path == "/refresh":
            try:
                r = subprocess.run([sys.executable, COLLECT], capture_output=True, text=True, timeout=120)
                bn = (True, "采集完成") if r.returncode == 0 else (False, "采集失败：%s" % (r.stderr or "")[:200])
            except Exception as e:
                bn = (False, "采集器没跑起来：%s" % str(e)[:160])
            return self._send(200, render(bn))
        if self.path in ("/api/toggle", "/api/schedule"):
            f = self._form()
            if f.get("t") != TOKEN:
                return self._send(403, render((False, "令牌不对或页面是旧的，没改任何东西")))
            rows = {r["id"]: r for r in load().get("rows", [])}
            row = rows.get(f.get("id"))
            if not row:
                return self._send(400, render((False, "登记表里没有这个 id，没改")))
            if self.path == "/api/toggle":
                want_on = f.get("want") == "on"
                ok, msg = do_toggle(row, want_on)
                audit({"action": "toggle", "id": row["id"], "name": row["name"],
                       "want": "on" if want_on else "off", "ok": ok, "detail": msg})
                head = ("已停用" if not want_on else "已开回来") if ok else "没改"
            else:
                ok, msg = do_schedule(row, f.get("hm", ""))
                audit({"action": "schedule", "id": row["id"], "name": row["name"],
                       "hm": f.get("hm"), "ok": ok, "detail": msg})
                head = "已改时刻" if ok else "没改"
            try:
                subprocess.run([sys.executable, COLLECT], capture_output=True, timeout=120)
            except Exception:
                pass
            return self._send(200, render((ok, "%s：%s ｜ %s ｜ 记录在 audit.log" % (head, row["name"], msg))))
        if self.path == "/api/run":
            f = self._form()
            if f.get("t") != TOKEN:
                return self._send(403, render((False, "令牌不对或页面是旧的（服务重启过就刷新一次），没执行任何东西")))
            rows = {r["id"]: r for r in load().get("rows", [])}
            row = rows.get(f.get("id"))
            if not row:
                return self._send(400, render((False, "登记表里没有这个 id，没执行")))
            ok, msg = trigger(row)
            audit({"action": "run", "id": row["id"], "name": row["name"], "ok": ok, "detail": msg})
            try:
                subprocess.run([sys.executable, COLLECT], capture_output=True, timeout=120)
            except Exception:
                pass
            return self._send(200, render((ok, ("已执行：%s ｜ %s" % (row["name"], msg)) if ok else ("没执行：%s ｜ %s" % (row["name"], msg)))))
        return self._send(404, "404")

    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (datetime.now().strftime("%H:%M:%S"), fmt % a))


def refresh_loop():
    while True:
        time.sleep(600)
        try:
            subprocess.run([sys.executable, COLLECT], capture_output=True, timeout=120)
        except Exception:
            pass


def main():
    if not os.path.exists(STATUS):
        subprocess.run([sys.executable, COLLECT], capture_output=True)
    threading.Thread(target=refresh_loop, daemon=True).start()
    print("任务台 http://%s:%d" % (HOST, PORT), flush=True)
    print("一次性令牌（本次启动有效，写进页面）：%s" % TOKEN, flush=True)
    print("执行记录：%s" % AUDIT, flush=True)
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()


if __name__ == "__main__":
    main()
