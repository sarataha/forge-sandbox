import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import NamedTuple
from unittest.mock import patch

from sandbox.__main__ import main


class CliResult(NamedTuple):
    code: int
    out: str
    err: str


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_dir = tmp.name
        self.db_path = os.path.join(self.tmp_dir, "ledger.db")
        patcher = patch.dict(os.environ, {"SANDBOX_LEDGER_DB": self.db_path})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("SANDBOX_LICENSE_KEY", None)

    def run_cli(self, *argv, env=None):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with patch.dict(os.environ, env or {}), redirect_stdout(out), redirect_stderr(err):
            try:
                code = main(["ledger", *argv])
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        return CliResult(code, out.getvalue(), err.getvalue())

    def write_file(self, name, text, encoding="utf-8"):
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding=encoding, newline="") as f:
            f.write(text)
        return path
