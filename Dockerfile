# Dockerfile for JobSearchAI Dashboard Web Application
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/instance \
    /app/process_cv/cv-data/input \
    /app/process_cv/cv-data/processed \
    /app/job-data-acquisition/data \
    /app/job_matches \
    /app/motivation_letters \
    /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=dashboard.py
ENV FLASK_ENV=production
ENV DATABASE_URL=sqlite:////app/instance/jobsearchai.db
ENV SECRET_KEY=your-secret-key-change-in-production
ENV OPENAI_API_KEY=""

# Expose port 8080 (Cloud Run will map this to PORT environment variable)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Initialize database and start dashboard
CMD ["sh", "-c", "python init_db.py create-tables && python init_db.py create-admin && python dashboard.py"]
