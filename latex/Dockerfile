FROM ubuntu:24.04

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

WORKDIR /app

# Install Python dependencies for compilation service
COPY requirements.txt /tmp/
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r /tmp/requirements.txt



# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD xelatex --version || exit 1

CMD ["python3", "latex_service.py"]
