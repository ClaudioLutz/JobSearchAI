#!/bin/bash
# Deployment script for JobSearchAI Scraper Service to Google Cloud Run
# This script builds and deploys the Docker container for the web scraping service

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"healthy-coil-466105-d7"}
SERVICE_NAME="jobsearchai-scraper"
REGION=${GOOGLE_CLOUD_REGION:-"europe-west6"}  # Zurich region - optimal for Switzerland
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "JobSearchAI Scraper Deployment Script"
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

# Build the Docker image using the job-data-acquisition Dockerfile
echo "🏗️  Building Docker image..."
echo "Building JobSearchAI Scraper with optimized Chromium configuration..."
docker build -f job-data-acquisition/Dockerfile -t ${IMAGE_NAME} .

# Push to Google Container Registry
echo "📤 Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run with optimized settings for browser automation
echo "🚀 Deploying to Cloud Run..."

# Check if OPENAI_API_KEY is provided
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY environment variable not set."
    echo "   Scraping will not work without the OpenAI API key."
    echo "   You can set it after deployment using:"
    echo "   export OPENAI_API_KEY=your_key && gcloud run services update ${SERVICE_NAME} --region=${REGION} --set-env-vars OPENAI_API_KEY=\$OPENAI_API_KEY"
    echo ""
    
    gcloud run deploy ${SERVICE_NAME} \
        --image ${IMAGE_NAME} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated \
        --memory 4Gi \
        --cpu 2 \
        --concurrency 10 \
        --timeout 600 \
        --max-instances 5 \
        --port 8080 \
        --set-env-vars FLASK_ENV=production,DISPLAY=:99
else
    echo "✅ OPENAI_API_KEY found - deploying with API key configured"
    
    gcloud run deploy ${SERVICE_NAME} \
        --image ${IMAGE_NAME} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated \
        --memory 4Gi \
        --cpu 2 \
        --concurrency 10 \
        --timeout 600 \
        --max-instances 5 \
        --port 8080 \
        --set-env-vars FLASK_ENV=production,DISPLAY=:99,OPENAI_API_KEY="${OPENAI_API_KEY}"
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format 'value(status.url)')

echo ""
echo "✅ Deployment completed successfully!"
echo "=========================================="
echo "Scraper Service URL: ${SERVICE_URL}"
echo "Health Check: ${SERVICE_URL}/health"
echo "Scrape Endpoint: ${SERVICE_URL}/scrape (POST)"
echo ""
echo "Configuration Details:"
echo "- Memory: 4 GiB (optimized for browser automation)"
echo "- CPU: 2 vCPU"
echo "- Concurrency: 10 (limited for browser instances)"
echo "- Timeout: 600s (10 minutes for complex scraping)"
echo "- Port: 8080"
echo "- Max Instances: 5 (resource management)"
echo ""
echo "Test the deployment:"
echo "curl ${SERVICE_URL}/health"
echo "curl -X POST ${SERVICE_URL}/scrape"
echo "=========================================="
