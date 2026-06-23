"""Vault I/O abstraction: filesystem and native /mcp/ backends."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from planner.config import Config
from planner.errors import VaultIOError


class Vault(Protocol):
    """Read/write access to an Obsidian vault, backend-agnostic."""

    def list_dir(self, dirpath: str) -> list[str]: ...
    def read(self, filepath: str) -> str: ...
    def stat_mtime(self, filepath: str) -> float: ...
    def write(self, filepath: str, content: str) -> None: ...
    def append(self, filepath: str, content: str) -> None: ...
    def patch_heading(self, filepath: str, heading: str, content: str,
                      operation: str = "append") -> None: ...
    def exists(self, filepath: str) -> bool: ...


def _insert_under_heading(body: str, heading: str, content: str, operation: str) -> str:
    """Insert content relative to a `## heading` (append=end of section, prepend=start)."""
    marker = f"## {heading}"
    start = body.find(marker)
    if start == -1:
        raise VaultIOError(f"Heading '## {heading}' not found")
    after = start + len(marker)
    nxt = body.find("\n## ", after)
    section_end = len(body) if nxt == -1 else nxt
    block = ("\n" + content.strip() + "\n")
    if operation == "prepend":
        return body[:after] + block + body[after:]
    return body[:section_end].rstrip() + "\n" + block + body[section_end:]


class FilesystemVault:
    """Vault backed by direct filesystem access under a root path."""

    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _abs(self, filepath: str) -> Path:
        return self._root / filepath

    def list_dir(self, dirpath: str) -> list[str]:
        d = self._abs(dirpath)
        if not d.is_dir():
            raise VaultIOError(f"Not a directory: {dirpath}")
        return sorted(e.name + ("/" if e.is_dir() else "") for e in d.iterdir())

    def read(self, filepath: str) -> str:
        p = self._abs(filepath)
        if not p.is_file():
            raise VaultIOError(f"File not found: {filepath}")
        return p.read_text(encoding="utf-8")

    def stat_mtime(self, filepath: str) -> float:
        p = self._abs(filepath)
        if not p.is_file():
            raise VaultIOError(f"File not found: {filepath}")
        return p.stat().st_mtime

    def write(self, filepath: str, content: str) -> None:
        p = self._abs(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def append(self, filepath: str, content: str) -> None:
        existing = self.read(filepath) if self.exists(filepath) else ""
        self.write(filepath, existing + ("\n" if existing and not existing.endswith("\n") else "") + content)

    def patch_heading(self, filepath: str, heading: str, content: str,
                      operation: str = "append") -> None:
        self.write(filepath, _insert_under_heading(self.read(filepath), heading, content, operation))

    def exists(self, filepath: str) -> bool:
        return self._abs(filepath).is_file()


def make_vault(cfg: Config) -> Vault:
    """Return the configured vault backend."""
    if cfg.obsidian.mode == "filesystem":
        return FilesystemVault(cfg.vault.path)
    from planner.obsidian_mcp import McpVault  # local import to keep deps lazy

    return McpVault(cfg)
