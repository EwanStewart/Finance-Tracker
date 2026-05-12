# Finance-Tracker

Personal finance tracker. FastAPI + SQLite. Self-hosted on a Raspberry Pi Zero 2 W.

## Run locally

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000.

## Test

```
pytest
```

If `pytest` picks up unrelated packages from a sourced ROS environment, run:

```
PYTHONPATH= AMENT_PREFIX_PATH= pytest
```

## Format and lint

```
black app tests
pylint app tests
```

## Deploy to a Raspberry Pi

Runs as a systemd service under the `ewastewa` user, listening on port 8000. No reverse proxy. Set `PI_HOST` to whatever hostname or IP your Pi answers on (for example `photobox.local`).

### One-off bootstrap

Install system dependencies:

```
ssh "$PI_HOST" 'sudo apt update && sudo apt install -y python3 python3-venv python3-pip git'
```

Clone, build the virtualenv, and install Python dependencies:

```
ssh "$PI_HOST" '
  git clone git@github.com:EwanStewart/Finance-Tracker.git ~/finance-tracker &&
  python3 -m venv ~/finance-tracker/.venv &&
  ~/finance-tracker/.venv/bin/pip install -r ~/finance-tracker/requirements.txt &&
  mkdir -p ~/finance-tracker/data
'
```

If the Pi has no GitHub key, clone over HTTPS instead, or push a deploy key first.

Copy the seeded database from the workstation (one-off):

```
scp data/finance.db "$PI_HOST":finance-tracker/data/finance.db
```

Install and start the service:

```
ssh "$PI_HOST" '
  sudo cp ~/finance-tracker/deploy/finance-tracker.service /etc/systemd/system/ &&
  sudo systemctl daemon-reload &&
  sudo systemctl enable --now finance-tracker
'
```

The service is reachable at `http://$PI_HOST:8000`.

### Updating

```
ssh "$PI_HOST" finance-tracker/deploy/update.sh
```

That pulls the latest commit, refreshes dependencies, and restarts the service. Requires passwordless `sudo systemctl restart finance-tracker.service` for the `ewastewa` user.
