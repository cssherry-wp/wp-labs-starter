"""Python Playwright e2e tests for session-dashboard.html."""

import re
import time
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.sync_api import Page, expect

DASHBOARD = (
    Path(__file__).parent / "../../scaffolding-sdlc/templates/claude/session-dashboard.html"
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
    source: str = "claude",
    account: str | None = None,
) -> dict:
    """Build a minimal session dict for injection into the dashboard.

    Args:
        uuid: Session UUID string.
        project: Project name; becomes projectLabel and projectNorm.
        title: Session title shown in the table.
        tools: Tool names used. Defaults to ["Bash", "Read"].
        skills: Skill names used. Defaults to empty list.
        ts: Start timestamp in milliseconds. Defaults to one hour ago.
        source: 'claude' or 'pi'. Defaults to 'claude'.
        account: Loaded folder name the session is attributed to, matching
            the name used in _set_dirs. Defaults to None (untagged).

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
        "source": source,
        "account": account,
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
            // Mirror what every real load path now does: allSessions is derived
            // from sessionStore, and the date-filter controls call load() via
            // ensureMonthsLoaded(). Without seeding the store and marking months
            // loaded, the first date-pill click rebuilds from an empty store and
            // wipes the injected rows.
            sessionStore = new Map(allSessions.map(s => [s.uuid, s]));
            loadedMonths.add('ALL');
            showLanding(false);
            showReloadAs('↻ Reload', () => {});
            render();
            // render() calls style.display='' which removes any inline style,
            // but the CSS rule '#search{display:none}' still wins. Force visible.
            document.getElementById('search').style.display = 'inline-block';
        }""",
        sessions,
    )


def _set_dirs(page: Page, claude_names: list[str], pi_names: list[str] | None = None) -> None:
    """Simulate loaded Claude/Pi folders and render the #dirPills filter.

    Sets fake handle objects (only `.name` is used by renderDirPills) rather
    than real FileSystemDirectoryHandle instances, which aren't available in
    a test page.

    Args:
        page: Playwright page with the dashboard loaded.
        claude_names: Folder names to simulate as loaded Claude handles.
        pi_names: Folder names to simulate as loaded Pi handles.
    """
    page.evaluate(
        """([claudeNames, piNames]) => {
            claudeHandles = claudeNames.map(name => ({name}));
            piHandles = piNames.map(name => ({name}));
            renderDirPills();
        }""",
        [claude_names, pi_names or []],
    )


def _set_period(page: Page, period: str) -> None:
    """Switch the active date filter and wait for its lazy month load to settle.

    Args:
        page: Playwright page with the dashboard loaded.
        period: A period key ('hour', 'today', 'week', 'month', 'all').
    """
    page.evaluate(
        """async period => {
            activeDateFilter = period;
            syncUrl();
            await ensureMonthsLoaded(neededMonthsForFilter());
            render();
        }""",
        period,
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
    page.wait_for_function("!!document.getElementById('status')?.textContent?.trim()")
    return page


# ── Landing ──────────────────────────────────────────────────────────────────


def test_landing_shown_initially(dash: Page) -> None:
    expect(dash.locator("#landing")).to_be_visible()


def test_landing_hidden_after_inject(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    expect(dash.locator("#landing")).to_be_hidden()


# ── Session rows ─────────────────────────────────────────────────────────────


def test_sessions_appear_after_inject(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Alpha session"),
            _make_session("bbb-222", title="Beta session"),
        ],
    )
    expect(dash.locator("tr.srow")).to_have_count(2)


def test_row_shows_session_title(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111", title="My special session")])
    expect(dash.locator("tr.srow")).to_contain_text("My special session")


# ── Search ───────────────────────────────────────────────────────────────────


def test_search_filters_rows(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Fix the bug"),
            _make_session("bbb-222", title="Write the docs"),
        ],
    )
    dash.fill("#search", "bug")
    dash.wait_for_timeout(300)
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Fix the bug")


def test_search_matches_assistant_text(dash: Page) -> None:
    s = _make_session("aaa-111", title="Generic title")
    s["lastAssistantText"] = "unique_assistant_keyword"
    _inject(dash, [s, _make_session("bbb-222", title="Other session")])
    dash.fill("#search", "unique_assistant_keyword")
    dash.wait_for_timeout(300)
    expect(dash.locator("tr.srow")).to_have_count(1)


# ── Filter icon ───────────────────────────────────────────────────────────────


def test_filter_icon_absent_with_no_filters_at_all(dash: Page) -> None:
    """Only 'All time' is a genuinely unfiltered view, so only it hides the funnel."""
    _inject(dash, [_make_session("aaa-111")])
    _set_period(dash, "all")
    expect(dash.locator("#filterInfo")).to_be_empty()


def test_default_month_window_is_reported_as_a_filter(dash: Page) -> None:
    """The 30-day default hides older sessions, so it must show in the funnel.

    Regression guard for the shift of the default from 'all' to 'month': a
    silently-filtered view is exactly the "hidden is indistinguishable from
    broken" failure the surrounding code went out of its way to avoid.
    """
    _inject(dash, [_make_session("aaa-111")])
    expect(dash.locator("#filterInfo .fi")).to_contain_text("1 filter")
    dash.locator("#filterInfo .fi").hover()
    expect(dash.locator("#tip")).to_contain_text("period: this month")


def test_filter_icon_shows_after_search(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111", title="searchable")])
    dash.fill("#search", "searchable")
    dash.wait_for_timeout(300)
    expect(dash.locator("#filterInfo .fi")).to_be_visible()


def test_filter_icon_count_label(dash: Page) -> None:
    """Search on top of the default period window counts as two filters."""
    _inject(dash, [_make_session("aaa-111")])
    dash.fill("#search", "anything")
    dash.wait_for_timeout(300)
    expect(dash.locator("#filterInfo .fi")).to_contain_text("2 filters")


# ── Clear all filters ─────────────────────────────────────────────────────────


def test_clear_all_returns_to_the_default_period(dash: Page) -> None:
    """Clear-all restores defaults, which now means the 30-day window, not 'All time'.

    Resetting to 'all' would both diverge from the state syncUrl treats as
    default and kick off an unrequested full-history scan.
    """
    _inject(dash, [_make_session("aaa-111")])
    dash.fill("#search", "anything")
    dash.wait_for_timeout(300)
    dash.locator("#clearAll").click()
    dash.wait_for_timeout(300)
    assert dash.evaluate("() => activeDateFilter") == "month"
    expect(dash.locator("#filterInfo .fi")).to_contain_text("1 filter")


def test_clear_all_does_not_write_period_to_the_url(dash: Page) -> None:
    """The post-clear state is the default, so it must round-trip as a bare URL."""
    _inject(dash, [_make_session("aaa-111")])
    dash.fill("#search", "anything")
    dash.wait_for_timeout(300)
    dash.locator("#clearAll").click()
    dash.wait_for_timeout(300)
    assert "period=" not in dash.evaluate("() => location.search")


def test_clear_all_restores_rows(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Alpha"),
            _make_session("bbb-222", title="Beta"),
        ],
    )
    dash.fill("#search", "Alpha")
    dash.wait_for_timeout(300)
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
    dash.wait_for_timeout(300)
    dash.locator("#filterInfo .fi").hover()
    dash.wait_for_timeout(300)
    tip = dash.locator("#tip")
    expect(tip).to_be_visible()
    expect(tip).to_contain_text("search")


def test_tooltip_hides_after_mouse_leave(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    dash.fill("#search", "anything")
    dash.wait_for_timeout(300)
    dash.locator("#filterInfo .fi").hover()
    dash.wait_for_timeout(300)
    dash.mouse.move(0, 0)
    dash.wait_for_timeout(200)
    expect(dash.locator("#tip")).to_be_hidden()


# ── Reload button ─────────────────────────────────────────────────────────────


def test_reload_button_hidden_before_data(dash: Page) -> None:
    expect(dash.locator("#reloadBtn")).to_be_hidden()


def test_reload_button_shown_after_inject(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    expect(dash.locator("#reloadBtn")).to_be_visible()


# ── Account filter (dirPills) ─────────────────────────────────────────────────


def test_dir_pills_render_one_per_loaded_folder(dash: Page) -> None:
    _set_dirs(dash, ["work-home", "personal-home"])
    expect(dash.locator("#dirPills .pill")).to_have_count(2)


def test_dir_pill_click_filters_table(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Work session", account="work-home"),
            _make_session("bbb-222", title="Personal session", account="personal-home"),
        ],
    )
    _set_dirs(dash, ["work-home", "personal-home"])
    expect(dash.locator("tr.srow")).to_have_count(2)
    dash.locator('[data-account="claude|work-home"]').click()
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Work session")


def test_dir_pill_click_marks_pill_active(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111", account="work-home")])
    _set_dirs(dash, ["work-home"])
    expect(dash.locator('[data-account="claude|work-home"].on')).to_have_count(0)
    dash.locator('[data-account="claude|work-home"]').click()
    expect(dash.locator('[data-account="claude|work-home"].on')).to_have_count(1)


def test_dir_pill_click_twice_clears_filter(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", account="work-home"),
            _make_session("bbb-222", account="personal-home"),
        ],
    )
    _set_dirs(dash, ["work-home", "personal-home"])
    pill = dash.locator('[data-account="claude|work-home"]')
    pill.click()
    expect(dash.locator("tr.srow")).to_have_count(1)
    pill.click()
    expect(dash.locator("tr.srow")).to_have_count(2)


def test_dir_pill_filter_shows_in_filter_icon(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111", account="work-home")])
    _set_dirs(dash, ["work-home"])
    dash.locator('[data-account="claude|work-home"]').click()
    # Account pill on top of the default period window.
    expect(dash.locator("#filterInfo")).to_contain_text("2 filters")


def test_clear_all_resets_dir_pill(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", account="work-home"),
            _make_session("bbb-222", account="personal-home"),
        ],
    )
    _set_dirs(dash, ["work-home", "personal-home"])
    dash.locator('[data-account="claude|work-home"]').click()
    expect(dash.locator("tr.srow")).to_have_count(1)
    dash.locator("#clearAll").click()
    expect(dash.locator("tr.srow")).to_have_count(2)
    expect(dash.locator('[data-account="claude|work-home"].on')).to_have_count(0)


def test_row_shows_account_label(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111", account="work-home")])
    expect(dash.locator("tr.srow")).to_contain_text("work-home")


def test_pi_dir_pill_filters_independently_of_claude(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Claude session", account="work-home", source="claude"),
            _make_session("bbb-222", title="Pi session", account="agent-box", source="pi"),
        ],
    )
    _set_dirs(dash, ["work-home"], ["agent-box"])
    dash.locator('[data-account="pi|agent-box"]').click()
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Pi session")


def test_file_input_account_gets_its_own_pill(dash: Page) -> None:
    """Sessions with no directory handle behind them are still filterable.

    The file-input fallback populates extraAccounts instead of claudeHandles,
    so renderDirPills must fold those in or the sessions become unreachable
    by any pill.
    """
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Dropped session", account="dropped-home"),
            _make_session("bbb-222", title="Handle session", account="work-home"),
        ],
    )
    dash.evaluate("() => { extraAccounts = ['claude|dropped-home']; renderDirPills(); }")
    _set_dirs(dash, ["work-home"])
    dash.evaluate("() => { extraAccounts = ['claude|dropped-home']; renderDirPills(); }")
    dash.locator('[data-account="claude|dropped-home"]').click()
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Dropped session")


# ── Session cache: month shards + index (localStorage branch) ────────────────
#
# With no analytics folder handle in IndexedDB, getAnalyticsHandle() returns
# null and the shard/index helpers fall through to localStorage, so the merge,
# bucketing, and migration logic is exercisable without mocking the File System
# Access API.


def _save_shard(page: Page, month: str, sessions: list[dict]) -> None:
    """Persist sessions into one month shard via saveCacheShard.

    Args:
        page: Playwright page with the dashboard loaded.
        month: Shard key, 'YYYY-MM'.
        sessions: Session dicts from _make_session.
    """
    _inject(page, sessions)
    page.evaluate("async month => { await saveCacheShard(month, allSessions); }", month)


def _load_shard(page: Page, month: str) -> dict[str, Any]:
    """Return one month shard's uuid -> session map.

    Args:
        page: Playwright page with the dashboard loaded.
        month: Shard key, 'YYYY-MM'.

    Returns:
        Dict keyed by uuid; empty when the shard does not exist.
    """
    return cast(
        "dict[str, Any]",
        page.evaluate("async month => await loadCacheShard(month)", month),
    )


def test_shard_round_trips_sessions(dash: Page) -> None:
    _save_shard(dash, "2026-08", [_make_session("aaa-111", account="work-home")])
    assert list(_load_shard(dash, "2026-08")) == ["aaa-111"]


def test_shard_write_does_not_leak_into_other_months(dash: Page) -> None:
    """Month-scoping is the whole point: a shard must hold only its own month."""
    _save_shard(dash, "2026-08", [_make_session("aaa-111")])
    _save_shard(dash, "2026-07", [_make_session("bbb-222")])
    assert list(_load_shard(dash, "2026-08")) == ["aaa-111"]
    assert list(_load_shard(dash, "2026-07")) == ["bbb-222"]


def test_shard_merges_across_folders_instead_of_replacing(dash: Page) -> None:
    """Saving folder B must not evict folder A's cached sessions.

    This is the regression the uuid-keyed cache exists to prevent: a per-combo
    key meant adding a folder orphaned everything scanned before it.
    """
    _save_shard(dash, "2026-08", [_make_session("aaa-111", account="work-home")])
    _save_shard(dash, "2026-08", [_make_session("bbb-222", account="personal-home")])
    assert sorted(_load_shard(dash, "2026-08")) == ["aaa-111", "bbb-222"]


def test_missing_shard_reads_as_empty_not_an_error(dash: Page) -> None:
    assert _load_shard(dash, "1999-01") == {}


def test_index_round_trips(dash: Page) -> None:
    stored = dash.evaluate(
        """async () => {
            await saveIndex({'aaa-111': {month: '2026-08', fileTs: 5, trustedLarge: true}});
            return await loadIndex();
        }"""
    )
    assert stored == {"aaa-111": {"month": "2026-08", "fileTs": 5, "trustedLarge": True}}


def test_delete_from_shard_removes_only_that_uuid(dash: Page) -> None:
    _save_shard(dash, "2026-08", [_make_session("aaa-111"), _make_session("bbb-222")])
    dash.evaluate("async () => { await deleteFromShardIfPresent('2026-08', 'aaa-111'); }")
    assert list(_load_shard(dash, "2026-08")) == ["bbb-222"]


def test_delete_from_shard_also_evicts_the_in_memory_copy(dash: Page) -> None:
    """Disk-only deletion lets a later flush write the stale entry straight back.

    Regression guard: without the in-memory eviction, a session whose startedAt
    month changed on reparse ends up duplicated across two shards.
    """
    _save_shard(dash, "2026-08", [_make_session("aaa-111")])
    remaining = dash.evaluate(
        """async () => {
            const shards = new Map([['2026-08', new Map([['aaa-111', {uuid: 'aaa-111'}]])]]);
            await deleteFromShardIfPresent('2026-08', 'aaa-111', shards);
            return [...shards.get('2026-08').keys()];
        }"""
    )
    assert remaining == []


def test_quota_exceeded_is_surfaced_in_status(dash: Page) -> None:
    """A full localStorage must not fail silently.

    The cache merges additively with no eviction, so the quota is reachable.
    Swallowing the error leaves a permanently stale cache and a full rescan on
    every load with nothing on screen to explain it.
    """
    _inject(dash, [_make_session("aaa-111", account="work-home")])
    dash.evaluate(
        """async () => {
            localStorage.setItem = () => {
                throw new DOMException('full', 'QuotaExceededError');
            };
            await saveCacheShard('2026-08', allSessions);
        }"""
    )
    expect(dash.locator("#status")).to_contain_text("browser cache full")
    expect(dash.locator("#status")).to_contain_text("2026-08")


def test_quota_exceeded_leaves_previous_shard_readable(dash: Page) -> None:
    """setItem is atomic, so a rejected write must not corrupt the old shard."""
    _save_shard(dash, "2026-08", [_make_session("aaa-111")])
    _inject(dash, [_make_session("bbb-222")])
    dash.evaluate(
        """async () => {
            localStorage.setItem = () => {
                throw new DOMException('full', 'QuotaExceededError');
            };
            await saveCacheShard('2026-08', allSessions);
        }"""
    )
    assert list(_load_shard(dash, "2026-08")) == ["aaa-111"]


# ── Legacy cache migration ────────────────────────────────────────────────────


def _seed_legacy(page: Page, sessions: list[dict]) -> None:
    """Write a pre-shard v5 blob under the legacy localStorage key.

    Args:
        page: Playwright page with the dashboard loaded.
        sessions: Session dicts from _make_session.
    """
    page.evaluate(
        """sessions => {
            const byUuid = {};
            for (const s of sessions) byUuid[s.uuid] = s;
            localStorage.setItem(
                'claude-sess-v5',
                JSON.stringify({ts: Date.now(), sessions: byUuid, accountTs: {}})
            );
        }""",
        sessions,
    )


def test_migration_buckets_legacy_sessions_by_started_at(dash: Page) -> None:
    aug = int(time.mktime((2026, 8, 14, 12, 0, 0, 0, 0, -1)) * 1000)
    _seed_legacy(dash, [_make_session("aaa-111", ts=aug)])
    index = dash.evaluate("async () => await migrateLegacyCacheIfNeeded({})")
    assert index["aaa-111"]["month"] == "2026-08"
    assert list(_load_shard(dash, "2026-08")) == ["aaa-111"]


def test_migration_runs_once_via_its_own_marker(dash: Page) -> None:
    """The gate is a marker, not "index is empty".

    A live scan can populate real entries before migration ever runs, and an
    empty-index gate would then skip migration forever.
    """
    _seed_legacy(dash, [_make_session("aaa-111")])
    index = dash.evaluate("async () => await migrateLegacyCacheIfNeeded({})")
    assert index["__migratedLegacy"] is True
    again = dash.evaluate("async () => await migrateLegacyCacheIfNeeded({__migratedLegacy: true})")
    assert "aaa-111" not in again


def test_migration_never_overwrites_a_live_scanned_entry(dash: Page) -> None:
    _seed_legacy(dash, [_make_session("aaa-111")])
    index = dash.evaluate(
        """async () => await migrateLegacyCacheIfNeeded(
            {'aaa-111': {month: '2026-01', fileTs: 99, trustedLarge: true}}
        )"""
    )
    assert index["aaa-111"]["month"] == "2026-01"
    assert index["aaa-111"]["fileTs"] == 99


def test_migration_skips_sessions_with_no_started_at(dash: Page) -> None:
    """No reliable bucket — leave it for a live scan to rediscover."""
    session = _make_session("aaa-111")
    session["startedAt"] = None
    _seed_legacy(dash, [session])
    index = dash.evaluate("async () => await migrateLegacyCacheIfNeeded({})")
    assert "aaa-111" not in index


def test_deserialize_cache_defaults_account_to_null(dash: Page) -> None:
    """Sessions cached before the account field existed must not be dropped."""
    account = dash.evaluate("() => deserializeCache([{uuid: 'aaa-111', usage: {}}])[0].account")
    assert account is None


# ── Date filter ───────────────────────────────────────────────────────────────


def test_today_filter_shows_recent_sessions(dash: Page) -> None:
    recent = _make_session("aaa-111", title="Recent", ts=NOW_MS - 60_000)
    old = _make_session("bbb-222", title="Old", ts=NOW_MS - 30 * 24 * ONE_HOUR_MS)
    _inject(dash, [recent, old])
    dash.locator("[data-period='today']").click()
    dash.wait_for_timeout(300)
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Recent")


# ── Table column sort ─────────────────────────────────────────────────────────


def test_sort_by_column_header(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Alpha"),
            _make_session("bbb-222", title="Beta"),
        ],
    )
    dash.locator("th[data-col='title']").click()
    dash.wait_for_timeout(300)
    rows = dash.locator("tr.srow")
    expect(rows.first).to_contain_text("Alpha")
    expect(rows.last).to_contain_text("Beta")


# ── Timeline drag ─────────────────────────────────────────────────────────────


def test_timeline_drag_sets_custom_date_filter(dash: Page) -> None:
    """Dragging across the timeline canvas activates the custom date filter."""
    s1 = _make_session("aaa-111", title="Old session", ts=NOW_MS - 24 * ONE_HOUR_MS)
    s2 = _make_session("bbb-222", title="Recent session", ts=NOW_MS - ONE_HOUR_MS)
    _inject(dash, [s1, s2])

    canvas = dash.locator(".tl-canvas")
    expect(canvas).to_be_visible()

    box = canvas.bounding_box()
    assert box is not None, "timeline canvas must have layout"

    # Drag across the middle of the axis row (first 24px — no session bars there)
    axis_y = box["y"] + 10
    dash.mouse.move(box["x"] + box["width"] * 0.2, axis_y)
    dash.mouse.down()
    dash.mouse.move(box["x"] + box["width"] * 0.7, axis_y)
    dash.mouse.up()
    dash.wait_for_timeout(200)

    expect(dash.locator("[data-period='custom'].on")).to_be_visible()


def test_timeline_drag_below_threshold_ignored(dash: Page) -> None:
    """A drag smaller than 0.5% of the timeline width is treated as a click, not a filter."""
    s1 = _make_session("aaa-111", title="Session", ts=NOW_MS - 2 * ONE_HOUR_MS)
    _inject(dash, [s1])

    canvas = dash.locator(".tl-canvas")
    expect(canvas).to_be_visible()

    box = canvas.bounding_box()
    assert box is not None
    # Move only 0.1% of canvas width — below the 0.5% threshold
    mid_x = box["x"] + box["width"] * 0.5
    axis_y = box["y"] + 10
    dash.mouse.move(mid_x, axis_y)
    dash.mouse.down()
    dash.mouse.move(mid_x + box["width"] * 0.001, axis_y)
    dash.mouse.up()
    dash.wait_for_timeout(200)

    # Custom period should NOT be active
    expect(dash.locator("[data-period='custom'].on")).to_have_count(0)


# ── Agent blocks ──────────────────────────────────────────────────────────────


def test_agent_block_shown_under_turn(dash: Page) -> None:
    tool_use_id = "toolu_01abc"
    s = _make_session("aaa-111", title="Agent session")
    s["userTurns"] = [
        {
            "role": "user",
            "text": "Do a search",
            "ts": NOW_MS,
            "agentSpawns": [{"toolUseId": tool_use_id, "label": "Search subagent"}],
        }
    ]
    s["agents"] = [
        {
            "agentId": "agent-xyz",
            "agentType": "claude",
            "description": "Search subagent",
            "toolUseId": tool_use_id,
            "spawnDepth": 1,
            "parentAgentId": None,
            "usage": {"in": 500, "out": 200, "cw": 0, "cr": 0},
            "model": "haiku-4-5",
            "effort": "normal",
            "tools": ["WebSearch"],
            "lastAssistantText": "Found results",
        }
    ]
    _inject(dash, [s])
    dash.locator("tr.srow").first.click()
    expect(dash.locator(".agent-block")).to_be_visible()
    expect(dash.locator(".agent-block")).to_contain_text("Search subagent")


def test_agent_block_shows_model_and_tokens(dash: Page) -> None:
    tool_use_id = "toolu_02def"
    s = _make_session("bbb-222", title="Agent with metadata")
    s["userTurns"] = [
        {
            "role": "user",
            "text": "Run agent",
            "ts": NOW_MS,
            "agentSpawns": [{"toolUseId": tool_use_id, "label": "Worker"}],
        }
    ]
    s["agents"] = [
        {
            "agentId": "agent-abc",
            "agentType": "claude",
            "description": "Worker",
            "toolUseId": tool_use_id,
            "spawnDepth": 1,
            "parentAgentId": None,
            "usage": {"in": 1000, "out": 400, "cw": 0, "cr": 0},
            "model": "haiku-4-5",
            "effort": "normal",
            "tools": ["Bash"],
            "lastAssistantText": None,
        }
    ]
    _inject(dash, [s])
    dash.locator("tr.srow").first.click()
    block = dash.locator(".agent-block")
    expect(block).to_be_visible()
    expect(block).to_contain_text("haiku-4-5")
    expect(block).to_contain_text("tok")


def test_agent_block_shows_cost(dash: Page) -> None:
    """Agent block shows a dollar cost when the model has known pricing."""
    tool_use_id = "toolu_03ghi"
    s = _make_session("ccc-333", title="Costed agent")
    s["userTurns"] = [
        {
            "role": "user",
            "text": "Run agent",
            "ts": NOW_MS,
            "agentSpawns": [{"toolUseId": tool_use_id, "label": "Priced agent"}],
        }
    ]
    s["agents"] = [
        {
            "agentId": "agent-cost",
            "agentType": "claude",
            "description": "Priced agent",
            "toolUseId": tool_use_id,
            "spawnDepth": 1,
            "parentAgentId": None,
            # large enough for cost >= $0.01 so it renders as $X.XX not $0.0000X
            "usage": {"in": 1_000_000, "out": 100_000, "cw": 0, "cr": 0},
            "model": "haiku-4-5",
            "effort": "normal",
            "tools": [],
            "lastAssistantText": None,
        }
    ]
    _inject(dash, [s])
    dash.locator("tr.srow").first.click()
    expect(dash.locator(".agent-cost")).to_be_visible()
    expect(dash.locator(".agent-cost")).to_contain_text("$")


def test_claude_footer_cost_uses_normalized_pricing(dash: Page) -> None:
    """The Claude usage-footer cost runs the full chain correctly: parseJSONL
    strips the `claude-` prefix and dated suffix so getPricing matches, and
    calcCost bills all four token buckets (in/out/cache-write/cache-read).

    Regression guard: if pricing keys regain a `claude-` prefix, normalization
    breaks, or a bucket is dropped, the footer would silently show "—" or a
    wrong dollar amount.
    """
    result = dash.evaluate(
        r"""() => {
            const line = JSON.stringify({
                type: "assistant",
                timestamp: "2026-01-01T00:00:00Z",
                message: {
                    model: "claude-sonnet-4-6-20250929",
                    usage: {
                        input_tokens: 1000000, output_tokens: 1000000,
                        cache_creation_input_tokens: 200000,
                        cache_read_input_tokens: 400000,
                    },
                    content: [{type: "text", text: "hi"}],
                },
            });
            const p = parseJSONL(line);
            return {model: p.model, cost: calcCost(p.model, p.usage, "claude")};
        }"""
    )
    assert result["model"] == "sonnet-4-6", result["model"]
    # $/MTok: in 3, out 15, cache-write 3.75 (1.25x in), cache-read 0.30
    expected = (1_000_000 * 3 + 1_000_000 * 15 + 200_000 * 3.75 + 400_000 * 0.30) / 1e6
    assert result["cost"] is not None, "Claude footer cost was null (getPricing miss)"
    assert abs(result["cost"] - expected) < 1e-9, (result["cost"], expected)


def test_agent_block_shows_tools(dash: Page) -> None:
    """Agent block shows tool names used by the agent."""
    tool_use_id = "toolu_04jkl"
    s = _make_session("ddd-444", title="Tooled agent")
    s["userTurns"] = [
        {
            "role": "user",
            "text": "Run agent",
            "ts": NOW_MS,
            "agentSpawns": [{"toolUseId": tool_use_id, "label": "Tool agent"}],
        }
    ]
    s["agents"] = [
        {
            "agentId": "agent-tools",
            "agentType": "claude",
            "description": "Tool agent",
            "toolUseId": tool_use_id,
            "spawnDepth": 1,
            "parentAgentId": None,
            "usage": {"in": 500, "out": 200, "cw": 0, "cr": 0},
            "model": "haiku-4-5",
            "effort": "normal",
            "tools": ["Bash", "Read", "Edit"],
            "lastAssistantText": None,
        }
    ]
    _inject(dash, [s])
    dash.locator("tr.srow").first.click()
    expect(dash.locator(".agent-block")).to_contain_text("Bash")


def test_agent_block_shows_effort_badge(dash: Page) -> None:
    """Effort badge appears in the agent block when effort is not 'normal'."""
    tool_use_id = "toolu_05mno"
    s = _make_session("eee-555", title="High effort agent")
    s["userTurns"] = [
        {
            "role": "user",
            "text": "Run agent",
            "ts": NOW_MS,
            "agentSpawns": [{"toolUseId": tool_use_id, "label": "Effort agent"}],
        }
    ]
    s["agents"] = [
        {
            "agentId": "agent-effort",
            "agentType": "claude",
            "description": "Effort agent",
            "toolUseId": tool_use_id,
            "spawnDepth": 1,
            "parentAgentId": None,
            "usage": {"in": 500, "out": 200, "cw": 0, "cr": 0},
            "model": "haiku-4-5",
            "effort": "high",
            "tools": [],
            "lastAssistantText": None,
        }
    ]
    _inject(dash, [s])
    dash.locator("tr.srow").first.click()
    expect(dash.locator(".agent-block")).to_contain_text("high")


# ── Month sharding helpers (pure functions) ───────────────────────────────────
#
# These are the sharding maths the whole lazy-load scheme rests on. They are
# pure, so they are cheap to pin down directly rather than only through the UI.


def _months_in_range(page: Page, from_ms: int, to_ms: int) -> list[str]:
    """Return monthsInRange()'s shard keys for a millisecond range.

    Args:
        page: Playwright page with the dashboard loaded.
        from_ms: Range start, milliseconds since epoch.
        to_ms: Range end, milliseconds since epoch.

    Returns:
        List of 'YYYY-MM' shard keys.
    """
    return cast(
        "list[str]",
        page.evaluate("([a, b]) => monthsInRange(a, b)", [from_ms, to_ms]),
    )


def _local_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    """Build a local-time epoch-milliseconds value.

    monthKey() buckets on local calendar fields, so tests must construct
    local times rather than UTC ones.

    Args:
        year: Four-digit year.
        month: Month, 1-12.
        day: Day of month.
        hour: Hour of day. Defaults to 0.
        minute: Minute. Defaults to 0.

    Returns:
        Milliseconds since the epoch.
    """
    return int(time.mktime((year, month, day, hour, minute, 0, 0, 0, -1)) * 1000)


def test_month_key_buckets_on_local_calendar_fields(dash: Page) -> None:
    key = dash.evaluate("ms => monthKey(ms)", _local_ms(2026, 8, 14, 12))
    assert key == "2026-08"


def test_months_in_range_single_month(dash: Page) -> None:
    assert _months_in_range(dash, _local_ms(2026, 8, 5), _local_ms(2026, 8, 20)) == ["2026-08"]


def test_months_in_range_spans_every_month_inclusive(dash: Page) -> None:
    assert _months_in_range(dash, _local_ms(2026, 6, 5), _local_ms(2026, 8, 20)) == [
        "2026-06",
        "2026-07",
        "2026-08",
    ]


def test_months_in_range_crosses_a_year_boundary(dash: Page) -> None:
    assert _months_in_range(dash, _local_ms(2025, 12, 31, 23), _local_ms(2026, 1, 1, 1)) == [
        "2025-12",
        "2026-01",
    ]


def test_months_in_range_ignores_time_of_day_within_one_month(dash: Page) -> None:
    """A range whose start is later in the day than its end still spans its month.

    Regression guard: normalizing only setDate(1) left the times-of-day in
    place, so this comparison inverted and the range returned no months at
    all — a timeline drag-select silently loaded nothing.
    """
    assert _months_in_range(dash, _local_ms(2026, 8, 5, 18), _local_ms(2026, 8, 20, 9)) == [
        "2026-08"
    ]


def test_months_in_range_keeps_the_final_month_across_times_of_day(dash: Page) -> None:
    """Regression guard: the end month was dropped when from-time > to-time.

    A Jun 18:00 -> Aug 09:00 drag returned only June and July, so August's
    shard was never loaded and its sessions silently vanished from the view.
    """
    assert _months_in_range(dash, _local_ms(2026, 6, 5, 18), _local_ms(2026, 8, 20, 9)) == [
        "2026-06",
        "2026-07",
        "2026-08",
    ]


def test_needed_months_for_all_is_the_all_sentinel(dash: Page) -> None:
    """'ALL' must stay a sentinel string, never a month array."""
    assert (
        dash.evaluate("() => { activeDateFilter = 'all'; return neededMonthsForFilter(); }")
        == "ALL"
    )


def test_needed_months_for_short_periods_covers_current_and_previous(
    dash: Page,
) -> None:
    """'month' is a rolling 30 days, so it can reach back into last month."""
    months = dash.evaluate("() => { activeDateFilter = 'month'; return neededMonthsForFilter(); }")
    assert months == dash.evaluate("() => defaultMonths()")
    assert len(months) in (1, 2)


def test_needed_months_for_custom_spans_the_picked_range(dash: Page) -> None:
    months = dash.evaluate(
        """([a, b]) => {
            activeDateFilter = 'custom';
            customDateFrom = a;
            customDateTo = b;
            return neededMonthsForFilter();
        }""",
        [_local_ms(2026, 6, 5), _local_ms(2026, 8, 20)],
    )
    assert months == ["2026-06", "2026-07", "2026-08"]


def test_ensure_months_loaded_is_a_noop_once_all_is_loaded(dash: Page) -> None:
    """'ALL' subsumes every month, so nothing should re-trigger a load."""
    called = dash.evaluate(
        """async () => {
            loadedMonths = new Set(['ALL']);
            let calls = 0;
            const real = load;
            load = () => { calls++; };
            await ensureMonthsLoaded(['2026-01']);
            load = real;
            return calls;
        }"""
    )
    assert called == 0


# ── Large-file trust gate ─────────────────────────────────────────────────────


def test_small_cache_entries_are_always_trusted(dash: Page) -> None:
    assert dash.evaluate("() => cacheEntryTrusted(false, 1024)") is True


def test_large_entries_are_untrusted_until_individually_verified(dash: Page) -> None:
    """Entries written under the removed 5MB read cap may be truncated.

    A stale cache cannot say which, so an oversized file re-parses until it
    has been verified under current code.
    """
    assert dash.evaluate("() => cacheEntryTrusted(false, 6 * 1024 * 1024)") is False
    assert dash.evaluate("() => cacheEntryTrusted(true, 6 * 1024 * 1024)") is True


# ── Archived / cache-only sessions ────────────────────────────────────────────


def test_orphaned_session_shows_an_archived_badge(dash: Page) -> None:
    session = _make_session("aaa-111")
    session["orphaned"] = True
    _inject(dash, [session])
    expect(dash.locator("tr.srow")).to_contain_text("· archived")


def test_live_session_has_no_archived_badge(dash: Page) -> None:
    _inject(dash, [_make_session("aaa-111")])
    expect(dash.locator("tr.srow")).not_to_contain_text("· archived")


def test_session_summaries_row_is_labeled_distinctly(dash: Page) -> None:
    """A lower-fidelity DB-backfilled row must not read as a normal session."""
    _inject(dash, [_make_session("aaa-111", source="session_summaries")])
    expect(dash.locator("tr.srow .model")).to_contain_text("Archived DB")


def test_source_pill_for_summaries_appears_only_when_such_rows_exist(
    dash: Page,
) -> None:
    """Otherwise picking 'Claude' hides them with no pill to get them back."""
    _inject(dash, [_make_session("aaa-111")])
    expect(dash.locator('[data-source="session_summaries"]')).to_have_count(0)
    _inject(dash, [_make_session("bbb-222", source="session_summaries")])
    expect(dash.locator('[data-source="session_summaries"]')).to_have_count(1)


def test_source_pill_filters_to_summaries_rows(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Live one"),
            _make_session("bbb-222", title="Backfilled one", source="session_summaries"),
        ],
    )
    dash.locator('[data-source="session_summaries"]').click()
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Backfilled one")


# ── Analytics folder permission ───────────────────────────────────────────────


def _stub_lapsed_handle(page: Page) -> None:
    """Make idbGet return a handle whose readwrite permission is not granted.

    Mirrors the common real case: FSA grants are dropped on browser restart,
    so a previously-picked folder is present in IndexedDB but unusable.

    Args:
        page: Playwright page with the dashboard loaded.
    """
    page.evaluate(
        """() => {
            analyticsHandle = null;
            window.idbGet = async () => ({
                name: 'ClaudeAnalytics',
                queryPermission: async () => 'prompt',
                requestPermission: async () => 'prompt',
            });
        }"""
    )


def test_lapsed_permission_is_detected(dash: Page) -> None:
    _stub_lapsed_handle(dash)
    assert dash.evaluate("async () => await analyticsPermissionLapsed()") is True


def test_no_stored_handle_is_not_reported_as_lapsed(dash: Page) -> None:
    """Never having picked a folder is a different state from losing access."""
    dash.evaluate("() => { analyticsHandle = null; window.idbGet = async () => null; }")
    assert dash.evaluate("async () => await analyticsPermissionLapsed()") is False


def test_lapsed_permission_warns_on_the_analytics_button(dash: Page) -> None:
    """Silently falling back to a ~5-10MB quota must be visible, not guessed at."""
    _stub_lapsed_handle(dash)
    dash.evaluate("async () => await updateAnalyticsBtn(null)")
    expect(dash.locator("#analyticsBtn")).to_have_text("⚠ Analytics")
    expect(dash.locator("#analyticsBtn")).to_have_attribute("title", re.compile("lapsed"))


def test_never_configured_shows_the_plain_setup_label(dash: Page) -> None:
    dash.evaluate("() => { analyticsHandle = null; window.idbGet = async () => null; }")
    dash.evaluate("async () => await updateAnalyticsBtn(null)")
    expect(dash.locator("#analyticsBtn")).to_have_text("⊕ Analytics")


def test_get_analytics_handle_never_prompts_for_permission(dash: Page) -> None:
    """It runs from background paths with no user gesture, where a request hangs."""
    requested = dash.evaluate(
        """async () => {
            let asked = false;
            analyticsHandle = null;
            window.idbGet = async () => ({
                name: 'ClaudeAnalytics',
                queryPermission: async () => 'prompt',
                requestPermission: async () => { asked = true; return 'granted'; },
            });
            await getAnalyticsHandle();
            return asked;
        }"""
    )
    assert requested is False


# ── Date filter does not discard loaded sessions ──────────────────────────────


def _load_from_file_input(page: Page, uuid: str, title: str) -> None:
    """Drive loadFromFileList with a synthetic directory pick.

    The real path takes a FileList from <input webkitdirectory>, which cannot
    be constructed in-page; loadFromFileList only reads `webkitRelativePath`
    and `text()`, so plain stand-ins exercise it faithfully.

    Args:
        page: Playwright page with the dashboard loaded.
        uuid: Session UUID, used as the .jsonl filename.
        title: Session title, written into the transcript's summary line.
    """
    page.evaluate(
        """async ([uuid, title]) => {
            const lines = [
                JSON.stringify({type: 'summary', summary: title}),
                JSON.stringify({
                    type: 'user',
                    timestamp: new Date().toISOString(),
                    message: {role: 'user', content: 'hello there'},
                }),
            ].join('\\n');
            await loadFromFileList([{
                webkitRelativePath: `.claude/projects/-Users-u-proj/${uuid}.jsonl`,
                text: async () => lines,
            }]);
        }""",
        [uuid, title],
    )


def test_file_input_load_populates_the_session_store(dash: Page) -> None:
    """load() rebuilds allSessions from sessionStore, so this path must seed it.

    Regression guard: the file-input fallback set allSessions directly and
    left sessionStore empty, so the first date-pill click rebuilt from an
    empty store and wiped the whole table, with no directory handle to
    rescan from and get it back.
    """
    _load_from_file_input(dash, "aaa-111", "Alpha")
    assert dash.evaluate("() => sessionStore.size") == 1
    assert dash.evaluate("() => loadedMonths.has('ALL')") is True


def test_switching_period_keeps_sessions_from_the_file_input_path(
    dash: Page,
) -> None:
    """End-to-end form of the same regression, through the real UI path."""
    _load_from_file_input(dash, "aaa-111", "Alpha")
    expect(dash.locator("tr.srow")).to_have_count(1)
    _set_period(dash, "all")
    expect(dash.locator("tr.srow")).to_have_count(1)


def test_switching_period_narrows_rather_than_empties(dash: Page) -> None:
    _inject(
        dash,
        [
            _make_session("aaa-111", title="Recent"),
            _make_session("bbb-222", title="Old", ts=NOW_MS - 300 * 24 * ONE_HOUR_MS),
        ],
    )
    _set_period(dash, "all")
    expect(dash.locator("tr.srow")).to_have_count(2)
    _set_period(dash, "today")
    expect(dash.locator("tr.srow")).to_have_count(1)
    expect(dash.locator("tr.srow")).to_contain_text("Recent")
