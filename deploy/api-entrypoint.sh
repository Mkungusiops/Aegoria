#!/usr/bin/env sh
# Aegoria API container entrypoint.
#
# Optionally seeds sample data into the embedded lakehouse, then execs the
# command (uvicorn by default). Seeding is OFF unless AEGORIA_SEED=1, so the
# default lean container starts fast and writes nothing it does not have to.
set -eu

if [ "${AEGORIA_SEED:-0}" = "1" ]; then
  echo "[aegoria] AEGORIA_SEED=1 — seeding sample data into ${AEGORIA_WAREHOUSE:-/data/.aegoria}"
  # Best-effort seed: the control-plane ships a console/CLI seeding hook. If it
  # is unavailable we still boot the API rather than failing the container.
  if python -c "import control_plane.seed" >/dev/null 2>&1; then
    python -m control_plane.seed || echo "[aegoria] seed step reported an error; continuing to serve"
  else
    echo "[aegoria] no control_plane.seed module found; skipping seed"
  fi
fi

# Hand off to the container CMD (uvicorn control_plane.app:app ...).
exec "$@"
