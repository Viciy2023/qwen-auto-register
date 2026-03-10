"""Allow running as python -m auto_register."""

from .main import run_cli
import sys

if __name__ == "__main__":
    sys.exit(run_cli())
