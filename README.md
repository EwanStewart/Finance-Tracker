# Finance-Tracker

Personal net wealth dashboard. FastAPI + SQLite. Self-hosted on a Raspberry Pi.

![Overview tab with projected net wealth chart](docs/overview.png)
![Accounts tab listing savings and credit cards](docs/accounts.png)
![Expenses tab listing monthly and yearly outgoings](docs/expenses.png)
![History tab with snapshots over time](docs/history.png)

## What it does

The Overview tab shows today's net wealth and a chart projecting balance over the next five years. Headline cards summarise the projection at fixed horizons and at a custom date. A card at the bottom shows the latest Fidelity Index World Fund price with its daily change.

The fund price comes from the [public factsheet](https://www.fidelity.co.uk/factsheet-data/factsheet/GB00BJS8SJ34-fidelity-index-world-fund-p-acc/key-statistics). The server caches it in SQLite and refetches at most once per London day, on the first page load of that day. If Fidelity is unreachable, the card keeps showing the last known price and says the update failed.

Each savings account compounds at its own annual rate, plus whatever monthly allocation it is given. Anything left over from income after expenses and allocations is projected as cash at no interest, and the chart says how much that is. A credit card balance is always stored as debt, so a positive figure entered there is negated.

The Accounts tab manages savings and credit cards. The Income tab lists each source with its monthly amount. The Expenses tab splits monthly and yearly outgoings. The yearly table also shows each item's monthly equivalent.

The History tab plots net wealth against actual snapshots. Every write to accounts, income, or expenses captures a snapshot, with consecutive writes within 60 seconds debounced into one entry. A "Snapshot now" button takes a labelled manual capture that the debounce never replaces. A filter narrows the view to manual snapshots only, or to month-end snapshots only.

![History tab filtered to manual snapshots only](docs/history-manual.png)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000.

## Installing on a Pi

Set `PI_HOST` to your Pi's hostname or IP, then:

```bash
ssh "$PI_HOST" '
  sudo apt update && sudo apt install -y python3 python3-venv python3-pip git &&
  git clone git@github.com:EwanStewart/Finance-Tracker.git ~/finance-tracker &&
  python3 -m venv ~/finance-tracker/.venv &&
  ~/finance-tracker/.venv/bin/pip install -r ~/finance-tracker/requirements.txt &&
  mkdir -p ~/finance-tracker/data
'

scp data/finance.db "$PI_HOST":finance-tracker/data/finance.db

ssh "$PI_HOST" '
  sudo cp ~/finance-tracker/deploy/finance-tracker.service /etc/systemd/system/ &&
  sudo systemctl daemon-reload &&
  sudo systemctl enable --now finance-tracker
'
```

The service listens on `127.0.0.1:8000` only. Caddy puts it on the network and Avahi gives it a name:

```bash
ssh "$PI_HOST" '
  sudo apt install -y caddy avahi-utils &&
  sudo cp ~/finance-tracker/deploy/Caddyfile /etc/caddy/Caddyfile &&
  sudo systemctl restart caddy &&
  sudo cp ~/finance-tracker/deploy/mdns-alias@.service /etc/systemd/system/ &&
  sudo systemctl enable --now mdns-alias@finance
'
```

Open http://finance.local.

## Backups

The Pi's SD card holds the only copy of every balance and snapshot. A nightly timer takes a consistent copy with SQLite's own backup and keeps the last 30:

```bash
ssh "$PI_HOST" '
  sudo cp ~/finance-tracker/deploy/finance-tracker-backup.* /etc/systemd/system/ &&
  sudo systemctl daemon-reload &&
  sudo systemctl enable --now finance-tracker-backup.timer
'
```

Copies land in `~/finance-backups`. Set `BACKUP_REMOTE` in `finance-tracker-backup.service` to an rsync target on another machine, otherwise a dead card still loses everything. Restore by stopping the service, copying a backup over `data/finance.db`, and starting it again.

## Deploying a change

Pushing to `main` runs the tests, then a self-hosted Actions runner on the Pi runs `deploy/update.sh`, which pulls, reinstalls dependencies and restarts the service. The script waits for `/health` to answer and fails the job if it does not, so a crash loop shows up as a red run rather than a silently dead site.

Check the runner is up with `systemctl is-active actions.runner.*`. To deploy by hand:

```bash
ssh "$PI_HOST" bash ~/finance-tracker/deploy/update.sh
```

## Tests

```bash
python -m pytest -q
```
