"""Input validation for MCP tool arguments.

Validates strings, integers, dicts, lists, and enums from MCP clients.
All user-facing arguments must pass through these validators before use.
"""

from __future__ import annotations

import json


class InputValidationError(ValueError):
    """Raised when an input argument fails validation.

    Messages are safe to return to MCP clients.
    """


def validate_string(
    value: object,
    name: str,
    *,
    max_length: int = 1_000_000,
) -> str:
    """Validate a string argument.

    Args:
        value: Raw value from MCP client.
        name: Parameter name (for error messages).
        max_length: Maximum character count.

    Returns:
        Validated string.
    """
    if not isinstance(value, str):
        raise InputValidationError(f"{name} must be a string.")
    if len(value) > max_length:
        raise InputValidationError(
            f"{name} too long ({len(value)} chars). Maximum: {max_length}."
        )
    return value


def validate_int(
    value: object,
    name: str,
    *,
    min_val: int = 0,
    max_val: int = 1_000_000,
) -> int:
    """Validate an integer argument.

    Args:
        value: Raw value from MCP client.
        name: Parameter name (for error messages).
        min_val: Minimum allowed value (inclusive).
        max_val: Maximum allowed value (inclusive).

    Returns:
        Validated integer.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise InputValidationError(f"{name} must be an integer.")
    if value < min_val or value > max_val:
        raise InputValidationError(
            f"{name} must be between {min_val} and {max_val}. Got: {value}."
        )
    return value


def validate_dict(
    value: object,
    name: str,
    *,
    max_keys: int = 100,
    max_size_bytes: int = 1_048_576,
) -> dict:
    """Validate a dict argument.

    Args:
        value: Raw value from MCP client.
        name: Parameter name (for error messages).
        max_keys: Maximum number of top-level keys.
        max_size_bytes: Maximum serialized size in bytes.

    Returns:
        Validated dict.
    """
    if not isinstance(value, dict):
        raise InputValidationError(f"{name} must be a dict.")
    if len(value) > max_keys:
        raise InputValidationError(
            f"{name} has too many keys ({len(value)}). Maximum: {max_keys}."
        )
    serialized = json.dumps(value, default=str)
    if len(serialized.encode("utf-8")) > max_size_bytes:
        raise InputValidationError(
            f"{name} too large. Maximum size: {max_size_bytes // 1024}KB."
        )
    return value


def validate_list(
    value: object,
    name: str,
    *,
    max_items: int = 10_000,
    item_type: type = str,
) -> list:
    """Validate a list argument.

    Args:
        value: Raw value from MCP client.
        name: Parameter name (for error messages).
        max_items: Maximum number of items.
        item_type: Expected type for each item.

    Returns:
        Validated list.
    """
    if not isinstance(value, list):
        raise InputValidationError(f"{name} must be a list.")
    if len(value) > max_items:
        raise InputValidationError(
            f"{name} has too many items ({len(value)}). Maximum: {max_items}."
        )
    for i, item in enumerate(value):
        if not isinstance(item, item_type):
            raise InputValidationError(
                f"{name}[{i}] must be {item_type.__name__}."
            )
    return value


def validate_enum(
    value: object,
    name: str,
    *,
    choices: set[str],
) -> str:
    """Validate a string against a fixed set of choices.

    Args:
        value: Raw value from MCP client.
        name: Parameter name (for error messages).
        choices: Set of allowed values.

    Returns:
        Validated string.
    """
    if not isinstance(value, str):
        raise InputValidationError(f"{name} must be a string.")
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise InputValidationError(
            f"Invalid {name}: {value!r}. Must be one of: {allowed}."
        )
    return value


def sanitize_for_output(text: str, max_length: int = 256) -> str:
    """Sanitize text for safe inclusion in MCP responses.

    Strips control characters and limits length to prevent
    prompt injection via filenames or messages in tool output.
    """
    sanitized = "".join(c for c in text if c.isprintable())
    return sanitized[:max_length]


def validate_optional_string(
    value: object,
    name: str,
    *,
    max_length: int = 256,
) -> str | None:
    """Validate an optional string argument.

    Returns None if value is None, otherwise validates as string.
    """
    if value is None:
        return None
    return validate_string(value, name, max_length=max_length)
