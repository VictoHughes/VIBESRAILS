"""Security tests: input validation.

Tests that validate_string/int/dict/list/enum reject malformed inputs
and accept valid ones.
"""

from __future__ import annotations

import pytest

from core.input_validator import (
    InputValidationError,
    validate_dict,
    validate_enum,
    validate_int,
    validate_list,
    validate_optional_string,
    validate_string,
)

# ── String ───────────────────────────────────────────────────────────


def test_string_non_string_rejected():
    with pytest.raises(InputValidationError, match="must be a string"):
        validate_string(12345, "field")


def test_string_oversized_rejected():
    with pytest.raises(InputValidationError, match="too long"):
        validate_string("x" * 101, "field", max_length=100)


def test_string_valid_accepted():
    assert validate_string("hello", "field") == "hello"


# ── Int ──────────────────────────────────────────────────────────────


def test_int_negative_rejected():
    with pytest.raises(InputValidationError, match="must be between"):
        validate_int(-1, "count", min_val=0, max_val=100)


def test_int_too_large_rejected():
    with pytest.raises(InputValidationError, match="must be between"):
        validate_int(999, "count", min_val=0, max_val=100)


def test_int_valid_accepted():
    assert validate_int(42, "count", min_val=0, max_val=100) == 42


def test_int_bool_rejected():
    """Booleans are technically ints in Python but should be rejected."""
    with pytest.raises(InputValidationError, match="must be an integer"):
        validate_int(True, "flag")


# ── Dict ─────────────────────────────────────────────────────────────


def test_dict_non_dict_rejected():
    with pytest.raises(InputValidationError, match="must be a dict"):
        validate_dict("not a dict", "config")


def test_dict_too_many_keys_rejected():
    big = {f"key_{i}": i for i in range(200)}
    with pytest.raises(InputValidationError, match="too many keys"):
        validate_dict(big, "config", max_keys=100)


def test_dict_valid_accepted():
    d = {"a": 1, "b": 2}
    assert validate_dict(d, "config") == d


# ── List ─────────────────────────────────────────────────────────────


def test_list_non_list_rejected():
    with pytest.raises(InputValidationError, match="must be a list"):
        validate_list("not a list", "items")


def test_list_wrong_item_type_rejected():
    with pytest.raises(InputValidationError, match="must be str"):
        validate_list(["ok", 123], "items", item_type=str)


def test_list_valid_accepted():
    items = ["a", "b", "c"]
    assert validate_list(items, "items") == items


# ── Enum ─────────────────────────────────────────────────────────────


def test_enum_unknown_rejected():
    with pytest.raises(InputValidationError, match="Invalid"):
        validate_enum("npm", "ecosystem", choices={"pypi"})


def test_enum_valid_accepted():
    assert validate_enum("pypi", "ecosystem", choices={"pypi"}) == "pypi"


# ── Optional string ─────────────────────────────────────────────────


def test_optional_string_none_accepted():
    assert validate_optional_string(None, "session_id") is None


def test_optional_string_valid_accepted():
    assert validate_optional_string("abc", "session_id") == "abc"


def test_optional_string_oversized_rejected():
    with pytest.raises(InputValidationError, match="too long"):
        validate_optional_string("x" * 300, "session_id", max_length=256)
