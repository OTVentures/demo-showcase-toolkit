# Demo Match client-showcase copy workflow

Verified against connected MCP schemas and current Demo Match docs on 2026-10-06. Recheck live tool schemas and preflight on every run. This is a composition of supported operations; there is no connected `copy_demo` or `clone_demo` operation.

## Tools and destination boundaries

Read: `get_publishing_requirements`, `get_file_upload_guidance`, `list_clients`, `list_demos`, `get_demo`, `get_video`, `list_subtitles`, `get_subtitle`, `get_page_palettes`, `get_demo_readiness`.

Write only new/reconciled destination records: `add_client`, `create_demo`, `add_video`, `prepare_video_upload`, `complete_video_upload`, `replace_factsheet_file`, `upload_subtitle`, `set_default_subtitle`, `reorder_videos`, `update_client_theme`, `publish_demo`. Client themes are optional. Source IDs never appear as mutation targets. Do not use `update_demo` to move sources, set publication status or imitate a clone.

Ordinary publishers can select managed clients but cannot necessarily create them. `Manage public links` permission alone is for collection pages, not this workflow. Verify available tools and private-media access for the signed-in user; a setup administrator may need to grant suitable access. Do not bundle an administrator token in this plugin.

## Before writing

1. Resolve the explicit source selection to published `get_demo` records. Save readbacks and an explicit brief. The helper's JSON inputs are arrays of these records, not raw MCP text-content envelopes.
2. Record the original stable metadata, client/visibility/status, video IDs, narration order, track metadata and factsheet identity. Private/internal notes must not be copied into the destination or distributable bundle.
3. Validate offered industries, languages, country/region and product families against current requirements. If the source contains retired values the create operation will refuse, report it; don't silently remap or remove content.
4. Check client name/slug collisions. If resuming, identify the exact existing client and provenance; never merge clients to resolve a conflict.
5. Generate a plan with `showcase_plan.py plan`. Its local caption prediction is advisory; the target's live `get_demo_readiness` decides whether publication is possible. The helper makes no network calls and does not execute its payloads.

Example operator commands, with paths resolved in the current task workspace:

```sh
python3 scripts/showcase_plan.py plan --brief brief.json --sources sources-before.json --output plan.json
python3 scripts/showcase_plan.py verify --stage draft --plan plan.json --before sources-before.json --after sources-after.json --targets copies.json --output draft-check.json
python3 scripts/showcase_plan.py verify --plan plan.json --before sources-before.json --after sources-after.json --targets published-copies.json --output final-check.json
```

Run these relative to the skill directory, or use its absolute script path. `--stage published` is the verification default. These examples are for the assistant, not a requirement for the marketer to use a terminal. A passed metadata report is only one component of the completion evidence below.

## Create and copy

### Client page

Call `add_client({name: title, slug: requestedSlug})`. Read the returned ID, slug and `client_page`. Re-adding a name may return an existing client, so do collision checks first. Journal the actual identity. If an approved palette was requested, query `get_page_palettes`, select its real ID/version and call `update_client_theme` on this destination client. Default styling is sufficient otherwise.

The client name supplies the page title. The current client-theme contract offers palettes, not a full page editor. The `subtle` and `branded` legacy theme-style values now render the same D dark-banner treatment; don't promise two different layouts. Custom introductions, navigation and presentation order would need separate confirmed capabilities.

### Demo record

Use the helper's `create_demo` payload, reconciled against the actual destination client identity:

```json
{
  "title": "Exact source demo title",
  "slug": "event-slug-demo-123",
  "status": "draft",
  "private": true,
  "audience": "client",
  "client": "Exact destination client name",
  "admin_note": "showcase-toolkit/1:event-slug:123"
}
```

Include copied description, tags, product information, website languages, country/region, walkthrough metadata, interactive demo URL and related links. The helper preserves an allowlist. A target's new public ID, slug, client and status are intentional differences. Do not copy source admin notes, sharing grants, votes, audit history, ingestion bindings or publication-managed identifiers.

`create_demo` currently does not accept `posting_policy_version`. Browser-created sources with `post-demo/1` do not pass that policy to an API-created copy. Do not inject unsupported fields or impersonate the browser's session API.

### Hosted videos

For each source video in its delivered sequence:

1. Freshly read the target's sequence revision before mutation when needed. Call `add_video({demo_id: destinationId, title, description, language, duration_seconds, expected_revision})`. Omit legacy `role`; derive the technical primary through complete ordering and default language. The typed schema/server sequence model takes precedence over legacy preflight prose that still lists role.
2. Journal the new video `public_id` against the source video `public_id` immediately.
3. For hosted source media, use the tested route: download the public source `/pv/...` alias locally, call `prepare_video_upload`, pass the exact response to `scripts/upload_video.py` on stdin, then call `complete_video_upload` for the new destination video. This creates independent destination bytes. Do not assign a source `/pv` or `/v` URL as `external_url`.
4. Do not use `replace_video_file` for same-site copy: both public `/pv` and signed same-site URLs returned `bad_url` in the live pilot. Do not log or save the prepare-upload response or any signed URL.
5. Read the new video back. Verify hosted state, new identity and comparable size/duration; compare SHA-256 and byte count when the authorized local download makes that practical.

`upload_video.py` accepts one or more local video paths and one JSON contract line per file on stdin. Wait for its ready message before feeding a terminal session; it disables echo and canonical input to accept long signed URLs without truncation. Pass only the exact `upload` object and `size_bytes` from the MCP response. Do not put the contract in shell arguments or a disk file. It requires Python 3 and curl on the desktop host.

If PUT fails, read the destination and ask `complete_video_upload` to reconcile the prepared transfer. If it reports `upload_not_found`, prepare a fresh upload for the SAME destination video and retry the local bytes. The live validation recovered this exact failure without a second video record. Never treat a failed upload as a reason to call `add_video` again.

For genuinely external video providers, copy the original `external_url` into a new video record. The provider remains a dependency; don't promise independent hosted bytes. Verify supported playback and preserve its narration language.

### Captions

For every source track, call `get_subtitle({public_id: SOURCE_ID, lang})` and pass the returned complete `vtt`, `label` and `default` to `upload_subtitle({public_id: NEW_ID, lang, vtt, label, default})`. Read back target tracks and compare their VTT text and default selection. Caption language and narration language are different fields.

Do not produce missing translations as if they were source copies. Currently legacy/unversioned copies may require `en`, `de`, and `fr-CA`. Keep missing-caption copies as drafts and identify the needed tracks. If the user separately asks for translations, scope and validate that content work first. Never exploit an admin override or edit status directly to get around readiness.

### Factsheet and other links

If a source has a hosted PDF factsheet, import it with `replace_factsheet_file({demo_id: NEW_ID, source_url: SOURCE_FACTSHEET_URL})`. Resolve the actual returned public factsheet URL; do not infer `/pf` IDs. Verify a separate destination factsheet identity and PDF response. Do not attach the source's raw hosted object URL directly to the copy.

This PDF route is supported by the tool schema but has not passed live copy validation. Same-site URL retrieval may fail as it did for videos. No presigned PDF-upload tool is currently exposed. If import fails, leave the selected batch in draft and report the factsheet transfer blocker. Do not omit the PDF, borrow hidden OAuth credentials, or invent an upload endpoint.

For an external PDF, import into the destination when supported. If retrieval is unavailable, report the dependency rather than silently dropping the factsheet or changing copy semantics. Preserve external interactive-demo URLs and supporting links as links; copying a showcase does not duplicate those external websites.

### Order, readiness and publication

Map the source sequence to all new video public IDs. Fetch the current destination revision, then call `reorder_videos({demo_id: NEW_ID, video_public_ids: ALL_NEW_IDS_IN_ORDER, default_narration_language: SOURCE_DEFAULT, expected_revision: CURRENT_REVISION})`. On `video_sequence_changed`, reload and reconcile rather than overwriting concurrent changes.

Complete all selected drafts first. Compare source snapshots to fresh source readbacks. Resolve any concurrent source changes. Call `get_demo_readiness` for every destination; keep the batch in draft if any is not ready. Refresh preflight just before publishing. Publish each ready destination using `publish_demo`, recording each result immediately. A lost response is reconciled by reading the demo's status. Sequential publication can be partial; report exact results.

## Resume rules

Initialize `showcase-run.json` from the plan with `showcase_run.py init --plan plan.json --output showcase-run.json`. It refuses to reset an existing run when its brief/source selection differs. `begin` saves one pending operation before every MCP write, with explicit source and destination fields; `complete` appends a redacted completion event and clears it. Do not store signed URLs or private notes. The helper refuses pending-operation overwrite and refuses a target that matches any selected source demo/video ID.

- `add_client`: reconcile name, slug, ID and intended ownership; don't merge.
- `create_demo`: search the complete relevant catalogue for exact deterministic slug AND provenance marker; read back to verify client identity. Do not issue another create just because the previous response was lost. A slug collision with different provenance is a conflict.
- `add_video`: use `reconcile-video` with a current `get_demo` response. It compares the saved pre-call video IDs plus intended title, language and description. Resume only if exactly one new candidate matches; zero or multiple candidates remain `needs_review`. Stop rather than creating duplicates.
- File replacement: inspect target media before retrying. Preserve already verified progress. Replacement writes only destination storage, but a lost result does not prove failure.
- Captions/order/theme: read current state and apply only the intended difference to known destination identities.
- Publication: `get_demo` status is the reconciliation source. Never blindly repeat unrelated mutations.
- Partial or abandoned work: leave recorded draft/published state visible in the run report. Cleanup is a separately scoped action on verified destinations only; no automatic destructive rollback.

## Completion evidence

Run `showcase_plan.py verify` with complete source before/after arrays and destination readbacks. It detects metadata/identity failures, not full media equivalence. Separately compare caption text, verify transferred media bytes or checksums when practical, and test public playback/PDF links. Record precisely which checks were performed.

Open the actual client page, confirm exact membership and heading, and test desktop plus a tablet-sized view with available browser tools. Existing client pages expose every published demo assigned to that client, so an unexpected record is not merely cosmetic. Report inability to do browser QA explicitly.

For media link checks use a bounded ranged GET or player request. The reference `/pv` endpoint returned 404 for HEAD but a valid `206 video/mp4` response for `GET Range: bytes=0-0`; HEAD alone is not evidence of a broken video. A successful ranged GET still does not prove complete playback or server-side reimport.

Sources: [Demo Match API](https://github.com/OTVentures/demo-match/blob/main/API.md), [README](https://github.com/OTVentures/demo-match/blob/main/README.md), connected tool schemas. Do not follow old local deployment instructions to change this application.
