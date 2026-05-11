#!/bin/bash
# Pull latest code, refresh dependencies, restart the service.
# Callable by the dietpi user (the GitHub Actions runner) or root.

set -euo pipefail

cd /opt/finance-tracker

git pull --ff-only
.venv/bin/pip install --quiet --upgrade -r requirements.txt
sudo -n /bin/systemctl restart finance-tracker.service

echo "Restarted finance-tracker at $(git rev-parse --short HEAD)"
