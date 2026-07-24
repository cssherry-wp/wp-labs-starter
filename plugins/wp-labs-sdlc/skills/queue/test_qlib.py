import os, tempfile, sys
sys.path.insert(0, os.path.dirname(__file__))
from _qlib import write_group

def _tmp(content):
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
    f.write(content); f.close()
    return f.name

def test_write_group_adds_field():
    path = _tmp("- [ ] Fix test\n  queued: 2026-01-01 00:00:00\n  ctx: foo\n\n")
    write_group(path, 1, 'ci-fixes')
    assert 'group: ci-fixes' in open(path).read()
    os.unlink(path)

def test_write_group_skips_existing():
    path = _tmp("- [ ] Fix test\n  queued: 2026-01-01 00:00:00\n  group: existing\n\n")
    write_group(path, 1, 'new-group')
    content = open(path).read()
    assert 'group: existing' in content
    assert 'group: new-group' not in content
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
    test_write_group_adds_field()
    test_write_group_skips_existing()
    test_write_group_targets_correct_item()
    test_write_group_strips_whitespace()
    print('All tests passed.')
