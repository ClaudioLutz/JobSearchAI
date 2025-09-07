# JobSearchAI Docker + Google Cloud Deployment Guide

## Overview

This guide provides complete instructions for deploying JobSearchAI with `headless=false` configuration using Docker and Google Cloud Platform. The solution uses Xvfb (X Virtual Framebuffer) to run headed browsers in containerized environments for optimal extraction quality.

## 🏗️ Architecture

**Local Development** → **Docker Container** → **Google Cloud Run/Compute Engine**

- **Browser Mode**: `headless=false` with Xvfb virtual display
- **Container**: Custom Docker image based on Microsoft Playwright
- **Virtual Display**: Xvfb running at `:99` (1920x1080x24)
- **API**: Flask REST API with health checks
- **Cloud Options**: Cloud Run (serverless) or Compute Engine (VM)

## 📋 Prerequisites

### Required Tools
- [Docker Desktop](https://docs.docker.com/get-docker/) 
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
- Google Cloud Project with billing enabled

### Required Permissions
- Cloud Run Admin
- Compute Engine Admin  
- Container Registry Admin
- Service Account User

## 🚀 Quick Start

### 1. Local Testing

Test the Docker container locally before deployment:

```bash
# Make scripts executable (if not already done)
chmod +x test-local-docker.sh deploy-cloud-run.sh deploy-compute-engine.sh

# Build and test locally
./test-local-docker.sh
```

This will:
- Build the Docker image with Xvfb support
- Start the container on port 8080
- Run health checks
- Display container logs

**Expected Output:**
```
✅ Health check passed!
Container is running at: http://localhost:8080
```

### 2. Cloud Run Deployment (Recommended)

Deploy to Google Cloud Run for serverless scaling:

```bash
# Set your project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Deploy to Cloud Run
./deploy-cloud-run.sh
```

**Configuration:**
- **Memory**: 4 GiB (for headed browser + Xvfb)
- **CPU**: 2 vCPU (optimal performance)
- **Concurrency**: 1 (Playwright requirement)
- **Timeout**: 15 minutes (long extraction jobs)

### 3. Compute Engine Deployment (Alternative)

For more control or if Cloud Run has limitations:

```bash
# Set your project ID and zone
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_ZONE="us-central1-a"

# Deploy to Compute Engine
./deploy-compute-engine.sh
```

## 📁 File Structure

```
JobSearchAI/
├── Dockerfile                    # Container definition with Xvfb
├── docker-compose.yml           # Local development setup
├── .dockerignore                # Docker build exclusions
├── cloudbuild.yaml              # Automated CI/CD builds
├── deploy-cloud-run.sh          # Cloud Run deployment script
├── deploy-compute-engine.sh     # Compute Engine deployment script  
├── test-local-docker.sh         # Local testing script
├── job-data-acquisition/
│   ├── app.py                   # Flask API with health checks
│   └── settings.json            # headless=false configuration
└── requirements.txt             # Python dependencies
```

## ⚙️ Configuration Details

### Browser Configuration (`settings.json`)

```json
{
    "scraper": {
        "headless": false,           // KEY: Use headed mode
        "wait_time": 3,             // Faster than headless
        "browser_config": {
            "args": [
                "--disable-dev-shm-usage",    // Memory optimization
                "--no-sandbox",               // Container requirement
                "--disable-setuid-sandbox",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows", 
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-blink-features=AutomationControlled"
            ],
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36...",
            "viewport": {"width": 1920, "height": 1080}
        },
        "timeout": 30000,
        "load_wait": "networkidle"
    }
}
```

### Docker Configuration

**Base Image**: `mcr.microsoft.com/playwright/python:v1.46.0-noble`

**Key Components**:
- Xvfb virtual display server
- Comprehensive font packages (Liberation, Noto, DejaVu)
- Optimized browser flags for containers
- Health check endpoints

**Environment Variables**:
- `DISPLAY=:99` (Xvfb display)
- `PORT=8080` (Flask server port)

## 🔧 API Endpoints

### Health Check
```bash
GET /health
```

**Response (Healthy)**:
```json
{
  "status": "healthy",
  "message": "JobSearchAI scraper is running",
  "display": ":99",
  "headless_mode": false,
  "timestamp": "2025-09-07T21:07:52.123Z"
}
```

### Trigger Scraping
```bash
POST /scrape
```

**Response**:
```json
{
  "status": "success", 
  "message": "Scraping completed",
  "output_file": "job-data-acquisition/data/job_data_20250907_210752.json",
  "timestamp": "2025-09-07T21:07:52.123Z"
}
```

### Service Information
```bash
GET /
```

## 🐳 Docker Commands

### Build Image
```bash
docker build -t jobsearchai-scraper:latest .
```

### Run Container
```bash
docker run -d \
  --name jobsearchai \
  -p 8080:8080 \
  -e DISPLAY=:99 \
  --shm-size=2g \
  jobsearchai-scraper:latest
```

### Debug Container
```bash
# Access shell
docker exec -it jobsearchai /bin/bash

# View logs
docker logs -f jobsearchai

# Check display
docker exec jobsearchai ps aux | grep Xvfb
```

## ☁️ Google Cloud Commands

### Cloud Run
```bash
# Deploy
gcloud run deploy jobsearchai-scraper \
  --image gcr.io/PROJECT-ID/jobsearchai-scraper \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --concurrency 1 \
  --timeout 900 \
  --max-instances 10

# View logs
gcloud run logs read jobsearchai-scraper --region us-central1
```

### Compute Engine
```bash
# SSH into instance
gcloud compute ssh jobsearchai-vm --zone us-central1-a

# Check service status
sudo systemctl status jobsearchai

# View logs
sudo journalctl -u jobsearchai -f
```

## 📊 Monitoring & Troubleshooting

### Health Monitoring
```bash
# Check if service is responding
curl https://YOUR-SERVICE-URL/health

# Test extraction
curl -X POST https://YOUR-SERVICE-URL/scrape
```

### Common Issues

**Issue**: `DISPLAY environment variable not set`
- **Solution**: Ensure Xvfb is running and DISPLAY=:99 is set

**Issue**: `Chrome crashes with insufficient memory`  
- **Solution**: Increase memory allocation to 4+ GB

**Issue**: `Permission denied errors`
- **Solution**: Check container user permissions and --no-sandbox flag

**Issue**: `Fonts not rendering correctly`
- **Solution**: Install additional font packages in Dockerfile

### Log Analysis

**Successful startup logs should show**:
```
Starting JobSearchAI Scraper API server on port 8080
Headless mode: false  
Display: :99
```

**Xvfb process should be running**:
```bash
ps aux | grep Xvfb
# Should show: Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -ac
```

## 🔒 Security Considerations

### Container Security
- Running with `--no-sandbox` (required for containers)
- Limited user permissions 
- No persistent data in containers
- Environment variables for sensitive config

### Network Security  
- HTTPS endpoints for production
- Firewall rules limiting access
- VPC networks for internal communication
- IAM roles with minimal permissions

### API Security
- Authentication via Cloud Run IAM (optional)
- Rate limiting for scraping endpoints
- Input validation and sanitization
- Secure headers and CORS policies

## 💰 Cost Optimization

### Cloud Run Pricing
- **CPU**: ~$0.0024 per vCPU/hour  
- **Memory**: ~$0.0025 per GB/hour
- **Requests**: $0.40 per million requests

**Estimated Cost**: $10-50/month for moderate usage

### Cost Reduction Tips
1. Use `min-instances=0` for auto-scaling to zero
2. Set appropriate timeout limits
3. Monitor usage patterns and adjust resources
4. Use regional deployments vs global

## 📈 Performance Optimization

### Resource Tuning
- **Memory**: 4GB minimum, 8GB for heavy workloads
- **CPU**: 2 vCPU optimal, 4 vCPU for concurrent requests
- **Disk**: SSD for faster startup times

### Browser Optimization
- Enable browser caching for static resources
- Use connection pooling for multiple requests
- Implement request queuing for high loads
- Cache frequently accessed pages

### Monitoring Metrics
- Response time percentiles (p50, p95, p99)
- Memory utilization over time
- CPU usage patterns  
- Error rates and success rates
- Container startup times

## 🔄 CI/CD Pipeline

### Automated Deployment with Cloud Build

The `cloudbuild.yaml` provides automated builds:

```yaml
# Triggered by git push
# Builds Docker image
# Pushes to Container Registry  
# Deploys to Cloud Run
```

**Setup**:
```bash
# Connect repository
gcloud builds triggers create github \
  --repo-name=JobSearchAI \
  --branch-pattern=main \
  --build-config=cloudbuild.yaml

# Manual trigger
gcloud builds submit --config=cloudbuild.yaml
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Docker installed and running
- [ ] Google Cloud CLI authenticated  
- [ ] Project billing enabled
- [ ] Required APIs enabled (Cloud Run, Compute Engine)
- [ ] Environment variables configured

### Local Testing
- [ ] `./test-local-docker.sh` passes
- [ ] Health check returns 200
- [ ] Scraping endpoint works
- [ ] Container logs show no errors

### Cloud Deployment  
- [ ] Cloud Run service deployed successfully
- [ ] External URL accessible 
- [ ] Health checks passing
- [ ] Scraping functionality verified
- [ ] Monitoring dashboards configured

### Production Readiness
- [ ] Load testing completed
- [ ] Error handling verified
- [ ] Logging and monitoring active
- [ ] Backup and recovery procedures
- [ ] Security review completed

## 🆘 Support & Troubleshooting

### Debug Commands
```bash
# Local container debugging
docker exec -it jobsearchai /bin/bash
ps aux | grep -E "(Xvfb|chrome|python)"

# Cloud Run logs
gcloud run logs read jobsearchai-scraper --region us-central1 --limit 50

# Health check debugging  
curl -v https://YOUR-SERVICE-URL/health
```

### Performance Testing
```bash
# Load test health endpoint
ab -n 100 -c 10 https://YOUR-SERVICE-URL/health

# Test scraping endpoint
curl -X POST https://YOUR-SERVICE-URL/scrape
```

### Common Solutions

**Problem**: Slow extraction times
- Increase CPU allocation
- Optimize browser configuration  
- Reduce wait times if possible

**Problem**: Memory issues
- Increase memory allocation to 4+ GB
- Add `--disable-dev-shm-usage` flag
- Monitor memory usage patterns

**Problem**: Display issues
- Verify Xvfb is running: `ps aux | grep Xvfb`
- Check DISPLAY environment variable
- Ensure font packages are installed

---

## 🎯 Next Steps

1. **Test locally** with `./test-local-docker.sh`
2. **Deploy to Cloud Run** with `./deploy-cloud-run.sh` 
3. **Verify functionality** with health and scrape endpoints
4. **Monitor performance** and adjust resources as needed
5. **Set up automated deployments** with Cloud Build

For additional support, check the logs and verify all configuration settings match this guide.
