"""Python Playwright e2e tests for session-dashboard.html."""
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

DASHBOARD = (
    Path(__file__).parent
    / "../../scaffolding-sdlc/templates/claude/session-dashboard.html"
).resolve()
DASHBOARD_URL = DASHBOARD.as_uri()

NOW_MS = int(time.time() * 1000)
ONE_HOUR_MS = 3_600_000


def _make_session(
    uuid: str,
    project: str = "myproject",
    title: str = "Test session",
    *,
    tools: list[str] | None = None,
    skills: list[str] | None = None,
    ts: int | None = None,
) -> dict:
    """Build a minimal session dict for injection into the dashboard.

    Args:
        uuid: Session UUID string.
        project: Project name; becomes projectLabel and projectNorm.
        title: Session title shown in the table.
        tools: Tool names used. Defaults to ["Bash", "Read"].
        skills: Skill names used. Defaults to empty list.
        ts: Start timestamp in milliseconds. Defaults to one hour ago.

    Returns:
        Session dict matching the shape of allSessions elements.
    """
    ts = ts or NOW_MS - ONE_HOUR_MS
    return {
        "uuid": uuid,
        "project": f"-Users-user-{project}",
        "projectLabel": project,
        "projectNorm": project,
        "projectWorktree": None,
        "title": title,
        "name": None,
        "startedAt": ts,
        "lastActivityAt": ts + 60_000,
        "model": "sonnet-4-5",
        "color": None,
        "usage": {"in": 1000, "out": 500, "cw": 0, "cr": 0},
        "userTurns": [{"role": "user", "text": f"first turn for {title}", "ts": ts}],
        "commands": [],
        "queueItems": [],
        "claudeTasks": [],
        "lastAssistantText": f"assistant reply for {title}",
        "prLinks": [],
        "tools": tools or ["Bash", "Read"],
        "skills": skills or [],
        "agents": [],
    }


def _inject(page: Page, sessions: list[dict]) -> None:
    """Inject sessions into the dashboard and trigger a render.

    Converts numeric timestamps to Date objects as the dashboard expects.

    Args:
        page: Playwright page with the dashboard loaded.
        sessions: Session dicts from _make_session.
    """
    page.evaluate(
        """sessions => {
            allSessions = sessions.map(s => ({
                ...s,
                startedAt: s.startedAt ? new Date(s.startedAt) : null,
                lastActivityAt: s.lastActivityAt ? new Date(s.lastActivityAt) : null,
                userTurns: s.userTurns.map(t => ({...t, ts: t.ts ? new Date(t.ts) : null})),
            }));
            showLanding(false);
            showReloadAs('↻ Reload', () => {});
            render();
            // render() calls style.display='' which removes any inline style,
            // but the CSS rule '#search{display:none}' still wins. Force visible.
            document.getElementById('search').style.display = 'inline-block';
        }""",
        sessions,
    )


@pytest.fixture()
def dash(page: Page) -> Page:
    """Load the dashboard as a file:// URL and wait for tryAutoLoad to settle.

    tryAutoLoad() is async and calls showLanding(true) when no IndexedDB
    handles exist (always the case in tests). It sets #status text when done.
    Waiting for that text ensures _inject()'s showLanding(false) call is not
    subsequently overridden by tryAutoLoad's async callbacks.

    Args:
        page: Playwright page fixture.

    Returns:
        Page with the dashboard loaded and tryAutoLoad complete.
    """
    page.goto(DASHBOARD_URL)
    page.wait_for_function(
        "!!document.getElementById('status')?.textContent?.trim()"
    )
    return page


# ── Landing ──────────────────────────────────────────────────────────────────

def test_landing_shown_initially(dash: Page) -> None:
    expect(dash.locator("#landing")).to_be_visible()


def test_landing_hidden_after_inject(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    expect(dash.locator("#landing")).to_be_hidden()


# ── Session rows ─────────────────────────────────────────────────────────────

def test_sessions_appear_after_inject(dash: Page) -> None:
    _inject(dash, [
        _make_session("aaa-111", title="Alpha session"),
        _make_session("bbb-222", title="Beta session"),
    ])
    expect(dash.locator("tr.srow")).to_have_count(2)


def test_row_shows_session_title(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111", title="My special session")])
    expect(dash.locator("tr.srow")).to_contain_text("My special session")


# ── Search ───────────────────────────────────────────────────────────────────

def test_search_filters_rows(dash: Page) -> None:
    _inject(dash, [
        _make_session("aaa-111", title="Fix the bug"),
        _make_session("bbb-222", title="Write the docs"),
    ])
    dash.fill("#search", "bug")
    dash.wait_for_timeout(100)
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Fix the bug")


def test_search_matches_assistant_text(dash: Page) -> None:
    s = _make_session("aaa-111", title="Generic title")
    s["lastAssistantText"] = "unique_assistant_keyword"
    _inject(dash, [s, _make_session("bbb-222", title="Other session")])
    dash.fill("#search", "unique_assistant_keyword")
    dash.wait_for_timeout(100)
    expect(dash.locator("tr.srow")).to_have_count(1)


# ── Filter icon ───────────────────────────────────────────────────────────────

def test_filter_icon_absent_without_filters(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    expect(dash.locator("#filterInfo")).to_be_empty()


def test_filter_icon_shows_after_search(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111", title="searchable")])
    dash.fill("#search", "searchable")
    dash.wait_for_timeout(100)
    expect(dash.locator("#filterInfo .fi")).to_be_visible()


def test_filter_icon_count_label(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    dash.fill("#search", "anything")
    dash.wait_for_timeout(100)
    expect(dash.locator("#filterInfo .fi")).to_contain_text("1 filter")


# ── Clear all filters ─────────────────────────────────────────────────────────

def test_clear_all_removes_filter_icon(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    dash.fill("#search", "anything")
    dash.wait_for_timeout(100)
    dash.locator("#clearAll").click()
    expect(dash.locator("#filterInfo")).to_be_empty()


def test_clear_all_restores_rows(dash: Page) -> None:
    _inject(dash, [
        _make_session("aaa-111", title="Alpha"),
        _make_session("bbb-222", title="Beta"),
    ])
    dash.fill("#search", "Alpha")
    dash.wait_for_timeout(100)
    expect(dash.locator("tr.srow")).to_have_count(1)
    dash.locator("#clearAll").click()
    expect(dash.locator("tr.srow")).to_have_count(2)


# ── Expandable rows ───────────────────────────────────────────────────────────

def test_clicking_row_expands_detail(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111", title="Expandable")])
    dash.locator("tr.srow").first.click()
    expect(dash.locator("tr.detail-row")).to_be_visible()


def test_detail_row_contains_turn_text(dash: Page) -> None:
    s = _make_session("aaa-111", title="Turn session")
    s["userTurns"] = [{"role": "user", "text": "distinctive turn content", "ts": NOW_MS}]
    _inject(dash, [s])
    dash.locator("tr.srow").first.click()
    expect(dash.locator("tr.detail-row")).to_contain_text("distinctive turn content")


def test_clicking_expanded_row_collapses(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    row = dash.locator("tr.srow").first
    row.click()
    expect(dash.locator("tr.detail-row")).to_be_visible()
    row.click()
    expect(dash.locator("tr.detail-row")).to_have_count(0)


# ── Tooltips ──────────────────────────────────────────────────────────────────

def test_tooltip_appears_on_filter_icon_hover(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    dash.fill("#search", "anything")
    dash.wait_for_timeout(100)
    dash.locator("#filterInfo .fi").hover()
    dash.wait_for_timeout(100)
    tip = dash.locator("#tip")
    expect(tip).to_be_visible()
    expect(tip).to_contain_text("search")


def test_tooltip_hides_after_mouse_leave(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    dash.fill("#search", "anything")
    dash.wait_for_timeout(100)
    dash.locator("#filterInfo .fi").hover()
    dash.wait_for_timeout(100)
    dash.mouse.move(0, 0)
    dash.wait_for_timeout(200)
    expect(dash.locator("#tip")).to_be_hidden()


# ── Reload button ─────────────────────────────────────────────────────────────

def test_reload_button_hidden_before_data(dash: Page) -> None:
    expect(dash.locator("#reloadBtn")).to_be_hidden()


def test_reload_button_shown_after_inject(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    expect(dash.locator("#reloadBtn")).to_be_visible()


# ── Date filter ───────────────────────────────────────────────────────────────

def test_today_filter_shows_recent_sessions(dash: Page) -> None:
    recent = _make_session("aaa-111", title="Recent", ts=NOW_MS - 60_000)
    old = _make_session("bbb-222", title="Old", ts=NOW_MS - 30 * 24 * ONE_HOUR_MS)
    _inject(dash, [recent, old])
    dash.locator("[data-period='today']").click()
    dash.wait_for_timeout(100)
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Recent")


# ── Table column sort ─────────────────────────────────────────────────────────

def test_sort_by_column_header(dash: Page) -> None:
    _inject(dash, [
        _make_session("aaa-111", title="Alpha"),
        _make_session("bbb-222", title="Beta"),
    ])
    dash.locator("th[data-col='title']").click()
    dash.wait_for_timeout(100)
    rows = dash.locator("tr.srow")
    expect(rows.first).to_contain_text("Alpha")
    expect(rows.last).to_contain_text("Beta")
