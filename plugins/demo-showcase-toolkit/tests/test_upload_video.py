import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "skills/demo-showcase/scripts/upload_video.py"
spec = importlib.util.spec_from_file_location("upload_video", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class UploadVideoTests(unittest.TestCase):
    def video(self, root, contents=b"copy bytes"):
        path = root / "copy.mp4"
        path.write_bytes(contents)
        return path

    def contract(self, size, headers=None):
        return {"size_bytes": size, "upload": {"method": "PUT",
                "url": "https://storage.example/presigned?X-Amz-Signature=signed-value",
                "headers": headers or {"content-type": "video/mp4"}}}

    def test_exact_upload_size_mismatch_skips_curl(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.video(Path(name))
            with patch.object(tool.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "byte count"):
                    tool.transfer(path, self.contract(path.stat().st_size + 1))
            run.assert_not_called()

    def test_authorization_header_is_denied_before_upload(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.video(Path(name))
            with patch.object(tool.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "Authorization"):
                    tool.transfer(path, self.contract(path.stat().st_size, {"Authorization": "Bearer no"}))
            run.assert_not_called()

    def test_config_newline_injection_is_refused(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.video(Path(name))
            with patch.object(tool.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "invalid transfer header"):
                    tool.transfer(path, self.contract(path.stat().st_size, {"content-type": "video/mp4\nheader = injected"}))
            run.assert_not_called()

    def test_failed_curl_does_not_echo_presigned_url(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.video(Path(name))
            signed = "https://storage.example/presigned?X-Amz-Signature=signed-value"
            failure = SimpleNamespace(returncode=22, stdout="403", stderr="upload failed " + signed)
            with patch.object(tool.subprocess, "run", return_value=failure):
                with self.assertRaises(RuntimeError) as raised:
                    tool.transfer(path, self.contract(path.stat().st_size))
            self.assertNotIn(signed, str(raised.exception))
            self.assertNotIn("signed-value", str(raised.exception))

    def test_successful_mocked_put_reports_local_checksum(self):
        with tempfile.TemporaryDirectory() as name:
            contents = b"independent destination bytes"
            path = self.video(Path(name), contents)
            success = SimpleNamespace(returncode=0, stdout="200", stderr="")
            with patch.object(tool.subprocess, "run", return_value=success) as run:
                result = tool.transfer(path, self.contract(len(contents)))
            self.assertEqual(result["sha256"], hashlib.sha256(contents).hexdigest())
            self.assertEqual(result["size_bytes"], len(contents))
            self.assertEqual(result["http_status"], 200)
            self.assertTrue(result["uploaded"])
            self.assertIn("X-Amz-Signature=signed-value", run.call_args.kwargs["input"])

    def test_redirect_is_not_treated_as_a_successful_upload(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.video(Path(name))
            redirect = SimpleNamespace(returncode=0, stdout="307", stderr="")
            with patch.object(tool.subprocess, "run", return_value=redirect):
                with self.assertRaisesRegex(RuntimeError, "HTTP 307"):
                    tool.transfer(path, self.contract(path.stat().st_size))
            for raw_status in ("", "200200", "000200", " 200", "200\n"):
                with self.subTest(status=raw_status):
                    malformed = SimpleNamespace(returncode=0, stdout=raw_status, stderr="")
                    with patch.object(tool.subprocess, "run", return_value=malformed):
                        with self.assertRaisesRegex(RuntimeError, "invalid HTTP status"):
                            tool.transfer(path, self.contract(path.stat().st_size))


if __name__ == "__main__":
    unittest.main()
