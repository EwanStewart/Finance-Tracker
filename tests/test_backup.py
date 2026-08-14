import sqlite3

from app.db import connect, insert_account
from app.projections import Account
from scripts.backup_db import backup_database, prune_backups


def _populated_db(path):
    conn = connect(path)
    insert_account(conn, Account(name="Cash ISA", balance_pence=1234))
    conn.close()


def test_backup_database_writes_a_readable_copy(tmp_path):
    db = tmp_path / "finance.db"
    _populated_db(db)
    backups = tmp_path / "backups"

    target = backup_database(db, backups, stamp="2026-08-14T0230")

    assert target == backups / "finance-2026-08-14T0230.db"
    rows = sqlite3.connect(target).execute("SELECT name FROM accounts").fetchall()
    assert rows == [("Cash ISA",)]


def test_prune_backups_keeps_only_the_newest(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    stamps = [f"2026-08-{day:02d}T0230" for day in range(1, 6)]
    for stamp in stamps:
        (backups / f"finance-{stamp}.db").write_text("x")

    removed = prune_backups(backups, keep=2)

    kept = sorted(p.name for p in backups.glob("finance-*.db"))
    assert kept == ["finance-2026-08-04T0230.db", "finance-2026-08-05T0230.db"]
    assert len(removed) == 3
