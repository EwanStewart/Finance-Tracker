#!/bin/bash
# Fetch from origin and redeploy only if there's something new.
# Driven by the self-hosted Actions runner on the Pi; safe to call manually
# over ssh. The run holds a lock so two triggers cannot interleave a reset
# and a reinstall.

set -euo pipefail

REPO=/home/ewastewa/finance-tracker
BRANCH=main
HEALTH_URL=http://127.0.0.1:8000/health
HEALTH_TIMEOUT=20

exec 9>/tmp/finance-tracker-deploy.lock
flock 9

cd "$REPO"

if ! git diff-index --quiet HEAD --; then
    echo "Working tree has uncommitted changes in $REPO; refusing to deploy" >&2
    exit 1
fi

git fetch --quiet origin "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0
fi

echo "Updating finance-tracker: ${LOCAL:0:7} -> ${REMOTE:0:7}"
git reset --hard "origin/$BRANCH"
.venv/bin/pip install --quiet -r requirements.txt
sudo -n /bin/systemctl restart finance-tracker.service

# systemctl returns as soon as the process starts, so a crash loop would
# otherwise look like a clean deploy. Wait for the app to answer.
for _ in $(seq "$HEALTH_TIMEOUT"); do
    if curl -fsS --max-time 2 "$HEALTH_URL" > /dev/null; then
        echo "Restarted finance-tracker at $(git rev-parse --short HEAD)"
        exit 0
    fi
    sleep 1
done

echo "finance-tracker did not answer $HEALTH_URL within ${HEALTH_TIMEOUT}s" >&2
systemctl status finance-tracker.service --no-pager --lines 20 >&2 || true
exit 1
