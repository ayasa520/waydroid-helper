import os
import re
import secrets

from waydroid_helper.controller.core.control_msg import ScreenInfo
from waydroid_helper.util.log import logger
from waydroid_helper.util.subprocess_manager import SubprocessManager

SCRCPY_SERVER_PATH_ON_DEVICE = "/data/local/tmp/scrcpy-server.jar"
SCRCPY_VERSION = "3.3.1"
# We assume the third_party folder is at project root/controller/third_party
SCRCPY_SERVER_PATH_ON_PC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../controller/third_party/scrcpy-server",
)


class AdbHelper:
    def __init__(self):
        self.sm = SubprocessManager()
        self.serial = "192.168.240.112:5555"

    async def connect(self) -> bool:
        """Connects to the ADB device using the configured serial."""
        logger.info(f"Connecting to ADB device: {self.serial}")
        try:
            result = await self.sm.run(f"adb connect {self.serial}")
            output = result["stdout"]
            if "connected" in output.lower() or "already connected" in output.lower():
                logger.info(f"Successfully connected to {self.serial}")
                return True
            else:
                logger.warning(f"ADB connect output: {output}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to ADB device {self.serial}: {e}")
            return False

    async def get_screen_resolution(self) -> tuple[int, int] | None:
        logger.info("Getting device screen resolution...")
        try:
            result = await self.sm.run(f"adb -s {self.serial} shell dumpsys window displays")
            output = result["stdout"]
            match = re.search(r"cur=(\d+)x(\d+)", output)
            if match:
                width = int(match.group(1))
                height = int(match.group(2))
                ScreenInfo().set_resolution(width, height)
                logger.info(f"Device resolution set to: {width}x{height}")
                return width, height
            else:
                logger.warning(
                    "Could not determine device resolution from 'wm size' output."
                )
                return None
        except Exception as e:
            logger.error(f"Failed to get screen resolution: {e}")
            return None

    async def push_scrcpy_server(self) -> bool:
        logger.info(f"Pushing scrcpy-server to {SCRCPY_SERVER_PATH_ON_DEVICE}")
        try:
            if not os.path.exists(SCRCPY_SERVER_PATH_ON_PC):
                logger.error(f"scrcpy-server not found at {SCRCPY_SERVER_PATH_ON_PC}")
                return False
            await self.sm.run(
                f"adb -s {self.serial} push {SCRCPY_SERVER_PATH_ON_PC} {SCRCPY_SERVER_PATH_ON_DEVICE}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to push scrcpy-server: {e}")
            return False

    async def reverse_tunnel(self, socket_name: str, port: int) -> bool:
        logger.info("Setting up adb reverse tunnel")
        try:
            await self.sm.run(f"adb -s {self.serial} reverse --remove-all")
            await self.sm.run(f"adb -s {self.serial} reverse localabstract:{socket_name} tcp:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to set up adb reverse tunnel: {e}")
            return False

    async def remove_reverse_tunnel(self) -> bool:
        logger.info("Removing adb reverse tunnel")
        try:
            await self.sm.run(f"adb -s {self.serial} reverse --remove-all")
            return True
        except Exception as e:
            logger.error(f"Failed to remove adb reverse tunnel: {e}")
            return False

    async def start_scrcpy_server(self, scid: str) -> bool:
        logger.info("Starting scrcpy-server on device")
        try:
            server_command = (
                f"adb -s {self.serial} shell CLASSPATH={SCRCPY_SERVER_PATH_ON_DEVICE} app_process / com.genymobile.scrcpy.Server "
                f"{SCRCPY_VERSION} scid={scid} log_level=debug video=false audio=false control=true"
            )
            await self.sm.run(server_command, flag=True)
            logger.info("scrcpy-server start command sent.")
            return True
        except Exception as e:
            logger.error(f"Failed to start scrcpy-server: {e}")
            return False

    def generate_scid(self) -> tuple[str, str]:
        scid_int = secrets.randbelow(0x7FFFFFFF)
        scid = f"{scid_int:x}"
        socket_name = f"scrcpy_{scid}"
        logger.info(f"Generated SCID (hex): {scid}, socket name: {socket_name}")
        return scid, socket_name 