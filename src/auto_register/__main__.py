"""Allow running as python -m auto_register."""

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())
