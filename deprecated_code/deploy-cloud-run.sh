#!/bin/bash
# Deployment script for JobSearchAI Dashboard to Google Cloud Run
# This script builds and deploys the Docker container for the web dashboard

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"healthy-coil-466105-d7"}  # Updated with actual project ID
SERVICE_NAME="jobsearchai-dashboard"
REGION=${GOOGLE_CLOUD_REGION:-"europe-west6"}  # Zurich region - optimal for Switzerland
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "JobSearchAI Dashboard Deployment Script"
echo "=========================================="
echo "Project ID: ${PROJECT_ID}"
echo "Service Name: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo "Image: ${IMAGE_NAME}"
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed."
    echo "Please install gcloud: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed."
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 &> /dev/null; then
    echo "❌ Error: Not authenticated with gcloud."
    echo "Please run: gcloud auth login"
    exit 1
fi

# Set the project
echo "🔧 Setting Google Cloud project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build the Docker image
echo "🏗️  Building Docker image..."
echo "Building JobSearchAI Dashboard..."
docker build -t ${IMAGE_NAME} .

# Push to Google Container Registry
echo "📤 Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."

# Check if OPENAI_API_KEY is provided
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY environment variable not set."
    echo "   CV summarization will not work without the OpenAI API key."
    echo "   You can set it after deployment using:"
    echo "   export OPENAI_API_KEY=your_key && ./set-api-key.sh \$OPENAI_API_KEY"
    echo ""
    
    gcloud run deploy ${SERVICE_NAME} \
        --image ${IMAGE_NAME} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --concurrency 50 \
        --timeout 300 \
        --max-instances 10 \
        --port 8080 \
        --set-env-vars FLASK_ENV=production,DATABASE_URL=sqlite:////app/instance/jobsearchai.db
else
    echo "✅ OPENAI_API_KEY found - deploying with API key configured"
    
    gcloud run deploy ${SERVICE_NAME} \
        --image ${IMAGE_NAME} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --concurrency 50 \
        --timeout 300 \
        --max-instances 10 \
        --port 8080 \
        --set-env-vars FLASK_ENV=production,DATABASE_URL=sqlite:////app/instance/jobsearchai.db,OPENAI_API_KEY="${OPENAI_API_KEY}"
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format 'value(status.url)')

echo ""
echo "✅ Deployment completed successfully!"
echo "=========================================="
echo "Dashboard URL: ${SERVICE_URL}"
echo "Login URL: ${SERVICE_URL}/login"
echo ""
echo "Default Admin Credentials:"
echo "Username: admin"
echo "Password: admin123"
echo ""
echo "IMPORTANT: Change the admin password after first login!"
echo ""
echo "Configuration Details:"
echo "- Memory: 2 GiB"
echo "- CPU: 2 vCPU"
echo "- Concurrency: 50 (web dashboard)"
echo "- Timeout: 300s (5 minutes)"
echo "- Port: 8080"
echo "=========================================="
