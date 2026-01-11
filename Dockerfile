FROM python:3.14-slim

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
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY resume_pipeline/ /app/resume_pipeline/

# Copy templates directory (HTML, CSS, and LaTeX templates)
COPY templates/ /app/templates/

# Create output directory
RUN mkdir -p /app/output

# Set entrypoint to handle user/group permissions
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "resume_pipeline"]
