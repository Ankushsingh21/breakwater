#!/usr/bin/env bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE="breakwater"
REPO_NAME="breakwater-repo"
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE}"

echo "Deploying Breakwater to project: $PROJECT_ID"

# 1. Enable required services (Removed Pub/Sub)
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com

# 2. Create Artifact Registry
gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Breakwater Docker Repository" || true

# 3. Apply IAM Permissions for Vertex AI and Firestore
PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUM}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/aiplatform.user" || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/datastore.user" || true

# 4. Build Docker Image
echo "Building image..."
gcloud builds submit --tag $IMAGE_URL 

# 5. Deploy to Cloud Run
#  --no-cpu-throttling is required so the Python ThreadPoolExecutor 
# can finish processing the background swarm after the FastAPI request returns 200 OK.
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE \
  --image $IMAGE_URL \
  --region $REGION \
  --platform managed \
  --timeout=300 \
  --no-cpu-throttling \
  --allow-unauthenticated \
  --set-env-vars USE_LOCAL_STORE=false,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GEMINI_MODEL=gemini-3.5-flash,GEMMA_MODEL=gemma-4-26b-a4b-it-maas,EMBEDDING_MODEL=text-embedding-005

SERVICE_URL=$(gcloud run services describe $SERVICE --region $REGION --format 'value(status.url)')

echo "================================================="
echo " Deployed successfully at: $SERVICE_URL"
echo "================================================="
