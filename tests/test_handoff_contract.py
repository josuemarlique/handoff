from pathlib import Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]

SKILL = "skills/handoff/SKILL.md"
GENERATION = "skills/handoff/references/handoff-generation.md"
RESUME = "skills/handoff/references/resume-verification.md"
CONTRACT = "skills/handoff/references/next-session-contract.md"
FORMATTING = "skills/handoff/references/prompt-engineering.md"

HANDOFF_EXAMPLES = [
    "skills/handoff/examples/handoff-full.md",
    "skills/handoff/examples/handoff-compact.md",
    "skills/handoff/examples/handoff-long.md",
]

# The goal file is deliberately size-capped. See next-session-contract.md 5.2.
GOAL_BODY_BUDGET = 3000

# Claude Code refuses a /goal condition longer than this.
GOAL_COMMAND_CEILING = 4000


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def slice_between(text: str, start_marker: str, end_marker: str) -> str:
    """Return the text between two markers. The end marker is excluded."""
    start = text.index(start_marker)
    end = text.index(end_marker, start + len(start_marker))
    return text[start:end]


def section(text: str, heading: str) -> str:
    """Return the body of a `## heading` section, up to the next `## ` heading.

    Fenced code blocks are skipped, so a `##` line inside an example does not
    end the section early.
    """
    lines = text.splitlines()
    start = lines.index(heading)
    body = [heading]
    in_fence = False
    for line in lines[start + 1 :]:
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def fenced_block_containing(text: str, needle: str) -> str:
    """Return the contents of the fenced code block that holds `needle`."""
    for chunk in text.split("```")[1::2]:
        # Drop the language tag on the opening fence.
        body = chunk.split("\n", 1)[1] if "\n" in chunk else ""
        if needle in body:
            return body.strip("\n")
    raise AssertionError(f"no fenced block contains {needle!r}")


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

        self.assertIn('mkdir -p ".handoffs/$DAY"', generation)
        self.assertIn(".handoffs/$DAY/$TS-handoff.md", generation)
        self.assertIn(".handoffs/LATEST.md", resume)
        self.assertIn("scripts/migrate-handoffs.sh", combined)

    def test_freshness_checks_watch_new_and_legacy_handoff_dirs(self):
        script = read("skills/handoff/scripts/freshness-check.sh")
        self.assertIn("docs .handoffs .claude .Codex .codex", script)

    def test_freshness_ignores_every_archived_handoff_folder(self):
        """Migration leaves the old folders in place. If the freshness check
        counts them as drift, every single resume reports a false alarm."""
        script = ROOT / "skills/handoff/scripts/freshness-check.sh"
        archives = [
            ".claude/handoffs",
            ".claude/.handoffs",
            ".codex/handoffs",
            ".Codex/handoffs",
            "docs/handoffs",
            "handoffs",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            subprocess.run(["git", "init", "-q", "."], cwd=project, check=True)
            for key, value in (("user.email", "t@t.t"), ("user.name", "t")):
                subprocess.run(["git", "config", key, value], cwd=project, check=True)
            (project / "app.js").write_text("app\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=project, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=project, check=True)
            head = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=project, check=True, text=True, stdout=subprocess.PIPE,
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project, check=True, text=True, stdout=subprocess.PIPE,
            ).stdout.strip()

            body = (
                "---\n"
                "created: 2026-08-16T14:30:00\n"
                f"branch: {branch}\n"
                f"last_commit: {head}\n"
                "uncommitted_changes: false\n"
                "---\n\n## Start Here\n\nx\n"
            )
            day = project / ".handoffs/2026-08-16"
            day.mkdir(parents=True)
            (day / "2026-08-16-14-30-handoff.md").write_text(body, encoding="utf-8")
            (project / ".handoffs/LATEST.md").write_text(body, encoding="utf-8")

            # Leftover archives, exactly as migration leaves them.
            for archive in archives:
                folder = project / archive
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "2026-01-01-08-00-handoff.md").write_text(
                    "archived\n", encoding="utf-8"
                )

            result = subprocess.run(
                ["sh", str(script), ".handoffs/LATEST.md"],
                cwd=project, check=False, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            checks = json.loads(result.stdout)["checks"]

            for archive in archives:
                self.assertNotIn(
                    archive,
                    str(checks["uncommitted_changes"]["files_changed"]),
                    f"{archive} archive counted as uncommitted work",
                )
                self.assertNotIn(
                    archive,
                    str(checks["spec_changes"]["modified_files"]),
                    f"{archive} archive counted as spec drift",
                )

    def test_wrong_location_list_matches_what_the_script_actually_sweeps(self):
        """SKILL.md tells the model which folders are wrong. The script is what
        actually sweeps them. If the two lists drift apart, a folder gets named
        as wrong but never migrated - or migrated but never explained."""
        skill = read(SKILL)
        migrate = read("skills/handoff/scripts/migrate-handoffs.sh")

        legacy_line = [
            line for line in migrate.splitlines() if line.startswith("LEGACY_DIRS=")
        ]
        self.assertEqual(len(legacy_line), 1, "LEGACY_DIRS is not a single assignment")
        swept = legacy_line[0].split("=", 1)[1].strip().strip('"').split()

        self.assertIn(".claude/handoffs", swept)
        for folder in swept:
            self.assertIn(
                f"`{folder}/`",
                skill,
                f"{folder} is swept by the script but not named in SKILL.md",
            )

        # And the reverse: nothing is called wrong without being swept.
        wrong_table = slice_between(
            skill, "**These locations are wrong.", "If you find handoffs in any"
        )
        for folder in swept:
            self.assertIn(folder, wrong_table, f"{folder} missing from the table")

    def test_freshness_ignores_the_handoff_run_own_files(self):
        script = ROOT / "skills/handoff/scripts/freshness-check.sh"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            day = project / ".handoffs/2026-08-16"
            day.mkdir(parents=True)
            body = (
                "---\n"
                "created: 2026-08-16T14:30:00\n"
                "branch: main\n"
                "last_commit: abc1234\n"
                "uncommitted_changes: false\n"
                "---\n\n## Refined Intent\n\ntest\n"
            )
            (day / "2026-08-16-14-30-handoff.md").write_text(body, encoding="utf-8")
            (day / "2026-08-16-14-30-prompt.md").write_text("p\n", encoding="utf-8")
            (day / "2026-08-16-14-30-goal.md").write_text("g\n", encoding="utf-8")
            for pointer, text in (
                ("LATEST.md", body),
                ("LATEST-PROMPT.md", "p\n"),
                ("LATEST-GOAL.md", "g\n"),
            ):
                (project / ".handoffs" / pointer).write_text(text, encoding="utf-8")

            def spec_changes():
                result = subprocess.run(
                    ["sh", str(script), ".handoffs/LATEST.md"],
                    cwd=project,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)["checks"]["spec_changes"]

            clean = spec_changes()
            self.assertFalse(
                clean["stale"],
                f"handoff run flagged its own files: {clean['modified_files']}",
            )

            docs = project / "docs"
            docs.mkdir()
            (docs / "roadmap.md").write_text("next\n", encoding="utf-8")
            drifted = spec_changes()
            self.assertTrue(drifted["stale"])
            self.assertEqual(
                [entry["path"] for entry in drifted["modified_files"]],
                ["docs/roadmap.md"],
            )

    def test_freshness_does_not_report_the_handoff_folder_as_uncommitted_work(self):
        script = ROOT / "skills/handoff/scripts/freshness-check.sh"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            subprocess.run(["git", "init", "-q", "."], cwd=project, check=True)
            for key, value in (("user.email", "t@t.t"), ("user.name", "t")):
                subprocess.run(
                    ["git", "config", key, value], cwd=project, check=True
                )
            (project / "app.js").write_text("app\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=project, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "initial"], cwd=project, check=True
            )
            head = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=project,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()

            day = project / ".handoffs/2026-08-16"
            day.mkdir(parents=True)
            body = (
                "---\n"
                "created: 2026-08-16T14:30:00\n"
                f"branch: {branch}\n"
                f"last_commit: {head}\n"
                "uncommitted_changes: false\n"
                "---\n\n## Start Here\n\nx\n"
            )
            (day / "2026-08-16-14-30-handoff.md").write_text(body, encoding="utf-8")
            (project / ".handoffs/LATEST.md").write_text(body, encoding="utf-8")

            def uncommitted():
                result = subprocess.run(
                    ["sh", str(script), ".handoffs/LATEST.md"],
                    cwd=project,
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)["checks"]["uncommitted_changes"]

            quiet = uncommitted()
            self.assertFalse(
                quiet["stale"],
                f"untracked .handoffs/ reported as work: {quiet['files_changed']}",
            )

            (project / "app.js").write_text("app\nedited\n", encoding="utf-8")
            noisy = uncommitted()
            self.assertTrue(noisy["stale"])
            self.assertIn("app.js", noisy["files_changed"])
            self.assertNotIn(".handoffs/", noisy["files_changed"])

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

    def test_migration_sweeps_every_known_stray_handoff_folder(self):
        script = ROOT / "skills/handoff/scripts/migrate-handoffs.sh"
        strays = {
            ".claude/handoffs": "2026-01-02-08-00-handoff.md",
            ".claude/.handoffs": "2026-01-03-08-00-handoff.md",
            ".codex/handoffs": "2026-01-04-08-00-handoff.md",
            ".Codex/handoffs": "2026-01-05-08-00-handoff.md",
            "docs/handoffs": "2026-01-06-08-00-handoff.md",
            "handoffs": "2026-01-07-08-00-handoff.md",
        }
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for folder, name in strays.items():
                target = project / folder
                target.mkdir(parents=True)
                (target / name).write_text(folder, encoding="utf-8")

            result = subprocess.run(
                ["sh", str(script)],
                cwd=project,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            for folder, name in strays.items():
                day = name[:10]
                landed = project / ".handoffs" / day / name
                self.assertTrue(landed.exists(), f"{folder} was not migrated")
                self.assertEqual(landed.read_text(encoding="utf-8"), folder)
                self.assertTrue(
                    (project / folder / name).exists(),
                    f"{folder} archive was deleted",
                )

    def test_migration_ignores_unrelated_folder_named_handoffs(self):
        script = ROOT / "skills/handoff/scripts/migrate-handoffs.sh"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            decoy = project / "handoffs"
            decoy.mkdir()
            (decoy / "index.ts").write_text("export {}\n", encoding="utf-8")

            result = subprocess.run(
                ["sh", str(script)],
                cwd=project,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "")
            self.assertFalse((project / ".handoffs").exists())

    def test_migration_folds_flat_files_into_day_folders_and_is_idempotent(self):
        script = ROOT / "skills/handoff/scripts/migrate-handoffs.sh"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            flat = project / ".handoffs"
            flat.mkdir()
            dated = [
                "2026-03-14-02-30-handoff.md",
                "2026-03-14-02-30-prompt.md",
                "2026-03-14-02-30-goal.md",
                "2026-04-02-09-00-handoff.md",
            ]
            for name in dated:
                (flat / name).write_text(name, encoding="utf-8")
            for pointer in ("LATEST.md", "LATEST-PROMPT.md", "LATEST-GOAL.md"):
                (flat / pointer).write_text(pointer, encoding="utf-8")

            first = subprocess.run(
                ["sh", str(script)],
                cwd=project,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("day folders", first.stdout)

            for name in dated:
                self.assertTrue((flat / name[:10] / name).exists(), name)
                self.assertFalse((flat / name).exists(), f"{name} left at top level")

            # Pointer files stay at the top level so paths never move.
            for pointer in ("LATEST.md", "LATEST-PROMPT.md", "LATEST-GOAL.md"):
                self.assertTrue((flat / pointer).exists(), pointer)

            second = subprocess.run(
                ["sh", str(script)],
                cwd=project,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                second.stdout.strip(), "", "second run should be a silent no-op"
            )


class StorageLayoutTest(unittest.TestCase):
    def test_skill_names_every_wrong_folder_and_forbids_writing_there(self):
        skill = read(SKILL)
        for wrong in (
            "`.claude/handoffs/`",
            "`.claude/.handoffs/`",
            "`handoffs/`",
            "`docs/handoffs/`",
        ):
            self.assertIn(wrong, skill, f"{wrong} is not listed as a wrong location")
        self.assertIn("There is exactly one correct location", skill)
        self.assertIn("Never write to them", skill)

    def test_migration_script_sweeps_the_same_folders_the_skill_lists(self):
        script = read("skills/handoff/scripts/migrate-handoffs.sh")
        for folder in (
            ".claude/handoffs",
            ".claude/.handoffs",
            ".codex/handoffs",
            ".Codex/handoffs",
            "docs/handoffs",
        ):
            self.assertIn(folder, script, f"{folder} is not swept by the script")

    def test_day_folder_layout_is_specified_everywhere_files_are_written(self):
        skill = read(SKILL)
        generation = read(GENERATION)

        self.assertIn(".handoffs/YYYY-MM-DD/YYYY-MM-DD-HH-MM-handoff.md", skill)
        self.assertIn('mkdir -p ".handoffs/$DAY"', generation)
        for artifact in ("handoff", "prompt", "goal"):
            self.assertIn(f".handoffs/$DAY/$TS-{artifact}.md", generation)

        # Pointer files stay at the top level so their paths never change.
        for pointer in ("LATEST.md", "LATEST-PROMPT.md", "LATEST-GOAL.md"):
            self.assertIn(f".handoffs/{pointer}", generation, pointer)
        self.assertIn("Never write a timestamped file to the top level", generation)

    def test_list_mode_walks_day_folders(self):
        generation = read(GENERATION)
        self.assertIn("find .handoffs -type f -name '*-handoff.md'", generation)


class NextSessionContractTest(unittest.TestCase):
    def start_here_block(self, text: str) -> str:
        self.assertIn("## Start Here", text)
        return section(text, "## Start Here").strip()

    def test_contract_defines_the_writing_and_working_rules(self):
        contract = read(CONTRACT)
        block = self.start_here_block(contract)

        # Plain language rules.
        self.assertIn("middle school student", block)
        self.assertIn("short form", block)
        self.assertIn("TL;DR", block)
        self.assertIn("em dash", block)

        # Working rules.
        self.assertIn("subagents", block)
        self.assertIn("fan out subagents", block)
        self.assertIn("message each other", block)
        self.assertIn("/handoff --resume", block)

    def test_start_here_block_is_identical_in_every_example(self):
        # The canonical copy lives fenced inside the contract.
        expected = fenced_block_containing(read(CONTRACT), "## Start Here").strip()
        self.assertTrue(expected.startswith("## Start Here"))

        for example in HANDOFF_EXAMPLES:
            actual = self.start_here_block(read(example))
            self.assertEqual(
                actual,
                expected,
                f"{example} drifted from the canonical Start Here block",
            )

    def test_every_example_leads_with_start_here_then_tldr(self):
        for example in HANDOFF_EXAMPLES:
            text = read(example)
            body = text.split("---\n", 2)[2]
            headings = [
                line.strip() for line in body.splitlines() if line.startswith("## ")
            ]
            self.assertEqual(headings[0], "## Start Here", example)
            self.assertEqual(headings[1], "## TL;DR", example)

    def test_tldr_block_has_the_five_fixed_bullets(self):
        contract = read(CONTRACT)
        for label in (
            "**Where we are:**",
            "**What got done:**",
            "**What is next:**",
            "**Watch out for:**",
            "**State:**",
        ):
            self.assertIn(label, contract, label)
        for example in HANDOFF_EXAMPLES:
            text = read(example)
            tldr = section(text, "## TL;DR")
            bullets = [l for l in tldr.splitlines() if l.startswith("- **")]
            self.assertEqual(len(bullets), 5, f"{example} TL;DR is not five bullets")

    def test_resume_mode_states_the_working_agreement_out_loud(self):
        resume = read(RESUME)
        self.assertIn("### Working agreement for this session", resume)
        self.assertIn("subagents", resume)
        self.assertIn("TL;DR", resume)


class GoalFileTest(unittest.TestCase):
    def test_contract_records_the_verified_goal_mechanics(self):
        contract = read(CONTRACT)
        # /goal is a finish line, not storage. Getting this wrong is the whole risk.
        self.assertIn("4,000 characters", contract)
        self.assertIn("cannot read files", contract)
        self.assertIn("/goal clear", contract)
        self.assertIn("One at a time", contract)
        self.assertIn("trusted workspace", contract)
        self.assertIn("measurable end state", contract)

    def test_contract_warns_against_pointing_a_goal_at_a_file(self):
        contract = read(CONTRACT)
        self.assertIn("/goal Follow .handoffs/LATEST-GOAL.md", contract)
        self.assertIn("The evaluator cannot read files", contract)

    def test_goal_file_is_on_by_default_and_has_an_off_switch(self):
        skill = read(SKILL)
        generation = read(GENERATION)
        self.assertIn("| `--no-goal` | Off |", skill)
        self.assertIn(".handoffs/LATEST-GOAL.md", skill)
        self.assertIn("### `--no-goal`", generation)
        self.assertIn("goal_file:", generation)

    def test_goal_file_size_budget_is_stated_and_the_example_respects_it(self):
        contract = read(CONTRACT)
        self.assertIn(f"{GOAL_BODY_BUDGET:,} characters", contract)

        goal = read("skills/handoff/examples/goal.md")
        body = goal.split("<!--")[0].rstrip()
        self.assertLessEqual(
            len(body),
            GOAL_BODY_BUDGET,
            f"goal example is {len(body)} chars, over the {GOAL_BODY_BUDGET} budget",
        )

    def test_goal_example_carries_a_usable_finish_line(self):
        goal = read("skills/handoff/examples/goal.md")
        self.assertIn("## Finish line", goal)
        conditions = [
            line.strip()
            for line in goal.splitlines()
            if line.strip().startswith("/goal ")
            and not line.strip().startswith("/goal clear")
        ]
        self.assertTrue(conditions, "no /goal condition in the goal example")
        for condition in conditions:
            self.assertLessEqual(len(condition), GOAL_COMMAND_CEILING)
            # A usable condition names its proof, not just the task.
            self.assertIn("this conversation", condition)

    def test_kickoff_block_loads_context_before_it_offers_goal(self):
        contract = read(CONTRACT)
        kickoff = slice_between(
            contract, "## 6. The kickoff block", "## 7. Resume Mode use"
        )
        load_step = kickoff.index(".handoffs/LATEST-GOAL.md")
        goal_step = kickoff.index("**2. Optional")
        self.assertLess(
            load_step, goal_step, "the /goal step must not come before loading context"
        )
        self.assertIn("plain message, not a slash command", kickoff)
        self.assertIn("single line with no newlines", kickoff)


class VerbosityModeTest(unittest.TestCase):
    LONG_ONLY = [
        "## File-By-File Notes",
        "## Commands That Matter",
        "## Open Questions",
        "## Glossary",
    ]

    def test_three_modes_are_defined_with_flags_and_bare_words(self):
        skill = read(SKILL)
        self.assertIn("| `--long` | Off |", skill)
        self.assertIn("| `--compact` | Off |", skill)
        self.assertIn("| `--mode <level>` | `full` |", skill)
        for typed in ("/handoff long", "/handoff compact", "/handoff full"):
            self.assertIn(typed, skill, typed)

    def test_compact_and_long_together_is_rejected(self):
        skill = read(SKILL)
        self.assertIn("You passed both `--compact` and `--long`", skill)

    def test_long_mode_sections_are_specified_and_demonstrated(self):
        generation = read(GENERATION)
        formatting = read(FORMATTING)
        example = read("skills/handoff/examples/handoff-long.md")
        for heading in self.LONG_ONLY:
            self.assertIn(heading, generation, f"{heading} missing from generation")
            self.assertIn(heading, formatting, f"{heading} missing from formatting")
            self.assertIn(heading, example, f"{heading} missing from long example")

    def test_long_only_sections_stay_out_of_the_other_examples(self):
        for example in (
            "skills/handoff/examples/handoff-full.md",
            "skills/handoff/examples/handoff-compact.md",
        ):
            text = read(example)
            for heading in self.LONG_ONLY:
                self.assertNotIn(heading, text, f"{heading} leaked into {example}")

    def test_every_example_declares_its_mode_in_frontmatter(self):
        for example, expected in zip(HANDOFF_EXAMPLES, ("full", "compact", "long")):
            self.assertIn(f"mode: {expected}", read(example), example)

    def test_goal_file_size_does_not_change_with_mode(self):
        contract = read(CONTRACT)
        self.assertIn("does **not** get longer in `--long` mode", contract)


class ReconcileTest(unittest.TestCase):
    SCRIPT = ROOT / "skills/handoff/scripts/reconcile-handoffs.sh"

    def run_reconcile(self, project, apply=False):
        args = ["sh", str(self.SCRIPT)]
        if apply:
            args.append("--apply")
        result = subprocess.run(
            args, cwd=project, check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def handoff(self, path, created, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\ncreated: {created}\nbranch: main\n---\n\n"
            f"## Refined Intent\n\n{body}\n",
            encoding="utf-8",
        )

    def messy_project(self, project):
        """The shape a real project ends up in after several skill versions."""
        self.handoff(
            project / ".claude/handoffs/2026-06-24-14-02-handoff.md",
            "2026-06-24T14:02:00", "old work",
        )
        # A LATEST.md matching no dated file: that handoff exists in one copy.
        self.handoff(
            project / ".claude/handoffs/LATEST.md",
            "2026-08-07T11:30:00", "this exists only as LATEST",
        )
        # Same name, different content, in another folder.
        self.handoff(
            project / "docs/handoffs/2026-06-24-14-02-handoff.md",
            "2026-06-24T14:02:00", "DIFFERENT content, same name",
        )
        # A prompt whose handoff is gone.
        (project / ".claude/handoffs/2026-07-05-13-00-prompt.md").write_text(
            "orphan\n", encoding="utf-8"
        )
        # Already canonical but sitting loose at the top level.
        self.handoff(
            project / ".handoffs/2026-08-01-09-00-handoff.md",
            "2026-08-01T09:00:00", "needs folding",
        )

    def test_report_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.messy_project(project)
            before = sorted(
                str(p.relative_to(project)) for p in project.rglob("*") if p.is_file()
            )

            out = self.run_reconcile(project)

            after = sorted(
                str(p.relative_to(project)) for p in project.rglob("*") if p.is_file()
            )
            self.assertEqual(before, after, "the report modified the project")
            self.assertIn("Nothing was changed", out)
            self.assertIn("--apply", out)

    def test_report_names_each_kind_of_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.messy_project(project)
            out = self.run_reconcile(project)

            self.assertIn("Rescue:", out)
            self.assertIn("Name collision:", out)
            self.assertIn("Orphan:", out)
            self.assertIn(".claude/handoffs/", out)
            self.assertIn("needs merging", out)

    def test_apply_rescues_a_latest_with_no_dated_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.messy_project(project)
            original = (project / ".claude/handoffs/LATEST.md").read_text(
                encoding="utf-8"
            )

            self.run_reconcile(project, apply=True)

            rescued = project / ".handoffs/2026-08-07/2026-08-07-11-30-handoff.md"
            self.assertTrue(rescued.exists(), "orphan LATEST.md was not rescued")
            self.assertEqual(rescued.read_text(encoding="utf-8"), original)

    def test_apply_keeps_both_sides_of_a_name_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.messy_project(project)
            self.run_reconcile(project, apply=True)

            day = project / ".handoffs/2026-06-24"
            landed = sorted(p.name for p in day.glob("*handoff*.md"))
            self.assertEqual(len(landed), 2, f"a colliding file was lost: {landed}")
            bodies = {(day / name).read_text(encoding="utf-8") for name in landed}
            self.assertEqual(len(bodies), 2, "both files kept but contents identical")

    def test_apply_never_deletes_a_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.messy_project(project)
            sources = sorted(
                str(p.relative_to(project))
                for p in project.rglob("*")
                if p.is_file() and not str(p.relative_to(project)).startswith(".handoffs")
            )

            self.run_reconcile(project, apply=True)

            still_there = sorted(
                str(p.relative_to(project))
                for p in project.rglob("*")
                if p.is_file() and not str(p.relative_to(project)).startswith(".handoffs")
            )
            self.assertEqual(sources, still_there, "a source file was removed")

    def test_apply_folds_canonical_files_into_day_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.messy_project(project)
            self.run_reconcile(project, apply=True)

            self.assertTrue(
                (project / ".handoffs/2026-08-01/2026-08-01-09-00-handoff.md").exists()
            )
            self.assertFalse(
                (project / ".handoffs/2026-08-01-09-00-handoff.md").exists(),
                "loose file left at the top level",
            )

    def test_running_it_twice_finds_nothing_to_do(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.messy_project(project)
            self.run_reconcile(project, apply=True)
            after_first = sorted(
                str(p.relative_to(project)) for p in project.rglob("*") if p.is_file()
            )

            second = self.run_reconcile(project, apply=True)
            after_second = sorted(
                str(p.relative_to(project)) for p in project.rglob("*") if p.is_file()
            )

            self.assertEqual(after_first, after_second, "second run changed files")
            self.assertIn("Nothing to do", second)

    def test_empty_project_says_so_and_exits_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_reconcile(Path(tmp))
            self.assertIn("No handoff files found", out)

    def test_unknown_argument_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                ["sh", str(self.SCRIPT), "--bogus"],
                cwd=tmp, check=False, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Usage:", result.stderr)

    def test_reconcile_is_documented_as_its_own_mode(self):
        skill = read(SKILL)
        readme = read("README.md")
        self.assertIn("## Reconcile Mode", skill)
        self.assertIn("| `--reconcile` | Off |", skill)
        self.assertIn("/handoff reconcile", skill)
        self.assertIn("scripts/reconcile-handoffs.sh", skill)
        # Report first is the whole safety property. It must be stated.
        self.assertIn("Never run `--apply` without showing the report first", skill)
        self.assertIn("--reconcile", readme)


class ReadmeTest(unittest.TestCase):
    def test_readme_opens_with_a_tldr(self):
        readme = read("README.md")
        headings = [l.strip() for l in readme.splitlines() if l.startswith("## ")]
        self.assertEqual(headings[0], "## TL;DR")

    def test_readme_has_github_renderable_diagrams(self):
        readme = read("README.md")
        blocks = readme.count("```mermaid")
        self.assertGreaterEqual(blocks, 3, "expected at least three mermaid diagrams")
        # A semicolon inside a sequenceDiagram message breaks the parser.
        for chunk in readme.split("```mermaid")[1:]:
            body = chunk.split("```")[0]
            if body.lstrip().startswith("sequenceDiagram"):
                for line in body.splitlines():
                    if "->>" in line:
                        self.assertNotIn(";", line, f"semicolon breaks mermaid: {line}")

    def test_readme_documents_the_new_surface(self):
        readme = read("README.md")
        for expected in (
            ".handoffs/",
            "day folders",
            "`--long`",
            "`--no-goal`",
            "4,000 characters",
            "cannot run commands and it cannot read files",
            "fan out subagents",
        ):
            self.assertIn(expected, readme, expected)


if __name__ == "__main__":
    unittest.main()
