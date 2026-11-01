# Deploying Parity to Cloud Run

One container (Playwright base image + the built workbench), one instance kept warm, run bundles in a Cloud Storage bucket,
the model key in Secret Manager. Spec: docs/19 §12. Docker is not needed on your machine; Cloud Build builds the image.

## First deploy
1. `gcloud auth login`, `gcloud config set project <id>` (billing enabled), `gcloud config set run/region us-central1`.
2. `deploy/cloudrun.sh setup` — enables the APIs; creates the Artifact Registry repo, the bucket (`<project>-parity-runs`, uniform
   access, never public), the `parity-run` service account with object-admin on that bucket only, and the empty secret.
3. `deploy/cloudrun.sh secret` — stores `MODEL_API_KEY` (from your shell, else from `.env`) as a secret version. Run this yourself;
   nothing prints the value.
4. `deploy/cloudrun.sh build` then `deploy/cloudrun.sh deploy` — builds with Cloud Build (tag = git sha) and deploys with
   `--allow-unauthenticated --min-instances 1 --max-instances 1 --cpu 2 --memory 2Gi --no-cpu-throttling --timeout 3600 --concurrency 20`,
   the bucket, the secret and `PARITY_TRUST_PROXY=1` (the per-visitor Live limit reads the first `X-Forwarded-For` hop).
5. Check `https://<url>/api/health`: `storage: "gcs"`, `models_ok: true`, `runs_indexed`.

## Redeploy
`deploy/cloudrun.sh build && deploy/cloudrun.sh deploy`. `build` tags the image with the commit it was built from and records that tag in `deploy/.image-tag` (local, git-ignored); `deploy` reuses it, so the two can run minutes and commits apart. `TAG=<sha> deploy/cloudrun.sh deploy` re-deploys any image already in the registry.

The service URL: `https://parity-u7lcbbxuia-uc.a.run.app` (project parity-hackathon-2026). Runs, decisions and screenshots live in the bucket, so they survive a
redeploy; the SQLite index and the model-response cache are rebuilt in `/tmp`. Boot reads each bundle once and evicts the oldest
Replay copies beyond `PARITY_REPLAY_KEEP` (default 50).

## Teardown
`deploy/cloudrun.sh teardown` deletes the service, the image repo, the bucket (all runs), the secret and the service account.

## Cost
A warm 2-CPU / 2 GiB instance is the cost that matters (a few dollars a day while judging); storage and operations are cents.
Set a budget alert in the Console if you leave it up.
