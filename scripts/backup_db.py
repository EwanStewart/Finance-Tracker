"""Back up the SQLite database and keep the most recent copies.

Driven by finance-tracker-backup.timer on the Pi; safe to run by hand.

The Pi's SD card is the only home of every snapshot and balance, so set
BACKUP_REMOTE to an rsync target on another machine. Without it the copies
sit on the same card and a card failure still loses the lot.
"""

import datetime
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "finance.db"
DEFAULT_BACKUP_DIR = Path.home() / "finance-backups"
KEEP = 30


def backup_database(db_path: Path, backup_dir: Path, stamp: str) -> Path:
    """Copy the database with SQLite's own backup, which is safe mid-write."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"finance-{stamp}.db"
    source = sqlite3.connect(str(db_path))
    try:
        destination = sqlite3.connect(str(target))
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()
    return target


def prune_backups(backup_dir: Path, keep: int = KEEP) -> list[Path]:
    backups = sorted(Path(backup_dir).glob("finance-*.db"))
    stale = backups[: max(0, len(backups) - keep)]
    for path in stale:
        path.unlink()
    return stale


def mirror(backup_dir: Path, remote: str) -> None:
    subprocess.run(
        ["rsync", "--archive", "--delete", f"{backup_dir}/", remote], check=True
    )


def main() -> int:
    backup_dir = Path(os.environ.get("BACKUP_DIR", DEFAULT_BACKUP_DIR))
    remote = os.environ.get("BACKUP_REMOTE", "")
    stamp = datetime.datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%dT%H%M")
    target = backup_database(DEFAULT_DB_PATH, backup_dir, stamp)
    print(f"Wrote {target}")
    for removed in prune_backups(backup_dir):
        print(f"Removed {removed}")
    if remote:
        mirror(backup_dir, remote)
        print(f"Mirrored to {remote}")
    else:
        print(
            "BACKUP_REMOTE is unset; copies stay on this device only", file=sys.stderr
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
