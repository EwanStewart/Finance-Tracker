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

## Deploy to a Raspberry Pi (DietPi)

On the Pi, install Python and avahi (one-off):

```
apt update && apt install -y python3 python3-venv python3-pip avahi-daemon
install -d -o dietpi -g dietpi /opt/finance-tracker/data
```

From the workstation, sync code, copy the seeded database, install the systemd unit:

```
rsync -av --delete --exclude __pycache__ --exclude .venv --exclude data \
    app/ root@fipi:/opt/finance-tracker/app/
rsync -av requirements.txt root@fipi:/opt/finance-tracker/
scp data/finance.db root@fipi:/opt/finance-tracker/data/finance.db
scp deploy/finance-tracker.service root@fipi:/etc/systemd/system/
```

On the Pi:

```
chown -R dietpi:dietpi /opt/finance-tracker
sudo -u dietpi python3 -m venv /opt/finance-tracker/.venv
sudo -u dietpi /opt/finance-tracker/.venv/bin/pip install -r /opt/finance-tracker/requirements.txt
systemctl daemon-reload
systemctl enable --now finance-tracker.service
```

The service listens on port 8000: http://fipi:8000.
