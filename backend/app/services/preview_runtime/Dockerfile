FROM node:22-bookworm-slim

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv build-essential \
    && rm -rf /var/lib/apt/lists/*

USER node
