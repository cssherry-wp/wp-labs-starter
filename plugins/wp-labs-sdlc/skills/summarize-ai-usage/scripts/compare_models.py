"""compare_models.py — compare summarize-ai-usage output across multiple AI models.

Usage:
    python3 compare_models.py [--analytics-dir DIR] [--out FILE] [--default-db PATH]

Reads session_summaries.db (default run) and test_*.db files from CLAUDE_ANALYTICS_DIR,
extracts the most recent summary from each, fuzzy-diffs JSON array fields against the
default model's output, scores each model 0–100, and writes results.json.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


# ── Config ────────────────────────────────────────────────────────────────────

ANALYTICS_DIR = Path(os.environ.get("CLAUDE_ANALYTICS_DIR", Path.home() / "ClaudeAnalytics"))
DEFAULT_DB = ANALYTICS_DIR / "session_summaries.db"

FUZZY_THRESHOLD = 0.65  # SequenceMatcher ratio to call two items "matched"

# Scoring weights (sum to 100 before bonus/penalty)
WEIGHTS: dict[str, int] = {
    "personal_learnings": 25,
    "unapplied_improvements": 25,
    "summary_text": 20,
    "completed_tasks": 10,
    "incomplete_tasks": 10,
    "unusual_flags": 10,
}
EXTRA_BONUS_MAX = 5    # max bonus points for finding extra items
MISS_PENALTY = 2       # points deducted per missed item
MISS_PENALTY_CAP = 10  # max total miss penalty

MODEL_DISPLAY: dict[str, str] = {
    "session_summaries": "claude-sonnet-4-6 (default)",
    "test_claude-haiku": "claude-haiku-4-5-20251001",
    "test_Qwen3.6-35B-A3B-4bit": "omlx / Qwen3.6-35B-A3B-4bit",
    "test_Qwen3.6-35B-A3B-OptiQ-4bit": "omlx / Qwen3.6-35B-A3B-OptiQ-4bit",
    "test_gemma-4-26B-A4B-it-OptiQ-4bit": "omlx / gemma-4-26B-A4B-it-OptiQ-4bit",
    "test_Phi-4-mini-reasoning-MLX-4bit": "omlx / Phi-4-mini-reasoning-MLX-4bit",
    "test_Phi-4-mini-instruct-8bit": "omlx / Phi-4-mini-instruct-8bit",
    "test_Devstral-Small-2-24B-Instruct-2512-4bit": "omlx / Devstral-Small-2-24B-Instruct-2512-4bit",
}

_DICT_KEYS = ("text", "description", "finding", "improvement", "learning", "flag", "task")


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Summary:
    """Aggregated summary data loaded from one model's DB."""

    db_stem: str
    display_name: str
    created_at: str
    summary_text: str
    completed_tasks: list[str]
    incomplete_tasks: list[str]
    unusual_flags: list[str]
    personal_learnings: list[str]
    unapplied_improvements: list[str]
    error: str = ""


@dataclass
class ItemDiff:
    """Fuzzy-diff result for one item in a JSON array field."""

    text: str
    status: str          # "matched" | "extra" | "missed"
    match_ratio: float = 0.0
    matched_to: str = ""


@dataclass
class FieldDiff:
    """Fuzzy-diff results for all items in one field."""

    field: str
    items: list[ItemDiff] = field(default_factory=list)

    @property
    def matched(self) -> list[ItemDiff]:
        """Items that fuzzy-matched a default item."""
        return [i for i in self.items if i.status == "matched"]

    @property
    def extra(self) -> list[ItemDiff]:
        """Items found by this model but not in default."""
        return [i for i in self.items if i.status == "extra"]

    @property
    def missed(self) -> list[ItemDiff]:
        """Default items not found by this model."""
        return [i for i in self.items if i.status == "missed"]


# ── DB helpers ────────────────────────────────────────────────────────────────

def _parse_json_list(raw: str | None) -> list[str]:
    """Parse a JSON array field into a flat list of strings.

    Args:
        raw: Raw JSON string from the DB column, or None.

    Returns:
        List of string items extracted from the JSON array.
    """
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    out = []
    for item in parsed:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            for key in _DICT_KEYS:
                if key in item:
                    out.append(str(item[key]))
                    break
            else:
                out.append(json.dumps(item))
    return out


def _dedup(lst: list[str]) -> list[str]:
    """Deduplicate a list, preserving first-seen order.

    Args:
        lst: Input list, possibly containing duplicates.

    Returns:
        List with duplicates removed, original order preserved.
    """
    seen: set[str] = set()
    out = []
    for x in lst:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def get_summarized_session_paths(db_path: Path) -> set[str]:
    """Return set of session paths that appear in session_summary_items.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Set of session path strings that have at least one linked summary.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """SELECT DISTINCT s.path FROM sessions s
               JOIN session_summary_items ssi ON ssi.session_id = s.id"""
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()
    finally:
        conn.close()


def find_common_session_paths(db_paths: list[Path]) -> set[str] | None:
    """Return intersection of summarized session paths across all DBs.

    Args:
        db_paths: Paths to all DB files to intersect.

    Returns:
        Set of session paths present in every DB, or None if lookup failed for all.
    """
    sets = [get_summarized_session_paths(p) for p in db_paths]
    non_empty = [s for s in sets if s]
    if not non_empty:
        return None
    common = non_empty[0]
    for s in non_empty[1:]:
        common = common & s
    return common


def _fetch_rows_for_date(
    db_path: Path,
    date_prefix: str,
    session_paths: set[str] | None = None,
) -> list[tuple]:
    """Fetch summary rows whose created_at starts with date_prefix.

    When session_paths is provided, only summaries linked to at least one
    session in that set are returned (fair cross-model comparison).

    Args:
        db_path: Path to the SQLite database file.
        date_prefix: YYYY-MM-DD prefix to match.
        session_paths: If set, restrict to summaries covering these sessions.

    Returns:
        List of row tuples (summary_text, completed_tasks, incomplete_tasks,
        unusual_flags, personal_learnings, unapplied_improvements).
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        if session_paths:
            # Use a temp table to avoid SQLite's per-query parameter limit.
            conn.execute("CREATE TEMP TABLE IF NOT EXISTS _cmp_paths (path TEXT PRIMARY KEY)")
            conn.executemany("INSERT OR IGNORE INTO _cmp_paths VALUES (?)", [(p,) for p in session_paths])
            return conn.execute(
                """SELECT DISTINCT su.summary_text, su.completed_tasks, su.incomplete_tasks,
                          su.unusual_flags, su.personal_learnings, su.unapplied_improvements
                   FROM summaries su
                   WHERE su.created_at LIKE ?
                     AND su.id IN (
                       SELECT ssi.summary_id FROM session_summary_items ssi
                       JOIN sessions s ON s.id = ssi.session_id
                       JOIN _cmp_paths cp ON cp.path = s.path
                     )""",
                (f"{date_prefix}%",),
            ).fetchall()
        return conn.execute(
            """SELECT summary_text, completed_tasks, incomplete_tasks,
                      unusual_flags, personal_learnings, unapplied_improvements
               FROM summaries WHERE created_at LIKE ?""",
            (f"{date_prefix}%",),
        ).fetchall()
    finally:
        conn.close()


def _aggregate_rows(rows: list[tuple]) -> tuple[str, list[str], list[str], list[str], list[str], list[str]]:
    """Aggregate multiple summary rows into deduplicated lists.

    Args:
        rows: Row tuples from _fetch_rows_for_date.

    Returns:
        Tuple of (summary_text, completed_tasks, incomplete_tasks,
        unusual_flags, personal_learnings, unapplied_improvements).
    """
    texts, all_ct, all_it, all_uf, all_pl, all_ui = [], [], [], [], [], []
    for st, c, i, u, p, ui in rows:
        texts.append(st or "")
        all_ct.extend(_parse_json_list(c))
        all_it.extend(_parse_json_list(i))
        all_uf.extend(_parse_json_list(u))
        all_pl.extend(_parse_json_list(p))
        all_ui.extend(_parse_json_list(ui))
    combined_text = "\n\n".join(t for t in texts if t)
    return combined_text, _dedup(all_ct), _dedup(all_it), _dedup(all_uf), _dedup(all_pl), _dedup(all_ui)


def load_summary(db_path: Path, session_filter: set[str] | None = None) -> Summary:
    """Load and aggregate the most recent day's summaries from a DB.

    Args:
        db_path: Path to the SQLite database file.
        session_filter: If set, only include summaries linked to these session paths.

    Returns:
        Summary dataclass with aggregated data from the most recent run day.
        On any error, returns a Summary with the error field set.
    """
    stem = db_path.stem
    display = MODEL_DISPLAY.get(stem, stem)

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        latest = conn.execute(
            "SELECT created_at FROM summaries ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
    except Exception as exc:
        return Summary(stem, display, "", "", [], [], [], [], [], error=str(exc))

    if latest is None:
        return Summary(stem, display, "", "", [], [], [], [], [], error="no rows in summaries table")

    created_at = latest[0] or ""
    date_prefix = created_at[:10]  # YYYY-MM-DD

    try:
        rows = _fetch_rows_for_date(db_path, date_prefix, session_paths=session_filter)
    except Exception:
        rows = []

    if not rows:
        return Summary(stem, display, created_at, "", [], [], [], [], [], error="no rows for date")

    text, ct, it, uf, pl, ui = _aggregate_rows(rows)
    return Summary(
        db_stem=stem,
        display_name=display,
        created_at=created_at,
        summary_text=text,
        completed_tasks=ct,
        incomplete_tasks=it,
        unusual_flags=uf,
        personal_learnings=pl,
        unapplied_improvements=ui,
    )


# ── Fuzzy diff ────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Strip markdown bullets/numbers, lowercase, collapse whitespace.

    Args:
        text: Raw item text from a summary field.

    Returns:
        Normalized string suitable for fuzzy comparison.
    """
    text = re.sub(r"^[\s\-\*\d\.\)]+", "", text.strip())
    return re.sub(r"\s+", " ", text).lower().strip()


def _best_match(item: str, candidates: list[str]) -> tuple[float, str]:
    """Find the candidate with the highest fuzzy match ratio.

    Args:
        item: The item to match.
        candidates: Items to compare against.

    Returns:
        Tuple of (best_ratio, best_candidate_text).
    """
    norm_item = _normalize(item)
    best_ratio = 0.0
    best_cand = ""
    for cand in candidates:
        ratio = difflib.SequenceMatcher(None, norm_item, _normalize(cand)).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_cand = cand
    return best_ratio, best_cand


def diff_field(field_name: str, default_items: list[str], model_items: list[str]) -> FieldDiff:
    """Compute fuzzy diff between default and model items for one field.

    Args:
        field_name: Name of the field being diffed.
        default_items: Items from the default (reference) model.
        model_items: Items from the model being evaluated.

    Returns:
        FieldDiff with matched/extra/missed classifications for each item.
    """
    fd = FieldDiff(field=field_name)
    matched_default_indices: set[int] = set()

    for model_item in model_items:
        ratio, best = _best_match(model_item, default_items)
        if ratio >= FUZZY_THRESHOLD:
            try:
                matched_default_indices.add(default_items.index(best))
            except ValueError:
                pass
            fd.items.append(ItemDiff(model_item, "matched", ratio, best))
        else:
            fd.items.append(ItemDiff(model_item, "extra", ratio))

    for i, default_item in enumerate(default_items):
        if i not in matched_default_indices:
            fd.items.append(ItemDiff(default_item, "missed"))

    return fd


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score_text(summary: Summary, all_summaries: list[Summary]) -> float:
    """Score summary text length relative to median across all models.

    Args:
        summary: Model summary to score.
        all_summaries: All model summaries (used to compute median).

    Returns:
        Score in [0, WEIGHTS['summary_text']].
    """
    all_lengths = [len(s.summary_text) for s in all_summaries if s.summary_text]
    median_len = sorted(all_lengths)[len(all_lengths) // 2] if all_lengths else 1
    ratio = min(len(summary.summary_text) / max(median_len, 1), 1.5) / 1.5
    return round(ratio * WEIGHTS["summary_text"], 2)


def _score_array_fields(
    summary: Summary,
    default: Summary,
) -> tuple[dict[str, FieldDiff], dict[str, float], float, float]:
    """Score all array fields and accumulate bonus/penalty totals.

    Args:
        summary: Model summary to score.
        default: Reference (default model) summary.

    Returns:
        Tuple of (field_diffs, field_scores, total_bonus, total_miss_penalty).
    """
    candidates = {
        "personal_learnings": (summary.personal_learnings, default.personal_learnings),
        "unapplied_improvements": (summary.unapplied_improvements, default.unapplied_improvements),
        "completed_tasks": (summary.completed_tasks, default.completed_tasks),
        "incomplete_tasks": (summary.incomplete_tasks, default.incomplete_tasks),
        "unusual_flags": (summary.unusual_flags, default.unusual_flags),
    }
    field_diffs: dict[str, FieldDiff] = {}
    field_scores: dict[str, float] = {}
    total_bonus = 0.0
    total_miss_penalty = 0.0

    for fname, (model_items, default_items) in candidates.items():
        fd = diff_field(fname, default_items, model_items)
        field_diffs[fname] = fd
        weight = WEIGHTS[fname]
        default_count = max(len(default_items), 1)
        base = (len(fd.matched) / default_count) * weight
        field_scores[fname] = round(min(base, weight), 2)
        total_bonus += (len(fd.extra) / default_count) * (EXTRA_BONUS_MAX / len(candidates))
        total_miss_penalty += len(fd.missed) * MISS_PENALTY

    return field_diffs, field_scores, total_bonus, total_miss_penalty


def score_model(
    summary: Summary,
    default: Summary,
    all_summaries: list[Summary],
) -> tuple[dict[str, float], dict[str, FieldDiff]]:
    """Score a model against the default reference and return scores + diffs.

    Args:
        summary: Model summary to score.
        default: Reference summary from the default (sonnet-4-6) model.
        all_summaries: All model summaries, used for median text length.

    Returns:
        Tuple of (scores_dict, field_diffs_dict). scores_dict contains per-field
        scores plus "extra_bonus", "miss_penalty", and "total".
    """
    scores: dict[str, float] = {}
    scores["summary_text"] = _score_text(summary, all_summaries)

    field_diffs, field_scores, total_bonus, total_miss_penalty = _score_array_fields(summary, default)
    scores.update(field_scores)
    scores["extra_bonus"] = round(min(total_bonus, EXTRA_BONUS_MAX), 2)
    scores["miss_penalty"] = round(-min(total_miss_penalty, MISS_PENALTY_CAP), 2)

    raw_total = sum(v for k, v in scores.items() if k not in ("extra_bonus", "miss_penalty"))
    scores["total"] = round(max(0.0, min(100.0, raw_total + scores["extra_bonus"] + scores["miss_penalty"])), 1)

    field_diffs["summary_text"] = FieldDiff(
        field="summary_text",
        items=[ItemDiff(summary.summary_text, "matched" if summary.summary_text else "missed")],
    )
    return scores, field_diffs


# ── Orchestration ─────────────────────────────────────────────────────────────

def find_dbs(analytics_dir: Path, default_db: Path) -> list[Path]:
    """Return [default_db] followed by sorted test_*.db files.

    Args:
        analytics_dir: Directory to search for test_*.db files.
        default_db: Path to the default model's DB.

    Returns:
        Ordered list of DB paths; default_db first if it exists.
    """
    dbs = [default_db] if default_db.exists() else []
    dbs += sorted(analytics_dir.glob("test_*.db"))
    return dbs


def _model_result_dict(summary: Summary, scores: dict[str, float], field_diffs: dict[str, FieldDiff]) -> dict:
    """Serialize one model's result to a JSON-serializable dict.

    Args:
        summary: Model summary data.
        scores: Per-field and total scores.
        field_diffs: Fuzzy diff results per field.

    Returns:
        Dict suitable for JSON serialization.
    """
    return {
        "db_stem": summary.db_stem,
        "display_name": summary.display_name,
        "created_at": summary.created_at,
        "error": summary.error,
        "scores": scores,
        "fields": {
            "summary_text": summary.summary_text,
            "completed_tasks": summary.completed_tasks,
            "incomplete_tasks": summary.incomplete_tasks,
            "unusual_flags": summary.unusual_flags,
            "personal_learnings": summary.personal_learnings,
            "unapplied_improvements": summary.unapplied_improvements,
        },
        "diffs": {
            fname: {
                "matched": [{"text": i.text, "matched_to": i.matched_to, "ratio": round(i.match_ratio, 3)} for i in fd.matched],
                "extra": [{"text": i.text, "ratio": round(i.match_ratio, 3)} for i in fd.extra],
                "missed": [{"text": i.text} for i in fd.missed],
            }
            for fname, fd in field_diffs.items()
            if fname != "summary_text"
        },
    }


def build_results(analytics_dir: Path, default_db: Path) -> list[dict]:
    """Load all DBs, score each, and return serializable result dicts.

    Only summaries linked to sessions present in ALL DBs are included, so
    models are compared on the same session corpus regardless of when each
    run completed.

    Args:
        analytics_dir: Directory containing session_summaries.db and test_*.db files.
        default_db: Path to the default (sonnet-4-6) DB used as the reference.

    Returns:
        List of result dicts, one per model, ordered default-first.

    Raises:
        FileNotFoundError: If no DB files are found.
    """
    dbs = find_dbs(analytics_dir, default_db)
    if not dbs:
        raise FileNotFoundError(f"No DBs found in {analytics_dir}")

    common = find_common_session_paths(dbs)
    if common is not None:
        print(f"Common sessions across {len(dbs)} DB(s): {len(common)}")

    summaries = [load_summary(db, session_filter=common) for db in dbs]
    default_summary = summaries[0]

    results = []
    for summary in summaries:
        scores, field_diffs = score_model(summary, default_summary, summaries)
        results.append(_model_result_dict(summary, scores, field_diffs))
    return results


_SENTINEL = "if (!('__RESULTS__' in window)) window.__RESULTS__ = null; // __RESULTS_JSON__"
_TEMPLATE  = Path(__file__).parent / "model_comparison_dashboard.html"


def write_dashboard(results: list[dict], template_path: Path, out_path: Path) -> None:
    """Bake results JSON into the dashboard HTML template and write to out_path.

    Replaces the sentinel line ``window.__RESULTS__ = null; // __RESULTS_JSON__``
    with the actual JSON payload so the file is self-contained.

    Args:
        results: List of model result dicts from build_results.
        template_path: Path to the HTML template containing the sentinel.
        out_path: Destination path for the generated HTML file.

    Raises:
        FileNotFoundError: If template_path does not exist.
    """
    template = template_path.read_text()
    payload = json.dumps({"models": results}, separators=(",", ":"))
    html = template.replace(_SENTINEL, f"window.__RESULTS__ = {payload}; // __RESULTS_JSON__")
    out_path.write_text(html)


def main() -> None:
    """CLI entry point: parse args, build results, write JSON and dashboard HTML."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analytics-dir", type=Path, default=ANALYTICS_DIR,
                        help="Directory containing session DBs")
    parser.add_argument("--default-db", type=Path, default=DEFAULT_DB,
                        help="Path to the default (sonnet-4-6) DB")
    parser.add_argument("--out", type=Path,
                        help="Output JSON path (default: <analytics-dir>/compare_models/results.json)")
    parser.add_argument("--template", type=Path, default=_TEMPLATE,
                        help="Dashboard HTML template path")
    args = parser.parse_args()

    out_path = args.out or (args.analytics_dir / "compare_models" / "results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading DBs from {args.analytics_dir}...")
    results = build_results(args.analytics_dir, args.default_db)
    print(f"Scored {len(results)} model(s):")
    for r in results:
        status = f" [ERROR: {r['error']}]" if r["error"] else ""
        print(f"  {r['display_name']:<55} score={r['scores']['total']:5.1f}{status}")

    out_path.write_text(json.dumps({"models": results}, indent=2))
    print(f"\nWrote {out_path}")

    if args.template.exists():
        dash_out = out_path.parent / "model_comparison_dashboard.html"
        write_dashboard(results, args.template, dash_out)
        print(f"Wrote {dash_out}")
    else:
        print(f"Template not found at {args.template} — skipping HTML generation")


if __name__ == "__main__":
    main()
