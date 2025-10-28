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
