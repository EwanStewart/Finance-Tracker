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

### One-off bootstrap

On the Pi, install dependencies and prepare the SSH deploy key:

```
apt update && apt install -y python3 python3-venv python3-pip git nginx avahi-daemon
sudo -u dietpi ssh-keygen -t ed25519 -N "" -f /home/dietpi/.ssh/id_finance_tracker -C "fipi-deploy"
cat /home/dietpi/.ssh/id_finance_tracker.pub
```

Add the printed public key as a **read-only deploy key** on the GitHub repo.

Configure SSH on the Pi to use that key:

```
cat >> /home/dietpi/.ssh/config <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile /home/dietpi/.ssh/id_finance_tracker
    IdentitiesOnly yes
EOF
chown dietpi:dietpi /home/dietpi/.ssh/config && chmod 600 /home/dietpi/.ssh/config
```

Clone, install, and start:

```
install -d -o dietpi -g dietpi /opt
sudo -u dietpi git clone git@github.com:EwanStewart/Finance-Tracker.git /tmp/ft-clone
mv /tmp/ft-clone /opt/finance-tracker
chown -R dietpi:dietpi /opt/finance-tracker
sudo -u dietpi python3 -m venv /opt/finance-tracker/.venv
sudo -u dietpi /opt/finance-tracker/.venv/bin/pip install -r /opt/finance-tracker/requirements.txt

cp /opt/finance-tracker/deploy/finance-tracker.service /etc/systemd/system/
cp /opt/finance-tracker/deploy/nginx-finance-tracker.conf /etc/nginx/sites-available/finance-tracker
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/finance-tracker /etc/nginx/sites-enabled/finance-tracker

systemctl daemon-reload
systemctl enable --now finance-tracker
systemctl reload nginx
```

Copy the seeded database from the workstation (one-off):

```
scp data/finance.db root@fipi:/tmp/finance.db
ssh root@fipi 'install -d -o dietpi -g dietpi /opt/finance-tracker/data && mv /tmp/finance.db /opt/finance-tracker/data/ && chown dietpi:dietpi /opt/finance-tracker/data/finance.db && systemctl restart finance-tracker'
```

The service is reachable at http://fipi.

### Updating

```
ssh root@fipi /opt/finance-tracker/deploy/update.sh
```

That pulls the latest commit, refreshes dependencies, and restarts the service.
