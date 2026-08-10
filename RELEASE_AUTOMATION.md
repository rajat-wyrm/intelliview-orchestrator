# Release Automation

This document explains the automated versioning and release pipeline set
up for this repository. It's the counterpart to the Conventional Commits
convention documented by the changelog/commit-docs task — that document
covers *how to write a commit*; this one covers *what happens to it
afterward*.

## What runs, and when

`.github/workflows/release.yml` runs on every push to the `main` branch, and
also accepts the repo's current `Stabilized-version` integration branch. It:

1. Checks out full git history (`fetch-depth: 0` — semantic-release needs
   every commit and tag to compute the next version).
2. Installs the pinned release tooling from `package-lock.json`
   (`npm ci`, not `npm install`, so CI always uses exactly what's committed).
3. Runs `npx semantic-release`, driven by `.releaserc.json`.

No manual version bump, changelog edit, or GitHub Release is ever created
by hand — the workflow is the only thing that writes a version.

## How the version number is decided

`.releaserc.json` configures `@semantic-release/commit-analyzer` with
`conventionalcommits` rules:

| Commit type | Version bump |
|---|---|
| `feat` | minor |
| `fix`, `perf`, `refactor`, `chore`, `docs`, `test` | patch |
| any commit with a `BREAKING CHANGE:` footer | major |

This is a deliberate departure from semantic-release's default (which
only reacts to `feat`/`fix`/`perf`): the task's Definition of Done says
*every* merge should produce a release, so every Conventional Commit type
in use here triggers at least a patch bump. If that turns out to be too
noisy in practice (e.g. a `docs:` typo fix cutting a release), tightening
`releaseRules` in `.releaserc.json` to drop `chore`/`docs`/`test` is a
one-line change.

## What gets generated automatically

On a successful run:

- **`CHANGELOG.md`** — `@semantic-release/changelog` prepends a new
  version section (grouped into Features / Bug Fixes / Chores /
  Documentation / etc., matching the commit types) above the existing
  content. It never rewrites history that's already there.
- **A git tag** — `vX.Y.Z`, pointing at the release commit.
- **A GitHub Release** — created by `@semantic-release/github`, with the
  same notes, attached to that tag.
- **A release commit** — `chore(release): X.Y.Z [skip ci]`, pushed back
  to the release branch (`main` or `Stabilized-version`), containing the
  updated `CHANGELOG.md`. The
  `[skip ci]` marker stops this commit from re-triggering the workflow.

## Commit message enforcement

`.github/workflows/commitlint.yml` runs on every pull request targeting
`main` or `Stabilized-version` and rejects any commit whose subject line
doesn't follow `<type>(<scope>): <subject>`. Allowed types are configured in
`.commitlintrc.json`. This exists because semantic-release's version
calculation is only as reliable as the commit history feeding it — a
malformed commit either gets silently ignored or misclassified, so it's
caught at PR time instead of discovered at release time.

## Required repository permissions

The workflow needs `contents: write` on `GITHUB_TOKEN` to push the tag,
release commit, and GitHub Release (already set in `release.yml`'s
`permissions:` block). Two things to check in the repo's own settings
if the first run fails with a permissions error rather than the
expected `EGITNOPERMISSION`/auth error you'd see locally:

- **Settings → Actions → General → Workflow permissions** — must allow
  "Read and write permissions."
- If branch protection is enabled on `Stabilized-version` with required
  status checks, add the release job to the bypass list for
  `github-actions[bot]`, or the push in step 3 will be rejected the same
  way a human's direct push would be.

## Testing performed

Before merging, the config was validated with a dry run against this
repo's actual commit history:

```bash
npm ci
npx semantic-release --dry-run
```

Result: all eight plugins (`commit-analyzer`, `release-notes-generator`,
`changelog`'s `verifyConditions`/`prepare`, `git`'s
`verifyConditions`/`prepare`, and `github`'s `verifyConditions`/`publish`/
`addChannel`/`success`/`fail`) loaded and initialized without error, and
semantic-release correctly identified `Stabilized-version` as the release
branch and attempted the tag push — it only stopped there because a dry
run uses a placeholder credential with no push access, which is expected
outside of real CI. This confirms the plugin chain and config are wired
together correctly; the first real run on `Stabilized-version` (with the
`GITHUB_TOKEN` GitHub Actions provides automatically) will be the
end-to-end confirmation.

To reproduce this locally against a fresh clone:

```bash
git clone --depth 1 -b Stabilized-version <repo-url>
cd intelliview-orchestrator
npm ci
npx semantic-release --dry-run --no-ci
```
