#!/usr/bin/env bash
# Local smoke test for GUI feature workflows (headless view-model + backend IPC).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pick_python() {
  local candidate
  for candidate in python python3 \
    "/mnt/c/Users/breno/AppData/Local/Programs/Python/Python314/python.exe" \
    "$ROOT/tools/../AppData/Local/Programs/Python/Python314/python.exe"
  do
    if command -v "$candidate" >/dev/null 2>&1; then
      candidate="$(command -v "$candidate")"
    elif [ ! -f "$candidate" ]; then
      continue
    fi
    if "$candidate" -m pip --version >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON="$(pick_python || true)"
if [ -z "${PYTHON:-}" ]; then
  echo "No Python interpreter with pip found" >&2
  exit 1
fi

echo "==> Backend feature tests"
(
  cd "$ROOT/backend"
  "$PYTHON" -m pip install -q -e ".[dev]"
  PYTHONPATH="$ROOT/backend" "$PYTHON" -m pytest \
    ../tests/backend/test_apply_features.py \
    ../tests/backend/test_windows_apply_errors.py \
    -q
)

echo "==> GUI view-model smoke tests"
(
  cd "$ROOT"
  LUA="${LUA:-tools/wxlua542/bin/64bit/lua.exe}"
  if [ -x "$LUA" ] || [ -f "$LUA" ]; then
    "$LUA" scripts/test-view-model.lua
  elif command -v busted >/dev/null 2>&1; then
    busted --config=gui/.busted gui/spec/view_model_spec.lua
  else
    echo "No Lua interpreter found; skipping GUI smoke tests"
  fi
)

echo "All feature smoke tests passed."
