"""Unit tests for summarize_ai_usage.py — LLM calls mocked, DB in :memory:."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from summarize_ai_usage import (
    MAX_BATCH,
    _MAX_TOOL_RESULT,
    _assistant_parts,
    _build_transcript,
    _extract_refs,
    _extract_turns,
    _find_project_root,
    _process_batch,
    _save_learnings_to_obsidian,
    _user_parts,
    init_db,
    _resolve_improvement_dest,
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
    from summarize_ai_usage import SCHEMA
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
                from summarize_ai_usage import sha256_file
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


class TestTranscriptExtraction(unittest.TestCase):
    """Transcript includes all turns; large tool_result blocks are trimmed."""

    def test_all_turns_included(self) -> None:
        """Every user and assistant turn appears regardless of session length."""
        entries = []
        for i in range(10):
            entries.append({"type": "user", "message": {"content": [{"type": "text", "text": f"msg {i}"}]}})
            entries.append({"type": "assistant", "message": {"model": "m", "usage": {},
                            "content": [{"type": "text", "text": f"reply {i}"}]}})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.jsonl"
            _write_jsonl(p, entries)
            transcript = _build_transcript(p)
        self.assertNotIn("omitted", transcript)
        for i in range(10):
            self.assertIn(f"msg {i}", transcript)
            self.assertIn(f"reply {i}", transcript)

    def test_tool_result_trimmed(self) -> None:
        """tool_result content longer than _MAX_TOOL_RESULT is trimmed with ellipsis."""
        long_content = "x" * (_MAX_TOOL_RESULT * 3)
        parts = _user_parts([{"type": "tool_result", "tool_use_id": "t1", "content": long_content}])
        self.assertEqual(len(parts), 1)
        self.assertIn("…", parts[0])
        self.assertLessEqual(len(parts[0]), _MAX_TOOL_RESULT + 50)  # trim + "[result: " prefix

    def test_followup_text_after_tool_result(self) -> None:
        """Text item after a tool_result in the same user turn is preserved."""
        content = [
            {"type": "tool_result", "tool_use_id": "t1", "content": "x" * (_MAX_TOOL_RESULT * 2)},
            {"type": "text", "text": "follow-up note"},
        ]
        parts = _user_parts(content)
        joined = " ".join(parts)
        self.assertIn("follow-up note", joined)

    def test_assistant_text_blocks_trimmed_independently(self) -> None:
        """Each assistant text block is trimmed independently; tool names are preserved."""
        from summarize_ai_usage import _MAX_ASST_TEXT
        content = [
            {"type": "text", "text": "a" * (_MAX_ASST_TEXT * 2)},
            {"type": "tool_use", "name": "Read"},
            {"type": "text", "text": "follow-up after tool"},
        ]
        parts = _assistant_parts(content)
        joined = " ".join(parts)
        self.assertIn("[Read]", joined)
        self.assertIn("follow-up after tool", joined)
        self.assertIn("…", joined)  # first text block was trimmed


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

            with patch("summarize_ai_usage.call_claude", side_effect=[(first_response, {}), (second_response, {})]) as mock_call:
                _process_batch(
                    [(f, f"{f.parent.name}/{f.name}", "-proj", "hash", extract_metadata(f))],
                    queue_dir, con, Path(tmp) / "claude", "2026-01-01T00:00:00+00:00", False, "claude-sonnet-4-6",
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

            with patch("summarize_ai_usage.call_claude", return_value=(_GOOD_LLM_JSON, {})):
                _process_batch(
                    [(f, f"-proj/{f.name}", "-proj", "hash", extract_metadata(f))],
                    queue_dir, con, Path(tmp) / "claude", "2026-01-01T00:00:00+00:00", True, "claude-sonnet-4-6",
                )

            self.assertEqual(con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM summaries").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM session_summary_items").fetchone()[0], 1)
            summary = con.execute("SELECT summary_text FROM summaries").fetchone()
            self.assertEqual(summary[0], "Did some work.")

    def test_first_start_last_end_populated(self) -> None:
        """first_start and last_end on summaries match the linked sessions."""
        con = _mem_db()
        sid = con.execute(
            """INSERT INTO sessions
               (path,file_hash,project,workspace,started_at,last_activity_at)
               VALUES (?,?,?,?,?,?)""",
            ("/s/f.jsonl", "h", "-p", "/w", "2026-01-01T09:00:00+00:00", "2026-01-01T11:00:00+00:00"),
        ).lastrowid
        con.commit()
        write_summary(con, [sid], {
            "summary_text": "x", "completed_tasks": [], "incomplete_tasks": [],
            "improvement_suggestions": [], "unusual_flags": [],
        }, {}, "2026-01-01T12:00:00+00:00")
        con.commit()
        row = con.execute("SELECT first_start, last_end FROM summaries").fetchone()
        self.assertEqual(row[0], "2026-01-01T09:00:00+00:00")
        self.assertEqual(row[1], "2026-01-01T11:00:00+00:00")

    def test_first_start_last_end_null_when_no_sessions(self) -> None:
        """first_start and last_end are NULL when session_ids is empty."""
        con = _mem_db()
        write_summary(con, [], {
            "summary_text": "", "completed_tasks": [], "incomplete_tasks": [],
            "improvement_suggestions": [], "unusual_flags": [],
        }, {}, "2026-01-01T00:00:00+00:00")
        con.commit()
        row = con.execute("SELECT first_start, last_end FROM summaries").fetchone()
        self.assertIsNone(row[0])
        self.assertIsNone(row[1])


class TestApplyEachActionType(unittest.TestCase):
    """apply_improvements queues high-confidence findings as brief files in pending/."""

    def _make_finding(self, action: str, target: str) -> dict:
        return {
            "category": "Friction", "action_type": action,
            "description": f"test {action}", "target": target,
            "content": f"# content for {action}", "confidence": 95,
        }

    def test_apply_queues_briefs(self) -> None:
        """High-confidence findings are written as brief .md files in ai-improvements/pending/."""
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / "claude"
            claude_dir.mkdir()
            analytics_dir = Path(tmp) / "analytics"
            analytics_dir.mkdir()
            pending_dir = analytics_dir / "ai-improvements" / "pending"

            findings = [
                self._make_finding("CLAUDE.md", "CLAUDE.md"),
                self._make_finding("Rules", "python.md"),
                self._make_finding("Memory", "user_role.md"),
            ]

            con = _mem_db()
            _, _ = write_summary(con, [], {
                "summary_text": "", "completed_tasks": [], "incomplete_tasks": [],
                "improvement_suggestions": findings, "unusual_flags": [],
            }, {}, "2026-01-01T00:00:00+00:00")
            con.commit()
            summary_id = con.execute("SELECT id FROM summaries").fetchone()[0]

            queued, unapplied = apply_improvements(
                con, summary_id, findings, "-test-repo", None,
                claude_dir, "2026-01-01T00:00:00+00:00", apply_changes=True,
                analytics_dir=analytics_dir,
            )

            self.assertEqual(len(queued), 3)
            self.assertEqual(len(unapplied), 0)
            briefs = list(pending_dir.glob("*.md"))
            self.assertEqual(len(briefs), 3)
            # Brief content includes the action_type and target
            text = briefs[0].read_text(encoding="utf-8")
            self.assertIn("action_type:", text)
            self.assertIn("target:", text)

    def test_low_confidence_stays_unapplied(self) -> None:
        """Findings with confidence <= 75 are not queued even with apply_changes=True."""
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp) / "claude"
            claude_dir.mkdir()
            findings = [{
                "category": "Friction", "action_type": "CLAUDE.md",
                "description": "low confidence finding", "target": "CLAUDE.md",
                "content": "some content", "confidence": 50,
            }]
            con = _mem_db()
            _, _ = write_summary(con, [], {
                "summary_text": "", "completed_tasks": [], "incomplete_tasks": [],
                "improvement_suggestions": findings, "unusual_flags": [],
            }, {}, "2026-01-01T00:00:00+00:00")
            con.commit()
            summary_id = con.execute("SELECT id FROM summaries").fetchone()[0]

            queued, unapplied = apply_improvements(
                con, summary_id, findings, "-proj", None,
                claude_dir, "2026-01-01T00:00:00+00:00", apply_changes=True,
            )

            self.assertEqual(len(queued), 0)
            self.assertEqual(len(unapplied), 1)


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

            with patch("summarize_ai_usage.call_claude", return_value=(_GOOD_LLM_JSON, {})):
                _process_batch(
                    [(f, f"-proj/{f.name}", "-proj", "hash", extract_metadata(f))],
                    queue_dir, con, claude_dir, "2026-01-01T00:00:00+00:00", False, "claude-sonnet-4-6",
                )

            # DB updated
            self.assertEqual(con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM summaries").fetchone()[0], 1)
            # No CLAUDE.md written
            self.assertFalse((claude_dir / "CLAUDE.md").exists(), "CLAUDE.md must not be written on dry-run")


class TestSessionsNotCommittedOnLLMFailure(unittest.TestCase):
    """Session rows are not committed when the LLM call fails (CR-008 fix)."""

    def test_session_reprocessed_after_llm_failure(self) -> None:
        """After a failed LLM call, sessions are not in the DB and are picked up on the next run."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "sessions" / "-proj"
            proj_dir.mkdir(parents=True)
            queue_dir = Path(tmp) / "queue"
            queue_dir.mkdir()
            db_path = Path(tmp) / "test.db"
            f = proj_dir / "failing.jsonl"
            _write_jsonl(f, [_USER, _ASSISTANT])

            # First run — LLM fails; connection is closed without committing
            con = init_db(db_path)
            with patch("summarize_ai_usage.call_claude", side_effect=RuntimeError("timeout")):
                _process_batch(
                    [(f, f"-proj/{f.name}", "-proj", "hash", extract_metadata(f))],
                    queue_dir, con, Path(tmp) / "claude", "2026-01-01T00:00:00+00:00", False, "claude-sonnet-4-6",
                )
            con.close()  # rolls back uncommitted session rows

            # Second run — fresh connection; scan_sessions must return the session again
            con2 = init_db(db_path)
            to_process = scan_sessions(str(proj_dir.parent), con2)
            con2.close()
            self.assertEqual(len(to_process), 1, "session must be reprocessed after LLM failure")


class TestFindProjectRootDecoding(unittest.TestCase):
    """_find_project_root decodes encoded project names to real paths."""

    def test_plain_path_decoding(self) -> None:
        """A project name with no literal hyphens decodes to the expected path."""
        with tempfile.TemporaryDirectory() as tmp:
            # Encode tmp as a project name: leading / → leading -, / → -
            encoded = tmp.replace("-", "--").replace("/", "-")
            git_dir = Path(tmp) / ".git"
            git_dir.mkdir()
            result = _find_project_root(None, encoded)
            self.assertEqual(result, tmp)

    def test_literal_hyphen_in_path(self) -> None:
        """Paths containing literal hyphens (encoded as --) decode correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create a subdir with a hyphen in its name
            hyphen_dir = Path(tmp) / "my-project"
            hyphen_dir.mkdir()
            (hyphen_dir / ".git").mkdir()
            # Encode: / → -, literal - → --
            encoded = str(hyphen_dir).replace("-", "--").replace("/", "-")
            result = _find_project_root(None, encoded)
            self.assertEqual(result, str(hyphen_dir))

    def test_workspace_takes_priority(self) -> None:
        """workspace path is tried before the decoded project name."""
        with tempfile.TemporaryDirectory() as tmp:
            ws_dir = Path(tmp) / "workspace"
            ws_dir.mkdir()
            (ws_dir / ".git").mkdir()
            result = _find_project_root(str(ws_dir), "-nonexistent-path")
            self.assertEqual(result, str(ws_dir))


class TestResolveImprovementDestPathTraversal(unittest.TestCase):
    """_resolve_improvement_dest strips path traversal from LLM-supplied targets."""

    def test_traversal_stripped_rules(self) -> None:
        """../../.bashrc target is reduced to .bashrc inside the rules dir."""
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp)
            dest = _resolve_improvement_dest("Rules", "../../.bashrc", None, claude_dir, "-proj")
            self.assertIsNotNone(dest)
            self.assertEqual(dest.name, ".bashrc")
            self.assertTrue(str(dest).startswith(str(claude_dir / "rules")))

    def test_traversal_stripped_memory(self) -> None:
        """../../etc/passwd target is reduced to passwd inside the memory dir."""
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp)
            dest = _resolve_improvement_dest("Memory", "../../etc/passwd", None, claude_dir, "-proj")
            self.assertIsNotNone(dest)
            self.assertEqual(dest.name, "passwd")
            self.assertTrue("memory" in str(dest))

    def test_plain_basename_unchanged(self) -> None:
        """A plain basename is passed through without modification."""
        with tempfile.TemporaryDirectory() as tmp:
            claude_dir = Path(tmp)
            dest = _resolve_improvement_dest("Rules", "python.md", None, claude_dir, "-proj")
            self.assertIsNotNone(dest)
            self.assertEqual(dest.name, "python.md")


class TestPersonalLearnings(unittest.TestCase):
    """personal_learnings is stored and grouped by category."""

    def test_learnings_stored_in_db(self) -> None:
        """personal_learnings from the LLM response is serialised into the summaries row."""
        con = _mem_db()
        learnings = [
            {"category": "Workflow", "learning": "Always grep callers before patching a shared helper."},
            {"category": "Technical", "learning": "sqlite3 ALTER TABLE silently ignores duplicate column adds."},
            {"category": "Tooling", "learning": "Use --output-format json with claude -p to get usage metadata."},
        ]
        write_summary(con, [], {
            "summary_text": "", "completed_tasks": [], "incomplete_tasks": [],
            "improvement_suggestions": [], "unusual_flags": [],
            "personal_learnings": learnings,
        }, {}, "2026-01-01T00:00:00+00:00")
        con.commit()
        raw = con.execute("SELECT personal_learnings FROM summaries").fetchone()[0]
        stored = json.loads(raw)
        self.assertEqual(len(stored), 3)
        categories = {item["category"] for item in stored}
        self.assertEqual(categories, {"Workflow", "Technical", "Tooling"})

    def test_missing_learnings_defaults_to_empty(self) -> None:
        """When the LLM omits personal_learnings, the column stores '[]'."""
        con = _mem_db()
        write_summary(con, [], {
            "summary_text": "", "completed_tasks": [], "incomplete_tasks": [],
            "improvement_suggestions": [], "unusual_flags": [],
        }, {}, "2026-01-01T00:00:00+00:00")
        con.commit()
        raw = con.execute("SELECT personal_learnings FROM summaries").fetchone()[0]
        self.assertEqual(json.loads(raw), [])

    def test_migration_adds_column_to_existing_db(self) -> None:
        """init_db adds personal_learnings to a DB that predates the column."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            # Bootstrap a DB without personal_learnings
            con = sqlite3.connect(db_path)
            con.executescript("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    summary_text TEXT
                );
            """)
            con.commit()
            con.close()
            # init_db should add the column via migration
            con2 = init_db(db_path)
            cols = {row[1] for row in con2.execute("PRAGMA table_info(summaries)")}
            con2.close()
            self.assertIn("personal_learnings", cols)
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestExtractRefs(unittest.TestCase):
    """_extract_refs preserves full URLs and deduplicates."""

    def _refs(self, lines: list[str]) -> list[str]:
        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
            for line in lines:
                f.write(json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": line}]}}) + "\n")
            path = f.name
        try:
            return _extract_refs(path)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_github_pr_url_preserved(self) -> None:
        """A full GitHub PR URL is returned verbatim."""
        url = "https://github.com/org/repo/pull/84"
        refs = self._refs([f"Created {url}"])
        self.assertIn(url, refs)

    def test_github_issue_url_preserved(self) -> None:
        """A full GitHub issue URL is returned verbatim."""
        url = "https://github.com/org/repo/issues/42"
        refs = self._refs([f"Fixes {url}"])
        self.assertIn(url, refs)

    def test_inline_only_ref_stored_as_number(self) -> None:
        """An inline '#N' ref with no URL is stored as '#N'."""
        refs = self._refs(["Closes #99"])
        self.assertIn("#99", refs)
        self.assertFalse(any("github.com" in r for r in refs))

    def test_jira_url_preserved(self) -> None:
        """A full Jira URL is returned verbatim."""
        url = "https://myorg.atlassian.net/browse/PROJ-123"
        refs = self._refs([f"See {url}"])
        self.assertIn(url, refs)

    def test_bitbucket_url_preserved(self) -> None:
        """A full Bitbucket PR URL is returned verbatim."""
        url = "https://bitbucket.org/org/repo/pull-requests/7"
        refs = self._refs([f"Review {url}"])
        self.assertIn(url, refs)

    def test_deduplication(self) -> None:
        """The same URL mentioned multiple times appears only once."""
        url = "https://github.com/org/repo/pull/5"
        refs = self._refs([f"{url} and {url} again"])
        self.assertEqual(refs.count(url), 1)

    def test_empty_file_returns_empty(self) -> None:
        """A JSONL with no refs returns an empty list."""
        refs = self._refs(["Just a normal message, no references."])
        self.assertEqual(refs, [])


class TestSaveLearningsToObsidian(unittest.TestCase):
    """_save_learnings_to_obsidian writes dated markdown to the vault directory."""

    def test_writes_file_with_all_categories(self) -> None:
        """All three categories appear as headings in the output file."""
        learnings = [
            {"category": "Workflow", "learning": "Check callers before patching shared helpers."},
            {"category": "Technical", "learning": "sqlite3 ALTER TABLE ignores duplicate columns."},
            {"category": "Tooling", "learning": "Pass --output-format json to get usage metadata."},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            obsidian_dir = Path(tmp) / "vault"
            path = _save_learnings_to_obsidian(learnings, obsidian_dir, "-myproject", "2026-01-15T10:30:00+00:00")
            self.assertIsNotNone(path)
            assert path is not None
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("## Workflow", text)
            self.assertIn("## Technical", text)
            self.assertIn("## Tooling", text)
            self.assertIn("Check callers before patching shared helpers.", text)

    def test_empty_learnings_returns_none(self) -> None:
        """Empty learnings list writes nothing and returns None."""
        with tempfile.TemporaryDirectory() as tmp:
            obsidian_dir = Path(tmp) / "vault"
            result = _save_learnings_to_obsidian([], obsidian_dir, "-proj", "2026-01-15T10:00:00+00:00")
            self.assertIsNone(result)
            self.assertFalse(obsidian_dir.exists())

    def test_creates_obsidian_dir_if_missing(self) -> None:
        """The vault directory is created when it does not exist."""
        learnings = [{"category": "Workflow", "learning": "Test learning."}]
        with tempfile.TemporaryDirectory() as tmp:
            obsidian_dir = Path(tmp) / "does" / "not" / "exist"
            path = _save_learnings_to_obsidian(learnings, obsidian_dir, "-proj", "2026-01-15T10:00:00+00:00")
            self.assertIsNotNone(path)
            self.assertTrue(obsidian_dir.exists())


if __name__ == "__main__":
    unittest.main()
