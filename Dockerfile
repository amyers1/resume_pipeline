FROM python:3.14-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Install system dependencies for WeasyPrint
# - gosu: for user permission management
# - Pango & HarfBuzz: required for WeasyPrint text rendering
# - fontconfig: font management
RUN apt-get update && apt-get install -y \
    gosu \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    fontconfig \
    fonts-liberation \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY resume_pipeline/ /app/resume_pipeline/

# Copy root Python scripts (monitor_jobs.py, submit_job.py, api.py, etc.)
COPY *.py /app/

# Copy templates directory (HTML, CSS, and LaTeX templates)
COPY templates/ /app/templates/

# Create output and jobs directories
RUN mkdir -p /app/output /app/jobs

# Expose API port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint to handle user/group permissions
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "resume_pipeline"]
