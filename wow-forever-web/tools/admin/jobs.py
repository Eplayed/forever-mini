"""Single-worker, local-only review jobs for the data console."""
import json
import os
import subprocess
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


def _curl_json(url):
    # Fixed host and fixed paths only. curl uses the system trust store on this Mac.
    p = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                        "--max-time", "30", url], capture_output=True, text=True, timeout=35)
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
    return {"message": "待审快照；未改成品数据", "path": os.path.relpath(path, ROOT),
            "fetchedAt": (doc.get("meta") or {}).get("fetchedAt"),
            "build": (doc.get("meta") or {}).get("foreverBuild"), "local": len(old), "remote": len(new),
            "added": len(added), "removed": len(removed), "changed": len(changed),
            "addedSample": added[:30], "removedSample": removed[:30], "changedSample": changed[:30]}


def dirty_data():
    """工作树里 app/data 与 app/img 的未提交改动（含未跟踪文件）。

    这台机器上常常有另一个会话正在写同一批数据，所以"脏"是常态而不是异常：
    判据要能单独拿出来给页面用（先列清单、由人确认），不能只在刷新里当一堵墙。
    """
    p = subprocess.run(["git", "status", "--porcelain", "--", "app/data", "app/img"],
                       cwd=ROOT, capture_output=True, text=True, timeout=15)
    if p.returncode:
        raise RuntimeError("读不到工作树状态（git status 非 0），不猜它干净")
    return [line[3:].strip() for line in p.stdout.splitlines() if line.strip()]


def refresh(topic, progress, force=False):
    workflows = {t[0]: t[7] for t in TOPICS if t[7]}
    if topic not in workflows:
        raise RuntimeError("该板块没有已核准的一键刷新链；请先做数据采编和命令设计")
    # A refresh chain rewrites derived data too. Never run over someone else's edits
    # unless the human saw the file list and said "照样跑"（force）.
    dirty = dirty_data()
    if dirty and not force:
        raise RuntimeError("app/data 或 app/img 有未提交改动；先收口工作树再刷新。\n" +
                           "\n".join(dirty)[:1200])
    if dirty:
        progress("已按确认跳过工作树检查，这些文件可能被覆盖：" + "、".join(dirty)[:400])
    progress("运行 tools/refresh.sh " + workflows[topic] + "；含构建门禁，可能需要数分钟")
    p = subprocess.run(["bash", "tools/refresh.sh", workflows[topic]], cwd=ROOT,
                       capture_output=True, text=True, timeout=900)
    output = ((p.stdout or "") + (p.stderr or ""))[-64000:]
    changed = subprocess.run(["git", "status", "--short", "--", "app/data", "app/img"],
                             cwd=ROOT, capture_output=True, text=True, timeout=15).stdout[:6000]
    if p.returncode:
        raise RuntimeError("刷新或门禁失败，已写文件可能仍在工作树，需检查后处理。\n" + output)
    note = "刷新链通过；未提交、未部署，请审阅变更"
    if dirty:
        note += "（本次按你的确认跳过了工作树检查）"
    return {"message": note, "code": 0, "skippedWorktreeCheck": bool(dirty),
            "changedFiles": changed, "logTail": output}


def start(action, topic=None, force=False):
    global active
    if action != "scan-items" and action != "refresh":
        return 400, {"error": "未知动作"}
    if action == "scan-items" and topic != "items":
        return 400, {"error": "物品公开 API 只支持 items"}
    if action == "refresh" and topic not in {t[0] for t in TOPICS if t[7]}:
        return 400, {"error": "该板块没有白名单刷新命令"}
    if action == "refresh" and not force:
        # 先在工作线程外问一次：脏就当场把清单回给页面，由人确认后再启动，不占单工作线程
        try:
            files = dirty_data()
        except RuntimeError as exc:
            return 500, {"error": str(exc)}
        if files:
            return 409, {"code": "dirty-worktree",
                         "error": "app/data 或 app/img 有未提交改动，刷新链会覆盖或混写这些文件",
                         "files": files}
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
            result = scan_items(progress) if action == "scan-items" else refresh(topic, progress, force)
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
