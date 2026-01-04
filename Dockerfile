FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
  build-essential \
  vim \
  libpq-dev \
  python3-dev \
  pkg-config \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ARG DOCKER_USER=django
RUN useradd -m $DOCKER_USER
WORKDIR /home/${DOCKER_USER}/app 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Prepare media & static directories
RUN mkdir -p /home/${DOCKER_USER}/app/media \
  && chown -R ${DOCKER_USER}:${DOCKER_USER} /home/${DOCKER_USER}/app/media

USER $DOCKER_USER
