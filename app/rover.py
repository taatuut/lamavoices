from viam.robot.client import RobotClient
from viam.rpc.dial import DialOptions, Credentials
from viam.components.base import Base
import logging, os, asyncio


class RobotClientOptions:
    """Shim for SDKs missing viam.robot.client.Options."""
    def __init__(self, dial_options, log_level=logging.INFO, disable_sessions=False):
        self.dial_options = dial_options
        self.log_level = log_level
        self.disable_sessions = disable_sessions

async def connect_viam():
    """Connect to a Viam rover using API key credentials."""
    robot_address = os.getenv("VIAM_ROBOT_ADDRESS")
    base_name = os.getenv("VIAM_BASE_NAME", "base")
    key_id = os.getenv("VIAM_API_KEY_ID")
    key = os.getenv("VIAM_API_KEY")

    if not all([robot_address, key_id, key]):
        raise EnvironmentError("Missing VIAM_ROBOT_ADDRESS, VIAM_API_KEY_ID, or VIAM_API_KEY in .env")

    creds = Credentials(type="api-key", payload=key)
    dial_opts = DialOptions(credentials=creds, auth_entity=key_id)
    opts = RobotClientOptions(dial_opts)  # ✅ replaces missing Options()

    print(f"🤖 Connecting to Viam Rover at {robot_address}")
    robot = await RobotClient.at_address(robot_address, opts)
    base = Base.from_robot(robot, base_name)
    print(f"✅ Connected to rover base '{base_name}'")
    return robot, base

async def apply_cmd(base, v, w):
    """
    Apply a velocity command to the Viam rover base.
    v: linear velocity (m/s)
    w: angular velocity (rad/s)
    """
    try:
        # Convert angular velocity to degrees/sec if necessary
        angular_deg = w * 180.0 / 3.14159

        if abs(v) < 1e-3 and abs(w) < 1e-3:
            await base.stop()
            print("🛑 Rover stopped")
        else:
            await base.set_power(linear=v, angular=angular_deg)
            print(f"🚗 Rover moving — v={v:.2f} m/s, w={w:.2f} rad/s")
    except Exception as e:
        print(f"⚠️ Failed to apply motion command: {e}")