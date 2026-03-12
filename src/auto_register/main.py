"""Entry point for Qwen token auto-acquisition (GUI only)."""

import sys


def main() -> int:
    """Launch the GUI application. Returns exit code."""
    from .gui.app import run_gui

    try:
        return run_gui()
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
