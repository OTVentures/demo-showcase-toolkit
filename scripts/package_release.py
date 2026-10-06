#!/usr/bin/env python3
"""Build a reproducible, allowlisted source/plugin bundle and SHA-256 checksum."""
import hashlib
import json
from pathlib import Path
import zipfile
from release_files import ROOT, PLUGIN, release_files


def main():
    version = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())["version"]
    name = "demo-showcase-toolkit-" + version
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    archive = output / (name + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        for path in release_files():
            info = zipfile.ZipInfo(str(Path(name) / path.relative_to(ROOT)), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            handle.writestr(info, path.read_bytes())
    with zipfile.ZipFile(archive) as handle:
        assert handle.testzip() is None
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(digest + "  " + archive.name + "\n", encoding="utf-8")
    print(archive.relative_to(ROOT))
    print(digest)


if __name__ == "__main__":
    main()
