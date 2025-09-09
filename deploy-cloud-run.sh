#!/bin/bash
# Deployment script for JobSearchAI to Google Cloud Run with Xvfb support
# This script builds and deploys the Docker container with headless=false configuration

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"healthy-coil-466105-d7"}  # Updated with actual project ID
SERVICE_NAME="jobsearchai-scraper"
REGION=${GOOGLE_CLOUD_REGION:-"europe-west6"}  # Zurich region - optimal for Switzerland
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "JobSearchAI Cloud Run Deployment Script"
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
echo "Building with headless=false for better quality extraction..."
docker build -t ${IMAGE_NAME} .

# Push to Google Container Registry
echo "📤 Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --concurrency 1 \
    --timeout 900 \
    --max-instances 10 \
    --set-env-vars="DISPLAY=:99" \
    --port 5000

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format 'value(status.url)')

echo ""
echo "✅ Deployment completed successfully!"
echo "=========================================="
echo "Service URL: ${SERVICE_URL}"
echo "Health Check: ${SERVICE_URL}/health"
echo "Scrape API: ${SERVICE_URL}/scrape (POST)"
echo ""
echo "Test the deployment:"
echo "curl ${SERVICE_URL}/health"
echo ""
echo "To trigger scraping:"
echo "curl -X POST ${SERVICE_URL}/scrape"
echo ""
echo "Configuration Details:"
echo "- Memory: 4 GiB (for headed browser + Xvfb)"
echo "- CPU: 2 vCPU (for better performance)"
echo "- Concurrency: 1 (recommended for Playwright)"
echo "- Timeout: 900s (15 minutes for complex scraping)"
echo "- Headless Mode: false (with Xvfb virtual display)"
echo "=========================================="
