"""Core package facade — re-exports public symbols for ``from core import X``.

Import order matters: leaf modules (no internal deps) first, then modules
that depend on them, to avoid circular-import errors.
"""

from __future__ import annotations

import os.path as _osp
import sys
import types

# Several submodule __init__.py files import from ``core`` (e.g.
# ``core.models`` does ``from core import FactCheckerOutput``).  While
# ``core`` is still being initialised those imports would raise
# ``ImportError``.  We temporarily pre-populate ``sys.modules`` with
# empty dummy modules for the affected packages so that Python skips
# the problematic ``__init__.py`` executions and lets us import the
# leaf modules directly.  The real packages are restored below.
_DUMMY_PKGS = ["core.models", "core.a2a", "core.logging", "core.utils"]
for _pkg in _DUMMY_PKGS:
    if _pkg not in sys.modules:
        _mod = types.ModuleType(_pkg)
        _mod.__path__ = [
            _osp.join(_osp.dirname(__file__), _pkg.replace("core.", ""))
        ]
        sys.modules[_pkg] = _mod


from pathlib import Path  # noqa: E402

from dotenv import dotenv_values  # noqa: E402

# --- Foundation symbols (MUST exist before core.settings import) ---
# settings_validation.validate_dotenv_keys does ``from core import ENV_FILE``
# at import time, so these must be defined before core.settings is loaded.
_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_ENV_FILE = _PROJECT_ROOT / ".env"
ENV_FILE = _ENV_FILE

# --- Pre-import symbols needed by circular dependencies ---
# core.a2a.request_task does ``from core import new_task`` at module level
# so new_task must be visible in core.__init__'s namespace before _facade
# triggers that import chain.
from core._all import __all__  # noqa: E402

# ---------------------------------------------------------------------------
# The import blocks live in _facade; the __all__ list lives in _all.
# Both are split to keep each file under pylint's 200-line limit.
# Import order in _facade is dependency-aware.
# ---------------------------------------------------------------------------
from core._facade import *  # noqa: E402, F403
from core.a2a.proto import new_task  # noqa: E402

# ---------------------------------------------------------------------------
# Restore real packages for submodules that are imported directly
# (e.g. ``from core.models import Claim`` or ``from core.a2a import
# A2AClient`` in tests). ``core.utils`` must be restored so
# ``import core.utils`` loads ``core.utils.__init__`` (re-exports), not
# the pre-facade dummy in ``sys.modules``.
# ---------------------------------------------------------------------------
for _pkg in ("core.models", "core.a2a", "core.utils"):
    if (
        _pkg in sys.modules
        and getattr(sys.modules[_pkg], "__file__", None) is None
    ):
        del sys.modules[_pkg]
        __import__(_pkg)

# Module-level aliases (used as ``from core import client`` etc.)
import core.a2a.client as client  # noqa: E402

# Restore submodule module references shadowed by ``from X import Y``.
import core.settings as _cs  # noqa: E402, F401
import core.utils as utils  # noqa: E402
import core.utils.citation_sanitize as citation_sanitize  # noqa: E402
