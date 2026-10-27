#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskboard 采集器：只读地探四种调度机制，结果写 ~/.taskboard/status.json。

为什么代码与状态都放 ~/.taskboard 而不是仓库里跑：launchd 起的进程读不到
~/Documents（macOS TCC），同机现成反例是 com.zhangyajun.haosailei.asr 每晚退出码 126。
仓库里那份是源，装过去才轮到 launchd 跑（见 install.sh --sync）。

为什么"页面不开就看不到"这件事必须由独立进程解决：应用内定时器（video2text 那两组、
5177 那条）本来就在工作台没开时不跑，管理页若寄生在同一个应用里，
它关着的整天正是它最该报警的时候。所以采集器由 launchd 独立跑，页面只读一份 JSON。

判据不在本文件里硬编码，全部读 registry.json 的声明。
"""
import json
import os
import plistlib
import re
import sqlite3
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "registry.json")
OUT_DIR = os.path.expanduser("~/.taskboard")
OUT = os.path.join(OUT_DIR, "status.json")
CST = timezone(timedelta(hours=8))

OK = "正常"
FAIL = "失败"
IDLE = "空转（已停用）"
APP_DOWN = "应用没开"
LATE = "超期未跑"
UNKNOWN = "未知"
ORDER = [FAIL, IDLE, APP_DOWN, LATE, UNKNOWN, OK]


def p(path):
    return os.path.expanduser(os.path.expandvars(path or ""))


def now():
    return datetime.now(CST)


def iso(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def tail_text(path, chars=4000):
    f = p(path)
    if not os.path.exists(f):
        return "", None
    with open(f, "rb") as h:
        h.seek(0, os.SEEK_END)
        size = h.tell()
        h.seek(max(0, size - chars))
        text = h.read().decode("utf-8", "replace")
    return text, datetime.fromtimestamp(os.path.getmtime(f), CST)


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return r.stdout
    except Exception:
        return ""


def launchctl_rows():
    out = {}
    for line in run(["launchctl", "list"]).splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 3:
            out[parts[2]] = {"pid": parts[0], "exit": parts[1]}
    return out


def plist_of(label):
    f = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % label)
    if not os.path.exists(f):
        return {}
    try:
        with open(f, "rb") as h:
            return plistlib.load(h)
    except Exception:
        return {}


def sched_text(d):
    itv = d.get("StartCalendarInterval") or []
    if isinstance(itv, dict):
        itv = [itv]
    times = ["%02d:%02d" % (int(i.get("Hour", -1)) % 24, int(i.get("Minute", 0))) for i in itv]
    if not times:
        sec = d.get("StartInterval")
        return ("每 %d 分钟" % (int(sec) // 60)) if sec else "（plist 里没有日历调度）"
    return " / ".join(sorted(times))


def cron_lines():
    return [l.strip() for l in run(["crontab", "-l"]).splitlines() if l.strip() and not l.strip().startswith("#")]


def cron_five_fields(line):
    body = re.sub(r"^[A-Z_]+=\S+\s+", "", line)          # 去掉行首的环境变量前缀
    f = body.split()
    return f[:5] if len(f) >= 5 else []


def sql_last(db, table):
    """取某张表里"最近一次"的时间：列名按语义现找，不把列名抄死在登记表里。"""
    f = p(db)
    if not os.path.exists(f):
        return None, "库文件不存在"
    try:
        con = sqlite3.connect("file:%s?mode=ro" % f, uri=True, timeout=10)
        cols = [r[1] for r in con.execute("pragma table_info(%s)" % table)]
        PREF = ("finished", "ended", "last", "next", "started", "run", "updated", "created")
        cand = [c for c in cols if re.search(r"(_at|_date|_ts)$|^date$", c, re.I) and "key" not in c.lower()]
        cand.sort(key=lambda c: min([i for i, k in enumerate(PREF) if k in c.lower()] or [90]))
        if not cand:
            return None, "%s 里没有像时间的列（列：%s）" % (table, ",".join(cols[:8]))
        q = "select max(%s) from %s" % (cand[0], table)
        v = con.execute(q).fetchone()[0]
        n = con.execute("select count(*) from %s" % table).fetchone()[0]
        con.close()
        return v, "%s.%s 共 %d 行" % (table, cand[0], n)
    except Exception as e:
        return None, "读库失败：%s" % (str(e)[:60])


def http_alive(base):
    try:
        with urllib.request.urlopen(base, timeout=2):
            return True
    except Exception as e:
        # 有响应但非 2xx 也算进程在（例如 404），只有连不上才算没开
        return "HTTP" in type(e).__name__ and False


def probe_local_port(base):
    m = re.match(r"https?://(127\.0\.0\.1|localhost):(\d+)", base or "")
    if not m:
        return None
    port = m.group(2)
    out = run(["lsof", "-nP", "-iTCP:%s" % port, "-sTCP:LISTEN"])
    return bool(out and "LISTEN" in out)


def evidence_row(entry, rows):
    """按声明收证据：上次活动时间、来源、退出码、日志里的关键词命中。"""
    row = {"id": entry["id"], "name": entry["name"], "kind": entry["kind"],
           "owner": entry.get("owner", ""), "status": UNKNOWN, "why": "",
           "last_run": "", "last_src": "", "exit": "", "note": entry.get("hint", ""),
           "run": entry.get("run") or {"kind": "none", "why": "登记表里没声明可执行动作，页面不给按钮"},
           "groups": []}
    ev = entry.get("evidence") or {}
    txt, mtime = tail_text(ev.get("log", ""))
    if mtime:
        row["last_run"] = iso(mtime)
        row["last_src"] = os.path.basename(p(ev["log"]))
    return row, txt


def classify(row, entry, txt=None, extra_fail=None, exit_code=None, last_dt=None):
    ev = entry.get("evidence") or {}
    expect = float(entry.get("expect_within_hours") or 0)
    low = (txt or "").lower()
    hits_off = [m for m in ev.get("off_markers", []) if m.lower() in low]
    off_files = [f for f in ev.get("off_files", []) if os.path.exists(p(f))]
    if hits_off or off_files or extra_fail == "off_env":
        row["status"] = IDLE
        row["why"] = "触发得到，但进去就退出：命中「%s」%s" % (
            "、".join(hits_off) or "停用标记", "；停用文件在：" + ", ".join(os.path.basename(p(f)) for f in off_files) if off_files else "")
        return row
    if exit_code not in (None, "", "0", 0):
        row["status"] = FAIL
        row["why"] = "退出码 %s" % exit_code
        for m in ev.get("fail_markers", []):
            if m.lower() in low:
                row["why"] += "，日志里有「%s」" % m
                break
        return row
    if row["kind"] == "app":
        alive = probe_local_port(entry.get("base_url"))
        if alive is False:
            row["status"] = APP_DOWN
            row["why"] = "端口没人听，这一类定时器活在应用进程里，没开就不跑"
            return row
    if last_dt is not None:
        row["last_run"] = iso(last_dt)
    if row["last_run"] and expect:
        hours = (now() - datetime.strptime(row["last_run"], "%Y-%m-%d %H:%M").replace(tzinfo=CST)).total_seconds() / 3600.0
        if hours > expect:
            row["status"] = LATE
            row["why"] = "距上次 %d 小时，超过预期 %.0f 小时" % (hours, expect)
            return row
        row["status"] = OK
        row["why"] = "%.1f 小时前动过（预期 %.0f 小时内）" % (hours, expect)
        return row
    if not row["last_run"]:
        row["status"] = UNKNOWN
        row["why"] = row["why"] or "没有可用证据（日志与状态文件都没找到）"
    else:
        row["status"] = OK
    return row


def collect():
    reg = json.load(open(REGISTRY, encoding="utf-8"))
    tasks = reg["tasks"]
    lc = launchctl_rows()
    crons = cron_lines()
    rows = []
    for e in tasks:
        k = e["kind"]
        row, txt = evidence_row(e, rows)
        if k == "launchd":
            info = lc.get(e["label"]) or {}
            d = plist_of(e["label"])
            row["schedule"] = sched_text(d) if d else "（没装 plist）"
            row["last_src"] = row["last_src"] or (os.path.basename(p(d.get("StandardErrorPath", ""))) if d else "")
            if not row["last_run"]:
                for key in ("StandardErrorPath", "StandardOutPath"):
                    _t, m = tail_text(d.get(key, ""))
                    if m:
                        row["last_run"] = iso(m)
                        row["last_src"] = os.path.basename(p(d[key]))
                        txt = (_t if _t else txt)
                        break
            row = classify(row, e, txt=txt, exit_code=info.get("exit"),
                           last_dt=datetime.strptime(row["last_run"], "%Y-%m-%d %H:%M") if row["last_run"] else None)
            if info:
                row["exit"] = info.get("exit", "") + ("（PID %s 在跑）" % info["pid"] if info.get("pid", "-") != "-" else "")
        elif k == "cron":
            line = next((l for l in crons if e["cron_hint"] in l), "")
            f5 = cron_five_fields(line)
            row["schedule"] = " ".join(f5) if f5 else "（crontab 里找不到这条）"
            off_env = e.get("evidence", {}).get("off_env")
            extra = "off_env" if (off_env and re.search(r"\b%s=1" % off_env, line)) else None
            dt = None
            _t, m = tail_text(e.get("evidence", {}).get("log", ""))
            if m:
                dt = m
            row = classify(row, e, txt=txt or _t, extra_fail=extra, last_dt=dt)
            if extra:
                row["note"] = (row["note"] + "；命令行带 %s=1" % off_env).strip("；")
        elif k == "app":
            st = {}
            if e.get("state") and os.path.exists(p(e["state"])):
                try:
                    st = json.load(open(p(e["state"]), encoding="utf-8"))
                except Exception as ex:
                    row["why"] = "状态文件读不了：%s" % str(ex)[:50]
            lst, src = [], ""
            if isinstance(st, dict) and isinstance(st.get("tasks"), list):
                for t in st["tasks"]:
                    lst.append("%s %s@%s" % (t.get("name"), "每%s天" % t.get("interval_days"), t.get("run_at")))
                    row["last_run"] = max([x for x in [row["last_run"], (t.get("last_run") or "")[:16]] if x])
                src = os.path.basename(p(e["state"])) + "（每组的上次执行）"
                row["exit"] = ",".join(sorted({str(t.get("last_status")) for t in st["tasks"]}))
                row["schedule"] = "；".join(lst)
                if e.get("groups"):
                    for t in st["tasks"]:
                        row["groups"].append({"name": t.get("name"), "sched": "每%s天@%s" % (
                            t.get("interval_days"), t.get("run_at")), "last": (t.get("last_run") or "—")[:16],
                            "status": t.get("last_status") or "?"})
            elif isinstance(st, dict):
                row["schedule"] = "%s（开关 %s）" % (st.get("run_at", "?"), "开" if st.get("enabled") else "关")
                src = os.path.basename(p(e["state"]))
                q = e.get("run_table")
                if q:
                    v, why = sql_last(e.get("db", ""), q)
                    if v:
                        row["last_run"] = str(v)[:16]
                        src = why
                    else:
                        row["why"] = why
            row["last_src"] = src
            dt = None
            if row["last_run"]:
                try:
                    dt = datetime.strptime(row["last_run"][:16], "%Y-%m-%d %H:%M").replace(tzinfo=CST)
                except Exception:
                    dt = None
            row = classify(row, e, last_dt=dt)
        elif k == "qoder":
            snap = p(e.get("snapshot", ""))
            if os.path.exists(snap):
                try:
                    d = json.load(open(snap, encoding="utf-8"))
                    ts = d.get("tasks") or d if isinstance(d, list) else d.get("tasks", [])
                    names, stamps = [], []
                    for t in ts:
                        sc = ((t.get("trigger") or {}).get("schedule") or {})
                        at = t.get("lastRunAt")
                        dt = datetime.fromtimestamp(at / 1000, CST) if at else None
                        if dt:
                            stamps.append(dt)
                        names.append("%s｜%s｜上次 %s｜%s" % (
                            t.get("name"), sc.get("expression") or sc.get("kind"),
                            dt.strftime("%m-%d %H:%M") if dt else "?", t.get("lastRunStatus") or "?"))
                    joined = "；".join(names)
                    row["schedule"] = (joined[:110] + "…（共 %d 条）" % len(ts)) if len(joined) > 120 else (joined or "快照里没有任务")
                    row["last_src"] = "agent 同步于 " + str(d.get("syncedAt", "?"))
                    if stamps:
                        row["last_run"] = iso(max(stamps))
                except Exception as ex:
                    row["why"] = "快照读不了：%s" % str(ex)[:60]
            else:
                row["schedule"] = "（没有快照文件）"
                row["why"] = "Qoder 定时任务本地没有稳定可读的存储，需 agent 用 qoder_cron list 写一份到 " + snap
            dt2 = None
            if row["last_run"]:
                dt2 = datetime.strptime(row["last_run"], "%Y-%m-%d %H:%M").replace(tzinfo=CST)
            row = classify(row, e, last_dt=dt2)
            if dt2:
                row["why"] += "（快照只读）"
        rows.append(row)
    rows.sort(key=lambda r: (ORDER.index(r["status"]), r["name"]))
    out = {"generatedAt": now().strftime("%Y-%m-%d %H:%M:%S"), "tz": "Asia/Shanghai(+08)",
           "source": REGISTRY, "count": len(rows),
           "summary": {s: sum(1 for r in rows if r["status"] == s) for s in ORDER},
           "rows": rows}
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    return out


def main():
    out = collect()
    print("采集完成 %s ｜ %d 条 ｜ %s" % (out["generatedAt"], out["count"],
          " ".join("%s×%d" % (k, v) for k, v in out["summary"].items() if v)))
    for r in out["rows"]:
        print("%-6s %-26s %-22s %s" % (r["status"], r["name"][:26], (r["last_run"] or "—")[:16], r["why"][:58]))
    print("→ " + OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
