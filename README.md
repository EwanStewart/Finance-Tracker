# Finance-Tracker

Personal net wealth dashboard. FastAPI + SQLite. Self-hosted on a Raspberry Pi.

![Overview tab with projected net wealth chart](docs/overview.png)
![Accounts tab listing savings and credit cards](docs/accounts.png)
![Expenses tab listing monthly and yearly outgoings](docs/expenses.png)

## What it does

The Overview tab shows today's net wealth and a chart projecting balance over the next five years. Headline cards summarise the projection at fixed horizons and at a custom date.

The Accounts tab manages savings and credit cards. The Income tab lists each source with its monthly amount. The Expenses tab splits monthly and yearly outgoings. The yearly table also shows each item's monthly equivalent.

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
