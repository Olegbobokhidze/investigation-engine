#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu LTS (24.04 or newer) EC2 instance: paste into "User data"
# when launching it, or run once over SSH with sudo. Installs Docker and the app directory;
# deploys come from .github/workflows/deploy-api.yml.
set -euo pipefail

apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# The deploy job logs in as `ubuntu`; the docker group lets it run docker without sudo.
usermod -aG docker ubuntu
install -d -o ubuntu -g ubuntu -m 0700 /opt/investigation-engine
