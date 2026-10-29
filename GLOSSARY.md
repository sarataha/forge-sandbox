# Ledger

A personal expense tracker run from the `sandbox ledger` command, used to pilot project mode.

## Language

**Expense**:
Money spent once: an amount, a date, a Category and an optional note.
_Avoid_: transaction, entry, record

**Category**:
A free-text label grouping Expenses, compared case-insensitively.
_Avoid_: tag, type

**Budget**:
The spending limit for one Category in every Month.
_Avoid_: limit, cap

**Month**:
A calendar month, written `YYYY-MM`; an Expense belongs to the Month of its date.
_Avoid_: period

**Report**:
Spending per Category for one Month, compared with each Category's Budget.
_Avoid_: summary, statement
