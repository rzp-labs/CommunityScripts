# Maintained PythonToolsInstaller feed

This public AGPL-3.0 fork preserves stashapp/CommunityScripts history and source.
Only PythonToolsInstaller is maintained/published here; the upstream catalog is
retained for history and is excluded by `publication-plugins.txt`.

The repair is tracked by Linear VEX-89. Codex assisted its implementation.
The upstream README's conditions for human code review and human testing govern
contributions submitted to stashapp/CommunityScripts. Publication from this fork
follows the user's scoped authorization and the coordinating task's explicit
independent review clearance. Automated reviews and agent-executed tests must be
reported as such; they do not constitute human review or human testing. A draft
PR and locally generated candidate ZIP are review materials; neither publishes
a release or enables a live migration.

## Validate and reproduce a committed candidate

Use Python 3.8+ and Git/Bash/coreutils. CI tests Python 3.13 and 3.14 with stdlib
unittest and an offline, locally generated wheel. No application image builds,
external runtime packages, credentials or live Stash instance are needed.

```sh
python3 -m unittest discover -s tests -v
./build_site.sh _site/stable
```

The feed uses upstream's `stable/index.yml` format and the descriptor's existing
`PythonToolsInstaller` runtime ID, task and exec settings. Version is `0.1.4` plus
the full source commit SHA; the index date is that commit's UTC committer date.
This identifies updates to any packaged docs/build/tests or HEAD provenance,
even when plugin runtime files do not change. ZIP bytes are deterministic
for a fixed commit, include full source/build scripts and AGPL notices, and have
their SHA-256 recorded in the index. Only tracked files are packaged: local venvs,
bytecode and copy logs are excluded. `SOURCE.json` records the full source commit
and immutable corresponding-source URL. Dependencies remain unpinned and are
resolved by pip at installation, matching upstream behavior.

## Release after independent review

1. Review the exact PR head and candidate ZIP, including tests and package hashes.
   Obtain explicit independent review clearance from the coordinating task before
   publication. Identify automated review and agent-executed tests accurately.
   If merging changes the commit, rebuild and inspect its new provenance and ZIP
   hash before release.
2. Enable repository Actions and configure GitHub Pages to use GitHub Actions if
   needed. Merge the reviewed source. Create a tag such as
   `pythontoolsinstaller-v0.1.4` at that exact reviewed release commit and publish
   a non-prerelease GitHub release. Do not use a moving branch as the release ref.
3. The existing Pages workflow pins checkout to the release event's `github.sha`,
   builds only `_site/stable` from the allowlist, runs the focused tests, and
   deploys once. Later tag movement cannot change its source. Branch pushes have no
   publication trigger. No develop or whole-catalog feed is generated.
4. Verify `https://rzp-labs.github.io/CommunityScripts/stable/index.yml`, its sole
   plugin ID, package hash and `SOURCE.json` against the release commit.

No GitHub release, Pages enablement or deployment is performed during candidate
preparation. Live migration and backups belong to the coordinating task; this
repository task must not change Unraid or run library sync. System site-packages
still need reinstallation after container replacement when not bundled in the
image; this repair does not change that persistence behavior.
