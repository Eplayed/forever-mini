#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""函数计算 FC 3.0 Web 函数（Python 3.10 / Debian 11）的静态托管与轻量统计入口。

为什么是这个形态：FC3 的 Web 函数要求用户自己起一个监听端口的 HTTP Server，
启动命令 `python3 app.py`、监听端口 9000 与控制台创建页一致。
只用标准库，不装任何三方包——冷启动零安装、镜像内即跑。

新增轻量隐私统计接收端（2026-11-25）：
    POST /api/t  接收前端匿名低基数事件（PV / 停留时长 / 推荐位曝光与点击 / 外链归因），
                 不存 Cookie、不记录原始 IP（仅做含当日日期与盐值的单向哈希前 12 位用于估算日 UV），
                 以单行结构化 JSON `[PB_STAT] {...}` 输出到 stdout 供阿里云 FC 日志服务 SLS 查询。
                 返回 204 No Content，失败或超限快速拒收，绝不影响静态站点响应。

部署包结构（tools/build-fc-package.py 打出）：
    app.py   本文件
    dist/    Vite 构建产物（hash 路由 SPA）
"""
import hashlib
import http.server
import json
import mimetypes
import os
import secrets
import socketserver
import sys
from datetime import datetime, timedelta, timezone

PORT = 9000
BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BASE, "dist")
STAT_PATH = "/api/t"
MAX_STAT_BODY = 4096
ALLOWED_EVENTS = frozenset(("pv", "page_stay", "slot_view", "slot_click", "outbound_click", "search"))
ALLOWED_VW = frozenset(("mobile", "tablet", "desktop", "wide"))
STAT_SALT = os.environ.get("PB_STAT_SALT") or secrets.token_hex(16)
BJ_TZ = timezone(timedelta(hours=8))

mimetypes.add_type("application/javascript; charset=utf-8", ".js")
mimetypes.add_type("text/css; charset=utf-8", ".css")
mimetypes.add_type("application/json; charset=utf-8", ".json")


def _clean_str(val, max_len):
    if not isinstance(val, str):
        return ""
    s = "".join(ch for ch in val.strip() if ord(ch) >= 32 and ch not in ("\r", "\n"))
    return s[:max_len]


def _visitor_hash(client_ip, day_str):
    raw = "%s|%s|%s" % (STAT_SALT, day_str, client_ip or "unknown")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def sanitize_stat_payload(raw_obj, client_ip="", now=None):
    """校验并裁剪单条匿名统计事件；非法时返回 None。"""
    if not isinstance(raw_obj, dict):
        return None
    ev = _clean_str(raw_obj.get("ev"), 24)
    if ev not in ALLOWED_EVENTS:
        return None
    ts = now or datetime.now(BJ_TZ)
    day_str = ts.strftime("%Y-%m-%d")
    rec = {
        "ts": ts.isoformat(timespec="seconds"),
        "day": day_str,
        "ev": ev,
        "p": _clean_str(raw_obj.get("p"), 120) or "/",
        "vh": _visitor_hash(client_ip, day_str),
    }
    sid = _clean_str(raw_obj.get("sid"), 32)
    if sid:
        rec["sid"] = sid
    ref = _clean_str(raw_obj.get("ref"), 80)
    if ref:
        rec["ref"] = ref
    vw = _clean_str(raw_obj.get("vw"), 16)
    if vw in ALLOWED_VW:
        rec["vw"] = vw
    slot = _clean_str(raw_obj.get("slot"), 64)
    if slot:
        rec["slot"] = slot
    kind = _clean_str(raw_obj.get("kind"), 32)
    if kind:
        rec["kind"] = kind
    pos = _clean_str(raw_obj.get("pos"), 32)
    if pos:
        rec["pos"] = pos
    host = _clean_str(raw_obj.get("host"), 80)
    if host:
        rec["host"] = host
    ms = raw_obj.get("ms")
    if isinstance(ms, (int, float)) and not isinstance(ms, bool):
        ms_i = int(ms)
        if 0 <= ms_i <= 1800000:
            rec["ms"] = ms_i
    if ev == "search" and isinstance(raw_obj.get("hit"), bool):
        rec["hit"] = raw_obj["hit"]
    return rec


class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SITE, **kwargs)

    def _client_ip(self):
        xff = self.headers.get("X-Forwarded-For") or ""
        if xff:
            return xff.split(",", 1)[0].strip()
        xri = self.headers.get("X-Real-IP") or ""
        if xri:
            return xri.strip()
        return (self.client_address[0] if self.client_address else "") or ""

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path == STAT_PATH:
            self.send_response(405)
            self.send_header("Allow", "POST")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        fp = os.path.normpath(os.path.join(SITE, path.lstrip("/")))
        if os.path.isdir(fp):
            fp = os.path.join(fp, "index.html")
        if not fp.startswith(SITE) or not os.path.isfile(fp):
            # 旧页地址/坏路径必须真 404（2026-10-24 撤跳转桩的口径），不能 200 兜底成首页。
            # body 用友好的 404.html，但状态码是 404；hash 路由的真实导航只请求 / 与资源，不走这里。
            page = os.path.join(SITE, "404.html")
            if not os.path.isfile(page):
                self.send_error(404)
                return
            with open(page, "rb") as f:
                body = f.read()
            self.path = "/404.html"
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path != STAT_PATH:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = -1
        if length <= 0 or length > MAX_STAT_BODY:
            self.send_response(413 if length > MAX_STAT_BODY else 400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        raw = self.rfile.read(length)
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        rec = sanitize_stat_payload(obj, client_ip=self._client_ip())
        if rec is None:
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        sys.stdout.write("[PB_STAT] " + json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
        sys.stdout.flush()
        self.send_response(204)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def end_headers(self):
        p = self.path
        if p.split("?", 1)[0] == STAT_PATH:
            super().end_headers()
            return
        if "/assets/" in p:
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        elif p.endswith((".html", ".json", ".xml", ".txt")):
            self.send_header("Cache-Control", "public, max-age=300")
        else:
            self.send_header("Cache-Control", "public, max-age=86400")
        super().end_headers()

    def log_message(self, *args):
        pass  # 静态资源访问保持安静；统计事件以 [PB_STAT] 单行落 SLS 日志


if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), SPAHandler) as httpd:
        httpd.serve_forever()
