"""Execution entry point for python -m cargo_doctor."""

from __future__ import annotations

import sys
from cargo_doctor.cli import main

if __name__ == "__main__":
    sys.exit(main())
