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

    def test_module_lifecycle_disables_notifications_and_restores_environment(self):
        for name in MODULES:
            for webhook in (None, WEBHOOK):
                for fail in (False, True):
                    with self.subTest(module=name, webhook=bool(webhook), test_error=fail), \
                            tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ):
                        importlib.import_module(name)
                        if webhook is None:
                            os.environ.pop(notify.ENV_NAME, None)
                        else:
                            os.environ[notify.ENV_NAME] = webhook
                        before = dict(os.environ)

                        def exercise(case):
                            session = record_started(Path(temp))
                            case.assertTrue(session.state["active"]["test-run"]["started"])
                            case.assertNotIn(notify.ENV_NAME, os.environ)
                            case.assertFalse((Path(temp) / notify.DB_NAME).exists())
                            if fail:
                                raise RuntimeError("deliberate test error")

                        case_type = type("RouterNotificationCase", (unittest.TestCase,),
                                         {"__module__": name, "test_record": exercise})
                        result = unittest.TestResult()
                        with mock.patch.object(notify, "_supervised_transport",
                                               return_value=(200, {}, b"")) as send:
                            unittest.TestSuite([case_type("test_record")]).run(result)
                        self.assertEqual(result.testsRun, 1)
                        self.assertEqual(result.failures, [])
                        self.assertEqual(len(result.errors), int(fail), result.errors)
                        if fail:
                            self.assertIn("deliberate test error", result.errors[0][1])
                        send.assert_not_called()
                        self.assertEqual(dict(os.environ), before)


if __name__ == "__main__":
    unittest.main()
