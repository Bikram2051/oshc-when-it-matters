'''Persistent local accounting. Amounts are integer millionths of one USD.'''

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing, contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "data/private_runtime/llm_budget.sqlite"
MODEL = "claude-haiku-4-5-20251001"
LIMIT = 8_000_000
POLICY = json.dumps({"version": 1, "model": MODEL, "limit": LIMIT,
                     "input_rate": 1, "output_rate": 5}, sort_keys=True)


class BudgetError(RuntimeError):
    pass


class Budget:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else LEDGER_PATH

    def initialize(self):
        # Explicit setup only. Ordinary calls never recreate a missing ledger.
        if self.path.exists():
            return self.status()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db:
            db.executescript('''
                CREATE TABLE policy (value TEXT NOT NULL);
                CREATE TABLE calls (
                    id TEXT PRIMARY KEY, request_hash TEXT NOT NULL,
                    reserved INTEGER NOT NULL CHECK(reserved > 0),
                    actual INTEGER CHECK(actual >= 0),
                    input_tokens INTEGER, output_tokens INTEGER,
                    state TEXT NOT NULL DEFAULT 'reserved',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            db.execute("INSERT INTO policy VALUES (?)", (POLICY,))
            db.commit()
        return self.status()

    @contextmanager
    def _transaction(self):
        if not self.path.is_file():
            raise BudgetError("Spending ledger is missing. Do not reset an existing budget.")
        db = sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw",
                             uri=True, timeout=15, isolation_level=None)
        try:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT value FROM policy").fetchall()
            if rows != [(POLICY,)]:
                raise BudgetError("Spending policy changed. Review the ledger before proceeding.")
            yield db
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _used(db):
        return db.execute(
            "SELECT COALESCE(SUM(COALESCE(actual, reserved)), 0) FROM calls"
        ).fetchone()[0]

    def reserve(self, request_hash, amount):
        if type(amount) is not int or not 0 < amount <= 100_000:
            raise BudgetError("Request exceeds the USD 0.10 per-call reservation limit.")
        with self._transaction() as db:
            if db.execute("SELECT 1 FROM calls WHERE state='overrun' LIMIT 1").fetchone():
                raise BudgetError("A request exceeded its reservation. Review billing first.")
            if self._used(db) + amount > LIMIT:
                raise BudgetError("Local USD 8 allowance exhausted. No paid request was sent.")
            ticket = uuid.uuid4().hex
            db.execute("INSERT INTO calls(id, request_hash, reserved) VALUES (?, ?, ?)",
                       (ticket, request_hash, amount))
        return ticket

    def settle(self, ticket, input_tokens, output_tokens):
        if any(type(n) is not int or n < 0 for n in (input_tokens, output_tokens)):
            raise BudgetError("Invalid usage. The full reservation remains charged locally.")
        actual = input_tokens + 5 * output_tokens
        with self._transaction() as db:
            row = db.execute("SELECT reserved, actual FROM calls WHERE id=?", (ticket,)).fetchone()
            if row is None or row[1] is not None:
                raise BudgetError("Unknown or already settled request.")
            overrun = actual > row[0]
            db.execute("""UPDATE calls SET actual=?, input_tokens=?, output_tokens=?, state=?
                          WHERE id=?""",
                       (actual, input_tokens, output_tokens,
                        "overrun" if overrun else "settled", ticket))
        if overrun:
            raise BudgetError("Actual usage exceeded its reservation. Further paid calls are blocked.")

    def status(self):
        with self._transaction() as db:
            used = self._used(db)
            pending = db.execute("SELECT COUNT(*) FROM calls WHERE actual IS NULL").fetchone()[0]
            blocked = bool(db.execute("SELECT 1 FROM calls WHERE state='overrun' LIMIT 1").fetchone())
        return {"currency": "USD", "limit": LIMIT / 1_000_000,
                "spent_or_reserved": used / 1_000_000,
                "remaining": (LIMIT - used) / 1_000_000,
                "unsettled_calls": pending, "blocked_for_review": blocked}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("init", "status"))
    args = parser.parse_args()
    budget = Budget()
    print(json.dumps(budget.initialize() if args.action == "init" else budget.status(), indent=2))
