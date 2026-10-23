import pathlib
import tempfile
import unittest
from devcity.guard.audit import RepoAuditor


class TestRepoAuditor(unittest.TestCase):
    def test_clean_repo_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir)
            (p / ".gitignore").write_text("node_modules\n.git\ndist\nbuild\n*.log\nvenv\n", encoding="utf-8")
            (p / "CLAUDE.md").write_text("# Project Guide\nRun tests: npm test\n", encoding="utf-8")

            auditor = RepoAuditor(p)
            res = auditor.audit()
            self.assertEqual(res.score, 100)
            self.assertEqual(res.grade, "A")
            self.assertEqual(len(res.findings), 0)

    def test_bloated_instruction_file_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir)
            (p / ".gitignore").write_text("node_modules\n.git\ndist\nbuild\n*.log\nvenv\n", encoding="utf-8")
            # Write 200 lines to CLAUDE.md
            bloat = "\n".join([f"- Rule {i}: detail" for i in range(200)])
            (p / "CLAUDE.md").write_text(bloat, encoding="utf-8")

            auditor = RepoAuditor(p)
            res = auditor.audit()
            self.assertLess(res.score, 100)
            warning_cats = [f.category for f in res.findings]
            self.assertIn("instructions", warning_cats)


if __name__ == "__main__":
    unittest.main()
