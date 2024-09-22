import logging
from .control_msg import ControlMsg
from .server import Server

logger = logging.getLogger(__name__)

class Controller:
    def __init__(self, server:Server) -> None:
        self.server = server

    def send_msg(self, msg:ControlMsg):
        logger.info(msg)
        packed = msg.pack()
        if packed:
            self.server.send(packed)
        