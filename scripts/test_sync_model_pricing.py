#!/usr/bin/env python3
"""Tests for sync-model-pricing.py. Run: python3 scripts/test_sync_model_pricing.py

No network access — exercises parsing/merge logic against fixture text and
throwaway file copies, never the real fetch_pricing_table().
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "sync_model_pricing", Path(__file__).parent / "sync-model-pricing.py"
)
sync_model_pricing = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sync_model_pricing)  # type: ignore[union-attr]

FIXTURE_TABLE = """## Model pricing

The following table shows pricing for all Claude models:

| Model | Base input tokens | 5m cache writes | 1h cache writes | Cache hits and refreshes | Output tokens |
| --- | --- | --- | --- | --- | --- |
| Claude Sonnet 5 | $2 / MTok | $2.50 / MTok | $4 / MTok | $0.20 / MTok | $10 / MTok |
| Claude Opus 4.1 ([retired, except on Bedrock and Google Cloud](https://x)) | $15 / MTok | $18.75 / MTok | $30 / MTok | $1.50 / MTok | $75 / MTok |
| Claude Fable 5.1 | $10 / MTok | $12.50 / MTok | $20 / MTok | $0.25 / MTok1 | $50 / MTok |

## Cloud platform pricing

unrelated section that must not be parsed as pricing rows
"""


class SlugifyTest(unittest.TestCase):
    def test_plain_name(self) -> None:
        self.assertEqual(
            sync_model_pricing.slugify("Claude Sonnet 4.6"), "claude-sonnet-4-6"
        )

    def test_strips_markdown_link_and_parenthetical(self) -> None:
        name = (
            "Claude Opus 4.1 ([retired, except on Bedrock and Google Cloud](https://x))"
        )
        self.assertEqual(sync_model_pricing.slugify(name), "claude-opus-4-1")

    def test_dotted_minor_version(self) -> None:
        self.assertEqual(
            sync_model_pricing.slugify("Claude Fable 5.1"), "claude-fable-5-1"
        )


class ParsePricingTableTest(unittest.TestCase):
    def _parse(self, text: str) -> dict[str, tuple[float, float, float, float]]:
        # Exercises the same row-parsing logic as fetch_pricing_table() without
        # the network call: split on the same section markers, reuse slugify
        # and PRICE_RE exactly as the real function does.
        section = text.split("## Model pricing", 1)[1].split("\n## ", 1)[0]
        pricing: dict[str, tuple[float, float, float, float]] = {}
        for line in section.splitlines():
            line = line.strip()
            if (
                not line.startswith("|")
                or line.startswith("| ---")
                or line.startswith("| Model")
            ):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 6:
                continue
            model_name, base_in, cw_5m, _cw_1h, cache_read, out = cells[:6]
            prices = [
                sync_model_pricing.PRICE_RE.search(c)
                for c in (base_in, cw_5m, cache_read, out)
            ]
            if not all(prices):
                continue
            in_p, cw_p, cr_p, out_p = (float(m.group(1)) for m in prices)
            slug = sync_model_pricing.slugify(model_name)
            pricing[f"claude-{slug.removeprefix('claude-')}"] = (
                in_p,
                out_p,
                cw_p,
                cr_p,
            )
        return pricing

    def test_parses_active_and_retired_rows(self) -> None:
        pricing = self._parse(FIXTURE_TABLE)
        self.assertEqual(pricing["claude-sonnet-5"], (2.0, 10.0, 2.5, 0.2))
        self.assertEqual(pricing["claude-opus-4-1"], (15.0, 75.0, 18.75, 1.5))

    def test_strips_footnote_marker_glued_to_price(self) -> None:
        pricing = self._parse(FIXTURE_TABLE)
        self.assertEqual(pricing["claude-fable-5-1"], (10.0, 50.0, 12.5, 0.25))

    def test_stops_at_next_section(self) -> None:
        pricing = self._parse(FIXTURE_TABLE)
        self.assertEqual(len(pricing), 3)


class MergePythonPricingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkstemp(suffix=".py")[1])
        self.tmp.write_text(
            "PRICING: dict[str, tuple[float, float, float, float]] = {\n"
            '    "claude-opus-4": (5.0, 25.0, 6.25, 0.5),\n'
            '    "_default": (3.0, 15.0, 3.75, 0.3),\n'
            "}\n"
        )
        self._orig = sync_model_pricing.SUMMARIZE_PY
        sync_model_pricing.SUMMARIZE_PY = self.tmp

    def tearDown(self) -> None:
        sync_model_pricing.SUMMARIZE_PY = self._orig
        self.tmp.unlink(missing_ok=True)

    def test_updates_existing_and_adds_new_before_default(self) -> None:
        changed = sync_model_pricing.merge_python_pricing(
            {
                "claude-opus-4": (15.0, 75.0, 18.75, 1.5),  # correction
                "claude-sonnet-5": (2.0, 10.0, 2.5, 0.2),  # new
            }
        )
        self.assertTrue(changed)
        text = self.tmp.read_text()
        self.assertIn("15.0, 75.0, 18.75, 1.5", text)
        self.assertIn("claude-sonnet-5", text)
        # _default stays last — a downstream reader may rely on it as the fallback.
        self.assertLess(text.index("claude-sonnet-5"), text.index("_default"))

    def test_noop_when_nothing_changed(self) -> None:
        sync_model_pricing.merge_python_pricing(
            {"claude-opus-4": (15.0, 75.0, 18.75, 1.5)}
        )
        before = self.tmp.read_text()
        changed = sync_model_pricing.merge_python_pricing(
            {"claude-opus-4": (15.0, 75.0, 18.75, 1.5)}
        )
        self.assertFalse(changed)
        self.assertEqual(self.tmp.read_text(), before)


class MergeDashboardPricingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkstemp(suffix=".html")[1])
        self.tmp.write_text(
            "const PRICING={'opus-4':{in:5,cw:6.25,cr:0.50,out:25}};\nrest of file"
        )
        self._orig = sync_model_pricing.DASHBOARD_HTML
        sync_model_pricing.DASHBOARD_HTML = self.tmp

    def tearDown(self) -> None:
        sync_model_pricing.DASHBOARD_HTML = self._orig
        self.tmp.unlink(missing_ok=True)

    def test_strips_claude_prefix_and_updates_value(self) -> None:
        changed = sync_model_pricing.merge_dashboard_pricing(
            {"claude-opus-4": (15.0, 75.0, 18.75, 1.5)}
        )
        self.assertTrue(changed)
        text = self.tmp.read_text()
        self.assertIn("'opus-4':{in:15,cw:18.75,cr:1.5,out:75}", text)
        self.assertIn(
            "rest of file", text
        )  # content outside the PRICING literal survives


if __name__ == "__main__":
    unittest.main()
