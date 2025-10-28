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

    # await db.intents.create_index([('session', 1), ('ts', 1)])
    # await db.consensus.create_index([('session', 1), ('ts', 1)])

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
