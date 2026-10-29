import os
import sqlite3
from collections.abc import Iterable
from typing import Self

from sandbox.ledger.model import Expense

SCHEMA = """
CREATE TABLE IF NOT EXISTS expense (
  id           INTEGER PRIMARY KEY,
  date         TEXT    NOT NULL CHECK (date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
  category     TEXT    NOT NULL CHECK (category <> ''),
  note         TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS expense_date ON expense (date);
CREATE TABLE IF NOT EXISTS budget (
  category     TEXT    PRIMARY KEY CHECK (category <> ''),
  amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0)
);
"""


class Store:
    def __init__(self, con: sqlite3.Connection):
        self.con = con

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def add(self, expenses: Iterable[Expense]) -> list[int]:
        ids = []
        with self.con:
            for e in expenses:
                cur = self.con.execute(
                    "INSERT INTO expense (date, amount_cents, category, note) VALUES (?, ?, ?, ?)",
                    (e.date, e.amount_cents, e.category, e.note),
                )
                ids.append(cur.lastrowid)
        return ids

    def expenses(self, month: str | None = None) -> list[Expense]:
        sql = "SELECT id, date, amount_cents, category, note FROM expense"
        params: tuple = ()
        if month is not None:
            sql += " WHERE date LIKE ?"
            params = (month + "-%",)
        rows = self.con.execute(sql + " ORDER BY date, id", params)
        return [Expense(d, a, c, n, id=i) for i, d, a, c, n in rows]

    def set_budget(self, category: str, amount_cents: int) -> None:
        with self.con:
            self.con.execute(
                "INSERT INTO budget (category, amount_cents) VALUES (?, ?) "
                "ON CONFLICT (category) DO UPDATE SET amount_cents = excluded.amount_cents",
                (category, amount_cents),
            )

    def budgets(self) -> dict[str, int]:
        rows = self.con.execute(
            "SELECT category, amount_cents FROM budget ORDER BY category"
        )
        return dict(rows.fetchall())

    def close(self) -> None:
        self.con.close()


def open_store(path: str | os.PathLike | None = None) -> Store:
    if path is None:
        path = os.environ.get("SANDBOX_LEDGER_DB") or "./ledger.db"
    con = sqlite3.connect(path, autocommit=False)
    try:
        with con:
            if con.execute("PRAGMA user_version").fetchone()[0] == 0:
                for stmt in SCHEMA.split(";"):
                    if stmt.strip():
                        con.execute(stmt)
                con.execute("PRAGMA user_version = 1")
    except BaseException:
        con.close()
        raise
    return Store(con)
