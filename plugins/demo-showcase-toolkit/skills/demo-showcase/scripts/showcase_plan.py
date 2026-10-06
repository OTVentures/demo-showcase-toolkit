#!/usr/bin/env python3
"""Build and verify local JSON plans for copying Demo Match showcase demos.

This tool deliberately makes no API calls.  ``plan`` prepares create_demo-shaped
draft payloads and media manifests; ``verify`` compares JSON snapshots after an
operator has performed the copy. It never claims media-byte equality: that needs
a separate byte/hash verification process.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

BASE = "https://demos.otventures.vc"
META = ("title", "description", "tags", "products", "product_alignment",
        "product_details", "product_descriptions", "website_languages", "country",
        "region", "has_walkthrough", "demo_url", "links")
CAPTIONS = ("en", "de", "fr-CA")
SENSITIVE_URL_PARAMETER = re.compile(
    r"(?:sig(?:nature)?|token|credential|x-amz-signature|awsaccesskeyid|api[_-]?key)=", re.I)


class ValidationError(ValueError):
    pass


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("cannot read JSON %s: %s" % (path, exc))


def records(value, label):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("demos", "records", "data"):
            if isinstance(value.get(key), list):
                return value[key]
    raise ValidationError("%s must be an array, or an object containing demos" % label)


def rec_id(record):
    value = record.get("id", record.get("demo_id"))
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("each demo record needs an integer id")
    return value


def public_id(record):
    for key in ("public_id", "publicId", "slug"):
        if record.get(key) not in (None, ""):
            return record[key]
    return str(rec_id(record))


def media(record, kind):
    bag = record.get("media", {})
    value = record.get(kind, bag.get(kind, [])) if isinstance(bag, dict) else record.get(kind, [])
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def published(record):
    return record.get("published") is True or record.get("status") == "published"


def safe_url(value, field):
    if not isinstance(value, str):
        return value
    parsed = urlparse(value)
    if parsed.scheme and parsed.scheme.lower() not in ("http", "https"):
        raise ValidationError("%s uses a disallowed URL scheme" % field)
    # URLs containing credentials or signed download parameters should never be
    # copied into a draft payload or a portable plan.
    if (parsed.username or parsed.password or SENSITIVE_URL_PARAMETER.search(parsed.query)
            or SENSITIVE_URL_PARAMETER.search(parsed.fragment)):
        raise ValidationError("%s appears to be an authenticated download URL" % field)
    return value


def clean_metadata(record):
    result = {}
    for key in META:
        if key not in record:
            continue
        value = copy.deepcopy(record[key])
        if key in ("demo_url",):
            safe_url(value, key)
        if key == "links":
            if not isinstance(value, list):
                raise ValidationError("links must be an array")
            for item in value:
                if isinstance(item, str):
                    safe_url(item, "links")
                elif isinstance(item, dict) and "url" in item:
                    safe_url(item["url"], "links.url")
        result[key] = value
    return result


def import_url(item, source_public_id, field):
    if item.get("hosted") is False:
        raw = item.get("external_url") or item.get("source_url") or item.get("url") or item.get("public_url")
    else:
        raw = item.get("source_url") or item.get("pub") or item.get("url") or item.get("public_url") or item.get("external_url")
    if raw:
        safe_url(raw, field)
    hosted = bool(item.get("hosted", raw))
    if not hosted:
        return raw
    if not raw:
        raise ValidationError("hosted %s needs a source_url" % field)
    parsed = urlparse(raw)
    path = parsed.path if parsed.scheme else raw
    if not parsed.scheme and (path.startswith("pub/") or path.startswith("/pub/") or path.startswith("pf/") or path.startswith("/pf/") or path.startswith("pv/") or path.startswith("/pv/") or path.startswith("v/") or path.startswith("/v/")):
        return BASE + "/" + path.lstrip("/")
    # Explicit public HTTPS URLs are allowed only as an import source; they are
    # never included in create_demo metadata as a target object URL.
    return raw


def video_spec(record):
    if media(record, "videos") and not published(record):
        raise ValidationError("source %s has hosted media but is not published" % rec_id(record))
    out, missing = [], []
    for item in media(record, "videos"):
        if not isinstance(item, dict):
            raise ValidationError("video entries must be objects")
        source_tracks = item.get("tracks", item.get("captions", []))
        if not isinstance(source_tracks, list):
            raise ValidationError("video tracks must be an array")
        # get_subtitle retrieves the caption body, label, and default flag by
        # source video ID plus language. Keep only that lookup key in plans so
        # signed VTT URLs and provider-specific fields never become durable
        # operator state.
        tracks = []
        for track in source_tracks:
            if not isinstance(track, dict):
                raise ValidationError("caption tracks must be objects")
            language = track.get("language", track.get("lang"))
            if not isinstance(language, str) or not language:
                raise ValidationError("caption tracks need a language")
            tracks.append({"language": language})
        languages = {track["language"] for track in tracks}
        lacking = [lang for lang in CAPTIONS if lang not in languages]
        if lacking:
            missing.append({"video_id": item.get("id"), "missing": lacking})
        out.append({"source_public_id": public_id(item), "title": item.get("title", record.get("title")),
                    "description": item.get("description", ""), "language": item.get("language"),
                    "duration_seconds": item.get("duration_seconds"), "hosted": bool(item.get("hosted", True)),
                    "source_url": import_url(item, public_id(record), "video.source_url"), "tracks": tracks})
    return out, missing


def slug_for(base, source_id, used):
    clean = re.sub(r"[^a-z0-9-]+", "-", str(base).lower()).strip("-") or "showcase"
    suffix = "-%s" % source_id
    candidate = clean[:64-len(suffix)].rstrip("-") + suffix
    serial = 2
    while candidate in used:
        serial_suffix = "-%d" % serial
        candidate = clean[:64-len(suffix)-len(serial_suffix)].rstrip("-") + suffix + serial_suffix
        serial += 1
    used.add(candidate)
    return candidate


def select(brief, source_records):
    if not isinstance(brief, dict) or not isinstance(brief.get("title"), str) or not brief["title"].strip():
        raise ValidationError("brief.title must be a nonempty string")
    if not isinstance(brief.get("slug"), str) or not brief["slug"].strip():
        raise ValidationError("brief.slug must be a nonempty string")
    ids = brief.get("source_ids")
    if brief.get("selection_confirmed") is not True:
        raise ValidationError("selection_confirmed must be true before drafts can be planned")
    if not isinstance(ids, list) or not ids:
        raise ValidationError("source_ids must be a nonempty array")
    if any(isinstance(x, bool) or not isinstance(x, int) for x in ids) or len(set(ids)) != len(ids):
        raise ValidationError("source_ids must contain unique integer IDs")
    mapping = {}
    for record in source_records:
        ident = rec_id(record)
        if ident in mapping:
            raise ValidationError("duplicate source record identity %s" % ident)
        mapping[ident] = record
    missing = [x for x in ids if x not in mapping]
    if missing:
        raise ValidationError("selected source IDs were not resolved: %s" % missing)
    unpublished = [x for x in ids if not published(mapping[x])]
    if unpublished:
        raise ValidationError("selected sources must be published before import: %s" % unpublished)
    return [(x, mapping[x]) for x in ids]


def plan(args):
    brief, source_records = load(args.brief), records(load(args.sources), "sources")
    chosen, used, drafts, blockers = select(brief, source_records), set(), [], []
    for source_id, source in chosen:
        showcase_slug = re.sub(r"[^a-z0-9-]+", "-", brief["slug"].lower()).strip("-") or "showcase"
        slug = slug_for(showcase_slug, source_id, used)
        videos, missing = video_spec(source)
        factsheets = []
        source_factsheets = media(source, "factsheets")
        if not source_factsheets and source.get("factsheet_url"):
            source_factsheets = [{"id": source.get("factsheet_id"), "title": source.get("factsheet"),
                                  "source_url": source["factsheet_url"], "hosted": True}]
        for item in source_factsheets:
            if not isinstance(item, dict):
                raise ValidationError("factsheet entries must be objects")
            factsheets.append({"title": item.get("title"), "hosted": bool(item.get("hosted", True)),
                               "source_url": import_url(item, public_id(source), "factsheet.source_url")})
        item_blockers = (["missing legacy captions: " + ", ".join(sorted({lang for x in missing for lang in x["missing"]}))] if missing else [])
        blockers.extend([{"source_id": source_id, "reason": x} for x in item_blockers])
        payload = clean_metadata(source)
        payload.update({"slug": slug, "status": "draft", "private": True, "audience": "client", "client": brief["title"],
                        "admin_note": "showcase-toolkit/1:%s:%s" % (showcase_slug, source_id)})
        drafts.append({"source_id": source_id, "source_public_id": public_id(source), "create_demo": payload,
                       "media": {"videos": videos, "factsheets": factsheets}, "publish_blockers": item_blockers})
    return {"schema_version": 1, "plan_status": "needs_input" if blockers else "ready_for_drafts",
            "brief": {"title": brief["title"], "slug": brief["slug"]}, "drafts": drafts,
            "publish_blockers": blockers, "verification_limits": {"media_bytes_verified": False,
            "reason": "IDs and URLs cannot prove media byte equality; separate byte/hash verification is required."}}


def signature(record):
    """Stable source state: retain operational ownership/publication fields too.

    Views, analytics and timestamps are intentionally omitted because they are
    expected to change while a showcase is being copied.
    """
    volatile = {"views", "view_count", "analytics", "created_at", "updated_at",
                "timestamp", "last_viewed_at", "plays", "play_count"}
    def stable(value):
        if isinstance(value, list):
            return [stable(x) for x in value]
        if isinstance(value, dict):
            return {k: stable(v) for k, v in value.items() if k not in volatile}
        return value
    return stable(record)


def target_for(targets, draft):
    marker = draft["create_demo"]["admin_note"]
    matches = [x for x in targets if x.get("admin_note") == marker]
    if len(matches) != 1:
        raise ValidationError("expected one target with marker %s; found %d" % (marker, len(matches)))
    return matches[0]


def caption_signature(tracks):
    """Compare caption meaning, not per-object VTT URLs or upload timestamps."""
    result = []
    for track in tracks or []:
        if not isinstance(track, dict):
            result.append(track)
            continue
        item = {k: track.get(k) for k in ("language", "lang", "label", "default") if k in track}
        for key in ("sha256", "content_hash", "vtt_sha256"):
            if key in track:  # hashes, when supplied, are meaningful evidence
                item[key] = track[key]
        result.append(item)
    return result


def factsheet_entries(record):
    entries = media(record, "factsheets")
    if entries:
        return entries
    if record.get("factsheet_url") or record.get("factsheet_id") or record.get("factsheet"):
        return [{"id": record.get("factsheet_id"), "title": record.get("factsheet"), "url": record.get("factsheet_url")}]
    return []


def verify(args):
    plan_data = load(args.plan)
    if not isinstance(plan_data, dict) or not isinstance(plan_data.get("drafts"), list):
        raise ValidationError("plan must contain drafts")
    if not plan_data["drafts"]:
        raise ValidationError("plan contains no selected drafts")
    before, after, targets = records(load(args.before), "before"), records(load(args.after), "after"), records(load(args.targets), "targets")
    before_map = {rec_id(x): x for x in before}
    after_map = {rec_id(x): x for x in after}
    failures, checks = [], []
    selected_source_ids = {draft["source_id"] for draft in plan_data["drafts"]}
    source_video_ids, target_demo_ids, target_video_ids = set(), set(), set()
    for source_id in selected_source_ids:
        original = before_map.get(source_id)
        if original:
            source_video_ids.update(v.get("public_id") for v in media(original, "videos") if v.get("public_id"))
    for draft in plan_data["drafts"]:
        source_id = draft["source_id"]
        original, current = before_map.get(source_id), after_map.get(source_id)
        if not original or not current or signature(original) != signature(current):
            failures.append({"source_id": source_id, "reason": "selected original changed or is missing"})
            continue
        try:
            target = target_for(targets, draft)
        except ValidationError as exc:
            failures.append({"source_id": source_id, "reason": str(exc)})
            continue
        target_ident = rec_id(target)
        if target_ident in selected_source_ids or target_ident in target_demo_ids:
            failures.append({"source_id": source_id, "reason": "target demo ID is reused across source/target copies"})
        target_demo_ids.add(target_ident)
        payload = draft["create_demo"]
        if rec_id(target) == source_id or public_id(target) == draft["source_public_id"]:
            failures.append({"source_id": source_id, "reason": "target reuses source identity"})
        for key, value in clean_metadata(original).items():
            if target.get(key) != value:
                failures.append({"source_id": source_id, "reason": "target metadata differs: %s" % key})
        if (target.get("private") is not True or target.get("audience") != "client"
                or target.get("client") != payload["client"] or target.get("status") != args.stage):
            failures.append({"source_id": source_id, "reason": "target %s/privacy/client fields are incorrect" % args.stage})
        if target.get("default_narration_language") != original.get("default_narration_language"):
            failures.append({"source_id": source_id, "reason": "default narration language differs"})
        source_v, target_v = media(original, "videos"), media(target, "videos")
        if len(source_v) != len(target_v):
            failures.append({"source_id": source_id, "reason": "video count differs"})
        source_ids = [v.get("public_id") for v in source_v]
        target_ids = [v.get("public_id") for v in target_v]
        if any(not x for x in source_ids + target_ids) or len(set(source_ids)) != len(source_ids) or len(set(target_ids)) != len(target_ids) or set(source_ids) & set(target_ids):
            failures.append({"source_id": source_id, "reason": "video public IDs are missing, duplicated, or reused"})
        if set(target_ids) & source_video_ids or set(target_ids) & target_video_ids:
            failures.append({"source_id": source_id, "reason": "target video public ID is reused across copies"})
        target_video_ids.update(x for x in target_ids if x)
        for index, (src, dst) in enumerate(zip(source_v, target_v)):
            for key in ("title", "description", "language", "duration_seconds"):
                if src.get(key) != dst.get(key):
                    failures.append({"source_id": source_id, "reason": "video %d differs: %s" % (index, key)})
            if caption_signature(src.get("tracks")) != caption_signature(dst.get("tracks")):
                failures.append({"source_id": source_id, "reason": "video %d differs: caption metadata" % index})
            source_pub, target_pub = src.get("pub"), dst.get("pub")
            if src.get("hosted", True):
                if dst.get("hosted") is not True:
                    failures.append({"source_id": source_id, "reason": "hosted video %d is not hosted" % index})
                if not target_pub:
                    failures.append({"source_id": source_id, "reason": "hosted video %d has no destination public URL" % index})
                for field in ("storage_key", "object_key"):
                    if src.get(field) and src.get(field) == dst.get(field):
                        failures.append({"source_id": source_id, "reason": "hosted video %d reuses source %s" % (index, field)})
                if source_pub and (target_pub == source_pub or (dst.get("external_url") and source_pub in dst["external_url"])):
                    failures.append({"source_id": source_id, "reason": "video %d references source publication" % index})
            elif dst.get("hosted") is not False or dst.get("external_url") != src.get("external_url"):
                failures.append({"source_id": source_id, "reason": "external video %d provider URL/hosting differs" % index})
        source_f, target_f = factsheet_entries(original), factsheet_entries(target)
        if len(source_f) != len(target_f):
            failures.append({"source_id": source_id, "reason": "factsheet count differs"})
        for index, (src, dst) in enumerate(zip(source_f, target_f)):
            if src.get("id") and src.get("id") == dst.get("id"):
                failures.append({"source_id": source_id, "reason": "factsheet %d reuses source ID" % index})
            source_url, target_url = src.get("url", src.get("source_url")), dst.get("url", dst.get("source_url"))
            if source_url and source_url == target_url:
                failures.append({"source_id": source_id, "reason": "factsheet %d references source URL" % index})
        checks.append({"source_id": source_id, "target_id": rec_id(target)})
    return {"verified": not failures, "status": "verified" if not failures else "failed", "checks": checks,
            "failures": failures, "media_bytes_verified": False,
            "verification_limits": "Media fields, ordering, captions, and identities were compared. Byte equality requires separate byte/hash verification."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fields in (("plan", ("brief", "sources")), ("verify", ("plan", "before", "after", "targets"))):
        cmd = sub.add_parser(name)
        for field in fields:
            cmd.add_argument("--" + field, required=True, type=Path)
        cmd.add_argument("--output", required=True, type=Path)
        if name == "verify":
            cmd.add_argument("--stage", choices=("draft", "published"), default="published",
                             help="expected target status (default: published for final verification)")
    args = parser.parse_args(argv)
    try:
        result = plan(args) if args.command == "plan" else verify(args)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        if args.command == "verify" and not result["verified"]:
            raise SystemExit(1)
    except ValidationError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
