"""Single-worker, local-only review jobs for the data console."""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from catalog import DATA, ROOT, TOPICS

REVIEW = os.path.join(os.path.dirname(__file__), "review")
API = "https://wowforever.wclbox.com/api/open/v1"
ITEM_FIELDS = ("id", "name", "status", "quality", "itemLevel", "requiredLevel", "slot", "type")
lock = threading.Lock()
jobs = {}
active = None

# node/npm 不能裸写：面板服务要是从精简 PATH 的环境起的（2026-11-03 实测，隐藏窗口自启那版
# 就是这样），CreateProcess 找不到 npm 直接 rc=127。先 which，再兜底这台机的安装位。
def _node_tool(name):
    hit = shutil.which(name)
    if hit:
        return hit
    for d in (os.environ.get("ProgramFiles") or r"C:\Program Files", r"D:\Program Files"):
        for sub in ((name + ".cmd",) if name == "npm" else (name + ".exe",)):
            p = os.path.join(d, "nodejs", sub)
            if os.path.isfile(p):
                return p
    return name


NPM = _node_tool("npm")
NODE = _node_tool("node")

# 双管道动作链的白名单单命令（02 同步屏的四步）。发布/上传/回滚是闸门步：
# 前端弹层只是慎重 UI，真正的闸在工具层——oss-release 的写操作必须带
# WOW_ALLOW_CROSS_CREDS=1（它自己的"每条写命令都要人工点头"卡口），deploy-gh-pages
# 不加 --push 就不动远端。这里把那条环境变量显式写在白名单里，页面上没有输口令就发不出去的东西。
OSS_WRITE = dict(os.environ, WOW_ALLOW_CROSS_CREDS="1", PYTHONIOENCODING="utf-8")
PIPELINE = {
    "web-build":    {"label": "网页 ① 构建",       "cmd": [NPM, "--prefix", "app", "run", "build"], "timeout": 1200},
    "web-package":  {"label": "网页 ② 打包",       "cmd": [sys.executable, "tools/release-package.py"], "timeout": 1800},
    "web-verify":   {"label": "网页 ③ 验收",       "cmd": [sys.executable, "tools/pkg-verify.py"], "timeout": 600},
    "web-publish":  {"label": "网页 ④ 发布（闸门）", "cmd": [sys.executable, "tools/deploy-gh-pages.py", "--push"], "timeout": 1800, "gate": True},
    "mini-export":  {"label": "小程序 ① 导出",     "cmd": [NODE, "tools/export-mini.js"], "timeout": 600},
    "mini-build":   {"label": "小程序 ② 成批",     "cmd": [NODE, "tools/oss-release.js", "build", "--env", "beta", "--check-identity"], "timeout": 900},
    "mini-upload":  {"label": "小程序 ③ 上传换指针（闸门）", "cmd": [NODE, "tools/oss-release.js", "upload", "--env", "beta"], "timeout": 1800, "env": OSS_WRITE, "gate": True},
    "mini-rollback": {"label": "小程序 ④ 回滚（闸门）", "cmd": None, "timeout": 1200, "env": OSS_WRITE, "gate": True},
}
DAILY_ARGS = ("", "--quick", "--no-gate")   # daily 的 topic 位只接受这三个变体
LEDGER = os.path.join(os.path.dirname(__file__), "reconcile", "ledger.jsonl")
OUT_MAX = 64 * 1024                                    # 命令输出截断（与 server.py 同一口径）


def _ref(path):
    """给页面看的相对路径。跨盘时 os.path.relpath 会抛 ValueError（这台仓库在 D:、
       临时目录在 C:），2026-11-02 实测把 test_scan_items 直接崩掉；退化成绝对路径总比整条任务崩好。"""
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return os.path.abspath(path).replace("\\", "/")


def _curl_json(url):
    # Fixed host and fixed paths only. curl uses the system trust store.
    # encoding 必须显式给 utf-8：这台 Windows 的默认码是 GBK，
    # 上游 JSON 里的中文会让 text=True 的解码线程抛 UnicodeDecodeError（2026-11-02 实测）。
    p = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                        "--max-time", "30", url], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=35)
    if p.returncode:
        raise RuntimeError("上游请求失败：" + p.stderr[-300:])
    return json.loads(p.stdout)


def scan_items(progress):
    info = _curl_json(API)
    total = info.get("items")
    if not isinstance(total, int) or not 0 < total < 100000:
        raise RuntimeError("公开 API 未返回可信物品总数")
    rows = []
    for offset in range(0, total, 100):
        page = _curl_json(API + "/items?limit=100&offset=" + str(offset) + "&sort=id&order=asc")
        batch = page.get("items")
        if page.get("total") != total or not isinstance(batch, list) or len(batch) != min(100, total - offset):
            raise RuntimeError("分页总数变化或页不完整，拒绝落盘；offset=" + str(offset))
        rows.extend({**{k: row.get(k) for k in ITEM_FIELDS},
                     "iconFile": os.path.basename(urlsplit(row.get("icon") or "").path)} for row in batch)
        progress("已读 %d / %d" % (len(rows), total))
        time.sleep(0.27)  # <= 4 requests/s, below the API's 5/s limit
    ids = [row["id"] for row in rows]
    if len(set(ids)) != total or ids != sorted(ids):
        raise RuntimeError("ID 重复或分页乱序，拒绝落盘")
    os.makedirs(REVIEW, exist_ok=True)
    doc = {"meta": {"source": API, "fetchedAt": datetime.now(timezone.utc).isoformat(),
                    "foreverBuild": info.get("foreverBuild"), "buildDate": info.get("buildDate"),
                    "purpose": "待审事实快照；未合入 app/data/items.json；不含说明文案"},
           "items": rows}
    path = os.path.join(REVIEW, "items-api-latest.json")
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(temp, path)
    return review_items()


def review_items():
    path = os.path.join(REVIEW, "items-api-latest.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    with open(os.path.join(DATA, "items.json"), encoding="utf-8") as f:
        local = json.load(f).get("items", [])
    old = {int(row["id"]): row for row in local}
    rows = doc.get("items") or []
    new = {int(row["id"]): row for row in rows}
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = []
    for key in sorted(set(old) & set(new)):
        a, b = old[key], new[key]
        if any(a.get(x) != b.get(y) for x, y in (("name", "name"), ("status", "status"),
                                                   ("quality", "quality"), ("ilvl", "itemLevel"))) or \
           (a.get("rlvl") or 0) != (b.get("requiredLevel") or 0):
            changed.append(key)
    return {"message": "待审快照；未改成品数据", "path": _ref(path),
            "fetchedAt": (doc.get("meta") or {}).get("fetchedAt"),
            "build": (doc.get("meta") or {}).get("foreverBuild"), "local": len(old), "remote": len(new),
            "added": len(added), "removed": len(removed), "changed": len(changed),
            "addedSample": added[:30], "removedSample": removed[:30], "changedSample": changed[:30]}


def dirty_data():
    """工作树里 app/data 与 app/img 的未提交改动（含未跟踪文件）。

    这台机器上常常有另一个会话正在写同一批数据，所以"脏"是常态而不是异常。
    2026-10-28 站主定的口径：**常态不当拦路石**——脏不再拒绝启动刷新链，
    改成跑前先把它提交成一次本地收口（现场保留、可回退、不 push），见 `commit_data`。
    """
    p = subprocess.run(["git", "status", "--porcelain", "--", "app/data", "app/img"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
    if p.returncode:
        raise RuntimeError("读不到工作树状态（git status 非 0），不猜它干净")
    return [line[3:].strip() for line in p.stdout.splitlines() if line.strip()]


def commit_data(message):
    """把 app/data 与 app/img 的未提交改动提交成一次本地收口，返回 (短哈希, 文件数)。

    三条边界：① **只碰这两个目录**，用 pathspec 提交，别人 staged 的无关文件不会被卷走；
    ② 只提交不推送——push 永远是人的动作；③ 提交号回给页面，出问题一句 `git revert` 能退掉。
    """
    files = dirty_data()
    if not files:
        return None
    add = subprocess.run(["git", "add", "-A", "--", "app/data", "app/img"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if add.returncode:
        raise RuntimeError("自动收口 git add 失败，刷新链没启动：" + (add.stderr or add.stdout)[-400:])
    p = subprocess.run(["git", "commit", "-q", "-m", message, "--", "app/data", "app/img"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if p.returncode:
        raise RuntimeError("自动收口 git commit 失败，刷新链没启动（不想在来历不明的工作树上跑）：" +
                           (p.stderr or p.stdout)[-400:])
    short = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15).stdout.strip()
    return (short, len(files))


def refresh(topic, progress):
    workflows = {t[0]: t[7] for t in TOPICS if t[7]}
    if topic not in workflows:
        raise RuntimeError("该板块没有已核准的一键刷新链；请先做数据采编和命令设计")
    pre_commit = None
    if dirty_data():
        # 先收口再跑：这条链会重写派生数据，跑前把现场存成一次提交，被覆盖的东西随时能取回
        pre_commit = commit_data("chore(admin): 刷新链 %s 启动前自动收口（未推送）" % topic)
        progress("跑前先收口：%d 个未提交文件已提交成本地 %s" % (pre_commit[1], pre_commit[0]))
    progress("运行 tools/refresh.sh " + workflows[topic] + "；含构建门禁，可能需要数分钟")
    # 超时从 900s 提到 2700s：这条链末尾含 site-check 全量，这台 Windows 实测单跑就要约 13 分钟
    # （Mac 上 900s 够用，2026-11-02 迁到这台后差点把跑完一半的链当成卡死杀掉）。
    p = subprocess.run(["bash", "tools/refresh.sh", workflows[topic]], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=2700)
    output = ((p.stdout or "") + (p.stderr or ""))[-64000:]
    if p.returncode:
        raise RuntimeError("刷新或门禁失败，已写文件仍在工作树里（没有自动提交），需检查后处理。\n" + output)
    post_commit = commit_data("chore(admin): 刷新链 %s 的产物（门禁已过，未推送、未发布）" % topic)
    changed = subprocess.run(["git", "show", "--stat", "--oneline", "-1", "--", "app/data", "app/img"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15).stdout[:6000]
    note = "刷新链通过；产物已提交到本地"
    if post_commit:
        note += "（%s，%d 个文件）" % (post_commit[0], post_commit[1])
    note += "，没有 push、没有发布"
    return {"message": note, "code": 0,
            "preCommit": list(pre_commit) if pre_commit else None,
            "postCommit": list(post_commit) if post_commit else None,
            "changedFiles": changed, "logTail": output}


def reconcile(progress):
    """只读对账：比本地 app/data 与线上 Pages 的那份、本地批次与线上指针。
       这一步不改任何数据、不构建、不发布——它就是把两个清单读回来比一比。
       要 ~2 分钟（这台机到 Pages 单请求常拖），所以走任务队列让页面轮询，不塞进 GET 里。"""
    out = os.path.join(os.path.dirname(__file__), "reconcile", "latest.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    progress("正在读线上那一份（Pages 与 OSS 指针，约两分钟）")
    p = subprocess.run([sys.executable, "tools/reconcile.py", "--env", "beta", "--json", out, "--quiet"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=400)
    if p.returncode:
        raise RuntimeError("对账没跑完（它只读不写，红也不影响数据）：" + ((p.stdout or "") + (p.stderr or ""))[-1200:])
    with open(out, encoding="utf-8") as f:
        rep = json.load(f)
    w, m = rep.get("web") or {}, rep.get("mini") or {}
    return {"message": "对账完成 %s｜网页线 一致 %s · 不同 %s · 读不到 %s｜小程序线 %s" % (
        rep.get("generatedAt"), (w.get("summary") or {}).get("一致"), (w.get("summary") or {}).get("不同"),
        (w.get("summary") or {}).get("读不到"),
        "本地与线上是同一批" if m.get("sameBatch") else "本地批次 %s ≠ 线上指针 %s" % (
            (m.get("local") or {}).get("buildId") or "—", (m.get("live") or {}).get("buildId") or "—")),
        "snapshot": out, "web": w.get("summary"), "mini": {"sameBatch": m.get("sameBatch"),
                                                           "summary": m.get("summary"),
                                                           "error": m.get("error")}}


def allowed(action, topic=None):
    """动作白名单的唯一一份判据：None 表示允许，否则是不允许的原因。
       单测原来直接调 jobs.start("refresh","items") 期望它被拒——我给 items 接上场景之后，
       那条断言由 400 变 202，**测试当场把一条真刷新链放了出去并留下一笔自动收口提交**（2026-11-02，ee25881）。
       判据抽出来之后，测它不用再启动任何东西。"""
    if action in PIPELINE:
        if action == "mini-rollback":
            # 回滚目标来自页面输入，是唯一一个客户端能递进命令的参数——按工具自己的
            # 校验口径先卡一道：12 位十六进制批次号，别的一律不放。
            if not (isinstance(topic, str) and re.fullmatch(r"[a-f0-9]{12}", topic)):
                return "回滚目标要是 12 位十六进制批次号"
        return None
    if action == "daily":
        return None if (topic or "") in DAILY_ARGS else "daily 只接受 --quick / --no-gate"
    if action not in ("scan-items", "refresh", "reconcile"):
        return "未知动作"
    if action == "scan-items" and topic != "items":
        return "物品公开 API 只支持 items"
    if action == "refresh" and topic not in {t[0] for t in TOPICS if t[7]}:
        return "该板块没有白名单刷新命令"
    return None


def ledger_append(lane, build_id, what):
    """append-only 发布账：谁、哪一批、带了什么。只在闸门步真正跑完且成功后记一条，
       失败的尝试不记账（账是"玩家读到了什么"的历史，不是操作日志）。"""
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    row = {"at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
           "lane": lane, "buildId": build_id, "what": what}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _stream_run(entry, jid, progress, extra_args=()):
    """长任务要有心跳：Popen 逐行读输出，尾行滚进 job 的 logTail（页面每 5 秒轮一次），
       门禁九分钟不再干等。只读 stdout/stderr，不解释、不停步——链红不红由退出码说。"""
    cmd = list(entry["cmd"]) + list(extra_args)
    t0 = time.time()
    # Windows 专项（2026-11-03）：server.py 的父终端被关掉后它成孤儿进程仍活着，
    # 这时再 spawn bash.exe（WSL 启动器）会拿不到可用控制台，直接 rc=0xC0000142
    # （DLL 初始化失败），链一步没跑、steps.tsv 纹丝不动，00 屏看着就是"点了没反应"。
    # CREATE_NO_WINDOW 给子进程一个自己的隐藏控制台，不依赖父进程的控制台死活；
    # stdin 接 DEVNULL 免得子进程去抢父进程已失效的输入。Linux 下无此常量，跳过。
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                             errors="replace", env=entry.get("env") or None,
                             creationflags=flags)
    except OSError as exc:
        return 127, str(exc)
    tail = []
    try:
        for line in p.stdout:
            line = line.rstrip()
            if not line:
                continue
            tail.append(line)
            if len(tail) > 60:
                tail = tail[-40:]
            with lock:
                jobs[jid]["logTail"] = "\n".join(tail)
            progress(line[-160:])   # 进度条上永远显示最新一行
        p.wait(timeout=max(30, entry["timeout"] - int(time.time() - t0)))
    except subprocess.TimeoutExpired:
        p.kill()
        return 124, "超时（%ds）" % entry["timeout"]
    out = "\n".join(tail)
    if len(out.encode("utf-8", "replace")) > OUT_MAX:
        out = out[:OUT_MAX // 4] + "\n…（输出过长，已截断）\n" + out[-OUT_MAX // 4:]
    return p.returncode, out


def start(action, topic=None):
    global active
    if action == "reconcile":
        topic = None
    error = allowed(action, topic)
    if error:
        return 400, {"error": error}
    with lock:
        if active is not None:
            return 409, {"error": "已有任务运行", "jobId": active}
        jid = uuid.uuid4().hex[:12]
        jobs[jid] = {"id": jid, "action": action, "topic": topic, "state": "running",
                     "progress": "排队中", "startedAt": datetime.now(timezone.utc).isoformat()}
        active = jid

    def run():
        global active
        def progress(message):
            with lock:
                jobs[jid]["progress"] = message
        try:
            if action == "scan-items":
                result = scan_items(progress)
            elif action == "reconcile":
                result = reconcile(progress)
            elif action == "daily":
                # 日更链是一条长链（25-40 分钟）：走流式读，输出尾行滚进 logTail，
                # 步子红没红由面板轮询 steps.tsv 看（daily.sh 现在写到固定位置）。
                args = [topic] if topic else []
                code, out = _stream_run({"cmd": ["bash", "tools/daily.sh"], "timeout": 3000},
                                        jid, progress, extra_args=args)
                if code:
                    raise RuntimeError("日更链没跑完（rc=%d）。红的那步在 00 水源台的链上看，别当已更新。\n%s" % (code, out[-1500:]))
                result = {"message": "日更链全绿。报告：docs/DATA-每日体检-%s.md" % datetime.now().strftime("%F"), "logTail": out}
            elif action in PIPELINE:
                entry = PIPELINE[action]
                code, out = _stream_run(entry, jid, progress,
                                        extra_args=(["--to", topic] if action == "mini-rollback" else ()))
                if code:
                    raise RuntimeError("%s 没跑成（rc=%d）。\n%s" % (entry["label"], code, out[-1500:]))
                if entry.get("gate"):
                    # 闸门步成功才记账；批次号从输出里捞（upload/rollback/deploy 都会打出它）
                    m = re.search(r"\b([a-f0-9]{12})\b", out)
                    ledger_append("mini" if action.startswith("mini") else "web",
                                  m.group(1) if m else "—",
                                  entry["label"] + "完成（上一批转入回滚位）" if action != "mini-rollback"
                                  else "回滚到 " + (topic or ""))
                result = {"message": entry["label"] + "通过，未自动做下一步", "logTail": out}
            else:
                result = refresh(topic, progress)
            with lock:
                jobs[jid].update(state="done", result=result, progress="完成")
        except Exception as exc:
            with lock:
                jobs[jid].update(state="error", error=str(exc), progress="失败")
        finally:
            with lock:
                jobs[jid]["finishedAt"] = datetime.now(timezone.utc).isoformat()
                active = None

    threading.Thread(target=run, daemon=True).start()
    return 202, {"jobId": jid}


def get(jid):
    with lock:
        return dict(jobs[jid]) if jid in jobs else None
