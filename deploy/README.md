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
   the bucket, the secret and `PARITY_TRUST_PROXY=1` (the per-visitor Live limit reads the right-most `X-Forwarded-For` hop, the address the front end saw).
5. Check `https://<url>/api/health`: `storage: "gcs"`, `models_ok: true`, `runs_indexed`.

## Redeploy
`deploy/cloudrun.sh build && deploy/cloudrun.sh deploy`. `build` tags the image with the commit it was built from and records that tag in `deploy/.image-tag` (local, git-ignored); `deploy` reuses it, so the two can run minutes and commits apart. `TAG=<sha> deploy/cloudrun.sh deploy` re-deploys any image already in the registry.

The service URL: `https://parity-u7lcbbxuia-uc.a.run.app` (project parity-hackathon-2026). Runs, decisions and screenshots live in the bucket, so they survive a
redeploy; the SQLite index and the model-response cache are rebuilt in `/tmp`. Boot reads each bundle once and evicts the oldest
Replay copies beyond `PARITY_REPLAY_KEEP` (default 20), except copies younger than `PARITY_REPLAY_MIN_AGE_S` (default two hours): a judge
still reviewing a finished Replay never loses it to other judges' clicks. A redeploy sends SIGTERM; the app cancels runs in flight and
records them as failed within Cloud Run's 10 s.

## Teardown
`deploy/cloudrun.sh teardown` deletes the service, the image repo, the bucket (all runs), the secret and the service account.

## Cost
A warm 2-CPU / 2 GiB instance is the cost that matters (a few dollars a day while judging); storage and operations are cents.
Set a budget alert in the Console if you leave it up.

## Continuous deployment (since 2 Nov)

Every push to `main` that changes the app redeploys the hosted demo once both CI suites pass: the `deploy` job in
`.github/workflows/ci.yml` runs `deploy/cloudrun.sh build && deploy/cloudrun.sh deploy`, the same two commands as a manual
redeploy. Docs-only pushes (`docs/`, `*.md`, `.superpowers/`, `.github/`) build nothing. A manual run of the workflow
(`gh workflow run ci.yml --ref main`, or the Actions tab → ci → Run workflow) deploys `main` as a push would.

How it authenticates: GitHub's OIDC token is exchanged through Workload Identity Federation for the service account
`parity-deployer@parity-hackathon-2026.iam.gserviceaccount.com` (pool `github`, provider `github`, trusted only for the repository
`TaahirSuleman/parity`). No key is stored in GitHub or in the repo. The deployer holds `run.admin`, `cloudbuild.builds.editor`, `viewer`,
`serviceusage.serviceUsageConsumer`, `iam.serviceAccountUser` on `parity-run` (the runtime account) and `storage.objectAdmin` on the
Cloud Build staging bucket. The secret's value is still added only by hand (`deploy/cloudrun.sh secret`); the deploy references it by name.

## Finding the project in the console

The project is `parity-hackathon-2026` (number 565679729433) and it belongs to the Google account `gcloud` is signed in as
(`gcloud auth list` shows it). The console shows only the projects of the account it is signed in with: if the project picker does not list
it, switch the console to that account, or grant another account access with
`gcloud projects add-iam-policy-binding parity-hackathon-2026 --member user:<email> --role roles/owner`. Direct links (append `?project=parity-hackathon-2026`):
the Cloud Run service `parity` in `us-central1` at `https://console.cloud.google.com/run/detail/us-central1/parity/revisions`; Cloud Build history at
`https://console.cloud.google.com/cloud-build/builds`; the run bundles bucket at `https://console.cloud.google.com/storage/browser/parity-hackathon-2026-parity-runs`;
the secret at `https://console.cloud.google.com/security/secret-manager/secret/parity-model-api-key`. "GCS" is only the bucket; the service lives under Cloud Run.
