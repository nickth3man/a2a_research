"""Windows-specific patches for Mesop static file serving.

Conditionally patch Mesop's static file serving on Windows to return 404
instead of 500 for missing files such as /robots.txt (framework bug on
Windows).
"""

import os
import sys
from typing import Any, Callable

if sys.platform == "win32":
    import mesop.server.static_file_serving as _sfs
    from flask import Response as _Response

    _original_send_file_compressed = _sfs.send_file_compressed

    def _patched_send_file_compressed(
        path: str, disable_gzip_cache: bool
    ) -> Any:
        if not os.path.exists(path):
            return _Response("Not found", status=404)
        return _original_send_file_compressed(path, disable_gzip_cache)

    _send_file_compressed_patch: Callable[[str, bool], Any] = (
        _patched_send_file_compressed
    )
    _sfs.send_file_compressed = _send_file_compressed_patch  # type: ignore
