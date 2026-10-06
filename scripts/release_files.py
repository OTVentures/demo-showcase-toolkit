"""Explicit public-release file inventory; never package a working directory wholesale."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "demo-showcase-toolkit"
ROOT_FILES = (
    "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md",
    ".gitignore", ".agents/plugins/marketplace.json", ".github/workflows/validate.yml",
    "docs/INSTALL.md", "docs/VALIDATION.md", "scripts/release_files.py",
    "scripts/check_release.py", "scripts/package_release.py",
)
PLUGIN_FILES = (
    ".codex-plugin/plugin.json", ".mcp.json", "LICENSE", "README.md",
    "examples/showcase-brief.json", "skills/demo-showcase/SKILL.md",
    "skills/demo-showcase/agents/openai.yaml",
    "skills/demo-showcase/references/copy-workflow.md",
    "skills/demo-showcase/references/run-record.json",
    "skills/demo-showcase/scripts/showcase_plan.py",
    "skills/demo-showcase/scripts/showcase_run.py",
    "skills/demo-showcase/scripts/upload_video.py",
    "tests/test_showcase_plan.py", "tests/test_showcase_run.py", "tests/test_upload_video.py",
)


def release_files():
    files = [ROOT / name for name in ROOT_FILES] + [PLUGIN / name for name in PLUGIN_FILES]
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError("missing file or forbidden symlink: %s" % path.relative_to(ROOT))
        if ROOT not in path.resolve().parents:
            raise ValueError("release path escapes repository")
    return sorted(files)
