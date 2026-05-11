#!/bin/bash
# Pull latest code, refresh dependencies, restart the service.
# Run as root: sudo /opt/finance-tracker/deploy/update.sh

set -euo pipefail

cd /opt/finance-tracker

sudo -u dietpi git pull --ff-only
sudo -u dietpi .venv/bin/pip install --quiet --upgrade -r requirements.txt

systemctl restart finance-tracker

revision=$(sudo -u dietpi git rev-parse --short HEAD)
echo "Restarted finance-tracker at ${revision}"
