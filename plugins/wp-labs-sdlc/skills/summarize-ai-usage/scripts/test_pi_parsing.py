import json, pathlib, tempfile, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from summarize_ai_usage import _is_pi_format, extract_metadata, _extract_turns

PI_LINES = [
    {"type": "model_change", "model": "llama3", "timestamp": "2026-07-30T10:00:00Z"},
    {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": "Hello Pi"}]}, "timestamp": "2026-07-30T10:00:01Z"},
    {"type": "message", "message": {"role": "assistant", "content": [{"type": "text", "text": "Hi there"}, {"type": "toolCall", "name": "bash", "arguments": {"command": "ls"}}], "model": "llama3", "usage": {"input": 10, "output": 5, "cacheWrite": 2, "cacheRead": 1}}, "timestamp": "2026-07-30T10:00:02Z"},
]
CLAUDE_LINES = [
    {"type": "system", "cwd": "/home/user"},
    {"type": "user", "message": {"content": [{"type": "text", "text": "Hello Claude"}]}, "timestamp": "2026-07-30T10:00:00Z"},
    {"type": "assistant", "message": {"model": "claude-sonnet-4-6", "usage": {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 2, "cache_read_input_tokens": 1}, "content": [{"type": "text", "text": "Hi"}]}, "timestamp": "2026-07-30T10:00:01Z"},
]

def write_jsonl(lines):
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    for line in lines:
        f.write(json.dumps(line) + '\n')
    f.close()
    return pathlib.Path(f.name)

def test_is_pi_format():
    pi_path = write_jsonl(PI_LINES)
    cl_path = write_jsonl(CLAUDE_LINES)
    assert _is_pi_format(pi_path) is True, "Pi file not detected"
    assert _is_pi_format(cl_path) is False, "Claude file wrongly detected as Pi"
    pi_path.unlink(); cl_path.unlink()

def test_extract_metadata_pi():
    pi_path = write_jsonl(PI_LINES)
    meta = extract_metadata(pi_path)
    assert meta["user_turns"] == 1
    assert meta["assistant_turns"] == 1
    assert meta["input_tokens"] == 10
    assert meta["output_tokens"] == 5
    assert meta["cache_write_tokens"] == 2
    assert meta["cache_read_tokens"] == 1
    assert meta["model"] == "llama3"
    assert meta["cost_usd"] is None, "Pi sessions must have NULL cost (no local pricing)"
    pi_path.unlink()

def test_extract_turns_pi():
    pi_path = write_jsonl(PI_LINES)
    turns = _extract_turns(pi_path)
    assert any("User" in t for t in turns)
    assert any("Assistant" in t for t in turns)
    assert any("[bash]" in t for t in turns)
    pi_path.unlink()

def test_extract_turns_pi_string_content():
    # Pi may store message.content as a plain string, not a block list.
    lines = [
        {"type": "model_change", "model": "llama3", "timestamp": "2026-07-30T10:00:00Z"},
        {"type": "message", "message": {"role": "user", "content": "just a string"},
         "timestamp": "2026-07-30T10:00:01Z"},
    ]
    p = write_jsonl(lines)
    turns = _extract_turns(p)
    assert any("just a string" in t for t in turns), "string-content turn was dropped"
    p.unlink()

def test_path_migration_prefixes_legacy_rows(tmp_path):
    from summarize_ai_usage import init_db
    db = tmp_path / "legacy.db"
    con = init_db(db)
    # Simulate a legacy unprefixed row, then re-open to trigger migration.
    con.execute("INSERT INTO sessions(path,file_hash,project) VALUES('proj/u.jsonl','h','proj')")
    con.commit(); con.close()
    con = init_db(db)
    row = con.execute("SELECT path FROM sessions").fetchone()
    assert row[0] == "claude/proj/u.jsonl", f"legacy path not migrated: {row[0]}"
    # Idempotent: second open leaves it unchanged.
    con.close(); con = init_db(db)
    assert con.execute("SELECT path FROM sessions").fetchone()[0] == "claude/proj/u.jsonl"
    con.close()

def test_scan_sessions_source(tmp_path):
    from summarize_ai_usage import scan_sessions, init_db
    proj = tmp_path / "myapp"
    proj.mkdir()
    session_file = proj / "fake-uuid.jsonl"
    session_file.write_text('\n'.join(json.dumps(l) for l in PI_LINES) + '\n')
    db_path = tmp_path / "test.db"
    con = init_db(db_path)
    items = scan_sessions(tmp_path, con, source="pi")
    assert len(items) == 1
    _, rel, _, _, meta = items[0]
    assert rel.startswith("pi/"), f"rel should start with 'pi/', got: {rel}"
    assert meta.get("source") == "pi"
    con.close()


def test_run_summarizer_routes():
    from summarize_ai_usage import run_summarizer
    import unittest.mock as mock
    with mock.patch('summarize_ai_usage.call_claude', return_value=('{"summary_text":"x","completed_tasks":[],"incomplete_tasks":[],"improvement_suggestions":[],"personal_learnings":[],"unusual_flags":[]}', {})) as m:
        text, usage = run_summarizer("prompt", "claude", "claude-sonnet-4-6")
        assert m.called
    try:
        run_summarizer("prompt", "badbackend", None)
        assert False, "should have raised"
    except ValueError:
        pass


if __name__ == "__main__":
    test_is_pi_format()
    test_extract_metadata_pi()
    test_extract_turns_pi()
    print("All Pi parsing tests passed.")
    test_scan_sessions_source(pathlib.Path(tempfile.mkdtemp()))
    print("scan_sessions source test passed.")
    test_run_summarizer_routes()
    print("run_summarizer routing test passed.")
