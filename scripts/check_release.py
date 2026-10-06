#!/usr/bin/env python3
"""Offline package checks and unit tests. Not a complete credential scanner."""
import json
import re
import subprocess
import sys
from release_files import ROOT, PLUGIN, release_files


def check():
    files = release_files()
    manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    connector = json.loads((PLUGIN / ".mcp.json").read_text())
    claude_manifest = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
    claude_marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    assert claude_manifest["name"] == manifest["name"]
    assert claude_manifest["version"] == manifest["version"]
    assert claude_manifest["license"] == "MIT"
    assert claude_marketplace["name"] == marketplace["name"]
    assert claude_marketplace["owner"]["name"] == "OTVentures"
    assert len(claude_marketplace["plugins"]) == 1
    claude_entry = claude_marketplace["plugins"][0]
    assert claude_entry["name"] == manifest["name"]
    assert claude_entry["source"] == "./plugins/demo-showcase-toolkit"
    assert manifest["name"] == PLUGIN.name
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]), "release needs stable version"
    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert marketplace["name"] == "otventures-demo-showcase"
    assert len(marketplace["plugins"]) == 1
    entry = marketplace["plugins"][0]
    assert entry["name"] == manifest["name"]
    assert entry["source"] == {"source": "local", "path": "./plugins/demo-showcase-toolkit"}
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert connector == {"mcpServers": {"demo-match": {"type": "http", "url": "https://demos.otventures.vc/mcp"}}}
    assert (ROOT / "LICENSE").read_bytes() == (PLUGIN / "LICENSE").read_bytes()
    skill = (PLUGIN / "skills/demo-showcase/SKILL.md").read_text()
    assert skill.startswith("---\nname: demo-showcase\n") and "\ndescription: " in skill
    brief = json.loads((PLUGIN / "examples/showcase-brief.json").read_text())
    assert brief["source_ids"] == [] and brief["selection_confirmed"] is False
    forbidden = (
        re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
        re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"https://[^\s]+[?&](?:X-Amz-Signature|sig)=[A-Za-z0-9]{20,}", re.I),
        re.compile(r"https://demos\.otventures\.vc/client/[a-z0-9]"),
    )
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert not any(pattern.search(content) for pattern in forbidden), "potential private artifact: %s" % path.relative_to(ROOT)
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if "://" not in target and not target.startswith("#"):
                    assert (path.parent / target.split("#", 1)[0]).exists(), "broken local link: %s in %s" % (target, path)
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(PLUGIN / "tests"), "-b"], check=True, cwd=PLUGIN)
    print("Release checks passed: %d allowlisted files; manifest, connector, examples, links and local tests." % len(files))


if __name__ == "__main__":
    check()
