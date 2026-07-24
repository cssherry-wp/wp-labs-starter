"""Unit tests for session_summarize.py — LLM calls mocked, DB in :memory:."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from session_summarize import (
    MAX_BATCH,
    TRANSCRIPT_TOKEN_LIMIT,
    _build_transcript,
    _extract_turns,
    _process_batch,
    apply_improvements,
    compute_cost,
    extract_metadata,
    group_sessions,
    insert_agents,
    parse_llm_response,
    scan_sessions,
    upsert_session,
    write_summary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_USER = {
    "type": "user",
    "timestamp": "2026-01-01T10:00:00.000Z",
    "message": {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
}
_ASSISTANT = {
    "type": "assistant",
    "timestamp": "2026-01-01T10:00:05.000Z",
    "message": {
        "role": "assistant",
        "model": "claude-sonnet-4-6",
        "content": [{"type": "text", "text": "Hi there"}],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_input_tokens": 200,
            "cache_read_input_tokens": 300,
        },
    },
}
_AI_TITLE = {"type": "ai-title", "aiTitle": "Test Session Title"}
_SYSTEM_STOP = {
    "type": "system",
    "subtype": "stop_hook_summary",
    "cwd": "/Users/testuser/code/myproject",
    "timestamp": "2026-01-01T10:01:00.000Z",
}
_AWAY = {
    "type": "system",
    "subtype": "away_summary",
    "content": "Working on feature X.",
    "timestamp": "2026-01-01T10:02:00.000Z",
}

_GOOD_LLM_JSON = json.dumps({
    "needs_full_context": [],
    "summary_text": "Did some work.",
    "completed_tasks": ["Task A"],
    "incomplete_tasks": ["Task B"],
    "improvement_suggestions": [
        {
            "category": "Friction",
            "action_type": "CLAUDE.md",
            "description": "Always run tests",
            "target": "CLAUDE.md",
            "content": "Always run `make test` before committing.",
            "confidence": 90,
        }
    ],
    "unusual_flags": [],
})


def _jsonl(entries: list[dict]) -> str:
    """Serialize a list of dicts as newline-delimited JSON."""
    return "\n".join(json.dumps(e) for e in entries) + "\n"


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.write_text(_jsonl(entries), encoding="utf-8")


def _mem_db() -> sqlite3.Connection:
    """Return an in-memory database with the schema applied."""
    con = sqlite3.connect(":memory:")
    from session_summarize import SCHEMA
    con.executescript(SCHEMA)
    con.commit()
    return con


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScanDetectsChanges(unittest.TestCase):
    """Phase 1 hash-based change detection."""

    def test_scan_detects_changes(self) -> None:
        """New file is processed; unchanged hash skipped; changed hash reprocessed."""
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "-test-proj"
            proj.mkdir()
            f = proj / "aaaa.jsonl"
            _write_jsonl(f, [_USER, _ASSISTANT])
            con = _mem_db()

            result = scan_sessions(tmp, con)
            self.assertEqual(len(result), 1, "new file should be returned")

            # Simulate the file being persisted to DB
            upsert_session(con, result[0][1], result[0][2], result[0][3], result[0][4])
            con.commit()

            # Same file, same hash → skipped
            result2 = scan_sessions(tmp, con)
            self.assertEqual(len(result2), 0, "unchanged file should be skipped")

            # Modify the file → reprocessed
            f.write_text(_jsonl([_USER, _ASSISTANT, _USER]), encoding="utf-8")
            result3 = scan_sessions(tmp, con)
            self.assertEqual(len(result3), 1, "changed hash should be reprocessed")


class TestPartialRescan(unittest.TestCase):
    """Only changed files are reprocessed when some are unchanged."""

    def test_partial_rescan(self) -> None:
        """3 changed + 2 unchanged → only 3 returned by scan_sessions."""
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "-proj"
            proj.mkdir()
            files = [proj / f"{i}.jsonl" for i in range(5)]
            for f in files:
                _write_jsonl(f, [_USER, _ASSISTANT])
            con = _mem_db()

            # Persist 2 files as already processed
            for f in files[:2]:
                rel = str(f.relative_to(tmp))
                from session_summarize import sha256_file
                h = sha256_file(f)
                upsert_session(con, rel, "-proj", h, extract_metadata(f))
            con.commit()

            result = scan_sessions(tmp, con)
            self.assertEqual(len(result), 3)


class TestExtractMetadata(unittest.TestCase):
    """Metadata extraction from JSONL without LLM."""

    def test_extract_metadata(self) -> None:
        """ai_title, user_title, timestamps, token counts, and model are parsed."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as tmp:
            tmp.write(_jsonl([_AI_TITLE, _USER, _ASSISTANT, _SYSTEM_STOP, _AWAY]))
            tmp_path = tmp.name
        try:
            meta = extract_metadata(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        self.assertEqual(meta["ai_title"], "Test Session Title")
        self.assertEqual(meta["started_at"], "2026-01-01T10:00:00.000Z")
        self.assertEqual(meta["model"], "claude-sonnet-4-6")
        self.assertEqual(meta["input_tokens"], 100)
        self.assertEqual(meta["output_tokens"], 50)
        self.assertEqual(meta["cache_write_tokens"], 200)
        self.assertEqual(meta["cache_read_tokens"], 300)
        self.assertEqual(meta["user_turns"], 1)
        self.assertEqual(meta["assistant_turns"], 1)
        self.assertEqual(meta["away_summary"], "Working on feature X.")
        self.assertEqual(meta["workspace"], "/Users/testuser/code/myproject")


class TestAgentExtraction(unittest.TestCase):
    """Agent spawn entries produce correct rows in the agents table."""

    def test_agent_extraction(self) -> None:
        """Agent tool_use in assistant content maps to an agents row."""
        agent_entry = {
            "type": "assistant",
            "timestamp": "2026-01-01T10:00:10.000Z",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [{
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {"model": "claude-haiku-4-5", "effort": "low",
                              "subagent_type": "Explore", "description": "x", "prompt": "y"},
                }],
                "usage": {"input_tokens": 10, "output_tokens": 5,
                          "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
            },
        }
        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as tmp:
            tmp.write(_jsonl([agent_entry]))
            tmp_path = tmp.name
        try:
            meta = extract_metadata(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        self.assertEqual(len(meta["agents"]), 1)
        a = meta["agents"][0]
        self.assertEqual(a["model"], "claude-haiku-4-5")
        self.assertEqual(a["effort"], "low")
        self.assertEqual(a["tools"], "Explore")

        con = _mem_db()
        sid = upsert_session(con, "p/x.jsonl", "-p", "hash", meta)
        insert_agents(con, sid, meta["agents"])
        con.commit()
        row = con.execute("SELECT model,effort,tools FROM agents WHERE session_id=?", (sid,)).fetchone()
        self.assertEqual(row, ("claude-haiku-4-5", "low", "Explore"))


class TestCostComputation(unittest.TestCase):
    """Token counts plus pricing table produce the correct cost_usd."""

    def test_cost_computation(self) -> None:
        """Known token counts for claude-sonnet-4-6 yield the expected USD cost."""
        # sonnet-4-6: 3.0/15.0/3.75/0.3 per 1M tokens
        cost = compute_cost("claude-sonnet-4-6", 1_000_000, 0, 0, 0)
        self.assertAlmostEqual(cost, 3.0)

        cost2 = compute_cost("claude-sonnet-4-6", 0, 1_000_000, 0, 0)
        self.assertAlmostEqual(cost2, 15.0)

        cost3 = compute_cost("unknown-model", 1_000_000, 0, 0, 0)
        self.assertAlmostEqual(cost3, 3.0)  # _default rate


class TestGroupSessions(unittest.TestCase):
    """Sessions are grouped by project and title prefix."""

    def _make_item(self, project: str, title: str) -> tuple:
        meta = {"ai_title": title}
        return (Path(f"/tmp/{project}/x.jsonl"), f"{project}/x.jsonl", project, "hash", meta)

    def test_same_project_groups_together(self) -> None:
        """Two sessions with the same 3-word title prefix land in one batch."""
        items = [self._make_item("-proj", "Fix auth bug"), self._make_item("-proj", "Fix auth bug")]
        batches = group_sessions(items)
        self.assertEqual(sum(len(b) for b in batches), 2)
        self.assertEqual(len(batches), 1)

    def test_different_project_separate_batch(self) -> None:
        """Sessions from different projects are in different batches."""
        items = [self._make_item("-proj-a", "Work"), self._make_item("-proj-b", "Work")]
        batches = group_sessions(items)
        self.assertEqual(len(batches), 2)

    def test_same_title_prefix_subgroups(self) -> None:
        """Sessions with the same 3-word title prefix land in the same sub-batch."""
        items = [
            self._make_item("-proj", "Fix auth bug one"),
            self._make_item("-proj", "Fix auth bug two"),
            self._make_item("-proj", "Add feature X"),
        ]
        batches = group_sessions(items)
        # "fix auth bug" and "add feature x" are different prefixes → 2 batches
        self.assertEqual(len(batches), 2)

    def test_batch_size_limit(self) -> None:
        """Batches are capped at MAX_BATCH sessions."""
        items = [self._make_item("-proj", "Same prefix title") for _ in range(MAX_BATCH + 2)]
        batches = group_sessions(items)
        self.assertTrue(all(len(b) <= MAX_BATCH for b in batches))


class TestTruncateTranscript(unittest.TestCase):
    """Transcript truncation based on approximate token count."""

    def _short_jsonl(self, tmp: str) -> Path:
        p = Path(tmp) / "short.jsonl"
        _write_jsonl(p, [_USER, _ASSISTANT])
        return p

    def _long_jsonl(self, tmp: str) -> Path:
        long_text = "x" * (TRANSCRIPT_TOKEN_LIMIT * 4 * 3)  # ~3× the limit
        turns = []
        for i in range(10):
            turns.append({"type": "user", "timestamp": f"2026-01-01T{i:02d}:00:00.000Z",
                          "message": {"content": [{"type": "text", "text": long_text}]}})
            turns.append({"type": "assistant", "timestamp": f"2026-01-01T{i:02d}:00:05.000Z",
                          "message": {"model": "m", "content": [{"type": "text", "text": long_text}],
                                      "usage": {"input_tokens": 0, "output_tokens": 0,
                                                "cache_creation_input_tokens": 0,
                                                "cache_read_input_tokens": 0}}})
        p = Path(tmp) / "long.jsonl"
        _write_jsonl(p, turns)
        return p

    def test_short_session_full_text(self) -> None:
        """Sessions under 6k tokens include the full transcript."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._short_jsonl(tmp)
            transcript = _build_transcript(p)
            self.assertNotIn("omitted", transcript)

    def test_long_session_truncated(self) -> None:
        """Sessions over 6k tokens get first 2 + last 2 turns with omission marker."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._long_jsonl(tmp)
            transcript = _build_transcript(p)
            self.assertIn("omitted", transcript)
            turns = _extract_turns(p)
            # First 2 and last 2 turn texts should appear
            self.assertIn(turns[0].split(": ", 1)[1][:20], transcript)
            self.assertIn(turns[-1].split(": ", 1)[1][:20], transcript)


class TestParseLLMResponse(unittest.TestCase):
    """LLM response parsing handles JSON, fenced code, and errors."""

    def test_valid_json(self) -> None:
        """Plain JSON is parsed to a dict."""
        data = parse_llm_response('{"summary_text": "hi", "completed_tasks": []}')
        self.assertEqual(data["summary_text"], "hi")

    def test_fenced_json(self) -> None:
        """JSON wrapped in markdown fences is extracted and parsed."""
        data = parse_llm_response('Here you go:\n```json\n{"summary_text": "ok"}\n```')
        self.assertEqual(data["summary_text"], "ok")

    def test_invalid_json_raises(self) -> None:
        """Text with no JSON object raises ValueError."""
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            parse_llm_response("Sorry, I can't help with that.")


class TestSecondPassTriggered(unittest.TestCase):
    """needs_full_context triggers a second claude -p call."""

    def test_second_pass_triggered(self) -> None:
        """When first response has needs_full_context, a second call is made."""
        uuid = "aaaa-bbbb"
        first_response = json.dumps({
            "needs_full_context": [uuid],
            "summary_text": "", "completed_tasks": [],
            "incomplete_tasks": [], "improvement_suggestions": [], "unusual_flags": [],
        })
        second_response = json.dumps({
            "summary_text": "Full pass done.", "completed_tasks": [],
            "incomplete_tasks": [], "improvement_suggestions": [], "unusual_flags": [],
        })

        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "sessions" / "-proj"
            proj_dir.mkdir(parents=True)
            queue_dir = Path(tmp) / "queue"
            queue_dir.mkdir()
            f = proj_dir / f"{uuid}.jsonl"
            _write_jsonl(f, [_USER, _ASSISTANT])
            con = _mem_db()

            with patch("session_summarize.call_claude", side_effect=[first_response, second_response]) as mock_call:
                _process_batch(
                    [(f, f"{f.parent.name}/{f.name}", "-proj", "hash", extract_metadata(f))],
                    queue_dir, con, Path(tmp) / "claude", "2026-01-01T00:00:00+00:00", False,
                )
                self.assertEqual(mock_call.call_count, 2, "second pass must fire")


class TestDBWrites(unittest.TestCase):
    """DB rows are written correctly after a summarize run."""

    def test_db_writes(self) -> None:
        """sessions, summaries, and session_summary_items rows are created."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "sessions" / "-proj"
            proj_dir.mkdir(parents=True)
            queue_dir = Path(tmp) / "queue"
            queue_dir.mkdir()
            f = proj_dir / "uuid-1234.jsonl"
            _write_jsonl(f, [_USER, _ASSISTANT])
            con = _mem_db()

            with patch("session_summarize.call_claude", return_value=_GOOD_LLM_JSON):
                _process_batch(
                    [(f, f"-proj/{f.name}", "-proj", "hash", extract_metadata(f))],
                    queue_dir, con, Path(tmp) / "claude", "2026-01-01T00:00:00+00:00", True,
                )

            self.assertEqual(con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM summaries").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM session_summary_items").fetchone()[0], 1)
            summary = con.execute("SELECT summary_text FROM summaries").fetchone()
            self.assertEqual(summary[0], "Did some work.")


class TestApplyEachActionType(unittest.TestCase):
    """Each of the 5 action_type values writes to the correct path."""

    def _make_finding(self, action: str, target: str) -> dict:
        return {
            "category": "Friction", "action_type": action,
            "description": f"test {action}", "target": target,
            "content": f"# content for {action}", "confidence": 95,
        }

    def test_apply_each_action_type(self) -> None:
        """All 5 action types write to their expected destination paths."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create a git root so Skill/Hook and CLAUDE.local.md can resolve
            git_root = root / "repo"
            (git_root / ".git").mkdir(parents=True)
            claude_dir = root / "claude"
            claude_dir.mkdir()

            project = "-test-repo"
            workspace = str(git_root)

            findings = [
                self._make_finding("CLAUDE.md", "CLAUDE.md"),
                self._make_finding("Rules", "python.md"),
                self._make_finding("Memory", "user_role.md"),
                self._make_finding("Skill/Hook", "my-skill.md"),
                self._make_finding("CLAUDE.local.md", "CLAUDE.local.md"),
            ]

            con = _mem_db()
            _, _, _ = write_summary(con, [], {
                "summary_text": "", "completed_tasks": [], "incomplete_tasks": [],
                "improvement_suggestions": findings, "unusual_flags": [],
            }, "2026-01-01T00:00:00+00:00")
            con.commit()
            summary_id = con.execute("SELECT id FROM summaries").fetchone()[0]

            apply_improvements(con, summary_id, findings, project, workspace,
                               claude_dir, "2026-01-01T00:00:00+00:00", dry_run=False)

            self.assertTrue((git_root / "CLAUDE.md").exists(), "CLAUDE.md")
            self.assertTrue((claude_dir / "rules" / "python.md").exists(), "Rules")
            self.assertTrue((claude_dir / "projects" / project / "memory" / "user_role.md").exists(), "Memory")
            self.assertTrue((git_root / ".superpowers" / "01-specs" / "my-skill.md").exists(), "Skill/Hook")
            self.assertTrue((git_root / "CLAUDE.local.md").exists(), "CLAUDE.local.md")


class TestDryRun(unittest.TestCase):
    """--dry-run skips file writes but DB is still updated."""

    def test_dry_run(self) -> None:
        """With dry_run=True, no files are written; summaries row is inserted."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "sessions" / "-proj"
            proj_dir.mkdir(parents=True)
            queue_dir = Path(tmp) / "queue"
            queue_dir.mkdir()
            claude_dir = Path(tmp) / "claude"
            claude_dir.mkdir()
            f = proj_dir / "dry-run.jsonl"
            _write_jsonl(f, [_USER, _ASSISTANT])
            con = _mem_db()

            with patch("session_summarize.call_claude", return_value=_GOOD_LLM_JSON):
                _process_batch(
                    [(f, f"-proj/{f.name}", "-proj", "hash", extract_metadata(f))],
                    queue_dir, con, claude_dir, "2026-01-01T00:00:00+00:00", dry_run=True,
                )

            # DB updated
            self.assertEqual(con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM summaries").fetchone()[0], 1)
            # No CLAUDE.md written
            self.assertFalse((claude_dir / "CLAUDE.md").exists(), "CLAUDE.md must not be written on dry-run")


if __name__ == "__main__":
    unittest.main()
