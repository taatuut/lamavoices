#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate || true
python3 -m app.recorder
