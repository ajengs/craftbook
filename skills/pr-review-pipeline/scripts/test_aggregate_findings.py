import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("aggregate_findings.py")


class AggregateFindingsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.json_output = self.root / "report.json"
        self.markdown_output = self.root / "findings.md"

    def write(self, name, findings):
        (self.root / f"{name}.json").write_text(
            json.dumps({"reviewer": name, "findings": findings}), encoding="utf-8"
        )

    def aggregate(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), "--json-out", str(self.json_output),
             "--md-out", str(self.markdown_output)],
            capture_output=True, text=True, check=False,
        )

    def report(self):
        return json.loads(self.json_output.read_text(encoding="utf-8"))

    def test_duplicate_keeps_highest_severity_and_strictest_action_in_either_order(self):
        common = {"file": "service.py", "line": 12, "title": "Result is lost"}
        blocker = dict(common, severity="medium", action_class=" BLOCKS-MERGE ")
        higher_severity = dict(common, severity="high", action_class="before-enablement")
        for first, second in ((blocker, higher_severity), (higher_severity, blocker)):
            with self.subTest(first=first["severity"]):
                self.write("logic", [first])
                self.write("tests", [second])
                run = self.aggregate()
                self.assertEqual(run.returncode, 0, run.stderr)
                report = self.report()
                finding, = report["findings"]
                self.assertEqual(finding["severity"], "high")
                self.assertEqual(finding["action_class"], "blocks-merge")
                self.assertEqual(finding["reviewers"], ["logic", "tests"])
                self.assertEqual(report["action_counts"]["blocks-merge"], 1)
                self.assertIn("conflicting action classes", run.stderr)
                self.assertIn("blocking merge", report["outcome_line"])

    def test_all_unusable_inputs_fail_without_writing_reports(self):
        (self.root / "logic.json").write_text("reviewer prose", encoding="utf-8")
        (self.root / "tests.json").write_text("[]", encoding="utf-8")
        (self.root / "config.json").write_text("{}", encoding="utf-8")
        run = self.aggregate()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("No usable reviewer JSON", run.stderr)
        self.assertFalse(self.json_output.exists())
        self.assertFalse(self.markdown_output.exists())

    def test_partial_coverage_preserves_usable_findings_and_qualifies_outcome(self):
        self.write("logic", [{"title": "Clean up import", "severity": "low", "action_class": "cleanup"}])
        self.write("tests", [{"line": []}])
        run = self.aggregate()
        self.assertEqual(run.returncode, 0, run.stderr)
        report = self.report()
        self.assertEqual(report["reviewers"], ["logic"])
        self.assertEqual(list(report["skipped_reviewers"]), ["tests.json"])
        self.assertEqual(report["action_counts"]["cleanup"], 1)
        self.assertIn("Review incomplete", report["outcome_line"])
        self.assertNotIn("nothing blocking merge", report["outcome_line"])
        markdown = self.markdown_output.read_text(encoding="utf-8")
        self.assertIn("Missing reviewer coverage", markdown)
        self.assertIn("tests.json", markdown)

    def test_incomplete_empty_review_carries_coverage_gap(self):
        self.write("logic", [])
        (self.root / "tests.json").write_text("reviewer prose", encoding="utf-8")
        run = self.aggregate()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("no findings in usable reviewer outputs", self.report()["outcome_line"])

    def test_valid_empty_review_is_complete_on_rerun(self):
        (self.root / "logic.json").write_text(
            '\n```json\n{"findings": []}\n```\n', encoding="utf-8"
        )
        for _ in range(2):
            run = self.aggregate()
            self.assertEqual(run.returncode, 0, run.stderr)
            report = self.report()
            self.assertEqual(report["outcome_line"], "No findings.")
            self.assertEqual(report["reviewers"], ["logic"])
            self.assertEqual(report["skipped_reviewers"], {})
