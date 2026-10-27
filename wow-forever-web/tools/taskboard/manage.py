#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2 的改动逻辑：启停与改周期。

分成两类东西：
  · **纯函数**（cron 文本改写、plist 改写、JSON 里 enabled/run_at 的定点改写）——
    可以拿临时文件测，不用碰真机器。
  · **落地动作**（写文件、launchctl bootout/bootstrap、crontab -）——
    一律先备份到 ~/.taskboard/backup/<时间戳>/，写完**回读校验**，
    校验不过就自动恢复备份并报错。crontab 是整表覆盖，这一条不是谨慎是必需。

不接受任何来自浏览器的命令文本：能改哪些文件、改哪个字段，全由 registry.json 的 manage 声明决定。
"""
import json
import os
import plistlib
import re
import shutil
import subprocess
import time
from datetime import datetime

HOME_DIR = os.path.expanduser("~/.taskboard")
BACKUP_ROOT = os.path.join(HOME_DIR, "backup")
CRON_OFF = "#taskboard:off "


def ts():
    return time.strftime("%Y%m%d-%H%M%S")


def backup(paths):
    """把要动的原件复制进 backup/<ts>/，返回目录（写动作前先调用）。"""
    d = os.path.join(BACKUP_ROOT, ts())
    os.makedirs(d, exist_ok=True)
    for p in paths:
        if p and os.path.exists(p):
            shutil.copy2(p, os.path.join(d, os.path.basename(p)))
    return d


def expand(p):
    return os.path.abspath(os.path.expanduser(os.path.expandvars(p)))


def read_cron():
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return r.stdout


def write_cron(text):
    r = subprocess.run(["crontab", "-"], input=text, capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout)[:160]


def cron_find(lines, hint):
    """返回 (索引, 是否已被本工具关掉)。找到的行必须只有一个匹配，多个就拒绝改。"""
    hits = [(i, l) for i, l in enumerate(lines) if hint and hint in l]
    if len(hits) != 1:
        return None, None, "匹配到 %d 条（要正好 1 条才敢动）" % len(hits)
    i, line = hits[0]
    off = line.strip().startswith(CRON_OFF.strip())
    return i, off, ""


def cron_set_enabled(lines, hint, want_on):
    """纯函数：返回新行列表 + 说明。只加/去本工具自己那行前缀，不重写别人的行。"""
    out = list(lines)
    i, off, err = cron_find(out, hint)
    if err:
        return None, err
    line = out[i]
    if off == (not want_on):
        return None, "已经是%s状态，没改" % ("开" if want_on else "关")
    if want_on:
        out[i] = line.strip().replace(CRON_OFF.strip() + " ", "", 1)
    else:
        out[i] = CRON_OFF + line.strip().lstrip("#").strip()
    return out, ""


TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def cron_set_time(lines, hint, hhmm):
    """纯函数：只改分与时两位，day/month/dow 原样留着（周几不在页面上改）。"""
    if not TIME_RE.match(hhmm or ""):
        return None, "时间格式要 HH:MM"
    out = list(lines)
    i, off, err = cron_find(out, hint)
    if err:
        return None, err
    body = out[i].strip()
    prefix = ""
    if body.startswith(CRON_OFF.strip()):
        prefix, body = CRON_OFF, body[len(CRON_OFF.strip()):].strip()
    f = body.split(None, 5)
    if len(f) < 6:
        return None, "这条 cron 字段不足 6 段，不敢改"
    hh, mm = hhmm.split(":")
    f[0], f[1] = str(int(mm)), str(int(hh))
    out[i] = (prefix + " ".join(f)) if prefix else " ".join(f)
    return out, ""


def plist_read(path):
    with open(path, "rb") as f:
        return plistlib.load(f)


def plist_write(path, data):
    with open(path, "wb") as f:
        plistlib.dump(data, f)


def plist_set_times(path, hm_list):
    """纯函数：把 StartCalendarInterval 换成给定时刻（[(Hour,Minute),…]）。"""
    d = plist_read(path)
    d["StartCalendarInterval"] = [{"Hour": h, "Minute": m} for h, m in hm_list]
    plist_write(path, d)
    back = [x for x in ([d["StartCalendarInterval"]] if isinstance(d["StartCalendarInterval"], dict)
                        else d["StartCalendarInterval"])]
    got = sorted((int(x.get("Hour", -1)), int(x.get("Minute", -1))) for x in back)
    want = sorted((int(h), int(m)) for h, m in hm_list)
    return got == want, "plist 里现在是 %s" % (got,)


def json_patch_text(path, key, want):
    """定点改一个布尔或字符串字段，不重排整个 JSON（这些文件是别的进程在读的）。"""
    raw = io_read(path)
    if isinstance(want, bool):
        pat = re.compile(r'("%s"\s*:\s*)(true|false)' % re.escape(key))
        newv = "true" if want else "false"
    else:
        pat = re.compile(r'("%s"\s*:\s*)"([^"]*)"' % re.escape(key))
        newv = '"%s"' % want
    if not pat.search(raw):
        return False, "文件里没有 %r 这个字段" % key
    cur = pat.search(raw).group(2)
    out = pat.sub(lambda m: m.group(1) + newv, raw, count=1)
    try:
        json.loads(out)
    except Exception as e:
        return False, "改完不是合法 JSON，放弃写入：%s" % str(e)[:60]
    io_write(path, out)
    back = json_patch_read(path, key)
    ok = str(back) == str(want if not isinstance(want, bool) else (newv == "true"))
    return ok, "字段 %s：%s → %s（回读 %s）" % (key, cur, newv, back)


def json_patch_read(path, key):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return None
    return d.get(key)


def io_read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def io_write(p, s):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(s)
    os.replace(tmp, p)


def launchctl_loaded(label):
    r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    return any(len(x.split("\t")) >= 3 and x.split("\t")[2] == label for x in r.stdout.splitlines())


def launchd_set(label, plist_path, want_on):
    uid = os.getuid()
    now = launchctl_loaded(label)
    if now == want_on:
        return True, "已经是%s状态" % ("加载" if want_on else "卸载")
    if want_on:
        r = subprocess.run(["launchctl", "bootstrap", "gui/%d" % uid, plist_path],
                           capture_output=True, text=True)
    else:
        r = subprocess.run(["launchctl", "bootout", "gui/%d/%s" % (uid, label)],
                           capture_output=True, text=True)
    ok = r.returncode == 0 and launchctl_loaded(label) == want_on
    if not ok:
        return False, "回读不符：%s" % (r.stderr or r.stdout)[:140]
    return True, ("已加载" if want_on else "已卸载（plist 文件留着，随时可开回来）")


def apply_cron(lines, note_id):
    text = "\n".join(lines) + "\n"
    ok, err = write_cron(text)
    if not ok:
        return False, "crontab 写入失败：%s" % err
    back = read_cron().splitlines()
    if [l.strip() for l in back if l.strip()] != [l.strip() for l in lines if l.strip()]:
        return False, "写完回读不一致，请从备份恢复（backup 目录见 audit）"
    return True, "crontab 已回读一致"


def restore_cron(backup_dir):
    src = os.path.join(backup_dir, "crontab.txt")
    if os.path.exists(src):
        write_cron(io_read(src))
        return True
    return False


def snapshot_cron(backup_dir):
    with open(os.path.join(backup_dir, "crontab.txt"), "w", encoding="utf-8") as f:
        f.write(read_cron() + "\n")


def audit(rec):
    rec["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(HOME_DIR, "audit.log"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec
