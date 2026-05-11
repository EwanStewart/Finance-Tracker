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
