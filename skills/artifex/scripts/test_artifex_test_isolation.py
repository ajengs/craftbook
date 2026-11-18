"""Regression tests for router test-module environment isolation."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_flow as flow
import artifex_notify as notify


MODULES = ("test_artifex_flow", "test_artifex_state")
WEBHOOK = "https://chat.googleapis.com/v1/spaces/test/messages?key=canary-key&token=canary-token"


def record_started(root):
    session = flow.Session(root / "milestones" / "test", must_exist=False)
    session.record({"type": "init", "milestone": "test", "ticket": "TEST"})
    session.record({"type": "dispatched", "phase": "P3", "run_id": "test-run"})
    session.record({"type": "started", "run_id": "test-run"})
    return session


class TestModuleIsolationTests(unittest.TestCase):
    def test_importing_test_modules_keeps_explicit_notifications_available(self):
        for name in MODULES:
            with self.subTest(module=name), tempfile.TemporaryDirectory() as temp:
                with mock.patch.dict(os.environ, {notify.ENV_NAME: WEBHOOK}), \
                        mock.patch.object(notify, "_supervised_transport", return_value=(200, {}, b"")) as send:
                    importlib.reload(importlib.import_module(name))
                    self.assertEqual(os.environ.get(notify.ENV_NAME), WEBHOOK)
                    session = record_started(Path(temp))
                    self.assertTrue(session.state["active"]["test-run"]["started"])
                    send.assert_called_once()
                    self.assertTrue((Path(temp) / notify.DB_NAME).exists())


if __name__ == "__main__":
    unittest.main()
