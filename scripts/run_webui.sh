```sh
#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate || true
uvicorn app.webui:app --host 0.0.0.0 --port 8080
