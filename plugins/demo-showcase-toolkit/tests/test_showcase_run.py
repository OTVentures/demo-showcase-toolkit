import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "skills/demo-showcase/scripts/showcase_run.py"
spec = importlib.util.spec_from_file_location("showcase_run", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def plan(source=7, video="old-video"):
    return {"brief": {"title": "Acme", "slug": "acme"}, "drafts": [{"source_id": source,
            "source_public_id": "old-%s" % source, "media": {"videos": [{"source_public_id": video}]}}]}


class ShowcaseRunTests(unittest.TestCase):
    def call(self, *args):
        try:
            tool.main(list(args))
        except SystemExit as exc:
            if exc.code == 2:
                return False
            raise
        return True

    def write(self, root, name, data):
        path = root / name
        path.write_text(json.dumps(data))
        return path

    def initialized(self, root):
        plan_path = self.write(root, "plan.json", plan())
        run = root / "run.json"
        self.assertTrue(self.call("init", "--plan", str(plan_path), "--output", str(run)))
        return run

    def begin_video(self, root, run, payload=None):
        payload_path = self.write(root, "payload.json", payload or {"demo_id": "new-demo", "title": "Intro", "language": "en", "description": "Welcome", "source_url": "https://x/a?X-Amz-Signature=leak"})
        state = self.write(root, "pre.json", {"videos": [{"public_id": "already"}]})
        return self.call("begin", "--run", str(run), "--operation", "add_video", "--target-id", "new-demo", "--source-id", "old-video", "--payload-file", str(payload_path), "--pre-state", str(state))

    def test_lost_video_response_reconciles_only_unique_match(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); self.begin_video(root, run)
            current = self.write(root, "current.json", {"id": "new-demo", "videos": [{"public_id": "already"}, {"public_id": "ybt5sidsquja", "title": "Intro", "language": "en", "description": "Welcome"}]})
            self.assertTrue(self.call("reconcile-video", "--run", str(run), "--current", str(current)))
            data = json.loads(run.read_text())
            self.assertIsNone(data["pending_operation"])
            self.assertEqual(data["events"][-1]["kind"], "reconciled")

    def test_lost_video_response_ambiguous_needs_review(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); self.begin_video(root, run)
            current = self.write(root, "current.json", {"videos": [{"public_id": "a", "title": "Intro", "language": "en", "description": "Welcome"}, {"public_id": "b", "title": "Intro", "language": "en", "description": "Welcome"}]})
            self.assertTrue(self.call("reconcile-video", "--run", str(run), "--current", str(current)))
            pending = json.loads(run.read_text())["pending_operation"]
            self.assertEqual(pending["recovery_status"], "needs_review")

    def test_repeat_init_mismatch_refuses_reset_and_atomic_write_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); original = run.read_text()
            other = self.write(root, "other-plan.json", plan(source=8))
            self.assertFalse(self.call("init", "--plan", str(other), "--output", str(run)))
            self.assertEqual(run.read_text(), original)
            with self.assertRaises(TypeError):
                tool.atomic_write(run, {"bad": {1, 2}})
            self.assertEqual(run.read_text(), original)

    def test_source_mutation_and_pending_overwrite_are_denied(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root)
            payload = self.write(root, "payload.json", {})
            self.assertFalse(self.call("begin", "--run", str(run), "--operation", "update_demo", "--target-id", "7", "--payload-file", str(payload)))
            self.assertTrue(self.begin_video(root, run))
            self.assertFalse(self.call("begin", "--run", str(run), "--operation", "create_demo", "--target-id", "another", "--payload-file", str(payload)))

    def test_payload_target_cannot_disagree_with_journal_target_or_point_at_source(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root)
            state = self.write(root, "pre.json", {"videos": []})
            mismatch = self.write(root, "mismatch.json", {"demo_id": "7", "title": "Intro"})
            self.assertFalse(self.call("begin", "--run", str(run), "--operation", "add_video", "--target-id", "new-demo", "--payload-file", str(mismatch), "--pre-state", str(state)))
            upload = self.write(root, "upload.json", {"public_id": "old-video", "vtt": "WEBVTT"})
            self.assertFalse(self.call("begin", "--run", str(run), "--operation", "upload_subtitle", "--target-id", "new-video", "--payload-file", str(upload)))

    def test_failed_completion_keeps_pending_for_review(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); self.begin_video(root, run)
            result = self.write(root, "failed.json", {"ok": False, "error": "remote failure"})
            self.assertTrue(self.call("complete", "--run", str(run), "--result-file", str(result)))
            data = json.loads(run.read_text())
            self.assertEqual(data["pending_operation"]["recovery_status"], "needs_review")
            self.assertEqual(data["events"][-1]["kind"], "completion_needs_review")

    def test_wrong_destination_completion_keeps_pending_but_new_video_id_is_allowed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); self.begin_video(root, run)
            wrong = self.write(root, "wrong-result.json", {"demo_id": "someone-else", "public_id": "new-video"})
            self.assertTrue(self.call("complete", "--run", str(run), "--result-file", str(wrong)))
            data = json.loads(run.read_text())
            self.assertEqual(data["pending_operation"]["recovery_status"], "needs_review")

        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); self.begin_video(root, run)
            created = self.write(root, "created-video.json", {"public_id": "new-video"})
            self.assertTrue(self.call("complete", "--run", str(run), "--result-file", str(created)))
            self.assertIsNone(json.loads(run.read_text())["pending_operation"])

    def test_recovery_rejects_wrong_destination_or_missing_or_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); self.begin_video(root, run)
            wrong = self.write(root, "wrong.json", {"id": "someone-else", "videos": []})
            self.assertFalse(self.call("reconcile-video", "--run", str(run), "--current", str(wrong)))
            missing = self.write(root, "missing.json", {"id": "new-demo", "videos": [{"title": "Intro", "language": "en", "description": "Welcome"}]})
            self.assertTrue(self.call("reconcile-video", "--run", str(run), "--current", str(missing)))
            self.assertEqual(json.loads(run.read_text())["pending_operation"]["recovery_status"], "needs_review")

        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); self.begin_video(root, run)
            duplicate = self.write(root, "duplicate.json", {"id": "new-demo", "videos": [{"public_id": "dup", "title": "Intro", "language": "en", "description": "Welcome"}, {"public_id": "dup", "title": "Intro", "language": "en", "description": "Welcome"}]})
            self.assertTrue(self.call("reconcile-video", "--run", str(run), "--current", str(duplicate)))
            self.assertEqual(json.loads(run.read_text())["pending_operation"]["recovery_status"], "needs_review")

    def test_secrets_are_redacted_from_pending_and_events(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); run = self.initialized(root); self.begin_video(root, run)
            contents = run.read_text()
            self.assertNotIn("leak", contents)
            self.assertIn("<redacted>", contents)
            result = self.write(root, "result.json", {"authorization": "Bearer secret", "upload_id": "capability", "url": "https://x/r?sig=private-signature-value", "upload_url": "https://x/token/path-secret"})
            self.assertTrue(self.call("complete", "--run", str(run), "--result-file", str(result)))
            contents = run.read_text()
            self.assertNotIn("secret", contents)
            self.assertNotIn("private-signature-value", contents)
            self.assertNotIn("capability", contents)
            self.assertNotIn("path-secret", contents)


if __name__ == "__main__":
    unittest.main()
