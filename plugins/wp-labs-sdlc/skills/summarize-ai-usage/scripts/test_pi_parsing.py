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
    pi_path.unlink()

def test_extract_turns_pi():
    pi_path = write_jsonl(PI_LINES)
    turns = _extract_turns(pi_path)
    assert any("User" in t for t in turns)
    assert any("Assistant" in t for t in turns)
    assert any("[bash]" in t for t in turns)
    pi_path.unlink()

if __name__ == "__main__":
    test_is_pi_format()
    test_extract_metadata_pi()
    test_extract_turns_pi()
    print("All Pi parsing tests passed.")
