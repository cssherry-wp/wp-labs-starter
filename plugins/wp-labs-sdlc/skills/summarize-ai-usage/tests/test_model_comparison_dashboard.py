"""Playwright e2e tests for model_comparison_dashboard.html.

Tests run against the dashboard template with synthetic data injected via
addInitScript so they work without a pre-generated live file.  A separate
live-file test verifies the real dashboard when results are available.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

DASHBOARD = (Path(__file__).parent.parent / "scripts" / "model_comparison_dashboard.html").resolve()
LIVE_DASHBOARD = (
    Path.home() / "ClaudeAnalytics" / "compare_models" / "model_comparison_dashboard.html"
)


# ── Synthetic data helpers ────────────────────────────────────────────────────

_DEFAULT_LEARNINGS    = ["Use git worktrees for isolation"]
_DEFAULT_IMPROVEMENTS = ["Add retry logic to API calls"]
_DEFAULT_COMPLETED    = ["Fix auth bug", "Write tests"]
_DEFAULT_INCOMPLETE   = ["Migrate DB schema"]
_DEFAULT_FLAGS        = ["Prompt-too-long error on batch 3"]


def _make_scores(total: float) -> dict:
    """Build a proportional scores dict for a given total.

    Args:
        total: Overall score (0–100).

    Returns:
        Scores dict with per-field and summary keys.
    """
    return {
        "personal_learnings":     round(total * 0.25, 1),
        "unapplied_improvements": round(total * 0.25, 1),
        "summary_text":           round(total * 0.20, 1),
        "completed_tasks":        round(total * 0.10, 1),
        "incomplete_tasks":       round(total * 0.10, 1),
        "unusual_flags":          round(total * 0.10, 1),
        "extra_bonus":            0.0,
        "miss_penalty":           0.0,
        "total":                  total,
    }


def _make_diffs(learnings: list[str], improvements: list[str]) -> dict:
    """Build placeholder diffs dict (all items treated as reference-matched).

    Args:
        learnings: Learning items to include.
        improvements: Improvement items to include.

    Returns:
        Diffs dict with empty matched/extra/missed lists for all array fields.
    """
    empty: dict = {"matched": [], "extra": [], "missed": []}
    return {
        "personal_learnings":     empty,
        "unapplied_improvements": empty,
        "completed_tasks":        empty,
        "incomplete_tasks":       empty,
        "unusual_flags":          empty,
    }


def _make_model(
    db_stem: str,
    display_name: str,
    *,
    total: float = 80.0,
    learnings: list[str] | None = None,
    improvements: list[str] | None = None,
    completed: list[str] | None = None,
    incomplete: list[str] | None = None,
    flags: list[str] | None = None,
    summary: str = "A short summary.",
    error: str = "",
    diffs: dict | None = None,
) -> dict:
    """Build a minimal model result dict matching compare_models.py output.

    Args:
        db_stem: DB filename stem (e.g. 'session_summaries').
        display_name: Human-readable model label.
        total: Total score.
        learnings: Personal learning items; uses defaults if None.
        improvements: Unapplied improvement items; uses defaults if None.
        completed: Completed task items; uses defaults if None.
        incomplete: Incomplete task items; uses defaults if None.
        flags: Unusual flag items; uses defaults if None.
        summary: Summary text.
        error: Error string (empty = no error).
        diffs: Pre-built diffs dict; auto-generated from learnings/improvements if None.

    Returns:
        Dict matching the shape of a model entry in results.json.
    """
    learn = learnings    if learnings    is not None else _DEFAULT_LEARNINGS
    improv = improvements if improvements is not None else _DEFAULT_IMPROVEMENTS
    return {
        "db_stem":       db_stem,
        "display_name":  display_name,
        "created_at":    "2026-07-30T12:00:00+00:00",
        "error":         error,
        "scores":        _make_scores(total),
        "fields": {
            "summary_text":           summary,
            "completed_tasks":        completed or _DEFAULT_COMPLETED,
            "incomplete_tasks":       incomplete or _DEFAULT_INCOMPLETE,
            "unusual_flags":          flags      or _DEFAULT_FLAGS,
            "personal_learnings":     learn,
            "unapplied_improvements": improv,
        },
        "diffs": diffs or _make_diffs(learn, improv),
    }


def _make_data(models: list[dict]) -> dict:
    """Wrap model list into the results.json top-level shape.

    Args:
        models: List of model dicts from _make_model.

    Returns:
        Dict with a 'models' key matching results.json structure.
    """
    return {"models": models}


def _inject(page: Page, data: dict) -> None:
    """Inject synthetic data before page load via addInitScript.

    Must be called before page.goto() so the script executes before
    DOMContentLoaded fires and init() reads window.__RESULTS__.

    Args:
        page: Playwright page (not yet navigated to the dashboard).
        data: Results dict from _make_data.
    """
    page.add_init_script(f"window.__RESULTS__ = {json.dumps(data)};")


def _wait_for_lb(page: Page) -> None:
    """Wait until the leaderboard has at least one row.

    Args:
        page: Playwright page with the dashboard loading.
    """
    page.wait_for_function("!!document.getElementById('lb-body')?.querySelector('tr')")


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def template_url() -> str:
    """Return the file:// URL for the dashboard template."""
    return DASHBOARD.as_uri()


@pytest.fixture()
def one_model_dash(page: Page, template_url: str) -> Page:
    """Dashboard loaded with one synthetic model (the default/reference).

    Args:
        page: Playwright page fixture.
        template_url: Template file:// URL.

    Returns:
        Page with dashboard rendered and leaderboard populated.
    """
    data = _make_data([_make_model("session_summaries", "claude-sonnet-4-6 (default)", total=93.3)])
    _inject(page, data)
    page.goto(template_url)
    _wait_for_lb(page)
    return page


@pytest.fixture()
def multi_model_dash(page: Page, template_url: str) -> Page:
    """Dashboard loaded with 3 synthetic models at different score levels.

    Args:
        page: Playwright page fixture.
        template_url: Template file:// URL.

    Returns:
        Page with dashboard rendered.
    """
    models = [
        _make_model("session_summaries", "claude-sonnet-4-6 (default)", total=93.3),
        _make_model("test_claude-haiku", "claude-haiku-4-5-20251001",   total=72.0),
        _make_model("test_Qwen3",        "omlx / Qwen3-35B",            total=55.0,
                    learnings=["Use batch processing"], improvements=[]),
    ]
    _inject(page, _make_data(models))
    page.goto(template_url)
    _wait_for_lb(page)
    return page


# ── No-data state ─────────────────────────────────────────────────────────────


def test_no_data_shown_when_results_null(page: Page, template_url: str) -> None:
    """With __RESULTS__=null the no-data panel is visible and dashboard hidden."""
    page.goto(template_url)
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#no-data")).to_be_visible()
    expect(page.locator("#dashboard")).to_be_hidden()


def test_no_data_panel_contains_command(page: Page, template_url: str) -> None:
    """No-data state shows the compare_models.py command."""
    page.goto(template_url)
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#no-data")).to_contain_text("compare_models.py")


# ── JS errors ─────────────────────────────────────────────────────────────────


def test_no_js_errors_on_load(page: Page, template_url: str) -> None:
    """Page loads without uncaught JS errors."""
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    _inject(page, _make_data([_make_model("session_summaries", "claude-sonnet-4-6 (default)")]))
    page.goto(template_url)
    page.wait_for_load_state("domcontentloaded")
    assert errors == [], f"Unexpected JS errors: {errors}"


# ── Leaderboard ───────────────────────────────────────────────────────────────


def test_leaderboard_shows_one_row(one_model_dash: Page) -> None:
    """Leaderboard renders exactly one row for a single-model dataset."""
    expect(one_model_dash.locator("#lb-body tr")).to_have_count(1)


def test_leaderboard_shows_correct_row_count(multi_model_dash: Page) -> None:
    """Leaderboard row count equals number of models in dataset."""
    expect(multi_model_dash.locator("#lb-body tr")).to_have_count(3)


def test_leaderboard_sorted_by_score_desc(multi_model_dash: Page) -> None:
    """Rows appear in descending total-score order."""
    rows = multi_model_dash.locator("#lb-body tr")
    assert "93.3" in rows.first.inner_text(), "Highest scorer should be first"
    assert "55.0" in rows.last.inner_text(), "Lowest scorer should be last"


def test_score_cells_are_non_empty(one_model_dash: Page) -> None:
    """Every score-num cell contains a numeric value."""
    for cell in one_model_dash.locator(".score-num").all():
        text = cell.inner_text().strip().lstrip("+-")
        assert text.replace(".", "", 1).isdigit(), f"Non-numeric score cell: {text!r}"


def test_scores_are_differentiated(multi_model_dash: Page) -> None:
    """Total scores are not all identical across models."""
    cells = multi_model_dash.locator("td.td-score .score-num").all()
    totals = {c.inner_text().strip() for c in cells}
    assert len(totals) > 1, f"All scores identical: {totals}"


def test_error_badge_shown_for_errored_model(page: Page, template_url: str) -> None:
    """ERR badge appears when a model has a non-empty error field."""
    models = [
        _make_model("session_summaries", "claude-sonnet-4-6 (default)"),
        _make_model("test_bad", "bad-model", error="connection refused"),
    ]
    _inject(page, _make_data(models))
    page.goto(template_url)
    _wait_for_lb(page)
    # Badge is inside a horizontally-scrollable table; check presence not viewport visibility.
    badge = page.locator(".err-badge")
    assert badge.count() >= 1, "ERR badge not found in leaderboard"
    assert badge.first.get_attribute("title") == "connection refused"


# ── Dimension tabs ────────────────────────────────────────────────────────────


def test_tab_bar_has_six_tabs(one_model_dash: Page) -> None:
    """Tab bar renders tabs for all six dimensions."""
    expect(one_model_dash.locator(".tab-btn")).to_have_count(6)


def test_first_tab_active_on_load(one_model_dash: Page) -> None:
    """Learnings tab is active (has 'on' class) on initial load."""
    cls = one_model_dash.locator(".tab-btn").first.get_attribute("class") or ""
    assert "on" in cls.split(), f"First tab not active, class={cls!r}"


def test_clicking_tab_switches_panel(one_model_dash: Page) -> None:
    """Clicking a tab makes its panel visible and hides others."""
    btn = one_model_dash.locator(".tab-btn[data-tab='unapplied_improvements']")
    btn.scroll_into_view_if_needed()
    btn.click()
    expect(one_model_dash.locator("#tp-unapplied_improvements")).to_be_visible()
    expect(one_model_dash.locator("#tp-personal_learnings")).to_be_hidden()


def test_each_tab_panel_has_content(multi_model_dash: Page) -> None:
    """Each dimension tab panel contains at least one chip or summary text."""
    for btn in multi_model_dash.locator(".tab-btn").all():
        btn.scroll_into_view_if_needed()
        btn.click()
        multi_model_dash.wait_for_timeout(50)
        panel_id = f"tp-{btn.get_attribute('data-tab')}"
        panel = multi_model_dash.locator(f"#{panel_id}")
        expect(panel).to_be_visible()
        has_content = (
            panel.locator(".item-chip").count() > 0 or panel.locator(".sum-text").count() > 0
        )
        assert has_content, f"Panel {panel_id} has no content"


# ── Item chips ────────────────────────────────────────────────────────────────


def test_default_model_items_show_as_ref(one_model_dash: Page) -> None:
    """Default model items render as 'ref' chips, not matched/extra/missed."""
    assert one_model_dash.locator(".item-chip.ref").count() >= 1
    expect(one_model_dash.locator(".item-chip.matched")).to_have_count(0)
    expect(one_model_dash.locator(".item-chip.extra")).to_have_count(0)
    expect(one_model_dash.locator(".item-chip.missed")).to_have_count(0)


def test_matched_extra_missed_chips_appear(page: Page, template_url: str) -> None:
    """Models with diff data render matched/extra/missed chips."""
    matched_diffs = {
        "personal_learnings": {
            "matched": [
                {"text": "Use git worktrees", "matched_to": "Use git worktrees", "ratio": 1.0}
            ],
            "extra":   [{"text": "New unique finding", "ratio": 0.0}],
            "missed":  [{"text": "Missed item from default"}],
        },
        "unapplied_improvements": {"matched": [], "extra": [], "missed": []},
        "completed_tasks":        {"matched": [], "extra": [], "missed": []},
        "incomplete_tasks":       {"matched": [], "extra": [], "missed": []},
        "unusual_flags":          {"matched": [], "extra": [], "missed": []},
    }
    test_model = _make_model("test_x", "test-model", total=60.0,
                             learnings=["Use git worktrees", "New unique finding"],
                             diffs=matched_diffs)
    models = [
        _make_model("session_summaries", "claude-sonnet-4-6 (default)"),
        test_model,
    ]
    _inject(page, _make_data(models))
    page.goto(template_url)
    _wait_for_lb(page)
    assert page.locator(".item-chip.matched").count() >= 1
    assert page.locator(".item-chip.extra").count() >= 1
    assert page.locator(".item-chip.missed").count() >= 1


# ── Theme toggle ─────────────────────────────────────────────────────────────


def test_theme_toggle_sets_data_theme(one_model_dash: Page) -> None:
    """Clicking the theme button sets data-theme on the root element."""
    one_model_dash.locator("#theme-btn").click()
    root_theme = one_model_dash.evaluate("document.documentElement.dataset.theme")
    assert root_theme in ("light", "dark"), f"Unexpected theme value: {root_theme!r}"


# ── Live dashboard ────────────────────────────────────────────────────────────


@pytest.mark.skipif(
    not LIVE_DASHBOARD.exists(),
    reason="Live dashboard not generated — run compare_models.py first",
)
def test_live_dashboard_loads_without_errors(page: Page) -> None:
    """Live generated dashboard (with real data) loads without JS errors."""
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(LIVE_DASHBOARD.as_uri())
    page.wait_for_load_state("domcontentloaded")
    assert errors == [], f"Unexpected JS errors: {errors}"
    assert page.locator("#lb-body tr").count() >= 1


@pytest.mark.skipif(
    not LIVE_DASHBOARD.exists(),
    reason="Live dashboard not generated — run compare_models.py first",
)
def test_live_dashboard_score_cells_numeric(page: Page) -> None:
    """Every score cell in the live dashboard contains a numeric value."""
    page.goto(LIVE_DASHBOARD.as_uri())
    _wait_for_lb(page)
    for cell in page.locator(".score-num").all():
        text = cell.inner_text().strip().lstrip("+-")
        assert text.replace(".", "", 1).isdigit(), f"Non-numeric: {text!r}"
