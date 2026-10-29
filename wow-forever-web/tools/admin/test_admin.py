"""Focused tests for staging and allowlist; run: python3 -m unittest discover -s tools/admin."""
import json
import io
import os
import tempfile
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess

import catalog
import jobs


class AdminTests(unittest.TestCase):
    def test_records_rejects_unlisted_topic_and_large_query(self):
        with self.assertRaises(ValueError):
            catalog.records("../../secret")
        with self.assertRaises(ValueError):
            catalog.records("items", "x" * 81)

    def test_scan_items_stages_exact_diff_without_touching_product(self):
        with tempfile.TemporaryDirectory() as directory:
            data = os.path.join(directory, "data")
            review = os.path.join(directory, "review")
            os.mkdir(data)
            original = {"items": [{"id": 1, "name": "甲", "status": "same", "quality": 1, "ilvl": 1, "rlvl": 1},
                                  {"id": 2, "name": "乙", "status": "same", "quality": 1, "ilvl": 1, "rlvl": 1}]}
            path = os.path.join(data, "items.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(original, f)
            remote = [{"id": 1, "name": "甲改", "status": "changed", "quality": 1, "itemLevel": 1, "requiredLevel": 1},
                      {"id": 3, "name": "丙", "status": "new", "quality": 2, "itemLevel": 2, "requiredLevel": 1}]
            def fake(url):
                return {"items": 2, "foreverBuild": "test", "buildDate": "today"} if url == jobs.API else {"total": 2, "items": remote}
            with patch.object(jobs, "DATA", data), patch.object(jobs, "REVIEW", review), \
                 patch.object(jobs, "_curl_json", side_effect=fake), patch.object(jobs.time, "sleep"):
                result = jobs.scan_items(lambda _: None)
            self.assertEqual((result["added"], result["removed"], result["changed"]), (1, 1, 1))
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f), original)
            with open(os.path.join(review, "items-api-latest.json"), encoding="utf-8") as f:
                staged = json.load(f)
            self.assertEqual(len(staged["items"]), 2)
            self.assertNotIn("description", staged["items"][0])

    def test_incomplete_page_never_replaces_review(self):
        with tempfile.TemporaryDirectory() as directory:
            review = os.path.join(directory, "review")
            os.mkdir(review)
            path = os.path.join(review, "items-api-latest.json")
            with open(path, "w") as f:
                f.write("old review")
            def fake(url):
                return {"items": 2} if url == jobs.API else {"total": 2, "items": [{"id": 1}]}
            with patch.object(jobs, "REVIEW", review), patch.object(jobs, "_curl_json", side_effect=fake):
                with self.assertRaises(RuntimeError):
                    jobs.scan_items(lambda _: None)
            with open(path) as f:
                self.assertEqual(f.read(), "old review")

    def test_action_allowlist(self):
        self.assertEqual(jobs.start("shell", "anything")[0], 400)
        self.assertEqual(jobs.start("refresh", "items")[0], 400)

    def test_refresh_refuses_topics_without_a_chain(self):
        with self.assertRaises(RuntimeError):
            jobs.refresh("items", lambda _: None)

    def test_commit_data_only_touches_data_and_img(self):
        """自动收口必须只提 app/data 与 app/img——别人 staged 的无关文件不能被卷走。"""
        import subprocess
        d = tempfile.mkdtemp()
        repo = lambda *a: subprocess.run(["git"] + list(a), cwd=d, capture_output=True, text=True)
        subprocess.run(["git", "init", "-q", d], capture_output=True, text=True)
        repo("config", "user.email", "t@t"); repo("config", "user.name", "t")
        for rel in ("app/data/x.json", "app/img/y.png", "docs/z.md"):
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with io.open(p, "w", encoding="utf-8") as f:
                f.write("base")
        repo("add", "-A"); repo("commit", "-q", "-m", "base")
        for rel in ("app/data/x.json", "app/img/y.png", "docs/z.md"):
            with io.open(os.path.join(d, rel), "w", encoding="utf-8") as f:
                f.write("dirty")
        with patch.object(jobs, "ROOT", d):
            got = jobs.commit_data("chore(admin): 测试收口")
        self.assertIsNotNone(got)
        self.assertEqual(got[1], 2, "只应提 data 与 img 那两个文件")
        left = subprocess.run(["git", "status", "--porcelain"], cwd=d, capture_output=True, text=True).stdout
        self.assertIn("docs/z.md", left, "docs 的改动不该被这次提交带走")
        self.assertNotIn("app/data", left)
        files = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=d,
                               capture_output=True, text=True).stdout.split()
        self.assertEqual(sorted(os.path.basename(x) for x in files), ["x.json", "y.png"])
        with patch.object(jobs, "ROOT", d):
            self.assertIsNone(jobs.commit_data("再来一次"))   # 干净就不该造空提交

    def test_refresh_autocommits_before_and_after_the_chain(self):
        """站主 2026-10-28 定的口径：工作树脏不再是拦路石，跑前收口现场、跑完提交产物、都不 push。"""
        state = {"dirty": ["wow-forever-web/app/data/x.json"], "commits": [], "cmds": []}

        def fake_run(cmd, *a, **kw):
            state["cmds"].append(cmd)
            if cmd[:2] == ["bash", "tools/refresh.sh"]:
                state["dirty"] = ["wow-forever-web/app/data/talents/druid.json"]
            return CompletedProcess([], 0, "", "")

        def fake_commit(message):
            state["commits"].append(message)
            n = len(state["dirty"])
            state["dirty"] = []
            return ("abc1234", n)

        with patch.object(jobs, "dirty_data", side_effect=lambda: list(state["dirty"])), \
             patch.object(jobs, "commit_data", side_effect=fake_commit), \
             patch.object(jobs.subprocess, "run", side_effect=fake_run):
            result = jobs.refresh("talents", lambda _: None)
        self.assertEqual(state["cmds"][0], ["bash", "tools/refresh.sh", "talents"])
        self.assertEqual(len(state["commits"]), 2)
        self.assertIn("启动前自动收口", state["commits"][0])
        self.assertIn("的产物（门禁已过，未推送、未发布）", state["commits"][1])
        self.assertEqual(result["preCommit"], ["abc1234", 1])
        self.assertEqual(result["postCommit"], ["abc1234", 1])
        self.assertIn("没有 push", result["message"])

    def test_a_failed_chain_leaves_the_worktree_for_a_human(self):
        """门禁没过就绝不自动提交产物——现场要留在工作树里给人看。"""
        state = {"dirty": [], "commits": []}

        def fake_run(cmd, *a, **kw):
            return CompletedProcess([], 1, "", "gate said no")

        with patch.object(jobs, "dirty_data", side_effect=lambda: list(state["dirty"])), \
             patch.object(jobs, "commit_data", side_effect=lambda m: state["commits"].append(m)), \
             patch.object(jobs.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(RuntimeError):
                jobs.refresh("talents", lambda _: None)
        self.assertEqual(state["commits"], [])


if __name__ == "__main__":
    unittest.main()
