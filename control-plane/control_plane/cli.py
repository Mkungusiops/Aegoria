"""Tiny launcher for the control-plane API (``aegoria-control-plane``).

Reads ``AEGORIA_API_HOST`` / ``AEGORIA_API_PORT`` (defaults ``127.0.0.1:8000``)
and serves :data:`control_plane.app.app` with uvicorn. Kept dependency-light so
the package's only runtime needs are FastAPI + uvicorn + the core engine.
"""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.environ.get("AEGORIA_API_HOST", "127.0.0.1")
    port = int(os.environ.get("AEGORIA_API_PORT", "8000"))
    uvicorn.run("control_plane.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
