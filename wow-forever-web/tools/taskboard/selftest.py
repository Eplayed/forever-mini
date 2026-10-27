#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskboard 自测：把六档状态的判定路径全走一遍。

为什么要这个：真实机器上只有「失败／空转／正常」三档有样本，
「应用没开／超期未跑／未加载」要等出事才看得到。等出事不是验证——
这里用假证据喂 classify()，确认代码路径确实会落到那几档、且落得对。
它证明的是判据逻辑，不冒充"这台机器真出过这事"。
"""
import copy
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

CST = timezone(timedelta(hours=8))
BASE = {"id": "t", "name": "n", "kind": "launchd", "owner": "", "status": "未知", "why": "",
        "last_run": "", "last_src": "", "exit": "", "note": "", "run": {"kind": "none"}, "groups": []}
ENT = {"id": "t", "name": "n", "kind": "launchd", "expect_within_hours": 13,
       "evidence": {"log": "", "ok_markers": ["退出码 0"], "fail_markers": ["Operation not permitted"]}}

n = 0
fails = []


def chk(label, got, want):
    global n
    n += 1
    if got == want:
        print("  ok   %-34s → %s" % (label, got))
    else:
        fails.append(label)
        print("  FAIL %-34s → %s（期望 %s）" % (label, got, want))


def row(kind="launchd", last_dt=None, exit_code=None, txt=""):
    e = copy.deepcopy(ENT)
    e["kind"] = kind
    r = copy.deepcopy(BASE)
    r["kind"] = kind
    return collect.classify(r, e, txt=txt, exit_code=exit_code, last_dt=last_dt)["status"]


def ago(h):
    return datetime.now(CST) - timedelta(hours=h)


print("[1] 六档判定")
chk("退出码 126 ＋ TCC 日志", collect.classify(
    {**BASE, "kind": "launchd"}, ENT, txt="bash: x.sh: Operation not permitted", exit_code="126",
    last_dt=ago(20))["status"], "失败")
chk("退出码 0，6 小时前跑过", row(exit_code="0", last_dt=ago(6)), "正常")
chk("退出码 2，刚跑过", row(exit_code="2", last_dt=ago(1)), "失败")
chk("很久没跑（40 小时 > 13）", row(last_dt=ago(40)), "超期未跑")
chk("没有任何证据", row(last_dt=None, exit_code="0"), "未知")
chk("launchd plist 在但没加载", collect.classify({**BASE, "kind": "launchd"}, ENT,
    exit_code="0", last_dt=ago(3), loaded=False)["status"], "未加载")
print("[2] 空转（被停用）优先于失败与正常")
off = {"id": "t", "kind": "cron", "expect_within_hours": 26,
       "evidence": {"log": "", "off_markers": ["已停用"], "off_files": [], "off_env": "X_OFF"}}
chk("日志命中「已停用」", collect.classify({**BASE, "kind": "cron"}, off,
    txt="2026-10-26 08:00 头条自动日程线已停用", exit_code="0", last_dt=ago(5))["status"], collect.IDLE)
chk("退出码非 0 但同时被停用 → 仍判空转", collect.classify({**BASE, "kind": "cron"}, off,
    txt="已停用", exit_code="1", last_dt=ago(5))["status"], collect.IDLE)
chk("命令行带 X_OFF=1", collect.classify({**BASE, "kind": "cron"}, off,
    txt="", extra_fail="off_env", last_dt=ago(5))["status"], collect.IDLE)
print("[3] 应用没开 / 未加载")
alive = collect.probe_local_port
collect.probe_local_port = lambda base: False
try:
    chk("端口没人听（有上次执行记录）", collect.classify({**BASE, "kind": "app"},
        {"id": "t", "kind": "app", "base_url": "http://127.0.0.1:1", "expect_within_hours": 26,
         "evidence": {}}, last_dt=ago(3))["status"], "应用没开")
finally:
    collect.probe_local_port = alive
chk("launchd 加载着 → 不因这条降级", collect.classify({**BASE, "kind": "launchd"}, ENT,
    exit_code="0", last_dt=ago(3), loaded=True)["status"], "正常")
print("[4] 执行白名单（不真跑东西）")
import server as tb  # noqa: E402   trigger() 住在 server.py，白名单在那儿

reg = {"real": {"id": "real", "run": {"kind": "none", "why": "被停用，不代跑"}},
       "bogus": {"id": "bogus", "run": {"kind": "teleport", "label": "x"}}}
tb.registry = lambda: reg
chk("id 不在登记表 → 拒", tb.trigger({"id": "nope", "name": "x"})[0], False)
chk("run.kind=none → 拒并给理由", tb.trigger({"id": "real", "name": "n"})[0], False)
chk("none 的理由透传", "不代跑" in tb.trigger({"id": "real", "name": "n"})[1], True)
chk("没声明过的 kind（teleport）→ 拒", tb.trigger({"id": "bogus", "name": "n"})[0], False)
print("[5] 判据不写死在代码里")
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "collect.py"), encoding="utf-8").read()
code_only = src.split('"""', 2)[2]
reg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.json"), encoding="utf-8"))
markers = set()
for tk in reg["tasks"]:
    ev = tk.get("evidence") or {}
    for k in ("ok_markers", "fail_markers", "off_markers"):
        markers.update(ev.get(k) or [])
    if ev.get("off_env"):
        markers.add(ev["off_env"])
chk("登记表里的判据关键词数量够多（不是空测试）", len(markers) >= 4, True)
bad = sorted(m for m in markers if m in code_only)
chk("这些关键词一个都不在 collect.py 正文里", bad, [])
env_keys = sorted(tk["id"] for tk in reg["tasks"] if (tk.get("run") or {}).get("kind") == "cmd"
                  and any(a.split("/")[-1] in code_only for a in tk["run"].get("argv", [])))
chk("登记表里写死的脚本名也没抄进代码", env_keys, [])

print("[6] P2 纯函数（临时文件，不碰真机器）")
import manage, plistlib, tempfile
tmpd = tempfile.mkdtemp(prefix="tb-selftest-")
cron = ["0 9 * * * /bin/bash /x/auto_daily.sh >> /tmp/a.log 2>&1",
        "0 8 * * 0,1,3,5 TOUTIAO_AUTOGEN_OFF=1 /usr/bin/python3 /y/pub.py >> /tmp/b.log 2>&1",
        "*/5 * * * * /usr/bin/true"]
out, err = manage.cron_set_enabled(cron, "auto_daily.sh", False)
chk("关一条 cron：加自己的前缀", bool(out) and out[0].startswith(manage.CRON_OFF), True)
chk("关 cron 时只动匹配那一条", out[1:] == cron[1:], True)
chk("cron 匹配到 0 条要拒绝", manage.cron_set_enabled(cron, "nope.sh", False)[0], None)
chk("cron 匹配到多条要拒绝", manage.cron_set_enabled(cron + ["9 auto_daily.sh x"], "auto_daily.sh", False)[0], None)
out2, err2 = manage.cron_set_enabled(out, "auto_daily.sh", True)
chk("再开回来等于原样", out2 == cron, True)
out3, err3 = manage.cron_set_time(cron, "auto_daily.sh", "07:15")
chk("改时刻只动分与时", out3[0].split()[0:2], ["15", "7"])
chk("周几等其余字段原样", out3[0].split()[2:5], cron[0].split()[2:5])
chk("非法时间被拒", manage.cron_set_time(cron, "auto_daily.sh", "25:99")[0], None)
closed = manage.cron_set_time(out, "auto_daily.sh", "06:00")[0]
chk("关着的行改时刻不顺手打开", closed[0].startswith(manage.CRON_OFF), True)
pj = os.path.join(tmpd, "p.plist")
manage.plist_write(pj, {"Label": "x", "StartCalendarInterval": [{"Hour": 8, "Minute": 40}, {"Hour": 20, "Minute": 40}]})
okp, msgp = manage.plist_set_times(pj, [(7, 5), (19, 25)])
chk("plist 改时刻并回读一致", (okp, manage.plist_read(pj)["StartCalendarInterval"]),
    (True, [{"Hour": 7, "Minute": 5}, {"Hour": 19, "Minute": 25}]))
jj = os.path.join(tmpd, "j.json")
open(jj, "w", encoding="utf-8").write('{\n "enabled": true,\n "run_at": "22:00",\n "note": ""\n}')
okj, mj = manage.json_patch_text(jj, "enabled", False)
chk("JSON 定点关 enabled", (okj, manage.json_patch_read(jj, "enabled")), (True, False))
okj2, mj2 = manage.json_patch_text(jj, "run_at", "23:10")
chk("JSON 改 run_at 且其余字段没被重排", (okj2, open(jj, encoding="utf-8").read().count('"note"')), (True, 1))
okj3, mj3 = manage.json_patch_text(jj, "nope_key", True)
chk("字段不存在要拒绝写盘", okj3, False)
chk("拒绝写盘时文件没被动过", manage.json_patch_read(jj, "enabled"), False)
bad = os.path.join(tmpd, "bad.json")
open(bad, "w", encoding="utf-8").write('{"enabled": true, ')   # 故意不合法
okbad, mbad = manage.json_patch_text(bad, "enabled", False)
chk("改完不是合法 JSON 就放弃", okbad, False)

print("\n%d 项，失败 %d 项" % (n, len(fails)))
if fails:
    print("失败项：" + "、".join(fails))
sys.exit(1 if fails else 0)
