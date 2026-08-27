#!/usr/bin/env bash
# Optional: makes Breakwater run autonomously on a schedule, not just on demand -
# this is what proves "runs in the background" for the demo video. Run this
# after deploy.sh has already created the breakwater-trigger Pub/Sub topic.
set -e
TOPIC="breakwater-trigger"

gcloud services enable cloudscheduler.googleapis.com

gcloud scheduler jobs create pubsub breakwater-hourly \
  --schedule="0 * * * *" \
  --topic=$TOPIC \
  --message-body="run" \
  --location=us-central1 || true

echo "Scheduler job created: Breakwater now runs automatically every hour."
