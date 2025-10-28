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
