# Use a stable Python version (3.13 is recommended for 2026)
FROM python:3.13-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Install system dependencies
# - gosu: for user permission management
# - Pango & HarfBuzz: required for WeasyPrint
# - libpq-dev: required for robust PostgreSQL support
RUN apt-get update && apt-get install -y \
    gosu \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    fontconfig \
    fonts-liberation \
    fonts-dejavu-core \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Copy requirements and install Python dependencies
# We use --system so uv installs into the global python environment
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
# Ensure 'templates' is a sibling of 'resume_pipeline' in your backend folder
COPY resume_pipeline/ /app/resume_pipeline/
COPY templates/ /app/templates/

# Copy root Python scripts (worker.py, api.py, etc.)
COPY *.py /app/

# Create output directory (jobs dir is no longer needed with DB)
RUN mkdir -p /app/output

# Expose API port (Documentary only)
EXPOSE 8000

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Entrypoint handles user permission mapping (UID/GID)
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command (Overridden by docker-compose.yml)
CMD ["python", "api.py"]
