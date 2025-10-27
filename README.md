# Lamavoices
to create a consensus operated robot

# Context
I have a VIAM Rover robot https://www.viam.com/resources/rover, and at Solace we have the entanglement demo https://sg.solace.rocks/qr/. How can these be combined to create a consensus based operated robot. It might literally not go anywhere at all if all people push for different directions. Similar to https://www.viam.com/resources/try-viam where one person can control a VIAM Rover robot in a lab but then real-time con trolled by multiple people using Solace event broker, maybe even add Solace Agent Mesh to the mix. This repo provides e a comprehensive plan layout and code framework to get it all working using Python as main programming language on macOS system, where necessary supported by tooling like brew installs, terminal shell scripts etc.

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

> **Purpose:** Operate a VIAM Rover by *crowd consensus* using Solace PubSub+. Many participants send intents; a consensus service merges them into one safe command stream. Includes a tiny FastAPI Web UI (live intents & consensus), a MongoDB recorder, and simple replay.

---

## Table of Contents
- [Goal](#goal)
- [High‑Level Architecture](#high-level-architecture)
- [Consensus Model Options](#consensus-model-options)
- [Topics & Message Schemas](#topics--message-schema)
- [Security & Identity](#security--identity)
- [Setup on macOS (Homebrew + Python)](#macos-setup-homebrew--python)
- [Project Layout](#project-layout)
- [Core Python Code](#core-python-code)
  - [`app/schema.py`](#appschemapy)
  - [`app/broker.py` (MQTT to Solace)](#appbrokerpy-mqtt-to-solace)
  - [`app/consensus.py`](#appconsensuspy)
  - [`app/safety.py`](#appsafetypy)
  - [`app/rover.py` (VIAM client)](#approverpy-viam-client)
  - [`app/agents.py`](#appagentspy)
  - [`app/runner.py`](#apprunnerpy)
- [Minimal Intent Publisher (CLI)](#minimal-intent-publisher-for-demos)
- [Run Scripts](#run-scripts)
- [Wiring the Solace Entanglement QR Demo](#wiring-to-the-solace-entanglement-demo-qr)
- [Solace Agent Mesh Ideas](#solace-agent-mesh-optional-but-fun)
- [Demo Script (5‑minute show)](#demo-script-5minute-show)
- [Troubleshooting](#troubleshooting)
- [Next Enhancements](#next-enhancements)
- [Tiny FastAPI Web UI (Live Intents & Consensus)](#tiny-fastapi-web-ui-live-intents--consensus)
- [MongoDB Recorder + Replay](#mongodb-recorder-replay-ready)
- [New Run Scripts](#new-run-scripts)
- [Notes](#notes)

---

## Goal
Use a VIAM Rover controlled by Python while *many people* send control intents simultaneously. All intents flow through Solace PubSub+ and are combined by a consensus service that outputs a single safe command stream to the rover. If everyone disagrees, the rover (safely) doesn’t move — or performs a tie‑break behavior.

---

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

---

## Consensus Model Options
1) **Majority per tick**: bucket intents into 100–250 ms epochs, pick the direction (N/E/S/W/Stop) with most votes.  
2) **Vector average** *(recommended)*: treat each intent as a 2D velocity vector `(v, ω)` and compute a clipped mean. Apply exponential smoothing. If ‖mean‖ < ε → STOP.  
3) **Ranked choice**: intents are discrete choices; run IRV each tick. Slower, more theatrical.

**Deadlock handling**: if standstill `> T_deadlock` (e.g., 3 s) → perform **tie‑break**: alternate short “shimmy” or pick the oldest non‑zero cohort for 500 ms. Always yield to the **safety gate** (e‑stop/obstacle avoidance).

---

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

---

## Security & Identity
- Use **MQTT over TLS (8883)** to Solace with per‑user creds or JWT via the REST delivery point.
- Optional **mTLS** with client certs for operators.
- Rate‑limit per `opId`; drop bursts; require a **nonce** per session to avoid drive‑by griefing.

---

## macOS Setup (Homebrew + Python)
```bash
# 1) Basics
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11 uv

# 2) Create project
mkdir consensus-rover && cd $_
uv venv            # or: python3 -m venv .venv
source .venv/bin/activate

# 3) Python deps
uv add paho-mqtt pydantic==2.* uvloop==0.*
uv add viam-sdk    # VIAM Python SDK
uv add aiohttp fastapi uvicorn[standard] python-dotenv rich
```
Create `.env`:
```ini
SOLACE_HOST="tcp://<host>:8883"     # use ssl:// for TLS; e.g. ssl://your.msg.solace.cloud:8883
SOLACE_USERNAME="<vpn>/<client-username>"
SOLACE_PASSWORD="<password>"
SOLACE_CLIENT_ID="consensus-node-1"

SESSION_ID="emea-tech-2025w44"
TICK_MS=200

# VIAM
VIAM_ROBOT_ADDRESS="<robot-address>:8080"
VIAM_API_KEY_ID="<key-id>"
VIAM_API_KEY="<secret>"
VIAM_BASE_NAME="base"
```

---

## Project Layout
```
consensus-rover/
  app/
    __init__.py
    schema.py
    broker.py
    consensus.py
    safety.py
    rover.py
    runner.py
    agents.py
    webui.py
    recorder.py
    replay.py
  scripts/
    run_consensus.sh
    run_rover.sh
    run_webui.sh
    run_recorder.sh
  .env
```

---

## Core Python Code

### `app/schema.py`
```python
from pydantic import BaseModel, Field
from typing import Literal

class Intent(BaseModel):
    opId: str
    session: str
    ts: int
    mode: Literal["vector", "discrete"] = "vector"
    v: float = 0.0  # -1..1
    w: float = 0.0  # -1..1
    priority: int = 1
    auth: str | None = None

class ConsensusCmd(BaseModel):
    session: str
    ts: int
    tick: int
    v: float
    w: float
    reason: str
    contributors: int
    standstill: bool = False

class Event(BaseModel):
    severity: Literal["INFO","WARN","ERROR"] = "INFO"
    code: str
    msg: str
    ts: int
```

### `app/broker.py` (MQTT to Solace)
```python
import json, ssl, os, time
import paho.mqtt.client as mqtt
from typing import Callable

class MqttBus:
    def __init__(self, client_id: str | None = None):
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        host = os.getenv("SOLACE_HOST", "ssl://localhost:8883")
        if host.startswith("ssl://") or host.endswith(":8883"):
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self.client.username_pw_set(os.getenv("SOLACE_USERNAME", ""), os.getenv("SOLACE_PASSWORD", ""))
        self.host, self.port = self._parse_host(host)
        self._on_msg_handlers: list[Callable[[str, bytes], None]] = []

    @staticmethod
    def _parse_host(url: str):
        scheme, rest = url.split("://", 1)
        host, port = rest.split(":")
        return host, int(port)

    def connect(self):
        self.client.on_message = lambda c, u, m: [h(m.topic, m.payload) for h in self._on_msg_handlers]
        self.client.connect(self.host, self.port, keepalive=30)
        self.client.loop_start()

    def publish(self, topic: str, payload: dict, qos: int = 1):
        self.client.publish(topic, json.dumps(payload).encode("utf-8"), qos=qos)

    def subscribe(self, topic: str):
        self.client.subscribe(topic, qos=1)

    def on_message(self, handler: Callable[[str, bytes], None]):
        self._on_msg_handlers.append(handler)
```

### `app/consensus.py`
```python
import time, math
from collections import defaultdict, deque
from typing import Dict, Tuple
from .schema import Intent, ConsensusCmd

class VectorConsensus:
    def __init__(self, tick_ms=200, deadlock_s=3.0, eps=0.07, alpha=0.4, vmax=0.6, wmax=0.8):
        self.tick_ms = tick_ms
        self.deadlock_s = deadlock_s
        self.eps = eps
        self.alpha = alpha
        self.vmax = vmax
        self.wmax = wmax
        self.buffer: Dict[str, list[Intent]] = defaultdict(list)
        self.last_nonzero_ts = time.time()
        self.sv_v = 0.0  # smoothed
        self.sv_w = 0.0
        self.tick = 0

    def ingest(self, intent: Intent):
        self.buffer[intent.session].append(intent)

    def _aggregate(self, session: str) -> Tuple[float, float, int]:
        intents = self.buffer.pop(session, [])
        if not intents:
            return 0.0, 0.0, 0
        # Weighted clipped mean
        total_w = sum(max(1, min(3, i.priority)) for i in intents)
        if total_w == 0:
            return 0.0, 0.0, len(intents)
        v = sum(i.v * max(1, min(3, i.priority)) for i in intents) / total_w
        w = sum(i.w * max(1, min(3, i.priority)) for i in intents) / total_w
        # clip
        v = max(-1.0, min(1.0, v)) * self.vmax
        w = max(-1.0, min(1.0, w)) * self.wmax
        return v, w, len(intents)

    def tick_once(self, session: str) -> ConsensusCmd:
        self.tick += 1
        v_raw, w_raw, n = self._aggregate(session)
        # EMA smoothing
        self.sv_v = self.alpha * v_raw + (1 - self.alpha) * self.sv_v
        self.sv_w = self.alpha * w_raw + (1 - self.alpha) * self.sv_w
        mag = math.hypot(self.sv_v, self.sv_w)
        standstill = mag < self.eps
        if not standstill:
            self.last_nonzero_ts = time.time()
        elif time.time() - self.last_nonzero_ts > self.deadlock_s:
            # tie-break shimmy
            self.sv_w = 0.3 * self.wmax
        return ConsensusCmd(
            session=session,
            ts=int(time.time()*1000),
            tick=self.tick,
            v=0.0 if standstill else self.sv_v,
            w=0.0 if standstill else self.sv_w,
            reason="vector_mean",
            contributors=n,
            standstill=standstill,
        )
```

### `app/safety.py`
```python
from .schema import ConsensusCmd

class SafetyGate:
    def __init__(self, max_v=0.6, max_w=0.8, obstacle=False):
        self.max_v=max_v; self.max_w=max_w; self.obstacle=obstacle

    def apply(self, cmd: ConsensusCmd) -> ConsensusCmd:
        if self.obstacle:
            cmd.v = 0.0; cmd.w = 0.0; cmd.reason += "+obstacle"
            cmd.standstill = True
            return cmd
        cmd.v = max(-self.max_v, min(self.max_v, cmd.v))
        cmd.w = max(-self.max_w, min(self.max_w, cmd.w))
        return cmd
```

### `app/rover.py` (VIAM client)
```python
import os, asyncio
from viam.robot.client import RobotClient
from viam.rpc.dial import DialOptions
from viam.components.base import BaseClient

async def connect_viam() -> tuple[RobotClient, BaseClient]:
    opts = DialOptions(without_security=False, auth_entity=os.getenv("VIAM_API_KEY_ID"),
                       credentials=(os.getenv("VIAM_API_KEY_ID"), os.getenv("VIAM_API_KEY")))
    robot = await RobotClient.at_address(os.getenv("VIAM_ROBOT_ADDRESS"), options=opts)
    base = robot.resource_by_name(BaseClient, os.getenv("VIAM_BASE_NAME", "base"))
    return robot, base

async def apply_cmd(base: BaseClient, v: float, w: float, dt: float=0.2):
    # VIAM "base" supports set_velocity(linear, angular)
    await base.set_velocity(linear=v, angular=w)
    await asyncio.sleep(dt)
```

### `app/agents.py`
```python
import asyncio, json, time, os
from .broker import MqttBus
from .schema import Intent
from .consensus import VectorConsensus
from .safety import SafetyGate

class ConsensusAgent:
    def __init__(self, bus: MqttBus, session: str):
        self.bus = bus
        self.session = session
        self.cons = VectorConsensus(
            tick_ms=int(os.getenv("TICK_MS", "200"))
        )
        self.safety = SafetyGate()
        self.bus.on_message(self._on_msg)
        self.bus.subscribe(f"ez/rover/intent/v1/{self.session}/+")

    def _on_msg(self, topic: str, payload: bytes):
        try:
            d = json.loads(payload.decode("utf-8"))
            intent = Intent(**d)
            self.cons.ingest(intent)
        except Exception as e:
            print("bad intent:", e)

    async def loop(self):
        tick = self.cons.tick_ms / 1000
        while True:
            cmd = self.cons.tick_once(self.session)
            cmd = self.safety.apply(cmd)
            self.bus.publish(f"ez/rover/consensus/v1/{self.session}", cmd.model_dump())
            await asyncio.sleep(tick)
```

### `app/runner.py`
```python
import asyncio, os, json
from .broker import MqttBus
from .rover import connect_viam, apply_cmd

async def rover_runner():
    session = os.getenv("SESSION_ID", "demo")
    bus = MqttBus(client_id=os.getenv("SOLACE_CLIENT_ID", "rover"))
    bus.connect()
    robot, base = await connect_viam()

    def on_msg(topic: str, payload: bytes):
        try:
            d = json.loads(payload.decode("utf-8"))
            asyncio.get_event_loop().create_task(apply_cmd(base, d["v"], d["w"], dt=int(os.getenv("TICK_MS","200"))/1000))
        except Exception as e:
            print("bad consensus:", e)

    bus.on_message(on_msg)
    bus.subscribe(f"ez/rover/consensus/v1/{session}")
    print("Rover runner ready.")
    while True:
        await asyncio.sleep(1)

async def consensus_runner():
    from .agents import ConsensusAgent
    bus = MqttBus(client_id=os.getenv("SOLACE_CLIENT_ID", "consensus"))
    bus.connect()
    agent = ConsensusAgent(bus, os.getenv("SESSION_ID", "demo"))
    await agent.loop()

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("which", choices=["consensus","rover"])
    args = p.parse_args()
    if args.which == "consensus":
        asyncio.run(consensus_runner())
    else:
        asyncio.run(rover_runner())
```

---

## Minimal Intent Publisher (for demos)
```bash
uv add typer
```
`intent_cli.py`:
```python
import json, time, os, random
import typer
from app.broker import MqttBus

app = typer.Typer()

@app.command()
def spam(op_id: str = "cli", v: float = 0.5, w: float = 0.0, hz: float = 5.0):
    bus = MqttBus(client_id=f"op-{op_id}-{random.randint(0,9999)}")
    bus.connect()
    topic = f"ez/rover/intent/v1/{os.getenv('SESSION_ID','demo')}/{op_id}"
    period = 1.0 / hz
    try:
        while True:
            msg = {
                "opId": op_id,
                "session": os.getenv("SESSION_ID","demo"),
                "ts": int(time.time()*1000),
                "mode": "vector",
                "v": v,
                "w": w,
                "priority": 1,
            }
            bus.publish(topic, msg)
            time.sleep(period)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    app()
```

---

## Run Scripts
`scripts/run_consensus.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate || source .venv/bin/activate.fish || true
python -m app.runner consensus
```

`scripts/run_rover.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate || source .venv/bin/activate.fish || true
python -m app.runner rover
```

Make executable:
```bash
chmod +x scripts/*.sh
```

---

## Wiring to the Solace Entanglement Demo (QR)
Map QR actions to vectors:
- `UP` → `(v=+1, w=0)`
- `DOWN` → `(v=-1, w=0)`
- `LEFT` → `(v=0, w=+1)`
- `RIGHT` → `(v=0, w=-1)`
- `STOP` → `(0,0)`

A tiny webhook (FastAPI) the QR app calls:
```python
from fastapi import FastAPI
from pydantic import BaseModel
from app.broker import MqttBus
import os, time

app = FastAPI()
bus = MqttBus(client_id="qr-bridge"); bus.connect()
SESSION = os.getenv("SESSION_ID","demo")

actions = {
    "UP":  (1.0, 0.0),
    "DOWN":(-1.0,0.0),
    "LEFT":(0.0, 1.0),
    "RIGHT":(0.0,-1.0),
    "STOP":(0.0, 0.0)
}

class Click(BaseModel):
    opId: str
    action: str

@app.post("/qr")
def qr(click: Click):
    v, w = actions.get(click.action.upper(), (0.0,0.0))
    msg = {"opId": click.opId, "session": SESSION, "ts": int(time.time()*1000),
           "mode":"vector", "v": v, "w": w, "priority": 1}
    bus.publish(f"ez/rover/intent/v1/{SESSION}/{click.opId}", msg)
    return {"ok": True}
```
Run:
```bash
uvicorn webhook:app --host 0.0.0.0 --port 8081
```

---

## Solace Agent Mesh (optional but fun)
Stand up separate processes that each subscribe/transform/publish:
- **normalizer**: validate schema, squash repeats from a single operator, deduplicate.  
- **rate_limiter**: token‑bucket per `opId`.  
- **authz**: verify nonce/JWT; set `priority` for VIPs.  
- **safety**: consumes consensus, applies geofence/obstacle input; raises `event`.  
- **recorder**: writes all topics to MongoDB for replay.  

If your Solace tier supports **Replay from Time**, you can also subscribe with replay; otherwise `replay.py` in this repo re‑emits from MongoDB.

---

## Demo Script (5‑minute show)
1. Open the QR page → participants submit directions.  
2. Show a **live terminal** tailing `ez/rover/consensus/...`.  
3. Toggle strategies (vector mean vs majority), show standstill & tie‑break.  
4. Flip the obstacle flag → safety gate stops the rover.  
5. Drive the real VIAM Rover.

---

## Troubleshooting
- **No movement** → check MQTT creds/VPN; verify `SESSION_ID` alignment.  
- **VIAM base missing** → ensure a `base` component exists; else use `Motor` API.  
- **Oscillation** → raise `TICK_MS` to 300–400 ms; increase EMA `alpha` to ~0.6.  
- **Griefers** → enable per‑op rate limiting; require QR nonce/JWT.

---

## Next Enhancements
- CRDT‑style intent merging weighted by trust.  
- A/B cohorts to compare control quality.  
- Heatmap overlay of intents on the Web UI.

---

## Tiny FastAPI Web UI (Live Intents & Consensus)

**Install extra deps**
```bash
uv add motor==3.* itsdangerous
```

**`app/webui.py`**
```python
import asyncio, json, os, time
from typing import AsyncIterator, Dict, Set
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from app.broker import MqttBus

SESSION = os.getenv("SESSION_ID", "demo")

app = FastAPI(title="Consensus Rover — Live")
bus = MqttBus(client_id="webui"); bus.connect()

class Fanout:
    def __init__(self):
        self.listeners: Set[asyncio.Queue] = set()
    def register(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.listeners.add(q)
        return q
    def unregister(self, q: asyncio.Queue):
        self.listeners.discard(q)
    def publish(self, item: dict):
        for q in list(self.listeners):
            try:
                q.put_nowait(item)
            except asyncio.QueueFull:
                pass

intent_bus = Fanout()
consensus_bus = Fanout()

bus.subscribe(f"ez/rover/intent/v1/{SESSION}/+")
bus.subscribe(f"ez/rover/consensus/v1/{SESSION}")

stats = {"operators": set(), "intents": 0, "last_cmd": None}

bus.on_message(lambda topic, payload: on_msg(topic, payload))

def on_msg(topic: str, payload: bytes):
    try:
        d = json.loads(payload.decode("utf-8"))
        if topic.startswith(f"ez/rover/intent/v1/{SESSION}/"):
            op = d.get("opId", "?")
            stats["operators"].add(op)
            stats["intents"] += 1
            intent_bus.publish({"type": "intent", **d})
        elif topic == f"ez/rover/consensus/v1/{SESSION}":
            stats["last_cmd"] = d
            consensus_bus.publish({"type": "consensus", **d})
    except Exception:
        pass

async def sse_stream(fanout: Fanout):
    q = fanout.register()
    try:
        while True:
            item = await q.get()
            yield f"data: {json.dumps(item)}\n\n".encode("utf-8")
    finally:
        fanout.unregister(q)

@app.get("/sse/intent")
async def sse_intent():
    return StreamingResponse(sse_stream(intent_bus), media_type="text/event-stream")

@app.get("/sse/consensus")
async def sse_consensus():
    return StreamingResponse(sse_stream(consensus_bus), media_type="text/event-stream")

@app.get("/")
async def index() -> HTMLResponse:
    html = f\"\"\"
<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>Consensus Rover — Live</title>
  <style>
    body {{ font-family: -apple-system, system-ui, Segoe UI, Roboto, sans-serif; margin: 24px; }}
    .card {{ padding:16px; border:1px solid #ddd; border-radius:12px; margin-bottom:16px; }}
    #log {{ height: 220px; overflow:auto; background:#fafafa; padding:8px; border-radius:8px; border:1px solid #eee; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>Consensus Rover — Live</h1>
  <div class='card'>
    <b>Session:</b> <code>{SESSION}</code>
    <div id='stats'></div>
  </div>
  <div class='card'>
    <h3>Latest Consensus</h3>
    <pre id='consensus'><em>waiting…</em></pre>
  </div>
  <div class='card'>
    <h3>Incoming Intents</h3>
    <div id='log'></div>
  </div>
<script>
function esc(s) { return s.replace(/[&<>]/g, c=>({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c])); }
const s1 = new EventSource('/sse/intent');
const s2 = new EventSource('/sse/consensus');
let operators = new Set();
let intents = 0;

s1.onmessage = (ev)=>{
  const d = JSON.parse(ev.data);
  operators.add(d.opId||'?');
  intents++;
  const log = document.getElementById('log');
  const line = document.createElement('div');
  line.innerHTML = `<code>${{new Date().toLocaleTimeString()}} op=${{esc(d.opId||'?')}} v=${{(d.v||0).toFixed(2)}} w=${{(d.w||0).toFixed(2)}}</code>`;
  log.prepend(line);
  const arr = [...log.children];
  if (arr.length>200) arr.slice(200).forEach(n=>n.remove());
  document.getElementById('stats').innerHTML = `<b>Operators:</b> ${{operators.size}} &nbsp; <b>Intents:</b> ${{intents}}`;
};

s2.onmessage = (ev)=>{
  const d = JSON.parse(ev.data);
  document.getElementById('consensus').textContent = JSON.stringify(d, null, 2);
};
</script>
</body>
</html>
\"\"\"
    return HTMLResponse(html)
```

**Run Web UI**
```bash
uvicorn app.webui:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080
```

---

## MongoDB Recorder (Replay‑ready)

**Env**
```ini
MONGODB_URI="mongodb+srv://<user>:<pass>@<cluster>/consensus?retryWrites=true&w=majority"
MONGODB_DB="consensus"
```

**`app/recorder.py`**
```python
import os, json, asyncio, time
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.broker import MqttBus

SESSION = os.getenv("SESSION_ID", "demo")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DBNAME = os.getenv("MONGODB_DB", "consensus")

async def main():
    cli = AsyncIOMotorClient(MONGODB_URI)
    db = cli[DBNAME]
    intents = db.intents
    consensus = db.consensus
    events = db.events

    bus = MqttBus(client_id="recorder"); bus.connect()
    bus.subscribe(f"ez/rover/intent/v1/{SESSION}/+")
    bus.subscribe(f"ez/rover/consensus/v1/{SESSION}")
    bus.subscribe(f"ez/rover/event/v1/{SESSION}")

    loop = asyncio.get_event_loop()

    def on_msg(topic: str, payload: bytes):
        d = json.loads(payload.decode("utf-8"))
        d["_ts"] = datetime.utcnow()
        if topic.startswith(f"ez/rover/intent/v1/{SESSION}/"):
            loop.create_task(intents.insert_one(d))
        elif topic == f"ez/rover/consensus/v1/{SESSION}":
            loop.create_task(consensus.insert_one(d))
        else:
            loop.create_task(events.insert_one(d))

    bus.on_message(on_msg)
    print("Recorder connected. Press Ctrl+C to stop.")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

**Indexes (optional)**
```python
await db.intents.create_index([('session', 1), ('ts', 1)])
await db.consensus.create_index([('session', 1), ('ts', 1)])
```

**`app/replay.py` (time‑scaled)** 
```python
import os, asyncio, time
from motor.motor_asyncio import AsyncIOMotorClient
from app.broker import MqttBus

SESSION = os.getenv("SESSION_ID","demo")
MONGODB_URI = os.getenv("MONGODB_URI","mongodb://localhost:27017")
DBNAME = os.getenv("MONGODB_DB","consensus")

async def main(scale: float = 1.0):
    cli = AsyncIOMotorClient(MONGODB_URI)
    db = cli[DBNAME]
    bus = MqttBus(client_id="replay"); bus.connect()
    cur = db.intents.find({"session": SESSION}).sort("ts", 1)
    t0_db = None; t0_rt = time.time()
    async for d in cur:
        if t0_db is None: t0_db = d["ts"]
        dt = (d["ts"] - t0_db)/1000.0/scale
        await asyncio.sleep(max(0, t0_rt + dt - time.time()))
        bus.publish(f"ez/rover/intent/v1/{SESSION}/{d.get('opId','replay')}", {k:v for k,v in d.items() if k!="_id"})

if __name__ == "__main__":
    asyncio.run(main(scale=2.0))
```

**Run Recorder & Replay**
```bash
python -m app.recorder
# … later …
python -m app.replay  # replays prior session at 2x speed (as coded)
```

---

## New Run Scripts
`scripts/run_webui.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate || true
uvicorn app.webui:app --host 0.0.0.0 --port 8080
```

`scripts/run_recorder.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate || true
python -m app.recorder
```

