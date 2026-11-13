"""Tests for catalog precedence, pinned identity and resolution across phase workspaces."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import artifex_tools as at


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "implementation"
        self.project.mkdir()
        self.home = self.root / "home"
        self.user = self.home / ".agents" / "artifex-tools.local.md"
        self.user.parent.mkdir(parents=True)

    def write(self, path, text="catalog"):
        path.write_text(text, encoding="utf-8")
        return path.resolve()

    def resolve(self, explicit=None):
        return at.resolve_catalog(self.project, explicit, home=self.home)

    def test_explicit_relative_path_wins_and_uses_implementation_root(self):
        selected = self.write(self.project / "chosen.md")
        self.write(self.project / "artifex-tools.local.md", "project")
        self.write(self.user, "user")
        result = self.resolve("chosen.md")
        self.assertEqual(Path(result["path"]), selected)
        self.assertEqual(result["source"], "explicit")

    def test_absent_explicit_selection_does_not_fall_back(self):
        self.write(self.user)
        with self.assertRaises(at.CatalogError):
            self.resolve("missing.md")

    def test_invalid_or_unreadable_project_selection_does_not_fall_back(self):
        selected = self.project / "artifex-tools.local.md"
        self.write(self.user)
        selected.mkdir()
        with self.assertRaises(at.CatalogError):
            self.resolve()
        selected.rmdir()
        self.write(selected)
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError("denied")):
            with self.assertRaises(at.CatalogError):
                self.resolve()

    def test_default_precedence_and_example_fallback(self):
        self.assertEqual(self.resolve()["source"], "example")
        self.write(self.user)
        self.assertEqual(self.resolve()["source"], "user")
        self.write(self.project / "artifex-tools.local.md")
        self.assertEqual(self.resolve()["source"], "project")

    def test_nested_workdir_resolves_repository_root(self):
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        nested = self.project / "src"
        nested.mkdir()
        selected = self.write(self.project / "artifex-tools.local.md")
        self.assertEqual(Path(at.resolve_catalog(nested, home=self.home)["path"]), selected)

    def test_check_uses_pinned_file_even_when_a_higher_precedence_file_appears(self):
        selected = self.write(self.user)
        plan = self.resolve()
        self.write(self.project / "artifex-tools.local.md", "different")
        self.assertEqual(Path(at.check_catalog(Path(plan["path"]), plan["sha256"])["path"]), selected)

    def test_changed_or_deleted_pinned_catalog_is_refused(self):
        selected = self.write(self.project / "artifex-tools.local.md")
        plan = self.resolve()
        self.write(selected, "changed")
        with self.assertRaises(at.CatalogError):
            at.check_catalog(selected, plan["sha256"])
        selected.unlink()
        with self.assertRaises(at.CatalogError):
            at.check_catalog(selected, plan["sha256"])

    def test_git_permission_and_ownership_failures_do_not_select_a_different_root(self):
        proc = subprocess.CompletedProcess([], 128, "", "fatal: detected dubious ownership in repository")
        with mock.patch.object(at.subprocess, "run", return_value=proc):
            with self.assertRaises(at.CatalogError):
                self.resolve()
        (self.project / ".git").mkdir()
        proc = subprocess.CompletedProcess([], 128, "", "fatal: not a git repository")
        with mock.patch.object(at.subprocess, "run", return_value=proc):
            with self.assertRaises(at.CatalogError):
                self.resolve()

    def test_relative_pinned_path_is_refused(self):
        with self.assertRaises(at.CatalogError):
            at.check_catalog(Path("catalog.md"), "x" * 64)


if __name__ == "__main__":
    unittest.main()
