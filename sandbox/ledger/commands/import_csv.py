import csv
import io
from collections import Counter

from sandbox.ledger.model import CSV_COLUMNS, LedgerError, make_expense
from sandbox.ledger.store import Store

REQUIRED = ("date", "amount", "category")


def _is_blank(row: list[str]) -> bool:
    return not any(cell.strip() for cell in row)


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            return f.read()
    except UnicodeDecodeError:
        raise LedgerError(f"{path}: not UTF-8") from None
    except OSError as err:
        raise LedgerError(f"cannot read {path}: {err.strerror or err}") from None


def _header_index(path: str, header: list[str]) -> dict[str, int]:
    names = [h.strip().casefold() for h in header]
    index: dict[str, int] = {}
    for col in CSV_COLUMNS:
        positions = [i for i, n in enumerate(names) if n == col]
        if len(positions) > 1:
            raise LedgerError(f"{path} line 1: repeated column '{col}'")
        if positions:
            index[col] = positions[0]
        elif col in REQUIRED:
            raise LedgerError(f"{path} line 1: missing column '{col}'")
    return index


def import_expenses(store: Store, path: str) -> tuple[int, int]:
    reader = csv.reader(io.StringIO(_read_text(path), newline=""), strict=True)
    try:
        header = next((r for r in reader if not _is_blank(r)), None)
        if header is None:
            raise LedgerError(f"{path}: empty file")
        index = _header_index(path, header)

        parsed = []
        for row in reader:
            if _is_blank(row):
                continue
            line = f"{path} line {reader.line_num}"
            if len(row) > len(header):
                raise LedgerError(f"{line}: too many fields")
            if len(row) < len(header):
                raise LedgerError(
                    f"{line}: missing column '{header[len(row)].strip()}'"
                )
            note = row[index["note"]] if "note" in index else None
            try:
                parsed.append(
                    make_expense(
                        row[index["date"]].strip(),
                        row[index["amount"]],
                        row[index["category"]],
                        note,
                    )
                )
            except LedgerError as err:
                raise LedgerError(f"{line}: {err}") from None
    except csv.Error as err:
        raise LedgerError(f"{path} line {reader.line_num}: {err}") from None

    # Multiset rule: each existing copy in the DB absorbs one copy from the file.
    existing = Counter(store.expenses())
    new = []
    skipped = 0
    for expense in parsed:
        if existing[expense] > 0:
            existing[expense] -= 1
            skipped += 1
        else:
            new.append(expense)
    store.add(new)
    return len(new), skipped


def handler(args, store, out) -> int:
    imported, skipped = import_expenses(store, args.path)
    out.write(f"imported {imported}, skipped {skipped} duplicates\n")
    return 0


def register(subparsers) -> None:
    p = subparsers.add_parser("import", help="load Expenses from a CSV file")
    p.add_argument("path")
    p.set_defaults(handler=handler)
