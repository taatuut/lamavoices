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
