"""Codex 复验反例；仅临时库+模型桩。参数为 video2text 仓库绝对路径。"""
import importlib.util
import json
import sys
import tempfile
import threading
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("e", repo / "scripts/e2e_plan_tasks.py")
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
failures = []


def check(name, ok, detail):
    print(("PASS " if ok else "FAIL ") + name + " " + json.dumps(detail, ensure_ascii=False))
    if not ok:
        failures.append(name)


with tempfile.TemporaryDirectory(prefix="codex-plan-r2-") as tmp:
    db = e.make_db(tmp)
    app, client = e.boot(db)
    client.post("/api/plan/task", json=e.payload(slot="pending-drift", vids=(12,)))
    response = client.post("/api/plan/task/generate",
                           json=e.payload(slot="pending-drift", vids=(112,)))
    data = response.get_json()
    if data.get("mode") == "started":
        done = e.wait_done(client, data["task_id"])
        task_ids = done["task"]["video_ids"]
        source_ids = json.loads(done["summary"]["source_video_ids"])
        check("生成与记录的证据一致", task_ids == source_ids,
              {"task": task_ids, "summary": source_ids})
    else:
        check("拒绝过期素材请求", response.status_code == 409, data)

    # 使用另一题，独立建立done，避免前一项修复改变本项前提。
    r = client.post("/api/plan/task/generate",
                    json=e.payload(slot="clear-done", vids=(12,))).get_json()
    e.wait_done(client, r["task_id"])
    r = client.post("/api/plan/task",
                    json=e.payload(slot="clear-done", vids=())).get_json()
    check("已开工版本清空采用得到空新版", r["task"]["video_ids"] == [],
          {"ids": r["task"]["video_ids"], "version": r["task"]["version"]})

    client.post("/api/plan/task", json=e.payload(slot="race-fast", vids=(12,)))
    original = app.plan_tasks.claim_running
    reached = threading.Event()
    release = threading.Event()
    output = {}

    def hooked(db_path, task_id):
        if threading.current_thread().name == "request-A":
            reached.set()
            release.wait(10)
        return original(db_path, task_id)

    def first_request():
        with app.app.test_client() as other:
            result = other.post("/api/plan/task/generate", json=e.payload(slot="race-fast"))
            output["a"] = result.get_json()

    app.plan_tasks.claim_running = hooked
    first = threading.Thread(target=first_request, name="request-A")
    before = len(e.CALLS)
    try:
        first.start()
        if not reached.wait(10):
            raise RuntimeError("未到达占锁边界；如接口重构，请更新此测试挂点")
        second = client.post("/api/plan/task/generate",
                             json=e.payload(slot="race-fast")).get_json()
        e.drain(client, second)
        release.set()
        first.join(timeout=15)
        if first.is_alive():
            raise RuntimeError("请求A未收尾")
        e.drain(client, output["a"])
        check("另一个请求完成后过期请求不能重复生成", len(e.CALLS) - before == 1,
              {"A": output["a"].get("mode"), "B": second.get("mode"),
               "model_calls": len(e.CALLS) - before})
    finally:
        release.set()
        first.join(timeout=15)
        app.plan_tasks.claim_running = original

sys.exit(1 if failures else 0)
