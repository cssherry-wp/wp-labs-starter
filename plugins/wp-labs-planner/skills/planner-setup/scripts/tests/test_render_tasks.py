from __future__ import annotations

from datetime import date, datetime

from planner.collectors.gsheet import OpenItem
from planner.render_tasks import (
    TaskRef,
    apply_open_items,
    existing_task_index,
    open_task_line,
    status_slug,
    week_end,
)


def test_week_end_is_sunday() -> None:
    # 2026-06-24 is a Wednesday; that week's Sunday is 2026-06-28
    assert week_end(date(2026, 6, 24)) == date(2026, 6, 28)


def test_status_slug_kebabs_multiword() -> None:
    assert status_slug("On Notice") == "on-notice"


def test_open_task_line_on_notice_high_priority_with_due() -> None:
    item = OpenItem(text="Give feedback", status="On Notice", carry_over_weeks=2, started_at=None)
    line = open_task_line(item, date(2026, 6, 28))
    assert line == "- [ ] Give feedback ⏫ 📅 2026-06-28 #status/on-notice (carried 2w)"


def test_open_task_line_waiting_low_priority() -> None:
    item = OpenItem(text="Ask review", status="Waiting", carry_over_weeks=0, started_at=None)
    line = open_task_line(item, date(2026, 6, 28))
    assert line == "- [ ] Ask review 🔽 #status/waiting"


def test_open_task_line_no_status_plain() -> None:
    item = OpenItem(text="New thing", status="", carry_over_weeks=0, started_at=None)
    assert open_task_line(item, date(2026, 6, 28)) == "- [ ] New thing"


def test_open_task_line_started_shows_start_date() -> None:
    item = OpenItem(text="Build", status="Started", carry_over_weeks=0,
                    started_at=datetime(2026, 1, 9, 4, 0, 0))
    line = open_task_line(item, date(2026, 6, 28))
    assert line == "- [ ] Build 🛫 2026-01-09 #status/started"


class FakeSearchVault:
    def __init__(self, rows: list[dict], fail: bool = False) -> None:
        self._rows = rows
        self._fail = fail

    def search_query(self, query: dict) -> list:
        if self._fail:
            raise RuntimeError("boom")
        return self._rows


def test_existing_task_index_keys_by_normalized_text() -> None:
    rows = [{"text": "Give feedback ⏫ #status/waiting", "path": "d/2026-06-20.md", "completed": False}]
    index = existing_task_index(FakeSearchVault(rows))
    assert "give feedback" in index
    assert index["give feedback"] == TaskRef(path="d/2026-06-20.md",
                                             text="Give feedback ⏫ #status/waiting", completed=False)


def test_existing_task_index_empty_without_search() -> None:
    assert existing_task_index(object()) == {}


def test_existing_task_index_empty_on_query_failure() -> None:
    assert existing_task_index(FakeSearchVault([], fail=True)) == {}


class RecordingVault:
    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = files or {}
        self.patches: list[tuple[str, str, str]] = []

    def exists(self, path: str) -> bool:
        return path in self.files

    def write(self, path: str, content: str) -> None:
        self.files[path] = content

    def read(self, path: str) -> str:
        return self.files[path]

    def patch_heading(self, path: str, heading: str, content: str, operation: str = "append") -> None:
        self.patches.append((path, heading, content))


def existing_task_index_stub(key: str, path: str, text: str) -> dict[str, TaskRef]:
    return {key: TaskRef(path=path, text=text, completed=False)}


def test_apply_open_items_appends_new_under_open_items() -> None:
    vault = RecordingVault()
    items = [OpenItem(text="New thing", status="", carry_over_weeks=0, started_at=None)]
    apply_open_items(vault, "daily", items, date(2026, 6, 24), index={})
    assert vault.patches == [("daily/2026-06-24.md", "Open Items", "- [ ] New thing")]
    assert vault.exists("daily/2026-06-24.md")  # stub created


def test_apply_open_items_skips_unchanged_existing() -> None:
    vault = RecordingVault({"daily/2026-06-20.md": "## TODO\n- [ ] New thing\n"})
    items = [OpenItem(text="New thing", status="", carry_over_weeks=0, started_at=None)]
    index = existing_task_index_stub("new thing", "daily/2026-06-20.md", "- [ ] New thing")
    apply_open_items(vault, "daily", items, date(2026, 6, 24), index=index)
    assert vault.patches == []  # nothing new appended
    assert vault.files["daily/2026-06-20.md"] == "## TODO\n- [ ] New thing\n"  # untouched


def test_apply_open_items_reconciles_stale_priority() -> None:
    vault = RecordingVault({"daily/2026-06-20.md": "## TODO\n- [ ] Give feedback 🔽 #status/waiting\n"})
    items = [OpenItem(text="Give feedback", status="On Notice", carry_over_weeks=1, started_at=None)]
    index = existing_task_index_stub("give feedback", "daily/2026-06-20.md",
                                     "- [ ] Give feedback 🔽 #status/waiting")
    apply_open_items(vault, "daily", items, date(2026, 6, 24), index=index)
    assert vault.patches == []  # already exists → not re-appended
    assert "⏫ 📅 2026-06-28 #status/on-notice" in vault.files["daily/2026-06-20.md"]
    assert "🔽 #status/waiting" not in vault.files["daily/2026-06-20.md"]
