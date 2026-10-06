#!/bin/bash
set -euo pipefail

# Bootstrap the dedicated monitoring EC2 (Amazon Linux 2023 or Ubuntu).
if command -v dnf >/dev/null 2>&1; then
  dnf install -y docker
  systemctl enable --now docker
  docker_config=/usr/local/lib/docker
  mkdir -p "$docker_config/cli-plugins"
  curl -fsSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
    -o "$docker_config/cli-plugins/docker-compose"
  chmod +x "$docker_config/cli-plugins/docker-compose"
else
  apt-get update
  apt-get install -y docker.io docker-compose-plugin
  systemctl enable --now docker
fi

usermod -aG docker ec2-user 2>/dev/null || usermod -aG docker ubuntu 2>/dev/null || true
mkdir -p /opt/observability
