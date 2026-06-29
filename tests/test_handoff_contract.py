from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class HandoffContractTest(unittest.TestCase):
    def test_repo_urls_use_neutral_handoff_name(self):
        checked_paths = [
            "README.md",
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
        ]
        for path in checked_paths:
            text = read(path)
            self.assertIn("josuemarlique/handoff", text)
            self.assertNotIn("josuemarlique/claude-handoff", text)

    def test_handoffs_is_canonical_with_claude_archive_migration(self):
        skill = read("skills/handoff/SKILL.md")
        generation = read("skills/handoff/references/handoff-generation.md")
        resume = read("skills/handoff/references/resume-verification.md")

        combined = "\n".join([skill, generation, resume])
        self.assertIn(".handoffs/", combined)
        self.assertIn(".claude/handoffs/", combined)
        self.assertIn("copy", combined.lower())
        self.assertIn("archive", combined.lower())
        self.assertIn("delete", combined.lower())

        self.assertIn("mkdir -p .handoffs", generation)
        self.assertIn(".handoffs/{timestamp}-handoff.md", generation)
        self.assertIn(".handoffs/LATEST.md", resume)
        self.assertIn("scripts/migrate-handoffs.sh", combined)

    def test_freshness_checks_watch_new_and_legacy_handoff_dirs(self):
        script = read("skills/handoff/scripts/freshness-check.sh")
        self.assertIn("docs .handoffs .claude .Codex .codex", script)

    def test_resume_status_report_includes_mode_context_and_limits(self):
        resume = read("skills/handoff/references/resume-verification.md")
        self.assertIn("**Mode:**", resume)
        self.assertIn("**Context size:**", resume)
        self.assertIn("**Limits:**", resume)

    def test_migration_script_copies_legacy_handoffs_without_deleting_archive(self):
        script = ROOT / "skills/handoff/scripts/migrate-handoffs.sh"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            legacy = project / ".claude/handoffs"
            legacy.mkdir(parents=True)
            (legacy / "LATEST.md").write_text("legacy handoff\n", encoding="utf-8")
            (legacy / "2026-06-28-12-00-handoff.md").write_text(
                "history\n", encoding="utf-8"
            )

            result = subprocess.run(
                ["sh", str(script)],
                cwd=project,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (project / ".handoffs/LATEST.md").read_text(encoding="utf-8"),
                "legacy handoff\n",
            )
            self.assertTrue((legacy / "LATEST.md").exists())
            self.assertIn("Migrated handoff history", result.stdout)
            self.assertIn("left in place as an archive", result.stdout)
            self.assertIn("delete `.claude/handoffs/`", result.stdout)


if __name__ == "__main__":
    unittest.main()
