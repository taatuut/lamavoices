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
