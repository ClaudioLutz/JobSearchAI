# Production Docker configuration for JobSearchAI Job Scraper Service
FROM python:3.10-slim

# Install system dependencies for Playwright + Chromium in containers
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    xvfb \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-color-emoji \
    fonts-unifont \
    ca-certificates \
    gnupg \
    lsb-release \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
COPY job-data-acquisition/dependencies.txt /app/job-data-acquisition/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r job-data-acquisition/dependencies.txt

# Install ScrapeGraphAI and related packages
RUN pip install scrapegraphai playwright beautifulsoup4

# Install Playwright browsers (skip system dependencies that cause issues)
RUN playwright install chromium --with-deps || playwright install chromium

# Copy application files
COPY config.py /app/
COPY job-data-acquisition/ /app/job-data-acquisition/

# Set environment variables
ENV DISPLAY=:99
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p /app/job-data-acquisition/logs /app/job-data-acquisition/data

# Expose port 8080 (Cloud Run will map this to the PORT environment variable)
EXPOSE 8080

# Health check (will work with any port the app starts on)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start with Xvfb and the scraper service
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -ac & sleep 2 && python job-data-acquisition/app.py"]
