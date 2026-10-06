# Demo Showcase Toolkit

Create a Demo Match showcase by describing the event or audience and choosing existing demos. The assistant creates an unlisted client page, copies the selected demos and hosted videos, preserves captions and order, and checks the result. Original library records stay unchanged.

**For marketers:** no coding is required after installation and account setup. You provide the page title and demo links; the assistant performs the copying and verification.

## Install and start

For **Claude Code**, follow the [Claude Code setup guide](docs/CLAUDE-CODE.md), or enter:

```text
/plugin marketplace add OTVentures/demo-showcase-toolkit
/plugin install demo-showcase-toolkit@otventures-demo-showcase
```

Start a new session and use `/mcp` to sign in if prompted. Invoke `/demo-showcase-toolkit:demo-showcase` or describe the showcase in plain language.

For **Codex desktop**, ask:

> Install the Demo Showcase Toolkit from https://github.com/OTVentures/demo-showcase-toolkit. Use my existing approved Demo Match connection if available; otherwise guide me through signing in with my own account.

Start a new session/task after installation. If the plugin does not appear, restart the host. In either assistant, ask:

> Use Demo Showcase to create a showcase called “Conference Demos”. Copy these demos: [paste the exact demo links]. Use the standard branding, include all videos and captions, preserve the originals, and give me the verified published link. If the title already exists, ask before reusing it.

For an event's “flagship” set, supply the approved list. The assistant will not guess which demos qualify. Creating another event or booth showcase uses the same prompt with a different title and selection.

See the [installation guide](docs/INSTALL.md) for account requirements, CLI installation, updates and troubleshooting.

## Requirements

- Claude Code or Codex desktop with plugin, MCP and local command support, plus an appropriate account/plan for that assistant. Claude Cowork and ordinary browser chat are not validated by this release.
- Your own approved Demo Match account with client creation and demo/media publishing permissions. Downloading this repository does not grant access.
- Python 3.9+ and curl for the local upload helper. No third-party Python packages are required. Live workflow validation used macOS; helper tests also run on Linux in CI. Native Windows and cloud-only chat execution are not validated.
- Network access to Demo Match and the upload destination returned by its authenticated connector, plus enough local disk space for the selected videos.

The toolkit code is free to reuse under the [MIT license](LICENSE). Demo Match access, demo content rights and AI-service costs are separate.

## What gets created

A page at `https://demos.otventures.vc/client/<showcase-address>` with Demo Match's existing branding, search, filters and player. Each selected demo receives a separate destination record and hosted video copies. Captions, narration order and supporting links are preserved. Interactive application links continue to open the existing applications.

**Private means unlisted, accessible to anyone with the link.** It does not mean password protected. Copies are snapshots; later changes to the source do not automatically update them.

## Tested scope and limits

Hosted-video copying, caption copying, readiness, publication, search, playlist navigation, source preservation and recovery have been exercised live. Local tests cover planning, verification, journaling and upload contracts. See [validation details](docs/VALIDATION.md).

- PDF factsheet transfers and external-provider players require per-showcase verification.
- Current API-created copies can require English, German and Canadian French captions even when the published source has fewer tracks. Missing requirements leave the new copies in draft.
- Publication is sequential and can partially succeed. The assistant reports exactly what was published and what remains incomplete.
- Physical booth devices and long playback sessions need event-specific checks.
- Custom domains, new layouts, password protection, automatic refresh and cloning interactive applications are outside this release.

## For maintainers

```sh
python3 scripts/check_release.py
python3 scripts/package_release.py
```

The first command validates the package, scans for common accidental private artifacts and runs the local tests without credentials or network calls. The second creates an allowlisted ZIP and SHA-256 checksum in `dist/`. CI runs the checks on macOS and Linux, including Claude manifest validation.

- [Plugin workflow](plugins/demo-showcase-toolkit/skills/demo-showcase/SKILL.md)
- [Copy and recovery contract](plugins/demo-showcase-toolkit/skills/demo-showcase/references/copy-workflow.md)
- [Contributing](CONTRIBUTING.md)
- [Security and data handling](SECURITY.md)
- [Release notes](CHANGELOG.md)

Only toolkit source and synthetic tests belong in this repository. Keep showcase run records, source readbacks, captions, downloaded videos and credentials outside it.
