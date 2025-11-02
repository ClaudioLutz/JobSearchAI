#!/bin/bash
# Helper script to set the OPENAI_API_KEY environment variable in Cloud Run
# Usage: ./set-api-key.sh YOUR_OPENAI_API_KEY

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"healthy-coil-466105-d7"}
SERVICE_NAME="jobsearchai-dashboard"
REGION=${GOOGLE_CLOUD_REGION:-"europe-west6"}

# Check if API key is provided
if [ $# -eq 0 ]; then
    echo "❌ Error: Please provide your OpenAI API key as an argument"
    echo "Usage: $0 YOUR_OPENAI_API_KEY"
    echo ""
    echo "Example:"
    echo "$0 sk-1234567890abcdef..."
    exit 1
fi

API_KEY="$1"

# Validate API key format (basic check)
if [[ ! "$API_KEY" =~ ^sk-[A-Za-z0-9]{20,}$ ]]; then
    echo "⚠️  Warning: API key doesn't match expected format (sk-...)"
    echo "Continuing anyway..."
fi

echo "=========================================="
echo "Setting OpenAI API Key for JobSearchAI"
echo "=========================================="
echo "Project ID: ${PROJECT_ID}"
echo "Service Name: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo "API Key: ${API_KEY:0:10}..."
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed."
    echo "Please install gcloud: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set the project
echo "🔧 Setting Google Cloud project..."
gcloud config set project ${PROJECT_ID}

# Update the Cloud Run service with the API key
echo "🔑 Setting OPENAI_API_KEY environment variable..."
gcloud run services update ${SERVICE_NAME} \
    --region ${REGION} \
    --set-env-vars OPENAI_API_KEY="${API_KEY}"

echo ""
echo "✅ OPENAI_API_KEY has been set successfully!"
echo ""
echo "The CV processing should now work in the web interface."
echo "Try uploading a CV file to test the functionality."
echo ""
echo "Service URL: https://jobsearchai-dashboard-l5bgmlkx4q-oa.a.run.app"
echo "=========================================="
