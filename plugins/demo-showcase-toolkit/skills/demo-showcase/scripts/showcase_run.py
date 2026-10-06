#!/usr/bin/env python3
"""Persist and recover local Demo Match copy operations without making API calls.

Use ``init`` once for a generated plan, ``begin`` immediately before one MCP
write, and ``complete`` after its readback.  ``reconcile-video`` only compares
saved pre-state with a supplied get_demo response; it never performs a write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


class ValidationError(ValueError):
    pass


SECRET_KEY = re.compile(r"(?:token|secret|password|authorization|credential|signature|signed|api[_-]?key|cookie|upload[_-]?id)", re.I)
SIGNED_QUERY = re.compile(r"(?:token|sig(?:nature)?|credential|awsaccesskeyid|x-amz-|expires|key)", re.I)
SIGNED_PATH = re.compile(r"/(?:token|tokens|sig|signature|signatures|signed)(?:/|$)", re.I)
TARGET_FIELD = {
    "add_video": "demo_id", "replace_video_file": "public_id",
    "upload_subtitle": "public_id", "set_default_subtitle": "public_id",
    "complete_video_upload": "public_id", "prepare_video_upload": "public_id", "update_demo": "id",
    "publish_demo": "id", "reorder_videos": "demo_id",
    "replace_factsheet_file": "demo_id", "update_client_theme": "id",
}
RESULT_TARGET_FIELD = {
    "replace_video_file": "public_id", "upload_subtitle": "public_id",
    "set_default_subtitle": "public_id", "complete_video_upload": "public_id",
    "prepare_video_upload": "public_id", "update_demo": "id",
    "publish_demo": "id", "reorder_videos": "demo_id",
    "replace_factsheet_file": "demo_id", "update_client_theme": "id",
}


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("cannot read JSON %s: %s" % (path, exc))


def redact(value, key=""):
    """Remove secrets before anything reaches the durable journal."""
    if SECRET_KEY.search(str(key)):
        return "<redacted>"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, str) and ("url" in str(key).lower() or value.startswith(("http://", "https://"))):
        parsed = urlsplit(value)
        if SIGNED_PATH.search(parsed.path):
            return "<redacted-url>"
        if parsed.query and SIGNED_QUERY.search(parsed.query):
            return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "<redacted>", ""))
    return value


def atomic_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, indent=2, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=".%s." % path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            directory = os.open(str(path.parent), os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except (AttributeError, OSError):
            pass
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def selected(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get("drafts"), list):
        raise ValidationError("plan must contain drafts")
    demo_ids, video_ids = set(), set()
    for draft in plan["drafts"]:
        if not isinstance(draft, dict) or draft.get("source_id") is None:
            raise ValidationError("every draft needs source_id")
        demo_ids.add(str(draft["source_id"]))
        if draft.get("source_public_id") is not None:
            demo_ids.add(str(draft["source_public_id"]))
        for video in (draft.get("media", {}).get("videos", []) if isinstance(draft.get("media"), dict) else []):
            if isinstance(video, dict) and video.get("source_public_id") is not None:
                video_ids.add(str(video["source_public_id"]))
    return demo_ids, video_ids


def plan_identity(plan):
    """The brief/source selection is the immutable identity for an initialized run."""
    demos, videos = selected(plan)
    brief = plan.get("brief", {})
    if not isinstance(brief, dict):
        raise ValidationError("plan.brief must be an object")
    return {"brief": redact({k: brief.get(k) for k in ("title", "slug")}),
            "source_ids": sorted(demos), "source_video_ids": sorted(videos)}


def make_run(plan):
    identity = plan_identity(plan)
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema": "demo-showcase-run/1", "run_id": str(uuid.uuid4()), "plan_identity": identity,
            "plan_fingerprint": fingerprint, "phase": "drafting", "pending_operation": None,
            "events": [], "checks": {"originals_unchanged": None, "metadata_verified": None,
            "media_bytes_verified": False, "caption_text_verified": False,
            "public_page_membership_verified": False, "desktop_playback_verified": False,
            "tablet_layout_verified": False}, "blockers": []}


def get_run(path):
    result = load(path)
    if not isinstance(result, dict) or result.get("schema") != "demo-showcase-run/1":
        raise ValidationError("not a demo showcase run record")
    return result


def event(run, kind, operation, source_id=None, target_id=None, **extra):
    entry = {"sequence": len(run["events"]) + 1, "kind": kind, "operation": operation,
             "source": {"id": str(source_id)} if source_id is not None else None,
             "destination": {"id": str(target_id)} if target_id is not None else None}
    entry.update(redact(extra))
    run["events"].append(entry)


def source_sets(run):
    identity = run.get("plan_identity", {})
    return set(identity.get("source_ids", [])), set(identity.get("source_video_ids", []))


def ensure_ids(run, target_id, source_id):
    source_demos, source_videos = source_sets(run)
    sources = source_demos | source_videos
    if str(target_id) in sources:
        raise ValidationError("mutation target matches a selected source demo or video ID")
    if source_id is not None and str(source_id) not in sources:
        raise ValidationError("source_id is not a selected source demo or video ID")


def ensure_payload_target(run, operation, target_id, payload):
    """Bind a write's actual MCP target field to its separately journaled target."""
    if not isinstance(payload, dict):
        raise ValidationError("operation payload must be an object")
    field = TARGET_FIELD.get(operation)
    if not field or payload.get(field) is None:
        return
    value = str(payload[field])
    if value != str(target_id):
        raise ValidationError("payload %s does not match --target-id" % field)
    ensure_ids(run, value, None)


def videos(snapshot):
    if isinstance(snapshot, dict):
        snapshot = snapshot.get("videos", snapshot.get("media", {}).get("videos", []))
    if not isinstance(snapshot, list):
        raise ValidationError("video state must be a get_demo object or videos array")
    return [item for item in snapshot if isinstance(item, dict)]


def video_id(video):
    for key in ("public_id", "publicId", "id"):
        if video.get(key) is not None:
            return str(video[key])
    return None


def command_init(args):
    plan = load(args.plan)
    candidate = make_run(plan)
    output = Path(args.output)
    if output.exists():
        old = get_run(output)
        if old.get("plan_fingerprint") != candidate["plan_fingerprint"]:
            raise ValidationError("run already exists for a different brief or source selection; refusing reset")
        print(json.dumps(redact(old), indent=2, sort_keys=True))
        return
    atomic_write(output, candidate)
    print(json.dumps(candidate, indent=2, sort_keys=True))


def command_begin(args):
    run = get_run(args.run)
    if run.get("pending_operation") is not None:
        raise ValidationError("a pending operation exists; reconcile or complete it before beginning another")
    payload, pre_state = load(args.payload_file), load(args.pre_state) if args.pre_state else None
    ensure_ids(run, args.target_id, args.source_id)
    ensure_payload_target(run, args.operation, args.target_id, payload)
    pending = {"operation": args.operation, "source": {"id": str(args.source_id)} if args.source_id is not None else None,
               "destination": {"id": str(args.target_id)}, "payload": redact(payload),
               "pre_state": redact(pre_state), "recovery_status": "pending"}
    # add_video reconciliation needs the complete pre-call destination video set.
    if args.operation == "add_video":
        if pre_state is None:
            raise ValidationError("add_video requires --pre-state from get_demo")
        pending["pre_video_ids"] = sorted(x for x in (video_id(v) for v in videos(pre_state)) if x)
    run["pending_operation"] = pending
    event(run, "begun", args.operation, args.source_id, args.target_id, payload=payload)
    atomic_write(args.run, run)
    print(json.dumps(redact(run), indent=2, sort_keys=True))


def command_complete(args):
    run = get_run(args.run)
    pending = run.get("pending_operation")
    if not pending:
        raise ValidationError("there is no pending operation to complete")
    result = load(args.result_file)
    failed = isinstance(result, dict) and (result.get("isError") is True or result.get("ok") is False or bool(result.get("error")))
    if failed:
        pending["recovery_status"] = "needs_review"
        event(run, "completion_needs_review", pending["operation"], (pending.get("source") or {}).get("id"),
              pending["destination"]["id"], result=result)
        atomic_write(args.run, run)
        print(json.dumps(redact(run), indent=2, sort_keys=True))
        return
    if completion_targets_another_destination(pending, result):
        pending["recovery_status"] = "needs_review"
        event(run, "completion_needs_review", pending["operation"], (pending.get("source") or {}).get("id"),
              pending["destination"]["id"], result=result,
              reason="completion result identifies a different destination")
        atomic_write(args.run, run)
        print(json.dumps(redact(run), indent=2, sort_keys=True))
        return
    event(run, "completed", pending["operation"], (pending.get("source") or {}).get("id"),
          pending["destination"]["id"], result=result)
    run["pending_operation"] = None
    atomic_write(args.run, run)
    print(json.dumps(redact(run), indent=2, sort_keys=True))


def completion_targets_another_destination(pending, result):
    """Reject results that explicitly identify a destination other than the pending one.

    Creation responses carry a newly assigned record ID, so an ``id`` is only
    comparable for operations whose target is itself a demo/client ID. Likewise
    add_video returns a new video ID: its parent demo is comparable only when
    the result explicitly exposes ``demo_id`` (or is a get_demo-shaped readback).
    """
    if not isinstance(result, dict):
        return False
    target = str(pending["destination"]["id"])
    operation = pending["operation"]
    field = RESULT_TARGET_FIELD.get(operation)
    if field and result.get(field) is not None:
        return str(result[field]) != target
    if operation == "add_video":
        if result.get("demo_id") is not None:
            return str(result["demo_id"]) != target
        if ("videos" in result or "media" in result) and result.get("id") is not None:
            return str(result["id"]) != target
    return False


def intended_matches(video, payload):
    for key in ("title", "language", "description"):
        if payload.get(key) != video.get(key):
            return False
    return True


def command_reconcile_video(args):
    run = get_run(args.run)
    pending = run.get("pending_operation")
    if not pending or pending.get("operation") != "add_video":
        raise ValidationError("reconcile-video requires a pending add_video operation")
    current_state = load(args.current)
    if isinstance(current_state, dict):
        stated_target = current_state.get("id", current_state.get("demo_id"))
        if stated_target is not None and str(stated_target) != pending["destination"]["id"]:
            raise ValidationError("current get_demo identity does not match the pending destination")
    current = videos(current_state)
    before = set(pending.get("pre_video_ids", []))
    candidates = [item for item in current if video_id(item) not in before and intended_matches(item, pending.get("payload", {}))]
    candidate_ids = [video_id(item) for item in candidates]
    unique_candidate = len(candidates) == 1 and candidate_ids[0] is not None and len(set(candidate_ids)) == len(candidate_ids)
    if unique_candidate:
        candidate = candidates[0]
        result = {"reconciled": True, "video_public_id": video_id(candidate), "video": candidate}
        event(run, "reconciled", "add_video", (pending.get("source") or {}).get("id"),
              pending["destination"]["id"], result=result)
        run["pending_operation"] = None
        outcome = "reconciled"
    else:
        pending["recovery_status"] = "needs_review"
        pending["recovery_candidates"] = redact([{k: item.get(k) for k in ("id", "public_id", "publicId", "title", "language", "description")} for item in candidates])
        event(run, "reconcile_needs_review", "add_video", (pending.get("source") or {}).get("id"),
              pending["destination"]["id"], candidate_count=len(candidates))
        outcome = "needs_review"
    atomic_write(args.run, run)
    print(json.dumps({"outcome": outcome, "run": redact(run)}, indent=2, sort_keys=True))


def command_status(args):
    print(json.dumps(redact(get_run(args.run)), indent=2, sort_keys=True))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init"); init.add_argument("--plan", required=True); init.add_argument("--output", required=True); init.set_defaults(func=command_init)
    begin = commands.add_parser("begin"); begin.add_argument("--run", required=True); begin.add_argument("--operation", required=True); begin.add_argument("--target-id", required=True); begin.add_argument("--source-id"); begin.add_argument("--payload-file", required=True); begin.add_argument("--pre-state"); begin.set_defaults(func=command_begin)
    complete = commands.add_parser("complete"); complete.add_argument("--run", required=True); complete.add_argument("--result-file", required=True); complete.set_defaults(func=command_complete)
    status = commands.add_parser("status"); status.add_argument("--run", required=True); status.set_defaults(func=command_status)
    reconcile = commands.add_parser("reconcile-video"); reconcile.add_argument("--run", required=True); reconcile.add_argument("--current", required=True); reconcile.set_defaults(func=command_reconcile_video)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        args.func(args)
    except ValidationError as exc:
        parser().error(str(exc))


if __name__ == "__main__":
    main()
