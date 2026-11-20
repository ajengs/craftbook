"""Real-git checks for artifex_flow.Git, the adapter the unit tests replace with FakeGit.

Skipped unless ARTIFEX_GIT_TESTS=1, because each git launch is slow on some machines.
Run: ARTIFEX_GIT_TESTS=1 python -m unittest test_artifex_git_integration -v
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifex_flow as af  # noqa: E402


def git(cwd, *args, check=True):
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and proc.returncode:
        raise AssertionError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout.strip()


@unittest.skipUnless(os.environ.get("ARTIFEX_GIT_TESTS") == "1", "set ARTIFEX_GIT_TESTS=1 to run real-git tests")
class GitAdapterTests(unittest.TestCase):
    """A bare origin and a clone on feature, one commit ahead of main, built once and copied per test."""

    @classmethod
    def setUpClass(cls):
        cls.template = tempfile.TemporaryDirectory()
        root = Path(cls.template.name)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(root / "origin.git")], check=True)
        subprocess.run(["git", "clone", "-q", str(root / "origin.git"), str(root / "work")],
                       check=True, capture_output=True)
        work = root / "work"
        # Relative, so a copied pair of folders still points at its own origin.
        git(work, "config", "remote.origin.url", "../origin.git")
        git(work, "config", "user.email", "t@example.com")
        git(work, "config", "user.name", "t")
        git(work, "checkout", "-q", "-b", "main")
        cls._commit(work, "app.py", "a = 1\n", "base")
        git(work, "push", "-q", "origin", "main")
        git(work, "checkout", "-q", "-b", "feature")
        cls._commit(work, "feature.py", "x = 1\n", "feature")

    @classmethod
    def tearDownClass(cls):
        cls.template.cleanup()

    @staticmethod
    def _commit(work, path, text, message):
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_text(text, encoding="utf-8")
        git(work, "add", path)
        git(work, "commit", "-q", "-m", message)
        return git(work, "rev-parse", "HEAD")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        shutil.copytree(self.template.name, root, dirs_exist_ok=True)
        self.work = root / "work"
        self.git = af.Git(self.work)
        self.old = git(self.work, "rev-parse", "HEAD")

    def commit(self, path, text, message):
        return self._commit(self.work, path, text, message)

    def advance_main(self, path, text):
        git(self.work, "checkout", "-q", "main")
        self.commit(path, text, "on main")
        git(self.work, "checkout", "-q", "feature")

    def classify(self, new):
        return af.classify_push(self.git, self.old, new, "main", af.DEFAULT_DOC_PATTERNS)["class"]

    def test_rebase_keeps_patch_ids_and_a_changed_patch_is_code(self):
        self.advance_main("other.py", "y = 1\n")
        git(self.work, "rebase", "-q", "main")
        rebased = git(self.work, "rev-parse", "HEAD")
        self.assertNotEqual(rebased, self.old)
        self.assertEqual(len(self.git.patch_ids("main", rebased)), 1)
        self.assertEqual(self.classify(rebased), "rebase")
        self.commit("feature.py", "x = 2\n", "amended")
        git(self.work, "reset", "-q", "--soft", "HEAD~2")
        git(self.work, "commit", "-q", "-m", "feature")
        self.assertEqual(self.classify(git(self.work, "rev-parse", "HEAD")), "code")

    def test_clean_merge_and_conflict_resolution_merge(self):
        self.advance_main("other.py", "y = 1\n")
        git(self.work, "merge", "-q", "--no-edit", "main")
        clean = git(self.work, "rev-parse", "HEAD")
        self.assertEqual(self.git.merges_between(self.old, clean), [clean])
        self.assertEqual(self.git.remerge_diff(clean), "")
        self.assertEqual(self.git.own_commits(self.old, clean, "main"), [])
        self.assertEqual(self.classify(clean), "merge")

        self.advance_main("feature.py", "x = 'main'\n")
        git(self.work, "merge", "-q", "main", check=False)
        (self.work / "feature.py").write_text("x = 'resolved'\n", encoding="utf-8")
        git(self.work, "add", "feature.py")
        git(self.work, "commit", "-q", "--no-edit")
        resolved = git(self.work, "rev-parse", "HEAD")
        self.assertTrue(self.git.remerge_diff(resolved))
        self.assertEqual(self.classify(resolved), "code")

    def test_ancestry_and_commit_lookup(self):
        new = self.commit("docs/guide.md", "hi\n", "docs")
        self.assertTrue(self.git.is_ancestor(self.old, new))
        self.assertFalse(self.git.is_ancestor(new, self.old))
        self.assertTrue(self.git.commit_exists(new))
        self.assertFalse(self.git.commit_exists("0" * 40))
        self.assertEqual(self.git.paths(new), ["docs/guide.md"])
        self.assertEqual(self.git.merge_base(new, "main"), git(self.work, "rev-parse", "main"))
        self.assertEqual(self.classify(new), "docs")

    def test_reads_origin_branch_after_push_and_internal_codes(self):
        self.assertEqual(self.git.rev_parse("origin/feature", verify=True), "")
        with self.assertRaises(af.GitError):
            self.git.rev_parse("origin/feature")
        head = self.commit("feature.py", "x = 1  # covers VER-12\n", "implement SPEC-3")
        git(self.work, "push", "-q", "origin", "feature")
        self.git.fetch("feature", "main")
        self.assertEqual(self.git.rev_parse("origin/feature"), head)
        with self.assertRaises(af.GitError):
            self.git.fetch("no-such-branch")
        self.assertEqual(af.internal_code_hits(self.git, self.old, head, af.DEFAULT_CODE_PATTERNS),
                         ["SPEC-3", "VER-12"])

    def test_target_ahead_counts_unpushed_target_commits(self):
        fields = {"workdir": str(self.work), "target": "main"}
        self.assertIsNone(af.target_ahead(fields))
        self.advance_main("local.py", "z = 1\n")
        ahead = af.target_ahead(fields)
        self.assertEqual(ahead["commits"], 1)
        self.assertEqual(ahead["local"], git(self.work, "rev-parse", "main"))
        self.assertEqual(ahead["origin"], git(self.work, "rev-parse", "origin/main"))


if __name__ == "__main__":
    unittest.main()
