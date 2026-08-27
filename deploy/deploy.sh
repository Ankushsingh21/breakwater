#!/usr/bin/env bash
set -e
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE="breakwater"

gcloud services enable run.googleapis.com pubsub.googleapis.com firestore.googleapis.com

gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE

gcloud run deploy $SERVICE \
  --image gcr.io/$PROJECT_ID/$SERVICE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars USE_LOCAL_STORE=false,GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest

gcloud pubsub topics create breakwater-trigger || true
SERVICE_URL=$(gcloud run services describe $SERVICE --region $REGION --format 'value(status.url)')
gcloud pubsub subscriptions create breakwater-sub \
  --topic breakwater-trigger \
  --push-endpoint="$SERVICE_URL/reconcile" || true

echo "Deployed: $SERVICE_URL"
