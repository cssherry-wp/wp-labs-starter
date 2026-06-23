from __future__ import annotations

import json

import pytest

import planner.synthesis as syn
from planner.config import LlmCfg
from planner.errors import SynthesisError


def test_extract_json_from_prose() -> None:
    text = 'Sure! Here is the result:\n{"a": 1, "b": [2,3]}\nHope that helps.'
    assert syn.extract_json(text) == {"a": 1, "b": [2, 3]}


def test_extract_json_missing_raises() -> None:
    with pytest.raises(SynthesisError):
        syn.extract_json("no json here")


def test_synthesize_daily_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    canned = json.dumps({"calls": [], "accomplishments_md": "- did x",
                         "learnings_md": "", "new_tasks": [{"text": "t", "priority": "high"}]})
    monkeypatch.setattr(syn, "run_backend", lambda cfg, prompt: canned)
    cfg = LlmCfg("claude", "claude", ["-p"], "", "")
    out = syn.synthesize_daily(cfg, "PROMPT {payload}", {"x": 1})
    assert out["new_tasks"][0]["priority"] == "high"


def test_run_backend_empty_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class P:
        returncode = 0
        stdout = "   "
        stderr = ""
    monkeypatch.setattr(syn.subprocess, "run", lambda *a, **k: P())
    with pytest.raises(SynthesisError):
        syn.run_backend(LlmCfg("claude", "claude", ["-p"], "", ""), "hi")
