# Build and retain the demo source bundle

The `source-bundle` CI job builds the fictional-data demo source ZIP and its
SHA-256 checksum without installing application dependencies. Its artifact,
`demo-source-bundle`, is retained for 14 days. It is source for an installation,
not a container image or evidence that a human has installed the demo.

For an installation, select the `push` run on `dev` for the owner's merged full
commit, with all applicable CI jobs passing. Save that run's
artifact before expiry, recording the repository, full source commit, run URL,
artifact name and ZIP checksum with the private operator release record. A
passing packaging job alone does not establish that the other checks passed.
PR artifacts are review candidates: the default pull-request checkout tests a
temporary merge commit, which can differ from the feature head and the later
squash-merge commit. Do not label a PR bundle with either of those other SHAs.
For PR review evidence, record its actual checked-out commit from checkout logs,
as well as the run URL, feature head and artifact checksum. The ZIP does not
embed a Git commit. Only the owner selects an installation.

## Build locally

From the selected source directory with Python 3.13:

```powershell
python build_deployment.py --output-dir output/source-candidate
Get-FileHash output/source-candidate/AgentX_Learn_Deployment.zip -Algorithm SHA256
Get-Content output/source-candidate/AgentX_Learn_Deployment.sha256
```

Compare the hash with the checksum file before extracting. On Linux use
`python3.13` and, from the output directory, `sha256sum -c AgentX_Learn_Deployment.sha256`.
The default command `python build_deployment.py` still writes to
`output/deployment`. Use a separate output directory to preserve earlier local
artifacts; the named ZIP/checksum in the selected directory are replaced on success.
Older files already tracked under `output/deployment` are historical outputs,
not evidence for the latest revision.

The ZIP includes `build_deployment.py`, this guide and its regression tests.
The extracted source can build another bundle using the same command. ZIP entry
order, timestamps and permissions are fixed, so repeated builds from identical
file bytes with the same Python/compression environment produce identical bytes.
Git checkout line endings and compression implementations can differ across
machines: compare the per-file manifest for content identity, and retain the
checksum of the actual approved artifact. Rebuilding after any source change
creates a different candidate requiring its own review evidence.

## What is checked

- Root files use an explicit allowlist. Source, tests, browser tests, agent
  documentation and CI files use the existing directory/extension allowlist.
- `.env`, data, generated output, temporary work, participant records placed
  outside the allowlist, Python caches and local skill/configuration directories
  are excluded. A file resolving outside the source root is rejected.
- The locally configured `LLM_GATEWAY_API_KEY`, if present in `.env`, must not
  appear in any payload file. This is a check for that configured key, not a
  general secret scanner. Do not put private records or credentials in source,
  tests, agent documentation or CI directories.
- `MANIFEST.sha256` lists the hash of every payload file except itself. The
  archive is reopened and checked for corruption, exact entry coverage and
  exact bytes before it replaces the selected output.
- Windows/Linux regression tests check checksum and manifest coverage, required
  documents, local Markdown links, private-file exclusion, repeated builds and
  configured-key rejection even with Python optimization enabled.

A missing required file or a key in the payload fails before output creation
or replacement. Diagnostics omit file contents and exception details. Archive
and checksum replacement are two filesystem operations, not a transaction;
interruption or an output error may leave a mismatched pair. Always compare
the ZIP hash with the checksum before using it. A failed CI build is not uploaded.

Hashes detect a mismatch against a retained trusted checksum; they are not a
signature, authenticity guarantee or complete security review. The bundle has
public fictional pilot material, so use private replacement assessments for
participants who have already seen it. Keep completed pilot records and actual
databases outside the repository and artifact.

Follow [the demo release handover](DEMO-RELEASE-CHECKLIST.md) for owner selection,
installation, backup, recovery and human checks. Use [README.md](README.md) or
[DEMO-DEPLOYMENT.md](DEMO-DEPLOYMENT.md) for the supported installation paths.
