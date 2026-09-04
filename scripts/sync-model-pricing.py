#!/usr/bin/env python3
"""Sync Claude model pricing from platform.claude.com into this repo.

Fetches the official "Model pricing" table (a plain markdown page, not a
scraped marketing page — Mintlify-style docs serve raw markdown at the
`.md` suffix) and reconciles every model row — active and retired alike —
into:

  - plugins/wp-labs-sdlc/skills/summarize-ai-usage/scripts/summarize_ai_usage.py
    (the PRICING dict; existing entries not present upstream, e.g. dated
    snapshot aliases like claude-haiku-4-5-20251001, are left untouched)
  - plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/session-dashboard.html
    (the PRICING JS object; same merge rule, "claude-" prefix stripped)

On a change, also bumps plugins/wp-labs-sdlc/.claude-plugin/plugin.json's
patch version and plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/statusline.sh's
SDLC_SOURCE_VERSION to match, per this repo's plugin-version-bump policy.

Usage: scripts/sync-model-pricing.py [--check]
  --check   exit 1 if anything would change, without writing (for CI diff detection
            when combined with `git diff --quiet` after a real run is preferred instead)

Prints "changed=true" or "changed=false" as the last line, for a workflow to key off.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

PRICING_URL = "https://platform.claude.com/docs/en/about-claude/pricing.md"

REPO_ROOT = Path(__file__).resolve().parent.parent
SUMMARIZE_PY = (
    REPO_ROOT
    / "plugins/wp-labs-sdlc/skills/summarize-ai-usage/scripts/summarize_ai_usage.py"
)
DASHBOARD_HTML = (
    REPO_ROOT
    / "plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/session-dashboard.html"
)
PLUGIN_JSON = REPO_ROOT / "plugins/wp-labs-sdlc/.claude-plugin/plugin.json"
STATUSLINE_SH = (
    REPO_ROOT
    / "plugins/wp-labs-sdlc/skills/scaffolding-sdlc/templates/claude/statusline.sh"
)

PRICE_RE = re.compile(r"\$([\d.]+)\s*/\s*MTok")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
PAREN_RE = re.compile(r"\([^)]*\)")


def slugify(name: str) -> str:
    """Turn a docs model name into this repo's id convention.

    "Claude Sonnet 4.6" -> "claude-sonnet-4-6"; "Claude Fable 5.1 (...)" ->
    "claude-fable-5-1". Matches the existing hand-written keys exactly, so
    an existing entry is recognized and updated in place, not duplicated.
    """
    name = MD_LINK_RE.sub(r"\1", name)
    name = PAREN_RE.sub("", name)
    name = name.strip().lower().replace(".", "-").replace(" ", "-")
    name = re.sub(r"-+", "-", name).strip("-")
    return name


def fetch_pricing_table() -> dict[str, tuple[float, float, float, float]]:
    """Return {slug: (input, output, cache_write_5m, cache_read)} per 1M tokens.

    Matches the 4-tuple shape summarize_ai_usage.py already uses. The docs
    table's 1h-cache-write column has no home in that shape and is dropped —
    this repo has never tracked it.
    """
    # The default urllib User-Agent gets a 403 from this host; any real UA string works.
    req = urllib.request.Request(PRICING_URL, headers={"User-Agent": "wp-labs-starter-ci"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed, trusted host
        text = resp.read().decode("utf-8")

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
        prices = [PRICE_RE.search(c) for c in (base_in, cw_5m, cache_read, out)]
        if not all(prices):
            continue  # a row with no $/MTok cells isn't a pricing row
        in_p, cw_p, cr_p, out_p = (float(m.group(1)) for m in prices)
        slug = slugify(model_name)
        if not slug.startswith("claude-"):
            slug = f"claude-{slug}"
        pricing[slug] = (in_p, out_p, cw_p, cr_p)
    if not pricing:
        raise RuntimeError("parsed zero pricing rows — docs page format likely changed")
    return pricing


def merge_python_pricing(fetched: dict[str, tuple[float, float, float, float]]) -> bool:
    """Reconcile the PRICING dict in summarize_ai_usage.py in place.

    Args:
        fetched: Slug to (input, output, cache_write, cache_read) $/MTok, as
            returned by fetch_pricing_table().

    Returns:
        True if the file was rewritten (something changed), else False.
    """
    text = SUMMARIZE_PY.read_text()
    match = re.search(r"PRICING: dict\[.*?\] = \{\n(.*?)\n\}\n", text, re.S)
    if not match:
        raise RuntimeError(f"could not find PRICING dict in {SUMMARIZE_PY}")
    body = match.group(1)

    existing: dict[str, str] = {}
    order: list[str] = []
    for line in body.splitlines():
        m = re.match(r'\s*"([^"]+)":\s*\(([^)]*)\),?\s*$', line)
        if not m:
            continue
        key, tup = m.group(1), m.group(2)
        existing[key] = tup
        order.append(key)

    changed = False
    for slug, (in_p, out_p, cw_p, cr_p) in fetched.items():
        tup = f"{in_p}, {out_p}, {cw_p}, {cr_p}"
        if slug not in existing:
            order.insert(len(order) - 1 if "_default" in order else len(order), slug)
            changed = True
        elif existing[slug].replace(" ", "") != tup.replace(" ", ""):
            changed = True
        existing[slug] = tup

    if not changed:
        return False

    # Column-align like the hand-written original; `ruff format` normalizes this
    # further on the next lint pass regardless, so exact alignment isn't load-bearing.
    width = max(len(f'"{k}":') for k in order)
    new_lines = [f'    "{k}":'.ljust(width + 4) + f"({existing[k]})," for k in order]
    new_body = "\n".join(new_lines)
    new_text = text[: match.start(1)] + new_body + text[match.end(1) :]
    SUMMARIZE_PY.write_text(new_text)
    return True


def merge_dashboard_pricing(
    fetched: dict[str, tuple[float, float, float, float]],
) -> bool:
    """Reconcile the PRICING object in session-dashboard.html in place.

    Args:
        fetched: Slug to (input, output, cache_write, cache_read) $/MTok, as
            returned by fetch_pricing_table().

    Returns:
        True if the file was rewritten (something changed), else False.
    """
    text = DASHBOARD_HTML.read_text()
    match = re.search(r"const PRICING=\{(.*?)\};", text)
    if not match:
        raise RuntimeError(f"could not find PRICING object in {DASHBOARD_HTML}")
    body = match.group(1)

    entries: dict[str, str] = {}
    order: list[str] = []
    for m in re.finditer(r"'([^']+)':\{([^}]*)\}", body):
        entries[m.group(1)] = m.group(2)
        order.append(m.group(1))

    def fmt(v: float) -> str:
        return f"{v:g}"

    changed = False
    for slug, (in_p, out_p, cw_p, cr_p) in fetched.items():
        key = slug.removeprefix("claude-")
        val = f"in:{fmt(in_p)},cw:{fmt(cw_p)},cr:{fmt(cr_p)},out:{fmt(out_p)}"
        if key not in entries:
            order.append(key)
            changed = True
        elif entries[key].replace(" ", "") != val.replace(" ", ""):
            changed = True
        entries[key] = val

    if not changed:
        return False

    new_body = ",".join(f"'{k}':{{{entries[k]}}}" for k in order)
    new_text = text[: match.start(1)] + new_body + text[match.end(1) :]
    DASHBOARD_HTML.write_text(new_text)
    return True


def bump_patch_version() -> str:
    """Bump wp-labs-sdlc's patch version and sync statusline.sh's copy.

    Returns:
        The new version string (e.g. "0.25.5").
    """
    manifest = json.loads(PLUGIN_JSON.read_text())
    major, minor, patch = manifest["version"].split(".")
    new_version = f"{major}.{minor}.{int(patch) + 1}"
    manifest["version"] = new_version
    PLUGIN_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    sl_text = STATUSLINE_SH.read_text()
    sl_text = re.sub(
        r'SDLC_SOURCE_VERSION="[^"]*"',
        f'SDLC_SOURCE_VERSION="{new_version}"',
        sl_text,
        count=1,
    )
    STATUSLINE_SH.write_text(sl_text)
    return new_version


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    fetched = fetch_pricing_table()

    py_changed = merge_python_pricing(fetched)
    html_changed = merge_dashboard_pricing(fetched)
    changed = py_changed or html_changed

    if changed and not check_only:
        new_version = bump_patch_version()
        print(f"version={new_version}")

    print(f"changed={'true' if changed else 'false'}")
    return 1 if (check_only and changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
