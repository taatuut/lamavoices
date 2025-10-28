# Lamavoices
to create a consensus operated robot

# Context
I have a VIAM Rover robot https://www.viam.com/resources/rover, and at Solace we have the entanglement demo https://sg.solace.rocks/qr/. How can these be combined to create a consensus based operated robot. It might literally not go anywhere at all if all people push for different directions.

Similar to https://www.viam.com/resources/try-viam where one person can control a VIAM Rover robot in a lab but then real-time controlled by multiple people using Solace event broker, maybe even add Solace Agent Mesh to the mix.

This repo provides a comprehensive plan layout and code framework to get it all working using Python as main programming language on macOS system, where necessary supported by tooling like brew installs, terminal shell scripts etc.

## Prerequisites
On macOS Make sure `brew` is installed. SQLite is bundled by default with Python (`sqlite3`, since Python 2.5). Then install `python`, `colima`, `docker`, `qemu`, and optionally `neo4j` and `mongodb`. See appendices for details.

### Environment
If not done, copy `sample.env` to `.env` and edit the variables to contain relevant values.

NOTE: for now happily using an `.env` file for sensitive data (do store in your password manager/digital wallet application of choice of course...).

Open a terminal and source environment variables if any.

```sh
source .env
```
### Brew

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python uv
```
Can pick specific version if preferred using `python@3.11`

### Python
Use `Python 3.10+`.

To create and source a Python virtual environment like  `~/.venv` in the Terminal run:

```sh
mkdir -p ~/.venv && python3 -m venv ~/.venv && source ~/.venv/bin/activate
```

To unload the `venv` run `deactivate`.

Using the Terminal install Python modules (optional: update `pip`) adn source the environment variables.

NOTE: pip including current latest version 25.2 has issue GHSA-4xh5-x5gv-qwph.

```sh
python3 -m pip install --upgrade pip
python3 -m pip install requests neo4j psutil aiohttp pyyaml ace-tools-open shapely solace-pubsubplus pymongo lxml dash plotly solace-agent-mesh pythonplantuml paho-mqtt pydantic uvloop viam-sdk fastapi 'uvicorn[standard]' python-dotenv rich typer motor itsdangerous
```

NOTE: if `activate` runs without errors but installing modules in `venv` fails with errors about global site-packages, then run `which python3`, should respond with something like `~/.venv/bin/python3`, not `/usr/local/bin/python3`. If the latter is the case (`/usr/local/bin/...`) then remove venv with `rm -rf ~/.venv` and create again, might also mean reinstalling modules.

_Optional_

pip-audit

```sh
python3 -m pip install pip-audit
# Scan the current virtualenv
pip-audit
```

Output (happy path) like

```sh
No known vulnerabilities found
```

If necessary  take (or automate) actions like updating vulnerable modules, uninstalling not needed modules.

# Plan
A full end-to-end plan + a ready-to-wire code framework: “Consensus Rover with Solace — Plan & Code Framework (Python/macOS)” covering:

Architecture (operators → Solace → Agent Mesh → VIAM Rover)

Topics & JSON schemas

Consensus strategies (vector averaging, majority, deadlock/tie-break)

Security (TLS/mTLS, rate limiting)

macOS install steps (brew + Python deps)

Runnable Python modules:

MQTT bus to Solace

Consensus agent

Safety gate

VIAM rover runner (using viam-sdk)

QR/entanglement bridge webhook

CLI spammer for testing

Shell scripts to run the consensus and rover processes

Demo flow + troubleshooting

A tiny FastAPI web UI to visualize live intents/consensus

And a MongoDB recorder for replay.

# Notes
The Web UI avoids external JS libs for a zero‑build demo.

Behind HTTPS, enable CORS in FastAPI if your QR page is on another origin.

For demo: mirror the Web UI; let the audience scan the QR and watch the consensus evolve.

# Operation

Consensus Rover with Solace & VIAM — Complete Plan, Web UI, and Recorder (macOS/Python)

**Purpose:** Operate a VIAM Rover by *crowd consensus* using Solace PubSub+. Many participants send intents; a consensus service merges them into one safe command stream. Includes a tiny FastAPI Web UI (live intents & consensus), a MongoDB recorder, and simple replay.

## Goal
Use a VIAM Rover controlled by Python while *many people* send control intents simultaneously. All intents flow through Solace PubSub+ and are combined by a consensus service that outputs a single safe command stream to the rover. If everyone disagrees, the rover (safely) doesn’t move — or performs a tie‑break behavior.

## High‑Level Architecture
```
+--------------------------- Crowd / Operators ---------------------------+
|  Web UI / QR links / Entanglement demo  |  CLI  |  Slack bot  | etc.  |
|         (publishes intents via Solace)  |       |             |       |
+-----------------------------------------+-------+-------------+-------+
                              | MQTT/SMF over TLS
                              v
+--------------------------- Solace PubSub+ ------------------------------+
|  Topics:                                                         
|    ez/rover/intent/v1/{session}/{operatorId}                     
|    ez/rover/consensus/v1/{session}       (derived decisions)     
|    ez/rover/telemetry/v1/{session}/{node} (metrics + state)      
|    ez/rover/event/v1/{session}            (alerts)               
+-----------------------------------------------------------------------+
                              |
                              v
+--------------------------- Agent Mesh ---------------------------------+
|  normalizer -> rate_limiter -> authz -> consensus -> safety -> outbus  |
|  (each agent subscribes/publishes on Solace topics)                     |
+-----------------------------------------------------------------------+
                              |
                              v
+------------------------- VIAM Rover Runner ----------------------------+
| Python process on macOS (or rover SBC) uses viam-sdk to drive base     |
| - Sub ez/rover/consensus/v1/{session}                                  |
| - Obstacle sensors (optional) feed back to safety agent                |
+------------------------------------------------------------------------+
```

## Consensus Model Options
1) **Majority per tick**: bucket intents into 100–250 ms epochs, pick the direction (N/E/S/W/Stop) with most votes.  
2) **Vector average** *(recommended)*: treat each intent as a 2D velocity vector `(v, ω)` and compute a clipped mean. Apply exponential smoothing. If ‖mean‖ < ε → STOP.  
3) **Ranked choice**: intents are discrete choices; run IRV each tick. Slower, more theatrical.

**Deadlock handling**: if standstill `> T_deadlock` (e.g., 3 s) → perform **tie‑break**: alternate short “shimmy” or pick the oldest non‑zero cohort for 500 ms. Always yield to the **safety gate** (e‑stop/obstacle avoidance).

## Topic & Message Schema
**Topics**
- Operator intents: `ez/rover/intent/v1/{session}/{operatorId}`
- Consensus cmd: `ez/rover/consensus/v1/{session}`
- Telemetry: `ez/rover/telemetry/v1/{session}/{node}`
- Events/alerts: `ez/rover/event/v1/{session}`

**Intent JSON**
```json
{
  "opId": "abc123",
  "session": "emea-tech-2025w44",
  "ts": 1730053202123,
  "mode": "vector",
  "v": 0.6,
  "w": -0.4,
  "priority": 1,
  "auth": "signedTokenOrProof"
}
```

**Consensus JSON**
```json
{
  "session": "emea-tech-2025w44",
  "ts": 1730053202301,
  "tick": 124,
  "v": 0.22,
  "w": -0.05,
  "reason": "vector_mean",
  "contributors": 37,
  "standstill": false
}
```

**Event JSON**
```json
{
  "severity": "WARN|ERROR|INFO",
  "code": "DEADLOCK|E_STOP|OBSTACLE|AUTH_FAIL",
  "msg": "text",
  "ts": 1730053202401
}
```

## Security & Identity
- Use **MQTT over TLS (8883)** to Solace with per‑user creds or JWT via the REST delivery point.
- Optional **mTLS** with client certs for operators.
- Rate‑limit per `opId`; drop bursts; require a **nonce** per session to avoid drive‑by griefing.

## Project Layout
```
lamavoices
├── .env
├── LICENSE
├── README.md
├── app
│   ├── agents.py
│   ├── broker.py
│   ├── consensus
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
└── scripts
    ├── run_consensus.sh
    ├── run_recorder.sh
    ├── run_rover.sh
    └── run_webui.sh
```

## Core Python Code

See folder `app`.

## Shell Scripts

See folder `scripts`.

Make executable:

```sh
chmod +x scripts/*.sh
```

## Wiring to the Solace Entanglement Demo (QR)
Map QR actions to vectors:
- `UP` → `(v=+1, w=0)`
- `DOWN` → `(v=-1, w=0)`
- `LEFT` → `(v=0, w=+1)`
- `RIGHT` → `(v=0, w=-1)`
- `STOP` → `(0,0)`

File `app/webhook.py` is the webhook (FastAPI) the QR app calls.

Run:
```sh
uvicorn app.webhook:app --host 0.0.0.0 --port 8345
```

## Solace Agent Mesh (optional but fun)
Stand up separate processes that each subscribe/transform/publish:
- **normalizer**: validate schema, squash repeats from a single operator, deduplicate.  
- **rate_limiter**: token‑bucket per `opId`.  
- **authz**: verify nonce/JWT; set `priority` for VIPs.  
- **safety**: consumes consensus, applies geofence/obstacle input; raises `event`.  
- **recorder**: writes all topics to MongoDB for replay.  

If your Solace tier supports **Replay from Time**, you can also subscribe with replay; otherwise `replay.py` in this repo re‑emits from MongoDB.

## Demo Script (5‑minute show)
1. Open the QR page → participants submit directions.  
2. Show a **live terminal** tailing `ez/rover/consensus/...`.  
3. Toggle strategies (vector mean vs majority), show standstill & tie‑break.  
4. Flip the obstacle flag → safety gate stops the rover.  
5. Drive the real VIAM Rover.

## Troubleshooting
- **No movement** → check MQTT creds/VPN; verify `SESSION_ID` alignment.  
- **VIAM base missing** → ensure a `base` component exists; else use `Motor` API.  
- **Oscillation** → raise `TICK_MS` to 300–400 ms; increase EMA `alpha` to ~0.6.  
- **Griefers** → enable per‑op rate limiting; require QR nonce/JWT.

## Next Enhancements
- CRDT‑style intent merging weighted by trust.  
- A/B cohorts to compare control quality.  
- Heatmap overlay of intents on the Web UI.

## FastAPI Web UI (Live Intents & Consensus)

**Run Web UI**
```sh
uvicorn app.webui:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080
```

## MongoDB Recorder (Replay‑ready)

**Run Recorder & Replay**
```sh
python3 -m app.recorder
# … later …
python3 -m app.replay  # replays prior session at 2x speed (as coded)
```

