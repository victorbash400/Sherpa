#!/usr/bin/env bash

set -euo pipefail

project_id="${GOOGLE_CLOUD_PROJECT:-sherpa-20260813}"
region="${SHERPA_RELAY_REGION:-africa-south1}"
repository="${SHERPA_ARTIFACT_REPOSITORY:-sherpa}"
service_account="${SHERPA_RELAY_SERVICE_ACCOUNT:-sherpa-relay@$project_id.iam.gserviceaccount.com}"

build_id=$(gcloud builds submit \
  --config infra/cloudbuild.relay.yaml \
  --project "$project_id" \
  --format='value(id)' \
  .)
image="$region-docker.pkg.dev/$project_id/$repository/relay:$build_id"

gcloud run deploy sherpa-relay \
  --project "$project_id" \
  --region "$region" \
  --image "$image" \
  --service-account "$service_account" \
  --set-secrets SHERPA_INTERNAL_SECRET=sherpa-internal-secret:latest \
  --set-env-vars SHERPA_TOOL_TIMEOUT_SECONDS=900 \
  --min-instances 1 \
  --max-instances 1 \
  --concurrency 80 \
  --timeout 3600 \
  --no-cpu-throttling \
  --allow-unauthenticated \
  --quiet
