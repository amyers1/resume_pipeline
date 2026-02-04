FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install LaTeX distribution
RUN apt-get update && apt-get install -y \
    texlive-xetex \
    texlive-latex-extra \
    texlive-fonts-extra \
    texlive-science \
    python3 \
    python3-pip \
    curl \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /service

# Install Python dependencies for compilation service
COPY ./service/requirements.txt /tmp/
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r /tmp/requirements.txt

# Copy application code
COPY ./service .

# Create runtime directories
RUN mkdir -p /workspace/templates /tmp/latex-compile

# Update font cache
RUN fc-cache -fv

# Verify LaTeX installation
RUN xelatex --version

# Create non-root user with UID 1001
RUN if ! id -u 1001 >/dev/null 2>&1; then \
        groupadd -g 1001 latex && \
        useradd -m -u 1001 -g latex latex; \
    fi

# Set ownership
RUN chown -R 1001:1001 /service /workspace /tmp/latex-compile

# Switch to non-root user
USER 1001

CMD ["python3", "run.py"]
