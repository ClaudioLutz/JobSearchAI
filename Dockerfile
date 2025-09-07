# Docker configuration for JobSearchAI with Xvfb virtual display support
# Enables headless=false mode in cloud environments for better extraction quality

FROM mcr.microsoft.com/playwright/python:v1.46.0

# Install Xvfb and fonts for better rendering and GUI support
RUN apt-get update && apt-get install -y \
    xvfb \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-dejavu-core \
    fonts-noto-cjk \
    fontconfig \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional Playwright dependencies if needed
RUN playwright install-deps

# Copy application code
COPY . .

# Set environment variables for virtual display
ENV DISPLAY=:99
ENV PORT=5000
ENV PYTHONPATH=/app
ENV FLASK_APP=dashboard.py
ENV FLASK_ENV=production

# Create necessary directories
RUN mkdir -p job-data-acquisition/logs job-data-acquisition/data \
    process_cv/cv-data/input process_cv/cv-data/processed \
    job_matches motivation_letters logs instance

# Initialize database with required tables and admin user
RUN python init_db.py create-tables && \
    python init_db.py create-admin admin admin@jobsearchai.local admin123

# Expose port for the dashboard application
EXPOSE 5000

# Health check endpoint for main dashboard
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start command with Xvfb virtual display running the full dashboard
# -screen 0 1920x1080x24: Set virtual display resolution
# -nolisten tcp: Disable TCP connections for security
# -ac: Disable access control (needed for container environment)
CMD xvfb-run -a -s "-screen 0 1920x1080x24 -nolisten tcp -ac" \
    python dashboard.py
