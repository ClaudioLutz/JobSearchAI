#!/bin/bash
# Compute Engine deployment script for JobSearchAI with full GUI support
# Fallback option if Cloud Run has issues with Xvfb

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}  # Replace with your actual project ID
INSTANCE_NAME="jobsearchai-vm"
ZONE=${GOOGLE_CLOUD_ZONE:-"us-central1-a"}  # Can be changed to europe-west1-b for EU
MACHINE_TYPE="e2-standard-2"  # 2 vCPU, 8 GB RAM
IMAGE_FAMILY="ubuntu-2004-lts"
IMAGE_PROJECT="ubuntu-os-cloud"

echo "=========================================="
echo "JobSearchAI Compute Engine Deployment"
echo "=========================================="
echo "Project ID: ${PROJECT_ID}"
echo "Instance Name: ${INSTANCE_NAME}"
echo "Zone: ${ZONE}"
echo "Machine Type: ${MACHINE_TYPE}"
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed."
    echo "Please install gcloud: https://cloud.google.com/sdk/docs/install"
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
gcloud services enable compute.googleapis.com

# Create startup script
echo "📝 Creating startup script..."
cat > startup-script.sh << 'EOF'
#!/bin/bash
# Startup script for JobSearchAI Compute Engine instance

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker $USER

# Install Xvfb and desktop environment for debugging (optional)
apt-get install -y xvfb xfce4 xfce4-goodies tightvncserver curl

# Install Docker Compose for easier management
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/jobsearchai
cd /opt/jobsearchai

# Create docker-compose.yml file
cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'
services:
  jobsearchai-scraper:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DISPLAY=:99
    volumes:
      - ./job-data-acquisition/data:/app/job-data-acquisition/data
      - ./job-data-acquisition/logs:/app/job-data-acquisition/logs
    restart: unless-stopped
    shm_size: 2g
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
COMPOSE_EOF

# Create systemd service for automatic startup
cat > /etc/systemd/system/jobsearchai.service << 'SERVICE_EOF'
[Unit]
Description=JobSearchAI Scraper Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/jobsearchai
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Enable the service
systemctl enable jobsearchai.service

# Log completion
echo "$(date): JobSearchAI VM setup completed" >> /var/log/startup-script.log
EOF

# Create the VM instance
echo "🚀 Creating Compute Engine instance..."
gcloud compute instances create ${INSTANCE_NAME} \
    --zone=${ZONE} \
    --machine-type=${MACHINE_TYPE} \
    --network-tier=PREMIUM \
    --maintenance-policy=MIGRATE \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=http-server,https-server \
    --image-family=${IMAGE_FAMILY} \
    --image-project=${IMAGE_PROJECT} \
    --boot-disk-size=50GB \
    --boot-disk-type=pd-ssd \
    --boot-disk-device-name=${INSTANCE_NAME} \
    --metadata-from-file startup-script=startup-script.sh

# Create firewall rule for HTTP traffic
echo "🔥 Creating firewall rule..."
gcloud compute firewall-rules create allow-jobsearchai-http \
    --allow tcp:8080 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server \
    --description "Allow HTTP traffic on port 8080 for JobSearchAI" || true

# Wait for instance to be ready
echo "⏳ Waiting for instance to start..."
sleep 30

# Get external IP
EXTERNAL_IP=$(gcloud compute instances describe ${INSTANCE_NAME} --zone=${ZONE} --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "✅ Compute Engine deployment initiated!"
echo "=========================================="
echo "Instance Name: ${INSTANCE_NAME}"
echo "External IP: ${EXTERNAL_IP}"
echo "Zone: ${ZONE}"
echo ""
echo "The instance is being set up with the startup script."
echo "This process may take 5-10 minutes to complete."
echo ""
echo "You can monitor the setup progress with:"
echo "gcloud compute ssh ${INSTANCE_NAME} --zone=${ZONE} --command='tail -f /var/log/startup-script.log'"
echo ""
echo "Once setup is complete, test the deployment:"
echo "curl http://${EXTERNAL_IP}:8080/health"
echo ""
echo "To copy your code to the instance:"
echo "gcloud compute scp --recurse . ${INSTANCE_NAME}:/opt/jobsearchai --zone=${ZONE}"
echo ""
echo "To SSH into the instance:"
echo "gcloud compute ssh ${INSTANCE_NAME} --zone=${ZONE}"
echo ""
echo "To start/stop the service:"
echo "sudo systemctl start jobsearchai"
echo "sudo systemctl stop jobsearchai"
echo "sudo systemctl status jobsearchai"
echo ""
echo "Configuration Details:"
echo "- Machine Type: ${MACHINE_TYPE} (2 vCPU, 8 GB RAM)"
echo "- OS: Ubuntu 20.04 LTS"
echo "- Docker with GUI support (Xvfb + optional VNC)"
echo "- Automatic startup on boot"
echo "- Headless Mode: false (full GUI capability)"
echo "=========================================="

# Clean up startup script
rm startup-script.sh
