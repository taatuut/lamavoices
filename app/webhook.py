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
