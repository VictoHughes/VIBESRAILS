"""Architecture layer definitions and helpers — extracted from architecture_drift.py."""

LAYER_DEFS: dict[str, tuple[list[str], list[str]]] = {
    "domain": (
        ["domain", "models"],
        [],
    ),
    "infrastructure": (
        ["infrastructure", "adapters"],
        ["domain"],
    ),
    "service": (
        ["services", "application"],
        ["domain"],
    ),
    "presentation": (
        ["api", "routes", "views"],
        ["service"],
    ),
}


def layer_for_dir(dirname: str) -> str | None:
    """Return layer name for a directory, or None."""
    for layer, (dirs, _) in LAYER_DEFS.items():
        if dirname in dirs:
            return layer
    return None


def allowed_deps(layer: str) -> list[str]:
    """Return allowed dependency layers for a given layer."""
    for name, (_, deps) in LAYER_DEFS.items():
        if name == layer:
            return deps
    return []


def all_layer_dirs() -> set[str]:
    """All directory names that map to a layer."""
    result: set[str] = set()
    for _, (dirs, _) in LAYER_DEFS.items():
        result.update(dirs)
    return result


def dirs_for_layer(layer: str) -> list[str]:
    """Return directory names for a layer."""
    for name, (dirs, _) in LAYER_DEFS.items():
        if name == layer:
            return dirs
    return []
