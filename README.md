# Lamavoices — Consensus‑Operated VIAM Rover (with Solace)

Run a crowd‑controlled rover where many operators send intents, a consensus service merges them, and a rover runner applies the final commands. Includes a QR webhook bridge, a live Web UI, and MongoDB recorder/replay.

---

## Project Layout
```
lamavoices
├── .env
├── LICENSE
├── README.md
├── app
│   ├── __pycache__
│   ├── agents.py
│   ├── broker.py
│   ├── consensus.py
│   ├── intent_cli.py
│   ├── recorder.py
│   ├── replay.py
│   ├── rover.py
│   ├── runner.py
│   ├── safety.py
│   ├── schema.py
│   ├── webhook.py
│   └── webui.py
├── sample.env
├── scripts
│   └── run_webui.sh
├── test_viam_connect.py
├── tree.txt
└── viam-jan-main.json
```

> This doc assumes the above structure with local only `.env` and `viam-jan-main.json` files, not part of repository.

---

## Prerequisites

- macOS with Homebrew
- Python 3.10+ (3.11 recommended) and a virtualenv
- A Solace PubSub+ broker (MQTT over TLS)
- A VIAM Rover with a `base` component configured
- (Optional) MongoDB (Atlas or local) for recorder/replay

### Install tooling

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python python-tk uv
```

### Create & activate venv

```bash
source .env && mkdir -p ~/.venv && python3 -m venv ~/.venv && source ~/.venv/bin/activate
```

### Viam

Set up the Viam Rover device via https://app.viam.com/ and https://docs.viam.com/operate/reference/prepare/rpi-setup/

Download the machine cloud credentials `viam-jan-main.json` to your repo (included in `.gitignore`).

_Optional_

When no hardware device is available, install `viam-server` on the laptop to create a dummy digital device for testing purposes.

```bash
brew tap viamrobotics/brews && brew install viam-server
```
Note that when installed via homebrew, the default location for the viam-server config is `/opt/homebrew/etc/viam.json`.

To start `viam-server` on your Mac:

```bash
viam-server -config ~/GitHub/taatuut/lamavoices/viam-jan-main.json
```

### Install Python dependencies

```bash
python3 -m pip install --upgrade pip
python3 -m pip install requests neo4j psutil aiohttp pyyaml ace-tools-open shapely solace-pubsubplus pymongo lxml dash plotly solace-agent-mesh pythonplantuml paho-mqtt pydantic uvloop viam-sdk fastapi 'uvicorn[standard]' python-dotenv rich typer motor itsdangerous paho-mqtt
```

### Configure environment

Copy and edit environment:

```bash
# only copy if not exists
# cp sample.env .env
# then open .env and fill Solace + VIAM + optional MongoDB settings
source .env
```

Key variables (see `.env`):
- `SOLACE_HOST`, `SOLACE_USERNAME`, `SOLACE_PASSWORD`
- `SESSION_ID` (e.g., `emea-tech-2025w44`)
- `TICK_MS` (e.g., `200`)
- `VIAM_ROBOT_ADDRESS`, `VIAM_API_KEY_ID`, `VIAM_API_KEY`, `VIAM_BASE_NAME`
- (Optional) `MONGODB_URI`, `MONGODB_DB` for recorder/replay

---

## Start Sequence (recommended order)

TODO: directly call Python (uvicorn) scripts for steps 1-4

> **TL;DR (scripts):**
> 1) `./scripts/run_consensus.sh`
> 2) `./scripts/run_rover.sh` (on the rover‑connected host)
> 3) `./scripts/run_webui.sh` (optional, live dashboard)
> 4) `./scripts/run_recorder.sh` (optional, DB logging)
> 5) Run the QR webhook bridge: `uvicorn app.webhook:app --host 0.0.0.0 --port 8345`

You can also invoke the Python modules directly (shown below). Ensure your virtualenv is active and `source .env` has been run.

### 1) Start the Consensus Agent
Merges crowd intents into a single command stream.

```bash
python3 -m app.runner consensus
```

### 2) Start the Rover Runner
Subscribes to consensus output and commands the VIAM base.

```bash
python3 -m app.runner rover
```

> **Tip:** You can run the Rover Runner on the same machine or on the rover’s SBC. It just needs network access to VIAM and Solace.

### 3) (Optional) Start the Web UI (Live Intents & Consensus)
A tiny FastAPI dashboard with Server‑Sent Events.

```bash
# Script
./scripts/run_webui.sh

# Or Python directly
uvicorn app.webui:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080
```

### 4) (Optional) Start the MongoDB Recorder
Persists intents/consensus/events for analytics and replay.

```bash
# Script
./scripts/run_recorder.sh

# Or Python directly
python3 -m app.recorder
```

### 5) (Optional/When using QR) Start the QR Webhook Bridge
Translates QR button clicks to intents published to Solace.

```bash
uvicorn app.webhook:app --host 0.0.0.0 --port 8345
# Point the entanglement QR app to POST http://<host>:8345/qr
```

---

## Testing & Utilities

### Send test intents from CLI
Generates steady intents to verify the pipeline.

```bash
python app/intent_cli.py spam --op-id alice --v 0.6 --w 0.0 --hz 5
```

### Replay a recorded session (from MongoDB)
Re‑emits historical intents onto the bus for demo or regression checks.

```bash
python3 -m app.replay   # default scale=2.0 inside the module; edit as needed
```

---

## Ports & Topics

| Component           | Default Port | Subscribes                                     | Publishes                                   |
|--------------------|--------------|-----------------------------------------------|---------------------------------------------|
| Consensus Agent    | —            | `ez/rover/intent/v1/{SESSION}/+`              | `ez/rover/consensus/v1/{SESSION}`           |
| Rover Runner       | —            | `ez/rover/consensus/v1/{SESSION}`             | VIAM `base.set_velocity()`                   |
| Web UI             | `8080`       | intents + consensus (via MQTT inside backend) | Serves SSE endpoints `/sse/intent`, `/sse/consensus` |
| QR Webhook Bridge  | `8345`       | —                                             | `ez/rover/intent/v1/{SESSION}/{opId}`       |
| Recorder           | —            | intents/consensus/events                      | MongoDB collections                          |

---

## Troubleshooting

- **No motion:** Check `SESSION_ID` matches everywhere; verify Solace creds and connectivity.
- **Consensus oscillation:** Increase `TICK_MS` (e.g., 300–400 ms) and/or EMA `alpha`.
- **VIAM errors:** Ensure the rover config exposes a `base` component and that auth values in `.env` are correct.
- **Web UI blank:** Confirm it connects to Solace (watch console logs) and that the consensus/intent topics are active.
- **QR clicks not moving rover:** Make sure the webhook is running on `:8345`, the QR app posts to `/qr`, and consensus/rover processes are up.

---

## Scripts Reference

Make scripts executable once:
```bash
chmod +x scripts/*.sh
```

- **Consensus:** `./scripts/run_consensus.sh`
- **Rover Runner:** `./scripts/run_rover.sh`
- **Web UI:** `./scripts/run_webui.sh`
- **Recorder:** `./scripts/run_recorder.sh`

The webhook bridge is run directly via uvicorn (or add your own script if desired).

---

## License
See `LICENSE`.
