#!/usr/bin/env bash
set -e
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE="breakwater"

# 1. Enable required APIs
gcloud services enable run.googleapis.com pubsub.googleapis.com firestore.googleapis.com aiplatform.googleapis.com

# 2. Give the default compute service account access to Vertex AI (Gemini) and Datastore (Firestore)
PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUM}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${COMPUTE_SA}" --role="roles/aiplatform.user" || true
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${COMPUTE_SA}" --role="roles/datastore.user" || true

# 3. Build the container
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE

# 4. Deploy to Cloud Run (Note: USE_LOCAL_STORE is false, activating Firestore)
gcloud run deploy $SERVICE \
  --image gcr.io/$PROJECT_ID/$SERVICE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars USE_LOCAL_STORE=false,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GEMINI_MODEL=gemini-1.5-flash

# 5. Wire up Pub/Sub
gcloud pubsub topics create breakwater-trigger || true
SERVICE_URL=$(gcloud run services describe $SERVICE --region $REGION --format 'value(status.url)')
gcloud pubsub subscriptions create breakwater-sub \
  --topic breakwater-trigger \
  --push-endpoint="$SERVICE_URL/reconcile" || true

echo "Deployed successfully at: $SERVICE_URL"