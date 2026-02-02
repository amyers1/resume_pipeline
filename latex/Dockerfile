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

WORKDIR /app

# Install Python dependencies for compilation service
COPY requirements.txt /tmp/
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r /tmp/requirements.txt

RUN mkdir -p /app/templates /tmp/latex-compile
RUN fc-cache -fv
RUN xelatex --version

# Run as non-root for security
RUN useradd -m -u 1000 latex && chown -R latex:latex /service /tmp/latex-compile
USER latex

CMD ["python3", "latex_service.py"]
