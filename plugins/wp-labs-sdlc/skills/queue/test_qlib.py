import os, tempfile, sys
sys.path.insert(0, os.path.dirname(__file__))
from _qlib import cancel_block, migrate_blocks, parse_block_meta, split_blocks, write_group


def _tmp(content):
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
    f.write(content); f.close()
    return f.name


# --- split_blocks ---

def test_split_blocks_empty():
    assert split_blocks('') == ['']

def test_split_blocks_single():
    blocks = split_blocks('- [ ] Ask\n  queued: 2026-01-01 00:00:00\n\n')
    opens = [b for b in blocks if b.startswith('- [ ]')]
    assert len(opens) == 1
    assert opens[0].startswith('- [ ] Ask')

def test_split_blocks_multiple():
    text = '- [ ] One\n  queued: 2026-01-01\n\n- [ ] Two\n  queued: 2026-01-01\n\n'
    opens = [b for b in split_blocks(text) if b.startswith('- [ ]')]
    assert len(opens) == 2

def test_split_blocks_preamble():
    text = '# header\n\n- [ ] Item\n  queued: 2026-01-01\n\n'
    blocks = split_blocks(text)
    assert blocks[0].startswith('# header')
    assert any(b.startswith('- [ ]') for b in blocks)


# --- cancel_block ---

def test_cancel_block_marks_cancelled():
    block = '- [ ] Fix test\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n'
    result = cancel_block(block, '2026-01-01 12:00:00', 'Test reason')
    assert result.startswith('- [-]')
    assert 'cancelled: 2026-01-01 12:00:00' in result
    assert 'reason: Test reason' in result
    assert 'moved-to:' not in result

def test_cancel_block_with_moved_to():
    block = '- [ ] Fix test\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n'
    result = cancel_block(block, '2026-01-01 12:00:00', 'Moved', 'abc123')
    assert 'moved-to: abc123' in result

def test_cancel_block_preserves_other_fields():
    block = '- [ ] Fix test\n  queued: 2026-01-01 00:00:00\n  ctx: my-project\n'
    result = cancel_block(block, '2026-01-01 12:00:00', 'Done')
    assert 'ctx: my-project' in result


# --- parse_block_meta ---

def test_parse_block_meta_basic():
    lines = ['  queued: 2026-01-01 00:00:00', '  ctx: my-project', '']
    meta, sub, interp = parse_block_meta(lines)
    assert meta['queued'] == '2026-01-01 00:00:00'
    assert meta['ctx'] == 'my-project'
    assert sub == []
    assert interp == []

def test_parse_block_meta_with_sub_bullets():
    lines = ['  - first sub', '  - second sub', '  queued: 2026-01-01', '']
    meta, sub, interp = parse_block_meta(lines)
    assert sub == ['first sub', 'second sub']

def test_parse_block_meta_with_interpretation():
    lines = ['  queued: 2026-01-01', '  interpretation: Fix the bug', '']
    meta, sub, interp = parse_block_meta(lines)
    assert 'Fix the bug' in interp

def test_parse_block_meta_interp_continuation():
    lines = ['  queued: 2026-01-01', '  interpretation: Main text', '    extra detail', '']
    meta, sub, interp = parse_block_meta(lines)
    assert 'Main text' in interp
    assert 'extra detail' in interp

def test_parse_block_meta_interp_dash_continuation_not_sub():
    # Regression: continuation lines starting with '- ' must not become sub-bullets.
    lines = ['  queued: 2026-01-01', '  interpretation: Main text', '    - nested point', '']
    meta, sub, interp = parse_block_meta(lines)
    assert sub == []
    assert any('nested point' in l for l in interp)

def test_parse_block_meta_group_and_priority():
    lines = ['  queued: 2026-01-01', '  priority: high', '  group: ci-fixes', '']
    meta, sub, interp = parse_block_meta(lines)
    assert meta['priority'] == 'high'
    assert meta['group'] == 'ci-fixes'


# --- migrate_blocks ---

_QUEUE_TWO = (
    "- [ ] Item one\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n\n"
    "- [ ] Item two\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n\n"
)

def test_migrate_blocks_cancels_and_returns_fresh():
    updated, fresh = migrate_blocks(_QUEUE_TWO, {1}, '2026-01-01 12:00:00', 'dst-sid')
    assert '- [-]' in updated
    assert 'moved-to: dst-sid' in updated
    assert len(fresh) == 1
    assert fresh[0].startswith('- [ ] Item one')

def test_migrate_blocks_leaves_unselected_open():
    updated, fresh = migrate_blocks(_QUEUE_TWO, {1}, '2026-01-01 12:00:00', 'dst-sid')
    assert '- [ ] Item two' in updated
    assert len(fresh) == 1

def test_migrate_blocks_empty_set_migrates_nothing():
    updated, fresh = migrate_blocks(_QUEUE_TWO, set(), '2026-01-01 12:00:00', 'dst-sid')
    assert updated == _QUEUE_TWO
    assert fresh == []

def test_migrate_blocks_multiple_items():
    updated, fresh = migrate_blocks(_QUEUE_TWO, {1, 2}, '2026-01-01 12:00:00', 'dst-sid')
    assert updated.count('- [-]') == 2
    assert len(fresh) == 2


# --- write_group ---

def test_write_group_adds_field():
    path = _tmp("- [ ] Fix test\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n\n")
    write_group(path, 1, 'ci-fixes')
    assert 'group: ci-fixes' in open(path).read()
    os.unlink(path)

def test_write_group_overwrites_existing():
    path = _tmp("- [ ] Fix test\n  queued: 2026-01-01 00:00:00\n  group: existing\n\n")
    write_group(path, 1, 'new-group')
    content = open(path).read()
    assert 'group: new-group' in content
    assert 'group: existing' not in content
    os.unlink(path)

def test_write_group_targets_correct_item():
    path = _tmp(
        "- [ ] Item one\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n\n"
        "- [ ] Item two\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n\n"
    )
    write_group(path, 2, 'docs')
    content = open(path).read()
    parts = content.split('- [ ]')
    assert 'group:' not in parts[1]       # item 1 unchanged
    assert 'group: docs' in parts[2]      # item 2 got group
    os.unlink(path)

def test_write_group_strips_whitespace():
    path = _tmp("- [ ] Fix test\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n\n")
    write_group(path, 1, '  ci-fixes  ')
    assert 'group: ci-fixes\n' in open(path).read()
    os.unlink(path)


if __name__ == '__main__':
    test_migrate_blocks_cancels_and_returns_fresh()
    test_migrate_blocks_leaves_unselected_open()
    test_migrate_blocks_empty_set_migrates_nothing()
    test_migrate_blocks_multiple_items()
    test_split_blocks_empty()
    test_split_blocks_single()
    test_split_blocks_multiple()
    test_split_blocks_preamble()
    test_cancel_block_marks_cancelled()
    test_cancel_block_with_moved_to()
    test_cancel_block_preserves_other_fields()
    test_parse_block_meta_basic()
    test_parse_block_meta_with_sub_bullets()
    test_parse_block_meta_with_interpretation()
    test_parse_block_meta_interp_continuation()
    test_parse_block_meta_interp_dash_continuation_not_sub()
    test_parse_block_meta_group_and_priority()
    test_write_group_adds_field()
    test_write_group_overwrites_existing()
    test_write_group_targets_correct_item()
    test_write_group_strips_whitespace()
    print('All tests passed.')
