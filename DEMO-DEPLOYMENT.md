# Run and maintain the fictional-data demo

This release is a local demo with shared seeded accounts. Use fictional content only.
Customer authentication, access provisioning, PostgreSQL migrations, public HTTPS,
monitoring and company onboarding belong to the later production milestone.

## Container installation

Install Docker with Compose, then run from this folder:

```sh
docker compose up --build -d --wait
docker compose ps
```

Open http://127.0.0.1:8010. Accounts: learner, trainer, alex; password:
`LearnDemo2026!`. The port binds only to localhost. Set `DEMO_PORT` in your shell
to choose another host port. Compose always uses offline demo mode and needs no
model key. `.env` and local databases never enter the image.

The container runs as UID 10001 with a read-only root filesystem. SQLite and
isolated rehearsals live in the named `training-data` volume. One application
worker is intentional; this demo is not a horizontally scalable deployment.

## Updates and rollback

Before updating, stop the app and back up its data. Check out the reviewed release
commit, then run `docker compose up --build -d --wait`. Container replacement
preserves the named volume. Keep the prior commit and its matching backup for
rollback: stop, restore that backup, check out the prior commit, rebuild and start.
Do not assume a newer database can be opened safely by older application code.
Never run `docker compose down --volumes` unless you intend to erase demo data.

## Consistent backup and restore

Stop the app before copying SQLite, including any journal files and rehearsals:

```sh
docker compose stop app
docker compose cp app:/app/data ./demo-backup
docker compose start app
```

Store backups outside Git with restricted access. Restore into an empty data volume
with the app stopped, using `python restore_demo.py ./demo-backup` (Python 3.13
on the host). This extracts files as UID 10001 so the app can write them afterward.
Then start and check `/health`, sign in, and verify a saved course or progress
record. Test restoration before relying on a backup. Copying is a local operation;
this setup does not provide automated off-machine backups.

## Local development and dependency updates

Use Python 3.13 (the verified container and development target):

```sh
python -m venv .venv
python -m pip install --require-hashes -r requirements.txt
python -m pytest -q
node --test tests/dashboard.test.cjs
```

Activate `.venv` before these Python commands, or use its interpreter explicitly.
`requirements.txt` retains the existing development install entrypoint;
`requirements-runtime.txt` contains only runtime dependencies. Input ranges live
in `requirements-dev.in` and `requirements-runtime.in`. To update, install
`pip-tools==7.6.2` in a tooling environment and regenerate both hashed locks with
Python 3.13:

```sh
pip-compile --upgrade --generate-hashes -o requirements-runtime.txt requirements-runtime.in
pip-compile --upgrade --generate-hashes -o requirements.txt requirements-dev.in
```

Review dependency and base-image changes in a feature PR. Verify a clean Windows
and Linux install, Python and dashboard tests, and the container smoke test.
Dependencies with platform markers require regenerating and checking both target
environments. The Docker base image is pinned by digest and must be refreshed
explicitly. No automatic publishing or deployment occurs in CI.
