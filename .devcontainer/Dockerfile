FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

# Install Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install additional tools
RUN apt-get update && apt-get install -y \
    git \
    make \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Install Python dependencies
COPY shared/service-template/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Install pre-commit
RUN pip install pre-commit