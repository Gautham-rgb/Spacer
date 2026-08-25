"""Single source of truth for the Spacer version.

Both the running program and end users can do::

    import version
    version.__version__

The packaged version is derived from this value via
``[tool.setuptools.dynamic] version = {attr = "version.__version__"}`` in
``pyproject.toml`` (mirrors the Kerbal Gravity Program pattern).
"""

from __future__ import annotations

__version__ = "0.2.0"

PROJECT_NAME = "spacer-bot"
