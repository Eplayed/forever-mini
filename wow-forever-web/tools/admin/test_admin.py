"""Focused tests for staging and allowlist; run: python3 -m unittest discover -s tools/admin."""
import json
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

    def test_refresh_refuses_dirty_data_before_workflow(self):
        with patch.object(jobs.subprocess, "run", return_value=CompletedProcess([], 0, " M app/data/world.json\n", "")) as run:
            with self.assertRaises(RuntimeError):
                jobs.refresh("world", lambda _: None)
            self.assertEqual(run.call_count, 1)

    def test_start_returns_the_file_list_for_confirmation(self):
        # 脏不再只是"启动失败"，要当场把清单回给页面让人确认，且不占单工作线程
        with patch.object(jobs, "dirty_data", return_value=["wow-forever-web/app/data/bis.json"]):
            code, obj = jobs.start("refresh", "bis")
        self.assertEqual((code, obj["code"], obj["files"]), (409, "dirty-worktree", ["wow-forever-web/app/data/bis.json"]))
        self.assertIsNone(jobs.active)

    def test_confirmed_force_runs_without_the_worktree_block(self):
        calls = []
        def fake(cmd, *a, **kw):
            calls.append(cmd)
            return CompletedProcess([], 0, "", "")
        with patch.object(jobs, "dirty_data", return_value=["wow-forever-web/app/data/bis.json"]), \
             patch.object(jobs.subprocess, "run", side_effect=fake):
            result = jobs.refresh("bis", lambda _: None, force=True)
        self.assertTrue(result["skippedWorktreeCheck"])
        self.assertIn("跳过了工作树检查", result["message"])
        self.assertEqual(calls[0], ["bash", "tools/refresh.sh", "bis"])


if __name__ == "__main__":
    unittest.main()
