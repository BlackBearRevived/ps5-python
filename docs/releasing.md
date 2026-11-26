# Releasing

GitHub Actions builds PS5 artifacts on Ubuntu with pinned CPython and PS5
Payload SDK revisions. The workflow runs for pull requests, pushes to
`main`, version tags, and manual dispatches.

## Prepare a release

Run the host checks and validate on a PS5 with the payload environment:

```sh
make host-suite
PS5_HOST="<your-PS5-IP>" make ps5-test
PS5_HOST="<your-PS5-IP>" make ps5-web
```

Push a new version tag from the commit you intend to release:

```sh
git tag -a v0.1.1 -m "PS5-Python v0.1.1"
git push origin v0.1.1
```

The [workflow](../.github/workflows/release.yml) installs the PS5 SDK,
builds and packages the following assets, then checks the package layout
and SHA-256 digests:

- `python.elf`, `python-web.elf`, and `python-app-supervisor.elf`
- A `.tar.gz` runtime bundle with those launchers, the CPython standard
  library, web assets, and example apps
- A SHA-256 manifest covering the four files

GitHub signs provenance for the four binaries and bundle on trusted builds
in the public repository. For a version tag, the workflow then publishes the
checked assets to GitHub Releases. The `main` builds are available in the
corresponding Actions runs.

## Verify a download

In the directory containing the downloaded assets, substitute your version:

```sh
version=v0.1.1
prefix="python-ps5-$version"
sha256sum -c --strict "$prefix-SHA256SUMS"
for asset in "$prefix".tar.gz "$prefix"-*.elf; do
  gh attestation verify "$asset" \
    --repo BlackBearRevived/ps5-python \
    --signer-workflow BlackBearRevived/ps5-python/.github/workflows/release.yml \
    --source-ref "refs/tags/$version"
done
```

For an Actions artifact from `main`, use its `ci-<short-commit>` label and
pass `--source-ref refs/heads/main` instead.

## Package locally

With the SDK and host tools configured as described in the
[build guide](../README.md), generate and verify a local bundle:

```sh
make source-fetch
make host-build
bash tools/build_ps5.sh core
bash tools/build_ps5.sh web
bash tools/package_release.sh local dist/local
python3 tools/verify_release.py dist/local local
```

The package includes the runtime files and example apps. GitHub provenance
applies to the artifacts built in Actions. Record the firmware and payload
environment used for console testing in the release notes.
