# Contributing

Use a branch and pull request for changes. Describe the behavior change, relevant validation and any new service dependency. Run `python3 scripts/check_release.py` before submitting.

Keep the client-copy workflow intact: new demo and media identities, unchanged source library records, complete content checks and readiness before publication. Do not introduce source reassignment, publication overrides, automatic destructive cleanup or hidden credential extraction.

Use synthetic fixtures. Never commit real client exports, run records, videos, caption files, signed upload/download URLs or tokens. Networked smoke tests must be separately authorized and use scoped validation destinations; the automated test suite must remain offline.

Python helpers use the standard library and support Python 3.9+. Add a focused regression test for a meaningful behavior fix. Changes to Demo Match itself are outside this repository.

For a release: update plugin version and CHANGELOG.md, run checks and the archive builder, inspect the archive file list, tag the tested commit, and attach the ZIP and SHA256SUMS file to the GitHub release. Update the installation guide's versioned examples. Document any unverified path without claiming broad compatibility.
