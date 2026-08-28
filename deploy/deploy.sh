#!/usr/bin/env bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE="breakwater"
REPO_NAME="breakwater-repo"
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE}"

echo "Deploying Breakwater to project: $PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com

gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Breakwater Docker Repository" || true

PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUM}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/aiplatform.user" || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/datastore.user" || true

# Build without cache to force pip to pick up requirements.txt changes
gcloud builds submit --tag $IMAGE_URL 

# Deploy with 5-minute timeout and the correct Gemeni/Gemma model strings
gcloud run deploy $SERVICE \
  --image $IMAGE_URL \
  --region $REGION \
  --platform managed \
  --timeout=300 \
  --allow-unauthenticated \
  --set-env-vars USE_LOCAL_STORE=false,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GEMINI_MODEL=gemini-3.5-flash,GEMMA_MODEL=gemma-4-26b-a4b-it-maas

gcloud pubsub topics create breakwater-trigger || true

SERVICE_URL=$(gcloud run services describe $SERVICE --region $REGION --format 'value(status.url)')

# Route Pub/Sub messages directly to the new push endpoint
gcloud pubsub subscriptions create breakwater-sub \
  --topic breakwater-trigger \
  --push-endpoint="$SERVICE_URL/process_break" \
  --ack-deadline=300 || true

echo "Deployed successfully at: $SERVICE_URL"
