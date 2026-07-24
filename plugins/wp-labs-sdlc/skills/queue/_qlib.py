"""Shared helpers for the q queue script."""
import re

_BLOCK_RE = re.compile(r'(?=^- \[)', re.MULTILINE)


def split_blocks(text: str) -> list[str]:
    """Split a queue file into item blocks on '- [' boundaries.

    Args:
        text: Raw file contents.

    Returns:
        List of string blocks; the first may be an empty preamble.
    """
    return _BLOCK_RE.split(text)


def parse_block_meta(lines: list[str]) -> tuple[dict[str, str], list[str], list[str]]:
    """Parse sub-bullets, metadata fields, and interpretation from a block's body lines.

    Args:
        lines: Lines from the block excluding the first '- [ ] ask' line.

    Returns:
        Tuple of (meta dict, sub-bullet list, interpretation lines list).
    """
    meta: dict[str, str] = {}
    sub: list[str] = []
    interp_lines: list[str] = []
    in_interp = False
    for line in lines:
        s = line.strip()
        if in_interp:
            if line.startswith('    '):
                interp_lines.append(s)
                continue
            else:
                in_interp = False
        if s.startswith('- '):
            sub.append(s[2:])
        elif s.startswith('interpretation:'):
            interp_lines.append(s[len('interpretation:'):].strip())
            in_interp = True
        elif ': ' in s and not in_interp:
            k, v = s.split(': ', 1)
            meta[k] = v
    return meta, sub, interp_lines


def cancel_block(block: str, stamp: str, reason: str, moved_to: str | None = None) -> str:
    """Replace '- [ ]' with '- [-]' and append cancellation metadata after the queued line.

    Args:
        block: Raw item block text starting with '- [ ]'.
        stamp: ISO-format cancellation timestamp.
        reason: Human-readable reason string.
        moved_to: Destination session ID or 'pending', if the item was relocated.

    Returns:
        Updated block with cancellation fields inserted.
    """
    cancelled = block.replace('- [ ]', '- [-]', 1)
    suffix = f'\n  cancelled: {stamp}\n  reason: {reason}'
    if moved_to:
        suffix += f'\n  moved-to: {moved_to}'
    return re.sub(
        r'^  queued: [^\n]+',
        lambda m: m.group() + suffix,
        cancelled, count=1, flags=re.MULTILINE,
    )


def write_group(path: str, num: int, group: str) -> None:
    """Assign or overwrite the group on open item num (1-indexed).

    Args:
        path: Absolute path to the queue .md file.
        num: 1-indexed item number (counts only open `- [ ]` blocks).
        group: Group name string; stripped of surrounding whitespace before writing.
    """
    text = open(path).read()
    blocks = split_blocks(text)
    n, result = 0, []
    for block in blocks:
        if block.startswith('- [ ]'):
            n += 1
            if n == num:
                group_name = group.strip()
                if 'group:' in block:
                    block = re.sub(
                        r'^  group: [^\n]*',
                        f'  group: {group_name}',
                        block, count=1, flags=re.MULTILINE,
                    )
                else:
                    block = block.rstrip() + f'\n  group: {group_name}\n\n'
        result.append(block)
    open(path, 'w').write(''.join(result))
