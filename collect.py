#!/usr/bin/env python3
"""DevCity (formerly claude-code-usage-city) collection entrypoint.

Backward-compatible wrapper around devcity.cli.
Run 'python3 collect.py --help' or 'usage-city --help' for options.
"""

import sys
from devcity.cli import main

if __name__ == "__main__":
    sys.exit(main())
