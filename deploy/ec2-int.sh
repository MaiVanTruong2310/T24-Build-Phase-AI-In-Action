#!/bin/bash
set -euo pipefail

# Cài Docker + Compose plugin trên Amazon Linux 2023 / Ubuntu
if command -v dnf >/dev/null 2>&1; then
  dnf install -y docker
  systemctl enable --now docker
  DOCKER_CONFIG=/usr/local/lib/docker
  mkdir -p $DOCKER_CONFIG/cli-plugins
  curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
    -o $DOCKER_CONFIG/cli-plugins/docker-compose
  chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
else
  apt-get update
  apt-get install -y docker.io docker-compose-plugin
  systemctl enable --now docker
fi

usermod -aG docker ec2-user 2>/dev/null || usermod -aG docker ubuntu 2>/dev/null || true

mkdir -p /opt/app