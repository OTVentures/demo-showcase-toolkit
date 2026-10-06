# Changelog

## 1.1.0

- Claude Code plugin manifest and marketplace entry alongside the existing Codex packaging.
- Shared skill and MCP connection with host-specific setup and marketer instructions.
- Release checks keep both manifests and marketplace entries consistent.
- Claude Code manifest validation included in CI.

## 1.0.1

- Public reusable distribution for the OTVentures organization.
- MIT license, general onboarding, version-pinned installation instructions, contribution and security guidance.
- Private validation references and machine-specific operator details removed.
- Offline release validation, macOS/Linux CI, and allowlisted versioned ZIP packaging.
- Caption plans retain only language metadata; signed URLs in queries or fragments are rejected.
- Upload success requires a valid 2xx response. Wrong-destination completion results remain pending for review.
- 25 offline tests, including regression coverage for these release fixes.

## 1.0.0

- Initial conversational client-copy workflow with planning, metadata verification, durable operation journal and hosted-video upload helper.
- Live validation of two copied demos, five videos and fifteen caption tracks; source preservation, publication, browser checks and retry recovery.
