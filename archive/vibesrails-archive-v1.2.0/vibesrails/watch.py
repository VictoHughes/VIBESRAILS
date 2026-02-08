"""
vibesrails watch mode - Live scanning during coding.

Monitors Python files and scans on save.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

from .scanner import BLUE, GREEN, NC, RED, YELLOW, load_config, scan_file

logger = logging.getLogger(__name__)

# Optional watchdog import
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    # Dummy base class when watchdog not installed
    class FileSystemEventHandler:
        """Fallback base class when watchdog is not installed."""
    Observer = None


class VibesRailsHandler(FileSystemEventHandler):
    """Handle file system events for Python files."""

    def __init__(self, config: dict):
        self.config = config
        self.last_scan = {}  # Debounce repeated events

    def on_modified(self, event: Any) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        filepath = event.src_path

        # Only scan Python files
        if not filepath.endswith(".py"):
            return

        # Skip virtual environments and cache
        skip_patterns = [".venv", "venv", "__pycache__", "node_modules", ".git"]
        if any(p in filepath for p in skip_patterns):
            return

        # Debounce - don't scan same file within 1 second
        now = time.time()
        if filepath in self.last_scan and now - self.last_scan[filepath] < 1:
            return
        self.last_scan[filepath] = now

        # Scan the file
        self.scan_file(filepath)

    def scan_file(self, filepath: str) -> None:
        """Scan a single file and report results."""
        # Get relative path for cleaner output
        try:
            rel_path = Path(filepath).relative_to(Path.cwd())
        except ValueError:
            rel_path = filepath

        results = scan_file(filepath, self.config)

        if not results:
            logger.info(f"{GREEN}✓{NC} {rel_path}")
            return

        blocking = [r for r in results if r.level == "BLOCK"]
        warnings = [r for r in results if r.level == "WARN"]

        if blocking:
            logger.info(f"\n{RED}✗ {rel_path}{NC}")
            for r in blocking:
                logger.info(f"  {RED}BLOCK{NC} :{r.line} [{r.pattern_id}] {r.message}")
        elif warnings:
            logger.info(f"\n{YELLOW}! {rel_path}{NC}")

        for r in warnings:
            logger.info(f"  {YELLOW}WARN{NC} :{r.line} [{r.pattern_id}] {r.message}")


def run_watch_mode(config_path: Path | None = None) -> bool:
    """Run watch mode to scan files on save."""
    logger.info(f"\n{BLUE}vibesrails --watch{NC}")
    logger.info("=" * 40)
    logger.info("Live scanning mode\n")

    if not HAS_WATCHDOG:
        logger.error(f"{RED}ERROR: watchdog package not installed{NC}")
        logger.error("Install with: pip install vibesrails[watch]")
        return False

    # Load config
    config = load_config(config_path)

    logger.info(f"{GREEN}Watching for changes...{NC}")
    logger.info("Press Ctrl+C to stop\n")

    # Set up observer
    handler = VibesRailsHandler(config)
    observer = Observer()
    observer.schedule(handler, ".", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)  # vibesrails: ignore — file watcher polling loop
    except KeyboardInterrupt:
        logger.info(f"\n{YELLOW}Stopping watch mode...{NC}")
        observer.stop()

    observer.join()
    logger.info(f"{GREEN}Watch mode stopped{NC}")
    return True
