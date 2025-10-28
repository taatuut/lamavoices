#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate || source .venv/bin/activate.fish || true
python -m app.runner consensus
