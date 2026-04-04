"""Tests for contract tracker — AST signature extraction, snapshot, compare."""

import textwrap

from vibesrails.contract_tracker import (
    ContractDiff,
    Signature,
    compare,
    extract_signatures,
    latest_snapshot,
    load_snapshot,
    save_snapshot,
    snapshot,
)

# ── Fixtures ───────────────────────────────────────────────────


def _write_py(tmp_path, name, content):
    """Write a Python file to tmp_path."""
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content))
    return path


# ── extract_signatures tests ──────────────────────────────────


def test_extract_function(tmp_path):
    path = _write_py(tmp_path, "mod.py", """\
        def greet(name: str) -> str:
            return f"hello {name}"
    """)
    sigs = extract_signatures(path, "mod")
    assert len(sigs) == 1
    assert sigs[0].name == "greet"
    assert sigs[0].kind == "function"
    assert sigs[0].params == ["name: str"]
    assert sigs[0].return_type == "str"


def test_extract_function_no_annotations(tmp_path):
    path = _write_py(tmp_path, "mod.py", """\
        def process(data):
            pass
    """)
    sigs = extract_signatures(path, "mod")
    assert len(sigs) == 1
    assert sigs[0].params == ["data"]
    assert sigs[0].return_type is None


def test_extract_skip_private(tmp_path):
    path = _write_py(tmp_path, "mod.py", """\
        def public_func():
            pass
        def _private_func():
            pass
        def __dunder():
            pass
    """)
    sigs = extract_signatures(path, "mod")
    assert len(sigs) == 1
    assert sigs[0].name == "public_func"


def test_extract_class_methods(tmp_path):
    path = _write_py(tmp_path, "mod.py", """\
        class MyService:
            def __init__(self, db: str):
                self.db = db
            def fetch(self, key: str) -> dict:
                pass
            def _internal(self):
                pass
    """)
    sigs = extract_signatures(path, "mod")
    names = [s.name for s in sigs]
    assert "MyService.__init__" in names
    assert "MyService.fetch" in names
    assert "MyService._internal" not in names


def test_extract_skip_private_class(tmp_path):
    path = _write_py(tmp_path, "mod.py", """\
        class _Internal:
            def method(self):
                pass
        class Public:
            def method(self):
                pass
    """)
    sigs = extract_signatures(path, "mod")
    classes = {s.name.split(".")[0] for s in sigs}
    assert "_Internal" not in classes
    assert "Public" in classes


def test_extract_async_function(tmp_path):
    path = _write_py(tmp_path, "mod.py", """\
        async def fetch_data(url: str) -> bytes:
            pass
    """)
    sigs = extract_signatures(path, "mod")
    assert len(sigs) == 1
    assert sigs[0].name == "fetch_data"


def test_extract_syntax_error(tmp_path):
    path = _write_py(tmp_path, "bad.py", "def broken(:\n")
    sigs = extract_signatures(path, "bad")
    assert sigs == []


# ── Signature methods ─────────────────────────────────────────


def test_signature_qualified_name():
    sig = Signature(module="mymod", name="func", kind="function")
    assert sig.qualified_name == "mymod.func"


def test_signature_str():
    sig = Signature(
        module="m", name="fn",
        kind="function", params=["x: int", "y: str"], return_type="bool",
    )
    assert sig.signature_str() == "fn(x: int, y: str) -> bool"


def test_signature_str_no_return():
    sig = Signature(module="m", name="fn", kind="function", params=["a"])
    assert sig.signature_str() == "fn(a)"


# ── snapshot + save/load tests ────────────────────────────────


def test_snapshot_project(tmp_path):
    _write_py(tmp_path, "app.py", """\
        def main() -> None:
            pass
        def helper(x: int) -> str:
            return str(x)
    """)
    _write_py(tmp_path, "utils.py", """\
        def format_name(first: str, last: str) -> str:
            return f"{first} {last}"
    """)
    result = snapshot(tmp_path)
    assert "app.main" in result
    assert "app.helper" in result
    assert "utils.format_name" in result


def test_snapshot_skips_tests(tmp_path):
    _write_py(tmp_path, "app.py", "def real(): pass\n")
    _write_py(tmp_path, "tests/test_app.py", "def test_real(): pass\n")
    result = snapshot(tmp_path)
    assert "app.real" in result
    # test file functions should not be in snapshot
    assert not any("test_real" in k for k in result)


def test_save_load_roundtrip(tmp_path):
    data = {"mod.func": {"kind": "function", "params": ["x: int"], "return_type": "str", "sig": "func(x: int) -> str"}}
    save_snapshot(tmp_path, 2, data)
    loaded = load_snapshot(tmp_path, 2)
    assert loaded == data


def test_load_nonexistent(tmp_path):
    assert load_snapshot(tmp_path, 99) is None


def test_latest_snapshot(tmp_path):
    save_snapshot(tmp_path, 1, {"a": {}})
    save_snapshot(tmp_path, 2, {"a": {}, "b": {}})
    result = latest_snapshot(tmp_path)
    assert result is not None
    phase, data = result
    assert phase == 2
    assert len(data) == 2


def test_latest_snapshot_none(tmp_path):
    assert latest_snapshot(tmp_path) is None


# ── compare tests ─────────────────────────────────────────────


def test_compare_no_changes():
    old = {"a": {"sig": "a()"}, "b": {"sig": "b(x: int)"}}
    new = {"a": {"sig": "a()"}, "b": {"sig": "b(x: int)"}}
    diff = compare(old, new)
    assert diff.added == []
    assert diff.removed == []
    assert diff.modified == []
    assert not diff.has_breaking


def test_compare_added():
    old = {"a": {"sig": "a()"}}
    new = {"a": {"sig": "a()"}, "b": {"sig": "b()"}}
    diff = compare(old, new)
    assert diff.added == ["b"]
    assert not diff.has_breaking


def test_compare_removed():
    old = {"a": {"sig": "a()"}, "b": {"sig": "b()"}}
    new = {"a": {"sig": "a()"}}
    diff = compare(old, new)
    assert diff.removed == ["b"]
    assert diff.has_breaking


def test_compare_modified():
    old = {"a": {"sig": "a(x: int)"}}
    new = {"a": {"sig": "a(x: int, y: str)"}}
    diff = compare(old, new)
    assert len(diff.modified) == 1
    assert diff.modified[0][0] == "a"
    assert diff.has_breaking


def test_compare_mixed():
    old = {"keep": {"sig": "keep()"}, "remove": {"sig": "remove()"}, "change": {"sig": "change(x: int)"}}
    new = {"keep": {"sig": "keep()"}, "add": {"sig": "add()"}, "change": {"sig": "change(x: str)"}}
    diff = compare(old, new)
    assert diff.added == ["add"]
    assert diff.removed == ["remove"]
    assert len(diff.modified) == 1


# ── ContractDiff properties ───────────────────────────────────


def test_diff_total_changes():
    diff = ContractDiff(added=["a", "b"], removed=["c"], modified=[("d", "old", "new")])
    assert diff.total_changes == 4


def test_diff_has_breaking_false():
    diff = ContractDiff(added=["a"])
    assert not diff.has_breaking


# ── Integration with snapshot ─────────────────────────────────


def test_full_snapshot_compare_cycle(tmp_path):
    """Snapshot, modify, compare — full cycle."""
    _write_py(tmp_path, "api.py", """\
        def get_user(uid: int) -> dict:
            pass
        def list_users() -> list:
            pass
    """)
    snap1 = snapshot(tmp_path)
    save_snapshot(tmp_path, 1, snap1)

    # Modify: change signature + add new + remove old
    _write_py(tmp_path, "api.py", """\
        def get_user(uid: int, include_email: bool = False) -> dict:
            pass
        def create_user(name: str) -> dict:
            pass
    """)
    snap2 = snapshot(tmp_path)
    diff = compare(snap1, snap2)

    assert "api.create_user" in diff.added
    assert "api.list_users" in diff.removed
    assert any("get_user" in m[0] for m in diff.modified)
