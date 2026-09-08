"""Shared pytest bootstrap: make the ``src/`` package importable.

Keep this dependency-free (just ``sys.path``) so the suite runs anywhere the
package does.
"""

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)