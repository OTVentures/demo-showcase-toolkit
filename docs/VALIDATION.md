# Validation and known limitations

## Claude Code support in 1.1.0

Claude Code 2.1.280 validated the plugin and marketplace with `--strict` and no warnings. Installation into an isolated test workspace succeeded; the installed component inventory showed one `demo-showcase` skill and one `demo-match` MCP server. The host's existing Demo Match MCP connection reported connected. The shared local suite still passes 25 tests; CI also validates the Claude manifests on macOS and Linux.

A live model-driven Claude test could not start because the saved Claude login returned an expired OAuth session that could not refresh. This is separate from Demo Match authentication. No new showcase was created by that failed test, and this release does not claim a completed end-to-end Claude copy run. Sign in to Claude Code with `/login` and run the bounded first-showcase test in the Claude Code guide to establish that evidence. The existing live copy evidence below was obtained through Codex.

Claude Cowork and ordinary web chat are not tested execution hosts for this toolkit.

Initial live validation on 2026-10-06 used an authorized account on Codex desktop/macOS. Private client URLs, real record IDs, local paths and operator data are intentionally omitted from this public report.

## Evidence

- Two existing published demos copied into an unlisted client showcase, with five distinct destination videos and fifteen caption tracks.
- All five video byte counts and SHA-256 hashes matched their sources. All caption VTT texts, labels and default flags matched.
- Source assignments, visibility and stable content fields remained unchanged. Draft and published metadata verification passed, as did live readiness without overrides.
- Correct two-demo membership, search, four-item playlist order and navigation were checked. Actual playback advanced with readyState 4 and paused false on both copies.
- Desktop and tablet layouts at widths 1440 and 1024 had no horizontal document overflow. Preserved interactive links opened their expected applications.
- A successful add_video result was deliberately withheld from the local mapping. Saved pre-state and remote readback recovered exactly one new video without another create. This simulated a lost local result; it was not an induced network outage.
- A real upload transport failure was reconciled as upload_not_found. A fresh upload contract for the same destination video succeeded without a duplicate record.
- A user subsequently reported successfully building a showcase they were happy with using the installed toolkit. This is usability feedback, not independent verification of every feature.

## Practical boundaries

Same-site replace_video_file URL imports failed in the initial test. The working route downloads authorized source media locally, uses prepare_video_upload and a presigned PUT, then completes the transfer through the same authenticated MCP session.

PDF copying and external-provider playback were not live validated. No PDF was present in the initial test demos. The workflow reports failures and leaves incomplete copies in draft rather than omitting assets.

Current generic MCP-created drafts can require English, German and Canadian French captions even when an existing published source has fewer. The toolkit copies available tracks and reports missing requirements without inventing translations or overriding readiness.

The in-app browser crashed when automation clicked a native pause control after successful playback. A fresh tab restored browsing. Physical event devices and long playback sessions still require event-specific checks.

Local unit tests use synthetic data and mocked uploads. They do not prove account permissions, remote API availability or live playback. CI validates helper portability on its declared runner matrix; the full live workflow was tested on macOS.
