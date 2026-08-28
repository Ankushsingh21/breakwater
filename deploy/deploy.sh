#!/usr/bin/env bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE="breakwater"
REPO_NAME="breakwater-repo"
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE}"

echo "Deploying Breakwater to project: $PROJECT_ID"

# 1. Enable required APIs
gcloud services enable \
  run.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com

# 2. Create standard Artifact Registry repository if it doesn't exist
gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Breakwater Docker Repository" || true

# 3. Give default compute service account required roles
PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUM}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/aiplatform.user" || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/datastore.user" || true

# 4. Build container directly into Artifact Registry
gcloud builds submit --tag $IMAGE_URL

# 5. Deploy to Cloud Run
gcloud run deploy $SERVICE \
  --image $IMAGE_URL \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars USE_LOCAL_STORE=false,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GEMINI_MODEL=gemini-2.0-flash,GEMMA_MODEL=gemini-2.0-flash

# 6. Wire up Pub/Sub
gcloud pubsub topics create breakwater-trigger || true

SERVICE_URL=$(gcloud run services describe $SERVICE --region $REGION --format 'value(status.url)')

gcloud pubsub subscriptions create breakwater-sub \
  --topic breakwater-trigger \
  --push-endpoint="$SERVICE_URL/reconcile" || true

echo "Deployed successfully at: $SERVICE_URL"
