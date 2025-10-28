import asyncio
import logging
import os
from viam.robot.client import RobotClient
from viam.rpc.dial import DialOptions, Credentials

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def connect_viam():
    robot_address = os.getenv("VIAM_ROBOT_ADDRESS")
    api_key_id = os.getenv("VIAM_API_KEY_ID")
    api_key = str(os.getenv("VIAM_API_KEY"))
    base_name = os.getenv("VIAM_BASE_NAME")

    creds = Credentials(type="api-key", payload=api_key)
    dial_options = DialOptions(auth_entity=api_key_id, credentials=creds)
    opts = RobotClient.Options(dial_options=dial_options)

    logger.info(f"🤖 Connecting to Viam Rover at {robot_address}")

    print("creds:", creds, type(creds))
    print("dial_options:", dial_options, type(dial_options))
    print("creds attributes:", getattr(creds, "__dict__", None))

    try:
        robot = await RobotClient.at_address(robot_address, opts)
        base = await robot.get_component(base_name)
        logger.info("✅ Successfully connected to the Viam robot.")
        return robot, base

    except ConnectionError:
        logger.error("❌ ConnectionError: Unable to establish a connection to the machine.", exc_info=False)
        print(
            "\n⚠️  ConnectionError: Unable to establish a connection to the machine.\n"
            "   - Ensure your robot is online in app.viam.com\n"
            "   - Verify viam-server is running and connected to the cloud.\n"
        )
        return None, None

    except Exception as e:
        logger.error(f"❌ Unexpected error while connecting to the robot: {e}", exc_info=False)
        logger.debug("Full traceback:", exc_info=True)
        print("\n⚠️  Unexpected error while connecting to the robot. Check logs for details.\n")
        return None, None


async def apply_cmd(base, linear_vel, angular_vel):
    cmd = {"linear": linear_vel, "angular": angular_vel}
    logger.info(f"Applying command: {cmd}")
    try:
        await base.move_straight(linear_vel, angular_vel)
        logger.info("Command applied successfully.")
    except Exception as e:
        logger.error(f"⚠️ Error applying command: {e}", exc_info=False)
        logger.debug("Full traceback:", exc_info=True)
        print("\n⚠️  Error while sending command to rover. Check logs for details.\n")


if __name__ == "__main__":
    asyncio.run(connect_viam())
