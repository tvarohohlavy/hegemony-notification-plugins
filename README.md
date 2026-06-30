<!--
SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# hegemony-notification-plugins

Standalone release repo for Hegemony notification plugin packages:

- `hegemony-notification-sdk`
- `hegemony-notification-core-transports`
- `hegemony-notification-shoutrrr-presets`
- `hegemony-notification-webhook-presets`

The SDK and all plugin wheels are released together from unified semver tags such as
`v0.2.0`. Plugin wheels depend on the exact SDK version from the same release.

A plugin depends only on `hegemony-notification-sdk` (which depends only on `pydantic`)
and exposes a `register(registry)` callable under the `hegemony.notification_providers`
entry-point group. The host injects a `NotificationServices` (secret resolution, template
rendering) into each transport, so plugins never import Hegemony internals. See the
[SDK README](packages/notification_sdk/README.md).

Public source is licensed under `AGPL-3.0-or-later`; commercial licenses may be
available separately. See [Licensing](LICENSING.md).

Contributions require the [Hegemony Contributor License Agreement](CLA.md). See
[Contributing](CONTRIBUTING.md).

## What is auto-installed vs opt-in

- **Auto-installed** with the platform (already present in Hegemony API and worker
  images): `hegemony-notification-sdk` and `hegemony-notification-core-transports` (the
  built-in `email`, `shoutrrr`, and `outgoing_webhook` transports).
- **Opt-in**: the preset packs (`hegemony-notification-shoutrrr-presets`,
  `hegemony-notification-webhook-presets`). Install only the packs a deployment wants.

A preset registers a friendly destination type that rewrites its config onto a base
transport. Both the **API** (to list/validate the destination type) and the **worker** (to
dispatch it) must have the pack installed. Restart both after installing so each registry
reloads its entry points. Do not use `--system`; Hegemony runs from `/opt/venv`.

## Install From A Release

Released wheels are published with a `SHA256SUMS` file. Verify downloaded wheels before
installing them. The example installs both preset packs into the API and worker; remove any
wheel names a deployment should not enable.

```bash
VERSION=0.2.0
API_CONTAINER=<your API container name>
WORKER_CONTAINER=<your worker container name>

for CONTAINER in "${API_CONTAINER}" "${WORKER_CONTAINER}"; do
  docker exec -u root -it "${CONTAINER}" bash -lc "
set -euo pipefail
version=${VERSION}
base=https://github.com/tvarohohlavy/hegemony-notification-plugins/releases/download/v\${version}
tmp=\$(mktemp -d)
cd \"\${tmp}\"
curl -fsSLO \"\${base}/SHA256SUMS\"
for wheel in \
  hegemony_notification_shoutrrr_presets-\${version}-py3-none-any.whl \
  hegemony_notification_webhook_presets-\${version}-py3-none-any.whl
do
  curl -fsSLO \"\${base}/\${wheel}\"
  grep \"  \${wheel}$\" SHA256SUMS | sha256sum -c -
done
uv pip install --python /opt/venv/bin/python --no-deps ./*.whl
rm -rf \"\${tmp}\"
"
  docker restart "${CONTAINER}"
done
```

Or build local wheels from this repository and copy them into the running dev containers:

```bash
cd ../hegemony-notification-plugins
task build

for CONTAINER in hegemony-dev-api-1 hegemony-dev-worker-1; do
  docker exec -u root "${CONTAINER}" mkdir -p /tmp/notification-wheels
  docker cp dist/. "${CONTAINER}:/tmp/notification-wheels/"
  docker exec -u root -it "${CONTAINER}" bash -lc '
  uv pip install --python /opt/venv/bin/python --no-deps \
    /tmp/notification-wheels/hegemony_notification_shoutrrr_presets-*.whl \
    /tmp/notification-wheels/hegemony_notification_webhook_presets-*.whl
  '
  docker restart "${CONTAINER}"
done
```

These Docker-command installs are runtime changes. Re-run them after recreating a container
or replacing the image.

## Development

```bash
uv sync --all-packages
uv run pre-commit install --install-hooks
```

If you have [Task](https://taskfile.dev/) installed, the common workflow is:

```bash
task setup
task lint
task test
task build
task smoke
```

The hook set mirrors Hegemony where applicable for this package-only repo: general file
hygiene, pyproject validation, typos, Zizmor, workflow schema checks, REUSE, Ruff,
typecheck, tests, Gitleaks, and commitlint. UI, Docker, OpenAPI, and task-runner hooks stay
in Hegemony because those surfaces are not present here.

Run the local equivalent of CI:

```bash
task ci
```

Run every configured pre-commit hook manually:

```bash
task precommit
```

Before tagging a release, update every package version and plugin SDK pin:

```bash
task version:set -- 0.2.0
task lock
```

Tags must match package metadata. A `v0.2.0` tag publishes four wheels plus `SHA256SUMS` to
the matching GitHub Release.

Releases are intended to be immutable: the release workflow fails if a GitHub Release for
the tag already exists and never replaces published assets. If a release artifact is wrong,
cut a new patch tag instead of mutating the existing release. The release workflow also
creates GitHub artifact attestations for the wheel files and checksum file.
