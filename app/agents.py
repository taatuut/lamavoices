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
