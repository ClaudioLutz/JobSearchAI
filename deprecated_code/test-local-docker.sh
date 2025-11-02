#!/bin/bash
# Local Docker test script for JobSearchAI with Xvfb support
# Tests the Docker container locally before deployment

set -e  # Exit on any error

# Configuration
IMAGE_NAME="jobsearchai-scraper:local"
CONTAINER_NAME="jobsearchai-test"
LOCAL_PORT="5000"

echo "=========================================="
echo "JobSearchAI Local Docker Test Script"
echo "=========================================="
echo "Image: ${IMAGE_NAME}"
echo "Container: ${CONTAINER_NAME}"
echo "Port: ${LOCAL_PORT}"
echo ""

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed."
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Stop and remove existing container if it exists
echo "🧹 Cleaning up existing containers..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

# Build the Docker image
echo "🏗️  Building Docker image locally..."
docker build -t ${IMAGE_NAME} .

# Run the container
echo "🚀 Starting container..."
docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${LOCAL_PORT}:5000 \
    -e DISPLAY=:99 \
    --shm-size=2g \
    ${IMAGE_NAME}

echo "⏳ Waiting for container to start..."
sleep 10

# Test health check
echo "🏥 Testing health check endpoint..."
if curl -f http://localhost:${LOCAL_PORT}/health; then
    echo ""
    echo "✅ Health check passed!"
else
    echo ""
    echo "❌ Health check failed!"
    echo "Container logs:"
    docker logs ${CONTAINER_NAME}
    exit 1
fi

echo ""
echo "🎯 Testing home endpoint..."
curl -s http://localhost:${LOCAL_PORT}/ | python -m json.tool

echo ""
echo "📊 Container status:"
docker ps --filter name=${CONTAINER_NAME}

echo ""
echo "📋 Container logs (last 20 lines):"
docker logs --tail 20 ${CONTAINER_NAME}

echo ""
echo "✅ Local Docker test completed successfully!"
echo "=========================================="
echo "Container is running at: http://localhost:${LOCAL_PORT}"
echo "Health Check: http://localhost:${LOCAL_PORT}/health"
echo "API endpoint: http://localhost:${LOCAL_PORT}/scrape (POST)"
echo ""
echo "Test commands:"
echo "curl http://localhost:${LOCAL_PORT}/health"
echo "curl -X POST http://localhost:${LOCAL_PORT}/scrape"
echo ""
echo "To see live logs:"
echo "docker logs -f ${CONTAINER_NAME}"
echo ""
echo "To stop the container:"
echo "docker stop ${CONTAINER_NAME}"
echo ""
echo "To access container shell for debugging:"
echo "docker exec -it ${CONTAINER_NAME} /bin/bash"
echo "=========================================="
