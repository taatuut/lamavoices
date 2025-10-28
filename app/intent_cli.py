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
