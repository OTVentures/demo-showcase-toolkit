import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "skills/demo-showcase/scripts/showcase_plan.py"
spec = importlib.util.spec_from_file_location("showcase_plan", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def source(ident=7):
    return {"id": ident, "public_id": "old-%s" % ident, "title": "Northwind", "description": "Demo",
            "tags": ["retail"], "demo_url": "https://northwind.example/demo", "links": [{"url": "https://northwind.example"}],
            "admin_note": "do not leak", "client": "Old client", "status": "published", "private": False,
            "videos": [{"public_id": "vid-90", "title": "Narration", "description": "Voiceover", "language": "en",
                        "duration_seconds": 22, "hosted": True, "pub": "/pv/vid-90",
                        "storage_key": "old/video", "tracks": [{"language": "en"}, {"language": "de"}, {"language": "fr-CA"}]}],
            "factsheet_url": "/pf/old-7/factsheet.pdf", "factsheet_id": "sheet-1", "factsheet": "PDF"}


class ShowcasePlanTests(unittest.TestCase):
    def invoke(self, command, **data):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = [command]
            for name, value in data.items():
                path = root / (name + ".json")
                path.write_text(json.dumps(value))
                args.extend(["--" + name.replace("_", "-"), str(path)])
            output = root / "result.json"
            args.extend(["--output", str(output)])
            try:
                tool.main(args)
            except SystemExit as exc:
                if command == "plan" or exc.code == 2:
                    raise
            return json.loads(output.read_text())

    def plan(self, item=None):
        return self.invoke("plan", brief={"title": "Acme review", "slug": "Acme Showcase", "source_ids": [7], "selection_confirmed": True}, sources=[item or source()])

    def test_plan_creates_bounded_draft_and_import_manifest(self):
        result = self.plan()
        draft = result["drafts"][0]
        payload = draft["create_demo"]
        self.assertEqual(result["plan_status"], "ready_for_drafts")
        self.assertEqual(payload["status"], "draft")
        self.assertEqual(payload["admin_note"], "showcase-toolkit/1:acme-showcase:7")
        self.assertEqual(payload["client"], "Acme review")
        self.assertNotEqual(payload["client"], source()["client"])
        self.assertNotIn("do not leak", payload.values())
        self.assertEqual(draft["media"]["videos"][0]["source_public_id"], "vid-90")
        self.assertEqual(draft["media"]["videos"][0]["source_url"], "https://demos.otventures.vc/pv/vid-90")
        self.assertEqual(draft["media"]["factsheets"][0]["source_url"], "https://demos.otventures.vc/pf/old-7/factsheet.pdf")

    def test_external_provider_is_a_dependency_not_a_hosted_import(self):
        item = source()
        item["videos"][0].update({"hosted": False, "pub": "/pv/stale-hosted-alias", "external_url": "https://video.example/watch/9"})
        result = self.plan(item)
        video = result["drafts"][0]["media"]["videos"][0]
        self.assertFalse(video["hosted"])
        self.assertEqual(video["source_url"], "https://video.example/watch/9")
        target = copy.deepcopy(item)
        target.update({"id": 1007, "public_id": "copy-7", "private": True, "audience": "client", "client": "Acme review",
                       "status": "published", "admin_note": result["drafts"][0]["create_demo"]["admin_note"]})
        target["videos"][0]["public_id"] = "external-copy-9"
        target["factsheet_id"] = "sheet-copy"
        target["factsheet_url"] = "/pf/copy-7/factsheet.pdf"
        verified = self.invoke("verify", plan=result, before=[item], after=[copy.deepcopy(item)], targets=[target])
        self.assertTrue(verified["verified"])

    def test_plan_requires_explicit_unique_existing_selection(self):
        with self.assertRaises(SystemExit):
            self.invoke("plan", brief={"title": "A", "slug": "a", "source_ids": [7, 7], "selection_confirmed": True}, sources=[source()])
        with self.assertRaises(SystemExit):
            self.invoke("plan", brief={"title": "A", "slug": "a", "source_ids": [8], "selection_confirmed": False}, sources=[source()])

    def test_missing_captions_blocks_publish_without_inventing_them(self):
        item = source()
        item["videos"][0]["tracks"] = [{"language": "en"}]
        result = self.plan(item)
        self.assertEqual(result["plan_status"], "needs_input")
        self.assertIn("de", result["drafts"][0]["publish_blockers"][0])
        self.assertEqual(result["drafts"][0]["media"]["videos"][0]["tracks"], [{"language": "en"}])

    def test_plan_projects_caption_tracks_and_rejects_sensitive_url_fragments(self):
        item = source()
        item["videos"][0]["tracks"][0].update({
            "url": "https://captions.example/en.vtt?X-Amz-Signature=secret",
            "provider_metadata": {"private": "value"}, "label": "English", "default": True,
        })
        result = self.plan(item)
        self.assertEqual(result["drafts"][0]["media"]["videos"][0]["tracks"][0], {"language": "en"})

        for suffix in ("#access_token=secret", "?sig=private-signature", "#sig=private-signature"):
            item = source()
            item["demo_url"] = "https://northwind.example/demo" + suffix
            with self.subTest(suffix=suffix), self.assertRaises(SystemExit):
                self.plan(item)

    def test_verification_detects_source_reassignment_caption_loss_order_and_source_url(self):
        plan = self.plan()
        before = [source()]
        after = [copy.deepcopy(before[0])]
        target = copy.deepcopy(before[0])
        target.update({"id": 1007, "public_id": "new-7", "private": True, "audience": "client", "client": "Acme review",
                       "status": "draft", "admin_note": plan["drafts"][0]["create_demo"]["admin_note"]})
        target["videos"][0].update({"public_id": "vid-91", "pub": "/pv/vid-91"})
        # Deliberately leave source URL/storage key, lose captions, and alter narration.
        target["videos"][0]["tracks"] = [{"language": "en"}]
        target["videos"][0]["title"] = "Narration reordered"
        result = self.invoke("verify", plan=plan, before=before, after=after, targets=[target])
        self.assertFalse(result["verified"])
        reasons = " ".join(x["reason"] for x in result["failures"])
        self.assertIn("caption metadata", reasons)
        self.assertIn("title", reasons)
        self.assertIn("references source", reasons)

    def test_verification_requires_unchanged_original_and_marker_resume_identity(self):
        plan = self.plan()
        before = [source()]
        after = [source()]
        after[0]["description"] = "edited source"
        result = self.invoke("verify", plan=plan, before=before, after=after, targets=[])
        self.assertFalse(result["verified"])
        self.assertIn("original changed", result["failures"][0]["reason"])
        # A duplicate marker must not be mistaken for a resumable copy.
        after = [source()]
        target = source(1007)
        target.update({"public_id": "copy", "private": True, "audience": "client", "client": "Acme review",
                       "status": "draft", "admin_note": plan["drafts"][0]["create_demo"]["admin_note"]})
        target["videos"][0].update({"public_id": "vid-91", "pub": "/pv/vid-91", "storage_key": "new/video"})
        result = self.invoke("verify", plan=plan, before=before, after=after, targets=[target, copy.deepcopy(target)])
        self.assertIn("expected one target", result["failures"][0]["reason"])

    def test_original_assignment_visibility_and_publication_changes_fail(self):
        plan = self.plan()
        for field, changed in (("client", "Event"), ("private", True), ("status", "draft")):
            after = source()
            after[field] = changed
            with self.subTest(field=field):
                result = self.invoke("verify", plan=plan, before=[source()], after=[after], targets=[])
                self.assertFalse(result["verified"])
                self.assertIn("original changed", result["failures"][0]["reason"])

    def test_real_two_video_order_is_preserved(self):
        original = source()
        second = copy.deepcopy(original["videos"][0])
        second.update({"public_id": "second-source", "pub": "/pv/second-source", "title": "Second chapter"})
        original["videos"].append(second)
        plan = self.plan(original)
        target = copy.deepcopy(original)
        target.update({"id": 1007, "public_id": "copy-7", "private": True, "audience": "client",
                       "client": "Acme review", "status": "published", "admin_note": plan["drafts"][0]["create_demo"]["admin_note"],
                       "factsheet_id": "copy-sheet", "factsheet_url": "/pf/copy-sheet"})
        for index, video in enumerate(target["videos"]):
            video.update({"public_id": "copy-video-%s" % index, "pub": "/pv/copy-video-%s" % index, "storage_key": "copy/%s" % index})
        result = self.invoke("verify", plan=plan, before=[original], after=[copy.deepcopy(original)], targets=[target])
        self.assertTrue(result["verified"])
        target["videos"].reverse()
        result = self.invoke("verify", plan=plan, before=[original], after=[copy.deepcopy(original)], targets=[target])
        self.assertFalse(result["verified"])
        self.assertTrue(any("title" in x["reason"] for x in result["failures"]))

    def test_published_copy_of_actual_api_shape_verifies(self):
        plan = self.plan()
        before = [source()]
        target = copy.deepcopy(before[0])
        target.update({"id": 1007, "public_id": "copy-7", "private": True, "audience": "client", "client": "Acme review",
                       "status": "published", "admin_note": plan["drafts"][0]["create_demo"]["admin_note"]})
        target["videos"][0].update({"public_id": "vid-copy-90", "pub": "/pv/vid-copy-90", "storage_key": "copy/video"})
        target["factsheet_id"] = "sheet-copy"
        target["factsheet_url"] = "/pub/copy-7/factsheet.pdf"
        result = self.invoke("verify", plan=plan, before=before, after=copy.deepcopy(before), targets=[target])
        self.assertTrue(result["verified"])
        self.assertFalse(result["media_bytes_verified"])

        target["videos"][0]["storage_key"] = before[0]["videos"][0]["storage_key"]
        result = self.invoke("verify", plan=plan, before=before, after=copy.deepcopy(before), targets=[target])
        self.assertFalse(result["verified"])
        self.assertTrue(any("reuses source storage_key" in x["reason"] for x in result["failures"]))


if __name__ == "__main__":
    unittest.main()
