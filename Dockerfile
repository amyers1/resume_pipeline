FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including gosu, LaTeX, and fonts
RUN apt-get update && apt-get install -y \
    gosu \
    texlive-xetex \
    texlive-latex-extra \
    texlive-fonts-recommended \
    fonts-roboto \
    fonts-font-awesome \
    fontconfig \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy resume_pipeline package
COPY resume_pipeline/ /app/resume_pipeline/

# Copy templates directory
COPY templates/ /app/templates/

# Copy fonts directory if it exists (optional)
COPY fonts* /app/fonts/

# Create output directory
RUN mkdir -p /app/output

# Set entrypoint to handle user/group permissions
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "resume_pipeline"]
